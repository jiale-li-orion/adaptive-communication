# Benchmark Construction Protocol v0.1

状态：Layer 1 construction authority / pre-task-freeze  
日期：2026-10-04

本协议规定什么样的现实材料可以进入 Source-grounded Emergency Communication Benchmark，什么样的候选只能留在 conformance、mechanism 或 exploratory 层。它不定义某个算法，也不允许从当前 capability、旧 simulator action surface 或历史 positive/negative experiment 反推任务。

**生成顺序固定为：外部 operational corpus → canonical operational objects → taxonomy → candidate family → source validation → state/action/transition/oracle contract → simulator mapping → case generator → validity/hardness audit。**

旧 repo 只在 candidate 已经由外部 corpus 产生之后，负责 semantic dedupe、historical closure、组件复用和 falsification。

## 1. Benchmark 的研究对象

Benchmark 测量的是：

在真实来源可追溯的 Operational Obligation 下，当通信状态部分可见、证据会老化、获取证据本身有成本、链路与能源机会受限时，一个 policy 是否能在多个合法行动之间做出正确选择，并保持未来义务仍可满足。

最小闭环：

    External requirement / field evidence
    → Operational Obligation
    → frozen environment + observation boundary
    → legal policy alternatives
    → execution
    → obligation-feasibility transition
    → external oracle

只有“读状态 → 写唯一正确配置”的任务属于 Conformance Suite，不属于 Decision Benchmark。

## 2. Benchmark construction 的外部方法学来源

### 2.1 NeurIPS Agentic Benchmark Checklist：先证明 validity

Zhu et al., Establishing Best Practices for Building Rigorous Agentic Benchmarks, NeurIPS 2025 Datasets & Benchmarks Track，把 agentic benchmark 的严谨性拆成 Task Validity、Outcome Validity 与 Benchmark Reporting。

本项目直接继承：

1. 环境、工具和 source snapshot 版本冻结；
2. 每个 case 清理历史状态；
3. Agent 与 ground truth / oracle 隔离；
4. 每个可评测 case 必须可解；
5. Oracle solver 能自动解全部正常 case；
6. 检查 shortcut / exploit；
7. evaluator 接受所有合法成功终态，不只匹配单一轨迹；
8. 同时检查相关状态与不应被改动的无关状态；
9. 报告 trivial / non-AI baseline、置信区间与 known flaw。

### 2.2 DORA：taxonomy 同时绑定 operational need 与 capability complexity

DORA 的任务 taxonomy 一方面对应真实灾害业务阶段，另一方面形成从 atomic perception 到长链 report synthesis 的能力复杂度层级；专家从 operational need 写任务，并绑定数据 manifest、可 replay 的 gold trajectory 和 structured outcome。

本项目继承：

- Task Family 先对应真实 Operational Obligation；
- hardness / capability complexity 作为第二组正交维度；
- annotation 必须可 replay；
- final outcome 与 trajectory 分开评估；
- data provenance 与 task annotation provenance 分离。

### 2.3 6G-Bench：taxonomy 必须有外部来源，规模来自 generator + validation

6G-Bench 从 3GPP、IETF、ETSI、ITU-T、O-RAN 等标准化活动抽取 decision tasks，再形成 capability taxonomy；大规模 scenario 生成后经过自动筛选与专家验证。

本项目继承：

- 一级 taxonomy 必须能回指 field / standard / operational source；
- scenario instance 可以程序化扩展，但 Task Family 不能由 LLM 自行发明；
- automated checks 与 source/expert audit 同时存在；
- train/dev/test 优先按 site、event、operating regime、source family 做 held-out，而不是只随机切同分布参数。

### 2.4 2026 agent benchmark surveys：benchmark 数字不是自解释的

最新 agent evaluation survey 强调 capability、scoring paradigm、environment topology 必须同时说明，并指出 contamination、non-determinism、execution cost 等是结构性威胁。

本项目因此不把“一个总成功率”视为完整 benchmark 结果。每个数字必须能回到：测什么能力、怎样判分、在哪种环境与成本边界下测。

