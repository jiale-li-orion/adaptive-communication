# When Freshness Feedback Lies: Stabilizing the Communication Execution Layer for Pre-Disaster Monitoring under Intermittent Backhaul and Energy Scarcity

*Working draft v1, 2026-09-15. All numbers are reproduced by `code/v3joint/` (16-seed paired unless noted) and archived under `results/`. Source-grade labels E/A/M follow the repo evidence ledger; nothing here is a field SLA. Placeholder citations marked [cite:…] must be verified against the transfer ledger before submission.*

## Abstract

Pre-disaster geohazard monitoring networks must keep delivering periodic and event-triggered obligations when the cellular backhaul is down for hours and nodes run on small solar-charged batteries. A natural engineering instinct—borrowed from the age-of-information (AoI) and energy-harvesting literature—is to **close the loop**: sample and report faster when the controller's information is stale or the battery looks healthy. We show that, in a two-segment access/backhaul architecture with a delayed Class-A downlink, this instinct backfires exactly where it is needed most. The controller's end-to-end AoI is *polluted by the backhaul*: during an outage the center stops receiving, so end-to-end age grows without bound even though the gateway keeps hearing fresh samples, and an AoI/SoC-gated policy responds by sampling 6× more densely and reporting faster—data that cannot leave. Under weak harvesting this drains the battery past the point of no return; the node is declared dead and **never reports again after the backhaul recovers**. Across a harvest×outage phase plane and 16 paired seeds, the canonical energy-AoI policy loses 69–73 routine-coverage points (16/16 seeds, CI excludes 0) and leaves ≈1 of 14 nodes alive, while a fixed sparse schedule with automatic primary/backup failover stays at 0.983–0.998 coverage and keeps every recoverable node alive. A literature-grade joint EH-AoI threshold mitigates but does not remove the loss; a delivery-anchored loop is safe but statistically tied with (0.2–0.3 pp below) the open-loop schedule. The same conclusion holds when obligations are tightened to 5–10 min risk windows: the end-to-end AoI loop (0.46) is Pareto-dominated by a feasible static operating point (0.76–0.81), and the only cell where a loop beats a fixed choice is an access-congestion artifact of an infeasible fixed point. We localize the cause to the **feedback signal**, not to parameters or scale, through no-outage controls, placement ablations, a static frontier, and a single-node causal trace, and state the design principle: the real-time sampling/reporting layer should run a static operating point matched to obligation tightness with automatic primary/backup failover, with any feedback anchored to *local deliverability at the gateway* rather than end-to-end age; operating-point changes track task-level risk state at a slow timescale. This execution layer is the substrate on which a higher-level agentic runtime can orchestrate recovery; it does not itself need an agent.

**Index terms**—age of information, energy harvesting, LoRaWAN Class A, intermittent backhaul, disaster monitoring, closed-loop stability, networked control.

---

## 1. Introduction

### 1.1 Setting

We study a pre-disaster (pre-event, always-on) mountain geohazard monitoring deployment: field sensor nodes on a slope access a single cached, locally-autonomous gateway over LoRaWAN Class A; the gateway reaches the operations center over an intermittent cellular backhaul with a constrained short-message backup (e.g., RDSS-style satellite short packets). Nodes are solar-powered with small batteries and no mains. The service is defined not as "never lose the link" but as **continuity of monitoring obligations**: each routine obligation requires one valid sample for an object to be taken in its hourly window and received at the center within the window plus a grace period; event obligations are short bursts after a local trigger. This is the deployment class of the Wang Guizhou loess-slope system [cite: Wang Front. Earth Sci. 2022], the Kumar asymmetric multi-WAN deployment [cite: Springer MONET 2019], and high-alpine sites such as Hochvogel [cite: EGU25-11121]; the concrete reference deployment, obligations, and evidence grades are fixed by the project task contract (E/A/M labels).

### 1.2 The instinct, and why it fails in two segments

