中文 | [English](README.md)

# 间歇连接下的智能体通信：基于真实来源的决策基准与未来选择上下文

> **当前研究结构：来源约束 Benchmark → Future-Choice Context / Decision-Semantic Compiler → Policy / Learning。** Layer 1 已在修正后的 `v0.2-retry-legality` 谱系上完成技术冻结：DB44/T 2457-2024 使用滑坡表 11，retry legality 允许“可能已经交付”后的合法重试，exact→V0–V9→结构化切分→public test 已重新生成。固定 universe 保持 58,752 个 recipes；V8 最终留下 **41 个 hard signatures / 174 个 pre-admission recipes**，冻结 public test 为 **3,804 cases**。Layer 1 现在是后续方法研究的可信底座，不再为制造方法 headroom 反向修改。正式 `BENCHMARK_ADMIT` 仍需完成 v0.2 的人工 source audit 与 release gate 刷新。

研究电池与光伏供电的山区地灾监测网：LoRaWAN Class A 节点接入现场网关，蜂窝主回传配北斗短报文备用；备用仅上行，控制下行会随主回传中断。任务与预警等级由外部授权，系统负责监测要求的通信执行。

**原始现实需求始终是一等约束。** 山区灾前长期监测面对供电不足和通信间歇中断，需要低功耗、低成本地维持有效感知与数据回传。仓库不能为了激活 Agent 或 learning 算法反向发明通信任务；新的 Task 必须从有来源支撑的 operational need 正向构造，并回到物理底座检验。

**共享通信底座：** 此前系统工作围绕控制路径失效后的持续通信状态，研究了源端期限释放、本地回退、分段执行证据、backup/DtS 与执行位置，并形成当前 simulator、信息边界、执行机制和结果台账。相关结论继续按 [CLAIMS](results/CLAIMS.md) 的范围成立，作为 Layer 1 / 2 / 3 共用的通信 substrate。

**原系统论文阶段（历史状态）：系统论文工作稿。** 这一阶段已经得到组件级正结果，并把配置租约、单节点停止、保留视界等候选收敛为 scoped-negative 边界；完整 runtime 增量、迁移验证与匹配能力 Agent 验证则留给后续阶段。该阶段的设计取舍、负结果和开放问题继续保存在 [论文闭环计划](paper/RESEARCH_PLAN.md) 与 [CLAIMS](results/CLAIMS.md) 中，作为研究谱系的一部分长期保留。

**当前研究主线：Benchmark 已进入研究冻结，方法主线转向 future-choice context。** 给定 operational obligations、合法 evidence、capability、剩余资源与 execution state，我们研究哪些动作仍能保持未来义务可完成，哪些缺失证据会改变这个集合，以及什么时候值得为取证支付真实通信成本。Policy / learning 只有在这个决策对象已经被清楚定义、可以由外部 oracle 检查之后才进入比较。

## 1. 当前论文、历史稿与权威入口

| 内容 | 入口 |
|---|---|
| 最新可构建 Agentic 稿件快照 | [英文 PDF](paper/agentic/en/main.pdf) · [LaTeX](paper/agentic/en/main.tex) · [workspace README](paper/agentic/README.md) |
| 系统论文兼容稿（持续接受 claim 纠错传播） | [英文](paper/en/main.tex) · [中文](paper/zh/main.tex) · [paper/README](paper/README.md) |
| Agentic 转向前系统稿不可变快照 | [paper/_archive/system-paper-2026-09-20](paper/_archive/system-paper-2026-09-20/README.md) · source commit `dd4f31a` |
| 当前研究控制面 | [research/README](research/README.md) · [Benchmark](research/benchmark/README.md) · [Compiler](research/compiler/README.md) · [Policy](research/policy/README.md) |
| 当前数学系统模型 | [SYSTEM-MODEL-v1](research/substrate/SYSTEM-MODEL-v1.md) |
| Runtime/domain ownership contract | [OWNERSHIP-v1](research/compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md) |
| 系统论文闭环计划（历史阶段） | [RESEARCH_PLAN](paper/RESEARCH_PLAN.md) |
| 逐主张复现 | [artifact/AE.md](artifact/AE.md) |
| 结果来源 / 主张状态 / 部署条件 | [结果登记](results/README.md) · [CLAIMS](results/CLAIMS.md) · [spec](spec/README.md) |

