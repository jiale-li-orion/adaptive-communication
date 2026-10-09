# Reference plan — Future-Choice paper

状态：**current citation map / shared bibliography = `paper/refs.bib`**。

通信论文不需要刻意压引用数量。背景与 Related Work 可以成簇引用，但最近邻工作必须明确承担 novelty boundary，不能只拿老引用做稻草人。

本文继续复用旧系统稿 / Agentic 稿已经核过的参考文献；新增 2025–2026 近邻文献也统一进入 `paper/refs.bib`，不建立第二份 bib。

## 1. Emergency / challenged communication substrate

```text
fall2003dtn, jain2004dtnrouting, dtnarch, rfc5050, rfc9171,
iranmaneshdtnqueue, ccsdssabr, sateriot, dzt0450, dzt0460, bdsps3
```

用途：store-carry-forward、有限 contact、缓存/expiry、卫星/非地面备份、延迟反馈与地灾行业约束。

## 2. Freshness / energy / deadline / control value

```text
kaul2012aoi, yates2021aoisurvey, bacinoglu1905, zakeri2311,
costa2014pm, wang2021voi, park2018wncs, kam2016deadline,
krishnan2019multihop, razavivideo, wada2009timeout, leboudec01
```

边界：不 claim 首次考虑 freshness / energy / deadline / task value；Future-Choice 只负责 hard completion set。

## 3. Semantic communication / goal-oriented value

基础背景：

```text
uysal2021semantic, guo2025semcomnet, jiang2025worldmodelsemcom,
du2024distributedfm, sheng2025wirelessfm
```

最近邻必须出现：

```text
agheli2025pull
wang2026wmcdt
saz2026logicalsemcom
zhao2026wirelesscontext
```

- `agheli2025pull`：active query / long-term GoE / query-cost constrained scheduling；
- `wang2026wmcdt`：closed-loop long-horizon return / counterfactual causal semantic value；
- `saz2026logicalsemcom`：goal-oriented decision state / evidence sufficiency / logical verifiability；
- `zhao2026wirelesscontext`：dynamic context orchestration under latency/energy/memory constraints。

核心区分：value、context relevance、decision sufficiency 都不能单独保证当前 action 后仍存在 hard operational completion continuation。

## 4. Active information acquisition / decision sufficiency

```text
javdani2014drd, huang2022asr, deshpande2013sbfe,
hellerstein2022adaptivity, green2007provenance, lin2026blip,
gao2026activemeasuring
```

用途：主动把 novelty boundary 压窄。不能 claim decision-aware acquisition、minimum sufficient evidence、query can hurt the future、fixed-guard certificate stopping。

本文 residual：world-changing action + future observation branch + hard obligation/resource continuation set。

## 5. Wireless / agentic AI landscape

```text
liang2025llmwireless, sheng2025wirelessfm, jiang2026largemodelsurvey,
lu2026agenticgnn, li2026agenticwireless, jiang2026agenticibn,
topollm, ossgpt, lu2026wirelessops
```

`lu2026wirelessops` 尤其重要：evidence validation / dependency-scoped repair / action assurance 已经是强近邻；本文不 claim evidence assurance 本身。

## 6. Benchmark related work

必须引用：

```text
ferrag2026sixgbench
tong2026wirelessbench
ferrag2026alpha3bench
dora2026
```

- **6G-Bench**：standardization-driven taxonomy、scenario construction、automatic filtering + expert validation、broad model panel。A 的差异是 executable physical lifecycle + final operational obligation state，而非 MCQ/truncated trajectory。
- **WirelessBench**：three-tier capability hierarchy、tolerance-aware scoring、tool-necessary tasks、reasoning-chain diagnosis。A 的差异是 communication substrate itself changes under action。
- **α³-Bench**：multi-turn UAV agent under dynamic 6G conditions，兼顾 task outcome/safety/tool consistency/robustness/communication cost。C 不得冒充“更完整 UAV benchmark”。
- **DORA**：real disaster events、expert-authored operational tasks、typed tools、replayable trajectories、failure taxonomy。A 更接近 final-state evaluator：允许多条合法 trajectory。

