English | [中文](README.zh.md)

# Agentic Communication under Intermittent Connectivity

Source-grounded decision benchmark, decision-semantic runtime, and learning-guided exact search for pre-disaster mountain monitoring under limited power and intermittent communication.

> **Current control plane:** Layer 1 retains three scoped assets: the v0.2 failure atlas, the reproducible-but-invalid v0.6 negative construction lineage, and the v0.7 process-support correction. None is a released benchmark. Gateway-local autonomy is now the frozen primary v0.7 placement; center remote control remains a transport `SIMULATOR_GAP`. A bounded 36-cell gateway pilot found no resolved ordinary-baseline survivor, while 8 cells remain computationally unresolved. Layer 2 remains reference/correctness infrastructure and Layer 3 is paused. Current ownership lives in [`research/`](research/README.md).

## 1. Architecture at a glance

```text
External operational sources / field requirement
                    │
                    ▼
┌──────────────────────────────────────────────────────────────┐
│ Layer 1 · Source-grounded Emergency Communication Benchmark │
│ obligation · partial observation · action · transition      │
│ exact oracle · validity / hardness · frozen split            │
└──────────────────────────────┬───────────────────────────────┘
                               │ public task/evidence/action contract
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Layer 2 · Decision-Semantic Compiler                         │
│ Task / Evidence / Capability / Execution                    │
│ legality · evidence lifecycle · future-choice L/U frontier  │
│ conflict structure · incremental maintenance · exact fallback│
└──────────────────────────────┬───────────────────────────────┘
                               │ legal structured decision surface
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Layer 3 · Policy                                             │
│ deterministic / search / LLM / learned guidance             │
│ current status: paused pending Layer-1 benchmark closure     │
└──────────────────────────────┬───────────────────────────────┘
                               │ selected communication action
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Shared Communication Substrate                              │
│ LoRa/Class-A · gateway · cellular · BeiDou backup · cache   │
│ battery/harvest · outage/recovery · execution · scorer      │
└──────────────────────────────────────────────────────────────┘

Cross-cutting: evaluation · literature · result ledger · provenance
```

Layer 1 owns the problem. Layer 2 owns deterministic correctness and the legal decision surface. Layer 3 owns choice order inside that surface. The shared substrate owns physical execution and scoring.

| Module | Owns | Current state | Entry |
|---|---|---|---|
| **Shared substrate** | communication physics, energy, cache, opportunity, fallback, execution lifecycle, mathematical model | stable shared base | [`research/substrate/`](research/substrate/README.md) |
| **Layer 1 · Benchmark** | source-grounded obligations, task construction, observation/action/oracle contract, validity/hardness, split/release | **source/generation infrastructure ready; gateway placement frozen; dynamic hardness open; NOT_BENCHMARK_ADMIT** | [`research/benchmark/`](research/benchmark/README.md) |
| **Layer 2 · Compiler** | Task/Evidence/Capability/Execution semantics, L/U future-choice frontier, evidence lifecycle, incremental update, exact fallback | **v2 deterministic core frozen on dev** | [`research/compiler/`](research/compiler/README.md) |
| **Layer 3 · Policy** | ordering and selection among legal / unresolved actions | **paused**; previous learned-ranking line retained only as negative/history until Layer 1 closes | [`research/policy/`](research/policy/README.md) |
| **Evaluation** | replay, attribution, ablation, baseline fairness, cross-layer audits | cross-cutting | [`research/evaluation/`](research/evaluation/README.md) |
| **Literature** | related work, source registry, claim boundary | cross-cutting | [`research/literature/`](research/literature/README.md) |
| **History** | superseded tracked research authority / roadmap | provenance | [`research/history/`](research/history/README.md) |

## 2. Problem anchor and research position

The project starts from a concrete pre-disaster monitoring requirement: mountain sensing nodes operate under limited power and intermittent connectivity; communication outages can isolate nodes and prevent monitoring data from reaching the centre; the system must preserve recoverable, sustainable monitoring communication at low power and cost.

The field requirement stays first-order. Agentic Semantic Communication / Agentic Communication Networks provides the external academic coordinate for the decision layer. The repository therefore follows this order:

