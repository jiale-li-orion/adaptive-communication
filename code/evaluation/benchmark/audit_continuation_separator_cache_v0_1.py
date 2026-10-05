#!/usr/bin/env python3
"""Compare full-boundary witness domains with replay-gated separator reuse."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from causal_evidence_process_v0_1 import attach_causal_evidence
from continuation_dependency_separator_v0_1 import DependencySeparator, separator_explanation
from continuation_resource_domains_v0_1 import ContinuationPlanner, verify_witness
from exact_reference_oracle_v0_1 import LocalState, _attempt_lattice


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUTS = ROOT / 'results/benchmark/layer1-retry-review-inputs.json'
DEFAULT_OUT = ROOT / 'results/benchmark/layer2-continuation-separator-cache-v0.1.json'
ORDERS = ('rich_to_poor', 'poor_to_rich')


def _cells(bundle, order):
    qmax = len(bundle['obligations'])
    bmax = int(bundle['public_environment']['satellite_budget_units'])
    cells = [(q, b) for q in range(qmax + 1) for b in range(bmax + 1)]
    if order == 'rich_to_poor':
        return sorted(cells, key=lambda x: (-x[0], -x[1]))
    return sorted(cells, key=lambda x: (x[0], x[1]))


def _initial(bundle, b):
    return {str(w['world_id']): LocalState(satellite_budget=b) for w in bundle['worlds']}


def _run(bundle, order, *, separator, max_expansions):
    process = attach_causal_evidence(bundle)
    sep_fn = None
    if separator:
        projector = DependencySeparator(bundle, process)
        sep_fn = projector.key
    planner = ContinuationPlanner(bundle, mode='witness_domain', separator_key_fn=sep_fn)
    start = min(_attempt_lattice(bundle))
    rows = []
    replay_failures = []
    for q, b in _cells(bundle, order):
        states = _initial(bundle, b)
        result = planner.solve(start, states, query_budget=q, max_expansions=max_expansions)
        if result['solvable'] is True:
            try:
                verify_witness(bundle, start, states, result['policy'], query_budget=q)
            except Exception as exc:
                replay_failures.append({
                    'cell': [q, b], 'error': f'{type(exc).__name__}: {exc}'
                })
        rows.append({
            'query_budget': q,
            'satellite_budget': b,
            'status': result['status'],
            'solvable': result['solvable'],
            'requirement': result['requirement'],
            'metrics': result['metrics'],
        })
    metric_keys = [
        'expanded', 'recursive_calls', 'exact_hits', 'domain_hits',
        'negative_domain_hits', 'domain_comparisons', 'separator_hits',
        'separator_replay_checks', 'separator_replay_failures',
        'separator_comparisons', 'separator_replay_wall_s', 'wall_s',
    ]
    totals = {k: sum(float(r['metrics'].get(k, 0)) for r in rows) for k in metric_keys}
    for k in metric_keys:
        if k not in {'wall_s', 'separator_replay_wall_s'}:
            totals[k] = int(totals[k])
    totals['zero_expansion_cells'] = sum(int(r['metrics']['expanded'] == 0) for r in rows)
    totals['cell_count'] = len(rows)
    totals['solvable_cells'] = sum(int(r['solvable'] is True) for r in rows)
    totals['unsolvable_cells'] = sum(int(r['solvable'] is False) for r in rows)
    totals['search_limit_cells'] = sum(int(r['status'] == 'SEARCH_LIMIT') for r in rows)
    return {
        'separator_enabled': separator,
        'order': order,
        'totals': totals,
        'positive_replay_failure_count': len(replay_failures),
        'positive_replay_failures': replay_failures,
        'cells': rows,
    }


def _outcomes(run):
    return {
        (r['query_budget'], r['satellite_budget']): (r['status'], r['solvable'])
        for r in run['cells']
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inputs', type=Path, default=DEFAULT_INPUTS)
    ap.add_argument('--out', type=Path, default=DEFAULT_OUT)
    ap.add_argument('--max-expansions', type=int, default=200_000)
    args = ap.parse_args()
    frozen = json.loads(args.inputs.read_text(encoding='utf-8'))

    cases = []
    aggregate = {}
    all_agree = True
    all_replay = True
    for order in ORDERS:
        aggregate[order] = {
            'full_boundary': {},
            'separator': {},
        }
    for index, source_row in enumerate(frozen['rows']):
        bundle = source_row['bundle']
        runs = {}
        comparison = {}
        for order in ORDERS:
            full = _run(bundle, order, separator=False, max_expansions=args.max_expansions)
            sep = _run(bundle, order, separator=True, max_expansions=args.max_expansions)
            runs[f'{order}|full'] = full
            runs[f'{order}|separator'] = sep
            agree = _outcomes(full) == _outcomes(sep)
            all_agree = all_agree and agree
            all_replay = all_replay and sep['positive_replay_failure_count'] == 0
            ft, st = full['totals'], sep['totals']
            comparison[order] = {
                'outcome_agreement': agree,
                'full_expanded': ft['expanded'],
                'separator_expanded': st['expanded'],
                'expansion_delta': st['expanded'] - ft['expanded'],
                'expansion_ratio': st['expanded'] / ft['expanded'] if ft['expanded'] else None,
                'full_wall_s': ft['wall_s'],
                'separator_wall_s': st['wall_s'],
                'wall_delta_s': st['wall_s'] - ft['wall_s'],
                'separator_hits': st['separator_hits'],
                'separator_replay_checks': st['separator_replay_checks'],
                'separator_replay_failures': st['separator_replay_failures'],
                'separator_replay_wall_s': st['separator_replay_wall_s'],
            }
            for label, totals in [('full_boundary', ft), ('separator', st)]:
                agg = aggregate[order][label]
                for k, value in totals.items():
                    agg[k] = agg.get(k, 0) + value
        cases.append({
            'index': index,
            'signature': source_row['signature'],
            'recipe_id': bundle['recipe_id'],
            'process': bundle['public_environment']['terrestrial_process_class'],
            'comparison': comparison,
            'runs': runs,
        })
        print(index + 1, bundle['recipe_id'], comparison, flush=True)

    aggregate_comparison = {}
    for order in ORDERS:
        f = aggregate[order]['full_boundary']
        s = aggregate[order]['separator']
        aggregate_comparison[order] = {
            'full_expanded': f['expanded'],
            'separator_expanded': s['expanded'],
            'expansion_delta': s['expanded'] - f['expanded'],
            'expansion_ratio': s['expanded'] / f['expanded'] if f['expanded'] else None,
            'full_wall_s': f['wall_s'],
            'separator_wall_s': s['wall_s'],
            'wall_delta_s': s['wall_s'] - f['wall_s'],
            'separator_hits': s['separator_hits'],
            'separator_replay_checks': s['separator_replay_checks'],
            'separator_replay_failures': s['separator_replay_failures'],
            'separator_replay_wall_s': s['separator_replay_wall_s'],
        }

    artifact = {
        'schema_version': '0.1',
        'status': 'REPLAY_GATED_SEPARATOR_CACHE_DIAGNOSTIC',
        'inputs_ref': str(args.inputs.relative_to(ROOT)),
        'inputs_sha256': sha256(args.inputs.read_bytes()).hexdigest(),
        'separator': separator_explanation(),
        'all_cell_outcomes_agree': all_agree,
        'all_separator_positive_witnesses_replay': all_replay,
        'aggregate': aggregate,
        'aggregate_comparison': aggregate_comparison,
        'cases': cases,
        'claim_boundary': [
            'The only algorithmic difference is success-certificate lookup through the dependency separator followed by deterministic target-state replay.',
            'Failure certificates never cross a compressed boundary.',
            'Wall time includes separator comparisons and replay checks but remains a small local diagnostic, not a deployment latency claim.',
            'The workload is repeated planning over the twelve frozen corrected-source bundles and their bounded resource rectangles.',
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({
        'all_cell_outcomes_agree': all_agree,
        'all_separator_positive_witnesses_replay': all_replay,
        'aggregate_comparison': aggregate_comparison,
        'out': str(args.out),
    }, ensure_ascii=False, indent=2))
    return 0 if all_agree and all_replay else 1


if __name__ == '__main__':
    raise SystemExit(main())