The AoI and energy-harvesting (EH) literature gives an appealing rule: spend energy to sample/report more densely when information is stale and the battery permits, and back off otherwise; for a finite-battery EH source an optimal online policy is a monotone threshold whose age threshold is non-increasing in battery level [cite: Bacinoglu, Sun, Uysal, Mutlu, arXiv:1905.06679]. These results assume a sender-local controller with **immediate, correct feedback**—the controller observes the consequence of its action on the same hop it controls. Our architecture violates that assumption in a specific, consequential way. The path from a sample to a decision has **two segments with very different availability**: the access segment (node→gateway) and the backhaul segment (gateway→center). A controller placed at the center computes AoI from *center-received* timestamps. When the **backhaul** fails while access still works, the gateway keeps ingesting fresh samples but the center's view freezes: end-to-end AoI grows as if the node had gone silent. A policy that densifies sampling on large AoI therefore densifies **precisely during a backhaul outage**, producing samples that pile up at the gateway and cannot be delivered, while paying the sensing energy (sensing costs ≈20× a transmission in our device profile). When harvesting is weak, this is a positive-feedback path to a dead battery. Because a node whose state of charge drops below one sensing energy is permanently declared dead, the damage is irreversible: when the backhaul returns hours later, the node is gone for the rest of the mission.

### 1.3 Contributions

We make and substantiate four claims, all inside the fixed scenario (no scenario substitution, no LLM in the loop, baselines tuned fairly and never weakened to win):

- **C1 — A grounded execution problem and harness.** A faithful two-segment, Class-A, energy-harvesting monitoring model with real obligation semantics, delayed/uncertain downlink, byte- and energy-accurate accounting, and a zero-copy primary/backup failover execution layer pinned by bit-identical regression anchors.
- **C2 — A counter-intuitive failure mode and its region.** End-to-end AoI/SoC-gated sampling/reporting *destabilizes* under long outages and weak harvesting: −69 to −73 coverage points, 16/16 paired seeds, ≈13 of 14 nodes killed, in the exact operating region mountain monitoring occupies. We map a 5×5 harvest×outage phase plane, show zero loss at outage = 0 (isolating the cause to backhaul-polluted feedback), and show the same failure at 5/9/14-node scales.
- **C3 — Mechanism localization and a design principle that holds in both regimes.** No-outage controls, controller-placement (center vs gateway) ablations, driver-signal ablations, a literature-grade joint EH-AoI baseline, an oracle upper bound, a static-configuration frontier, and a single-node causal trace converge on one cause—the feedback signal is polluted by a segment the controller does not control. Across the obligation-tightness axis (1 h routine down to 5 min risk-window), an end-to-end AoI/SoC loop is never on the Pareto frontier: it destabilizes in the loose/energy-scarce regime and is Pareto-dominated by a feasible static operating point in the tight regime. The principle: the real-time layer should run a **static operating point matched to obligation tightness** (sparse for routine, denser only for key nodes during a risk window) plus automatic primary/backup failover; any feedback must be anchored to *gateway-local deliverability/obligation phase*, not end-to-end AoI, and a correct delivery-anchored loop is at best statistically tied with the matched static point. Switching the operating point with the task-level risk state (intensify on alert, revert when cleared) is a slow, task-driven orchestration action—not a per-tick AoI loop.
- **C4 — Scope for the agentic layer.** We delineate where an agent runtime can and cannot help: the real-time execution layer needs no agent and is harmed by naive adaptive feedback; agentic value, if any, lives in slower, context-bearing orchestration/recovery above a reliable execution layer, which we position and leave to a second stage rather than assert.

### 1.4 What would change our conclusion (pre-registered)

Following the project's falsification discipline, we state the kill criteria up front. The "open-loop is optimal at the real-time layer" claim is scoped to (i) the low data rate of geohazard routine/event obligations, (ii) backup capacity that exceeds the tiny backlog, and (iii) fixed, value-equal obligations. It would be overturned by a *legal-information* policy (no future truth, same budget) that beats fixed scheduling on paired coverage or real cost, or by a regime where denser sampling has genuine service value. We tested both: an oracle that sees future outages cannot beat fixed scheduling on reporting alone, and delivery-anchored dense sampling never triggers because sparse sampling already satisfies obligations—i.e., the claim holds in the declared regime, and we report its boundary rather than over-generalize.

## 2. Related work

