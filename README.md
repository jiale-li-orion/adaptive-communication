English | [中文](README.zh.md)

# Agentic Communication under Intermittent Connectivity: Source-Grounded Decision Benchmark and Decision-Semantic Runtime

> **Current research architecture: Layer-1 Decision Benchmark v0.2 → frozen Layer-2 v1 revalidation classification → Layer-2 v2 future-choice / L-U method validation → Layer-3 learning only after the deterministic method contract is stable.** Layer-2 v1 has a completed revalidation **classification** at **A=4 / B=5 / C=1**; five B rows remain task-binding limits rather than re-executed v0.2 mechanism results. Layer-2 v2 currently has a validated **planning kernel**: 18/18 dev and 7/7 held-out hard signatures match generic-exact task/resource outcomes, and the held-out kernel uses 23.165% of generic-exact expansions and 53.251% of its wall time. This is not yet the full `cache06.md` method claim. The stronger same-order exact control still runs faster in wall time (v2 = 122.621% of ordered exact), and the original method contract additionally requires persistent conditional-frontier maintenance, explicit validity/invalidation domains, incremental-vs-full-rebuild equivalence on legal prefixes, a stronger ordinary/incremental baseline ladder, structural holdout, and the three-ledger task-quality/acquisition/computation evaluation. Layer 3 may be explored in parallel, but it does not yet own the main contribution.

**Layer-1 current state:** T1 `Monitoring Information Continuity` is the main Family; T2 `Warning Delivery & Response Handoff` remains a boundary extension with an explicit simulator gap. v0.2 exact labels are 55,008 no-paid-query / 2,106 paid-evidence / 630 information-infeasible / 1,008 mixed-world-solvability recipes. V0–V7 leaves 1,423 pass signatures; V8 leaves 41 signatures / 174 recipes, all `FINITE_CROSSING_WINDOWS + GATEWAY_SUMMARY_QUERY + overlap 3/4`. The structure-aware split contains 30,180 pre-admission recipes with hard train/dev/test signatures 16/18/7 and zero cross-split solver-signature leakage; public test identity is frozen at 3,804 cases. **Research freeze: yes. Public release admission: not yet.** The v0.2 release refresh is now **12 PASS / 1 BLOCKED**: Q6 DeepSeek Flash frozen-test baseline is complete (0/7 hard signatures succeed; 0 invalid actions; all failures are `DEADLINE_EXPIRED`), the agentic-reducibility and communication-attribution release audits both pass 41/41 hard signatures, and only Q11 real human/source review remains before `BENCHMARK_ADMIT`. See [Layer-1 Authority](research/benchmark/LAYER1-AUTHORITY.md) and the machine-readable [current state](research/benchmark/LAYER1-CURRENT-STATE.v0.1.json).

**Layer-1 graduation standard:** a released Decision Benchmark must demonstrate more than source grounding and case count. Its admitted decision cases must preserve **sequential interdependence, partial observability and adaptive strategy formation**; information acquisition must have real cost and compete fairly with passive feedback / normal send-as-probe; actions must change the physical state and future obligation feasibility; success must be judged by an external non-anticipative oracle rather than a model judge; strong ordinary baselines must leave held-out decision headroom; and controlled interventions must show that difficulty comes from communication/information constraints rather than generic task incompetence. The normative contract is [Layer-1 Decision Benchmark v0.2](spec/benchmark/LAYER1-DECISION-BENCHMARK-v0.2.md); the module-level checklist and current status live in [research/benchmark/README](research/benchmark/README.md). All machine/release-evidence gates are now closed except Q11, which still requires a real reviewer rather than an automated self-signoff.

This repository studies battery/solar mountain geohazard monitoring: LoRaWAN Class A nodes reach a field gateway, which uses cellular backhaul and an uplink-only BeiDou short-message backup. Monitoring requirements and warning-level changes are externally authorised. The system executes their communication requirements.

**Original field requirement:** pre-disaster mountain monitoring must keep useful sensing and return paths alive despite limited power and intermittent communication. This requirement remains first-order. The repository must not invent a communication task merely to activate an Agent or a learning algorithm; new Tasks are derived from source-backed operational needs and tested against the physical substrate.

**Shared communication substrate:** earlier systems work studied persistent communication state under control-path failure using source-local expiry, local fallback, segment-specific execution evidence, backup/DtS, and execution placement. Those results, the simulator, information boundaries, and execution mechanisms remain valid under the scopes registered in [CLAIMS](results/CLAIMS.md). They now serve as the common substrate beneath all three research layers.

