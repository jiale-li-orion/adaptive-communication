# Research Ownership

状态：2026-10-05 ownership freeze。

本目录按研究对象分层，不再按实验轮次或某一版论文状态组织。`results/CLAIMS.md` 仍是 claim-state authority；Layer 1 当前方向与状态由 [`benchmark/LAYER1-AUTHORITY.md`](benchmark/LAYER1-AUTHORITY.md) 唯一拥有；本文件只定义谁拥有哪类语义。

| Owner | 负责对象 | 当前状态 | 入口 |
|---|---|---|---|
| `substrate/` | 山区灾前监测通信物理、能量、缓存、机会、回传、fallback、执行生命周期与数学系统模型 | 稳定底座 | `substrate/README.md` |
| `benchmark/` | Layer 1：source-grounded operational needs、Task construction、validity/hardness、conformance/decision benchmark | **research freeze 已完成**；v0.2 release evidence 已刷新为 **12 PASS / 1 BLOCKED**，Q6 LLM、agentic reducibility、communication attribution、Q10 reproducibility 均已闭合；formal `BENCHMARK_ADMIT` 只剩 Q11 真实 human/source review | `benchmark/LAYER1-AUTHORITY.md` · `benchmark/README.md` · `../spec/benchmark/LAYER1-DECISION-BENCHMARK-v0.2.md` |
| `compiler/` | Layer 2：Task/Evidence/Capability/Execution 到 live decision surface、EvidenceNeed、commitment、persistent execution | 已有 A7–A11 机制证据，接口冻结 | `compiler/README.md` |
| `policy/` | Layer 3：deterministic/search、LLM、未来 GNN/offline RL/hybrid policy；只在合法 decision surface 上做选择 | LLM/规则已有，learned policy 尚未实现 | `policy/README.md` |
| `evaluation/` | replay、attribution、ablation、baseline fairness、生成结果摘要 | 横切三层 | `evaluation/README.md` |
| `literature/` | 当前 related work 与来源登记 | 横切三层 | `literature/README.md` |
| `history/` | 被后续决策取代的混合 authority、旧 roadmap | provenance only | `history/README.md` |

## Research line

Layer 1 从原始山区灾前需求和可核查来源构造 Operational Task，并要求 task 在物理系统中激活真实 policy choice、partial evidence、resource conflict 或 temporal dependence。Layer 2 将合法 Task、Evidence、Capability 与 Execution 编译成 typed live decision surface。Layer 3 在该合法空间内选择 commit/query/wait/fallback/replan 等策略。通信结果由独立 physical scorer 评价。

当前版本关系固定为：**Layer 2 v1 已先完成一版机制并由 A7–A11 等结果冻结；由于旧 Layer 1 大量任务在 compilation 后退化为 `unique-ready`，研究随后回到 Layer 1 重做 Decision Benchmark；Layer 1 v0.2 现已 research-freeze。当前主线是用新 Layer-1 v0.2 重验 frozen Layer-2 v1，而不是预先重写 Layer 2。** 只有在 task/capability 已无损表达后，v1 仍出现真正 EvidenceNeed / Context / acquisition / execution 决策失败，才开启 Layer-2 v2；Layer 3 的新 policy/learning claim 随后再展开。

O1–O6 继续作为 T1 Runtime/semantic conformance/regime assets；A7–A11 继续作为 Layer-2 v1 的机制与执行证据。Layer-1 v0.2 的毕业标准与 release 状态见 `benchmark/README.md` 和 `../spec/benchmark/LAYER1-DECISION-BENCHMARK-v0.2.md`。

## Ownership invariants

1. 现实来源定义 operational need、能力边界和可辩护参数范围；simulator 中的研究参数不得反向伪装成现场事实。
2. shared substrate 不为某个 policy 改物理语义；policy 比较共享同一 Task、信息边界、action legality 与 scorer。
3. protocol legality、authority、owner、freshness、execution lifecycle 由 deterministic semantics 持有；learning 只优化合法选择空间。
4. conformance correctness 与 decision quality 分开报告。唯一 ready action 的任务可以验证 Runtime，但不能单独证明 planning/learning 能力。
5. 历史负结果、撤回结果和被普通机制覆盖的 candidate 保留 provenance，不回到 current owner。
