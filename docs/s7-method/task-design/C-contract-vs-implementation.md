# C · 契约 vs 实现：这个 task 是不是 toy，根因在哪一层

> **性质**：只读对照分析。左侧是仓库里已成文的契约，右侧是实际被运行的实现。
> **纪律**：每条结论后跟 `文件名:行号`。**文档说的与代码做的冲突时以代码为准**，冲突处单独标出。
> **未修改任何既有文件**，未运行任何实验，未写任何结果文件。为核实实现行为，只做了两次只读的
> `python3 -c` 打印（需求集结构与逐字节摘要），不产生副作用。
>
> **契约侧**：`docs/s7-method/task-and-action-space.md`、`docs/s6-model/system-model.md`、
> `docs/s6-model/evaluation-contract.md`、`docs/s6-model/downlink-opportunity.md`、
> `docs/s6-model/pre-disaster-paper-contract-v0.1.md`。
> **实现侧**：`code/monitoring/task_generator.py`、`code/monitoring/scorer.py`、
> `code/monitoring/node_model.py`，以及它们的调用方 `runner.py` / `interfaces.py` /
> `policies.py` / `compose.py`（不看调用方就无法回答"哪些动作真的被用"）。
>
> **本文的定位**：这是 `docs/s7-method/task-challenge-pivot-2026-09-13.md`（下称 pivot）与
> `README.md:81` 的 D46 的**证据化续篇**。pivot 已经把"任务无效"判断成结论；本文把它拆成
> **逐条可核查的差异表**，并回答 pivot 没有直接回答的那一问：这个 toy 是**实现偏离了契约**，
> 还是**契约本身就是 toy**。

---

## 0. 结论速览

| 问题 | 回答 | 依据 |
|---|---|---|
| 契约规定的任务是什么 | 外部给定的需求序列 + 7 个动作 + 五条命题 + 7 项业务指标 | §1 |
| 实现的任务是什么 | 一个**外生、无观测依赖**的需求集（430 条）+ 4 个接口 + 一个以 `set_monitoring_profile` 为唯一承重动作的执行机制 | §2 |
| 逐条差异的分布 | **一致 18 项 / (a) 实现漏了 9 项 / (b) 实现改了 6 项 / (c) 契约本身没要求 5 项** | §3 |
| 契约里有没有"由观测结果决定的决策" | **没有。**（唯一例外是需求表述里出现"现场观测"一词，但契约没有任何条目把它落成义务；详见 §4） | §4 |
| 实现里能不能表达这种决策 | **不能。** 模拟器里根本没有"观测值"这个量 | §4.3 |
| 7 个动作的实现状态 | 1 个承重、1 个半死（默认只走免费分支）、1 个默认关闭、1 个条件启用、3 个未实现 | §5 |
| **根因** | **在契约。** | §6 |

---

## 1. 契约规定的任务是什么

### 1.1 需求（任务）怎么定义

**任务表示**（`pre-disaster-paper-contract-v0.1.md:47`）：

> `Task(id, node_set, measurement_type, release_time, sample_window, delivery_deadline, priority, policy_generation)`

同处两句承重的话（`pre-disaster-paper-contract-v0.1.md:47`）：需求**"由外部需求序列生成，不同方法共享需求分母"**；
**"不能用各方法自行产生的样本数给及时服务打分"**。这句被 `README.md:53` 的 D18 固化成"需求集 D 不随种子变化"。

**参考负载的数值**（`pre-disaster-paper-contract-v0.1.md:74-79`，全部标为 **A：诊断参数**）：

| 参数 | 契约值 | 出处 |
|---|---|---|
| 时长与风险窗 | 72 h；第 12–18 h、48–54 h | `pre-disaster-paper-contract-v0.1.md:74` |
| 常态 profile | 每 5 min 采样、每 60 min 上传 | `pre-disaster-paper-contract-v0.1.md:75` |
| 加密 profile | 每 1 min 采样、每 5 min 上传 | `pre-disaster-paper-contract-v0.1.md:76` |
| 低风险节能 profile | 每 15 min 采样、每 60 min 上传 | `pre-disaster-paper-contract-v0.1.md:77` |
| 常态需求 | 每 60 min 一窗，窗内至少一个有效样本于窗开后 90 min 内到达 | `pre-disaster-paper-contract-v0.1.md:78` |
| 风险需求 | **关键节点**每 5 min 一窗，窗内至少一个有效样本于窗开后 10 min 内到达 | `pre-disaster-paper-contract-v0.1.md:79` |
| 关键测点集合 | **"风险窗口内关键测点集合由任务给出"** | `pre-disaster-paper-contract-v0.1.md:39` |
| 规模 | 16 节点、2 个坡面组、1 个网关 | `pre-disaster-paper-contract-v0.1.md:39` |

**推荐的需求表述**（`task-and-action-space.md:41`）：

> 在灾害尚未发生的长期监测阶段，系统依据**外部风险信息**和**现场观测**，在常态、加密观测与节能维持
> 模式之间切换；……保全关键测点的数据新鲜度与历史记录。

紧跟一句限定（`task-and-action-space.md:43`）：**"该表述不要求 LLM 自主判定滑坡发生时刻。风险等级、采样下限
与预警规则由领域规范/专家或固定回放给定"**。§5 的最小案例把这条落成具体事件（`task-and-action-space.md:82-83`）：
"**外部风险等级上升**：将指定关键节点切到加密 profile……**本地触发规则继续独立工作**"。

### 1.2 七个动作及完成判据

`task-and-action-space.md:55` 先划定范围：**"第一轮只实现前四项 + 设备状态回报"**。七个动作与判据全表在
`task-and-action-space.md:57-65`：

| # | 动作 | 完成判据（契约原文要点） | 出处 |
|---|---|---|---|
| 1 | `read_status(node, max_age)` | 得到**带时间戳的电量、版本、缓存水位**；**不够新则返回未知**；"有成本的观测，不能直接读模拟器真值" | `task-and-action-space.md:59` |
| 2 | `set_monitoring_profile(node, profile, generation, expires_at)` | 设备报告**匹配版本/配置摘要**，并**观察到对应采样行为**；主负载 | `task-and-action-space.md:60` |
| 3 | `upload_records(node, time_range, cursor, budget)` | 接收端确认**样本 ID 或连续游标**，并**校验缺口**；过期历史与新数据分队列 | `task-and-action-space.md:61` |
| 4 | `request_measurement(node, request_id, deadline)` | 返回**本次请求对应**的采集时间与结果，**不能拿旧值冒充** | `task-and-action-space.md:62` |
| 5 | `set_backhaul_policy(gateway, policy, generation)` | 以**版本回报及端到端探测**确认切换效果；**"后续扩展"** | `task-and-action-space.md:63` |
| 6 | `set_relay_config(relay, config, generation)` | 中继配置确认并出现**可验证的数据通路**；**"后续扩展"** | `task-and-action-space.md:64` |
| 7 | `restart_device(node, request_id)` | **新启动标识及服务恢复记录**；**"ACK 本身不充分"** | `task-and-action-space.md:65` |

