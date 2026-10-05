# Future-Choice Context — Layer 2/3 checkpoint (2026-10-05)

This checkpoint follows the Layer-1 `v0.2-retry-legality` correction. It keeps
three ledgers separate: task/reference correctness, computation, and acquisition
decision quality.

## 1. Current object

The Layer-2 context is action-relative:

```text
legal actions
    -> actions with replayable causal continuation certificates
    -> future-choice set
```

A query can be legal yet absent from the future-choice set because consuming the
read opportunity destroys all valid continuations. The controller therefore
tracks propositions such as:

- query is harmful now;
- query can be deferred;
- paid acquisition can stop;
- query is required now.

These propositions are defined by future feasibility, not freshness or a query
score.

## 2. What did not become the method contribution

### Resource-domain caching

On twelve frozen source-corrected bundles and 172 resource cells, witness-domain
caching is sound, but it improves over ordinary resource-monotone memo by only
about 0.52% expansions in rich-to-poor traversal and 0% in the reverse order.

### Dependency separator

Natural collisions with equal dependency separator but different full history
were correctness-checked and witness-replayed. Expansion savings stayed around
0.6--1%, while bookkeeping made wall time worse.

### Full structural L/U context as a compute shortcut

The first exact-action-frontier study contains 298 real decision boundaries and
640 action classifications. Structural upper bounds safely prune some failures;
static lower leaves and deeper event-depth search provide limited additional
coverage. Choice-depth search correctly exposes that 22--65 raw event steps may
contain only 2--6 send/query interventions, but deeper choice proof search is
expensive.

On the current seven hard test signatures (107 prefix boundaries), a U4/L6
bound-only full-context controller is sound and decisive at every boundary, but
its recorded wall time is roughly 2x the full exact action-frontier reference.

A fairer same-predicate comparison gives the same conclusion. Using an immutable
exact reference snapshot (`6291e4d7...6601e`), demand-driven structural proofs
resolve all 428 predicate instances with zero soundness errors and zero exact-
reference mismatches, but remain slower than generic exact early-stop:

| Predicate | Bound / exact wall ratio |
|---|---:|
| CAN_DEFER_QUERY | ~3.88x |
| QUERY_HARMFUL_NOW | ~1.18x |
| QUERY_REQUIRED_NOW | ~3.81x |
| STOP_ACQUISITION | ~6.85x |

Therefore **a computation-speed advantage is not established** on these cases.
Avoiding a function named `exact` is not evidence of a cheaper algorithm.

## 3. What did become a meaningful decision result

The exact action frontier shows 209 boundaries in the 12-case development study
where querying is legal but not future-feasibility-certified. Three cases show a
`certified -> uncertified -> certified` re-entry pattern for the same query over
time.

The stronger result is closed-loop. On the seven current hard test signatures,
all acquisition policies share the same exact non-query task-action selector;
they differ only in query timing:

| Acquisition policy | Success | Harmful queries |
|---|---:|---:|
| NO_QUERY | 0 / 7 | 0 |
| EARLIEST_LEGAL_QUERY | 0 / 7 | 7 |
| EXACT_FUTURE_CHOICE | 7 / 7 | 0 |
| BOUND_FUTURE_CHOICE (U4/L6) | 7 / 7 | 0 |

Both future-choice policies use exactly one paid query and two satellite sends
per successful signature. The bound policy selects exactly the same query time
as the exact future-choice oracle on all seven signatures:

```text
0a126d9bfbc1  2040 s
1f8d481b2365  2040 s
5e5e19d0b430  16500 s
7a1091a59eb0  2040 s
a645322c9cdb  2040 s
d4ac10808458  2040 s
f9b58a16cfc7  2040 s
```

The earliest-legal baseline queries at `t=0` in all seven signatures. Each of
those queries is future-feasibility-destroying, and all seven runs fail. This is
the current clearest algorithmic/semantic evidence for the project:

> legality or relevance does not determine whether evidence should be acquired;
> acquisition must be conditioned on the future feasible-choice set.

The bound controller has zero unresolved decisions and zero controller
soundness errors in these closed-loop runs.

## 4. Evaluation hygiene

The seven Layer-1 test signatures have now been inspected repeatedly during
method development. They remain structurally disjoint from train/dev, but they
must no longer be described as a pristine final held-out set for a publication
claim. Current results are **development diagnostics on a structure-aware test
partition**.

Future paper-grade validation needs a newly frozen method-evaluation holdout or
new source/trace-grounded structural support that is not used during method
iteration. Do not reshuffle recipe aliases and call them independent holdout
cases.

## 5. Next work

1. Freeze the current future-choice semantics and U4/L6 controller as a method
   checkpoint; stop tuning on the seven repeatedly inspected test signatures.
2. Run the same closed-loop protocol over all 41 hard signatures to measure
   coverage and failure modes, reported as development-scale evidence rather
   than held-out generalization.
3. Keep computation and communication ledgers separate. The present positive
   result is decision/communication quality; current structural proof search is
   computationally slower than generic exact early-stop.
4. For later algorithm work, target cheaper proof objects or learned scheduling
   only after a fresh evaluation split is frozen. Do not keep increasing proof
   depth on the current test set.

### Validity result added after the checkpoint

An 18-signature development audit tested whether future-choice context could be
reused by dropping absolute time from the dependency separator while preserving
future obligation/window membership and execution/resource state.  Context
truth here includes both legal and certified action sets.  The timeless key is
not sound: 69 of 117 natural collision groups contain different exact Context
truth.

The opposite extreme is also wasteful.  Across 414 adjacent prefix transitions,
exact Context truth changes 129 times, while the current conservative separator
invalidates on all 414 transitions.  A phase-aware candidate that preserves
`FUTURE/ACTIVE` obligation phase and `FUTURE/OPEN` communication-window phase is
sound on all 15 observed collision groups, but saves only 15 otherwise-redundant
invalidations.  Truth-stable runs still average 2.94 boundaries / 2,061 seconds
and reach 11 boundaries / 13,380 seconds, leaving real validity headroom.

The next validity target is therefore proof-relative slack / `valid_until`
conditions.  In this audit every truth-changing WAIT lands on a communication
opportunity phase boundary (`TERR_START`, `SAT_START`, or `SAT_END`), while WAIT
is never the only legal action.  This rules out both timeless reuse and free
WAIT contraction as shortcuts.
