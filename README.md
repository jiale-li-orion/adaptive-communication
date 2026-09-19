English | [中文](README.zh.md)

# Terminating Installed Communication State When the Control Path Dies

**Deadline Expiry and Delivery-Bounded Configuration Leases for Intermittent Pre-Disaster Monitoring**

This repository contains the simulation implementation and the result registry for a pre-disaster mountain geohazard monitoring system, together with the English and Chinese manuscripts. The studied deployment is battery-plus-solar LoRaWAN Class A: field nodes reach a gateway over LoRaWAN Class A, and the gateway reaches the centre over a cellular primary backhaul with a BeiDou short-message backup. The backup link is intermittent, metered, and uplink-only.

## 1. Manuscripts

| Manuscript | Source | Built | Pages |
|---|---|---|---|
| English | [`paper/en/main.tex`](paper/en/main.tex) | [`paper/en/main.pdf`](paper/en/main.pdf) | 9 |
| Chinese | [`paper/zh/main.tex`](paper/zh/main.tex) | [`paper/zh/main.pdf`](paper/zh/main.pdf) | 14 |

The two manuscripts are independent documents with section-by-section correspondence, and they share [`paper/refs.bib`](paper/refs.bib). Build with:

```bash
cd paper && ./build.sh            # build both; ./build.sh en|zh builds one
```

The English manuscript is built with `pdflatex` and IEEEtran. The Chinese manuscript is built with XeTeX (`xetex -fmt=xelatex`, Noto Serif CJK SC), because the target environment provides no `xelatex` command and none of the `ctex`, `xeCJK`, `luatexja` or `CJK` packages. On first run the build script generates a format file with `xetex -ini -etex` and caches it under `paper/.build/`.

## 2. Abstract

When a mountain-site backhaul fails, the network keeps executing communication state that was installed before the failure. Unacknowledged records keep filling the few recovery access batches, and a dense sampling configuration that can no longer be countermanded keeps draining a battery overnight. We study where, and on what evidence, these two forms of **persistent installed state** can be terminated. One decision problem, local termination under partial evidence, covers both: a node holding only its clock, battery, cache, recent access receipts and install-time bounds decides to retain or release a record and to hold or relax a configuration, under no-false-release, energy-survival, locality and no-false-completion constraints. A record's termination time is its business deadline, which the node knows unconditionally; the resulting source-local rule is bit-identical to standard Bundle-Protocol per-record expiry, and its cross-segment placement decides the gain. Source-local expiry raises outage on-time delivery from 202 to 434 and 2.52-fold over ten seeds, whereas suppressing expired sends at the gateway alone back-pressures the access segment. A configuration's termination time is not locally observable, because it depends on mission revisions travelling the failed path and on return-slot geometry held at the gateway. A clock night-guard leaves 20 to 31 deaths under overcast skies. Earlier preloaded revert bounds avoid those deaths; a fixed 8 h TTL also preserves aggregate yellow delivery with zero deaths in both tested phases. The proposed **delivery-bounded lease** still needs online validation: current experiments compute its bound from the future downgrade time and preload it at initialisation. The record-expiry and placement results remain supported; the online lease increment is open in [the claim ledger](results/CLAIMS.md).

## 3. The failure studied

After a backhaul failure the network keeps running: communication state installed before the failure is still executing, and the control and acknowledgement path required to terminate it has failed at the same time. Two phenomena are reproducible. First, unacknowledged cached records are retransmitted oldest-first under the standard hold-until-acknowledged edge discipline, so records past their business deadline keep occupying the scarce recovery access batches; a gateway that stops sending without releasing the source cache pushes the cost onto the access segment, moving outage on-time delivery from 202 down to 194. Second, a dense sampling configuration already in effect cannot be countermanded once the backhaul fails, and keeps draining the battery overnight; under overcast skies with tight energy the nodes discharge fatally, while a downgrade command issued by the centre envelope cannot be installed because the downlink is unavailable.

The paper unifies these two objects as **persistent installed state**: **record state** (unacknowledged samples) and **configuration state** (the applied sampling and reporting profile). This is a communication problem independent of any agent.