当前稿与旧稿形成一条连续谱系。`paper/en|zh` 保存系统阶段的最新纠错版本；`paper/_archive/system-paper-2026-09-20/` 保存 Agentic 转向前的确切源文件；`paper/agentic/` 是最新可构建的 Agentic 稿件快照。2026-10-04 的 benchmark-validity 复盘之后，它不再拥有全局研究方向。README 只维护当前 ownership；完整演化通过 Git、`results/history/`、`paper/_archive/` 与本地 research episodes 追溯。

## 2. 仓库 authority 与长期约束

这个仓库既是论文实现，也是证据系统。下面这些 authority 来自长期 README 历史、当前实验设计和 [论文仓库规范](tooling/paper-repository/PAPER-REPO-STANDARD.zh.md)，后续重构沿用同一 ownership：

| Authority / 约束 | 当前规则 |
|---|---|
| 主张真值 | `results/CLAIMS.md` 是唯一 claim-state authority；README 展示其当前投影 |
| 数字真值 | 实验数字由 `results/` 持有，经 `scripts/make_tables.py` / `scripts/make_agentic_artifacts.py` 生成论文事实与表格 |
| 场景与参数 | `spec/substrate/instance-v1-manifest.md`、`spec/substrate/datasets.md` 与 source registry 冻结部署、数据与来源，所有方法共享同一场景 |
| 数学模型 | `research/substrate/SYSTEM-MODEL-v1.md` 持有公开方程/系统模型；本地 `docs/` 保留推导过程，release 依赖全部位于 tracked tree |
| Runtime/domain ownership | `research/compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md` 冻结 canonical Task/Evidence/Context/Capability/physical-substrate 边界；平行 schema、hidden-truth shortcut 都属于 contract violation |
| Task authority | 风险等级、监测要求与 Operational Task 由外部 authority 给定；Agent 负责通信执行，业务义务分母由 scorer 独立持有 |
| Evidence boundary | node/gateway/center 只看到其合法 owner evidence；缺失、过期、不可达、负观测分开；simulator hidden truth 仅供 evaluator/oracle |
| Action / capability boundary | Capability registry 持有合法通信动作；新能力通过 source、authority、binding、cost 与 failure semantics 进入 action space |
| Baseline fairness | 普通 expiry、TTL、本地 guard、AoI/EnergyAware、EDF/maxcov、deterministic compiler 等成熟机制对所有方法公平开放；Agent 增量以超出强普通组合的可隔离效果为准 |
| 贡献判据 | task/evidence/tool/policy 语义增量或 physical/business outcome 增量承担论文贡献；统一对象、接口与 Context 结构承担系统工程价值 |
| 评价层次 | Communication outcome 是主结果；Task grounding、EvidenceNeed、tool selection/order/arguments、Context、model calls、latency 等承担 failure attribution |
| 模型结果 | scripted/deterministic consumer 负责基础设施与 reference；真实 backend run 负责模型效果 claim |
| 历史 | Git、`paper/_archive/`、`results/history/withdrawn/` 保存被取代的论文与结论，当前文档只维护当前语义 |

## 3. 系统底座：已收敛的技术与证据

**基本单位是监测义务及其执行状态。** 一条义务需要窗口内的合格样本，经 LoRa 到网关，再在期限内回传至中心。记录保留、配置生效、网关听到与中心完成分别记账。缺少某一段证据时保留 unknown。

**局部处置可以先于完整诊断。** 网关对「没采」和「采了但尚未听到」保留未知，源端则可凭已知期限停止过期记录重传；本地回退使用已有授权与自身电量直接执行。处置位置同时受证据可得、执行权限和剩余反应时间约束。

| 技术对象 | 当前证据支持什么 | 在论文中的作用 |
|---|---|---|
| 源端期限释放与跨段保留责任 | 标准 expiry 释放源缓存；仅在网关停发可能反压接入 | 主要系统正结果（C2/C3） |
| 配置回退的执行位置 | 本地普通保护能处理中心无法及时执行的降档；普通组合覆盖已测停止问题 | 位置原则与适用边界（C5/C6/C9） |
| 部分可观测的执行证据 | 合法在线归因覆盖可证义务，其余保持 unknown；接入、回传、完成分别保留独立证据 | 接口设计及 Agent 失效分析（C4/C7/C8） |

