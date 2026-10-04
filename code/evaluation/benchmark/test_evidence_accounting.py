#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))
if str(ROOT/'code') not in sys.path:
    sys.path.insert(0,str(ROOT/'code'))

from agentic_communication.capabilities import CommunicationCapabilityCatalog
from agentic_communication.contracts import CommunicationEvidence, EvidenceStatus
from evidence_accounting import (
    EvidenceCostClass,
    EvidenceLedger,
    FreshnessRequirement,
    PlannerComputationCharge,
    classify_observation,
    freshness_state,
    next_context_expiry,
)


def main() -> int:
    catalog=CommunicationCapabilityCatalog()
    binding=catalog.binding('communication.gateway.primary_health')

    center=classify_observation(binding=binding,planner_location='center')
    gateway=classify_observation(binding=binding,planner_location='gateway')
    assert center.cost_class==EvidenceCostClass.REMOTE_ACQUISITION
    assert center.transport_cost_unknown
    assert gateway.cost_class==EvidenceCostClass.LOCAL_CONTEXT
    assert not gateway.transport_cost_unknown

    ev=CommunicationEvidence(
        evidence_id='e1',
        proposition='communication.gateway.node_report',
        subject_ref='n0',
        value={'alive':True},
        source_id='test',
        source_role='gateway',
        owner_location='gateway',
        generated_at_s=100,
        observed_at_s=120,
        world_revision=1,
        status=EvidenceStatus.CURRENT,
    )
    req=FreshnessRequirement(
        proposition=ev.proposition,
        subject_ref='n0',
        max_age_s=60,
        basis='generated_at_s',
    )
    assert freshness_state(ev,at_s=160,requirement=req).fresh
    assert not freshness_state(ev,at_s=161,requirement=req).fresh
    assert next_context_expiry([ev],[req],at_s=150)==161

    ledger=EvidenceLedger()
    ledger.add_evidence_charge(center)
    ledger.add_evidence_charge(gateway)
    ledger.add_computation(PlannerComputationCharge(
        subset_solves=3,preprocessing_solves=6,memo_nodes=100,context_bytes=512,planner_calls=1
    ))
    summary=ledger.summary()
    assert summary['local_context']['read_count']==1
    assert summary['remote_acquisition']['request_count']==1
    assert summary['remote_acquisition']['unknown_transport_cost_count']==1
    assert summary['planner_computation']['memo_nodes']==100

    print('PASS evidence accounting: owner-relative locality, freshness expiry and planner computation remain separate ledgers')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
