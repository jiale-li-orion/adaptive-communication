# D — 可防御的空白、母论文 task 范式、venue 与缺全文清单

> **本文性质：只读提取。** 不评价本项目方法现状，不做实验，不补全任何文献信息。
> 每条结论带 `文件名:行号`；材料没写的一律写「**材料未给出**」。
>
> **材料基准（均在 `docs/s3-novelty/`）**
>
> | 文件 | 行数 | 本文用它做什么 |
> |---|---|---|
> | `prior-art-agent-runtime.md` | 743 | 已占据机制清单、Gap 1–7、诚实性约束 |
> | `prior-art-mother-papers.md` | 263 | 母论文做了什么/怎么做、最近先行工作、未验证清单 |
> | `venue-and-positioning.md` | 339 | venue 建议与理由、隐含要求 |
> | `verified-evidence.md` | 346 | 一手核验证据、novelty threat、PoC 方法学发现 |
> | `shijin-group-survey.md` | 132 | 同域（金石组）已占/未占的方向 |
> | `topollm-fulltext-completion-audit.md` | 54 | TopoLLM 全文级 task 构造与完成链条 |
>
> **另引 2 份同目录材料**（交付项 5 的「必读项仍缺 N/M」原文、以及一处风险评级原文只出现在其中，不引会造成缺证）：
> - `agent-assumption-audit.md`（67 行）— 四判定问题逐篇核对表、G1–G7、**「最大风险项」原文**、「仍缺 4 项」原文
> - `paper-strategy-review.md`（88 行）— 另一套 venue 建议（主论文 TNSM + 另起 SenSys 短论文）

---

## 0. 引用与措辞纪律（材料自带的约束，设计 task 时须一并遵守）

- 材料对全部空白的方法论声明：**"All are phrased as 'no positive hit found,' not 'proven absent.'"**（`prior-art-agent-runtime.md:684`）；全文警告 "Absence of a hit is *not* proof of absence."（`prior-art-agent-runtime.md:27`）。
- 材料明令禁止的两种写法：不可写 "no prior work injects network faults"，不可写 "no one injects faults into agents"（后者 "is false and refutable in one paragraph"）（`prior-art-agent-runtime.md:723-724`）。
- 材料给本项目的**诚实性约束**：机制层正在被 2026 年的其他组实时发表，可防御的贡献"is now narrower"（`verified-evidence.md:295-296`）。
- 材料对 TopoLLM 判定的收窄：不可泛化成"其真实部署假设所有工具可靠即时"（`topollm-fulltext-completion-audit.md:36`、`agent-assumption-audit.md:28`）。

---

## 1. Gap 清单

### 表 1-A｜`prior-art-agent-runtime.md` 自列的 Gap 1–7（材料原文按可防御性排序）

| # | Gap 一句话 | 支撑它的先行工作（谁做了什么 / 差在哪） | 材料给出的风险评级 | 需要什么实验才能证实 |
|---|---|---|---|---|
| **A1** | 把**射频/信道/DTN 故障模型**叠加到 agent 工具调用上的注入 harness 不存在——现有注入全在 tool-API 层、上下文层或基础设施层（`prior-art-agent-runtime.md:686-687`） | AgentDisruptBench 的 20 类清单是**工具调用层**；AgentChaos 在**共享 HTTP 接口**注入；ReliabilityBench 是**应用层**故障；ToolMaze 是工具异常（`:688`）。差在"no positive hit … that overlays a radio/channel/DTN fault model — packet loss as a channel process, ACK loss, node disconnect mid-call, store-and-forward replay after reconnection — onto an agent's tool invocations"（`:687`） | 原文 **"Risk:** α³-Bench models packet loss/jitter/throughput; it is the closest to crossing this line. **Read it in full.**"（`:690`）；**"α³-Bench（arXiv 2601.03281）—— Gap 1 的最大风险项，必须补读。**需确认它是把 packet loss 作用到 **tool call** 上，还是只影响推理上下文。这个问题不解决，Gap 1 的表述就不能落笔。"（`agent-assumption-audit.md:64`） | 需一个「信道故障 → 工具调用」的注入 harness；材料给的配方：**6GAgentGym 的 effect-typed 工具分类 + 2608.02645 的注入式故障 harness + 2608.03836 的 fault-matrix 方法学**三者组合（`prior-art-mother-papers.md:235`）。前置条件：先读完 α³-Bench 全文（`prior-art-agent-runtime.md:690`；`paper-strategy-review.md:78`） |
| **A2** | 「动作已执行但无法得知」**不作为一类被注入的故障类**——它只在事务/恢复文献里作为语义关切出现（`prior-art-agent-runtime.md:692-693`） | AgentDisruptBench 的 `timeout` 是**可见**超时；ToolMaze 的故障都留有替代路径（agent 能判断工具失败）；unknown-outcome / duplicate-delivery 只在 SagaLLM、DART、ACRFence、Atomix、Restate durable webhooks 等语义工作里被讨论，**"never as *injected fault classes* with a measured failure rate"**（`:693`） | 材料未给出"风险"字样评级；给出的是定性判断：**"This is the sharpest gap because it is a *taxonomy* gap, not a coverage gap"**（`:694`）。外部佐证：ACRFence 提供该类造成不可逆现实损害的可同行评审证据（`:694`） | 注入「occurrence is epistemically unavailable to the agent」的故障，并**测量由此产生的重复副作用**；材料给的可落笔句：*"Existing benchmarks inject failures whose occurrence is observable. We inject failures whose occurrence is epistemically unavailable to the agent, and measure the resulting duplicate side effects."*（`:695`） |
| **A3** | 把**副作用类别 × authority** 绑定到**恢复策略**，并在「退化 → 超时 → 不可用 → 恢复」的能力生命周期下求解——即 recovery policy = f(side_effect_class × availability state × freshness/age × mission criticality) 这个**乘积**（`:697-699`） | 6GAgentGym 已做只读/状态变更的分类，但用于学习与奖励，**不是**重试/重放/补偿决策（`:698`、`:510`、`:667`）；材料称没有任何正面命中把 side-effect class 与 authority 耦合到 degraded capability availability 下的 recovery policy（`:698`） | 原文 **"Risk:** arXiv 2605.02697 (executor-side risk-gated actuation) and arXiv 2605.12729 (privilege levels) are close on parts of this. Read both."（`:700`） | 需要一个**四因子组合**实验设计：把当前文档 §3 的 side_effect_class / authority / availability / 能力生命周期组合进同一个恢复策略，并用任务关键度与能量把决策逼出来（`:699`）。材料注明"the individual axes are all known; the *product* is not"（`:699`） |
| **A4** | 没有 agent benchmark 的**故障过程来自实测链路/断连 trace**；本项目的故障分布可以 trace-driven（`prior-art-agent-runtime.md:702-704`） | 材料写 **"No positive hit** found for any agent benchmark whose fault process is derived from measured link/outage traces."（`:703`）。Caveat 自带：trace-driven 评测分布式系统本身很老，贡献必须表述为 trace-driven **agent execution semantics**；且需核实所引数据集是否真的暴露 link-level trace（`:705`） | 材料未给出风险评级；仅给"AI-assisted: this is distinctive and hard to refute"（`:704`）与上述 caveat（`:705`） | 用实测 trace 生成故障分布；且必须**显式报告 flapping / missed-outage 权衡**：PoC 证明把 1102 次可用性转换压到 14 次所需的 dwell，会同时抹掉该 trace 里全部真实 outage（总计约 25 分钟、5 个连续样本）（`verified-evidence.md:202-220`）。解法：不要手调单一阈值，改用 IODA 异常打分序列（`gtr-sarima` / `gtr-norm`）或**两时间尺度状态机**（快速 outage 检测 + 慢速退化基线）（`verified-evidence.md:217-220`） |
| **A5** | 三支互不引用的文献之间没有桥：持久执行语义在系统产品与数据库论文、故障注入评测在 ML/agent benchmark 社区、无线 agent benchmark 在通信社区（`:707-708`） | 三支各自的代表（`:708`）。差在 **"No positive hit found for work that bridges all three."**（`:708`） | 材料称其为 **"The cleanest *positioning* gap"**（`:708`）；但同一材料同时把"整体 framing"列为**不新颖**（`:675`），并称"the *thesis* is already stated in the literature" | 材料**未给出实验方案**，只给定位句：*"Mature execution semantics are available in systems; rigorous fault injection is available in the agent-benchmark literature; realistic communication impairment models are available in the wireless literature. What does not exist is a runtime that binds them together under a disaster-communication fault model."*（`:709`） |
| **A6** | 缺**终态副作用等价**这类正确性指标，而不是 task-success 指标（`prior-art-agent-runtime.md:711-713`） | WirelessBench 独立在无线 agent 场景确立动机结果：**23% 的错误是 exact-match 指标看不见的灾难性失败**（`:712`、`:525`）；ReliabilityBench 给出正确性判据 **action metamorphic relations（end-state equivalence）** 与 R(k, ε, λ)；τ-bench 给出 pass^k（`:712`、`:304`） | 材料未给出风险评级；给出可落笔判断："The paper's §12 claim … **is exactly this gap, and it is defensible.**"（`:713`） | 需要一个把无线/灾害 agent benchmark 接到**终态副作用等价**的评测；材料明说"adopt ReliabilityBench's metamorphic end-state relations rather than inventing a metric"（`:713`）。命名候选：PALADIN 的 **"Catastrophic Success Rate"**（`:424-425`） |
| **A7** | **验证器自身不可用**：verify-before-retry 递归进它本要解决的问题（`:715-717`） | CRITIC 的未检验假设是"验证器从不失败"（`:342`、`:716`）；arXiv 2608.02645 的 postcondition verification 是对**会应答的单个工具**规定的，分区下 postcondition 检查自己就超时且结果未知（`:716`）。材料称没有正面命中把验证器自身可用性纳入故障模型（`:716`） | 材料未给"风险"字样；给出的是最高级定性判断：**"This is probably the paper's best single conceptual contribution."**（`:717`） | 材料称"cheap to state"（`:717`），把它从"加验证"变成**两难**（盲重试，或验证而可能验证失败），解法需要持久日志 + reconcile 机制；材料**未给出实验方案** |

