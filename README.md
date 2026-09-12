# Agent Runtime for Maintaining Task Execution over Churning Emergency-Communication Entities

**状态**：调研与设计阶段（pre-paper）｜**更新**：2026-09-12
**性质**：通信论文（JSAC / TCOM / TWC / TMC / INFOCOM 一类）

---

## 0. 一句话

> **现有应急通信研究，是在给定的网络角色与通信基础设施之间做「组合」与「恢复」。
> 我们的 agent runtime 位于这些通信实体之上，负责在它们动态上线 / 掉线 / 退化 / 恢复时，维持任务执行。**

场景：灾前山区滑坡 / 泥石流监测——供电受限、链路频繁中断。
底座：通感算一体化（LoRa / NB-IoT / CPE / UAV / HAPS / 卫星 / 微波 多实体）。

---

## 1. 定位

### 1.1 分层

| | 现有应急通信 | **本文** |
|---|---|---|
| **通信实体** | 给定的选项池，在其间组合与恢复 | 动态集合：上线 / 掉线 / 退化 / 恢复 |
| **研究对象** | 组合策略、切换时机、恢复路径 | 任务执行本身在集合变动下的存续 |
| **agent 角色** | 选择器 | 运行时 |

### 1.2 证据：实体确实在成片、长时间地掉

**政策**

- **工信部联信管〔2024〕256号**（14 部门，2024-12-31）明确点名**断路、断电、断网**；把**北斗短报文与天通**放在基层兜底层；要求设备**适应严寒、密林**；目标年 2027。
- ⚠️ **十五五方案（自然资办函〔2026〕1198号）不含任何传输连续性 / 功耗 / 覆盖要求** ⇒ 通信侧只能引 256 号文。

**灾害中的实体退服记录（第二周汇报第 30–34 页案例）**

| 事件 | 实体损失 |
|---|---|
| 2026 西藏吉隆口岸泥石流 | **5 个基站退服**；投入卫星电话 36 部、便携卫星设备 10 套、发电油机 18 台 |
| 2024 四川康定姑咱泥石流 | **22 km 光缆受损 + 7 个基站退服**；投入 1 架大型无人机基站、6 辆应急通信车、9 台高通量卫星便携基站 |
| 2024 日本奥能登土砂灾害 | 一度 **88 个基站中断**；用移动基站车、可搬型基站恢复 |
| 2023 新西兰 Gabrielle | 滑坡破坏主干光纤；**峰值约 20% 基站离线**，**Gisborne 一度 90% 基站连续两天离线**；卫星 + 微波临时回传，容量低于原光纤 |

**物理约束（本项目实测）**

- 西藏波密 / 易贡真实 SRTM 地形（海拔 2025–6690 m）：**单网关地形死区 27.7%**（SF12 也连不通）。
- **决定连通性的是遮挡，不是距离**：8.4 km / 1169 m 遮挡连不通；12.6 km / 1102 m 遮挡反而能通。
- **SF 7→12 只多 14 dB 灵敏度，而地形遮挡是 30–50 dB 量级** ⇒ 链路自适应救不了被挡住的节点。
- 真实 LoRa 轨迹拟合（ChirpBox，20,913 快照 / 420 链路）：丢失率 7.44%，**平均中断突发 3.30 h**，i.i.d. 预测只有 1.08 h（**3.1×**）。
- −20 °C 下 LiFePO4 容量约 50%、**低于 +5 °C 无法充电** ⇒ 高海拔站点**季节性长时段静默**。

**空白**

- **中国地灾监测网络的实测可靠性数据基本不存在**：到报率 / 在线率 / 掉线次数 / 断链时长全无数值，
  只有合同条款（广东验收 ≥70%、昆明 ≥95%、河南 ≥95%）。
  ⇒ 本研究给的是 **estimate，不是 measurement**。

---

## 2. 通信实体分类（依据第二周汇报 PPT 及其引文）

### 2.1 灾损断点 → 恢复手段

**来源：PPT 第 36 页。** 其依据为 **[5] SAGIN 灾害管理综述**（IEEE TNSM 22(5):4021–4049, 2025）与
**[6] 灾害区域网络综述**（IEEE Access 13:91129–91160, 2025）。

