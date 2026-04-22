# P2 Vector Role Filter Report

## Scope

- Added role-derived vector metadata filters for known frontend roles.
- Kept tenant and explicit metadata filters working with the role ACL filters.
- Preserved application-layer registry filtering as a second enforcement layer.

## Query-Time Filter

For a known `user_role`, `build_vector_metadata_filter()` now adds:

- `access_managed=True`
- `access_published=True`
- `access_visible_to_frontend=True`
- `access_deleted=False`
- `access_role_<role>=True`

Unknown roles do not produce role ACL filters.

## Verification

- `D:\agentlearn\miniconda\envs\test3\python.exe -m pytest tests/admin/test_p2_vector_store_backend.py -q`
  - Result: 10 passed.
- `D:\agentlearn\miniconda\envs\test3\python.exe -m py_compile tools/rag/vector_store_backend.py tools/rag_tool.py`
  - Result: passed.
- `D:\agentlearn\miniconda\envs\test3\python.exe -m pytest tests/admin/test_p1_agent_hardening.py tests/admin/test_p0_rag_security_trace.py -q`
  - Result: 12 passed, 10 warnings.
- `D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_visibility tests.admin.test_knowledge_admin_registry -v`
  - Result: 11 passed.

## Residual Risks

- Existing vector rows still need rebuild or reload before they contain `access_*` metadata.
- Unknown roles rely on application-layer filtering only.
- Existing dependency warnings and Chroma telemetry noise remain outside this change.
