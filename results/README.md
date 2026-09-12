# 结果文件的数据来源

本目录的每个文件都由仓库内的脚本产生，不手工编辑。每条给出：产出脚本、可复现的命令、
配置（种子、时长、臂或轨迹）、以及它可以被引用来说明什么。

**引用规则。** 一个读数要进正文，必须能回答"哪个脚本、哪个命令、哪些种子"。命令里没有
`--seeds` 的结果不得当作主结果；`scripted` 后端产生的任何数字不得当作模型结果。
种子取自**开发区间**（0–999）；测试区间（seed ≥ 10000）除一致性审计外未被触碰。

## 一、机制层：`code/experiments/method_comparison.py`

固定决策轨迹下比较执行运行时，含协议消融。写入、验证读、调和读、回复全部走同一条链路并
计入空口。

```bash
export PYTHONPATH="$PWD/libs/pylibs"
python3 code/experiments/method_comparison.py --days 30 --seeds 5 \
  --arms one_shot,verified_tool_calls,ours,exact_version_cas --workload operation
```

| 文件 | 配置 | 说明什么 |
|---|---|---|
| `method_comparison.json` | 30 天 / 5 种子 / 4 条臂 / `operation` 负载；`reach=12 blocked=4`，`retry_budget=3`，`read_cost_ratio=1.0`，能量模型开 | 公平化之后的精确版本 CAS 与本文打平而归一代价低 29%（README §7.23 第三节）。**只有 5 个种子，尚未按 20 种子的口径重跑。** |

每条臂的 `per_seed` 保存逐种子值，因此配对差值与逐种子的零值检查可以直接做：

```bash
python3 code/analysis/paired_ci.py results/method_comparison.json \
  --arm-a ours --arm-b exact_version_cas --workload operation --zero-check
```

其余机制层批次（等预算对照、加热扫描、读写成本敏感性、中继 2×2、P2 消融、重启实验）已随
产生它们的实现一并撤销，清单与逐条原因在 `_withdrawn/MANIFEST.md`。

## 二、业务层：`code/experiments/monitoring_trajectories.py`

七条轨迹（无故障加契约 §5 的六类）× 若干臂 × 若干种子。每条臂看同一部署、同一外生需求、
同一注入、同一网关与回传、同一机会预算。

```bash
# 业务臂
python3 code/experiments/monitoring_trajectories.py --days 3 --seeds 20 \
  --arms local_rules,versioned_config,vtc_style,ours,oracle --tag business

# planner x runtime 2x2
python3 code/experiments/monitoring_trajectories.py --days 3 --seeds 20 \
  --arms rule__naive,rule__contract,llm__naive,llm__contract --tag 2x2
```

| 文件 | 配置 | 说明什么 |
|---|---|---|
| `monitoring_trajectories_business.json` | 3 天 / 20 种子 / 5 条业务臂 / 七条轨迹 | 业务臂在七条轨迹上的覆盖、关键观测空窗、误报成功、知晓时延、机会账目与远端契约计数 |
| `monitoring_trajectories_2x2.json` | 3 天 / 20 种子 / 2×2 四格 / 七条轨迹 | planner 因子与 runtime 因子的分解（README §7.23 第四节） |
| `monitoring_trajectories_paths.json` | 3 天 / 2 种子 / `rule__contract` / 无故障；`--paths backhaul:0.62,backup:0.55 --runtime-paths 0,1` | 独立管理路径对照组：runtime 会发现并使用备用回传（README §7.24） |
| `monitoring_trajectories_paths_primary_only.json` | 同上，但 `--runtime-paths 0` | 同一部署下只用主路径的对照 |

结果文件的 `per_seed` 保存逐种子值，`workload` 字段即轨迹名，因此可按轨迹分组做配对比较与
零值检查：

```bash
python3 code/analysis/paired_ci.py results/monitoring_trajectories_2x2.json \
  --arm-a rule__contract --arm-b rule__naive --workload stale_command --zero-check
```

**口径提醒。** 这两个文件的 `--days 3` 是 72 小时，与契约 §10 P1 的参考负载一致。`llm__*`
两格用的是 `scripted` 后端（`compose.ScriptedWorldBackend`），它是管道证据，不是模型证据。
真实端点当前返回 401、缺 `OPENAI_API_KEY`，接上之后这两格才能改名为模型结果。

## 三、物理层：地形、传播、信道与能量

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
| `heating_sweep.txt` | `code/physics/energy.py` 驱动的扫描 | 见 `code/README.md` | 加热比例 0/0.25/0.5/0.75/1.0 下的停电率。`heated_fraction=0.5` 是 A 层取值 |
| `energy_model_result.txt`、`energy_model_after_fix.txt` | `code/physics/energy_model.py` | `python3 code/physics/energy_model.py` | 太阳能加储能的年扫描，比较电池化学与面板尺寸对年停电天数的影响。两个文件是发电量规则修正前后的对照 |
| `terrain_mesh.obj`、`terrain_scene.xml`、`terrain_render.png`、`terrain_mesh.json` | `code/physics/dem_to_mitsuba.py` | `python3 code/physics/dem_to_mitsuba.py` | SRTM 瓦片转三角网格与 Mitsuba 场景，格点与 `coverage_grid.csv` 对齐以便逐点比较。依赖 `data/dem/hgt` |
| `relay_siting_summary.txt`、`relay_availability_sweep.txt`、`relay_run.log`、`sweeps.log` | `code/physics/relay_siting.py`、`code/physics/coverage_map.py` | 见 `code/README.md` | 带高程与坡度约束的中继选址，与无约束版本互为对照 |

## 四、系统策略案例研究：`code/experiments/mission_sim.py`

```bash
python3 code/experiments/mission_sim.py --days 365 --seeds 5 --tag year
```

| 文件 | 配置 | 说明什么 |
|---|---|---|
| `mission_sim.json`、`mission_sim.txt` | 30 天 / 1 种子 | 早期单种子读数，保留作对照 |
| `mission_sim_year.json` | 365 天 / 5 种子 | 系统策略的年度案例研究：盲发 26.4%、存储转发 41.3%、急切中继 47.8%、churn 感知 47.7% |
| `mission_sim_relay.json` | 365 天 / 3 种子 / `--tag relay` | 中继组的同一研究 |

**定位。** 这是**系统策略案例研究**，不是 agent 基线：它的策略不含执行层的身份、回执与
调和，因此不能拿来回答"runtime 有什么用"。`mission_sim*` 的 `per_seed` 为空，做配对比较
需要先补逐种子记录。

## 五、已撤销

`_withdrawn/MANIFEST.md` 逐条列出被删除的结果文件及其失效原因。被删的文件在 git 历史里
仍可找回，但**不得**再用作证据。三条撤销主线：

1. `verified_tool_calls` 的保真度缺陷（`want` 被覆盖使 Unknown 从不等待、verify/reconcile
   绕过链路、日清理用固定预算），使"Verified 有天花板"与"预算 20 下追平"两条结论作废。
2. 业务层把网关与中心合并、四接口只通一个、四条臂里没有本文 runtime。
3. 精确版本 CAS 被做成每次写前必读，违反契约 §7 的公平性要求，据此得出的"更严契约净亏"
   作废。

## 六、未纳入本目录的中间产物

`data/` 是**输入**不是结果。它的来源见 `data/README.md`，逐条复现命令与"跑对了的标志"
见 `data/REPRODUCE.md`。`libs/` 是第三方依赖。
`results/` 下不再保留构建缓存（原 `.drjit-cache/` 已删除，可重新生成）。