系统由成熟原语组成。新的系统价值通过组合、执行位置和实际业务后果来验证；模块统一、对象规范与 Agent 接口则承担工程复用价值。

## 4. Decision-Semantic Compiler 与当前 Conformance Suite

Decision-Semantic Compiler 继续使用同一个山区灾前监测 physical/data plane，把合法的 Task/Evidence/Capability/Execution 状态编译成模型可消费的 live decision surface：

```text
Physical/Data Plane
    -> Evidence World
    -> Operational Task
    -> Runtime TaskContract / TaskRun
    -> EvidenceNeed / InvestigationState
    -> ContextManifest / PromptAssembly
    -> evidence-use Capability / device-use Capability
    -> PlannerDecision
    -> existing communication simulator
    -> Communication metrics + Agent/runtime trace
```

**两层 Task 明确分开。** Operational Task 是 benchmark/业务语义，回答“这个山区监测系统现在要完成什么”；Runtime TaskContract 是一次 Agent harness 执行实例的程序语义，回答“本次 run 的 target、evidence contract、effect ceiling、temporal contract、completion predicate 是什么”。两层对象各自拥有稳定 schema 与 revision。

### 4.1 O1–O6 Conformance Catalog

当前 O1–O6 共用同一部署、通信能力与 scorer，只改变业务任务或受控扰动。**它们当前的角色是 conformance suite，而不是最终 Layer-1 decision benchmark。** 其中多项 Task 会收敛到唯一 supported plan；这对协议/runtime 验证有价值，但不足以支持 policy-learning claim。

| Task | 通信场景语义 | 主要评价对象 |
|---|---|---|
| O1 Monitoring Continuity | 常态/给定监测等级下持续完成周期义务 | timely delivery、AoI、energy、bytes |
| O2 Risk Escalation | 外部 authority 提高监测等级，要求更密采样/更短上报 | config install latency、mismatch duration、coverage、survival |
| O3 Backhaul-Outage Sustainment | 主回传中断期间维持监测回传 | delivery/recovery、backup cost、store-and-forward、DtS |
| O4 Energy-Constrained Monitoring | 低采能/低 SoC 下维持给定任务 | service-energy tradeoff、brownout、survival |
| O5 Recovery / Reconciliation | 回传恢复后收敛配置、缓存与执行状态 | recovery latency、duplicate/late traffic、config confirmation |
| O6 Mixed / scoped operations | 局部 target、owner/reachability 差异与组合扰动 | Context relevance、tool trajectory、physical outcome |

### 4.2 Evidence World 与 Context

Evidence World 把 node/gateway/center 的真实可观测信息组织为 typed、versioned evidence。每条 evidence 带 owner、source/provenance、observed time、revision、freshness/reachability 与 status；`CURRENT / STALE / NONE_RECENT / UNREACHABLE` 等语义分开。ContextManifest 保存 reference-preserving selection，FullDump 作为 baseline materializer。

当前 runtime 支持真正的多轮闭环：`Context@k -> evidence capability -> CapabilityResult/Percept -> Evidence World revision -> Context@k+1 -> device action/stop`。gateway-owner evidence 在路径不可达时返回 `UNREACHABLE`，负观测则使用独立 status 表达。

### 4.3 Capability surface

通信 domain registry 位于 [`research/compiler/COMMUNICATION-DOMAIN-REGISTRY.v0.1.json`](research/compiler/COMMUNICATION-DOMAIN-REGISTRY.v0.1.json)。当前正常 planner surface 已接通 3 个 observation capabilities 与 5 个 device capabilities；FullDump 单独保留为 baseline：

- evidence-use：gateway receipt summary、gateway primary-health、center node report；
- configuration device：set sampling interval、set report period；
- communication device：gateway backup、terminal-DtS、access-assist；
- baseline-only：center FullDump materializer。

