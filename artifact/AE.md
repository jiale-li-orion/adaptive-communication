# Artifact Evaluation Guide

This is the reviewer's entry point. It states the environment, how to obtain the artifact, a short path that reaches one verdict, the full reproduction of each paper claim, and what this artifact does not do. The paper's claims and their current statuses are in [`results/CLAIMS.md`](../results/CLAIMS.md); the frozen values that verdicts compare against are in [`results/reference/`](../results/reference/README.md).

The document is in English because it is written for the artifact committee; the repository's own entry pages are bilingual.

## 1. Scope

The artifact is a Python simulation of a pre-disaster mountain geohazard monitoring deployment: sensor nodes over LoRaWAN Class A to a gateway, and a gateway to a centre over an intermittent cellular backhaul with a rate-limited BeiDou short-message backup. It contains the simulator, the experiment scripts, the result files, the normative specifications, and the two manuscripts.

Claims C1 to C7 are fully reproducible here without credentials and without network access beyond the one-time data acquisition. Claim C8 is a formative study whose live runs called an external model; only its zero-LLM offline replays are re-runnable, and its saved traces are provided.

## 2. Environment

Measured on the machine that produced the frozen reference results:

| Item | Value |
|---|---|
| OS | Ubuntu 24.04.3 LTS under WSL2 (Linux 6.6.87.2-microsoft-standard-WSL2) |
| CPU | 12 cores; single-threaded experiments |
| Memory | 7 GB |
| Python | 3.12.3 |
| Third-party packages | `numpy` 2.4.6 (system), `itmlogic` 1.2 (fetched into `libs/pylibs`) |
| GPU | not used |
| Disk | about 400 MB for the acquired data and packages, plus about 60 MB per clone of results |
| Network | required once for `make deps` and `make data`; not required afterwards |
| Credentials | none for C1–C7; `DEEPSEEK_API_KEY` only for re-running C8's live runs |
| Paper build | `pdflatex` (pdfTeX 3.14, TeX Live 2023) and `xetex`; see `paper/README.md` |

## 3. Obtaining the artifact

```bash
git clone https://github.com/jiale-li-orion/agentic-communication.git
cd agentic-communication
make deps     # itmlogic into libs/pylibs (idempotent)
make data     # SRTM terrain tiles and NASA POWER irradiance (idempotent, ~100 MB)
```

`docs/` is not part of the artifact; the normative material a reviewer needs lives in `spec/`. If a check finds an acquired dependency missing, it prints the command that fetches it rather than raising an unexplained error.

## 4. Getting Started

```bash
make check                     # 20 checks plus 5 joint-layer anchors
make tables                    # regenerate the paper tables from the result files
./artifact/reproduce_all.sh --only C1    # one full claim verdict, about 3 minutes
```

`make check` prints one PASS or FAIL line per check and exits non-zero on any failure. `make tables`
regenerates `paper/generated/`; `make tables ARGS=--check` only reports whether the committed tables
still match the result files. `reproduce_all.sh` re-runs the claim's script, then compares the result file against the frozen value with a relative tolerance and prints PASS or FAIL.

## 5. Repeating each claim

`./artifact/reproduce_all.sh` runs every claim; `--only C2 C5` restricts it; `--check-only` compares the existing result files without re-running anything.

