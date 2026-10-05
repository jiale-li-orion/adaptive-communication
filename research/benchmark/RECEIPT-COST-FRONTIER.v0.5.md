# v0.5 Receipt Cost Frontier

状态：机制已成立；当前普通策略族覆盖 frozen 三义务链的完整 query–satellite Pareto 前沿。尚未形成方法性能差额。

## 1. 精确参照

`receipt_cost_frontier_v0_5.py` 在“所有声明世界均按期完成”的硬约束下，不使用加权 reward，直接枚举执行分支合计的：

- remote receipt query 次数；
- satellite send 次数。

只保留非支配点。该实现是小实例 exact reference，不是快速算法。

当前 frozen 三义务链：

```text
exact Pareto = {(10 queries, 13 satellite sends),
                (14 queries,  9 satellite sends)}
```

## 2. 普通策略公平对照

普通中心策略只接收公开任务、时刻表、已执行发送、合法反馈、剩余预算，不读取 hidden outcome / world id / future truth。

策略族包括：

- passive；
- passive + latest-feasible rescue；
- conditional reserve + EDF；
- conditional reserve + latest-feasible rescue；
- fixed batch reads；
- 单个 receipt window fixed read；
- 上述 fixed read 的 latest-feasible rescue 版本；
- gateway-local ordinary rule 作为部署位置对照。

当前 frozen 三义务链：

```text
center ordinary Pareto = {(10, 13), (14, 9)}
gateway-local          =  (0, 9)
```

因此当前 chain 的完整成本前沿已经被小型普通策略族覆盖。不能将 query 减少或条件停止单独升级成算法优势。

## 3. 开发与结构留出协议

`audit_receipt_cost_frontier_v0_5.py` 默认只声明 grid，不执行全量 exact sweep。

### Development

108 cells：

- 4 个既有 geometry phases；
- satellite budget ∈ {1,2,3}；
- query response delay ∈ {60,120,300}s；
- final ACK offset ∈ {-600,0,+600}s。

### Structural holdout

80 cells：

- 从完整 48h geometry trace 中选择 10 个开发集未见的 satellite-window overlap signatures；
- budget ∈ {1,2}；
- query delay ∈ {90,240}s；
- ACK offset ∈ {-300,+300}s。

留出按窗口与义务关系划分，不按 seed、world id 或名称划分。

## 4. 当前边界

本轮只重新对账 frozen chain；没有重新运行完整 188-cell sweep。

Astra 上一轮审查报告过：开发集和结构留出中的可解格均被补全后的普通策略族覆盖。该结论在进入论文结果前必须由当前脚本重新物化；目前 repo 只把可复现协议和 exact/ordinary 对照固定下来。

当前最重要的研究边界是：

> 累计 receipt summary、已知未来时界、单一共享 satellite budget 和当前窗口匹配足以产生真实 EvidenceNeed，但仍可能被很小的 ordinary policy family 完全覆盖。

因此下一步方法工作不能继续靠增加 query 数或阶段数。若要形成算法贡献，必须出现普通 reserve / fixed-read / wait-ACK 无法同时覆盖的**资源条件续接结构**，并且这种结构来自已有通信约束，而不是人为奖励或隐藏 future state。