另有两条**评分与设计纪律**（`task-and-action-space.md:69-73`）：(a) 不同语义不能统一用"每命令恰好执行一次"打分，
同值重发只计成本；(b) 配置冲突域宜限定为一个 profile/资源，全实体单调 epoch 的粒度需重新论证。

四个接口的另一份成文契约在 `pre-disaster-paper-contract-v0.1.md:57-62`（`read_status` 含"不读模拟器真值"；
`set_monitoring_profile` 含"同值重发计成本，不算有害重复"；`request_measurement` 含"旧缓存不能冒充新采集"；
`upload_records` 含"发送游标与确认游标不同"），并要求**"同一比较组对所有方法提供相同端侧契约"**
（`pre-disaster-paper-contract-v0.1.md:66`）、**分开记录 `applied_at` / `observed_at` / `currently_active`**
（`pre-disaster-paper-contract-v0.1.md:64`）。

### 1.3 五条可检验命题

`task-and-action-space.md:47-51`：

1. **缺报原因不唯一**——休眠、没电、传感器故障、接入丢失、回传丢失表现相同；不能从一次超时判定原因（`:47`）。
2. **风险阶段与能量预算冲突**——加密观测耗更多采样与传输，节电让观测不够新；**这种耦合需用动作驱动的电量模型验证**（`:48`）。
3. **控制链路也会断**——超时可能是请求没到，也可能是执行了但应答丢了；**查询同样受接收窗口与带宽约束**（`:49`）。
4. **重连带来过时工作**——旧低频配置晚到会降低风险时段观测频率，旧高频配置晚到会多耗电（`:50`）。
5. **数据补齐不等于预警及时**——次日补回昨天数据提高档案完整率，却无法弥补昨天关键时间窗的缺测（`:51`）。

同处声明：第 1、3、4 项的**具体发生频率仍是待测假设**（`task-and-action-space.md:53`）。

### 1.4 七项业务损害指标与两个分母

`evaluation-contract.md:44-52`（标题即"主指标（取代纯执行计数）"）：

| # | 指标 | 契约要求的关键点 | 出处 |
|---|---|---|---|
| 1 | 风险窗口及时数据覆盖率 | 按风险时段、测点与必要测项，数据到达时年龄是否低于规定期限 | `evaluation-contract.md:46` |
| 2 | **关键观测空窗** | 数据年龄越限的**持续时长及分位数**；区分单传感器与多个关键测点同时缺测 | `evaluation-contract.md:47` |
| 3 | 配置错配时长 | 对"实际 profile ≠ 期望 profile"**积分**，而不是轮末一致率 | `evaluation-contract.md:48` |
| 4 | 模式切换期限满足率 | 有效期内配置被执行且取得足够执行证据；**分别报"实际生效"与"平台知晓"的时延** | `evaluation-contract.md:49` |
| 5 | 每个及时有效记录的能量/通信代价 | 含采样、接收、查询、重传、持久化、网关及备用回传，**不只计 Tx** | `evaluation-contract.md:50` |
| 6 | 历史完整率 | 按样本 ID/采集时间统计补齐，**独立于实时合格率** | `evaluation-contract.md:51` |
| 7 | 语义失败及未知率 | 陈旧覆盖、过期执行、实际副作用重复、误报成功、结果长期未知**分别报告** | `evaluation-contract.md:52` |

**两个分母必须同时报告**（`evaluation-contract.md:56-57`）：分母 1 = 全部任务需求；分母 2 = 物理上至少有一次
可用机会的任务需求。主指标定义为 `TimelyCoverage = Σ w_d·I(有效样本在窗内且按期到达)/Σ w_d`
（`pre-disaster-paper-contract-v0.1.md:128`），并明确主表**分别报常态、风险、关键节点**（`:130`）。

### 1.5 其余承重规定（后续逐条对照要用）

- **三个业务闭环**（`pre-disaster-paper-contract-v0.1.md:49-53`）：W1 风险上升后的加密观测 / W2 断连后的关键数据
  恢复 / W3 解除风险后的节能恢复。三个闭环的触发全部写作**外部公告**（"中心收到公告""新解除公告"）。
- **五项基线结构**（`evaluation-contract.md:19-23`）：①固定本地规则+缓存补传+静态回传；②同 planner+持久队列+
  重试退避+设备端幂等键；③同 planner+版本化 desired/reported 调和；④队列化接触窗口交付（LwM2M Queue Mode
  **语义实现**，不得称完整复现）；⑤现有 verified-tool-calls 与本文 runtime 等预算比较。
- **实验编排**（`evaluation-contract.md:29-40`）：A 固定动作的运行时机制 + 分开注入七类故障 + **保留永远不可达的
  负面案例**；B 灾前任务闭环、**以事件驱动模型表达秒/分钟窗口**；C 最小硬件闭环（2–4 节点 + 网关 + 电流记录）。
- **本地自治**（`task-and-action-space.md:90`、`pre-disaster-paper-contract-v0.1.md:55`）：**"本地规则已经足够"是必须
  被排除的替代解释**；所有方法都有相同本地触发规则，保护预设监测下限。
- **触发阈值**（`system-model.md:90`）：触发式采集的阈值可引"雨量 0.2 mm、位移 20 mm"。
- **下行机会约束**（`downlink-opportunity.md:14-17`）：Class A 下一次上行至多一次下行；`contract-v0.1.md:90`
  要求"一次 Class A 上行后通常至多一次成功下行，不是两个工具额度"。`downlink-opportunity.md:97` 另把动作分为
  四类，其中**"节点侧自主动作不受机会约束"**。

---

## 2. 实际实现的任务是什么

### 2.1 `task_generator.py` 实际生成什么

**它是纯函数，不读任何仿真状态**（`task_generator.py:12-19`）："it never reads channel state, energy state, buffer
state, agent beliefs or any simulator object"。`build_demand(deployment, hours, seed)` 的入参只有部署、时长与种子
（`task_generator.py:539`），而**种子不抽样任何东西**（`task_generator.py:552-556`）。

