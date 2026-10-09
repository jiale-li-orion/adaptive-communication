# Research Workstreams

这里不是第四个 Layer，也不持有任何实现或 benchmark authority。

它只回答一个复盘问题：**当前有哪些研究路线正在被证伪/验证，它们各自依赖哪些正式 Layer 资产？**

正式 ownership 仍然只有：

- Layer 1：[`../benchmark/`](../benchmark/README.md)
- Layer 2：[`../compiler/`](../compiler/README.md)
- Layer 3：[`../policy/`](../policy/README.md)
- shared substrate：[`../substrate/`](../substrate/README.md)

现有三条 workstream 已形成统一的问题叙事与 A/B/C 实验证据，但这不自动代表 **DeepSeek Agent + Future-Choice 统一决策方法** 已完成。A7–A11 的模型/取证/物理执行与 F1–F7 的结构化 Future-Choice 计算分别有效；联合方法的来源、动作、证书和 task-outcome 归因要通过单独的 M0–M3 验收门。

当前综合 paper story 与 claim ledger 见 [`PAPER-SYNTHESIS.md`](PAPER-SYNTHESIS.md)。

2026-10-09 的**实现级止漂审计与下一阶段计划**：[`LLM-FUTURE-CHOICE-UNIFICATION-AUDIT-2026-10-09.md`](LLM-FUTURE-CHOICE-UNIFICATION-AUDIT-2026-10-09.md)。它只记录跨线的接口缺口和新实验准入，不修改已冻结的实验或 Layer authority。

| Workstream | 当前问题 | 主要正式资产 | 当前状态 |
|---|---|---|---|
| [`S7-ORIGINAL-SCENARIO.md`](S7-ORIGINAL-SCENARIO.md) | 原始灾前山区需求如何形成 source-grounded executable benchmark | Layer 1 task surface + shared substrate | **BENCHMARK PRE-RELEASE / deterministic test done / frozen LLM subset running** |
| [`ASC-TRANSFER.md`](ASC-TRANSFER.md) | future-choice feasibility 是否构成已有 ASC formulation 上独立且可维护的方法对象 | Layer 2 + external ASC formulation | **F1–F3 SUPPORTED：conditional obligations + shared-opportunity conflict + persistent/component-local reuse** |
| [`EMERGENCY-COMM-TRANSFER.md`](EMERGENCY-COMM-TRANSFER.md) | 同一 future-choice 对象能否迁移到独立外部 sequential mission 并产生质量/搜索收益 | Layer 2 + external mission environments | **F4–F6 SUPPORTED：N=10 exact-correct headroom + cross-domain set-conflict transfer；N=15 仅 bounded probe** |

统一纪律：

1. 不再新增 benchmark generator 版本来制造 hardness。
2. workstream 文档可以更新，但正式语义必须回写到对应 Layer authority。
3. 外部 transfer 不允许改写核心方法定义；transfer 的作用是测试 generality。
4. 任何负结果都保留。某条线失败不反向修改 task distribution。

当前正式 claim state 只认 [`../../results/CLAIMS.md`](../../results/CLAIMS.md)：Layer 1 使用 `B*`，当前 Future-Choice 方法/transfer 使用 `F1–F7`。本目录只负责导航与跨线 synthesis。

当前跨线复盘：

- [`EXPERIMENT-MATRIX-2026-10-09.md`](EXPERIMENT-MATRIX-2026-10-09.md) / [`EXPERIMENT-MATRIX-2026-10-09.json`](EXPERIMENT-MATRIX-2026-10-09.json)：**当前实验设计 authority**；固定 RQ、规模、cohort、baseline、correctness、统计、资源 contract 与 stop rule；
- [`LITERATURE-GAP-AUDIT-2026-10-09.md`](LITERATURE-GAP-AUDIT-2026-10-09.md)：同期 benchmark / ASC / active-measurement / world-model 文献重新对齐后的 novelty、实验与写作边界；
- [`ASSET-REUSE-AUDIT-2026-10-09.md`](ASSET-REUSE-AUDIT-2026-10-09.md)：current core、paper evidence、可复用 support、provenance-only 与 retire 资产分级。
