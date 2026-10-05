# V8 Strong-Baseline Contract v0.1

状态：**CURRENT / placement-aware**

V8 不使用“某个确定性算法能解”作为 benchmark 否决条件。exact observation-matched solver 本来就是 reference；generic memo / incremental AND–OR 主要用于 computation fairness。V8 真正检查的是：在相同 operational contract、相同 placement、相同合法信息边界下，普通短视策略是否已经饱和目标 decision surface。

## 1. 三类 baseline 分账

### A. Same-information shortcut

可以直接降低相应 hardness claim：

- blind/public-geometry EDF/reserve；
- passive-only；
- normal-send-as-probe；
- fixed / periodic / batch owner reads；
- shallow rule combiner；
- myopic conflict/latency/VoI；
- true finite-depth belief planner；
- receding-horizon planner。

若这些策略在结构留出集上饱和任务质量及主要成本前沿，对应 H2/H4/H5 或长程规划 claim 降级。简单 case 仍保留为 conformance / easy / boundary coverage。

### B. Deployment alternative

改变 planner placement 或免费暴露 owner-local state 的方法单独报告，例如 `gateway_local_edf_reserve`。它回答“是否需要中心远程 acquisition / center placement”，不能直接作为 same-information `SHORTCUT_SOLVED`。

gateway-local 100% 成功时允许的结论是：当前问题可能更适合 gateway autonomy，中心远程取证的系统必要性不能泛化。它不证明 evaluated placement 下的信息决策结构不存在。

### C. Computation reference

- generic exact AND–OR；
- generic memo / early stop；
- ordinary dependency tracking；
- cached flow / invalidation + rebuild；
- incremental exact search。

这些 reference 应与后续结构化方法比较 wall-clock、展开节点、flow 次数、失效范围与 context 大小。它们能取得 exact 任务质量是预期行为，不能作为 benchmark invalidity。

## 2. 当前第一层结果

216 个 `VALIDITY_PENDING` structural cells：

```text
same-information shortcut solved  100
first-layer survivors              116
gateway-local deployment success   216
```

15 个 stratified `PAID_EVIDENCE_REQUIRED` cells：

```text
same-information shortcut solved    0
first-layer survivors               15
gateway-local deployment success    15
```

因此下一步固定为 placement-preserving policy ladder。只有 shallow/depth-k/receding 等普通策略追平，才能继续收窄相应 decision-hardness claim；generic exact 的成功不参与该否决。

## 3. 之后的方法评价

若普通策略任务质量已经做满，仍可比较：

- 同任务质量下实际远程取证成本；
- 同任务质量、同信息条件下在线总计算时间；
- 同计算预算下距离 observation-matched exact 的任务质量；
- 动态事件后局部重算与全量 rebuild 的代价；
- gateway 与 center placement 的系统边界。

这些指标必须分别计账，不能把本地 read 数、无线请求数和 memo nodes 混成一个“cost”。
