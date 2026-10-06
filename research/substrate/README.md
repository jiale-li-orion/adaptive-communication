# Shared Communication Substrate

本目录持有三层研究共同使用的 communication/world model、physical execution semantics 与 mathematical system model。Benchmark、compiler、policy 可以改变各自 owner 的对象；substrate 负责保持同一物理世界与同一 scorer。

当前 authority：

- 数学系统模型：[`SYSTEM-MODEL-v1.md`](SYSTEM-MODEL-v1.md)
- 冻结 numeric deployment point：[`../../spec/substrate/instance-v1-manifest.md`](../../spec/substrate/instance-v1-manifest.md)
- 数据/部署规范：[`../../spec/substrate/`](../../spec/substrate/)
- 物理实现：`../../code/substrate/`
- 当前 machine evidence：`../../results/communication-substrate/`

## 1. Ownership

Substrate 持有：

```text
terrain / propagation
sampling / reporting
battery / harvest
finite source cache
LoRa/Class-A opportunity
center ↔ gateway ↔ node reachability
gateway store-and-forward
primary / backup / DtS / access-assist
command execution lifecycle
partial observation / evidence placement substrate
physical/business scorer
```

Layer 1 使用这些对象构造 task/world；Layer 2 使用它们推导 legality、evidence validity 与 future feasibility；Layer 3 在合法 surface 内选择动作。三层评测共用同一 physical transition 与 scorer。

## 2. Historical lineage

这个目录承接了仓库最早、最长的一段系统研究历史。

### 2.1 2026-09-13：instance-v1 physical closure

这一轮是旧轻量仿真到当前 communication substrate 的主要物理升级。关键 commit：

| Commit | 物理闭环增量 |
|---|---|
| `a68c01b` | 外生过程 + 三时刻 transfer semantics |
| `78a6372` | finite cache + action-driven battery + separated scorer |
| `5c6457d` | multi-node + SRTM/ITM terrain；communication opportunity 开始成为真实选择 |
| `0b53d01` | propagation records + tail observation + multi-node outcome |
| `4db804d` | outage/recovery 下 collection loss 与 delivery loss 分列 |
| `9cecba2` | center-originated control + acknowledgement + first closed-loop comparison |
| `0616ecb` | source-shaped harvest process + autonomy margin + oracle/action-space correction |
| `dcf1840` | NASA POWER source-derived irradiance + deployment provenance + consistency audit |
| `a827a82` | 16-item manifest closure + capability matrix + method-independent scoring audit |

这一轮建立了 E/A/M provenance：

- **E** — external/source evidence；
- **A** — declared research/deployment choice；
- **M** — model / implementation output。

后续所有系统参数都沿用这套边界。`spec/substrate/instance-v1-manifest.md` 是当前数值 authority。

### 2.2 2026-09-14–30：systems research becomes reusable substrate

后续系统研究围绕 expiry、fallback、control-path failure、execution placement、persistent communication state、backup/DtS 与 ordinary scheduling 展开。多个最初看起来可能成为 method novelty 的机制，在强 ordinary baseline / counterexample 下被证明更适合作为 runtime substrate、baseline 或 negative boundary。

这一阶段留下的价值是一个更成熟的 physical/data plane：方法不能通过修改 expiry、fallback、scheduler、backup chooser、DtS semantics、hidden-state exposure 或 scorer 来制造收益。

### 2.3 2026-10-01–03：system-model rewrite for Agentic Communication

旧 `system-model.md` 当时仍有四类 stale：

- 121×121 大网格与当前 14-device frozen instance 不一致；
- Agent 抽象仍停留在旧 execution-uncertainty framing；
- GE / energy / deployment 参数与当前代码/manifest 有版本差；
- terminal-DtS、backup 与新的 Task/Evidence/Capability runtime 已超出旧文档表达。

因此系统模型从 `spec + code` 反向重建。2026-10-01 先按当前 full simulator 重写；随后补齐 communication-physical mathematics：monitoring obligation、battery、cache、Class-A opportunity、backhaul/fallback、capability cost、execution lifecycle、observation/evidence world 与 vector outcome。2026-10-03 公开提升为 `SYSTEM-MODEL-v1` authority；2026-10-04 仓库重组后归入当前 `research/substrate/` owner。

Optional hazard layer 也在这一轮明确：TRIGRS/infinite-slope、IMERG、Grfin 等只负责 `hazard -> external authority -> Operational Task` 的可选 task generation。Communication claim 从 Operational Task 开始，Agent 不承担地灾预测任务。

### 2.4 A7–A11 / cache04–05 阶段：研究地位重新分层

本地 control-plane cache04/05 与对应的 A7–A11 公开 machine evidence 记录了这一轮强对照，结论集中在几个稳定事实：

- persistent intent / async executor 属于普通 runtime substrate；
- candidate-plan deterministic expansion 属于 runtime substrate；
- ordinary backward slicing + current-state evaluation 可以覆盖当时大量 dependency construction；
- decision-closed O1–O6 里大量状态可由 compiled checklist 完成；
- query-positive mechanism 能闭合 `uncertainty → evidence → feasibility transition → commitment → physical effect`，但旧 task set 仍不足以形成完整 communication-policy benchmark。

