# Layer-1 v0.6 Oracle Adapter v0.1

状态：**CURRENT PRE-ADMISSION ORACLE CONTRACT**  
输入：official `layer1-v0.6-preoracle-r4`  
实现：`code/evaluation/benchmark/layer1_v06_oracle_adapter.py`

v0.6 不重写一套新的 exact planner。它复用已经过 v0.2 correctness/regression 审计的 non-anticipative AND/OR kernel，只参数化 r4 已冻结的新 evidence/timing 语义。

## 1. 保留的旧 correctness 语义

- compatible worlds 共享同一 observable history 时必须执行同一动作；
- query 与 `SEND_TERR` 消耗同一 terrestrial opportunity-capacity ledger；
- `SEND_TERR` 可以作为 normal probe，但不获得额外免费 tool；
- satellite window capacity 与 global fallback budget 同时约束；
- pending query / receipt / ACK 通过事件时间进入历史；
- full-current-state 只免费暴露当前状态，不暴露未来 service transition；
- hindsight physical feasibility 与 causal policy feasibility 分离。

## 2. v0.6 参数化

Dedicated query 的 payload 从旧 `gateway current-state summary` 改为冻结的：

```text
communication.gateway.receipt_summary
```

它只返回 sample time 已经真实发生的 gateway receipts；不得返回当前/未来 service state、未来 satellite opportunity、world ID 或 recommended action。query 是否能返回仍受当下 terrestrial path/capacity 约束，因此 timeout 本身是合法 transport feedback。

Case-specific timing直接读取 r4：

- `gateway_receipt_delay_s`；
- `final_ack_delay_s`；
- `remote_query.response_delay_s`。

## 3. 无新增自由度的派生规则

r4 没有另设三个独立 timing axes。为避免把旧常量偷偷带进新 benchmark，oracle 使用确定性派生：

1. failed `SEND_TERR` 的 negative timeout deadline = case 的 expected final-ACK delay；
2. unreachable remote query 的 timeout deadline = case 的 query-response delay；
3. satellite completion delay = `0`，因为 r4 physical matching 已把 model-derived satellite opportunity timestamp 当作 completion opportunity；旧 oracle 的固定 `+5s` 不得跨版本继承。

这三条不引入可调参数，也不根据 baseline/method 结果变化。若后续 source/physical model要求独立 timeout/completion delay，必须开启新的 generation/oracle contract version，不能原地调数。

## 4. 四个 reference

每个 `ALL_WORLD_PHYSICAL` case 先计算：

1. `FULL_CURRENT_STATE`：当前真实 service + execution state 免费可见，未来仍未知；
2. `OBSERVATION_MATCHED_EXACT`：只用自然反馈 + receipt-summary query；
3. `OBSERVATION_MATCHED_NO_PAID_QUERY`：保留 ACK/send-as-probe，禁 dedicated query；
4. `BLIND_OPEN_LOOP_REFERENCE`：禁 paid query，也隐藏 passive feedback，只允许固定于时间/history-independent 的 execution。

后续 admission 只根据这四参照和独立 baseline/filter 结果分类，不反向修改 r4 generator。

