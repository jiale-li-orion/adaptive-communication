# -*- coding: utf-8 -*-
"""r47 - does the delivery-bounded lease ever buy SERVICE (not just samples) under tight energy?

r46 at nominal solar (peak .03) showed tau=h6 removes ~48% of post-deadline daytime dense samples
with zero service change (night-floor already gets all svc, 0 deaths; solar caps the savings).
This sweeps tighter harvest (overcast) and multiple seeds, comparing night-floor (tau=None) with
earlier lease ends. If under tight energy an earlier tau reduces deaths / raises deadline-valid
service, the lease is a service mechanism; otherwise it is strictly a resource/state-hygiene gain
and the paper must claim it as such.
"""
import os, sys, json
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from joint_run import run_joint

H2, H6, H8, H10, H12 = (2, 6, 8, 10, 12)
H2, H6, H8, H10, H12 = (x * 3600 for x in (H2, H6, H8, H10, H12))
SCHED = [(0, 600, "blue"), (H2, 300, "yellow"), (H6, 600, "blue")]
TAUS = {"night_floor_h12": None, "lease_h6": H6, "lease_h8": H8, "lease_h10": H10}
PEAKS = [0.03, 0.02, 0.015, 0.012, 0.01]
SEEDS = [0, 1, 2]


def base_for(peak):
    return dict(task_hours=48, tail_hours=1, arm="local", groups=2,
                sample_interval_s=600, report_period_s=600, routine_period_s=600,
                harvest_mode="solar", harvest_peak_wh_per_hour=peak, capacity_wh=0.05,
                initial_soc=1.0, outage_start_h=4, outage_hours=16,
                enable_backup=True, backup_rate_s=1200, backup_bytes=78,
                backup_chooser="maxcov", cache_service="generic_expiry",
                mission_schedule=SCHED, mission_mode="dayfeed", collect_rows=False)


def one(peak, tau, seed):
    r, _i, _o = run_joint(seed=seed, local_floor=True,
                          floor_lease_end_s=(tau if tau is not None else None), **base_for(peak))
    sv = r["survival"]
    return {"svc": round(r["routine"]["delivered"] / r["routine"]["n"], 4),
            "dead": len(sv.get("dead", [])),
            "soc": round(sv.get("mean_final_soc"), 4)}


def main():
    out = {}
    for peak in PEAKS:
        out[str(peak)] = {}
        for name, tau in TAUS.items():
            runs = [one(peak, tau, s) for s in SEEDS]
            agg = {"svc_mean": round(sum(x["svc"] for x in runs) / len(runs), 4),
                   "dead_total": sum(x["dead"] for x in runs),
                   "soc_mean": round(sum(x["soc"] for x in runs) / len(runs), 4),
                   "runs": runs}
            out[str(peak)][name] = agg
            print(f"peak={peak:<5} {name:<14} svc={agg['svc_mean']:.4f} "
                  f"dead={agg['dead_total']:>2} soc={agg['soc_mean']:.3f}")
        print()
    p = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "results", "r47_lease_energy.json")
    json.dump({"schedule": SCHED, "outage_h": [4, 20], "peaks": PEAKS, "seeds": SEEDS,
               "taus": list(TAUS), "results": out},
              open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("saved", p, flush=True)


if __name__ == "__main__":
    main()
