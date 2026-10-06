English | [中文](README.zh.md)

# Agentic Communication under Intermittent Connectivity

Source-grounded decision benchmark, decision-semantic runtime, and policy learning for pre-disaster mountain monitoring under limited power and intermittent communication.

> **Current control plane:** Layer 1 is research-frozen on benchmark semantics; Layer 2 v2 deterministic future-choice semantics are frozen on dev; Layer 3 is the active method line for learned search guidance inside the frozen Layer-2 correctness boundary. Module state is owned by [`research/`](research/README.md).

## 1. System architecture

The original field requirement remains the root object: mountain monitoring nodes must keep useful sensing and return paths available through power scarcity, backhaul interruption, cache pressure, and recovery. External sources define operational obligations and capability boundaries. The repository turns those obligations into a causal communication decision problem and evaluates the resulting policy in one shared physical substrate.

```text
External operational sources / field requirement
                    │
                    ▼
┌──────────────────────────────────────────────────────────────┐
│ Layer 1 · Source-grounded Emergency Communication Benchmark │
│ Operational obligations · partial observation · actions     │
│ causal transitions · exact oracle · hardness · frozen split │
└──────────────────────────────┬───────────────────────────────┘
                               │ public task/evidence/action contract
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Layer 2 · Decision-Semantic Compiler                         │
│ Task / Evidence / Capability / Execution                    │
│ legality · evidence lifecycle · future-choice L/U frontier  │
│ incremental maintenance · exact fallback                    │
└──────────────────────────────┬───────────────────────────────┘
                               │ legal structured decision surface
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Layer 3 · Policy                                             │
│ deterministic/search/LLM/learned guidance                   │
│ current focus: unresolved-action ranking and search order   │
└──────────────────────────────┬───────────────────────────────┘
                               │ selected communication action
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Shared Communication Substrate                              │
│ LoRa/Class-A · gateway · cellular · BeiDou backup · cache   │
│ battery/harvest · outage/recovery · execution · scorer      │
└──────────────────────────────────────────────────────────────┘

Cross-cutting: evaluation / literature / result ledger / provenance
```

The three layers own different semantics. Layer 1 owns the problem. Layer 2 owns deterministic correctness and the legal decision surface. Layer 3 owns choice order inside that surface. The shared substrate owns physical execution and scoring.

## 2. Module ownership

| Module | Owns | Produces | Current state | Entry |
|---|---|---|---|---|
| **Shared substrate** | communication physics, energy, cache, opportunity, fallback, execution lifecycle, mathematical system model | state transition and physical outcome | stable shared base | [`research/substrate/`](research/substrate/README.md) |
| **Layer 1 · Benchmark** | source-grounded operational obligations, task construction, observation/action contract, oracle, validity/hardness, split/release | frozen benchmark instances and exact references | **research-frozen**; release gate remains Q11 human/source review | [`research/benchmark/`](research/benchmark/README.md) |
| **Layer 2 · Compiler** | Task/Evidence/Capability/Execution semantics, evidence validity, L/U future-choice frontier, incremental update, exact fallback | legal structured decision surface | **v2 deterministic core frozen on dev** | [`research/compiler/`](research/compiler/README.md) |
| **Layer 3 · Policy** | ordering and selection among legal/unresolved actions | search guidance / policy choice | **active**; learned ranking is under dev evaluation | [`research/policy/`](research/policy/README.md) |
| **Evaluation** | replay, attribution, ablation, baseline fairness, cross-layer audits | machine-checkable verdicts | cross-cutting | [`research/evaluation/`](research/evaluation/README.md) |
| **Literature** | related work and source registry | claim boundary and source traceability | cross-cutting | [`research/literature/`](research/literature/README.md) |
| **Research history** | superseded tracked research authority and roadmaps | provenance | frozen history | [`research/history/`](research/history/README.md) |

The current research object is:

```text
source-grounded operational obligation
+ action-relative evidence sufficiency
+ heterogeneous capability for evidence acquisition
+ intermittent long-horizon obligation feasibility
+ external causal oracle for action / completion validity
```

Paper-facing benchmark comparisons, related-work links, construct coverage, and v0.2 distribution figures are maintained by the Layer-1 module: [`research/benchmark/README.md`](research/benchmark/README.md#paper-facing-benchmark-landscape-and-statistics).

## 3. Current state

| Owner | Frozen / active boundary |
|---|---|
| Layer 1 | v0.2 research semantics, exact oracle, validity/hardness ladder, structure-aware split, paper-facing statistics are frozen. Formal public admission waits for Q11 real human/source review. |
| Layer 2 | v1 remains the historical runtime/compiler baseline. v2 deterministic future-choice semantics are frozen after dev correctness and strong-control audits. Raw wall time versus the lean ordinary persistent-exact control remains an explicit open/negative systems boundary. |
| Layer 3 | Learning may rank unresolved actions (`L=0, U=1`) and guide search/context. Legality, evidence ownership, L/U meaning, and exact fallback remain Layer-2 authority. |
| Generalization | The historical seven-signature test was exposed in earlier Layer-2 work and now serves regression evidence. A future structural-generalization claim requires a new preregistered holdout. |

Machine results live under [`results/`](results/README.md). Claim state lives in [`results/CLAIMS.md`](results/CLAIMS.md). Numeric paper assets follow a result → generator → generated artifact path.

## 4. Authority map

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

An authority file owns one semantic class. Generated README sections, figures, tables, and paper macros are projections of their source artifacts.

## 5. Repository layout

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

## 6. Build and checks

```bash
make deps
make data
make check
make tables ARGS=--check
make agentic-preapi
make paper
```

`make check` includes the Layer-1 paper-asset drift check. Benchmark figures and statistics are regenerated by `scripts/make_layer1_paper_figures.py`; numeric values are derived from frozen `results/benchmark` artifacts.

## 7. Paper and history

- Current buildable Agentic manuscript snapshot: [`paper/agentic/`](paper/agentic/README.md)
- Systems-paper compatibility copies: [`paper/en/`](paper/en/) and [`paper/zh/`](paper/zh/)
- Immutable manuscript history: [`paper/_archive/`](paper/_archive/)
- Current claim ledger: [`results/CLAIMS.md`](results/CLAIMS.md)
- Local research lineage and episodes: workspace-only `local_research/README.md`
- Tracked historical executable bundles: [`archive/`](archive/README.md)

Git preserves round-by-round changes. Current module READMEs preserve current ownership and state.
