# 文档索引

`README.md` 是权威文档：命题、定位、实体分类、现状盘点、系统模型、方法与结果都在那里。本目录存放支撑其结论的材料。

## 场景与数据

| 文件 | 内容 |
|---|---|
| `s2-scenario/geohazard-china-context.md` | 中国地灾监测的政策与产业背景，含政策文号、北斗约束、低温物理与工程实况 |
| `s2-scenario/lowpower-mountain-recon.md` | 低功耗山区通信的可用数据与仿真工具链盘点 |
| `s2-scenario/evidence/sub-annual-report-policy.md` | 政策文本的一手摘录与核验 |
| `s2-scenario/evidence/sub-datasets.md` | 公开数据集的可用性核验 |
| `s2-scenario/evidence/sub-link-physics.md` | 链路物理参数的出处核验 |
| `s2-scenario/evidence/sub-coverage-enhancement.md` | **覆盖增强与地形传播的增量证据**：RIS 山区实测缺失的否定性证据、ITM 现代使用与误差标定（URSI 2015：均值 −1.4 dB / SD 8.4 dB）、射线追踪标定要求、8 条定位缺口（G1 季节性地形 × 长期可用性预测、G3 ITM 未用于 LPWAN） |

## 物理模型与故障源

| 文件 | 内容 |
|---|---|
| `s4-fault-source/simulation-feasibility.md` | 真实地形、信道与能量模型的实测结果、工具链，以及实现中修掉的错误记录 |
| `s4-fault-source/dataset-recon.md` | 数据集普查与排序，含负面结论 |

## 系统模型

| 文件 | 内容 |
|---|---|
| `s6-model/system-model.md` | 论文 Section II 的完整版：部署几何、两段式信道、能量模型、业务参数、失效与中断模型、指标定义。每条参数标注证据层 |
| `s6-model/downlink-opportunity.md` | **控制面的可达机会**：LoRaWAN Class A 接收窗口、NB-IoT PSM（TS 23.682 cl 4.5.4 原文：PSM 终端对下行不可达）、eDRX/PTW、LwM2M Queue Mode、LoRa Alliance FUOTA 套件（TS003/004/005）的标准依据。**改变 system-model 的信道模型**：下行机会由节点唤醒时刻表决定，与重试预算无关 |
| `s6-model/evaluation-contract.md` | **评测契约**：强基线（Device Shadow / LwM2M Queue Mode / CoAP 去重）、5 项基线结构、实验 A/B/C 编排、7 项**业务损害指标**、**两个分母**（全部需求 vs 物理上至少有一次机会）、代码层面 7 处测量缺陷（含 `energy.py` 发电量约 2 倍）、继续投入的可证伪判据 |

## 方法

| 文件 | 内容 |
|---|---|
| `s7-method/execution-runtime.md` | 论文 Section III 的完整版：执行歧义模型、三个正交维度、操作生命周期、调和与结算、三条性质与主图 |
| `s7-method/task-and-action-space.md` | **任务与动作空间**：E1–E7 证据表（含 Kumar 等、重庆官方设备通信接口 `0042`/`0045`/`00D0`）、断点→手段映射（作为 runtime 的执行资源池）、需求表述与五条可检验命题、**7 个动作及完成判据**、两条评分纪律（不同语义不能统一按"恰好一次"打分；配置冲突域须限定为单资源）、完全灾前最小案例 |

## 新颖性与定位

| 文件 | 内容 |
|---|---|
| `s3-novelty/prior-art-agent-runtime.md` | Agent runtime 执行语义的先行工作侦察、已被占据的机制清单、可主张的空白 |
| `s3-novelty/agent-assumption-audit.md` | **Agent 执行假设审计**：四个判定问题（工具可靠？状态可观测？超时后效果未知？分钟–小时级观测延迟？）逐篇核对；7 条空白，其中 G5「观测通道 ≡ 控制通道」最干净；必读项仍缺 4/6（**α³-Bench 为 Gap 1 最大风险项**） |
| `s3-novelty/paper-strategy-review.md` | **论文策略复审**：两个结构性洞（多实体集合未实例化、主实验无 agent）、`energy.py` 发电量约 2 倍的代码缺陷（压在 93.7% 这个数字上）、venue 建议（主论文 TNSM + SenSys benchmark 短论文） |

## 仓库之外

`docs/s1-input/` 与调研过程中产生的内部材料保留在本地，不纳入版本控制。
