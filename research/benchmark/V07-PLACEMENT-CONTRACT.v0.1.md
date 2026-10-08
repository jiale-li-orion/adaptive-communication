# Layer-1 v0.7 Placement Contract v0.1

状态：**GATEWAY PRIMARY FROZEN / CENTER SIMULATOR GAP**

机器 authority：`PLACEMENT-VISIBILITY-CONTRACT.v0.1.json`

## 1. 主位置

v0.7 以 gateway-local execution 为主位置。该选择来自 `cache06.md` 已冻结的系统边界：当前关键事实位于 gateway，通信动作也在 gateway 附近执行。它不是为了回避 remote-query cost，也不根据 baseline 成绩选择。

Gateway-local policy 可以直接使用：

- 已发布 obligation / deadline；
- gateway queue 与 send log；
- 已经真实发生的 gateway receipt；
- gateway 持有的 terrestrial / fallback resource ledger；
- 已经到达的 final center ACK / timeout。

它仍然看不到：

- 未来 terrestrial service transitions；
- 未发布任务；
- ACK 到达前的 final center completion；
- evaluator world identity。

`communication.gateway.receipt_summary` 在此位置是 owner-local state projection。它不构成 dedicated communication action，不消耗网络 opportunity，也不继承 center remote-query delay。Gateway-local track 因而研究 natural feedback 下的 send / wait / fallback commitment，不 claim paid remote acquisition。

## 2. Center placement

Center 只作为位置对照，当前明确标为 `SIMULATOR_GAP`。Gateway receipt 在 center 不自动可见；telemetry/query 到达前保持未知。若 query request/response 需要通信路径，center 下发 send/control command 也必须具有：

- outbound required path；
- arrival time；
- timeout / dedupe / acknowledgement；
- 与 data、telemetry、query traffic 的 resource-sharing semantics。

这些对象未冻结前，不运行 center-placement exact/no-query/paid-evidence classification。

## 3. 对 frozen v0.7 universe 的影响

本合同属于 downstream evaluation coordinate，不改 `GENERATION-AXES.v0.2.json`，也不重生成 v0.7 r1。

Gateway-local evaluation 会折叠 query-delay variants，因为 receipt-summary remote delay在该位置不活跃。合法 downstream structure key 为：

```text
base_structure_id
× feedback_profile
× fallback_budget_mode
```

原始 case ID 与完整 provenance 继续保留；折叠只用于 placement-specific exact/baseline 统计，不能回写 generator case count。

## 4. 下一步

```text
frozen v0.7 r1
→ gateway-local structure dedupe
→ blind/open-loop gate
→ full-current causal feasibility
→ gateway natural-feedback feasibility
→ mechanism witnesses / interventions
→ ordinary gateway-local baseline ladder
```

如果 gateway-local natural feedback 已被 blind/open-loop 或 ordinary reserve policy 饱和，应如实降级。不能把 owner-local receipt 重新收费来制造 EvidenceNeed。
