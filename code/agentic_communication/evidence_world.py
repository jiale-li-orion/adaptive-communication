"""Legal communication observations -> versioned Evidence World."""
from __future__ import annotations

from hashlib import sha256
import json

from .contracts import CommunicationEvidence, EvidenceStatus, EvidenceWorldSnapshot


def _eid(kind: str, subject: str, observed_at_s: int, value) -> str:
    material = json.dumps(
        [kind, subject, int(observed_at_s), value],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return "comm-evidence:" + sha256(material.encode()).hexdigest()[:24]


class CommunicationEvidenceWorld:
    """In-memory adapter over legal CenterView/GatewayView fields only."""

    def __init__(self) -> None:
        self._revision = 0
        self._last_digest: str | None = None
        self._snapshot: EvidenceWorldSnapshot | None = None

    @property
    def snapshot(self) -> EvidenceWorldSnapshot | None:
        return self._snapshot

    def observe(self, view) -> EvidenceWorldSnapshot:
        # A new owner-local observation updates only that owner's slice.  Evidence
        # acquired earlier from another owner (for example a gateway-local read)
        # remains part of the Evidence World until it is explicitly replaced or
        # considered stale by task/context freshness rules.  Rebuilding a
        # CenterView must never erase legal gateway evidence.
        preserved = [
            e
            for e in (self._snapshot.evidence if self._snapshot is not None else [])
            if e.owner_location != "center"
        ]
        evidence: list[CommunicationEvidence] = list(preserved)
        next_revision = max(1, self._revision + 1)

        for nid in view.node_ids:
            snap = dict(view.reports.get(nid) or {})
            if snap:
                observed_at = int(view.report_at.get(nid, view.t_s))
                generated_at = snap.get("read_at")
                value = {
                    k: snap.get(k)
                    for k in (
                        "alive",
                        "soc_wh",
                        "sample_interval_s",
                        "report_period_s",
                        "cache_level",
                        "read_at",
                        "config_generation",
                        "field_generation",
                    )
                    if k in snap
                }
                evidence.append(
                    CommunicationEvidence(
                        evidence_id=_eid("center.node_report", nid, observed_at, value),
                        proposition="communication.center.node_report",
                        subject_ref=nid,
                        value=value,
                        source_id="center-view.reports",
                        source_role="center",
                        owner_location="center",
                        generated_at_s=(None if generated_at is None else int(generated_at)),
                        observed_at_s=observed_at,
                        world_revision=next_revision,
                        status=EvidenceStatus.CURRENT,
                        freshness={
                            "basis": "generated_at_s/read_at when present; otherwise observed_at_s"
                        },
                        provenance={"surface": "CenterView.reports"},
                    )
                )

            newest = view.newest_taken_at.get(nid)
            if newest is not None:
                observed_at = int(view.report_at.get(nid, view.t_s))
                val = {"newest_taken_at": int(newest)}
                evidence.append(
                    CommunicationEvidence(
                        evidence_id=_eid("center.delivery_status", nid, observed_at, val),
                        proposition="communication.center.delivery_status",
                        subject_ref=nid,
                        value=val,
                        source_id="center-view.newest_taken_at",
                        source_role="center",
                        owner_location="center",
                        generated_at_s=int(newest),
                        observed_at_s=observed_at,
                        world_revision=next_revision,
                        status=EvidenceStatus.CURRENT,
                        freshness={"basis": "newest_taken_at"},
                        provenance={"surface": "CenterView.newest_taken_at"},
                    )
                )

        link_value = {
            "heard_nodes": sorted(nid for nid in view.node_ids if view.report_at.get(nid) is not None),
            "n_reports": len(view.reports),
        }
        link_observed_at = max(view.report_at.values(), default=0)
        evidence.append(
            CommunicationEvidence(
                evidence_id=_eid(
                    "center.link_summary", "monitoring-network", link_observed_at, link_value
                ),
                proposition="communication.center.link_summary",
                subject_ref="monitoring-network",
                value=link_value,
                source_id="center-view.report_at",
                source_role="center",
                owner_location="center",
                observed_at_s=int(link_observed_at),
                world_revision=next_revision,
                status=EvidenceStatus.CURRENT,
                freshness={"basis": "latest_center_observation_time"},
                provenance={"surface": "CenterView.report_at"},
            )
        )

        # Gateway-local evidence is emitted only when the supplied view owns it.
        if view.gateway_pending_depth is not None:
            gateway_value = {
                "last_forward_ok_at": view.gateway_last_forward_ok_at,
                "pending_depth": view.gateway_pending_depth,
                "oldest_pending_age_s": view.gateway_oldest_pending_age_s,
            }
            evidence.append(
                CommunicationEvidence(
                    evidence_id=_eid("gateway.primary_health", "gw0", view.t_s, gateway_value),
                    proposition="communication.gateway.primary_health",
                    subject_ref="gw0",
                    value=gateway_value,
                    source_id="gateway-view.forward-state",
                    source_role="gateway",
                    owner_location="gateway",
                    observed_at_s=int(view.t_s),
                    world_revision=next_revision,
                    status=EvidenceStatus.CURRENT,
                    freshness={"basis": "gateway_local_observation"},
                    provenance={"surface": "GatewayView.local_forward_state"},
                )
            )

        candidate = EvidenceWorldSnapshot.build(
            revision=next_revision,
            observed_at_s=int(view.t_s),
            evidence=evidence,
        )
        if candidate.digest == self._last_digest and self._snapshot is not None:
            return self._snapshot.model_copy(update={"observed_at_s": int(view.t_s)})
        self._revision = next_revision
        self._last_digest = candidate.digest
        self._snapshot = candidate
        return candidate

    def merge_gateway_observation(
        self,
        *,
        capability_id: str,
        view,
        resource: str | None = None,
    ) -> EvidenceWorldSnapshot:
        """Merge a legally acquired gateway-owner observation into the world.

        This method is called only after the runtime observation provider has
        returned a successful owner-scoped read.  It never checks path truth by
        itself and therefore cannot turn hidden simulator state into evidence.
        """
        base = list(self._snapshot.evidence if self._snapshot is not None else [])
        next_revision = max(1, self._revision + 1)
        if capability_id == "communication.gateway.primary_health":
            value = {
                "last_forward_ok_at": view.gateway_last_forward_ok_at,
                "pending_depth": view.gateway_pending_depth,
                "oldest_pending_age_s": view.gateway_oldest_pending_age_s,
                "query_path_reachable": True,
            }
            prop = capability_id
            source = "gateway-view.forward-state"
            subject = "gw0"
        elif capability_id == "communication.gateway.receipt_summary":
            value = {
                "heard_nodes": sorted(view.reports),
                "report_at": {k: int(v) for k, v in sorted(view.report_at.items())},
                "newest_taken_at": {
                    k: int(v) for k, v in sorted(view.newest_taken_at.items())
                },
            }
            prop = capability_id
            source = "gateway-view.receipt-state"
            subject = "gw0"
        elif capability_id == "communication.gateway.node_report":
            if not resource:
                raise ValueError("gateway.node_report requires a node resource")
            snap = dict(view.reports.get(resource) or {})
            if not snap:
                # A successful owner read can still truthfully return no report.
                # Do not manufacture a negative node state from absence.
                return self._snapshot or EvidenceWorldSnapshot.build(
                    revision=max(1, self._revision),
                    observed_at_s=int(view.t_s),
                    evidence=base,
                )
            value = {
                k: snap.get(k)
                for k in (
                    "alive",
                    "soc_wh",
                    "sample_interval_s",
                    "report_period_s",
                    "cache_level",
                    "read_at",
                    "config_generation",
                    "field_generation",
                )
                if k in snap
            }
            prop = capability_id
            source = "gateway-view.reports"
            subject = str(resource)
        else:
            raise ValueError(f"unsupported gateway evidence capability {capability_id!r}")

        observed_at = int(view.report_at.get(subject, view.t_s)) if capability_id == "communication.gateway.node_report" else int(view.t_s)
        generated_at = (
            value.get("read_at")
            if capability_id == "communication.gateway.node_report" and isinstance(value, dict)
            else None
        )
        row = CommunicationEvidence(
            evidence_id=_eid(prop, subject, observed_at, value),
            proposition=prop,
            subject_ref=subject,
            value=value,
            source_id=source,
            source_role="gateway",
            owner_location="gateway",
            generated_at_s=(None if generated_at is None else int(generated_at)),
            observed_at_s=observed_at,
            world_revision=next_revision,
            status=EvidenceStatus.CURRENT,
            freshness={
                "basis": (
                    "node read_at plus gateway receipt time"
                    if capability_id == "communication.gateway.node_report"
                    else "gateway_owner_observation"
                )
            },
            provenance={"surface": "GatewayView", "capability_id": capability_id},
        )
        if capability_id == "communication.gateway.node_report":
            base = [
                e for e in base
                if not (e.proposition == capability_id and e.subject_ref == subject)
            ]
        else:
            base = [e for e in base if e.proposition != capability_id]
        base.append(row)
        candidate = EvidenceWorldSnapshot.build(
            revision=next_revision,
            observed_at_s=int(view.t_s),
            evidence=base,
        )
        if candidate.digest == self._last_digest and self._snapshot is not None:
            return self._snapshot.model_copy(update={"observed_at_s": int(view.t_s)})
        self._revision = next_revision
        self._last_digest = candidate.digest
        self._snapshot = candidate
        return candidate

    @staticmethod
    def select(
        snapshot: EvidenceWorldSnapshot,
        *,
        propositions: set[str] | None = None,
        subjects: set[str] | None = None,
    ) -> list[CommunicationEvidence]:
        rows = snapshot.evidence
        if propositions is not None:
            rows = [e for e in rows if e.proposition in propositions]
        if subjects is not None:
            rows = [e for e in rows if e.subject_ref in subjects]
        return rows
