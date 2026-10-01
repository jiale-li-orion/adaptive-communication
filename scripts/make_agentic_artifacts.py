#!/usr/bin/env python3
"""Generate Agentic Communication paper/research artifacts from frozen results.

Single source of numeric truth:

    results/agentic/*/{aggregate,audit,source_manifest}.json

Generated/controlled outputs:

    paper/generated/table_agentic_o2_{global,localized}.{zh,en}.tex
    paper/generated/table_agentic_o2_baselines.{zh,en}.tex
    paper/generated/table_agentic_source_period.{zh,en}.tex
    paper/generated/table_agentic_task_transfer.{zh,en}.tex
    paper/generated/table_agentic_attribution_infra.{zh,en}.tex
    paper/generated/table_agentic_o2_{global,localized}.meta.json
    paper/generated/agentic_facts.tex
    paper/generated/agentic_facts.meta.json
    research/generated/agentic_o2_summary.md
    research/README.md        (controlled block only)
    results/README.md         (controlled registry block only)

Use ``--check`` in CI/audit mode.  A result change without regeneration must fail.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
PAPER_GEN = ROOT / "paper" / "generated"
RESEARCH_GEN = ROOT / "research" / "generated"

GLOBAL = ROOT / "results" / "agentic" / "o2-risk-escalation-v1"
LOCAL = ROOT / "results" / "agentic" / "o2-localized-risk-escalation-v1"
DIAGNOSIS = ROOT / "results" / "agentic" / "o2-diagnosis-first-v1"
BASELINE_MATRIX = ROOT / "results" / "agentic" / "o2-baseline-matrix-v1"
SOURCE_PERIOD = ROOT / "results" / "agentic" / "source-period-smoke-v1.json"
ROBUSTNESS_MATRIX = ROOT / "results" / "agentic" / "robustness-matrix-v1"
TASK_TRANSFER = ROOT / "results" / "agentic" / "task-transfer-qili-v1"
ATTRIBUTION_INFRA = ROOT / "results" / "agentic" / "attribution-matrix-infra-v1"
COMM_BASELINE_MATRIX = ROOT / "results" / "agentic" / "communication-baseline-matrix-v1"
MODEL_CONTEXT_INPUTS = (
    ROOT
    / "results"
    / "agentic"
    / "model-context-inputs-v1"
    / "global"
    / "seed-000"
    / "frozen_input_manifest.json"
)

RESEARCH_README = ROOT / "research" / "README.md"
RESULTS_README = ROOT / "results" / "README.md"

BEGIN = "<!-- BEGIN GENERATED: agentic-o2 -->"
END = "<!-- END GENERATED: agentic-o2 -->"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def f(value: float, nd: int) -> str:
    q = Decimal(1).scaleb(-nd)
    return str(Decimal(repr(float(value))).quantize(q, rounding=ROUND_HALF_UP))


def pct(value: float, nd: int = 2) -> str:
    return f(100.0 * float(value), nd)


def tex_cell(value) -> str:
    """Escape plain manifest/result labels before emitting them into a TeX cell."""
    text = str(value)
    for src, dst in (
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("#", r"\#"),
        ("_", r"\_"),
    ):
        text = text.replace(src, dst)
    return text.replace("→", r"$\rightarrow$")


def _bundle(root: Path) -> dict:
    agg_p = root / "aggregate.json"
    audit_p = root / "audit.json"
    source_p = root / "source_manifest.json"
    contract_p = root / "experiment_contract.json"
    for p in (agg_p, audit_p, source_p, contract_p):
        if not p.is_file():
            raise FileNotFoundError(p)
    audit = load(audit_p)
    if audit.get("status") != "PASS" or not audit.get("all_physical_equivalent"):
        raise RuntimeError(f"refusing to publish unaudited/non-equivalent result: {root}")
    contract = load(contract_p)
    return {
        "root": root,
        "aggregate": load(agg_p),
        "audit": audit,
        "source": load(source_p),
        "contract": contract,
        "sha256": {
            "aggregate.json": sha256(agg_p),
            "audit.json": sha256(audit_p),
            "source_manifest.json": sha256(source_p),
            "experiment_contract.json": sha256(contract_p),
        },
    }


def _attribution_bundle(root: Path) -> dict:
    agg_p = root / "aggregate.json"
    audit_p = root / "audit.json"
    contract_p = root / "experiment_contract.json"
    rows_p = root / "per_turn_results.jsonl"
    for p in (agg_p, audit_p, contract_p, rows_p):
        if not p.is_file():
            raise FileNotFoundError(p)
    audit = load(audit_p)
    if (
        audit.get("status") != "PASS"
        or not audit.get("upstream_full_replacement_restores_gold_assembly")
        or not audit.get("planner_posthoc_keeps_gold_assembly")
        or audit.get("final_tool_exact_match_rate") != 1.0
    ):
        raise RuntimeError(f"refusing to publish failed attribution infrastructure: {root}")
    return {
        "root": root,
        "aggregate": load(agg_p),
        "audit": audit,
        "contract": load(contract_p),
        "sha256": {
            "aggregate.json": sha256(agg_p),
            "audit.json": sha256(audit_p),
            "experiment_contract.json": sha256(contract_p),
            "per_turn_results.jsonl": sha256(rows_p),
        },
    }


def _task_transfer_bundle(root: Path) -> dict:
    agg_p = root / "aggregate.json"
    audit_p = root / "audit.json"
    source_p = root / "source_manifest.json"
    contract_p = root / "experiment_contract.json"
    for p in (agg_p, audit_p, source_p, contract_p):
        if not p.is_file():
            raise FileNotFoundError(p)
    audit = load(audit_p)
    if (
        audit.get("status") != "PASS"
        or not audit.get("all_physical_equal_reference")
        or not audit.get("all_replay_exact")
        or not audit.get("same_runtime_and_planner")
        or not audit.get("qili_source_ref_present")
    ):
        raise RuntimeError(f"refusing to publish failed task transfer: {root}")
    return {
        "root": root,
        "aggregate": load(agg_p),
        "audit": audit,
        "source": load(source_p),
        "contract": load(contract_p),
        "sha256": {
            "aggregate.json": sha256(agg_p),
            "audit.json": sha256(audit_p),
            "source_manifest.json": sha256(source_p),
            "experiment_contract.json": sha256(contract_p),
        },
    }


def _baseline_matrix_bundle(root: Path) -> dict:
    agg_p = root / "aggregate.json"
    audit_p = root / "audit.json"
    source_p = root / "source_manifest.json"
    contract_p = root / "experiment_contract.json"
    for p in (agg_p, audit_p, source_p, contract_p):
        if not p.is_file():
            raise FileNotFoundError(p)
    audit = load(audit_p)
    if (
        audit.get("status") != "PASS"
        or not audit.get("all_physical_equal_reference")
        or not audit.get("all_replay_exact")
    ):
        raise RuntimeError(f"refusing to publish failed baseline matrix: {root}")
    return {
        "root": root,
        "aggregate": load(agg_p),
        "audit": audit,
        "source": load(source_p),
        "contract": load(contract_p),
        "sha256": {
            "aggregate.json": sha256(agg_p),
            "audit.json": sha256(audit_p),
            "source_manifest.json": sha256(source_p),
            "experiment_contract.json": sha256(contract_p),
        },
    }


def _source_period_bundle(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = load(path)
    if payload.get("status") != "PASS" or not payload.get("all_physical_equivalent"):
        raise RuntimeError(f"refusing to publish failed source-period smoke: {path}")
    return {"path": path, "payload": payload, "sha256": sha256(path)}


def _communication_baseline_bundle(root: Path) -> dict:
    agg_p = root / "aggregate.json"
    audit_p = root / "audit.json"
    contract_p = root / "experiment_contract.json"
    rows_p = root / "per_seed_results.jsonl"
    for p in (agg_p, audit_p, contract_p, rows_p):
        if not p.is_file():
            raise FileNotFoundError(p)
    audit = load(audit_p)
    if (
        audit.get("status") != "PASS"
        or not audit.get("dynamic_energy_upper_bound_valid")
        or not audit.get("delivery_upper_bound_order_valid")
        or not audit.get("oracle_separated_from_online")
    ):
        raise RuntimeError(f"refusing to publish failed communication baseline matrix: {root}")
    return {
        "root": root,
        "aggregate": load(agg_p),
        "audit": audit,
        "contract": load(contract_p),
        "sha256": {
            "aggregate.json": sha256(agg_p),
            "audit.json": sha256(audit_p),
            "experiment_contract.json": sha256(contract_p),
            "per_seed_results.jsonl": sha256(rows_p),
        },
    }


def _model_context_input_bundle(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = load(path)
    if payload.get("mode") != "frozen_model_context_inputs":
        raise RuntimeError(f"unexpected model-context input manifest: {path}")
    expected = {"task_conditioned", "full_dump", "generic_react"}
    rows = payload.get("rows") or []
    if {row.get("context_mode") for row in rows} != expected:
        raise RuntimeError(f"incomplete model-context input set: {path}")
    for row in rows:
        if not row.get("physical_equal_legacy"):
            raise RuntimeError(f"non-equivalent frozen model input: {row.get('context_mode')}")
        if not (row.get("replay_audit") or {}).get("passed"):
            raise RuntimeError(f"failed replay for frozen model input: {row.get('context_mode')}")
        trace = ROOT / row["trace"]
        if not trace.is_file() or sha256(trace) != row.get("trace_sha256"):
            raise RuntimeError(f"frozen model input trace hash mismatch: {trace}")
    return {"path": path, "payload": payload, "sha256": sha256(path)}


def _robustness_bundle(root: Path) -> dict:
    agg_p = root / "aggregate.json"
    audit_p = root / "audit.json"
    source_p = root / "source_manifest.json"
    contract_p = root / "experiment_contract.json"
    rows_p = root / "per_episode_results.jsonl"
    for p in (agg_p, audit_p, source_p, contract_p, rows_p):
        if not p.is_file():
            raise FileNotFoundError(p)
    audit = load(audit_p)
    if (
        audit.get("status") != "PASS"
        or not audit.get("all_physical_equal_reference")
        or not audit.get("all_replay_exact")
        or not all((audit.get("axis_activation") or {}).values())
    ):
        raise RuntimeError(f"refusing to publish failed robustness matrix: {root}")
    rows = [json.loads(line) for line in rows_p.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {
        "root": root,
        "aggregate": load(agg_p),
        "audit": audit,
        "source": load(source_p),
        "contract": load(contract_p),
        "rows": rows,
        "sha256": {
            "aggregate.json": sha256(agg_p),
            "audit.json": sha256(audit_p),
            "source_manifest.json": sha256(source_p),
            "experiment_contract.json": sha256(contract_p),
            "per_episode_results.jsonl": sha256(rows_p),
        },
    }


def _diagnosis_bundle(root: Path) -> dict:
    agg_p = root / "aggregate.json"
    audit_p = root / "audit.json"
    source_p = root / "source_manifest.json"
    contract_p = root / "experiment_contract.json"
    for p in (agg_p, audit_p, source_p, contract_p):
        if not p.is_file():
            raise FileNotFoundError(p)
    audit = load(audit_p)
    if (
        audit.get("status") != "PASS"
        or not audit.get("all_physical_equal")
        or not audit.get("all_replay_exact")
    ):
        raise RuntimeError(f"refusing to publish failed diagnosis baseline: {root}")
    contract = load(contract_p)
    return {
        "root": root,
        "aggregate": load(agg_p),
        "audit": audit,
        "source": load(source_p),
        "contract": contract,
        "sha256": {
            "aggregate.json": sha256(agg_p),
            "audit.json": sha256(audit_p),
            "source_manifest.json": sha256(source_p),
            "experiment_contract.json": sha256(contract_p),
        },
    }


def agentic_facts(
    global_b: dict,
    local_b: dict,
    diagnosis_b: dict,
    baseline_b: dict,
    source_period_b: dict,
    robustness_b: dict,
    model_inputs_b: dict,
) -> tuple[str, dict]:
    gm = global_b["aggregate"]["task_conditioned"]["mean"]
    lm = local_b["aggregate"]["task_conditioned"]["mean"]
    lf = local_b["aggregate"]["full_dump"]["mean"]
    dd = diagnosis_b["aggregate"]["paired_delta_mean"]
    bm = baseline_b["aggregate"]["paired_delta_mean"]
    sp = source_period_b["payload"]["rows"]
    mi = {row["context_mode"]: row for row in model_inputs_b["payload"]["rows"]}
    bm = baseline_b["aggregate"]["paired_delta_mean"]
    sp = source_period_b["payload"]["rows"]
    sp_by_year = {int(row["year"]): row for row in sp}
    defs = {
        "agenticGlobalTdr": f(gm["communication.timely_delivery_rate"], 5),
        "agenticGlobalCollection": f(gm["communication.collection_rate"], 5),
        "agenticGlobalLatencyP": f(gm["communication.delivery_latency_p90_s"], 1),
        "agenticGlobalBackupBytes": f(gm["communication.backup_bytes"], 1),
        "agenticGlobalEnergy": f(gm["communication.total_consumed_wh"], 5),
        "agenticLocalTdr": f(lm["communication.timely_delivery_rate"], 5),
        "agenticLocalCollection": f(lm["communication.collection_rate"], 5),
        "agenticLocalLatencyP": f(lm["communication.delivery_latency_p90_s"], 1),
        "agenticLocalTaskEvidence": f(lm["agent.mean_selected_evidence"], 2),
        "agenticLocalDumpEvidence": f(lf["agent.mean_selected_evidence"], 2),
        "agenticLocalTaskBytes": f(lm["agent.mean_materialized_bytes"], 1),
        "agenticLocalDumpBytes": f(lf["agent.mean_materialized_bytes"], 1),
        "agenticLocalSufficiency": f(lm["agent.context_sufficiency_recall"], 3),
        "agenticLocalConfirmRate": pct(lm["agent.physical_action_confirmation_rate"]),
        "agenticDiagnosisModelRequests": f(dd["model_requests"], 2),
        "agenticDiagnosisCapabilityRequests": f(dd["capability_requests"], 2),
        "agenticDiagnosisContexts": f(dd["context_manifests"], 2),
        "agenticDiagnosisPercepts": f(dd["percepts"], 2),
        "agenticDiagnosisMaterializedBytes": f(dd["total_materialized_bytes"], 1),
        "agenticFixedOrderModelRequests": f(bm["fixed_order_eager"]["model_requests"], 2),
        "agenticFixedOrderCapabilityRequests": f(bm["fixed_order_eager"]["capability_requests"], 2),
        "agenticFixedOrderMaterializedBytes": f(bm["fixed_order_eager"]["total_materialized_bytes"], 1),
        "agenticGenericReactModelRequests": f(bm["generic_react"]["model_requests"], 2),
        "agenticGenericReactCapabilityRequests": f(bm["generic_react"]["capability_requests"], 2),
        "agenticGenericReactContexts": f(bm["generic_react"]["context_manifests"], 2),
        "agenticGenericReactMaterializedBytes": f(bm["generic_react"]["total_materialized_bytes"], 1),
        "agenticEvidenceAwareExtraCapabilities": f(bm["evidence_aware"]["capability_requests"], 2),
        "agenticSourceHarvestTwentyTwo": f(sp_by_year[2022]["total_harvested_wh"], 5),
        "agenticSourceHarvestTwentyThree": f(sp_by_year[2023]["total_harvested_wh"], 5),
        "agenticSourceHarvestTwentyFour": f(sp_by_year[2024]["total_harvested_wh"], 5),
        "agenticRobustnessCoordinates": str(int(robustness_b["aggregate"]["n_coordinates"])),
        "agenticRobustnessAxes": str(len(robustness_b["aggregate"]["axes"])),
        "agenticTaskContextProtocolBytes": f(mi["task_conditioned"]["protocol_bytes_mean"], 1),
        "agenticFullDumpProtocolBytes": f(mi["full_dump"]["protocol_bytes_mean"], 1),
        "agenticGenericReactProtocolBytes": f(mi["generic_react"]["protocol_bytes_mean"], 1),
    }
    lines = [
        "%% Generated by scripts/make_agentic_artifacts.py; do not edit.",
        "%% Agentic Communication prose numbers must use these macros rather than literals.",
    ]
    for name in sorted(defs):
        if not name.isalpha():
            raise RuntimeError(f"TeX macro name must contain letters only: {name}")
        lines.append(f"\\newcommand{{\\{name}}}{{{defs[name]}}}")
    meta = {
        "generator": "scripts/make_agentic_artifacts.py",
        "definitions": defs,
        "sources": {
            "global": {
                "root": str(global_b["root"].relative_to(ROOT)),
                "aggregate_sha256": global_b["sha256"]["aggregate.json"],
                "audit_status": global_b["audit"]["status"],
                "all_physical_equivalent": global_b["audit"]["all_physical_equivalent"],
            },
            "localized": {
                "root": str(local_b["root"].relative_to(ROOT)),
                "aggregate_sha256": local_b["sha256"]["aggregate.json"],
                "audit_status": local_b["audit"]["status"],
                "all_physical_equivalent": local_b["audit"]["all_physical_equivalent"],
            },
            "diagnosis_first": {
                "root": str(diagnosis_b["root"].relative_to(ROOT)),
                "aggregate_sha256": diagnosis_b["sha256"]["aggregate.json"],
                "audit_status": diagnosis_b["audit"]["status"],
                "all_physical_equal": diagnosis_b["audit"]["all_physical_equal"],
            },
            "baseline_matrix": {
                "root": str(baseline_b["root"].relative_to(ROOT)),
                "aggregate_sha256": baseline_b["sha256"]["aggregate.json"],
                "audit_status": baseline_b["audit"]["status"],
                "all_physical_equal_reference": baseline_b["audit"]["all_physical_equal_reference"],
            },
            "source_period": {
                "path": str(source_period_b["path"].relative_to(ROOT)),
                "sha256": source_period_b["sha256"],
                "status": source_period_b["payload"]["status"],
            },
            "robustness": {
                "root": str(robustness_b["root"].relative_to(ROOT)),
                "aggregate_sha256": robustness_b["sha256"]["aggregate.json"],
                "audit_status": robustness_b["audit"]["status"],
                "axis_activation": robustness_b["audit"]["axis_activation"],
            },
            "model_context_inputs": {
                "path": str(model_inputs_b["path"].relative_to(ROOT)),
                "sha256": model_inputs_b["sha256"],
            },
        },
    }
    return "\n".join(lines) + "\n", meta


def _mean(bundle: dict, arm: str, key: str):
    return bundle["aggregate"][arm]["mean"][key]


def _physical_equal_label(lang: str) -> str:
    return "yes" if lang == "en" else "是"


def render_global_table(bundle: dict, lang: str) -> str:
    labels = {
        "en": {
            "legacy_comply": "legacy comply",
            "task_conditioned": "task-conditioned runtime",
            "full_dump": "FullDump runtime",
            "head": "Arm & TDR (\\%) & Collection (\\%) & p90 latency (s) & Energy (Wh) & Backup (B) & Physical = ref",
        },
        "zh": {
            "legacy_comply": "legacy comply",
            "task_conditioned": "task-conditioned runtime",
            "full_dump": "FullDump runtime",
            "head": "实验臂 & TDR (\\%) & 采集率 (\\%) & p90 时延 (s) & 能耗 (Wh) & 备用字节 & 与参照物理等价",
        },
    }[lang]
    rows = []
    for arm in ("legacy_comply", "task_conditioned", "full_dump"):
        m = bundle["aggregate"][arm]["mean"]
        rows.append(
            f"{labels[arm]} & {pct(m['communication.timely_delivery_rate'])} & "
            f"{pct(m['communication.collection_rate'])} & "
            f"{f(m['communication.delivery_latency_p90_s'], 1)} & "
            f"{f(m['communication.total_consumed_wh'], 5)} & "
            f"{f(m['communication.backup_bytes'], 1)} & {_physical_equal_label(lang)}"
        )
    body = "\\\\\n".join(rows) + "\\\\"
    return (
        "%% Generated by scripts/make_agentic_artifacts.py; do not edit.\n"
        "\\begin{tabular}{lrrrrrc}\n"
        "\\toprule\n"
        f"{labels['head']}\\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
    )

def render_attribution_table(bundle: dict, lang: str) -> str:
    labels = {
        "en": {
            "head": "Cumulative layer & Assembly = gold (\\%) & Stop correct (\\%) & Tool exact (\\%) & Arg acc. (\\%) & Unresolved arg slots",
            "base": "corrupted base",
            "gold_task": "+ Task",
            "gold_evidence_need": "+ EvidenceNeed",
            "gold_percept": "+ Percept",
            "gold_context": "+ Context",
            "gold_capability_selection": "+ capability selection",
            "gold_capability_order": "+ capability order",
            "gold_capability_arguments": "+ capability arguments",
        },
        "zh": {
            "head": "累计替换层 & Assembly=gold (\\%) & Stop 正确 (\\%) & Tool exact (\\%) & 参数正确 (\\%) & 未解析参数槽",
            "base": "corrupted base",
            "gold_task": "+ Task",
            "gold_evidence_need": "+ EvidenceNeed",
            "gold_percept": "+ Percept",
            "gold_context": "+ Context",
            "gold_capability_selection": "+ capability selection",
            "gold_capability_order": "+ capability order",
            "gold_capability_arguments": "+ capability arguments",
        },
    }[lang]
    rows = []
    for row in bundle["aggregate"]["rows"]:
        layers = row["cumulative_layers"]
        key = layers[-1] if layers else "base"
        arg = row.get("argument_grounding_accuracy")
        rows.append(
            f"{labels[key]} & {pct(row['assembly_match_rate'])} & "
            f"{pct(row['stopping_correctness']) if row['stopping_correctness'] is not None else '--'} & "
            f"{pct(row['tool_exact_match_rate']) if row['tool_exact_match_rate'] is not None else '--'} & "
            f"{pct(arg) if arg is not None else '--'} & "
            f"{f(row['mean_unresolved_argument_slots'], 2)}"
        )
    return (
        "%% Generated by scripts/make_agentic_artifacts.py; do not edit.\n"
        "\\begin{tabular}{lrrrrr}\n"
        "\\toprule\n"
        f"{labels['head']}\\\\\n"
        "\\midrule\n"
        + "\\\\\n".join(rows)
        + "\\\\\n\\bottomrule\n\\end{tabular}\n"
    )


def render_task_transfer_table(bundle: dict, lang: str) -> str:
    tasks = bundle["contract"]["task_schedules"]
    rows = []
    labels = {
        "hand_authored_o2": ("hand-authored O2", "手工 O2"),
        "qili_source_derived": ("Qili source-derived", "Qili 来源派生"),
    }
    source_label = {
        "hand_authored_o2": "benchmark authority",
        "qili_source_derived": "S14",
    }
    for schedule_id in ("hand_authored_o2", "qili_source_derived"):
        task = tasks[schedule_id]
        phase_profile = " / ".join(
            f"{int(p['start_s']) // 3600}h:{int(p['required_period_s'])}s"
            for p in task["phases"]
        )
        summary = bundle["aggregate"]["schedules"][schedule_id]
        yes = "yes" if lang == "en" else "是"
        no = "no" if lang == "en" else "否"
        rows.append(
            f"{labels[schedule_id][0 if lang == 'en' else 1]} & {source_label[schedule_id]} & "
            f"{phase_profile} & {yes if summary['physical_equal_reference'] else no} & "
            f"{yes if summary['replay_exact'] else no}"
        )
    head = {
        "en": "Operational Task & Authority & Benchmark phase profile & Paired physical = ref & Replay exact",
        "zh": "Operational Task & Authority & Benchmark 阶段 profile & 配对物理等价 & Replay exact",
    }[lang]
    return (
        "%% Generated by scripts/make_agentic_artifacts.py; do not edit.\n"
        "\\begin{tabular}{lllcc}\n"
        "\\toprule\n"
        f"{head}\\\\\n"
        "\\midrule\n"
        + "\\\\\n".join(rows)
        + "\\\\\n\\bottomrule\n\\end{tabular}\n"
    )


def render_robustness_table(bundle: dict, lang: str) -> str:
    grouped: dict[str, list[dict]] = {}
    for row in bundle["rows"]:
        grouped.setdefault(row["axis"], []).append(row)
    axis_labels = {
        "weather_window": ("weather window", "天气窗口"),
        "backhaul_outage": ("backhaul outage", "回传中断"),
        "target_scope": ("target scope", "任务范围"),
        "evidence_owner": ("evidence owner", "证据 owner"),
        "deployment_scale": ("deployment scale", "部署规模"),
    }
    signal = {}
    if "weather_window" in grouped:
        a, b = grouped["weather_window"]
        signal["weather_window"] = (
            f"harvest {f(a['communication_metrics']['total_harvested_wh'], 5)}→"
            f"{f(b['communication_metrics']['total_harvested_wh'], 5)} Wh"
        )
    if "backhaul_outage" in grouped:
        a, b = grouped["backhaul_outage"]
        signal["backhaul_outage"] = (
            f"backup {f(a['communication_metrics']['backup_bytes'], 0)}→"
            f"{f(b['communication_metrics']['backup_bytes'], 0)} B"
        )
    if "target_scope" in grouped:
        a, b = grouped["target_scope"]
        signal["target_scope"] = (
            f"obligations {a['communication_metrics']['routine_obligations']}→"
            f"{b['communication_metrics']['routine_obligations']}"
        )
    if "evidence_owner" in grouped:
        a, b = grouped["evidence_owner"]
        signal["evidence_owner"] = (
            "/".join(a["observed_owner_classes"]) + "→" + "/".join(b["observed_owner_classes"])
        )
    if "deployment_scale" in grouped:
        a, b = grouped["deployment_scale"]
        signal["deployment_scale"] = f"nodes {a['node_count']}→{b['node_count']}"

    head = {
        "en": "Axis & Coordinates & Activated signal & Paired physical = ref & Replay exact",
        "zh": "轴 & 坐标两端 & 实际激活信号 & 配对物理等价 & Replay exact",
    }[lang]
    rows = []
    order = ("weather_window", "backhaul_outage", "target_scope", "evidence_owner", "deployment_scale")
    for axis in order:
        xs = grouped[axis]
        label = axis_labels[axis][0 if lang == "en" else 1]
        levels = tex_cell(f"{xs[0]['level']}→{xs[1]['level']}")
        physical = all(x["physical_equal_reference"] for x in xs)
        replay = all(x["replay_passed"] for x in xs)
        yes = "yes" if lang == "en" else "是"
        no = "no" if lang == "en" else "否"
        rows.append(
            f"{label} & {levels} & {tex_cell(signal[axis])} & {yes if physical else no} & {yes if replay else no}"
        )
    return (
        "%% Generated by scripts/make_agentic_artifacts.py; do not edit.\n"
        "\\begin{tabular}{llllcc}\n"
        "\\toprule\n"
        f"{head}\\\\\n"
        "\\midrule\n"
        + "\\\\\n".join(rows)
        + "\\\\\n\\bottomrule\n\\end{tabular}\n"
    )


def render_baseline_table(bundle: dict, lang: str) -> str:
    labels = {
        "en": {
            "evidence_aware": "task-conditioned evidence",
            "diagnosis_first": "diagnosis-first",
            "fixed_order_eager": "fixed-order eager",
            "generic_react": "generic ReAct context",
            "head": "Baseline & Extra model calls & Extra tool calls & Extra contexts & Extra materialized bytes & Physical = ref",
        },
        "zh": {
            "evidence_aware": "task-conditioned evidence",
            "diagnosis_first": "diagnosis-first",
            "fixed_order_eager": "fixed-order eager",
            "generic_react": "generic ReAct context",
            "head": "基线 & 额外 model 调用 & 额外 tool 调用 & 额外 Context & 额外 materialized bytes & 与参照物理等价",
        },
    }[lang]
    means = bundle["aggregate"]["paired_delta_mean"]
    rows = []
    for arm in ("evidence_aware", "diagnosis_first", "fixed_order_eager", "generic_react"):
        m = means[arm]
        rows.append(
            f"{labels[arm]} & {f(m['model_requests'], 1)} & "
            f"{f(m['capability_requests'], 1)} & {f(m['context_manifests'], 1)} & "
            f"{f(m['total_materialized_bytes'], 1)} & {_physical_equal_label(lang)}"
        )
    return (
        "%% Generated by scripts/make_agentic_artifacts.py; do not edit.\n"
        "\\begin{tabular}{lrrrrc}\n"
        "\\toprule\n"
        f"{labels['head']}\\\\\n"
        "\\midrule\n"
        + "\\\\\n".join(rows)
        + "\\\\\n\\bottomrule\n\\end{tabular}\n"
    )


def render_source_period_table(bundle: dict, lang: str) -> str:
    labels = {
        "en": "Split & NASA POWER year & Harvested (Wh) & Consumed (Wh) & TDR (\\%) & Physical = paired ref",
        "zh": "Split & NASA POWER 年份 & Harvested (Wh) & Consumed (Wh) & TDR (\\%) & 与配对参照物理等价",
    }
    rows = []
    for row in bundle["payload"]["rows"]:
        rows.append(
            f"{row['split']} & {row['year']} & {f(row['total_harvested_wh'], 5)} & "
            f"{f(row['total_consumed_wh'], 5)} & {pct(row['timely_delivery_rate'])} & "
            f"{_physical_equal_label(lang)}"
        )
    return (
        "%% Generated by scripts/make_agentic_artifacts.py; do not edit.\n"
        "\\begin{tabular}{lrrrrc}\n"
        "\\toprule\n"
        f"{labels[lang]}\\\\\n"
        "\\midrule\n"
        + "\\\\\n".join(rows)
        + "\\\\\n\\bottomrule\n\\end{tabular}\n"
    )


def render_localized_table(bundle: dict, lang: str) -> str:
    labels = {
        "en": {
            "task_conditioned": "task-conditioned",
            "full_dump": "FullDump",
            "head": "Context & Selected evidence & Materialized bytes & Sufficiency & Action confirm (\\%) & Physical = ref",
        },
        "zh": {
            "task_conditioned": "task-conditioned",
            "full_dump": "FullDump",
            "head": "Context & 选中 evidence & materialized bytes & 充分性 & 动作确认率 (\\%) & 与参照物理等价",
        },
    }[lang]
    rows = []
    for arm in ("task_conditioned", "full_dump"):
        m = bundle["aggregate"][arm]["mean"]
        rows.append(
            f"{labels[arm]} & {f(m['agent.mean_selected_evidence'], 2)} & "
            f"{f(m['agent.mean_materialized_bytes'], 1)} & "
            f"{f(m['agent.context_sufficiency_recall'], 3)} & "
            f"{pct(m['agent.physical_action_confirmation_rate'])} & {_physical_equal_label(lang)}"
        )
    body = "\\\\\n".join(rows) + "\\\\"
    return (
        "%% Generated by scripts/make_agentic_artifacts.py; do not edit.\n"
        "\\begin{tabular}{lrrrrc}\n"
        "\\toprule\n"
        f"{labels['head']}\\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
    )


def table_meta(bundle: dict, table: str) -> dict:
    return {
        "generator": "scripts/make_agentic_artifacts.py",
        "table": table,
        "result_root": str(bundle["root"].relative_to(ROOT)),
        "seeds": bundle["contract"]["seeds"],
        "arms": bundle["contract"]["arms"],
        "source_sha256": {
            k: bundle["sha256"][k]
            for k in ("aggregate.json", "source_manifest.json", "experiment_contract.json")
        },
        "audit_status": bundle["audit"]["status"],
        "all_physical_equivalent": bundle["audit"]["all_physical_equivalent"],
        "claim_ceiling": bundle["contract"]["claim_ceiling"],
    }


def research_block(global_b: dict, local_b: dict, diagnosis_b: dict, baseline_b: dict, source_period_b: dict, robustness_b: dict, transfer_b: dict, attribution_b: dict, model_inputs_b: dict, comm_baseline_b: dict) -> str:
    gm = global_b["aggregate"]["task_conditioned"]["mean"]
    lm = local_b["aggregate"]["task_conditioned"]["mean"]
    lf = local_b["aggregate"]["full_dump"]["mean"]
    dd = diagnosis_b["aggregate"]["paired_delta_mean"]
    bm = baseline_b["aggregate"]["paired_delta_mean"]
    sp = source_period_b["payload"]["rows"]
    mi = {row["context_mode"]: row for row in model_inputs_b["payload"]["rows"]}
    cb = comm_baseline_b["aggregate"]
    return f"""{BEGIN}