### 表 1-B｜`agent-assumption-audit.md` 的 G1–G7（按「四判定问题」逐篇核对得出）

| # | Gap 一句话 | 支撑它的先行工作 | 材料给出的风险评级 | 需要什么实验才能证实 |
|---|---|---|---|---|
| **B1（G1）** | 通信中断**未被建模为 agent 观测与控制通道的固有属性**：网络侧 5 篇全部假定观测通道可用，`partition`/`disconnect` 命中数为 **0**；通用侧把网络层失败**显式排除**（`agent-assumption-audit.md:40`） | 全量词频扫描为 0（`:40`）；Q1/Q2 逐篇判定见 `:19-26` 表 | 材料未给出风险评级 | 需要把"链路中断"写进 agent 的前提假设而非环境背景；即 task 中观测能力必须随链路状态退化 |
| **B2（G2）** | **分钟至小时级的观测延迟无人处理**；现有最长延迟语义是最终一致副本（**秒级** Delayed Visibility）（`:41`） | Verified Tool Calls 的 Delayed Visibility（`:22`、`:41`）；bounded clock skew 工作（`:41`） | 材料未给出风险评级 | 需要把观测延迟的量级设到**分钟至小时**，而不是秒级最终一致 |
| **B3（G3）** | **超时后远端效果未知**：网络运维侧 **0 篇**；通用侧仅 Verified Tool Calls 一篇形式化（`:42`） | Q3 统计（`:42`）；Verified Tool Calls 的四类失败（Timeout-After-Dispatch / Delayed Visibility / Partial Success / Stale Conflicts）（`:22`） | 材料未给出风险评级 | 需要把 Q3 从"未处理"变成被测变量：注入超时并检验远端效果可知性 |
| **B4（G4）** | **幂等性与跨断连的操作生命周期**：网络运维侧 **0 篇**；operation identity / fencing token / reconcile 在 agent 文献中基本缺席（**`reconcile` 命中 0**）（`:43`） | Q3 统计（`:43`） | 材料未给出风险评级 | 需要跨断连的操作生命周期与幂等性成为 task 的可观测对象 |
| **B5（G5）** | **「观测通道 ≡ 控制通道」在检索覆盖的文献中无任何对应工作**；所有基准都默认存在一个**带外可用的观测接口**（`:44`） | 全量扫描：无一篇讨论 probe 本身穿过被评估链路（`:44`）。材料对它的评级原文：**"这是最干净的一条"**（`:44`） | 材料给出的评级即上句原文；结论段再次确认"**其中 G5 尤其干净**"（`:58`） | 需要 task 的结构本身满足：agent 的**唯一**观测通路就是承载其控制命令的同一条链路（无可带外探测接口）；材料对最强相关者的逐一排除见 `:54-56` |
| **B6（G6）** | **灾区/山地监测网络作为前提的 agent 工作缺失**；唯一沾边的是 DORA，但它评测**遥感地理空间推理**，不涉及链路存续或遥测延迟（`:45`） | DORA 全文（`:45`）、DORA 的 Q1/Q2 判定为"是"（`:25`） | 材料未给出风险评级 | 需要把灾区/山地监测网络写成 task 的前提，而不只是动机段 |
| **B7（G7）** | TopoLLM 全文核实已完成；**此项为证据补齐，不是研究空白**（`:46`） | 见 `:28` 与 `topollm-fulltext-completion-audit.md` | 材料明确它不是 gap | 不需要实验（材料原文：不是研究空白） |

材料对 G1–G7 的合并结论（可直接当作 task 设计的目标判据）：

- **"没有。"** 在检索覆盖的文献中，**没有任何一篇**同时把「链路频繁中断 + 观测延迟数十分钟至数小时 + 工具执行结果不可知」作为 agent 运行的前提假设（`agent-assumption-audit.md:50`）。
- 三个最强相关者各推进一步但未合流：WirelessOpsAgent（执行期授权，但陈旧来自更新速率与乱序，不是链路中断）、Verified Tool Calls（非原子执行与超时后效果未知，但通用客服/发票工作流）、DORA（在灾害域，但评地理空间推理）（`:54-56`）。
- 对 README 命题的判定：「agent 的观测通道与它的控制通道是同一条，'实体已静默'与'我的查询在回程丢了'在观测上不可区分」**在本文献范围内是未被占据的位置**（`:58`）。

### 表 1-C｜母论文材料与证据日志派生出的可主张项

| # | 可主张项一句话 | 支撑/差在哪 | 风险评级 | 需要的实验 |
|---|---|---|---|---|
| **C1** | **非原子工具语义的域迁移**：超时—结果未知 / 重复副作用问题已确立，但从未被实例化到**网络执行类工具**上，那里的副作用是**物理基础设施状态变化**，且"本应承载一次重试或一次 reconcile 的网络，本身就是失败的那个" | 问题已在 2608.02645、2608.01710、2603.20625 确立（`prior-art-mother-papers.md:233`） | 材料未给出风险评级 | 需要把工具换成**网络执行类**（改变远端设备/网络状态）并在链路自身失效的条件下评测 |
| **C2** | **退化—恢复链路上的 runtime contract**：跨分区的 durable intent ledger、显式 outcome-unknown 状态、exactly-once 效果施加、actuation authority 的 lease、reconcile 协议 | 现有无线 benchmark 是**故意把失败抽象掉**的：α³-Bench 声明 A2A "logically instantaneous"；6GAgentGym 自认 "does not capture full protocol-level transients, particularly during handover and failure recovery"（`prior-art-mother-papers.md:234`、`:58`） | 材料未给出风险评级 | 需要一个 runtime contract 及其在分区/恢复下的测量（材料称之为 "unclaimed territory"，`prior-art-mother-papers.md:234`） |
| **C3** | **评测方法学**：不存在带**注入式非原子工具故障**的无线 benchmark | 材料给的可组合配方：6GAgentGym 的 effect-typed 工具分类（obs/rea/cfg）+ 2608.02645 的注入 harness + 2608.03836 的 fault-matrix 方法学；且可直接坐在两个最可引的无线 artifact 上（α³-Bench 已发布 113k episodes 数据集、WirelessAgent++ 已发布代码）（`prior-art-mother-papers.md:235`） | 材料未给出风险评级 | 构造带 fault matrix 的 wirelss/disaster benchmark，并以已发布 artifact 为底料 |
| **C4** | 结论段把可防御贡献收窄为**三件事**：(1) 以真实 IODA/FEMA trace 为依据的**通信专用故障模型**；(2) 带能力生命周期、在间歇连通下的**应急通信 benchmark**；(3) **已发表无线 agent 基线在该 regime 下失败的实证**（`verified-evidence.md:296-299`） | 同文件 10a–10d 列出机制层在 2026 年被实时发表的四项威胁（`:261-293`） | 材料原文：**"The 'we add verify-before-retry with idempotency keys' claim is no longer available."**（`verified-evidence.md:277`）；**"the mechanism layer of this paper is being published in real time by other groups in 2026."**（`:296`） | 需要 (1)(2)(3) 同时成立；其中 (3) 明确要求**把已发表的无线 agent 基线跑在该 regime 下并展示其失败** |
| **C5** | 跨任务的**方法学发现**（可直接做成 benchmark-design 贡献，而非 nuisance parameter）：dwell/hysteresis 的 flapping↔missed-outage 权衡 | PoC：naive threshold 下 1026 次状态切换；PR/Fiona 真实 outage 仅约 25 分钟；dwell 600s→1800s→3600s 把转换数压到 73→14→5，同时抹掉全部 `disconnect` 事件（`verified-evidence.md:141-156`、`:202-220`） | 材料原文：**"This is the single most important methodological finding of the PoC."**（`:213`）；且"trace 选择决定 outage 是否存在"（`:202`、`7b` 显示 Helene 六州 **零 full disconnect**，`:190-200`） | 需要 (a) 不手调单一阈值、(b) 显式报告 flapping/missed-outage 权衡、(c) 用 IODA 异常打分序列或两时间尺度状态机（`:217-220`）；且必须报告**detection method 的选择会改变观测到的 outage**（PR 的 BGP 信号只掉 1.58%，与 ping-slash24 差异巨大，`:129-130`） |

