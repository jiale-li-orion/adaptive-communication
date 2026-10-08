# Workstream B — ASC Transfer

## Question

future-choice feasibility 能否作为已有 Agentic / Goal-Oriented Semantic Communication 方法下方的 deterministic correctness layer，而不是只在自建 benchmark 上成立？

## Target interface

不与已有工作争“long-horizon value”或“active query”本身。接口固定为：

```text
existing ASC scheduler / semantic-value model
        ↓ candidate actions / scores
future-choice feasibility layer
        ↓ L(a), U(a), certificates / feasibility mask
legal unresolved candidates
        ↓ existing learned/value ranking
```

核心问题：**一个 scalar semantic value / expected return 很高的通信动作，是否可能删除 hard operational obligations 的最后一条 feasible continuation？**

## Candidate external formulations

优先级：

1. world-model / counterfactual long-horizon semantic-value formulation：最适合测试“expected return vs hard feasibility”；
2. goal-oriented logical decision / decision-sufficient evidence formulation：最适合测试“current decision sufficiency vs future obligation sufficiency”；
3. pull/query scheduling：最适合测试 query value 与 shared communication opportunity 的竞争。

multi-agent / heterogeneous-team ASC 只做 related-work 或 secondary transfer，不作为主 task，避免把论文主线带入 multi-agent。

### First frozen formulation: Pull-Based Query Scheduling

第一 transfer 对象冻结为 Agheli, Pappas, Kountouris, **Pull-Based Query Scheduling for Goal-Oriented Semantic Communication**（arXiv:2503.06725；IEEE TCOM 2026）。该工作把 hub query scheduling 写成 CMDP：state 包含 AoI / attribute knowledge，action 决定查询哪些 sensing agents，目标最大化长期 CPT-based GoE，同时满足 query-cost constraint。

我们只复用这个公开 formulation interface，不宣称复现其论文数值或 CPT 参数。机器探针：`code/evaluation/transfer/asc_pull_query_future_choice_probe.py`。

当前 probe 已通过一个 paired counterexample：

- 两个 state 的 current semantic scores 与 query budget 完全相同；
- 未修改的 scalar scheduler 在两者都选择当前高价值 query `A`；
- relaxed future 中 `A` 保留 future hard-goal continuation；
- tight future 中，未来 `B@t1`、`C@t2` 都是尚未生成、必须在 release 后查询的 hard goals，当前再花一次 query 会删除唯一 completion schedule；
- future-choice shield 因此只在 tight state 把 `A` 改成 `WAIT`。

这个结果只证明 **interface compatibility + scalar semantic value 与 future hard feasibility 非等价**。下一步必须进入更接近原论文 dynamics 的 finite-horizon/CMDP replay；当前不写 empirical improvement claim。

## Hard gate

至少满足一项：

- 原方法在合法高-value action 上出现 future-feasibility violation，而 feasibility layer 修复；
- 同任务质量下 feasibility layer 显著减少 unsafe/infeasible rollouts 或搜索；
- feasibility mask 与原 scalar ranking 正交，能产生原方法无法由简单阈值复现的决策差异。

如果只得到“加一个约束当然更安全”，且 ordinary constrained MPC 同样解决，则这条线只保留为外部验证，不 claim method novelty。

## Next

把当前 formulation probe 升级成原 query/AoI dynamics 上的 wrapper replay，并加入 unconstrained/value-only、ordinary constrained-DP、future-choice incremental feasibility 三组对照。只有在相同 hard-goal质量下得到额外计算/解释或 learned-policy safety 收益，才保留为 method contribution。
