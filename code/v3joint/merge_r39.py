#!/usr/bin/env python3
"""merge_r39.py — 合并 r39 三组结果为一张总表，输出 JSON 并打印 LaTeX/Markdown 友好表。"""
import os, sys, json, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r38_agent_three_arm as R

base = json.load(open(os.path.join(R.TRACEDIR, "r39_envelope_summary.json"), encoding="utf-8"))
lf = json.load(open(os.path.join(R.TRACEDIR, "r39_localfull.json"), encoding="utf-8"))
pl = json.load(open(os.path.join(R.TRACEDIR, "r39_purelocal.json"), encoding="utf-8"))
rows = base + lf + pl

order = ["pure-local", "local-dayfeed", "comply", "dayfeed-c", "env-comply",
         "comply+floor", "dayfeed-c+floor", "env-comply+floor", "local-full", "env-dayfeed"]
arms = [a for a in order if any(r["arm"] == a for r in rows)]

def agg(a):
    rs = [r for r in rows if r["arm"] == a]
    sv = [r["svc"] for r in rs]
    ref = sum(r["refused"] for r in rs if r.get("refused") is not None)
    sent = sum(r["sent"] for r in rs if r.get("sent") is not None)
    return dict(arm=a, svc_mean=round(statistics.mean(sv), 4),
                svc_min=round(min(sv), 4), svc_max=round(max(sv), 4),
                dead_total=sum(r["dead"] for r in rs),
                refused_total=ref, sent_total=sent,
                missColl_mean=round(statistics.mean([r["missColl"] for r in rs]), 1),
                missDeliv_mean=round(statistics.mean([r["missDeliv"] for r in rs]), 1),
                soc_mean=round(statistics.mean([r["mean_soc"] for r in rs]), 4))

table = [agg(a) for a in arms]
json.dump({"per_run": rows, "aggregate": table},
          open(os.path.join(R.TRACEDIR, "r39_table.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

print("arm\tsvc_mean\tsvc_range\tdead\trefused(3seed)\tsent(3seed)\tmissColl\tmissDeliv\tsoc")
for t in table:
    print("%s\t%.4f\t%.3f-%.3f\t%d\t%d\t%d\t%.0f\t%.0f\t%.3f" % (
        t["arm"], t["svc_mean"], t["svc_min"], t["svc_max"], t["dead_total"],
        t["refused_total"], t["sent_total"], t["missColl_mean"], t["missDeliv_mean"], t["soc_mean"]))
print("\nsaved r39_table.json")
