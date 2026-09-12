# Verified evidence log (first-hand, 2026-09-12)

Everything below was checked directly against live endpoints/APIs from this machine.
Items marked **VERIFIED** were reproduced by an actual HTTP query or file inspection.

---

## 1. FEMA TEMPO — TEMPO_Communication_Impacts  **VERIFIED**

- Service: `https://gis.fema.gov/arcgis/rest/services/TEMPO/TEMPO/MapServer/4`
  Feature service: `.../FeatureServer/4`, layer name `TEMPO_Communication_Impacts`.
- Source of record: FCC **DIRS** (Disaster Information Reporting System), aggregated to **county level**, **daily** during an incident.
- Schema (fields confirmed by querying the FeatureServer):
  `event`, `name` (county), `state_abbr`, `cnty_fips`, `population`,
  `cell_sites_served`, `cell_sites_out`, `percentout`, `percent_out`,
  `cell_sites_out_due_to_damage`, `cell_sites_out_due_to_power`,
  `cell_sites_out_due_to_transpor`, `populationaffected`, `lastupdatedon`.
- Row count: **1237** county-day records.
- Events present: `HurricaneA`, `Nicole`, `Karen`, `Ida`, `Fiona`, `Ian` — **all 2022**.
- **Data-quality defect found:** `date_` is **null for all 1237 rows** (epoch 0). `lastupdatedon`
  is null for **414/1237** rows, and those 414 rows are **exactly all of the `Ida` event**.
  ⇒ The Ida timeline is **not recoverable** from this layer as published.
- Usable lifecycle events: **Ian (477 rows, 2022-09-29→10-07), Fiona (234 rows, 2022-09-19→09-23)**,
  plus small Karen (32), Nicole (34), HurricaneA (46).
- Only **15 distinct days** exist in the whole layer.

### Ian (Hurricane Ian, Florida) per-day aggregate — real recovery curve
| day | sites out | due to damage | due to power | counties reporting |
|---|---|---|---|---|
| 2022-09-29 | 1740 | 188 | 808 | 122 |
| 2022-09-30 | 1096 | 25 | 751 | 61 |
| 2022-10-01 | 779 | 12 | 493 | 88 |
| 2022-10-02 | 445 | 11 | 260 | 51 |
| 2022-10-03 | 305 | 10 | 167 | 31 |
| 2022-10-04 | 249 | 7 | 148 | 31 |
| 2022-10-05 | 153 | 12 | 89 | 31 |
| 2022-10-06 | 122 | 15 | 78 | 31 |
| 2022-10-07 | 103 | 12 | 71 | 31 |

- Ian: 88 counties total, **61 counties present on ≥3 days**; median outage-days per county **3**, max **9**.
- Top-30 counties by `cell_sites_served` represent **14,040 cell sites** — a plausible node set.
- Fiona: 78 counties, only 3 reporting days (09-19, 09-20, 09-23), captures the **degradation ramp**
  (8.5% → 30.9% mean percent-out) rather than the recovery tail.

**Verdict:** usable as a **county-level, ~daily, cause-attributed outage/recovery trace**; combine
Fiona (ramp) + Ian (tail) to get a full lifecycle. Weaknesses: county granularity (no per-site),
sparse and irregular day coverage (needs interpolation), 2022 only, one event unusable.

Raw file: `tempo_comm_impacts.json`

---

## 2. ITU Disaster Connectivity Map (DCM)  **VERIFIED — visualization only**

- Portal `https://dcm.itu.int/` is a **GeoServer-backed WMS viewer**.
- Layer inventory pulled from `.../geoserver/dcm_prod/wms?service=WMS&request=GetCapabilities`:
  **64 layers**, including time-enabled:
  - `dcm_prod:dcm_scr_1hr_1km` — **1-hour step, 2013-01-11 → present**
  - `dcm_prod:dcm_scr_24hr_1km` — daily, same span
  - `dcm_prod:dcm_mix_archive_2020/2021/2022_1hr_allscales` — hourly archives
  - `dcm_prod:Latest Connectivity By Hour` — 2025-10-20 → present, PT1H
