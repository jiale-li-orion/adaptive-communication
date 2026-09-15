# doc31 — 成稿前文献核验（四条区别），2026-09-15

目的：锁定 related work 措辞，禁称首次/空白。方式：general_search + web.fetch 直连官方/出版源。分级 A=官方原文/出版记录，B=作者版/机构，C=二手摘要，D=文档分享/未取到。

## 1. CCSDS 734.3-B-1 —— 纠正旧标注（重要）
- 官方蓝皮书 PDF（ccsds.org/Pubs/734x3b1.pdf，A）：标题 **Schedule-Aware Bundle Routing (SABR)**，§1.1："dynamic route computation in an environment of stable topology but time-varying connectivity when instances of connectivity are scheduled rather than opportunistic."
- **它是计划感知的 bundle 路由（在已排期接触上选路/转发），不是"overbooking 装包"。** v1/v2 初稿"overbooking in space links"标注错误，全部改为 schedule-aware bundle routing over planned contacts。与本文区别：SABR 决定 bundle 走哪条计划接触（路由层），不做包内义务级样本选择，也没有义务覆盖/时效两层。

## 2. 北斗短报文容量受限优先级装包 —— 已核：存在，但是单维优先级（C/B）
- 专利（天眼查，C）：分三类业务（高精度回传 > 重传补发 > 常规实时监测），每次发送机会按**固定业务类别**优先级组织消息。
- 专利（xjishu 202610226320，C）："取报文总容量减位置段得剩余比特，按各数据**标准化偏离度**建优先级队列，从高到低截取填入直至比特耗尽"——容量受限下按**单样本风险值单维排序装满**。
- 沈航学报 2024.01（B）：图像按北斗 4.0 接口分包、关键包（首两包）优先、丢关键包则停。
- 武大学报·信息科学版（B，ch.whu.edu.cn）：民用北斗 IC 卡**包长 124 B，去包头 20 B/包尾 5 B，用户数据容量 104 B**，可容约 10 类环境参数——给净荷一个真实参照（本文 {78,200} B 是研究扫描值，104 B 落在其间，threats 引用此来源，不声称 78/200 是标准值）。
- **cover 的区别（写进 related work）**：上述都是**单份数据的静态优先级**（固定业务类别，或单样本风险值/关键包标记）的一次填满，不维护跨机会的义务覆盖集、不处理一条义务多份时序竞争候选的时效、不区分"覆盖广度/样本时效"两层，也不涉及主备双尺度与网关仅链路回执的信息结构。cover 不是"按风险排序"，风险等级在本文固定等价值义务下根本不使用。

## 3. SHETLAND-NET —— 仍未核实（D/未取到）
- general_search 未返回学术原文（地名噪声）；本机此前直连 429。**不写 4.6 kbps/242 B/夜间可用率 0% 等具体数字到正文**，related work 仅以"contact-aware triage at extreme low-rate contacts *(unverified in this environment)*"占位，成稿前需取到原文（IEEE/作者页）再决定。

## 4. Zakeri POMDP —— 已核摘要（A，arXiv 记录）
- 准确信息：A. Zakeri, M. Moltafet, M. Codreanu, **"Semantic-aware Sampling and Transmission in Energy Harvesting Systems: A POMDP Approach,"** arXiv:2311.06522（v4 2024-10-04，DOI 10.48550/arXiv.2311.06522；Asilomar23/Globecom23 初步版）。修正 v2 旧标题"in Real-time Tracking Systems"。
- 内容：部分可观测 Markov 源 + EH + 不可靠信道，联合采样/传输，POMDP→belief MDP→相对值迭代/DRL，最优策略对 AoI 非单调切换。**单源、发送端、同槽动作**；无两段接入/回传分离、无主备双尺度窄通道、无义务多对多与包内仲裁。作为 Finding I 的模型比较依据成立。

## 5. ICLDC（已核，沿用 doc27）
arXiv:2504.14556 / DOI 10.1109/JIOT.2025.3615410：单跳 UAV 采集 + LLM in-context 调度，基线 DQN/最大信道增益；形式邻近＝有限服务机会，不含本文主备/多对多/两层。

## 净结论（措辞纪律）
- related work 明说"容量受限按优先级装包在北斗工程与 DTN/空间链路已有"，**不主张内容选择性装包是新的**；本文可主张的区别仅三点组合：主备双尺度 + 义务多对多绝对期限/宽限 + 网关仅有链路回执下的"覆盖广度×样本时效"两层在线规则，且以同字节配对、消融、held-out、上界为证据。
- 不出现 first/novel/gap/uncovered；α³-Bench 等未读条目继续阻塞此类措辞。
