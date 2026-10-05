# Layer 1 — Source-grounded Emergency Communication Benchmark

本层拥有“现实山区灾前需求如何变成可评测通信决策任务”。它不从现有 tool/capability 反推题目。

## Construction contract

1. `Original requirement`：山区供电不足、通信间歇中断导致节点失联/数据无法回传，目标是灾前低功耗持续稳定监测。
2. `Source grounding`：field deployment、standard、government/industry material 分别证明 operational need、能力和约束；证据等级与未知项保留。
3. `Operational corpus`：先逐条抽取 obligation、authority、observation、action、constraint、transition、outcome，不从 simulator 反推题目。
4. `Taxonomy`：由 corpus 聚类产生 Operational Family，并与 Agentic Capability / Hardness / Operating Regime 正交。
5. `Historical semantic dedupe`：candidate 产生后才查旧 repo；语义等价直接继承旧 verdict，不重复跑实验。
6. `Task specification`：给 goal、hard constraints、resource budgets、authority/effect envelope、time window 与 provenance。
7. `Simulator mapping`：外部 source 支持而 simulator 缺失的 state/action 记为 SIMULATOR_GAP，不因当前跑不了而删题。
8. `Case generator + oracle`：从 source-backed profiles 生成大量 case，并构建 external oracle。
9. `Validity + hardness`：完成 shortcut、ordinary baseline、held-out 与 non-toy coverage 审计后才进入 policy evaluation。

## Validity / hardness gate

一个 Decision Benchmark task 至少要能回答以下问题：来源是否支持这个 operational need；是否存在真实选择而非唯一已知写入；观测/不确定性是否可能改变选择；资源或时序约束是否实际 binding；不同合法策略是否产生 materially different physical outcomes；强 ordinary mechanism 是否仍留下需要决策的空间。增加节点数、seed 或窗口数量本身不增加 decision richness。

## Current authority and disposition

**当前 Layer 1 全局状态只由 [LAYER1-AUTHORITY.md](LAYER1-AUTHORITY.md) 拥有。** 本 README 不再以某个 generator/receipt 版本代表全局进度。

当前一级 taxonomy：

- **T1 Monitoring Information Continuity** — MAIN；
- **T2 Warning Delivery & Response Handoff** — boundary extension，当前 actor-chain environment 为 `SIMULATOR_GAP`。

O1–O6 是历史 T1 operational regime/conformance assets；完整 task surface 与 closure 见 [TASK-COVERAGE-CLOSURE.v0.1.md](TASK-COVERAGE-CLOSURE.v0.1.md) 和 [TASK-SURFACE-REGISTRY.v0.1.json](TASK-SURFACE-REGISTRY.v0.1.json)。

Q11 source review 于 2026-10-05 发现 DB44/T 2457-2024 profile 的 pre-release extraction bug：旧 cadence 对应表 15 地裂缝，而项目原始场景与 intended T1 authority 是山区滑坡。profile 已改为 `hazard_type=landslide`，采用 §9.2.2.2 表 11；随后 retry legality 也修正为“未知是否已交付 ≠ 禁止重试”。`v0.2-retry-legality` 已完成 exact→V0–V9→split→public-test 全链重算。当前 exact 为 8,064 solver signatures；V8 最终保留 41 hard signatures / 174 recipes；split hard train/dev/test signatures = 16/18/7；public test = 3,804 cases。旧 LLM/Q-gate lineage 暂按 historical result 处理，LLM rerun deferred，Q11 需基于 v0.2 重建。机器状态见 [LAYER1-CURRENT-STATE.v0.1.json](LAYER1-CURRENT-STATE.v0.1.json)。

v0.1–v0.5、receipt-race、receipt-chain、joint query–satellite Pareto 和 continuation frontier 继续保留，但它们的角色是 generator/mechanism regression、exact-reference 与 shortcut audit。尤其 188-cell receipt grid **不是 benchmark case count**；当前普通 reserve/fixed-read/wait-ACK family 仍覆盖 frozen receipt-chain 的 exact cost frontier。

当前唯一主工程：

    DB44 landslide source correction                 [DONE]
    → retry legality correction                      [DONE v0.2]
    → exact / V0–V9 regeneration                     [DONE v0.2]
    → held-out split / public test                    [DONE v0.2]
    → frozen-split LLM baseline                       [DEFERRED]
    → rebuild Q11 package and Q0–Q12                  [PENDING]
    → frozen BENCHMARK_ADMIT release

除 correctness/source/simulator blocker 外，默认不继续扩局部 receipt fixture，不先训练 RL/LLM，不让 Layer 2/3 方法反向塑造 Layer 1 分布。


## Construction authority

Formal benchmark construction, admission, validity, hardness, non-toy coverage, baseline and release rules are owned by [BENCHMARK-CONSTRUCTION-PROTOCOL.v0.1.md](BENCHMARK-CONSTRUCTION-PROTOCOL.v0.1.md). The protocol includes the Family Identity Test: Family boundaries are determined by protected subject, completion predicate, authority chain and lifecycle scope; warning level, outage/reconnect, path choice, cache/retransmission and other capabilities/regimes do not automatically create new Families.

Large-scale case generation, oracle construction, automatic validity filtering, provenance classes and held-out split are owned by [CASE-GENERATION-PROTOCOL.v0.1.md](CASE-GENERATION-PROTOCOL.v0.1.md). Frozen case artifacts follow [CASE-SCHEMA.v0.1.json](CASE-SCHEMA.v0.1.json). Candidate-family records follow [CANDIDATE-SCHEMA.v0.1.json](CANDIDATE-SCHEMA.v0.1.json). Status now separates SOURCE_GAP / SOURCE_SUPPORTED / SIMULATOR_GAP / HISTORICALLY_CLOSED / ADMISSION_READY / BENCHMARK_ADMIT.

Construction order is fixed:

    external operational corpus
    → canonical operational objects
    → provisional taxonomy
    → candidate family + source validation
    → historical semantic dedupe
    → state/action/transition/oracle contract
    → simulator mapping / explicit gaps
    → case generator
    → task/outcome validity
    → hardness + non-toy coverage
