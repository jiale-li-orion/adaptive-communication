# Layer 2 proof target review — 2026-10-05

This note reviews the workspace after `4b7fe35` and the subsequent uncommitted
future-choice controller/compiler work. It does not modify those active files.
The three-layer and source-grounded compositional task decisions in cache06
remain unchanged.

## Current conclusion

The project now has a concrete action-relative context object, not merely an
architecture diagram: replayable successful continuations, safe impossibility
bounds, unresolved actions, and query/defer/stop predicates. That is methodological
progress. A performance advantage has not yet been established.

The current recorded evidence says:

- Resource-domain tightening adds at most 0.52% expansion reduction beyond the
  ordinary resource-monotone cache in one traversal order, and zero in the other.
- The 12-case action-frontier study agrees with its exact reference on 640
  classifications. Eliminating exact fallback can nevertheless increase total
  bounded-search work; fallback counts alone are not the objective.
- The recorded seven-signature test-prefix study contains 107 decision boundaries.
  U4/L6 classifies all of them consistently with the exact reference, but takes
  about 6.51 s against 3.25 s. This is a bounded prefix diagnostic, not closed-loop
  task success or a statistically established runtime ratio.

## Insight to retain: proof depth is not elapsed event count

Successful residual policies can have 22–65 raw event steps yet only 2–6
send/query actions. This explains why event-limited search can miss short
intervention sequences. It does not establish that all WAIT actions are passive.

Current choice-depth code gives every WAIT zero horizon cost. A WAIT selected
instead of a feasible transmission or timely query can be an irreversible
resource decision. Therefore the existing parameter is accurately described as
**send/query intervention depth**, not the count of all genuine decisions.
Correctness of the bounds is a separate issue from the interpretation of depth.

A true event contraction may freely bypass forced waiting only while retaining
all observation branches and stopping before a changed actionable alternative.
Any stronger commutation/dominance contraction requires a proof. Both ordinary
planning baselines and the proposed method must receive the same event handling;
otherwise a comparison mostly measures different horizon accounting.

## Next method target: context should answer an explicit decision predicate

The current compiler generally classifies every legal action, then derives a
query/defer/stop label. Those labels require different amounts of proof:

| Requested context conclusion | Sufficient proof |
|---|---|
| A particular action preserves completion | One replayable causal continuation |
| Query can be deferred now | One certified non-query first action; later queries remain allowed |
| Paid acquisition can stop for feasibility | One complete continuation using zero future paid queries |
| Query is required now | A certified query continuation AND impossibility of every legal non-query alternative |
| Query is harmful now | No successful continuation after that query under the declared contract |
| More evidence cannot improve transmission cost | Cost-frontier evidence; feasibility alone does not establish this |

The next single implementation increment should schedule these proof obligations
on demand, reuse established witnesses, and stop when the requested proposition
is established. Do not compute the entire action frontier unless it is actually
requested. Return unresolved under a computational limit, not a fabricated label.

This develops the existing action-relative sufficiency design. It is not a new
query scoring direction, a new generator, or an argument to abandon the scene.
It also is not novel merely because it uses early stopping: ordinary existential
search and AND/OR proof search are the required comparison.

## Fair next comparison

For each identical legal boundary and requested predicate, compare:

1. Generic exact search answering that predicate directly, with memo and early stop.
2. Existing full-action context construction, followed by predicate extraction.
3. Demand-driven structural L/U proof scheduling with the same cached information.

Use identical action sets, intervention-depth/event treatment, physical costs,
support and available feedback. Count total runtime including flow bounds,
proof construction, lookup, replay validation and context serialization. Report
false positive conclusions, unresolved fraction and per-predicate results.
In particular, 106 defer boundaries and one query-required boundary must not be
collapsed into a headline accuracy dominated by the easy conclusion.

The exact-policy prefixes currently recorded remain a diagnostic distribution.
A later closed-loop evaluation must also visit states induced by each policy's
own choices. No new held-out claim should be made from repeated inspection of
the same seven test signatures.

## What would count as progress

A sound predicate answered at lower total cost than a generic same-question
solver, or more sound answers under the same computational allowance, is useful
algorithm evidence. Merely avoiding a function named `exact`, or assigning WAIT
zero depth while still expanding it, is not that evidence.

The broader target remains cache06's task quality–communication–computation
frontier. This increment gives a precise interface and fair comparison for
reaching it, while preserving the existing operational scenario and contracts.
