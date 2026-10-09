# Repository Asset Reuse Audit — 2026-10-09

状态：**current reuse map / no semantic authority**。

目标：停止重复实现。每个旧资产只允许有一个当前角色：`CURRENT CORE / PAPER EVIDENCE / REUSABLE SUPPORT / PROVENANCE ONLY / RETIRE`。

---

## 1. CURRENT CORE — 继续维护 / 新实验直接复用

### `code/evaluation/agentic/future_choice_engine.py`

角色：**generic correctness orchestration core**。

持有：

```text
carried replayable certificate
→ sound U=0
→ constructive L=1
→ exact fallback
→ certificate carry after commit
```

不持有 domain physics / transition / certificate construction。

规则：B/C 下一步若再写 orchestration，应先扩 adapter/protocol，不得再造第三个 engine。

### `code/evaluation/agentic/layer2_v2_conflict_frontier.py`

角色：**current set-level conflict / event-local structural core**。

持有：

- obligation–opportunity connected components；
- bipartite max-flow / residual min-cut Hall deficit；
- minimum-backup lower bound；
- dependency / validity domain；
- component-local invalidation。

ASC shared-opportunity / component-local transfer 已直接复用它。后续 set-level feasibility work 首选扩这里。

### `code/evaluation/agentic/layer2_v2_persistent_frontier.py`

角色：**persistent conditional certificate core**。

继续用于：certificate validity-domain、resource interval、causal policy prefix reuse、exact fallback integration。

### `code/evaluation/agentic/layer2_v2_dependency_cache_baseline.py`

角色：**strong ordinary systems baseline**，不是 method component。

必须保留，因为 reviewer 会问“普通 persistent exact / dependency cache 不就够了吗”。当前 F3 的一个重要价值正是它在 ASC event sequence 上没有额外 separator replay。

### Layer-1 exact / causal process / baseline infrastructure

```text
exact_reference_oracle_v0_1.py
causal_evidence_process_v0_1.py
v8_policy_baselines_v0_1.py
layer1_v02_exact_continuation.py
```

角色：**correctness authority / red-team infrastructure**。继续复用，不再重写 exact solver。

---

## 2. PAPER EVIDENCE — 结果直接服务论文，但代码不一定继续扩

### B transfer family

```text
asc_pull_query_conditional_family.py
asc_pull_query_shared_opportunity_frontier.py
asc_pull_query_dynamic_frontier_reuse.py
asc_pull_query_component_invalidation.py
asc_pull_query_component_strong_baselines.py
```

角色：F1–F3 attribution suite。

规则：不再扩 K/D/组件数量堆更多同质格子。下一步只允许：结构 holdout、wall-time implementation、proof/audit。

### C external mission suite

```text
audit_uav_attention_future_choice.py
run_uav_attention_continuation_shield.py
run_uav_attention_future_choice_lu.py
run_uav_attention_receding_baselines.py
summarize_uav_attention_n10_headroom.py
summarize_uav_attention_set_mst_attribution.py
```

角色：F4–F6 external outcome / correctness / cross-domain attribution。

规则：N=5 已经饱和；N=10 是主结果；N=15 只保留 bounded scaling。不要继续 brute-force exact 扩大 N。

### A paper release suite

```text
materialize_layer1_paper_inventory.py
audit_layer1_fullsim_evaluator_release.py
freeze_layer1_paper_split.py
freeze_layer1_paper_release_candidate.py
run_layer1_paper_deterministic_eval.py
run_layer1_paper_llm_eval.py
analyze_layer1_paper_*.py
freeze_layer1_paper_final_release.py
```

角色：benchmark release construction / execution / final freeze。

规则：A 不再接 method-driven generator axis。

---

## 3. REUSABLE SUPPORT — 不属于 main method，但应主动复用

### `code/legacy-communication/analysis/paired_ci.py`

价值：paired bootstrap / CI / repeated-seed statistical utilities。paper statistical analysis 若功能重叠，优先抽 common utility，而不是每个新 analyzer 重写 bootstrap。

### `code/legacy-communication/analysis/pareto_front.py`

价值：quality/resource Pareto 分析。特别适合 C 的 `zero-tardiness / compute / energy` correctness–compute frontier 与 A 的 TDR/energy/fallback tradeoff 图。

### `obligation_arrival_ledger.py` / `episode_lifecycle.py`

价值：把 source obligation → sample → gateway → center delivery lifecycle 做可审计 ledger。A 的 failure taxonomy / appendix 示例应复用这些账本，不再写第四套 trace parser。

### substrate `instance/oracle.py` / physics / joint plane

