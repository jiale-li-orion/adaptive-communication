#!/usr/bin/env python3
"""Conditional feasibility frontier for Layer-1 dynamic communication planning.

This is the first implementation of the cache06/Astra method contract:
- derive set-valued terrestrial deficiency witnesses with max-flow/min-cut;
- attach resource-validity domains to reusable certificates;
- preserve certificates while the current state remains inside their domain;
- invalidate only certificates whose dependencies or resource domain changed.

The frontier is a deterministic planning object. It does not assign rewards,
learn relevance scores, or delete unresolved actions heuristically.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable

from multi_evidence_scenario_tree import Bundle, Obligation, World


@dataclass(frozen=True)
class SetConflictWitness:
    world_id: str
    obligations: tuple[str, ...]
    terrestrial_neighbors: tuple[int, ...]
    terrestrial_capacity: int
    required_backup: int


@dataclass(frozen=True)
class FrontierCertificate:
    certificate_id: str
    world_ids: tuple[str, ...]
    conflict_witnesses: tuple[SetConflictWitness, ...]
    min_satellite_budget: int
    valid_budget_min: int
    valid_budget_max: int | None
    evidence_dependencies: tuple[str, ...]
    execution_dependencies: tuple[str, ...]

    def valid_for_budget(self, budget: int) -> bool:
        if budget < self.valid_budget_min:
            return False
        if self.valid_budget_max is not None and budget > self.valid_budget_max:
            return False
        return True


@dataclass(frozen=True)
class FrontierUpdate:
    kept_certificate_ids: tuple[str, ...]
    invalidated_certificate_ids: tuple[str, ...]
    rebuilt_certificate_ids: tuple[str, ...]
    active_world_ids: tuple[str, ...]


class _ResidualFlow:
    def __init__(self) -> None:
        self.cap: dict[str, dict[str, int]] = {}

    def add_edge(self, u: str, v: str, c: int) -> None:
        self.cap.setdefault(u, {})
        self.cap.setdefault(v, {})
        self.cap[u][v] = self.cap[u].get(v, 0) + int(c)
        self.cap[v].setdefault(u, 0)

    def solve(self, source: str, sink: str) -> tuple[int, dict[str, dict[str, int]]]:
        residual={u:dict(vs) for u,vs in self.cap.items()}
        total=0
        while True:
            parent: dict[str,str|None]={source:None}
            q=deque([source])
            while q and sink not in parent:
                u=q.popleft()
                for v,c in residual.get(u,{}).items():
                    if c>0 and v not in parent:
                        parent[v]=u
                        q.append(v)
            if sink not in parent:
                break
            aug=10**9
            v=sink
            while parent[v] is not None:
                u=parent[v]
                aug=min(aug,residual[u][v])
                v=u
            v=sink
            while parent[v] is not None:
                u=parent[v]
                residual[u][v]-=aug
                residual[v][u]=residual[v].get(u,0)+aug
                v=u
            total+=aug
        return total,residual


def _eligible_terrestrial_slots(obligation: Obligation, world: World, *, at_s:int) -> tuple[int,...]:
    return tuple(
        t for t in world.terrestrial_slots
        if t >= at_s and obligation.release_s <= t <= obligation.deadline_s
    )


def terrestrial_set_conflict(bundle: Bundle, world: World, *, at_s:int) -> SetConflictWitness:
    """Return one canonical Hall/min-cut deficiency witness for terrestrial service.

    For the unit-report/unit-slot model, max-flow on obligation->slot edges finds
    how many reports can be served terrestrially. Residual reachability from
    unmatched obligations yields a deficient obligation set U. The deficit
    |U|-|N_T(U)| is a lower bound on backup transmissions required by that set.
    """
    obligations=tuple(o for o in bundle.obligations if o.deadline_s >= at_s)
    source='SRC'; sink='SNK'; f=_ResidualFlow()
    slot_nodes={t:f'slot:{t}' for t in sorted(set(world.terrestrial_slots)) if t>=at_s}
    for o in obligations:
        on=f'obl:{o.oid}'
        f.add_edge(source,on,1)
        for t in _eligible_terrestrial_slots(o,world,at_s=at_s):
            f.add_edge(on,slot_nodes[t],1)
    for sn in slot_nodes.values():
        f.add_edge(sn,sink,1)
    matched,res=f.solve(source,sink)
    deficit=max(0,len(obligations)-matched)
    if deficit==0:
        return SetConflictWitness(world.world_id,(),(),0,0)

    # Start from obligation nodes with residual source capacity (unmatched).
    starts=[f'obl:{o.oid}' for o in obligations if res[source].get(f'obl:{o.oid}',0)>0]
    seen=set(starts); q=deque(starts)
    while q:
        u=q.popleft()
        for v,c in res.get(u,{}).items():
            if c>0 and v not in seen and v not in {source,sink}:
                seen.add(v); q.append(v)
    U=tuple(sorted(x.split(':',1)[1] for x in seen if x.startswith('obl:')))
    N=tuple(sorted(int(x.split(':',1)[1]) for x in seen if x.startswith('slot:')))
    # Residual component is the canonical witness. Fall back to all active
    # obligations only if the residual component is unexpectedly empty.
    if not U:
        U=tuple(sorted(o.oid for o in obligations))
        neighbor=set()
        for o in obligations:
            neighbor.update(_eligible_terrestrial_slots(o,world,at_s=at_s))
        N=tuple(sorted(neighbor))
    required=max(0,len(U)-len(N))
    if required==0:
        required=deficit
    return SetConflictWitness(
        world_id=world.world_id,
        obligations=U,
        terrestrial_neighbors=N,
        terrestrial_capacity=len(N),
        required_backup=required,
    )


def _world_signature(w: SetConflictWitness) -> tuple[tuple[str,...],int]:
    return (w.obligations,w.required_backup)


def build_frontier_certificates(
    bundle: Bundle,
    *,
    active_world_ids: Iterable[str] | None=None,
    at_s:int | None=None,
    satellite_budget:int | None=None,
) -> tuple[FrontierCertificate,...]:
    active=set(active_world_ids or (w.world_id for w in bundle.worlds))
    worlds=[w for w in bundle.worlds if w.world_id in active]
    if not worlds:
        return ()
    now=bundle.fixed_event_times[0] if at_s is None else int(at_s)
    budget=bundle.satellite_budget if satellite_budget is None else int(satellite_budget)
    witnesses=[terrestrial_set_conflict(bundle,w,at_s=now) for w in worlds]

    groups: dict[tuple[tuple[str,...],int],list[SetConflictWitness]]={}
    for w in witnesses:
        groups.setdefault(_world_signature(w),[]).append(w)

    qids=tuple(q.query_id for q in bundle.queries)
    certs=[]
    for idx,(sig,rows) in enumerate(sorted(groups.items(),key=lambda kv:kv[0])):
        min_budget=max((r.required_backup for r in rows),default=0)
        certs.append(FrontierCertificate(
            certificate_id=f'{bundle.bundle_id}:frontier:{idx}',
            world_ids=tuple(sorted(r.world_id for r in rows)),
            conflict_witnesses=tuple(sorted(rows,key=lambda r:r.world_id)),
            min_satellite_budget=min_budget,
            valid_budget_min=min_budget,
            valid_budget_max=None,
            evidence_dependencies=qids,
            execution_dependencies=('delivered','satellite_budget','terrestrial_slots','pending_ack'),
        ))
    # Certificates may exist even when current budget violates their domain;
    # callers can use this to derive an infeasibility upper bound.
    return tuple(certs)


class ConditionalFeasibilityFrontier:
    def __init__(self, bundle: Bundle) -> None:
        self.bundle=bundle
        self.active_world_ids=set(w.world_id for w in bundle.worlds)
        self.at_s=bundle.fixed_event_times[0]
        self.satellite_budget=bundle.satellite_budget
        self.certificates=build_frontier_certificates(bundle)

    def snapshot(self) -> tuple[FrontierCertificate,...]:
        return self.certificates

    def _refresh(self, *, changed_dependencies:set[str]) -> FrontierUpdate:
        kept=[]; invalid=[]
        for cert in self.certificates:
            dependency_hit=bool(changed_dependencies & set(cert.execution_dependencies+cert.evidence_dependencies))
            worlds_changed=not set(cert.world_ids) <= self.active_world_ids
            budget_invalid=not cert.valid_for_budget(self.satellite_budget)
            if dependency_hit or worlds_changed or budget_invalid:
                invalid.append(cert.certificate_id)
            else:
                kept.append(cert)
        rebuilt=build_frontier_certificates(
            self.bundle,
            active_world_ids=self.active_world_ids,
            at_s=self.at_s,
            satellite_budget=self.satellite_budget,
        )
        kept_ids={c.certificate_id for c in kept}
        rebuilt=[c for c in rebuilt if c.certificate_id not in kept_ids]
        self.certificates=tuple(kept+rebuilt)
        return FrontierUpdate(
            kept_certificate_ids=tuple(sorted(c.certificate_id for c in kept)),
            invalidated_certificate_ids=tuple(sorted(invalid)),
            rebuilt_certificate_ids=tuple(sorted(c.certificate_id for c in rebuilt)),
            active_world_ids=tuple(sorted(self.active_world_ids)),
        )

    def apply_query_result(self, *, query_id:str, value:str) -> FrontierUpdate:
        keep={
            w.world_id for w in self.bundle.worlds
            if w.world_id in self.active_world_ids and dict(w.evidence_values).get(query_id)==value
        }
        if not keep:
            raise ValueError('query result incompatible with active frontier')
        self.active_world_ids=keep
        return self._refresh(changed_dependencies={query_id})

    def apply_satellite_commit(self, *, new_budget:int) -> FrontierUpdate:
        if new_budget > self.satellite_budget or new_budget < 0:
            raise ValueError('invalid satellite budget transition')
        old=self.satellite_budget
        self.satellite_budget=int(new_budget)
        # Resource-domain certificate remains reusable while still inside the
        # same valid interval; only force invalidation when crossing a boundary.
        crossed=any(c.valid_for_budget(old) and not c.valid_for_budget(self.satellite_budget) for c in self.certificates)
        return self._refresh(changed_dependencies={'satellite_budget'} if crossed else set())

    def advance_time(self, *, at_s:int) -> FrontierUpdate:
        if at_s < self.at_s:
            raise ValueError('time cannot move backwards')
        self.at_s=int(at_s)
        return self._refresh(changed_dependencies={'terrestrial_slots'})
