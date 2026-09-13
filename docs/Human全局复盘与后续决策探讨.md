我重新把 repo 从早期 runtime、三轮公平化、Task pivot、instance closure、第二阶段三轨、一直读到这次五小时 STOP。

现在这条实验史逐渐逼出了一条很统一的东西。只是我们一直在拿不同名字碰它：`runtime correctness`、energy-aware、AoI、burstiness、stale evidence、continuous config admission。

它们最后撞到的都是同一个限制，即**做一次自适应控制之前，默认假设自己以后还能及时看到、及时改。山区间歇通信把这个假设打碎了。**

先用大白话把 repo 到底发生了什么重新讲一遍。

最早那版项目其实想证明，Agent 发出的操作经过断连、重试、乱序、重启之后，一个有身份、版本、日志、原子执行的 runtime 会比普通执行可靠。

后来公平化审计把几个很漂亮的优势一个个打掉了。比如“重启后领先 14.1 点”，最后发现是runtime有持久状态，而 baseline 被清空了；给 baseline 同等持久化能力后结果反转。

还有一些差距来自排序缺陷、identity 少字段、oracle 本身不是上界。

这一阶段最值钱的结果不是某个数字，而是发现，多所谓 agent infra 优势，实际上只是偷偷给了一边更多能力，或者评分器/任务把问题做成了擅长的样子。repo 后来专门把这些写成 D37–D43。

然后又发现更严重的问题，期 task 根本没什么“决策”。中心一开始就知道两个 risk window 什么时候开始、什么时候结束，要做的事情几乎就是，点给 8 个节点写一次 risk profile，再到点写回来。所以成熟的设备 shadow/固定调度赢很正常。这个 task 连方法赢和方法输都解释不了，因为它实际测的是“谁更会把预先知道的配置送过去”。因此整条方法主张被暂停，重新从真实监测义务和设备能力往上建。

Task v1.1 建起来之后，一个很重要的事实开始反复出现，**自治已经很强**。
事件触发、事件加密采样、本地缓存、自动补发都不需要中心。于是事件采集/事件交付那两列从头到尾都不随中心策略变化。中心真正能动的只有两个很朴素的东西，采样间隔和上报周期。

LLM 再聪明也没法凭空创造控制权。Agent 的价值上限先由 action surface 和 local autonomy 决定。如果本地已经把真正关键的突发业务接管了，中心 Agent 剩下的就是慢时标资源管理。所以突破口可能是它比本地自治多知道什么、多能做什么，而不是LLM 能不能想出更好的策略。

接下来是能量实验。最开始 dense 看起来挺好：采得多、报得勤，服务会上升。等能量真正 binding 以后，结果突然翻转：`dense600` 把节点自己采死了。这时 contract / atomic execution 居然开始改善业务。乍看像“执行正确性终于有用了”，后来把过程拆开却发现，它们主要是把密集配置晚一点送到节点。naive 大家 4.17h 一起进入 dense；atomic 有的节点拖到 5–11h 才切进去，于是少采 105 次、少耗大量采样能量，最后少死节点。总耗差里 97% 来自少采样，空口成本只有 3%。

这个实验解释，atomicity 当时救节点，不是因为事务语义神奇地提高了业务正确性，而是因为它无意中成了一个 actuator throttle。

也就是说，真正有用的变量是“高耗能配置从什么时候开始生效、持续多久”，而不是 generation number 本身。

执行时机 / 驻留时间 / 资源暴露，比隔离防护、生成机制、精确一次更加重要。

然后真实天气进来，又把“资源状态”这个概念往前推了一步。一开始也想把系统压成一个 `autonomy_margin`，后来发现完全不行：两条窗口 margin 都是 1.37，一条 84.5%，另一条 12.5%；后者采能总量甚至高 15 倍，却因为电来得太晚，节点在太阳出来之前已经死了。再加上事件连采，routine-only margin 甚至会把实际全灭的窗口判成可行。还有 24h 步长扫描刚好和昼夜周期锁相，365 个窗口一个不可行都看不到，而全 8760 个起点里有 31.7% 不可行。

**这种系统不能只看“有多少资源”，必须看“资源什么时候来、动作什么时候发生、缓存有多大、死掉以后还能不能回来”。**

