# Agentic Emergency Communication 研究上下文

**日期：2026-09-12**  
**用途：后续继续选题、找数据、搭 benchmark、做实验、写 paper 的工作上下文。**

## 0. 当前任务

当前目标已经从“泛泛探索 agentic communication”收敛为一个直接的 paper pipeline：

**找已有 task / mother paper → 找现成数据集 → 定义 benchmark/environment → 跑 baseline → 加入成熟 agent runtime 机制 → 做实验与 ablation → 写论文。**

研究不需要重新发明 agent，也不需要在通信侧和 PHY / optimization 专家硬卷。更有价值的切口是：把 agent infra 已经较成熟的 runtime 语义带进自然灾害 / 应急通信场景，并证明现有 wireless-agent 系统在真实 disruption 下会发生系统性 execution failure。

---

## 1. 研究定位

通信方向长期聚焦于自然灾害、山区监测、应急通信、低功耗与不稳定连接。FutureComm Lab / 金石老师课题组是持续 follow 的重要来源，但不是唯一边界；选题由问题本身驱动，可以横向吸收无线通信、IoT、应急网络、DTN、mobile systems、agent systems 等工作。

当前更适合 paper 的问题空间是：

> 在自然灾害导致通信链路、网关、边缘节点和 sensing / actuation capability 持续退化、掉线、恢复的情况下，tool-using agent 如何保持长期任务的正确执行、持续推进和安全恢复？

这里的通信不可靠不是人工 fault injection，而是任务本身的现实属性。灾害、断电、山体遮挡、基础设施损坏、回传链路中断都会让 tool / capability 的可达性和结果可靠性随时间变化。

---

## 2. 我们真正有优势的部分：Agent Runtime

通信领域已经开始大量吸收 LLM agent 的 planning、tool use、workflow、reflection、resource allocation、self-healing，但当前公开工作更多集中在“agent 如何规划与调用工具”，对成熟 agent infra 中的 runtime semantics 吸收得不完整。

我们更熟悉的一层包括：

- retry semantics，而不仅是“失败后再试一次”；
- operation lifecycle；
- timeout 后的 `outcome-unknown`；
- idempotency 与副作用工具的重复执行；
- durable queue / durable execution；
- bounded replay；
- retry budget；
- head-of-line blocking；
- fairness / progress / liveness；
- heartbeat / lease；
- stale observation；
- recovery barrier；
- reconcile / verify-before-retry；
- node / process / network failure 后的 resume；
- canonical state、event log、audit、commit / rollback；
- permission、authority、side-effect class 与恢复语义的绑定。

这些机制本身不能宣称为全新贡献。新的论文价值来自：**自然灾害与应急通信给出了一类 communication-specific partial failure distribution，而现有 wireless agents 没有把这层 execution semantics 当成中心对象；我们需要给出 benchmark、runtime abstraction 和实验证据。**

---

## 3. 当前最强论文命题

推荐先用下面这个版本作为工作标题：

**Disruption-Tolerant Runtime for Tool-Using Agents in Emergency Communication Networks**

对应的论文 claim 可以写成：

> Existing agentic wireless systems mainly optimize decision quality under an assumed-available tool interface. Emergency communication exposes a different failure regime in which connectivity, observations, capabilities, and tool outcomes are intermittent and stateful. We study execution failures caused by communication-induced partial failure, introduce a disruption-tolerant runtime, and evaluate whether it preserves task progress and side-effect correctness under real or trace-driven emergency-network conditions.

这篇 paper 需要证明三件事：

1. 现有 wireless-agent runtime 在 intermittent connectivity 下会出现可重复的系统性 failure，例如 duplicate side effect、错误 retry、stale action、pending task 丢失、recovery 后错误 replay、starvation / head-of-line blocking。
2. 这些 failure 不会简单随着 LLM 更强而消失，因为问题来自 execution semantics。
3. lifecycle-aware runtime 在相同 LLM、相同 task、相同通信环境下显著改善 task completion、recovery、side-effect correctness 和 progress。

---

## 4. 最值得做的 Task

### Task A：Disruption-Tolerant Tool Execution

