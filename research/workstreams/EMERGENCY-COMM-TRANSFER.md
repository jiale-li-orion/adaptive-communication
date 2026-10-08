# Workstream C — Emergency Communication Transfer

## Question

future-choice / operational-obligation feasibility 能否在已有应急通信控制环境中提供超出 coverage / throughput / weighted-reward 优化的增量？

## Scope

不把主项目改造成 post-disaster UAV paper。外部应急通信环境只承担 generality test。

优先寻找具备以下至少三项的公开任务：

- sequential communication/resource decisions；
- finite energy / bandwidth / contact opportunities；
- hard deadlines or mission stages；
- partial observation / delayed feedback；
- action commitment 会持续影响后续资源或可达性。

## Intended comparison

```text
existing resource allocator / RL / MPC
vs
same allocator + operational-obligation feasibility layer
```

关注的不是再提高一点 throughput，而是：

> resource-optimal action 是否会在 long horizon 上使 mission obligation set 不再可完成？

## Hard gate

只有当外部任务存在真实的 mission-level continuation conflict 才保留。若所有差异都能由普通 hard constraint / MPC horizon 直接吸收，则该环境不适合支撑 future-choice claim。

## Next

第一可执行候选冻结为 **DRL-EC³**（BIT-MCS/DRL-EC3，JSAC 2018）。它的官方代码明确面向 emergency communications / remote-area communication，包含可训练 environment、连续 UAV movement action、persistent UAV energy、spatial data-collection state，以及 movement + collection 的真实持续能耗。

本地只读 checkout：`local_research/external/DRL-EC3`。由于原 repo 把 rendering flag 绑到 TensorFlow 1.x、并依赖旧 Gym，当前 smoke 用内存中的最小 compatibility shim 解耦这两个**非科学依赖**；未修改外部 checkout、未安装 TensorFlow、未训练模型。环境 reset + one-step dynamics 已跑通：2 UAV 初始 energy 500，一次 zero-movement step 仍因数据采集把每台 energy 降到约 499.352，并更新 remaining-data state。

静态/运行审计同时确认一个关键边界：released environment **没有 hard operational deadline / obligation object**。因此它现在的正确角色是：

> **RESOURCE_BASELINE_AND_SECONDARY_TRANSFER_CANDIDATE**

不能把 future-choice semantics 说成原论文已有。下一步只允许显式添加一个薄的 mission-obligation wrapper（例如 time-bounded coverage commitments），保持原 dynamics/reward/policy 不变，再测试 value/DRL action 是否删除 hard mission continuation。如果 wrapper 只是普通 constrained MPC 一行就解决，这条线降级为普通 external baseline。

### Hard-deadline UAV mission red-team

另外保留一个**不冒充 emergency-communication domain**、但对方法更强的 external mission red-team：`mdehghani86/uav-attention-routing`（2026）。该公开环境原生包含单 UAV、customer deadlines、persistent battery、charger、depot return 与 finite-horizon control；论文实验 N=5 使用 `mission_time=15`、deadline range `3–12`。

代码审计发现 released `get_action_mask()` 只检查“下一节点是否在当前 battery + remaining mission time 下可达”，不保证该动作后仍存在满足全部 customer deadlines 的完整 route；deadline 主要进入 observation / tardiness / potential shaping。我们没有修改外部 checkout，而是用 evaluator-only exact DFS 把**其原生 deadline 字段解释为 hard operational obligations**，检查 continuation existence。

在论文 N=5 evaluation setting 中，扫描到 seed 24：

