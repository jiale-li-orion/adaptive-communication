# Terminating Installed Communication State When the Control Path Dies

**灾前山区滑坡/泥石流监测：电池＋小光伏、LoRaWAN Class A 接入、网关现场自治、蜂窝主回传＋北斗短报文备用（间歇、计量、仅反向）。场景固定，不替换。**

英文工作稿：**“Terminating Installed Communication State When the Control Path Dies: Deadline Expiry and Delivery-Bounded Configuration Leases for Intermittent Pre-Disaster Monitoring”**（method v1.2 / paper v0.8）。
更新：2026-09-19。

- 论文 PDF：[`docs/s8-report/latex/main.pdf`](docs/s8-report/latex/main.pdf)（16 页）；源码 [`main.tex`](docs/s8-report/latex/main.tex)、[`refs.bib`](docs/s8-report/latex/refs.bib)。
- 方法收敛与证据边界：[doc52](docs/s7-method/v1.2/52-runtime-convergence-assessment-2026-09-19.md)、[doc53（v0.7 重接地）](docs/s7-method/v1.2/53-v07-regrounding-and-paper-revision-2026-09-19.md)；独立审查 [doc51](docs/s7-method/v1.2/51-independent-review-paper-v06-2026-09-19.md)。
- 每个数字的脚本/口径/分母：[results/README.md](results/README.md)（结果登记册，新增 json 必须在此登记）。

## 1. 研究的网络失效（具体行为，不是抽象概念）

回传中断后网络并不会停住：**中断前安装进去的通信状态仍在持续执行，而终止它所需的控制/确认路径恰好已经失效。** 两个可复现现象：

1. 未确认的缓存记录在 hold-until-ACK 边缘纪律下被最老优先重传，**已经过了业务期限的记录继续占掉稀缺的恢复接入批**；网关只停止发送、不释放源缓存，反而把代价压到接入段（中断按期 202→194）。
2. 一条已生效的密集采样配置，在回传断后无法被中心降级命令撤回，**继续按密集档耗电过夜**；阴雨紧能量下节点放电致死，而中心信封/降级命令因下行不可达救不了。

论文把这两类对象统一为 **persistent installed state（持久安装状态）**：record state（未确认样本）与 configuration state（已生效采样/上报档位）。这是一个独立于任何 agent 存在的通信问题。

## 2. Problem 1：部分证据下的本地终止（论文 §3–§4）

中断 `O=[a,b)` 内，仍持有合法证据的实体（节点：时钟、自身 SoC、缓存、最近 Class A 收据、命令安装时携带的 bound；网关：实际听到的样本、转发日志、备份槽）对每类状态选动作：
record `a∈{retain, release}`，config `a∈{hold, revert}`。最小化未交付义务＋死亡＋超期状态占用成本，受四条约束：

- **C1 no-false-release**：不得早于“最后可交付时刻” `t_rel(x)` 释放/降级；
- **C2 energy-survival**：SoC 全程不归零（主配置下为吸收态死亡）；
- **C3 locality**：决策只能用该实体在 t 时刻合法持有的证据（不得读未来任务表段、全局样本、回传真值）；
- **C4 no-false-completion**：判不了就报 unconfirmed / unfulfillable，不得宣告完成或不可达。

关键不对称：record 的 `t_rel(s)=业务 deadline`，节点凭公开节奏即可确定；config 的 `t_rel(q)` 取决于走故障回传才能到达的**任务修订**和只有网关掌握的**回传/备份槽几何**，节点在中断中不可观测。

## 3. 机制地图：成熟原语如实署名，只剩一个 residual

| 持久状态 / 情形 | 普通机制（先公平施加） | 是否覆盖 | 证据 |
|---|---|---|---|
| 缓存记录到期 | 每记录到期 = BPv7 lifetime / 标准 deadline expiry | **覆盖**；`deadline_purge` 与 `generic_expiry` 十种子**逐位等价** | r41 |
| 记录：在哪释放 | 端到端业务期限基准＋**源/网关跨段一致性**（网关单侧抑制会反压接入） | 系统组合增量：中断按期 202→434、2.52× | r41/r37e |
| 配置：夜间密集耗电 | 节点本地**时钟夜门 / 能量 guard**（成熟 time/energy rule） | 中断与日落同相、能量宽松时覆盖 | r39/r45/r47 |
| 配置：白天降级落入中断＋阴雨紧能量 | 固定时钟门滞后致死；**任何固定 TTL 都无法跨相位两全** | **不覆盖 → residual**：**delivery-bounded config lease** | r46/r47/r48 |
| 段归因 / 可行性 | 槽几何出条件性证书；不可判保留 unknown | 在线 53.3% 可判、已判精度 100%；全时域 time-aware 归因 | r40/r43/r44 |