**Age of information and energy-harvesting sampling.** A line of work optimizes sampling/update timing to minimize an age penalty under an energy-harvesting or finite-battery constraint, yielding threshold/switching policies on age and battery [cite: Bacinoglu et al. arXiv:1905.06679; age-penalty sampling Arafa et al. arXiv:2007.10200; TCOM/TII AoI-energy]. Their controller is **sender-local** (co-located with the sampler/transmitter) and receives immediate per-action feedback—battery, its own buffer, and ACK/NACK on a single (possibly error-prone) hop. We adopt the strongest such structure we found (a joint `(SoC ∧ AoI)` threshold, our `eh_aoi`) as a first-class baseline and show the assumption that breaks in two-segment access/backhaul: the age the controller sees is not the age at the point it can act on. We do not claim these policies are wrong in their native model; we identify the structural condition under which they destabilize.

**Scheduling with bounded buffers and limited service opportunities.** Constrained-queue formulations model sensor queues of finite buffer depth (loss on overflow), exogenous sensor arrivals, a server that visits each object at limited opportunities, and receipt/performance feedback [cite: Emami et al., ICLDC, arXiv:2504.14556 / IEEE IoT-J 2025]—formal elements we inherit (note that in that work the scheduler is an LLM using in-context learning, placing it also in the agent lineage). Their sensor arrival process is exogenous; in our setting the *arrival of data at the gateway is endogenously changed by a delayed remote configuration action* (Class A), which is the coupling we study. Joint sampling/transmission/energy problems under partial source observability are formulated as POMDPs [cite: "Semantic-aware Sampling and Transmission in Real-time Tracking Systems: A POMDP Approach," arXiv:2311.06522]; its own system model places the controller **at the transmitter side**, observing battery, its local buffer, and ACK/NACK, and acting in the same slot—the sender-local, immediate-feedback assumption we listed above. We state these differences explicitly rather than use them to claim a blanket gap.

**Delay/disruption-tolerant and emergency networks.** DTN store-and-forward [cite: Fall SIGCOMM 2003], contact-aware triage under extreme low-rate contacts (e.g., SHETLAND-NET, *not fully verified in this environment*), and overbooking in space links [cite: CCSDS 734.3-B-1] address scheduling over sparse contacts. Content-selective packing under satellite scarcity is therefore a *solved sub-problem* in the literature; our finding is consistent with this—at our data rate, deadline-ordered packing is bit-identical to EDF and is a dead parameter, so we do not re-claim it.

**Agents/LLMs for emergency and disaster networks.** A lineage starting from TopoLLM [cite: Digital Communications and Networks 12 (2026) 273–282] splits into (i) LLMs that directly schedule network resources (UAV path/bandwidth, e.g., PS-UAV, LODA, WirelessAgent), (ii) LLM-assisted reinforcement learning, and (iii) post-disaster infrastructure agents that compose recovery tools (ESWA IIN-recovery, SCS Lifeline/MCP). These let an agent choose **network resources or recovery sequences after a disaster**. Our object is different: long-horizon **pre-disaster** continuity across acquisition→configuration→backhaul→recovery for a single obligation's end-to-end delivery, and—per C4—we separate the communication execution layer (this paper, agent-free) from the planner layer (future comparison under identical information and budget). We make no "first/novel gap" claim; the candidate space is registered as such pending the standing literature review (α³-Bench and others remain unread).

## 3. System model and problem

### 3.1 Deployment and roles

The reference instance has 14 nodes = 1 gateway `gw0` + 13 displacement stations `n00–n16` (3 marginally reachable, all SF7), per the v1.1 manifest; a 5-node S1 instance and a 9-node instance are used as scale axes. The gateway has a cache and preloaded local-autonomy rules; there is no mains power. Nodes sense displacement (6 B) and rainfall (4 B); the aggregate data rate is very low (on the order of a few bytes per node per hour), a fact that drives several results.

### 3.2 Two-segment communication and the Class-A control delay

A sample traverses an **access segment** (node→gateway, intermittent LoRa, Class A) and a **backhaul segment** (gateway→center, cellular primary + short-message backup). A downlink configuration command (`set_sampling_interval`, `set_report_period`) can only be emitted in a Class-A receive window opened by an uplink, then takes effect after the next sampling cycle; it may be delayed or never take effect (DWELL 300 s, command TTL 6 h). Control and data therefore compete for the same scarce bidirectional opportunities (W1/W3 in the project framing).