**Historical systems-paper stage:** that stage produced component-level positive results and narrowed configuration leasing, single-node stopping and retention-horizon tuning into scoped-negative boundaries. The systems-paper compatibility copies, immutable archive, `CLAIMS`, Git and withdrawn-result snapshots preserve those design choices, negative results and open questions as part of the research lineage.

**Current research line:** Layer 1 is frozen for method work. Layer-2 v1 revalidation classification is closed at **A=4 / B=5 / C=1**, with acquisition timing as the only confirmed C-class failure: 744/808 query-legal pre-query boundaries are legal-but-harmful and 41/41 first-legal queries are harmful. Layer-2 v2 planning-kernel correctness has passed held-out: 7/7 exact resource-point matches, ordinary baselines 0/7, online expansions **508 vs 2,193** and wall **0.050 s vs 0.095 s** against generic exact. The stronger same-order exact control uses 994 expansions / 0.041 s, while v2 uses 508 / 0.050 s; therefore structural pruning is real, but a strong-baseline wall-time advantage is not yet established. The next main work remains Layer-2 v2 method closure under the original `cache06.md` gates; learned ranking/search guidance is a secondary extension, not a substitute for those gates.

## 0. External positioning and current claim boundary

The repository now sits inside the emerging **Agentic Semantic Communication / Agentic Communication Networks** literature, but it does not claim novelty from adding an Agent to a communication loop. The 2026 literature already covers most broad mechanism claims that are easy to overstate:

- task-aware semantic transmission and content selection;
- active probing / feedback acquisition under communication cost;
- “information insufficient → request more information → decide again” loops;
- context acquisition, ageing, persistence and delivery lifecycles;
- intent / task compilation into communication workflows;
- cross-step memory reuse and incremental semantic transmission;
- dynamic communication-pipeline reconfiguration;
- value-of-information send / no-send policies;
- world-model prediction and proactive transmission;
- long-horizon physical closed loops and counterfactual semantic value;
- freshness-aware semantic value and online channel adaptation.

Representative neighbours include RAMSemCom, Reasoning-Native Agentic Communication, Wireless Context Engineering, SkillComm, WM-CDT, GOSC / SVoI, imperfect-CSIT agentic link adaptation, Agentic TokenCom, AAMTSC and A2SSC. These works are treated as prior art, not renamed as our contribution.

The defensible research objects are narrower:

```text
source-grounded operational obligation
    + action-relative evidence sufficiency
    + heterogeneous capability for evidence acquisition
    + intermittent long-horizon obligation feasibility
    + external oracle for action / completion validity
```

The key distinction is **action validity rather than inference quality**. Existing systems often ask whether information is sufficient to answer a question, worth transmitting, fresh enough, or causally valuable to long-term reward. This repository asks a stricter operational question:

```text
Under the current real obligation and resource state,
which communication actions are still authorised by sufficient evidence,
and after taking one of them, which future obligations remain feasible?
```

This positioning also fixes the benchmark comparison. α³-Bench already provides interactive wireless-Agent control; 6G-Bench provides standards-derived network reasoning and oracle decisions; RAMSemCom already provides active information acquisition with wireless cost. The Layer-1 benchmark is therefore justified by the **combination** of source-traceable operational obligations, partial observation, costly acquisition, asynchronous physical state transitions, obligation-feasibility transitions, long intermittent connectivity / recovery, and an external exact oracle—not by “interaction”, “active sensing” or “physical communication” alone.

## 1. Manuscript lineage and authority entry points

| Material | Entry |
|---|---|
| Latest buildable Agentic manuscript snapshot | [English PDF](paper/agentic/en/main.pdf) · [LaTeX](paper/agentic/en/main.tex) · [workspace README](paper/agentic/README.md) |
| Systems-paper compatibility copies (still receive claim-correction propagation) | [English](paper/en/main.tex) · [Chinese](paper/zh/main.tex) · [paper/README](paper/README.md) |
| Immutable pre-Agentic systems-paper snapshot | [paper/_archive/system-paper-2026-09-20](paper/_archive/system-paper-2026-09-20/README.md) · source commit `dd4f31a` |
| Current research control plane | [Layer-1 Authority](research/benchmark/LAYER1-AUTHORITY.md) · [research/README](research/README.md) · [Benchmark](research/benchmark/README.md) · [Compiler](research/compiler/README.md) · [Policy](research/policy/README.md) |
| Current mathematical system model | [SYSTEM-MODEL-v1](research/substrate/SYSTEM-MODEL-v1.md) |
| Runtime/domain ownership contract | [OWNERSHIP-v1](research/compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md) |
| Systems-paper completion plan (historical stage) | [RESEARCH_PLAN](paper/RESEARCH_PLAN.md) |
| Claim-by-claim reproduction | [artifact/AE.md](artifact/AE.md) |
| Provenance, claim states, deployment | [Results](results/README.md) · [CLAIMS](results/CLAIMS.md) · [spec](spec/README.md) |

