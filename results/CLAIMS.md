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
| C1 | §7.1 表 1 | 固定资源下各项物理资源单独/同时放宽的反事实干预：base 3065/7560（0.4054），仅放宽回传 4740（0.6270），仅放宽能量 4128（0.5460），双放宽 6023（0.7967）；4495 条失约分解为仅回传 1675（37.3%）、仅能量 1065（23.7%）、耦合 218（4.8%）、剩余结构项 1537（34.2%）。这是已实现策略上的干预分解，不是全局上界 | `code/v3joint/r30c_walls.py` | `results/r30c_walls.json` | scoped-negative |
| C2 | §5.1、§7.2 表 2 | `deadline-purge` 与标准 `generic-expiry` 在十个种子上逐位相同（服务、中断按期、死亡、备份 on/late、交付集合），修正 gateway deadline 边界后仍 10/10 全同；当前两臂均为 svc 0.416257、中断按期 4227、备份 on 4800、过期 0、死亡 0。原“仅网关抑制会造成跨段回压（202→194）”见证在修正后翻号为 226→248，已撤回，不再支撑本 claim | `code/v3joint/r41_expiry_equiv.py` | `results/r41_expiry_equiv.json` | supported |
| C3 | §7.2 | 源端标准逐记录到期相对 FIFO 的十种子配对增益：平均服务 0.380→0.416，配对 **+3.593 点**（95%CI [+2.996,+4.189]，10/10 为正）；中断按期交付 2009→4227（2.10×），过期备份 2100→0，死亡 12→0；相对 AoI `latest-only` **+5.708 点**（95%CI [+5.037,+6.378]，10/10 为正）。不再引用已翻号的 gateway-only suppression 见证 | `code/v3joint/r37e_full_seeds.py` | `results/r37e_full_seeds.json` | supported |
| C4 | §7.1 | 全时域时间感知归因：4495 条失约中，S_energy=2002（44.5%）、S_cap=1091（24.3%）、S_access=814（18.1%）、S_time=588（13.1%）；旧 heard-ever 口径的 S_cap=1905/S_access=0 中有 814 条应移到接入迟到 | `code/v3joint/r44_fullhorizon_attribution.py` | `results/r44_fullhorizon_attribution.json` | supported |
| C5 | §7.3 表 3 | 普通配置终止机制覆盖受检候选族。η=.012：A 相位 `valid_until/ttl8` 均 0 死亡、黄级 854/2016，候选能量族 0 死亡但仅 580/2016；B 相位 `valid_until/ttl8` 均 0 死亡、2020/3528，而候选族为 **1 死亡、1221/3528**。四条候选 `soc_mpc/soc_mpc_cons/energy_lease/lease_safety` 在受检格聚合结果逐格相同；结论只覆盖当前 phase/peak/信息条件，不否定所有在线 lease | `code/v3joint/c5_matrix.py` | `results/c5_matrix.json` | scoped-negative |
| C6 | §7.5 表 5 | 历史 r39 时钟 envelope 的执行位置对照：朴素中心合规 svc 0.168 / 死亡 39；历史中心 envelope 0.366 / 死亡 12；匹配的“历史 envelope + 节点本地门”保持 0.366 且死亡 0、拒绝 222；pure-local 0.362 / 死亡 0 / 0 命令。该表保留 legacy clock 语义，只作 placement 证据，不代表当前 evidence envelope | `code/v3joint/r39_envelope.py` | `results/agent_traces/r39_table.json` | supported |
| C7 | §7.4 表 4 | 任务表到达时 2112 条已失约升级义务中，仅凭网关当时合法证据可判 1114（52.7%），已判定子集 100% 正确：S_time=588、S_cap=321、可证 S_access=205；998 保持 unknown，其离线真值为 S_energy=571 与尚未听到的 S_access=427。离线全量真值为 S_time/S_cap/S_access/S_energy = 588/321/632/571 | `code/v3joint/r40_local_attribution.py` | `results/r40_local_attribution.json` | supported |
| C8 | §7.6 | 真实 agent 十一轨迹、1089 次决策的对称计量；接口故障与解析失败账目 | `code/v3joint/r38_agent_three_arm.py`、`code/v3joint/r42_claim_relabel.py`、`code/v3joint/r43_cert_v5_replay.py` | `results/agent_traces/r38_three_arm_summary.json`、`results/r42_claim_relabel.json`、`results/r43_cert_v5_replay.json` | formative |
| C9 | §7.3 | 预注册 v3 单节点同信息停止族的 scoped-negative：40 个 (phase, peak, σ) 格 × 5 个 λ = 200 个计价格上，最强普通组合与精确非预知参照的服务差 200/200 为 0，目标差最大绝对值约 2.27e-13。C5 紧能量格 peak=.012、σ=.047 的 strict 端点仍不可行（all-sparse 低分支最低 −0.284 mWh，临界 σ*=.040617<.047）；λ=48 时 p_death≈1.682e-4，普通 TTL/阈值组合追平同信息最优。只关闭当前声明模型，不外推网络调度或未知任务表 | `code/v3joint/c5_seqref.py`、`code/experiments/measure_seqref_calibration.py`、`code/experiments/audit_seqref.py` | `results/c5_seqref.json`、`results/c5_seqref_calibration.json` | scoped-negative |
| C10 | §5.1、§7.2 | **共享 deadline equality 缺陷及修正**：修正前 `prefix` 服务 61.3530%、交付 26799/43680、到期当拍删除 21488；普通 corrected boundary/current 为 62.8571%、27456/43680，+1.5041 点（95%CI [+1.3177,+1.6906]，10/10 为正），其中到期当拍听到 1792、1674 恰等于真业务期限。该 equality 同时影响源端 expiry 与 gateway maxcov/salvage，旧“网关侧不受影响”已撤回。`fixed2` 与 corrected boundary 服务逐位相同；`adaptive` 为 −0.0023 点（CI [−0.0068,+0.0022]，0/10 为正），因此旧视界增益没有独立残差 | `code/analysis/retention_deadline_audit.py` | `results/retention_deadline_audit.json` | supported |
| C11 | §4（记录状态）、§7.2 | 反向确认延迟的条件性敏感界：种子 100--104 上 `ack1` 与 `ack0` 逐 seed 完全相同（13860/21840，服务 63.4615%，上行均值 1012.1 s）；`ack2` −0.9799 点（95%CI [−1.1388,−0.8210]），`ack4` −1.2500 点（95%CI [−1.4588,−1.0412]）。聚合 6/12 个机会对 3 条消息只作容量算术，**不能**推出逐节点/逐 deadline 不争用；本 claim 不测真实收据时延分布，也不由此关闭联合调度问题 | `code/analysis/reverse_feedback_budget.py` | `results/reverse_feedback_budget.json` | supported |

