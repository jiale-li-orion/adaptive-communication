"""Read-only seed-0 attribution audit; no API calls or result-file mutation.

Run: python3 docs/s8-report/review-v0.7/attribution_probe.py
"""
import sys,json,pickle
from pathlib import Path
from collections import Counter,defaultdict
root=Path(__file__).resolve().parents[3]
for d in ('v3joint','instance','physics','runtime','experiments','analysis','monitoring'):
    sys.path.insert(0,str(root/'code'/d))
from joint_run import run_joint
import r37_conformance as r37
from r40_local_attribution import opt_slot
r,inst,obls=run_joint(backup_chooser='maxcov',cache_service='fifo',**r37.COMMON)
rows={v['oid']:v for v in r['rows'] if v['kind']=='routine' and not v.get('censored')}
by_nm=defaultdict(list)
for s in inst.log.samples.values():by_nm[(s.node_id,s.measurand)].append(s)
full=Counter();subset=Counter();gw=Counter();no_slot_after_access=[];multi_order=[]
for o in obls.obligations:
    if o.oid not in rows:continue
    ms=[s for s in by_nm[(o.node_id,o.measurand)] if o.matches(s)]
    def heard(s):return inst.log.transit[s.sample_id].heard_at
    if rows[o.oid]['delivered']:seg='delivered'
    elif opt_slot(o,o.window[0]) is None:seg='S_time'
    elif not ms:seg='S_collection'
    elif not any(heard(s) is not None and heard(s)<=o.deadline for s in ms):seg='S_access'
    else:
        seg='S_return'
        first=min(heard(s) for s in ms if heard(s) is not None)
        if opt_slot(o,first) is None:no_slot_after_access.append((o.oid,first,o.deadline))
    full[seg]+=1
    if o.release_at>=r37.H6 and o.deadline<=r37.OUT_HI and seg!='delivered':
        subset[seg]+=1
        vis=[s for s in ms if heard(s) is not None and heard(s)<=r37.OUT_HI]
        if opt_slot(o,o.window[0]) is None:label='S_time'
        elif not vis:label='unknown'
        elif min(heard(s) for s in vis)<=o.deadline:label='S_return'
        else:label='S_access'
        gw[label]+=1
out={'full_horizon':dict(full),'missed_upgrade_subset':dict(subset),'gateway_visible_subset':dict(gw),'return_cases_with_no_slot_after_actual_hearing':len(no_slot_after_access),'examples_no_slot_after_hearing':no_slot_after_access[:5]}
print(json.dumps(out,indent=2))
