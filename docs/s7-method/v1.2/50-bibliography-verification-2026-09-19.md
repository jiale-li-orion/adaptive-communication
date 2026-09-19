# doc50　投稿前参考文献书目核验（refs.bib 占位条目升级）

日期：2026-09-19　｜　范围：把 `docs/s8-report/latex/refs.bib` 中 9 条 `@misc` 占位升级为带作者/卷期/页码/DOI 的规范条目；重建论文 PDF。
纪律：只采用从**一手记录**（arXiv 记录页/HTML、MDPI 期刊页、Eurecom 出版库、IFIP/IEEE、CCSDS、NTU 机构库）核实到的书目事实；核实不到的作者**不猜**，用 `and others`（et al.）并在 note 注明。本文不新增任何实验数字。

## 1. 逐条核验结果

| key | 真实出处（核实渠道） | 作者 | 关键修正 |
|---|---|---|---|
| `icldc` | **LLM-Enabled In-Context Learning for Data Collection Scheduling in UAV-Assisted Sensor Networks**，IEEE Internet of Things Journal 2025，DOI 10.1109/JIOT.2025.3615410；arXiv:2504.14556v2（arXiv 记录页 + HTML 系统模型） | Yousef Emami, Hao Zhou, SeyedSina Nabavirazani, Luis Almeida | **原 refs 标题"Constrained-queue scheduling with exogenous arrivals…"不是该文标题，属误述**，已改为真实标题。读其系统模型确认：地面传感器状态为 e_j={q_j 队列长度, γ_j 信道, b_j 电池}、外生感知数据、单 UAV 每步有限采集（服务）机会、安全 verifier override、以及把队列/电池/信道与丢包作为 feedback 回灌。故正文原"有界队列/外生到达/有限服务机会/反馈"的**状态模型锚点在该层面成立**，但它是 LLM in-context 采集调度论文、不是经典约束队列理论论文；related work 已改写为准确表述（见 §2）。 |
| `topollm` | **TopoLLM: LLM-Driven Adaptive Tool Learning for Real-Time Emergency Network Topology Planning**，Digital Communications and Networks 12:273–282，online 2025-10-01，DOI 10.1016/j.dcan.2025.10.002（Semantic Scholar corpus 282226083；ScienceDirect 全文本环境 403） | Yizhuo Ma, Rongzheng Wang, Ke Qin, **and others** | 正式版为 5 作者，本环境仅核实 3 位，按 et al. 标注、note 说明，不臆造另两位。正文删去未在正式标题/记录核实的"resource planning"，改为"adaptive tool learning for emergency network topology planning"。 |
| `icgrestore` | **ICG-Restore: Intent-Constrained, Graph-Enhanced LLM Planning with Minimal-Edit Repair for Post-Disaster Emergency Communication Recovery**，AI (MDPI) 7(8):294，2026，DOI 10.3390/ai7080294（MDPI 期刊页） | Jinyin Bai, Wei Zhu, Xiangchen Wang, Shiluo Guo, Zongzhe Nie, Tianjin Ni, Jinji Zhou, Kaiyang Kou, Lingxin Xu, Yihao Zhong（10 位全） | 由 misc 升 @article，补全作者/卷期/DOI。 |
| `ossgpt` | **OSS-GPT: An LLM-Powered Intent-Driven Operations Support System for 6G Networks**，IEEE NetSoft 2025（Budapest, 2025-06）；另有 SIGCOMM 2025 版"Next-generation 6G network management with OSS-GPT"（Eurecom publi-8206 出版库） | Abdelkader Mekrache, Adlen Ksentini, Christos Verikoukis | 由"Eurecom technical publication"改为正式 @inproceedings(NetSoft)，note 注明 SIGCOMM 版本。 |
| `sdnconsistency` | **Consistent Updates in Software Defined Networks: On Dependencies, Loop Freedom, and Blackholes**，IFIP Networking Conference and Workshops, Vienna, pp.1–9, 2016，DOI 10.1109/IFIPNetworking.2016.7497232（Semantic Scholar/ACM/IEEE 多条一致） | Klaus-Tycho Förster, Ratul Mahajan, Roger Wattenhofer | 原记为"Microsoft Research technical report"（MS URL 实为作者托管副本），改为正式 @inproceedings。 |
| `zakeri2311` | **Semantic-Aware Sampling and Transmission in Energy Harvesting Systems: A POMDP Approach**，arXiv:2311.06522v4（preliminary at Asilomar 2023 / IEEE GLOBECOM 2023） | Abolfazl Zakeri, Mohammad Moltafet, Marian Codreanu | 原 refs 标题"Energy harvesting wireless control under partial observability (EH-POMDP)"非真实标题，已更正；采样+传输成本、部分可观测的联合优化定性不变。 |
| `bacinoglu1905` | **Optimal Status Updating with a Finite-Battery Energy Harvesting Source**，arXiv:1905.06679v3 | Baran Tan Bacinoglu, Yin Sun, Elif Uysal, Volkan Mutlu | 补全作者、改为真实标题；"门限为瞬时电池电量非增函数"的引用定性与原文一致。 |
| `ccsdssabr` | **Schedule-Aware Bundle Routing (SABR)**，CCSDS 734.3-B-1，Blue Book Issue 1，**2019-07**（CCSDS 官网蓝书页 + PDF 封面） | 机构作者 Consultative Committee for Space Data Systems | 补年份/期号；正名是 **Schedule-Aware**（非 Scheduled-Aware）；SABR 处理"已调度而非机会性"接触下的动态路由与 overbooking。 |
| `sateriot` | **SateRIoT: High-Performance Ground-Space Networking for Rural IoT**，Proc. ACM MobiCom'24（30th MobiCom）（NTU 机构库 dr.ntu.edu.sg） | Yidong Ren, Amalinda Gamage, Li Liu, Mo Li, Shigang Chen, Younsuk Dong, Zhichao Cao | 本环境一手摘要仅核实 temporal link estimation 与 ground-space 集成；**未在一手记录核实"priority queue / de-duplication"**，故 related work 弱化为"按估计的时间卫星接触调度"，不再断言未核实机制。 |

