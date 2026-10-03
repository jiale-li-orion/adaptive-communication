# Agentic experiment evidence catalog

本目录不是“运行输出垃圾桶”，而是 Agentic Communication 的实验资产库。实验目录名一旦进入
cache、runner、claim 或论文引用，就保持路径稳定；后续通过本索引改变它的**研究地位**，不靠搬目录
改写历史。

## 1. 两个正交维度

### Research role

| Tier | 含义 | 允许用途 |
|---|---|---|
| **F — formal** | 当前 claim / 主表 / held-out / 强对照的正式证据 | 正文主表、claim、artifact verdict |
| **S — supporting** | 已验证机制、消融、上下界、敏感性或公平性证据 | 正文机制表、appendix、答审、后续重组表格 |
| **D — development-diagnosis** | 被后续版本 supersede，但保留真实失败与方法演进信息 | failure analysis、历史消融、附录诊断；不得直接冒充当前 main result |
| **B — substrate/baseline** | pre-API、普通通信基线、source/robustness/attribution 基础设施 | 公平性、benchmark validity、通信底座表格 |

### Artifact role inside one experiment

| Artifact | 地位 | Git policy |
|---|---|---|
| `aggregate.json` / `audit.json` / `source-manifest.json` / `summary.json` | compact evidence / 可直接重算表格 | formal 或被论文引用时晋升 |
| `paper-results.json` / generated table source | 数值 authority | 必须晋升 |
| `result.json` / devset / frozen inputs | replay / mechanism payload | 体积小且正文/消融需要时晋升，否则本地保留 |
| `runtime_trace.jsonl` / per-tick trace / 大型 frozen input dump | raw replay payload | 默认本地；可外置归档，不作为单独 claim authority |
| `runner.log` / progress / rc / retry residue | ephemeral execution log | 本地，不用于填表 |

因此，“不进入远端”只描述 storage policy，不代表“不可复用”。论文数字仍遵守
`result -> generator -> paper/generated -> manuscript` 单一来源链。

## 2. F — 当前正式论文证据

| Experiment | 当前用途 | 远端保存粒度 |
|---|---|---|
| `main-table-v6-confirmatory/` | A7；query-negative 3 tasks × 5 seeds × 4 arms 主表 | aggregate/audit/claim candidate/manifests + per-row summaries |
| `woa-style-baseline-v1/` | A8；same-interface WirelessOpsAgent-style 强对照 | aggregate/audit/fairness/analysis + audit 所需 authorization records |
| `heldout-qili-2024-w1/model-transfer-v7/` | A9；Qili + NASA POWER 2024 + DeepSeek/MiMo transfer | aggregate/audit/manifests + per-seed summaries |
| `query-positive-gateway-backup-v1/` | A10/A11；owner query -> guard closure -> backup -> physical gain | deterministic gate、aggregate/audit/manifests、DeepSeek/MiMo summaries；raw trace 本地 |
| `paper-v1/` | 四张正式论文表的 compact numeric authority | `paper-results.json` + human-readable table projection |

这五组是当前正文数字的第一来源。formal 目录中的大 trace 仍是 replay payload，不需要和 compact
authority 一起进 Git。

## 3. S — 可复用的机制 / 消融 / 后续填表证据

这些实验当前没有独立 A* claim，但已经回答了明确问题；后续写 appendix、机制表、答审或重新组织
实验时应优先复用，不应重跑同一问题。

| Experiment | 已验证问题 / 可复用表格 |
|---|---|
| `causal-interface-probe-v1/` | CF/CS 单变量干预：compact evidence 成本与 explicit no-action sufficiency 的独立作用；当前机制表直接使用 |
| `mimo-decision-closed-projection-probe-v1/` | M/P/D：retired-plan unresolved guard 对 MiMo 的干扰与 v7 精确修复；当前机制表直接使用 |
| `compiled-checklist-v1/` | CR deterministic consumer：证明 A7 workload 已被编译语义高度决定，限制“LLM reasoning” claim |
| `v6-mechanism-activation-audit.json` | 123/123 unique-ready、visible EvidenceNeed=0；A7 mechanism-activation ceiling |
| `basis-selection-headroom-v1/` | alternative-proof / minimum-basis headroom kill criterion；支持“不实现伪算法”结论 |
| `o1-o6-mechanism-eligibility-audit-v1.json` | O1–O6 哪些机制真正可激活；用于实验覆盖度/任务选择说明 |
| `action-conditioned-context-localized-o2-v1/` | action-conditioned selector 相对 candidate+FullDump 的 evidence/protocol contraction；可做 Context 成本表 |
| `action-context-devset-v1/` | candidate/guard/dependency compiler 的 deterministic devset；可做 correctness appendix |
| `dependency-expressiveness-probe-v1/` | syntax guard vs current-state partial evaluation 的表达能力差异；可做 compiler ablation |
| `plan-id-interface-v1/` | plan-ID selection + Runtime typed expansion；可做 interface-mechanism ablation |
| `persistent-config-intent-conformance-v1/` | semantic intent 跨异步执行持久化；可做 execution-semantics appendix |
| `no-action-sufficiency-v1/` | zero-effect hold 的 sufficiency / stopping；可做 stopping ablation |
| `query-positive-closure-gap-v1.json` | query-positive 早期 coverage gap：query 后 guard 未闭合；用于解释为何补 ordinary evidence->guard evaluation |
| `o5-context-update-ablation-v1/` | Task revision / Context update 组件消融 |
| `o5-query-delay-multiseed-v1/` | remote query delay 跨 control opportunity 时的 20-seed physical divergence；可做 latency sensitivity |
| `o5-query-delay-backhaul-sweep-v1/` | backhaul delay sensitivity |
| `o5-query-delay-opportunity-sweep-v1/` | opportunity-boundary sensitivity |
| `o5-query-delay-threshold-summary-v1.json` | 上述 delay/opportunity sweep 的 compact threshold summary |
| `o6-query-delay-multiseed-v1/` | compound O6 下 query delay 的异步执行后果；可做跨任务机制复核 |
| `o5-scoped-query-multiseed-v1/` / `o6-scoped-query-multiseed-v1/` | scoped query 对 O5/O6 的多种子后果 |
| `o5-execution-layer-audit-v1/` | query / plan / executor / physical layer ownership 分解 |
| `o5-task-revision-consequence-v1/` | Task authority revision 的真实物理后果 |
| `mimo-nonblocking-dependency-projection-probe-v1/` | 比 v7 更激进的 projection 是否继续有益；negative/ceiling evidence |

