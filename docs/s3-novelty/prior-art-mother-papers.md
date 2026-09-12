# Literature Reconnaissance: "Mother Papers" for

> ⚠️ **定位说明（2026-09-12 追加）**：本文写作时的论文标题是
> *"Disruption-Tolerant Runtime for Tool-Using Agents in Emergency Communication Networks"*，
> **该定位已被取代**。当前定位见 [`../../README.md`](../../README.md)：
> **agent runtime 位于通信实体之上，在它们动态上线 / 掉线 / 退化 / 恢复时维持任务执行**。
> 本文的**调研内容与引用仍然有效**；只有"论文标题/中心"这一层需要按新定位重读。



## *Disruption-Tolerant Runtime for Tool-Using Agents in Emergency Communication Networks*

**Reconnaissance date:** 2026-09-12 (UTC)
**Method:** `web_search` plus direct retrieval of primary metadata APIs (Crossref, OpenAlex, DOAJ, Unpaywall, GitHub API) and arXiv abstract/HTML pages. Where a claim is not directly verifiable it is marked **UNVERIFIED**.
**Cached primary sources:** `/home/orion/Communications/recon/cache/`

> **Read this first.** Two of the six requested items could not be read in full text (TopoLLM — ScienceDirect bot-wall; ICG-Restore — MDPI bot-wall), and three IEEE Xplore items could not be opened at all. Those entries are marked accordingly. Nothing below is invented: every DOI, arXiv ID, volume/page and author list was read from a metadata API or the publisher's own abstract page.

---

## 1. TopoLLM

