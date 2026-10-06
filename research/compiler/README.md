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

Layer-2 v2 当前已经形成 **dev-complete deterministic mechanism core / final method freeze pending**。planning kernel、persistent action-feasibility frontier、flow/min-cut conflict frontier、event-local invalidation、versioned evidence lifecycle、L/U soundness、完整 baseline ladder、three-ledger accounting、structural descriptor、acquisition-mode competition 与 controlled intervention 都已经有 full-dev machine artifact。conditional `Q×B` frontier 在 query-timing scope 上 432/432 与 exact 一致，并在 1,947 个 resource-cell 请求中由 validity domain 直接回答 960 个。当前 deterministic freeze 前的主要 open correctness gate 已收敛为 **bounded off-policy non-anticipativity / bound-pruning / incremental-equivalence audit**；strong-baseline net-compute / system-frontier 仍独立保持 OPEN。final structural test 在 freeze 前继续封存，Layer 3 不进入主结果。

## Baseline ladder audit

Baseline 不再按当前实现临时挑选，统一回到 `cache06.md` 的两版要求：Layer-1 admission 阶段的强 deterministic ladder 用来证明 hard surface 不会被廉价规则饱和；Layer-2 v2 阶段的 final ladder 用来区分 future-choice/conditional-frontier 方法收益与普通规划、普通缓存、普通增量工程优化。

Layer-1 v0.2 已冻结的 V8 结果仍然有效：1,423 个 V0–V7 pass signatures 中，cheap policy rule 覆盖 1,346，finite/deep horizon 再覆盖 36，最终留下 41 个 hard signatures。具体 baseline coverage 包括 `always_query_then_plan=608`、`least_slack=1326`、`myopic_flow_voi=1192`、`shallow_rule_combiner=1009`、`true_depth_2_belief=3`、`receding_horizon_3=23`、`receding_horizon_4=3`、`receding_horizon_6=10`。这些数字回答 **benchmark headroom**，不自动回答 Layer-2 方法归因。

Layer-2 方法公平性按下面这张固定表验收：

| `cache06.md` baseline | 当前 repo 对应实现 | 当前状态 | Layer-2 v2 还需要什么 |
|---|---|---|---|
| Gateway local-autonomy EDF/reserve | `ordinary_baselines_compositional_v0_1.gateway_local_edf_reserve` | 已实现；Layer-1 deployment alternative | 在 frozen hard signatures 上统一记 task/acquisition/compute 三账 |
| Passive-only planner | no-paid-query observation-matched exact ceiling + passive ACK semantics | **full-dev 0/18** | exact ceiling 已证明这 18 个 hard signatures 上不存在任何合法 no-paid-query common policy；弱 passive heuristic 不可能反转该结论 |
| Normal-send-as-probe | `send_probe_ack_fallback` + causal `NORMAL_SEND_AS_PROBE` | 已实现 | 与条件 query 同账比较，不能只数 API 次数 |
| Fixed primary+receipt / fixed refresh | `fixed_owner_read_edf`；`solve_fixed_query_schedule(FIRST_RELEASE/EVERY_RELEASE/SATELLITE_START/EVERY_SECOND_EVENT)` | **full-dev 全部 0/18** | hard dev 上未饱和；test 在方法冻结后一次性运行 |
| Myopic conflict/latency / VoI | `solve_myopic_flow_voi` | **full-dev 0/18** | hard dev 上未饱和 |
| Shallow rule combiner | `solve_shallow_rule` | **full-dev 0/18** | 浅层规则门 dev PASS |
| True depth-k belief planner | `solve_depth_k` | **depth-2 = 0/18，depth-3 = 0/18** | 行动—观察深度定义已满足；hard dev 未饱和 |
| Receding-horizon planner | Layer-2 evaluator 中 `receding_flow_terminal_{2,3,4}`，使用 generic residual-flow terminal relaxation | **horizon 2/3/4 全部 0/18** | 不再用仅改名的旧 `solve_receding_horizon` 冒充 final baseline；当前 flow-terminal 版本已进入方法矩阵 |
| Generic exact | `ExactContinuationReference` / observation-matched exact | 完整 | oracle / quality ceiling；不算方法失败 |
| **Ordinary incremental AND–OR** | `layer2_v2_incremental_exact_baseline.PersistentOrderedExact` | **full-dev 1,053/1,053 exact frontier match；51,264 expansions** | 当前最强 wall-time control；v2 净 wall 门仍未过 |
| **Ordinary structure-optimized cache/dependency** | `layer2_v2_dependency_cache_baseline.PersistentDependencyExact` | **full-dev 1,053/1,053 exact frontier match；44,343 expansions；159 replay-gated separator hits** | 不使用 conditional frontier；作为方法结构强对照保留 |

