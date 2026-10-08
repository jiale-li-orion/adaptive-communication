#!/usr/bin/env python3
"""Task-level future-choice witness on the existing S7/O6 full simulator.

The audit fixes one predeclared NASA POWER dev coordinate and compares an
operationally-authorized warning-profile commitment made at its effective time
versus one hour earlier.  It then removes one mechanism at a time:

* persistent-energy pressure (larger existing battery-capacity regime),
* loss of later access/control opportunity (disable the access outage).

No task surface, action, capability, generator axis, or hidden oracle is added.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


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

from agentic_communication.benchmark_split import WINDOW_START_HOURS  # noqa: E402
from agentic_communication.episodes import (  # noqa: E402
    benchmark_episode_catalog,
    o6_compound_long_horizon_task,
)
from joint_run import run_joint  # noqa: E402


SEED = 0
YEAR = 2023
WINDOW_ID = "w2"
CAPACITY_BINDING_WH = 0.03
CAPACITY_RELAXED_WH = 0.05
NOTICE_LEAD_S = 2 * 3600
PREPARATION_LEAD_S = 3600


def _run(*, prepare: bool, capacity_wh: float, access_outage: bool) -> dict[str, Any]:
    task = o6_compound_long_horizon_task(task_hours=12)
    kw = dict(benchmark_episode_catalog()["O6"].simulator_overrides)
    kw.update(
        {
            "seed": SEED,
            "task_hours": 12,
            "tail_hours": 1,
            "arm": "local",
            "groups": 2,
            "sample_interval_s": 3600,
            "report_period_s": 3600,
            "routine_period_s": 3600,
            "harvest_mode": "irradiance",
            "irradiance_year": YEAR,
            "irradiance_start_hour": WINDOW_START_HOURS[WINDOW_ID],
            "capacity_wh": float(capacity_wh),
            "initial_soc": 1.0,
            "backup_rate_s": 120,
            "backup_bytes": 200,
            "execution_feedback": True,
            "mission_schedule": task.mission_schedule(),
            "mission_mode": "comply",
            "mission_gateway_delegate": True,
            "mission_notice_lead_s": NOTICE_LEAD_S,
            "mission_record_trace": True,
            "mission_preparation_lead_s": PREPARATION_LEAD_S if prepare else 0,
            "mission_preparation_resource_guard": False,
            "collect_rows": True,
        }
    )
    if not access_outage:
        kw["access_outage_hours"] = 0.0
    result, instance, _obligations = run_joint(**kw)
    rows = {
        str(row["oid"]): row
        for row in result["rows"]
        if row.get("kind") == "routine"
    }
    return {
        "result": result,
        "instance": instance,
        "rows": rows,
        "intents": list(instance.intent_log),
        "decision_trace": list(getattr(instance.policy, "decision_trace", [])),
        "node_dead_at": {
            nid: getattr(node, "dead_at", None)
            for nid, node in instance.nodes.items()
        },
    }


def _pair_summary(no_prepare: dict[str, Any], prepare: dict[str, Any]) -> dict[str, Any]:
    a = no_prepare["rows"]
    b = prepare["rows"]
    assert set(a) == set(b)

    gained = []
    lost = []
    for oid in sorted(a):
        left = a[oid]
        right = b[oid]
        row = {
            "oid": oid,
            "node_id": left["node_id"],
            "release_at": left["release_at"],
            "deadline": left["deadline"],
            "no_prepare_collected": left["collected"],
            "no_prepare_delivered": left["delivered"],
            "prepare_collected": right["collected"],
            "prepare_delivered": right["delivered"],
        }
        if (not left["delivered"]) and right["delivered"]:
            gained.append(row)
        elif left["delivered"] and (not right["delivered"]):
            lost.append(row)

    def phase(rows, lo, hi):
        return [row for row in rows if lo <= int(row["release_at"]) < hi]

    early_intents = [
        {"at_s": int(t), "target": str(target), "value": value}
        for t, target, value in prepare["intents"]
        if int(t) < 5 * 3600
    ]
    dead = sorted(
        nid for nid in prepare["result"]["survival"]["dead"]
        if nid in prepare["instance"].nodes
    )
    dead_at = {nid: prepare["node_dead_at"].get(nid) for nid in dead}
    post_lost = phase(lost, 10 * 3600, 12 * 3600)
    return {
        "routine_delivered": {
            "no_prepare": no_prepare["result"]["routine"]["delivered"],
            "prepare": prepare["result"]["routine"]["delivered"],
        },
        "warning_gain_count": len(phase(gained, 5 * 3600, 10 * 3600)),
        "post_warning_loss_count": len(post_lost),
        "post_warning_loss_nodes": sorted({row["node_id"] for row in post_lost}),
        "dead_nodes_after_prepare": dead,
        "dead_at_s": dead_at,
        "first_early_prepare_intent_at_s": min(
            (row["at_s"] for row in early_intents), default=None
        ),
        "early_prepare_intent_count": len(early_intents),
        "warning_gained_obligations": phase(gained, 5 * 3600, 10 * 3600),
        "post_warning_lost_obligations": post_lost,
    }


def main() -> int:
    binding_no = _run(
        prepare=False, capacity_wh=CAPACITY_BINDING_WH, access_outage=True
    )
    binding_prepare = _run(
        prepare=True, capacity_wh=CAPACITY_BINDING_WH, access_outage=True
    )
    relaxed_no = _run(
        prepare=False, capacity_wh=CAPACITY_RELAXED_WH, access_outage=True
    )
    relaxed_prepare = _run(
        prepare=True, capacity_wh=CAPACITY_RELAXED_WH, access_outage=True
    )
    control_no = _run(
        prepare=False, capacity_wh=CAPACITY_BINDING_WH, access_outage=False
    )
    control_prepare = _run(
        prepare=True, capacity_wh=CAPACITY_BINDING_WH, access_outage=False
    )

    binding = _pair_summary(binding_no, binding_prepare)
    energy_relaxed = _pair_summary(relaxed_no, relaxed_prepare)
    control_available = _pair_summary(control_no, control_prepare)
    payload = {
        "stage": "T1_S7_FUTURE_CHOICE_WITNESS",
        "task_surface": "T1.S7_COMPOUND_CONTINUITY",
        "coordinate": {
            "seed": SEED,
            "irradiance_year": YEAR,
            "window_id": WINDOW_ID,
            "irradiance_start_hour": WINDOW_START_HOURS[WINDOW_ID],
            "notice_lead_s": NOTICE_LEAD_S,
            "preparation_lead_s": PREPARATION_LEAD_S,
        },
        "binding": binding,
        "interventions": {
            "energy_relaxed_capacity_0_05": energy_relaxed,
            "later_access_control_available": control_available,
        },
        "mechanism_checks": {
            "binding_has_warning_gain": binding["warning_gain_count"] > 0,
            "binding_has_post_warning_loss": binding["post_warning_loss_count"] > 0,
            "post_warning_loss_overlaps_dead_nodes": bool(
                set(binding["post_warning_loss_nodes"])
                & set(binding["dead_nodes_after_prepare"])
            ),
            "energy_relaxation_reduces_post_warning_loss": (
                energy_relaxed["post_warning_loss_count"]
                < binding["post_warning_loss_count"]
            ),
            "control_availability_reduces_post_warning_loss": (
                control_available["post_warning_loss_count"]
                < binding["post_warning_loss_count"]
            ),
        },
        "claim_boundary": [
            "This is a bounded mechanism witness on an existing S7/O6 task, not a benchmark distribution claim.",
            "The dense target is external-authority task state; the policy only chooses when to install it.",
            "The witness is useful only if the early commitment gains warning obligations while losing later monitoring obligations, and the loss weakens under mechanism-removing interventions.",
            "No new fallback quota, cache pressure, tool, or generator family is introduced.",
        ],
    }
    out = ROOT / "local_research/current/benchmark/t1-s7-future-choice-witness.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"out": str(out), **payload["mechanism_checks"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
