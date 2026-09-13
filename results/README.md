# 结果文件的数据来源

本目录的每个文件都由仓库内的脚本产生，不手工编辑。每条给出：产出脚本、可复现的命令、
配置（种子、时长、臂或轨迹）、以及它可以被引用来说明什么。

**引用规则。** 一个读数要进正文，必须能回答"哪个脚本、哪个命令、哪些种子"。命令里没有
`--seeds` 的结果不得当作主结果；`scripted` 后端产生的任何数字不得当作模型结果。
种子取自**开发区间**（0–999）；测试区间（seed ≥ 10000）除一致性审计外未被触碰。

## 索引

`results/` 只放**当前可引用**的文件。被取代或被缺陷污染的一律移入 `_withdrawn/`，逐条理由见
该目录的 `MANIFEST.md`。**目录结构不按层分，因为每个脚本的输出路径是硬编码的；改动结构会
让 `README.md` 里的复现命令失效。**文件名里的 `2x2v3`、`restart20v4` 等后缀就是命令的
`--tag`，因此命令与文件名一一对应。

引用判据（D29）：文件必须在下面第一张表里、引用时须带 `--seeds`、标 `scripted` 的不得当
模型证据、种子数不足 20 的须注明。

## 一、业务层主结果：`code/experiments/monitoring_trajectories.py`

七条轨迹（无故障加契约 §5 的六类）× 若干臂 × 若干种子。

| 文件 | 命令 | 种子 | 说明什么 |
|---|---|---|---|
| `monitoring_trajectories_business3.json` | `--days 3 --seeds 20 --arms local_rules,versioned_config,vtc_style,ours,oracle --tag business3` | 20 | **业务层定稿表**：五条臂 × 七条轨迹（§六、§7.33、§7.34、§7.35）。§7.34 修好下发顺序之后重跑 |
| ~~`monitoring_trajectories_business2.json`~~ | — | 20 | **已取代**：§7.34 的下发顺序修正之前产出，`ours` 记 89.07 / 604.8，当前代码给 94.53 / 628.9。只有 `local_rules` / `versioned_config` / `vtc_style` / `oracle` 四条未受影响的臂仍可引用 |
| `monitoring_trajectories_2x2v3.json` | `--days 3 --seeds 20 --arms rule__naive,rule__contract,llm__naive,llm__contract --tag 2x2v3` | 20 | **2×2 定稿表**：planner 因子与 runtime 因子的分解（§六）。**用 `scripted` 后端**。四格都是组合实现，不受 §7.34 影响 |
| ~~`monitoring_trajectories_restart20v4.json`~~ | — | 20 | **已作废**（§7.30）：重启对照不公平——本文臂的状态留在活着的对象里，基线被清空。**读数不得引用** |
| `monitoring_trajectories_fairrestart4.json` | `--days 3 --seeds 20 --arms versioned_config,versioned_config_shadow,versioned_config_version_only,vtc_style,vtc_style_durable,ours,ours_amnesiac,ours_reconstructed,oracle --trajectories none,coordinator_restart --tag fairrestart4` | 20 | **恢复归因定稿表**（§7.33）：给基线平等的持久化能力之后，重启轴上本文不再领先。九条臂，含 `vtc_style_durable`（该行的证据只在这个文件里） |
| ~~`monitoring_trajectories_fairrestart2.json`~~ | — | 20 | **已取代**：§7.34 的顺序修正之前产出 |
| ~~`monitoring_trajectories_ablate20.json`~~ | — | 20 | **已撤下**：该文件由旧代码产出，`ours` 记 63.00 / 下行 682.5，而当时的代码给 89.07 / 604.8。**覆盖与下行两列都不一致，与主表不可拼接。** |
| `monitoring_trajectories_ablate20v3.json` | `--days 3 --seeds 20 --arms ours,ours_no_evidence,ours_no_contract,versioned_config,vtc_style --trajectories none,ack_lost,stale_command --tag ablate20v3` | 20 | 两条只改一处的消融与两条强基线的同批对照（§7.35）。`ours` 在 `none` 上记 94.53 / 628.9，**与 `business3` 逐位一致**，故与主表可拼接 |
| ~~`monitoring_trajectories_ablate20v2.json`~~ | — | 20 | **已取代**：§7.34 的顺序修正之前产出 |
| `monitoring_trajectories_paths.json` | `--days 3 --seeds 2 --arms rule__contract --trajectories none --paths backhaul:0.62,backup:0.55 --runtime-paths 0,1 --tag paths` | **2** | 独立管理路径对照：runtime 会发现并使用备用回传 |
| `monitoring_trajectories_paths_primary_only.json` | 同上，`--runtime-paths 0` | **2** | 同部署下只用主路径的对照 |

