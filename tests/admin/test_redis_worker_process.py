import os
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
import redis

from app.services.task_queue_service import TaskQueueService


@pytest.mark.skipif(not os.environ.get('TEST_REDIS_URL'), reason='requires dedicated test Redis')
def test_idle_worker_consumes_later_task_across_processes():
    connection = redis.Redis.from_url(os.environ['TEST_REDIS_URL'])
    name = 'integration-' + uuid.uuid4().hex
    queue = TaskQueueService(redis_connection=connection, queue_name=name)
    root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env['PYTHONPATH'] = os.pathsep.join((str(root / 'backend'), str(root)))
    code = """
import os, redis, sys
from app.services.task_queue_service import TaskQueueService
from app.services.task_worker import TaskWorker
queue = TaskQueueService(redis_connection=redis.Redis.from_url(os.environ['TEST_REDIS_URL']), queue_name=sys.argv[1])
TaskWorker(queue, handlers={'test': lambda payload: {'value': payload['value']}}).run_forever(idle_sleep_seconds=0.1)
"""
    worker = subprocess.Popen([sys.executable, '-c', code, name], cwd=str(root), env=env)
    try:
        time.sleep(1)
        assert worker.poll() is None
        task = queue.enqueue(task_type='test', payload={'value': 42})
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            current = queue.get_task(task['task_id'])
            if current['status'] == 'succeeded':
                break
            assert worker.poll() is None
            time.sleep(0.1)
        assert current['status'] == 'succeeded'
        assert current['result'] == {'value': 42}
    finally:
        worker.terminate()
        worker.wait(timeout=10)


@pytest.mark.skipif(not os.environ.get('TEST_REDIS_URL'), reason='requires dedicated test Redis')
def test_concurrent_producers_share_one_job_per_active_version():
    url = os.environ['TEST_REDIS_URL']
    name = 'integration-' + uuid.uuid4().hex
    participants = 8
    start = Barrier(participants)

    def submit(index):
        version = str(index % 2)
        with redis.Redis.from_url(url) as connection:
            queue = TaskQueueService(redis_connection=connection, queue_name=name)
            start.wait(timeout=10)
            task = queue.enqueue(
                task_type='knowledge_index_document',
                payload={'document_id': 'doc', 'version_id': version},
                idempotency_key='knowledge_index_document:doc:' + version,
            )
            return version, task['task_id']

    with ThreadPoolExecutor(max_workers=participants) as pool:
        results = set(pool.map(submit, range(participants)))
    assert len(results) == 2
    job_ids = {job_id for _, job_id in results}
    with redis.Redis.from_url(url) as connection:
        queue = TaskQueueService(redis_connection=connection, queue_name=name)
        assert queue.rq_queue.count == len(job_ids) == 2
        assert {queue.claim_next()['task_id'] for _ in range(2)} == job_ids
        assert queue.claim_next() is None
        assert len(queue.list_tasks()) == 2


