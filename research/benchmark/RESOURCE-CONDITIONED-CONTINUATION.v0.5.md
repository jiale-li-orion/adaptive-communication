# Resource-Conditioned Causal Continuation v0.5

状态：exact small-instance reference。它定义下一阶段算法必须维护的对象，不是最终快速方法。

## 核心对象

对 reached legal history `H_t`，不再只问“还需要几次 query”，而是维护成功续接的联合非支配成本：

```text
(remote receipt queries, satellite rescue sends)
```

所有声明的相容世界都必须按期完成；不使用加权 reward。

由此分开两个停止条件：

1. `can_stop_acquiring`：是否存在 `0` 次额外远端读取的共同成功续接；
2. `query_can_reduce_rescue`：即使已经可以停止取证，继续读取是否仍能减少后续 satellite rescue。

前者描述“信息是否足以保完成”，后者描述“更多信息是否还能释放资源”。二者不能混为一个 stopping rule。

## 三义务链第一条收据后的 exact reference

### A 已在 gateway 收到

相容世界：4。

```text
Pareto = {(0 future queries, 8 satellite sends),
          (4 future queries, 4 satellite sends)}
```

因此：

```text
can_stop_acquiring = True
query_can_reduce_rescue = True
```

含义：现有信息已经足以保证任务完成，但继续读取后续收据仍可能避免不必要的备用发送。

### A 尚未在 gateway 收到

相容世界：3。

```text
Pareto = {(3 future queries, 5 satellite sends)}
```

因此：

```text
can_stop_acquiring = False
```

第二次取证不是固定阶段动作，而是由第一次执行结果及剩余补救资源共同触发。

## 对后续方法的约束

未来快速方法至少需要维护：

- 当前相容执行历史；
- 尚未完成的 obligation 与 release/deadline；
- 具体 terrestrial / satellite opportunities 及竞争关系；
- 剩余 satellite budget；
- in-flight sends / queries / expected feedback；
- 在不同 query/rescue 预算下仍存在的共同非预知续接；
- 使这些续接证明失效的事件。

只维护 backup deficit、字段 freshness 或 query relevance 不够。

算法成功标准也随之固定：在保持该 exact joint continuation frontier 的正确性时，减少全局重解、取证或在线计算；若普通 reserve / fixed-read / wait-ACK 仍覆盖完整前沿，则该分布只保留为机制回归，不升级为方法主表。
