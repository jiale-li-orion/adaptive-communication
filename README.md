English | [中文](README.zh.md)

> **Current work direction (exploratory).** The active line is **Evidence-Grounded Closed-Loop Agentic Communication**. The repository now contains a self-contained `TaskContract / EvidenceNeed / Capability / Percept / InvestigationState / ContextManifest` runtime, communication-domain bindings, full-simulator execution and typed runtime traces. See [research](research/README.md) and the [roadmap](research/ROADMAP.md). [CLAIMS](results/CLAIMS.md) remains the historical experimental claim ledger.

# Local Communication Control for Pre-Disaster Monitoring with Intermittent Backhaul

This repository studies battery/solar mountain geohazard monitoring: LoRaWAN Class A nodes reach a field gateway, which uses cellular backhaul and an uplink-only BeiDou short-message backup. Monitoring requirements and warning-level changes are externally authorised. The system executes their communication requirements.

**Original systems-paper line, now the substrate for the current research: how should persistent communication state be handled when the control path fails, using only evidence available at the relevant location?** Unacknowledged records continue to occupy retransmission batches, installed dense profiles continue consuming energy, and even a correct central decision may be impossible to install after backhaul loss. Earlier work studied source-local expiry, local fallback, segment-specific execution evidence and control-path failure. Those results, the simulator, the information boundaries and the execution mechanisms remain in force under the scopes registered in [CLAIMS](results/CLAIMS.md) and are reused as the common substrate for the Agent line.

**Historical systems-paper stage: communication-systems working draft.** That stage produced component-level positive results while also showing that configuration leasing, single-node stopping and retention-horizon tuning do not carry new-algorithm claims. At the time, an independent runtime increment over same-component ordinary combinations, limited transfer validation and matched-capability Agent validation remained incomplete. The design choices, negative results and unfinished items remain documented in the [paper completion plan](paper/RESEARCH_PLAN.md) and [CLAIMS](results/CLAIMS.md); they are retained rather than erased by the current direction change.

**Current research line: Evidence-Grounded Closed-Loop Agentic Communication on the same scenario, data, communication capabilities and execution substrate.** The method has two layers: (i) convert the physical/data plane into a typed, provenance-preserving Evidence World with owner/time/revision/freshness/reachability/status semantics; (ii) compile benchmark-level Operational Tasks into self-contained Runtime TaskContracts/TaskRuns, assemble versioned ContextManifests, perform multi-round evidence-use and communication-device capability calls, and execute decisions back on the physical system. Communication outcome and Agent-runtime quality are evaluated together. The experiment-design authority is [Experiment Design v1](research/EXPERIMENT-DESIGN-v1.md); build order is in the [roadmap](research/ROADMAP.md).

## 1. Reading entry points

| Material | Entry |
|---|---|
| English manuscript | [PDF](paper/en/main.pdf) · [LaTeX](paper/en/main.tex) |
| Chinese manuscript | [PDF](paper/zh/main.pdf) · [LaTeX](paper/zh/main.tex) |
| Current Agent experiment design | [Experiment Design v1](research/EXPERIMENT-DESIGN-v1.md) · [research/README](research/README.md) · [ROADMAP](research/ROADMAP.md) |
| Systems-paper completion plan (historical stage) | [RESEARCH_PLAN](paper/RESEARCH_PLAN.md) |
| Claim-by-claim reproduction | [artifact/AE.md](artifact/AE.md) |
| Provenance, claim states, deployment | [Results](results/README.md) · [CLAIMS](results/CLAIMS.md) · [spec](spec/README.md) |

## 2. Technical object and established evidence

A monitoring obligation requires an in-window sample, LoRa access to the gateway and central receipt before its deadline. Record retention, installed configuration, gateway receipt and central completion are distinct execution states. Missing evidence remains unknown.

**Local action can require less information than complete diagnosis.** A gateway may be unable to distinguish an absent sample from one not yet heard, while its source can still expire a record against a known deadline. An authorised local fallback can act on local energy without awaiting a command over the failed backhaul. Placement therefore depends on evidence, authority and the remaining response time.

| Object | Evidence | Role in the paper |
|---|---|---|
| Source expiry and cross-segment retention | Standard expiry releases the source cache; gateway-only suppression can back-pressure access | Main positive system result (C2/C3) |
| Configuration fallback placement | Local ordinary protection handles some downgrades unreachable from the centre; ordinary combinations cover the tested stopping problem | Placement principle and boundary (C5/C6/C9) |
| Partial execution evidence | Online attribution is incomplete; access receipts do not establish backhaul delivery | Interface and formative Agent analysis (C4/C7/C8) |

The system uses mature primitives. Its contribution must be demonstrated through composition, execution placement and physical outcomes. A unified name or an Agent interface alone does not establish a method increment.

## 3. Representative results