- Style/title metadata shows the layers carry **latency (ms)**, **download speed (Mbps)**,
  **upload speed (Mbps)** and **point coverage**.
- **WFS is disabled:** `service=WFS&request=GetCapabilities` →
  `ServiceException: Service WFS is disabled`.
- `GetFeatureInfo` is **blocked by a server-side style defect**:
  `The requested Style can not be used with this layer. The style specifies an attribute named 'map_scale', not found in ...`
  A query on `dcm_mix_archive_2022_1hr_allscales` returned
  `{"type":"FeatureCollection","features":[],"numberReturned":0}`.
- Underlying sources linked from the DCM page: **Ookla Open Data** (`teamookla/ookla-open-data`,
  AWS `registry.opendata.aws/speedtest-global-performance`), Meta Data for Good network coverage maps,
  Collins Bartholomew, JRC NetBravo.

**Verdict:** **not** a clean bulk-download trace. Extractable only by rendering tiles and reading pixels,
or by going to the open upstream sources (Ookla on AWS S3). Not a first-choice dependency.

Raw files: `dcm.html`, `dcm_wms_caps.xml`

---

## 3. IODA (Internet Outage Detection and Analysis, Georgia Tech)  **VERIFIED — strongest find**

- API base: `https://api.ioda.inetintel.cc.gatech.edu/v2/`
- `GET /outages/events?from=<epoch>&until=<epoch>` → outage **events** with
  `location`, `start`, `duration`, `datasource`, `method`, `score`, `fraction`, `status`.
  (`from` is mandatory; omitting it returns HTTP 400.)
- `GET /signals/raw/<entityType>/<entityCode>?from=&until=&datasource=<ds>` → raw time series,
  **`step: 300` (5-minute granularity)**.
- Data sources available: `bgp`, `merit-nt`, `gtr`, `gtr-norm`, `gtr-sarima`,
  `ping-slash24`, `ping-slash24-loss`, `ping-slash24-latency`,
  `upstream-delay-penult-asns`, `upstream-delay-penult-e2e-latency`, `mozilla`.
  (`datasource` takes a **single** value; a comma list is rejected.)
- Entity types confirmed working: **country** (e.g. `country/PR`) and **ASN** (e.g. `asn/7922` →
  `AS7922 (COMCAST-7922)`, `ip_count` 68,238,848). Region entities exist but use **NetAcuity numeric
  codes** (`entities/query?entityType=region` → code `"1"` = Aruba), and `region/PR`, `region/US-FL`
  return `cannot find corresponding metadata entity`.
- Free, no API key observed. Copyright notice: © 2021–2025 Georgia Tech Research Corporation.

### Puerto Rico / Hurricane Fiona 2022 — measured lifecycle, merit-nt, 5-min step
Request: `signals/raw/country/PR?from=1663286400&until=1664755200&datasource=merit-nt`
(4896 points, 2022-09-16 00:00 → 2022-10-02 23:55 UTC)

| date | daily min | daily mean |
|---|---|---|
| 2022-09-16 | 1.0 | 3.5 |
| 2022-09-17 | 1.8 | 3.4 |
| **2022-09-18** | **0.0** | 2.3 |
| 2022-09-19 | 0.0 | 1.0 |
| 2022-09-20 | 0.0 | 1.5 |
| 2022-09-21 | 0.4 | 1.8 |
| 2022-09-22 | 0.4 | 2.1 |
| 2022-09-23 | 1.2 | 2.8 |
| 2022-09-24 | 2.0 | 3.4 |
| 2022-09-25 | 0.8 | 2.6 |
| 2022-09-26 | 1.2 | 3.1 |
| 2022-09-27 | 1.0 | 4.1 |
| 2022-09-28 | 2.4 | 5.1 |
| 2022-09-29 | 2.4 | 4.8 |
| 2022-09-30 | 3.4 | 5.6 |
| 2022-10-01 | 2.8 | 5.6 |
| 2022-10-02 | 3.6 | 6.2 |

