# Novelty Boundary v1 — Plan–Evidence–Execution Semantics

Status: **paper-boundary / pre-algorithm authority**
Date: 2026-10-03

This document does **not** claim a new optimization problem merely because the
repository uses communication-specific names.  Its purpose is to state when the
current problem collapses to established formulations, what those formulations
already cover, and which additional dynamics would have to matter before a new
algorithmic claim is defensible.

The paper may proceed using the current compiler/runtime contribution even if no
additional algorithm survives this boundary test.

---

## 1. Current object

At runtime time `t`, define the legal runtime state

```text
S_t = (
    Operational Task / TaskContract,
    Evidence World,
    capability / authority surface,
    candidate-plan family,
    execution / commitment state
)
```

The compiler constructs a control relation

```text
R_t = Compile(S_t)
```

containing, for each currently represented plan:

```text
plan identity
effect / parameters / resource scope
authority
feasibility
supporting evidence
blocking evidence / unresolved guard
control eligibility
execution obligation
```

The full audit relation and the model-facing relation are different objects:

```text
R_t^audit
    -> all represented candidate/dependency rows

R_t^control
    -> currently control-eligible plans only

R_t^model
    -> live decision relation projected to the model
```

The model/runtime may then:

```text
commit a supported action
commit explicit no-action
acquire blocking owner evidence
wait for an already committed effect to progress
replan after the commitment basis changes
```

The current contribution is therefore a **dynamic typed relation + commitment
runtime**, not a generic sufficient-state or active-learning principle.

---

## 2. Static reduction tests

The following reductions are deliberate.  If an algorithmic proposal falls
inside one of them, it must be described as an application/adaptation of the
existing problem, not as a new generic algorithm.

### 2.1 Decision Region Determination / HEC

Javdani et al. (AISTATS 2014) study sequential tests over a fixed hidden
hypothesis space.  Hypotheses may belong to overlapping decision regions; testing
may stop once every hypothesis still consistent with observations lies inside at
least one common acceptable decision region.  Their HEC objective gives a
cost-sensitive acquisition policy with approximation guarantees.

Our problem reduces to DRD when all of the following are frozen:

```text
Operational Task and authority do not revise
candidate-plan family does not change
tests do not change the physical world
execution state does not feed back into candidate legality
evidence owner/path/freshness are fixed test properties
the goal is only to identify one acceptable final decision region
```

Therefore the following are **not novelty claims** here:

```text
do not resolve all uncertainty
stop once remaining uncertainty cannot change the acceptable decision
acquire information for decision rather than diagnosis
cost-aware sequential evidence acquisition in general
```

The paper may use DRD/HEC as a static acquisition reference, but cannot claim to
invent decision-aware acquisition or decision sufficiency.

### 2.2 Stochastic Boolean Function Evaluation / SSSC

SBFE evaluates a known Boolean function on unknown variables whose values can be
revealed at a cost.  Approximation algorithms reduce important cases to
Stochastic Submodular Set Cover; adaptive and non-adaptive testing gaps are also
well studied.

For any fixed plan `p`, suppose its feasibility is

```text
feasible(p) = g_p(x_1, ..., x_n)
```

where each `x_i` is a fixed unknown proposition, querying `x_i` only reveals its
value, and query cost is fixed.  Then evaluating whether `p` is feasible is an
SBFE instance.

If several fixed plans are evaluated simultaneously, shared propositions do not
make the problem new by themselves; simultaneous function evaluation and shared
test cost are already part of the SBFE/SSSC neighborhood.

Therefore these are **not novelty claims**:

```text
query the cheapest variable that helps certify a guard
adaptive query ordering over fixed Boolean guards
shared tests across several fixed guards
certificate-based stopping over a fixed guard graph
```

### 2.3 Minimum certificate / weighted set cover

Suppose the full Evidence World is already known and the only problem is to send
the model a cheaper subset `B` while preserving a fixed set of guard truth
values.  If each evidence item covers one or more fixed proof obligations and the
objective is minimum additive token cost, then

```text
min TokenCost(B)
s.t. B covers all required proof obligations
```

is a weighted set-cover / minimum-certificate form.