| Claim | Command | Expected verdict | Time |
|---|---|---|---|
| C1 resource walls | `python3 code/v3joint/r30c_walls.py` | base 3025/7560 (0.4001); backhaul relaxed 4740; energy relaxed 4089; both 6023; decomposition 1715 backhaul-only, 1128 energy-only, 155 coupled, 4535 base failures | ≈3 min (measured) |
| C2 expiry equivalence | `python3 code/v3joint/r41_expiry_equiv.py` | `bit_identical_purge_generic_expiry` is `true`; ten-seed paired service gain +4.21 points, 95% CI +3.64 to +4.79; outage on-time 1691 → 4265; expired backup records 2538 → 1; gateway-only suppression gives 194 on-time at seed 0 | ≈3 min (estimated) |
| C3 cross-segment placement | `python3 code/v3joint/r37e_full_seeds.py` | ten-seed sweep; paired `deadline_purge` minus `fifo` mean +4.21 points with all ten positive; outage on-time total 1691 → 4265 (2.52×); expired 2538 → 1; purge dominates `latest_only` by +5.73 points, CI +5.06 to +6.39 | ≈15 min (measured) |
| C4 attribution correction | `python3 code/v3joint/r44_fullhorizon_attribution.py` | time-aware `S_energy` 2002, `S_cap` 1115, `S_access` 830, `S_time` 588; the 830 move from capacity to access relative to the earlier accounting | ≈1 min (estimated) |
| C5 delivery-bounded lease | `python3 code/v3joint/r46_lease_sweep.py`, `r47_lease_energy.py`, `r48_ttl_vs_lease.py` | geometric bound τ = 6.33 h (phase A) and 8.33 h (phase B); under overcast η = 0.012 the clock guard leaves 20 and 31 deaths while the lease reaches 0 in both phases; a fixed 4 h TTL falsely releases 183 yellow obligations in phase B; at η = 0.01 all arms incur about 40 deaths | a few minutes (estimated) |
| C6 enforcement placement | `python3 code/v3joint/r39_envelope.py && python3 code/v3joint/merge_r39.py` | naive centre compliance 39 deaths at service 0.162; with the node-local guard 0 deaths; envelope plus guard reduces refused admission attempts to 222; pure-local pre-provisioned rhythm reaches 0.360 | a few minutes (estimated) |
| C7 online attribution coverage | `python3 code/v3joint/r40_local_attribution.py` | of 2136 missed obligations, online coverage 0.5328 (1138 labelled) at labelled accuracy 1.000, with 998 unknown; offline truth `S_time` 588, `S_cap` 327, `S_access` 650, `S_energy` 571 | ≈1 min (estimated) |
| C8 agent interface fault | `python3 code/v3joint/r42_claim_relabel.py && python3 code/v3joint/r43_cert_v5_replay.py` | symmetric relabelling of 1089 decisions across 11 traces; 52 parse-failure holds; per-arm format-failure rates 7.1% / 6.4% / 1.3%; A0 and A0s assert "link up" on 36 and 32 in-outage decisions against 1 for A1 | ≈1 min (estimated) |

Timings were measured on the machine in section 2; entries marked estimated follow from the number of simulated seeds and have not been timed individually. Nothing in C1 to C8 requires a GPU.

The live A0/A0s/A1 runs behind C8 are **not** re-runnable without an API key. Their traces are committed under `results/agent_traces/`, and the relabelling and projector replays in the last row run over those traces deterministically.

## 6. What this artifact does not do

It does not reproduce the cited third-party systems; no author code was executed. It does not provide the end-to-end unknown-aware v5 agent runs, the matched-capability arm, or cross-model replication — those are stated as future work in the manuscripts and are not claimed. It does not include `docs/`, which is the authors' local process archive; the normative subset a reviewer needs is in `spec/`.

## 7. Normative material

| Content | Where |
|---|---|
| Deployment conditions (site, topology, time, energy, harvest, link, storage) | [`spec/instance-v1-manifest.md`](../spec/instance-v1-manifest.md) |
| Datasets: source, parameters, licence, acquisition, freeze rule | [`spec/datasets.md`](../spec/datasets.md) |
| Result registry: the script, command, seeds and denominator behind every number | [`results/README.md`](../results/README.md) |
| Claims and their current statuses | [`results/CLAIMS.md`](../results/CLAIMS.md) |
| Frozen verdict baselines | [`results/reference/`](../results/reference/README.md) |

## 8. Layout

| Path | Contents |
|---|---|
| `paper/` | English and Chinese manuscripts, shared bibliography, build script |
| `code/instance/` | Nodes, gateway, energy, exogenous obligations, scoring |
| `code/v3joint/` | Joint communication experiments, mission-view gate, agent harness |
| `code/physics/`, `code/analysis/`, `code/monitoring/`, `code/runtime/`, `code/experiments/` | Terrain and propagation, analysis, monitoring, earlier execution semantics, regression checks |
| `results/` | Result files and agent traces; `results/reference/` holds the frozen baselines |
| `spec/` | Normative specifications |
| `scripts/` | Acquisition scripts for the dependencies that are not in the repository |