⇒ textbook **degradation (09-18) → total outage (09-18→09-20, min = 0) → partial recovery (09-21→09-23)
→ restored/above-baseline (09-30→10-02)** at **5-minute resolution**.

- IODA event API for PR returns two corroborating events:
  `country/PR` `bgp` start 2022-09-18T16:40Z, **duration 339.42 h**;
  `country/PR` `ping-slash24` start 2022-09-18T16:50Z, **duration 343.17 h**.
- BGP signal for PR is a much weaker indicator (4734 → 4659, only 1.58% drop) — i.e. **the choice of
  detection method materially changes the observed outage**, which is itself a useful paper point.

**Verdict: primary trace source.** Free, key-less, 5-minute, per-country and **per-ASN** timelines,
plus pre-computed anomaly-scored series (`gtr-sarima`, `gtr-norm`) that avoid hand-rolled thresholding.
Gives the "many nodes with heterogeneous outage/recovery curves" structure needed for a multi-node
benchmark (per-ASN = per-network node).

Raw files: `ioda_PR_bgp.json`, `ioda_PR_merit-nt.json`, `ioda_events_region.json`

---

## 4. Trace→state conversion prototype, and the flapping problem  **VERIFIED (PoC)**

Naive thresholding of the PR merit-nt series (median 3.2 baseline; `up` ≥0.8×baseline,
`degraded` ≥0.4×, `severe` >0.05×, else `outage`) produced:

```
total state runs: 1026
run counts by state: {'degraded': 494, 'up': 341, 'severe': 186, 'outage': 5}
minutes by state:    {'degraded': 5125, 'up': 16585, 'severe': 2745, 'outage': 25}
```

⇒ **1026 availability transitions over 17 days from a plain threshold.** Most are diurnal noise, not
disruption. This is concrete proof that (a) the "flapping" failure mode is real and not hypothetical,
and (b) trace preprocessing **requires hysteresis / dwell-time / anomaly-scored baselines**, and the
preprocessing choice must be reported and ablated. Use IODA's `gtr-sarima` / `gtr-norm` anomaly series
rather than raw level thresholds.

---

## 5. Local environment feasibility  **VERIFIED**

- Python **3.12.3**; installed: pandas 3.0.3, numpy 2.4.6, matplotlib 3.10.9, requests 2.34.2,
  openai 2.40.0, datasets 4.8.5, transformers 5.9.0.
- **Missing** but pip-installable: `gymnasium`, `networkx`, `simpy`. No local PyTorch.
- Network reachable: PyPI 200, HuggingFace 200; FEMA ArcGIS, ITU GeoServer, IODA API, arXiv,
  GitHub API all reachable from this machine.
- LLM access: `OPENAI_BASE_URL` / `ECHOFLOW_BASE_URL` are set (no plaintext key in env).
- `www.fcc.gov` returns **HTTP 403** to scripted requests (both with and without a browser UA) —
  FCC DIRS pages must be fetched manually or through a browser skill.

⇒ A trace-replay environment (Python, pure-python simulator, no NS-3 dependency) is buildable here today.

---

## 6. DSH "existing primitives" claim — partially unverified

The context doc §3 lists `CapabilityDescriptor`, `ToolInvocation` with `idempotency_key`, etc. as
existing transferable primitives.

- `grep -ril "CapabilityDescriptor"` across `/home/orion/agent-system-learning/dsh-community-suite`
  → **no matches**. No `idempotencyKey` either (1 file mentions "idempotency").
- DSH core *does* contain related machinery: `replay` (348 files), `capability` (357), `lease` (315),
  `deadline` (106), `provenance` (69), `reconcile` (65), `freshness` (29), `heartbeat` (5),
  `sideEffect` (2).