一个 agent 执行长期监测 / 应急任务，工具位于多个通信节点上。运行过程中节点会掉线、恢复、超时、返回 stale data 或出现 outcome unknown。

重点不在 PHY 控制，而在：

- 调用已经发出但结果没回来；
- tool 在执行过程中离线；
- tool 恢复后是否 replay；
- side-effect tool 是否被重复执行；
- observation 是否已经过期；
- pending work 是否能继续推进；
- 一个持续失败节点是否堵住整个队列；
- 恢复后是否需要 reconcile。

### Task B：Long-Horizon Emergency Workflow

用更完整的 workflow 表达灾害场景，例如：

- 持续读取关键 sensing node；
- 上传灾害监测结果；
- 主链路退化后切备用 gateway / relay / backhaul；
- 关键数据优先回传；
- 断网时 durable enqueue；
- 网络恢复后 replay / reconcile；
- 完成任务后恢复低功耗状态。

这个 task 更像真正的 agent runtime benchmark，也更容易自然纳入 mission criticality、energy、freshness。

### Task C：Self-Healing Through Reconfiguration

agent 通过已有 tool 对局部通信系统进行 reconfiguration，例如 route switch、relay activation、backhaul switching、parameter update。这里的“self-repair”优先限定为 reconfiguration / recovery，而不是宣称物理维修。

---

## 5. 可直接 follow 的 Mother Papers / Benchmark

### TopoLLM

定位：LLM + tool use + emergency network topology planning。  
价值：场景最接近自然灾害 / 应急通信，可以直接继承 story、task 和 tool-driven planning 框架。  
可改进点：把原有“工具可执行”的假设改成 intermittent / stateful execution，研究 timeout、disconnect、recovery、stale state 和 side effect。

### 6GAgentGym

定位：closed-loop wireless-agent environment，typed tools，configuration 会真正改变 network state。  
价值：适合直接继承 benchmark / environment 设计思路。  
可改进点：把 network degradation 从“环境状态变化”进一步推进到“tool execution semantics 变化”，例如 timeout、unknown outcome、duplicate delivery、tool disappearance。

### WirelessAgent / WirelessAgent++

定位：wireless agent、workflow、tool use、network slicing / service assurance。  
价值：适合作为 baseline、related work、代码参考。  
局限：和自然灾害 / emergency communication 场景距离较远，不优先作为主问题。

### α³-Bench

定位：动态 6G / UAV agent episodes，网络条件包括 latency、jitter、packet loss、throughput 等。  
价值：可能适合直接改造成 runtime failure benchmark，尤其适合 failure injection 和 trace-driven evaluation。

### 其他 related work

ICG-Restore、ComAgent、自愈 RAN、agentic wireless survey 等可以用于证明通信领域已经进入 agentic planning / self-healing，但还没有系统覆盖成熟 runtime execution semantics。

---

## 6. 现成数据集 / Trace 候选

当前优先级最高的是能直接产生 **degradation → outage → recovery** 生命周期的数据。

### FEMA TEMPO Communication Impacts

记录灾害事件期间通信基础设施受影响情况，可按时间观察 cell site outage / recovery，并区分 damage、power、transport 等原因。

适合：infrastructure lifecycle、node availability、failure / recovery episode。

### ITU Disaster Connectivity Map

覆盖灾害期间 connectivity、latency、throughput、位置和时间等信息。

适合：link degradation / network partition / recovery。  
需要进一步确认 bulk raw data 是否足够开放、粒度是否适合 benchmark。

### SitkaNet

真实滑坡监测部署，LoRa、低功耗 sensor、复杂地形，存在不可靠传输。

适合：山区灾前监测 mission、sensor / hub lifecycle、低功耗场景。  
需要进一步检查是否能获得足够细粒度的通信 trace。

### Avalanche LoRa / SAR Dataset

意大利山区 / 雪崩场景，包含 RSSI、SNR、distance、GPS、snow depth 等真实无线测量。

适合：把 capability 从简单 online/offline 扩展成 degraded → timeout → unavailable。  
也适合建立真实的通信质量变化分布。

### Long-term LoRaWAN Metadata

长期 RSSI、SNR、spreading factor、frequency、airtime、天气等。

