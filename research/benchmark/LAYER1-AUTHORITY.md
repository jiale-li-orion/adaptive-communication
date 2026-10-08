# Layer 1 Authority — Source-grounded Emergency Communication Benchmark

状态：**CURRENT / AUTHORITATIVE**  
冻结依据：`cache06.md` 全文二次收敛（2026-10-04~05）及其已落库实现。  
作用：本文件只拥有 **Layer 1 当前研究对象、边界、已关闭结构、当前工程阶段与下一步执行顺序**。历史讨论、局部 generator 版本、receipt 机制实验均不得覆盖本文件。

## 0. Authority precedence

Layer 1 相关信息发生冲突时，按以下顺序解释：

1. `results/CLAIMS.md`：已经支持 / scoped-negative / formative / retracted 的事实主张；
2. **本文件 `LAYER1-AUTHORITY.md`**：Layer 1 当前研究方向与冻结状态；
3. `../../spec/benchmark/LAYER1-DECISION-BENCHMARK-v0.2.md`：当前 v0.2 environment / observation / action / oracle / graduation 的 normative contract；
4. `BENCHMARK-CONSTRUCTION-PROTOCOL.v0.1.md`：construction / admission / release 方法学；
5. `TASK-SURFACE-REGISTRY.v0.1.json`：Family / task surface / historical closure 的机器可读 authority；
6. `FAMILY-ENVIRONMENT-CONTRACT.v0.1.md`：T1/T2 environment boundary 与 simulator mapping；
7. `BENCHMARK-QUALITY-GATE.v0.1.md`：Q0–Q12 release gate；
8. `SCENARIO-GENERATOR.v0.*`、`V0.5-*`、receipt 文档：版本化机制实验与 regression，不拥有全局方向。

顶层 README、`research/README.md`、`research/benchmark/README.md` 只投影本 authority，不另立研究路线。

## 1. Immutable problem anchor

项目中心保持原始现实需求：

> 灾前山区长期监测中，供电不足、通信链路间歇中断会造成感知节点失联与监测数据无法回传；系统需要在低功耗、低成本条件下维持可恢复、可持续的监测通信。

ASC 是外部学术坐标，不是新的项目中心。项目不改造成“Semantic Communication + LLM”，也不因 Agent / learning 需要而发明通信任务。

三层研究架构冻结为：

```text
Layer 1  Source-grounded Emergency Communication Benchmark
Layer 2  Decision-Semantic Compiler
Layer 3  Policy
```

Layer 1 先定义真实、非退化、可审计的 decision problem；Layer 2 deterministic semantics 拥有 legality / authority / owner / freshness / lifecycle / deadline；Layer 3 才比较 deterministic/search、LLM、learned 或 hybrid policy。

## 2. Layer 1 construct

Layer 1 评测的不是“会不会调用某个工具”，而是：

> 当 Operational Obligation 来自现实来源，合法信息部分可见且会随执行变化，取得信息本身可能消耗时间/机会/资源，Agent 能否在异构通信能力和长期间歇连接下维持后续义务可行性，并由独立 oracle 判断动作与完成状态。

核心对象冻结为：

1. Source-grounded Operational Obligation；
2. Action-relative Evidence Sufficiency；
3. Heterogeneous Capability for Evidence Acquisition；
4. Intermittent Long-Horizon Obligation Feasibility；
5. External Oracle for Action / Completion Validity。

长期方法主线冻结为：

> **可行性冲突指导取证与 context 构造，再用学习扩展求解能力。**

任何新工作若不能推进以下至少一项，默认不进入当前主线：

- 更准确地构造 delivery-feasibility conflict；
- 更准确地判断 evidence 对 feasible plans 的相关性；
- 减少无关 evidence acquisition；
- 在 correctness 可证明前提下安全剪枝 / 加速 policy search；
- 增量维护 decision context / conditional continuation frontier；
- 更严格地验证上述性质。

## 3. Taxonomy：一级 Family 只有两个

### T1 — Monitoring Information Continuity

**MAIN family。** protected subject 是灾前监测信息持续可用。常态、预警升级、退化连接、断链缓存、恢复、多链路、长期低能量属于同一 lifecycle 的 regime / capability / hardness axis。

### T2 — Warning Delivery & Response Handoff

**BOUNDARY / extension family。** protected subject、authority chain、completion predicate 已变化为预警授权、发布、层级送达、确认与 response handoff。当前 source 已足够，但旧 sensor-node environment 缺 actor-chain / multi-recipient / authority-gated state machine，因此保持 `SIMULATOR_GAP`，不得硬塞入 T1。

Family Identity Test 固定看四项：

- protected operational subject；
- completion predicate；
- authority owner / chain；
- lifecycle scope。

warning level、deadline/cadence、outage/reconnect、path/fallback、cache/retransmission、probe、remote configuration、query/tool 名均不能单独升格为 Family。

## 4. T1 operational task surfaces 与 closure

机器可读 authority：`TASK-SURFACE-REGISTRY.v0.1.json`。当前冻结 8 个 T1 surfaces：

