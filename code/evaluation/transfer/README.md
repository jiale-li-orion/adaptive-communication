# External Transfer Probes

这个目录只放**外部 formulation / environment 的最小兼容性与机制探针**。

它不持有 Layer-1 benchmark authority，也不把外部工作重新实现成仓库主方法。正式研究路线由 `research/workstreams/` 记录。

当前：

- `asc_pull_query_future_choice_probe.py`：在 Pull-Based Query Scheduling 的 `state → query action → semantic effectiveness / query cost` 接口上测试 future-choice feasibility shield；只做 formulation-level probe，不宣称复现原论文数值。
- `asc_pull_query_cmdp_replay.py`：Pull-Based AoI/query/value 结构上的 finite-horizon constrained replay。
- `asc_pull_query_conditional_frontier_probe.py`：最小 observation-conditioned future-obligation witness。
- `asc_pull_query_conditional_family.py`：conditional query-chain scaling / persistent-exact negative boundary。
- `asc_pull_query_shared_opportunity_frontier.py`：branch-conditioned obligations × shared opportunities；复用 Layer-2 max-flow/min-cut conflict frontier。
- `asc_pull_query_dynamic_frontier_reuse.py`：多次 semantic observation 下 persistent conditional-domain reuse 与 event-local resource invalidation。
- `asc_pull_query_component_invalidation.py`：revealed branch 内 send/pending/receipt/ACK/time/resource 事件的 component-local invalidation 与 fresh structural rebuild 对账。
- `asc_pull_query_component_strong_baselines.py`：同一 event sequence 下 fresh exact / ordinary persistent exact / dependency-cache exact / incremental conflict-frontier strong ladder。
- `audit_drl_ec3_transfer_fit.py`：静态审计官方 DRL-EC³ emergency-communication environment 是否具备 future-choice transfer 所需结构。
- `audit_uav_attention_future_choice.py`：公开 UAV hard-deadline environment 的 native continuation failure / official heuristic red-team。
- `run_uav_attention_continuation_shield.py`：evaluator-only exact continuation shield upper bound。
- `run_uav_attention_future_choice_lu.py`：L/U + replayable route certificate + exact fallback future-choice prototype。
- `summarize_uav_attention_future_choice_robustness.py`：200/1000-seed compact robustness artifact。
- `run_uav_attention_receding_baselines.py`：depth-k optimistic receding strong baseline。
- `summarize_uav_attention_receding_headroom.py`：N=5 depth4 saturation boundary。
- `select_uav_attention_constructive_cohort.py`：不使用 method/exact 的 N=10 constructive hard-feasible cohort selector。
- `summarize_uav_attention_n10_headroom.py`：N=10 L/U vs depth4/exact compact headroom artifact。
- `summarize_uav_attention_set_mst_attribution.py`：B 的 set-level conflict → C deadline-set MST sound U-bound 跨域归因；固定 N=10 cohort + N=15 bounded probe。
- `summarize_uav_attention_correctness_compute_frontier.py`：复用 legacy Pareto 纪律，把 depth4 / basic-U / set-MST / pure exact 组织成 correctness–compute 非支配前沿；只使用内部 search-state proxy，不冒充 wall time。
- `uav_future_choice_adapter.py`：C 的正式 generic-engine domain adapter；只持有 route transition / set-MST optimistic bound / replayable route certificate / exact domain fallback semantics。
- `audit_uav_generic_engine_n10_parity.py`：冻结 N=10 21-seed cohort 上的 actual core-path parity；要求 generic engine 完整复现 924 个 exact frontier 和 F5/F6 task-quality evidence。
- `freeze_uav_attention_scale_extension_cohorts.py`：冻结 C4 external-paper-matched 50 与 C5 constructive hard-feasible 100；selection 全部 method-independent。
- `run_uav_attention_scale_extension.py` / `scripts/run_uav_attention_scale_chunk.sh`：resource-safe C4/C5 scale execution；不重复 every-frontier pure-exact audit。
- `analyze_uav_attention_scale_extension.py`：Wilson / paired bootstrap / exact McNemar / search-work scale statistics。
- `materialize_future_choice_claim_matrix.py`：从 tracked A/B/C evidence 生成 paper-facing scoped claim matrix；不替代 `results/CLAIMS.md` 的 claim-state authority。
