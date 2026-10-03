# Query-positive gateway backup — five-seed DeepSeek confirmatory

| Seed | Status | Turns | Effect exact | Queries | Backup | Physical/reference | TDR Δ | AoI Δ (s) | Tokens |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|
| 0 | RECOVERED_PASS | 15 | 15/15 | 5 | 1 | recovered execution-equivalent | 0.017857 | -305.5 | 137866 |
| 1 | PASS | 8 | 8/8 | 2 | 1 | direct exact | 0.005952 | -646.3 | 71187 |
| 2 | PASS | 11 | 11/11 | 3 | 1 | direct exact | 0.130952 | -2303.1 | 99566 |
| 3 | PASS | 9 | 9/9 | 2 | 1 | direct exact | 0.101190 | -2137.1 | 80072 |
| 4 | PASS | 13 | 13/13 | 4 | 1 | direct exact | 0.005952 | -361.8 | 120028 |

Mean TDR delta: **0.052381** (+5.238 pp).
Mean AoI delta: **-1150.7 s**.
Effect-scope exact: **56/56**; failed attempts: **0**.
Owner queries: **16**; gateway-backup applied effects: **5**.

Seed0 boundary: task 018's episode completed, but its original runner was SIGKILLed during high-memory post-processing before summary write. The recovered row is kept explicitly distinct from the four directly persisted physical-signature rows.