### 3.3 Energy

Per-tick state of charge evolves with harvested energy minus sleep/sensing/TX/RX; sensing costs 4.7e-4 Wh/sample (Ragnoli et al., JLPEA 12(3):47, 2022, measured) and an uplink 2.33e-5 Wh—**sensing is ≈20× costlier than reporting**. Capacity is 0.05 Wh. Harvesting uses a solar/irradiance model with a tunable peak, optional per-node blackout fraction (a fixed, seed-determined set, identical across arms for fairness), and initial SoC. **A node whose SoC falls below one sensing energy is permanently declared dead** (it cannot even take a sample); this irreversibility is central to the failure mode.

### 3.4 Obligations and the service metric

A routine obligation for object $i$ opens a window $[r_i, r_i{+}P]$ and, with grace $P$, has deadline $d_i=(k{+}2)P$ at $P=3600$ s. An event obligation is a single-point window with 600 s grace (three slots 300 s apart). The shared, exogenous denominator is identical for all policies (a policy is not scored by samples it itself decides to take). The primary metric is **timely routine coverage** = obligations with a valid sample taken in-window and received by the deadline, plus event delivery; we also report nodes alive, final SoC, uplink airtime, and downlink command attempts (real cost). Unreachable points stay in the denominator; we separately name access-hard-loss (class A), arrived-too-late (class B), and on-time-at-gateway-but-missed-to-center (class C).

### 3.5 The controller's observable plane—and the pollution

A center-placed controller's view is built from **center-received** timestamps: `AoI(t)=t−newest_center_received_at`. A gateway-placed controller builds it from **gateway-heard** timestamps. During a backhaul outage with working access, these diverge: gateway AoI stays current while center AoI grows without bound. The same policy code under the two placements therefore sees different "staleness," which we exploit as a causal instrument (Sec. 6.4). A legal controller may know its own current link state and history, but never future outage truth.

### 3.6 Problem

For each obligation choose sampling interval, reporting period, and primary/backup sending over time, using only legal observable history, to maximize timely coverage under the energy and opportunity budget. We compare, under identical exogenous trajectories and budgets: open-loop fixed schedules; the existing v1.1 adaptive report policies; an Energy-AoI policy (`ea_aoi`); a literature-grade joint EH-AoI threshold (`eh_aoi`); a delivery-anchored policy (`anchor`); and diagnostic oracles.

## 4. Communication execution layer and policy family

### 4.1 Zero-copy primary/backup failover

The execution layer wraps the v1.1 control plane without altering its primary-path behavior. When the primary backhaul is unavailable, at each backup opportunity ($t \bmod r_b = 0$) it packetizes one subset of currently-pending samples at sample granularity (net payload = backup bytes − header), splits a source item across packets if needed, and removes taken items from the primary pending queue to prevent primary/backup duplication. A timestamp `last_primary_ok_at` updates **only** when the primary genuinely forwards (backup does not count), so link-up beliefs are not fooled by backup success. Five regression anchors pin correctness; crucially, with backup disabled the wrapped plane is bit-identical to the v1.1 baseline. Backup rate/payload ({120,300,600} s; {78,200} B) are scanned as **A-level research assumptions**: the ≥1 min cadence and ≤200 B figures belong to different sections of DZ/T 0450 and are not fused into a single "standard operating point."

### 4.2 Policy family (all get the same failover layer and budgets)

- **local / fixed900 (open-loop).** Constant 3600 s sampling; `local` keeps the default 3600 s reporting, `fixed900` a constant 900 s reporting. No downlink after initialization.
- **ea_aoi (Energy-AoI).** Dense 600 s sampling iff SoC ≥ healthy threshold; fast 300 s reporting iff end-to-end AoI is missing or > stale threshold, else 900 s. This is the canonical "spend when healthy and stale" loop.
- **eh_aoi (joint EH-AoI, literature structure).** Dense iff `(SoC ≥ θ) ∧ (AoI > θage)`—a conjunctive battery-and-age threshold in the finite-battery EH threshold structure of Bacinoglu et al.; harder to enter dense mode than `ea_aoi`.
- **anchor (delivery-anchored).** Placed at the gateway; decisions use gateway-local obligation phase/satisfaction and (optionally) the time to the next backup opportunity, never end-to-end AoI. With sampling gating disabled it reduces to the v1.1 `ObligationSlackPolicy` idea (report-only); we keep both to test whether gating *sampling* adds anything.
- **Oracles.** A clairvoyant policy that sees future outage windows (diagnostic upper bound only, not an implementable baseline); a report-only variant; and a center-vs-gateway placement variant of `ea_aoi` for mechanism attribution.

