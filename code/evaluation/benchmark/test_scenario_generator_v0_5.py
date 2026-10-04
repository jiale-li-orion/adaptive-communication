#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
from dynamic_scenario_tree_v0_5 import observed_prefix
from scenario_generator_v0_5 import build_bundle


def main():
    b=build_bundle()
    assert len(b.obligations)==6 and len(b.worlds)==4
    start=min(b.fixed_event_times)
    # All worlds share the complete observable prefix before the first future service transition.
    prefixes={observed_prefix(w,before_s=start+7200) for w in b.worlds}
    assert len(prefixes)==1
    # After the transition, legal current owner state may differ.
    later={observed_prefix(w,before_s=start+7201) for w in b.worlds}
    assert len(later)>1
    # Future trajectories are not encoded in the initial observation.
    initial={w.owner_value('communication.gateway.primary_health',start) for w in b.worlds}
    assert initial=={'healthy'}
    print('PASS v0.5 generator: two-stream six-obligation dynamic process preserves shared prefixes and future-state ambiguity without hidden-future encoding')
    return 0

if __name__=='__main__':raise SystemExit(main())
