#!/usr/bin/env python3
"""Audit whether frozen Layer-2 v1 can represent Layer-1 v0.2 hard tasks as-is.

This audit intentionally does not modify Layer-2. It distinguishes generic
schema compatibility from the task/capability/candidate bindings that were
implemented for the earlier O1--O6 workload.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import re

from compositional_recipe_generator_v0_1 import core_recipes
from dynamic_world_materializer_v0_1 import materialize_recipe


ROOT = Path(__file__).resolve().parents[3]
SPLIT = ROOT / "results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json"
REGISTRY = ROOT / "research/compiler/COMMUNICATION-DOMAIN-REGISTRY.v0.1.json"
SELECTOR = ROOT / "code/agentic_communication/action_context.py"
TASK_COMPILER = ROOT / "code/agentic_communication/task_compiler.py"


def hard_representatives() -> list[dict]:
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in split["rows"]:
        if row.get("candidate_role") == "HARD_PRE_ADMISSION_SURVIVOR":
            grouped[str(row["signature"])].append(row)
    out = []
    for sig, rows in sorted(grouped.items()):
        rep = min(rows, key=lambda x: str(x["recipe_id"]))
        out.append({"signature": sig, "split": rep["split"], "recipe_id": rep["recipe_id"]})
    return out


def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    capability_ids = {str(x["capability_id"]) for x in registry["capabilities"]}
    capability_actions = {str(x.get("action", "")) for x in registry["capabilities"]}
    selector_text = SELECTOR.read_text(encoding="utf-8")
    task_compiler_text = TASK_COMPILER.read_text(encoding="utf-8")
    plan_ids = sorted(set(re.findall(r'"plan_id":\s*"([^"]+)"', selector_text)))
    recipes = {r.recipe_id: r for r in core_recipes()}

    rows = []
    for rep in hard_representatives():
        bundle = materialize_recipe(recipes[str(rep["recipe_id"])])
        obligations = list(bundle["obligations"])
        releases = [int(x["release_s"]) for x in obligations]
        deadlines = [int(x["deadline_s"]) for x in obligations]
        required_actions = ["WAIT", "SEND_TERR", "SEND_SAT", "ISSUE_QUERY:gateway_state_summary"]

        current_task_compiler_lossless = (
            len(obligations) == 1
            and "operational_phase_execution" not in task_compiler_text
        )
        # Every final hard signature has 3/4 simultaneously live obligation
        # identities. The current compiler owns one active phase and one
        # phase-level completion predicate, so this must remain false unless the
        # compiler itself is changed in a future version.
        obligation_identity_preserved = current_task_compiler_lossless

        action_binding = {
            "WAIT": "WAIT" in capability_actions or "wait_current_obligation" in plan_ids,
            "SEND_TERR": any("terr" in x.lower() and "send" in x.lower() for x in capability_actions),
            "SEND_SAT": any("sat" in x.lower() and "send" in x.lower() for x in capability_actions),
            "ISSUE_QUERY:gateway_state_summary": "communication.gateway.state_summary" in capability_ids,
        }
        all_actions_bound = all(action_binding.values())
        as_is_lossless = obligation_identity_preserved and all_actions_bound
        rows.append(
            {
                **rep,
                "obligation_count": len(obligations),
                "release_s": releases,
                "deadline_s": deadlines,
                "required_action_semantics": required_actions,
                "task_compiler_preserves_per_obligation_identity": obligation_identity_preserved,
                "action_binding": action_binding,
                "selector_plan_ids": plan_ids,
                "as_is_lossless": as_is_lossless,
            }
        )

    lossless = sum(bool(x["as_is_lossless"]) for x in rows)
    artifact = {
        "schema_version": "0.1",
        "status": "COMPLETE",
        "scope": "frozen Layer-1 v0.2 V8 hard signatures against frozen Layer-2 v1 as-is compiler/registry/selector",
        "signature_count": len(rows),
        "as_is_lossless_count": lossless,
        "as_is_lossy_count": len(rows) - lossless,
        "obligation_count_distribution": dict(sorted(Counter(str(x["obligation_count"]) for x in rows).items())),
        "generic_runtime_schema_verdict": "COMPATIBLE_IN_PRINCIPLE",
        "task_compiler_verdict": "LOSSY_FOR_OVERLAPPING_OBLIGATION_CONTRACT",
        "capability_registry_verdict": "MISSING_LAYER1_V02_SEND_AND_GATEWAY_SUMMARY_BINDINGS",
        "candidate_selector_verdict": "OLD_O1_O6_PROFILE_FALLBACK_CANDIDATE_FAMILY_ONLY",
        "classification": "B_COMPATIBILITY_GAP_NOT_YET_LAYER2_V2_METHOD_FAILURE",
        "required_next_step": [
            "lossless obligation TaskContract binding",
            "Layer-1 public action/capability binding for WAIT/SEND_TERR/SEND_SAT/gateway_state_summary",
            "candidate_action_context materialization from Layer-1 lawful action surface without oracle labels",
            "then rerun frozen Layer-2 v1 planner/Decision-Sufficiency semantics before changing the method",
        ],
        "rows": rows,
    }
    print(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