Every fed signal passes an **identifiability gate**: if setting it constant (or shuffling it) does not change actions, it is a dead parameter and is reported as such rather than kept for appearance.

## 5. Why end-to-end AoI feedback destabilizes

### 5.1 The positive-feedback loop

During a backhaul outage with working access: (1) the center stops receiving ⇒ end-to-end AoI rises monotonically; (2) an AoI-gated reporter switches to fast 300 s; (3) an SoC-gated sampler, seeing a battery above the healthy threshold, switches to dense 600 s (6× sensing, the dominant energy cost); (4) the extra samples cannot leave, so they neither lower center AoI nor deliver value; (5) energy is spent with no unloading; under weak harvesting the SoC falls; (6) in `ea_aoi` the dense gate is released only when SoC is already critically low—too late—and the node crosses the one-sample energy floor and is declared dead. The loop is **positive** because the very signal that should indicate "send more" (high AoI) is caused by a downstream segment the extra upstream action cannot fix.

### 5.2 Why the joint threshold only mitigates

Conjoining AoI to the SoC gate (`eh_aoi`) raises the bar for entering dense mode, reducing the net discharge rate and pushing the failure frontier outward; but because end-to-end AoI keeps growing throughout any sufficiently long outage, the conjunctive condition is eventually met. A threshold on a *polluted* signal cannot remove the pollution—it only delays crossing. This predicts the phase diagram: `eh_aoi` should beat `ea_aoi` everywhere but still lose to open-loop at long outages, which is what we observe.

### 5.3 Semi-quantitative critical condition

During an outage the node's net energy change is harvesting inflow minus (dense-sensing count × sensing energy + fast-report count × TX energy). Open-loop/anchor keep 1/h sensing and are net-positive (they charge during daylight); a closed loop in dense+fast mode is net-negative. Death occurs when

$$\text{outage length}\times(\text{dense net discharge rate}) > \text{usable battery buffer at outage start}.$$

This gives a design frontier in the (battery buffer, outage length) plane and explains the monotone phase diagram: stronger harvesting or shorter outages keep the closed loop on the safe side; the mountain monitoring regime (hour-to-day outages, weak winter harvesting) sits deep in the unstable region. A full analytic bound is future work; the present paper establishes the frontier empirically (Sec. 6.3).

## 6. Evaluation

### 6.1 Setup

Full instance = 14 nodes; access arrival prob 0.74, backhaul good prob 0.62; routine P = 3600 s with one grace period; event bursts per the manifest; 48 h horizon (1 h tail); backup at 300 s/78 B unless noted; solar harvesting with swept peak, initial SoC, and per-node blackout fraction. Evaluation seeds (0–15) are separate from any arm-selection seeds (0–3); paired comparisons share one exogenous trajectory per seed. All arms share identical harvesting/outage draws.

### 6.2 Main paired result (Table 1)

Against open-loop `fixed900`, 16 paired seeds (8 for dual outage), routine-coverage Δ in pp with paired-t 95% CI:

| Condition | arm | Δ (pp) | 95% CI | worse/total | alive (/14) |
|---|---|---|---|---|---|
| stressed: 16h outage, peak .005, bo .3 | ea_aoi | **−69.04** | [−75.22,−62.86] | 16/16 | 1.31 |
|  | eh_aoi | −4.97 | [−10.98,+1.05] | 14/16 | 12.19 |
|  | anchor | −0.20 | [−0.34,−0.05] | 9/16 | 13.69 |
| deep: 32h outage, peak .003, bo .4 | ea_aoi | **−73.14** | [−77.42,−68.86] | 16/16 | 0.88 |
|  | eh_aoi | −6.44 | [−16.07,+3.20] | 11/16 | 7.69 |
|  | anchor | −0.15 | [−0.27,−0.03] | 8/16 | 8.12 |
| dual: 16h backhaul + 4h access outage | ea_aoi | **−71.47** | [−74.13,−68.80] | 8/8 | 1.12 |
|  | eh_aoi | −8.89 | [−20.75,+2.97] | 7/8 | 11.62 |
|  | anchor | −0.32 | [−0.63,−0.00] | 6/8 | 13.75 |

