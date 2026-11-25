from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import redis
from redis.client import Pipeline
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job, JobStatus

from app.config import settings


TASK_STATUSES = {"queued", "running", "succeeded", "failed", "dead"}
DEFAULT_QUEUE_NAME = "knowledge-tasks"
DISPATCHER_PATH = "app.services.task_dispatcher.dispatch_task"
LEASE_SECONDS = 30


def _now() -> str:
    return datetime.now().isoformat()


def _decode(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


class ActiveTaskConflict(ValueError):
    """Another active task already owns the requested idempotency key."""


class TaskQueueService:
    """Redis/RQ-backed task queue with the app's existing task API shape."""

    def __init__(
        self,
        *,
        redis_connection: Optional[redis.Redis] = None,
        queue_name: str = DEFAULT_QUEUE_NAME,
        lease_seconds: float = LEASE_SECONDS,
    ) -> None:
        self.connection = redis_connection or self._create_redis_connection()
        self.queue_name = queue_name
        self.rq_queue = Queue(queue_name, connection=self.connection)
        self._task_ids_key = f"task_queue:{queue_name}:task_ids"
        self._idempotency_key = f"task_queue:{queue_name}:idempotency"
        self._leases_key = f"task_queue:{queue_name}:leases"
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        self.lease_seconds = lease_seconds

    def _time(self) -> float:
        seconds, micros = self.connection.time()
        return seconds + micros / 1_000_000

    @staticmethod
    def _create_redis_connection() -> redis.Redis:
        return redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
        )

    def enqueue(
        self,
        *,
        task_type: str,
        payload: Dict[str, Any],
        actor_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        max_attempts: int = 3,
    ) -> Dict[str, Any]:
        task_id = f"task_{uuid4().hex}"
        now = _now()
        task = {
            "task_id": task_id,
            "task_type": task_type,
            "payload": dict(payload or {}),
            "actor_id": actor_id,
            "idempotency_key": idempotency_key,
            "status": "queued",
            "attempts": 0,
            "max_attempts": int(max_attempts),
            "error": None,
            "result": None,
            "created_at": now,
            "updated_at": now,
            "started_at": None,
            "finished_at": None,
        }

        with self.connection.pipeline() as pipe:
            while True:
                try:
                    if idempotency_key:
                        existing = self._watch_active_task(pipe, idempotency_key)
                        if existing:
                            return existing
                    # RQ 2.1 calls MULTI on the supplied pipeline for this
                    # dependency-free job. The queue and both indexes commit together.
                    self.rq_queue.enqueue_call(
                        func=DISPATCHER_PATH,
                        args=(task_type, task["payload"]),
                        job_id=task_id,
                        meta={"task": task},
                        pipeline=pipe,
                    )
                    pipe.rpush(self._task_ids_key, task_id)
                    if idempotency_key:
                        pipe.hset(self._idempotency_key, idempotency_key, task_id)
                    pipe.execute()
                    return dict(task)
                except redis.WatchError:
                    continue

    def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        task_ids = [_decode(item) for item in self.connection.lrange(self._task_ids_key, 0, -1)]
        tasks: List[Dict[str, Any]] = []
        for task_id in task_ids:
            task = self.get_task(task_id)
            if not task:
                continue
            if status and task["status"] != status:
                continue
            tasks.append(task)
        return tasks

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        self._recover_task(task_id)
        job = self._fetch_job(task_id)
        if not job:
            return None
        task = self._task_from_job(job)
        task.pop("lease_token", None)
        return task

    def claim_next(self, task_types: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        self.recover_expired()
        allowed = set(task_types or [])
        with self.connection.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(self.rq_queue.key)
                    ids = pipe.lrange(self.rq_queue.key, 0, -1)
                    selected = None
                    for raw_id in ids:
                        task_id = _decode(raw_id)
                        pipe.watch(Job.key_for(task_id))
                        job = self._fetch_job(task_id)
                        if not job:
                            continue
                        task = self._task_from_job(job)
                        if task.get("status") == "queued" and (not allowed or task["task_type"] in allowed):
                            selected = (task_id, job, task)
                            break
                    if selected is None:
                        return None
                    task_id, job, task = selected
                    now = _now()
                    task.update(status="running", attempts=task["attempts"] + 1,
                                started_at=now, finished_at=None, updated_at=now,
                                lease_token=uuid4().hex)
                    pipe.multi()
                    pipe.lrem(self.rq_queue.key, 1, task_id)
                    pipe.zadd(self._leases_key, {task_id: self._time() + self.lease_seconds})
                    self._save_task(job, task, JobStatus.STARTED, pipeline=pipe)
                    pipe.execute()
                    return dict(task)
                except redis.WatchError:
                    continue

    def _recover_task(self, task_id: str) -> bool:
        with self.connection.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(Job.key_for(task_id), self._leases_key, self.rq_queue.key)
                    job = self._fetch_job(task_id)
                    if not job:
                        return False
                    task = self._task_from_job(job)
                    if task.get("status") == "queued":
                        if any(_decode(item) == task_id for item in pipe.lrange(self.rq_queue.key, 0, -1)):
                            return False
                        # Repair the old worker's pop-before-registration gap.
                        pipe.multi()
                        pipe.rpush(self.rq_queue.key, task_id)
                        pipe.execute()
                        return True
                    if task.get("status") != "running":
                        return False
                    expiry = pipe.zscore(self._leases_key, task_id)
                    if expiry is not None and expiry > self._time():
                        return False
                    now = _now()
                    task.update(status="failed", error="worker lease expired or legacy running task; verify side effects before retry", finished_at=now, updated_at=now)
                    task.pop("lease_token", None)
                    pipe.multi()
                    pipe.zrem(self._leases_key, task_id)
                    self._save_task(job, task, JobStatus.FAILED, pipeline=pipe)
                    pipe.execute()
                    return True
                except redis.WatchError:
                    continue

    def recover_expired(self) -> int:
        # Also inspect pre-upgrade running records, which have no lease.
        return sum(self._recover_task(_decode(task_id)) for task_id in self.connection.lrange(self._task_ids_key, 0, -1))

    def heartbeat(self, task_id: str, lease_token: str) -> bool:
        with self.connection.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(Job.key_for(task_id), self._leases_key)
                    job = self._fetch_job(task_id)
                    if not job:
                        return False
                    task = self._task_from_job(job)
                    expiry = pipe.zscore(self._leases_key, task_id)
                    if task.get("status") != "running" or task.get("lease_token") != lease_token or expiry is None or expiry <= self._time():
                        return False
                    pipe.multi()
                    pipe.zadd(self._leases_key, {task_id: self._time() + self.lease_seconds})
                    pipe.execute()
                    return True
                except redis.WatchError:
                    continue

    def complete(self, task_id: str, result: Optional[Dict[str, Any]] = None, *, lease_token: Optional[str] = None) -> Dict[str, Any]:
        return self._finish(task_id, lease_token, result=result)

    def fail(self, task_id: str, error: str, *, lease_token: Optional[str] = None) -> Dict[str, Any]:
        return self._finish(task_id, lease_token, error=str(error))

    def _finish(self, task_id: str, lease_token: Optional[str], *, result=None, error=None) -> Dict[str, Any]:
        with self.connection.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(Job.key_for(task_id), self._leases_key)
                    job = Job.fetch(task_id, connection=self.connection)
                    task = self._task_from_job(job)
                    expiry = pipe.zscore(self._leases_key, task_id)
                    if (not lease_token or task.get("lease_token") != lease_token or task.get("status") != "running"
                            or expiry is None or expiry <= self._time()):
                        raise ActiveTaskConflict("task lease is no longer owned by this execution")
                    now = _now()
                    task.update(finished_at=now, updated_at=now, error=error)
                    task.pop("lease_token", None)
                    if error is None:
                        task.update(status="succeeded", result=dict(result or {}))
                        status = JobStatus.FINISHED
                    elif task["attempts"] >= task["max_attempts"]:
                        task["status"] = "dead"
                        status = JobStatus.FAILED
                    else:
                        task["status"] = "queued"
                        status = JobStatus.QUEUED
                    pipe.multi()
                    pipe.zrem(self._leases_key, task_id)
                    self._save_task(job, task, status, pipeline=pipe)
                    if status == JobStatus.QUEUED:
                        self.rq_queue.push_job_id(task_id, pipeline=pipe)
                    pipe.execute()
                    return dict(task)
                except redis.WatchError:
                    continue

    def retry(self, task_id: str) -> Dict[str, Any]:
        with self.connection.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(Job.key_for(task_id))
                    job = Job.fetch(task_id, connection=self.connection)
                    task = self._task_from_job(job)
                    if task["status"] not in {"failed", "dead"}:
                        return task
                    key = task.get("idempotency_key")
                    if key:
                        active = self._watch_active_task(pipe, key)
                        if active and active["task_id"] != task_id:
                            raise ActiveTaskConflict(f"task {active['task_id']} is already active")
                    task.update(status="queued", error=None, finished_at=None, updated_at=_now())
                    pipe.multi()
                    self._save_task(job, task, JobStatus.QUEUED, pipeline=pipe)
                    self.rq_queue.push_job_id(task_id, pipeline=pipe)
                    if key:
                        pipe.hset(self._idempotency_key, key, task_id)
                    pipe.execute()
                    return task
                except redis.WatchError:
                    continue

    def _watch_active_task(self, pipe: Pipeline, key: str) -> Optional[Dict[str, Any]]:
        pipe.watch(self._idempotency_key)
        owner = pipe.hget(self._idempotency_key, key)
        if not owner:
            return None
        task_id = _decode(owner)
        pipe.watch(Job.key_for(task_id))
        task = self.get_task(task_id)
        if task and task["status"] in {"queued", "running"}:
            return task
        return None

    def _fetch_job(self, task_id: str) -> Optional[Job]:
        try:
            return Job.fetch(task_id, connection=self.connection)
        except NoSuchJobError:
            return None

    @staticmethod
    def _task_from_job(job: Job) -> Dict[str, Any]:
        task = dict(job.meta.get("task") or {})
        if not task:
            raise KeyError(f"job {job.id} does not contain task metadata")
        return task

    @staticmethod
    def _save_task(
        job: Job, task: Dict[str, Any], status: JobStatus, *, pipeline: Optional[Pipeline] = None,
    ) -> None:
        job.meta["task"] = dict(task)
        job.set_status(status, pipeline=pipeline)
        job.save(include_meta=True, include_result=False, pipeline=pipeline)


task_queue_service = TaskQueueService()
