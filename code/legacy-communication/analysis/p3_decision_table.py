"""P3：一张可决策的表（doc 58 §P3）。

**只读已有结果，不重跑**：把 P2（`pacing_copies.json`）与上一轮（`pacing_fair.json`）
的臂**合并成一个前沿**——两个文件的基底、中断条件、执行位置、`dwell_s` 与 20 个开发种子
必须一致（脚本先断言，不一致就响亮失败）。

沿用 doc 58 §P3 的读数约定：**固定分母**（672，不改 SLA）、主研究容差 **0% / 1%**、
边界容差 **3% / 5%**；**上行、下行尝试、上行空口、总能耗、AoI、缺采六列分别报告**。
参照服务取**冻结普通基线**中最高者（doc 53/54/60 的同一取法）。

    python3 code/analysis/p3_decision_table.py
"""
from __future__ import annotations

import json
import os as _os

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
RES = _os.path.normpath(_os.path.join(_CODE, "..", "results"))

TOLERANCES = (0.00, 0.01, 0.03, 0.05)
MAIN = ("0.00%", "1.00%")
AXES = ("uplinks", "downlink_attempts", "airtime_uplink_h", "energy_consumed_wh",
        "aoi_mean_s", "missing_collection")
SRC = ("pacing_copies", "pacing_fair")
#: 参照（定容差分位）用的**冻结普通基线**——它们参与前沿竞争，
#: 但与 doc 60 一样：**参照服务的分位由这一组决定**，不由候选决定。
REFERENCE_SET = ("local", "fixed300", "fixed600", "fixed900", "fixed1800", "fixed3600",
                 "aoi", "aoi_const300", "aoi_f600", "aoi_t7200")


def main() -> None:
    data = {t: json.load(open(_os.path.join(RES, f"{t}.json"), encoding="utf-8"))
            for t in SRC}
    a, b = data["pacing_copies"], data["pacing_fair"]
    for k in ("base", "placement", "seeds"):
        assert a[k] == b.get(k), f"两个来源的 {k} 不一致：{a[k]} != {b.get(k)}"
    print(f"来源一致：base={a['base']} placement={a['placement']} seeds={a['seeds']}")

    out = {"sources": list(SRC), "denom": None, "tolerances": list(TOLERANCES),
           "main_tolerances": list(MAIN), "axes": list(AXES), "conditions": {}}

    for cond in a["rows"]:
        assert cond in b["rows"], f"{cond} 不在 {SRC[1]} 里"
        merged: dict[str, dict] = {}
        origin: dict[str, str] = {}
        for tag, src in (("pacing_copies", a), ("pacing_fair", b)):
            for arm, row in src["rows"][cond].items():
                if arm in merged:
                    # 同一臂在两个文件里都跑过：**必须逐项一致**，否则不能合并
                    for k in AXES + ("service",):
                        if row.get(k) != merged[arm].get(k):
                            raise SystemExit(
                                f"{cond}/{arm} 在两来源间不一致：{k} "
                                f"{merged[arm].get(k)} != {row.get(k)}")
                    continue
                merged[arm] = row
                origin[arm] = tag
        den = merged["fixed300"]["service_denom"]
        ref_arm = max(REFERENCE_SET, key=lambda x: merged[x]["service"])
        ref_srv = merged[ref_arm]["service"]
        ref_mc = merged[ref_arm]["missing_collection"]
        block = {"denom": den, "n_arms": len(merged), "reference_arm": ref_arm,
                 "reference_service": ref_srv, "reference_missing_collection": ref_mc,
                 "origin": origin, "points": {}}
        for t in TOLERANCES:
            floor = ref_srv - t * den
            feas = [x for x in merged if merged[x]["service"] >= floor - 1e-9]
            cheapest = {}
            for ax in AXES:
                pick = min(feas, key=lambda x: (merged[x][ax] if merged[x][ax] is not None
                                                else float("inf")))
                cheapest[ax] = {"arm": pick, "value": merged[pick][ax],
                                "service": round(merged[pick]["service"], 4),
                                "missing_collection": merged[pick]["missing_collection"],
                                "origin": origin[pick]}
            viol = [x for x in feas
                    if (merged[x]["missing_collection"] or 0) > ref_mc + 1e-9]
            block["points"][f"{t:.2%}"] = {
                "floor": round(floor, 4), "n_feasible": len(feas),
                "cheapest_by_axis": cheapest, "violating_missing_collection": viol}
        # **上一条表**：全部臂六列分列（不省略任何一列）
        block["table"] = {
            x: {k: merged[x][k] for k in ("service", "missing_collection",
                                          "missing_delivery", *AXES)}
            for x in sorted(merged, key=lambda y: -merged[y]["service"])}
        out["conditions"][cond] = block
        out["denom"] = den

    path = _os.path.join(RES, "decision_table.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"wrote {path}\n")

    hdr = (f"{'档':<18}{'容差':>6}{'可行':>5}{'地板':>8}  "
           f"{'上行':<26}{'下行':<26}{'空口h':<26}{'总能耗Wh':<26}{'AoI s':<26}{'缺采':<26}")
    for cond, blk in out["conditions"].items():
        print(f"===== {cond}  参照 {blk['reference_arm']} = {blk['reference_service']:.2f}"
              f"/{blk['denom']}（缺采 {blk['reference_missing_collection']:.2f}）"
              f"  臂数 {blk['n_arms']}")
        print(hdr)
        for t, pt in blk["points"].items():
            c = pt["cheapest_by_axis"]
            tag = "★主" if t in MAIN else " 边界"
            cells = ""
            for ax in AXES:
                v = c[ax]
                val = ("—" if v["value"] is None else
                       f"{v['value']:.4g}")
                cells += f"{v['arm']}({val})".ljust(26)
            print(f"{tag:<18}{t:>6}{pt['n_feasible']:>5}{pt['floor']:>8.2f}  {cells}")
            if pt["violating_missing_collection"]:
                print(f"    ⚠ 违反缺采约束：{pt['violating_missing_collection']}")
        print()


if __name__ == "__main__":
    main()
