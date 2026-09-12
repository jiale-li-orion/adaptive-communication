# Agent runtime for maintaining task execution over churning emergency-communication entities

状态：调研与设计阶段。性质：通信论文，目标venue为 JSAC / TCOM / TWC / TMC / INFOCOM。

## 命题

现有应急通信研究在给定的网络角色与通信基础设施之间做组合与恢复。本文将 agent runtime 置于这些通信实体之上，研究对象是它在实体动态上线、掉线、退化、恢复时维持任务执行的能力。

场景取灾前山区滑坡与泥石流监测，供电受限且链路频繁中断。底层资源是通感算一体化的多实体集合，包含 LoRa、NB-IoT、CPE、UAV、HAPS、卫星与微波。

**关键结构假设：agent 的观测通道与它的控制通道是同一条。** 它没有带外信道，没有独立的健康监测接口，没有预示实体将要掉线的先知信息。它判断某实体是否可用，只能向该实体发一次调用并观察结果，而这次调用本身穿过它试图评估的那条链路。因此"实体已静默"与"我的查询在回程丢了"在观测上不可区分，只能靠后续调用的时序模式逐步排除。既有工作多在"状态可观测"或"故障发生可被检出"的前提下讨论恢复策略，本文的自变量正是这道观测投影带来的不确定性。

## 一、定位

|  | 现有应急通信 | 本文 |
|---|---|---|
| 通信实体 | 给定的选项池，在其间组合与恢复 | 动态集合，随时间上线、掉线、退化、恢复 |
| 研究对象 | 组合策略、切换时机、恢复路径 | 任务执行在集合变动下的存续 |
| agent 角色 | 选择器 | 运行时 |

### 支撑命题的证据

**政策层面。** 工信部联信管〔2024〕256号（14 部门，2024-12-31）点名断路、断电、断网，把北斗短报文与天通列为基层兜底手段，要求设备适应严寒与密林，目标年为 2027。十五五方案（自然资办函〔2026〕1198号）不含任何传输连续性、功耗或覆盖要求，因此通信侧的论证只能引 256 号文。

**灾害中的实体退服记录。** 第二周汇报第 30 至 34 页整理了四起事件，其中的实体损失为：2026 年西藏吉隆口岸泥石流造成 5 个基站退服，同期投入卫星电话 36 部、便携卫星设备 10 套、发电油机 18 台；2024 年四川康定姑咱泥石流造成 22 km 光缆受损与 7 个基站退服，投入 1 架大型无人机基站、6 辆应急通信车、9 台高通量卫星便携基站；2024 年日本奥能登土砂灾害一度中断 88 个基站，靠移动基站车与可搬型基站恢复；2023 年新西兰 Gabrielle 滑坡破坏主干光纤，峰值约 20% 基站离线，Gisborne 一度有 90% 基站在两天内离线，临时回传改走卫星与微波，容量低于原光纤。

**物理约束，来自本项目实测。** 西藏波密与易贡的 SRTM 地形海拔跨度为 2025 至 6690 m。单网关在 121×121 网格上的可达点仅 1689 个，占 11.5%；连不通的点 12952 个，占 88.5%，这些点在 SF12 下仍不闭合。决定连通性的是遮挡而非距离：8.37 km 处有 1169 m 遮挡的点位损耗 217.0 dB，12.61 km 处只有 1102 m 遮挡的点位损耗 201.2 dB，近 4.2 km 反而差 15.8 dB。地形遮挡造成的超额损耗在 71 至 107 dB 量级，而 SF 从 7 提到 12 只增加 14 dB 灵敏度，因此链路自适应无法救回被地形挡住的节点。ChirpBox 真实轨迹（20,913 快照、420 条链路）拟合出的丢失率为 7.44%，平均中断突发 3.30 h，而同丢失率下 i.i.d. 模型只预测 1.08 h，两者相差 3.1 倍。供电侧，LiFePO4 在 −20 °C 下容量约为标称值的 50%，且低于 +5 °C 无法充电，高海拔站点因此在冬季长时间静默。

