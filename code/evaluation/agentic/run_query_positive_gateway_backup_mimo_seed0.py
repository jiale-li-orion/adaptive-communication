#!/usr/bin/env python3
"""MiMo seed-0 query-positive gate using the low-memory execution path."""
from __future__ import annotations

import argparse
import gc
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CODE = HERE.parents[1]
for path in (CODE, HERE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from agentic_communication.metrics import metric_delta, physical_signature  # noqa: E402
from agentic_communication.planner import BackendPlannerConsumer, BudgetedPlannerConsumer  # noqa: E402
from query_positive_streaming_audit import audit_query_positive_trace_streaming  # noqa: E402
from run_heldout_qili2024_seed0 import MODELS, _backend, _usage  # noqa: E402
from run_query_positive_gateway_backup_gate import (  # noqa: E402
    QueryPositiveReferenceConsumer,
    _run_policy,
    _trace_audit,
)
from run_query_positive_gateway_backup_model_probe import (  # noqa: E402
    CONTEXT_MODE,
    CONTEXT_VARIANT,
    MAX_CALLS,
    PROTOCOL_REVISION,
    RUNTIME_REVISION,
    SELECTOR_REVISION,
    _query_behavior,
)
from run_r3_model_eval import _planner_behavior_audit  # noqa: E402


MODEL = MODELS[1]
SEED = 0
BASE = ROOT / "results" / "agentic" / "query-positive-gateway-backup-v1"
BASE_MANIFEST = BASE / "model-probe-source-manifest.json"
DETERMINISTIC_GATE = BASE / "deterministic-gate.json"
A10_AUDIT = BASE / "confirmatory-audit.json"
MANIFEST = BASE / "mimo-seed0-source-manifest.json"
OUT = BASE / MODEL["id"] / "seed-000"
SUMMARY = OUT / "summary.json"
TRACE = OUT / "runtime_trace.jsonl"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_and_freeze() -> None:
    base = json.loads(BASE_MANIFEST.read_text(encoding="utf-8"))
    mismatches = []
    for rel, expected in (base.get("files") or {}).items():
        path = ROOT / rel
        actual = _sha(path) if path.is_file() else None
        if actual != expected:
            mismatches.append({"path": rel, "expected": expected, "actual": actual})
    if mismatches:
        raise RuntimeError(
            "query-positive frozen source differs from A10/task018 base: "
            + json.dumps(mismatches, ensure_ascii=False)
        )
    gate = json.loads(DETERMINISTIC_GATE.read_text(encoding="utf-8"))
    if gate.get("status") != "PASS":
        raise RuntimeError("query-positive deterministic gate is not PASS")
    a10 = json.loads(A10_AUDIT.read_text(encoding="utf-8"))
    if a10.get("status") != "PASS":
        raise RuntimeError("A10 DeepSeek confirmatory audit is not PASS")

    payload = {
        "experiment": "query-positive-gateway-backup-v1-mimo-seed0",
        "frozen_at": _now(),
        "base_task018_manifest_sha256": _sha(BASE_MANIFEST),
        "deterministic_gate_sha256": _sha(DETERMINISTIC_GATE),
        "a10_confirmatory_audit_sha256": _sha(A10_AUDIT),
        "base_files": base.get("files") or {},
        "runner": str(Path(__file__).resolve().relative_to(ROOT)),
        "runner_sha256": _sha(Path(__file__).resolve()),
        "streaming_audit": "code/evaluation/agentic/query_positive_streaming_audit.py",
        "streaming_audit_sha256": _sha(HERE / "query_positive_streaming_audit.py"),
        "model": MODEL,
        "protocol_revision": PROTOCOL_REVISION,
        "context_mode": CONTEXT_MODE,
        "context_variant": CONTEXT_VARIANT,
        "selector_revision": SELECTOR_REVISION,
        "runtime_revision": RUNTIME_REVISION,
    }
    if MANIFEST.is_file():
        frozen = json.loads(MANIFEST.read_text(encoding="utf-8"))
        comparable = dict(payload)
        comparable.pop("frozen_at", None)
        frozen_comparable = dict(frozen)
        frozen_comparable.pop("frozen_at", None)
        if frozen_comparable != comparable:
            raise RuntimeError("MiMo query-positive seed0 manifest changed after freeze")
        return
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _deterministic_row() -> dict:
    data = json.loads(DETERMINISTIC_GATE.read_text(encoding="utf-8"))
    return next(row for row in data["rows"] if int(row["seed"]) == SEED)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze-only", action="store_true")
    args = ap.parse_args()
    _verify_and_freeze()
    if args.freeze_only:
        print(f"FROZEN {MANIFEST}")
        return 0
    if SUMMARY.is_file():
        data = json.loads(SUMMARY.read_text(encoding="utf-8"))
        if data.get("status") in {"PASS", "FAIL"}:
            print(f"SKIP existing {data['status']} {SUMMARY}")
            return 0 if data["status"] == "PASS" else 2

    deterministic = _deterministic_row()
    reference, reference_policy, _ = _run_policy(
        seed=SEED,
        consumer=QueryPositiveReferenceConsumer(),
    )
    reference_signature = physical_signature(reference)
    reference_metrics = reference["agentic"]["communication_metrics"]
    reference_query = _trace_audit(reference_policy)
    del reference_policy, reference
    gc.collect()

    backend = _backend(MODEL)
    base_consumer = BackendPlannerConsumer(
        backend,
        consumer_id=f"query-positive:{MODEL['provider']}:{MODEL['id']}",
        provider=MODEL["provider"],
        model=MODEL["id"],
    )
    consumer = BudgetedPlannerConsumer(base_consumer, MAX_CALLS)
    result, policy, inst = _run_policy(seed=SEED, consumer=consumer)

    metrics = result["agentic"]["communication_metrics"]
    control_metrics = deterministic["no_acquisition_control"]
    physical_equal = physical_signature(result) == reference_signature
    behavior = _planner_behavior_audit(policy)
    query_behavior = _query_behavior(policy)
    usage = _usage(policy)
    backup_final = bool(inst.plane.enable_backup)
    OUT.mkdir(parents=True, exist_ok=True)
    policy.trace.write_jsonl(TRACE)

    del policy, result, inst, consumer, base_consumer, backend
    gc.collect()

    replay = audit_query_positive_trace_streaming(TRACE, context_mode=CONTEXT_MODE)
    success = bool(
        replay["passed"]
        and behavior["failed_model_attempts"] == 0
        and behavior["effect_scope_inexact_turns"] == 0
        and query_behavior["covered_all_open_query_capabilities"]
        and query_behavior["backup_effect_count"] == 1
        and backup_final
        and physical_equal
        and metrics["timely_delivery_rate"] > control_metrics["timely_delivery_rate"]
        and metrics["aoi_mean_s"] < control_metrics["aoi_mean_s"]
    )
    summary = {
        "generated_at": _now(),
        "experiment": "query-positive-gateway-backup-v1-mimo-seed0",
        "status": "PASS" if success else "FAIL",
        "config": {
            "model": MODEL["id"],
            "provider": MODEL["provider"],
            "seed": SEED,
            "generation": MODEL["generation"],
            "max_model_calls": MAX_CALLS,
            "model_protocol_revision": PROTOCOL_REVISION,
            "context_mode": CONTEXT_MODE,
            "context_variant": CONTEXT_VARIANT,
            "selector_revision": SELECTOR_REVISION,
            "context_runtime_revision": RUNTIME_REVISION,
        },
        "communication_metrics": metrics,
        "deterministic_reference_metrics": reference_metrics,
        "no_acquisition_control_metrics": control_metrics,
        "delta_vs_no_acquisition": metric_delta(metrics, control_metrics),
        "physical_equal_deterministic_query_positive_reference": physical_equal,
        "deterministic_reference_query_audit": reference_query,
        "model_calls_consumed": behavior["planner_decision_turns"],
        "usage": usage,
        "planner_behavior_audit": behavior,
        "query_behavior_audit": query_behavior,
        "replay_audit": replay,
        "trace": str(TRACE),
        "source_manifest": str(MANIFEST),
        "claim_boundary": (
            "Single MiMo v2.6 Flash seed0 transfer gate on the frozen A10 query-positive coordinate. "
            "A PASS supports one cross-model acquisition witness only; it is not a five-seed MiMo claim."
        ),
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": summary["status"],
                "calls": summary["model_calls_consumed"],
                "failed_attempts": behavior["failed_model_attempts"],
                "effect_exact": behavior["effect_scope_exact_turns"],
                "effect_inexact": behavior["effect_scope_inexact_turns"],
                "queried_capabilities": query_behavior["queried_capabilities"],
                "backup_effect_count": query_behavior["backup_effect_count"],
                "physical_equal_reference": physical_equal,
                "r2_exact": replay["R2"]["exact_assembly_matches"],
                "r2_total": replay["R2"]["contexts"],
                "tdr_delta": summary["delta_vs_no_acquisition"]["timely_delivery_rate"],
                "aoi_delta_s": summary["delta_vs_no_acquisition"]["aoi_mean_s"],
                "tokens": usage["total_tokens"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    print(f"WROTE {SUMMARY}", flush=True)
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())