## 4. System model

**Obligations and the delivery chain.** A monitoring obligation $o=(n,m,[l_o,h_o),d_o)$ is defined over node $n$ and measurand $m$; a routine obligation at period $P$ satisfies $h_o-l_o=P$ and $d_o=h_o+P$. A sample fulfils $o$ only if it matches the measurand, is taken in-window, and is received centrally by $d_o$, traversing four stages: a qualified sample at the node, being heard at the gateway (LoRa access), being returned before $d_o$ (cellular or short message), and arriving at the centre as evidence. For piecewise missions the first segment uses a closed interval and later segments half-open windows.

**Deployment and operating point.** Fourteen nodes in two groups monitor slope displacement and rainfall. The backup carries one 78-byte packet every 1200 s; a displacement sample is 6 B and rainfall 4 B, so roughly 9 to 10 samples fit per packet. The elevated (yellow) task uses a 300 s period with a delivery window of about 600 s, shorter than the 1200 s backup slot spacing. LoRa access succeeds per opportunity with $p_a{=}0.74$, and the primary backhaul is good with $p_b{=}0.62$ outside a declared outage. Node count, role mapping and disturbance parameters follow the frozen Task v1.1 instance manifest.

**Control outage.** An outage is an interval $\mathcal O=[a,b)$ during which the primary is unavailable to centre-to-field traffic: centre commands and mission-table segments are refused at admission and never transmitted, and the short-message backup cannot carry downlink configuration. During $\mathcal O$ only the node and the gateway can change field communication behaviour: the node acts on its own clock, battery, cache, recent access receipts and the bounds carried by already-applied commands; the gateway acts on samples it has actually heard, its forwarding log and backup slots used. The centre retains authority to authorise changes but has no channel through which to install them.

**Energy.** A sample costs $e_s{=}4.7{\times}10^{-4}$ Wh and an uplink $e_u{=}2.33{\times}10^{-5}$ Wh; battery capacity is $C{=}0.05$ Wh. Solar input is a 12 h half-sine with a nominal peak of 0.03 Wh/h plus stochastic cloud occlusion. Holding dense sampling through a 12 h night draws about 0.071 Wh, exceeding battery capacity; a node whose state of charge reaches zero dies permanently.

**Release time and four constraints.** For each state $x$, the release time $t_{\mathrm{rel}}(x)$ is the earliest time after which keeping $x$ alive can no longer contribute to a fulfilled obligation. For a record this is its business deadline, $t_{\mathrm{rel}}(s)=d(s)$. For a configuration, the draft proposes a bound using the last feasible return slot and obligation deadlines; its relationship to the earliest safe time to stop new acquisition remains unvalidated, since acquired samples can still be forwarded after acquisition is relaxed. During an outage an entity chooses `retain` or `release` for a record and `hold` or `revert` for a configuration, minimising unfulfilled obligations, node deaths and the resource cost of state that outlives its release time, subject to:

- **C1 no false release**: release or downgrade must not precede $t_{\mathrm{rel}}(x)$;
- **C2 energy survival**: the state of charge never reaches zero, which is absorbing in the main configuration;
- **C3 locality**: an action is a function only of the evidence the entity lawfully holds at that time; future mission-table segments, simulator-wide samples and backhaul truth are excluded;
- **C4 no false completion**: under unknown feasibility the system reports unconfirmed or unfulfillable, and never reports fulfilment or unreachability.

**Three statement classes.** Every feasibility claim is confirmed (an independent report shows the target profile, or a matching sample is received centrally), unconfirmed (a command is in flight or receipts are incomplete, which implies neither that it took effect nor that the channel is down), or unreachable (the current path is known down from explicit network-side state). A LoRa access receipt is evidence about the access link only and can never by itself establish backhaul reachability.

**The key asymmetry.** A record's release time is locally certain from the public cadence. A configuration's release time depends on **mission revisions**, which reach the field only over the failed backhaul, and on **return-slot geometry**, which only the gateway holds; neither is observable at the node during an outage. This asymmetry is the technical centre of the paper.

