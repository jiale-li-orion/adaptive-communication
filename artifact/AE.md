# Artifact Evaluation Guide

This is the reviewer-facing entry point for the paper repository. It explains the current manuscript lineage, the authority hierarchy, the credential-free reproduction path, and the claim-by-claim verdict commands. Current claim state is defined only by [`results/CLAIMS.md`](../results/CLAIMS.md); frozen verdict baselines live under [`results/reference/`](../results/reference/README.md).

The repository contains two claim namespaces:

- `C*`: systems-paper / communication-substrate claims retained from the earlier manuscript line;
- `A*`: current Agentic Communication deterministic / infrastructure claims.

There is currently **no real-model performance claim**. The current Agentic manuscript freezes the model protocol and the R1/R3 runners, but no scripted consumer is accepted as an LLM result.

## 1. Scope and manuscript lineage

The physical scenario is pre-disaster mountain geohazard monitoring: battery/solar sensor nodes use LoRaWAN Class A to reach a gateway; the gateway uses cellular primary backhaul plus an uplink-only BeiDou short-message backup. Monitoring requirements and warning levels are externally authorised.

The active manuscript is [`paper/agentic/en/main.tex`](../paper/agentic/en/main.tex). The corrected systems-paper compatibility copies remain in `paper/en/` and `paper/zh/`; the exact pre-Agentic source snapshot is immutable under [`paper/_archive/system-paper-2026-09-20/`](../paper/_archive/system-paper-2026-09-20/README.md), sourced from commit `dd4f31a`.

The artifact supports three layers of reproduction:

1. **communication substrate (`C*`)**: physical mechanisms, ordinary baselines, claim corrections and scoped negative results;
2. **Agentic deterministic/infrastructure (`A*`)**: Runtime Task / Evidence World / Context / Capability wiring, replay, baseline isolation, robustness coordinates, task transfer, attribution and communication-baseline/oracle substrate;
3. **future live-model runs**: model-facing inputs and transport are present, but model performance is intentionally outside the current claim ledger until a real backend result is frozen.

## 2. Authority hierarchy

| Object | Authority |
|---|---|
| Current claim status | [`results/CLAIMS.md`](../results/CLAIMS.md) |
| Fresh result registry / allowed interpretation | [`results/README.md`](../results/README.md) |
| Frozen verdict baselines | [`results/reference/`](../results/reference/README.md) |
| Deployment/data provenance | [`spec/`](../spec/README.md) |
| Current Agentic experiment design | [`research/README.md`](../research/README.md) |
| Current mathematical system model | [`research/substrate/SYSTEM-MODEL-v1.md`](../research/substrate/SYSTEM-MODEL-v1.md) |
| Canonical runtime/domain ownership | [`research/compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md`](../research/compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md) |
| Current benchmark/runtime status | [`research/README.md`](../research/README.md), [`research/README.md`](../research/README.md) |
| Generated paper facts/tables | `paper/generated/`, produced from result files; never hand-edited |

The root README is an entry-page projection of these authorities, not a second claim ledger.

## 3. Environment and acquisition

The frozen artifact was developed on Ubuntu 24.04 under WSL2 with Python 3.12. GPU execution is not required for the credential-free experiments.

```bash
git clone https://github.com/jiale-li-orion/adaptive-communication.git
cd adaptive-communication
make deps
make data
```

`make deps` and `make data` acquire the dependencies/data declared by the repository. After acquisition, the credential-free claim checks require no model API. Local `docs/` and `local_experiments/` are author process areas and are deliberately excluded from the released artifact; normative/reproducible material needed by the reviewer is in `spec/`, `research/`, `code/`, `results/`, `paper/`, and `artifact/`.

## 4. Getting started

```bash
make check
make tables ARGS=--check
./artifact/reproduce_all.sh --check-only
```

`make check` runs repository-level semantic, monitoring, claim, paper, sequence-reference, Agentic-runtime and joint-layer gates. `make tables ARGS=--check` verifies that committed generated facts/tables match their result sources. `reproduce_all.sh --check-only` compares the current result files against the frozen claim references without rerunning long experiments.

To rerun one claim instead of only comparing the committed result:

