# Dynamic World / Alias-Bundle Materialization v0.1

状态：**CURRENT / Layer-1 construction stage complete**
上游 authority：`LAYER1-AUTHORITY.md`、`LAYER1-CURRENT-STATE.v0.1.json`
实现：`code/evaluation/benchmark/dynamic_world_materializer_v0_1.py`

## 1. 这一层拥有的对象

`compositional_recipe_generator_v0_1.py` 冻结的是组合坐标；本层把每个坐标编译成一个可以交给后续 causal process / oracle 的 world IR：

```text
CandidateRecipe
→ source-deadline obligation timeline
→ public warning/geometry/resource environment
→ dynamic terrestrial service worlds
→ recovery-state contract
→ observation-equivalent alias set
→ evidence-surface skeleton
```

输出仍是 `NOT_BENCHMARK_ADMIT`。本层不运行 exact oracle，不产生 V0–V9 disposition，不把 hardness candidate 当成 hardness label，也不生成 query/ACK 的未来答案。

## 2. 一对一 materialization

冻结 universe 中的 **58,752 个 recipe 各产生一个 world bundle**。不在 materialization 阶段通过复制 world、随机 seed 或过滤 easy cell 改变候选总数。

当前 manifest：

```text
58,752 input recipes
→ 58,752 dynamic world / alias bundles

alias world count:
  1 world : 14,688
  2 worlds: 14,688
  3 worlds: 14,688
  4 worlds: 14,688
```

完整机器快照见 `results/benchmark/layer1-world-materialization-v0.1.json`。`bundle_id_stream_sha256` 冻结 bundle 身份序列；它用于检测 materializer 语义漂移，不把 bundle 数量解释成 benchmark case count。

## 3. Obligation timeline

DB44 source-resolved `report_interval_s` 继续拥有每条 reporting obligation 的 deadline：

```text
deadline_s - release_s == report_interval_s
```

`overlap_count ∈ {2,3,4}` 只控制同时存在的 reporting streams，并明确标成 `CONTROLLED_STRESS`。materializer 采用半个 source interval 的 release spacing，使 workload density 真正产生 overlapping active obligations；它没有改变任何单条 obligation 的来源时限，也没有把 overlap count 解释成来源规定的现场节点数。

warning workload 在 episode 起点保留显式 transition contract。`from/to warning_state` 与 cadence 来自 DB44 source cells；transition placement 属于 `CONTROLLED_STRESS`。前一 warning cell 若存在 cadence range，固定使用最小 source-valid interval 作为 deterministic boundary rule，仅用于 transition metadata，不覆盖当前 recipe 的 exact interval。

## 4. Geometry 与 service process

Connecta 48h、20° mask opportunity 来自冻结 `MODEL_DERIVED_TRACE`。几何窗口是 public environment：所有 alias worlds 共享同一组 satellite windows，policy 不需要 query 才知道公开 geometry，也不能通过隐藏 geometry 人为制造 EvidenceNeed。

四类 service process 在 world IR 中承担不同角色：

- `STEADY_AVAILABLE_CONTROL`：持续 terrestrial service，保留 easy/conformance anchor；
- `MONOTONE_RECOVERY_NEGATIVE`：不同 world 只有 recovery time 不同，恢复后持续可用，保留 historical shortcut regression；
- `FINITE_CROSSING_WINDOWS`：每个 obligation 有有限 terrestrial rescue opportunity，不同 world 丢失不同 opportunity；
- `MULTI_WINDOW_DYNAMIC`：每个 obligation 有 early/late windows，不同 world 保留不同非嵌套组合。

这些 terrestrial schedule 都是 `CONTROLLED_STRESS`，不声称是现场 outage 分布。Jiaozuo 的 `NB → 4G/5G → BeiDou` priority 保存在 public contract；world IR 把更高优先级 terrestrial path 聚合成 service class，不因此授予 center 任意 per-slot path override authority。

## 5. Shared resource 与 recovery

recipe 的 `resource_headroom` 继续映射到 normalized satellite rescue budget。该 budget 是 binding-resource coverage 用的 `CONTROLLED_STRESS`，不是电池能量，也不伪装成实际卫星吞吐率。

DZ/T 0450 的 `minimum_cache_days = 7` 原样进入 recovery contract。`RECONNECT_RECONCILE_OBJECTIVE_CHECK` 不填补 `reconnect_backlog_priority`：如果后续 oracle 发现 fresh/backlog 无法同时完成且需要牺牲顺序，V7 必须返回 `OBJECTIVE_AMBIGUOUS`。当前有 **9,792** 个 bundle 从 recipe 层直接携带这一 blocker。

## 6. Alias-world boundary

world bundle 只冻结 physical future support；support size 不由 evidence regime 决定。当前规则：

```text
STEADY_AVAILABLE_CONTROL      → 1 world
other dynamic service process → overlap_count worlds
```

evidence regime 只决定 policy 当前能观察什么、能否主动查询，以及执行后会收到什么反馈；它不改变 underlying physical worlds。partial-observation bundle 的 worlds 共享同一个 `initial_public_observation_hash`。world 差异落在 terrestrial service schedule、后续 delivery receipt state 和必要时 recovery state；公开 satellite geometry 永远不进入 hidden fields。`FULL_OBSERVATION_CONTROL` 也只获得 full **current** state，不提前知道 future service realization，因此不能退化为 clairvoyant upper bound。

`evidence_surfaces` 当前只声明 owner/capability：passive ACK、owner query、normal send-as-probe。每个 world 对这些 evidence 的具体值、`sampled_at`、`arrived_at`、freshness、query 与 execution 的因果关系全部保持 `PENDING_NEXT_STAGE`。这样可以阻止 materializer 直接把 future truth 写成 current query answer。

## 7. 下一阶段契约

下一阶段固定为 `CAUSAL_OBSERVATION_EVIDENCE_PROCESS`。它必须在当前 world bundle 上补齐：

1. passive telemetry / ACK 的真实触发事件与到达时间；
2. owner query 的 sample time、transport/arrival time 与 freshness；
3. normal send-as-probe 的执行结果与观测副作用；
4. 同一 observable history 的 world partition；
5. gateway receipt 与 final center completion 的分离；
6. query/ACK 更新后 alias set 的单调收缩或明确失效原因。

完成 causal process 后才进入 exact full-state / observation-matched oracle，再依次运行 V0–V9。materialization 的 58,752 bundles 仍不能写成 benchmark cases。