- **Exact title:** TopoLLM: LLM-driven adaptive tool learning for real-time emergency network topology planning
- **Venue + year:** *Digital Communications and Networks* (Elsevier BV / KeAi), **Vol. 12, Issue 2, pp. 273–282**; Crossref `issued` = **2026-02**; OpenAlex `publication_date` = **2025-10-18** (online-first). So: DOI registered 2025, issue-dated 2026.
- **Authors:** Yizhuo Ma; Rongzheng Wang; Shuang Liang; Guangchun Luo; Ke Qin
- **Institution:** University of Electronic Science and Technology of China (OpenAlex `authorships.institutions`)
- **DOI:** `10.1016/j.dcan.2025.10.002` — **CONFIRMED** against the Crossref API. The DOI in the task prompt is correct. Note the DOI carries a `2025` fragment while the issue is dated 2026 — that is normal for Elsevier online-first.
- **URLs:** [https://doi.org/10.1016/j.dcan.2025.10.002](https://doi.org/10.1016/j.dcan.2025.10.002) · [ScienceDirect S2352864825001476](https://www.sciencedirect.com/science/article/pii/S2352864825001476) · [DOAJ record](https://doaj.org/article/7001296cad924a6cba163383d45828eb)

**What it actually does (abstract-level only — see gap note).** Emergency communication infrastructure is described as often destroyed first in disasters, so rapid UAV + satellite deployment is needed for rescue-critical links. Existing emergency-network design is expert-driven and suffers from poor resource allocation and congestion. TopoLLM couples an LLM's reasoning with **TopoTool**, a domain-specific optimization toolkit built for "high-precision and load-balanced network planning in disaster scenarios." An **adaptive tool-selection mechanism** drives autonomous generation of resilient topologies and resource allocation, reducing human intervention. Evaluation is on **simulated disaster scenarios**, reporting higher-accuracy and more robust topologies versus existing approaches.

**Tool / execution semantics notes.** Only two things are verifiable at abstract level: (i) a domain toolkit named **TopoTool**, and (ii) an "adaptive tool-selection mechanism" that picks what to call. **Nothing verifiable** about how tools are invoked, what happens on tool failure/timeout/disconnect, whether state mutations are transactional, or whether recovery/replay exists.

**Artifact availability:** No code or dataset link found — not in the Crossref record, not in the DOAJ record, and not in the accessible abstract. **Not found.**

**⚠️ Major gap.** Both `curl` and a headless Chromium (Playwright) fetch of the ScienceDirect article returned a JavaScript shell containing **zero** occurrences of the string "TopoLLM". The full text, its tool catalogue, its environment and its failure semantics are **UNVERIFIED**. This is the single largest hole in this report and the first thing to close manually (institutional ScienceDirect access).

---

## 2. 6GAgentGym

- **Exact title:** 6GAgentGym: Tool Use, Data Synthesis, and Agentic Learning for Network Management
- **Venue + year:** **arXiv preprint, 31 March 2026** — arXiv:2603.29656v1, primary class **cs.NI**, cross-list cs.AI. **No journal reference, no DOI** (both fields absent from the arXiv record). Not a published venue paper as of this date.
- **Authors:** Jiao Chen; Jianhua Tang; Xiaotong Yang; Zuohong Lv
- **Institutions (read from HTML full text "Affiliation:" markers):** (1) Shenzhen Smart City Technology Development Group Company, Ltd.; (2) Shien-Ming Wu School of Intelligent Engineering, South China University of Technology; (3) China Unicom Group, Co., Ltd.
- **URLs:** [https://arxiv.org/abs/2603.29656](https://arxiv.org/abs/2603.29656) · [HTML full text](https://arxiv.org/html/2603.29656) · [ADS record](https://ui.adsabs.harvard.edu/abs/2026arXiv260329656C/abstract)

**What it actually does.** It is a *closed-loop interactive environment + data-synthesis pipeline + training recipe* for 6G network management agents, motivated by the claim that "45% of network outages stem from configuration and change management failures." Three components:

1. **Interactive environment with 42 typed tools**, partitioned by effect on network state into three disjoint sets: **Observation** (16 read-only tools), **Reasoning** (22 pure-computation tools), **Configuration** (4 state-mutating tools). Named tools in the paper's catalogue include `read_telemetry`, `check_network_state`, `get_signal_strength`, `scan_available_gnbs`, `get_edge_load`, `get_slice_status`, `predict_sla_violation`, `check_handover_status`, `monitor_interference`, `check_link_quality`, `select_recovery_strategy`, `check_migration_feasib[ility]`, `risk_assessment`, `evaluate_intent_feasib[ility]`, `check_geofence`, `path_planning`, `compute_energy_budget`, `select_offload_target`, `negotiate_priority`, `set_waypoint`, `adjust_altitude`, `adjust_speed`, `collision_avoidance`, `swarm_formation`, `assign_task`, `send_alert`, `request_handover`, `log_decision`, `update_mission_plan`, `broadcast_status`, **`heartbeat`**, `verify_sla_compliance`, `validate_mission_compl[iance]`, and — in the 4-tool Configuration set — **`switch_network_slice`**, **`graceful_degradation`**, **`edge_offload`**, **`trigger_slice_realloc[ation]`**.
2. **A learned "Experiment Model"** calibrated on NS-3 simulation data that predicts six-dimensional network state transitions. This is the execution backend: tools execute against the Experiment Model, **not** against a live network.
3. **6G-Forge** data synthesis + **6GAgentBench** evaluation + two-stage training (agentic SFT then RL with DAPO).

**Benchmark structure.** Three difficulty tiers: **L1** (≤3 steps, sense-decide-act chains), **L2** (4–7 steps, e.g. degradation detection and slice reallocation), **L3** (≥8 steps, long-horizon multi-agent workflows under network degradation). Five evaluation domains: network slicing, edge offloading, UAV control, **degradation recovery**, and multi-agent coordination. Tasks where any model exceeds 80% zero-shot success are excluded. Training data: 3,000 real NS-3 trajectories (seeds 1–50) + 50,000 synthetic (30,000 golden + 20,000 error-recovery augmented) = 53,000; evaluation uses a disjoint seed range (51–80) plus ROUGE-L leakage filtering at ≥0.7. Models evaluated include GPT-5, Claude-Sonnet-4, Gemini-2.5-Pro, Qwen3-VL-72B/8B/4B, DeepSeek-V3, Llama-4-Scout; the fine-tuned 8B `6GAgent-8B` is reported as comparable overall to GPT-5 with an advantage on long-horizon tasks. Ablations: closed-loop trajectories +4.8% over open-loop; error-recovery +1.3%; NS-3 real data +2.2%; agentic RL +4.8%.

**Tool-failure / timeout / disconnect semantics — the honest read.** The paper's **only** error path is an *offline data-synthesis* construct. In 6G-Forge Step 3, each candidate trajectory is executed step-by-step against the Experiment Model M_θ; "when M_θ returns an error, the teacher is re-prompted to correct the failed step," producing an **error-recovery augmented trajectory**. Both golden and error-recovery traces are retained for training. That is a *data augmentation* device, not a runtime contract. Specifically absent: no tool **timeout**, no **outcome-unknown** after dispatch, no **idempotency key**, no **duplicate-side-effect** suppression, no **lease**, no **reconcile loop**, no durable replay. ("Duplicate" appears only as ROUGE-L deduplication of training trajectories.) The reward function penalises malformed tool calls (`R_format`) — format validity, not failure semantics.

**Is network state change real?** **No.** State transitions come from a *learned* Experiment Model calibrated on NS-3; NS-3 is used offline for seeds and 3k real trajectories. The authors state this limitation explicitly: *"The Experiment Model approximates NS-3 dynamics but does not capture full protocol-level transients, particularly during handover and failure recovery."* They also note the 42-tool set excludes radio-level operations (beamforming, power control). **This sentence is arguably the single best citation hook for the proposed paper.**

**Artifact availability:** **No code or dataset release found.** The paper contains no repository link, and a GitHub repository search for "6GAgentGym" returns **0 results**. The paper mentions an internal Streamlit dashboard over NS-3 CSV traces, but it is not published. Treat as **not released / not found**.

---

## 3. WirelessAgent and WirelessAgent++

### 3a. WirelessAgent (original)

- **Exact title:** WirelessAgent: Large Language Model Agents for Intelligent Wireless Networks
- **Venue + year:** *China Communications*, **Vol. 23, No. 3, pp. 265–285, March 2026**, DOI `10.23919/jcc.fa.2025-0163.202603` — **verified via Crossref** (authors listed there as Tong Jingwen; Guo Wei; Shao Jiawei; Wu Qiong; Li Zijian; Lin Zehong; Zhang Jun).
  - Also exists as **arXiv:2409.07964** (12 Sep 2024, cs.NI) and as **arXiv:2505.01074** (2 May 2025), whose comment states it "is an extended version of a previous magazine version and is now submitted to a journal for possible publication," with an arXiv admin note flagging **text overlap with 2409.07964**. So there are three records of one evolving work; the 2505.01074 extended version implements the framework "based on agentic workflows and the **LangGraph** architecture."
- **Authors:** Jingwen Tong; Jiawei Shao; Qiong Wu; Wei Guo; Zijian Li; Zehong Lin; Jun Zhang
- **URLs:** [https://doi.org/10.23919/jcc.fa.2025-0163.202603](https://doi.org/10.23919/jcc.fa.2025-0163.202603) · [arXiv:2409.07964](https://arxiv.org/abs/2409.07964) · [arXiv:2505.01074](https://arxiv.org/abs/2505.01074)

**What it actually does.** A four-module LLM agent framework mirroring cognition — **perception** (text understanding, multimodal processing), **memory**, **planning** (reasoning, retrieval, reflection), **action** (text generation, **tool manipulation**) — with external knowledge bases and tools. The contribution is largely conceptual plus a **proof-of-concept case study on network slicing management**: intent understanding, slice resource allocation, maintaining optimal performance.

**Tool / execution semantics.** Essentially none. The paper *states the desideratum* that an agent "should be able to respond rapidly to immediate changes and even failures in telecommunication systems" and "figure out effective countermeasures and adapt its operational strategies to avoid disruptions" — but provides no mechanism, no error taxonomy, no retry/timeout/idempotency discussion. Its action module merely includes "tool manipulation" as a capability heading. This is a vision-plus-demo paper; it is a good *motivational* citation, not a semantics citation.

**Artifact availability:** GitHub [https://github.com/weiiguo/Wireless-Agent](https://github.com/weiiguo/Wireless-Agent) exists (13 stars, created 2024-09-08, last push 2025-05-06) but **its contents are a single `README.md`** — no code. Practical availability: effectively **README only**.

### 3b. WirelessAgent++

- **Exact title:** WirelessAgent++: Automated Agentic Workflow Design and Benchmarking for Wireless Networks
- **Venue + year:** **arXiv preprint, 28 February 2026**, arXiv:2603.00501v1, cs.NI. Author comment: *"This manuscript has submitted to a possible Journal for publication"* → **no venue yet, not peer-reviewed as of this date.**
- **Authors:** Jingwen Tong; Zijian Li; Fang Liu; Wei Guo; Jun Zhang
- **URLs:** [https://arxiv.org/abs/2603.00501](https://arxiv.org/abs/2603.00501) · [code](https://github.com/jwentong/WirelessAgent-R2)

**What it actually does.** It reframes *agent design* as *program search*: each agentic workflow is executable code composed of modular **operators**, and a domain-adapted **Monte Carlo Tree Search** searches over operator compositions. It introduces **WirelessBench**, a three-part benchmark: **WCHW** (Wireless Communication Homework — knowledge reasoning), **WCNS** (Network Slicing — code-augmented tool use), **WCMSA** (Mobile Service Assurance — multi-step decision-making). Reported results: 78.37% / 90.95% / 97.07% test scores, total search cost **below $5 per task**, beating SOTA prompting baselines by up to 31% and general-purpose workflow optimizers by 11.1%.

**Tool / execution semantics — the most concrete in the wireless group, but still thin.** Two findings from the full text:
- **`Programmer` operator:** "Generates and executes Python code (**3 retries, 30s timeout per attempt**)." This is the *only* timeout and retry budget in the paper, and it applies to **code execution inside a workflow**, not to wireless/network tool calls.
- **ReAct-based `ToolAgent` operator** (Algorithm 1): takes a max iteration count *I* and maintains a **consecutive-failure counter `n_fail`** across the loop — so there is a failure-accounting notion, but it is loop-termination bookkeeping rather than a semantic contract.
- **Mutation dedup:** before a workflow mutation is accepted, a modification check verifies it "is not an exact duplicate of a previously failed modification" and contains no known harmful patterns. This is **search-space** deduplication, not runtime side-effect deduplication.

**⚠️ Important nuance on "outage."** The token "outage" appears twice in the paper and **both** occurrences are *Rayleigh/Rician outage probability* inside the wireless-mathematics calculator tool (`erfc`, `Q`-function, Bessel, Marcum Q, BER, Shannon capacity, fading statistics). It is **physical-layer outage probability, not service outage or loss of connectivity.** Do not cite this paper as handling connectivity outage.

**Artifact availability:** [https://github.com/jwentong/WirelessAgent-R2](https://github.com/jwentong/WirelessAgent-R2) — 22 stars, Python, created 2026-01-13, last push 2026-08-24. Described as an MCTS-based workflow optimization system. A second repo, `github.com/jwentong/WirelessBench`, is referenced. **Code released: yes.**

---

## 4. α³-Bench

- **Exact title:** $\alpha^3$-Bench: A Unified Benchmark of Safety, Robustness, and Efficiency for LLM-Based UAV Agents over 6G Networks
- **Venue + year:** **arXiv preprint, 1 January 2026**, arXiv:2601.03281v1, primary class **eess.SY**, cross-list cs.AI; 20 pages; license CC BY 4.0. **No journal reference, no DOI.** (I examined v1; I did not confirm whether later versions exist.)
- **Authors:** Mohamed Amine Ferrag; Abderrahmane Lakas; Merouane Debbah
- **Institutions:** **UNVERIFIED** — arXiv metadata carries no affiliations and I did not open the PDF's affiliation block.
- **URLs:** [https://arxiv.org/abs/2601.03281](https://arxiv.org/abs/2601.03281) · [HTML](https://ar5iv.labs.arxiv.org/html/2601.03281) · [dataset](https://github.com/maferrag/AlphaBench)

**What it actually does.** It benchmarks LLM-driven UAV autonomy as a **multi-turn conversational reasoning-and-control** problem under dynamic 6G conditions. Each mission is a "language-mediated control loop" between an LLM UAV agent and a **human operator**, with hard constraints on schema validity, mission policy, **speaker alternation** (`r_t ≠ r_{t−1}`), and safety. Corpus: **113k conversational UAV episodes** grounded in UAVBench scenarios; evaluation on a **fixed subset of 50 episodes per scenario** with **deterministic decoding** across **17 SOTA LLMs**. Metric: composite **α³** unifying six pillars — Task Outcome, Safety Policy, **Tool Consistency**, Interaction Quality, **Network Robustness**, Communication Cost — plus efficiency-normalized scores per second and per 1k tokens. Headline result: Task Outcome and Safety Policy ≥ 0.95 for several frontier models, but **Network Robustness drops 30–40% under degraded 6G conditions**.

**Environment and network state.** Each turn injects a 6G network state vector **n_t = (slice, latency, jitter, packet loss, throughput, edge load)**. The degradation rule is explicit: when **lat_t > 40 ms or loss_t ≥ 1%**, the policy must choose from a *communication-safe* action subset 𝒜_adaptive(n_t) ⊂ 𝒜_total — "which include decisions like switching to URLLC slice, **buffering commands**, or postponing sensor activation." Failing to adapt lowers Network Robustness and Task Outcome. Observations are "synthetically generated from the underlying UAV state, network context, and action semantics, following a **deterministic execution logic augmented with controlled stochastic perturbations**." **So the network state is simulated, not a real testbed and not NS-3.**

**Tool invocation semantics — the closest thing in the wireless literature to a tool contract.** There is a dedicated subsection **"Operational Semantics of MCP and A2A Tools"**:
- Each tool is defined by "its inputs, outputs, affected state variables, and **execution constraints**, thereby eliminating ambiguity in how conversational actions influence UAV behavior and observations."
- **MCP action:** issued as `(mcp, name, args)`, **deterministically produces** an observation `(tool = name, result)`. `read_telemetry` returns position/velocity/yaw/battery/link-quality; control tools (`set_waypoint`, `navigate_to`, `set_altitude`) modify pose/trajectory subject to altitude bounds, geofencing and kinematic feasibility; `switch_network_slice` modifies the active slice "while preserving safety and protocol constraints"; sensor tools alter the observation space without changing flight dynamics.
- **A2A action:** issued as `(a2a, task, to, payload)`, acknowledged by `(task, from, status, payload)`. Crucially: *"A2A interactions are asynchronous and **logically instantaneous** at the dialogue level, but their availability and reliability are conditioned on the current 6G network state."*
- Usage profile: `read_telemetry` alone is >21% of all MCP calls, averaging >2 invocations per episode.

**Tool failure / timeout / disconnect.** **Not modelled.** Tools are deterministic; A2A is logically instantaneous; there is no timeout, no outcome-unknown, no idempotency, no duplicate-side-effect handling, no reconnection. The word "retry" appears only for **episode generation** (max 3 attempts; if schema validation fails, stricter constraints are appended; exhausted attempts are written to disk as **failure stubs** so generation failure rates are not optimistically biased). "Tool Consistency" measures protocol/schema conformance of calls, **not** failure recovery.

**Artifact availability:** **Dataset released** — [https://github.com/maferrag/AlphaBench](https://github.com/maferrag/AlphaBench) (10 stars, created 2025-12-21, last push 2026-01-08). Top-level contents: `113k_episodes/`, `Figures/`, `Research Paper/`, `Results_Evaluation/`, `README.md` (27 KB). No language/`license` field in repo metadata → likely data+docs only, no runnable harness. The README was not opened, so training/harness claims are unverified.

**Immediately related companion paper (worth knowing).** **$\alpha^3$-SecBench: A Large-Scale Evaluation Suite of Security, Resilience, and Trust for LLM-based UAV Agents over 6G Networks**, **arXiv:2601.18754** (26 January 2026, cs.CR), **same three authors**. It augments benign α³-Bench episodes with **20,000 validated security-overlay attack scenarios** across seven autonomy layers (sensing, perception, planning, control, communication, edge/cloud infrastructure, LLM reasoning) and evaluates agents on three orthogonal dimensions starting with security. This is the natural "adversarial/degraded" companion to α³-Bench. URL: [https://arxiv.org/abs/2601.18754](https://arxiv.org/abs/2601.18754)

---

## 5. ICG-Restore and ComAgent

### 5a. ICG-Restore

- **Exact title:** ICG-Restore: Intent-Constrained, Graph-Enhanced LLM Planning with Minimal-Edit Repair for Post-Disaster Emergency Communication Recovery
- **Venue + year:** ***AI* (MDPI), Vol. 7, Issue 8, Article 294, published 2 August 2026**, DOI `10.3390/ai7080294` — **verified via Crossref and OpenAlex**. Gold open access.
- **Authors:** Jinyin Bai; Wei Zhu; Xiangchen Wang; Shiluo Guo; Zongzhe Nie; Tianjin Ni; Jinji Zhou; Kaiyang Kou; Lingxin Xu; Yihao Zhong
- **Institutions:** Beijing Satellite Navigation Center; National University of Defense Technology; Wuhan University (OpenAlex `authorships.institutions`)
- **URLs:** [https://doi.org/10.3390/ai7080294](https://doi.org/10.3390/ai7080294) · [MDPI page](https://www.mdpi.com/2673-2688/7/8/294) · [DOAJ](https://doaj.org/article/?q=doi%3A10.3390%2Fai7080294)

**What it actually does.** It treats post-disaster emergency communication recovery as a **high-level constrained planning** problem (service priorities, inter-object dependencies, resource budgets, time windows), not a link-repair task. Pipeline: compile natural-language requests + structured network observations + operational rules into a **task-intent object**; retrieve context from a **heterogeneous scenario graph** and a **restoration knowledge graph**; generate **stage-wise restoration candidates**; apply **bounded local corrections** ("minimal-edit repair") to candidates that violate encoded prerequisites, stage-order relations, budget limits or temporal constraints; validate feasibility under an encoded high-level constraint model; then rank accepted candidates via a "safety-aware agent executor operating in an **abstract restoration action space**." Evaluation is on **controlled abstract topologies** covering 3 scales, 4 restoration tasks and 5 environmental evolution modes. Versus Direct-LLM: CSR +1.99%, CRS +24.56%, WCTС@5 structural-alignment +38.87%.

**Tool / execution semantics.** The paper is explicit that it works with "**abstract executors or schedulers**" and labels "minimal-edit" as "**a descriptive label for a bounded local repair principle** that prioritizes less disruptive corrections" — i.e. **planning-time constraint repair, not a runtime transaction/idempotency mechanism**. A search snippet of the article's own limitations section reads: *"the present evaluation focuses primarily on offline high-level planning by a single planner and does not fully characte…"* (truncated). **There is no evidence of tool timeout, retry, duplicate-side-effect, or reconnect semantics.**

**Artifact availability:** **Not found / UNVERIFIED.** The article is gold OA, but MDPI served `Access Denied` (HTTP-level bot wall) to both `curl` with browser headers and headless Chromium, so I could not read the Data/Code Availability statement. This is a fast manual check for anyone with a browser.

### 5b. ComAgent — ⚠️ name collision, read carefully

There are **two different works called "ComAgent"**, which is worth knowing before citing.

**(i) ComAgent: Multi-LLM based Agentic AI Empowered Intelligent Wireless Networks**
- **arXiv preprint, 27 January 2026**, arXiv:2601.19607v1, cs.AI. **No journal reference, no DOI.**
- **Authors:** Haoyun Li; Ming Xiao; Kezhi Wang; Robert Schober; Dong In Kim; Yong Liang Guan
- **URL:** [https://arxiv.org/abs/2601.19607](https://arxiv.org/abs/2601.19607)

*What it does:* a multi-LLM agentic framework with a closed-loop **Perception–Planning–Action–Reflection** cycle coordinating specialized agents for **literature search, coding, and scoring**, autonomously producing **solver-ready mathematical formulations and reproducible simulations** for wireless problems. Motivation: manual translation of high-level intents into mathematical formulations is a bottleneck, and monolithic LLMs "lack sufficient domain grounding, constraint awareness, and verification capabilities." Evaluated on **beamforming optimization** (expert-comparable) and other wireless tasks.

*Execution semantics:* one **"Error handling branch"** — if the simulation **fails to compile or execute**, the Scoring Agent captures the error signal (syntax errors or runtime exceptions) and reports it to the Coding Agent, which "performs self-reflection to diagnose the root cause and rectify the issue in the subsequent iteration"; the alternative "wireless validity branch" handles physically meaningless results. **This is compile/execution error handling in a code-generation loop.** Full-text keyword counts: `timeout` **0**, `retry` **0**, `idempot` 0, `disconnect` 0. No repository link appears anywhere in the paper.

**(ii) From Large AI Models to Agentic AI: A Tutorial on Future Intelligent Communications**
- **Venue:** ***IEEE Journal on Selected Areas in Communications* (JSAC), 2026**, DOI `10.1109/JSAC.2026.3660010` — **verified via Crossref**. Authors per Crossref: Feibo Jiang; Cunhua Pan; Kezhi Wang; Pietro Michiardi; Octavia A. Dobre; Merouane Debbah. (The GitHub README lists a different, earlier author set — Feibo Jiang, Cunhua Pan, Li Dong, Kezhi Wang, Octavia A. Dobre, Merouane Debbah — matching arXiv:2505.22311 v1; the published JSAC list is the one above.)
- **URLs:** [https://doi.org/10.1109/JSAC.2026.3660010](https://doi.org/10.1109/JSAC.2026.3660010) · [arXiv:2505.22311](https://arxiv.org/abs/2505.22311)

*What it does:* a long tutorial on LAMs (Transformers, ViT, VAE, diffusion, DiT, MoE) and Agentic AI for intelligent communications — including an LAM-based agentic system with **planners, knowledge bases, tools, and memory**, and a multi-agent framework with data retrieval, collaborative planning and reflective evaluation for 6G. This is the survey-grade reference for "tools in communication agents."

**Artifact caveat:** the repo [https://github.com/jiangfeibo/ComAgent](https://github.com/jiangfeibo/ComAgent) (35 stars) is advertised as "the code repository" for the JSAC tutorial, but its **entire contents are `README.md` + a `fig/` directory — there is no code.** Combined with case (i) having no repository at all, **"ComAgent" has no working released code** as far as I can verify.

---

## 6. Surveys on agentic wireless networks / LLM agents for network management (2025–2026)

All five below were verified through Crossref or the arXiv abstract page unless noted.

| # | Title | Venue + year | Identifiers | Notes |
|---|---|---|---|---|
| S1 | **LLM-Powered Agentic AI for 5G/6G Networks: A Tutorial and Survey on Architectures, Protocols, and Standardization** | arXiv preprint, **17 Jul 2026** | [arXiv:2607.16066](https://arxiv.org/abs/2607.16066) | Authors: Mazene Ameur; Abdelkader Mekrache; Bouziane Brik; Adlen Ksentini (cs.NI). Two-part tutorial-and-survey. **Part I** formalises the control, management and AI-native planes of 5G/6G, then covers agentic foundations: **reasoning, planning, tool use, multi-agent coordination, and evaluation**. **Part II** maps agentic capabilities onto 5G/6G control surfaces, **standardization**, and major 6G initiatives. Gap it claims: existing surveys treat the two domains in isolation. *This is the single most on-point survey for the proposed paper's framing.* |
| S2 | **Towards fully autonomous network management: A survey on LLM-based Multi-Agent Systems** | ***ICT Express*, 2026** (Crossref issued 2026-08) | DOI [`10.1016/j.icte.2026.07.003`](https://doi.org/10.1016/j.icte.2026.07.003) | Authors: Ki-Hyeon Kim; Cheoneum Park; Hyeonjeong Lee; Chanjin Park; Taehoon Kim; Mi-Jung Choi. Verified via Crossref. Abstract not read — **content summary UNVERIFIED**. |
| S3 | **Agentic Graph Neural Networks for Wireless Communications and Networking Toward Edge General Intelligence: A Survey** | ***IEEE Communications Surveys & Tutorials*, 2026** | DOI [`10.1109/comst.2026.3651990`](https://doi.org/10.1109/comst.2026.3651990) | Authors: Yang Lu; Shengli Zhang; Chang Liu; Ruichen Zhang; Bo Ai; Dusit Niyato. Verified via Crossref. Abstract not read — **content summary UNVERIFIED**. |
| S4 | **From Large AI Models to Agentic AI: A Tutorial on Future Intelligent Communications** | ***IEEE JSAC*, 2026** | DOI [`10.1109/JSAC.2026.3660010`](https://doi.org/10.1109/JSAC.2026.3660010) | Authors: Feibo Jiang; Cunhua Pan; Kezhi Wang; Pietro Michiardi; Octavia A. Dobre; Merouane Debbah. Full abstract read (see §5b(ii)). Covers planner / knowledge-base / tool / memory components of communication agents. |
| S5 | **Agent-Native Wireless Communications: Architecture, Opportunities, and the Road Ahead** | arXiv preprint, **15 May 2026** | [arXiv:2605.15873](https://arxiv.org/abs/2605.15873) | Authors: Yuanwei Liu; Xu Gan; Zhaolin Wang; Shan Shan; Zongyao Zhao; Zhiguo Ding (eess.SP). Organises the coupling as "**agents for communications**" and "**communications for agents**", over deployable computing infrastructure, programmable O-RAN software and controllable communication interfaces. **Architecture/position article rather than a strict survey** — label it as such. |

**Also relevant as a survey-adjacent anchor:** **Agentic Open RAN: A Deterministic and Auditable Framework for Intent-Driven Radio Control** — [arXiv:2604.13384](https://arxiv.org/abs/2604.13384), 15 Apr 2026, 6 pages, **accepted at IEEE ICC 2026**. Authors: Hengxu Li; Dongkuan Xu; Mingzhe Chen; Yuchen Liu. (Details in §7.)

---

## 7. Closest prior art for execution semantics in wireless agents

### 7.1 Direct answer

**No paper was found that explicitly studies agent runtime execution semantics — timeout/outcome-unknown, idempotency, duplicate side effects, durable replay, leases, or reconcile — in a wireless, RAN, or emergency-communication setting.** I searched for the combination from several angles (wireless/network-management terms crossed with `idempotency`, `exactly-once`, `at-least-once`, `outcome unknown`, `duplicate side effects`, `durable execution`, `checkpoint/replay`, `disruption-tolerant`, `intermittent connectivity`) and found no such paper. Every paper I did find that *formally* studies these semantics is written in the general-purpose-agent / systems / software-engineering register, and every wireless-domain paper treats the tool layer as deterministic and instantaneous. The two literatures are disjoint as of 2026-09-12.

That disjointness is a genuine novelty opening — but note it also means **there is no wireless-domain baseline to compare against**, so the new paper will likely need to import its evaluation methodology from the systems papers below.

### 7.2 Closest on the wireless side (domain, but no runtime semantics)

| Paper | Venue | What comes closest | What is missing |
|---|---|---|---|
| **Agentic Open RAN: A Deterministic and Auditable Framework for Intent-Driven Radio Control** ("A1gent") — [arXiv:2604.13384](https://arxiv.org/abs/2604.13384), Hengxu Li; Dongkuan Xu; Mingzhe Chen; Yuchen Liu. **Accepted, IEEE ICC 2026** | ICC 2026 | The strongest wireless match: it **decouples reasoning from real-time actuation** — a non-RT agentic rApp compiles operator goals into **typed A1 policy instances**, and three near-RT agentic xApps enforce them "through a **deterministic loop** with plane-scoped actuation" (E2 for mobility/load steering, O1 for energy orchestration), with **encoded guardrails** and a **fixed-priority action merger for conflict governance** | Grepping the full text: `retry` **0**, `idempot` **0**, `disconnect` **0**, `stale` **0**, `rollback` **0**; `timeout` **1**, `duplicate` **2**, `outage` **1** (generic/physical sense). Its determinism is about RIC-tier coordination and conflict resolution, **not** about outcome-unknown tool calls or duplicate side effects |
| **6GAgentGym** — [arXiv:2603.29656](https://arxiv.org/abs/2603.29656) | arXiv 2026 | Explicit **effect classification** of 42 tools into read-only / pure-computation / **state-mutating Configuration**; an "error-recovery" trajectory class; a `graceful_degradation` tool; `heartbeat`; `select_recovery_strategy`; `check_migration_feasibility` | Error recovery is offline data augmentation; the authors themselves state the model "does not capture full protocol-level transients, particularly during **handover and failure recovery**"; no timeout/idempotency/lease/reconcile |
| **α³-Bench** — [arXiv:2601.03281](https://arxiv.org/abs/2601.03281) | arXiv 2026 | A dedicated **"Operational Semantics of MCP and A2A Tools"** section defining inputs/outputs/affected state/**execution constraints**; network-degradation-conditional action subset including **"buffering commands"** and postponing sensor activation when lat > 40 ms or loss ≥ 1% | Tools are **deterministic**; A2A is "**logically instantaneous**"; no timeout, no outcome-unknown, no duplicate handling |
| **WirelessAgent++** — [arXiv:2603.00501](https://arxiv.org/abs/2603.00501) | arXiv 2026 | The only explicit **timeout (`30s`) and retry (`3`) budget** in the wireless set, plus a **consecutive-failure counter** in the ReAct ToolAgent operator | Budget applies to **code execution** inside the `Programmer` operator, not to network/tool calls; "outage" means **fading outage probability**, not connectivity loss |
| **ICG-Restore** — [10.3390/ai7080294](https://doi.org/10.3390/ai7080294) | *AI* (MDPI) 2026 | Emergency-communication **recovery** planning with a **validator** gate and bounded **minimal-edit repair** of constraint-violating plans | Explicitly "abstract executors or schedulers"; author-labeled as a **descriptive** repair principle; the authors describe the evaluation as **offline high-level planning by a single planner** |
| **WirelessAgent** — [10.23919/jcc.fa.2025-0163.202603](https://doi.org/10.23919/jcc.fa.2025-0163.202603) | China Commun. 2026 | States the requirement that an agent adapt to "changes and even failures in telecommunication systems" | Vision statement only; no mechanism |
| **ComAgent** — [arXiv:2601.19607](https://arxiv.org/abs/2601.19607) | arXiv 2026 | Closed-loop Perception–Planning–Action–Reflection with an explicit **error-handling branch** from the Scoring Agent back to the Coding Agent | Compile/runtime error handling in a **code-generation** loop; zero mentions of timeout or retry |

### 7.3 Closest on the execution-semantics side (the semantics, but no wireless)

These are the papers a "Disruption-Tolerant Runtime" paper must engage as prior art. **None of them is set in wireless or emergency communications.**

1. **Verified Tool Calls Improve LLM Agent Reliability Under Non-Atomic Failures** — [arXiv:2608.02645](https://arxiv.org/abs/2608.02645), 31 Jul 2026, cs.SE/cs.AI. Authors: Isham Kalappurackal Mansoor; Abhishek Phadke; Pratip Rana.
   **This is the single closest paper to the proposed execution semantics.** Motivation: existing frameworks "assume that tool calls are **atomic** and return binary success or failure signals," while real systems exhibit "**timeouts after dispatch, delayed visibility, and partial state updates**," causing "**duplicate actions**, task success, and unnecessary tool executions." Contribution: a lightweight **verification-aware tool wrapper** adding **postcondition verification, verify-before-retry logic, and idempotency keys**. Evaluated in a **controlled simulated environment with injected non-atomic failures** across multiple task templates; significantly reduces duplicate actions while holding task success roughly constant. Explicitly frames "strengthening **tool interaction semantics**" as the direction. **This paper has your problem statement almost verbatim — minus the wireless/emergency domain, minus the network-disruption model, and minus a distributed/multi-node runtime.**

2. **Beyond Single-Use Tokens: Durable Authorization State for Replay-Resistant LLM Agent Actions** — [arXiv:2608.01710](https://arxiv.org/abs/2608.01710), 3 Aug 2026, cs.AI. Authors: Jinghan Xu; Longze Fan; Zeyuan Wang; Xinjin Li; Hankai Liu.
   Names a failure mode — **"semantic replay"**: agents "replan, retry failed operations, delegate tasks, and resume after crashes," causing one authorization to be requested and executed multiple times even when each token is single-use. Argues identifier-local token consumption **cannot** prevent reissuance "unless the issuer retains **monotonic durable state** over the authorized action, confirmation event, and remaining execution budget." Introduces **CapLease** with transactional **Issue–Prepare–Commit** transitions. Evaluated across **replanning, retry, delegation, concurrency, confirmation-replay, and crash-recovery** scenarios; shows duplicate admission is prevented, and "with an idempotent sink, duplicate external effects." **Directly relevant vocabulary: durable state, leases, transactional commit, idempotent sink.**

3. **Resume Means Resume: A Machine-Checked Conformance Contract for Checkpoint, Interrupt, and Resume Semantics in Workflow Persistence Layers** — [arXiv:2608.03836](https://arxiv.org/abs/2608.03836), v1 4 Aug 2026 / v3 8 Aug 2026. Author: Sajjad Khan.
   Defines a six-property **RESUME CONTRACT**: prefix continuation, **effect exactly-once**, fork determinism, checkpoint validity, **consume-once**, **recovery determinism**, plus fork-intent and liveness obligations. Machine-checked with a **TLA+ model** (7.4M states) and **TLAPS proofs** (196 obligations), with a **39-cell fault matrix**. Measures real frameworks: **LangGraph 1.2.9** durably records a second resume value and never consults it, persists schema-invalid state silently, and **re-executes durably recorded work after a real SIGKILL** — "exactly-once across interrupts, at-least-once across crashes, on one API"; **CrewAI 1.15.2** re-executes completed effect-bearing methods; **pydantic-graph 1.x** cannot resume after a mid-node crash; **consume-once fails under concurrent delivery**, with **k processes resuming one parked interrupt firing the gated effect k times (saturation 1.0 in 36 of 40 cells), crossing hosts.** Offers **REMIT**, a reference sequencer with a Verus-verified recovery core. **This is the methodological template if the new paper wants to state and machine-check a runtime contract.**

4. **Agent libOS: A Runtime Substrate for Capability-Controlled Self-Evolving LLM Agents** — [arXiv:2606.03895](https://arxiv.org/abs/2606.03895), v1 2 Jun 2026 / v3 18 Aug 2026, cs.OS/cs.AI/cs.CR. Author: Yingqi Zhang.
   Provides persistent processes, Object Memory, Skills, syscall-mediated JIT tools, images/checkpoints, typed providers, budgets and **durable recovery**. Most relevant line: "Provider-backed effects use a **prepare-dispatch-settle protocol that exposes ambiguity and prevents blind replay**," and "a crash after provider dispatch but before finalization may leave a **durable intent without its terminal event**." Honest about limits: "does not prevent prompt injection, provide kernel-grade sandboxing, **or roll back irreversible external effects**." **"Prepare-dispatch-settle" and "durable intent without its terminal event" are exactly the vocabulary of outcome-unknown tool calls.**

5. **ACRFence: Preventing Semantic Rollback Attacks in Agent Checkpoint-Restore** — [arXiv:2603.20625](https://arxiv.org/abs/2603.20625), 21 Mar 2026, cs.CR. Authors: Yusheng Zheng; Yiwei Yang; Wei Zhang; Andi Quinn.
   Attacks the assumption behind "make external tool calls safe to retry": LLM agents **re-synthesize subtly different requests after restore**, so servers treat them as new, "enabling **duplicate payments**, unauthorized reuse of consumed credentials, and other **irreversible side effects**" — termed **semantic rollback attacks** (classes: **Action Replay**, **Authority Resurrection**). Proposes a framework-agnostic mitigation recording irreversible tool effects and enforcing **replay-or-fork semantics**. **This is the best source for "why naive checkpoint/restore is unsafe for actuating tools."**

6. **Durable Execution for AI Agents: A Design Pattern for Fault-Tolerant Agent Loops** — [IEEE Xplore document 11638700](https://ieeexplore.ieee.org/document/11638700). **⚠️ Title and URL verified only via search listings; IEEE Xplore and the EurekaMag mirror both blocked retrieval. Authors, venue, year, and content are UNVERIFIED.** Listed because it is squarely on-topic and must be checked by hand.

7. **DelAct: A Replayable Boundary Runtime for Auditable and Governed LLM Agent Workflows** — [IEEE Xplore document 11661202](https://ieeexplore.ieee.org/document/11661202). **⚠️ Title and URL verified only via search listings; authors, venue, year and content UNVERIFIED.**

8. **Rollback Is Not Undo: Path-Dependent Failures in LLM-Arbitrated Network Control** — [IEEE Xplore document 11571400](https://ieeexplore.ieee.org/document/11571400). **⚠️ Title and URL verified only via search listings; IEEE Xplore blocked retrieval. Authors, venue and — critically — whether "network control" means wireless/RAN or datacenter/SDN are UNVERIFIED.** *Prioritise this one: by title it is the closest existing collision with the proposed contribution space.*

9. **Abhyasa: Custody Transfer of Governance Obligations over Unreliable Channels in Agent Networks** — Zenodo record [20644822](https://zenodo.org/records/20644822) (v1 11 June 2026; v2 9 Aug 2026), code at [github.com/ravikiran438/abhyasa-protocol](https://github.com/ravikiran438/abhyasa-protocol). **Closest match on "unreliable channel + agent protocol"**, but the semantics are governance/authorization custody transfer, not tool execution. Zenodo-hosted (not clearly peer-reviewed).

10. **Graph-Based Self-Healing Tool Routing for Cost-Efficient LLM Agents** — [arXiv:2603.01548](https://arxiv.org/abs/2603.01548), 2 Mar 2026 ("Working paper"), Neeraj Bholani. Treats control flow as **routing**: parallel health monitors assign priority scores to runtime conditions "such as **tool outages** and risk signals," and a cost-weighted tool graph uses **Dijkstra shortest-path** routing where "when a tool fails mid-execution, its edges are reweighted to infinity and the path is re-routed." **A deterministic, reproducible alternative to LLM re-planning under tool outage — a useful foil for a latency- and disruption-constrained runtime, though it is not wireless and is an unrefereed working paper.**

### 7.4 What this implies for positioning

Three defensible novelty claims fall out of the evidence above:
1. **Domain transfer of non-atomic tool semantics.** The timeout-outcome-unknown / duplicate-side-effect problem is established (2608.02645, 2608.01710, 2603.20625) but has never been instantiated on network-actuating tools, where side effects are *physical infrastructure state changes* and where the network that would carry a retry or a reconcile is itself the thing that failed.
2. **A runtime contract for degraded-and-recovering links.** The existing wireless benchmarks deliberately abstract failure away — α³-Bench declares A2A "logically instantaneous"; 6GAgentGym concedes it "does not capture full protocol-level transients, particularly during handover and failure recovery." A runtime that keeps a *durable intent ledger* across partitions, with explicit outcome-unknown states, exactly-once effect application, leases for actuation authority, and a reconcile protocol, is unclaimed territory.
3. **Evaluation methodology.** There is no wireless benchmark with **injected non-atomic tool failures**. Combining 6GAgentGym's effect-typed tool taxonomy (obs/rea/cfg) with 2608.02645's injected-failure harness and 2608.03836's fault-matrix methodology would be a novel and well-grounded contribution, and it would sit directly on top of the two most citable wireless artifacts (α³-Bench's released 113k-episode dataset, WirelessAgent++'s released code).

---

## Confidence / gaps

### Not verified — needs a manual read
1. **TopoLLM full text.** ScienceDirect returned a JavaScript shell (**0** occurrences of "TopoLLM") via both `curl` and headless Chromium. Its tool set ("TopoTool" internals), environment, failure semantics and artifact availability are **unknown**. Highest-priority manual check (institutional access).
2. **ICG-Restore full text.** MDPI returned `Access Denied` to both `curl` with browser headers and headless Chromium. The Data/Code Availability statement and any runtime detail beyond the abstract are **unknown**. The abstract, DOI, venue, volume/issue/article number, year, authors and institutions *are* verified.
3. **IEEE Xplore items 11571400 ("Rollback Is Not Undo"), 11638700 ("Durable Execution for AI Agents"), 11661202 ("DelAct").** Titles and URLs verified only as search-result listings. **Authors, venues, years, and content unverified.** 11571400 is the highest-priority manual check because of its title.
4. **6GAgentGym** — no journal venue or DOI exists; it is a preprint. Also: the three affiliation strings were read from HTML "Affiliation:" markers; the **author→affiliation mapping is unverified**.
5. **α³-Bench author institutions** — unverified (arXiv metadata has no affiliations). I examined **v1** and did not check whether later versions exist.
6. **Survey content for S2 (ICT Express) and S3 (IEEE COMST)** — metadata verified via Crossref, but abstracts were **not read**; the one-line content descriptions are unverified.
7. **Survey S1 (arXiv:2607.16066)** — abstract read; whether it has a published venue is unverified (search results pointed to Eurecom's publication list, which I did not open).
8. **AlphaBench dataset README** — not opened; harness/loader availability assumed from the directory listing, not confirmed.
9. **Abhyasa** — Zenodo-hosted; peer-review status unknown.
10. **Graph-Based Self-Healing Tool Routing** — self-described "working paper"; not peer-reviewed.

### Known uncertainties and traps
- **"ComAgent" is ambiguous.** Two distinct works share the name (§5b). The GitHub repo `jiangfeibo/ComAgent` belongs to the **JSAC tutorial**, not to arXiv:2601.19607, and contains **no code** (README + `fig/` only).
- **WirelessAgent has three records** (arXiv:2409.07964, arXiv:2505.01074 with an explicit text-overlap note, and China Communications 2026). The extended version is LangGraph-based; **the original magazine version's code repo contains only a README**. Choose which record you cite deliberately.
- **"Outage" is a false friend in WirelessAgent++**: both occurrences are physical-layer **fading outage probability** inside a math calculator tool, not connectivity loss.
- **α³-Bench's network conditions are simulated** by "deterministic execution logic augmented with controlled stochastic perturbations" — not a testbed, not NS-3. **6GAgentGym's are a learned surrogate**, not NS-3 at runtime.
- **Vendor/preprint churn:** several 2026 entries are non-peer-reviewed preprints (6GAgentGym, α³-Bench, WirelessAgent++, ComAgent, S1, S5). Cite venue status accurately.
- **My negative claim is a search-based finding, not a proof of absence.** I searched from multiple angles and the two literatures (wireless agents / runtime execution semantics) showed no overlap, but a paper using different vocabulary (e.g. store-and-forward, DTN, MEC orchestration, service-mesh actuation) could exist that my queries missed. Recommendations for closing this: (a) forward/backward citation crawl on arXiv:2608.02645 and 2603.20625; (b) keyword sweep on `DTN` / `store-and-forward` / `opportunistic` crossed with `agent`; (c) IEEE Xplore and ACM DL full-text search (both blocked to me); (d) a targeted check of the three unread IEEE items above.

### Search that came up empty (recorded so it is not repeated)
- GitHub repository search for `6GAgentGym` → **0 repositories**.
- No code or dataset link in: TopoLLM (Crossref/DOAJ/abstract), 6GAgentGym, ComAgent (arXiv:2601.19607), ICG-Restore (unverifiable).
