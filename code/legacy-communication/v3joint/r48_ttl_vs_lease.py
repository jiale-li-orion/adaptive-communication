# -*- coding: utf-8 -*-
"""r48 - fixed config-TTL vs delivery-bounded lease across outage/upgrade phases.

A delivery-bounded lease ends dense at the last time its data can still meet an obligation
(backup-aligned). A plain config TTL ends dense a fixed duration after install (the obvious
ordinary mechanism). If one fixed TTL were near-optimal across phases, the delivery geometry adds
nothing and the lease is just a TTL. We use two phases with different gaps upgrade->downgrade,
at tight energy (.012, where r47 showed deaths) and nominal (.03, where early TTL false-releases
yellow), and report deaths / svc / yellow delivered.
"""
import os, sys, json, math
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from joint_run import run_joint

RATE = 1200
# phase A: upgrade h2, downgrade h6(noon), outage h4-h20, sunset h12
# phase B: upgrade h1, downgrade h8, outage h6-h22, sunset h12  (longer dense->downgrade gap)
PHASES = {
    "A": dict(up=2 * 3600, down=6 * 3600, out_start=4, out_hours=16),
    "B": dict(up=1 * 3600, down=8 * 3600, out_start=6, out_hours=16),
}
PEAKS = [0.012, 0.03]
SEEDS = [0, 1, 2]
SUNSET = 12 * 3600


def geo_tau(down):
    last_release = down - 300
    P = 300
    dl = (last_release // P + 2) * P
    return math.ceil(dl / RATE) * RATE


def run_phase(ph, peak, tau, seed):
    up, down = ph["up"], ph["down"]
    sched = [(0, 600, "blue"), (up, 300, "yellow"), (down, 600, "blue")]
    kw = dict(task_hours=48, tail_hours=1, arm="local", groups=2,
              sample_interval_s=600, report_period_s=600, routine_period_s=600,
              harvest_mode="solar", harvest_peak_wh_per_hour=peak, capacity_wh=0.05,
              initial_soc=1.0, outage_start_h=ph["out_start"], outage_hours=ph["out_hours"],
              enable_backup=True, backup_rate_s=RATE, backup_bytes=78,
              backup_chooser="maxcov", cache_service="generic_expiry",
              mission_schedule=sched, mission_mode="dayfeed", collect_rows=True)
    r, _i, _o = run_joint(seed=seed, local_floor=True,
                          floor_lease_end_s=(tau if tau is not None else None), **kw)
    sv = r["survival"]
    rows = [x for x in r["rows"] if x["kind"] == "routine" and not x["censored"]]
    ydel = sum(1 for x in rows if up <= x["release_at"] < down and x["delivered"])
    yn = sum(1 for x in rows if up <= x["release_at"] < down)
    return {"svc": round(r["routine"]["delivered"] / r["routine"]["n"], 4),
            "dead": len(sv.get("dead", [])), "soc": round(sv.get("mean_final_soc"), 3),
            "yellow_delivered": ydel, "yellow_n": yn}


def strategies(ph):
    up, down = ph["up"], ph["down"]
    g = geo_tau(down)
    return {"nightfloor": None,
            "ttl4": up + 4 * 3600, "ttl6": up + 6 * 3600, "ttl8": up + 8 * 3600,
            "delivery_geo": g}


def main():
    out = {}
    for pname, ph in PHASES.items():
        out[pname] = {"geo_tau_h": round(geo_tau(ph["down"]) / 3600, 2), "peaks": {}}
        for peak in PEAKS:
            out[pname]["peaks"][str(peak)] = {}
            for sname, tau in strategies(ph).items():
                runs = [run_phase(ph, peak, tau, s) for s in SEEDS]
                agg = {"dead_total": sum(x["dead"] for x in runs),
                       "svc_mean": round(sum(x["svc"] for x in runs) / 3, 4),
                       "soc_mean": round(sum(x["soc"] for x in runs) / 3, 3),
                       "yellow_delivered": sum(x["yellow_delivered"] for x in runs),
                       "yellow_n": sum(x["yellow_n"] for x in runs)}
                out[pname]["peaks"][str(peak)][sname] = agg
                print(f"phase{pname} peak={peak:<5} {sname:<13} tau_h="
                      f"{None if tau is None else round(tau/3600,2)} dead={agg['dead_total']:>2} "
                      f"svc={agg['svc_mean']:.4f} soc={agg['soc_mean']:.3f} "
                      f"Ydel={agg['yellow_delivered']}/{agg['yellow_n']}")
            print()
    p = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "results", "r48_ttl_vs_lease.json")
    json.dump({"phases": PHASES, "peaks": PEAKS, "results": out},
              open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("saved", p, flush=True)


if __name__ == "__main__":
    main()
