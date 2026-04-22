# P2 Vector Access Reload Report

## Scope

- Confirmed the existing knowledge-base reload path clears and rebuilds the vector collection.
- Added reload response fields that expose access metadata rebuild status.
- Added the current access policy version to the reload response.

## Behavior

`POST /api/v1/knowledge-base/reload` now returns:

- `access_metadata_rebuilt=True`
- `access_policy_version=<registry policy hash>`

Because reload calls `load_document()` and `add_documents_to_vector_db()` for each supported document, rebuilt chunks receive the P2-C `access_*` metadata.

## Verification

- `D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_base_reload_api -v`
  - Result: 1 passed.
- `D:\agentlearn\miniconda\envs\test3\python.exe -m py_compile backend/app/api/v1/knowledge_base.py tools/rag/vector_store_backend.py tools/rag_tool.py`
  - Result: passed.

## Residual Risks

- Operators still need to call reload after deploying P2-C/P2-D for existing chunks to receive access metadata.
- This phase does not add a background migration job.
- Chroma telemetry noise remains outside this change.
