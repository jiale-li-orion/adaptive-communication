# Literature / Paper-Gap Audit — 2026-10-09

状态：**current paper-positioning audit / derived from full-paper reread + current repo evidence**。

用途：回答两个问题：

1. A/B/C 现在做下来的对象是否真的和 2025–2026 同期工作区分开；
2. 论文应该怎样组织实验和写作，才能避免“benchmark + toy method + unrelated UAV”三块拼盘。

本文件不拥有 claim state。正式 claim 只认 `results/CLAIMS.md` B* / F1–F7。

---

## 1. 同期工作重新定位

### 1.1 6G-Bench — benchmark construction 已经占据“标准驱动 semantic reasoning”

Reference: `arXiv:2602.08675`, **6G-Bench: An Open Benchmark for Semantic Communication and Network-Level Reasoning with Foundation Models in AI-Native 6G Networks**.

它的强项不是 executable closed-loop control，而是完整的 benchmark construction discipline：

```text
standards / standardization activities
→ 30-task taxonomy
→ existing multi-turn UAV/network episodes
→ semantic state + action abstraction
→ oracle decision / truncated trajectory
→ task-conditioned item construction
→ automatic filtering + expert validation
→ broad model panel + task/category analysis
```

因此 A 不应写：

- “第一个 standard/source-grounded semantic-communication benchmark”；
- “第一个 network-level reasoning benchmark”；
- “第一个 multi-turn 6G semantic benchmark”。

A 的真正差异：

> **field/standard/procurement requirement → executable operational obligation → causal communication environment → final operational outcome evaluator**。

即：A 不把 episode 截成 decision MCQ；动作真的改变队列、能量、配置、链路、ACK 与后续 obligation completion。

写作学习：6G-Bench 的 taxonomy/construction/validation/model-study 四段非常值得照搬组织方式；不要把内部几十轮纠错 history 写进主文，只把它们压成 benchmark validity methodology。

### 1.2 WirelessBench — 学习“能力分层 + 风险型评分 + failure taxonomy”

Reference: `arXiv:2603.21251`, **WirelessBench: A Tolerance-Aware LLM Agent Benchmark for Wireless Network Intelligence**.

它把 benchmark 明确拆成三层 cognitive hierarchy，并把设计原则横向展开为 tolerance-aware scoring、tool-necessary task、trajectory diagnosis。更重要的是，它不靠一个 aggregate score，而是主动回答：

```text
模型是知识不会？
工具没用？
链式传播错？
单位/数量级灾难错？
```

其 quality-assurance pipeline 还包含 deterministic verification、deduplication、difficulty calibration、stratified human validation 与 psychometric-inspired filtering。

对 A 的直接启示：

- 我们把 `Operational-Conformance / Interactive-Decision / Future-Choice-Stress` 分轨是对的；
- “ordinary baseline saturation” 应当写成 benchmark finding，而不是删题理由；
- failure taxonomy 比“谁 TDR 高”更重要；
- execution evaluator mutation audit + source/task audit 应进入 methodology 主文，不要藏 appendix。

差异边界：WirelessBench 的 Tier 3 仍是 predefined multi-step chain / tool-augmented structured output；A 的核心是 **physical lifecycle + final obligation state**，不是 tool use 本身。

### 1.3 DORA — 学习“真实 operational task + step/final 双层评测”

Reference: `arXiv:2605.11633`, **Can LLM Agents Respond to Disasters? Benchmarking Heterogeneous Geospatial Reasoning in Emergency Operations**.

DORA 的 paper construction 非常接近 A 在“operational realism”层面的理想写法：

- 45 real disaster events；
- 515 expert-authored operational tasks；
- 108 tools；
- expert-verified replayable trajectories；
- trajectory/tool/parameter + final answer 双层 scoring；
- 失败按 damage grounding / modality mismatch / pipeline composition 归因；
- ablation 不只换模型，而是给 gold tool-order hint，定位 residual argument-grounding failure。

对 A 的启示：

> paper 不需要证明每条任务都有新 algorithm headroom；benchmark 本身靠 operational task validity、environment/tool/data contract、step/final evaluator 与 failure diagnosis 成立。

对我们更重要的是：DORA 的 gold trajectory 很强，但它仍以 expert trajectory 作为重要 reference；A 可以强调 **final-state / obligation evaluator 接受多条合法 execution trajectory**，这是我们更接近 `τ-bench / OSWorld` 的地方。

### 1.4 Pull-Based Query Scheduling — B 的直接 ASC anchor，但不是 novelty 本身

Reference: `arXiv:2503.06725`, IEEE TCOM 2026, **Pull-Based Query Scheduling for Goal-Oriented Semantic Communication**.

已覆盖：