device tool 直接复用既有物理模型。`gateway_backup` 作用于现有 `JointControlPlane`；terminal-DtS 使用既有 opportunity/energy/success profile；access-assist 使用原 simulator 的 window 与 duration/bypass 账本。Agent 经过 typed authority/schema/lifecycle gate 调用这些通信机制。

### 4.4 Trace、Replay 与 attribution

每次 run 形成完整 typed trace：TaskRun、Context revision、CapabilityRequest/Result、Percept、ModelRequest/Attempt/Usage、PlannerDecision 与 physical effect 均可重放。当前分四层：

- **R0 Protocol Replay**：Task → EvidenceNeed → Capability → State/Context → Policy；
- **R1 Frozen Model Input**：在同一 PromptAssembly 上比较 stopping、selection、order、arguments；
- **R2 Frozen Context Replay**：精确重建 Context/assembly hash；
- **R3 Full Simulator Re-execution**：把 policy/device effect 放回物理系统，测真正通信后果。

Gold replacement 已覆盖 upstream `Task / EvidenceNeed / Percept / Context` 与 planner `selection / order / arguments / policy`；attribution protocol 先用受控 corruption 自检，再用于未来真实模型 failure decomposition。

## 5. 当前可复现结果与 claim 投影

- **源端到期**：修正网关 deadline 边界后，标准逐记录 expiry 仍是所测缓存模型中受支持的跨段 placement 结果。具体 effect size 与 paired interval 只由冻结 result / 自动生成论文表持有，入口页不再复制数字。[C3 结果](results/communication-substrate/claims/r37e_full_seeds.json)
- **配置终止**：固定 TTL 在两个受检相位覆盖候选的存活与黄级交付工作点。候选能量门没有独立收益；单节点声明模型中的普通组合也追平所扫风险权重下的同信息精确停止参照。[配置矩阵](results/communication-substrate/claims/c5_matrix.json) · [序列参照](results/communication-substrate/claims/c5_seqref.json)
- **在线可知范围**：修正 deadline 边界后，网关合法证据支持“已判定部分正确、其余保持 unknown”的局部归因接口；精确数量/比例只由冻结 result / 自动生成论文表持有。[C7 结果](results/communication-substrate/claims/r40_local_attribution.json)
- **Agent 接口**：真实模型轨迹暴露了将 LoRa 接入收据当作回传状态的双向错误。v5 离线重放改善声明；独立的端到端机制增益尚未验证。[C8 入口](results/CLAIMS.md)

资源放宽实验用于说明容量与能源压力，不作为所有调度器的上界。C10 到期边界修正归入实现语义，后续比较使用修正后的普通 expiry。

下表是 [CLAIMS](results/CLAIMS.md) 的受检投影，不另行维护主张状态。

| 主张 | 范围 | 状态 |
|---|---|---|
| C1 | 资源放宽的反事实刻画 | scoped-negative |
| C2 | 与普通记录到期等价 | supported |
| C3 | 源端到期的跨段安置效果 | supported |
| C4 | 时间感知的失败归因 | supported |
| C5 | 已测配置租约候选 | scoped-negative |
| C6 | 本地执行位置 | supported |
| C7 | 部分在线归因 | supported |
| C8 | 真实 Agent 接口失效 | formative |
| C9 | 同信息单节点停止 | scoped-negative |
| C10 | 到期边界修正 | supported |
| C11 | 反向确认延迟界（条件性）；R1 关闭理由已撤回 | supported |
| A1 | Agentic runtime / physics conformance | supported |
| A2 | O2 deterministic Agent/runtime baseline isolation | supported |
| A3 | source-period 与五轴 robustness infrastructure | supported |
| A4 | source-derived Operational Task transfer | supported |
| A5 | attribution protocol self-check | supported |
| A6 | communication baseline / evaluator-only oracle substrate | supported |
| A7 | protocol-v6 DeepSeek Flash 五种子确认性模型结果 | supported |
| A8 | 同候选接口 WirelessOpsAgent-style 强对照 | supported |
| A9 | v7 held-out task/source/model transfer | supported |
| A10 | decision-conditioned evidence acquisition | supported |
| A11 | query-positive model transfer | supported |