**实测（只读打印 `build_deployment(0)` + `build_demand(hours=72)`）：**

| 项 | 实测值 | 代码出处 |
|---|---|---|
| 需求总数 | **430** | `task_generator.py:628`（断言处） |
| 常态需求 | 142 = 71 窗 × 2 测项 | `task_generator.py:387`、`task_generator.py:664` |
| 风险需求 | 288 = 144 窗 × 2 测项 | `task_generator.py:406-407` |
| 被丢弃的窗 | 常态 1（`deadline` 落在运行结束之后）、风险 0 | `task_generator.py:356-371` |
| 关键节点 | **8 / 16**（每组 4：6 个位移站 + 2 个雨量计） | `task_generator.py:197-206` |
| 常态窗 | 样本窗 3600 s、宽限 `deadline-release` = 5400 s | `task_generator.py:80,82,608-609` |
| 风险窗 | 样本窗 **300 s**、宽限 **600 s** | `task_generator.py:81-82,608-609` |
| profile 日程 | `profile_for_hour` 是**时钟的纯函数** | `task_generator.py:312-324` |
| `policy_generation` | 只随 profile 变化推进（实测取值 1–5，即 W1/W3 各 2 次 + 初始 1 次） | `task_generator.py:598-601` |
| 需求集与种子无关 | 实测 seed=0 与 seed=10000 的 `canonical_demand_bytes` **逐字节相同**，digest 均为 `01134028264ccdf3…` | `task_generator.py:688-697` |

**每一条需求携带什么**：`Task` 的八个字段（`task_generator.py:255-275`）。关键事实是**需求里没有"值"**——
只有 `measurement_type`（"displacement"/"rainfall"）与节点集，没有观测数值、没有阈值、没有"如果……则……"
（`task_generator.py:255-275`）。风险窗内每一刻同时叠加常态任务与风险任务，两者节点集不相交
（`task_generator.py:582-609`）。

**部署侧**：16 节点 2 组 + 1 网关，坐标是高程数据抽样后的 **A 层假定**（`task_generator.py:136-206`），
`build_deployment(seed)` 显式忽略 seed（`task_generator.py:491-498`）。

**发现的两处注释与代码冲突（以代码为准）**：

| 位置 | 注释写的 | 代码实际做的 |
|---|---|---|
| `task_generator.py:653-654` | "71 常态窗、**120** 风险窗、142+240=**382** 条任务、丢弃 **25** 窗（常态 1、风险 24）" | `expected_counts(72)` 实测返回 `risk_windows=144`、`total_tasks=430`、`dropped_risk_windows=0`；同文件 `task_generator.py:548-550` 的注释反而是对的（144 窗 / 288 任务）。**L653-654 是过期注释** |
| `task_generator.py:203-204`、`task_generator.py:470-471` | "10 个位移站、6 个雨量计" | 实测 `_demands_for_instant` 产出 **14 个位移站、2 个雨量计**（`_ROLE_BY_LOCAL_INDEX` 每组只有 1 个 rainfall，`task_generator.py:194-195`） |

### 2.2 `scorer.py` 实际算什么

**入口与形制**：`score(record, weights)`（`scorer.py:434`）→ `ScoreResult(coverage, covered, demands, by_class, servable, aux)`
（`scorer.py:97-108`）。权重默认全 1（`scorer.py:55-58`）。

**真的被计算并进入主表的**：

| 计算 | 代码 | 是否被报告 |
|---|---|---|
| 及时覆盖率（两半条件：窗内采到 **且** 按期到达） | `scorer.py:111-127` | ✅ 所有实验脚本 |
| 按常/风险/关键节点分桶 | `scorer.py:442-479` | ✅（但"关键节点"桶 = 风险桶，见下） |
| 分母 2（物理可服务子集：需求生存期内该节点至少一次上行被网关听到） | `scorer.py:148-164`、`scorer.py:471-473`、`scorer.py:505-506` | ✅ |
| 配置错配时间积分 | 累加在 `runner.py:600-604`，读在 `scorer.py:490` | ✅（`analysis/steady_gap.py:237`） |
| AoI 与空窗（均值/p99/最大、最长空窗/p99、逐节点） | `scorer.py:196-249` | ⚠️ 只有 `aoi_mean_s` 有消费者（`experiments/sensitivity.py:51`） |
| 误报成功、知晓时延 | `scorer.py:381-402`、`scorer.py:419-420` | ⚠️ `false_successes`/`knowledge_latency_s` 上报（`monitoring_trajectories.py:51-52`）；`_max_s` 无人读 |
| 未满足需求三成因分类 | `scorer.py:287-340` | ⚠️ 只报 `late_delivery` 与 `no_sample_in_window`（`sensitivity.py:52-53`） |
| 语义失败计数（stale/fenced/duplicate/expired/unknown） | `scorer.py:404-431`；计数在 `runner.py:722-733` | ⚠️ 部分（`monitoring_trajectories.py:55-59`） |
| 档案完整率 | `scorer.py:481-497` | ❌ 见下 |

**算了但没有任何消费者的字段**（全仓 grep：除 `scorer.py` 与 `test_scorer.py` 外零命中）：

- `uplink_airtime_ms` / `downlink_airtime_ms`（`scorer.py:354-355`）——**上下行空口拆分**，而 `scorer.py:343-351`
  的注释专门论证"命令的成本记在机会账上，不记在能量账上"，这个论证的载体本身没人读。
- `energy_per_met_demand_wh`（`scorer.py:357`）→ **契约指标 5（每个及时有效记录的能量代价）没有落到任何报表**。
- `expected_samples` / `taken_samples` / `observation_gap_samples`（`scorer.py:405-407`）——只有比率被读。
- `aoi_p99_s` / `aoi_max_s` / `longest_gap_s` / `longest_gap_p99_s` / `per_node_aoi`（`scorer.py:242-249`）
  → **契约指标 2 要求"持续时长及分位数"，分位数全部算了出来，全部没有上报**。
