# Agentic Communication frozen verdict references

This directory contains compact frozen verdict baselines for the current `A*` claim namespace. Runtime traces remain under `results/agentic/`; the reference layer freezes only the aggregate result and the semantic audit verdict needed for claim reproduction.

`audit.json` files from several runners include `result_hashes` over run manifests and traces. Those hashes intentionally identify a particular execution and may change when a semantically identical rerun receives a new run timestamp. `artifact/reproduce_all.sh` therefore compares Agentic audit files with `result_hashes` ignored, while all other audit fields and all aggregate fields are deep-compared.

| Claim | Frozen reference files | Fresh result owner |
|---|---|---|
| A1 | `A1-o2-global-{aggregate,audit}.json`, `A1-o2-localized-{aggregate,audit}.json` | `results/agentic/o2-*-risk-escalation-v1/` |
| A2 | `A2-baseline-{aggregate,audit}.json` | `results/agentic/o2-baseline-matrix-v1/` |
| A3 | `A3-source-period.json`, `A3-robustness-{aggregate,audit}.json` | source-period + robustness runners |
| A4 | `A4-transfer-{aggregate,audit}.json` | `results/agentic/task-transfer-qili-v1/` |
| A5 | `A5-attribution-{aggregate,audit}.json` | `results/agentic/attribution-matrix-infra-v1/` |
| A6 | `A6-communication-{aggregate,audit}.json` | `results/agentic/communication-baseline-matrix-v1/` |

Update rule: a semantic change to an `A*` result must update the corresponding reference in the same commit and explain why the claim still has its recorded status. A rerun timestamp alone is not a semantic change.
