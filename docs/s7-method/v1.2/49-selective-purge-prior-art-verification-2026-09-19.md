# doc49 — selective purge 新颖性成稿前文献核验（doc45 §6 闭环）

- 日期：2026-09-19
- 触发：doc45 §6「成稿前待办（证据升级）」要求打开 Razavi（IEEE 4567352）、Wada（IEEE 5291354）、Krishnan（arXiv:1909.06571）确认 δ2 未被等价覆盖，并补一条 DTN custody transfer（RFC 5050 / BPv7）对照。本轮同时把 refs.bib 的 misc 占位升级为带作者/出处/卷页/DOI 的条目。
- 检索通道：`scholar_search`、`general_search`、`web.fetch`（rfc-editor.org 原文、IEEE Xplore/Semantic Scholar/出版社与机构库摘要）。IEEE Xplore 正文在本环境未直接打开（Semantic Scholar API 一次 link fetch error）；Razavi/Wada 的**书目元数据为 A 级**（出版社/书目库一致），**机制边界为 B+ 级**（出版社或同组论文的完整方法摘要、多来源一致），按仓库纪律不写成"已逐页读全文"的 A 级。
- 与 r38 全量真实 LLM 跑批同机并行进行，本轮**未改任何仿真代码与结果**，只改 `refs.bib`、论文 related work 一段、新增本记录。

## §1 三篇 δ2 相邻工作的核验结论

### 1.1 Razavi, Fleury, Ghanbari — deadline-aware video / Bluetooth（B+，δ2 不覆盖）
- 准确书目：**Rouzbeh Razavi, Martin Fleury, Mohammed Ghanbari**, "Deadline-aware video delivery in a disrupted Bluetooth network," **IEEE Sarnoff Symposium, 2007**, IEEE Xplore document 4567352（refs.bib 原误记 2008，已改 2007）。
- 同组互证论文："Fuzzy Logic Control of Adaptive ARQ for Video Distribution over a Bluetooth Wireless Link," EURASIP JWCN/Hindawi 2007, DOI 10.1155/2007/45798；"Buffer size resilience for Bluetooth video streams from adaptive ARQ with active discard," IET Electronics Letters 2007, DOI 10.1049/el:20070980。
- 机制（多来源摘要一致）：adaptive ARQ 按 picture type/内容重要性调整重传；并对**发送缓冲（send buffer）中已过显示/解码期限的包主动丢弃（active discard）**，以防缓冲溢出、在 RF 误码突发/中断后快速恢复。
- δ 核对：discard 与 ARQ 在**同一发送节点的同一缓冲、同一跳蓝牙 piconet** 内协同。**不存在**两个分离网络段（节点 LoRa 接入段 vs 网关蜂窝/卫星回传段），**不存在**"回传段终点的端到端确认才清除上游接入段 FIFO repair cache"的反向跨段耦合，触发量是视频 picture-type 的本地显示期限而非监测义务的绝对交付 deadline，也**不保留**仍可在恢复后交付的记录。判定：对应 doc45 δ2 表中"Razavi discard+ARQ（单跳）"，**δ1/δ2/δ3 均不被等价覆盖**。

### 1.2 Wada, Kitamoto, Fukuhara, Sasase — (RT)² 源端时限抑制（B+，δ2 不覆盖）
- 准确书目：**Takahiro Wada, Hayato Kitamoto, Takerou Fukuhara, Iwao Sasase**（Keio University）, "A Transport Protocol with Energy Consumption Reduction by Reducing Redundant Transmissions in Wireless Sensor and Actor Networks," **IEEE PACRIM 2009**, IEEE Xplore document 5291354。
- 机制（IEEE Xplore 完整方法摘要）：sensor node 用"过去传输得到的单跳延迟 × 跳数"估计到 actor 的包到达延迟；**若预计到达延迟已超过剩余 time limit，则在该时刻根本不生成该包**（并在理想排队假设下偏小估计以保可靠性），从而减少必然 time-out 的冗余传输与能耗。
- δ 核对：这是**源端抑制生成（suppress generation）**，发生在包存在之前；没有 repair cache、没有两段、没有端到端 ACK 驱动的一致性、没有对已生成但仍可挽救记录的选择性保留。判定：是 δ1 邻接（源端按预计时延不生成），**δ2/δ3 不覆盖**。

### 1.3 Krishnan & Sharma — 多跳 AoI 本地丢旧（A 级，doc45 已判定，本轮补书目）
- 准确书目：**Ashok Krishnan K. S., Vinod Sharma**（Indian Institute of Science, Bangalore）, "Minimizing Age of Information in a Multihop Wireless Network," arXiv:1909.06571, 2019。
- doc45 §6 已读全文（A 级）：SDSPD 的丢弃规则是"每个队列对每条流只保留最新一个包、其余丢弃"，明确为本地决策、节点间无需交换信息；Discussion 另给要求不丢任何信息时应改用的 SDSPnD-LCFS。它是本文 AoI **latest-only 反方的多跳学术原型**，无义务/绝对 deadline、无未确认 repair cache 与端到端 ACK 清除结构、无两段一致性、不保留可挽救记录。**δ2/δ3 不覆盖**（维持 A 级判定），论文已将其作为 latest-only 代表与 selective（保留 d>t）对照。

