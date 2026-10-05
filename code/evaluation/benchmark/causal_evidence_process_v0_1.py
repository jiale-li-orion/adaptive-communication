#!/usr/bin/env python3
"""Attach a causal observation/evidence process to Layer-1 world bundles.

This stage owns *how information can legally arrive*.  It does not solve the
worlds.  Query responses sample owner state at ``sampled_at_s`` and are only
visible at ``arrived_at_s``; passive ACKs exist only after an executed send;
normal send-as-probe is the ordinary send action, not a synthetic oracle tool.

The process intentionally exposes current/past owner facts only.  Future
service windows remain evaluator truth and never appear in a query payload.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from typing import Any, Iterable, Mapping
import json

from dynamic_world_materializer_v0_1 import iter_world_bundles


QUERY_RESPONSE_DELAY_S = 60
QUERY_TIMEOUT_S = 60
GATEWAY_RECEIPT_DELAY_S = 10
FINAL_ACK_DELAY_S = 30
ACK_TIMEOUT_S = 60
SATELLITE_COMPLETION_DELAY_S = 5


class CausalEvidenceError(ValueError):
    pass


def _digest(payload: Any, n: int = 16) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()[:n]


def _merge_intervals(windows: Iterable[Mapping[str, Any]]) -> list[tuple[int, int]]:
    rows = sorted((int(w["start_s"]), int(w["end_s"])) for w in windows)
    out: list[list[int]] = []
    for start, end in rows:
        if end <= start:
            raise CausalEvidenceError("service window must have positive duration")
        if not out or start > out[-1][1]:
            out.append([start, end])
        else:
            out[-1][1] = max(out[-1][1], end)
    return [(a, b) for a, b in out]


def _availability_events(intervals: list[tuple[int, int]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for start, end in intervals:
        events.append({"at_s": start, "proposition": "terrestrial_available_now", "value": True})
        events.append({"at_s": end, "proposition": "terrestrial_available_now", "value": False})
    return sorted(events, key=lambda x: (int(x["at_s"]), not bool(x["value"])))


def _world_process(world: Mapping[str, Any]) -> dict[str, Any]:
    intervals = _merge_intervals(world.get("terrestrial_windows", []))
    return {
        "world_id": str(world["world_id"]),
        "owner": "communication_subsystem",
        "proposition": "communication.gateway.state_summary",
        "terrestrial_intervals": [[a, b] for a, b in intervals],
        "owner_state_events": _availability_events(intervals),
        "future_state_visibility": "EVALUATOR_ONLY",
    }


def attach_causal_evidence(world_bundle: Mapping[str, Any]) -> dict[str, Any]:
    if world_bundle.get("stage") != "WORLD_BUNDLE_PRE_EVIDENCE_PRE_ORACLE":
        raise CausalEvidenceError("causal process requires a world-materialized parent")
    regime = str(world_bundle["observation_projection"]["evidence_regime"])
    surfaces = list(world_bundle["observation_projection"].get("evidence_surfaces", []))
    surface_kinds = {str(x["kind"]) for x in surfaces}

    queries: list[dict[str, Any]] = []
    if "OWNER_QUERY" in surface_kinds:
        queries.append(
            {
                "query_id": "gateway_state_summary",
                "capability_id": "remote_state_read",
                "owner": "monitoring_center",
                "sample_delay_s": 0,
                "response_delay_s": QUERY_RESPONSE_DELAY_S,
                "timeout_s": QUERY_TIMEOUT_S,
                "required_path": "TERRESTRIAL_HIGHER_PRIORITY_AGGREGATE",
                "resource_cost": {"terrestrial_window_capacity_units": 1},
                "timing_provenance": "CONTROLLED_STRESS",
                "payload_rule": "current/past gateway state only; no future window or plan label",
            }
        )

    passive_rules: list[dict[str, Any]] = []
    if "PASSIVE_ACK" in surface_kinds or "NORMAL_SEND_AS_PROBE" in surface_kinds:
        passive_rules.append(
            {
                "evidence_id": "delivery_ack",
                "trigger": "EXECUTED_TERRESTRIAL_SEND",
                "gateway_receipt_delay_s": GATEWAY_RECEIPT_DELAY_S,
                "final_ack_delay_s": FINAL_ACK_DELAY_S,
                "negative_observation_after_s": ACK_TIMEOUT_S,
                "timing_provenance": "CONTROLLED_STRESS",
                "rule": "no send => no receipt evidence; accepted send and final completion remain distinct events",
            }
        )

    probe_rules: list[dict[str, Any]] = []
    if "NORMAL_SEND_AS_PROBE" in surface_kinds:
        probe_rules.append(
            {
                "evidence_id": "normal_send_probe",
                "action": "SEND_TERR",
                "extra_tool": False,
                "resource_cost": "same delivery capacity consumed by the executed report",
                "observation": "delivery_ack_or_timeout",
            }
        )

    direct = regime == "FULL_OBSERVATION_CONTROL"
    process_payload = {
        "parent_bundle_id": world_bundle["bundle_id"],
        "regime": regime,
        "world_ids": [w["world_id"] for w in world_bundle["worlds"]],
        "query_ids": [q["query_id"] for q in queries],
    }
    process = {
        "schema_version": "0.1",
        "process_id": f"T1E-{_digest(process_payload)}",
        "parent_bundle_id": str(world_bundle["bundle_id"]),
        "recipe_id": str(world_bundle["recipe_id"]),
        "stage": "CAUSAL_EVIDENCE_PRE_ORACLE",
        "evidence_regime": regime,
        "direct_observation": direct,
        "query_capabilities": queries,
        "passive_observation_rules": passive_rules,
        "normal_send_probe_rules": probe_rules,
        "world_owner_processes": [_world_process(w) for w in world_bundle["worlds"]],
        "history_contract": {
            "non_anticipative": True,
            "query_sample_precedes_or_equals_arrival": True,
            "query_payload_future_fields_forbidden": [
                "future_window_count",
                "next_window_start_s",
                "future_delivery_success",
                "recommended_action",
                "world_id",
            ],
            "gateway_receipt_is_final_completion": False,
            "same_observable_history_same_action_required": True,
        },
        "resource_contract": {
            "query_uses_real_opportunity": bool(queries),
            "query_capacity_units": 1 if queries else 0,
            "send_as_probe_has_extra_cost": False,
            "passive_ack_has_acquisition_cost": False,
        },
        "release_status": "NOT_BENCHMARK_ADMIT",
        "next_stage": "EXACT_ORACLE_REFERENCE_LABELS",
    }
    validate_causal_process(world_bundle, process)
    return process


def _process_by_world(process: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(x["world_id"]): x for x in process["world_owner_processes"]}


def _available_now(world_process: Mapping[str, Any], at_s: int) -> bool:
    return any(int(a) <= at_s < int(b) for a, b in world_process["terrestrial_intervals"])


def gateway_snapshot(world_process: Mapping[str, Any], sampled_at_s: int) -> dict[str, Any]:
    """Return only current/past owner facts at the exact sample time."""
    intervals = [(int(a), int(b)) for a, b in world_process["terrestrial_intervals"]]
    started = [(a, b) for a, b in intervals if a <= sampled_at_s]
    completed = [(a, b) for a, b in intervals if b <= sampled_at_s]
    last_end = max((b for _a, b in completed), default=None)
    return {
        "terrestrial_available_now": _available_now(world_process, sampled_at_s),
        "started_window_count": len(started),
        "completed_window_count": len(completed),
        "last_window_end_age_s": None if last_end is None else sampled_at_s - last_end,
    }


def issue_gateway_query(
    process: Mapping[str, Any],
    *,
    world_id: str,
    issue_at_s: int,
) -> dict[str, Any]:
    queries = list(process.get("query_capabilities", []))
    if not queries:
        raise CausalEvidenceError("gateway query is not legal in this evidence regime")
    q = queries[0]
    sampled_at = issue_at_s + int(q["sample_delay_s"])
    world = _process_by_world(process).get(world_id)
    if world is None:
        raise CausalEvidenceError(f"unknown world {world_id}")
    reachable = _available_now(world, sampled_at)
    arrived_at = sampled_at + int(q["response_delay_s"] if reachable else q["timeout_s"])
    return {
        "kind": "QUERY_RESPONSE" if reachable else "QUERY_TIMEOUT",
        "query_id": str(q["query_id"]),
        "sampled_at_s": sampled_at,
        "arrived_at_s": arrived_at,
        "payload": gateway_snapshot(world, sampled_at) if reachable else None,
    }


def _obligation(world_bundle: Mapping[str, Any], obligation_id: str) -> Mapping[str, Any]:
    for o in world_bundle["obligations"]:
        if str(o["obligation_id"]) == obligation_id:
            return o
    raise CausalEvidenceError(f"unknown obligation {obligation_id}")


def terrestrial_send_observation(
    world_bundle: Mapping[str, Any],
    process: Mapping[str, Any],
    *,
    world_id: str,
    obligation_id: str,
    send_at_s: int,
    consumed_by_window: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Evaluate one actually executed SEND_TERR and its later observable result."""
    consumed = consumed_by_window or {}
    obligation = _obligation(world_bundle, obligation_id)
    if not (int(obligation["release_s"]) <= send_at_s <= int(obligation["deadline_s"])):
        raise CausalEvidenceError("send must target an active obligation")
    world = next((w for w in world_bundle["worlds"] if str(w["world_id"]) == world_id), None)
    if world is None:
        raise CausalEvidenceError(f"unknown world {world_id}")
    candidates = []
    for w in world["terrestrial_windows"]:
        if int(w["start_s"]) <= send_at_s < int(w["end_s"]):
            used = int(consumed.get(str(w["window_id"]), 0))
            if used < int(w["capacity_units"]):
                candidates.append(w)
    if candidates:
        chosen = min(candidates, key=lambda w: (int(w["end_s"]), str(w["window_id"])))
        return {
            "kind": "SEND_ACCEPTED",
            "obligation_id": obligation_id,
            "send_at_s": send_at_s,
            "capacity_window_id": str(chosen["window_id"]),
            "gateway_receipt_at_s": send_at_s + GATEWAY_RECEIPT_DELAY_S,
            "final_ack_at_s": send_at_s + FINAL_ACK_DELAY_S,
            "negative_observation_at_s": None,
        }
    return {
        "kind": "SEND_NOT_ACCEPTED",
        "obligation_id": obligation_id,
        "send_at_s": send_at_s,
        "capacity_window_id": None,
        "gateway_receipt_at_s": None,
        "final_ack_at_s": None,
        "negative_observation_at_s": send_at_s + ACK_TIMEOUT_S,
    }