配对差值与逐种子零值检查：

```bash
python3 code/analysis/paired_ci.py results/monitoring_trajectories_business2.json \
  --arm-a ours --arm-b versioned_config --workload none --zero-check
```

## 一之二、实例层读数：`code/experiments/instance_run.py`

Task Contract v1.1 的实例层。**不做方法比较**，只把当前实例在多个种子下的分列指标落盘。

| 文件 | 命令 | 种子 | 说明什么 |
|---|---|---|---|
| `instance_base.json` | `instance_run.py --seeds 20 --task-hours 12 --tail-hours 1 --tag base` | 20 | 多节点 + 真实地形实例的分列读数：周期新鲜度与完整性、事件采集与交付、传播时延、通信代价、删失 |
| `instance_arms.json` | `instance_run.py --seeds 20 --task-hours 12 --tail-hours 1 --arms local,fixed300,fixed900,aoi,aoi_link --tag arms` | 20 | **中心策略对照**：现场自治 / 固定周期 / 按 AoI 自适应 / 自适应+跳过静默节点，分列报告业务指标与代价 |
| `instance_execlayer.json` | `instance_run.py --seeds 20 --task-hours 12 --tail-hours 1 --arms aoi --exec-layers naive,contract --hold-every 2 --hold-s 14400 --tag execlayer` | 20 | **执行机制诊断**：同一中心策略、同能力同预算，只改报文是否携带稳定逻辑身份与单调版本 |
| `instance_energy_sweep.json` | `instance_run.py --seeds 20 --task-hours 12 --tail-hours 1 --arms local,dense300,…,energy_aware --harvest-mode hetero --low-wh-per-hour 0 --tag energy_sweep` | 20 | **能量绑定的冲突条件**：固定采样间隔扫描 vs 能量感知策略 |
| `instance_ea_sweep.json` | `instance_run.py --seeds 20 --task-hours 12 --tail-hours 1 --arms dense600,energy_aware,ea_h5,ea_h15,ea_h25,ea_i600,ea_i600h5 --harvest-mode hetero --low-wh-per-hour 0 --tag ea_sweep` | 20 | 自适应阈值扫描（保证固定基线与自适应都被调过参数再比） |
| `instance_energy.json` | `--harvest-mode hetero --tag energy` | 10 | 异质采能的过渡读数（能量尚未 binding，见 04 解析 §四） |
| `instance_energy2.json` | `--arms local,dense300,energy_aware --harvest-mode hetero --low-wh-per-hour 0 --tag energy2` | 10 | 同上，接入采样间隔动作之后 |
| `instance_uncertain015.json` | `--arms local,dense600,dense900,dense1200,dense1800,ea_i600 --capacity-wh 0.015 --tag uncertain015` | 20 | **参数不确定性（关键）**：固定配置按名义容量选点、实际容量 0.015 Wh 时崩到 `local` 以下 |
| `instance_nominal050.json` | 同上，`--capacity-wh 0.05 --tag nominal050` | 20 | 名义容量下的对照 |
| `instance_cap0.004.json`、`instance_cap0.008.json`、`instance_cap0.015.json`、`instance_cap0.025.json`、`instance_cap0.05.json`、`instance_cap0.10.json` | `--capacity-wh C --tag capC` | 10 | 电池容量扫描（参数不确定性的核心轴） |
| `instance_blackout0_0.0.json`、`instance_blackout4_0.3.json`、`instance_blackout4_0.6.json` | `--blackout-start-h H --blackout-frac F --capacity-wh 0.02 --tag blackoutH_F` | 10 | **节点失电**：切断部分站点采能 → 后果是**采集缺失**（不可补回）。本轮最强的一组正面读数 |
| `instance_outage_eventoverlap.json` | `--access-outage-h 2 --access-outage-start-h 0.5 --tag outage_eventoverlap` | 10 | 中断窗**叠加事件触发** |
| `instance_lf0.2.json`、`instance_lf0.4.json`、`instance_lf0.6.json`、`instance_lf0.8.json` | `--low-frac F --tag lfF` | 10 | 遮荫比例扫描（对调好的固定配置无影响） |
| `instance_sens_u0.5_b0.62.json`、`instance_sens_u0.74_b0.4.json`、`instance_sens_u0.74_b0.62.json`、`instance_sens_u0.74_b0.85.json`、`instance_sens_u0.9_b0.62.json` | `--arms local,dense600,ea_i600 --uplink-p-arrive U --backhaul-p-good B --tag sens_uU_bB` | 10 | **敏感性**：上行到达率 0.5/0.74/0.9 × 回传可用率 0.4/0.62/0.85 |
| `instance_outage_backhaul.json` | `--outage-start-h 4 --outage-hours 3 --tag outage_backhaul` | 10 | 回传中断 3 h |
| `instance_outage_access.json` | `--access-outage-h 3 --tag outage_access` | 10 | **接入中断 3 h**（节点有电、照常采样，损失全在交付侧） |
| `instance_outage_both.json` | 两者同时 `--tag outage_both` | 10 | 接入 + 回传同时中断 |
| `instance_arms_outage3h.json` | `instance_run.py --seeds 20 --task-hours 12 --tail-hours 1 --outage-start-h 4 --outage-hours 3 --arms local,fixed900,aoi,aoi_link --tag arms_outage3h` | 20 | 同上，外加回传中断 3 h 的恢复分列 |
| `instance_outage3h.json` | `instance_run.py --seeds 20 --task-hours 12 --tail-hours 1 --outage-start-h 4 --outage-hours 3 --tag outage3h` | 20 | 同上，另加**回传中断 3 h** 的恢复分列：采集缺失与交付缺失分开，以及自动补发追回数 |

