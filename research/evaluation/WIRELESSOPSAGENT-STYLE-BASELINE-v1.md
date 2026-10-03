# WirelessOpsAgent-style Strong Baseline v1

Status: comparative adaptation specification. This is **not** a claim that the
original WirelessOpsAgent source code has been reproduced.

Reference: Lu et al., *WirelessOpsAgent: A Benchmark and Agent Design for Action
Assurance in Wireless Networks*, arXiv:2608.08277, especially §IV-A–E.

## 1. Why this baseline exists

WirelessOpsAgent is the closest current related method to the evidence/action
assurance part of Agentic Communication. A fair comparison must preserve its
actual strengths:

```text
canonical evidence binding before generation
proposal-level evidence/dependency checking after generation
typed integrity diagnosis
dependency-scoped bounded repair
revalidation
risk-aware APPLY / HOLD / RETRY / ESCALATE / ABSTAIN authorization
```

It must not be weakened into “wait for every telemetry field”, “clear state every
turn”, or “force a remote query before every action”.

## 2. Shared substrate

The WOA-style arm shares exactly the same:

```text
Operational Task / TaskContract
legal Evidence World
control-eligible candidate-plan menu
plan parameters and affected resources
selected_plan_id -> typed invocation expander
persistent semantic execution intent
runtime admission / in-flight / confirmation lifecycle
semantic decision-state replan gate
communication simulator and scorer
DeepSeek Flash model settings / call budget
```

It does **not** receive the Method's explicit `decision_sufficiency` certificate.

The model-facing evidence slice is deliberately strong: the full legal Evidence
World is exposed, while the candidate menu remains the same compact
control-eligible menu used by the Method.

## 3. Input binding

The repository already normalizes Evidence World records into typed fields:

```text
evidence_id
proposition / subject_ref / value
source_id / source_role / owner_location
generated_at_s / observed_at_s / world_revision
status / freshness
provenance
```

This typed Evidence World serves as the WOA-style immutable canonical ledger.
The adaptation does not invent aliases, alternate units, clock-skew metadata, or
other fields not exposed by this repository.

## 4. Proposal assurance

The LLM output is treated as a proposal, never as directly executable truth.

The assurance layer checks:

```text
schema:
    capability exists in the shared catalog
    canonical argument shape is valid

unit:
    canonical-unit conformance where the repository exposes a unit-bearing field
    otherwise explicitly not-applicable

source / provenance:
    proposal-supporting evidence remains bound to exposed ledger sources

freshness:
    proposal-supporting evidence is current under the exposed status/freshness metadata

conflict:
    no unresolved InvestigationState conflict or contradictory current ledger value

scope completeness:
    proposed effects remain inside the candidate plan's affected-resource set

authorization:
    selected plan is currently supported and has no unresolved blocking condition
```

The check is dependency-scoped. Unrelated FullDump evidence does not block a
supported plan merely because it exists or is older.

## 5. Bounded local repair

Recoverable proposal failures are repaired without another LLM call:

```text
invalid / rejected selected plan
    -> if exactly one supported ready plan exists, bind proposal to that plan

incomplete effect list
    -> bind the affected proposal region to the matching supported candidate plan

wrong stop bit on an otherwise supported plan
    -> repair stop semantics from zero-effect vs effect-bearing plan

nonblocking observation calls attached to an already-supported plan
    -> drop those calls
```

Unrelated clean proposal fields are not broadly rewritten. Every accepted repair
is recorded and the rebuilt proposal is revalidated before authorization.

## 6. Governor

The ordered adapted governor is:

```text
APPLY:
    supported effect-bearing plan passes revalidation

ESCALATE:
    unresolved conflict / ambiguous authorization state remains

RETRY:
    a blocking EvidenceNeed maps to an exposed retryable observation capability

HOLD:
    required support is not current, or the supported plan is an intentional zero-effect hold

ABSTAIN:
    no supported action and no more specific recovery route exists
```

For this repository, a supported `hold_current_profile` is mapped to `HOLD` as the
no-effect authorization outcome; the authorization record distinguishes this from
an evidence-blocked hold.

## 7. Replayable authorization record

Each planner turn stores a sidecar record containing:

```text
raw model proposal
ready supported candidate IDs
integrity checks and violations
used evidence IDs
accepted local repairs
unresolved risks
governor result
final Runtime decision
state/world revision
```

This is evaluator-visible audit data and is not fed back into the tested model.

## 8. Current adaptation boundary

The public paper artifact/source was not integrated into this repository at the
time of this specification. Therefore results must be named:

```text
WirelessOpsAgent-style adaptation
```

not:

```text
official WirelessOpsAgent reproduction
```

If author code becomes available and is mapped later, the mapping must be audited
before changing that label.

## 9. Evaluation order

Start with seed0 only:

```text
localized O2
O5
O6
```

Measure both raw proposal and post-assurance decision:

```text
raw plan/effect errors
governor outcome
accepted repair count/type
post-assurance effect-scope exactness
observation calls
model calls / tokens / latency
physical equality to candidate and legacy reference
```

Only if seed0 is technically sound should the baseline expand to seeds0–4.
