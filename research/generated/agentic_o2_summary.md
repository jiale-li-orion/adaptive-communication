# Agentic O2 generated summary

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