The manuscript lineage is continuous. `paper/en|zh` remain corrected compatibility copies so historical `C*` claims continue to build against current frozen semantics; `paper/_archive/system-paper-2026-09-20/` is the immutable pre-Agentic snapshot; `paper/agentic/` is the latest buildable Agentic manuscript snapshot. It no longer owns the global research direction after the 2026-10-04 benchmark-validity reset. README focuses on current ownership; Git, `results/history/`, `paper/_archive/`, and local research episodes preserve the full lineage.

## 2. Repository authority and long-lived constraints

This repository is both an implementation and an evidence system. The following ownership rules recur across the README history, the current experiment design, and the [paper-repository standard](tooling/paper-repository/PAPER-REPO-STANDARD.md); future refactors continue to use the same authority structure.

| Authority / invariant | Current rule |
|---|---|
| Claim truth | `results/CLAIMS.md` is the sole claim-state authority; README presents its current projection |
| Layer-1 direction/state | `research/benchmark/LAYER1-AUTHORITY.md` is the sole current Layer-1 direction/state authority; versioned generator/receipt notes cannot override it |
| Numeric truth | Experimental numbers originate in `results/` and reach papers/generated facts through `scripts/make_tables.py` or `scripts/make_agentic_artifacts.py` |
| Scenario and parameters | `spec/substrate/instance-v1-manifest.md`, `spec/substrate/datasets.md`, and the source registry own deployment/data provenance; every method shares the same frozen scenario |
| Mathematical model | `research/substrate/SYSTEM-MODEL-v1.md` is the public equation/model authority; local `docs/` may retain derivation notes while release dependencies remain in the tracked tree |
| Runtime/domain ownership | `research/compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md` owns canonical Task/Evidence/Context/Capability/physical-substrate boundaries; parallel schemas and hidden-truth shortcuts are contract violations |
| Layer-1 benchmark contract | `spec/benchmark/LAYER1-DECISION-BENCHMARK-v0.2.md` owns the normative v0.2 environment/observation/action/oracle/graduation contract; `research/benchmark/LAYER1-AUTHORITY.md` owns current Layer-1 status |
| Task authority | Risk levels, monitoring requirements, and Operational Tasks are externally authorised; the Agent owns communication execution while the scorer independently owns the obligation denominator |
| Evidence boundary | node/gateway/centre only see lawful owner-scoped evidence; missing, stale, unreachable, and negative observations are distinct; simulator hidden truth belongs only to evaluator/oracle paths |
| Action / capability boundary | the Capability registry owns the legal communication action surface; new capabilities enter through source, authority, binding, cost and failure semantics |
| Baseline fairness | ordinary expiry, TTL, local guards, AoI/EnergyAware, EDF/maxcov, deterministic compilers and other mature mechanisms remain equally available; an Agent contribution is the isolated increment beyond strong ordinary combinations |
| Contribution criterion | task/evidence/tool/policy semantics or physical/business outcome carry research contribution; unified objects, interfaces and Context structure carry systems-engineering value |
| Evaluation layers | Communication outcome is primary; Task grounding, EvidenceNeed, tool selection/order/arguments, Context, model calls and latency provide failure attribution |
| Model results | scripted/deterministic consumers own infrastructure/reference validation; real backend runs own model-effect claims |
| History | Git, `paper/_archive/`, and `results/history/withdrawn/` preserve superseded manuscripts and readings while current documents maintain current semantics |

## 3. Systems substrate: established technical object and evidence

A monitoring obligation requires an in-window sample, LoRa access to the gateway and central receipt before its deadline. Record retention, installed configuration, gateway receipt and central completion are distinct execution states. Evidence gaps remain explicitly `unknown`.

**Local action can require less information than complete diagnosis.** A gateway can preserve uncertainty between an absent sample and one not yet heard, while its source can still expire a record against a known deadline. An authorised local fallback can act directly on local energy. Placement therefore depends on evidence, authority and the remaining response time.

