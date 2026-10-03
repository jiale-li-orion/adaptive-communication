# 系统模型：Evidence-Grounded Closed-Loop Agentic Communication

更新：2026-10-02。状态：**当前公开系统模型 authority / v1**。本文件由作者本地 `docs/s6-model/system-model.md` 的 2026-10-01 authority draft 提升到远端 `research/`，使 reviewer clone 不依赖 ignored `docs/`。数值参数以 `spec/instance-v1-manifest.md` 与代码为最终真值；Task/Runtime/Metric 语义以 `research/EXPERIMENT-DESIGN-v1.md` 为准；claim 状态只认 `results/CLAIMS.md`。

## 1. 场景与建模边界

研究对象是灾前山区地灾监测通信系统。低功耗节点由电池/光伏供电，经 LoRaWAN Class A 类链路接入现场 gateway；gateway 经蜂窝等主回传连接中心，并可使用既有 gateway backup、terminal-DtS、access assist 等能力。风险等级、监测范围和监测频率由外部 authority 给出；Agent 负责通信执行，不负责预测“是否会发生滑坡”。

当前冻结主实例：

- `gw0` + 13 个坡面位移节点，共 14 个设备；
- `TICK_S = 60 s`；
- 任务 12 h + 1 h tail；
- normal monitoring 3600 s；
- 主实例 node cache `K_i = 240` records；
- `sample_wh = 4.7e-4 Wh`；
- Class A：一次合法 uplink 至多承载一次 downlink opportunity；
- propagation：SRTM1 + ITM；
- solar/temperature：NASA POWER source-derived windows；
- temporal LoRa variation：ChirpBox-derived process。

本文把物理系统分成四层：

```text
optional hazard/task generator
        ↓
Operational Task
        ↓
Communication Physical/Data Plane
        ↓
Evidence World
        ↓
Agent Runtime / Capability / Policy
        ↓
Communication Physical Effect
```

主论文的 communication claims 只依赖后四层中的 `Operational Task -> communication outcome`。Hazard physics 只用于 secondary task generation/transfer，不作为通信结果成立的必要前提。

---

## 2. Optional hazard → Operational Task layer

灾前监测任务可以继续使用来源约束的人工/标准 task schedule。为了避免所有 benchmark task 都是手写 schedule，secondary experiment 可以增加 physics-grounded task generator：

\[
R(t),\;DEM,\;Soil
\rightarrow
Hydrology
\rightarrow
Slope\ Stability / Deformation
\rightarrow
External\ Authority
\rightarrow
\tau_t.
\]

### 2.1 降雨入渗 / 孔压

可采用 USGS TRIGRS 作为外部 generator（来源 `research/sources.json::S10`）。TRIGRS 的职责是把时变降雨输入转换为 transient pore-pressure / factor-of-safety 场；本文**不重新实现或重新声称其水文 PDE**。为了说明系统依赖关系，可以把这一层抽象写成：

\[
\psi_i(\cdot,t)
=
\mathcal H_{TRIGRS}
\left(R_i(\le t),DEM_i,\theta_i^{soil}\right),
\]

其中 \(\psi\) 为 pressure head，\(R_i(t)\) 为 rainfall forcing。若需要真实降雨 forcing，可选 NASA GPM IMERG（`S11`）；它只作为外生降雨产品，不当作坡面雨量真值。孔隙水压力：

\[
u_i(z,t)=\rho_w g\psi_i(z,t).
\]

### 2.2 Infinite-slope stability

对于浅层降雨诱发边坡，可用：

\[
FS_i(t)=
\frac{
c_i'
+\left[\gamma_i z_i\cos^2\beta_i-u_i(t)\right]\tan\phi_i'
}{
\gamma_i z_i\sin\beta_i\cos\beta_i
}.
\]

参数含有效黏聚力 \(c'_i\)、内摩擦角 \(\phi'_i\)、潜在滑面深度 \(z_i\)、坡角 \(\beta_i\) 与单位重 \(\gamma_i\)。

TRIGRS 本身使用 cell-wise infinite-slope stability 计算 factor of safety（`S10`）。上式只写出本文需要的经典变量关系，不替代 TRIGRS 的官方理论/实现。

**边界**：当前没有目标坡面的 geotechnical calibration，因此本文不把某个 \(FS\) 数值直接宣布为 yellow/red threshold。若使用该层，只把它作为 `hazard state -> external authority -> Operational Task` 的可审计 generator，并对 soil/risk threshold 做 sensitivity / source-based parameter set。

### 2.3 位移前兆 stress test

