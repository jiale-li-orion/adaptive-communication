# Layer-1 Scenario Generator v0.4 — multi-conflict process pilot

状态：method-development pilot / not benchmark release

v0.4 将 v0.3 的单一资源冲突扩展为两个独立时间段的 service conflict，并保留相同的 source-shaped 2 h reporting cadence、真实 Connecta opportunity phase、异步 evidence 和 exact non-anticipative oracle。

默认 4-phase pilot 生成 64 个 bundles：

    NO_PAID_QUERY           16
    SINGLE_QUERY            16
    MULTI_QUERY              4
    INFORMATION_INFEASIBLE  28

三笔账：

- information gap：36 个 exact-solvable bundles 中，20 个没有 paid evidence 无法完成；
- algorithm gap：best single-query 32/36；fixed primary+receipt 36/36；conflict-guided 36/36；
- evidence cost：conflict-guided 平均 0.67 条 query，fixed pair 为 2，always-query-all 为 5；
- computation gap：query-required cases 上 conflict-guided exact search 的 memo work 约为 exhaustive 的 0.54。

当前不能 claim success-rate 优于 fixed two-query baseline。可以 claim 的只是：在保持 exact success 的同时，feasibility-conflict 能减少不必要 evidence acquisition 和 exact evidence-subset search。

下一主线：让 conflict 与 evidence validity 随时间变化，测试 stale evidence、异步到达和阶段性重新取证，而不是继续扩大静态 catalog。
