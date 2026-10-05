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

当前结论很明确：cache/domain 本身不构成方法优势；真正新增的信息来自**通信结构直接给出的 future-choice upper/lower certificate**。下一步增强 lower bound，优先使用 compatible worlds 共同可执行的 terrestrial opportunities + public satellite schedule，并继续要求生成可 replay 的 causal policy。

## Claim boundary

- 这里只覆盖 12 个预选 corrected-source bundles，不是 regenerated benchmark 的频率估计。
- exact action frontier 是 reference；L/U 是待发展的在线近似。
- 所有性能数字必须和 ordinary memo 分账，不能把 memo reuse 当作结构方法收益。
- 当前尚未证明 wall-clock 或 benchmark-wide speedup。

