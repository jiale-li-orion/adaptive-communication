# Method scaffold — System model and Future-Choice formalism

状态：**current manuscript method scaffold / reuses repository system model**。

原则：不重造完整系统模型。§2–§3 应引用 `research/substrate/SYSTEM-MODEL-v1.md` 已有 Operational Task、obligation、physical transition、Evidence World、capability 与 metric 定义；本文只引入 Future-Choice 必需的附加对象。

---

## 1. Existing ASC/emergency system model to reuse

### Operational task

沿用：

\[
\tau=(\mathcal N_\tau,\mathcal M_\tau,\mathcal P_\tau,\mathcal W_\tau,
\mathcal D_\tau,\mathcal A_\tau,\mathcal S_\tau).
\]

### Hard task-semantic obligation

沿用：

\[
o=(i,m,r_o,[s_o,e_o],d_o).
\]

解释成 ASC language：`o` 是 downstream goal诱导的 hard semantic requirement，不是一个独立于 semantic communication 的调度任务。

### Physical communication state

沿用：

\[
x_{t+1}=F(x_t,a_t,\xi_t;\phi),
\]

其中 `x_t` 已包含 battery、source cache、installed config、access/backhaul state、gateway queue、runtime state等；本文不更改 `F`。

### Partial semantic/communication observation

沿用：

\[
z_t=H(x_{\le t},a_{<t},\xi_{\le t},\ell),
\qquad
\mathcal E_t=\{e_j:t_j^{obs}\le t\}.
\]

定义合法 history（`p_t` 为已知 pending query / send / ACK 记录，而非未来响应）：

\[
h_t=(\tau_{\le t}^{pub},\mathcal E_{\le t},a_{<t},z_{\le t},p_t,t),
\]

仅包含 runtime legally observed information，不含 simulator hidden truth、未发布 task revision 或已发未达 query 的结果。query 是真实环境 action，可能消耗机会并延迟返回；合法 SEND attempt 在某些 compatible worlds 内允许失败。

---

## 2. Compatible worlds and active obligations

令：

\[
\mathcal W(h_t)
\]

为与合法 history `h_t` 相容的 latent/exogenous worlds，包括后续环境变化和授权 task revisions，但不得提前暴露给 policy。robust guarantee 只针对冻结的有限 support。

在 world `w` 诱导的完整执行轨迹 `\gamma_w` 下，Operational Task 产生的 hard obligation set（包括未来发布/释放的义务）：

\[
\mathcal O(\gamma_w).
\]

定义 `Done(o,\gamma_w)=1` 当且仅当合格 sample 在义务时窗内生成并在 deadline 前到达中心。send attempt / gateway receipt / command queued 不构成最终义务完成。未来 observation / task revision 可以让 obligation branch 在未来才确定，因此不能在 `t` 时把所有可能未来 obligation 静态并集成一个 unconditional set。

---

## 3. Non-anticipative continuation policy

令 `\mathcal A(h_t)` 为合法可尝试动作，`\Pi^{na}(h_t;a)` 为首先执行 `a\in\mathcal A(h_t)`、之后只依赖合法 history 的 continuation policies。完整 trajectory 写作：

\[
\gamma_w=\operatorname{Run}(h_t,a,\pi,w).
\]

query / send / wait 经过同一个 physical transition，延迟 ACK、query response、passive report 与 timeout 只能在实际 arrival 后影响 policy。

continuation policy `\pi` 必须 non-anticipative：

