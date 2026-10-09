# Figure plan — Future-Choice paper

状态：**current figure shortlist / every figure answers one reviewer question**。

风格原则来自近期 networking/systems/benchmark papers：早期用一张清晰的 construction/method figure建立心智模型，结果部分优先 CDF/paired distribution/Pareto/ablation/failure decomposition；图在双栏缩放和黑白打印时都必须可读。禁止雷达图、装饰饼图、把现成表格机械换成柱状图。

## MAIN-1 — Future-Choice mechanism

Asset：`paper/generated/fig_future_choice_mechanism.tex`

回答：**为什么 static reserve / scalar value 不是同一个问题，以及方法到底做什么？**

三部分：static union false-negative → observation-conditioned branch policy → `carried/U/L/exact` runtime。

建议位置：Introduction末尾或 Method开头，`figure*` 全宽。

## MAIN-2 — A lifecycle failures

Asset：`fig_layer1_failure_lifecycles.pdf`

回答：**为什么 benchmark 不能只报 TDR？**

三条相同时间轴：delivery-only / energy-collection / task-revision execution。数字来自 frozen deterministic case-study artifact，不手选“最好看”case。

建议位置：RQ1 benchmark findings，单栏或跨栏半宽。

## MAIN-3 — B dependency-local invalidation

Asset：`fig_dependency_local_invalidation.pdf`

回答：**新 history event 是否必然要求重建 future-feasibility structure？**

C=16 event sequence：send→pending只重建1/16；gateway receipt和final ACK 0 rebuild；global backup budget才全重建。

建议位置：RQ3 / Method maintenance。

## MAIN-4 — C paired outcome gain

Asset：`fig_uav_paired_gain.pdf`

回答：**在100个预先冻结的 hard-feasible layouts 上，FutureChoice 相对强 depth4 的收益多大、稳定不稳定、有无反向 harm？**

Forest plot显示 paired zero-tardy rate gain + bootstrap 95% CI，并标 favorable/adverse discordance + exact McNemar。

建议位置：RQ4 main result。**优先级最高的数据图。**

## MAIN-5 — B→C set-level attribution

Asset：`fig_setmst_ablation.pdf`

回答：**B 的 set-level conflict insight迁到 C 后，是否真的减少 exact-correct search burden？**

connected-dot两面板：exact fallback / pure exact 与 total search proxy / pure exact，basic-U→set-MST-U，任务质量保持不变。

建议位置：RQ5 attribution / ablation。

## APPENDIX candidates

不再为以下内容额外画主图：

- N=5 1000-seed robustness：主文信息已经被 N=10/100 scale覆盖，放表/appendix即可；
- external-paper-matched 50：主要用于 scale/protocol对齐，若信号有限就用表而不是图；
- A LLM 30×2：只有模型诊断价值，除非 failure breakdown很有信息，否则不抢主图位置；
- 旧 Layer1 benchmark landscape热图：可留 benchmark appendix / artifact，不与 Future-Choice主线竞争。

## Reproduction

```bash
python3 scripts/make_future_choice_figures.py
python3 scripts/make_future_choice_figures.py --check
```

数据 authority：`results/` tracked artifacts；图不拥有独立数值真相。
