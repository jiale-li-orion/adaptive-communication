# How communications papers actually run experiments, where baselines and data come from, and what a reviewer expects

Method note: every claim below is tied to a URL I fetched and read (paper PDF/HTML, venue policy page, or slide deck), except where marked *[search snippet]*. Where a number comes from a study, the population it was measured over is stated.

---

## 0. Direct answer first (5 sentences)

1. **The accepted practice in JSAC/TCOM/TWC/TMC is to *re-derive* the baselines, not to run someone else's code**: you cite the published algorithm, re-implement its mathematical description yourself (usually as a few MATLAB scripts alongside your own method), and report a head-to-head curve on the same synthetic channel realizations, because almost no baseline in this literature ships runnable code.
2. **Your own artifact is expected to be a *description*, not a repository** — a precise system model, a complete simulation-parameter list, an algorithm in pseudocode or closed form, and results averaged over a stated number of Monte Carlo trials — because IEEE (and even ComSoc's own author pages) only *encourage* code and data sharing, and a 2025 IEEE COMST survey of 130 ML-based resource-allocation papers found that "the vast majority" of the 27 papers it audited in detail do not share source code at all ([source](https://oulurepo.oulu.fi/bitstream/10024/54634/1/nbnfioulu-202503202122.pdf)).
3. **Data is simulated, essentially always**: you take a standardized channel/statistical model (3GPP TR 38.901 at 0.5–100 GHz for anything cellular, Rayleigh/Rician fading for anything theoretical), a standard topology and parameter table, MATLAB or ns-3/OMNeT++-Simu5G as the engine, and you generate fresh realizations — public *datasets* are the exception, not the norm (78.46% of the surveyed papers gave no usable data-source information at all, per that same COMST survey).
4. **So a reviewer's expectation is reproducibility of the *method*, not of the *artifact***: they want to know that the comparison is fair (same channel model, same SNR sweep, same power/bandwidth budget, same number of realizations, baselines given a fair shot), that the baseline is correctly re-implemented (a wrong baseline is a common and fatal reviewer complaint), and that the parameters are complete enough to re-code; they will not ask you for a GitHub link.
5. **The contrast with the systems community is stark and is not accidental** — ACM SIGMOBILE (MobiCom/MobiSys/SenSys), ACM SIGCOMM/CoNEXT and USENIX NSDI run voluntary artifact-evaluation tracks with ACM badges and DOI-backed archives ([SenSys](http://sensys.acm.org/2024/art/), [SIGMOBILE AE guidelines](https://www.sigmobile.org/grav/about/artifact-guidelines), [NSDI '26 CfA](https://www.usenix.org/conference/nsdi26/call-for-artifacts)), whereas in IEEE ComSoc the strongest official wording found is TMLCN's "authors of accepted papers are strongly encouraged to: a) include a GitHub link to their codes and datasets … and/or b) to submit their codes" ([TMLCN policies](https://www.comsoc.org/publications/journals/ieee-tmlcn/policies-guidelines)) — and even the artifact-evaluation community reports that adoption "stagnates over the years" ([Gallenmüller et al., SIGCOMM/CoNEXT AE analysis](https://slices-de.org/20250909_SIGCOMM/05_Gallenmueller_Artifact_Evaluation.pdf)).

---

## 1. What a typical baseline section in JSAC / TCOM / TWC / TMC looks like

(Scope note: JSAC, TCOM and TWC are IEEE ComSoc journals; "TMC" is IEEE Transactions on Mobile Computing, published by the IEEE Computer Society, and it sits between the two cultures — it uses the same mathematical-simulation baseline style as ComSoc, but its conference neighbours are the ACM MobiCom/MobiSys world where artifact badges exist.)

### 1.1 The dominant pattern: a short enumerated list of re-derived schemes

Baselines are named *schemes*, not named *implementations*. The canonical shape is: "For comparison, we consider the following benchmark schemes: 1. … 2. … 3. …", where each item is a paragraph of math, and each is then re-coded by the authors. A verified full example — IRS-assisted OFDM, IEEE TWC — lists exactly three:

> "For comparison, we consider the following benchmark schemes: 1. **Channel Power Maximization (CPM)**: … the IRS coefficients as obtained via the initialization method based on the CPM proposed in Section IV-D, and the WF transmit power allocation … 2. **Random Phase**: … each IRS coefficient has a random phase independently and uniformly distributed in [0, 2π] and the maximum amplitude … 3. **Without IRS**: … the WF transmit power allocation and achievable rate based on the BS-user direct link only."

Source: [arXiv:1906.09956](https://arxiv.org/abs/1906.09956) (HTML full text, Section V-A), published as "IRS and OFDM: Protocol Design and Rate Maximization," IEEE TWC. Note the vocabulary: **water-filling (WF)**, **random phase**, **without-IRS** — textbook or trivially-degenerate references, not competitor systems.

A second verified example, ISAC waveform design, uses three *ablation-style* baselines and states its statistical setup in the same breath:

> "Fig. 4 compares the proposed scheme against three baseline approaches, as considered in [19, 7]: subcarrier assignment with uniform power allocation (SAUPA), random subcarrier assignment with power allocation (RSAPA), and random subcarrier assignment with uniform power allocation (RSAUPA). … In both RSAPA and RSAUPA, 50% of the subcarriers are randomly selected for sensing." … "The results are averaged over 3,000 Monte Carlo simulation trials."

Source: [arXiv:2603.08442](https://arxiv.org/abs/2603.08442), "OFDM Waveform Optimization for Bistatic Integrated Sensing and Communications."

### 1.2 The named-algorithm vocabulary you should expect

Recurring names that function as baselines in this literature (all encountered in the fetched full texts above or in the search results below):

| Family | Typical baseline names |
|---|---|
| Convex/optimization | **water-filling** (and *bounded* / *geometric* water-filling), **SCA / successive convex approximation**, **WMMSE**, **SDR / semidefinite relaxation** (+ Gaussian randomization), **Lagrangian dual decomposition**, **FP / quadratic transform**, **alternating optimization (AO)**, **exhaustive search** (as optimality reference), **CVX** as the solver |
| Learning | **DQN**, **DDPG**, **PPO**, **A3C**, **Q-learning**, plain supervised DNN/LSTM |
| Degenerate/heuristic | **random phase**, **equal/uniform power allocation**, **without-RIS/without-IRS**, **full-local** and **full-offload**, **greedy**, **max-ratio**, **no-power-control** |
| Bound | **CRB** as lower bound on estimation MSE; the relaxed/SDR problem objective as an **upper bound** on the original |

Concrete learning-baseline list (verified, MEC offloading with DDPG, IEEE-venue paper): *"(1) Full Local: all UEs execute their tasks by local computing. (2) Full Offload: all UEs offload their tasks to the MEC server and the whole computational resource F is allocated equally to each UE. … (3) DQN-based Solution: The conventional discrete action space based DRL algorithm, DQN [12], is also implemented as a solution approach."* — [NSF PAR 10180277](https://par.nsf.gov/servlets/purl/10180277). "Also implemented as a solution approach" is the tell: they wrote the DQN themselves.

### 1.3 Are baselines re-implemented from math, or downloaded?

Re-implemented. The evidence is the code packages themselves: when a TWC/TVT paper *does* release code, the package contains the baselines as local scripts, because there was nothing to import. Verified example — "Weighted Sum-Rate Maximization for Reconfigurable Intelligent Surface Aided Wireless Networks," IEEE TWC, whose repository ships one `.m` file per compared method:

> `without_RIS.m`, `RIS_phaserand.m`, `converge_AO_perfect.m` (alternating optimization, Section III), `converge_A2_perfect.m` (proposed), plus `generate_location.m` / `generate_pathloss.m` / `generate_channel.m` to synthesize the channel, and it instructs the user to download the Manopt toolbox first.

Source: [luanedge/WSR-maximization-for-RIS-system](https://github.com/luanedge/WSR-maximization-for-RIS-system).

Same pattern for DRL: [BJTU-MIMO/Power_Allocation_DDPG](https://github.com/BJTU-MIMO/Power_Allocation_DDPG) (IEEE TVT) is a MATLAB package containing `environment`, `actor`, `critic`, `ddpg`, `buffer` — a hand-written environment and a hand-written DDPG, which is what a re-implemented baseline looks like in practice.

### 1.4 Do authors share code? Sometimes — and it is a *choice by research group*, not a venue norm

Real, live, verified examples (all reachable as of this writing):

- [emilbjornson/scalable-cell-free](https://github.com/emilbjornson/scalable-cell-free) — "Simulation code for 'Scalable Cell-Free Massive MIMO Systems,'" IEEE TCOM. Björnson's group has a standing practice: one MATLAB package per paper, one script per figure, "We encourage you to also perform reproducible research!"
- [CristinaGomezSantamaria/optimal-beamforming](https://github.com/CristinaGomezSantamaria/optimal-beamforming) — IEEE SPM paper.
- [ZheWang77/Uplink_Precoding_CF_mMIMO_Multi_Antenna_Users_I_WMMSE](https://github.com/ZheWang77/Uplink_Precoding_CF_mMIMO_Multi_Antenna_Users_I_WMMSE) — IEEE TCOM 2023.
- [zctzzy/STCNet](https://github.com/zctzzy/STCNet) — "Source code of IEEE JSAC."
- [lorenzomiretti/duality](https://github.com/lorenzomiretti/duality) — IEEE TSP 2024.

But the population-level picture is much worse than these examples suggest; see §5.

---

## 2. Artifact/code-release culture: IEEE ComSoc vs. ACM vs. USENIX

**The split is real and it is a venue-policy split.**

**IEEE / ComSoc — encouragement, no requirement, no badges:**

- IEEE Author Center: *"All IEEE authors are encouraged to share their data, code, and other research outputs to facilitate verification and reproducibility of experiments and their conclusions."* — [IEEE Research Reproducibility](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/research-reproducibility/). IEEE promotes Code Ocean capsules and IEEE DataPort, i.e. *optional* hosting.
- ComSoc journal pages: TMLCN is the most explicit — *"In order to promote reproducible research, authors of accepted papers are strongly encouraged to: a) include a GitHub link to their codes and datasets in their camera-ready version and/or b) to submit their codes and other relevant experimental artefacts."* — [TMLCN policies](https://www.comsoc.org/publications/journals/ieee-tmlcn/policies-guidelines). The [JSAC](https://www.comsoc.org/publications/journals/ieee-jsac/policies-guidelines), [TCOM](https://www.comsoc.org/publications/journals/ieee-tcom/policies-guidelines) and [TWC](https://www.comsoc.org/publications/journals/ieee-twc/policies-guidelines) author-guideline pages I fetched contain **no code/data-sharing clause at all** — only "supplementary materials … requested" after acceptance.
- There is **no artifact-evaluation track and no ACM/IEEE badge awarded for reproducibility** in ComSoc journals.

**ACM SIGMOBILE (MobiCom / MobiSys / SenSys) — formal AEC with three independent badges:**

- *"At SenSys, we aim to … advance the state of the art. However, traditional peer-review of papers alone cannot guarantee the reproducibility of the research results. The Artifact Evaluation process complements the paper review process by verifying that the artifacts (e.g., code, data, scripts, or instructions) associated with a paper are correct, complete, and properly documented."* … "Authors will apply for specific ACM badges for 'Artifact available', 'Artifact evaluated – functional', 'Results reproduced' … These badges are independent, and authors may seek one, two, or all three of the badges." — [SenSys 2024 Call for Artifacts](http://sensys.acm.org/2024/art/).
- The badge bar is concrete: "Artifacts Available" requires *"a publicly accessible DOI or link to the source code repository"*; hardware-dependent papers must give *"remote access … e.g., using Zoom, Microsoft Teams, or Google Hangouts with anonymous accounts"*. — [SIGMOBILE artifact guidelines](https://www.sigmobile.org/grav/about/artifact-guidelines).

**ACM SIGCOMM / CoNEXT — same model, and it is not growing:**

- "Analysis of AE — Development of the SIGCOMM conference AE over Time … **Adoption stagnates over the years**"; "AE participation stagnates"; "Hardware requirements may prevent effective reproduction" (3 artifacts needed NVIDIA GPUs, 3 needed Intel Tofino switches, one needed 512 GB RAM, one needed >$1000 of AWS). — [Gallenmüller, Saucez, Carle, *SIGCOMM and CoNEXT Artifact Evaluation and Infrastructure Needs*, 2025](https://slices-de.org/20250909_SIGCOMM/05_Gallenmueller_Artifact_Evaluation.pdf).
- Earlier, more optimistic baseline of the same program: [Saucez, Iannone, Bonaventure, "Evaluating the artifacts of SIGCOMM papers," ACM CCR 2019](https://dl.acm.org/doi/10.1145/3336937.3336944).

**USENIX NSDI — explicit, all-papers, but still voluntary:**

- *"The NSDI '26 artifact evaluation process is open to all accepted papers. … Artifact evaluation is optional, although we hope all papers will participate."* Three badges, DOI-backed long-term storage encouraged, plus *"the AEC would inform and advise the Program Committee"* on decisions in future. — [NSDI '26 Call for Artifacts](https://www.usenix.org/conference/nsdi26/call-for-artifacts).

**EuroSys (for calibration of what a mature AEC looks like):** 5 years of AE, three badges, 98 committee members in 2025, and an explicit roadmap that includes *"Require AE for all accepted papers, with opt-outs"* and *"Tie AE outcomes to paper acceptance"* — i.e. even the strongest artifact community has not yet made artifacts mandatory. — [SIGOPS, *Lessons from Five Years of Artifact Evaluation at EuroSys*](https://www.sigops.org/2025/lessons-from-five-years-of-artifact-evaluation-at-eurosys/).

**Signal-processing precedent that failed by the standard it set:** a EURASIP *Journal on Advances in Signal Processing* special issue on reproducible research required code and data at submission, checked during review, with software downloadable after publication. Result: *"at the end only 4 papers were accepted the reason being that among the 31 submissions most papers were immediately rejected as they did not show any sign of reproducibility at all."* — [Rupp, Gini, Pérez-Neira, Pesquet-Popescu, Pikrakis, Sankur, Vandewalle, Zoubir, *Reproducible research in signal processing*, EURASIP JASP 2011](https://link.springer.com/article/10.1186/1687-6180-2011-93). This is the cleanest natural experiment showing that the communications/SP community's actual code-sharing rate was near zero when it was measured directly.

---

## 3. Where does the simulation data come from?

**Norm: there is no dataset. There is a channel model, a parameter table, and a random-number generator.**

The 2025 IEEE COMST survey of 130 ML-for-resource-allocation-in-wireless papers measured this directly ([PDF](https://oulurepo.oulu.fi/bitstream/10024/54634/1/nbnfioulu-202503202122.pdf), Pivoto et al., DOI 10.1109/COMST.2025.3552370):

- **128 of 130 articles used a simulation environment**; only **5** involved additional experimental equipment.
- **Only 40 of 130** stated the software/framework/IDE used. Among those, **MATLAB was the most common (28 studies)**, then Python (32 mentions of the language), PyCharm (4), one C++.
- Named engines seen in their Table IX: **MATLAB** (with Optimization/NN/RL toolboxes), **ns-3** (several papers, incl. the **5G-LENA** module and `ns3gym` RL framework), **NS-2** (legacy), **Mininet-WiFi** (5 papers), **Castalia**, **LoRaSim**, **IoTSim-Osmosis**, **LTE-Sim / 5G-Scheduler**, GNU Radio + USRP (for the few hardware papers), SUMO (mobility), CloudSim/iFogSim.
- **Datasets are borrowed, not shared:** the few "real" datasets are usually datasets from *other* fields or a single operator's proprietary data — the **Telecom Italia Big Data Challenge** (Milan) dataset (SMS/call/web traffic on a 100×100 grid) and a **GWAT-13 / Materna** cloud-provider VM-utilisation dataset are the representative examples they cite.
- **Standardised public wireless benchmarks do exist but are niche and model-specific:** [DeepMIMO](https://github.com/DeepMIMO/deepmimo) (ray-tracing datasets), the DeepSig **RadioML** modulated-signal datasets ([deepsig.ai/datasets](https://www.deepsig.ai/datasets/)).

**The standard simulation setup** — what a reviewer reads as "the experiments" — is:

- **Channel model:** for cellular/6G claims, **3GPP TR 38.901** ("Study on channel model for frequencies from 0.5 to 100 GHz"), now at Release 19 ([ETSI TR 138 901 V19.1.0](https://www.etsi.org/deliver/etsi_tr/138900_138999/138901/19.01.00_60/tr_138901v190100p.pdf), [whatthespec mirror](https://whatthespec.net/friendlyspec/spec/38.901/19.4.0)). For theory papers, **Rayleigh / Rician / correlated Rayleigh** with an explicit model for LoS vs NLoS, an exponential power-delay profile, and a stated SNR-gap Γ (the verified IRS example uses `Γ = 8.8 dB`). Comparisons of 3GPP vs NYUSIM channel models are themselves publishable: [arXiv:1707.00291](https://arxiv.org/abs/1707.00291).
- **Topology:** standard scenarios (UMa/UMi, indoor office), hexagonal or Poisson-point-process base-station layouts, or a simple grid.
- **Averaging:** "averaged over 100 independent channel realizations" ([arXiv:1906.09956](https://arxiv.org/abs/1906.09956)) or "3,000 Monte Carlo simulation trials" ([arXiv:2603.08442](https://arxiv.org/abs/2603.08442)). Median/percentile-vs-SNR curves, not single-run numbers.
- **Engine variants for system-level work:** [ns-3 + 5G-LENA](https://arxiv.org/list/cs/2024-04) for 5G NR system-level simulation, [Simu5G for OMNeT++](https://ieeexplore.ieee.org/abstract/document/9211504) (Nardini et al.), the [Vienna 5G link/system-level simulators](https://arxiv.org/abs/1806.03929).
- **Reporting quality is the weak point, not the tooling:** **52 of 130 articles (~40%) lacked sufficient information about the validation environment**, and the survey's recommendation is the revealing one — *"Future efforts should focus on establishing standardized guidelines for reporting simulation and experimentation setups."*

---

## 4. LLM-agent-in-networking papers (2024–2026): baselines and evaluation

A dedicated verification pass over 16 papers (full texts read, artifact links HTTP-checked on 2026-09-12) gives the following picture. Detailed table: `/home/orion/Communications/.research-sub3/report.md`.

**What the standard baseline set is:** *a GPT-4o/GPT-5-class frontier model + one open-weight LLM (usually Qwen or Llama), both run zero-shot or inside the same ReAct tool-use loop, scored by executable test cases or an LLM judge.* Counts over the 14 measurement papers: frontier proprietary LLMs as baseline **12/14**; open-weight LLMs **9/14**; a fixed ReAct scaffold shared across models **8/14**; classical optimization / rule-based / DRL baselines **only 5/14** and essentially absent from the network-*operations* papers; **human-expert baselines: zero**.

Important nuance: **ReAct is usually the harness, not the baseline.** Because every model runs in the same ReAct loop, papers ablate *model choice* or *scaffold design* rather than prompting strategy; explicit zero-shot vs CoT vs ReAct comparisons are rare. Examples of the exceptions: "Agentic AI Empowered Intent-Based Networking for 6G" compares rule-based IBN / direct LLM prompting / monolithic single agent / proposed multi-agent ([arXiv:2601.06640](https://arxiv.org/abs/2601.06640)); "WirelessOpsAgent" compares Direct / WirelessAgent++ / CRITIC-style ([arXiv:2608.08277](https://arxiv.org/abs/2608.08277)).

Three verified baseline statements worth quoting:

- **LLMs as the baseline instead of classical methods:** *"Since classical methods require manual expertise, MAINTAINED prioritizes the autonomous orchestration of reliable algorithms. Consequently, we evaluate performance against state-of-the-art LLMs and RAG baselines rather than classical methods."* Baselines = ChatGPT-4o, Claude Sonnet 4, DeepSeek-R1, bare Qwen3-4B, Qwen3-4B+RAG. — [arXiv:2601.13843](https://arxiv.org/abs/2601.13843) (IEEE Communications Magazine, accepted).
- **Classical synthesis tools explicitly excluded:** *"Our evaluation focuses on LLM agents, so traditional configuration synthesis tools are not included as baselines; they start from formal specifications rather than from natural-language intent."* Baselines = qwen3-8B/32B and deepseek-v4-flash/pro, each with thinking off/on. — [arXiv:2608.23179](https://arxiv.org/abs/2608.23179), NetConfArena.
- **Agent scaffolds as baselines, model as the controlled variable:** FaulT-Bench evaluates **SADE, a ReAct agent, and Claude Code** on the same 200 Kathará-emulated scenarios, scored by an LLM judge. — [arXiv:2608.27021](https://arxiv.org/abs/2608.27021).

**Evaluation: mostly their own task, with a shared-benchmark movement starting in 2026.** 8/14 invented their own task/simulator with no shared benchmark; 6/14 reused something public — and even then the reuse is mostly *infrastructure* (GNS3, Kathará, NS-3, OpenAirInterface, MCP tool interfaces) rather than shared *task instances*. The clearest genuine reuse is FaulT-Bench building on NIKA's dataset and tool interface ([NIKA, arXiv:2512.16381](https://arxiv.org/abs/2512.16381)).

Public benchmarks that have emerged, with their anchors:

- **NIKA** ([arXiv:2512.16381](https://arxiv.org/abs/2512.16381), [code](https://github.com/sands-lab/nika)) — 640 incidents / 54 issues / 5 scenarios / >30 MCP tools; the emerging *reuse hub*, with FaulT-Bench built directly on it.
- **NetConfEval** (CoNEXT 2024) — [paper PDF](https://marchiesa.bitbucket.io/docs/chiesa/netconfeval-conext-2024.pdf), [code](https://github.com/NetConfEval/NetConfEval), [HF dataset](https://huggingface.co/datasets/NetConfEval/NetConfEval). Baselines: GPT-4/Turbo/3.5 (+fine-tuned), CodeLlama variants; verified by deploying configs on FRRouting containers rather than by a judge.
- **TeleCom-Bench** (KDD 2026) — [arXiv:2605.18025](https://arxiv.org/abs/2605.18025), [code](https://github.com/ZTE-AICloud/TeleCom-Bench): 12 evaluation sets, 22,678 samples, LLM-only baselines, and the "Execution Wall" finding (knowledge-comprehension accuracy ~90% collapsing to ~30% on end-to-end tasks).
- **WirelessOptBench / WirelessOpsAgent** — [arXiv:2608.08277](https://arxiv.org/abs/2608.08277), artifact behind an anonymous-review login.
- **NetArena** ([arXiv:2506.03231](https://arxiv.org/abs/2506.03231), [code](https://github.com/Froot-NetSys/NetArena)) — dynamic on-demand query generation explicitly motivated by contamination risk in static benchmarks.
- **6GAgentGym** — [arXiv:2603.29656](https://arxiv.org/abs/2603.29656): the richest baseline set in the sample (8 frontier LLMs **plus** Threshold-Rule, MAPE-K heuristic with 50 hand-written rules, and DRL-Slicing; Experiment Model calibrated on NS-3 data), and **no code link**.
- **NetConfBench**, proposed as the *standardisation* answer in the IETF NMRG draft — GNS3 emulator, 40 tasks, reasoning/command/testcase scores: [draft-cui-nmrg-llm-benchmark-01](https://datatracker.ietf.org/doc/html/draft-cui-nmrg-llm-benchmark-01).

A structural observation that predicts where this subfield is going: the four 2025–26 papers that are being cited as benchmarks each justify themselves by attacking the *same* prior practice in almost identical words — NetConfArena: *"static command generation or … overly simplified settings"*; FaulT-Bench: *"only on accurate tickets and always assume a fault is present"*; WirelessOpsAgent: *"task solving from fixed observations"*; NetArena: *"static design … contamination … high statistical variance."* That is the signature of a field that has just acquired a shared baseline and is now racing on top of it — the opposite of the classical ComSoc situation, where the reference points (water-filling, random phase, without-IRS) have been stable for a decade.
- Critique source: *"Large Language Models for Agentic NetOps and AIOps: Architectures, Evaluation, and Safety"* ([arXiv:2605.12729](https://arxiv.org/abs/2605.12729), 59 pp.) — the most on-point meta-source: it documents a **capability–assurance gap** (evidence is strong for read-oriented assistance and tool-grounded diagnosis but "substantially less complete" approaching configuration change and closed-loop operation), argues for moving "beyond static question answering and model accuracy towards workflow-level assessment," and names proprietary incident corpora, heterogeneous telemetry infrastructure, weak ground truth and **benchmark contamination** as the field's core problems. It ships an evidence-audit dataset on Mendeley Data (DOI 10.17632/2p5ppxzy4s.3).
- **NetInjectBench** ([arXiv:2607.10490](https://arxiv.org/abs/2607.10490)) — 130-scenario *prompt-injection* benchmark for network-ops agents where the baselines are **defenses rather than models**: naive execution 82.5% unsafe vs prompt-only 25.6%, Self-Reminder 21.7%, Spotlighting 18.3%, two-pass LLM judge 10.0%, static allowlisting 5.0% but 0% usefulness.

**Two methodological trends worth flagging to a reader of this literature:** (i) *verification regressed then partly recovered* — NetConfEval (2024) had no LLM judge at all and verified by deploying configurations on a real FRRouting daemon, whereas some 2026 work scores free text with an LLM judge; the strongest 2026 papers pair the judge with hidden executable test cases. (ii) *no human-expert baseline exists in any of the 14 sampled measurement papers*, even though several evaluate tasks that operators perform daily.

**Code release is materially more common here than in classical IEEE communications papers** — but with two caveats. Of 16 papers, 8 had live artifacts, 3 announced artifacts that were broken or access-restricted at check time (one 401 anonymous-review login, one 404 dead link), and 5 shipped nothing. Benchmark papers release almost universally; algorithm/application papers often do not, and the IEEE-published items in the sample were the weakest (one IEEE ComMag paper released, one did not, and the IEEE OJ-COMS ReAct paper defers release until after publication).

---

## 5. Reproducibility studies with actual numbers

**Communications-specific (the strongest evidence in this report):**

| Finding | Population | Source |
|---|---|---|
| **Only 18/130 (13.85%)** provided usable information about the sources/databases of their data samples | 130 ML-for-resource-allocation papers in wireless | [COMST survey PDF](https://oulurepo.oulu.fi/bitstream/10024/54634/1/nbnfioulu-202503202122.pdf) |
| **102/130 (78.46%)** gave no clear or sufficient information about their data sources; **13** offered data/code "upon request" | same | same |
| **~40% (52/130)** lacked sufficient information about the validation environment | same | same |
| *"The vast majority of the 27 surveyed papers do not provide or share the source code of the proposed ML algorithms."* Only one of the 27 mentions the possibility of making code accessible; another offers data on request | the 27 papers they audited parameter-by-parameter | same |
| **4 of 31** submissions survived an explicitly reproducibility-gated special issue; the rest were rejected outright *"as they did not show any sign of reproducibility at all"* | EURASIP JASP reproducible-research special issue | [Rupp et al. 2011](https://link.springer.com/article/10.1186/1687-6180-2011-93) |
| Reproducible research is named as an open challenge, with the proposed fix being *"a set of common scenarios"* | Wi-Fi ML survey (IEEE COMST) | [Wi-Fi Meets ML](https://doi.org/10.1109/COMST.2022.3179242) |

**Networking/systems measurements (the contrast case):**

| Finding | Source |
|---|---|
| **~15%** of MobiHoc simulation papers (2000–2005) were repeatable; **~33% of 134** *Telecommunications Policy* papers released datasets but **only 9% released code**; **~32% of 600** ACM CS papers exhibited weak repeatability | [Bajpai et al., *Challenges with Reproducibility*, SIGCOMM 2017 Reproducibility Workshop](http://conferences.sigcomm.org/sigcomm/2017/files/program-reproducibility/3.pdf) |
| **56.2%** of 402 ACM computer-systems papers backed by code actually shared it; **32.3%** built within 30 minutes; **48.3%** built with extra effort; **54.0%** built by the author; **43.3%** of accepted papers submitted an AE artifact and **29.5%** were accepted (7 conferences); of 177 author survey responses, **83.1%** said the released code is identical to the result-producing version | [Collberg, Proebsting, Warren, *Repeatability in computer systems research*, **Communications of the ACM** 59(3), DOI 10.1145/2812803](https://dlnext.acm.org/doi/10.1145/2812803) |
| **~40%** of ML-based wireless papers gave insufficient information about tools/validation; only **28/130** report MATLAB, **4** PyCharm | [COMST 2025 survey](https://oulurepo.oulu.fi/bitstream/10024/54634/1/nbnfioulu-202503202122.pdf) |
| Artifact-evaluation badge adoption at SIGCOMM and CoNEXT **"stagnates over the years"**; AE is the bottleneck on author/reviewer time. Concrete example — **CoNEXT 2023: 30 papers accepted, 19 (63%) submitted artifacts**, and overall *award* rates were **60% (Available) / 47% (Functional) / 33% (Reusable)** | [Gallenmüller, *Reproducible Experiments: SIGCOMM and CoNEXT AE*, 2025](https://slices-de.org/04_Gallenmueller_2025-07-02_Reproducible_Experiments.pdf) and [the companion deck](https://slices-de.org/20250909_SIGCOMM/05_Gallenmueller_Artifact_Evaluation.pdf) |
| AE at EuroSys remains **voluntary**, and the chairs' roadmap lists *"Tie AE outcomes to paper acceptance"* as still-to-do | [SIGOPS blog](https://www.sigops.org/2025/lessons-from-five-years-of-artifact-evaluation-at-eurosys/) |
| **48%** of ACSAC, **26%** of AsiaCCS, **31%** of EuroS&P, **38%** of WiSec artifacts are made for reproduc… (truncated; the paper is an 11-year review of applied-security venues) | [Reproducibility in Applied Security Conferences, ACM](https://dl.acm.org/doi/10.1145/3736731.3746151) *[search snippet]* |

**Calibration from adjacent fields (why the ComSoc culture is what it is):**

- **NeurIPS** papers with open-source code rose from **27.6% (2016)** to **>60% (2019 onward)**, with a **20.6%** jump between 2018 and 2019 that correlates with the NeurIPS reproducibility checklist. **ICRA** (robotics) exceeded **5%** only once in six years; **CDC** (control) first surpassed **2%** in 2021. — [Zhou et al., *What is the Impact of Releasing Code with Publications?*, IEEE Control Systems Magazine / arXiv:2308.10008](https://arxiv.org/abs/2308.10008). **CDC is the right cultural analogue for TCOM/TWC**: a control/optimization community where re-derivation from equations was historically considered sufficient.
- Corroborating pattern: the *MobiHoc/ToIP/ACM* numbers above, and the *"[t]he CS networking discipline is extremely fast-paced … Norm is to get the paper accepted, release artifacts later"* diagnosis in the same SIGCOMM workshop deck.
- Broader AI baseline over a decade: papers sharing **both code and data rose from 11% (2014) to 64% (2024)** across 56,800 conference papers from five top-tier AI venues — [Coakley, Snelleman, Hoos, Gundersen, *The embrace of open science*, arXiv:2606.16974](https://arxiv.org/pdf/2606.16974v2). That is the direction of travel in ML; ComSoc journals have no equivalent mechanism pushing them that way.
- The reimplementation-as-methodology point has an empirical echo: Raff was able to reproduce **63.4% of 255 papers by reimplementing algorithms from scratch** (cited in the same paper), whereas Gundersen et al. reproduced **33% of papers that provided only data vs 86% of papers that shared both code and data**. Re-derivation works, but it is measurably worse than having the artifact.

---

## 6. What a new paper should actually do — the reviewer's checklist

If you are writing a TWC/TCOM/JSAC-style paper and want the comparison to survive review:

1. **Re-implement the baselines yourself, and say so precisely.** Name each one, cite the paper you took the *algorithm* from, and state that it was re-implemented — "we implement [X] following the update rules in [ref, eq. (n)]" — so the reviewer can check the equations rather than wonder about a library.
2. **Give every baseline a fair shot:** same channel realizations, same SNR sweep, same power/bandwidth/complexity budget, same number of Monte Carlo trials, and tune each baseline's free parameters rather than freezing them at the proposed method's values. The most common fatal criticism is a strawman baseline.
3. **Include at least one degenerate reference and one bound or exhaustive-search reference** — "without RIS", "uniform power", "random phase", or exhaustive search in the small regime — so the reader can place your gain on the axis. This is universal practice in the verified examples above.
4. **Make the data section falsifiable without a repository:** complete parameter table (carrier frequency, bandwidth, topology, path-loss model and reference such as TR 38.901, noise figure, fading distribution, codebook sizes), explicit trial count, explicit seeds or generation procedure, and pseudocode for your algorithm.
5. **Treat code release as optional overhead, not as evidence of quality** — but if you release, release a single MATLAB/Python package with one script per figure, a README mapping claims to scripts, and (for the systems-adjacent venues) a DOI-backed archive; note that at SIGMOBILE/NSDI the *badges* are what a reviewer looks for, and at ComSoc they are not available at all.
6. **If you are writing in the LLM-agent space instead, invert the expectations:** you will be expected to compare against a frontier model plus an open-weight model in a documented prompting/agent loop, to state your agent scaffold (ReAct, tool-use, multi-agent) explicitly, to evaluate on a *named public benchmark* if one fits (or to release yours with executable test cases rather than an LLM-judge-only score), and to release code or the benchmark — because in that subfield a benchmark without an artifact is not citable as a benchmark.

### The five-sentence answer, restated

> A new paper in this field compares against existing methods by **re-deriving them from their published mathematical descriptions and re-coding them in the authors' own simulator** — named schemes like water-filling, random phase, without-IRS, SCA/SDR, alternating optimization, DQN or DDPG, typically implemented as a handful of MATLAB scripts in one package — rather than by running anyone's released code, because essentially no baseline in JSAC/TCOM/TWC/TMC ships runnable code: only 9% of networking papers released code in the classic measurement, and a 2025 IEEE COMST survey found that "the vast majority" of the 27 ML-for-wireless papers it audited release no source code at all. Experiments are run on **synthesized data** — a standardized channel model (3GPP TR 38.901 or Rayleigh/Rician), a standard topology and parameter table, MATLAB or ns-3/Simu5G, and Monte-Carlo-averaged curves over independent channel realizations — because 128 of 130 surveyed papers used simulation, only 5 used hardware, and 78.46% gave no usable data-source information. **What a reviewer expects is therefore methodological reproducibility, not artifact reproducibility**: a complete system model and parameter list, correctly re-implemented and fairly tuned baselines, a degenerate scheme and a bound or exhaustive-search reference, and a stated averaging convention — with code release treated as a bonus, since IEEE only "encourages" sharing and ComSoc offers no artifact badges, unlike ACM SIGMOBILE/SIGCOMM/CoNEXT and USENIX NSDI, whose voluntary artifact-evaluation tracks award ACM badges and whose own organizers report that adoption "stagnates over the years." The one fast-moving exception is the LLM-agent-for-networking literature, where the accepted practice has already shifted to comparing a frontier model against an open-weight model inside an explicitly documented ReAct/tool-use scaffold on a named or newly released benchmark with executable test cases, and where releasing the artifact is now the majority practice. In short: **if you submit to a ComSoc journal, expect to be judged on whether your equations and parameters would let someone else rebuild your experiment; if you submit to a systems venue or an LLM-agent paper, expect to be judged on whether they can run your artifact.**

---

## 本报告的来源

调研过程中抓取的原始材料（COMST 调查 PDF、论文、演示稿、会议政策页、16 篇 LLM-agent 论文的核验表）
存放在临时工作目录中，**已随工作区清理删除**。
本文件保留了全部结论与引用链接；**如需复核某条，请按正文中的 URL 重新抓取**。

---

> ⚠️ **本节按当时的「agent 中心」框架写**。当前定位下，本文中心是
> **实体生命周期下的任务维持**，与本节所说的"执行语义"不是同一层。
> 本节的事实与引文仍可用，**但"我们的批评是什么"需要按 [`../../README.md`](../../README.md) §3.5 重写**。

## 7. ⚠️ 战略判断：这个子领域正在"同一根稻草人"上竞速

**四篇 2025–26 论文用几乎相同的话否定同一个既有做法**：

| 论文 | 它攻击的对象（原文措辞） |
|---|---|
| **NetConfArena** | *"static command generation… overly simplified settings"* |
| **FaulT-Bench** | *"only accurate tickets and always assume a fault is present"* |
| **WirelessOpsAgent** | *"fixed observations"* |
| **NetArena** | *"static design… contamination… high variance"* |

⇒ **这是一个刚刚获得"共享 baseline"、正在其上竞速的领域的典型特征**——
与经典 ComSoc 恰好相反（那里的参照点 water-filling / random phase / without-IRS 十年不变）。

### 7.1 对我们的直接影响：**必须把自己和那根稻草人区分开**

**这个子领域拥挤的批评是：「评测是静态的 / 过度简化」。**

**我们的批评是另一件事**：

> **「工具接口被默认可用，执行语义在 partial failure 下不成立。」**

这两者**不同**，但**很容易被读成同一件事**。如果不显式区分，我们会显得像第五篇说同样话的论文。

**必须写清楚的区别**：

| | 拥挤的批评 | **我们的批评** |
|---|---|---|
| 攻击对象 | 评测**任务**是静态的、简化的 | **执行语义**假定工具可用 |
| 失败原因 | 任务代表性不足 | **信道导致结果不可知** |
| 修复方向 | 更真实的任务/环境 | **lifecycle-aware runtime** |
| 是否已被占 | ✅ **正在被快速占满** | 🟡 仍空（见 `s6-6` 附录 A） |

⇒ **这是当前的定位风险，也是必须尽早写进 Introduction 的一句话。**

### 7.2 三条可直接引用的强支撑

1. **TeleCom-Bench 的 "Execution Wall"**（KDD 2026）
   知识理解准确率 **~90% → 端到端任务 ~30%**
   ⇒ **直接支撑我们的 claim 2：「能力 ≠ 执行正确性」。**

2. **arXiv 2605.12729**（59 页，*LLMs for Agentic NetOps and AIOps*）—— 最对症的元文献
   记录了一个 **capability–assurance gap**：读向辅助证据充分，
   但**一旦逼近配置变更/闭环操作就"substantially less complete"**；
   并点名该领域的核心问题是**专有事件语料、弱 ground truth、预训练污染**。
   随文发布 Mendeley 证据审计数据集（DOI `10.17632/2p5ppxzy4s.3`）。

3. **NIKA** 正在成为**复用枢纽**（640 事件 / 54 问题 / **>30 个 MCP 工具**），
   FaulT-Bench 直接建在它的数据集与工具接口上
   ⇒ 说明该领域**工具面已经开始标准化**，这对我们是有利的（可以对齐）。

### 7.3 一条方法论警示（对我们也是约束）

**验证方式先退化、后部分恢复**：
- NetConfEval（CoNEXT 2024）**不用 LLM judge**，把配置部署到**真实 FRRouting 守护进程**上验证
- 部分 2026 工作改用 **LLM judge 给自由文本打分**
- 最强的 2026 工作把 judge **与隐藏的可执行测试用例配对**

⇒ 我们**必须采用后者**：**可执行测试用例 + judge 配对**，不能只给 LLM judge。
这条已并入 `s6-5` 的实验协议。

**另有**：14 篇样本中**没有任何一篇设人类专家 baseline**——即使其中几篇评测的正是运维人员每天在做的事。
⇒ 我们**也不需要**，但要意识到这是一个共同的弱点。

---

## 8. 无法确证的事项（Caveats）

- **No published study measures ComSoc journal code-release rates directly.** The best proxies are the IEEE COMST survey (§5), the EURASIP special issue, and computing-systems reproducibility studies. No ComSoc-specific percentage is invented here.
- Several 2026 arXiv IDs referenced (NetConfArena, FaulT-Bench, WirelessOpsAgent, 6GAgentGym, TeleCom-Bench) are preprints with no venue comment; treat venue attributions as author-declared.
- Two anchors that looked like shared LLM-agent benchmarks are not: "NetGym" resolves to *NetworkGym*, a DRL/MARL multi-access traffic-management environment ([arXiv:2411.04138](https://arxiv.org/abs/2411.04138)), and "NetBench" resolves to a network-*traffic* foundation-model dataset ([arXiv:2403.10319](https://arxiv.org/abs/2403.10319)).
- Two ACM DL pages are Cloudflare-blocked from this sandbox (the applied-security reproducibility paper, and Collberg's ACM version); the Collberg figures above came from a downloaded copy of the open Arizona TR — flagged inline — and the security paper's figures are marked *[search snippet]*.
- NetArena's arXiv v2 title differs from the framework name used inside its own full text ("NetPress").
