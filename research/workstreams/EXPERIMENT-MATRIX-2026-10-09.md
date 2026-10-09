# Experiment Matrix — 2026-10-09

状态：**CURRENT EXPERIMENT-DESIGN AUTHORITY / paper execution plan**。

这份矩阵解决一个问题：实验不再由会话记忆、临时直觉或“哪个结果好看”驱动。每个 paper-facing run 必须有固定 ID、研究问题、cohort、selection rule、baseline、metric、correctness authority、统计口径、资源上限与 stop rule。

机器可读版本：[`EXPERIMENT-MATRIX-2026-10-09.json`](EXPERIMENT-MATRIX-2026-10-09.json)。正式 claim state 仍只认 `results/CLAIMS.md`。

## 0. Global rules

### Scientific discipline

1. **A / benchmark distribution 不因 B/C method outcome 修改。**
2. **Scale experiment 与 correctness experiment 分开。** 大规模 run 不重复每个 frontier 的 pure-exact audit；correctness 由冻结的 exact-audit cohort承担。
3. OOM / timeout / search-limit = `UNRESOLVED_COMPUTATION`，不得记为 infeasible 或 method failure。
4. 新 baseline / bound / model 在看 test outcome 后不得加入原 frozen confirmatory cohort；只能作为新增 extension artifact。
5. negative result 保留。

### Host-resource discipline

WSL 上的默认执行 contract：

```text
CPU affinity: 2 logical CPUs
nice: +10
BLAS / OMP / MKL / NUMEXPR threads: 1
long run: chunked + resumable
default memory target: < 512 MiB RSS
hard exact audit: bounded cohort only
```

禁止再次执行“100 seed × every-frontier pure exact audit”式长任务。2026-10-09 constructive-100 试跑在 96.6s / 433MiB 后 MemoryError，归类为 **RESOURCE_LIMITED_AUDIT DESIGN**，不构成科学结果。

---

# RQ1 — Is the source-grounded emergency benchmark valid and diagnostically useful?

## A1 · Source / task / evaluator validity — DONE

| Field | Contract |
|---|---|
| Purpose | 证明 source→task→execution→outcome chain 合法，不把模型表现当 benchmark validity |
| Scale | 11 canonical surfaces；23 stratified source/task samples × 5 review dimensions；7/7 current release surfaces evaluator mutation audit |
| Correctness | source profile provenance + full-sim mutation/replay |
| Result | internal audit PASS；无 independent external expert review |
| Main/Appendix | Methodology main text + audit appendix |

Outputs：`layer1-paper-track-inventory.json`、`layer1-fullsim-evaluator-release-audit.json`、`layer1-internal-source-audit-2026-10-09.json`。

## A2 · Frozen deterministic benchmark evaluation — DONE

| Field | Contract |
|---|---|
| Cohort | frozen test `2024 × {w0,w2,w3} × {O1,O2,O3,O4,O6} × seeds100..109 = 150 coordinates` |
| Online rows | 750 |
| Oracle diagnostic rows | 210 |
| Baselines | local / deterministic comply / AoI / energy-aware / EA-AoI / mission comply+sustain / backup EDF+maxcov（按 task applicability） |
| Metrics | obligation TDR, collection, delivery miss, energy/survival, AoI, backup use, task revision, failure taxonomy |
| Statistics | paired coordinate differences + frozen bootstrap/Wilson protocol |
| Main/Appendix | Main benchmark table + failure appendix |

## A3 · Frozen LLM model-spectrum subset — RUNNING

| Field | Contract |
|---|---|
| Cohort | 30 frozen coordinates × 2 modes = 60 rows |
| Model | DeepSeek official `deepseek-flash`, temp0, low reasoning, frozen protocol |
| Modes | `generic_react`, `task_conditioned` |
| Role | **benchmark model-spectrum diagnostic only**；不承担 Future-Choice method claim |
| Resource | `scripts/run_layer1_paper_llm_safe_chunk.sh`: 2 CPUs, nice+10, single-thread libs, 2 new rows/chunk |
| Statistics | paired TDR / calls / tokens / latency；runtime failures保留 |
| Stop | exactly 60 unique frozen row IDs + replay/digest checks |