适合：建立正常波动与异常退化的长期 baseline。

### Landslide LoRaWAN Dataset

包含滑坡监测 sensor 数据与 LoRaWAN 系统。

适合：hazard context。  
需要确认是否包含完整链路 trace；如果只有 sensor value，不能单独承担 runtime failure benchmark。

---

## 7. Benchmark 的最小设计

每个 episode 由以下内容组成：

- scenario / mission；
- node 与 capability 初始状态；
- 真实或 trace-driven 的 network / outage trajectory；
- tool schema；
- agent observation；
- tool invocation；
- runtime event；
- result / timeout / disconnect / stale / unknown outcome；
- recovery event；
- terminal mission outcome。

tool 不需要很多，第一版十几个就够。可以从下面这些开始：

- `sensor.read`
- `sensor.status`
- `battery.get`
- `link.metrics`
- `gateway.status`
- `buffer.status`
- `buffer.flush`
- `route.switch`
- `relay.enable`
- `backhaul.switch`
- `sampling.set_rate`
- `radio.configure`

其中 read-only tool、state-mutating tool、side-effect tool 要分开，因为恢复语义不同。

---

## 8. Runtime Failure Model

建议显式定义 operation lifecycle，而不是只返回 success / fail。

最低限度可以区分：

- `not_started`
- `running`
- `committed`
- `failed`
- `retryable`
- `timeout`
- `outcome_unknown`
- `stale_result`
- `unavailable`
- `recovering`
- `compensating`

重点 failure case：

- RPC 发出后节点掉线；
- action 已执行但 ACK 丢失；
- timeout 后 blind retry 导致重复副作用；
- capability 掉线后 pending invocation 被遗忘；
- stale observation 被当作当前事实；
- node 恢复后 replay 顺序错误；
- 一个持续失败 operation 耗尽 retry budget；
- FIFO replay 导致 critical task starvation；
- gateway / relay flapping；
- network partition 后 state divergence；
- long-running workflow 中 agent process 或 coordinator 重启。

---

## 9. Method 最小集合

不要一上来做一个巨大 runtime。第一版可以只做四到六个机制：

1. operation state machine；
2. idempotency-aware retry；
3. lease / lifecycle-aware capability registry；
4. bounded + fair replay；
5. stale-state / freshness guard；
6. reconcile / verify-before-retry。

如果这几项已经能显著改善真实 disaster trace 上的任务完成率和副作用正确性，就足够支撑论文。

---

## 10. Baseline

至少需要：

- ordinary ReAct / tool-using agent；
- naive retry；
- fixed retry；
- exponential backoff；
- static tool surface；
- dynamic tool surface but no lifecycle-aware recovery；
- full runtime method。

再做 ablation：

- 去掉 idempotency；
- 去掉 freshness；
- 去掉 lease；
- 去掉 bounded replay；
- 去掉 fair scheduling；
- 去掉 reconcile。

这样可以把增益来源拆清楚。

---

## 11. Metrics

Agent / runtime 侧优先：

- task completion rate；
- recovery latency；
- duplicate side effects；
- lost operations；
- unsafe replay；
- stale-state decisions；
- pending task loss；
- starvation / head-of-line blocking；
- tool-call overhead；
- progress / liveness。

通信 / mission 侧辅助：

- critical data delivery ratio；
- data freshness / AoI；
- outage duration；
- communication overhead；
- energy consumption；
- critical sensor coverage。

论文主结果应该让 reviewer 看清：runtime 机制改变了 execution correctness，而不是仅仅多发了几次 tool call。

---

## 12. Novelty Boundary

不能把这些单独写成新贡献：

- retry；
- idempotency；
- heartbeat；
- durable queue；
- event log；
- lifecycle state machine。

这些在 distributed systems / agent infra 里都有成熟来源。

真正需要形成的新 contribution 是：

- communication-specific failure model；
- emergency communication task / benchmark；
- 将 capability lifecycle 与 intermittent connectivity、energy、freshness、mission criticality 结合；
- 在 wireless-agent baseline 上证明 runtime semantics failure；
- 给出一套适用于 emergency communication agent 的 runtime abstraction；
- trace-driven / real-data empirical evidence。

