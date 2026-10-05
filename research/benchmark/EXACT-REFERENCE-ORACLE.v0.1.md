# Exact Reference Oracle v0.1

状态：**CURRENT / implementation + full-universe exact labeling complete, pre-admission**
上游：`DYNAMIC-WORLD-MATERIALIZATION.v0.1.md`、`CAUSAL-EVIDENCE-PROCESS.v0.1.md`
实现：`code/evaluation/benchmark/exact_reference_oracle_v0_1.py`
审计：`results/benchmark/layer1-exact-reference-audit-v0.1.json`

## 1. Reference boundary

Layer 1 同时保留四种信息边界：

| Reference | 已知信息 | 用途 |
|---|---|---|
| `HINDSIGHT_PHYSICAL_FEASIBILITY` | 单个 frozen world 的完整外生未来 | 物理可行性上界 |
| `FULL_CURRENT_STATE` | 当前真实状态全部可见；未来 service transition 仍按声明 support 分支 | 隐藏当前状态的代价 |
| `OBSERVATION_MATCHED_EXACT` | 与被评策略相同的 causal history、query/passive/probe 能力与资源 | 可实现 exact 参照 |
| `OBSERVATION_MATCHED_NO_PAID_QUERY` | 同上，但禁止额外 owner query；保留 passive ACK、自然反馈与 normal send-as-probe | 独立付费取证的价值 |

`FULL_CURRENT_STATE` 不逐 world 偷看 future schedule。dynamic world materializer 已把 physical future support 与 evidence regime 解耦；solver 在每个决策时刻免费暴露完整**当前**状态，同时对尚未发生的 terrestrial transition 继续做 AND branch。逐 realized world 单独求解只属于 hindsight reference。

所有 online reference 满足 non-anticipativity；query、SEND、gateway receipt、final ACK 与 shared resource 使用同一 causal execution semantics。四个 reference 都只做 hard-constraint feasibility，不使用 scalar reward。

## 2. Physical full scan

58,752 个 materialized bundles 已全部运行 hindsight physical matching：

```text
ALL_WORLD_SOLVABLE       57,528
MIXED_WORLD_SOLVABILITY   1,224
NO_WORLD_SOLVABLE             0

physical worlds:
  SOLVABLE   145,332
  INFEASIBLE   1,548
```

29,376 个 `VALIDITY_PENDING` bundles 全部属于 `ALL_WORLD_SOLVABLE`。1,224 个 mixed bundle 全部来自 `MONOTONE_RECOVERY_NEGATIVE` regression 区域，因此当前 hard-candidate 主体没有被 generator-level physical infeasibility 污染。

这一步只回答“每个 declared future realization 单独看是否存在物理成功轨迹”，不回答是否存在共同 causal policy。

## 3. 216-cell structural exact audit

为了先检查 generator 是否整体退化，当前对 `VALIDITY_PENDING` universe 做 deterministic structural diagnostic。cell 由：

```text
service process
× evidence regime
× overlap count
× resource headroom
× recovery regime
```

构成。`FINITE_CROSSING_WINDOWS` 与 `MULTI_WINDOW_DYNAMIC` 共形成 216 个结构 cell。每个 cell 只取 task/geometry 坐标中 stable hash 最小的 representative；该规则与模型表现无关，也不是 benchmark split 或 admission filter。

在 `max_memo_nodes = 200,000` 下全部 216 cells 精确收敛：

```text
P  = all-world physical feasible            216
FC = full-current-state causal feasible     216
F  = observation-matched exact feasible     204
N  = no-paid-query exact feasible           189

NO_PAID_QUERY_REQUIRED                      189
PAID_EVIDENCE_REQUIRED                       15
INFORMATION_INFEASIBLE                       12
SEARCH_LIMIT                                  0
```

结构 diagnostic 上：

```text
Delta_info = (|F| - |N|) / |F| = 15 / 204 ≈ 7.35%
```

这个比例不代表最终 benchmark case 分布。它说明当前 generator 没有整体退化成 common-safe/no-query；同时 genuine paid EvidenceNeed 只占结构空间的一部分。后续 release 不能筛成“全是 query-positive”，`NO_PAID_QUERY_REQUIRED`、`INFORMATION_INFEASIBLE`、easy 与 regression cells 都要按 gate 正常保留、降级或分流。

