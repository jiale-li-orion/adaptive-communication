# Experiment Design v1：Evidence-Grounded Closed-Loop Agentic Communication

日期：2026-10-01<br>
状态：**当前实验设计 authority / design freeze candidate**<br>
作用：统一 benchmark task、data/evidence plane、Agent runtime、trace、metric、baseline、oracle 与 full-sim evaluation。后续实验基础设施默认实现本文，不再从旧 perception/repair probe 反向定义实验。

## 0. 术语冻结：两层 Task，不能再混用

本文以后只使用下面两层语义。

### 0.1 Operational Task：benchmark / 通信业务任务

Operational Task 回答：**在山区灾前监测场景里，这次系统到底要完成什么通信业务任务？**

它是 benchmark 层对象，来源于外部授权的监测要求、风险等级、目标节点/测项、任务时窗、数据新鲜度/交付要求与允许的资源约束。它不描述 LLM 内部推理过程，也不等同于一轮 prompt。

例：

```text
风险等级由外部系统从常态提升为黄色；
n02/n03/n04 在接下来 2 h 内进入 10 min 监测；
每个 monitoring obligation 要求在声明的窗口内采到有效样本并送达中心；
蜂窝主回传存在间歇中断；
系统可以使用已部署的 gateway backup / terminal-DtS / access assist，
但必须同时记录通信、能量和执行代价。
```

Operational Task 不负责判断“是否真的会发生滑坡”。风险与任务授权来自外部权威；本文研究通信执行。

### 0.2 Runtime TaskContract：Agent harness 一次运行实例

Runtime TaskContract 回答：**为了执行当前 Operational Task，Agent runtime 这一轮 TaskRun 需要达到什么 desired state、需要什么 evidence、允许什么 effect、何时完成/停止？**

Runtime TaskContract 使用本仓统一的程序语义：

```text
task_kind
target_resources
desired_state
evidence_contract
temporal_contract
effect_ceiling
completion_predicate
resource/scoring profile ref
policy revision
```

一个 Operational Task 可以生成多个 Runtime TaskRun。例如风险升级过程可以依次出现：配置安装、监测连续性、回传恢复、未确认执行收口等 TaskRun。

以后文档中的裸 `Task` 如可能歧义，必须显式写 `Operational Task` 或 `Runtime TaskContract`。

## 1. 论文问题与方法边界

场景固定为**电池/光伏供电的山区灾前地灾监测网络**：LoRaWAN Class A 类接入、现场 gateway、蜂窝主回传、北斗短报文/备用回传与 terminal-DtS 等受限能力；供电不足、接入中断、回传中断、睡眠/不可达和恢复均可发生。

论文研究两个连续的方法层。

### Method I — Physical/Data Plane → Evidence World

现有 simulator / 真实部署接口产生的是物理状态、通信事件、执行事件和原始记录。Agent 不直接读取 simulator truth，也不直接吃一份 flat telemetry dump。第一层方法把 data plane 组织成可审计 Evidence World：

```text
Physical/Data Plane
  node / battery / cache / config
  gateway receipt / queue / path state
  center delivery state
  primary / backup / DtS opportunity
  command submission / delivery / apply / confirmation
        ↓
Observation / Artifact
        ↓
Evidence object
  value / proposition
  subject
  source / provenance
  owner_location
  generated_at / observed_at / valid_at
  world_revision
  freshness / validity
  reachability / acquisition status
  confidence/status semantics
        ↓
Evidence World
```

核心 invariant：

```text
simulator truth != Agent evidence
UNREACHABLE != negative observation
TIMEOUT != not applied
STALE != current
NO ACK != not executed
CapabilityResult != durable fact automatically
raw output != Context automatically
```

这一层把 Evidence / provenance / state-integration 与通信侧的 owner、path、freshness、bytes、airtime、energy 与 contact opportunity 统一到同一 runtime contract。

### Method II — Operational Task → Task-conditioned Agent Runtime

第二层方法把 benchmark 业务任务编译成自包含 Agent Runtime，并持续从 Evidence World 构造当前决策所需 Context：