换到控制理论语言，就是 trajectory 和 state constraints 比平均量重要。换到 Agent infra 语言，就是 planner 不能只拿一个 summary 然后做决策；某些 summary 会把一个因果上完全不同的世界压成同一个数字。

再往后，遥测实验又出了一个很有意思的反直觉：**没信息有时比错信息安全。** `ea_nb` 丢掉 99% SoC 报告只掉很少，因为它没读数就少动，行为自然靠近 `local`；但把电量系统性高估 3 倍，性能掉得明显，因为“有一个错误但看起来可信的数字”会主动把节点推到 dense。

这次五小时之前的 `out3` 又把这件事推进了一层。现在已经知道真实机制是：h3 后中心再也收不到新读数，可它仍保存着 h3 的 0.0185，于是 h7/h8 仍然认为“健康”，不断重申 dense，节点 h8 被耗死。修完 `prune` 和 `in_flight` 两个真 bug 后，这个业务损害一条没少，所以不是队列卡住造成的；就是**陈旧的确定性**。

**unknown、stale、wrong 三者不是一回事。**

现在很多 agent/runtime 状态机喜欢把世界压成“有结果 / 没结果”“成功 / 未知”。这个场景显示，最危险的可能恰恰是“有一个结果，所以我继续相信它”，而不是 `unknown`。**证据的价值不仅是内容，还包括它还能不能代表现在。**

然后是整个 repo 最决定性的链路实验。最初 i.i.d. 链路下，`local`、`aoi`、`dense`、`ea_nb` 能差三四个点，很容易让人产生“继续做聪明 controller 还能挤出很多东西”的感觉。接上 ChirpBox 的时间相关以后，差距迅速缩小；接 LoRa-on-Ice 那种长坏突发以后，宽松能量下五条甚至十条策略几乎直接重合。关键是你们保持了平均可用率附近的条件，真正改变的是**失败聚在一起还是散开**。

**每小时随机坏 40%，和连续坏几十小时，平均数可能差不多，但对控制器来说根本不是同一个世界。**

前一种世界里，“我多试几次”“我缩短上报周期”真的能增加撞上好时刻的机会。后一种世界里，这几十小时就是死区，你发一百次和发一次没有区别。

所以 link burstiness 在这里其实不是普通的 channel parameter，它决定了**中心还有没有控制权**。

这条跟 Cleveland 第二业务来源、12→96h 长度扫描结合以后就更清楚了：只要策略自己的 report cadence 已经足够满足业务 cadence，那么在这种长突发链路下，8 条正常策略之间的 service spread 到 96h 也才 0.29 点；但 i.i.d. 下一直有 3.5–4.5 点差距。反过来，Cleveland 业务每 900s 要一条，如果策略还 3600s 才报一次，那直接少 8–18 点。

**先问“物理上来不来得及”，再问“策略聪不聪明”。**

周期比业务义务还慢，必输；链路一个坏突发比你的决策周期长很多，基本也没得优化；只有落在中间那块“有机会、有资源、而且选择会改变结果”的区域，controller intelligence 才有价值。

这个观察把后面的 queue 实验也统一起来了。12h 下 FIFO/LIFO/latest 基本没区别，因为缓存压根没堆到有意义的程度；40h 断链以后 backlog 超过一个机会能服务的容量，LIFO 才明显改善 freshness，甚至把 AoI 砍半。

所以又得到一个朴素规律：

**机制有没有价值，常常由它对应的“压力”是否真的跨过激活阈值决定。**

atomicity 只有命令交错真的发生才有价值；queue discipline 只有 backlog 真堆起来才有价值；energy control 只有能量真的 binding 才有价值；AoI control 只有链路还有可利用机会才有价值。很多过去所谓“机制没效果”，其实只是没进入它该工作的 regime。

然后是intent ledger。

名义链路下，`aoi` 生成 266 条 intent，其中 179 条纯重发，占 67%；一个服务完全一样的 `aoi_const300` 只有 60 条左右。`eh_aoi` 更夸张，500 个 intent 只有 81 个真正发出去。到了南极突发链路，`aoi` 558 个 intent 里 553 个来自 unknown state，546 个最后被挡掉；`ea_nb` 只有 11 个 intent，却拿到同样的 38.5% service。

