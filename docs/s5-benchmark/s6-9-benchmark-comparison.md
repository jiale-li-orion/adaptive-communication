# Six agent "network" benchmarks vs. a long-horizon degraded-channel monitoring study

Method: abstracts + full arXiv HTML (`arxiv.org/html/<id>`) read directly, plus GitHub API/repo files for artifacts. Local text extracts in `papers/`. Anything not found in the source is marked **UNVERIFIED**.

Headline: **the answer to (a)+(b)+(c) is NO for all six.**

---

## 1. WirelessOptBench / WirelessOpsAgent — arXiv:2608.08277

- **Fault model**: injected, telemetry-only. "It turns wireless tasks into execution state decision episodes with **controlled telemetry faults** and action constraints." Stress realization = "observation ledger, an execution contract, and a stress realization". Five stress domains × 3 task families × 40 = 600 episodes: schema/unit, freshness/order, availability-brownout, conflict/provenance, mixed. Grounded in "TeleLogs … AIOps2025 and RCA100" for "operational fault vocabulary", but stresses are benchmark-defined: "the taxonomy and oracle are benchmark-defined rather than drawn from an unseen generator or independent deployment study."
- **Object vs. medium**: **OBJECT**. Agent reads an immutable observation ledger and emits APPLY/HOLD/RETRY/ESCALATE/ABSTAIN. The degradation is *freshness/conflict of evidence about the radio*, not loss on the agent's own link.
- **Transport**: none. No simulator, no emulator, no live network: "WirelessOptBench is a controlled benchmark rather than a live network deployment study." Radio state is closed-form SINR/RSRP (Eq. 1–5) + WirelessBench ray-tracing values. No proprietary images/hardware.
- **Energy/power**: **NO.** (Only `P_k` transmit power as an SINR term.) Zero hits for energy/battery/joule across the full text.
- **Terrain/propagation**: indirect only — inherits HKUST OSM ray-tracing-derived CQI values as ledger fields; the benchmark itself does no propagation modeling.
- **Scenario domain**: wireless (RAN slicing + mobility service assurance) — not datacenter/enterprise/disaster.
- **Artifact**: https://anonymous.4open.science/r/wirelessopsbench-artifact-D969/ (anonymous, 4open.science). Runnable-code status **UNVERIFIED** (anonymous host, not inspected).

## 2. NetConfArena — arXiv:2608.23179

- **Fault model**: **none injected** for the agent's task; failure enters only as the agent's own configuration errors. Evaluation is "hidden task-specific executable test cases"; metrics "target the functional correctness of the final network behavior rather than network performance such as latency, congestion, or transient routing dynamics." Fault-tolerant scenarios are explicitly future work: "we plan to add tasks that begin from legacy configurations conflicting with the intended objective, as well as tasks that target fault-tolerant configuration scenarios."
- **Object vs. medium**: **OBJECT** (pure configuration). Agent acts via five primitives: `get_running_config`, `apply_config`, `execute_validation`, `wait`, `submit`.
- **Transport**: **GNS3** emulator with vendor router images: "built on GNS3 … By running vendor router images in GNS3, NetConfArena emulates vendor-specific command syntax, device feedback, and protocol dynamics." Vendor images are a redistribution/licensing dependency; whether the repo ships them is **UNVERIFIED**.
- **Energy/power**: **NO** (no hits).
- **Terrain/propagation**: **NO** (only route *propagation*).
- **Scenario domain**: enterprise/ISP routing & switching (RIP/OSPF/BGP/MPLS/VRF style protocol templates); "controlled configuration scenarios on small topologies".
- **Artifact**: https://github.com/liujona/NetConfArena/ — Apache-2.0, Python, 2 stars, default branch `main`, pushed 2026-08-23; contains `agent/`, `environment/`, `evaluator/`, `mcp_server/`, `task/`, `main.py`, `run.sh`, `requirements*.txt`. Runnable-looking.