- **Source expiry:** under the corrected gateway deadline boundary, relative to FIFO over ten paired seeds, on-time service improves by **3.59 percentage points**, 95% CI **[+3.00, +4.19]**; outage on-time delivery increases **2009→4227 (2.10×)**, expired backup records decrease **2100→0**, and deaths **12→0**. This is a placement result for standard per-record expiry in the tested cache model. [C3 data](results/r37e_full_seeds.json)
- **Configuration termination:** a fixed TTL covers the candidate's survival and yellow-delivery operating points in the two tested phases. The energy-derived candidate has no independent benefit. Ordinary combinations also match the same-information exact stopping reference across the declared risk-weight sweep.
  [Matrix](results/c5_matrix.json) · [Reference](results/c5_seqref.json)
- **Online knowledge:** under the corrected deadline boundary, at task-table arrival legal gateway evidence attributes **1114/2112 obligations (52.7%)**, with all labelled cases correct; **998** remain unknown. This supports a partial evidence interface. [C7 data](results/r40_local_attribution.json)
- **Agent interface:** live traces expose bidirectional errors caused by interpreting LoRa receipts as backhaul state. Offline v5 replay improves statements; independent end-to-end effects remain unestablished. [C8 entry](results/CLAIMS.md)

Resource relaxations characterise capacity and energy pressure; they are not upper bounds over all schedulers. C10 is an expiry-boundary implementation correction. Subsequent comparisons use corrected ordinary expiry.

Current states below are a checked projection of [CLAIMS](results/CLAIMS.md), not a separate ledger.

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

## 4. Current experiment stage

The project no longer searches for a new toy perception case as a prerequisite for building experiments. Work now proceeds directly to the unified harness: `Operational Task -> Runtime TaskContract -> Evidence World / Context -> capability use -> physical execution -> Communication × Agent metrics`. The 09-28–10-01 action-closure and resource-negative results remain useful benchmark-validity checks, ordinary baselines and ablations; they no longer block harness construction, LLM benchmarking or full-simulator runs.

The pre-API experiment stack is now closed end to end. O1–O6 Operational Tasks execute through the same typed runtime and full simulator; O2 global/localized R3, R0/R1/R2 replay, ModelRequest/Attempt/Usage ledgers, upstream/planner gold replacement and attribution evaluation are implemented. The Agent side has a formal 5-seed matrix for deterministic comply, task-conditioned evidence-aware, diagnosis-first, fixed-order eager and generic-ReAct; the communication side has a 5-seed matrix for Local, AoI, EnergyAware, mission-comply, backup EDF/maxcov and evaluator-only dynamic/delivery oracles. NASA POWER 2022/2023/2024 source-period gates, five-axis weather/outage/scope/owner/scale robustness, S14/Qili source-derived Task transfer and three frozen model-context variants have also passed their audits. No scripted backend is presented as a model result. The next stage is live-model evaluation: R1 frozen-input diagnosis first, then R3 physical consequence and failure attribution.

## 5. Scenario and scope

The [instance manifest](spec/instance-v1-manifest.md) defines deployment, sources and parameters. The main point has fourteen nodes, finite Class A windows and sparse short-message return opportunities. Remote sampling/reporting changes are legal; autonomous hazard assessment, deletion of difficult obligations and automatically granted extra satellite resources are outside the action space.

Synchronous airtime-free central acknowledgements, synthetic harvesting and absorbing brownout in the main configuration limit deployment extrapolation. Episode I studies an upgrade, outage and recovery. Episode II isolates fallback across two authorised upgrade/downgrade phases. The exact stopping reference assumes a public task table, declared energy process and quantised single-node state; it does not establish optimality for unknown missions or a full network.

## 6. Build and reproduce

```bash
make deps
make data
make check
make tables ARGS=--check
make agentic-preapi
make paper
```

Both manuscripts share [refs.bib](paper/refs.bib). English uses pdflatex and Chinese uses XeTeX; see [build notes](paper/README.md). Tables and factual macros are generated by `scripts/make_tables.py` from result files. Do not hand-edit `paper/generated/`.

`make check` covers simulation, execution semantics, claims, tables, the stopping reference, Agent runtime and joint-layer anchors without model API calls. `make agentic-preapi` reruns every current credential-free Agent/communication baseline, source-period gate, robustness coordinate, task-transfer experiment, attribution infrastructure and model-input freeze, then regenerates the controlled research/result documentation from result JSON. Claim-level commands and frozen references are in [artifact/AE.md](artifact/AE.md) and [results/reference](results/reference/README.md). Live model runs require an endpoint/key; missing credentials fail explicitly rather than falling back to a scripted backend.

## 7. Repository map

| Path | Contents |
|---|---|
| `paper/` | Bilingual sources, PDFs, bibliography, generated tables and the current paper plan |
| `spec/` | Deployment, information boundaries and active experiment contracts |
| `code/instance/`, `code/v3joint/` | Physical simulation, joint communication mechanisms and Agent interface |
| `code/analysis/`, `code/experiments/` | Diagnostics, reproduction and checks |
| `results/` | Registered results, sole claim-state ledger, frozen references and withdrawals |
| `artifact/`, `scripts/` | Reviewer entry, dependency acquisition and the result-to-paper pipeline |

The repository follows [PAPER-REPO-STANDARD](PAPER-REPO-STANDARD.md). Git and withdrawal archives retain historical conclusions. Local `docs/` contains research-process material and is not part of the release; this entry page presents the current state.
