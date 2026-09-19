"""按 doc 60 §5 的预注册规则判读 `results/pacing_copies.json`。
本模块引用的 `docs/…` 路径为作者本地过程文档，不随仓库发布。

**本脚本只做判读，不重跑实验**：读数来自 `pacing_copies.py`，臂集合与规则先写定在
`docs/s7-method/instance-v1/60-pre-registration-copy-coverage-pacing-2026-09-14.md`。

判读前的两条**读数约定**（先写定，见 doc 61 §0）：

* doc 60 §4 把「服务、缺采、缺送、**AoI**」与「**上行、下行尝试、上行空口、总能耗、死节点**」
  分列 ⇒ **资源成本轴**取 `uplinks / downlink_attempts / airtime_uplink_h / energy_consumed_wh`
  四条；`aoi_mean_s` 是**单独报告的结果轴**（节奏类臂本来就是拿新鲜度换成本的），
  `nodes_dead` 作**不劣约束**而非成本轴。R1/R2 的「成本不高于 / 严格更低」在资源成本轴上判，
  AoI 与死节点**照样逐档列出**，不得省略。
* 「同一服务容差下服务不低于它」读作 `service_arm ≥ service_ref − t·分母`。

    python3 code/analysis/copy_coverage_verdict.py
"""
from __future__ import annotations

import json
import os as _os
import sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
RES = _os.path.normpath(_os.path.join(_CODE, "..", "results"))

RESOURCE_AXES = ("uplinks", "downlink_attempts", "airtime_uplink_h", "energy_consumed_wh")
EPS = 1e-9


