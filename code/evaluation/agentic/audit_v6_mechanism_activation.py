#!/usr/bin/env python3
"""Audit which Method mechanisms are actually activated in the formal v6 table.

This is a read-only diagnostic over the 15 audited Method traces.  It aligns
``model_request.assembly_id`` with the exact PromptAssembly consumed by the
planner, so ordinary Context refreshes that never reached the model do not count.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RESULT_ROOT = (
    ROOT
    / "results"
    / "agentic"
    / "main-table-v6-confirmatory"
    / "deepseek-flash"
)
OUT = ROOT / "results" / "agentic" / "v6-mechanism-activation-audit.json"
TASKS = ("localized-o2", "o5", "o6")
SEEDS = tuple(range(5))


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _trace_rows(path: Path) -> tuple[list[dict], list[dict]]:
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assemblies: dict[str, dict] = {}
    for event in events:
        if event.get("event_type") == "prompt_assembly":
            payload = event.get("payload") or {}
            assembly_id = str(payload.get("assembly_id") or "")
            if assembly_id:
                assemblies[assembly_id] = payload

    requested = []
    failures = []
    for event in events:
        if event.get("event_type") != "model_request":
            continue
        payload = event.get("payload") or {}
        assembly_id = str(payload.get("assembly_id") or "")
        assembly = assemblies.get(assembly_id)
        if assembly is None:
            failures.append(
                {
                    "type": "missing_requested_assembly",
                    "assembly_id": assembly_id,
                    "t_s": event.get("t_s"),
                }
            )
            continue
        fragments = {
            str(row.get("kind") or ""): row.get("content")
            for row in assembly.get("fragments", [])
            if isinstance(row, dict)
        }
        candidate = fragments.get("candidate_action_context") or {}
        plans = [row for row in candidate.get("candidate_plans", []) if isinstance(row, dict)]
        ready = [
            row
            for row in plans
            if row.get("feasibility") == "supported"
            and not bool(row.get("unresolved_conditions"))
        ]
        needs = [row for row in (fragments.get("evidence_needs") or []) if isinstance(row, dict)]
        blocking_needs = [row for row in needs if row.get("blocking_plan_ids")]
        sufficiency = candidate.get("decision_sufficiency") or {}
        requested.append(
            {
                "t_s": int(event.get("t_s") or 0),
                "assembly_id": assembly_id,
                "ready_supported_plan_ids": [str(row.get("plan_id")) for row in ready],
                "visible_evidence_need_ids": [str(row.get("need_id")) for row in needs],
                "blocking_need_ids": [str(row.get("need_id")) for row in blocking_needs],
                "decision_sufficiency_status": sufficiency.get("status"),
                "primary_plan_id": sufficiency.get("primary_plan_id"),
                "shadow_candidate_plan_ids": list(candidate.get("shadow_candidate_plan_ids") or []),
            }
        )
    return requested, failures


def main() -> int:
    rows = []
    failures = []
    trace_hashes = {}
    per_episode = []
    for task in TASKS:
        for seed in SEEDS:
            trace = (
                RESULT_ROOT
                / task
                / f"seed-{seed:03d}"
                / "action_conditioned_compact"
                / "runtime_trace.jsonl"
            )
            if not trace.is_file():
                failures.append({"type": "missing_trace", "task": task, "seed": seed})
                continue
            trace_hashes[str(trace.relative_to(ROOT))] = _sha(trace)
            episode_rows, episode_failures = _trace_rows(trace)
            for row in episode_rows:
                row["task"] = task
                row["seed"] = seed
            rows.extend(episode_rows)
            failures.extend(
                [{"task": task, "seed": seed, **failure} for failure in episode_failures]
            )
            per_episode.append(
                {
                    "task": task,
                    "seed": seed,
                    "planner_requests": len(episode_rows),
                    "unique_ready_plan_turns": sum(
                        len(row["ready_supported_plan_ids"]) == 1 for row in episode_rows
                    ),
                    "ambiguous_ready_plan_turns": sum(
                        len(row["ready_supported_plan_ids"]) > 1 for row in episode_rows
                    ),
                    "no_ready_plan_turns": sum(
                        not row["ready_supported_plan_ids"] for row in episode_rows
                    ),
                    "visible_need_turns": sum(
                        bool(row["visible_evidence_need_ids"]) for row in episode_rows
                    ),
                    "blocking_need_turns": sum(
                        bool(row["blocking_need_ids"]) for row in episode_rows
                    ),
                }
            )

    status_counts = Counter(str(row.get("decision_sufficiency_status")) for row in rows)
    plan_counts = Counter(str(row.get("primary_plan_id")) for row in rows)
    by_task = defaultdict(list)
    for row in rows:
        by_task[row["task"]].append(row)

    aggregate = {
        "episodes": len(per_episode),
        "planner_requests": len(rows),
        "unique_ready_plan_turns": sum(len(row["ready_supported_plan_ids"]) == 1 for row in rows),
        "ambiguous_ready_plan_turns": sum(len(row["ready_supported_plan_ids"]) > 1 for row in rows),
        "no_ready_plan_turns": sum(not row["ready_supported_plan_ids"] for row in rows),
        "visible_evidence_need_turns": sum(bool(row["visible_evidence_need_ids"]) for row in rows),
        "blocking_plan_local_need_turns": sum(bool(row["blocking_need_ids"]) for row in rows),
        "shadow_candidate_visible_turns": sum(bool(row["shadow_candidate_plan_ids"]) for row in rows),
        "decision_sufficiency_status_counts": dict(sorted(status_counts.items())),
        "primary_plan_counts": dict(sorted(plan_counts.items())),
        "by_task": {
            task: {
                "planner_requests": len(task_rows),
                "unique_ready_plan_turns": sum(
                    len(row["ready_supported_plan_ids"]) == 1 for row in task_rows
                ),
                "visible_evidence_need_turns": sum(
                    bool(row["visible_evidence_need_ids"]) for row in task_rows
                ),
                "blocking_plan_local_need_turns": sum(
                    bool(row["blocking_need_ids"]) for row in task_rows
                ),
            }
            for task, task_rows in sorted(by_task.items())
        },
    }
    passed = (
        not failures
        and len(per_episode) == 15
        and len(rows) == 123
        and aggregate["unique_ready_plan_turns"] == 123
        and aggregate["ambiguous_ready_plan_turns"] == 0
        and aggregate["no_ready_plan_turns"] == 0
        and aggregate["visible_evidence_need_turns"] == 0
        and aggregate["blocking_plan_local_need_turns"] == 0
    )
    payload = {
        "experiment": "v6-mechanism-activation-audit",
        "status": "PASS" if passed else "FAIL",
        "source_result_root": str(RESULT_ROOT.relative_to(ROOT)),
        "trace_sha256": trace_hashes,
        "aggregate": aggregate,
        "per_episode": per_episode,
        "failures": failures,
        "interpretation_boundary": (
            "This audit only measures whether the frozen v6 Method requests activate multiple "
            "ready plans or visible EvidenceNeeds. It does not prove such mechanisms are unnecessary "
            "outside the measured tasks/seeds."
        ),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], **aggregate}, ensure_ascii=False, indent=2))
    print(f"WROTE {OUT}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