### 自动生成结果摘要

> 数字由 `scripts/make_agentic_artifacts.py` 从 `results/agentic/*/aggregate.json` 生成；不要手改本区块。

**Global O2 / 5 seeds / R3 conformance.** `legacy_comply`、`task_conditioned`、`full_dump` 三臂逐 seed physical signature 完全一致，audit=`PASS`。共同 physical mean：TDR `{f(gm['communication.timely_delivery_rate'], 5)}`，collection rate `{f(gm['communication.collection_rate'], 5)}`，p90 delivery latency `{f(gm['communication.delivery_latency_p90_s'], 1)} s`，backup `{f(gm['communication.backup_bytes'], 1)} B`，total consumed energy `{f(gm['communication.total_consumed_wh'], 5)} Wh`。

**Localized O2 / 5 seeds / Context conformance.** task-conditioned 与 FullDump 同样保持逐 seed physical-equivalent，Context sufficiency recall 均为 `1.000`。task-conditioned 平均选择 `{f(lm['agent.mean_selected_evidence'], 2)}` 条 evidence、materialize `{f(lm['agent.mean_materialized_bytes'], 1)}` B；FullDump 分别为 `{f(lf['agent.mean_selected_evidence'], 2)}` 条和 `{f(lf['agent.mean_materialized_bytes'], 1)}` B。两臂共同 physical mean：TDR `{f(lm['communication.timely_delivery_rate'], 5)}`，collection rate `{f(lm['communication.collection_rate'], 5)}`，p90 delivery latency `{f(lm['communication.delivery_latency_p90_s'], 1)} s`。