当前主 benchmark 继续使用仓库已有的 displacement workload / simulator signal。若未来引入失稳前加速位移模型，必须先把对应 field model、参数范围与适用阶段登记到 `research/sources.json`，再进入 episode generator；当前不把未经登记的 phenomenological failure-time model 写进默认系统方程。

### 2.4 Debris-flow/runout

灾前主实验**不需要**完整两相 debris-flow CFD。若未来研究灾害启动后 topology destruction，可用 USGS Grfin（`S12`）这类低参数 empirical runout/inundation 工具生成 damage mask：

\[
HazardSource+DEM
\rightarrow
RunoutMask
\rightarrow
Node/GatewayDamageState.
\]

只有拥有充分地质参数和明确灾后研究问题时，才考虑 USGS D-Claw（`S13`）级 depth-averaged two-phase mass/momentum 模型。D-Claw 在当前设计里被明确排除出默认 pre-disaster benchmark，避免用未校准的两相流参数制造“高保真”假象。

---

## 3. Operational Task

Operational Task \(\tau\) 是 benchmark/业务层对象：

\[
\tau=(\mathcal N_\tau,\mathcal M_\tau,\mathcal P_\tau,\mathcal W_\tau,
\mathcal D_\tau,\mathcal A_\tau,\mathcal S_\tau),
\]

分别表示目标节点、测项、monitoring profile、时窗、deadline、授权 effect/action set 与 scoring/source profile。

当前 task families：Monitoring Continuity、Risk Escalation、Backhaul-Outage Sustainment、Energy-Constrained Monitoring、Recovery & Reconciliation、Compound Long-Horizon Operation。

Agent 不改变 \(\tau\) 的业务 denominator。比如提高采样频率不能把没完成的 obligation 从评价集合删除。

---

## 4. Monitoring obligation model

一条监测义务定义为：

\[
o=(i,m,r_o,[s_o,e_o],d_o),
\]

其中 \(i\) 是 node，\(m\) 是 measurand，\(r_o\) 是 release，\([s_o,e_o]\) 是合法采样窗口，\(d_o\) 是中心交付截止。

若存在合法 sample \(s\)：

\[
t_s\in[s_o,e_o],
\]

则定义 collection indicator：

\[
I_o^{col}=1.
\]

若该 sample 最终到达 center 且：

\[
t_s^{center}\le d_o,
\]

则：

\[
I_o^{succ}=1.
\]

主业务指标 Timely Obligation Delivery Rate：

\[
TDR(\pi)=\frac{\sum_{o\in\mathcal O}I_o^{succ}}{|\mathcal O|}.
\]

另外分列：collection rate、missing collection、missing delivery、censored、delivery latency、AoI/observation gap。物理上完全不存在合法服务机会的 obligation 可以单独报告 feasible-denominator 版本，但不能偷偷改原分母。

---

## 5. Node state, energy and sampling

节点 \(i\) 的核心状态：

\[
x_{i,t}=(B_{i,t},Q_{i,t},C_{i,t},A_{i,t},L_{i,t},\ldots),
\]

其中 \(B\) 为 battery，\(Q\) 为 source cache，\(C\) 为 installed communication/sampling config，\(A\) 为 liveness/application state，\(L\) 为 link/local execution state。

### 5.1 Battery dynamics

\[
B_{i,t+1}
=
\min\left\{
B_i^{max},
\left[
B_{i,t}+H_{i,t}
-E^{sense}_{i,t}
-E^{UL}_{i,t}
-E^{DL}_{i,t}
-E^{DtS}_{i,t}
-E^{other}_{i,t}
\right]^+
\right\}.
\]

当前实例 `sample_wh=4.7e-4 Wh`；radio energy 按实际 airtime / RX opportunity 计；terminal-DtS 单独计能量。

### 5.2 Source-derived harvest

NASA POWER 给出逐小时辐照 \(G(t)\) 和温度。当前实现不声称拥有真实面板面积/效率标定，而采用 source-shape + A-layer scale：

\[
H_{i,t}=\lambda_i\frac{G(t)}{G_{max}}\Delta t,
\]

其中 \(\lambda_i\) 即 `harvest_peak_wh_per_hour`，是可扫描参数。低温 charging gate 与 capacity derating 继续按 manifest/code 执行。

`run_joint` 暴露 `irradiance_year` 与 `irradiance_start_hour`，因此 benchmark 可以按真实天气窗口 split。

### 5.3 Cache dynamics

设 \(S_{i,t}\) 是新产生的 samples，\(ACK_{i,t}\) 是已确认可释放 records，\(EXP_{i,t}\) 是按既有 expiry semantics 到期 records：

