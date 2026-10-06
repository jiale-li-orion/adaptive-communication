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
| `benchmark/` | **Layer 1**：source-grounded operational obligation、task construction、observation/action/oracle、validity/hardness、split/release | **research-frozen**；formal admission 等待 Q11 human/source review | [`benchmark/LAYER1-AUTHORITY.md`](benchmark/LAYER1-AUTHORITY.md) · [`benchmark/README.md`](benchmark/README.md) |
| `compiler/` | **Layer 2**：Task/Evidence/Capability/Execution、legality、evidence lifecycle、future-choice L/U、incremental frontier、exact fallback | **v2 deterministic core frozen on dev** | [`compiler/README.md`](compiler/README.md) · [`compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md`](compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md) |
| `policy/` | **Layer 3**：合法 / unresolved action 的排序、search guidance、LLM / learned policy | **active**；当前聚焦 learned unresolved-action ranking | [`policy/README.md`](policy/README.md) |
| `evaluation/` | replay、attribution、ablation、baseline fairness、跨层 audit contract | 横切三层 | [`evaluation/README.md`](evaluation/README.md) |
| `literature/` | related work、source registry、claim boundary | 横切三层 | [`literature/README.md`](literature/README.md) |
| `history/` | 被当前设计取代的 tracked research authority / roadmap | provenance only | [`history/README.md`](history/README.md) |

## Current research line

Layer 1 已完成当前研究所需的 benchmark freeze。Layer 2 v1 保留为第一版 runtime/compiler baseline；v0.2 重验暴露 acquisition timing failure 后，Layer 2 v2 建立 future-choice / L-U deterministic core，并在 dev correctness 与强对照审计后冻结。当前主线进入 Layer 3：在固定 legality、evidence ownership、L/U 与 exact fallback 下学习 unresolved-action ordering / search guidance。

当前边界：

- Layer 1 只因 source/correctness/evaluator defect 重开；方法结果不反向修改 generator。
- Layer 2 deterministic semantics 只因 correctness defect 重开；performance temptation 不改变 frozen contract。
- Layer 3 可以学习排序、search order、compact context；它消费 Layer-2 decision surface，不接管 protocol legality 或 oracle。
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
