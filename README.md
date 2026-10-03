English | [中文](README.zh.md)

> **Current line: Evidence-Grounded Closed-Loop Agentic Communication.** The method has two layers: (i) convert node/gateway/centre events from the existing communication Data Plane into a provenance-preserving **Evidence World** with owner/time/revision/freshness/reachability/status semantics; (ii) compile benchmark/business **Operational Tasks** into self-contained **Runtime TaskContracts / TaskRuns**, assemble `ContextManifest`s, perform multi-round evidence-use and communication-device capability calls, and execute decisions back on the physical simulator. [Experiment Design v1](research/README.md) is the design authority; [research/README](research/README.md) and [ROADMAP](research/README.md) record the current experiment state. [CLAIMS](results/CLAIMS.md) remains the repository's sole claim-state authority: `C*` denotes systems-paper/communication-substrate claims and `A*` current Agentic deterministic/infrastructure claims.

# Local Communication Control for Pre-Disaster Monitoring with Intermittent Backhaul

This repository studies battery/solar mountain geohazard monitoring: LoRaWAN Class A nodes reach a field gateway, which uses cellular backhaul and an uplink-only BeiDou short-message backup. Monitoring requirements and warning-level changes are externally authorised. The system executes their communication requirements.

**Original systems-paper line, now the substrate for the current research:** how should persistent communication state be handled when the control path fails, using only evidence available at the relevant location? Unacknowledged records continue to occupy retransmission batches, installed dense profiles continue consuming energy, and even a correct central decision may be impossible to install after backhaul loss. Earlier work studied source-local expiry, local fallback, segment-specific execution evidence and control-path failure. Those results, the simulator, the information boundaries and the execution mechanisms remain in force under the scopes registered in [CLAIMS](results/CLAIMS.md) and are reused as the common substrate for the Agent line.

**Historical systems-paper stage:** that stage produced component-level positive results and narrowed configuration leasing, single-node stopping and retention-horizon tuning into scoped-negative boundaries. The systems-paper compatibility copies, immutable archive, `CLAIMS`, Git and withdrawn-result snapshots preserve those design choices, negative results and open questions as part of the research lineage.

**Current research line:** on the same scenario, data, communication capabilities and execution substrate, construct an Evidence World and a complete Agent runtime, then evaluate Communication outcome and Agent-runtime quality together.

## 1. Current paper, historical manuscripts, and authority entry points

| Material | Entry |
|---|---|
| Current Agentic Communication manuscript | [English PDF](paper/agentic/en/main.pdf) · [LaTeX](paper/agentic/en/main.tex) · [workspace README](paper/agentic/README.md) |
| Systems-paper compatibility copies (still receive claim-correction propagation) | [English](paper/en/main.tex) · [Chinese](paper/zh/main.tex) · [paper/README](paper/README.md) |
| Immutable pre-Agentic systems-paper snapshot | [paper/_archive/system-paper-2026-09-20](paper/_archive/system-paper-2026-09-20/README.md) · source commit `dd4f31a` |
| Current Agent experiment design | [Experiment Design v1](research/README.md) · [research/README](research/README.md) · [ROADMAP](research/README.md) |
| Current mathematical system model | [SYSTEM-MODEL-v1](research/substrate/SYSTEM-MODEL-v1.md) |
| Runtime/domain ownership contract | [OWNERSHIP-v1](research/compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md) |
| Systems-paper completion plan (historical stage) | [RESEARCH_PLAN](paper/RESEARCH_PLAN.md) |
| Claim-by-claim reproduction | [artifact/AE.md](artifact/AE.md) |
| Provenance, claim states, deployment | [Results](results/README.md) · [CLAIMS](results/CLAIMS.md) · [spec](spec/README.md) |

The manuscript lineage is continuous. `paper/en|zh` remain corrected compatibility copies so the historical `C*` claims continue to build against current frozen semantics; `paper/_archive/system-paper-2026-09-20/` is an immutable source snapshot from before the Agentic pivot; `paper/agentic/` is the active submission workspace. README focuses on current state and long-lived authority, while Git, `results/history/withdrawn/`, `paper/_archive/`, and the author's local `docs/_archive/` preserve research history.

## 2. Repository authority and long-lived constraints

