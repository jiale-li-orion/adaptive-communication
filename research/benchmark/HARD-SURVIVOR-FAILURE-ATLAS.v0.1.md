# Layer-1 Hard-Survivor Failure Atlas v0.1

状态：**CURRENT DIAGNOSTIC / REOPENS BENCHMARK COVERAGE**  
依据：`调研cache.md`、`cache06.md`、当前 `v0.2-retry-legality` Layer-1 artifacts。  
机器结果：`results/benchmark/layer1-hard-survivor-failure-atlas-v0.1.json`。  
实现：`code/evaluation/benchmark/audit_hard_survivor_failure_atlas_v0_1.py`。

## 1. 为什么做这次审计

Layer 1 的目的不是筛出一小批“我们的方法能赢”的样本，而是从 source-grounded operational problem 中识别稳定的 decision failure，再据此决定是否存在新的算法对象。

当前主 generator 从 58,752 个 recipes 出发，经 exact labels、V0–V7 validity 与 V8 strong-baseline ladder 后留下 174 个 hard recipes / 41 个 exact solver signatures。此前仓库把这一结果连同 structure-aware split、public-test freeze 和 Q0–Q12 machine checklist 解释成“机器侧 construction 已完成，仅剩 Q11 human review”。本审计发现，这个解释过强：**hardness 存在，但 hard-mechanism coverage 明显坍缩。**

因此，本文件重新打开 Layer-1 的 scientific-coverage gate；不撤销已经成立的 source、oracle、evaluator、validity 与 regression 资产。

## 2. 41 个 hard signatures 实际覆盖什么

41 / 41 survivor signatures 全部同时满足：

```text
service process = FINITE_CROSSING_WINDOWS
evidence regime = GATEWAY_SUMMARY_QUERY
hardness        = H2 Evidence Value
                × H3 Shared Resource Conflict
                × H4 Coupled Sequential Commitment
overlap         = 3 or 4
```

其中 recovery regime、resource headroom、reporting interval、warning state 与 geometry signature 有参数变化，但这些变化不能等价解释为独立机制覆盖。

当前 174 hard recipes 的结构分布仍然全部落在同一个 `FINITE_CROSSING_WINDOWS + GATEWAY_SUMMARY_QUERY` mechanism family。

### 2.1 V0–V7 pass 中哪些轴没有形成独立 hard surface

V8 输入的 1,423 个 signatures 中：

| 轴 | V0–V7 pass | V8 survivor | 结论 |
|---|---:|---:|---|
| `FULL_OBSERVATION_CONTROL` | 373 | 0 | cheap rule 饱和 |
| `PASSIVE_ACK_ONLY` | 373 | 0 | cheap rule 饱和 |
| `MIXED_PASSIVE_QUERY_PROBE` | 373 | 0 | cheap rule 饱和；H5 未形成独立 hard surface |
| `GATEWAY_SUMMARY_QUERY` | 304 | 41 | 当前唯一 hard evidence regime |
| `FINITE_CROSSING_WINDOWS` | 663 | 41 | 当前唯一 hard service process |
| `MULTI_WINDOW_DYNAMIC` | 760 | 0 | finite horizon / cheap rule 饱和 |

`least_slack` 对 `FULL_OBSERVATION_CONTROL`、`PASSIVE_ACK_ONLY`、`MIXED_PASSIVE_QUERY_PROBE` 都是 373 / 373。`myopic_flow_voi` 也分别 373 / 373。当前 generator 因而不能声称已经覆盖 `cache06.md` 要求的动态 passive/query/probe competition、不同 evidence lifecycle 或多种独立 hard mechanism。

## 3. 41 个 survivors 为什么难：first irreversible loss

本审计不再只看最终 `DEADLINE_EXPIRED`。对每条 ordinary baseline 的实际 causal trajectory，在每个合法 decision prefix 上调用独立 exact continuation reference：

```text
执行前：存在 observation-matched 成功 continuation
执行动作 a
执行后：不存在任何 observation-matched 成功 continuation
```

第一次发生上述转变的动作定义为 **first irreversible loss**。

为了避免把“未来 query 次数不足”伪装成动作破坏，本诊断 continuation 在每个前缀都给出 `len(obligations)+2` 的宽松未来 query allowance。因而被标记的 loss 表示：**该动作已经改变了物理/执行状态，使后续即使允许继续取证也无法恢复 all-obligation completion。**

### 3.1 结果

9 类 ordinary policies 在 41 / 41 signatures 上都出现可定位的 first irreversible loss：

| Baseline | first-loss action |
|---|---|
| Always-query-then-plan | `ISSUE_QUERY` 41 branches；后续 `SEND_SAT` 错误承诺 62 branches |
| Shallow rule | `ISSUE_QUERY` 58 branches |
| Least-slack | `SEND_TERR` 40 signatures；`SEND_SAT` 1 |
| Fixed-query every release | `SEND_TERR` 40；`SEND_SAT` 1 |
| True depth-2 belief | `SEND_TERR` 40；`SEND_SAT` 1 |
| True depth-3 belief | `SEND_TERR` 40；`SEND_SAT` 1 |
| Myopic flow / VoI | `SEND_TERR` 32；`WAIT` 9 |
| Receding flow horizon 4 | `SEND_TERR` 32；`WAIT` 9 |
| Receding flow horizon 6 | `SEND_TERR` 32；`WAIT` 9 |

