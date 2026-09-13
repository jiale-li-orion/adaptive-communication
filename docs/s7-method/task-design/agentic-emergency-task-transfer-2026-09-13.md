# Agent 调度通信与恢复：任务设计可继承性复核

日期：2026-09-13。承接用户提供的七篇候选，服务于 [Task v1.1](../task-contract-v1.1.md)，不另开灾后／UAV 研究方向，不宣称已完成系统性检索。用户本轮确认：老师／中通服是否已有“中心必须介入”的具体运维流程，**当前未知**；该未知已进入契约扩展边界。

## 1. 时间和文献谱系

这些论文构成相近工作集合，不能仅按正式卷期认定均为“TopoLLM 之后出现”的方法。Public Safety UAV 的作者预印本始于2025-06；WirelessAgent 有2025-05预印本及更早的同题版本。论文互引、方法继承和刊出时间需要分别核查。本轮不据七篇名单下结论说相关领域稀疏或某一空白无人研究。

## 2. 候选核验与借用边界

| 工作及来源 | 本轮核验到的对象 | 可以借用 | 不能由此证明 |
|---|---|---|---|
| **From Prompts to Protection**，IEEE Wireless Communications，DOI [10.1109/MWC.2026.3666489](https://doi.org/10.1109/MWC.2026.3666489)；[作者版2506.02649](https://arxiv.org/html/2506.02649v1) | 出版社检索可确认期刊／DOI；作者全文 §IV–V。正式题名用 Assisted，作者版用 Enabled。案例基于队列、信道状态安排 UAV 数据收集，讨论移动、速度和功率等动作 | 任务目标、输入、可行动作、示例、反馈的显式规格；数据收集有来源支持的队列竞争 | 这些队列状态在山区固定节点可免费实时获取；控制消息和回执中断已被评测；全部讨论动作均有独立完整实验 |
| **WirelessAgent**，China Communications 23(3):265–285, 2026；[出版社](https://ieeexplore.ieee.org/document/11503159/)，[作者版2505.01074](https://arxiv.org/abs/2505.01074) | 出版社摘要、出版信息：LangGraph workflow，network slicing；有规则对手和代码链接 | planner／工具动作拆分、意图到资源配置的接口，强规则对照 | 灾前监测需求、低功耗端点的执行语义；本轮未复跑其代码 |
| **LODA**，Computer Communications, 2026，DOI [10.1016/j.comcom.2026.108566](https://www.sciencedirect.com/science/article/pii/S0140366426001568) | 出版社摘要与引言：LLM 迭代联合优化 UAV 部署和资源；明确集中式、理想通信的评价范围，onboard fallback 为扩展讨论 | 状态／QoS／约束 → 候选方案 → 性能反馈的闭环；明确理想通信假设 | fallback 已实现或验证；作者将其称上界不构成数学最优上界证明；UAV 移动能力适用于固定监测站 |
| **LPTORA / LLM enabled DRL for trajectory optimization and resource allocation in UAV-assisted emergency communication networks**，Physical Communication 77:103177, 2026，DOI [10.1016/j.phycom.2026.103177](https://www.sciencedirect.com/science/article/pii/S1874490726001862) | 出版社摘要与引言：PPO 执行联合优化；LLM 辅助奖励生成与修订；用户／业务模型由作者定义 | 正式列出决策变量、外部过程、资源约束和目标 | 在线 tool-using LLM 承担恢复；其灾后移动用户模型就是灾前传感事件模型 |
| **Large Language Model-Enabled Reinforcement Learning for Wireless Network Optimization**，IEEE Communications Magazine, 2026，DOI [10.1109/MCOM.001.2500384](https://doi.org/10.1109/MCOM.001.2500384)；[作者机构记录](https://pure.qub.ac.uk/en/publications/large-language-model-enabled-reinforcement-learning-for-wireless-/)，[2602.13210](https://arxiv.org/abs/2602.13210) | 机构记录与作者摘要：LLM 状态表示／语义提取辅助 MARL；包含迁移、路由与 UAV–卫星拓扑案例 | 区分 LLM 辅助优化、在线决策及执行层的角色 | 长期灾前 workflow、低功耗 LoRa 控制面的实证 |
| **LLM-driven smart agents using tools for the recovery of interdependent infrastructure networks**，ESWA, 2026，DOI [10.1016/j.eswa.2026.132701](https://www.sciencedirect.com/science/article/abs/pii/S0957417426016143) | 出版社摘要／章节摘录及作者仓库：39工具、TS-ReAct、50任务；Shelby County案例。工具覆盖恢复顺序、资源分配等计算 | 从领域文献中的任务到工具集合；发布任务表、输入与评价结果；任务选择与执行分离 | 算法工具调用等同现场设备动作；高 task success 证明物理基础设施恢复或无线断连恢复 |
| **LLM-empowered agents for lifeline network recovery with graph-guided MCP tools**，Sustainable Cities and Society 149:107846, 2026-10卷期，DOI [10.1016/j.scs.2026.107846](https://www.sciencedirect.com/science/article/pii/S2210670726007304) | 本轮出版社已可访问摘要／引言：47 MCP工具、50任务、图引导工具链模式 | 工具前置依赖、工具链选择／执行模式的对照；可检查任务集合 | “跨多个工具持续执行恢复任务”本身仍是空白；这50任务已外推到长期灾前监测 |

本轮未统一核实所有论文的最早上线日；除直接核到的出版信息外，不填日级时间。ESWA 的作者机构检索返回2026-05-06上线，仓库也公告2026-05上线；SCS 的未来卷期不妨碍当前出版社已有在线正文。作者版与刊物版不混用版本特有的实验结论。

## 3. 更直接的任务母论文：ICLDC

Public Safety UAV 的参考文献[14]指向：**Emami 等，LLM-Enabled In-Context Learning for Data Collection Scheduling in UAV-Assisted Sensor Networks**，[arXiv:2504.14556](https://arxiv.org/abs/2504.14556)，相关 IEEE IoT Journal DOI [10.1109/JIOT.2025.3615410](https://doi.org/10.1109/JIOT.2025.3615410)。初版2025-04-20，v2为2025-10-15；本轮读取作者版系统模型／协议及版本摘要，采用 [v2](https://arxiv.org/html/2504.14556v2) 作为后续精读锚点。

它比综述式 UAV 文章更适合核对数据收集任务：对象是多个有队列的传感器，选择数据收集对象会影响溢出和通信错误；通信过程含选择／beacon、传感数据及状态、确认。v2还加入规则 verifier，不能用 v1 的对照替代 v2 的完整方法。

**可继承的抽象**：有界队列、外生数据到达、可选服务对象、有限服务机会、接收结果反馈；调度后果按独立环境评估。**本项目需另证的变化**：固定监测站、现场事件规则、能源收支、Class A 可达性、网关—中心回传、证据陈旧和命令执行结果。不得借其 UAV beacon 协议让 Class A 叶节点随叫随到。

这个模型已允许“外生到达＋观测驱动选择”。因此旧文档把外生需求本身判为没有决策，不能成立。反过来，将该调度目标加到监测网里，也不自动证明新颖性；需指出上述哪一项变化改变了可行行动、信息或最优取舍，并给出公平对照。

## 4. ESWA artifact 能提供的具体材料

作者公开仓库：[Smart-Agents-for-the-Recovery-of-Interdependent-Infrastructure-Networks](https://github.com/ayupow/Smart-Agents-for-the-Recovery-of-Interdependent-Infrastructure-Networks)。本轮仅核对网页目录，未运行或导入代码。目录可见39工具实现、ReAct／TS-ReAct运行代码，以及 `Table S1 39 developed agent-oriented tools and a 50-task IIN recovery test set.xlsx`、响应与鲁棒性表。

后续若沿用任务表组织方法，应逐题提取：任务来自哪篇领域文献、输入从哪里来、工具有何前置条件、正确答案怎样得到、替代工具链是否允许、失败怎样计分。**当前只确认 artifact 存在，没有宣称其50题已经逐题审计。**

该类工作的“执行工具”可能是在模型上计算恢复方案。要映射本项目，应分别标出计划计算、模拟器状态修改、经真实通信到达的设备操作；三个层次不能用同一个“执行成功”指标掩盖。

## 5. 对当前 task 的正式影响

采用三类来源分工：**现场论文与设备协议决定业务义务和能力；监测／调度论文决定形式化对象与指标；agent论文决定任务表、工具边界和闭环评价组织。** 不要求已有论文已经使用 agent 才承认某个监测问题有价值，也不要求合作方预先提出算法。

用户确认工作流未知后，跨节点升级／全局资源分配可继续作为待验证的研究假设，允许用公开领域证据补充；不将“尚未被合作方提出”写成“不允许研究”。升级为核心义务需要说明其服务何种已经存在的目标、什么共享资源产生竞争，以及本地／网关既有方案为何未直接解决。不能只用“这让agent有事可做”解释任务。

“跨采集、配置、回传、恢复和路径切换的长期 workflow”可以作为候选研究范围；目前不能称为已证实的明显空白。上表已经覆盖数据收集调度和灾害工具链组织，新增动作类别的数量不足以构成贡献。可检验的差异应落在：**相同监测义务和硬件下，部分可见且需要通信才能执行的控制，是否改变长期服务／成本表现。**

**D54：文献继承与现场需求分工。** ICLDC优先作为调度问题锚点，ESWA artifact作为任务表设计锚点，LODA作为理想通信假设对照；不迁移UAV硬件、不扩大灾后范围、不启动新实验、不冻结方法优势或唯一性主张。MARL清单本轮未逐篇核验，不进入事实依据表。
