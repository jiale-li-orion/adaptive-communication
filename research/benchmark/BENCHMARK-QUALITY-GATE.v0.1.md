# Benchmark Quality Gate v0.1

状态：Layer 1 release-quality authority  
日期：2026-10-04

目的：把成熟 benchmark 论文中关于 validity、coverage、evaluation、reporting、reproducibility 与 maintenance 的要求，转成当前 Emergency Communication Benchmark 的硬 gate。任何 split / family 在标记 BENCHMARK_ADMIT 前必须逐项通过。

## Q0 Construct validity

回答：我们声称测的能力，是否真的是任务成功所需要的能力？

要求：
- 明确 target construct；
- 说明哪些 task observable/action/outcome 对应这个 construct；
- 说明哪些能力明确不在 scope 内；
- 检查 trivial shortcut / irrelevant skill dependency；
- 若一个 ordinary mechanism 即可饱和结果，降低 claim，不继续包装为 agentic capability。

失败：CONSTRUCT_INVALID。

## Q1 Task validity

要求：
- task 来源可追溯到 operational corpus；
- family identity 通过 Family Identity Test；
- 每个 case 可解或明确属于 impossible/abstain split；
- 不因 tool 缺失、simulator bug、ground-truth leak 人工制造难度；
- current simulator 缺 source-backed object 时标 SIMULATOR_GAP，不改 task 语义。

失败：TASK_INVALID。

## Q2 Outcome validity / evaluator soundness

要求：
- external oracle / success predicate 与 policy 输出分离；
- evaluator 接受 multiple legal success terminal states；
- authority violation、deadline violation、未执行但文本正确等必须失败；
- mutation tests 覆盖 positive / negative / irrelevant-state corruption；
- LLM-as-judge 不拥有核心 task success 判定。

失败：EVALUATOR_INVALID。

## Q3 Source-grounded taxonomy

要求：
-一级 taxonomy 由 field / standard / workflow corpus 归纳；
- capability / failure / radio / tool 名不能直接成为 Family；
- family merge audit 完成；
- adjacent literature 只能补 mechanism plausibility，不能覆盖 direct task authority；
- source profile / source snapshot 可追溯。

失败：TAXONOMY_UNGROUNDED。

## Q4 Non-toy coverage

要求：
- case 规模来自 profile × regime × site/device × trace × observation projection；
- normal / boundary / failure / recovery / resource-binding cells 有覆盖；
- 至少一个结构化 held-out split，不只随机 seed；
- case count 由 coverage 与统计需要决定，不由“看起来够大”决定；
- near-duplicate / template leakage 有审计。

失败：COVERAGE_INSUFFICIENT。

## Q5 Decision validity / hardness

要求：
- multiple legal options；
- no common zero-regret safe action for intended H1/H2 states；
- source-backed binding constraint；
- observation/evidence can change legal/feasible plan set when relevant；
- legal policies产生 materially different obligation-feasibility transition；
- hardness 不能由 arbitrary hidden field / reward weight 制造。

失败：DECISION_DEGENERATE。

## Q6 Baseline ladder

至少包括：
- no-op / trivial；
- static source-backed rule；
- ordinary automatic/local mechanism；
- greedy / EDF / fixed-priority where semantically legal；
- observation-matched deterministic search/planner；
- full-state feasibility oracle；
- clairvoyant upper bound；
- LLM / reasoning agent；
- learned policy only when repeated state-dependent choice justifies it。

要求报告 baseline saturation / headroom。

失败：BASELINE_INCOMPLETE。

## Q7 Generalization split

主 test split 至少有一个不是随机行切分：
- held-out jurisdiction；
- held-out standard/source family；
- held-out site/deployment；
- held-out communication capability profile；
- held-out operating regime；
- held-out empirical trace window。

要求：
- train/dev/test 不共享同一 trace window；
- source-derived template近邻不得跨 split 泄漏；
- split rationale 在 release 文档中明确。

失败：GENERALIZATION_WEAK。

## Q8 Contamination / benchmark gaming

要求：
- frozen public test artifact 与 development generator 分离；
- source/profile/case ids 有版本；
- 不用 evaluated model 表现反向调 difficulty；
- benchmark-specific prompt tuning 与 repeated private variant selection 需披露；
- 对公开模型训练污染风险明确限制与解释；
- release 后变更必须新版本，不静默修改 leaderboard target。

失败：CONTAMINATION_OR_GAMING_RISK。

## Q9 Statistical reporting

要求：
- 不只报 point estimate；
- 对 stochastic policy / environment 重复运行；
- 报置信区间或 bootstrap interval；
- family / hardness / regime / held-out profile 分层报告；
- pairwise comparison 使用 paired analysis when case ids align；
- 多模型/多指标比较说明 multiple-comparison handling；
- report failure counts and invalid-run policy。

失败：STATISTICS_INCOMPLETE。

## Q10 Reproducibility

release 至少包含：
- immutable case artifacts；
- source/profile refs；
- generator version；
- frozen environment/tool version；
- oracle implementation/version；
- evaluator tests；
- baseline implementations；
- split manifest；
- replay traces or deterministic seeds where possible；
- one-command validation / reproduction entry；
- known limitations / known flaws。

失败：REPRODUCIBILITY_INCOMPLETE。

## Q11 Human/source audit

要求：
- source audit 与 task audit 分开；
- stratified sample by Family × profile × hardness × split；
- 人工核查 source extraction 是否反转 authority/priority/time semantics；
- 抽查 oracle success set / evaluator；
- 记录审计者、版本、发现的问题与修正。

失败：AUDIT_INCOMPLETE。

## Q12 Maintenance / benchmark lifecycle

要求：
- schema / generator / source snapshots / cases 独立版本；
- stale external source 有 replacement policy；
- evaluator flaw 有 disclosure + migration policy；
- leaderboard/result 绑定 benchmark version；
- 新 case family 不允许在不重跑 validity gate 的情况下并入主分数。

失败：MAINTENANCE_UNDEFINED。

## BENCHMARK_ADMIT rule

只有以下条件全部满足，candidate split 才可标 BENCHMARK_ADMIT：

    V0–V9 automatic validity filters = PASS
    Q0–Q12 quality gates = PASS
    source audit = PASS
    task/evaluator audit = PASS
    held-out split frozen
    benchmark version frozen

任何一项 FAIL 都必须保留具体 disposition，不能用 aggregate score 覆盖。

## Paper-facing reporting template

正式 benchmark 论文至少按以下顺序报告：

1. construct / research question
2. real operational corpus and source provenance
3. taxonomy derivation
4. environment and family contracts
5. case generation and variable provenance
6. oracle / evaluator design
7. validity and shortcut audits
8. scale / coverage / held-out split
9. baseline ladder
10. model/policy results
11. statistical uncertainty
12. failure analysis
13. limitations / contamination / maintenance
14. artifacts and reproducibility

这份顺序优先于“先报 SOTA 分数”的写法。
