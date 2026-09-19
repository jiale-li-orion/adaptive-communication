# Terminating Installed Communication State When the Control Path Dies

**控制路径失效后终止已安装的通信状态：间歇灾前监测下的期限到期与交付界配置租约**

电池加小光伏的 LoRaWAN Class~A 灾前山区监测部署：节点经 LoRaWAN Class~A 接入现场网关，网关经蜂窝主回传与北斗短报文备用回传抵达中心；备用链路间歇可用、按量计费、只走反向。场景固定。

## 1. 两份成稿

| 文档 | 源码 | 成品 | 页数 |
|---|---|---|---|
| 英文稿 | [`paper/en/main.tex`](paper/en/main.tex) | [`paper/en/main.pdf`](paper/en/main.pdf) | 9 |
| 中文稿 | [`paper/zh/main.tex`](paper/zh/main.tex) | [`paper/zh/main.pdf`](paper/zh/main.pdf) | 14 |

两份互为独立成稿，结构一一对应，共享同一份 [`paper/refs.bib`](paper/refs.bib)。构建：

```bash
cd paper && ./build.sh            # 两份都构建；./build.sh en|zh 只构建一份
```

英文走 `pdflatex` 加 IEEEtran；中文走 XeTeX（`xetex -fmt=xelatex`，字体 Noto Serif CJK SC），因为本机没有 `xelatex` 命令也没有 `ctex`/`xeCJK`/`luatexja`/`CJK` 任一中文宏包。构建脚本首次运行会用 `xetex -ini -etex` 自建格式文件并缓存到 `paper/.build/`。

## 2. 摘要

**中文。** 山地站点回传失效之后，网络继续执行的是失效之前安装进去的通信状态。未确认的记录继续占满仅有的几次恢复接入批次；一条再也撤不回的密集采样配置继续耗电过夜。本文研究这两类**持久安装状态（persistent installed state）**可以依据什么证据、在哪个位置终止。两者归入**一个决策问题：部分证据下的本地终止**。节点只握有时钟、自身电量、缓存、最近接入收据与安装时刻携带的界，就此决定保留还是释放记录、维持还是退回配置，受无假释放、能量存续、证据局部性、无假完成四条约束。记录的终止时刻是业务期限，节点本地确定；该规则与标准 Bundle Protocol 的逐记录到期逐位相同，决定增益的是**跨段安置位置**：源端到期把中断按期交付从 202 提到 434、十种子 2.52 倍，而只在网关抑制过期发送会把代价反压到接入段。配置的终止时刻本地不可观测，它取决于走故障路径才能到达的任务修订，以及网关掌握的回传槽几何。中断与日落同相、能量宽松时时钟夜门够用；阴雨天气下它留下 20--31 个节点放电致死，而短到能救活这些节点的固定 config TTL 会在另一个中断相位误释放 183 条仍可交付的义务。**交付界租约（delivery-bounded lease）**是一条普通租约，界取当前档数据最后仍能满足义务的时刻，在各相位消除死亡且不误释放。全部结论来自确定性、仓库可复现的运行；端到端与跨模型验证列为后续工作。

**English.** When a mountain-site backhaul fails, the network keeps executing communication state that was installed before the failure. Unacknowledged records keep filling the few recovery access batches, and a dense sampling configuration that can no longer be countermanded keeps draining a battery overnight. We study where, and on what evidence, these two forms of *persistent installed state* can be terminated. One decision problem---local termination under partial evidence---covers both: a node holding only its clock, battery, cache, recent access receipts and install-time bounds decides to retain or release a record and to hold or relax a configuration, under no-false-release, energy-survival, locality and no-false-completion constraints. A record's termination time is its business deadline, locally certain; the rule is bit-identical to standard Bundle-Protocol per-record expiry, and its *cross-segment placement* decides the gain: source-local expiry raises outage on-time delivery 202→434 and 2.52-fold over ten seeds, whereas suppressing expired sends at the gateway alone back-pressures access. A configuration's termination time is not locally observable, because it depends on mission revisions travelling the failed path and on return-slot geometry held at the gateway. A clock night-guard suffices when the outage aligns with sunset and energy is ample; under overcast skies it leaves 20--31 nodes to discharge fatally, and a fixed config TTL short enough to save them falsely releases 183 still-deliverable obligations in another outage phase. A *delivery-bounded lease*---an ordinary lease whose bound is the last time the current profile's data can still meet an obligation---removes those deaths in every phase without false release. All claims come from deterministic, repository-reproducible runs; end-to-end and cross-model agent validation is future work.

