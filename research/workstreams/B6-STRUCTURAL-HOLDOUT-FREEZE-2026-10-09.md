# B6 Structural Holdout Freeze — 2026-10-09

状态：**FROZEN BEFORE EXECUTION / method-independent topology holdout**。

目的：回答 reviewer 最直接的泛化质疑：当前 Future-Choice conflict frontier 的局部维护收益，是否只来自开发阶段反复使用的“等大小、完全 disconnected components”。

本 holdout **不扩大 K/C 数量**，而改变 obligation–opportunity graph motif。所有 motif、规模、event sequence、correctness authority 和 resource contract 在运行 solver 前冻结；执行后不得删除失败 motif 或修改 topology 使方法更好看。

机器可读 authority：[`B6-STRUCTURAL-HOLDOUT-FREEZE-2026-10-09.json`](B6-STRUCTURAL-HOLDOUT-FREEZE-2026-10-09.json)。

## Global contract

- placement：post-query revealed gateway branch；无额外 direct-observation event；
- hard obligations / terrestrial windows / satellite fallback 使用现有 Layer2 v2 semantics；
- correctness authority：incremental snapshot 每个 event 后必须与 fresh full structural rebuild canonical-equal；
- bounded exact control：fresh ordered exact / ordinary persistent exact / dependency-cache exact 的完整 action frontier必须一致；
- OOM / timeout = `UNRESOLVED_COMPUTATION`；
- `partition_fallback` **不是失败本身**。若 topology 变化违反 monotonic component-reuse assumption，保守 repartition/full rebuild是正确行为；
- work-unit comparison只写 component recompute/reuse 与 exact expansions，不写 wall-time superiority；
- 默认 2 CPU / nice+10 / single-thread numerical libraries / ≤512 MiB target。

## H1 — ASYMMETRIC_DISJOINT

开发结构变化：component size 从统一 `3` 改为：

```text
[2, 3, 5, 4]
```

每个 component 有自己的 terrestrial window；capacity = `|O_c|-1`，因此每个 component产生1个 local backup deficit；time blocks互不重叠。

冻结 event sequence：

```text
initial
send_pending in size-3 component
gateway_receipt same obligation
final_ack same obligation
time-boundary crossing in size-2 component
global satellite-budget decrement
```

研究问题：local dependency invalidation是否与 component size无关。

## H2 — BRIDGED_PAIR

四个 base groups，sizes：

```text
[3, 4, 3, 2]
```

其中 group0 / group1 除各自 local window外，共享一个合法 terrestrial bridge window `bridge-01`；group2 / group3保持独立。

初始 graph 应当因此包含：

```text
component A = group0 ∪ group1
component B = group2
component C = group3
```

冻结 event sequence：

```text
initial
pending feedback on group0 obligation
consume one slot in group0 local window
consume bridge-01 capacity
global satellite-budget decrement
```

研究问题：algorithm不得把“逻辑上两个subgroup”误当可独立复用；shared bridge存在时，依赖传播必须尊重真实 connected component。

## H3 — CHAIN_OVERLAP_SPLIT

四个 groups，sizes：

```text
[2, 3, 2, 3]
```

group0–group1共享 `bridge-01`，group1–group2共享 `bridge-12`，形成 chain；group3完全独立。

初始 graph：

```text
component A = group0 ∪ group1 ∪ group2
component B = group3
```

`bridge-01` 与 `bridge-12` 都是 frozen future opportunity，不会在未来“凭空出现”；event 只允许耗尽/过期，使 edge消失。

冻结 event sequence：

```text
initial
consume bridge-01 to exhaustion
cross bridge-12 validity boundary
pending feedback in remaining chain
global satellite-budget decrement
```

研究问题：当旧大 component因 opportunity edge消失而 split，runtime能否重算受影响旧 component，同时继续复用完全独立 group3；若 partition安全条件不满足，fallback必须 conservative而非复用错误证书。

## H4 — MIXED_LOCAL_GLOBAL

五个 asymmetric disconnected groups：

```text
[2, 4, 3, 5, 2]
```

全部 component依赖 shared satellite budget，但 terrestrial windows彼此独立。

冻结 event sequence：

```text
initial
local send_pending in group1
local terrestrial capacity consumption in group3
local final_ack in group1
global satellite-budget decrement
local time-boundary crossing in group0
```

研究问题：local event与global validity event交错时，dependency-local invalidation和global invalidation能否同时保持 fresh-equivalent。

## Pre-registered checks

每个 motif 都必须报告：

1. incremental snapshot == fresh full rebuild at every event；
2. exact fresh == ordinary persistent == dependency-cache action frontier；
3. component recompute / reuse / partition fallback逐 event；
4. exact expansions逐 event；
5. initial / final optimistic feasibility 与 backup lower bound；
6. topology signature（component membership + shared opportunity IDs）必须等于 frozen manifest预期；
7. resource/timeout termination不得转换成 infeasibility。

## Claim policy

### 若全部 correctness checks PASS

可以写：Future-Choice incremental maintenance在未见 topology motif上保持 fresh-equivalent，并在适用时复用 dependency-disjoint components；bridge/split topology会正确扩大 invalidation scope或触发 conservative fallback。

### 若 correctness PASS但复用收益消失

保留结果。可以写：representation/correctness泛化成立，但incremental efficiency依赖 graph locality。

### 若某 motif触发 partition fallback

不视为 method failure，只要 fresh-equivalent。正文应把它写成明确的 safety boundary。

### 若 incremental/fresh 不一致

B6 FAIL，必须修 correctness；禁止把该 motif从 holdout删除。