## A4 · Lifecycle failure case studies — DONE

固定 lexicographic selection：delivery-only / energy-collection / task-revision 三种 failure layer；instrumented replay 必须与 frozen aggregate一致。

Main text用途：解释 aggregate TDR为何不够；Appendix给完整 lifecycle ledger。

## A5 · Final benchmark release — BLOCKED ONLY BY A3

A3 完成后运行 `analyze_layer1_paper_llm_test.py` → `freeze_layer1_paper_final_release.py`，目标状态 `BENCHMARK_ADMIT`；Future-Choice-Stress 允许为空。

---

# RQ2 — Why are scalar value and static reservation insufficient?

## B1 · Observation-conditioned obligation family — DONE

| Scale | K∈{1,2,4,8,16}, D∈{1,2,3,4}; 20 cells |
| Core check | conditional frontier = fresh exact action frontier |
| Negative baseline | static union reserve |
| Result | 16/16 nontrivial multi-branch cells static-union false-negative |
| Claim | F1 representation necessity |

## B2 · Shared-opportunity set conflict — DONE

| Scale | K∈{1,2,4,8,16,32}, D∈{2,4,8}; 18 cells |
| Baselines | static union / exact branch / max-flow-min-cut conflict certificate |
| Result | 15/15 nontrivial cells static-union false-negative；branch min-backup stays local while union explodes |
| Role | F1 + set-level conflict mechanism |

---

# RQ3 — Can exact-correct Future-Choice structure be maintained incrementally?

## B3 · Observation-domain reuse — DONE

| Scale | up to 32 branches × 5 observation narrowing levels |
| Comparison | fresh branch frontier rebuild vs persistent conditional domain |
| Result | max fresh 192 builds vs persistent 32 |
| Unit | frontier builds, **not wall time** |

## B4 · Active-branch component invalidation — DONE

| Scale | C∈{2,4,8,16}, 3 obligations/component |
| Events | send→pending, gateway receipt, final ACK, time boundary, global backup-budget change |
| Strong baselines | fresh ordered exact / ordinary persistent exact / dependency-cache exact / incremental conflict frontier |
| Correctness | exact action frontiers agree；incremental structural snapshot = fresh rebuild every event |
| C=16 | fresh exact 866 expansions；persistent/dependency exact 246；separator replay 0；conflict 36 recompute / 62 reuse |
| Role | F2–F3 |

## B5 · Generic core-path parity — DONE

`FutureChoiceEngine + domain adapter` is the only new-experiment orchestration path.

- cross-domain ASC/UAV smoke：DONE；
- frozen N=10 21-seed × 4-policy C main cohort：924/924 frontier exact match，task quality parity：DONE。

Historical domain-local orchestration remains provenance only.

## B6 · Structural holdout — FROZEN / TO RUN

目的：回答 synthetic family 是否只对训练/设计过的 graph motif 有效。

冻结前不得看结果。建议 holdout 不是继续放大 K/C，而是**改变结构**：

1. asymmetric component sizes；
2. overlapping opportunity bridge（components 不再完全 disconnected）；
3. mixed local/global validity events；
4. unseen branch-depth / opportunity-topology compositions。

Correctness authority仍是 fresh exact/fresh structural rebuild。该项优先于继续跑 K=64/128。

结构已冻结于 `B6-STRUCTURAL-HOLDOUT-FREEZE-2026-10-09.{md,json}`：`ASYMMETRIC_DISJOINT / BRIDGED_PAIR / CHAIN_OVERLAP_SPLIT / MIXED_LOCAL_GLOBAL`。执行后不得删除或改写失败 motif。

## B7 · Net wall-time gate — OPTIONAL / CURRENTLY OPEN

只有实际 implementation 在 ordinary persistent exact / dependency-cache exact 下净 wall-time更优，才升级 efficiency claim。否则正文只写 structural/search-work reduction。

---

# RQ4 — Does preserving future choices improve task outcomes outside our benchmark?

