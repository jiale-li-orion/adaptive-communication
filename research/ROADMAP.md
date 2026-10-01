# Roadmap：Evidence World + Closed-Loop Agent Runtime

日期：2026-10-01。实验语义与指标由 [`EXPERIMENT-DESIGN-v1.md`](EXPERIMENT-DESIGN-v1.md) 持有，本文只拥有建设顺序。

## P0 — Design freeze

已完成：

- Operational Task / Runtime TaskContract 两层语义；
- Evidence World / Runtime Trace / Communication × Agent metric contract；
- 14-node 当前系统模型；
- 9 个 communication capability 的 domain registry；
- source-grounded hybrid simulation 数据边界。

## P1 — Unified runtime harness

当前状态：**统一 runtime 主干已经可用，当前从基础设施建设转入 baseline / LLM / robustness 扩展。**

已落代码：

```text
code/agentic_communication/runtime_contracts.py
code/agentic_communication/contracts.py
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
code/agentic_communication/trace.py
code/agentic_communication/metrics.py
code/agentic_communication/run.py
```

已完成：

- O2 deterministic R3：task-conditioned/full-dump 两臂与旧 `mission-comply` 在 5/5 seeds 上 physical signature 逐项一致；
- `ModelRequest / ModelAttempt / ModelUsage / PlannerDecision` live ledger；
- generic `PlannerConsumer` interface，deterministic / callable model / gold wrapper 共用；
- R0 protocol、R1 frozen model input、R2 exact context reconstruction、R3 full simulator；
- owner-scoped gateway evidence：可达时产生 typed Percept，主回传中断时返回 `UNREACHABLE`；
- multi-round `Context -> evidence capability -> Evidence World revision -> Context -> device policy`；
- config device capabilities 与 `gateway_backup` 已经从 PlannerDecision 真实作用到现有 full simulator；
- cumulative live gold replacement 可在 R3 上替换 capability selection / order / arguments / policy；
- R1 frozen-input evaluator 已能计算 stopping、tool selection、order、argument grounding。
- model-facing protocol 已冻结为 `communication-planner-json-v1`，带稳定 hash、typed proposal schema 与 evaluator-truth leakage guard；
- `BackendPlannerConsumer` 可复用仓库现有 `complete(messages)` backend；R1/R3 model CLI 已落，缺 endpoint/key 时硬失败，不回退 scripted backend。

当前 capability registry 明确区分“已声明”与“已接入 Agent runtime”：3 个 live observation、5 个 live device、1 个 baseline-only。5 个 device capability 均已走 typed PlannerDecision -> existing full-sim effect：sampling interval、report period、gateway backup、terminal-DtS、access assist。`center.full_dump` 只保留为 baseline materializer，不作为正常 planner tool。

## P2 — Operational Task benchmark

已完成 O1–O6 可重放 episode catalog：

1. Monitoring Continuity；
2. Risk Escalation；
3. Backhaul-Outage Sustainment；
4. Energy-Constrained Monitoring；
5. Recovery & Reconciliation；
6. Compound Long-Horizon Operation。

O1–O6 已用同一个 typed live planner 做过 R3 catalog smoke，6/6 task families 与 legacy comply reference physical signature 逐项一致；该结果只证明 benchmark/runtime conformance，不构成方法收益。

每个 episode coordinate 冻结：Operational Task、source refs、NASA POWER year/start window、link/outage seed、capability registry revision、scorer revision 与 evaluator-only world coordinate。

source-period split 已落为 [`AGENTIC-BENCHMARK-SPLIT.v1.json`](AGENTIC-BENCHMARK-SPLIT.v1.json)：2022=train、2023=dev、2024=test，source year 先于 random seed。O4 跨 2022/2023/2024 的 full-sim smoke 已验证三个 source hash 与实际 harvested-energy outcome 均分离，同时每个年份 typed runtime 与 paired deterministic reference 保持 physical-equivalent。窗口位置属于 A-layer benchmark coordinate，不冒充真实历史灾害日期。

## P3 — Deterministic baselines / oracle

当前已有机器可读 registry：[`AGENTIC-BASELINE-REGISTRY.v1.json`](AGENTIC-BASELINE-REGISTRY.v1.json)，canonical owner 为 `code/agentic_communication/baselines.py`。online baseline 与 evaluator-only oracle 使用不同 class。

### Communication：已注册

- local autonomy / local floor；
- mission-comply deterministic reference；
- AoI / EnergyAware ordinary controllers；
- gateway backup EDF / maxcov；
- existing local autonomy；
- `dynamic_oracle` / `delivery_oracle` evaluator-only reference。

### Agent/runtime：已注册 / 已实现

- FullDump；
- task-conditioned Context；
- deterministic comply planner；
- diagnosis-first fixed-probe baseline；
- fixed-order eager baseline；
- typed callable planner interface；
- live R3 gold replacement；
- R1 frozen-input diagnostic evaluator。

O2 Agent baseline matrix 已有正式 5-seed paired result：deterministic comply / evidence-aware / diagnosis-first / fixed-order eager / generic-ReAct 五臂均通过 physical-equivalence 与 replay audit。数值只从 `results/agentic/o2-baseline-matrix-v1/aggregate.json` 进入 [`README.md`](README.md) 的自动生成区块和 `paper/generated/`，本文不复制实验数字。

传统 communication baseline matrix 也已完成 5-seed 正式运行：Local / AoI / EnergyAware / mission-comply 在同一 O2 / `DEFAULT_FULLSIM` 下比较，backup chooser 的 EDF / maxcov 采用固定 LocalPolicy 的单因素对照；`dynamic_oracle` 与 `delivery_oracle` 保持 evaluator-only 身份。冻结结果位于 `results/agentic/communication-baseline-matrix-v1/`，生成器只从该目录的 aggregate/audit 更新 research/results 摘要。