```bash
./artifact/reproduce_all.sh --only C3
./artifact/reproduce_all.sh --only A2
```

To see every registered claim command:

```bash
./artifact/reproduce_all.sh --list
```

## 5. Systems-paper / communication-substrate claims (`C*`)

The table intentionally avoids duplicating paper numbers. The expected verdict is the semantic claim boundary in `results/CLAIMS.md` plus equality to the frozen reference. This prevents the artifact guide from becoming a third numeric source.

| Claim | Reproduction command | Expected verdict |
|---|---|---|
| C1 resource-wall characterisation | `python3 code/legacy-communication/v3joint/r30c_walls.py` | fresh result matches `results/reference/communication-substrate/claims/r30c_walls.json`; interpretation remains `scoped-negative` |
| C2 ordinary record-expiry equivalence | `python3 code/legacy-communication/v3joint/r41_expiry_equiv.py` | fresh result matches `results/reference/communication-substrate/claims/r41_expiry_equiv.json`; ordinary expiry equivalence remains supported |
| C3 cross-segment source-expiry placement | `python3 code/legacy-communication/v3joint/r37e_full_seeds.py` | fresh result matches `results/reference/communication-substrate/claims/r37e_full_seeds.json`; placement result remains supported under the registered cache/deadline semantics |
| C4 time-aware failure attribution | `python3 code/legacy-communication/v3joint/r44_fullhorizon_attribution.py` | fresh result matches `results/reference/communication-substrate/claims/r44_fullhorizon_attribution.json`; partial attribution remains evidence-bounded |
| C5 evaluated configuration-lease candidate | `python3 code/legacy-communication/v3joint/c5_matrix.py 0 1 2` | fresh matrix matches `results/reference/communication-substrate/claims/c5_matrix.json`; claim remains `scoped-negative` rather than a lease-algorithm gain |
| C6 local enforcement placement | `python3 code/legacy-communication/v3joint/r39_envelope.py && python3 code/legacy-communication/v3joint/merge_r39.py` | merged result matches `results/reference/communication-substrate/claims/r39_table.json`; result remains a placement/system property |
| C7 partial online attribution | `python3 code/legacy-communication/v3joint/r40_local_attribution.py` | fresh result matches `results/reference/communication-substrate/claims/r40_local_attribution.json`; unresolved evidence remains unknown |
| C8 historical live-Agent interface fault | `python3 code/substrate/joint/r42_claim_relabel.py && python3 code/substrate/joint/r43_cert_v5_replay.py` | deterministic replay outputs match their frozen references; historical live traces remain formative and are not current Agentic model evidence |
| C9 same-information non-prescient stopping | `python3 code/legacy-communication/v3joint/c5_seqref.py && python3 code/legacy-communication/experiments/measure_seqref_calibration.py` | both fresh files match their frozen references; the result remains scoped to the declared same-information single-node stopping family |
| C10 expiry-boundary correction | `python3 code/legacy-communication/analysis/retention_deadline_audit.py` | fresh audit matches `results/reference/communication-substrate/claims/retention_deadline_audit.json`; this is an implementation/semantic correction, not a new method |
| C11 conditional reverse-acknowledgement delay bound | `python3 code/legacy-communication/analysis/reverse_feedback_budget.py` | fresh audit matches `results/reference/communication-substrate/claims/reverse_feedback_budget.json`; aggregate opportunity capacity is not promoted into a no-contention theorem |

The old live model calls behind C8 are not required for the current deterministic replay verdict. Their committed traces are historical evidence; C8 remains `formative`.

## 6. Agentic Communication deterministic/infrastructure claims (`A*`)

Agentic claim references are compact aggregate + semantic-audit snapshots under [`results/reference/agentic/`](../results/reference/agentic/README.md). Several audit files contain `result_hashes` over timestamped run manifests/traces; `reproduce_all.sh` ignores only that non-semantic field while deep-comparing all aggregate values and all semantic audit verdict fields.

