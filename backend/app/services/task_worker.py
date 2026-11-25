from __future__ import annotations

import time
import threading
from typing import Callable, Dict, Optional

from app.services.task_queue_service import TaskQueueService, task_queue_service


TaskHandler = Callable[[dict], dict]


class TaskWorker:
    def __init__(
        self,
        queue: TaskQueueService = task_queue_service,
        handlers: Optional[Dict[str, TaskHandler]] = None,
    ) -> None:
        self.queue = queue
        self.handlers = handlers or {}

    def run_once(self) -> bool:
        task = self.queue.claim_next(task_types=list(self.handlers.keys()))
        if task is None:
            return False

        handler = self.handlers.get(task["task_type"])
        token = task["lease_token"]
        if handler is None:
            self.queue.fail(task["task_id"], f"no handler for {task['task_type']}", lease_token=token)
            return True

        stopped = threading.Event()
        def heartbeat():
            while not stopped.wait(min(5.0, self.queue.lease_seconds / 3)):
                try:
                    if not self.queue.heartbeat(task["task_id"], token):
                        return
                except Exception:
                    # Do not extend locally when Redis is unavailable.
                    continue
        thread = threading.Thread(target=heartbeat, daemon=True)
        thread.start()
        try:
            result = handler(task["payload"])
            self.queue.complete(task["task_id"], result=result, lease_token=token)
        except Exception as exc:
            from app.services.task_queue_service import ActiveTaskConflict
            if not isinstance(exc, ActiveTaskConflict):
                try:
                    self.queue.fail(task["task_id"], str(exc), lease_token=token)
                except ActiveTaskConflict:
                    pass
        finally:
            stopped.set()
            thread.join()
        return True

    def run_forever(self, *, idle_sleep_seconds: float = 1.0) -> None:
        while True:
            did_work = self.run_once()
            if not did_work:
                time.sleep(idle_sleep_seconds)
