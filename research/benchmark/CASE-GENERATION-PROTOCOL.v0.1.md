# Case Generation & Validation Protocol v0.1

状态：Layer 1 case-construction authority / pre-release  
日期：2026-10-04

本协议规定：一个 source-supported Operational Family 怎样扩成大规模、非 toy、可自动审计的 benchmark cases。它继承 `BENCHMARK-CONSTRUCTION-PROTOCOL.v0.1.md`，重点解决 generator、oracle、validity filter、hardness shaping 与 held-out split。

## 1. Design principle

Case generator 不拥有任务语义。它只能在 source profile 已经定义的义务、authority、capability 与参数边界内实例化世界。

完整流水线：

    source snapshot / profile registry
    → family contract
    → world instantiation
    → obligation compilation
    → authority/capability derivation
    → full-state oracle solve
    → source/solvability filters
    → observation projection + alias worlds
    → decision-validity filters
    → hardness annotation
    → shortcut / ordinary-baseline audit
    → held-out assignment
    → source/expert validation
    → frozen case artifact

生成规模来自 profile × regime × site/device × trace × observation projection，而不是增加同义 Family 名。

## 2. Variable provenance classes

Case 中每一个影响 state transition、legal action、completion predicate 或 oracle 结果的变量，都必须标注 provenance class。

### FIXED_BY_SOURCE

来源明确给出离散值/规则，generator 不得改写。

例：
- Yining 的 15 min / 1 h / 15-15-30 min warning-delivery timing；
- DZ/T 0450 的 ≥7 d local cache；
- source-defined authority chain；
- source-defined path priority。

### SOURCE_RANGE

来源给出合法范围、等级表或多个允许配置，generator 可以在范围内采样。

例：
- DB44 不同 monitoring grade × warning level 的 reporting cadence ranges；
- source-defined device/path classes；
- standard-permitted site profiles。

采样必须记录原始 range 与 sampling rule。

### EMPIRICAL_TRACE

来自真实观测、field trace、weather/solar/contact trace、deployment log 或可追溯数据集。

要求：
- 保存 source id、time/site range 与预处理版本；
- train/dev/test 切分不能让同一 trace window 泄漏到多个 split；
- 若 trace 只覆盖单一场景，不能外推为行业分布。

### CONTROLLED_STRESS

不是 field-calibrated 概率，而是为了覆盖边界/故障/hardness 进行的显式干预。

允许：
- prolong outage within a declared stress envelope；
- remove one path to test redundancy；
- stale one observation field；
- reduce resource budget to a declared boundary cell。

不允许：
- 通过反复调参数直到 our policy 获胜；
- 把 stress value 写成“现实典型值”；
- 用 stress 替代 source-required nominal profiles。

所有 CONTROLLED_STRESS case 必须单独报告。

### UNRESOLVED

来源尚未定义、当前又会影响任务正确答案的变量。

规则：**禁止采样。**

遇到 UNRESOLVED：
- 若该变量不影响当前 case 的 legal plan / success predicate，可从 case contract 中删除；
- 若会影响答案，case 标 `SOURCE_GAP`，不得进入生成集；
- 不允许用 uniform/random/default/reward weight 静默填补。

## 3. World instantiation

每个 world 必须从一个或多个兼容 source profiles 合成，并保存 field-level provenance。

### 3.1 Profile compatibility

组合两个 source profiles 前必须检查：
- hazard / monitoring scope 是否兼容；
- actor/authority 是否冲突；
- time semantics 是否能共存；
- device/path capability 是否可同时成立；
- 一个 profile 是否只是 adjacent evidence，而另一个拥有 task authority。

Adjacent source 只能补 mechanism/capability plausibility，不能覆盖 direct geohazard profile 的 obligation/authority。

### 3.2 World state minimum

T1 至少包含：
- operational/warning state；
- monitoring obligations；
- device energy/storage/health；
- path capabilities and availability；
- time/contact/weather trace where relevant；
- evidence values + timestamps + owner/scope；
- source-profile completion predicates。

T2 至少包含：
- warning candidate + validity/expiry；
- verification/publication state；
- actor/authority graph；
- recipient graph；
- delivery channels + availability/latency；
- attempt / acknowledgement state；
- source-profile deadlines；
- response-handoff state。

## 4. Obligation compilation

Generator 不直接生成 reward。它生成 obligation ledger。

每条 obligation 必须包含：
- `obligation_id`；
- protected subject；
- release condition/time；
- completion predicate；
- timing/cadence semantics；
- authority owner；
- source-defined priority（若有）；
- expiration/cancellation rule（若有）；
- provenance。

如果两个义务竞争资源，但来源没有定义优先级：
- oracle 先求是否存在同时满足全部义务的计划；
- 若存在，case 可继续；
- 若不存在且来源没有 priority/order，则标 `OBJECTIVE_AMBIGUOUS`，不得用人工 scalar reward 决定牺牲谁。