| Object | Evidence | Role in the paper |
|---|---|---|
| Source expiry and cross-segment retention | Standard expiry releases the source cache; gateway-only suppression can back-pressure access | Main positive system result (C2/C3) |
| Configuration fallback placement | Local ordinary protection handles some downgrades unreachable from the centre; ordinary combinations cover the tested stopping problem | Placement principle and boundary (C5/C6/C9) |
| Partial execution evidence | Online attribution covers the provable subset while the rest stays unknown; access, backhaul and completion retain separate evidence | Interface and formative Agent analysis (C4/C7/C8) |

The system uses mature primitives. Research value is demonstrated through composition, execution placement and physical outcomes; unified naming, object models and Agent interfaces provide engineering reuse.

## 4. Decision-Semantic Compiler v1 and post-benchmark revalidation

The Decision-Semantic Compiler stays on the same mountain pre-disaster monitoring physical/data plane and maps lawful Task/Evidence/Capability/Execution state into a model-facing decision surface:

```text
Physical/Data Plane
    -> Evidence World
    -> Operational Task
    -> Runtime TaskContract / TaskRun
    -> EvidenceNeed / InvestigationState
    -> ContextManifest / PromptAssembly
    -> evidence-use Capability / device-use Capability
    -> PlannerDecision
    -> existing communication simulator
    -> Communication metrics + Agent/runtime trace
```

Layer 2 v1 is already a completed mechanism line, not an unfinished placeholder. Its contribution is the typed runtime boundary between Task, lawful Evidence, Capability, Context, PlannerDecision and physical execution. The v1 line includes owner-scoped evidence acquisition, multi-round Context revision, action-conditioned candidate surfaces, persistent execution state, deterministic/reference consumers, model-facing PromptAssembly, replay, attribution, and live-model validation.

The benchmark reset does **not** invalidate those mechanisms. It changes the question asked of them. Earlier O1–O6 tasks often collapsed to a single ready action after compilation; the new Layer-1 v0.2 hard subset deliberately retains obligation-level deadlines, uncertain service, finite backup resources and multiple legal next actions. The current cross-layer evaluation therefore asks whether the frozen v1 compiler/runtime can still represent and solve that richer decision surface without hidden-truth leakage.

The revalidation result is now:

```text
Layer-1 v0.2 public task/evidence/capability/execution state
    -> existing Layer-2 v1 Task/Evidence/Context/Capability contracts
    -> B: as-is O1-O6 binding is lossy on 41/41 hard signatures
    -> thin lossless Layer-1-to-v1 binding [DONE]
       41/41 hard signatures PASS
       2,224 reachable decision boundaries
       4,577 legal candidate actions
       0 action round-trip mismatch / 0 hidden-field leakage
    -> C: frozen v1 acquisition trigger is unsafe on the new physical decision surface
       808 legal pre-query boundaries checked
       64 certified / 744 harmful
       41/41 first legal query boundaries harmful
    -> open Layer-2 v2 future-choice / L-U method
```

Category B remains compatibility engineering and is not an algorithmic contribution. Category C is now established for the acquisition trigger: v1 can recognize that owner evidence is unresolved, but it does not reason about whether acquiring that evidence **now** preserves future obligation feasibility. This is the concrete v2 problem.

**The two meanings of Task are frozen separately.** An Operational Task is benchmark/business semantics: what this mountain monitoring system must accomplish. A Runtime TaskContract is one Agent-harness execution instance: its targets, evidence contract, effect ceiling, temporal contract, and completion predicate. Each layer owns a stable schema and revision.

### 4.1 O1–O6 conformance catalog

O1–O6 share deployment, communication capabilities and scorer; they vary the business task or controlled disturbance rather than creating unrelated disaster questions. **They are retained as a conformance suite, not treated as the final Layer-1 decision benchmark.** In the current suite, several Tasks collapse to a unique supported plan; this is useful for protocol/runtime validation but insufficient for policy-learning claims.

| Task | Communication scenario semantics | Main evaluation object |
|---|---|---|
| O1 Monitoring Continuity | continuously satisfy periodic obligations at a given monitoring level | timely delivery, AoI, energy, bytes |
| O2 Risk Escalation | an external authority raises the monitoring level and requests denser sampling/shorter reporting | config install latency, mismatch duration, coverage, survival |
| O3 Backhaul-Outage Sustainment | sustain monitoring return during primary-backhaul failure | delivery/recovery, backup cost, store-and-forward, DtS |
| O4 Energy-Constrained Monitoring | maintain the authorised task under low harvest / low SoC | service-energy tradeoff, brownout, survival |
| O5 Recovery / Reconciliation | converge configuration, cache, and execution state after connectivity recovers | recovery latency, duplicate/late traffic, config confirmation |
| O6 Mixed / scoped operations | local targets, owner/reachability differences and composed disturbances | Context relevance, tool trajectory, physical outcome |

