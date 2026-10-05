#!/usr/bin/env python3
"""Audit future-choice context validity/invalidation on exact-policy prefixes.

The audit treats the current dependency separator as the conservative reference
and attempts to falsify a cheaper event-frontier key that omits absolute time.
No candidate key is promoted merely because it compresses more states.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from audit_conditional_acquisition_timing_v0_1 import _initial
from causal_evidence_process_v0_1 import attach_causal_evidence
from continuation_dependency_separator_v0_1 import dependency_separator_key, separator_state
from continuation_resource_domains_v0_1 import ContinuationPlanner
from exact_reference_oracle_v0_1 import _attempt_lattice
from v8_policy_baselines_v0_1 import _normalize_one, _step


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUTS = ROOT / "results/benchmark/layer1-v0.2-hard-signature-bundles.json"
DEFAULT_REFERENCE = ROOT / "results/benchmark/layer2-future-choice-exact-reference-hard-dev-v0.2.json"
DEFAULT_OUT = ROOT / "results/benchmark/layer2-future-choice-context-validity-dev-v0.1.json"


def _truth(boundary: dict[str, Any]) -> tuple[Any, ...]:
    t = boundary["truth"]
    return (
        tuple(boundary["legal_action_keys"]),
        tuple(boundary["certified_action_keys"]),
        bool(t["defer"]), bool(t["harmful"]), bool(t["required"]), bool(t["stop"]),
    )


def _resource_coordinate(states, query_budget: int) -> tuple[Any, ...]:
    return (
        int(query_budget),
        tuple(sorted((str(wid), int(st.satellite_budget)) for wid, st in states.items())),
    )


def _future_structure(bundle, at_s: int) -> tuple[Any, ...]:
    obligations = tuple(
        (str(o["obligation_id"]), int(o["release_s"]), int(o["deadline_s"]))
        for o in bundle["obligations"]
        if int(o["deadline_s"]) > at_s
    )
    terrestrial = tuple(
        (
            str(w["world_id"]),
            tuple(
                (str(x["window_id"]), int(x["start_s"]), int(x["end_s"]), int(x["capacity_units"]))
                for x in w["terrestrial_windows"]
                if int(x["end_s"]) > at_s
            ),
        )
        for w in bundle["worlds"]
    )
    satellite = tuple(
        (str(x["window_id"]), int(x["start_s"]), int(x["end_s"]), int(x["capacity_units"]))
        for x in bundle["public_environment"]["satellite_windows"]
        if int(x["end_s"]) > at_s
    )
    return obligations, terrestrial, satellite


def _event_frontier_key(bundle, process, at_s: int, states, query_budget: int) -> tuple[Any, ...]:
    # Intentionally omits absolute time. The audit must falsify this key if
    # remaining slack matters despite identical future object membership.
    projected = tuple(
        sorted(
            (
                str(wid),
                separator_state(
                    bundle, process, wid=str(wid), at_s=at_s, state=st,
                    normalize_satellite_budget=True,
                ),
            )
            for wid, st in states.items()
        )
    )
    return projected, _resource_coordinate(states, query_budget), _future_structure(bundle, at_s)


def _phase_structure(bundle, at_s: int) -> tuple[Any, ...]:
    obligations = tuple(
        (
            str(o["obligation_id"]),
            "FUTURE" if at_s < int(o["release_s"]) else "ACTIVE",
            int(o["release_s"]),
            int(o["deadline_s"]),
        )
        for o in bundle["obligations"]
        if int(o["deadline_s"]) >= at_s
    )
    terrestrial = tuple(
        (
            str(w["world_id"]),
            tuple(
                (
                    str(x["window_id"]),
                    "FUTURE" if at_s < int(x["start_s"]) else "OPEN",
                    int(x["start_s"]),
                    int(x["end_s"]),
                    int(x["capacity_units"]),
                )
                for x in w["terrestrial_windows"]
                if int(x["end_s"]) > at_s
            ),
        )
        for w in bundle["worlds"]
    )
    satellite = tuple(
        (
            str(x["window_id"]),
            "FUTURE" if at_s < int(x["start_s"]) else "OPEN",
            int(x["start_s"]),
            int(x["end_s"]),
            int(x["capacity_units"]),
        )
        for x in bundle["public_environment"]["satellite_windows"]
        if int(x["end_s"]) > at_s
    )
    return obligations, terrestrial, satellite


def _phase_event_frontier_key(bundle, process, at_s: int, states, query_budget: int) -> tuple[Any, ...]:
    projected = tuple(
        sorted(
            (
                str(wid),
                separator_state(
                    bundle, process, wid=str(wid), at_s=at_s, state=st,
                    normalize_satellite_budget=True,
                ),
            )
            for wid, st in states.items()
        )
    )
    return projected, _resource_coordinate(states, query_budget), _phase_structure(bundle, at_s)


def _case_trace(bundle, reference_row: dict[str, Any], max_expansions: int) -> list[dict[str, Any]]:
    q, b = map(int, reference_row["minimal_resource_point"])
    start = min(_attempt_lattice(bundle))
    initial = _initial(bundle, b)
    solved = ContinuationPlanner(bundle, mode="exact_memo").solve(
        start, deepcopy(initial), query_budget=q, max_expansions=max_expansions,
    )
    if solved["solvable"] is not True:
        raise RuntimeError(f"frozen reference case no longer exact-solvable: {bundle['recipe_id']}")
    process = attach_causal_evidence(bundle)
    states = initial
    at_s = start
    node = solved["policy"]
    rows = []
    boundary_index = 0
    qleft = q

    while node and not node.get("terminal"):
        branches = _normalize_one(bundle, process, at_s, states)
        if len(branches) != 1 or next(iter(branches)) != "same" or node.get("event") == "OBSERVATION":
            break
        states = next(iter(branches.values()))
        if boundary_index >= len(reference_row["boundaries"]):
            raise RuntimeError("exact trace has more decision boundaries than frozen reference")
        ref = reference_row["boundaries"][boundary_index]
        if int(ref["time_s"]) != int(at_s):
            raise RuntimeError(
                f"boundary alignment drift at {bundle['recipe_id']} index={boundary_index}: "
                f"trace={at_s} reference={ref['time_s']}"
            )
        conservative = (
            dependency_separator_key(bundle, process, at_s, states),
            _resource_coordinate(states, qleft),
        )
        candidate = _event_frontier_key(bundle, process, at_s, states, qleft)
        phase_candidate = _phase_event_frontier_key(bundle, process, at_s, states, qleft)
        rows.append({
            "boundary_index": boundary_index,
            "time_s": at_s,
            "truth": _truth(ref),
            "conservative_key": conservative,
            "candidate_key": candidate,
            "phase_candidate_key": phase_candidate,
            "exact_action": node.get("action"),
            "exact_arg": node.get("arg"),
        })
        if node["action"] == "ISSUE_QUERY":
            break
        stepped = _step(bundle, process, states, at_s, (node["action"], node["arg"]))
        if stepped is None:
            break
        states, at_s = stepped
        node = node["subpolicy"]
        boundary_index += 1

    if len(rows) != len(reference_row["boundaries"]):
        raise RuntimeError(
            f"boundary count drift for {bundle['recipe_id']}: trace={len(rows)} "
            f"reference={len(reference_row['boundaries'])}"
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    ap.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-expansions", type=int, default=200_000)
    args = ap.parse_args()

    inputs = json.loads(args.inputs.read_text(encoding="utf-8"))
    reference = json.loads(args.reference.read_text(encoding="utf-8"))
    input_by_sig = {str(r["signature"]): r for r in inputs["rows"]}
    all_rows = []
    stable_runs = []
    transition_counts = Counter()
    action_counts = Counter()
    candidate_groups = defaultdict(list)
    phase_candidate_groups = defaultdict(list)

    for refrow in reference["rows"]:
        sig = str(refrow["signature"])
        source = input_by_sig[sig]
        trace = _case_trace(source["bundle"], refrow, args.max_expansions)
        run_start = 0
        for i in range(1, len(trace) + 1):
            if i < len(trace) and trace[i]["truth"] == trace[run_start]["truth"]:
                continue
            first = trace[run_start]
            last = trace[i - 1]
            stable_runs.append({
                "signature": sig,
                "start_boundary_index": first["boundary_index"],
                "end_boundary_index": last["boundary_index"],
                "boundary_count": i - run_start,
                "start_time_s": first["time_s"],
                "end_time_s": last["time_s"],
                "duration_s": int(last["time_s"]) - int(first["time_s"]),
            })
            run_start = i
        for row in trace:
            candidate_groups[row["candidate_key"]].append((sig, row["boundary_index"], row["truth"]))
            phase_candidate_groups[row["phase_candidate_key"]].append(
                (sig, row["boundary_index"], row["truth"])
            )
        for left, right in zip(trace, trace[1:]):
            truth_changed = left["truth"] != right["truth"]
            conservative_changed = left["conservative_key"] != right["conservative_key"]
            candidate_changed = left["candidate_key"] != right["candidate_key"]
            phase_candidate_changed = (
                left["phase_candidate_key"] != right["phase_candidate_key"]
            )
            transition_counts[(
                conservative_changed,
                candidate_changed,
                phase_candidate_changed,
                truth_changed,
            )] += 1
            action_counts[(str(left["exact_action"]), truth_changed)] += 1
            all_rows.append({
                "signature": sig,
                "from_boundary_index": left["boundary_index"],
                "to_boundary_index": right["boundary_index"],
                "from_time_s": left["time_s"],
                "to_time_s": right["time_s"],
                "action": left["exact_action"],
                "conservative_key_changed": conservative_changed,
                "candidate_key_changed": candidate_changed,
                "phase_candidate_key_changed": phase_candidate_changed,
                "truth_changed": truth_changed,
            })

    candidate_collision_count = 0
    candidate_unsound_collision_count = 0
    candidate_safe_collision_count = 0
    unsound_examples = []
    for key, members in candidate_groups.items():
        if len(members) < 2:
            continue
        candidate_collision_count += 1
        truths = {m[2] for m in members}
        if len(truths) > 1:
            candidate_unsound_collision_count += 1
            if len(unsound_examples) < 20:
                unsound_examples.append({
                    "members": [
                        {"signature": s, "boundary_index": i, "truth": list(t)}
                        for s, i, t in members[:8]
                    ],
                    "distinct_truth_count": len(truths),
                })
        else:
            candidate_safe_collision_count += 1

    phase_candidate_collision_count = 0
    phase_candidate_unsound_collision_count = 0
    phase_candidate_safe_collision_count = 0
    phase_unsound_examples = []
    for key, members in phase_candidate_groups.items():
        if len(members) < 2:
            continue
        phase_candidate_collision_count += 1
        truths = {m[2] for m in members}
        if len(truths) > 1:
            phase_candidate_unsound_collision_count += 1
            if len(phase_unsound_examples) < 20:
                phase_unsound_examples.append({
                    "members": [
                        {"signature": s, "boundary_index": i, "truth": list(t)}
                        for s, i, t in members[:8]
                    ],
                    "distinct_truth_count": len(truths),
                })
        else:
            phase_candidate_safe_collision_count += 1

    conservative_invalidations = sum(
        1 for r in all_rows if r["conservative_key_changed"] and not r["truth_changed"]
    )
    candidate_invalidations = sum(
        1 for r in all_rows if r["candidate_key_changed"] and not r["truth_changed"]
    )
    phase_candidate_invalidations = sum(
        1
        for r in all_rows
        if r["phase_candidate_key_changed"] and not r["truth_changed"]
    )
    truth_changes = sum(1 for r in all_rows if r["truth_changed"])
    run_lengths = [int(r["boundary_count"]) for r in stable_runs]
    run_durations = [int(r["duration_s"]) for r in stable_runs]
    artifact = {
        "schema_version": "0.1",
        "status": "FUTURE_CHOICE_CONTEXT_VALIDITY_DIAGNOSTIC",
        "inputs_ref": str(args.inputs.relative_to(ROOT)),
        "inputs_sha256": sha256(args.inputs.read_bytes()).hexdigest(),
        "reference_ref": str(args.reference.relative_to(ROOT)),
        "reference_sha256": sha256(args.reference.read_bytes()).hexdigest(),
        "signature_count": len(reference["rows"]),
        "transition_count": len(all_rows),
        "truth_change_count": truth_changes,
        "oracle_truth_stability": {
            "run_count": len(stable_runs),
            "multi_boundary_run_count": sum(x > 1 for x in run_lengths),
            "max_boundary_count": max(run_lengths, default=0),
            "mean_boundary_count": (sum(run_lengths) / len(run_lengths)) if run_lengths else None,
            "max_duration_s": max(run_durations, default=0),
            "mean_duration_s": (sum(run_durations) / len(run_durations)) if run_durations else None,
            "runs": stable_runs,
        },
        "conservative_invalidation_without_truth_change_count": conservative_invalidations,
        "candidate_invalidation_without_truth_change_count": candidate_invalidations,
        "phase_candidate_invalidation_without_truth_change_count": phase_candidate_invalidations,
        "transition_class_count": {
            f"conservative={c}|candidate={k}|phase_candidate={p}|truth={t}": n
            for (c, k, p, t), n in sorted(transition_counts.items())
        },
        "by_exact_action_and_truth_change": {
            f"{a}|truth_change={t}": n for (a, t), n in sorted(action_counts.items())
        },
        "event_frontier_candidate": {
            "collision_group_count": candidate_collision_count,
            "safe_collision_group_count": candidate_safe_collision_count,
            "unsound_collision_group_count": candidate_unsound_collision_count,
            "sound_on_observed_collisions": candidate_unsound_collision_count == 0,
            "unsound_examples": unsound_examples,
        },
        "phase_event_frontier_candidate": {
            "collision_group_count": phase_candidate_collision_count,
            "safe_collision_group_count": phase_candidate_safe_collision_count,
            "unsound_collision_group_count": phase_candidate_unsound_collision_count,
            "sound_on_observed_collisions": phase_candidate_unsound_collision_count == 0,
            "unsound_examples": phase_unsound_examples,
        },
        "transitions": all_rows,
        "claim_boundary": [
            "The current dependency separator remains the conservative reference; this audit does not promote a replacement key.",
            "The event-frontier candidate intentionally removes absolute time while retaining future obligation/window membership and resource/evidence state, and must be rejected if any equal-key collision has different exact future-choice truth.",
            "The phase-aware candidate additionally retains FUTURE/ACTIVE obligation phase and FUTURE/OPEN communication-window phase; it remains a diagnostic candidate until proved from transition semantics.",
            "Invalidation without truth change measures conservatism, not an error; truth change under an equal candidate key is a soundness failure.",
            "This audit uses development hard signatures and exact-policy prefixes only.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps({
        "signature_count": artifact["signature_count"],
        "transition_count": artifact["transition_count"],
        "truth_change_count": truth_changes,
        "conservative_invalidation_without_truth_change_count": conservative_invalidations,
        "candidate_invalidation_without_truth_change_count": candidate_invalidations,
        "phase_candidate_invalidation_without_truth_change_count": phase_candidate_invalidations,
        "event_frontier_candidate": artifact["event_frontier_candidate"],
        "phase_event_frontier_candidate": artifact["phase_event_frontier_candidate"],
        "out": str(args.out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
