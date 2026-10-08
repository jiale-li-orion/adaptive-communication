中文 | [English](README.md)

# 间歇连接下的智能体通信

面向山区灾前长期监测的 source-grounded 决策基准、决策语义运行时与 learning-guided exact search。场景长期存在供电受限、回传间歇中断、缓存压力和恢复过程；任务义务由外部来源定义，系统负责通信执行。

> **当前控制面：** Layer 1 当前保留 v0.2 scoped failure atlas、v0.6 可复现判废 lineage 与 v0.7 process-support correction，三者都不是 released benchmark。gateway-local autonomy 已冻结为 v0.7 主 placement；center remote control 继续保持 transport `SIMULATOR_GAP`。当前 36-cell gateway bounded pilot 中，已解析格没有 ordinary-baseline survivor，另有 8 格保持 computation unresolved。Layer 2 继续承担 deterministic/reference infrastructure，Layer 3 暂停。当前 ownership 统一由 [`research/`](research/README.md) 持有。

## 1. 架构总览

```text
外部 operational source / 原始现场需求
                    │
                    ▼
┌──────────────────────────────────────────────────────────────┐
│ Layer 1 · Source-grounded Emergency Communication Benchmark │
│ obligation · partial observation · action · transition      │
│ exact oracle · validity / hardness · frozen split            │
└──────────────────────────────┬───────────────────────────────┘
                               │ public task/evidence/action contract
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Layer 2 · Decision-Semantic Compiler                         │
│ Task / Evidence / Capability / Execution                    │
│ legality · evidence lifecycle · future-choice L/U frontier  │
│ conflict structure · incremental maintenance · exact fallback│
└──────────────────────────────┬───────────────────────────────┘
                               │ legal structured decision surface
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Layer 3 · Policy                                             │
│ deterministic / search / LLM / learned guidance             │
│ 当前状态：等待 Layer-1 placement / benchmark closure         │
└──────────────────────────────┬───────────────────────────────┘
                               │ selected communication action
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Shared Communication Substrate                              │
│ LoRa/Class-A · gateway · cellular · BeiDou backup · cache   │
│ battery/harvest · outage/recovery · execution · scorer      │
└──────────────────────────────────────────────────────────────┘

横切模块：evaluation · literature · result ledger · provenance
```

Layer 1 定义问题；Layer 2 持有 deterministic correctness 与合法 decision surface；Layer 3 持有该 surface 内的选择与搜索顺序；shared substrate 持有物理执行与 scorer。

| 模块 | 持有对象 | 当前状态 | 入口 |
|---|---|---|---|
| **Shared substrate** | 通信物理、能量、缓存、机会、fallback、执行生命周期、数学系统模型 | 稳定共享底座 | [`research/substrate/`](research/substrate/README.md) |
| **Layer 1 · Benchmark** | source-grounded obligations、task construction、observation/action/oracle contract、validity/hardness、split/release | **source/generation infrastructure ready；gateway placement frozen；dynamic hardness open；NOT_BENCHMARK_ADMIT** | [`research/benchmark/`](research/benchmark/README.md) |
| **Layer 2 · Compiler** | Task/Evidence/Capability/Execution 语义、L/U future-choice frontier、evidence lifecycle、incremental update、exact fallback | **v2 deterministic core frozen on dev** | [`research/compiler/`](research/compiler/README.md) |
| **Layer 3 · Policy** | 合法 / unresolved action 的排序与选择 | **paused**；learned-ranking v0.1 只保留为 negative/history | [`research/policy/`](research/policy/README.md) |
| **Evaluation** | replay、attribution、ablation、baseline fairness、跨层 audit | 横切 | [`research/evaluation/`](research/evaluation/README.md) |
| **Literature** | related work、source registry、claim boundary | 横切 | [`research/literature/`](research/literature/README.md) |
| **History** | superseded tracked research authority / roadmap | provenance | [`research/history/`](research/history/README.md) |

## 2. 原始问题与研究定位

项目始终围绕一个现实需求：山区灾前长期监测节点面临供电不足和通信链路间歇中断，节点可能失联、监测数据可能无法回传；系统需要在低功耗、低成本条件下维持可恢复、可持续的监测通信。

ASC / Agentic Communication Networks 提供决策层的外部学术坐标。仓库的研究顺序固定为：

