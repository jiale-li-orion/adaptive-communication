# 通信 context 自主构造：相关工作与方法借用

检索与阅读日期：2026-09-30。范围：主动信息获取、信息使用时刻、网络 Agent 的证据与在线评测。本表是有界的方向调研，不宣称系统综述或穷尽检索。论文结果未在本地复现；作者报告的性能不能直接移植为本项目预期。

## 1. 文献如何进入本项目

三条输入分别解决三个建设问题：主动特征获取提供取证策略；通信信息新鲜度工作提供时间建模；网络/调查 Agent 工作提供证据接口和闭环任务设计。每篇文献同时说明能借用什么、还需在本场景验证什么。

| ID / 工作 | 核验层次与状态 | 可借用的内容 | 与本项目的距离 |
|---|---|---|---|
| R01 [Near-Optimal Bayesian Active Learning with Noisy Observations](https://proceedings.neurips.cc/paper_files/paper/2010/file/1e6e0a04d20f50967c64dac2d639a577-Paper.pdf)，Golovin 等，NeurIPS 2010，EC² | 论文的等价类判定与算法说明 | 将共同对应一种决策的世界归入同类；成本敏感的自适应取证基线 | 静态等价类不能直接代表查询过程中会改变的执行机会；原理论保证不得直接套用 |
| R02 [Near Optimal Bayesian Active Learning for Decision Making](https://proceedings.mlr.press/v33/javdani14.html)，Javdani 等，AISTATS 2014，DRD/HEC | PMLR 书目、摘要与决策区域定义 | 多个世界共享可接受动作时即可停止，不要求唯一诊断或唯一标签 | 需要实例化任务结果、行动合法性和误判损失 |
| R03 [Active Feature Acquisition with Generative Surrogate Models](https://proceedings.mlr.press/v139/li21p.html)，Li、Oliva，ICML 2021 | PMLR 书目与方法摘要 | 用条件生成模型估计未知观测及获取价值，辅助取证策略学习 | 先使用可检验的经验模型；以后才考虑学习，不直接训练大模型生成物理事实 |
| R04 [Query Age of Information: Freshness in Pull-Based Communication](https://arxiv.org/abs/2105.06845v2)，Chiariotti 等，IEEE TCOM 2022，70(3):1606–1622 | arXiv 摘要、作者机构页面、Crossref DOI 元数据 | 在信息被使用的时刻评价新鲜度；通信机会和查询时刻相关 | 本项目需要对齐实际动作生效时刻及证据类型，不能只把 AoI 政名。DOI：10.1109/TCOMM.2022.3141786 |
| R05 [Pull or Wait: How to Optimize Query Age of Information](https://arxiv.org/abs/2111.02309)，Ildiz 等，2021 预印本 | 摘要层；未独立核期刊版本 | 将立即请求与等待作为同一决策空间，借用随机延迟下的参照建模 | 未精读证明，不引用其最优性范围作为本项目保证 |
| R06 [WirelessOpsAgent](https://arxiv.org/html/2608.08277v1)，Lu 等，2026 预印本 | 全文 IV-A–E 与评测接口 | 规范证据账本、时间/来源/依赖检查、局部修复；作为普通结构化 Agent 强对照 | 已覆盖大量 context 整合机制。本项目需测经过物理通信链的取得、时机或绑定增量 |
| R07 [MAP: A Map-then-Act Paradigm for Long-Horizon Interactive Agent Reasoning](https://arxiv.org/html/2605.13037v1)，2026 预印本 | 方法 §3.2 | 主动建图、任务特定探索、停止机制；可做 Agent 工作流对照 | 网络任务不能把地图完整度当目标；应按尚可兑现的监测动作停止 |
| R08 [DORA: Can LLM Agents Respond to Disasters?](https://arxiv.org/html/2605.11633v1)，Wang 等，NeurIPS 2026 Oral | 正文任务/工具/实验/工具顺序消融；作者主页与 NeurIPS 2026 下载页于 2026-10-01 复核接收状态 | 515 tasks / 45 events / 10 disaster types、108 typed MCP tools、3,500 gold tool-call steps；借 expert/replayable trajectory、Parameter Accuracy、deterministic replay、final-primary / trajectory-diagnostic 与 oracle ablation | 遥感/地理空间工作流不提供 battery、gateway receipt、Class-A opportunity、config apply/confirm、backup/DtS 等通信状态；其数据只适合作为上游 disaster evidence / Operational Task 来源，不能替换通信 data plane；当前 source inventory 尚未固定官方 code/data URL |
| R09 [ExCyTIn-Bench](https://arxiv.org/html/2507.14201v3)，Wu 等，2025 首版 / 2026 v3 | §3.2–3.3、§4.3；arXiv v3 作者注明 ICML 2026 接收，会议页未另核 | 从多表日志及调查图生成可追溯任务；按实体和时间跨表查证；评测中间进展 | 可借任务生成方式，不能把安全事件搬成新通信需求；物理任务仍由本项目来源契约产生 |
| R10 [NetArena](https://arxiv.org/html/2506.03231v2)，Zhou 等，ICLR 2026 | 官方项目入口、会议 PDF、v2 方法与评测 | 动态任务生成，Agent 与网络仿真器交互，同时测正确性、安全及延迟 | 借环境接线与评分，不引入数据中心场景。旧名 NetPress 与 NetArena 是同一 arXiv 的演进，不算两篇独立证据 |
| R11 [Agent-Native Telemetry: Verifiable State-Delta Evidence for Autonomous Operations](https://arxiv.org/html/2608.16178v1)，He、Yu，2026 预印本 | §2 与 ledger-relative verified negative、访问层 | 事件/观察/关系/检查点分离；带覆盖范围的证据片段；空结果只在已观测范围成立 | 紧凑账本和可验证否定已有先例；不复造加密协议。源端事件是否发生仍可能未知 |
| R12 [LENS: In-Context Search via Latent Evidence Exploration over Dynamic Raw Documents](https://arxiv.org/html/2608.16185v1)，Wang 等，2026 预印本 | 方法 §4.1–4.4 与主结果 | 低成本缩小候选范围、迭代定位、证据聚合和预算停止；适合先检索已有本地证据 | 文档检索与真实无线查询成本不同；论文自身的 evidence recall 与答案准确率也非同步改善 |
| R13 [NIKA](https://github.com/sands-lab/nika)，2026 软件项目 | 官方仓库 README；非已核实论文 | 在线故障环境、工具接入、Agent 轨迹与统一环境评测 | 可借 harness 组织，不借硬件假设或网络类型；未安装运行 |
| R14 [NetOpsBench](https://github.com/NetX-lab/NetOpsBench)，2026 软件项目 | 官方 README 和软件引用；非期刊论文 | 故障场景、诊断/定位、时间与工具成本分别报告 | 同上；不能把其基线性能搬进本项目 |

## 2. 新读文献产生的三个设计变化

**证据图用于生成任务的可评分依据。** R09 表明，直接让模型看全部日志生成问题容易得到泛化、不可判定的问题。这里应由已有义务与执行事件确定锚点，再用 node/record/window/path/time 的关系生成需要追溯的证据链。自然语言只是合法任务的表达层。生成图可使用离线真值；在线 Agent 只见按 owner 与时刻发布的证据投影。

**新鲜度在消费端定义。** R04/R05 说明信息使用时刻会改变查询策略。对本项目，同一电量或路径记录在“现在解释历史”与“等 Class A 窗口后安装配置”中具有不同价值。应把预计生效时刻、可用机会和证据变化界接入 context 更新，不只给每种字段一个固定 TTL。

**证据结构可以复用成熟设计，把研究投入留给决策行为。** R06/R11 已覆盖来源和依赖维护，R12 已覆盖预算化证据定位。先实现普通可靠版本，再研究任务绑定、查询分支和刷新触发如何改变通信结果。论文的差别需在场景中的可测行为上呈现。

## 3. 推荐阅读与实现顺序

先读 R09 §3.2–3.3 与 R10 §3，建立可运行任务；随后用 R06/R11 做普通证据底座。用 R01/R02 建静态取证参照，用 R04/R05 引入时间推进。只有连续任务中确实出现重复取证、代价或泛化瓶颈时，再把 R03 的学习方法接入。R07/R12 用于 Agent 工作流比较，不能仅用裸 ReAct 对照。

这组文献支持一个建设路线：来源任务 → 可执行证据调查 → 通信机会感知的取得与更新 → 实际任务结果。它们不支持“已有主动感知，所以本项目无问题”，也不支持“组合这些名称即有新颖性”。
