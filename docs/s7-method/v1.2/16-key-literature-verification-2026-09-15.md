# Task v1.2 — 16 · 关键文献记录级核验：修正一处误引、坐实两条假设差异

日期：2026-09-15。承接 [15](15-obligation-tightness-frontier-2026-09-15.md)。
论文相关工作此前多为摘要/台账级，本件对承重的三篇做记录/全文级核验（直接抓 arXiv 记录与系统模型），
避免把假设差异建立在二手转述上。

## 1. 修正一处误引（重要）

- **arXiv:1905.06679 的真实书目**：Bacinoglu T. B., Sun Y., Uysal E., Mutlu V.,
  *Optimal Status Updating with a Finite-Battery Energy Harvesting Source*（cs.IT，2019，v3）。
  主结论：有限电池 EH 源上最优在线策略是单调门限，**年龄门限是电池电量的非增函数**。
  仓库早期台账与 `center.py` EhAoiPolicy 注释把它错挂在 "Arafa, Baknina, Ulusoy & Ulukus" 名下，
  论文初稿也写作 "Arafa et al., Timely Estimation Using Sampled and Age-Optimal Sources"——**作者、
  标题均错**。已修正论文 Intro/Related/方法/References 四处与 `center.py` 注释（仅注释，逻辑未动，
  test_joint 5 锚点全过、总检 18/18）。
- Arafa 的 timely-estimation 系列真实出处是 *Sample, Quantize, and Encode: Timely Estimation over
  Noisy Channels*（arXiv:2007.10200；另有 Coded Quantized Samples arXiv:2004.12982），主题是噪声信道
  采样/量化与 age-penalty，**不是**有限电池门限；论文改以 2007.10200 作为 age-penalty 采样的一般引用，
  EH 门限结构只归于 Bacinoglu。作者全名单/发表 venue 提交前再核。

## 2. 坐实两条"假设差异"（论文 C3 的承重前提，现在有原文）

- **arXiv:2311.06522** 真实标题 *Semantic-aware Sampling and Transmission in Real-time Tracking
  Systems: A POMDP Approach*。§III-A 原文："the controller, **located at the transmitter side**,
  does not observe the source; the controller observes the battery level, the information in the
  buffer, and the transmission results (ACK/NACK feedback)"，动作在同一 slot 生效。
  ⇒ 论文"它们的控制器在发送端本地、观测电量/本地缓存/ACK、动作即时"的差异陈述**逐字成立**；
  它有 error-prone 信道 q，但控制器与采样/发送同处一端，**不存在跨一条独立失效回传段计算 AoI** 的结构，
  这正是本文失稳机制的前提差异。作者名单提交前核。
- **arXiv:2504.14556（ICLDC）**：Emami, Zhou, Nabavirazani, Almeida, *LLM-Enabled In-Context
  Learning for Data Collection Scheduling in UAV-assisted Sensor Networks*，IEEE IoT-J 2025，
  DOI 10.1109/JIOT.2025.3615410。系统模型确有：地面传感器**有限 buffer 深度 D、溢出计丢包**（Eq.5c
  g_i=1 iff q_i>D）、UAV 沿轨迹逐节点访问＝**有限服务机会**、queue length/channel/battery 反馈回路。
  ⇒ 论文把它作为"有限缓冲/外生到达/有限服务机会/接收反馈"形式要素来源**成立**；同时必须注明其调度器
  是 **LLM 上下文学习 + 规则 verifier**（故它也属 agent 谱系）。本文差异"它们的传感器到达外生，本文
  数据到达网关的时刻被一个延迟的远端配置动作内生改变"成立。

## 3. 对论文主张的净影响

- C3"反馈信号被不可控段污染"的对照前提从"摘要级转述"升级为"原文级坐实"，相关工作可直接写。
- 不改变任何实验数字与结论；eh_aoi 作为"文献结构最强基线"的定位反而更准确（其门限结构确有经典出处，
  只是被修正了署名）。

## 4. 仍未核实、提交前必须处理（不得当已核事实）

- TopoLLM 及谱系三线（PS-UAV/LODA/WirelessAgent、LLM+DRL、ESWA-IIN/SCS-Lifeline）：摘要/机构记录级，
  主张仅限谱系描述，不据其下"空白"结论；α³-Bench 未读。
- TCOM 2025/2021、TII 2025、INFOCOM 2026 的 AoI-energy 具体卷页/DOI 待补全。
- SHETLAND-NET 本机 429、MDPI/IEEE 主站 403；CCSDS 734.3-B-1、Fall SIGCOMM2003 书目待按标准格式核。
- arXiv:2007.10200 与 2311.06522 的完整作者名单/最终 venue 提交前核（标题/号/模型已核）。
- DZ/T 标准取文渠道为文档分享站（官方站 TLS 失败），等级标注保留。