```text
真实 operational need
→ 可追溯约束与能力
→ 物理通信环境
→ 合法 partial observation
→ 有真实成本的通信选择
→ obligation-feasibility causal transition
→ exact / executable evaluation
→ hardness
→ Agent / learning method
```

当前研究对象由五个核心 contract 组成：

1. **Source-grounded Operational Obligation**：现实需求要求系统完成什么。
2. **Action-relative Evidence Sufficiency**：当前合法证据是否足以支持一个具体通信动作。
3. **Heterogeneous Capability for Evidence Acquisition**：缺失事实通过真实 owner、路径和反馈能力怎样获得。
4. **Intermittent Long-Horizon Obligation Feasibility**：发送、等待、取证、回退如何改变未来义务的可完成性。
5. **External Oracle for Action / Completion Validity**：由独立可执行规则判定动作可行性和任务完成。

本项目里的 semantic object 是：**关于通信任务能否继续兑现、并会改变后续行动选择的信息。** 它的价值由任务、剩余资源、执行历史和未来选择共同决定。

Evidence acquisition 按 placement 解释，不把它强制成每个 case 的必要动作。Owner-local 事实保持本地状态，不为了制造信息差额重新按通信收费；只有真实存在合法 owner / transport contract 时，异构 remote acquisition 才进入评测。

## 3. Shared Communication Substrate 与系统模型谱系

Shared substrate 是仓库中历史最久、至今仍承担当前研究的技术层。三层 benchmark/compiler/policy 架构是在它之上长出来的；后续任何方法都必须面对同一套物理后果。

### 3.1 当前 substrate 是怎么建出来的

物理系统经历过两次关键升级。

**2026-09-13 · instance-v1 physical closure。** 一串连续 commit（`a68c01b` → `a827a82`）把早期轻量实例升级成可复现的多节点通信系统：外生过程与三时刻传递、有限缓存、动作驱动电量、SRTM 地形 + ITM 逐链路可达性、采集/交付分列、center-originated command 与回执、source-derived harvest、16 项 deployment manifest 和一致性检查。这一阶段同时建立了后续一直沿用的 E/A/M 纪律：来源事实、research operating-point choice、本项目模型/实现输出分开登记。

**2026-10-01–03 · current system-model rewrite。** 旧 system-model 仍保留 121×121 大网格和早期 execution-uncertainty framing。随后它被按冻结的 14-device full simulator 重写，并继续把 monitoring obligation、battery/cache dynamics、Class-A opportunity、backhaul/fallback、command lifecycle、partial observation、typed evidence 与 capability cost 一项项数学闭合。最终 authority 提升为 [`research/substrate/SYSTEM-MODEL-v1.md`](research/substrate/SYSTEM-MODEL-v1.md)。

cache04/05 阶段改变的是这些机制的**研究地位**。Persistent intent、async execution、plan expansion、ordinary dependency slicing、local fallback 等对象经过强 baseline 反复攻击后，被归入 shared substrate / compiler substrate。由此形成今天的实验边界：Layer 1 可以换 task，Layer 2 可以换 deterministic decision semantics，Layer 3 可以换 policy；三层始终面对同一个 physical world。

### 3.2 数学骨架

当前系统是 source-grounded hybrid simulator。核心方程把 Agent decision 一直连到最终监测通信结果。

一条 monitoring obligation 定义为：

\[
o=(i,m,r_o,[s_o,e_o],d_o),
\]

分别表示 node/measurand、release、合法 sampling window 和 center-delivery deadline。Timely delivery 从原始 obligation 集合计算：

\[
TDR(\pi)=\frac{\sum_{o\in\mathcal O}I_o^{succ}}{|\mathcal O|}.
\]

节点电量：

\[
B_{i,t+1}=\min\left\{B_i^{max},\left[B_{i,t}+H_{i,t}-E^{sense}_{i,t}-E^{UL}_{i,t}-E^{DL}_{i,t}-E^{DtS}_{i,t}-E^{other}_{i,t}\right]^+\right\}.
\]

Source-derived solar forcing 与 deployment scale 分开：

\[
H_{i,t}=\lambda_i\frac{G(t)}{G_{max}}\Delta t.
\]

