#!/usr/bin/env python3
"""Apply a real human Q11 review response to the frozen audit sample.

The reviewer response is intentionally tiny and external to automation.  This
script validates reviewer identity + five PASS/FAIL fields per sample, updates
the Q11 artifact, then leaves gate/release regeneration to the caller.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
AUDIT = ROOT / "results/benchmark/layer1-human-source-audit-v0.1.json"

FIELDS = (
    "source_extraction_semantics",
    "authority_priority_time_semantics",
    "task_family_identity",
    "oracle_success_set",
    "evaluator_trace",
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("review_json", type=Path, help="JSON array/object containing reviewer decisions")
    ap.add_argument("--out", type=Path, default=AUDIT)
    args = ap.parse_args()

    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    raw = json.loads(args.review_json.read_text(encoding="utf-8"))
    reviews = raw["samples"] if isinstance(raw, dict) and "samples" in raw else raw
    if not isinstance(reviews, list):
        raise ValueError("review_json must be a list or {'samples': [...]} object")
    by_id = {str(x["sample_id"]): x for x in reviews}
    expected = {str(x["sample_id"]) for x in audit["samples"]}
    if set(by_id) != expected:
        raise ValueError(f"review sample ids mismatch: missing={sorted(expected-set(by_id))}, extra={sorted(set(by_id)-expected)}")

    any_fail = False
    for sample in audit["samples"]:
        sid = str(sample["sample_id"])
        incoming = by_id[sid]
        reviewer = incoming.get("reviewer")
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise ValueError(f"{sid}: reviewer must be a non-empty real reviewer name")
        review = sample["review"]
        review["reviewer"] = reviewer.strip()
        review["notes"] = incoming.get("notes")
        for field in FIELDS:
            value = str(incoming.get(field, "")).upper()
            if value not in {"PASS", "FAIL"}:
                raise ValueError(f"{sid}: {field} must be PASS or FAIL")
            review[field] = value
            any_fail = any_fail or value == "FAIL"

    audit["status"] = "FAIL" if any_fail else "PASS"
    audit["review_completion"] = {
        "completed_sample_count": len(audit["samples"]),
        "all_five_fields_completed": True,
        "named_reviewer_required": True,
        "any_fail": any_fail,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": audit["status"], "sample_count": len(audit["samples"]), "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
