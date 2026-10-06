中文 | [English](README.md)

# 间歇连接下的智能体通信

面向山区灾前长期监测的 source-grounded 决策基准、决策语义运行时与策略学习。场景长期存在供电受限、回传间歇中断、缓存压力与恢复过程；任务义务由外部来源定义，系统负责通信执行。

> **当前控制面：** Layer 1 benchmark 语义已经 research freeze；Layer 2 v2 deterministic future-choice core 已在 dev 冻结；Layer 3 是当前活跃方法线，在固定 Layer-2 correctness boundary 内学习 search guidance。当前模块状态统一由 [`research/`](research/README.md) 持有。

## 1. 系统架构

原始现场需求是一切研究对象的上游：山区监测节点需要在低功耗、低成本和间歇连接条件下持续产生有效感知，并在真实时限内完成回传。外部来源定义 operational obligation 与 capability boundary；仓库把这些义务构造成可执行的通信决策问题，并在统一物理底座上评价策略后果。

```text
外部 operational source / 原始现场需求
                    │
                    ▼
┌──────────────────────────────────────────────────────────────┐
│ Layer 1 · Source-grounded Emergency Communication Benchmark │
│ Operational obligation · partial observation · action       │
│ causal transition · exact oracle · hardness · frozen split  │
└──────────────────────────────┬───────────────────────────────┘
                               │ public task/evidence/action contract
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Layer 2 · Decision-Semantic Compiler                         │
│ Task / Evidence / Capability / Execution                    │
│ legality · evidence lifecycle · future-choice L/U frontier  │
│ incremental maintenance · exact fallback                    │
└──────────────────────────────┬───────────────────────────────┘
                               │ legal structured decision surface
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Layer 3 · Policy                                             │
│ deterministic / search / LLM / learned guidance             │
│ 当前对象：unresolved-action ranking 与 search order          │
└──────────────────────────────┬───────────────────────────────┘
                               │ selected communication action
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Shared Communication Substrate                              │
│ LoRa/Class-A · gateway · cellular · BeiDou backup · cache   │
│ battery/harvest · outage/recovery · execution · scorer      │
└──────────────────────────────────────────────────────────────┘

横切模块：evaluation / literature / result ledger / provenance
```

三层分别拥有不同语义：Layer 1 定义问题；Layer 2 持有 deterministic correctness 与合法 decision surface；Layer 3 持有该 surface 内的选择顺序；shared substrate 持有物理执行与 scorer。

## 2. 模块 ownership

| 模块 | 持有对象 | 输出 | 当前状态 | 入口 |
|---|---|---|---|---|
| **Shared substrate** | 通信物理、能量、缓存、机会、fallback、执行生命周期、数学系统模型 | state transition 与 physical outcome | 稳定底座 | [`research/substrate/`](research/substrate/README.md) |
| **Layer 1 · Benchmark** | source-grounded operational obligation、task construction、observation/action contract、oracle、validity/hardness、split/release | frozen benchmark instances 与 exact reference | **research-frozen**；release 只剩 Q11 human/source review | [`research/benchmark/`](research/benchmark/README.md) |
| **Layer 2 · Compiler** | Task/Evidence/Capability/Execution 语义、evidence validity、L/U future-choice frontier、incremental update、exact fallback | 合法结构化 decision surface | **v2 deterministic core frozen on dev** | [`research/compiler/`](research/compiler/README.md) |
| **Layer 3 · Policy** | 合法 / unresolved action 的排序与选择 | search guidance / policy choice | **active**；learned ranking 正在 dev 评测 | [`research/policy/`](research/policy/README.md) |
| **Evaluation** | replay、attribution、ablation、baseline fairness、跨层 audit | machine-checkable verdict | 横切 | [`research/evaluation/`](research/evaluation/README.md) |
| **Literature** | related work 与 source registry | claim boundary 与来源追溯 | 横切 | [`research/literature/`](research/literature/README.md) |
| **Research history** | 已被当前设计取代的 tracked research authority / roadmap | provenance | 冻结历史 | [`research/history/`](research/history/README.md) |

当前研究对象固定为：

```text
source-grounded operational obligation
+ action-relative evidence sufficiency
+ heterogeneous capability for evidence acquisition
+ intermittent long-horizon obligation feasibility
+ external causal oracle for action / completion validity
```