```text
Operational Task
        ↓ Task Compiler
Runtime TaskContract / TaskRun
        ↓
ContextManifest@0
        ↓ materialize
ModelRequest / deterministic planner
        ↓
EvidenceNeed / continuation
        ↓
CapabilityRequest
        ↓
CapabilityResult / Percept / StatePatch
        ↓
InvestigationState + Evidence World revision
        ↓
ContextManifest@1
        ↓
multi-round reasoning
        ↓
PolicyDecision
        ↓
communication-device capability
        ↓
Physical effect
        ↓
new Evidence
        ↓
Task completion / failure / continuation
```

LLM 只是这个 runtime 的一个 planner/consumer。Task、evidence、state、context、capability、effect 和 trace 都由 harness 持有确定性 authority。

### 1.3 Action-conditioned Context construction

当前 Method II 的方法主体进一步从“按 Task family 固定 EvidenceNeed / scope filter”推进为**围绕候选通信行动构造 Context**：

```text
Runtime TaskContract + legal Capability surface
        ↓
candidate communication plans
        ↓
passive task-outcome screening
        ↓
decision guards / candidate disagreement graph
        ↓
evidence dependency tracing
        ↓
contract Context when one ordinary action region is sufficient
OR
expand Context along shared gateway/access/peer dependencies
        ↓
optional owner-scoped evidence acquisition
        ↓
model / deterministic consumer chooses plan + arguments
```

算法遵循三条规则：

1. **action scope 与 evidence scope 分离**：允许修改单个节点时，Context 可以沿共享 gateway/access path 扩展到关联节点；action authority 保持原 TaskContract 范围。
2. **先用已持有证据筛候选**：center-local config/delivery evidence 先决定 fallback 是否仍有决策价值；共享/远端 evidence 只在候选仍存活时展开。
3. **任务与证据 revision 驱动局部更新**：候选 action、decision guard 或依赖发生变化时刷新相关 Context；近期 blocked/timeout acquisition 作为有时效 runtime information 保留，避免 telemetry churn 触发重复调查。

每个候选计划声明 `decision_guards`。当前 selector 对仍存活 candidate pair 计算 guard-family pair coverage，得到 symbolic candidate-disagreement signal；它用于排序后续 Context expansion / evidence acquisition，当前不冒充校准后的 VoI。真正 cost-weighted acquisition 等 latency/bytes/airtime/energy/opportunity cost 有 source-backed 或 simulator-authoritative 模型后再启用。

正式第一条 method probe 使用 localized O2，`action_conditioned` 与 `action_candidates_full_dump` 共享完全相同的 candidate-plan generation / deterministic reference consumer，仅隔离 evidence selector。结果由 `results/agentic/action-conditioned-context-localized-o2-v1/` 持有并经生成链进入 research/results 摘要。

### 1.4 A/B/C 的新地位

此前 A/B/C 不再承担整篇论文的主 framing，降为 Method II 内部机制和 ablation：

- **A — EvidenceNeed tracing**：从 Runtime TaskContract / current state 追溯还缺什么 evidence；
- **B — communication-constrained capability planning**：在 query / wait / act / fallback 中考虑 reachability、latency、bytes、energy 与机会；
- **C — context dependency invalidation / refresh**：Task/world/evidence revision 后局部刷新 ContextManifest。

它们可以分别做 deterministic implementation、LLM implementation、oracle replacement 和消融。

## 2. Benchmark Operational Task taxonomy

Benchmark 不需要制造很多互不相关的灾害题；共享同一个山区灾前监测系统，只改变业务任务与扰动。

### O1 Monitoring Continuity

在常态或给定监测等级下持续完成周期 monitoring obligations。

主要扰动：普通 packet loss、短时 access/backhaul degradation、节点睡眠。
主要通信结果：timely delivery、AoI/observation gap、energy、bytes。

### O2 Risk Escalation

外部权威提高风险等级，指定节点/测项需要更密采样和更短上报周期；Agent 负责将授权要求转换成通信执行并确认实际效果。

主要对象：configuration desired/reported/applied、Class A downlink opportunity、执行确认、额外采样能耗。
主要结果：configuration install latency、mismatch duration、升级后 monitoring coverage、energy survival。

### O3 Backhaul-Outage Sustainment

蜂窝主回传中断期间，维持灾前监测数据的及时/历史服务；允许使用既有 gateway backup、store-and-forward、terminal-DtS 等能力。