**Diagnosis-first / 5 seeds / deterministic efficiency baseline.** fixed gateway diagnosis 与直接 deterministic comply 在 5/5 seeds 上 physical signature 完全一致；每个 episode 平均额外产生 `{f(dd['model_requests'], 2)}` 次 model request、`{f(dd['capability_requests'], 2)}` 次 capability request、`{f(dd['percepts'], 2)}` 个 Percept、`{f(dd['context_manifests'], 2)}` 次 Context revision，并额外 materialize `{f(dd['total_materialized_bytes'], 1)}` B。该结果只度量“先做与任务无关的固定诊断”的 runtime 开销。


**O2 baseline matrix / 5 seeds.** 五臂 physical signature 与 replay 均逐 seed 一致。相对 direct deterministic comply，task-conditioned evidence-aware 在 O2 上额外 tool call 为 `{f(bm['evidence_aware']['capability_requests'], 1)}`；diagnosis-first 平均额外 `{f(bm['diagnosis_first']['capability_requests'], 1)}` 次 tool / `{f(bm['diagnosis_first']['model_requests'], 1)}` 次 model；每小时 fixed-order eager 平均额外 `{f(bm['fixed_order_eager']['capability_requests'], 1)}` 次 tool / `{f(bm['fixed_order_eager']['model_requests'], 1)}` 次 model，并额外 materialize `{f(bm['fixed_order_eager']['total_materialized_bytes'], 1)}` B；generic ReAct context 的 tool/model delta 为 `{f(bm['generic_react']['capability_requests'], 1)}/{f(bm['generic_react']['model_requests'], 1)}`，materialized-bytes delta 为 `{f(bm['generic_react']['total_materialized_bytes'], 1)}` B。该对照支持“按任务打开 evidence need 可以避免固定探测开销，并量化 harness cognitive fragments 的 Context 成本”，不支持 LLM 质量提升主张。