\[
\pi(h)=\pi(h')
\quad\text{whenever }h,h'\text{ expose the same legal observation history}.
\]

即 policy 不能在 observation 真正到来前按 hidden world 分支；离线对每个 world 单独选 `\pi_w` 只能作为 optimistic upper reference。

---

## 4. Future-Choice set

定义：

\[
\mathcal F(h_t,a)
=
\left\{
\pi:\;
\forall w\in\mathcal W(h_t),
\forall z\text{ reachable under }(h_t,a,\pi,w),
\;\pi\text{ legally completes all }o\in\mathcal O(w,h)
\right\}.
\]

Boolean exact feasibility：

\[
V^*(h_t,a)=\mathbf 1[\mathcal F(h_t,a)\neq\varnothing].
\]

这是 policy-valued robust feasibility：一个 causal policy 覆盖全部 compatible worlds，但收到不同合法 observation 后允许分支。它不同于逐 world 完美信息策略，也不同于概率阈值风险约束；后者不属于当前 oracle/L-U/结果口径。

Future-Choice不是新的 semantic value metric。给定任意现有 semantic/task utility `Q_{sem}(h,a)`，最直接组合是：

\[
\max_a Q_{sem}(h_t,a)
\quad\text{s.t.}\quad
V^*(h_t,a)=1.
\]

---

## 5. Exact-correct L/U decomposition

对每个 candidate action维护：

\[
L_t(a)\le V^*(h_t,a)\le U_t(a),
\qquad L_t,U_t\in\{0,1\}.
\]

### Replayable lower certificate

`L_t(a)=1` 当且仅当当前持有一个**可重放 causal completion certificate**，能在所有其声明覆盖的 compatible observation branches上完成 hard obligations。

### Sound optimistic upper test

`U_t(a)=0` 当一个比真实问题更乐观的 relaxation仍 infeasible。

### Unresolved

\[
L_t(a)=0,\;U_t(a)=1
\]

才进入 exact fallback；可选 Layer3只能改变 unresolved actions的 search order，不得改变 correctness。

---

## 6. Set-level opportunity conflict

在一个 realized/compatible branch内，令 hard obligations为左侧节点，future communication/service opportunities为右侧节点；若 obligation `o` 可以由 opportunity `r` 合法完成，则连边。

得到 bipartite graph：

\[
G=(\mathcal O,\mathcal R,E).
\]

capacity-aware max-flow给出 optimistic matching；residual min-cut / Hall deficit给出 set-level conflict certificate。关键不是判断“某个 obligation有没有一个 slot”，而是：

> **某个 obligation subset是否共同争夺同一组稀缺 future opportunities。**

这也是 B→C transferable abstraction：UAV中用 deadline-threshold due-set MST构造同类 set-level optimistic infeasibility certificate。

---

## 7. Certificate validity domain

每个 certificate携带：

\[
D(c)=
(\mathcal W_c,
[b_{min},b_{max}],
\mathcal D_c,
t_c^{valid},
\text{witness}).
\]

其中：

- `W_c`：compatible world/support domain；
- resource interval：certificate适用的 budget/resource range；
- `D_c`：future-feasibility dependencies（obligation/opportunity/pending execution等）；
- `t_valid`：下一次时间/机会边界；
- witness：replayable policy / structural conflict certificate。

Observation narrowing只缩 `W_c`；event `e` 只有在改变 `D_c` 或 validity boundary时才使 certificate失效。

这给出本文重要systems distinction：

> **history changed does not imply future-feasibility structure changed.**

---

## 8. Minimal soundness lemmas

### Lemma 1 — Replayable lower-bound soundness

若 certificate `c` 在声明的 validity domain内给出一个 legal、non-anticipative、可重放 continuation policy，且该 policy在所有覆盖的 compatible branches完成全部 active hard obligations，则：

\[
L_t(a)=1\Rightarrow V^*(h_t,a)=1.
\]

**Proof sketch.** certificate witness本身就是 `\mathcal F(h_t,a)` 的一个元素。

### Lemma 2 — Optimistic upper-bound soundness

设 relaxation `\widetilde{P}(h_t,a)` 删除约束或增加资源，因此真实 feasible set是其子集。若 relaxation infeasible，则：

\[
U_t(a)=0\Rightarrow V^*(h_t,a)=0.
\]

**Proof sketch.** 若真实问题存在 completion，则同一 completion在更乐观 relaxation中也可行，矛盾。

### Lemma 3 — Deadline-set MST soundness (C adapter)

对任意 deadline threshold `d`，令 `S_d` 为尚未完成且 deadline≤d 的客户集合。任何在 d 前服务完 `S_d` 的 route prefix都是连接 current position与 `S_d` 的 connected walk，其长度至少为 Euclidean MST：

\[
L_{route}(S_d)\ge MST(\{x_t\}\cup S_d).
\]

若：

\[
t+\frac{MST(\{x_t\}\cup S_d)}{v}>d,
\]

则真实 route infeasible，因此可 sound 地置 `U=0`。Battery、charger detour与depot return被忽略，只让 relaxation更乐观。

### Lemma 4 — Dependency-disjoint certificate preservation

设 event `e` 发生后：

1. certificate的support/resource/time validity domain仍成立；
2. event修改的state/dependency set与 `D_c` 不相交；
3. event不新增连接 reused component 与外部 component的合法 future opportunity edge。

则 certificate witness / conflict structure在新 history下仍有效，无需重建该 component。

若第3项不成立，incremental runtime必须 conservative fallback到 repartition/full rebuild；这正是 B6 structural holdout要审的边界。

---

## 9. Runtime algorithm in paper form

对 native/ASC scheduler提出的 candidate actions：

```text
for action a:
    if carried certificate is still valid:
        mark feasible
    elif optimistic relaxation proves impossible:
        prune a
    elif constructive certificate succeeds:
        mark feasible and cache witness/domain
    else:
        run exact fallback

choose among exact-correct feasible actions
using the existing ASC semantic/task value policy
```

这段非常重要：Future-Choice是 **feasibility/safety layer around ASC value policy**，不是另一个 semantic scorer。

---

## 10. What remains domain-specific

Generic core只拥有 `carried → U=0 → L=1 → exact fallback` correctness orchestration。

Domain adapter仍拥有：

- physical transition；
- obligation/resource graph；
- optimistic relaxation；
- constructive certificate；
- exact authority。

因此不能声称“一套统一物理模型解决所有ASC任务”；我们声称的是**统一 feasibility protocol与transferable set-level conflict abstraction**。
