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
| `instance_execlayer.json` | `instance_run.py --seeds 20 --task-hours 12 --tail-hours 1 --arms aoi --exec-layers naive,contract --hold-every 2 --hold-s 14400 --tag execlayer` | 20 | **执行机制诊断（单字段策略）**：同一中心策略、同能力同预算，只改报文是否携带稳定逻辑身份与单调版本。该臂只下发 `set_report_period`，因此不受身份缺字段维度的缺陷影响，读数仍有效 |
| `instance_exec_layer_20s_v2.json` | `instance_run.py --seeds 20 --task-hours 12 --tail-hours 1 --arms local,ea_i600,dense600,aoi --exec-layers naive,contract,atomic --hold-op set_sampling_interval --hold-s 10800 --harvest-mode hetero --low-wh-per-hour 0 --capacity-wh 0.05 --tag exec_layer_20s_v2` | 20 | **三层执行层对照（能量宽松区）**：交付不动或变差、AoI 一律变差，唯一收益是上行 −19.5%。执行层在这一区是代价机制 |
| `instance_exec_layer_nohold_v2.json` | 同上但去掉 `--hold-op/--hold-s --tag exec_layer_nohold_v2` | 20 | **不扣留的对照**：`contract` 与 `naive` 逐列全同（连上行都一样）→ 契约字段只在乱序/延迟下起作用；`atomic` 的 AoI 代价**不是扣留造成的**（不扣留照样 +199/+205 s）；混配常态即 1422 min |
| `instance_exec_layer_bind0.008v2.json`、`instance_exec_layer_bind0.004v2.json` | 同 20s_v2 但 `--arms ea_i600,dense600,aoi --capacity-wh 0.008\|0.004 --tag exec_layer_bind…v2` | 20 | **三层执行层对照（能量绑定区）**：`dense600` 上交付 122.2→131.1→**132.2**、缺采 33.5→24.8→**22.6**、亏空 41.7→32.6→**29.6 h**，随层级单调；容量再小一半同序复现。执行层在这一区是正确性机制 |
| `instance_oodoracle_C1.json`、`instance_oodoracle_C2.json`、`instance_oodoracle_C3.json`、`instance_oodoracle_C4.json`、`instance_oodoracle_C5.json`、`instance_oodoracle_C6.json`、`instance_oodoracle_C7.json` | `instance_run.py --seeds 20 --task-hours 12 --tail-hours 1 --arms local,dense300,…,dense1800,ea_i600 --harvest-mode hetero --low-wh-per-hour 0 --dynamic-oracle --capacity-wh C [--blackout-start-h 4 --blackout-frac F] [--low-frac G] --tag oodoracle_Cn` | 20 | **OOD regret 换用真上界重算（主结果）**：七条件同 ⑨，但分母从"事后最优固定配置"换成真上界。**七条条件的真上界全部是 168.0**——整个 OOD 轴落在上界饱和区 |
| `instance_oodoracle_cap0.006.json`、`instance_oodoracle_cap0.004.json`、`instance_oodoracle_cap0.002.json`、`instance_oodoracle_cap0.001.json` | 同上但 `--capacity-wh 0.006\|0.004\|0.002\|0.001`，臂增加 `ea_nb` | 20 | **把 OOD 轴伸进上界真正绑定的区间**：12 h 按 3600 s 采样只需 `12×4.93e-4 = 5.9e-3 Wh`，所以容量 ≥0.008 时上界必然饱和。真上界 162.6 / 146.2 / 124.4 / 113.5。固定 `dense600` 的 regret 峰值 33.4%，反馈 `ea_nb` 恒在 8.8–13.5% |
| `instance_my2022_cold_goff.json`、`instance_my2022_cold_g5.json`、`instance_my2022_warm_goff.json`、`instance_my2022_warm_g5.json`、`instance_my2023_cold_goff.json`、`instance_my2023_cold_g5.json`、`instance_my2023_warm_goff.json`、`instance_my2023_warm_g5.json`、`instance_my2024_cold_goff.json`、`instance_my2024_cold_g5.json`、`instance_my2024_warm_goff.json`、`instance_my2024_warm_g5.json` | `--seeds 10 --arms local,aoi,dense600,ea_nb,eh_aoi --harvest-mode irradiance --irr-year Y --irr-start-h S --charge-min-c off|5 --irr-peak-wh-per-hour 0.02 --capacity-wh 0.006 --dynamic-oracle --tag my*` | 10 | **多年份（2022/2023/2024）冷/暖窗口 × 闸门**。**⚠ 这批的窗口选择有缺陷**：按「最低气温最小」选的 12 小时窗在三年里**采能全为 0**，于是年份与闸门都无关紧要（`can_charge and harvest > 0` 永不成立）——是**选择判据把要检验的量归零了**，与相位锁定同类。保留作为该陷阱的证据 |
| `instance_dec4_c0.05.json`、`instance_dec4_c0.008.json`、`instance_dec4_c0.004.json` | `--seeds 20 --task-hours 12 --tail-hours 1 --arms local,aoi,aoi_f600,aoi_t7200,dense600,ea_nb --harvest-mode hetero --low-wh-per-hour 0 --capacity-wh 0.05|0.008|0.004 --dynamic-oracle --tag dec4_c*` | 20 | **交付四分解**（`168 = 交付 + 转发损 + 择时损 + 采集损 + 链路损`，恒等式逐条成立）：**转发损恒 1.1–2.1、链路损恒 9.1（与臂无关）**；择时损是策略能动的一维（`aoi` **1.4–1.5** vs `local`/`ea_nb` **7.3–7.9**）；采集损只在绑定条件出现（0.05 时 0.0、0.008 时 2.3–2.5、0.004 时 22.7–28.2，`dense600` 最惨 41.2/47.9）。**回答「同一物理链路下再聪明的发送调度最多还能拿回几条」：只优化转发 1–2 条；再优化发送时刻 1.4–7.9 条（`aoi` 只剩 1.4）；怎么都拿不回 9.1 条** |
| `instance_gy2022_s2622_goff.json`、`instance_gy2022_s2622_g5.json`、`instance_gy2023_s3174_goff.json`、`instance_gy2023_s3174_g5.json`、`instance_gy2024_s3174_goff.json`、`instance_gy2024_s3174_g5.json` | 同上但窗口按「**闸门挡掉最多采能**」选（`--tag gy*`） | 10 | **闸门效应的决定性证据（三年逐位相同）**：该窗口辐照充足（2022 **8112** / 2023 **8380** / 2024 **7723** Wh/m²）而整段气温低于 5 °C，闸门挡掉 **100%**。闸门 off→on：`dense600` **91.0% → 21.1%**、`aoi` 91.7% → 77.1%。**三年结果逐位相同** ⇒ 闸门与采能的冲突**不是 2023 单年偶然** |
| `instance_idle_0.json`、`instance_idle_5e-8.json`、`instance_idle_2e-7.json`、`instance_idle_1e-6.json` | `--seeds 10 --task-hours 12 --tail-hours 1 --arms local,aoi,dense600,ea_nb,eh_aoi --harvest-mode hetero --low-wh-per-hour 0 --capacity-wh 0.004 --idle-wh-per-tick 0|5e-8|2e-7|1e-6 --dynamic-oracle --tag idle_*` | 10 | **A 层：静息功耗敏感性**（0 → 3.6e-3 Wh/h）。`dense600` **恒定 72.9%**（不受影响），`aoi` 87.2→84.8、`ea_nb` 86.4→83.8。**cliff 依然存在**（72.9 vs 84.8–87.2）——即使静息达到名义负载的 7.3 倍 |
| `instance_gate_off.json`、`instance_gate_0.json`、`instance_gate_5.json`、`instance_gate_10.json` | `--seeds 10 --task-hours 12 --tail-hours 1 --arms local,aoi,dense600,ea_nb,eh_aoi --harvest-mode irradiance --irr-start-h 2190 --irr-peak-wh-per-hour 0.02 --capacity-wh 0.006 --charge-min-c off|0|5|10 --dynamic-oracle --tag gate_*` | 10 | **A 层：低温充电闸门（决定性）**。该窗口气温 **−7.6…−1.8 °C**，13 小时全在 0 以下 ⇒ `0/5/10` 三个阈值**都完全阻断充电、结果逐位相同**；只有 `off` 是另一个状态。**闸门把 `dense600` 从 85.4% 打到 21.1%（−64 点）**。⇒ 真实天气窗口下 cliff 的**严重程度由一个没有来源支撑的 A 层器件参数决定** |
| `instance_scale_0.25.json`、`instance_scale_1.json`、`instance_scale_4.json`、`instance_scale_16.json` | `--seeds 10 --task-hours 12 --tail-hours 1 --arms local,aoi,dense600,dense1800 --harvest-mode hetero --low-wh-per-hour 0 --capacity-wh 0.004 --harvest-wh-per-hour 3.0 --energy-scale 0.25|1|4|16 --dynamic-oracle --tag scale_*` | 10 | **能量尺度不变性（决定性）**：整个能量系统（采样能耗、电池容量、空口母线、采能、上界上行能耗）同时乘以 λ，**四条无能量阈值臂的每一列在 λ∈{0.25,1,4,16} 下逐位相同**。⇒ 该实例的能量轴是**无量纲**的，**绝对 Wh 不是现实部署数值**；论文必须改用无量纲自主小时数 `A₀ = soc₀·C/(sample_wh+uplink_wh)` |
| `instance_front2_c0.05.json`、`instance_front2_c0.008.json`、`instance_front2_c0.004.json` | `--seeds 20 --task-hours 12 --tail-hours 1 --arms local,aoi,aoi_f600,aoi_t7200,aoi_t1800,aoi_s3600,aoi_const300,dense600,ea_nb,eh_aoi,eh_aoi_t1800 --dynamic-oracle --harvest-mode hetero --low-wh-per-hour 0 --capacity-wh 0.05|0.008|0.004 --tag front2_c*` | 20 | **传统基线的完整 Pareto frontier**（四目标：服务↑、上行↓、下行↓、AoI↓）。cap 0.05 下 **11 个点里 9 个非支配**，而 `aoi` **自己被支配**（`aoi_f600` 同服务上行更低、`aoi_t7200` 同服务下行低一半）。含文献结构 `eh_aoi`（(电量,年龄) 二维联合门限）与固定周期端点 `aoi_const300`。有效前沿：`local`（零中心控制）→ `ea_nb`/`eh_aoi` → `aoi_t7200`/`aoi_f600`/`aoi_const300` |
| `instance_do_c0.05.json`、`instance_do_c0.008.json`、`instance_do_c0.004.json` | `--seeds 20 --task-hours 12 --tail-hours 1 --arms local,aoi,dense600,dense1800,ea_nb --harvest-mode hetero --low-wh-per-hour 0 --capacity-wh 0.05|0.008|0.004 --dynamic-oracle --tag do_c*` | 20 | **发送侧三分解**（`168 = 实际交付 + 转发损 + 择时损 + 链路损`）：转发损恒 **1.1–2.1**、链路损恒 **9.1**、自由上界恒 **158.9**，三项都与臂无关；择时损才是策略能动的一维，`aoi` 把宽松区余量从 7.3 压到 **1.4**。**限定**：自由上界假设样本总存在，故中间项同时含「发送时刻」与「采集缺失」，绑定区大数主要是后者 |
| `instance_v2_a_0.05.json`、`instance_v2_a_0.008.json`、`instance_v2_a_0.004.json` | `--seeds 20 --task-hours 12 --tail-hours 1 --arms local,aoi,dense600,dense1800,ea_nb,ea_aoi --harvest-mode hetero --low-wh-per-hour 0 --capacity-wh 0.05|0.008|0.004 --dynamic-oracle --tag v2_a_*` | 20 | **修正 counterfactual 污染后的基线重跑（新链路流）**：下行抽签键从 `message.identity`（全局命令序号）改为 `(node_id, opportunity_index, slot)`，使潜在结果与策略无关。数值仅在第三位有效数字上变动，**定性结论不变**：`aoi` 仍三条件最高（92.5/91.0/87.6%）。**旧流与新流的数字不得混用** |
| `instance_base_a1_005.json`、`instance_base_a2_008.json`、`instance_base_a3_004.json` | `--seeds 20 --task-hours 12 --tail-hours 1 --arms local,aoi,dense600,dense1800,ea_nb,ea_aoi --dynamic-oracle --capacity-wh 0.05|0.008|0.004 --tag base_a*` | 20 | **最强传统基线对照**：`aoi` 在三个条件下都最高（92.7 / 91.3 / 87.8%），高于 `ea_nb`（91.2 / 87.6 / 87.0%）与最优固定 `dense600`（91.9 / 67.7 / 73.5%）。**基线以 `aoi` 为底，不是 `ea_nb`** |
| `instance_soc2_bias0.7.json`、`instance_soc2_bias1.0.json`、`instance_soc2_bias1.4.json`、`instance_soc2_bias2.0.json`、`instance_soc2_bias3.0.json`、`instance_soc2_loss0.3.json`、`instance_soc2_loss0.6.json`、`instance_soc2_loss0.9.json`、`instance_soc2_loss0.99.json` | `--seeds 10 --arms local,aoi,ea_nb,ea_aoi --harvest-mode hetero --low-wh-per-hour 0 --capacity-wh 0.02 --dynamic-oracle --soc-bias X|--soc-loss-p L --tag soc2_*` | 10 | **被动反馈的有效信息**：乘性高估 3.0 倍 → 达标率 −3.9 点；报告丢失 99% → 只 −1.1 点。`aoi` 对两者完全免疫。机制：无读数时退回默认档（安全），而**偏置会让策略做错动作**，两者性质不同 |
| `instance_adm_slack005.json`、`instance_adm_bind008.json`、`instance_adm_bind004.json`、`instance_adm_irr005_s0.json`、`instance_adm_irr005_s2190.json`、`instance_adm_irr005_s4380.json`、`instance_adm_irr005_s6570.json` | `instance_run.py --seeds 20 --task-hours 12 --tail-hours 1 --arms local,aoi,dense600,ea_i600,ea_hyst2,ea_nb,ea_nb_hyst --dynamic-oracle` + 各条件的 `--harvest-mode hetero|irradiance --capacity-wh …`，`--tag adm_*` | 20 | **动作准入归类（逐命令）**：`改值 / 同值 / 未知状态` 三条互斥且穷尽。`ea_nb` 在**任何**条件下都不写同值、不做无证据下发；`ea_i600` 在绑定区**全部**控制流量都是值域空操作（改值 0，同值 26） |
| `instance_pair_winter.json`、`instance_pair_summer.json` | `--harvest-mode irradiance --irr-start-h 1095|5475 --irr-peak-wh-per-hour 0.02 --capacity-wh 0.006 --initial-soc 0.2 --charge-min-c off --dynamic-oracle --tag pair_winter|pair_summer` | 20 | **同 margin、不同 temporal shape 的成对反例**：两条轨迹 margin **都是 1.37**，而 `local` 达标率 **84.5% vs 12.5%**。机制：采能到达时刻 vs 初始电量支撑时长；并暴露 `autonomy_margin` 的代价模型**漏掉事件采样项**，在窗口含触发时系统性偏乐观 |
| `instance_irr_c0.004_s0.json`、`instance_irr_c0.004_s1095.json`、`instance_irr_c0.004_s2190.json`、`instance_irr_c0.004_s3285.json`、`instance_irr_c0.004_s4380.json`、`instance_irr_c0.004_s5475.json`、`instance_irr_c0.004_s6570.json`、`instance_irr_c0.004_s7665.json`、`instance_irr_c0.006_s0.json`、`instance_irr_c0.006_s1095.json`、`instance_irr_c0.006_s2190.json`、`instance_irr_c0.006_s3285.json`、`instance_irr_c0.006_s4380.json`、`instance_irr_c0.006_s5475.json`、`instance_irr_c0.006_s6570.json`、`instance_irr_c0.006_s7665.json` | `instance_run.py --seeds 10 --task-hours 12 --tail-hours 1 --arms local,dense600,dense1800,ea_i600,ea_nb --harvest-mode irradiance --irr-start-h S --irr-peak-wh-per-hour 0.02 --irr-no-source-temp --capacity-wh 0.004|0.006 --charge-min-c off --dynamic-oracle --tag irr_c<cap>_s<S>` | 10 | **真实辐照下的 calibration cliff**：cap 0.004 时 `dense600` 达标率 19.5%–91.1%，`local`/`ea_i600`/`ea_nb` 稳在 55–88%。窗口 1095/6570 的真上界本身掉到 140/112 |
| `instance_irrs_m0_o0.json`、`instance_irrs_m0_o6.json`、`instance_irrs_m0_o12.json`、`instance_irrs_m0_o18.json`、`instance_irrs_m1_o0.json`、`instance_irrs_m1_o6.json`、`instance_irrs_m1_o12.json`、`instance_irrs_m1_o18.json`、`instance_irrs_m2_o0.json`、`instance_irrs_m2_o6.json`、`instance_irrs_m2_o12.json`、`instance_irrs_m2_o18.json`、`instance_irrs_m3_o0.json`、`instance_irrs_m3_o6.json`、`instance_irrs_m3_o12.json`、`instance_irrs_m3_o18.json`、`instance_irrs_m4_o0.json`、`instance_irrs_m4_o6.json`、`instance_irrs_m4_o12.json`、`instance_irrs_m4_o18.json`、`instance_irrs_m5_o0.json`、`instance_irrs_m5_o6.json`、`instance_irrs_m5_o12.json`、`instance_irrs_m5_o18.json`、`instance_irrs_m6_o0.json`、`instance_irrs_m6_o6.json`、`instance_irrs_m6_o12.json`、`instance_irrs_m6_o18.json`、`instance_irrs_m7_o0.json`、`instance_irrs_m7_o6.json`、`instance_irrs_m7_o12.json`、`instance_irrs_m7_o18.json`、`instance_irrs_m8_o0.json`、`instance_irrs_m8_o6.json`、`instance_irrs_m8_o12.json`、`instance_irrs_m8_o18.json`、`instance_irrs_m9_o0.json`、`instance_irrs_m9_o6.json`、`instance_irrs_m9_o12.json`、`instance_irrs_m9_o18.json`、`instance_irrs_m10_o0.json`、`instance_irrs_m10_o6.json`、`instance_irrs_m10_o12.json`、`instance_irrs_m10_o18.json`、`instance_irrs_m11_o0.json`、`instance_irrs_m11_o6.json`、`instance_irrs_m11_o12.json`、`instance_irrs_m11_o18.json` | 同上但**相位分层**：`--irr-start-h $((月*730 + 相位))`，相位 ∈ {0,6,12,18}，12 月 × 4 相位 = 48 个窗口，`--tag irrs_m<月>_o<相位>` | 10 | **真实天气窗口的分布性结论**：`dense600` 达标率 中位 29.8%、**极差 71.5 点**；`local`/`ea_i600`/`ea_nb` 极差仅 33 点。**抽样必须相位分层**——每 24 h 取一个会与昼夜周期锁相，实测一个不可行窗口都抽不到（8760 个真实窗口里 2775 个不可行，占 31.7%） |
| `instance_initsoc_1.0.json`、`instance_initsoc_0.5.json`、`instance_initsoc_0.2.json`、`instance_initsoc_0.05.json` | `instance_run.py --seeds 20 --task-hours 12 --tail-hours 1 --arms local,dense600,dense1800,ea_i600,ea_nb --harvest-mode hetero --low-wh-per-hour 0 --capacity-wh 0.006 --initial-soc S --dynamic-oracle --tag initsoc_S` | 20 | **初始 SoC 轴（goal 一 点名的一维）**：真上界 162.6 / 129.8 / 113.5 / 102.6。固定 `dense600` 达标率 66.6% → 80.5% → 89.0% → **92.1%**，即 regret **33.4% → 19.5% → 11.0% → 7.9%**，在满格启动时最大、初始电量越低越小（0.05 时 `dense600` 反超 `local`）。与 ⑫ 的容量轴同形：**regret 的峰值出现在"上界还撑得住、而固定配置已经撑不住"的那一段** |
| `instance_solar_s12p1.json`、`instance_solar_s12p2.json`、`instance_solar_s12p4.json`、`instance_solar_s6p1.json`、`instance_solar_s6p2.json`、`instance_solar_s0p4.json` | `instance_run.py --seeds 20 --task-hours 12 --tail-hours 1 --arms local,dense600,dense1800,ea_i600,ea_nb --harvest-mode solar --solar-day-start-h S --solar-peak-wh-per-hour P --solar-cloud-p 0.35 --capacity-wh 0.010 --initial-soc 0.2 --dynamic-oracle --tag solar_sSP` | 20 | **真实采能时间过程 `H_i(t)` 与 autonomy margin（横轴不用绝对 Wh）**：`solar_harvest` 是**合成**曲线（A 层研究取值，非拟合值）。日照窗位置决定形状：12h 起点=先出电后转黑、6h 起点=整段白天、0h 起点=先黑 6 h。margin 0.72/1.44/2.88/1.44/2.87/0.00 对应上界 126/168/168/168/168/126。**`dense600` 达标率崩到 15–42%，而反馈臂恒在 82–88%** |
| `instance_pareto_nominal.json`、`instance_pareto_cap002.json`、`instance_pareto_blackout3.json` | `--seeds 20 --arms local,aoi,dense600,dense1800,ea_i600,ea_hyst1,ea_hyst2,ea_hyst3,ea_nb,ea_nb_hyst --capacity-wh 0.05\|0.02 [--blackout-start-h 4 --blackout-frac 0.3] --tag pareto_*` | 20 | **下行代价的 Pareto**：滞环/死区在名义条件下**逐位无效果**，在绑定条件下只把下行 85.9→74.6 而交付 150.8→148.2（沿前沿滑动、方向变差）。真正把下行 71.4→**37.5** 的是 `ea_nb`——省掉"未知状态时的保守配置"那一代，它同时消除策略**自己制造**的跨代混配（1422→**0** min） |
| `instance_oracle_headroom005.json`、`instance_oracle_headroom008.json`、`instance_oracle_headroom004.json` | `instance_run.py --seeds 20 --task-hours 12 --tail-hours 1 --arms local,dense300,…,dense1800,ea_i600 --harvest-mode hetero --low-wh-per-hour 0 --dynamic-oracle --capacity-wh 0.05\|0.008\|0.004 --tag oracle_headroom…` | 20 | **真上界与策略余地（关键）**：逐节点逐小时的离线 DP，读完整未来采能轨迹。旧上界 `dynamic_upper_bound` 松到 168/168 不带信息，本轮换成有区分力的真上界。周期达标率 91.9% / 87.6% / 87.0%，且缺口可精确拆解为 `缺采 + 缺送`（168 = 交付 + 缺采 + 缺送） |
| `instance_energy_sweep.json` | `instance_run.py --seeds 20 --task-hours 12 --tail-hours 1 --arms local,dense300,…,energy_aware --harvest-mode hetero --low-wh-per-hour 0 --tag energy_sweep` | 20 | **能量绑定的冲突条件**：固定采样间隔扫描 vs 能量感知策略 |
| `instance_ea_sweep.json` | `instance_run.py --seeds 20 --task-hours 12 --tail-hours 1 --arms dense600,energy_aware,ea_h5,ea_h15,ea_h25,ea_i600,ea_i600h5 --harvest-mode hetero --low-wh-per-hour 0 --tag ea_sweep` | 20 | 自适应阈值扫描（保证固定基线与自适应都被调过参数再比） |
| `instance_energy.json` | `--harvest-mode hetero --tag energy` | 10 | 异质采能的过渡读数（能量尚未 binding，见 04 解析 §四） |
| `instance_energy2.json` | `--arms local,dense300,energy_aware --harvest-mode hetero --low-wh-per-hour 0 --tag energy2` | 10 | 同上，接入采样间隔动作之后 |
| `instance_uncertain015.json` | `--arms local,dense600,dense900,dense1200,dense1800,ea_i600 --capacity-wh 0.015 --tag uncertain015` | 20 | **参数不确定性（关键）**：固定配置按名义容量选点、实际容量 0.015 Wh 时崩到 `local` 以下 |
| `instance_nominal050.json` | 同上，`--capacity-wh 0.05 --tag nominal050` | 20 | 名义容量下的对照 |
| `instance_cap0.004.json`、`instance_cap0.008.json`、`instance_cap0.015.json`、`instance_cap0.025.json`、`instance_cap0.05.json`、`instance_cap0.10.json` | `--capacity-wh C --tag capC` | 10 | 电池容量扫描（参数不确定性的核心轴） |
| `instance_soc_age14400.json`、`instance_soc_age28800.json`、`instance_soc_age3600.json`、`instance_soc_age7200.json`、`instance_soc_bias0.7.json`、`instance_soc_bias1.4.json`、`instance_soc_bias2.0.json`、`instance_soc_loss0.3.json`、`instance_soc_loss0.6.json`、`instance_soc_loss0.9.json`、`instance_soc_noise0.002.json`、`instance_soc_noise0.005.json`、`instance_soc_noise0.010.json`、`instance_soc_perfect.json` | `instance_run.py --seeds 10 --arms local,dense600,ea_i600 --harvest-mode hetero --low-wh-per-hour 0 --capacity-wh 0.02 --blackout-start-h 4 --blackout-frac 0.3 --soc-{max-age-s,s-noise-wh,bias,loss-p} X --tag soc_*` | 10 | **反证测试**：攻击 `soc_wh`。观测年龄/加性噪声不敏感，乘性高估与报告丢失有害 |
| `instance_ood_C1.json`、`instance_ood_C2.json`、`instance_ood_C3.json`、`instance_ood_C4.json`、`instance_ood_C5.json`、`instance_ood_C6.json`、`instance_ood_C7.json`、`instance_ood_ref.json` | `instance_run.py --seeds 10 --arms local,dense300,…,dense1800,ea_i600 --harvest-mode hetero --low-wh-per-hour 0 --capacity-wh C [--blackout-start-h 4 --blackout-frac F] [--low-frac G] --tag ood_Cn` | 10 | **OOD 稳健性主表**：`dense600` 与 `ea_i600` 只在名义条件定一次后冻结，7 个测试条件；另跑 6 条固定间隔取事后最优作为 regret 分母。C1 名义 / C2–C4 容量 / C5–C6 失电 / C7 遮蔽 |
| `instance_oracle_bo0.0.json`、`instance_oracle_bo0.3.json`、`instance_oracle_bo0.6.json` | `--arms local,dense600,ea_i600,oracle_deploy --harvest-mode hetero --low-wh-per-hour 0 --capacity-wh 0.02 --blackout-start-h 4 --blackout-frac F --tag oracle_boF` | 20 | **决定性对照**：反馈策略 vs 全知上界（`oracle_deploy` 读环境真值并逐节点模拟能量可行性，不是可实现策略）。失电 0/30/60% |
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
