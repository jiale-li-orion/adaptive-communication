# Layer-2 v2 — Future-Choice / L-U

状态：**DEV PASS / HELD-OUT PENDING**

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

因此 dev 阶段已经满足 `cache06.md` 要求的最低系统门：结果不再只是“少 memo node”，而是在相同 task quality / 相同资源点下同时降低 search expansion 与真实 wall time。

## 5. Claim boundary

当前可以说：

> 在冻结的 Layer-1 v0.2 dev hard signatures 上，sound future-choice L/U pruning + replayable causal tail + exact fallback 保持 exact task/resource outcome，同时显著降低 online exact-planning compute。

当前还不能说：

- held-out test 已通过；
- v2 已经优于所有可能 planner；
- L/U 已证明对任意 Agentic Communication task 都有复杂度优势；
- learning 已经提供额外贡献。

held-out test 必须在 v0.1 code freeze 后一次性运行；测试结果出来前不再根据 test 调参。