### 表 1-D｜同域（金石组）已占 / 未占（`shijin-group-survey.md`）

| # | 结论一句话 | 位置 |
|---|---|---|
| **D1** | 该组已占**"agentic foundation model → network autonomy"**叙事与 agent-to-agent 语义传输原语；**缺失**的是把它接到 ISAC 感知载荷或灾害/监测任务上——材料原文称"that is genuine white space" | `shijin-group-survey.md:29` |
| **D2** | 该组**几乎没有**灾害/极端环境/山地部署工作：全文 300 篇语料中关键词仅 3 命中，且都不是该组的 ISAC 工作；唯一明确的灾后论文是 NTN 通信+计算资源协同，**仿真only** | `shijin-group-survey.md:73-77` |
| **D3** | 材料原文：**"There is no mountain deployment, no remote-site deployment, no disaster-field trial, no extreme-environment measurement paper from this group."** | `shijin-group-survey.md:79` |
| **D4** | 交汇点判断：(a) agentic/AI-native 编排栈、(b) 带真实雷达与 RIS 硬件的 ISAC 感知/成像能力、(c) 一项水文学味儿的野外感知结果、(d) 一篇灾后 NTN 仿真——**"Nobody in the group has yet joined (a) to (b) under a (d)-style mission."** | `shijin-group-survey.md:120` |
| **D5** | 该组的 SHM-ISAC 线**纯理论+数值**（全文本词频："testbed"/"field"/"prototype"/"bridge" 命中 0），材料明令 **"Do not describe this as validated."** | `shijin-group-survey.md:47` |
| **D6** | 材料未给出该组任何 agent runtime / 执行语义工作；`WirelessOpsAgent` 的 artifact URL 返回 HTTP 401，标 **UNVERIFIED** | `shijin-group-survey.md:92`、`:130` |

---

## 2. 母论文的 task 设计对照表

### 表 2-A｜六篇母论文（照抄其 task 构造范式用）