**同类论文的结构性空白。** 对 9 篇近期 JSAC / TCOM / TWC / TMC / TVT 同域论文的通读给出四个计数。分母 9 是本次侦察中读到方法与评测层的篇数，非普查；论文中只能表述为 *in the nine papers we surveyed*，不能写成 *no work does X*。方向上有更强的旁证：2025 年一篇 COMST 综述统计 130 篇基于机器学习的资源分配论文，详审的 27 篇中绝大多数不共享源码，78.46% 未给可用的数据来源信息（见 `docs/s5-benchmark/s6-7-experimental-norms.md`）。用 DEM、地形数据库或实测信道 trace 论证仿真真实性的为 **0 篇**，地形最多作为几何抽象出现（一个环形部署廊道），多数完全缺席；3GPP TR 38.901 参数表的使用为 0 篇。设立失效与中断模型小节的为 **0 篇**，中断在多数工作中是参数扫描的一个维度而非被建模的过程。运行第三方公开实现作对照的为 **0 篇**，其中 6 篇以重实现或自建方式构造对照。用外部 benchmark 或公开数据集作评测基底的为 **2/9**（一篇用 Sub-SkyFinder 图像数据集作学习底座，一篇用真实太阳能采集数据驱动能量模型），且无一采用"公共 benchmark 加统一协议"的形式。这四条同时说明本文的差异化位置与对照方案的构造惯例。

**任务级可靠性没有公认指标名。** 同域论文中的可靠性一律写作链路级的 coverage / outage probability，或服务级的 availability / feasibility rate；"reporting rate"、"mission completion" 这类任务级说法在通读的 9 篇中一次未出现。本文使用的到报率与零执行周期属任务级指标，须在首次出现处给出定义式并论证其必要性。

**一处数据空白。** 中国地灾监测网络的实测可靠性数据在公开文献中不存在，到报率、在线率、掉线次数、断链时长均无数值，可查到的只有合同条款（广东验收 ≥70%，昆明 ≥95%，河南 ≥95%）。本研究给出的是估计值，不是实测值。

## 二、通信实体的分类

下面三张表来自第二周汇报，每张表附其原始文献依据。它们共同定义通信实体集合：每个实体带角色与基础设施类型，并投影成 agent 可调用的 capability。本文不研究该用哪一类实体，那三张表已经回答；本文研究集合随时间变动时任务如何继续。

### 按灾损断点选恢复手段

出处为汇报第 36 页，依据为 [5] SAGIN 灾害管理综述（IEEE TNSM 22(5):4021–4049, 2025）与 [6] 灾害区域网络综述（IEEE Access 13:91129–91160, 2025）。

| 灾损断点 | 恢复手段 |
|---|---|
| Sensor 接入困难 | LoRa / NB-IoT |
| 蜂窝弱覆盖 | CPE / UAV Relay / UAV-BS |
| 局部基站退服 | 便携站 / 应急车 / UAV-BS |
| 光缆 backhaul 中断 | 微波 / HAPS / 卫星 |
| 大范围地面网络失效 | HAPS / 卫星 / NTN |
| 电源失效 | 油机 / 移动电源 |
| 线路物理损坏 | 光缆抢修 / UAV 辅助布缆 |

### 按 UAV 通信角色分

出处为汇报第 16 页，依据为 [20] OWAID et al., ICEEE 2024 的 UAV 辅助通信综述，以及 [21] NICT 与 [22] ZTE 的工程方案。角色分为 `Relay`、`Base Station`、`Airborne UE` 三类，架构分为 `Infrastructure`、`Ad-hoc`、`Hybrid` 三类，工程组网有四类形态：UAV Relay、UAV 临时基站、UAV+CPE、UAV Mesh。

### 按低功耗接入与回传的组合分

出处为汇报第 14 页，依据为 [14] JOUHARI et al., IEEE COMST 25(3):1841–1876, 2023 的 LoRaWAN 综述与 [15] 工信部 2017 年第 27 号公告。组合方式为 LoRa + 4G/卫星、NB-IoT + 运营商核心网、LoRa + NB-IoT、LoRa Mesh + 卫星。

## 三、现状盘点

### 可用数据

