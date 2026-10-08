# Benchmark Paper Positioning

状态：**CURRENT PAPER-FRAMING AUTHORITY / benchmark validity 与 method headroom 解耦**
日期：2026-10-09

本文件只回答一个问题：如果 Layer 1 独立作为 benchmark contribution，论文到底应该怎样成立？它不修改 source/task semantics，不新增 generator axis，也不替 Layer 2 制造 hard case。

## 1. 结论

当前最重要的修正是：

> **benchmark validity、interactive decision richness、future-choice method headroom 是三个不同层级，不能继续绑成同一个 admission gate。**

一个 task 可以是 source-grounded、可复现、执行式可判分、覆盖现实 workflow，同时被 ordinary deterministic planner 很容易解决。它仍然可以作为 benchmark 的 sanity / coverage / attribution 资产；它只是不能承担“Agentic hardness”或“future-choice 方法必要性”的 claim。

反过来，只有一小部分 structural stress case 需要承担 Layer-2 方法主张。

## 2. 同类 benchmark paper 真正靠什么成立

### 2.1 6G-Bench：taxonomy + construction + validation 本身就是贡献

6G-Bench 从 3GPP、IETF、ETSI、ITU-T、O-RAN 等标准化活动抽取 30 类 decision task，再从 113,475 个 episode/scenario 构造 10,000 个候选问题，经自动检查与专家人工验证保留 3,722 个高置信 evaluation items。

它的 benchmark contribution 主要来自：

1. 外部标准驱动的 task taxonomy；
2. scenario → semantic state/action → oracle decision → item 的 construction pipeline；
3. automated filtering + expert review；
4. 大模型谱系与 task/category-level failure analysis。

它并不要求每个 task 都对应作者自己的新算法 headroom。

参考：`https://arxiv.org/abs/2602.08675`

### 2.2 WirelessBench：一个 benchmark 可以合法拥有多个 cognitive tier

WirelessBench 把评测分成三层：domain knowledge reasoning、intent-driven resource allocation、proactive multi-step mobility decision；同时强调 tolerance-aware scoring、tool-necessary tasks 与可诊断 trajectory。

对本项目最重要的启发不是具体无线题型，而是：

> **同一 benchmark 不需要把所有 item 强行包装成最高难度 Agent task。**

较低层任务可以承担基础 construct / unit / tool / conformance 覆盖；真正的 multi-step interactive subset 再承担更强 claim。

参考：`https://arxiv.org/abs/2603.21251`

### 2.3 DORA：operational corpus + expert-authored tasks + replayable trajectories

DORA 使用 45 个真实灾害事件，构造 515 个 expert-authored operational tasks，并给出 3,500 个 expert-verified replayable tool-call steps。它的主要价值来自真实灾害工作流、异构数据与 end-to-end operational composition，而不是给每个任务求 exact optimal policy。

对本项目的直接启发：

- “真实来源定义 task，具体 episode 由 benchmark designer 构造”完全成立；
- source / event grounding、task authoring、trajectory/evaluator audit 可以分别报告；
- trajectory length / composition depth 可以作为 diagnostic axis，但不是 task legitimacy 的来源。

参考：`https://arxiv.org/abs/2605.11633`

### 2.4 τ-bench / OSWorld：final state / execution evaluator 比唯一 gold trajectory 更重要

τ-bench 用动态用户交互、domain policy 与 API tools，最终比较 database state 与 annotated goal state；OSWorld 为每个真实 computer-use task 提供可复现 initial state 与 execution-based evaluation script。

这两类 benchmark 共同强调：

1. 环境真实执行；
2. success 由终态/可执行 predicate 判定；
3. 允许多条合法 trajectory；
4. 初始化、环境和 evaluator 可复现；
5. stochastic agent 要看 reliability，而不只看单次 success。

参考：

- `https://arxiv.org/abs/2406.12045`
- `https://arxiv.org/abs/2404.07972`

### 2.5 Agentic Benchmark Checklist：validity flaw 的影响可以大于模型差异

NeurIPS 2025 的 Agentic Benchmark Checklist 说明 task setup / reward / evaluator flaw 可以把 agent performance 严重高估或低估；benchmark paper 的首要责任是 task validity、outcome validity 与 reporting discipline。

这恰好支持本项目过去几轮主动撤回：retry legality、v0.6 blind shortcut、placement、gateway ownership 等 correctness 修复应该被写成 benchmark methodology strength，而不是“项目反复失败”的尴尬历史。

