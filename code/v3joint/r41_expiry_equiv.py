# -*- coding: utf-8 -*-
"""r41 (doc51 R5 / doc52 sec 2.2) — deadline_purge vs ordinary same-deadline expiration.

Zero LLM. Main operating point (maxcov backup), seeds 0-9. Compare node edge queues:
  fifo / deadline_purge / generic_expiry / latest_only,
where generic_expiry is the STANDARD per-record lifetime (BPv7-style creation-relative lifetime
ending at the business-useful deadline (floor(taken/P)+2)P; expire-and-release, keep unexpired,
FIFO among survivors) and references no obligation id, slot geometry, or certificate.

Test: deadline_purge must be BIT-IDENTICAL to generic_expiry with the same deadlines (same svc,
same outage on-time count, same deaths, same delivered-oid set). If it is, the node mechanism is
standard deadline expiration (an instantiation, not a new discard algorithm); the defensible
contribution is the cross-segment cost witness, the business-deadline basis, and the
source-local zero-downlink placement -- not a novel queue. Also reruns gateway-only suppression
(maxcov_ontime) to restate the cross-segment access back-pressure cost, and recomputes the
paired ten-seed CIs (purge-fifo, purge-latest).
"""
import os, sys, math, json
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from exogenous import KIND_ROUTINE
from joint_run import run_joint
import r37_conformance as r37

BASE = {k: v for k, v in r37.COMMON.items() if k != "seed"}
QS = ("fifo", "deadline_purge", "generic_expiry", "latest_only")
SEEDS = list(range(10))
T9 = 2.262
P_UP = 300  # post-hoc accounting period for yellow backup deadlines (not visible online)


def mean(xs):
    return sum(xs) / len(xs)


def sd(xs):
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def ci(diffs):
    m, s = mean(diffs), sd(diffs)
    h = T9 * s / math.sqrt(len(diffs))
    return m, s, m - h, m + h


def silent_metrics(r, inst, obligations):
    rows = {x["oid"]: x for x in r["rows"] if x["kind"] == "routine"}
    allr = [x for x in r["rows"] if x["kind"] == "routine" and not x.get("censored")]
    svc = sum(1 for x in allr if x["delivered"]) / len(allr)
    dead = len(r.get("survival", {}).get("dead", []))
    jobs = [o for o in obligations.obligations
            if o.kind == KIND_ROUTINE and o.release_at >= r37.H6 and o.deadline <= r37.OUT_HI
            and o.oid in rows and not rows[o.oid].get("censored")]
    d = sum(1 for o in jobs if rows[o.oid]["delivered"])
    on = late = 0
    for sid, sx in inst.log.samples.items():
        tr = inst.log.transit.get(sid)
        if tr is None or tr.received_at is None or not (r37.OUT_LO <= tr.received_at < r37.OUT_HI):
            continue
        dl = r37.deadline_of(sx.taken_at)
        if tr.received_at <= dl:
            on += 1
        else:
            late += 1
    dset = frozenset(x["oid"] for x in allr if x["delivered"])
    return dict(svc=svc, dead=dead, d=d, on=on, late=late, dset=dset)


