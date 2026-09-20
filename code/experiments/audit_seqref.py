#!/usr/bin/env python3
"""audit_seqref.py — 判定 `spec/prereg-nonprescient-sequence-v3.md` 是否被满足。

三代审计的教训：断言"三方满分、差额为零"会随模型一起错；只断言"文件与常数一致"会漏掉层级与
结构错误。本版按 v3 断言四类东西——**层级、结构、执行语义、数值**，每一条都给出可直接运行的见证：

  1. 登记与取代链：v1/v2 结果已归档、两处预注册都已标取代、撤回记录在盘上；
  2. 常数同源 + 离散化契约（`std(levels(σ)) == σ`）+ 台账校准；
  3. **层级**：结果里必须记录"零失电属于风险口径层而非任务要求层"的来源依据，且 strict 端点结论
     必须自带 scope 字段（不得表述成任务不可行或物理不可行）；
  4. **结构**：strict 口径下最优是否**恰好等于**贪心可行性规则（v2 的空洞之处）、λ>0 时是否
     既不同于贪心也不同于永不终止（真正的停止规则）、λ=0 时目标是否对停止时刻不敏感；
  5. **执行语义**：隐藏终点不得改变执行（固定规则与 DP 策略各一条）、窗口后配置仍继续、求值器与 DP
     不接受终点参数；
  6. **数值**：独立反例（永不终止必须被判不安全、TTL8 物理执行破线且复现审阅报告的值、逐拍单调性）、
     strict 端点带临界 σ、每个 λ 的三方量与恒等式、核例穷举与分辨力。

Run: python3 code/experiments/audit_seqref.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
for _d in ("v3joint", "instance", "physics", "runtime", "experiments", "analysis", "monitoring"):
    _p = os.path.join(ROOT, "code", _d)
    if _p not in sys.path:
        sys.path.insert(0, _p)

V3 = "spec/prereg-nonprescient-sequence-v3.md"
V2 = "spec/prereg-nonprescient-sequence-v2.md"
V1 = "spec/prereg-nonprescient-sequence-v1.md"
RESULT = "results/c5_seqref.json"
RES_V1 = "results/c5_seqref_v1_semantics.json"
RES_V2 = "results/c5_seqref_v2_semantics.json"
CALIB = "results/reference/c5_seqref_calibration.json"
WD_V1 = "results/_withdrawn/2026-09-20-c9-v1-semantics.md"
WD_V2 = "results/_withdrawn/2026-09-20-c9-v2-semantics.md"
REGISTRY = "results/README.md"
TOL_SOC_WH = 5e-4
TESTED = (("A", 0.012), ("A", 0.016), ("B", 0.012), ("B", 0.016))

FAIL: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"    {'PASS' if ok else 'FAIL'}  {what}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAIL.append(what)


def registered(name: str) -> bool:
    with open(os.path.join(ROOT, REGISTRY), encoding="utf-8") as fh:
        text = fh.read()
    return f"`{name}`" in text or f"`{os.path.basename(name)}`" in text


def main() -> int:
    print("  [1] 登记与取代链")
    for rel in (V1, V2, V3, RESULT, RES_V1, RES_V2, CALIB, WD_V1, WD_V2):
        check(f"{rel} 存在", os.path.exists(os.path.join(ROOT, rel)))
    check("c5_seqref.json 已登记", registered("c5_seqref.json"))
    check("v1 结果已登记", registered("c5_seqref_v1_semantics.json"))
    check("v2 结果已登记", registered("c5_seqref_v2_semantics.json"))
    check("校准参考已登记", registered("c5_seqref_calibration.json"))
    for name, path in (("v1", V1), ("v2", V2)):
        with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
            txt = fh.read()
        check(f"{name} 预注册已标注被取代", "已被 v3 取代" in txt or "已被 v2 取代" in txt)
    if FAIL:
        print(f"\n  {len(FAIL)} 项失败（后续判定跳过）")
        return 1

    import c5_seqref as S

    res = json.load(open(os.path.join(ROOT, RESULT), encoding="utf-8"))
    cal = json.load(open(os.path.join(ROOT, CALIB), encoding="utf-8"))
    check("结果自述的契约是 v3", res.get("contract") == V3, str(res.get("contract")))

    print("  [2] 常数同源、离散化契约、台账校准")
    dec, mea = cal["declared_constants"], cal["measured_constants"]
    check("稀疏/密集负载与声明值逐位一致",
          S.LOAD_SPARSE_H == dec["load_sparse_wh_per_h"] and S.LOAD_DENSE_H == dec["load_dense_wh_per_h"])
    check("射频与采样常数逐位一致",
          S.RADIO_WH_PER_REPORT == dec["radio_wh_per_report"] and S.SAMPLE_WH == dec["sample_wh"])
    check("声明与实测负载偏差 ≤ 1e-9 Wh/h",
          abs(dec["load_sparse_wh_per_h"] - mea["load_sparse_wh_per_h"]) <= 1e-9
          and abs(dec["load_dense_wh_per_h"] - mea["load_dense_wh_per_h"]) <= 1e-9)
    for sig in (0.02, 0.047, 0.09):
        lv = S.levels(sig)
        check(f"σ={sig} 时 std(levels)==σ", abs(float(np.std(lv)) - sig) < 1e-12,
              f"offset={S.levels_offset(sig):.8f}")
    cd = cal.get("cloud_discretisation", {})
    check("声明 σ 不小于实测 σ（保守）", S.CLOUD_SIGMA >= cd.get("std_factor", 0.0),
          f"声明 {S.CLOUD_SIGMA} 实测 {cd.get('std_factor')}")
    factors = {h["hour"]: h["factor"] for h in cal["hourly"] if h["factor"]}
    dense = {h["hour"] for h in cal["hourly"] if h["interval_s"] == 300}
    tr = S.path_trace(S.CAP_WH, dense, factors, cal["provenance"]["environment"]["peak_wh_per_h"])
    worst = max((abs(tr["hour_end"][h["hour"]] - h["soc_end_wh"])
                 for h in cal["hourly"] if h["soc_end_wh"] is not None), default=0.0)
    check(f"台账校准 max|Δsoc| ≤ {TOL_SOC_WH}", worst <= TOL_SOC_WH, f"{worst:.3e} Wh")

    print("  [3] 层级：风险口径是参数层，strict 只是端点")
    ts = res.get("task_semantics", {})
    for k in ("paper_objective", "paper_reporting", "restart_experiment", "no_extrapolation_rule"):
        check(f"层级依据已记录：{k}", bool(ts.get(k, {}).get("where")), ts.get(k, {}).get("where", ""))
    pd = ts.get("placement_decision", {})
    check("明确写了风险层与任务层的分置", "risk_layer" in pd and "task_layer" in pd)
    check("明确写了没有为差额回调口径", "not_a" not in pd and "not_done" in pd)
    for phase, peak in TESTED:
        c = res["cells"][f"{phase}|{peak}|{S.CLOUD_SIGMA}"]
        st = c["strict"]
        check(f"{phase}|{peak} strict 结论自带 scope",
              "scope" in st and "不构成任务要求" in st["scope"])
        check(f"{phase}|{peak} strict 与计价两口径都给出",
              "feasible_under_strict" in st and bool(c["priced"]))

    print("  [4] 结构：退化见证与真正的停止规则")
    dg = res["witnesses"]["degeneracy"]
    check("strict 口径最优 == 贪心可行性规则（v2 的空洞之处）",
          bool(dg["strict_mode_equals_greedy_feasibility"]))
    check("λ>0 时既不同于贪心可行性规则，也不同于永不终止（真正的停止规则）",
          not dg["priced_lambda_gt_0_equals_greedy_feasibility"]
          and not dg["priced_lambda_gt_0_equals_never_stop"])
    check("λ=0 时目标对停止时刻不敏感", bool(dg["priced_lambda_0_objective_is_flat"]))
    check("见证覆盖整个地平线的小时数", dg["hours_compared"] == S.END_HOUR - S.PHASES["A"]["up_h"],
          str(dg["hours_compared"]))

    print("  [5] 执行语义：隐藏终点不得改变执行；窗口后配置仍继续")
    w = res["witnesses"]
    check("固定规则跨隐藏终点执行逐位相同",
          bool(w["endpoint_invariance_fixed_rule"]["executed_dense_hours_identical"]),
          f"{w['endpoint_invariance_fixed_rule']['true_window_end_h']}h 对 "
          f"{w['endpoint_invariance_fixed_rule']['alternative_window_end_h']}h")
    check("strict 口径的 DP 策略跨计分窗口终点规则表逐位相同",
          bool(w["policy_window_invariance_strict"]["rule_table_bit_identical"]),
          f"比较 {w['policy_window_invariance_strict']['hours_compared']} 小时")
    hem = w.get("hidden_endpoint_not_modelled", {})
    check("授权终点不是决策输入（结构上不可能改变执行）",
          hem.get("revocation_endpoint_is_a_decision_input") is False)
    check("priced 口径对**公开任务表**的依赖是声明的（并区别于隐藏终点）",
          hem.get("mission_schedule_is_public_and_used_for_scoring_only") is True
          and "公开任务表" in hem.get("note", ""))
    with open(os.path.join(ROOT, V3), encoding="utf-8") as fh:
        spec3 = fh.read()
    check("spec v3 声明了任务表假设", "公开任务表" in spec3 or "任务表公开" in spec3)
    pw = w["post_window_execution"]
    check("窗口后配置继续执行（计分只数窗口内）",
          bool(pw["config_runs_to_horizon"]) and abs(pw["service_scored_per_node"] - 48.0) < 1e-9,
          f"计分 {pw['service_scored_per_node']}")
    check("求值器与 DP 都不接受终点参数",
          "endpoint" not in S.evaluate_rule.__code__.co_varnames
          and "endpoint" not in S.solve_nonprescient.__code__.co_varnames)

    print("  [6] 独立反例")
    ns = w["never_stop_is_not_free"]
    check("'永远继续密集'的判定与真正执行整条地平线一致", bool(ns["agree"]),
          f"evaluator={ns['evaluator_safe']} true={ns['true_safe_under_low_branch']}")
    check("'永远继续密集'被判不安全", ns["evaluator_safe"] is False)
    hc = w["ttl8_physical_execution"]
    check("TTL8 物理执行到自己的结束时刻",
          hc["stopped_at_hour"] == 10 and hc["dense_hours_executed"] == list(range(2, 10)))
    check("TTL8 在低采能未来里破线", hc["safe_under_low_branch"] is False,
          f"min_soc={hc['min_soc_wh_low_branch']}")
    check("复现审阅报告的值（v1 偏移约定 0.3295257 mWh）",
          bool(hc["v1_offset_convention_matches_review"]))
    sd = w["sparse_dominance"]
    check("逐拍单调性：稀疏不低于任何密集安排", bool(sd["monotone_as_claimed"]),
          f"max(dense-sparse)={sd['max_dense_min_soc_wh'] if 'max_dense_min_soc_wh' in sd else sd['max_dense_minus_sparse_min_soc_wh']}")

    print("  [7] 数值：strict 端点、三方量与恒等式")
    for key, c in res["cells"].items():
        if not key.endswith(str(S.CLOUD_SIGMA)):
            continue
        cs = c["critical_sigma_strict"]
        check(f"{key} 给出 strict 临界 σ", cs["sparse_only"] is not None or
              not c["strict"]["feasible_under_strict"], str(cs["sparse_only"]))
        for lam, r in c["priced"].items():
            g = r["gaps"]
            check(f"{key} λ={lam} 三方量齐备",
                  None not in (r["nonprescient"]["service_per_node"],
                               r["nonprescient"]["p_death"],
                               r["ordinary"]["service_per_node"], r["ordinary"]["p_death"],
                               r["omniscient"]["mean_service_per_node"],
                               r["omniscient"]["p_death"]))
            check(f"{key} λ={lam} 恒等式残差为 0", abs(g["identity_residual"]) < 1e-9)
            check(f"{key} λ={lam} 两个差额分别给出",
                  "objective_implementable" in g and "objective_information" in g)
            check(f"{key} λ={lam} DP 与规则前推一致",
                  bool(r["nonprescient"]["selfcheck_objective_agrees"]))
            check(f"{key} λ={lam} Task 1 单列",
                  "不参与" in r["ordinary"]["task1_reference"]["note"])

    print("  [8] 核例：DP vs 穷举，且仪器有分辨力")
    core = S.core_instance()
    bf = core["brute_force"]
    check("穷举条数 = 2^可达决策格数", bf["enumerated_rules"] == 2 ** bf["n_cells"])
    check("DP 与穷举最优逐位一致", bool(core["dp_matches_brute_force"]))
    check("安全过滤在起作用", bf["n_admissible"] < bf["enumerated_rules"],
          f"{bf['n_admissible']}/{bf['enumerated_rules']}")
    ttl = core["best_safe_ttl"]
    check("最强安全固定租约 < DP（可实现差额 > 0）",
          core["dp"]["service_per_node"] - ttl["service_per_node"] > 0,
          f"ttl{ttl['k']} {ttl['service_per_node']} vs DP {core['dp']['service_per_node']}")
    check("核例离散化满足 σ 契约",
          abs(core["level_std_check"] - core["declared"]["sigma"]) < 1e-12)

    print(f"\n  结果文件 {len(res['cells'])} 格")
    if FAIL:
        print(f"\n  {len(FAIL)} 项失败")
        for f in FAIL:
            print(f"    - {f}")
        return 1
    print("  全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