## 3. 研究的问题

回传中断后，网络继续运行：**中断前安装的通信状态仍在执行，而终止它所需的控制与确认路径同时失效。** 两个可复现现象。未确认的缓存记录在确认前保留的边缘纪律下按最老优先重传，已过业务期限的记录继续占掉稀缺的恢复接入批；网关只停止发送、不释放源缓存，把代价压到接入段（中断按期 202→194）。一条已生效的密集采样配置在回传断后收不到中心的降级命令，继续按密集档耗电过夜；阴雨紧能量下节点放电致死，而中心信封发出的降级命令因下行不可达无法落地。

论文把这两类对象统一为**持久安装状态**：**记录状态**（未确认样本）与**配置状态**（已生效采样与上报档）。这是独立于 agent 的通信问题。

## 4. 系统模型

**义务与交付链。** 监测义务 $o=(n,m,[l_o,h_o),d_o)$ 定义在节点 $n$、测量量 $m$ 上；周期 $P$ 的例行义务有 $h_o-l_o=P$、$d_o=h_o+P$。样本满足义务的条件是测量量匹配、在窗口内采集、并在 $d_o$ 前被中心收到，依次经过节点采出合格样本、在网关被听到（LoRa 接入）、在 $d_o$ 前回传（蜂窝或短报文）、到达中心成为证据四个环节。分段任务首段用闭区间、后续段用半开窗口。

**部署与工作点。** 十四个节点分两组监测坡体位移与降雨。备用链路每 1200~s 一个 78 字节包，位移样本 6~B、降雨 4~B，每包约装 9--10 个。黄级任务周期 300~s，交付窗约 600~s，短于 1200~s 的备份槽间距。LoRa 接入每次机会以 $p_a{=}0.74$ 成功，主回传在非中断期以 $p_b{=}0.62$ 良好。节点数、角色与扰动按冻结的 Task v1.1 实例清单。

**控制中断。** 中断是区间 $\mathcal O=[a,b)$，其间主回传对中心到现场的流量不可用：中心命令与任务表段在准入处被拒、从未发出，短报文备用无法承载下行配置。期间能改变现场通信行为的只有节点（依据自身时钟、电量、缓存、最近接入收据与已生效命令携带的界）与网关（依据实际听到的样本、转发日志与已用备份槽）。中心保留授权变更的权力，没有安装变更的通道。

**能量。** 单次采样耗 $e_s{=}4.7{\times}10^{-4}$~Wh，单次上行耗 $e_u{=}2.33{\times}10^{-5}$~Wh，电池容量 $C{=}0.05$~Wh；日照为 12~h 半正弦，标称峰值 $0.03$~Wh/h，叠加随机云遮挡。整夜维持密集采样约耗 $0.071$~Wh，超过电池容量；电量归零的节点永久死亡。

**释放时刻与四条约束。** 对每个状态 $x$ 定义释放时刻 $t_{\mathrm{rel}}(x)$：在此之后继续保留已不可能为任何被满足的义务作出贡献。记录的 $t_{\mathrm{rel}}(s)=d(s)$；配置的 $t_{\mathrm{rel}}(q)$ 是该档数据仍能经某条可行路径满足的最后一条义务期限，即义务期限与最后回传槽时刻的较小者取最大。中断 $\mathcal O$ 内，实体对记录取 `retain` 或 `release`、对配置取 `hold` 或 `revert`，最小化未满足义务、节点死亡与超期存活状态的资源代价，受