## 5. Authority and legal-action derivation

Legal action set 必须由 source profile + family contract 导出。

禁止：
- 因 simulator API 存在就把 API 暴露给 Agent；
- 因研究方便让 center 绕过 local autonomy；
- 把 device-local automatic failover 改成 center per-slot routing，除非 profile 有 authority evidence；
- 让 communication Agent impersonate warning publication authority。

若 source-backed action 当前 simulator 不支持，标 `SIMULATOR_GAP`，case 暂停，不降格语义。

## 6. Full-state oracle

Oracle 的第一职责是可解性与合法性，不是产生单一 gold action。

### 6.1 Output

Oracle 至少返回：
- `feasible_success_plan_set`；
- `valid_terminal_state_set` 或 success predicate witness；
- legal actions at each oracle-relevant decision point；
- violated hard constraints for infeasible worlds；
- raw resource metrics；
- Pareto frontier when multiple valid plans exist。

### 6.2 No arbitrary scalarization

只有 source 明确给出优先级/顺序/成本关系时，oracle 才能据此排序。

否则：
- multiple valid success plans 全部接受；
- energy / latency / bytes / monetary cost 分开报告；
- 不为生成唯一答案而发明 reward weights。

### 6.3 Oracle variants

- `FULL_STATE_FEASIBILITY`：知道当前真实隐藏状态，不知道未来随机结果；
- `CLAIRVOYANT_UPPER_BOUND`：额外知道 frozen exogenous trace，仅作 upper bound；
- `OBSERVATION_MATCHED_SEARCH`：只使用与 evaluated policy 同等观测，用于 deterministic/search baseline。

三者不能混为同一个 baseline。

## 7. Automatic validity filters

每个 candidate case 在进入 benchmark 前依次过以下过滤器。

### V0 SOURCE_COMPLETE

所有 answer-relevant fields 不是 UNRESOLVED；source/profile compatible。

失败：`SOURCE_GAP`。

### V1 SOLVABLE

`FULL_STATE_FEASIBILITY` 至少存在一个合法成功计划。

失败原因区分：
- `GENERATOR_INVALID`：world 组合自身矛盾；
- `SOURCE_INFEASIBLE`：来源允许的真实极端状态本就不可满足；若 benchmark target 包含正确 abstain/failure handling，可进入独立 impossible split，否则不进入主 success benchmark。

### V2 MULTIPLE_LEGAL_OPTIONS

至少一个决策点存在两个以上 legal actions/plans。

若从起点就只有一个 supported action/plan：
- 标 `UNIQUE_READY`；
- 降入 Conformance Split；
- 不计入 Decision Benchmark hardness。

### V3 COMMON_SAFE_ACTION

构造与当前 observation 一致的 alias worlds。

若存在同一个 legal action 在所有 alias worlds 都 outcome-equivalent / zero-regret，并且无需额外 evidence：
- 标 `COMMON_SAFE_ACTION`；
- 该 observation state 不测 Evidence Sufficiency；
- 可留作 sanity/conformance，不进入 H1/H2。

### V4 OBSERVATION_RELEVANCE

对 intended H1/H2 case，至少存在一个新增/更新 evidence field 会改变：
- legal action set，或
- feasible-success plan set，或
- source-defined action ordering。

否则标 `EVIDENCE_IRRELEVANT`。

### V5 BINDING_CONSTRAINT

至少一个 source-backed resource/time/authority constraint 对 feasible set 有实际约束作用。

若解除该 constraint 后 feasible set 不变，且其他 constraint 也不 binding，标 `NO_BINDING_CONSTRAINT`。

### V6 OUTCOME_SEPARATION

至少两个 legal policies/plans 在 frozen world 中产生不同 obligation-feasibility transition 或不同 success/failure terminal outcome。

若全部合法 policy outcome-equivalent：`OUTCOME_EQUIVALENT`。

### V7 OBJECTIVE_DEFINED

如果不是所有义务都能同时满足，source 必须提供 priority/order/completion semantics。

否则：`OBJECTIVE_AMBIGUOUS`，返回 source research queue，不进入 benchmark。

### V8 SHORTCUT_AUDIT

至少运行：
- no-op；
- fixed source rule；
- ordinary local automatic mechanisms；
- simple greedy/EDF/fixed-priority where semantically legal。

若一个不使用 target capability 的 trivial/ordinary baseline 饱和 evaluator，标 `SHORTCUT_SOLVED`；case 降级或重构。

### V9 EVALUATOR_SOUNDNESS

对 oracle success/failure plans做 mutation tests：
- multiple legal success terminal states must pass；
- authority violation must fail；
- missed source deadline/cadence must fail；
- unrelated protected-state corruption must fail；
- textually plausible but physically unexecuted action must fail。

失败：`EVALUATOR_INVALID`，修 evaluator，不修 policy。

