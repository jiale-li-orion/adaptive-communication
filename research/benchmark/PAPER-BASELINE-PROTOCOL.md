# Layer 1 Paper Baseline / Evaluation Protocol

状态：**FROZEN BEFORE PAPER TEST EXECUTION**
日期：2026-10-09

## 1. Purpose

本协议只服务 Layer 1 benchmark paper。它在 150-coordinate locked test cohort 打开之前冻结 baseline、LLM 子集、模型设置、指标与统计口径。

它**不**承担 Layer-2 future-choice method claim；B/C transfer experiments 使用独立 protocol。

## 2. Test cohort

来源：`results/benchmark/layer1-paper-split.json`。

```text
2024 × {w0,w2,w3} × {O1,O2,O3,O4,O6} × seeds 100..109 = 150 episodes
```

`2024-w1` 因历史 Qili held-out/model-transfer 已被执行而排除。test identity 已冻结，当前 outcome 仍锁定。

## 3. Full-test deterministic spectrum — 150/150

每个 test coordinate 至少运行其适用集合中的所有在线 baseline。不得在观察 test outcome 后增删 baseline 或调参数。

### Universal floor / runtime references

- `comm.local_policy`：现场自治、中心不重配置；所有 O1/O2/O3/O4/O6。
- `agent.deterministic_comply`：typed Agent runtime 内的普通 deterministic comply；所有 O1/O2/O3/O4/O6。

### Freshness / energy controls

- `comm.aoi`：O1 / O2 / O6。
- `comm.energy_aware`：O4 / O6。
- `comm.ea_aoi`：O4 / O6；现有 `EnergyAoiPolicy`，用于强 ordinary energy+freshness control。

### Authorized task-revision controls

- `comm.mission_comply`：O2 / O6。
- `comm.mission_sustain`：O2 / O6；`MissionChangePolicy(mode=sustain)`，持续滞回能量保护。

### Backhaul packing controls

- `comm.backup_edf`：O3 / O6。
- `comm.backup_maxcov`：O3 / O6。

对于 O3/O6 的 backup comparison，center policy 与其他 simulator settings 固定，只改变 backup chooser；不得同时改变 task schedule 或资源轴。

## 4. Evaluator-only upper bounds

不列入 online policy 排名，只用于区分物理不可行与在线策略损失：

- `oracle.delivery`：所有 O1/O2/O3/O4/O6 的**独立 primary-only decomposition coordinate**。现有 `delivery_oracle` 只建模 primary path，因此该 reference run 必须显式 `enable_backup=false`；它只报告 fixed-send / free-send-require-sample / link-opportunity ceiling 的分解，不得与启用 gateway backup 的 online policy 当作同场 task-quality upper bound排名；
- `oracle.dynamic_energy`：O4 / O6。

任何 oracle 结果必须单列，不能与 online Agent/communication policy 混表平均排名。

该说明是 test outcome 打开前的 correctness clarification：`code/agentic_communication/run.py::_delivery_oracles` 已经明确拒绝在额外 gateway-backup / terminal-DtS / access-assist path 启用时把历史 primary-only delivery oracle 当 full-system upper bound。

## 5. LLM spectrum — preregistered 30/150 subset

为了控制 API 成本并覆盖所有 task/window，LLM 子集固定为：

```text
{O1,O2,O3,O4,O6} × {w0,w2,w3} × {seed100, seed105} = 30 coordinates
```

每个 coordinate 固定运行：

- `generic_react`
- `task_conditioned`

二者使用完全相同的模型、工具面、action/evaluator contract 与重规划规则，只改变 context materialization mode。

固定模型协议：

```text
provider: deepseek_official
model: deepseek-flash
temperature: 0
reasoning_effort: low
max_tokens: 8192
json_object: true
planner_replan_mode: decision_state
max_model_calls: 32
```

LLM 失败、timeout、invalid action 不重试换模型；只按 frozen runtime retry/error policy 记录。

## 6. Primary metrics

以 execution scorer 的 operational outcome 为主：

- obligation count / timely delivered count / TDR；
- missing collection / missing delivery；
- recovery delivered / backlog lifecycle metrics（适用时）；
- dead nodes / final SoC / energy consumption（适用时）；
- center AoI + no-observation duration；
- backup packets/records/bytes、command count、failed command / retry；
- final task success / failure reason taxonomy。

LLM 额外报告：planner turns、model calls、tool calls、invalid actions、input/output tokens、latency；这些不是主要 task-quality 指标。

## 7. Statistics

- 每个 task × baseline 报 10-seed mean、median、std；
- 同一 coordinate 上做 paired difference；
- 主要连续指标报告 paired bootstrap 95% CI（10,000 resamples，seed 固定）；
- binary success/failure 报 raw count 与 Wilson 95% CI；
- 不因 test outcome 删除 outlier；environment/runtime failure 必须单列。

30-coordinate LLM 子集单独报告，不外推成 150-coordinate 全量 LLM 结论。

## 8. Failure taxonomy

至少区分：

- `PHYSICAL_INFEASIBLE`
- `COLLECTION_MISS`
- `DELIVERY_DEADLINE_MISS`
- `ENERGY_EXHAUSTION`
- `BACKHAUL/ACCESS_OPPORTUNITY_MISS`
- `TASK_REVISION_NOT_APPLIED`
- `INVALID/UNAUTHORIZED_ACTION`
- `MODEL_OR_TOOL_RUNTIME_FAILURE`

Future-Choice-specific first-irreversible-loss 不属于 Layer 1 release 的必填项；只有后续 Track C stress subset 才要求。

## 9. No-test-tuning rule

test 打开后禁止：

- 调 AoI / energy threshold；
- 更换 EDF/maxcov 参数；
- 改 LLM provider/model/temperature/reasoning effort；
- 改 LLM 子集 seed/window/task；
- 新增只因 test 表现差才引入的 baseline；
- 修改 source/task/evaluator semantics。

若发现 correctness bug，必须全局修复、记录 invalidated run，并重新执行受影响 cohort；不得局部修 test。