- `false_successes_instant` / `false_successes_overwritten`（`scorer.py:411-412`）——7.6 定义的两个半边的分解。
- `actions_settled`（`scorer.py:409`）、`knowledge_latency_max_s`（`scorer.py:420`）。
- `residual_met` / `residual_served_stale_reading` / `residual_unmet`（`scorer.py:339-340`）。
- `wasteful_measurement_requests` / `duplicate_physical_samples`（`scorer.py:283-284`）→ **契约 §8 的"额外物理采集等有害执行"没有上报**。
- `declared_without_evidence`（`scorer.py:418`）、`log_entries` / `records_taken` / `records_arrived`（`scorer.py:493-496`）。
- `restart_events` / `restart_unresolved` / `restart_lost` / `llm_calls` / `llm_illegal`（`scorer.py:426-430`）
  ——runner 直接从策略对象读这些数（`runner.py:708-710`），`aux` 里的那份是死字段。
- `archive_completeness`（`scorer.py:494`）→ 唯一打印它的是 `format_score`（`scorer.py:511-527`），
  而 **`format_score` 在全仓没有任何调用点**（grep 仅命中定义处）。

**算了但恒为常数**：`spurious_measurements`（`scorer.py:491`）——`runner.py:723` 硬写 `spurious_measurements=0`，
即该字段永远是 0。

**口径被改掉的两处**：

1. **"关键节点"桶等价于"风险"桶**：`scorer.py:464` 写 `critical = klass == "risk"`，于是
   `by_class["critical"]` 与 `by_class["risk"]` 在数值上完全相同（`scorer.py:458-469`）。因为风险需求本就只落在
   关键节点上（`task_generator.py:476`），契约 `pre-disaster-paper-contract-v0.1.md:130` 要求的"分别报常态、风险、
   关键节点"里，**第三行不含任何独立信息**。
2. **"误报成功"是合成量**：`false_successes = overwritten_after_settle + (结算时实际 profile ≠ 被命令的 profile)`
   （`scorer.py:386-402`）。这与 `evaluation-contract.md:52` 的"误报成功"语义接近但不是同一件事的原始计数。

**完全没算的**：契约指标 4 的"**模式切换期限满足率**"。评分器只有"知晓时延"的均值/最大
（`scorer.py:390-392,419-420`）；"在有效期限内配置被执行且取得足够执行证据"的**比率**只在一个分析脚本里以
粗粒度出现（`analysis/steady_gap.py:200-222` 的 `risk_open_wrong` 与 `switch_on_delay_min`），不在评分器内。

### 2.3 `node_model.py` 的采样与上传周期

- **时钟 1 分钟**（`node_model.py:40`，`TICK_S=60`），理由写在 `node_model.py:17-20`：10 min 的风险截止在小时
  粒度上不可表达。
- **采样完全由 profile 驱动**：`maybe_sample` 按 `MONITORING_PROFILES[profile]["sample_s"]` 逐拍采样
  （`node_model.py:213-240`）；`set_profile` **重基准**采样与上传时刻（`node_model.py:179-193`），
  所以 profile 是真正改变行为的变量。
- **上传**：`upload_due` / `begin_upload` 按 `upload_s` 周期触发（`node_model.py:259-290`），一次上传
  **重传所有未确认记录**，上限 `batch_max=240`（`node_model.py:55,286`），按 100 B/包切包（`node_model.py:49,292-306`）。
- **缓存**：容量 2880 条，溢出丢最旧并计数（`node_model.py:43,242-252`）。
- **请求采集的语义**：采样时刻打 `request_id` 标签、样本身份带 `:r{rid}` 后缀（`node_model.py:87-94,219-231`），
  超窗未答则记 `requests_expired`（`node_model.py:237-239`）→ 满足"不能拿旧值冒充"。
- **状态快照**（`node_model.py:365-387`）：`read_at`/`incarnation`/`profile`/`profile_version`/`buffer_level`/
  `newest_sample_at`/`acked_cursor`/`send_cursor`；**`battery_wh` 恒为 `None`**（`node_model.py:381`）。
  供电台账只写进 `record.supply_ledger`（`runner.py:739`），**从未进入策略可见的 `WorldView`**
  （`runner.py:582-583` 只把节点快照塞进 `status`）。
- **采样与上传不受下行机会约束**：节点自主进行（`runner.py:593-629`），对应 `downlink-opportunity.md:97` 的第四类动作。
- **无电就什么都不做**：`runner.py:596-598`，这是能量与监测缺口的耦合点。
- **没有本地触发规则**：全监控层 grep 无阈值/触发/看门狗逻辑；`LocalRulesPolicy.plan` 直接返回空
  （`runner.py:94-105`）。契约要求的"相同本地触发规则，保护预设监测下限"
  （`pre-disaster-paper-contract-v0.1.md:55`、`task-and-action-space.md:82,90`、`system-model.md:90` 的
  0.2 mm/20 mm 阈值）**在实现中不存在**。

### 2.4 动作路由：谁真的用这些动作

- 中心可声明的 op 只有四个（`policies.py:62-69` 的 `OPS`），`compose.py:43-45` 的意图词汇只有三个
  （`set_profile`/`request_measurement`/`upload_records`）。
- runner 的路由（`runner.py:481-507`）：`set_profile` → `iface.set_monitoring_profile`；
  `request_measurement` → `iface.request_measurement`；`upload_records` → `iface.upload_records`；
  **其它一切（含 `read_status`）计入 `refused_actions` 并丢弃**（`runner.py:503-507`，注释明说
  "`read_status` 由遥测回答，从不作为动作派发"）。
- 因此 `interfaces.py:306-315` 的**主动查询分支在产品路径上不可达**，只被 `experiments/test_interfaces.py:143-153` 覆盖。
- 中心可见的世界（`runner.py:55-71` 的 `WorldView`）：时间、节点表、**上一次状态读**、**被授予的需求日程**、
  未决命令、中心自己的档案最新点。**没有观测值、没有电量、没有采样计划**。
- **日程是全量授予的**：`grant_announcement=True` 是默认值（`runner.py:166`），只要授予就把
  **整份 profile 日程**发给中心（`runner.py:459-467`，注释自陈"包括窗口什么时候结束"）。
- 组成层：`RulePlanner` 三件事（profile / 必要时请求采集 / 限预算补历史）（`compose.py:103-243`）；
  `LLMPlanner` 只在 `_has_decision` 为真时调用模型（`compose.py:264-305`），且**模型返回空时用规则结果兜底**
  （`compose.py:285-286`：`return intents if intents else floor`）。
- `RuntimePolicy`（单体臂）的 plan 只依赖 `demanded_profile`、遥测上报、`in_flight`、`archive_newest`
  （`policies.py:943-1150`）。

---

## 3. 逐条差异表