This repository is both an implementation and an evidence system. The following ownership rules recur across the README history, the current experiment design, and the [paper-repository standard](tooling/paper-repository/PAPER-REPO-STANDARD.md); future refactors continue to use the same authority structure.

| Authority / invariant | Current rule |
|---|---|
| Claim truth | `results/CLAIMS.md` is the sole claim-state authority; README presents its current projection |
| Numeric truth | Experimental numbers originate in `results/` and reach papers/generated facts through `scripts/make_tables.py` or `scripts/make_agentic_artifacts.py` |
| Scenario and parameters | `spec/substrate/instance-v1-manifest.md`, `spec/substrate/datasets.md`, and the source registry own deployment/data provenance; every method shares the same frozen scenario |
| Mathematical model | `research/substrate/SYSTEM-MODEL-v1.md` is the public equation/model authority; local `docs/` may retain derivation notes while release dependencies remain in the tracked tree |
| Runtime/domain ownership | `research/compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md` owns canonical Task/Evidence/Context/Capability/physical-substrate boundaries; parallel schemas and hidden-truth shortcuts are contract violations |
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

## 4. Current Agentic Communication system

The current work stays on the same mountain pre-disaster monitoring physical/data plane, and the benchmark is built directly on its execution chain:

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

**The two meanings of Task are frozen separately.** An Operational Task is benchmark/business semantics: what this mountain monitoring system must accomplish. A Runtime TaskContract is one Agent-harness execution instance: its targets, evidence contract, effect ceiling, temporal contract, and completion predicate. Each layer owns a stable schema and revision.

### 4.1 Operational Task catalog

O1–O6 share deployment, communication capabilities and scorer; they vary the business task or controlled disturbance rather than creating unrelated disaster questions.

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

## 5. Current reproducible evidence and claim projection

- **Source expiry:** under the corrected gateway deadline boundary, standard per-record expiry remains a supported cross-segment placement result in the tested cache model. Numeric effect sizes and paired intervals are owned by the frozen result / generated paper table rather than this entry page. [C3 data](results/communication-substrate/claims/r37e_full_seeds.json)
- **Configuration termination:** a fixed TTL covers the candidate's survival and yellow-delivery operating points in the two tested phases. The energy-derived candidate collapses to the ordinary mechanism frontier, and ordinary combinations match the same-information exact stopping reference across the declared risk-weight sweep. [Matrix](results/communication-substrate/claims/c5_matrix.json) · [Reference](results/communication-substrate/claims/c5_seqref.json)
- **Online knowledge:** under the corrected deadline boundary, legal gateway evidence supports a correct-but-partial attribution interface while unresolved obligations remain unknown; exact counts/rates are owned by the frozen result / generated table. [C7 data](results/communication-substrate/claims/r40_local_attribution.json)
- **Agent interface:** historical live traces expose bidirectional errors caused by interpreting LoRa receipts as backhaul state. Offline v5 replay improves statements; C8 keeps this evidence at the formative-interface level. [C8 entry](results/CLAIMS.md)

Resource relaxations characterise capacity and energy pressure within the tested strategy family. C10 records the expiry-boundary implementation correction. Subsequent comparisons use corrected ordinary expiry.

Current states below are a checked projection of [CLAIMS](results/CLAIMS.md); that file remains the ledger of record.

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

The `A*` namespace now contains deterministic/infrastructure claims plus narrowly scoped A7–A11 model-effect claims. A7 covers query-negative development tasks; A8 shows the same-interface WirelessOpsAgent-style reliability tie with 35.804% higher total model-token cost than the Method; A9 adds held-out Qili/NASA-POWER-2024 transfer across DeepSeek Flash and MiMo v2.6 Flash. A10 closes the previously missing query-positive loop on one gateway-backup family with DeepSeek Flash. A11 repeats the same frozen acquisition loop with MiMo v2.6 Flash: 5/5 episodes preserve the deterministic query-positive physical reference and improve TDR/AoI versus no acquisition. These claims establish a two-model witness for one acquisition family, not globally optimal or universal evidence acquisition.

## 6. Frozen Agentic paper state

The pre-API stack remains the deterministic/fairness substrate, but the current paper state has moved beyond it. A7–A11 are frozen live-model claims spanning the v6 main table, a same-interface WirelessOpsAgent-style strong comparison, held-out Qili/NASA-POWER-2024 transfer, and a query-positive gateway-backup acquisition loop reproduced with DeepSeek Flash and MiMo v2.6 Flash. The paper-level compact numeric authority is `results/agentic/paper-v1/paper-results.json`; the complete claim ceiling remains `results/CLAIMS.md`.