\[
Q_{i,t+1}
=
Cap_{K_i}\left[
(Q_{i,t}\setminus ACK_{i,t}\setminus EXP_{i,t})\cup S_{i,t}
\right].
\]

其中 \(K_i=240\)。overflow 按现实现有规则处理。未确认记录继续占用缓存/重传批次，这一物理后果由原 simulator 保留。

---

## 6. Wireless access / Class A opportunities

LoRa access 由地形/ITM 的可达性与时间相关链路过程共同决定。设一次 uplink 成功被 gateway 听到：

\[
U_{i,t}=1.
\]

Class A 设备随后打开两个 receive windows：

\[
U_{i,t}=1
\Rightarrow
W^{RX1}_{i,t+\Delta_1}=1,
\qquad
W^{RX2}_{i,t+\Delta_2}=1.
\]

当前 simulator 将其离散成“一次 uplink 至多一次 downlink”资源约束；downlink energy 与 airtime 单独计数。

一个 center-originated control action 能被 node 接收至少要求：

\[
W^{RX}_{i,t}=1
\land
P^{c\rightarrow g}_{t}=1
\land
A^{g\rightarrow i}_{t}=1,
\]

其中 \(P^{c\rightarrow g}\) 表示 center→gateway control path 可用，\(A^{g\rightarrow i}\) 表示 gateway→node access opportunity/链路可达。

因此“中心决策正确”与“配置实际安装”是两个不同事件。

---

## 7. Gateway, primary backhaul, backup and DtS

设 gateway queue 为 \(G_t\)。primary backhaul state：

\[
P_t\in\{0,1\}.
\]

当 \(P_t=0\) 时，gateway 继续 store-and-forward；恢复后可补发历史 records。Gateway backup 和 terminal-DtS 是独立 capability，不与 primary 合并成一个布尔变量。

Backup execution 产生：

\[
(N_t^{bk},Bytes_t^{bk}),
\]

DtS execution 产生：

\[
(N_t^{dts},N_t^{succ},E_t^{dts}).
\]

这些量直接来自 `JointControlPlane` / `Instance` counters，而不是由 Agent 自报。

---

## 8. Command execution lifecycle

一个 device-changing capability 不能简化为 `tool(args)->success`。定义生命周期：

\[
REQUESTED
\rightarrow ACCEPTED/REFUSED
\rightarrow DELIVERED
\rightarrow APPLIED
\rightarrow CONFIRMED.
\]

其中：

- `accepted`：control plane 接收了 submission；
- `delivered`：downlink 到达 node；
- `applied`：node 的当前 config/state 已改变；
- `confirmed`：后续合法 node report 将该 effect 带回 center。

因此：

\[
NO\_CONFIRMATION\not\Rightarrow NOT\_APPLIED.
\]

当前 Agentic Runtime 的 `note_command_sent` 只登记 `accepted_unconfirmed`；之后 report 与 target/generation 对齐才登记 `applied_confirmed`。

---

## 9. Physical state transition

全系统状态可写为：

\[
x_t=(B_t,Q_t,C_t,L_t,G_t,R_t,M_t,\ldots).
\]

外生输入：

\[
\xi_t=(H_t,\Theta_t,\Gamma_t,O_t,\Omega_t),
\]

分别表示 harvest、temperature、wireless stochastic process、access/backhaul outage 与 Operational Task revision 等。

给定合法 physical action \(a_t\)：

\[
x_{t+1}=F(x_t,a_t,\xi_t;\phi),
\]

其中 \(\phi\) 是 frozen deployment/device/protocol parameters。函数 \(F\) 的具体分量由 §§5–8 和既有 simulator 实现定义；Agent 不修改它。

---

## 10. Observation and Evidence World

Agent 不观察 \(x_t\)。在 owner/location \(\ell\) 上，合法 observation：

\[
z_t=H(x_{\le t},a_{<t},\xi_{\le t},\ell).
\]

Evidence adapter 形成 typed evidence：

\[
e_j=
(p_j,v_j,s_j,o_j,t_j^{gen},t_j^{obs},\rho_j,\nu_j,\sigma_j),
\]

其中：

- \(p_j,v_j\)：proposition/value；
- \(s_j\)：source/provenance；
- \(o_j\)：owner location；
- \(t^{gen},t^{obs}\)：生成/获得时间；
- \(\rho_j\)：world/evidence revision；
- \(\nu_j\)：freshness/validity semantics；
- \(\sigma_j\)：status semantics。

status 至少区分：

\[
\sigma_j\in
\{CURRENT,STALE,NONE\_RECENT,UNREACHABLE,TIMEOUT,NEGATIVE\}.
\]