这组实验真正说的是决策系统的输出速率和物理系统的执行速率可以完全脱节。

planner 每分钟都可以“想出新动作”，但网络可能一天只给你几个真正的执行机会。超过这个 service rate 之后，更多 planning activity 不再等于更多 control，只是在产生 backlog、重发和垃圾 intent。

这很像 queueing，也很像 agent runtime：LLM 的 reasoning loop 可以跑得很快，environment actuator 是慢的、稀疏的、有副作用的。

最后就是刚停掉的 continuous-config admission。它试图非常保守地说：“我现在把节点切到高负载之后，如果剩下整个任务期间再也改不了，它还能不能活？”答案当然是：活不了，于是 171.9 次全拒绝，行为退化成 `local`。

**host 端如果既要求 hard safety，又不敢假设未来还能恢复控制，那么在“高负载 6.5h 就能耗死、任务还有 12h”的场景里，它没有聪明选择。它只能不介入。**

这几乎就是一个小型 impossibility condition。

所以否掉候选以后还能推出什么，从这里推的话。

> 一个远程控制动作有没有价值，不只取决于现在的物理状态，还取决于四个时间尺度：
> **多久能拿到新证据、多久能再次把命令送进去、当前配置多久会造成不可逆损害、业务多久必须得到结果。**


**看得回来吗？改得回来吗？撑得到那时候吗？业务等得起吗？**

repo 到现在绝大多数现象都能放进这四句话里。

`out3` 是：看不回来，节点又撑不到恢复。

南极 burst 是：很久改不进去，所以各种策略没区别。

Cleveland 3600 vs 900 是：业务根本等不起。

atomic 在 binding 区有收益，是它无意间把“开始高负载”往后拖，让节点撑得更久。

hard admission 退化，是因为它假设“以后完全改不回来”，于是安全动作集合只剩 local。

queue discipline 激活，是因为数据积累时间长到超过缓存服务能力。

这个东西如果愿意用控制理论继续推，是**control authority（控制权/可纠正能力）应该成为显式状态**。

现在 `ea_nb` 看 SoC，`aoi` 看 freshness，传统 controller 看物理状态；execution runtime 看 command id/version；但没有一个东西显式问：

> “如果我现在把系统推到这个状态，我下一次有把握纠正它是在什么时候？”


从这里能看到几个方法候选，但先把它们都当“推导方向”，不当创新结论：

* **风险化的 control-authority-aware controller。** 五小时那个 gate 用的是最坏情况：以后再也控制不了，所以它必然全拒绝。可以反过来不追求 hard guarantee，而使用合法历史估计“未来 H 小时重新获得观测/控制机会的概率”，然后给失败风险一个预算。能量、当前配置、证据年龄、链路 burst belief 一起决定能否进入 dense。这就是从 worst-case robust control 走到 chance-constrained / risk-sensitive control。它可能产生 hard gate 没有的中间态。它显然有大量控制理论先行工作，所以方法 novelty 还要另外找，但作为下一步实验假设是合理的。

* **remote effect belief。** 现在 runtime 很爱记录“我发了什么”“版本是多少”，但实际系统更需要维护“远端现在可能处于哪些配置”。ACK 丢失、partial apply、陈旧回执以后，不应该只剩 known/unknown 两态，而应该有一个可能状态集合或 belief。下一步决策按这个 belief 做资源/风险计算。你前面的 contract/atomic、stale evidence、continuous load 三条实验其实都能接到这里。这个更偏 `agent infra + distributed systems / POMDP`。

* **intent backpressure。** Planner 产生 intent 的速度不能超过 actuator 的长期 service rate。对“设置状态”类工具，重复目标、无新证据重发、信道根本不可达时继续生成，可以在 host 侧 coalesce / suppress。你已经有 67% resend、11× generation difference、polar 下 98% 被拒的直接证据。它目前最大的缺口就是这些都是 scripted policy；真实 LLM 如果自然出现同一现象，这会是最干净的 agent-infra 入口。