## 3. NetArena — arXiv:2506.03231 (ICLR 2026)

- **Fault model**: injected/synthesized per query — "dynamically generates queries via randomized sampling in each evaluation round"; routing app: "Agents diagnose and repair **dynamic faults** (e.g., broken links or invalid forwarding rules) in Mininet."
- **Object vs. medium**: **OBJECT**. Three apps: datacenter capacity planning (Google Mogul-style topology), routing misconfiguration repair (Mininet), microservice policy troubleshooting (Google microservices-demo on Kubernetes).
- **Transport**: Mininet + Kubernetes + Docker: "By integrating with high-fidelity network emulators (e.g., Mininet, Kubernetes)". No proprietary images or hardware; needs Linux netns/Docker.
- **Energy/power**: **NO** (capacity planning is bandwidth/structural constraints only).
- **Terrain/propagation**: **NO**.
- **Scenario domain**: datacenter + cloud microservice.
- **Artifact**: https://github.com/Froot-NetSys/NetArena — Python, 43 stars, no license file, default branch `a2a-agentx`, pushed 2026-07-30; `app-k8s/`, `app-malt/`, `app-route/`, `src/`, `Dockerfile`, `environment_mininet.yml`, `experiments/`. Runnable. (ICLR 2026 poster venue claim: consistent with [iclr.cc listing](https://iclr.cc/virtual/2026/poster/10010955), not stated in the arXiv text.)

## 4. NIKA — arXiv:2512.16381

- **Fault model**: injected, but realistic and trace-grounded in vocabulary: 54 issues from link/host failures to resource contention; "It also orchestrates traffic generation and failure injection"; injection via "Linux Traffic Control (TC) for link-level issues, stress-ng for software contentions, and custom scripts for device-level failures such as process crashes and misconfigurations." 640 incidents.
- **Object vs. medium**: **OBJECT** (diagnosis/root-cause). Closest to monitoring: agents get 30+ MCP tools (ping, traceroute, iperf, HTTP latency, port counters, flow/routing tables, logs) and must detect → localize → RCA. Explicitly no mitigation: "NIKA currently focuses on diagnosis tasks (detection, localization, RCA) but does not yet support evaluating mitigation actions."
- **Transport**: **Kathará** container emulator: "We build NIKA on top of Kathará, an open-source container-based network emulator. Traffic workloads are generated via iperf3 and ApacheBench." No proprietary images/hardware; no special hardware required.
- **Energy/power**: **NO** (no hits). Admits emulation limits: "it cannot faithfully reproduce issues that manifest only in high-speed networks, or that require specialized hardware."
- **Terrain/propagation**: **NO**.
- **Scenario domain**: DC CLOS (scalable), campus 3-tier (scalable), ISP backbone meshed (scalable), SDN cloud POP fabric (scalable), P4 testbed. Sizes S/M/L ≈ 11/27/101 nodes. Full eval ≈ 7–15 h wall clock (long, but single-shot incident, not continuous monitoring).
- **Artifact**: https://github.com/sands-lab/nika — Python, 58 stars, no license file, pushed 2026-09-07; `benchmark/`, `src/`, `config/`, `scripts/`, `tests/`, `docs/`, `AGENTS.md`. Runnable.

## 5. NetOpsBench — github.com/NetX-lab/NetOpsBench

