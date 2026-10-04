#!/usr/bin/env python3
from __future__ import annotations
from collections import deque
from dataclasses import asdict,dataclass
import json
from scenario_generator_v0_5 import build_bundle

class Flow:
    def __init__(self): self.c={}
    def edge(self,u,v,c=1):
        self.c.setdefault(u,{});self.c.setdefault(v,{})
        self.c[u][v]=self.c[u].get(v,0)+c;self.c[v].setdefault(u,0)
    def run(self,s,t):
        r={u:dict(vs) for u,vs in self.c.items()};tot=0
        while True:
            p={s:None};q=deque([s])
            while q and t not in p:
                u=q.popleft()
                for v,c in r[u].items():
                    if c>0 and v not in p:p[v]=u;q.append(v)
            if t not in p:break
            v=t
            while p[v] is not None:
                u=p[v];r[u][v]-=1;r[v][u]=r[v].get(u,0)+1;v=u
            tot+=1
        return tot

def physical(bundle,world):
    f=Flow();S='S';T='T';SB='SATB'
    sats=tuple(sorted(set(bundle.satellite_send_times)))
    for o in bundle.obligations:
        on='o:'+o.oid;f.edge(S,on)
        for d in world.delivery_events:
            if d.oid==o.oid and d.accepted and d.final_ack_at_s is not None and d.final_ack_at_s<=o.deadline_s:
                f.edge(on,'terr:'+str(d.send_at_s))
        for t in sats:
            if o.release_s<=t<=o.deadline_s:f.edge(on,'sat:'+str(t))
    terr_times=sorted({d.send_at_s for d in world.delivery_events if d.accepted})
    for t in terr_times:f.edge('terr:'+str(t),T)
    for t in sats:f.edge('sat:'+str(t),SB)
    f.edge(SB,T,bundle.satellite_budget)
    return f.run(S,T)==len(bundle.obligations)

def sig(bundle,world):
    return frozenset((d.oid,d.send_at_s) for d in world.delivery_events if d.accepted and d.final_ack_at_s is not None and d.final_ack_at_s<=next(o.deadline_s for o in bundle.obligations if o.oid==d.oid))

def audit(family):
    b=build_bundle(process_family=family)
    per={w.world_id:physical(b,w) for w in b.worlds}
    ss={w.world_id:sig(b,w) for w in b.worlds}
    worst=next((wid for wid,s in ss.items() if all(s<=x for x in ss.values())),None)
    return {'family':family,'per_world_physical':per,'all_worlds_physical':all(per.values()),'common_worst_world':worst,'satellite_windows':len(b.satellite_send_times),'satellite_budget':b.satellite_budget}

if __name__=='__main__':print(json.dumps([audit('independent-bits'),audit('shifted-window')],indent=2,sort_keys=True))