主要结果：timely delivery、historical completeness、backup traffic、DtS energy、censoring。

### O4 Energy-Constrained Monitoring

在 NASA POWER 派生采能或明确的低采能/遮挡条件下执行同一类监测任务。Agent 不能改变外部风险授权，只能选择已有合法通信/配置动作。

主要结果：task completion、node survival、residual energy、monitoring gaps、communication energy。

### O5 Recovery & Reconciliation

链路恢复后处理未确认配置、未回传记录、重复/陈旧动作与历史数据恢复。必须区分 requested / accepted / delivered / applied / confirmed。

主要结果：recovery latency、history recovery、semantic failure、duplicate/stale effect、unknown closure。

### O6 Compound Long-Horizon Operation

Operational Task revision、access/backhaul interruption、energy pressure 与恢复在同一 episode 中发生，用于测试多轮 Evidence World / Context evolution，而不是额外发明新的通信能力。

主要结果同时覆盖 communication outcome 与 Agent trajectory robustness。

### 2.7 Task 数据来源

Operational Task 分两级：

1. **Source-grounded task schedules**：来自现有公开山区/地灾监测资料、Task v1.1、设备可配置周期与公开事件片段；参数来源和 A/E/M 层级保持可追溯。
2. **Real-disaster-derived task schedules（transfer/secondary）**：未来可将 DORA/DisasterM3/Landslide4Sense 等真实灾害数据只用于上游 hazard/authority → task schedule，不把遥感数据伪装成通信链路数据。通信 Agent 接收授权后的 Operational Task，不负责遥感危险判定。

## 3. Data：source-grounded hybrid simulation benchmark

本文主 benchmark 不是纯 dataset replay，也不是纯手写 synthetic simulation，而是 **source-grounded hybrid simulation**。

### 3.1 Physical / exogenous data

当前直接复用：

- SRTM1：真实地形与 topology/coverage 构造；
- NASA POWER 2022/2023/2024 hourly irradiance + temperature：采能/温度外生输入；
- ChirpBox LoRa trace：拟合时间相关链路过程；
- 实测/来源派生的 device energy profile；
- Class A receive-window / 设备通信接口 / 北斗业务材料；
- frozen `spec/instance-v1-manifest.md` 的 14-node deployment 和 full-sim 参数。

数据集 URL、hash、许可和派生规则继续由 `spec/datasets.md` 与 `research/sources.json` 持有。

### 3.2 Simulator-generated benchmark data

给定 Operational Task、部署、seed 与外生 trace，full simulator 生成：

```text
physical world trajectory
raw observations/events
Evidence World revisions
available/reachable capability states
Runtime TaskRuns
Agent runtime trace
physical/business outcome
```

训练/开发/测试不得只按随机 seed 切分同一个 event fragment；优先按 source period / task schedule / outage regime / disaster-derived task source 分层。

## 4. Mathematical system model

设物理状态为

\[
x_t = (b_t, q_t, c_t, l_t, g_t, r_t, m_t, \ldots),
\]

其中分别表示节点能量、缓存/队列、已安装配置、access/link state、gateway/backhaul state、record/delivery state、mission/monitoring state 等。

外生输入

\[
\xi_t=(h_t,\theta_t,\gamma_t,o_t,\omega_t),
\]

包含采能/气温、无线随机过程、access/backhaul outage、Operational Task revision 和其它不由 Agent 控制的扰动。

Agent/普通控制器选择合法通信动作 \(a_t\)，系统按现有 full-sim 转移：

\[
x_{t+1}=F(x_t,a_t,\xi_t;\phi),
\]

其中 \(\phi\) 是冻结 deployment/device/protocol 参数。

Agent 不观察 \(x_t\)。data plane 只在某个 owner/location 产生 observation：

\[
z_t = H(x_{\le t}, a_{<t}, \xi_{\le t}, \ell_t),
\]

Evidence adapter 将 observation 编译为 typed evidence：

\[
e_i=(p_i,v_i,s_i,o_i,t_i^{gen},t_i^{obs},\rho_i,\nu_i,\sigma_i),
\]