### 4.2 Evidence World and Context

The Evidence World represents lawful node/gateway/centre observations as typed, versioned evidence. Each record carries owner, source/provenance, observation time, revision, freshness/reachability and status; `CURRENT / STALE / NONE_RECENT / UNREACHABLE` remain distinct. `ContextManifest` performs reference-preserving selection, while FullDump serves as the baseline materialiser.

The runtime now executes a real multi-round loop: `Context@k -> evidence capability -> CapabilityResult/Percept -> Evidence World revision -> Context@k+1 -> device action/stop`. A gateway-owner read returns `UNREACHABLE` when its path is unavailable, while a negative observation uses its own status semantics.

### 4.3 Capability surface

The communication registry is [`research/compiler/COMMUNICATION-DOMAIN-REGISTRY.v0.1.json`](research/compiler/COMMUNICATION-DOMAIN-REGISTRY.v0.1.json). The normal planner surface currently contains three live observation capabilities and five live device capabilities; FullDump is separate and baseline-only:

- evidence-use: gateway receipt summary, gateway primary-health, centre node report;
- configuration device: set sampling interval, set report period;
- communication device: gateway backup, terminal-DtS, access-assist;
- baseline-only: centre FullDump materialiser.

Device tools reuse the existing physical models directly. `gateway_backup` changes the existing `JointControlPlane`; terminal-DtS keeps the existing opportunity/energy/success profile; access-assist keeps the simulator's original window and duration/bypass accounting. The Agent invokes those mechanisms through typed authority/schema/lifecycle gates.

### 4.4 Trace, replay and attribution

Each run emits a typed trace containing TaskRun, Context revision, CapabilityRequest/Result, Percept, ModelRequest/Attempt/Usage, PlannerDecision and physical effects. Four replay/evaluation levels are implemented:

- **R0 Protocol Replay**: Task → EvidenceNeed → Capability → State/Context → Policy;
- **R1 Frozen Model Input**: evaluate stopping, selection, order and arguments on the same PromptAssembly;
- **R2 Frozen Context Replay**: reconstruct Context/assembly hash exactly;
- **R3 Full Simulator Re-execution**: return policy/device effects to the physical system and measure communication consequences.

Gold replacement covers upstream `Task / EvidenceNeed / Percept / Context` and planner `selection / order / arguments / policy`. The attribution protocol is self-checked with controlled corruption before it is used for frozen real-model failure decomposition.

### 4.5 Current Layer-2 status

Layer 2 v1 is **frozen-complete as a first version**. Its established evidence includes:

- Task / Evidence / Context / Capability / Execution ownership and typed runtime contracts;
- multi-round `EvidenceNeed -> capability -> Percept -> Context revision -> action/stop` execution;
- candidate-action Context and action-conditioned deterministic/reference consumers;
- persistent execution / lifecycle state and replay/attribution infrastructure;
- CR / CF / CS comparisons and ordinary compiled baselines;
- WirelessOpsAgent-style same-interface comparison;
- A10/A11 query-positive acquisition evidence, including two-model transfer on the frozen gateway-backup family.

The reason research returned to Layer 1 was **insufficient benchmark decision headroom**, not an unfinished Layer 2. The old benchmark/compiler combination frequently produced `unique-ready` tasks, so additional Agent reasoning could not be meaningfully separated from ordinary compilation.

Layer-1 v0.2 fixes the original benchmark precondition, and the first v1 revalidation exposes a real method boundary. The old binding is lossy, but the new evaluation-only adapter now closes that compatibility gap without adding oracle or hidden-state information. The acquisition-trigger counterfactual therefore cannot be dismissed as a representation artifact: even when an owner query is legal and genuinely relevant, taking it too early can consume the communication opportunity required by later obligations. This is the first confirmed category-C failure on the new benchmark.

The post-reset method work is **not discarded**. `cache06.md` converged on a retained Layer-2 v2 hypothesis, and the new acquisition-trigger audit now supplies the category-C failure needed to activate it: **construct and maintain a communication context that preserves future feasible choices, rather than merely answering the current action.** In this view, evidence value is determined by which downstream plans remain feasible under shared opportunities, deadlines, execution history and resource commitments. Querying can increase information while simultaneously consuming time or communication opportunities, so information gain and action-space loss must be evaluated in the same causal state transition.

The corresponding algorithmic skeleton is a dynamic residual-feasibility / conflict frontier with action-wise bounds

