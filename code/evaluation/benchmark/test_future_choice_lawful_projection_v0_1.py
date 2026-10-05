#!/usr/bin/env python3
import json
from pathlib import Path

from future_choice_lawful_projection_v0_1 import (
    assert_lawful_features,
    canonical_action,
    feature_digest,
    project_features,
)


ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    frozen = json.loads(
        (ROOT / "results/benchmark/layer1-v0.2-hard-signature-bundles.json").read_text(
            encoding="utf-8"
        )
    )
    bundle = frozen["rows"][0]["bundle"]
    history = [{"time_s": 0, "action": "WAIT", "arg": None}]
    features = project_features(
        bundle,
        at_s=1,
        query_budget_remaining=1,
        action_history=history,
    )
    assert_lawful_features(features)
    assert set(features) == {
        "schema_version", "time_s", "task", "communication",
        "evidence_contract", "recovery", "own_action_history",
    }
    assert feature_digest(features) == feature_digest(features)
    oid = str(bundle["obligations"][0]["obligation_id"])
    assert canonical_action(bundle, "SEND_TERR", oid) == "SEND_TERR:stream_0"
    print("PASS lawful future-choice projection: public/runtime features only")


if __name__ == "__main__":
    main()