## 3. 三层对象：Family、Case、Stress Axis

### 3.1 Operational Task Family

Family 的定义来自义务，不来自当前 tool。

每个 Family 必须明确：

- obligation subject；
- trigger / release condition；
- required outcome；
- completion condition；
- failure condition；
- time semantics；
- authority boundary。

例如“恢复后补发缓存”只有在外部来源证明存在持续数据义务与恢复行为时，才可能成为 Family；“调用 upload_records”永远不是 Family。

### 3.2 Case

Case 是一个 Family 在具体 frozen scenario 下的实例：

- site / topology；
- device capability profile；
- energy state；
- connectivity trace；
- obligation arrivals；
- observation boundary；
- exogenous trace / random seed。

一个 Family 应对应大量 Case，而不是一个手写 episode。

### 3.3 Stress / Hardness Axis

Stress axis 不拥有任务语义，只改变 decision difficulty：

- partial / stale / conflicting evidence；
- energy scarcity；
- contact-window scarcity；
- payload / airtime limit；
- storage pressure；
- correlated failure；
- unknown execution outcome；
- multi-obligation contention；
- long-horizon opportunity dependence；
- scale / heterogeneity。

一个 failure mode 不能因为“更难”就自动升格为 Task Family。


## 3.5 Gate 0 — Corpus-first / Historical Closure

Gate 0 在所有 admission gate 之前执行，但它有两个方向完全不同的约束。

### 3.5.1 Corpus-first

候选 Family 必须先由外部 corpus 产生。允许的来源包括：

- field deployment；
- government / industry standard；
- operational workflow；
- device capability document；
- peer-reviewed adjacent system；
- current ASC / wireless benchmark taxonomy。

候选不得由以下对象直接生成：

- 当前 simulator 已有 action；
- 旧 reward；
- 旧 policy name；
- 某个 historical positive result；
- “这个机制看起来适合 Agent”的直觉。

如果外部 evidence 支持一个新的 operational obligation / authority / action / state，而当前 simulator 没有它，应记录为 **SIMULATOR_GAP**，而不是因为“现在跑不了”就删除候选。

### 3.5.2 Historical Closure

只有在候选已经由 corpus 产生之后，才查询 `local_research/REPO-HISTORY.md` 与对应 episode。

历史结果只回答：

1. 这个语义是否已经被旧实验完整研究过；
2. 哪些 ordinary mechanisms 必须作为 baseline；
3. 哪些 measurement / contract bug 已知；
4. 哪些旧 state/action/evaluator 可以复用。

若新候选与旧问题在 **operational obligation + authority + information structure + action set + binding constraint** 上语义等价，则标 `HISTORICALLY_CLOSED`，直接引用旧 verdict，不重复跑实验。

若至少一项由新的外部 evidence 实质改变，则它是新 candidate；历史结果只能约束 baseline，不能 veto。


## 4. Candidate Admission Gate

候选必须依次通过六道 Gate。任一道失败，都不得进入正式 Decision Benchmark。

### Gate A — Operational Grounding

必须回答：

1. 义务从哪里来：field / standard / government / peer-reviewed deployment 中至少有一类可靠证据支持这个 operational need；
2. 能力从哪里来：设备与链路 capability 有独立来源，不能用 capability 反推义务；
3. 约束从哪里来：deadline、freshness、能耗、窗口、payload 等分别记录来源层级；
4. 哪些仍是假设：未知项进入 explicit assumption ledger；
5. 是否与已有 local autonomy 冲突：已有自动机制必须成为 shared baseline，不能人为删除来制造中心决策。

“存在 API / 存在链路”不等于通过 Gate A。

### Gate B — Construct / Task Validity

必须声明 target capability，并验证“具备该能力”确实是任务成功的必要组成。

要求：

- case 可由 oracle 自动解；
- 无 do-nothing、always-fallback、fixed-config 等 trivial shortcut；
- 不因 simulator bug 或 unavailable tool 变成 impossible；
- ground truth 与 Agent observation 隔离；
- environment、tool、source snapshot 冻结；
- invalid / impossible case 若保留，正确 abstain / reject 必须属于 target capability。

