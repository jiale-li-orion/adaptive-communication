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
| C5 | §7.3 表 3 | 普通机制覆盖配置终止这一格：$\eta{=}.012$ 下固定 8~h TTL 与 Task-1 `valid_until` 在 A/B 两相位均为零死亡且黄级交付 849/2016、2020/3528；候选能量门（开环界、滚动门、安全网三等价）同为零死亡但降至 559/2016、1194/3528。该结论的成立条件是**非预知预测器加电池容量项**，不是“密采物理不可行” | `code/v3joint/c5_matrix.py` | `results/c5_matrix.json` | scoped-negative |
| C6 | §7.5 表 5 | 同一规则在中心与节点的执行位置对照；节点本地门消除所测种子死亡并压低被拒准入 | `code/v3joint/r39_envelope.py` | `results/agent_traces/r39_table.json` | supported |
| C7 | §7.4 表 4 | 任务表到达时仅凭网关本地证据的可判定覆盖与已判定精度 | `code/v3joint/r40_local_attribution.py` | `results/r40_local_attribution.json` | supported |
| C8 | §7.6 | 真实 agent 十一轨迹、1089 次决策的对称计量；接口故障与解析失败账目 | `code/v3joint/r38_agent_three_arm.py`、`code/v3joint/r42_claim_relabel.py`、`code/v3joint/r43_cert_v5_replay.py` | `results/agent_traces/r38_three_arm_summary.json`、`results/r42_claim_relabel.json`、`results/r43_cert_v5_replay.json` | formative |
| C9 | §7.3 | 按预注册 v3 的单节点声明模型。**层级**：'全部未来零失电'是风险口径层的一个端点（α=0），不是任务要求——论文目标函数把死亡计为一项、评测按臂报告死亡、`v3joint_r02_restart.json` 记录'0 存活主要是吸收态产物'、r47 已写明不得外推为物理不可行。**结构**：strict 口径下精确最优**恰好等于**贪心可行性规则（序列内容为空，已逐状态核对），λ>0（与论文一致地给死亡计价）才出现真正的停止规则。**读数**：C5 实测格（峰值 .012、σ=.047）strict 端点不可行（稀疏最低 −0.0087 mWh < 0.47 mWh，临界 σ*=.0429），该结论只在该口径内成立；计价口径下非预知最优 48/48、死亡概率 3.5e-5，最强普通组合（`ttl7`+8 mWh 门）同样 48/48、3.5e-5 → 两个差额均 ≈ 0。**能力边界**：本模型是最优**停止**问题，不是调度问题，故不得据此谈密集预算的最优分配。v1/v2 口径下的结论均已撤回 | `code/v3joint/c5_seqref.py`、`code/experiments/measure_seqref_calibration.py`、`code/experiments/audit_seqref.py` | `results/c5_seqref.json`、`results/c5_seqref_calibration.json` | open |
| C10 | §5.1、§7.2 | **源端到期的同拍次序缺陷及其修正**：现行实现于每次上报/转发**之前**按 `expires_at <= t_s` 删除记录，而评分接受 `received_at <= deadline`，故期限恰为当拍的记录被删而非上传（相位 A、peak .012、ttl8、十种子：`current` 到期当拍被听到 0 条）。只把边界改为保留截止当拍（普通 expiry，周期不变）即把全时域服务从 61.1081% 提到 **62.5778%（+1.47 点，95%CI [+1.28,+1.66]，10/10 为正）**，其中 1674/1792 条被救样本的听到时刻恰等于真业务期限；死亡 3→4、最低电量 0.162→0.182 mWh，故按 (服务, 死亡) 二元报告，不主张支配。**视界延长相对该修正无额外增益**：`fixed2` 与修正版逐位相同（27334 = 27334），`adaptive` 仅多 0.0183 点。网关侧不受影响（`maxcov` 不按期限排除，`salvage` 用 `dl <= t_s`）；该缺陷对 C3 不利，故 C3 的 +4.21 点未被抬高 | `code/analysis/retention_deadline_audit.py` | `results/retention_deadline_audit.json` | supported |

