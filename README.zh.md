中文 | [English](README.md)

> **当前工作方向（探索中）。** 当前主线是**Evidence-Grounded Closed-Loop Agentic Communication**。方法分两层：①把现有通信 Data Plane 的 node/gateway/center/执行事件组织成带 provenance、owner、time、revision、freshness/reachability/status 的 **Evidence World**；②把 benchmark/业务层 **Operational Task** 编译成自包含的 **Runtime TaskContract / TaskRun**，由 `ContextManifest + Capability` 支撑多轮 reasoning，并把 evidence-use tool 与 communication-device tool 统一进同一 typed capability runtime。当前实验设计 authority 见 [Experiment Design v1](research/EXPERIMENT-DESIGN-v1.md)，建设顺序见 [ROADMAP](research/ROADMAP.md)；[CLAIMS](results/CLAIMS.md) 仍只持有历史冻结实验主张。

# 间歇回传下灾前监测的本地通信控制

研究电池与光伏供电的山区地灾监测网：LoRaWAN Class A 节点接入现场网关，蜂窝主回传配北斗短报文备用；备用仅上行，控制下行会随主回传中断。任务与预警等级由外部授权，系统负责监测要求的通信执行。

**原系统论文主线（已收敛为当前研究底座）：失联后持续执行的通信状态，怎样依靠现场证据得到正确处置。** 未确认记录会继续占用重传批次，已安装密采配置会继续耗电；中心即使做出正确判断，也可能因控制路径中断而无法执行。此前工作围绕这些物理后果研究源端期限释放、本地回退、分段执行证据与控制路径失效，并形成了当前 simulator、执行机制、信息边界和结果台账。相关结论继续按 [CLAIMS](results/CLAIMS.md) 的既有范围成立，也继续作为后续 Agent 研究必须复用的共同底座。

**原系统论文阶段（历史状态）：系统论文工作稿。** 这一阶段已经得到组件级正结果，同时确认配置租约、单节点停止、保留视界等候选不承担新算法主张；完整 runtime 相对同组件普通组合的独立增量、有限迁移验证与匹配能力 Agent 验证当时仍未闭合。该阶段的设计取舍、负结果和未完成项继续保存在 [论文闭环计划](paper/RESEARCH_PLAN.md) 与 [CLAIMS](results/CLAIMS.md) 中，不因当前方向演进而删除。

**当前研究主线：在上述同一场景、数据、通信能力和执行底座上，构造 Evidence World 与完整 Agent Runtime。** benchmark 层先定义 Operational Task，例如持续监测、风险升级、主回传中断维持、能源受限监测和恢复收口；harness 再把它编译成 Runtime TaskContract，组装 Context、发起多轮 evidence/device capability use，并将 action 真实作用到通信系统。最终同时评价通信结果（obligation delivery、latency、energy、backup/DtS cost、config execution）与 Agent runtime（Task grounding、EvidenceNeed、capability selection/arguments、Context sufficiency、stop/policy/failure attribution）。

## 1. 论文与阅读入口

| 内容 | 入口 |
|---|---|
| 中文稿 | [PDF](paper/zh/main.pdf) · [LaTeX](paper/zh/main.tex) |
| 英文稿 | [PDF](paper/en/main.pdf) · [LaTeX](paper/en/main.tex) |
| 当前 Agent 实验设计 | [Experiment Design v1](research/EXPERIMENT-DESIGN-v1.md) · [research/README](research/README.md) · [ROADMAP](research/ROADMAP.md) |
| 系统论文闭环计划（历史阶段） | [RESEARCH_PLAN](paper/RESEARCH_PLAN.md) |
| 逐主张复现 | [artifact/AE.md](artifact/AE.md) |
| 结果来源 / 主张状态 / 部署条件 | [结果登记](results/README.md) · [CLAIMS](results/CLAIMS.md) · [spec](spec/README.md) |