`fixed900` absolute coverage is 0.9984 / 0.9832 / 0.9438 (the dual-outage gap to 1 is access-hard loss that no upstream policy can recover). The Energy-AoI collapse is overwhelming and sign-unanimous; the literature joint threshold converts a catastrophic loss into a small, directionally-negative one; the delivery-anchored loop is safe but statistically tied-to-slightly-below open-loop. **No feedback loop beats simple open-loop at this layer.**

### 6.3 Failure-region phase diagram (Fig. `v3joint_phase.png`)

A 5 (harvest peak .003–.020) × 5 (outage 0–32 h) grid. At outage = 0 both AoI loops have ≈0 loss—**the failure is switched on by the backhaul outage**, isolating the cause. Loss grows monotonically with outage length and inversely with harvesting; a frontier sits around 4–8 h, beyond which `ea_aoi` drops 14–72 pp while `eh_aoi` drops 6–18 pp; open-loop/anchor stay at 0.998 across all 25 cells. The 4-seed phase grid is exploratory for trend; Table 1's 16-seed numbers govern quantitative claims.

### 6.4 Mechanism ablations

- **No-outage control:** with the backhaul up, `ea/eh` ≈ open-loop ⇒ the policy is not intrinsically bad; the polluted feedback is.
- **Placement (center vs gateway AoI):** moving the *same* `ea_aoi` code to the gateway (so AoI uses gateway-heard time) only partially rescues it (stressed .652 vs .292, still dying): fixing the reporting-side signal does not fix the SoC-gated dense sampling, which never looks at deliverability.
- **Driver signal:** replacing the dense trigger with obligation phase (no per-tick downstream quantity) removes the instability entirely (0.982–0.998 across the energy axis, survival identical to fixed).
- **Sampling gating is a dead branch here:** report-only and full sampling-gated anchor are bit-identical—with a 1 h window + 1 h grace, sparse sampling already satisfies every obligation, so "densify near need" never fires. Dense sampling has no service value in this task.
- **Oracle upper bound:** a policy that peeks at future outages and densifies only inside windows still reaches only 0.991 < fixed 0.998, with more commands—even god's-eye time-varying densification cannot beat constant 900 s reporting.
- **Send-side packing:** true deadline ordering is bit-identical to naive periodic EDF at every packet (backup capacity always exceeds the tiny backlog) ⇒ a dead parameter, consistent with DTN literature.
- **Scale axis:** the failure reproduces at 5/9/14 nodes (stressed `ea_aoi` 0.530/0.409/0.327, alive 1.0/1.0/1.25; `eh_aoi` 0.952/0.936/0.861; fixed/anchor 0.997–0.999) and is if anything worse at small scale where each obligation matters more.

### 6.5 Single-node causal trace (Fig. `v3joint_timeline.png`)

Node n00, seed 0, stressed. All arms start 3600/3600 at 25 mWh. From h2 `ea/eh` enter 600 s sampling and, after the h4 outage, 300 s reporting; their SoC declines 26→0.2–0.5 mWh and they are permanently dead at h16. Open-loop/anchor hold 3600/900 and, fed by weak daylight harvesting, *charge* to 45–50 mWh and survive. At h20 the backhaul recovers: the closed-loop node's battery later recharges to ≈28 mWh but the node is dead and reports nothing for the remaining 28 h; the open-loop node continues. Dense-600 hours over the run: 47 for `ea/eh`, 0 for open-loop/anchor. This trace ties the aggregate −69 pp to a single auditable causal chain: outage → end-to-end AoI inflation → dense sampling/fast reporting → drain → irreversible death → permanent post-recovery blackout.

### 6.6 Obligation-tightness axis: the closed loop is dominated in the risk-window regime too