- **Fault model**: injected, explicitly: "run reproducible fault scenarios on live SONiC-VS / Containerlab topologies"; "labeled faults run against repeatable SONiC-VS and Containerlab topologies"; custom faults supported (`examples/faults/custom_fault_pack`, `custom-faults.mdx`). 12 canonical types across 5 categories: link (`link_down`, `link_flapping`), routing (`blackhole_route`, `static_route_misconfig`, `bgp_neighbor_misconfig`, `route_policy_misconfig`), impairment (`mtu_mismatch`, `packet_loss`, `packet_corruption`, `high_latency`), system (`device_down`), ACL (`acl_misconfig`). Impairments are `tc`-style parameterized constants (`loss_pct=30`, `latency_ms=100`, `corruption_pct=20`) — not measured from real links. **No paper found; repo-only.**
- **Object vs. medium**: **OBJECT**, and the closest to operational monitoring of the six: agent inspects "live Pingmesh, BGP, gNMI, syslog, and switch state"; scored for detection, fault type, device/interface localization, runtime, tool calls, token usage.
- **Transport**: Containerlab + Docker, SONiC-VS virtual switch images (`yyyyyt123/netopsbench-sonic-vs-202505-telemetry`, `docker.io/yyyyyt123/netopsbench-client`) — public on Docker Hub, **Linux-only**: "NetOpsBench runtime execution requires Linux because Containerlab depends on Linux networking primitives. Windows and macOS hosts are not supported." Scales up to Fat-tree K=12 (180 switches, 144 clients) → heavy host RAM/CPU. No proprietary vendor images (SONiC is open); no physical hardware.
- **Energy/power**: **NO** (no energy/power terms in README/docs inspected).
- **Terrain/propagation**: **NO**.
- **Scenario domain**: datacenter / AI-infrastructure fabrics (CLOS + Fat-tree).
- **Artifact**: repo MIT-licensed, Python, 30 stars, pushed 2026-08-24; `netopsbench/`, `scenarios/`, `containers/`, `native/`, `examples/`, `docs/`, `tests/`, `pyproject.toml`. Runnable. Trace dataset (Hugging Face, 319 agent trajectories) is agent trajectories, **not** physical-layer traces.

## 6. WirelessBench / WirelessAgent++ — arXiv:2603.00501

- **Fault model**: **none.** No failure injection, no channel degradation of any kind. Ground truths are deterministic/expert: "All ground truths are constructed from deterministic rules or expert solutions, ensuring reproducibility." The only "noise" is LLM-output stochasticity and numerical precision.
- **Object vs. medium**: **OBJECT** at the *static problem* level (classify service, predict CQI, allocate bandwidth). No live network, no closed loop against a network environment; the closed loop is the MCTS workflow optimizer over datasets.
- **Transport**: none — datasets only. WCHW 1,392 textbook problems; WCNS/WCMSA generated from HKUST OSM geometry + a ray-tracing tool with `TX power` etc. No simulator, no images, no hardware.
- **Energy/power**: **NO** (only "water-filling power allocation" and TX power as formula topics).
- **Terrain/propagation**: **partial** — best of the six for *propagation*: "A site-specific ray-tracing engine estimates received signal quality based on user positions… real-world building geometry extracted from OpenStreetMap (OSM) data covering three HKUST campus regions." But it is a *tool the agent calls to compute CQI*, not a channel the agent's traffic traverses, and it is 2D building footprints with a default building height (not terrain/elevation).
- **Scenario domain**: wireless / campus RAN (slicing, mobility).
- **Artifact**: https://github.com/jwentong/WirelessBench — MIT, Python, 9 stars, pushed 2026-03-04; `benchmarks/`, `data/`, `config/`, `preprocessing/`, `evaluate.py`, `requirements.txt`, `scripts/`. Runnable (data + eval harness).

---

## Summary table (5 dimensions)

