# Reliable Execution of Agentic Monitoring Workflows under Intermittent Connectivity and Energy Constraints

**灾前山区滑坡与泥石流监测：供电受限、LoRa 接入与间歇回传下的任务执行。**

更新：2026-09-19。当前主线收敛为 **Execution-Grounded Obligation Runtime**：以监测义务关联采集、配置、缓存、回传与确认，研究持续执行何时仍有任务价值，以及哪个位置能够及时约束或释放其资源。

**当前阶段：已有可复现的执行机制正结果，正在修订证据边界并核验相对成熟组合的独立增量。** 统一 runtime 是已采纳的组织与设计方向，完整接口和方法新颖性仍待验证；论文 v0.6 是工作稿。

## 当前入口

| 阅读目的 | 入口 |
|---|---|
| 方法怎样收敛、哪些判断保留 | [doc52：Obligation Runtime 收敛评估](docs/s7-method/v1.2/52-runtime-convergence-assessment-2026-09-19.md) |
| 当前证据可信到什么程度 | [doc51：v0.6 独立审查](docs/s7-method/v1.2/51-independent-review-paper-v06-2026-09-19.md) |
| 下一步具体做什么 | [最小执行计划](docs/s8-report/review-v0.6/experiment_todo.md)、[修订表](docs/s8-report/review-v0.6/revision_log.md) |
| 查看论文 | [main.pdf](docs/s8-report/latex/main.pdf)、[LaTeX 与构建说明](docs/s8-report/latex/README.md)；正文尚未落实 doc51 的全部修订 |
| 核对原始证据 | [审计数据](docs/s8-report/review-v0.6/evidence.json)、[结果索引](results/README.md)、[数据与来源](data/README.md) |

## 场景与任务边界

- 保持灾前监测范围；风险等级和任务授权由外部给定，不训练滑坡预测器，不把监测服务改善解释为减少伤亡。
- 参考链路为节点 → LoRa/Class A → 现场网关 → 间歇主回传 → 中心。v1.2 在网关加入有来源依据的北斗短报文备用能力；部署规模、容量、机会与能量数值按具体运行规格声明。
- 各方法共享现场自治、外生义务、设备能力和资源预算。Agent 不能删除失约义务或改分母；成熟规则、配置管理与本地安全能力进入公平对照。
- 决策只使用所在位置在当时实际收到的信息；被动遥测允许存在，不提供隐藏健康旁路或未来故障真值。信息不足时保留 `unknown`。
- 场景需求依据见 [s2 决策](docs/s2-scenario/pre-disaster-runtime-decision-2026-09-12.md)与[来源台账](docs/s7-method/task-design/source-audit-2026-09-13.md)。基础任务见 [Task v1.1](docs/s7-method/task-contract-v1.1.md)；备用能力见 [v1.2 来源审计](docs/s7-method/v1.2/01-actuator-source-audit-2026-09-14.md)与[部署卡](docs/s7-method/v1.2/09-deployment-card-joint-2026-09-15.md)；任务变更及其修订见 [doc35](docs/s7-method/v1.2/35-mission-change-freeze-2026-09-16.md)、[doc39](docs/s7-method/v1.2/39-prereq-fix-and-r24-2026-09-18.md)、[doc51](docs/s7-method/v1.2/51-independent-review-paper-v06-2026-09-19.md)。早期部署卡不替代各实验的实际配置。

## 当前结果与主张

| 内容 | 已有证据 | 当前解释 |
|---|---|---|
| 节点期限清理 `deadline_purge` | r37e 十种子相对 FIFO：服务均值 **+4.21 个百分点**，中断按期交付 **2.52×**；doc51 独立复现 seed0 `3025/7560 → 3267/7560` | 给定端到端确认/FIFO 缓存模型内的正结果保留；相对同期限普通 expiry 的增量尚未证明 |
| 本地执行位置 | R39 所测三种子内，本地夜间规则消除死亡 | 支持条件性的部署位置效果；未证明普遍安全不变量 |
| 真实 Agent 三臂 | r38 已有 **11 条轨迹、1089 个决策**；服务与死亡读数可对账 | A1 是额外规则、常量与证书文本的输入包；独立证书收益仍需公平普通规则对照 |
| 可行性投影与段归因 | 有条件的槽几何判定、离线执行链诊断 | 在线证据边界待修：r32 使用全局/未来信息；r33 提前量依赖已知不可用区间 |

