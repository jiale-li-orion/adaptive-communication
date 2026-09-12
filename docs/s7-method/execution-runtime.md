# 方法：面向中断通信的远端操作运行时

论文 Section III 初稿。

## A. 研究问题：通信引起的执行歧义

系统里有一个 agent runtime，它通过无线链路调用远端通信实体——网关、中继、UAV-BS 或其他 capability。控制请求与执行结果穿过同一条可能中断的路径，没有可靠的带外确认通道。

对一次有副作用的操作 $o$，agent 发出请求后等到超时，能确定的只有

$$\text{response was not observed}$$

推不出

$$\text{effect was not executed}$$

远端可能根本没收到请求，可能收到但执行失败，也可能已经执行而回执丢失。节点此后还可能掉线、恢复、重启，于是旧操作与新操作跨越多个连通期。

这把经典的"无线链路中断"变成了一个**远端执行歧义**问题：通信故障开始影响控制操作的语义，而不只是影响分组投递概率。

本文研究的是这一层。关键的新对象是

$$\text{physical execution state} \neq \text{runtime knowledge state}$$

大多数通信恢复工作考虑的是 $\text{network state} \rightarrow \text{choose recovery action}$；本文的模型多了一层

$$\text{choose action} \rightarrow \text{uncertain remote execution} \rightarrow \text{reconciliation}$$

## B. 三个正交维度

早先的实现把所有东西塞进一个 11 状态枚举，其中有明确的自相矛盾：`outcome_unknown` 同时出现在终态集合里和"未决"查询的返回里。四个不同维度的量被混为一谈——runtime 自己的生命周期、远端物理效果、agent 掌握的证据、实体的可达性。

现在拆开。一次操作记录

```text
Operation
    operation_id, entity_id, capability, arguments_hash
    logical_intent, epoch, side_effect
    created_at, first_dispatch_at, attempts

    lifecycle       # runtime 拥有
    outcome         # 远端物理效果
    observation     # agent 当前的证据
    settled_at
    detail          # 与种类相关的具体事实，不构成新状态
```

**lifecycle** 只描述 runtime 自己拥有的过程：`registered → running → stopping → settled`。比通用 job runtime 多一个 `registered`，因为无线操作必须先持久登记再发送。

**outcome** 描述远端效果：`unknown | applied | rejected | failed | superseded`。`unknown` 是一个正当的、常常是永久的答案。

**observation** 描述 agent 手里的证据：`fresh | unknown | stale | unavailable`。

旧状态因此各归其位：`timeout` 成为一个 **wait event**，不是状态；`outcome_unknown` 表达为 `outcome=unknown`；`stale_result` 是 observation；`unavailable` 是实体观测；`recovering` 是恢复过程；`compensating` 是另一个 operation。

## C. 一次远端操作的完整生命周期

agent 只产生一个逻辑动作，例如 `set_sampling_rate(node_17, 5min)`。从这一刻起，可靠性不再由 agent 的推理负责，而由 runtime 接管。

**登记。** runtime 生成稳定的 `operation_id` 与单调递增的 `epoch`，写入 registry，然后才允许发送。顺序不能反：先发包后记账会留下一个窗口，协调者恰在此刻崩溃就会产生一个远端可能已执行、而本地完全不知道存在过的幽灵操作。

**发送。** 请求携带 `operation_id`、`entity_id`、`epoch`、`capability`、`arguments`。重试不产生新的逻辑操作，它始终重发同一个 `operation_id + epoch`。

**远端接受。** 实体维护最小的持久元数据：`last_accepted_epoch` 与可选的 `operation_id → outcome` 回执。

```text
epoch <  last_accepted_epoch  -> 拒绝（过期）
epoch == last_accepted_epoch  -> 已接受过，返回此前记录的结果
epoch >  last_accepted_epoch  -> 原子地：应用效果、推进 epoch、记录回执
```

第三步的原子性是必需的。如果"应用效果"与"推进 epoch"不在同一个接受边界内，两者之间崩溃就会重新打开 epoch 本来要关闭的重复窗口。

**等待。** 见 D 节。

**调和。** 见 E 节。

