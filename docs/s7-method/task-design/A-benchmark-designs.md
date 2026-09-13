# A · 可沿用的既有 task / benchmark 设计提取

> **性质**：只读材料挖掘的产物。本文件只做提取与索引，**不评价本项目方法好坏**，不做任何推测性补全。
> **唯一来源**：任务书列出的 10 个文件（见 §0.1）。凡材料未写明的字段一律写「材料未给出」。
> **纪律**：每条结论后跟文件名与行号。行号对应当前文件版本。
> **未运行任何实验**，未触碰 `code/`。

---

## 0. 读之前必须知道的三件事

### 0.1 本文件的来源文件

| 缩写 | 文件 |
|---|---|
| `R` | `docs/s5-benchmark/README.md` |
| `C9` | `docs/s5-benchmark/s6-9-benchmark-comparison.md` |
| `N7` | `docs/s5-benchmark/s6-7-experimental-norms.md` |
| `B6` | `docs/s5-benchmark/s6-6-same-domain-baselines.md` |
| `A10` | `docs/s5-benchmark/s6-10-wirelessopsbench-artifact-audit.md` |
| `E11` | `docs/s5-benchmark/s6-11-execution-layer-results.md` |
| `F1` | `docs/s5-benchmark/s5-1-failure-model.md` |
| `P2` | `docs/s5-benchmark/s6-2-physical-model-results.md` |
| `D5` | `docs/s5-benchmark/s6-5-data-provenance.md` |
| `S3` | `docs/s3-novelty/agent-assumption-audit.md` |

### 0.2 这些材料的时效状态（直接影响哪些数字能用）

`R:17-26` 给出逐文件状态表，必须随结论一起读：

- **仍在用**：`N7`（`R:19`）
- **事实记录有效**：`A10`（`R:20`）
- **参考价值**：`B6`、`D5`（`R:21-22`）
- **已被取代**：`C9`（`R:23`）、`F1`（`R:24`）、`E11`（`R:25`）
- **数字已失效，勿引用**：`P2`（`R:26-38`）。失效原因是两处错误：自由空间损耗常数写成 `-27.55`（正确为 `+32.44`，差 60 dB），使覆盖网格可达率由 72.3% 变为 11.5%；ChirpBox 的 `node_link_matrix` 被当邻接表误读，正确可用率 68.75%、平均中断突发 6.38 h（`R:32-34`）。`P2` 的**相对结论方向**（能量模型影响大于信道模型；toy 假设低估问题规模）「可能仍然成立」，但倍数必须重算后才能引用（`R:36`）。

⇒ 本文件引用 `P2` 的任何数字时都标注了「已失效，勿引用」。`F1` 使用旧的 11 状态词汇，读时须换到现行三维语义（`R:38`、`R:24`）。

### 0.3 这批材料里不存在「通信领域的任务套件 benchmark」这一前提

`R:7-11` 的结论：对照 9 篇 JSAC / TCOM / TWC / TMC / TVT 同域论文，**用外部 benchmark 或公开数据集作评测基底的仅 2/9**，且无一采用「公共 benchmark 加统一协议」形式；**运行第三方公开实现作对照的 0/9**。另：候选的六个 benchmark 全部是「港科大或园区尺度的 5G 切片与配置类任务」，与山区监测在物理层、能量维度、时间尺度上都不重合。
另一侧：2025 年一篇 COMST 综述统计 130 篇同类论文，详审的 27 篇中绝大多数不共享源码，78.46% 未给可用的数据来源信息（`R:9`）。

⇒ 因此下节清单里的「可沿用部分」，**来源重心是 LLM-agent-in-networking 那一支 benchmark 与同域 baseline 仓库**，而不是经典 ComSoc 论文。

---

## 1. 可沿用的 task 设计清单

字段口径：**出处**按材料所给；**任务是什么 / 怎么生成的 / 怎么打分 / 靠什么避免 toy / 我们能沿用哪一部分**，凡材料未给出即写「材料未给出」。

### 1.1 六篇 agent「network」benchmark（来源：`C9`，逐条核验）

#### (1) WirelessOptBench / WirelessOpsAgent — arXiv:2608.08277

| 字段 | 内容 | 出处 |
|---|---|---|
| 出处 | arXiv:2608.08277；另有本地 artifact 审计与一页作者列表 | `C9:9`、`A10:12-13` |
| 任务是什么 | 「把无线任务转成**执行状态决策 episode**，带受控遥测故障与动作约束」。agent 读一份不可变观测账本，发出 `APPLY/HOLD/RETRY/ESCALATE/ABSTAIN`。三个任务族：WCNS（网络切片）、WCMSA（移动性服务保障）、WCHW（无线家庭作业/教材题） | `C9:11-12`、`A10:27-28`、`A10:40` |
| 怎么生成的 | 五类压力域 × 3 任务族 × 40 = **600 episode**；压力域为 schema/unit、freshness/order、availability-brownout、conflict/provenance、mixed。故障词汇借用 TeleLogs（AIOps2025）与 RCA100，但**压力本身由 benchmark 定义**：原文「the taxonomy and oracle are benchmark-defined rather than drawn from an unseen generator or independent deployment study」 | `C9:11` |
| 怎么打分 | 指标口径为**任务正确性（task correctness）+ 动作授权（action assurance）**；同域量化结果：Unsafe APPLY Rate 从 82.2% 降到 10.3% | `A10:90`、`S3:32` |
| 靠什么避免 toy | ① **契约层显式机器可判定**：状态机 `stage_<fam>` → `validate_evidence` → `commit_authorization` → `post_check` → `rollback`，里程碑 `evidence_checked` → `policy_committed` → `post_checked`，授权正确性可按 `legal_transitions` 强制；② **乐观并发 + 风险带**：`commit_policy` 要求 `stage_id` 与 `expected_version`；`risk_field` 为 `protected_*_impact`，`maximum_protected_impact` 为 28 或 40 等，超过即 `dangerous_proposal`；③ **预算硬约束**：`max_model_calls` 24、`max_steps` 24、`max_tokens` 32000、`max_tool_calls` 12、`wall_time_ms` 60000；④ **七类故障条件**成轴（时序不一致含 stale 与乱序、缺失必需证据、来源冲突、schema 漂移、实体错绑、并发版本漂移、假成功更新） | `A10:64-66`、`A10:70-80` |
| 我们能沿用哪一部分 | `A10:84` 明列「可继承」：**任务文本与参数、九工具契约与 `mutates_state` 标记、预算、合法迁移与里程碑、动作 schema 的乐观并发与风险带、七类故障作为对照故障轴**。工具面九项中只有 `commit_policy` 与 `rollback_policy` 两项 `mutates_state=True`（`A10:52-62`） | `A10:84` |
| 必须自建、不可声称 | **须自建**：证据账本内容、`ray_tracing` CQI 提供者、runtime、scoring 谓词（`A10:86`）。**不可声称**与论文所报数值可比——artifact 不含 baseline 分数、轨迹、token 数、成本与延迟（`A10:88`） | `A10:86-88` |
| 材料明确的分工定位 | 我们的接入点是**两个 `mutates_state=True` 工具外侧的 dispatch → execute → observe 环**；相邻关系为「WirelessOpsBench 的 Task correctness → Action assurance，本文接 Execution assurance」 | `A10:90-94` |

#### (2) NetConfArena — arXiv:2608.23179

| 字段 | 内容 | 出处 |
|---|---|---|
| 出处 | arXiv:2608.23179；代码 `liujona/NetConfArena`，Apache-2.0 | `C9:19-27`、`B6:23` |
| 任务是什么 | 纯**配置类**任务（企业/ISP 路由交换，RIP/OSPF/BGP/MPLS/VRF 式协议模板），「小拓扑上的受控配置场景」。agent 通过五个原语行动：`get_running_config`、`apply_config`、`execute_validation`、`wait`、`submit` | `C9:22-26` |
| 怎么生成的 | **96 模板 → 480 实例 → 3840 轨迹**（`B6:23`）。故障**不注入**：失败只作为 agent 自身的配置错误进入；原文说容错场景是未来工作（「we plan to add tasks that begin from legacy configurations conflicting with the intended objective, as well as tasks that target fault-tolerant configuration scenarios」） | `B6:23`、`C9:21` |
| 怎么打分 | 「hidden task-specific executable test cases」——**隐藏的、任务专属的可执行测试用例**；指标「target the functional correctness of the final network behavior rather than network performance such as latency, congestion, or transient routing dynamics」 | `C9:21` |
| 靠什么避免 toy | ① **模板 → 实例 → 轨迹的三级生成**，从 96 个模板扩到 480 实例、3840 轨迹；② **隐藏的、任务专属可执行测试用例**（不是 LLM judge）；③ 与 OneShot 对照（ReAct vs OneShot，含完整 prompt 与工具定义）。它自我定位为攻击「static command generation or … overly simplified settings」 | `B6:23`、`C9:21`、`N7:150` |
| 我们能沿用哪一部分 | `B6:67` 明列 **B-D1：NetConfArena 的 ReAct + OneShot harness**，Apache-2.0，搬运成本**低**，理由是「其工具分类 `get_current_config` 只读 / `apply_config` **副作用** / `execute_validation` 只读 **与我们的完全一致**」。另 `D5:53` 建议 prompt 优先沿用已发布的 harness（例如 NetConfArena 的 ReAct prompt）以减少调参质疑 | `B6:67`、`D5:53` |
| 成本与依赖 | 需**专有 Cisco 镜像**；baseline = qwen3-8B/32B 与 deepseek-v4-flash/pro 各开/关 thinking；经典配置综合工具被**显式排除**：「Our evaluation focuses on LLM agents, so traditional configuration synthesis tools are not included as baselines; they start from formal specifications rather than from natural-language intent.」 | `B6:23`、`N7:135` |

