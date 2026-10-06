# Layer-1 v0.6 Case Generation Pipeline

状态：**PRE-ORACLE GENERATION AUTHORITY**  
上位合同：[`ENVIRONMENT-GENERATION-CONTRACT.v0.1.md`](ENVIRONMENT-GENERATION-CONTRACT.v0.1.md) · [`GENERATION-AXES.v0.1.json`](GENERATION-AXES.v0.1.json)  
实现：`code/evaluation/benchmark/generate_layer1_v06_cases.py`

## 1. 生成目标

v0.6 generator 只把已经冻结的 source/model/stress contract 编译成 declarative case universe。它**不读取** ordinary baseline、Layer-2 或 Layer-3 成绩，也不产生 `HARD` 标签。

每个 case 必须能追溯：

1. source task cell；
2. source-owned / model-derived / controlled-stress 变量；
3. obligation composition；
4. terrestrial service support；
5. terrestrial / satellite opportunity derivation；
6. full-state minimum backup demand；
7. feedback/query timing derivation；
8. generator/config/source/trace hashes；
9. deterministic `base_id / case_id / structure_id`；
10. 后续 oracle/filter disposition。

## 2. 两级生成

### 2.1 Base scenario

Base scenario 只包含会改变 world/support/resource topology 的轴：

```text
source task cell
× obligation composition
× terrestrial service-process support family
× terrestrial opportunity capacity
× Connecta geometry mask + slice signature
```

它 materialize：

- 两个报告流、4–6 个 obligations；
- 至少三个 unique release/decision stages；
- 每个 obligation interval 内公开 terrestrial opportunities；
- 预声明的 finite-state `UP/DOWN` support；
- public/model-derived satellite opportunity windows；
- 每个 world 在 full-state 下完成全部 obligations 所需的最小 backup-send 数。

### 2.2 Case variant

只有 `ALL_WORLD_PHYSICAL` base scenario 展开：

```text
feedback timing profile
× remote-query response-delay ratio
× fallback headroom mode
```

`TIGHT` 定义为：

\[
B_{\rm tight}=\max_{w\in\Omega}\min_{\pi\;\text{with full state}}N_{\rm sat}(\pi,w).
\]

`BALANCED=min(TIGHT+1, #obligations)`；`SLACK_CONTROL=#obligations`。这个预算完全由物理 matching 派生，不由任何待评方法成绩决定。

## 3. Obligation composition

DB44/T 2457-2024 给出 source cadence `D`。

- Stream A：`0, D, 2D, ...`
- Stream B / `ALIGNED`：与 A 同 phase
- Stream B / `HALF_PERIOD_OFFSET`：`D/2, 3D/2, ...`
- deadline = `release + D`

若组合少于三个 unique release stages，按 `cache06.md` v0.5 process contract 在 preflight 排除；不是按 hardness 排除。episode horizon 超过 frozen 48h geometry trace 同理排除并计数。

## 4. Terrestrial service support

Service state 定义在 unique release stages 上；同一 stage 之后、下一个 stage 之前的 terrestrial opportunities 共享该 stage 的 `UP/DOWN` 状态。

- `SINGLE_RECOVERY`：至多一个连续 DOWN run；
- `REINTERRUPTIBLE`：至多两个 DOWN runs；
- `FULL_BINARY_SUPPORT`：全部 binary stage-state sequences，作为 diagnostic upper-support control。

Generator 枚举完整 support，不附加现场概率。证据不能读取未来 service sequence。

## 5. Communication opportunities

### 5.1 Terrestrial

对每个 obligation，从其 release 生成 `0.25D`、`0.75D` 两个 candidate opportunity epochs；同一时间戳去重。每个 opportunity 的 normalized capacity 来自 frozen `{1,2}` axis。

该 capacity 后续同时约束 `SEND_TERR` 与 center-placement remote query transport。它只叫 normalized opportunity capacity，不冒充 bytes / airtime / throughput。

### 5.2 Satellite

`CONNECTA_20260922_SIHUI_GEOMETRY_48H` 提供 model-derived visibility windows。Generator：

1. 遍历 trace-profile 已声明 masks `{0,5,10,20,30}`；
2. 以 1800s stride 枚举所有 horizon-fitting slices；
3. 保留 slice 内全部 window starts；
4. 以 300s-rounded relative `(start,end)` shape 去重；
5. 相同 shape 只保存最早 representative slice，并记录等价 slice 数与全部 `equivalent_slice_starts_s`，确保 signature 可反查原始 trace 切片；
6. 不读取任何 policy / baseline 结果。

每个 visible window 的 v0.6 normalized capacity 固定为 1；这只是可审计的 opportunity unit，不声称 PHY throughput 或历史部署服务可用性。

## 6. Full-state physical derivation

对每个 world，构造一个 unit-demand bipartite min-cost flow：

```text
source → obligation (cap=1, cost=0)
obligation → active terrestrial opportunity (cap=1, cost=0)
obligation → satellite opportunity (cap=1, cost=1)
opportunity → sink (cap=declared normalized capacity)
```

只有位于 `[release, deadline]` 内的 opportunity 与 obligation 连边。最小总 cost 即该 world 的 minimum backup demand。无法送满全部 obligations 时，该 world 为 physical-infeasible。

Base scenario disposition：

- `ALL_WORLD_PHYSICAL`
- `MIXED_WORLD_PHYSICAL`
- `NO_WORLD_PHYSICAL`

只有第一类展开正式 dynamic case variants；后两类仍保存在 base-universe artifact，供后续 physical-invalid diagnostics 使用。

## 7. Case identity 与结构 identity

所有 ID 都从 canonical JSON（UTF-8、sorted keys、无浮点非规范表示）计算 SHA-256：

- `base_id = T1V06B-<16 hex>`：base recipe；
- `case_id = T1V06C-<16 hex>`：base + timing/headroom variant；
- `structure_id = T1V06S-<16 hex>`：忽略 source case ID、绝对 geometry slice start，只保留可迁移结构字段与 relative geometry shape。

同一个 commit/config 重生成时 ID 必须稳定。

## 8. Artifacts

生成目录：

```text
local_research/current/benchmark/generated/layer1-v0.6-preoracle/
  base-scenarios.jsonl.gz
  cases.jsonl.gz
  geometry-signatures.jsonl.gz
  MANIFEST.json
```

Git 中保存 generator/schema/audit 和 manifest 摘要；大体积 case universe 留在 ignored `local_research/`。

`MANIFEST.json` 至少记录：

- generator code SHA-256；
- generation axes SHA-256；
- environment contract SHA-256；
- source/profile bundle SHA-256；
- trace SHA-256；
- git commit；
- candidate/base/case/structure counts；
- 每个 axis 的计数；
- 每个 artifact 的 bytes + SHA-256 + canonical uncompressed SHA-256；
- exact regeneration command；
- claim boundary。

## 9. Reproducibility gate

`audit_layer1_v06_generation.py` 至少检查：

1. config/source/trace hash 与 manifest 一致；
2. 所有 case ID / base ID / structure ID 可由内容重算；
3. case 引用的 base 存在；
4. axis value 全部属于 frozen config；
5. source-owned deadline/cadence 未被覆盖；
6. geometry windows 可从 frozen trace + slice 重建；
7. `TIGHT/BALANCED/SLACK` 可从 base physical derivation 重算；
8. 两次独立生成的 canonical uncompressed artifact hash 完全一致。

后续 exact oracle、shortcut audit、ordinary baseline ladder 只能消费这批 frozen cases，不能回写 generator 参数。

