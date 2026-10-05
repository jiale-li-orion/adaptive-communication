# v0.5：条件收据取证与续接可行性审阅

2026-10-05。审阅基底：`9530200` 的实现；隔离工作树起点为 `5ba01ec`（后者只重复追加了说明段）。本次未重开 TTL、能源门、调度器或新硬件方向。

## 判定

`receipt-race` 是**声明支持集与交付假设下可信的 INFORMATION_POSITIVE 机制见证**。证据来自真正执行过的发送；网关本地收据与中心最终 ACK 分离；无额外取证的共同策略无解、有取证可解。它不是现场发生频率的测量，也不是方法优于普通规则的证据。

三义务 `receipt-chain` 已经实现本轮所需的最小连续扩展：A 的补救与 B/C 的补救共用两次备用额度；B/C 的期限区间重叠；第二次读取同一个 receipt capability；第一条证据后仍存在多个未来；A 失败时继续取证、A 成功时可停止。

**当前最重要的新发现：保完成所需的信息已经足够，不意味着继续取证没有资源价值。** 少查一次可能多耗备用发送。后续方法必须比较任务质量—远端证据—备用消耗的前沿，不能将减少 query 自身当作无代价收益。

## 已复现结果

机器结果：[receipt-continuation-v0.5.json](../../results/benchmark/receipt-continuation-v0.5.json)。以下是穷举七个支持世界的计数，不是七个随机种子，也不假定现场等概率。

| 判别 | 结果 |
|---|---|
| 原两世界 receipt-race | 无取证不可解；最多一次取证可解 |
| 三义务链 | 最多 0/1 次取证均不可解；最多 2 次可解 |
| A 成功收据之后，仍有 4 个相容世界 | 额外取证最少 0 次 |
| A 未收到之后，仍有 3 个相容世界 | 额外取证最少 1 次 |
| 不补 A，越过它最后备用机会 | 在受检续接预算内无解 |
| 最终 ACK 改为提前到达 | 不用付费取证即可解 |
| query 响应延迟至 A 补救机会之后 | 有完整收据内容仍不可解 |
| 恢复三次全失败的第八个世界 | 该世界物理不可行；全支持集不能保证全完成 |

强普通基线只接收公共时刻表、任务、已收到证据与剩余额度，不接收 world id、隐藏成功标记或未来真值。

| 控制器 | 全完成世界 | 远端 query 总数 | 备用发送总数 |
|---|---:|---:|---:|
| 中心 passive + 正常发送/ACK + EDF | 4/7 | 0 | 14 |
| 中心普通 conditional reserve + EDF | 7/7 | 10 | 13 |
| 中心 fixed two reads + EDF | 7/7 | 14 | 9 |
| 网关本地普通规则 | 7/7 | 0 | 9 |

最后一行合法地改变了执行位置，单独报告，**不是相同信息条件下的算法优势**。它说明当前所需证据都属于网关时，不能把中心主动查询说成部署上不可替代。

conditional reserve 与 fixed-read 的两项成本互有取舍；额外四次读取少用了四次备用发送。没有真实成本/预算依据，不指定哪个更优。

plain exact 的 memo 为 676，guided exact 为 56；但 guided 在七个世界都读取两次，plain exact 在 A 成功的四个世界只读取一次。两者只优化可行性，**并未求相同执行成本目标**，不能把 memo 比作为同质量综合收益。新增 continuation oracle 是昂贵参考，非加速算法。

## 必须带着走的信息边界

1. **支持集先验。** 七世界链明确假设“至少一次地面成功”；原两世界还假设两次结果互补。排除全失败不是免费筛选：它改变 planner 的先验。`include_all_failed=True` 现在保留完整父过程作负对照。不能先按真值删除不可行世界，再声称未条件化过程可以可靠全完成。
2. **收据不等于一般网络的交付保证。** 此 fixture 中 accepted 的发送都已有期限内最终 ACK，因此正收据足以解除补救需求。这是模型关系，不是 `gateway_received` 字段天然具有的含义。若现实 capability 仅证明接收、不能证明及时转发，必须保留收据相同而最终交付不同的世界。
3. **“paid”尚未标定。** 当前执行请求、120 s 响应延迟有语义；远端字节、能耗、争用没有标定。不能从 query 数外推节能。return_path/owner 元数据不等于已经模拟运输资源。
4. **公共日程。** 当前可读取时刻在所有世界相同，ordinary baseline 同样得到这些时刻。现场未知 reachability 不能继续被当作公共精确表。禁止向策略暴露 hidden accepted、world id、全局 trace。
5. **收据新鲜度。** “A 已收到”是历史事实，不应凭年龄自行失效；“尚无 B”只对 sample time 之前的观察成立。后续发送/收据/ACK 会改变它对当前选择的作用。当前 receipt query 只支持 sample_delay=0，不能宣称已处理任意延迟采样。

## 唯一继续的结构：共享补救资源下的条件收据续接

保留现有三义务、两次备用额度、已有发送/读取/ACK 能力，不加任务类型、owner、硬件或 catalog noise。

公开状态：release/deadline、完整备用机会表、剩余预算、已发请求及采样/到达时刻、自己发出的普通发送、已到达 ACK、已合法读取的收据。

隐藏状态：未被合法反馈揭示的接收与最终交付结果。未来结果由事先声明的过程支持集生成，不由 query 标签生成。

