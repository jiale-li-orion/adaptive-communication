#!/usr/bin/env python3
"""Freeze exact future-choice truth for Layer-1 v0.2 hard test signatures."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import argparse
import json
from pathlib import Path

from audit_conditional_acquisition_timing_v0_1 import _initial, _minimal_policy
from causal_evidence_process_v0_1 import attach_causal_evidence
from conditional_action_frontier_v0_1 import build_action_frontier
from exact_reference_oracle_v0_1 import _attempt_lattice
from v8_policy_baselines_v0_1 import _normalize_one, _step


ROOT = Path(__file__).resolve().parents[3]
INPUTS = ROOT / "results/benchmark/layer1-v0.2-hard-signature-bundles.json"
OUT = ROOT / "results/benchmark/layer2-future-choice-exact-reference-hard-test-v0.2.json"


def _truth(frontier: dict) -> dict[str, bool]:
    cert = set(frontier["certified_action_keys"])
    qkey = "ISSUE_QUERY:gateway_state_summary"
    non_query = [x for x in cert if x != qkey]
    return {
        "stop": frontier["context"]["query_free_completion"] is True,
        "harmful": frontier["context"]["query_now_legal"] and qkey not in cert,
        "defer": bool(non_query),
        "required": qkey in cert and not non_query,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", type=Path, default=INPUTS)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--split", choices=["train", "dev", "test", "all"], default="test")
    ap.add_argument("--max-expansions", type=int, default=200_000)
    args = ap.parse_args()
    data = json.loads(args.inputs.read_text(encoding="utf-8"))
    selected = [r for r in data["rows"] if args.split == "all" or r["split"] == args.split]
    rows = []
    for i, row in enumerate(selected):
        bundle = row["bundle"]
        chosen = _minimal_policy(bundle, args.max_expansions)
        if chosen is None:
            raise RuntimeError(f"no minimal policy for {row['signature']}")
        q, b, solved = chosen
        process = attach_causal_evidence(bundle)
        states = _initial(bundle, b)
        at_s = min(_attempt_lattice(bundle))
        node = solved["policy"]
        boundaries = []
        while node and not node.get("terminal"):
            branches = _normalize_one(bundle, process, at_s, states)
            if len(branches) != 1 or next(iter(branches)) != "same" or node.get("event") == "OBSERVATION":
                break
            states = next(iter(branches.values()))
            frontier = build_action_frontier(
                bundle,
                at_s=at_s,
                states=deepcopy(states),
                query_budget=q,
                max_expansions=args.max_expansions,
            )
            boundaries.append({
                "time_s": at_s,
                "truth": _truth(frontier),
                "certified_action_keys": frontier["certified_action_keys"],
                "legal_action_keys": frontier["legal_action_keys"],
            })
            if node["action"] == "ISSUE_QUERY":
                break
            stepped = _step(bundle, process, states, at_s, (node["action"], node["arg"]))
            if stepped is None:
                break
            states, at_s = stepped
            node = node["subpolicy"]
        rows.append({
            "signature": row["signature"],
            "recipe_id": bundle["recipe_id"],
            "split": row["split"],
            "minimal_resource_point": [q, b],
            "boundary_count": len(boundaries),
            "boundaries": boundaries,
        })
        print(i + 1, str(row["signature"])[:12], len(boundaries), flush=True)

    artifact = {
        "schema_version": "0.2",
        "status": "FROZEN_EXACT_FUTURE_CHOICE_REFERENCE",
        "inputs_ref": str(args.inputs.relative_to(ROOT)),
        "inputs_sha256": sha256(args.inputs.read_bytes()).hexdigest(),
        "split_filter": args.split,
        "signature_count": len(rows),
        "boundary_count": sum(r["boundary_count"] for r in rows),
        "rows": rows,
        "rules": [
            "Truth is regenerated with the current exact action frontier and replay-validated continuation witnesses.",
            "This file contains no structural L/U controller output and is immutable input for subsequent predicate audits.",
            "Any audit must record this file's SHA-256 and must not read a concurrently rewritten controller artifact as truth.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "signature_count": artifact["signature_count"],
        "boundary_count": artifact["boundary_count"],
        "sha256": sha256(args.out.read_bytes()).hexdigest(),
        "out": str(args.out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