| 灾损断点 | 恢复手段 |
|---|---|
| Sensor 接入困难 | LoRa / NB-IoT |
| 蜂窝弱覆盖 | CPE / UAV Relay / UAV-BS |
| 局部基站退服 | 便携站 / 应急车 / UAV-BS |
| 光缆 Backhaul 中断 | 微波 / HAPS / 卫星 |
| 大范围地面网络失效 | HAPS / 卫星 / NTN |
| 电源失效 | 油机 / 移动电源 |
| 线路物理损坏 | 光缆抢修 / UAV 辅助布缆 |

### 2.2 UAV 通信角色

**来源：PPT 第 16 页。** 依据 **[20] OWAID et al., ICEEE 2024**（UAV 辅助通信综述）与
**[21] NICT**、**[22] ZTE** 工程方案。

- 角色：`Relay` / `Base Station` / `Airborne UE`
- 架构：`Infrastructure` / `Ad-hoc` / `Hybrid`
- 四类工程组网：UAV Relay ｜ UAV 临时基站 ｜ UAV+CPE ｜ UAV Mesh

### 2.3 低功耗接入 + 回传组合

**来源：PPT 第 14 页。** 依据 **[14] JOUHARI et al., IEEE COMST 25(3):1841–1876, 2023**（LoRaWAN 综述）
与 **[15] 工信部 2017 年第 27 号公告**（NB-IoT 频率使用要求）。

LoRa + 4G/卫星 ｜ NB-IoT + 运营商核心网 ｜ LoRa + NB-IoT ｜ LoRa Mesh + 卫星

### 2.4 这三张表的用途

它们定义**通信实体集合**。每个实体有角色与基础设施类型，并投影成 agent 可调用的 capability。

**本文不研究"该用哪一类实体"（2.1–2.3 已回答），研究"当集合随时间变动时，任务如何继续"。**

---

## 3. 现状盘点

### 3.1 Dataset

| 数据 | 内容 | 许可 | 用途 |
|---|---|---|---|
| **SRTM1** | 30 m 全球高程 | 公开 | 地形与链路可达性（已用） |
| **ChirpBox**（Zenodo 5527877） | 21 节点、4.5 个月、逐链路 RSSI/SNR + 天气 | CC-BY-4.0 | 断链的时间相关结构（已用） |
| **Strasbourg**（Zenodo 20390366） | **5 年** LoRa 抓包，25.5 GB | CC-BY-4.0 | 跨年泛化检验 |
| **LoED**（Zenodo 4048255） | 9 网关、~1130 万条报文、含 `crc_status` | CC-BY-4.0 | 丢包结构 |
| **LoRa on Ice**（Zenodo 13693107） | 逐包收发 + GPS/距离/RSSI/SNR，含真实中断弧线 | CC-BY-4.0 | 单链路验证 |
| **LR-FHSS 电流实测**（Zenodo 13838241） | 端设备实测电流 | CC-BY-4.0 | 能耗模型校准 |
| **IODA** | 5 分钟粒度断网/恢复轨迹，2013→今，逐区域/逐 ASN | GT copyright | 真实 outage 生命周期 |
| **FEMA TEMPO** | 县粒度日度基站退服，含 damage/power/transport 归因 | 无明确许可 | 事件时间线校准 |

**关键空白**：**不存在山区 WSN 链路轨迹数据集**（ChirpBox 是上海城区、LoED 是城市、LoRa on Ice 是南极海冰）。
⇒ 空间维故障由**真实地形 + 标准传播模型**合成；时间维借用真实轨迹的**统计结构**。

### 3.2 Baseline

**第一层 · 通信侧（核心对照）** —— 每条附原始出处

