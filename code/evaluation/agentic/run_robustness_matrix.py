#!/usr/bin/env python3
"""Run the first axis-wise Agentic Communication robustness gate."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = CODE.parent
for p in (
    CODE,
    CODE / "substrate" / "joint",
    CODE / "substrate" / "instance",
    CODE / "substrate" / "monitoring",
    CODE / "substrate" / "physics",
    CODE / "substrate" / "runtime",
    CODE / "evaluation" / "agentic",
    CODE / "legacy-communication" / "analysis",
):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from agentic_communication.metrics import physical_signature  # noqa: E402
from agentic_communication.planner import EvidenceAwareComplyPlannerConsumer  # noqa: E402
from agentic_communication.replay import audit_trace  # noqa: E402
from agentic_communication.robustness import robustness_coordinates, task_for_coordinate  # noqa: E402
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402


DEFAULT_OUT = ROOT / "results" / "agentic" / "robustness-matrix-v1"


def _dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def _source_manifest() -> dict:
    paths = [
        ROOT / "research" / "benchmark" / "CONFORMANCE-ROBUSTNESS-MATRIX.v1.json",
        ROOT / "research" / "compiler" / "COMMUNICATION-DOMAIN-REGISTRY.v0.1.json",
        ROOT / "research" / "policy" / "BASELINE-REGISTRY.v1.json",
        ROOT / "spec" / "substrate" / "instance-v1-manifest.md",
        ROOT / "data" / "downloads" / "nasa_power_irradiance" / "power_hourly_2023_30.33N_94.78E.csv",
        ROOT / "data" / "dem" / "hgt" / "N29E094.hgt",
        ROOT / "data" / "dem" / "hgt" / "N29E095.hgt",
        ROOT / "data" / "dem" / "hgt" / "N30E094.hgt",
        ROOT / "data" / "dem" / "hgt" / "N30E095.hgt",
    ]
    rows = []
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        rows.append(
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": _sha(path),
            }
        )
    return {
        "schema_revision": "1",
        "artifacts": rows,
        "boundary": (
            "robustness coordinates are benchmark-design inputs; only listed source files and "
            "existing simulator semantics may support physical/data claims"
        ),
    }


def _owners(policy) -> list[str]:
    owners = set()
    for event in policy.trace.events:
        if event.event_type != "evidence_world_revision":
            continue
        for row in event.payload.get("evidence", []):
            owner = row.get("owner_location")
            if owner:
                owners.add(str(owner))
    return sorted(owners)


def _axis_activation(rows: list[dict]) -> dict:
    by_axis: dict[str, list[dict]] = {}
    for row in rows:
        by_axis.setdefault(row["axis"], []).append(row)

    def pair(axis: str) -> tuple[dict, dict]:
        xs = by_axis[axis]
        if len(xs) != 2:
            raise RuntimeError(f"axis {axis} expected 2 rows, got {len(xs)}")
        return xs[0], xs[1]

    a, b = pair("weather_window")
    weather = a["communication_metrics"]["total_harvested_wh"] != b["communication_metrics"]["total_harvested_wh"]

    a, b = pair("backhaul_outage")
    outage_keys = ("backup_bytes", "missing_delivery", "delivery_latency_p90_s", "gateway_forwarded")
    outage = any(a["communication_metrics"].get(k) != b["communication_metrics"].get(k) for k in outage_keys)

    a, b = pair("target_scope")
    scope = a["communication_metrics"]["routine_obligations"] != b["communication_metrics"]["routine_obligations"]

    a, b = pair("evidence_owner")
    owner = a["observed_owner_classes"] != b["observed_owner_classes"]

    a, b = pair("deployment_scale")
    scale = a["node_count"] != b["node_count"]

    return {
        "weather_window": weather,
        "backhaul_outage": outage,
        "target_scope": scope,
        "evidence_owner": owner,
        "deployment_scale": scale,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--coordinates", default=None, help="comma-separated coordinate ids")
    args = ap.parse_args()
    requested = None if not args.coordinates else {x.strip() for x in args.coordinates.split(",") if x.strip()}
    coords = [c for c in robustness_coordinates() if requested is None or c.coordinate_id in requested]
    if requested is not None and {c.coordinate_id for c in coords} != requested:
        missing = sorted(requested - {c.coordinate_id for c in coords})
        raise SystemExit("unknown robustness coordinates: " + ",".join(missing))
    if not coords:
        raise SystemExit("no robustness coordinates selected")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    contract = {
        "experiment_id": "agentic-robustness-matrix-v1",
        "coordinates": [c.model_dump(mode="json") for c in coords],
        "planner_consumer": "EvidenceAwareComplyPlannerConsumer",
        "context_mode": "task_conditioned",
        "claim_ceiling": (
            "Infrastructure/benchmark robustness gate only. It validates that weather/outage/scope/owner/scale "
            "coordinates reach the real simulator/runtime while preserving paired reference physics; it does not "
            "establish a method gain on any robustness axis."
        ),
    }
    _dump(out / "experiment_contract.json", contract)
    _dump(out / "source_manifest.json", _source_manifest())

    rows = []
    replay_rows = []
    with (out / "per_episode_results.jsonl").open("w", encoding="utf-8") as fh:
        for c in coords:
            task = task_for_coordinate(c)
            reference, ref_inst, _ = run_reference_comply(
                seed=c.seed,
                operational_task=task,
                simulator_kwargs=dict(c.simulator_overrides),
            )
            result, policy, inst, _ = run_agentic_episode(
                seed=c.seed,
                operational_task=task,
                planner_consumer=EvidenceAwareComplyPlannerConsumer(),
                simulator_kwargs=dict(c.simulator_overrides),
            )
            trace_path = out / "runtime_traces" / f"{c.coordinate_id.replace(':', '-')}.jsonl"
            policy.trace.write_jsonl(trace_path)
            replay = audit_trace(trace_path, context_mode="task_conditioned")
            replay_rows.append({"coordinate_id": c.coordinate_id, **replay})
            owners = _owners(policy)
            expected_owner_met = set(c.expected_owner_classes).issubset(set(owners))
            row = {
                "coordinate_id": c.coordinate_id,
                "axis": c.axis,
                "level": c.level,
                "task_id": task.task_id,
                "seed": c.seed,
                "simulator_overrides": c.simulator_overrides,
                "node_count": len(inst.nodes),
                "reference_node_count": len(ref_inst.nodes),
                "observed_owner_classes": owners,
                "expected_owner_classes": c.expected_owner_classes,
                "expected_owner_met": expected_owner_met,
                "physical_equal_reference": physical_signature(reference) == physical_signature(result),
                "communication_metrics": result["agentic"]["communication_metrics"],
                "agent_metrics": result["agentic"]["agent_metrics"],
                "trace_path": _display_path(trace_path),
                "replay_passed": bool(replay["passed"]),
            }
            rows.append(row)
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    activation = _axis_activation(rows) if requested is None else {}
    aggregate = {
        "n_coordinates": len(rows),
        "all_physical_equal_reference": all(row["physical_equal_reference"] for row in rows),
        "all_replay_exact": all(row["replay_passed"] for row in rows),
        "all_expected_owners_met": all(row["expected_owner_met"] for row in rows),
        "axis_activation": activation,
        "axes": sorted({row["axis"] for row in rows}),
    }
    _dump(out / "aggregate.json", aggregate)
    _dump(out / "replay_audit.json", {"runs": replay_rows})
    _dump(
        out / "run_manifest.json",
        {
            "generated_at": datetime.now(UTC).isoformat(),
            "python": sys.version,
            "cwd": str(ROOT),
            "coordinate_ids": [c.coordinate_id for c in coords],
            "runtime": "code/agentic_communication/",
        },
    )
    full_matrix = requested is None
    passed = (
        aggregate["all_physical_equal_reference"]
        and aggregate["all_replay_exact"]
        and aggregate["all_expected_owners_met"]
        and (not full_matrix or all(activation.values()))
    )
    audit = {
        "status": "PASS" if passed else "FAIL",
        **aggregate,
        "trace_files": len(list((out / "runtime_traces").glob("*.jsonl"))),
        "expected_trace_files": len(coords),
        "result_hashes": {
            str(path.relative_to(out)): _sha(path)
            for path in sorted(out.rglob("*"))
            if path.is_file() and path.name != "audit.json"
        },
        "claim_ceiling": contract["claim_ceiling"],
    }
    _dump(out / "audit.json", audit)
    print(json.dumps({"audit": audit, "rows": rows}, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