15 个 paid-evidence cells 主要出现在 `MULTI_WINDOW_DYNAMIC + GATEWAY_SUMMARY_QUERY`，`FINITE_CROSSING_WINDOWS + GATEWAY_SUMMARY_QUERY` 也出现 2 个；它们来自正式 compositional generator，不依赖 receipt-race fixture。

## 4. Computation pressure

216-cell audit 的 exact search：

```text
mean max memo nodes       1,492.5
max observed memo nodes 118,660
search-limit cells             0
```

较长 cadence、4-way overlap、tight resource 的 no-query reference 已出现十万级 memo state。generic exact 仍能完成这些 representatives，所以 computation pressure 可以成为后续 baseline/算法比较对象；人工 search limit 不能被记成 `INFORMATION_INFEASIBLE`。

action-time lattice 只保留 release/deadline、service-window boundary 与异步事件到达。piecewise-constant service interval 内没有新的 release/state transition；earlier feasible action 对纯 feasibility 弱支配更晚同类行动，因此删除 midpoint/end-minus-one 只移除重复搜索时刻，不改变信息边界。

## 5. Execution semantics 与 V9 core

exact solver 已与 causal evidence contract 对齐：accepted `SEND_TERR` 先产生 gateway receipt，再产生 final ACK；gateway receipt 不提前完成 obligation；query response 保留真实 sample time；satellite completion timing 由 shared causal-process timing contract 持有；execution witness 可以交给独立 evaluator 重放。

`execution_trace_evaluator_v0_1.py` 当前已通过 V9 core mutation regression：合法 oracle witness 通过；authority violation、虚构 service window、protected-subject corruption、漏执行以及 source deadline violation 均失败。它还不是完整 V9 release audit。

## 6. Current boundary

full-universe exact labels 已经完成。58,752 recipes 通过 9,216 个 solver-equivalent signatures 去重求解，再投影回 recipe universe：

```text
signature labels:
  NO_PAID_QUERY_REQUIRED    8,312
  PAID_EVIDENCE_REQUIRED      416
  INFORMATION_INFEASIBLE      248
  MIXED_WORLD_SOLVABILITY     240

projected recipes:
  NO_PAID_QUERY_REQUIRED   53,424
  PAID_EVIDENCE_REQUIRED    2,562
  INFORMATION_INFEASIBLE    1,542
  MIXED_WORLD_SOLVABILITY   1,224

VALIDITY_PENDING only:
  NO_PAID_QUERY_REQUIRED   25,272
  PAID_EVIDENCE_REQUIRED    2,562
  INFORMATION_INFEASIBLE    1,542
```

signature digest：`160c0afa17291d4cbeaa5f2bc9fb4d86454016c14a3a696a89218ee6042b8abb`。compact authority 见 `results/benchmark/layer1-exact-label-manifest-v0.1.json`；大 JSONL 是 deterministic generated artifact，保留在 `local_research`，可以由 materializer 重建。

这些 classification 只描述 exact information feasibility。**2,562 不是 hard benchmark count。** 以下工作仍未完成：

1. V0–V7 filter engine 已有 pilot implementation，但尚未获得 full-universe release authority；
2. V3 当前采用 conservative blind-open-loop witness 排除明显 common-safe degeneration，最终 V3/V4 仍需结合完整 policy/plan-set witness 审核；
3. V8 第一层 ordinary compositional baseline 已通过测试，但必须按 placement 分账：15 个 stratified paid-evidence cells 全部存活于 same-information ordinary baselines，同时 15/15 可由 gateway-local EDF/reserve 这一 deployment alternative 完成；全 216 个结构 cells 中 100 个被 same-information shortcut 覆盖、116 个仍存活；
4. V9 已有 evaluator core regression，完整 release audit 尚未完成；
5. V8 仍需 shallow rule combiner、真正 depth-k belief planner、receding horizon、普通 dependency/cache 优化与 fair generic exact/incremental AND–OR；
6. structure-aware split、near-duplicate audit、Q0–Q12 尚未开始。

gateway-local EDF/reserve 改变 planner placement，并使用 owner-local current state。它是必须报告的强 deployment baseline，但不能与同 placement / 同信息 ordinary policy 混为一个 `SHORTCUT_SOLVED` 判据。它能够否定“center remote acquisition 在所有部署位置都不可替代”这类过强 claim；是否存在 algorithm/computation gap 仍要由后续同条件 V8 ladder 决定。

当前工程阶段固定为：

```text
V0_V9_AUTOMATIC_FILTERING
```

任何 V0–V9 之前的数量都不能写成 benchmark case count。