其中 \(p_i\) 是 proposition/field，\(v_i\) 是值，\(s_i\) 是 source/provenance，\(o_i\) 是 owner，\(\rho_i\) 是 world/revision，\(\nu_i\) 是 validity/freshness，\(\sigma_i\) 是 acquisition/status semantics。

Evidence World：

\[
\mathcal E_t = \{e_i: t_i^{obs}\le t,\ e_i \text{ accepted by state gate}\}.
\]

Operational Task \(\tau\) 被编译成 Runtime TaskContract \(T_j\)：

\[
T_j = \Gamma(\tau, \mathcal E_t, \text{policy revision}),
\]

ContextManifest：

\[
C_t=M(T_j,S_t,\mathcal E_t,K_t),
\]

其中 \(S_t\) 是 InvestigationState，\(K_t\) 是当前 visible/reachable capability metadata。模型只看到 \(\mathrm{Materialize}(C_t)\)，而不是 \(x_t\) 或完整 \(\mathcal E_t\)。

Agent runtime 的一步输出可以是 evidence acquisition \(q_t\)、communication action \(a_t\)、wait 或 stop：

\[
(q_t,a_t,\delta S_t,stop_t)=\pi(T_j,C_t,K_t).
\]

Capability execution 经过实际通信路径，因此 observation 与 action 都受同一个物理系统影响；query/action 的 latency、bytes、airtime、energy 与 opportunity 进入同一账本。

## 5. Tool / Capability：统一 evidence use 与 communication device use

Tool / Capability 统一采用三层：

```text
CapabilityContract
        ↓
CapabilityBinding
        ↓
ToolImplementation
```

Agent 不直接依赖 Python method / MCP endpoint 名称。

### 5.1 Evidence-use capabilities

用于从 Evidence World 或合法 owner surface 取得/构造 Percept，例如：

```text
communication.gateway.receipt_summary
communication.gateway.primary_health
communication.center.delivery_status
communication.node.report
communication.satellite.visibility
evidence.retrieve_by_subject_window
evidence.compare_revision
evidence.aggregate_status
```

其中 generic evidence operation 直接复用本仓 `runtime_contracts.py` 与 Evidence World 的 canonical schema，不再创建同义协议。

### 5.2 Communication-device capabilities

直接改变 physical data plane：

```text
communication.config.set_sampling_interval
communication.config.set_report_period
communication.fallback.gateway_backup
communication.fallback.terminal_dts
communication.fallback.access_assist
wait / retry / local fallback where already implemented
```

两类 capability 共享 typed input/output、authority、owner/path、latency、failure、risk、bytes/airtime/energy 和 effect semantics。差别只在 `observation semantics` 与 `external side effect semantics`。

## 6. Benchmark episode schema

借鉴 DORA 的 \((\mathcal Q,\mathcal D,\mathcal T^*,\mathcal A^*)\) 设计，但扩展为动态闭环 episode：

\[
\mathcal B=(\tau,W_0,X,C_0,K,\Pi^*,Y^*,R),
\]

其中：

- \(\tau\)：Operational Task；
- \(W_0\)：evaluator-only 初始 WorldSnapshot；
- \(X\)：冻结 exogenous trace / seed coordinate；
- \(C_0\)：Agent 初始 ContextManifest；
- \(K\)：Capability catalog + binding revision；
- \(\Pi^*\)：reference/oracle trajectory 或 acceptable reference set；
- \(Y^*\)：reference physical outcome；
- \(R\)：source/replay/provenance coordinate。

推理时 Agent 只能看到 Operational Task 的授权视图、Runtime TaskContract、materialized context 与 visible capabilities；不能看到 evaluator-only WorldSnapshot 或未来 exogenous trace。

Gold/reference trajectory **不是唯一正确轨迹**。最终 physical/business outcome 是主评价，trajectory metric 用于 failure attribution。

## 7. Runtime trace：天然 benchmark measurement substrate

每个正式 run 至少保存：

