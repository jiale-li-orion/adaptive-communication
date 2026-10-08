#!/usr/bin/env python3
"""Aggregate the bounded 36-cell v0.7 gateway-local mechanism pilot.

Only the official 50k-memo indexed-cell outputs enter the main disposition.
Optional higher-budget diagnostic reruns are deliberately excluded from counts.
Natural-feedback candidates must also have a same-information ordinary-baseline
audit before they can be classified as shortcut-solved or remain open.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
LOCAL = ROOT / "local_research/current/benchmark"
INDEX = LOCAL / "v07-gateway-pilot-index.json"
DEFAULT_OUT = ROOT / "results/benchmark/layer1-v0.7-gateway-pilot-v0.1.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    index = _load(INDEX)
    assert index["axis_cell_count"] == 36
    indexed = {int(row["ordinal"]): row for row in index["rows"]}
    assert set(indexed) == set(range(1, 37))

    raw_counts = Counter()
    final_counts = Counter()
    by_process: dict[str, Counter[str]] = defaultdict(Counter)
    by_composition: dict[str, Counter[str]] = defaultdict(Counter)
    by_feedback: dict[str, Counter[str]] = defaultdict(Counter)
    rows = []

    for ordinal in range(1, 37):
        result_path = LOCAL / f"v07-gateway-indexed-cell-{ordinal}.json"
        result = _load(result_path)
        source = indexed[ordinal]
        assert result["ordinal"] == ordinal
        assert result["case_id"] == source["case"]["case_id"]
        assert result["base_id"] == source["case"]["base_id"]
        assert result["axis_cell"] == source["axis_cell"]
        assert result["max_memo_nodes_per_reference"] == 50_000

        raw = str(result["disposition"])
        raw_counts[raw] += 1
        final = raw
        baseline = None
        if raw == "GATEWAY_NATURAL_FEEDBACK_REQUIRED_CANDIDATE":
            baseline_path = LOCAL / f"v07-gateway-candidate-baselines-{ordinal}.json"
            baseline = _load(baseline_path)
            assert baseline["ordinal"] == ordinal
            assert baseline["case_id"] == result["case_id"]
            if baseline["any_ordinary_success"]:
                final = "ORDINARY_BASELINE_SHORTCUT_SOLVED"
            else:
                final = "GATEWAY_NATURAL_FEEDBACK_BASELINE_SURVIVOR"

        final_counts[final] += 1
        axis = result["axis_cell"]
        by_process[str(axis["service_process"])][final] += 1
        comp = f"{axis['obligations_per_stream']}x2::{axis['phase_mode']}"
        by_composition[comp][final] += 1
        by_feedback[str(axis["feedback_profile"])][final] += 1
        rows.append(
            {
                "ordinal": ordinal,
                "axis_cell": axis,
                "case_id": result["case_id"],
                "base_id": result["base_id"],
                "raw_disposition": raw,
                "final_pilot_disposition": final,
                "references": result["references"],
                "ordinary_baseline": baseline,
            }
        )

    payload = {
        "schema_version": "0.1",
        "stage": "V07_GATEWAY_LOCAL_BOUNDED_MECHANISM_PILOT",
        "placement": "GATEWAY_LOCAL_PRIMARY",
        "generation_run": index["official_generation_run"],
        "generation_manifest_sha256": index["official_generation_manifest_sha256"],
        "selection_rule": index["selection_rule"],
        "selection_depends_on_method_or_baseline": False,
        "axis_cell_count": 36,
        "max_memo_nodes_per_reference": 50_000,
        "raw_disposition_counts": dict(sorted(raw_counts.items())),
        "final_pilot_disposition_counts": dict(sorted(final_counts.items())),
        "unresolved_ordinals": [
            row["ordinal"] for row in rows
            if row["final_pilot_disposition"] == "UNRESOLVED_COMPUTATION"
        ],
        "ordinary_shortcut_ordinals": [
            row["ordinal"] for row in rows
            if row["final_pilot_disposition"] == "ORDINARY_BASELINE_SHORTCUT_SOLVED"
        ],
        "baseline_survivor_ordinals": [
            row["ordinal"] for row in rows
            if row["final_pilot_disposition"] == "GATEWAY_NATURAL_FEEDBACK_BASELINE_SURVIVOR"
        ],
        "by_service_process": {
            key: dict(sorted(value.items())) for key, value in sorted(by_process.items())
        },
        "by_composition": {
            key: dict(sorted(value.items())) for key, value in sorted(by_composition.items())
        },
        "by_feedback_profile": {
            key: dict(sorted(value.items())) for key, value in sorted(by_feedback.items())
        },
        "rows": rows,
        "claim_boundary": [
            "This is a 36-axis-cell placement-specific pilot, not a benchmark distribution estimate or hard-case count.",
            "Each cell is selected before solving; solver/baseline outcomes do not alter the frozen v0.7 generator or selection index.",
            "UNRESOLVED_COMPUTATION is not counted as hard, infeasible, or method failure.",
            "A natural-feedback candidate solved by any same-information ordinary baseline is downgraded to shortcut/control.",
            "Gateway-local owner state is not charged as remote acquisition; no paid-evidence or center-placement claim is made.",
        ],
    }
    DEFAULT_OUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "out": str(DEFAULT_OUT.relative_to(ROOT)),
        "raw": payload["raw_disposition_counts"],
        "final": payload["final_pilot_disposition_counts"],
        "unresolved": payload["unresolved_ordinals"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
