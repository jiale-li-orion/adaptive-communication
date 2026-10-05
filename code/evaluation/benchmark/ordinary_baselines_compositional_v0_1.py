#!/usr/bin/env python3
"""Ordinary non-learning baselines on the compositional Layer-1 world IR.

These policies are intentionally small and auditable.  They consume the same
service windows, source deadlines, ACK delays, satellite budget and owner-query
capacity as the exact references.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from causal_evidence_process_v0_1 import (
    ACK_TIMEOUT_S,
    FINAL_ACK_DELAY_S,
    QUERY_RESPONSE_DELAY_S,
    attach_causal_evidence,
    gateway_snapshot,
)
from exact_reference_oracle_v0_1 import SATELLITE_COMPLETION_DELAY_S


def _pending(bundle: Mapping[str, Any], delivered: set[str], at_s: int) -> list[Mapping[str, Any]]:
    return sorted(
        [
            o for o in bundle["obligations"]
            if str(o["obligation_id"]) not in delivered
            and int(o["release_s"]) <= at_s <= int(o["deadline_s"])
        ],
        key=lambda o: (int(o["deadline_s"]), int(o["release_s"]), str(o["obligation_id"])),
    )


def _take_terr_window(world: Mapping[str, Any], used: Counter[str], at_s: int) -> Mapping[str, Any] | None:
    candidates = []
    for w in world["terrestrial_windows"]:
        wid = str(w["window_id"])
        if int(w["start_s"]) <= at_s < int(w["end_s"]) and used[wid] < int(w["capacity_units"]):
            candidates.append(w)
    if not candidates:
        return None
    w = min(candidates, key=lambda x: (int(x["end_s"]), str(x["window_id"])))
    used[str(w["window_id"])] += 1
    return w


def _take_sat_window(bundle: Mapping[str, Any], used: Counter[str], at_s: int) -> Mapping[str, Any] | None:
    candidates = []
    for w in bundle["public_environment"]["satellite_windows"]:
        wid = str(w["window_id"])
        if int(w["start_s"]) <= at_s < int(w["end_s"]) and used[wid] < int(w["capacity_units"]):
            candidates.append(w)
    if not candidates:
        return None
    w = min(candidates, key=lambda x: (int(x["end_s"]), str(x["window_id"])))
    used[str(w["window_id"])] += 1
    return w


def _result(bundle: Mapping[str, Any], delivered: dict[str, int], actions: list[dict[str, Any]]) -> dict[str, Any]:
    obligations = {str(o["obligation_id"]): o for o in bundle["obligations"]}
    missing = sorted(set(obligations) - set(delivered))
    late = sorted(
        oid for oid, t in delivered.items() if t > int(obligations[oid]["deadline_s"])
    )
    return {
        "success": not missing and not late,
        "delivered": dict(sorted(delivered.items())),
        "missing": missing,
        "late": late,
        "actions": actions,
    }


def gateway_local_edf_reserve(bundle: Mapping[str, Any], world: Mapping[str, Any]) -> dict[str, Any]:
    """Gateway-local current-state EDF with public-satellite deadline reserve."""
    delivered: dict[str, int] = {}
    terr_used: Counter[str] = Counter()
    sat_used: Counter[str] = Counter()
    sat_budget = int(bundle["public_environment"]["satellite_budget_units"])
    actions: list[dict[str, Any]] = []
    sat_starts = sorted({int(w["start_s"]) for w in bundle["public_environment"]["satellite_windows"]})
    events = sorted(
        {int(o["release_s"]) for o in bundle["obligations"]}
        | {int(w["start_s"]) for w in world["terrestrial_windows"]}
        | set(sat_starts)
    )
    for t in events:
        # Local current-state autonomy can react to a terrestrial service start.
        while True:
            pending = _pending(bundle, set(delivered), t)
            if not pending:
                break
            w = _take_terr_window(world, terr_used, t)
            if w is None:
                break
            o = next((x for x in pending if t + FINAL_ACK_DELAY_S <= int(x["deadline_s"])), None)
            if o is None:
                break
            oid = str(o["obligation_id"])
            delivered[oid] = t + FINAL_ACK_DELAY_S
            actions.append({"at_s": t, "action": "SEND_TERR", "obligation_id": oid})

        if t in sat_starts and sat_budget > 0:
            pending = _pending(bundle, set(delivered), t)
            if not pending:
                continue
            future_sat = [s for s in sat_starts if s > t]
            next_sat = min(future_sat) if future_sat else None
            must = [
                o for o in pending
                if next_sat is None or int(o["deadline_s"]) < next_sat + SATELLITE_COMPLETION_DELAY_S
            ]
            if not must:
                continue
            o = must[0]
            if t + SATELLITE_COMPLETION_DELAY_S > int(o["deadline_s"]):
                continue
            w = _take_sat_window(bundle, sat_used, t)
            if w is None:
                continue
            oid = str(o["obligation_id"])
            delivered[oid] = t + SATELLITE_COMPLETION_DELAY_S
            sat_budget -= 1
            actions.append({"at_s": t, "action": "SEND_SAT", "obligation_id": oid})
    return _result(bundle, delivered, actions)


def blind_satellite_edf(bundle: Mapping[str, Any], world: Mapping[str, Any]) -> dict[str, Any]:
    del world
    delivered: dict[str, int] = {}
    used: Counter[str] = Counter()
    budget = int(bundle["public_environment"]["satellite_budget_units"])
    actions: list[dict[str, Any]] = []
    for t in sorted({int(w["start_s"]) for w in bundle["public_environment"]["satellite_windows"]}):
        if budget <= 0:
            break
        pending = _pending(bundle, set(delivered), t)
        if not pending:
            continue
        o = next((x for x in pending if t + SATELLITE_COMPLETION_DELAY_S <= int(x["deadline_s"])), None)
        if o is None:
            continue
        if _take_sat_window(bundle, used, t) is None:
            continue
        oid = str(o["obligation_id"])
        delivered[oid] = t + SATELLITE_COMPLETION_DELAY_S
        budget -= 1
        actions.append({"at_s": t, "action": "SEND_SAT", "obligation_id": oid})
    return _result(bundle, delivered, actions)


def send_probe_ack_fallback(bundle: Mapping[str, Any], world: Mapping[str, Any]) -> dict[str, Any]:
    """Attempt ordinary terrestrial send at release; use ACK/timeout before fallback."""
    delivered: dict[str, int] = {}
    terr_used: Counter[str] = Counter()
    sat_used: Counter[str] = Counter()
    budget = int(bundle["public_environment"]["satellite_budget_units"])
    failures: list[tuple[int, str]] = []
    actions: list[dict[str, Any]] = []
    obligations = sorted(bundle["obligations"], key=lambda o: (int(o["release_s"]), int(o["deadline_s"])))
    for o in obligations:
        oid = str(o["obligation_id"])
        t = int(o["release_s"])
        w = _take_terr_window(world, terr_used, t)
        actions.append({"at_s": t, "action": "SEND_TERR", "obligation_id": oid})
        if w is not None and t + FINAL_ACK_DELAY_S <= int(o["deadline_s"]):
            delivered[oid] = t + FINAL_ACK_DELAY_S
        else:
            failures.append((t + ACK_TIMEOUT_S, oid))

    sat_starts = sorted({int(w["start_s"]) for w in bundle["public_environment"]["satellite_windows"]})
    by_oid = {str(o["obligation_id"]): o for o in obligations}
    for known_fail_at, oid in sorted(failures, key=lambda x: (x[0], int(by_oid[x[1]]["deadline_s"]))):
        if oid in delivered or budget <= 0:
            continue
        o = by_oid[oid]
        candidates = [
            t for t in sat_starts
            if t >= known_fail_at and t + SATELLITE_COMPLETION_DELAY_S <= int(o["deadline_s"])
        ]
        for t in candidates:
            if _take_sat_window(bundle, sat_used, t) is None:
                continue
            delivered[oid] = t + SATELLITE_COMPLETION_DELAY_S
            budget -= 1
            actions.append({"at_s": t, "action": "SEND_SAT", "obligation_id": oid})
            break
    return _result(bundle, delivered, actions)


def fixed_owner_read_edf(bundle: Mapping[str, Any], world: Mapping[str, Any]) -> dict[str, Any]:
    """One fixed gateway owner read per obligation release, then EDF execution."""
    process = attach_causal_evidence(bundle)
    pm = {str(x["world_id"]): x for x in process["world_owner_processes"]}
    proc_world = pm[str(world["world_id"])]
    delivered: dict[str, int] = {}
    terr_used: Counter[str] = Counter()
    sat_used: Counter[str] = Counter()
    budget = int(bundle["public_environment"]["satellite_budget_units"])
    actions: list[dict[str, Any]] = []
    sat_starts = sorted({int(w["start_s"]) for w in bundle["public_environment"]["satellite_windows"]})
    obligations = sorted(bundle["obligations"], key=lambda o: (int(o["release_s"]), int(o["deadline_s"])))
    for o in obligations:
        oid = str(o["obligation_id"])
        sample = int(o["release_s"])
        # Query pays one real terrestrial capacity unit when reachable.
        qwindow = _take_terr_window(world, terr_used, sample)
        reachable = qwindow is not None
        payload = gateway_snapshot(proc_world, sample) if reachable else None
        arrive = sample + QUERY_RESPONSE_DELAY_S
        actions.append({"at_s": sample, "action": "OWNER_QUERY", "obligation_id": oid})

        attempted = False
        if reachable and payload and bool(payload["terrestrial_available_now"]):
            attempted = True
            w = _take_terr_window(world, terr_used, arrive)
            actions.append({"at_s": arrive, "action": "SEND_TERR", "obligation_id": oid})
            if w is not None and arrive + FINAL_ACK_DELAY_S <= int(o["deadline_s"]):
                delivered[oid] = arrive + FINAL_ACK_DELAY_S
                continue
        fallback_known = arrive + (ACK_TIMEOUT_S if attempted else 0)
        if budget <= 0:
            continue
        for t in sat_starts:
            if t < fallback_known or t + SATELLITE_COMPLETION_DELAY_S > int(o["deadline_s"]):
                continue
            if _take_sat_window(bundle, sat_used, t) is None:
                continue
            delivered[oid] = t + SATELLITE_COMPLETION_DELAY_S
            budget -= 1
            actions.append({"at_s": t, "action": "SEND_SAT", "obligation_id": oid})
            break
    return _result(bundle, delivered, actions)


BASELINES = {
    "gateway_local_edf_reserve": gateway_local_edf_reserve,
    "blind_satellite_edf": blind_satellite_edf,
    "send_probe_ack_fallback": send_probe_ack_fallback,
    "fixed_owner_read_edf": fixed_owner_read_edf,
}

BASELINE_COMPARISON_CONTRACT = {
    "gateway_local_edf_reserve": {
        "placement": "gateway",
        "comparison_role": "DEPLOYMENT_ALTERNATIVE",
        "information_contract": "gateway-local current state + public geometry",
    },
    "blind_satellite_edf": {
        "placement": "same-as-evaluated-policy",
        "comparison_role": "SAME_INFORMATION_SHORTCUT",
        "information_contract": "public geometry + released obligations only",
    },
    "send_probe_ack_fallback": {
        "placement": "same-as-evaluated-policy",
        "comparison_role": "SAME_INFORMATION_SHORTCUT",
        "information_contract": "declared passive ACK / normal-send feedback only",
    },
    "fixed_owner_read_edf": {
        "placement": "same-as-evaluated-policy",
        "comparison_role": "SAME_INFORMATION_SHORTCUT",
        "information_contract": "declared owner-query capability + public state",
    },
}


def audit_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    rows = {}
    regime = str(bundle["observation_projection"]["evidence_regime"])
    legal = {
        "gateway_local_edf_reserve": True,
        "blind_satellite_edf": True,
        "send_probe_ack_fallback": regime in {"PASSIVE_ACK_ONLY", "MIXED_PASSIVE_QUERY_PROBE"},
        "fixed_owner_read_edf": regime in {"GATEWAY_SUMMARY_QUERY", "MIXED_PASSIVE_QUERY_PROBE"},
    }
    for name, fn in BASELINES.items():
        contract = BASELINE_COMPARISON_CONTRACT[name]
        if not legal[name]:
            rows[name] = {
                "legal": False,
                **contract,
                "robust_success": None,
                "world_success_count": None,
                "world_count": len(bundle["worlds"]),
                "per_world": {},
            }
            continue
        per_world = {str(w["world_id"]): fn(bundle, w) for w in bundle["worlds"]}
        rows[name] = {
            "legal": True,
            **contract,
            "robust_success": all(x["success"] for x in per_world.values()),
            "world_success_count": sum(bool(x["success"]) for x in per_world.values()),
            "world_count": len(per_world),
            "per_world": per_world,
        }
    return rows
