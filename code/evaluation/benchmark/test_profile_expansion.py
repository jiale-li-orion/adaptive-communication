#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from profile_contract import SourceProfileContractError  # noqa: E402
from profile_expansion import expand_nominal_profile, expand_ready_registry  # noqa: E402


def profile(status: str = "READY") -> dict:
    return {
        "schema_version": "0.1",
        "profile_id": "p",
        "families": ["T1"],
        "generator_status": status,
        "source_refs": [
            {
                "source_id": "s",
                "source_class": "STANDARD",
                "directness": "DIRECT_TASK_AUTHORITY",
            }
        ],
        "scope": {},
        "heldout_groups": {"JURISDICTION": "A"},
        "variables": {
            "fixed": {
                "provenance_class": "FIXED_BY_SOURCE",
                "answer_relevant": True,
                "source_ref_ids": ["s"],
                "value": 7,
            },
            "a": {
                "provenance_class": "SOURCE_RANGE",
                "answer_relevant": True,
                "source_ref_ids": ["s"],
                "range": ["x", "y"],
                "sampling_rule": "enumerate",
            },
            "b": {
                "provenance_class": "SOURCE_RANGE",
                "answer_relevant": True,
                "source_ref_ids": ["s"],
                "range": [1, 2, 3],
                "sampling_rule": "enumerate",
            },
            "context_only": {
                "provenance_class": "SOURCE_RANGE",
                "answer_relevant": False,
                "source_ref_ids": ["s"],
                "range": ["u", "v", "w"],
                "sampling_rule": "source-supported context set",
            },
        },
        "obligation_templates": [
            {
                "template_id": "o",
                "protected_subject": "info",
                "trigger": {},
                "completion_predicate": {},
                "timing_semantics": {},
                "authority_owner": "system",
                "source_priority": None,
                "expiration_rule": None,
                "task_authority_source_ref_ids": ["s"],
            }
        ],
        "capabilities": [],
        "authority_invariants": [],
        "unknowns": [],
    }


def main() -> int:
    rows = expand_nominal_profile(profile())
    assert len(rows) == 6, len(rows)
    got = {(r["source_range_assignment"]["a"], r["source_range_assignment"]["b"]) for r in rows}
    assert got == {("x", 1), ("x", 2), ("x", 3), ("y", 1), ("y", 2), ("y", 3)}
    assert all(r["fixed_by_source"]["fixed"] == 7 for r in rows)
    assert all(r["contextual_source_ranges"]["context_only"] == ["u", "v", "w"] for r in rows)

    partial = profile("PARTIAL_SOURCE_GAP")
    assert expand_ready_registry([profile(), partial]) == rows

    continuous = profile()
    continuous["variables"]["a"]["range"] = {"min": 0, "max": 1}
    try:
        expand_nominal_profile(continuous)
    except SourceProfileContractError as exc:
        assert "explicit sampler" in str(exc)
    else:
        raise AssertionError("non-discrete SOURCE_RANGE must not silently sample")

    print("PASS nominal profile expansion: only answer-relevant source ranges multiply cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
