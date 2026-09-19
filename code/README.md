# 代码结构

更新：2026-09-19。当前论文实验入口在 `v3joint/`，基础节点与评分实现在 `instance/`。其余目录包含物理支撑、历史实验与回归；下方早期脚本说明保留用于复现，不代表当前论文的证据状态。结论与待办见[根 README](../README.md)。

```
code/
├── v3joint/        当前联合层、任务视图、Agent 接入、r37–r39 与联合检查
├── instance/       节点、网关、能量、义务与评分基础实现
├── physics/        物理层：地形、传播、信道时间结构与能量
├── runtime/        早期执行层：操作语义与环境
├── monitoring/     早期业务闭环与接口
├── experiments/    历史实验驱动、实例实验与回归检查
└── analysis/       数据处理：从真实轨迹拟合参数
```

各脚本头部注明依赖与输出。常用检查和数据准备见[根 README 的复现入口](../README.md#代码与复现)；旧 README 章节已[归档](../docs/早期状态/2026-09-19-README-history.md)。

当前联合层检查为 `python3 code/v3joint/test_joint.py`；仓库回归为 `python3 code/run_checks.py --quiet`。现有 Agent 轨迹的只读审计见 [audit_traces.py](../docs/s8-report/review-v0.6/audit_traces.py)，不调用模型。论文证据边界见 [doc51](../docs/s7-method/v1.2/51-independent-review-paper-v06-2026-09-19.md)。

## physics/ — 物理层

结论的物理依据都在这里。凡是系统模型里标注 M（实测）或 S（标准模型）的参数，来源都是这一组。

| 脚本 | 职责 | 依赖 | 输出 |
|---|---|---|---|
| `mountain_lora_link.py` | 单点链路预算。读 SRTM1 高度瓦片，沿大圆路径采样地形剖面，跑 Longley-Rice ITM 得到总损耗，再按 SX1276 各 SF 的灵敏度换算可用 SF 与单次上行的能耗。**这一组的地基**，其余脚本多数从它导入 | 高程数据 | 终端输出 |
| `coverage_map.py` | 把单点预算扩展到 121×121 网格，统计可达率、各 SF 分布与不可达点数量；随后做贪心中继选址 | `mountain_lora_link` | `results/coverage_grid.csv`、`coverage_summary.txt`、`coverage_map.png` |
| `relay_siting.py` | 带高程与坡度约束的中继选址，与 `coverage_map` 的无约束版本互为对照 | `mountain_lora_link` | 终端输出 |
| `los_vs_itm.py` | 几何视线判定：沿 DEM 剖面做第一菲涅尔区净空判据，与 ITM 的结果交叉验证；同时测网格分辨率对遮挡判定的影响 | `dem_to_mitsuba` | `results/los_vs_itm.json` |
| `dem_to_mitsuba.py` | 把 SRTM 瓦片转成三角网格与 Mitsuba 场景，供射线追踪使用。格点与 `coverage_grid.csv` 对齐，使两者可逐点比较 | — | `results/terrain_mesh.obj`、`terrain_scene.xml`、`terrain_render.png` |
| `energy.py` | 节点能量状态：气温随海拔与季节变化，LiFePO4 低温容量衰减与 +5 °C 充电闸门，积雪掩埋，光伏发电 | — | 被其它脚本导入 |
| `energy_model.py` | 太阳能加储能的可行性年扫描，比较电池化学与面板尺寸对年停电天数的影响 | — | `results/energy_model_result.txt` |
| `mountain_lora_feasibility.py` | 早期的可行性脚本，保留作为方法演进的记录 | — | 终端输出 |
| `itm_validate.py`、`itm_test.py` | ITM 的回归检查。平地必须退化为两径地面反射模型，这是发现自由空间损耗常数错了 60 dB 的那次检查 | `mountain_lora_feasibility` | 终端输出 |

## runtime/ — 执行层

早期执行语义实现。这一组与物理层无关，可以单独理解；不等同于 doc52 拟议的完整 obligation runtime。

| 脚本 | 职责 | 依赖 | 输出 |
|---|---|---|---|
| `operations.py` | **三维操作语义**：`lifecycle`（runtime 拥有）、`outcome`（远端效果）、`observation`（agent 的证据）；append-only 日志与恢复；远端 sink 的 epoch fencing 与 operation 回执；运行时不变量的强制。`__main__` 跑五条性质的自检 | — | 终端输出 |
| `disruption_env.py` | 把物理层与执行层接起来的环境：真实地形节点、Gilbert-Elliott 信道、能量模型、分区 / flapping / 重放 / 协调者重启，以及异步的 `dispatch`/`poll` | `operations`、`physics/energy` | 被实验脚本导入 |
| `agent_react.py` | 可切换恢复策略的调度器骨架，含 `MockBackend` 与 `OpenAICompatBackend`。LLM 补充实验的接入点 | `disruption_env` | 终端输出 |

## experiments/ — 实验驱动

| 脚本 | 回答什么问题 | 输出 |
|---|---|---|
| `method_comparison.py` | **主实验**。固定决策轨迹下比较执行运行时，并含协议消融；`--workload mutable_state` 切换到陈旧覆盖专用的可覆盖字段负载；`--relay` 切换到架构与协议的 2×2；`--heated` 与 `--relay-availability` 用于敏感性扫描；`--stale-p`/`--stale-max` 打开传输层延迟投递；`--read-cost-ratio` 给读消息一个相对写入的权重，只作用于加权通信代价、不改变物理空口，用于读写通信成本敏感性 | `results/method_comparison*.json` |
| `mission_sim.py` | 任务级指标：到报率、到达时延分位数、能量、存活节点数。遥测间隔与控制面变更速率是两个独立参数 | `results/mission_sim*.txt/json` |
| `restart_experiment.py` | 协调者重启后 durable lifecycle 是否存续。三种身份来源（每次重发新身份 / 重算同一身份 / 持久日志）× 两类命令（身份可重算的周期测量、身份不可重算的临时处置），全部跑在同一 C1 + C2 远端上。记分按任务原本想执行的那一条身份计，另计『非请求副作用』：重发时换了身份，落地的是任务没要求的动作 | `results/restart_experiment.*` |
| `monitoring_trajectories.py` | **业务层全量对照**。七条轨迹（无故障 + 契约 §5 六类）× 全部业务臂（`policies.BUSINESS_ARMS`：本地规则 / 版本化配置 / VTC 风格 / 本文 runtime / oracle），分辨率含四项业务指标、机会账目与远端契约计数，并保存 per-seed 值供配对比较。README §7.21 的读数由它产生 | `results/monitoring_trajectories*.json` |
| `sensitivity.py` | **契约 §9 第②项：通信机会与断连敏感性**。两条轴分开扫——每次上行给几个下行机会（机会供给）、回传中断时长（断连），读数含覆盖、观测空窗、unknown 时长、AoI、下行次数与残余失败分类。两条轴不合成一个鲁棒性分数：机会供给帮助的是命令能不能送到，中断时长考验的是送不到之后怎么收场 | `results/sensitivity*.json` |
| `test_failure_model.py` | 11 类故障的确定性验证，每类一个定向用例，退出码 0 表示全部可复现 | 终端输出 |
| `test_draw_keys.py` | 报文级随机契约的回归测试：同一逻辑操作在不同 runtime 间配对、不同逻辑操作不共用抽样、抽样不受其它操作数量影响，且到达/应答/扣留/扣留时长/中继投递五类随机量都带逻辑操作身份 | 退出码 |
| `test_journal_schema.py` | 持久日志 schema 回归：写入侧拒绝未知 kind 与字段集不符；重放侧先校验整条日志再构造状态，未知 kind、版本不符、多字段、缺字段一律拒绝恢复。两个条目族（注册表 / 决策）版本独立 | 退出码 |
| `test_interfaces.py` | 四个接口与可审计证据：曾生效与当前生效分开记录、超时保持未知、状态读优先用被动遥测（超期才消耗机会）、新采集不能由旧缓存冒充、发送游标与确认游标不是同一个数、审计链字段完整、端侧效果真实发生而非仅收到确认 | 退出码 |
| `test_opportunity.py` | 控制面机会模型的回归测试：下行机会数 ≤ 上行次数 × 每次上行额度（按**尝试次数**而非成功投递计）；空口时间含前导、头部与编码率并与独立算式逐值比对；同节点同小时的不同逻辑操作不共享结局；无上行则无下行；回传中断在中心侧拒绝而非静默丢弃；接收窗口在每次上行后计费 | 退出码 |
| `audit_consistency.py` | 一致性审计：远端观测是否全部经链路、环境轨迹是否对所有 arm 一致、覆盖是否为真实领域状态覆盖、重启恢复是否只依赖持久状态、中继是否绕开遮挡路径、延迟请求是否不计下行、README 各表是否与结果文件逐行对齐 | 退出码 |
| `run_baseline.py` | 执行层故障的复现与机制确认：重复副作用、丢失、过期读取 | `results/baseline_experiment.txt` |

## analysis/ — 数据处理

从真实轨迹拟合参数，不参与仿真运行。

| 脚本 | 职责 | 输出 |
|---|---|---|
| `paired_ci.py` | 配对比较：把同一 seed 下两两 runtime 的差值取 95% t 区间，并逐 seed 检查重复/乱序/覆盖这类计数指标是否真的每个 seed 都为 0。结果文件保存 per-seed 值以便此步 | 终端输出 |
| `fit_loss_model.py` | 从 ChirpBox 逐小时快照重构每条有向链路的通断序列，拟合 Gilbert-Elliott 两态链，并与同丢失率的 i.i.d. 模型对照 | `results/loss_model.json` |
| `fit_outage_distribution.py` | 中断时长的**分布**拟合：指数、对数正态、Weibull 三种的 MLE、KS 距离与 AIC，连同类未删失段的经验分位数 | `results/outage_distribution.json` |
| `trace_to_episode.py` | 把 IODA 的真实断网轨迹转成 episode 的早期概念验证 | 终端输出 |
| `steady_gap.py` | 无故障稳态下单体 runtime 与组合式 runtime 的差距归因：14 条配置各改一处（参数逐项放宽 + 三条结构性消融），同部署同需求同能量同机会额度 | `results/steady_gap_<tag>.json` |
| `fit_link_sources.py` | 从**两个独立来源**拟合链路两态结构并换算到同一时间粒度：ChirpBox（上海，小时级，读 `results/loss_model.json`）与 **LoRa-on-Ice（南极冰面，原始 10 s，本地 `data/downloads/lora_on_ice/`）**。**必须同粒度比**，否则突发度会被尝试速率污染 | 终端输出 |
| `make_irradiance_csv.py` | 把 NASA POWER 的原始 JSON 派生成本实例读的 CSV，**并核对哈希与观测区间**（行数、辐照峰值、气温上下限、≥5 °C 小时数）——对不上就报错，不要只改脚本里的期望值 | 原地重写 `data/downloads/nasa_power_irradiance/*.csv`，终端打印核对结果 |
| `steady_gap_counters.py` | 同一 runtime 的逐分支决策计数（`skip/in_flight` 及其中「有 W1 请求未结」的占比），为上面那条归因提供支撑证据 | `results/steady_gap_counters_<tag>.json` |

## 约定

**真值来自环境，不来自 agent 的信念。** 所有实验脚本的重复副作用、丢失、零执行等计数都从环境的 ground truth 取，不采信策略自己的判断。

**参数带证据层。** 系统模型中的每个参数标 M（实测）、S（标准模型）、F（拟合）、A（假定）。A 层必须做敏感性扫描，不能当作实测值报告。

**确定性优先。** 故障类的验证用定向构造而非随机命中；实验用固定种子，可复现。
- `analysis/regime_map.py`：**两轴结构判据**（`C = T_report/T_deadline` 与 `R = P(T_ctrl > T_harm)`）。`T_ctrl` 生存曲线由两态链吸收式 DP 精确算出、`T_harm^worst` 手算可核。`--selftest` 手算核对、`--blind` 盲测。见 `docs/s7-method/instance-v1/21-...`
- `analysis/pareto_front.py --with-harm`：把损害（缺采 / 不可供电节点小时）加入目标族重算前沿。**实测 284/285 个文件前沿不变**——见 `docs/s7-method/instance-v1/22-...`
- `protocols/llm_naive_v1.json`：**真实 LLM naive baseline 的冻结协议**（模型 / prompt 原文 / 状态与动作模式 / 条件与 seed / 预算 caps / 成本模型 / 预注册判据）。**代码不复制其中任何字符串**——`llm_naive_baseline.py` 从它读取并记录 `protocol_sha256`，跑前 `protocol_guard()` 校验未被改动。见 `docs/s7-method/instance-v1/26-...`
- `analysis/llm_naive_baseline.py`：按上述协议跑真实 LLM 的 **naive** planner（每 60 s epoch 一次调用、`thinking` 显式关闭、硬预算闸门 `max_calls=4500` 等）。`--smoke` 用 `call_limit=3` 只验管道。