generic ReAct context baseline 已完成：模型侧只保留 Runtime TaskContract、resource inventory、合法 raw evidence、capability catalog 与 recent tool outcomes，不暴露 EvidenceNeed / InvestigationState / task-conditioned selection；同一 deterministic planner 下已通过 paired physical-equivalence，且正式 O2 baseline matrix 已包含该臂。ordinary deterministic compiler/keyed-join baseline 由 `DeterministicComplyPlannerConsumer` 直接承担，不再新增同义实体。

P3 当前只保留 generic VoI/active acquisition 为条件项。VoI 必须等 evidence acquisition 的 latency/bytes/airtime/energy/opportunity-cost 至少有一套 source-backed 或 simulator-authoritative cost model后再启用；当前 gateway remote-read transport cost 明确标记为 `unmodeled`，因此不会用任意权重制造一个看似很强的 VoI baseline。除此之外，接 API 前可执行的 deterministic Agent baseline、传统 communication controller、oracle/reference、source-period、robustness、task-transfer、attribution infrastructure 与 frozen model inputs 已由 `make agentic-preapi` 统一覆盖。

### Method ablation

- raw/flat telemetry vs Evidence World；
- EvidenceNeed tracing on/off；
- communication-aware capability planning on/off；
- context dependency refresh on/off；
- typed evidence-use/device-use capability runtime on/off。

## P4 — LLM Agent benchmark

Planner-level gold replacement 已经可执行：capability selection / order / arguments / policy 可以在同一 R3 episode 中累计替换并重跑物理系统。模型横向比较之外，完整目标仍是：

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

目标不是只报“哪个模型最高分”，而是沿 Runtime Trace 定位 task grounding、evidence、tool/capability、context、policy 和 physical execution 各层的 failure contribution。

P4 当前 transport、三-context model matrix 与 attribution matrix infrastructure 均已就绪，但尚无真实模型结果：环境未配置可用 endpoint/key，因此没有发外部 API，也没有 scripted 结果冒充模型结果。`results/agentic/model-context-inputs-v1/global/seed-000/` 已冻结 task-conditioned / FullDump / generic-ReAct 三套 O2 输入，三者共享 Operational Task、capability surface 与 paired physical reference，且 R0/R1/R2 replay exact。`run_model_context_matrix.py` 支持先 R1 frozen-input diagnosis，再对选中的 model/context 进入 R3；缺凭证会在任何模型实验前显式失败。upstream gold replacement 已覆盖 Task / EvidenceNeed / Percept / Context；planner-level live replacement 已覆盖 capability selection / order / arguments / policy；`results/agentic/attribution-matrix-infra-v1/` 已验证两类 replacement 按协议累计组合且层间不偷渡。真实模型接入后直接复用该协议跑实际 failure attribution。

[`AGENTIC-ATTRIBUTION-PROTOCOL.v1.json`](AGENTIC-ATTRIBUTION-PROTOCOL.v1.json) 已冻结 layer ownership：当前架构下 Task/EvidenceNeed/Percept/Context 属于 runtime/method ablation，替换后必须重新跑模型；capability selection/order/arguments 属于 planner/model post-hoc diagnostic；Gold Policy 与 Physical Oracle 必须回到 R3 才能评价通信后果。

## P5 — Full-sim communication evaluation

primary：

- Timely Obligation Delivery Rate；
- Feasible-Obligation Delivery Rate；
- collection / delivery / missing / censored；
- latency p50/p90/p95 / AoI / observation gap；
- config install / mismatch / command lifecycle；
- node survival / residual energy；
- backup packets/bytes；
- DtS attempts/energy；
- uplink/downlink/control airtime；
- recovery latency / historical completeness。

Agent diagnostics 同时报告，但不与通信指标硬加权成一个 overall score。

## P6 — Robustness / transfer

已完成两层 robustness gate：

- source-period gate：NASA POWER 2022/2023/2024 跨年 full-sim；
- five-axis paired gate：weather window、backhaul outage、target scope、evidence owner、deployment scale，共 10 个 coordinate，全部通过 paired physical-equivalence、R0/R1/R2 replay 与 axis-activation audit。
- secondary task-authority transfer：S14/Qili 公开监测文献的阶段顺序映射为 source-derived Operational Task；5 seeds 下 hand-authored 与 source-derived schedule 均通过 paired physical-equivalence / replay，且 hand-authored arm 逐项复现主 O2 aggregate。时间压缩与通信 profile 仍是 A-layer benchmark transform，不当作现场预警阈值。

当前正式 coordinate 由 [`AGENTIC-ROBUSTNESS-MATRIX.v1.json`](AGENTIC-ROBUSTNESS-MATRIX.v1.json) 持有，结果由 `results/agentic/robustness-matrix-v1/` 持有。下一步扩展：

- NASA POWER 2022/2023/2024 与不同 start window；
- source-grounded vs synthetic harvest；
- access outage duration/phase；
- 更细 target subset / evidence owner count；
- context revision length；
- deployment scale / reachable subset；
- model family；
- raw monitoring-data / rainfall-hydrology-slope-stability generator 驱动的 Operational Task transfer。

地灾 physics 只作为上游 task generator；主 Agent 不承担灾害预测。

## P7 — Artifact / paper freeze

每个 confirmatory experiment 必须有：

```text
experiment_contract.json
run_manifest.json
source_manifest.json
per_episode_results.jsonl
runtime_traces/
aggregate.json
audit.json
```

要求 paired seed、baseline success、oracle success、metric denominator 一致、无 hidden-truth leakage、无 post-hoc exclusion，并由结果文件生成 paper 表图。
