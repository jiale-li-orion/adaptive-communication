#!/usr/bin/env python3
"""Ordinary deadline-aware reserve baseline for Generator v0.1 candidates.

Policy:
- terrestrial recovered: send pending reports EDF over terrestrial;
- before recovery: use satellite only for released reports whose deadline is
  strictly before terrestrial recovery; otherwise reserve satellite budget;
- satellite service uses the same frozen geometry trace and upper-envelope
  semantics as the generator.

This is intentionally simple and non-learning. It is a shortcut/baseline audit.
"""
from __future__ import annotations

from bisect import bisect_left
from collections.abc import Mapping
from pathlib import Path
from typing import Any
import json

from scenario_generator_v0_1 import BENCH, PROFILE_DIR, ROOT, _trace_slots


def _load(path: Path) -> Any:
    return json.loads(path.read_text())


def run_deadline_reserve(
    candidate: Mapping[str, Any],
    *,
    trace_payload: Mapping[str, Any],
) -> dict[str, Any]:
    obligations = [dict(x) for x in candidate["obligations"]]
    pending = {o["obligation_id"]: o for o in obligations}
    delivered: dict[str, dict[str, Any]] = {}

    c = candidate["coordinates"]
    recovery = int(candidate["terrestrial_recovery_s"])
    budget = int(c["satellite_tx_budget_count"])
    mask = int(c["elevation_mask_deg"])
    step = int(trace_payload["step_s"])
    horizon = max(int(o["deadline_s"]) for o in obligations)

    sat = [
        t for t in _trace_slots(trace_payload, mask)
        if int(c["scenario_start_s"]) <= t <= horizon
    ]
    terr = list(range(
        int((recovery + step - 1) // step) * step,
        horizon + 1,
        step,
    ))

    events = sorted(set(sat) | set(terr))
    sat_set = set(sat)
    terr_set = set(terr)

    for t in events:
        # Remove already impossible obligations only at final accounting; they
        # remain pending so the policy cannot silently drop failures.
        available = [
            o for o in pending.values()
            if int(o["release_s"]) <= t <= int(o["deadline_s"])
        ]

        if t in terr_set and available:
            o = min(available, key=lambda x: (int(x["deadline_s"]), int(x["release_s"]), x["obligation_id"]))
            oid = o["obligation_id"]
            delivered[oid] = {"path": "terrestrial", "delivery_s": t}
            pending.pop(oid, None)
            available = [
                x for x in pending.values()
                if int(x["release_s"]) <= t <= int(x["deadline_s"])
            ]

        if t in sat_set and budget > 0 and available:
            must_sat = [
                o for o in available
                if int(o["deadline_s"]) < recovery
            ]
            if must_sat:
                o = min(must_sat, key=lambda x: (int(x["deadline_s"]), int(x["release_s"]), x["obligation_id"]))
                oid = o["obligation_id"]
                delivered[oid] = {"path": "satellite", "delivery_s": t}
                pending.pop(oid, None)
                budget -= 1

    success = len(delivered) == len(obligations) and all(
        int(o["release_s"]) <= int(delivered[o["obligation_id"]]["delivery_s"]) <= int(o["deadline_s"])
        for o in obligations
        if o["obligation_id"] in delivered
    )
    return {
        "success": success,
        "delivered_count": len(delivered),
        "obligation_count": len(obligations),
        "satellite_budget_remaining": budget,
        "deliveries": delivered,
        "undelivered": sorted(pending),
    }


def main() -> int:
    trace_registry = _load(PROFILE_DIR / "TRACE-PROFILE-REGISTRY.v0.1.json")
    trace = next(
        x for x in trace_registry["profiles"]
        if x["trace_profile_id"] == "CONNECTA_20260922_SIHUI_GEOMETRY_48H"
    )
    trace_payload = _load(ROOT / trace["trace_ref"])
    hard_path = ROOT / "local_research/current/benchmark/generated/scenario-generator-v0.1/hard-candidates.jsonl"
    rows = [json.loads(x) for x in hard_path.read_text().splitlines() if x]

    passed = 0
    for row in rows:
        if run_deadline_reserve(row, trace_payload=trace_payload)["success"]:
            passed += 1
    print(json.dumps({
        "baseline": "deadline_aware_reserve_edf",
        "hard_candidates": len(rows),
        "success_count": passed,
        "success_rate": passed / len(rows) if rows else None,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