## 2. 已收敛的技术与证据

**基本单位是监测义务及其执行状态。** 一条义务需要窗口内的合格样本，经 LoRa 到网关，再在期限内回传至中心。记录保留、配置生效、网关听到与中心完成分别记账。缺少某一段证据时保留 unknown。

**局部处置可以先于完整诊断。** 网关未必分得清「没采」和「采了但尚未听到」，源端仍可凭已知期限停止过期记录重传；本地回退可使用已有授权与自身电量，不等待中心通过故障链路降档。处置位置同时受证据可得、执行权限和剩余反应时间约束。

| 技术对象 | 当前证据支持什么 | 在论文中的作用 |
|---|---|---|
| 源端期限释放与跨段保留责任 | 标准 expiry 释放源缓存；仅在网关停发可能反压接入 | 主要系统正结果（C2/C3） |
| 配置回退的执行位置 | 本地普通保护能处理中心无法及时执行的降档；普通组合覆盖已测停止问题 | 位置原则与适用边界（C5/C6/C9） |
| 部分可观测的执行证据 | 合法在线归因只能覆盖部分义务；接入收据不能代替回传或完成证据 | 接口设计及 Agent 失效分析（C4/C7/C8） |

系统由成熟原语组成。新的系统价值需要在组合、执行位置和实际业务后果上成立；模块改名、统一对象或增加 Agent 均不自动构成方法贡献。

## 3. 代表结果

- **源端到期**：修正网关 deadline 边界后，十种子相对 FIFO，按期服务配对 **+3.59 个百分点**，95% CI **[+3.00, +4.19]**；中断按期交付 **2009→4227（2.10 倍）**，过期备份记录 **2100→0**，死亡 **12→0**。这是标准逐记录到期在所测缓存模型中的安置效果，不是新的删除算法。[C3 结果](results/r37e_full_seeds.json)
- **配置终止**：固定 TTL 在两个受检相位覆盖候选的存活与黄级交付工作点。候选能量门没有独立收益；单节点声明模型中的普通组合也追平所扫风险权重下的同信息精确停止参照。
  [配置矩阵](results/c5_matrix.json) · [序列参照](results/c5_seqref.json)
- **在线可知范围**：修正 deadline 边界后，任务表到达时网关凭当时合法证据可归因 **1114/2112 条（52.7%）**，已判定部分全对，**998 条**保持 unknown。这支持局部证据接口，不意味着任意时刻均能完整诊断。[C7 结果](results/r40_local_attribution.json)
- **Agent 接口**：真实模型轨迹暴露了将 LoRa 接入收据当作回传状态的双向错误。v5 离线重放改善声明；独立的端到端机制增益尚未验证。[C8 入口](results/CLAIMS.md)

资源放宽实验用于说明容量与能源压力，不作为所有调度器的上界。C10 到期边界修正归入实现语义，后续比较使用修正后的普通 expiry。

下表是 [CLAIMS](results/CLAIMS.md) 的受检投影，不另行维护主张状态。

| 主张 | 范围 | 状态 |
|---|---|---|
| C1 | 资源放宽的反事实刻画 | scoped-negative |
| C2 | 与普通记录到期等价 | supported |
| C3 | 源端到期的跨段安置效果 | supported |
| C4 | 时间感知的失败归因 | supported |
| C5 | 已测配置租约候选 | scoped-negative |
| C6 | 本地执行位置 | supported |
| C7 | 部分在线归因 | supported |
| C8 | 真实 Agent 接口失效 | formative |
| C9 | 同信息单节点停止 | scoped-negative |
| C10 | 到期边界修正 | supported |
| C11 | 反向确认延迟界（条件性）；R1 关闭理由已撤回 | supported |

## 4. 当前实验阶段

