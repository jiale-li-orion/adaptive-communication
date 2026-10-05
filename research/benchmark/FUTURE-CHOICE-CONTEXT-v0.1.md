# Future-Choice Context v0.1

Status: Layer-2 method line, 2026-10-05.  This document records the current
method object after the Layer-1 retry-legality correction; it does not alter
Layer-1 source/task semantics or benchmark admission.

## Object

At a causal decision boundary, the context should represent which next actions
still preserve at least one valid causal continuation under the current resource
budget and evidence state.  This is stronger than action legality and different
from an information-relevance score.

```text
legal_actions(t)
    -> certified_actions(t, Q, B)
    -> future-choice context
```

For action `a`:

- `legal(a)` means the action is executable under authority/resource semantics;
- `certified(a)` means forcing `a` still admits a causal completion witness;
- `L_t(a)=1` means a cheap replayable certificate already proves that fact;
- `U_t(a)=0` means a cheap relaxed structural argument proves no completion can
  survive the action;
- only `L_t(a)=0, U_t(a)=1` requires exact continuation search.

This yields explicit acquisition predicates:

- `query_now_legal`;
- `query_now_certified`;
- `query_legal_but_not_certified`;
- `can_defer_query_now`;
- `query_free_completion`.

`can_defer_query_now` is intentionally weaker than `query_free_completion`: a
non-query action may preserve the option to acquire evidence later even when
all-query-free completion is impossible.

## Evidence already established

### Resource-domain certificates

On twelve frozen source-corrected bundles and 172 `(query budget, satellite
budget)` cells, exact memo, ordinary resource-monotone memo and witness-domain
memo agree on every outcome; all positive witnesses replay.  Witness-tightened
resource domains add only about 0.52% expansion reduction beyond ordinary
monotonicity in rich-to-poor traversal and zero gain in poor-to-rich traversal.
Resource validity is sound but not the method advantage.

### Dependency separator

Natural search-state collisions with equal dependency separator but different
full history were found and independently checked.  Correctness held and
cross-state witnesses replayed, but expansion savings were about 0.6--1% and
index maintenance made wall time worse.  Historical-state compression alone is
therefore not the main contribution.

### Conditional continuation and acquisition timing

Among the twelve frozen retry-corrected cases, ten show information feasibility
gain and two are query-free after retry legality is fixed.  In the ten evidence-
requiring cases, seven have a single sufficient query time and three have
multiple disconnected sufficient query times.  A query can remain legally
executable while temporarily leaving the feasible future-choice set because the
read consumes a terrestrial opportunity required by task execution.

### Certified action frontier

The exact action-frontier audit traces 298 real decision boundaries on minimal-
resource causal policies.  Every exact-policy action belongs to the certified
action set and the query-certification times exactly match the independent
acquisition-timing frontier.  Across these boundaries there are 209 cases where
query is legal but not certified.  Three bundles exhibit
`certified -> uncertified -> certified` query re-entry.

This converts the earlier timing observation into a reusable context object:
**information acquisition should be judged by preservation of future feasible
choices, not by legality, freshness or standalone information value.**

## L/U baseline decomposition

The first lazy classifier uses cached causal witnesses as `L=1`, per-world
optimistic residual flow as `U=0`, and exact continuation only on unresolved
actions.  On 640 action classifications, every tested variant reproduces the
exact certified-action frontier.

The current ablation shows:

- exact/witness-only: 74 exact fallbacks, 36,942 exact expansions;
- structural upper d0: 60 fallbacks, 35,300 expansions;
- structural upper d4: 56 fallbacks, 35,052 expansions;
- d6 adds cost without reducing exact expansions further;
- satellite/common static lower leaves do not reduce fallback count;
- event-depth causal lower d1/d2 gives small additional success certificates;
  d4/d6 only increases lower-search work after d2.

The unresolved-success policies expose why event depth is a poor coordinate:
exact successful tails have raw depth 22--65 but only 2--6 non-WAIT decisions.
Most depth is passive time-lattice progression.  The next lower bound therefore
counts deliberate future choices rather than raw WAIT events.

## Current method hypothesis

A useful communication context is a compact certificate of **future choices and
its validity conditions**.  Computation should be spent only when the current
context cannot prove either side:

```text
L_t(a)=1        -> keep action a without exact re-planning
U_t(a)=0        -> remove action a without exact re-planning
L_t(a)=0,U_t(a)=1 -> exact fallback / evidence acquisition decision
```

The research question is no longer whether a smarter cache can reproduce exact
planning.  It is whether communication structure supplies cheap, reusable
certificates that keep the future-choice set correct while reducing exact
planning and unnecessary acquisition.

## Validity / invalidation diagnostic

The first explicit validity audit uses 18 development hard signatures and 414
adjacent exact-policy-prefix transitions.  Context truth includes both the
legal-action surface and the certified future-choice set.  It changes on 129
transitions.  The conservative dependency separator invalidates on every
observed transition, so 285 invalidations occur without any change in Context
truth.

A deliberately cheaper candidate key was then tested, rather than assumed: it
removed absolute time while retaining future obligation/window membership,
resource coordinates, pending operations and evidence state.  This candidate
is **not sound**.  Among 117 natural equal-key collision groups, 69 contain more
than one exact Context truth.  Examples include states with the same future
object membership where opportunity phase changes make new send/query actions
legal or alter the certified set.

A second candidate retains obligation phase (`FUTURE/ACTIVE`) and communication
opportunity phase (`FUTURE/OPEN`) while still removing absolute time.  On the
observed development collisions it is sound: 15/15 equal-key groups have one
Context truth.  Its additional reuse is small, however.  Conservative
invalidation-without-truth-change falls only from 285 to 270 transitions.  This
candidate is therefore retained as a correctness clue, not promoted as the
computational method.

The exact Context remains stable for meaningful intervals: truth-stable runs
average 2.94 boundaries / 2,061 s and reach 11 boundaries / 13,380 s.  Yet WAIT
is a genuine decision in this hard subset—no recorded hard-prefix boundary has
`WAIT` as the sole legal action.  Among WAIT transitions that do change Context
truth, the destination is always a communication-opportunity phase boundary in
this development audit (`TERR_START`, `SAT_START`, or `SAT_END`).

Therefore the next validity object cannot be a generic TTL-free cache key or a
free WAIT contraction.  The target is proof-relative **valid-until / slack
domain** semantics tied to the temporal/resource inequalities actually used by
the certificate.  Phase-aware state is necessary evidence, but its observed
reuse gain is not yet large enough to claim an algorithmic advantage.

## Claim boundary

All Layer-2 numbers above come from twelve frozen corrected-source cases and
exact-policy-prefix boundaries.  They establish method behavior and failure
modes, not benchmark-wide speedup or deployment superiority.  Layer-1 v0.2 is
the source of task/reference authority; Layer-2 prototypes must remain
separable from benchmark admission.