其中已经进入当前 paper-v1 机制表的 compact 结果已晋升；其余完整本地数据继续保留，只有真正进入
正文/appendix 数值链时才 promotion，避免把几十 MB trace 当作 Git 数据库。

## 4. B — benchmark / baseline / fairness substrate

| Experiment | 用途 |
|---|---|
| `o2-risk-escalation-v1/` / `o2-localized-risk-escalation-v1/` | A1 runtime/physics conformance |
| `o2-diagnosis-first-v1/` / `o2-baseline-matrix-v1/` | A2 ordinary Agent baseline isolation |
| `communication-baseline-matrix-v1/` | A6 Local/AoI/EnergyAware/mission/EDF/maxcov + evaluator-only oracle |
| `source-period-smoke-v1.json` / `robustness-matrix-v1/` | A3 source-period / robustness substrate |
| `task-transfer-qili-v1/` | A4 source-derived Operational Task transfer substrate |
| `attribution-matrix-infra-v1/` | A5 cumulative gold-replacement / attribution infrastructure |
| `model-context-inputs-v1/` | task-conditioned / FullDump / generic-ReAct frozen-input fairness；后续模型表仍可复用 |
| `catalog-smoke-v1.json` | task catalog smoke / schema conformance |

这些结果不是“旧了就没用”。它们承担 formal model comparison 的公平性与 benchmark validity；A7–A11
是在这层之上成立。

## 5. D — development diagnosis / superseded iteration

这一层保存真实失败、接口 bug、方法收敛过程。它们**可以复用做 failure analysis 或 appendix**，但
若要重新进入当前 claim/table，必须明确说明 superseded boundary，不能与 v6/v7 formal result 混写。

### Main-table evolution

- `main-table-v1/`：早期完整 Context/main-table 诊断。
- `main-table-v1b-shadow-projection/`：shadow projection 修复阶段。
- `main-table-v2-confirmatory/`：中止的 confirmatory；cache 已明确只作 development diagnosis。
- `main-table-v3-scope-authority/`：global Task authority bug 修复见证。
- `main-table-v5-corrected/`：plan-ID / scope / sufficiency 修正后的 seed0 正式前身。
- `main-table-v5-confirmatory/`：v6 前 confirmatory 前身。
- `r3-model/`：早期 DeepSeek R3 decision-state/every-context diagnosis。

### Decision-sufficiency / stopping evolution

- `o3-decision-sufficiency-transfer-devset-v1/`、`o3-decision-sufficiency-transfer-model-probe-v1/`、
  `o3-decision-sufficiency-transfer-model-probe-v1-repeat2/`、`o3-decision-sufficiency-transfer-model-probe-v1-repeat3/`。
- `o5-decision-sufficiency-devset-v1/`、`o5-decision-sufficiency-ablation-v1/`、`o5-decision-sufficiency-model-probe-v1/`。
- `o5-plan-local-stopping-devset-v1/`、`o5-plan-local-stopping-model-probe-v1/`、
  `o5-plan-local-stopping-model-probe-v1-repeat2/`、`o5-plan-local-stopping-model-probe-v1-repeat3/`。
- `o5-context-transition-devset-v1/`、`o5-context-update-model-probe-v1/`、`o5-context-update-model-probe-v2-decision-sufficient/`。
- `o5-transition-context-model-probe-v1/`、`o5-transition-context-model-probe-v2-decision-sufficient/`。
- `o5-saved-stopping-ablation-r3-readback-v1/`、`o5-saved-model-one-shot-continuation-v2-decision-sufficient/`、`o5-saved-model-backhaul-sensitivity-v1/`。

这些目录最有价值的不是“再拿来做主结果”，而是回答：某个设计为什么被引入、哪个 failure 是真实
模型 failure、哪个只是旧接口暴露了无关状态。需要写方法演进图或答审时，优先从这里取证。

## 6. Storage / promotion rule

`results/agentic/*` 默认本地保留，是为了阻止新实验自动把大 trace 推入 Git；它不是删除规则。

一次实验满足以下任一条件时，promotion compact evidence：

1. 数字进入正文、appendix、图或表；
2. 被 `results/CLAIMS.md` 某条 claim 引用；
3. 是复核 formal result 所必需的 aggregate/audit/summary/manifest；
4. 是关键 negative result / kill criterion，后续设计决策依赖它。

promotion 时优先提交 aggregate/audit/summary/manifest；若 compact 文件足以重算论文数字，就不把
raw trace 一并提交。若未来 artifact review 要求完整 raw run，应通过外部 archive / acquisition step
提供，并在 `artifact/AE.md` 登记其 hash 与获取方式。

一句话：**实验结果按研究价值归类，运行文件按复现职责分层；“大文件不进 Git”不能被解释成
“实验不值得保留”。**