```text
real operational need
→ traceable constraints and capabilities
→ physical communication environment
→ lawful partial observation
→ communication choices with real cost
→ causal obligation-feasibility transition
→ exact / executable evaluation
→ hardness
→ Agent / learning method
```

The current research object is a five-part decision contract:

1. **Source-grounded Operational Obligation** — what the monitoring system must accomplish.
2. **Action-relative Evidence Sufficiency** — whether current lawful evidence supports a concrete communication action.
3. **Heterogeneous Capability for Evidence Acquisition** — how missing facts can be obtained through real owners, paths and feedback mechanisms.
4. **Intermittent Long-Horizon Obligation Feasibility** — how sending, waiting, querying and fallback change which future obligations remain achievable.
5. **External Oracle for Action / Completion Validity** — an executable authority for action feasibility and task completion.

The semantic object in this repository is **action-useful information about whether communication obligations remain achievable**. Its value depends on the task, remaining resources, execution history and future choices.

Evidence acquisition is placement-aware rather than mandatory. Owner-local facts remain local state and are not re-priced as communication merely to manufacture an information gap; heterogeneous remote acquisition becomes an evaluated mechanism only when a lawful owner/transport contract actually exists.

## 3. Shared communication substrate and system-model lineage

The shared substrate is the oldest technical layer that still carries current research. It predates the three-layer benchmark/compiler/policy architecture and preserves the physical consequences that later Agentic work must respect.

### 3.1 How the current substrate was built

The physical model reached its current shape in two major upgrades.

**2026-09-13 · instance-v1 physical closure.** A dense sequence of commits (`a68c01b` → `a827a82`) replaced the earlier lightweight instance with a reproducible multi-node communication system: exogenous processes and three-time transfer semantics; finite cache and action-driven energy; SRTM terrain + ITM per-link feasibility; separated collection/delivery accounting; centre-originated command delivery and acknowledgement; source-derived harvest; a 16-item deployment manifest and consistency checks. This stage also established the E/A/M discipline used throughout the repository: source evidence, research operating-point choice, and model/implementation output are recorded separately.

**2026-10-01–03 · current system-model rewrite.** The old system-model draft still described a stale large-grid setting and an earlier execution-uncertainty framing. It was rewritten against the frozen 14-device full simulator and then mathematically closed around obligations, battery/cache dynamics, Class-A opportunities, backhaul/fallback, command lifecycle, partial observation, typed evidence and capability cost. The resulting authority was promoted into [`research/substrate/SYSTEM-MODEL-v1.md`](research/substrate/SYSTEM-MODEL-v1.md) and later moved under the substrate owner.

A7–A11-era method work changed the **research status** of this machinery while preserving the underlying system semantics. Persistent intent, asynchronous execution, plan expansion, ordinary dependency slicing, local fallback and related mechanisms were repeatedly attacked with strong controls. Components that ordinary deterministic infrastructure could provide were assigned to the shared substrate/compiler substrate. This separation is what made the later architecture possible: Layer 1 can vary tasks, Layer 2 can vary decision semantics, and Layer 3 can vary policy while all three face the same physical world.

### 3.2 Mathematical backbone

The current system model is a source-grounded hybrid simulator. Its central equations are explicit enough to connect an Agent decision to physical monitoring outcome.

A monitoring obligation is:

\[
o=(i,m,r_o,[s_o,e_o],d_o),
\]

where node/measurand, release time, legal sampling window and centre-delivery deadline are evaluator-owned. Timely delivery is measured from the original obligation set:

\[
TDR(\pi)=\frac{\sum_{o\in\mathcal O}I_o^{succ}}{|\mathcal O|}.
\]

Node energy evolves as:

\[
B_{i,t+1}=\min\left\{B_i^{max},\left[B_{i,t}+H_{i,t}-E^{sense}_{i,t}-E^{UL}_{i,t}-E^{DL}_{i,t}-E^{DtS}_{i,t}-E^{other}_{i,t}\right]^+\right\}.
\]

Solar forcing uses source-derived irradiance shape with an explicit deployment scale:

\[
H_{i,t}=\lambda_i\frac{G(t)}{G_{max}}\Delta t.
\]

The source cache retains unconfirmed records and applies acknowledgement, expiry and finite capacity:

\[
Q_{i,t+1}=Cap_{K_i}\left[(Q_{i,t}\setminus ACK_{i,t}\setminus EXP_{i,t})\cup S_{i,t}\right].
\]

LoRaWAN Class-A control opportunity is causally tied to uplink activity:

\[
U_{i,t}=1\Rightarrow W^{RX1}_{i,t+\Delta_1}=1,\qquad W^{RX2}_{i,t+\Delta_2}=1.
\]

A centre-originated device action also depends on centre→gateway and gateway→node reachability, so a correct decision and a physically applied configuration remain distinct events.

The overall world is represented as:

\[
x_{t+1}=F(x_t,a_t,\xi_t;\phi),
\]

with endogenous state containing battery, cache, configuration, link/execution, gateway and mission state; exogenous input contains harvest, temperature, stochastic link process, outage/access state and task revision. The Agent receives an owner-aware lawful projection; complete simulator truth remains evaluator-side:

\[
z_t=H(x_{\le t},a_{<t},\xi_{\le t},\ell).
\]

Typed evidence preserves proposition/value, provenance, owner, generation/observation time, revision, freshness semantics and status. Evidence-use and device-control capabilities share one contract:

\[
\mathcal K=\mathcal K^E\cup\mathcal K^A,
\]

\[
k=(I_k,O_k,Owner_k,Path_k,L_k,Bytes_k,E_k,Authority_k,Failure_k,Effect_k).
\]

A device-changing capability follows a physical lifecycle:

```text
REQUESTED → ACCEPTED/REFUSED → DELIVERED → APPLIED → CONFIRMED
```

so `NO_CONFIRMATION` does not imply `NOT_APPLIED`. This lifecycle later became essential to Evidence World, commitment semantics and the Layer-2 future-choice model.

The default objective is a physical/business vector:

\[
J(\pi)=(TDR,Collection,Latency,Energy,Bytes,Airtime,Survival,Recovery,\ldots).
\]

Operational sources may impose hard constraints or priorities. Scalar weights require an explicit Operational-Task/source authority.

### 3.3 What grounds each part

| Model component | Grounding / authority | Claim boundary |
|---|---|---|
| Terrain and spatial link feasibility | NASA SRTM1 terrain + ITM point-to-point propagation | deployment-oriented spatial feasibility; no claim of site-measured RF calibration |
| Temporal LoRa variation | ChirpBox-derived two-state temporal process | stress/burstiness distribution; Tibet-specific field fitting remains outside the current evidence |
| LoRa/Class-A receive opportunities | LoRaWAN Class-A receive-window semantics + repository-selected access configuration | Class A is the selected model configuration; cited deployments retain their own protocol scope |
| Solar/temperature forcing | NASA POWER hourly irradiance / T2M windows | forcing shape is source-derived; panel/controller size and harvest scale are deployment parameters |
| Sampling/radio energy | instance-v1 manifest + measured/declared device/radio profiles | operating point and sensitivity axes are reported as such |
| Monitoring cadence, cache/retransmission, warning/task semantics | geohazard standards, procurement/field material and source registry | sources justify the operational primitive/range; benchmark composition remains explicit |
| Primary/backup/DtS/access assist | existing simulator capabilities with source-backed engineering plausibility where available | per-path budgets/reliability remain declared-model quantities unless calibrated |
| Numeric deployment point | [`spec/substrate/instance-v1-manifest.md`](spec/substrate/instance-v1-manifest.md) + code checks | single numeric authority; README/paper should project from this owner |

Several parameters remain **declared research operating points**: frequency/channel choice, nominal battery capacity, selected uplink/backhaul probabilities, harvest scale, outage timing and some backup limits. The current simulator scope is source-grounded communication research and controlled sensitivity. A calibrated Tibet-site digital twin would additionally require dense-MAC/field RF evidence, site-certified regulatory configuration and field geotechnical calibration.

### 3.4 Optional hazard-to-task layer

Hazard physics is upstream of the communication Agent. The default benchmark begins at an externally authorised Operational Task. A secondary task generator may use mature external models:

\[
R(t),DEM,Soil\rightarrow Hydrology\rightarrow FS(t)\rightarrow ExternalAuthority\rightarrow OperationalTask.
\]