**实例是什么**：一个监测单元 = 网关带雨量计 + 13 个坡面位移测点（真实 SRTM/ITM 布点，绕射边缘上
的 3 个位点已排除）。业务事件来自 Wang 等 2022 Table 3 的公开片段（7 组触发），常态 1 h 定时。

**读数的效力边界（必须随引用一起写）**：
- 采能是**合成的恒定过程**（A 层），因此**能源相关读数不得外推**；
- 不是真实 trace benchmark，不是任何站点的配置；
- 单一片段、同一天、同一设备 → **只能报案例级诊断，不认领跨站泛化**；
- 不含中心下发动作，因此**不能支持任何"中心改配置更快"类结论**。

## 二、机制层主表：`code/experiments/method_comparison.py`

| 文件 | 命令 | 种子 | 说明什么 |
|---|---|---|---|
| `method_comparison_main20.json` | `--days 180 --seeds 20 --workload operation --tag main20` | 20 | **机制层主表**：11 条臂含公平化的精确版本 CAS 与四条消融（§六）。不经过评分器的到达索引，因而不受 §7.32 影响 |

```bash
python3 code/analysis/paired_ci.py results/method_comparison_main20.json \
  --arm-a ours --arm-b exact_version_cas --workload operation --zero-check
```

**机制层的加热与中继扫描未重跑**，产出它们的脚本版本带有 §7.18 与 §7.23 记录的两处缺陷，
旧输出已移入 `_withdrawn/`。重跑命令：

```bash
for h in 0 0.25 0.5 0.75 1.0; do
  python3 code/experiments/method_comparison.py --days 180 --seeds 20 --workload operation \
    --heated $h --arms one_shot,retry_uncertainty,verified_tool_calls,ours --tag heat$h
done
for a in 0.25 0.5 1.0; do
  python3 code/experiments/method_comparison.py --days 180 --seeds 20 --workload operation \
    --relay --relay-availability $a --arms relay_retry_uncertainty,relay_ours --tag relayav$a
done
```