动作：正常发送、已有备用发送、等待、读取已有 receipt capability。读取只获得已经发生的接收；不读取 future health。业务发送保留信息作用。

最小过程契约：

- A 的最终 ACK 晚于 A 最后补救机会，但其已执行发送的收据可在该机会前返回。
- B/C 的后续补救机会与 A 共用预算，且 B/C 的可用窗口/期限真实重叠。
- 第一次读取后，后续发送尚未产生的新结果仍有分叉；后续读取获得新执行事实。
- 查询是否再进行取决于已花掉的备用额度与未解决义务的窗口可匹配性，不由 stage index 指定。
- 不改变义务分母；不添加“必须 query”奖励。只评价按期交付及三种分别计账的成本。
- 七世界 pilot 是 CONTROLLED_STRESS 条件过程，完整父过程始终保留；前者不能替代后者的风险说明。

来源类别：山区监测、普通传输/收据能力属于既有 source-backed 能力依据；具体卫星 window starts 为仓库几何模型导出的 MODEL_DERIVED 数据；三义务的放置、预算二、60/120 s 延迟、结果互补/至少一成功、receipt→及时 ACK 关系均为当前模型或 CONTROLLED_STRESS，不能升级成现场经验事实。

## Frontier 的准确对象

令 `H_t` 为合法已到达历史及其全部相容世界；`r` 包含剩余预算、未用机会、未完成义务、在途证据与在途发送。

\[
\mathcal A_q(H_t,r)=\{a:\exists\text{共同非预知续接策略，以 }a\text{ 开始，}\
\forall w\in H_t\text{ 满足任务，且每条分支额外读取}\le q\}.
\]

新增 `continuation_frontier` 精确计算小实例中的最少未来读取以及强制当前动作后的上述判别。无法在给定 query 上限内找到策略记为 bounded-unsolved，不伪装成无界不可行。

停止取证有两个不同命题：

- **可停止而仍保完成：**存在不再发起付费读取的共同续接。允许已有 query 返回、被动信息与业务 ACK 继续到达。
- **应停止以优化成本：**进一步取证不能改善声明的资源目标/预算前沿。前一个命题不推出这一个。

最终算法对象必须记录具体 opportunity 的分配与条件续接，不只是 backup 数量；同一 deficit 可对应完全不同的 release/deadline matching 和取证时限。每个条目至少包含：首动作、适用相容历史/资源域、后续观察分支、剩余 query 与备用需求、支撑的机会集合、使支撑失效的执行事件。

已有 `FutureChoiceFrontier` 是乐观 per-world 候选集合和排序器，不能代替这一定义；各世界都有续接，不保证存在共同因果续接。本次 exact 参考每次全量重建，**没有新增增量复用正确性或复杂度主张**。

## Admission gate：只沿这一结构推进

1. **语义门：**共同历史共同动作；未执行发送不产生 receipt；样本在响应途中不被未来覆盖；普通 ACK / send-as-probe 不被禁用。owner-local 读取与 remote acquisition 分账。
2. **支持门：**报告原始支持及物理不可行部分；不能按 hidden truth 筛完世界再给 oracle 新先验。receipts 对最终交付的承诺范围必须由 capability contract 声明。
3. **条件门：**第一条证据后的两个合法分支，同样可用 capability 与时刻，最少未来取证不同；至少一个分支仍含未解决未来。当前链通过。
4. **反事实门：**提前普通 ACK 或增加足够公共补救资源应消除强制取证；证据来不及时应失效；用旧 snapshot 顶替新读取不能偷看未来。
5. **算法门：**至少比较本次 conditional EDF/reserve、fixed batch-read、passive、gateway autonomy、滚动 horizon 2/3/4，以及小实例 exact。质量相同再看 query—备用—计算 Pareto；当前普通规则已覆盖成功率与条件停止，**算法优势尚未通过**。
6. **生成门：**从实际完整几何表改变 release phase/ACK 相对时序/公共预算，先生成后分类，保留无信息收益与不可行格。不得仅留下需要查询的格，不得用添加阶段或增加无关字段制造规模。训练与留出按时间关系/窗口重叠结构划分，重命名义务/世界不改变结果。
7. **部署门：**所有决策依赖均可网关本地取得且授权允许本地执行时，网关自治必须列为合法方案。若它覆盖全部目标，不认领中心远端 acquisition 的系统必要性。

继续方向不变：把 resource-conditioned causal continuation 做成可维护的前沿。下一步补强只围绕**同一过程内窗口分配、取证与备用消耗的前沿**，不是继续堆阶段；若上述普通方法仍完全覆盖，则该分布作为机制回归保留，不升级为方法性能主表。

## 实现与复现

```bash
python3 code/evaluation/benchmark/test_receipt_continuation_v0_5.py
python3 code/evaluation/benchmark/audit_receipt_continuation_v0_5.py
```

第二条默认只向 stdout 输出；用 `--output /tmp/receipt-audit.json` 可另存。核对已登记结果时不要覆盖它。

实现改动：动态 oracle 增加 reached-prefix 与 per-branch query budget；新增 exact continuation reference；新增只读 public-view 的 ordinary reserve/EDF；显式完整八世界父过程；一个核心回归文件。

本轮按用户要求不扩测试体系。核心回归及有界 audit 通过；没有宣称全仓检查通过。隔离工作树的预检发现老 benchmark 多项依赖未跟踪 local_research registry，已停止全量跑，未把这些无关环境问题纳入本轮修复。