paper 的话术要避免“我们首次给 agent 加 retry”，而应该是“现有 wireless agents 缺少适配 communication-induced partial failure 的 execution semantics”。

---

## 13. 与通信研究的关系

这篇工作不需要 LLM 直接接管高速 PHY 控制。PHY / MAC 的毫秒级或更快闭环仍然由传统算法承担。

Agent 更适合较慢时间尺度：

- tool / node availability；
- link degradation diagnosis；
- routing / backhaul switch；
- sensing / communication priority；
- mission-level scheduling；
- recovery；
- capability orchestration；
- data / computation placement。

自然灾害 / emergency communication 的价值在于：runtime failure 不是人为制造的边角情况，而是系统正常运行时就必须面对的基本条件。

---

## 14. 投稿方向

当前最匹配的 venue 方向：

- **SenSys**：最适合 sensor / wireless / extreme environment / benchmark / systems；
- **MobiSys**：如果 runtime implementation 和真实系统做得比较厚；
- **MobiCom**：如果 wireless system 和真实网络实验很强；
- **ICC / Globecom / WCNC**：如果更偏通信 benchmark / agentic network management；
- **IEEE TMC**：如果最后成为完整 mobile / distributed runtime paper；
- **IEEE TNSM**：如果更偏 autonomous network/service management 与 recovery。

具体 deadline 后续准备投稿时重新查，不在此文档固定。

---

## 15. 当前 paper pipeline

下一步按这个顺序推进：

1. 精读 TopoLLM、6GAgentGym、WirelessAgent++，确认现有 task / environment / tool execution 假设；
2. 下载并检查 FEMA TEMPO、Avalanche LoRa、SitkaNet 等数据；
3. 确认哪个数据能产生最自然的 lifecycle episode；
4. 定义最小 runtime failure model；
5. 搭一个 trace-replay environment；
6. 跑普通 tool agent + naive retry baseline；
7. 先证明现有 runtime 确实系统性失败；
8. 加 lifecycle-aware runtime；
9. 做 ablation；
10. 再决定是否需要更复杂的 agent method；
11. 写 Introduction 时从“wireless-agent 已有 planning / orchestration，但 emergency communication 暴露 execution semantics gap”切入。

最重要的 go / no-go 判断不是“故事听起来新不新”，而是：

> 能不能用现成数据和现有 wireless-agent baseline，稳定复现一批 runtime failure，并让成熟 agent-infra 机制显著修复这些 failure。

如果能，paper 基本成立。

---

## 16. 通信学习上下文

用户当前按通信零基础学习，但学校正在上 signal processing。通信学习目标不是考试，而是能够：

- 看懂通信课题；
- 识别研究对象和核心问题；
- 看懂主要技术机制；
- 判断论文 contribution 与假设；
- 服务当前 communication paper。

教学要求：

- 对照经典教材和课程，不自己发明知识树；
- 当前无线通信主线可参考 Chalmers SSY135（Henk Wymeersch）；
- 参考教材 Goldsmith《Wireless Communications》；
- 辅助参考 Tse & Viswanath《Fundamentals of Wireless Communication》、Proakis；
- 每次只讲一个层级；
- 不把不同抽象层次对象混在同一列表；
- 解释“为什么”以后再引入术语和公式；
- 用连续 prose，少用文本框、单词堆叠和纯排版式箭头。

目前已经学到 wireless channel 的基础概念：LoS/NLoS、path loss、shadowing、multipath、small-scale fading，并开始看 SSY135 的离散时变多径信道模型：

\[
y_k=\sum_l h_{l,k}x_{k-l}+w_k+i_k.
\]

---

## 17. 研究边界与长期偏好

- FutureComm Lab / 金石老师课题组长期 follow，但不限制选题边界；
- 重点仍然聚焦通信方向；
- 自然灾害、山区监测、应急通信是当前最强应用场景；
- 可以吸收 agent infra、mobile systems、distributed systems、DTN、IoT 等成熟思想；
- 目标是快速形成能验证、能实验、能投稿的 research artifact，而不是无限扩展理论框架；
- 优先找已有 task、已有数据、已有 baseline，再加独特 runtime contribution。