当前不再继续寻找新的 toy perception case 作为开工前置条件，直接进入统一实验基础设施：`Operational Task -> Runtime TaskContract -> Evidence World / Context -> capability use -> physical execution -> Communication × Agent metrics`。09-28～10-01 的 action-closure 与 resource negative results继续保留，用于 benchmark validity、ordinary-baseline 与 ablation，不再阻塞 harness、LLM benchmark 或 full-sim 实验。

当前 pre-API 实验基础设施已经闭环。O1–O6 Operational Task 均可通过同一 typed runtime/full simulator 执行；O2 的 global/localized R3、R0/R1/R2 replay、ModelRequest/Attempt/Usage ledger、upstream/planner gold replacement 与 attribution evaluator 已落地。Agent 侧已有 deterministic comply、task-conditioned evidence-aware、diagnosis-first、fixed-order eager、generic-ReAct 五臂 5-seed baseline matrix；通信侧已有 Local、AoI、EnergyAware、mission-comply、backup EDF/maxcov 与 evaluator-only dynamic/delivery oracle 的 5-seed matrix。NASA POWER 2022/2023/2024 source-period、weather/outage/scope/owner/scale 五轴 robustness、S14/Qili source-derived Task transfer 与三种 model-context frozen inputs 也已通过审计。当前没有用 scripted backend 冒充模型结果；下一阶段直接接真实 API，先做 R1 frozen-input diagnosis，再进入 R3 physical consequence 与 failure attribution。

## 5. 场景与能力边界

部署、数据与参数以 [实例清单](spec/instance-v1-manifest.md) 为准。当前主点为十四节点、有限 Class A 接收窗口和稀疏短报文回传。采样/上报周期可远程配置；风险判断、删除困难义务、自动获批额外卫星资源均不属于动作空间。模型使用同步且不占空口的中心 ACK、合成日照/云遮与主配置下的吸收态掉电；这些是实装外推边界。

Episode I 研究升级任务、回传中断与恢复；Episode II 用两个授权升降级相位隔离配置回退。精确停止参照采用公开任务表、声明能量过程和量化单节点状态，不能外推为未知任务或完整网络的最优性结论。

## 6. 构建与复现

```bash
make deps
make data
make check
make tables ARGS=--check
make agentic-preapi
make paper
```

两份稿件共享 [refs.bib](paper/refs.bib)，英文由 pdflatex 构建，中文由 XeTeX 构建。[构建说明](paper/README.md)列出环境与生成链。论文表格和事实宏由 `scripts/make_tables.py` 从结果文件生成，不手改 `paper/generated/`。

`make check` 包括仿真、执行语义、主张、表格、序列参照、Agent runtime 与联合层锚点；不调用模型 API。`make agentic-preapi` 统一重跑当前所有无需模型凭据的 Agent/communication baseline、source-period、robustness、task-transfer、attribution 与 model-input freeze，并从结果 JSON 自动刷新研究/结果文档。逐主张命令与冻结参考见 [artifact/AE.md](artifact/AE.md) 和 [results/reference](results/reference/README.md)。真实模型调用需要另外配置 endpoint/key；缺凭据时 runner 显式失败，不回退 scripted backend。

## 7. 仓库结构

| 路径 | 内容 |
|---|---|
| `paper/` | 双语稿件、PDF、书目、生成表格与当前论文计划 |
| `spec/` | 部署、信息边界与生效实验契约 |
| `code/instance/`、`code/v3joint/` | 当前物理仿真、联合通信机制与 Agent 接口 |
| `code/analysis/`、`code/experiments/` | 诊断、复现和检查 |
| `results/` | 登记结果、唯一主张状态、冻结参考与撤回档案 |
| `artifact/`、`scripts/` | 评审入口、依赖获取、结果到论文的生成链 |

本仓库遵循 [论文仓库规范](PAPER-REPO-STANDARD.zh.md)。历史结论保存在 Git 与撤回档案；本地 `docs/` 是研究过程材料，不随发布。入口页只呈现当前研究状态。
