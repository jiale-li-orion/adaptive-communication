# 部署条件（冻结实例 v1.1）

**地位**：论文系统模型一节据本节呈现，引用部署条件时引用本节。本节数值是**从代码读出的当前真值**，不是设计意图；改代码就改这里，两边不一致时以代码为准，并由 `code/run_checks.py` 的检查 [11] 判定。

**来源**：摘自作者本地的过程文档 `docs/s7-method/instance-v1/02-instance-manifest.md` §三·〇（该文件不随仓库发布）。抽取时未改动任何数值。

层标：**E** 来源事实／**A** 研究选择／**M** 本项目实现。

| 组 | 项 | 值 | 层 | 状态 |
|---|---|---|---|---|
| **站点** | 网关坐标 | **30.33 N, 94.78 E**（`GATEWAY_LAT/LON`，藏东南山地） | A | 确定 |
| | 网关海拔 | **2317 m** | E（SRTM1 读出） | 确定 |
| | 地形瓦片 | `N30E094`、SRTM1 v3、1 弧秒（约 30 m） | E | 确定 |
| | 频段 | **868 MHz** | A | 确定（与重庆核准频段不同，是 A 选择） |
| **拓扑** | 组 0 | 中心正北 **1500 m**，站间距 220 m | A | 确定 |
| | 组 1 | 中心东南 **(+1768, −1768) m**，站间距 220 m | A | 确定 |
| | 位点稳定性检验 | 每站按半径 `STABILITY_M = 2.0 m` 扰动检验；排除 `n12`/`n14`/`n17`（绕射边缘） | M | 确定 |
| | **实际节点数** | **14**：网关 `gw0`（测项 `rainfall`）+ **13 个位移站** `n00…n16`（测项 `displacement`） | M | 确定（已实测点数） |
| | 坐标精度 | **不四舍五入**（四舍五入到 5 位小数约 1 m，曾让两个节点损耗摆动 65–70 dB） | M | 确定 |
| **时间** | tick | `TICK_S = 60 s` | M | 确定 |
| | 任务与尾部 | 12 h + **1 h 尾部观察期** | A | 确定 |
| | 常态义务周期 | `ROUTINE_PERIOD_S = 3600 s`，窗 = 周期（`[rel, rel+3600]`） | E | 确定 |
| | 事件节奏 | 触发 + `EVENT_SPACING_S = 300 s` × `EVENT_SLOTS = 3` | E | 确定 |
| **能量** | 单条采样能耗 | `sample_wh = 4.7e-4 Wh`（活跃 15 s × 35.7 mA @ **3.3 V**，传感器母线，来自实测剖面；与空口的 `BUS_V = 3.6` 不是同一个量；已扣空口） | A | 确定（**取代旧表的 2e-5**） |
| | 电池容量 | 名义 `0.05 Wh`；扫描轴 0.001–0.05 | A | 确定 |
| | 初始电量 | `initial_soc`（比例）× 容量；默认 1.0，扫描用 0.05–1.0 | A | 确定 |
| | 静息功耗 | `idle_wh_per_tick = 0.0`（**没有静息项**，耗电全在采样与空口） | A | 确定 |
| | 低温闸门 | `charge_min_c = 5.0`、`cold_ref_c = −20.0`、`capacity_at_cold = 0.5` | A | 确定接口；v1.1 §8 明令不得固定翻译成某一种电池的冬季阈值 |
| | 空口能耗 | `opportunity.RadioEnergy` 按空口时间计，`BUS_V = 3.6` 母线；实测约 **2.33e-5 Wh/次上行**、**rx 窗口 2.2e-5 Wh/次** | M（由 A 参数导出） | 确定 |
| **采能** | 异质（默认主用） | `hetero_harvest`：`low_frac = 0.4` 站点采能 `low_wh_per_hour`（默认 **0**）、其余 `high_wh_per_hour`（默认 **3.0**） | A | 确定 |
| | 日照（合成） | `solar_harvest`：正弦日照窗 + 逐小时云遮 + 积雪归零 | A（合成，非拟合） | 确定，须标合成 |
| | **日照（来源派生）** | `irradiance_harvest`：**NASA POWER 2023 逐小时** `ALLSKY_SFC_SW_DWN`（Wh/m²）与 `T2M`，坐标与部署点逐位相同 | E（再分析产品） | 见 `data/downloads/nasa_power_irradiance/SOURCE.md` |
| **链路** | 上行被听到概率 | `uplink_p_arrive = 0.74` | A | 确定 |
| | 回传可用概率 | `backhaul_p_good = 0.62`（按小时抽签，store-and-forward） | A | 确定 |
| | 信道模型依据 | `data/downloads/chirpbox.csv` 拟合的 Gilbert-Elliott 两态链 + ITM 逐链路 | E→M | 确定 |
| | 下行机会 | Class A：**一次上行至多一次下行**（`downlink_per_uplink`） | E | 确定 |
| **存储** | 节点缓存 | 按**条数**，`cache_slots = 240`，溢出**丢最老**并计数 | A | 确定 |

## 为什么这一节单独存在

部署条件是系统模型一节唯一的数字来源。它们此前散落在 `deployment.py`、`network.py`、`results/README.md` 与若干分析章节里，已经出现过同一件事两处写法不一致：采样能耗曾长期停在已作废的 `2e-5 Wh`，而实现早已是 `4.7e-4 Wh`。这类不一致不会自己报错，只会让引用它的人算错，因此检查 [11] 对每个数值项逐一比对代码实算值。

## 与代码的对应

`deployment.py` 提供站点几何与瓦片（`GATEWAY_LAT`、`GATEWAY_LON`、`GATEWAY_ELEV_M`、`TILE`）；`network.py` 的 `DeviceProfile` 提供 `sample_wh`、`charge_min_c`、`idle_wh_per_tick`、`cache_slots`；节点数与测项分布由 `nodes_from(build_deployment(groups=2))` 实算。
