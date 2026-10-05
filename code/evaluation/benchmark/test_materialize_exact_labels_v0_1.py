#!/usr/bin/env python3
from __future__ import annotations

from itertools import islice

from causal_evidence_process_v0_1 import attach_causal_evidence
from dynamic_world_materializer_v0_1 import iter_world_bundles
from materialize_exact_labels_v0_1 import solver_signature, solver_signature_payload


def main() -> int:
    rows = list(islice(iter_world_bundles(), 64))
    assert len(rows) == 64
    # Signature is deterministic and insensitive to recipe/source identity.
    for b in rows[:8]:
        assert solver_signature(b) == solver_signature(b)
        payload = solver_signature_payload(b)
        assert payload["solver_version"] == "T1-exact-reference-oracle-v0.2-retry-legality"
        assert len(payload["world_terrestrial_windows"]) == len(b["worlds"])
        process = attach_causal_evidence(b)
        assert payload["observation_process"]["direct_observation"] == bool(process["direct_observation"])

    # Recovery/source metadata is not consumed by the exact solver and must not
    # split otherwise identical dynamics.  Find a pair differing only in that
    # metadata inside the deterministic stream.
    seen = {}
    found = False
    for b in iter_world_bundles():
        sig = solver_signature(b)
        if sig in seen and seen[sig]["recipe_id"] != b["recipe_id"]:
            found = True
            break
        seen[sig] = b
        if len(seen) > 5000:
            break
    assert found, "expected solver-equivalent recipes for projection dedupe"
    print("PASS exact-label materializer: canonical solver signatures are deterministic and projectable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
