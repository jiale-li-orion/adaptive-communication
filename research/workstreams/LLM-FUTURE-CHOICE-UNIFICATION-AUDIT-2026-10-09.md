# LLM–Future-Choice Unified ASC Method: Implementation Audit and Next Gates

状态：**IMPLEMENTATION-AUDITED / DISTINCT WORKING LOOPS / JOINT METHOD NOT ADMITTED**。审计日期：2026-10-09。本文是现状与实验准入记录；Layer 1/2/3 的语义权威、`results/CLAIMS.md` 与已冻结实验维持原状。另一个会话负责 Related Work 和论文修改，本审计不改文献或稿件。

## 1. 总结

灾前山区的真实通信问题没有改变：有限供电、access/backhaul 间歇中断、任务修订与延迟反馈；Agent 必须在合法观测下进行取证、配置、发送、等待等决策，并完成 operational obligations。

**问题故事已统一；两条关键实现链分别成立；完整 LLM-driven Future-Choice ASC method 尚未有同一执行链的实证。**

第一条链是 DeepSeek 的 **decision-semantic/evidence-acquisition runtime**，已经有真实模型决策、执行、owner-scoped 取证和原生任务指标改善。第二条链是 **Future-Choice feasibility / certificates / exact fallback**，已经有 B 结构正确性与 C 的公开 UAV 外部任务结果。二者的组合既不能凭两个结果相加声称完成，也不应因此否定已有证据。

## 2. 实际输入、输出与控制流程

### DeepSeek Agent（已实现，full communication simulator）

- **输入构造**：`code/agentic_communication/context_runtime.py` 生成 `PromptAssembly`；`model_protocol.py::render_planner_protocol` 输出任务合同、资源清单、当前合法 evidence、近期 capability 结果、可用能力及 output schema。视模式额外携带 `investigation_state`、`evidence_needs` 和 `candidate_action_context`。`planner.py::BackendPlannerConsumer` 把该 envelope 作为 JSON 发给真实模型。
- **输出合同**：`runtime_contracts.py::PlannerDecisionProposal` 的 `stop`、`selected_plan_id`、`invocations`、`state_patch`、`reason_codes`。`planner.py::_expand_selected_candidate_plan` 只展开模型选中的 **Runtime-supported 且无 unresolved conditions** 的既有计划；其他观察能力可在同一决定中单独调用。
- **执行与反馈**：`policy.py::AgenticCommunicationPolicy` / `query_positive.py` 将调用交给 capability owner 和 `run_joint` 物理运行，保留 pending/in-flight、Class-A、owner query 延迟、ACK、配置命令、后续证据及审计记录。模型输出影响通信行为及其最终评分；这不只是 JSON 格式化实验。
- **结果**：`results/CLAIMS.md` 的 A7–A11 中，A10/A11 记录 gateway-backup query-positive loop。DeepSeek A10 在五个冻结 seed 上有 56/56 planner-turn effect-scope exact、16 次 owner query，较 no-acquisition control 平均 TDR **+5.238 pp**、AoI **−1150.7 s**，范围限于该 gateway-backup family。其他 query-negative/held-out 结果不等于复杂 future-feasibility reasoning。

**术语防混淆**：以上 `candidate_plan.feasibility = supported` 是 Runtime 当前 evidence/guard 支持某个操作；它**不代表** Future-Choice 的 `F(h,a)=1`，也不附带对所有兼容未来世界有效的 causal completion certificate。

### Future-Choice（已实现，Layer 1 v0.2 / B/C）