## C1 · N=5 robustness — DONE / APPENDIX

| Scan | 1000 seeds |
| Hard-feasible | 107 |
| Result | exact shield / L-U 均消除 heuristic residual failure；depth4 已 107/107，因此 N=5 不支持 method superiority |
| Role | robustness / correctness appendix |

## C2 · N=10 frozen exact-correct main cohort — DONE / MAIN

| Selection | method-independent constructive selector, seeds0..199 → 21 hard-feasible；至少一条官方 heuristic native zero-tardy完成 |
| Policies | 4 official heuristics |
| Strong control | depth4 receding |
| Method | set-MST FutureChoice `L/U + exact fallback` |
| Exact audit | **924/924 reached frontiers** independent exact parity |
| Task result | FutureChoice 4 policies均 21/21 zero-tardy / complete / 0 infeasible；depth4 residual gap按 policy保留 |
| Role | F5 主质量/correctness result |

## C3 · Set-level U-bound attribution — DONE / MAIN

同一 C2 cohort，only change = basic-U → B-inspired deadline-set MST U。

- task quality unchanged；
- exact fallback / pure exact → 11–18%；
- total search proxy / pure exact → 25.8–30.9%；
- relative to basic-U total proxy ≈60% reduction；
- exact-correct Pareto：set-MST dominates basic-U and pure exact search points。

## C4 · External-paper-matched 50-episode panel — DONE / CONTEXT SCALE

**Scale authority来自外部 repo**：其 `evaluate_policy(... episodes=50, seed=999)` 用 `np.random.default_rng(999)` 生成 50 个 fresh layout seeds。我们冻结**完全相同的 seed序列**，不自行用 `999..1048` 近似。

目的：让 reviewer看到在外部论文自己的 evaluation scale/distribution 上发生什么。

### Methods

- 4 official native heuristics；
- depth4 receding；
- generic set-MST FutureChoice。

### Feasibility accounting

- 所有 50 layouts 都进入 distribution-level outcome summary；
- FutureChoice 不得把 hard-infeasible start 写成 method failure；
- hard-feasible status由 exact start check / constructive witness 单独报告；
- exact per-action frontier parity **不在全部50重复执行**，correctness由 C2 冻结 audit承担；可加固定子样本 audit。

### Main metrics

completion / returned / zero-tardiness / tardiness / infeasible / energy + hard-feasible prevalence。

### Frozen result

- exact external `evaluate_policy(... episodes=50, seed=999)` layout-seed sequence：50/50完成；
- official-heuristic constructive hard-feasible **lower bound = 6/50**；该数字只表示“至少这些 layout 有 ordinary constructive witness”，不是 exact feasibility prevalence；
- all-50 native/depth4：
  - NN / BatteryAware：native 3/50 zero-tardy，depth4 10/50；两者 completion 50/50；
  - Greedy：native 6/50 zero-tardy、24/50 complete；depth4 7/50、26/50；
  - NearestDeadline：native 2/50 zero-tardy、14/50 complete、42 infeasible；depth4 7/50、16/50、37 infeasible；
- FutureChoice 只在 6 个 constructive-witness layout 上运行，四条 policy均 6/6 zero-tardy / complete / 0 infeasible；**n=6只作 descriptive，不作大样本 significance claim**。

## C5 · Constructive hard-feasible 100 paired panel — DONE / MAIN SCALE

0..999 method-independent scan：126/1000 seeds被至少一条官方 heuristic native zero-tardy完成；四 heuristic命中计数：NN58 / NDF16 / Greedy98 / BatteryAware58。

冻结：按 seed升序取前100个 constructive witnesses（last seed=812）。

### Purpose

统计稳定性，不重复 C2 的 full exact audit。

### Methods

- native official heuristic；
- depth4 receding；
- generic set-MST FutureChoice。

### Correctness strategy

- initial hard feasibility由官方 heuristic constructive witness保证，不需 exact start search；
- FutureChoice内部仍有 sound L/U + exact fallback；
- **不做100-seed every-frontier independent pure-exact mask**；
- exact parity引用 C2 的 924/924，并可在100中预注册一个固定 audit subset（建议首20个 constructive seeds）做重复确认。