A reviewer may object that a 1 h obligation window is too lax, so that open-loop winning is trivial. We therefore stress the obligation period down to the risk-window level (P = 300–900 s, the W1 intensified-observation regime of the project contract), with energy made feasible to avoid confounding. Two findings. **(i) Energy-feasibility boundary first:** at P = 600 s under the *stressed* energy budget, even fixed 600 s sampling kills all 14 nodes—48 h of 600 s sensing needs ≈0.135 Wh against a 0.05 Wh battery; tight obligations are physically infeasible there for any policy, which is an energy boundary, not a control result. **(ii) Under feasible energy, the end-to-end AoI loop is Pareto-dominated by the legal static configuration frontier** (6 paired seeds, P = 300 s, 16-h outage; Fig. X): the best static point grid600×300 reaches 0.800 and grid600×600 0.768, while `ea_aoi` reaches only 0.457—**31.2 pp below grid600×600 (paired 95% CI [−33.7, −28.7], 6/6 worse)**; grid900×600 attains 0.483 with *less* airtime (490 s) than `ea_aoi`'s 539 s, i.e. it Pareto-dominates the loop, and the joint EH-AoI loop is 56 pp below at 0.205. Moving from grid600×600 to the denser grid600×300 costs 2.4× airtime for an insignificant +3.2 pp (CI crosses zero), so grid600×600 is the cost-effective frontier point. Across P, the period-matched open-loop point is 0.869/0.984/0.999/1.000 at P = 600/900/1800/3600 versus 0.810/0.900/0.998/1.000 for `ea_aoi`. The one cell where a loop beats a *fixed* choice (P = 300: fixed 300/300 collapses to 0.054 while `ea_aoi` gets 0.461) is an **access-congestion** artifact: fixed 300/300 generates 26,743 samples that never reach the gateway (mean gateway backlog 110, cache overflow); the loop merely slows down to relieve congestion—but a *feasible* static point 600/600 reaches 0.763 and beats it. Loss decomposition (A never-at-gateway / B late-at-gateway / C missed-to-center) confirms this. Hence even in the tight regime the right object is a static operating point chosen *inside the access-feasible region* plus failover; per-tick end-to-end AoI feedback is not on the Pareto frontier (Fig. X). The 0.80 ceiling at P = 300 also shows that network-wide 5-min intensification approaches single-gateway access capacity—a deployment argument for intensifying only key nodes (W1), not the whole field.

**[Fig. X here: `results/v3joint_frontier.png` — service–airtime static frontier with the two end-to-end loops below it.]**

## 7. Discussion

**What the result is, and is not.** It is not "closed loops are bad" or "AoI is wrong." It is a *boundary statement*: AoI/EH threshold policies assume sender-local, immediate, correct feedback; when the freshness signal is computed across a separately-failing segment, closing the loop on it introduces a positive-feedback energy path in the loose regime and, under tight risk-window obligations, a policy still Pareto-dominated by a feasible static operating point. Across both regimes the real-time layer is best served by a tightness-matched static point plus failover. We explicitly do not claim this holds for value-heterogeneous obligations, contested backup quotas, or operation beyond the single-gateway access-feasible region; the network-wide 5-min ceiling of 0.81 indicates where the access capacity—and thus the problem—moves from control to architecture (key-node-only intensification, a second gateway, relay). The identifiability test (does gating sampling on a signal ever change an action?) still tells an operator which regime they are in.

**Why rules winning is a contribution.** Per the project contract and collaborator review, a communication paper does not require an irreplaceable LLM. A reliable execution layer—correct failover, feedback that cannot be polluted by a downstream outage, a stated open-loop frontier—is a communication-systems contribution that *any* higher-layer planner (rule MPC or tool-using agent) benefits from. We did not weaken baselines: the literature joint threshold is a first-class baseline, oracles use future truth only as diagnostics, and the delivery-anchored loop's small *negative* gap is reported rather than hidden.

**Where the agent goes (C4, future work).** The real-time layer needs no agent. A possible agentic role is slower orchestration/recovery over heterogeneous means when context is non-numeric and evolving. In the current fixed, structured, single-value task that problem is also covered by a standard MPC over the same legal information, so we do not claim it; we state the exact condition (non-structurable task context, model mismatch that online re-estimation cannot repair) under which a second-stage planner comparison would be meaningful, and leave it there rather than re-run the previously falsified "LLM scores record importance" experiment.

