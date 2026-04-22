# P3 Logger Encoding Smoke Report

Date: 2026-04-22

Environment:
- Python: `D:\agentlearn\miniconda\envs\test3\python.exe`
- Shell: Windows PowerShell, GBK console behavior

## Scope

This smoke test covers the remaining P3 issue where Loguru printed internal `UnicodeEncodeError` reports when console output contained characters not encodable by the active Windows console codec.

The triggering example was the checkmark in `tools/rag_tool.py` deduplication logs.

## Change

`core.logger` now wraps the console stream so unsupported characters are replaced instead of raising during console writes. File sinks still write UTF-8 as before.

Regression test:
- `tests/admin/test_logger_encoding.py`

## Verification

Unit test:
- `D:\agentlearn\miniconda\envs\test3\python.exe -m pytest tests/admin/test_logger_encoding.py -q`
- Result: `1 passed`

Real smoke:
- Called `rag_tool.add_documents_to_vector_db()` with a unique temporary document.
- The checkmark log was emitted as `?` on the GBK console.
- No Loguru `--- Logging error ---` block was printed.

Cleanup:
- The temporary Chroma vector id `doc_1776836414731_1ad4e582` was deleted directly by content match.
- Chroma count after cleanup: 75

## Remaining Noise

Chroma telemetry warnings still appear:
- `Failed to send telemetry event ... capture() takes 1 positional argument but 3 were given`

Those warnings are unrelated to the console encoding failure and remain the next P3 cleanup candidate.
