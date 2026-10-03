# Protocol-v6 confirmatory main table

Rows: **60/60**

## Method gate

- `rows`: `15`
- `expected_rows`: `15`
- `all_effect_exact`: `True`
- `all_zero_observation`: `True`
- `all_candidate_exact`: `True`
- `all_legacy_exact`: `True`

## Group summary

| Task | Context | Seeds | Pooled effect exact | Episodes with error | Physical=legacy | Obs mean | Calls mean | Tokens mean | Context bytes mean |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| localized-o2 | action_conditioned_compact | 5 | 100.0% | 0 | 5/5 | 0.00 | 6.80 | 36261 | 17599 |
| localized-o2 | task_conditioned | 5 | 48.8% | 5 | 1/5 | 8.80 | 8.40 | 68107 | 21199 |
| localized-o2 | full_dump | 5 | 50.0% | 5 | 0/5 | 9.20 | 8.00 | 84621 | 30828 |
| localized-o2 | generic_react | 5 | 38.3% | 5 | 0/5 | 9.40 | 9.80 | 114521 | 29419 |
| o5 | action_conditioned_compact | 5 | 100.0% | 0 | 5/5 | 0.00 | 9.00 | 61200 | 22538 |
| o5 | task_conditioned | 5 | 37.3% | 5 | 0/5 | 28.00 | 10.40 | 154886 | 39526 |
| o5 | full_dump | 5 | 44.0% | 5 | 0/5 | 22.60 | 10.20 | 145226 | 38627 |
| o5 | generic_react | 5 | 29.4% | 5 | 0/5 | 17.80 | 11.40 | 131945 | 30498 |
| o6 | action_conditioned_compact | 5 | 100.0% | 0 | 5/5 | 0.00 | 8.80 | 100761 | 37542 |
| o6 | task_conditioned | 5 | 34.9% | 5 | 0/5 | 26.20 | 12.60 | 185166 | 38848 |
| o6 | full_dump | 5 | 27.9% | 5 | 0/5 | 27.60 | 14.00 | 205055 | 38697 |
| o6 | generic_react | 5 | 23.9% | 5 | 0/5 | 7.60 | 9.80 | 113895 | 29472 |

## Semantic failure taxonomy

- `localized-o2/task_conditioned`: effect_omission=11, underscope=10
- `localized-o2/full_dump`: effect_omission=10, underscope=10
- `localized-o2/generic_react`: effect_omission=10, underscope=12, wrong_scope=5, spurious_effect=2
- `o5/task_conditioned`: effect_omission=24, wrong_scope=5, spurious_effect=3
- `o5/full_dump`: effect_omission=19, underscope=1, wrong_scope=8
- `o5/generic_react`: effect_omission=21, underscope=5, overscope=1, wrong_scope=7, spurious_effect=2
- `o6/task_conditioned`: effect_omission=30, underscope=4, overscope=1, wrong_scope=6
- `o6/full_dump`: effect_omission=33, underscope=5, overscope=2, wrong_scope=9
- `o6/generic_react`: effect_omission=13, underscope=15, wrong_scope=5, spurious_effect=2

## Paired Method vs baseline

Positive exact-rate delta favors Method; negative observation/call/token delta means Method uses less.

| Task | Baseline | Pairs | Exact-rate Δ | Obs Δ | Calls Δ | Token Δ | Token reduction |
|---|---|---:|---:|---:|---:|---:|---:|
| localized-o2 | task_conditioned | 5 | 51.3 pp | -8.80 | -1.60 | -31846 | 45.4% |
| localized-o2 | full_dump | 5 | 50.0 pp | -9.20 | -1.20 | -48360 | 56.9% |
| localized-o2 | generic_react | 5 | 58.3 pp | -9.40 | -3.00 | -78260 | 65.2% |
| o5 | task_conditioned | 5 | 62.5 pp | -28.00 | -1.40 | -93686 | 60.1% |
| o5 | full_dump | 5 | 54.5 pp | -22.60 | -1.20 | -84026 | 56.9% |
| o5 | generic_react | 5 | 68.1 pp | -17.80 | -2.40 | -70745 | 45.1% |
| o6 | task_conditioned | 5 | 61.4 pp | -26.20 | -3.80 | -84405 | 43.9% |
| o6 | full_dump | 5 | 70.3 pp | -27.60 | -5.20 | -104294 | 50.8% |
| o6 | generic_react | 5 | 73.6 pp | -7.60 | -1.00 | -13134 | 9.8% |
