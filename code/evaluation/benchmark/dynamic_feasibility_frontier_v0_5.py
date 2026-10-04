#!/usr/bin/env python3
"""Dynamic feasibility frontier for v0.5.

This object maintains conservative remaining-feasibility diagnostics.  A
certificate is NOT a complete success policy.  It contains:
- a safe lower bound on additional backup transmissions;
- remaining terrestrial/satellite opportunity dependencies;
- pending in-flight obligations that must not be double-counted;
- world support and invalidation boundaries.
Exact non-anticipative search remains the success authority.
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
    usable_satellite_times: tuple[int,...]
    pending_cover: tuple[str,...]
    required_backup_lower_bound: int
    optimistic_backup_feasible: bool
    depends_on_time_from_s: int


@dataclass(frozen=True)
class FrontierSnapshot:
    active_world_ids: tuple[str,...]
    delivered: tuple[str,...]
    violated: tuple[str,...]
    pending_cover: tuple[str,...]
    at_s: int
    satellite_budget: int
    certificates: tuple[ConflictCertificate,...]


class _Flow:
    def __init__(self): self.cap={}
    def edge(self,u,v,c=1):
        self.cap.setdefault(u,{});self.cap.setdefault(v,{})
        self.cap[u][v]=self.cap[u].get(v,0)+c;self.cap[v].setdefault(u,0)
    def run(self,s,t):
        r={u:dict(vs) for u,vs in self.cap.items()};total=0
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
    # A terrestrial opportunity is useful only when its FINAL ACK can meet the deadline.
    return tuple(sorted({
        d.send_at_s for d in world.delivery_events
        if d.oid==oid and d.accepted and d.final_ack_at_s is not None
        and at_s<=d.send_at_s and d.final_ack_at_s<=deadline
    }))


def _satellite_times(bundle:Bundle,oid:str,at_s:int,deadline:int) -> tuple[int,...]:
    return tuple(t for t in bundle.satellite_send_times if at_s<=t<=deadline)


def _world_certificate(bundle:Bundle,world:World,*,delivered:set[str],violated:set[str],pending_cover:set[str],at_s:int,satellite_budget:int) -> tuple[ConflictCertificate,int]:
    remaining=[o for o in bundle.obligations if o.oid not in delivered and o.oid not in pending_cover and o.oid not in violated and o.deadline_s>=at_s]
    src='S';sink='T';f=_Flow();all_times=set()
    for o in remaining:
        on='o:'+o.oid;f.edge(src,on)
        for t in _accepted_times(world,o.oid,at_s,o.deadline_s):
            all_times.add(t);f.edge(on,'t:'+str(t))
    for t in sorted(all_times):f.edge('t:'+str(t),sink)
    matched,res=f.run(src,sink)
    deficit=max(0,len(remaining)-matched)
    starts=['o:'+o.oid for o in remaining if res[src].get('o:'+o.oid,0)>0]
    seen=set(starts);q=deque(starts)
    while q:
        u=q.popleft()
        for v,c in res.get(u,{}).items():
            if c>0 and v not in seen and v not in {src,sink}:seen.add(v);q.append(v)
    U=tuple(sorted(x[2:] for x in seen if x.startswith('o:')))
    N=tuple(sorted(int(x[2:]) for x in seen if x.startswith('t:')))
    if deficit and not U:U=tuple(sorted(o.oid for o in remaining))
    lb=max(deficit,len(U)-len(N) if U else 0)

    # Backup feasibility is optimistic: each remaining report only needs some
    # compatible satellite opportunity, and total budget must cover the lower bound.
    sat=set()
    every_report_has_backup=True
    for o in remaining:
        times=_satellite_times(bundle,o.oid,at_s,o.deadline_s)
        sat.update(times)
        if not _accepted_times(world,o.oid,at_s,o.deadline_s) and not times:
            every_report_has_backup=False
    optimistic = (not violated) and every_report_has_backup and satellite_budget>=lb and len(sat)>=lb
    return ConflictCertificate(
        world_ids=(world.world_id,),obligations=U,
        usable_terrestrial_times=N,usable_satellite_times=tuple(sorted(sat)),
        pending_cover=tuple(sorted(pending_cover)),required_backup_lower_bound=lb,
        optimistic_backup_feasible=optimistic,depends_on_time_from_s=at_s,
    ),1


def rebuild_frontier(bundle:Bundle,*,active_world_ids:Iterable[str],delivered:Iterable[str],violated:Iterable[str]=(),pending_cover:Iterable[str]=(),at_s:int,satellite_budget:int) -> tuple[FrontierSnapshot,int]:
    active=set(active_world_ids);done=set(delivered);bad=set(violated);pending=set(pending_cover);rows=[];flows=0
    for w in bundle.worlds:
        if w.world_id not in active:continue
        c,n=_world_certificate(bundle,w,delivered=done,violated=bad,pending_cover=pending,at_s=at_s,satellite_budget=satellite_budget);rows.append(c);flows+=n
    groups={}
    for c in rows:
        key=(c.obligations,c.usable_terrestrial_times,c.usable_satellite_times,c.pending_cover,c.required_backup_lower_bound,c.optimistic_backup_feasible)
        groups.setdefault(key,[]).append(c)
    certs=[]
    for key,cs in sorted(groups.items(),key=lambda kv:repr(kv[0])):
        certs.append(ConflictCertificate(
            tuple(sorted(c.world_ids[0] for c in cs)),key[0],key[1],key[2],key[3],key[4],key[5],at_s
        ))
    return FrontierSnapshot(tuple(sorted(active)),tuple(sorted(done)),tuple(sorted(bad)),tuple(sorted(pending)),at_s,satellite_budget,tuple(certs)),flows


class DynamicFeasibilityFrontier:
    def __init__(self,bundle:Bundle):
        self.bundle=bundle;self.active=set(w.world_id for w in bundle.worlds);self.delivered=set();self.violated=set();self.pending_cover=set()
        self.at_s=min(bundle.fixed_event_times);self.budget=bundle.satellite_budget
        self.snapshot_value,self.flow_solves=self._rebuild()

    def _rebuild(self):
        return rebuild_frontier(self.bundle,active_world_ids=self.active,delivered=self.delivered,violated=self.violated,pending_cover=self.pending_cover,at_s=self.at_s,satellite_budget=self.budget)
    def snapshot(self):return self.snapshot_value

    def apply_query_observation(self,*,query_id:str,sampled_at_s:int,arrival_at_s:int,value:str) -> int:
        if arrival_at_s < sampled_at_s or arrival_at_s < self.at_s: raise ValueError('invalid query timing')
        q=next(q for q in self.bundle.queries if q.query_id==query_id)
        self.at_s=arrival_at_s
        if value=='__TIMEOUT__':
            self.active={w.world_id for w in self.bundle.worlds if w.world_id in self.active and not w.query_reachable(sampled_at_s)}
        else:
            self.active={w.world_id for w in self.bundle.worlds if w.world_id in self.active and w.query_reachable(sampled_at_s) and w.owner_value(q.proposition,sampled_at_s)==value}
        if not self.active: raise ValueError('query observation incompatible with active worlds')
        self.snapshot_value,n=self._rebuild();self.flow_solves+=n;return n

    def apply_gateway_receipt(self,oid:str,*,at_s:int) -> int:
        if at_s<self.at_s:raise ValueError('time reversal')
        self.at_s=at_s;self.pending_cover.add(oid)
        self.snapshot_value,n=self._rebuild();self.flow_solves+=n;return n

    def apply_final_ack(self,oid:str,*,at_s:int) -> int:
        if at_s<self.at_s:raise ValueError('time reversal')
        self.at_s=at_s;self.pending_cover.discard(oid)
        deadline=next(o.deadline_s for o in self.bundle.obligations if o.oid==oid)
        if at_s<=deadline:self.delivered.add(oid)
        else:self.violated.add(oid)
        self.snapshot_value,n=self._rebuild();self.flow_solves+=n;return n

    def apply_satellite_commit(self,oid:str,*,at_s:int) -> int:
        if at_s<self.at_s or self.budget<=0:raise ValueError('invalid satellite commit')
        self.at_s=at_s;self.budget-=1
        deadline=next(o.deadline_s for o in self.bundle.obligations if o.oid==oid)
        if at_s<=deadline:self.delivered.add(oid)
        else:self.violated.add(oid)
        self.snapshot_value,n=self._rebuild();self.flow_solves+=n;return n

    def advance_time(self,at_s:int) -> int:
        if at_s<self.at_s:raise ValueError('time reversal')
        # Safe invalidation: any crossed release/deadline/terrestrial/satellite opportunity may create a new tight set.
        relevant=set(self.bundle.terrestrial_send_times)|set(self.bundle.satellite_send_times)
        relevant.update(o.release_s for o in self.bundle.obligations);relevant.update(o.deadline_s for o in self.bundle.obligations)
        crossed=any(self.at_s < t <= at_s for t in relevant)
        self.at_s=at_s
        if not crossed:
            s=self.snapshot_value;self.snapshot_value=FrontierSnapshot(s.active_world_ids,s.delivered,s.violated,s.pending_cover,at_s,s.satellite_budget,s.certificates);return 0
        self.snapshot_value,n=self._rebuild();self.flow_solves+=n;return n

    def reference_rebuild(self) -> tuple[FrontierSnapshot,int]:
        return self._rebuild()
