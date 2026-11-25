from __future__ import annotations

from typing import Any, Dict


def dispatch_task(task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.task_handlers import TASK_HANDLERS

    handler = TASK_HANDLERS.get(task_type)
    if handler is None:
        raise ValueError(f"no handler for {task_type}")
    return handler(payload)