## 撤回表

| 原主张 | superseded_by | 理由 | 来源提交 |
|---|---|---|---|
| `deadline-purge` 承载相对同期限普通 expiry 的算法新颖性 | C2 | 两者逐位等价，机制即标准逐记录到期；增益改由跨段安置位置承载 | `e8ff1c4` |
| 固定资源下任何中心控制器都无空间（全局调度上界、零残差） | C1 | 干预与贪心装包不构成全体合法策略的上界；收窄为所测策略族上的限定负结果 | `e8ff1c4` |
| 本地夜间规则构成普遍安全保证 | C6 | 规则仅依据时钟，未证明任意采能与初始电量下的存活不变量；收窄为所测种子的经验结果 | `e8ff1c4` |
| 强制中断窗的 24/19 次「配置生效谎报」与 r38 零解析回退 | C8 | 原评分只在命令密集的决策上运行、在对照组从不运行、并统计提示词自身教会的词；决策数不等于成功请求数 | `e8ff1c4` |
| 候选能量门在阴雨紧能量下保住存活且不损失黄级交付总数（开环交付界与滚动门同交付 849/2020） | C5 | 修正前的预测账本缺电池容量截断、任务发布门提前暴露未来 end；该读数的载体是 8be31d2 上的**未跟踪本地树**，从未入库。诚实账本下候选三臂降至 559/2016 与 1194/3528，而固定 8~h TTL 与 Task-1 有效期同样零死亡且 849/2020；详见 [归档](_withdrawn/2026-09-20-c5-precorrection.md) | `8be31d2` |
| C9 v1：受检格三方零差额、可实现差额为 0，据此"中间行已建成、方向已关闭" | C9 | v1 的求值器在黄级窗口终点替策略自动降档（隐藏授权终点改变了执行），且等权三点把偏移当标准差（实际 σ 只有声明值的 √(2/3)）；修正后该格在严格口径下无可行策略。见证见 [归档](_withdrawn/2026-09-20-c9-v1-semantics.md)；
反例由 `code/experiments/audit_seqref.py` 与 `results/c5_seqref.json` 的 `counterexamples` 字段随仓库复现（独立审阅的本地记录不随仓库发布） | `a665642` |
| C9 v2：紧能量格在严格口径下"无可行策略"，据此作为该格实质结论 | C9 | 把关口层级弄错：仓库目标函数把死亡计为一项、评测按臂报告死亡（r02 记录"0 存活主要是吸收态产物"），故"全部未来不得死亡"是风险口径的端点而非任务要求；此外 v2 的"序列最优"结构上等于贪心可行性规则。详见 [归档](_withdrawn/2026-09-20-c9-v2-semantics.md) | `1a36d52` |
| C10 原陈述：视界跟随自有收据时延的自适应规则抬升全时域服务 1.49 点 | C10 | 公平的普通到期对照显示 98.7% 的增益来自同一拍内「先删后传」的次序缺陷：周期不变的普通 expiry 只改边界即得 +1.47 点，`fixed2` 与 `adaptive` 相对它分别追加 0.0000 与 0.0183 点。视界延长不构成独立机制 | `2db290e` |
| 固定 TTL 在两个相位都无法满足存活与无黄级交付总数损失；当前结果证明合法在线交付界租约的独立增量 | C5 | 8 h TTL 在两相位满足上述计数判据；候选界读取未来降级时间并预置，未通过命令安装；详见 [不可变归档](_withdrawn/2026-09-20-c5-lease-claims.md) | `59e5ef1` |

## 维护规则

新增主张时同时给出脚本与参考结果，两者缺一不可。参考结果缺失时对应的实验脚本要先补机器可读输出；靠 `print` 输出的读数不得进入本表，因为它无法被机器核对。状态变化与章节编号变化在**同一次提交**里更新本表与 `results/README.md` 的登记条目。
