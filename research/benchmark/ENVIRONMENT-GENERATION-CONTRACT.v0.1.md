# Layer-1 Environment & Generation Contract v0.1

状态：**PRE-METHOD AUTHORITY / BENCHMARK RECONSTRUCTION CONTRACT**  
日期：2026-10-06  
上位依据：`/home/orion/Communications/调研cache.md`、`/home/orion/Communications/cache06.md`、[`LAYER1-AUTHORITY.md`](LAYER1-AUTHORITY.md)。  
用途：在下一版正式 generator 出现之前，先冻结“什么是环境、什么可以生成、什么不能为了 baseline/method 输赢修改”。

---

## 1. Benchmark 范式：source-grounded synthetic / simulation benchmark 是成熟做法

本项目不要求每个 episode 都是现场逐条采集的历史轨迹。可辩护的 benchmark 形式是：**现实来源约束问题空间，参数化 generator 在该空间内系统覆盖，simulator 因果执行，独立 evaluator/oracle 判定结果。** 这种范式在通信、自动驾驶与 embodied decision benchmark 中有直接先例。

| 先例 | Grounding | 具体 case 如何产生 | 对本项目的直接方法学启示 |
|---|---|---|---|
| **DeepMIMO** | 具体 3D 环境、Remcom Wireless InSite ray tracing | `ray-tracing scenario + 参数集合 → channel dataset`；参数化、可复现 | synthetic channel 不等于无依据；关键是物理模型、场景与参数配置可审计、可复现。Paper: https://arxiv.org/abs/1902.06435 |
| **CARLA Leaderboard** | NHTSA pre-crash typology + 道路/交通规则 | 真实交通冲突类型在不同道路、天气、位置中参数化实例化并由 simulator 执行 | scenario type 可以来自现实 taxonomy，而每个具体危险 episode 不必历史上原样发生。Docs: https://leaderboard.carla.org/scenarios/ |
| **ScenarioNet** | Waymo、nuScenes、Lyft L5、nuPlan 等真实驾驶数据 | 真实 traffic scenario 统一表示后在 MetaDrive 中重建、回放和交互 | 更强版本是 `real trace → canonical scenario → closed-loop simulator`；未来真实通信 trace 可用于升级本 benchmark。Paper: https://proceedings.neurips.cc/paper_files/paper/2023/hash/0c26a501df8fb919a0350e2df06b5d39-Abstract-Datasets_and_Benchmarks.html |
| **Waymax / Waymo CAT** | Waymo Open Motion Dataset；真实道路/test-track/crash data + ODD expert knowledge | logged scenario 进入 closed-loop simulator；危险/不可采场景也允许 fully synthetic stress；真实场景可修改 actor speed/position 做 counterfactual | controlled stress 合法，但必须由 coverage / ODD 需求驱动，而不是由某个待发表方法的输赢驱动。Waymax: https://waymo-research.github.io/waymax/docs/ ; CAT: https://waymo.com/blog/2022/12/waymos-collision-avoidance-testing/ |
| **Habitat Challenge** | Gibson / Matterport3D 等真实 3D scenes | 在 unseen environment 中自动采样起点、朝向、目标并在 simulator 中闭环执行 | `真实环境 + synthetic episode + hidden test scenes` 是成熟评测范式；episode generation 与 environment split 必须分离。Docs: https://aihabitat.org/challenge/2021/ |
| **ALFWorld** | ALFRED household goals / embodied task semantics | 任务映射到 TextWorld 抽象环境，在可控 simulator 中生成交互 episode | “task semantics 真实、episode 合成”可成立；抽象环境的 claim 必须限制在其模拟语义。Paper: https://arxiv.org/abs/2010.03768 |
| **6G-Bench** | 3GPP、IETF、ETSI、ITU-T、O-RAN 标准化活动 | 30 类标准驱动 decision tasks；从 113,475 scenarios 生成候选，自动筛选 + expert validation 后保留 3,722 题 | 与本项目最接近的通信/6G provenance 先例：标准定义任务空间，具体题目可以大规模生成，但 generator/filter/人工审计必须公开。Paper: https://arxiv.org/abs/2602.08675 |
| **DORA** | 45 个真实灾害事件 + 真实异构地理数据 | 515 个 expert-authored operational tasks + expert-verified replayable trajectories | 灾害 benchmark 不要求任务天然存在于日志；真实事件/data 提供 grounding，专家/benchmark designer 负责任务构造与验证。Paper: https://arxiv.org/abs/2605.11633 |

