#!/usr/bin/env python3
"""Evaluator-only selective-preparation headroom for the S7 future-choice witness.

This audit does not implement the proposed method.  It asks a narrower question:
is there *any* action-selection headroom between the existing all-or-nothing
ordinary rules?

On the frozen bounded witness coordinate, the full early-preparation arm reveals
six nodes whose one-hour-early persistent densification later destroys two
post-warning obligations each.  The evaluator-only oracle prepares every other
node at h4, while those six wait until the authorized yellow phase actually
becomes effective at h5.  All nodes return to the blue profile at h10.

The hindsight node set is explicitly evaluator-only and may never be used as a
policy input.  Its sole purpose is to measure whether a selective policy could,
in principle, dominate the coarse comply/sustain/resource-guard trade-off.
"""
from __future__ import annotations

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

from agentic_communication.benchmark_split import WINDOW_START_HOURS  # noqa: E402
from agentic_communication.episodes import (  # noqa: E402
    benchmark_episode_catalog,
    o6_compound_long_horizon_task,
)
from center import (  # noqa: E402
    CenterPolicy,
    OP_SET_REPORT_PERIOD,
    OP_SET_SAMPLING_INTERVAL,
)
from joint_run import run_joint  # noqa: E402


BOUND_UNSAFE_EARLY = frozenset({"n00", "n01", "n03", "n04", "n07", "n15"})
H4 = 4 * 3600
H5 = 5 * 3600
H10 = 10 * 3600


class HindsightSelectivePreparationPolicy(CenterPolicy):
    """Evaluator-only upper bound; the unsafe node set is hidden-truth hindsight."""

    name = "oracle-selective-preparation"

    def __init__(self) -> None:
        super().__init__()
        self._last_target: dict[str, tuple[int, int]] = {}

    @staticmethod
    def _target(nid: str, t_s: int) -> tuple[int, int]:
        if t_s < H4:
            return 3600, 3600
        if t_s < H5:
            return (3600, 3600) if nid in BOUND_UNSAFE_EARLY else (300, 300)
        if t_s < H10:
            return 300, 300
        return 3600, 3600

    def plan(self, view):
        out = []
        for nid in view.node_ids:
            target = self._target(nid, int(view.t_s))
            snap = view.reports.get(nid) or {}
            current = (
                int(snap.get("sample_interval_s") or 3600),
                int(snap.get("report_period_s") or 3600),
            )
            if current == target:
                continue
            if nid in view.in_flight:
                continue
            if self._last_target.get(nid) == target:
                # The normal runtime already handles retries/confirmation; this
                # upper bound only needs one generation per intended target.
                continue
            self._last_target[nid] = target
            a, b = self.stamp_pair(
                nid,
                {"op": OP_SET_SAMPLING_INTERVAL, "interval_s": target[0]},
                {"op": OP_SET_REPORT_PERIOD, "period_s": target[1]},
            )
            out.extend(((nid, a), (nid, b)))
        return out


def _base_kwargs():
    task = o6_compound_long_horizon_task(task_hours=12)
    kw = dict(benchmark_episode_catalog()["O6"].simulator_overrides)
    kw.update(
        {
            "seed": 0,
            "task_hours": 12,
            "tail_hours": 1,
            "arm": "local",
            "groups": 2,
            "sample_interval_s": 3600,
            "report_period_s": 3600,
            "routine_period_s": 3600,
            "harvest_mode": "irradiance",
            "irradiance_year": 2023,
            "irradiance_start_hour": WINDOW_START_HOURS["w2"],
            "capacity_wh": 0.03,
            "initial_soc": 1.0,
            "backup_rate_s": 120,
            "backup_bytes": 200,
            "execution_feedback": True,
            "mission_schedule": task.mission_schedule(),
            "mission_notice_lead_s": 2 * 3600,
            "collect_rows": True,
        }
    )
    return task, kw


def _phase(result, lo: int, hi: int) -> dict:
    rows = [
        row for row in result["rows"]
        if row.get("kind") == "routine" and lo <= int(row["release_at"]) < hi
    ]
    return {
        "n": len(rows),
        "delivered": sum(bool(row["delivered"]) for row in rows),
        "missing_collection": sum(not bool(row["collected"]) for row in rows),
    }


def _summary(result) -> dict:
    return {
        "routine_delivered": result["routine"]["delivered"],
        "warning": _phase(result, H5, H10),
        "post_warning": _phase(result, H10, 12 * 3600),
        "dead_nodes": list(result["survival"]["dead"]),
        "mean_final_soc": result["survival"]["mean_final_soc"],
        "commands_sent": result["command_counters"]["commands_sent"],
        "commands_delivered": result["command_counters"]["commands_delivered"],
    }


def main() -> int:
    task, base = _base_kwargs()

    # Existing all-early comply arm.
    full_kw = dict(base)
    full_kw.update(
        {
            "mission_mode": "comply",
            "mission_gateway_delegate": True,
            "mission_preparation_lead_s": 3600,
            "mission_preparation_resource_guard": False,
        }
    )
    full, _inst, _obs = run_joint(**full_kw)

    # Existing coarse protective arm.
    safe_kw = dict(base)
    safe_kw.update(
        {
            "mission_mode": "sustain",
            "mission_gateway_delegate": True,
            "mission_preparation_lead_s": 3600,
            "mission_preparation_resource_guard": False,
        }
    )
    sustain, _inst, _obs = run_joint(**safe_kw)

    # Evaluator-only selective upper bound.  The policy is placed at the gateway
    # like the compared delegated preparation arm; scorer obligations remain the
    # complete O6 task because mission_scope is untouched.
    oracle_kw = dict(base)
    oracle_kw.update(
        {
            "mission_policy_obj": HindsightSelectivePreparationPolicy(),
            "mission_policy_placement": "gateway",
        }
    )
    oracle, _inst, _obs = run_joint(**oracle_kw)

    rows = {
        "all_early_comply": _summary(full),
        "sustain": _summary(sustain),
        "hindsight_selective_upper_bound": _summary(oracle),
    }
    upper = rows["hindsight_selective_upper_bound"]
    payload = {
        "stage": "T1_S7_SELECTIVE_PREPARATION_HEADROOM",
        "task_surface": "T1.S7_COMPOUND_CONTINUITY",
        "coordinate": "2023-w2/seed0/capacity0.03",
        "hindsight_unsafe_early_nodes": sorted(BOUND_UNSAFE_EARLY),
        "rows": rows,
        "checks": {
            "task_denominator_equal": len({row["warning"]["n"] for row in rows.values()}) == 1,
            "upper_bound_preserves_post_warning_continuity": (
                upper["post_warning"]["missing_collection"] == 0
                and len(upper["dead_nodes"]) == 0
            ),
            "upper_bound_improves_warning_over_sustain": (
                upper["warning"]["delivered"] > rows["sustain"]["warning"]["delivered"]
            ),
            "upper_bound_improves_post_warning_over_all_early": (
                upper["post_warning"]["delivered"]
                > rows["all_early_comply"]["post_warning"]["delivered"]
            ),
        },
        "claim_boundary": [
            "The selective node set is evaluator-only hindsight and is not a deployable policy.",
            "The audit measures action-selection headroom only; it does not validate the Layer-2 method.",
            "Task obligations, source schedule, physical dynamics, placement and scorer are unchanged across arms.",
            "A failed upper bound would reject this task as a future-choice method target even if the coarse baselines trade off.",
        ],
    }
    out = ROOT / "local_research/current/benchmark/t1-s7-selective-preparation-headroom.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"out": str(out), **payload["checks"], "rows": rows}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