**Delivery-bounded lease（论文唯一的机制增量）** 不发明新原语，而是复用普通 config-lease/TTL，把它的 bound 从“固定时长 Δ”重做为**当前档数据的最后可交付时刻**（最后一条可交付义务的 deadline 对齐到主/备回传槽，Eq. 1），由网关在连接时算好随安装命令下发，节点在 `t≥τ_L` 无下行本地回 sparse。类比 SVC-HARQ 复用 HARQ 但重设 error criterion：成熟原语 + 新通信对象 ⇒ 实质性重设计，而非工程拼装。

## 4. 关键结果（数字与分母见 results/README，均可仓库复现）

- **资源墙（scoped 负结果，非最优上界）**：Episode I 7560 条义务，强基线交付 3025（0.400）；单放宽回传 4740、单放宽能量 4089、双放宽 6023。大吞吐增益是物理性的，因此论文转向**状态终止**而非更聪明的调度器；不声称零残差或全局最优。
- **全时域归因修正（r44）**：4535 条失约按“heard 不晚于 deadline”计为 energy 2002 / capacity 1115 / **access 830** / time 588；旧 heard-ever 口径误把这 830 条接入迟到记成回传容量（1945/0）。交付数 3025 两口径一致。
- **记录到期（r41，maxcov 固定）**：源端到期使全时段服务 0.373→0.415（配对 **+4.21 点**，95%CI +3.64/+4.79，10/10 为正）、中断按期 1691→4265（**2.52×**）、备份过期记录 2538→1、死亡 12→0；标准到期与证书 purge 逐位相同。
- **配置租约（r46–r48，generic_expiry+maxcov 固定）**：标称光伏下租约只省资源不改服务；阴雨峰值 η=.012 时，时钟夜门在相位 A/B 分别死 20/31 节点，交付几何租约两相位均 **0 死、0 误杀、最终 SoC 最高（约翻倍）**；固定 TTL 4h 在相位 B **误杀 183 条**仍可交付的 yellow 义务、6h 仍少 26，而 8h 在相位 A 仅余最小电量裕度——**不存在两相位都安全的固定 TTL**。η=.01 连 sparse 都供不上（各机制皆死），正确输出是声明 unfulfillable。
- **执行位置（r39）**：同一条“勿整夜密集”规则在中心是迟到、可被拒的建议（信封单独救不了最紧种子），在节点是每 tick 强制不变量（三种子死亡清零）；预装零命令本地节奏在静态任务上达到 0.360，与中心编译臂相当（对预装任务的中心采样控制为 scoped 负结果）。
- **真实 agent（formative，r38/r42/r43）**：deepseek-flash 11 条轨迹 1089 决策。观测 `link` 只有 LoRa 接入收据、无回传状态，导致双向误判（A0/A0s 强制中断窗 36/32 次“link up”乐观断言，A1 去噪后 1 次；v4 证书在 5 个健康链路时刻反向悲观）。52 次解析失败→hold 系 max_tokens 截断（逐臂格式失败率 A0 7.1%/A0s 6.4%/A1 1.3%），不是模型选择 hold。unknown-aware v5 离线 replay 把健康链路误报全部改 unconfirmed、把 528 次夜间硬杀拆成 189 真能量不可行＋339 建议。**agent 只是候选 controller，不是问题定义的一部分。**

## 5. 复现地图

两个受控场景：**Episode I**（v1.1 manifest：升级 t=6h、中断 4–20h、任务表 20h 到网关）驱动资源墙/归因/记录到期/位置/agent；**Episode II**（为隔离 config 终止构造：相位 A 升级 2h/正午降级 6h/中断 4–20h，相位 B 升级 1h/降级 8h/中断 6–22h；t=0=本地 06:00、t=12h=日落）驱动租约，参数除 schedule/中断相位/光伏峰值外与 I 相同，**不是新的现场事实**。

| 论文对象 | 脚本 | 结果 json |
|---|---|---|
| 全时域 time-aware 归因（830 修正） | `code/v3joint/r44_fullhorizon_attribution.py` | `results/r44_fullhorizon_attribution.json` |
| 时钟对齐与 residual 现象见证 | `code/v3joint/r45_residual_witness.py` | `results/r45_residual_witness.json` |
| 租约 τ 扫描 / 交付几何 bound | `code/v3joint/r46_lease_sweep.py` | `results/r46_lease_sweep.json` |
| 光伏能量 × τ | `code/v3joint/r47_lease_energy.py` | `results/r47_lease_energy.json` |
| 固定 TTL vs 交付租约（两相位） | `code/v3joint/r48_ttl_vs_lease.py` | `results/r48_ttl_vs_lease.json` |
| 记录到期等价性 / 跨段 | `code/v3joint/r41_expiry_equiv.py` | `results/r41_expiry_equiv.json` |
| 网关本地到达归因（53.3%） | `code/v3joint/r40_local_attribution.py` | `results/r40_local_attribution.json` |
| agent 声明对称重标 / v5 证书 replay | `code/v3joint/r42_claim_relabel.py`、`r43_cert_v5_replay.py` | `results/r42_claim_relabel.json`、`r43_cert_v5_replay.json` |
| 资源墙、十种子、位置对照 | r30 系列 / r37e / r39（命令与口径见 results/README） | 同名 json |