**Threats to validity.** (i) Backup cadence/payload are A-level assumptions from different standard sections, scanned not asserted; RDSS unit cost/power lack a verbatim source. (ii) Harvesting is a model, not a site trace; we sweep peak/initial/blackout precisely because the absolute level is uncertain. (iii) Phase-grid cells use 4 seeds; quantitative claims rest on the 16-seed paired table. (iv) We do not claim field outage distributions; the GE temporal structure is borrowed from ChirpBox (urban) for correlation structure, not absolute level. (v) "Rain-driven acceleration" is never labeled a false precursor—geotechnical truth is left to local node autonomy and is not used by any controller.

## 8. Conclusion

In a pre-disaster mountain monitoring network with Class-A control delay, a split access/backhaul path, intermittent primary backhaul, and scarce solar energy, the intuitive freshness/energy closed loop is a liability: its end-to-end feedback is polluted by the very backhaul outage it cannot act on, driving dense sampling that drains and permanently kills nodes during long outages, and—when obligations tighten to risk-window cadence—it is Pareto-dominated by a feasible static operating point. Across both regimes, a tightness-matched static schedule with automatic primary/backup failover is on the efficient frontier and keeps recoverable nodes alive. We mapped the failure region and the tightness frontier, localized the cause to the feedback signal through controls, ablations, a literature baseline, an oracle, a static frontier, and a per-node causal trace, and stated the design principle—match the real-time operating point to obligation tightness, anchor any feedback to gateway-local deliverability, and move operating-point changes to slow, task-level orchestration. This gives the agentic monitoring runtime a stable communication substrate rather than an unstable one.

## References (to be completed from the transfer ledger; verify each before submission)

- Bacinoglu, Sun, Uysal, Mutlu, "Optimal Status Updating with a Finite-Battery Energy Harvesting Source," arXiv:1905.06679 (verified full abstract/model: monotone threshold, age threshold non-increasing in battery; structural source of `eh_aoi`). *(Earlier draft mis-attributed this arXiv id to "Arafa"; corrected 2026-09-15 after fetching the arXiv record.)*
- Arafa et al., "Sample, Quantize, and Encode: Timely Estimation over Noisy Channels," arXiv:2007.10200 (age-penalty sampling; verify exact author list/venue before submission).
- "Semantic-aware Sampling and Transmission in Real-time Tracking Systems: A POMDP Approach," arXiv:2311.06522 (verified §III-A: controller at transmitter side, observes battery/local buffer/ACK-NACK, same-slot action; verify author list before submission).
- Emami, Zhou, Nabavirazani, Almeida, "LLM-Enabled In-Context Learning for Data Collection Scheduling in UAV-assisted Sensor Networks" (ICLDC), arXiv:2504.14556 / IEEE IoT-J 2025, DOI 10.1109/JIOT.2025.3615410 (verified: finite buffer depth D with overflow loss Eq.5c, UAV-visit limited service, feedback loop; scheduler is an LLM with rule verifier).
- TopoLLM, Digital Communications and Networks 12 (2026) 273–282.
- Ragnoli et al., measured LoRa node energy profile, JLPEA 12(3):47, 2022.
- Wang et al., Guizhou loess-slope LoRa–gateway–4G monitoring, Front. Earth Sci. 2022, 10.3389/feart.2022.899509.
- Kumar et al., asymmetric multi-WAN landslide deployment, Springer MONET, 10.1007/s11276-019-02059-7.
- Fall, "Delay-Tolerant Network Architecture," SIGCOMM 2003.
- CCSDS 734.3-B-1 overbooking; SHETLAND-NET extreme low-rate contact triage *(access unverified in this environment)*.
- DZ/T 0450-2023 §7.4.2.3 / §7.4.3.2, DZ/T 0460-2023 §5.3.7 *(text obtained via document-sharing mirror; official site TLS failed locally — grade D channel)*.
- USGS/Iverson, landslide motion, dilatancy and pore-pressure feedback (rain-driven motion may be genuine acceleration).
- PS-UAV (IEEE WCM 2026), LODA (Computer Communications 2026), WirelessAgent (China Communications 2026), ESWA IIN-recovery, SCS Lifeline/MCP — lineage, abstract-level verification per transfer ledger.