#### (3) NetArena — arXiv:2506.03231（ICLR 2026）

| 字段 | 内容 | 出处 |
|---|---|---|
| 出处 | arXiv:2506.03231，code `Froot-NetSys/NetArena`；ICLR 2026 poster 的 venue 主张「consistent with iclr.cc listing, not stated in the arXiv text」 | `C9:29-37` |
| 任务是什么 | 三个 app：数据中心容量规划（Google Mogul 式拓扑）、路由错配修复（Mininet）、微服务策略排障（Google microservices-demo on Kubernetes） | `C9:31-32` |
| 怎么生成的 | **每次评测轮内随机采样动态生成查询**（「dynamically generates queries via randomized sampling in each evaluation round」）；路由 app 是「诊断并修复动态故障（断链或非法转发规则）」 | `C9:31` |
| 怎么打分 | 材料未给出评分口径 | `C9:29-37` |
| 靠什么避免 toy | **动态按需生成查询**，其自身动机写的是「static design … contamination … high statistical variance」——即同时针对**静态设计、预训练污染、高统计方差**三个问题 | `N7:146`、`N7:150` |
| 我们能沿用哪一部分 | `B6:69` 明列 **B-D3：NetArena 的 prompt-based agent**，ICLR 2026，搬运成本中。另有可复用的**同领域环境**（`B6:88`） | `B6:24`、`B6:69`、`B6:88` |
| 实测对照 | prompt-based agent vs A2A 框架，「agent 平均只拿 13–38%」 | `B6:24` |

#### (4) NIKA — arXiv:2512.16381

| 字段 | 内容 | 出处 |
|---|---|---|
| 出处 | arXiv:2512.16381，code `sands-lab/nika`（1662 文件 / 1456 代码，58★） | `C9:39-47`、`B6:25` |
| 任务是什么 | **纯诊断**：detect → localize → RCA。agent 拿到 30+ MCP 工具（ping、traceroute、iperf、HTTP latency、端口计数、流/路由表、日志）。明确**不做缓解**：「NIKA currently focuses on diagnosis tasks (detection, localization, RCA) but does not yet support evaluating mitigation actions.」 | `C9:42` |
| 怎么生成的 | 注入式且词汇来自真实：**54 个 issues、640 incidents**；注入手段为 Linux TC（链路级）、stress-ng（软件争用）、自定义脚本（进程崩溃、错配）。场景：DC CLOS、campus 3-tier、ISP backbone meshed、SDN cloud POP fabric、P4 testbed；规模 S/M/L ≈ 11/27/101 节点 | `C9:41`、`C9:46` |
| 怎么打分 | 材料未给出评分谓词；`C9:92` 说明其运行时长为**聚合 wall clock**：全 150-incident 套件 7–15 h | `C9:46`、`C9:92` |
| 靠什么避免 toy | ① **注入手段是真实的系统工具**（TC / stress-ng / 进程崩溃），不是纯软件标志位；② **规模可扫**（11→101 节点，S/M/L）；③ **工具面最宽**（>30 MCP 工具），被 `N7:142` 称为新兴的**复用枢纽**，FaulT-Bench 直接建在它的数据集与工具接口上 | `C9:41`、`C9:46`、`N7:142`、`N7:269` |
| 我们能沿用哪一部分 | `B6:88`：NIKA「可直接对比的**同领域环境**」。`N7:271`：其工具面**已经开始标准化**，「这对我们是有利的（可以对齐）」 | `B6:88`、`N7:271` |
| 明确的局限 | 「it cannot faithfully reproduce issues that manifest only in high-speed networks, or that require specialized hardware」 | `C9:44` |

#### (5) NetOpsBench — 无同行评审论文，仅仓库

| 字段 | 内容 | 出处 |
|---|---|---|
| 出处 | `github.com/NetX-lab/NetOpsBench`，MIT，Python，30★，**No paper found; repo-only** | `C9:49-57`、`B6:26` |
| 任务是什么 | 运维监控/诊断：agent 检视「live Pingmesh, BGP, gNMI, syslog, and switch state」，被评的是**检测、故障类型、设备/接口定位** | `C9:52` |
| 怎么生成的 | 注入式且**显式为参数化常量**：12 个 canonical 类型分 5 类（link：`link_down`/`link_flapping`；routing：`blackhole_route`/`static_route_misconfig`/`bgp_neighbor_misconfig`/`route_policy_misconfig`；impairment：`mtu_mismatch`/`packet_loss`/`packet_corruption`/`high_latency`；system：`device_down`；ACL：`acl_misconfig`）。impairments 是 `tc` 式常数（`loss_pct=30`、`latency_ms=100`、`corruption_pct=20`），**不是从真实链路测得的**；支持自定义故障包 | `C9:51` |
| 怎么打分 | 「scored for detection, fault type, device/interface localization, **runtime, tool calls, token usage**」——质量与效率双轴 | `C9:52` |
| 靠什么避免 toy | ① **12 canonical 故障家族成分类法**，分 5 类，可扩展自定义故障包；② **规模可扩**：Fat-tree K=12（180 交换机、144 客户端）；③ **效率轴**（runtime / tool calls / token usage）与质量轴并列；④ 公开的 SONiC-VS 与 client 镜像在 Docker Hub，可复现 | `C9:51-53` |
| 我们能沿用哪一部分 | `B6:88`：可直接对比的**同领域环境**。`C9:97` 称它在六者中**最接近运维框架**。其 HF 轨迹数据集（319 条 agent 轨迹）**不是物理层轨迹** | `B6:88`、`C9:97`、`C9:57` |
| 运行时约束 | **Linux-only**：「NetOpsBench runtime execution requires Linux because Containerlab depends on Linux networking primitives. Windows and macOS hosts are not supported.」；K=12 时宿主 RAM/CPU 很重 | `C9:53` |

#### (6) WirelessBench / WirelessAgent++ — arXiv:2603.00501

| 字段 | 内容 | 出处 |
|---|---|---|
| 出处 | arXiv:2603.00501，code `jwentong/WirelessBench`，MIT，298 文件 / 119 代码 | `C9:59-67`、`B6:28` |
| 任务是什么 | **静态问题求解**：分类服务、预测 CQI、分配带宽。没有 live network、没有闭环对着网络环境；闭环是 MCTS 工作流优化器在数据集上跑 | `C9:62` |
| 怎么生成的 | 两组：**WCHW 1,392 道教材题**（`B6:28` 称 WirelessBench 共 3,392 题）；WCNS/WCMSA **由港科大 OSM 几何 + 射线追踪工具生成**，字段含 `TX power` 等 | `C9:63`、`B6:28` |
| 怎么打分 | 材料未给出评分口径；`D5`/`C9` 只说 ground truth 由确定性规则或专家解构造 | `C9:61` |
| 靠什么避免 toy | ① **ground truth 确定性**：「All ground truths are constructed from deterministic rules or expert solutions, ensuring reproducibility.」；唯一「噪声」是 LLM 输出随机性与数值精度；② **六者中唯一有物理信道建模**：site-specific 射线追踪引擎 + OSM 提取的真实建筑几何，覆盖港科大三个校园区域。但它是 **agent 可调用的 CQI 计算工具，不是 agent 流量所穿过的信道**，且是 2D 建筑轮廓加默认建筑高度，**不含地形/高程** | `C9:61`、`C9:65` |
| 我们能沿用哪一部分 | `B6:87`：**WirelessBench（3,392 题）**用于「证明我们的方法在**领域标准任务**上不退化」。`B6:68` 另列 **B-D2：WirelessAgent++ 工作流**，MIT，成本中（需把 operator 接到我们的环境） | `B6:87`、`B6:68` |
| 同族另一样本 | `/WirelessAgent`（arXiv:2505.01074，IEEE/CIC China Communications 2026）：baseline 为 prompt-based + rule-based 最优，环境为射线追踪 CQI + 网络切片场景。`B6:24` 标注其对照为「prompt-based agent vs A2A 框架」，其读数「agent 平均只拿 13–38%」 | `B6:27`、`B6:24` |

### 1.2 材料中出现的其他 benchmark（`N7` §4，信息量较少）

