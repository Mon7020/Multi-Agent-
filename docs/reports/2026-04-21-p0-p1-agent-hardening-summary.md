# P0/P1 Agent Hardening Summary

Date: 2026-04-21
Environment: `D:\agentlearn\miniconda\envs\test3\python.exe`

## Purpose

This document is the handoff summary for the current P0/P1 work. It groups the changed files by concern so the next step can be a clean commit, review, or rollback decision.

## P0 Scope

P0 hardened the existing RAG and trace path without changing the main orchestration shape.

- RAG cache keys now include retrieval policy dimensions:
  - `user_role`
  - `tenant_id`
  - `knowledge_version`
  - `enable_hybrid`
  - `enable_rerank`
- RAG documents are filtered by frontend access policy:
  - `published`
  - `visible_to_frontend`
  - `allowed_roles`
- `trace_id` is propagated through:
  - `ChatServiceV3`
  - `SessionContext`
  - `SupervisorAgent`
  - `RAGTool`
- Chat responses expose `trace_id`.

## P1 Scope

P1 upgraded the system from a linear Supervisor flow toward an observable state graph.

- Added explicit state graph:
  - `intent`
  - `plan`
  - `retrieve`
  - `execute`
  - `verify`
  - `replan`
  - `final`
- Added node execution policy:
  - timeout
  - retry
  - fallback
  - node status
  - node timing
  - per-attempt error history
- Promoted RAG retrieval into a first-class graph node for `general` intent.
- Reused prefetched RAG results in the execute node to avoid duplicate retrieval.
- Added low-quality RAG fallback planning:
  - rewrite query
  - increased retry `top_k`
  - clarification fallback
- Added replan retry:
  - first tries `rag_fallback.rewrite_query`
  - uses successful retry documents as `general_replan`
  - falls back to clarification only when retry still has no documents
- Extended long-term memory metadata:
  - `importance`
  - `ttl_seconds`
  - `expires_at`
  - `consent`

## Changed Files

### New Files

- `agents/agent_state_graph.py`
- `tools/rag/cache_policy.py`
- `tools/rag/fallback_policy.py`
- `tests/admin/test_p0_rag_security_trace.py`
- `tests/admin/test_p1_agent_hardening.py`
- `docs/reports/2026-04-21-p0-agent-hardening-test-report.md`
- `docs/reports/2026-04-21-p1-agent-hardening-test-report.md`
- `docs/reports/2026-04-21-p0-p1-agent-hardening-summary.md`

### Modified Files

- `agents/supervisor_agent.py`
- `backend/app/schemas.py`
- `backend/app/services/chat_service_v3.py`
- `backend/app/services/knowledge_admin_service.py`
- `core/session_context.py`
- `tools/rag/context_engineering.py`
- `tools/rag_tool.py`

## Verification Commands

The latest verification set was run in `test3`.

```text
D:\agentlearn\miniconda\envs\test3\python.exe -m pytest tests/admin/test_p1_agent_hardening.py -q
9 passed, 10 warnings
```

```text
D:\agentlearn\miniconda\envs\test3\python.exe -m pytest tests/admin/test_p0_rag_security_trace.py -q
3 passed, 10 warnings
```

```text
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_visibility -v
Ran 6 tests
OK
```

```text
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_settings_admin_service -v
Ran 4 tests
OK
```

```text
D:\agentlearn\miniconda\envs\test3\python.exe -m py_compile agents\agent_state_graph.py agents\supervisor_agent.py backend\app\services\chat_service_v3.py backend\app\schemas.py tools\rag\fallback_policy.py tools\rag\context_engineering.py
exit code 0
```

## Known Risk

- `tests/test_session_context.py` still has an existing isolation issue because it uses fixed session data and can restore old persisted state from `data/memory/session_context`. This was not introduced by P0/P1.
- `retrieve` is first-class for `general` intent. Sales, tech support, and negotiation still rely on their existing skill/tool paths.
- The state graph is still in-process. It is not yet a distributed scheduler, checkpoint store, or resumable workflow engine.

## Suggested Commit Boundary

Recommended single commit:

```text
feat: harden agent rag security and state graph orchestration
```

Reason: P0 and P1 are coupled now because `trace_id`, retrieval policy, RAG filtering, state graph retrieval, fallback, and response schemas touch the same runtime path.

Alternative split if stricter review is needed:

1. `feat: harden rag cache policy and access filtering`
2. `feat: add observable supervisor state graph`

The split is possible but requires careful staging because `chat_service_v3.py`, `supervisor_agent.py`, and tests contain changes from both phases.

## Recommended Next Step

Before starting P2, do one of:

- Commit the current P0/P1 work as one feature commit.
- Create a PR/review checkpoint.
- Run a broader backend smoke test if the project has an agreed command for it.

P2 should start only after this work is anchored, because P2 will touch storage and deployment assumptions: vector DB abstraction, Redis/DB session state, model routing, and load testing.
