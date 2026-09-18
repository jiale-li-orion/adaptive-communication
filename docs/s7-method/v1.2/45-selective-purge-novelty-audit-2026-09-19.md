# doc45 — E2 selective purge 新颖性独立复审（成稿前先行工作台账）

- 日期：2026-09-19
- 触发：doc44 §12.4 要求；LaTeX v0.2 已把 deadline-aware selective purge 写成第二贡献，投稿前必须独立核验"义务失约后一致终止接入段持有/重传与回传段发送、并与保留可挽救记录配对"是否已被覆盖。
- 方法：`scholar_search` 六组 query（两轮，每轮 3 条并行），覆盖 AoI/截止期丢弃、DTN bundle 生命周期/托管释放、LoRaWAN-卫星回传、ACK/重传头阻塞、端到端 ACK 与链路层交互、效用/覆盖约束丢弃。证据分级沿用本仓库：**B 级**＝出版社/arXiv 摘要与可辨识机制描述（本轮多数）；**A 级**＝读全文（本轮未逐篇打开，见 §6 缺口）。本轮不据摘要下"无人做过"的强结论，只判定**候选空位是否仍在**与**论文措辞边界**。
- 结论先行（一句话）：**"丢弃过期/陈旧包"本身高度成熟、绝不新颖；可防守的新颖性是一个三点合一的执行层机制，且应作为第二贡献依附于 plan 侧义务级可行性证书，主新颖性仍在证书。** 判定 **GO（限定措辞）**。

---

## §1 相邻先行工作分类（按与本机制的距离排序）