- hub 主动查询 sensing attributes；
- knowledge / AoI-style state；
- long-term expected semantic effectiveness；
- query-cost constraint；
- model-based dynamic programming；
- model-free DRL；
- GoE / CPT 风险敏感 effectiveness。

因此 B 不能 claim：

- “首次主动 query”；
- “首次 query-cost constrained semantic scheduler”；
- “首次长期 semantic effectiveness”；
- “query only when it matters to goals”。

B 的合法扩展恰恰是当前 F1–F3：

> scalar effectiveness objective 下再加 **hard operational completion feasibility**；未来 hard obligations 可以在未来 observation 后才 branch-activate；因此 static union reserve 会 false-negative，certificate 必须 observation-conditioned 并带 validity/dependency domain。

### 1.5 WM-CDT — 已占据“long-horizon + counterfactual semantic value”

Reference: `arXiv:2605.16547`, **World Model-Enabled Causal Digital Twins for Semantic Communications in Physical AI Systems**.

其问题已经明确是 closed-loop sensing–communication–inference–control，并用 world model / counterfactual rollout 评估 semantic token 对长期 return 的 causal contribution（CIV），最终优化 return-per-bit。

因此我们不能写：

- “现有 semantic communication 都是一拍脑袋的 instantaneous value”；
- “首次把 semantic communication 放进 long-horizon physical control”；
- “首次 counterfactual semantic value / causal effect”。

我们的区分：

```text
WM-CDT: scalar expected long-horizon return / token value

Future-Choice:
  hard obligation completion set
  non-anticipative observation-conditioned branches
  L=1 replayable completion witness
  U=0 sound impossibility certificate
  certificate validity / dependency-local invalidation
```

即：**value optimization 与 hard feasibility preservation 是两个不同对象**。

### 1.6 Goal-Oriented Semantic Communication for Logical Decision Making — 已占据 decision-state / evidence sufficiency

Reference: `arXiv:2604.19614`.

该工作用 FOL world representation、goal-oriented states 与 semantic information bottleneck 选择对 decision 最关键的 clauses，并强调 logical verifiability。

因此我们不能把“action-relative evidence sufficiency / 只发送影响决策的信息”本身写成 novelty。

Future-Choice residual：**当前 decision sufficient 仍不等于当前 action 会保留未来 hard completion choices**。

### 1.7 Wireless Context Engineering — 已占据 dynamic context orchestration

Reference: `arXiv:2602.07321`.

它明确把 inference-time context filtering / structuring / injection 延伸到 wireless edge intelligence，并讨论 sensing、latency、energy、memory constraint。

所以旧 Agentic line 的“dynamic context engineering”不能再做主 novelty。它现在最合适的角色是 runtime/implementation background；当前主方法对象应是 **future-feasibility certificate**，不是 context 本身。

### 1.8 Active Measuring with Delayed Negative Effects — “测量会伤害未来”也不是 novelty

Reference: AISTATS 2026, **Active Measuring in Reinforcement Learning With Delayed Negative Effects**.

该工作已经形式化 measurement action 既减少 uncertainty、又可能对 future outcome 产生 delayed negative effects。

因此不能 claim：

- “首次发现 query/measurement 不是免费”；
- “首次考虑 measurement 的 delayed negative effect”。

我们的残差更窄：

> action/query 不只是带来一个 delayed scalar penalty，而是可能改变 **哪些 hard obligations 仍存在共同可完成 continuation**；这一集合随 observation branch、shared opportunity 与 execution feedback 动态变化。

---

## 2. ABC 是否跑偏

结论：**没有跑偏，但主语必须从“Agentic Communication system”进一步收缩为“Future-Choice feasibility”。**

### A 没跑偏

cache05/cache06 反复要求：task/source/evaluator 先于 method；不为方法事后造 scarce resource；ordinary method 能解就诚实保留负结果。

当前 A 已经做到：

- source-grounded operational surfaces；
- physical execution lifecycle；
- evaluator mutation audit；
- ordinary baseline saturation controls；
- benchmark validity 与 method hardness 分账。

A 现在应该停止继续找“让方法赢的 emergency task”，专心做 release/failure analysis。

### B 没跑偏，而且终于从旧 Agentic/context line 收敛到 cache06 真正想要的对象

cache06 当时最严格的 reviewer checklist：

```text
集合级 conflict，不是逐 obligation mandatory
certificate 有 validity domain
event-local invalidation
observation branch conditionality
strong ordinary persistent/dependency exact
exact fallback
不把不同 work unit 冒充 wall-time speedup
```

现在 F1–F3 已逐项兑现。当前未过的只剩：generic net wall-time superiority 与更广 structural generalization；这属于 claim ceiling，不是方向错误。

### C 没跑偏，但必须一直保持“external mission validation”身份

C 证明：