### Statistics

paired per-seed outcome；zero-tardy / completion / infeasible raw counts + Wilson 95% CI；tardiness / energy paired bootstrap；search-work汇总；policy-stratified results。

### Frozen result

前21个 seed **完全等于 C2 frozen exact-audited cohort**；因此 C5 的设计是：

```text
21/100  correctness + exact parity + outcome
79/100  scale / statistical stability only
```

FutureChoice 四条 policy：**100/100 zero-tardy、100/100 complete、0 infeasible**；Wilson 95% lower bound均为 **0.963**。

Depth4 zero-tardy：

```text
NN              87/100
BatteryAware    87/100
Greedy          87/100
NearestDeadline 47/100
```

Completion / infeasible：

```text
NN/BatteryAware   100 complete / 0 infeasible
Greedy             98 complete / 3 infeasible
NearestDeadline    69 complete / 41 infeasible
FutureChoice      100 complete / 0 infeasible (all four)
```

FutureChoice vs depth4 paired zero-tardy：

- NN / BatteryAware / Greedy：`+13pp`，bootstrap 95% CI `[+7,+20]pp`，13/0 favorable/adverse discordance，exact McNemar `p=2.44e-4`；
- NearestDeadline：`+53pp`，95% CI `[+43,+63]pp`，53/0 discordance，exact McNemar约 `2.22e-16`。

Scale run **不新增 every-frontier pure-exact audit**；correctness authority继续是嵌套前21个 C2 seeds 的 924/924 exact parity。

## C6 · N=15 bounded scaling — DONE / APPENDIX ONLY

seed1 exact-audited bounded probe；不得升级为 distribution result。若 C4/C5 完成，不再 brute-force N=15 exact。

## C7 · Learned PPO comparison — OPTIONAL

外部 repo 未随代码发布 checkpoint。除非能获得作者 checkpoint，否则**不重训 PPO 作为主论文门**。可引用外部 paper reported learned results做背景，但我们的 paired shield主比较使用 released official heuristics / receding controls。

---

# RQ5 — Is B→C transfer real rather than two unrelated tricks?

## BC1 · Set-level conflict transfer — DONE

B set-level obligation conflict → C deadline-threshold MST sound U；C3 是直接 attribution。

## BC2 · Shared generic orchestration — DONE

`FutureChoiceEngine` formal C adapter已在 C2 full cohort parity通过。

---

# Paper placement matrix

| ID | Main paper | Appendix | Purpose |
|---|---:|---:|---|
| A1/A2 | ✓ | ✓ | benchmark validity + deterministic landscape |
| A3 | small table / maybe appendix | ✓ | model-spectrum diagnostic |
| A4 | 1 compact case figure | ✓ | failure taxonomy |
| B1/B2 | ✓ | ✓ | representation necessity |
| B3/B4 | ✓ | ✓ | incremental correctness/maintenance |
| B6 | if completed | ✓ | structural generalization |
| C1 |  | ✓ | N=5 robustness |
| C2/C3 | ✓ | ✓ | main external quality + compute result |
| C4 | ✓ or appendix depending signal | ✓ | external-paper scale alignment |
| C5 | ✓ | ✓ | statistical stability on 100 hard-feasible cases |
| C6 |  | ✓ | bounded scaling |
| BC1/BC2 | ✓ | ✓ | one-method synthesis |

---

# Freeze / stop order

优先级固定：

```text
P0  A3 finish → A5 final benchmark release
P1  B6 structural holdout
P1  write theorem/soundness statements + manuscript RQ sections
P2  B7 wall-time gate
P2  learned PPO only if checkpoint becomes available
```

**Scale stop rule 已触发。** 除非 reviewer-style audit发现新科学缺口，停止继续扩大 seed/N；当前规模证据已经覆盖 external-paper 50-episode protocol + 100 hard-feasible paired cases（其中21 exact-audited）+ 1000-seed N=5 robustness + N=15 bounded probe。