价值：paper appendix 的 operational lifecycle / oracle boundary / simulator assumptions。不要把这些复制进 method layer。

### old A7–A11 Agentic runtime assets

价值：model-facing context/runtime、DeepSeek backend、replay audit、source manifest、frozen runner pattern。

当前已复用到 Layer-1 paper LLM runner；不再作为当前 Future-Choice novelty。

---

## 4. PROVENANCE ONLY — 保留测试/history，禁止作为当前 method core

### `future_choice_frontier_v0_5.py`

价值：第一次把“still potentially preservable backup commitments + query partitions + valid_until”显式化。

局限：它是 optimistic action ordering，只做 completeness-preserving ranking，不提供当前 `L/U + exact fallback` correctness contract，也不具备 component-level dependency maintenance。

处置：保留 regression / conceptual lineage；论文 history 可以说明方法演化，但当前实现一律使用 Layer2 v2 / generic engine。

### `feasibility_conflict_planner.py`

价值：早期 exact action-support matrix + alias conflict + EvidenceNeed；证明“同一 history 下不能按 hidden world 分支”。

局限：依赖小型 exact scenario-tree / fixed initial conflict；EvidenceNeed/query 是旧中心问题，不等于现在 observation-conditioned future obligations。

处置：保留 tests 和 provenance；不要在新实验直接 import 它作为主方法。

### `incremental_conflict_context.py`

价值：早期“query/ACK 只过滤 active worlds、cached world witness 不重算”的增量思想。

局限：主要做 world-support filtering；没有当前 resource/event component invalidation、min-cut conflict certificate 与 exact strong-baseline ladder。

处置：conceptual predecessor；不与 `layer2_v2_conflict_frontier` 双线维护。

### v0.2 / v0.5 / v0.6 / v0.7 benchmark history

价值：correctness regression、shortcut atlas、placement/ownership bug provenance。

处置：appendix / benchmark methodology 可引用；不能作为 paper-facing release identity 或 current hard-case count。

---

## 5. RETIRE / 不再投入时间

### 旧“Evidence-Grounded Closed-Loop Agentic Communication”主线继续扩展

理由：Wireless Context Engineering、WirelessOpsAgent、decision sufficiency / active acquisition 等邻域已经覆盖大量旧卖点；A7–A11 继续作为 runtime evidence，不再扩成独立当前主论文。

### N=5 UAV 再加 heuristic / seed / exact 规模

理由：depth4 已饱和；科学信息已被 N=10/N=15 scaling 替代。

### 为 A 人工加入 scarce resource 以制造 Future-Choice-Stress

理由：违反 cache05/cache06 与当前 benchmark authority；A 的 role 是 falsifier/reality authority。

### 继续扩 ASC synthetic K/D/component axis

理由：F1–F3 mechanism 已清楚；继续扩轴不会回答 reviewer 新问题。

---

## 6. 当前复用进度与下一步

### 6.1 统计 common utility — DONE

已从 legacy paired-analysis discipline 中抽出 current shared utility：

```text
code/evaluation/common/paper_stats.py
```

持有 paired bootstrap、Wilson interval、paired differences 与 explicit zero-check。Layer-1 deterministic / LLM analyzers 已改用 shared functions；deterministic statistical-analysis / RESULTS-SUMMARY 重新生成后 **零 diff**，因此这是纯复用重构，不改变冻结统计语义。

### 6.2 统一 correctness–compute Pareto — DONE

复用 `pareto_front.py`，把：

```text
depth-k receding
basic-U L/U
set-MST L/U
pure exact
```

已抽出：

```text
code/evaluation/common/pareto.py
```

并生成：

```text
results/transfer/uav-attention-correctness-compute-frontier.json
```

结果：四条 N=10 policy 上，exact-correct 方法族中 set-MST Future-Choice 均支配 old basic-U 与 pure-exact-mask search point；把 depth4 加入后，depth4 与 set-MST Future-Choice 同时保持非支配。该前沿只使用内部 search-state proxy，明确不冒充 CPU/wall-time ratio。

### 6.3 统一 lifecycle failure ledger — NEXT

复用 obligation arrival / episode lifecycle assets，为 A 提供 2–3 个完整 failure case study：collection miss、delivery miss、energy exhaustion、task revision/commitment failure。

### 6.4 把 current method core 的入口变成 one-path — NEXT

目标：

```text
FutureChoiceEngine
  + domain adapter
  + Layer2 v2 conflict/persistent certificate library
  + exact authority
```

旧 v0.5 / conflict planner 只留 test/provenance。新 paper code path 不应再从旧模块绕行。
