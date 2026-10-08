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
| `benchmark/` | **Layer 1**：source-grounded operational obligation、task construction、observation/action/oracle、validity/hardness、split/release | source/generation infrastructure ready；gateway policy placement retained；data-location/action ownership correctness open；formal admission 关闭 | [`benchmark/LAYER1-AUTHORITY.md`](benchmark/LAYER1-AUTHORITY.md) · [`benchmark/README.md`](benchmark/README.md) |
| `compiler/` | **Layer 2**：Task/Evidence/Capability/Execution、legality、evidence lifecycle、future-choice L/U、incremental frontier、exact fallback | **v2 deterministic core frozen on dev** | [`compiler/README.md`](compiler/README.md) · [`compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md`](compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md) |
| `policy/` | **Layer 3**：合法 / unresolved action 的排序、search guidance、LLM / learned policy | **paused**；等待 Layer-1 benchmark coverage / holdout 闭合 | [`policy/README.md`](policy/README.md) |
| `evaluation/` | replay、attribution、ablation、baseline fairness、跨层 audit contract | 横切三层 | [`evaluation/README.md`](evaluation/README.md) |
| `literature/` | related work、source registry、claim boundary | 横切三层 | [`literature/README.md`](literature/README.md) |
| `history/` | 被当前设计取代的 tracked research authority / roadmap | provenance only | [`history/README.md`](history/README.md) |

## Current research line

Layer 1 当前保留三类 scoped 资产：v0.2 failure atlas、v0.6 可复现判废 lineage、v0.7 process-support correction。它们都不等于已完成 benchmark。gateway policy placement 与 owner-local receipt visibility 继续保留，但 `V07-GATEWAY-ACTION-OWNERSHIP-REVIEW.v0.1.md` 发现旧端到端 `SEND_TERR → gateway receipt → center ACK` 被错误复用成 gateway-local action；因此必须先冻结 report/data-location lifecycle 与 gateway 合法 action owner，再重启 exact。center placement 继续保持独立 `SIMULATOR_GAP`。此前 36-cell gateway pilot 与 bifurcation intervention 只作为 provisional-kernel diagnostic，不承担 admission。Layer 2 v1/v2 继续作为 deterministic/reference 资产保留；Layer 3 暂停。

当前边界：

- Layer 1 当前因 dynamic mechanism、hard-mechanism coverage 与 test provenance 正式重开；方法结果不得反向修改 generator。
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
