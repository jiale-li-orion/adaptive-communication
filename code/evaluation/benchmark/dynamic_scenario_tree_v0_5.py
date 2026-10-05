#!/usr/bin/env python3
"""Dynamic Layer-1 scenario tree for v0.5 method development.

Key semantics demanded by cache06/Astra:
- repeated owner-scoped queries with distinct request ids;
- sample time differs from response-arrival time;
- owner state may change between samples;
- data send acceptance, gateway receipt and final delivery ACK are distinct;
- passive observations and ACKs share the same non-anticipative history;
- execution trace records actual requests/actions, not enabled capability count.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Obligation:
    oid: str
    release_s: int
    deadline_s: int


@dataclass(frozen=True)
class QueryCapability:
    query_id: str
    proposition: str
    owner: str
    sample_delay_s: int
    response_delay_s: int
    return_path: tuple[str,...]
    opportunity_dependency: tuple[str,...]


@dataclass(frozen=True)
class OwnerStateEvent:
    at_s: int
    proposition: str
    value: str


@dataclass(frozen=True)
class PassiveEvent:
    at_s: int
    key: str
    value: str


@dataclass(frozen=True)
class DeliveryEvent:
    send_at_s: int
    oid: str
    accepted: bool
    gateway_receipt_at_s: int | None
    final_ack_at_s: int | None


@dataclass(frozen=True)
class World:
    world_id: str
    owner_state_events: tuple[OwnerStateEvent,...]
    passive_events: tuple[PassiveEvent,...] = ()
    delivery_events: tuple[DeliveryEvent,...] = ()
    query_reachable_times: tuple[int,...] = ()

    def owner_value(self, proposition:str, at_s:int) -> str:
        rows=[e for e in self.owner_state_events if e.proposition==proposition and e.at_s<=at_s]
        if not rows:
            return '__UNKNOWN__'
        return max(rows,key=lambda e:e.at_s).value

    def query_reachable(self, at_s:int) -> bool:
        return at_s in set(self.query_reachable_times)

    def delivery(self, oid:str, send_at_s:int) -> DeliveryEvent | None:
        for e in self.delivery_events:
            if e.oid==oid and e.send_at_s==send_at_s:
                return e
        return None


@dataclass(frozen=True)
class PendingQuery:
    request_id: str
    query_id: str
    sample_at_s: int
    arrive_at_s: int
    sampled_value: str
    reachable: bool


@dataclass(frozen=True)
class PendingDelivery:
    oid: str
    send_at_s: int
    gateway_receipt_at_s: int | None
    final_ack_at_s: int | None
    accepted: bool


@dataclass(frozen=True)
class LocalState:
    final_delivered: tuple[str,...] = ()
    violated_obligations: tuple[str,...] = ()
    gateway_received: tuple[str,...] = ()
    pending_queries: tuple[PendingQuery,...] = ()
    pending_deliveries: tuple[PendingDelivery,...] = ()
    seen_passive: tuple[tuple[int,str],...] = ()
    next_request_seq: int = 0
    sat_budget: int = 0
    trace: tuple[tuple[Any,...],...] = ()


@dataclass(frozen=True)
class Bundle:
    bundle_id: str
    obligations: tuple[Obligation,...]
    worlds: tuple[World,...]
    fixed_event_times: tuple[int,...]
    terrestrial_send_times: tuple[int,...]
    satellite_send_times: tuple[int,...]
    satellite_budget: int
    queries: tuple[QueryCapability,...]


Action=tuple[str,str|None]


def _pending(bundle:Bundle,st:LocalState,t:int) -> list[Obligation]:
    done=set(st.final_delivered)
    return [o for o in bundle.obligations if o.oid not in done and o.release_s<=t<=o.deadline_s]


def _expired(bundle:Bundle,st:LocalState,t:int) -> bool:
    if st.violated_obligations:
        return True
    done=set(st.final_delivered)
    return any(o.oid not in done and o.deadline_s<t for o in bundle.obligations)


def _success(bundle:Bundle,st:LocalState) -> bool:
    return not st.violated_obligations and len(st.final_delivered)==len(bundle.obligations)


def _next_event(bundle:Bundle,t:int,states:dict[str,LocalState]) -> int|None:
    c=[x for x in bundle.fixed_event_times if x>t]
    wm={w.world_id:w for w in bundle.worlds}
    for wid,st in states.items():
        c += [q.arrive_at_s for q in st.pending_queries if q.arrive_at_s>t]
        for d in st.pending_deliveries:
            if d.gateway_receipt_at_s is not None and d.gateway_receipt_at_s>t:
                c.append(d.gateway_receipt_at_s)
            if d.final_ack_at_s is not None and d.final_ack_at_s>t:
                c.append(d.final_ack_at_s)
        seen=set(st.seen_passive)
        for e in wm[wid].passive_events:
            if e.at_s>t and (e.at_s,e.key) not in seen:
                c.append(e.at_s)
    return min(c) if c else None


def _normalize(bundle:Bundle,t:int,states:dict[str,LocalState]) -> dict[str,dict[str,LocalState]]:
    wm={w.world_id:w for w in bundle.worlds}
    out:dict[str,dict[str,LocalState]]={}
    for wid,st in states.items():
        obs=[]
        final=set(st.final_delivered); violated=set(st.violated_obligations); gateway=set(st.gateway_received)
        pqs=[]
        for q in st.pending_queries:
            if q.arrive_at_s<=t:
                value=q.sampled_value if q.reachable else '__TIMEOUT__'
                obs.append((f'query:{q.request_id}:{q.query_id}',value,f'sampled@{q.sample_at_s}'))
            else:
                pqs.append(q)
        pds=[]
        for d in st.pending_deliveries:
            if d.gateway_receipt_at_s is not None and d.gateway_receipt_at_s<=t and d.accepted:
                if d.oid not in gateway:
                    gateway.add(d.oid)
            if d.final_ack_at_s is not None and d.final_ack_at_s<=t and d.accepted:
                if d.oid not in final and d.oid not in violated:
                    deadline=next(o.deadline_s for o in bundle.obligations if o.oid==d.oid)
                    if d.final_ack_at_s<=deadline:
                        final.add(d.oid); obs.append((f'final_ack:{d.oid}','ok',f'sent@{d.send_at_s}'))
                    else:
                        violated.add(d.oid); obs.append((f'final_ack:{d.oid}','late',f'sent@{d.send_at_s}'))
            if not (d.final_ack_at_s is not None and d.final_ack_at_s<=t):
                pds.append(d)
        seen=set(st.seen_passive)
        new_seen=set(seen)
        for e in wm[wid].passive_events:
            m=(e.at_s,e.key)
            if e.at_s<=t and m not in seen:
                obs.append((f'passive:{e.key}',e.value,f'at@{e.at_s}')); new_seen.add(m)
        key='|'.join(':'.join(x) for x in sorted(obs)) or 'same'
        trace=st.trace + tuple(('OBS',t,*x) for x in sorted(obs))
        ns=LocalState(
            final_delivered=tuple(sorted(final)),violated_obligations=tuple(sorted(violated)),gateway_received=tuple(sorted(gateway)),
            pending_queries=tuple(pqs),pending_deliveries=tuple(pds),seen_passive=tuple(sorted(new_seen)),
            next_request_seq=st.next_request_seq,sat_budget=st.sat_budget,trace=trace,
        )
        out.setdefault(key,{})[wid]=ns
    return out


def _actions(bundle:Bundle,t:int,states:dict[str,LocalState]) -> list[Action]:
    common=None
    for st in states.values():
        ids={o.oid for o in _pending(bundle,st,t)}
        common=ids if common is None else common & ids
    common=common or set()
    a:[Action]=[('WAIT',None)]
    if t in bundle.terrestrial_send_times:
        a += [('SEND_TERR',oid) for oid in sorted(common)]
    if t in bundle.satellite_send_times and all(st.sat_budget>0 for st in states.values()):
        a += [('SEND_SAT',oid) for oid in sorted(common)]
    # Repeatable queries are legal after the previous request has resolved,
    # but the same capability may have at most one in-flight request per history.
    for q in bundle.queries:
        if all(all(p.query_id != q.query_id for p in st.pending_queries) for st in states.values()):
            a.append(('ISSUE_QUERY',q.query_id))
    return a





def _sample_query_value(world:World,st:LocalState,q:QueryCapability,sample_at_s:int) -> str:
    if q.proposition=='communication.gateway.receipt_summary':
        if q.sample_delay_s!=0:
            raise ValueError('receipt_summary currently requires zero sample delay')
        received=','.join(sorted(st.gateway_received)) or 'none'
        return f'gateway_received={received}'
    return world.owner_value(q.proposition,sample_at_s)

def _query_partitions(bundle:Bundle,t:int,states:dict[str,LocalState],query_id:str) -> bool:
    """Whether issuing this query can produce different legal observations now.

    Search-only dominance check: a query that deterministically yields the same
    response (including timeout) in every compatible world cannot change a
    non-anticipative feasibility policy and is omitted from exact search.
    """
    q=next(q for q in bundle.queries if q.query_id==query_id)
    sample=t+q.sample_delay_s
    wm={w.world_id:w for w in bundle.worlds}
    outcomes=set()
    for wid,st in states.items():
        w=wm[wid]
        outcomes.add(_sample_query_value(w,st,q,sample) if w.query_reachable(sample) else '__TIMEOUT__')
        if len(outcomes)>1:return True
    return False

def _step_action(bundle:Bundle,t:int,states:dict[str,LocalState],action:Action) -> tuple[dict[str,dict[str,LocalState]],int] | None:
    """Apply one legal action using the canonical dynamic execution semantics."""
    wm={w.world_id:w for w in bundle.worlds}; qm={q.query_id:q for q in bundle.queries}
    act,arg=action
    branches:dict[str,dict[str,LocalState]]={'same':{}}
    if act=='WAIT':
        nt=_next_event(bundle,t,states)
        if nt is None:return None
        return {'same':dict(states)},nt
    if act=='ISSUE_QUERY':
        q=qm[str(arg)]
        for wid,st in states.items():
            req=f'{q.query_id}#{st.next_request_seq}'
            sample=t+q.sample_delay_s; arrive=sample+q.response_delay_s
            reachable=wm[wid].query_reachable(sample)
            value=_sample_query_value(wm[wid],st,q,sample) if reachable else '__TIMEOUT__'
            pq=PendingQuery(req,q.query_id,sample,arrive,value,reachable)
            branches['same'][wid]=LocalState(
                final_delivered=st.final_delivered,violated_obligations=st.violated_obligations,gateway_received=st.gateway_received,
                pending_queries=tuple(sorted(st.pending_queries+(pq,),key=lambda x:(x.arrive_at_s,x.request_id))),
                pending_deliveries=st.pending_deliveries,seen_passive=st.seen_passive,next_request_seq=st.next_request_seq+1,sat_budget=st.sat_budget,
                trace=st.trace+(('QUERY',t,req,q.query_id,sample,arrive),),
            )
        return branches,t
    if act in {'SEND_TERR','SEND_SAT'}:
        for wid,st in states.items():
            if act=='SEND_SAT':
                deadline=next(o.deadline_s for o in bundle.obligations if o.oid==str(arg))
                delivered=set(st.final_delivered); violated=set(st.violated_obligations)
                if t<=deadline: delivered.add(str(arg))
                else: violated.add(str(arg))
                ns=LocalState(final_delivered=tuple(sorted(delivered)),violated_obligations=tuple(sorted(violated)),gateway_received=st.gateway_received,pending_queries=st.pending_queries,pending_deliveries=st.pending_deliveries,seen_passive=st.seen_passive,next_request_seq=st.next_request_seq,sat_budget=st.sat_budget-1,trace=st.trace+(('SEND_SAT',t,arg),))
            else:
                de=wm[wid].delivery(str(arg),t)
                if de is None:de=DeliveryEvent(t,str(arg),False,None,None)
                pd=PendingDelivery(str(arg),t,de.gateway_receipt_at_s,de.final_ack_at_s,de.accepted)
                ns=LocalState(final_delivered=st.final_delivered,violated_obligations=st.violated_obligations,gateway_received=st.gateway_received,pending_queries=st.pending_queries,pending_deliveries=st.pending_deliveries+(pd,),seen_passive=st.seen_passive,next_request_seq=st.next_request_seq,sat_budget=st.sat_budget,trace=st.trace+(('SEND_TERR',t,arg,de.accepted),))
            branches['same'][wid]=ns
        nt=_next_event(bundle,t,branches['same'])
        next_t=t if nt is None and all(_success(bundle,st) for st in branches['same'].values()) else nt
        if next_t is None:return None
        return branches,next_t
    return None

def solve(bundle:Bundle,*,max_decision_depth:int|None=None,forced_first_action:Action|None=None,disabled_queries:frozenset[str]=frozenset(),prefix_upper_bound:Callable[[Bundle,int,dict[str,LocalState]],bool]|None=None,action_order:Callable[[Bundle,int,dict[str,LocalState],list[Action]],list[Action]]|None=None) -> dict[str,Any]:
    wm={w.world_id:w for w in bundle.worlds}; qm={q.query_id:q for q in bundle.queries}
    start=min(bundle.fixed_event_times)
    initial={w.world_id:LocalState(sat_budget=bundle.satellite_budget) for w in bundle.worlds}
    memo={}

    def state_key(st:LocalState):
        # Execution trace is accounting-only and must not prevent memo merging.
        return (st.final_delivered,st.violated_obligations,st.gateway_received,st.pending_queries,st.pending_deliveries,st.seen_passive,st.next_request_seq,st.sat_budget)
    def canon(states): return tuple(sorted((wid,state_key(st)) for wid,st in states.items()))

    def rec(t:int,states:dict[str,LocalState],depth:int):
        norm=_normalize(bundle,t,states)
        if len(norm)>1 or next(iter(norm))!='same':
            children=[]
            for obs,ch in sorted(norm.items()):
                ok,sub=rec(t,ch,depth)
                if not ok:return False,None
                children.append({'observation':obs,'worlds':sorted(ch),'subpolicy':sub})
            return True,{'time_s':t,'event':'OBSERVATION','children':children}
        states=next(iter(norm.values()))
        if prefix_upper_bound is not None and not prefix_upper_bound(bundle,t,states):
            return (False,None)
        key=(t,depth,canon(states))
        if key in memo:return memo[key]
        if any(_expired(bundle,s,t) for s in states.values()): return (False,None)
        if all(_success(bundle,s) for s in states.values()): return (True,{'terminal':True})
        if max_decision_depth is not None and depth>=max_decision_depth: return (False,None)
        actions=[a for a in _actions(bundle,t,states) if not (a[0]=='ISSUE_QUERY' and (a[1] in disabled_queries or not _query_partitions(bundle,t,states,str(a[1]))))]
        if action_order is not None:
            actions=action_order(bundle,t,states,actions)
        if forced_first_action is not None and t==start and depth==0:
            actions=[x for x in actions if x==forced_first_action]
        for act,arg in actions:
            stepped=_step_action(bundle,t,states,(act,arg))
            if stepped is None:continue
            branches,next_t=stepped
            children=[]; good=True
            for obs,ch in sorted(branches.items()):
                ok,sub=rec(next_t,ch,depth+1)
                if not ok:good=False;break
                children.append({'observation':obs,'worlds':sorted(ch),'subpolicy':sub})
            if good:
                ans=(True,{'time_s':t,'action':act,'arg':arg,'children':children})
                memo[key]=ans;return ans
        memo[key]=(False,None);return memo[key]

    solvable,policy=rec(start,initial,0)
    return {'solvable':solvable,'policy':policy,'memo_nodes':len(memo)}


def policy_trace_for_world(policy:dict[str,Any] | None, world_id:str) -> tuple[tuple[Any,...],...]:
    """Project one exact policy onto one world and return actual executed events.

    This is for accounting. It counts actions/observations on the realized branch,
    never the number of capabilities merely enabled in the policy.
    """
    if not policy or policy.get('terminal'):
        return ()
    if policy.get('event')=='OBSERVATION':
        for child in policy.get('children',[]):
            if world_id in child.get('worlds',[]):
                obs=('OBS',policy.get('time_s'),child.get('observation'))
                return (obs,) + policy_trace_for_world(child.get('subpolicy'),world_id)
        raise ValueError(f'world {world_id!r} absent from observation branches')
    action=('ACTION',policy.get('time_s'),policy.get('action'),policy.get('arg'))
    children=policy.get('children',[])
    if not children:
        return (action,)
    for child in children:
        if world_id in child.get('worlds',[]):
            return (action,) + policy_trace_for_world(child.get('subpolicy'),world_id)
    raise ValueError(f'world {world_id!r} absent from action branches')


def execution_accounting(bundle:Bundle, policy:dict[str,Any] | None) -> dict[str,Any]:
    per_world={}
    for w in bundle.worlds:
        trace=policy_trace_for_world(policy,w.world_id)
        per_world[w.world_id]={
            'query_requests':sum(1 for x in trace if len(x)>=4 and x[0]=='ACTION' and x[2]=='ISSUE_QUERY'),
            'terrestrial_sends':sum(1 for x in trace if len(x)>=4 and x[0]=='ACTION' and x[2]=='SEND_TERR'),
            'satellite_sends':sum(1 for x in trace if len(x)>=4 and x[0]=='ACTION' and x[2]=='SEND_SAT'),
            'observations':sum(1 for x in trace if x and x[0]=='OBS'),
            'trace':trace,
        }
    return {
        'per_world':per_world,
        'max_query_requests':max((x['query_requests'] for x in per_world.values()),default=0),
        'max_total_sends':max((x['terrestrial_sends']+x['satellite_sends'] for x in per_world.values()),default=0),
    }


def observed_prefix(world:World, *, before_s:int) -> tuple[tuple[Any,...],...]:
    """World-local exogenous facts that are legally observable before a cutoff.

    Future owner-state changes and future delivery outcomes are excluded. This
    provides a direct prefix-consistency check for generator worlds.
    """
    rows=[]
    rows += [('OWNER',e.at_s,e.proposition,e.value) for e in world.owner_state_events if e.at_s<before_s]
    rows += [('PASSIVE',e.at_s,e.key,e.value) for e in world.passive_events if e.at_s<before_s]
    rows += [('REACHABLE',t) for t in world.query_reachable_times if t<before_s]
    for d in world.delivery_events:
        if d.send_at_s<before_s:
            rows.append(('SEND_OUTCOME',d.send_at_s,d.oid,d.accepted))
        if d.gateway_receipt_at_s is not None and d.gateway_receipt_at_s<before_s:
            rows.append(('GW_RECEIPT',d.gateway_receipt_at_s,d.oid))
        if d.final_ack_at_s is not None and d.final_ack_at_s<before_s:
            rows.append(('FINAL_ACK',d.final_ack_at_s,d.oid))
    return tuple(sorted(rows,key=repr))
