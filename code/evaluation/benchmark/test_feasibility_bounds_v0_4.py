#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path: sys.path.insert(0,str(HERE))
from feasibility_bounds import satellite_commit_bounds
from scenario_generator_v0_4 import generate


def main() -> int:
    rows=generate(phase_limit=1,catalog_size=5)
    row=next(r for r in rows if r.coordinates['conflict_count']==2 and r.exact_solvable)
    t=min(row.bundle.satellite_slots)
    bounds=satellite_commit_bounds(row.bundle,time_s=t)
    assert bounds
    assert all(b.lower<=b.upper for b in bounds)
    assert any(b.upper==0 for b in bounds) or any(b.lower==0 and b.upper==1 for b in bounds)
    print('PASS feasibility bounds v0.4: structural L/U bounds classify irreversible satellite commits before exact continuation search')
    return 0


if __name__=='__main__': raise SystemExit(main())