Persistent-frontier 已经把 method object 从“一次 policy search”推进到 live action-feasibility surface。full-dev four-arm audit 在 **1,053 / 1,053 reachable decision prefixes** 上都与 fresh exact action frontier 完全一致；v2 search expansions 稳定为 ordinary persistent exact 的约 **41.7–41.8%**。但两次独立冻结运行的 v2/ordinary wall-time 分别为 **1.202× / 1.512×**，因此净计算门继续 `OPEN`。后续不再用单 case timing 或 Python 常数优化覆盖这个结论。

### Dynamic conflict-frontier audit

`cache06.md` 要求的算法对象已经从 memo/search engineering 单独抽出来，当前实现位于 `code/evaluation/agentic/layer2_v2_conflict_frontier.py`。它显式维护 obligation–opportunity–resource 的冲突连通分量、Hall deficit / minimum-backup lower bound、component validity domain 与 event-local invalidation；query observation 只更新 compatible support，terrestrial/satellite commit、pending completion 和机会变化只使依赖相交的 component 失效。冲突见证现已严格由 **bipartite max-flow + residual min-cut** 生成，不再枚举 obligation 子集；exact/L-U 仍是 unresolved frontier 的 correctness authority。

当前 flow/min-cut full-dev audit 已完成，结果写入 `results/agentic/layer2-v2-conflict-frontier-dev-flowcut.json`：

- **18 / 18 hard signatures PASS**；
- **1,053 / 1,053 reachable causal prefixes** 上 incremental conflict frontier 与 fresh full rebuild 完全一致；
- fresh rebuild 累计会重建 **2,934** 个 world-level conflict components；
- incremental algorithm 实际只重算 **360** 个，复用 **2,574** 个；
- `recompute_ratio_incremental_over_full = 12.270%`；
- 1,053 / 1,053 reachable prefixes 上仍与 fresh rebuild 完全一致，且 0 次 partition fallback。

这项结果回答的是原始 method contract 的“受影响冲突分量增量更新”门，而不是 Python 常数优化：未受事件影响的 conditional component certificate 被直接保留，事件只触发依赖域相交部分的重算；机器审计同时要求每个合法 prefix 与 fresh rebuild 完全一致。当前 model-facing context 只暴露 support-level feasibility consequence（support count、backup lower bound、conflict obligations/components），不暴露 per-world future window identity、内部 certificate validity interval 或 oracle witness；validity domain 只留在 planner 内部作为复用/失效依据。

强对照已经补到同一接口：`PersistentOrderedExact` 是 same action order + persistent memo + early stop、无 L/U/conditional certificate；`PersistentDependencyExact` 进一步加入历史 dependency-separator 的 dead-history projection 和 replay-gated success reuse，但不使用 conditional frontier。两次独立 full-dev four-arm 冻结运行都达到 **1,053 / 1,053 action-frontier exact match**。search expansion 很稳定：v2 为 **21,381–21,432**，ordinary incremental exact 为 **51,264**，dependency-cache exact 为 **44,343**，fresh exact-per-action 为 **365,295**；即 v2 约为 ordinary incremental 的 **41.7–41.8%**。wall-time 则明确没有过最强基线门：两次 v2/ordinary 比分别为 **1.202×** 与 **1.512×**。因此当前可以 claim 结构搜索空间缩减和 affected-component update，但 **净计算门仍 OPEN**；不再用 Python micro-optimization 或单次计时噪声把它包装成 PASS。

