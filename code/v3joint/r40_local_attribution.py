# -*- coding: utf-8 -*-
"""r40 (doc51 R4 / doc52 sec 2.1) — arrival-time attribution under LOCAL visibility only.

r32's "100% segment attribution when the mission table reaches the gateway" used simulator-wide
samples (inst.log.samples, including samples the node took but never reported) and an untruncated
heard test (heard_any: heard_at is not None, with no heard_at <= arrival cutoff). That is an
OFFLINE global diagnostic, not attribution from the gateway's legal local evidence, and it
violates the original G5 constraint: with no report, "not sampled" (S_energy) and "sampled but
not delivered to the gateway" (S_access) are indistinguishable and must remain unknown.

This script recomputes attribution for the obligations already past deadline when the yellow
mission table reaches the gateway (ka), three ways:
  * precise ground truth (simulator-wide, TIME-AWARE): earliest matching sample's taken/heard/
    received vs the window and deadline -> one of delivered/S_time/S_access/S_cap/S_energy;
  * OFFLINE retrospective attribution using all simulator evidence (should match truth, 100%);
  * ONLINE arrival-time attribution using ONLY evidence the gateway legally holds at ka
    (heard_at <= ka, received_at <= ka): geometric S_time needs no sample; a sample heard by the
    deadline but not returned is S_cap; a sample heard in (deadline, ka] is late access S_access;
    anything with no sample heard by ka is UNKNOWN (S_energy vs S_access not separable).
It reports online coverage, accuracy of the online-labelled subset against truth, the truth
composition of UNKNOWN, and witnesses for samples heard after ka (427) / after deadline (650).
Zero LLM, deterministic, seed 0 main operating point.
"""
import os, sys, math, json
from collections import defaultdict, Counter
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from exogenous import KIND_ROUTINE
from joint_run import run_joint
import r37_conformance as r37


def opt_slot(o, ready):
    """Same optimistic earliest-return test as r32/r33: primary tick or in-outage r1200 slot."""
    tt = ready
    while tt <= o.deadline:
        h = tt // 3600 * 3600
        if not (r37.OUT_LO <= tt < r37.OUT_HI):
            return ("primary", tt)
        c = math.ceil(tt / r37.RATE) * r37.RATE
        if c <= o.deadline and r37.OUT_LO <= c < r37.OUT_HI:
            return ("backup", c)
        tt = h + 3600
    return None