| baseline | 原始出处 | 它假定什么 |
|---|---|---|
| **ADR / 链路自适应** | LoRaWAN 自适应速率控制：Reynders, Meert, Pollin, *Power and spreading factor control in low-power wide area networks*, **IEEE ICC 2017**, DOI `10.1109/icc.2017.7996380`；协议综述 Haxhibeqiri et al., *A Survey of LoRaWAN for IoT*, **Sensors 18:3995, 2018**, DOI `10.3390/s18113995` | 链路存在，只调 SF / 发射功率 |
| **DTN store-and-forward** | Fall, *A delay-tolerant network architecture for challenged internets*, **ACM SIGCOMM 2003**, DOI `10.1145/863956.863960` | 接触机会到来即可转发 |
| **Spray-and-Wait（DTN 代表策略）** | Spyropoulos, Psounis, Raghavendra, **ACM SIGCOMM Workshop 2005**, DOI `10.1145/1080139.1080143` | 靠副本数控制投递率 |
| **AoI 最优调度** | 原始：Kaul, Yates, Gruteser, *Real-time status: How often should one update?*, **IEEE INFOCOM 2012**, DOI `10.1109/infcom.2012.6195689`；综述：Yates, Sun, Brown et al., *Age of Information: An Introduction and Survey*, **IEEE JSAC 39:1183–1210, 2021**, DOI `10.1109/jsac.2021.3065072` | 控制信道可靠，命令按时下达 |
| **Whittle 指数调度** | Hsu, *Age of Information: Whittle Index for Scheduling Stochastic Arrivals*, **IEEE ISIT 2018**, DOI `10.1109/isit.2018.8437712` | 可观测全部信道状态 |
| **Max-weight / 吞吐最优** | Tassiulas, Ephremides, *Stability properties of constrained queueing systems and scheduling policies for maximum throughput*, **IEEE TAC 37:1936–1948, 1992**, DOI `10.1109/9.182479` | 队列状态可观测、控制可靠 |
| **多连接链路选择** | Khan, Jacob, *Link Adaptation for Multi-connectivity Enabled 5G URLLC*, **IEEE COMSNETS 2021**, DOI `10.1109/comsnets51098.2021.9352811` | 各链路状态可及时获得 |
| **单链路 / 静态选择** | 退化参照（无单一出处，作为下界） | 无多链路 |
| **Oracle** | 无出处；已知未来链路状态的**上界** | 全知 |

**第二层 · Agent 侧（对照）**

| baseline | 原始出处 |
|---|---|
| ReAct | Yao et al., **ICLR 2023**, arXiv `2210.03629`（⚠️ 不是 2201.11903，那是 CoT） |
| blind retry / 指数退避 | 工程惯例（AWS Builders' Library、Google SRE Book） |
| verified wrapper | Mansoor, Phadke, Rana, arXiv `2608.02645`（2026-07-31） |
| 默认工具超时语义 | MCP 规范 2026-07-28 Cancellation 章 |

### 3.3 Benchmark

#### 逐条核验：六个现有 benchmark 都不适用

**方法**：读全部六篇论文的 arXiv HTML 全文（非摘要），并检查仓库。详见 `docs/s5-benchmark/s6-9-benchmark-comparison.md`。

| benchmark | 故障模型 | 网络是**对象**还是**介质** | 载体 | 能量/功率 | 地形/传播 |
|---|---|---|---|---|---|
| **WirelessOptBench**（2608.08277） | **注入**的遥测故障（5 域 × 600 episode） | **对象**（动作授权） | 无；闭式 SINR + 继承的射线追踪 CQI | **无** | 间接 |
| **NetConfArena**（2608.23179） | **不注入**；只有 agent 自己的配置错误 | **对象**（配置） | **GNS3 + 厂商路由器镜像**（许可问题） | **无** | **无** |
| **NetArena**（2506.03231） | 每次查询**合成** | **对象**（规划/修复/策略） | Mininet + K8s + Docker | **无** | **无** |
| **NIKA**（2512.16381） | 经 **TC / stress-ng / 脚本注入**；54 问题 / 640 事件 | **对象**（检测→定位→根因） | Kathará 容器 | **无** | **无** |
| **NetOpsBench**（无论文） | 注入 **`tc` 常量**（`loss_pct=30`、`latency_ms=100`）；12 类 | **对象**（监测/诊断） | Containerlab + SONiC-VS；**仅 Linux，重** | **无** | **无** |
| **WirelessBench**（2603.00501） | **无**故障；确定性/专家解 | **对象**（静态解题） | 无；数据集 + OSM 射线追踪**工具** | **无** | 部分（2D 几何 + 射线追踪） |

#### 两条可直接引用的自述

> **NetConfArena**：容错是**未来工作** —— *"we plan to add … tasks that target fault-tolerant configuration scenarios."*
> 其指标 *"target the functional correctness of the final network behavior rather than network performance such as latency, congestion, or transient routing dynamics."*

> **NIKA**：**不支持评估缓解动作** —— *"NIKA currently focuses on diagnosis tasks (detection, localization, RCA) but **does not yet support evaluating mitigation actions**."*

⇒ 这两句说明：现有 benchmark **自己承认**容错与缓解动作不在覆盖面内。