def validate_causal_process(world_bundle: Mapping[str, Any], process: Mapping[str, Any]) -> None:
    if process.get("stage") != "CAUSAL_EVIDENCE_PRE_ORACLE":
        raise CausalEvidenceError("wrong causal process stage")
    if process.get("parent_bundle_id") != world_bundle.get("bundle_id"):
        raise CausalEvidenceError("causal process parent mismatch")
    if process.get("release_status") != "NOT_BENCHMARK_ADMIT":
        raise CausalEvidenceError("causal process must not claim benchmark admission")
    parent_world_ids = [str(w["world_id"]) for w in world_bundle["worlds"]]
    process_world_ids = [str(w["world_id"]) for w in process["world_owner_processes"]]
    if parent_world_ids != process_world_ids:
        raise CausalEvidenceError("causal process world support drift")
    direct = bool(process["direct_observation"])
    if direct and process["query_capabilities"]:
        raise CausalEvidenceError("full observation control must not add owner queries")
    for q in process["query_capabilities"]:
        if int(q["sample_delay_s"]) < 0 or int(q["response_delay_s"]) < 0:
            raise CausalEvidenceError("query timing must be causal")
        if "future" in str(q["payload_rule"]).lower() and "no future" not in str(q["payload_rule"]).lower():
            raise CausalEvidenceError("query payload rule may not expose future truth")


