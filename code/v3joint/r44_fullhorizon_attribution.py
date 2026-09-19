# -*- coding: utf-8 -*-
"""r44 (doc53 follow-up) - full-horizon time-aware failure attribution.

v0.7 Table/frontier text still quoted the legacy r24 full-horizon split in which S_access = 0
because "heard" used heard_at with NO deadline cutoff (a sample heard at any later time cleared
the access segment). r40 introduced the time-aware test (heard BY the deadline) for the ka
upgrade subset; this script applies the SAME precise_truth test to EVERY routine obligation over
the full 48 h, and reports the legacy (heard-ever) split alongside, so the paper uses one
consistent time-aware definition. Reproduces the delivered total (3025) as a denominator check.
"""
import os, sys, json
from collections import Counter, defaultdict
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from joint_run import run_joint
import r37_conformance as r37
from r40_local_attribution import opt_slot

KIND_ROUTINE = "routine"


def main():
    r, inst, obligations = run_joint(backup_chooser="maxcov", cache_service="fifo", **r37.COMMON)
    rows = {x["oid"]: x for x in r["rows"]
            if x["kind"] == KIND_ROUTINE and not x.get("censored")}
    by_nm = defaultdict(list)
    for s in inst.log.samples.values():
        by_nm[(s.node_id, s.measurand)].append(s)
    for k in by_nm:
        by_nm[k].sort(key=lambda s: s.taken_at)
    heard_of = {sid: tr.heard_at for sid, tr in inst.log.transit.items()}
    recv_of = {sid: tr.received_at for sid, tr in inst.log.transit.items()}

    def matches(o, s):
        return s.node_id == o.node_id and s.measurand == o.measurand and o.matches(s)

    def delivered(o, ms):
        return any(recv_of.get(s.sample_id) is not None and recv_of[s.sample_id] <= o.deadline
                   for s in ms)

    def time_aware(o):
        ms = [s for s in by_nm.get((o.node_id, o.measurand), []) if matches(o, s)]
        if delivered(o, ms):
            return "delivered"
        if opt_slot(o, o.window[0]) is None:
            return "S_time"
        inwin = [s for s in ms if s.taken_at <= o.window[1] + o.tolerance_s]
        if not inwin:
            return "S_energy"
        s0 = min(inwin, key=lambda s: s.taken_at)
        hv = heard_of.get(s0.sample_id)
        rv = recv_of.get(s0.sample_id)
        if hv is None or hv > o.deadline:
            return "S_access"      # never heard, OR heard only after the deadline
        if rv is None or rv > o.deadline:
            return "S_cap"         # at the gateway in time, not returned by deadline
        return "delivered"

    def legacy_heard_ever(o):
        ms = [s for s in by_nm.get((o.node_id, o.measurand), []) if matches(o, s)]
        if delivered(o, ms):
            return "delivered"
        if opt_slot(o, o.window[0]) is None:
            return "S_time"
        inwin = [s for s in ms if s.taken_at <= o.window[1] + o.tolerance_s]
        if not inwin:
            return "S_energy"
        s0 = min(inwin, key=lambda s: s.taken_at)
        hv = heard_of.get(s0.sample_id)
        rv = recv_of.get(s0.sample_id)
        if hv is None:
            return "S_access"      # legacy: only NEVER-heard counts as access failure
        if rv is None or rv > o.deadline:
            return "S_cap"         # heard at ANY later time clears access -> capacity
        return "delivered"

    ta, leg = Counter(), Counter()
    moved = Counter()
    n = 0
    for o in obligations.obligations:
        if o.oid not in rows:
            continue
        n += 1
        a, b = time_aware(o), legacy_heard_ever(o)
        ta[a] += 1
        leg[b] += 1
        if a != b:
            moved[(b, a)] += 1

    def pct(c, key):
        return round(100.0 * c[key] / max(1, n - c["delivered"]), 1)

    print(f"== r44 full-horizon attribution over n={n} routine obligations ==")
    print("LEGACY (heard at any later time clears access):", dict(leg),
          {k: f"{pct(leg,k)}%" for k in ("S_time", "S_cap", "S_energy", "S_access")})
    print("TIME-AWARE (heard by deadline):              ", dict(ta),
          {k: f"{pct(ta,k)}%" for k in ("S_time", "S_cap", "S_energy", "S_access")})
    print("label moves legacy -> time-aware:", dict(moved))
    out = {"n": n, "legacy_heard_ever": dict(leg), "time_aware": dict(ta),
           "legacy_pct_of_misses": {k: pct(leg, k) for k in
                                    ("S_time", "S_cap", "S_energy", "S_access")},
           "time_aware_pct_of_misses": {k: pct(ta, k) for k in
                                        ("S_time", "S_cap", "S_energy", "S_access")},
           "label_moves_legacy_to_timeaware": {f"{k[0]}->{k[1]}": v for k, v in moved.items()}}
    resdir = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "results")
    p = os.path.join(resdir, "r44_fullhorizon_attribution.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("saved", p, flush=True)


if __name__ == "__main__":
    main()
