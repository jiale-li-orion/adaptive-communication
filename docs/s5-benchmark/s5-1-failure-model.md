# S5-1 · Runtime Failure Model

> ✅ **本模型的 11 个状态与 11 类故障已全部实现并确定性验证（见 `code/test_failure_model.py`，11/11 PASS）。**
> 代码：`code/operations.py`（lifecycle）、`code/disruption_env.py`（故障产生）、
> `code/test_failure_model.py`（**11/11 PASS**）。

**本段目标**：定义一篇论文里最核心的那个对象——**operation lifecycle 与故障类**。
**不在本段**：episode 格式、工具集、metrics（下一段）。

---

## 为什么需要新的 failure model

现有 agent / wireless-agent 系统对工具调用的默认假设是：

1. 调用是**原子的**；
2. 返回是**二值**的（success / fail）；
3. 观测是**当前的**；
4. 重试是**安全的**。

在灾害通信环境里这四条**同时不成立**。

**而且这不是实现缺陷——是协议层面的空白**（一手核验，见 `s3-novelty/verified-evidence.md`）：

MCP 规范 2026-07-28 版规定超时后发送方「SHOULD cancel the request and stop waiting for a response」，
同时承认「cancellation notifications may arrive after request processing has completed, and **potentially after a response has already been sent**」，
并要求发送方「SHOULD ignore any response to the request that arrives afterward」。

而全规范里 **`outcome` 零命中、`idempot` 零命中**。

> ⇒ 超时 → 取消并停止等待 → 动作**可能已提交** → 丢弃之后才到的响应 → **没有结果不确定状态、没有幂等键**
> ⇒ **任何重试都是被协议层面正当化的重复副作用。**

**这就是本文要研究的对象的定义域。**

---

## Operation lifecycle（11 状态）

用状态机取代二值返回。这是 benchmark 的"真值层"。

| 状态 | 含义 | 是否终态 | 副作用的确定性 |
|---|---|---|---|
| `not_started` | 尚未发出 | 否 | 无副作用 |
| `running` | 已发出，执行中 | 否 | 未知（可能已部分生效） |
| `committed` | 已执行且**已确认** | ✅ | **确定已生效** |
| `failed` | 已执行且**明确失败** | ✅ | **确定未生效** |
| `retryable` | 失败但**可安全重试**（幂等安全） | 否 | 确定未生效 |
| `timeout` | 超时终止 | ✅ | ⚠️ **未知** |
| `outcome_unknown` | **结果不可知**（信道/节点丢失，无法确认） | ✅ | ⚠️ **未知——核心** |
| `stale_result` | 返回的是**过期**结果（来自更早的采样） | ✅ | 取决于工具类 |
| `unavailable` | capability/节点当前不可达（尚未发出或已放弃） | 否 | 无新副作用 |
| `recovering` | 节点已回来，正在对账/重放 | 否 | 待 reconcile 确定 |
| `compensating` | 正在执行补偿动作 | 否 | 有反向副作用 |

**关键设计点**：`timeout` 与 `outcome_unknown` **必须分开**。
- `timeout` 意味着"我方放弃等待"，**不代表对方没执行**；
- `outcome_unknown` 是**认识论状态**：我们知道"不知道"。

现存 benchmark 的 `timeout` 类都是**可见超时**（agent 能判断工具失败了）。
**没有任何 benchmark 把"动作执行了但你看不出来"作为一等注入类**——这是 S3 里认定的**分类学 gap**。

---

## 故障类 → 生成源映射

每个故障类都必须有**物理上真实的来源**，而不是随便注入。下表把故障类接到 S4 已跑通的仿真上。

### 空间维：地形导致的不可达（`code/coverage_map.py`）

| 故障类 | 生成方式 | 实测规模 |
|---|---|---|
| `unavailable`（永久） | 网格点在地形死区内，任何 SF 都不闭合 | **27.7% 的点位** |
| `unavailable`（边缘） | 仅高 SF 闭合 → 可用但吞吐极低 | SF8–SF12 占 29.6% |
| `stale_result` | 节点只能间歇上报 → 网关持有的是若干轮前的值 | 由上报成功率的间隔导出 |

