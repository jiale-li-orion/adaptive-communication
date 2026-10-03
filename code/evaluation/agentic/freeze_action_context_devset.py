#!/usr/bin/env python3
"""Freeze a small pre-registered model dev set for action-conditioned context.

The selected times are defined from the localized-O2 episode schedule, not from
observed model failures:
  5h: primary-backhaul outage, before risk escalation
  6h: task revision / escalation boundary
  7h: escalated task while the primary outage persists
  8h: primary-backhaul recovery boundary

Each requested time maps to the first PromptAssembly at or after that simulator
time.  The same coordinates are used across all context arms.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = CODE.parent
for p in (CODE, CODE / "substrate" / "joint", CODE / "substrate" / "instance", CODE / "substrate" / "monitoring", CODE / "substrate" / "physics"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from agentic_communication.model_protocol import protocol_bytes, render_planner_protocol  # noqa: E402
from agentic_communication.replay import frozen_r1_inputs, load_trace  # noqa: E402


DEFAULT_INPUT = ROOT / "results" / "agentic" / "model-context-inputs-v1" / "localized" / "seed-000"
DEFAULT_OUT = ROOT / "results" / "agentic" / "action-context-devset-v1"
DEFAULT_CONTEXTS = (
    "task_conditioned",
    "full_dump",
    "generic_react",
    "action_conditioned",
    "action_candidates_full_dump",
)
EVENTS = (
    ("outage_pre_escalation", 5 * 3600),
    ("task_revision_escalation", 6 * 3600),
    ("escalated_during_outage", 7 * 3600),
    ("primary_recovery_boundary", 8 * 3600),
)


def _dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-root", default=str(DEFAULT_INPUT))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--contexts", default=",".join(DEFAULT_CONTEXTS))
    args = ap.parse_args()
    root = Path(args.input_root)
    out = Path(args.out)
    contexts = [x.strip() for x in args.contexts.split(",") if x.strip()]

    records_by_context = {}
    for mode in contexts:
        trace = root / "frozen_inputs" / f"{mode}.jsonl"
        if not trace.is_file():
            raise SystemExit(f"missing frozen input trace: {trace}")
        records_by_context[mode] = frozen_r1_inputs(load_trace(trace))

    chosen: dict[str, dict[str, object]] = {}
    # Coordinates are chosen on the action-conditioned trace, then shared by
    # simulator time across every arm.
    anchor = records_by_context["action_conditioned"]
    for event_id, requested_t in EVENTS:
        row = next((r for r in anchor if r.t_s >= requested_t), None)
        if row is None:
            raise RuntimeError(f"no prompt at/after {requested_t}s for {event_id}")
        chosen[event_id] = {"requested_t_s": requested_t, "selected_t_s": row.t_s}

    rows = []
    for event_id, coord in chosen.items():
        selected_t = int(coord["selected_t_s"])
        for mode in contexts:
            record = next((r for r in records_by_context[mode] if r.t_s == selected_t), None)
            if record is None:
                raise RuntimeError(f"{mode}: no prompt at selected time {selected_t}s")
            envelope = render_planner_protocol(record.assembly)
            raw = protocol_bytes(record.assembly)
            path = out / "inputs" / event_id / f"{mode}.json"
            _dump(path, envelope)
            rows.append(
                {
                    "event_id": event_id,
                    "requested_t_s": coord["requested_t_s"],
                    "selected_t_s": selected_t,
                    "context_mode": mode,
                    "task_run_id": record.task_run_id,
                    "trace_seq": record.seq,
                    "protocol_bytes": len(raw),
                    "protocol_sha256": _hash(raw),
                    "candidate_action_context": "candidate_action_context" in envelope,
                    "input": str(path.relative_to(ROOT)),
                }
            )
    manifest = {
        "schema_revision": "1",
        "experiment_id": "action-context-devset-v1",
        "source": str(root.relative_to(ROOT)),
        "selection_policy": (
            "pre-registered localized-O2 event times; first PromptAssembly at/after each time; "
            "same simulator time reused across context arms"
        ),
        "events": [
            {"event_id": event_id, **coord} for event_id, coord in chosen.items()
        ],
        "contexts": contexts,
        "rows": rows,
        "claim_ceiling": (
            "Frozen development inputs only. These coordinates support small-batch model diagnosis and "
            "R3 continuation; they are not selected from observed model failures."
        ),
    }
    _dump(out / "manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