| Surface | 当前角色 | Standalone 结论 |
|---|---|---|
| S0 Steady Monitoring | easy / conformance anchor | O1 replay/conformance 已成立，不作 hard-task claim |
| S1 Warning Cadence Transition | workload-arrival axis | O2 standalone config/control 在 A7 已 unique-ready；外部 warning→obligation transition 继续保留 |
| S2 Intermittent Backhaul / Fallback | active composition axis | one-shot permanent recovery、ordinary two-path fallback 已被 reserve/EDF/fallback 覆盖 |
| S3 Energy-Constrained Continuity | resource axis after core | EnergyAware/dynamic-energy 已有强基线；旧 O4 不构成 novelty closure of all energy coupling |
| S4 Outage Cache Retention | state constraint / conformance | DZT0450 ≥7d cache 不允许人为压小造难 |
| S5 Recovery Reconciliation | objective-defined cases only | O5 standalone control 已 unique-ready；backlog-vs-fresh sacrifice priority 未定义时必须 `OBJECTIVE_AMBIGUOUS` |
| S6 Heterogeneous Path Priority | capability/conflict axis | 已知 path priority / fallback 自身不是 hard task |
| S7 Compound Continuity | **primary compositional target** | 历史 O6 只证明 runtime conformance；新组合必须重新过 V0–V9 与 strong baselines |

O1–O6 是历史 T1 regime/template，不是六个一级 Family。它们保留为 conformance、regression、intervention control 和真实 primitive。

T2 当前 3 个 task surfaces：authority-gated publication、hierarchical warning delivery + ACK、progressive call-response / feedback；全部在 T2 environment 建成前保持 `SIMULATOR_GAP`。

## 5. Historical closures：不重跑，但不删除现实机制

以下 standalone 结构已经关闭或降级，不再作为论文 hard-task 重新包装：

- unique-ready TaskContract / config install；
- one-shot permanent terrestrial recovery；
- ordinary outage + two-path fallback；
- standalone cache retention；
- generic recovery/config TTL；
- v0.1 deadline-reserve/EDF degeneracy；
- v0.2 timing-rule-covered first-step selection；
- historical O1–O6 deterministic conformance episodes；
- two-obligation receipt-race 本身；
- 当前 three-obligation receipt-chain 在普通 reserve/fixed-read/wait-ACK 族上的 Pareto saturation。

这些 closure 只关闭**对应结构的 hardness / novelty claim**。对应 warning、outage、cache、path、energy、receipt、recovery primitive 仍进入新的 compositional generator。

## 6. Source / generator discipline