- **C1 无假释放**：释放或降级不得早于 $t_{\mathrm{rel}}(x)$；
- **C2 能量存续**：SoC 全程不归零（主配置下归零是吸收态死亡）；
- **C3 证据局部性**：决策只用该实体在该时刻合法持有的证据，未来任务表段、全局样本与回传真值都出界；
- **C4 无假完成**：未知可行性下只报 unconfirmed 或 unfulfillable，宣告完成与宣告不可达同样出界。

**三态声明。** 每条可行性声明属于 confirmed（独立上报显示目标档，或有匹配样本被中心收到）、unconfirmed（命令在途中或收据不全，既不蕴含已生效也不蕴含链路已断）或 unreachable（由明确的网络侧状态得知当前路径已断）。LoRa 接入收据只构成接入链路的证据，凭它本身永远不能确立回传可达。

**关键不对称。** 记录的释放时刻节点凭公开节奏即可确定；配置的释放时刻取决于**任务修订**（只有走故障回传才能到达）与**回传槽几何**（只有网关掌握），节点在中断中不可观测。这一不对称是全文的技术中心。

## 5. 主张与机制

**记录侧：标准到期，增益来自跨段位置。** 每次上传机会删除 $d(s)\le t$ 的缓存记录，其余按最老优先发送，实现为 `deadline-purge` 与 `generic-expiry` 两种写法；后者是普通 BPv7 式逐记录生命期，$\text{expires}=t_s+((P-t_s\bmod P)+P)=d(s)$，不引用义务 id、槽几何或证书。两者在每种子上逐位相同，因此记录侧机制就是标准的逐记录到期，本文不主张新的丢弃算法。系统层的内容是端到端业务期限基准（用业务期限，而非包龄或逐跳 TTL）、零下行的源端安置，以及决定性的跨段一致性——确认耦合使得仅在网关释放并不能释放源端缓存。EDF 与义务贪心队列只重排、从不释放；AoI 的 `latest-only` 无差别释放，用放弃恢复后覆盖换取中断期新鲜度。

**配置侧：交付界租约（本文唯一的机制增量）。** 复用普通 config-lease/TTL，改动落在界的定义上：固定时长 $\Delta$ 换成**当前档数据的最后可交付时刻**，由网关在连接期间算好随安装命令下发，节点在 $t\ge\tau_L$ 且无下行时本地退回稀疏。该界只使用安装时刻有效的信息，从不预测未来的授权。与之并列的成熟做法是节点本地时钟与能量门：夜间钳回稀疏，白天不动中心命令，默认关闭且关闭时逐位不变。

**可行性投影与声明纪律。** 编译期中心持有义务表、当前（从不预测）的网络侧中断状态与公开参数；任务表到达时网关只持有它听到过的东西。结构性无回传证书仅由槽几何产生并显式以主回传不可用为条件，几何本身从不断言中断。到达时刻投影器只在本地位证据能区分各段时给出标注，否则返回 unknown。

**明确不主张的内容：** LLM 胜过求解器、新的丢弃算法、全局调度上界。确定性机制是同一层里对规则、求解器与 agent 同等可用的工具。

## 6. 关键结果