| Benchmark | Fault model | Network role | Transport / images | Energy/power | Terrain/propagation |
|---|---|---|---|---|---|
| WirelessOptBench (2608.08277) | Injected **telemetry** faults (5 domains, 600 eps); "controlled telemetry faults" | OBJECT (action authorization) | None; closed-form SINR + inherited ray-tracing CQI | NO | Indirect (inherited CQI only) |
| NetConfArena (2608.23179) | **None injected**; agent's own config errors only; fault tolerance = future work | OBJECT (config) | GNS3 + **vendor router images** (licensing) | NO | NO |
| NetArena (2506.03231) | Injected/synthesized per generated query ("dynamic faults") | OBJECT (planning, repair, policy) | Mininet + K8s + Docker; open | NO | NO |
| NIKA (2512.16381) | Injected via **TC / stress-ng / scripts**; 54 issues, 640 incidents | OBJECT (detect → localize → RCA) | Kathará containers + iperf3/ApacheBench; open | NO | NO |
| NetOpsBench | Injected **`tc`-style constants** (loss 30%, latency 100 ms, corruption 20%) + link/routing/system/ACL faults | OBJECT (monitoring/diagnosis) | Containerlab + SONiC-VS Docker; **Linux-only, heavy** | NO | NO |
| WirelessBench (2603.00501) | **None**; deterministic/expert ground truth | OBJECT (static problem solving) | None; datasets + OSM ray-tracing tool | NO | Partial (2D building geometry + ray tracing) |

**Energy/power is absent from all six.** **Terrain/propagation appears in exactly one** (WirelessBench) and only as a callable CQI tool.

---

## The plain answer

**(a) Does the agent's own operation channel degrade? — NO, in all six.** In every benchmark the agent's tool calls, MCP traffic, SSH/CLI session, and LLM API calls ride an undegraded channel. The network is always the **OBJECT** of the agent's action or diagnosis, never the **MEDIUM** that carries the agent's own telemetry. Searched all six full texts for agent-channel constructs (agent traffic/latency/connection, out-of-band control plane, edge-deployed agent) — **zero hits**.

**(b) Are failures trace-driven from real terrain/power? — NO, in all six.** Every failure is injected, synthesized, or absent. The strongest claims are *vocabulary*-grounded (WirelessOptBench cites TeleLogs/AIOps2025/RCA100 for the fault taxonomy; NIKA curates "realistic" issues) — but the realizations are benchmark-defined. WirelessOptBench says so itself: "the taxonomy and oracle are benchmark-defined rather than drawn from an unseen generator or independent deployment study." NetOpsBench's impairments are hand-set constants. No benchmark derives a failure from a propagation model, elevation data, RF measurement trace, or a power/energy state.

**(c) Is the task a long-horizon monitoring mission? — NO.** NIKA and NetOpsBench are the nearest, and both are *episodic*: one incident → detect/localize/RCA → episode ends. NIKA's long runtime (7–15 h for the full 150-incident suite) is aggregate wall clock, not one long mission; NetOpsBench's "efficiency" metrics are *tool calls and tokens*, not elapsed monitoring time. Neither penalizes an agent for missing an incident that occurs mid-episode, decays a channel state over time, or asks the agent to maintain situational awareness across hours of degrading conditions.

### Partial coverage, stated exactly

- **NIKA** goes furthest on realism of *injection* (TC/stress-ng/process crashes, 54 issues, sizes 11→101 nodes) and gives the richest passive/active monitoring tool surface — but the agent is out-of-band, faults are injected not measured, there is no energy model, no propagation model, and each incident is a bounded diagnostic episode.
- **NetOpsBench** goes furthest toward *operations* framing (Pingmesh, gNMI, syslog, 12 fault families, up to 180 switches, quality/efficiency scoring) — but the degradations are `tc` constants, the agent's own link is clean, and scoring is single-incident diagnosis.
- **WirelessBench** is the only one with any *physical* channel modeling (OSM ray tracing over HKUST), and it is the only one with **no faults at all** and no live environment whatsoever. It is the farthest of the six from (a) and (c).

**Conclusion: no benchmark among the six satisfies (a), (b), or (c), singly or in combination. A study whose premise is a long-horizon monitoring mission over a channel that degrades the agent's own operation, with failures trace-driven from real terrain and power, is not covered by any of them — and is not merely under-served but structurally out of scope for the whole category, which consistently fixes the network as the object of control rather than the medium of the agent.**