判定口径：**一致** = 契约与实现相符；**(a) 实现漏了** = 契约要求了，实现没有或不可达；
**(b) 实现改了** = 实现做了别的东西或改了口径；**(c) 契约本身没要求** = 差异的根源在契约侧。

| # | 契约要求（出处） | 实现现状（出处） | 判定 |
|---|---|---|---|
| 1 | Task 八字段（`pre-disaster-paper-contract-v0.1.md:47`） | `Task` 八字段同名同序（`task_generator.py:255-275`） | 一致 |
| 2 | 需求"由外部需求序列生成"，各臂共享分母（`pre-disaster-paper-contract-v0.1.md:47`） | `build_demand` 纯函数；实测跨种子逐字节相同（`task_generator.py:539-556`、`44-49`） | 一致（被加强为 byte-identical） |
| 3 | 常态需求：60 min 一窗、90 min 内到达（`pre-disaster-paper-contract-v0.1.md:78`） | `NORMAL_INTERVAL_S=3600`、`DEADLINE_S["normal"]=5400`（`task_generator.py:80,82`） | 一致 |
| 4 | 风险需求：关键节点 5 min 一窗、10 min 内到达（`pre-disaster-paper-contract-v0.1.md:79`） | `RISK_INTERVAL_S=300`、`DEADLINE_S["risk"]=600`（`task_generator.py:81-82`） | 一致 |
| 5 | 风险窗 12–18 h、48–54 h（`pre-disaster-paper-contract-v0.1.md:74`） | `RISK_WINDOWS_H`（`task_generator.py:78`） | 一致 |
| 6 | 关键测点集合**由任务给出**、不逐任务重抽（`pre-disaster-paper-contract-v0.1.md:39`） | 写死为部署常量（`task_generator.py:197-206`） | 一致 → **(c)**：契约把它定义为"给定"，等于把"看哪里"从决策空间里拿走 |
| 7 | 需求表述含"依据外部风险信息**和现场观测**"切换模式（`task-and-action-space.md:41`） | 需求生成器不读任何观测（`task_generator.py:12-19,44-49`）；无任何条目兑现这半句 | **(a)** 按表述口径；按可检验条目口径见 §4.2 |
| 8 | 风险等级由**固定回放**给定（`task-and-action-space.md:43`）；最小案例只写"风险等级上升"（`:82`） | 整份日程（含窗口结束时刻）一次授予中心（`runner.py:166,459-467`） | **(b)** 实现改了：回放粒度由"上升公告"放大为"全程预告" |
| 9 | 所有方法有**相同本地触发规则**，保护预设监测下限（`pre-disaster-paper-contract-v0.1.md:55`；`task-and-action-space.md:82,90`） | 监控层无任何本地规则；`local_rules` 臂的 plan 返回空（`runner.py:94-105`） | **(a)** 实现漏了 |
| 10 | 触发式采集阈值（雨量 0.2 mm、位移 20 mm）（`system-model.md:90`） | 无任何阈值逻辑 | **(a)** 实现漏了 |
| 11 | 每个动作带逻辑身份、参数、冲突域、期限、证据年龄（`pre-disaster-paper-contract-v0.1.md:64`） | `ActionRecord` 全字段 + 四个冲突域（`interfaces.py:65-103`、`59-62`） | 一致 |
| 12 | 分开记录 `applied_at`/`observed_at`/`currently_active`（`pre-disaster-paper-contract-v0.1.md:64`） | 字段齐全（`interfaces.py:76-81,102`）；但 `currently_active` 的生产代码里**从未被赋值**，只有测试赋过（全仓 grep：`experiments/test_interfaces.py:108,114`），实际运行中恒为 `None` | **(a)** 部分：字段存在、语义未被填充 |
| 13 | 同一比较组对所有方法相同端侧契约（`pre-disaster-paper-contract-v0.1.md:66`） | 远端契约统一在 `runner.remote_apply`（`runner.py:326-347`），对每臂相同 | 一致 |
| 14 | `read_status` 判据含**带时间戳的电量**（`task-and-action-space.md:59`；`pre-disaster-paper-contract-v0.1.md:59`） | `battery_wh` 恒为 `None`（`node_model.py:381`），供电台账只进 record（`runner.py:739`） | **(a)** 实现漏了：电量从未进入 agent 可观测面 |
| 15 | `read_status` 是**有成本的观测**，不够新返回未知（`task-and-action-space.md:59`） | 新鲜遥测免费回答（`interfaces.py:298-304`）；主动查询分支被 runner 拒绝（`runner.py:503-507`） | **(b)** 实现改了：默认零成本被动读，主动查询为死代码 |
| 16 | `set_monitoring_profile` 判据含**匹配版本/配置摘要**（`task-and-action-space.md:60`） | 采样行为真实改变（`node_model.py:179-193`）；但节点只回传 profile 名与本地变更计数 `profile_version`（`node_model.py:379-380`），中心写入的 `version/generation` 不回传 | **(a)** 部分：版本匹配不可核验（fencing 由 runner 另行实现，`runner.py:340-346`） |
| 17 | 同值重发只计成本、不算有害重复（`task-and-action-space.md:70-71`；`pre-disaster-paper-contract-v0.1.md:60`） | `DOMAIN_PROFILE` + `reaccepted` 去重记账（`interfaces.py:59,334-337`；`runner.py:334-339`） | 一致 |
| 18 | `upload_records` 判据：确认样本 ID/游标并**校验缺口**（`task-and-action-space.md:61`） | 按 `sample_id` 去重（`node_model.py:308-323`）、双游标（`:325-340`）都在；但**接口默认关闭**（`policies.py:808-809`；`compose.py:117`），`archive_gap` 的调用点只有测试（`node_model.py:345-362` vs `experiments/test_interfaces.py:292,296`） | **(b)** 实现改了：契约的"数据面恢复"在主表里不参与 |
| 19 | `request_measurement` 判据：不能拿旧值冒充（`task-and-action-space.md:62`） | 采样时刻打标签 + 身份带请求后缀（`node_model.py:87-94,219-231`） | 一致 |
| 20 | `set_backhaul_policy`（契约自标"后续扩展"）（`task-and-action-space.md:63`） | 未实现为动作；仅 profile 命令带 `path` 字段（`interfaces.py:169,337`；`runner.py:494`），主表单路径 `PATHS=(("backhaul",0.62),)`、`RUNTIME_PATHS=(0,)`（`analysis/steady_gap.py:50-51`） | **(a)** 实现漏了（契约本身标为后续扩展） |
| 21 | `set_relay_config`（契约自标"后续扩展"）（`task-and-action-space.md:64`） | 未实现；监控层无中继实体（旧层只有 `gateway.failover`，`code/runtime/disruption_env.py:98`） | **(a)** 实现漏了 |
| 22 | `restart_device`，判据为**新启动标识及服务恢复记录**（`task-and-action-space.md:65`） | 未实现为中心动作；重启是**注入故障**（`faults.py:99-100`；`runner.py:239-243,431-439`）；启动标识字段存在（`node_model.py:166,377`） | **(a)** 实现漏了（作为动作）；证据字段存在 |
| 23 | 主指标两半条件（`pre-disaster-paper-contract-v0.1.md:128`） | `_covered_by` 严格两半（`scorer.py:111-127`） | 一致 |
| 24 | 两个分母同时报告（`evaluation-contract.md:56-57`；`pre-disaster-paper-contract-v0.1.md:130`） | 可服务子集实现并上报（`scorer.py:148-164,471-473,505-506,520-522`） | 一致（**修掉了 README 自承的 47.8% 口径问题**） |
| 25 | 主表分别报常态、风险、**关键节点**（`pre-disaster-paper-contract-v0.1.md:130`） | `critical` 桶 = `risk` 桶（`scorer.py:458-469`，判定式在 `:464`） | **(b)** 实现改了：第三行无独立信息 |
| 26 | 指标 2：关键观测空窗的**持续时长及分位数**（`evaluation-contract.md:47`） | 分位数全算了（`scorer.py:242-249`），只有均值有消费者（`sensitivity.py:51`） | **(a)** 报告层缺（算而未报） |
| 27 | 指标 3：配置错配**时间积分**（`evaluation-contract.md:48,71`） | 逐分钟累加（`runner.py:600-604`）并上报（`steady_gap.py:237`） | 一致（`evaluation-contract.md:71` 指出的轮末比对缺陷已修掉） |
| 28 | 指标 4：模式切换**期限满足率**，分报"实际生效"与"平台知晓"（`evaluation-contract.md:49`） | 评分器只有知晓时延均值/最大（`scorer.py:390-392,419-420`）；"满足率"仅在分析脚本里粗粒度出现（`steady_gap.py:200-222`） | **(a)** 部分：满足率未进评分器 |
| 29 | 指标 5：每及时有效记录的能量/通信代价（含采样、接收、重传……）（`evaluation-contract.md:50`） | 空口拆分与 `energy_per_met_demand_wh` 都算了（`scorer.py:343-358`），**零消费者** | **(a)** 报告层缺 |
| 30 | 指标 6：历史完整率**独立于实时合格率**（`evaluation-contract.md:51`） | 算了（`scorer.py:481-497`）；唯一打印它的 `format_score` 无调用点（`scorer.py:511-527`） | **(a)** 报告层缺 |
| 31 | 指标 7：语义失败与未知率**分别报告**（`evaluation-contract.md:52`） | 分项都在（`scorer.py:404-431`），部分上报（`monitoring_trajectories.py:55-59`）；"误报成功"是合成量（`scorer.py:386-402`） | **(b)** 部分实现：口径被改 |
| 32 | （隐含）指标里的"有害执行" | `spurious_measurements` 恒为 0（`runner.py:723`）；真正算出的 `wasteful_measurement_requests`/`duplicate_physical_samples` 无消费者（`scorer.py:252-284`） | **(b)** 实现改了 + (a) 报告层缺 |
| 33 | 五项基线结构（`evaluation-contract.md:19-23`） | 实现为 `local_rules`/`versioned_config`/`vtc_style` + 2×2（`policies.py:1277-1290`；`compose.py:717-736`）；②的"持久队列+幂等键"被拆进共同基础设施（`opportunity.py` 网关队列、`runner.py:326-347`） | **(b)** 实现改了：5 项被合并重构 |
| 34 | 实验 A：分开注入故障 + 保留永远不可达案例（`evaluation-contract.md:30`） | 六类故障分开注入（`faults.py:99-100`）；88.5% 的地形死区保留在部署里（`system-model.md:62`） | 一致 |
| 35 | 实验 B：灾前闭环、以事件驱动表达秒/分钟窗（`evaluation-contract.md:32-36`） | `TICK_S=60`（`node_model.py:40`），300 s/600 s 的风险窗可表达 | 一致（**修掉了"小时粒度不能证明 5 min 时限"**） |
| 36 | 实验 C：最小硬件闭环（`evaluation-contract.md:38-40`） | 代码库内不存在 | **(c)** 不属于仿真实现范围 |
| 37 | 命题 1：不能从一次超时判定原因（`task-and-action-space.md:47`） | `UNKNOWN` 是一级结果、超时不改判（`interfaces.py:45-50,277-289`）；`unknown_s` 累计（`runner.py:471-472`） | 一致 |
| 38 | 命题 2：风险与能量耦合需**动作驱动**的电量模型（`task-and-action-space.md:48`） | `SupplyFleet` 按各臂动作扣电（`runner.py:173-179,356-366,429-431`） | 一致（机制）；**(c)** 负载不 binding（README D46 `README.md:81`：主表 0 死节点） |
| 39 | 命题 3：控制链路也会断、查询同样受窗口约束（`task-and-action-space.md:49`） | `request_lost`/`ack_lost` 故障（`faults.py:99-100`）+ 机会不变量断言（`opportunity.py:434-451`） | 一致 |
| 40 | 命题 4：重连带来过时工作（`task-and-action-space.md:50`） | `stale_command` 故障 + 乱序/覆盖分开计数（`runner.py:510-526,674-679`） | 一致 |
| 41 | 命题 5：数据补齐不等于预警及时（`task-and-action-space.md:51`） | 档案完整率与及时率分离（`scorer.py:481-497`）；残余失败按投递/采样分类（`scorer.py:287-340`） | 一致 |
| 42 | 下行机会受 Class A 约束（`downlink-opportunity.md:14-17`；`pre-disaster-paper-contract-v0.1.md:90`） | 一次上行至多一次下行 + 不变量断言（`opportunity.py:392-397,434-451`） | 一致（**修掉了 `downlink-opportunity.md:75` 指出的"下行与上行无关"**） |
| 43 | 节点侧自主动作不受机会约束（`downlink-opportunity.md:97`） | 采样/重传不经下行（`node_model.py:213-240,262-290`） | 一致 |

