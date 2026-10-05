# Conditional Action Frontier v0.1

状态：**BOUNDED METHOD DIAGNOSTIC / Layer 2 reference object**

目标不是给 query 打分，而是维护当前 causal boundary 上哪些动作仍然保住未来任务可行性。

```text
legal_actions
    ↓ force one action
exact causal continuation + replay
    ↓
certified_actions(Q,B)
```

因此同时区分：

- `query_now_legal`
- `query_now_certified`
- `query_legal_but_not_certified`
- `can_defer_query_now`
- `query_free_completion`

在 12 个 retry-semantics frozen corrected-source bundles 上，沿 exact minimal-resource policy 的 pre-query decision boundaries 做审计：

```text
decision boundaries                         298
legal query but not certified boundaries    209
query-free from initial boundary               2
single certified query time                    7
query certification re-entry                   3
```

三条 re-entry 轨迹与此前 acquisition-timing frontier 完全一致：

```text
16800 → gap → 27600
15000 → gap → 25800
14100 → gap → 24900
```

所有 exact-policy 当前动作均属于 certified action set；所有 certified action 均携带 replay 通过的 causal continuation witness。

## L/U lazy classification diagnostic

对同一批 boundary/action 做五组对照。普通 exact-state memo、resource-monotone memo、witness-domain memo 在该 workload 上结果完全相同：

```text
classified actions           640
exact fallback calls          74
fallback expansions       36,942
```

加入 per-world optimistic residual-flow `U=0` 后：

```text
exact fallback calls          60   (-14, -18.9%)
fallback expansions       35,300   (-1,642, -4.4%)
```

`satellite-only` structural lower certificate 能独立证明 6 个 action，但这 6 个在 warm-cache traversal 上本来已经 exact memo-hit，因此没有进一步减少 fallback。

进一步把 upper 写成 bounded non-anticipative causal lookahead，收益很快饱和：

```text
upper d0   fallback 60   exact expansions 35,300   upper nodes   564
upper d1   fallback 60   exact expansions 35,300   upper nodes 1,156
upper d2   fallback 60   exact expansions 35,300   upper nodes 1,754
upper d4   fallback 56   exact expansions 35,052   upper nodes 3,060
upper d6   fallback 56   exact expansions 35,052   upper nodes 4,510
```

因此在线版本优先保留 d0：d4 为了额外剪掉 4 个 failure fallback，需要新增 2,496 个 upper-search nodes，只减少 248 个 exact expansions；d6 再增加 1,450 个 upper nodes，已经没有新的 exact-expansion 收益。

event-depth causal lower 同样迅速饱和：

```text
lower d1 + upper d0   fallback 58
lower d2 + upper d0   fallback 56
lower d4 + upper d0   fallback 56
lower d6 + upper d0   fallback 56
```

对剩余 56 个 exact fallback 进一步诊断：25 个 success 在 event-depth d12 仍没有结构 lower certificate；31 个 failure 中只有 4 个在 upper d4 被证伪、2 个在 upper d8 被证伪，剩余 25 个到 d12 仍 unresolved。这里最重要的发现是 success policy 的**原始事件深度与真实选择深度严重错位**：

```text
25 个 success fallback：
raw policy depth        22–65
non-WAIT choice depth    2–6
query count              0–1
observation depth        0–1
```

原 event-depth lower 把 pending completion、future release 和 time-lattice progression 中的几十个 `WAIT` 都当作 horizon 消耗，因此 `d12` 仍可能看不到一个只含 3–6 次真实发送/取证选择的策略。Layer 2 后续统一把 **future-choice depth** 与 raw event depth 分开：`WAIT` 不消耗 choice horizon，`SEND_* / ISSUE_QUERY` 消耗 1，observation 是 AND 分支但不算主动选择。这个坐标比“planner 深度”更接近需要维护的 context 复杂度。

当前结论很明确：cache/domain 本身不构成方法优势；真正新增的信息来自**通信结构直接给出的 future-choice upper/lower certificate**。exact action frontier 已经定义 reference，在线对象改写为三值 context：`L=1` 的动作已有 replayable continuation certificate，`U=0` 的动作已被结构证伪，只有 `L=0,U=1` 才需要 exact fallback。取证控制直接从这个 context 派生：`STOP_ACQUISITION_CERTIFIED / CAN_DEFER_QUERY / QUERY_REQUIRED_NOW / QUERY_HARMFUL_NOW / UNRESOLVED`，不再额外设计 query relevance score。

## Claim boundary

- 这里只覆盖 12 个预选 corrected-source bundles，不是 regenerated benchmark 的频率估计。
- exact action frontier 是 reference；L/U 是待发展的在线近似。
- 所有性能数字必须和 ordinary memo 分账，不能把 memo reuse 当作结构方法收益。
- 当前尚未证明 wall-clock 或 benchmark-wide speedup。