Evidence World：

\[
\mathcal E_t=\{e_j:t_j^{obs}\le t,\ e_j\text{ accepted by runtime gate}\}.
\]

Evidence revision 只在事实内容改变时推进；age/AoI 是 materialization/freshness-check 时相对当前 \(t\) 计算的派生量。

---

## 11. Capability model

统一 capability set：

\[
\mathcal K=\mathcal K^E\cup\mathcal K^A,
\]

其中 \(\mathcal K^E\) 是 evidence-use capability，\(\mathcal K^A\) 是 communication-device capability。

每个 capability：

\[
k=(I_k,O_k,Owner_k,Path_k,L_k,Bytes_k,E_k,Authority_k,Failure_k,Effect_k).
\]

Evidence capability execution：

\[
q_t(k)
\rightarrow
(status,result,provenance,cost).
\]

Device capability execution：

\[
a_t(k)
\rightarrow
(lifecycle,status,effect,cost,x_{t+1}).
\]

`cost` 可以包含：

\[
c_k=(latency,bytes,airtime,energy,opportunity).
\]

当 evidence tool 只是 center-local Evidence World retrieval 时，network bytes/airtime/energy 可为 0；当它需要通过受损通信路径取得 observation 时，其 cost 与 reachability 使用同一物理系统计账。

---

## 12. Agent Runtime

Task compiler：

\[
T_j=\Gamma(\tau, S_t^{legal}, revision),
\]

其中只允许读取 runtime 已合法持有的 state/evidence refs，不读取 simulator truth。

ContextManifest：

\[
C_t=M(T_j,S_t,\mathcal E_t,K_t).
\]

进入 planner/model 前：

\[
P_t=Materialize(C_t).
\]

Planner 输出：

\[
(q_t,a_t,\Delta S_t,stop_t)=\pi(T_j,P_t,K_t).
\]

第一版 deterministic `comply` consumer 只用于验证 runtime 不改变 physical behavior；LLM / learned / oracle planner 后续使用完全相同的 Task/Evidence/Context/Capability contract。

---

## 13. Objective and metrics

本文不预设无来源依据的单一加权目标：

\[
TDR-\lambda_1E-\lambda_2Bytes-\lambda_3Latency.
\]

除非 Operational Task/source 明确给出这些权重，否则不这样做。

主报告使用向量：

\[
J(\pi)=
(TDR,Collection,Latency,Energy,Bytes,Airtime,Survival,Recovery,\ldots).
\]

并做 paired comparison / Pareto analysis。

Agent diagnostics 另报：Task grounding、EvidenceNeed、capability selection/arguments、status confusion、Context sufficiency/redundancy、stop correctness、policy regret、model/tool calls、tokens、materialized bytes 与 action confirmation rate。

最终 physical/business outcome 是 primary；trajectory metric 用于 failure attribution。

---

## 14. Benchmark episode

一个 episode：

\[
\mathcal B=(\tau,W_0,X,C_0,K,\Pi^*,Y^*,R),
\]

其中：

- \(\tau\)：Operational Task；
- \(W_0\)：evaluator-only initial world；
- \(X\)：frozen exogenous trace / seed / NASA POWER window；
- \(C_0\)：initial ContextManifest；
- \(K\)：Capability catalog revision；
- \(\Pi^*\)：reference/oracle trajectory or acceptable set；
- \(Y^*\)：reference physical outcome；
- \(R\)：source/version/replay coordinate。

Agent 只能看到授权 Task、Runtime TaskContract、materialized Context 和 visible capabilities；未来 \(X\) 与 evaluator-only \(W\) 不可见。

---

## 15. Current implementation mapping

| 数学对象 | 实现 owner |
|---|---|
| \(\tau\) Operational Task | `code/agentic_communication/contracts.py` |
| \(T_j\) Runtime TaskContract | `code/agentic_communication/runtime_contracts.py` + `task_compiler.py` |
| \(\mathcal E_t\) Evidence World | `evidence_world.py` |
| \(C_t,P_t\) Context / materialization | `context_runtime.py` |
| \(K\) Capability | `capabilities.py` + domain registry |
| \(\pi\) planner/runtime policy | `policy.py` |
| Runtime Trace | `trace.py` |
| communication metric | `metrics.py` + existing `scoring.py` |
| physical transition \(F\) | existing `Instance / JointControlPlane / run_joint` |

当前 O2 Risk Escalation 的 5-seed R3 run 已验证：新增 runtime/trace 层不改变原 `mission-comply` 的 physical signature。
