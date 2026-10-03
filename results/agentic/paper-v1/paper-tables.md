# Agentic Communication — Paper Tables v1

## T1. Query-negative main result (DeepSeek Flash, 5 seeds)

| Task | Arm | Effect exact | Episodes w/ error | Physical exact | Obs/ep | Calls/ep | Tokens/ep |
|---|---|---:|---:|---:|---:|---:|---:|
| Localized O2 | Method | 100.0% | 0/5 | 5/5 | 0.0 | 6.8 | 36261 |
| Localized O2 | Task-conditioned | 48.8% | 5/5 | 1/5 | 8.8 | 8.4 | 68107 |
| Localized O2 | FullDump | 50.0% | 5/5 | 0/5 | 9.2 | 8.0 | 84621 |
| Localized O2 | Generic ReAct | 38.3% | 5/5 | 0/5 | 9.4 | 9.8 | 114521 |
| O5 | Method | 100.0% | 0/5 | 5/5 | 0.0 | 9.0 | 61200 |
| O5 | Task-conditioned | 37.3% | 5/5 | 0/5 | 28.0 | 10.4 | 154886 |
| O5 | FullDump | 44.0% | 5/5 | 0/5 | 22.6 | 10.2 | 145226 |
| O5 | Generic ReAct | 29.4% | 5/5 | 0/5 | 17.8 | 11.4 | 131945 |
| O6 | Method | 100.0% | 0/5 | 5/5 | 0.0 | 8.8 | 100761 |
| O6 | Task-conditioned | 34.9% | 5/5 | 0/5 | 26.2 | 12.6 | 185166 |
| O6 | FullDump | 27.9% | 5/5 | 0/5 | 27.6 | 14.0 | 205055 |
| O6 | Generic ReAct | 23.9% | 5/5 | 0/5 | 7.6 | 9.8 | 113895 |

## T2. Same-interface WirelessOpsAgent-style strong baseline

| Task | Method physical | WOA physical | WOA raw exact | Repairs | Method tokens/ep | WOA tokens/ep | Method token reduction |
|---|---:|---:|---:|---:|---:|---:|---:|
| Localized O2 | 5/5 | 5/5 | 34/34 | 0 | 36261 | 70954 | 48.9% |
| O5 | 5/5 | 5/5 | 45/45 | 0 | 61200 | 110445 | 44.6% |
| O6 | 5/5 | 5/5 | 44/44 | 0 | 100761 | 127379 | 20.9% |

## T3. Mechanism ablations / causal probes

| Mechanism | Ablation | Result |
|---|---|---|
| Evidence projection | CF: same candidate/needs/sufficiency + FullDump evidence | O5 action exact=True; O6 hold exact=True; FullDump input increases model cost (see T2) |
| Explicit no-action sufficiency | CS: remove explicit sufficiency from same compact input | O6 hold stop_exact=False; spurious observations=2 |
| Retired-dependency projection | M keep retired unresolved vs P prune retired-plan unresolved vs D prune more | M effect exact 1/3, obs=4; P 3/3, obs=0; D 3/3, obs=0 |
| Decision-conditioned acquisition | Full loop vs no-acquisition control | 5/5 TDR improved; 5/5 AoI improved; mean TDR +5.238 pp; mean AoI -1150.7 s |

## T4. Transfer and query-positive acquisition

| Setting | Model | Effect exact | Physical exact | Owner queries | Communication gain |
|---|---|---:|---:|---:|---|
| Held-out Qili/NASA-POWER-2024 | DeepSeek Flash | 29/29 | 5/5 | 0 | N/A (query-negative transfer) |
| Held-out Qili/NASA-POWER-2024 | MiMo v2.6 Flash | 29/30 | 5/5 | 1 | N/A (query-negative transfer) |
| Query-positive gateway backup | DeepSeek Flash | 56/56 | 5/5 execution-equivalent (4 direct + 1 recovered) | 16 | TDR +5.238 pp; AoI -1150.7 s |
| Query-positive gateway backup | MiMo v2.6 Flash | 56/56 | 5/5 direct | 16 | TDR +5.238 pp; AoI -1150.7 s |

## Claim boundary

The method claim is a decision-semantic compiler over Task/Evidence/Execution contracts. The current paper evidence covers three query-negative development tasks, one held-out task/source coordinate, one gateway-backup query-positive family, two LLMs on transfer/acquisition, and mechanism-specific causal probes. It does not claim globally optimal acquisition or arbitrary fallback coverage.
