#!/usr/bin/env python3
"""Method-independent stratified oracle pilot on frozen Layer-1 v0.6 r4.

The pilot validates oracle semantics and search tractability before any full
admission sweep.  It chooses exactly one deterministic case per declared axis
cell:

  composition × service-process × terrestrial-capacity
  × feedback-profile × query-delay × fallback-mode

The representative is the lexicographically smallest case_id in that cell.
No baseline or method score participates in selection.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import argparse
import gzip
import json
from pathlib import Path
import subprocess
import time
from typing import Any

from layer1_v06_oracle_adapter import solve_v06_references


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUN = ROOT / "local_research/current/benchmark/generated/layer1-v0.6-preoracle-r4"


def _sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True
    ).stdout.strip()


def _rows(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def _base_meta(run: Path) -> dict[str, dict[str, Any]]:
    out = {}
    for row in _rows(run / "base-scenarios.jsonl.gz"):
        comp = row["composition"]
        out[str(row["base_id"])] = {
            "obligations_per_stream": int(comp["obligations_per_stream"]),
            "phase_mode": str(comp["phase_mode"]),
            "service_process": str(row["service_process"]["family"]),
            "terr_capacity": int(row["terrestrial"]["capacity_units_per_opportunity"]),
        }
    return out


def _cell_key(meta: dict[str, Any], case: dict[str, Any]) -> tuple[Any, ...]:
    return (
        meta["obligations_per_stream"],
        meta["phase_mode"],
        meta["service_process"],
        meta["terr_capacity"],
        str(case["feedback_profile"]),
        float(case["remote_query"]["response_delay_ratio"]),
        str(case["fallback_budget_mode"]),
    )


def _select_cases(run: Path, meta: dict[str, dict[str, Any]]) -> dict[tuple[Any, ...], dict[str, Any]]:
    selected: dict[tuple[Any, ...], dict[str, Any]] = {}
    for case in _rows(run / "cases.jsonl.gz"):
        m = meta[str(case["base_id"])]
        key = _cell_key(m, case)
        old = selected.get(key)
        if old is None or str(case["case_id"]) < str(old["case_id"]):
            selected[key] = case
    return selected


def _load_selected_bases(run: Path, base_ids: set[str]) -> dict[str, dict[str, Any]]:
    out = {}
    for row in _rows(run / "base-scenarios.jsonl.gz"):
        bid = str(row["base_id"])
        if bid in base_ids:
            out[bid] = row
    if set(out) != base_ids:
        missing = sorted(base_ids - set(out))[:10]
        raise ValueError(f"missing selected bases: {missing}")
    return out


def _status(ref: dict[str, Any]) -> tuple[str, bool | None]:
    return str(ref["status"]), ref["solvable"]


def disposition(result: dict[str, Any]) -> str:
    refs = result["references"]
    if any(str(v["status"]) == "SEARCH_LIMIT" for v in refs.values()):
        return "ORACLE_SEARCH_LIMIT"
    full = bool(refs["full_current"]["solvable"])
    exact = bool(refs["observation_matched_exact"]["solvable"])
    no_query = bool(refs["no_paid_query"]["solvable"])
    blind = bool(refs["blind_open_loop"]["solvable"])
    if not full:
        return "NON_ANTICIPATIVE_FULL_CURRENT_INFEASIBLE"
    if not exact:
        return "INFORMATION_INFEASIBLE"
    if blind:
        return "BLIND_OPEN_LOOP_SOLVED"
    if no_query:
        return "NATURAL_FEEDBACK_SUFFICIENT"
    return "PAID_EVIDENCE_REQUIRED_CANDIDATE"


def audit(run: Path, *, max_memo_nodes: int) -> dict[str, Any]:
    manifest = json.loads((run / "MANIFEST.json").read_text(encoding="utf-8"))
    meta = _base_meta(run)
    selected = _select_cases(run, meta)
    bases = _load_selected_bases(run, {str(c["base_id"]) for c in selected.values()})

    rows = []
    disp = Counter()
    by_process: dict[str, Counter[str]] = defaultdict(Counter)
    by_feedback: dict[str, Counter[str]] = defaultdict(Counter)
    by_fallback: dict[str, Counter[str]] = defaultdict(Counter)
    t0 = time.time()
    for key, case in sorted(selected.items(), key=lambda kv: kv[0]):
        base = bases[str(case["base_id"])]
        started = time.time()
        result = solve_v06_references(base, case, max_memo_nodes=max_memo_nodes)
        d = disposition(result)
        elapsed = time.time() - started
        disp[d] += 1
        by_process[str(base["service_process"]["family"])][d] += 1
        by_feedback[str(case["feedback_profile"])][d] += 1
        by_fallback[str(case["fallback_budget_mode"])][d] += 1
        compact_refs = {}
        for name, ref in result["references"].items():
            compact_refs[name] = {
                "status": ref["status"],
                "solvable": ref["solvable"],
                "memo_nodes": ref["memo_nodes"],
                "attempt_lattice_size": ref["attempt_lattice_size"],
            }
        rows.append(
            {
                "axis_cell": {
                    "obligations_per_stream": key[0],
                    "phase_mode": key[1],
                    "service_process": key[2],
                    "terr_capacity": key[3],
                    "feedback_profile": key[4],
                    "query_delay_ratio": key[5],
                    "fallback_mode": key[6],
                },
                "case_id": case["case_id"],
                "base_id": case["base_id"],
                "structure_id": case["structure_id"],
                "source_task_case_id": base["task"]["task_case_id"],
                "geometry_signature_id": base["satellite"]["geometry_signature_id"],
                "disposition": d,
                "elapsed_s": round(elapsed, 6),
                "references": compact_refs,
            }
        )

    return {
        "schema_version": "0.1",
        "stage": "V06_ORACLE_STRATIFIED_PILOT",
        "selection_rule": "one lexicographically-smallest case_id per composition×process×capacity×feedback×query-delay×fallback cell",
        "selection_depends_on_method_or_baseline": False,
        "official_generation_run": run.name,
        "official_generation_manifest_sha256": _sha(run / "MANIFEST.json"),
        "oracle_git_commit": _git_head(),
        "oracle_adapter_sha256": _sha(ROOT / "code/evaluation/benchmark/layer1_v06_oracle_adapter.py"),
        "exact_kernel_sha256": _sha(ROOT / "code/evaluation/benchmark/exact_reference_oracle_v0_1.py"),
        "max_memo_nodes_per_reference": max_memo_nodes,
        "axis_cell_count": len(selected),
        "elapsed_s": round(time.time() - t0, 3),
        "disposition_counts": dict(sorted(disp.items())),
        "by_service_process": {k: dict(sorted(v.items())) for k, v in sorted(by_process.items())},
        "by_feedback_profile": {k: dict(sorted(v.items())) for k, v in sorted(by_feedback.items())},
        "by_fallback_mode": {k: dict(sorted(v.items())) for k, v in sorted(by_fallback.items())},
        "rows": rows,
        "claim_boundary": [
            "Pilot validates oracle semantics/search tractability; it is not a benchmark distribution estimate.",
            "Representative selection is independent of policy/baseline outcome.",
            "No generator axis is changed by pilot results.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, default=DEFAULT_RUN)
    ap.add_argument("--max-memo-nodes", type=int, default=100_000)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    payload = audit(args.run.resolve(), max_memo_nodes=args.max_memo_nodes)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
