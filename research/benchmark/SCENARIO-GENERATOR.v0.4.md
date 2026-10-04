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
- computation gap：delivery-constraint witness 接入后，query-required cases 上 conflict-guided exact search 的 memo work 约为 exhaustive 的 0.274；另单独报告平均 12 次 lightweight max-flow structural solves。

当前 evidence values 由决策时刻已经存在的 gateway 状态 / 过去反馈投影生成：

- primary_health：last-forward age、pending depth、oldest pending age、query reachability；
- receipt_summary：recent receipt count、last receipt age、missing receipt count；
- node_report noise：当前设备状态摘要。

query 返回值不包含 future opportunity、obligation ID、oracle witness 或 “which report needs satellite” 类答案标签。当前事实与未来有限服务窗口之间的相关性属于显式 CONTROLLED_STRESS 状态转移模型。

当前不能 claim success-rate 优于 fixed two-query baseline。可以 claim 的只是：在保持 exact success 的同时，feasibility-conflict 能减少不必要 evidence/context selection 与 exact evidence-subset search；是否构成论文级算法贡献仍需后续方法审查。

当前 v0.4 作为多冲突 process pilot 冻结。进一步的时间变化 conflict / freshness / learning 扩展不在本文件预先定案；后续以最新 cache06 与 reviewer/Astra 方法审查为准。

## Contract closure update

Current v0.4 mainline now additionally enforces:

- gateway evidence is aggregated from an explicit pre-decision forwarding / queue / receipt event log rather than directly exposing the latent service label；
- primary_health / receipt_summary / node_report query contracts freeze owner, required path, return path and opportunity dependency from the tracked communication capability registry；
- gateway reachability failure produces query timeout rather than hidden-state access；
- passive telemetry is an exogenous observation path in the same non-anticipative scenario tree；
- normal terrestrial delivery ACK may partition alias worlds and therefore remains available as send-as-probe；
- incremental conflict context consumes the same current JSON evidence contract as v0.4 and reuses cached world feasibility witnesses；
- irreversible satellite commits expose conservative structural feasibility bounds：common-opportunity feasibility is a lower bound and per-world feasibility is an upper bound；ambiguous L=0,U=1 actions remain for exact continuation search。

These changes close mechanism contracts only. They do not change the existing negative result that fixed primary_health + receipt_summary still matches conflict-guided success rate on the current pilot, and remote-read transport bytes / airtime / energy remain unmodeled.

### Strong deterministic baselines

On the 36 exact-solvable v0.4 pilot bundles:

- no-paid-query exact: 16 / 36；
- myopic conflict-separation-per-latency, one paid query maximum: 32 / 36；
- depth-2 belief/evidence planner, at most two paid evidence capabilities: 36 / 36；
- fixed primary_health + receipt_summary: 36 / 36；
- conflict-guided: 36 / 36。

Therefore current v0.4 has no task-success headroom over a two-evidence limited-depth planner. The retained method signal is conditional evidence/context/search reduction, not higher completion rate.
