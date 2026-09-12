# 金石 (Shi Jin), Southeast University — recent work relevant to *agentic communication + 通感算一体化 (ISAC)* for disaster / mountain monitoring

Scope note: I deliberately exclude pure sensing-theory (waveform/ambiguity-function/CRB) and pure communication-theory (MIMO detection, CSI feedback, precoding) results except where they carry an agentic or application payload. All dates are arXiv first-submission dates unless an IEEE/Elsevier record is cited. "Group" = 金石 + the SEU NMCRL circle he co-authors with (梁乐/Le Liang, 杨杰/Jie Yang, 李潇/Xiao Li, 郭嘉佳/Jiajia Guo, 韩瑜/Yu Han, 刘凡/Fan Liu, 冯伟/Wei Feng, 黄逸轩/Yixuan Huang — Chinese names given as commonly written, Latin forms are the ones on the papers).

---

## 1. Agentic / AI-native / autonomous directions

This is now the group's largest and fastest-moving line. 梁乐 (Le Liang)'s LLGroup + 郭嘉佳 (Jiajia Guo) drive most of it, with 金石 as a standing co-author.

| # | Title | Venue / year | One line | URL |
|---|---|---|---|---|
| 1 | **WirelessOpsAgent: A Benchmark and Agent Design for Action Assurance in Wireless Networks** | arXiv preprint, Aug 2026 | Introduces **WirelessOptBench** (execution-state decision episodes with controlled telemetry faults) + an agent that re-grounds candidate actions in current evidence before execution; unsafe-APPLY rate on Claude Sonnet 4.6 drops 82.2% → 10.3%. | [arXiv 2608.08277](http://arxiv.org/abs/2608.08277) |
| 2 | **Large Language Models for Wireless Communications: From Adaptation to Autonomy** | arXiv preprint, Jul 2025 (tutorial/overview) | Three-stage roadmap: adapting pretrained LLMs → wireless-native foundation models → agentic LLMs with autonomous reasoning and coordination. | [arXiv 2507.21524](http://arxiv.org/abs/2507.21524) |
| 3 | **Foundation Models for Wireless Communications: From PHY Intelligence to Network Autonomy** | arXiv preprint, Jun 2026 | Follow-on overview that explicitly names **agentic foundation models** for "autonomous, reasoning-driven network orchestration" and singles out ISAC as a 6G frontier. | [arXiv 2606.06239](http://arxiv.org/abs/2606.06239) |
| 4 | **Learning Multi-Access Point Coordination in Agentic AI Wi-Fi with Large Language Models** | arXiv preprint, Nov 2025 | Each AP is an **autonomous LLM agent** that negotiates MAPC in natural-language dialogue with memory, reflection and tool use; beats spatial-reuse baseline in simulation. | [arXiv 2511.20719](http://arxiv.org/abs/2511.20719) |
| 5 | **AgentComm: Semantic Communication for Embodied Agents** | arXiv preprint, Apr 2026 | LLM semantic processor condenses agent-to-agent messages + importance-aware protection; ~50% bandwidth reduction at negligible task loss. Directly on-topic for "agentic communication". | [arXiv 2604.13558](http://arxiv.org/abs/2604.13558) |
| 6 | **Intention-Aware Semantic Agent Communications for AI Glasses** | arXiv preprint, Apr 2026 | Same agentic-semantic-communication family, applied to a wearable/embodied device. | [arXiv 2604.23691](http://arxiv.org/abs/2604.23691) |
| 7 | **Wireless Power Control Based on Large Language Models** (PC-LLM) | arXiv preprint, Feb 2026 | Physics-informed attention bias injects the channel-gain matrix into a pretrained LLM's self-attention; 50% depth reduction, zero-shot generalization. | [arXiv 2603.00474](http://arxiv.org/abs/2603.00474) |
| 8 | **Joint Task Orchestration and Resource Optimization for SC3 Closed Loop in 6G Networks** | arXiv preprint, Mar 2026 | Joint **task + resource** orchestration for the sensing-communication-computing-control loop — the closest thing in the group to "通感算一体化 orchestration". | [arXiv 2603.23217](http://arxiv.org/abs/2603.23217) |
| 9 | **Semantic Communications with World Models** | arXiv preprint, Oct 2025 | World-model-based semantic communication. | [arXiv 2510.24785](http://arxiv.org/abs/2510.24785) |
| 10 | **Beam Prediction Based on Multimodal Large Language Models** | arXiv preprint, Mar 2026 | MLLM used as a beam predictor. | [arXiv 2603.15093](http://arxiv.org/abs/2603.15093) |
| 11 | **Structure-Aware Multimodal LLM Framework for Trustworthy Near-Field Beam Prediction** | arXiv preprint, Mar 2026 | Multimodal LLM + structure prior, "trustworthy" framing. | [arXiv 2603.16143](http://arxiv.org/abs/2603.16143) |
| 12 | **NF-TrackLLM: Joint Prediction of UAV Trajectory and Near-Field Beam for LAE XL-MIMO Systems** | arXiv preprint, May 2026 | LLM for joint UAV trajectory + near-field beam prediction — UAV/低空, agentic-flavoured. | [arXiv 2605.26928](http://arxiv.org/abs/2605.26928) |
| 13 | **Exploring the Potential of Large Language Models for Massive MIMO CSI Feedback** | arXiv preprint, Jan 2025 | Earliest LLM entry in the group's list. | [arXiv 2501.10630](http://arxiv.org/abs/2501.10630) |

Related but not LLM-based: **Deep Reinforcement Learning-Empowered Wireless Sensor Networking for 6G Closed-Loop Controls** ([arXiv 2607.08272](http://arxiv.org/abs/2607.08272), Jul 2026) and the MARL channel-access / resource-allocation series (Yu, Fang, Wang, 2024–2026) — control-theoretic autonomy rather than agentic AI.

**Framing for your paper:** the group has already staked out the *"agentic foundation model → network autonomy"* narrative (items 2, 3) and an *agent-to-agent semantic transport* primitive (item 5). What is **missing** is anyone connecting that to ISAC sensing payloads or to a disaster/monitoring mission — that is genuine white space.

---

## 2. ISAC + application work (monitoring / infrastructure)

**Anchors verified via Crossref** (I confirm they exist as you stated, with corrected author lists):

- *RIS-Aided Cooperative ISAC Networks for Structural Health Monitoring* — IEEE JSAC, vol. 44, pp. 592–607, 2026, DOI [10.1109/JSAC.2025.3610805](https://doi.org/10.1109/jsac.2025.3610805). Authors: **Jie Yang, Chao-Kai Wen, Xiao Li, Shi Jin**. Preprint: [arXiv 2507.02731](http://arxiv.org/abs/2507.02731).
- *CSI-Based Instantaneous Rainfall Monitoring in Sub-6 GHz for ISAC Applications* — IEEE Trans. Commun., vol. 74, pp. 12418–12433, 2026, DOI [10.1109/TCOMM.2026.3720922](https://doi.org/10.1109/tcomm.2026.3720922). Authors: **Yan Li, Jie Yang, Weisheng Dong, Chao-Kai Wen, Shi Jin** (all SEU except Wen).
- *An overview of multi-modal sensing systems and the potential of ISAC technologies in SHM* — Physical Communication, vol. 69, art. 102614, Apr 2025, DOI [10.1016/j.phycom.2025.102614](https://doi.org/10.1016/j.phycom.2025.102614). Authors: **Zedong Zhu, Jie Yang, Chao-Kai Wen, Shuqiang Xia, Shi Jin**.

### What is *around* those anchors — and critically, what physical quantity each senses and in what environment

**A. The SHM-ISAC line (杨杰 / Jie Yang) — theory + simulation only.**

| Work | Senses | Environment |
|---|---|---|
| RIS-Aided Cooperative ISAC Networks for SHM (JSAC 2026 / arXiv 2507.02731) | **Millimetre-level structural deformation** — RIS as phase-controlled reference points suppress background multipath; Fisher-information position error bound + Bayesian damage-state inference | **Pure theory + numerical.** I fetched the full text: zero occurrences of "testbed", "test bed", "field", "prototype", "bridge"; 3 "numerical", 3 "experiment" (all analytical). No hardware, no structure, no dataset. **Do not describe this as validated.** |
| Difference Imaging-Based Parking Lot Surveillance in Multi-RIS-Aided Collaborative ISAC System (arXiv 2507.03851, Jul 2025) | **Occupancy / scattering-coefficient variation** of parking bays, via compressed-sensing difference imaging | Controlled **indoor multi-RIS testbed** ("Experimental results…"). Small-scale, not field. |
| RIS-Aided Cooperative ISAC Network for Imaging-Based Low-Altitude Surveillance (arXiv 2601.16033, Jan 2026) | **Aerial target reflectivity field** (imaging), active-RIS amplified; CRLB derived | Simulation + numerical. |
| Physics-Informed Implicit Neural Representation for Wireless Imaging in RIS-Aided ISAC (arXiv 2601.15113, Jan 2026) | **Voxel scattering coefficients** of targets from CSI | Simulation. |
| Cooperative / Learned Off-Grid Imager for Low-Altitude Economy (arXiv 2505.02440, 2506.07799; 2025) | **UAV position as a sparse radio image**, multi-BS CS + physics-embedded learning | Simulation. |
| *Wireless Imaging for Low-Altitude Surveillance: A New Paradigm for ISAC Networks* ([arXiv 2608.00062](http://arxiv.org/abs/2608.00062), Jul 2026) — Yixuan Huang, Jie Yang, Wen, Jin | Position paper: hierarchical imaging from wide-area snapshot → trajectory-aware → target-centric fine-grained | Concept/overview. **"Flight monitoring" is the group's stated ISAC application north star.** |
| Integrated Communication and Learned Recognizer with Customized RIS Phases ([arXiv 2503.02244](http://arxiv.org/abs/2503.02244), Mar 2025) and Learned Intelligent Recognizer with Adaptively Customized RIS Phases ([arXiv 2505.02446](http://arxiv.org/abs/2505.02446), May 2025) | Target **presence/class** via a learned recognizer jointly designed with RIS phase + sensing duration | Simulation. |

**B. The rainfall / environmental-sensing line (李岩 / Yan Li, 杨杰 / Jie Yang) — the group's only genuine fieldwork.**

| Work | Senses | Environment |
|---|---|---|
| RainGaugeNet: CSI-Based Sub-6 GHz Rainfall Attenuation Measurement and Classification (IEEE TCOM 74, Dec 2025, DOI [10.1109/TCOMM.2025.3606633](https://doi.org/10.1109/tcomm.2025.3606633); preprint [arXiv 2501.02175](http://arxiv.org/abs/2501.02175)) | **Rain-induced attenuation on 2.8 GHz CSI**, delay spread, RSS mean/variance → rainfall-class classification (RainGaugeNet, >90% LoS / >85% NLoS from 20 s of CSI) | **Real over-the-air field measurement**, NI USRP-2974 Tx + horn antenna at 2.8 GHz, 100 MHz OFDM, LoS and NLoS paths on the SEU campus. Co-author **Tao Yang is from the National Engineering Research Center of Water Resources Efficient Utilization and Engineering Safety** (hydrology institute) — a real cross-domain bridge. |
| CSI-Based Instantaneous Rainfall Monitoring in Sub-6 GHz for ISAC Applications (IEEE TCOM 74, 2026, DOI above) | Same physical quantity, likely instantaneous rainfall-rate inversion rather than classification | Presumably the same 2.8 GHz SEU setup. **UNVERIFIED** — IEEE Xplore returned HTTP 202 with no abstract to my client; Crossref carries no abstract. |
| RainGaugeNet text explicitly proposes **"drone-based measurements for hard-to-reach areas like valleys or lakes"**, noting rain gauges are "unsuitable for extreme environments" | — | **This is the only sentence in the entire corpus that reaches toward mountain / remote deployment — and it is a future-work remark, not a demonstrated result.** |

**C. ISAC testbed / prototype capability.** *ISAC Prototype System for Multi-Domain Cooperative Communication Networks* ([arXiv 2410.22956](http://arxiv.org/abs/2410.22956), Oct 2024) — monostatic + bistatic + network sensing modes, 5G NR-aligned, multimodal data capture/sync, up to 16 UL / 10 DL UEs; measured RMSE 2.3° angle, 0.3 m range, 0.25 m SLAM localization, 0.8 m mapping. **This is the hardware asset your paper could plausibly build on** — it exists, it is characterised, and it is not yet pointed at any infrastructure-monitoring mission.

Two adjacent 2025–2026 items worth knowing because they show the group's low-altitude/ISAC sensing muscle and their hardware cadence: *AI-Empowered Low-Altitude Economy: Cooperative Sensing With Fixed Wireless Access* ([arXiv 2605.07623](http://arxiv.org/abs/2605.07623), May 2026) turns **densely deployed FWA customer-premises equipment into "wireless cameras"**, using uplink CSI from multiple BS–CPE pairs for UAV detection and localization — a cheap, wide-coverage, infrastructure-reuse sensing idea that transfers well to mountain/remote sites; and *Pioneering Scalable Prototyping for Mid-Band XL-MIMO Systems: Design and Implementation* ([arXiv 2510.02793](http://arxiv.org/abs/2510.02793), Oct 2025; IEEE JSAC 44:3365, 2026) is the paper behind the 200 MHz XL-MIMO prototype 金石's team exhibited in Nanjing. *SkySense* ([arXiv 2606.04076](http://arxiv.org/abs/2606.04076)) is a semi-supervised generative CSI-fingerprint framework for UAV localization in ISAC networks, aimed explicitly at **extreme data scarcity**.

---

## 3. Emergency / disaster / extreme environment / remote or mountain deployment

**Explicit answer: essentially none, from 金石's group.**

I keyword-searched the full 300-entry arXiv corpus (2023-12 → 2026-09) for emergency / disaster / rescue / wildfire / flood / mountain / extreme environment. Exactly three hits, and **none of them is ISAC from this group**:

1. *Latency-Constrained Resource Synergization for Mission-Oriented 6G Non-Terrestrial Networks* (arXiv 2603.14812, Mar 2026) — Yueshan Lin, **Wei Feng**, Yunfei Chen, Yongxu Zhu, Ning Ge, **Shi Jin**. Post-disaster scenario: terrestrial infrastructure damaged, UAVs with edge information hubs provide temporary coverage; joint comms+compute resource config and EIH location optimisation; ~20% cost reduction. **Simulation only.** This is the group's single explicit disaster paper, and it is about **comms+computing**, not sensing — a natural hook for you to extend to the third leg (通感算).
2. *Physical Layer Security for Sensing-Communication-Computing-Control Closed Loop* (arXiv 2603.00943, Mar 2026) — same Wei Feng / 葛宁 group with 金石 and Tony Quek. Motivation is "industrial automation or **emergency rescue**"; SC3 closed loop (sensor → EIH → robot) with closed-loop negentropy maximised under a security constraint. **Simulation only**, and the "emergency" framing is motivational.
3. *RainGaugeNet* (see §2B) — mentions floods and "extreme environments" only as motivation and future work.

**There is no mountain deployment, no remote-site deployment, no disaster-field trial, no extreme-environment measurement paper from this group.** The group's actual field experience is: one campus-scale 2.8 GHz rainfall link, one indoor/multi-RIS imaging testbed, and one lab ISAC prototype. Any claim of disaster or mountain ISAC capability in the literature you are framing against would have to come from *other* groups.

---

## 4. Open source / testbeds / datasets

Verified by fetching each page/repo:

| Artifact | URL | Contains code? |
|---|---|---|
| **Multimodal-Wireless dataset** (Tianhao Mao, Le Liang, Jie Yang, Hao Ye, Shi Jin, Geoffrey Ye Li; ICC 2026) | [github.com/le-liang/Multimodal-Wireless](https://github.com/le-liang/Multimodal-Wireless) · project site [le-liang.github.io/mmw](https://le-liang.github.io/mmw/) | **Yes** — README.md, requirements.txt, Python scripts for dataset extension/replay, CARLA sensor storage + Sionna channel storage pipelines, LICENSE. Data hosted on OneDrive + a Quark mainland mirror. 161,400 frames, 4 virtual towns, 16 comms scenarios, 3 weather conditions; 100 Hz CSI + LiDAR/RGB/depth/IMU/radar, **all-weather by design**. Synthetic (CARLA+Sionna), not field. |
| **LAM4PHY_6G** (curated reading list for large AI models in the wireless PHY) | [github.com/ACELab-SEU/LAM4PHY_6G](https://github.com/ACELab-SEU/LAM4PHY_6G) | Curated **list**, not code — README.markdown only (37 KB, last updated Jan 2026); contributors 郭嘉佳/Jiajia Guo, Yiming Cui, Tianyue Zheng, Peiwen Jiang. Mirror: [github.com/AI4Wireless/LAM4PHY_6G](https://github.com/AI4Wireless/LAM4PHY_6G). |
| **3DGS_for_Wireless** | [github.com/AI4Wireless/3DGS_for_Wireless](https://github.com/AI4Wireless/3DGS_for_Wireless) | Curated **list** only (README.md, 13 KB), maintained by Jiajia Guo, Jinya Zhang, Yumeng Zhang, Chunyu Ling, Yiming Cui. |
| **WirelessOptBench** artifact (from WirelessOpsAgent) | `https://anonymous.4open.science/r/wirelessopsbench-artifact-D969/` | **Could not verify** — returned HTTP 401 `{"error":"not_connected"}`. The quoted URL is anonymous-review-shaped and may already be dead. Mark **UNVERIFIED**. |
| **DRFF-R2** multi-scenario UAV RF dataset (26 UAV units / 8 models, real acquisition platform) | [arXiv 2603.00106](http://arxiv.org/abs/2603.00106), Feb 2026 — Haolin Zheng, Ning Gao, Zhenghang Zhu, Zhijun Huang, **Shi Jin**, Michail Matthaiou | A *dataset* is claimed. **UNVERIFIED** as 金石's group and unverified for a public download link. |

**Gaps:** the group has released **no code or dataset for the SHM-ISAC work, no code for the rainfall/RainGaugeNet work, and no public package for the ISAC prototype system**. Given the lab explicitly has hardware (§2C), this is a notable gap and a plausible contribution angle for a student.

---

## 5. Direction signals 2025–2026

**Person / institutional position.** 金石 is now **Vice President of Southeast University (东南大学副校长)** and a standing figure in the Chinese communications establishment: 主任委员 of the 中国电子学会通信分会 (CIE Communications Society), executive chair of the 中国科协 ISAC workshop, chair of the 2026 通信理论与技术学术会议 programme committee.

**Talks and forums (verified):**

- **Oct 14, 2025 — 中国科协"通信感知一体化"研讨活动**, 中国科技会堂, Beijing. 金石 was **executive chair** and gave the keynote **《随机通信信号感知理论与典型应用》**, presenting the group's "random ISAC signal sensing" framework — integrated waveform design so sensing and communication share radio resources. Other participants: 冯志勇 (BUPT) on wide-area integrated sensing; 程翔 (PKU) on LLM/foundation-model-empowered comms + multimodal sensing fusion ("机器联觉"); 赵亚军 (ZTE) on 6G RIS standardisation. Consensus: ISAC needs more concrete application scenarios and standards layering. [cast.org.cn](https://www.cast.org.cn/xs/XSDT/art/2025/art_3af45741accd400fb9e458543215147a.html)
- **May 9–10, 2026 — 中国电子学会第47期青年人才托举沙龙暨"6G智能体通信感知计算一体化"专题论坛**, 第二届空天信息技术大会, Tongxiang, Zhejiang. Co-organised with **东南大学** as one of the host institutions. This is almost exactly your topic name (智能体 + 通信感知计算一体化). SEU speakers included 黄杰 (continuous 3-D-space ISAC channel measurement/modelling, RIS channel measurement experiments) and 徐浩 (fluid-antenna channel estimation). **金石 is not listed as a forum speaker — UNVERIFIED as a direct 金石 initiative, though SEU is a host.** [cie.org.cn](https://www.cie.org.cn/list_42/15931.html) · [cast.org.cn](https://www.cast.org.cn/xw/qgxh/ZHXX/art/2026/art_de90e53237eb4599b692d83a9b447724.html)
- **Aug 15, 2026 — 2026年通信理论与技术学术会议**, Nanjing; 金石 chaired the opening plenary and delivered the 中国电子学会通信分会 work report. Keynotes leaned heavily "AI-native": 尤肖虎 on network digital-twin autonomous optimisation, 王现斌 on "intelligence-native and trust-native 6G", 郭贵生 on "Token communication for machine-to-machine AI model collaboration", 江涛 on task-oriented communication for embodied agent networks. [cie.org.cn](https://www.cie.org.cn/list_42/16745.html)
- **May 23, 2025 — 第四届电磁频谱学术大会**, Nanjing. 金石 (as SEU VP) spoke on low-altitude economy / space-air-ground-sea integrated smart networking and **electromagnetic spectrum intelligent management**; his team exhibited its **200 MHz-bandwidth XL-MIMO prototype**. [seu.edu.cn](https://www.seu.edu.cn/2026/0122/c124a553459/page.htm)
- **2026 全球6G技术与产业生态大会**, Nanjing, Jun 2026 — SEU-hosted; 金石 is an institutional organiser. [seu.edu.cn](https://www.seu.edu.cn/2026/0604/c124a570216/page.htm)

**Standards activity.** No direct evidence found of 金石 personally publishing into IMT-2030(6G)推进组 ISAC reports; the group's standards-adjacent signal is that its application scenarios are framed against **3GPP** use cases (parking-lot surveillance, per [arXiv 2507.03851](http://arxiv.org/abs/2507.03851); UAV supervision as a 3GPP use case, per [arXiv 2605.07623](http://arxiv.org/abs/2605.07623)). **UNVERIFIED** for named standards-editor roles.

**National key R&D projects.** I found **no verifiable public record** of a specific 国家重点研发计划 project led by 金石 on ISAC/disaster monitoring. The only grant evidence surfaced was a 2024 NSFC 青年学生基础研究项目 awarded to four SEU 信息学院 doctoral students (not 金石's own project). **UNVERIFIED — do not cite.**

**Programme / lab names worth watching.**
- **前沿科学中心"移动信息通信与安全" (Frontiers Science Center for Mobile Information Communication and Security)** — 金石's papers routinely carry this affiliation alongside NMCRL; it is the newer, larger umbrella.
- **"师生共创科研团队项目"** — a 金石 + 梁乐 joint teaching-research programme; signals that the Liang–Jin agentic-AI collaboration is being institutionalised, not just co-authorship. [WeChat](https://mp.weixin.qq.com/s/eALgHVlG1WYrcfgz_T57SA)
- **LLGroup** (liang-seu.net) — Le Liang's group site, the de facto home of the agentic/AI-native output. Datasets page linked from it is currently **broken (HTTP 404)**.

**Where the trajectories cross.** Read together: the group is (a) building the agentic/AI-native orchestration stack, (b) building ISAC sensing/imaging capability with real radar-and-RIS hardware, (c) has one hydrology-flavoured field sensing result, and (d) has one post-disaster NTN simulation. **Nobody in the group has yet joined (a) to (b) under a (d)-style mission.** That junction is the opening.

---

## Confidence and gaps

**High confidence:** the three anchors (verified in Crossref with corrected author lists and, for the rainfall paper, volume/pages 74:12418–12433); the SHM-ISAC line being theory+numerical only (verified by full-text term search of the JSAC preprint); the existence and scope of the agentic line; the Multimodal-Wireless repo containing real code; 金石's VP role and CIE offices.

**Medium confidence:** venue/year attributions for arXiv items that have not yet appeared in a journal; the identities of co-authors on the low-altitude/UAV papers, where several 金/Shi variants and cross-institution collaborations (Matthaiou, Gao Ning) make attribution to *this* 金石 uncertain.

**Explicit UNVERIFIED items:** the WirelessOptBench artifact URL (HTTP 401); the DRFF-R2 dataset download and its attribution to this 金石; the TCOM-2026 rainfall paper's experimental setup; any 国家重点研发计划 project led by 金石; 金石's personal standards-editor roles; whether the "6G智能体通信感知计算一体化" forum is a 金石 initiative or merely SEU-hosted. Also, several §1 item IDs were resolved from the arXiv API result set rather than by opening each abstract page, though all IDs now point at a confirmed record.

**Method / reproducibility notes.** dblp (both dblp.org and dblp.dagstuhl.de) is behind an Anubis anti-bot wall from this host, and OpenAlex + Semantic Scholar both returned HTTP 429 — so I could not build an authoritative publication list from those. Instead I used the arXiv API author query for "Shi Jin" (300 unique entries, 2023-12 → 2026-09), filtered to entries sharing co-authors with the verified anchors (Chao-Kai Wen, Yu Han, Jie Yang, Jiajia Guo, Le Liang, Xiao Li, Fan Liu, Wei Feng, Yixuan Huang). That filter admits a small amount of homonym noise (a Fudan/Fan-Liu-affiliated 金石 and several quantum-algorithm papers on entirely different topics, which I excluded from the tables). Raw corpus: `_shijin_survey/arxiv_all.json`; the per-paper abstracts I quoted are in the same file. Guest access to IEEE Xplore PDFs was not attempted; application-layer details for papers without arXiv preprints are therefore UNVERIFIED.
