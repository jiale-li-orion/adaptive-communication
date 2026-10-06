# Layer-2 v2 — Future-Choice / L-U

状态：**DETERMINISTIC DEV FREEZE CANDIDATE / STRONG WALL GATE OPEN / INDEPENDENT STRUCTURAL HOLDOUT UNRESOLVED**

Layer-2 v2 针对 frozen v1 已确认的 category-C failure：v1 能识别 unresolved owner evidence，却不会判断“此刻取证以后，未来 obligation feasibility 是否仍成立”。Layer-1 v0.2 中 query 是真实通信 action，会消耗时间和通信机会，因此 evidence relevance 与 acquisition timing 必须在同一 causal state transition 内评估。

## 1. Method object

v2 维护 future-choice context：当前合法 action 之后，哪些 causal continuation 仍可能完成全部 operational obligations。

对 action `a`：

```text
L_t(a) <= V*(h_t, a) <= U_t(a)

L_t(a) = 1  -> 已有可 replay 的 causal continuation 证明任务可完成
U_t(a) = 0  -> 乐观 structural relaxation 仍不可行，因此该 action 必死
L_t(a) = 0, U_t(a) = 1 -> unresolved，进入 exact same-information fallback
```

当前实现位于：

- `code/evaluation/agentic/layer2_v2_future_choice.py`
- `code/evaluation/agentic/run_layer2_v2_matrix.py`
- `code/evaluation/agentic/test_layer2_v2_future_choice.py`

## 2. Correct implementation boundary

当前实现刻意避免旧 prototype 的主要错误：

- 不为每个 action 单独启动一个 depth-bounded proof planner；
- `U=0` 使用便宜且 sound 的 optimistic residual-feasibility necessary conditions；
- `L=1` 使用可 replay 的 common-opportunity causal tail certificate；
- unresolved state 才进入一个共享 memo 的 exact AND/OR fallback；
- fallback 内的 U/L 是 cheap prune / tail completion，不是另一套昂贵 planner；
- policy witness 可以 replay，不能只返回 scalar score；
- Layer-1 task/evidence/transition/oracle semantics 完全冻结。

dev ablation 比较了 `root_query / query_recursive / all_recursive / none`。当前 `all_recursive` 在 cheap-U 实现下同时取得最好的 search reduction 与 end-to-end runtime，因此作为 v0.1 默认。这里的 `all_recursive` 指**每个 exact fallback action 先做便宜 structural U 必要条件检查**，不代表重新运行深层 bounded proof stack。

## 3. Soundness gate

`test_layer2_v2_future_choice.py` 当前要求：

- v2 与 generic exact 找到相同 minimal `(paid-query, satellite-budget)` resource point；
- 当 `U=0` 时，强制对应 query 后的 exact continuation 也必须 infeasible；
- 当 `L=1` 时，certificate 必须能在 frozen Layer-1 kernel 上 replay 到完成。

当前：**PASS**。

## 4. Development result

固定 development hard split：18 signatures。

结果文件：`results/agentic/layer2-v2-matrix-dev-all-recursive.json`。

正确性 / task quality：

- 18 / 18 v2 success；
- 18 / 18 minimal resource point 与 generic exact 一致；
- six ordinary baselines 均 0 / 18 success：shallow rule、least-slack、latest-feasible-send、always-query-then-plan、myopic flow VoI、depth-3 flow；
- sound U prunes：6,675；
- replayable L hits：138。

同一当前资源点上的 **online planning compute**：

- generic exact expansions：28,317；
- v2 expansions：3,963；
- expansion ratio：**0.13995**；
- generic exact wall：1.4212 s；
- v2 wall：0.4673 s；
- wall ratio：**0.32880**；
- v2 在 18 / 18 signatures 上 expansions 更低；
- v2 在 18 / 18 signatures 上 wall time 更低。

离线 resource-envelope construction 也单独报告，不能和 online planner cost 混为一谈：

- expansion ratio：0.31192；
- wall ratio：0.76199；
- 18 / 18 expansions 更低；
- 15 / 18 wall 更低。

因此 dev/held-out 已经证明这套 future-choice L/U kernel 不只是“少 memo node”：相对仓库 generic exact，它在相同 task quality / 相同资源点下同时降低 search expansion 与真实 wall time。但这只是 `cache06.md` 完整方法合同中的 **planning-kernel gate**，不能等价成 Layer-2 v2 已毕业。

## 4.1 Gap to the original cache06 method contract

原始 `cache06.md` 对 v0.5/Layer-2 v2 的要求高于当前 kernel。以下项目仍然是正式 open gate：

