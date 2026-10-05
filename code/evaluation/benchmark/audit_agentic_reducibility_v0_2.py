#!/usr/bin/env python3
"""Freeze Layer-1 v0.2 agentic reducibility evidence from existing exact artifacts.

The audit does not introduce a new solver.  It joins the already-frozen
observation-matched, no-paid-query and blind-open-loop references for the final
V8 hard survivors.  A survivor passes only if adaptive observation-matched
control succeeds while both current-observation/no-paid acquisition and blind
open-loop control cannot guarantee the task.
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
    for s in sorted(survivors, key=lambda r: r['signature']):
        sig = str(s['signature'])
        v = v0v7[sig]
        e = exact[sig]
        exact_ok = e['exact']['status'] == 'EXACT' and e['exact']['solvable'] is True
        no_paid_fails = e['no_paid_query']['status'] == 'EXACT' and e['no_paid_query']['solvable'] is False
        blind_fails = (
            v['blind']['solvable'] is False
            and v['blind']['status'] in {'EXACT', 'DERIVED_FROM_NO_PAID_INFEASIBLE'}
        )
        full_current_ok = e['full_current']['status'] == 'EXACT' and e['full_current']['solvable'] is True
        common_safe_excluded = v['filters']['V3_COMMON_SAFE_ACTION'] is True
        paid_evidence = e['classification'] == 'PAID_EVIDENCE_REQUIRED'
        query_surface = s['evidence_regime'] == 'GATEWAY_SUMMARY_QUERY'
        passed = all((exact_ok, no_paid_fails, blind_fails, full_current_ok, common_safe_excluded, paid_evidence, query_surface))
        rows.append({
            'signature': sig,
            'representative_recipe_id': s['representative_recipe_id'],
            'exact_observation_matched_success': exact_ok,
            'no_paid_query_success': not no_paid_fails,
            'blind_open_loop_success': not blind_fails,
            'full_current_state_success': full_current_ok,
            'common_safe_open_loop_excluded': common_safe_excluded,
            'paid_evidence_required': paid_evidence,
            'evidence_regime': s['evidence_regime'],
            'passed': passed,
        })
    passed = len(rows) == 41 and all(r['passed'] for r in rows)
    artifact = {
        'schema_version': '0.2',
        'status': 'PASS' if passed else 'FAIL',
        'audit': 'AGENTIC_REDUCIBILITY',
        'hard_signature_count': len(rows),
        'pass_count': sum(r['passed'] for r in rows),
        'fail_count': sum(not r['passed'] for r in rows),
        'classification': dict(sorted(Counter(s['exact_classification'] for s in survivors).items())),
        'interpretation': [
            'Observation-matched adaptive policy succeeds on every admitted hard signature.',
            'The no-paid-query reference still keeps passive telemetry, ACK and normal send-as-probe; its failure shows the current observation plus ordinary feedback is insufficient.',
            'The blind open-loop reference also fails, excluding a fixed observation-independent action sequence as a robust solution.',
            'Full-current-state causal feasibility succeeds, so the task is not physically impossible once the hidden current state is revealed.',
        ],
        'claim_boundary': 'This establishes non-reducibility of the admitted hard signatures to current-observation/no-paid-acquisition or blind open-loop control. It does not claim that every public-test case is agentic-hard; easy/conformance/diagnostic cases are intentionally retained.',
        'rows': rows,
    }
    print(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
