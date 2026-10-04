#!/usr/bin/env python3
"""Minimal deterministic alias-bundle generator for Layer-1 v0.2."""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json
from scenario_tree_oracle import Bundle,Obligation,World,solve,hindsight,winning_first_actions_single_world

ROOT=Path(__file__).resolve().parents[3]
TRACE=ROOT/'research/benchmark/traces/v0.1/CONNECTA_20260922_SIHUI_GEOMETRY_48H.json'

def _h(x):
    return sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:16]

def _sat_slots():
    d=json.loads(TRACE.read_text())
    start=d['start_utc']
    from datetime import datetime
    t0=datetime.fromisoformat(start)
    slots=[]
    for w in d['thresholds']['20']['windows_utc']:
        a=int((datetime.fromisoformat(w['start'])-t0).total_seconds())
        slots.append(a)
    return sorted(set(slots))

def generate():
    sats=_sat_slots()
    out=[]
    # Grade-3 orange permits a 2-4 h reporting cadence. Use the 2 h source
    # boundary so two consecutive obligations fit inside the 48 h trace.
    post_interval=2*3600
    for i,s0 in enumerate(sats[:-1]):
        start=s0-300
        if start<0:
            continue
        release0=start
        deadline0=release0+post_interval
        release1=deadline0
        deadline1=release1+post_interval
        # Need a later real satellite opportunity only for the second report.
        later=[s for s in sats[i+1:] if release1 <= s <= deadline1]
        if not later:
            continue
        s1=later[0]

        early_terr=s0+600
        late_terr=release1+600
        if not (s0 < early_terr < deadline0 < late_terr <= deadline1):
            continue

        obligations=(
            Obligation('report_0',release0,deadline0),
            Obligation('report_1',release1,deadline1),
        )
        grid=tuple(sorted(set([
            start,s0,early_terr,deadline0,release1,late_terr,s1,deadline1
        ])))
        base_public=(
            ('warning','orange'),
            ('report_period_s',str(post_interval)),
            ('gateway_health','stale'),
            ('sat_budget','1'),
        )
        # Crossed worlds:
        # early: report_0 can use terrestrial; report_1 needs late satellite.
        # late: report_0 needs early satellite; report_1 can use terrestrial.
        worlds=(
            World('w_early','EARLY_WINDOW',(early_terr,), 'recent-forward',
                  passive_evidence_at_s=s0+1200, passive_value='recent-forward'),
            World('w_late','LATE_WINDOW',(late_terr,), 'stale-backlog',
                  passive_evidence_at_s=s0+1200, passive_value='stale-backlog'),
        )
        coords={'s0':s0,'s1':s1,'early_terr':early_terr,'late_terr':late_terr,'post_interval':post_interval}

        required=Bundle(
            'v02-'+_h({**coords,'kind':'query_required'}),
            grid,obligations,(s0,s1),worlds,1,True,120,base_public
        )
        h=hindsight(required)
        q=solve(required,allow_query=True)
        nq=solve(required,allow_query=False)
        first={w.world_id:sorted(winning_first_actions_single_world(required,w.world_id)) for w in worlds}
        direct_intersection=set(first['w_early']) & set(first['w_late'])
        out.append({
            'kind':'QUERY_REQUIRED','bundle':required,'hindsight':h,
            'query':q,'no_query':nq,'first_actions':first,
            'direct_intersection':sorted(direct_intersection),
        })

        # Query-harmful control: both worlds need report_0 on the early satellite;
        # the 10-minute query misses that slot, while report_1 has a common late terrestrial slot.
        common_late=(late_terr,)
        harmful_worlds=(
            World('w_h1','COMMON_LATE',common_late,'diag-a'),
            World('w_h2','COMMON_LATE',common_late,'diag-b'),
        )
        harmful=Bundle(
            'v02-'+_h({**coords,'kind':'query_harmful'}),
            grid,obligations,(s0,s1),harmful_worlds,1,True,600,base_public
        )
        out.append({
            'kind':'QUERY_HARMFUL','bundle':harmful,
            'hindsight':hindsight(harmful),
            'query':solve(harmful,allow_query=True),
            'no_query':solve(harmful,allow_query=False),
            'first_actions':{},'direct_intersection':[],
        })

        # Passive-better control: free telemetry distinguishes worlds one minute
        # before the early satellite; paid query is slower than waiting for it.
        passive_worlds=(
            World('w_p1','EARLY_WINDOW',(early_terr,), 'recent-forward',
                  passive_evidence_at_s=s0-60, passive_value='recent-forward'),
            World('w_p2','LATE_WINDOW',(late_terr,), 'stale-backlog',
                  passive_evidence_at_s=s0-60, passive_value='stale-backlog'),
        )
        passive_grid=tuple(sorted(set(grid+(s0-60,))))
        passive=Bundle(
            'v02-'+_h({**coords,'kind':'passive_better'}),
            passive_grid,obligations,(s0,s1),passive_worlds,1,True,600,base_public
        )
        out.append({
            'kind':'PASSIVE_BETTER','bundle':passive,
            'hindsight':hindsight(passive),
            'query':solve(passive,allow_query=True),
            'no_query':solve(passive,allow_query=False),
            'first_actions':{},'direct_intersection':[],
        })
        if len(out)>=90:
            break
    return out

def summarize(rows):
    from collections import Counter
    c=Counter()
    for r in rows:
        if all(r['hindsight'].values()): c['all_worlds_hindsight_solvable']+=1
        if r['query']['solvable']: c['obs_query_solvable']+=1
        if r['no_query']['solvable']: c['no_query_solvable']+=1
        if r['kind']=='QUERY_REQUIRED' and r['query']['solvable'] and not r['no_query']['solvable'] and not r['direct_intersection']:
            c['h2_positive']+=1
        c['kind_'+r['kind']]+=1
    c['total']=len(rows)
    return dict(c)

if __name__=='__main__':
    rows=generate()
    print(json.dumps(summarize(rows),indent=2,sort_keys=True))
