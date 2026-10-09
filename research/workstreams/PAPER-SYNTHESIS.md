# Paper Synthesis — Preserving Future Choices in Agentic Communication

状态：**CURRENT PAPER STORY / claims not yet final**
日期：2026-10-09

这不是第四个 Layer。它只把 A/B/C 三条 workstream 组合成一篇论文的共同问题、证据链和剩余门槛；正式 benchmark / method ownership 仍分别属于 Layer 1 / Layer 2。

## 1. One-sentence problem

> **A communication or information action is not only valuable for what it reveals or delivers now; it can also preserve or destroy the set of future ways in which outstanding operational obligations can still be completed.**

现有 semantic value / GoE / VoI、one-step action mask、short receding horizon 都可能只回答“当前动作有多好 / 当前能不能执行”，而没有显式表示：

```text
take action a under history h
→ future observation z arrives
→ which obligation/resource continuations remain feasible?
```

核心对象因此不是单个 scalar value，而是 **observation-conditioned future completion set / frontier**。

## 2. Three workstreams, one paper role each

### A — Reality and benchmark authority

A 的职责不是给方法“造一道会赢的题”，而是定义现实 task、执行环境和 outcome evaluator，并对方法进行反作弊。

当前已经完成：

- 11 个 canonical operational surfaces；
- 7 个 paper release-candidate T1 surfaces；
- `Operational-Conformance / Interactive-Decision / Future-Choice-Stress` 三轨；
- source → obligation → lifecycle → evaluator provenance；
- full-sim evaluator mutation audit 覆盖 7/7 release surfaces；
- fresh execution split `200 train / 200 dev / 150 test`；
- 23/23 × 5 internal source/task/evaluator audit；
- digest-bound pre-release manifest；
- baseline/policy protocol 已在 test outcome 打开前冻结。

最重要的科学结果不是“所有真实 task 都很 Agentic”，而是相反：

- gateway natural-feedback candidate 可被 myopic/depth-k flow 吃掉；
- persistent-energy commitment 可被 `ResourceGate` 吃掉；
- shared-backup stress 可被 maxcov/packing 吸收；
- T2 warning-chain task 很真实，但 source 并没有授权我们事后发明 contact quota 来制造 hardness。

因此 A 给论文一个非常关键的可信度：**future-choice 不是通过反向修改 emergency benchmark 才出现的。**

当前 A 的 150-coordinate deterministic test 已按 frozen protocol 完成并提交 aggregate / statistical / failure evidence；剩余的是 frozen 30-coordinate × 2 context-mode LLM subset、联合统计/失败 taxonomy 与 final release manifest。该 LLM 子表只补 model spectrum，不承担 Future-Choice 方法主张。

### B — Direct ASC method formulation

B 直接回答“future-choice 在已有 ASC formulation 中是否是一个独立对象”。

当前证据链：

1. **Value ≠ feasibility**：Pull-Based Query Scheduling 风格 AoI/query/GoE replay 中，current value policy 在相同当前 state 下会因 future hard-goal geometry 不同而从 safe 变 unsafe；future-choice shield 保持 constrained exact optimum。
2. **Static union is wrong**：observation-conditioned future obligations 不能把所有可能 branch obligation 静态并集。最小 probe 中 `QUERY_H` 有 causal contingent policy，而 static union reserve 错误拒绝。
3. **Shared-opportunity conflict**：`K∈{1,2,4,8,16,32}` branches × `D∈{2,4,8}` obligations；每个真实 branch 的 min backup 始终为 1，K>1 的 15/15 cells static-union false-negative；`K=32,D=8` union 被夸成 min-backup=249。
4. **Structured computation**：branch 内复用 Layer-2 max-flow/min-cut conflict certificate。D=8 时 exact branch search 约 778 memo states / branch，而 deterministic flow graph只有 71 forward edges；这是 structural-work proxy，不是 wall-time claim。
5. **Persistent conditional domain reuse**：L=5/K=32 多次 semantic observations 的完整 scenario tree 上，fresh branch-aware flow 需要 192 次 frontier builds，persistent conditional domains 只建 32 次，build ratio `1/6`；observation 只缩 support 时证书保持，backup budget 跨 validity boundary 时只失效 realized active branch。

B 已经支持的最强 claim：

> **Future obligations and resource conflicts must be represented conditionally on future observations; static worst-case unions can reject valid causal policies, while persistent conditional domains avoid repeated structural reconstruction.**

尚未支持：generic Layer-2 algorithm 在完整 dynamic shared-resource problem 上的最终 wall-time superiority。active branch 的 time/resource/pending-feedback component-local invalidation gate 已关闭，并补了 ordinary persistent exact / dependency-cache strong ladder；当前更准确的边界是：**structured recomputation / exact-fallback work 已有明确下降，净 wall-time superiority 仍然 OPEN。**

