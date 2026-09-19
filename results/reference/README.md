# 冻结参考结果

本目录存放论文主张的**判定基准**：`results/` 下同名结果文件在冻结时刻的快照。`artifact/reproduce_all.sh` 重新跑出结果文件后与本目录逐项比较，比较通过才给出 PASS。

冻结的意义在于让"复现成功"有确定的比较对象。缺了它，"复现"退化为"又产出了一个数字"，而本次运行与论文所引数值之间的漂移不可见。

| 文件 | 对应主张 | 来源 |
|---|---|---|
| `r30c_walls.json` | C1 | `code/v3joint/r30c_walls.py` |
| `r41_expiry_equiv.json` | C2 | `code/v3joint/r41_expiry_equiv.py` |
| `r37e_full_seeds.json` | C3 | `code/v3joint/r37e_full_seeds.py` |
| `r44_fullhorizon_attribution.json` | C4 | `code/v3joint/r44_fullhorizon_attribution.py` |
| `r46_lease_sweep.json`、`r47_lease_energy.json`、`r48_ttl_vs_lease.json` | C5 | 同名脚本 |
| `r39_table.json` | C6 | `code/v3joint/r39_envelope.py` 经 `merge_r39.py` 汇总 |
| `r40_local_attribution.json` | C7 | `code/v3joint/r40_local_attribution.py` |
| `r38_three_arm_summary.json`、`r42_claim_relabel.json`、`r43_cert_v5_replay.json` | C8 | 保存的 agent 轨迹与其离线重放 |

更新规则：结果文件变动必须在**同一次提交**里更新本目录的对应快照，并说明变动原因。冻结值不与 `results/` 下的活文件自动同步，两者出现差异是**信号**，不是噪声：它说明某处改动了实验或其口径。
