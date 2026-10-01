# 当前研究：Evidence-Grounded Closed-Loop Agentic Communication

更新：2026-10-01。本文是当前公开研究入口。部署参数以 `spec/instance-v1-manifest.md` 和代码为准，实验设计以 [`EXPERIMENT-DESIGN-v1.md`](EXPERIMENT-DESIGN-v1.md) 为准，数学系统模型以 [`docs/s6-model/system-model.md`](../docs/s6-model/system-model.md) 为准，历史冻结主张仍只认 [`results/CLAIMS.md`](../results/CLAIMS.md)。

场景固定为**灾前山区地灾监测**：电池/光伏供电的监测节点经 LoRaWAN Class A 类接入现场网关，蜂窝主回传可能间歇中断，系统已有 gateway backup、terminal-DtS、access assist、采样/上报配置和本地自治等能力。风险等级与监测要求由外部授权；本文研究这些任务如何在受损通信条件下被正确执行。

## 1. 两层 Task

**Operational Task** 是 benchmark / 业务语义，回答“这次通信系统要完成什么”。当前 task families：

- O1 Monitoring Continuity；
- O2 Risk Escalation；
- O3 Backhaul-Outage Sustainment；
- O4 Energy-Constrained Monitoring；
- O5 Recovery & Reconciliation；
- O6 Compound Long-Horizon Operation。

**Runtime TaskContract / TaskRun** 是 Agent Runtime 的程序语义。一个 Operational Task 可被编译为多个 TaskRun；`desired_state / evidence_contract / temporal_contract / effect_ceiling / completion_predicate` 决定当前运行实例需要知道什么、允许产生什么 effect、什么时候完成或停止。

## 2. 方法

方法由两层闭环组成。

```text
Method I — Evidence World

Physical/Data Plane
  -> Observation / Artifact
  -> typed Evidence
       provenance / owner / generated_at / observed_at
       revision / freshness / reachability / status
  -> Evidence World

Method II — Task-conditioned Agent Runtime

Operational Task
  -> Task Compiler
  -> Runtime TaskContract / TaskRun
  -> EvidenceNeed / InvestigationState
  -> ContextManifest / materialization
  -> evidence-use capabilities
  -> communication-device capabilities
  -> Policy / Physical Effect
  -> new Evidence / next runtime revision
```

Agent 不直接读取 simulator hidden truth。`UNREACHABLE / TIMEOUT / STALE / NONE_RECENT / NEGATIVE_OBSERVATION` 是不同 observation semantics；控制 action 也必须区分 `requested / accepted / delivered / applied / confirmed`。

此前研究过的 EvidenceNeed tracing、communication-constrained capability planning、context refresh 继续作为 Runtime 内部机制和 ablation，不再单独承担整篇论文 framing。

## 3. 自包含 Runtime

公开实现全部位于本仓：

```text
code/agentic_communication/runtime_contracts.py
  TaskContract / TaskRun
  EvidenceNeed / InvestigationState
  CapabilityContract / Binding / Request / Result
  Percept
  ContextManifest / MaterializedFragment / PromptAssembly

code/agentic_communication/contracts.py
  OperationalTask
  CommunicationEvidence / EvidenceWorldSnapshot
  ExperimentSpec / RuntimeTraceEvent

code/agentic_communication/task_compiler.py
code/agentic_communication/evidence_world.py
code/agentic_communication/capabilities.py
code/agentic_communication/context_runtime.py
code/agentic_communication/planner.py
code/agentic_communication/replay.py
code/agentic_communication/trajectory_eval.py
code/agentic_communication/r1_evaluation.py
code/agentic_communication/gold_replacement.py
code/agentic_communication/model_protocol.py
code/agentic_communication/baselines.py
code/agentic_communication/benchmark_split.py
code/agentic_communication/policy.py
code/agentic_communication/metrics.py
code/agentic_communication/run.py
```

两类 tool 使用同一 Capability abstraction：

- **evidence-use capability**：从合法 Evidence World / owner surface 取得 Percept；
- **communication-device capability**：改变配置、路径、发送或本地通信行为。

它们共享 typed input/output、authority、owner/path、latency、bytes/airtime/energy、failure 与 effect semantics；底层 Python function/API 名不是能力语义。

