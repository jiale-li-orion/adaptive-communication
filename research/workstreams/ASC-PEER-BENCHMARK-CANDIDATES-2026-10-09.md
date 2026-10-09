# ASC Peer-Paper Benchmark Search — 2026-10-09

状态：**RESEARCH DISCOVERY / NOT SCIENTIFIC EVIDENCE / NO NEW EXPERIMENT RUN**。

## 目标与纠偏

本检索回应 Future-Choice 论文的独立泛化性疑问。现有 C 的 `uav-attention-routing` 是外部环境且有原生 deadline/battery，但 `zero-tardiness` 强制 hard completion 是我们的 evaluator interpretation，外部方法以 routing 为主。要找的是 **ASC、Goal-/Task-Oriented Semantic Communication、VoI 控制等直接相邻论文正在使用的 benchmark/task**，最好论文对应代码可运行，具备可审计的 `action→physical/evidence transition→final task outcome`。不能用泛 UAV LLM 多选题充当未来完成路径的正确性实验。

原来关于“有一篇 UAV benchmark task 正合适”的具体名称在当前本地历史中未确认。下面列的是本轮真正重新核对的公开记录，不追认成历史已选。

## 一、论文与真实可执行 benchmark 配对（优先）

### A. LogiCity + Goal-Oriented Semantic Communication for Logical Decision Making

- **原生 benchmark**：LogiCity: Advancing Neuro-Symbolic AI with Abstract Urban Simulation，NeurIPS 2024 Datasets and Benchmarks；长期城市仿真、FOL/Z3 交通规则、局部观测、动态交通 actor、决策和状态演进。官方摘要：https://proceedings.neurips.cc/paper_files/paper/2024/hash/8196be81e68289d7a9ece21ed7f5750a-Abstract-Datasets_and_Benchmarks_Track.html
- **直接同行工作**：Ahmet Faruk Saz、Faramarz Fekri，*Goal-Oriented Semantic Communication for Logical Decision Making* (2026；作者代码标注 IEEE GLOBECOM 2026)。https://arxiv.org/abs/2604.19614
- **作者直接 fork 的可执行 repo**：https://github.com/ahmetfsaz/LogiCity 。仓库 `README.md` 已核：`logicity/agents/gna.py` 是可替换 semantic evidence-selection hook，`logicity/utils/semantic_selection.py` 是 baseline objective，`config/tasks/sim/expert.yaml` 控制 `enable_gna`/`gna_selection_mode`/`gna_top_k`，`scripts/sim/run_semantic_quick_test.sh` 是轻量先导，完整实验有四种 rule set、六种 selection mode。
- **强项**：真正在可执行 SemCom 同类论文上评估谁该收到哪些逻辑证据，环境不是我们编的；与 B 的 conditional evidence/decision semantics 相接，有具体接口和同行 baseline。
- **限制**：作者实验主要是 per-decision H-DSR/A-DSR vs full-information，预算是 per-slot top-k，而原生跨时段 hard obligation / 不可逆通信机会未证实。若需要我们额外添加跨时段约束，结果身份只能写 `BENCHMARK-ADAPTED`。不能根据运行可行就声称 FutureChoice 带来原生 task gain。此候选原始仿真包含多个 traffic actors，不必采用多智能体通信算法主线；可先只研究单 ego/GNA 的局部决策接口。

### B. MDrive/CARLA + Goal-Oriented Logic-based Semantic Communication for Neuro-Symbolic Reasoning

- **原生 benchmark**：UCLA MDrive: Benchmarking Closed-Loop Cooperative Driving for End-to-End Multi-agent Systems；225 closed-loop CARLA scenarios：112 interaction、67 V2XPnP Real2Sim、46 InterDrive。官方仓库：https://github.com/ucla-mobility/MDrive ；官网：https://mdrive-challenge.github.io/
- **直接同行工作**：Saz、Xu、Fekri，*Goal-Oriented Logic-based Semantic Communication for Neuro-Symbolic Reasoning with Applications onto Autonomous Driving*（arXiv:2608.00878，2026 预印本）。https://arxiv.org/abs/2608.00878
- **作者发布完整 semantic-communication implementation**：https://github.com/ahmetfsaz/GOLBSCNSR 。仓库明示 `CARLA 0.9.12`、`tools/run_custom_eval.py`、`scenarioset/interaction`；RSU 语义选择、budgeted FOL 上下行、逻辑交通规则、车辆动作、评测与逐事件 debug 日志。
- **强项**：同时满足真实长程状态转移、受限通信选择、原生安全/完成条件；原生 benchmark 有独立维护者，引用与 reproducibility 更强。可探索同一真实场景中“当前通信内容有用但丢失未来避险路径”的可判别性。
- **限制**：CARLA/模型及多车控制系统重，通信预算主要是每 tick 预算；是否存在不能由常规 safe MPC 已覆盖的 future-choice conflict 需要验证。该预印本已有自己的 safety-aware inference / semantic strategy，需作为强 baseline 正面比较；不要因为 NeSy/ASC 看起来贴近就默认方法优越。

## 二、ASC-UAV 最直接的科学机制邻居（代码可用性待确认）