### Gate C — Decision Validity

这是本项目额外增加的核心 gate。

一个正式 Decision Case 必须存在至少一个 decision point，使：

1. 同一 observable history 下有两个或以上合法行动；
2. 不存在一个对所有 alias world 都 zero-regret 或 outcome-equivalent 的 common safe action；
3. partial observation 或新增 evidence 能改变 action feasibility / ranking；
4. 至少一个真实资源或时序约束实际 binding；
5. 不同合法 policy 产生 materially different physical outcomes；
6. 差异最终进入 obligation feasibility，而不只进入任意加权 reward。

如果 compiler 在 case 起点就闭合成唯一 supported plan，该 case 自动降为 Conformance。

### Gate D — Outcome Validity

核心 evaluator 检查环境终态与 obligation ledger，不检查“模型有没有说得像对”。

必须提供：

- External Oracle；
- obligation ledger；
- action legality / authority check；
- all-success-state set 或 success predicate；
- irrelevant-state protection；
- deadline、freshness、energy、cost 等独立原始量；
- counterfactual replay；
- no-op / random / static policy 无法利用 evaluator 漏洞得高分。

LLM-as-a-judge 只能评价无法结构化的辅助输出，不能拥有核心 success 判定。

### Gate E — Hardness

通过 validity 不代表有研究价值。每个 Family 还必须证明：

- ordinary deterministic baseline 不饱和；
- deterministic search / constrained planner 与 learned / LLM policy 有比较空间；
- difficulty 随信息结构、资源或 horizon 单调或可解释变化；
- model failure 不只是通信知识缺失、格式错误或工具 schema 不熟；
- perfect-observation、oracle-communication、no-resource-conflict 等 ablation 能解释困难来源。

### Gate F — Non-toy / Coverage

多跑 seed 不能把 toy task 变成 benchmark。

正式 Family 需要：

1. 来源覆盖：跨独立 source family；若只有单部署，就明确 single-deployment scope；
2. 场景覆盖：多个 topology、device、operating regime，而不是一个 hand-tuned cell；
3. 结构覆盖：normal、boundary、failure/recovery、resource-binding cases；
4. held-out coverage：site / event / regime / source-family 级 held-out；
5. 统计覆盖：case 数由置信区间或功效分析决定；
6. shortcut coverage：trivial、ordinary、oracle 三类 baseline；
7. maintenance：case schema、generator、source snapshot、known flaw 有版本策略。

## 5. Taxonomy Construction Rule

正式 taxonomy 先由 Operational Corpus Ledger 聚类，再使用正交坐标描述。Family 的数量不靠预设，也不靠 simulator action 数量决定。一个小数量、高语义覆盖的 Family 集合，可以通过大量跨 source/site/device/regime 的 Case 构成非 toy benchmark。

### 5.1 Family Identity Test

一级 Family 的 identity 由四个对象共同定义：

1. protected operational subject：最终保护/交付的对象是什么；
2. completion predicate：什么状态才算义务完成；
3. authority owner/chain：谁有权做决定、确认完成；
4. lifecycle scope：义务从何时产生，到何时解除/完成。

两个 candidate 若上述 identity 相同，只因为 warning level、deadline/cadence、link type、energy state、failure/recovery phase、observation quality 或 available capability 不同，默认合并到同一 Family，差异进入 Case / Operating Regime / Hardness / Capability axis。

只有当 protected subject、completion predicate 或 authority chain 发生实质改变时，才有理由拆成新的一级 Family。

因此下列对象默认不能单独生成 Family：

- probe / EvidenceNeed；
- fallback / path switching；
- cache / retransmission；
- sampling/upload-frequency adjustment；
- warning level 本身；
- outage / reconnect 本身；
- remote query / configuration；
- 某一种 radio / satellite capability。

每次 taxonomy freeze 前必须执行一次 merge audit：若两个 Family 可以共享同一 completion predicate 与 authority owner，只是运行阶段不同，应优先合并。

