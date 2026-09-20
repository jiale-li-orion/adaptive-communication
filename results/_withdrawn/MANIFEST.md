# 已撤销的结果文件

这些文件的读数建立在已修好的实现缺陷之上，继续留在 `results/` 里会被当成可用证据。
删除它们的依据是 README §7.18–§7.23 记录的修复；每条都注明了它为什么失效。

> **本地材料说明。** 本文件引用的 `docs/…` 路径属于作者本地的过程文档与逐轮审计记录，不随本仓库发布；远端仓库只包含 `paper/`、`code/`、`results/` 与根 README。

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
| `monitoring_trajectories_ablate20.json` | `monitoring_trajectories_ablate20v3.json` | 由旧代码产出：同一臂同一轨迹同一批 20 种子，`ours` 记 63.00 / 下行 682.5，当时代码给 89.07 / 604.8。**两列都不一致，此前被误当成"评分口径不同"**。§7.35 |
| `monitoring_trajectories_restart20v4.json` | `monitoring_trajectories_fairrestart3.json` | §7.33：重启对照不公平——本文臂的状态留在活着的对象里，基线被清空。据此得出的"跨重启领先 14.1 个点"作废 |
| `monitoring_trajectories_fairrestart2.json` | `monitoring_trajectories_fairrestart4.json` | §7.34 的下发顺序修正之前产出；`ours` 记 89.07 / 604.8，修正后 94.53 / 628.9 |
| `monitoring_trajectories_fairrestart3.json` | `monitoring_trajectories_fairrestart4.json` | 臂集合漏了 `vtc_style_durable`，而正文引用了该行的读数（D29 违规：引用无落盘产物的读数） |
| `monitoring_trajectories_ablate20v2.json` | `monitoring_trajectories_ablate20v3.json` | 同上（§7.34 之前） |
| `monitoring_trajectories_business2.json` | `monitoring_trajectories_business3.json` | 同上（§7.34 之前）。四条未受影响的臂（`local_rules` / `versioned_config` / `vtc_style` / `oracle`）读数不变 |
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

## 实例层：`arm-removed_2026-09-13/`

| 文件 | 失效原因 |
|---|---|
| `instance_oracle_bo0.0.json`、`instance_oracle_bo0.3.json`、`instance_oracle_bo0.6.json` | 这三份用的臂是 `oracle_deploy`，**该臂已从 `center.ARMS` 中移除**（被 `clairvoyant_static` 取代）。2026-09-13 的全量重跑里它们是唯一三份**连命令都跑不起来**的文件（`unknown arm 'oracle_deploy'`），既不能重算也不能核对，因此移出可引用集 |

## 实例层：`aoi_defect_2026-09-13/`（备份，不是撤销）

这个子目录放的是 **237 个实例结果文件在 AoI 修复前的原样副本**，外加：

| 文件 | 说明 |
|---|---|
| `regeneration_report.json` | 逐文件记录重跑后的差异：`only_aoi`＝只有 AoI/无观测这一列变（66 个）；`moved`＝**别的列也变了**（171 个），并列出变化的字段名 |

**为什么这不是"撤销"。** `scoring._routine_block` 的 AoI 实现有两个缺陷（按采集时刻而非接收时刻推进；
`newest` 可倒退），修好之后**每一个实例结果文件的 AoI 列都作废**。处理办法不是把这些文件撤出引用，
而是**用文件自己记录的 `config` 重建命令、逐文件重跑**（`code/analysis/rerun_from_config.py`），
并把重跑前后的差异逐路径核对出来。旧副本留在这里，是为了让"重跑之后到底变了什么"可被审计，
**其读数本身不得引用**。

**重跑同时暴露的第二件事**：171 个文件在现行代码下**除 AoI 之外也有列变化**
（典型字段 `consumed_wh` / `airtime_uplink_h` / `commands_refused` / `dead_nodes_end`）——
也就是说，**它们登记时的代码与现在不同**。这不是本次修复造成的，是它们早已如此，
只是此前没有任何检查会发现这一点。逐文件结论见 `regeneration_report.json`。

## 实例层：`prune-unit_2026-09-13/`