| 名称 | 出处 | 任务是什么 | 怎么生成 | 怎么打分 | 靠什么避免 toy | 我们能沿用哪一部分 |
|---|---|---|---|---|---|---|
| **NetConfEval** | ACM CoNEXT 2024（`N7:143`、`B6:35`） | 5 类配置任务（`B6:35`） | 材料未给出 | **不用 LLM judge**，把配置部署到**真实 FRRouting 守护进程**上验证（`N7:143`、`N7:277`） | 「把配置部署到真实 FRRouting 上验证」这一验证方式（`N7:277`）；有 reproducible `artifact/` 脚本（`B6:35`） | 验证方式：真守护进程 + 可复现 artifact 脚本；代码 `RedHatResearch/conext24-NetConfEval`，124 文件，42★，MIT（`B6:35`） |
| **TeleCom-Bench** | KDD 2026（`N7:144`） | 12 个评测集、22,678 样本（`N7:144`） | 材料未给出 | LLM-only baselines；发现 **Execution Wall**：知识理解准确率 ~90% 塌到端到端任务 ~30%（`N7:144`、`N7:261`） | 「Execution Wall」这一现象本身：把**知识理解**与**端到端执行**分成两个量级分开报（`N7:261`） | 该发现可直接引为「能力 ≠ 执行正确性」的支撑（`N7:261`、`N7:263`） |
| **6GAgentGym** | arXiv:2603.29656（`N7:147`） | 材料未给出 | 材料未给出 | 材料未给出 | **样本中 baseline 最丰富的一套**：8 个前沿 LLM **加** Threshold-Rule、**含 50 条手写规则的 MAPE-K 启发式**、DRL-Slicing；Experiment Model 按 NS-3 数据标定。**无 code link**（`N7:147`） | 启发式 baseline 的形态：**手写规则库的规模要写清（50 条）**，且与 DRL baseline 并列（`N7:147`） |
| **NetConfBench** | IETF NMRG draft `draft-cui-nmrg-llm-benchmark-01`（`N7:148`） | GNS3 模拟器 + **40 个任务**（`N7:148`） | 材料未给出 | **reasoning / command / testcase 三档分数**（`N7:148`） | 把评分拆成「推理—命令—测试用例」三级，最后一级是可执行测试用例（`N7:148`） | 三级评分口径；它被提为**标准化**答案（`N7:148`、`B6:128`） |
| **FaulT-Bench** | arXiv:2608.27021（`N7:136`） | 同一批 200 个 Kathará 模拟场景（`N7:136`） | 材料未给出 | 由 **LLM judge** 打分（`N7:136`） | ① **在被评测对象上做横向对照**：SADE、一个 ReAct agent、Claude Code 三种 scaffold 跑同一 200 场景；② 建在 NIKA 的数据集与工具接口上；③ 攻击的是「only on accurate tickets and always assume a fault is present」——即**工单一定准确、故障一定存在**这两个假设 | 评测方式：**同一任务集上跑多个 scaffold，让 scaffold 成为自变量**（`N7:136`、`N7:138`）；其攻击对象可作为我们论点的引文（`N7:150`） |
| **NetInjectBench** | arXiv:2607.10490（`N7:152`） | **130 场景的 prompt-injection benchmark**（`N7:152`） | 材料未给出 | 被评测对象是**防御而非模型**：naive execution 82.5% unsafe、prompt-only 25.6%、Self-Reminder 21.7%、Spotlighting 18.3%、two-pass LLM judge 10.0%、**static allowlisting 5.0% 但 0% usefulness**（`N7:152`） | **用「不安全率 + 有用性」两条轴同时报**——allowlisting 的 5.0% 是「以 usefulness 归零换来的」，单看一轴就会误判（`N7:152`） | 「双轴报告」这一做法本身（`N7:152`）；以及「baseline 可以是防御而不是模型」的定位（`N7:152`） |
| **α³-Bench** | arXiv:2601.03281（`S3:64`） | 材料未给出任务描述 | 材料未给出 | 材料未给出 | 材料未给出；`S3:64` 只把它列为「Gap 1 的最大风险项，必须补读」——需确认 packet loss 是作用在 **tool call** 上还是只影响推理上下文 | 材料未给出（**未读**，被列为阻塞项） |
| **Atomix** | arXiv:2602.14849（`S3:65`） | 材料未给出 | 材料未给出 | 材料未给出；`S3:65` 指明需读其 **"A.2 Fault Injection Details" 附录** | 材料未给出 | 材料未给出（**未读**） |
| **AgentChaos / AgentDisruptBench** | arXiv:2608.06790 与 HF `kavirubc/AgentDisruptBench`（`S3:66`） | 材料未给出 | 材料未给出 | 材料未给出 | 材料未给出 | 用途被写明：**用于构建「注入故障类的对照表」，该表是 Related Work 的关键产物**（`S3:66`） |

---

## 2. 实验规范清单（来源：`N7`，带数字）

`N7` 的方法学前提：每条论断都绑定到抓取并读过的 URL（论文 PDF/HTML、venue 政策页或讲稿），除非标 *[search snippet]*（`N7:3`）。原始抓取材料「已随工作区清理删除」，复核须按正文 URL 重新抓取（`N7:213-214`）。

### 2.1 种子数 / 重复次数 / 随机化

| 要求 | 具体数字 | 出处 |
|---|---|---|
| 蒙特卡洛平均的报法 | 「averaged over **100 independent channel realizations**」——**100 次**独立信道实现 | `N7:118` |
| 同一结构的另一实例 | 「The results are averaged over **3,000 Monte Carlo simulation trials**」——**3,000 次** | `N7:31`、`N7:118` |
| 曲线报法 | **median/percentile-vs-SNR 曲线，不是单次运行的数字** | `N7:118` |
| 本项目协议口径（`D5` 自定） | **不少于 10 个种子**，报均值与置信区间；**配对比较**（同一 episode 集跑所有方法）；**做显著性检验** | `D5:87` |
| API 模型的额外要求 | temperature=0 输出也非完全确定 ⇒ **必须报多种子 + 置信区间**，并把**模型版本与调用日期**写进论文 | `B6:254`、`B6:266` |
| 种子冻结 | 种子集**未冻结**（`D5:53`），协议要求**冻结并公开 episode 集**（`D5:53`、`D5:85`） | `D5:53`、`D5:85` |

### 2.2 基线数量与选择

| 要求 | 具体数字 | 出处 |
|---|---|---|
| 「至少一个**退化参照**与一个**上界或穷举搜索参照**」（如 without RIS、uniform power、random phase，或小规模下的穷举搜索） | **各 1 个**；「This is universal practice in the verified examples above」 | `N7:199` |
| 经验基线数量 | IRS-assisted OFDM（IEEE TWC）**3 个**（CPM / Random Phase / Without IRS）；ISAC 波形设计对照**3 个**（SAUPA / RSAPA / RSAUPA）；MEC offloading 学习式论文**3 个**（Full Local / Full Offload / DQN-based） | `N7:25`、`N7:31`、`N7:46` |
| 常见基线词汇表 | 凸优化族：water-filling（含 bounded/geometric）、SCA、WMMSE、SDR（+Gaussian randomization）、Lagrangian dual decomposition、FP/quadratic transform、AO、exhaustive search、CVX；学习族：DQN / DDPG / PPO / A3C / Q-learning / 监督式 DNN-LSTM；退化/启发式族：random phase、equal/uniform power allocation、without-RIS/without-IRS、full-local、full-offload、greedy、max-ratio、no-power-control；界：CRB 作为估计 MSE 下界、松弛/SDR 目标作为原问题的上界 | `N7:41-44` |
| 公平性四要件 | **同一组信道实现、同一 SNR 扫点、同一功率/带宽/复杂度预算、同一蒙特卡洛次数**；且**每个基线的自由参数要调**，不能冻结在所提方法取值上 | `N7:198` |
| 最常见的致命批评 | **稻草人基线**（strawman baseline） | `N7:198` |
| 基线的实现方式 | **自行重实现**，并写清「we implement [X] following the update rules in [ref, eq. (n)]」，让评审能核方程而不是猜库 | `N7:197` |
| 基线被排除时要说明 | 例：NetConfArena「traditional configuration synthesis tools are not included as baselines; they start from formal specifications rather than from natural-language intent」 | `N7:135` |
| LLM-agent 子领域的基线集 | **前沿专有模型 12/14、开源权重模型 9/14、共享 ReAct 脚手架 8/14、经典/规则/DRL 仅 5/14、人类专家 0/14**（14 篇测量论文） | `N7:128`、`B6:117-121` |
| 对 ReAct 的定性 | **ReAct 是 harness 不是 baseline**；论文消融的是**模型选择或 scaffold 设计**，不是 prompting 策略。把 ReAct 当 baseline 是错位 | `N7:130`、`B6:110`、`B6:123-124` |
| 人类专家基线 | **0/14**，且「我们也不需要，但要意识到这是一个共同的弱点」 | `N7:154`、`N7:283` |

### 2.3 消融

材料对消融的**具体数字要求**：材料未给出。可从材料中读到的相邻规范只有三条：