def main():
    rows = {}
    for seed in SEEDS:
        for cs in QS:
            r, inst, obl = run_joint(seed=seed, backup_chooser="maxcov", cache_service=cs, **BASE)
            rows[(seed, cs)] = silent_metrics(r, inst, obl)
        print(f"seed{seed} done", flush=True)
    # gateway-only suppression cross-segment cost at seed0
    r, inst, obl = run_joint(seed=0, backup_chooser="maxcov_ontime", cache_service="fifo", **BASE)
    ontime0 = silent_metrics(r, inst, obl)

    print("\n== r41 expiry equivalence (maxcov, seeds 0-9) ==")
    hdr = f"{'queue':<16}{'svc mean':>10}{'svc sd':>8}{'outage d total':>15}{'bk on':>7}{'bk late':>7}{'dead':>6}"
    print(hdr)
    for cs in QS:
        sv = [rows[(s, cs)]['svc'] for s in SEEDS]
        dd = [rows[(s, cs)]['d'] for s in SEEDS]
        on = sum(rows[(s, cs)]['on'] for s in SEEDS)
        late = sum(rows[(s, cs)]['late'] for s in SEEDS)
        dead = sum(rows[(s, cs)]['dead'] for s in SEEDS)
        print(f"{cs:<16}{mean(sv):>10.4f}{sd(sv):>8.4f}{sum(dd):>15}{on:>7}{late:>7}{dead:>6}")

    print("\n== bit-identity: deadline_purge vs generic_expiry (per seed) ==")
    all_ident = True
    for s in SEEDS:
        a, b = rows[(s, 'deadline_purge')], rows[(s, 'generic_expiry')]
        ident = (abs(a['svc'] - b['svc']) < 1e-12 and a['d'] == b['d'] and a['dead'] == b['dead']
                 and a['on'] == b['on'] and a['late'] == b['late'] and a['dset'] == b['dset'])
        all_ident &= ident
        print(f"seed{s}: svc {a['svc']:.4f}={b['svc']:.4f} d {a['d']}={b['d']} dead {a['dead']}={b['dead']} "
              f"on {a['on']}={b['on']} late {a['late']}={b['late']} deliveredSetEqual={a['dset']==b['dset']} "
              f"-> {'IDENTICAL' if ident else 'DIFFER'}")
    print(f"BIT-IDENTICAL ON ALL 10 SEEDS: {all_ident}")

    print("\n== paired CIs ==")
    for cmp_name, base_cs in (("deadline_purge - fifo", "fifo"),
                              ("deadline_purge - latest_only", "latest_only")):
        dsvc = [rows[(s, 'deadline_purge')]['svc'] - rows[(s, base_cs)]['svc'] for s in SEEDS]
        m, s, lo, hi = ci(dsvc)
        per = ",".join(f"{x*100:+.1f}" for x in dsvc)
        print(f"{cmp_name}: mean {m*100:+.2f} pts, 95%CI [{lo*100:+.2f},{hi*100:+.2f}], "
              f"all+={all(x>0 for x in dsvc)}; per-seed {per}")

    print("\n== cross-segment cost of gateway-only suppression (seed0, fifo edge) ==")
    base0 = rows[(0, 'fifo')]
    print(f"maxcov(fifo):        svc={base0['svc']:.4f} outage_d={base0['d']} late_sends={base0['late']}")
    print(f"maxcov_ontime(fifo): svc={ontime0['svc']:.4f} outage_d={ontime0['d']} late_sends={ontime0['late']} "
          f"(suppressing expired BACKUP sends while node cache still holds them)")

    out = {"bit_identical_purge_generic_expiry": all_ident,
           "queues": {cs: {"svc_mean": mean([rows[(s, cs)]['svc'] for s in SEEDS]),
                           "svc_sd": sd([rows[(s, cs)]['svc'] for s in SEEDS]),
                           "outage_d_total": sum(rows[(s, cs)]['d'] for s in SEEDS),
                           "backup_on": sum(rows[(s, cs)]['on'] for s in SEEDS),
                           "backup_late": sum(rows[(s, cs)]['late'] for s in SEEDS),
                           "dead_total": sum(rows[(s, cs)]['dead'] for s in SEEDS)} for cs in QS},
           "per_seed": {f"{s}:{cs}": {k: (v if k != 'dset' else len(v)) for k, v in rows[(s, cs)].items()}
                        for s in SEEDS for cs in QS},
           "seed0_gateway_only_suppression": {k: v for k, v in ontime0.items() if k != 'dset'}}
    resdir = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "results")
    os.makedirs(resdir, exist_ok=True)
    outp = os.path.join(resdir, "r41_expiry_equiv.json")
    json.dump(out, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\nsaved", outp, flush=True)


if __name__ == "__main__":
    main()
