# P1 Agent Hardening Test Report

Date: 2026-04-21
Environment: `D:\agentlearn\miniconda\envs\test3\python.exe`

## Scope

This P1 slice implements the next hardening layer after P0:

- Explicit Supervisor state graph: `intent -> plan -> retrieve -> execute -> verify -> replan -> final`
- Node-level execution policy with timeout, retry, and fallback metadata
- Node-level observability metadata: `started_at`, `ended_at`, `duration_ms`, and retry error history
- First-class RAG retrieval node with prefetch metadata and execute-node reuse
- Replan retry path that uses `rag_fallback.rewrite_query` before clarification fallback
- Low-quality RAG fallback decision for rewrite + clarification
- Long-term memory metadata for `confidence`, `importance`, `ttl_seconds`, `expires_at`, and `consent`
- API response exposure for `rag_fallback`

## Changed Areas

- `agents/agent_state_graph.py`
  - Added lightweight async graph executor and graph state object.
  - Node status records `success`, `fallback`, attempt count, and error type.
  - Node status now includes timing fields and per-attempt error history for debugging.
  - Graph state now carries `retrieval_result` and `rag_fallback`.

- `agents/supervisor_agent.py`
  - Replaced the linear `classify -> route -> integrate` main flow with an explicit state graph.
  - `retrieve` now calls RAG for `general` intent and stores `prefetched_rag_result`.
  - `execute` reuses prefetched RAG documents, avoiding duplicate retrieval in the general branch.
  - `verify` treats low-quality RAG fallback or missing business success as a replan trigger.
  - `replan` now retries retrieval with the fallback rewrite query, and only falls back to clarification when retry retrieval still has no documents.
  - Returns graph definition, node status, plan, and graph metadata in `agent_graph`.

- `tools/rag/fallback_policy.py`
  - Added deterministic fallback planning for empty or low-quality retrieval.

- `backend/app/services/chat_service_v3.py`
  - Stores RAG fallback decision in context metadata and response payload.

- `backend/app/schemas.py`
  - Added `rag_fallback` to `ChatResponse`.

- `tools/rag/context_engineering.py`
  - Extended long-term preference updates with importance, TTL, expiry, and consent.
  - Skips persistence when consent is explicitly false and records `missing_consent`.

## Verification

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

## Notes

The `retrieve` graph node is now a first-class retrieval step for `general` intent. Non-general intents still skip prefetch because sales, support, and negotiation skills own their own tool usage paths today.

Warnings are existing Pydantic and LangChain deprecation warnings.