固定 construction 顺序：

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
→ held-out split / scale-up
→ policy evaluation
```

变量 provenance 只有：

- `FIXED_BY_SOURCE`
- `SOURCE_RANGE`
- `EMPIRICAL_TRACE` / `MODEL_DERIVED_TRACE`
- `CONTROLLED_STRESS`
- `UNRESOLVED`

规则：

- `UNRESOLVED` answer-relevant 字段禁止采样；
- `CONTROLLED_STRESS` 必须显式标注，不能冒充现场分布；
- source profile 可以是 partial：**已解决 primitive 可以复用，未解决 task semantics 仍然阻塞对应 case**；
- 不能把 acquisition cadence 偷换成 communication delivery deadline；
- 不能人为编 backlog-vs-fresh priority；
- 不能隐藏公开 geometry；
- 不能由 future truth 编码 current query response；
- 不能用 arbitrary reward weight 生成唯一 gold action。

Oracle 首先做 hard-constraint feasibility，返回全部合法成功 plans / terminal states；source 未定义牺牲顺序时返回 `OBJECTIVE_AMBIGUOUS`，而不是自行 scalarize。

## 7. 当前 generator 权威状态

当前真正的 T1 generator 入口：

- `code/evaluation/benchmark/compositional_recipe_generator_v0_1.py`
- `code/evaluation/benchmark/source_primitive_catalog.py`
- `code/evaluation/benchmark/compositional_generator_scope.py`

当前 source task authority：DB44 reporting table 已解析成 **27 个 source-resolved reporting contracts**。

其中：

- 17 个 contract 的 reporting interval ≤12h，可在当前 48h geometry trace 中形成 core continuous-obligation composition；
- 10 个更长 cadence contract **不删除**，保留为 easy/coverage/trace-horizon-gap anchors。

当前 core pre-oracle universe：

```text
17 task contracts
× 8 geometry opportunity signatures
× 4 service-process classes
× 3 obligation-overlap levels
× 3 resource-headroom levels
× 4 evidence regimes
× 3 recovery regimes
= 58,752 pre-world / pre-oracle candidate recipes
```

分布：

- 14,688 `EASY_CONFORMANCE`
- 14,688 `NEGATIVE_REGRESSION`
- 29,376 `VALIDITY_PENDING`

**这 58,752 个 recipe 不是 benchmark cases。** 它们是 generator universe。v0.2 已完成 dynamic world、causal evidence、full-universe exact reference、V0–V9、strong-baseline shortcut audit、structure-aware split 与 public-test freeze；正式 benchmark release 由当前 Q0–Q12 + Q11 gate 决定，不能把 raw recipe count 当作 release case count。

materialization 当前冻结状态：

- 58,752 recipe → 58,752 world bundles；
- physical world support 与 evidence regime 解耦：steady control 为 1-world；其余 dynamic service process 由 `overlap_count` 决定 bounded support size。当前分布为 14,688 个 1-world、14,688 个 2-world、14,688 个 3-world、14,688 个 4-world bundle；
- 公开 Connecta geometry 在所有 alias worlds 中保持相同，不作为 hidden answer bit；
- dynamic terrestrial schedule、recovery state 与 workload density 保持 `CONTROLLED_STRESS` provenance；
- 9,792 个 validity-pending reconnect bundle 继续携带 `reconnect_backlog_priority` source blocker；
- causal observation/evidence process 已完成：query 只采样 current/past owner state，`sampled_at` 与 `arrived_at` 分离，passive ACK 只由真实 SEND 触发，normal send-as-probe 复用正常发送动作；
- owner query / passive ACK 各覆盖 29,376 个 process；exact reference 已消费同一 causal contract，并完成 29,376 个 `VALIDITY_PENDING` bundles 的 full-universe label projection。

world 机器快照见 `results/benchmark/layer1-world-materialization-v0.1.json`；causal evidence 快照见 `results/benchmark/layer1-causal-evidence-v0.1.json`；exact audit 见 `results/benchmark/layer1-exact-reference-audit-v0.1.json`。语义分别见 `DYNAMIC-WORLD-MATERIALIZATION.v0.1.md`、`CAUSAL-EVIDENCE-PROCESS.v0.1.md`、`EXACT-REFERENCE-ORACLE.v0.1.md`。

exact reference 当前冻结事实：

- 58,752 bundles 中 57,528 为 `ALL_WORLD_SOLVABLE`，1,224 为 `MIXED_WORLD_SOLVABILITY`；后者全部属于 `MONOTONE_RECOVERY_NEGATIVE` controlled-stress cells；
- `VALIDITY_PENDING` 的 216 个结构 cell 已做 deterministic stratified causal exact audit，无 search-limit；
- 四 reference 计数为 `P=216`、`FULL_CURRENT_STATE=216`、`F=204`、`N=189`；189 cell 为 `NO_PAID_QUERY_REQUIRED`，15 cell 为 `PAID_EVIDENCE_REQUIRED`，12 cell 为 `INFORMATION_INFEASIBLE`；
- structural diagnostic 的 `Delta_info = 15/204 ≈ 7.35%` 只说明 generator 存在 genuine EvidenceNeed，不代表最终 benchmark 中 7.35% 的 cases 需要 paid query；
- exact search 在该 audit 中最大 118,660 memo nodes，200,000 上限下 216 cells 全部收敛；
- full-universe exact 求解把 58,752 recipes 压成 9,216 个 solver-equivalent signatures；投影后全 universe 为 53,424 `NO_PAID_QUERY_REQUIRED`、2,562 `PAID_EVIDENCE_REQUIRED`、1,542 `INFORMATION_INFEASIBLE`、1,224 `MIXED_WORLD_SOLVABILITY`；其中 `VALIDITY_PENDING` 为 25,272 / 2,562 / 1,542；
- full label digest 为 `160c0afa17291d4cbeaa5f2bc9fb4d86454016c14a3a696a89218ee6042b8abb`；
- V0–V7 stratified audit 已完成；V9 structural evaluator soundness audit 已通过 216 / 216。V8 必须按 placement 分账：第一层 216-cell audit 中 100 个 cell 被 same-information ordinary baselines 覆盖、116 个存活；`gateway_local_edf_reserve` 对 216 / 216 成功，但它改变 planner placement，只作为 deployment alternative。paid-evidence 全量 signature ladder 已进一步从 416 个 signatures 压到 73 个 survivors，对应 435 个 pre-admission recipes。它们仍不是最终 hard benchmark count。

同理：receipt 188-grid 是 v0.5 mechanism/process audit grid，不是 benchmark case count。

## 8. T1 compositional generator 必须覆盖的结构

核心组合维度冻结为：

```text
multi-obligation release/deadline
× warning-driven workload transition
× finite non-nested terrestrial service opportunities
× intermittent satellite opportunities
× shared real resource/capacity
× outage cache/recovery state
× legal partial evidence + async ACK/query feedback
```

核心稳定后再加入：

```text
source/trace-grounded energy pressure
future authority-published warning transition
```

Hardness 不能由增加无关字段、延长 horizon、删掉真实机会、强制隐藏本地事实、串行化本可并行的 capability 或人为 query 计费获得。

## 9. Observation / evidence / causal solving contract

策略只能使用已经合法到达其 placement 的历史。相同 observable history 必须选择相同行动：

```text
h_t(w) = h_t(w')  =>  pi(h_t(w)) = pi(h_t(w'))
```

必须区分：

- local owner facts；
- passive telemetry / ACK；
- normal send-as-probe；
- paid/remote query；
- query sampled_at 与 arrived_at；
- gateway receipt 与 final center completion；
- historical fact 与基于历史事实形成的当前推断。

至少保留四个 reference：

- hindsight physical feasibility；
- full-current-state oracle；
- observation-matched exact oracle；
- observation-matched no-paid-query oracle。

逐世界可行但不存在共同非预知策略时，应标 `INFORMATION_INFEASIBLE`，不能算算法失败。

## 10. Automatic validity / release gate

V0–V9 冻结为：source complete、solvable、multiple legal options、common-safe-action、observation relevance、binding constraint、outcome separation、objective defined、shortcut audit、evaluator soundness。

典型 disposition：

- `UNIQUE_READY` → Conformance；
- `COMMON_SAFE_ACTION` → 非 EvidenceNeed；
- `OBJECTIVE_AMBIGUOUS` → source research queue；
- `SIMULATOR_GAP` → 扩 environment，不改 task；
- `SHORTCUT_SOLVED` → 降级 / regression；
- `EVALUATOR_INVALID` → 修 evaluator。

真正 `BENCHMARK_ADMIT` 还必须通过 Q0–Q12、source/task audit、结构化 held-out split 与版本冻结。详见 `BENCHMARK-QUALITY-GATE.v0.1.md`。

## 11. Strong baseline floor

后续 candidate 不得只打弱 baseline。至少保留：

- gateway local-autonomy EDF/reserve；
- passive-only；
- normal-send-as-probe；
- fixed / periodic / batch primary+receipt reads；
- myopic conflict/latency or VoI；
- shallow rule combiner；
- true depth-k belief planner；
- receding-horizon planner；
- generic exact / incremental AND–OR with fair memo/early-stop；
- ordinary dependency tracking + cached flow/rebuild；
- full-state / clairvoyant references where appropriate。

若 ordinary mechanism 饱和当前 task-quality / resource / computation frontier，则降低相应 hardness/method claim，不通过增加阶段或筛掉 easy cases 强行制造 headroom。

## 12. v0.5 / receipt work 的正确位置

receipt-race、overlapping receipt chain、joint query–satellite Pareto、resource-conditioned continuation frontier 已经完成重要机制验证：

- genuine EvidenceNeed 可以成立；
- 第一次执行结果可以决定后续是否还需 evidence；
- “可以停止取证保证完成”与“继续取证仍可释放资源”是两个不同 stopping condition；
- exact continuation / Pareto teacher 已有实现。

但当前 ordinary reserve / fixed-read / wait-ACK family 覆盖 frozen receipt-chain 的 exact cost frontier。因此这些工作现在是：

> **H2/H4/H5 mechanism regression + exact-reference infrastructure**

它们不拥有 benchmark taxonomy，不定义最终 case count，也不构成当前算法收益主表。

## 13. 当前唯一主工程

**2026-10-09 paper-framing correction：benchmark release validity 与 method-stress headroom 正式分账。** 2026-10-06 的 hard-survivor audit 仍然成立：174 hard recipes / 41 signatures 全部坍缩到同一 `FINITE_CROSSING_WINDOWS + GATEWAY_SUMMARY_QUERY + H2×H3×H4` mechanism family，且旧 7-signature test 已暴露；但这一事实只否定“benchmark-wide hard-mechanism coverage / Layer-2 method readiness”，不再否定 source-grounded benchmark 的 Operational-Conformance / Interactive-Decision release 价值。同行 benchmark 的成熟做法也是先冻结 task/environment/evaluator/coverage，再把 hardest capability 作为分层 subset，而不是要求每个 task 都让作者方法取得 headroom。

因此 Layer 1 当前状态改为：

> **SOURCE/TASK/EVALUATOR INFRASTRUCTURE ACTIVE / RELEASE-TRACK ASSEMBLY OPEN / FUTURE-CHOICE STRESS SEPARATE / NOT_BENCHMARK_ADMIT**

Gateway action/data-location ownership 已由 `T1-GATEWAY-DATA-LIFECYCLE-CONTRACT.v0.1.md` 与 corrected gateway-backhaul adapter 闭合；它不再是当前 blocker。2026-10-09 的 assistant-led internal source/task/evaluator audit 已完成 23/23 stratified samples × 5 review dimensions；它明确不是 independent expert validation。当前 benchmark-release blockers 固定为：

1. `BASELINE_PROTOCOL_AND_TEST_EVALUATION_OPEN`：新的 150-coordinate test execution cohort 已冻结但 outcome 保持锁定；digest-bound pre-release candidate manifest 已完成。必须先冻结 paper baseline/policy protocol，再允许执行 test 与生成最终 result/release manifest。

已关闭：

- full-sim execution evaluator mutation/replay audit：7/7 当前 release-candidate T1 surfaces 覆盖；
- fresh benchmark execution split：train/dev/test = 200/200/150，test exact identities 在 freeze 前无 tracked result hit；
- Q11 internal source/task/evaluator audit：23/23 × 5 PASS；external independent expert review 未执行并作为 limitation 保留。

方法线单独保留：

- `FUTURE_CHOICE_STRESS_EMPTY`：当前 Layer 1 尚无通过 strong ordinary-baseline headroom 的 stress subset；
- `METHOD_STRUCTURAL_HOLDOUT_OPEN`：未来 Layer-2/3 claim 仍需 pristine structural cohort。

这两项只阻塞 future-choice method claim，不再阻塞 A 作为 benchmark paper 的 release construction。

当前执行顺序固定为：

```text
DB44/T 2457-2024 source correction               [DONE]
   ↳ pre-release profile had Table 15 (ground fissure) values
   ↳ corrected authority = §9.2.2.2 Table 11 (landslide)
   ↳ hazard_type fixed to landslide