### 3.1 "契约本身没要求"的条目（直接喂给 §4）

逐个看 (c) 条目，它们指向同一处：

| 条目 | 契约的原文 | 为什么这是契约侧问题 |
|---|---|---|
| #6 关键测点集合固定 | "风险窗口内关键测点集合**由任务给出**"（`pre-disaster-paper-contract-v0.1.md:39`） | "下一步看哪里"被定义成输入，不是决策 |
| #2 需求外生 | "由**外部需求序列**生成，不同方法共享需求分母"（`pre-disaster-paper-contract-v0.1.md:47`） | 需求集不许是方法的输出，也不许是观测的函数 |
| #8 风险等级回放 | "风险等级、采样下限与预警规则由领域规范/专家或**固定回放**给定"（`task-and-action-space.md:43`） | 触发加密观测的唯一依据是外部公告 |
| #36 实验 C | 硬件闭环（`evaluation-contract.md:38-40`） | 与"任务里有没有决策"无关 |
| #38 能量不 binding | 命题 2 只要求"用动作驱动的电量模型验证"（`task-and-action-space.md:48`） | 契约要求了模型，没有要求负载必须在主表里把电打穿 |

**一句话总结第 3 节**：实现忠实地实现了契约写下的东西；被漏掉的 9 项（电量可观测、本地规则、三项动作、
若干指标上报）都是**补丁**，补上也不会让任务变得非 toy。真正决定"toy 与否"的，是 (c) 那 5 条，
它们全部指向同一件事——**契约把"看哪里、要不要加测"写成了输入**。

