# Agentic Communication Component Ablation v1

Status: pre-registered design only. Do not execute before protocol-v6 5-seed confirmatory completes and the formal result gate passes.

## 1. Purpose

Main-table confirmatory answers whether the frozen Method works end to end. This ablation answers a different question:

> Which model-facing decision semantics account for the gain, once ordinary Runtime execution substrate is held fixed?

The ablation must not re-open architecture search or introduce a new algorithm.

## 2. Frozen ordinary substrate

All arms share the same:

```text
Operational Task / TaskContract
Evidence World
candidate-plan generator
capability registry / authority
selected_plan_id -> typed invocation expander
persistent execution intent
runtime admission / dwell / in-flight handling
async observation timing
communication simulator / scorer
candidate reference / legacy comply reference
source period / task / seed
```

These are execution or evaluator substrate. They are not independently credited as Method novelty in this ablation.

## 3. Primary causal axes

### 0. Strong candidate-controlled Context baseline

Before attributing gains to evidence projection or Decision Sufficiency, compare
against a baseline that receives the **same Runtime-generated candidate graph**.

```text
M full-v6:
    candidate plans
    action-conditioned evidence projection
    plan-local EvidenceNeed scope
    decision_sufficiency

CF candidate+FullDump:
    same candidate plans
    same capability/action authority
    FullDump legal evidence surface
    no action-conditioned evidence contraction
```

The existing `action_candidates_full_dump` representation is the natural first
implementation target.  This is the key strong Context baseline for answering:

```text
Does candidate-conditioned evidence projection add value once candidate-plan
construction itself is held fixed?
```

Main-table `task-conditioned / FullDump / generic-ReAct` arms remain important
end-to-end baselines, but they are not sufficient for causal attribution because
they do not share the candidate-plan interface.

### A. Decision sufficiency certificate

Hold candidate plans, visible dependencies, evidence slice and Runtime execution fixed.

```text
A1 full-v6:
    candidate plans
    plan-local EvidenceNeed scope
    decision_sufficiency status

A0 no-explicit-sufficiency:
    same candidate plans
    same plan-local EvidenceNeed scope
    remove decision_sufficiency object and its protocol rules
```

Question:

```text
Does explicitly stating current commitment sufficiency change
effect-scope correctness / unnecessary acquisition / model cost?
```

This arm tests the certificate interface, not candidate generation.

### B. Plan-local dependency scope

Hold candidate plans and evidence content fixed.

```text
B1 plan-local:
    EvidenceNeed.blocking_plan_ids preserved

B0 globalized-needs:
    same unresolved needs exposed without plan-local blocking scope
```

The no-sufficiency certificate must be removed or recomputed consistently in B0 so the arm does not leak the answer through another field.

Question:

```text
Does dependency scope prevent evidence for one alternative from blocking
an already-supported independent plan?
```

### C. Semantic-state replanning

Hold the exact same model-facing Context semantics fixed.

```text
C1 decision_state
C0 every_context
```

Question:

```text
Does replanning only when the control-relevant decision relation changes
reduce repeated reasoning / acquisition without changing physical outcome?
```

This is primarily a system-efficiency / maintenance ablation. It should not be presented as a new planner algorithm.

## 4. Arms not treated as Method ablation

Do not use the following as headline contribution arms:

```text
with vs without persistent execution intent
with vs without selected_plan_id expansion
with vs without scoped Runtime admission
with vs without typed capability execution
```

Those comparisons are useful as conformance/interface diagnostics, but removing them creates an intentionally broken Runtime and confounds semantic planning with mechanical execution.

## 5. Execution order

Only execute after v6 confirmatory is complete.

Start with one task/seed that contains the relevant mechanism, then expand only if discriminative:

```text
O5 seed0:
    M vs CF candidate+FullDump
    A1 vs A0
    B1 vs B0

O5 seed0:
    C1 vs C0
```

If A/B do not produce a meaningful semantic or acquisition difference, do not scale them to 5 seeds merely to fill a table.

If C reproduces the already observed large call/token reduction with physical equality, scale only enough to establish robustness; it remains a Runtime-efficiency component.

## 6. Metrics

Use the same three-layer separation as the main table.

```text
Semantic:
    effect-scope exactness
    omission / underscope / overscope / wrong-scope / spurious-effect
    unnecessary observations

System:
    model calls
    total/input/output tokens
    API latency
    materialized Context bytes
    capability calls

Physical:
    candidate/legacy signature equality
    TDR / collection / AoI
    config mismatch
    command lifecycle
    energy / backup
```

No overall score.

## 7. Interpretation discipline

The component ablation may support statements such as:

```text
explicit plan-local dependency representation reduces unnecessary investigation
explicit no-action/action sufficiency improves stopping/commitment behavior
semantic-state replanning removes repeated equivalent reasoning
```

It must not be used to claim:

```text
generic decision sufficiency is new
action-sufficient representation is new
ordinary Runtime persistence/scheduling is a new algorithm
automatic dependency solving has been demonstrated
```

The last point remains gated by the dependency-expressiveness result: ordinary backward slicing plus current-state partial evaluation already reconstructs the current dependency target on `453/453` runtime-unresolved rows.
