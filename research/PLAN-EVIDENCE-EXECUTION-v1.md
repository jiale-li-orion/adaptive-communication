# Plan–Evidence–Execution Method Semantics v1

Status: development design note. This file defines the current method boundary;
it does not claim novelty by itself.

## 1. Problem object

At simulator time `t`, the Runtime owns:

```text
Operational Task / TaskContract
Evidence World
candidate communication plans
capability authority
execution state
```

The method compiles these into a dynamic decision dependency structure.

The structure is not a world-state estimator. It answers a narrower question:

> which communication effects are already justified for the current Task, which
> candidate branches remain unresolved, and which evidence can still change the
> currently legal decision surface?

## 2. Four distinct surfaces

### Full audit graph

Contains all currently represented candidate plans and dependencies, including
exploratory plans that are not yet control-eligible.

Purpose:

- audit/replay;
- benchmark diagnostics;
- future candidate-family closure;
- dependency-construction evaluation.

The full graph may therefore contain `shadow_only` fallback/preparation branches.

### Control-eligible surface

Contains only candidate plans that the current Runtime semantics permit the model
to select as real control choices.

Invariant:

```text
shadow-only candidate != active decision branch
```

Evidence that can only refine a shadow-only branch must not become an active
EvidenceNeed for the model.

### Model Context projection

The compact Context is a projection of the control-eligible surface, not a dump
of the full audit graph.

It preserves the currently declared relation among:

```text
Task authority
candidate effect / parameters / resources
supporting evidence
blocking evidence
unresolved control-relevant dependencies
execution feedback
```

Resolved audit rows and dependencies belonging only to shadow candidates may be
omitted while their full form remains available in RuntimeTrace/audit artifacts.

### Persistent execution surface

Once the planner selects a semantic configuration effect, ordinary Runtime owns
its progression through:

```text
intent
-> admission
-> submitted
-> delivered
-> applied
-> confirmed
```

The model is not required to repeat the same semantic plan every simulator tick.
Observation-only or no-effect planner turns do not implicitly cancel unfinished
configuration intent. TaskContract revision and observed target satisfaction are
explicit invalidation/completion events.

### Semantic plan selection vs mechanical expansion

When Runtime has already constructed a typed candidate plan, the planner's
semantic choice is the candidate identity, not a second transcription of every
per-resource capability invocation.

Current protocol therefore permits:

```text
selected_plan_id = <supported candidate>
```

Runtime validates that the selected plan is model-visible, `supported`, and has
no unresolved conditions, then deterministically expands its declared typed
invocations. Explicit planner invocations remain available for additional
observations, so `selected_plan_id + query` is still a valid mixed decision.

This expander is ordinary execution substrate. It contributes no planning
intelligence and must not be described as algorithmic novelty. Its purpose is to
separate semantic plan choice from mechanical JSON duplication, especially when
one global Task plan expands to many resource-local effects.

## 3. Decision sufficiency

For a supported primary plan `p`, unresolved evidence need `n` is blocking only
when it can still alter `p`'s legality, parameters, scope, or required execution.

Current representation:

```text
EvidenceNeed.blocking_plan_ids
candidate_plan.unresolved_conditions
candidate_context.decision_sufficiency
```

Open evidence attached only to another candidate does not delay an already
supported primary action.

No-action is also an explicit semantic decision.  After projection to the
current control-eligible surface, a zero-effect plan such as
`hold_current_profile` is decision-complete only when it is the unique ready
supported plan, no other control-visible live alternative remains, and its own
blocking need set is empty.  In that case the model-facing status is:

```text
sufficient_for_no_action
```

This status is intentionally computed after shadow-only plans are removed from
the model control surface.  The full audit graph may remain `undetermined`
because it retains future/unclosed fallback branches; that audit uncertainty
must not leak back into the current control decision and trigger unnecessary
evidence acquisition.

Conversely, if a real control-eligible conditional alternative remains live,
`hold_current_profile` is not enough to declare no-action sufficient.  The
projection must stay `undetermined` or blocked until the decision-changing
evidence is resolved.

Prior-art boundary: generic decision sufficiency / decision regions are not new;
Javdani et al. (AISTATS 2014) already formalize stopping information acquisition
once remaining hypotheses share an acceptable decision region. The current
research question is the dynamic communication setting: partial commitment,
changing Task authority, heterogeneous evidence ownership, and asynchronous
physical execution.

## 4. Semantic replanning

Planner invocation is triggered by changes in the control-relevant decision
relation, not by every Context/EvidenceWorld refresh.

Examples that require replanning:

```text
TaskContract revision
candidate feasibility change
effect resource-scope expansion/contraction that changes semantic action scope
blocking dependency opened/resolved
previous commitment invalidated
```

Examples that must not by themselves require replanning:

```text
ordinary execution progress already owned by persistent intent
refresh of evidence attached only to shadow candidates
change in a nonblocking evidence need
audit-only dependency updates
```

The replan key is model-hidden and shared across Context-representation baselines
when the experiment is intended to isolate model-visible Context effects.

## 5. Current algorithm boundary

The current dependency compiler is deliberately ordinary.

The development probe over O1--O6 + localized O2, after the global Task-scope
authority repair, found:

```text
runtime unresolved dependency rows: 453
guard-name backward slice:           341/453 exact, 112 FP, 0 FN
+ current-state partial evaluation:  453/453 exact, 0 FP, 0 FN
```

Therefore automatic safe-prefix/dependency solving is not currently supported as
an independent algorithmic contribution. It remains compiler substrate unless a
future benchmark case exposes a dependency relation that ordinary slicing and
partial evaluation cannot recover.

## 6. Representation boundary

The method does not claim a globally minimal sufficient state representation.
Huang et al. (ICML 2022) already study action-sufficient state representations
for control under structural constraints.

The narrower invariant here is:

> for the declared Task and candidate-plan family, the projected Context should
> preserve the action / parameter / authority / blocking-dependency relation
> needed for the current model decision.

Compression is therefore evaluated relative to this explicit decision relation,
not as a claim of POMDP-state sufficiency or globally optimal policy preservation.

## 7. Evaluation separation

Method evaluation must keep three layers distinct:

```text
semantic:
    effect-scope exactness
    action/parameter/resource errors
    unnecessary observation

system:
    model calls
    Context bytes
    tokens / API latency
    capability calls

physical:
    TDR / collection / AoI
    configuration mismatch
    command/downlink trajectory
    energy / backup usage
```

Physical equality to the deterministic candidate reference demonstrates faithful
execution of the declared candidate semantics. It does not by itself prove that
the candidate reference is globally optimal against every communication policy.
