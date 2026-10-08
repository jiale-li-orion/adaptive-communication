# External Transfer Probes

这个目录只放**外部 formulation / environment 的最小兼容性与机制探针**。

它不持有 Layer-1 benchmark authority，也不把外部工作重新实现成仓库主方法。正式研究路线由 `research/workstreams/` 记录。

当前：

- `asc_pull_query_future_choice_probe.py`：在 Pull-Based Query Scheduling 的 `state → query action → semantic effectiveness / query cost` 接口上测试 future-choice feasibility shield；只做 formulation-level probe，不宣称复现原论文数值。
- `audit_drl_ec3_transfer_fit.py`：静态审计官方 DRL-EC³ emergency-communication environment 是否具备 future-choice transfer 所需结构。
