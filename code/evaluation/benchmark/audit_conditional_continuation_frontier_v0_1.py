#!/usr/bin/env python3
"""Build conditional continuation frontiers on the frozen retry-review sample."""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from conditional_continuation_frontier_v0_1 import build_conditional_frontier


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUTS = ROOT / 'results/benchmark/layer1-retry-review-inputs.json'
DEFAULT_OUT = ROOT / 'results/benchmark/layer2-conditional-continuation-frontier-v0.1.json'


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inputs', type=Path, default=DEFAULT_INPUTS)
    ap.add_argument('--out', type=Path, default=DEFAULT_OUT)
    ap.add_argument('--max-expansions', type=int, default=200_000)
    args = ap.parse_args()
    frozen = json.loads(args.inputs.read_text(encoding='utf-8'))

    rows = []
    by_gain = Counter()
    by_process_gain = Counter()
    frontier_shapes = Counter()
    for index, source_row in enumerate(frozen['rows']):
        bundle = source_row['bundle']
        frontier = build_conditional_frontier(bundle, max_expansions=args.max_expansions)
        gain = frontier['evidence_gain_type']
        process = bundle['public_environment']['terrestrial_process_class']
        by_gain[gain] += 1
        by_process_gain[f'{process}|{gain}'] += 1
        shape = tuple(
            (x['query_budget'], x['satellite_budget'])
            for x in frontier['frontier_points']
        )
        frontier_shapes[str(shape)] += 1
        rows.append({
            'index': index,
            'signature': source_row['signature'],
            'recipe_id': bundle['recipe_id'],
            'process': process,
            'frontier': frontier,
        })
        print(index + 1, bundle['recipe_id'], gain, shape, frontier['context'], flush=True)

    artifact = {
        'schema_version': '0.1',
        'status': 'FROZEN_SAMPLE_CONDITIONAL_FRONTIER_DIAGNOSTIC',
        'inputs_ref': str(args.inputs.relative_to(ROOT)),
        'inputs_sha256': sha256(args.inputs.read_bytes()).hexdigest(),
        'selection': frozen['selection'],
        'by_evidence_gain_type': dict(sorted(by_gain.items())),
        'by_process_and_gain': dict(sorted(by_process_gain.items())),
        'frontier_shape_count': dict(sorted(frontier_shapes.items())),
        'rows': rows,
        'claim_boundary': [
            'The twelve inputs were selected as paid-evidence-required under the pre-retry corrected-source oracle; this is a semantic diagnostic, not a random sample.',
            'The retry-legality repair is active. Receiver deduplication is not enabled.',
            'Evidence feasibility gain and satellite-resource gain are distinct outcomes.',
            'Absence of resource gain in this sample does not imply absence in the regenerated universe.',
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({
        'by_evidence_gain_type': artifact['by_evidence_gain_type'],
        'by_process_and_gain': artifact['by_process_and_gain'],
        'frontier_shape_count': artifact['frontier_shape_count'],
        'out': str(args.out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