## 8. Observation projection and alias worlds

Partial observability 不能靠任意藏字段制造。

Projection 来源只允许：
- source 中确实只在 local device / monitoring center / authority 一侧可见的 state；
- source-backed delayed/stale telemetry；
- capability-dependent query result；
- declared CONTROLLED_STRESS observation loss。

每个 H1/H2 case 保存：
- full world state；
- policy observation；
- hidden fields；
- alias-world ids；
- which evidence item separates legal plans。

EvidenceNeed 必须能被 oracle 的 alias-world analysis 复现。

## 9. Hardness shaping

Generator 可以定向生成 hardness bucket，但不能以模型表现反向调世界。

### H0 Conformance
- unique legal plan or deterministic contract check。

### H1 Partial observation
- multiple alias worlds require different legal/feasible actions。

### H2 Active evidence acquisition
- a legal query/probe can resolve H1 ambiguity；query has source/controlled cost。

### H3 Resource conflict
- multiple simultaneously valid obligations share a binding resource；source priority exists if not all can be met。

### H4 Long-horizon opportunity
- current action changes future ability to satisfy later source-backed obligations。

### H5 Recovery divergence
- link can be restored while knowledge/decision/task state remains unrecovered。

### H6 Authority-gated multi-hop delivery
- T2 warning must traverse multiple authorized actors/channels/acknowledgements under deadlines。

Hardness label is descriptive, not a reward.

## 10. Family-specific generation plans

### T1 Monitoring Information Continuity

Generator axes:
- DB44 monitoring grade × warning level → source-range cadence profiles；
- DB11 no-rain/rain + GPRS/BeiDou energy/path profile；
- DZ/T0450 normal → outage → reconnect retention/recovery lifecycle；
- Jiaozuo NB → 4G/5G → BeiDou priority + center-visible device state；
- source-backed no-sun / battery-only profiles；
- empirical or frozen contact/weather traces where available。

Restrictions:
- unresolved reconnect priority cases do not enter conflict benchmark；
- path override is only generated when active profile grants policy authority；
- local emergency autonomy is never disabled to create difficulty。

### T2 Warning Delivery & Response Handoff

Generator axes:
- Yining actor cascade + 15 min / 1 h / 15-15-30 min deadlines；
- phone primary + WeChat/SMS redundancy + retry/alternate-contact semantics；
- satellite-phone fallback where source profile enables it；
- Baoshan 12/6/2 h progressive states + 30/50 min feedback；
- stateful duplicate suppression for unchanged already-called areas；
- recipient/channel reachability traces as EMPIRICAL_TRACE or declared CONTROLLED_STRESS。

Restrictions:
- policy cannot create/approve warning without authority event；
- deadline values stay source-profile-specific；
- T2 remains a boundary split unless final benchmark scope explicitly includes downstream warning delivery。

## 11. Split policy

Random row split is forbidden as the primary benchmark split.

Preferred held-out axes:
1. source family / standard family；
2. jurisdiction；
3. site / deployment；
4. device / communication capability profile；
5. operating regime；
6. event/trace window。

At least one main test split should require structural generalization beyond a new random seed.

Examples:
- train on national/industry profiles + one local jurisdiction, test another jurisdiction；
- train normal/escalation/degraded, test reconnect；
- train GPRS/BeiDou profile, test another source-backed terrestrial+satellite profile；
- keep entire weather/contact traces held out。

## 12. Scale-up and sampling

Do not freeze an arbitrary target case count early.

Scale-up stops when:
- required coverage cells are populated；
- rare boundary/failure cells have enough cases for stable estimates；
- confidence intervals/power analysis meet reporting target；
- source/jurisdiction held-out splits remain large enough；
- duplicate/near-duplicate rate stays below release threshold。

Thousands of cases may be appropriate, but the number follows coverage and statistical requirements, not aesthetics。

## 13. Source/expert audit

Before release, every Family/profile gets two audits:

### Source audit
- source statement exists；
- extraction did not invert authority/priority/time semantics；
- adjacent evidence is not used as direct task authority；
- parameter provenance class is correct。

### Task audit
- case wording/observation does not reveal hidden oracle state；
- legal action set matches authority；
- oracle solution set is complete enough for evaluator；
- no invalid shortcut；
- no arbitrary reward determines correctness。

Human audit samples should be stratified by Family × source profile × hardness × split, not purely random。

## 14. Frozen case artifact

Every released case contains:
- immutable case JSON matching `CASE-SCHEMA.v0.1.json`；
- source/profile refs；
- variable provenance map；
- full world seed/trace refs；
- observation projection；
- legal capability/authority contract；
- obligation ledger；
- oracle solution-set metadata；
- validity/filter results；
- split assignment；
- generator version；
- known limitations。

Raw ground truth/oracle-private fields live outside the Agent-visible payload。
