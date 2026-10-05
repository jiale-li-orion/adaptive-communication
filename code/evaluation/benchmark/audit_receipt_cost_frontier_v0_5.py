#!/usr/bin/env python3
"""Bounded Pareto coverage audit for the v0.5 receipt process.

Default mode only materializes the declared development/holdout grids.  Full
exact-frontier evaluation requires --run so normal repository checks stay fast.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from typing import Any

from audit_receipt_continuation_v0_5 import public_contract
from receipt_cost_frontier_v0_5 import exact_cost_frontier
from receipt_reserve_baseline_v0_5 import PublicReceiptContract, solve_receipt_reserve
from scenario_generator_v0_5 import (
    _slots, build_overlapping_receipt_chain_at_start,
    build_overlapping_receipt_chain_bundle, phase_groups,
)


def _pareto_points(points: list[tuple[int,int]]) -> list[tuple[int,int]]:
    pts=sorted(set(points))
    return [p for p in pts if not any(q!=p and q[0]<=p[0] and q[1]<=p[1] for q in pts)]


def _cost(result:dict[str,Any]) -> tuple[int,int] | None:
    if not result['solvable']:
        return None
    rows=result['per_world'].values()
    return (sum(x['queries'] for x in rows),sum(x['satellite_sends'] for x in rows))


def ordinary_family(bundle) -> dict[str,Any]:
    base=public_contract(bundle)
    rows={}
    center_specs=[
        ('passive','passive',base),
        ('passive-wait','passive-wait',base),
        ('conditional','conditional',base),
        ('conditional-wait','conditional-wait',base),
        ('fixed-all','fixed-read',base),
        ('fixed-all-wait','fixed-read-wait',base),
    ]
    for t in base.receipt_read_times:
        one=replace(base,receipt_read_times=(t,))
        center_specs.append((f'fixed@{t}','fixed-read',one))
        center_specs.append((f'fixed-wait@{t}','fixed-read-wait',one))
    for name,mode,contract in center_specs:
        result=solve_receipt_reserve(bundle,contract,mode=mode)
        rows[name]={'result':result,'cost':_cost(result),'placement':'center'}
    local=solve_receipt_reserve(bundle,base,gateway_local=True)
    rows['gateway-local']={'result':local,'cost':_cost(local),'placement':'gateway'}
    center_points=_pareto_points([x['cost'] for x in rows.values()
                                  if x['placement']=='center' and x['cost'] is not None])
    return {'policies':rows,'center_pareto':center_points,
            'gateway_local_cost':rows['gateway-local']['cost']}


def _shift_ack(bundle,offset_s:int):
    worlds=[]; fixed=set(bundle.fixed_event_times)
    for w in bundle.worlds:
        events=[]
        for e in w.delivery_events:
            if not e.accepted or e.final_ack_at_s is None:
                events.append(e);continue
            floor=e.gateway_receipt_at_s if e.gateway_receipt_at_s is not None else e.send_at_s
            final=max(floor,e.final_ack_at_s+offset_s)
            fixed.add(final)
            events.append(replace(e,final_ack_at_s=final))
        worlds.append(replace(w,delivery_events=tuple(events)))
    return replace(bundle,worlds=tuple(worlds),fixed_event_times=tuple(sorted(fixed)))


def make_variant(*,start:int,budget:int,query_delay_s:int,ack_offset_s:int,tag:str):
    b=build_overlapping_receipt_chain_at_start(start=start,bundle_tag=tag)
    b=replace(b,satellite_budget=budget,
              queries=(replace(b.queries[0],response_delay_s=query_delay_s),))
    return _shift_ack(b,ack_offset_s)


def _window_signature(start:int) -> tuple[int,...]:
    # Relative geometry overlap with the three obligation windows and the two
    # receipt read opportunities.  Holdout selection excludes signatures seen
    # in development, not merely start timestamps.
    sats=tuple(t for t in _slots() if start<=t<=start+8*3600)
    rel=tuple(t-start for t in sats)
    bounds=((0,7200),(10800,21600),(18000,25200))
    counts=tuple(sum(lo<=x<=hi for x in rel) for lo,hi in bounds)
    early=sum(0<=x<=4500+60 for x in rel)
    middle=sum(4500+60<x<=18900+60 for x in rel)
    late=sum(x>18900+60 for x in rel)
    return counts+(early,middle,late)


def development_grid() -> list[dict[str,int|str]]:
    # 4 geometry phases * 3 budgets * 3 query delays * 3 ACK offsets = 108.
    starts=[phase_groups(4,i+1)[i][0] for i in range(4)]
    rows=[]
    for phase,start in enumerate(starts):
        for budget in (1,2,3):
            for qd in (60,120,300):
                for ack in (-600,0,600):
                    rows.append({'split':'dev','phase_index':phase,'start':start,
                                 'budget':budget,'query_delay_s':qd,
                                 'ack_offset_s':ack,'signature':repr(_window_signature(start))})
    return rows


def holdout_starts(limit:int=10) -> list[int]:
    dev_starts={row['start'] for row in development_grid()}
    dev_sigs={_window_signature(int(x)) for x in dev_starts}
    horizon=48*3600
    rows=[]; seen=set()
    for start in range(0,horizon-8*3600+1,1800):
        if start in dev_starts:continue
        sig=_window_signature(start)
        if sig in dev_sigs or sig in seen:continue
        # Keep only starts with at least one geometry window; physical/information
        # admission later decides whether the actual task is solvable.
        if not any(sig[:3]):continue
        rows.append(start);seen.add(sig)
        if len(rows)>=limit:break
    if len(rows)<limit:
        raise RuntimeError(f'only {len(rows)} unseen geometry-overlap signatures')
    return rows


def holdout_grid() -> list[dict[str,int|str]]:
    # 10 unseen overlap signatures * 2 budgets * 2 delays * 2 ACK offsets = 80.
    rows=[]
    for idx,start in enumerate(holdout_starts(10)):
        for budget in (1,2):
            for qd in (90,240):
                for ack in (-300,300):
                    rows.append({'split':'holdout','holdout_index':idx,'start':start,
                                 'budget':budget,'query_delay_s':qd,
                                 'ack_offset_s':ack,'signature':repr(_window_signature(start))})
    return rows


def audit_cell(spec:dict[str,Any]) -> dict[str,Any]:
    tag=f"{spec['split']}-{spec.get('phase_index',spec.get('holdout_index'))}-b{spec['budget']}-q{spec['query_delay_s']}-a{spec['ack_offset_s']}"
    b=make_variant(start=int(spec['start']),budget=int(spec['budget']),
                   query_delay_s=int(spec['query_delay_s']),
                   ack_offset_s=int(spec['ack_offset_s']),tag=tag)
    exact=exact_cost_frontier(b,max_queries_per_world=len(b.worlds[0].query_reachable_times))
    ordinary=ordinary_family(b)
    exact_points=[(x['remote_queries'],x['satellite_sends']) for x in exact['points']]
    ordinary_points=ordinary['center_pareto']
    covered=all(any(op[0]<=ep[0] and op[1]<=ep[1] for op in ordinary_points)
                for ep in exact_points)
    return {**spec,'exact_solvable':exact['solvable'],'exact_pareto':exact_points,
            'ordinary_center_pareto':ordinary_points,
            'ordinary_covers_exact':covered if exact['solvable'] else None,
            'gateway_local_cost':ordinary['gateway_local_cost'],
            'exact_memo_states':exact['memo_states']}


def run_grid(rows:list[dict[str,Any]],limit:int|None=None):
    selected=rows if limit is None else rows[:limit]
    return [audit_cell(x) for x in selected]


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--split',choices=('dev','holdout','both'),default='both')
    ap.add_argument('--run',action='store_true')
    ap.add_argument('--limit',type=int)
    args=ap.parse_args()
    rows=[]
    if args.split in ('dev','both'):rows.extend(development_grid())
    if args.split in ('holdout','both'):rows.extend(holdout_grid())
    payload={'declared_cells':len(rows),
             'dev_cells':len(development_grid()),'holdout_cells':len(holdout_grid()),
             'holdout_starts':holdout_starts(10)}
    if args.run:
        result=run_grid(rows,args.limit)
        payload['evaluated_cells']=len(result)
        payload['rows']=result
        solv=[x for x in result if x['exact_solvable']]
        payload['exact_solvable_cells']=len(solv)
        payload['ordinary_covered_solvable_cells']=sum(bool(x['ordinary_covers_exact']) for x in solv)
    print(json.dumps(payload,indent=2,sort_keys=True))
