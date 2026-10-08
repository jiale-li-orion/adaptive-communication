# Research Workstreams

这里不是第四个 Layer，也不持有任何实现或 benchmark authority。

它只回答一个复盘问题：**当前有哪些研究路线正在被证伪/验证，它们各自依赖哪些正式 Layer 资产？**

正式 ownership 仍然只有：

- Layer 1：[`../benchmark/`](../benchmark/README.md)
- Layer 2：[`../compiler/`](../compiler/README.md)
- Layer 3：[`../policy/`](../policy/README.md)
- shared substrate：[`../substrate/`](../substrate/README.md)

当前同时推进三条线，任何一条先通过 hard gate 都可以独立形成论文贡献；三条都成立时再合并成完整 paper story。

| Workstream | 当前问题 | 主要正式资产 | 当前状态 |
|---|---|---|---|
| [`S7-ORIGINAL-SCENARIO.md`](S7-ORIGINAL-SCENARIO.md) | 原始灾前山区任务是否天然产生 future-choice hardness | Layer 1 task surface + shared substrate | **PRIMARY / task-level witness found; strong-baseline gate open** |
| [`ASC-TRANSFER.md`](ASC-TRANSFER.md) | future-choice feasibility layer 能否增强已有 ASC scheduler / VoI 方法 | Layer 2 + external ASC formulation | **FORMULATION PROBE PASS / empirical transfer open** |
| [`EMERGENCY-COMM-TRANSFER.md`](EMERGENCY-COMM-TRANSFER.md) | 同一方法能否迁移到已有应急通信控制/资源优化任务 | Layer 2 + external emergency-comm environment | **DRL-EC3 runnable / obligation wrapper required** |

统一纪律：

1. 不再新增 benchmark generator 版本来制造 hardness。
2. workstream 文档可以更新，但正式语义必须回写到对应 Layer authority。
3. 外部 transfer 不允许改写核心方法定义；transfer 的作用是测试 generality。
4. 任何负结果都保留。某条线失败不反向修改 task distribution。
