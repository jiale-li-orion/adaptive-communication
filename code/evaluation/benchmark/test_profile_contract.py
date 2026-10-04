#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from profile_contract import (  # noqa: E402
    SourceProfileContractError,
    answer_relevant_unresolved,
    validate_source_profile,
    validate_source_profile_registry,
)


def direct_profile() -> dict:
    return {
        "schema_version": "0.1",
        "profile_id": "direct-demo",
        "families": ["T1"],
        "generator_status": "READY",
        "source_refs": [
            {
                "source_id": "std",
                "source_class": "STANDARD",
                "directness": "DIRECT_TASK_AUTHORITY",
                "snapshot_ref": "source://std",
                "locator": "sec.1",
            },
            {
                "source_id": "device",
                "source_class": "DEVICE_DOCUMENT",
                "directness": "DIRECT_CAPABILITY",
                "snapshot_ref": "source://device",
                "locator": None,
            },
        ],
        "scope": {},
        "heldout_groups": {
            "SOURCE_FAMILY": "std-family",
            "JURISDICTION": "demo-jurisdiction",
        },
        "variables": {
            "deadline": {
                "provenance_class": "FIXED_BY_SOURCE",
                "answer_relevant": True,
                "source_ref_ids": ["std"],
                "value": 15,
            }
        },
        "obligation_templates": [
            {
                "template_id": "deliver",
                "protected_subject": "monitoring info",
                "trigger": {"kind": "release"},
                "completion_predicate": {"kind": "delivered"},
                "timing_semantics": {"deadline_min": 15},
                "authority_owner": "monitoring_platform",
                "source_priority": None,
                "expiration_rule": None,
                "task_authority_source_ref_ids": ["std"],
            }
        ],
        "capabilities": [
            {
                "capability_id": "send",
                "owner": "device",
                "source_ref_ids": ["device"],
                "constraints": {},
            }
        ],
        "authority_invariants": [],
        "unknowns": [],
    }


def expect_error(profile: dict, contains: str) -> None:
    try:
        validate_source_profile(profile)
    except SourceProfileContractError as exc:
        assert contains in str(exc), (contains, str(exc))
        return
    raise AssertionError(f"expected SourceProfileContractError containing {contains!r}")


def main() -> int:
    profile = direct_profile()
    validate_source_profile(profile)
    validate_source_profile_registry([profile])

    unresolved = deepcopy(profile)
    unresolved["variables"]["deadline"] = {
        "provenance_class": "UNRESOLVED",
        "answer_relevant": True,
        "source_ref_ids": [],
        "unresolved_reason": "not specified",
    }
    assert answer_relevant_unresolved(unresolved) == ["deadline"]
    expect_error(unresolved, "READY profile has answer-relevant UNRESOLVED")

    bad_authority = deepcopy(profile)
    bad_authority["obligation_templates"][0][
        "task_authority_source_ref_ids"
    ] = ["device"]
    expect_error(bad_authority, "as task authority")

    adjacent = deepcopy(profile)
    adjacent["profile_id"] = "adjacent"
    adjacent["generator_status"] = "ADJACENT_ONLY"
    adjacent["source_refs"] = [
        {
            "source_id": "paper",
            "source_class": "PEER_REVIEWED_ADJACENT",
            "directness": "ADJACENT_MECHANISM",
            "snapshot_ref": None,
            "locator": None,
        }
    ]
    adjacent["variables"] = {}
    adjacent["obligation_templates"] = []
    adjacent["capabilities"] = [
        {
            "capability_id": "ack",
            "owner": "runtime",
            "source_ref_ids": ["paper"],
            "constraints": {},
        }
    ]
    validate_source_profile(adjacent)

    adjacent_claims_task = deepcopy(adjacent)
    adjacent_claims_task["obligation_templates"] = deepcopy(
        profile["obligation_templates"]
    )
    adjacent_claims_task["obligation_templates"][0][
        "task_authority_source_ref_ids"
    ] = ["paper"]
    expect_error(adjacent_claims_task, "as task authority")

    duplicate = deepcopy(profile)
    try:
        validate_source_profile_registry([profile, duplicate])
    except SourceProfileContractError as exc:
        assert "duplicate profile_id" in str(exc)
    else:
        raise AssertionError("duplicate profile ids must fail")

    print(
        "PASS source profile contract: direct authority/provenance/adjacent-evidence guards"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