- **资源墙（scoped 负结果，非最优上界）**：Episode I 中强基线交付 3025/7560（0.400）；单放宽回传 4740、单放宽能量 4089、双放宽 6023。仅被回传容量阻塞 1715 条、仅被电池阻塞 1128 条、两者共同阻塞 155 条（2.0\%）。大吞吐增益来自物理放宽，因此论文的落点是**状态终止**而非更聪明的调度器。
- **全时域归因修正**：4535 条失约按"heard 不晚于 deadline"计为 energy 2002（44.1\%）/ capacity 1115（24.6\%）/ **access 830（18.3\%）** / time 588（13.0\%）。旧口径把这 830 条接入迟到记成回传容量（1945/0）；交付数 3025 在两口径下一致，改变的是损失记在哪一段。
- **记录到期**：源端到期把全时段服务从 0.373 提到 0.415（配对 **+4.21 点**，95\% 区间 +3.64/+4.79，10/10 为正）、中断按期交付 1691→4265（**2.52×**）、备份过期记录 2538→1、死亡 12→0；相对 `latest-only` 领先 +5.73 点。网关单侧抑制把中断按期从 202 压到 194。
- **配置租约**：阴雨峰值 $\eta{=}0.012$ 时时钟夜门在相位 A/B 分别死 20/31 个节点，交付几何租约两相位均 **0 死、0 误释放、最终 SoC 最高（0.066→0.122）**；固定 TTL 4~h 在相位 B **误释放 183 条**仍可交付的黄级义务、6~h 仍少 26 条，8~h 在相位 A 只剩最小能量裕度——**不存在两相位都安全的固定 TTL**。标称光伏下租约只省资源不改服务；$\eta{=}0.01$ 时连稀疏运行都无法供电（各机制约 40 死），此时的正确输出是声明不可兑现。
- **执行位置**：同一条"勿整夜密集"规则在中心是迟到、可被拒的建议（信封单独救不了最紧种子，朴素中心合规在三个种子上杀死 39 个节点、服务 0.162），在节点是每 tick 强制的不变量（死亡清零，被拒准入尝试压到 222）。预置零命令本地节奏在静态任务上达到 0.360，与中心编译臂相当——对预置任务的中心采样控制属 scoped 负结果。
- **任务表到达时的可判定范围**：2136 条已错过的黄级义务中，离线时间感知归因全部标对；只用网关在 $t_a{=}20$~h 前合法持有的证据可标注 1138/2136（**53.3\%**），已标注子集精度 100\%，其余 998 条保持 unknown（离线真值为 571 条从未采样、427 条在 $t_a$ 之后才被听到）。"从未采样"与"采到但尚未听到"在缺少证据时无法分离，这正是原始的 G5 约束。
- **真实 agent（形成性）**：deepseek-flash 11 条轨迹、1089 次决策。观测的 `link` 只含 LoRa 接入收据、不含回传状态，由此产生双向误判：A0/A0s 在强制中断窗给出 36/32 次"link 在线"乐观断言，A1 去噪后 1 次；v4 证书在 5 个健康链路时刻反向悲观。52 次解析失败退回 hold 的成因是 `max_tokens` 截断（逐臂格式失败率 A0 7.1\% / A0s 6.4\% / A1 1.3\%）。**agent 是候选控制器：问题定义先于它成立。**

## 7. 复现

两个受控场景。**Episode I**（v1.1 清单工作点：升级 $t{=}6$~h、中断 4--20~h、任务表 20~h 到网关）驱动资源墙、归因、记录到期、执行位置与 agent；**Episode II**（为隔离配置终止而构造：相位 A 升级 2~h、正午降级 6~h、中断 4--20~h，相位 B 升级 1~h、降级 8~h、中断 6--22~h；$t{=}0$ 为本地 06:00、$t{=}12$~h 为日落）驱动租约。两场景参数除时刻表、中断相位与光伏峰值外相同；Episode II 是受控构造，不构成新的现场事实。

```bash
R="$PWD"
export PYTHONPATH="$R/libs/pylibs:$R/code/v3joint:$R/code/instance:$R/code/physics:$R/code/runtime:$R/code/experiments:$R/code/analysis:$R/code/monitoring"
python3 code/run_checks.py            # 18/18：含 results/README 登记与磁盘 json 互为子集的一致性校验
python3 code/v3joint/test_joint.py    # 5/5 联合层锚点（关闭备份/guard/lease 时与 v1.1 逐位一致）
```