def iter_causal_processes(
    bundles: Iterable[Mapping[str, Any]] | None = None,
) -> Iterable[dict[str, Any]]:
    source = iter_world_bundles() if bundles is None else bundles
    for bundle in source:
        yield attach_causal_evidence(bundle)


def causal_process_manifest() -> dict[str, Any]:
    count = 0
    by_regime: Counter[str] = Counter()
    by_query_count: Counter[int] = Counter()
    by_passive: Counter[bool] = Counter()
    digest = sha256()
    for process in iter_causal_processes():
        count += 1
        by_regime[str(process["evidence_regime"])] += 1
        by_query_count[len(process["query_capabilities"])] += 1
        by_passive[bool(process["passive_observation_rules"])] += 1
        digest.update(str(process["process_id"]).encode("ascii"))
        digest.update(b"\n")
    return {
        "schema_version": "0.1",
        "process": "T1-causal-observation-evidence-v0.1",
        "stage": "CAUSAL_EVIDENCE_PRE_ORACLE",
        "parent_bundle_count": count,
        "process_count": count,
        "process_id_stream_sha256": digest.hexdigest(),
        "by_evidence_regime": dict(sorted(by_regime.items())),
        "by_query_capability_count": {str(k): v for k, v in sorted(by_query_count.items())},
        "by_passive_ack_enabled": {str(k).lower(): v for k, v in sorted(by_passive.items())},
        "timing_contract": {
            "query_response_delay_s": QUERY_RESPONSE_DELAY_S,
            "query_timeout_s": QUERY_TIMEOUT_S,
            "gateway_receipt_delay_s": GATEWAY_RECEIPT_DELAY_S,
            "final_ack_delay_s": FINAL_ACK_DELAY_S,
            "ack_timeout_s": ACK_TIMEOUT_S,
            "satellite_completion_delay_s": SATELLITE_COMPLETION_DELAY_S,
            "provenance": "CONTROLLED_STRESS",
        },
        "rules": [
            "Queries sample current owner state before response arrival; later world changes cannot rewrite the sampled value.",
            "Query payloads contain current/past gateway facts only and never future service windows, plan labels or world ids.",
            "Passive delivery evidence exists only after an executed send.",
            "Gateway receipt and final completion ACK remain separate events.",
            "Normal send-as-probe is the ordinary SEND_TERR action and pays no extra synthetic tool cost.",
            "Owner query consumes one declared terrestrial opportunity-capacity unit; passive ACK is acquisition-free.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(causal_process_manifest(), ensure_ascii=False, indent=2, sort_keys=True))
