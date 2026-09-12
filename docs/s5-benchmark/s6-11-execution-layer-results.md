# 执行层在 WirelessOpsBench 任务契约上的结果

复现命令：

```bash
export PYTHONPATH="$PWD/libs/pylibs"
python3 code/wirelessops_adapter.py --limit 120 --ticks 1200 --rounds 1,2,4,8,16,32,64
```

原始输出在 `results/wirelessops_execution_layer.txt`。120 个公开任务（WCNS 与 WCMSA 各取前若干），Gilbert-Elliott 信道，每个 horizon 跑满 7,680 个操作周期。

## 一、实验设定的两处约束

任务正确性不重新评分。公开包扣留了 scoring 谓词，重评等于替 benchmark 造答案。授权正确性由接入层按 `legal_transitions` 强制，四个策略的授权违规次数全为 0，因此测得的差异全部来自执行层。

每个周期恰好意图一次逻辑写入。重复副作用因此可以精确计数为"落地的写入数减已驱动的周期数"，不从轨迹推断。

## 二、2×2 消融

两个机制正交：重试是否复用同一条逻辑写入的身份，以及是否向实体查询本次写入是否落地、查询是否限定在本次写入上。

| 策略 | 身份 | 验证 | 来源 |
|---|---|---|---|
| `naive` | 每次尝试新身份 | 无 | agent 默认行为 |
| `stable_key_only` | 周期内稳定 | 无 | 只取幂等键 |
| `verified_wrapper` | 每次尝试新身份 | 非限定 | arXiv `2608.02645` 的做法 |
| `lifecycle` | 周期内稳定 | cycle 限定 | 本文 |

## 三、结果

每千周期计数，七个 horizon。

| horizon | 策略 | 重复/1k | 零效果/1k | sink 去重 |
|---:|---|---:|---:|---:|
| 1 | naive | 225.0 | 0.0 | 0 |
| 1 | stable_key_only | 0.0 | 0.0 | 27 |
| 1 | verified_wrapper | 91.7 | **0.0** | 0 |
| 1 | lifecycle | 0.0 | 0.0 | 11 |
| 8 | naive | 287.5 | 12.5 | 0 |
| 8 | stable_key_only | 0.0 | 12.5 | 276 |
| 8 | verified_wrapper | 143.8 | **54.2** | 0 |
| 8 | lifecycle | 0.0 | 4.2 | 143 |
| 32 | naive | 274.5 | 9.1 | 0 |
| 32 | stable_key_only | 0.0 | 9.1 | 1054 |
| 32 | verified_wrapper | 135.4 | **73.4** | 0 |
| 32 | lifecycle | 0.0 | 4.9 | 543 |
| 64 | naive | 280.7 | 8.1 | 0 |
| 64 | stable_key_only | 0.0 | 8.1 | 2156 |
| 64 | verified_wrapper | 132.4 | **73.2** | 0 |
| 64 | lifecycle | 0.0 | 4.3 | 1081 |

三条结论。

**身份稳定性单独就消除了全部重复。** `stable_key_only` 在所有 horizon 上重复为 0，其 sink 去重计数与 `naive` 的重复计数逐 horizon 精确相等：27、62、140、276、554、1054、2156。每一个 naive 造成的重复，都是稳定键本可合并掉的那一次重发。`naive` 的重复率在 225 至 292 每千周期之间基本不随 horizon 变化，因此这不是短 horizon 的人为产物，而是按周期线性累积的。

**非限定验证比不验证更差，且只在重复 horizon 下暴露。** `verified_wrapper` 的零效果率为 0.0、33.3、43.8、54.2、67.7、73.4、73.2 每千周期，而 `naive` 为 0.0、12.5、16.7、12.5、12.5、9.1、8.1，相差 6 至 9 倍。horizon 为 1 时两者都是 0.0，缺陷不可见。原因是其谓词问的是"此实体上是否曾应用过 `commit_policy`"，重复 horizon 下该问题会被更早周期的写入回答为是，于是包装器判定完成并停止，本周期该发生的写入从未发生。

**cycle 限定的验证才是零效果率的解。** `lifecycle` 的零效果率为 0.0、0.0、2.1、4.2、2.6、4.9、4.3，相对 `stable_key_only` 下降 2 至 4 倍。代价体现在验证流量与未决操作上：horizon 64 时 `lifecycle` 的 sink 去重 1081 次、验证返回 `unknown` 2145 次、未决操作 1663 个，而 `stable_key_only` 分别为 2156、46、1965。

## 四、这一结果针对的是什么

`verified_wrapper` 相对 `naive` 把重复从 2156 降到 1017，看起来是一次改进。它把重复换成的是静默的不执行：562 个周期的写入根本没有落地。只统计任务结果与重复率的评测会把 `verified_wrapper` 排为更优解。

这正是不加执行层就测不出来的东西。WirelessOpsBench 的七类条件全部刻画证据账本的可信度，其 episode 把工具调用视为必然送达，因此重复与零效果这两条轴都不在其故障表内。公开包还不含 baseline 分数，`2608.02645` 的 verified wrapper 在该 benchmark 上的表现也无从对照。

## 五、效力威胁

CQI 是本项目提供的替代量，公开包不含 `ray_tracing` 实现与证据内容，该参数属于假定层，须做敏感性扫描而非当作实测值。

接入层把 bench 任务的三类角色映射到真实地形节点上，节点选择来自 SRTM 覆盖网格，映射本身是设计选择。

`unknown` 的验证结果在两个策略下都未做超时重试以外的处理，验证不可用时的最优策略未做搜索。

全部数值为本文自己的 runtime 在公开开发集上的结果，不是该 benchmark 的官方分数。
