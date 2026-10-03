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

## Current disposition

`CONFORMANCE-SPLIT.v1.json` 与 `CONFORMANCE-ROBUSTNESS-MATRIX.v1.json` 保留 O1–O6 的 source-period、scope、owner、outage、scale 等坐标，用于 Runtime/physics/conformance 回归。A7 的 123/123 唯一 ready supported plan 说明这些开发状态大量已由 compiler 闭合，因此它们不再代表完整 Decision Benchmark。

本地 source/task lineage 位于 `../../local_research/current/benchmark/`；其中旧 `task-challenge-pivot`、scenario-interface bridge、source audits 与 pain-point extraction 是本层的 provenance，不作为新文件重复发明。


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
