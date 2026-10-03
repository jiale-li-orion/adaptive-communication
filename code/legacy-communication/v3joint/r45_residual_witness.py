# -*- coding: utf-8 -*-
"""r45 - residual witness: a DAYTIME mission downgrade whose control command cannot arrive.

The v0.7 record-side fix (generic_expiry) and the node local clock night-floor are both standard
mechanisms. The open residual (doc52/doc53) is installed *config* state whose termination the
centre cannot reach during a control outage. The night-floor only acts at dusk (hod>=18); it is
blind to a daytime downgrade/release and to delivery opportunity. This script builds the cheapest
witness (no new mechanism, no LLM): yellow upgrade at h6 (control healthy, applies), then a
conferred downgrade back to sparse at h14 (daytime) that falls inside a control outage h12-h24.
It compares the ordinary centre policies with/without the clock floor, all on generic_expiry
(record side already optimal), and reports:
  * overall deadline-valid service and deaths;
  * obligations released in [h14,h24): collected-but-not-delivered (wasted dense work) vs delivered;
  * for a representative node, the time after the downgrade it is STILL running dense (iv=300),
    and its minimum SoC overnight (does the clock floor's 4 h daytime lag cost energy or kill it).
"""
import os, sys, json
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from joint_run import run_joint

H6, H14, H12, H24 = 6 * 3600, 14 * 3600, 12 * 3600, 24 * 3600
SCHED = [(0, 600, "blue"), (H6, 300, "yellow"), (H14, 600, "blue")]

BASE = dict(task_hours=48, tail_hours=1, arm="local", groups=2,
            sample_interval_s=600, report_period_s=600, routine_period_s=600,
            harvest_mode="solar", harvest_peak_wh_per_hour=0.03, capacity_wh=0.05,
            initial_soc=1.0, outage_start_h=12, outage_hours=12,
            enable_backup=True, backup_rate_s=1200, backup_bytes=78,
            backup_chooser="maxcov", cache_service="generic_expiry",
            mission_schedule=SCHED, collect_rows=True)

ARMS = [
    ("comply_nofloor", "comply", False),
    ("dayfeed_nofloor", "dayfeed", False),
    ("dayfeed_floor", "dayfeed", True),
    ("sustain_floor", "sustain", True),
]


def dense_dwell(inst, nid="n00"):
    """State samples for nid between downgrade h14 and h24: fraction still at dense iv=300, min SoC."""
    states = [(t, iv, rp, soc, alive) for (t, n, k, iv, rp, soc, alive)
              in inst.trace_events if k == "state" and n == nid and H14 <= t < H24]
    n = len(states)
    dense = sum(1 for (_t, iv, _rp, _s, _a) in states if iv == 300)
    minsoc = min((soc for (_t, _iv, _rp, soc, _a) in states), default=None)
    dead = any(not a for (_t, _iv, _rp, _s, a) in states)
    return {"n_state": n, "dense_states": dense,
            "dense_frac": round(dense / n, 3) if n else None,
            "min_soc_14_24": round(minsoc, 5) if minsoc is not None else None,
            "dead_in_window": dead}


def seg_counts(r):
    rows = [x for x in r["rows"] if x["kind"] == "routine" and not x["censored"]]
    win = [x for x in rows if H14 <= x["release_at"] < H24]
    up = [x for x in rows if H6 <= x["release_at"] < H14]
    def block(zs):
        d = sum(1 for x in zs if x["delivered"])
        coll = sum(1 for x in zs if x.get("collected") and not x["delivered"])
        return {"n": len(zs), "delivered": d, "collected_not_delivered": coll}
    allr = block(rows)
    return {"overall": allr, "upgrade_h6_14": block(up),
            "downgrade_window_h14_24": block(win)}


def main():
    out = {}
    for tag, mode, floor in ARMS:
        r, inst, _obs = run_joint(seed=0, mission_mode=mode, local_floor=floor, **BASE)
        sv = r["survival"]
        out[tag] = {
            "svc": round(r["routine"]["delivered"] / r["routine"]["n"], 4),
            "dead": len(sv.get("dead", [])),
            "mean_final_soc": sv.get("mean_final_soc"),
            "segments": seg_counts(r),
            "n00_dwell": dense_dwell(inst),
            "backup_packets": r["backup"]["backup_packets"],
            "backup_records": r["backup"]["backup_records"],
        }
        print(json.dumps({tag: out[tag]}, ensure_ascii=False, indent=2))
    p = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "results",
                     "r45_residual_witness.json")
    json.dump({"schedule": SCHED, "outage_h": [12, 24], "arms": out},
              open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("saved", p, flush=True)


if __name__ == "__main__":
    main()
