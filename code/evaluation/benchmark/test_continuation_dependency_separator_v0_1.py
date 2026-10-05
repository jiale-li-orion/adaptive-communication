#!/usr/bin/env python3
from dataclasses import replace

from audit_retry_action_mask_v0_1 import minimal_witness
from causal_evidence_process_v0_1 import attach_causal_evidence
from continuation_dependency_separator_v0_1 import DependencySeparator, dependency_separator_key
from exact_reference_oracle_v0_1 import LocalState


def main():
    bundle = minimal_witness()
    process = attach_causal_evidence(bundle)
    projector = DependencySeparator(bundle, process)
    # At t=100, A0 has ended.  Historical use of A0 cannot be read by any
    # future matching operation.  last_direct_signature is also dead because
    # this process has no direct-current-state observation surface.
    base = {
        'A': LocalState(satellite_budget=0),
        'B': LocalState(satellite_budget=0),
    }
    changed = {
        'A': replace(base['A'], terrestrial_used=(('A0', 1),), last_direct_signature='obsolete'),
        'B': replace(base['B'], last_direct_signature='different-obsolete'),
    }
    assert base != changed
    assert dependency_separator_key(bundle, process, 100, base) == dependency_separator_key(bundle, process, 100, changed)
    assert projector.key(100, base) == projector.key(100, changed)

    # At t=60 A0 is still potentially usable; its consumption is a live
    # dependency and must keep the states separated.
    assert dependency_separator_key(bundle, process, 60, base) != dependency_separator_key(bundle, process, 60, changed)
    assert projector.key(60, base) != projector.key(60, changed)
    print('PASS continuation dependency separator: dead-history compression keeps live capacity explicit')


if __name__ == '__main__':
    main()