## §2 DTN custody transfer 专门对照（A 级 RFC 原文）
- RFC 5050（**Kevin Scott, Scott Burleigh**, Bundle Protocol Specification, IRTF, 2007）术语与 §5.10：to *accept custody* 是下游节点在转发时承诺保留副本、必要时重转，直到 custody 被释放；对单播（singleton）目的，custody 在 (a) 收到另一节点已接受同一 bundle custody 的通知、(b) 收到 bundle 已在目的端交付的通知、或 (c) bundle 因 lifetime 到期等被显式删除时释放。
- RFC 9171（Bundle Protocol Version 7, IETF, 2022）Appendix A「Significant Changes from RFC 5050」明确：**custody transfer 迁出核心 bundle 协议，移交给 bundle-in-bundle 封装规范（BIBE）**；控制标志"Custody transfer is requested"标注为 BPv6 专用。
- δ 核对（关键，方向相反）：custody transfer 是**正向交接（forward hand-off）**——下游接管重传/保留责任后释放上游，其设计目的正是**把可靠性与端到端确认解耦**；触发量是 bundle custody/lifetime/相遇，而非"某条具体监测义务在绝对截止期前不可由回程几何交付"。它既没有两个被端到端链路层 ACK 耦合的段，也**不需要**"两段一致终止"——DTN 本就不依靠端到端中心 ACK 去清上游链路层 repair cache。本文 selective purge 处理的是**反向**过程：回传段终点经义务不可行判定后，必须在接入段节点侧同时停止持有/重传，否则经"中心收到才清 FIFO repair cache"反向污染新鲜接入批次（r37b 实证 −8 on-time、9 条 sid 见证）。**δ2 不被 custody transfer 覆盖，二者是不同方向、不同触发、不同耦合结构。** 论文 related work 已新增该专门对照并引 RFC 5050/9171。

## §3 refs.bib 元数据补全（本轮）
| key | 处理 | 核实数据 |
|---|---|---|
| razavivideo | misc→inproceedings | Razavi/Fleury/Ghanbari, IEEE Sarnoff Symp. 2007, doc 4567352（年份 2008→2007 更正） |
| wada2009timeout | misc→inproceedings | Wada/Kitamoto/Fukuhara/Sasase, IEEE PACRIM 2009, doc 5291354 |
| krishnan2019multihop | 补作者 | Ashok Krishnan K. S., Vinod Sharma, arXiv:1909.06571 |
| costa2014pm | misc→article | Costa/Codreanu/Ephremides, IEEE TIT 62(4):1897–1910, 2016, DOI 10.1109/TIT.2016.2533395（会议版 ISIT 2014 pp.1583–1587 入 note） |
| kam2016deadline | misc→inproceedings | Kam/Kaya/Ephremides, IEEE MILCOM 2016, DOI 10.1109/MILCOM.2016.7795343 |
| iranmaneshdtnqueue | misc→article | Saeid Iranmanesh, EURASIP JWCN 2016, 2016:88, pp.1–23, DOI 10.1186/s13638-016-0576-6（QM-EBRP：TTL/相遇率/副本数效用） |
| rfc5050（新增） | techreport | Scott & Burleigh, RFC 5050, 2007（custody 正向交接、解耦 E2E ACK） |
| rfc9171（新增） | techreport | RFC 9171 / BPv7, IETF 2022（custody 迁出核心协议至 BIBE） |
| dtnarch | 补作者 | Fall/Burleigh/Hooke et al., RFC 4838, 2007 |

仍保留 misc（未在本轮从主记录核实作者，按文件头纪律不猜）：topollm、icldc、icgrestore、ossgpt、sdnconsistency、zakeri2311、bacinoglu1905、ccsdssabr、sateriot。这些是谱系/背景/强基线引用，不承载 selective purge 的新颖性主张。

## §4 对论文主张的净影响
1. doc45 §2 的三点 delta **全部维持**：δ1（义务级端到端可行性触发，非包龄/本地 TTL/单包剩余时延）、δ2（接入/回传两段必须一致终止，源于端到端 ACK 驱动 FIFO repair cache 的反向跨段因果）、δ3（释放已死记录与保留 d>t 可挽救记录配对）。
2. 最近的两篇威胁（Razavi、Wada）经核验落点分别是**单跳视频发送缓冲 discard+ARQ**与**源端按预计时延不生成**，均不构成 δ2 的等价跨段机制；DTN custody 是正向托管交接且以解耦 E2E ACK 为目的，方向相反。论文 related work 已逐一点名并区分（含新增 custody 专句）。
3. 措辞纪律不变：Razavi/Wada 为 B+（未打开 IEEE 正文），论文不写"首次/无人做过"，只写"以本轮核验到的文献为限，未见以义务可行性证书为触发、并要求两段一致终止的工作"；α³-Bench 等未读条目仍阻塞任何"首次"主张（与 doc45 §5、README 一致）。
4. 局限：本轮是**定向相邻工作核验**，非穷尽系统综述；scholar 对 Razavi 的一条 query 返回空（已用 general search / Semantic Scholar / 同组论文替代）；IEEE 正文未逐页打开。若投稿前能取得 IEEE 全文，建议把 Razavi/Wada 升级为 A 级并复核其 ARQ/抑制是否触及任何跨缓存状态（当前摘要证据显示不触及）。