参考：`https://proceedings.neurips.cc/paper_files/paper/2025/hash/f316275b44ee2de533102913828a8107-Abstract-Datasets_and_Benchmarks_Track.html`

## 3. Layer 1 的 release strata

从现在开始，Layer 1 不再要求所有正式资产同时满足最高级 Agentic hardness。

### Track A — Operational / Conformance

目标：证明 source-grounded task contract、physical lifecycle 和 evaluator 正确。

允许：

- deterministic / ordinary-rule solved；
- fixed policy 可完成；
- 单轮可约化；
- known easy / negative regression。

必须满足：source validity、task validity、outcome/evaluator validity、reproducibility、coverage 与 no-exploit。

用途：sanity、coverage、regression、attribution；**不承担 Agentic / Layer-2 claim**。

### Track B — Interactive Decision

目标：评测动作执行后会改变环境/义务状态的 sequential communication decision。

额外要求：

- multiple legal actions；
- action mutates causal environment；
- observation / feedback 在 episode 内推进；
- final obligation state 用 execution evaluator 判分。

ordinary planner 可以表现很好；baseline saturation 本身是一条 benchmark finding，不导致 task 失效。

### Track C — Future-Choice Stress

目标：专门承担 future-choice / Agentic hardness / Layer-2 方法研究。

额外要求：

- partial observability / alias history；
- observation-conditioned continuation；
- binding shared resource / opportunity；
- no common safe open-loop shortcut；
- strong ordinary baseline 未饱和；
- exact / counterfactual reference 可定位 first irreversible loss；
- held-out structural generalization。

只有 Track C 可以用来写“future-choice representation / method is necessary”。

## 4. 对当前 A 线的重新判断

### 可以留下

- T1 source-grounded monitoring continuity：属于 benchmark 主 family；
- warning/task revision、energy、cache、outage/recovery、gateway forwarding：作为 source-backed lifecycle/case axes；
- corrected gateway placement/data-lifecycle：属于 outcome validity infrastructure；
- S7 persistent-energy witness：可以作为 Track B mechanism / failure-analysis case，即使 `resource_guard` 能解决；
- shared-backup preflight negative：可以作为 ordinary mechanism saturation finding；
- T2 Yining/Baoshan：source-valid candidate extension，可以进入 taxonomy / SIMULATOR_GAP ledger，即使当前不具备 future-choice hardness。

### 不再要求

- 每个 T1/T2 family 都必须有 paid EvidenceNeed；
- 每个 benchmark case 都必须击败 EDF / maxcov / ResourceGate；
- 所有 source-grounded task 都必须进入 Layer-2 hard split；
- exact optimal policy 必须覆盖全部大规模 release case。Exact oracle 可以对可解 bounded subset / diagnostic strata 提供更强 reference；大规模 execution evaluator 才是 release 核心。

### 仍然必须补

1. **Task corpus coverage**：family / source / operating regime 是否够代表原始灾前需求；
2. **Environment contract**：T1 current environment 哪些 lifecycle object 真正 release-ready；
3. **Outcome evaluator**：final obligation state、deadline、collection/delivery/recovery predicate 的 mutation test；
4. **Human/source audit**：独立抽样核 source → obligation → evaluator；
5. **Model/policy spectrum**：至少 rule / MPC-search / LLM-agent / learned policy 中若干有代表性的 baseline；
6. **Interactive challenge subset**：不要求 Layer2 赢，但至少要有一部分 case 能区分 open-loop / interactive / perfect-observation policy；
7. **Maintenance/release artifact**：immutable manifest、version、known flaws、replay entry。

## 5. Paper story

如果 A 独立成 benchmark paper，主故事应收成：

> Existing wireless/ASC benchmarks increasingly cover telecom knowledge, resource allocation, tools and dynamic network control, but operational emergency-communication evaluation still lacks a benchmark that traces field/standard requirements into executable long-horizon communication obligations and scores agents by causal task outcomes under intermittent connectivity and persistent resource state.

贡献顺序：

1. source-grounded operational taxonomy；
2. executable communication environment / lifecycle contract；
3. obligation-state evaluator + bounded exact references；
4. three-track benchmark suite；
5. baseline/model study + failure taxonomy；
6. source/evaluator audit + reproducible release。

Layer 2 future-choice method 若最终成熟，可以作为 strong baseline / companion method；**它不再是 A 成立的前置条件。**