**Traditional communication baselines / O2 / 5 seeds.** Local、AoI、EnergyAware、mission-comply 与 backup EDF/maxcov 已在同一个 O2 / `DEFAULT_FULLSIM` 下正式运行。中心策略比较固定 backup chooser=EDF；backup chooser 比较固定 center policy=Local。mean TDR：Local `{f(cb['online']['local_edf']['mean']['timely_delivery_rate'], 5)}`、AoI `{f(cb['online']['aoi_edf']['mean']['timely_delivery_rate'], 5)}`、EnergyAware `{f(cb['online']['energy_aware_edf']['mean']['timely_delivery_rate'], 5)}`、mission-comply `{f(cb['online']['mission_comply_edf']['mean']['timely_delivery_rate'], 5)}`。Local+maxcov 在该坐标上与 Local+EDF 的 TDR 相同，但 backup bytes 为 `{f(cb['online']['local_maxcov']['mean']['backup_bytes'], 1)}` vs `{f(cb['online']['local_edf']['mean']['backup_bytes'], 1)}`。evaluator-only dynamic-energy oracle 未被任一 online arm 突破；primary-only delivery oracle 的 `actual → fixed-send → free-send-with-sample → link-opportunity` 均值为 `{f(cb['oracles']['delivery_primary_only']['mean_actual_routine_delivered'], 1)} → {f(cb['oracles']['delivery_primary_only']['mean_fixed_send_oracle'], 1)} → {f(cb['oracles']['delivery_primary_only']['mean_free_send_require_sample_oracle'], 1)} → {f(cb['oracles']['delivery_primary_only']['mean_link_opportunity_ceiling'], 1)}`。oracle 只作 evaluator reference，不参与 online policy 排名。

