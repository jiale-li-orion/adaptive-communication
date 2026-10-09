# Formal-prior-art boundary: winning regions, shielding, and Future-Choice

状态：**related-work / novelty-risk audit**。仅约束论文声称范围；不修改 frozen A/B/C 数据、实验 ID、cohort 或 correctness authority。

## 1. 必须承认的直接近邻

1. **Junges, Jansen, Seshia, CAV 2021, *Enforcing Almost-Sure Reachability in POMDPs*.** 论文把 belief-support 的 reach-avoid winning region 转为 permissive action shield，并提出 incremental SAT 求解与 symbolic alternative；它已经研究在局部不可观测的情况下保留一条能够达到目标且避免 bad state 的策略。官方全文：https://doi.org/10.1007/978-3-030-81688-9_28 。相关 BibTeX 建议键：`junges2021reachability`。
2. **Ajdarów, Brlej, Novotný, AAAI 2023, *Shielding in Resource-Constrained Goal POMDPs*.** 论文把 action-dependent resource use、可能的资源补充、部分可观测的 goal planning 和 formal safety shield 结合，并以 POMCP 求解期望目标代价。论文明确保证避免资源耗尽；**不能仅凭摘要声称它已经直接证明多义务 deadline completion**。官方入口：https://doi.org/10.1609/aaai.v37i12.26715 。相关 BibTeX 建议键：`ajdarow2023rsgoshield`。
3. **Carr, Jansen, Junges, Topcu, AAAI 2023, *Safe Reinforcement Learning via Shielding under Partial Observability*.** 面向部分可观测环境中 shield 与 agent policy 的结合，属于通用 shielding 模块的直接相关工作。官方入口：https://doi.org/10.1609/aaai.v37i12.26723 。相关 BibTeX 建议键：`carr2023partialshield`。

## 2. 与本文的实质交集

在冻结的有限-horizon、有限 scenario support 下，把状态扩充成 `(physical state, legal observation history, pending events, outstanding obligations, deadlines, t)`，即可把“所有任务义务最终按时完成”构造为一个 reach-avoid/contingent winning-policy 判别问题。由此：

- `∃ non-anticipative policy ∀ compatible worlds: Done` 采用的是已知的 observation-based winning strategy 逻辑，**不能称为首次提出的普适规划对象**。
- “剔除会摧毁未来可行策略的 action” 属于 shielding / winning-region 家族，**不能宣称发明了 action shield**。
- 单纯“增量求解 winning region”也已有 CAV 2021 incremental SAT 先例，**不能把 incremental 一词本身包装为独创性**。
- CAV 2021 的 almost-sure reachability 与本文在固定 finite support 上的 `∀w` completion **不可直接宣称数学等价**：概率零路径、时间 horizon、world support、观察可得性和外生 task revision 处理均应写明。可主张两者共享 reachability/shielding 建模范式。

## 3. 可以保留的、需要实验支撑的剩余贡献

本文特殊化到 ASC 的 executable semantics：合格采集、deadline 前最终到达中心、task revision、owner-scoped evidence、query/send/ACK 的真实状态迁移和共享通信机会。F1 的 observation-conditioned obligations 避免把互斥 future branches 做 static union；set-level matching/Hall deficits 计算同一未来机会的容量冲突。F2/F3 在 **obligation–opportunity dependence structure** 上维护可重放的 L/U certificate validity，并对不确定性剩余采用 exact fallback。这是针对通信义务与机会图的增量证书机制，而非通用 POMDP winning-region 求解算法的新发明。

验证范围同样需要精确：B 是受控机制/结构/独立 exact 测试，C 是一个外部已发布环境及其官方 heuristic/finite-horizon control。C 内的 exact frontier oracle 是强计算正确性 authority，不能将其误写成与已有 shield systems 的实测 head-to-head。尚未移植 CAV 2021 或 AAAI 2023 的实现到相同实例，论文不得声称相对这些系统的 wall-time 或 solver-state 优势。

## 4. 需要进入论文的修订

- **Introduction:** `missing primitive` 明确限制为 *in the target ASC semantic-action formulation*；承认 formal shielding 存在，强调具体 hard-obligation representation 与 amortized certificates。
- **Related Work:** 增加小段 *Belief-support reachability and shielding*，明确 CAV 2021 与 AAAI 2023 的贡献；和 `active information acquisition` 段区分。
- **Method:** 可用“specialized finite-support winning-policy test”作连接，保持 `∃π ∀w`、non-anticipativity 和 evidence-arrival timing；避免把单世界可行性当作共同 causal policy。
- **Results / Limitations:** F1 的 static-union counterexample 只反驳 static reservation，**不反驳 POMDP/contingent planners**；F2/F3 的增量证据只针对已冻结 baselines。没有直接 formal shield baseline 时必须声明，避免归因越界。

## 5. 推荐的一段英文 Related Work 文字（待与正文统稿）

> Formal synthesis has long used belief-support winning regions to restrict actions to those preserving reach-avoid objectives under partial observability; incremental SAT procedures and permissive shields were developed before our work. Resource-constrained goal POMDPs further integrate shielding with action-dependent resource consumption and replenishment. Accordingly, we do not claim novelty for the general notion of preserving a winning continuation. Our contribution is an executable ASC specialization in which hard monitoring/delivery obligations, delayed evidence, task revisions, and shared contact opportunities induce observation-conditioned obligation–opportunity conflicts. We exploit these conflicts to maintain polarity-safe, dependency-scoped feasibility certificates with exact fallback, and verify their effect on independent communication-mission instances.

引用核查边界：上述论文的题名、作者、年份与核心摘要来自 Springer CAV 2021、AAAI 2023 官方出版页；涉及计算模型差异时以正文明确陈述为准，未实施可比 solver 不能推测性能。