论文候选 benchmark 对比图、同类工作链接、construct coverage 与 v0.2 数据分布统一由 Layer-1 模块维护：[`research/benchmark/README.md`](research/benchmark/README.md#paper-facing-benchmark-landscape-and-statistics)。

## 3. 当前状态

| Owner | 当前冻结 / 活跃边界 |
|---|---|
| Layer 1 | v0.2 research semantics、exact oracle、validity/hardness ladder、structure-aware split 与 paper-facing statistics 已冻结。正式 public admission 等待 Q11 真人 source/task/oracle/evaluator review。 |
| Layer 2 | v1 保留为历史 runtime/compiler baseline。v2 deterministic future-choice semantics 完成 dev correctness 与强对照后冻结。对 lean ordinary persistent exact 的 raw wall-time 劣势作为公开 systems boundary 保留。 |
| Layer 3 | Learning 只在 `L=0,U=1` unresolved actions 上学习排序、search guidance 与 compact context。legality、evidence ownership、L/U 语义和 exact fallback 继续由 Layer 2 持有。 |
| Generalization | 历史 7-signature test 已在早期 Layer-2 工作中暴露，当前归入 regression evidence。新的 structural-generalization claim 需要重新 preregister holdout。 |

机器结果统一进入 [`results/`](results/README.md)，claim state 统一进入 [`results/CLAIMS.md`](results/CLAIMS.md)。论文数字遵循 result → generator → generated artifact 的单一生成链。

## 4. Authority map

| Authority | Owner |
|---|---|
| 当前研究 ownership | [`research/README.md`](research/README.md) |
| Layer-1 方向与 disposition | [`research/benchmark/LAYER1-AUTHORITY.md`](research/benchmark/LAYER1-AUTHORITY.md) |
| Layer-1 normative environment / action / oracle contract | [`spec/benchmark/LAYER1-DECISION-BENCHMARK-v0.2.md`](spec/benchmark/LAYER1-DECISION-BENCHMARK-v0.2.md) |
| Runtime/domain semantics | [`research/compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md`](research/compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md) |
| 数学系统模型 | [`research/substrate/SYSTEM-MODEL-v1.md`](research/substrate/SYSTEM-MODEL-v1.md) |
| 部署 / 数据参数 | [`spec/substrate/`](spec/substrate/) |
| Claim truth | [`results/CLAIMS.md`](results/CLAIMS.md) |
| Result ownership | [`results/README.md`](results/README.md) |
| Reviewer reproduction | [`artifact/AE.md`](artifact/AE.md) |

每份 authority 文件只持有一类语义。README、图、表和 paper macro 属于 authority artifact 的可生成投影。

## 5. 仓库结构

```text
adaptive-communication/
├── research/                  当前研究 ownership 与语义
│   ├── substrate/             shared communication/world model
│   ├── benchmark/             Layer 1
│   ├── compiler/              Layer 2
│   ├── policy/                Layer 3
│   ├── evaluation/            跨层 evaluation contract
│   ├── literature/            related work / source registry
│   └── history/               superseded tracked research authority
│
├── spec/                      normative contract 与 deployment/data spec
│   ├── benchmark/
│   ├── substrate/
│   └── history/
│
├── code/
│   ├── substrate/             physical simulator 与 substrate tests
│   ├── agentic_communication/ typed runtime objects
│   ├── evaluation/            Layer-1/2/3 runner 与 audit
│   └── legacy-communication/  可复现历史实现
│
├── results/
│   ├── benchmark/             Layer-1 frozen evidence
│   ├── agentic/               Layer-2 / Layer-3 evidence 与历史 A* 资产
│   ├── communication-substrate/
│   ├── reference/             frozen comparator
│   ├── history/               withdrawn / superseded result record
│   └── legacy-communication/
│
├── paper/                     manuscript lineage 与 generated paper artifact
├── artifact/                  reviewer / reproduction 入口
├── scripts/                   result-to-paper 与仓库生成脚本
├── tooling/                   可复用论文 / 仓库工具
├── archive/                   tracked historical executable bundle，路径冻结
├── data/                      `make data` 获取/生成的 workspace data
├── libs/                      `make deps` 获取的本地依赖
└── local_research/            本地 current / lineage / episodes / archive
```

`docs/` 与 `local_experiments/` 是 workspace compatibility symlink，实际指向 `local_research/archive/compat/`。新研究材料进入明确 owner 模块或 local research 四区。

## 6. 构建与检查

```bash
make deps
make data
make check
make tables ARGS=--check
make agentic-preapi
make paper
```

`make check` 已包含 Layer-1 paper asset drift check。Benchmark 图和统计由 `scripts/make_layer1_paper_figures.py` 从 frozen `results/benchmark` artifacts 自动生成。

## 7. 论文与历史

- 当前可构建 Agentic 稿件：[`paper/agentic/`](paper/agentic/README.md)
- 系统稿兼容副本：[`paper/en/`](paper/en/)、[`paper/zh/`](paper/zh/)
- 不可变稿件历史：[`paper/_archive/`](paper/_archive/)
- 当前 claim ledger：[`results/CLAIMS.md`](results/CLAIMS.md)
- 本地 research lineage / episode：workspace-only `local_research/README.md`
- tracked 历史可执行 bundle：[`archive/`](archive/README.md)

Git 保存逐轮修改历史；各模块 README 只维护当前 ownership 与当前状态。
