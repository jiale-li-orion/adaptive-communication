#!/usr/bin/env python3
"""Dynamic conditional feasibility frontier for the v0.5 process.

The frontier is rebuilt from the same public process model as the exact oracle.
Incremental updates may reuse certificates only when their dependencies remain
valid; a reference full rebuild is provided for prefix-by-prefix equivalence.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable

from dynamic_scenario_tree_v0_5 import Bundle,World


@dataclass(frozen=True)
class ConflictCertificate:
    world_ids: tuple[str,...]
    obligations: tuple[str,...]
    usable_terrestrial_times: tuple[int,...]
    required_backup: int
    valid_budget_min: int
    depends_on_time_from_s: int


@dataclass(frozen=True)
class FrontierSnapshot:
    active_world_ids: tuple[str,...]
    delivered: tuple[str,...]
    at_s: int
    satellite_budget: int
    certificates: tuple[ConflictCertificate,...]


class _Flow:
    def __init__(self): self.cap={}
    def edge(self,u,v,c=1):
        self.cap.setdefault(u,{});self.cap.setdefault(v,{})
        self.cap[u][v]=self.cap[u].get(v,0)+c;self.cap[v].setdefault(u,0)
    def run(self,s,t):
        r={u:dict(vs) for u,vs in self.cap.items()}; total=0
        while True:
            p={s:None};q=deque([s])
            while q and t not in p:
                u=q.popleft()
                for v,c in r.get(u,{}).items():
                    if c>0 and v not in p:p[v]=u;q.append(v)
            if t not in p:break
            v=t
            while p[v] is not None:
                u=p[v];r[u][v]-=1;r[v][u]=r[v].get(u,0)+1;v=u
            total+=1
        return total,r


def _accepted_times(world:World,oid:str,at_s:int,deadline:int) -> tuple[int,...]:
    return tuple(sorted({d.send_at_s for d in world.delivery_events if d.oid==oid and d.accepted and at_s<=d.send_at_s<=deadline}))


def _world_certificate(bundle:Bundle,world:World,*,delivered:set[str],at_s:int) -> tuple[ConflictCertificate,int]:
    obs=[o for o in bundle.obligations if o.oid not in delivered and o.deadline_s>=at_s]
    f=_Flow();src='S';sink='T';all_times=set()
    for o in obs:
        on='o:'+o.oid;f.edge(src,on)
        for t in _accepted_times(world,o.oid,at_s,o.deadline_s):
            all_times.add(t);f.edge(on,'t:'+str(t))
    for t in sorted(all_times):f.edge('t:'+str(t),sink)
    matched,res=f.run(src,sink)
    deficit=max(0,len(obs)-matched)
    if deficit==0:
        cert=ConflictCertificate((world.world_id,),(),tuple(sorted(all_times)),0,0,at_s)
        return cert,1
    starts=['o:'+o.oid for o in obs if res[src].get('o:'+o.oid,0)>0]
    seen=set(starts);q=deque(starts)
    while q:
        u=q.popleft()
        for v,c in res.get(u,{}).items():
            if c>0 and v not in seen and v not in {src,sink}:seen.add(v);q.append(v)
    U=tuple(sorted(x[2:] for x in seen if x.startswith('o:')))
    N=tuple(sorted(int(x[2:]) for x in seen if x.startswith('t:')))
    if not U:U=tuple(sorted(o.oid for o in obs))
    req=max(deficit,len(U)-len(N))
    cert=ConflictCertificate((world.world_id,),U,N,req,req,at_s)
    return cert,1


def rebuild_frontier(bundle:Bundle,*,active_world_ids:Iterable[str],delivered:Iterable[str],at_s:int,satellite_budget:int) -> tuple[FrontierSnapshot,int]:
    active=set(active_world_ids);done=set(delivered);rows=[];flows=0
    for w in bundle.worlds:
        if w.world_id not in active:continue
        c,n=_world_certificate(bundle,w,delivered=done,at_s=at_s);rows.append(c);flows+=n
    groups={}
    for c in rows:
        key=(c.obligations,c.usable_terrestrial_times,c.required_backup)
        groups.setdefault(key,[]).append(c)
    certs=[]
    for key,cs in sorted(groups.items(),key=lambda kv:repr(kv[0])):
        certs.append(ConflictCertificate(
            tuple(sorted(c.world_ids[0] for c in cs)),key[0],key[1],key[2],key[2],at_s
        ))
    return FrontierSnapshot(tuple(sorted(active)),tuple(sorted(done)),at_s,satellite_budget,tuple(certs)),flows


class DynamicFeasibilityFrontier:
    def __init__(self,bundle:Bundle):
        self.bundle=bundle;self.active=set(w.world_id for w in bundle.worlds);self.delivered=set()
        self.at_s=min(bundle.fixed_event_times);self.budget=bundle.satellite_budget
        self.snapshot_value,self.flow_solves=rebuild_frontier(bundle,active_world_ids=self.active,delivered=self.delivered,at_s=self.at_s,satellite_budget=self.budget)

    def snapshot(self):return self.snapshot_value

    def apply_query_observation(self,*,query_id:str,sampled_at_s:int,value:str) -> int:
        q=next(q for q in self.bundle.queries if q.query_id==query_id)
        self.active={w.world_id for w in self.bundle.worlds if w.world_id in self.active and w.owner_value(q.proposition,sampled_at_s)==value}
        # World filtering does not change per-world flow certificates; reuse and regroup.
        old=[c for c in self.snapshot_value.certificates if set(c.world_ids)&self.active]
        certs=[]
        for c in old:
            ids=tuple(sorted(set(c.world_ids)&self.active))
            if ids:certs.append(ConflictCertificate(ids,c.obligations,c.usable_terrestrial_times,c.required_backup,c.valid_budget_min,c.depends_on_time_from_s))
        self.snapshot_value=FrontierSnapshot(tuple(sorted(self.active)),tuple(sorted(self.delivered)),self.at_s,self.budget,tuple(certs))
        return 0

    def apply_final_ack(self,oid:str,*,at_s:int) -> int:
        self.at_s=at_s;self.delivered.add(oid)
        self.snapshot_value,n=rebuild_frontier(self.bundle,active_world_ids=self.active,delivered=self.delivered,at_s=self.at_s,satellite_budget=self.budget)
        self.flow_solves+=n;return n

    def apply_satellite_commit(self,oid:str,*,at_s:int) -> int:
        self.at_s=at_s;self.delivered.add(oid);self.budget-=1
        self.snapshot_value,n=rebuild_frontier(self.bundle,active_world_ids=self.active,delivered=self.delivered,at_s=self.at_s,satellite_budget=self.budget)
        self.flow_solves+=n;return n

    def advance_time(self,at_s:int) -> int:
        if at_s<self.at_s:raise ValueError('time reversal')
        # Rebuild only if crossing a future terrestrial opportunity represented in a certificate.
        crossed=any(self.at_s<=t<at_s for c in self.snapshot_value.certificates for t in c.usable_terrestrial_times)
        self.at_s=at_s
        if not crossed:
            s=self.snapshot_value;self.snapshot_value=FrontierSnapshot(s.active_world_ids,s.delivered,at_s,s.satellite_budget,s.certificates);return 0
        self.snapshot_value,n=rebuild_frontier(self.bundle,active_world_ids=self.active,delivered=self.delivered,at_s=self.at_s,satellite_budget=self.budget)
        self.flow_solves+=n;return n

    def reference_rebuild(self) -> tuple[FrontierSnapshot,int]:
        return rebuild_frontier(self.bundle,active_world_ids=self.active,delivered=self.delivered,at_s=self.at_s,satellite_budget=self.budget)