Source cache 保留未确认记录，并显式处理 ACK、expiry 与有限容量：

\[
Q_{i,t+1}=Cap_{K_i}\left[(Q_{i,t}\setminus ACK_{i,t}\setminus EXP_{i,t})\cup S_{i,t}\right].
\]

LoRaWAN Class-A 的 control opportunity 由 uplink 触发：

\[
U_{i,t}=1\Rightarrow W^{RX1}_{i,t+\Delta_1}=1,\qquad W^{RX2}_{i,t+\Delta_2}=1.
\]

因此 center decision、gateway reachability、node receive opportunity 和 config applied 是不同事件。

全系统转移写为：

\[
x_{t+1}=F(x_t,a_t,\xi_t;\phi),
\]

其中 endogenous state 包含 battery、cache、config、link/execution、gateway 与 mission state；exogenous input 包含 harvest、temperature、stochastic link process、outage/access state 和 task revision。Agent 只看到合法 projection：

\[
z_t=H(x_{\le t},a_{<t},\xi_{\le t},\ell).
\]

Typed evidence 保存 proposition/value、provenance、owner、generation/observation time、revision、freshness 与 status。Evidence-use capability 与 device-control capability 共享统一 contract：

\[
\mathcal K=\mathcal K^E\cup\mathcal K^A,
\]

\[
k=(I_k,O_k,Owner_k,Path_k,L_k,Bytes_k,E_k,Authority_k,Failure_k,Effect_k).
\]

Device-changing capability 的 physical lifecycle：

```text
REQUESTED → ACCEPTED/REFUSED → DELIVERED → APPLIED → CONFIRMED
```

这条 lifecycle 后来直接成为 Evidence World、persistent commitment 和 Layer-2 future-choice semantics 的基础。

默认业务/物理结果按向量报告：

\[
J(\pi)=(TDR,Collection,Latency,Energy,Bytes,Airtime,Survival,Recovery,\ldots).
\]

Operational source 可以给 hard constraint 或 priority；统一 scalar objective 只在来源明确给出权重时成立。

### 3.3 各部分依据什么

| 模型部分 | Grounding / authority | 当前 claim scope |
|---|---|---|
| Terrain / spatial link feasibility | NASA SRTM1 + ITM point-to-point propagation | deployment-oriented spatial feasibility |
| Temporal LoRa variation | ChirpBox-derived two-state temporal process | temporal burstiness / stress distribution |
| LoRa/Class-A receive opportunity | LoRaWAN Class-A receive-window semantics + 当前 access configuration | 当前模型的 receive-opportunity contract |
| Solar / temperature forcing | NASA POWER hourly irradiance / T2M | forcing shape source-derived；panel/controller/harvest scale 由 deployment parameter 持有 |
| Sampling / radio energy | instance-v1 manifest + measured/declared device/radio profile | operating point 与 sensitivity axis 明确分层 |
| Monitoring cadence、cache/retransmission、warning/task semantics | 地灾标准、采购/现场材料、source registry | operational primitive / range grounding |
| Primary / backup / DtS / access assist | simulator capability + 对应工程来源 | declared-model path capability 与 cost |
| Numeric deployment point | [`spec/substrate/instance-v1-manifest.md`](spec/substrate/instance-v1-manifest.md) + code checks | 唯一 numeric authority |

频段/channel、名义 battery capacity、部分 uplink/backhaul probability、harvest scale、outage timing 和部分 backup limit 属于 **declared research operating point**。当前 substrate 面向 source-grounded communication research 与 controlled sensitivity；site-calibrated RF digital twin、dense LoRa MAC contention/capture、具体站点法规认证和 field-calibrated geotechnical parameter 属于更高一级 deployment evidence。

### 3.4 Optional hazard-to-task layer

Hazard physics 位于 communication Agent 上游。默认 benchmark 从 external authority 已经给出的 Operational Task 开始；secondary task generator 可以调用成熟外部模型：

\[
R(t),DEM,Soil\rightarrow Hydrology\rightarrow FS(t)\rightarrow ExternalAuthority\rightarrow OperationalTask.
\]

TRIGRS / infinite-slope 可生成 rainfall-induced pressure / stability trajectory，IMERG 可提供 rainfall forcing，Grfin 可生成 post-initiation runout/damage mask。D-Claw 级 two-phase debris-flow dynamics 需要独立 geotechnical calibration，因此保留给未来研究。

