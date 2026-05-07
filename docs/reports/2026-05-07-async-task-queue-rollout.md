# Async Task Queue Rollout

## Scope

Added an in-process task queue boundary for slow knowledge work. Chat remains synchronous. User-facing answer generation is not queued.

## Queued Operations

Knowledge reload and document indexing can be represented as task records. API callers receive a `task_id` and poll task status from the admin task endpoints.

## Worker

Run one worker pass:

```powershell
D:\agentlearn\miniconda\envs\test3\python.exe backend\scripts\run_task_worker.py --once
```

Run continuously by omitting `--once`.

## Retry Behavior

Tasks retry up to `max_attempts`. Permanent failures move to `dead`; admins can move dead tasks back to `queued` with the retry endpoint.

## Follow-Ups

- Persist task records in SQL instead of process memory.
- Add Redis/Celery adapter behind the same queue interface.
- Add task metrics to the admin dashboard.