* **regime-aware supervisor。** 系统先判断自己现在处于 link-dominated、energy-dominated、cadence-limited 还是 control-useful 区间，再决定到底让中心自适应、保持 local、还是仅做 AoI。你现在其实已经有几个 regime 的实验图了。它未必是新控制算法，可能更像 meta-controller，但能把“什么时候 Agent 应该闭嘴”变成系统机制。

* **端侧 lease / failsafe** 其实是最直接的工程解：中心下发 dense 时附一个有效期，到期没收到续租就本地降档。这样 `out3` 不会无限跑 dense。可惜当前 capability 没有来源支持，所以不能偷偷塞进 core benchmark。它更像一个后续 system-design extension：如果以后设备协议真的支持 timer/lease，这个方向会一下变得很自然。

如果现在选“最值得想”的一个抽象，可以先看fresh evidence time、next effective control time、time-to-harm、business deadline，逐个把 repo 的实验塞进去。


---

以上仅供参考。

---


我们思考一下这个场景本质需要什么，现行调度方法的缺陷本质是什么，如果现行agent应急方案放进去是什么状况，我们刚刚的结论推导能否定它什么，能带给它什么，这就是出论文的东西。


这个场景缺的未必是“更聪明的调度器”，而是一个能意识到“我现在到底还有多少控制权”的决策系统。

山区灾前监测和普通无线资源分配有个很关键的差别：中心看到的状态会旧，控制命令不一定能进去，进去以后配置会持续生效，本地节点还有自己的自治逻辑，而且业务有自己的时限。也就是说，中心一次动作不是“我现在选 A 还是 B”这么简单，它隐含了一个更深的前提：

我做完这个动作以后，未来如果情况变坏，我还来得及重新看到它、重新改它。

而我们这一轮又一轮实验，其实一直在把这个隐含前提拆出来。

我现在会用四个时间来理解整个场景：

多久能再次看到可信状态：T_obs
多久能再次真正把控制送进去：T_ctrl
当前/候选配置多久会把系统推到不可逆损害：T_harm
业务最晚多久必须得到结果：T_deadline

很多结果一下子就通了。

Cleveland 那个 900 s 义务下，3600 s 上报的策略直接差 8–18 点，因为 T_report > T_deadline。这时候算法多聪明都没用，物理节奏已经跟不上义务。

南极 burst 下，各种调度策略几乎完全重合，因为坏突发几十小时，远大于你正常控制和业务的时标。T_ctrl 巨大，中心这段时间实际上没有控制权。i.i.d. 链路下还有 3.5–4.5 点可以争，换成真实突发结构后只剩 0–0.29 点。这个结果很强，因为它直接说明：平均链路质量一样，“失败是散着发生还是连续发生”会决定智能调度还有没有作用。

能量绑定时，atomic 之所以救了一部分节点，也不是事务语义本身有什么魔法，而是它把 dense 配置的生效时间往后拖了。节点少跑几个小时高负载，就没那么容易死。换句话说，真正决定结果的是 action exposure time——高耗能动作什么时候开始、持续多久。

out3 更漂亮。中心最后看到 h3 的 0.0185，之后虽然这个读数已经老了，却一直拿它当“当前健康状态”，于是 h7/h8 还在重申 dense，最后节点耗死。这里暴露的是：有信息不等于有知识。 stale-but-plausible evidence 有时候比彻底没有 evidence 更危险。没有读数时 ea_nb 反而少动，接近 local；错误或陈旧但看起来正常的读数会驱使系统主动做危险动作。

再看 intent ledger：南极 burst 下 aoi 生成五百多条 intent，99% 来自 unknown state，98% 连信道都没拿到；ea_nb 用大约 1/50 的 intent 量得到同样 service。名义链路下，aoi 67% intent 只是 resend。

这个结果放到 agent 世界里就非常有意思了：

planner 的 reasoning rate 和 actuator 的 service rate 是两回事。

LLM 一秒钟能重规划很多次，不代表设备一秒钟能接受很多次动作。物理执行机会如果一天只有几个，你让 Agent 多想一百次，最后可能只是制造一百条垃圾 intent。

所以我会这样概括“现行调度方法”的根本局限。

传统 AoI、queue、EH、resource allocation 之类的方法，绝大多数是在回答：

当前状态给定，我应该选哪个动作？

而我们这个场景前面还有一个问题：

