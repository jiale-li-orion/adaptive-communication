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

### Paper-structured finite-horizon replay

第二阶段已经把 toy score interface 升级成 `code/evaluation/transfer/asc_pull_query_cmdp_replay.py`：保留 Pull-Based formulation 的核心结构——per-attribute AoI、每槽最多 query 一个 attribute 或 wait、成功 query reset AoI / 未刷新 AoI 增长、有限 query-cost budget，以及 freshness/usefulness 单调组合的 GoE。为避免伪造论文数值，当前使用 deterministic-success 子情形、finite horizon 和 `sum usefulness/AoI` 这一合法 GoE subclass；不复现 CPT 参数或论文曲线。

hard operational query goals 明确标为 transfer extension。结果：

- value-only GoE DP：`WAIT → A → WAIT → A → WAIT`；
- relaxed future goal 中该 policy 仍 hard-feasible；
- current AoI/usefulness/query budget 完全不变，只把 future goals 改成 `B@t1`、`C@t2` 后，value-only policy 违反 hard goals；
- generic hard-goal exact DP：`WAIT → B → C → WAIT → WAIT`；
- future-choice shield + 同一 GoE objective 得到**完全相同 constrained policy 与 value**；
- generic exact 访问 `30` states、评估 `29` actions；shielded exact 访问 `6` states、评估 `14` actions，提前剪掉 `9` 个已破坏 future choice 的动作。

这个结果证明 transfer correctness 与 search headroom，但仍不等于 Layer-2 novelty：当前 hard-goal extension 是 unit-demand deadline scheduling，ordinary scheduling-aware constrained DP 也能使用同一个 matching certificate。因此 B 线下一步必须进入**共享资源 / dynamic goal revision / delayed observation**的 formulation，才能测试完整 conditional frontier 是否有不可被普通 unit-job certificate 吸收的增量。

## Hard gate

至少满足一项：

- 原方法在合法高-value action 上出现 future-feasibility violation，而 feasibility layer 修复；
- 同任务质量下 feasibility layer 显著减少 unsafe/infeasible rollouts 或搜索；
- feasibility mask 与原 scalar ranking 正交，能产生原方法无法由简单阈值复现的决策差异。

如果只得到“加一个约束当然更安全”，且 ordinary constrained MPC 同样解决，则这条线只保留为外部验证，不 claim method novelty。

## Next

当前 query/AoI replay、conditional-obligation family、shared-opportunity family 与 multi-observation persistent-domain reuse 均已完成。下一步不再扩大静态 K/D，而是让 active branch 内出现 **time/resource/pending-feedback event**，比较 fresh exact、ordinary persistent exact、branch-aware flow/receding、dependency-cache exact、persistent conditional frontier；目标是验证 component-level invalidation，而不是整个 branch certificate 级复用。只有这一强 ladder 下仍有增量，才升级为最终 method contribution。

### Conditional frontier probe

第三阶段开始测试真正区别于静态 resource reservation 的对象：**未来 obligation 取决于尚未到达的语义 observation**。

`code/evaluation/transfer/asc_pull_query_conditional_frontier_probe.py` 构造两个初始不可区分 world，共享 query budget=2：

- `QUERY_H` 在 t=0 消耗 1 次 query，并揭示后续需要 `B` 还是 `C`；
- H=0 分支在 t=1 只需 `QUERY_B`；
- H=1 分支在 t=1 只需 `QUERY_C`。

exact causal 结果：

- `QUERY_H`: `L=1,U=1`，存在 observation-conditioned non-anticipative completion policy；
- `WAIT / QUERY_B / QUERY_C`: `L=0,U=1`，物理上并非必死，但当前 history 下无法同时覆盖两个 aliased worlds；
- 静态 worst-case union reserve 会把未来 `{B,C}` 同时计入，认为 `QUERY_H` 后预算 1 < 2，因此错误拒绝一个真实可行的 action；
- conditional frontier 按 observation 分支保留 `H=0→B`、`H=1→C`，避免这个 false negative。

这条结果第一次真正击中当前 Layer-2 的 representation insight：**future choices 必须按未来 observation 条件化，而不能把所有可能 obligation 静态并集化。**

边界仍然严格：exact belief-space AND-OR solver 同样能表示该结构，因此当前证明的是 representation necessity / static-reserve failure，不是 wall-time 或算法 novelty。下一步必须在更大的 shared-resource / delayed-feedback formulation 上比较 incremental conditional frontier 与 strong exact/receding solver。

### Scaling boundary: pure query-chain family

