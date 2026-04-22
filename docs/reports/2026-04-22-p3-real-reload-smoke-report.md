# P3 Real Reload Smoke Report

## Scope

- Ran a real Chroma reload against `data/docs` in the `test3` environment.
- Verified rebuilt chunks contain the P2 `access_*` metadata.
- Ran role-based RAG smoke retrieval for `user`, `operator`, `admin`, and `super_admin`.
- Fixed Chroma multi-field metadata filters by wrapping them in `$and`.

## Reload Result

- Before reload: 75 chunks.
- Before reload with `access_*` metadata: 0 chunks.
- Loaded files:
  - `产品手册_v1.0.pdf`: 2 chunks.
  - `常见问题_FAQ.txt`: 2 chunks.
  - `招呼消息.txt`: 1 chunk.
  - `用户指南_2024.docx`: 42 chunks.
  - `电子商品价格表.txt`: 18 chunks.
- After reload: 65 verified chunks.
- Chunks missing access metadata: 0.
- Access policy version: `365100730b951a26`.

## Role Smoke

Query: `保修 售后 常见问题`

- `user`: 3 docs from `常见问题_FAQ.txt`, `用户指南_2024.docx`.
- `operator`: 3 docs from `常见问题_FAQ.txt`, `用户指南_2024.docx`.
- `admin`: 3 docs from `常见问题_FAQ.txt`, `用户指南_2024.docx`.
- `super_admin`: 3 docs from `常见问题_FAQ.txt`, `用户指南_2024.docx`.

All current real registry documents are published, visible, and allowed for all four roles, so this smoke test verifies positive access behavior. Negative role isolation still depends on synthetic/unit coverage unless a restricted real document is added.

## Chroma Compatibility Fix

Chroma rejected flat multi-field filters such as:

```python
{"access_managed": True, "access_role_user": True}
```

The adapter now converts multi-field filters to:

```python
{"$and": [{"access_managed": True}, {"access_role_user": True}]}
```

## Verification

- Real reload script in `test3`: passed after Chroma `$and` fix.
- Real role smoke in `test3`: passed.
- `D:\agentlearn\miniconda\envs\test3\python.exe -m pytest tests/admin/test_p2_vector_store_backend.py -q`
  - Result: 12 passed.
- `D:\agentlearn\miniconda\envs\test3\python.exe -m py_compile tools/rag/chroma_backend.py tools/rag/vector_store_backend.py tools/rag_tool.py`
  - Result: passed.

## Observed Noise

- Chroma telemetry warnings remain.
- Loguru console output on GBK consoles can fail on checkmark characters during reload logging.