| 数据 | 内容 | 许可 | 用途 |
|---|---|---|---|
| SRTM1 | 30 m 全球高程 | 公开 | 地形与链路可达性（已用） |
| ChirpBox（Zenodo 5527877） | 21 节点、4.5 个月、逐链路 RSSI/SNR 与天气 | CC-BY-4.0 | 断链的时间相关结构（已用） |
| Strasbourg（Zenodo 20390366） | 5 年 LoRa 抓包，25.5 GB | CC-BY-4.0 | 跨年泛化检验 |
| LoED（Zenodo 4048255） | 9 网关、约 1130 万条报文，含 `crc_status` | CC-BY-4.0 | 丢包结构 |
| LoRa on Ice（Zenodo 13693107） | 逐包收发与 GPS、距离、RSSI、SNR，含真实中断弧线 | CC-BY-4.0 | 单链路验证 |
| LR-FHSS 电流实测（Zenodo 13838241） | 端设备实测电流 | CC-BY-4.0 | 能耗模型校准 |
| IODA | 5 分钟粒度断网与恢复轨迹，2013 年至今，逐区域与逐 ASN | Georgia Tech 版权 | 真实 outage 生命周期 |
| FEMA TEMPO | 县粒度日度基站退服，含 damage / power / transport 归因 | 无明确许可 | 事件时间线校准 |

山区 WSN 链路轨迹数据集不存在：ChirpBox 采自上海城区，LoED 采自城市，LoRa on Ice 采自南极海冰。空间维故障因此由真实地形加标准传播模型合成，时间维借用真实轨迹的统计结构。

### Baseline

第一层是通信侧对照，每条附原始出处。

| baseline | 出处 | 隐含假设 |
|---|---|---|
| ADR / 链路自适应 | Reynders, Meert, Pollin, *Power and spreading factor control in low-power wide area networks*, IEEE ICC 2017, DOI `10.1109/icc.2017.7996380`；Haxhibeqiri et al., *A Survey of LoRaWAN for IoT*, Sensors 18:3995, 2018, DOI `10.3390/s18113995` | 链路存在，只需调 SF 与发射功率 |
| DTN store-and-forward | Fall, *A delay-tolerant network architecture for challenged internets*, ACM SIGCOMM 2003, DOI `10.1145/863956.863960` | 接触机会到来即可转发 |
| Spray-and-Wait | Spyropoulos, Psounis, Raghavendra, ACM SIGCOMM Workshop 2005, DOI `10.1145/1080139.1080143` | 靠副本数控制投递率 |
| AoI 最优调度 | Kaul, Yates, Gruteser, *Real-time status: How often should one update?*, IEEE INFOCOM 2012, DOI `10.1109/infcom.2012.6195689`；综述见 Yates, Sun, Brown et al., IEEE JSAC 39:1183–1210, 2021, DOI `10.1109/jsac.2021.3065072` | 控制信道可靠，命令按时下达 |
| Whittle 指数调度 | Hsu, *Age of Information: Whittle Index for Scheduling Stochastic Arrivals*, IEEE ISIT 2018, DOI `10.1109/isit.2018.8437712` | 全部信道状态可观测 |
| Max-weight / 吞吐最优 | Tassiulas, Ephremides, IEEE TAC 37:1936–1948, 1992, DOI `10.1109/9.182479` | 队列状态可观测且控制可靠 |
| 多连接链路选择 | Khan, Jacob, *Link Adaptation for Multi-connectivity Enabled 5G URLLC*, IEEE COMSNETS 2021, DOI `10.1109/comsnets51098.2021.9352811` | 各链路状态可及时获得 |
| 单链路 / 静态选择 | 退化参照，无单一出处 | 无多链路 |
| Oracle | 已知未来链路状态的上界 | 全知 |

第二层是 agent 侧对照：ReAct（Yao et al., ICLR 2023, arXiv `2210.03629`）；blind retry 与指数退避（工程惯例，见 AWS Builders' Library 与 Google SRE Book）；verified wrapper（Mansoor, Phadke, Rana, arXiv `2608.02645`）；默认工具超时语义（MCP 规范 2026-07-28 的 Cancellation 章）。

第三层是场景对照，即已发表的 LoRa 滑坡与落石监测系统。它们同时是本文参数的实测来源和自然对照集：读者会问"你的设置与真实部署差多远"，这一层就是回答。