- **动态条件前沿**：显式维护哪些后续方案仍可行、依赖哪些 evidence/resource/pending-execution 条件，而不只在一次 exact search 内做 memo；
- **证书有效域与局部失效**：证书应在一段资源/机会条件上复用，并由 ACK、发送承诺、窗口关闭、新 obligation、证据老化等事件精确失效；
- **incremental/full-rebuild 等价**：对每条合法事件前缀核对保留的可行行动、成本前沿和证书有效性，而不只比较最终成功或 minimal resource point；
- **完整 correctness gates**：non-anticipativity、bound soundness、pruning preservation、历史事实/当前推断分离都需要全前缀机器审计；当前 soundness test 只是代表性 smoke + 端到端 exact outcome 对账；
- **强基线 ladder**：补 gateway local autonomy、passive-only、normal-send-as-probe、fixed periodic/batch evidence、真正 depth-k belief/receding-horizon、普通 incremental AND-OR/dependency-tracking 等原文指定对照；
- **方法归因**：当前 same-order exact 在 held-out wall time 上仍快于 v2（0.041 s vs 0.050 s），所以“L/U 相对强同序实现的净计算优势”尚未通过；
- **结构泛化 provenance**：7-signature held-out/test 已在 planning-kernel checkpoint `fdc0846` 暴露；后续 full-v2 开发发生在该结果已知之后，因此它只能作为 regression evidence。train/dev-only structural descriptor 可做 coverage 诊断，但不能把旧 test 重新包装成 pristine method-level structural holdout；独立 generalization claim 需要新的 preregistered protocol/cohort。
- **三笔账与系统前沿**：分别落盘 gateway-local evidence、remote acquisition、planner computation，并最终比较 task-quality / acquisition-cost / computation frontier；当前主要完成 planner compute；
- **ASC system claim**：当前 hard family 只有 `gateway_state_summary` 这一类 owner query，尚未证明异构 evidence acquisition、evidence ageing/revalidation 与 layered recovery 组成的完整 autonomous-information-construction 闭环。

在这些门关闭前，Layer 3 learning 只能作为 search/context 的辅助实验，不能替代 Layer-2 v2 方法验收。

## 5. Held-out result

held-out hard split：7 signatures。测试在冻结 commit `2f0c47f976d9b013fe66c8298696d6834a23ae08` 上一次性运行；测试过程中没有修改源码。

结果文件：`results/agentic/layer2-v2-matrix-test-all-recursive.json`。

正确性 / task quality：

- 7 / 7 v2 success；
- 7 / 7 minimal resource point 与 generic exact 一致；
- six ordinary baselines 均 0 / 7 success。

相对 generic exact：

- online expansions ratio：**0.23165**；
- online wall ratio：**0.53251**；
- 7 / 7 expansions 更低；
- 7 / 7 wall 更低。

相对更强的 **same-order ordered exact**：

- ordered exact 先使用与 v2 相同的 action order，再做普通 exact search，因此隔离“只是排序更好”这一解释；
- v2 online expansions ratio：**0.51107**；
- v2 online wall ratio：**1.22621**；
- 说明 L/U 本身在 held-out 上继续减少约一半搜索节点，但当前 Python structural-check 常数开销仍使 wall time 比 ordered exact 高 22.6%；
- v2 仅在 2 / 7 signatures 上 wall time 优于 ordered exact。

因此 Layer-2 v2 的 held-out 结论应写成：**future-choice L/U 在保持 exact task/resource outcome 的同时，稳定减少搜索空间；相对 generic exact 已获得端到端 wall-time 收益，但相对 same-order exact 的 wall-time 优势尚未成立。** 这个负边界不能隐藏，也不能通过重新调 held-out 参数修饰。

## 6. Claim boundary

当前可以说：

> 在冻结的 Layer-1 v0.2 dev hard signatures 上，sound future-choice L/U pruning + replayable causal tail + exact fallback 保持 exact task/resource outcome，同时显著降低 online exact-planning compute。

当前还不能说：

- v2 已经优于所有可能 planner；
- L/U 已证明对任意 Agentic Communication task 都有复杂度优势；
- learning 已经提供额外贡献。

下一阶段如果引入 learning，只允许改变 unresolved action 的 search order / ranking，不得改变 legality、L/U soundness、evidence ownership、task success 或 exact fallback correctness。这样才能把“搜索空间减少”进一步转成相对 strong ordered-exact 的真实 wall-time收益，而不把安全性押给 learned policy。
