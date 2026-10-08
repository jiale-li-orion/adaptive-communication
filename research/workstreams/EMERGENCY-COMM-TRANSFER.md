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

### Hard-deadline UAV mission red-team

另外保留一个**不冒充 emergency-communication domain**、但对方法更强的 external mission red-team：`mdehghani86/uav-attention-routing`（2026）。该公开环境原生包含单 UAV、customer deadlines、persistent battery、charger、depot return 与 finite-horizon control；论文实验 N=5 使用 `mission_time=15`、deadline range `3–12`。

代码审计发现 released `get_action_mask()` 只检查“下一节点是否在当前 battery + remaining mission time 下可达”，不保证该动作后仍存在满足全部 customer deadlines 的完整 route；deadline 主要进入 observation / tardiness / potential shaping。我们没有修改外部 checkout，而是用 evaluator-only exact DFS 把**其原生 deadline 字段解释为 hard operational obligations**，检查 continuation existence。

在论文 N=5 evaluation setting 中，扫描到 seed 24：

- 初始存在 zero-tardiness full route `0→1→2→4→3→5→0`；
- customer 2 是 native mask 允许、当前可达且按时的动作，但从它开始不存在满足全部 deadlines + battery + mission-time + depot-return 的 continuation；
- 四条官方 heuristic（NN、Nearest Deadline、Greedy-DB、Battery-Aware NN）的第一步全部落在 destructive action set；
- 原生 episode replay：NN 虽完成并回 depot，但 tardiness `0.79`；Nearest Deadline / Greedy-DB tardiness约 `2.00 / 2.28` 且产生 infeasible termination；Battery-Aware NN 只完成 4/5；
- exact hard-feasible route 在相同原生 `completion_ratio` reward 下 5/5、回 depot、tardiness `0`、infeasible `0`，energy `107.0`，低于 NN 的 `112.1`。

机器审计：`code/evaluation/transfer/audit_uav_attention_future_choice.py`。

边界必须保持：原环境自己的 `completed` flag 允许 tardy service，因此“deadline 必须零迟到”是我们的 operational-obligation transfer interpretation；但 avoidable tardiness / infeasibility / incomplete service 都由原环境自己的 KPI 直接记录，不是我们新造的 reward。当前结果支持 **continuation-aware masking 有真实 external mission surface**，尚不支持“当前 Layer-2 实现优于该论文 learned policy”——learned PPO checkpoint 需单独公平评测。

当前分工因此是：

- **DRL-EC³**：emergency-communication system/resource transfer anchor；
- **uav-attention-routing**：hard-deadline mission-level future-choice red-team；
- 若能找到同时具备 emergency-communication domain + native hard obligations 的公开环境，再替换二者的组合，不为凑 domain 自造环境。