于是 repo 被重新分层：

```text
Shared substrate
    physical truth / execution / scorer

Layer 1
    source-grounded task legitimacy + decision hardness

Layer 2
    deterministic decision semantics

Layer 3
    genuine remaining policy/search choice
```

这次分层保留了旧系统资产，也把 ordinary mechanism 从当前 method claim 中剥离。

## 3. Mathematical backbone

完整推导见 [`SYSTEM-MODEL-v1.md`](SYSTEM-MODEL-v1.md)。模块入口只保留关键对象。

### Monitoring obligations

\[
o=(i,m,r_o,[s_o,e_o],d_o)
\]

\[
TDR(\pi)=\frac{\sum_{o\in\mathcal O}I_o^{succ}}{|\mathcal O|}
\]

Evaluator 拥有 obligation denominator；policy 改 sampling/reporting 不能删除未完成业务义务。

### Battery / harvest

\[
B_{i,t+1}=\min\left\{B_i^{max},\left[B_{i,t}+H_{i,t}-E^{sense}_{i,t}-E^{UL}_{i,t}-E^{DL}_{i,t}-E^{DtS}_{i,t}-E^{other}_{i,t}\right]^+\right\}
\]

\[
H_{i,t}=\lambda_i\frac{G(t)}{G_{max}}\Delta t
\]

`G(t)` 可以来自 NASA POWER；`\lambda_i` 持有 deployment-scale choice。两者在 provenance 上分开。

### Cache

\[
Q_{i,t+1}=Cap_{K_i}\left[(Q_{i,t}\setminus ACK_{i,t}\setminus EXP_{i,t})\cup S_{i,t}\right]
\]

未确认 record 持续占用 cache / retransmission state；expiry、ACK 和 overflow 分别处理。

### Communication opportunities

\[
U_{i,t}=1\Rightarrow W^{RX1}_{i,t+\Delta_1}=1,\qquad W^{RX2}_{i,t+\Delta_2}=1
\]

Center-originated action 还需要 center→gateway path 与 gateway→node opportunity。Primary backhaul、gateway backup、terminal-DtS 分别持有 capability/state/cost。

### Execution lifecycle

```text
REQUESTED → ACCEPTED/REFUSED → DELIVERED → APPLIED → CONFIRMED
```

`accepted`、`delivered`、`applied`、`confirmed` 分别是独立状态。后续 Evidence World 与 Layer-2 semantics 直接依赖这一区分。

### World and observation

\[
x_{t+1}=F(x_t,a_t,\xi_t;\phi)
\]

\[
z_t=H(x_{\le t},a_{<t},\xi_{\le t},\ell)
\]

Agent 通过 owner/location-aware observation interface 看到合法投影；evaluator 保留完整 world truth。

### Capability

\[
\mathcal K=\mathcal K^E\cup\mathcal K^A
\]

\[
k=(I_k,O_k,Owner_k,Path_k,L_k,Bytes_k,E_k,Authority_k,Failure_k,Effect_k)
\]

Evidence acquisition 与 device actuation 都经过同一 physical system，因此 latency/opportunity/resource 可以共同 binding。

### Outcome

\[
J(\pi)=(TDR,Collection,Latency,Energy,Bytes,Airtime,Survival,Recovery,\ldots)
\]

Hard constraint / priority 由 Operational Task/source 持有；资源指标按 vector / paired / Pareto 方式报告。

## 4. Evidence and parameter boundary

| Object | Grounding | Scope |
|---|---|---|
| terrain | NASA SRTM1 | DEM / elevation |
| spatial propagation | ITM | point-to-point terrain-sensitive feasibility |
| temporal LoRa variation | ChirpBox-derived process | burstiness/stress distribution |
| Class-A opportunity | LoRaWAN Class-A semantics | selected access configuration |
| irradiance / temperature | NASA POWER | exogenous forcing windows |
| sampling / reporting / retransmission / remote config | field paper / standard / official procurement / device material | operational primitive and source-supported range |
| numeric operating point | `spec/substrate/instance-v1-manifest.md` | current frozen research instance |
| physical transition | `code/substrate/` | executable world dynamics |

Current system model explicitly separates:

```text
source-grounded structure / range
vs
research operating point
vs
field-calibrated deployment truth
```

Current claims cover the first two. Site-certified RF calibration、dense LoRa MAC contention/capture、specific China-compliant channel plan、panel/controller sizing、field geotechnical calibration 等对象需要独立 deployment evidence 后才能升级 claim。

## 5. Compatibility rule

任何新 benchmark / compiler / policy 实验都先回答：

1. physical transition 是否保持同一 authority；
2. hidden simulator state 是否仍经过合法 observation/evidence boundary；
3. action/capability 是否来自已声明 catalog；
4. physical scorer / obligation denominator 是否保持；
5. synthetic / source-derived / operating-point parameter 是否继续分层报告。

满足这五项以后，method gain 才能解释为 benchmark/compiler/policy gain。
