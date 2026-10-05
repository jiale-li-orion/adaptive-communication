# Layer 2 — Decision-Semantic Compiler

本层拥有 Task + Evidence + Capability + Execution 的程序语义，以及它们到 live decision surface 的编译。

Canonical contracts 见 `RUNTIME-DOMAIN-OWNERSHIP-v1.md`；方法关系见 `PLAN-EVIDENCE-EXECUTION-v1.md`；capability/task registry 见 `COMMUNICATION-DOMAIN-REGISTRY.v0.1.json`；prior-art/claim ceiling 见 `NOVELTY-BOUNDARY-v1.md`。

当前稳定对象包括 audit/control/model/persistent-execution surfaces、plan–evidence dependency、dependency liveness、Decision Sufficiency、EvidenceNeed、semantic plan selection、persistent execution intent 与 semantic-state replanning。ordinary dependency construction 能解释当前正式 workload 时，不为了算法复杂度追加 solver。

## 当前 v0.2 重验状态

Layer 2 v1 仍然冻结为第一版 runtime/compiler 机制，但新的 Layer-1 v0.2 已经暴露出两个需要严格分开的结果。

**第一，as-is compatibility 不成立，但 B 类兼容缺口已经关闭。** `audit_layer1_v02_layer2_v1_representability.py` 在 41 个 frozen hard signatures 上得到 `0/41` lossless。原因是旧 O1–O6 compiler/registry/selector 仍围绕单 phase profile/fallback candidate family：它不能保留 3/4 个 overlapping obligation identity，也没有 per-obligation `WAIT / SEND_TERR / SEND_SAT / gateway_state_summary` binding。这个结果属于 **B 类兼容工程**，不能当方法贡献。随后新增 evaluation-only `layer1_v02_v1_binding.py`，只把公开 obligation contract 与 legal action surface 映射到现有 v1 `TaskContract / candidate_action_context / PlannedCapabilityInvocation`，不读取 future feasibility、hidden world、oracle witness 或 recommended action。

机器结果：[`results/agentic/layer1-v02-layer2-v1-representability.json`](../../results/agentic/layer1-v02-layer2-v1-representability.json)。

lossless-binding audit：41/41 hard signatures PASS；沿 exact policy tree 共检查 **2,224 个 reachable decision boundaries / 4,577 个 legal candidate actions**，typed invocation round-trip **0 mismatch**，结构化 hidden-field audit **0 leakage**。机器结果：[`results/agentic/layer1-v02-v1-lossless-binding.json`](../../results/agentic/layer1-v02-v1-lossless-binding.json)。这层 binding 只关闭兼容问题，不给 v1/v2 注入决策答案。

**第二，v1 acquisition trigger 本身存在 C 类 decision-semantic failure。** 在一个 lossless binding 假设下，直接调用 frozen `ActionConditionedReferencePlannerConsumer` 可以确认：当 owner dependency unresolved 且 capability visible 时，v1 会先发起 query。随后使用 Layer-1 v0.2 的 frozen transition semantics，在 41 个 hard signatures 的 exact minimal-resource policy 首次 query 之前做 counterfactual：

- query-legal boundaries：808；
- query 后仍有 exact causal continuation：64；
- legal-but-harmful queries：744；
- 41/41 signatures 都存在 harmful boundary；
- 41/41 signatures 的第一次 query-legal boundary 都 harmful；
- 41/41 signatures 的 exact minimal-resource policy 都把 query 推迟到更晚时刻。

机器结果：[`results/agentic/layer1-v02-layer2-v1-acquisition-trigger.json`](../../results/agentic/layer1-v02-layer2-v1-acquisition-trigger.json)。该 artifact 同时包含对 frozen `ActionConditionedReferencePlannerConsumer` 的 protocol check，确认 unresolved active owner dependency 会真实触发 query，而不是审计脚本自行假设这一规则。

因此当前问题已经从“EvidenceNeed 能否指出缺什么事实”推进到：

> **当前这份证据值得取得，但现在取得它是否仍保留后续任务选择？**

这使 `cache06.md` 保留的 future-choice / L-U 方法线正式成为 Layer-2 v2 主线。v2 应维护剩余 obligation、共享 opportunity/resource、evidence 与 pending execution 的动态可行前沿；`L_t(a)=1` 由可执行 causal continuation 支撑，`U_t(a)=0` 由 sound structural relaxation 排除，未决部分才继续取证、规划或 exact fallback。旧的“为每个 action 重新跑昂贵 depth-bounded proof stack”不代表这条方法线本身。

完整 v1 revalidation matrix 见 [`LAYER2-V1-REVALIDATION-v0.2.md`](LAYER2-V1-REVALIDATION-v0.2.md)：10 个机制项最终为 **A=4 / B=5 / C=1**。唯一确认的 C 类 failure 是 acquisition timing；B 类只表示旧 O1–O6 task binding 不能直接迁移，不能包装成方法失败。

Layer-2 v2 第一版已经完成 dev + held-out 验证，设计与结果见 [`LAYER2-V2-FUTURE-CHOICE-v0.1.md`](LAYER2-V2-FUTURE-CHOICE-v0.1.md)。当前实现采用 cheap sound structural `U=0`、replayable causal `L=1` 与 shared-memo exact fallback；不再为每个 action 重跑 depth-bounded proof stack。dev 18/18、held-out 7/7 的 task/resource outcome 都与 generic exact 一致，six ordinary baselines 分别为 0/18 与 0/7。held-out 上相对 generic exact：online expansions = 23.165%，wall = 53.251%。更强的 same-order ordered-exact 控制进一步表明：v2 expansions 仍只有 ordered exact 的 51.107%，但 wall 为 122.621%，因此当前剩余瓶颈已经从“搜索空间过大”收敛为“如何把结构剪枝的节点优势兑现成 strong-baseline wall-time 优势”。这也是 Layer 3 可以安全介入的接口：learning 只指导 unresolved action ranking，L/U 与 exact fallback 继续掌握 correctness。
