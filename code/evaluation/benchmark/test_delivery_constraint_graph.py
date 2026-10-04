#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path: sys.path.insert(0,str(HERE))
from delivery_constraint_graph import alias_conflict_witness, world_resource_signatures
from scenario_generator_v0_4 import generate


def main() -> int:
    rows=generate(phase_limit=1,catalog_size=5)
    exact=[r for r in rows if r.exact_solvable]
    assert exact

    witnessed=0
    for row in exact:
        w=alias_conflict_witness(row.bundle)
        assert all(x.feasible for x in w.world_witnesses)
        sig=world_resource_signatures(row.bundle)
        assert set(sig)=={x.world_id for x in row.bundle.worlds}
        if row.coordinates['conflict_count']>0 and len(row.bundle.worlds)>1:
            assert w.differing_obligations
            witnessed+=1
    assert witnessed>0
    print(f'PASS delivery constraint graph: {witnessed} exact-solvable conflict bundles expose explicit shared-resource witnesses')
    return 0


if __name__=='__main__': raise SystemExit(main())
