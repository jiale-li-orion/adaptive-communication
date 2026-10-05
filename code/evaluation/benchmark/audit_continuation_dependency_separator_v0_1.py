#!/usr/bin/env python3
"""Natural-state collision audit for the continuation dependency separator.

The collector observes states reached by the real continuation search.  It does
not manufacture state pairs.  Distinct full histories with equal separator and
resource coordinates are independently re-solved; successful witnesses are
cross-replayed before any reuse credit is counted.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter
from typing import Any

from causal_evidence_process_v0_1 import attach_causal_evidence
from continuation_dependency_separator_v0_1 import DependencySeparator, separator_explanation
from continuation_resource_domains_v0_1 import ContinuationPlanner, verify_witness
from exact_reference_oracle_v0_1 import LocalState, _attempt_lattice


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUTS = ROOT / 'results/benchmark/layer1-retry-review-inputs.json'
DEFAULT_OUT = ROOT / 'results/benchmark/layer2-continuation-dependency-separator-v0.1.json'


def _full_key(t: int, states: dict[str, LocalState], q: int):
    return (t, q, tuple(sorted(states.items())))


def _budget(states: dict[str, LocalState]) -> int:
    values = {st.satellite_budget for st in states.values()}
    if len(values) != 1:
        raise ValueError('non-shared satellite budget in observed support')
    return next(iter(values))


def _has_removed_history(bundle, process, t: int, states: dict[str, LocalState]) -> bool:
    sat_past = {
        str(w['window_id']) for w in bundle['public_environment']['satellite_windows']
        if int(w['end_s']) <= t
    }
    world_map = {str(w['world_id']): w for w in bundle['worlds']}
    passive = bool(process.get('passive_observation_rules'))
    direct = bool(process.get('direct_observation'))
    for wid, st in states.items():
        terr_past = {
            str(w['window_id']) for w in world_map[str(wid)]['terrestrial_windows']
            if int(w['end_s']) <= t
        }
        if any(str(k) in terr_past for k, _ in st.terrestrial_used):
            return True
        if any(str(k) in sat_past for k, _ in st.satellite_used):
            return True
        if not direct and st.last_direct_signature is not None:
            return True
        if not passive and any(d.gateway_receipt_seen for d in st.pending_deliveries):
            return True
    return False


class Collector:
    def __init__(self, bundle, *, max_pairs: int):
        self.bundle = bundle
        self.process = attach_causal_evidence(bundle)
        self.projector = DependencySeparator(bundle, self.process)
        self.max_pairs = max_pairs
        self.first: dict[Any, tuple[Any, int, dict[str, LocalState], int]] = {}
        self.pairs: list[dict[str, Any]] = []
        self.seen_pair_digests: set[tuple[str, str]] = set()
        self.observed = 0
        self.removable_history_observed = 0

    def __call__(self, t: int, states: dict[str, LocalState], q: int):
        self.observed += 1
        removable = _has_removed_history(self.bundle, self.process, t, states)
        self.removable_history_observed += int(removable)
        b = _budget(states)
        sep = (self.projector.key(t, states), q, b)
        full = _full_key(t, states, q)
        full_digest = sha256(repr(full).encode()).hexdigest()
        old = self.first.get(sep)
        if old is None:
            self.first[sep] = (full, t, deepcopy(states), q)
            return
        old_full, old_t, old_states, old_q = old
        if old_full == full or len(self.pairs) >= self.max_pairs:
            return
        old_digest = sha256(repr(old_full).encode()).hexdigest()
        pair_digest = tuple(sorted((old_digest, full_digest)))
        if pair_digest in self.seen_pair_digests:
            return
        self.seen_pair_digests.add(pair_digest)
        self.pairs.append({
            'time_s': t,
            'query_budget': q,
            'satellite_budget': b,
            'left': deepcopy(old_states),
            'right': deepcopy(states),
            'left_full_sha256': old_digest,
            'right_full_sha256': full_digest,
            'left_has_removed_history': _has_removed_history(self.bundle, self.process, old_t, old_states),
            'right_has_removed_history': removable,
        })


def _cells(bundle):
    qmax = len(bundle['obligations'])
    bmax = int(bundle['public_environment']['satellite_budget_units'])
    return sorted(
        ((q, b) for q in range(qmax + 1) for b in range(bmax + 1)),
        key=lambda x: (x[0], x[1]),
    )


def _initial(bundle, b: int):
    return {str(w['world_id']): LocalState(satellite_budget=b) for w in bundle['worlds']}


def _solve_fresh(bundle, t, states, q, max_expansions):
    planner = ContinuationPlanner(bundle, mode='exact_memo')
    return planner.solve(t, deepcopy(states), query_budget=q, max_expansions=max_expansions)


def _pair_audit(bundle, pair, max_expansions):
    left = _solve_fresh(bundle, pair['time_s'], pair['left'], pair['query_budget'], max_expansions)
    right = _solve_fresh(bundle, pair['time_s'], pair['right'], pair['query_budget'], max_expansions)
    same_outcome = (left['status'], left['solvable']) == (right['status'], right['solvable'])
    cross = {'left_to_right': None, 'right_to_left': None}
    replay_wall_s = 0.0
    if left['solvable'] is True:
        started = perf_counter()
        try:
            actual = verify_witness(
                bundle, pair['time_s'], deepcopy(pair['right']), left['policy'],
                query_budget=pair['query_budget'],
            )
            cross['left_to_right'] = {'passed': True, 'requirement': actual}
        except Exception as exc:
            cross['left_to_right'] = {'passed': False, 'error': f'{type(exc).__name__}: {exc}'}
        replay_wall_s += perf_counter() - started
    if right['solvable'] is True:
        started = perf_counter()
        try:
            actual = verify_witness(
                bundle, pair['time_s'], deepcopy(pair['left']), right['policy'],
                query_budget=pair['query_budget'],
            )
            cross['right_to_left'] = {'passed': True, 'requirement': actual}
        except Exception as exc:
            cross['right_to_left'] = {'passed': False, 'error': f'{type(exc).__name__}: {exc}'}
        replay_wall_s += perf_counter() - started
    successful_cross = [x for x in cross.values() if x is not None]
    cross_ok = all(x['passed'] for x in successful_cross)
    saved_expansions_if_left_reused = (
        right['metrics']['expanded']
        if left['solvable'] is True and cross['left_to_right'] and cross['left_to_right']['passed']
        else 0
    )
    return {
        'same_exact_outcome': same_outcome,
        'left': {k: left[k] for k in ('status', 'solvable', 'requirement', 'metrics')},
        'right': {k: right[k] for k in ('status', 'solvable', 'requirement', 'metrics')},
        'cross_replay': cross,
        'cross_replay_passed': cross_ok,
        'cross_replay_wall_s': replay_wall_s,
        'saved_expansions_if_left_certificate_reused': saved_expansions_if_left_reused,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inputs', type=Path, default=DEFAULT_INPUTS)
    ap.add_argument('--out', type=Path, default=DEFAULT_OUT)
    ap.add_argument('--max-pairs-per-bundle', type=int, default=6)
    ap.add_argument('--max-expansions', type=int, default=200_000)
    args = ap.parse_args()
    frozen = json.loads(args.inputs.read_text(encoding='utf-8'))

    cases = []
    total_pairs = 0
    all_outcomes = True
    all_cross = True
    saved_expansions = 0
    for index, source_row in enumerate(frozen['rows']):
        bundle = source_row['bundle']
        collector = Collector(bundle, max_pairs=args.max_pairs_per_bundle)
        planner = ContinuationPlanner(bundle, mode='exact_memo', observer=collector)
        for q, b in _cells(bundle):
            planner.solve(
                min(_attempt_lattice(bundle)), _initial(bundle, b), query_budget=q,
                max_expansions=args.max_expansions,
            )
        audited = []
        for pair in collector.pairs:
            result = _pair_audit(bundle, pair, args.max_expansions)
            all_outcomes = all_outcomes and result['same_exact_outcome']
            all_cross = all_cross and result['cross_replay_passed']
            saved_expansions += int(result['saved_expansions_if_left_certificate_reused'])
            audited.append({
                'time_s': pair['time_s'],
                'query_budget': pair['query_budget'],
                'satellite_budget': pair['satellite_budget'],
                'left_full_sha256': pair['left_full_sha256'],
                'right_full_sha256': pair['right_full_sha256'],
                'left_has_removed_history': pair['left_has_removed_history'],
                'right_has_removed_history': pair['right_has_removed_history'],
                'audit': result,
            })
        total_pairs += len(audited)
        cases.append({
            'index': index,
            'signature': source_row['signature'],
            'recipe_id': bundle['recipe_id'],
            'process': bundle['public_environment']['terrestrial_process_class'],
            'observed_search_boundaries': collector.observed,
            'boundaries_with_removable_history': collector.removable_history_observed,
            'natural_separator_collision_count': len(collector.pairs),
            'audited_pairs': audited,
        })
        print(index + 1, bundle['recipe_id'], 'observed', collector.observed,
              'removable', collector.removable_history_observed,
              'collisions', len(collector.pairs), flush=True)

    artifact = {
        'schema_version': '0.1',
        'status': 'NATURAL_STATE_SEPARATOR_DIAGNOSTIC',
        'inputs_ref': str(args.inputs.relative_to(ROOT)),
        'inputs_sha256': sha256(args.inputs.read_bytes()).hexdigest(),
        'separator': separator_explanation(),
        'natural_collision_pair_count': total_pairs,
        'all_collision_exact_outcomes_agree': all_outcomes,
        'all_successful_cross_replays_pass': all_cross,
        'potential_saved_expansions_on_audited_left_to_right_reuse': saved_expansions,
        'reuse_rule': 'Only successful causal witnesses are eligible for cross-full-boundary reuse and must replay under the target state before acceptance; failure certificates are not transferred in v0.1.',
        'cases': cases,
        'claim_boundary': [
            'Only naturally reached search states count toward collision/reuse opportunity.',
            'A collision demonstrates state compression opportunity, not deployment-frequency prevalence.',
            'Replay-gated success reuse is a correctness mechanism; wall-time benefit must count replay cost.',
            'No failure certificate is transferred across compressed boundaries in this version.',
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True, default=str) + '\n', encoding='utf-8')
    print(json.dumps({
        'natural_collision_pair_count': total_pairs,
        'all_collision_exact_outcomes_agree': all_outcomes,
        'all_successful_cross_replays_pass': all_cross,
        'potential_saved_expansions': saved_expansions,
        'out': str(args.out),
    }, ensure_ascii=False, indent=2))
    return 0 if all_outcomes and all_cross else 1


if __name__ == '__main__':
    raise SystemExit(main())
