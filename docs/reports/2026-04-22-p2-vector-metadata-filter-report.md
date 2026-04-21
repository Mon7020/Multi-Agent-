# P2 Vector Metadata Filter Report

## Scope

- Added `build_vector_metadata_filter()` for safe retrieval-policy-to-vector-filter conversion.
- Added `metadata_matches_filter()` so hybrid BM25 uses the same metadata constraints as vector search.
- Wired `RAGTool.retrieve()` to pass vector metadata filters into `_vector_search()`.
- Passed filters through `VectorSearchRequest` into the Chroma adapter.

## Behavior

- Non-default `tenant_id` is pushed down as an exact Chroma metadata filter.
- Optional `vector_metadata_filter` values are accepted only when they are scalar Chroma-safe values.
- Default tenant does not create a filter, preserving compatibility with existing documents that do not carry tenant metadata.
- BM25 indexing and BM25 result conversion skip documents that do not match the same metadata filter.

## Verification

- `D:\agentlearn\miniconda\envs\test3\python.exe -m pytest tests/admin/test_p2_vector_store_backend.py -q`
  - Result: 6 passed.
- `D:\agentlearn\miniconda\envs\test3\python.exe -m py_compile tools/rag/vector_store_backend.py tools/rag/chroma_backend.py tools/rag_tool.py`
  - Result: passed.
- `D:\agentlearn\miniconda\envs\test3\python.exe -m pytest tests/admin/test_p1_agent_hardening.py tests/admin/test_p0_rag_security_trace.py -q`
  - Result: 12 passed, 10 warnings.
- `D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_visibility -v`
  - Result: 6 passed.

## Residual Risks

- Role ACL is still enforced by the existing application-layer registry filter.
- Existing vector documents may not contain tenant metadata, so default-tenant behavior intentionally remains unfiltered.
- Full vector-store-level role filtering requires ingestion-time access metadata normalization, which remains separate P2 work.
- Existing pytest-asyncio, Pydantic, and LangChain deprecation warnings remain outside this change.
