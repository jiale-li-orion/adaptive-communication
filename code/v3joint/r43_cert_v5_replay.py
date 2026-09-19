# -*- coding: utf-8 -*-
"""r43 (doc51 R3) — offline replay of v4 vs v5 feasibility certificates on the FINAL r38 traces.

Zero LLM. For every decision snapshot in the 11 final traces we recompute both the v4 certificate
(online_cert_block, which produced the r38 runs) and the v5 unknown-aware certificate
(online_cert_block_v5) on the SAME observation, with no network-side backhaul field (as in the
current harness, primary_backhaul_state absent -> None). We count:
  v4: definite CONTROL-PLANE-NOT-DELIVERING assertions; blanket "PERMANENTLY kills" night claims;
  v5: UNREACHABLE assertions (should be 0 without a network-side field), UNCONFIRMED labels,
      computed ENERGY-INFEASIBLE vs mere NIGHT ENERGY ADVISORY.
We inspect the five evidence-confirmed healthy-path false-alarm times in the no-forced-outage A1
trace (28800/41400/90000/104400/174600) and night/near-dawn decisions. This is a counterfactual
mechanism witness (certificate text on logged observations), not an end-to-end v5 agent run.
"""
import os, sys, json
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from agent_cert import online_cert_block, online_cert_block_v5
from r42_claim_relabel import FINAL, T

CTX = {"dense": 300, "sparse": 600, "capacity_wh": 0.05, "sample_wh": 4.7e-4}
OUT_LO, OUT_HI = 4 * 3600, 20 * 3600
HEALTHY_FALSE_ALARM = [28800, 41400, 90000, 104400, 174600]


def classify(txt):
    return {
        "v4_cp_assert": ("NOT DELIVERING" in txt),
        "v4_night_kill": ("PERMANENTLY kills" in txt),
        "v5_unreachable": ("command UNREACHABLE now" in txt),
        "v5_unconfirmed": ("command delivery UNCONFIRMED" in txt),
        "v5_energy_infeas": ("ENERGY-INFEASIBLE TO OPEN" in txt),
        "v5_energy_advisory": ("NIGHT ENERGY ADVISORY" in txt),
    }


def main():
    per = {}
    detail_healthy = []
    near_dawn = []
    for (tag, arm, seed), fn in sorted(FINAL.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
        recs = [json.loads(l) for l in open(os.path.join(T, fn), encoding="utf-8")]
        agg = dict(decisions=0, v4_cp_assert=0, v4_night_kill=0, v5_unreachable=0,
                   v5_unconfirmed=0, v5_energy_infeas=0, v5_energy_advisory=0,
                   v4_cp_in_forced_outage=0, dark=0)
        for rec in recs:
            obs = rec["observation"]
            t = rec["t_s"]; hod = obs.get("clock_hod", 12)
            dark = hod < 6 or hod >= 18
            v4 = online_cert_block(obs, CTX)
            v5 = online_cert_block_v5(obs, CTX)
            c4, c5 = classify(v4), classify(v5)
            agg["decisions"] += 1
            if dark:
                agg["dark"] += 1
            for k in ("v4_cp_assert", "v4_night_kill", "v5_unreachable", "v5_unconfirmed",
                      "v5_energy_infeas", "v5_energy_advisory"):
                agg[k] += int(c4[k] if k.startswith("v4") else c5[k])
            if c4["v4_cp_assert"] and tag == "outage" and OUT_LO <= t < OUT_HI:
                agg["v4_cp_in_forced_outage"] += 1
            if tag == "nolinkout" and arm == "A1" and t in HEALTHY_FALSE_ALARM:
                detail_healthy.append({
                    "t": t, "hod": hod,
                    "n_heard": obs["link"]["n_heard"],
                    "applied300": sum(1 for x in obs["nodes"]
                                      if str(x.get("id", "")).startswith("n") and x.get("cur_sample_s") == 300),
                    "v4_asserts_not_delivering": c4["v4_cp_assert"],
                    "v5_unreachable": c5["v5_unreachable"],
                    "v5_unconfirmed": c5["v5_unconfirmed"],
                    "v5_energy_infeas": c5["v5_energy_infeas"],
                    "v5_energy_advisory": c5["v5_energy_advisory"]})
            if dark and 4.5 <= hod < 6.0 and arm == "A1":
                socs = [x.get("soc_wh") for x in obs["nodes"] if x.get("soc_wh") is not None]
                near_dawn.append({"tag": tag, "seed": seed, "t": t, "hod": hod,
                                  "min_soc": min(socs) if socs else None,
                                  "v4_night_kill": c4["v4_night_kill"],
                                  "v5_energy_infeas": c5["v5_energy_infeas"],
                                  "v5_energy_advisory": c5["v5_energy_advisory"]})
        per[f"{tag}|{arm}|s{seed}"] = agg

    print("== r43 v4 vs v5 certificate replay on final traces ==")
    hdr = (f"{'trace':<20}{'dec':>4}{'dark':>5}{'v4cpAssert':>11}{'v4cp@forced':>11}"
           f"{'v4nightKill':>12}{'v5UNREACH':>10}{'v5UNCONF':>9}{'v5ENinfeas':>11}{'v5ADVICE':>9}")
    print(hdr)
    for k, a in per.items():
        print(f"{k:<20}{a['decisions']:>4}{a['dark']:>5}{a['v4_cp_assert']:>11}"
              f"{a['v4_cp_in_forced_outage']:>11}{a['v4_night_kill']:>12}{a['v5_unreachable']:>10}"
              f"{a['v5_unconfirmed']:>9}{a['v5_energy_infeas']:>11}{a['v5_energy_advisory']:>9}")

    print("\n== healthy-path (no forced outage) A1: five evidence times ==")
    for d in detail_healthy:
        print(" ", d)
    nfa = sum(1 for d in detail_healthy if d["v4_asserts_not_delivering"])
    n5 = sum(1 for d in detail_healthy if d["v5_unreachable"])
    print(f" v4 asserts NOT-DELIVERING at {nfa}/{len(detail_healthy)} evidence times; "
          f"v5 asserts UNREACHABLE at {n5}/{len(detail_healthy)} (must be 0 with no network field).")

    print("\n== near-dawn (hod 4.5-6) A1 night claims ==")
    for d in near_dawn[:12]:
        print(" ", d)

    # totals
    tot = {k: sum(a[k] for a in per.values()) for k in next(iter(per.values()))}
    print("\ntotals:", tot)

    resdir = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "results")
    outp = os.path.join(resdir, "r43_cert_v5_replay.json")
    json.dump({"per_trace": per, "healthy_false_alarm_times": detail_healthy,
               "near_dawn": near_dawn, "totals": tot},
              open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("saved", outp, flush=True)


if __name__ == "__main__":
    main()