| Claim | Reproduction command | Expected verdict |
|---|---|---|
| A1 runtime / physics conformance | `python3 code/evaluation/agentic/run_o2_risk_escalation.py --variant global --seeds 0,1,2,3,4` and the same runner with `--variant localized` | global/localized aggregates and semantic audits match A1 references; paired physical equivalence and replay remain valid |
| A2 deterministic Agent/runtime baseline isolation | `python3 code/evaluation/agentic/run_o2_baseline_matrix.py --seeds 0,1,2,3,4` | aggregate/audit match A2 references; runtime/context overhead is isolated without being re-labelled as LLM gain |
| A3 source-period + five-axis robustness infrastructure | `python3 code/evaluation/agentic/run_source_period_smoke.py --seed 0 && python3 code/evaluation/agentic/run_robustness_matrix.py` | source-period and robustness verdicts match A3 references; this validates coordinates/infrastructure, not generic method robustness |
| A4 source-derived Operational Task transfer | `python3 code/evaluation/agentic/run_task_transfer_qili.py --seeds 0,1,2,3,4` | aggregate/audit match A4 references; task translation changes workload authority/schedule while keeping runtime/capability/scorer fixed |
| A5 attribution-protocol self-check | `python3 code/evaluation/agentic/run_attribution_matrix_infra.py --turns 20` | aggregate/audit match A5 references; cumulative gold replacement restores the declared layers without smuggling downstream gold state |
| A6 communication baselines and evaluator-only oracles | `python3 code/evaluation/agentic/run_communication_baseline_matrix.py --seeds 0,1,2,3,4` | aggregate/audit match A6 references; online controllers remain separated from evaluator-only oracle rows |

No `A*` claim says that an LLM beats deterministic baselines or improves the physical communication outcome. The model-facing protocol, three frozen context variants, R1 diagnostics and R3 runner are infrastructure awaiting real backend runs.

## 7. Pre-API benchmark suite

The complete credential-free current stack can be regenerated with:

```bash
make agentic-preapi
```

This covers O1–O6 catalog conformance, O2 global/localized, deterministic Agent baselines, ordinary communication baselines/oracles, NASA POWER source-period separation, five-axis robustness coordinates, source-derived Task transfer, attribution infrastructure and the frozen model-input matrix. It then checks generated artifacts and manifests.

For a shorter reviewer path, use `--check-only` against the committed frozen results. The long suite is intended for full artifact reproduction, not as a prerequisite for reading the paper.

## 8. What this artifact does not claim

- No current LLM performance result is claimed. Real-model runners require an external endpoint/key and fail explicitly if credentials are absent; there is no scripted fallback accepted as a model score.
- The generic VoI/active-acquisition baseline is not instantiated with arbitrary weights. It remains gated on a defensible evidence-acquisition latency/bytes/airtime/energy/opportunity-cost model.
- The current debris-flow/landslide physics is not an established hazard predictor. Hazard/flow models may generate upstream Operational Tasks only under their own validation boundary.
- Source-period and robustness gates validate benchmark/simulator coordinates; they are not evidence that a method is universally robust.
- Evaluator-only oracles may inspect information unavailable online and are never ranked as deployable policies.

## 9. Layout

| Path | Contents |
|---|---|
| `paper/agentic/` | current Agentic Communication manuscript |
| `paper/en/`, `paper/zh/` | corrected systems-paper compatibility copies |
| `paper/_archive/` | immutable paper/plan provenance snapshots |
| `code/agentic_communication/` | Task/Evidence/Context/Capability/Planner/Replay/Evaluation runtime |
| `code/substrate/instance/`, `code/substrate/joint/` | physical simulator and joint communication mechanisms |
| `code/evaluation/agentic/` | formal Agentic benchmark/baseline/robustness/attribution runners |
| `results/` | current registered results and sole claim ledger |
| `results/reference/` | frozen verdict baselines used by artifact reproduction |
| `results/history/withdrawn/` | superseded/defective historical result material with provenance |
| `spec/` | normative deployment/data/information-boundary contracts |
| `research/` | current Agentic experiment design, registries, roadmap and generated research summary |
| `scripts/` | result-to-paper and manifest generation |

Local `docs/` and `local_experiments/` are intentionally excluded from the release dependency graph. They contain research-process material, killed candidates, audit notes and one-off probes; current paper claims must not depend on them.