1. **建议的 baseline 矩阵形态是二维矩阵**（模型 × 恢复语义），横向看同模型下恢复语义的差异（核心 claim），纵向看同语义下模型强弱的差异（claim 2）——`B6:134-147`。
2. **实验规模给出的是运行计数**：极小 pilot **5 episode × 4 策略 × 1 模型 ≈ 20 次运行**；主实验 **4 策略 × 2–3 个称职模型 × 数十 episode**——`B6:250`、`B6:251`、`B6:261`、`B6:262`。
3. **成功复现一个 baseline 的验收标准**（7 条，`B6:233-241`）：① 由**真 LLM** 驱动，prompt 与工具描述公开可查；② **有 trace**：每轮 thought / tool / args / observation 全部落盘、可人工审计；③ **不由我们调参**：策略参数（重试次数、退避曲线、超时阈值）取文献或规范默认值并给出处；④ **可复现**：固定模型版本 + 固定种子 + 固定 episode 集；⑤ **成本可报**：token 数与调用次数计入 metrics；⑥ **公平**：同 episode 集、同种子、配对比较；⑦ **含退化参照与上界**：至少一个退化方案（如「不重试」）加一个上界（如穷举/最优调度）。

### 2.4 统计检验

| 要求 | 具体内容 | 出处 |
|---|---|---|
| 本项目协议口径 | **做显著性检验**；配对比较；报置信区间 | `D5:87` |
| 波动幅度实例（为什么必须报区间） | 某指标在 5 个种子间为 **3389、7394、6、3373、7393**；「当前只报了均值，还需要补多种子置信区间」 | `P2:54` |
| 效力威胁登记 | **V7：种子间波动大（6 至 7393），中；对策 = 报置信区间，不能只报均值** | `D5:71` |
| 相邻社区的对照 | Raff 复现了 **63.4% of 255 papers**（从零重实现算法）；Gundersen 等复现了**只提供数据的论文 33%** vs **同时提供代码与数据的论文 86%** | `N7:189` |

### 2.5 可复现性（按 venue 分层，含政策原文与数字）

**IEEE / ComSoc 一侧：只有鼓励，没有要求，没有徽章**

- IEEE Author Center：「All IEEE authors are encouraged to share their data, code, and other research outputs…」——`N7:78`。
- TMLCN 是最明确的一家：「authors of accepted papers are strongly encouraged to: a) include a GitHub link to their codes and datasets … and/or b) to submit their codes…」——`N7:79`。
- **JSAC、TCOM、TWC 的 author-guideline 页面「no code/data-sharing clause at all」**，只有接收后「supplementary materials … requested」——`N7:79`。
- ComSoc 期刊**没有 artifact-evaluation track、没有徽章**——`N7:80`。
- 反面自然实验：EURASIP JASP 可复现专刊要求投稿时提供代码与数据并在评审中检查，结果 **31 篇投稿只有 4 篇被接收**，其余「did not show any sign of reproducibility at all」——`N7:98`、`N7:170`。

**ACM SIGMOBILE（MobiCom / MobiSys / SenSys）：正式 AEC + 三个独立徽章**

- 「Authors will apply for specific ACM badges for 'Artifact available', 'Artifact evaluated – functional', 'Results reproduced' … These badges are **independent**, and authors may seek one, two, or all three」——`N7:84`。
- 硬门槛：「Artifacts Available」要求「a publicly accessible DOI or link to the source code repository」；依赖硬件的论文必须提供「remote access … e.g., using Zoom, Microsoft Teams, or Google Hangouts with anonymous accounts」——`N7:85`。

**ACM SIGCOMM / CoNEXT：同一模型，但不增长**

- 「Adoption **stagnates over the years**」；「AE participation stagnates」；「Hardware requirements may prevent effective reproduction」（3 个 artifact 需 NVIDIA GPU、3 个需 Intel Tofino、1 个需 512 GB RAM、1 个需 >$1000 AWS）——`N7:89`。
- **CoNEXT 2023：接收 30 篇，19 篇（63%）提交 artifact**；整体**授予率 60%（Available）/ 47%（Functional）/ 33%（Reusable）**——`N7:180`。

**USENIX NSDI：明文开放全部接收论文，但仍自愿**

- 「The NSDI '26 artifact evaluation process is open to all accepted papers. … Artifact evaluation is **optional**, although we hope all papers will participate.」三个徽章，鼓励 DOI 背书的长期存储，AEC 会「inform and advise the Program Committee」——`N7:94`。

**EuroSys（成熟 AEC 的标定）**

- 5 年 AE、三个徽章、2025 年 98 名委员；路线图仍把「Require AE for all accepted papers, with opt-outs」与「Tie AE outcomes to paper acceptance」列为**待办**——即最强的 artifact 社区也**尚未强制**——`N7:96`、`N7:181`。

**群体层面的实测数字（`N7` §5）**

| 数字 | 总体 | 出处 |
|---|---|---|
| 只有 **18/130（13.85%）** 提供了数据样本来源的可用信息 | 130 篇无线 ML 资源分配论文 | `N7:166` |
| **102/130（78.46%）** 完全未说明数据来源；**13** 篇称「request 后提供」 | 同上 | `N7:167` |
| **~40%（52/130）** 对验证环境信息不足 | 同上 | `N7:168`、`N7:120` |
| 详审的 **27 篇中「the vast majority」不提供也不共享源码**，只有 1 篇提到可能公开代码 | 同上 | `N7:169` |
| **128/130 用仿真环境**，只有 **5** 篇用了额外实验设备 | 同上 | `N7:108` |
| 只有 **40/130** 说明了所用软件/框架/IDE；其中 MATLAB 最多（**28** 项研究），Python 提及 32 次，PyCharm 4，C++ 1 | 同上 | `N7:109` |
| **56.2%** 的 402 篇声称有代码的 ACM 系统论文实际共享了代码；**32.3%** 能在 30 min 内构建；**48.3%** 需额外功夫才能构建；**43.3%** 的接收论文提交了 AE artifact、**29.5%** 被接受（7 个会议）；177 份作者问卷中 **83.1%** 说公开代码与产生结果的版本一致 | 402 篇 ACM 计算机系统论文等 | `N7:178` |
| MobiHoc 仿真论文（2000–2005）**~15%** 可重复；134 篇 *Telecommunications Policy* 论文 **33%** 发布数据但**只有 9%** 发布代码；600 篇 ACM CS 论文 **~32%** 弱可重复 | — | `N7:177` |
| 应用安全会议 artifact 制作率：**ACSAC 48%、AsiaCCS 26%、EuroS&P 31%、WiSec 38%**（*[search snippet]*） | 11 年综述 | `N7:182` |
| NeurIPS 有开源代码的论文从 **27.6%（2016）** 升到 **>60%（2019 起）**，2018→2019 的 **20.6%** 跳升与 reproducibility checklist 相关；ICRA 六年只有一次超过 **5%**；CDC 到 2021 年才首次超过 **2%** | — | `N7:186` |
| 五个顶会 56,800 篇论文中同时共享代码与数据的比例从 **11%（2014）** 升到 **64%（2024）** | 五个顶会 AI 会议 | `N7:188` |

**LLM-agent 子领域的 artifact 现状（16 篇核验，2026-09-12 HTTP 检查）**

- **8 篇有可访问 artifact，3 篇公告的链接已坏或受限**（一个 401 匿名评审登录、一个 404 死链），**5 篇什么都没发**——`N7:156`、`B6:130`。
- 「**benchmark papers release almost universally**；algorithm/application papers often do not」；样本中 IEEE 系最弱——`N7:156`。
- 定性判断：**「a benchmark without an artifact is not citable as a benchmark」**——`N7:202`。

### 2.6 评审人 checklist（`N7:195-202`，逐条）

1. **自己重实现基线并写清**：命名每个基线、引用取出**算法**的论文、声明是重实现的（「we implement [X] following the update rules in [ref, eq. (n)]」）。
2. **给每个基线公平机会**：同一信道实现、同一 SNR 扫点、同一功率/带宽/复杂度预算、同一蒙特卡洛次数，并调每个基线的自由参数。**最常见的致命批评是稻草人基线**。
3. **至少含一个退化参照与一个上界/穷举参照**。
4. **无仓库也要可证伪**：完整参数表（载频、带宽、拓扑、路损模型及其引用如 TR 38.901、噪声系数、衰落分布、码本大小）、**显式试验次数**、**显式种子或生成过程**、算法伪代码。
5. **代码公开是可选的额外开销，不是质量证据**；若发布，发单一 MATLAB/Python 包，**一图一脚本**，README 把 claim 映射到脚本；系统类 venue 要 DOI 背书归档。
6. **若写在 LLM-agent 空间则把期望倒过来**：会要求**前沿模型 + 开源权重模型**在**文档化的 prompting/agent loop** 内比较，**显式声明 scaffold**（ReAct / tool-use / multi-agent），**在具名公开 benchmark 上评测**（若合适），否则**发布自建 benchmark 并附可执行测试用例而非仅 LLM judge 分数**，且要发布代码或 benchmark。

### 2.7 引用规范与数据来源分层（`D5`）