因此本项目允许使用 synthetic / simulation case，但**不允许**把“synthetic”当作免审计许可。有效性取决于 source ownership、environment fidelity、generation independence、evaluator isolation、coverage 与 held-out discipline，而不是取决于每个 episode 是否来自现场原始日志。

---

## 2. Discovery simulator 与 final evaluation benchmark 必须分离

当前研究明确区分两种用途：

### 2.1 Discovery simulator

用于回答：

- 哪些真实 operational primitives 的组合会产生 decision failure；
- failure 来自 evidence、resource、timing、recovery 还是 execution feedback；
- 哪些旧假设造成 benchmark collapse；
- 哪些 intervention 会消除困难。

Discovery 阶段允许提出新的**研究假设**并修改环境，但每次修改必须留下 provenance 和 falsification 记录。当前 v0.1 degeneracy、v0.2 41-signature hard surface、receipt v0.5 等都属于 discovery lineage。

### 2.2 Final evaluation benchmark

正式 benchmark 必须在方法冻结前由本文档和后续 frozen specification 完整定义：

```text
source/task contract
→ environment state/action/observation/transition contract
→ predeclared generation axes and ranges
→ full candidate universe generation
→ independent validity/oracle/baseline audits
→ preregistered structural split / hidden holdout
→ method evaluation
```

**禁止**：观察某个 baseline 或 proposed method 的成绩以后，再调整 ACK delay、query delay、outage pattern、resource budget、window timing 或 task composition，使其“刚好失败/成功”，然后把该调整后的集合当 final benchmark。

---

## 3. Variable ownership：四类 provenance，不允许混淆

### 3.1 Source-owned

现实 source 拥有：

- operational family 与 protected subject；
- obligation completion predicate；
- source-resolved reporting cadence / deadline；
- authority chain；
- 合法 capability 的存在性与 owner；
- cache / retransmission / recovery 等业务语义；
- 已有工程路径的 priority / fallback 约束（仅当 source 明确给出）。

这些字段**不能**因为 benchmark hardness 修改。

### 3.2 Empirical / model-derived

测量或声明物理模型拥有：

- satellite geometry / visibility opportunity；
- terrain / propagation-derived feasibility；
- 未来若获得的 field connectivity trace；
- 其他有明确生成模型的外生过程。

每个 model-derived 变量必须绑定 model/trace version；不能伪称 field measurement。

### 3.3 Controlled stress

Benchmark designer 可以预先声明、系统覆盖：

- obligation overlap / release phase；
- outage/recovery topology；
- resource headroom；
- evidence response delay / feedback delay；
- service-window interleaving；
- bounded uncertainty support。

但必须满足：

1. 维度来自真实问题结构，而不是从 proposed method failure 倒推；
2. 范围在生成前冻结并解释；
3. 全量 grid / sampling rule 可重现；
4. 结果中明确标注 `CONTROLLED_STRESS`，不报告成 empirical frequency；
5. easy / physical-invalid / information-infeasible / shortcut-solved cells 不因“不好看”被删除。

### 3.4 Unresolved

没有来源、没有物理模型、也没有合理 predeclared stress rationale 的 answer-relevant 变量保持 `UNRESOLVED`，不得采样进入正式 benchmark。

---

## 4. Environment contract：下一版 generator 之前必须先冻结的对象

T1 环境至少显式拥有以下状态：

\[
x_t=(O_t,C_t,R_t,E_t,F_t,K_t),
\]

其中：

