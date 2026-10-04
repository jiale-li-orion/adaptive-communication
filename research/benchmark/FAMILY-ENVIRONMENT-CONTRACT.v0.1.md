# Family Environment Contract v0.1

状态：Layer 1 environment/mapping authority / pre-oracle  
日期：2026-10-04

本文件规定 T1/T2 怎样映射到 executable environment，以及哪些历史 substrate 可以复用、哪些必须由 source-aware Layer-1 adapter 替代。

## 1. Shared rule

Layer 1 不要求“重写整个 simulator”，也不允许“为了复用旧 simulator 而改 task”。

复用标准只有一个：

> 历史组件的 state/action/transition/evaluator 语义必须与 source-profile contract 等价；只要它会引入 source 未定义的 deadline、authority、reward、future information 或 completion predicate，就不能直接复用。

## 2. Reusable substrate

当前可以直接复用或薄适配复用：

- deterministic event loop / replay seeds；
- node/gateway/center execution locations；
- command delivery / acknowledgement / execution ledger；
- local storage / gateway queue；
- battery accounting and source/empirical harvest traces；
- terrestrial primary / backup path availability abstraction；
- terminal/gateway fallback mechanisms；
- typed evidence ownership / freshness infrastructure；
- physical transmission counters and byte accounting；
- execution-state persistence and replay。

这些组件只提供机制，不拥有 Task Family 语义。

## 3. Components that must not be reused unchanged

### 3.1 Historical routine obligation deadline

旧 routine obligation 默认窗口等于 period，同时 grace 也等于 period，因此 deadline 实际落在两个 period 之后。源码已经明确说明 grace 是研究容忍时延，不是 SLA。

Layer 1 source-profile case 禁止默认继承该 grace。

对于 source 明确给 reporting cadence P 的 profile，source-aware obligation contract 默认要求每个 source interval 内完成一份 required report，completion deadline 就是该 interval 的结束。若某 source 明确给额外送达宽限，再由该 profile 单独加入。

### 3.2 Historical sensing process

T1 是 communication benchmark。source 只定义 reporting/delivery obligation 时，不得为了兼容旧 Node sampling model，把 reporting cadence 偷换成 sampling cadence。

Layer-1 boundary：

    upstream monitoring subsystem
    -> report payload becomes available
    -> communication benchmark begins

只有 source 同时定义 sampling semantics 时，sampling 才进入 T1 environment state/action。

这允许复用通信 plane，同时避免“采不到数据”成为一个并非通信能力造成的 benchmark failure。

### 3.3 Historical weighted / research-only scorer semantics

继续保留：
- obligation completion；
- raw latency；
- energy；
- bytes / attempts；
- survival / availability where source-relevant。

禁止：
- arbitrary scalar reward；
- research tolerance 被称作 source SLA；
- old aggregate metric 替代 source completion predicate。

## 4. T1 — Monitoring Information Continuity

### 4.1 Protected subject

source-required monitoring information availability。

### 4.2 Environment boundary

Input from upstream：
- report payload release；
- operational / warning state；
- source profile；
- device/path state visible under profile authority。

Communication environment owns：
- local queue/storage；
- path opportunity；
- energy cost；
- transmission/fallback；
- acknowledgement / upper-platform delivery；
- evidence staleness；
- reconnect and resynchronization where source-defined。

### 4.3 DB44 reporting profile

Source semantics：
- monitoring grade × warning state chooses a reporting-cadence range；
- generator resolves a concrete deployment profile only through declared SOURCE_RANGE sampler；
- every interval defines one reporting obligation；
- completion = timely complete report before interval deadline；
- transport classes are allowed context, not answer-relevant dimensions by themselves。

Mapping：
- report_interval_s -> Layer-1 obligation recurrence and deadline；
- warning state / grade -> profile selection；
- communication plane -> historical shared substrate；
- old routine grace -> not reused；
- old sample interval -> not used as task semantics。

### 4.4 Jiaozuo deployment profile

Source semantics：
- acquisition at least hourly；
- monitoring data must reach required local/national platforms；
- NB -> 4G/5G -> BeiDou priority is source-defined；
- center can read device work/storage state and block-read history。

Current limitation：
- available source does not provide a numeric upper-platform delivery deadline equivalent to the 1h acquisition cadence。

Therefore：
- profile remains useful for communication priority / state visibility / delivery-target conformance；
- it cannot by itself generate a timed decision-hard communication case by treating 1h acquisition as 1h delivery；
- if a downstream delivery timing source is not found, V5/V6 hardness may fail and the profile remains conformance/supporting coverage。

## 5. T2 — Warning Delivery & Response Handoff

T2 cannot be represented by the old sensor-node simulator alone。

Required environment objects：
- warning candidate；
- verification state；
- publication authority；
- actor / recipient graph；
- communication channel availability；
- delivery attempts；
- acknowledgement；
- retry / alternate-contact state；
- stage deadline；
- response handoff。

Reusable substrate：
- typed actor ownership；
- attempt/ack ledger pattern；
- channel/fallback abstraction；
- replay/failure accounting。

New Layer-1 environment required：
- actor-chain state machine；
- multi-recipient delivery；
- authority-gated transitions；
- source-specific deadline propagation；
- completion predicate extending beyond packet arrival。

T2 remains a boundary split; it must not replace T1 as the main mountain-monitoring benchmark。

## 6. Simulator mapping dispositions

Every source-resolved case must receive one mapping disposition before V1：

- DIRECT_REUSE — semantics match existing substrate exactly；
- ADAPTER_REQUIRED — shared physics/runtime can be reused but task/evaluator adapter is required；
- SIMULATOR_GAP — required source-backed state/action/actor/transition does not exist；
- SUPPORT_ONLY — source profile is useful for capability/coverage but cannot independently define a decision case。

Current expected status：
- DB44 T1 -> ADAPTER_REQUIRED；
- Jiaozuo T1 -> SUPPORT_ONLY for timed hardness unless delivery semantics are added；
- Yining T2 -> SIMULATOR_GAP；
- Baoshan T2 -> SIMULATOR_GAP。

No case may enter V1 oracle solving before its mapping disposition and environment contract are explicit。