通信 domain registry 位于 [`COMMUNICATION-DOMAIN-REGISTRY.v0.1.json`](COMMUNICATION-DOMAIN-REGISTRY.v0.1.json)，当前登记 2 个 Runtime Task template、9 个 communication capability contracts（4 observation + 5 action）。registry 同时持有 `runtime_status`：当前 3 个 live planner observation、5 个 live planner device、1 个 FullDump baseline-only。五条 device path（sampling/report config、gateway backup、terminal-DtS、access assist）都已通过“runtime invocation 与静态/既有机制 physical-equivalent”的 conformance test；`center.full_dump` 不计正常 planner tool。

## 4. 数据与系统

主实验采用 **source-grounded hybrid simulation**：

- SRTM1：真实地形与 ITM 逐链路传播；
- NASA POWER 2022/2023/2024：逐小时 irradiance / T2M；
- ChirpBox：LoRa 时间相关链路 trace；
- 公开设备、Class A、北斗/备用通信与地灾监测资料：约束 capability/task 语义；
- frozen 14-node full simulator：`Instance + JointControlPlane + run_joint + evaluate`。

`run_joint` 已暴露 `irradiance_year / irradiance_start_hour`。[`AGENTIC-BENCHMARK-SPLIT.v1.json`](AGENTIC-BENCHMARK-SPLIT.v1.json) 当前按 source period 固定 2022=train、2023=dev、2024=test，再在每个 source period 内展开 task family / weather window / seed；不会让 random seed 跨 split。O4 已做 2022/2023/2024 full-sim smoke，三个 source year 的实际 harvested-energy outcome 分离，且每年 typed runtime 与 paired deterministic reference 逐项 physical-equivalent。

地灾 physics 只作为可选的上游 task generator：`Rainfall/DEM/Soil -> Hydrology -> Slope Stability -> External Authority -> Operational Task`。主通信 Agent 从已授权 Operational Task 开始，不承担滑坡预测。

## 5. Evaluation

**Communication outcome 是 primary。** 当前统一抽取：Timely Obligation Delivery Rate、collection rate、delivery latency / AoI、missing collection/delivery、node survival / residual energy、backup packets/bytes、DtS attempts/energy、control airtime、command lifecycle 等。

**Agent/runtime metric 用于 failure attribution。** 当前 R1 frozen-input evaluator 已直接计算 stopping correctness、capability selection precision/recall、order LCS、argument grounding；R3 cumulative gold replacement 可把 selection/order/arguments/policy 的修复继续传到真实 communication outcome。Task、EvidenceNeed、Percept、Context 的 upstream frozen-artifact replacement 已实现，并已与 planner-level selection/order/arguments 组合成正式 cumulative attribution matrix infrastructure：20 个 O2 frozen R1 turns 的受控 corruption/recovery audit 已 PASS。下一步是把同一 matrix 用在真实模型输出上。Context sufficiency/redundancy、accepted/confirmed split、model/tool calls、latency 与 materialized bytes 已进入现有 trace/aggregate。

真实模型边界已冻结为 `communication-planner-json-v1`。`BackendPlannerConsumer` 只依赖现有 backend 的 `complete(messages)` 接口，可直接复用仓库 OpenAI-compatible / local-vLLM transport；`run_r1_model_eval.py` 先在 frozen PromptAssembly 上诊断模型，`run_r3_model_eval.py` 再进入 full simulator，并带硬 model-call budget。当前环境没有配置可用 API endpoint/key，所以这里只冻结了协议、transport、dry-run 与失败纪律，没有产生真实模型数字，也不会回退 scripted backend。

不设置拍脑袋 overall score；physical outcome 与资源成本做 paired comparison / Pareto。

## 6. 当前已跑通的第一条 R3 vertical slice

O2 Risk Escalation 已接入现有 full simulator。实验入口：

```bash
python3 code/experiments/agentic/run_o2_risk_escalation.py --seeds 0,1,2,3,4
```

输出：`results/agentic/o2-risk-escalation-v1/`

第一批三臂：

```text
legacy_comply
task_conditioned runtime + deterministic comply planner
full_dump runtime + deterministic comply planner
```

实验数字不在本文手写。以下区块由 `scripts/make_agentic_artifacts.py` 从冻结结果自动更新；独立生成版见 [`generated/agentic_o2_summary.md`](generated/agentic_o2_summary.md)。

<!-- BEGIN GENERATED: agentic-o2 -->
### 自动生成结果摘要

> 数字由 `scripts/make_agentic_artifacts.py` 从 `results/agentic/*/aggregate.json` 生成；不要手改本区块。

**Global O2 / 5 seeds / R3 conformance.** `legacy_comply`、`task_conditioned`、`full_dump` 三臂逐 seed physical signature 完全一致，audit=`PASS`。共同 physical mean：TDR `0.32436`，collection rate `0.51062`，p90 delivery latency `468.0 s`，backup `2141.6 B`，total consumed energy `0.35077 Wh`。