当前这个时刻，我到底有没有资格把这个动作当成“可控动作”？

这不是一回事。

调度算法一般默认 action set 是存在的，链路质量可能影响成功概率，但 scheduler 至少在每个 decision epoch 还能重新观察、重新选择。我们这里的 feasible action set 本身会随着长断链消失；更麻烦的是，这个消失往往不可及时观测。

所以 channel state / battery / queue / AoI 这些还不够，还少了一个变量：

effective control authority，或者先用大白话叫“当前控制权”。

这个量表示的不是“链路有没有信号”，而是：

从现在开始，到这个动作可能造成不可逆后果或者业务 deadline 到来之前，我还有没有足够机会重新观察和纠正。

这就是五小时那个 hard gate 为什么会退化成 local。它假设未来完全不能纠正，又要求 hard safety。dense 6.5 h 能耗死节点，而任务还有 12 h，那数学上根本没有折中：要绝对安全就只能别动。

这其实很有价值，因为它告诉我们：

仅靠中心侧 safety filter，在完全未知的未来控制可达性下，不可能同时获得 aggressive adaptation 和 hard safety。

这不是“我们过滤器写烂了”，而更接近一个结构性边界。

于是 current agent emergency communication 的问题也一下清楚了。

repo 里调研的几条 agent 线，大体是在更高层做“决定什么”：

TopoLLM 做拓扑/资源规划，Public Safety UAV 做数据收集调度，WirelessAgent 把 intent 拆成 workflow 和资源配置，LODA 做 UAV/资源联合优化；ESWA 和 SCS 则更像让 Agent 选 recovery tools / tool chain。ICLDC 是最接近我们的问题形式：有限服务机会、有界队列、状态反馈、选择服务对象。

但 repo 的复核已经明确：这些工作不能被直接解释成“控制命令和 ACK 在长时间断连下已经被处理”。LODA 甚至明确把集中式、理想通信作为评价范围；ESWA 的 tool execution 很多是在模型里计算恢复序列和资源方案，跟一个 LoRa Class A 节点真正收到配置不是同一种“执行”。

所以把这些 Agent 直接塞进我们的 benchmark，我预判会出现一个非常典型的现象：

plan quality 很好，但 effective control 很差。

Agent 可能正确判断“n02 电量高，可以加密采样”。

问题是它没有意识到：

“我一旦这么做，未来 6 小时之内必须还有机会重新看到它、重新改回来。”

如果网络后来断 9 小时，这个 action 在做出那一刻虽然“局部合理”，从闭环角度却已经是不安全的。

这就是 agent emergency 方案目前最容易隐含的一个假设：

reasoning loop 是闭环的，所以 environment 也会持续闭环。

但我们的实验说明，这两个闭环可以解耦。

LLM 还在 reasoning。

中心还在生成 action。

设备那一侧的闭环已经断了。

我觉得这就是 paper 很值得打的一个点。

我们现有实验已经能否定几种很自然但其实错误的想法。

“Agent 更聪明，所以服务一定更高”不成立——链路 burst 足够长以后，所有正常 controller 服务几乎一样。

“更频繁 adaptation 会更好”不成立——intent 可以多 50 倍而 service 一样。

“状态越多越好”不成立——陈旧但可信-looking 的状态可能比缺失更危险。

“中心加一个 robust safety layer 就能解决”也不成立——如果未来纠正机会完全无保证，hard safety 会直接退化成不介入。

“只要 tool call 成功了，action 就算处理完了”也不成立——采样配置成功以后还会持续吃电，它的后果横跨未来。

这些合起来，我觉得可以提出一个比“又一个 scheduler”更有信息量的问题：

Agentic emergency systems currently optimize what to do; in intermittently connected monitoring, the missing question is whether the system still has enough control authority to make that decision meaningful.

然后方法也能从这里自然长。

我现在最看好的不是一个具体 heuristic，而是一层 authority-aware control/runtime。

它维护的对象不只是 battery、AoI、queue，还包括：

evidence age
estimated next control opportunity
persistent action exposure
time-to-harm
business deadline

Agent 当然仍然可以提出动作。

runtime/controller 再判断：

这个动作现在属于“可闭环动作”，还是“我一旦做了以后就可能再也改不回来的 open-loop commitment”？

