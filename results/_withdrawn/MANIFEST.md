# 已撤销的结果文件

这些文件的读数建立在已修好的实现缺陷之上，继续留在 `results/` 里会被当成可用证据。
删除它们的依据是 README §7.18–§7.23 记录的修复；每条都注明了它为什么失效。

## 机制层：`verified_tool_calls` 保真度与 CAS 公平性

| 文件 | 失效原因 |
|---|---|
| `method_comparison_main.json` | 主表。四条臂里没有本文 runtime；`verified_tool_calls` 的 `want` 被覆盖使 Unknown 从不等待、verify/reconcile 绕过链路、日清理用固定预算，"Verified 有天花板"的结论已作废 |
| `method_comparison_p2.json` | P2 消融，同一批代码 |
| `method_comparison_budget1/3/8/20.json`、`_b3/_b8/_b20.json` | 等预算对照因固定 `RETRY_BUDGET` 与 `arm != "ours"` 而失效 |
| `method_comparison_heat*.json`、`_h00/_h025/_h05/_h075/_h10.json` | 加热扫描，同一批代码 |
| `method_comparison_msr*.json` | 读写成本敏感性，同一批代码，且当时 CAS 仍是每次写前必读 |
| `method_comparison_relay*.json`、`_relayav*.json`、`_ra025/_ra05/_ra10.json` | 中继 2×2 与可用性扫描，同一批代码 |
| `method_comparison_sm.json`、`_fid.json` | 同一批代码 |
| `method_comparison.txt`、`method_comparison_relay.txt` | 上述批次的终端转储 |

**`method_comparison.json` 保留**：它是当前代码、公平 CAS 下的 5 种子读数。

## 业务层：网关与中心合并、四接口只通一个

| 文件 | 失效原因 |
|---|---|
| `monitoring_trajectories.json`、`_ablate.json` | 3 种子；产生于四接口与三个闭环接通之前，W2 当时完全未实现，且只有本文臂会用 W1/W2 |
| `restart_experiment.json`、`_main.json`、`_smoke.json`、`.txt` | 产生于按动作武装故障与时钟派生 epoch 修复之前 |
| `baseline_experiment.txt` | 执行层故障复现，属同一批机制层代码 |
| `wirelessops_execution_*.txt` | 来自已移出仓库的适配器 |

## 业务与机制层：本轮修复过程中被取代的文件

这些文件在产出时是有效的，之后被同一个实验在修完缺陷后的重跑取代。保留它们是为了让
"某个读数曾经是多少、后来为什么变了"可被追溯。

| 文件 | 被谁取代 | 取代原因 |
|---|---|---|
| `monitoring_trajectories_business.json` | `business2` | §7.32：评分器的到达索引取最后一次而非第一次，压低全部覆盖读数 |
| `monitoring_trajectories_2x2.json` | `2x2v3` | §7.29 的逻辑身份缺陷 + §7.32 的评分缺陷 |
| `monitoring_trajectories_restart20.json` | `restart20v4` | 同上 |
| `monitoring_trajectories_restart20v2.json` | `restart20v4` | 同上（v2 只修了 rule planner，`llm__*` 两格仍带缺陷） |
| `monitoring_trajectories_restart20v3.json` | `restart20v4` | 同上（v3 仍未用定稿评分器） |
| `monitoring_trajectories_ablate20.json` | `monitoring_trajectories_ablate20v2.json` | 由旧代码产出：同一臂同一轨迹同一批 20 种子，`ours` 记 63.00 / 下行 682.5，当前代码给 89.07 / 604.8。**两列都不一致，此前被误当成"评分口径不同"**——下行次数同样不同，说明是运行不同而非评分不同。§7.35 |
| `monitoring_trajectories_restart20v4.json`（仍在 `results/`，但已失效） | `monitoring_trajectories_fairrestart2.json` | §7.33：重启对照不公平——本文臂的状态留在活着的对象里，基线被清空。该文件保留在 `results/` 只为可追溯，**读数不得引用** |
| `method_comparison.json` | `method_comparison_main20.json` | 只有 5 个种子、4 条臂；主表用 20 种子、11 条臂 |

## 机制层的加热与中继扫描：产出代码已被取代

`heating_sweep.txt`、`relay_availability_sweep.txt`、`sweeps.log` 由 `method_comparison.py`
的 `--heated` 与 `--relay` 扫描产生，而那一版脚本带有 `verified_tool_calls` 的保真度缺陷
（§7.18）与不公平的精确版本 CAS（§7.23）。**它们既未被重跑，也不得引用**；重跑命令见
`results/README.md`。

## 位置数据

`data/` 下的内容全部保留：`dem/hgt` 是 SRTM 高程，`downloads/chirpbox.csv`、`lora_on_ice`、
`lora_sar`、`inetintel`、`ioda_*.json` 是源数据集。它们是输入不是结果，删掉就无法重跑。

## 物理层保留

`coverage_*`、`itm_constant_check.txt`、`los_vs_itm.json`、`loss_model.*`、
`outage_distribution.*`、`energy_model_*`、`heating_sweep.txt`、`mountain_lora_result.txt`、
`terrain_*`、`relay_siting_summary.txt`、`relay_availability_sweep.txt`、`sweeps.log`
不受上述任何缺陷影响，全部保留。
