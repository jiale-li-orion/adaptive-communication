# Runtime failure model

本文件定义 operation lifecycle 与故障类，即 benchmark 的真值层。episode 格式、工具集与 metrics 不在本文件范围内。

11 个状态与 11 类故障已全部实现并做确定性验证，代码分布在 `code/operations.py`（lifecycle）、`code/disruption_env.py`（故障产生）与 `code/test_failure_model.py`（11/11 通过）。

## 为什么需要生命周期而非二值返回

agent 框架对工具调用的默认假设有四项：调用是原子的，返回是二值的，观测是当前的，重试是安全的。在本文场景中这四条同时失效。

关键的结构性原因是控制命令与数据走同一条链路：协调通信实体所依赖的命令，必须通过被协调的那条不可靠链路下达。命令超时后，发送方停止等待，但该命令可能已经在远侧执行；此后到达的响应已经没有接收方。现有协议在这一处留下空白，MCP 规范 2026-07-28 版是最直接的例证：它规定了超时后发送方 SHOULD cancel the request and stop waiting for a response，承认 cancellation notifications may arrive after request processing has completed, and potentially after a response has already been sent，并要求发送方 SHOULD ignore any response to the request that arrives afterward，而整份规范中没有结果不确定状态，也没有幂等语义（一手核验见 `docs/s3-novelty/verified-evidence.md`）。

## 状态集合

| 状态 | 含义 | 终态 | 副作用确定性 |
|---|---|---|---|
| `not_started` | 尚未发出 | 否 | 无副作用 |
| `running` | 已发出，执行中 | 否 | 未知，可能已部分生效 |
| `committed` | 已执行且已确认 | 是 | 确定已生效 |
| `failed` | 已执行且明确失败 | 是 | 确定未生效 |
| `retryable` | 失败但可安全重试 | 否 | 确定未生效 |
| `timeout` | 超时终止 | 是 | 未知 |
| `outcome_unknown` | 结果不可知 | 是 | 未知 |
| `stale_result` | 返回更早采样得到的值 | 是 | 取决于工具类 |
| `unavailable` | 节点或 capability 当前不可达 | 否 | 无新副作用 |
| `recovering` | 节点已回来，正在对账或重放 | 否 | 待 reconcile 确定 |
| `compensating` | 正在执行补偿动作 | 否 | 有反向副作用 |

`timeout` 与 `outcome_unknown` 是两回事，分开记录才不丢信息。`timeout` 只说明我方放弃等待，不说明远侧未执行。`outcome_unknown` 是认识论状态，它记录了"我们不知道"。现有 benchmark 的 `timeout` 类都是可见超时，agent 能据此判断工具失败；尚无 benchmark 把动作已执行但结果不可见作为一等注入类。

## 故障类与生成源

每个故障类都接在已跑通的仿真上，来源是地形、供电与真实轨迹，而非任意注入。

### 空间维：地形导致的不可达

生成器为 `code/coverage_map.py`。

| 故障类 | 生成方式 | 实测规模 |
|---|---|---|
| `unavailable`（永久） | 网格点落在地形死区内，任何 SF 都不闭合 | 88.5% 的点位 |
| `unavailable`（边缘） | 仅高 SF 闭合，可用但吞吐极低 | SF8 至 SF12 占 29.6% |
| `stale_result` | 节点间歇上报，网关持有的是若干轮之前的值 | 由上报成功率与间隔导出 |

遮挡决定连通性，距离不是决定因素：8.37 km 处有 1169 m 遮挡的点位损耗 217.0 dB，12.61 km 处只有 1102 m 遮挡的点位损耗 201.2 dB。SF 从 7 提到 12 只增加 14 dB 灵敏度，地形遮挡的超额损耗在 71 至 107 dB 量级，因此 ADR 无法救回被挡住的节点，这类 `unavailable` 是持续的而非暂时的。

### 时间维：供电导致的掉线与恢复

生成器为 `code/energy.py` 与 `code/energy_model.py`。

| 故障类 | 生成方式 |
|---|---|
| `unavailable` 转 `recovering` | 电池耗尽使节点静默，充电后恢复 |
| `outcome_unknown` | 调用跨越掉线时刻 |
| commit 后无 ACK | 动作已执行，节点在回 ACK 前掉线 |
| 恢复后乱序重放 | 节点缓存多次待发结果，回来时批量上传 |

高海拔站点在低温下无法充电，节点长期静默，掉线呈成片、长时段形态而非零星抖动。`outcome_unknown` 因此会在很大范围与很长时间上同时发生，这是单节点故障注入测不出来的分布特征。

### 链路抖动维：来自真实轨迹

| 故障类 | 生成方式 |
|---|---|
| `timeout` 与 `outcome_unknown` 交替 | 真实 LoRa 轨迹中的丢包突发（ChirpBox、LoED、Strasbourg 五年） |
| flapping | 状态在 up 与 degraded 之间反复 |

flapping 的检测需要迟滞。在 IODA 轨迹上实测，朴素阈值在 5 分钟采样下产生 1102 次状态迁移，而加大平滑窗口后真实中断被一并抹掉。这个权衡是 benchmark 设计的组成部分，不能当作调参细节隐藏。

## 三类通信专属故障

下面三类只在信道退化场景下出现，进程级故障测试（例如 arXiv `2608.03836` 的 SIGKILL 矩阵）覆盖不到它们。

**ACK 丢失导致的重复副作用。** 动作在节点侧已提交，ACK 在回程丢失，发送方进入 `outcome_unknown`；盲重试会把同一副作用施加两次。与进程崩溃的区别在于，崩溃时进程已死，可用 durable log 判定；这里节点存活、动作已执行，只有确认丢失。

**陈旧观测驱动的动作。** 节点长期失联时，agent 依据的观测是几分钟到几小时之前的，而它按当前事实行动。这里陈旧发生在效果层，即 `stale_result`，与推理层或记忆层的陈旧不同。

**恢复后的批量重放。** 节点回来时缓存了若干次未送达的结果并批量上传。agent 若按到达顺序处理，会用旧结果覆盖新状态，或重复执行已完成的动作。这类故障依赖时序，单次故障注入无法复现，需要恢复屏障与对账机制。

## 与既有工作的边界

| 本文故障类 | 最接近的既有工作 | 分界 |
|---|---|---|
| `outcome_unknown` | arXiv `2608.02645` 的 timeouts after dispatch | 该文用注入的非原子故障；本文由真实地形与供电导出，并把结果不可知作为一等类量化发生率 |
| 重复副作用 | arXiv `2608.03836` 已实测 LangGraph 与 CrewAI | 该文测进程崩溃；本文测信道导致的确认丢失 |
| reconcile | arXiv `2606.03895` 的 prepare-dispatch-settle | 该文假设对账通道可用；本文研究对账本身也不可达的情形 |
| 恢复语义 | INFOCOM 2026 "Rollback Is Not Undo" | 该文场景为边缘 DDoS 控制面并注入扰动；本文场景为灾害监测并使用真实轨迹 |

## 后续

episode 格式需要把上述故障编码进事件流，并让 `code/` 的仿真直接产出。验收标准是一个 episode 跑完后能自动报告 `outcome_unknown` 次数、重复副作用次数、陈旧决策次数与恢复后乱序事件数，这四个量构成后续证伪实验的自变量。
