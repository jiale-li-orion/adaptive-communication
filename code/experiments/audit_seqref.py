#!/usr/bin/env python3
"""audit_seqref.py — 判定 `spec/prereg-nonprescient-sequence-v2.md` 是否被满足。

v1 的审计断言的是"三方全为满分、差额为零"。那组断言本身没错，但它随模型一起错：它**没有**
独立核对信息契约与不确定性契约，于是两处契约错误（隐藏终点改变执行、等权三点的实际标准差
只有声明值的 √(2/3)）都能全绿通过。本版按 v2 重写，把"能全绿"换成"错就会被抓到"：

  1. 文件、登记与取代关系都在盘上（v1 结果已归档，撤回记录存在，v1 预注册已标取代）；
  2. 常数同源：模型声明 vs 校准参考的声明值逐位一致，并与实测值比偏差；
  3. 离散化契约：`std(levels(σ)) == σ`（**不是**把偏移当标准差）；
  4. 台账校准：用实测逐小时因子复算抽象轨迹，最大小时末电量偏差不超过容差；
  5. **独立反例**（v1 缺陷的直接见证，每次都必须给出）：
     "永远继续密集"规则的安全判定必须与真正执行整条地平线的结论一致；
     `TTL8+8 mWh 门`物理执行到自己的结束时刻后，在低采能未来里必须破线；
     同一策略跨两个隐藏终点的配置轨迹必须逐位相同；
     逐拍单调性（稀疏 ≥ 任何密集安排）必须成立——它是"稀疏破线 ⇒ 无可行策略"的依据；
  6. 可行性前置：受检格先判可行性。不可行的格必须记 `status=infeasible` 且 `gaps=None`，
     并给出破线时的最低电量与临界 σ；临界 σ 必须与声明 σ 直接可比（同为 σ 单位）；
  7. 核例：DP 与"穷举可达决策格上每一条规则"逐位一致，且安全规则数 < 穷举条数、
     最强安全固定租约 < DP（仪器有分辨力）；
  8. 可行格的三方表：三个量都在，两个差额分别给出、恒等式残差为 0、规则前推自检一致、
     Task 1 参照单列而不混入同一信息条件的比较。

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

PREREG_V2 = "spec/prereg-nonprescient-sequence-v2.md"
PREREG_V1 = "spec/prereg-nonprescient-sequence-v1.md"
RESULT = "results/c5_seqref.json"
RESULT_V1 = "results/c5_seqref_v1_semantics.json"
CALIB = "results/reference/c5_seqref_calibration.json"
WITHDRAWN = "results/_withdrawn/2026-09-20-c9-v1-semantics.md"
REGISTRY = "results/README.md"
TOL_SOC_WH = 5e-4
TESTED = (("A", 0.012), ("A", 0.016), ("A", 0.03), ("B", 0.012), ("B", 0.016), ("B", 0.03))

FAIL: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"    {'PASS' if ok else 'FAIL'}  {what}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAIL.append(what)


def registered(name: str) -> bool:
    """登记表里可能写全相对路径，也可能只写文件名；两种都认，别把写法差异报成未登记。"""
    with open(os.path.join(ROOT, REGISTRY), encoding="utf-8") as fh:
        text = fh.read()
    return f"`{name}`" in text or f"`{os.path.basename(name)}`" in text


def main() -> int:
    print("  [1] 文件、登记与取代关系")
    for rel in (PREREG_V2, PREREG_V1, RESULT, RESULT_V1, CALIB, WITHDRAWN):
        check(f"{rel} 存在", os.path.exists(os.path.join(ROOT, rel)))
    check("c5_seqref.json 已登记", registered("c5_seqref.json"))
    check("v1 结果已登记（作为被取代的记录）", registered("c5_seqref_v1_semantics.json"))
    check("校准参考已登记", registered("c5_seqref_calibration.json"))
    with open(os.path.join(ROOT, PREREG_V1), encoding="utf-8") as fh:
        v1 = fh.read()
    check("v1 预注册已标注被 v2 取代", "已被 v2 取代" in v1)
    if FAIL:
        print(f"\n  {len(FAIL)} 项失败（后续判定跳过）")
        return 1

    import c5_seqref as S

    res = json.load(open(os.path.join(ROOT, RESULT), encoding="utf-8"))
    cal = json.load(open(os.path.join(ROOT, CALIB), encoding="utf-8"))

    print("  [2] 常数同源（声明 vs 参考的声明值逐位；再与实测比偏差）")
    dec, mea = cal["declared_constants"], cal["measured_constants"]
    check("稀疏负载逐位一致", S.LOAD_SPARSE_H == dec["load_sparse_wh_per_h"],
          repr(S.LOAD_SPARSE_H))
    check("密集负载逐位一致", S.LOAD_DENSE_H == dec["load_dense_wh_per_h"], repr(S.LOAD_DENSE_H))
    check("射频常数逐位一致", S.RADIO_WH_PER_REPORT == dec["radio_wh_per_report"])
    check("单次采样能耗逐位一致", S.SAMPLE_WH == dec["sample_wh"])
    check("容量", abs(S.CAP_WH - 0.05) < 1e-12)
    check("声明与实测偏差 ≤ 1e-9 Wh/h",
          abs(dec["load_sparse_wh_per_h"] - mea["load_sparse_wh_per_h"]) <= 1e-9
          and abs(dec["load_dense_wh_per_h"] - mea["load_dense_wh_per_h"]) <= 1e-9,
          f"{dec['load_sparse_wh_per_h'] - mea['load_sparse_wh_per_h']:.3e} / "
          f"{dec['load_dense_wh_per_h'] - mea['load_dense_wh_per_h']:.3e}")

    print("  [3] 离散化契约：等权三点的**实际标准差**必须等于声明 σ")
    for sig in (0.02, 0.047, 0.09):
        lv = S.levels(sig)
        check(f"σ={sig} 时 std(levels)==σ", abs(float(np.std(lv)) - sig) < 1e-12,
              f"std={float(np.std(lv)):.10f} offset={S.levels_offset(sig):.8f}")
    check("偏移 = σ·sqrt(3/2)", abs(S.levels_offset(0.047) - 0.047 * np.sqrt(1.5)) < 1e-15)
    cd = cal.get("cloud_discretisation", {})
    check("校准参考记有实测/理论 σ", bool(cd) and cd.get("std_factor") is not None,
          f"实测 {cd.get('std_factor')} 理论 {cd.get('theoretical_std')} 声明 {S.CLOUD_SIGMA}")
    check("声明 σ 不小于实测 σ（保守）", S.CLOUD_SIGMA >= cd.get("std_factor", 0.0),
          f"{S.CLOUD_SIGMA} vs {cd.get('std_factor')}")

    print("  [4] 台账校准（抽象递推 vs 实测轨迹）")
    factors = {h["hour"]: h["factor"] for h in cal["hourly"] if h["factor"]}
    dense = {h["hour"] for h in cal["hourly"] if h["interval_s"] == 300}
    env = cal["provenance"]["environment"]
    tr = S.path_trace(S.CAP_WH, dense, factors, env["peak_wh_per_h"])
    worst, worst_h = 0.0, None
    for h in cal["hourly"]:
        if h["soc_end_wh"] is None:
            continue
        d = abs(tr["hour_end"][h["hour"]] - h["soc_end_wh"])
        if d > worst:
            worst, worst_h = d, h["hour"]
    check(f"最大小时末电量偏差 ≤ {TOL_SOC_WH}", worst <= TOL_SOC_WH, f"{worst:.3e} Wh @h{worst_h}")

    print("  [5] 独立反例：v1 的两处契约错误必须被抓住")
    ce = res.get("counterexamples", {})
    ns = ce.get("never_stop_is_not_free", {})
    check("'永远继续密集'：求值器结论与真正执行整条地平线一致",
          bool(ns.get("agree")), f"evaluator_safe={ns.get('evaluator_safe')} "
                                 f"true={ns.get('true_safe_under_low_branch')}")
    check("'永远继续密集'被正确判为不安全", ns.get("evaluator_safe") is False)
    hc = ce.get("ttl8_physical_execution", {})
    check("TTL8 物理执行到自己的结束时刻（不被真值终点截断）",
          hc.get("stopped_at_hour") == 10 and hc.get("dense_hours_executed") == list(range(2, 10)),
          f"dense={hc.get('dense_hours_executed')} stop=h{hc.get('stopped_at_hour')}")
    check("TTL8 在低采能未来里破线（v2 偏移约定）",
          hc.get("safe_under_low_branch") is False,
          f"min_soc={hc.get('min_soc_wh_low_branch')}")
    check("同一见证复现审阅报告的值（v1 偏移约定 0.3295257 mWh）",
          bool(hc.get("v1_offset_convention_matches_review")),
          f"{hc.get('min_soc_wh_low_branch_v1_offset_convention')}")
    sd = ce.get("sparse_dominance", {})
    check("逐拍单调性：稀疏不低于任何密集安排",
          bool(sd.get("monotone_as_claimed")),
          f"max(dense-sparse)={sd.get('max_dense_minus_sparse_min_soc_wh')}")
    ei = res.get("endpoint_invariance", {}).get("ttl8_alt_window_end", {})
    check("跨隐藏终点同一策略的配置轨迹逐位相同",
          bool(ei.get("executed_dense_hours_identical")),
          f"终点 {ei.get('true_window_end_h')}h 对 {ei.get('alternative_window_end_h')}h")
    check("DP 的动作区间覆盖到地平线（不按窗口终点截断）",
          res["cells"][f"A|0.016|{S.CLOUD_SIGMA}"]["nonprescient"]["action_horizon_hours"][1]
          == S.END_HOUR)

    print("  [6] 可行性前置：先判能否，再谈多少")
    # σ 用**结果文件里声明的扫描点**，不另造键：实测值映射到最接近的扫描点
    sweep = list(res["sigmas"])
    measured_sigma = float(cal["cloud_discretisation"]["std_factor"])
    nearest = min(sweep, key=lambda x: abs(x - measured_sigma))
    print(f"       实测 σ={measured_sigma:.6f} → 用扫描点 σ={nearest}"
          f"（差 {abs(nearest - measured_sigma):.2e}）")
    check("实测 σ 的最近扫描点足够近（≤1e-3）", abs(nearest - measured_sigma) <= 1e-3)
    for phase, peak in TESTED:
        for sig in (S.CLOUD_SIGMA, nearest):
            key = f"{phase}|{peak}|{sig}"
            c = res["cells"].get(key)
            if c is None:
                check(f"{key} 在结果里", False)
                continue
            f = c["feasibility"]
            cs = c["critical_sigma"]
            if not f["feasible"]:
                check(f"{key} 记 infeasible 且不给差额",
                      c["status"] == "infeasible" and c["gaps"] is None,
                      f"稀疏最低 {f['sparse_min_soc_wh_low_branch']*1000:+.5f} mWh")
                check(f"{key} 给出临界 σ 且 < 声明 σ",
                      cs["sparse_only"] is not None and cs["sparse_only"] < sig,
                      f"σ*={cs['sparse_only']} vs σ={sig}")
                check(f"{key} 破线确实低于安全线",
                      f["sparse_min_soc_wh_low_branch"] < S.SAMPLE_WH)
            else:
                check(f"{key} 可行", True,
                      f"稀疏最低 {f['sparse_min_soc_wh_low_branch']*1000:+.4f} mWh")
                check(f"{key} 临界 σ ≥ 声明 σ", (cs["sparse_only"] or 0) >= sig,
                      f"σ*={cs['sparse_only']}")

    print("  [7] 核例：DP vs 穷举，且仪器有分辨力")
    core = S.core_instance()
    bf = core["brute_force"]
    check("穷举条数 = 2^可达决策格数", bf["enumerated_rules"] == 2 ** bf["n_cells"],
          f"{bf['enumerated_rules']} = 2^{bf['n_cells']}")
    check("DP 与穷举最优逐位一致", bool(core["dp_matches_brute_force"]),
          f"DP {core['dp']['service_per_node']} vs 穷举 {bf['best']['service_per_node']}")
    check("安全过滤在起作用", bf["safe_rules"] < bf["enumerated_rules"],
          f"{bf['safe_rules']}/{bf['enumerated_rules']}")
    ttl = core["best_safe_ttl"]
    check("最强安全固定租约 < DP（可实现差额 > 0）",
          core["dp"]["service_per_node"] - ttl["service_per_node"] > 0,
          f"ttl{ttl['k']} {ttl['service_per_node']} vs DP {core['dp']['service_per_node']}")
    check("核例的离散化也满足 σ 契约",
          abs(core["level_std_check"] - core["declared"]["sigma"]) < 1e-12)

    print("  [8] 可行格的三方表与两个差额")
    n_feas = 0
    for key, c in res["cells"].items():
        if c.get("status") != "feasible":
            continue
        n_feas += 1
        g = c["gaps"]
        check(f"{key} 三方量齐备", None not in (c["nonprescient"]["service_per_node"],
                                                c["ordinary"]["service_per_node"],
                                                c["omniscient"]["mean_service_per_node"]))
        check(f"{key} 恒等式残差为 0", abs(g["identity_residual"]) < 1e-9)
        check(f"{key} 两个差额分别给出",
              "implementable_strategy_per_node" in g and "information_per_node" in g)
        check(f"{key} 规则前推自检", bool(c["nonprescient"]["selfcheck_service_agrees"]))
        check(f"{key} Task 1 参照单列",
              "task1_reference" in c["ordinary"]
              and "不参与" in c["ordinary"]["task1_reference"]["note"])
    check("存在可行格（否则第 8 节形同虚设）", n_feas > 0, f"{n_feas} 格")

    print(f"\n  结果文件 {len(res['cells'])} 格，其中可行 {n_feas} 格")
    if FAIL:
        print(f"\n  {len(FAIL)} 项失败")
        for f in FAIL:
            print(f"    - {f}")
        return 1
    print("  全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