| 系统 | 规模与组网 | 采样与载荷 | 发射功率 | 能耗实测 | 地形处理 |
|---|---|---|---|---|---|
| 贵州水城滑坡监测（Wang et al., *Frontiers in Earth Science* 10:899509, 2022） | 5 套设备，星形单网关，回传走 4G，连续运行 9 个月 | 定时 1 h；触发时 5 min×3 包；阈值雨量 0.2 mm、位移 20 mm | 30 dBm（1 W） | 12 V/10 Ah LiFePO4 加太阳能，板功率未报告 | 未建模；作者称现场有效范围 <3 km 故不设中继 |
| Pantelleria（Ragnoli et al., *JLPEA* 12(3):47, 2022） | 12 节点、2 网关，LoRaWAN Class A 加 ADR，回传走 LTE | 60 min，载荷 38 B，单次活跃窗口约 15 s | 13 dBm | 活跃 35.7 mA、待机 16 µA、周期 0.148 mAh、日均 3.56 mAh、无光照约 2.8 年（INA229 实测） | 未建模；观测到部分节点丢包 |
| Hochvogel 高山岩土监测（Leinauer & Krautblatter, EGU25-11121, 2025） | 10 至 12 个传感器，单一网关，自 2019-10 连续运行超过 5 年 | 10 min | 未报告 | 未报告 | 多数传感器处于射频量程边缘，水平 2800 m、垂直 1500 m，且大多无直接视距 |
| FresSim 验证场景（Torres-Sanz et al., *Internet of Things* 38:102012, 2026） | 6 端节点加 1 网关，另有 5 网关覆盖图场景 | 未报告 | 14 dBm | 睡眠电流 3.5 µA | **显式建模**：DEM 剖面逐点判第一菲涅尔区净空，60% 判据；12 场景与实测连通性 100% 一致，不含地形的基线仅 50% |

上表的用法有三处。参数直接采用，见系统模型；FresSim 的判据作为本文地形模块的方法依据与验证靶子；贵州水城与 Pantelleria 的实测间隔（1 h 与 60 min）与 Hochvogel 的 10 min 共同界定本文采样间隔的取值范围。

对照构造的惯例需要声明：通读的 9 篇同类论文中，运行第三方公开实现作对照的为 0 篇，6 篇以重实现或自建方式构造对照。本文沿用该惯例，并公开代码。

### Benchmark

六个现有 agent-network benchmark 全部不适用于本文场景，判断基于对六篇论文 arXiv HTML 全文的阅读与仓库检查，逐条记录见 `docs/s5-benchmark/s6-9-benchmark-comparison.md`。

| benchmark | 故障模型 | 网络的角色 | 载体 | 能量建模 | 地形建模 |
|---|---|---|---|---|---|
| WirelessOpsBench（WirelessOpsAgent 论文，`2608.08277`） | 7 类证据账本故障，每 base 七个孪生 case | 对象（动作授权） | 无 runtime；只发数据与工具契约，射线追踪工具供 CQI | 无 | 仅 HKUST_North / HKUST_South 两区域 |
| NetConfArena（`2608.23179`） | 不注入，只有 agent 自身的配置错误 | 对象（配置） | GNS3 加厂商路由器镜像，存在许可问题 | 无 | 无 |
| NetArena（`2506.03231`） | 每次查询合成 | 对象（规划与修复） | Mininet 加 Kubernetes 与 Docker | 无 | 无 |
| NIKA（`2512.16381`） | 经 Linux TC、stress-ng 与脚本注入，54 问题 / 640 事件 | 对象（检测、定位、根因） | Kathará 容器 | 无 | 无 |
| NetOpsBench | 注入 `tc` 常量（`loss_pct=30`、`latency_ms=100`），12 类 | 对象（监测与诊断） | Containerlab 加 SONiC-VS，仅限 Linux 且资源占用高 | 无 | 无 |
| WirelessBench（`2603.00501`） | 无故障，答案为确定性规则或专家解 | 对象（静态解题） | 无仿真器；数据集加 OSM 射线追踪工具 | 无 | 部分，仅 2D 建筑几何 |

其中两条自述可以直接引用。NetConfArena 把容错列为未来工作，原文为 *"we plan to add … tasks that target fault-tolerant configuration scenarios"*，其指标 *"target the functional correctness of the final network behavior rather than network performance such as latency, congestion, or transient routing dynamics"*。NIKA 明确不支持评估缓解动作，原文为 *"NIKA currently focuses on diagnosis tasks (detection, localization, RCA) but does not yet support evaluating mitigation actions"*。