- native local legality 真的会删除 full continuation；
- strong depth-k control 有 residual failure；
- exact-correct L/U safety layer 有任务质量收益；
- B 的 set-level conflict principle 可以形成 C 的 sound U-bound 并减少 fallback search。

只要不把它写成 emergency-communication benchmark，C 就非常干净。

---

## 3. 现在真正剩下的 scientific gap

### Gap 1 — net wall-time / system cost

当前我们可以写：

```text
structured recomputation reduction
exact-fallback state reduction
branch/frontier build reduction
```

不能写：

```text
faster planner
lower end-to-end latency
more computationally efficient overall
```

除非 generic implementation 在强 persistent exact / depth-k baseline 下通过净 wall-time 门。

### Gap 2 — structural generalization beyond hand-designed stress families

B 的 synthetic family 是 mechanism attribution，很干净，但 reviewer 会问：

> 这些 branch / conflict pattern 是否只对你设计的图有效？

当前最强回答是 C external mission + B→C set-level transfer。若还要补一刀，优先补**结构 holdout**，不是再扩 K/D 数量。

### Gap 3 — theorem / soundness statement需要收紧成很小但明确

不需要大而全理论。真正值得写的 theorem/lemma：

1. replayable causal policy ⇒ `L=1` sound；
2. optimistic relaxation infeasible ⇒ `U=0` sound；
3. deadline-set MST 的 `U=0` soundness；
4. dependency-disjoint event 不改变 component certificate（在声明的 contract 下）。

这四条足够支撑方法 correctness narrative。

---

## 4. 推荐论文实验组织：按 research question，不按 A/B/C 三篇拼盘

### RQ1 — Is the operational benchmark valid, and are all realistic tasks actually hard?

用 A。

主结果：source/task/evaluator validation + deterministic baseline spectrum + negative saturation cases + LLM model-spectrum appendix/subtable。

结论：很多 realistic emergency tasks ordinary-solved；benchmark 不为方法裁题。

### RQ2 — When does scalar value/static reservation fail?

用 B F1。

主实验：Pull-Based-style conditional family + shared-opportunity family。

对照：value-only / static-union / exact contingent policy。

### RQ3 — Can Future-Choice certificates be maintained incrementally without sacrificing correctness?

用 B F2–F3。

主实验：fresh exact / persistent exact / dependency-cache exact / conflict frontier；observation narrowing + active branch events。

指标：exact frontier match、frontier builds、component recompute/reuse、exact expansions。明确不把不同 work unit混成 CPU ratio。

### RQ4 — Does preserving future choices change real task outcomes outside our benchmark?

用 C F4–F5。

主实验：native heuristic / depth-k receding / exact shield / L/U shield。

指标：zero-tardiness、completion、infeasible、energy、search proxy、frontier exact match。

### RQ5 — Does the representation transfer, or are B and C two unrelated tricks?

用 F6–F7。

主实验：basic U → set-level deadline MST U 的 attribution；generic FutureChoiceEngine cross-domain audit。

这是把整篇论文真正焊起来的一问。

---

## 5. 写作结构建议

不要写成：

```text
Section 3: our benchmark
Section 4: our ASC method
Section 5: our UAV experiment
```

更好的主文顺序：

```text
1 Introduction
2 Operational problem + why value/local legality is insufficient
3 Source-grounded evaluation construction (A, compressed)
4 Future-Choice formulation and L/U certificate method (B)
5 Experiments organized by RQ1–RQ5
6 Related work / limitations
```

A 的工程细节大量放 appendix/artifact；主文只留下“为什么它是 reality authority + ordinary baseline falsifier”。

### 5.1 从同期论文全文学到的实验组织

这一轮不只看摘要，重新读了 6G-Bench、WirelessBench、DORA、Pull-Based Query Scheduling 与 WM-CDT 的完整公开正文/HTML。最值得复用的不是术语，而是它们如何把“一个复杂系统论文”拆成 reviewer 可以逐项验证的问题。

#### 6G-Bench：construction validity 先于 model ranking

其主结构非常清楚：

```text
standardization-driven taxonomy
→ semantic state/action abstraction
→ task-conditioned construction
→ automated filtering
→ expert validation
→ frozen evaluation protocol
→ model panel / task-level / group-level / robustness analysis
```

对 A 的直接要求：source/task/evaluator/split/protocol 必须在“谁表现更好”之前讲完。A 的 internal correctness history 不要逐版本展开，而应压成 design/QA pipeline：source provenance、shortcut red-team、placement/ownership correction、execution-evaluator mutation、fresh split、frozen protocol。

#### WirelessBench：不要只报 aggregate score，要把 benchmark 本身当可审计系统

WirelessBench 的完整正文依次给出：

