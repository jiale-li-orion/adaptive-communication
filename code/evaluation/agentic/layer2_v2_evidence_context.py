#!/usr/bin/env python3
"""Versioned evidence ledger and model-facing context graph for Layer-2 v2.

Layer-1 owns causal evidence arrival.  This module owns the Layer-2 context
semantics required by ``cache06.md``:

* evidence keeps proposition/subject/owner/sample/arrival/request/version;
* query issue and response are distinct events;
* historical facts are never deleted merely because they are old;
* a past gateway-state snapshot can become stale for *current inference* while
  remaining an immutable historical record;
* timeout is an observed timeout, not a fabricated remote fact;
* newer versions dominate current inference without erasing older history.

No future hidden service-window identity is materialized on the model-facing
surface.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from typing import Any, Iterable, Mapping

from causal_evidence_process_v0_1 import QUERY_RESPONSE_DELAY_S
from layer2_v2_conflict_frontier import ConflictFrontierSnapshot, IncrementalConflictFrontier


GATEWAY_QUERY_ID = "gateway_state_summary"
GATEWAY_PROPOSITION = "communication.gateway.state_summary"


@dataclass(frozen=True)
class PendingEvidenceRequest:
    request_id: str
    query_id: str
    proposition: str
    subject: str
    owner: str
    sampled_at_s: int
    expected_arrive_at_s: int
    version: int


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    proposition: str
    subject: str
    owner: str
    value: Any
    outcome: str
    sampled_at_s: int
    arrived_at_s: int
    request_id: str
    version: int
    historical_fact: bool


def _query_observation_parts(observation: str) -> tuple[str, int] | None:
    prefix = f"query:{GATEWAY_QUERY_ID}="
    if not observation.startswith(prefix) or ":sampled@" not in observation:
        return None
    value, sample = observation[len(prefix):].rsplit(":sampled@", 1)
    return value, int(sample)


class EvidenceLedger:
    """Persistent legal-history evidence state, cloneable across AND/OR branches."""

    def __init__(self) -> None:
        self._request_counter = 0
        self._version_by_key: dict[tuple[str, str], int] = {}
        self._pending: list[PendingEvidenceRequest] = []
        self._records: list[EvidenceRecord] = []

    def clone(self) -> "EvidenceLedger":
        return deepcopy(self)

    @property
    def records(self) -> tuple[EvidenceRecord, ...]:
        return tuple(self._records)

    @property
    def pending(self) -> tuple[PendingEvidenceRequest, ...]:
        return tuple(self._pending)

    def _next_version(self, proposition: str, subject: str) -> int:
        key = (proposition, subject)
        value = self._version_by_key.get(key, 0) + 1
        self._version_by_key[key] = value
        return value

    def issue_gateway_query(self, *, issue_at_s: int) -> PendingEvidenceRequest:
        if any(row.query_id == GATEWAY_QUERY_ID for row in self._pending):
            raise ValueError("gateway query already pending")
        self._request_counter += 1
        version = self._next_version(GATEWAY_PROPOSITION, "gateway")
        row = PendingEvidenceRequest(
            request_id=f"{GATEWAY_QUERY_ID}:request:{self._request_counter:04d}",
            query_id=GATEWAY_QUERY_ID,
            proposition=GATEWAY_PROPOSITION,
            subject="gateway",
            owner="communication_subsystem",
            sampled_at_s=int(issue_at_s),
            expected_arrive_at_s=int(issue_at_s) + QUERY_RESPONSE_DELAY_S,
            version=version,
        )
        self._pending.append(row)
        return row

    def _pending_query(self, sampled_at_s: int) -> PendingEvidenceRequest:
        rows = [
            row
            for row in self._pending
            if row.query_id == GATEWAY_QUERY_ID and row.sampled_at_s == int(sampled_at_s)
        ]
        if len(rows) != 1:
            raise ValueError(
                f"query response sampled@{sampled_at_s} has {len(rows)} matching pending requests"
            )
        return rows[0]

    def _append(
        self,
        *,
        proposition: str,
        subject: str,
        owner: str,
        value: Any,
        outcome: str,
        sampled_at_s: int,
        arrived_at_s: int,
        request_id: str,
        version: int | None = None,
        historical_fact: bool,
    ) -> EvidenceRecord:
        if arrived_at_s < sampled_at_s:
            raise ValueError("evidence arrival precedes sampling")
        if version is None:
            version = self._next_version(proposition, subject)
        row = EvidenceRecord(
            evidence_id=f"evidence:{proposition}:{subject}:v{version}:{sampled_at_s}:{arrived_at_s}",
            proposition=proposition,
            subject=subject,
            owner=owner,
            value=value,
            outcome=outcome,
            sampled_at_s=int(sampled_at_s),
            arrived_at_s=int(arrived_at_s),
            request_id=request_id,
            version=int(version),
            historical_fact=bool(historical_fact),
        )
        self._records.append(row)
        return row

    def apply_observation_key(self, observation_key: str, *, arrived_at_s: int) -> list[EvidenceRecord]:
        """Apply one normalized Layer-1 observation branch to the ledger."""

        if observation_key == "same":
            return []
        added: list[EvidenceRecord] = []
        for observation in observation_key.split("|"):
            query = _query_observation_parts(observation)
            if query is not None:
                raw_value, sampled_at_s = query
                request = self._pending_query(sampled_at_s)
                if arrived_at_s < request.expected_arrive_at_s:
                    raise ValueError("query response arrived before declared delay")
                if raw_value == "__TIMEOUT__":
                    value = None
                    outcome = "TIMEOUT"
                else:
                    value = json.loads(raw_value)
                    outcome = "RESPONSE"
                added.append(
                    self._append(
                        proposition=request.proposition,
                        subject=request.subject,
                        owner=request.owner,
                        value=value,
                        outcome=outcome,
                        sampled_at_s=request.sampled_at_s,
                        arrived_at_s=arrived_at_s,
                        request_id=request.request_id,
                        version=request.version,
                        historical_fact=True,
                    )
                )
                self._pending.remove(request)
                continue

            if observation.startswith("gateway_receipt:") and observation.endswith(":ok"):
                oid = observation[len("gateway_receipt:"):-len(":ok")]
                added.append(
                    self._append(
                        proposition="delivery.gateway_receipt",
                        subject=oid,
                        owner="gateway",
                        value="received",
                        outcome="OBSERVED",
                        sampled_at_s=arrived_at_s,
                        arrived_at_s=arrived_at_s,
                        request_id=f"passive:gateway_receipt:{oid}:{arrived_at_s}",
                        historical_fact=True,
                    )
                )
                continue

            if observation.startswith("final_ack:"):
                payload = observation[len("final_ack:"):]
                oid, status = payload.rsplit(":", 1)
                value = "delivered" if status == "ok" else "ack_timeout_observed"
                added.append(
                    self._append(
                        proposition="delivery.final_ack",
                        subject=oid,
                        owner="monitoring_center",
                        value=value,
                        outcome="OBSERVED" if status == "ok" else "TIMEOUT",
                        sampled_at_s=arrived_at_s,
                        arrived_at_s=arrived_at_s,
                        request_id=f"passive:final_ack:{oid}:{arrived_at_s}",
                        historical_fact=True,
                    )
                )
                continue

            if observation.startswith("direct_current_state="):
                added.append(
                    self._append(
                        proposition="communication.direct_current_state",
                        subject="communication_subsystem",
                        owner="communication_subsystem",
                        value=observation.split("=", 1)[1],
                        outcome="DIRECT_OBSERVATION",
                        sampled_at_s=arrived_at_s,
                        arrived_at_s=arrived_at_s,
                        request_id=f"direct:{arrived_at_s}",
                        historical_fact=True,
                    )
                )
                continue

            raise ValueError(f"unsupported Layer-1 observation for evidence ledger: {observation}")
        return added

    def view(self, *, at_s: int) -> dict[str, Any]:
        """Return history + current-inference support without deleting stale facts."""

        latest: dict[tuple[str, str], EvidenceRecord] = {}
        for row in self._records:
            if row.arrived_at_s > at_s:
                continue
            key = (row.proposition, row.subject)
            old = latest.get(key)
            if old is None or (row.version, row.sampled_at_s, row.arrived_at_s) > (
                old.version,
                old.sampled_at_s,
                old.arrived_at_s,
            ):
                latest[key] = row

        nodes = []
        for row in self._records:
            if row.arrived_at_s > at_s:
                continue
            is_latest = latest.get((row.proposition, row.subject)) == row
            if row.proposition == GATEWAY_PROPOSITION:
                if row.outcome == "TIMEOUT":
                    inference = "UNRESOLVED_TIMEOUT"
                elif is_latest and row.sampled_at_s == at_s:
                    inference = "CURRENT_AT_SAMPLE"
                elif is_latest:
                    inference = "STALE_FOR_CURRENT_STATE"
                else:
                    inference = "SUPERSEDED_HISTORY"
            else:
                inference = "HISTORICAL_CONFIRMED" if is_latest else "SUPERSEDED_HISTORY"
            nodes.append(
                {
                    "evidence_id": row.evidence_id,
                    "proposition": row.proposition,
                    "subject": row.subject,
                    "owner": row.owner,
                    "value": row.value,
                    "outcome": row.outcome,
                    "sampled_at_s": row.sampled_at_s,
                    "arrived_at_s": row.arrived_at_s,
                    "request_id": row.request_id,
                    "version": row.version,
                    "historical_fact_retained": row.historical_fact,
                    "current_inference_status": inference,
                }
            )
        return {
            "at_s": int(at_s),
            "evidence_nodes": nodes,
            "pending_requests": [
                {
                    "request_id": row.request_id,
                    "query_id": row.query_id,
                    "sampled_at_s": row.sampled_at_s,
                    "expected_arrive_at_s": row.expected_arrive_at_s,
                    "version": row.version,
                }
                for row in self._pending
            ],
        }


def materialize_context_graph(
    bundle: Mapping[str, Any],
    *,
    at_s: int,
    conflict_snapshot: ConflictFrontierSnapshot,
    evidence_ledger: EvidenceLedger,
    legal_actions: Iterable[tuple[str, str | None]],
) -> dict[str, Any]:
    """Build the model-facing typed context graph required by the method contract."""

    evidence = evidence_ledger.view(at_s=at_s)
    released = [
        row
        for row in bundle["obligations"]
        if int(row["release_s"]) <= at_s
    ]
    conflict_context = IncrementalConflictFrontier.materialized_context(conflict_snapshot)
    nodes: list[dict[str, Any]] = [
        {
            "node_id": "state:current",
            "kind": "State",
            "time_s": at_s,
            "compatible_support_count": conflict_snapshot.active_world_count,
        },
        {
            "node_id": "resource:satellite-budget",
            "kind": "OpportunityResource",
            "minimum_backup_lower_bound": conflict_snapshot.worst_case_backup_lower_bound,
        },
    ]
    edges: list[dict[str, str]] = []
    for row in released:
        oid = str(row["obligation_id"])
        nodes.append(
            {
                "node_id": f"obligation:{oid}",
                "kind": "Obligation",
                "obligation_id": oid,
                "release_s": int(row["release_s"]),
                "deadline_s": int(row["deadline_s"]),
                "source_ref_ids": list(row.get("source_ref_ids", [])),
            }
        )
        edges.append({"from": "state:current", "to": f"obligation:{oid}", "kind": "HAS_OBLIGATION"})

    for index, row in enumerate(conflict_context["conflict_components"]):
        cid = f"conflict:{index}"
        nodes.append({"node_id": cid, "kind": "Conflict", **row})
        for oid in row["obligations"]:
            edges.append({"from": cid, "to": f"obligation:{oid}", "kind": "CONSTRAINS"})
        edges.append({"from": cid, "to": "resource:satellite-budget", "kind": "MAY_REQUIRE"})

    for row in evidence["evidence_nodes"]:
        eid = row["evidence_id"]
        nodes.append({"node_id": eid, "kind": "Evidence", **row})
        if row["current_inference_status"] == "CURRENT_AT_SAMPLE":
            edges.append({"from": eid, "to": "state:current", "kind": "SUPPORTS_CURRENT_INFERENCE"})
        else:
            edges.append({"from": eid, "to": "state:current", "kind": "HISTORY_ONLY"})

    for action, arg in legal_actions:
        aid = f"action:{action}:{arg if arg is not None else '-'}"
        nodes.append({"node_id": aid, "kind": "Action", "action": action, "arg": arg})
        edges.append({"from": "state:current", "to": aid, "kind": "LEGAL_ACTION"})
        if arg is not None and action in {"SEND_TERR", "SEND_SAT"}:
            edges.append({"from": aid, "to": f"obligation:{arg}", "kind": "ACTS_ON"})
        if action == "ISSUE_QUERY":
            edges.append({"from": aid, "to": "state:current", "kind": "MAY_REFRESH_EVIDENCE"})

    return {
        "schema_version": "layer2-v2-context-graph-0.1",
        "time_s": at_s,
        "nodes": nodes,
        "edges": edges,
        "pending_requests": evidence["pending_requests"],
        "hidden_future_window_identity_exposed": False,
        "oracle_witness_exposed": False,
    }
