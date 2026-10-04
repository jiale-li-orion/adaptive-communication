# Layer-1 Scenario Generator v0.1

状态：tracked generator authority / pre-release
生成器 ID：T1_ESCALATION_RESOURCE_COUPLING_V0

## 1. 目标

这一版 generator 不再等待现实资料替 benchmark 写出完整 hard case。

现实 source 负责定义：
- Operational Family；
- warning / monitoring state；
- source cadence；
- 合法 capability；
- site / geometry；
- payload class；
- completion predicate；
- authority boundary。

Generator 负责在这些 primitives 内构造受控的、可审计的时序组合，用 oracle/validity filter 筛出真正有决策价值的 cases。

核心目标是生成 T1 Monitoring Information Continuity 的 H4 候选：

当前是否消耗稀缺 satellite resource，会改变 warning escalation 后未来 obligation 的可满足性。

## 2. Claim boundary

Generator v0.1 只允许以下 claim：
- source-backed task semantics；
- source-backed path existence / payload / site / geometry input；
- controlled stress 下的 decision-validity / resource-coupling properties；
- exact oracle 与 ordinary baseline 的可重复比较。

禁止：
- 把 controlled outage / satellite budget 写成广东现场统计分布；
- 把 model-derived visibility 写成 measured contact；
- 用 evaluated model 的结果调 generator 轴；
- 为了得到困难 case 修改 source cadence、authority、payload 或 completion predicate；
- 用任意 reward weight 决定牺牲哪个 obligation。

## 3. Frozen input bundle

Generator 只从 tracked bundle 读取：
- research/benchmark/profiles/v0.1/
- research/benchmark/traces/v0.1/
- research/benchmark/PROFILE-BUNDLE-MANIFEST.v0.1.json
- research/benchmark/GENERATOR-CONFIG.v0.1.json

Profile bundle 变更必须生成新 bundle hash；generator config 变更必须升级 generator version。

## 4. Source-backed primitives

Task：DB44T2457_2024_warning_reporting。
提供 monitoring grade、warning state、state-specific reporting cadence range、timely-complete-report completion semantics。

Site：GUANGDONG_SIHUI_HIGH_SCHOOL_LANDSLIDE。
提供广东 jurisdiction、真实滑坡隐患点、政府隐患登记坐标、历史远程滑坡监测 field evidence、DEM-derived observer altitude。

Capability：PLAN_S_CONNECTA_IOT_MODULE_D2S。
提供 terrestrial LoRaWAN、Connecta direct-to-satellite LoRa/LR-FHSS、TLE-based wake-up、satellite payload <= 51 B。

Payload：DZT0450_TYPE1_SINGLE_SENSOR_EXAMPLE。
提供 exact 32 B Type-1 real-time single-sensor source example。

Opportunity trace：CONNECTA_20260922_SIHUI_GEOMETRY_48H。
提供 pinned Connecta TLE、SGP4、四会 field-site geometry、48 h / 60 s visibility windows。
Geometry 不等于 service success。

## 5. Controlled generator axes

所有 controlled axes 在生成前冻结，不根据模型结果修改。

Warning transition 只生成单调升级：
- blue -> yellow
- blue -> orange
- blue -> red
- yellow -> orange
- yellow -> red
- orange -> red

pre/post cadence 都来自同一 DB44 grade 的 source table boundary values。

transition_fraction_of_pre_deadline：
- 0.25
- 0.50
- 0.75

warning transition time = fraction × pre-warning report deadline。

recovery_lag_post_intervals：
- 1.25
- 1.75
- 2.50

terrestrial outage 从 scenario start 开始；
recovery = warning transition + lag × post-warning interval。

结构筛选要求：

    first post-warning deadline < terrestrial recovery < pre-warning deadline

因此：
- pre-warning routine report 可以合法等待 terrestrial recovery；
- first urgent post-warning report 不能等待 recovery；
- satellite resource consumption 可能影响未来 feasibility。

