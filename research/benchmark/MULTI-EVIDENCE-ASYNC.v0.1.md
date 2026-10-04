# Multi-Evidence Async Contract v0.1

状态：benchmark/method infrastructure

这一层只解决信息能力契约，不声明 benchmark hardness。

## 已支持

- 多个 owner-scoped evidence query；
- query issuance 与 data send 异步并行；
- query response 到达时才分裂 alias worlds；
- 相同 observation history 保持 non-anticipativity；
- normal transmission ACK 仍参与 observation；
- evidence subset 可单独启用/禁用；
- 单一 sufficient query、冗余 query、互补 query、无关 query；
- 并行 query 的时间代价按 critical-path delay，而非 delay 求和。

当前用于机制测试的 capability IDs：

- communication.gateway.primary_health
- communication.gateway.receipt_summary
- communication.gateway.node_report

它们沿用已有 capability owner/semantics，不新增设备能力。

## 回归性质

1. 发出长延迟 query 不会自动错过当前 satellite send opportunity。
2. 若只有 primary_health 能消除 feasibility conflict，planner 只选 primary_health。
3. 若只有 receipt_summary 能消除 conflict，planner 只选 receipt_summary。
4. 若两者都能单独解决，优先选择 critical-path 更短的 sufficient query。
5. 若 single query 都不足但二者组合足够，返回 MULTI_QUERY。
6. 无关 node_report 不因 catalog 中存在就被查询。
7. 没有任何 evidence subset 能恢复共同策略时，返回 INFORMATION_INFEASIBLE。

下一步：用 feasibility-conflict structure 对 evidence subset search 做剪枝，比较 exact subset enumeration 的搜索量与相同决策质量。

## Conflict-guided subset search

当前 evidence subset search 只做可证明安全的静态剪枝：

- constant query：对当前 alias set 不产生任何 partition；
- dominated query：同 owner、无额外显式资源成本、返回不更早，且另一个 query 的 partition 至少同样细。

其它 query 不因 heuristic score 被删除。

剩余 query 只按“分离多少 direct-action conflict pair”排序；排序影响搜索效率，不影响 correctness。

在当前 4 个机制回归 case 上：

    unstructured non-empty subsets = 28
    conflict-guided exact subset solves = 6

最终 evidence plan 与 reference exact subset search 一致。

该结果仅验证剪枝/排序机制；catalog 只有三个真实已登记 gateway evidence capability，不能作为规模性结果。
