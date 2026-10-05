#!/usr/bin/env python3
"""Deterministic V0-V7 audit on one representative per hard-structure cell."""
from __future__ import annotations

from collections import Counter
import argparse
import json

from audit_v8_baselines_v0_1 import _representatives
from validity_filters_v0_1 import evaluate_v0_v7


def audit(*, max_memo_nodes: int = 200_000) -> dict:
    reasons: dict[str, Counter[str]] = {}
    pass_counts: dict[str, Counter[str]] = {}
    rows = []
    reps = _representatives()
    for cell, (_rank, bundle) in sorted(reps.items()):
        result = evaluate_v0_v7(bundle, max_memo_nodes=max_memo_nodes)
        summary = {}
        for f in result["filters"]:
            fid = str(f["filter_id"])
            reasons.setdefault(fid, Counter())[str(f["reason_code"])] += 1
            pass_counts.setdefault(fid, Counter())[str(f["passed"])] += 1
            summary[fid] = {
                "passed": f["passed"],
                "reason_code": f["reason_code"],
            }
        rows.append({
            "cell": list(cell),
            "recipe_id": bundle["recipe_id"],
            "filters": summary,
            "oracle_summary": result["oracle_summary"],
        })
    return {
        "schema_version": "0.1",
        "status": "V0_V7_STRATIFIED_AUDIT",
        "selection": {
            "cell_count": len(reps),
            "rule": "VALIDITY_PENDING only; one minimum-stable-hash representative per service×evidence×overlap×headroom×recovery cell",
            "use": "construction audit; not final held-out split",
        },
        "pass_counts": {k: dict(sorted(v.items())) for k, v in sorted(pass_counts.items())},
        "reason_counts": {k: dict(sorted(v.items())) for k, v in sorted(reasons.items())},
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-memo-nodes", type=int, default=200_000)
    args = ap.parse_args()
    print(json.dumps(audit(max_memo_nodes=args.max_memo_nodes), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