## 2. 正文（main.tex）三处对齐

1. `icldc` 句：从"Constrained-queue scheduling with exogenous arrivals and finite service opportunities provides our formal anchors"改为"a recent LLM in-context data-collection scheduler … whose state model pairs per-sensor bounded queues, exogenous sensing arrivals, one-UAV finite per-step service opportunities, battery/channel state, and a verifier feedback loop"。**结论不变**（该文提供最接近的状态模型先例，且作为强基线/上界工具而非稻草人），只是不再误称其为约束队列调度理论。
2. `topollm` 句：改为正式标题口径（adaptive tool learning / real-time emergency network topology planning）。
3. `sateriot` 句：改为 temporal satellite contacts；并把它与"deadline discard"机制分句，避免把非丢弃工作并入并列。

其余引用（ICG-Restore/OSS-GPT 的 intent/预算/时间窗/候选计划检查/局部修复/文档化 API 编排；Bacinoglu 瞬时电池门限；Zakeri 部分可观测 EH 控制；CCSDS overbooking；SDN 一致性更新的依赖/无环；RFC 5050/9171 custody）经本次核对与原文定性一致，未改。

## 3. 未核实项与局限（不得当作已核事实）

- TopoLLM 正式版 5 作者中仅核实 3 位（ScienceDirect 全文 403）；已用 et al. 诚实标注。
- SHETLAND-NET 现场端点在本网络仍 403/429，论文不引用其任何数字。
- 未运行任何被引系统的作者参考实现，论文不声称复现（limitations 已声明）。
- DZ/T 0460 取文渠道仍为文档分享站（A 级文档 / D 级复制链），官方站 TLS 失败，条款号经两份独立副本复核（doc49 已记）。

## 4. 构建核验

refs.bib 共 22 个条目、**全部被正文引用**；`pdflatex→bibtex→pdflatex×2` exit=0，论文 **19 页**，无 undefined citation/reference、无 bibtex error；新书目在 PDF p.17–19 渲染正确（作者、卷期页、DOI、note 齐全）。