- `O_t`：已发布/未完成 operational obligations、release/deadline/completion；
- `C_t`：当前 terrestrial/backhaul/fallback service state 与恢复阶段；
- `R_t`：剩余通信机会、shared fallback capacity、可审计 energy/airtime/bytes ledger；
- `E_t`：当前合法 evidence 及 freshness/provenance；
- `F_t`：in-flight send/query/receipt/ACK execution；
- `K_t`：cache / store-and-forward / recovery-owned state。

Agent 只能看到 lawful history projection：

\[
z_t=H(x_{\le t},a_{<t}),
\]

不能读取 evaluator-side hidden state。

### 4.1 合法动作

最小动作集合：

- `SEND_TERR(o, path)`；
- `SEND_FALLBACK(o, path)` / `SEND_SAT(o)`；
- `ISSUE_QUERY(capability)`；
- `WAIT`；
- source/simulator 已合法定义的 retry/reconcile action。

### 4.2 Transition ownership

每个动作必须同时声明：

- 物理/业务 effect；
- 消耗的 time/opportunity/resource；
- execution failure / timeout；
- 产生或触发的 observation；
- 对后续 obligation feasibility 的影响。

下一版环境**不得**再用“query 只是一个抽象计数”“ACK 免费瞬时到达”“send 不改变未来资源”等 shortcut，除非该设置明确属于 control arm。

### 4.3 Natural feedback first

Dedicated query 不是默认信息源。以下自然反馈必须保留给所有公平 baseline：

- normal send-as-probe；
- gateway receipt；
- final ACK / timeout；
- passive telemetry；
- local execution result；
- cache/recovery observable state（若 capability 合法）。

只有在保留这些路径后，paid acquisition 仍提高可实现 task value，才能标正 `EvidenceNeed`。

---

## 5. Generator contract：coverage-first，不做 hardness targeting

正式 generator 只能消费已经冻结的：

```text
source profile
× model/trace-derived environment
× predeclared controlled-stress axes
```

Generator 不拥有 gold，不读取 proposed method 结果，也不根据 baseline 结果修改参数。

生成后再独立执行：

```text
physical validity
→ observation-matched exact oracle
→ information feasibility
→ shortcut/open-loop audit
→ ordinary baseline ladder
→ intervention attribution
→ structural dedupe
→ split / holdout
```

Hardness 是**测量结果**，不是 generator 的优化目标。

### 5.1 Case count discipline

论文必须同时报告：

- candidate recipes；
- executable episodes / bundles；
- structural signatures；
- hard structural signatures；
- control / diagnostic cases；
- held-out hard structures。

不得用“大量 easy/control recipes”替代 hard-structure coverage，也不得把 174 recipes 写成 174 个独立 hard structures。

---

## 6. “强”不是文案：Strong-claim admission gates

此前 README 中“强×7”使用过早。自本合同起，`Strong` 只在下面条件全部满足时允许进入 paper-facing claim；否则写 `OPEN`、`PARTIAL` 或 `SUPPORTED-SCOPED`。

| Claim 维度 | 允许写 `Strong` 之前必须存在的证据 |
|---|---|
| **Continuous interaction** | hard cases 的成功策略必须跨多个 separated decision epochs；single-shot / blind open-loop / fixed action sequence 不能饱和；该现象至少跨两个独立 process/mechanism family，而不是同一 signature 的参数复制。 |
| **Active information acquisition** | 保留 passive telemetry、ACK、normal send-as-probe 后，no-paid-query task value 仍严格更低；always-query/fixed-query schedule 不能饱和；至少有 reached histories 的 acquisition decision 随 execution/evidence history 改变。 |
| **Physical communication resources** | query/send/wait/fallback 进入同一可审计 physical opportunity/resource ledger；移除 shared conflict 的 intervention 必须显著消除对应 hardness；normalized capacity 与真实 bytes/airtime/energy 不得混报。 |
| **Action changes future state** | exact first-irreversible-loss / preserving-alternative counterfactual 可复现；至少两类不同 communication actions 能改变后续 completion frontier；transition mutation tests 能捕捉错误实现。 |
| **Long outage / recovery** | 至少两个 source-compatible recovery/interruption topology 形成非等价 decision structures；recovery/cache/reconnect intervention 对任务难度有可解释因果效应；仅在 split 中出现不同字符串不算 strong。 |
| **External requirement traceability** | 所有 answer-relevant source-owned 字段 provenance 闭合；Q11 真实 human/source review 完成；source correction 可触发全链再生成并留下 lineage。 |
| **Computable optimal policy** | observation-matched non-anticipative exact oracle；与 brute-force/独立 reference 在小实例一致；evaluator mutation tests、information-infeasible 判定、retry/duplicate legality 全通过。 |
| **Structural generalization** | 方法冻结前 preregister 新的 structural holdout；test identity 未被方法开发访问；按 conflict topology / process topology / obligation composition / evidence topology 报告，而不是随机 seed split。 |

