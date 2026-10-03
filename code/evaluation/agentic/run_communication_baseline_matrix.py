#!/usr/bin/env python3
"""Formal pre-API matrix for existing communication controllers and oracles.

This experiment reuses the O2 Operational Task and DEFAULT_FULLSIM.  It changes
one ordinary communication-control dimension at a time:

* center policy: local / AoI / EnergyAware / mission-comply, backup chooser=EDF;
* backup chooser: local+EDF vs local+maxcov;
* evaluator-only references: dynamic energy oracle and a primary-only delivery
  oracle coordinate (backup disabled because the current delivery oracle is
  intentionally primary-path-only).

No model/API is involved.
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
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

from agentic_communication.episodes import o2_risk_escalation_task  # noqa: E402
from agentic_communication.metrics import communication_metrics  # noqa: E402
from agentic_communication.run import DEFAULT_FULLSIM  # noqa: E402
from joint_run import run_joint  # noqa: E402
from network import DeviceProfile  # noqa: E402
from oracle import delivery_oracle, dynamic_oracle  # noqa: E402


OUT = ROOT / "results" / "agentic" / "communication-baseline-matrix-v1"

ONLINE_ARMS = {
    "local_edf": {
        "baseline_id": "comm.local_policy",
        "arm": "local",
        "backup_chooser": "edf",
    },
    "local_maxcov": {
        "baseline_id": "comm.backup_maxcov",
        "arm": "local",
        "backup_chooser": "maxcov",
    },
    "aoi_edf": {
        "baseline_id": "comm.aoi",
        "arm": "aoi",
        "backup_chooser": "edf",
    },
    "energy_aware_edf": {
        "baseline_id": "comm.energy_aware",
        "arm": "energy_aware",
        "backup_chooser": "edf",
    },
    "mission_comply_edf": {
        "baseline_id": "comm.mission_comply",
        "arm": "local",
        "mission_mode": "comply",
        "backup_chooser": "edf",
    },
}


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def mean_rows(rows: list[dict]) -> dict:
    keys = sorted(
        k
        for k, v in rows[0]["communication_metrics"].items()
        if isinstance(v, (int, float)) and not isinstance(v, bool)
    )
    return {
        key: statistics.fmean(float(row["communication_metrics"][key]) for row in rows)
        for key in keys
    }


def _dynamic_energy_oracle(inst, obligations, simulator: dict) -> dict:
    profile = DeviceProfile(
        sample_interval_s=int(simulator["sample_interval_s"]),
        report_period_s=int(simulator["report_period_s"]),
        capacity_wh=float(simulator["capacity_wh"]),
        initial_soc=float(simulator["initial_soc"]),
        obligation_period_s=int(simulator["routine_period_s"]),
    )
    return dynamic_oracle(
        obligations,
        int(simulator["task_hours"]),
        inst.truth.harvest_wh,
        inst.nodes.keys(),
        profile=profile,
        initial_wh=float(simulator["capacity_wh"]) * float(simulator["initial_soc"]),
        tail_hours=int(simulator["tail_hours"]),
    )


def _routine_delivered(result: dict) -> int:
    return int(result["routine"]["delivered"])


def run_online(seed: int, task, simulator: dict, spec: dict):
    kw = dict(simulator)
    kw.update(
        {
            "trace": True,
            "mission_schedule": task.mission_schedule(),
            "mission_scope": (task.target_node_ids or None),
            "backup_chooser": spec["backup_chooser"],
        }
    )
    if spec.get("mission_mode"):
        kw["mission_mode"] = spec["mission_mode"]
    result, inst, obligations = run_joint(seed=seed, arm=spec["arm"], **kw)
    return result, inst, obligations


def primary_only_delivery_reference(seed: int, task, simulator: dict) -> dict:
    kw = dict(simulator)
    kw.update(
        {
            "trace": True,
            "mission_schedule": task.mission_schedule(),
            "mission_scope": (task.target_node_ids or None),
            "mission_mode": "comply",
            "enable_backup": False,
            "backup_chooser": "edf",
        }
    )
    result, inst, obligations = run_joint(seed=seed, arm="local", **kw)
    hours = int(simulator["task_hours"] + simulator["tail_hours"])
    fixed = delivery_oracle(obligations, inst.log, hours, plane=inst.plane)
    free_sample = delivery_oracle(
        obligations,
        inst.log,
        hours,
        plane=inst.plane,
        free_transmit=True,
        require_sample=True,
    )
    free = delivery_oracle(
        obligations,
        inst.log,
        hours,
        plane=inst.plane,
        free_transmit=True,
    )
    actual = _routine_delivered(result)
    return {
        "actual_routine_delivered": actual,
        "delivery_fixed_send": fixed,
        "delivery_free_send_require_sample": free_sample,
        "delivery_link_opportunity_ceiling": free,
        "upper_bound_order_valid": (
            actual <= int(fixed["total_oracle"])
            <= int(free_sample["total_oracle"])
            <= int(free["total_oracle"])
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="0,1,2,3,4")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    task = o2_risk_escalation_task()
    simulator = dict(DEFAULT_FULLSIM)
    contract = {
        "experiment_id": "communication-baseline-matrix-v1",
        "task": task.model_dump(mode="json"),
        "seeds": seeds,
        "simulator": simulator,
        "simulator_authority": "code/agentic_communication/run.py::DEFAULT_FULLSIM",
        "online_arms": ONLINE_ARMS,
        "evaluator_only_oracles": ["oracle.dynamic_energy", "oracle.delivery"],
        "fairness": {
            "center_policy_comparison": "backup chooser fixed to EDF",
            "backup_chooser_comparison": "center policy fixed to LocalPolicy",
            "delivery_oracle_coordinate": (
                "primary-only (gateway backup disabled) because code/substrate/instance/oracle.py::delivery_oracle "
                "is primary-path-only"
            ),
        },
        "claim_ceiling": (
            "Pre-API communication-controller/oracle baseline only. Online controller results may be "
            "compared under the same O2 task and simulator. Evaluator-only oracle values are upper-bound "
            "diagnostics and must not be ranked as online policies."
        ),
    }
    dump(out / "experiment_contract.json", contract)

    online_rows: list[dict] = []
    oracle_rows: list[dict] = []
    with (out / "per_seed_results.jsonl").open("w", encoding="utf-8") as fh:
        for seed in seeds:
            seed_dynamic = None
            for arm_name, spec in ONLINE_ARMS.items():
                result, inst, obligations = run_online(seed, task, simulator, spec)
                if seed_dynamic is None:
                    seed_dynamic = _dynamic_energy_oracle(inst, obligations, simulator)
                row = {
                    "kind": "online_baseline",
                    "seed": seed,
                    "arm": arm_name,
                    "baseline_id": spec["baseline_id"],
                    "communication_metrics": communication_metrics(result),
                    "routine_delivered": _routine_delivered(result),
                    "command_counters": result["command_counters"],
                    "backup": result["backup"],
                    "survival": result["survival"],
                }
                online_rows.append(row)
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

            assert seed_dynamic is not None
            max_online_routine = max(
                row["routine_delivered"] for row in online_rows if row["seed"] == seed
            )
            dynamic_row = {
                "kind": "evaluator_only_oracle",
                "seed": seed,
                "oracle_id": "oracle.dynamic_energy",
                "total_oracle": int(seed_dynamic["total_oracle"]),
                "max_online_routine_delivered": int(max_online_routine),
                "upper_bound_not_broken": max_online_routine <= int(seed_dynamic["total_oracle"]),
            }
            delivery = primary_only_delivery_reference(seed, task, simulator)
            delivery_row = {
                "kind": "evaluator_only_oracle",
                "seed": seed,
                "oracle_id": "oracle.delivery",
                **delivery,
            }
            oracle_rows.extend([dynamic_row, delivery_row])
            fh.write(json.dumps(dynamic_row, ensure_ascii=False) + "\n")
            fh.write(json.dumps(delivery_row, ensure_ascii=False) + "\n")

    aggregate = {
        "n_seeds": len(seeds),
        "online": {
            arm: {
                "mean": mean_rows([row for row in online_rows if row["arm"] == arm]),
                "mean_routine_delivered": statistics.fmean(
                    row["routine_delivered"] for row in online_rows if row["arm"] == arm
                ),
            }
            for arm in ONLINE_ARMS
        },
        "oracles": {
            "dynamic_energy": {
                "mean_total_oracle": statistics.fmean(
                    row["total_oracle"]
                    for row in oracle_rows
                    if row["oracle_id"] == "oracle.dynamic_energy"
                ),
                "all_upper_bounds_valid": all(
                    row["upper_bound_not_broken"]
                    for row in oracle_rows
                    if row["oracle_id"] == "oracle.dynamic_energy"
                ),
            },
            "delivery_primary_only": {
                "mean_actual_routine_delivered": statistics.fmean(
                    row["actual_routine_delivered"]
                    for row in oracle_rows
                    if row["oracle_id"] == "oracle.delivery"
                ),
                "mean_fixed_send_oracle": statistics.fmean(
                    row["delivery_fixed_send"]["total_oracle"]
                    for row in oracle_rows
                    if row["oracle_id"] == "oracle.delivery"
                ),
                "mean_free_send_require_sample_oracle": statistics.fmean(
                    row["delivery_free_send_require_sample"]["total_oracle"]
                    for row in oracle_rows
                    if row["oracle_id"] == "oracle.delivery"
                ),
                "mean_link_opportunity_ceiling": statistics.fmean(
                    row["delivery_link_opportunity_ceiling"]["total_oracle"]
                    for row in oracle_rows
                    if row["oracle_id"] == "oracle.delivery"
                ),
                "all_upper_bound_orders_valid": all(
                    row["upper_bound_order_valid"]
                    for row in oracle_rows
                    if row["oracle_id"] == "oracle.delivery"
                ),
            },
        },
    }
    dump(out / "aggregate.json", aggregate)

    audit = {
        "status": "PASS",
        "seeds_complete": sorted({row["seed"] for row in online_rows}) == sorted(seeds),
        "online_arms_complete": sorted({row["arm"] for row in online_rows}) == sorted(ONLINE_ARMS),
        "dynamic_energy_upper_bound_valid": aggregate["oracles"]["dynamic_energy"]["all_upper_bounds_valid"],
        "delivery_upper_bound_order_valid": aggregate["oracles"]["delivery_primary_only"]["all_upper_bound_orders_valid"],
        "oracle_separated_from_online": all(row["kind"] == "evaluator_only_oracle" for row in oracle_rows),
    }
    audit["status"] = "PASS" if all(v is True for k, v in audit.items() if k != "status") else "FAIL"
    dump(out / "audit.json", audit)
    dump(
        out / "run_manifest.json",
        {
            "generated_at": datetime.now(UTC).isoformat(),
            "runner": "code/evaluation/agentic/run_communication_baseline_matrix.py",
            "seeds": seeds,
            "result_hashes": {
                p.name: sha256(p)
                for p in sorted(out.iterdir())
                if p.is_file() and p.name not in {"audit.json", "run_manifest.json"}
            },
        },
    )
    print(json.dumps({"audit": audit, "aggregate": aggregate}, ensure_ascii=False, indent=2))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
