# P3 API Reload Smoke Report

Date: 2026-04-22

Environment:
- Python: `D:\agentlearn\miniconda\envs\test3\python.exe`
- API layer: FastAPI `TestClient` with the real `/api/v1/auth` and `/api/v1/knowledge-base` routers
- Vector store: real local Chroma store
- Auth store: real configured auth database

## Scope

This smoke test validates the existing API layer for knowledge-base reload and frontend role visibility:
- `POST /api/v1/knowledge-base/reload`
- `GET /api/v1/knowledge-base`

The smoke used a temporary document:
- Document id: `doc_064b101491264cdca191235f6d38a1c5`
- Source file: `data\docs\p3_api_operator_only_smoke.txt`
- Allowed roles: `operator`, `admin`, `super_admin`

## Fixes Required

The first API smoke attempt failed with `500 {"detail": "failed to rebuild vector collection"}`.

Root causes:
- `rag_runtime.get_rag_tool()` created a second `RAGTool` even though `tools.rag_tool` already creates a module-level `rag_tool`.
- `knowledge_admin_service._get_vector_collection()` opened the same Chroma path with default settings, while `RAGTool` opens it with `anonymized_telemetry=False`.

Changes made:
- `rag_runtime.get_rag_tool()` now reuses the module-level `tools.rag_tool.rag_tool`.
- `knowledge_admin_service._get_vector_collection()` now uses the same Chroma setting shape as `RAGTool`.

Regression tests added:
- `tests/admin/test_rag_runtime_singleton.py`
- `KnowledgeAdminRegistryTest.test_persistent_vector_store_fallback_uses_rag_chroma_settings`

## Successful Smoke Results

Restricted reload response:
- `success: true`
- `total_chunks: 76`
- `verified_chunks: 76`
- `access_metadata_rebuilt: true`
- `access_policy_version: bd8f92e3277ed3b7`
- `params_used: {"chunk_size": 400, "chunk_overlap": 50}`

Role list results:

| Role | API total | Temporary document visible |
| --- | ---: | --- |
| `user` | 5 | false |
| `operator` | 6 | true |
| `admin` | 6 | true |
| `super_admin` | 6 | true |

Restricted vector metadata:
- Matching temporary chunks: 1
- `access_managed: true`
- `access_published: true`
- `access_visible_to_frontend: true`
- `access_role_user: false`
- `access_role_operator: true`
- `access_role_admin: true`
- `access_role_super_admin: true`

## Cleanup

The smoke restored the original registry bytes, deleted the temporary source file, and reloaded through the same API endpoint.

Restore reload response:
- `success: true`
- `total_chunks: 75`
- `verified_chunks: 75`
- `access_metadata_rebuilt: true`
- `access_policy_version: 365100730b951a26`
- `temp_exists_after_restore: false`

Post-smoke direct Chroma inspection:
- `count: 75`
- `with_access: 75`
- `temp_present: false`

Note: the previous persisted vector store had 65 chunks. A real API reload with the current runtime parameters rebuilds the same source documents into 75 chunks, so the restored vector store now reflects the current reload behavior rather than the older persisted index.

## Remaining Noise

The smoke still prints Chroma telemetry warnings. On the GBK PowerShell console, Loguru also reports encoding errors for checkmark characters in several `tools/rag_tool.py` log messages. These did not fail the API smoke, but they are good P3 cleanup candidates.