def _load(tag: str) -> dict:
    with open(_os.path.join(RES, f"{tag}.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _ci(paired_map: dict, arm: str, ref: str, key: str):
    return ((paired_map.get(f"{arm}|{ref}") or {}).get(key) or {})


def judge(data: dict) -> dict:
    competing = data["competing"]
    copies = [a for a in competing if a.startswith("oblig_copies")]
    backlog = "pacing_backlog900_300"
    cand = "oblig_slack"
    ablations = [a for a in competing if a.startswith("oblig_slack_no_")]
    rivals = list(data["r2_rivals"])
    res: dict = {"reference": data["reference"], "conditions": {}}

    for cond in data["rows"]:
        row = data["rows"][cond]
        pai = data["paired"][cond]
        den = data["reference"][cond]["denom"]
        ref_arm = data["reference"][cond]["reference_arm"]
        ref_srv = data["reference"][cond]["reference_service"]
        ref_mc = data["reference"][cond]["reference_missing_collection"]
        cb = row[backlog]
        cc = row[cand]
        block: dict = {"denom": den, "reference_arm": ref_arm,
                       "reference_service": ref_srv,
                       "reference_ok": (cc["service"] >= ref_srv - 0 * den),
                       "r1": {}, "r2": {}, "r3": {}, "per_axis": {}}

        # ---------------- R1：普通规则是否已覆盖被定位的那一跳
        for t in data["tolerances"]:
            for k in copies:
                ck = row[k]
                svc_ok = ck["service"] >= cb["service"] - t * den
                mc_ok = ck["missing_collection"] <= cb["missing_collection"] + EPS
                axis = {a: ck[a] <= cb[a] + EPS for a in RESOURCE_AXES}
                block["r1"][f"{k}@{t:.2%}"] = {
                    "service": round(ck["service"], 4),
                    "service_ok": bool(svc_ok),
                    "missing_collection": round(ck["missing_collection"], 4),
                    "missing_collection_ok": bool(mc_ok),
                    "cost_ok_by_axis": axis,
                    "cost_ok": all(axis.values()),
                    "aoi_mean_s": round(ck["aoi_mean_s"], 2),
                    "d_aoi_vs_backlog": round(ck["aoi_mean_s"] - cb["aoi_mean_s"], 2),
                    "nodes_dead": ck["nodes_dead"],
                    "holds": bool(svc_ok and mc_ok and all(axis.values())),
                    "strict_cost_below_on": [a for a in RESOURCE_AXES if ck[a] < cb[a] - EPS],
                }
        block["r1_any_holds"] = {
            f"{t:.2%}": any(v["holds"] for kk, v in block["r1"].items()
                            if kk.endswith(f"@{t:.2%}"))
            for t in data["tolerances"]}

        # ---------------- R2：候选是否在**全部**竞争者之上
        for t in data["tolerances"]:
            per_rival, a_ok, b_ok, c_ok = {}, True, True, True
            for r in rivals:
                if r == cand:
                    continue
                cr = row[r]
                svc = cc["service"] >= cr["service"] - t * den
                mc = cc["missing_collection"] <= cr["missing_collection"] + EPS
                axis = {ax: cc[ax] <= cr[ax] + EPS for ax in RESOURCE_AXES}
                strict = [ax for ax in RESOURCE_AXES if cc[ax] < cr[ax] - EPS]
                a_ok &= svc
                b_ok &= mc
                c_ok &= all(axis.values()) and bool(strict)
                per_rival[r] = {
                    "service_ok": bool(svc), "missing_collection_ok": bool(mc),
                    "cost_ok": all(axis.values()), "cost_ok_by_axis": axis,
                    "strictly_lower_on": strict,
                    "d_service": round(cc["service"] - cr["service"], 4),
                    "d_uplinks": round(cc["uplinks"] - cr["uplinks"], 2),
                    "d_energy_wh": round(cc["energy_consumed_wh"]
                                         - cr["energy_consumed_wh"], 6),
                    "d_aoi_s": round(cc["aoi_mean_s"] - cr["aoi_mean_s"], 2),
                    "d_downlink": round(cc["downlink_attempts"] - cr["downlink_attempts"], 2)}
            # R2.d：与「rivals 中服务最高的那条」配对差的区间
            feas = [r for r in rivals if r != cand
                    and cc["service"] >= row[r]["service"] - t * den]
            top = max(feas, key=lambda r: row[r]["service"]) if feas else None
            d_sig = {}
            if top:
                for ax in RESOURCE_AXES + ("service", "missing_collection"):
                    ci = _ci(pai, cand, top, ax)
                    d_sig[ax] = {"mean_delta": ci.get("mean_delta"), "ci95": ci.get("ci95"),
                                 "ci_excludes_0": ci.get("ci_excludes_0"),
                                 "n_pos": ci.get("n_pos"), "n_neg": ci.get("n_neg")}
            strongest = [ax for ax, v in d_sig.items()
                         if ax in RESOURCE_AXES and v["ci_excludes_0"]
                         and v["mean_delta"] is not None and v["mean_delta"] < 0]
            block["r2"][f"{t:.2%}"] = {
                "service_not_worse_than_all": bool(a_ok),
                "missing_collection_not_worse_than_all": bool(b_ok),
                "cost_below_all_with_one_strict": bool(c_ok),
                "top_rival_feasible": top,
                "paired_vs_top_rival": d_sig,
                "cost_axes_ci_excludes_0_lower": strongest,
                "holds": bool(a_ok and b_ok and c_ok and strongest),
                "per_rival": per_rival}
        block["r2_any_holds"] = any(v["holds"] for v in block["r2"].values())

        # ---------------- R3：消融必须解释收益
        for ab in ablations:
            ca = row[ab]
            entry = {}
            for ax in RESOURCE_AXES + ("service", "missing_collection", "aoi_mean_s"):
                ci = _ci(pai, cand, ab, ax)
                entry[ax] = {"d_cand_minus_ablation": round(cc[ax] - ca[ax], 6),
                             "ci95": ci.get("ci95"),
                             "ci_excludes_0": ci.get("ci_excludes_0")}
            block["r3"][ab] = {
                "ablation_name": ab, "axes": entry,
                "indistinguishable_on_costs": all(
                    not entry[ax]["ci_excludes_0"] for ax in RESOURCE_AXES),
                "explains_gain": any(entry[ax]["ci_excludes_0"] for ax in RESOURCE_AXES)}

        # ---------------- 逐臂逐档总表（分列，不省略）
        block["table"] = {
            a: {k: row[a][k] for k in
                ("service", "missing_collection", "missing_delivery", "aoi_mean_s",
                 "uplinks", "downlink_attempts", "airtime_uplink_h",
                 "energy_consumed_wh", "nodes_dead", "n_config_changes",
                 "on_time_heard", "late_heard", "never_heard",
                 "stuck_at_gateway_hop", "delivered", "mean_copies_heard")}
            for a in competing + [ref_arm]}
        block["stuck_vs_backlog"] = {
            a: round(row[a]["stuck_at_gateway_hop"] - cb["stuck_at_gateway_hop"], 2)
            for a in competing}
        block["stuck_vs_backlog_ci"] = {
            a: _ci(pai, a, backlog, "stuck_at_gateway_hop") for a in competing
            if a != backlog}
        block["reference_floor_note"] = (
            f"参照服务取冻结普通基线最高者 {ref_arm}={ref_srv:.2f}/{den}"
            f"（缺采 {ref_mc:.2f}）；容差 1% 折合 {0.01 * den:.2f} 条义务")
        res["conditions"][cond] = block

    # ---------------- 总体判决
    res["verdict"] = {}
    for cond, b in res["conditions"].items():
        if b["r2_any_holds"]:
            v = "候选有余量（须再过 R3）"
        elif b["r1_any_holds"]["0.00%"] or b["r1_any_holds"]["1.00%"]:
            v = "普通规则已覆盖（R1 成立）⇒ 不实现更复杂机制"
        else:
            v = "本轮臂集合内候选与普通规则都未胜出"
        res["verdict"][cond] = {"verdict": v,
                                "r1_any": b["r1_any_holds"], "r2_any": b["r2_any_holds"]}
    res["r1_holds_all_conditions"] = all(
        b["r1_any_holds"]["0.00%"] or b["r1_any_holds"]["1.00%"]
        for b in res["conditions"].values())
    return res


def main() -> None:
    tag = _sys.argv[1] if len(_sys.argv) > 1 else "pacing_copies"
    data = _load(tag)
    out = judge(data)
    path = _os.path.join(RES, "copy_coverage_verdict.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"wrote {path}\n")
    for cond, b in out["conditions"].items():
        print(f"=== {cond}  {b['reference_floor_note']}")
        hdr = (f"{'臂':<26}{'服务':>7}{'缺采':>7}{'上行':>8}{'下行':>7}"
               f"{'空口h':>8}{'能耗Wh':>9}{'AoI':>9}{'卡住':>7}{'副本':>7}")
        print(hdr)
        for a, t in b["table"].items():
            print(f"{a:<26}{t['service']:>7.1f}{t['missing_collection']:>7.1f}"
                  f"{t['uplinks']:>8.0f}{t['downlink_attempts']:>7.0f}"
                  f"{t['airtime_uplink_h']:>8.4f}{t['energy_consumed_wh']:>9.4f}"
                  f"{t['aoi_mean_s']:>9.1f}{t['stuck_at_gateway_hop']:>7.1f}"
                  f"{t['mean_copies_heard']:>7.3f}")
        for key, v in b["r1"].items():
            mark = "✅" if v["holds"] else "❌"
            print(f"  R1 {key:<22} {mark} 服务{v['service_ok']} 缺采{v['missing_collection_ok']}"
                  f" 成本{v['cost_ok_by_axis']} ΔAoI{v['d_aoi_vs_backlog']:+.1f}")
        for key, v in b["r2"].items():
            mark = "✅" if v["holds"] else "❌"
            print(f"  R2 {key:<22} {mark} 服务不劣{v['service_not_worse_than_all']}"
                  f" 缺采不劣{v['missing_collection_not_worse_than_all']}"
                  f" 成本{v['cost_below_all_with_one_strict']}"
                  f" 显著轴{v['cost_axes_ci_excludes_0_lower']} vs {v['top_rival_feasible']}")
        for ab, v in b["r3"].items():
            print(f"  R3 {ab:<24} 解释收益={v['explains_gain']} "
                  f"成本不可区分={v['indistinguishable_on_costs']}")
        print(f"  → {out['verdict'][cond]['verdict']}\n")
    print("R1 在三档全部成立:", out["r1_holds_all_conditions"])


if __name__ == "__main__":
    main()