**Source-period full-sim gate.** O4 在 NASA POWER 2022/2023/2024 三个独立 source period 上均保持 typed runtime 与 paired deterministic reference physical-equivalent；实际 harvested energy 分别为 `{' / '.join(f(row['total_harvested_wh'], 5) for row in sp)} Wh`，证明 split 已进入物理 simulator，而非只存在 manifest 中。该实验仍是 robustness-coordinate gate，不是跨年方法收益结果。

**Five-axis robustness gate.** `robustness-matrix-v1` 当前包含 `{robustness_b['aggregate']['n_coordinates']}` 个 paired coordinates，覆盖 `{len(robustness_b['aggregate']['axes'])}` 个轴：weather window、backhaul outage、target scope、evidence owner、deployment scale。五轴 activation 均为 `PASS`，所有 coordinate 都与 paired deterministic reference physical-equivalent 且 R0/R1/R2 replay exact。该结果只证明 benchmark 轴真正进入 full simulator/runtime，不构成 robustness 方法收益。

**Source-derived Operational Task transfer / 5 seeds.** `task-transfer-qili-v1` 将 S14 报告的真实监测阶段顺序映射成 external-authority Operational Task，并与 hand-authored O2 共享同一个 `DEFAULT_FULLSIM`、runtime、capability surface、planner 与 scorer。两种 schedule 各自 5/5 paired physical-equivalent 且 replay exact；hand-authored arm 的通信均值逐项复现主 O2。Qili 的等时 4 h phase 压缩和 `3600/300/3600 s` profile 是 A-layer workload transform；跨 schedule 的 TDR/energy 差异属于任务需求差异，不作方法收益比较。

