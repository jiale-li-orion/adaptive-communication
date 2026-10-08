# Layer 1 Release Tracks

状态：**CURRENT PAPER-CONSTRUCTION MAP / not a frozen benchmark release**

这张图只负责把现有 task surfaces 放回正确论文角色。它不新增 task，不改变 generator，也不把 ordinary-solved case 包装成 hard case。

## Track A — Operational / Conformance

当前候选：

- `T1.S0_STEADY_MONITORING`
- `T1.S1_WARNING_CADENCE_TRANSITION`
- `T1.S4_OUTAGE_CACHE_RETENTION`
- `T1.S6_HETEROGENEOUS_PATH_PRIORITY`

这些 surface 主要证明 source → task → lifecycle → evaluator 的闭合，承担 sanity、regression、coverage、attribution。被 fixed rule / ordinary mechanism 解掉不构成 benchmark invalidity。

## Track B — Interactive Decision

当前候选：

- `T1.S2_INTERMITTENT_BACKHAUL_FALLBACK`
- `T1.S3_ENERGY_CONSTRAINED_CONTINUITY`
- `T1.S7_COMPOUND_CONTINUITY`

它们都有真实 action→state / feedback / resource transition，可以用 final operational-obligation state 做执行式评测。当前发现的 gateway natural-feedback、persistent-energy、warning-revision 等机制即使被 myopic flow / ResourceGate / maxcov 覆盖，仍然是 benchmark failure-analysis 与 baseline-saturation 证据。

## Track C — Future-Choice Stress

当前：**空。**

这不是 Layer 1 失败，也不阻塞 A 作为 benchmark paper 继续构造。只有当某个 frozen subset 同时满足 partial observation、observation-conditioned continuation、binding shared future resource、no common safe open-loop shortcut、strong ordinary baseline 未饱和和 structural holdout 时，才进入 Track C。

Layer 2 的主方法结果只允许在这个 track 上宣称。

## Blocked / extension

- `T1.S5_RECOVERY_RECONCILIATION`：backlog-vs-fresh sacrifice priority 尚未被 source 闭合；
- T2 三个 surface：task source-valid，但 actor-chain environment 仍是 `SIMULATOR_GAP`；当前 source-only preflight 也没有给出跨阶段 shared contact resource，不能为了 method 人为补 quota/duration。

## 为什么这样分

同类 benchmark paper 的共同做法不是“删掉所有容易题”，而是把 benchmark coverage 与 hardest capability 分层：6G-Bench 用 source/standard taxonomy + validation 建 benchmark；WirelessBench 明确分知识、资源分配、多步移动决策三层；DORA 用真实灾害 operational tasks + replayable trajectories；τ-bench/OSWorld 用动态环境和 final-state/execution evaluator。一个 valid benchmark 可以同时有 sanity、ordinary-solved 和 challenging subsets。

因此 Layer 1 的 paper question 改成：

> 我们是否构造了一个来源可追溯、可执行、可复现、能覆盖灾前间歇通信 lifecycle，并能区分 conformance、interactive decision 与 future-choice stress 的 benchmark suite？

而不是：

> 每一个 task 能不能让 Layer 2 赢？
