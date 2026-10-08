# Layer 1 Deterministic Test Results

Frozen test: **150 coordinates / 750 online rows / 210 oracle diagnostics**. Paired bootstrap: 10,000 resamples; binary intervals: Wilson 95%.

| Task | Baseline | Mean TDR | Δ vs local [95% CI] | Full success | Survival | Energy Wh |
|---|---|---:|---:|---:|---:|---:|
| O1 | `agent.deterministic_comply` | 0.979 | +0.000 [+0.000,+0.000] | 3/30 | 1.000 | 0.101 |
| O1 | `comm.aoi` | 0.999 | +0.020 [+0.016,+0.025] | 27/30 | 1.000 | 0.103 |
| O1 | `comm.local_policy` | 0.979 | — | 3/30 | 1.000 | 0.101 |
| O2 | `agent.deterministic_comply` | 0.326 | +0.182 [+0.155,+0.208] | 0/30 | 1.000 | 0.361 |
| O2 | `comm.aoi` | 0.147 | +0.003 [+0.002,+0.004] | 0/30 | 1.000 | 0.103 |
| O2 | `comm.local_policy` | 0.144 | — | 0/30 | 1.000 | 0.101 |
| O2 | `comm.mission_comply` | 0.326 | +0.182 [+0.155,+0.208] | 0/30 | 1.000 | 0.361 |
| O2 | `comm.mission_sustain` | 0.326 | +0.182 [+0.155,+0.208] | 0/30 | 1.000 | 0.361 |
| O3 | `agent.deterministic_comply` | 0.979 | +0.000 [+0.000,+0.000] | 3/30 | 1.000 | 0.101 |
| O3 | `comm.backup_edf` | 0.979 | +0.000 [+0.000,+0.000] | 3/30 | 1.000 | 0.101 |
| O3 | `comm.backup_maxcov` | 0.979 | +0.000 [+0.000,+0.000] | 3/30 | 1.000 | 0.101 |
| O3 | `comm.local_policy` | 0.979 | — | 3/30 | 1.000 | 0.101 |
| O4 | `agent.deterministic_comply` | 0.979 | +0.000 [+0.000,+0.000] | 3/30 | 1.000 | 0.101 |
| O4 | `comm.ea_aoi` | 0.994 | +0.015 [+0.011,+0.019] | 17/30 | 0.988 | 0.349 |
| O4 | `comm.energy_aware` | 0.838 | -0.142 [-0.171,-0.114] | 0/30 | 0.564 | 0.348 |
| O4 | `comm.local_policy` | 0.979 | — | 3/30 | 1.000 | 0.101 |
| O6 | `agent.deterministic_comply` | 0.193 | +0.045 [+0.035,+0.055] | 0/30 | 1.000 | 0.259 |
| O6 | `comm.aoi` | 0.153 | +0.004 [+0.003,+0.005] | 0/30 | 1.000 | 0.102 |
| O6 | `comm.backup_edf` | 0.148 | +0.000 [+0.000,+0.000] | 0/30 | 1.000 | 0.100 |
| O6 | `comm.backup_maxcov` | 0.148 | +0.000 [+0.000,+0.000] | 0/30 | 1.000 | 0.100 |
| O6 | `comm.ea_aoi` | 0.279 | +0.130 [+0.124,+0.136] | 0/30 | 1.000 | 0.434 |
| O6 | `comm.energy_aware` | 0.265 | +0.117 [+0.099,+0.136] | 0/30 | 0.943 | 0.501 |
| O6 | `comm.local_policy` | 0.148 | — | 0/30 | 1.000 | 0.100 |
| O6 | `comm.mission_comply` | 0.193 | +0.045 [+0.035,+0.055] | 0/30 | 1.000 | 0.259 |
| O6 | `comm.mission_sustain` | 0.193 | +0.045 [+0.035,+0.055] | 0/30 | 1.000 | 0.259 |

## Boundary notes

- O3 is a saturation/control result if multiple ordinary baselines remain statistically indistinguishable; do not manufacture hardness.
- O4 must be read as a TDR–survival–energy trade-off, not a single-score leaderboard.
- O6 is the strongest current interactive benchmark surface; no Future-Choice Stress claim is implied by these deterministic results.
- Evaluator-only oracles are diagnostic and excluded from online ranking.