三个维度上的核验结果如下。agent 自身的操作通道是否退化：六篇全文检索 agent 通道相关构造（agent 自身流量与连接、带外控制面、边缘部署 agent、agent 之间的连通性）零命中，网络在这六个基准中始终是控制的对象，不承载 agent 自身的遥测。故障是否由真实地形与供电导出：六者的故障全部为注入、合成或不存在，词汇层面最接近真实的是 WirelessOptBench（其分类引用 TeleLogs、AIOps2025、RCA100），但该论文承认 oracle 是 benchmark 自定义的；NetOpsBench 用的是手设常数。任务是否为长时监测 mission：NIKA 与 NetOpsBench 最接近，但都是单事件式，一次事件完成检测、定位与根因后即结束；NIKA 报告的 7 至 15 小时是 150 个事件的累计墙钟时间，NetOpsBench 的 efficiency 统计的是 tool call 数与 token 数。二者都不惩罚中途漏掉事件、不惩罚信道随时间衰减、不要求跨小时维持态势。

能量与功率建模在六个基准中全部缺失，地形与传播建模只出现在 WirelessBench，且仅作为 agent 可调用的 CQI 工具，不是其流量所穿越的信道。这属于结构差异而非参数差异：六个基准都把网络固定为控制对象，因此自建 benchmark 不必要也无收益。

### 仿真平台

上表六个都是 LLM-agent 的任务套件，属另一物种。通信领域的惯例不是任务套件而是**仿真器加标准信道模型加可复现场景**：通读的 9 篇同类论文中用外部 benchmark 作评测基底的仅 2 篇，且无一采用"公共 benchmark 加统一协议"的形式，其余全部为作者自建仿真。因此本文不寻找 benchmark，而是选定仿真器栈并公开场景定义。

候选与其状态如下，均为本次逐一核验。

| 平台 | 覆盖 | 状态 | 与本文的关系 |
|---|---|---|---|
| ns-3.48 + FLoRa | LoRaWAN 的 MAC/PHY | 活跃；FLoRa v0.3.7 要求 ns-3.48 | 标准 LoRaWAN 平台，自带 `LoraRadioEnergyModel`、干扰模型与 ADR 组件。本文的协议与能耗层 |
| Sionna RT | 可微射线追踪 | 活跃 | 课题组既有平台（Sionna 0.19.1 的 RayTracing，OSM 加 Blender 场景，基站-RIS-UAV，3.5 GHz）。RT 接受 Mitsuba 场景，因此可把 OSM 楼房换成 DEM 地形网格，在同一工具链上落到本文场景 |
| Longley-Rice ITM | 不规则地形传播 | 稳定 | 本文地形维的物理模型，非射线追踪。与 RT 互为交叉验证 |
| The ONE | DTN 与机会网络 | 半死（master 最后提交 2023-04）；Helsinki 地图另有许可限制 | 仅作方法学参考。其基线多数依赖节点移动相遇，在固定节点加间歇链路中退化 |
| SNS3 | 卫星 DVB-S2/RCS2 载荷 | 活跃 | 卫星回传若需载荷级细节时使用。ns-3 已内置 LEO 移动模型与 3GPP TR 38.811 NTN 信道，起步不必依赖它 |

平台选择同时承担一项验证义务。FresSim 的实测场景给出可复核的靶子：6 个端节点距网关 190、250、500、620、2200、3200 m，网关海拔 1295 m、节点 1285–1385 m，需复现三个定性结论——2200 与 3200 m 的山区链路不通、平坦地形通、超长距 28 km 场景可通。本文的地形模块以复现这三条为验收标准。

传播模型按**三档递增真实度**组织并逐档量化增益：自由空间 → 加 DEM 视线遮挡 → 加刃峰绕射。该叙事结构取自同类文献的既有做法，本文沿用并把"只按距离"作为最低档对照，用于量化地形建模本身带来的差异。

### 采用方案

不新造 benchmark，不定义新 task，只补已有 benchmark 缺的执行层。任务语义、工具契约、预算、合法迁移与里程碑继承 WirelessOpsBench 的公开开发集。