Thus the proposed "low-cost complete basis selection" is **not yet an independent
algorithmic contribution**.  It must first show structure that changes the
problem beyond ordinary certificate/set-cover selection.

Kill criterion:

```text
If the current frozen graph can be represented as fixed proof obligations plus
static additive evidence costs, and an exact/greedy weighted set-cover baseline
fully explains the achievable compression, stop this direction.
```

Do not manufacture a new sensor, authority edge, alternate proof, or hidden guard
to create headroom.

### 2.4 Provenance minimum witness

Database provenance already represents alternative derivations with OR and joint
support with AND.  Selecting a small witness/derivation from a fixed provenance
expression is established territory.

Therefore the following alone is insufficient novelty:

```text
AND = evidence that must co-occur
OR  = alternative evidence
shared evidence supports several guards
choose the smallest proof bundle
```

If the proposed basis algorithm only renames tuples/derivations as
Evidence/Plans, it should be treated as provenance/minimum-witness engineering.

### 2.5 Action-Sufficient State Representation

Huang et al. (ICML 2022) explicitly study compact state representations that
retain sufficient information for downstream control/policy learning, including
minimality under structural assumptions.

If our compiler is frozen to a one-shot mapping

```text
high-dimensional evidence -> compact action-sufficient representation
```

then the generic "minimal action-sufficient state" idea is already occupied.

Our current distinction is narrower:

```text
typed, explicit Task/Evidence/Capability/Execution contracts
no latent representation training
preserve a declared control relation, not all optimal policies
audit graph retained separately from model projection
```

This supports a compiler/runtime contribution, not a first-principles claim of
action sufficiency.

### 2.6 WirelessOpsAgent

WirelessOpsAgent already covers substantial evidence-grounded action assurance:

```text
canonical evidence binding
source/freshness/conflict/integrity checks
decision-linked evidence dependencies
dependency-scoped repair
revalidation
risk-aware authorization / governor
replayable assurance record
```

Therefore evidence graphs, support checking, scoped repair, and safe action
authorization are not independently novel here.

Our A8 comparison deliberately treats this as a strong same-interface baseline.
The current residual is not "we check evidence better"; it is the dynamic
compiler/runtime semantics around plan lifecycle, model projection, acquisition
through the communication substrate, and persistent physical execution.

### 2.7 Semantic communication / AoI / VoI

Semantic communication and information-timeliness literature already studies
relevance, freshness, value of information, process-aware sampling, and the fact
that communication/control utility depends on when information is used.

Hence these are not sufficient novelty claims:

```text
freshness should depend on task/control value
not all fresh information is useful
querying should trade information benefit against communication cost
latency and freshness are different
```

Any future validity-horizon contribution must be tied to a concrete typed guard
and commitment invalidation semantics, not just renamed VoI/AoI.

---

## 3. Residual structure that is not removed by the static reductions

The current paper's defensible residual is the **composition of these structures
inside one auditable communication execution lifecycle**.

### 3.1 Candidate/dependency liveness is endogenous

A dependency is not globally live merely because its proposition is unknown.

```text
plan becomes rejected / dominated
    -> its unresolved condition retires from R_t^model

plan becomes control-eligible
    -> its unresolved condition may become an active EvidenceNeed
```

The liveness of an evidence dependency is therefore a function of the current
candidate lifecycle, not only the truth/unknown status of a fixed variable.

A9 provides direct evidence that exposing a retired dependency changes model
behavior even when current decision sufficiency is already closed.

### 3.2 Action changes the future evidence problem

An action is not a terminal label.  A selected effect progresses through

```text
requested -> accepted -> delivered -> applied -> confirmed
```

and changes subsequent physical/evidence state.

Thus the system alternates between information acquisition and world-changing
execution.  A static hypothesis-test model is recovered only when these feedback
effects are removed.

### 3.3 Commitment persists across asynchronous execution

Decision sufficiency creates a semantic commitment, not merely an answer at time
`t`.

During ordinary transport/admission/confirmation delay:

```text
same commitment remains active
model need not restate the plan every tick
unrelated evidence refresh does not automatically reopen planning
```

Replanning occurs when the **commitment basis** changes, for example:

```text
TaskContract revision
candidate legality / authority change
blocking dependency resolution/invalidity
observed target satisfaction
explicit supersede / execution failure requiring a new semantic decision
```

This is the main structural distinction from a one-shot sufficient-state or
decision-region formulation.

### 3.4 Evidence acquisition is a communication action with ownership/path

Evidence is not an abstract zero-time test.  A query has typed semantics:

```text
Owner
Path / reachability
latency
bytes / airtime / energy
freshness at return/use time
failure status
```

The center-placement query-positive attempt is an important negative witness:
at a 3600 s backhaul delay, evidence returned after 3660 s and correctly failed
the 3600 s freshness gate.  The experiment did not relax freshness to preserve a
positive case.

The eventual gateway-placement A10/A11 coordinate is therefore a real owner/path
instance rather than an abstract test oracle.

### 3.5 Audit relation and model relation intentionally differ

The runtime keeps a complete audit graph while projecting only the currently
decision-live relation to the model.

This is not ordinary lossy state compression:

```text
audit completeness is preserved for replay/accountability
control eligibility determines model visibility
retired/shadow relations remain auditable without remaining actionable
```

The compiler therefore solves an interface/lifecycle problem even when no new
combinatorial optimization algorithm is claimed.

---

## 4. What A7–A11 actually establish

### A7 — query-negative main result

Establishes reliable model consumption and end-to-end execution on three
development tasks.  It does **not** establish autonomous acquisition or complex
candidate tradeoff because all 123 Method requests had a unique ready supported
plan and no visible EvidenceNeed.

### A8 — same-interface WirelessOpsAgent-style comparison

Establishes that on the same query-negative coordinates a strong assurance-style
baseline can be equally reliable, while the compact Method uses fewer model
tokens.  This supports a model-interface cost result, not a reliability win over
WirelessOpsAgent and not optimal Context compression.

### A9 — held-out transfer / dependency liveness

Establishes that retired-plan unresolved conditions can perturb a second model,
and that the narrow v7 projection repair transfers to full execution.  This is
evidence for dependency-liveness semantics, not a generic theorem about minimal
representations.

### A10/A11 — query-positive acquisition

Establishes a real closed loop:

```text
blocking EvidenceNeed
-> legal owner query
-> evidence return
-> conditional plan becomes rejected/supported
-> semantic commit
-> one real gateway-backup effect
-> changed communication outcome
```

The physical gain is relative to **acquisition disabled**, not relative to an
optimal DRD/SBFE acquisition policy or a strong local trigger.  Therefore A10/A11
prove that the acquisition branch is real and useful in this system; they do not
prove globally optimal acquisition.

---

## 5. Claim language allowed in the paper

Recommended method-level statement:

> We compile Task, Evidence, Capability, and Execution contracts into a dynamic
> plan–evidence relation.  The runtime exposes only currently control-live
> dependencies to the model, explicitly represents action/no-action sufficiency,
> acquires owner evidence when a live plan remains blocked, and persists the
> resulting semantic commitment through asynchronous physical execution.

Recommended novelty location:

```text
dynamic plan/dependency lifecycle
+ audit/control/model surface separation
+ persistent semantic commitment
+ communication-constrained evidence acquisition
+ physical execution/replay integration
```

Do **not** write:

```text
we introduce decision-aware acquisition
we introduce decision sufficiency
we introduce minimal action-sufficient Context
we introduce cost-optimal evidence selection
we introduce AND/OR proof minimization
we introduce value/freshness-aware communication
we outperform optimal acquisition
```

unless a future result directly establishes the corresponding stronger claim.

---

## 6. Basis-selection candidate: formal go/no-go test

The basis-selection idea is quarantined from the paper method until it passes the
following decomposition.

### Static baseline problem

Given a frozen control relation `R` and evidence universe `E`, define a basis `B`
as any subset preserving the same current control relation:

```text
DecisionRelation(B) = DecisionRelation(E)
```

with additive token/materialization cost.

Before implementing a new algorithm, mechanically construct the corresponding
fixed proof-obligation instance and compare against:

```text
exact enumeration / integer program on small graphs
weighted set-cover/minimum-certificate formulation where applicable
ordinary dependency slicing + schema/value dedup + group-by baseline
```

