#!/usr/bin/env python3
"""No-API fairness audit for the WOA-style same-interface baseline."""
from __future__ import annotations

import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = HERE.parents[2]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agentic_communication.episodes import benchmark_episode_catalog, o2_localized_risk_escalation_task  # noqa: E402
from agentic_communication.metrics import physical_signature  # noqa: E402
from agentic_communication.planner import CompiledChecklistPlannerConsumer  # noqa: E402
from agentic_communication.run import run_agentic_episode  # noqa: E402


OUT = ROOT / "results" / "agentic" / "woa-style-baseline-v1" / "fairness-audit.json"
TASKS = (
    ("localized-o2", o2_localized_risk_escalation_task(), {}),
    ("o5", benchmark_episode_catalog()["O5"].task, benchmark_episode_catalog()["O5"].simulator_overrides),
    ("o6", benchmark_episode_catalog()["O6"].task, benchmark_episode_catalog()["O6"].simulator_overrides),
)


def _requested(policy):
    assemblies = {}
    for event in policy.trace.events:
        if event.event_type == "prompt_assembly":
            assemblies[str(event.payload.get("assembly_id"))] = event
    rows = []
    for event in policy.trace.events:
        if event.event_type != "model_request":
            continue
        assembly = assemblies[str(event.payload.get("assembly_id"))]
        fragments = {
            str(row.get("kind")): row.get("content")
            for row in assembly.payload.get("fragments", [])
            if isinstance(row, dict)
        }
        rows.append({"t_s": int(event.t_s), "fragments": fragments})
    return rows


def _candidate_without_sufficiency(value):
    row = dict(value or {})
    row.pop("decision_sufficiency", None)
    return row


def main() -> int:
    episodes = []
    failures = []
    for task_name, task, sim in TASKS:
        for seed in range(5):
            results = {}
            for mode in ("action_conditioned_compact", "woa_style"):
                result, policy, _, _ = run_agentic_episode(
                    seed=seed,
                    operational_task=task,
                    context_mode=mode,
                    planner_consumer=CompiledChecklistPlannerConsumer(),
                    planner_replan_mode="decision_state",
                    simulator_kwargs=sim,
                )
                results[mode] = (result, _requested(policy))

            compact_result, compact = results["action_conditioned_compact"]
            woa_result, woa = results["woa_style"]
            episode_failures = []
            if physical_signature(compact_result) != physical_signature(woa_result):
                episode_failures.append("deterministic_physical_signature_differs")
            if [row["t_s"] for row in compact] != [row["t_s"] for row in woa]:
                episode_failures.append("planner_request_times_differ")
            if len(compact) != len(woa):
                episode_failures.append("planner_request_count_differs")

            evidence_expansion = []
            for idx, (left, right) in enumerate(zip(compact, woa, strict=False)):
                lf = left["fragments"]
                rf = right["fragments"]
                if _candidate_without_sufficiency(lf.get("candidate_action_context")) != rf.get(
                    "candidate_action_context"
                ):
                    episode_failures.append(f"candidate_surface_differs@{idx}")
                for kind in ("evidence_needs", "resource_inventory", "capability_catalog", "runtime_task_contract"):
                    if lf.get(kind) != rf.get(kind):
                        episode_failures.append(f"{kind}_differs@{idx}")
                if "decision_sufficiency" not in (lf.get("candidate_action_context") or {}):
                    episode_failures.append(f"compact_missing_sufficiency@{idx}")
                if "decision_sufficiency" in (rf.get("candidate_action_context") or {}):
                    episode_failures.append(f"woa_leaks_sufficiency@{idx}")
                left_evidence = list(lf.get("evidence_slice") or [])
                right_evidence = list(rf.get("evidence_slice") or [])
                if len(right_evidence) < len(left_evidence):
                    episode_failures.append(f"woa_has_less_evidence@{idx}")
                evidence_expansion.append(len(right_evidence) - len(left_evidence))

            episodes.append(
                {
                    "task": task_name,
                    "seed": seed,
                    "planner_requests": len(compact),
                    "physical_equal": physical_signature(compact_result) == physical_signature(woa_result),
                    "evidence_expansion_per_request": evidence_expansion,
                    "failures": episode_failures,
                }
            )
            failures.extend(
                {"task": task_name, "seed": seed, "failure": failure}
                for failure in episode_failures
            )

    payload = {
        "experiment": "woa-style-fairness-audit-v1",
        "status": "PASS" if not failures else "FAIL",
        "episodes": len(episodes),
        "planner_requests": sum(row["planner_requests"] for row in episodes),
        "physical_equal_episodes": sum(row["physical_equal"] for row in episodes),
        "failures": failures,
        "episode_rows": episodes,
        "allowed_differences": [
            "WOA-style evidence_slice may contain more legal Evidence World records",
            "WOA-style candidate_action_context omits decision_sufficiency",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "episodes": payload["episodes"],
                "planner_requests": payload["planner_requests"],
                "physical_equal_episodes": payload["physical_equal_episodes"],
                "failure_count": len(failures),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"WROTE {OUT}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