继承的边界由公开包的实际内容划定。公开包只有数据：300 base、2400 case、180 repair，无 runner、无 scoring 谓词、无 fault schedule。同一 base 的八个 case 的 `public_task` 逐字节相同，仅 `case_id` 不同；`public_input` 只含任务参数，WCHW 一族为空对象；全库无答案、gold、reference 或 label 字段。证据账本、`ray_tracing` 实现与评测谓词均在评测端扣留。因此可直接取用的是任务契约层，不是可运行的 episode。

须自建的四项为证据账本内容、CQI 提供者、runtime 与 scoring 谓词，即本文所补的执行层。公开包不含 baseline 分数、轨迹、token 数与延迟，故本文数值不与论文所报数值可比，只能作为本文自己的 development 结果报告。完整核验见 `docs/s5-benchmark/s6-10-wirelessopsbench-artifact-audit.md`。

工具面九项，真正变更状态的只有 `commit_policy` 与 `rollback_policy`，`stage_policy` 与 `post_check` 的 `mutates_state` 均为 False。`commit_policy` 要求 `stage_id` 与 `expected_version`，已带乐观并发；`stage_policy` 带以 `protected_*_impact` 为风险字段的危险提案带。状态机三族同构：`stage_<fam>` → `validate_evidence` → `commit_authorization` → `post_check` → `rollback`，外带一条指名实体的 `refresh_then_validate:<entity_id>`。预算为 `max_steps` 24、`max_tool_calls` 12、`wall_time_ms` 60000。

层栈相邻关系直接来自论文标题。WirelessOpsBench 做 **Task correctness → Action assurance**：判据是动作在分发前是否被正确授权，其 7 类故障——temporal inconsistency、missing required evidence、conflicting sources、schema drift、entity misbinding、concurrent version drift、false-success update——全部落在证据账本的可信度上。本文在同一任务契约上补 **Execution assurance**：判据是动作分发之后到底发生了几次、有没有发生。

这两组判据不可互相表达。WirelessOpsBench 的 false-success update 是上报成功但状态未生效；本文的 ACK 丢失是状态已生效但回执未达，重试即产生重复副作用，方向相反。其 concurrent version drift 由数据面并发写者造成；本文的视图落后由控制面链路中断造成，触发源不同。派发后节点失联、pending 被遗忘、重放顺序错、网关抖动、分区分歧、协调者重启六类在其故障表中没有对应项，因为其 episode 把工具调用视为必然送达。

本文的故障打点在 `commit_policy` 与 `rollback_policy` 两个 `mutates_state=True` 工具外侧的 dispatch → execute → observe 环上。该环随 runtime 一并自建。

已完成的执行层组件见 `code/`：`disruption_env.py` 提供真实地形节点、Gilbert-Elliott 信道、能量模型以及分区、flapping、重放与重启机制；`operations.py` 实现生命周期状态机与故障记账；`test_failure_model.py` 对 11 类故障做确定性验证，当前 11/11 通过；`agent_react.py` 是可切换恢复语义的调度器骨架；`wirelessops_adapter.py` 在公开任务契约上驱动执行层。

### 初步结果

在 120 个公开任务上按 2×2 消融两个 agent 侧机制——重试是否复用同一写入身份，以及验证是否限定在本次写入上——并对远端做三种配置。每千操作周期计数，horizon 为 64，详见 `docs/s5-benchmark/s6-11-execution-layer-results.md`。

| 远端 | naive | stable_key_only | verified_wrapper | lifecycle |
|---|---|---|---|---|
| 幂等 sink | 280.7 / 8.1 | 0.0 / 8.1 | 132.4 / 73.2 | 0.0 / 4.3 |
| 非幂等 sink | 280.7 / 8.1 | 280.7 / 8.1 | 132.4 / 73.2 | 140.8 / 4.3 |
| 非幂等且强制 epoch | 0.0 / 6.8 | 0.0 / 6.8 | 0.0 / 66.4 | 0.0 / 5.3 |