### C. Goal-Oriented Semantic Communication for ISAC-Enabled Robotic Obstacle Avoidance

- Wenjie Liu、Yansha Deng、Henk Wymeersch，IEEE Transactions on Wireless Communications 2026，DOI `10.1109/TWC.2026.3716013`，https://arxiv.org/abs/2603.02291 。
- UAV 避障任务；BS 的 KF state estimation、MD-DWA safety-aware C&C generation、E-DQN VoI scheduling 共同决定是否传 sensing/C&C，当前动作可选择静默/感知/感知+控制。作者报告 100% task success，减少 92.4% sensing/C&C signals 与 85.5% transmission timeslots。
- **最直接的 B→C 意义**：与现有 ASC value/VoI 决策在同一个通信控制接口上比较 hard future safety reachability；观察不更新、失联、资源消耗改变后续运动安全，符合 FutureChoice 需要的 causal dependencies。
- **代码状态**：已核对论文、期刊 metadata；尚未识别官方完整环境代码/任务发布。属于 `METHOD-NEIGHBOR / EXECUTION_UNVERIFIED`，不能直接以论文模拟数值当我们的 benchmark。

### D. World Model-Enabled Causal Digital Twins for Semantic Communications in Physical AI Systems (WM-CDT)

- Lingyi Wang、Tingyu Shui、Walid Saad、Pascal Adjakple，arXiv:2605.16547，https://arxiv.org/abs/2605.16547 。
- 已在 **AirSim + Sionna UAV navigation simulator** 上验证；Causal Information Value (CIV) 根据 counterfactual transmission 对 long-term return 的变化给 semantic token 估值，目标是 return-per-bit。该领域中 value / causal counterfactual baseline 的最邻近机制之一。
- 与 FutureChoice 的区分变量：`Δ expected long-horizon return` 能否替代 `∃ non-anticipative completion policy across compatible worlds`，以及 value-optimal action 在 hard completion constraints 下何时可能删光 future continuation。
- **代码状态**：按论文标注的 AirSim-Sionna 实验可定位科学 setting；GitHub repository search 未识别作者官方 release。属于 `HIGH-CONCEPTUAL_MATCH / EXECUTION_UNVERIFIED`。

### E. Safety-guaranteed and Goal-oriented Semantic Sensing, Communication, and Control for Robotics

- Wenchao Wu 等，arXiv:2603.13502，https://arxiv.org/abs/2603.13502 ，UAV target-tracking case study；安全与任务有效性双目标与 FutureChoice 直接相邻。未证实完整代码仓库；更适合正面 novelty 对照，不作为预设下一实验任务。

## 三、当前最合适的筛选结果

| 目标 | 优先对象 | 有效证据 / 阻塞 |
|---|---|---|
| **尽快接第三方 executable ASC peer task** | LogiCity + Saz/Fekri 2026 | 完整 fork、规则、选择器与实验入口已核；欠原生 future hard-completion 机制审计 |
| **最强 benchmark-native closed-loop task outcomes** | MDrive + Saz/Xu/Fekri 2026 | 225 官方 CARLA 场景、同行 SemCom implementation；运行成本高，跨时段通信资源争用需核 |
| **验证与 VoI/current action 强直接冲突** | ISAC UAV obstacle avoidance | 最强的 task/decision-interface 匹配之一；官方可执行代码未找到 |
| **正面比较 causal semantic value vs future feasibility** | WM-CDT (AirSim/Sionna UAV) | 长程反事实 value 路线非常接近；无已确认作者实验代码 |

因此：**没有理由因候选列表而重开 C seed/N；有理由引入一个“同行 SemCom 实验环境”的独立 transfer gate。** 须先在未看 FutureChoice outcomes 前确认原生任务、evaluator、行动是否可改变后续世界、通信预算生命周期和强 ordinary control。如果原生评测不区分不同后续 hard completion，那么最多得到接口外部性，不得包装为 generalized method superiority。

## 四、后续具体核查，不触动他人写作工作

1. 对 LogiCity fork 只读梳理 `main.py` → `City.update`/GNA → semantic subset → Z3 decision → transition → scores，标注哪些是官方 LogiCity 任务、哪些是 SemCom 作者 fork 的 extension，以及是否能实现 native-feasible full-action frontier。
2. 对 MDrive 复用作者 repo 的 experiment/evaluator contract，先审查 hard safety & completion evaluator 与同一 seed 的 replay determinism，之后再定运行资源。
3. WM-CDT/ISAC 两篇补作者代码发布情况；如果未公开，按 `EXECUTION_UNVERIFIED` 保留，不为了凑新评测临时复制一套自己的 AirSim 仿真并声称作者 benchmark。
4. 当前 WSL 网络路径 `rtnl_dumpit` D-state，A3 仍在安全 checkpoint 等待恢复；禁止在同宿主上执行新的大型环境安装/批量 evaluation。

**实验纪律**：候选 discovery 不是结果；一旦确定 task，另起 machine-readable freeze/experiment ID，完整保留 baseline 与原生终态 evaluator，negative / saturation 同样发布。Related Work / bib / 论文措辞交给并行会话，本文件只维护候选与执行合同。