TRIGRS / infinite-slope physics can generate rainfall-induced pressure/stability trajectories; IMERG may provide rainfall forcing; Grfin may generate a post-initiation runout/damage mask. D-Claw-level two-phase debris-flow dynamics are reserved for a future study with calibrated geotechnical inputs. This boundary keeps the research question on communication decisions while allowing physics-grounded task generation when evidence supports it.

The detailed equations, implementation mapping and source boundaries live in [`research/substrate/SYSTEM-MODEL-v1.md`](research/substrate/SYSTEM-MODEL-v1.md); module lineage and owner rules live in [`research/substrate/README.md`](research/substrate/README.md).

## 4. Layer 1 — Source-grounded Emergency Communication Benchmark

### 3.1 Source grounding and benchmark construction

Real sources establish the legitimate problem space; the benchmark generator composes discriminative instances inside that space.

The current source corpus includes geohazard monitoring standards and operational material such as DZ/T 0450/0460, DB11/T 1677, DB44/T 2457, the 2024 Jiaozuo automated geohazard-monitoring procurement, the 2025 Yining near-disaster warning procedure, and Baoshan 1262 operational material. These sources support monitoring/reporting cadence, cache/retransmission requirements, authority chains, path priorities, device/state access and warning-delivery procedures.

Source-backed objects and generated challenge variables have separate provenance:

| Provenance | Role |
|---|---|
| `FIXED_BY_SOURCE` | directly fixed by a source |
| `SOURCE_RANGE` | sampled inside a source-supported range |
| `EMPIRICAL_TRACE` / `MODEL_DERIVED_TRACE` | derived from measurement or a declared physical model |
| `CONTROLLED_STRESS` | benchmark-authored stress condition, reported explicitly |
| `UNRESOLVED` | source gap; answer-relevant fields remain unavailable to generation |

The construction pipeline is fixed as:

```text
external operational corpus
→ canonical operational objects
→ Family Identity Test / taxonomy
→ source-profiled obligation contract
→ historical semantic dedupe
→ state / action / transition / oracle contract
→ simulator mapping / SIMULATOR_GAP
→ case generator
→ automatic validity / hardness filters
→ structure-aware split / scale-up
→ policy evaluation
```

This separation preserves both realism and benchmark authorship: sources establish task semantics, mechanisms, authority, capabilities and physical ranges; the generator controls timing, overlap, outage phase, resource headroom, evidence availability and other stress combinations within the declared contract.

### 3.2 Operational taxonomy

Layer 1 has two top-level families, determined by protected operational subject, completion predicate, authority owner/chain and lifecycle scope.

- **T1 · Monitoring Information Continuity** — the main family. Steady monitoring, warning cadence changes, intermittent backhaul, cache retention, recovery, heterogeneous paths and energy pressure are regimes inside one monitoring-information lifecycle.
- **T2 · Warning Delivery & Response Handoff** — an extension family whose protected subject and authority chain shift to warning authorization, publication, hierarchical delivery, acknowledgement and response handoff. Its source contract exists; its actor-chain simulator remains a declared `SIMULATOR_GAP`.

T1 currently exposes eight task surfaces: steady monitoring, warning cadence transition, intermittent backhaul/fallback, energy-constrained continuity, outage cache retention, recovery reconciliation, heterogeneous path priority and compound continuity. Historical O1–O6 retain conformance/regression roles; T1 and T2 remain the top-level families.

### 3.3 Decision semantics

A Layer-1 policy sees only lawful observation history:

```text
h_t(w) = h_t(w')  =>  π(h_t(w)) = π(h_t(w'))
```

The environment distinguishes local owner facts, passive telemetry/ACK, normal-send-as-probe, paid/remote query, sampled-at versus arrived-at time, gateway receipt versus final centre completion, historical fact versus current inference, and future state outside the queryable surface.

Core actions include `WAIT`, terrestrial send, satellite/fallback send, and legal evidence acquisition. Query, send and wait advance the same causal execution process: they consume time/opportunity/resources, create asynchronous feedback, update completion state and change future obligation feasibility.

### 3.4 EvidenceNeed and exact references