`A*` 现在包含 deterministic / infrastructure 主张与窄范围的 A7–A11 model-effect 主张。A7 覆盖 query-negative 开发任务；A8 证明同接口 WirelessOpsAgent-style 可以追平可靠性，但 Method 总模型 token 少 35.804%；A9 覆盖 Qili/NASA POWER 2024 held-out task/source 与 DeepSeek/MiMo 双模型。A10 补上此前缺失的 query-positive 闭环：在一个 gateway-backup family 上，DeepSeek 五个种子都真实查询 blocking owner evidence，证据返回后闭合 plan feasibility、提交 backup，并相对 no-acquisition 改善 TDR/AoI。A11 在完全相同的 frozen 坐标上用 MiMo v2.6 Flash 重复该闭环，5/5 episode 直接保持 deterministic query-positive physical reference，并同样提升 TDR/AoI。A10/A11 支持一个 acquisition family 的双模型见证，不宣称全局最优或普适取证策略。

## 6. Agentic 论文冻结状态

pre-API 基础设施继续承担 deterministic/fairness substrate，但当前论文状态已经进入 A7–A11 正式冻结阶段：v6 五种子主表、同接口 WirelessOpsAgent-style 强对照、Qili/NASA-POWER-2024 held-out transfer，以及 DeepSeek Flash / MiMo v2.6 Flash 双模型 query-positive gateway-backup acquisition loop 均已有正式 claim。论文四张主表的 compact 数值 authority 为 `results/agentic/paper-v1/paper-results.json`；完整 claim ceiling 仍以 `results/CLAIMS.md` 为唯一 authority。

无需 API 的正式入口统一为 `make agentic-preapi`。该入口覆盖 catalog conformance、O2 global/localized、五臂 Agent baseline、传统通信 baseline、source-period、robustness、task transfer、attribution infrastructure 与 frozen model inputs，并在最后运行生成物/manifest/check。当前完整 repository gate 与 JointControlPlane anchor gate 均通过。

当前三种真实模型输入已经冻结在 `results/agentic/model-context-inputs-v1/`：task-conditioned、FullDump、generic-ReAct 共用同一 Operational Task、capability surface 与 paired physical reference。generic-ReAct 不暴露 EvidenceNeed / InvestigationState harness artifacts；这使后续模型比较能隔离 harness cognition，而不是把不同 tool surface 混在一起。

下一阶段是 paper freeze / writing / repository release，不再继续发散模型或 acquisition family。novelty 边界已收窄到 dynamic plan/dependency liveness、audit/control/model surface 分离、persistent semantic commitment、communication-constrained owner acquisition 与异步 physical execution/replay。decision-aware acquisition、action sufficiency、certificate/minimum witness、VoI/freshness 等均按 prior art 处理；frozen-input basis-selection headroom audit 没有发现真实 alternative-proof choice，因此该 side study 已终止。

## 7. 场景、物理模型与外推边界

部署、数据与参数以 [实例清单](spec/substrate/instance-v1-manifest.md) 为准。当前主点为十四节点、有限 Class A 接收窗口和稀疏短报文回传。Action space 包含已登记的采样/上报配置与通信能力；风险判断由外部 authority 提供，卫星/备份资源按 registry 与实例预算进入。模型采用同步中心 ACK、合成日照/云遮与主配置下的吸收态掉电，这些假设共同定义实装外推边界。

Episode I 研究升级任务、回传中断与恢复；Episode II 用两个授权升降级相位隔离配置回退。精确停止参照的适用域是公开任务表、声明能量过程和量化单节点状态；更大网络与新任务由后续 benchmark coordinate 单独验证。

当前主通信/能量模型包括 LoRa 接入、Class A 接收机会、蜂窝主回传、短报文备用、gateway backup、terminal-DtS、access-assist、节点缓存与 deadline expiry、采样/上报配置、太阳能/电池状态和 outage process。NASA POWER 小时辐照数据已经进入 source-period split；synthetic solar/heterogeneous harvest 用于受控研究条件。泥石流/滑坡流体或地质过程作为**上游 Operational Task generator**，其输出经过独立 hazard-model validation 后才能晋升为场景事实。