### C — Independent external mission validation

C 不承担 emergency-communication domain claim；它负责证明 future-choice 不是 A 自建环境特供。

外部公开 `uav-attention-routing` 原生包含 customer deadlines、persistent battery、charger、depot return、finite horizon 和 action mask。

证据链：

1. native mask 只保证 one-step reachability；seed24 存在 zero-tardiness full route，但 native-mask-allowed action 会删除全部 full continuation，四条官方 heuristic 都会选入 destructive action set。
2. exact continuation shield 在 N=5 / 1000 seeds 的 107 个 hard-feasible episodes 上，把四条 heuristic 全部修到 107/107 zero-tardiness / completed / 0 infeasible，无反向 zero-tardiness harm。
3. L/U + replayable route certificate + exact fallback 在 N=5 / 1000 seeds 的 2,568 reached frontiers 上与 exact mask **0 mismatch**；exact fallback 只承担约 42–46% 的 pure-exact new states。
4. **负边界**：N=5 depth4 receding 已经 107/107 zero-tardiness，且 search proxy 比当前 L/U 便宜；因此 N=5 只证明 continuation value / correctness，不证明算法 superiority。
5. **N=10 scaling**：用完全 method-independent 的 constructive selector 扫 seeds0..199，得到 21 个“至少一条官方 heuristic 原生 zero-tardiness 完成”的 hard-feasible cohort。Greedy 本身已能解 20/21，因此 cohort 对 proposed method 是保守的。
6. N=10 / 21 seeds：L/U future-choice 对四条 heuristic 均 **21/21 zero-tardiness、21/21 completed、0 infeasible**，924 reached frontiers / 0 mismatch；depth4 只有 NN 17/21、BatteryAware 17/21、NearestDeadline 11/21、Greedy 20/21。
7. N=10 search：L/U exact-fallback new-state search约 pure exact mask 的 42–55%；加 bounded constructive search 后 total proxy约 66–78%。
8. **B→C set-level conflict transfer**：把 B 的 obligation-set conflict 思想实例化为 C 的 deadline-threshold MST optimistic U。N=10 同一 frozen 21-seed cohort、924/924 exact frontier match、任务质量完全不变时，exact fallback ratio进一步压到 **11–18%**，total search proxy压到 **25.8–30.9%** of pure exact；相对旧 basic-U total proxy下降约 **60%**。N=15 seed1 bounded scaling 上，basic-U fallback已退化到 pure exact的约92–96%，set-MST降到约 **5.8–8.1%**，同时 66/66 frontier exact match。

C 已经支持的最强 claim：

> **A locally legal short-horizon action can destroy an otherwise feasible full mission continuation; an exact-correct L/U future-choice layer can selectively eliminate these failures beyond depth-4 receding lookahead on longer native tasks, while set-level future-conflict certificates transferred from the ASC formulation materially reduce the exact-correct search burden.**

边界：route adapter 仍是 domain-specific；search-work count 不是 wall-time theorem；learned PPO checkpoint 尚未做 paired shield。

## 3. Unified formal object

令：

- `h_t`：当前合法 history / evidence；
- `W(h_t)`：与 history 相容的 worlds；
- `a`：当前 action；
- `z`：未来 observation / execution feedback；
- `O(w,h)`：在 world/history 下有效的 hard operational obligations；
- `R_t`：剩余共享资源 / opportunities；
- `Π(h,a,z)`：从该 action 后可执行的 non-anticipative continuation policies。

定义 action 的 future-choice set：

```text
F(h_t, a) = {
  π ∈ Π : for every compatible world and every observation branch,
          π completes all active obligations within resource/time constraints
}
```

关键不是求一个新的 scalar score，而是维护三个 deterministic objects：

```text
L(h,a)=1   → 有可 replay 的 causal completion certificate
U(h,a)=0   → optimistic relaxation 已证明不存在 completion
otherwise  → unresolved，交给 exact fallback / learned ranking
```

certificate 带 validity domain：compatible support、resource interval、execution/evidence dependencies。Observation narrowing 只缩 support；resource/time/pending-feedback event 只 invalidates 依赖相交 component。

这正好统一：

- B 的 observation-conditioned future obligations / min-cut conflicts；
- C 的 route continuation certificate / MST U-bound / exact fallback；
- 历史 Layer-2 v2 的 `L/U + conditional Q×B frontier + event-local conflict invalidation`。

## 4. Paper claim ladder

### Claim A — Benchmark

**Pending final test execution.**

> A source-grounded executable benchmark for pre-disaster emergency communication, separating conformance, interactive decision, and future-choice stress instead of presuming every realistic task requires Agent reasoning.

### Claim B — Representation