## 撤回表

| 原主张 | superseded_by | 理由 | 来源提交 |
|---|---|---|---|
| `deadline-purge` 承载相对同期限普通 expiry 的算法新颖性 | C2 | 两者逐位等价，机制即标准逐记录到期；增益改由跨段安置位置承载 | `e8ff1c4` |
| 固定资源下任何中心控制器都无空间（全局调度上界、零残差） | C1 | 干预与贪心装包不构成全体合法策略的上界；收窄为所测策略族上的限定负结果 | `e8ff1c4` |
| 本地夜间规则构成普遍安全保证 | C6 | 规则仅依据时钟，未证明任意采能与初始电量下的存活不变量；收窄为所测种子的经验结果 | `e8ff1c4` |
| 强制中断窗的 24/19 次「配置生效谎报」与 r38 零解析回退 | C8 | 原评分只在命令密集的决策上运行、在对照组从不运行、并统计提示词自身教会的词；决策数不等于成功请求数 | `e8ff1c4` |
| C11 原陈述：以「每小时 6/12 个机会 > 3 条消息」的容量比率判定收据与配置不争用，据此关闭候选 R1 并暗示真实反向确认落在 ≤1 个上行机会内 | C11 | 聚合容量比率不等于逐节点/逐截止期的可行性——仓库在 C1 上已有同一纪律（时段总供给有余不能排除某节点截止前缺机会）。真实收据作为独立下行消息时有普通 RX 丢失与重试、并真实消耗下行机会与空口；`ack0/1/2/4` 因此收窄为**条件性**延迟敏感性实验。真实收据的代价与联合调度判定另见本地探索记录 | `cffac6d` |
| 候选能量门在阴雨紧能量下保住存活且不损失黄级交付总数（开环交付界与滚动门同交付 849/2020） | C5 | 修正前的预测账本缺电池容量截断、任务发布门提前暴露未来 end；该读数的载体是 8be31d2 上的**未跟踪本地树**，从未入库。诚实账本下候选三臂降至 559/2016 与 1194/3528，而固定 8~h TTL 与 Task-1 有效期同样零死亡且 849/2020；详见 [归档](_withdrawn/2026-09-20-c5-precorrection.md) | `8be31d2` |
| C9 v1：受检格三方零差额、可实现差额为 0，据此"中间行已建成、方向已关闭" | C9 | v1 的求值器在黄级窗口终点替策略自动降档（隐藏授权终点改变了执行），且等权三点把偏移当标准差（实际 σ 只有声明值的 √(2/3)）；修正后该格在严格口径下无可行策略。见证见 [归档](_withdrawn/2026-09-20-c9-v1-semantics.md)；
反例由 `code/experiments/audit_seqref.py` 与 `results/c5_seqref.json` 的 `counterexamples` 字段随仓库复现（独立审阅的本地记录不随仓库发布） | `a665642` |
| C9 v2：紧能量格在严格口径下"无可行策略"，据此作为该格实质结论 | C9 | 把关口层级弄错：仓库目标函数把死亡计为一项、评测按臂报告死亡（r02 记录"0 存活主要是吸收态产物"），故"全部未来不得死亡"是风险口径的端点而非任务要求；此外 v2 的"序列最优"结构上等于贪心可行性规则。详见 [归档](_withdrawn/2026-09-20-c9-v2-semantics.md) | `1a36d52` |
| C10 原陈述：视界跟随自有收据时延的自适应规则抬升全时域服务 1.49 点 | C10 | 公平的普通到期对照显示 98.7% 的增益来自同一拍内「先删后传」的次序缺陷：周期不变的普通 expiry 只改边界即得 +1.47 点，`fixed2` 与 `adaptive` 相对它分别追加 0.0000 与 0.0183 点。视界延长不构成独立机制 | `2db290e` |
| 固定 TTL 在两个相位都无法满足存活与无黄级交付总数损失；当前结果证明合法在线交付界租约的独立增量 | C5 | 8 h TTL 在两相位满足上述计数判据；候选界读取未来降级时间并预置，未通过命令安装；详见 [不可变归档](_withdrawn/2026-09-20-c5-lease-claims.md) | `59e5ef1` |

## 维护规则

新增主张时同时给出脚本与参考结果，两者缺一不可。参考结果缺失时对应的实验脚本要先补机器可读输出；靠 `print` 输出的读数不得进入本表，因为它无法被机器核对。状态变化与章节编号变化在**同一次提交**里更新本表与 `results/README.md` 的登记条目。