这个区分我觉得特别关键。

比如：

set_report_period(900) 可能比较便宜，风险小。

set_sampling_interval(600) 会持续烧能量，风险大。

对于后者，如果 T_ctrl 的风险分布已经接近或超过 T_harm，那它应该被看成一种 commitment，而不是普通 config write。

这里就和 agent infra 接上了。

现在 Agent tool schema 一般告诉模型：

“这个工具叫 set_sampling_interval，参数是多少。”

我们可能真正需要的是工具/动作还带这些语义：

“它会持续多久影响系统”
“多久不纠正会产生不可逆代价”
“需要什么 evidence 才安全”
“执行后下一次纠正依赖什么通信机会”

这样 planner 不只是调用工具，而是知道这个工具的 control dependency。

再往 Agent infra 推一步，就是你已经有实验证据的 backpressure。

如果没有新 evidence，也没有新的执行机会，planner 就不应该每轮都重新制造 intent。

也就是说 runtime 可以告诉 LLM：

“环境状态没有发生可行动变化，当前执行面仍不可达，不要继续重规划。”

这不是简单 rate limit，而是 reasoning 与 actuation 的 backpressure。

你现在 scripted policy 已经看到 67% resend、98% rejected/无信道，但真实 LLM 还没接，所以这里正好是一条很干净的实验门：

如果真实 agent 也在无新证据、无执行机会时反复规划、反复调用工具，那么这个 failure 是自然产生的。

这时 runtime 可以做的不是“替它做更聪明的无线调度”，而是把：

new evidence
new actuation opportunity
previous action resolution

作为重新 reasoning 的触发条件。

这就非常 agent infra 了。

控制理论那一侧也有一条对应路线。

你可以把它看成一个 hybrid / partially observable control 问题：系统有时候处于“中心有控制权”，有时候处于“纯本地自治”，中间还有“证据旧了但配置仍生效”的灰区。

这时候 controller 的任务不是永远优化一个 policy，而是先判断自己在哪个 regime：

control-useful
link-dominated
energy-dangerous
cadence-infeasible

然后决定 central adaptation 是否应该打开。

这可能最后表现成一个 supervisor，而不是一个复杂 scheduler。

而且 repo 已经给了这些 regime 的 empirical boundary：

report period 跟不上 obligation → cadence infeasible；

bad burst 远长于业务/决策时标 → link dominated；

高负载的 time-to-harm 小于可能的 correction delay → dangerous open-loop commitment；

通信和能量都宽松 → 复杂 execution semantics 反而只是额外开销。

这已经很像一个 regime map 了。

所以现在我觉得论文可能真正的 intellectual story 是：

过去 Agent 通信论文把 intelligence 放在 decision layer；我们发现，在 intermittently connected monitoring 里，performance 首先由 control authority 决定。

然后证据链是：

真实来源链路 → burstiness 把 controller 差异压平；

真实业务 cadence → 先有 feasibility boundary；

energy-binding → action timing/persistence 决定成败；

stale telemetry → perceived state ≠ actionable state；

intent ledger → reasoning activity ≠ effective control；

hard safety → 没有未来控制保证时只能退回 local。

最后才轮到一个方法：

让 Agent/runtime 显式建模和管理 control authority，而不是把所有合法 tool action 都当成当前可执行的 action。

这个方向我认为比“找一个能把 service 再提高 2 个点的 policy”强很多。

它也把你通信和 agent infra 两边真正接起来了：

通信负责告诉系统“什么时候还有执行机会、多久可能恢复、路径的 burst structure 是什么”；

控制负责告诉系统“当前动作多久会进入不可恢复区域”；

agent runtime 负责告诉 planner“哪些 action 当前值得 reasoning、哪些需要 abstain / defer、什么时候值得 replan”。

这三层是有因果链的，不是为了拼 interdisciplinary 关键词。

我现在甚至会把后续思考压成一个很具体的问题：

一个 Agent 在什么条件下应该被允许改变远端系统状态？

如果这个问题能被我们从 T_obs / T_ctrl / T_harm / T_deadline 推出一套可测的判据，再用现有 benchmark + real LLM 去验证，那就真的开始像一篇完整论文了。