**已实测的地形事实**（决定了这个故障分布长什么样）：
- 决定连通性的是**遮挡，不是距离**：8.4 km / 1169 m 遮挡连不通；12.6 km / 1102 m 遮挡反而能通
- SF 7→12 只多 **14 dB** 灵敏度，而地形遮挡是 **30–50 dB** 量级
  ⇒ **链路自适应（ADR）救不了被挡住的节点**，这类 `unavailable` 不是暂时的

### 时间维：供电导致的掉线—恢复（`code/energy_model.py`）

| 故障类 | 生成方式 |
|---|---|
| `unavailable` → `recovering` | 电池耗尽 → 节点静默 → 充电后回来 |
| `outcome_unknown` | **调用恰好跨越掉线时刻** ← 最有价值的一类 |
| `commit` 后无 ACK | 动作已执行，节点在回 ACK 前掉线 |
| 恢复后**乱序重放** | 节点缓存了多次待发结果，回来时批量上传 |

**已实测的供电事实**：高海拔站点在低温下**电池无法充电**，节点长期静默；掉线是**成片、长时间**的，不是零星抖动。这意味着 `outcome_unknown` 会在**大范围、长时段**上同时发生——这正是单节点故障注入测不出来的。

### 链路抖动维（来自真实轨迹）

| 故障类 | 生成方式 |
|---|---|
| `timeout` / `outcome_unknown` 交替 | 真实 LoRa 轨迹的丢包突发（ChirpBox / LoED / Strasbourg 五年） |
| flapping | 状态在 up/degraded 间反复（⚠️ **必须做迟滞**，否则 5 分钟采样会给出上千次伪切换——我在 IODA 轨迹上实测过：朴素阈值 1102 次迁移，平滑后又把真实中断全抹掉） |

---

## ⭐ 三类"通信专属"的故障（本文的立足点）

这三类**只在信道退化场景下出现**，通用 crash 测试（如 arXiv 2608.03836 的 SIGKILL 矩阵）**测不到**：

**① ACK 丢失型重复副作用**
动作在节点侧**已提交**，但 ACK 在回程丢失。发送方进入 `outcome_unknown`，若盲重试则**副作用被施加两次**。
> 与进程崩溃的区别：崩溃时**进程死了**，可以用 durable log 判断；这里**节点活着、动作执行了、只有确认丢了**。

**② 陈旧观测驱动的动作**
节点长期失联，agent 依据的观测是**几分钟到几小时前**的。它在"当前事实"的假设下做出动作。
> ⚠️ 注意与记忆/推理层的陈旧区分：这里是**效果层**的陈旧（`stale_result`），不是推理层的。

**③ 恢复后的批量重放**
节点回来时**缓存了若干次未送达的结果**，批量上传。agent 若按到达顺序处理，可能**用旧结果覆盖新状态**，或**重复执行已完成的动作**。
> 这类故障需要"恢复屏障 + 对账"，是单次故障注入天然测不到的**时序**问题。

---

## 与已占工作的边界（避免撞车）

| 我们的故障类 | 最接近的已占工作 | 界线 |
|---|---|---|
| `outcome_unknown` | arXiv 2608.02645 的 "timeouts after dispatch" | 它用**注入**的非原子故障；我们用**真实地形/供电**导出，且把它作为**一等类**并量化发生率 |
| 重复副作用 | arXiv 2608.03836 已实测 LangGraph/CrewAI | 它测**进程崩溃**；我们测**信道导致的确认丢失** |
| reconcile | arXiv 2606.03895 libOS "prepare-dispatch-settle" | 它假设**存在可用的对账通道**；我们研究**对账本身也不可达**时怎么办 |
| 恢复语义 | INFOCOM 2026 "Rollback Is Not Undo" | 它是**边缘 DDoS 控制面**、注入扰动；我们是**灾害监测**、真实轨迹 |

---

## 下一段（S5-2）

定 episode 格式：把上面三类故障**编码进 episode 的事件流**，并让 `code/` 的仿真直接产出它。

**验收标准**：一个 episode 跑完，能自动报告
`outcome_unknown 次数` / `重复副作用次数` / `stale 决策次数` / `恢复后乱序事件数`
——这四个数就是 S6 证伪实验的自变量。
