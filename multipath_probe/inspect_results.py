import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "results", "probe_results.json")))
print(f"{'K':>2} {'burst':>8} {'arm':>9} | {'E%':>6} {'R%':>6} {'wasted':>7} {'satW':>5} {'money':>6} {'energy':>8}")
for c in d["cells"]:
    for a, m in c["arms"].items():
        print(f"{c['K']:>2} {c['burst']:>8} {a:>9} | "
              f"{m['event_rate_mean']*100:6.1f} {m['routine_rate_mean']*100:6.1f} "
              f"{m['wasted_bad_path_mean']:7.1f} {m['sat_quota_wasted_mean']:5.1f} "
              f"{m['money_mean']:6.1f} {m['energy_mean']:8.1f}")
    print("-" * 70)
