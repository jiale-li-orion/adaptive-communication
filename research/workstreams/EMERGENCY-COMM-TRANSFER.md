# Workstream C — Emergency Communication Transfer

## Question

future-choice / operational-obligation feasibility 能否在已有应急通信控制环境中提供超出 coverage / throughput / weighted-reward 优化的增量？

## Scope

不把主项目改造成 post-disaster UAV paper。外部应急通信环境只承担 generality test。

优先寻找具备以下至少三项的公开任务：

- sequential communication/resource decisions；
- finite energy / bandwidth / contact opportunities；
- hard deadlines or mission stages；
- partial observation / delayed feedback；
- action commitment 会持续影响后续资源或可达性。

## Intended comparison

```text
existing resource allocator / RL / MPC
vs
same allocator + operational-obligation feasibility layer
```

关注的不是再提高一点 throughput，而是：

> resource-optimal action 是否会在 long horizon 上使 mission obligation set 不再可完成？

## Hard gate

只有当外部任务存在真实的 mission-level continuation conflict 才保留。若所有差异都能由普通 hard constraint / MPC horizon 直接吸收，则该环境不适合支撑 future-choice claim。

## Next

第一可执行候选冻结为 **DRL-EC³**（BIT-MCS/DRL-EC3，JSAC 2018）。它的官方代码明确面向 emergency communications / remote-area communication，包含可训练 environment、连续 UAV movement action、persistent UAV energy、spatial data-collection state，以及 movement + collection 的真实持续能耗。

本地只读 checkout：`local_research/external/DRL-EC3`。由于原 repo 把 rendering flag 绑到 TensorFlow 1.x、并依赖旧 Gym，当前 smoke 用内存中的最小 compatibility shim 解耦这两个**非科学依赖**；未修改外部 checkout、未安装 TensorFlow、未训练模型。环境 reset + one-step dynamics 已跑通：2 UAV 初始 energy 500，一次 zero-movement step 仍因数据采集把每台 energy 降到约 499.352，并更新 remaining-data state。

静态/运行审计同时确认一个关键边界：released environment **没有 hard operational deadline / obligation object**。因此它现在的正确角色是：

> **RESOURCE_BASELINE_AND_SECONDARY_TRANSFER_CANDIDATE**

不能把 future-choice semantics 说成原论文已有。下一步只允许显式添加一个薄的 mission-obligation wrapper（例如 time-bounded coverage commitments），保持原 dynamics/reward/policy 不变，再测试 value/DRL action 是否删除 hard mission continuation。如果 wrapper 只是普通 constrained MPC 一行就解决，这条线降级为普通 external baseline。
