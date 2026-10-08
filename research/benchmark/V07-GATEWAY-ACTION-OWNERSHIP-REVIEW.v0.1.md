# Layer-1 v0.7 Gateway Action-Ownership Review v0.1

状态：**BLOCK GATEWAY EXACT ADMISSION / DATA-LOCATION + ACTION-OWNERSHIP CONTRACT OPEN**

机器结果：`results/benchmark/layer1-v0.7-gateway-action-ownership-review.json`  
上位依据：`cache06.md`、`research/substrate/SYSTEM-MODEL-v1.md`、`PLACEMENT-VISIBILITY-CONTRACT.v0.1.json`

## 1. 新发现的问题不是 placement 本身，而是 placement 后的 action 仍沿用了旧端到端抽象

`SYSTEM-MODEL-v1.md` 已经把数据生命周期分成两段：

```text
sensor/node uplink
→ gateway hears/queues record
→ primary backhaul / gateway backup
→ center delivery
```

其中 node uplink 成功由 `U_{i,t}=1` 表示；gateway 另有独立 queue `G_t` 与 primary backhaul state `P_t`。最终 monitoring obligation 的完成判据是 sample 在 deadline 前到达 center。

历史 v0.5 `receipt-race` 也沿用同一事件顺序：

```text
normal terrestrial send
→ gateway-local receipt
→ final center ACK
```

因此旧 `SEND_TERR` 是一个跨越“尚未到 gateway → gateway 已收到 → center 最终交付”的抽象 delivery attempt。它最初与 center-side policy / receipt query 一起使用。

v0.7 placement 修正正确地指出 gateway receipt 是 gateway owner-local state，不能收费为 center remote query；但 `layer1_v07_gateway_oracle_adapter.py` 同时又把 `SEND_TERR / SEND_SAT / WAIT` 声明为 gateway-local execution。exact kernel 随后在执行 `SEND_TERR` 后才生成未来 `gateway_receipt_at_s`。

这两件事不能同时成立，除非另外声明“gateway 如何驱动尚在 node 的 report 发起 uplink”的控制路径。当前 contract 没有这个对象。

## 2. 当前缺的不是一个字段，而是数据位置与动作阶段

gateway-local 主位置仍然合理，但合法 action surface 需要按 report 所在位置拆开。至少要区分：

```text
report not yet released / at sensor
report generated at sensor
report received / queued at gateway
report in gateway→center forwarding
report center-delivered
```

随后才能定义：

- node→gateway uplink 是 source/report schedule 触发的自然事件，还是 gateway 可控动作；
- 若 gateway 可以控制 uplink，对 node 的命令如何到达、何时生效；
- gateway 已持有 record 后，primary backhaul forwarding 与 fallback forwarding 分别是什么 action；
- gateway receipt 与 center ACK 分别更新哪一个 location/obligation state。

在这些对象闭合前，把旧 `SEND_TERR` 直接解释成 gateway-local action 会混淆 execution owner 与 receipt owner。

## 3. 对刚完成的 36-cell gateway pilot 的处置

36-cell bounded pilot 仍有诊断价值：它已经暴露了 `SINGLE_RECOVERY` blind-easy / `REINTERRUPTIBLE` causal-infeasible-or-shortcut 的二分，并且 second-outage intervention 可定位该二分的一部分结构来源。

但这批结果现在必须降级为：

> **provisional-kernel diagnostic, not gateway deployment admission evidence.**

它不能支撑“gateway-local benchmark 已完成 staged exact admission”“gateway deployment 下没有 hard case”或任何实际通信成本结论。修正 action/data-location contract 后需要重新运行。

## 4. 下一步顺序

```text
freeze report/data-location lifecycle
→ freeze gateway-local legal action ownership
→ audit causal event ownership / timing
→ adapt exact kernel without changing source task or public geometry
→ rerun small bounded pilot
→ only then discuss dynamic hardness
```

这不是为了制造 hard case。它是 `SYSTEM-MODEL-v1` 与 gateway placement 之间的 correctness closure；即使修正后全部变 easy，也应接受该结果。