| 论文对象 | 脚本 | 结果 |
|---|---|---|
| 全时域时间感知归因（830 修正） | `code/v3joint/r44_fullhorizon_attribution.py` | `results/r44_fullhorizon_attribution.json` |
| 时钟对齐与 residual 现象见证 | `code/v3joint/r45_residual_witness.py` | `results/r45_residual_witness.json` |
| 租约 $\tau$ 扫描与交付几何界 | `code/v3joint/r46_lease_sweep.py` | `results/r46_lease_sweep.json` |
| 光伏能量 × $\tau$ | `code/v3joint/r47_lease_energy.py` | `results/r47_lease_energy.json` |
| 固定 TTL 对照交付租约（两相位） | `code/v3joint/r48_ttl_vs_lease.py` | `results/r48_ttl_vs_lease.json` |
| 记录到期等价性与跨段 | `code/v3joint/r41_expiry_equiv.py` | `results/r41_expiry_equiv.json` |
| 网关本地到达归因（53.3\%） | `code/v3joint/r40_local_attribution.py` | `results/r40_local_attribution.json` |
| agent 声明对称重标与 v5 投影器重放 | `code/v3joint/r42_claim_relabel.py`、`r43_cert_v5_replay.py` | `results/r42_claim_relabel.json`、`results/r43_cert_v5_replay.json` |
| 资源墙、十种子、执行位置对照 | r30 系列 / r37e / r39 | 同名 json，口径见 `results/README.md` |

每个数字的脚本、口径与分母登记在 [`results/README.md`](results/README.md)；新增 json 必须在此登记。真实模型实验需配置 `DEEPSEEK_API_KEY`，并把请求、重试与解析计入账本（决策数不等于成功请求数）。

## 8. 仓库结构

| 路径 | 内容 |
|---|---|
| `paper/` | 论文英文稿与中文稿的 LaTeX 源码、PDF、共享书目与构建脚本 |
| `code/instance/` | 节点、网关、能量、外生义务与评分；`network.py` 含缓存纪律、本地时钟夜门与租约执行器（默认关闭） |
| `code/v3joint/` | 当前联合通信实验、任务视图门、agent harness、r37--r48 |
| `code/physics/`、`code/analysis/`、`code/monitoring/`、`code/runtime/`、`code/experiments/` | 地形与传播、轨迹分析、监测、早期执行语义、历史对照 |
| `results/` | 结果与 agent 轨迹；以 `results/README.md` 为登记册，`results/_withdrawn/` 为作废清单 |
| `data/`、`libs/` | 原始数据与依赖，按获取说明在本地准备，不入版本控制 |

## 9. 边界与后续

资源墙与吞吐负结果**仅限所测策略族与单一工作点**，不构成最优性定理；租约结果是两相位、五采能点的确定性证据，证明机制存在与固定 TTL 跨相位失效，不主张普适参数。备份速率与载荷、节点数、容量、云模型与复机阈值的更广扫描待做。Episode II 是配置子问题的受控场景，独立于现场测量；中心确认建模为同步且不占空口，该简化同等有利于各队列规则。

**端到端与跨模型重跑由作者后续自补**：unknown-aware v5 证书（建议给观测增加网络侧 `primary_backhaul_state` 字段）、硬化记账与对称评分器三者就位后，重跑 A0/A0s/A1 多 seed，并新增 **matched-capability 臂**（给普通对照同样的昼夜策略、几何常量、确认规则与 note 模板，但不给段投影器），端到端串上本地安全门后再评残留死亡，并做跨模型复现。harness 已就绪，本仓库不主张这些结论。

**场景与证据纪律。** 场景固定为灾前山区监测，风险等级与授权由外部给定（DZ/T 0460--2023 §5.3.3 允许按预警等级远程调采样与上传频率，§8.4.1 定义四级、§8.4.2 会商升降级，具体周期是研究选择；备用速率与载荷依据 BDS-OS-PS-3.0 与 DZ/T 0450--2023，1200~s/78~B 是已声明的研究选择）；系统判滑坡风险出界，删除失约义务或改分母同样出界。强基线公平：禁止 strawman、禁止"调到赢"、禁止为救方法改判据或收紧任务；普通规则、MPC 与标准机制带来的增益同样计入通信系统贡献，普通组合已覆盖的部分如实关闭。来源分级 A/B/C/D，未核验不进事实表。

历史文档、逐轮审计与提交溯源另在本地维护，不在本仓库中；索引见本地 `docs/_archive/README.md`。