`make agentic-preapi` is the single credential-free entry point. It reruns catalog conformance, O2 global/localized, the five-arm Agent matrix, ordinary communication baselines, source-period, robustness, task transfer, attribution infrastructure and frozen model inputs, then checks generated artifacts/manifests. The full repository gate and JointControlPlane anchor gate both pass.

Three model-facing inputs are frozen under `results/agentic/model-context-inputs-v1/`: task-conditioned, FullDump, and generic-ReAct. They share the same Operational Task, capability surface and paired physical reference. generic-ReAct deliberately omits EvidenceNeed / InvestigationState harness artifacts so future model comparison can isolate harness cognition rather than mixing different tool surfaces.

The next stage is paper freeze and repository release, not another model search. The current novelty boundary is intentionally narrow: dynamic plan/dependency liveness, separation of audit/control/model surfaces, persistent semantic commitment, communication-constrained owner acquisition, and asynchronous physical execution/replay. Generic decision-aware acquisition, action sufficiency, certificate minimization, provenance witness selection, and VoI/freshness are treated as prior art rather than rebranded novelty. A frozen-input basis-selection headroom audit found no real alternative-proof choice in the current paper workloads, so that side study is closed.

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

The current Agentic manuscript and historical systems-paper copies share [refs.bib](paper/refs.bib). [Build notes](paper/README.md) describe the role and build path of all manuscript trees. Tables and factual macros are generated from result files by `scripts/make_tables.py` / `scripts/make_agentic_artifacts.py`, with `paper/generated/` owned by that generation chain.

`make check` covers simulation, execution semantics, claims, tables, the stopping reference, Agent runtime and joint-layer anchors. `make agentic-preapi` reruns the credential-free Agent/communication substrate; A7–A11 live-model artifacts are frozen separately and represented in compact aggregate/audit/result files rather than raw traces. Claim-level commands and frozen references are in [artifact/AE.md](artifact/AE.md) and [results/reference](results/reference/README.md).

## 9. Repository map

| Path | Contents |
|---|---|
| `paper/agentic/` | current Agentic Communication manuscript |
| `paper/en/`, `paper/zh/` | systems-paper compatibility copies; still receive claim-correction propagation, while `paper/agentic/` owns the active submission positioning |
| `paper/_archive/` | immutable manuscript/plan snapshots, including the pre-Agentic systems-paper source |
| `spec/` | deployment, information boundaries and active experiment contracts |
| `research/` | current Experiment Design, registries, benchmark split, baseline/robustness/attribution protocols and research entry points |
| `code/substrate/instance/`, `code/substrate/joint/` | physical simulation, joint communication mechanisms and Agent interface |
| `code/agentic_communication/` | self-contained Task/Evidence/Context/Capability/Planner/Replay/Evaluation runtime |
| `code/analysis/`, `code/experiments/` | diagnostics, reproduction and checks |
| `results/` | registered results, sole claim-state ledger, frozen references and withdrawals |
| `artifact/`, `scripts/` | reviewer entry, dependency acquisition and the result-to-paper pipeline |

## 10. Remote repository versus local research zones

The repository follows [PAPER-REPO-STANDARD](tooling/paper-repository/PAPER-REPO-STANDARD.md): clone-verifiable, one numeric source, one current state per claim, traceable history. The remote repository contains paper-relevant implementation, specifications, compact frozen results, generated artifacts and auditable archives. Large `runtime_trace.jsonl` files, live-model per-run logs, workspace-local `local_work/`, compatibility `docs/`, and `local_experiments/` remain local/acquired research artifacts and are excluded from the release tree.

Local research zones may contain Astra reviews, killed candidates, one-off probes, HTML snapshots and early paper sandboxes. Promotion to the remote repository follows four gates: current normative dependency, stable owner, formal runner/result-registry use, and `make check` success. Assets that satisfy the gates join the formal tree; the rest stay as local provenance.

README presents the **current system state and long-lived authority**. Git/archive preserve round-by-round history, and `results/CLAIMS.md` supplies the current claim-state projection.