## 三、敏感性：`code/experiments/sensitivity.py`

| 文件 | 命令 | 种子 | 说明什么 |
|---|---|---|---|
| `sensitivity_full.json` | `--days 3 --seeds 3 --arms versioned_config,ours,rule__contract,rule__naive --opportunities 1,2,4 --outages 0,2,6,12 --tag full` | **3** | (F)②：(a) 机会额度轴、(b) 回传中断轴（§7.28）。**3 个种子，不得作主结果** |

## 四、系统策略案例研究：`code/experiments/mission_sim.py`

| 文件 | 命令 | 种子 |
|---|---|---|
| `mission_sim_year.json` | `--days 365 --seeds 5 --tag year` | 5 |
| `mission_sim_relay.json` | `--days 365 --seeds 3 --tag relay` | 3 |
| `mission_sim.json`、`mission_sim.txt` | 30 天 / 1 种子 | 1 |

**定位。** 系统策略案例研究，不是 agent 基线：它的策略不含执行层的身份、回执与调和，不能
回答"runtime 有什么用"。**`per_seed` 为空**，做配对比较需先补逐种子记录。这三个文件的产出
时间早于本轮全部修复，但其策略与评分不经过业务层或机制层被修的那几处，**未复核**。

## 五、物理层：地形、传播、信道与能量

不受执行层任何修复影响，全部保留。

| 文件 | 产出脚本 | 命令 | 说明什么 |
|---|---|---|---|
| `coverage_grid.csv`、`coverage_summary.txt`、`coverage_map.png` | `code/physics/coverage_map.py` | `python3 code/physics/coverage_map.py` | 121×121 网格的可达率、SF 分布与不可达点数（地形死区 88.5%）。依赖 `data/dem/hgt` |
| `coverage_rerun.log` | 同上 | 同上 | 上述一次重跑的终端记录 |
| `itm_constant_check.txt` | `code/physics/itm_validate.py` | `python3 code/physics/itm_validate.py` | ITM 在平地必须退化为两径地面反射模型。这是发现自由空间损耗常数错了 60 dB 的那次检查 |
| `los_vs_itm.json` | `code/physics/los_vs_itm.py` | `python3 code/physics/los_vs_itm.py --samples 700 --scales 1,7,27` | 视距与 ITM 的逐点对照，以及一组按固定规则取出的遮挡-距离对照：4.06 km/1029 m 遮挡 198.8 dB 对 14.40 km/74 m 遮挡 190.2 dB，近的反而差 8.6 dB。**遮挡而非距离**。三档剖面分辨率下可达点均为 1689/14641，即 88.5% 死区 |
| `mountain_lora_result.txt` | `code/physics/mountain_lora_feasibility.py` | 同上 | 早期可行性脚本的终端输出，保留作方法演进记录 |
| `loss_model.json`、`loss_model.txt` | `code/analysis/fit_loss_model.py` | `python3 code/analysis/fit_loss_model.py` | 从 ChirpBox 逐小时快照重构有向链路通断序列，拟合 Gilbert-Elliott 两态链并与同丢失率的 i.i.d. 对照。可用率 68.75%，均值下行突发 6.38 h、上行 14.04 h，突发度 4.4×，i.i.d. 预测 1.45 h。依赖 `data/downloads/chirpbox.csv` |
| `outage_distribution.json`、`outage_distribution.txt` | `code/analysis/fit_outage_distribution.py` | `python3 code/analysis/fit_outage_distribution.py` | 中断时长的分布拟合（指数 / 对数正态 / Weibull 的 MLE、KS 与 AIC）及未删失段经验分位数。依赖同上 |
| ~~`heating_sweep.txt`~~ | — | **已归档**：产出它的 `method_comparison.py` 版本带 §7.18 与 §7.23 记录的缺陷；重跑命令见第二节 |
| `energy_model_result.txt`、`energy_model_after_fix.txt` | `code/physics/energy_model.py` | `python3 code/physics/energy_model.py` | 太阳能加储能的年扫描，比较电池化学与面板尺寸对年停电天数的影响。两个文件是发电量规则修正前后的对照 |
| `terrain_mesh.obj`、`terrain_scene.xml`、`terrain_render.png`、`terrain_mesh.json` | `code/physics/dem_to_mitsuba.py` | `python3 code/physics/dem_to_mitsuba.py` | SRTM 瓦片转三角网格与 Mitsuba 场景，格点与 `coverage_grid.csv` 对齐以便逐点比较。依赖 `data/dem/hgt` |
| `relay_siting_summary.txt`、`relay_run.log` | `code/physics/relay_siting.py`、`code/physics/coverage_map.py` | 见 `code/README.md` | 带高程与坡度约束的中继选址，与无约束版本互为对照 |
| ~~`relay_availability_sweep.txt`~~、~~`sweeps.log`~~ | — | **已归档**：同上（`method_comparison.py` 的中继可用度扫描）；重跑命令见第二节 |