Versioned evidence-dependent validity 已经闭合，`cache06.md` Gate 8/9 机制审计现在也已经闭合。acquisition-mode artifact 在 **441 个 exact-policy reachable、query-budget-positive boundaries** 上区分 frozen process 中真实存在的 acquisition alternatives：dedicated query safe 39 / harmful 402；18 个边界 query 唯一必要；12 个边界 query 与正常 `SEND_TERR` 都安全；3 个边界 query harmful 但 normal send-as-probe 仍安全；75 个边界 query harmful 而有真实 pending delivery/ACK 的 passive WAIT 仍安全；30 个边界 direct fallback 安全而 query harmful。controlled-intervention artifact 则以 original no-query 0/18 为基线：只放松 satellite budget 为 9/18，彻底取消 shared backup scarcity 为 18/18，perfect current observation 为 18/18，共同晚期恢复机会为 18/18；instant execution ACK 与 deadline-only relaxation 都仍为 0/18。后两项 negative control 被保留，说明困难不是“ACK 慢”或“deadline 短”这一维解释。所有 intervention 都是 evaluator-only deep-copy / temporary timing counterfactual，不修改 frozen Layer-1 generator、split 或 test。

### Versioned evidence context audit

Evidence lifecycle 已从 Layer-1 causal observation 中恢复为独立的 Layer-2 runtime object，代码位于 `layer2_v2_evidence_context.py`。它不修改 Layer-1 state schema，而是在 compiler/runtime 层维护 versioned evidence ledger：`proposition / subject / owner / value / sampled_at / arrived_at / request-id / version`，并分别记录 query issue、query response/timeout、gateway receipt 与 final ACK。历史记录始终保留；只有它对“当前状态推断”的支撑资格会随时间和新版本变化。

full-dev audit `results/agentic/layer2-v2-evidence-context-dev.json` 已通过：

- **18 / 18 hard signatures，1,053 causal prefixes**；
- `history_retention_pass = true`；
- `timeout_unresolved_pass = true`，timeout 不产生伪造远端 payload；
- `gateway_version_monotone = true`，新 owner read 不会被旧响应覆盖；
- `no_hidden_future_pass = true`、`no_oracle_witness_pass = true`；
- **18 / 18 signatures** 都实际出现 gateway snapshot 被保留为历史事实、但对当前状态已经 `STALE_FOR_CURRENT_STATE` 的前缀；
- `CURRENT_AT_SAMPLE = 0` 是预期结果：当前 owner query 有声明的 60 s return delay，center 收到时 snapshot 已经是过去采样。它是否仍足以支持当前行动由 future-choice feasibility 判断，而不是把“非当前采样”直接等同于“无用”。

model-facing context graph 现在显式包含 State / Obligation / OpportunityResource / Conflict / Evidence / Action 六类节点及 evidence-support/history-only 边，同时继续隐藏 per-world future window identity 和 oracle witness。这关闭了 `cache06.md` correctness property ⑤ 的第一版机器门：**历史事实与当前推断分离**。

### Correctness gate audit

当前 deterministic v2 对 `cache06.md` 五项 correctness property 的机器状态如下。这里严格区分 **exact-policy reachable prefixes 已验证** 与 **全 legal off-policy history 尚未穷举**：

