#!/usr/bin/env python3
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r39_envelope as E
from agent_mission import ScriptedDecider

rows = []
for s in [0, 1, 2]:
    rows.append(E.run_policy(s, ScriptedDecider("comply"), "local-full", floor=True, dayfeed=True))
cols = ['arm', 'seed', 'svc', 'dead', 'mean_soc', 'missColl', 'missDeliv', 'sent', 'refused']
print('\t'.join(cols))
for r in rows:
    print('\t'.join(str(r.get(k)) for k in cols))
sv = [r['svc'] for r in rows]
print('local-full mean svc=%.4f dead=%d range=%.3f..%.3f'
      % (sum(sv)/3, sum(r['dead'] for r in rows), min(sv), max(sv)))
out = os.path.join(E.R.TRACEDIR, "r39_localfull.json")
json.dump(rows, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('saved', out)