---

## 4. 契约本身是否 toy：契约里有没有"由观测结果决定的决策"

**问题**：中心下一步看哪里、要不要加测，是否取决于它已经看到了什么？

### 4.1 直接回答：没有

按**可检验条目**（命题、完成判据、指标、参考负载表）的口径，契约里**没有任何一条**把
"下一步观测什么 / 是否增加观测"定义为"已经看到的观测结果"的函数。逐条核对：

| 契约条文 | 它把决策挂在什么上 | 出处 |
|---|---|---|
| 需求集 D 的来源 | **外部需求序列**，各臂共享 | `pre-disaster-paper-contract-v0.1.md:47` |
| 关键测点集合 | **由任务给出**（输入） | `pre-disaster-paper-contract-v0.1.md:39` |
| 加密观测的触发 | **外部风险等级上升**（公告） | `task-and-action-space.md:82` |
| 模式回退 | **风险解除公告**（W3 是 W1 的逆操作） | `pre-disaster-paper-contract-v0.1.md:53` |
| W2 补历史 | **恢复后有积压**（连通性事件，不是观测值） | `pre-disaster-paper-contract-v0.1.md:52` |
| 风险等级/采样下限/预警规则 | **领域规范、专家或固定回放给定** | `task-and-action-space.md:43` |
| 动作表里唯一带"必要时"的动作 | `request_measurement`——契约**没有给出"必要"的判据** | `task-and-action-space.md:62`；`pre-disaster-paper-contract-v0.1.md:51` |

**必须区分的一件事**：契约确实要求 agent **依据观测做下一步**，但那些"观测"是**自己调用的结果**
（完成/未完成/结果不可知），不是**监测对象的观测值**。这一点写在 `system-model.md:19`
（"观测通道与它的控制通道是同一条"）、`system-model.md:114`（投影为三值）、`system-model.md:124`
（重试、改走另一实体、放弃并上报）、`system-model.md:128`（必须区分"超时"与"结果不可知"），
以及命题 1/3/4（`task-and-action-space.md:47,49,50`）。所以契约的闭环是
**"执行证据 → 执行策略"**，不是 **"观测值 → 观测计划"**。前者在实现中完整存在（§2.4），
后者在契约与实现中都不存在。

pivot 的说法与此一致（`task-challenge-pivot-2026-09-13.md:71,145`：唯一承重的动作是把 profile 从 normal
改成 risk 再改回来；"中心看到什么都不影响它下一步要看什么"），`README.md:81`（D46）已把它登记为决策：
**"判据是「任务里是否存在一个由观测结果决定的决策」"**。

### 4.2 唯一一处措辞例外，以及它为何不构成要求

`task-and-action-space.md:41` 的推荐需求表述里确实写着"依据外部风险信息**和现场观测**"。若严格按这句话读，
实现是 **#7 (a) 实现漏了**。但这句话**没有落成任何义务**：

- 五条命题（`task-and-action-space.md:47-51`）里没有一条以观测值为自变量；
- 七个动作的完成判据（`:59-65`）里没有一条要求"依观测改变后续计划"；
- 7 项指标（`evaluation-contract.md:46-52`）里没有一项度量"观测驱动的决策质量"；
- 参考负载表（`pre-disaster-paper-contract-v0.1.md:74-82`）里没有观测依赖项，且明写"**数据由真正的采样调度
  产生，外部评分器持有真值**"（`:84`）；
- §5 最小案例把每一步都挂在风险等级上（`task-and-action-space.md:82-85`）。

结论：**有词无条**。按"契约是否规定了一项可检验的义务"的口径，答案是**没有**。

### 4.3 更彻底的一层：实现里根本没有"观测值"这个量

即使明天在契约里补一句"中心应依据观测结果决定下一步"，当前实现**无法表达它**：

- `Sample` 只有 `sample_id / node_id / taken_at / measurement_type / payload_bytes / request_id`
  （`node_model.py:72-94`）——**没有读数**。样本是一条"存在性"事件，不是一次测量。
- `Task` 只有 `measurement_type`（`task_generator.py:255-275`）——没有阈值、没有条件、没有依赖另一测点。
- 中心可见面里没有电量（`node_model.py:381`），没有观测值（`runner.py:55-71` 的 `WorldView` 全部字段）。
- 需求生成器不读任何仿真对象（`task_generator.py:12-19`），实测跨种子逐字节相同（§2.1）。

也就是说，"由观测结果决定的决策"在当前实现中不是"没实现"，而是**没有承载体**：要实现它，必须先给
`Sample` 加数值语义、给 `Task` 加条件依赖、给 `WorldView` 加观测投影。这正是 pivot §6 第一条
（`task-challenge-pivot-2026-09-13.md:145-147`）在说的事。

---

## 5. 七个动作：哪些真的被使用，哪些是死代码或默认关闭

