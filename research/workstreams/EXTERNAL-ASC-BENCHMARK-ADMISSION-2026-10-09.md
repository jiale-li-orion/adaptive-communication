# External ASC Benchmark Admission — Future-Choice Transfer

状态：**EXPLORATORY CANDIDATE SCREEN / NOT BENCHMARK ADMIT / NOT PAPER EVIDENCE**。
**2026-10-09 纠偏：此文件的 α³/UAVBench/6G-Bench 主导筛选不满足用户强调的“ASC 同类论文已经采用的任务/评测”要求。已被 [ASC-PEER-BENCHMARK-CANDIDATES-2026-10-09.md](ASC-PEER-BENCHMARK-CANDIDATES-2026-10-09.md) 的 peer-paper-first 检索结果取代。保留本文件仅作初期负候选/准入合同审计。**
日期：2026-10-09。任务来自论文泛化性审查：C 已在作者公开的 `uav-attention-routing` 环境里运行，但仍是我们自行解释零迟到 hard obligations、执行 paired 仿真的一组结果。需要额外寻找 ASC / agentic wireless 社区已经发布的 **benchmark task**，以独立任务定义与原生评价降低“方法在作者自己仿真里有效”的外部效度质疑。原会话口头回忆指向一个 UAV benchmark task；其确切 identity 尚未由先前 frozen artifact 证明，因此本文件不得冒充当时已经选定的 benchmark。

## 1. 与现有 A/B/C 的关系

- A：灾前山区应急监测的 source-grounded operational reality / anti-tailoring，冻结不动，不重新为 method 造 hard case。
- B：未来义务按 observation 条件化；set-level shared opportunities；polarized L/U 证书的 validity 与 dependency-local incremental 维护，冻结不动。
- C：外部 UAV routing 的原生动态、官方 heuristic、100-seed paired outcomes、21-seed/924-frontier exact audit 与 B→C set-MST attribution，冻结不动。它是 **已完成的 external environment validation**，但其 `zero tardiness` hard-obligation interpretation 与额外 method shield 属于我们自己的评测接口。
- 本文新增的是 **已有通信领域 benchmark task 的独立准入判定**。通过准入并先冻结选定 task/baseline/cohort/metrics 后，才允许单独建立新的 confirmatory experiment ID；当前仅筛选资料，任何 candidate 都不得从本文件直接进入 `results/CLAIMS.md`。

## 2. Method application 的硬准入条件

**I0 — Authority.** 公开第三方 task，明确任务集、作者、版本、评价方式与可复现的 test slice。任务选择在看到 FutureChoice outcomes 前完成。

**I1 — Counterfactual execution.** 同一合法 prefix 下，除官方记录的动作外还能执行其他 legal actions，并由 **独立原始环境** 产生后续 physical state、delayed observation、resource consumption；如果只有 frozen JSON trajectory / single-choice answer，此项不通过，不能声称验证 `F(h,a)`。

**I2 — Native hard goal.** Benchmark 明确任务完成条件、hard SLA/deadline/safety/mission constraints，且有可程序化核验的 official terminal/scoring semantics；若我们自行添加 deadline/obligation，必须记录为 `TRANSFER_EXTENSION`，不能冒充 benchmark-native correctness。

**I3 — Causal information boundary.** Agent 只能看到 prefix 时已到达的 evidence、合法任务修订和已知 pending state；有 observation-conditioned uncertainty 或至少两个未来条件分支；回放未来观测不得提前用于 action selection。

**I4 — Resource / opportunity coupling.** 至少一个 action 会消耗未来可共享的 transmission/energy/window/compute/control opportunity，影响剩余 task completion 的合法路径。只有「回答哪个 slice 比较好」的独立选择题，不足以实例化 `F(h,a)`。

**I5 — Controls.** 保留原 benchmark baseline/evaluator，另比较 native one-step legal action、同信息普通 constrained/receding baseline、FutureChoice L/U + exact fallback；精确正确性小规模由独立 oracle 审核。不得把时间、deadline、mission objective 写成方法有利的私有规则。

**I6 — Disclosure.** 报告原环境 vs adapter/wrapper 的字段与行级变更清单。缺失 I1/I2 的候选可以成为 **ASC interface / semantic-value diagnostic**，但不得升级为新的 external method-confirmation cohort。

## 3. 2026-10-09 候选预筛