- The referenced design doc《DeepSeek Harness 多设备 Agent 与 Mobile / Physical Capability 架构》was
  **not located** in this checkout. The only similar-named artifact found is an unrelated audit note,
  `/home/orion/agent-system-learning/community-audit/notes/dsh-mobile.md` (a plugin audit, not the
  capability architecture).

⇒ **Action item:** locate/confirm that design doc before the paper leans on "we already have these
primitives". The safest framing is: the *design* exists in our own architecture notes; the paper
contributes the communication-specific failure model + benchmark + validation, not the primitives.

---

## 7. Working PoC: trace → benchmark episode  **VERIFIED (runs end-to-end)**

`pre_work/poc/trace_to_episode.py` — resolves IODA region entities, pulls 5-min signals, builds a
baseline + hysteresis/dwell state machine, and emits an episode JSON with per-tick node availability
and discrete lifecycle events (`disconnect` / `degrade` / `recover`).

### 7a. Region-level granularity confirmed (sub-national nodes)
`entities/query?entityType=region&search=Florida` →
`geo.netacuity.SA.UY.4397` (Uruguay) **and** `geo.netacuity.NA.US.4437` (US).
Region names are **not globally unique**; a name-only lookup silently selected the wrong country.
Country code lives at `fqid.split('.')[3]`. Working codes: FL `4437`, GA `4438`, SC `4440`,
NC `4444`, TN `4446`, VA `4447`, Puerto Rico `3304`.

### 7b. Hurricane Helene 2024 episode (6 US states, merit-nt, 3168 ticks × 300 s, 11 days)
```
region/4437 Florida        worst=degraded  up=11410 degraded=4430
region/4438 Georgia        worst=degraded  up=14200 degraded=1640
region/4444 North Carolina worst=severe    up=5460  severe=9465 degraded=915
region/4440 South Carolina worst=severe    up=9540  degraded=5345 severe=955
region/4446 Tennessee      worst=degraded  up=15785 degraded=55
region/4447 Virginia       worst=up        up=15840
event kinds: {'degrade': 48, 'recover': 16, 'change': 21}   (85 lifecycle transitions)
```
Heterogeneous per-node degradation, **but zero full disconnects** — the six nodes never collapse to 0.

### 7c. Trace choice decides whether outages exist at all
Puerto Rico / Hurricane Fiona 2022 (`region/3304`, merit-nt) does collapse to 0.
Dwell-time ablation on that same trace:

| dwell | worst state | transitions | events |
|---|---|---|---|
| 0 s (naive threshold) | **outage** | **1102** | 5 `disconnect`, 9 `recover`, 367 `change`, 730 `degrade` |
| 600 s | severe | 73 | 50 `degrade`, 22 `change`, 1 `recover` |
| 1800 s | severe | 14 | 9 `degrade`, 5 `change` |
| 3600 s | severe | 5 | 3 `degrade`, 2 `change` |

**This is the single most important methodological finding of the PoC.** The real total outages in
this trace last only ~25 minutes total (5 consecutive samples). Any dwell/hysteresis filter long
enough to suppress diurnal flapping (1102 → 14 transitions) **also erases every genuine outage**.

⇒ The paper must (a) not hand-tune a single threshold, (b) report the flapping/missed-outage trade-off
explicitly, and (c) either use IODA's anomaly-scored series (`gtr-sarima` / `gtr-norm`) or a
two-timescale state machine (fast outage detector + slow degradation baseline). This is a genuine
benchmark-design contribution, not a nuisance parameter.

Artifacts: `poc/trace_to_episode.py`, `poc/episode_helene_meritnt.json`,
`poc/episode_fiona_pr.json` (md5 `5f674014a209f65a7eb9938d53e2c2a7`).

---

## 8. α³-Bench artifact reality check  **VERIFIED**

- Repo `maferrag/AlphaBench` (GitHub API): description matches, ~13.5 MB, 1105 tracked files,
  last push 2026-01-08, **10 stars**, **license: none declared** (GitHub returns `license: null`).
