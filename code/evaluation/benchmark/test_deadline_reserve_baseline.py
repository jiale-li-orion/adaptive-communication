#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))

from baseline_deadline_reserve import run_deadline_reserve
from scenario_generator_v0_1 import PROFILE_DIR

def main() -> int:
    trace_registry=json.loads((PROFILE_DIR/'TRACE-PROFILE-REGISTRY.v0.1.json').read_text())
    trace=next(
        x for x in trace_registry['profiles']
        if x['trace_profile_id']=='CONNECTA_20260922_SIHUI_GEOMETRY_48H'
    )
    trace_payload=json.loads((ROOT/trace['trace_ref']).read_text())
    hard_path=ROOT/'local_research/current/benchmark/generated/scenario-generator-v0.1/hard-candidates.jsonl'
    rows=[json.loads(x) for x in hard_path.read_text().splitlines() if x]
    assert rows
    solved=sum(run_deadline_reserve(r,trace_payload=trace_payload)['success'] for r in rows)
    assert solved==len(rows), (solved,len(rows))
    print(
        f'PASS degeneracy audit: deadline-aware reserve + EDF solves '
        f'{solved}/{len(rows)} Generator-v0.1 candidates previously labelled HARD_CANDIDATE'
    )
    return 0

if __name__=='__main__':
    raise SystemExit(main())
