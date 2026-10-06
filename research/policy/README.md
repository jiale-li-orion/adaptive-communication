# Layer 3 — Policy

Layer 3 持有 **frozen Layer-2 decision surface 上的选择与搜索顺序**。当前由于 Layer 1 benchmark hard-mechanism coverage 重开，本层处于 **PAUSED** 状态。

输入由 Layer 2 提供：合法 candidate actions、lawful current context、`L/U` 状态、evidence/resource/obligation structure，以及 unresolved set：

```text
A_u(s) = { a | L(s,a)=0, U(s,a)=1 }
```

Layer 3 输出 action ordering / search guidance。Protocol legality、authority、evidence truth、L/U 语义、exact fallback 与 physical dynamics 继续由 Layer 2 / substrate 持有。

## Current disposition

2026-10-06 起，Layer 3 不再是当前主工程。此前 v0.1 **learning-guided exact search** 保留为 negative/history：

```text
Layer-1 instance
    -> Layer-2 semantic compilation
    -> deterministic pruning
    -> Layer-3 learned ordering on unresolved actions
    -> exact exploration / proof
```

该历史线的训练信号曾按两个层级组织：

1. exact-feasible unresolved action 优先于 exact-infeasible action；
2. 同一 feasibility 类别内，exact downstream proof/search cost 更低的 action 优先。

学习器只影响 unresolved-action 的探索顺序。最终 action-feasibility frontier 仍由 frozen Layer-2 + exact reference 验证。当前不继续扩展该方法，也不允许它反向定义 Layer-1 hard cases。

## Historical v0.1 result

当前 train/dev rank dataset 已完成：train 16 signatures / 1,191 unresolved boundaries / 1,722 action records；dev 18 signatures / 3,825 boundaries / 5,169 action records。历史 test split 未进入训练或选模。

第一版 pairwise linear ranker 已完成 full-dev audit：

- action-feasibility frontier：**1,053 / 1,053 prefixes match**；
- frozen Layer-2 adapter：21,432 expansions；
- learned ordering：21,354 expansions（ratio 0.99636）；
- ordinary persistent exact：51,264 expansions；
- learned wall time 约为 ordinary persistent exact 的 1.55×，且包含 scorer inference cost。

当前 disposition：**correctness PASS，search reduction 很小，systems wall-time negative。** 这组结果只承担 v0.1 baseline / kill signal，不再驱动当前研究方向。

机器入口：`results/agentic/layer3-rank-dataset-{train,dev}.json`、`layer3-linear-ranker-train.json`、`layer3-learned-ranking-dev.json`。

## Restart gate

Layer 3 只有在下面条件全部满足后才允许重新启动：

1. Layer-1 environment / generation contract 冻结；
2. hard mechanism 不再坍缩到单一 family；
3. ordinary fixed/open-loop/passive/query/VoI/depth-k/receding baselines 完整红队；
4. 新 structural-generalization cohort 在 method freeze 前 preregister；
5. Layer-3 目标首先对应 task completion / delivery，而不是只优化 exact solver 的内部 search cost。

## Historical evaluation contract

当前优先级固定为：

1. **wall time**：包含模型推理开销；
2. **exact search expansions**：验证 search-space reduction；
3. **frontier correctness**：learned ordering 必须保持 frozen action-feasibility frontier；
4. **ranking accuracy**：只作为诊断指标。

Ordinary persistent exact 是主要 systems control。若 learned ordering 减少 expansions 但 wall time 变差，结果按真实 systems trade-off 报告。

## Split discipline

- train：用于构造 rank data 与拟合；
- dev：用于方法选择、correctness 和 systems evaluation；
- 历史 7-signature test：已暴露，当前只作 regression；
- 新 structural-generalization claim：需要新的 preregistered holdout。

`BASELINE-REGISTRY.v1.json` 继续登记历史 deterministic / LLM / oracle 边界。A7–A11 保留为 runtime/model provenance，不承担当前 Layer-3 learning claim。
