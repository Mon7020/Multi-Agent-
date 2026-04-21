# P2 Vector Access Metadata Report

## Scope

- Added vector-store-safe access metadata normalization with scalar fields.
- Added registry lookup by source path or filename for vector access metadata.
- Added ingestion-time metadata merge in `RAGTool.add_documents_to_vector_db()`.
- Kept existing application-layer role filtering as the enforcement source of truth.

## Metadata Fields

- `tenant_id`
- `access_managed`
- `access_document_id`
- `access_published`
- `access_visible_to_frontend`
- `access_deleted`
- `access_role_user`
- `access_role_operator`
- `access_role_admin`
- `access_role_super_admin`

## Behavior

- Known registry records produce scalar metadata that Chroma can filter exactly.
- Unknown or failed registry lookups produce `access_managed=False` and all access booleans false.
- Tenant metadata is preserved from document metadata when present, otherwise `default` is used.
- This phase prepares vector-level ACL filtering but does not remove the existing registry-based post-filter.

## Verification

- `D:\agentlearn\miniconda\envs\test3\python.exe -m pytest tests/admin/test_p2_vector_store_backend.py tests/admin/test_knowledge_admin_registry.py::KnowledgeAdminRegistryTest::test_vector_access_metadata_for_source_uses_registry_record -q`
  - Result: 9 passed, 9 warnings.
- `D:\agentlearn\miniconda\envs\test3\python.exe -m py_compile tools/rag/vector_store_backend.py tools/rag/chroma_backend.py tools/rag_tool.py backend/app/services/knowledge_admin_service.py`
  - Result: passed.
- `D:\agentlearn\miniconda\envs\test3\python.exe -m pytest tests/admin/test_p1_agent_hardening.py tests/admin/test_p0_rag_security_trace.py -q`
  - Result: 12 passed, 10 warnings.
- `D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_visibility tests.admin.test_knowledge_admin_registry -v`
  - Result: 11 passed.

## Residual Risks

- Existing vector rows need rebuild or reload before they contain the new access metadata fields.
- Query-time role filters are not yet built from these fields.
- Chroma telemetry and dependency deprecation warnings remain outside this change.
