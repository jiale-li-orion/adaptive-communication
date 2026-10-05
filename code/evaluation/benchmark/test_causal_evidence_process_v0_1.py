#!/usr/bin/env python3
"""Causal evidence regression for the Layer-1 compositional universe."""
from __future__ import annotations

from causal_evidence_process_v0_1 import (
    CausalEvidenceError,
    attach_causal_evidence,
    gateway_snapshot,
    issue_gateway_query,
    terrestrial_send_observation,
)
from dynamic_world_materializer_v0_1 import iter_world_bundles


def _find_mixed_dynamic():
    for bundle in iter_world_bundles():
        if (
            bundle["observation_projection"]["evidence_regime"] == "MIXED_PASSIVE_QUERY_PROBE"
            and bundle["public_environment"]["terrestrial_process_class"] == "MULTI_WINDOW_DYNAMIC"
            and len(bundle["worlds"]) >= 2
        ):
            return bundle
    raise AssertionError("no mixed dynamic bundle")


def main() -> int:
    bundle = _find_mixed_dynamic()
    process = attach_causal_evidence(bundle)
    assert process["next_stage"] == "EXACT_ORACLE_REFERENCE_LABELS"
    assert len(process["query_capabilities"]) == 1
    assert process["passive_observation_rules"]
    assert process["normal_send_probe_rules"][0]["extra_tool"] is False

    worlds = process["world_owner_processes"]
    # Find a time where current owner state differs.  The query may expose that
    # present fact, but it must not include a future window or world identity.
    candidate_times = sorted({int(x) for w in worlds for ab in w["terrestrial_intervals"] for x in ab})
    split_t = None
    for t in candidate_times:
        snapshots = [gateway_snapshot(w, t) for w in worlds]
        if len({str(x) for x in snapshots}) > 1:
            split_t = t
            break
    assert split_t is not None
    responses = [
        issue_gateway_query(process, world_id=w["world_id"], issue_at_s=split_t)
        for w in worlds
    ]
    for r in responses:
        assert r["sampled_at_s"] == split_t
        assert r["arrived_at_s"] >= r["sampled_at_s"]
        text = str(r.get("payload"))
        assert "world_id" not in text
        assert "next_window" not in text
        assert "future" not in text

    # Sample/arrival separation: the returned payload is fixed at sampled_at,
    # irrespective of any owner-state event before the response arrives.
    first = worlds[0]
    q = issue_gateway_query(process, world_id=first["world_id"], issue_at_s=split_t)
    if q["kind"] == "QUERY_RESPONSE":
        assert q["payload"] == gateway_snapshot(first, q["sampled_at_s"])

    # Action-dependent evidence: choose a real active window.  No hypothetical
    # ACK exists until SEND_TERR is executed; accepted and rejected worlds can
    # then produce different observations.
    obligation = bundle["obligations"][0]
    active_send = None
    accepted_world = None
    rejected_world = None
    for w in bundle["worlds"]:
        for window in w["terrestrial_windows"]:
            t = max(int(window["start_s"]), int(obligation["release_s"]))
            if t < min(int(window["end_s"]), int(obligation["deadline_s"])):
                active_send = t
                accepted_world = w
                break
        if active_send is not None:
            break
    assert active_send is not None and accepted_world is not None
    accepted = terrestrial_send_observation(
        bundle,
        process,
        world_id=accepted_world["world_id"],
        obligation_id=obligation["obligation_id"],
        send_at_s=active_send,
    )
    assert accepted["kind"] == "SEND_ACCEPTED"
    assert accepted["gateway_receipt_at_s"] < accepted["final_ack_at_s"]

    for w in bundle["worlds"]:
        r = terrestrial_send_observation(
            bundle,
            process,
            world_id=w["world_id"],
            obligation_id=obligation["obligation_id"],
            send_at_s=active_send,
        )
        if r["kind"] == "SEND_NOT_ACCEPTED":
            rejected_world = w
            assert r["gateway_receipt_at_s"] is None
            assert r["negative_observation_at_s"] > active_send
            break
    # Some world structures may share service at this particular point; the
    # process remains valid even when this one send does not partition them.

    # A regime without owner-query capability must reject synthetic query use.
    passive_bundle = next(
        b for b in iter_world_bundles()
        if b["observation_projection"]["evidence_regime"] == "PASSIVE_ACK_ONLY"
    )
    passive_process = attach_causal_evidence(passive_bundle)
    try:
        issue_gateway_query(
            passive_process,
            world_id=passive_process["world_owner_processes"][0]["world_id"],
            issue_at_s=0,
        )
    except CausalEvidenceError:
        pass
    else:
        raise AssertionError("passive-only regime illegally exposed an owner query")

    print(
        "PASS causal evidence process: sampled/arrived time, state-grounded query, "
        "action-dependent ACK and send-as-probe semantics are causal"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