satellite_tx_budget_count：
- 1
- 2
- 3

这是 CONTROLLED_STRESS，表示 scenario horizon 内可消费的 normalized satellite-send budget。
它不是套餐 quota，也不是 field-calibrated battery count。

post_obligation_count：
- 2
- 3
- 4

用于生成 multi-obligation temporal coupling。

elevation mask：
- 5°
- 10°
- 20°
- 30°

全部标 CONTROLLED_STRESS；不声称是真实 terrain skyline。

每个 structural coordinate 在可容纳 scenario span 的 trace 区间内做固定数量的等距 phase bins。
phase sampling 不随机、不按模型失败点回采，每个 bin 由 scenario span + frozen trace horizon 唯一决定。

## 6. Service abstraction

terrestrial：
- outage 期间不可用；
- recovery 之后可用；
- 每个 trace step 最多发送 terrestrial_reports_per_step 份 fitting report。

satellite：
- 只有 model-derived geometry visible step 才有 candidate slot；
- 每个 visible step 最多发送 satellite_reports_per_visible_step 份 fitting report；
- 每次 satellite report 消耗 1 个 normalized satellite budget；
- v0.1 service success 使用 named upper-envelope stress semantics。

这组 abstraction 用于 decision-validity mining，不用于 field reliability claim。

## 7. Obligation structure

每个 candidate 包含：
1. 一个 pre-warning monitoring obligation：release = scenario start；deadline = pre-warning source cadence。
2. N 个 post-warning obligations：first release = warning transition；recurrence = post-warning source cadence；每个 deadline = release + post-warning cadence。

所有 obligations 必须全部满足，因此无需人工 priority/reward。

## 8. Exact oracle

v0.1 oracle 解离散 unit-report scheduling feasibility。

每个 obligation 可分配到 terrestrial service slot 或 satellite service slot。

约束：
- release <= delivery <= deadline；
- 每个 slot capacity 有限；
- satellite path 受 total budget；
- 每份 report 只完成一次。

Oracle 枚举 obligation -> path subset，再对每类 path 做 deadline-feasible slot assignment。

输出：
- solvable / infeasible；
- feasible path-assignment count；
- witness plan；
- satellite budget binding；
- forced-send / forced-wait counterfactual；
- ordinary baseline outcomes。

Oracle 不输出 scalar reward。

## 9. Generator-side validity mining

Generator 可以根据 oracle 属性筛 candidate，但不能根据模型表现筛 candidate。

v0.1 hard candidate 要求：
- V0 source/profile complete；
- V1 oracle solvable；
- V2 first decision 有 send routine by satellite 与 wait 两个 legal options；
- V5 satellite resource actually binding；
- V6 forced early satellite send 与 wait 产生不同 future obligation feasibility；
- V8 ordinary greedy fallback 在该 case 上失败，而 oracle 成功；
- objective unambiguous：所有 obligations 同时可满足。

未通过的 candidate 不删除；manifest 统计 disposition。

## 10. Anti-gaming / leakage rules

- generator config 在 policy evaluation 前冻结；
- hard-case mining 不读取任何 LLM / RL / learned-policy score；
- source cadence / trace / site / payload 不因为模型结果改变；
- candidate ID 是 canonical coordinates 的 hash；
- near-duplicate group key 不包含 trace phase；
- final split 必须按 structural group 分组，不能把同一结构不同 phase 随机拆到 train/test；
- benchmark release 记录 raw candidate count、各 gate 淘汰数与最终 case count。

## 11. 当前不是最终 benchmark

Generator v0.1 的目标是找到并冻结有效的 H4 candidate distribution。

之后仍要完成 V9 evaluator mutation audit、held-out split、near-duplicate/contamination audit、source/expert audit、baseline ladder、statistical reporting plan。

完成这些之前不标 BENCHMARK_ADMIT。
