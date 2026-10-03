#!/usr/bin/env python3
"""O2 Risk Escalation: first full-sim Agentic Communication benchmark slice."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import statistics
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

from agentic_communication.episodes import (  # noqa: E402
    o2_localized_risk_escalation_task,
    o2_risk_escalation_task,
)
from agentic_communication.metrics import (  # noqa: E402
    communication_metrics,
    metric_delta,
    physical_signature,
)
from agentic_communication.run import (  # noqa: E402
    DEFAULT_FULLSIM,
    run_agentic_episode,
    run_reference_comply,
)
from agentic_communication.replay import audit_trace  # noqa: E402
from agentic_communication.planner import DeterministicComplyPlannerConsumer  # noqa: E402


ARMS = ("legacy_comply", "task_conditioned", "full_dump")


def _json_dump(path: Path, value) -> None:
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


def _source_manifest(task, simulator: dict) -> dict:
    year = int(simulator["irradiance_year"])
    nasa_csv = (
        ROOT
        / "data"
        / "downloads"
        / "nasa_power_irradiance"
        / f"power_hourly_{year}_30.33N_94.78E.csv"
    )
    loss_model = ROOT / "results" / "communication-substrate" / "calibration" / "link" / "loss_model.json"
    outage_model = ROOT / "results" / "communication-substrate" / "calibration" / "link" / "outage_distribution.json"

    artifacts = []
    for label, path, authority in (
        ("srtm1_n29e094", ROOT / "data" / "dem" / "hgt" / "N29E094.hgt", "terrain/ITM geometry"),
        ("srtm1_n29e095", ROOT / "data" / "dem" / "hgt" / "N29E095.hgt", "terrain/ITM geometry"),
        ("srtm1_n30e094", ROOT / "data" / "dem" / "hgt" / "N30E094.hgt", "terrain/ITM geometry"),
        ("srtm1_n30e095", ROOT / "data" / "dem" / "hgt" / "N30E095.hgt", "terrain/ITM geometry"),
        (f"nasa_power_{year}", nasa_csv, "irradiance/temperature exogenous trace"),
        ("chirpbox_loss_model", loss_model, "derived temporal link model"),
        ("chirpbox_outage_model", outage_model, "derived outage-duration model"),
    ):
        row = {
            "id": label,
            "path": str(path.relative_to(ROOT)),
            "authority": authority,
            "exists": path.is_file(),
        }
        if path.is_file():
            row["bytes"] = path.stat().st_size
            row["sha256"] = _sha(path)
        artifacts.append(row)

    return {
        "task_source_refs": list(task.source_refs),
        "source_inventory": "research/literature/sources.json",
        "dataset_authority": "spec/substrate/datasets.md",
        "instance_authority": "spec/substrate/instance-v1-manifest.md",
        "artifacts": artifacts,
        "chirpbox_raw": {
            "path": "data/downloads/chirpbox.csv",
            "source": "Zenodo 10.5281/zenodo.5527877",
            "note": "raw file is large; experiment manifest freezes the small derived model artifacts used by the simulator",
        },
        "nasa_power_window": {
            "year": year,
            "start_hour": int(simulator["irradiance_start_hour"]),
        },
    }


def _aggregate(rows: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["arm"]].append(row)
    out = {}
    for arm, rs in grouped.items():
        scalars: dict[str, list[float]] = defaultdict(list)
        for r in rs:
            for prefix, metrics in (
                ("communication", r["communication_metrics"]),
                ("agent", r.get("agent_metrics") or {}),
            ):
                for k, v in metrics.items():
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        scalars[f"{prefix}.{k}"].append(float(v))
        out[arm] = {
            "n": len(rs),
            "mean": {k: statistics.fmean(vs) for k, vs in sorted(scalars.items())},
            "median": {k: statistics.median(vs) for k, vs in sorted(scalars.items())},
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="0,1,2,3,4")
    ap.add_argument("--variant", choices=["global", "localized"], default="global")
    ap.add_argument(
        "--out",
        default=None,
    )
    args = ap.parse_args()
    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]
    if args.variant == "localized":
        task = o2_localized_risk_escalation_task()
        experiment_id = "o2-localized-risk-escalation-v1"
    else:
        task = o2_risk_escalation_task()
        experiment_id = "o2-risk-escalation-v1"
    out = Path(args.out) if args.out else ROOT / "results" / "agentic" / experiment_id
    out.mkdir(parents=True, exist_ok=True)

    experiment_contract = {
        "experiment_id": experiment_id,
        "variant": args.variant,
        "status": "exploratory infrastructure + deterministic conformance",
        "design_authority": "research/README.md",
        "system_model": "research/substrate/SYSTEM-MODEL-v1.md",
        "scenario": "spec/substrate/instance-v1-manifest.md",
        "operational_task": task.model_dump(mode="json"),
        "arms": list(ARMS),
        "agent_planner_consumer": "DeterministicComplyPlannerConsumer",
        "seeds": seeds,
        "simulator": {**DEFAULT_FULLSIM},
        "simulator_authority": "code/agentic_communication/run.py::DEFAULT_FULLSIM",
        "primary_metrics": [
            "timely_delivery_rate",
            "collection_rate",
            "delivery_latency_p90_s",
            "total_consumed_wh",
            "backup_bytes",
            "physical_action_confirmation_rate",
            "context_sufficiency_recall",
            "mean_materialized_bytes",
        ],
        "claim_ceiling": (
            "This run validates the unified runtime and measures the O2 deterministic slice. "
            "It is not a claim that task-conditioned context improves physical service, because "
            "the deterministic planner is intentionally behavior-equivalent to legacy comply."
        ),
    }
    _json_dump(out / "experiment_contract.json", experiment_contract)
    _json_dump(out / "source_manifest.json", _source_manifest(task, experiment_contract["simulator"]))
    simulator_kwargs = dict(experiment_contract["simulator"])

    rows: list[dict] = []
    equivalence = []
    replay_audits = []
    with (out / "per_episode_results.jsonl").open("w", encoding="utf-8") as fh:
        for seed in seeds:
            reference, _, _ = run_reference_comply(
                seed=seed,
                operational_task=task,
                simulator_kwargs=simulator_kwargs,
            )
            ref_sig = physical_signature(reference)
            ref_comm = communication_metrics(reference)
            ref_row = {
                "seed": seed,
                "arm": "legacy_comply",
                "communication_metrics": ref_comm,
                "agent_metrics": None,
            }
            rows.append(ref_row)
            fh.write(json.dumps(ref_row, ensure_ascii=False) + "\n")

            for arm in ("task_conditioned", "full_dump"):
                result, policy, _, _ = run_agentic_episode(
                    seed=seed,
                    operational_task=task,
                    context_mode=arm,
                    planner_consumer=DeterministicComplyPlannerConsumer(),
                    simulator_kwargs=simulator_kwargs,
                )
                sig_equal = physical_signature(result) == ref_sig
                equivalence.append({"seed": seed, "arm": arm, "physical_equal": sig_equal})
                trace_path = out / "runtime_traces" / f"seed-{seed:03d}-{arm}.jsonl"
                policy.trace.write_jsonl(trace_path)
                replay = audit_trace(trace_path, context_mode=arm)
                replay_audits.append({"seed": seed, "arm": arm, **replay})
                row = {
                    "seed": seed,
                    "arm": arm,
                    "communication_metrics": result["agentic"]["communication_metrics"],
                    "agent_metrics": result["agentic"]["agent_metrics"],
                    "delta_vs_legacy": metric_delta(
                        result["agentic"]["communication_metrics"], ref_comm
                    ),
                    "physical_equal_legacy": sig_equal,
                    "trace_path": _display_path(trace_path),
                }
                rows.append(row)
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    aggregate = _aggregate(rows)
    _json_dump(out / "aggregate.json", aggregate)
    _json_dump(out / "replay_audit.json", {"runs": replay_audits})
    run_manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "python": sys.version,
        "cwd": str(ROOT),
        "seeds": seeds,
        "arms": list(ARMS),
        "runtime_contract_owner": "code/agentic_communication/runtime_contracts.py",
        "planner_consumer": "code/agentic_communication/planner.py::DeterministicComplyPlannerConsumer",
        "capability_registry": "research/compiler/COMMUNICATION-DOMAIN-REGISTRY.v0.1.json",
        "fullsim": "code/substrate/joint/joint_run.py::run_joint",
        "scorer": "code/substrate/instance/scoring.py::evaluate",
    }
    _json_dump(out / "run_manifest.json", run_manifest)

    all_equal = all(x["physical_equal"] for x in equivalence)
    all_replay = all(x["passed"] for x in replay_audits)
    trace_files = sorted((out / "runtime_traces").glob("*.jsonl"))
    audit = {
        "status": "PASS" if (all_equal and all_replay) else "FAIL",
        "episode_rows": len(rows),
        "expected_episode_rows": len(seeds) * len(ARMS),
        "trace_files": len(trace_files),
        "expected_trace_files": len(seeds) * 2,
        "physical_equivalence_to_legacy_comply": equivalence,
        "all_physical_equivalent": all_equal,
        "all_replay_exact": all_replay,
        "replay_audit": "replay_audit.json",
        "hidden_truth_policy_check": (
            "AgenticCommunicationPolicy receives CenterView only; bind_instance is audit-only and "
            "is never read by plan()."
        ),
        "result_hashes": {
            str(p.relative_to(out)): _sha(p)
            for p in sorted(out.rglob("*"))
            if p.is_file() and p.name != "audit.json"
        },
    }
    _json_dump(out / "audit.json", audit)
    print(json.dumps({"audit": audit["status"], "aggregate": aggregate}, ensure_ascii=False, indent=2))
    return 0 if (all_equal and all_replay) else 1


if __name__ == "__main__":
    raise SystemExit(main())