Information matters when compatible worlds require different commitments and lawful acquisition can improve the realizable strategy. Passive telemetry, ACK and normal-send feedback remain available to ordinary baselines.

Layer 1 retains four reference levels:

- hindsight physical feasibility;
- full-current-state oracle;
- observation-matched exact oracle;
- observation-matched no-paid-query oracle.

A set of worlds may be individually solvable while lacking any common non-anticipative strategy. Those cases are labelled `INFORMATION_INFEASIBLE` and remain separate from algorithm failure.

### 3.5 Validity, hardness and release

Automatic validity/hardness uses V0–V9: source completeness, solvability, multiple legal options, common-safe-action, observation relevance, binding constraint, outcome separation, objective definition, shortcut audit and evaluator soundness.

Typical dispositions include conformance (`UNIQUE_READY`), non-EvidenceNeed (`COMMON_SAFE_ACTION`), source gaps (`OBJECTIVE_AMBIGUOUS`), environment gaps (`SIMULATOR_GAP`), shortcut-covered regression (`SHORTCUT_SOLVED`) and evaluator repair (`EVALUATOR_INVALID`).

Hardness is carried by information and communication structure: observation sparsity, staleness, finite/non-nested opportunities, shared resources, deadline pressure, action irreversibility, overlapping obligations, recovery delay and long-horizon coupling.

The strong baseline floor includes local EDF/reserve, passive-only planning, normal-send-as-probe, fixed/periodic/batch reads, myopic VoI, shallow rule combiners, true depth-k belief planning, receding-horizon planning, generic/incremental exact search and ordinary dependency/cache optimization.

### 3.6 Current construction and admission status

Three lineages are retained for different reasons:

| Lineage | What it establishes | What it does not establish |
|---|---|---|
| v0.2 | one scoped H2×H3×H4 failure family and a first-irreversible-commitment atlas | benchmark-wide mechanism coverage or pristine generalization |
| v0.6 | auditable, byte-reproducible source/trace-driven generation | decision validity; all 1,262,790 variants collapse to a blind public satellite-only policy |
| v0.7 | corrected recovery/reinterruptible support semantics; candidate `TIGHT` removes the specific v0.6 satellite-only shortcut | placement-valid exact semantics, dynamic sufficiency, paid-evidence value, ordinary-baseline headroom or hard-case count |

The local audited v0.7 pre-oracle universe contains 103,408 base scenarios, of which 74,952 are `ALL_WORLD_PHYSICAL`; these expand to 2,023,704 variants / 863,460 pre-oracle structure IDs. These are generation counts only. No v0.7 case is currently admitted as hard.

The next gate is not another generator version or a full two-million-case exact sweep. The frozen v0.7 universe first needs an explicit gateway/center placement, visibility and control-path contract. The previous adapter charged a center-side remote query while exposing gateway receipts for free and omitted center control transport, so its pilots were discarded. Once placement is valid, the universe must expose the four `cache06.md` mechanism witnesses before staged exact classification.

Current authority:

- [`research/benchmark/LAYER1-AUTHORITY.md`](research/benchmark/LAYER1-AUTHORITY.md)
- [`research/benchmark/ENVIRONMENT-GENERATION-CONTRACT.v0.1.md`](research/benchmark/ENVIRONMENT-GENERATION-CONTRACT.v0.1.md)
- [`research/benchmark/GENERATION-AXES.v0.2.json`](research/benchmark/GENERATION-AXES.v0.2.json)
- [`results/benchmark/layer1-v0.7-shortcut-preflight.json`](results/benchmark/layer1-v0.7-shortcut-preflight.json)
- [`research/benchmark/V07-PLACEMENT-VISIBILITY-REVIEW.v0.1.md`](research/benchmark/V07-PLACEMENT-VISIBILITY-REVIEW.v0.1.md)

Current paper-facing comparison, construct coverage and frozen v0.2 distribution are generated in the module README:

- [Related benchmark landscape and links](research/benchmark/README.md#paper-facing-benchmark-landscape-and-statistics)
- [Layer-1 authority](research/benchmark/LAYER1-AUTHORITY.md)
- [Normative v0.2 contract](spec/benchmark/LAYER1-DECISION-BENCHMARK-v0.2.md)

## 5. Layer 2 — Decision-Semantic Compiler

Layer 2 compiles the current lawful task state into a structured decision surface:

```text
Operational obligations
+ lawful evidence history
+ capabilities / owner / transport
+ resources / opportunities / pending execution
        ↓
action legality and evidence validity
        ↓
future-choice feasibility surface
        ↓
L/U bounds + conditional frontier + exact fallback
```

The core research question is:

> Under intermittent communication, finite resources and asynchronous execution, how can the system acquire, combine and maintain enough evidence for critical communication decisions while preserving the future feasibility of the task?

A query has two simultaneous effects: epistemic uncertainty may shrink, while physical action space may also shrink because time and communication opportunity have been consumed. Evidence value is therefore tied to the feasible plans it changes.

The v2 method maintains delivery-feasibility conflict structure over obligations, opportunities/resources, evidence and pending execution. Conflict witnesses are derived from delivery constraints; evidence and execution events invalidate only the affected dependency region when that localization is sound.

For an action `a`, the deterministic layer maintains:

```text
L_t(a) <= V*(h_t, a) <= U_t(a)

L_t(a) = 1   executable causal success certificate exists
U_t(a) = 0   the declared relaxation certifies infeasibility
L=0,U=1      unresolved; acquire evidence, continue planning, or use exact fallback
```

Five correctness properties define the frozen boundary:

1. non-anticipativity;
2. reliable L/U bounds;
3. pruning preservation;
4. incremental update equivalence to full rebuild on the declared prefix scope;
5. separation of historical fact from current inference validity.

The current v2 deterministic core is frozen on dev. It has demonstrated exact-frontier preservation and substantial search-expansion reduction through conflict-aware/incremental structure, while raw wall time against the lean ordinary persistent-exact control remains an explicit negative/open systems boundary. Detailed machine state lives in [`research/compiler/README.md`](research/compiler/README.md).

## 6. Layer 3 — Policy and learning-guided exact search

Layer 3 operates only on the legal structured surface emitted by Layer 2. Its current unresolved set is:

```text
A_u(s) = { a | L(s,a)=0, U(s,a)=1 }
```

The active v0.1 line learns action ordering for exact search. Training preference is lexicographic: exact-feasible unresolved actions rank ahead of infeasible actions; within the same feasibility class, lower downstream exact proof/search cost ranks earlier.

The learned model never owns legality, evidence truth, oracle semantics or hard pruning. A ranking error may waste computation; exact fallback preserves the correctness contract.

Current v0.1 evidence is intentionally treated as a baseline/kill signal: full-dev frontier correctness is preserved, the first linear ranker yields only a very small expansion reduction, and its total wall time is worse than the ordinary persistent-exact control. The next research target models marginal search value from solver state and conflict structure; static local-action features remain the v0.1 reference.

Detailed status and machine artifacts are indexed in [`research/policy/README.md`](research/policy/README.md) and [`results/agentic/README.md`](results/agentic/README.md).

## 7. Evaluation and accounting

The repository separates three ledgers:

1. **Task / communication outcome** — obligation completion, deadlines, resource feasibility and physical execution.
2. **Information / acquisition cost** — local evidence reads, remote query/request/response, passive feedback and any explicitly modelled transport cost.
3. **Planner computation** — graph construction, bounds, flow/cut, memoization, incremental updates, exact fallback and model inference.

Uncalibrated bytes, airtime and energy remain explicitly unknown; action counts stay in their own ledger. Gateway-local evidence remains distinct from remote acquisition. Query and control paths obey their declared owner/transport constraints.

The main method target is a task-quality / communication / computation frontier: preserve or improve task feasibility under tighter communication and online-compute budgets while retaining exact correctness where claimed.

The long-term paper target has three linked deliverables:

- **Structure discovery:** identify which evidence/resource/temporal couplings change future feasible choices and where ordinary rules remain sufficient.
- **Algorithm property:** state when evidence can be reused, when local invalidation is sound, when acquisition can stop, and when exact global planning must resume.
- **Systems result:** move the achievable task-quality / communication / computation frontier under the source-grounded mountain-monitoring contract.


## 8. Related-work boundary

The surrounding ASC / agentic-communication literature already covers task-aware semantic transmission, active probing, iterative information acquisition, context lifecycle, intent-to-workflow compilation, memory reuse, dynamic pipeline reconfiguration, VoI send/no-send, world-model prediction, long-horizon physical consequence, counterfactual semantic value, freshness-aware value and online channel adaptation.

The repository therefore anchors its contribution in the combined decision contract above. The closest benchmark/system neighbours occupy different parts of that space:

- α³-Bench: interactive wireless-Agent control;
- 6G-Bench: standards-derived network reasoning and oracle decisions;
- GenSC-6G: physical semantic-link evaluation;
- RAMSemCom: active information acquisition under wireless cost;
- network-agent benchmarks such as NetConfArena / WirelessOpsAgent-style systems: executable closed-loop network actions and action assurance.

The maintained qualitative comparison matrix, paper links and local audit links live in the [Layer-1 paper-facing benchmark section](research/benchmark/README.md#paper-facing-benchmark-landscape-and-statistics). That matrix owns qualitative claim-boundary positioning; benchmark performance remains in each benchmark's own metrics.

## 9. Project evolution: from communication system to three-layer research stack

The current architecture emerged through repeated validity audits and strong-baseline attacks, with each surviving object assigned a stable owner.

```text
Stage A · physical communication system
real mountain-monitoring problem
→ terrain / energy / sampling / cache / access / backhaul / fallback
→ instance-v1 physical closure

Stage B · first benchmark-validity pivot
source / scenario / capability grounding
→ audit shows early workload contains little genuine decision freedom
→ method claim paused; task validity becomes a gate

Stage C · typed Agentic runtime and compiler
Operational Task / Authority / Evidence / Capability / Execution
→ live plan–evidence relation
→ persistent commitment and asynchronous execution
→ A7–A11 mechanism evidence

Stage D · second benchmark-collapse finding
strong checklist / ordinary controls solve decision-closed O1–O6 states
→ O1–O6 retained as conformance/mechanism assets
→ benchmark legitimacy and communication-policy freedom return to the centre

Stage E · current architecture
Layer 1 source-grounded decision benchmark
→ Layer 2 deterministic decision-semantic compiler
→ Layer 3 learnable/search policy
→ same shared physical substrate
```

The important continuity is the substrate. Earlier systems work produced real reusable assets—source-local expiry, local fallback, segment-specific execution evidence, finite cache, energy dynamics, opportunity-constrained control, store-and-forward, backup/DtS, persistent execution and physical scoring. Later work changed their ownership and scientific role. Ordinary deterministic mechanisms belong below the method claim; benchmark/compiler/policy research is evaluated on top of them.

The two benchmark-collapse episodes are also part of the research method. In September, an early task was rejected because its desired state was effectively known in advance and the workload reduced to writing a known configuration. In the later Agentic runtime stage, 123/123 formal decision points exposed exactly one ready supported plan, and a compiled checklist could match the physical reference. These failures motivated the current Layer-1 criterion: a Decision Benchmark must expose real operational grounding together with policy alternatives, partial evidence, resource conflict, temporal dependence and materially different physical outcomes.

The current three-layer split continues the old repo: the substrate carries physical truth, old conformance/mechanism work remains regression evidence, Layer 1 owns task legitimacy and hardness, Layer 2 owns deterministic semantics, and Layer 3 receives the genuine remaining choice space.

## 10. Current state and known boundaries

| Owner | Frozen / active boundary |
|---|---|
| Layer 1 | v0.6 is retained as reproducible negative lineage. v0.7 corrects only process-support semantics and passes the specific TIGHT satellite-shortcut preflight; exact admission is blocked until gateway/center placement, visibility and control transport are explicit. No current lineage is `BENCHMARK_ADMIT`. |
| Layer 2 | v1 remains the historical runtime/compiler baseline. v2 deterministic future-choice semantics are frozen after dev correctness and strong-control audits. |
| Layer 3 | paused. The previous learned search-ranking baseline is a negative historical result, not the current research line; no new Layer-3 method may shape Layer-1 generation. |
| Generalization | the historical seven-signature test was exposed during earlier Layer-2 work and now serves regression evidence. A new structural-generalization claim requires a preregistered holdout. |
| Deployment claims | benchmark guarantees apply to the declared model/process. Site-level reliability, bytes/airtime/energy savings and cross-site generalization require corresponding measurements or calibrated models. |

Machine results live under [`results/`](results/README.md). Claim state lives in [`results/CLAIMS.md`](results/CLAIMS.md). Numeric paper assets follow `result → generator → generated artifact`; root/module prose is a projection of that authority.

## 11. Authority map

| Authority | Owner |
|---|---|
| Current research ownership | [`research/README.md`](research/README.md) |
| Layer-1 direction and disposition | [`research/benchmark/LAYER1-AUTHORITY.md`](research/benchmark/LAYER1-AUTHORITY.md) |
| Layer-1 normative environment / action / oracle contract | [`spec/benchmark/LAYER1-DECISION-BENCHMARK-v0.2.md`](spec/benchmark/LAYER1-DECISION-BENCHMARK-v0.2.md) |
| Runtime/domain semantics | [`research/compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md`](research/compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md) |
| Mathematical system model | [`research/substrate/SYSTEM-MODEL-v1.md`](research/substrate/SYSTEM-MODEL-v1.md) |
| Deployment/data parameters | [`spec/substrate/`](spec/substrate/) |
| Claim truth | [`results/CLAIMS.md`](results/CLAIMS.md) |
| Result ownership | [`results/README.md`](results/README.md) |
| Reviewer reproduction | [`artifact/AE.md`](artifact/AE.md) |

## 12. Repository layout

```text
adaptive-communication/
├── research/                  research ownership and current semantics
│   ├── substrate/             shared communication/world model
│   ├── benchmark/             Layer 1
│   ├── compiler/              Layer 2
│   ├── policy/                Layer 3
│   ├── evaluation/            cross-layer evaluation contracts
│   ├── literature/            related work / source registry
│   └── history/               superseded tracked research authority
│
├── spec/                      normative contracts and deployment/data specs
│   ├── benchmark/
│   ├── substrate/
│   └── history/
│
├── code/
│   ├── substrate/             physical simulator and substrate tests
│   ├── agentic_communication/ typed runtime objects
│   ├── evaluation/            Layer-1/2/3 runners and audits
│   └── legacy-communication/  reproducible historical implementations
│
├── results/
│   ├── benchmark/             Layer-1 frozen evidence
│   ├── agentic/               Layer-2 / Layer-3 evidence and historical A* assets
│   ├── communication-substrate/
│   ├── reference/             frozen comparators
│   ├── history/               withdrawn/superseded result records
│   └── legacy-communication/
│
├── paper/                     manuscript lineage and generated paper artifacts
├── artifact/                  reviewer / reproduction entry points
├── scripts/                   result-to-paper and repository generation tools
├── tooling/                   reusable paper/repository tooling
├── archive/                   tracked historical executable bundles with frozen paths
├── data/                      acquired/generated workspace data (`make data`)
├── libs/                      acquired local dependencies (`make deps`)
└── local_research/            workspace-local current/lineage/episodes/archive and heavy provenance
```

`docs/` and `local_experiments/` are workspace compatibility symlinks into `local_research/archive/compat/`. New research material enters an owned module or one of the four local-research zones.

## 13. Build and checks

```bash
make deps
make data
make check
make tables ARGS=--check
make agentic-preapi
make paper
```

`make check` includes the Layer-1 paper-asset drift check. Benchmark figures and statistics are regenerated by `scripts/make_layer1_paper_figures.py` from frozen `results/benchmark` artifacts.

## 14. Paper and history

- Current buildable Agentic manuscript snapshot: [`paper/agentic/`](paper/agentic/README.md)
- Systems-paper compatibility copies: [`paper/en/`](paper/en/) and [`paper/zh/`](paper/zh/)
- Immutable manuscript history: [`paper/_archive/`](paper/_archive/)
- Current claim ledger: [`results/CLAIMS.md`](results/CLAIMS.md)
- Local research lineage and episodes: workspace-only `local_research/README.md`
- Tracked historical executable bundles: [`archive/`](archive/README.md)

Git preserves round-by-round changes. Current module READMEs preserve current ownership and state.
