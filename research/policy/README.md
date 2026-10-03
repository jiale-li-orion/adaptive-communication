# Layer 3 — Policy

本层拥有 typed decision surface 上的选择策略；它不拥有 protocol legality、authority、evidence truth 或 physical dynamics。

当前可比较 policy 包括 deterministic heuristic/search、现有 LLM Agent 与 strong ordinary baselines。未来 learned policy 的接口保持同一 action/evidence surface，可采用 GNN、offline RL 或 hybrid policy。

目标形态是 deterministic semantics + learnable decision policy：compiler 负责暴露合法、结构化、task-conditioned decision graph；policy 学习“选哪个合法 plan、查哪条 evidence、何时 wait/fallback/replan、怎样分配有限资源”。在线探索不作为灾前关键监测的默认训练假设，优先考虑 simulator trajectory 上的 offline learning / constrained learning。

`BASELINE-REGISTRY.v1.json` 记录现有 baseline/oracle 边界。任何 learned-policy claim 需要新的 Layer 1 Decision Benchmark 支撑；当前 A7–A11 不能直接外推 sample efficiency、transfer 或 policy optimality。