## 5. Claims and mechanisms

**Records: standard expiry, with the gain in cross-segment placement.** At each upload opportunity the node deletes cached records with $d(s)\le t$ and sends survivors oldest-first, implemented as `deadline-purge` and `generic-expiry`. The latter is an ordinary BPv7-style per-record lifetime, $\text{expires}=t_s+((P-t_s\bmod P)+P)=d(s)$, referencing no obligation id, slot geometry or certificate. The two are bit-identical on every seed, so the record mechanism is standard per-record expiration and no new discard algorithm is claimed. The system-level content is an end-to-end business-deadline basis, rather than packet age or a hop TTL; zero-downlink source placement; and cross-segment consistency, since the acknowledgement coupling means a gateway-only release does not free the source cache. EDF and obligation-greedy queues only reorder and never release; AoI `latest-only` releases indiscriminately, buying outage freshness by abandoning post-recovery coverage.

**Configurations: a proposed delivery-bounded lease.** The experiments demonstrate local reversion at a supplied absolute time. The candidate bound is computed from the full mission schedule and installed at node initialisation, not transmitted with a versioned configuration command. Its upward slot rounding also differs from the latest-feasible-slot equation. Online derivation from lawful install-time evidence, command-carried installation and an increment over ordinary mission-validity expiry remain unvalidated. The implemented local guard is clock-based; a node-local SoC guard remains a required ordinary comparator.

**Feasibility projection and statement discipline.** At compile time the centre holds the obligation table, the current and never-forecast network-side outage state, and public parameters; at mission-table arrival the gateway holds only what it has heard. A structural no-return certificate is emitted from slot geometry alone and is explicitly conditional on the primary being unavailable; geometry never infers an outage. An arrival-time projector labels a missed obligation only when local evidence separates the stages, and otherwise returns unknown.

**What is not claimed.** No advantage of an LLM over a solver, no new discard algorithm and no global scheduling upper bound. The deterministic mechanisms are in-layer tools available equally to rules, solvers and agents.

## 6. Key results

- **Resource walls (a negative result scoped to the tested policies).** In Episode I the strong baseline delivers 3025 of 7560 obligations (0.400); relaxing backhaul alone gives 4740, relaxing energy alone 4089, and both 6023. Backhaul capacity alone blocks 1715 obligations, battery alone 1128, and both 155 (2.0%). The large throughput gains are physical, which is why the paper targets state termination rather than a more elaborate scheduler.
- **Full-horizon attribution correction.** Charging the 4535 failures with "heard" required by the deadline rather than at any later time gives energy 2002 (44.1%), capacity 1115 (24.6%), access 830 (18.3%) and time 588 (13.0%). An earlier accounting had charged those 830 late-access failures to backhaul capacity (1945/0). The delivered count of 3025 is identical under both accountings; the correction changes where the loss is charged.
- **Record expiry.** Source-local expiry raises full-horizon service from 0.373 to 0.415 (paired +4.21 points, 95% CI +3.64 to +4.79, positive on all ten seeds), outage on-time delivery from 1691 to 4265 (2.52-fold), reduces expired backup records from 2538 to 1 and deaths from 12 to 0, and leads `latest-only` by 5.73 points. Gateway-only suppression moves outage on-time delivery from 202 down to 194.
- **Configuration termination.** At the overcast peak $\eta{=}0.012$, the clock guard leaves 20 and 31 deaths in phases A and B. Both the candidate preloaded bound and fixed TTL 8 h have zero deaths and the same aggregate yellow-delivery counts (849 and 2020). Mean final SoC in phase A is 0.122 versus 0.117; phase B ties at 0.122. A smaller mean final SoC is not a violation of the declared survival constraint. TTL 4 h loses 183 yellow deliveries in phase B and TTL 6 h loses 26. These data do not exclude a fixed TTL that succeeds in both phases, or establish a slot-derived online lease advantage.

## 7. Reproducibility