- **四层证据分层**：M · Measured（真实观测）/ S · Standard model（按标准取参）/ F · Fitted（参数由真实数据估计，须给拟合方法与拟合优度）/ A · Assumed（本文选择，**必须做敏感性分析**）。**A 层参数必须扫描，不能只报一个点，否则等于把假设当结论**——`D5:9-16`。
- **固定项 vs 扫描项**：固定地形、节点集与 episode 集（冻结并公开）、标准模型与参数、模型版本、解码参数与种子；扫描全部 A 层项（温度基线与季节振幅、积雪概率、加热电池箱比例、地面电参数、ACK 丢失率）——`D5:85`。
- **可复现清单**：发布代码、episode 集与全部超参，提供**一键复现脚本**，记录模型版本与调用成本——`D5:89`。
- **七条效力威胁**（按严重性）：V1 信道统计来自城市 LoRa 而非山区（最高）；V2 温度基线未标定（高）；V3 无任何自有实测（中高）；V4 故障分布为合成（中高）；V5 **baseline 为自实现**（中）；V6 agent 为脚本驱动（高）；V7 种子波动大（中）——`D5:63-71`。
- **子领域归属决定了适用哪套最严标准**：「本文落在第三个子领域（LLM-agent），因此适用其中最严的一套标准。baseline 需要重实现并公平调参，数据需要提供公开 benchmark 或自建并附可执行测试用例，模型对比需要同时覆盖前沿与开源权重，artifact 需要发布」——`D5:79-81`。
- **一条硬约束**：「只用 LLM judge 打分**不被接受**」——`D5:79`；`N7:280` 同义：「我们必须采用后者：**可执行测试用例 + judge 配对**，不能只给 LLM judge」。

---

## 3. 同域基线清单（来源：`B6`）

`B6` 的核验方式：GitHub 仓库实际解析 + 目录内容检查 + raw 文件抓取，2026-09-12（`B6:9`）。用途：确定论文的同领域 baseline 与可复用环境（`B6:10`）。

### 3.1 第一梯队：有论文 + 有代码 + 任务类型相关（`B6:18-28`）

| # | 方法 | 会议/期刊 | **它的 task** | **它的指标 / baseline** | 数据/环境 | 代码规模与许可 |
|---|---|---|---|---|---|---|
| 1 | **LMTE**（arXiv 2602.00941） | **IEEE INFOCOM 2026** | 流量工程（TE） | **baseline = Gurobi 经典解（COPE / oblivious / optimal）+ 学习式 baseline**；指标材料未给出 | **GÉANT +4 TE 数据集**；LLaMA-3 | `Y-debug-sys/LMTE`：`cl_baselines/`、`ml_baselines/`、`src/`、`lms/`、`scripts/`、`main.py`，Apache-2.0 |
| 2 | **NetConfArena**（arXiv 2608.23179） | arXiv | 网络**配置**任务 | baseline = **ReAct vs OneShot**（含完整 prompt 与工具定义） | **GNS3**；**96 模板 → 480 实例 → 3840 轨迹**；需专有 Cisco 镜像 | `liujona/NetConfArena`：**364 文件**，Apache-2.0 |
| 3 | **NetArena**（arXiv 2506.03231） | **ICLR 2026** | DC 容量规划 / 路由修复 / 微服务策略排障 | baseline = prompt-based agent vs A2A 框架；**agent 平均只拿 13–38%** | **Mininet + Kubernetes**；动态生成查询 | `Froot-NetSys/NetArena`：`a2a_llm/`、`app-k8s/`、`app-malt/`、`app-route/`、`src/netarena/`，43★ |
| 4 | **NIKA**（arXiv 2512.16381） | arXiv | detect → localize → RCA | baseline = **SOTA LLM agent（可插拔）**；指标材料未给出 | **Kathará + Containerlab**；5 场景 54 故障 | `sands-lab/nika`：**1662 文件 / 1456 代码**，58★ |
| 5 | **NetOpsBench** | 无同行评审论文 | 运维监控/诊断 | **统一评测器（检测 / 定位 / 效率 / 工具使用）** | **SONiC-VS + Containerlab**；HF 轨迹数据集 | `NetX-lab/NetOpsBench`：**373 文件 / 307 代码**，30★，**MIT** |
| 6 | **WirelessAgent**（arXiv 2505.01074） | **IEEE/CIC China Communications 2026** | 网络切片场景 | baseline = **prompt-based + rule-based 最优** | 射线追踪 CQI + 网络切片场景 | `jwentong/WirelessAgent_R1`：16 代码文件，47★ |
| 7 | **WirelessAgent++ / WirelessBench**（arXiv 2603.00501） | arXiv | 静态无线问题求解（分类服务 / 预测 CQI / 分配带宽） | baseline = **SOTA prompting + 通用 workflow 优化器** | **WirelessBench（3,392 题）**；MCTS 工作流搜索 | `jwentong/WirelessAgent-R2`：**298 文件 / 119 代码**，**MIT** |

### 3.2 第二梯队：顶会顶刊、有代码，但任务类型偏离（`B6:30-37`）

| # | 方法 | 会议/期刊 | **它的 task** | **指标 / baseline** | 代码 |
|---|---|---|---|---|---|
| 8 | **NetLLM**（arXiv 2402.02338） | **ACM SIGCOMM 2024** | LLM 适配（非 agentic） | baseline = **A3C / CNN / LSTM** | `duowuyms/NetLLM`：**4249 文件**，205★，MIT |
| 9 | **NetConfEval** | **ACM CoNEXT 2024** | **5 类配置任务** | 有 reproducible `artifact/` 脚本；验证方式是部署到真实 FRRouting（`N7:143`、`N7:277`） | `RedHatResearch/conext24-NetConfEval`：124 文件，42★，MIT |
| 10 | **Cellular-X**（arXiv 2504.13190） | **ACM MobiSys 2025**（demo） | 蜂窝网络任务 | baseline = **RAG vs 非 RAG** | `SeaBreezing/Cellular-X`：11 代码文件；**真实 USRP + srsRAN LTE testbed** |
| 11 | **ORION**（arXiv 2603.03667） | arXiv | O-RAN | 指标材料未给出 | **6 个仓库**，其中 `orion-xapp` 1092 代码文件（C++/ASN1c）；O-RAN SMO + rApp + xApp + E2Sim |

### 3.3 明确找不到代码的（`B6:39-44`）

- **"Rollback Is Not Undo"（IEEE INFOCOM 2026）**——闭源、无 artifact（已核实 CLOSED）；`S3:67` 另记 DOI `10.1109/INFOCOM59046.2026.11571400`，IEEE 付费、需机构订阅。
- Network CoPilot（INFOCOM 2025）、RIDAS、RepLLM（SIGCOMM 2026）、MobiLLM。
- **任何 IEEE JSAC / TCOM / TWC / TMC 2024–2026 的 LLM-agent 公开 artifact——一个都没确认到**；但「这些期刊很多论文没有 arXiv 版，属**检索盲区，不等于不存在**」（`B6:44`）。

### 3.4 修正后的 baseline 方案（`B6:61-81`）

**第一层 · 同领域（必需）**

| baseline | 来源 | 搬运成本 |
|---|---|---|
| **B-D1** NetConfArena 的 **ReAct + OneShot harness** | Apache-2.0 | **低**：prompt 与工具定义可直接搬，其工具分类（只读 / 副作用 / 只读验证）「与我们的完全一致」 |
| **B-D2** WirelessAgent++ 工作流 | MIT | 中：需把 operator 接到我们的环境 |
| **B-D3** NetArena 的 prompt-based agent | ICLR 2026 | 中 |
| **B-D4** LMTE 的**经典 Gurobi 最优** baseline | Apache-2.0 | 中：代表「通信领域的优化方法」这一路 |

**第二层 · 跨域机制（对照）**

| baseline | 来源 |
|---|---|
| B0 | **Verified Tool Calls（arXiv 2608.02645，已实现）** |
| B1 | ReAct（ICLR 2023） |
| B2 | MCP 默认语义（已实现） |
| B3 | timeout + blind retry（已实现） |

`B6:81`：**两层都要，缺一不可。**

**可复用的 benchmark**（`B6:85-89`）

| benchmark | 用途 |
|---|---|
| **WirelessBench（3,392 题）** | 证明方法在**领域标准任务**上不退化 |
| NetConfArena / NIKA / NetOpsBench | 可直接对比的**同领域环境** |
| **我们的 disruption benchmark** | 核心 claim |

### 3.5 同域里最值得正面单列的一条跨域 baseline：arXiv 2608.02645（`B6` 附录 B）

- 标题：「Verified Tool Calls Improve LLM Agent Reliability Under Non-Atomic Failures」，作者 Isham Kalappurackal Mansoor、Abhishek Phadke、Pratip Rana，2026-07-31（`B6:173-174`）。
- 摘要原文：*"a lightweight, **verification-aware tool wrapper** … augments tool calls with **postcondition verification, verify-before-retry logic, and idempotency keys**"*；评价方式是 *"a controlled simulated environment with **injected** non-atomic failures"*；故障类为 *"timeouts after dispatch, delayed visibility, and partial state updates"*（`B6:178-181`）。
- 定位：「它是『已发表的最强恢复机制』的代表。只跟 naive retry 比，审稿人会说赢的是稻草人」（`B6:183`）。
- **三段式实验设计（`B6:203-210`）** ——这是 `B6` 里最接近「可沿用的 task 结构」的一段：

