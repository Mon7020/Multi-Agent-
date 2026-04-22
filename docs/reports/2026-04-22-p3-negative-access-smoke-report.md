# P3 Negative Access Smoke Report

Date: 2026-04-22

Environment:
- Python: `D:\agentlearn\miniconda\envs\test3\python.exe`
- Offline model flags enabled for the smoke run: `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`
- Target: real local Chroma store and knowledge registry

## Scope

This smoke test validates that vector metadata ACL filters block a restricted document for the `user` role while allowing the same document for privileged roles.

The test created a temporary published document:
- Document id: `doc_5dc927f13271479595972f8708ec34ec`
- Source file: `data\docs\p3_operator_only_smoke.txt`
- Allowed roles: `operator`, `admin`, `super_admin`
- Probe query: `P3NEGATIVEACCESS-OPERATOR-ONLY <after-sales escalation channel>`

## Results

After adding the temporary document and reloading Chroma:
- Reloaded chunks: 66
- Access policy version with restricted document: `729a4b4ee53e23dd`
- The temporary document contributed 1 restricted chunk.

Role query results:

| Role | Retrieval success | Returned documents | Restricted doc matches |
| --- | --- | ---: | ---: |
| `user` | true | 5 | 0 |
| `operator` | true | 5 | 1 |
| `admin` | true | 5 | 1 |
| `super_admin` | true | 5 | 1 |

Assertions passed:
- `user_blocked: true`
- `operator_admin_super_admin_allowed: true`

## Cleanup

The smoke test restored the original knowledge registry, removed the temporary source document, and reloaded the real Chroma store.

Post-cleanup state:
- Restored chunks: 65
- Verified chunks: 65
- Restored access policy version: `365100730b951a26`

## Notes

The run produced Chroma telemetry warnings, but retrieval and assertions completed successfully. The PowerShell console also replaced some Chinese characters with `?` in preview logs because of console encoding; the role-filter assertions used the actual retrieval results and passed.
