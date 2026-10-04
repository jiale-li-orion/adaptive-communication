#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path: sys.path.insert(0,str(HERE))
from incremental_conflict_context import IncrementalConflictContext
from scenario_generator_v0_4 import generate


def main() -> int:
    rows=generate(phase_limit=1,catalog_size=5)
    row=next(
        r for r in rows
        if r.coordinates['conflict_count']==2
        and r.coordinates['evidence_profile']=='BOTH'
        and r.exact_solvable
    )
    ctx=IncrementalConflictContext(row.bundle)
    initial=ctx.snapshot()
    assert len(initial.active_world_ids)==4
    assert initial.conflict.resource_conflict_present
    initial_flows=initial.accumulated_structural_flow_solves

    target=row.bundle.worlds[0]
    values=dict(target.evidence_values)
    d1=ctx.apply_query_result(query_id='primary_health',value=values['primary_health'])
    assert len(d1.remaining_world_ids)==2
    assert d1.structural_flow_solves_added==0
    mid=ctx.snapshot()
    assert mid.accumulated_structural_flow_solves==initial_flows
    assert mid.conflict.differing_obligations

    d2=ctx.apply_query_result(query_id='receipt_summary',value=values['receipt_summary'])
    assert len(d2.remaining_world_ids)==1
    assert d2.structural_flow_solves_added==0
    final=ctx.snapshot()
    assert final.accumulated_structural_flow_solves==initial_flows
    assert final.conflict.differing_obligations==()
    assert not final.conflict.resource_conflict_present

    materialized=ctx.materialized_context()
    assert 'world_id' not in str(materialized)
    assert materialized['alias_count']==1

    print('PASS incremental conflict context: query evidence narrows 4->2->1 aliases and resolves conflicts with zero additional max-flow solves')
    return 0


if __name__=='__main__': raise SystemExit(main())
