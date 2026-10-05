# Conditional continuation frontier v0.1

Status: implemented bounded Layer-2 context diagnostic, 2026-10-05.

This object is the first direct implementation of the `cache06.md` requirement
that context preserve **future feasible choices and their validity conditions**,
rather than only cache a solved state or score a query.

## Object

For a fixed causal execution/evidence boundary `z`, evaluate the bounded integer
resource rectangle:

```text
Q = maximum additional paid owner queries
B = maximum remaining satellite sends
```

Each cell asks whether a causal policy exists that completes all obligations in
every compatible world while respecting the real transition semantics.  Queries
still consume terrestrial opportunity capacity; `Q` is an analysis/selection
bound, not a source SLA.

The context stores the Pareto-minimal feasible `(Q,B)` cells plus a replayed
causal witness for each point.  From the complete bounded rectangle it exposes:

```text
can_stop_acquiring_for_feasibility
minimum_query_budget_for_any_success
minimum_satellite_budget_without_paid_query
minimum_satellite_budget_with_query_allowed
satellite_budget_released_by_allowing_query
evidence_gain_type
```

The current evidence-gain taxonomy is deliberately non-scalar:

- `INFORMATION_FEASIBILITY_GAIN`: no query-free continuation exists in the
  declared rectangle, while a paid-evidence continuation does;
- `INFORMATION_RESOURCE_GAIN`: a query-free continuation exists, but allowing
  evidence lowers minimum satellite requirement;
- `NO_INFORMATION_GAIN_IN_Q_B_RECTANGLE`: query-free feasibility already attains
  the same minimum satellite requirement;
- `UNSOLVABLE_IN_BOUNDED_RECTANGLE`: no tested resource cell succeeds.

The first two are different scientific claims and must not be merged into one
generic "query helps" score.

## Frozen twelve-case result after retry-legality repair

The input is the same twelve source-corrected `GATEWAY_SUMMARY_QUERY` bundles
frozen for `LAYER1-RETRY-SEMANTICS-REVIEW-2026-10-05.md`.  They were selected as
paid-evidence-required **before** the retry-legality repair, so this is a semantic
diagnostic rather than a random estimate of the regenerated universe.

After the repair:

| conditional frontier | cases |
|---|---:|
| `INFORMATION_FEASIBILITY_GAIN` | 10 |
| `NO_INFORMATION_GAIN_IN_Q_B_RECTANGLE` | 2 |
| `INFORMATION_RESOURCE_GAIN` | 0 |

Frontier shapes are:

| minimal `(Q,B)` | cases | interpretation |
|---|---:|---|
| `(0,0)` | 2 | legal retries already give a query-free continuation; acquisition can stop for feasibility |
| `(1,0)` | 4 | one owner query is necessary in the bounded model; no satellite fallback is required |
| `(1,2)` | 6 | one owner query plus two satellite sends are necessary in the bounded model |

The two `(0,0)` cases are the two corrected-source signatures already identified
by the retry-action-mask review.  Allowing query does not reduce their satellite
requirement below zero, so they supply no resource-value claim.

The remaining ten retain genuine information-feasibility gain under the current
**no-duplicate-completion receiver contract**.  This statement is conditional on
that task/protocol contract.  The separate receiver-deduplication sensitivity
makes all twelve query-free and therefore cannot be silently folded into this
frontier.

## What this adds beyond resource-domain caching

`CONTINUATION-RESOURCE-DOMAINS.v0.1.md` showed that witness-tightened resource
memoization adds only ~0.5% expansion savings over ordinary resource monotonicity.
`CONTINUATION-DEPENDENCY-SEPARATOR.v0.1.md` showed that dead-history state
compression is correct but currently fails the net-compute gate.

The conditional frontier is a different object: it describes **what future
choices remain attainable under which evidence/resource conditions**.  It can
therefore support a decision such as "stop acquiring; ordinary execution is
already sufficient" or "one query is still feasibility-critical" without
pretending that cache reuse itself is the contribution.

## Next dynamic test

The initial-frontier result has now been extended along the real exact-policy
prefix before its first paid query.  At every decision time where a query is
legal, the audit forces exactly one query and then asks whether exact
continuation succeeds with zero additional queries.  Every positive continuation
is replayed.

The twelve-case timing result is:

| timing class | cases |
|---|---:|
| `STOP_FROM_INITIAL_BOUNDARY` | 2 |
| `SINGLE_CRITICAL_QUERY_TIME` | 7 |
| `DISCONNECTED_SUFFICIENT_QUERY_TIMES` | 3 |

For all ten evidence-required cases, no-query continuation remains infeasible at
every exact-policy prefix before the first query.  Ordinary send/wait execution
does not silently erase the evidence requirement.  The exact minimal-resource
policy issues its query at the **latest sufficient query time** in all ten cases.

The three disconnected cases are more important than a generic "query later"
story.  Their sufficient times are respectively:

```text
16800, 27600
15000, 25800
14100, 24900
```

Many intermediate decision times expose a legal owner query, but forcing the
query there makes exact zero-additional-query continuation fail.  Query legality
therefore does not imply query sufficiency, and sufficiency is not monotone in
time.  The reason is structural: the query consumes the same terrestrial
opportunity capacity needed by later report execution, while its sampled result
and future resource state also change with execution history.

This yields the dynamic context transition the method should eventually maintain:

```text
must acquire evidence
    ↓ event / execution
can stop acquiring
```

In the current ten hard examples the transition does **not** occur before the
first query; in the two retry-resolved examples it has already occurred at the
initial boundary.  The desired method property is not that the label changes
often.  It is that the maintained context changes **exactly when its supported
future-choice set changes**, while unaffected certificates remain valid and exact
fallback agrees.  The acquisition-timing frontier additionally shows that the
context must represent *when* a query remains feasibility-preserving, not merely
whether the query is relevant.

Artifacts:

- `code/evaluation/benchmark/conditional_continuation_frontier_v0_1.py`
- `code/evaluation/benchmark/audit_conditional_continuation_frontier_v0_1.py`
- `code/evaluation/benchmark/audit_conditional_acquisition_timing_v0_1.py`
- `results/benchmark/layer2-conditional-continuation-frontier-v0.1.json`
- `results/benchmark/layer2-conditional-acquisition-timing-v0.1.json`