**Attribution protocol infrastructure / 20 frozen R1 turns.** `attribution-matrix-infra-v1` 对同一 O2 frozen trace 注入受控 upstream + planner corruption，并按 Task→EvidenceNeed→Percept→Context→Selection→Order→Arguments 累计修复。完成 Gold Context 后 assembly match rate=`{pct(attribution_b['aggregate']['rows'][4]['assembly_match_rate'])}%`；完成 capability selection 后 tool exact=`{pct(attribution_b['aggregate']['rows'][5]['tool_exact_match_rate'])}%`，但平均 unresolved argument slots=`{f(attribution_b['aggregate']['rows'][5]['mean_unresolved_argument_slots'], 2)}`；直到 Gold Arguments 后 argument grounding 才到 `{pct(attribution_b['aggregate']['rows'][-1]['argument_grounding_accuracy'])}%`。该结果只验证 attribution evaluator 的层级隔离/累计恢复，不是 LLM failure rate。

**Frozen model-context inputs / O2 seed 0.** task-conditioned、FullDump、generic-ReAct 三套输入各冻结 `{mi['task_conditioned']['turns']}` 个 R1 turn，三者均与 paired legacy physical-equivalent 且 R0/R1/R2 replay exact。model-facing protocol mean bytes 分别为 `{f(mi['task_conditioned']['protocol_bytes_mean'], 1)} / {f(mi['full_dump']['protocol_bytes_mean'], 1)} / {f(mi['generic_react']['protocol_bytes_mean'], 1)}`。generic-ReAct 输入完全移除 EvidenceNeed / InvestigationState harness artifacts；该 manifest 只冻结公平模型输入，不包含任何真实模型结果。

