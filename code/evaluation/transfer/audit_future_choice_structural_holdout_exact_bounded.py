#!/usr/bin/env python3
"""Resource-bounded exact strong controls for the frozen B6 holdout.

Each motif × baseline sequence executes in its own subprocess.  Event results are
checkpointed before advancing, so a later timeout/OOM preserves earlier exact
frontiers.  Resource termination is reported as UNRESOLVED_COMPUTATION and is
never converted to infeasibility.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
TRANSFER = ROOT / "code/evaluation/transfer"
BENCH = ROOT / "code/evaluation/benchmark"
AGENTIC = ROOT / "code/evaluation/agentic"
for _p in (TRANSFER, BENCH, AGENTIC):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from audit_future_choice_structural_holdout import (  # noqa: E402
    MATERIALIZERS,
    _exact_row,
)
from layer2_v2_dependency_cache_baseline import PersistentDependencyExact  # noqa: E402
from layer2_v2_incremental_exact_baseline import PersistentOrderedExact  # noqa: E402


OUT = ROOT / "results/transfer/future-choice-structural-holdout-exact-bounded.json"
BASELINES = ("fresh", "persistent", "dependency")


def _append(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        fh.flush()


def _child(motif: str, baseline: str, checkpoint: Path) -> int:
    bundle, events, _expected = MATERIALIZERS[motif]()
    if checkpoint.exists():
        checkpoint.unlink()
    planner = None
    if baseline == "persistent":
        planner = PersistentOrderedExact(bundle)
    elif baseline == "dependency":
        planner = PersistentDependencyExact(bundle)
    elif baseline != "fresh":
        raise ValueError(baseline)

    for index, (label, at_s, state) in enumerate(events):
        current = PersistentOrderedExact(bundle) if baseline == "fresh" else planner
        assert current is not None
        try:
            row = _exact_row(current, at_s, state)
        except MemoryError:
            # Best effort: the parent also detects abrupt memory termination if
            # the interpreter cannot allocate enough memory to serialize this.
            _append(
                checkpoint,
                {
                    "event_index": index,
                    "event": label,
                    "status": "UNRESOLVED_COMPUTATION",
                    "reason": "MEMORY_LIMIT",
                },
            )
            return 75
        _append(
            checkpoint,
            {
                "event_index": index,
                "event": label,
                "at_s": at_s,
                "status": "RESOLVED",
                "frontier": row,
            },
        )
    return 0


def _limit_memory(mib: int) -> None:
    limit = int(mib) * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))


def _read_checkpoint(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _run_child(
    motif: str,
    baseline: str,
    *,
    timeout_s: int,
    memory_mib: int,
    checkpoint: Path,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--child",
        "--motif",
        motif,
        "--baseline",
        baseline,
        "--checkpoint",
        str(checkpoint),
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=timeout_s,
            env={
                **os.environ,
                "OPENBLAS_NUM_THREADS": "1",
                "OMP_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1",
                "NUMEXPR_NUM_THREADS": "1",
            },
            preexec_fn=lambda: _limit_memory(memory_mib),
        )
        rows = _read_checkpoint(checkpoint)
        if result.returncode == 0:
            run_status = "RESOLVED_SEQUENCE"
            reason = None
        else:
            run_status = "UNRESOLVED_COMPUTATION"
            reason = (
                "MEMORY_LIMIT"
                if result.returncode == 75 or "MemoryError" in result.stderr
                else f"EXIT_{result.returncode}"
            )
        return {
            "motif": motif,
            "baseline": baseline,
            "status": run_status,
            "reason": reason,
            "returncode": result.returncode,
            "events_checkpointed": rows,
            "stderr_tail": result.stderr[-2000:],
        }
    except subprocess.TimeoutExpired as exc:
        rows = _read_checkpoint(checkpoint)
        return {
            "motif": motif,
            "baseline": baseline,
            "status": "UNRESOLVED_COMPUTATION",
            "reason": "TIMEOUT",
            "returncode": None,
            "events_checkpointed": rows,
            "stderr_tail": (exc.stderr or "")[-2000:] if isinstance(exc.stderr, str) else "",
        }


def _aggregate(runs: list[dict[str, Any]], timeout_s: int, memory_mib: int) -> dict[str, Any]:
    by = {(r["motif"], r["baseline"]): r for r in runs}
    motifs = []
    for motif, materializer in MATERIALIZERS.items():
        _bundle, events, _expected = materializer()
        event_rows = []
        for index, (label, at_s, _state) in enumerate(events):
            cells = {}
            for baseline in BASELINES:
                run = by[(motif, baseline)]
                resolved = next(
                    (
                        row
                        for row in run["events_checkpointed"]
                        if int(row["event_index"]) == index
                        and row.get("status") == "RESOLVED"
                    ),
                    None,
                )
                cells[baseline] = resolved
            resolved_frontiers = [
                cell["frontier"]["actions"]
                for cell in cells.values()
                if cell is not None
            ]
            all_three = len(resolved_frontiers) == 3
            match = all_three and all(
                frontier == resolved_frontiers[0]
                for frontier in resolved_frontiers[1:]
            )
            event_rows.append(
                {
                    "event_index": index,
                    "event": label,
                    "at_s": at_s,
                    "resolved_baselines": [
                        baseline for baseline, cell in cells.items() if cell is not None
                    ],
                    "all_three_resolved": all_three,
                    "exact_frontiers_match_if_all_resolved": match if all_three else None,
                    "frontiers": {
                        baseline: (cell["frontier"] if cell is not None else None)
                        for baseline, cell in cells.items()
                    },
                }
            )
        motifs.append(
            {
                "motif": motif,
                "runs": {baseline: by[(motif, baseline)] for baseline in BASELINES},
                "events": event_rows,
                "resolved_event_count_all_three": sum(
                    row["all_three_resolved"] for row in event_rows
                ),
                "matching_event_count_all_three": sum(
                    row["exact_frontiers_match_if_all_resolved"] is True
                    for row in event_rows
                ),
            }
        )

    all_resolved_comparisons_match = all(
        row["exact_frontiers_match_if_all_resolved"] is not False
        for motif in motifs
        for row in motif["events"]
    )
    payload = {
        "stage": "FUTURE_CHOICE_B6_EXACT_STRONG_CONTROL_BOUNDED",
        "resource_contract": {
            "memory_mib_per_process": memory_mib,
            "timeout_s_per_motif_baseline_sequence": timeout_s,
            "baseline_processes": len(MATERIALIZERS) * len(BASELINES),
        },
        "motifs": motifs,
        "checks": {
            "all_resolved_exact_comparisons_match": all_resolved_comparisons_match,
            "resource_termination_never_treated_as_infeasible": True,
        },
        "summary": {
            "resolved_sequences": sum(r["status"] == "RESOLVED_SEQUENCE" for r in runs),
            "unresolved_sequences": sum(r["status"] != "RESOLVED_SEQUENCE" for r in runs),
            "unresolved_reasons": sorted(
                {
                    r["reason"]
                    for r in runs
                    if r["status"] != "RESOLVED_SEQUENCE"
                }
            ),
            "events_all_three_resolved": sum(
                m["resolved_event_count_all_three"] for m in motifs
            ),
            "events_all_three_matching": sum(
                m["matching_event_count_all_three"] for m in motifs
            ),
        },
        "claim_boundary": [
            "B6 structural correctness is owned by the separate incremental-vs-fresh holdout artifact; exact strong controls here are bounded resource diagnostics.",
            "Any timeout or memory termination is UNRESOLVED_COMPUTATION, never infeasibility.",
            "Only events where all three exact baselines resolve are eligible for exact-frontier equivalence claims."
        ],
    }
    if not all(payload["checks"].values()):
        raise AssertionError(payload["checks"])
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--child", action="store_true")
    ap.add_argument("--motif", choices=tuple(MATERIALIZERS))
    ap.add_argument("--baseline", choices=BASELINES)
    ap.add_argument("--checkpoint", type=Path)
    ap.add_argument("--timeout-s", type=int, default=30)
    ap.add_argument("--memory-mib", type=int, default=512)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if args.child:
        if not args.motif or not args.baseline or not args.checkpoint:
            raise SystemExit("child mode requires --motif --baseline --checkpoint")
        return _child(args.motif, args.baseline, args.checkpoint)

    runs = []
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        for motif in MATERIALIZERS:
            for baseline in BASELINES:
                checkpoint = base / f"{motif}__{baseline}.jsonl"
                run = _run_child(
                    motif,
                    baseline,
                    timeout_s=args.timeout_s,
                    memory_mib=args.memory_mib,
                    checkpoint=checkpoint,
                )
                runs.append(run)
                print(
                    motif,
                    baseline,
                    run["status"],
                    run["reason"],
                    "events",
                    len(run["events_checkpointed"]),
                    flush=True,
                )
    payload = _aggregate(runs, args.timeout_s, args.memory_mib)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"out": str(args.out), **payload["summary"], **payload["checks"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
