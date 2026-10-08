# T1 Gateway Data-Lifecycle / Action-Ownership Contract v0.1

状态：**FROZEN PRE-ORACLE / GATEWAY BACKHAUL SCOPE**

机器合同：`T1-GATEWAY-DATA-LIFECYCLE-CONTRACT.v0.1.json`

## 1. Scope 不再含糊

Gateway 主轨对应现有 task registry 的 `T1.S2_INTERMITTENT_BACKHAUL_FALLBACK`，并可作为 `T1.S7_COMPOUND_CONTINUITY` 的通信子层。它研究的是：

> 已经进入 gateway queue 的 monitoring record，在 primary backhaul 间歇中断、fallback 有限、deadline 继续推进时，gateway communication subsystem 怎样保持 required-platform delivery obligations 可完成。

这个 scope 不把 node→gateway access 从完整系统删除。它只是把 access 放到当前 benchmark slice 的入口边界。`SYSTEM-MODEL-v1.md` 已经明确：node uplink 被 gateway 听到和 gateway primary backhaul 是两个物理阶段；当前先把后一个阶段做正确。

## 2. 数据位置是一等对象

主轨至少区分：

```text
UPSTREAM_OF_GATEWAY
        │ gateway receipt（自然/执行事件，不是 gateway policy action）
        ▼
GATEWAY_READY
   ├── FORWARD_PRIMARY  → PRIMARY_IN_FLIGHT  ── ACK/timeout ──┐
   └── FORWARD_FALLBACK → FALLBACK_IN_FLIGHT ─ completion ────┤
                                                               ▼
                                                       CENTER_DELIVERED
```

Monitoring obligation 的 source release/deadline 不因这个 scope 被改写；gateway receipt 也不等于 obligation completion。完成仍由 required center/platform delivery 判定。

## 3. Gateway policy 真正拥有的动作

Gateway-local policy 的最小合法动作面改为：

- `FORWARD_PRIMARY(obligation)`；
- `FORWARD_FALLBACK(obligation)`；
- `WAIT`。

`FORWARD_PRIMARY` 消耗 primary backhaul opportunity/capacity；`FORWARD_FALLBACK` 只能使用来源允许的 fallback，并消耗声明的 fallback opportunity/budget。二者都只能作用于已经 `GATEWAY_READY` 的 record。

历史 `SEND_TERR` 不能直接继续出现在 gateway action surface。它原本跨越 send → gateway receipt → center ACK。若未来 end-to-end benchmark 要让 gateway 控制 node uplink，必须另外声明 gateway→node command/access transport 和 node-side execution；当前不能从“gateway placement”自动推导出这份 authority。

## 4. Evidence 边界

Gateway 本地可见：queue、record location、send log、local resource ledger，以及实现确实能立即知道的 local execution result。它们不算 remote acquisition。

异步到达：center ACK、timeout/negative completion feedback、来源明确给出的 telemetry。

始终隐藏：未来 primary service transitions、未来 execution success、evaluator world id。

这意味着 gateway 主轨不再需要 `receipt_summary` 作为 paid query；gateway receipt 是进入 backhaul slice 前的数据位置事件。

## 5. 对 v0.7 frozen universe 的兼容边界

可以继续保留：

- source-owned monitoring obligations 与 deadline；
- public Connecta geometry；
- primary opportunity/capacity topology，只要明确解释为 gateway→center primary backhaul；
- fallback budget derivation，在后续 ownership replay 通过的前提下；
- recovery/reinterrupt support 作为 process candidate lineage。

不能静默复用：

- `gateway_receipt_delay_s` 作为 gateway forwarding 后的反馈；
- `SEND_TERR → future gateway receipt` transition；
- 任何隐含的 gateway→node command authority。

因此下一步不是重做百万 case。先做一个 corrected gateway execution IR，在极小 bounded slice 上验证 data-location、action ownership、ACK/timeout 和 resource ledger；通过后再决定 v0.7 universe 哪些轴可以合法投影复用、哪些必须版本化重生成。
