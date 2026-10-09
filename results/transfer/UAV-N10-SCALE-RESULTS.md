# UAV N=10 Scale Extension

## Constructive hard-feasible 100

All 100 seeds were selected before FutureChoice evaluation by an official-heuristic zero-tardiness witness. The first 21 are exactly the previously frozen exact-audited cohort.

| Policy | Native zero | Depth4 zero | FutureChoice zero | Native complete | Depth4 complete | Future complete | Depth4 infeasible | Future infeasible |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| nearest_neighbour | 49/100 | 87/100 | 100/100 | 100/100 | 100/100 | 100/100 | 0 | 0 |
| nearest_deadline | 12/100 | 47/100 | 100/100 | 51/100 | 69/100 | 100/100 | 41 | 0 |
| greedy_deadline_battery | 79/100 | 87/100 | 100/100 | 95/100 | 98/100 | 100/100 | 3 | 0 |
| battery_aware_nn | 49/100 | 87/100 | 100/100 | 100/100 | 100/100 | 100/100 | 0 | 0 |

## External-paper-matched 50

The 50 layout seeds exactly follow the external repository's evaluate_policy RNG protocol (episodes=50, seed=999). Six layouts have an ordinary constructive zero-tardiness witness; FutureChoice is only evaluated on those six.

Full Wilson intervals, paired bootstrap CIs, exact McNemar discordance, energy/tardiness deltas and search-work summaries are in `uav-attention-n10-scale-statistics.json`.