历史 README 中长期保留的一条纪律继续有效：**scenario source、研究选择、simulator-derived quantity 分开管理。** 公开规范/论文/厂商材料决定 source-backed facts；研究选择进入 experiment contract；simulator-derived quantity 进入 results。缺少公开证据的网络级共享配额、端到端 SLA、卫星额度等保持 `unknown`，等待新的 source 或 measurement 再进入 contract。

## 8. 构建与复现

```bash
make deps
make data
make check
make tables ARGS=--check
make agentic-preapi
make paper
```

最新可构建 Agentic 稿件快照与历史系统稿共享 [refs.bib](paper/refs.bib)。[构建说明](paper/README.md)列出三套稿件的角色和构建链。论文表格和事实宏由 `scripts/make_tables.py` / `scripts/make_agentic_artifacts.py` 从结果文件生成，`paper/generated/` 由生成链统一维护。

`make check` 包括仿真、执行语义、主张、表格、序列参照、Agent runtime 与联合层锚点。`make agentic-preapi` 重跑 credential-free Agent/communication substrate；A7–A11 live-model 结果单独冻结，并只向远端发布 compact aggregate/audit/result authority，不发布大型 raw trace。逐主张命令与冻结参考见 [artifact/AE.md](artifact/AE.md) 和 [results/reference](results/reference/README.md)。

## 9. 仓库结构

| 路径 | 内容 |
|---|---|
| `paper/agentic/` | 最新可构建 Agentic 稿件快照；不再承担全局研究控制面 |
| `paper/en/`、`paper/zh/` | 系统论文兼容稿；继续接收 claim 纠错传播 |
| `paper/_archive/` | 不可变论文/计划快照；包含 Agentic 转向前系统稿 |
| `research/substrate/` | 通信/world model 与长期系统语义 |
| `research/benchmark/` | Layer-1 benchmark validity、hardness、conformance split 与构造契约 |
| `research/compiler/` | Layer-2 Task/Evidence/Capability/Execution 语义与 Decision-Semantic Compiler |
| `research/policy/` | Layer-3 policy / baseline ownership |
| `spec/substrate/`、`spec/history/` | 当前部署/数据 authority 与历史 prereg contract |
| `code/substrate/` | 物理仿真、联合通信机制、校准与 substrate tests |
| `code/agentic_communication/` | Task/Evidence/Context/Capability/Planner/Replay runtime |
| `code/evaluation/` | 当前 Agentic evaluation、claim audit 与论文检查 |
| `code/legacy-communication/` | 为复现保留的历史通信方法 runner |
| `results/communication-substrate/` | 当前 C* 通信底座证据 |
| `results/agentic/` | A* 实验产物；研究角色由 `ROLE-MANIFEST.*` 索引 |
| `results/reference/`、`results/history/`、`results/legacy-communication/` | 冻结对照、撤回/历史与旧结果族 |
| `results/CLAIMS.md` | 唯一 claim-state ledger |
| `artifact/`、`scripts/` | 评审入口、依赖获取、结果到论文的生成链 |
| `tooling/` | 与研究 ownership 分离的可复用仓库/论文工具 |

## 10. 远端仓库与本地研究区

本仓库遵循 [论文仓库规范](tooling/paper-repository/PAPER-REPO-STANDARD.zh.md)：克隆可验证、数字单一来源、主张单一状态、历史可追溯。远端保留论文需要的实现、规范、compact frozen results、生成物和可审计 archive；大型 `runtime_trace.jsonl`、live-model per-run log、workspace-local `local_work/`、兼容入口 `docs/` 与 `local_experiments/` 留在本地/外部研究区，由 `.gitignore` 与 release tree 隔离。

本地研究区保存 Astra review、被杀候选、一次性 probe、网页快照和早期 paper sandbox。对象进入远端时经过四个 promotion gate：当前规范性依赖、稳定 owner、正式 runner/result registry 使用、`make check` 通过。满足 gate 的资产进入正式仓库，其余继续作为 provenance 留在本地研究区。

README 呈现**当前系统状态与长期 authority**。逐轮研究过程由 Git log 与 archive 追溯；当前 claim 状态统一从 `results/CLAIMS.md` 投影。