- 初始存在 zero-tardiness full route `0→1→2→4→3→5→0`；
- customer 2 是 native mask 允许、当前可达且按时的动作，但从它开始不存在满足全部 deadlines + battery + mission-time + depot-return 的 continuation；
- 四条官方 heuristic（NN、Nearest Deadline、Greedy-DB、Battery-Aware NN）的第一步全部落在 destructive action set；
- 原生 episode replay：NN 虽完成并回 depot，但 tardiness `0.79`；Nearest Deadline / Greedy-DB tardiness约 `2.00 / 2.28` 且产生 infeasible termination；Battery-Aware NN 只完成 4/5；
- exact hard-feasible route 在相同原生 `completion_ratio` reward 下 5/5、回 depot、tardiness `0`、infeasible `0`，energy `107.0`，低于 NN 的 `112.1`。

机器审计：`code/evaluation/transfer/audit_uav_attention_future_choice.py`。

边界必须保持：原环境自己的 `completed` flag 允许 tardy service，因此“deadline 必须零迟到”是我们的 operational-obligation transfer interpretation；但 avoidable tardiness / infeasibility / incomplete service 都由原环境自己的 KPI 直接记录，不是我们新造的 reward。当前结果支持 **continuation-aware masking 有真实 external mission surface**，尚不支持“当前 Layer-2 实现优于该论文 learned policy”——learned PPO checkpoint 需单独公平评测。

当前分工因此是：

- **DRL-EC³**：emergency-communication system/resource transfer anchor；
- **uav-attention-routing**：hard-deadline mission-level future-choice red-team；
- 若能找到同时具备 emergency-communication domain + native hard obligations 的公开环境，再替换二者的组合，不为凑 domain 自造环境。

### Continuation-aware shield: 200-seed paired result

`code/evaluation/transfer/run_uav_attention_continuation_shield.py` 进一步把 evaluator-only exact continuation 从“反例解释器”变成 action shield：

```text
official heuristic ranking
    ↓
released native one-step action mask
    ↓ intersect
exact zero-tardiness full-continuation mask
    ↓
same official heuristic ranking
```

环境 transition、deadline、battery、charger、mission time 和 heuristic ranking 都不改；shield 只屏蔽“执行后不再存在全客户 zero-tardiness + depot-return continuation”的动作。

论文 N=5 setting 上扫描 seeds `0..199`。其中 **18/200** initial states 本身存在 hard-feasible full continuation；统计只在这 18 个可兑现 episodes 上做 paired comparison：

| Official heuristic | zero-tardiness | completed | infeasible episodes | mean tardiness Δ (shield-native) |
|---|---:|---:|---:|---:|
| Nearest Neighbour | 9/18 → **18/18** | 18/18 → 18/18 | 0 → 0 | **-1.148** |
| Nearest Deadline | 9/18 → **18/18** | 16/18 → **18/18** | 6 → **0** | **-1.437** |
| Greedy Deadline-Battery | 11/18 → **18/18** | 18/18 → 18/18 | 3 → **0** | **-0.534** |
| Battery-Aware NN | 10/18 → **18/18** | 15/18 → **18/18** | 3 → **0** | **-0.963** |

四条 heuristic 都没有出现 `native zero-tardiness → shielded tardy` 的反向伤害。NearestDeadline / Greedy / NN 的平均 energy 同时下降；Battery-Aware NN 的 shielded energy 平均增加约 1.58，但 completion 与 zero-tardiness 同时改善，因此 energy 不是单调优势 claim。

这个结果已经超出“native mask 存在理论漏洞”：在 hard-feasible cohort 上，continuation-aware masking 可以系统性修复原生 heuristic 的 avoidable tardiness / incomplete / infeasible failure。

边界仍然必须保持：

- 18/200 是 **hard-feasible prevalence**，不能把 200 当成方法成功分母；
- shield 当前使用 evaluator-side exact DFS，是效果上界/transfer oracle，不是高效 deployable Layer-2 implementation；
- 原环境的 `completed` 允许 tardiness，zero-tardiness hard obligation 是 transfer interpretation；
- learned PPO checkpoint 尚未做相同 paired shield 评测。

### L/U + exact-fallback method prototype