| 文件 | 失效原因 |
|---|---|
| `instance_contcfg_b{1.0,3.0}_{noout,out0,out3}.json` | 这一批产出时 `ControlPlane.prune` 的**时间单位不一致**（参数按小时、`expires_at` 按秒）⇒ 过期永不触发、`downlink_expired` 恒为 0；且过期只在投递路径里被检查 ⇒ 接入中断期间 `in_flight` 永久为真。两个缺陷都已在 2026-09-13 修好并**重跑同一批**。**业务列变化很小**（缺采在 24 个格子里逐位不变），但 `expired` 一列作废。依据见 `docs/s7-method/instance-v1/17-gate-0-1h-mechanism-closure-2026-09-13.md` §一 |

## 实例层：`fixed-horizon_2026-09-13/`

| 文件 | 失效原因 |
|---|---|
| `instance_adm_{noout,out0,out3}.json` | 这一批产出时 `ResourceGate` 用的是**固定保护时域**（构造时传入、每次 `check` 从 `t=0` 跑满 `task_hours*3600`），而不是规格要求的**剩余时域** `end_s − t`。后果是后期仍在问"你还能再撑 13 h 吗"，把"剩余时域变短 ⇒ 加密变可行"的中间态整个压掉，**伪造出 `accept = 0` 与"候选逐位等于 `local`"**。已修为剩余时域并重跑同一批（`results/instance_adm_*.json`）。依据见 `docs/s7-method/instance-v1/20-remaining-horizon-rerun-2026-09-13.md` |

## 实例层：`pre-prune-refresh_2026-09-13/`

| 文件 | 失效原因 |
|---|---|
| **全部 287 个** `instance_*.json` 的副本 | 这一批产出时 `ControlPlane.prune` 的时间单位不一致、且过期只在投递路径里被检查（两个缺陷见 `docs/s7-method/instance-v1/17-gate-0-1h-mechanism-closure-2026-09-13.md` §一）。它们的 **`expired` / `queued_left` 两列是错的**（`expired` 恒为 0），业务列也有小幅位移——**逐文件实测最大位移为 `accout40_fifo` 的 `aoi` 交付 142.75 → 141.35（−1.40 条 / −0.83 点）**，1573 条 (文件, 臂, 列) 条目上有差异，其余绝大多数 ≤0.1 条。已用现行代码**整批重跑**，本目录只作差异审计用，**读数不得引用** |

## 论文主张：C5 配置租约（2026-09-20）

[主张快照](2026-09-20-c5-lease-claims.md) 保存固定 TTL 跨相位不可行、在线界已实现等被取代的解释。r46/r47/r48 的原始结果与冻结参考数字均保留；当前状态只由 `results/CLAIMS.md` 管理。

## 记录到期的同拍边界（2026-09-20）

`Node.batch` 在当拍上传/转发**之前**执行到期清理，原用 `expires_at <= t_s`；而评分接受
`received_at <= deadline`。因此期限恰为当拍的记录被删而非发出，丢掉的正是该拍唯一还能得分的
机会。修正为 `<`（保留截止当拍），`generic_expiry` 与 `deadline_purge` 两处同步改。

依据：`results/retention_deadline_audit.json`（相位 A、peak .012、十种子：普通 expiry 只改边界即
+1.47 点，10/10 为正，其中 1674/1792 条被救样本的听到时刻恰等于真业务期限）。验收测试
`code/experiments/test_instance.py` 的 [35] 组钉住"当拍仍进批次"与"过期即释放"两侧。

影响面：`cache_service="fifo"` 与 `latest_only` 从不按期限删除，**读数逐字节不变**（`r30c_walls.json`
的 3025 与 `latest_only` 的 4250 均未变）；只有会删除的臂受影响。

| 文件 | 失效原因 |
|---|---|
| `2026-09-20-r41_expiry_equiv_prefix.json` | 修正前语义。两条会删除的臂在种子 0 上 434 → 修正后 420，`late` 0 → 14；**逐位等价结论不变**（两条臂同改，仍逐字节相同） |
| `2026-09-20-r37e_full_seeds_prefix.json` | 修正前语义。十种子：purge 中断按期 4265 → 4145、过期 1 → 120、配对 +4.214 → +4.038 点（CI [3.477, 4.599]，10/10 仍为正）；fifo 与 latest_only 不变 |

引用这些读数时必须说明是修正前语义；当前可引用的数值在 `results/` 同名活文件与
`results/reference/` 冻结快照里。
