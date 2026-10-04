#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path: sys.path.insert(0,str(HERE))
from scenario_generator_v0_4 import generate


def main() -> int:
    rows=generate(phase_limit=1,catalog_size=5)
    seen_primary=set(); seen_receipt=set()
    for row in rows:
        for world in row.bundle.worlds:
            values=dict(world.evidence_values)
            for qid,value in values.items():
                low=value.lower()
                assert 'needs-' not in low
                assert 'report_' not in low
                assert 'sat@' not in low
                if value!='same':
                    obj=json.loads(value)
                    assert isinstance(obj,dict)
            if values['primary_health']!='same': seen_primary.add(values['primary_health'])
            if values['receipt_summary']!='same': seen_receipt.add(values['receipt_summary'])
    assert len(seen_primary)==2
    assert len(seen_receipt)==2
    print('PASS v0.4 state-grounded evidence: query values expose current/past gateway facts without future-plan labels')
    return 0


if __name__=='__main__': raise SystemExit(main())