```text
L_t(a) <= V*(h_t, a) <= U_t(a)

L_t(a) = 1 : an actually executable causal continuation already proves success
U_t(a) = 0 : even an optimistic structural relaxation proves the action cannot preserve completion
L_t(a) = 0, U_t(a) = 1 : unresolved; acquire evidence, expand planning, or fall back to exact search
```

The intended contribution is **not** a generic bounded planner that recomputes a deep proof for every action. The retained design uses communication structure to maintain reusable validity domains over obligations, shared opportunities, remaining resources, evidence and pending execution; ACKs, sends, window loss, new obligations and evidence updates should invalidate only the affected frontier when this is sound. Exact search remains the fallback when dependencies cannot be isolated or bounds overlap. Any v2 implementation must satisfy non-anticipativity, bound soundness, pruning preservation, incremental-vs-full-rebuild equivalence on legal prefixes, and honest end-to-end computation accounting.

The target research claim is therefore stronger than “fewer queries” or “fewer memo nodes”: **structure discovery + algorithmic property + system result**. The method must explain which evidence/resource coupling defeats ordinary rules, establish when future-choice context can be reused or locally recomputed, and finally move the task-quality / acquisition-cost / computation frontier toward lower communication and lower online computation. A result that only reduces internal search counters without improving end-to-end cost is treated as an implementation signal, not the final contribution.

## 5. Historical substrate evidence and frozen claim ledger

The `C*` and `A*` claims below are retained because they are still reproducible evidence and useful controls, **not because they define the current research direction**. They belong to the systems/runtime and earlier Agentic-paper lineage. Current Layer-1 state is owned by the benchmark authority; current Layer-2 state is the frozen Compiler/Runtime v1 plus its post-benchmark revalidation status described above. `results/CLAIMS.md` remains the historical/current claim ledger for these older result families.

- **Source expiry:** under the corrected gateway deadline boundary, standard per-record expiry remains a supported cross-segment placement result in the tested cache model. Numeric effect sizes and paired intervals are owned by the frozen result / generated paper table rather than this entry page. [C3 data](results/communication-substrate/claims/r37e_full_seeds.json)
- **Configuration termination:** a fixed TTL covers the candidate's survival and yellow-delivery operating points in the two tested phases. The energy-derived candidate collapses to the ordinary mechanism frontier, and ordinary combinations match the same-information exact stopping reference across the declared risk-weight sweep. [Matrix](results/communication-substrate/claims/c5_matrix.json) · [Reference](results/communication-substrate/claims/c5_seqref.json)
- **Online knowledge:** under the corrected deadline boundary, legal gateway evidence supports a correct-but-partial attribution interface while unresolved obligations remain unknown; exact counts/rates are owned by the frozen result / generated table. [C7 data](results/communication-substrate/claims/r40_local_attribution.json)
- **Agent interface:** historical live traces expose bidirectional errors caused by interpreting LoRa receipts as backhaul state. Offline v5 replay improves statements; C8 keeps this evidence at the formative-interface level. [C8 entry](results/CLAIMS.md)

Resource relaxations characterise capacity and energy pressure within the tested strategy family. C10 records the expiry-boundary implementation correction. Subsequent comparisons use corrected ordinary expiry.

The frozen states below are a checked projection of [CLAIMS](results/CLAIMS.md); that file remains the ledger of record.

| Claim | Scope | Status |
|---|---|---|
| C1 | Resource-relaxation characterisation | scoped-negative |
| C2 | Equivalence to ordinary record expiry | supported |
| C3 | Cross-segment placement of source expiry | supported |
| C4 | Time-aware failure attribution | supported |
| C5 | Evaluated configuration-lease candidate | scoped-negative |
| C6 | Local enforcement placement | supported |
| C7 | Partial online attribution | supported |
| C8 | Live Agent interface failures | formative |
| C9 | Same-information single-node stopping | scoped-negative |
| C10 | Expiry-boundary correction | supported |
| C11 | Reverse-acknowledgement delay bound (conditional); R1-closure rationale retracted | supported |
| A1 | Agentic runtime / physics conformance | supported |
| A2 | O2 deterministic Agent/runtime baseline isolation | supported |
| A3 | source-period and five-axis robustness infrastructure | supported |
| A4 | source-derived Operational Task transfer | supported |
| A5 | attribution protocol self-check | supported |
| A6 | communication baseline / evaluator-only oracle substrate | supported |
| A7 | protocol-v6 DeepSeek Flash confirmatory model result | supported |
| A8 | same-interface WirelessOpsAgent-style comparison | supported |
| A9 | held-out task/source/model transfer (v7) | supported |
| A10 | decision-conditioned evidence acquisition | supported |
| A11 | query-positive model transfer | supported |

