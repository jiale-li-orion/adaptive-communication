#!/usr/bin/env python3
"""Run the frozen deterministic Layer-1 paper evaluation protocol.

The runner is deliberately resumable and defensive:

* paper protocol / split digests must match the pre-release manifest;
* the frozen test split requires an explicit ``--execute-frozen-test`` flag;
* simulator/runtime source hashes are frozen in the output directory before the
  first row and must match on resume;
* each coordinate × baseline/oracle result is appended immediately to JSONL;
* no CLI option can override baseline parameters from the frozen protocol.

LLM arms are intentionally excluded.  They have a separate frozen 30-coordinate
protocol and will run only after this deterministic table is complete.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import statistics
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
CODE = ROOT / "code"
for p in (
    CODE,
    CODE / "substrate" / "joint",
    CODE / "substrate" / "instance",
    CODE / "substrate" / "monitoring",
    CODE / "substrate" / "physics",
    CODE / "substrate" / "runtime",
):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from agentic_communication.episodes import benchmark_episode_catalog  # noqa: E402
from agentic_communication.metrics import communication_metrics, configuration_execution_metrics  # noqa: E402
from agentic_communication.planner import DeterministicComplyPlannerConsumer  # noqa: E402
from agentic_communication.run import DEFAULT_FULLSIM, _delivery_oracles, run_agentic_episode  # noqa: E402
from joint_run import run_joint  # noqa: E402
from network import DeviceProfile  # noqa: E402
from oracle import delivery_oracle, dynamic_oracle  # noqa: E402


PROTOCOL = ROOT / "research/benchmark/PAPER-BASELINE-PROTOCOL.json"
SPLIT = ROOT / "results/benchmark/layer1-paper-split.json"
PRE_RELEASE = ROOT / "results/benchmark/layer1-paper-release-candidate.json"

SOURCE_FILES = (
    "code/agentic_communication/episodes.py",
    "code/agentic_communication/metrics.py",
    "code/agentic_communication/planner.py",
    "code/agentic_communication/policy.py",
    "code/agentic_communication/context_runtime.py",
    "code/agentic_communication/run.py",
    "code/substrate/joint/joint_run.py",
    "code/substrate/joint/joint_plane.py",
    "code/substrate/joint/mission_policy.py",
    "code/substrate/instance/center.py",
    "code/substrate/instance/network.py",
    "code/substrate/instance/scoring.py",
    "code/substrate/instance/oracle.py",
    "research/benchmark/PAPER-BASELINE-PROTOCOL.json",
    "results/benchmark/layer1-paper-split.json",
)

DIRECT_BASELINES = {
    "comm.local_policy": {"kind": "joint", "arm": "local"},
    "comm.aoi": {"kind": "joint", "arm": "aoi"},
    "comm.energy_aware": {"kind": "joint", "arm": "energy_aware"},
    "comm.ea_aoi": {"kind": "joint", "arm": "ea_aoi"},
    "comm.mission_comply": {"kind": "joint", "arm": "local", "mission_mode": "comply"},
    "comm.mission_sustain": {"kind": "joint", "arm": "local", "mission_mode": "sustain"},
    "comm.backup_edf": {"kind": "joint", "arm": "local", "backup_chooser": "edf"},
    "comm.backup_maxcov": {"kind": "joint", "arm": "local", "backup_chooser": "maxcov"},
    "agent.deterministic_comply": {"kind": "agent_deterministic"},
}


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_frozen_inputs(protocol: dict, split: dict, pre: dict) -> None:
    file_rows = pre["files"]
    expected_protocol = file_rows["baseline_protocol"]["sha256"]
    expected_split = file_rows["execution_split"]["sha256"]
    if _sha(PROTOCOL) != expected_protocol:
        raise RuntimeError("paper baseline protocol drifted after pre-release freeze")
    if _sha(SPLIT) != expected_split:
        raise RuntimeError("paper execution split drifted after pre-release freeze")
    if protocol["status"] != "FROZEN_BEFORE_TEST_EXECUTION":
        raise RuntimeError("paper protocol is not frozen")
    if split["status"] != "FROZEN_COORDINATES_TEST_NOT_EXECUTED_BY_THIS_SCRIPT":
        raise RuntimeError("unexpected split state")


def _source_manifest() -> dict[str, str]:
    return {rel: _sha(ROOT / rel) for rel in SOURCE_FILES}


def _freeze_or_check_sources(out: Path) -> None:
    path = out / "source-manifest.json"
    current = {
        "git_commit_at_start": _head(),
        "files": _source_manifest(),
    }
    if path.exists():
        old = _load(path)
        if old.get("files") != current["files"]:
            changed = sorted(
                rel
                for rel in set(current["files"]) | set(old.get("files") or {})
                if current["files"].get(rel) != (old.get("files") or {}).get(rel)
            )
            raise RuntimeError("paper deterministic source drift on resume: " + ", ".join(changed))
        return
    out.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _simulator(template, coordinate: dict) -> dict:
    sim = dict(DEFAULT_FULLSIM)
    sim.update(template.simulator_overrides)
    sim.update(coordinate["simulator_overrides"])
    return sim


def _decorate_result(result: dict, inst, obligations, task, sim: dict) -> dict:
    result["configuration_execution"] = configuration_execution_metrics(inst, task)
    result["evaluator_oracles"] = _delivery_oracles(
        inst, obligations, int(sim["task_hours"] + sim["tail_hours"])
    )
    return result


def _run_joint_baseline(seed: int, task, sim: dict, spec: dict):
    kw = dict(sim)
    kw.update(
        trace=True,
        mission_schedule=task.mission_schedule(),
        mission_scope=(task.target_node_ids or None),
    )
    if spec.get("mission_mode") is not None:
        kw["mission_mode"] = spec["mission_mode"]
    if spec.get("backup_chooser") is not None:
        kw["backup_chooser"] = spec["backup_chooser"]
    result, inst, obligations = run_joint(seed=seed, arm=spec["arm"], **kw)
    return _decorate_result(result, inst, obligations, task, sim), inst, obligations


def _run_online(seed: int, task, sim: dict, baseline_id: str):
    spec = DIRECT_BASELINES[baseline_id]
    if spec["kind"] == "joint":
        return _run_joint_baseline(seed, task, sim, spec)
    if spec["kind"] == "agent_deterministic":
        result, _policy, inst, obligations = run_agentic_episode(
            seed=seed,
            operational_task=task,
            context_mode="task_conditioned",
            planner_mode="comply",
            planner_consumer=DeterministicComplyPlannerConsumer(),
            planner_replan_mode="decision_state",
            simulator_kwargs=sim,
        )
        return result, inst, obligations
    raise KeyError(baseline_id)


def _dynamic_energy_reference(inst, obligations, sim: dict) -> dict:
    profile = DeviceProfile(
        sample_interval_s=int(sim["sample_interval_s"]),
        report_period_s=int(sim["report_period_s"]),
        capacity_wh=float(sim["capacity_wh"]),
        initial_soc=float(sim["initial_soc"]),
        obligation_period_s=int(sim["routine_period_s"]),
    )
    row = dynamic_oracle(
        obligations,
        int(sim["task_hours"]),
        inst.truth.harvest_wh,
        inst.nodes.keys(),
        profile=profile,
        initial_wh=float(sim["capacity_wh"]) * float(sim["initial_soc"]),
        tail_hours=int(sim["tail_hours"]),
    )
    return {
        "total_oracle": int(row["total_oracle"]),
        "semantics": "energy/sampling evaluator-only upper bound; delivery relaxed by design",
    }


def _primary_only_delivery(seed: int, task, sim: dict) -> dict:
    kw = dict(sim)
    kw.update(
        trace=True,
        mission_schedule=task.mission_schedule(),
        mission_scope=(task.target_node_ids or None),
        mission_mode="comply",
        enable_backup=False,
        backup_chooser="edf",
    )
    result, inst, obligations = run_joint(seed=seed, arm="local", **kw)
    hours = int(sim["task_hours"] + sim["tail_hours"])
    fixed = delivery_oracle(obligations, inst.log, hours, plane=inst.plane)
    free_sample = delivery_oracle(
        obligations, inst.log, hours, plane=inst.plane, free_transmit=True, require_sample=True
    )
    free = delivery_oracle(
        obligations, inst.log, hours, plane=inst.plane, free_transmit=True
    )
    actual = int(result["routine"]["delivered"])
    order_ok = (
        actual <= int(fixed["total_oracle"])
        <= int(free_sample["total_oracle"])
        <= int(free["total_oracle"])
    )
    if not order_ok:
        raise AssertionError("primary-only delivery oracle order violated")
    return {
        "actual_primary_only_routine_delivered": actual,
        "fixed_send_oracle": int(fixed["total_oracle"]),
        "free_send_require_sample_oracle": int(free_sample["total_oracle"]),
        "link_opportunity_ceiling": int(free["total_oracle"]),
        "upper_bound_order_valid": True,
        "coordinate_override": {"enable_backup": False},
        "ranking_role": "diagnostic_only",
    }


def _failure_reasons(metrics: dict) -> list[str]:
    rows = []
    if int(metrics.get("missing_collection") or 0) > 0:
        rows.append("COLLECTION_MISS")
    if int(metrics.get("missing_delivery") or 0) > 0:
        rows.append("DELIVERY_DEADLINE_MISS")
    if (
        metrics.get("alive_nodes") is not None
        and metrics.get("total_nodes") is not None
        and int(metrics["alive_nodes"]) < int(metrics["total_nodes"])
    ):
        rows.append("ENERGY_EXHAUSTION")
    rate = metrics.get("config_revision_install_completion_rate")
    if rate is not None and float(rate) < 1.0:
        rows.append("TASK_REVISION_NOT_APPLIED")
    return rows


def _compact_online(result: dict, baseline_id: str, coordinate: dict) -> dict:
    metrics = communication_metrics(result)
    return {
        "kind": "online_baseline",
        "row_id": f"{coordinate['coordinate_id']}::{baseline_id}",
        "coordinate_id": coordinate["coordinate_id"],
        "coordinate_sha256": coordinate["coordinate_sha256"],
        "split": coordinate["split"],
        "task_template": coordinate["task_template"],
        "seed": int(coordinate["seed"]),
        "window_id": coordinate["window_id"],
        "baseline_id": baseline_id,
        "communication_metrics": metrics,
        "failure_reasons": _failure_reasons(metrics),
    }


def _read_existing(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    out = {}
    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"invalid JSONL at {path}:{lineno}") from exc
            out[row["row_id"]] = row
    return out


def _append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        fh.flush()


def _baselines_for(protocol: dict, template: str) -> list[str]:
    return list(protocol["full_test"]["universal"]) + list(
        protocol["full_test"]["by_template"].get(template, [])
    )


def _coordinate_rows(split: dict, split_name: str, *, limit_per_template: int | None):
    rows = split["coordinates"][split_name]
    if limit_per_template is None:
        return list(rows)
    kept = []
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        task = row["task_template"]
        if counts[task] >= limit_per_template:
            continue
        counts[task] += 1
        kept.append(row)
    return kept


def _aggregate(rows: list[dict]) -> dict:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        if row["kind"] != "online_baseline":
            continue
        grouped[(row["task_template"], row["baseline_id"])].append(row)

    out = {}
    for (task, baseline), items in sorted(grouped.items()):
        metrics = [row["communication_metrics"] for row in items]
        def vals(key):
            return [float(m[key]) for m in metrics if isinstance(m.get(key), (int, float)) and not isinstance(m.get(key), bool)]
        summary = {"n": len(items)}
        for key in (
            "timely_delivery_rate",
            "collection_rate",
            "missing_collection",
            "missing_delivery",
            "aoi_mean_s",
            "no_observation_s",
            "node_survival_rate",
            "mean_final_soc",
            "total_consumed_wh",
            "backup_packets",
            "backup_records",
            "commands_sent",
            "commands_delivered",
            "config_revision_install_completion_rate",
        ):
            xs = vals(key)
            if xs:
                summary[key] = {
                    "mean": statistics.fmean(xs),
                    "median": statistics.median(xs),
                    "std": statistics.stdev(xs) if len(xs) > 1 else 0.0,
                }
        out[f"{task}/{baseline}"] = summary
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=("dev", "test"), default="dev")
    ap.add_argument("--limit-per-template", type=int)
    ap.add_argument("--execute-frozen-test", action="store_true")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    protocol = _load(PROTOCOL)
    split = _load(SPLIT)
    pre = _load(PRE_RELEASE)
    _assert_frozen_inputs(protocol, split, pre)
    if args.split == "test" and not args.execute_frozen_test:
        raise SystemExit("refusing frozen test execution without --execute-frozen-test")
    if args.split == "test" and args.limit_per_template is not None:
        raise SystemExit("frozen test must run the complete coordinate set; partial test execution is forbidden")

    out = args.out or (ROOT / "results/benchmark" / f"layer1-paper-deterministic-{args.split}")
    _freeze_or_check_sources(out)
    rows_path = out / "rows.jsonl"
    existing = _read_existing(rows_path)
    catalog = benchmark_episode_catalog()
    coordinates = _coordinate_rows(split, args.split, limit_per_template=args.limit_per_template)

    expected_online = 0
    for coordinate in coordinates:
        template = catalog[coordinate["task_template"]]
        task = template.task
        sim = _simulator(template, coordinate)
        baseline_ids = _baselines_for(protocol, coordinate["task_template"])
        expected_online += len(baseline_ids)
        local_inst = None
        local_obligations = None

        for baseline_id in baseline_ids:
            row_id = f"{coordinate['coordinate_id']}::{baseline_id}"
            if row_id in existing:
                continue
            result, inst, obligations = _run_online(
                int(coordinate["seed"]), task, sim, baseline_id
            )
            row = _compact_online(result, baseline_id, coordinate)
            _append(rows_path, row)
            existing[row_id] = row
            if baseline_id == "comm.local_policy":
                local_inst, local_obligations = inst, obligations

        # Recover a local instance when resuming after the online row already
        # exists, because dynamic-energy reference needs realized harvest truth.
        needs_dynamic = coordinate["task_template"] in {"O4", "O6"}
        dynamic_id = f"{coordinate['coordinate_id']}::oracle.dynamic_energy"
        if needs_dynamic and dynamic_id not in existing:
            if local_inst is None:
                _result, local_inst, local_obligations = _run_online(
                    int(coordinate["seed"]), task, sim, "comm.local_policy"
                )
            value = _dynamic_energy_reference(local_inst, local_obligations, sim)
            row = {
                "kind": "evaluator_only_oracle",
                "row_id": dynamic_id,
                "coordinate_id": coordinate["coordinate_id"],
                "task_template": coordinate["task_template"],
                "seed": int(coordinate["seed"]),
                "window_id": coordinate["window_id"],
                "oracle_id": "oracle.dynamic_energy",
                "value": value,
            }
            _append(rows_path, row)
            existing[dynamic_id] = row

        delivery_id = f"{coordinate['coordinate_id']}::oracle.delivery.primary_only_decomposition"
        if delivery_id not in existing:
            row = {
                "kind": "evaluator_only_oracle",
                "row_id": delivery_id,
                "coordinate_id": coordinate["coordinate_id"],
                "task_template": coordinate["task_template"],
                "seed": int(coordinate["seed"]),
                "window_id": coordinate["window_id"],
                "oracle_id": "oracle.delivery.primary_only_decomposition",
                "value": _primary_only_delivery(int(coordinate["seed"]), task, sim),
            }
            _append(rows_path, row)
            existing[delivery_id] = row

        print(
            json.dumps(
                {
                    "coordinate": coordinate["coordinate_id"],
                    "online_baselines": len(baseline_ids),
                    "rows_total": len(existing),
                },
                sort_keys=True,
            ),
            flush=True,
        )

    rows = list(existing.values())
    expected_oracles = len(coordinates) + sum(
        row["task_template"] in {"O4", "O6"} for row in coordinates
    )
    actual_online = sum(row["kind"] == "online_baseline" for row in rows)
    actual_oracles = sum(row["kind"] == "evaluator_only_oracle" for row in rows)
    complete = actual_online == expected_online and actual_oracles == expected_oracles
    aggregate = {
        "stage": "LAYER1_PAPER_DETERMINISTIC_EVALUATION",
        "split": args.split,
        "coordinate_count": len(coordinates),
        "expected_online_rows": expected_online,
        "actual_online_rows": actual_online,
        "expected_oracle_rows": expected_oracles,
        "actual_oracle_rows": actual_oracles,
        "complete": complete,
        "baseline_summary": _aggregate(rows),
    }
    (out / "aggregate.json").write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "generated_at": _now(),
        "runner": str(Path(__file__).relative_to(ROOT)),
        "git_commit": _head(),
        "protocol_sha256": _sha(PROTOCOL),
        "split_sha256": _sha(SPLIT),
        "pre_release_sha256": _sha(PRE_RELEASE),
        "rows_sha256": _sha(rows_path),
        "aggregate_sha256": _sha(out / "aggregate.json"),
        "complete": complete,
    }
    (out / "run-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"out": str(out), **aggregate}, sort_keys=True))
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
