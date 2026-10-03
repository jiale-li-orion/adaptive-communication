# -*- coding: utf-8 -*-
"""r46 (v2) - delivery-bounded config lease oracle sweep, clock-aligned.

Sim clock maps t=0 to local 06:00 sunrise and t=h12 to 18:00 sunset (node floor uses
hod=(6+t/3600)%24, night at hod>=18 i.e. t>=h12). To expose a residual the clock night-floor
cannot reach, the conferred DOWNGRADE must fall in DAYTIME (t<h12) inside the outage:
  upgrade yellow t=h2 (control healthy, applies), downgrade back to sparse t=h6 (noon),
  outage t=h4..h20 (covers the noon downgrade, the 6 daytime hours h6-h12, and the night).
The night-floor only releases dense at t=h12; a lease tau in [h6,h12) is the open window.
tau<h6 risks false-releasing yellow obligations still deliverable over backup. Sweep reports
yellow delivered (must not drop), deaths, daytime wasted dense samples, energy.
"""
import os, sys, json, math
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from joint_run import run_joint

H2, H4, H5, H6, H12, H20 = (2, 4, 5, 6, 12, 20)
H2, H4, H5, H6, H12, H20 = (x * 3600 for x in (H2, H4, H5, H6, H12, H20))
SUNSET = H12
RATE = 1200
SCHED = [(0, 600, "blue"), (H2, 300, "yellow"), (H6, 600, "blue")]
BASE = dict(task_hours=48, tail_hours=1, arm="local", groups=2,
            sample_interval_s=600, report_period_s=600, routine_period_s=600,
            harvest_mode="solar", harvest_peak_wh_per_hour=0.03, capacity_wh=0.05,
            initial_soc=1.0, outage_start_h=4, outage_hours=16,
            enable_backup=True, backup_rate_s=RATE, backup_bytes=78,
            backup_chooser="maxcov", cache_service="generic_expiry",
            mission_schedule=SCHED, mission_mode="dayfeed", collect_rows=True)


def yellow_deadline(taken):
    P = 300 if H2 <= taken < H6 else 600
    return (taken // P + 2) * P


def hourly_profile(inst, nid, lo, hi):
    cnt = {}
    for s in inst.log.samples.values():
        if s.node_id == nid and lo <= s.taken_at < hi:
            h = s.taken_at // 3600
            cnt[h] = cnt.get(h, 0) + 1
    return cnt


def evaluate(tau):
    r, inst, _o = run_joint(seed=0, local_floor=True,
                            floor_lease_end_s=(tau if tau is not None else None), **BASE)
    rows = [x for x in r["rows"] if x["kind"] == "routine" and not x["censored"]]
    yel = [x for x in rows if H2 <= x["release_at"] < H6]
    daywin = [x for x in rows if H6 <= x["release_at"] < SUNSET]      # daytime post-downgrade
    # samples taken in daytime residual window [h6,sunset), per node (dense=12/h, sparse=6/h)
    day_samples = {}
    for s in inst.log.samples.values():
        if H6 <= s.taken_at < SUNSET:
            day_samples[s.node_id] = day_samples.get(s.node_id, 0) + 1
    total_sampled = sum(getattr(n, "sampled", 0) for n in inst.nodes.values())
    sv = r["survival"]
    n00 = sorted(hourly_profile(inst, "n00", H2, H20).items())
    return {
        "tau_h": None if tau is None else round(tau / 3600, 2),
        "svc": round(r["routine"]["delivered"] / r["routine"]["n"], 4),
        "dead": len(sv.get("dead", [])),
        "yellow_n": len(yel), "yellow_delivered": sum(1 for x in yel if x["delivered"]),
        "daywin_h6_12_delivered": sum(1 for x in daywin if x["delivered"]),
        "daywin_collected_not_delivered":
            sum(1 for x in daywin if x.get("collected") and not x["delivered"]),
        "day_dense_samples_total": sum(day_samples.values()),
        "day_dense_samples_per_node": {k: day_samples[k] for k in sorted(day_samples)},
        "total_sampled": total_sampled,
        "mean_final_soc": round(sv.get("mean_final_soc"), 4),
        "n00_hourly_h2_20": n00,
    }


def main():
    taus = [None] + [H5 + 1800 * k for k in range(int((H12 - H5) / 1800) + 1)]
    res = []
    for t in taus:
        z = evaluate(t)
        res.append(z)
        print(f"tau={str(z['tau_h']):>5} svc={z['svc']:.4f} dead={z['dead']:>2} "
              f"Ydel={z['yellow_delivered']}/{z['yellow_n']} "
              f"dayDel={z['daywin_h6_12_delivered']} dayCnd={z['daywin_collected_not_delivered']} "
              f"daySamples={z['day_dense_samples_total']} sampled={z['total_sampled']} "
              f"soc={z['mean_final_soc']}")
    print("\nn00 hourly sample counts (h2-h20) for night-floor (tau=None):")
    print(res[0]["n00_hourly_h2_20"])
    last_release = H6 - 300
    dl = yellow_deadline(last_release)
    tau_geo = math.ceil(dl / RATE) * RATE
    print(f"\ngeometric: last yellow release={last_release} deadline={dl} "
          f"backup-aligned tau*_geo={tau_geo} ({tau_geo/3600:.2f}h)")
    base_y = res[0]["yellow_delivered"]
    feasible = [z for z in res if z["tau_h"] is not None and z["yellow_delivered"] >= base_y
                and z["dead"] <= res[0]["dead"]]
    if feasible:
        best = min(feasible, key=lambda z: (z["day_dense_samples_total"], z["dead"]))
        print("best feasible tau:", best["tau_h"], "h; daySamples", best["day_dense_samples_total"],
              "vs night-floor", res[0]["day_dense_samples_total"],
              "; dead", best["dead"], "vs", res[0]["dead"],
              "; svc", best["svc"], "vs", res[0]["svc"])
    p = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "results", "r46_lease_sweep.json")
    json.dump({"schedule": SCHED, "outage_h": [4, 20], "sunset_h": 12, "tau_geo_s": tau_geo,
               "night_floor": res[0], "sweep": res[1:]},
              open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("saved", p, flush=True)


if __name__ == "__main__":
    main()
