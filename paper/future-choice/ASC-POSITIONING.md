# ASC positioning and terminology map

状态：**current community-positioning authority for manuscript writing**。

目标：让论文从 Agentic / Goal-Oriented Semantic Communication 社区内部自然长出来，而不是 generic planning paper 套一个 wireless 场景。

场景不变：本文始终以**灾前山区应急监测**为主问题需求——供电不足、链路间歇中断、节点/网关长期运行，仍需持续完成监测、上报与任务修订义务。变化的是抽象层次：我们把这个现实需求提升为 ASC 中一个尚未被 semantic value / context / query scheduling 显式表示的问题。

---

## 1. Community-native starting point

本文采用 ASC / goal-oriented semantic communication 的共同抽象：

```text
semantic source / sensing agents
    ↓ observe task-relevant source attributes
semantic acquisition / query / transmission action
    ↓ consumes communication, sensing, energy, or opportunity resources
knowledge / context state at an intermediate or receiving agent
    ↓
downstream actuation / decision / task objective
```

与现有代表性工作的关系：

- `agheli2025pull`：multiple sensing agents → hub → actuation agents；hub 依据 query cost 与 long-term Grade of Effectiveness 决定 what/when to query；
- `saz2026logicalsemcom`：goal-oriented states 表示 downstream decision 相关抽象，semantic bottleneck 选择最有 decision information 的 clauses；
- `wang2026wmcdt`：closed-loop Physical AI 中用 world model / counterfactual rollout 估计 semantic tokens 对 long-horizon return 的 causal contribution；
- `zhao2026wirelesscontext`：wireless context engineering 处理 context filtering / structuring / injection，并显式考虑 latency / energy / memory constraints；
- `ferrag2026sixgbench`、`tong2026wirelessbench`：把 semantic/network reasoning、tool use 与 agent decision推到 benchmark层。

本文继承这些问题语言，不重新定义“semantic”“goal-oriented”“agentic”几个大词。

---

## 2. Original emergency requirement → ASC abstraction

原始需求保持：

```text
灾前山区监测
  + 节点供电不足
  + access / backhaul 间歇中断
  + 任务会随风险阶段改变
  + 配置、缓存、能量与通信机会具有持久状态
  + 仍需持续完成监测/告警相关业务义务
```

这在 ASC 语言下不只是“哪个 packet 更重要”，而是：

```text
当前 semantic / communication action
    ↓
改变知识状态 E_t
同时改变 resource / opportunity state R_t
    ↓
未来 observation 分支到来
    ↓
哪些 hard task semantics 仍有合法 completion continuation？
```

因此本文从真实 emergency requirement 中抽象出 ASC 语义动作下的可执行完成约束：

> **semantic action can change the feasible set of future task completions.**

这句话仅承担 ASC community framing。其通用形式与 POMDP reachability winning-region / shielding 已有交集，参见 `FORMAL-PRIOR-ART-BOUNDARY-2026-10-09.md`。可检验的增量主张是 owner-scoped、异步付费证据与动态任务义务、机会容量冲突的专门形式化，以及在该结构上维护 sound L/U certificate 与 exact fallback；不得将 observation-based winning policy 或 action shielding 本身包装为首次提出。

---

## 3. Repo system model → ASC vocabulary

仓库 `research/substrate/SYSTEM-MODEL-v1.md` 是物理/业务 authority。正文只做 community-facing 映射，不另建平行系统模型。

| Existing object | ASC interpretation | Paper symbol |
|---|---|---|
| Operational Task | downstream goal / task specification | `\tau` |
| Monitoring obligation | hard task-semantic requirement induced by the goal | `o\in\mathcal O_t` |
| Node/source state | semantic source + sensing-agent physical state | `x_t` |
| Evidence World | receiver/agent knowledge or context state | `\mathcal E_t` |
| Evidence capability | semantic acquisition / query action | `q_t` |
| Device capability | communication / actuation action | `a_t` |
| Gateway/center observation history | hub / downstream agent knowledge history | `h_t` |
| Future communication/resources | sensing/communication budget and service opportunities | `\mathcal R_t` |
| Obligation evaluator | downstream task-effectiveness authority | completion predicate |

`obligation` 不是与 semantic communication 无关的 OR object。它是把“task relevance”从 soft utility推进为**可执行 hard task semantics**后的 operational unit。

---

## 4. Existing ASC object vs our object

### Existing: semantic value / effectiveness

典型问题：

```text
V_semantic(message/query | current knowledge, task)
```

可以是 GoE、VoI、task utility、decision information、counterfactual return contribution、context utility。

### Ours: future-choice feasibility

本文不再发明另一个 scalar semantic score。定义：

```text
F(h_t,a)
= set of non-anticipative future policies that,
  after taking action a under current semantic/communication history h_t,
  can still complete every outstanding hard task-semantic obligation
  on every future observation branch compatible with that policy.
```

因此：

```text
semantic value asks:
    how useful is this information/action for the task?

Future-Choice asks:
    after taking it, does at least one causal way to finish the hard task remain?
```

二者是互补关系。Future-Choice 最自然的 ASC 使用方式是：

```text
maximize existing semantic/task value
subject to FutureChoice(h_t,a) != empty
```

而不是用 Future-Choice 替换所有 semantic utility。

---

## 5. ASC-native problem statement

推荐正文 opening：

> In agentic semantic communication, an agent does more than encode a source: it decides what to query, transmit, retain, or actuate as observations and communication opportunities evolve. Existing work has made these actions increasingly task-aware through semantic value, goal-oriented state, context relevance, and long-horizon return. Yet in long-lived emergency monitoring, an action can be highly task-relevant now and still consume the only communication opportunity, battery reserve, or observation branch needed to satisfy a later hard requirement. We therefore study a complementary object: whether a current semantic/communication action preserves at least one non-anticipative future policy that can still complete all outstanding hard task obligations.

---

## 6. What makes this Agentic Semantic Communication

本文不以“是否用了 LLM”定义 Agentic。

Agentic structure来自：

```text
observe partial semantic/communication state
→ decide whether/what to acquire, transmit, or actuate
→ action changes both knowledge and future communication/task state
→ receive delayed semantic / execution feedback
→ revise subsequent communication choices
```

因此 Future-Choice 本身可以由 deterministic / exact planner实现；LLM只是同一 runtime下的一种 policy family。

---

## 7. Terminology discipline

### Prefer

- Agentic Semantic Communication
- Goal-Oriented Semantic Communication
- semantic acquisition / query scheduling
- task-relevant information
- knowledge / context state
- downstream task effectiveness
- hard operational obligation / hard task semantics
- future completion feasibility
- observation-conditioned continuation
- shared communication opportunity
- replayable causal certificate
- sound optimistic relaxation

### Do not sell as novelty

- context engineering；
- counterfactual semantic value；
- active semantic query；
- decision-sufficient evidence；
- measurement can hurt future outcomes；
- long-horizon semantic communication。

这些已经被最近邻工作覆盖。本文 novelty 必须始终落在：

> **hard completion set + future observation conditionality + set-level shared opportunity conflict + certificate validity/dependency-local maintenance.**
