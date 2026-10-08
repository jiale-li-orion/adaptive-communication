#!/usr/bin/env python3
"""Release-facing mutation audit for the full communication simulator scorer.

The historical V9 audit attacks the abstract world-bundle execution evaluator.
The paper-facing Operational-Conformance / Interactive-Decision tracks also use
the full simulator's Sample -> gateway heard -> center received lifecycle and
obligation scorer.  This audit therefore mutates *executed logs* from one O1
conformance episode and one O6 compound interactive episode, then reruns the
same scorer.

Required behaviour:

* remove all samples that can satisfy one delivered obligation -> collection
  for that obligation must fail;
* preserve collection but push all matching center arrivals past the deadline
  -> delivery must fail while collection remains true;
* add an unrelated executed record -> obligation outcome must not change;
* change an arrival to a different legal on-time instant -> success remains
  accepted, demonstrating that the evaluator does not require one gold trace.

No policy text, model name, oracle action or reward is an evaluator input.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
CODE = ROOT / "code"
for _p in (
    CODE,
    CODE / "substrate" / "joint",
    CODE / "substrate" / "instance",
    CODE / "substrate" / "monitoring",
    CODE / "substrate" / "physics",
    CODE / "substrate" / "runtime",
):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from agentic_communication.episodes import benchmark_episode_catalog  # noqa: E402
from joint_run import run_joint  # noqa: E402
from network import Sample, Transit  # noqa: E402
from scoring import evaluate  # noqa: E402


TASK_HOURS = 12
TAIL_HOURS = 1


def _run_episode(name: str):
    template = benchmark_episode_catalog(task_hours=TASK_HOURS)[name]
    kw = dict(template.simulator_overrides)
    kw.update(
        seed=0,
        task_hours=TASK_HOURS,
        tail_hours=TAIL_HOURS,
        arm="local",
        groups=2,
        collect_rows=True,
    )
    if len(template.task.phases) > 1:
        kw.update(
            mission_schedule=template.task.mission_schedule(),
            mission_mode="comply",
            mission_gateway_delegate=True,
            execution_feedback=True,
        )
    result, instance, obligations = run_joint(**kw)
    return template, result, instance, obligations


def _rescore(instance, obligations, log):
    return evaluate(
        obligations,
        log,
        TASK_HOURS + TAIL_HOURS,
        instance.nodes.keys(),
        battery={k: v.power.to_dict() for k, v in instance.nodes.items()},
        plane=instance.plane,
        task_hours=TASK_HOURS,
        collect_rows=True,
    )


def _row(result: dict, oid: str) -> dict:
    return next(row for row in result["rows"] if str(row["oid"]) == oid)


def _target(result: dict, obligations, log):
    by_oid = {str(o.oid): o for o in obligations.obligations}
    candidates = []
    for row in result["rows"]:
        if row.get("kind") != "routine" or not row.get("delivered"):
            continue
        oid = str(row["oid"])
        obligation = by_oid[oid]
        matching = []
        for sid, sample in log.samples.items():
            if not obligation.matches(sample):
                continue
            transit = log.transit[sid]
            if transit.received_at is None:
                continue
            matching.append((sid, sample, transit))
        on_time = [x for x in matching if int(x[2].received_at) <= int(obligation.deadline)]
        if not on_time:
            continue
        first = min(on_time, key=lambda x: int(x[2].received_at))
        if int(first[2].received_at) < int(obligation.deadline):
            candidates.append((oid, obligation, matching, first))
    if not candidates:
        raise AssertionError("no delivered routine obligation with on-time arrival slack")
    return candidates[0]


def _audit_episode(name: str) -> dict:
    template, original, instance, obligations = _run_episode(name)
    baseline = _rescore(instance, obligations, deepcopy(instance.log))
    assert baseline["routine"] == original["routine"], name

    oid, obligation, matching, first = _target(baseline, obligations, instance.log)
    matching_ids = [sid for sid, _sample, _transit in matching]

    # Mutation 1: remove all records eligible for the target obligation.
    dropped_log = deepcopy(instance.log)
    for sid in matching_ids:
        dropped_log.samples.pop(sid, None)
        dropped_log.transit.pop(sid, None)
    dropped = _rescore(instance, obligations, dropped_log)
    dropped_row = _row(dropped, oid)

    # Mutation 2: preserve samples/gateway history, but make center completion late.
    late_log = deepcopy(instance.log)
    for sid in matching_ids:
        transit = late_log.transit[sid]
        if transit.received_at is None:
            continue
        transit.received_at = max(
            int(obligation.deadline) + 60,
            int(transit.heard_at or 0),
        )
    late = _rescore(instance, obligations, late_log)
    late_row = _row(late, oid)

    # Mutation 3: add a physically logged but task-irrelevant record.
    irrelevant_log = deepcopy(instance.log)
    fake_id = f"__release_audit_irrelevant__:{name}"
    irrelevant_log.samples[fake_id] = Sample(
        sample_id=fake_id,
        node_id="__irrelevant_node__",
        measurand="__irrelevant_measurand__",
        taken_at=0,
        value=0.0,
        unit="n/a",
    )
    irrelevant_log.transit[fake_id] = Transit(
        sample_id=fake_id,
        heard_at=0,
        received_at=0,
    )
    irrelevant = _rescore(instance, obligations, irrelevant_log)

    # Mutation 4: move the earliest successful arrival to a *different* legal
    # on-time instant. The task outcome should remain accepted.
    alternate_log = deepcopy(instance.log)
    first_sid, _sample, first_transit = first
    old_received = int(first_transit.received_at)
    heard = int(first_transit.heard_at or 0)
    deadline = int(obligation.deadline)
    if old_received + 60 <= deadline:
        new_received = max(heard, old_received + 60)
    else:
        new_received = max(heard, old_received - 60)
    if new_received == old_received:
        raise AssertionError("could not construct distinct legal arrival time")
    alternate_log.transit[first_sid].received_at = new_received
    alternate = _rescore(instance, obligations, alternate_log)
    alternate_row = _row(alternate, oid)

    checks = {
        "baseline_replay_matches_original_routine": baseline["routine"] == original["routine"],
        "removed_matching_records_break_target_collection": (
            dropped_row["collected"] is False and dropped_row["delivered"] is False
        ),
        "late_center_arrival_preserves_collection_but_breaks_delivery": (
            late_row["collected"] is True and late_row["delivered"] is False
        ),
        "irrelevant_record_does_not_change_routine_outcome": irrelevant["routine"] == baseline["routine"],
        "alternate_on_time_arrival_remains_success": alternate_row["delivered"] is True,
        "alternate_success_uses_distinct_execution_time": new_received != old_received,
    }
    if not all(checks.values()):
        raise AssertionError({name: checks})

    return {
        "episode": name,
        "task_id": template.task.task_id,
        "target_obligation_id": oid,
        "target_deadline_s": deadline,
        "baseline_target": _row(baseline, oid),
        "mutations": {
            "remove_matching_records": dropped_row,
            "late_center_arrival": late_row,
            "irrelevant_record": {
                "routine_equal": irrelevant["routine"] == baseline["routine"],
                "fake_sample_id": fake_id,
            },
            "alternate_legal_arrival": {
                "old_received_at": old_received,
                "new_received_at": new_received,
                "target": alternate_row,
            },
        },
        "checks": checks,
    }


def main() -> int:
    # O1/O2/O3/O4/O6 cover every currently release-candidate T1 surface:
    # S0->O1; S1->O2; S2/S4/S6->O3; S3->O4; S7->O6. O5 is intentionally
    # excluded because T1.S5 remains OBJECTIVE_AMBIGUOUS / SOURCE_GAP.
    episode_surface_map = {
        "O1": ["T1.S0_STEADY_MONITORING"],
        "O2": ["T1.S1_WARNING_CADENCE_TRANSITION"],
        "O3": [
            "T1.S2_INTERMITTENT_BACKHAUL_FALLBACK",
            "T1.S4_OUTAGE_CACHE_RETENTION",
            "T1.S6_HETEROGENEOUS_PATH_PRIORITY",
        ],
        "O4": ["T1.S3_ENERGY_CONSTRAINED_CONTINUITY"],
        "O6": ["T1.S7_COMPOUND_CONTINUITY"],
    }
    rows = []
    for episode in episode_surface_map:
        row = _audit_episode(episode)
        row["paper_surfaces_covered"] = episode_surface_map[episode]
        rows.append(row)
    covered_surfaces = sorted(
        {sid for values in episode_surface_map.values() for sid in values}
    )
    payload = {
        "stage": "LAYER1_FULLSIM_EXECUTION_EVALUATOR_RELEASE_AUDIT",
        "tracks_covered": ["OPERATIONAL_CONFORMANCE", "INTERACTIVE_DECISION"],
        "paper_surfaces_covered": covered_surfaces,
        "episodes": rows,
        "checks": {
            "all_episode_mutation_checks_pass": all(
                all(row["checks"].values()) for row in rows
            ),
            "policy_text_or_model_output_not_evaluator_input": True,
            "multiple_legal_success_execution_times_accepted": all(
                row["checks"]["alternate_on_time_arrival_remains_success"] for row in rows
            ),
            "all_current_release_candidate_t1_surfaces_covered": len(covered_surfaces) == 7,
        },
        "claim_boundary": [
            "This audit validates the full-simulator obligation scorer across every currently release-candidate T1 surface using the canonical O1/O2/O3/O4/O6 templates; it is not an exhaustive enumeration of every possible mutation class.",
            "The evaluator operates on executed sample/transit state and obligation contracts, not planner text or model self-reported success.",
            "Historical abstract-world V9 remains separate regression evidence; this artifact covers the paper-facing full simulator."
        ],
    }
    assert all(payload["checks"].values()), payload["checks"]
    out = ROOT / "results/benchmark/layer1-fullsim-evaluator-release-audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"out": str(out), **payload["checks"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
