# Layer-1 Task Coverage & Historical Closure v0.1

状态：`cache06.md` 全文口径的 task-surface / closure authority。  
目的：防止三类反复发生的错误：把 capability 当 task、把历史 O1–O6 当一级 Family、把某个 evidence mechanism 当成整个 benchmark。

## 1. 一级 Family 只有两个

### T1 — Monitoring Information Continuity

主 Family。protected subject 是灾前监测信息持续可用；warning/cadence、outage/reconnect、cache、path、energy、probe、remote config 都只是在同一生命周期中的 regime / capability / hardness axis。

### T2 — Warning Delivery & Response Handoff

边界扩展 Family。protected subject、authority chain 和 completion predicate 已改变为预警发布、送达、确认与 response handoff。当前 source 充分，但 actor-chain environment 尚未完成，因此保持 `SIMULATOR_GAP`，不能拿 T1 sensor-node simulator 硬套。

## 2. T1 实际 task surfaces 与 closure

| Surface | 现实语义 | 历史对应 | Standalone 结论 | 在新 generator 中的角色 |
|---|---|---|---|---|
| S0 Steady Monitoring | 常态周期监测信息按 source contract 可用 | O1 | Conformance / easy regression | 必须保留简单分布，不当 hard task |
| S1 Warning Cadence Transition | authority 发布预警后 cadence 收紧、新义务持续到达 | O2 | 单独 config/control 已在 A7 unique-ready | 作为 workload transition 进入组合生成 |
| S2 Intermittent Backhaul/Fallback | 地面服务间歇，合法 fallback 维持交付 | O3 | 单次 outage+永久恢复、普通双路径已被 reserve/EDF/fallback 吃掉 | 只允许有限、非嵌套机会 + 共享义务重新进入 hardness mining |
| S3 Energy-Constrained Continuity | 低采能/电池压力下维持义务 | O4 | 已有 EnergyAware / dynamic-energy 强基线；不能以旧 O4 声称新颖性 | 作为真实 resource axis，核心机会过程稳定后再绑定 |
| S4 Outage Cache Retention | 断链时至少保持 source-required 本地记录 | O3/O5 | deterministic conformance | 作为状态约束；禁止缩小 7d cache 造难 |
| S5 Recovery Reconciliation | 恢复后补齐合法未完成记录/确认状态 | O5 | A7 standalone control unique-ready；DZT0450 backlog-vs-fresh priority 未定义 | 只有 objective 已定义时进入生成；否则 `OBJECTIVE_AMBIGUOUS` |
| S6 Heterogeneous Path Priority | NB/4G/5G/BeiDou/satellite 等授权路径及 source priority | O3 | 已知 path rule / fallback 自身不是 hard task | 作为 capability/conflict axis，与 partial evidence、机会和共享资源组合 |
| S7 Compound Continuity | 上述义务、状态、机会、恢复和资源在连续 episode 中组合 | O6 | 历史 O6 只证明 runtime conformance，不证明 hardness | **T1 主 compositional generator target** |

结论：O1–O6 不是六个独立 Family。它们提供的是 T1 的 operational surface 与历史 closure 证据。关闭的是旧的 standalone 结构，不是把对应现实机制从 benchmark 删除。

## 3. T2 task surfaces

| Surface | Source | 当前状态 |
|---|---|---|
| Authority-gated publication | Yining | `SIMULATOR_GAP`：缺 warning candidate / verification / publication authority state |
| Hierarchical delivery + ACK | Yining | `SIMULATOR_GAP`：缺 actor graph、多 recipient、retry/alternate contact、handoff |
| Progressive call-response / duplicate suppression | Baoshan 1262 | `SIMULATOR_GAP`：缺 progressive actor-chain + feedback ledger |

T2 后续应做独立 extension environment；不能为了 case 数把它塞进 T1。

## 4. 明确不是 task 的对象

以下对象只能作为 capability / regime / evidence / hardness mechanism：

- `set_sampling_interval` / `set_report_period`；
- cache / retransmission tool；
- NB、4G/5G、BeiDou、satellite 名称；
- `receipt_summary` / `primary_health` / `node_report`；
- remote state/history read；
- probe；
- receipt-race；
- warning level label 本身。

其中 receipt-race / receipt-chain 的正确定位是 H2/H4/H5 **mechanism regression**：它们验证 EvidenceNeed、sequential commitment、passive/probe/query competition 是否真实存在，但不能代表完整 benchmark task taxonomy。

## 5. Generator 不能再只吃 READY 单 profile

旧 `compile_ready_registry()` 只编译 `generator_status=READY` 的单 source profile，会整份丢掉：

- `DZT0450`：虽然 `reconnect_backlog_priority` 未定义，但 7d cache、disconnect/reconnect lifecycle、satellite capability、remote control 等 primitive 都已 source-resolved；
- `DB11/T1677`：虽然 upper-platform communication completion deadline 未定义，但双通道、5min 场景 endurance、battery/signal/mode visibility 与 dry/rain acquisition cadence 都是真实 primitive。

新规则：

> **Task authority 必须完整；support primitive 可以来自 partial profile 的已解决部分；UNRESOLVED answer-relevant 字段永不采样。**

因此 source profiles 的角色要拆成：

1. `TASK_AUTHORITY_RESOLVED`：可直接生成 obligation semantics；
2. `RESOLVED_PRIMITIVE_SUPPORT`：可贡献 capability / envelope / state mechanism；
3. `TASK_AUTHORITY_WITH_OBJECTIVE_GAP`：只在不依赖缺失 objective 的组合中使用；
4. `BLOCKED_BY_SOURCE_GAP`：对应语义禁止进入 generator。

## 6. T1 compositional generator 的固定覆盖维度

最终 T1 generator 至少要能组合：

```text
multi-obligation release/deadline
× warning-driven workload transition
× finite non-nested terrestrial opportunities
× intermittent satellite opportunities
× shared real resource/capacity
× outage cache/recovery state
× legal partial evidence + async ACK/query feedback
```

在核心过程稳定后，再加入：

```text
source/trace-grounded energy pressure
future authority-published warning transition
```

这些维度来自同一 T1 Family 的真实机制，不是额外 task taxonomy。

## 7. 历史 closure policy

以下已关闭结构不再单独重跑为论文 hard task：

- unique-ready TaskContract / config install；
- one-shot permanent terrestrial recovery；
- ordinary outage + two-path fallback；
- standalone cache retention；
- generic recovery TTL / config TTL；
- receipt-race 两义务机制本身；
- historical O1–O6 deterministic conformance episodes。

但它们必须继续保留为：

- easy / conformance split；
- regression；
- intervention control；
- compositional generator 的真实 primitive。

只有**新组合后的 scenario bundle**重新通过 V0–V9、strong baseline、structure-heldout 后，才能获得新的 hardness / `BENCHMARK_ADMIT` 身份。

## 8. 当前真正未完成的 Layer-1 工程

```text
Task-surface registry / closure               DONE
Resolved primitive catalog                    DONE
T1 compositional scope                        DONE
T2 simulator-gap declaration                  DONE

下一步：
source-profile + primitive composition
→ large candidate bundle universe
→ observation/evidence process
→ exact oracle
→ V0–V9
→ shortcut/strong-baseline mining
→ structural split
→ Q0–Q12 release gate
```

现在不能再用 188 个 receipt timing/resource cells 代表 Benchmark。188 只是一个 mechanism/process audit grid。
