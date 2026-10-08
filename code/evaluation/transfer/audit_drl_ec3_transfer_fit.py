#!/usr/bin/env python3
"""Static transfer-fit audit for the official DRL-EC3 environment checkout."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXT = ROOT / "local_research/external/DRL-EC3"
ENV = EXT / "experiments/env0/data_collection0.py"
SETTING = EXT / "experiments/env0/env_setting0.py"


def main() -> int:
    env = ENV.read_text(encoding="utf-8")
    setting = SETTING.read_text(encoding="utf-8")
    facts = {
        "official_training_environment_present": "class Env(object):" in env,
        "sequential_step_present": "def step(self, actions" in env,
        "persistent_energy_state": "self.energy" in env and "MAX_ENERGY" in setting,
        "continuous_movement_action": "spaces.Box" in env and "NUM_ACTION" in setting,
        "data_collection_state": "self.mapmatrix" in env and "self.collection" in env,
        "energy_consumed_by_movement_and_collection": (
            "self.__cusume_energy1(i, 0, distance)" in env
            and "self.__cusume_energy1(i, value, 0.)" in env
        ),
        "hard_operational_deadlines_present": "deadline" in env.lower(),
        "explicit_operational_obligation_object_present": "obligation" in env.lower(),
    }
    compatible = all(
        facts[k]
        for k in (
            "official_training_environment_present",
            "sequential_step_present",
            "persistent_energy_state",
            "continuous_movement_action",
            "data_collection_state",
            "energy_consumed_by_movement_and_collection",
        )
    )
    needs_obligation_layer = not (
        facts["hard_operational_deadlines_present"]
        or facts["explicit_operational_obligation_object_present"]
    )
    payload = {
        "stage": "EMERGENCY_COMM_DRL_EC3_TRANSFER_FIT",
        "external_repo": "BIT-MCS/DRL-EC3",
        "external_checkout": str(EXT),
        "facts": facts,
        "compatible_sequential_resource_environment": compatible,
        "requires_operational_obligation_extension": needs_obligation_layer,
        "disposition": (
            "RESOURCE_BASELINE_AND_SECONDARY_TRANSFER_CANDIDATE"
            if compatible and needs_obligation_layer
            else "REVIEW"
        ),
        "claim_boundary": [
            "The external source is inspected read-only; no TensorFlow training or dependency installation is performed.",
            "DRL-EC3 already supplies sequential movement/data-collection decisions and persistent UAV energy, but its released environment optimizes aggregate collection/fairness/energy rather than source-grounded hard operational obligations.",
            "Adding mission obligations would therefore be an explicit transfer extension, not a claim that the original paper already contains future-choice semantics.",
        ],
    }
    out = ROOT / "local_research/current/transfer/drl-ec3-transfer-fit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"out": str(out), "disposition": payload["disposition"], **facts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