### A. AoI 包管理 / 截止期丢弃（最近、最易被引为覆盖）
- Costa, Codreanu, Ephremides, *On the AoI in Status Update Systems with Packet Management*, IEEE ISIT 2014 / arXiv:1506.08637。源节点可丢弃陈旧状态更新以免浪费网络资源；提出 peak age。**单源-目的、包龄驱动、本地丢弃。**
- Kam, Kompella, Nguyen, Wieselthier, Ephremides, *Controlling the Age of Information: Buffer Size, Deadline, and Packet Replacement*, IEEE MILCOM 2016（doc 7795343）；及 *AoI with Packet Deadlines*（M/M/1/2）。在 buffer/server 设包 deadline 丢弃、包替换，优化平均 AoI。**deadline 是控制参数、目标是 freshness。**
- Krishnan & Sharma, *Minimizing AoI in a Multihop Wireless Network*, arXiv:1909.06571。**多跳**、各队列本地丢旧包降 AoI、避免拥塞，逼近下界。最接近"接入段丢旧"，但目标 flow AoI、无义务/截止期可行性、无主备两段、无计量回传。
- Wang et al., *AoI of Short-Packet Communications with Packet Management*, arXiv:1908.05447：NP/preemption/**retransmission(RT)** 三策略，AoI 闭式解。已在同一跳讨论 discard 与重传。
- Sinha & Roy, *Deadline-aware Scheduling for Maximizing Information Freshness in ICPS*, IEEE Sensors J. / arXiv:1912.11310：deadline-aware highest-latency-first。
- Fountoulakis et al., *Information Freshness and Packet Drop Rate Interplay in a Two-User Multi-Access Channel*, arXiv:2006.01515：deadline-constrained 流与 AoI 流的丢包率-AoI 权衡。
- 另：Kam *AoI with Packet Deadlines*、Zhou & Saad MDP threshold、Stamatakis heterogeneous FIFO、Banerjee preemption 等一整片 AoI 队列文献。

### B. 截止期感知丢弃 × 重传/ARQ 联动（**最大相邻威胁之一**）
- Razavi, Fleury, Ghanbari, *Deadline-aware video delivery in a disrupted bluetooth network*, IEEE（doc 4567352）。**deadline-aware buffer discard + adaptive ARQ**，按 picture type 多 deadline，抑制过期包重传与缓冲溢出，中断后快速恢复。
  - 与本工作相似处：都把"过期丢弃"和"重传策略"联动，都在 disrupted 链路上。
  - 区别：单跳蓝牙、视频帧、重要性/内容 deadline；**无端到端监测义务链、无接入 vs 主备回传两条异构路径、无"回传段抑制→端到端 ACK 缺失→接入 FIFO 污染→新鲜样本 heard 推迟"的反向因果见证、无 plan/execute 同一证书抽象**。

### C. 源端按预计时限抑制生成/发送
- Wada, Kitamoto, Fukuhara, Sasase, *A Transport Protocol with Energy Consumption Reduction by Reducing Redundant Transmissions in WSANs ((RT)²)*, IEEE PACRIM 2009（doc 5291354）。节点估计到 actor 的端到端延迟，**若预计超过剩余时限则不生成该包**，减少 time-out 冗余传输与能耗。
  - 区别：在源端**不生成**、单条应用时限、一跳延迟估计；不处理"已在节点 repair cache 中的记录因端到端 ACK 未达而持续占接入批次"，也无义务级可行性证书与两段一致性。

### D. DTN bundle 生命周期/到期与丢弃策略
- Cerf et al., *Delay-Tolerant Networking Architecture*, IRTF **RFC 4838**（bundle 层、state management、lifetime/expiration）；BPv7 bundle lifetime、LTP（RFC 5326）重传可靠性；Yang et al. *Modeling Optimal RTO for Bundle Protocol*, IEEE TAES 2018。
- Iranmanesh, *A novel queue management policy for DTNs*, EURASIP J. Wireless Comms & Networking 2016：TTL、encounter rate、副本数驱动的 scheduling/drop，对比 DO/LIFO/FIFO/MOFO/LEPR/HOP-COUNT。
  - 区别：bundle **自带 lifetime、逐跳本地到期本地删**，custody transfer 的设计本就为**解耦**端到端确认；触发量是 TTL/相遇率，不是"该记录服务的具体义务的端到端可行性"。**没有也不需要"两段一致终止"**，因为 DTN 不依赖端到端中心 ACK 来清上游 repair cache。这正是本场景（LoRa 链路层端到端确认驱动 FIFO 重传）与 DTN 的结构性差异。

### E. 无线链路 ACK / 重传交互（说明"ACK 语义影响重传"是经典议题，但落点不同）
- Balakrishnan et al., *A Comparison of Mechanisms for Improving TCP Performance over Wireless Links*, IEEE/ACM ToN 1996：端到端/链路层/split-connection，SACK 与显式丢失通知。
- *Proactive-WTCP*, IEEE LCN 2003：抑制 duplicate ACK 让链路层恢复、断连前 persist。
- Zhang et al., *Frame Retransmissions Considered Harmful: Micro-ACKs*, MobiCom 2012。
- Xi et al., *Coordinator to eliminate redundant local retransmission*；Libman *Retransmission Strategies for Resource-Limited Devices*（GBN/advance retransmission）。
  - 区别：服务于 TCP 拥塞控制误判/频谱效率/吞吐，不涉及义务 deadline、不判定"哪条监测义务已不可挽回"、不做主备回传抑制。

### F. LoRa / 卫星回传应急与 rural IoT（场景近邻，机制不同）
- Ren et al., *SateRloT*, ACM MobiCom 2024：LoRa + LEO rural IoT，bursty link 模型、多跳 flooding、**priority data queue、去重**、网关缓冲共享；COTS 实测。
- Kuntke et al., *Rural Communication in Outage Scenarios: DTN via LoRaWAN Setups*, ISCRAM 2023。
- Sisinni et al., *Emergency communication in IoT by transparent LoRaWAN enhancement (LoRa-REP)*, IEEE 2020（消息复制降事务时延）；Giambene *Low-Power IoT in Remote Areas with NTN Opportunistic Connectivity*, IEEE TAES。
  - 区别：链路估计/flooding/复制/优先级去重，无义务截止期核销、无 ACK 驱动的跨段一致性。

---

## §2 三点 delta 的逐条覆盖核对

| # | 本机制要件 | 最接近的先行工作 | 是否被覆盖 | 防守判断 |
|---|---|---|---|---|
| δ1 | 释放判定基于**具体监测义务的端到端可行性**（绝对交付 deadline × 现场合法可知的回程几何，中断期仅公开 P），而非包龄/AoI/本地 TTL/单包剩余时延 | AoI deadline（Kam/Costa/Sinha）；Wada 单包剩余时限；DTN bundle TTL | **未见以"义务级可行性证书"为触发** | 可防守，但与 plan 侧证书共用才成立；单独讲"按 deadline 丢"会撞 B/C |
| δ2 | **接入段与回传段必须一致终止**；实证仅抑制回传发送会经"中心收到才清节点 FIFO repair cache"反向污染接入批次、拖慢新鲜样本 heard（r37b：−8 on-time、9 条 sid 见证） | Krishnan 多跳本地丢旧（同跳立即生效）；Razavi discard+ARQ（单跳）；DTN custody（本就解耦 E2E ACK）；TCP-LL ACK 交互（非义务） | **未见该跨段反向因果及其"一致终止"处方** | **最强、最新颖的一点**；是实证反例驱动的反直觉洞见，建议作为 selective purge 的核心卖点 |
| δ3 | 与**严格保留一切可挽救记录**配对（零假阳 d≤t 判定），相对 AoI latest-only 显式保住全时段覆盖（.432 vs .363） | AoI latest-only/preemption（目标函数不要覆盖）；DTN drop（缓冲溢出导向） | **未见"只核销被证明不可挽回的、保留其余"以保覆盖为目标的配对** | 可防守；Table 3 latest-only 反方是关键证据 |

三点合一、且落在"灾前监测义务 + LoRaWAN Class A + 计量北斗短报文 + 标准授权动作 + plan/execute 同一证书"场景，本轮检索**未发现整体覆盖**。但 δ1 单独偏弱，**新颖性重心应放在 δ2（跨段一致性，含 r37b 反例）+ 证书抽象的两端统一（plan 侧 S_time 与 execute 侧 purge 同一判定）**，δ3 作为与 AoI 的实证分界。

---

## §3 对论文措辞的硬约束（已在 v0.2 落实）

1. **不得**写"首次提出丢弃过期/陈旧包""首次抑制过期重传"。v0.2 §7 已新增 *Packet discard, freshness, and DTN expiry* 段，显式引用 Costa/Kam/Krishnan/Razavi/Wada/RFC4838/Iranmanesh/SateRloT，并写明"We claim not the act of dropping expired packets but the obligation-feasibility test, its cross-segment consistency, and its identity with the compile-time certificate"。
2. §5.6 已加一句：丢弃在 AoI/DTN 中已知，新颖在触发信号与跨段一致性。
3. 主贡献排序保持：**义务链 + 对称前沿（负结果）→ plan 侧可行性证书（S_time 几何 100%/0FP、到达时段归因 100%，最新颖最硬）→ 执行层 selective purge（δ2 跨段一致性 + 固定资源服务增益）→ 真实 agent 存在性见证**。selective purge 不得升格为头号贡献。
4. 所有"过期丢弃有益"的表述都必须带 r37b 的限定：**朴素单段抑制为负（−8）**，增益来自一致核销；否则与 AoI/DTN 文献和我们自己的反例冲突。

## §4 仍存在的新颖性风险（诚实列出）
- **Razavi（discard+ARQ）**与"Wada（源端时限）"是最近的两篇：若审稿人读全文发现其已含"上游持有/重传随下游抑制一致停止"的等价机制，δ2 的新颖性会被削弱。当前仅凭摘要判定其为单跳/视频，**成稿前必须读全文（或至少方法节）确认**。
- DTN **custody signaling / custody transfer** 的专门文献（RFC 5050 时代 custody/acknowledgment handling）可能讨论过"托管转移后上游释放"，与本机制的"一致释放"在精神上相邻；BPv7 已移除 custody，但需在 related work 一句话交代"我们的一致核销发生在链路层 repair cache 与计量回传之间，非 DTN custody 交接"。
- NACK / 选择性确认 / 链路层"抑制对已失效 SDU 的重传"在实时视频/工业无线有工程实践（Razavi 即一例），可能还有未命中的同义工作（关键词：per-hop deadline, stale SDU, useless retransmission, real-time wireless discard）。
- 本轮为摘要级检索（B 级），**未逐篇读全文、未跑引用滚雪球（forward/backward citation）**；α³-Bench 等 agent-benchmark 条目与本机制无关，不影响此处。

## §5 结论
- 候选空位（δ1+δ2+δ3 在义务级证书下合一、并以 r37b 跨段反例为证据）**当前仍在**，可进入成稿；按 doc33 检索纪律，这不等于"无人研究"的强断言，而是"在本轮可查文献中未被整体覆盖"。
- 机制可作为**通信执行层贡献**成立（规则可实现、节点本地零信令、固定资源 +3.2~5.6 点、中断 on-time 翻倍、留出稳健），符合"规则获益也支持通用通信执行层、不必 agent 不可替代"的既定立场。
- agent 的角色仍限定为：在任务变化/多义务竞争/证据不完整时**维护义务级判定**（E3 存在性见证，待扩），不声称 LLM 比全任务模型求解器更会优化。

## §6 成稿前待办（证据升级）
1. 打开 Razavi（IEEE 4567352）、Wada（IEEE 5291354）、Krishnan（arXiv:1909.06571，开源可下）三篇全文/方法节，书面确认 δ2 未被等价覆盖；若覆盖则按 doc38 §7.5 下调或改写该贡献。
   - **Krishnan 已读全文（2026-09-19，A 级）**：SDSPD 的丢弃规则是"每个队列对每条流只保留最新一个包、其余丢弃"（$Q_i^f\in\{0,1\}$），明确写明"这是本地决策、节点间无需交换信息"，并在 Discussion 明确：若应用要求"所有包都送达、不丢任何信息"，应改用不丢弃的 SDSPnD-LCFS。即：**它就是本文 latest-only 反方的多跳学术原型**——无义务/绝对 deadline 判定、无未确认 repair cache 与端到端 ACK 清除结构、无接入/回传两段一致性、不保留仍可挽救记录。**判定：δ2、δ3 均不被其覆盖（A 级）**，且该文应在论文中作为 AoI keep-only-latest 的代表与我们 selective（保留 $d>t$）对照（v0.2 §7 已引）。
   - Razavi、Wada 为 IEEE 托管，本机若 403 则维持摘要级 B 判定，不把"未覆盖"写成 A 级；二者即使成立，落点也是单跳视频/源端不生成，与 δ2 的跨段 ACK 耦合结构不同。
2. 补一条 DTN custody（RFC 5050 custody transfer / BPv7 removal）的对照说明。
3. ~~对 r37e 的 seed 0–9 全扫给出配对 CI~~ **已完成（doc46）**：n=10 配对 svc 均值 +4.21 点、95% CI [+3.64,+4.79]、10/10 全正，中断 on-time 2.52×（1691→4265），对 latest-only +5.73、CI [+5.06,+6.39]、10/10 支配；论文 Abstract/贡献 4/RQ3/§8(iv) 已替换为该 n=10 结果。
4. IEEE/MDPI 在本机曾 403；若打不开，标注为摘要级 B 证据，不把"未覆盖"写成 A 级结论。
