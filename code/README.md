# 代码结构

四组，按职责划分。每组内部的脚本可以互相导入，跨组导入由每个脚本头部的模块引导块保证。

```
code/
├── physics/        物理层：地形、传播、信道时间结构与能量
├── runtime/        执行层：操作语义与环境
├── experiments/    实验驱动：主表、任务仿真、重启、故障验证
└── analysis/       数据处理：从真实轨迹拟合参数
```

各脚本头部注明依赖与输出，运行方式见仓库根目录 `README.md` 第七节。

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

论文方法的主体。这一组与物理层无关，可以单独理解。

| 脚本 | 职责 | 依赖 | 输出 |
|---|---|---|---|
| `operations.py` | **三维操作语义**：`lifecycle`（runtime 拥有）、`outcome`（远端效果）、`observation`（agent 的证据）；append-only 日志与恢复；远端 sink 的 epoch fencing 与 operation 回执；运行时不变量的强制。`__main__` 跑五条性质的自检 | — | 终端输出 |
| `disruption_env.py` | 把物理层与执行层接起来的环境：真实地形节点、Gilbert-Elliott 信道、能量模型、分区 / flapping / 重放 / 协调者重启，以及异步的 `dispatch`/`poll` | `operations`、`physics/energy` | 被实验脚本导入 |
| `agent_react.py` | 可切换恢复策略的调度器骨架，含 `MockBackend` 与 `OpenAICompatBackend`。LLM 补充实验的接入点 | `disruption_env` | 终端输出 |

## experiments/ — 实验驱动

| 脚本 | 回答什么问题 | 输出 |
|---|---|---|
| `method_comparison.py` | **主实验**。固定决策轨迹下比较四种执行运行时，并含协议消融；`--relay` 切换到架构与协议的 2×2；`--heated` 与 `--relay-availability` 用于敏感性扫描；`--stale-p`/`--stale-max` 打开传输层延迟投递，写入跨过链路后被网络扣留若干小时再释放，用于时间乱序与陈旧覆盖 | `results/method_comparison*.txt/json` |
| `mission_sim.py` | 任务级指标：到报率、到达时延分位数、能量、存活节点数。遥测间隔与控制面变更速率是两个独立参数 | `results/mission_sim*.txt/json` |
| `restart_experiment.py` | 协调者重启后 durable lifecycle 是否存续。三种身份来源（每次重发新身份 / 重算同一身份 / 持久日志）× 两类命令（身份可重算的周期测量、身份不可重算的临时处置），全部跑在同一 C1 + C2 远端上。记分按任务原本想执行的那一条身份计，另计『非请求副作用』：重发时换了身份，落地的是任务没要求的动作 | `results/restart_experiment.*` |
| `test_failure_model.py` | 11 类故障的确定性验证，每类一个定向用例，退出码 0 表示全部可复现 | 终端输出 |
| `run_baseline.py` | 执行层故障的复现与机制确认：重复副作用、丢失、过期读取 | `results/baseline_experiment.txt` |

## analysis/ — 数据处理

从真实轨迹拟合参数，不参与仿真运行。

| 脚本 | 职责 | 输出 |
|---|---|---|
| `fit_loss_model.py` | 从 ChirpBox 逐小时快照重构每条有向链路的通断序列，拟合 Gilbert-Elliott 两态链，并与同丢失率的 i.i.d. 模型对照 | `results/loss_model.json` |
| `fit_outage_distribution.py` | 中断时长的**分布**拟合：指数、对数正态、Weibull 三种的 MLE、KS 距离与 AIC，连同类未删失段的经验分位数 | `results/outage_distribution.json` |
| `trace_to_episode.py` | 把 IODA 的真实断网轨迹转成 episode 的早期概念验证 | 终端输出 |

## 约定

**真值来自环境，不来自 agent 的信念。** 所有实验脚本的重复副作用、丢失、零执行等计数都从环境的 ground truth 取，不采信策略自己的判断。

**参数带证据层。** 系统模型中的每个参数标 M（实测）、S（标准模型）、F（拟合）、A（假定）。A 层必须做敏感性扫描，不能当作实测值报告。

**确定性优先。** 故障类的验证用定向构造而非随机命中；实验用固定种子，可复现。
