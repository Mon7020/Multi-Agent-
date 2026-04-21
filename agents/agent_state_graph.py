"""Lightweight explicit state graph for Agent orchestration."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from time import perf_counter
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple


@dataclass
class AgentGraphState:
    query: str
    context: Any = None
    trace_id: Optional[str] = None
    intent: Optional[str] = None
    confidence: float = 0.0
    plan: Dict[str, Any] = field(default_factory=dict)
    retrieval_result: Dict[str, Any] = field(default_factory=dict)
    rag_fallback: Dict[str, Any] = field(default_factory=dict)
    routing_results: List[Tuple[str, Any]] = field(default_factory=list)
    final_response: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    node_status: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    needs_replan: bool = False


NodeHandler = Callable[[AgentGraphState], Awaitable[AgentGraphState]]
FallbackHandler = Callable[[AgentGraphState, Exception], Awaitable[AgentGraphState]]


@dataclass
class NodeExecutionPolicy:
    timeout_seconds: Optional[float] = 20.0
    retries: int = 0
    fallback: Optional[FallbackHandler] = None


class StateGraphExecutor:
    """Execute named async nodes with timeout, retry, and fallback metadata."""

    def __init__(self) -> None:
        self._nodes: List[Tuple[str, NodeHandler, NodeExecutionPolicy]] = []

    def add_node(
        self,
        name: str,
        handler: NodeHandler,
        policy: Optional[NodeExecutionPolicy] = None,
    ) -> None:
        self._nodes.append((name, handler, policy or NodeExecutionPolicy()))

    def definition(self) -> List[str]:
        return [name for name, _, _ in self._nodes]

    async def run(self, state: AgentGraphState) -> AgentGraphState:
        for name, handler, policy in self._nodes:
            state = await self._run_node(name, handler, policy, state)
        return state

    async def _run_node(
        self,
        name: str,
        handler: NodeHandler,
        policy: NodeExecutionPolicy,
        state: AgentGraphState,
    ) -> AgentGraphState:
        attempts = 0
        last_error: Optional[Exception] = None
        started_at = datetime.now().isoformat()
        started_perf = perf_counter()
        errors: List[Dict[str, Any]] = []

        for _ in range(policy.retries + 1):
            attempts += 1
            try:
                if policy.timeout_seconds is None:
                    state = await handler(state)
                else:
                    state = await asyncio.wait_for(handler(state), timeout=policy.timeout_seconds)
                state.node_status[name] = self._build_status(
                    status="success",
                    attempts=attempts,
                    started_at=started_at,
                    started_perf=started_perf,
                    errors=errors,
                )
                return state
            except Exception as error:
                last_error = error
                errors.append(
                    {
                        "attempt": attempts,
                        "type": type(error).__name__,
                        "message": str(error),
                    }
                )

        if policy.fallback and last_error is not None:
            state = await policy.fallback(state, last_error)
            state.node_status[name] = self._build_status(
                status="fallback",
                attempts=attempts,
                started_at=started_at,
                started_perf=started_perf,
                errors=errors,
                error=type(last_error).__name__,
            )
            return state

        if last_error is not None:
            state.node_status[name] = self._build_status(
                status="failed",
                attempts=attempts,
                started_at=started_at,
                started_perf=started_perf,
                errors=errors,
                error=type(last_error).__name__,
            )
            raise last_error

        return state

    def _build_status(
        self,
        *,
        status: str,
        attempts: int,
        started_at: str,
        started_perf: float,
        errors: List[Dict[str, Any]],
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        ended_at = datetime.now().isoformat()
        node_status: Dict[str, Any] = {
            "status": status,
            "attempts": attempts,
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_ms": round((perf_counter() - started_perf) * 1000, 3),
            "errors": errors,
        }
        if error:
            node_status["error"] = error
        return node_status