exact continuation shield 只回答 attainable upper bound，因此又实现 `code/evaluation/transfer/run_uav_attention_future_choice_lu.py`，把 C 映射到当前 Layer-2 correctness contract：

```text
post-action state
  ├─ U=0: sound optimistic necessary condition fails
  │       (individual earliest-arrival deadline + Euclidean MST mission-time lower bound)
  ├─ L=1: bounded constructive search finds a replayable full route
  ├─ L=1: previously carried route suffix remains valid
  └─ unresolved: exact continuation fallback
```

每个 reached decision boundary 都额外用独立 exact cache 重建 action mask，防止 method fallback 偷吃 correctness-audit memo；因此可以逐 action 检查 L/U mask 是否与 exact continuation mask 一致。

**200 seeds：**

- 18 hard-feasible initial states；四条 official heuristic 均保持 **18/18 zero-tardiness / completed / 0 infeasible**；
- **432** reached action frontiers，`0` mismatch；
- pure exact mask 需要约 `933–951` new exact states / heuristic；
- L/U method 只把 `387–388` new states 留给 exact fallback（约 **40.7–41.6%**）；
- 加上 bounded constructive L-search 后，total search-work proxy 约为 pure exact 的 **74.8–75.0%**；
- carried continuation certificate 命中 `90` 次，sound `U=0` 直接剪掉 `174–182` 次动作。

**1000-seed robustness：**

- 107 hard-feasible initial states；四条 heuristic 均为 **107/107 zero-tardiness / completed / 0 infeasible**；
- **2,568** reached action frontiers，`0` mismatch；
- exact fallback state ratio约 **42.5–46.0%** of pure exact mask；
- 加 bounded constructive search 后 total search-work proxy约 **76.3–80.0%**；
- carried certificate `535` hits / heuristic；sound U=0 约 `1,014–1,061` actions；
- 与 exact shield 一样，没有出现 native zero-tardiness 被 future-choice mask 破坏的 seed。

1000-seed raw episode rows保留在 `local_research/current/transfer/raw/`，避免 git 膨胀；tracked compact artifact `results/transfer/uav-attention-future-choice-robustness-summary.json` 保存关键统计、raw SHA 与重跑命令。

这意味着 C 已经从“exact oracle 证明 continuation 有价值”推进到一个 correctness-preserving future-choice method prototype：大量动作由 cheap U/L certificate 处理，exact 只负责 unresolved fallback。

当前不能越界：

- N=5 exact 本来就便宜，不能用 wall-time 证明算法优势；
- `lower_search_expanded + exact_fallback_new_states` 只是 search-work proxy；
- 下一强门必须是 **depth-k / receding / route-recovery ordinary baseline**，以及 N=10+ 的 scaling；
- learned PPO checkpoint 仍未做 paired continuation shield；
- 当前 route certificate 是 C-domain adapter，不等于 generic Layer-2 core 已经跨 domain 自动适配。

### Strong finite-horizon red-team: N=5 boundary

为了排除“future-choice 只是多看几步”的解释，新增 `code/evaluation/transfer/run_uav_attention_receding_baselines.py`：对同一 official heuristic 加 optimistic depth-k action mask。它只要求存在 k-step legal/on-time partial continuation，并在 horizon 末端检查 sound optimistic necessary conditions；不证明 full completion，也不使用 exact fallback。

1000-seed / N=5、107 个 hard-feasible initial states：

| Policy | depth1 zero-tardy | depth2 | depth3 | depth4 | L/U future-choice |
|---|---:|---:|---:|---:|---:|
| NN | 84/107 | 89/107 | 99/107 | **107/107** | **107/107** |
| Nearest Deadline | 61/107 | 74/107 | 92/107 | **107/107** | **107/107** |
| Greedy DB | 74/107 | 85/107 | 97/107 | **107/107** | **107/107** |
| Battery-Aware NN | 86/107 | 91/107 | 100/107 | **107/107** | **107/107** |

