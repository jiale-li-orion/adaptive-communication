#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path: sys.path.insert(0,str(HERE))
from conditional_feasibility_frontier import ConditionalFeasibilityFrontier,terrestrial_set_conflict
from scenario_generator_v0_4 import generate


def main() -> int:
    rows=generate(phase_limit=1,catalog_size=5)
    row=next(r for r in rows if r.coordinates['conflict_count']==2 and r.exact_solvable and r.coordinates['evidence_profile']=='BOTH')
    frontier=ConditionalFeasibilityFrontier(row.bundle)
    certs=frontier.snapshot()
    assert certs
    # Set witness is not restricted to a single mandatory report.
    assert any(len(w.obligations)>=1 for c in certs for w in c.conflict_witnesses)
    target=row.bundle.worlds[0]
    values=dict(target.evidence_values)
    upd=frontier.apply_query_result(query_id='primary_health',value=values['primary_health'])
    assert len(upd.active_world_ids)==2
    before=frontier.snapshot()
    upd2=frontier.apply_satellite_commit(new_budget=row.bundle.satellite_budget)
    # Staying inside the same resource-validity domain does not force a rebuild.
    assert not upd2.invalidated_certificate_ids
    assert frontier.snapshot()==before
    print('PASS conditional feasibility frontier: min-cut set witnesses, evidence-conditioned frontier narrowing, and resource-domain certificate reuse')
    return 0


if __name__=='__main__': raise SystemExit(main())
