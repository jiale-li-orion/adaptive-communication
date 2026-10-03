#!/usr/bin/env python3
"""Low-memory single-seed live-model runner for query-positive confirmation.

Each invocation runs exactly one seed and exits.  The deterministic reference is
released before the live-model episode.  After the model trace is written, the
large in-memory policy trace is released before streaming R0/R2 audit.
"""
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
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from agentic_communication.metrics import metric_delta, physical_signature  # noqa: E402
from agentic_communication.planner import BackendPlannerConsumer, BudgetedPlannerConsumer  # noqa: E402
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
    MODEL,
    PROTOCOL_REVISION,
    RUNTIME_REVISION,
    SELECTOR_REVISION,
    _query_behavior,
)
from run_r3_model_eval import _planner_behavior_audit  # noqa: E402
from query_positive_streaming_audit import audit_query_positive_trace_streaming  # noqa: E402


BASE = ROOT / "results" / "agentic" / "query-positive-gateway-backup-v1"
BASE_MANIFEST = BASE / "model-probe-source-manifest.json"
DETERMINISTIC_GATE = BASE / "deterministic-gate.json"
CONFIRMATORY_MANIFEST = BASE / "confirmatory-safe-source-manifest.json"
SAFE_RUNNER = Path(__file__).resolve()


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
            "query-positive frozen source differs from task-018 source: "
            + json.dumps(mismatches, ensure_ascii=False)
        )
    gate = json.loads(DETERMINISTIC_GATE.read_text(encoding="utf-8"))
    if gate.get("status") != "PASS":
        raise RuntimeError("query-positive deterministic gate is not PASS")

    payload = {
        "experiment": "query-positive-gateway-backup-v1-confirmatory-safe",
        "frozen_at": _now(),
        "base_task018_manifest_sha256": _sha(BASE_MANIFEST),
        "deterministic_gate_sha256": _sha(DETERMINISTIC_GATE),
        "base_files": base.get("files") or {},
        "safe_runner": str(SAFE_RUNNER.relative_to(ROOT)),
        "safe_runner_sha256": _sha(SAFE_RUNNER),
        "streaming_audit": "code/experiments/agentic/query_positive_streaming_audit.py",
        "streaming_audit_sha256": _sha(HERE / "query_positive_streaming_audit.py"),
        "model": MODEL["id"],
        "provider": MODEL["provider"],
        "protocol_revision": PROTOCOL_REVISION,
        "context_mode": CONTEXT_MODE,
        "context_variant": CONTEXT_VARIANT,
        "selector_revision": SELECTOR_REVISION,
        "runtime_revision": RUNTIME_REVISION,
    }
    if CONFIRMATORY_MANIFEST.is_file():
        frozen = json.loads(CONFIRMATORY_MANIFEST.read_text(encoding="utf-8"))
        comparable = dict(payload)
        comparable.pop("frozen_at", None)
        frozen_comparable = dict(frozen)
        frozen_comparable.pop("frozen_at", None)
        if frozen_comparable != comparable:
            raise RuntimeError("query-positive safe confirmatory manifest changed after freeze")
        return
    CONFIRMATORY_MANIFEST.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _deterministic_row(seed: int) -> dict:
    data = json.loads(DETERMINISTIC_GATE.read_text(encoding="utf-8"))
    row = next((row for row in data.get("rows") or [] if int(row.get("seed", -1)) == seed), None)
    if row is None:
        raise RuntimeError(f"deterministic query-positive seed {seed} is missing")
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--freeze-only", action="store_true")
    args = ap.parse_args()
    if args.seed not in {1, 2, 3, 4}:
        raise SystemExit("safe confirmatory runner is frozen for seeds 1..4; seed0 is recovered task 018")
    _verify_and_freeze()
    if args.freeze_only:
        print(f"FROZEN {CONFIRMATORY_MANIFEST}")
        return 0

    seed = args.seed
    out = BASE / MODEL["id"] / f"seed-{seed:03d}"
    summary_path = out / "summary.json"
    trace_path = out / "runtime_trace.jsonl"
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("status") == "PASS":
            print(f"SKIP existing PASS {summary_path}")
            return 0
        raise RuntimeError(f"existing non-PASS summary requires ChatGPT judgment: {summary_path}")

    deterministic = _deterministic_row(seed)

    # Reference first; retain only compact evaluator products before freeing its
    # very large in-memory RuntimeTrace.
    reference, reference_policy, _ = _run_policy(
        seed=seed,
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
    result, policy, inst = _run_policy(seed=seed, consumer=consumer)

    metrics = result["agentic"]["communication_metrics"]
    control_metrics = deterministic["no_acquisition_control"]
    physical_equal = physical_signature(result) == reference_signature
    behavior = _planner_behavior_audit(policy)
    query_behavior = _query_behavior(policy)
    usage = _usage(policy)
    backup_final = bool(inst.plane.enable_backup)
    out.mkdir(parents=True, exist_ok=True)
    policy.trace.write_jsonl(trace_path)

    # Drop the 180MB-class in-memory trace before replaying the file.
    del policy, result, inst, consumer, base_consumer, backend
    gc.collect()

    replay = audit_query_positive_trace_streaming(trace_path, context_mode=CONTEXT_MODE)
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
        "experiment": "query-positive-gateway-backup-v1-confirmatory-safe",
        "status": "PASS" if success else "FAIL",
        "config": {
            "model": MODEL["id"],
            "provider": MODEL["provider"],
            "seed": seed,
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
        "trace": str(trace_path),
        "source_manifest": str(CONFIRMATORY_MANIFEST),
        "failure_safety": (
            "single-seed process; deterministic reference trace released before live model; live policy "
            "trace released before streaming R0/R2 audit"
        ),
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "seed": seed,
                "status": summary["status"],
                "model_calls": summary["model_calls_consumed"],
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
    print(f"WROTE {summary_path}", flush=True)
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())