任何 “Strong” 都必须在 `results/CLAIMS.md` 有独立 claim entry、脚本、机器结果和 scoped boundary。

---

## 7. Paper-facing benchmark claim：先写验收版，不先写结论版

### 7.1 当前允许写的安全版本

> We build a source-grounded discovery simulator for pre-disaster mountain monitoring under intermittent connectivity. Operational obligations and legal communication capabilities are derived from geohazard standards and field/procurement materials, while satellite opportunities are projected from a declared geometry trace and benchmark-authored stress variables are explicitly separated from empirical claims. A non-anticipative exact oracle and ordinary-baseline ladder expose a reproducible hard mechanism family in which locally reasonable communication commitments can eliminate successful future continuations. The current prototype is used for mechanism discovery; benchmark-wide hard-mechanism coverage and pristine structural generalization remain open.

这段可以描述当前状态，但**不能**写成最终 benchmark contribution。

### 7.2 目标论文 claim 模板（只有全部 gate 通过后才能去掉方括号）

> We introduce **[BENCHMARK NAME]**, a source-grounded simulation benchmark for operational communication under intermittent connectivity. Real geohazard-monitoring standards and field deployments define the obligation, authority, capability, cache/recovery, and completion semantics; public/model-derived traces provide physical opportunity structure; and all benchmark-authored stress axes are preregistered independently of evaluated methods. The benchmark contains **[N executable cases / M structurally distinct signatures]** spanning **[K independently validated mechanism families]**, with a non-anticipative exact oracle, explicit physical/information-infeasible controls, and a pristine structural holdout. Across **[baseline ladder]**, failure analysis identifies **[mechanism statement]** as a recurring cause of missed operational obligations; targeted interventions remove the corresponding difficulty without changing task semantics. This benchmark therefore evaluates whether a communication policy preserves future operational feasibility, rather than merely whether it predicts or transmits task-relevant information.

### 7.3 方括号替换条件

- `[N/M]`：只能来自 frozen release manifest；
- `[K]`：必须是独立 mechanism family，不按 recipe 参数计数；
- `[baseline ladder]`：必须含 fixed/open-loop、passive/send-as-probe、always/fixed query、VoI、depth-k belief、receding-horizon、generic exact；
- `[mechanism statement]`：必须由 failure atlas + intervention + unseen-structure replication 共同支持；
- `pristine structural holdout`：test identity 在 method freeze 前生成并封存。

---

## 8. 当前 blocker

1. `HARD_MECHANISM_COVERAGE_REOPENED`：41 个 v0.2 hard signatures 全部坍缩到单一 H2×H3×H4 family；
2. `ENVIRONMENT_CONTRACT_NOT_YET_FROZEN`：本文是 v0.1 contract，仍需把 source-owned / controlled-stress ranges 与 substrate implementation 逐项映射；
3. `GENERATOR_REBUILD_PENDING`：下一版 generator 必须从本文出发重新构建，不继承刚才探索过程中按 baseline 结果调出的参数；
4. `PRISTINE_STRUCTURAL_GENERALIZATION_OPEN`：旧 7-signature test 已暴露；
5. `Q11_HUMAN_SOURCE_REVIEW_PENDING`：machine preaudit 不能代签。

Layer 3 在上述 benchmark blocker 关闭前保持暂停。

