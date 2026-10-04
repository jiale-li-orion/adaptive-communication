#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
if str(HERE) not in sys.path: sys.path.insert(0,str(HERE))

from site_contract import compatible_with_task_jurisdiction, validate_site_registry

BASE=ROOT/'local_research/current/benchmark/task-design/operational-needs'

def main() -> int:
    sites=json.loads((BASE/'SITE-PROFILE-REGISTRY.v0.1.json').read_text())['profiles']
    tasks=json.loads((BASE/'SOURCE-PROFILE-REGISTRY.v0.1.json').read_text())['profiles']
    validate_site_registry(sites)
    site=sites[0]
    db44=next(p for p in tasks if p['profile_id']=='DB44T2457_2024_warning_reporting')
    assert compatible_with_task_jurisdiction(site, db44['scope'])
    assert abs(site['coordinates']['lat_deg']-23.3188888889)<1e-10
    assert site['variables']['altitude_m']['provenance_class']=='MODEL_DERIVED_TRACE'
    assert site['variables']['altitude_m']['value']==16.0
    print('PASS site profiles: Guangdong field site has independent register coordinates + field-monitoring evidence')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
