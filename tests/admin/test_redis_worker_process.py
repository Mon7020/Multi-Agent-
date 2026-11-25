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