→ retry legality / duplicate-free resend semantics       [DONE v0.2]
→ regenerate 58,752 recipe-derived exact labels         [DONE v0.2]
→ regenerate V0–V9                                      [DONE v0.2]
→ rebuild structure-aware split + frozen public test     [DONE v0.2]
→ frozen-split LLM baseline                              [DONE v0.2; DeepSeek 0/7]
→ agentic-reducibility / communication attribution       [DONE 41/41]
→ rebuild Q11 human/source audit package                 [DONE]
→ machine preaudit                                       [DONE 23/23]
→ rerun legacy Q0–Q12 machine checklist                  [DONE 12 PASS / 1 BLOCKED; HISTORICAL CHECKLIST ONLY]
→ hard-survivor failure / coverage audit                 [DONE; COVERAGE REOPENED]
→ freeze method-independent environment/generation contract [DONE v0.1]
→ freeze generation axes before generator execution      [DONE v0.1]
→ dynamic-process generator reconstruction               [DONE v0.6 PRE-ORACLE; r4 reproducible]
→ v0.6 non-anticipative oracle / shortcut admission     [DONE; GLOBAL V3 FAIL]
   ↳ 486/486 stratified pilot cells blind-open-loop solvable
   ↳ 46,770/46,770 physical bases contain ALL_DOWN support
   ↳ TIGHT budget = obligation count on 46,770/46,770 bases
   ↳ 1,262,790/1,262,790 cases inherit full fallback budget
