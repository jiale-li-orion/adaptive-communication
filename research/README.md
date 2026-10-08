# Research Ownership

状态：2026-10-06 current ownership。

`research/` 只按研究对象组织。实验轮次进入 `results/` 或本地 `local_research/episodes/`；当前 claim state 由 `results/CLAIMS.md` 持有。

## Architecture

```text
source / field requirement
        ↓
Layer 1 · benchmark
        ↓ public task/evidence/action/oracle contract
Layer 2 · decision-semantic compiler
        ↓ legal structured decision surface
Layer 3 · policy
        ↓ selected action
shared communication substrate + scorer
```

| Owner | 持有语义 | 当前状态 | Authority / entry |
|---|---|---|---|
| `substrate/` | 通信物理、能量、缓存、机会、fallback、执行生命周期、system model | 稳定共享底座 | [`substrate/README.md`](substrate/README.md) · [`substrate/SYSTEM-MODEL-v1.md`](substrate/SYSTEM-MODEL-v1.md) |
| `benchmark/` | **Layer 1**：source-grounded operational obligation、task construction、observation/action/oracle、validity/hardness、split/release | 三条 release track 已定义；action/data-location ownership 已闭合；正式 release 仍待 track artifact / evaluator / fresh split / Q11 | [`benchmark/LAYER1-AUTHORITY.md`](benchmark/LAYER1-AUTHORITY.md) · [`benchmark/README.md`](benchmark/README.md) |
| `compiler/` | **Layer 2**：Task/Evidence/Capability/Execution、legality、evidence lifecycle、future-choice L/U、incremental frontier、exact fallback | **v2 deterministic core frozen on dev** | [`compiler/README.md`](compiler/README.md) · [`compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md`](compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md) |
| `policy/` | **Layer 3**：合法 / unresolved action 的排序、search guidance、LLM / learned policy | **paused**；等待 Layer-1 benchmark coverage / holdout 闭合 | [`policy/README.md`](policy/README.md) |
| `evaluation/` | replay、attribution、ablation、baseline fairness、跨层 audit contract | 横切三层 | [`evaluation/README.md`](evaluation/README.md) |
| `literature/` | related work、source registry、claim boundary | 横切三层 | [`literature/README.md`](literature/README.md) |
| `workstreams/` | 当前跨层研究探索索引；只记录问题、证据、否决条件与下一步，不持有正式语义 | 横切三层 | [`workstreams/README.md`](workstreams/README.md) |
| `history/` | 被当前设计取代的 tracked research authority / roadmap | provenance only | [`history/README.md`](history/README.md) |

## Current research line

当前同时推进的研究路线先看 [`workstreams/README.md`](workstreams/README.md)。它只负责导航；正式 task / method / policy 语义仍分别回写到 benchmark / compiler / policy。

Layer 1 当前保留 v0.2 failure atlas、v0.6 negative construction lineage、v0.7 process-support correction 作为历史/诊断资产，但 paper-facing construction 已切换到 `Operational-Conformance / Interactive-Decision / Future-Choice-Stress` 三条 release track。gateway report/data-location 与 backhaul action ownership 已由当前 contract 闭合；center placement 继续保持独立 `SIMULATOR_GAP`。旧 hard-survivor / bounded gateway pilot 不再决定整个 benchmark 是否可 release，只决定 Future-Choice-Stress / method claim 是否成立。Layer 2 v1/v2 继续作为 deterministic/reference 资产保留；Layer 3 只因 method-stress 线暂停。

当前边界：

- Layer 1 benchmark release 当前因 track-specific artifact、execution evaluator、fresh split 与 Q11 正式重开；hard-mechanism coverage 只属于 Future-Choice-Stress / method claim。
- Layer 2 deterministic semantics 只因 correctness defect 重开；performance temptation 不改变 frozen contract。
- Layer 3 当前暂停；未来重新启动时仍只能消费 frozen Layer-1/2 contract，不接管 protocol legality、oracle 或 benchmark generation。
- 历史 7-signature test 已暴露，承担 regression evidence；新的 structural-generalization claim 需要重新 preregister holdout。
- task quality、acquisition/communication cost、planner compute 三账分别记录。

## Ownership invariants

1. 外部来源持有 operational need、authority boundary 与可辩护参数范围。
2. `substrate/` 持有共享物理语义；benchmark/compiler/policy 使用同一 physical transition 与 scorer。
3. `benchmark/` 持有问题定义和 exact evaluation contract。
4. `compiler/` 持有 deterministic correctness：legality、evidence lifecycle、L/U、incremental validity 与 exact fallback。
5. `policy/` 持有合法空间内的选择与搜索顺序。
6. 数字进入论文前经过 `results -> generator -> generated artifact` 链；README 不建立第二份数字 authority。
7. superseded 结果进入 history/lineage/provenance，不回写 current owner。