| property | 当前机器证据 | 状态 |
|---|---|---|
| 非预知性 | Layer-1 observation-matched support；v0.2→v1/v2 binding 0 hidden leakage；conflict/evidence context 不暴露 future world/window identity 或 oracle witness | reachable protocol surface PASS；全 off-policy exhaustive audit 仍 OPEN |
| L/U 界可靠性 | `layer2-v2-bound-soundness-dev.json`：18 signatures、1,053 prefixes、**2,184 legal actions**；990 个 `L=1` 全部 exact-feasible，510 个 `U=0` 全部 exact-infeasible，2,184/2,184 `L<=U` | reachable-prefix PASS |
| 剪枝保持性 | dev 18/18 minimal resource point = generic exact；persistent action frontier **1,053/1,053** = fresh exact | reachable-prefix / dev resource frontier PASS |
| incremental = full rebuild | flow/min-cut conflict frontier **1,053/1,053** exact match；360/2,934 component recomputes | reachable-prefix PASS |
| 历史事实 / 当前推断分离 | 18 signatures / 1,053 prefixes evidence audit：history retained、timeout unresolved、version monotone、18/18 stale-but-historical gateway snapshots | PASS |

这张表还不允许写成“形式证明完成”。尤其 non-anticipativity、bound/pruning 的 **全部合法 off-policy histories** 仍需在最终方法冻结后做 exhaustive/bounded exhaustive audit；当前 claim 只覆盖 frozen hard-dev exact-policy reachable prefixes 与 resource/action frontiers。

### Three-ledger accounting

`results/agentic/layer2-v2-three-ledgers-dev.json` 已把 `cache06.md` 要求的三笔账分开落盘，不引入加权总分：

- **Task quality**：18/18 hard-dev signatures 完成全部 obligations，18/18 与 generic exact 的 minimal `(query budget, satellite budget)` point 一致；
- **Acquisition / communication**：winning policy 的 worst causal branch 共 **18 次 remote owner queries**，即每 case 平均 **1.0**；terrestrial report sends 共 39，平均 **2.167**；satellite report sends 共 48，平均 **2.667**。passive ACK 仍是零额外 acquisition cost；bytes / airtime / energy 保持 `unknown`，不从动作次数外推；
- **Planner compute**：winning resource cell 累计 **3,963 expansions / 0.450 s**，均值约 **220.17 expansions / 0.0250 s**；完整 minimal-resource sweep 累计 46,725 expansions / 6.924 s。

三账的目的不是宣称这些绝对 wall-time 可跨机器复现，而是禁止把“少 query、少 satellite、少 planner compute”揉成一个 reward 后掩盖 trade-off。后续结构/test 结果仍分别报告三账。

### Structural holdout freeze

结构留出 descriptor 已在 **不读取 test split** 的前提下冻结到 `results/agentic/layer2-v2-structural-descriptor-freeze.json`。固定维度来自 `cache06.md`：obligation count、maximum temporal overlap、maximum conflict width、event classes、first-occurrence ordering 与 compressed event-interleaving skeleton；明确禁止使用 recipe ID、solver signature、seed 或仅起始相位充当结构键。

当前 coverage 诊断只读 train/dev：train 16 signatures / 3 structural keys，dev 18 / 4 structural keys，按冻结 descriptor **dev 18/18 均属于 train 未覆盖结构**。这说明 dev 的结构迁移压力真实存在，但因为 dev 已经参与方法开发，不能把它包装成最终 structural holdout。**test 仍未读取；只有 deterministic method freeze 后才允许一次性运行 test，并单独报告 train/dev 未覆盖 structural keys。**

这一门现在已经扩展到完整 dev split，并且结果进一步分成两层：