完整方程、implementation mapping 和 source boundary 见 [`research/substrate/SYSTEM-MODEL-v1.md`](research/substrate/SYSTEM-MODEL-v1.md)；模块谱系与 owner 规则见 [`research/substrate/README.md`](research/substrate/README.md)。

## 4. Layer 1 — Source-grounded Emergency Communication Benchmark

### 3.1 Source grounding 与 benchmark construction

现实来源定义合法问题空间；benchmark generator 在该空间内构造具有判别力的实例。

当前 corpus 包括 DZ/T 0450/0460、DB11/T 1677、DB44/T 2457、焦作 2024 地灾自动化监测采购、伊宁 2025 临灾预警制度、保山 1262 等监测标准与 operational material。它们提供 reporting cadence、缓存/补传要求、authority chain、通信优先序、设备状态读取和 warning delivery procedure 等真实 primitive。

变量 provenance 分为：

| Provenance | 作用 |
|---|---|
| `FIXED_BY_SOURCE` | 来源直接固定 |
| `SOURCE_RANGE` | 在来源支持范围内采样 |
| `EMPIRICAL_TRACE` / `MODEL_DERIVED_TRACE` | 测量或声明物理模型推导 |
| `CONTROLLED_STRESS` | benchmark 作者构造的受控压力，单独报告 |
| `UNRESOLVED` | source gap；answer-relevant 字段不进入生成 |

Construction pipeline 固定为：

```text
external operational corpus
→ canonical operational objects
→ Family Identity Test / taxonomy
→ source-profiled obligation contract
→ historical semantic dedupe
→ state / action / transition / oracle contract
→ simulator mapping / SIMULATOR_GAP
→ case generator
→ automatic validity / hardness filters
→ structure-aware split / scale-up
→ policy evaluation
```

Source 持有 task semantics、机制、authority、capability 与物理范围；generator 负责在 contract 内组合 warning timing、overlap、outage phase、resource headroom、evidence availability 等 challenge axis。

### 3.2 Operational taxonomy

Layer 1 目前只有两个一级 Family。Family Identity Test 看 protected operational subject、completion predicate、authority owner/chain、lifecycle scope。

- **T1 · Monitoring Information Continuity**：主 Family。常态监测、预警 cadence 变化、间歇回传、cache retention、恢复、异构路径和 energy pressure 都属于同一 monitoring-information lifecycle 的 regime。
- **T2 · Warning Delivery & Response Handoff**：扩展 Family。protected subject 与 authority chain 切换到预警授权、发布、层级送达、确认和 response handoff。Source contract 已存在，actor-chain simulator 仍处于 `SIMULATOR_GAP`。

T1 当前有八个 task surface：steady monitoring、warning cadence transition、intermittent backhaul/fallback、energy-constrained continuity、outage cache retention、recovery reconciliation、heterogeneous path priority、compound continuity。历史 O1–O6 继续作为 conformance / regression asset。

### 3.3 Decision semantics

Policy 只能使用已经合法到达 placement 的 observation history：

```text
h_t(w) = h_t(w')  =>  π(h_t(w)) = π(h_t(w'))
```

环境明确区分 local owner fact、passive telemetry/ACK、normal-send-as-probe、paid/remote query、`sampled_at` 与 `arrived_at`、gateway receipt 与 final center completion、历史事实与当前推断，以及无法提前查询的 future state。

核心动作包括 `WAIT`、terrestrial send、satellite/fallback send 和合法 evidence acquisition。Query、send、wait 共用一个 causal execution process：时间、机会、资源和在途执行同时推进，随后改变 completion state 和 future obligation feasibility。

### 3.4 EvidenceNeed 与 exact reference

EvidenceNeed 的判定围绕两个问题：兼容世界是否需要不同 commitment；合法取证是否能改善可实现策略。Passive telemetry、ACK 和 normal-send feedback 始终对普通 baseline 开放。

Layer 1 保留四个 reference：

- hindsight physical feasibility；
- full-current-state oracle；
- observation-matched exact oracle；
- observation-matched no-paid-query oracle。

