#!/usr/bin/env python3
"""Freeze communication/information attribution controls for Layer-1 v0.2.

All controls are projected from already-frozen exact/V0-V7 references.  The
audit asks whether hard cases change under information and physical-constraint
interventions, rather than attributing failure to generic model incompetence.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
V8 = ROOT / 'local_research/current/benchmark/generated/v8-all-pass-v0.2-retry-legality/signature-v8.jsonl'
V0V7 = ROOT / 'local_research/current/benchmark/generated/v0-v7-full-v0.2-retry-legality/signature-validity.jsonl'
EXACT = ROOT / 'local_research/current/benchmark/generated/exact-labels-v0.2-retry-legality/signature-labels.jsonl'


def load_jsonl(path: Path) -> dict[str, dict]:
    out = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            row = json.loads(line)
            out[str(row['signature'])] = row
    return out


def main() -> int:
    v8 = load_jsonl(V8)
    v0v7 = load_jsonl(V0V7)
    exact = load_jsonl(EXACT)
    survivors = [r for r in v8.values() if r['v8_disposition'] == 'SURVIVES_V8_LADDER_V0_1']
    rows = []
    binding_counts = Counter()
    for s in sorted(survivors, key=lambda r: r['signature']):
        sig = str(s['signature'])
        v = v0v7[sig]
        e = exact[sig]
        binding = dict(v['binding'])
        for k, val in binding.items():
            if val:
                binding_counts[k] += 1
        acquisition_matters = e['exact']['solvable'] is True and e['no_paid_query']['solvable'] is False
        perfect_current_state_recovers = e['full_current']['solvable'] is True
        physical_worlds_feasible = e['physical']['all_worlds_solvable'] is True
        some_constraint_binding = any(binding.values())
        outcome_separated = v['filters']['V6_OUTCOME_SEPARATION'] is True
        passed = all((acquisition_matters, perfect_current_state_recovers, physical_worlds_feasible, some_constraint_binding, outcome_separated))
        rows.append({
            'signature': sig,
            'representative_recipe_id': s['representative_recipe_id'],
            'full_system_observation_matched_success': bool(e['exact']['solvable']),
            'no_paid_acquisition_success': bool(e['no_paid_query']['solvable']),
            'perfect_current_observation_success': bool(e['full_current']['solvable']),
            'all_hidden_worlds_physically_feasible': bool(e['physical']['all_worlds_solvable']),
            'binding_constraints': binding,
            'outcome_separation': outcome_separated,
            'passed': passed,
        })
    passed = len(rows) == 41 and all(r['passed'] for r in rows)
    artifact = {
        'schema_version': '0.2',
        'status': 'PASS' if passed else 'FAIL',
        'audit': 'COMMUNICATION_ATTRIBUTION',
        'hard_signature_count': len(rows),
        'pass_count': sum(r['passed'] for r in rows),
        'fail_count': sum(not r['passed'] for r in rows),
        'binding_constraint_signature_count': dict(sorted(binding_counts.items())),
        'controls': {
            'full_system': 'observation-matched exact policy',
            'no_paid_acquisition': 'paid owner query disabled; passive telemetry, ACK and normal send-as-probe retained',
            'perfect_current_observation': 'full-current-state causal reference',
            'resource_deadline_intervention': 'V5 binding flags are derived from relaxed-deadline / relaxed-capacity / relaxed-satellite-budget physical plan-set expansion',
            'no_memory': 'NOT_APPLICABLE_TO_CURRENT_T1_HARD_SURVIVORS_AS_A_SEPARATE_RELEASE_CONTROL; causal history is part of the declared observation process rather than a detachable model-memory module',
        },
        'interpretation': [
            'Every hard survivor is physically feasible in every hidden world.',
            'Every hard survivor is solvable when the current hidden state is revealed, but fails when paid acquisition is removed while ordinary feedback remains.',
            'Every hard survivor has at least one source-deadline or controlled resource constraint whose relaxation expands the physical success-plan set.',
            'Therefore the admitted hardness is attributable to the joint information/communication/constraint structure rather than raw task impossibility.',
        ],
        'rows': rows,
    }
    print(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