#### 三条关键事实（逐条有出处）

**① agent 自己的操作通道会退化吗？——六个全部：不会。**
六篇全文检索 agent 通道相关构造（agent 自身流量/时延/连接、带外控制面、边缘部署 agent、"agent 之间的连通性"）：**零命中**。
**网络始终是控制的「对象」，从不是承载 agent 遥测的「介质」。**

**② 故障是从真实地形/供电导出的吗？——六个全部：不是。**
全部为注入、合成或不存在。最强的也只是**词汇**层面接地（WirelessOptBench 的分类引用 TeleLogs/AIOps2025/RCA100），
但实现是 benchmark 自定义的——**该论文自己承认这一点**。NetOpsBench 是**手设的 `tc` 常数**。
**没有任何一个从传播模型、高程数据、RF 实测轨迹或供电状态导出故障。**
⚠️ 陷阱：NetOpsBench 的 "trace dataset" 是 **319 条 agent 轨迹**，不是链路轨迹。

**③ 任务是长时监测 mission 吗？——不是。**
最接近的 NIKA 与 NetOpsBench **都是单事件式**：一个事件 → 检测/定位/根因 → 结束。
NIKA 的 7–15 小时是**整个测试集的累计墙钟时间**（150 个事件），不是单个 mission；
NetOpsBench 的 "efficiency" 数的是 **tool call 数与 token 数**，不是经过时间。
**两者都不惩罚"中途漏掉一个事件"、不惩罚信道随时间衰减、不要求跨数小时维持态势。**

#### 结论

> **六个 benchmark 里，能量/功率一条**全部没有**；地形/传播只有 WirelessBench 沾到一点，而且只是 agent 可调用的 CQI 工具。**
>
> **这不是"覆盖不足"，是结构上不属于这一类**——它们一致地把网络固定为**控制的对象**，
> 而不是**agent 自身所处的介质**。

⇒ 需要自建。而自建的部分是**结构性差异**，不是参数差异。

#### 已有的自建部分（`code/`）

| 模块 | 内容 |
|---|---|
| `disruption_env.py` | 环境：真实地形节点、Gilbert-Elliott 信道、能量模型、分区 / flapping / 重放 / 重启 |
| `operations.py` | 生命周期状态机 + 故障记账 |
| `test_failure_model.py` | **11 类故障确定性验证（11/11 PASS）** |
| `agent_react.py` | 调度器骨架，恢复语义可切换 |

### 3.4 Related work

#### 最危险的邻居

**INFOCOM 2026 — "Rollback Is Not Undo: Path-Dependent Failures in LLM-Arbitrated Network Control"**
Weici Pan, Zhenhua Liu. DOI `10.1109/INFOCOM59046.2026.11571400`｜DBLP `conf/infocom/PanL26`｜**闭源无 artifact**（已核验 `open_access: CLOSED`）

它在**同类会议、同类问题空间**已证明：LLM 仲裁的网络控制回路中**回滚恢复不了行为、且路径相关**；
提出 `recovery gap` 指标；故障模式含 observation corruption / delay-reordering / agent dropout。
**它没占掉的**：灾害 / 应急场景、真实轨迹驱动、**实体生命周期**、公开 artifact。
⇒ **必须引，必须显式对比。**

#### 同组先前工作（对象不同）

**WirelessOpsAgent / WirelessOptBench** — Zijian Lu, Yiping Zuo, Hao Xu, Weicong Chen, Xin He,
Jiajia Guo, Shi Jin. arXiv `2608.08277`（2026-08-08）

它自己的表述：*"**repairs recoverable support failures** before execution"*。
⇒ 它把问题**限定在可修复**；本文场景中 **27.7% 点位永久不可达、断电可达数周**，**大量失败不可修复**。
中心也不同：它做 **repair**，本文做**任务执行在实体变动下的存续**。⇒ 只作 related work 引用与边界参照。

#### 已占掉的机制（**不可声称**）