## 六、稳态差距归因：`code/analysis/steady_gap.py`

无故障稳态（trajectory `none`）下 `ours` 与 `rule__contract` 之间 5.3 个点的来源归因。
14 条配置各改一处，同部署、同需求、同能量、同机会额度。结论见
`docs/s8-report/q3-steady-state-gap.md`。

| 文件 | 命令 | 种子 | 说明什么 |
|---|---|---|---|
| `steady_gap_q3_attrib.json` | `--seeds 20 --tag q3_attrib` | 20 | 每条臂的覆盖率/观测空窗/下行次数：参数逐项放宽 + 三条结构性消融（W1 关闭、W3 先于 W1、去 in-flight 否决） |
| `steady_gap_counters_q3_attrib.json` | `steady_gap_counters.py --seeds 20 --tag q3_attrib` | 20 | 同一 runtime 的逐分支决策计数：`skip/in_flight` 与其中「有 W1 请求未结」的占比 |
| `steady_gap_w1postfix.json` | `steady_gap.py --seeds 20 --arms "ours,ours W1 off,rule__contract" --tag w1postfix` | 20 | **W1 边际值的定稿读数**（§7.36）：修好下发顺序之后，保留 W1 值 +0.16 点、多花 305 次下行 |
| `steady_gap_q3_dpu2.json` | `--seeds 20 --tag q3_dpu2 --downlink-per-uplink 2 --arms "ours,rule__contract,ours W3 before W1"` | 20 | **机制验证，不是场景结论**：`downlink_per_uplink` 是 Class A 之外的假设（冻结场景是 1），只用来检验"队首阻塞"这条机制——把它提到 2，5.34 个点里的 4.77 点无需改任何代码就消失 |

```bash
export PYTHONPATH="$PWD/libs/pylibs"
python3 code/analysis/steady_gap.py --seeds 20 --tag q3_attrib
python3 code/analysis/steady_gap_counters.py --seeds 20 --tag q3_attrib
python3 code/analysis/steady_gap.py --seeds 20 --tag q3_dpu2 --downlink-per-uplink 2 \
  --arms "ours,rule__contract,ours W3 before W1"
```

## 七、已撤销

`_withdrawn/MANIFEST.md` 逐条列出被删除的结果文件及其失效原因。被删的文件在 git 历史里
仍可找回，但**不得**再用作证据。三条撤销主线：

1. `verified_tool_calls` 的保真度缺陷（`want` 被覆盖使 Unknown 从不等待、verify/reconcile
   绕过链路、日清理用固定预算），使"Verified 有天花板"与"预算 20 下追平"两条结论作废。
2. 业务层把网关与中心合并、四接口只通一个、四条臂里没有本文 runtime。
3. 精确版本 CAS 被做成每次写前必读，违反契约 §7 的公平性要求，据此得出的"更严契约净亏"
   作废。

## 八、未纳入本目录的中间产物

`data/` 是**输入**不是结果。它的来源见 `data/README.md`，逐条复现命令与"跑对了的标志"
见 `data/REPRODUCE.md`。`libs/` 是第三方依赖。
`results/` 下不再保留构建缓存（原 `.drjit-cache/` 已删除，可重新生成）。
