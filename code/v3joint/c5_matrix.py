# -*- coding: utf-8 -*-
"""c5_matrix.py — same-information ordinary vs candidate config terminators (LOCAL experiment).

Task 1 (announced validity): upgrade command carries absolute valid_until = downgrade time.
Task 2 (runtime authorisation, downgrade authorised during the outage and undeliverable): node only
has clock, measured SoC, expected solar curve, protocol period and pre-authorised fallback rights.
No Task-2 strategy reads `down`. All arms share clock night floor / generic_expiry / maxcov / online
install (lease starts at the actual over-the-air dense-apply edge, never at t=0).

Usage: python3 c5_matrix.py [seeds..]   (default seeds 0 1 2)
Writes results/c5_matrix.json (local, untracked) and prints a compact table.
"""
import os, sys, json, statistics
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
for d in ("v3joint", "instance", "physics", "runtime", "experiments", "analysis", "monitoring"):
    p = os.path.join(REPO, "code", d)
    if p not in sys.path:
        sys.path.insert(0, p)
sys.path.insert(0, HERE)
import c5_common
c5_common.install()
import c5_gate
c5_gate.install()   # Task-2 走外推发布；Task-1（valid_until）保留预告时刻表
from joint_run import run_joint

H = lambda h: h * 3600
RATE = 1200
PHASES = {
    "A": dict(up=H(2), down=H(6), ostart=4, ohours=16),
    "B": dict(up=H(1), down=H(8), ostart=6, ohours=16),
}
PEAKS = [.012, .03]


def base(ph, peak, mission_mode):
    up, down = PHASES[ph]["up"], PHASES[ph]["down"]
    sched = [(0, 600, "blue"), (up, 300, "yellow"), (down, 600, "blue")]
    return dict(task_hours=48, tail_hours=1, arm="local", groups=2,
                sample_interval_s=600, report_period_s=600, routine_period_s=600,
                harvest_mode="solar", harvest_peak_wh_per_hour=peak, capacity_wh=0.05,
                initial_soc=1.0, outage_start_h=PHASES[ph]["ostart"],
                outage_hours=PHASES[ph]["ohours"],
                enable_backup=True, backup_rate_s=RATE, backup_bytes=78,
                backup_chooser="maxcov", cache_service="generic_expiry",
                mission_schedule=sched, mission_mode=mission_mode, collect_rows=True)


# strategy -> (c5_mode, mission_mode, cfg overrides)
def strategies(ph):
    down = PHASES[ph]["down"]
    return {
        "all_sparse":   ("nightfloor", "ignore", {}),
        "nightfloor":   ("nightfloor", "dayfeed", {}),
        "valid_until":  ("valid_until", "dayfeed", {"valid_until_s": down}),       # Task 1 ordinary
        "ttl4":         ("ttl", "dayfeed", {"ttl_delta_s": H(4)}),
        "ttl8":         ("ttl", "dayfeed", {"ttl_delta_s": H(8)}),
        "soc_mpc":      ("soc_mpc", "dayfeed", {"reserve_mult": 1.0, "peak_frac": 1.0}),
        "soc_mpc_cons": ("soc_mpc", "dayfeed", {"reserve_mult": 4.0, "peak_frac": 1.0}),
        "energy_lease": ("energy_lease", "dayfeed", {"reserve_mult": 1.0, "peak_frac": 1.0}),
        "lease_safety": ("lease_safety", "dayfeed", {"reserve_mult": 1.0,
                                                     "safety_mult": 4.0, "peak_frac": 1.0}),
    }


DEFAULTS = dict(ttl_delta_s=H(8), valid_until_s=None, peak_frac=1.0, reserve_mult=1.0,
                safety_mult=4.0)


