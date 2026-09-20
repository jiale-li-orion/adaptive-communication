#!/usr/bin/env python3
"""audit_seqref.py — 判定 `spec/prereg-nonprescient-sequence-v1.md` 是否被满足。

预注册把口径写死，本文件负责"运行结果有没有兑现它"。八项判定，任一不成立即红：

  1. 预注册文件与两份结果都在盘上，并已登记进 `results/README.md`（未登记的结果不得引用）；
  2. 常数同源：`c5_seqref` 里声明的负载常数与校准参考里由实测推出的常数逐位一致；
  3. 台账校准：用实测逐小时云遮因子复算抽象轨迹，49 个小时末电量的最大偏差不超过容差；
  4. 核例：DP 与"穷举可达决策格上每一条规则"的结论逐位一致，且穷举条数 = 2^可达格数；
  5. 核例分辨力：安全规则数 < 穷举条数（安全过滤真的在起作用），且最强安全固定租约 < DP
     ——仪器在存在可实现差额的实例上必须能把它找出来；
  6. 受检格三方表：DP = 普通组合 = 全知参照 = 满窗义务数，三个差额为 0，恒等式残差为 0，
     且规则前推自检与 DP 一致；
  7. 非预知性：分叉前两个未来的动作序列逐位相同；
  8. 临界严重度：受检格的 `s_full` 必须大于实测标准差，否则"满窗可行"这句在实测噪声下就是空的。

Run: python3 code/experiments/audit_seqref.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
for _d in ("v3joint", "instance", "physics", "runtime", "experiments", "analysis", "monitoring"):
    _p = os.path.join(ROOT, "code", _d)
    if _p not in sys.path:
        sys.path.insert(0, _p)

PREREG = "spec/prereg-nonprescient-sequence-v1.md"
RESULT = "results/c5_seqref.json"
CALIB = "results/reference/c5_seqref_calibration.json"
REGISTRY = "results/README.md"
TOL_SOC_WH = 5e-4          # 台账校准容差：容量的 1%
TESTED = (("A", 0.012), ("A", 0.03), ("B", 0.012), ("B", 0.03))

FAIL: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"    {'PASS' if ok else 'FAIL'}  {what}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAIL.append(what)


def registered(name: str) -> bool:
    """登记表里可能写全相对路径，也可能只写文件名（本仓库两种都出现过）。

    检查工具不该把"自己只认一种写法"报成"结果未登记"——先两种都认。
    """
    with open(os.path.join(ROOT, REGISTRY), encoding="utf-8") as fh:
        text = fh.read()
    return f"`{name}`" in text or f"`{os.path.basename(name)}`" in text


def main() -> int:
    print("  [1] 文件与登记")
    for rel in (PREREG, RESULT, CALIB):
        check(f"{rel} 存在", os.path.exists(os.path.join(ROOT, rel)))
    check("c5_seqref.json 已登记", registered("c5_seqref.json"))
    check("校准参考已登记", registered("c5_seqref_calibration.json"))
    if FAIL:
        print(f"\n  {len(FAIL)} 项失败（后续判定跳过）")
        return 1

    import c5_seqref as S

    res = json.load(open(os.path.join(ROOT, RESULT), encoding="utf-8"))
    cal = json.load(open(os.path.join(ROOT, CALIB), encoding="utf-8"))

    print("  [2] 常数同源（模型声明 vs 参考的声明值，逐位；再与实测值比偏差）")
    dec, mea = cal["declared_constants"], cal["measured_constants"]
    check("稀疏负载与声明值逐位一致", S.LOAD_SPARSE_H == dec["load_sparse_wh_per_h"],
          f"{S.LOAD_SPARSE_H!r} vs {dec['load_sparse_wh_per_h']!r}")
    check("密集负载与声明值逐位一致", S.LOAD_DENSE_H == dec["load_dense_wh_per_h"],
          f"{S.LOAD_DENSE_H!r} vs {dec['load_dense_wh_per_h']!r}")
    check("射频常数与声明值逐位一致", S.RADIO_WH_PER_REPORT == dec["radio_wh_per_report"])
    check("单次采样能耗与声明值逐位一致", S.SAMPLE_WH == dec["sample_wh"])
    check("容量", abs(S.CAP_WH - 0.05) < 1e-12)
    check("声明值与实测值偏差 ≤ 1e-9 Wh/h",
          abs(dec["load_sparse_wh_per_h"] - mea["load_sparse_wh_per_h"]) <= 1e-9
          and abs(dec["load_dense_wh_per_h"] - mea["load_dense_wh_per_h"]) <= 1e-9,
          f"{dec['load_sparse_wh_per_h'] - mea['load_sparse_wh_per_h']:.3e} / "
          f"{dec['load_dense_wh_per_h'] - mea['load_dense_wh_per_h']:.3e}")
    check("单次采样能耗与花费账本一致",
          abs(mea["sample_wh_from_code"] - mea["sample_wh_from_spend"]) < 1e-9,
          f"{mea['sample_wh_from_code']} vs {mea['sample_wh_from_spend']}")

    print("  [3] 台账校准（抽象递推 vs 实测轨迹）")
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
    check(f"最大小时末电量偏差 ≤ {TOL_SOC_WH}", worst <= TOL_SOC_WH,
          f"{worst:.3e} Wh @h{worst_h}")

    print("  [4] 核例：DP vs 穷举")
    core = S.core_instance()
    bf = core["brute_force"]
    check("穷举条数 = 2^可达决策格数", bf["enumerated_rules"] == 2 ** bf["n_cells"],
          f"{bf['enumerated_rules']} = 2^{bf['n_cells']}")
    check("DP 与穷举最优逐位一致", bool(core["dp_matches_brute_force"]),
          f"DP {core['dp']['service_per_node']} vs 穷举 {bf['best']['service_per_node']}")

    print("  [5] 核例分辨力（仪器必须能找出真实差额）")
    check("安全过滤真的在起作用", bf["safe_rules"] < bf["enumerated_rules"],
          f"{bf['safe_rules']}/{bf['enumerated_rules']} 安全")
    ttl = core["best_safe_ttl"]
    gap = core["dp"]["service_per_node"] - ttl["service_per_node"]
    check("最强安全固定租约 < DP（可实现差额 > 0）", gap > 0,
          f"ttl{ttl['k']} {ttl['service_per_node']} vs DP {core['dp']['service_per_node']}，Δ={gap}")

    print("  [6] 受检格三方表")
    for phase, peak in TESTED:
        key = f"{phase}|{peak}|{S.CLOUD_SIGMA}"
        c = res["cells"].get(key)
        if c is None:
            check(f"{key} 在结果里", False)
            continue
        W = c["window_obligations_per_node"]
        dp = c["nonprescient"]["service_per_node"]
        od = c["ordinary"]["service_per_node"]
        om = c["omniscient"]["mean_service_per_node"]
        tag = f"{key}"
        check(f"{tag} 非预知可行", bool(c["nonprescient"]["admissible"]))
        check(f"{tag} 三方都拿到满窗义务", dp is not None and od is not None
              and abs(dp - W) < 1e-6 and abs(od - W) < 1e-6 and abs(om - W) < 1e-6,
              f"W={W} DP={dp} ORD={od} OMNI={om}")
        g = c["gaps"]
        check(f"{tag} 可实现策略差额为 0", abs(g["implementable_strategy_per_node"]) < 1e-9,
              str(g["implementable_strategy_per_node"]))
        check(f"{tag} 信息差额为 0", abs(g["information_per_node"]) < 1e-9)
        check(f"{tag} 恒等式残差为 0", abs(g["identity_residual"]) < 1e-9)
        check(f"{tag} 规则前推自检", bool(c["nonprescient"]["selfcheck_service_agrees"]))
        check(f"{tag} 满窗租约在实测噪声下安全",
              (c["critical_severity"]["s_full_window_lease"] or 0) > S.CLOUD_SIGMA,
              f"s_full={c['critical_severity']['s_full_window_lease']} "
              f"sigma={S.CLOUD_SIGMA}")

    print("  [7] 非预知性：分叉前动作必须一致")
    if not res["nonanticipation"]:
        check("存在非预知性记录", False)
    for key, rec in res["nonanticipation"].items():
        check(f"{key} 分叉前动作一致", bool(rec["agree_before_split"]),
              f"split_hour={rec['split_hour']}")

    print("  [8] 声明的不确定性下确有不可行区（口径不是空话）")
    infeasible = [k for k, c in res["cells"].items()
                  if not c["nonprescient"]["admissible"] and c["gaps"] is None]
    check("存在'无任何可行职责'的格（否则严格口径未被真正触及）", bool(infeasible),
          f"{len(infeasible)} 格")

    print(f"\n  受检格 {len(TESTED)} 个，结果文件 {len(res['cells'])} 格")
    if FAIL:
        print(f"\n  {len(FAIL)} 项失败")
        for f in FAIL:
            print(f"    - {f}")
        return 1
    print("  全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
