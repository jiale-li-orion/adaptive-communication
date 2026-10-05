# Layer-1 Decision Benchmark v0.2 — Normative Contract

状态：**RESEARCH_FROZEN / PUBLIC_RELEASE_PENDING**
适用谱系：`v0.2-retry-legality`
当前状态 owner：`research/benchmark/LAYER1-AUTHORITY.md`
release gate owner：`research/benchmark/BENCHMARK-QUALITY-GATE.v0.1.md`

本规范固定 Layer 1 当前版本“测什么、允许什么、怎样判定成功、做到什么程度才算毕业”。它不拥有研究历史，不记录 generator 推演过程，也不定义 Layer 2/3 算法。

## 1. Research construct

Layer 1 测量的是：

> 在现实来源可追溯的 Operational Obligation 下，当通信状态部分可见、证据会老化、主动取证具有真实成本、链路与资源机会有限时，policy 能否依据新证据连续调整行动，并保持未来义务仍可满足。

主 Family：

- `T1 Monitoring Information Continuity`：MAIN；
- `T2 Warning Delivery & Response Handoff`：boundary Family，当前 actor-chain environment 仍为 `SIMULATOR_GAP`。

Family identity 由四项决定：protected operational subject、completion predicate、authority owner/chain、lifecycle scope。warning level、outage/reconnect、fallback、probe、cache、radio type 等默认只是 regime / capability / hardness axis。

## 2. Agentic-case minimum threshold

承担 Agentic Communication 主 claim 的 case 必须同时满足：

1. **Sequential interdependence**：后续动作依赖前序 action / execution 产生的新 observation；
2. **Partial observability**：关键当前状态不直接暴露给 policy；
3. **Adaptive strategy formation**：新 evidence 可能改变后续 strategy，而固定 open-loop action sequence 不能等价替代。

正式 release 必须报告 single-shot / open-loop reducibility audit。若一次性给出当前全部合法 observation 后，一轮静态选择或固定 open-loop sequence 已接近 observation-matched oracle，则该 case 降为 reasoning / conformance，不承担 Agentic 主 claim。

## 3. Environment contract

环境至少包含：

- source-grounded operational obligations；
- hidden physical/service state；
- intermittent communication opportunities；
- finite resource / backup budget；
- obligation release / deadline；
- execution lifecycle；
- failure / recovery；
- lawful observation boundary。

当前 v0.2 hard subset 的主要结构为：

- `FINITE_CROSSING_WINDOWS`；
- `GATEWAY_SUMMARY_QUERY`；
- overlapping obligations 3/4；
- train/dev/test hard signatures = 16/18/7。

这些是 v0.2 hardness survivor 的结果，不重新定义 Family。

## 4. Observation and evidence contract

Agent 只能看到 lawful owner-scoped evidence。以下对象不得进入 normal policy input：

- hidden world id；
- future service windows；
- oracle witness / disposition；
- unreleased warning / obligation；
- evaluator-only latent state。

合法信息来源可以包括：

- initial public observation；
- passive telemetry；
- normal-send execution feedback；
- gateway receipt / final ACK；
- timeout / negative observation；
- declared owner query。

`missing`、`stale`、`unreachable`、`negative observation` 必须保持不同语义。

## 5. Action contract

当前 T1 causal action surface 至少包括：

- `WAIT`；
- `SEND_TERR(obligation)`；
- `SEND_SAT(obligation)`；
- `ISSUE_QUERY(gateway_state_summary)`，仅在 capability 合法时。

动作 legality、physical executability 与 obligation-preserving feasibility 是三个不同概念。一个授权合法的 action 可以因为资源/时序后果损害未来任务可行性，但不能因此从 legal action space 中偷偷删除。

## 6. Physical and obligation transition contract

动作必须真实改变同一个 causal state：

- query 消耗声明的 terrestrial opportunity / time；
- send 消耗对应窗口与资源；
- satellite send 消耗 satellite budget；
- wait 推进到下一个事件并减少剩余 slack；
- ACK / timeout / query response 作为异步 observation 进入后续 history；
- delivery completion 修改 obligation ledger；
- recovery 改变 connection / knowledge / decision / task feasibility 的时间点应保持可区分。

核心 consequence 不是任意 reward，而是：**哪些 operational obligations 仍可按 contract 完成。**

## 7. EvidenceNeed contract

EvidenceNeed 必须经过两层判定。

### 7.1 Decision divergence

对同一合法 history 的 compatible states，若存在所有 world 都 outcome-equivalent 的 common safe commitment，则不能仅因状态不同声明 EvidenceNeed。

### 7.2 Acquisition value

比较同信息/同资源/同反馈 contract 下：

- observation-matched exact policy；
- observation-matched no-paid-query policy。

no-paid-query 仍必须保留 passive telemetry、自然到达 evidence、ACK 与 normal send-as-probe。只有付费取证在这些普通反馈存在时仍严格增加可实现任务价值，才能声明 positive paid EvidenceNeed。

必须显式排除：query 来不及、query 无区分度、normal send 同时完成任务并提供等价信息、query 被普通 action 支配等伪 EvidenceNeed。

## 8. Oracle contract

至少分离四个 reference：

1. **Hindsight physical oracle**：完整外生未来，仅作物理上界；
2. **Full-current-state causal oracle**：当前真实状态已知，未来仍按声明 process 展开；
3. **Observation-matched exact oracle**：与 policy 相同的历史/能力/process contract；
4. **Observation-matched no-paid-query oracle**：禁止额外付费 query，其余自然反馈保持。

Observation-matched oracle 必须满足 non-anticipativity：

```text
same visible history -> same action
```