| Candidate | 公开 task 与支持 | 当前可接受的角色 | 阻塞/下一核查 |
|---|---|---|---|
| **α³-Bench / AlphaBench** | 113k UAV multi-turn missions；6G slices、latency/loss/load、MCP/A2A actions、sensor query、network adaptation、final mission state；[repository](https://github.com/maferrag/AlphaBench) / [paper](https://arxiv.org/abs/2601.03281) | **ASC relevance first / candidate task: 6G-adaptive UAV mission**。优先检查网络降级→关键 control/reporting、slice-switching、buffering/data handover 的 hard goal 与 future opportunity conflicts | 公开仓库顶层为 episodes、figures、paper、evaluation results、README；确认有固定轨迹，不等于确认可执行不同动作后的 `env.step` 或 exact replay。**I1 未证实**；不可直接声称 run method |
| **UAVBench** | 50k physically validated UAV scenarios + 50k MCQ；schema 包含 battery, `time_budget_s`, mission, `comms.loss_windows`，见 [repository](https://github.com/maferrag/UAVBench) | 有潜力提供独立 scenario distributions / mission task specification | 公开内容证明 scenario/MCQ 和验证规则，尚未证明统一可执行 counterfactual simulator。作为 I1 待证、I2 待证 |
| **PhysAI-Bench** | 10,178 UAV decision instances；仅提供 decision 前历史、MCP/A2A、传感器和 6G 网络上下文；[paper](https://arxiv.org/abs/2609.23695) / [repository](https://github.com/maferrag/physai-bench) | 原生 prefix 信息纪律、offline decision benchmark；补 ASC task framing | 多选 decision labels 本身无法评估未选择动作造成的后续完成路径。按目前发布描述，I1 不成立 |
| **6G-Bench** | 30 task types、3,722 questions，网络语义决策、UAV intent/replanning MCQ；[repository](https://github.com/maferrag/6G-Bench) | terminology/task taxonomy 参考 | 冻结选择题，不是可交互任务生命周期；**I1 不满足** |
| **WirelessBench / WCMSA** | Mobile Service Assurance：trajectory prediction、ray tracing CQI、slice/bandwidth、QoS verification；[repository](https://github.com/jwentong/WirelessBench) | 通信侧 QoS/task evaluation 与工具接口参照 | 多步解题 workflow 预测单个问题输出，非 action 改变后续 world state；**I1 不满足** |
| **BEDI** | Published UAV agent benchmark；UE 4.27/AirSim dynamic task environment、state/action/perception APIs、task-level scoring；[repository](https://github.com/lostwolves/BEDI) / [paper](https://doi.org/10.1016/j.isprsjprs.2026.01.013) | 如果 AlphaBench 无 runnable engine，则作为可执行 external UAV task 备选 | 运行环境重量级，原生 6G/communication hard obligations 未证实。若须自造资源/义务将削弱方法验证的独立性。**I2/I4 待证** |

该表区分“相关论文 benchmark 名声”和“真正能接受其他 action 并客观裁决后果”。评价的科学对象是 **continuation feasibility**，因此两者不可混同。

## 4. 优先级与停止规则

1. **第一优先级：α³-Bench 具体任务可执行性**。定位正式 episode/schema/evaluator，并追踪 action→transition→observation 实现。查明是否提供 counterfactual simulator/API、native terminal goals、同义 action 的可重复 replay。缺任一事实则明确记 `NOT_ADMITTED`，不自行补一个作者 sim 然后说是 benchmark-native。
2. **第二优先级：可执行候选的原生任务审计**。仅在原方法外添加 FutureChoice adapter；不得修改官方 dynamics、任务 deadline、baseline scoring。若仅静态评测合法，则可做离线 prefix/decision diagnostic，但不能支持 exact safety 或 outcome claim。
3. **第三优先级：prospective extension**。有合格任务后，单独冻结任务名、release commit/hash、样本选择、action legality、hard terminal evaluator、native baseline、强普通 control、exact audit、failure taxonomy、2CPU/nice10 内存与超时合同。之后才开始运行；失败不替换任务来挑容易获益的场景。
4. **停止规则：** 找不到满足 I1+I2+I4 的独立任务，保留 C 现有外部实验证据及其 evaluator-extension 边界，论文以 `external environment transfer` 陈述；绝不为了多一个社区 benchmark 名称制造新的 synthetic outcome claim。

## 5. 项目边界与协作

Related Work、主文引用、bib/论文语言调整由并行会话管理。本工作区只负责 candidate/source capability audit、可执行性、experiment admission 与日后真正的 task-level run。当前 WSL 的 `rtnl_dumpit` 宿主机 blocker 与 A3 checkpoint 是独立问题；不得在内核网络阻塞期间启动大规模仓库下载、外部 simulator 或并发评测。