Two controlled episodes are used. **Episode I** is the v1.1 manifest operating point: an upgrade at $t{=}6$ h, an outage from 4 to 20 h, and the mission table reaching the gateway at 20 h; it supports the resource walls, attribution, record expiry, enforcement placement and agent results. **Episode II** was constructed to isolate configuration termination: phase A upgrades at $t{=}2$ h with a downgrade at $t{=}6$ h and an outage from 4 to 20 h, and phase B upgrades at $t{=}1$ h with a downgrade at $t{=}8$ h and an outage from 6 to 22 h; $t{=}0$ is 06:00 local and $t{=}12$ h is sunset. The two episodes share all parameters except the schedule, the outage phasing and the swept harvest. Episode II is a controlled construction and not a new field claim.

```bash
make deps     # third-party packages not in the repository (idempotent)
make data     # terrain tiles and irradiance data (idempotent, about 100 MB)
make check    # 20 checks in four groups, plus 5 joint-layer anchors
make paper    # build both manuscripts
make tables   # regenerate the paper tables from the result files
```

`make check` covers four groups: **mechanism** (execution semantics and the frozen mechanism-isolation experiment), **monitoring** (the business-loop simulator), **claims** (the claim table: every claim names an existing script and reference result), and **paper** (the manuscripts' tables are generated from result files rather than typed in). After the two acquisition steps, nothing needs network access or credentials.

| Claim | Paper object | Script | Result |
|---|---|---|---|
| C1 | Resource walls and the fixed-resource negative result | `code/v3joint/r30c_walls.py` | `results/r30c_walls.json` |
| C2 | Expiry equivalence with standard per-record lifetime | `code/v3joint/r41_expiry_equiv.py` | `results/r41_expiry_equiv.json` |
| C3 | Cross-segment placement: ten-seed paired gain | `code/v3joint/r37e_full_seeds.py` | `results/r37e_full_seeds.json` |
| C4 | Full-horizon time-aware attribution | `code/v3joint/r44_fullhorizon_attribution.py` | `results/r44_fullhorizon_attribution.json` |
| C5 | Delivery-bounded lease against fixed TTL, two phases | `code/v3joint/r46_lease_sweep.py`, `r47_lease_energy.py`, `r48_ttl_vs_lease.py` | `results/r46_lease_sweep.json`, `results/r47_lease_energy.json`, `results/r48_ttl_vs_lease.json` |
| C6 | Enforcement placement: centre against node | `code/v3joint/r39_envelope.py` | `results/agent_traces/r39_table.json` |
| C7 | Attributable fraction at mission-table arrival | `code/v3joint/r40_local_attribution.py` | `results/r40_local_attribution.json` |
| C8 | Formative agent study and the interface fault | `code/v3joint/r38_agent_three_arm.py`, `r42_claim_relabel.py`, `r43_cert_v5_replay.py` | `results/agent_traces/r38_three_arm_summary.json`, `results/r42_claim_relabel.json`, `results/r43_cert_v5_replay.json` |

The script, convention and denominator behind every number are registered in [`results/README.md`](results/README.md), and any new result file must be registered there. [`results/CLAIMS.md`](results/CLAIMS.md) carries every claim with its script, reference result and one current status; [`artifact/AE.md`](artifact/AE.md) is the reviewer's entry point, with a per-claim command and expected verdict; [`results/reference/`](results/reference/README.md) holds the frozen values those verdicts compare against. Manuscript tables are generated by `scripts/make_tables.py` into `paper/generated/` and included with `\input`; the generated files are committed and never hand-edited. Real-model experiments require `DEEPSEEK_API_KEY` and must account for requests, retries and parsing, since the number of decisions is not the number of successful requests.

## 8. Repository layout

| Path | Contents |
|---|---|
| `Makefile` | Four entry points: `check`, `paper`, `tables`, `data` |
| `paper/` | LaTeX sources, PDFs, shared bibliography and build script; `paper/generated/` holds the generated table bodies |
| `spec/` | Normative specifications: deployment conditions and dataset provenance |
| `artifact/` | Reviewer entry point: `AE.md`, `reproduce_all.sh`, `compare_result.py` |
| `scripts/` | Acquisition scripts for dependencies that are not in the repository, the table generator, and `new_paper_repo.sh` |
| `template/` | Skeleton for a new paper repository, instantiated by `scripts/new_paper_repo.sh` |
| `PAPER-REPO-STANDARD.md` | The maintenance standard this repository is the reference implementation of, plus the Chinese version |
| `code/instance/` | Nodes, gateway, energy, exogenous obligations and scoring; `network.py` holds the cache discipline, the local clock night-guard and the lease executor, all off by default |
| `code/v3joint/` | Current joint communication experiments, the mission-view gate, the agent harness, and the r37 to r48 rounds |
| `code/physics/`, `code/analysis/`, `code/monitoring/`, `code/runtime/`, `code/experiments/` | Terrain and propagation models, trajectory analysis, monitoring simulation, earlier execution semantics and historical comparisons |
| `results/` | Result files and agent traces; `README.md` is the registry, `CLAIMS.md` the claim table, `reference/` the frozen verdict baselines and `_withdrawn/` the withdrawal list |
| `data/`, `libs/` | Raw data and dependencies, prepared locally according to the acquisition notes and not version-controlled |

This repository doubles as the reference implementation of [`PAPER-REPO-STANDARD.md`](PAPER-REPO-STANDARD.md) (Chinese: [`PAPER-REPO-STANDARD.zh.md`](PAPER-REPO-STANDARD.zh.md)), a reusable convention for repositories whose primary product is a paper. Four invariants drive it: the clone is verifiable, numbers have one source, claims have one current status, and history is immutable; each is paired with a mechanical check. To start a new paper repository from the same skeleton, run `./scripts/new_paper_repo.sh <directory>`: it copies `template/`, takes the audit and comparison mechanisms from this repository so there is a single implementation, runs one example experiment end to end, and verifies the wiring with `make check` before reporting.

## 9. Scope and future work

The resource walls and the throughput negative result are scoped to the policy families and the single operating point tested; they are not an optimality theorem. Configuration experiments cover five harvest levels in phase A and two in phase B. They establish effects of supplied revert times; online lease derivation and installation remain open, and fixed TTL 8 h succeeds in both phases by the reported counts. Wider sweeps of backup rate and payload, node count, capacity, cloud model and restart thresholds remain open. Episode II is a controlled scenario for the configuration sub-problem, independent of field measurement; central acknowledgement is modelled as synchronous and airtime-free, a simplification that equally favours every queue rule.

**End-to-end and cross-model reruns remain to be completed by the authors.** Once the unknown-aware v5 certificate (which proposes adding a network-side `primary_backhaul_state` field to the observation), hardened accounting and the symmetric scorer are in place, the multi-seed A0, A0s and A1 runs will be repeated together with a new **matched-capability arm** that receives the same day/night policy, geometry constants, confirmation rules and note template but no segment projector. The residual deaths will then be reassessed with the local safety floor wired end to end, followed by cross-model replication. The harness is in place; this repository does not claim those results.

**Scenario and evidence discipline.** The scenario is fixed to pre-disaster mountain monitoring, and risk levels and authorisation are externally given (DZ/T 0460-2023 §5.3.3 permits remote adjustment of sampling and upload frequency by warning level, §8.4.1 defines four levels and §8.4.2 governs conferral of upgrades and downgrades; the specific periods are research choices. Backup rate and payload follow BDS-OS-PS-3.0 and DZ/T 0450-2023, where 1200 s and 78 B are declared research choices). Judging landslide risk is out of scope, as is deleting an obligation or changing the denominator. Baseline fairness forbids strawman comparisons, tuning to win, and relaxing the criterion or tightening the task to save a method; gains from ordinary rules, MPC and standard mechanisms count as communication-system contributions, and any part already covered by an ordinary combination is closed as such. Sources are graded A/B/C/D and unverified material does not enter the fact table.

Historical documents, round-by-round audit records and commit provenance are maintained locally and are not distributed with this repository; the index is the local `docs/_archive/README.md`.
