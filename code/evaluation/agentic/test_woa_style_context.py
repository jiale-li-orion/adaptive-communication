#!/usr/bin/env python3
"""WOA-style baseline must share candidates while receiving stronger evidence input."""
from __future__ import annotations

from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agentic_communication.episodes import benchmark_episode_catalog  # noqa: E402
from agentic_communication.planner import CompiledChecklistPlannerConsumer  # noqa: E402
from agentic_communication.replay import frozen_r1_inputs  # noqa: E402
from agentic_communication.run import run_agentic_episode  # noqa: E402


def _fragments(assembly):
    return {row.kind: row.content for row in assembly.fragments}


def _requested_assemblies(policy):
    frozen = {row.assembly.assembly_id: row.assembly for row in frozen_r1_inputs(policy.trace.events)}
    out = []
    for event in policy.trace.events:
        if event.event_type != "model_request":
            continue
        assembly_id = str(event.payload.get("assembly_id") or "")
        if assembly_id in frozen:
            out.append(frozen[assembly_id])
    return out


def main() -> int:
    episode = benchmark_episode_catalog()["O6"]
    outputs = {}
    for mode in ("action_conditioned_compact", "woa_style"):
        result, policy, _, _ = run_agentic_episode(
            seed=0,
            operational_task=episode.task,
            context_mode=mode,
            planner_consumer=CompiledChecklistPlannerConsumer(),
            planner_replan_mode="decision_state",
            simulator_kwargs=episode.simulator_overrides,
        )
        outputs[mode] = (result, _requested_assemblies(policy))

    compact = outputs["action_conditioned_compact"][1]
    woa = outputs["woa_style"][1]
    assert len(compact) == len(woa) == 11, (len(compact), len(woa))

    for left, right in zip(compact, woa, strict=True):
        lf = _fragments(left)
        rf = _fragments(right)
        lc = dict(lf["candidate_action_context"])
        rc = dict(rf["candidate_action_context"])
        assert "decision_sufficiency" in lc
        assert "decision_sufficiency" not in rc
        lc.pop("decision_sufficiency", None)
        assert lc == rc, (left.context_manifest_revision, lc, rc)
        assert len(rf.get("evidence_slice") or []) >= len(lf.get("evidence_slice") or [])
        assert lf.get("resource_inventory") == rf.get("resource_inventory")
        assert lf.get("capability_catalog") == rf.get("capability_catalog")
        assert lf.get("evidence_needs") == rf.get("evidence_needs")

    print(
        "PASS WOA-style context: same compact candidate/need/control surface, "
        "no Method sufficiency certificate, FullDump legal evidence"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