def main():
    r, inst, obligations = run_joint(backup_chooser="maxcov", cache_service="fifo", **r37.COMMON)
    seg_gw = {s["level"]: s["gateway_received_at"] for s in r.get("mission_timing", [])}
    ka = seg_gw.get("yellow", 0)
    rows = {x["oid"]: x for x in r["rows"] if x["kind"] == "routine"}

    by_nm = defaultdict(list)
    for s in inst.log.samples.values():
        by_nm[(s.node_id, s.measurand)].append(s)
    for k in by_nm:
        by_nm[k].sort(key=lambda s: s.taken_at)
    heard_of = {sid: tr.heard_at for sid, tr in inst.log.transit.items()}
    recv_of = {sid: tr.received_at for sid, tr in inst.log.transit.items()}

    def matches(o, s):
        return s.node_id == o.node_id and s.measurand == o.measurand and o.matches(s)

    def precise_truth(o):
        """Time-aware simulator-wide ground-truth first-failing segment."""
        ms = [s for s in by_nm.get((o.node_id, o.measurand), []) if matches(o, s)]
        if any(recv_of.get(s.sample_id) is not None and recv_of[s.sample_id] <= o.deadline
               for s in ms):
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
            return "S_access"                      # sampled, never reached gateway
        if hv > o.deadline:
            return "S_access"                      # reached gateway too late
        if rv is None or rv > o.deadline:
            return "S_cap"                         # at gateway in time, not returned by deadline
        return "delivered"

    def offline_retro(o):
        """r32-style retrospective using ALL simulator evidence at ka (global, time-aware)."""
        ms = [s for s in by_nm.get((o.node_id, o.measurand), [])
              if s.taken_at <= ka and matches(o, s)]
        if any(recv_of.get(s.sample_id) is not None and recv_of[s.sample_id] <= o.deadline
               for s in ms):
            return "delivered"
        if opt_slot(o, o.window[0]) is None:
            return "S_time"
        heard = [s for s in ms if heard_of.get(s.sample_id) is not None]
        if not heard:
            return "S_energy"                      # global truth: node has no heard sample
        s0 = min(heard, key=lambda s: heard_of[s.sample_id])
        if heard_of[s0.sample_id] <= o.deadline:
            return "S_cap"
        return "S_access"                         # global truth sees the late arrival

    def online_at_ka(o):
        """Gateway-local attribution at ka: only heard_at<=ka / received_at<=ka, else UNKNOWN."""
        ms = [s for s in by_nm.get((o.node_id, o.measurand), [])
              if s.taken_at <= ka and matches(o, s)]
        if any(recv_of.get(s.sample_id) is not None and recv_of[s.sample_id] <= o.deadline
               and recv_of[s.sample_id] <= ka for s in ms):
            return "delivered"
        if opt_slot(o, o.window[0]) is None:
            return "S_time"                        # public geometry, no sample needed
        vis = [s for s in ms
               if heard_of.get(s.sample_id) is not None and heard_of[s.sample_id] <= ka]
        if not vis:
            return "unknown"                      # G5: not-sampled vs not-delivered inseparable
        s0 = min(vis, key=lambda s: heard_of[s.sample_id])
        hv = heard_of[s0.sample_id]
        if hv <= o.deadline:
            rv = recv_of.get(s0.sample_id)
            if rv is None or rv > o.deadline:
                return "S_cap"                    # gateway held it in time, did not return it
            return "delivered"
        return "S_access"                         # gateway can prove it arrived after deadline

    # obligations already past deadline when the table reaches the gateway
    jobs = [o for o in obligations.obligations
            if o.kind == KIND_ROUTINE and o.release_at >= r37.H6 and o.deadline <= ka
            and o.oid in rows and not rows[o.oid].get("censored")]
    truth, off, onl = {}, {}, {}
    heard_after_ka = heard_after_dl = 0
    examples_ka, examples_dl = [], []
    for o in jobs:
        t = precise_truth(o)
        truth[o.oid] = t
        if t == "delivered":
            continue
        off[o.oid] = offline_retro(o)
        onl[o.oid] = online_at_ka(o)
        ms = [s for s in by_nm.get((o.node_id, o.measurand), []) if matches(o, s)]
        late_ka = [s for s in ms if heard_of.get(s.sample_id) is not None
                   and heard_of[s.sample_id] > ka and s.taken_at <= ka]
        late_dl = [s for s in ms if heard_of.get(s.sample_id) is not None
                   and heard_of[s.sample_id] > o.deadline and s.taken_at <= o.deadline]
        if late_ka:
            heard_after_ka += 1
            if len(examples_ka) < 5:
                s = late_ka[0]
                examples_ka.append((o.oid, s.sample_id, s.taken_at, heard_of[s.sample_id]))
        if late_dl:
            heard_after_dl += 1
            if len(examples_dl) < 5:
                s = late_dl[0]
                examples_dl.append((o.oid, s.sample_id, s.taken_at, heard_of[s.sample_id]))

    n = len([oid for oid, t in truth.items() if t != "delivered"])
    print(f"== r40 local-visibility arrival attribution (ka={ka}s, past-deadline upgrade obligations n={n}) ==")
    print("precise truth segments:", dict(Counter(t for t in truth.values() if t != "delivered")))

    off_correct = sum(1 for oid, seg in off.items() if seg == truth[oid])
    print(f"\n[OFFLINE global retrospective] labelled {len(off)}, correct vs truth {off_correct} "
          f"({off_correct/len(off):.4f}); segments {dict(Counter(off.values()))}")

    onl_counter = Counter(onl.values())
    labelled = {oid: seg for oid, seg in onl.items() if seg != "unknown"}
    lab_correct = sum(1 for oid, seg in labelled.items() if seg == truth[oid])
    print(f"[ONLINE gateway-local at ka] segments {dict(onl_counter)}")
    print(f"  coverage (a segment other than unknown) = {len(labelled)}/{n} = {len(labelled)/n:.4f}")
    print(f"  unknown = {onl_counter['unknown']} ({onl_counter['unknown']/n:.4f})")
    print(f"  accuracy of online-labelled subset vs truth = {lab_correct}/{len(labelled)} = "
          f"{lab_correct/max(1,len(labelled)):.4f}")
    # confusion of online labels
    conf = Counter((seg, truth[oid]) for oid, seg in labelled.items())
    print("  online-vs-truth confusion (online->truth):",
          {f"{a}->{b}": k for (a, b), k in sorted(conf.items())})
    unk_truth = Counter(truth[oid] for oid, seg in onl.items() if seg == "unknown")
    print("  truth composition of online-UNKNOWN:", dict(unk_truth))

    print(f"\n[visibility violations in r32-style logic] obligations with a matching sample heard "
          f"AFTER ka={ka}: {heard_after_ka}; heard AFTER their deadline (taken<=deadline): {heard_after_dl}")
    print("  examples heard>ka (oid, sample, taken, heard):")
    for e in examples_ka:
        print("   ", e)
    print("  examples heard>deadline (oid, sample, taken, heard):")
    for e in examples_dl:
        print("   ", e)

    out = {"ka_s": ka, "n_past_deadline": n,
           "truth_segments": dict(Counter(t for t in truth.values() if t != "delivered")),
           "offline": {"labelled": len(off), "correct": off_correct,
                       "accuracy": off_correct / len(off), "segments": dict(Counter(off.values()))},
           "online": {"segments": dict(onl_counter), "coverage": len(labelled) / n,
                      "unknown": onl_counter["unknown"], "unknown_frac": onl_counter["unknown"] / n,
                      "labelled_correct": lab_correct,
                      "labelled_accuracy": lab_correct / max(1, len(labelled)),
                      "confusion": {f"{a}->{b}": k for (a, b), k in conf.items()},
                      "unknown_truth_composition": dict(unk_truth)},
           "obligations_with_sample_heard_after_ka": heard_after_ka,
           "obligations_with_sample_heard_after_deadline": heard_after_dl,
           "examples_heard_after_ka": examples_ka, "examples_heard_after_deadline": examples_dl}
    resdir = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "results")
    os.makedirs(resdir, exist_ok=True)
    outp = os.path.join(resdir, "r40_local_attribution.json")
    json.dump(out, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
    print("\nsaved", outp, flush=True)


if __name__ == "__main__":
    main()