### GO requires both

```text
1. Real frozen repository graphs contain genuine alternative/shared proof
   structure that leaves nontrivial headroom over ordinary compact compilation.

2. The remaining optimization contains a dynamic constraint not captured by the
   fixed minimum-certificate/set-cover formulation, and that constraint matters
   on existing workloads without manufacturing a new scenario.
```

Candidate dynamic constraints worth checking, but not presuming novel:

```text
proof validity must survive an in-flight commitment interval
candidate retirement/reactivation changes which proof obligations remain live
owner/path/freshness makes future evidence availability state-dependent
execution feedback changes the next proof graph
```

### KILL if either

```text
ordinary compact is already at/near the exact static minimum

OR

all observed headroom is explained by weighted set cover / minimum witness /
minimum certificate on a frozen graph
```

If killed, retain A8 as the paper's Context-cost evidence and do not add an
optimization algorithm solely for novelty.

### 6.1 Frozen-input audit result — **KILL**

The go/no-go audit has now been executed on the formal model-facing inputs from
A7, A10 and A11:

```text
results/agentic/basis-selection-headroom-v1/audit.json
```

Coverage:

```text
235 requested PromptAssemblies
32 requests with >1 live visible plan
```

Observed proof-choice structure:

```text
first-class alternative proof fields = 0
EvidenceNeed blocking >1 live plan    = 0
multi-source evidence requirement     = 0
duplicate proposition/subject rows    = 0
```

The 32 multi-live-plan requests come from the real query-positive family, but
that does not create a minimum-basis choice problem: `consider_gateway_backup`
has a fixed conjunctive owner-evidence guard.  The model must resolve that guard;
there are no alternative proof bundles to optimize over.

Decision:

```text
KILL_BASIS_SELECTION_NO_REAL_CHOICE_SPACE
```

Therefore no exact set-cover oracle, heuristic basis optimizer, or additional
model experiment will be implemented for this paper.  Creating such headroom
would require introducing proof alternatives that are absent from the frozen
paper workloads, which violates the pre-registered kill criterion.

---

## 7. Validity-horizon candidate: hold

Do not open a new validity-horizon algorithm now.

The literature already covers task-sensitive information freshness/VoI.  A new
contribution would require a workload where a typed guard is valid at observation
time but may cease to support an already in-flight commitment before
application/confirmation, and where this distinction changes decisions relative
to ordinary freshness handling.

A10/A11 do not provide that structure: their successful gateway-owner query is
local and immediately actionable.  Therefore current evidence does not justify a
new algorithm here.

---

## 8. Research decision

Current decision:

```text
FREEZE A7–A11 METHOD/RESULTS
STOP NEW MODEL EXPERIMENTS
WRITE THE PAPER NOW
STOP BASIS-SELECTION SIDE STUDY
```

The optional side study returned a negative result by its own kill criterion.
The paper therefore remains a compiler/runtime/system-method contribution with
the current four formal tables.  No additional algorithm is added solely to make
the contribution look more "algorithmic".

---

## 9. Literature boundary

Primary references used for this boundary:

1. Javdani et al., *Near Optimal Bayesian Active Learning for Decision Making*,
   AISTATS 2014 — Decision Region Determination / HEC.
2. Huang et al., *Action-Sufficient State Representation Learning for Control
   with Structural Constraints*, ICML 2022.
3. Deshpande, Hellerstein, Kletenik, *Approximation Algorithms for Stochastic
   Boolean Function Evaluation and Stochastic Submodular Set Cover*, 2013.
4. Hellerstein et al., *Adaptivity Gaps for the Stochastic Boolean Function
   Evaluation Problem*, 2022.
5. Lu et al., *WirelessOpsAgent: A Benchmark and Agent Design for Action
   Assurance in Wireless Networks*, 2026 preprint.
6. Semantic communication / information-timeliness literature summarized in
   `RELATED_WORK.md`, including AoI/VoI and query-age references.
7. Database provenance / minimum-witness literature for AND/OR derivations and
   minimal supporting witnesses.

This list constrains claim language; it does not imply that the current paper
must solve every referenced optimization problem.