→ freeze corrected v0.7 process-support contract        [DONE]
→ v0.7 method-independent generator                     [DONE PRE-ORACLE; local r1 audited]
→ v0.7 specific v0.6-style shortcut preflight           [DONE; candidate TIGHT shortcut count = 0]
→ placement / visibility boundary                       [DONE FOR OWNER-LOCAL RECEIPT; CENTER GAP RETAINED]
→ gateway-local bounded 36-cell mechanism pilot         [DONE; DIAGNOSTIC ONLY]
→ easy / causal-infeasible bifurcation attribution      [DONE SCOPED DIAGNOSTIC]
→ gateway action/data-location ownership audit          [DONE; CORRECTNESS BLOCKER FOUND]
→ freeze report/data-location + gateway legal actions   [DONE; 53af145]
→ define three paper-facing release tracks              [DONE; 7b7a2d6]
→ assemble semantic track inventory                     [DONE; 7 release candidates / 4 blocked]
→ execution-evaluator mutation/replay audit             [DONE; 7/7 candidate surfaces]
→ freeze fresh benchmark execution split                [DONE; 200/200/150; test locked]
→ internal source/task/evaluator audit                  [DONE; 23/23 × 5 PASS]
→ freeze total pre-release candidate manifest           [DONE]
→ freeze paper baseline/policy protocol                 [PENDING]
→ execute locked test cohort + statistical report       [AFTER PROTOCOL FREEZE]
→ frozen BENCHMARK_ADMIT release                        [AFTER RESULT/RELEASE BLOCKERS]