`code/evaluation/transfer/asc_pull_query_conditional_family.py` 把上述结构扩成 `K∈{1,2,4,8,16}` hidden branches × `D∈{1,2,3,4}` branch-specific future query goals。20/20 cells 的 conditional action frontier 与 fresh/persistent exact 完全一致；K>1 的 16/16 cells 都触发 static-union false negative。

但这组结果同时给出一个重要负边界：纯 unit-query chain 太简单。比如 `K=16,D=4`：fresh exact 130 expansions、persistent exact 66、conditional branch certificate 64 steps。strong persistent exact 已经近似线性，因此继续扩大 K/D 只会重复“static union 错”这一 representation 结论，不会形成有说服力的算法 headroom。

### Shared-opportunity conditional frontier

因此 B 继续引入真正的 Layer-2 conflict object，但仍保持 Pull-Based query interface：`QUERY_H` 揭示一个 mutually-exclusive future branch；每个 branch 激活 D 个 hard operational reports，它们共享 `D-1` 个 terrestrial opportunities + `1` 个 backup unit。

实现：`code/evaluation/transfer/asc_pull_query_shared_opportunity_frontier.py`。branch 内部不另写 matching 算法，直接复用仓库冻结的 `ConditionalFeasibilityFrontier` max-flow/min-cut conflict certificate；小 cell 再由 independent exact scenario-tree solver 对账。

当前网格：`K∈{1,2,4,8,16,32}` × `D∈{2,4,8}`，共 18 cells。

- K>1 的 **15/15** cells：query observation 后每个 branch exact-solvable；
- K>1 的 **15/15** cells：static union reserve false-negative；
- 每个真实 branch 的 minimum backup requirement 始终是 **1**；
- static union 把 mutually-exclusive future obligations 同时计入，最坏把 minimum backup 放大到 **249** (`K=32,D=8`)；
- `D=8` 时 exact branch solver 每 branch 约 778 memo states；同一 branch 的 max-flow/min-cut graph 只有 71 个 forward edges。聚合到 `K=32,D=8` 是 24,896 exact memo states vs 2,272 deterministic flow-graph edges，约 **10.96×** search-vs-structure work proxy。

这一步比纯 query chain 更接近当前 method insight：future obligations 不仅 observation-conditioned，而且在每个 branch 内存在共享 future opportunities / Hall conflict。

边界：memo-state count 与 flow-edge count 不是同一 CPU 操作，10.96× 只能作为 deterministic work proxy，不能写成 runtime speedup。ordinary branch-aware max-flow planner 也是强 baseline；真正的方法增量仍需来自 **多次 observation / delayed feedback 下 conditional component 的 persistent reuse 与 event-local invalidation**，而不是一次 query 后重新建 branch flow。

### Dynamic observation-domain reuse

`code/evaluation/transfer/asc_pull_query_dynamic_frontier_reuse.py` 已把上述下一门补上。设 `K=2^L` mutually-exclusive branches，连续 L 次 semantic query 每次揭示一个 branch bit；每个 branch 都持有固定的 D=8 shared-opportunity conflict graph。query observation 只缩小 active support，不修改该 branch 的 obligation/opportunity/resource graph。

比较两种同样正确的 branch-aware planner：

1. **fresh flow**：每个 observation node 都重新构造 active support 中全部 branch conflict frontiers；
2. **persistent conditional domain**：root 对每个 branch 构一次 certificate，后续 observation 仅筛 active domain，未变化 certificate 直接复用。

完整 non-anticipative observation tree 的结果：

- L=1 / K=2：persistent build ratio = `1/2`；
- L=2 / K=4：`1/3`；
- ...
- L=5 / K=32：fresh 共 **192** 次 branch-frontier builds，persistent **32** 次，build ratio **1/6**，省 **160** 次结构重建。

最后再施加 resource event `backup budget 1→0`：只有 realized active branch 的 certificate 跨越 validity domain 并失效；其余 31 个 mutually-exclusive inactive branch 不需要被重建。这一检查把“query observation support narrowing”和“resource-domain invalidation”明确分开。

这一结果已经落到当前 Layer-2 方法对象本身：**conditional validity domain 不是只帮助一次 query decision，它允许证书跨多次 observation 保持，并只在依赖/资源域真正变化时局部失效。**

边界：当前 branch graph 在 observation-only 阶段故意保持不变，因此 `1/(L+1)` 是干净的 reuse upper case；下一更强 gate 是在 active branch 内同时发生 time/resource/pending-feedback event，只让部分 conflict components 失效，并与 ordinary dependency-cache / persistent exact 做同接口 comparison。