- Contains: `113k_episodes dataset/113k_episodes dataset.zip`, `Results_Evaluation/eval_runs/<provider>/<model>/uav/*.json`
  (per-episode eval traces), `Research Paper/2601.03281v1.pdf`, `Figures/`.
- Episode JSON structure (from README): `initial_state` with `domain`, `time_s`, `env`
  (`weather`, `wind_mps`, `wind_dir_deg`), `airspace` (`alt_bounds`, `geofence` polygons),
  `uav` (`pose`, `speed_mps`, `energy.battery_pct`, `sensors` status `ok`).
- Uses MCP and A2A protocols for action invocation; composite α³ metric over mission success, safety,
  dialogue quality, tool-use consistency, communication efficiency.

⇒ **Excellent structural template** for our episode schema (typed initial state + environment +
capability/energy/sensor status). **Caveat: no declared license** — must be clarified before
redistribution; fine for internal experimentation.

---

## 9. IODA coverage of recent events  **VERIFIED**

Query for 2024-09-20 → 2024-11-10 (`entityType=country`, limit 50) returned 50 events, e.g.
`country/YT` merit-nt start 2024-09-16 dur 1294.6 h (score 7.77e6), `country/SL` bgp dur 948.8 h,
plus AW, LC, MF, MP, NR, GU, NC, EE, ZM. IODA is a **live, ongoing** record (not an archived 2022
dataset), so episodes can be drawn from 2022 through the present.
Note: `/outages/events` has no hazard filter — linking an event to a named storm requires an external
join (GDACS/IBTrACS), and heavy `limit`/`orderBy` combinations returned HTTP 000/500, so paginate
modestly.

---

## 10. NOVELTY THREAT — direct prior art for the proposed runtime  **VERIFIED**

Found while checking novelty. These are **published** and overlap the context doc's §9/§10 method.

### 10a. 注意：Closest threat
**"Verified Tool Calls Improve LLM Agent Reliability Under Non-Atomic Failures"**
Isham Kalappurackal Mansoor, Abhishek Phadke, Pratip Rana — arXiv **2608.02645**, 2026-07-31.
Abstract (quoted): *"Existing agent frameworks typically assume that tool calls are atomic and return
binary success or failure signals. However, real-world systems exhibit non-atomic behaviors such as
**timeouts after dispatch, delayed visibility, and partial state updates**. These mismatches lead to
reliability issues including **duplicate actions**, task success, and unnecessary tool executions.
A lightweight, **verification-aware tool wrapper** is introduced that augments tool calls with
**postcondition verification, verify-before-retry logic, and idempotency keys**. The approach is
evaluated in a **controlled simulated environment with injected non-atomic failures** across multiple
task templates… significantly reduces duplicate actions, while maintaining comparable task success."*

⇒ This is essentially the context doc's Task A + Method items (operation lifecycle, idempotency-aware
retry, reconcile/verify-before-retry), evaluated with **injected** faults.
**Remaining differentiation:** real disaster traces instead of injection; communication-specific
failure distribution; capability/node lifecycle + freshness + fairness; wireless-agent baselines.
The "we add verify-before-retry with idempotency keys" claim is **no longer available.**

### 10b. Agent runtime at a *networking* venue (注意：the venue is closing too)
**"DelAct: A Replayable Boundary Runtime for Auditable and Governed LLM Agent Workflows"**
Yuanbo Zhang, Hanlong Liao, Deke Guo, Guoming Tang — **IEEE/ACM IWQoS 2026**,
DOI `10.1109/iwqos70441.2026.11661202`, 2026-06. (NUDT). Replayable boundary runtime for LLM agent
workflows = directly adjacent to "bounded replay".

### 10c.
**"Durable Execution for AI Agents: A Design Pattern for Fault-Tolerant Agent Loops"**
Stenio De Lima Ferreira — **IEEE SmartCloud 2026**, DOI `10.1109/smartcloud69481.2026.00014`, 2026-05.

