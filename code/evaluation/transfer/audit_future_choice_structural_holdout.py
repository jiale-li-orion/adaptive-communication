#!/usr/bin/env python3
"""Execute the preregistered B6 structural-topology holdout.

The motif identities, group sizes, event sequences and correctness gates are
frozen in ``research/workstreams/B6-STRUCTURAL-HOLDOUT-FREEZE-2026-10-09.json``.
This runner only materializes those motifs using the existing Layer-2 v2
obligation/window semantics and evaluates incremental/fresh/exact parity.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
TRANSFER = ROOT / "code/evaluation/transfer"
BENCH = ROOT / "code/evaluation/benchmark"
AGENTIC = ROOT / "code/evaluation/agentic"
for _p in (TRANSFER, BENCH, AGENTIC):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from exact_reference_oracle_v0_1 import LocalState, PendingDelivery  # noqa: E402
from layer2_v2_conflict_frontier import (  # noqa: E402
    IncrementalConflictFrontier,
    canonical_snapshot,
)
from layer2_v2_dependency_cache_baseline import PersistentDependencyExact  # noqa: E402
from layer2_v2_incremental_exact_baseline import PersistentOrderedExact  # noqa: E402


FREEZE = ROOT / "research/workstreams/B6-STRUCTURAL-HOLDOUT-FREEZE-2026-10-09.json"
OUT = ROOT / "results/transfer/future-choice-structural-holdout.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _window(wid: str, start: int, end: int, capacity: int) -> dict[str, Any]:
    return {
        "window_id": wid,
        "start_s": int(start),
        "end_s": int(end),
        "capacity_units": int(capacity),
    }


def _group_obligations(
    group: int,
    size: int,
    *,
    release: int,
    deadline: int,
) -> list[dict[str, Any]]:
    return [
        {
            "obligation_id": f"g{group}:o{j}",
            "release_s": int(release),
            "deadline_s": int(deadline),
        }
        for j in range(size)
    ]


def _bundle(
    motif: str,
    group_sizes: list[int],
    *,
    group_release_deadline: list[tuple[int, int]],
    terr_windows: list[dict[str, Any]],
    horizon: int = 500,
) -> dict[str, Any]:
    obligations: list[dict[str, Any]] = []
    satellite_windows: list[dict[str, Any]] = []
    for g, (size, (release, deadline)) in enumerate(
        zip(group_sizes, group_release_deadline)
    ):
        obligations.extend(
            _group_obligations(g, size, release=release, deadline=deadline)
        )
        # Keep fallback temporally bounded, as in the existing component
        # audits.  A globally always-open fallback window creates a factorial
        # number of scientifically equivalent exact SEND_SAT orderings and is
        # not part of the frozen terrestrial topology motif.  All windows still
        # consume the same shared satellite_budget in LocalState.
        satellite_windows.append(
            _window(
                f"sat-g{g}",
                max(release, deadline - 12),
                deadline - 4,
                size,
            )
        )
    return {
        "schema_version": "0.1",
        "bundle_id": f"b6-{motif.lower()}",
        "recipe_id": "B6_STRUCTURAL_HOLDOUT_FROZEN_2026_10_09",
        "stage": "WORLD_BUNDLE_PRE_EVIDENCE_PRE_ORACLE",
        "obligations": obligations,
        "public_environment": {
            "horizon_s": int(horizon),
            "satellite_windows": satellite_windows,
        },
        "observation_projection": {
            "evidence_regime": "POST_QUERY_REVEALED_BRANCH",
            "evidence_surfaces": [],
        },
        "worlds": [
            {
                "world_id": "revealed-branch",
                "terrestrial_windows": terr_windows,
                "latent_state": {},
            }
        ],
    }


def _add_usage(state: LocalState, wid: str, used: int) -> LocalState:
    rows = dict(state.terrestrial_used)
    rows[str(wid)] = int(used)
    return replace(state, terrestrial_used=tuple(sorted(rows.items())))


def _pending(
    oid: str, *, receipt: int, ack: int, seen: bool = False
) -> PendingDelivery:
    return PendingDelivery(
        obligation_id=oid,
        accepted=True,
        gateway_receipt_at_s=receipt,
        final_ack_at_s=ack,
        negative_observation_at_s=None,
        gateway_receipt_seen=seen,
    )


def materialize_h1() -> tuple[dict, list[tuple[str, int, LocalState]], list[list[str]]]:
    sizes = [2, 3, 5, 4]
    bundle = _bundle(
        "H1_ASYMMETRIC_DISJOINT",
        sizes,
        group_release_deadline=[(120, 165), (90, 145), (140, 185), (160, 205)],
        terr_windows=[
            _window("local-g1", 100, 110, 2),
            _window("local-g0", 120, 132, 1),
            _window("local-g2", 140, 150, 4),
            _window("local-g3", 160, 170, 3),
        ],
    )
    state = LocalState(satellite_budget=5)
    rows = [("initial", 90, state)]
    p = _pending("g1:o0", receipt=110, ack=130)
    state = replace(_add_usage(state, "local-g1", 1), pending_deliveries=(p,))
    rows.append(("send_pending_g1", 100, state))
    state = replace(state, pending_deliveries=(replace(p, gateway_receipt_seen=True),))
    rows.append(("gateway_receipt_g1", 110, state))
    state = replace(state, delivered=("g1:o0",), pending_deliveries=())
    rows.append(("final_ack_g1", 130, state))
    rows.append(("time_boundary_g0", 132, state))
    state = replace(state, satellite_budget=4)
    rows.append(("global_satellite_budget_decrement", 133, state))
    return bundle, rows, [["g0"], ["g1"], ["g2"], ["g3"]]


def materialize_h2() -> tuple[dict, list[tuple[str, int, LocalState]], list[list[str]]]:
    sizes = [3, 4, 3, 2]
    bundle = _bundle(
        "H2_BRIDGED_PAIR",
        sizes,
        group_release_deadline=[(90, 155), (120, 175), (160, 205), (180, 230)],
        terr_windows=[
            _window("local-g0", 100, 110, 2),
            _window("bridge-01", 120, 130, 1),
            _window("local-g1", 140, 150, 3),
            _window("local-g2", 160, 170, 2),
            _window("local-g3", 180, 190, 1),
        ],
    )
    state = LocalState(satellite_budget=4)
    rows = [("initial", 90, state)]
    p = _pending("g0:o0", receipt=110, ack=130)
    state = replace(_add_usage(state, "local-g0", 1), pending_deliveries=(p,))
    rows.append(("pending_g0", 100, state))
    state = _add_usage(state, "local-g0", 2)
    rows.append(("consume_local_g0", 105, state))
    state = _add_usage(state, "bridge-01", 1)
    rows.append(("consume_bridge_01", 120, state))
    state = replace(state, satellite_budget=3)
    rows.append(("global_satellite_budget_decrement", 121, state))
    return bundle, rows, [["g0", "g1"], ["g2"], ["g3"]]


def materialize_h3() -> tuple[dict, list[tuple[str, int, LocalState]], list[list[str]]]:
    sizes = [2, 3, 2, 3]
    bundle = _bundle(
        "H3_CHAIN_OVERLAP_SPLIT",
        sizes,
        group_release_deadline=[(70, 145), (100, 165), (120, 185), (160, 220)],
        terr_windows=[
            _window("local-g0", 80, 90, 1),
            _window("bridge-01", 100, 110, 1),
            _window("bridge-12", 120, 130, 1),
            _window("local-g2", 140, 150, 1),
            _window("local-g3", 160, 170, 2),
        ],
    )
    state = LocalState(satellite_budget=6)
    rows = [("initial", 75, state)]
    state = _add_usage(state, "bridge-01", 1)
    rows.append(("exhaust_bridge_01", 100, state))
    rows.append(("cross_bridge_12_boundary", 130, state))
    p = _pending("g2:o0", receipt=150, ack=170)
    state = replace(_add_usage(state, "local-g2", 1), pending_deliveries=(p,))
    rows.append(("pending_remaining_chain", 140, state))
    state = replace(state, satellite_budget=5)
    rows.append(("global_satellite_budget_decrement", 141, state))
    return bundle, rows, [["g0", "g1", "g2"], ["g3"]]


def materialize_h4() -> tuple[dict, list[tuple[str, int, LocalState]], list[list[str]]]:
    sizes = [2, 4, 3, 5, 2]
    bundle = _bundle(
        "H4_MIXED_LOCAL_GLOBAL",
        sizes,
        group_release_deadline=[(132, 174), (90, 139), (145, 189), (110, 160), (160, 220)],
        terr_windows=[
            _window("local-g1", 100, 105, 3),
            _window("local-g3", 110, 115, 4),
            _window("local-g0", 132, 137, 1),
            _window("local-g2", 145, 150, 2),
            _window("local-g4", 160, 165, 1),
        ],
    )
    state = LocalState(satellite_budget=7)
    rows = [("initial", 90, state)]
    p = _pending("g1:o0", receipt=110, ack=130)
    state = replace(_add_usage(state, "local-g1", 1), pending_deliveries=(p,))
    rows.append(("send_pending_g1", 100, state))
    state = _add_usage(state, "local-g3", 1)
    rows.append(("consume_local_g3", 110, state))
    state = replace(state, delivered=("g1:o0",), pending_deliveries=())
    rows.append(("final_ack_g1", 130, state))
    state = replace(state, satellite_budget=6)
    rows.append(("global_satellite_budget_decrement", 131, state))
    rows.append(("time_boundary_g0", 137, state))
    return bundle, rows, [["g0"], ["g1"], ["g2"], ["g3"], ["g4"]]


MATERIALIZERS = {
    "H1_ASYMMETRIC_DISJOINT": materialize_h1,
    "H2_BRIDGED_PAIR": materialize_h2,
    "H3_CHAIN_OVERLAP_SPLIT": materialize_h3,
    "H4_MIXED_LOCAL_GLOBAL": materialize_h4,
}


def _group(oid: str) -> str:
    return str(oid).split(":", 1)[0]


def _topology(snapshot) -> list[list[str]]:
    worlds = snapshot.world_certificates
    if len(worlds) != 1:
        raise AssertionError("B6 expects one revealed world")
    return sorted(
        [sorted({_group(oid) for oid in comp.obligations}) for comp in worlds[0].components]
    )


def _topology_detail(snapshot) -> list[dict[str, Any]]:
    world = snapshot.world_certificates[0]
    return [
        {
            "groups": sorted({_group(oid) for oid in comp.obligations}),
            "obligation_count": len(comp.obligations),
            "terrestrial_window_ids": sorted({slot[1] for slot in comp.terrestrial_slots}),
            "hall_deficit": int(comp.hall_deficit),
            "valid_until_s": comp.valid_until_s,
        }
        for comp in world.components
    ]


def _exact_row(planner, at_s: int, state: LocalState) -> dict[str, Any]:
    result = planner.build_frontier(
        at_s=at_s,
        states={"revealed-branch": state},
        query_budget=0,
    )
    return {
        "actions": result["actions"],
        "expanded": int(result["metrics"]["expanded"]),
        "recursive_calls": int(result["metrics"]["recursive_calls"]),
        "memo_hits": int(result["metrics"]["memo_hits"]),
        "separator_replay_success": int(result["metrics"].get("separator_replay_success", 0)),
    }


def run_motif(motif: str, *, structural_only: bool) -> dict[str, Any]:
    bundle, events, expected_initial = MATERIALIZERS[motif]()
    runtime = IncrementalConflictFrontier(bundle)
    persistent = None if structural_only else PersistentOrderedExact(bundle)
    dependency = None if structural_only else PersistentDependencyExact(bundle)
    rows = []

    for index, (label, at_s, state) in enumerate(events):
        states = {"revealed-branch": state}
        snapshot, delta = runtime.update(at_s=at_s, states=states)
        fresh_snapshot = runtime.full_rebuild(at_s=at_s, states=states)
        structural_match = canonical_snapshot(snapshot) == canonical_snapshot(fresh_snapshot)
        if not structural_match:
            raise AssertionError((motif, label, "incremental/fresh structural mismatch"))

        topology = _topology(snapshot)
        if index == 0 and topology != sorted(expected_initial):
            raise AssertionError(
                {"motif": motif, "expected_initial": sorted(expected_initial), "actual": topology}
            )

        fresh_exact = ordinary_exact = dependency_exact = None
        if not structural_only:
            assert persistent is not None and dependency is not None
            fresh_exact = _exact_row(PersistentOrderedExact(bundle), at_s, state)
            ordinary_exact = _exact_row(persistent, at_s, state)
            dependency_exact = _exact_row(dependency, at_s, state)
            if not (
                fresh_exact["actions"]
                == ordinary_exact["actions"]
                == dependency_exact["actions"]
            ):
                raise AssertionError(
                    {
                        "motif": motif,
                        "event": label,
                        "fresh": fresh_exact["actions"],
                        "persistent": ordinary_exact["actions"],
                        "dependency": dependency_exact["actions"],
                    }
                )

        rows.append(
            {
                "event": label,
                "at_s": at_s,
                "topology": topology,
                "topology_detail": _topology_detail(snapshot),
                "structural_match_fresh": structural_match,
                "component_count": snapshot.component_count,
                "backup_lower_bound": snapshot.worst_case_backup_lower_bound,
                "optimistic_feasible": snapshot.optimistic_feasible_all_worlds,
                "incremental": {
                    "recomputed": int(delta["component_recomputes"]),
                    "reused": int(delta["component_reuses"]),
                    "partition_fallbacks": int(delta["partition_fallbacks"]),
                    "invalidated_keys": [list(x) for x in delta["invalidated_component_keys"]],
                    "recomputed_keys": [list(x) for x in delta["recomputed_component_keys"]],
                    "reused_keys": [list(x) for x in delta["reused_component_keys"]],
                },
                "fresh_exact": fresh_exact,
                "persistent_exact": ordinary_exact,
                "dependency_exact": dependency_exact,
            }
        )

    return {
        "motif": motif,
        "bundle_id": bundle["bundle_id"],
        "expected_initial_topology": sorted(expected_initial),
        "events": rows,
        "checks": {
            "all_structural_snapshots_match_fresh": all(r["structural_match_fresh"] for r in rows),
            "all_exact_frontiers_match": (
                None
                if structural_only
                else all(
                    r["fresh_exact"]["actions"]
                    == r["persistent_exact"]["actions"]
                    == r["dependency_exact"]["actions"]
                    for r in rows
                )
            ),
            "initial_topology_matches_freeze": rows[0]["topology"] == sorted(expected_initial),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--motifs",
        default=",".join(MATERIALIZERS),
        help="Comma-separated frozen motif IDs",
    )
    ap.add_argument(
        "--structural-only",
        action="store_true",
        help="Skip exact strong-control solvers; used for resource-safe B6 topology/certificate audit.",
    )
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    freeze = _load(FREEZE)
    frozen_ids = [row["id"] for row in freeze["motifs"]]
    requested = [x.strip() for x in args.motifs.split(",") if x.strip()]
    if any(x not in frozen_ids for x in requested):
        raise SystemExit(f"requested motif outside frozen holdout: {requested}")

    motifs = [run_motif(motif, structural_only=bool(args.structural_only)) for motif in requested]
    checks = {
        "freeze_status_correct": freeze["status"] == "FROZEN_BEFORE_EXECUTION",
        "all_structural_snapshots_match_fresh": all(
            row["checks"]["all_structural_snapshots_match_fresh"] for row in motifs
        ),
        "all_exact_frontiers_match": (
            None
            if args.structural_only
            else all(row["checks"]["all_exact_frontiers_match"] for row in motifs)
        ),
        "all_initial_topologies_match_freeze": all(
            row["checks"]["initial_topology_matches_freeze"] for row in motifs
        ),
    }
    required_checks = [
        checks["freeze_status_correct"],
        checks["all_structural_snapshots_match_fresh"],
        checks["all_initial_topologies_match_freeze"],
    ]
    if not args.structural_only:
        required_checks.append(checks["all_exact_frontiers_match"])
    if not all(required_checks):
        raise AssertionError(checks)

    payload = {
        "stage": "FUTURE_CHOICE_B6_STRUCTURAL_HOLDOUT",
        "freeze_sha256": _sha(FREEZE),
        "structural_only": bool(args.structural_only),
        "motifs": motifs,
        "checks": checks,
        "claim_boundary": [
            "The holdout changes graph topology rather than merely increasing branch/component count.",
            "Partition fallback is a conservative correctness mechanism, not an efficiency failure by itself.",
            "Exact expansions and component recomputation counts remain different work units.",
            "Any resource-limited exact comparison must be reported unresolved rather than infeasible."
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"out": str(args.out), "motifs": requested, **checks}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