逐世界都能完成、但不存在共同 non-anticipative policy 的 bundle 标为 `INFORMATION_INFEASIBLE`，与算法失败分开。

### 3.5 Validity、hardness 与 release

V0–V9 自动 gate 包括 source completeness、solvability、multiple legal options、common-safe-action、observation relevance、binding constraint、outcome separation、objective definition、shortcut audit 和 evaluator soundness。

典型 disposition 包括 conformance (`UNIQUE_READY`)、non-EvidenceNeed (`COMMON_SAFE_ACTION`)、source gap (`OBJECTIVE_AMBIGUOUS`)、environment gap (`SIMULATOR_GAP`)、shortcut-covered regression (`SHORTCUT_SOLVED`) 和 evaluator repair (`EVALUATOR_INVALID`)。

Hardness 来自真实信息与通信结构：observation sparsity、staleness、finite/non-nested opportunity、shared resource、deadline pressure、action irreversibility、overlapping obligation、recovery delay 与 long-horizon coupling。

强 baseline floor 包括 gateway-local EDF/reserve、passive-only、normal-send-as-probe、fixed/periodic/batch read、myopic VoI、shallow rule、true depth-k belief planning、receding-horizon planning、generic/incremental exact，以及 ordinary dependency/cache optimization。

### 3.6 当前 construction 与 admission 状态

当前保留三条 lineage，各自承担不同证据角色：

| Lineage | 已建立 | 尚未建立 |
|---|---|---|
| v0.2 | 一个 scoped H2×H3×H4 failure family 与 first-irreversible-commitment atlas | benchmark-wide mechanism coverage、pristine generalization |
| v0.6 | source/trace-driven generation 的可审计与 byte-level reproducibility | decision validity；1,262,790 variants 全部存在 blind public satellite-only policy |
| v0.7 | recovery/reinterruptible process-support 语义修正；candidate `TIGHT` 已消除 v0.6 的特定 satellite-only shortcut | placement-valid exact semantics、dynamic sufficiency、paid-evidence value、ordinary-baseline headroom、hard-case count |

本地 audited v0.7 pre-oracle universe 有 103,408 个 base scenarios，其中 74,952 个为 `ALL_WORLD_PHYSICAL`，展开成 2,023,704 variants / 863,460 pre-oracle structure IDs。这些数字只表示 generation coverage；当前 admitted hard case 数仍为 0。

当前 blocker 已定位到 oracle contract：旧 adapter 一边按 center-side remote query 收取 terrestrial opportunity/capacity，一边把 gateway receipt 免费暴露给同一 policy，并且没有 center send/control command transport。`cache06.md` 已冻结 owner 边界：gateway queue/send/receipt state 在 gateway 本地可读；center 只能使用已经到达的 telemetry 或合法 query。Gateway 与 center 必须分开建模，不能把两种语义混成一个 oracle。

当前 authority：

- [`research/benchmark/LAYER1-AUTHORITY.md`](research/benchmark/LAYER1-AUTHORITY.md)
- [`research/benchmark/GENERATION-AXES.v0.2.json`](research/benchmark/GENERATION-AXES.v0.2.json)
- [`research/benchmark/V07-PLACEMENT-VISIBILITY-REVIEW.v0.1.md`](research/benchmark/V07-PLACEMENT-VISIBILITY-REVIEW.v0.1.md)
- [`results/benchmark/layer1-v0.7-placement-visibility-review.json`](results/benchmark/layer1-v0.7-placement-visibility-review.json)

论文候选 benchmark 对比图、同类链接、construct coverage 与冻结 v0.2 数据分布由 Layer-1 模块自动生成：

