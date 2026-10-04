# Feasibility-Conflict-Guided Evidence Planner v0.1

状态：mechanism method / deterministic reference implementation

## 1. 方法对象

输入不是完整 hidden world，而是当前合法 observation history 对应的 alias bundle。

方法只回答三个问题：

1. 当前是否存在 observation-matched 的共同成功直接动作；
2. 如果没有，哪些隐藏差异真正改变后续 obligation feasibility；
3. 哪条合法 owner evidence 能及时消除该冲突。

它不把所有未知字段都转成 EvidenceNeed，也不按字段做独立 importance score。

## 2. Feasibility conflict

对当前可执行 direct action a：

- Lower bound L(a)=1：强制 a 后，整个 alias bundle 仍存在一棵 non-anticipative 成功策略；
- Upper bound U(a)=1：即使随后立刻知道 hidden world，a 在每个 world 中仍然可能成功。

因此：

    L(a) <= Q*(h,a) <= U(a)

若存在 L=1 的动作，就不需要为了当前决策主动补信息。

若所有 direct action 的 L=0，同时某些 action 的 U=1 且其支持 world 不同，则当前存在 feasibility conflict。

## 3. EvidenceNeed

当前 v0.1 只接已有合法 proposition：

    communication.gateway.primary_health

owner：

    gateway

EvidenceNeed 只有同时满足以下条件才打开：

- 当前存在 feasibility conflict；
- query 能区分至少两个 alias partition；
- query latency 进入物理时间；
- 强制 query 后存在 observation-matched 成功策略。

query 不及时、无区分度或不能恢复任务可行性时，不标 resolving EvidenceNeed。

## 4. Passive evidence

主动 query 之前先检查：

    WAIT + no paid query

是否已经存在共同成功策略。

如果正常 ACK / 已有遥测 / passive evidence 能及时消除冲突，则等待免费信息优先于额外 query。

这避免把独立 query 的收益建立在剥夺普通机制反馈之上。

## 5. Incremental context

context 只保留：

- Operational obligations；
- 当前 satellite budget；
- 已公开 satellite opportunity schedule；
- 当前 feasibility conflict；
- resolving owner evidence contract；
- query delay。

owner evidence 返回后，仅过滤与返回值不一致的 alias worlds，然后重新计算受影响的 conflict/evidence slice。

不把 hidden mode、world id 或 oracle witness materialize 给策略。

## 6. 当前机制结果

在 Generator v0.2 的 72 个 mechanism bundles 上：

- QUERY_REQUIRED 24：全部识别 gateway resolving EvidenceNeed；
- QUERY_HARMFUL 24：不选择 resolving query；
- PASSIVE_BETTER 24：等待 passive evidence；
- deterministic first-step policy 72/72 保持 exact success。

这只是机制正确性，不是算法优势 claim。

当前 v0.2 仍被一个 depth-2 timing rule 72/72 覆盖，因此不能据此声称 planner 优于普通规则。

## 7. 下一阶段

方法价值需要在更一般的 process-generated distribution 上验证：

- 多个 evidence source / capability；
- evidence 重叠与互补；
- 多个 resource conflict；
- 异步、可并行 query；
- query / normal send / ACK 共享真实成本；
- 不同 conflict 只需要部分 evidence。

届时重点测三笔账：

1. information value；
2. algorithm gap；
3. computation/search reduction。

学习方法只考虑用于搜索顺序、界估计或 context 表示，不拥有 legality / authority / execution truth。
