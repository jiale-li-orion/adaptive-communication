English | [中文](README.zh.md)

> **Current work direction (exploratory).** The active line is **candidate-direction exploration**, not a new claim. The question under test: can an Agent contribute anything where the trusted task authority does not already fix execution — that is, interpreting operator requirements that are not yet fully structured, and requesting exactly the information whose resolution would change a legal plan, under intermittent backhaul? This is exploratory work in progress. No result here is published, no claim status changes, and the closed lines (configuration leasing, single-node stopping, retention-horizon tuning) stay closed; [CLAIMS](results/CLAIMS.md) remains the sole claim-state ledger. Directions under evaluation, entry conditions and open questions are kept in the [research plan](paper/RESEARCH_PLAN.md).

# Local Communication Control for Pre-Disaster Monitoring with Intermittent Backhaul

This repository studies battery/solar mountain geohazard monitoring: LoRaWAN Class A nodes reach a field gateway, which uses cellular backhaul and an uplink-only BeiDou short-message backup. Monitoring requirements and warning-level changes are externally authorised. The system executes their communication requirements.

**Paper focus: acting on persistent communication state after the control path fails.** Unacknowledged records continue occupying retransmission batches; applied dense profiles continue consuming energy. A correct central decision may be impossible to install. The paper studies source-local release, local configuration fallback and segment-specific execution evidence.

**Current stage: a communication-systems working draft.** Component-level positive results are available. An independent increment over a same-component ordinary stack, limited transfer validation and matched-capability Agent evaluation remain to be established. Configuration leasing, single-node stopping and retention-horizon tuning no longer carry new-algorithm claims. See the [research and completion plan](paper/RESEARCH_PLAN.md); [CLAIMS](results/CLAIMS.md) is the sole current claim-state ledger.

## 1. Reading entry points

| Material | Entry |
|---|---|
| English manuscript | [PDF](paper/en/main.pdf) · [LaTeX](paper/en/main.tex) |
| Chinese manuscript | [PDF](paper/zh/main.pdf) · [LaTeX](paper/zh/main.tex) |
| Technical choices and remaining evidence | [RESEARCH_PLAN](paper/RESEARCH_PLAN.md) |
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

- **Source expiry:** relative to FIFO over ten paired seeds, on-time service improves by **4.04 percentage points**, 95% CI **[+3.48, +4.60]**; outage on-time delivery increases **1691→4145 (2.45×)**, expired backup records decrease **2538→120**, and deaths **12→0**. This is a placement result for standard per-record expiry in the tested cache model. [C3 data](results/r37e_full_seeds.json)
- **Configuration termination:** a fixed TTL covers the candidate's survival and yellow-delivery operating points in the two tested phases. The energy-derived candidate has no independent benefit. Ordinary combinations also match the same-information exact stopping reference across the declared risk-weight sweep.
  [Matrix](results/c5_matrix.json) · [Reference](results/c5_seqref.json)
- **Online knowledge:** at task-table arrival, legal gateway evidence attributes 1138/2136 obligations (53.3%), with all labelled cases correct; the remainder stays unknown. This supports a partial evidence interface. [C7 data](results/r40_local_attribution.json)
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

## 4. Remaining work

**Primary research direction: Agent task planning and communication execution.** The present live harness mainly selects per-node periods from an already structured mission. The next discriminator is whether plan repair tied to outstanding obligations improves the same Agent over matched expert tools and ordinary guards. It need not beat the strongest deterministic controller to establish an Agent-system benefit. See [the Agent research brief](paper/AGENT_RESEARCH.md).

1. **Composition:** fix the planner and resources; compare a same-component ordinary stack with evidence-driven action admission. Both receive expiry, local protection, shadows and deterministic tools. Measure service, harm, actual communication cost and rejected beneficial actions.
2. **Transfer and deployment:** select a small set of existing outage phases, access/backhaul failures and harvesting conditions. Report required firmware capabilities and byte/storage cost; avoid a full Cartesian sweep or new scenario.
3. **Agent integration:** compare the same Agent with matched expert rules versus the runtime, sharing observations, tools, local protection and parsing budgets. Isolate the effect with one model before cross-model confirmation.

**Secondary research entry: retention responsibility under a finite reverse-channel budget.** The current simulator clears source records synchronously and without airtime when the centre receives them. An uplink-only backup does not automatically provide that feedback. The hypothesis concerns acknowledgement/custody receipts and configuration messages sharing Class A opportunities, with ordinary custody, cumulative/bitmap ACKs and piggybacking as strong comparators. First establish that the budget binds; charging formerly free feedback is not itself a method gain.

**Validation and new search remain separate.** Matched-capability v5 action-interface validation continues as unfinished existing work; joint control-opportunity admission remains paused. The [plan](paper/RESEARCH_PLAN.md) excludes previously tested leasing, stopping, retention, probing and conditional-plan directions and specifies prior art and entry conditions for the new hypothesis.

## 5. Scenario and scope

The [instance manifest](spec/instance-v1-manifest.md) defines deployment, sources and parameters. The main point has fourteen nodes, finite Class A windows and sparse short-message return opportunities. Remote sampling/reporting changes are legal; autonomous hazard assessment, deletion of difficult obligations and automatically granted extra satellite resources are outside the action space.

Synchronous airtime-free central acknowledgements, synthetic harvesting and absorbing brownout in the main configuration limit deployment extrapolation. Episode I studies an upgrade, outage and recovery. Episode II isolates fallback across two authorised upgrade/downgrade phases. The exact stopping reference assumes a public task table, declared energy process and quantised single-node state; it does not establish optimality for unknown missions or a full network.

## 6. Build and reproduce

```bash
make deps
make data
make check
make tables ARGS=--check
make paper
```

Both manuscripts share [refs.bib](paper/refs.bib). English uses pdflatex and Chinese uses XeTeX; see [build notes](paper/README.md). Tables and factual macros are generated by `scripts/make_tables.py` from result files. Do not hand-edit `paper/generated/`.

`make check` covers simulation, execution semantics, claims, tables, the stopping reference and joint-layer anchors without model API calls. Claim-level commands and frozen references are in [artifact/AE.md](artifact/AE.md) and [results/reference](results/reference/README.md). Live model runs require credentials and separate decision, request and parsing-failure accounting.

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