Parallel method line (not a benchmark-release prerequisite):
→ discover Future-Choice Stress subset                  [OPEN]
→ preregister pristine method structural cohort         [AFTER STRESS CONTRACT]
→ Layer 3 policy/search learning                        [PAUSED]
```

### 13.1 2026-10-05 source correction

Q11 source review uncovered a pre-release extraction error in `DB44T2457_2024_warning_reporting`: the profile had encoded the three monitoring-grade rows from **Table 15 (ground fissure)** while the project story and intended T1 authority are **landslide monitoring**. DB44/T 2457-2024 §9.2.2 explicitly makes reporting frequency depend on geohazard type; §9.2.2.2 Table 11 is the landslide table. The corrected Table 11 values are grade 1 = `1–3d / 6–12h / 4–6h / 30–60min / 5min`, grade 2 = `3–5d / 12–24h / 6–12h / 1–2h / 5min`, grade 3 = `5–7d / 1–2d / 12–24h / 2–4h / 5min`.

The source correction preserves the combinatorial envelope: source expansion remains 27 DB44 reporting contracts, 17 contracts remain inside the ≤12h 48h-core composition, and the recipe universe remains 58,752. It **does change task timing values**. Together with the later retry-legality fix, this invalidated the previous exact/V8/split/LLM lineage. The current machine lineage is `v0.2-retry-legality`; old 73-survivor / 435-recipe / 32-8-33 hard-split / 33-signature LLM numbers are historical only.

Evidence index: `research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md`. Q11 remains human-reviewed after regeneration; the source correction itself cannot be waived by machine consistency checks.

V8 必须区分 **same-information shortcut** 与 **deployment alternative**。gateway-local EDF/reserve 免费使用 gateway 已有 owner-local current state，并改变 planner placement；它是必须保留的强部署对照，但不能与同 placement / 同信息 policy 混成一个 `SHORTCUT_SOLVED` 判据。

retry-legality v0.2 将“可能已经交付”与“禁止再次尝试”分离后，exact full-universe 标签变为：55,008 `NO_PAID_QUERY_REQUIRED`、2,106 `PAID_EVIDENCE_REQUIRED`、630 `INFORMATION_INFEASIBLE`、1,008 `MIXED_WORLD_SOLVABILITY`。相对 pre-retry lineage，594 个 paid-evidence recipes 与 594 个 information-infeasible recipes 转为 no-paid-query；另有 204 个 information-infeasible recipes 转为 paid-evidence。2,106 个 paid-evidence recipes 仍全部来自 `GATEWAY_SUMMARY_QUERY`，说明 ACK 可见性 / receiver retry semantics 是 task contract 的组成部分。

V0–V7 v0.2 覆盖 8,064 / 8,064 solver signatures。`VALIDITY_PENDING` recipes 中：18,252 `COMMON_SAFE_ACTION`、630 `INFORMATION_INFEASIBLE_DIAGNOSTIC`、384 `NO_BINDING_CONSTRAINT`、396 `UNIQUE_READY`、9,714 `V0_V7_PASS`。1,423 个 `V0_V7_PASS` signatures 进入同一 placement-preserving V8 ladder：1,346 个由 cheap policy rule 覆盖、23 个由 finite horizon 覆盖、13 个由 deep horizon 覆盖，最终保留 **41 个 signatures / 174 个 pre-admission recipes**。41 个 survivors 全部属于 `PAID_EVIDENCE_REQUIRED`，且全部集中在 `FINITE_CROSSING_WINDOWS + GATEWAY_SUMMARY_QUERY + overlap 3/4`；`MULTI_WINDOW_DYNAMIC` 已被现有 baseline ladder 覆盖。

41 / 174 仍是 **pre-admission V8 survivors**，不是 benchmark case count。简单、中等、复杂结构继续保留；ordinary mechanism 能解的 cells 用于刻画适用边界。若未来更强的同信息普通策略追平，降级的是对应 hardness / algorithm claim；不得反向发明拓扑、关闭 local autonomy 或删除合法反馈来制造困难。

V9 structural audit 已在 216 个 `VALIDITY_PENDING` 结构代表上通过：合法 physical witness 全部被独立 execution evaluator 接受；no-op、authority violation、虚构 service window、protected-subject corruption 与 missing completion mutation 全部被拒绝。

structure-aware split v0.2 已冻结到 `results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json`：pre-admission pool 为 **30,180 recipes**，train/dev/test = 15,108 / 11,268 / 3,804；hard survivors 为 60 / 90 / 24 recipes，对应 **16 / 18 / 7 signatures**。exact solver-signature cross-split overlap 为 0，component split violation 为 0。public-test identity v0.2 当前冻结 3,804 个 test cases。

旧 Q6 DeepSeek frozen-test baseline 与旧 Q0–Q12 gate 状态均属于 pre-retry lineage，继续只作历史证据。当前 v0.2 已重新运行 DeepSeek Flash frozen-test baseline：7/7 hard signatures 均失败，181 次 API 调用中 0 invalid action，失败全部为 `DEADLINE_EXPIRED`。agentic-reducibility 与 communication-attribution release audit 均在 41/41 hard signatures 上 PASS；Q11 sample 已基于 v0.2 split 重建，machine preaudit 为 23/23 PASS。旧 machine checklist 的结果仍是 **12 PASS / 1 BLOCKED**，但它没有编码最新发现的 hard-mechanism coverage collapse 与 test-exposure provenance，不能再解释成“Q11-only release readiness”。`BENCHMARK_ADMIT` 继续关闭。

最新解释见 `HARD-SURVIVOR-FAILURE-ATLAS.v0.1.md`。机器审计在 41/41 survivors 上为 9 类 ordinary policies 找到明确 first irreversible loss：错误动作既包括 `ISSUE_QUERY`，也包括 `SEND_TERR`、`SEND_SAT` 与 `WAIT`；在同一 prefix 上 exact frontier 存在 preserving alternatives。当前最有价值的结构发现因此是 **premature communication commitment can destroy future completion continuations**，而不是窄化成 query timing。但该结论目前只在 H2×H3×H4 survivor family 上成立，必须由下一版 dynamic generator 扩展/证伪。

生成器的合法输入空间由 [`ENVIRONMENT-GENERATION-CONTRACT.v0.1.md`](ENVIRONMENT-GENERATION-CONTRACT.v0.1.md) 与 generation axes 在执行前冻结。v0.6 使用 `GENERATION-AXES.v0.1.json`；v0.7 只在 `GENERATION-AXES.v0.2.json` 中修正 process-support 语义和预声明的最小 release-stage 条件。baseline / Layer-2 / Layer-3 结果均为 forbidden generator dependencies。该冻结只保证 construction independence，不代表 hardness / mechanism coverage / release admission。

v0.6 method-independent generator 已完成 official clean-tree pre-oracle run r4。生成器从 27 个 DB44 source task cells 出发，51 个合法两流/4–6 obligation compositions 通过 preflight；公开 Connecta trace 在冻结 mask/slice/signature 规则下形成 6,045 个实际 geometry signatures；全量生成 77,556 个 base scenarios，其中 46,770 个 `ALL_WORLD_PHYSICAL`、30,786 个 `MIXED_WORLD_PHYSICAL`。物理全可解 base 按冻结 feedback/query/headroom 轴展开为 **1,262,790 dynamic cases / 499,608 pre-oracle structure IDs**。这些数字是 generation coverage，不是 hard-case count。r2/r3/r4 三次独立生成的 artifact bytes、raw SHA、canonical SHA 与 rows 全部逐项一致；clean r4 manifest 绑定 commit `0ad64380b82ab940bf2ba0cd8c6570583d20d776`。机器证据见 `results/benchmark/layer1-v0.6-preoracle-generation-r4.json`，过程 ledger 见 `GENERATION-RUN-LEDGER.v0.1.md`。

因此 `METHOD_INDEPENDENT_GENERATOR_REBUILD_PENDING` 已关闭；下一门只允许消费 frozen r4 universe 做 oracle / validity / mechanism admission。任何 downstream 结果不得回写 v0.6 generator axes。

### 13.2 v0.6 global shortcut collapse

v0.6 的 generation engineering / reproducibility 通过，但 benchmark validity **失败**。这不是某个 proposed method 的结果，而是 V3/common-safe-action gate 对 frozen r4 的全量构造证明：

1. 46,770 / 46,770 个 `ALL_WORLD_PHYSICAL` base 的声明 support 都包含 `ALL_DOWN` terrestrial world；
2. `TIGHT = max_w(min backup demand)`，而 `ALL_DOWN` 只能靠 satellite 完成，因此 46,770 / 46,770 个 base 都有 `TIGHT = obligation_count`；
3. `BALANCED` 被 cap 到 obligation count，`SLACK_CONTROL` 本身也等于 obligation count，因此 **1,262,790 / 1,262,790 cases** 三种 fallback mode 最终都拥有完整 backup budget；
4. `ALL_DOWN` 被标记为 physically feasible，又意味着 public satellite opportunities 单独就可以调度全部 obligations；
5. satellite geometry / opportunities 跨 worlds 公开且不变，因此同一个 satellite-only schedule 自动成为整个 support 上的 blind open-loop policy。

机器证明：`results/benchmark/layer1-v0.6-shortcut-collapse-r4.json`。独立 486-cell exact pilot 覆盖 composition × service process × capacity × feedback × query-delay × fallback，结果为 **486 / 486 `BLIND_OPEN_LOOP_SOLVED`**，无 search-limit，见 `results/benchmark/layer1-v0.6-oracle-pilot-r4.json`。

因此 v0.6 disposition 固定为：

> **GENERATION_REPRODUCIBILITY_PASS / BENCHMARK_VALIDITY_FAIL / RETAIN_AS_NEGATIVE_LINEAGE**

这个失败不允许通过修改 r4 budget、删除 satellite windows 或手挑 baseline-failure cases 修补。下一版另开 v0.7，只修 `cache06.md` process contract 已经能够证明的语义错误：`SINGLE_RECOVERY` 不再允许“全程 DOWN、从未恢复”冒充 recovery；`REINTERRUPTIBLE` 必须真的含“恢复后再次中断”的支持轨迹；`FULL_BINARY_SUPPORT` 继续保留为 diagnostic upper-support control。fallback budget derivation 保持不变，让 shortcut 是否消失由新 support contract 自然决定。

### 13.3 v0.7 scoped verdict

v0.7 已完成上述 **process-support correction**，并保留 v0.6 的 source task、public geometry、capacity、feedback/query timing 与 fallback derivation。当前本地 audited pre-oracle run `layer1-v0.7-preoracle-r1` 包含 103,408 base scenarios；其中 74,952 个 `ALL_WORLD_PHYSICAL`，展开为 2,023,704 variants / 863,460 pre-oracle structure IDs。它们仍然只是 generation universe，不是 admitted benchmark cases。

cheap construction preflight 的结论严格限定为：candidate `TIGHT` cells 中，v0.6 的“完整 fallback budget + public satellite-only schedule”shortcut 数为 0；`BALANCED` 与 `SLACK_CONTROL` 仍产生预期的 shortcut/control cells。这个结果只说明特定 v0.6 collapse 被修掉，**不证明**：

- 存在 paid-evidence-required hard case；
- query 优于 passive feedback / normal send-as-probe；
- 早期行动形成 non-separable cross-stage commitment；
- dynamic evidence freshness / repeated query 已产生有效差额；
- ordinary baseline 留有任务质量余量。

placement/visibility 审计进一步确认旧 v0.7 oracle adapter 不成立：`receipt_summary` 被按 center-side remote query 计入 terrestrial opportunity/capacity，同时 policy history 又自动收到 gateway receipt；case/base/process schema 没有声明 policy placement，且 center send/control command 没有 transport/timing contract。机器结果见 `results/benchmark/layer1-v0.7-placement-visibility-review.json`，解释见 `V07-PLACEMENT-VISIBILITY-REVIEW.v0.1.md`。

这与 `cache06.md` 的冻结边界一致。随后 [`PLACEMENT-VISIBILITY-CONTRACT.v0.1.json`](PLACEMENT-VISIBILITY-CONTRACT.v0.1.json) / [`V07-PLACEMENT-CONTRACT.v0.1.md`](V07-PLACEMENT-CONTRACT.v0.1.md) 正确冻结了 **policy placement 与 owner-local receipt visibility**：gateway queue、send log 与 receipt 在 gateway 本地可读；center 只能使用已经到达的 telemetry 或合法 query；如果 query 依赖通信路径，send/control command 也不能瞬时抵达。但后续 action-ownership audit 发现，该 contract 中“旧 `SEND_TERR` 可直接作为 gateway-local execution”这一层并未闭合。

- gateway policy placement 是主位置；owner-local `receipt_summary` 不能计作远程 paid acquisition；
- center placement 是独立位置对照；在 telemetry/query/control transport 闭合前不运行 exact；
- v0.7 生成 universe 保留；gateway exact 在 data-location/action-owner contract 闭合前重新关闭；gateway 主位置不产生 paid-remote-receipt EvidenceNeed claim。

旧 mixed-placement partial pilot 结果与 active pilot code 均已删除。新的 gateway-local indexed pilot 只消费 frozen v0.7 universe，并将 remote-query timing 在 placement-specific identity 中折叠；但它现在只作 provisional-kernel diagnostic，不承担 deployment admission。

placement contract 闭合后的 exact admission 固定为**分层求解**，避免给所有 case 同时运行四个昂贵 reference：

```text
blind open-loop exact
  ├─ success → EASY / COMMON_SAFE_CONTROL
  └─ fail
       ↓