这说明当前 hard surface 不能被解释成单一“query timing”技巧。query、send、wait、satellite commitment 都可能成为第一次不可逆错误。

### 3.2 同一失败点存在什么可行替代

在 first-loss prefix 上枚举全部合法动作并逐一 exact-check：

- Always-query 的 41 个 query-loss events 中，41 / 41 都存在 preserving `SEND_TERR`；22 / 41 同时可 `WAIT`。
- Least-slack / depth-k 的 40 个 `SEND_TERR` loss 中，40 / 40 都存在 preserving `ISSUE_QUERY`；27 / 40 同时可 `WAIT`。
- Myopic / receding 的 32 个 `SEND_TERR` loss 中，32 / 32 都存在 preserving `ISSUE_QUERY`；19 / 32 可 `WAIT`；3 / 32 还有 preserving `SEND_SAT`。
- Myopic / receding 的 9 个 `WAIT` loss 中，9 / 9 都必须在当下使用 preserving `SEND_SAT`。
- Always-query 后续 62 个 `SEND_SAT` loss 中，全部存在另一个 obligation 的 preserving satellite commitment，并且全部仍可 `WAIT`。

因此当前最稳定的经验现象不是“查询有害”，而是：

> **局部合理的 communication commitment 会删除某些后续 completion continuations；不同 baseline 因只看当前信息价值、slack、短 horizon 或局部 flow 而在不同位置过早关闭未来选择。**

这与 `cache06.md` 的目标一致，但目前只在一个窄的 H2×H3×H4 generator family 上得到支持。它是方法发现线索，不是跨场景定理。

## 4. 旧 v0.5 dynamic prototype 不能直接补这个缺口

`scenario_generator_v0_5.py` 已经实现过 `cache06.md` 要求的一部分动态 process semantics：重复 owner query、sample/arrival 分离、owner state 更新、SEND/gateway receipt/final ACK 分离、两个流与六项义务。

重新审计后：

- `independent-bits` 四个 phase 都含至少一个 physical-infeasible world；
- `shifted-window` phase 1 / 3 虽通过旧 fast physical/common-worst gate，但 full non-anticipative exact 在 satellite budget = 2 时仍不可解；
- 将 satellite budget 提到 3 以后 exact 可解，但 no-query exact 也可解，EvidenceNeed 消失；
- receipt-race / receipt-chain 保留 genuine EvidenceNeed，但已被 ordinary reserve/fixed-read/wait-ACK family 覆盖，继续只作为 H2/H4/H5 mechanism regression。

所以旧 v0.5 不能被重新命名为“最终 dynamic benchmark”。它只能提供可复用的事件语义与历史反例。

## 5. 当前 Layer-1 verdict

### 已经成立

- T1 operational family 与 source contracts；
- provenance discipline；
- compositional recipe infrastructure；
- causal observation / evidence semantics；
- non-anticipative exact reference；
- V0–V9 validity/evaluator infrastructure；
- v0.1 degeneracy falsification；
- 当前 H2×H3×H4 hard mechanism 的存在性；
- first irreversible commitment failure 可以被 exact counterfactual 定位。

### 重新打开

1. **Hard-mechanism coverage**：当前 41 signatures 不能代表 `cache06.md` 要求的全部动态 evidence / resource / execution interaction。
2. **Dynamic-process admission**：必须把重复取证、异步 ACK、send-as-probe、future branch uncertainty 和 action-dependent evidence value 真正编进主 generator，而不是作为孤立 prototype。
3. **Pristine structural generalization**：旧 7-signature test 已在 `fdc0846` 暴露，不能作为最终方法泛化 claim。
4. **Q11 human/source audit**：仍然必须完成，但不再是唯一 blocker。

## 6. 下一步唯一允许的主工程

暂停 Layer 3 learning。下一版 generator 必须直接实现 `cache06.md` 1580–1658 与 1866–1878 的 contract：

```text
source-grounded T1 contracts
× two report streams / 4–6 obligations
× shared-prefix finite-state terrestrial process
× public model-derived satellite opportunities
× repeated owner query
× async query / SEND / gateway receipt / final ACK
× normal send-as-probe
× action-dependent remaining resources
→ exact non-anticipative oracle
→ mechanism gates
→ strong-baseline ladder
→ structure coverage / holdout
```

至少先通过四个机制门：

1. non-separable cross-stage witness；
2. dynamic sufficiency witness；
3. dedicated query / passive feedback / normal-send-as-probe competition；
4. resource/evidence/timing interventions 能按预期消除对应困难。

Generator 不允许根据 proposed method 成绩选 case；easy、shortcut、information-infeasible、physical-invalid control 必须继续保留并分账。