**Currently supported.**

> Scalar semantic value and static worst-case resource reservation are insufficient when future obligations depend on future observations; correct planning requires observation-conditioned future-choice domains.

### Claim C — Method correctness

**Supported on B/C adapters and shared orchestration core.**

> Replayable L certificates + sound optimistic U bounds + exact fallback preserve exact action feasibility while allowing persistent certificate reuse and selective pruning.

Cross-domain attribution is now stronger than orchestration reuse alone: B's set-level obligation-conflict principle directly strengthens C's sound U-bound without changing task outcomes or the exact correctness authority.

### Claim D — Method efficiency

**Partially supported, not final.**

- B dynamic-domain build count: up to 192→32 builds (`1/6`) under observation-only narrowing；
- B active-branch component events: at C=16, pending send recomputes 1/16 components, gateway receipt/final ACK recompute 0/16, while ordinary persistent/dependency exact still perform 7–14 expansions on those changed histories；
- C N=10 **set-MST** exact-fallback state search: about **11–18%** of pure exact mask；total search proxy **25.8–30.9%**；relative to the earlier basic-U implementation this cuts total search proxy by ~60%；
- C correctness–compute Pareto：四条 policy 上，set-MST Future-Choice 在 exact-correct 方法族内都支配 old basic-U 与 pure-exact-mask point；把 depth4 加入后，depth4 与 set-MST Future-Choice 同时保持非支配，明确体现“cheap approximate vs exact-correct safety”的真实 trade-off；
- C N=15 seed1 bounded probe: exact fallback约 **5.8–8.1%** of pure exact after set-MST, but this is not yet a distribution-level result；
- historical Layer-2 v2: strong expansion reduction but ordinary persistent exact still had better Python wall time。

Final claim must be phrased as structured-search / recomputation reduction unless generic implementation clears a wall-time gate.

### Claim E — Generality

**Supported at formulation/domain level.**

- direct ASC query scheduling (B)；
- independent external hard-deadline mission environment (C)；
- source-grounded emergency communication benchmark (A)。

Do not claim C is itself an emergency-communication benchmark; it is cross-domain validation of the planning object.

## 5. Why one paper can be stronger than three loose papers

The synthesis is not “benchmark + random algorithm + random UAV experiment.” The causal chain is:

```text
A: reality audit says many realistic communication tasks are ordinary-solved
   and prevents tailoring the task to the method

B: direct ASC analysis isolates the missing representation:
   observation-conditioned future obligations / resource conflicts

C: independent environment shows the same failure mode causes real outcome loss,
   and longer-horizon N=10 keeps a gap against strong depth-4 receding control
```

因此论文真正的论点是：

> **Agentic communication should not be defined by adding LLMs or tools. It becomes non-trivial when current communication/information actions change the feasible set of future operational completions, especially under delayed observations and shared opportunities.**

## 6. Remaining hard gates before paper freeze

1. **Generic method core**：**orchestration + actual C core-path parity gates 均已关闭**。`FutureChoiceEngine` 已让 B/C 走同一 `carried → U=0 → L=1 → exact fallback` correctness protocol；formal `UAVFutureChoiceAdapter + FutureChoiceEngine` 又在冻结 N=10 21-seed × 4-policy cohort上复现 924/924 exact frontier 与全部主质量结果。剩余边界是 domain-specific certificate construction，而不是 core orchestration。
2. **B component-level invalidation**：**gate 已关闭**。active branch 的 send/pending/receipt/ACK/time/resource event 已与 fresh rebuild 对账，并补 ordinary persistent exact / dependency-cache strong ladder。下一步主要是把该 structural layer 接入最终 generic engine/论文实验接口，不再扩 synthetic axis。
3. **C stronger scale/control**：N=10 gate 已关闭；N=15 只保留 bounded scaling probe，不一把梭 exact。公开 repo 未随代码提供 PPO checkpoint，因此 learned PPO paired shield 降为 optional；下一方法重点是把 set-level conflict certificate 泛化到 generic core，而不是重训 RL。
4. **A final release**：deterministic 150-coordinate test 已完成；当前只剩 frozen 30-coordinate×2-mode LLM subset、联合统计/失败 taxonomy 与 final manifest。
5. **Paper claim table**：`results/CLAIMS.md` 已新增 F1–F7 正式 claim family；下一步只允许从 tracked artifact / generated claim matrix 投影到 manuscript。wall-time 没过就绝不写“faster”。

## 7. Provisional title space

首选工作标题：

> **Preserving Future Choices in Agentic Semantic Communication**

副标题候选：

> Source-Grounded Emergency Evaluation and Conditional Feasibility Planning

如果最终 A 更重：

> **From Operational Obligations to Future Choices: Benchmarking and Planning for Agentic Communication**
