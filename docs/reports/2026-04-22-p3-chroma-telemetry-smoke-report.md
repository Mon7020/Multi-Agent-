# P3 Chroma Telemetry Smoke Report

Date: 2026-04-22

Environment:
- Python: `D:\agentlearn\miniconda\envs\test3\python.exe`
- ChromaDB: `0.6.1`
- PostHog: `7.9.12`

## Scope

This smoke test covers the remaining P3 telemetry noise:

`Failed to send telemetry event ... capture() takes 1 positional argument but 3 were given`

## Root Cause

ChromaDB `0.6.1` calls the older PostHog API shape:

`posthog.capture(user_id, event_name, properties)`

The installed PostHog `7.9.12` exposes an incompatible `capture` signature. Chroma catches that exception and logs it as a telemetry failure. This still happens even when Chroma clients are created with `anonymized_telemetry=False`.

## Change

Added `tools.rag.chroma_telemetry.disable_chroma_telemetry()`:
- Sets Chroma's bundled PostHog client to disabled.
- Replaces Chroma's direct telemetry capture path with a no-op.
- Is called before each project-owned Chroma `PersistentClient` creation path:
  - `tools/rag_tool.py`
  - `tools/rag/vector_db_manager.py`
  - `backend/app/services/knowledge_admin_service.py`

Regression test:
- `tests/admin/test_chroma_telemetry.py`

## Verification

Unit test:
- `D:\agentlearn\miniconda\envs\test3\python.exe -m pytest tests/admin/test_chroma_telemetry.py -q`
- Result: `1 passed`

Real smoke:
- Imported `tools.rag_tool.rag_tool`.
- Read the real Chroma collection count and one metadata payload.
- Result:
  - `count: 75`
  - `sample_metadatas: 1`
  - No Chroma telemetry warning was printed.

Remaining non-project noise:
- `jieba` prints dictionary cache load messages during initialization.