## 7. External UAV / emergency mission context

可复用：

```text
sharma2024uavmarl, xu2025uavllm, icldc, icgrestore
```

作用：说明 UAV / emergency networking 中 sequential mission planning、multi-hop coordination、restoration/control 已有丰富背景。

external `uav-attention-routing` source paper 使用：

```text
dehghani2026uavattention
```

当前 bibliographic status 为 authors' companion repository 所列 **IISE Transactions, under review, 2026**；正式发表后再升级 venue metadata。

## 8. 2026-10-09 新增到共享 bib

```text
ferrag2026sixgbench
tong2026wirelessbench
ferrag2026alpha3bench
agheli2025pull
wang2026wmcdt
zhao2026wirelesscontext
saz2026logicalsemcom
gao2026activemeasuring
kaelbling1998pomdp
bitmonnot2016contingentobserve
cheng2026stnust
lei2026amcats
ahmad2025iotvoi
junges2021reachability
ajdarow2023rsgoshield
carr2023partialshield
```

后一组按 IJCAI / Elsevier / Springer / IEEE WF-IoT 正式论文页核查：

- `kaelbling1998pomdp`：合法 history / partially observable policy 的标准背景；**本稿使用 robust finite-support AND/OR 可行性，不宣称等同于 Bayesian POMDP optimal control**。
- `bitmonnot2016contingentobserve`、`cheng2026stnust`：contingent observation / sensing action / dynamic controllability 已有形式化。本文的差异须放在 observation resource cost + communication obligation feasibility，而非“首个可选择观测的 temporal planner”。
- `lei2026amcats`：feasibility screening、critical resource soft reservation、time window、selective deferral 已有实例，不能独占 claim future-window preservation 本身。它没有为本文提供现成的 same-information exact continuation baseline；Related Work 应明确是 conceptual neighbor 而非声称 direct reproduction。
- `ahmad2025iotvoi`：真实 flash-flood sensing 数据上的 VoI / battery SoE / receding-horizon MPC，直接压缩了“首次联合监测与能源决策”的 claim。
- `junges2021reachability`（CAV 2021）：POMDP belief-support winning region、permissive action shield 与 incremental SAT；不再将 `∃ causal policy ∀ worlds` 或 shielding 当作本文独创。
- `ajdarow2023rsgoshield`（AAAI 2023）：资源消耗/补充与局部不可观测目标的 shielding，削弱“首次考虑 action-resource future feasibility”的泛化 claim。
- `carr2023partialshield`（AAAI 2023）：shield 与 partially observable RL controller 结合；本稿 Layer 3 若使用 learned guidance 也不能据此主张首次 shielding。

形式化文献的直接约束详见 `FORMAL-PRIOR-ART-BOUNDARY-2026-10-09.md`。三个 shielding 引用属于 prior art；目前没有 head-to-head 对照其实作 solver，不能暗示原论文已经作为比较 baseline 运行。CAV almost-sure reachability 与本稿 frozen finite-support robust completion 的数学口径保留区别。

其余条目分别由 arXiv / PMLR 当前公开记录核对；camera-ready 前若已有正式期刊/会议版本，再升级 venue metadata。

## 9. 仍需补的 bib gap

1. 若正文保留 `τ-bench / OSWorld` 的 final-state evaluator precedent，补正式 bib；
2. 若正文保留 Agentic Benchmark Checklist 的 validity 论点，补 NeurIPS 2025 正式 bib；
3. camera-ready 前检查 6G-Bench / WirelessBench / Pull-Based / UAV routing 等是否已有正式 publication record。

## 10. 引用密度建议

通信背景段落可以成簇引用：

- DTN / challenged networking：4–6 篇；
- AoI / VoI / energy / deadline：5–8 篇；
- semantic communication：4–7 篇；
- Agentic wireless：5–8 篇；
- benchmark：4–6 篇；
- decision sufficiency / active acquisition：5–7 篇。

真正 novelty contrast 反而要少而准：Pull-Based / WM-CDT / Logical Decision / Active Measuring / Wireless Context Engineering 必须逐项说清“它已经覆盖什么、Future-Choice 还剩什么”。