The `A*` namespace contains deterministic/runtime evidence plus narrowly scoped historical model-effect claims. A7–A11 remain valid only within their frozen task/interface/model coordinates. They are retained as baselines and provenance for the current program; they do not establish the present benchmark, future-choice method, or any universal acquisition policy.

## 6. Historical Agentic paper lineage versus current research program

The A7–A11 live-model results remain frozen evidence, not the current research control plane. They cover the historical v6 paper table, same-interface WirelessOpsAgent-style comparison, held-out source/model transfer, and one query-positive gateway-backup acquisition family reproduced with DeepSeek Flash and MiMo v2.6 Flash. Their compact numeric authority remains `results/agentic/paper-v1/paper-results.json`; the complete claim ceiling remains `results/CLAIMS.md`.

`make agentic-preapi` still reproduces the credential-free runtime/conformance substrate. The three frozen model-facing inputs under `results/agentic/model-context-inputs-v1/` remain useful for historical model comparisons. None of those assets are discarded; they have been demoted from “next paper direction” to **controlled historical baselines and runtime evidence**.

The current research program is now versioned explicitly:

```text
Layer 1
source-grounded benchmark
    -> operational obligation
    -> partial observation / causal execution
    -> exact oracle / hardness / frozen split
    -> v0.2 technically frozen

Layer 2
Decision-Semantic Compiler / Runtime v1
    -> already completed and frozen as the first mechanism version
    -> Task/Evidence/Context/Capability/Execution
    -> multi-round acquisition + persistent execution + replay
    -> CR / CF / CS / WOA-style / A10-A11 evidence

Current bridge
Layer-1 v0.2 -> Layer-2 v1 revalidation
    -> B compatibility gap confirmed: 0/41 as-is lossless
    -> C acquisition-trigger failure confirmed on 41/41 hard signatures
    -> thin lossless binding remains required for end-to-end comparison

Layer 2 v2
future-choice / L-U context
    -> action-relative evidence sufficiency
    -> preserve future feasible choices
    -> conditional validity / local invalidation
    -> exact fallback when bounds or dependencies remain unresolved

Layer 3
policy / learning
    -> deferred until v2 semantics and fair v1/v2 end-to-end comparison are stable
    -> then compare deterministic / search / LLM / learned / hybrid policies
    -> keep task outcome, acquisition cost and computation separately accounted
```

The three accounting ledgers remain separate: **information/acquisition cost**, **task/communication outcome**, and **planner computation**. Exact success does not erase an information problem; a no-query successful policy does not erase resource or computation questions; a closed-loop task-success result does not by itself establish a computational method advantage.

Post-reset studies have now moved beyond exploratory signal at one specific boundary: legal-but-harmful acquisition is a confirmed frozen-v1 failure mode on all 41 hard signatures under the acquisition-trigger counterfactual. Earlier continuation/frontier/cache experiments remain research lineage; they are inputs to v2 design, not automatically promoted as the final v2 algorithm.

The v1 revalidation has now isolated such a decision-semantic failure, so the retained v2 research target is active: **autonomous information construction for task feasibility**. The Agent must decide what it still needs to know, whether to obtain it through owner queries, normal-send feedback, passive ACK/telemetry or waiting, whether acquisition at the current time still preserves future choices, when the current information is sufficient to act, and when previous evidence remains decision-valid after resources and execution state change. The deterministic feasibility/L-U layer supplies verified support and pruning; learning may later guide search order, evidence ranking or compact context construction, but it must not redefine legality, evidence ownership or task success.

Learning remains a solver choice, not the problem definition. No Layer-3 learning claim is opened until the existing Layer-2 v1 stack has been tested fairly on the new benchmark and any genuine v1 failure mode is isolated.

## 7. Scenario, physical model and extrapolation boundary

The [instance manifest](spec/substrate/instance-v1-manifest.md) defines deployment, sources and parameters. The main point has fourteen nodes, finite Class A windows and sparse short-message return opportunities. The action space contains registered sampling/reporting controls and communication capabilities; external authority supplies hazard/risk state, while satellite/backup resources enter through registry and instance budgets.

Synchronous airtime-free central acknowledgements, synthetic harvesting and absorbing brownout in the main configuration define the current extrapolation boundary. Episode I studies an upgrade, outage and recovery. Episode II isolates fallback across two authorised upgrade/downgrade phases. The exact stopping reference applies to a public task table, declared energy process and quantised single-node state; larger networks and new missions receive their own benchmark coordinates.

