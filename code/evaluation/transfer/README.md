# External Transfer Probes

这个目录只放**外部 formulation / environment 的最小兼容性与机制探针**。

它不持有 Layer-1 benchmark authority，也不把外部工作重新实现成仓库主方法。正式研究路线由 `research/workstreams/` 记录。

当前：

- `asc_pull_query_future_choice_probe.py`：在 Pull-Based Query Scheduling 的 `state → query action → semantic effectiveness / query cost` 接口上测试 future-choice feasibility shield；只做 formulation-level probe，不宣称复现原论文数值。
- `asc_pull_query_cmdp_replay.py`：Pull-Based AoI/query/value 结构上的 finite-horizon constrained replay。
- `asc_pull_query_conditional_frontier_probe.py`：最小 observation-conditioned future-obligation witness。
- `asc_pull_query_conditional_family.py`：conditional query-chain scaling / persistent-exact negative boundary。
- `asc_pull_query_shared_opportunity_frontier.py`：branch-conditioned obligations × shared opportunities；复用 Layer-2 max-flow/min-cut conflict frontier。
- `audit_drl_ec3_transfer_fit.py`：静态审计官方 DRL-EC³ emergency-communication environment 是否具备 future-choice transfer 所需结构。
- `audit_uav_attention_future_choice.py`：公开 UAV hard-deadline environment 的 native continuation failure / official heuristic red-team。
- `run_uav_attention_continuation_shield.py`：evaluator-only exact continuation shield upper bound。
- `run_uav_attention_future_choice_lu.py`：L/U + replayable route certificate + exact fallback future-choice prototype。
- `summarize_uav_attention_future_choice_robustness.py`：200/1000-seed compact robustness artifact。