**结算。** 见 F 节。

## D. Timeout 的语义

通用 agent 框架通常把 timeout 暴露成一个 tool error，然后由模型下一轮自己决定要不要重试。这个语义是错的：它把"我方停止等待"和"远端没有执行"混为一谈。

本 runtime 规定

$$\text{wait\_timeout} \neq \text{execution\_failure}$$

回执没回来时，runtime 的状态是

```text
lifecycle   = running
outcome     = unknown
observation = unknown
```

操作继续留在 registry 里。timeout 只是协调者的一个本地观测事件 `WAIT_TIMEOUT(op_id, t)`，之后策略才能决定：继续等、查询、重试、调和、放弃、或补偿。

这条语义之所以重要，是因为**结果未知可能持续数小时**。用 ChirpBox 实测轨迹拟合（21 节点、420 条有向链路、20,913 个逐小时快照）：链路可用率 68.75%，平均中断突发 6.38 h，而中断时长分布的 p99 是 42 h。也就是说 `outcome_unknown` 不是一次短 RPC 超时，它可能横跨整个夜间。一个把超时当失败处理的运行时，会在每个夜里把大量实际已执行的操作当成未执行来处理。

## E. 调和：不允许模型重新猜

实体恢复连接后，runtime 检查所有属于该实体、`outcome=unknown` 的操作，逐一做**限定范围的调和**：

```text
read_operation(operation_id)   优先：operation 级回执
read_version()                 退化：epoch 比较
read_current_state()           兜底：当前状态
```

结果有四种：远端记录了该 `operation_id` → `applied`；远端 epoch 大于该操作的 epoch → `superseded`；远端 epoch 小于该操作的 epoch → 该写入从未成为当前值，同 epoch 重试是安全的；远端不可达 → 保持 unknown。

**范围限定不是细节。** 问"这个实体上是否曾经出现过这个效果"会被更早的操作回答成"是"，于是策略停止重试一次根本没发生的写入。这类谓词在一锤子买卖的 episode 里是对的，在重复运行的监测任务里会系统性地把重复换成静默丢失。本文的实验已经量化过这个效应。

正确的问法是"操作 $o$ / epoch $e$ 是否生效"，而不是"这个效果是否曾经出现过"。

## F. 结算 first-wins

runtime 已通过调和确认 `op42 = superseded`，十分钟后一个迟到的 ACK 回来报告成功。它不能把 registry 改回 `applied`。

终态证据一旦按规则结算，后来的分组只能成为 `late_evidence` 记录，不能改写操作真值。否则延迟到达的确认本身又会造成状态回滚。

## G. Agent 与 runtime 的边界

agent 只负责选择 capability、选择逻辑动作。runtime 在动作之外包住登记、身份分配、epoch 分配、发送、等待、调和、重试许可与结算。

这条边界让实验的因果变干净：可以固定完全相同的 LLM 轨迹与相同的动作序列，只替换 runtime。

$$\text{same agent} + \text{same action} + \text{same channel} + \text{different runtime}$$

论文因此不需要证明"我的 agent 更聪明"。

## H. 三条贡献

**一、通信引起的执行歧义模型。** 建立一个 agent 控制模型，其中观测与执行共用同一条不可靠链路，由此 timeout 只反映本地等待截止，无法确定远端效果；实体变动、回执丢失、延迟观测与协调者重启会产生跨时间存续的未决操作。核心新对象是物理执行状态与 runtime 知识状态的分离。

**二、面向中断通信的版本化操作生命周期。** 基于稳定操作身份、runtime 拥有的生命周期、持久 epoch fencing、first-wins 结算与 operation 级限定调和，构造一个中断容忍的执行协议。

定位需要写准。运行时应拥有身份与生命周期、超时不应取消工作、终态一次写成，这些是通用的运行时设计原则，本文不据此声称贡献。进程内执行与远端执行的区别在于前者依赖执行方最终返回完成信号，因此不存在"已执行而完成证据永远丢失"这种状态；本文补的正是这一种状态及其处置协议。

本文的增量应表述为：

> We extend a runtime-owned operation lifecycle from process-local execution to non-atomic remote actuation over disrupted communication links.

