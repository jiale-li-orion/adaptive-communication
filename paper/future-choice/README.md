# Future-Choice paper workspace

状态：**current manuscript workspace / writing scaffold / no independent claim authority**。

工作标题：

> **Preserving Future Choices in Agentic Semantic Communication**

本目录是 2026-10-09 之后当前论文的写作入口。它不接管研究语义，也不手工维护实验数字。

## Authority

写作前依次读取：

1. [`../../results/CLAIMS.md`](../../results/CLAIMS.md) — 唯一 claim-state authority；
2. [`../../research/workstreams/PAPER-SYNTHESIS.md`](../../research/workstreams/PAPER-SYNTHESIS.md) — A/B/C 综合叙事；
3. [`../../research/workstreams/LITERATURE-GAP-AUDIT-2026-10-09.md`](../../research/workstreams/LITERATURE-GAP-AUDIT-2026-10-09.md) — current novelty / experiment / writing boundary；
4. [`../../research/workstreams/EXPERIMENT-MATRIX-2026-10-09.md`](../../research/workstreams/EXPERIMENT-MATRIX-2026-10-09.md) — current RQ / cohort / scale / baseline / statistics / resource execution plan；
5. [`../../research/workstreams/ASSET-REUSE-AUDIT-2026-10-09.md`](../../research/workstreams/ASSET-REUSE-AUDIT-2026-10-09.md) — current core 与旧资产复用地图；
6. [`../../research/benchmark/LAYER1-AUTHORITY.md`](../../research/benchmark/LAYER1-AUTHORITY.md) — A / benchmark authority；
7. [`../../research/compiler/README.md`](../../research/compiler/README.md) — B / method correctness boundary；
8. [`../../results/transfer/future-choice-claim-matrix.json`](../../results/transfer/future-choice-claim-matrix.json) — machine-readable scoped paper projection；
9. [`REFERENCE-PLAN.md`](REFERENCE-PLAN.md) — 旧论文引用复用 + 2025–2026 最近邻 citation clusters；
10. generated paper facts/tables in [`../generated/`](../generated/)。

任何数字必须来自 generated artifact 或 tracked source result；禁止从聊天、README 或本目录手抄数字到正文。

## Paper roles

- **A — Reality / benchmark authority**：真实灾前应急通信 task、physical lifecycle、final operational evaluator、ordinary-baseline falsification。
- **B — Direct ASC formulation**：observation-conditioned future obligations、set-level opportunity conflict、certificate validity/domain 与 dependency-local invalidation。
- **C — Independent external validation**：local legality 删除 full continuation、depth-k residual gap、exact-correct L/U safety layer、B→C set-conflict transfer。

## Generated numeric artifacts

```text
paper/generated/future_choice_facts.tex
paper/generated/table_future_choice_asc.tex
paper/generated/table_future_choice_uav.tex
paper/generated/future_choice_facts.meta.json
```

生成 / 检查：

```bash
python3 scripts/make_future_choice_artifacts.py
python3 scripts/make_future_choice_artifacts.py --check
```

## Current claim ceiling

当前可写：`results/CLAIMS.md` 的 Layer-1 `B*` 与 Future-Choice `F1–F7`。

当前禁止：

- wall-time superiority；
- “所有真实 emergency task 都需要 Future-Choice”；
- 把 C 写成 emergency-communication benchmark；
- 把 N=15 seed1 写成 distribution result；
- 把 assistant-led internal audit 写成 independent expert validation；
- A 的 frozen LLM subset 在 final analysis 完成前写最终模型结论。

正文骨架可以现在写；A 最后 LLM 子表与 final Layer-1 release manifest 完成后，再冻结 abstract / result headline。