- [Related benchmark landscape and links](research/benchmark/README.md#paper-facing-benchmark-landscape-and-statistics)
- [Layer-1 authority](research/benchmark/LAYER1-AUTHORITY.md)
- [Normative v0.2 contract](spec/benchmark/LAYER1-DECISION-BENCHMARK-v0.2.md)

## 5. Layer 2 — Decision-Semantic Compiler

Layer 2 将当前合法任务状态编译为结构化 decision surface：

```text
Operational obligations
+ lawful evidence history
+ capabilities / owner / transport
+ resources / opportunities / pending execution
        ↓
action legality and evidence validity
        ↓
future-choice feasibility surface
        ↓
L/U bounds + conditional frontier + exact fallback
```

核心研究问题是：

> 在间歇通信、有限资源和异步执行下，系统如何按任务需要主动取得、组合并维护现场证据，使关键通信决策获得足够的信息支持，同时保留任务的后续可行性？

一次 query 同时改变两部分状态：认知不确定性下降；时间和通信机会被消耗后，物理行动空间也可能缩小。因此 evidence value 由它改变的 feasible plans 定义。

v2 方法围绕 obligation、opportunity/resource、evidence 与 pending execution 维护 delivery-feasibility conflict structure。冲突见证来自交付约束；在依赖可安全局部化时，evidence / execution event 只使受影响区域失效和重算。

对 action `a` 维护：

```text
L_t(a) <= V*(h_t, a) <= U_t(a)

L_t(a) = 1   已有可执行 causal success certificate
U_t(a) = 0   声明的 relaxation 也无法保住成功
L=0,U=1      unresolved；继续取证、规划或进入 exact fallback
```

冻结 correctness boundary 包括五项：

1. non-anticipativity；
2. L/U bound reliability；
3. pruning preservation；
4. declared prefix scope 上 incremental 与 full rebuild 等价；
5. historical fact 与 current-inference validity 分离。

当前 v2 deterministic core 已在 dev 冻结。它已经证明 exact-frontier preservation，并通过 conflict-aware / incremental structure 显著减少 search expansion；对最轻 ordinary persistent-exact control 的 raw wall time 仍是公开 negative / open systems boundary。详细机器状态见 [`research/compiler/README.md`](research/compiler/README.md)。

## 6. Layer 3 — Policy 与 learning-guided exact search

Layer 3 只消费 Layer 2 输出的合法结构化 surface。当前 unresolved set 为：

```text
A_u(s) = { a | L(s,a)=0, U(s,a)=1 }
```

历史 v0.1 学习 exact search 的 action ordering。训练 preference 分两层：exact-feasible unresolved action 优先；同 feasibility 类别内 downstream exact proof/search cost 更低的 action 优先。

Learned model 只改变 unresolved-action exploration order。Legality、evidence truth、oracle semantics 和 hard pruning 继续由 deterministic layer 持有；ranking error 影响效率，exact fallback 维持 correctness contract。

v0.1 的 disposition 是：full-dev frontier correctness 保持一致；linear ranker 的 expansion reduction 很小；total wall time 劣于 ordinary persistent-exact control。该结果只保留为 negative/history。Layer 1 的 placement、mechanism coverage 与 pristine holdout 闭合前，不继续训练新的 Layer-3 policy，也不允许 Layer-3 结果反向塑造 generator。

详细状态与 machine artifact 见 [`research/policy/README.md`](research/policy/README.md) 和 [`results/agentic/README.md`](results/agentic/README.md)。

## 7. Evaluation 与三账

仓库分别记录三类成本：

1. **Task / communication outcome**：义务完成、deadline、资源可行性与真实 physical execution。
2. **Information / acquisition cost**：local evidence read、remote request/response、passive feedback 与明确建模的 transport cost。
3. **Planner computation**：构图、bound、flow/cut、memo、incremental update、exact fallback 与 model inference。

未标定的 bytes、airtime、energy 保持 unknown；动作次数不自动换算为物理通信成本。Gateway-local evidence 与 remote acquisition 分账；query 与 control 遵守各自 owner / transport contract。

方法最终要推进的是 task-quality / communication / computation frontier：在更紧的通信与在线计算预算下保留或扩大可完成任务区域，并保持声明范围内的 correctness。

长期论文目标由三部分组成：

- **结构发现**：找出哪些 evidence / resource / temporal coupling 真正改变 future feasible choices，同时明确 ordinary rule 的适用区间。
- **算法性质**：给出 evidence 复用、局部失效、停止取证与 exact global planning 重启的可靠条件。
- **系统结果**：在 source-grounded 山区监测 contract 下推进 task-quality / communication / computation frontier。


## 8. Related-work boundary

ASC / agentic-communication 近邻已经覆盖 task-aware semantic transmission、active probing、iterative information acquisition、context lifecycle、intent-to-workflow、memory reuse、dynamic pipeline reconfiguration、VoI send/no-send、world-model prediction、long-horizon physical consequence、counterfactual semantic value、freshness-aware value 和 online channel adaptation。

因此当前 claim 压在完整 decision contract 的组合上。最接近的 benchmark / system 分别占据不同位置：

- α³-Bench：interactive wireless-Agent control；
- 6G-Bench：standards-derived network reasoning 与 oracle decision；
- GenSC-6G：physical semantic-link evaluation；
- RAMSemCom：wireless cost 下的 active information acquisition；
- NetConfArena / WirelessOpsAgent-style systems：executable closed-loop network action 与 action assurance。

维护中的定性对比矩阵、paper link 和 repo audit link 见 [Layer-1 paper-facing benchmark section](research/benchmark/README.md#paper-facing-benchmark-landscape-and-statistics)。该图用于 claim-boundary 定位，不作为 leaderboard。

## 9. 项目演进：从通信系统到三层研究栈

当前三层架构来自多轮 validity audit 和 strong-baseline attack，并保留了早期系统研究的有效资产。

```text
Stage A · physical communication system
真实山区监测问题
→ terrain / energy / sampling / cache / access / backhaul / fallback
→ instance-v1 physical closure

Stage B · 第一次 benchmark-validity pivot
source / scenario / capability grounding
→ audit 发现初代 workload 缺少真实 decision freedom
→ 暂停 method claim，把 task validity 设成 gate

Stage C · typed Agentic runtime / compiler
Operational Task / Authority / Evidence / Capability / Execution
→ live plan–evidence relation
→ persistent commitment / async execution
→ A7–A11 mechanism evidence

Stage D · 第二次 benchmark-collapse
strong checklist / ordinary control 覆盖 decision-closed O1–O6
→ O1–O6 保留为 conformance / mechanism asset
→ benchmark legitimacy 与 communication-policy freedom 回到主线

Stage E · 当前架构
Layer 1 source-grounded decision benchmark
→ Layer 2 deterministic decision-semantic compiler
→ Layer 3 learnable/search policy
→ 共享同一 physical substrate
```

真正贯穿整个仓库的是 substrate。早期 systems work 留下 source-local expiry、local fallback、segment-specific execution evidence、finite cache、energy dynamics、opportunity-constrained control、store-and-forward、backup/DtS、persistent execution 和 physical scorer。后续研究重新分配了这些资产的 ownership：ordinary deterministic mechanism 下沉为共同底座，benchmark/compiler/policy 在它之上接受公平比较。

两次 benchmark collapse 也是当前研究方法的一部分。9 月第一代 task 因 desired state 基本预先已知，最终退化成“把一个已知配置写进节点”，因此主动暂停方法 claim。后来的 Agentic Runtime 阶段又出现 123/123 decision point 只有一个 ready supported plan，compiled checklist 可以复现 physical reference。这个历史直接催生了现在 Layer-1 的验收原则：Decision Benchmark 需要 real operational grounding、policy alternatives、partial evidence、resource conflict、temporal dependence 与 materially different physical outcomes。

因此当前三层架构延续了旧仓库：substrate 持有 physical truth；旧 conformance/mechanism 工作进入 regression evidence；Layer 1 持有 task legitimacy / hardness；Layer 2 持有 deterministic semantics；Layer 3 只接收剩余的真实 choice space。

## 10. 当前状态与已知边界

| Owner | 当前冻结 / 活跃边界 |
|---|---|
| Layer 1 | v0.6 保留为 reproducible negative lineage。v0.7 只修正 process-support 语义并通过特定 `TIGHT` satellite-shortcut preflight；exact admission 被 gateway/center placement、visibility 与 control transport contract 阻塞。当前没有 lineage 达到 `BENCHMARK_ADMIT`。 |
| Layer 2 | v1 保留为历史 runtime/compiler baseline。v2 deterministic future-choice semantics 完成 dev correctness 与强对照后冻结。 |
| Layer 3 | paused。历史 linear ranking baseline correctness 保持成立，但 search/wall-time gain 未出现；它不再驱动当前研究方向。 |
| Generalization | 历史 7-signature test 已在早期 Layer-2 工作中暴露，当前归入 regression evidence；新的 structural-generalization claim 需要 preregistered holdout。 |
| Deployment claim | benchmark guarantee 只覆盖声明模型 / process。site-level reliability、bytes/airtime/energy 节省与跨站点泛化需要独立 measurement / calibration。 |

机器结果进入 [`results/`](results/README.md)，claim state 进入 [`results/CLAIMS.md`](results/CLAIMS.md)。论文数字遵循 `result → generator → generated artifact` 单一生成链；根 README 与模块 prose 只投影 authority。

## 11. Authority map

| Authority | Owner |
|---|---|
| 当前 research ownership | [`research/README.md`](research/README.md) |
| Layer-1 方向与 disposition | [`research/benchmark/LAYER1-AUTHORITY.md`](research/benchmark/LAYER1-AUTHORITY.md) |
| Layer-1 normative environment / action / oracle contract | [`spec/benchmark/LAYER1-DECISION-BENCHMARK-v0.2.md`](spec/benchmark/LAYER1-DECISION-BENCHMARK-v0.2.md) |
| Runtime/domain semantics | [`research/compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md`](research/compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md) |
| 数学 system model | [`research/substrate/SYSTEM-MODEL-v1.md`](research/substrate/SYSTEM-MODEL-v1.md) |
| Deployment / data parameter | [`spec/substrate/`](spec/substrate/) |
| Claim truth | [`results/CLAIMS.md`](results/CLAIMS.md) |
| Result ownership | [`results/README.md`](results/README.md) |
| Reviewer reproduction | [`artifact/AE.md`](artifact/AE.md) |

## 12. 仓库结构

```text
adaptive-communication/
├── research/                  当前 research ownership 与语义
│   ├── substrate/             shared communication/world model
│   ├── benchmark/             Layer 1
│   ├── compiler/              Layer 2
│   ├── policy/                Layer 3
│   ├── evaluation/            cross-layer evaluation contract
│   ├── literature/            related work / source registry
│   └── history/               superseded tracked research authority
│
├── spec/                      normative contract 与 deployment/data spec
│   ├── benchmark/
│   ├── substrate/
│   └── history/
│
├── code/
│   ├── substrate/             physical simulator 与 substrate tests
│   ├── agentic_communication/ typed runtime objects
│   ├── evaluation/            Layer-1/2/3 runner 与 audit
│   └── legacy-communication/  可复现历史实现
│
├── results/
│   ├── benchmark/             Layer-1 frozen evidence
│   ├── agentic/               Layer-2 / Layer-3 evidence 与历史 A* asset
│   ├── communication-substrate/
│   ├── reference/             frozen comparator
│   ├── history/               withdrawn / superseded result record
│   └── legacy-communication/
│
├── paper/                     manuscript lineage 与 generated paper artifact
├── artifact/                  reviewer / reproduction 入口
├── scripts/                   result-to-paper 与仓库生成脚本
├── tooling/                   可复用论文 / 仓库工具
├── archive/                   tracked historical executable bundle，路径冻结
├── data/                      `make data` 获取/生成的 workspace data
├── libs/                      `make deps` 获取的本地依赖
└── local_research/            本地 current / lineage / episodes / archive 与重资产 provenance
```

`docs/` 与 `local_experiments/` 是 workspace compatibility symlink，实际指向 `local_research/archive/compat/`。新研究材料进入明确 owner 模块或 local research 四区。

## 13. 构建与检查

```bash
make deps
make data
make check
make tables ARGS=--check
make agentic-preapi
make paper
```

`make check` 已包含 Layer-1 paper asset drift check。Benchmark 图和统计由 `scripts/make_layer1_paper_figures.py` 从 frozen `results/benchmark` artifacts 自动生成。

## 14. 论文与历史

- 当前可构建 Agentic 稿件：[`paper/agentic/`](paper/agentic/README.md)
- 系统稿兼容副本：[`paper/en/`](paper/en/)、[`paper/zh/`](paper/zh/)
- 不可变稿件历史：[`paper/_archive/`](paper/_archive/)
- 当前 claim ledger：[`results/CLAIMS.md`](results/CLAIMS.md)
- 本地 research lineage / episode：workspace-only `local_research/README.md`
- tracked 历史可执行 bundle：[`archive/`](archive/README.md)

Git 保存逐轮修改历史；各模块 README 维护当前 ownership 与当前状态。
