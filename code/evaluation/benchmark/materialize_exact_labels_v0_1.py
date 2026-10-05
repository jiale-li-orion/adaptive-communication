#!/usr/bin/env python3
"""Materialize exact reference labels for the full compositional universe.

The expensive causal solver is executed once per solver-equivalent dynamic IR,
then projected back to every recipe.  Equivalence excludes recipe/source ids
and includes every field consumed by the current exact solver: obligation
timing, public satellite opportunities/budget, per-world terrestrial service,
and observation-process capabilities.

Outputs are generated artifacts, not BENCHMARK_ADMIT cases.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping
import argparse
import json

from causal_evidence_process_v0_1 import attach_causal_evidence
from dynamic_world_materializer_v0_1 import iter_world_bundles
from exact_reference_oracle_v0_1 import hindsight_bundle_reference, solve_observation_matched


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT = ROOT / "local_research/current/benchmark/generated/exact-labels-v0.1"
SOLVER_VERSION = "T1-exact-reference-oracle-v0.1"


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


def solver_signature_payload(bundle: Mapping[str, Any]) -> dict[str, Any]:
    process = attach_causal_evidence(bundle)
    return {
        "solver_version": SOLVER_VERSION,
        "obligations": [
            {
                "release_s": int(o["release_s"]),
                "deadline_s": int(o["deadline_s"]),
            }
            for o in bundle["obligations"]
        ],
        "satellite_budget_units": int(bundle["public_environment"]["satellite_budget_units"]),
        "satellite_windows": [
            (int(w["start_s"]), int(w["end_s"]), int(w["capacity_units"]))
            for w in bundle["public_environment"]["satellite_windows"]
        ],
        "world_terrestrial_windows": [
            [
                (int(w["start_s"]), int(w["end_s"]), int(w["capacity_units"]))
                for w in world["terrestrial_windows"]
            ]
            for world in bundle["worlds"]
        ],
        "observation_process": {
            "direct_observation": bool(process["direct_observation"]),
            "query_capability_count": len(process["query_capabilities"]),
            "passive_rule_count": len(process["passive_observation_rules"]),
            "probe_rule_count": len(process["normal_send_probe_rules"]),
            "history_contract": process["history_contract"],
            "resource_contract": process["resource_contract"],
        },
    }


def solver_signature(bundle: Mapping[str, Any]) -> str:
    return _canonical_hash(solver_signature_payload(bundle))


def _classify(bundle: Mapping[str, Any], max_memo_nodes: int) -> dict[str, Any]:
    physical = hindsight_bundle_reference(bundle)
    if not physical["all_worlds_solvable"]:
        return {
            "classification": (
                "MIXED_WORLD_SOLVABILITY"
                if physical["any_world_solvable"]
                else "NO_WORLD_SOLVABLE"
            ),
            "physical": {
                "all_worlds_solvable": physical["all_worlds_solvable"],
                "any_world_solvable": physical["any_world_solvable"],
            },
            "full_current": None,
            "exact": None,
            "no_paid_query": None,
        }

    process = attach_causal_evidence(bundle)
    full_current = solve_observation_matched(
        bundle,
        process,
        disable_paid_query=True,
        force_full_current_state=True,
        max_memo_nodes=max_memo_nodes,
    )
    exact = solve_observation_matched(
        bundle, process, disable_paid_query=False, max_memo_nodes=max_memo_nodes
    )
    no_query = solve_observation_matched(
        bundle, process, disable_paid_query=True, max_memo_nodes=max_memo_nodes
    )
    refs = (full_current, exact, no_query)
    if any(x["status"] == "SEARCH_LIMIT" for x in refs):
        cls = "SEARCH_LIMIT"
    elif not full_current["solvable"]:
        cls = "FULL_CURRENT_STATE_INFEASIBLE"
    elif not exact["solvable"]:
        cls = "INFORMATION_INFEASIBLE"
    elif no_query["solvable"]:
        cls = "NO_PAID_QUERY_REQUIRED"
    else:
        cls = "PAID_EVIDENCE_REQUIRED"
    return {
        "classification": cls,
        "physical": {
            "all_worlds_solvable": True,
            "any_world_solvable": True,
        },
        "full_current": {
            "status": full_current["status"],
            "solvable": full_current["solvable"],
            "memo_nodes": full_current["memo_nodes"],
        },
        "exact": {
            "status": exact["status"],
            "solvable": exact["solvable"],
            "memo_nodes": exact["memo_nodes"],
        },
        "no_paid_query": {
            "status": no_query["status"],
            "solvable": no_query["solvable"],
            "memo_nodes": no_query["memo_nodes"],
        },
    }


def _solve_one(args: tuple[str, dict[str, Any], int]) -> tuple[str, dict[str, Any]]:
    signature, bundle, max_memo_nodes = args
    result = _classify(bundle, max_memo_nodes)
    result["signature"] = signature
    result["representative_recipe_id"] = bundle["recipe_id"]
    return signature, result


def _collect_universe() -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], Counter[str]]:
    representatives: dict[str, dict[str, Any]] = {}
    recipes: list[dict[str, Any]] = []
    multiplicity: Counter[str] = Counter()
    for bundle in iter_world_bundles():
        sig = solver_signature(bundle)
        multiplicity[sig] += 1
        old = representatives.get(sig)
        if old is None or str(bundle["recipe_id"]) < str(old["recipe_id"]):
            representatives[sig] = bundle
        recipes.append({
            "recipe_id": bundle["recipe_id"],
            "bundle_id": bundle["bundle_id"],
            "signature": sig,
            "pre_oracle_disposition": bundle["pre_oracle_disposition"],
            "service_process": bundle["public_environment"]["terrestrial_process_class"],
            "evidence_regime": bundle["observation_projection"]["evidence_regime"],
            "overlap_count": len(bundle["obligations"]),
            "recovery_regime": bundle["recovery"]["regime"],
            "geometry_signature_id": bundle["public_environment"]["geometry_signature_id"],
            "task_case_id": bundle["task_case_id"],
        })
    return representatives, recipes, multiplicity


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


def _artifact_ref(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def materialize(
    *,
    out_dir: Path,
    workers: int,
    max_memo_nodes: int,
    resume: bool,
    limit_signatures: int | None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    signature_path = out_dir / "signature-labels.jsonl"
    recipe_path = out_dir / "recipe-labels.jsonl"
    representatives, recipes, multiplicity = _collect_universe()
    completed = _load_completed(signature_path) if resume else {}
    if not resume and signature_path.exists():
        signature_path.unlink()

    todo = sorted(set(representatives) - set(completed))
    if limit_signatures is not None:
        todo = todo[:limit_signatures]

    mode = "a" if resume and signature_path.exists() else "w"
    with signature_path.open(mode, encoding="utf-8", buffering=1) as f:
        if workers <= 1:
            iterator = (_solve_one((sig, representatives[sig], max_memo_nodes)) for sig in todo)
            for sig, row in iterator:
                completed[sig] = row
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        else:
            with ProcessPoolExecutor(max_workers=workers) as ex:
                futures = {
                    ex.submit(_solve_one, (sig, representatives[sig], max_memo_nodes)): sig
                    for sig in todo
                }
                for future in as_completed(futures):
                    sig, row = future.result()
                    completed[sig] = row
                    f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    complete = len(completed) == len(representatives)
    projected = Counter()
    projected_pending = Counter()
    by_service_evidence = Counter()
    if complete:
        with recipe_path.open("w", encoding="utf-8") as f:
            for recipe in recipes:
                label = completed[recipe["signature"]]
                cls = str(label["classification"])
                projected[cls] += 1
                if recipe["pre_oracle_disposition"] == "VALIDITY_PENDING":
                    projected_pending[cls] += 1
                by_service_evidence[(recipe["service_process"], recipe["evidence_regime"], cls)] += 1
                f.write(json.dumps({**recipe, "classification": cls}, ensure_ascii=False, sort_keys=True) + "\n")

    signature_counts = Counter(row["classification"] for row in completed.values())
    signature_digest = sha256()
    for sig in sorted(completed):
        signature_digest.update(sig.encode("ascii"))
        signature_digest.update(b":")
        signature_digest.update(str(completed[sig]["classification"]).encode("ascii"))
        signature_digest.update(b"\n")
    return {
        "schema_version": "0.1",
        "status": "COMPLETE" if complete else "PARTIAL",
        "solver_version": SOLVER_VERSION,
        "bundle_count": len(recipes),
        "unique_solver_signature_count": len(representatives),
        "completed_signature_count": len(completed),
        "projection_multiplicity": {
            "mean": len(recipes) / len(representatives),
            "max": max(multiplicity.values()),
        },
        "signature_classification": dict(sorted(signature_counts.items())),
        "projected_recipe_classification": dict(sorted(projected.items())) if complete else {},
        "projected_validity_pending_classification": dict(sorted(projected_pending.items())) if complete else {},
        "by_service_evidence": {
            f"{a}|{b}|{c}": n for (a, b, c), n in sorted(by_service_evidence.items())
        } if complete else {},
        "signature_label_digest_sha256": signature_digest.hexdigest(),
        "signature_labels_ref": _artifact_ref(signature_path),
        "recipe_labels_ref": _artifact_ref(recipe_path) if complete else None,
        "rules": [
            "Solver-equivalent dynamics are solved once and projected to every recipe with the same exact-solver input.",
            "Equivalence excludes recipe/source identity but includes all dynamic and observation-process fields consumed by the exact solver.",
            "Projected labels remain pre-admission and do not bypass V0-V9 or Q0-Q12."
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-memo-nodes", type=int, default=200_000)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--limit-signatures", type=int)
    ap.add_argument("--manifest", type=Path)
    args = ap.parse_args()
    if args.workers < 1:
        raise ValueError("workers must be >=1")
    manifest = materialize(
        out_dir=args.out_dir,
        workers=args.workers,
        max_memo_nodes=args.max_memo_nodes,
        resume=args.resume,
        limit_signatures=args.limit_signatures,
    )
    text = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