### Axis O — Operational Obligation

一级分类只从 Operational Corpus Ledger 聚类产生；当前 draft 见 local research，不在 tracked protocol 里冻结具体 Family 名。任何 Family 必须能回指一组 canonical operational objects 和 source bundle，并通过 Family Identity Test。

### Axis H — Decision Hardness

每个 Family 再标：

- H0 deterministic / conformance；
- H1 partial-observation choice；
- H2 active evidence acquisition；
- H3 resource-conflict multi-obligation choice；
- H4 long-horizon opportunity / recovery choice；
- H5 recovery with incomplete / divergent state。

H0 可以进入 release 作为 sanity / conformance split，但不能用于证明 Agent policy 能力。

## 6. Candidate Status

候选状态与 CANDIDATE-SCHEMA.v0.1.json 保持一致：

- SOURCE_GAP：candidate 有合理 operational hypothesis，但关键现实来源不足；
- SOURCE_SUPPORTED：Family identity / obligation 已有足够外部来源，尚未完成后续 mapping/validity；
- SIMULATOR_GAP：source-backed contract 需要当前 substrate 尚不存在的 state/action/actor/transition；
- HISTORICALLY_CLOSED：与旧问题在 obligation + authority + information structure + action set + binding constraint 上语义等价，直接继承旧 verdict；
- ADMISSION_READY：source、history dedupe、contract、simulator mapping 与 oracle 已闭合，可生成正式 case 做 validity/hardness audit；
- BENCHMARK_ADMIT：case family 已通过 task/outcome validity、shortcut、hardness 与 non-toy coverage audit。

BENCHMARK_ADMIT 只能由完整 construction pipeline 产生，不能由单次 simulator positive result 产生。

## 7. Required Candidate Record

每个 candidate 至少记录：

    candidate_id
    provisional_family
    canonical_operational_objects
    operational_obligation

    source_bundle:
      requirement
      field
      standard_or_government
      capability
      parameter

    evidence_strength
    known_unknowns
    authority
    observation_boundary
    candidate_actions
    shared_ordinary_mechanisms
    resource_constraints
    time_semantics
    oracle_definition
    success_predicate
    historical_semantic_match
    simulator_mapping
    simulator_gaps
    hardness_axes
    heldout_axes
    status
    blocking_evidence

## 8. Baseline Ladder

正式 benchmark 不允许只报 our Agent vs weaker Agent。

每个 Family 至少包含：

1. no-op / trivial；
2. static source-backed rule；
3. ordinary greedy / EDF / fixed-priority / automatic fallback；
4. deterministic constrained search / planner；
5. clairvoyant / full-state oracle upper bound；
6. LLM / reasoning agent；
7. learned policy，仅当状态空间和重复选择确实需要时加入。

任何新 policy 的增益必须说明越过了哪一级 baseline。

## 9. Benchmark Release Unit

一个可发布 benchmark 是 measurement contract，不是一个脚本。最小发布单元：

- source snapshots；
- task-family definitions；
- case generator；
- frozen environment；
- tool / capability schemas；
- oracle solver；
- success predicates；
- baseline implementations；
- held-out split；
- replay traces；
- validity / shortcut audits；
- statistical reporting；
- known-flaw ledger。

## 10. 当前执行顺序

当前 Layer 1 的方向、taxonomy、closure 与工程状态以 [`LAYER1-AUTHORITY.md`](LAYER1-AUTHORITY.md) 为唯一 current-state authority；本协议只拥有 construction / admission 方法，不由局部 generator 版本改写全局方向。

    external operational corpus
    → canonical operational objects
    → provisional taxonomy
    → candidate family + source validation
    → historical semantic dedupe
    → state/action/transition/oracle contract
    → simulator mapping / explicit simulator gaps
    → case generator
    → validity / hardness audit
    → held-out split + scale-up
    → policy evaluation

任何局部 simulator / Agent Infra 改动，若不能解除某个 corpus/taxonomy/admission blocker，默认不做。