```text
OperationalTask
TaskCompiler input/output
RuntimeTaskContract / TaskRun

WorldSnapshotRef / ExogenousTraceRef       # evaluator-only
EvidenceWorldRevision
InvestigationStateRevision

ContextManifest@k
MaterializedFragmentRefs@k
ModelRequest@k
ModelAttempt/Usage@k
ModelResponse@k

EvidenceNeed@k
CapabilityVisibility@k
CapabilityRequest@k
CapabilityResult@k
Percept@k
StatePatch@k

PolicyDecision@k
ActionRequest@k
ActionResult@k
PhysicalEffect@k

TaskCompletion / Failure / StopReason
PhysicalScore
```

这使 R0/R1/R2/R3 replay 可以从同一 trace 派生，而不是为 benchmark 另写一套日志。

## 8. Metric Contract：Communication × Agent 双层评测

### 8.1 Communication / physical outcome：论文主结果

禁止建立任意总加权分。主指标直接复用现有 scorer / runtime counter，并在需要时补全定义。

**Task service**

\[
\mathrm{TDR}=\frac{\#\{o:\ delivered(o)\land delivered\_at(o)\le deadline(o)\}}
{\#\{o:\ required(o)\}}
\]

- Timely Obligation Delivery Rate；
- Feasible-Obligation Delivery Rate：分母限制为物理上存在至少一次合法服务机会的 obligation，用于隔离不可避免物理失效；
- collected / delivered / missing / censored 分列；
- delivery latency p50/p90/p95；
- observation gap / AoI 分布；
- historical completeness / recovery latency。

**Configuration execution**

- desired-vs-applied mismatch duration；
- install latency；
- requested / accepted / delivered / applied / confirmed 各阶段成功率与时延；
- stale/duplicate/late effect。

**Energy/resource**

- node survival / residual energy / energy consumed；
- sampling energy / radio energy / DtS energy；
- backup packets / bytes；
- uplink/downlink/control airtime；
- access-assist/backup-boost duration and use。

所有通信指标都按 Task family、seed、node/segment 和物理可行性层次分列，不把 packet success 直接称 task success。

### 8.2 Agent / runtime metrics：解释为什么成功或失败

**Task compilation**

- Runtime TaskContract correctness / field validity；
- target/deadline/effect-ceiling grounding accuracy；
- completion predicate correctness。

**EvidenceNeed**

- required-need recall；
- unnecessary-need rate；
- invalid/unsupported need rate；
- stop correctness / over-investigation / premature stop。

**Capability use**

- capability selection recall/precision；
- capability order / normalized LCS（diagnostic）；
- argument grounding accuracy；
- owner/reachability correctness；
- stale / timeout / unreachable / negative-observation confusion matrix；
- calls / retries / redundant calls。

**Context**

- Context sufficiency：materialized context 是否包含支持最终 acceptable decision 所需的 evidence refs；
- Context redundancy：未参与 task/policy support 的 materialized refs / bytes；
- evidence-to-context inclusion recall；
- stale/invalid evidence inclusion；
- manifest revisions / materialized bytes / tokens。

**Policy / execution attribution**

- policy regret vs reference acceptable-action set；
- actuation request correctness；
- correct action but failed execution；
- evidence available but omitted；
- evidence present in prompt but unused/misused。

**Efficiency**

- model requests / attempts / tokens；
- evidence capability calls；
- communication-device capability calls；
- wall-clock/planner latency；
- physical query/action bytes, airtime, energy。

Efficiency 与 task outcome 画 Pareto/frontier，不压成单一 overall score。

## 9. Baseline registry

### Communication baselines

- existing local autonomy / local floor；
- standard expiry/store-and-forward；
- gateway backup / terminal-DtS / access assist ordinary combinations；
- existing deterministic policies in `code/instance` / `code/v3joint`；
- clairvoyant physical oracle/reference where already defined。

### Agent/context baselines

- FullDump：所有合法 center-visible telemetry/materialized state；
- candidate + FullDump：与 action-conditioned method 共享候选行动生成，只关闭 evidence selector，用于隔离 Context selection 本身；
- task-conditioned scope filter：按 Operational Task scope/family 的上一版 Context selector；
- fixed tool/capability order；
- diagnosis-first/full diagnosis；
- ordinary keyed join/compiler；
- generic ReAct；
- generic VoI / active-feature-style baseline where applicable；
- no-agent / fixed communication policy。

所有 baseline 共享同一设备能力、合法 information boundary、local autonomy 与 effect ceiling。

## 10. Oracle replacement / failure attribution

除了模型横向比较，正式实验必须做逐层 gold replacement：

```text
Full Agent
+ Gold Runtime TaskContract
+ Gold EvidenceNeed
+ Gold Capability selection
+ Gold Capability arguments
+ Gold CapabilityResult / Percept
+ Gold ContextManifest/materialization
+ Gold Policy
+ Physical Oracle
```

每层 replacement 都复用同一 episode 和下游 runtime，测 communication outcome 改善与 Agent diagnostic 改善。这直接定位 failure 在 task grounding、evidence construction、tool/capability use、context、policy 还是 physical execution。

## 11. DORA：直接借用什么、明确超过什么

R08 DORA 已验证的强设计值得复用：Operational Task taxonomy、typed tool I/O、expert/replayable reference trajectory、trajectory+final dual-level metrics、Parameter Accuracy、gold tool-order ablation、deterministic replay。DORA 515 tasks / 45 real events / 10 disaster types / 108 MCP tools / 3,500 tool-call steps，并把 final answer 作为 primary、trajectory 作为 diagnostic；这些是我们 benchmark construction 的直接参考。

我们的实验不以“比 DORA 多几个 tool”作为贡献，而针对它没有建模的闭环维度建立更严格环境：

| 维度 | DORA | 本文要求 |
|---|---|---|
| world | 预先给定 heterogeneous geospatial data manifest | Agent action 会改变 battery/cache/config/未来通信状态的 endogenous dynamic world |
| evidence | tool 对数据执行，结果主要由计算/感知工具返回 | evidence 有 owner、freshness、reachability、path、unknown/timeout/negative semantics |
| tool cost | 主要计 tool trajectory/efficiency | evidence query 与 device action 真实消耗 latency/bytes/airtime/energy/opportunity |
| action | 输出 operational answer/planning result | action 真正进入通信设备/网络并产生物理 effect |
| execution lifecycle | tool call → result | requested → accepted → delivered → applied → confirmed，可在任一段失败 |
| context | task data manifest + ReAct history | versioned Evidence World + InvestigationState + ContextManifest + materialization |
| task dynamics | 一个 task 的数据/trajectory | Operational Task revision 可在 episode 内改变 Runtime TaskRun 和 context |
| final evaluation | structured answer primary | physical monitoring outcome primary + Agent trace diagnostic |

DORA 本身已经显示 gold tool order 只提高最终准确率 1.08–4.40pp，证明 tool selection 之外 argument grounding/后续 composition 同样重要。本文因此必须保留逐层 oracle replacement，而不能只报 tool-call accuracy。

### DORA 数据的使用边界

DORA/xBD/DisasterM3/Landslide4Sense 等数据不替代通信 trace，因为它们不包含 node battery、gateway receipt、Class A opportunity、cache、command apply/confirm、backup/DtS state。它们若用于本文，只进入上游 `real disaster evidence -> external authority -> Operational Task schedule` transfer experiment。

## 12. Replay 与 result audit

Replay 统一分四层：

```text
R0 Protocol Replay
  固定 Task/Capability/State transitions；查 schema/invariant

R1 Frozen Model-Input Replay
  固定真正发给模型的 assembly，只换 consumer/model

R2 Frozen Context Replay
  固定 ContextManifest + WorldSnapshot coordinate，重跑 materializer/consumer

R3 Full Simulator Re-execution
  固定 Operational Task + exogenous seed/trace，重跑 runtime/policy/physical execution
```

每次 confirmatory run 保存：

```text
experiment_contract.json
run_manifest.json
source_manifest.json
code_revision.json
per_episode_results.jsonl
runtime_traces/
aggregate.json
audit.json
```

`audit.json` 至少检查：episode completeness、seed/task coverage、exception/retry、baseline success、oracle success、metric denominator、hidden-truth leakage、post-hoc exclusion、source/version、result hash。

## 13. 当前方法冻结后的实验顺序

通用 runtime / replay / metric / baseline 基础设施已经完成，真实模型开发阶段也已越过事件级 probe。当前工程顺序冻结为：

1. protocol-v6 formal main table：`localized O2 / O5 / O6 × seeds0..4 × {action-conditioned compact, task-conditioned, FullDump, generic-ReAct}`；
2. Method 15 rows 先通过预注册 gate：`effect_scope_inexact=0`、`extra observation=0`、`physical==candidate==legacy`；该 gate 当前已 `15/15 PASS`，剩余 45 baseline rows 正在同一 frozen source manifest 下运行；
3. 完整 60-row aggregate 通过后，先冻结 machine-checkable claim candidate，再决定是否进入 `results/CLAIMS.md`；
4. formal result 成立后做 full-episode component ablation，只解释 action-conditioned projection / plan-local dependency / decision sufficiency / semantic-state replanning 的因果贡献，不新增方法实体；
5. component ablation 之后再决定第二模型 confirmatory；
6. query-positive safety case、composed fallback closure、decision-equivalent Context compression 属于 coverage/cost extension，等待主结果与因果解释冻结后再开放。

当前不重新开放 automatic safe-action-prefix solver：在修正 global Task scope 后，ordinary backward slicing + current-state partial evaluation 已对 `453/453` runtime-unresolved dependency rows exact。只有未来 benchmark 出现该 ordinary compiler 不能重建的真实依赖缺口，才重新把 automatic dependency construction 升格为方法问题。

任何新增 capability、Task family、metric 或数据源都必须先补 source/contract，再进入 benchmark；不得因当前模型表现调整 task denominator、action space 或 metric definition。

## 14. Implementation status（2026-10-03）

本文已经不只是 design proposal。当前已落：

```text
OperationalTask / RuntimeTaskContract          DONE
EvidenceWorld adapter                          DONE (center surface first slice)
Capability registry/binding                    DONE (9 capabilities)
ContextManifest / PromptAssembly               DONE
Communication × Agent metric collector         DONE
R3 full-simulator re-execution                  DONE
R0 protocol audit                              DONE
R1 frozen PromptAssembly replay API            DONE
R2 exact context/materialization replay         DONE
result contract / source manifest / audit       DONE
paper/research artifact generation              DONE
Action-conditioned Context selector             DONE (pre-model method probe)
Candidate disagreement graph                    DONE (symbolic pair coverage)
Localized event-based real-model devset         DONE (4 pre-registered events)
DeepSeek Flash R3 full-episode model path        DONE
Global Task scope authority regression           DONE (O5/O6 seeds0..4 candidate == legacy)
Runtime candidate-plan selection/expansion       DONE (ordinary substrate)
Persistent semantic execution intent             DONE (ordinary substrate)
Semantic decision-state replanning               DONE
Compact shadow-only control projection           DONE
No-action decision sufficiency                    DONE (protocol v6)
Protocol-v6 Method 5-seed confirmatory gate      DONE (15/15 rows)
Protocol-v6 45 baseline confirmatory rows         RUNNING
```

当前 R3 实验入口：

```bash
python3 code/experiments/agentic/run_o2_risk_escalation.py --variant global --seeds 0,1,2,3,4
python3 code/experiments/agentic/run_o2_risk_escalation.py --variant localized --seeds 0,1,2,3,4
```

canonical result roots：

```text
results/agentic/o2-risk-escalation-v1/
results/agentic/o2-localized-risk-escalation-v1/
```

每条 Agentic trace 的正式 audit 同时要求：

```text
R3 physical signature == legacy reference
AND R0 protocol audit PASS
AND R2 PromptAssembly exact replay PASS
```

R1/R3 已接入真实 DeepSeek Flash backend；缺 endpoint/key 时仍硬失败，不回退 scripted backend。真实模型结果必须保留 `ModelRequest / ModelAttempt / ModelUsage / PlannerDecision` ledger，并以当前 protocol revision 与 source manifest 区分开发批次；旧 protocol / scope-bug 结果只保留作 diagnosis，不与当前 confirmatory 拼表。

结果到文档使用单向生成链：

```text
experiment runner
  -> aggregate.json / audit.json / replay_audit.json / source_manifest.json
  -> scripts/make_agentic_artifacts.py
  -> paper/generated/* + research/generated/*
  -> controlled blocks in research/README.md and results/README.md
```

`make tables ARGS=--check` 与 `code/experiments/audit_tables.py` 会检查结果和生成物是否漂移；公开叙事不再手抄实验数字。
