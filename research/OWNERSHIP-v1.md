# Agentic Communication：Runtime / Domain Ownership

状态：**当前公开 Implementation Contract / v1**
更新：2026-10-03

本文件由作者本地 `docs/Agentic-Communication-后续研究Ownership.md` 的 2026-10-01 implementation contract 提升到远端 `research/`。当前代码 owner、capability registry、trace/replay 与 acceptance 以本文件 + `code/agentic_communication/` + `research/COMMUNICATION-DOMAIN-REGISTRY.v0.1.json` 为准；本地旧稿只保留 provenance。

## 1. 两层 Task

**Operational Task** 是 benchmark / communication-business semantics：描述目标节点/测项、监测阶段、release/window/deadline、授权 effect 和 scoring profile。

**Runtime TaskContract / TaskRun** 是 Agent Runtime 的程序语义：`desired_state / evidence_contract / temporal_contract / effect_ceiling / completion_predicate` 决定本轮运行实例需要什么 evidence、允许做什么、何时完成。

一个 Operational Task 可以产生多个 TaskRun。两层对象不能混用。

Runtime TaskContract 在同一 TaskRun 内是不可变 contract；`now/tick` 属于 runtime execution/context coordinate，不得在 contract ID/revision 不变时偷偷改变 contract 内容。

Task target authority 与 evidence availability 必须分离：

```text
OperationalTask.target_node_ids 非空
    -> 显式 target subset

global monitoring-network Task
    -> Runtime 合法 resource inventory / deployment scope

node report 是否存在、是否 stale、是否 reachable
    -> 只改变 matched / mismatched / unknown evidence state
    -> 不得静默缩窄 Task scope
```

`resource_inventory` 是 Runtime 已合法持有的部署资源，不等于 simulator hidden truth。

## 2. Canonical runtime ownership

本仓公开 runtime contract 的唯一代码 owner：

`code/agentic_communication/runtime_contracts.py`

它拥有：

```text
TaskContract / TaskRun
EvidenceNeed / InvestigationState
CapabilityContract / CapabilityBinding
CapabilityRequest / CapabilityResult
Percept
ContextManifest
MaterializedFragment / PromptAssembly
```

Operational Task、Communication Evidence、ExperimentSpec 与 RuntimeTraceEvent 由 `code/agentic_communication/contracts.py` 持有。

任何新模块必须引用这些 canonical types，不得再创建同义 `CommTask / CommPercept / CommContext` 平行协议。

## 3. Evidence World ownership

`code/agentic_communication/evidence_world.py` 只接收合法 observation surface，不接收 simulator hidden state。

每条 evidence 至少保留：

```text
proposition / subject_ref / value
source_id / source_role / provenance
owner_location
generated_at / observed_at
world_revision
freshness semantics
status semantics
```

固定 invariant：

```text
UNREACHABLE != NONE_RECENT
TIMEOUT != negative observation
STALE != current
NO ACK != not applied
CapabilityResult != durable fact automatically
simulator truth != Agent evidence
```

Evidence World revision 只在事实内容改变时增加。时间流逝本身不自激生成 revision；age/AoI 在 materialization 或 freshness check 时计算。

## 4. Context ownership

Context 是 reference-preserving runtime object，不是 transcript 或 telemetry dump。

```text
ContextManifest
  task_contract_ref
  investigation_state_ref
  evidence_refs
  capability_refs
  policy/budget refs
  world_revision
        ↓
Context materialization
        ↓
MaterializedFragment[]
        ↓
PromptAssembly / deterministic planner input
```

FullDump 作为 baseline。当前方法使用 action-conditioned compact control projection；Context selection、materialization、model request 是三个独立可审计阶段。

Context 同时区分四层 ownership：

```text
full audit candidate graph
    -> 保存全部候选/依赖，允许含 shadow-only branch

control-eligible surface
    -> 当前真正允许模型选择的 candidate family

model-facing compact projection
    -> 只暴露当前 control-relevant candidate / dependency / sufficiency relation

persistent execution surface
    -> 已选择 semantic effect 的跨 tick admission / delivery / apply / confirm
```

固定 invariant：

```text
shadow-only candidate != active decision branch
shadow-only dependency != active EvidenceNeed
full-audit undetermined != model-facing undetermined automatically
```

compact projection 必须在当前 model-visible control family 上重算 Decision Sufficiency。唯一 ready supported plan 若为 zero-effect hold，且不存在其它 control-visible live alternative / blocking need，则显式标记 `sufficient_for_no_action`；不能用含 shadow branch 的 full-audit uncertainty 诱导模型继续无意义调查。

## 5. Capability ownership

Agent 面向稳定 capability semantics：

```text
CapabilityContract
  -> CapabilityBinding
  -> physical/tool implementation
```

两类 capability 共用这一套 contract。

### Evidence-use

```text
communication.center.node_report
communication.gateway.receipt_summary
communication.gateway.primary_health
communication.center.full_dump   # baseline materializer only; not a normal planner tool
```

### Communication-device

```text
communication.config.set_sampling_interval
communication.config.set_report_period
communication.fallback.gateway_backup
communication.fallback.terminal_dts
communication.fallback.access_assist
```

底层函数/API 名不定义 capability identity。Binding 必须声明 owner/path/return path/freshness/latency/cost/opportunity/failure semantics。