这组结果的 claim ceiling 仅为：**同一正确 deterministic policy 下，Operational Task scope 可以减少无关 evidence/context materialization，而不改变物理业务结果。** 它不证明 LLM policy quality 提升。
{END}"""


def results_block(global_b: dict, local_b: dict, diagnosis_b: dict, baseline_b: dict, source_period_b: dict, robustness_b: dict, transfer_b: dict, attribution_b: dict, model_inputs_b: dict, comm_baseline_b: dict) -> str:
    def row(name: str, bundle: dict, cmd: str, note: str) -> str:
        seeds = bundle["contract"]["seeds"]
        seed_text = ",".join(str(x) for x in seeds)
        root = bundle["root"].relative_to(ROOT)
        return (
            f"| `{root}/` | `{cmd}` | `{seed_text}` | "
            f"audit=PASS；{note} |"
        )

    return f"""{BEGIN}
## Agentic Communication 当前自动登记结果

> 本表由 `scripts/make_agentic_artifacts.py` 从实验 contract/audit 自动生成；不要手改本区块。

| 结果目录 | 复现命令 | seeds | 允许支持的结论 |
|---|---|---|---|
{row('global', global_b, 'python3 code/experiments/agentic/run_o2_risk_escalation.py --variant global --seeds 0,1,2,3,4', 'global O2 runtime conformance；两种新 runtime 与 legacy comply 逐 seed physical-equivalent')}
{row('localized', local_b, 'python3 code/experiments/agentic/run_o2_risk_escalation.py --variant localized --seeds 0,1,2,3,4', 'localized O2 Context conformance；task-conditioned 减少无关 materialization，physical outcome 不变')}
{row('diagnosis-first', diagnosis_b, 'python3 code/experiments/agentic/run_o2_diagnosis_baseline.py --seeds 0,1,2,3,4', 'diagnosis-first deterministic efficiency baseline；固定 gateway diagnosis 增加 runtime 开销而 5/5 seeds physical outcome 不变')}
{row('baseline-matrix', baseline_b, 'python3 code/experiments/agentic/run_o2_baseline_matrix.py --seeds 0,1,2,3,4', 'O2 deterministic Agent baseline matrix；evidence-aware / diagnosis-first / fixed-order eager / generic ReAct context 在相同物理结果下比较 runtime/context 开销')}
| `{comm_baseline_b['root'].relative_to(ROOT)}/` | `python3 code/experiments/agentic/run_communication_baseline_matrix.py --seeds 0,1,2,3,4` | `0,1,2,3,4` | audit=PASS；传统 communication baseline matrix；Local/AoI/EnergyAware/mission-comply、EDF/maxcov 与 evaluator-only dynamic/delivery oracle，online/oracle 严格分栏 |
| `{source_period_b['path'].relative_to(ROOT)}` | `python3 code/experiments/agentic/run_source_period_smoke.py --seed 0` | `0` | status=PASS；NASA POWER 2022/2023/2024 source-period full-sim gate，三年 source hash/harvest outcome 分离且 paired physical-equivalent |
| `{robustness_b['root'].relative_to(ROOT)}/` | `python3 code/experiments/agentic/run_robustness_matrix.py` | `{robustness_b['aggregate']['n_coordinates']} coords` | audit=PASS；五轴 robustness infrastructure gate；weather/outage/scope/owner/scale 全部激活，paired physical-equivalent + replay exact |
{row('task-transfer-qili', transfer_b, 'python3 code/experiments/agentic/run_task_transfer_qili.py --seeds 0,1,2,3,4', 'S14 source-derived Operational Task transfer；只替换 task authority/schedule，同一 DEFAULT_FULLSIM/runtime/planner/scorer，paired physical-equivalent + replay exact')}
| `{attribution_b['root'].relative_to(ROOT)}/` | `python3 code/experiments/agentic/run_attribution_matrix_infra.py --turns 20` | `20 frozen R1 turns` | audit=PASS；attribution protocol infrastructure；upstream assembly replacement 与 planner post-hoc replacement 分层累计恢复，不是模型结果 |
| `{model_inputs_b['path'].parent.relative_to(ROOT)}/` | `make agentic-model-inputs` | `seed 0 / 3 contexts` | frozen-input conformance；task-conditioned / FullDump / generic-ReAct 共用 Task/tool/physics，三套 trace physical-equivalent + R0/R1/R2 exact；不包含模型分数 |