**Localized O2 / 5 seeds / Context conformance.** task-conditioned 与 FullDump 同样保持逐 seed physical-equivalent，Context sufficiency recall 均为 `1.000`。task-conditioned 平均选择 `10.32` 条 evidence、materialize `19763.6` B；FullDump 分别为 `27.32` 条和 `29575.6` B。两臂共同 physical mean：TDR `0.45020`，collection rate `0.61124`，p90 delivery latency `3000.0 s`。

**Diagnosis-first / 5 seeds / deterministic efficiency baseline.** fixed gateway diagnosis 与直接 deterministic comply 在 5/5 seeds 上 physical signature 完全一致；每个 episode 平均额外产生 `2.00` 次 model request、`4.00` 次 capability request、`4.00` 个 Percept、`2.00` 次 Context revision，并额外 materialize `65046.8` B。该结果只度量“先做与任务无关的固定诊断”的 runtime 开销。


**O2 baseline matrix / 5 seeds.** 五臂 physical signature 与 replay 均逐 seed 一致。相对 direct deterministic comply，task-conditioned evidence-aware 在 O2 上额外 tool call 为 `0.0`；diagnosis-first 平均额外 `4.0` 次 tool / `2.0` 次 model；每小时 fixed-order eager 平均额外 `28.0` 次 tool / `14.0` 次 model，并额外 materialize `480537.8` B；generic ReAct context 的 tool/model delta 为 `0.0/0.0`，materialized-bytes delta 为 `-377527.4` B。该对照支持“按任务打开 evidence need 可以避免固定探测开销，并量化 harness cognitive fragments 的 Context 成本”，不支持 LLM 质量提升主张。

**Traditional communication baselines / O2 / 5 seeds.** Local、AoI、EnergyAware、mission-comply 与 backup EDF/maxcov 已在同一个 O2 / `DEFAULT_FULLSIM` 下正式运行。中心策略比较固定 backup chooser=EDF；backup chooser 比较固定 center policy=Local。mean TDR：Local `0.14084`、AoI `0.14505`、EnergyAware `0.44487`、mission-comply `0.32436`。Local+maxcov 在该坐标上与 Local+EDF 的 TDR 相同，但 backup bytes 为 `808.4` vs `768.4`。evaluator-only dynamic-energy oracle 未被任一 online arm 突破；primary-only delivery oracle 的 `actual → fixed-send → free-send-with-sample → link-opportunity` 均值为 `191.0 → 191.0 → 355.8 → 529.2`。oracle 只作 evaluator reference，不参与 online policy 排名。

**Source-period full-sim gate.** O4 在 NASA POWER 2022/2023/2024 三个独立 source period 上均保持 typed runtime 与 paired deterministic reference physical-equivalent；实际 harvested energy 分别为 `0.14604 / 0.14674 / 0.09480 Wh`，证明 split 已进入物理 simulator，而非只存在 manifest 中。该实验仍是 robustness-coordinate gate，不是跨年方法收益结果。

**Five-axis robustness gate.** `robustness-matrix-v1` 当前包含 `10` 个 paired coordinates，覆盖 `5` 个轴：weather window、backhaul outage、target scope、evidence owner、deployment scale。五轴 activation 均为 `PASS`，所有 coordinate 都与 paired deterministic reference physical-equivalent 且 R0/R1/R2 replay exact。该结果只证明 benchmark 轴真正进入 full simulator/runtime，不构成 robustness 方法收益。

**Source-derived Operational Task transfer / 5 seeds.** `task-transfer-qili-v1` 将 S14 报告的真实监测阶段顺序映射成 external-authority Operational Task，并与 hand-authored O2 共享同一个 `DEFAULT_FULLSIM`、runtime、capability surface、planner 与 scorer。两种 schedule 各自 5/5 paired physical-equivalent 且 replay exact；hand-authored arm 的通信均值逐项复现主 O2。Qili 的等时 4 h phase 压缩和 `3600/300/3600 s` profile 是 A-layer workload transform；跨 schedule 的 TDR/energy 差异属于任务需求差异，不作方法收益比较。