| 阶段 | 做什么 | 期望 | 作用 |
|---|---|---|---|
| ① **忠实复现** | 在它自己的**注入式**故障上跑它 | 重复动作下降 | **证明我们的实现忠实**，不是稻草人 |
| ② **换故障生态** | 同一实现，跑在**地形驱动**故障上 | 验证者不可达 → 退化 | 找到它结构性失效的工况 |
| ③ **我们的方法** | lifecycle runtime：durable log + reconcile 处理「验证者不可达」 | 恢复正确性 | 给出修复 |

- 对照的干净之处：**同一方法、两种故障生态（注入 vs 轨迹驱动）**（`B6:209`）。
- 原文未定义的分支必须标注：`verify_postcondition` 返回 `UNKNOWN` 时原文未定义（`B6:214-227`），复现时「按**最有利于它的读法**实现（退化为盲目重试），并**在论文里明确标注**这是我们的补充而非原文规定」（`B6:226-227`）。
- 其结构性软肋已有实测（信道属性，与 agent 无关）：最真实配置下（G-E + real energy）2400 次验证尝试返回 unknown **1212 次，占 50.5%**；另三格分别为 41.6% / 40.8% / 49.9%（`B6:190-198`）。

### 3.6 同域另一些带代码的工作（`B6:273-288`）

| 工作 | 说明 |
|---|---|
| `duowuyms/OpenCATP-LLM` | 城市蜂窝容量/流量预测；baseline 为 LLaMA/OPT/Qwen + LoRA 与非 LLM 预测 |
| `dadsetani/llm-safemit` | IEEE TNSM，Zenodo 有 release，但仅 **8 文件 / 3 代码（很薄）** |
| `frezazadeh/LangChain-RAG-Technology` | ns-3 + 5G-LENA 多 agent；**论文自称是 "lightweight mock version"，不是完整实现** |
| `secretcheng/HybridRAG-for-Network-Optimization` | **仅有 README + 1 个 notebook**，是 demo 不是实现 |
| `emilbjornson/scalable-cell-free` | TCOM，系数级可复现 |
| `luanedge/WSR-maximization-for-RIS-system` | TWC，**随附 `without_RIS.m`、`RIS_phaserand.m` 作为独立 baseline 脚本** |
| `BJTU-MIMO/Power_Allocation_DDPG` | TVT |
| `zctzzy/STCNet` | JSAC |

**核验方法**：GitHub API + HTML tree 实际解析，确认含真实源文件（`.py/.c/.cpp/.ipynb/.sh` + 构建文件），**不是 README-only**。`B6:288` 记：「README-only」的失败模式在本次核验中未出现；反而有两篇是「有代码但不可用」。

---

## 4. 反面清单：材料里明确写过的「toy / 不成立」判断

逐条摘出，保留原文措辞。

### 4.1 本项目 task 本身被判定为不合理

1. **「判断是：task 本身不合理——早期任务设计太 toy，不能反映本项目的场景、定位与问题。」**——`docs/s7-method/task-challenge-pivot-2026-09-13.md:29`（本次十文件清单之外，但为该项目「太 toy」判断的唯一原始出处）。
2. **非 toy 任务必须具备的四件事（尚未采纳，供决策）**——`task-challenge-pivot-2026-09-13.md:143`：① **需求必须内生**：中心下一步看哪里必须取决于它已经看到了什么；② **观测之间必须有依赖**：漏掉第二次观测使第一次观测失去价值；③ **覆盖增强必须成为决策而不是背景**（备用路径现在只出现在 3 种子的旁支实验里，主表 `runtime_paths=0`）；④ **供电必须 binding**。同文件 `:160` 给出根因：「设备影子维护的是『被命令的状态』，它**没有表达『这次观测比那次更值钱』的词**」；`:169-170` 另有一条纪律：「**不能只加复杂度**……把 16 个节点变成 64 个、把风险窗变成 20 个，**仍然没有决策，只是更贵**」。
3. **闸门 1（任务有效性）：任务里必须存在一个由观测结果决定的决策**——`task-challenge-pivot-2026-09-13.md:130`。闸门 0 更前置：若 (a) 显示中心极少下发命令，则「机会竞争」这个前提本身就弱（`:124-127`）。

### 4.2 toy 假设对结论的定量影响（`P2`，**数字已失效**）

4. `P2:3`：「把 toy 的物理假设换成真实模型，结论是否改变。答案是会变，而且幅度很大，**toy 假设同时低估了问题规模与修复价值**。」
5. `P2:26`：**「toy 假设把问题规模压小了 5.7 倍」**（核心故障类 `outcome_unknown` 从 1354.4 → 7717.4）。
6. `P2:28`：**「toy 假设把修复价值压小了 11 倍」**（lifecycle 相对 naive 的重复副作用削减由 1.6 倍变为 18.7 倍）。
7. `P2:30`：「**能量模型的影响大于信道模型**……供电导致的长时间静默是故障分布的主导维度」（单独换信道 480.2→442.0 几乎不变；单独换能量 480.2→1806.2，3.8 倍；两者同换 1620.6，存在交互而非叠加）。
8. `P2:32-36`：toy 窗口本身也制造假结论——「错在窗口选择——30 天窗口恰好从 1 月开始，只覆盖死亡过程，看不到复活」。
9. **但 `P2` 的绝对数字全部作废**：`R:26` 标「数字已失效，勿引用」；`R:32-34` 给出两处错误（`-27.55` 应为 `+32.44`，差 60 dB；`node_link_matrix` 被误读）。`R:36`：「`s6-2` 的相对结论（能量模型的影响大于信道模型；toy 假设会低估问题规模）方向可能仍然成立，但其中的倍数必须重算后才能引用。」

### 4.3 现有 benchmark 全体的结构性判断

10. `C9:5`（Headline）：**「the answer to (a)+(b)+(c) is NO for all six.」**（六篇全不满足）
11. `C9:88`：**(a) agent 自己那条链路是否退化——六篇全为 NO**。「在每一个 benchmark 里，agent 的工具调用、MCP 流量、SSH/CLI 会话与 LLM API 调用都跑在未退化的信道上。网络永远是 agent 动作或诊断的 **OBJECT**，从来不是承载 agent 自身遥测的 **MEDIUM**。」对 agent-channel 构造搜遍六篇全文「zero hits」。
12. `C9:90`：**(b) 故障是否由真实地形/功率 trace 驱动——六篇全为 NO**。「每一个故障都是注入的、合成的或干脆不存在。」最强者只是**词汇**层面有据（WirelessOptBench 引 TeleLogs/AIOps2025/RCA100；NIKA 手工整理「realistic」issue），**实现仍是 benchmark 定义**。原文自认：「the taxonomy and oracle are benchmark-defined rather than drawn from an unseen generator or independent deployment study.」NetOpsBench 的 impairments 是**手设常数**。**没有任何 benchmark 从传播模型、高程数据、RF 实测 trace 或功率/能量状态导出故障。**
13. `C9:92`：**(c) 任务是否是长时程监测 mission——NO**。NIKA 与 NetOpsBench 最近，但**都是 episodic**：一次事件 → detect/localize/RCA → episode 结束。「NIKA 的长运行时（全 150 事件套件 7–15 h）是**聚合 wall clock，不是一次长 mission**；NetOpsBench 的『效率』指标是**工具调用数与 token**，不是监测耗时。**两者都不因 agent 漏掉 episode 中途发生的事件而扣分，都不随时间衰减信道状态，也不要求 agent 在数小时的退化条件下维持态势感知。**」
14. `C9:100`（结论）：**「六个 benchmark 中没有一个满足 (a)、(b) 或 (c)，单独或组合皆然」**；且这**不是服务不足，而是整个类别的结构性 out of scope**——「这一类别一致地把网络固定为控制的对象而非 agent 的媒介」。
15. `C9:82`：**「Energy/power is absent from all six」**；**「Terrain/propagation appears in exactly one（WirelessBench）并只作为一个可调用的 CQI 工具」**。
16. `C9:96-98`（部分覆盖，精确表述）：NIKA 在**注入的真实性**上走得最远但 agent 在带外、故障是注入非实测、无能量模型、无传播模型、每个事件是有界诊断 episode；NetOpsBench 在**运维框架**上走得最远但退化是 `tc` 常数、agent 自己的链路是干净的、评分是单事件诊断；WirelessBench 是唯一有任何**物理**信道建模的，也是唯一**完全无故障**、没有任何 live 环境的，**是六者中离 (a) 和 (c) 最远的**。

### 4.4 WirelessOpsBench artifact 层的不可执行判定（`A10`）

