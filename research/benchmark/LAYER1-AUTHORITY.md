# Layer 1 Authority — Source-grounded Emergency Communication Benchmark

状态：**CURRENT / AUTHORITATIVE**  
冻结依据：`cache06.md` 全文二次收敛（2026-10-04~05）及其已落库实现。  
作用：本文件只拥有 **Layer 1 当前研究对象、边界、已关闭结构、当前工程阶段与下一步执行顺序**。历史讨论、局部 generator 版本、receipt 机制实验均不得覆盖本文件。

## 0. Authority precedence

Layer 1 相关信息发生冲突时，按以下顺序解释：

1. `results/CLAIMS.md`：已经支持 / scoped-negative / formative / retracted 的事实主张；
2. **本文件 `LAYER1-AUTHORITY.md`**：Layer 1 当前研究方向与冻结状态；
3. `BENCHMARK-CONSTRUCTION-PROTOCOL.v0.1.md`：construction / admission / release 方法学；
4. `TASK-SURFACE-REGISTRY.v0.1.json`：Family / task surface / historical closure 的机器可读 authority；
5. `FAMILY-ENVIRONMENT-CONTRACT.v0.1.md`：T1/T2 environment boundary 与 simulator mapping；
6. `BENCHMARK-QUALITY-GATE.v0.1.md`：Q0–Q12 release gate；
7. `SCENARIO-GENERATOR.v0.*`、`V0.5-*`、receipt 文档：版本化机制实验与 regression，不拥有全局方向。

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

**这 58,752 个 recipe 不是 benchmark cases。** dynamic world、causal evidence 与 full-universe exact reference labels 已完成；当前仍未完成 V0–V9、strong-baseline shortcut audit、structural split 与 Q0–Q12，因此不能称 benchmark cases。

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

当前 Layer 1 尚未完成。下一步执行顺序冻结为：

```text
DB44/T 2457-2024 source correction               [DONE]
   ↳ pre-release profile had Table 15 (ground fissure) values
   ↳ corrected authority = §9.2.2.2 Table 11 (landslide)
   ↳ hazard_type fixed to landslide
→ retry legality / duplicate-free resend semantics       [DONE v0.2]
→ regenerate 58,752 recipe-derived exact labels         [DONE v0.2]
→ regenerate V0–V9                                      [DONE v0.2]
→ rebuild structure-aware split + frozen public test     [DONE v0.2]
→ frozen-split LLM baseline                              [DEFERRED]
→ rebuild Q11 human/source audit package                 [PENDING]
→ rerun Q0–Q12                                           [AFTER Q11]
→ frozen BENCHMARK_ADMIT release
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

旧 Q6 DeepSeek frozen-test baseline 与旧 Q0–Q12 gate 状态均属于 pre-retry lineage，当前不再作为 release evidence。按当前决策暂不重跑 LLM；Q11 需要基于 v0.2 split 重新抽样并由真实 reviewer 完成 source/task/oracle/evaluator 核查。`BENCHMARK_ADMIT` 仍保持关闭。

V8 的 baseline 分类与否决边界见 `V8-BASELINE-CONTRACT.v0.1.md`。generic exact / memo / dependency-cache / incremental AND–OR 属于 computation reference：它们取得 exact 任务质量是预期结果，不能因为“确定性算法能解”再次否定 benchmark；当前 16-cell computation reference 中 generic exact 平均约 54.6 ms、最大约 280.7 ms，no-paid-query 平均约 503.8 ms、最大约 4.0 s。这些数值只作为后续方法公平计算基线。

## 14. Layer 2/3 的未来方法方向

Layer 1 稳定后，主方法对象是：

> **resource-conditioned causal continuation frontier / feasibility-conflict frontier**

Context 应保留“未来选择”而不是只回答当前动作。方法应维护哪些后续方案仍可行、依赖哪些 evidence / resource condition、什么事件使证书失效，以及何时必须 query / wait / send / fallback / exact-replan。

最终希望证明的不是“少两个 query”本身，而是：

- 同任务质量、同合法信息条件下更低在线规划成本；或
- 同计算预算下更接近 observation-matched exact；或
- 同质量下减少真实取证且不把成本转移到其他资源；或
- 在现实允许的通信/计算预算下扩大可完成任务区域。

这部分不得反向修改 Layer 1 generator 以迁就方法。