**Attribution protocol infrastructure / 20 frozen R1 turns.** `attribution-matrix-infra-v1` 对同一 O2 frozen trace 注入受控 upstream + planner corruption，并按 Task→EvidenceNeed→Percept→Context→Selection→Order→Arguments 累计修复。完成 Gold Context 后 assembly match rate=`100.00%`；完成 capability selection 后 tool exact=`100.00%`，但平均 unresolved argument slots=`0.85`；直到 Gold Arguments 后 argument grounding 才到 `100.00%`。该结果只验证 attribution evaluator 的层级隔离/累计恢复，不是 LLM failure rate。

**Frozen model-context inputs / O2 seed 0.** task-conditioned、FullDump、generic-ReAct 三套输入各冻结 `74` 个 R1 turn，三者均与 paired legacy physical-equivalent 且 R0/R1/R2 replay exact。model-facing protocol mean bytes 分别为 `31293.4 / 31293.4 / 26943.2`。generic-ReAct 输入完全移除 EvidenceNeed / InvestigationState harness artifacts；该 manifest 只冻结公平模型输入，不包含任何真实模型结果。

这组结果的 claim ceiling 仅为：**同一正确 deterministic policy 下，Operational Task scope 可以减少无关 evidence/context materialization，而不改变物理业务结果。** 它不证明 LLM policy quality 提升。
<!-- END GENERATED: agentic-o2 -->

## 7. 下一步

1. 有真实 endpoint/key 后先跑三-context model matrix 的 R1 frozen-input diagnosis，再决定哪些模型/context 值得进入 R3 physical consequence；共享 frozen input 已落在 `results/agentic/model-context-inputs-v1/`，协议/transport 已就绪，但不会用 scripted backend 冒充真实模型结果；
2. generic ReAct context baseline 已完成并进入正式 O2 baseline matrix；deterministic compiler/reference、task-conditioned evidence-aware、diagnosis-first、fixed-order eager 也已有同 capability surface 的正式对照。VoI 仅在 evidence acquisition cost/value 模型有 source-backed / simulator-authoritative 依据后启用，当前不造任意权重 baseline；
3. attribution matrix infrastructure 已完成；真实模型接入后按现有 Task→EvidenceNeed→Percept→Context→Selection→Order→Arguments→Policy/Physical Oracle 协议跑实际 failure attribution；
4. 在已完成的 source-period + weather/outage/scope/owner/scale 五轴 gate 上继续扩 access-outage phase、reachable subset、context length、owner count 与更大 deployment scale；
5. secondary transfer 已完成第一条 S14/Qili source-derived schedule；下一步再做 raw monitoring-data 或 rainfall/hydrology/slope-stability generator 驱动的 Operational Task transfer，并继续把 hazard prediction 留在 external authority 一侧。

建设顺序见 [`ROADMAP.md`](ROADMAP.md)。

## 8. 公开入口

| 文件 | 用途 |
|---|---|
| [`EXPERIMENT-DESIGN-v1.md`](EXPERIMENT-DESIGN-v1.md) | benchmark / task / trace / metric / baseline / oracle authority |
| [`ROADMAP.md`](ROADMAP.md) | 当前建设顺序 |
| [`COMMUNICATION-DOMAIN-REGISTRY.v0.1.json`](COMMUNICATION-DOMAIN-REGISTRY.v0.1.json) | typed communication capability registry |
| [`AGENTIC-BASELINE-REGISTRY.v1.json`](AGENTIC-BASELINE-REGISTRY.v1.json) | online baseline / evaluator-only oracle registry |
| [`AGENTIC-BENCHMARK-SPLIT.v1.json`](AGENTIC-BENCHMARK-SPLIT.v1.json) | source-period-separated O1–O6 replay coordinates |
| [`AGENTIC-ROBUSTNESS-MATRIX.v1.json`](AGENTIC-ROBUSTNESS-MATRIX.v1.json) | weather/outage/scope/owner/scale 五轴 paired robustness coordinates |
| [`AGENTIC-ATTRIBUTION-PROTOCOL.v1.json`](AGENTIC-ATTRIBUTION-PROTOCOL.v1.json) | runtime/model/evaluator 的 gold-replacement ownership 与 rerun/post-hoc 边界 |
| [`sources.json`](sources.json) | 来源 URL、scope、boundary |
| [`RELATED_WORK.md`](RELATED_WORK.md) | benchmark / Agent / communication related work |
| [`../docs/s6-model/system-model.md`](../docs/s6-model/system-model.md) | 数学系统模型 |
| [`../docs/Agentic-Communication-后续研究Ownership.md`](../docs/Agentic-Communication-后续研究Ownership.md) | runtime/domain ownership 与 invariant |
| [`../results/CLAIMS.md`](../results/CLAIMS.md) | 历史冻结主张 |