数字来源：[r37e 十种子报告](docs/s7-method/v1.2/46-r37e-full-seed-sweep-2026-09-19.md)、[R39 位置对照](docs/s7-method/v1.2/48-execution-locality-layered-runtime-r39-2026-09-19.md)、[r38 原始汇总](results/agent_traces/r38_three_arm_summary.json)。这些历史报告的解释以 doc51 修订为准；十种子 CI 本轮未全量重跑。

以下旧结论不再作为当前证据：**固定资源下任何调度器都无空间；合法在线归因 100%；r38 零回退；24/19 次已核实的配置生效谎报；A0-structured 已排除普通专家规则解释。** 原始 trace 有 52 次解析回退，声明评分需要语义重标。研究执行层不依赖先证明调度空间已封闭。

## 方法收敛与下一步

统一对象为 obligation；围绕三个问题组织设计：当前证据支持怎样的履约判断、哪些执行状态应保留或释放、约束能在哪个位置及时生效。**完整任务无法诊断时，局部证据仍可能足以支持停止无价值重传或限制持续耗电。** 这是待验证的系统设计方向。

按以下顺序推进，不再增加第四个机制或扩大场景：

1. **修已有证据。** 重标现有 Agent 声明，分开解析回退与策略错误；修在线可见性，报告 unknown 与可判定部分可靠性。先用现有轨迹，不新增模型调用。
2. **判别普通机制能否覆盖。** 核对 `deadline_purge` 与同期限 expiry 的决策等价性；普通对照共享本地能量门、配置确认、原始常量及输出协议。固定 planner 后，定位 runtime 是否仍改变处置和实际资源消耗。
3. **有剩余机制再做小对照。** 落盘“合法证据 → 不同处置 → 资源变化 → 服务或损害变化”的见证，同时报告误释放和有益动作误拒；再决定有限真实 Agent 验证。
4. **统一文稿。** 按最终被支持的结果改摘要、方法、表格与讨论。回归通过、增加图表或方法命名不替代机制验证。

具体实验编号、输入输出和停止条件见[最小执行计划](docs/s8-report/review-v0.6/experiment_todo.md)。

## 代码与复现

| 目录 | 用途 |
|---|---|
| `code/v3joint/` | 当前联合通信实验、任务视图、Agent 接入、r37–r39 与联合层检查 |
| `code/instance/` | 节点、网关、能量、外生义务与评分基础实现 |
| `code/physics/`、`code/analysis/` | 地形/传播模型、轨迹拟合与分析工具 |
| `code/runtime/`、`code/monitoring/`、`code/experiments/` | 早期执行语义与业务仿真、历史对照和回归检查；结果不自动迁入当前任务 |
| `docs/s7-method/` | 任务契约、实例、方法推导与逐轮判别 |
| `docs/s8-report/` | 草稿、审查与进度日志 |
| `results/`、`data/` | 结果索引及原始来源；大体积数据按获取说明准备 |

在仓库根目录运行以下检查，均不调用 LLM：

```bash
python3 code/run_checks.py --quiet
python3 code/v3joint/test_joint.py
python3 docs/s8-report/review-v0.6/audit_traces.py
```

前两项分别检查 18 个回归入口和 5 个联合层锚点；第三项只读已保存的 r38 轨迹并输出 JSON。检查通过不证明论文主张成立。

脚本与依赖见[代码索引](code/README.md)，数据准备见[复现说明](data/REPRODUCE.md)。十种子期限清理实验入口为 [r37e_full_seeds.py](code/v3joint/r37e_full_seeds.py)，其参数和指标见对应 r37e 报告；不随日常文档检查自动重跑。真实模型实验需要另行配置凭据并计入请求、重试与解析账。

## 历史与决策索引

README 只呈现当前状态，不再追加多轮“最新进展”。历史编号、原文和被推翻的结论均保留：

- [早期状态归档索引](docs/早期状态/README.md)：包含本轮移出的 **1,525 行旧 README** 与旧论文目录说明，标明来源提交 `e8ff1c4`。
- [决策记录 D1–D54](docs/早期状态/2026-09-19-README-history.md#decisions)：保留原编号和取代关系；其中的历史架构、数字与待办不自动成为当前约束。
- [进度与审计日志](docs/s8-report/progress-log.md)：既有 `§7.x` 引用仍指向此处。
- [作废结果清单](results/_withdrawn/MANIFEST.md)：解释结果撤销及替代关系，归档不等于重新认可旧读数。

后续更新将最新结论写回本文件，阶段过程落到具名文档；引用历史读数时，同时检查后续审查是否改变了其适用范围。