- `code/evaluation/agentic/layer1_v02_v1_binding.py` 把 Layer 1 v0.2 的合法 `WAIT` / `SEND_TERR` / `SEND_SAT` / `ISSUE_QUERY` 编成 typed invocation 与 `candidate_plans`，仅完成**合法性与语义绑定**；其代码明确不计算 future feasibility 或泄露 oracle。
- `code/evaluation/agentic/layer2_v2_future_choice.py` 实现 observation-conditioned continuation、optimistic `U=0`、replayable `L=1` 与 exact fallback。`future_choice_context()` 可以生成模型可见的 L/U 摘要，但当前直接调用者是验证/审计脚本，尚未进入 full-simulator DeepSeek Agent 的真实 planner input。
- `code/evaluation/agentic/future_choice_engine.py` 是跨域 `carried certificate → U=0 → L=1 → exact fallback` 协议；`code/evaluation/transfer/uav_future_choice_adapter.py` 通过外部任务专用 transition 与 certificate 实现 C。C 使用四个官方 **heuristic**，不能把 C 的效果归因于 DeepSeek。
- B 的 conditional/shared-opportunity/dependency-local 结果以及 C 的 21-instance 924-frontier exact audit、100-instance paired scale、set-MST 归因，均保留在 F1–F7 与冻结矩阵。它们不需要为补 LLM 的方法而重跑。

### Layer 1 A3 与 Learning 的归属

- `code/evaluation/benchmark/run_layer1_paper_llm_eval.py` 冻结 `{O1,O2,O3,O4,O6} × {w0,w2,w3} × {seed100,seed105} × {generic_react,task_conditioned}`，直接调用 `run_agentic_episode`，**没有调用** `FutureChoiceEngine` / `future_choice_context`。该 60-row subset 是 benchmark diagnostic，不是 unified method experiment。最后检查为 41 条唯一 OK checkpoint，A5 仍待 A3。
- `research/policy/README.md` 的历史 v0.1 learning-to-rank 在 dev 上 correctness 1,053/1,053、expansions 21,432→21,354（ratio 0.99636），却比 ordinary persistent exact 的 wall time 高约 1.55 倍；故 Layer 3 当前为 **PAUSED/OPTIONAL**，保留负结果，不能把“learning 已做”升级成有效的算法主贡献。

## 3. 目前最大的两个科学缺口

**J1：统一的可执行动作与证据语义。** full-simulator Agent 主要处理参数配置、gateway owner 取证和备用回传；Layer 1 v0.2 的 Future-Choice 主要处理按 obligation 的发送/卫星机会/query/wait，C 又使用路线/电池/充电。共享 correctness orchestration 并不意味着三个环境共享一份物理 transition。必须核实 action mapping、费用/时钟、ACK/pending、hidden-world 支持集、证书有效域和最终 native outcome，禁止把不同动作硬拼成同一 policy。

**J2：任务收益及算法增量的联合归因。** 当前没有在 **同一 DeepSeek + 同一任务 + 同一合法 history** 下，比较使用/不使用 Future-Choice 的实际行动、TDR/AoI/发送与取证成本、运行代价的冻结实验。这个缺口比继续扩大 C seed 数或寻找第三个相似的小仿真更直接。一般 POMDP shielding / resource-constrained reachability 已有先例；不能仅凭 safe mask 证明算法首创。

## 4. 四阶段执行计划（按 gate 前进）

### M0 — Action / observation / outcome contract bridge（最高优先级，禁止改 A3）

1. 各取一条 **真实记录**：DeepSeek query-positive 中的 `PromptAssembly → raw proposal → selected plan expansion → capability request/result → physical task metric`；Layer 1 v0.2 中的 `legal action → observation-conditioned state → FutureChoice L/U/exact → actual transition`。列出相同字段与独立字段，避免靠示意图推断。
2. 为 **一种** 语义一致的 ASC 任务边界指定 `FutureChoiceAdapter`，`candidate_action_context` 暴露当前合法候选；正确性层在模型决策前计算 ‎`L/U/certificate`（必要时 exact），保留原生 query/send/feedback 物理演进。优先复用 `layer1_v02_v1_binding.py` 和 `future_choice_context()`；若想接 full simulator，先验证原始设备配置动作存在忠实的 future-completion 模型，**否则不要冒充已统一**。
3. 将 `Runtime-supported` 和 `Continuation-certified` 分开编码；模型输入只使用 lawful public state、兼容世界描述与可公开的证书摘要，绝不能携带 evaluator-only hidden world 或离线最优答案。`unknown` 不得被默认为 safe；执行前所有证书都要重新核验 validity。

