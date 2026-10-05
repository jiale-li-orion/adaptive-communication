#!/usr/bin/env python3
from __future__ import annotations

from dynamic_world_materializer_v0_1 import iter_world_bundles
from ordinary_baselines_compositional_v0_1 import audit_bundle


def main() -> int:
    easy = next(
        b for b in iter_world_bundles()
        if b["public_environment"]["terrestrial_process_class"] == "STEADY_AVAILABLE_CONTROL"
        and b["observation_projection"]["evidence_regime"] == "FULL_OBSERVATION_CONTROL"
    )
    a = audit_bundle(easy)
    assert a["gateway_local_edf_reserve"]["robust_success"] is True
    assert a["send_probe_ack_fallback"]["legal"] is False
    assert a["send_probe_ack_fallback"]["robust_success"] is None

    dynamic = next(
        b for b in iter_world_bundles()
        if b["public_environment"]["terrestrial_process_class"] == "MULTI_WINDOW_DYNAMIC"
        and b["observation_projection"]["evidence_regime"] == "GATEWAY_SUMMARY_QUERY"
        and b["pre_oracle_disposition"] == "VALIDITY_PENDING"
    )
    d = audit_bundle(dynamic)
    assert set(d) == {
        "gateway_local_edf_reserve",
        "blind_satellite_edf",
        "send_probe_ack_fallback",
        "fixed_owner_read_edf",
    }
    assert d["send_probe_ack_fallback"]["legal"] is False
    assert d["fixed_owner_read_edf"]["legal"] is True
    assert all(x["world_count"] == len(dynamic["worlds"]) for x in d.values())
    print("PASS ordinary compositional baselines: local reserve, blind satellite, send-probe and fixed-read policies consume the new world IR")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
