# Layer-1 v0.7 Placement / Visibility Review v0.1

状态：**CURRENT BLOCKER / ORACLE ADMISSION CLOSED**
机器审计：`results/benchmark/layer1-v0.7-placement-visibility-review.json`
实现：`code/evaluation/benchmark/audit_layer1_v07_placement_visibility.py`

## 1. 结论

v0.7 的 source/trace/generator 资产继续保留，但现有 oracle adapter 不能用于 case classification。它混合了两种互斥 placement 语义：

1. `receipt_summary` 按 center-side remote query 计账，会消耗 terrestrial opportunity/capacity；
2. 同一个 policy history 又自动收到 gateway receipt；
3. case/base/process schema 没有声明 policy placement；
4. center 若需要通信才能查询 gateway，当前 `SEND_TERR` 控制动作却没有对应的 command transport/timing contract。

这违反 `cache06.md` 的 owner/transport 约束：gateway queue、send log 和 received receipt 在 gateway 本地可读；center 只能使用已经到达的 telemetry 或合法 query。查询需要路径时，控制命令也不能瞬时抵达。

因此：

> **现有 v0.7 exact/no-query/paid-evidence pilot 全部不得进入 claim ledger、README 统计或论文表格。**

## 2. 两个合法 placement 必须分开

### Gateway-local placement（主位置）

- gateway queue / send / receipt state owner-local 可见；
- `receipt_summary` local read 不计远程通信成本；
- gateway local-autonomy EDF/reserve 是强 deployment baseline；
- 可研究 send/wait/fallback、异步 ACK 和跨阶段资源承诺；
- 当前版本不能据此 claim paid remote EvidenceNeed。

### Center placement（位置对照）

- gateway receipt 在 telemetry/query 到达前不可见；
- query request/response 遵守 required path、return path、capacity 与 delay；
- center 发出的 send/control command 也必须遵守控制路径和到达时间；
- 若要加入 passive telemetry，必须单独声明 payload、周期/触发、路径和 delay；
- 这些字段冻结前，不运行 center-placement exact admission。

## 3. 对当前 v0.7 的 scoped 处置

v0.7 仍然可以承担：

- process-support correction regression；
- source/geometry/generation coverage；
- gateway-local dynamic mechanism witness 的候选 universe；
- v0.6 blind-satellite shortcut 的反例修复检查。

v0.7 当前不能承担：

- paid-evidence-required hard-case count；
- center-side no-query vs paid-query gap；
- gateway receipt query 的通信节省；
- gateway/center placement 对比结果；
- final exact admission。

## 4. 下一步顺序

```text
frozen v0.7 generated universe
→ freeze placement / visibility / control-path contract
→ gateway-local mechanism witnesses
→ center-placement transport extension（若 source/contract 足够）
→ staged exact admission per placement
→ ordinary-baseline ladder
```

placement contract 属于 evaluation/oracle correctness，不读取 Layer-2/Layer-3 成绩，也不允许按 hard-case 结果调参。