格式为重复 / 零效果。三条结论。幂等键在没有配合的远端时价值为零：`stable_key_only` 从 0 重复变成与 `naive` 逐位相同的 280.7，远端去重计数从 2156 掉到 0，收益全部来自远端对键的配合。epoch 强制让所有策略的重复归零，包括每次都用新身份的 `naive`，重复这一侧的修复位置在远端而不在 agent。重复归零后唯一剩下的差异是冲突消解，`verified_wrapper` 的非限定谓词把零效果率推到不做验证的 9.8 倍，而该缺陷在 horizon 为 1 时不可见（四个策略的零效果均为 0.0）。cycle 限定的验证在三种远端配置下零效果都最低，其优势不依赖远端配合。

### Related work

**最危险的邻居。** INFOCOM 2026 的 "Rollback Is Not Undo: Path-Dependent Failures in LLM-Arbitrated Network Control"（Weici Pan, Zhenhua Liu，DOI `10.1109/INFOCOM59046.2026.11571400`，DBLP `conf/infocom/PanL26`）已在同类会议与同类问题空间证明，LLM 仲裁的网络控制回路中回滚无法恢复行为，且恢复效果路径相关；该文提出 `recovery gap` 指标，故障模式包含 observation corruption、delay-reordering 与 agent dropout。该文为闭源，`open_access` 字段为 `CLOSED`，无公开 artifact。它未覆盖的是灾害与应急场景、真实轨迹驱动、实体生命周期与公开 artifact，本文需要引用它并显式对比。

**同组先前工作。** WirelessOpsAgent 论文（Zijian Lu, Yiping Zuo, Hao Xu, Weicong Chen, Xin He, Jiajia Guo, Shi Jin，arXiv `2608.08277`，2026-08-08，CC BY 4.0）发布 WirelessOpsBench。论文标题把研究层次定为 **Action Assurance**：判据是动作在下发前是否被正确授权。其表述为 *"repairs recoverable support failures before execution"*，问题被限定在可修复范围内；本文场景中 88.5% 的点位永久不可达、断电可持续数周，大量失败不可修复。该文中心是分发前的 repair，本文中心是分发后任务在实体变动下的存续，因此只作引用与边界参照。

公开 artifact 已逐字核验（本地 SHA-256 `df832540beae8cdfe776ea0ffbe294be1355421c1279e69479e0b0655428940d`，与 README 相符）。三族任务为 WCHW（教科书无线计算）、WCNS（5G 切片，含射线追踪 CQI）、WCMSA（移动性保障，含 Kalman 预测加射线追踪 CQI）。开发集 300 base、2400 case、180 repair；完整冻结集 900 base、6300 孪生 case、540 归因与修复记录，final 分片扣在尚未上线的评测服务器后。artifact 只含数据，不含 runner、scoring 谓词与 fault schedule；同一 base 的八个 case 的 `public_task` 逐字节相同，仅 `case_id` 不同，故障由评测端运行时注入。公布的工具面为 `get_primary_evidence`、`get_secondary_evidence`、`get_entity`、`get_schema`、`stage_policy`、`validate_policy`、`commit_policy`、`post_check`、`rollback_policy`，其中三者标注 `mutates_state: True`，`commit_policy` 已带 `expected_version` 乐观并发，预算为 `max_steps` 24、`max_tool_calls` 12、`wall_time_ms` 60000。

**已被占据的机制，不可声称。** 下表列出机制与其原始出处。

| 机制 | 出处 |
|---|---|
| idempotency、verify-before-retry、后置条件验证 | Mansoor, Phadke, Rana, arXiv `2608.02645`（2026-07-31），已对 LLM agent 逐字发表 |
| effect exactly-once 与 consume-once | Khan, arXiv `2608.03836`，含 TLA+ 740 万状态穷举、TLAPS 证明与 39 格故障矩阵，并实测出 LangGraph 1.2.9 在 SIGKILL 后重执行、CrewAI 重复副作用 |
| outcome-unknown 与防盲目重放 | Zhang, arXiv `2606.03895` "Agent libOS"，提出 prepare-dispatch-settle protocol |
| authority 与恢复语义绑定 | Xu et al., arXiv `2608.01710` "CapLease"，semantic replay 加 Issue–Prepare–Commit |
| 只读与改状态工具分类 | Chen, Tang, Yang, Lv, arXiv `2603.29656` "6GAgentGym"，42 个 effect-typed 工具 |
| retry budget、stale context、恢复预算 | Babu, Agrawal, arXiv `2606.01416` "Self-Healing Agentic Orchestrators"（2026-05-31） |
| 公平排队 | Demers, Keshav, Shenker, ACM SIGCOMM 1989, DOI `10.1145/75247.75248` |
| lease 与 heartbeat | Gray, Cheriton, ACM SOSP 1989, DOI `10.1145/74850.74870` |
| LLM agent serving 中的队头阻塞 | Luo et al., *Autellix*, arXiv `2502.13965`（2025-02-19） |
| 验证者永不失败的隐含假设 | Gou et al., *CRITIC*, arXiv `2305.11738`（ICLR 2024） |

