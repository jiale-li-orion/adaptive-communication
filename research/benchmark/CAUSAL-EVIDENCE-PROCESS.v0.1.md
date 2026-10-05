# Causal Observation / Evidence Process v0.1

状态：**CURRENT / Layer-1 construction stage complete**
父对象：`DYNAMIC-WORLD-MATERIALIZATION.v0.1.md`
实现：`code/evaluation/benchmark/causal_evidence_process_v0_1.py`

## 1. 这一层解决什么

world materialization 冻结 physical alias set；本层冻结信息怎样合法到达 policy history：

```text
physical world state
→ owner-local state at sampled_at
→ acquisition / execution event
→ transport / delay
→ arrived_at observation
→ alias-set partition
```

它仍然不判断 world 是否可解，不产生 gold action，不运行 V0–V9。58,752 个 world bundle 各产生一个 causal evidence process，输出状态为 `CAUSAL_EVIDENCE_PRE_ORACLE`。

## 2. Non-anticipativity

query response 只允许包含 `sampled_at_s` 时已经成立的 current/past owner facts。当前 `gateway_state_summary` 返回：

- `terrestrial_available_now`；
- 已开始 service-window 数；
- 已结束 service-window 数；
- 最近一次结束窗口距 sample time 的时间。

response 明确禁止包含 future window count、next-window start、未来 delivery success、recommended action、world id。world 在 sample 后、response 到达前继续变化时，已经采样的 payload 不得被后来状态重写。

当前 timing 采用统一 `CONTROLLED_STRESS` contract：query sample delay 0 s、response/timeout 60 s。它用于检验 acquisition delay 与 opportunity/resource coupling，不声称是现场典型控制面时延。

## 3. Passive ACK 与执行因果

passive evidence 只由真实执行触发：

```text
SEND_TERR executed
→ service window / capacity accepts or rejects
→ accepted: gateway receipt at t+10s
→ final completion ACK at t+30s

rejected:
→ no gateway receipt
→ no final ACK
→ negative observation / timeout at t+60s
```

三个 delay 同样属于 `CONTROLLED_STRESS`。这里冻结的是因果顺序和事件分离：gateway receipt 证明 gateway 已收到，final ACK 才能证明当前抽象中的 center completion；二者不能合并成一个提前成功事件。

没有执行 SEND 时，runtime 不生成 hypothetical ACK。这样可以防止 evaluator 把“如果你发送会成功”提前泄漏给 policy。

## 4. Normal send-as-probe

`MIXED_PASSIVE_QUERY_PROBE` 不新增 probe API。normal send-as-probe 使用正常 `SEND_TERR` 动作、正常 reporting payload、正常 service capacity；其 ACK/timeout 同时承担 delivery consequence 与 evidence consequence。

因此 send-as-probe 的 acquisition cost 不另计一份 tool cost，但它真实消耗本次 delivery opportunity。后续 oracle 必须在同一个 resource ledger 上处理“完成当前义务”和“通过执行获得信息”。

## 5. Owner query 的资源语义

`GATEWAY_SUMMARY_QUERY` / `MIXED_PASSIVE_QUERY_PROBE` 暴露一个 `gateway_state_summary` owner query。query 依赖 higher-priority terrestrial path，并声明消耗一个 terrestrial opportunity-capacity unit。这个 cost 是 `CONTROLLED_STRESS`，用于阻止“免费远端读状态”把 EvidenceNeed 退化成无成本 oracle read。

query 在 sample time 路径不可达时返回 timeout；路径可达时返回当时的 state-grounded snapshot。query 自身不会返回未来 service schedule。

## 6. 四种 evidence regime

```text
FULL_OBSERVATION_CONTROL
    direct current state; no owner query

PASSIVE_ACK_ONLY
    execution-triggered delivery ACK / timeout

GATEWAY_SUMMARY_QUERY
    paid owner query; no passive ACK acquisition surface

MIXED_PASSIVE_QUERY_PROBE
    owner query + passive ACK + normal SEND_TERR as probe
```

这些是 observation-process regime，不是 task Family。后续 V3/V4 会判断 alias set 是否真的需要这些 evidence；如果 common-safe action 已存在或 evidence 不改变 feasible plan set，对应 bundle 降为 conformance/regression。

## 7. 冻结 manifest

```text
58,752 parent world bundles
→ 58,752 causal evidence processes

owner-query enabled : 29,376
owner-query disabled: 29,376
passive-ACK enabled : 29,376
passive-ACK disabled: 29,376
```

机器快照：`results/benchmark/layer1-causal-evidence-v0.1.json`。

## 8. 下一阶段

下一阶段固定为 `EXACT_ORACLE_REFERENCE_LABELS`。oracle 需要消费 world + evidence process 的同一执行语义，并分别构造：

- physical / hindsight feasibility reference；
- full-current-state feasibility；
- observation-matched exact policy；
- observation-matched no-paid-query policy。

只有 oracle 产生合法 plan/terminal witness 后，V1–V7 才能判断 solvability、common-safe-action、EvidenceNeed、binding constraint、outcome separation 与 objective ambiguity。当前 58,752 processes 仍不是 benchmark cases。
