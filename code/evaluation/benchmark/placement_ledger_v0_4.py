#!/usr/bin/env python3
"""Planner-placement-sensitive evidence accounting for v0.4.

The same selected gateway-owned evidence can be a local context read for a
planner resident at the gateway, or a remote acquisition for a center planner.
This script keeps that distinction explicit and leaves unknown transport cost
unknown when the simulator does not model it.
"""
from __future__ import annotations

from collections import Counter
from typing import Any
from pathlib import Path
import json
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))
if str(ROOT/'code') not in sys.path:
    sys.path.insert(0,str(ROOT/'code'))

from agentic_communication.capabilities import CommunicationCapabilityCatalog
from evidence_accounting import EvidenceLedger, PlannerComputationCharge, classify_observation
from multi_evidence_conflict_planner import conflict_guided_query_search
from scenario_generator_v0_4 import generate


def _policy_query_ids(row, policy: str) -> tuple[str, ...]:
    ids=tuple(q.query_id for q in row.bundle.queries)
    if policy=='conflict_guided':
        plan,_=conflict_guided_query_search(row.bundle)
        return tuple(plan.selected_query_ids)
    if policy=='fixed_pair':
        return tuple(q for q in ('primary_health','receipt_summary') if q in ids)
    if policy=='always_all':
        return ids
    raise ValueError(policy)


def _capability_id(query_id: str) -> str:
    if query_id=='primary_health':
        return 'communication.gateway.primary_health'
    if query_id=='receipt_summary':
        return 'communication.gateway.receipt_summary'
    if query_id.startswith('node_report:'):
        return 'communication.gateway.node_report'
    raise ValueError(query_id)


def placement_ledger(*, phase_limit:int=4, catalog_size:int=5) -> dict[str,Any]:
    rows=[r for r in generate(phase_limit=phase_limit,catalog_size=catalog_size) if r.exact_solvable]
    catalog=CommunicationCapabilityCatalog()
    out={}

    for planner_location in ('gateway','center'):
        by_policy={}
        for policy in ('conflict_guided','fixed_pair','always_all'):
            ledger=EvidenceLedger()
            query_counter=Counter()
            for row in rows:
                query_ids=_policy_query_ids(row,policy)
                for qid in query_ids:
                    query_counter[qid]+=1
                    binding=catalog.binding(_capability_id(qid))
                    ledger.add_evidence_charge(classify_observation(
                        binding=binding,
                        planner_location=planner_location,
                        result=None,
                    ))
                if policy=='conflict_guided':
                    _,diag=conflict_guided_query_search(row.bundle)
                    ledger.add_computation(PlannerComputationCharge(
                        subset_solves=diag.subset_solves,
                        preprocessing_solves=diag.preprocessing_solves,
                        memo_nodes=diag.total_memo_nodes,
                    ))
            by_policy[policy]={
                'exact_solvable_cases':len(rows),
                'selected_query_count':sum(query_counter.values()),
                'mean_selected_query_count':sum(query_counter.values())/len(rows) if rows else None,
                'query_id_counts':dict(sorted(query_counter.items())),
                'ledger':ledger.summary(),
            }
        out[planner_location]=by_policy

    return {
        'generator':'v0.4-multi-conflict-process-pilot',
        'planner_placements':out,
        'interpretation':{
            'gateway':'gateway-owned evidence is local context/read work; do not report it as network acquisition',
            'center':'gateway-owned evidence is remote acquisition; transport bytes/airtime/energy remain unknown unless runtime results provide them',
        },
    }


if __name__=='__main__':
    print(json.dumps(placement_ledger(),indent=2,sort_keys=True))
