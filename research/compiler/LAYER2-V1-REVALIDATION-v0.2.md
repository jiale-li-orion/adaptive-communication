# Layer-2 v1 Revalidation on Layer-1 v0.2

状态：**COMPLETE**

本文件记录 frozen Layer-2 v1 在 Layer-1 v0.2 hard decision surface 上的重验结果。目标是区分三类现象：

- **A — mechanism transfers**：v1 的通用 contract / runtime 语义在 lossless binding 后仍成立；
- **B — compatibility gap**：旧 O1–O6 实现绑定了 profile/fallback task surface，不能直接拿来评价新 benchmark；
- **C — method failure**：在 lossless binding 已经闭合后，v1 的 decision semantics 本身仍失败。

机器结果：`results/agentic/v1-revalidation-matrix-v0.2.json`。

## 1. Compatibility closure

旧 v1 as-is task compiler / registry / selector 对 Layer-1 v0.2 hard set **0/41 lossless**。原因不是 generic runtime contract 不够，而是旧实现仍围绕单 phase + profile/fallback candidate family：

- hard set 中 14 signatures 含 3 条 overlapping obligations；
- 27 signatures 含 4 条 overlapping obligations；
- 旧 registry 没有 per-obligation `WAIT / SEND_TERR / SEND_SAT / gateway_state_summary` binding；
- 旧 selector 只生成 `hold/install profile + fallback` candidate family。

evaluation-only thin binding 已关闭该兼容问题：

- 41 / 41 hard signatures；
- 2,224 reachable decision boundaries；
- 4,577 legal candidate actions；
- action roundtrip mismatch = 0；
- hidden/oracle field leakage = 0。

因此后续 C 类结果不能再归因于 task representation loss。

## 2. Frozen v1 matrix

| Mechanism | Class | v0.2 verdict |
|---|---|---|
| Task / Evidence / Context / Capability runtime contracts | A | lossless binding 后可继续使用 |
| old O1–O6 compiler / registry / selector binding | B | task-specific，as-is lossy |
| CompiledChecklist ordinary baseline | A | 新 hard surface 不再 unique-ready；41/41 初始边界均停止，无法饱和 benchmark |
| EvidenceAwareComply owner acquisition | B | capability ID 与 fallback comply path 绑定旧 task fields；41/41 新 task 触发 binding error / 无 gateway-summary query |
| ActionConditionedReference active dependency trigger | **C** | owner evidence relevance 会触发 query，但缺少 future-choice safety |
| Decision Sufficiency / candidate feasibility compiler | B | 旧 selector 的 supported/dominated 语义绑定 profile/fallback，不等价于 obligation future feasibility |
| persistent execution / typed invocation lifecycle | A | contract 层可迁移；typed action roundtrip 0 mismatch |
| CR / CF / CS model-facing ablations | B | frozen context coordinates 是 O1–O6 profile/fallback fragments，不能直接冒充 v0.2 revalidation |
| WirelessOpsAgent-style adaptation | B | old domain adapter 与 O1–O6 capability family 绑定；后续若比较属于新 policy adaptation |
| A10/A11 query-positive mechanism evidence | A | 历史机制证据继续有效，但不自动迁移成 v0.2 成功 claim |

计数：**A=4, B=5, C=1**。

## 3. Confirmed category-C failure

Frozen v1 的 ActionConditionedReference 语义是：

> unresolved dependency + active visible owner capability → 先获取 owner evidence。

Layer-1 v0.2 使 query 本身成为物理通信 action，因此该规则不再安全。对 41 个 hard signatures 的 exact minimal-resource policy prefixes 做 counterfactual：

- query-legal pre-query boundaries：808；
- query 仍保留 causal success：64；
- query 合法但会摧毁后续完成性：**744**；
- 41 / 41 signatures 的 first-legal query 都是 harmful；
- 41 / 41 exact policy 的真正 query 都晚于 first-legal query。

该结果说明 v1 能回答“这条 owner evidence 与候选行动有关”，但不能回答：

> **现在获取它以后，未来任务可行选择还剩多少？**

这就是 Layer-2 v2 的真实 method surface。它不是 compatibility gap，也不是为了制造新方法而修改 benchmark。

## 4. What v1 keeps

v2 不推翻 v1 的以下 ownership：

- Task / Evidence / Capability / Execution typed contracts；
- owner-scoped evidence acquisition；
- candidate-action Context；
- Decision Sufficiency / stop semantics 作为接口位置；
- persistent execution intent 与 lifecycle state；
- planner/model output 与 executable typed invocation 分离。

v2 需要补的是 **future-choice feasibility semantics**：EvidenceNeed、query timing、candidate feasibility 与 stop-acquisition 判断必须看到 acquisition / execution 对后续 obligation feasibility 的影响。

## 5. Claim boundary

- B 类不计入方法失败；
- A7–A11 继续是 frozen v1 的历史机制证据，除非明确在 v0.2 上重新运行，否则不改写为 v0.2 结果；
- 当前只确认一个 C 类 failure family：**acquisition timing under opportunity/resource coupling**；
- Layer-2 v2 必须在同信息、同 task quality 下改善该 failure，并单独核算 acquisition cost 与 planner compute。