自检（不调用 LLM；在仓库根目录）：

```bash
R="$PWD"
export PYTHONPATH="$R/libs/pylibs:$R/code/v3joint:$R/code/instance:$R/code/physics:$R/code/runtime:$R/code/experiments:$R/code/analysis:$R/code/monitoring"
python3 code/run_checks.py            # 18/18：含 results/README 登记与磁盘 json 互为子集的一致性校验
python3 code/v3joint/test_joint.py    # 5/5 联合层锚点（关闭备份/guard/lease 时与 v1.1 逐位一致）
```

构建论文：`cd docs/s8-report/latex && pdflatex -interaction=nonstopmode main && bibtex main && pdflatex ... && pdflatex ...`（无 latexmk）。

真实模型实验需配置 `DEEPSEEK_API_KEY`，并计入请求、重试与解析账（决策数≠成功请求数）。

## 6. 仓库导航

| 路径 | 内容 |
|---|---|
| `code/instance/` | 节点/网关/能量/外生义务/评分；`network.py` 含缓存纪律、本地时钟夜门与 lease 执行器（默认关闭） |
| `code/v3joint/`（118 脚本） | 当前联合通信实验、任务视图门、agent harness、r37–r48 |
| `code/physics/` `code/analysis/` `code/monitoring/` `code/runtime/` `code/experiments/` | 地形/传播、分析、监测、早期执行语义、历史对照；旧负载结论不自动迁入 v1.1 |
| `results/`（372 json） | 结果与 agent 轨迹；以 `results/README.md` 为登记册，`results/_withdrawn/` 为作废清单 |
| `docs/s1-input`…`docs/s6-model` | 输入、场景、新颖性、故障源、benchmark、模型 |
| `docs/s7-method/v1.2/`（55 篇） | 逐轮预注册、反例、复核、独立审查；关键：01 来源审计、doc33 全局综合、doc51/52/53 |
| `docs/s8-report/` | 论文 LaTeX、草稿、进度日志、`review-v0.6/`、`review-v0.7/`（外部只读审查证据） |
| `docs/早期状态/` | 1525 行旧 README、D1–D54 决策与旧论文说明的完整归档 |

## 7. 场景红线与证据纪律

- 不换场景：灾前山区监测、LoRaWAN Class A、网关现场自治、电池＋小光伏、蜂窝主＋北斗短报文备；节点规模/角色/扰动按 Task v1.1 manifest（主表 14 节点；旧 D2 的 16 节点不作现场事实）。中继/备用回传仅在有硬件与能力依据时进入扩展。
- 风险等级与授权由外部给定（DZ/T 0460 §5.3.3 允许按预警等级远程调采样/上传频率，§8.4.2 会商升降级；具体周期是研究选择）；系统不判滑坡风险、不删失约义务、不改分母。
- 强基线公平：不造 strawman、不“调到赢”、不为救方法改判据/改紧任务；普通规则/MPC/标准机制获益也算通信系统贡献；普通组合覆盖就诚实关闭。
- 来源分级 A/B/C/D，未核验不进事实表；标准取文一处为文档分享站（A 级文档/D 级复制链，官方站本机 TLS 失败），国际 LoRa+卫星与部分厂商线未核实，不充当事实。

## 8. 已知边界与 future work

- 资源墙与吞吐负结果**仅限所测策略族与单一工作点**，不是最优性定理；租约结果是两相位/五光伏点的确定性证据，证明机制存在与固定 TTL 跨相位失效，不声称普适参数。备份速率/载荷、节点数、容量、云模型、复机阈值的更广扫描待做。
- Episode II 是为 config 子问题构造的受控场景，不是独立现场测量；中央确认建模为同步无空口（同等有利于各队列规则）。
- **cross-model 与端到端 v5 重跑由作者后续自补**：unknown-aware v5 证书（建议给观测增加网络侧 `primary_backhaul_state` 字段）＋硬化记账＋对称评分器，重跑 A0/A0s/A1 多 seed，新增 **matched-capability 臂**（给普通对照同样的昼夜策略/几何常量/确认规则/note 模板但不给段 projector），端到端串 L0 后再评 r38 残留 4 死，以及跨模型复现。harness 已就绪、协议见 doc53 §3，本仓库不主张这些结论。

历史编号、被推翻结论与提交溯源见 `docs/早期状态/`、`results/_withdrawn/MANIFEST.md` 与 `docs/s8-report/progress-log.md`；引用历史读数时同时核对后续审查是否收窄了其适用范围。
