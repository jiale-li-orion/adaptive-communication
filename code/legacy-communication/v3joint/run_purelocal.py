#!/usr/bin/env python3
"""run_purelocal.py — 干净的本地自治上界：节点本地预装昼夜能量底座 + 既有 local 策略，
无中心任务编译策略（不构造 AgentMissionPolicy/MissionChangePolicy）。"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from joint_run import run_joint
import r38_agent_three_arm as R

rows = []
for s in [0, 1, 2]:
    kw = dict(R.BASE); kw["seed"] = s
    r, _i, _o = run_joint(**kw, mission_schedule=R.UP,
                          local_floor=True, local_dayfeed=True)
    rr = r["routine"]; sv = r["survival"]; cc = r.get("command_counters", {})
    rows.append({"arm": "pure-local", "seed": s,
                 "svc": round(rr["delivered"]/rr["n"], 4),
                 "missColl": rr.get("missing_collection"),
                 "missDeliv": rr.get("missing_delivery"),
                 "dead": len(sv["dead"]), "mean_soc": round(sv["mean_final_soc"], 4),
                 "sent": cc.get("commands_sent"), "refused": cc.get("commands_refused")})
cols = ['arm', 'seed', 'svc', 'dead', 'mean_soc', 'missColl', 'missDeliv', 'sent', 'refused']
print('\t'.join(cols))
for r in rows:
    print('\t'.join(str(r.get(k)) for k in cols))
sv = [r['svc'] for r in rows]
print('pure-local mean svc=%.4f dead=%d range=%.3f..%.3f refused=%d'
      % (sum(sv)/3, sum(r['dead'] for r in rows), min(sv), max(sv),
         sum(r['refused'] for r in rows)))
json.dump(rows, open(os.path.join(R.TRACEDIR, "r39_purelocal.json"), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
