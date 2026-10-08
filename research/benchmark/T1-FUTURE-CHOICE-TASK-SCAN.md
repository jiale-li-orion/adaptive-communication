# T1 Future-Choice Task Scan

状态：**CURRENT TASK-SELECTION AUTHORITY / NO NEW GENERATOR VERSION**

依据：`cache05.md`、`cache06.md`、`调研cache.md`、`TASK-SURFACE-REGISTRY.v0.1.json`、`SYSTEM-MODEL-v1.md`。

## 1. 目标

当前不再增加 generator 版本、evidence capability、process family 或 stress axis。唯一问题是：

> 现有 T1 operational surfaces 中，哪一类任务天然要求 policy 维护 future completion choices，而不是靠局部 VoI、EDF、短视 flow 或 depth-k 就能稳定解决？

Future-choice 候选至少同时满足：

1. 存在多个跨阶段 operational obligations；
2. 至少一种资源或状态跨阶段持续存在，而不是每时隙自动重置；
3. 当前合法动作会改变后续可完成方案，而不只是当前 reward；
4. 后续 workload / connectivity / evidence 仍会变化，当前不能一次性看全；
5. first irreversible loss 可以由独立 exact/counterfactual reference 定位；
6. ordinary EDF / myopic flow / finite-horizon planner 必须作为强否决基线。

## 2. 现有 T1 surfaces

| Surface | Future-choice 必要结构 | 当前判断 | 处置 |
|---|---|---|---|
| `S0_STEADY_MONITORING` | workload 固定，长期状态弱 | 不足 | easy / conformance |
| `S1_WARNING_CADENCE_TRANSITION` | 后续 workload 会由外部 authority 改变 | **必要但不充分** | 作为 S7 workload-revision 组成 |
| `S2_INTERMITTENT_BACKHAUL_FALLBACK` | opportunity 不确定、可恢复/再中断 | **必要但单独不充分** | 作为 S7 connectivity 组成 |
| `S3_ENERGY_CONSTRAINED_CONTINUITY` | battery/harvest 跨阶段持续并被动作真实消耗 | **核心候选状态** | 与 S1/S2 组合 |
| `S4_OUTAGE_CACHE_RETENTION` | queue/cache 跨阶段持续 | 可提供 state coupling，但 source 要求 ≥7d cache，不得人为缩小制造 hardness | 只用真实 occupancy / ACK lifecycle |
| `S5_RECOVERY_RECONCILIATION` | reconnect 后 backlog + fresh work 竞争 | 有潜力，但 source 未定义通用 backlog-vs-fresh sacrifice priority | objective ambiguity 未解决前不做主 task |
| `S6_HETEROGENEOUS_PATH_PRIORITY` | 多路径与 fallback authority | capability 层，不是独立 hardness | 作为合法 action/path 边界 |
| `S7_COMPOUND_CONTINUITY` | task revision + intermittent opportunities + persistent resources + recovery | **PRIMARY FUTURE-CHOICE CANDIDATE** | 当前唯一主探索对象 |

## 3. 为什么 S2 gateway backhaul 单独不够

现有 `JointControlPlane` 的 gateway backup 是固定稀疏发送机会与每包容量约束。一次 backup forwarding 消耗当前机会/字节，但下一 backup slot 会重新出现；如果任务 workload 本身稳定，EDF、max-coverage、myopic residual-flow 很容易把问题局部化。

这与 corrected gateway pilot 的结果一致：自然 ACK/timeout 确实有决策价值，但已找到的 candidate 被 myopic flow / depth-2/3 flow baseline 饱和。

因此不能继续通过增加 backhaul process 复杂度寻找方法空间。

## 4. S7 中真正值得测的 future-choice 结构

现有 full simulator 已经具备，不需要新增 capability：

```text
初始 routine monitoring
→ 外部 authority 发布 warning/cadence revision
→ workload 变密，新增 future obligations

同时：
primary/access 可中断与恢复
gateway queue/store-and-forward 持续存在
node battery/harvest 持续存在
gateway backup / terminal fallback / access assist 受既有 authority 约束
```

最重要的状态是 **persistent battery / resource state**。与 per-slot backup capacity 不同，早期通信、采样或 terminal fallback 会改变后续 warning 阶段还能执行哪些动作。

最小 scientific witness 应满足：

```text
same lawful prefix h_t
same future exogenous process

early action a:
  当前 obligation 看起来推进更快
  但消耗 persistent resource
  → warning revision 后所有 completion continuations 消失

early action b:
  当前保持 / 等待 / 使用可恢复路径
  → 保留至少一条后续 all-obligation continuation
```

差异必须由 source/task + existing simulator dynamics 自然产生，不能靠手写“预留给未来”的 quota 或人为缩小 cache。

## 5. 与现有 ASC work 的接口

当前不需要把 ASC 相关工作只放进 related work。Future-choice 方法可以直接作为现有 closed-loop ASC scheduler 的 feasibility layer：

- GOSC 类方法给 message / transmission 一个 task value，再做 what/when/how-reliable scheduling；future-choice layer 可提供 hard obligation-preserving feasibility mask / certificate，而不是另一个 scalar value。
- WM-CDT 类方法用 rollout / intervention 算长期 semantic contribution；future-choice layer可把 hard deadline/resource feasibility 从 expected return 中拆出，避免高 return 动作删除唯一合法 continuation。
- RAMSemCom 类方法在当前信息不足时主动补传；future-choice layer可判断“当前已经足够做安全 action”以及 retrieval 本身是否会挤压后续关键 communication opportunity。

因此 method novelty 不应写成“考虑长期价值”或“主动获取信息”，而应写成：

> **maintain and update the feasible completion set / conditional frontier under communication commitments, and use it as a deterministic correctness layer beneath learned or value-based ASC policies.**

## 6. 与已有应急通信优化的接口

现有 emergency communication 主流工作大量优化 UAV coverage、routing、trajectory、bandwidth、power、MEC offloading 与 anti-jamming。它们可以提供物理/系统 benchmark 和强优化基线，但多数优化目标是 throughput、coverage、latency、energy 或 weighted reward，而不是 source-grounded operational obligation continuation。

因此有两种合法接法：

1. **method transfer**：在其环境中加入硬 mission obligations，将 future-choice layer 作为 constrained planner / safety layer；
2. **system baseline**：保留其 resource-allocation/MPC/RL 作为强基线，在我们的 pre-disaster monitoring task 上比较。

当前不建议为了“更像应急通信论文”转成 post-disaster UAV deployment；这会丢失原始山区灾前需求和已有 source/substrate 资产。

## 7. 当前执行顺序

```text
不再新增 benchmark version
→ S7 only
→ 从现有 O6/full-sim 抽取 warning × intermittent-connectivity × persistent-energy witness
→ first irreversible loss / preserving alternative exact or bounded reference
→ EDF / EnergyAware / backup-maxcov / myopic-flow / depth-k / receding red-team
→ 若仍有 survivor：Layer-2 future-choice 回归主方法
→ 若全部被覆盖：保留 benchmark / negative finding，停止为 method 造 task
```