full-current-state exact
  ├─ fail → CAUSAL_FULL_CURRENT_INFEASIBLE diagnostic
  └─ success
       ↓
no-paid-query exact（保留 passive ACK / send-as-probe）
  ├─ success → NATURAL_FEEDBACK_SUFFICIENT
  └─ fail
       ↓
observation-matched exact with legal acquisition
  ├─ success → PAID_EVIDENCE_REQUIRED candidate
  └─ fail → INFORMATION_INFEASIBLE diagnostic

任一层 SEARCH_LIMIT → UNRESOLVED_COMPUTATION
```

在扩大 exact sweep 前，必须先冻结 placement/visibility/control-path contract，再从同一个 frozen v0.7 universe 验证四个 mechanism witness：non-separable cross-stage choice、later-observation dynamic sufficiency、dedicated query / passive / send-as-probe competition、以及对应 intervention attribution。若 gateway-local 主位置只能产生自然反馈决策而不能产生 paid remote EvidenceNeed，必须如实缩小 claim；不能通过把 owner-local receipt 重新收费来制造 gap。

当前 provisional gateway kernel 的 bounded pilot 已覆盖 **36 个 placement-relevant TIGHT axis cells**（composition × candidate process × terrestrial capacity × feedback profile；remote-query timing 在 gateway placement 下无效并先行 dedupe）。50k memo contract 下原始结果为：18 `BLIND_OPEN_LOOP_SOLVED`、8 `FULL_CURRENT_CAUSAL_INFEASIBLE`、2 `GATEWAY_NATURAL_FEEDBACK_REQUIRED_CANDIDATE`、8 `UNRESOLVED_COMPUTATION`。两个 natural-feedback candidate 均被 same-information `myopic_flow_voi` 与 depth-2/3 flow baseline 解掉，因此 provisional disposition 为 **18 blind control / 8 causal-infeasible diagnostic / 2 ordinary-baseline shortcut / 8 unresolved / 0 resolved baseline survivor**。机器结果见 `results/benchmark/layer1-v0.7-gateway-pilot-v0.1.json`。它现在只作 scoped diagnostic；不能作为 gateway deployment hard-case count，也不能把 8 个 unresolved 当成 hardness。

进一步的 bifurcation attribution 证明：pilot 实际 stage count `{3,4,6}` 下 `SINGLE_RECOVERY` 全部具有共同 final-UP stage，而 `REINTERRUPTIBLE` 没有共同 UP stage；8 个 TIGHT full-current causal-infeasible cells 去掉 second-outage worlds 后 **8/8 立即变为 blind-open-loop solvable**。机器结果见 `results/benchmark/layer1-v0.7-gateway-bifurcation-v0.1.json`。这说明 process support 确实造成 easy / causal-infeasible 二分，但仍只是 provisional-kernel attribution。

更上游的 action-ownership audit 随后发现 correctness defect：`SYSTEM-MODEL-v1` 明确区分 node uplink、gateway queue/backhaul 与 center delivery；v0.5 的 `SEND_TERR` 语义是发送后出现 gateway receipt、再出现 center final ACK；而当前 gateway adapter 将该 `SEND_TERR` 直接声明为 gateway-local action。机器结果见 `results/benchmark/layer1-v0.7-gateway-action-ownership-review.json`，解释见 `V07-GATEWAY-ACTION-OWNERSHIP-REVIEW.v0.1.md`。因此上述 gateway pilot/bifurcation **降级为 diagnostic**；正式 gateway exact 重新关闭，当前唯一主工程改为 data-location/action-owner closure。

V8 的 baseline 分类与否决边界见 `V8-BASELINE-CONTRACT.v0.1.md`。generic exact / memo / dependency-cache / incremental AND–OR 属于 computation reference：它们取得 exact 任务质量是预期结果，不能因为“确定性算法能解”再次否定 benchmark；当前 16-cell computation reference 中 generic exact 平均约 54.6 ms、最大约 280.7 ms，no-paid-query 平均约 503.8 ms、最大约 4.0 s。这些数值只作为后续方法公平计算基线。

## 14. Layer 2/3 的下一步边界

Layer 2 已有 deterministic mechanism / correctness 资产继续保留，但**暂停以当前 41-signature survivor set 继续驱动 Layer 3 learning 或 search-ranking 优化**。当前优先级重新服从 `cache06.md`：先让 Layer 1 的动态过程与结构覆盖闭合，再讨论 learning。

Layer 1 generator 的修改只能由 source/task contract、已声明的 process semantics、failure analysis 与 benchmark validity 触发；不得读取 proposed method outcome 反向挑 case。Layer 2/3 也不得修改 source-owned deadline、合法能力、public geometry、authority 或 observation ownership 来制造 headroom。

下一版 generator 完成后，Layer 2 必须重新回答：

1. 哪些 ordinary baseline failure 可以由统一的 future-choice / option-destruction structure 解释；
2. 哪些结构其实被 passive feedback、send-as-probe、短 horizon 或 local autonomy 解决，应当降级为 control；
3. 哪些新的 dynamic-process states 需要 deterministic feasibility representation；
4. 该 representation 在未见 conflict topology / event interleaving 上是否仍有效。

只有这些问题闭合后，Layer 3 才允许重新启动。