三句不能写。"我们是第一个把 X 用于 LLM agent"（X 取 idempotency、verify-before-retry、retry budget、checkpointing、staleness guard、fair scheduling 中任一）可由上表直接反驳。"没有 benchmark 注入 tool 失败"同样可反驳。"没有工作注入网络故障"应改为 *"we are not aware of a benchmark that overlays a communication-channel fault model onto agent tool execution"*。

### 尚未覆盖的部分

| 空白 | 依据 |
|---|---|
| 分发后的执行语义 | WirelessOpsBench 的 7 类条件全部刻画证据账本的可信度，无一描述分发后的传输语义 |
| 实体生命周期作为一等对象 | 六个 benchmark 全文检索 agent 通道相关构造零命中，网络一律是控制对象 |
| 结果不可知作为一等故障类 | 六者的故障全为注入、合成或不存在，且注入类的发生都可观测 |
| 不可修复失败 | WirelessOpsAgent 自述限定 recoverable support failures；本文有 88.5% 永久不可达与数周断电 |
| verifier 自身不可用 | CRITIC 与 `2608.02645` 均假定 verifier 会响应；分区下验证本身也会超时且结果不可知 |
| 能量与供电维度 | 六个 benchmark 全部缺失 |
| 地形与传播维度 | 六个中只有 WirelessBench 涉及，且仅是 agent 可调用的 CQI 工具 |

## 四、仓库与运行

```
agentic communication/
├── README.md
├── code/          18 个可运行脚本
├── docs/          24 份支撑材料，s1-input 至 s6-model 六个目录
├── results/       仿真输出
├── data/          666 MB，未纳入版本控制
├── libs/          71 MB 加 simlibs，未纳入版本控制
└── other_repo/    WirelessOpsBench 公开 artifact，未纳入版本控制
```

```bash
export PYTHONPATH="$PWD/libs/pylibs:$PWD/libs/simlibs"

# 物理与几何
python3 code/mountain_lora_link.py        # 单点链路预算
python3 code/coverage_map.py              # 区域覆盖图，约 2 min
python3 code/los_vs_itm.py                # 几何视线判定与 ITM 交叉验证
python3 code/dem_to_mitsuba.py --render   # SRTM 转 Mitsuba 地形网格并渲染

# 执行层
python3 code/test_failure_model.py        # 11 类故障确定性验证，11/11
python3 code/wirelessops_adapter.py --limit 120 --ticks 1200 --rounds 1,2,4,8,16,32,64
```

`wirelessops_adapter.py` 在 WirelessOpsBench 的公开任务契约上驱动执行层，artifact 路径可用环境变量 `WIRELESSOPS_ARTIFACT` 覆盖。

仓库之外另有两处。`../ns3/` 为 ns-3.48 加 FLoRa（3.2 GB），构建后 `./ns3 run` 使用；`/home/orion/Communications/recon/` 存放文献侦察的原始抽取（全文、DOI 核验、抽取脚本）。

未纳入版本控制的文件及获取方式：`data/` 含 SRTM 高程瓦片与下载的真实轨迹，SRTM 的下载路径见 `code/mountain_lora_link.py` 头部注释，轨迹数据集见上表 Zenodo DOI；`libs/` 为本地 pip 依赖，`pylibs` 可用 `pip install numpy itmlogic` 重建，`simlibs` 用 `pip install mitsuba`；`docs/s1-input/week2-deck.md` 由课题组汇报 PPT 提取，与 `*.pptx` 一并留在仓库之外。
