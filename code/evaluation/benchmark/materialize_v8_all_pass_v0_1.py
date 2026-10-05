#!/usr/bin/env python3
"""Placement-preserving V8 ladder over every V0-V7-passing solver signature."""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from materialize_exact_labels_v0_1 import _collect_universe
from ordinary_baselines_compositional_v0_1 import audit_bundle
from v8_policy_baselines_v0_1 import (
    solve_always_query_then_plan,
    solve_depth_k,
    solve_depth_k_flow_terminal,
    solve_fixed_query_schedule,
    solve_latest_feasible_send,
    solve_least_slack,
    solve_myopic_flow_voi,
    solve_receding_horizon,
    solve_shallow_rule,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
V0V7_SIG = ROOT / "local_research/current/benchmark/generated/v0-v7-full-v0.1/signature-validity.jsonl"
DEFAULT_OUT = ROOT / "local_research/current/benchmark/generated/v8-all-pass-v0.1"


def _load_pass_labels() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for line in V0V7_SIG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["v0_v7_disposition"] == "V0_V7_PASS":
            out[str(row["signature"])] = row
    return out


def _solve_one(args: tuple[str, dict[str, Any], dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    sig, bundle, vlabel = args
    ordinary = audit_bundle(bundle)
    winners = sorted(
        name
        for name, row in ordinary.items()
        if row.get("legal")
        and row.get("robust_success") is True
        and row.get("comparison_role") == "SAME_INFORMATION_SHORTCUT"
    )
    stage = "ORDINARY_FIRST_LAYER"

    if not winners:
        cheap = {
            "shallow_rule_combiner": solve_shallow_rule(bundle),
            "least_slack": solve_least_slack(bundle),
            "always_query_then_plan": solve_always_query_then_plan(bundle),
            "latest_feasible_send": solve_latest_feasible_send(bundle),
            "myopic_flow_voi": solve_myopic_flow_voi(bundle),
        }
        winners = sorted(name for name, row in cheap.items() if row["solvable"])
        stage = "CHEAP_POLICY_RULE"

    if not winners:
        finite = {
            "true_depth_1_belief": solve_depth_k(bundle, depth=1),
            "true_depth_2_belief": solve_depth_k(bundle, depth=2),
            "receding_horizon_3": solve_receding_horizon(bundle, horizon_decisions=3),
        }
        winners = sorted(name for name, row in finite.items() if row["solvable"])
        stage = "FINITE_HORIZON"

    if not winners:
        flow = {
            f"depth_{k}_flow_terminal": solve_depth_k_flow_terminal(bundle, depth=k)
            for k in (1, 2, 3, 4)
        }
        winners = sorted(name for name, row in flow.items() if row["solvable"])
        stage = "FLOW_TERMINAL_HORIZON"

    if not winners:
        for k in (4, 5, 6):
            out = solve_receding_horizon(bundle, horizon_decisions=k)
            if out["solvable"]:
                winners = [f"receding_horizon_{k}"]
                stage = "DEEP_HORIZON"
                break

    if not winners:
        for k in (5, 6):
            out = solve_depth_k_flow_terminal(bundle, depth=k)
            if out["solvable"]:
                winners = [f"depth_{k}_flow_terminal"]
                stage = "DEEP_FLOW_TERMINAL"
                break

    if not winners:
        fixed = []
        for mode in ("FIRST_RELEASE", "EVERY_RELEASE", "SATELLITE_START", "EVERY_SECOND_EVENT"):
            out = solve_fixed_query_schedule(bundle, mode=mode)
            if out["solvable"]:
                fixed.append(out["baseline"])
        winners = sorted(fixed)
        stage = "FIXED_QUERY_TAIL"

    if not winners:
        stage = "SURVIVES_V8_LADDER_V0_1"

    return sig, {
        "signature": sig,
        "representative_recipe_id": bundle["recipe_id"],
        "exact_classification": vlabel["exact_classification"],
        "service_process": bundle["public_environment"]["terrestrial_process_class"],
        "evidence_regime": bundle["observation_projection"]["evidence_regime"],
        "overlap_count": len(bundle["obligations"]),
        "recovery_regime": bundle["recovery"]["regime"],
        "v8_disposition": stage,
        "winning_baselines": winners,
    }


def _load_completed(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        out[str(row["signature"])] = row
    return out


def materialize(*, out_dir: Path, workers: int, resume: bool) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "signature-v8.jsonl"
    labels = _load_pass_labels()
    representatives, _recipes, multiplicity = _collect_universe()
    wanted = set(labels)
    if not wanted <= set(representatives):
        raise RuntimeError(f"missing V0-V7 pass signatures from generator universe: {len(wanted - set(representatives))}")

    completed = _load_completed(path) if resume else {}
    if not resume and path.exists():
        path.unlink()
    todo = sorted(wanted - set(completed))
    mode = "a" if resume and path.exists() else "w"
    with path.open(mode, encoding="utf-8", buffering=1) as f:
        if workers <= 1:
            for sig in todo:
                _, row = _solve_one((sig, representatives[sig], labels[sig]))
                completed[sig] = row
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        else:
            with ProcessPoolExecutor(max_workers=workers) as ex:
                futures = {
                    ex.submit(_solve_one, (sig, representatives[sig], labels[sig])): sig
                    for sig in todo
                }
                for future in as_completed(futures):
                    sig, row = future.result()
                    completed[sig] = row
                    f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    complete = len(completed) == len(wanted)
    disposition = Counter()
    coverage = Counter()
    by_exact = Counter()
    survivors: list[str] = []
    projected_survivor_recipes = 0
    for sig, row in completed.items():
        disposition[row["v8_disposition"]] += 1
        by_exact[(row["exact_classification"], row["v8_disposition"])] += 1
        for winner in row["winning_baselines"]:
            coverage[winner] += 1
        if row["v8_disposition"] == "SURVIVES_V8_LADDER_V0_1":
            survivors.append(sig)
            projected_survivor_recipes += multiplicity[sig]

    digest = sha256()
    for sig in sorted(completed):
        digest.update(sig.encode("ascii"))
        digest.update(b":")
        digest.update(str(completed[sig]["v8_disposition"]).encode("ascii"))
        digest.update(b"\n")
    return {
        "schema_version": "0.1",
        "status": "COMPLETE" if complete else "PARTIAL",
        "input_v0_v7_pass_signature_count": len(wanted),
        "completed_signature_count": len(completed),
        "disposition": dict(sorted(disposition.items())),
        "baseline_coverage": dict(sorted(coverage.items())),
        "by_exact_classification": {
            f"{a}|{b}": n for (a, b), n in sorted(by_exact.items())
        },
        "survivor_signature_count": len(survivors),
        "projected_survivor_recipe_count": projected_survivor_recipes,
        "survivor_signatures": sorted(survivors),
        "v8_digest_sha256": digest.hexdigest(),
        "signature_labels_ref": str(path.relative_to(ROOT)),
        "release_status": "NOT_BENCHMARK_ADMIT",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--manifest", type=Path)
    args = ap.parse_args()
    manifest = materialize(out_dir=args.out_dir, workers=args.workers, resume=args.resume)
    text = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