**通过门**：一个模型动作可以由 source-visible history 和 `PlannerDecisionProposal` 无损映射到 FutureChoice 候选、由同一 native runtime 执行并被原生 scorer 评价；反向 action/evidence/cost/clock replay 一致。先做 deterministic smoke/trace audit，暂不调用模型 API。

### M1 — 原生 metric headroom / decision diversity

审查现有 A/开发轨迹中三类决策：普通规则已饱和、仅有一个 verified-safe action、多个 verified-safe actions 但 native AoI/TDR/资源成本不同。额外记录：LLM 是否有 genuine evidence-use decision、是否可改变实际物理后果；记录前缀在完整任务分布中的占比，避免只挑会赢的例子。已有测试样本用于诊断，confirmatory split 另行冻结。

**通过门**：模型可控动作与原生任务指标之间有可重复、可归因的 headroom；即使为 negative/saturation 也按合同保留。

### M2 — Frozen DeepSeek ASC unified comparison

同一真实模型、task、allowed actions、observation history、执行 runtime、API 预算和模型参数；先对照：

| Arm | 模型可见/可选信息 | 识别的因果效果 |
|---|---|---|
| S0 ordinary LLM | 当前合法 task/evidence/capabilities/candidates | 无 Future-Choice 时的完整基线 |
| S1 binary continuation shield | S0 + sound action feasibility filter（unresolved 依合同 exact 验证） | **仅限制错误动作** 的效应 |
| S2 structured Future-Choice | 同一 verified action set + conditional obligation/resource bottleneck/certificate summary | 结构信息是否改善 **可行动作间的任务效用选择** |
| S3 ordinary planning-context control | 同一 action safety 与 budget + 普通 slack/remaining-budget/plan summary | 排除“任意更多规划信息都会产生同样收益” |

原生 outcome：TDR / AoI / on-time obligations / native task utility 与能力/备用通信开销；另报告 query次数、tokens、模型 latency、feasibility solver time、wall-time 和违规数。**不能把 checkpoint 中已知 deterministic witness 提前泄露给模型。** 如有必要另设已适配的固定 planner 强 control，并与 C 的 heuristic 尺度区分。

**通过门**：模型真实执行 + replay audits + paired native outcome；S1/S2/S3 差异可以归因，source manifest 和新实验 ID 独立于原 A3/B/C 冻结数据。

### M3 — Algorithm / learning only after measured deficit

若 S1==S2，则当前证据支持 **certifying LLM decisions**，不能主张 LLM 从结构信息中获得额外增量；优先深化证书计算。若 S2>S1 且超过 S3，考虑通过 supervision/structured feedback 改善 LLM 的资源与任务决策。若结构计算太慢，优先 certificate/invalidation 的真实 wall-time gate；历史 learned ranking 的系统负结果不得隐去。不得在没有任务效用或 solver cost 余量时新造 Pareto frontier/GNN/PPO 模块。

## 5. 论文与仓库的止漂约束

- 原 Story 暂保留 **Reality → Future-Choice Abstraction → External Validation**；当前的 B/C 是正确性及独立机制证据，A7–A11 是已运行的 LLM evidence-use 子系统。统一方法没有完成之前，正文不能把 B/C 归为 `DeepSeek-based Future-Choice method results`。
- Formal shielding、POMDP reachability 的贡献边界见 `paper/future-choice/FORMAL-PRIOR-ART-BOUNDARY-2026-10-09.md`；净 wall-time 尚未过门，不能写 universal solver speedup。
- A3 41/60 数据位于 `results/benchmark/layer1-paper-llm-test/`，**不能 reset 或删除**。停止/恢复 WSL 状态要实查，不以此前 incident 的状态自动推断当前网络健康。
- 本审计只改变 research documentation，不改 frozen model runner、benchmark/source-manifest、`results/CLAIMS.md` 或论文主文。新的方法或实验结果必须通过各自独立 gate 才能升级 claim。

**下一项具体交付**：`LLM ↔ Layer 2 action/observation binding` 的逐字段证据对照和 deterministic replay smoke。此门未过，不训练、不扩 seed、不宣称 unified method accepted。
