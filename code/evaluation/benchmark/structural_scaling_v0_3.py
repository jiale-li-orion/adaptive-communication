#!/usr/bin/env python3
"""Structural scaling pilot over worlds/obligations using actual Connecta phases."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from math import ceil, log2
from pathlib import Path
from typing import Any
import json

from multi_evidence_conflict_planner import (
    conflict_guided_query_search,
    exhaustive_query_search,
)
from multi_evidence_scenario_tree import Bundle, EvidenceQuery, Obligation, World, solve

ROOT=Path(__file__).resolve().parents[3]
TRACE=ROOT/'research/benchmark/traces/v0.1/CONNECTA_20260922_SIHUI_GEOMETRY_48H.json'
CADENCE_S=2*3600
MASK_DEG=20


def _slots() -> list[int]:
    d=json.loads(TRACE.read_text())
    t0=datetime.fromisoformat(d['start_utc'])
    return [
        int((datetime.fromisoformat(w['start'])-t0).total_seconds())
        for w in d['thresholds'][str(MASK_DEG)]['windows_utc']
    ]


def phase_groups(k:int, limit:int=4) -> list[tuple[int,tuple[int,...]]]:
    slots=_slots(); horizon=48*3600
    out=[]
    for start in range(0,horizon-k*CADENCE_S+1,1800):
        picked=[]
        for i in range(k):
            lo=start+i*CADENCE_S; hi=lo+CADENCE_S
            xs=[s for s in slots if lo+120<=s<hi-120]
            if not xs:
                picked=[]; break
            picked.append(xs[0])
        if picked:
            out.append((start,tuple(picked)))
            if len(out)>=limit:
                break
    return out


def _query_defs(k:int, irrelevant:int=2) -> tuple[EvidenceQuery,...]:
    bits=max(1,ceil(log2(k)))
    semantic=[
        ('primary_health','communication.gateway.primary_health',40),
        ('receipt_summary','communication.gateway.receipt_summary',20),
        ('node_report:n0','communication.gateway.node_report',60),
    ]
    rows=[]
    for i in range(bits):
        qid,prop,delay=semantic[i]
        rows.append(EvidenceQuery(qid,prop,'gateway',delay))
    for j in range(irrelevant):
        rows.append(EvidenceQuery(
            f'node_report:noise{j}',
            'communication.gateway.node_report',
            'gateway',
            80+10*j,
        ))
    return tuple(rows)


def _value_for(query_id:str, mode:int, bit_index:int|None) -> str:
    if bit_index is None:
        return 'same'
    bit=(mode>>bit_index)&1
    if query_id=='primary_health':
        return 'recent' if bit==0 else 'stale'
    if query_id=='receipt_summary':
        return 'heard' if bit==0 else 'missing'
    return f'cache-bucket-{bit}'


def build_bundle(k:int, phase_index:int, start:int, sats:tuple[int,...], irrelevant:int=2) -> Bundle:
    queries=_query_defs(k,irrelevant)
    relevant=[q for q in queries if 'noise' not in q.query_id]
    bit_index={q.query_id:i for i,q in enumerate(relevant)}
    obligations=tuple(
        Obligation(f'report_{i}',start+i*CADENCE_S,start+(i+1)*CADENCE_S)
        for i in range(k)
    )
    rescue=[]
    for i,sat in enumerate(sats):
        r=min(sat+600,obligations[i].deadline_s-60)
        if r<=sat:
            raise ValueError('invalid rescue slot')
        rescue.append(r)
    worlds=[]
    for mode in range(k):
        values=[]
        for q in queries:
            values.append((q.query_id,_value_for(q.query_id,mode,bit_index.get(q.query_id))))
        worlds.append(World(
            world_id=f'mode{mode}',
            terrestrial_slots=tuple(rescue[i] for i in range(k) if i!=mode),
            evidence_values=tuple(values),
        ))
    fixed={start,*sats,*rescue}
    for o in obligations:
        fixed.add(o.release_s); fixed.add(o.deadline_s)
    return Bundle(
        bundle_id=f'struct-k{k}-p{phase_index}',
        fixed_event_times=tuple(sorted(fixed)),
        obligations=obligations,
        satellite_slots=sats,
        worlds=tuple(worlds),
        satellite_budget=1,
        queries=queries,
        initial_public_observation=(
            ('warning','orange'),
            ('report_period_s',str(CADENCE_S)),
            ('satellite_budget','1'),
        ),
    )


def run_structural_scaling(ks:tuple[int,...]=(2,3,4), phase_limit:int=4) -> dict[str,Any]:
    rows=[]
    for k in ks:
        for phase_index,(start,sats) in enumerate(phase_groups(k,phase_limit)):
            b=build_bundle(k,phase_index,start,sats)
            all_q=frozenset(q.query_id for q in b.queries)
            no_query=solve(b,disabled_queries=all_q)
            exact=solve(b)
            ex,exd=exhaustive_query_search(b)
            gd,gdd=conflict_guided_query_search(b)
            if not exact['solvable'] or no_query['solvable']:
                raise AssertionError((k,phase_index,no_query,exact))
            if ex.mode!=gd.mode or set(ex.selected_query_ids)!=set(gd.selected_query_ids):
                raise AssertionError((ex,gd))
            rows.append({
                'world_count':k,
                'obligation_count':k,
                'phase_index':phase_index,
                'catalog_size':len(b.queries),
                'selected_query_count':len(gd.selected_query_ids),
                'exact_policy_memo_nodes':int(exact['memo_nodes']),
                'exhaustive_subset_solves':exd.subset_solves,
                'guided_subset_solves':gdd.subset_solves,
                'guided_preprocessing_solves':gdd.preprocessing_solves,
                'guided_structural_flow_solves':gdd.structural_flow_solves,
                'exhaustive_total_memo_nodes':exd.total_memo_nodes,
                'guided_total_memo_nodes':gdd.total_memo_nodes,
            })
    grouped=defaultdict(list)
    for r in rows:
        grouped[r['world_count']].append(r)
    summary={}
    for k,group in sorted(grouped.items()):
        def avg(key): return sum(float(x[key]) for x in group)/len(group)
        summary[str(k)]={
            'cases':len(group),
            'catalog_size':group[0]['catalog_size'],
            'selected_query_count':group[0]['selected_query_count'],
            'mean_exact_policy_memo_nodes':avg('exact_policy_memo_nodes'),
            'mean_exhaustive_subset_solves':avg('exhaustive_subset_solves'),
            'mean_guided_subset_solves':avg('guided_subset_solves'),
            'mean_guided_preprocessing_solves':avg('guided_preprocessing_solves'),
            'mean_guided_structural_flow_solves':avg('guided_structural_flow_solves'),
            'mean_exhaustive_total_memo_nodes':avg('exhaustive_total_memo_nodes'),
            'mean_guided_total_memo_nodes':avg('guided_total_memo_nodes'),
            'guided_over_exhaustive_memo_ratio':avg('guided_total_memo_nodes')/avg('exhaustive_total_memo_nodes'),
        }
    return {'rows':rows,'summary':summary}


if __name__=='__main__':
    print(json.dumps(run_structural_scaling()['summary'],indent=2,sort_keys=True))