1. **persistent action-feasibility frontier correctness**：18/18 dev hard signatures、共 **1,053 / 1,053 reachable decision prefixes** 与 fresh exact action frontier 完全一致；persistent v2 构造这些 live action surfaces 时累计 **21,432 expansions**，ordinary persistent exact 为 **51,264**，fresh exact-per-action 为 **365,295**。因此 v2 的 search-space reduction 在完整 dev 上成立，expansion ratio 分别为 **41.81%**（vs ordinary incremental exact）和 **5.87%**（vs fresh rebuild）。但 wall-time 仍是 **5.402 s vs 3.187 s**，即 v2 / ordinary incremental exact = **1.695×**；净 wall gate 仍未通过。
2. **dependency/conflict frontier incremental maintenance**：当前 v0.2 实现显式维护 obligation–opportunity conflict components、Hall deficit / minimum backup lower bound、resource/pending-execution dependency 与 validity interval。第一版 17.38% logical recomputation ratio 已撤销，因为那版仍先 fresh-build world frontier。当前 corrected runtime 使用真正 event-delta invalidation：从 old→new execution state 得到 changed dependency nodes，只重建相交 obligation component，并在分区可能非单调 merge 时保守 full fallback。完整 dev 已通过：18/18 signatures、**1,053 / 1,053 prefixes** 与 fresh rebuild 完全一致；fresh rebuild 共需构造 **2,934** components，incremental runtime 实际重算 **360**、复用 **2,574**，**recompute ratio = 12.27%**。

同时，`QUERY_HARMFUL_NOW` 的 full-dev 结构审计说明 **physical conflict frontier 只是必要子层，不能独立解决 v1 failure**：query-timing audit 的 432 个 pre-query boundaries 中 exact 判定 402 harmful / 30 safe；纯 physical Hall/optimistic matching `U=0` 对 harmful 覆盖为 0/402。主对象因此固定为 **conditional `Q×B` future-choice frontier**，并已进一步接到 acquisition-mode audit：更广的 all-reachable scope 有 441 个 query-budget-positive boundaries，其中 18 个 query 唯一必要，12 个与业务 send-as-probe 竞争，75 个 harmful query 可由真实 pending feedback + WAIT 安全替代。当前不再扩充 Q/B 坐标或新造 evidence capability；下一 deterministic correctness gate 是 bounded off-policy histories。

这两个结果的 claim boundary 固定为：**增量结构与局部失效 correctness 已通过 dev；search-space advantage 已通过；相对 ordinary persistent exact 的净 wall-time 优势尚未通过。** 因此后续主方法工作应该继续减少 unresolved component 进入 exact fallback 的范围，或证明随 conflict width / affected-component size 增长的算法优势；不再用 Python object/layout 微优化冒充算法贡献。

完整 baseline ladder artifact 已落在 `results/agentic/layer2-v2-baseline-ladder-dev.json`。18 个 hard-dev signatures 上：gateway-local autonomy = **18/18**；generic exact = **18/18**；no-paid-query exact = **0/18**；normal-send-as-probe、fixed owner read、四种 fixed query schedule、myopic VoI、shallow rule、true depth-2/3、flow-terminal receding horizon 2/3/4 均为 **0/18**。因此当前困难不是物理不可达：本地 placement 可完成；困难来自 center placement 下 evidence acquisition、shared opportunity 和跨阶段 future-choice 耦合。该 hard set 是 Layer-1 在 v2 方法形成前冻结的 structural survivor，不允许因这些结果再反改 generator。

后续顺序固定为：**bounded off-policy correctness / non-anticipativity audit → deterministic method freeze → 只读一次 final test / structural holdout → 系统前沿汇总 → 再决定 Layer-3 learned ranking 是否进入主结果**。acquisition-mode 与 controlled-intervention Gate 8/9 已在 dev 关闭；strong ordinary persistent exact 的净 wall-time 门继续独立记为 `OPEN`，不通过 Python 微优化冒充算法贡献。

ordinary incremental AND–OR 与 replay-gated dependency/cache exact 的 full-dev 四臂归因已经完成并冻结：1,053/1,053 action frontiers 与 fresh exact 一致；v2 为 **21,432 expansions**，ordinary persistent exact **51,264**，dependency-cache exact **44,343**，fresh exact-per-action **365,295**。v2 wall 明显优于 dependency-cache control，但仍慢于 lean ordinary persistent exact，因此结构收益已排除“只是 dead-history cache”的解释，净 wall gate 仍保持 OPEN。