逐 hidden world 分别选择成功 trajectory 不构成合法 policy。若每个 world 各自物理可解，但不存在共同 observation-matched causal policy，则 disposition 为 `INFORMATION_INFEASIBLE`。

## 9. Hardness contract

Hardness 必须来自 communication / information structure，而不是 prompt 长度或 arbitrary hidden field。有效 hardness axis 包括：

- observation sparsity / staleness；
- service uncertainty；
- resource scarcity；
- deadline pressure；
- multi-obligation conflict；
- action irreversibility；
- feedback delay；
- recovery delay；
- long-horizon opportunity coupling。

普通 baseline ladder 至少覆盖：

- deadline-reserve / EDF；
- greedy fallback；
- fixed-priority / least-slack；
- latest-feasible-send；
- always-query-then-plan；
- never-query + passive feedback；
- myopic VoI；
- finite-horizon / rolling belief-aware planner；
- development-tuned shallow rule/tree；
- observation-matched exact reference。

Exact solver 能解小实例是预期行为。Hardness admission 排除的是 ordinary shallow-policy saturation，而不是“所有 deterministic algorithms 都不能解”。

## 10. Communication-attribution contract

正式 benchmark 必须证明 measured difficulty 来自 communication / information constraint，而不是 generic task incompetence。适用时至少报告：

- full system；
- no communication / no paid acquisition；
- oracle communication / perfect current observation；
- no active sensing；
- no memory；
- remove resource conflict；
- relaxed deadline；
- controlled stale evidence / delayed feedback / disabled fallback 等单因素 intervention。

预期性质：移除资源竞争、给及时完美证据、放宽 deadline 后，对应困难应减弱；若不减弱，需要重新审查 construct。

## 11. Construction and split contract

固定顺序：

```text
external operational corpus
-> canonical operational objects
-> Family Identity Test / taxonomy
-> source-profiled obligation contract
-> historical semantic dedupe
-> state / action / transition / oracle contract
-> simulator mapping / SIMULATOR_GAP
-> generator
-> V0-V9 validity / hardness
-> structure-aware held-out split
-> policy evaluation
```

变量 provenance 只能属于：

- `FIXED_BY_SOURCE`；
- `SOURCE_RANGE`；
- `EMPIRICAL_TRACE` / declared model-derived trace；
- `CONTROLLED_STRESS`；
- `UNRESOLVED`。

`UNRESOLVED` answer-relevant variable 禁止采样；`CONTROLLED_STRESS` 必须显式标注，不能冒充 field-calibrated fact。

Split 不允许按随机行简单切分后宣称 generalization。至少需要 solver/signature/component/near-duplicate leakage audit，并保留结构化 held-out rationale。

## 12. Success and metrics

核心 success：所有适用 obligations 按 source/task contract 完成，且 authority、resource、time constraints 均满足。

核心指标至少包括：

- task success / obligation coverage；
- deadline violation；
- acquisition cost；
- communication / backup cost；
- invalid action / authority violation；
- regret relative to declared oracle；
- recovery timing / post-recovery sustainability when applicable。

Constraint violation 不能通过更高 weighted reward 抵消。若 source 没有定义 sacrifice priority，不允许人为加权制造唯一 gold action。

## 13. Graduation and release rule

Layer 1 有两个不同的“完成”状态：

### 13.1 Research freeze

允许 Layer 2/3 在该 benchmark 上继续研究，要求：

- source-grounded task identity closed；
- causal observation/action/transition contract closed；
- exact oracle closed；
- shortcut / strong baseline audit closed；
- held-out split frozen；
- no known correctness blocker that would change task semantics。

当前 v0.2：**PASS**。

### 13.2 Public `BENCHMARK_ADMIT`

公开 benchmark release 必须同时满足：

- V0–V9 = PASS；
- Q0–Q12 = PASS；
- v0.2 human/source audit = PASS；
- task/evaluator audit = PASS；
- single-shot/open-loop reducibility audit frozen；
- communication-attribution intervention matrix frozen；
- held-out split / public artifact / benchmark version frozen；
- reproducibility + maintenance metadata complete。

当前 v0.2：**PENDING**。

Pending release evidence 不能作为继续修改 generator 的理由；只有 correctness/source/simulator blocker 才允许打破 research freeze。

## 14. Current v0.2 machine state

- recipe universe: 58,752；
- exact solver signatures: 8,064 / 8,064；
- exact projected labels:
  - 55,008 `NO_PAID_QUERY_REQUIRED`；
  - 2,106 `PAID_EVIDENCE_REQUIRED`；
  - 630 `INFORMATION_INFEASIBLE`；
  - 1,008 `MIXED_WORLD_SOLVABILITY`；
- V8 hard survivors: 41 signatures / 174 recipes；
- hard train/dev/test signatures: 16 / 18 / 7；
- frozen public test: 3,804 cases；
- public-test SHA256: `23307c06ed7c9f9d992db4bcc5cee12b1703e38d997a293b3d1677cc1b91b6f5`；
- research freeze: PASS；
- public `BENCHMARK_ADMIT`: PENDING Q11 + Q0–Q12 refresh + release evidence closure。

## 15. Non-goals

Layer 1 不负责：

- 证明某个新 Agent / LLM 优于传统控制；
- 为某个 Layer 2/3 方法反向改难度；
- 通过增加 seed / overlap / prompt complexity 人工制造 benchmark scale；
- 把 path/cache/radio/tool 名拆成虚假的 Task Family；
- 用 LLM judge 代替可执行 task-success evaluator；
- 把 exploratory certificate/frontier/cache 方法写进 benchmark definition。
