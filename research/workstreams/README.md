# Research Workstreams

这里不是第四个 Layer，也不持有任何实现或 benchmark authority。

它只回答一个复盘问题：**当前有哪些研究路线正在被证伪/验证，它们各自依赖哪些正式 Layer 资产？**

正式 ownership 仍然只有：

- Layer 1：[`../benchmark/`](../benchmark/README.md)
- Layer 2：[`../compiler/`](../compiler/README.md)
- Layer 3：[`../policy/`](../policy/README.md)
- shared substrate：[`../substrate/`](../substrate/README.md)

当前同时推进三条线，任何一条先通过 hard gate 都可以独立形成论文贡献；三条都成立时再合并成完整 paper story。

当前综合 paper story 与 claim ledger 见 [`PAPER-SYNTHESIS.md`](PAPER-SYNTHESIS.md)。

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
