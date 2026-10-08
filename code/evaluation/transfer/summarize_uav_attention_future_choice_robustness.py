#!/usr/bin/env python3
"""Compact the 200/1000-seed UAV transfer robustness runs.

Raw 1000-seed episode rows stay under ``local_research/`` to avoid bloating the
tracked repository.  The compact artifact records their hashes, exact rerun
commands and all paper-relevant paired statistics.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXACT_200 = ROOT / "results/transfer/uav-attention-continuation-shield-n5-200.json"
LU_200 = ROOT / "results/transfer/uav-attention-future-choice-lu-n5-200.json"
EXACT_1000 = ROOT / "local_research/current/transfer/raw/uav-attention-continuation-shield-n5-1000seeds.json"
LU_1000 = ROOT / "local_research/current/transfer/raw/uav-attention-future-choice-lu-n5-1000.json"
OUT = ROOT / "results/transfer/uav-attention-future-choice-robustness-summary.json"


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _paired_exact(doc):
    return {
        name: {
            key: row[key]
            for key in (
                "hard_feasible_seed_count",
                "zero_tardiness_native",
                "zero_tardiness_shielded",
                "completed_native",
                "completed_shielded",
                "infeasible_native",
                "infeasible_shielded",
                "mean_tardiness_delta_shield_minus_native",
                "mean_energy_delta_shield_minus_native",
                "seeds_harmed_zero_tardiness",
            )
        }
        for name, row in doc["paired_hard_feasible"].items()
    }


def _paired_lu(doc):
    out = {}
    for name, row in doc["paired_hard_feasible"].items():
        exact = int(row["exact_mask_new_states"])
        fallback = int(row["exact_fallback_new_states"])
        lower = int(row["lower_search_expanded"])
        out[name] = {
            **row,
            "exact_fallback_state_ratio_over_exact_mask": fallback / exact if exact else None,
            "total_search_proxy_ratio_over_exact_mask": (fallback + lower) / exact if exact else None,
        }
    return out


def main() -> int:
    exact200, lu200, exact1000, lu1000 = map(_load, (EXACT_200, LU_200, EXACT_1000, LU_1000))
    p_exact200 = _paired_exact(exact200)
    p_exact1000 = _paired_exact(exact1000)
    p_lu200 = _paired_lu(lu200)
    p_lu1000 = _paired_lu(lu1000)

    # The L/U method must reproduce the exact-shield task quality on the
    # hard-feasible cohort at both scales.
    checks = {
        "lu_200_zero_tardiness_matches_exact_shield": all(
            p_lu200[name]["zero_tardiness"] == p_exact200[name]["zero_tardiness_shielded"]
            for name in p_lu200
        ),
        "lu_1000_zero_tardiness_matches_exact_shield": all(
            p_lu1000[name]["zero_tardiness"] == p_exact1000[name]["zero_tardiness_shielded"]
            for name in p_lu1000
        ),
        "lu_200_frontier_exact_match": lu200["correctness"]["frontier_mismatch"] == 0,
        "lu_1000_frontier_exact_match": lu1000["correctness"]["frontier_mismatch"] == 0,
        "exact_shield_no_zero_tardiness_harm_1000": all(
            not row["seeds_harmed_zero_tardiness"] for row in p_exact1000.values()
        ),
        "lu_exact_fallback_uses_fewer_states_than_exact_mask_1000": all(
            row["exact_fallback_new_states"] < row["exact_mask_new_states"]
            for row in p_lu1000.values()
        ),
    }
    assert all(checks.values()), checks

    payload = {
        "stage": "UAV_ATTENTION_FUTURE_CHOICE_ROBUSTNESS_SUMMARY",
        "checks": checks,
        "exact_shield_200": p_exact200,
        "lu_frontier_200": p_lu200,
        "exact_shield_1000": p_exact1000,
        "lu_frontier_1000": p_lu1000,
        "correctness": {
            "lu_200_reached_frontier_checks": lu200["correctness"]["reached_frontier_match_checks"],
            "lu_1000_reached_frontier_checks": lu1000["correctness"]["reached_frontier_match_checks"],
        },
        "raw_run_hashes": {
            "exact_200": _sha(EXACT_200),
            "lu_200": _sha(LU_200),
            "exact_1000_local": _sha(EXACT_1000),
            "lu_1000_local": _sha(LU_1000),
        },
        "rerun_commands": {
            "exact_1000": "OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 code/evaluation/transfer/run_uav_attention_continuation_shield.py --seeds 1000 --out <path>",
            "lu_1000": "OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 code/evaluation/transfer/run_uav_attention_future_choice_lu.py --seeds 1000 --lower-search-limit 24 --out <path>",
        },
        "claim_boundary": [
            "1000-seed raw rows are reproducible local artifacts and are not tracked to avoid repository bloat; this summary records their hashes and rerun commands.",
            "Paired task-quality claims use only initial hard-feasible episodes: 18/200 and 107/1000.",
            "Exact fallback state count and bounded-lower-search expansion count are separate work units; their sum is reported only as a search-work proxy, not wall-time equivalence.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), **checks}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