正式 O2 结果目录包含 `experiment_contract.json / source_manifest.json / run_manifest.json / per_episode_results.jsonl / runtime_traces/ / aggregate.json / audit.json`；source-period smoke 当前是单文件 infrastructure gate。
{END}"""


def replace_block(text: str, block: str) -> str:
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        raise RuntimeError(f"missing controlled markers {BEGIN} ... {END}")
    return pattern.sub(block, text, count=1)


def _write_or_check(path: Path, expected: str, check: bool, stale: list[str], written: list[str]):
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old == expected:
        return
    rel = str(path.relative_to(ROOT))
    if check:
        stale.append(rel)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(expected, encoding="utf-8")
        written.append(rel)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    global_b = _bundle(GLOBAL)
    local_b = _bundle(LOCAL)
    diagnosis_b = _diagnosis_bundle(DIAGNOSIS)
    baseline_b = _baseline_matrix_bundle(BASELINE_MATRIX)
    source_period_b = _source_period_bundle(SOURCE_PERIOD)
    robustness_b = _robustness_bundle(ROBUSTNESS_MATRIX)
    transfer_b = _task_transfer_bundle(TASK_TRANSFER)
    attribution_b = _attribution_bundle(ATTRIBUTION_INFRA)
    model_inputs_b = _model_context_input_bundle(MODEL_CONTEXT_INPUTS)
    comm_baseline_b = _communication_baseline_bundle(COMM_BASELINE_MATRIX)
    stale: list[str] = []
    written: list[str] = []

    for name, bundle, renderer in (
        ("agentic_o2_global", global_b, render_global_table),
        ("agentic_o2_localized", local_b, render_localized_table),
    ):
        for lang in ("en", "zh"):
            _write_or_check(
                PAPER_GEN / f"table_{name}.{lang}.tex",
                renderer(bundle, lang),
                args.check,
                stale,
                written,
            )
        meta = json.dumps(table_meta(bundle, name), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        _write_or_check(
            PAPER_GEN / f"table_{name}.meta.json", meta, args.check, stale, written
        )

    for lang in ("en", "zh"):
        _write_or_check(
            PAPER_GEN / f"table_agentic_o2_baselines.{lang}.tex",
            render_baseline_table(baseline_b, lang),
            args.check,
            stale,
            written,
        )
        _write_or_check(
            PAPER_GEN / f"table_agentic_source_period.{lang}.tex",
            render_source_period_table(source_period_b, lang),
            args.check,
            stale,
            written,
        )
    _write_or_check(
        PAPER_GEN / "table_agentic_o2_baselines.meta.json",
        json.dumps(
            {
                "generator": "scripts/make_agentic_artifacts.py",
                "result_root": str(baseline_b["root"].relative_to(ROOT)),
                "aggregate_sha256": baseline_b["sha256"]["aggregate.json"],
                "audit_status": baseline_b["audit"]["status"],
                "claim_ceiling": baseline_b["contract"]["claim_ceiling"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        args.check,
        stale,
        written,
    )

    for lang in ("en", "zh"):
        _write_or_check(
            PAPER_GEN / f"table_agentic_task_transfer.{lang}.tex",
            render_task_transfer_table(transfer_b, lang),
            args.check,
            stale,
            written,
        )
    _write_or_check(
        PAPER_GEN / "table_agentic_task_transfer.meta.json",
        json.dumps(
            {
                "generator": "scripts/make_agentic_artifacts.py",
                "result_root": str(transfer_b["root"].relative_to(ROOT)),
                "aggregate_sha256": transfer_b["sha256"]["aggregate.json"],
                "audit_status": transfer_b["audit"]["status"],
                "same_runtime_and_planner": transfer_b["audit"]["same_runtime_and_planner"],
                "claim_ceiling": transfer_b["contract"]["claim_ceiling"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        args.check,
        stale,
        written,
    )
    _write_or_check(
        PAPER_GEN / "table_agentic_source_period.meta.json",
        json.dumps(
            {
                "generator": "scripts/make_agentic_artifacts.py",
                "source": str(source_period_b["path"].relative_to(ROOT)),
                "sha256": source_period_b["sha256"],
                "status": source_period_b["payload"]["status"],
                "claim_ceiling": source_period_b["payload"]["claim_ceiling"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        args.check,
        stale,
        written,
    )

    for lang in ("en", "zh"):
        _write_or_check(
            PAPER_GEN / f"table_agentic_robustness.{lang}.tex",
            render_robustness_table(robustness_b, lang),
            args.check,
            stale,
            written,
        )
    _write_or_check(
        PAPER_GEN / "table_agentic_robustness.meta.json",
        json.dumps(
            {
                "generator": "scripts/make_agentic_artifacts.py",
                "result_root": str(robustness_b["root"].relative_to(ROOT)),
                "aggregate_sha256": robustness_b["sha256"]["aggregate.json"],
                "audit_status": robustness_b["audit"]["status"],
                "axis_activation": robustness_b["audit"]["axis_activation"],
                "claim_ceiling": robustness_b["contract"]["claim_ceiling"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        args.check,
        stale,
        written,
    )

    for lang in ("en", "zh"):
        _write_or_check(
            PAPER_GEN / f"table_agentic_attribution_infra.{lang}.tex",
            render_attribution_table(attribution_b, lang),
            args.check,
            stale,
            written,
        )
    _write_or_check(
        PAPER_GEN / "table_agentic_attribution_infra.meta.json",
        json.dumps(
            {
                "generator": "scripts/make_agentic_artifacts.py",
                "result_root": str(attribution_b["root"].relative_to(ROOT)),
                "aggregate_sha256": attribution_b["sha256"]["aggregate.json"],
                "audit_status": attribution_b["audit"]["status"],
                "claim_ceiling": attribution_b["contract"]["claim_ceiling"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        args.check,
        stale,
        written,
    )

    facts_text, facts_meta = agentic_facts(
        global_b,
        local_b,
        diagnosis_b,
        baseline_b,
        source_period_b,
        robustness_b,
        model_inputs_b,
    )
    _write_or_check(
        PAPER_GEN / "agentic_facts.tex", facts_text, args.check, stale, written
    )
    _write_or_check(
        PAPER_GEN / "agentic_facts.meta.json",
        json.dumps(facts_meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        args.check,
        stale,
        written,
    )

    summary = (
        "# Agentic O2 generated summary\n\n"
        + research_block(global_b, local_b, diagnosis_b, baseline_b, source_period_b, robustness_b, transfer_b, attribution_b, model_inputs_b, comm_baseline_b)
        + "\n"
    )
    _write_or_check(
        RESEARCH_GEN / "agentic_o2_summary.md", summary, args.check, stale, written
    )

    research_expected = replace_block(
        RESEARCH_README.read_text(encoding="utf-8"), research_block(global_b, local_b, diagnosis_b, baseline_b, source_period_b, robustness_b, transfer_b, attribution_b, model_inputs_b, comm_baseline_b)
    )
    _write_or_check(RESEARCH_README, research_expected, args.check, stale, written)

    results_expected = replace_block(
        RESULTS_README.read_text(encoding="utf-8"), results_block(global_b, local_b, diagnosis_b, baseline_b, source_period_b, robustness_b, transfer_b, attribution_b, model_inputs_b, comm_baseline_b)
    )
    _write_or_check(RESULTS_README, results_expected, args.check, stale, written)

    if args.check:
        if stale:
            print("Agentic generated artifacts are stale:")
            for p in stale:
                print(f"  {p}")
            print("Run: python3 scripts/make_agentic_artifacts.py")
            return 1
        print("Agentic generated artifacts match frozen results")
        return 0

    if written:
        print("Generated/updated:")
        for p in written:
            print(f"  {p}")
    else:
        print("Agentic generated artifacts already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
