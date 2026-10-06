#!/usr/bin/env python3
"""Static admission audit for the pre-method Layer-1 generation axes.

The purpose of this audit is intentionally boring: prove that the next
generator consumes source/profile/trace authorities and a predeclared stress
spec, rather than values inferred from baseline or proposed-method outcomes.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
AXES = ROOT / "research/benchmark/GENERATION-AXES.v0.1.json"
SOURCE = ROOT / "research/benchmark/profiles/v0.1/SOURCE-PROFILE-REGISTRY.v0.1.json"
CAPS = ROOT / "research/benchmark/profiles/v0.1/CAPABILITY-PROFILE-REGISTRY.v0.1.json"
MANIFEST = ROOT / "research/benchmark/PROFILE-BUNDLE-MANIFEST.v0.1.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _profile(registry: dict, pid: str) -> dict:
    return next(row for row in registry["profiles"] if row.get("profile_id") == pid)


def _cap_profile(registry: dict, pid: str) -> dict:
    return next(row for row in registry["profiles"] if row.get("capability_profile_id") == pid)


def main() -> int:
    axes = _load(AXES)
    src = _load(SOURCE)
    caps = _load(CAPS)
    manifest = _load(MANIFEST)

    assert axes["status"] == "FROZEN_FOR_LAYER1_REBUILD"
    assert axes["scope"]["family"] == "T1_MONITORING_INFORMATION_CONTINUITY"

    task = _profile(src, axes["scope"]["primary_task_profile"])
    assert task["generator_status"] == "READY"
    assert task["scope"]["hazard_type"] == "landslide"
    assert task["variables"]["cadence_table"]["provenance_class"] == "FIXED_BY_SOURCE"
    assert not task.get("unknowns"), "primary task profile must have no answer-relevant source gaps"

    dzt = _profile(src, "DZT0450_2023_disconnect_recovery")
    assert dzt["variables"]["minimum_cache_days"]["value"] == 7
    assert dzt["variables"]["reconnect_backlog_priority"]["provenance_class"] == "UNRESOLVED"
    assert "reconnect priority cannot be invented" in dzt["authority_invariants"]

    jiaozuo = _profile(src, "JIAOZUO_2024_geohazard_monitoring_deployment")
    cap_ids = {row["capability_id"] for row in jiaozuo["capabilities"]}
    assert {"remote_state_read", "block_read_local_history", "beidou_fallback"} <= cap_ids
    assert jiaozuo["variables"]["communication_priority"]["value"] == ["NB", "4G/5G", "BeiDou"]

    # The Connecta trace may only be paired with its own service-family device
    # profile; this audit prevents silently treating generic DZ/T satellite
    # parameters as the same physical service.
    connecta = _cap_profile(caps, "PLAN_S_CONNECTA_IOT_MODULE_D2S")
    assert connecta["scope"]["service_family"] == "PLAN_S_CONNECTA_D2S"
    assert any("pair with Connecta TLE geometry" in note for note in connecta["notes"])

    rel = axes["model_derived"]["satellite_geometry"]["trace_path"]
    trace = ROOT / rel
    assert trace.exists()
    manifest_row = next(row for row in manifest["files"] if row["path"] == rel)
    digest = hashlib.sha256(trace.read_bytes()).hexdigest()
    assert digest == manifest_row["sha256"], "public geometry trace drifted from frozen profile bundle"

    cs = axes["controlled_stress"]
    assert cs["obligation_composition"]["stream_count"] == 2
    assert cs["obligation_composition"]["obligations_per_stream"] == [2, 3]
    assert len(cs["terrestrial_service_process"]["support_families"]) >= 3
    assert cs["terrestrial_service_process"]["probability_model"] is None
    assert cs["terrestrial_opportunities"]["phase_ratios"] == [0.25, 0.75]
    assert set(cs["terrestrial_opportunities"]["capacity_units"]) == {1, 2}

    for row in cs["feedback_timing_profiles"]:
        r = float(row["gateway_receipt_delay_over_deadline"])
        a = float(row["final_ack_delay_over_deadline"])
        assert 0.0 <= r <= a <= 1.0
    qd = [float(x) for x in cs["remote_query_response_delay_over_deadline"]]
    assert qd == sorted(qd) and all(0.0 <= x <= 1.0 for x in qd)

    forbidden = " ".join(axes["forbidden_generator_dependencies"]).lower()
    assert "baseline" in forbidden and "layer-2" in forbidden and "layer-3" in forbidden
    assert "hidden future" in forbidden

    print("PASS generation axes v0.1: source/task/capability/trace authorities resolve; controlled-stress grid is method-independent and frozen before generator rebuild")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