The current communication/energy substrate includes LoRa access, Class A receive opportunities, cellular primary backhaul, short-message backup, gateway backup, terminal-DtS, access-assist, node caches and deadline expiry, sampling/reporting configuration, solar/battery state and outage processes. NASA POWER hourly irradiance reaches the source-period split; synthetic solar/heterogeneous harvest remains a controlled research condition. Debris-flow/landslide fluid or geotechnical models act as an **upstream Operational Task generator** and can be promoted to scenario facts after their own validation.

One long-standing README discipline remains active: **scenario sources, research choices, and simulator-derived quantities are separate classes of facts.** Public standards/papers/vendor material define source-backed facts; research choices enter the experiment contract; simulator-derived quantities enter results. Network-wide shared quotas, end-to-end SLAs and satellite budgets stay `unknown` until a source or measurement promotes them into the contract.

## 8. Build and reproduce

```bash
make deps
make data
make check
make tables ARGS=--check
make agentic-preapi
make paper
```

The latest Agentic manuscript snapshot and historical systems-paper copies share [refs.bib](paper/refs.bib). [Build notes](paper/README.md) describe the role and build path of all manuscript trees. Tables and factual macros are generated from result files by `scripts/make_tables.py` / `scripts/make_agentic_artifacts.py`, with `paper/generated/` owned by that generation chain.

`make check` covers simulation, execution semantics, claims, tables, the stopping reference, Agent runtime and joint-layer anchors. `make agentic-preapi` reruns the credential-free Agent/communication substrate; A7–A11 live-model artifacts are frozen separately and represented in compact aggregate/audit/result files rather than raw traces. Claim-level commands and frozen references are in [artifact/AE.md](artifact/AE.md) and [results/reference](results/reference/README.md).

## 9. Repository map

| Path | Contents |
|---|---|
| `paper/agentic/` | latest buildable Agentic manuscript snapshot; not the global research control plane |
| `paper/en/`, `paper/zh/` | systems-paper compatibility copies that still receive claim-correction propagation |
| `paper/_archive/` | immutable manuscript/plan snapshots, including the pre-Agentic systems-paper source |
| `research/substrate/` | communication/world model and long-lived system semantics |
| `research/benchmark/` | Layer-1 benchmark validity, hardness, conformance split and construction contract |
| `research/compiler/` | Layer-2 Task/Evidence/Capability/Execution semantics and Decision-Semantic Compiler |
| `research/policy/` | Layer-3 policy/baseline ownership |
| `spec/benchmark/` | normative Layer-1 Decision Benchmark contract; research-frozen semantics and public-release graduation requirements |
| `spec/substrate/`, `spec/history/` | current deployment/data authority and historical prereg contracts |
| `code/substrate/` | physical simulation, joint communication mechanisms, calibration and substrate tests |
| `code/agentic_communication/` | Task/Evidence/Context/Capability/Planner/Replay runtime |
| `code/evaluation/` | current Agentic evaluation, claim audits and paper-facing checks |
| `code/legacy-communication/` | historical communication-method runners retained for reproducibility |
| `results/communication-substrate/` | current C* communication-substrate evidence |
| `results/agentic/` | A* experiment artifacts; semantic role is indexed by `ROLE-MANIFEST.*` |
| `results/reference/`, `results/history/`, `results/legacy-communication/` | frozen comparators, withdrawn/history, and historical result families |
| `results/CLAIMS.md` | sole claim-state ledger |
| `artifact/`, `scripts/` | reviewer entry, dependency acquisition and the result-to-paper pipeline |
| `tooling/` | reusable repository/paper tooling, separate from research ownership |

## 10. Remote repository versus local research zones

The repository follows [PAPER-REPO-STANDARD](tooling/paper-repository/PAPER-REPO-STANDARD.md): clone-verifiable, one numeric source, one current state per claim, traceable history. The remote repository contains paper-relevant implementation, specifications, compact frozen results, generated artifacts and auditable archives. Large `runtime_trace.jsonl` files, live-model per-run logs, workspace-local `local_work/`, compatibility `docs/`, and `local_experiments/` remain local/acquired research artifacts and are excluded from the release tree.

Local research zones may contain Astra reviews, killed candidates, one-off probes, HTML snapshots and early paper sandboxes. Promotion to the remote repository follows four gates: current normative dependency, stable owner, formal runner/result-registry use, and `make check` success. Assets that satisfy the gates join the formal tree; the rest stay as local provenance.

README presents the **current system state and long-lived authority**. Git/archive preserve round-by-round history, and `results/CLAIMS.md` supplies the current claim-state projection.