def run_one(ph, peak, seed, name, spec):
    c5mode, mmode, ov = spec
    # 信息条件按臂分开：valid_until 是 Task 1（升级命令携带绝对有效期，时刻表属预告），
    # 其余臂是 Task 2（运行中获得授权），网关不得提前看到下一段的真实 end。
    c5_gate.MODE = "task1" if c5mode == "valid_until" else "task2"
    c5_common.C5Config.mode = c5mode
    c5_common.C5Config.peak_wh_h = peak
    c5_common.C5Config.task_end_s = 49 * 3600
    for k, v in DEFAULTS.items():
        setattr(c5_common.C5Config, k, v)
    for k, v in ov.items():
        setattr(c5_common.C5Config, k, v)
    r, inst, _ = run_joint(seed=seed, local_floor=True, **base(ph, peak, mmode))
    up, down = PHASES[ph]["up"], PHASES[ph]["down"]
    rows = [x for x in r["rows"] if x["kind"] == "routine" and not x.get("censored")]
    yel = [x for x in rows if up <= x["release_at"] < down]
    ydel = [x for x in yel if x["delivered"]]
    ymiss_collect = [x for x in yel if not x.get("collected")]
    ymiss_transit = [x for x in yel if x.get("collected") and not x["delivered"]]
    sv = r["survival"]
    mins, fins, revt, revw, sampled = [], [], [], [], 0
    for nid, n in inst.nodes.items():
        if hasattr(n, "_c5_min_soc"):
            mins.append(n._c5_min_soc)
        else:
            mins.append(n.soc_wh)
        fins.append(n.soc_wh)
        sampled += getattr(n, "sampled", 0)
        if getattr(n, "_c5_revert_t", None):
            revt.append(n._c5_revert_t)
            revw.append(n._c5_revert_why)
    return {
        "svc": round(r["routine"]["delivered"] / r["routine"]["n"], 4),
        "dead": len(sv.get("dead", [])),
        "dead_ids": sv.get("dead", []),
        "yellow_n": len(yel),
        "yellow_delivered": len(ydel),
        "yellow_miss_collect": len(ymiss_collect),
        "yellow_miss_transit": len(ymiss_transit),
        "yellow_delivered_oids": sorted(x["oid"] for x in ydel),
        "min_soc": round(min(mins), 6) if mins else None,
        "mean_final_soc": round(statistics.mean(fins), 5) if fins else None,
        "revert_t_h": [round(t / 3600, 2) for t in sorted(revt)],
        "revert_why": {w: revw.count(w) for w in set(revw)},
        "sampled": sampled,
    }


def main():
    seeds = [int(x) for x in sys.argv[1:]] or [0, 1, 2]
    out = {"phases": {k: {kk: vv / 3600 for kk, vv in v.items()} for k, v in PHASES.items()},
           "peaks": PEAKS, "seeds": seeds, "cells": {}}
    for ph in PHASES:
        for peak in PEAKS:
            for name, spec in strategies(ph).items():
                runs = [run_one(ph, peak, s, name, spec) for s in seeds]
                key = f"{ph}|{peak}|{name}"
                agg = {
                    "svc_mean": round(statistics.mean(x["svc"] for x in runs), 4),
                    "dead_total": sum(x["dead"] for x in runs),
                    "yellow_delivered_total": sum(x["yellow_delivered"] for x in runs),
                    "yellow_n_total": sum(x["yellow_n"] for x in runs),
                    "yellow_miss_collect_total": sum(x["yellow_miss_collect"] for x in runs),
                    "min_soc_worst": min(x["min_soc"] for x in runs if x["min_soc"] is not None),
                    "mean_final_soc": round(statistics.mean(x["mean_final_soc"] for x in runs), 5),
                    "runs": runs,
                }
                out["cells"][key] = agg
                print(f"{ph} p={peak:<5} {name:14} svc={agg['svc_mean']:.4f} dead={agg['dead_total']:>2} "
                      f"Ydel={agg['yellow_delivered_total']}/{agg['yellow_n_total']} "
                      f"missCol={agg['yellow_miss_collect_total']:>3} "
                      f"minSoc={agg['min_soc_worst']:.5f} finSoc={agg['mean_final_soc']:.4f}")
    od = os.path.join(REPO, "results")
    os.makedirs(od, exist_ok=True)
    p = os.path.join(od, "c5_matrix.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("saved", p, flush=True)


if __name__ == "__main__":
    main()