| # | 动作 | 判定 | 证据 |
|---|---|---|---|
| 1 | `read_status` | **半死：只有免费被动分支活着；主动查询是死代码** | 被动：`interfaces.py:298-304`（新鲜遥测直接回答）、`policies.py:843-857`、`compose.py:134-142` 都只读 `view.status`。主动查询：`interfaces.py:306-315` 存在但 **runner 拒绝派发任何 `read_status`**（`runner.py:503-507`），唯一的调用者是测试（`experiments/test_interfaces.py:143-153`）。并且它本该回答的"电量"恒为 `None`（`node_model.py:381`） |
| 2 | `set_monitoring_profile` | **唯一承重动作；所有对照臂都在用它** | 接口：`interfaces.py:317-338`；路由：`runner.py:490-495`；单体 runtime：`policies.py:1000-1121`；规则 planner：`compose.py:153-176`；基线：`VersionedConfigPolicy`（`policies.py:148`）、`VTCPolicy`（`policies.py:398`）；oracle：`runner.py:125-134`。pivot 也认定它是"剩下唯一承重的动作"（`task-challenge-pivot-2026-09-13.md:63`） |
| 3 | `upload_records` | **实现完整，但默认关闭（D32）；且缺口核验在产品路径上是死代码** | 默认关闭：`policies.py:808-809`（`enable_backfill = False`）、`compose.py:117`（规则 planner 同样关闭）、门禁在 `policies.py:898-899` 与 `compose.py:216-217`；关闭的理由是实测（`policies.py:884-897`，`README.md:67` 的 D32）。`archive_gap`（缺口核验）只有测试调用（`node_model.py:345-362` vs `experiments/test_interfaces.py:292,296`）。打开它只在旁支实验里：`analysis/steady_gap.py:154,159` |
| 4 | `request_measurement` | **被使用，但条件启用（仅风险窗 + 档案过期）** | 接口：`interfaces.py:351-359`；节点侧：`node_model.py:195-197,219-231`；调用条件：`policies.py:859-882`（`want != PROFILE_RISK` 直接返回 False）与 `policies.py:967-981`；组合层同一判据：`compose.py:178-207`。**它不是主表的承重动作**：风险需求能否被满足主要由 profile 是否已切到风险档决定（样本窗 300 s < 常态上传周期 3600 s） |
| 5 | `set_backhaul_policy` | **未实现** | 监控层无该动作；只有 profile 命令携带 `path`（`interfaces.py:169,337`；`runner.py:494`）。路径选择能力存在于组成层（`compose.py:365-373` 的 `NaiveRuntime.paths`），但**主表是单路径**：`PATHS=(("backhaul",0.62),)`、`RUNTIME_PATHS=(0,)`（`analysis/steady_gap.py:50-51`），与 pivot 记录的"主表 `runtime_paths=0`、备用路径只在 3 种子旁支"一致（`task-challenge-pivot-2026-09-13.md:153`）。契约本身标为"后续扩展"（`task-and-action-space.md:63`） |
| 6 | `set_relay_config` | **未实现** | 监控层没有中继实体，也没有中继配置冲突域（`interfaces.py:59-62` 只有 profile/measurement/transfer/status 四域）。旧执行层只有 `gateway.failover`（`code/runtime/disruption_env.py:98`），与本契约的动作不是同一个东西。契约标为"后续扩展"（`task-and-action-space.md:64`） |
| 7 | `restart_device` | **作为动作未实现；作为故障与证据字段存在** | 中心的动作集只有四个（`policies.py:62-69`）。节点重启由故障注入器产生（`faults.py:99-100` 的 `node_restart`；`runner.py:239-243` 建窗、`runner.py:431-439` 执行，重启后 profile 回落 normal）。契约要求的"新启动标识"字段存在：`node_model.py:166`（`incarnation`）与 `node_model.py:377`（进快照）；但"服务恢复记录"没有独立产物。契约另有"ACK 本身不充分"的要求（`task-and-action-space.md:65`），实现以 `applied_at`/`observed_at` 分离来满足（`interfaces.py:195-223`） |

**汇总**：7 个契约动作中，**1 个承重**（`set_monitoring_profile`）、**1 个半死**（`read_status`）、
**1 个默认关闭**（`upload_records`）、**1 个条件启用且非承重**（`request_measurement`）、
**3 个未实现**（`set_backhaul_policy`、`set_relay_config`、`restart_device`）。
契约自己在 `task-and-action-space.md:55` 就写明"第一轮只实现前四项"，因此第 5–7 项的缺席**是履约**，
不是违约；真正值得记的是：**被实现的前四项里，只有一项在主表上承重**。

---

## 6. 一段话回答：这个 task 太 toy，根因在实现还是在契约

**根因在契约。** 实现确实有偏离（§3 的 9 条 (a) 与 6 条 (b)：电量从未进入 agent 可观测面、本地触发规则
完全缺失、`upload_records` 默认关闭、`read_status` 的主动查询不可达、三项指标算而未报、关键节点桶与风险桶
重复），但这些偏差**没有一条是把一个非 toy 的任务做成了 toy**——它们要么是补丁（补上只会让同一个任务更完整），
要么是**放大**了契约本身的倾向（`runner.py:459-467` 把整份日程一次性预告给中心，`runner.py:503-507` 让状态读
基本免费，两者都让"决策"进一步消失）。真正决定性质的是契约侧那 5 条 (c)：**需求集被规定为外部生成**
（`pre-disaster-paper-contract-v0.1.md:47`）、**关键测点集合被规定为任务给定**（`:39`）、**风险等级被规定为
固定回放**（`task-and-action-space.md:43`）、**触发加密观测的唯一依据是外部公告**（`:82`）、
**唯一的"必要时"没有判据**（`:62`）——这五条合起来，使"中心下一步看哪里、要不要加测"在契约里就是**输入**，
而不是**决策**。更彻底的是，实现里连"观测值"这个量都不存在（`node_model.py:72-94` 的 `Sample` 没有读数），
所以即使把实现的所有 (a) 都补上，任务仍然是"在两个窗口开启时，把一次已知的状态尽快写进 8 个节点"
（pivot 的推论三，`task-challenge-pivot-2026-09-13.md:65-67`），成熟设备影子仍会赢。**结论：要动的是契约，
不是实现**——按 pivot §6 的四条（需求内生、观测间有依赖、覆盖增强成为决策、供电 binding，
`task-challenge-pivot-2026-09-13.md:143-160`）重写任务定义；实现侧的 15 条偏差作为重写时的"已欠债清单"
并行处理，其中电量可观测（`node_model.py:381`）与本地触发规则（`runner.py:94-105`）是重写后必须补齐的两项。
