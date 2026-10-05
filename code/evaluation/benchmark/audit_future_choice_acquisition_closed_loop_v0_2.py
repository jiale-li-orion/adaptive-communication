#!/usr/bin/env python3
"""Closed-loop acquisition-timing audit on held-out Layer-1 v0.2 hard signatures."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path

from audit_conditional_acquisition_timing_v0_1 import _initial, _minimal_policy
from exact_reference_oracle_v0_1 import _attempt_lattice
from future_choice_acquisition_policy_v0_2 import AcquisitionPolicyBuilder, POLICIES


ROOT = Path(__file__).resolve().parents[3]
INPUTS = ROOT / "results/benchmark/layer1-v0.2-hard-signature-bundles.json"
DEFAULT_OUT = ROOT / "results/benchmark/layer3-future-choice-acquisition-closed-loop-hard-test-v0.2.json"


def _aggregate(rows: list[dict]) -> dict:
    status = Counter(); failure = Counter(); queries = satellites = 0
    harmful = unresolved = soundness = boundaries = 0
    selector_wall = controller_wall = 0.0
    for row in rows:
        status[row["status"]] += 1
        if row["failure_reason"]:
            failure[row["failure_reason"]] += 1
        if row["requirement"] is not None:
            queries += int(row["requirement"][0]); satellites += int(row["requirement"][1])
        m = row["metrics"]
        harmful += int(m["harmful_query_actions"])
        unresolved += int(m["controller_unresolved"])
        soundness += int(m["controller_soundness_errors"])
        boundaries += int(m["decision_boundaries"])
        selector_wall += float(m["task_selector_wall_s"])
        controller_wall += float(m["acquisition_controller_wall_s"])
    success = int(status["SUCCESS"])
    return {
        "signature_count": len(rows),
        "status_count": dict(sorted(status.items())),
        "success_count": success,
        "success_fraction": success / len(rows) if rows else None,
        "failure_reason_count": dict(sorted(failure.items())),
        "total_queries_on_success": queries,
        "total_satellite_sends_on_success": satellites,
        "harmful_query_action_count": harmful,
        "controller_unresolved_count": unresolved,
        "controller_soundness_error_count": soundness,
        "decision_boundary_count": boundaries,
        "task_selector_wall_s": selector_wall,
        "acquisition_controller_wall_s": controller_wall,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--split", choices=["test", "dev", "train", "all"], default="test")
    ap.add_argument("--choice-upper-depth", type=int, default=4)
    ap.add_argument("--choice-lower-depth", type=int, default=6)
    ap.add_argument("--max-expansions", type=int, default=200_000)
    args = ap.parse_args()
    data = json.loads(INPUTS.read_text(encoding="utf-8"))
    selected = [r for r in data["rows"] if args.split == "all" or r["split"] == args.split]
    results = {}
    for policy_name in POLICIES:
        rows = []
        for i, row in enumerate(selected):
            bundle = row["bundle"]
            chosen = _minimal_policy(bundle, args.max_expansions)
            if chosen is None:
                rows.append({
                    "signature": row["signature"], "recipe_id": bundle["recipe_id"],
                    "split": row["split"], "status": "FAIL",
                    "failure_reason": "NO_MINIMAL_RESOURCE_POINT", "requirement": None,
                    "query_times_s": [],
                    "metrics": {"harmful_query_actions": 0, "controller_unresolved": 0,
                                "controller_soundness_errors": 0, "decision_boundaries": 0,
                                "task_selector_wall_s": 0.0, "acquisition_controller_wall_s": 0.0},
                })
                continue
            q, b, _ = chosen
            builder = AcquisitionPolicyBuilder(
                bundle, policy=policy_name,
                choice_upper_depth=args.choice_upper_depth,
                choice_lower_depth=args.choice_lower_depth,
                max_expansions=args.max_expansions,
            )
            start = min(_attempt_lattice(bundle))
            out = builder.build(at_s=start, states=_initial(bundle, b), query_budget=q)
            rows.append({
                "signature": row["signature"], "recipe_id": bundle["recipe_id"],
                "split": row["split"], "minimal_resource_point": [q, b], **out,
            })
            print(policy_name, i + 1, str(row["signature"])[:12], out["status"], out["failure_reason"], out["query_times_s"], flush=True)
        results[policy_name] = {"aggregate": _aggregate(rows), "rows": rows}

    artifact = {
        "schema_version": "0.2",
        "status": "CLOSED_LOOP_ACQUISITION_TIMING_EVAL",
        "inputs_ref": str(INPUTS.relative_to(ROOT)),
        "inputs_sha256": sha256(INPUTS.read_bytes()).hexdigest(),
        "split_filter": args.split,
        "choice_upper_depth": args.choice_upper_depth,
        "choice_lower_depth": args.choice_lower_depth,
        "policies": results,
        "claim_boundary": [
            "All policies share the same exact non-query future-choice selector; only acquisition timing differs.",
            "EARLIEST_LEGAL_QUERY intentionally treats legal query availability as sufficient and therefore can choose future-feasibility-destroying reads.",
            "BOUND_FUTURE_CHOICE uses no exact acquisition fallback; exact action frontiers are used only as the shared task-action selector and evaluation reference.",
            "This isolates decision/communication benefit and does not claim computational speedup.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({name: value["aggregate"] for name, value in results.items()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
