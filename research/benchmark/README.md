# Layer 1 — Source-grounded Emergency Communication Benchmark

本层拥有“现实山区灾前需求如何变成可评测通信决策任务”。它不从现有 tool/capability 反推题目。

## Construction contract

1. `Original requirement`：山区供电不足、通信间歇中断导致节点失联/数据无法回传，目标是灾前低功耗持续稳定监测。
2. `Source grounding`：field deployment、standard、government/industry material 分别证明 operational need、能力和约束；证据等级与未知项保留。
3. `Operational need`：归纳真实运行目标，不先固定动作答案。
4. `Task specification`：给 goal、hard constraints、resource budgets、authority/effect envelope、time window 与 provenance。
5. `Frozen physical scenario`：在 shared substrate 上实例化，不为算法调 physics。
6. `Policy envelope/replay`：先用 deterministic/search/ordinary baselines 确认存在多个合法且结果不同的策略。
7. `Validity + hardness`：通过后才进入 Agent/learned-policy evaluation。

## Validity / hardness gate

一个 Decision Benchmark task 至少要能回答以下问题：来源是否支持这个 operational need；是否存在真实选择而非唯一已知写入；观测/不确定性是否可能改变选择；资源或时序约束是否实际 binding；不同合法策略是否产生 materially different physical outcomes；强 ordinary mechanism 是否仍留下需要决策的空间。增加节点数、seed 或窗口数量本身不增加 decision richness。

## Current disposition

`CONFORMANCE-SPLIT.v1.json` 与 `CONFORMANCE-ROBUSTNESS-MATRIX.v1.json` 保留 O1–O6 的 source-period、scope、owner、outage、scale 等坐标，用于 Runtime/physics/conformance 回归。A7 的 123/123 唯一 ready supported plan 说明这些开发状态大量已由 compiler 闭合，因此它们不再代表完整 Decision Benchmark。

本地 source/task lineage 位于 `../../local_research/benchmark-grounding/`；其中旧 `task-challenge-pivot`、scenario-interface bridge、source audits 与 pain-point extraction 是本层的 provenance，不作为新文件重复发明。