### 10d.
**"A Governed Shared-Kernel Architecture for Persistent, Auditable Multi-Agent Societies Beyond the
LLM Session"** — Saeed Farokhi, preprint, 2026-08-31, DOI `10.21203/rs.3.rs-10847583/v1`. Covers
effect-time authorization, fencing, **recovery-before-effect**, tamper-evident evidence — i.e. the
"permission/authority bound to recovery semantics" item in §3 of the context doc.

⇒ **Consequence for the plan:** the mechanism layer of this paper is being published in real time by
other groups in 2026. The defensible contribution is now narrower and must be executed on:
(1) a **communication-specific failure model grounded in real IODA/FEMA traces**,
(2) an **emergency-communication benchmark** with capability lifecycle under intermittent connectivity,
(3) **empirical proof that published wireless-agent baselines fail** in that regime.

---

## 11. THE DECISIVE COLLISION — INFOCOM 2026  **VERIFIED (Crossref + Semantic Scholar)**

**"Rollback Is Not Undo: Path-Dependent Failures in LLM-Arbitrated Network Control"**
**Weici Pan, Zhenhua Liu** — **IEEE INFOCOM 2026**, 2026-05-18.
DOI `10.1109/INFOCOM59046.2026.11571400` · DBLP `conf/infocom/PanL26` · CorpusId 289701645 ·
**open access: CLOSED** (abstract only; no PDF).

Abstract, quoted in full:

> "AI components are rapidly entering network control planes: LLM agents interpret telemetry, propose
> mitigations, and a learned arbitrator selects actions. Operationally, such systems inherit a familiar
> safety valve from traditional networking: protocol rollback. A common assumption is that reverting a
> patch restores behavior. **We show this assumption can fail in AI-augmented control loops.** We study
> an online, closed-loop setting where two LLM agents propose conflicting actions and an LLM arbitrator
> executes a single decision each round. We formalize protocol paths and introduce a **post-rollback
> recovery metric, the recovery gap**, which compares post-rollback performance against a baseline that
> never experienced the patch. **Even when the post-rollback protocol text is identical, the system can
> exhibit persistent degradation**, consistent with path dependence arising from both stateful network
> trajectories and history-dependent in-context arbitration. Empirically, we instantiate a **multi-LLM
> edge DDoS mitigation task with realistic transient fault modes (observation corruption,
> delay/reordering, agent dropout, and proposal corruption)**. Across these perturbations, we observe
> nontrivial and directionally asymmetric recovery gaps after rollback. Finally, we propose a
> lightweight mitigation that improves absolute post-rollback cost, though the relative recovery gap
> persists."

**Why this is decisive.** It is at the *exact* venue family the user targets (INFOCOM), in the exact
problem space (LLM agents in a network control loop), and it already establishes:
- transient communication fault modes (delay/reordering, dropout, observation corruption, →
  i.e. stale observation + outcome-unknown) as the studied failure regime;
- that naive recovery (rollback) **fails** in LLM-arbitrated network control;
- a purpose-built recovery metric, and a mitigation that only partially closes the gap.

**What it does NOT cover (remaining room):**
1. **Emergency / disaster communication.** It is edge DDoS mitigation, not disaster networks; there is
   no mission, no criticality, no energy/freshness, no sensing-node capability lifecycle.
2. **Injected, not trace-driven.** Fault modes are injected perturbations, not real degradation
   trajectories with a measured outage/recovery distribution.
3. **Rollback semantics, not the fuller lifecycle.** No idempotency, duplicate side effects, leases,
   fair replay, head-of-line blocking, or budgeted retry.
4. **No benchmark / environment release** (closed access, no artifact).

⇒ This paper must be cited **in the introduction** and the differentiation must be explicit. It is
also a strong *supporting* citation: a top-tier venue already agrees that recovery in LLM network
control is path-dependent and that the naive assumption fails.
