"""Unified Communication x Agent metric extraction.

Physical outcome remains primary. Runtime metrics explain *why* a run succeeds or
fails and are never collapsed into a single weighted score.
"""
from __future__ import annotations

from copy import deepcopy
import math


def _ratio(num: float, den: float) -> float | None:
    return None if not den else float(num) / float(den)


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    xs = sorted(float(x) for x in values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * float(p) / 100.0
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    w = pos - lo
    return xs[lo] * (1.0 - w) + xs[hi] * w


def configuration_execution_metrics(inst, operational_task) -> dict:
    """Evaluator-only desired-vs-applied configuration metrics.

    Uses ``Instance.trace_events`` physical state records. This data never enters
    Agent Context/PromptAssembly. Only task-horizon, alive target-node ticks count.
    """
    states: dict[tuple[int, str], tuple[int, int, bool]] = {}
    times: set[int] = set()
    nodes: set[str] = set()
    for row in getattr(inst, "trace_events", ()):
        if len(row) < 7 or row[2] != "state":
            continue
        t_s, node_id, _kind, sample_s, report_s, _soc, alive = row[:7]
        t_s = int(t_s)
        if t_s >= int(operational_task.task_horizon_s):
            continue
        node_id = str(node_id)
        states[(t_s, node_id)] = (int(sample_s), int(report_s), bool(alive))
        times.add(t_s)
        nodes.add(node_id)
    ordered_times = sorted(times)
    diffs = [b - a for a, b in zip(ordered_times, ordered_times[1:]) if b > a]
    tick_s = min(diffs) if diffs else 60
    targets = set(operational_task.target_node_ids) or nodes

    evaluated_node_s = 0
    sample_mismatch_s = 0
    report_mismatch_s = 0
    any_mismatch_s = 0
    for (t_s, node_id), (sample_s, report_s, alive) in states.items():
        if node_id not in targets or not alive:
            continue
        phase = operational_task.phase_at(t_s)
        desired = int(phase.required_period_s)
        evaluated_node_s += tick_s
        sample_bad = sample_s != desired
        report_bad = report_s != desired
        sample_mismatch_s += tick_s if sample_bad else 0
        report_mismatch_s += tick_s if report_bad else 0
        any_mismatch_s += tick_s if (sample_bad or report_bad) else 0

    installs: list[dict] = []
    install_latencies: list[float] = []
    revision_install_latencies: list[float] = []
    phases = list(operational_task.phases)
    for i, phase in enumerate(phases):
        start = int(phase.start_s)
        end = (
            int(phases[i + 1].start_s)
            if i + 1 < len(phases)
            else int(operational_task.task_horizon_s)
        )
        desired = int(phase.required_period_s)
        previous_desired = (
            int(phases[i - 1].required_period_s) if i > 0 else None
        )
        is_revision = i > 0 and desired != previous_desired
        for node_id in sorted(targets):
            first = None
            alive_seen = False
            for t_s in ordered_times:
                if t_s < start or t_s >= end:
                    continue
                state = states.get((t_s, node_id))
                if state is None:
                    continue
                sample_s, report_s, alive = state
                if not alive:
                    continue
                alive_seen = True
                if sample_s == desired and report_s == desired:
                    first = t_s
                    break
            latency = None if first is None else max(0, first - start)
            if latency is not None:
                install_latencies.append(float(latency))
                if is_revision:
                    revision_install_latencies.append(float(latency))
            installs.append(
                {
                    "phase_start_s": start,
                    "phase_end_s": end,
                    "node_id": node_id,
                    "desired_period_s": desired,
                    "is_revision": is_revision,
                    "alive_seen": alive_seen,
                    "installed_at_s": first,
                    "install_latency_s": latency,
                    "installed": first is not None,
                }
            )

    eligible_installs = [x for x in installs if x["alive_seen"]]
    completed_installs = [x for x in eligible_installs if x["installed"]]
    revision_eligible = [x for x in eligible_installs if x["is_revision"]]
    revision_completed = [x for x in revision_eligible if x["installed"]]
    return {
        "authority": "evaluator-only Instance.trace_events + OperationalTask phases",
        "tick_s": tick_s,
        "target_nodes": sorted(targets),
        "evaluated_alive_node_s": evaluated_node_s,
        "config_mismatch_node_s": any_mismatch_s,
        "sampling_mismatch_node_s": sample_mismatch_s,
        "report_mismatch_node_s": report_mismatch_s,
        "config_mismatch_rate": _ratio(any_mismatch_s, evaluated_node_s),
        "sampling_mismatch_rate": _ratio(sample_mismatch_s, evaluated_node_s),
        "report_mismatch_rate": _ratio(report_mismatch_s, evaluated_node_s),
        "install_eligible": len(eligible_installs),
        "install_completed": len(completed_installs),
        "install_completion_rate": _ratio(len(completed_installs), len(eligible_installs)),
        "install_latency_mean_s": (
            sum(install_latencies) / len(install_latencies) if install_latencies else None
        ),
        "install_latency_p50_s": _percentile(install_latencies, 50),
        "install_latency_p90_s": _percentile(install_latencies, 90),
        "install_latency_p95_s": _percentile(install_latencies, 95),
        "revision_install_eligible": len(revision_eligible),
        "revision_install_completed": len(revision_completed),
        "revision_install_completion_rate": _ratio(
            len(revision_completed), len(revision_eligible)
        ),
        "revision_install_latency_mean_s": (
            sum(revision_install_latencies) / len(revision_install_latencies)
            if revision_install_latencies else None
        ),
        "revision_install_latency_p50_s": _percentile(revision_install_latencies, 50),
        "revision_install_latency_p90_s": _percentile(revision_install_latencies, 90),
        "revision_install_latency_p95_s": _percentile(revision_install_latencies, 95),
        "install_rows": installs,
    }


def communication_metrics(result: dict) -> dict:
    routine = result.get("routine", {})
    event = result.get("event", {})
    comm = result.get("communication", {})
    backup = result.get("backup", {})
    repair = result.get("repair", {})
    survival = result.get("survival", {})
    commands = result.get("command_counters", {})
    recovery = result.get("recovery", {})
    evaluator_oracles = result.get("evaluator_oracles", {})
    config = result.get("configuration_execution", {})
    energy_nodes = result.get("energy", {}).get("per_node", {})
    total_consumed = sum(float(v.get("consumed_wh", 0.0)) for v in energy_nodes.values())
    total_harvested = sum(float(v.get("harvested_wh", 0.0)) for v in energy_nodes.values())
    n = int(routine.get("n", 0) or 0)
    delivered = int(routine.get("delivered", 0) or 0)
    collected = max(0, n - int(routine.get("missing_collection", 0) or 0))
    oracle_applicable = evaluator_oracles.get("applicable") is True
    oracle_fixed = evaluator_oracles.get("delivery_fixed_send", {}) if oracle_applicable else {}
    oracle_mid = evaluator_oracles.get("delivery_free_send_require_sample", {}) if oracle_applicable else {}
    oracle_free = evaluator_oracles.get("delivery_link_opportunity_ceiling", {}) if oracle_applicable else {}
    fixed_n = oracle_fixed.get("total_oracle")
    mid_n = oracle_mid.get("total_oracle")
    free_n = oracle_free.get("total_oracle")
    return {
        "routine_obligations": n,
        "routine_collected": collected,
        "routine_delivered": delivered,
        "timely_delivery_rate": _ratio(delivered, n),
        "collection_rate": _ratio(collected, n),
        "delivery_oracle_fixed_send": fixed_n,
        "delivery_oracle_free_send_require_sample": mid_n,
        "delivery_oracle_link_opportunity_ceiling": free_n,
        "delivery_oracle_fixed_rate": _ratio(float(fixed_n or 0), n) if fixed_n is not None else None,
        "delivery_oracle_free_sample_rate": _ratio(float(mid_n or 0), n) if mid_n is not None else None,
        "delivery_oracle_link_opportunity_rate": _ratio(float(free_n or 0), n) if free_n is not None else None,
        "delivery_gap_to_fixed_oracle": (
            None if fixed_n is None else int(fixed_n) - delivered
        ),
        "delivery_gap_to_free_sample_oracle": (
            None if mid_n is None else int(mid_n) - delivered
        ),
        "delivery_gap_to_link_opportunity_ceiling": (
            None if free_n is None else int(free_n) - delivered
        ),
        "delivery_oracle_applicable": oracle_applicable,
        "delivery_oracle_na_reason": (
            None if oracle_applicable else evaluator_oracles.get("reason")
        ),
        "missing_collection": int(routine.get("missing_collection", 0) or 0),
        "missing_delivery": int(routine.get("missing_delivery", 0) or 0),
        "censored": int(routine.get("censored", 0) or 0),
        "delivery_latency_mean_s": routine.get("latency_mean_s"),
        "delivery_latency_p50_s": routine.get("latency_p50_s"),
        "delivery_latency_p90_s": routine.get("latency_p90_s"),
        "delivery_latency_p95_s": routine.get("latency_p95_s"),
        "aoi_mean_s": routine.get("aoi_mean_s"),
        "aoi_p50_s": routine.get("aoi_p50_s"),
        "aoi_p90_s": routine.get("aoi_p90_s"),
        "aoi_p95_s": routine.get("aoi_p95_s"),
        "no_observation_s": routine.get("no_observation_s"),
        "event_delivery_rate": event.get("deliver_rate"),
        "event_match_rate": event.get("match_rate"),
        "samples_collected": int(comm.get("samples_collected", 0) or 0),
        "uplinks": int(comm.get("uplinks", 0) or 0),
        "uplinks_heard": int(comm.get("uplinks_heard", 0) or 0),
        "gateway_forwarded": int(comm.get("gateway_forwarded", 0) or 0),
        "uplink_airtime_h": float(comm.get("airtime_uplink_h", 0.0) or 0.0),
        "downlink_attempts": int(comm.get("downlink_attempts", 0) or 0),
        "downlink_airtime_h": float(comm.get("airtime_downlink_h", 0.0) or 0.0),
        "backup_packets": int(backup.get("backup_packets", 0) or 0),
        "backup_records": int(backup.get("backup_records", 0) or 0),
        "backup_bytes": int(backup.get("backup_bytes_sent", 0) or 0),
        "terminal_dts_attempts": int(repair.get("terminal_dts_attempts", 0) or 0),
        "terminal_dts_success": int(repair.get("terminal_dts_success", 0) or 0),
        "terminal_dts_energy_wh": float(repair.get("terminal_dts_energy_wh", 0.0) or 0.0),
        "access_assist_duration_s": int(repair.get("access_assist_duration_s", 0) or 0),
        "access_assist_dynamic_s": int(repair.get("access_assist_dynamic_s", 0) or 0),
        "access_assist_bypassed": int(repair.get("access_assist_bypassed", 0) or 0),
        "backup_boost_duration_s": int(repair.get("backup_boost_duration_s", 0) or 0),
        "backup_boost_packets": int(repair.get("backup_boost_packets", 0) or 0),
        "backup_boost_bytes": int(repair.get("backup_boost_bytes_sent", 0) or 0),
        "backup_boost_records": int(repair.get("backup_boost_records", 0) or 0),
        "commands_sent": int(commands.get("commands_sent", 0) or 0),
        "commands_delivered": int(commands.get("commands_delivered", 0) or 0),
        "commands_refused": int(commands.get("commands_refused", 0) or 0),
        "command_delivery_rate": _ratio(
            int(commands.get("commands_delivered", 0) or 0),
            int(commands.get("commands_sent", 0) or 0),
        ),
        "config_mismatch_node_s": config.get("config_mismatch_node_s"),
        "config_mismatch_rate": config.get("config_mismatch_rate"),
        "sampling_mismatch_node_s": config.get("sampling_mismatch_node_s"),
        "sampling_mismatch_rate": config.get("sampling_mismatch_rate"),
        "report_mismatch_node_s": config.get("report_mismatch_node_s"),
        "report_mismatch_rate": config.get("report_mismatch_rate"),
        "config_install_completion_rate": config.get("install_completion_rate"),
        "config_install_latency_mean_s": config.get("install_latency_mean_s"),
        "config_install_latency_p50_s": config.get("install_latency_p50_s"),
        "config_install_latency_p90_s": config.get("install_latency_p90_s"),
        "config_install_latency_p95_s": config.get("install_latency_p95_s"),
        "config_revision_install_completion_rate": config.get(
            "revision_install_completion_rate"
        ),
        "config_revision_install_latency_mean_s": config.get(
            "revision_install_latency_mean_s"
        ),
        "config_revision_install_latency_p50_s": config.get(
            "revision_install_latency_p50_s"
        ),
        "config_revision_install_latency_p90_s": config.get(
            "revision_install_latency_p90_s"
        ),
        "config_revision_install_latency_p95_s": config.get(
            "revision_install_latency_p95_s"
        ),
        "writes_changed": int(commands.get("writes_changed", 0) or 0),
        "writes_same_value": int(commands.get("writes_same_value", 0) or 0),
        "alive_nodes": int(survival.get("alive", 0) or 0),
        "total_nodes": int(survival.get("n", 0) or 0),
        "mean_final_soc": survival.get("mean_final_soc"),
        "node_survival_rate": _ratio(
            int(survival.get("alive", 0) or 0), int(survival.get("n", 0) or 0)
        ),
        "total_consumed_wh": total_consumed,
        "total_harvested_wh": total_harvested,
        "recovery_outage_hours": recovery.get("outage_hours"),
        "recovery_observation_s": recovery.get("recovery_observation_s"),
        "recovery_obligations": recovery.get("n_obligations_in_window"),
        "recovery_delivered": recovery.get("delivered"),
        "recovery_delivery_rate": _ratio(
            float(recovery.get("delivered", 0) or 0),
            float(recovery.get("n_obligations_in_window", 0) or 0),
        ),
        "recovery_missing_collection": recovery.get("missing_collection"),
        "recovery_missing_delivery": recovery.get("missing_delivery"),
        "recovery_censored": recovery.get("censored"),
        "recovery_backlog_recovered": recovery.get("backlog_recovered"),
        "recovery": deepcopy(recovery),
    }


def agent_metrics(policy) -> dict:
    out = dict(policy.trace_summary())
    # Explicit aliases used by paper tables / result audits.
    out["context_sufficiency_recall"] = out.pop("required_evidence_recall")
    out["physical_action_confirmation_rate"] = _ratio(
        out.get("confirmed_requests", 0), out.get("accepted_requests", 0)
    )
    return out


def physical_signature(result: dict) -> dict:
    """Policy-independent physical fields used for harness equivalence checks."""
    keep = [
        "by_kind",
        "routine",
        "event",
        "communication",
        "recovery",
        "energy",
        "backup",
        "repair",
        "command_counters",
        "survival",
        "mission_timing",
    ]
    return {k: deepcopy(result.get(k)) for k in keep if k in result}


def metric_delta(lhs: dict, rhs: dict) -> dict:
    """Numeric lhs-rhs deltas for shared scalar metrics."""
    out = {}
    for key in sorted(set(lhs) & set(rhs)):
        a, b = lhs[key], rhs[key]
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            out[key] = float(a) - float(b)
    return out
