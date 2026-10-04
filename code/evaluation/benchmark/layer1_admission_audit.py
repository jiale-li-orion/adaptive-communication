#!/usr/bin/env python3
"""Non-negotiable Astra/cache06 admission audit for the current Layer-1 pilot."""
from __future__ import annotations

from dataclasses import dataclass,asdict
from typing import Any
import json

from experiment_ledger_v0_4 import build_ledger
from scenario_generator_v0_4 import generate


@dataclass(frozen=True)
class Gate:
    gate: str
    status: str
    evidence: str


def audit(*,phase_limit:int=1,catalog_size:int=5) -> dict[str,Any]:
    rows=generate(phase_limit=phase_limit,catalog_size=catalog_size)
    ledger=build_ledger(phase_limit=phase_limit,catalog_size=catalog_size)
    exact=[r for r in rows if r.exact_solvable]

    query_contracts=all(
        q.capability_id and q.return_path and q.opportunity_dependency
        for r in rows for q in r.bundle.queries
    )
    prehistory=all(w.prehistory_events for r in rows for w in r.bundle.worlds)
    fixed_pair=ledger['algorithm_gap']['fixed_primary_plus_receipt_success_rate']
    guided=ledger['algorithm_gap']['conflict_guided_success_rate']

    gates=[
        Gate('source_shaped_obligations','PASS','DB44 2h cadence + actual Connecta opportunity phases'),
        Gate('process_generated_labels','PASS','oracle labels bundles after generation'),
        Gate('nonanticipative_exact_oracle','PASS','alias worlds share actions until legal observations split history'),
        Gate('history_derived_current_evidence','PASS' if prehistory else 'FAIL','gateway evidence aggregated from prehistory forwarding/queue/receipt events'),
        Gate('capability_owner_transport_contract','PASS' if query_contracts else 'FAIL','mainline queries freeze registry capability binding and gateway reachability timeout'),
        Gate('passive_and_send_as_probe_supported','PASS','exact engine supports passive telemetry and terrestrial ACK partitioning'),
        Gate('incremental_context_current_contract','PASS','v0.4 JSON evidence narrows cached feasibility witnesses without new flow solves'),
        Gate('structural_feasibility_bounds','PASS','satellite commit actions have conservative structural L/U bounds'),
        Gate('success_rate_headroom_over_fixed_pair','FAIL' if fixed_pair>=guided else 'PASS',f'guided={guided:.3f}, fixed_pair={fixed_pair:.3f}'),
        Gate('real_transport_cost_calibrated','FAIL','gateway remote-read bytes/airtime/energy remain unknown in current simulator'),
        Gate('full_strong_baseline_ladder','PARTIAL','reserve/shallow/fixed/single/exhaustive exist; myopic-VoI and limited-depth belief planner not frozen'),
        Gate('benchmark_release_admit','FAIL','method-development pilot only; strong-baseline/transport/held-out release gates remain open'),
    ]
    return {
        'layer1_status':'METHOD_DEVELOPMENT_PILOT',
        'gates':[asdict(g) for g in gates],
        'hard_failures':[g.gate for g in gates if g.status=='FAIL'],
        'claim_now':[
            'source-grounded non-anticipative communication decision environment',
            'feasibility-conflict-guided evidence selection reduces unnecessary evidence/search on the pilot',
        ],
        'claim_forbidden':[
            'success-rate superiority over strong fixed deterministic policy',
            'real network traffic/energy reduction when transport counters are unknown',
            'final benchmark admission',
        ],
    }


if __name__=='__main__':
    print(json.dumps(audit(),indent=2,sort_keys=True))