```text
three-tier capability hierarchy
tolerance-aware scoring
tool-necessary tasks
traceability
data construction
psychometric cleaning
human validation
difficulty calibration
main evaluation
metric sensitivity
failure-mode decomposition
```

其 appendix 还明确列 rule-based filter、multi-model response matrix、hierarchical grading、dedup、difficulty calibration 与 stratified human review。

对 A 的启示：

- `Operational-Conformance / Interactive-Decision / Future-Choice-Stress` 应像 capability hierarchy 一样在主文前半段就出现；
- evaluator mutation / internal source review / negative shortcut findings 是 benchmark methodology，而不是“补充材料里的自我辩护”；
- 结果节必须有 failure decomposition：collection miss、delivery miss、energy exhaustion、backhaul opportunity miss、task-revision failure、model/runtime failure；
- LLM 子集只是 model-spectrum diagnostic，不应该盖过 deterministic mechanisms 的 attribution。

#### DORA：用 ablation 判断失败层，而不是只比较 agent 名字

DORA 的强点是 expert task design + deterministic replay，把 symbolic trajectory 解析成真正执行结果；结果又分别看 tool selection/order/parameter accuracy/final answer，并用 gold tool-order hint、Plan-then-Execute、Reflexion、ReWOO 等 intervention 追问“失败到底来自哪里”。

对 A/C 的启示：

- A 应当选 2–3 个完整 lifecycle case study，把 operational failure 沿 sample→gateway→center→obligation completion 追到底；
- C 的 depth-k / exact shield / L-U / set-MST attribution 不是“多几个 baseline”，而是 failure-layer ablation：local mask、short horizon、exact continuation、structured U-bound；
- 论文结果 section 应优先解释 residual failure source，而不是按算法名逐行念表。

#### WM-CDT：通信论文的 method evaluation 应分“效果、成本、metric validity、ablation”

WM-CDT 的 simulation section 是很标准的通信论文组织：

```text
realistic simulator
system/hyperparameter table
convergence
computational complexity
task performance under resource budget
robustness to packet error
metric-vs-counterfactual-ground-truth validation
module ablations
```

尤其值得学的是它单独验证 CIV 与“true counterfactual return gain”的相关性，而不是只展示最终 policy reward。

对应到我们：

- Future-Choice 的 `L/U` 也必须单独验证 **certificate correctness**，不能只报 zero-tardiness；现有 924/924 frontier match、B fresh rebuild match、generic engine audit正是这类证据；
- compute 需要单列：fresh/persistent/dependency exact、depth-k、basic-U、set-MST-U，不与 task quality 混成一个 weighted score；
- set-MST 应作为 module ablation/attribution：任务质量不变，只改变 U-bound 后 exact fallback/search proxy显著下降。

#### Pull-Based：强近邻要按它自己的目标和 solution class 公平比较

Pull-Based 正文明确是：GoE（freshness + usefulness）→ CPT long-term effectiveness → query-cost constrained CMDP → model-based dynamic programming + model-free DRL → cost/scalability evaluation。

因此 B 的实验不能只拿一个 value-only greedy 当对手。当前正确的 baseline ladder是：

```text
scalar/value objective
static union/resource reserve
generic constrained exact
ordinary persistent exact
dependency-cache exact
conditional conflict frontier
```

其中 ordinary persistent/dependency exact必须保留，因为它们是真正 reviewer-grade systems control。

### 5.2 推荐主文 Results 按 RQ 而不是按代码模块排

```text
RQ1 Benchmark validity / ordinary saturation         ← A
RQ2 Why value/static union is insufficient           ← B F1
RQ3 Exact correctness + persistent/local maintenance ← B F2–F3
RQ4 External task-quality headroom vs depth-k         ← C F4–F5
RQ5 Cross-domain transfer / set-level attribution     ← F6–F7
```

这样 A/B/C 看起来是一个因果证据链，而不是三份项目报告拼接。

### 5.3 主表数量要克制，appendix 要丰富

建议主文只保留：

1. A benchmark taxonomy / validity table；
2. B ASC representation + strong-baseline work table；
3. C N=10 correctness–compute frontier table；
4. B→C set-MST attribution ablation；
5. A LLM spectrum 作为小表或 appendix，除非结果本身很有诊断价值。

appendix 再放 source audit、mutation cases、完整 baseline matrix、N=5 robustness、N=15 bounded probe、全部 model/runtime trace summary。

---

## 6. 当前最稳的一句话

> **Future-Choice is not a new semantic value metric. It is an explicit representation of whether a current communication or information action preserves at least one non-anticipative way to complete all outstanding hard operational obligations under future observations and shared opportunities.**

这句话同时避开 Pull-Based GoE、WM-CDT CIV、Wireless Context Engineering、logical decision-state sufficiency 与 generic active measurement 的 novelty 区域。