17. `A10:35`：**「公开包不可执行，这是本节的关键结论。」**四条独立证据（`A10:39-42`）：① 同一 base 的八个 case，`public_task` **逐字节相同**，只有 `case_id` 不同——「**故障不由数据承载**」；② `public_input` 只含任务参数，不存在证据账本内容；③ **无任何答案、gold、reference 或 label 字段**，全库检索只命中动作 schema 里的 `expected_version`；④ **`ray_tracing` 不在 `tool_schemas` 里**，而 200 份 WCNS/WCMSA 的题面要求「You MUST call the ray_tracing tool」——**题面与工具契约不自洽**。
18. `A10:44`：评测端扣留 READY 证据与评测谓词——「Evaluator-private initial states, schedules, labels, reference interventions, and scoring predicates are excluded」，且服务器「not yet online」。
19. `A10:22`：「公开包**只有数据，无 runner、无 scoring 谓词、无 fault schedule**。」
20. `A10:80`：七类故障条件「全部刻画证据账本的可信度，判据是『这条记录可不可信』。**无一条描述动作分发之后的传输语义。**」
21. `A10:92`：两套判据不可互译——其 false-success update 是「上报成功而状态未生效」，我们的 ACK 丢失是「状态已生效而回执未达，重试即产生重复副作用」，**方向相反**；其 concurrent version drift 由数据面并发写者造成，我们的视图落后由控制面链路中断造成；**「派发后节点失联、pending 被遗忘、重放顺序错、网关抖动、分区分歧、协调者重启六类在其故障表中没有对应项，因为其 episode 把工具调用视为必然送达。」**
22. `A10:88`：**不可声称与论文所报数值可比**——artifact 不含 baseline 分数、轨迹、token 数、成本与延迟。

### 4.5 执行层在 benchmark 任务契约上的判定（`E11`）

23. `E11:16`：「**任务正确性不重新评分。公开包扣留了 scoring 谓词，重评等于替 benchmark 造答案。**」
24. `E11:43`：**「幂等键在没有配合的远端时价值为零。」**`stable_key_only` 在幂等 sink 上重复为 0，换成非幂等 sink 后变成 280.7 每千周期，**与 `naive` 逐位相同**；同时 sink 的去重计数从 2,156 掉到 0。「上一行里那份收益**全部来自远端对键的配合，与 agent 的纪律无关**。」
25. `E11:45`：「**epoch 强制让所有策略的重复归零，包括每次都用新身份的 `naive`。**……agent 什么都不用改。**重复这一侧的修复位置在远端，不在 agent。**」
26. `E11:47`：**「已发表的谓词在这里失效。」**`verified_wrapper` 的零效果率在强制 epoch 后从 6.8 升到 **66.4** 每千周期，**是不做任何验证的 9.8 倍**；「horizon 为 1 时该缺陷**不可见**：四个策略的零效果均为 0.0」。
27. `E11:53`：**「只统计任务结果与重复率的评测会把它排为更优解。」**`verified_wrapper` 把重复从 280.7 降到 132.4，看似改进；在强制 epoch 配置下把重复降到 0 的代价是 **510 个周期的写入从未落地**。
28. `E11:55`：「上游 benchmark 的七类条件……其 episode 把工具调用视为必然送达，**重复与零效果这两条轴都不在其故障表内**；公开包也不含 baseline 分数。」
29. `E11:65`：「验证返回 `unknown` 时的**最优策略未做搜索**，当前只做有界重试。」

### 4.6 「工具调用默认可用」这一前设在同域文献中的空白（`S3`）

30. `S3:9`：agent 框架对工具调用的默认假设有四项——调用是原子的、返回是二值的、观测是当前的、重试是安全的；「在本文场景中这四条**同时失效**」。
31. `S3:11`：结构性原因——**控制命令与数据走同一条链路**，「协调通信实体所依赖的命令，必须通过被协调的那条不可靠链路下达」；MCP 规范 2026-07-28 版是最直接例证：规定超时后发送方 SHOULD cancel the request and stop waiting，「承认 cancellation notifications may arrive after request processing has completed」，并要求发送方 SHOULD ignore 之后到达的响应，**而整份规范中没有结果不确定状态，也没有幂等语义**。
32. `S3:29`：现有 benchmark 的 `timeout` 类**都是可见超时**，agent 能据此判断工具失败；**「尚无 benchmark 把『动作已执行但结果不可见』作为一等注入类。」**
33. `S3:2`（四问表）：**Q1（是否假设工具调用可靠且即时返回）在网络侧 5 篇全部为「否」**，但 **Q2（是否假设网络状态完全可观测）为「是」** 的包括 6GAgentGym、WirelessBench、WirelessOpsAgent、DORA；**Q3（超时后效果不可知/幂等）仅在 Verified Tool Calls 一篇为「是」**，其余为「否」或「部分」；**Q4（分钟至小时级观测延迟）无一篇命中**。
34. `S3:40-46`（Gap 清单，每条写成「未找到正面命中」）：**G1** 通信中断未被建模为 agent 观测与控制通道的固有属性（网络侧 5 篇全部假定观测通道可用，`partition`/`disconnect` 命中 **0**）；**G2** 分钟至小时级观测延迟无人处理（最长语义是**秒级** Delayed Visibility）；**G3** 超时后远端效果未知：**网络运维侧 0 篇**；**G4** 幂等性与跨断连的操作生命周期：**网络运维侧 0 篇**，`reconcile` 命中 **0**；**G5** 「观测通道 ≡ 控制通道」**在检索覆盖的文献中无任何对应工作**，「所有基准都默认存在一个带外可用的观测接口」——「**这是最干净的一条**」；**G6** 灾区/山地监测网络作为前提的 agent 工作缺失。
35. `S3:50`：**「没有任何一篇同时把『链路频繁中断 + 观测延迟数十分钟至数小时 + 工具执行结果不可知』作为 agent 运行的前提假设。」**最强的三篇各推进一步但不合流（WirelessOpsAgent 只处理更新速率与乱序导致的陈旧；Verified Tool Calls 在通用客服/发票工作流上；DORA 在灾害域但评测地理空间推理）。
36. `S3:58`：所立命题——「agent 的观测通道与它的控制通道是同一条，『实体已静默』与『我的查询在回程丢了』**在观测上不可区分**」——**在本文献范围内是未被占据的位置**。
37. `S3:28`（引用纪律）：TopoLLM 的判定「**不等于证明**其部署中假设所有工具可靠、所有网络状态完全可知」。

### 4.7 子领域层面的「拥挤批评」与定位风险（`N7` §7）

38. `N7:224-231`：四篇 2025–26 论文用几乎相同的话否定同一个既有做法——NetConfArena 攻击「static command generation… overly simplified settings」；FaulT-Bench 攻击「only accurate tickets and always assume a fault is present」；WirelessOpsAgent 攻击「fixed observations」；NetArena 攻击「static design… contamination… high variance」。
39. `N7:238-244`：**「这个子领域拥挤的批评是：『评测是静态的 / 过度简化』」**，与另一件事不同但**很容易被读成同一件事**；若不显式区分，「会显得像第五篇说同样话的论文」。

### 4.8 已被取代的旧设计（避免沿用时踩到）

40. `R:24`：`s5-1-failure-model.md` 的 11 状态生命周期「**已被取代**」——「该设计把执行生命周期、观测状态、远端效果与环境可达性**混在同一个枚举里**，且 `outcome_unknown` **同时被当作终态与未决**」；现行设计见 `README.md` 第五节与 `code/operations.py`。
41. `R:25`：`s6-11` 是「在 benchmark 任务契约上的 2×2 消融」，「**已被取代**」；其可迁移结论已并入 `README.md` 第六节的协议消融表。
42. `R:23`：`s6-9` 「**已被取代**」，benchmark 路线放弃后不再进入正文。
43. `R:13-14`：放弃 benchmark 路线的另一条独立理由与替代方案——「自建仿真基底，各层选择与参数全部公开」。

---

## 5. 我们缺什么：材料**没有**提供的东西

只列材料中**确认为空缺**的项；凡材料明确点名的缺口都带出处。

### 5.1 task 生成机制层面（最关键的缺口）

1. **一套可复用的 task/需求生成器**。`task-challenge-pivot-2026-09-13.md:168` 写明重设计会「作废**需求生成器**、评分口径与四张业务表」——即现行生成器存在但被认为无效；**材料未给出**新生成器应采用的生成范式（规则 / 真实 trace / 模板采样中的哪一种）。材料里唯一可援引的生成范式是别人的：NetConfArena 的「96 模板 → 480 实例 → 3840 轨迹」（`B6:23`）与 NetArena 的「每轮评测随机采样动态生成查询」（`C9:31`）——**是否适用于本项目，材料未给出**。
2. **episode 格式定义**。`F1:3` 明写「episode 格式、工具集与 metrics **不在本文件范围内**」；`F1:90` 把「episode 格式需要把上述故障编码进事件流」列为**后续**。⇒ **材料未给出 episode 的字段级定义。**
3. **评分谓词（scoring predicates）**。`A10:86` 明列「须自建：证据账本内容、`ray_tracing` CQI 提供者、runtime、**scoring 谓词**」；`A10:44` 说明上游把「scoring predicates」列为 evaluator-private 排除项；`A10:88` 说 artifact 不含 baseline 分数。⇒ **材料未给出可执行的成功判据。**
4. **可执行测试用例**。`N7:202`/`D5:79` 要求「可执行测试用例 + judge 配对，不能只给 LLM judge」；但材料**未给出**任何具体测试用例集、其形态或数量。`A10:86` 只说这一层「即本项目所补的执行层」。
5. **真实 mission objective 的形式化**。`P2:64`：「任务形式化（**用真实 mission objective 替代阈值告警**）与公平评估协议（双轨指标加置信区间）都可在纯 CPU 上完成」——被列为**后续**，⇒ **形式化本身材料未给出**。现行任务只是「持续读取传感并在异常时告警，`alert.send` 为副作用工具」（`P2:9`）。
6. **「双轨指标」的具体定义**。`P2:64` 只点名「双轨指标加置信区间」，`P2:58` 说明其动机是「`lifecycle` 的残留重复部分来自 agent 的分段判断与环境真值之间的错位」，并称「评估公平性尚未解决」——**两轨各是什么、怎么算，材料未给出。**
7. **故障 schedule / 注入时刻表**。`A10:22`：「公开包**只有数据，无 runner、无 scoring 谓词、无 fault schedule**」；`A10:86` 把带 `ray_tracing` 的 runtime 列为须自建。⇒ 沿用时**须自建 fault schedule**，材料未给出其规范。

