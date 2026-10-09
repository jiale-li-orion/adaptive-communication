# Storyline — Preserving Future Choices in Agentic Semantic Communication

状态：**current narrative authority / top-conference writing scaffold**。

本文不按 A/B/C 三个项目依次讲，而按一条问题链讲。A/B/C 只是证据角色。

---

## 1. Hook: the emergency requirement

开头从真实场景进入，不从“LLM很火”进入：

> Remote landslide-monitoring deployments must keep sensing and reporting before a disaster even when power is scarce and communication repeatedly disappears. The hard part is not only getting a useful message through now. A configuration change, query, fallback transmission, or backup use can consume the energy, contact, or control opportunity needed by a later monitoring obligation.

核心直觉：

> **communication actions are commitments to future task feasibility.**

---

## 2. Community bridge: ASC already optimizes value, but not this object

承认社区已经解决很多问题：

- what / when to query；
- semantic value / GoE / VoI；
- context relevance；
- decision-sufficient semantic state；
- long-horizon counterfactual return；
- resource-aware semantic transmission。

然后只提出一个 residual gap：

> These objectives score how useful an action is. They do not explicitly represent whether taking the action leaves any causal policy that can still satisfy all remaining hard task semantics after future observations arrive.

不是“现有工作短视”，而是“优化对象不同”。

---

## 3. Minimal failure pattern

用 Fig.1 而不是长文字：

```text
same history h_t, hidden H in {0,1}

query H now
  → observe H=0 → later need B
  → observe H=1 → later need C

one remaining branch-specific resource is enough

static union reserves {B,C}
  → falsely rejects the valid contingent policy
```

一句话 insight：

> **Future choices must be conditioned on future observations rather than reserved against their static union.**

---

## 4. Method reveal

不要一上来堆 max-flow/min-cut。先给读者三个对象：

```text
L(h,a)=1  replayable causal completion exists
U(h,a)=0  even an optimistic relaxation is infeasible
otherwise unresolved → exact fallback / optional ranking
```

然后说为什么可增量：certificate带有 support/resource/execution dependency domain；history变化但 dependency不变时不重算。

再进入 set-level conflict representation / flow certificate。

---

## 5. Why the benchmark is part of the method story

A 不是“另一个贡献硬塞进来”，它回答 reviewer 的反事实：

> Did the authors tailor an emergency simulator until their method looked necessary?

我们的回答：没有。

benchmark先独立冻结 source/task/evaluator；很多真实任务被 ResourceGate、packing、myopic/depth-k ordinary rules解决；这些负结果保留。Future-Choice-Stress甚至可以为空。

因此 A 的叙事角色是：

> **reality authority + anti-tailoring falsifier.**

---

## 6. Why C is necessary

C 也不是“再找一个能赢的环境”，它回答另一个 reviewer 反事实：

> Is Future-Choice only an artifact of the authors' emergency benchmark?

在独立公开 UAV deadline/battery mission中：

- native action mask允许 locally legal action；
- action会删除原本存在的 zero-tardiness full continuation；
- strong depth-4 receding仍有 residual failure；
- Future-Choice exact-correct layer修复这些 failure；
- B 的 set-level conflict insight还能直接强化 C 的 sound U-bound。

因此 C 的角色是：

> **external falsification of benchmark-specificity.**

---

## 7. Introduction contribution packaging

推荐只写四点，不写十点：

1. **Problem abstraction.** We identify future-choice feasibility as a missing complement to semantic value in agentic semantic communication: current communication/information actions can preserve or destroy the causal set of future hard-task completions.
2. **Method.** We develop an exact-correct `L/U + certificate + fallback` framework with observation-conditioned obligation domains, set-level opportunity conflicts, and dependency-local certificate maintenance.
3. **Reality-grounded evaluation.** We derive an executable pre-disaster emergency-communication benchmark from field/standard requirements and deliberately retain ordinary-solved/negative cases, separating benchmark validity from method hardness.
4. **Cross-domain evidence.** On an independent public deadline/battery mission, Future-Choice removes residual depth-4 failures on a 100-instance hard-feasible cohort, while ASC-derived set-level certificates materially reduce exact-correct search work.

---

## 8. Results narrative by research question

不要写“Table 1 shows A, Table 2 shows B”。写：

### RQ1 — Are realistic emergency tasks all actually hard?

No. Many are saturated by ordinary mechanisms. This is a benchmark finding, not a failed method result.

### RQ2 — When does value/static reservation fail?

When future hard task semantics branch on future observations and share opportunities, static union rejects valid contingent policies.

### RQ3 — Can the structure be maintained exactly and incrementally?

Yes: fresh/incremental frontiers agree; dependency-disjoint history events can trigger zero structural recomputation; strong persistent exact remains an important control.

### RQ4 — Does this matter outside our benchmark?

Yes: on 100 preselected hard-feasible external missions, Future-Choice removes residual depth-4 failures with no reverse zero-tardiness harm.

### RQ5 — Are B and C really the same idea?

Yes: the ASC set-level conflict abstraction becomes the UAV deadline-set MST U-bound, and both execute through the same FutureChoiceEngine correctness protocol.

---

## 9. Reviewer-resistant sentence discipline

### Say

- exact-correct safety layer；
- structured search/recomputation reduction；
- paired hard-feasible outcome gain；
- observation-conditioned future completion；
- benchmark validity is independent of method hardness。

### Do not say

- universally better than MPC；
- faster than exact planning；
- first long-horizon semantic communication；
- first active semantic query；
- all emergency tasks require Agentic reasoning；
- C is an emergency-communication benchmark。

---

## 10. Abstract spine

Abstract最终只要五句逻辑：

1. 应急监测里 communication action会改变未来 hard task completion；
2. ASC现有 semantic value/goal/context对象没有显式表示这个 feasible continuation set；
3. 我们提出 Future-Choice + exact-correct L/U certificate framework；
4. source-grounded emergency benchmark证明现实任务并非都需要该方法，独立UAV环境则给出真实 continuation failure与100-instance paired收益；
5. 结论：Future-Choice应作为 semantic value 的 feasibility complement，而不是新的 value metric。