新增的是远端效果不确定性、持久远端 epoch、无线重连、operation 级限定调和与过期重放 fencing。

**三、真实通信条件下的系统刻画。** 真实 DEM 加地形传播、ChirpBox 相关中断、能量导致的静默与实体变动共同回答"这个执行问题在无线通信系统里是不是玩具问题"。实测数字：可用率 68.75%，平均中断突发 6.38 h，同丢失率下 i.i.d. 只预测 1.45 h，突发性被低估 4.4 倍。这些是把 durable lifecycle 与普通重试循环区分开的物理依据。

## I. 三个性质

方法不能只报成功率，否则看起来仍像一个工程 wrapper。在以下假设下——远端 epoch 持久化、效果应用与 epoch 推进原子、同一逻辑操作的重试复用同一 epoch——可以给出三条性质。

**At-most-once acceptance。** 对任意逻辑操作 $o$，epoch $e_o$ 被远端接受的次数至多一次。首次成功后有 $E_{\text{remote}} = e_o$，此后所有重试满足 $e_o \le E_{\text{remote}}$，被 fencing 规则拒绝。注意只能声称 at-most-once acceptance，不能声称 exactly-once：第一次请求从未到达时，效果可能根本不发生。

**No stale overwrite。** 若 $e_j > e_i$，一旦 $o_j$ 被接受，任何迟到的 $o_i$ 都不能覆盖它。这直接解决分区、延迟重放与重连后的旧命令污染。

**Eventual resolution under eventual reachability。** 若实体最终保持可达且其远端执行元数据未丢失，未决操作经调和最终能落到 `applied | rejected | superseded | failed`。若元数据随远端重启丢失，则不能保证解决。这条限制必须显式写出，因为它说明协议保证依赖远端持久化——而本文的实验同样说明，仅靠 agent 侧的技巧解决不了这个问题。

三条性质在 `code/operations.py` 中可执行验证，连同一条负面结果：客户端只复用幂等键而远端不认该键时，5 次重试全部生效；epoch fencing 下 5 次重试只被接受 1 次。远端配合是幂等性的前提，这一点属于方法陈述的一部分。

## J. 主图

```text
LLM / Agent
    |
    | logical action
    v
+-----------------------------------+
| Operation Runtime                 |
|   identity / epoch assignment     |
|   lifecycle registry              |
|   wait semantics                  |
|   reconciliation (operation-scoped)|
|   first-wins settlement           |
+-----------------------------------+
           |
           | unreliable control + observation channel
           v
+-----------------------------------+
| Communication Entity              |
|   capability executor             |
|   durable epoch                   |
|   operation receipt               |
+-----------------------------------+
           |
           v
山区 LoRa 节点 / 网关 / UAV 中继 / 卫星回传
```

## K. 运行时不变量的强制

协议的正确性论证强度受限于运行时的强制力度。若 runtime 静默接受一次乱序转换，关于正确性的论证前提就不成立。因此 runtime 自己维护每次操作的转换阶段并在非法时立即抛错，而非依赖调用方守规矩：

| 非法转换 | 处理 |
|---|---|
| 未登记即结算 | `Violation` |
| 未发送即调和 | `Violation` |
| 效果已确定后重发 | `Violation`（那是第二次逻辑写入，不是重试） |
| 操作未注册进本 registry | `Violation` |
| 重试改变 logical_intent 或 epoch | `Violation` |

五条均已实测会抛出。注意第四行与"结果未知时允许重发"并不矛盾：`outcome=unknown` 的操作**可以**重发，这正是 fencing 起作用的前提；被禁止的是在效果已经确定之后再发。

## 待补

- Compensating operation 目前只是"另一个 operation"这一句，缺少补偿日志与可补偿性判定的形式化。
- 协调者重启后的 registry 恢复尚未实现持久化，当前 `F11` 只做计数。
- 性质三依赖的"远端元数据未丢失"需要给出量化：远端在什么持久化强度下能把未决率压到多少。
- 与 `2608.02645` 的对照需要补一条同轨迹不同 runtime 的实测，目前只有定性区分。
