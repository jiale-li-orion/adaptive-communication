#!/usr/bin/env python3
"""Minimal dependency-expressiveness probe for Astra Candidate 1.

No model calls and no new solver.  Compare the current hand-authored
``blocking_plan_ids`` against two ordinary compiler baselines:

1. guard-name backward slice: a dependency blocks every plan whose declared
   decision_guards mention the same guard family;
2. the same slice plus ordinary current-state partial evaluation: among unresolved
   dependencies, a currently supported plan with no unresolved conditions is not
   blocked merely because the guard family appears in its declaration.

The goal is diagnostic: if the ordinary baselines recover the current dependency
scope, automatic dependency construction is compiler substrate rather than a
demonstrated algorithmic gap.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = CODE.parent
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agentic_communication.episodes import (  # noqa: E402
    benchmark_episode_catalog,
    o2_localized_risk_escalation_task,
)
from agentic_communication.planner import DeterministicComplyPlannerConsumer  # noqa: E402
from agentic_communication.run import DEFAULT_FULLSIM, run_agentic_episode  # noqa: E402


OUT = ROOT / "results" / "agentic" / "dependency-expressiveness-probe-v1" / "result.json"


def _canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _candidate_from_prompt(event) -> dict | None:
    for fragment in event.payload.get("fragments", []):
        if isinstance(fragment, dict) and fragment.get("kind") == "candidate_action_context":
            content = fragment.get("content")
            return content if isinstance(content, dict) else None
    return None


def _closure(candidate: dict) -> tuple[bool, str]:
    disagreement = candidate.get("candidate_disagreement") or {}
    closure = disagreement.get("action_closure") or {}
    return (
        bool(closure.get("closed_for_current_candidate_family")),
        str(closure.get("control_eligibility") or "unknown"),
    )


def _plan_maps(candidate: dict) -> tuple[dict[str, dict], set[str]]:
    plans = {
        str(plan.get("plan_id")): plan
        for plan in candidate.get("candidate_plans", [])
        if isinstance(plan, dict) and plan.get("plan_id")
    }
    live = {
        plan_id
        for plan_id, plan in plans.items()
        if plan.get("feasibility") not in {"dominated", "rejected"}
    }
    return plans, live


def _syntax_slice(scope_reason: str, plans: dict[str, dict], allowed: set[str]) -> set[str]:
    return {
        plan_id
        for plan_id in allowed
        if scope_reason in dict(plans[plan_id].get("decision_guards") or {})
    }


def _partial_eval_slice(
    *,
    scope_reason: str,
    plans: dict[str, dict],
    live: set[str],
    dependency_fresh: bool,
) -> set[str]:
    sliced = _syntax_slice(scope_reason, plans, live)
    if dependency_fresh:
        return sliced
    # Ordinary current-state partial evaluation: if the candidate compiler has
    # already established a plan as supported with no unresolved condition while
    # this dependency remains unknown/stale, that unknown cannot be a current
    # blocker for the plan.  This adds no future/oracle information.
    return {
        plan_id
        for plan_id in sliced
        if not (
            plans[plan_id].get("feasibility") == "supported"
            and not (plans[plan_id].get("unresolved_conditions") or [])
        )
    }


def _set_metrics(pred: set[str], gold: set[str]) -> dict:
    tp = len(pred & gold)
    fp = len(pred - gold)
    fn = len(gold - pred)
    precision = 1.0 if not pred else tp / len(pred)
    recall = 1.0 if not gold else tp / len(gold)
    return {
        "exact": pred == gold,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
    }


def _episode_specs():
    specs = []
    for name, episode in benchmark_episode_catalog().items():
        specs.append((name, episode.task, dict(episode.simulator_overrides)))
    specs.append(("O2-localized", o2_localized_risk_escalation_task(), dict(DEFAULT_FULLSIM)))
    return specs


def main() -> int:
    occurrences: list[dict] = []
    seen_states: set[str] = set()
    unique_rows: list[dict] = []

    for episode_name, task, simulator_kwargs in _episode_specs():
        _, policy, _, _ = run_agentic_episode(
            seed=0,
            operational_task=task,
            context_mode="action_conditioned",
            planner_consumer=DeterministicComplyPlannerConsumer(),
            planner_replan_mode="every_context",
            simulator_kwargs=simulator_kwargs,
        )
        for event in policy.trace.events:
            if event.event_type != "prompt_assembly":
                continue
            candidate = _candidate_from_prompt(event)
            if not candidate:
                continue
            plans, live = _plan_maps(candidate)
            closed, eligibility = _closure(candidate)
            state_basis = {
                "episode": episode_name,
                "phase_index": candidate.get("phase_index"),
                "required_period_s": candidate.get("required_period_s"),
                "plans": [
                    {
                        "plan_id": pid,
                        "feasibility": plans[pid].get("feasibility"),
                        "decision_guards": plans[pid].get("decision_guards") or {},
                        "unresolved_conditions": plans[pid].get("unresolved_conditions") or [],
                    }
                    for pid in sorted(plans)
                ],
                "dependencies": [
                    {
                        key: dep.get(key)
                        for key in (
                            "proposition",
                            "subject",
                            "scope_reason",
                            "blocking_plan_ids",
                            "fresh",
                            "acquisition",
                        )
                    }
                    for dep in candidate.get("dependencies", [])
                    if isinstance(dep, dict)
                ],
            }
            state_hash = hashlib.sha256(_canonical(state_basis).encode("utf-8")).hexdigest()

            state_rows: list[dict] = []
            for dep in candidate.get("dependencies", []):
                if not isinstance(dep, dict):
                    continue
                scope_reason = str(dep.get("scope_reason") or "")
                gold_all = set(str(x) for x in (dep.get("blocking_plan_ids") or []))
                syntax_all = _syntax_slice(scope_reason, plans, set(plans))
                gold_live = gold_all & live
                syntax_live = _syntax_slice(scope_reason, plans, live)
                partial_live = _partial_eval_slice(
                    scope_reason=scope_reason,
                    plans=plans,
                    live=live,
                    dependency_fresh=bool(dep.get("fresh")),
                )
                row = {
                    "episode": episode_name,
                    "t_s": int(event.t_s),
                    "state_hash": state_hash,
                    "phase_index": candidate.get("phase_index"),
                    "action_closure_closed": closed,
                    "control_eligibility": eligibility,
                    "proposition": dep.get("proposition"),
                    "subject": dep.get("subject"),
                    "scope_reason": scope_reason,
                    "fresh": bool(dep.get("fresh")),
                    "acquisition": dep.get("acquisition"),
                    "gold_all": sorted(gold_all),
                    "syntax_all": sorted(syntax_all),
                    "structural_syntax_metrics": _set_metrics(syntax_all, gold_all),
                    "gold_live": sorted(gold_live),
                    "syntax_live": sorted(syntax_live),
                    "partial_eval_live": sorted(partial_live),
                    "runtime_syntax_metrics": _set_metrics(syntax_live, gold_live),
                    "runtime_partial_eval_metrics": _set_metrics(partial_live, gold_live),
                }
                state_rows.append(row)
                occurrences.append(row)
            if state_hash not in seen_states:
                seen_states.add(state_hash)
                unique_rows.extend(state_rows)

    def summarize(rows: list[dict], metric_key: str) -> dict:
        return {
            "rows": len(rows),
            "exact_rows": sum(bool(row[metric_key]["exact"]) for row in rows),
            "fp": sum(int(row[metric_key]["fp"]) for row in rows),
            "fn": sum(int(row[metric_key]["fn"]) for row in rows),
        }

    unresolved = [row for row in unique_rows if not row["fresh"]]
    unresolved_eligible = [
        row
        for row in unresolved
        if row["action_closure_closed"] and row["control_eligibility"] == "eligible"
    ]
    unresolved_shadow = [row for row in unresolved if row not in unresolved_eligible]

    disagreements = [
        row
        for row in unique_rows
        if not row["structural_syntax_metrics"]["exact"]
        or (
            not row["fresh"]
            and (
                not row["runtime_syntax_metrics"]["exact"]
                or not row["runtime_partial_eval_metrics"]["exact"]
            )
        )
    ]
    scope_counts = Counter(row["scope_reason"] for row in unique_rows)
    result = {
        "schema_revision": "1",
        "experiment_id": "dependency-expressiveness-probe-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "seed": 0,
        "episodes": [name for name, _, _ in _episode_specs()],
        "claim_boundary": (
            "Diagnostic only: tests whether current hand-authored blocking scope exceeds ordinary guard slicing "
            "and current-state partial evaluation on existing candidate graphs. It is not an algorithm gain."
        ),
        "baselines": {
            "syntax_slice": "dependency scope_reason blocks live plans declaring the same decision_guards key",
            "partial_eval": (
                "syntax_slice plus removal of currently supported/no-unresolved plans when the dependency itself "
                "is unresolved; no future/oracle information"
            ),
        },
        "unique_candidate_states": len(seen_states),
        "unique_dependency_rows": len(unique_rows),
        "occurrence_dependency_rows": len(occurrences),
        "scope_reason_counts": dict(sorted(scope_counts.items())),
        "structural_all_dependencies": {
            "syntax_slice": summarize(unique_rows, "structural_syntax_metrics"),
        },
        "runtime_unresolved_dependencies": {
            "all": {
                "syntax_slice": summarize(unresolved, "runtime_syntax_metrics"),
                "partial_eval": summarize(unresolved, "runtime_partial_eval_metrics"),
            },
            "eligible_closed_family": {
                "rows": len(unresolved_eligible),
                "syntax_slice": summarize(unresolved_eligible, "runtime_syntax_metrics"),
                "partial_eval": summarize(unresolved_eligible, "runtime_partial_eval_metrics"),
            },
            "shadow_or_open_family": {
                "rows": len(unresolved_shadow),
                "syntax_slice": summarize(unresolved_shadow, "runtime_syntax_metrics"),
                "partial_eval": summarize(unresolved_shadow, "runtime_partial_eval_metrics"),
            },
        },
        "disagreements": disagreements,
        "unique_rows": unique_rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "unique_candidate_states": result["unique_candidate_states"],
                "unique_dependency_rows": result["unique_dependency_rows"],
                "structural_all_dependencies": result["structural_all_dependencies"],
                "runtime_unresolved_dependencies": result["runtime_unresolved_dependencies"],
                "disagreement_rows": len(disagreements),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"WROTE {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