depth4 已经关闭全部 zero-tardiness gap，因此 **N=5 不能支撑“future-choice 比 sufficiently-deep receding lookahead 更强”的 task-quality claim**。

终态上仍有小差异：depth4 Battery-Aware NN 为 106/107 completed、1 infeasible；depth4 NN 仍有 1 infeasible；L/U future-choice 为四条 policy 全部 107/107 completed、0 infeasible。但这不足以掩盖主要负结论。

计算侧也必须诚实：depth4 partial-search expansions 为约 `2.5k–2.6k / policy`，低于当前 L/U 的 `lower-search + exact-fallback` proxy（约 `4.9k–5.3k`）。因此 N=5 上当前 L/U **没有**算法效率优势。

compact artifact：`results/transfer/uav-attention-receding-headroom-summary.json`。

这条 red-team 把下一门槛钉死为论文原生 N=10+ setting：此时 depth4 才是真正局部 horizon。N=10 exact/L-U scaling 必须在严格内存护栏下做；如果 depth4 仍饱和且更便宜，C 只保留 external continuation-value evidence，不承担方法 superiority。

### N=10 paper setting: depth-4 no longer closes the gap

N=10 使用外部论文自己的 setting：`mission_time=30, deadline=5–25, one charger`。为避免用 proposed method / exact oracle挑有利 case，先运行 `select_uav_attention_constructive_cohort.py` 扫 seeds 0..199：一个 seed 只有在**至少一条官方 heuristic 原生完成 10/10、回 depot、zero-tardiness、zero infeasible**时才进入 cohort。

得到 21 个 method-independent constructive hard-feasible seeds：

`[21,23,39,40,74,78,79,84,86,91,95,96,110,113,122,124,145,167,171,177,186]`

其中 Greedy Deadline-Battery 原生就能解 20/21，NN / BatteryAware 各 10/21，NearestDeadline 1/21。因此这个 cohort **偏向 ordinary baseline，而不是偏向 future-choice**。

在这 21 个 seeds 上：

| Policy | depth4 zero-tardy | depth4 completed / infeasible | L/U future-choice |
|---|---:|---:|---:|
| NN | 17/21 | 21 / 0 | **21/21, 21/21, 0** |
| Battery-Aware NN | 17/21 | 21 / 0 | **21/21, 21/21, 0** |
| Nearest Deadline | 11/21 | 14 / 8 | **21/21, 21/21, 0** |
| Greedy Deadline-Battery | 20/21 | 21 / 0 | **21/21, 21/21, 0** |

L/U correctness：**924 reached action frontiers / 0 mismatch** against independent exact mask。

search decomposition：

- pure exact mask new states：约 `33.9k–46.0k / policy`；
- L/U exact fallback new states：约 `14.3k–25.2k`，即 pure exact 的约 **42–55%**；
- 加 bounded constructive lower search 后 total search-work proxy约 pure exact 的 **66–78%**；
- carried route certificates `210` hits / policy；sound U=0 直接剪 `424–568` actions。

这和 N=5 的 scoped-negative 形成了干净 scaling boundary：N=5 depth4 几乎是 full horizon；N=10 depth4 仍是局部 horizon，因此不能稳定保住 full mission continuation，而 L/U + exact fallback 仍与 exact frontier 完全一致。

tracked artifacts：

- `results/transfer/uav-attention-n10-constructive-cohort.json`
- `results/transfer/uav-attention-n10-future-choice-summary.json`

raw 21-seed LU / receding rows继续保留在 `local_research/current/transfer/`，summary 记录 SHA 与重跑命令。

仍然不能越界：Greedy depth4 已经 20/21，future-choice 不是“所有普通方法都失败”的万能层；它更合理的定位是 **selective hard-feasibility / safety layer**。search-work count 也不是 wall-time theorem。下一步优先做 N=10+ 更广 constructive cohort / learned PPO paired shield，而不是继续调 N=5。