| 机制 | 原始出处 |
|---|---|
| idempotency + verify-before-retry + 后置条件验证 | Mansoor, Phadke, Rana, arXiv `2608.02645`（2026-07-31）——**已对 LLM agent 逐字发表** |
| effect exactly-once / consume-once | Khan, arXiv `2608.03836`（TLA+ 穷举 740 万状态 + TLAPS 证明 + 39 格故障矩阵；实测 LangGraph 1.2.9 SIGKILL 后重执行、CrewAI 重复副作用） |
| outcome-unknown + 防盲目重放 | Zhang, arXiv `2606.03895` "Agent libOS"（*prepare-dispatch-settle protocol*） |
| authority 与恢复语义绑定 | Xu et al., arXiv `2608.01710` "CapLease"（semantic replay + Issue–Prepare–Commit） |
| 只读 vs 改状态工具分类 | Chen, Tang, Yang, Lv, arXiv `2603.29656` **6GAgentGym**（42 个 effect-typed 工具） |
| retry budget / stale context / 恢复预算 | Babu, Agrawal, arXiv `2606.01416` "Self-Healing Agentic Orchestrators"（2026-05-31） |
| 公平排队（fair replay 的理论祖先） | Demers, Keshav, Shenker, *Analysis and simulation of a fair queueing algorithm*, **ACM SIGCOMM 1989**, DOI `10.1145/75247.75248` |
| lease / heartbeat | Gray, Cheriton, *Leases: an efficient fault-tolerant mechanism for distributed file cache consistency*, **ACM SOSP 1989**, DOI `10.1145/74850.74870` |
| LLM agent serving 中的队头阻塞 | Luo et al., *Autellix*, arXiv `2502.13965`（2025-02-19） |
| 验证者永不失败的隐含假设 | Gou et al., *CRITIC*, arXiv `2305.11738`（ICLR 2024） |

**⛔ 三句绝不能写**
1. "我们是第一个把 X 用于 LLM agent"（X ∈ idempotency / verify-before-retry / retry budget / checkpointing / staleness guard / fair scheduling）
2. "没有 benchmark 注入 tool 失败" —— 假的，一段话可驳
3. "没有工作注入网络故障" → 改为 *"we are not aware of a benchmark that overlays a communication-channel fault model onto agent tool execution"*

### 3.5 仍然空着的（每条附依据）

| # | 空白 | 依据 |
|---|---|---|
| **1** | **实体生命周期作为一等对象** | §3.3：六个 benchmark 全文检索，**agent 通道相关构造零命中**，网络一律是控制对象而非 agent 所处介质 |
| **2** | **"结果不可知"作为一等故障类** | §3.3：六者的故障全为**注入/合成/无**，且注入类的发生都是**可观测**的；未见把"动作执行了但看不出来"作为注入类 |
| **3** | **不可修复失败** | §3.4：WirelessOpsAgent 自述限定 *"recoverable support failures"*；本文有 27.7% 永久不可达 + 断电数周（§1.2 实测） |
| **4** | **verifier 自身不可用** | §3.4：CRITIC（`2305.11738`）与 `2608.02645` 均假定 verifier 会响应；分区下验证本身也超时且结果不可知 |
| **5** | **能量 / 供电维度** | §3.3：六个 benchmark **全部无** energy/power 建模 |
| **6** | **地形 / 传播维度** | §3.3：六个中只有 WirelessBench 沾到，且仅作为 agent 可调用的 CQI **工具**，非其流量所穿越的信道 |

## 4. 工作区

```
Communications/
├── README.md
├── docs/          FRAMING.md · PROGRESS.md · INDEX.md · PRIOR-WORK-*.md · s1–s5
├── code/          13 个可运行脚本
├── data/          SRTM、下载数据
├── results/       仿真输出
└── libs/pylibs/
```

```bash
export PYTHONPATH="$PWD/libs/pylibs"
python3 code/mountain_lora_link.py     # 单点链路预算
python3 code/coverage_map.py           # 区域覆盖图（约 30 s）
python3 code/test_failure_model.py     # 11 类故障验证
```

**仓库不含**（见 `.gitignore`）：

| 目录 / 文件 | 原因 | 如何获得 |
|---|---|---|
| `data/` (666 MB) | SRTM 高程瓦片 + 下载的真实轨迹 | SRTM 见 `code/mountain_lora_link.py` 头部注释的 S3 路径；轨迹数据集见 README §3.1 的 Zenodo DOI |
| `libs/` (71 MB) | 本地 pip 依赖 | `pip install numpy itmlogic` |
| `docs/s1-input/week2-deck.md` | 由课题组汇报 PPT 提取，属第三方资料 | 保存在仓库之外 |
| `*.pptx` | 同上 | — |