## 6. Physical substrate ownership

以下语义继续由原 simulator 持有，Agent 层不能为了获得收益而修改：

```text
code/instance/
  PhysicalWorld / node / cache / CenterView / GatewayView

code/monitoring/opportunity.py
  Class A/control opportunity

code/v3joint/joint_plane.py
  primary/backup transport

code/v3joint/joint_run.py
  full-sim composition root

code/instance/scoring.py
  physical/business outcome
```

terminal-DtS、gateway backup、access assist、本地自治、sampling/report config 等全部复用既有 implementation。

## 7. Agent planner ownership

Planner/LLM 只能提出下一步 intent：

```text
EvidenceNeed / capability request
state patch proposal
communication-device action
supported candidate-plan selection
wait / stop
```

Runtime 持有 schema validation、effect ceiling、owner/reachability、freshness、事实写入和 trace authority。

当 Runtime 已构造 typed candidate plan 时，模型负责 semantic selection：

```text
selected_plan_id = <supported model-visible candidate>
```

Runtime 负责验证该 plan 的 visibility / feasibility / unresolved conditions，并确定性展开其 typed invocations。模型不需要机械复制几十条 per-resource JSON action；该 expander 属于普通 Runtime substrate，不提供额外 planning intelligence。

已选择的 config semantic effect 进入 Runtime-owned persistent execution intent。普通 in-flight / dwell / admission delay 不要求模型每 tick 重复提出同一 action；observation-only 或 no-effect planner turn 也不隐式取消未完成 intent。TaskContract revision、显式 supersede 或 observed target satisfaction 才能改变/完成对应 intent。

第一版 deterministic planner 必须和已有强普通策略行为等价，以验证 harness；之后 LLM/learned planner 使用同一 runtime 和 capability set。

## 8. Action lifecycle

通信 action 至少区分：

```text
requested
accepted/refused
delivered
applied
confirmed
```

`note_command_sent` 只证明 submission accepted，不等于 applied。节点后续合法报告与 generation/value 对齐后，才能记录 `applied_confirmed`。

## 9. Runtime Trace ownership

每个正式 run 至少落：

```text
OperationalTask
RuntimeTaskContract / TaskRun
EvidenceWorldRevision
InvestigationState / EvidenceNeed
ContextManifest / PromptAssembly
Model/Planner request + response
CapabilityRequest / Result
Percept / StatePatch
PolicyDecision
ActionRequest / Result / PhysicalEffect
TaskCompletion
PhysicalScore
```

R0/R1/R2/R3 replay 和 Agent metric 都从同一 trace 派生。

## 10. Current acceptance

1. Operational Task 与 Runtime TaskContract 可机械区分并编译；
2. Evidence adapter 不泄漏 hidden truth；
3. evidence/device tools 使用同一 capability contract；
4. ContextManifest 保留 refs/revision；
5. Runtime Trace 可重放；
6. communication + Agent metrics 同时输出；
7. baseline/oracle 使用同一 action space/information boundary；
8. 新 runtime 不改变旧 simulator semantics；
9. `run_checks.py` 的 agentic conformance 必须通过；
10. candidate reference 在进入真实模型评价前必须与 benchmark ordinary comply semantics 做 deterministic physical identity gate；
11. model-facing protocol revision、source hash、per-run replay audit 与 result aggregate 必须能机械追溯。

当前上述 acceptance 已进入正式 `run_checks.py` / experiment audit：

- O1–O6 Operational Task 可通过同一 runtime 编译/执行；
- O2 global/localized 在 paired seeds 上保持 deterministic physical-equivalence；
- R0 protocol replay、R1 frozen model input、R2 exact Context reconstruction、R3 full-simulator re-execution 已实现；
- `ModelRequest / ModelAttempt / ModelUsage / PlannerDecision` ledger 已实现；
- gateway owner evidence acquisition 会区分 `UNREACHABLE` 与负观测；
- sampling/report config、gateway backup、terminal-DtS、access-assist 五条 device capability 均通过 typed runtime→既有 physics conformance；
- upstream `Task/EvidenceNeed/Percept/Context` 与 planner `selection/order/arguments/policy` gold replacement 已实现；
- communication baseline / evaluator-only oracle schema 与 Agent baseline registry 已冻结；
- global Task scope authority 已由 O5/O6 seeds0..4 candidate-reference == legacy comply 的 deterministic physical identity regression 固定；
- `center.full_dump` 的 `baseline_materializer_only` ownership 会从正常 planner-visible capability surface 排除；
- candidate-plan semantic selection / Runtime expansion 与 no-action sufficiency 均已进入 hard regression；
- 当前 model-facing protocol 为 `communication-planner-json-v6-no-action-sufficiency`；
- DeepSeek Flash 已进入真实 R3 full episode；正式 5-seed main-table 的 Method-first 15 rows 已全部通过 effect-scope exact / zero-observation / candidate+legacy physical exact gate，剩余 baseline confirmatory 仍在运行，因此尚未自动晋升为 `results/CLAIMS.md` 的模型方法 claim。

任何新增 module 若引入平行 Task/Context/Capability schema、绕开 owner/reachability/freshness gate、把 evaluator truth 暴露给 planner，或为了收益改动既有 physical scorer/simulator semantics，都视为违反本 contract，即使单个实验数字变好。
