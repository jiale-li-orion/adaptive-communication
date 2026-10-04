# Layer-1 Evidence / Context / Computation Accounting v0.1

状态：tracked accounting authority

## 1. 三笔账必须分开

### Local context/read

当 evidence owner 与 planner 部署位置相同：

- 计 local read / context selection；
- 不计 remote network acquisition；
- 仍可单独计 context bytes / planner compute。

例：gateway-owned primary_health 对 gateway-resident planner 是本地读取。

### Remote evidence acquisition

当 evidence owner 与 planner 部署位置不同：

- 计 remote acquisition request；
- 使用 CapabilityResult 中真实 latency / network_bytes / airtime_s / energy_wh；
- simulator 未提供 transport cost 时保持 unknown，不补 0。

例：gateway-owned primary_health 对 center-resident planner 是远程取证。

### Planner/search computation

独立记录：

- evidence subset solves；
- conflict preprocessing solves；
- memo / expanded policy-tree nodes；
- materialized context bytes；
- planner/model calls。

这些不能与通信开销相加成任意 scalar reward。

## 2. Freshness / expiry

复用 CommunicationEvidence：

- generated_at_s；
- observed_at_s；
- owner_location；
- freshness metadata。

每个决策依赖单独声明：

- proposition；
- subject；
- max_age_s；
- freshness basis。

Evidence 超过 freshness bound 后只意味着：

    当前 context dependency 失效

不自动意味着：

    必须发起远程 query

后续动作仍须比较：

- owner-local reread；
- passive telemetry；
- normal send / ACK as probe；
- remote acquisition；
- wait。

## 3. v0.4 placement audit

36 个 exact-solvable bundles：

Conflict-guided selected evidence：24 total，mean 0.667 / case。

### Planner at gateway

- conflict-guided：24 local reads，0 remote acquisitions；
- fixed pair：72 local reads；
- query-all：180 local reads。

因此这里可以 claim context/evidence selection reduction，不能 claim network traffic reduction。

### Planner at center

- conflict-guided：24 remote acquisitions；
- fixed pair：72 remote acquisitions；
- query-all：180 remote acquisitions。

当前 simulator 没有为这些 gateway-owner reads 提供真实 transport bytes / airtime / energy，所以只能报告 request count；network cost 保持 unknown。

## 4. Claim boundary

当前 accounting 支持：

- owner-relative locality；
- freshness expiry；
- local/remote/computation 三账分离；
- placement-sensitive evidence-count comparison。

当前 accounting 不支持：

- 把 gateway-local read 写成通信开销；
- 把 unknown transport cost 写成 0；
- 用 query count 代替真实 bytes / airtime / energy；
- 把 planner memo nodes 与 network cost 相加为单一 reward。
