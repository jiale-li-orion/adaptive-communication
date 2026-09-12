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

## 位置数据

`data/` 下的内容全部保留：`dem/hgt` 是 SRTM 高程，`downloads/chirpbox.csv`、`lora_on_ice`、
`lora_sar`、`inetintel`、`ioda_*.json` 是源数据集。它们是输入不是结果，删掉就无法重跑。

## 物理层保留

`coverage_*`、`itm_constant_check.txt`、`los_vs_itm.json`、`loss_model.*`、
`outage_distribution.*`、`energy_model_*`、`heating_sweep.txt`、`mountain_lora_result.txt`、
`terrain_*`、`relay_siting_summary.txt`、`relay_availability_sweep.txt`、`sweeps.log`
不受上述任何缺陷影响，全部保留。