### 5.2 对照与基线层面

8. **主实验用哪几个模型：未定**。`B6:165`：「前沿模型 + 中档模型 ⬜ 待定」；`B6:104`：「确认主实验用哪几个模型（见 §C 的同类论文惯例）」列为待补；`B6:262` 只给形式「4 策略 × 2–3 个称职模型 × 数十 episode」。`D5:53`：「模型版本层为 M，**取值未定**，须固定并记录」。
9. **B-D1 / B-D2 接入本环境的实际工作量**：`B6:103` 明列为待补项「⬜ 逐个确认 B-D1 / B-D2 接入我们环境的实际工作量」。
10. **人类专家基线**：`N7:154`、`N7:283` 记录该子领域 **0/14** 无人类专家 baseline，且「我们**也不需要**，但要意识到这是一个共同的弱点」——即材料**不提供**人类专家 baseline 的设计。
11. **上界/最优解的存在性**：`N7:199` 要求「至少一个退化方案 + 一个上界（如穷举/最优调度）」（`B6:241` 同）；但材料**未给出**本场景的上界怎么算（哪些维度可穷举、规模上限何在）。
12. **同域对照的可比读数**：`A10:88`「不可声称与论文所报数值可比」；`E11:67`「全部数值为本文自己的 runtime 在公开开发集上的结果，**不是该 benchmark 的官方分数**」。⇒ 沿用时**拿不到官方分数作为参照**，材料未给出替代方案。

### 5.3 物理与数据层面（A 层未标定项）

13. **温度基线未标定**：`D5:45`「温度基线 A · Assumed，未用气象站数据核对，自估可能偏冷约 10 °C」；`D5:60`「温度基线未与气象站数据核对」；`D5:97` 列为待补。对策在材料里是二选一（用真实站点数据标定，或做完整敏感性分析），**材料未给出选定结果**。
14. **`ray_tracing` CQI 提供者缺失**：`A10:42` 指出题面要求调用 `ray_tracing` 但它不在 9 个工具 schema 内；`A10:86` 列为须自建；`E11:59`「CQI 是本项目提供的**替代量**……该参数属假定层，须做敏感性扫描而非当作实测值报告」。⇒ **该值本身材料未给出，且被明确限定为不可当实测。**
15. **域偏移分析未做**：`D5:65` V1（最高威胁）要求「做显式域偏移分析」；`D5:34` 要求「必须做域偏移分析并写明」；`P2:52` 说明 ChirpBox 采自上海城区而非山区。⇒ **分析本身材料未给出。**
16. **ITU-R P.1546 / P.2001 对 ITM 的交叉验证未做**：`D5:26` 要求「必须用 ITU-R P.1546 或 P.2001 交叉验证」；`D5:97` 待补。`D5:52` 另限定「两者不可混用」。
17. **所有 A 层参数的敏感性扫描未给结果**：`D5:16`「A 层参数必须扫描，不能只报一个点」；`D5:85` 列出须扫描项（温度基线与季节振幅、积雪概率、加热电池箱比例、地面电参数、ACK 丢失率）；`P2:49` 记积雪维度「被充电闸门遮盖」。
18. **置信区间普遍缺失**：`P2:54`「当前只报了均值，还需要补多种子置信区间」；`D5:71` V7 同；`B6:266` 要求「必须报多种子 + 置信区间」。

### 5.4 论证与定位层面

19. **「中心多久真的下一次命令」这一前提未被文献确认**。`task-challenge-pivot-2026-09-13.md:124-127`：闸门 0 须确认「(a) 灾前监测里中心多久真的下一次命令；(b)『观测结果改变观测计划』是不是真实存在的做法」；若 (a) 显示中心极少下发命令，「则『机会竞争』这个前提本身就弱，整个框架需要重新论证」。⇒ **材料未给出该问题的答案。**
20. **「由观测结果决定的决策」的判据尚未落笔**。`task-challenge-pivot-2026-09-13.md:130` 立了闸门 1，但 `:172` 明说「**闸门 1 必须在动手前用可核查的判据写清楚**，而不是事后解释」——⇒ **该判据材料未给出。**
21. **方法关口的对手尚未造出**。`task-challenge-pivot-2026-09-13.md:132-134`：需与「成熟影子 + 合理的固定优先级/截止时间调度 + 简单的冗余请求抑制」比较，而「这个对手**必须先被造出来并证明它已经吃掉了排序修复那 5.5 个点**，否则又是一次能力不对等」。⇒ **该对手与其读数材料未给出。**
22. **必读文献仍有 4/6 未读**。`S3:62-67`：仍缺 ① **α³-Bench（arXiv 2601.03281）——Gap 1 的最大风险项，必须补读**（需确认 packet loss 作用在 tool call 上还是只影响推理上下文，「这个问题不解决，Gap 1 的表述就不能落笔」）；② Atomix（arXiv 2602.14849）的 **A.2 Fault Injection Details** 附录；③ AgentChaos（arXiv 2608.06790）+ AgentDisruptBench——「用于构建**注入故障类的对照表**（该表是 Related Work 的关键产物）」；④ *Rollback Is Not Undo*（INFOCOM 2026，DOI `10.1109/INFOCOM59046.2026.11571400`，付费、需机构订阅）。⇒ **这四项的 task 设计细节，材料未给出。**
23. **同域 9 篇论文中 task 与指标的具体形态**：`R:7-9` 只给了统计口径（2/9 用外部 benchmark、0/9 跑第三方实现、惯例是重实现 + 标准信道模型 + 报 Monte Carlo 次数），**未给出任何一篇的 task 描述**。
24. **sub-field 的一份关键对照表尚缺**：`S3:66` 指明 AgentChaos / AgentDisruptBench 的用途是构建「注入故障类的**对照表**」，该表被列为 Related Work 的关键产物——⇒ **表材料未给出。**
25. **「超时后效果未知」在本领域的位置是否已被占**：`S3:64` 把 α³-Bench 定为「Gap 1 的最大风险项」，读它之前 **Gap 1 的表述不能落笔** ⇒ **结论材料未给出。**

---

## 6. 一句话回答：最值得沿用的一个 task 设计

**在这批材料里最值得沿用的是 `WirelessOpsBench / WirelessOpsAgent`（arXiv:2608.08277）的「任务契约层」，理由是它是十个文件里唯一一份被逐字节审计过、并且已被明确定义好「哪一部分可以继承、哪一部分必须自建」的 task 设计（`A10:3`、`A10:84-88`）：它的可继承部分是一套完整的、机器可判定的任务骨架——任务文本与参数、九个工具及其 `mutates_state` 标记、预算（`max_model_calls` 24 / `max_steps` 24 / `max_tokens` 32000 / `max_tool_calls` 12 / `wall_time_ms` 60000）、合法迁移与里程碑（`stage_<fam>` → `validate_evidence` → `commit_authorization` → `post_check` → `rollback`；`evidence_checked` → `policy_committed` → `post_checked`）、动作 schema 的乐观并发与风险带（`stage_id` + `expected_version`；`maximum_protected_impact` 28/40），以及七类故障作为对照故障轴（`A10:64-80`），而它的「须自建」部分（证据账本内容、`ray_tracing` CQI 提供者、runtime、scoring 谓词）恰好就是本项目已经声明要补的执行层（`A10:86`），因此沿用它是**填空而不是重造**；它的「不可声称」边界也已被写死（artifact 不含 baseline 分数、轨迹、token 数、成本与延迟，`A10:88`），这消掉了沿用时最容易翻车的一类声称；更关键的是，它的不足不是靠印象判断而是有四条独立证据（同 base 的八个 case `public_task` 逐字节相同、`public_input` 只含参数、无 gold 字段、`ray_tracing` 不在工具 schema 内，`A10:39-42`）与一条来自执行层的量化反证（只统计任务结果与重复率的评测会把 `verified_wrapper` 排为更优解，而它在强制 epoch 下代价是 510 个周期的写入从未落地，`E11:53`），这意味着「沿用它的契约 + 在它之外补执行判据」这一组合本身就是可被评审检验的论证结构，而材料里其他候选都没有同时具备「可继承清单」「须自建清单」「不可声称清单」这三件东西——NetConfArena 只给了 harness 可搬（`B6:67`）、NIKA/NetOpsBench 只被列为可对比环境（`B6:88`）、WirelessBench 只被用作不退化的旁证（`B6:87`）、六个 benchmark 整体在 (a)(b)(c) 上全为 NO（`C9:5`、`C9:88-92`）。**
