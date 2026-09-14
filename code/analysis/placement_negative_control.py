"""判别 A 的**正确负对照**：给中心也免掉回传跳。

**为什么原来那个负对照是错的。** §7.112（`docs/s8-report/progress-log.md`）诊断出：
把"接入中断"当负对照**不能**证伪仪器——网关的优势来源是**它比中心少一跳回传**，
而接入中断对两个放置**一视同仁**（都听不到新东西），**并不移除回传跳**。
实测残差在**无中断档就已经存在**（Δ服务 +0.30），所以那个控制**从一开始就不成立**。

**正确的控制**：把**回传跳的代价消掉**——`backhaul_p_good = 1.0`（无损、零延迟）。
于是中心收到的遥测与网关**同一 tick**，下发的命令也**同一 tick**进同一个队列，
两个位置的**证据与命令路径完全等价** ⇒ **同一个策略在两处必须给出逐位相同的运行**。
**若仍有差，才是仪器漏了信息或权力。**

    python3 code/analysis/placement_negative_control.py --seeds 3

写 `results/placement_negative_control.json`。
"""
from __future__ import annotations

import argparse
import json
import os as _os
import sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, _CODE,
           *(_os.path.join(_CODE, d) for d in
             ("physics", "runtime", "experiments", "analysis", "monitoring", "instance"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

from instance_run import one_seed                                        # noqa: E402
from placement_contrast import BASE                                      # noqa: E402

RES = _os.path.normpath(_os.path.join(_CODE, "..", "results"))
ARMS = ("ea_aoi", "aoi")
#: 控制条件：**无中断 + 无损零延迟回传**；以及**接入中断 + 无损零延迟回传**。
CONTROLS = {
    "D1_perfect_backhaul_no_outage": dict(backhaul_p_good=1.0),
    "D2_perfect_backhaul_access_outage": dict(backhaul_p_good=1.0,
                                              access_outage_start_h=4.0,
                                              access_outage_h=3.0),
}
#: **按设计就该不同的键**：前者是"命令由谁产生"的记账（位置对照的定义本身），
#: 后者是执行位置本身。
BY_DESIGN = {"placement", "cache_backlog"}
BY_DESIGN_COUNTER = {"commands_sent_by_gateway"}


def diff_paths(a, b, path=""):
    """递归找出两侧**取值不同**的路径。"""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k in BY_DESIGN:
                continue
            if k in BY_DESIGN_COUNTER:
                continue
            out += diff_paths(a.get(k), b.get(k), f"{path}.{k}" if path else k)
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}[len {len(a)} vs {len(b)}]"]
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff_paths(x, y, f"{path}[{i}]")
        return out
    return [] if a == b else [f"{path}: {a!r} != {b!r}"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--out", default="placement_negative_control")
    args = ap.parse_args()

    out = {"note": ("正确负对照＝把**回传跳的代价**消掉（`backhaul_p_good = 1.0`）。"
                    "两个位置的证据与命令路径因此完全等价，同一策略必须给出**逐位相同**的运行。"
                    "原「接入中断作负对照」是控制设计错误：残差来自回传跳，"
                    "而接入中断不移除它（无中断档 Δ 已达 +0.30）。"),
           "arms": list(ARMS), "controls": {}, "by_design_ignored": sorted(BY_DESIGN | BY_DESIGN_COUNTER)}
    for cond, over in CONTROLS.items():
        blk = {"overrides": over, "per_arm": {}}
        for arm in ARMS:
            pairs = []
            for s in range(args.seeds):
                kw = {**BASE, **over}
                c = one_seed(s, arm=arm, placement="center", **kw)
                g = one_seed(s, arm=arm, placement="gateway", **kw)
                d = diff_paths(c, g, f"seed{s}")
                pairs.append({"seed": s, "identical": not d, "n_diff_paths": len(d),
                              "diff_sample": d[:8]})
            blk["per_arm"][arm] = {
                "all_seeds_identical": all(p["identical"] for p in pairs),
                "per_seed": pairs,
                "service_center": [one_seed(s, arm=arm, placement="center",
                                            **{**BASE, **over})["routine"]["delivered"]
                                   for s in range(args.seeds)],
            }
        out["controls"][cond] = blk

    path = _os.path.join(RES, f"{args.out}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"wrote {path}\n")
    for cond, blk in out["controls"].items():
        print(f"=== {cond}  覆盖 {blk['overrides']}")
        for arm, r in blk["per_arm"].items():
            print(f"  {arm:<8} 全部种子逐位相同 = {r['all_seeds_identical']}"
                  f"  服务(中心放置) = {r['service_center']}")
            for p in r["per_seed"]:
                if not p["identical"]:
                    print(f"      seed{p['seed']} 差异 {p['n_diff_paths']} 处: {p['diff_sample']}")


if __name__ == "__main__":
    main()