| 母论文 | 它研究什么 | 它的 task 怎么构造 | 它用什么指标 | 它怎么证明自己的方法有用 | 位置 |
|---|---|---|---|---|---|
| **TopoLLM**（Ma et al., *Digital Communications and Networks* 12 (2026) 273–282, DOI `10.1016/j.dcan.2025.10.002`） | 灾后救援通信拓扑规划：已知需求节点位置，确定 UAV 数量与位置，满足覆盖、连接与负载要求 | **合成数据 + 四个自研算法工具**：合成 **3,000 个问题实例**，三组规模 3–50 / 51–100 / 101–200；结构为 WOA / MUC / IMUC / REUC 四个算法框；自然语言参数解析 → 工具选择 → 调用算法 → 输出拓扑；Llama3-8B + LoRA（**全文未给清晰训练/测试比例**）。母论文材料写"evaluation is on **simulated disaster scenarios**" | 拓扑的"higher-accuracy and more robust"；全文含位置准确率（**其定义与覆盖率重合**）、Table 4 参数/工具/数量/位置评测、Table 5 异构带宽需求；**每配置 10 次试验并报告标准差** | **与成熟基线对照**：WOA、MUC、Greedy、GPT-3.5、GPT-4o、Ours（Tables 1–3）；再做**方法分解与扩展**（Table 4、Table 5）；两个 100 节点案例（分散 11 UAV + 4 中继；集中 11 UAV）。**注意：小规模结果里 MUC 比 Ours 更快，不能概括成全面领先**；其 7 图 5 表 4 算法框是"承载问题与证据的形式，不是我们必须照搬的数量目标" | `topollm-fulltext-completion-audit.md:5`, `:11`, `:13`, `:14`, `:15`, `:16`, `:17`, `:18`, `:20`；`prior-art-mother-papers.md:30` |
| **6GAgentGym**（arXiv:2603.29656，2026-03-31，**无期刊 venue、无 DOI**） | 6G 网络管理 agent 的**闭环交互环境 + 数据合成管线 + 训练配方**（动机："45% 的网络中断源于配置与变更管理失败"） | **学习式仿真后端 + 三档难度 + 五个评测域**：42 个带类型的工具按对网络状态的作用分成三个不相交集合（Observation 16 只读 / Reasoning 22 纯计算 / Configuration 4 状态变更）；工具执行打在**学习的 Experiment Model M_θ**（以 NS-3 数据标定）上，**不是在活网络上**（作者自述："does not capture full protocol-level transients, particularly during handover and failure recovery"）。难度 L1（≤3 步）/ L2（4–7 步）/ L3（≥8 步长时程多 agent）；五个域：网络切片、边缘卸载、UAV 控制、**退化恢复**、多 agent 协同。数据：3,000 条真实 NS-3 轨迹（seed 1–50）+ 50,000 合成（30,000 golden + 20,000 错误恢复增强）= 53,000；评测用不相交 seed 51–80，并对训练数据做 **ROUGE-L ≥0.7 泄漏过滤**；**任何模型 zero-shot 成功率 >80% 的任务被剔除** | 6GAgentBench 任务成功率（按 L1/L2/L3）；`R_format` 惩罚畸形工具调用（**格式有效性，不是失败语义**） | 评测 GPT-5、Claude-Sonnet-4、Gemini-2.5-Pro、Qwen3-VL-72B/8B/4B、DeepSeek-V3、Llama-4-Scout；微调 8B 的 `6GAgent-8B` 整体可比 GPT-5 且长时程占优。**四组消融**：闭环轨迹 +4.8%（对比开环）、错误恢复 +1.3%、NS-3 真实数据 +2.2%、agentic RL +4.8% | `prior-art-mother-papers.md:43`, `:48`, `:50`, `:51`, `:52`, `:54`, `:58` |
| **WirelessAgent**（*China Communications* 23(3) 265–285, 2026-03；另有 arXiv:2409.07964 / arXiv:2505.01074 共三条记录） | 面向智能无线网络的 LLM agent 框架（**概念 + 演示**） | 四模块（perception / memory / planning / action），外接知识库与工具；**task 构造 = 一个网络切片管理的 proof-of-concept case study**（意图理解、切片资源分配、维持最优性能）。**"Tool / execution semantics: Essentially none."** | 材料未给出指标 | **材料未给出**（原文：vision-plus-demo，无机制、无错误分类、无重试/超时/幂等讨论）；材料称其为好的**动机**引用，不是语义引用 | `prior-art-mother-papers.md:69`, `:74`, `:76` |
| **WirelessAgent++**（arXiv:2603.00501，2026-02-28，**尚无 venue**） | 把 **agent 设计重构为程序搜索**：agentic workflow 是可执行代码，由模块化 operator 组成，领域适配的 **MCTS** 搜索 operator 组合 | **三部分 benchmark（WirelessBench）**：WCHW（Wireless Communication Homework，知识推理）、WCNS（Network Slicing，代码增强工具使用）、WCMSA（Mobile Service Assurance，多步决策）；`Programmer` operator 有明确的 **3 次重试 / 每次 30s 超时**（**只作用于 workflow 内代码执行，不作用于网络/工具调用**）；ReAct `ToolAgent` 维护**连续失败计数 `n_fail`**（循环终止簿记）；mutation 去重是**搜索空间**去重，不是运行时副作用去重 | 三部分 test score：**78.37% / 90.95% / 97.07%**；搜索成本 **<$5 per task** | 对比 SOTA prompting 基线 **up to 31%** 提升，对比通用 workflow 优化器 **11.1%**；代码已发布 `github.com/jwentong/WirelessAgent-R2` | `prior-art-mother-papers.md:83`, `:87`, `:90`, `:91`, `:92`, `:96` |
| **α³-Bench**（arXiv:2601.03281，2026-01-01，**无 journal ref、无 DOI**） | LLM 驱动的 UAV 自主性，作为**动态 6G 条件下的多轮对话式推理与控制**问题 | **合成语料 + 固定评测子集**：113k 对话式 UAV episode（以 UAVBench 场景为底）；每回合注入 6G 网络状态向量 **n_t = (slice, latency, jitter, packet loss, throughput, edge load)**；退化规则显式——**lat_t > 40 ms 或 loss_t ≥ 1%** 时策略须从 *communication-safe* 动作子集 𝒜_adaptive(n_t) ⊂ 𝒜_total 中选（含"**buffering commands**"、推迟传感器激活）。观测"following a **deterministic execution logic augmented with controlled stochastic perturbations**"——**即网络状态是仿真的，不是 testbed、也不是 NS-3**。硬约束：schema 有效性、任务策略、**说话人交替**（r_t ≠ r_{t−1}）、安全 | 复合 **α³** 六支柱：Task Outcome、Safety Policy、**Tool Consistency**、Interaction Quality、**Network Robustness**、Communication Cost；另有效率归一化分数（per second / per 1k tokens）。评测 **每场景固定 50 个 episode、确定性解码、17 个 SOTA LLM** | 头条结果：多个前沿模型 Task Outcome 与 Safety Policy ≥ 0.95，但**Network Robustness 在退化 6G 条件下掉 30–40%**。**工具失败/超时/断连未建模**：工具确定性、A2A "logically instantaneous"；"retry" 只出现在 **episode 生成**（最多 3 次尝试，失败写为 **failure stubs** 以免生成失败率被乐观低估）；"Tool Consistency" 衡量协议/schema 一致性，**不是失败恢复**。数据集已发布 `github.com/maferrag/AlphaBench`（113k_episodes / Figures / Research Paper / Results_Evaluation / README，**GitHub 返回 license: null**） | `prior-art-mother-papers.md:102`, `:108`, `:110`, `:112`, `:114`, `:115`, `:118`, `:120`；`verified-evidence.md:227-241` |
| **ICG-Restore**（*AI* (MDPI) 7(8) 294, 2026-08-02, DOI `10.3390/ai7080294`） | 灾后应急通信恢复作为**高层约束规划**问题（服务优先级、对象间依赖、资源预算、时间窗），不是链路修复任务 | **受控抽象拓扑 + 三尺度四任务五演化模式**：自然语言请求 + 结构化网络观测 + 运行规则 → task-intent 对象；从异质场景图与恢复知识图谱检索；生成分阶段恢复候选；对违反前置/阶段序/预算/时序约束的候选做 **bounded local corrections（minimal-edit repair）**；在编码的高层约束模型下验证可行性；再在**抽象恢复动作空间**中用 safety-aware agent executor 排序。评测在**受控抽象拓扑**上，覆盖 3 个尺度、4 个恢复任务、5 个环境演化模式 | 对比 Direct-LLM：**CSR +1.99%**、**CRS +24.56%**、**WCTS@5 结构对齐 +38.87%** | 与 Direct-LLM 基线对照。**工具/执行语义：明确使用 "abstract executors or schedulers"**；"minimal-edit" 自称"a **descriptive label** for a bounded local repair principle"；其限制段自述 "the present evaluation focuses primarily on **offline high-level planning by a single planner**"；**无 timeout / retry / duplicate-side-effect / reconnect 证据** | `prior-art-mother-papers.md:130`, `:136`, `:138` |
| **ComAgent（i）**（arXiv:2601.19607，2026-01-27，**无 journal ref、无 DOI**） | 多 LLM agentic 框架，闭环 **Perception–Planning–Action–Reflection**，协调文献检索 / 编码 / 打分三类专用 agent，自动产出**可解的数学建模与可复现仿真** | **任务域 = 无线问题的数学建模 + 代码生成 + 仿真执行的闭环**；一条 **"Error handling branch"**：仿真编译/执行失败时 Scoring Agent 捕获错误信号（语法错误或运行时异常）回报 Coding Agent，后者自反思定位根因并在下一轮修正；另有 "wireless validity branch" 处理物理无意义结果 | 材料未给出具体指标（记为"evaluated on beamforming optimization (expert-comparable) and other wireless tasks"） | 与专家水平可比（beamforming optimization）。**全文词频：`timeout` 0、`retry` 0、`idempot` 0、`disconnect` 0；无仓库链接** | `prior-art-mother-papers.md:147`, `:151`, `:153` |
| **ComAgent（ii）**（JSAC 2026 教程，DOI `10.1109/JSAC.2026.3660010`） | LAM + Agentic AI 的长篇教程（planner / knowledge base / tools / memory；多 agent 的数据检索、协同规划与反思评估） | **无 task、无实验** | 材料未给出 | 材料未给出；且 `github.com/jiangfeibo/ComAgent`（35 stars）**全部内容只有 `README.md` + `fig/`，没有代码** | `prior-art-mother-papers.md:155-161` |
| **五篇综述 S1–S5** | S1 `arXiv:2607.16066`（5G/6G agentic 的教程与综述，Part I 含 reasoning/planning/tool use/多 agent 协同/**evaluation**）；S2 *ICT Express* 2026；S3 *IEEE COMST* 2026；S4 = ComAgent（ii）；S5 `arXiv:2605.15873`（把耦合组织为 "agents for communications" / "communications for agents"，**属架构/立场文章**） | 无 task | 材料未给出 | 无实验。材料对 S1 的评价：**"the single most on-point survey for the proposed paper's framing"**；S2、S3 **摘要未读，内容概要 UNVERIFIED** | `prior-art-mother-papers.md:171`, `:172`, `:173`, `:175` |

### 表 2-B｜补充：最近的执行语义侧先行工作，它们的 task 是怎么构造的（可照抄的方法学模板）

| 论文 | task 怎么构造 | 指标 | 证明方式 | 位置 |
|---|---|---|---|---|
| **Verified Tool Calls**（arXiv:2608.02645）| **受控仿真环境 + 注入的非原子故障**，跨多个 task 模板 | 重复动作数（"significantly reduces duplicate actions"）与任务成功率（"maintaining comparable task success"）；另在 `agent-assumption-audit.md` 中被记为四类失败：Timeout-After-Dispatch / Delayed Visibility / Partial Success / Stale Conflicts | 与"原子工具调用"基线对照 | `prior-art-mother-papers.md:206`；`verified-evidence.md:262-277`；`agent-assumption-audit.md:22` |
| **Beyond Single-Use Tokens / CapLease**（arXiv:2608.01710）| 覆盖 **replanning, retry, delegation, concurrency, confirmation-replay, crash-recovery** 六类场景 | 重复准入是否被阻止；"with an idempotent sink, duplicate external effects" | 逐场景对照 | `prior-art-mother-papers.md:209` |
| **Resume Means Resume**（arXiv:2608.03836，v1 08-04 / v3 08-08）| **六性质 RESUME CONTRACT + 39 格 fault matrix**；TLA+ 模型（7.4M states）与 TLAPS 证明（196 obligations）；实测 LangGraph 1.2.9 / CrewAI 1.15.2 / pydantic-graph 1.x | prefix continuation、effect exactly-once、fork determinism、checkpoint validity、consume-once、recovery determinism；"k processes resuming one parked interrupt firing the gated effect k times (saturation 1.0 in 36 of 40 cells)" | **机器可检验的契约 + 真实框架的 SUT 测量**；材料称这是"if the new paper wants to state and machine-check a runtime contract"的方法学模板 | `prior-art-mother-papers.md:211`（同段内容见 `:212`） |
| **Agent libOS**（arXiv:2606.03895，v1 06-02 / v3 08-18）| 运行时基底（persistent processes、Object Memory、Skills、syscall-mediated JIT tools、images/checkpoints、typed providers、budgets、durable recovery） | prepare-dispatch-settle 协议下"exposes ambiguity and prevents blind replay" | 系统实现 + 诚实列出边界（"or roll back irreversible external effects"） | `prior-art-mother-papers.md:215` |
| **ACRFence**（arXiv:2603.20625）| checkpoint-restore 场景下的语义回滚攻击（Action Replay / Authority Resurrection） | 重复支付、已消耗凭证被未授权复用等不可逆副作用 | 提出框架无关的缓解：记录不可逆工具效果 + replay-or-fork 语义 | `prior-art-mother-papers.md:218`；`prior-art-agent-runtime.md:376-379` |
| **ReliabilityBench**（arXiv:2601.06112）| **1,280 episodes、4 域**；chaos-engineering 式注入器，故障为 timeouts / rate limits / partial responses / schema drift | 统一可靠面 **R(k, ε, λ)**；**action metamorphic relations**（终态等价，非文本相似） | 扰动把成功率 96.9% → 88.1%；**rate limiting 是最具破坏性的故障**；ReAct 比 Reflexion 更稳 | `prior-art-agent-runtime.md:304-305` |
| **ToolMaze**（arXiv:2606.05806）| 二维设计：DAG 拓扑复杂度 × **2×2 工具扰动分类（explicit/implicit × transient/permanent）** | Perturbation Recovery Rate（PRR，implicit 语义失败下掉 ~37%） | 关键结果：**agentic 容错随模型规模改善的速度比基本任务执行慢 3.66×** | `prior-art-agent-runtime.md:299-300` |
| **AgentChaos**（arXiv:2608.06790）| **在 LLM API 的共享 HTTP 接口注入**，不改源码；定义 crash / omission / value 三类故障，并**验证每个故障确实被触发**；65 组故障配置 | pass@1（最多掉 **50 个百分点**）；故障类型诊断 <53%、故障步定位 <56% | 排名跨模型一致 → **鲁棒性取决于系统实现而非模型能力** | `prior-art-agent-runtime.md:308-310` |
| **Self-Healing Agentic Orchestrators**（arXiv:2606.01416）| **100-task fault-injection benchmark**；失败信号 → 失败类 → 在**显式预算**下选恢复动作 → 验证恢复轨迹 → 记录可观测 trace | 成功率；**recovery-budget sweep**；silent-failure 比例 | 98.8% vs 94.5%（retry-only）、93.8%（full replanning）；单次恢复尝试差距最大（94.0% vs 85.3%/88.2%）；verifier-guided self-healing 把 silent failure 降到 **0.0%** | `prior-art-agent-runtime.md:391-393` |
| **Rollback Is Not Undo**（**IEEE INFOCOM 2026**，DOI `10.1109/INFOCOM59046.2026.11571400`）| **在线闭环**：两个 LLM agent 提冲突动作、一个 LLM 仲裁者每轮执行单一决策；实例化为**多 LLM 边缘 DDoS 缓解任务**，注入真实瞬态故障模式（**observation corruption、delay/reordering、agent dropout、proposal corruption**） | 新提出 **post-rollback recovery metric: the recovery gap**（回滚后性能 vs 从未打过补丁的基线） | 即使回滚后协议文本完全一致，系统仍出现**持续退化**（路径依赖）；提出轻量缓解改善绝对回滚后成本，但相对 recovery gap 依旧存在 | `verified-evidence.md:303-333` |
| **评测统计纪律（方法学）** | 材料要求任何可靠性声明都要**重复运行 + 误差棒** | — | "Threshold Choice, Not Sample Size, Bounds Trustless Verification of Nondeterministic Compound AI Workflows"（arXiv 2609.10601）指出**决策阈值**而非样本量才是可验证性的绑定约束；配合 "On Randomness in Agentic Evals"（arXiv 2602.07150，把非确定性来源逐项编目为环境、harness、评测回路，而不只是采样温度） | `prior-art-agent-runtime.md:420-421`, `:349-352` |

### 表 2-C｜TopoLLM 全文审计给出的「完成链条」——task 设计必须补齐的七环

材料把 TopoLLM 的完成度逐环对照成"我们需要达到的对应完成度"，这是可照抄的 task 设计骨架（`topollm-fulltext-completion-audit.md:9-18`）：

| 环节 | TopoLLM 全文中的实际内容 | 材料要求的对应完成度 |
|---|---|---|
| 明确问题 | 灾后救援通信拓扑规划；已知需求节点位置，确定 UAV 数量与位置，满足覆盖/连接/负载；§3 第 2 页 | 明确**灾前监测任务、期限、设备能力和资源限制**；不能只给一组抽象工具调用 |
| 可计算模型 | 需求点坐标、UAV 坐标、覆盖半径、最大负载；几何覆盖与连通模型 | 采样事件、报文事件、接收窗口、电量和配置状态相互作用；**能从操作推到业务后果** |
| 可执行工具 | WOA、MUC、IMUC、REUC 四个算法框；第 3–5 页 | 四类监测接口**真正改变端侧状态或产生记录**，错误与回执有可审计路径 |
| 模型实际参与 | 自然语言参数解析、工具选择、调用算法、输出拓扑；Llama3-8B + LoRA，给出训练超参数；第 3–6 页 | **至少有一个真实 LLM 在部分可观测的监测工作流里决定实际参数及后续动作** |
| 数据与实验协议 | 合成 3,000 个问题实例，三组规模；说明训练/测试划分但未给比例；第 6 页 | 固定任务生成器、开发/测试隔离、**故障与场景分组**、配对复现 |
| 主比较 | WOA、MUC、Greedy、GPT-3.5、GPT-4o、Ours；每配置 10 次试验并报标准差 | 同资源的成熟设备管理、效果验证及本文 runtime；**报告配对不确定性** |
| 方法分解与扩展 | 参数/工具/数量/位置评测 Table 4；异构带宽需求 Table 5 | **执行机制消融、规划器 × runtime 因子实验、资源与失败类型分析** |
| 案例与边界 | 两个 100 节点案例；§5.5–6 第 8 页 | 两条完整灾前任务轨迹；**说明何时 runtime 有用、何时本地自治已足够、何时无物理路径** |

同文件另给两条免做项与一条纪律：不必先微调（主自变量是 runtime，可用冻结 LLM 保留 prompt/输出/动作轨迹）；不必先有野外试点（可完成"证据支持的场景建模 + 仿真 + 软件执行验证"，但若声称实测或成本节省则另需证据）；不必增加 UAV/HAPS 才像通信论文（通信约束可来自接入/回传共因失效、可接收机会、空口与能耗）（`topollm-fulltext-completion-audit.md:43-46`）。
可复现性纪律：**不应继承其报告不足**——全文未给清晰训练/测试比例、位置准确率的定义与覆盖率重合、无系统性去 LLM/去微调因子消融（`:48`）。

---

## 3. Venue 与要求

### 3.1 `venue-and-positioning.md` 的建议

| 层级 | venue | 材料给的理由 | 位置 |
|---|---|---|---|
| **首选** | **ACM SenSys 2027 第二轮**（摘要 **2026-10-29**、全文 **2026-11-05**），投 **Benchmarks / Tools** 类别；有真实应急通信评测则全论文 12 页，若核心贡献是执行语义 benchmark + 示范性 runtime 则短论文 6 页 | ① 贡献类型与 venue 匹配："An execution-semantics benchmark + runtime is a *systems* claim — 'does the runtime do what it says under failure injection?' — evaluated by reproducibility and artifact criteria"；② 应急场景在 scope 内（"systems for extreme environments"、"fault-tolerance, dependability, and robustness"、satellite/UAV 条目）；③ 双 deadline 模型是真实对冲（被拒后可实质性修改重投，附 ≤4 页 response）；④ 短论文明确"evaluated on originality, clarity, and potential impact, even without extensive evaluation" | `venue-and-positioning.md:306`, `:309`, `:310`, `:311` |
| **最高价值冲刺（仅当 artifact 已就绪）** | **USENIX NSDI '27 fall**（全文 **2026-09-17**；title/abstract 已于 **2026-09-10** 截止） | 更高声望、真实 artifact evaluation、**Frontiers Track** 专为 "bold ideas … challenging to evaluate in the traditional sense" 而设 | `venue-and-positioning.md:314`, `:113` |
| **安全高契合兜底** | **IEEE TNSM**（滚动、无截止日） | 编辑立场明确欢迎 "applied contributions (reporting on experiences and experiments with actual systems)"；**10 页免费且含参考文献**，可到 16 页——"the most permissive home for a benchmark + runtime + case study" | `venue-and-positioning.md:316`, `:92`, `:94`, `:95` |
| **第二兜底** | **IEEE TMC**（滚动） | 有直接先例：TMC 2026 发表了 MRLMN（LLM 驱动的 UAV 应急通信组网），编辑胃口可证 | `venue-and-positioning.md:316`, `:86` |
| **建议路线** | SenSys 2027（2026-11-05）为主 → 被拒即转 IEEE TNSM（滚动，扩写版加应急通信案例） → 并行把机制后续投向 **INFOCOM 2028**（~2027-07）的 "Agentic communication and networking" 主题 | — | `venue-and-positioning.md:327` |

**为什么通信会议在材料看来是较弱的主选**（`venue-and-positioning.md:318-325`）：ICC 2027（2026-10-02）与 WCNC 2027（2026-09-15）是**硬 6 页**上限，且这些 venue 的评审奖励"新通信机制或优化结果"而非失败分类学；INFOCOM 本轮已闭（2027 于 2026-07-31 截止），主线正文 ≤9 页（含图、表、附录，不含参考文献）对 benchmark 偏紧，且**无 artifact evaluation track**，若走该路线应规划为"用我们的 benchmark 展示一个具体应急网络机制"的**后续**；MobiCom/MobiSys 拟合度较弱（MobiSys 2027 日期全 TBA、无 benchmarks 类别；MobiCom 下一轮在 ~2027-03 且 TBD）；CoNEXT 按其自身 scope 规则出局；SIGCOMM 在文化上不适配；COMPASS 除非重构为弱势社区/可持续社会影响否则出局；**IPSN 已不存在，改投 SenSys**（`:325`、`:321-324`、`:127`）。

**材料对交汇点的判断**：**"Honest answer: today, no single family does. The two halves live in different communities, and that split is the opportunity."**（`venue-and-positioning.md:288`）；**"I found no paper that is simultaneously (1) an execution-semantics benchmark, (2) a runtime system, and (3) framed around wireless/emergency communication."**（`:298`）。两个让系统路线可行的信号：SenSys 2027 明确把 benchmarks/tools/frameworks 列为一等投稿类别；INFOCOM 2027 把 "Agentic communication and networking" 列为 topic，并配 "Fault tolerance, reliability, and survivability"（`:300-302`）。

### 3.2 `paper-strategy-review.md` 的另一套建议（与 3.1 的分工不同，材料未判定二者互相冲突）

- **主论文改投 TNSM**，明确承认"这是一次主动的 venue 降级，账要算清"；对照表给出：JSAC/TCOM 期望"新机制 + 明确优于所有基线"，TNSM 则明确欢迎诚实系统结论；篇幅上 TNSM **10 页免费**（含参考文献与作者照片）、最多 16 页；节奏上 TNSM **滚动投稿、无截止日**；"主要风险"两栏分别写 **"被读成'增量协议'"**（JSAC/TCOM）与 **"影响因子低于 JSAC"**（TNSM）（`paper-strategy-review.md:62-70`）。
- 若必须冲 JSAC，材料给的唯一可行路径是把机会约束做成主结果，叙事从"我们的协议多 0.58 个百分点"变成"**现有协议族撞到了 MAC 层的机会天花板，识别并绕开它是本文的贡献**"（`:72`）。
- **第二篇：SenSys 2027 的 Tools / Datasets / Benchmarks 短论文（≤6 页）**，并注明这与 `docs/s5-benchmark/README.md` 的决定不冲突——那里放弃的是"采用别人的 benchmark"，这里建议的是"把已经建好的环境发布出去，代价为零"（`:74-76`）。
- 投递前必做：**读完 α³-Bench（arXiv 2601.03281）**，确认 packet loss 是否真的作用到 tool call 上；"不读完，短论文与主论文的定位句都不能落笔"（`:78`）。

### 3.3 这些 venue 对 task 与实验的**明确要求**（材料逐条写出的约束）

**投稿形态类**

| 要求 | 数值/原文 | 位置 |
|---|---|---|
| SenSys 2027 篇幅 | 全论文 ≤ **12 页**；短论文（visions / experiences / **tools / datasets / benchmarks**）≤ **6 页**；参考文献不限页 + 可选附录（审稿人不必读附录）；两栏 9pt `acmart.cls`（sigconf 优先）；**双盲** | `venue-and-positioning.md:21` |
| SenSys 2027 类别 | 明确接受 "Visions, Experiences, Tools, Datasets, and Benchmarks"，含 "Benchmarks for evaluating systems, models, algorithms, or tools" 与 "Tools, toolkits, or frameworks"；短论文"即使没有大量评测，也按原创性、清晰度与潜在影响评估" | `venue-and-positioning.md:22` |
| SenSys 2027 出局项 | **"survey and tutorial papers are out of scope for SenSys 2027."** | `venue-and-positioning.md:26` |
| SenSys 2027 相关 topics | "Large language models for edge and embedded systems"、"Fault-tolerance, dependability, and robustness in embedded platforms"、"Systems for extreme environments (e.g., underwater, aerial, space)"、"Satellite systems and applications, including CubeSats" | `venue-and-positioning.md:25` |
| SenSys 2027 artifact | **CFP 未提及 artifact evaluation**；demo/poster 截止 2027-02-13；ACM 自 2026-01-01 起全面 OA | `venue-and-positioning.md:23`, `:27` |
| NSDI '27 | **12 页**（含脚注、图、表），参考文献与补充附录可另计；**Introduction ≤ 3 页**（prescreening 只读它）；有独立 Artifact Evaluation 委员会；**Frontiers Track** 面向"bold ideas with a high degree of novelty but may not have yet had a full evaluation"，明确是给"challenging to evaluate in the traditional sense"的工作，**不是**给早期工作；作者上限 8 篇 | `venue-and-positioning.md:112`, `:113`, `:114`, `:115` |
| TNSM | **10 页免费**（两栏，含标题、摘要、全部图/表/参考文献/作者照片）；超页 **US$220/页**，最多 **16 页**；学术无经费作者可申请免除（接受后 30 天内）；鼓励理论贡献**与** applied contributions；明确欢迎扩展会议论文（须真实扩展、换标题、引用会议版） | `venue-and-positioning.md:92`, `:93`, `:94` |
| TMC | 滚动、无截止日；页限 **UNVERIFIED**（IEEE CS 用 MOPC 政策，且"All page limits include abstracts, references, and author biographies"）；鼓励向 IEEE DataPort 存数据 | `venue-and-positioning.md:83-87` |
| INFOCOM 2027 | 最多 **10 印刷页**，其中**主线正文（含图、表、附录与一切非参考文献材料）≤ 9 页**；不合规不送审；个人最多 5 篇；**无 benchmark/tooling 类别、无 artifact evaluation**；相关 topics 含 "Agentic communication and networking"、"Fault tolerance, reliability, and survivability"、"Network observability/telemetry/monitoring"、"Challenging network environments"、"Testbeds, experimentations, and experimental platforms" | `venue-and-positioning.md:53`, `:54`, `:55`, `:56` |
| ICC 2027 / GLOBECOM / WCNC | **6 印刷页**（10pt）；GLOBECOM：超 6 页**不送审直接拒**，终稿可加 1 页 **US$100**；WCNC 同上但终稿最多加 2 页（每页 US$100）；ICC 2027 自身页限 **UNVERIFIED**（其 submission-guidelines 页面 404），6 页是 ComSoc 同族已核实的标准 | `venue-and-positioning.md:63`, `:70`, `:79` |
| CoNEXT | 按其 scope 规则出局："papers focusing on the wireless physical layer without considering the impact on the network … are out of scope"；AI 模型类贡献只有在给出"a critical and in-depth analysis of the advantages and disadvantages"且有明确 networking take-home 时才受欢迎；出版于 PACMNET | `venue-and-positioning.md:123` |
| COMPASS | 无严格页限（典型 ~7,000–8,000 词，<4,000 或 >12,000 词可能被 desk reject）；单栏 ACM、双盲（CHI relaxed anonymization）；拟合度要求围绕弱势/边缘人群与可持续社会影响 | `venue-and-positioning.md:134`, `:135` |

**对实验内容与 artifact 的隐含要求（材料写明的话）**

- SenSys 短论文路线成立的前提是"核心贡献是执行语义 benchmark + 示范性 runtime"（`venue-and-positioning.md:306`）。
- **"Caveat to respect: SenSys 2027 declares survey/tutorial papers out of scope. This must be a benchmark + runtime with real measurements and failure analysis, not a taxonomy paper."**（`venue-and-positioning.md:312`）。
- 材料要求：~8 周时间足够"build and freeze the artifact"（`venue-and-positioning.md:306`）——即投稿前 artifact 必须冻结。
- NSDI 路线的隐含门槛：title/abstract 注册已于 2026-09-10 截止，全文 5 天后到期，**"realistic only if the artifact already exists and was registered"**（`venue-and-positioning.md:314`）。
- TNSM 路线的隐含门槛：需要有"experiences and experiments with **actual systems**"的实测内容（`venue-and-positioning.md:316`）。
- 通信会议路线的隐含门槛：6 页放不下 benchmark + runtime + 评测，且评审奖励"new communication mechanism or optimisation result"；应只用于紧凑的 "first results"（`venue-and-positioning.md:319`）；INFOCOM 路线应规划为后续并用 benchmark 展示**具体应急网络机制**（`:320`）。
- 公开数据/代码的许可风险（工程要求，非投稿要求）：α³-Bench 仓库 **GitHub 返回 `license: null`**（无声明许可）——"must be clarified before redistribution; fine for internal experimentation"（`verified-evidence.md:230`, `:240-241`）。WirelessAgent++ 代码已发布、WirelessAgent 原版仓库只有 README、ComAgent 两个记录都无可运行代码、6GAgentGym 无代码无数据集、TopoLLM 未找到代码或数据集（`prior-art-mother-papers.md:34`, `:60`, `:78`, `:96`, `:161`；`prior-art-mother-papers.md:263`）。

---

## 4. 已被占据的机制清单（不能主张）

材料原文标题：**"# Mechanisms that are NOT novel"**；并称"the overlap is **larger** than §13's list of six … **None of these can be a contribution.**"（`prior-art-agent-runtime.md:651`, `:653`）。

| # | 被占据的机制（材料原文条目） | Owned by（材料原文） | 材料给出的状态原文 |
|---|---|---|---|
| 1 | **§10.1 operation state machine** / §9 lifecycle states | Saga (1987); Beldi/OSDI 2020; Temporal & Restate docs; IEEE 11638700 "Durable Execution for AI Agents" | **Not novel.** §13 already concedes. Note this is standard durable-execution design. |
| 2 | **§10.2 idempotency-aware retry** | Birrell & Nelson (1984); Helland, ACM Queue (2012); KIP-98; **arXiv 2608.02645 publishes it verbatim for agents** | **Not novel, and already published *for LLM agents*.** Highest-priority cite. |
| 3 | **§10.3 lease / lifecycle-aware capability registry** | Gray & Cheriton, *Leases* (1989); Chandra & Toueg (1996); φ-accrual detector (2004) | **Not novel.** Leases are the canonical mechanism; graded suspicion (φ) is the improvement to adopt. |
| 4 | **§10.4 bounded + fair replay** | Demers/Keshav/Shenker fair queueing (1989); Chandy & Lamport (1985); Elnozahy et al. survey (2002); MillWheel low watermarks (2013); **arXiv 2606.01416 recovery-budget sweep** | **Not novel** — both "bounded" and "fair" have canonical owners. |
| 5 | **§10.5 stale-state / freshness guard** | Terry et al. session guarantees (1994); **Age of Information** (Kaul et al. 2012); **arXiv 2606.01416 "stale context"**; **ACSOS 2026 verdict-staleness**; MCP FreshCtx proposal | **Not novel.** The AoI literature is the rigorous version. |
| 6 | **§10.6 reconcile / verify-before-retry** | **arXiv 2608.02645 (verify-before-retry + idempotency keys, for agents)**; **arXiv 2605.23311 DART (admissible restore points)**; **arXiv 2603.20625 ACRFence (replay-or-fork)**; CRITIC (ICLR 2024); arXiv 2605.12729 "recovery verification"; Kubernetes level-triggered reconciliation `[IND]` | **Not novel — this is the most occupied mechanism of the six.** |
| 7 | §3 `deadline` on ToolInvocation | AWS Builders' Library timeouts/retries/backoff; MCP SEP-1539 | Not novel. |
| 8 | §3 `idempotency_key` | Helland (2012); Stripe idempotency keys `[IND]` | Not novel. |
| 9 | §3 `heartbeat` / lease for online status | Chandra & Toueg; Gray & Cheriton; φ-accrual | Not novel. |
| 10 | §3 canonical session / event log / audit | Chandy & Lamport; Beldi; Temporal event history; DeltaBox (sandbox checkpoint/rollback) | Not novel. |
| 11 | §3 read-only vs **state-mutating vs side-effect tool separation** | **6GAgentGym (arXiv 2603.29656) already distinguishes read-only observation from state-mutating configuration** | **Not novel as a taxonomy** — only the *recovery semantics* bound to it can be claimed. |
| 12 | §3 `authority` / permission bound to actions | arXiv 2605.12729 privilege-level taxonomy; ACRFence "Authority Resurrection" | Not novel as a concept. |
| 13 | §9 `compensating` state, rollback | Garcia-Molina & Salem (1987); Azure Saga pattern; Elnozahy "output commit" | Not novel — and note compensation is *impossible* once output is committed. |
| 14 | §9 "retry budget exhausted" | Google SRE adaptive throttling / retry budgets; arXiv 2608.25403 Adaptive Retry Budgeting | Not novel. |
| 15 | §9 head-of-line blocking / starvation | Demers et al. fair queueing (1989); **Autellix (arXiv 2502.13965) already names head-of-line blocking in LLM agent serving** | **Not novel.** Autellix is the agent-specific citation. |
| 16 | §9 "long-running workflow, agent process / coordinator restart" | Candea & Fox crash-only software (2003); Gray & Lamport (2006); Temporal/DBOS | Not novel. |
| 17 | §9 "network partition → state divergence" | FLP (1985); Chandy & Lamport (1985); Bailis et al. HAT (2014) | Not novel. |
| 18 | §12 metrics（completion、recovery latency、duplicate side effects、stale decisions、starvation、progress/liveness） | τ-bench pass^k; ToolMaze PRR; ReliabilityBench R(k,ε,λ) + metamorphic relations; arXiv 2602.16666 12-metric framework | **Not novel as metrics.** Adopt existing ones. |
| 19 | **整体 framing**："agents should be treated as distributed systems / runtime semantics matter" | Waldo et al. (1994); **"Language Model Teams as Distributed Systems" (arXiv 2603.12229)**; **"Model or Harness?" (arXiv 2607.28802)**; **"Self-Healing Agentic Orchestrators" (arXiv 2606.01416)**; SAS uncertainty literature | **Not novel.** **This is the most important concession: the *thesis* is already stated in the literature.** |
| 20 | 「**fault injection into agents**」作为方法论 | ToolMaze, ReliabilityBench, AgentChaos, ChaosLLM, AgentDisruptBench, ToolMisuseBench, WAREX, OperAID, arXiv 2407.00125 survey | **Not novel, and a claim that "no one injects faults into agents" is FALSE and easily refuted.** |

**材料附在表末的明确警告（原文）**：

> **"Explicit warning to the authors."** Any sentence of the form *"we are the first to apply X to LLM agents"* for X ∈ {idempotency, verify-before-retry, retry budgets, checkpointing, staleness guards, fair scheduling} is refutable from citations in this document. So is *"no existing benchmark injects tool failures."*（`prior-art-agent-runtime.md:678`）

**同一清单在其他材料里的补充条目**（与上表重叠但不完全一致，一并摘出）：

| 已被占据的条目 | 材料原文 | 位置 |
|---|---|---|
| verify-before-retry + idempotency keys | **"The 'we add verify-before-retry with idempotency keys' claim is no longer available."** | `verified-evidence.md:277` |
| 机制层的整体时间窗 | **"the mechanism layer of this paper is being published in real time by other groups in 2026. The defensible contribution is now narrower"** | `verified-evidence.md:295-296` |
| 故障→恢复动作的映射 | Self-Healing Orchestrators 的 failure-class → recovery-action 表、SHIELDA 的 36 异常类型 / 12 artifact 分类；**"本文不声称首创该映射。"** | `agent-assumption-audit.md:34` |
| read-only / state-mutating 的区分 | 6GAgentGym 已用于学习；**"The paper cannot claim the read-only/state-mutating distinction as novel."** | `prior-art-agent-runtime.md:510`；母论文侧同判见 `prior-art-mother-papers.md:194`（7.2 表该行）与 `:50`（§2 正文） |
| 持久日志 / 幂等 / fencing 的新颖性边界 | TopoLLM 的工具组合**不改变**本项目在持久日志、幂等与 fencing 上的既有新颖性边界 | `topollm-fulltext-completion-audit.md:46` |

---

## 5. 必须引用但仓库里还没有全文的文献

### 5.1 材料明确给出「必读项仍缺 N/M」的那一份

原文：**"`docs/s3-novelty/prior-art-agent-runtime.md` 列的必读项中，本地已有 2 项（Verified Tool Calls、Self-Healing Orchestrators）。仍缺 4 项："**（`agent-assumption-audit.md:62`）→ **N = 4，M = 6**。

| # | 篇名（材料原文写法） | 标识 | 材料给出的补读理由（原文要点） | 位置 |
|---|---|---|---|---|
| 1 | **α³-Bench** | arXiv 2601.03281 | **"Gap 1 的最大风险项，必须补读。"** 需确认它是把 packet loss 作用到 **tool call** 上，还是只影响推理上下文；**"这个问题不解决，Gap 1 的表述就不能落笔。"** | `agent-assumption-audit.md:64` |
| 2 | **Atomix**（"Atomix: Timely, Transactional Tool Use for Reliable Agentic Workflows"） | arXiv 2602.14849 | 其 **"A.2 Fault Injection Details"** 附录 | `agent-assumption-audit.md:65` |
| 3 | **AgentChaos** + **AgentDisruptBench** | arXiv 2608.06790 / HuggingFace dataset | 用于构建**注入故障类的对照表**——"该表是 Related Work 的关键产物" | `agent-assumption-audit.md:66` |
| 4 | ***Rollback Is Not Undo: Path-Dependent Failures in LLM-Arbitrated Network Control*** | INFOCOM 2026, DOI `10.1109/INFOCOM59046.2026.11571400` | **IEEE 付费，需机构订阅** | `agent-assumption-audit.md:67` |

同一份必读清单在 `prior-art-agent-runtime.md:726-732` 以"最高信息价值优先"排序给出，共 6 项：① α³-Bench（确认 packet loss 是否改变 *tool call* 还是只改变 *reasoning context*）；② Rollback Is Not Undo（在本文自己的领域里已经走了多远）；③ Verified Tool Calls（范围与机制边界）；④ Atomix（A.2 Fault Injection Details 附录）；⑤ Self-Healing Agentic Orchestrators（budgeted recovery，避免重复推导）；⑥ AgentChaos + AgentDisruptBench datasheet（构建注入故障类对照表，"the table is the paper's key related-work artifact"）。

### 5.2 `prior-art-mother-papers.md` 的「未验证 / 需人工阅读」清单（10 条）

材料前置声明：**"Two of the six requested items could not be read in full text (TopoLLM — ScienceDirect bot-wall; ICG-Restore — MDPI bot-wall), and three IEEE Xplore items could not be opened at all."**（`prior-art-mother-papers.md:17`）

| # | 条目 | 状态与位置 |
|---|---|---|
| 1 | **TopoLLM 全文** | 原文：ScienceDirect 对 `curl` 与 headless Chromium 都返回 JS shell（"TopoLLM" 命中 **0**）；工具集（TopoTool 内部）、环境、失败语义与 artifact 可用性 **unknown**；"Highest-priority manual check (institutional access)"（`:242`，另见 `:36` "the single largest hole in this report"）。**后续已被关闭**：见 5.3 |
| 2 | **ICG-Restore 全文** | MDPI 返回 `Access Denied`；Data/Code Availability 声明与摘要以外的运行时细节 **unknown**（摘要、DOI、venue、卷期号、年份、作者、机构已核实）（`:243`） |
| 3 | **IEEE Xplore 三项** 11571400（*Rollback Is Not Undo*）、11638700（*Durable Execution for AI Agents*）、11661202（*DelAct*） | 原判：标题与 URL 仅经搜索结果列表核验，**作者、venue、年份与内容均 unverified**；**11571400 是最高优先的人工检查项**，因为其标题（`:244`）。**其中 2 项的"缺少身份"已被后续材料关闭**：见 5.3 |
| 4 | **6GAgentGym** | 无期刊 venue、无 DOI，是 preprint；三个 affiliation 字符串读自 HTML "Affiliation:" 标记，**作者→机构映射未核实**（`:245`） |
| 5 | **α³-Bench 作者机构** | arXiv 元数据无 affiliation，未核实；材料只看了 **v1**，未确认是否有后续版本（`:246`） |
| 6 | **综述 S2（*ICT Express*）与 S3（*IEEE COMST*）** | 元数据经 Crossref 核实，但**摘要未读**；一句话内容描述 unverified（`:247`；表在 `:172-173`） |
| 7 | **综述 S1（arXiv:2607.16066）** | 摘要已读；**是否有已发表 venue 未核实**（搜索结果指向 Eurecom 的 publication list，材料未打开）（`:248`） |
| 8 | **AlphaBench 数据集 README** | 未打开；harness/loader 可用性是从目录列表**假定**的，未确认（`:249`） |
| 9 | **Abhyasa**（"Custody Transfer of Governance Obligations over Unreliable Channels in Agent Networks"，Zenodo record 20644822，v1 2026-06-11 / v2 2026-08-09） | Zenodo 托管，**同行评审状态未知**（`:250`；正文见 `:226`） |
| 10 | **Graph-Based Self-Healing Tool Routing for Cost-Efficient LLM Agents**（arXiv 2603.01548） | 自述 "Working paper"，**未同行评审**（`:251`；正文见 `:228`） |

### 5.3 后续材料已关闭或部分关闭的缺口（同样属于「不能凭空补全」的清单）

| 条目 | 关闭到什么程度 | 位置 |
|---|---|---|
| **TopoLLM 全文** | **已通读用户提供的 PDF，可作全文级引用**；文件位于 `uploads/mobile-app/TopoLLM-main.pdf`；逐页证据与完成度对照见全文审计 | `topollm-fulltext-completion-audit.md:3`、`:28`（审计内页码指 PDF 页）；`agent-assumption-audit.md:28` |
| **IEEE 11661202** | 身份已补齐：**DelAct: A Replayable Boundary Runtime for Auditable and Governed LLM Agent Workflows**，Yuanbo Zhang / Hanlong Liao / Deke Guo / Guoming Tang，**IEEE/ACM IWQoS 2026**，DOI `10.1109/iwqos70441.2026.11661202`，2026-06（NUDT） | `verified-evidence.md:280-283` |
| **IEEE 11638700** | 身份已补齐：**Durable Execution for AI Agents: A Design Pattern for Fault-Tolerant Agent Loops**，Stenio De Lima Ferreira，**IEEE SmartCloud 2026**，DOI `10.1109/smartcloud69481.2026.00014`，2026-05。（材料只补了身份，**未给出已读全文的记录**） | `verified-evidence.md:286-287` |
| **IEEE 11571400** | 身份已补齐：**Weici Pan, Zhenhua Liu**，**IEEE INFOCOM 2026**，2026-05-18，DOI `10.1109/INFOCOM59046.2026.11571400`，DBLP `conf/infocom/PanL26`，CorpusId 289701645；**open access: CLOSED（abstract only; no PDF）** → **全文仍缺**，且被列为"decisive collision"，必须在 introduction 引用并显式区分 | `verified-evidence.md:303-345`（尤其 `:306-308`、`:344`） |
| **α³-Bench 全文** | **仍缺**：材料要求读全文以确认 packet loss 是否作用到 tool call；投递前必做，"不读完，短论文与主论文的定位句都不能落笔" | `agent-assumption-audit.md:64`；`paper-strategy-review.md:78`；`prior-art-agent-runtime.md:690` |
| **六个必读项中的其余 4 项（Atomix / AgentChaos / AgentDisruptBench / Rollback Is Not Undo）** | **仍缺**（见 5.1） | `agent-assumption-audit.md:62-67` |
| **ICG-Restore 全文** | **仍缺**（MDPI bot wall），无后续材料声明已读 | `prior-art-mother-papers.md:243` |
| 其他未读项 | 6GAgentGym 作者→机构映射、α³-Bench 机构与后续版本、S2/S3 摘要、S1 venue、AlphaBench README、Abhyasa 同行评审状态、arXiv 2603.01548 的自述 working paper 状态——**均无后续材料声明已读** | `prior-art-mother-papers.md:245-251` |

### 5.4 材料自己标为「引用前必须核验」的元数据风险（不是缺全文，但影响引用可防御性）

- 约三分之二的 2026 年引用是 **venue 未核实的 preprint**；`[FLAG]` 项有未决不确定性，特别点名 **TRACE 缩写碰撞、两个不同的 "AgentChaos" 项目、以及 "AgentFail" 究竟是论文还是数据集未能确定**（`prior-art-agent-runtime.md:734`）。
- 需要"核对后再引用"的纠正项：AgentTaxo 不是 failure taxonomy；**WirelessBench 的 "tolerance" 指打分容差而非网络容差（false alarm）**；API-Bank 的标题应为 "A **Comprehensive** Benchmark"；AgentChaos 指两个不同项目；Demers 等人的 fair queueing DOI 应为 `10.1145/75246.75248` / `10.1145/75247.75248`（`:742`）。
- 术语雷区："**outage**" 在 WirelessAgent++ 里是物理层 **fading outage probability**，不是连接中断，**不要引用该文来支撑"处理连接中断"**（`prior-art-mother-papers.md:94`, `:256`）；"**reliability**" 在 WAREX / τ-bench pass^k 语境下常指**重复运行稳定性**而非**容错**，必须先定义术语（`prior-art-agent-runtime.md:320`, `:733`）。
- 一个**名称歧义**（会直接影响 task 设计时的 baseline 引用）：材料把 `WirelessBench` 记为两处不同记录——`prior-art-mother-papers.md:87` 说 WirelessAgent++（arXiv:2603.00501）引入 WirelessBench（WCHW/WCNS/WCMSA，78.37/90.95/97.07）；`venue-and-positioning.md:174-178` 另列 **WirelessBench: A Tolerance-Aware LLM Agent Benchmark**（arXiv **2603.21251**，2026-03-22，venue unverified，WCHW 1,392 项 / WCNS 1,000 项 / WCMSA 1,000 项）；`prior-art-agent-runtime.md:525` 称后者是前者的 **"sibling benchmark"（同 WCHW/WCNS/WCMSA 三层）**。材料**未给出**二者是同一件工作还是两件工作的结论。
- `prior-art-mother-papers.md:261-263` 记录了"搜索为空、不必重复"的事项：GitHub 搜 `6GAgentGym` → **0 repositories**；TopoLLM（Crossref/DOAJ/abstract）、6GAgentGym、ComAgent（arXiv:2601.19607）、ICG-Restore（不可核实）均无代码或数据集链接。

---

## 6. 结论：材料里最干净、最可能守得住的那个 gap，以及它需要的 task 形状

材料给出评级最明确、且被两处独立确认的就是 **G5：「agent 的观测通道与它的控制通道是同一条」**——`agent-assumption-audit.md:44` 把它记为"所有基准都默认存在一个带外可用的观测接口"，并原文写下 **"这是最干净的一条"**；`:58` 再次确认在本文献范围内该命题"是未被占据的位置，**其中 G5 尤其干净**"。它的支撑结构是三重排除：网络运维侧 5 篇的 `partition`/`disconnect` 命中为 **0**（`:40`），通用侧的 Verified Tool Calls 虽形式化了"超时后效果未知"却在通用客服/发票工作流上、其通道假设是可靠网络（`:55`、`:33`），灾害域的 DORA 只评遥感地理空间推理（`:45`、`:56`）；而 `prior-art-agent-runtime.md:687` 与 `:693` 用两套独立的故障目录（传输层 vs. 工具 API 层；可见故障 vs. 结果不可知故障）从另一侧锁住了同一个位置，`:716-717` 的"验证器自身也不可用"则是它最锋利的理论形态。要守住它，task 的形状必须是：**agent 没有任何带外探测接口**——它关于远端实体是否还活着的**全部**证据都必须穿过承载它控制命令的同一条间歇链路，于是"实体已静默"与"我的查询在回程丢了"在观测上不可区分（`:44`、`:58`）；故障注入必须是**认识上不可得**的那一类（`prior-art-agent-runtime.md:695`），并按实测 trace 驱动而非合成（`:703`、`verified-evidence.md:296-299`）；判分必须落在**终态副作用等价**而不是任务成功率（`prior-art-agent-runtime.md:713`），因为材料已证明 exact-match 类指标会漏掉 23% 的灾难性失败（`:525`）；同时必须显式报告 trace 预处理里 flapping 与 missed-outage 的权衡，否则该 trace 上的真实 outage 会被自身的去抖滤波器抹掉（`verified-evidence.md:213-220`）；并且按材料要求，必读项中仍缺的 4 篇（α³-Bench、Atomix、AgentChaos+AgentDisruptBench、Rollback Is Not Undo）中的 α³-Bench 要**先读后落笔**，否则 Gap 1 的表述以及主论文/短论文的定位句都不能写（`agent-assumption-audit.md:64`、`paper-strategy-review.md:78`）。
