#!/usr/bin/env python3
"""Materialize three lifecycle-level Layer-1 failure case studies.

Selection is frozen and transparent over the canonical deterministic paper test:

1. delivery-only miss: first O1 ``comm.local_policy`` row with collection intact
   and at least one delivery miss;
2. energy/collection miss: first O4 ``comm.ea_aoi`` row with ENERGY_EXHAUSTION;
3. task-revision miss: first O2 ``comm.mission_comply`` row with
   TASK_REVISION_NOT_APPLIED.

The selected frozen coordinates are replayed with the identical simulator and
policy, adding only ``collect_rows=True`` / trace instrumentation.  The replay
aggregate must equal the canonical paper row before any case-study facts are
accepted.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
BENCH = ROOT / "code/evaluation/benchmark"
CODE = ROOT / "code"
for _p in (BENCH, CODE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import run_layer1_paper_deterministic_eval as runner  # noqa: E402


CANONICAL = ROOT / "results/benchmark/layer1-paper-deterministic-test/rows.canonical.jsonl"
SPLIT = ROOT / "results/benchmark/layer1-paper-split.json"
OUT = ROOT / "results/benchmark/layer1-paper-deterministic-test/failure-case-studies.json"
MD = ROOT / "results/benchmark/layer1-paper-deterministic-test/FAILURE-CASE-STUDIES.md"


def _rows() -> list[dict[str, Any]]:
    return [json.loads(x) for x in CANONICAL.read_text(encoding="utf-8").splitlines() if x.strip()]


def _online() -> list[dict[str, Any]]:
    return [r for r in _rows() if r.get("kind") == "online_baseline"]


def _select() -> dict[str, dict[str, Any]]:
    rows = _online()

    def first(predicate):
        cand = sorted((r for r in rows if predicate(r)), key=lambda r: r["row_id"])
        if not cand:
            raise AssertionError("case-study selection found no candidate")
        return cand[0]

    return {
        "delivery_only": first(
            lambda r: r["task_template"] == "O1"
            and r["baseline_id"] == "comm.local_policy"
            and int(r["communication_metrics"]["missing_collection"]) == 0
            and int(r["communication_metrics"]["missing_delivery"]) > 0
        ),
        "energy_collection": first(
            lambda r: r["task_template"] == "O4"
            and r["baseline_id"] == "comm.ea_aoi"
            and "ENERGY_EXHAUSTION" in r.get("failure_reasons", [])
        ),
        "task_revision": first(
            lambda r: r["task_template"] == "O2"
            and r["baseline_id"] == "comm.mission_comply"
            and "TASK_REVISION_NOT_APPLIED" in r.get("failure_reasons", [])
        ),
    }


def _coord_map() -> dict[str, dict[str, Any]]:
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    return {row["coordinate_id"]: row for row in split["coordinates"]["test"]}


def _numeric_match(canonical: dict, replay: dict, keys: tuple[str, ...]) -> bool:
    cm = canonical["communication_metrics"]
    rm = runner.communication_metrics(replay)
    for key in keys:
        a, b = cm.get(key), rm.get(key)
        if isinstance(a, float) or isinstance(b, float):
            if a is None or b is None or abs(float(a) - float(b)) > 1e-12:
                return False
        elif a != b:
            return False
    return True


def _failure_class(row: dict) -> str:
    if not row["collected"]:
        return "COLLECTION_MISS_NO_MATCHING_SAMPLE"
    if row["first_heard_at"] is None:
        return "COLLECTED_BUT_NEVER_HEARD_AT_GATEWAY"
    if not row["heard_on_time"]:
        return "LATE_TO_GATEWAY"
    if row["first_received_at"] is None:
        return "ON_TIME_GATEWAY_BUT_NEVER_CENTER"
    if not row["received_on_time"]:
        return "ON_TIME_GATEWAY_BUT_LATE_CENTER"
    return "OTHER"


def _replay(canonical: dict):
    coord = _coord_map()[canonical["coordinate_id"]]
    template = runner.benchmark_episode_catalog()[canonical["task_template"]]
    sim = runner._simulator(template, coord)
    sim["collect_rows"] = True
    result, inst, obligations = runner._run_online(
        int(coord["seed"]), template.task, sim, canonical["baseline_id"]
    )
    check_keys = (
        "timely_delivery_rate",
        "collection_rate",
        "missing_collection",
        "missing_delivery",
        "node_survival_rate",
        "total_consumed_wh",
        "config_revision_install_completion_rate",
    )
    if not _numeric_match(canonical, result, check_keys):
        raise AssertionError(f"instrumented replay drifted: {canonical['row_id']}")
    return coord, template, sim, result, inst, obligations


def _delivery_case(canonical: dict) -> dict[str, Any]:
    coord, _template, _sim, result, _inst, _oblig = _replay(canonical)
    failed = [r for r in result["rows"] if r.get("kind") == "routine" and not r["delivered"]]
    classes = Counter(_failure_class(r) for r in failed)
    example = sorted(failed, key=lambda r: (r["release_at"], r["oid"]))[0]
    return {
        "selection_rule": "lexicographically first O1 comm.local_policy row with collection intact and delivery miss",
        "row_id": canonical["row_id"],
        "coordinate_id": coord["coordinate_id"],
        "baseline_id": canonical["baseline_id"],
        "routine": result["routine"],
        "failed_obligation_classes": dict(sorted(classes.items())),
        "first_failed_obligation": example,
        "interpretation": (
            "Collection is complete; failures occur after sensing. The obligation-level ledger distinguishes "
            "samples that never reach the gateway from samples that reach it only after the deadline, rather than "
            "collapsing both into a generic delivery miss."
        ),
    }


def _energy_case(canonical: dict) -> dict[str, Any]:
    coord, _template, _sim, result, inst, _oblig = _replay(canonical)
    dead = list(result["survival"]["dead"])
    dead_rows = {}
    for nid in dead:
        state_events = [e for e in inst.trace_events if len(e) > 6 and e[1] == nid and e[2] == "state"]
        first_false = next((int(e[0]) for e in state_events if e[6] is False), None)
        samples = sorted(s.taken_at for s in inst.log.samples.values() if s.node_id == nid)
        missed = [
            r for r in result["rows"]
            if r.get("kind") == "routine" and r["node_id"] == nid and not r["collected"]
        ]
        dead_rows[nid] = {
            "first_alive_false_s": first_false,
            "last_sample_taken_at_s": max(samples) if samples else None,
            "power": inst.nodes[nid].power.to_dict(),
            "missing_collection_obligations": len(missed),
            "first_missing_obligation": (sorted(missed, key=lambda r: r["release_at"])[0] if missed else None),
        }
    return {
        "selection_rule": "lexicographically first O4 comm.ea_aoi ENERGY_EXHAUSTION row",
        "row_id": canonical["row_id"],
        "coordinate_id": coord["coordinate_id"],
        "baseline_id": canonical["baseline_id"],
        "routine": result["routine"],
        "survival": result["survival"],
        "dead_node_lifecycle": dead_rows,
        "interpretation": (
            "The failed obligation has no matching sample: the loss is a sensing/survival failure, not a packet "
            "delivery failure. This is why collection and delivery must remain separate outcome dimensions."
        ),
    }


def _revision_case(canonical: dict) -> dict[str, Any]:
    coord, template, sim, result, inst, _oblig = _replay(canonical)
    dense = min(period for _start, period, _level in template.task.mission_schedule())
    revision_start = next(
        int(start)
        for start, period, _level in template.task.mission_schedule()
        if int(period) == int(dense)
    )
    target_events = [
        e for e in inst.trace_events
        if len(e) > 5 and e[2] in {"plan", "sent", "applied"}
        and (
            (e[2] in {"plan", "sent"} and e[4] in {"set_sampling_interval", "set_report_period"} and int(e[5]) == int(dense))
            or (e[2] == "applied" and e[3] in {"set_sampling_interval", "set_report_period"} and int(e[4]) == int(dense))
        )
    ]
    by_type = Counter(e[2] for e in target_events)
    first_by_type = {
        typ: min((int(e[0]) for e in target_events if e[2] == typ), default=None)
        for typ in ("plan", "sent", "applied")
    }
    applied_by_node: dict[str, set[str]] = {}
    for e in target_events:
        if e[2] != "applied":
            continue
        applied_by_node.setdefault(str(e[1]), set()).add(str(e[3]))
    complete_nodes = sorted(
        nid for nid, ops in applied_by_node.items()
        if {"set_sampling_interval", "set_report_period"} <= ops
    )
    routine_failed = [r for r in result["rows"] if r.get("kind") == "routine" and not r["delivered"]]
    before_first_plan = [
        r for r in routine_failed
        if first_by_type["plan"] is not None
        and revision_start <= int(r["release_at"]) < int(first_by_type["plan"])
    ]
    classes = Counter(_failure_class(r) for r in routine_failed)
    return {
        "selection_rule": "lexicographically first O2 comm.mission_comply TASK_REVISION_NOT_APPLIED row",
        "row_id": canonical["row_id"],
        "coordinate_id": coord["coordinate_id"],
        "baseline_id": canonical["baseline_id"],
        "task_schedule": [list(x) for x in template.task.mission_schedule()],
        "revision_required_at_s": revision_start,
        "required_dense_period_s": dense,
        "template_outage": {
            "outage_start_s": int(float(sim["outage_start_h"]) * 3600),
            "outage_end_s": int((float(sim["outage_start_h"]) + float(sim["outage_hours"])) * 3600),
        },
        "revision_event_counts": dict(sorted(by_type.items())),
        "first_revision_event_s": first_by_type,
        "nodes_with_both_dense_settings_applied": complete_nodes,
        "config_revision_install_completion_rate": runner.communication_metrics(result)["config_revision_install_completion_rate"],
        "routine": result["routine"],
        "failed_obligation_classes": dict(sorted(classes.items())),
        "failed_obligations_released_after_revision_before_first_plan": len(before_first_plan),
        "interpretation": (
            "The operational requirement tightens during the declared communication outage. All nodes remain alive, "
            "yet only a subset receives both dense sampling/report settings; many new dense-cadence obligations then "
            "lack matching samples. This is an execution-of-task-revision failure, not energy death."
        ),
    }


def main() -> int:
    selected = _select()
    payload = {
        "stage": "LAYER1_PAPER_FAILURE_CASE_STUDIES",
        "selection_is_posthoc_but_rule_based": True,
        "cases": {
            "delivery_only": _delivery_case(selected["delivery_only"]),
            "energy_collection": _energy_case(selected["energy_collection"]),
            "task_revision": _revision_case(selected["task_revision"]),
        },
        "checks": {
            "three_distinct_failure_layers": True,
            "instrumented_replays_match_frozen_aggregate": True,
        },
        "claim_boundary": [
            "Cases are illustrative post-hoc diagnostics selected by fixed lexicographic rules from the frozen deterministic test; they are not a new benchmark split or quantitative effect estimate.",
            "collect_rows/trace instrumentation does not alter the frozen simulator or policy and is accepted only after aggregate metrics match the canonical row.",
            "The task-revision case reports observed trace timing; it does not infer hidden causal reasons beyond the declared outage/task schedule and recorded plan/sent/applied events."
        ],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    d = payload["cases"]["delivery_only"]
    e = payload["cases"]["energy_collection"]
    t = payload["cases"]["task_revision"]
    md = [
        "# Layer-1 Failure Case Studies",
        "",
        "These are rule-selected illustrative diagnostics from the frozen deterministic paper test; they do not change the benchmark or effect estimates.",
        "",
        "## Delivery-only failure",
        "",
        f"- `{d['row_id']}`",
        f"- routine: {d['routine']}",
        f"- failed obligation classes: {d['failed_obligation_classes']}",
        f"- first failed obligation: `{d['first_failed_obligation']['oid']}` (release {d['first_failed_obligation']['release_at']}s, deadline {d['first_failed_obligation']['deadline']}s, first gateway heard {d['first_failed_obligation']['first_heard_at']})",
        "",
        "## Energy / collection failure",
        "",
        f"- `{e['row_id']}`",
        f"- dead nodes: {e['survival']['dead']}",
        f"- dead-node lifecycle: {e['dead_node_lifecycle']}",
        "",
        "## Task-revision execution failure",
        "",
        f"- `{t['row_id']}`",
        f"- task schedule: {t['task_schedule']}",
        f"- outage: {t['template_outage']}",
        f"- first plan/sent/applied: {t['first_revision_event_s']}",
        f"- nodes with both dense settings applied: {t['nodes_with_both_dense_settings_applied']}",
        f"- revision completion rate: {t['config_revision_install_completion_rate']}",
        f"- failure classes: {t['failed_obligation_classes']}",
        "",
        "Full obligation rows and trace-derived counts are in `failure-case-studies.json`.",
    ]
    MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "summary": str(MD), "row_ids": {k: v["row_id"] for k, v in payload["cases"].items()}}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
