# 主张表

**每条主张只有一个当前状态。** 本表是论文主张的当前真值来源；叙事文档（含 README）不承担研究历史。被撤回的主张移入本文件末尾的撤回表并留下 `superseded_by` 指针，其详细过程保留在作者本地的 `docs/` 归档内。

状态取自六个值，含义固定：

| 状态 | 含义 |
|---|---|
| `supported` | 有确定性、仓库可复现的证据支持，且已相对普通对照核实 |
| `scoped-negative` | 负结果，适用范围限定在所测策略族与工作点，不构成最优性定理 |
| `formative` | 形成性证据，用于定位接口问题，不用于确立机制 |
| `open` | 尚未判定 |
| `reproduced-externally` | 由本仓库之外的独立复现支持 |
| `retracted` | 已撤回，见撤回表 |

「冻结提交」不写在本表里。每个参考结果文件的最后一次修改提交由 `code/experiments/audit_claims.py` 在运行时用 `git log` 计算并打印，避免手填的提交号与 git 历史脱节。

## 当前主张

| Claim | 论文位置 | 证据 | 脚本 | 参考结果 | 状态 |
|---|---|---|---|---|---|
| C1 | §7.1 表 1 | 固定资源下各项物理资源单独放宽与同时放宽的反事实干预；集合分解显示仅回传容量阻塞 1715 条、仅电池阻塞 1128 条、两者耦合 155 条（2.0%） | `code/v3joint/r30c_walls.py` | `results/r30c_walls.json` | scoped-negative |
| C2 | §5.1、§7.2 表 2 | `deadline-purge` 与 `generic-expiry` 在十个种子上逐位相同（服务、中断计数、死亡、交付集合） | `code/v3joint/r41_expiry_equiv.py` | `results/r41_expiry_equiv.json` | supported |
| C3 | §7.2 | 源端按期限到期相对 FIFO 的十种子配对增益，以及仅在网关抑制造成的反压 | `code/v3joint/r37e_full_seeds.py` | `results/r37e_full_seeds.json` | supported |
| C4 | §7.1 | 全时域时间感知归因：4535 条失约中 830 条由回传容量改记为接入迟到 | `code/v3joint/r44_fullhorizon_attribution.py` | `results/r44_fullhorizon_attribution.json` | supported |
| C5 | §7.3 表 3 | 预置回退界相对日落回退的效果可复现；8 h TTL 在两相位也为零死亡且黄级交付总数不减。在线交付界推导、随命令安装及相对同信息普通租约的增量待验证 | `code/v3joint/r46_lease_sweep.py`、`code/v3joint/r47_lease_energy.py`、`code/v3joint/r48_ttl_vs_lease.py` | `results/r46_lease_sweep.json`、`results/r47_lease_energy.json`、`results/r48_ttl_vs_lease.json` | open |
| C6 | §7.5 表 5 | 同一规则在中心与节点的执行位置对照；节点本地门消除所测种子死亡并压低被拒准入 | `code/v3joint/r39_envelope.py` | `results/agent_traces/r39_table.json` | supported |
| C7 | §7.4 表 4 | 任务表到达时仅凭网关本地证据的可判定覆盖与已判定精度 | `code/v3joint/r40_local_attribution.py` | `results/r40_local_attribution.json` | supported |
| C8 | §7.6 | 真实 agent 十一轨迹、1089 次决策的对称计量；接口故障与解析失败账目 | `code/v3joint/r38_agent_three_arm.py`、`code/v3joint/r42_claim_relabel.py`、`code/v3joint/r43_cert_v5_replay.py` | `results/agent_traces/r38_three_arm_summary.json`、`results/r42_claim_relabel.json`、`results/r43_cert_v5_replay.json` | formative |

## 撤回表

| 原主张 | superseded_by | 理由 | 来源提交 |
|---|---|---|---|
| `deadline-purge` 承载相对同期限普通 expiry 的算法新颖性 | C2 | 两者逐位等价，机制即标准逐记录到期；增益改由跨段安置位置承载 | `e8ff1c4` |
| 固定资源下任何中心控制器都无空间（全局调度上界、零残差） | C1 | 干预与贪心装包不构成全体合法策略的上界；收窄为所测策略族上的限定负结果 | `e8ff1c4` |
| 本地夜间规则构成普遍安全保证 | C6 | 规则仅依据时钟，未证明任意采能与初始电量下的存活不变量；收窄为所测种子的经验结果 | `e8ff1c4` |
| 强制中断窗的 24/19 次「配置生效谎报」与 r38 零解析回退 | C8 | 原评分只在命令密集的决策上运行、在对照组从不运行、并统计提示词自身教会的词；决策数不等于成功请求数 | `e8ff1c4` |
| 固定 TTL 在两个相位都无法满足存活与无黄级交付总数损失；当前结果证明合法在线交付界租约的独立增量 | C5 | 8 h TTL 在两相位满足上述计数判据；候选界读取未来降级时间并预置，未通过命令安装；详见 [不可变归档](_withdrawn/2026-09-20-c5-lease-claims.md) | `59e5ef1` |

## 维护规则

新增主张时同时给出脚本与参考结果，两者缺一不可。参考结果缺失时对应的实验脚本要先补机器可读输出；靠 `print` 输出的读数不得进入本表，因为它无法被机器核对。状态变化与章节编号变化在**同一次提交**里更新本表与 `results/README.md` 的登记条目。