@pytest.mark.skipif(not os.environ.get('TEST_REDIS_URL'), reason='requires dedicated test Redis')
@pytest.mark.parametrize('stop_before_commit', [True, False])
def test_killed_worker_recovers_with_consistent_api_and_fenced_retry(stop_before_commit, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from rq.job import Job, JobStatus
    from app.admin_main import app
    from app.api.admin import tasks as tasks_api
    from app.services.auth_service import auth_service
    from app.services.task_queue_service import ActiveTaskConflict

    connection = redis.Redis.from_url(os.environ['TEST_REDIS_URL'])
    name = 'recovery-' + uuid.uuid4().hex
    queue = TaskQueueService(redis_connection=connection, queue_name=name, lease_seconds=1.5)
    task = queue.enqueue(task_type='test', payload={}, idempotency_key='test:v1')
    signal = name + ':signal'
    env = os.environ.copy()
    root = Path(__file__).resolve().parents[2]
    env['PYTHONPATH'] = os.pathsep.join((str(root / 'backend'), str(root)))
    code = '''
import os, redis, sys, time
from app.services.task_queue_service import TaskQueueService
from app.services.task_worker import TaskWorker
c=redis.Redis.from_url(os.environ['TEST_REDIS_URL'])
q=TaskQueueService(redis_connection=c, queue_name=sys.argv[1], lease_seconds=1.5)
if sys.argv[3] == '1':
    original=q._save_task
    def blocked(*args, **kwargs):
        original(*args, **kwargs)
        c.set(sys.argv[2], 'before')
        time.sleep(60)
    q._save_task=blocked
def handler(payload):
    c.set(sys.argv[2], 'running')
    time.sleep(60)
    return {}
TaskWorker(q, handlers={'test': handler}).run_forever(idle_sleep_seconds=.1)
'''
    worker = subprocess.Popen([sys.executable, '-c', code, name, signal, '1' if stop_before_commit else '0'], cwd=str(root), env=env)
    try:
        deadline = time.monotonic() + 15
        while not connection.get(signal) and time.monotonic() < deadline:
            assert worker.poll() is None
            time.sleep(.05)
        assert connection.get(signal)
        before = queue.get_task(task['task_id'])
        worker.kill()
        worker.wait(timeout=10)
        if stop_before_commit:
            assert before['status'] == 'queued'
            assert queue.rq_queue.job_ids == [task['task_id']]
            assert Job.fetch(task['task_id'], connection=connection).get_status() == JobStatus.QUEUED
            return

        assert before['status'] == 'running'
        old_token = Job.fetch(task['task_id'], connection=connection).meta['task']['lease_token']
        started = time.monotonic()
        while time.monotonic() - started < 5:
            status = queue.get_task(task['task_id'])
            if status['status'] == 'failed':
                break
            time.sleep(.05)
        elapsed = time.monotonic() - started
        assert status['status'] == 'failed' and elapsed < 3
        assert 'verify side effects' in status['error']
        assert Job.fetch(task['task_id'], connection=connection).get_status() == JobStatus.FAILED
        auth_service.reconfigure(database_url='sqlite:///' + (tmp_path / 'auth.sqlite3').as_posix())
        admin = auth_service.register('recovery.admin', 'password123')
        auth_service.update_user_role(admin['id'], 'admin')
        headers = {'Authorization': 'Bearer ' + auth_service.create_token(admin['id'], admin['username'])['token']}
        monkeypatch.setattr(tasks_api, 'task_queue_service', queue)
        with TestClient(app) as client:
            response = client.get('/api/admin/tasks/' + task['task_id'], headers=headers)
            assert response.status_code == 200 and response.json()['status'] == 'failed'
            response = client.post('/api/admin/tasks/' + task['task_id'] + '/retry', headers=headers)
            assert response.status_code == 200 and response.json()['status'] == 'queued'
        new = queue.claim_next(['test'])
        assert new['lease_token'] != old_token
        assert not queue.heartbeat(task['task_id'], old_token)
        with pytest.raises(ActiveTaskConflict):
            queue.complete(task['task_id'], {'stale': True}, lease_token=old_token)
        queue.complete(task['task_id'], {'ok': True}, lease_token=new['lease_token'])
        assert queue.get_task(task['task_id'])['result'] == {'ok': True}
        print(f'recovery_elapsed_seconds={elapsed:.3f}')
    finally:
        if worker.poll() is None:
            worker.kill()
            worker.wait(timeout=10)


@pytest.mark.skipif(not os.environ.get('TEST_REDIS_URL'), reason='requires dedicated test Redis')
def test_default_lease_expiry_after_worker_killed():
    connection = redis.Redis.from_url(os.environ['TEST_REDIS_URL'])
    name = 'default-lease-' + uuid.uuid4().hex
    queue = TaskQueueService(redis_connection=connection, queue_name=name)
    task = queue.enqueue(task_type='test', payload={})
    signal = name + ':signal'
    root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env['PYTHONPATH'] = os.pathsep.join((str(root / 'backend'), str(root)))
    code = '''
import os, redis, sys, time
from app.services.task_queue_service import TaskQueueService
from app.services.task_worker import TaskWorker
c=redis.Redis.from_url(os.environ['TEST_REDIS_URL'])
q=TaskQueueService(redis_connection=c, queue_name=sys.argv[1])
def handler(payload):
    c.set(sys.argv[2], 'running')
    time.sleep(90)
    return {}
TaskWorker(q, handlers={'test': handler}).run_once()
'''
    worker = subprocess.Popen([sys.executable, '-c', code, name, signal], cwd=str(root), env=env)
    try:
        deadline = time.monotonic() + 15
        while not connection.get(signal) and time.monotonic() < deadline:
            assert worker.poll() is None
            time.sleep(.05)
        assert connection.get(signal)
        worker.kill()
        worker.wait(timeout=10)
        start = time.monotonic()
        while time.monotonic() - start < 35:
            state = queue.get_task(task['task_id'])
            if state['status'] == 'failed':
                break
            time.sleep(.1)
        elapsed = time.monotonic() - start
        assert state['status'] == 'failed'
        assert 27 <= elapsed <= 33
        print(f'default_recovery_elapsed_seconds={elapsed:.3f}')
    finally:
        if worker.poll() is None:
            worker.kill()
            worker.wait(timeout=10)


@pytest.mark.skipif(not os.environ.get('TEST_REDIS_URL'), reason='requires dedicated test Redis')
def test_healthy_worker_renews_lease_for_long_handler():
    from app.services.task_worker import TaskWorker
    import threading

    connection = redis.Redis.from_url(os.environ['TEST_REDIS_URL'])
    queue = TaskQueueService(redis_connection=connection, queue_name='healthy-' + uuid.uuid4().hex, lease_seconds=.9)
    task = queue.enqueue(task_type='test', payload={})
    started = threading.Event()
    def handler(payload):
        started.set()
        time.sleep(2.2)
        return {'finished': True}
    worker = threading.Thread(target=TaskWorker(queue, handlers={'test': handler}).run_once)
    worker.start()
    assert started.wait(5)
    try:
        time.sleep(1.4)
        assert queue.get_task(task['task_id'])['status'] == 'running'
    finally:
        worker.join(timeout=5)
    assert not worker.is_alive()
    assert queue.get_task(task['task_id'])['status'] == 'succeeded'


@pytest.mark.skipif(not os.environ.get('TEST_REDIS_URL'), reason='requires dedicated test Redis')
def test_legacy_records_and_competing_recovery():
    from rq.job import Job, JobStatus
    connection = redis.Redis.from_url(os.environ['TEST_REDIS_URL'])
    queue = TaskQueueService(redis_connection=connection, queue_name='legacy-' + uuid.uuid4().hex)
    lost = queue.enqueue(task_type='test', payload={})
    connection.lpop(queue.rq_queue.key)
    assert queue.get_task(lost['task_id'])['status'] == 'queued'
    assert queue.rq_queue.job_ids == [lost['task_id']]
    claimed = queue.claim_next()
    connection.zrem(queue._leases_key, claimed['task_id'])
    with ThreadPoolExecutor(max_workers=4) as pool:
        recovered = list(pool.map(lambda _: queue._recover_task(claimed['task_id']), range(4)))
    assert sum(recovered) == 1
    assert queue.get_task(claimed['task_id'])['status'] == 'failed'
    assert Job.fetch(claimed['task_id'], connection=connection).get_status() == JobStatus.FAILED
    assert queue.retry(claimed['task_id'])['status'] == 'queued'
