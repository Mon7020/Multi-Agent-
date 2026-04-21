# P0 Agent Hardening Test Report

Date: 2026-04-21

Scope: P0 hardening based on the interview gap analysis. The implementation keeps P1/P2 extension points open by passing an explicit retrieval policy and trace id through the chat/RAG path.

## Changes Verified

1. Retrieval cache isolation
   - Added `tools/rag/cache_policy.py`.
   - Cache keys now include normalized retrieval policy fields: `user_role`, `tenant_id`, `knowledge_version`, `enable_hybrid`, `enable_rerank`.
   - `LocalCache`, `RedisCache`, and `RAGTool.retrieve()` accept `retrieval_policy`.

2. Chat RAG permission filtering
   - Added `KnowledgeAdminService.filter_retrieved_documents_for_role()`.
   - ChatService filters RAG documents by `published`, `visible_to_frontend`, and `allowed_roles`.
   - Unknown or hidden sources are removed from chat retrieval results.

3. Trace id propagation
   - `ChatServiceV3.process_message()` generates a request-level `trace_id`.
   - `SessionContext.add_turn()` records trace id on each turn and includes it in summaries.
   - `SupervisorAgent.process()` and `RAGTool.retrieve()` accept and return trace id.

4. P1/P2 compatibility
   - `retrieval_policy` is stored on session metadata, so future StateGraph nodes can reuse it without recomputing policy.
   - `tenant_id` and `knowledge_version` are already part of the cache key for future multi-tenant/vector-store migration.

## Verification Commands

All commands were run with the `test3` Python environment:

```powershell
D:\agentlearn\miniconda\envs\test3\python.exe -m pytest tests/admin/test_p0_rag_security_trace.py -q
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_visibility -v
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_settings_admin_service -v
D:\agentlearn\miniconda\envs\test3\python.exe -m py_compile core\session_context.py agents\supervisor_agent.py backend\app\services\chat_service_v3.py backend\app\services\knowledge_admin_service.py backend\app\schemas.py tools\rag_tool.py tools\rag\cache_policy.py
```

## Results

| Check | Result |
| --- | --- |
| `tests/admin/test_p0_rag_security_trace.py` | 3 passed |
| `tests.admin.test_knowledge_visibility` | 6 passed |
| `tests.admin.test_settings_admin_service` | 4 passed |
| `py_compile` targeted files | passed |

Warnings observed are existing dependency deprecation warnings from Pydantic/LangChain and do not block this P0 change.

## Known Test Isolation Issue

`D:\agentlearn\miniconda\envs\test3\python.exe -m pytest tests/test_session_context.py -q` currently fails when `data/memory/session_context/test_001_context.json` already exists, because that test uses a fixed `session_id="test_001"` and `SessionContext` restores persisted state by design.

Root cause: test fixture state is not isolated from the real persisted session directory.

I did not delete the persisted file during verification. Recommended fix for a separate cleanup pass: make `tests/test_session_context.py` use a unique `user_id/session_id` per test or inject a temporary session storage path.
