#!/usr/bin/env python3
"""Bounded comparison of exact memo vs resource-domain continuation caches.

This is a method diagnostic on the twelve frozen corrected-source bundles from
the retry-semantics review.  It does not relabel Layer 1 and does not claim a
benchmark-wide speedup.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from continuation_resource_domains_v0_1 import ContinuationPlanner, MODES, verify_witness
from exact_reference_oracle_v0_1 import LocalState, _attempt_lattice
from materialize_exact_labels_v0_1 import SOLVER_VERSION


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUTS = ROOT / 'results/benchmark/layer1-retry-review-inputs.json'
DEFAULT_OUT = ROOT / 'results/benchmark/layer2-continuation-resource-domains-v0.1.json'
ORDERS = ('rich_to_poor', 'poor_to_rich')


def _cells(bundle: dict[str, Any], order: str) -> list[tuple[int, int]]:
    qmax = len(bundle['obligations'])
    bmax = int(bundle['public_environment']['satellite_budget_units'])
    cells = [(q, b) for q in range(qmax + 1) for b in range(bmax + 1)]
    if order == 'rich_to_poor':
        return sorted(cells, key=lambda x: (-x[0], -x[1]))
    if order == 'poor_to_rich':
        return sorted(cells, key=lambda x: (x[0], x[1]))
    raise ValueError(order)


def _initial_states(bundle: dict[str, Any], satellite_budget: int) -> dict[str, LocalState]:
    return {
        str(world['world_id']): LocalState(satellite_budget=satellite_budget)
        for world in bundle['worlds']
    }


def _sum_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = (
        'expanded', 'recursive_calls', 'exact_hits', 'domain_hits',
        'negative_domain_hits', 'domain_comparisons', 'wall_s',
    )
    out = {k: sum(float(r['metrics'][k]) for r in rows) for k in keys}
    for k in keys[:-1]:
        out[k] = int(out[k])
    out['zero_expansion_cells'] = sum(int(r['metrics']['expanded'] == 0) for r in rows)
    out['domain_reuse_cells'] = sum(
        int(r['metrics']['domain_hits'] > 0 or r['metrics']['negative_domain_hits'] > 0)
        for r in rows
    )
    out['solvable_cells'] = sum(int(r['solvable'] is True) for r in rows)
    out['unsolvable_cells'] = sum(int(r['solvable'] is False) for r in rows)
    out['search_limit_cells'] = sum(int(r['status'] == 'SEARCH_LIMIT') for r in rows)
    return out


def _run_mode(bundle: dict[str, Any], mode: str, order: str, max_expansions: int) -> dict[str, Any]:
    planner = ContinuationPlanner(bundle, mode=mode)
    start = min(_attempt_lattice(bundle))
    rows = []
    replay_failures = []
    requirement_slack = []
    for q, b in _cells(bundle, order):
        states = _initial_states(bundle, b)
        result = planner.solve(start, states, query_budget=q, max_expansions=max_expansions)
        row = {
            'query_budget': q,
            'satellite_budget': b,
            'status': result['status'],
            'solvable': result['solvable'],
            'requirement': result['requirement'],
            'metrics': result['metrics'],
        }
        if result['solvable'] is True:
            try:
                actual = verify_witness(
                    bundle, start, states, result['policy'], query_budget=q,
                )
                row['replay_requirement'] = actual
                if result['requirement'] != actual:
                    replay_failures.append({
                        'cell': [q, b],
                        'kind': 'DECLARED_REQUIREMENT_MISMATCH',
                        'declared': result['requirement'],
                        'replayed': actual,
                    })
                requirement_slack.append({
                    'query_slack': q - actual[0],
                    'satellite_slack': b - actual[1],
                })
            except Exception as exc:  # diagnostic artifact must preserve the failure
                replay_failures.append({
                    'cell': [q, b], 'kind': 'REPLAY_EXCEPTION',
                    'error': f'{type(exc).__name__}: {exc}',
                })
        rows.append(row)
    total = _sum_metrics(rows)
    total['max_query_slack_on_success'] = max((r['query_slack'] for r in requirement_slack), default=0)
    total['max_satellite_slack_on_success'] = max((r['satellite_slack'] for r in requirement_slack), default=0)
    return {
        'mode': mode,
        'order': order,
        'cell_count': len(rows),
        'totals': total,
        'replay_failure_count': len(replay_failures),
        'replay_failures': replay_failures,
        'cells': rows,
    }


def _outcome_map(run: dict[str, Any]) -> dict[tuple[int, int], tuple[str, bool | None]]:
    return {
        (int(r['query_budget']), int(r['satellite_budget'])): (str(r['status']), r['solvable'])
        for r in run['cells']
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inputs', type=Path, default=DEFAULT_INPUTS)
    ap.add_argument('--out', type=Path, default=DEFAULT_OUT)
    ap.add_argument('--max-expansions', type=int, default=200_000)
    args = ap.parse_args()

    frozen = json.loads(args.inputs.read_text(encoding='utf-8'))
    case_rows = []
    aggregate = defaultdict(Counter)
    all_agree = True
    all_replay = True

    for index, source_row in enumerate(frozen['rows']):
        bundle = source_row['bundle']
        runs = {}
        for order in ORDERS:
            for mode in MODES:
                run = _run_mode(bundle, mode, order, args.max_expansions)
                runs[f'{order}|{mode}'] = run
                all_replay = all_replay and run['replay_failure_count'] == 0

        reference = _outcome_map(runs['rich_to_poor|exact_memo'])
        disagreements = []
        for name, run in runs.items():
            observed = _outcome_map(run)
            if observed != reference:
                all_agree = False
                for cell in sorted(set(reference) | set(observed)):
                    if reference.get(cell) != observed.get(cell):
                        disagreements.append({
                            'run': name, 'cell': list(cell),
                            'reference': reference.get(cell),
                            'observed': observed.get(cell),
                        })

        comparison = {}
        for order in ORDERS:
            exact = runs[f'{order}|exact_memo']['totals']
            mono = runs[f'{order}|monotone_memo']['totals']
            witness = runs[f'{order}|witness_domain']['totals']
            comparison[order] = {
                'expanded': {
                    'exact_memo': exact['expanded'],
                    'monotone_memo': mono['expanded'],
                    'witness_domain': witness['expanded'],
                },
                'witness_vs_exact_expansion_delta': witness['expanded'] - exact['expanded'],
                'witness_vs_monotone_expansion_delta': witness['expanded'] - mono['expanded'],
                'witness_domain_reuse_cells': witness['domain_reuse_cells'],
                'monotone_domain_reuse_cells': mono['domain_reuse_cells'],
                'witness_zero_expansion_cells': witness['zero_expansion_cells'],
                'monotone_zero_expansion_cells': mono['zero_expansion_cells'],
            }
            for mode, totals in [('exact_memo', exact), ('monotone_memo', mono), ('witness_domain', witness)]:
                key = f'{order}|{mode}'
                aggregate[key]['expanded'] += totals['expanded']
                aggregate[key]['recursive_calls'] += totals['recursive_calls']
                aggregate[key]['domain_reuse_cells'] += totals['domain_reuse_cells']
                aggregate[key]['zero_expansion_cells'] += totals['zero_expansion_cells']
                aggregate[key]['cell_count'] += runs[key]['cell_count']

        case_rows.append({
            'index': index,
            'signature': source_row['signature'],
            'recipe_id': bundle['recipe_id'],
            'process': bundle['public_environment']['terrestrial_process_class'],
            'evidence_regime': bundle['observation_projection']['evidence_regime'],
            'obligation_count': len(bundle['obligations']),
            'max_satellite_budget': int(bundle['public_environment']['satellite_budget_units']),
            'outcome_agreement': not disagreements,
            'disagreements': disagreements,
            'comparison': comparison,
            'runs': runs,
        })
        print(index + 1, bundle['recipe_id'], comparison, flush=True)

    aggregate_rendered = {}
    for key, counts in sorted(aggregate.items()):
        aggregate_rendered[key] = dict(counts)
    for order in ORDERS:
        e = aggregate_rendered[f'{order}|exact_memo']['expanded']
        m = aggregate_rendered[f'{order}|monotone_memo']['expanded']
        w = aggregate_rendered[f'{order}|witness_domain']['expanded']
        aggregate_rendered[f'{order}|comparison'] = {
            'witness_vs_exact_expansion_delta': w - e,
            'witness_vs_monotone_expansion_delta': w - m,
            'witness_vs_exact_expansion_ratio': (w / e) if e else None,
            'witness_vs_monotone_expansion_ratio': (w / m) if m else None,
        }

    artifact = {
        'schema_version': '0.1',
        'status': 'BOUNDED_METHOD_DIAGNOSTIC',
        'layer': 'LAYER2_METHOD_PROTOTYPE',
        'solver_version': SOLVER_VERSION,
        'inputs_ref': str(args.inputs.relative_to(ROOT)),
        'inputs_sha256': sha256(args.inputs.read_bytes()).hexdigest(),
        'selection': frozen['selection'],
        'resource_rectangle_rule': 'Q=0..obligation_count; B=0..bundle source-generated satellite budget',
        'orders': list(ORDERS),
        'modes': list(MODES),
        'all_cell_outcomes_agree': all_agree,
        'all_positive_witnesses_replay': all_replay,
        'aggregate': aggregate_rendered,
        'cases': case_rows,
        'claim_boundary': [
            'Measures repeated continuation queries over resource budgets at an unchanged causal boundary.',
            'witness_domain stores the actual resource use of the first found causal witness; it is an inner success domain, not a Pareto-minimum frontier.',
            'No result here establishes benchmark-wide online speedup, held-out generalization, or deployment benefit.',
            'Any gain over monotone_memo is the incremental value of witness-tightened success domains under the same action ordering.',
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({
        'all_cell_outcomes_agree': all_agree,
        'all_positive_witnesses_replay': all_replay,
        'aggregate': aggregate_rendered,
        'out': str(args.out),
    }, ensure_ascii=False, indent=2))
    return 0 if all_agree and all_replay else 1


if __name__ == '__main__':
    raise SystemExit(main())
