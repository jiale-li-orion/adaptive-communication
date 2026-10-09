#!/usr/bin/env python3
"""Frozen statistical analysis for the deterministic Layer-1 paper test.

Consumes only the canonical 960-row table.  Statistical choices are fixed by
PAPER-BASELINE-PROTOCOL: paired bootstrap with 10k resamples / seed 20261009,
Wilson 95% intervals for binary success, and no outlier deletion.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics
import sys
from typing import Any


ROOT=Path(__file__).resolve().parents[3]
COMMON=ROOT/"code/evaluation/common"
if str(COMMON) not in sys.path: sys.path.insert(0,str(COMMON))
from paper_stats import bootstrap_mean_ci_linear, wilson_interval  # noqa: E402
BASE=ROOT/"results/benchmark/layer1-paper-deterministic-test"
ROWS=BASE/"rows.canonical.jsonl"
PROTOCOL=ROOT/"research/benchmark/PAPER-BASELINE-PROTOCOL.json"
OUT=BASE/"statistical-analysis.json"
MD=BASE/"RESULTS-SUMMARY.md"


def load_rows()->list[dict[str,Any]]:
    with ROWS.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def numeric(metrics:dict,key:str):
    v=metrics.get(key)
    return float(v) if isinstance(v,(int,float)) and not isinstance(v,bool) else None


def main()->int:
    protocol=json.loads(PROTOCOL.read_text(encoding="utf-8")); stats=protocol["statistics"]
    resamples=int(stats["paired_bootstrap_resamples"]); boot_seed=int(stats["paired_bootstrap_seed"])
    rows=load_rows(); online=[r for r in rows if r["kind"]=="online_baseline"]; oracles=[r for r in rows if r["kind"]=="evaluator_only_oracle"]
    assert len(rows)==960 and len(online)==750 and len(oracles)==210

    grouped=defaultdict(list); by_coord={}
    for row in online:
        grouped[(row["task_template"],row["baseline_id"])].append(row)
        by_coord[(row["coordinate_id"],row["baseline_id"])]=row

    metric_keys=("timely_delivery_rate","collection_rate","node_survival_rate","total_consumed_wh","aoi_mean_s","backup_packets","commands_sent")
    groups={}
    for (task,baseline),items in sorted(grouped.items()):
        vals={key:[numeric(r["communication_metrics"],key) for r in items] for key in metric_keys}
        vals={k:[x for x in xs if x is not None] for k,xs in vals.items()}
        full=sum(
            int(r["communication_metrics"]["missing_collection"]==0 and r["communication_metrics"]["missing_delivery"]==0)
            for r in items
        )
        group={
            "n":len(items),
            "metrics":{
                key:{"mean":statistics.fmean(xs),"median":statistics.median(xs),"std":statistics.stdev(xs) if len(xs)>1 else 0.0}
                for key,xs in vals.items() if xs
            },
            "routine_full_success":wilson_interval(full,len(items)),
            "failure_taxonomy":dict(sorted(Counter(reason for r in items for reason in r.get("failure_reasons",[])).items())),
        }
        if baseline!="comm.local_policy":
            local=[]; paired=[]
            for r in items:
                ref=by_coord.get((r["coordinate_id"],"comm.local_policy"))
                if ref is not None: local.append(ref); paired.append((r,ref))
            group["paired_vs_local"]={}
            for idx,key in enumerate(("timely_delivery_rate","collection_rate","node_survival_rate","total_consumed_wh")):
                deltas=[]
                for a,b in paired:
                    av=numeric(a["communication_metrics"],key); bv=numeric(b["communication_metrics"],key)
                    if av is not None and bv is not None: deltas.append(av-bv)
                group["paired_vs_local"][key]=bootstrap_mean_ci_linear(deltas,seed=boot_seed+idx,resamples=resamples)
        groups[f"{task}/{baseline}"]=group

    best={}
    for task in sorted({r["task_template"] for r in online}):
        candidates=[]
        for key,g in groups.items():
            if not key.startswith(task+"/"): continue
            tdr=g["metrics"]["timely_delivery_rate"]["mean"]
            surv=g["metrics"].get("node_survival_rate",{}).get("mean")
            candidates.append((tdr, surv if surv is not None else -1,key.split("/",1)[1]))
        best[task]={"best_mean_tdr":max(candidates)[0],"best_baselines":[b for t,s,b in candidates if abs(t-max(candidates)[0])<1e-12]}

    oracle_summary=defaultdict(list)
    for row in oracles:
        oracle_summary[(row["task_template"],row["oracle_id"])].append(row["value"])
    oracle_out={}
    for (task,oid),items in sorted(oracle_summary.items()):
        if oid=="oracle.dynamic_energy":
            xs=[float(x["total_oracle"]) for x in items]
            oracle_out[f"{task}/{oid}"]={"n":len(xs),"mean_total_oracle":statistics.fmean(xs),"min":min(xs),"max":max(xs)}
        else:
            oracle_out[f"{task}/{oid}"]={
                "n":len(items),
                "mean_actual_primary_only":statistics.fmean(float(x["actual_primary_only_routine_delivered"]) for x in items),
                "mean_fixed_send_oracle":statistics.fmean(float(x["fixed_send_oracle"]) for x in items),
                "mean_free_send_require_sample":statistics.fmean(float(x["free_send_require_sample_oracle"]) for x in items),
                "mean_link_opportunity_ceiling":statistics.fmean(float(x["link_opportunity_ceiling"]) for x in items),
                "all_upper_bound_order_valid":all(x["upper_bound_order_valid"] for x in items),
            }

    payload={
        "stage":"LAYER1_PAPER_DETERMINISTIC_STATISTICAL_ANALYSIS",
        "rows_ref":"results/benchmark/layer1-paper-deterministic-test/rows.canonical.jsonl",
        "statistics_contract":{"paired_bootstrap_resamples":resamples,"paired_bootstrap_seed":boot_seed,"binary_interval":"Wilson 95%","outlier_deletion":False},
        "groups":groups,
        "best_by_task":best,
        "oracles":oracle_out,
        "checks":{
            "canonical_rows_960":len(rows)==960,
            "online_rows_750":len(online)==750,
            "oracle_rows_210":len(oracles)==210,
            "all_online_groups_n30":all(g["n"]==30 for g in groups.values()),
            "all_primary_delivery_oracle_orders_valid":all(v.get("all_upper_bound_order_valid",True) for v in oracle_out.values()),
        },
        "claim_boundary":["Best-by-task uses mean TDR only as a descriptive summary; energy/survival trade-offs remain separately reported.","Paired confidence intervals compare only identical frozen coordinates against comm.local_policy.","Primary-only delivery oracle diagnostics are not full-system upper bounds and are never included in online rankings."],
    }
    assert all(payload["checks"].values()),payload["checks"]
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")

    lines=["# Layer 1 Deterministic Test Results","",f"Frozen test: **150 coordinates / 750 online rows / 210 oracle diagnostics**. Paired bootstrap: {resamples:,} resamples; binary intervals: Wilson 95%.","","| Task | Baseline | Mean TDR | Δ vs local [95% CI] | Full success | Survival | Energy Wh |","|---|---|---:|---:|---:|---:|---:|"]
    for key,g in groups.items():
        task,baseline=key.split("/",1); tdr=g["metrics"]["timely_delivery_rate"]["mean"]; surv=g["metrics"].get("node_survival_rate",{}).get("mean"); energy=g["metrics"].get("total_consumed_wh",{}).get("mean"); fs=g["routine_full_success"]
        if baseline=="comm.local_policy": delta="—"
        else:
            ci=g["paired_vs_local"]["timely_delivery_rate"]; delta=f"{ci['mean']:+.3f} [{ci['lo']:+.3f},{ci['hi']:+.3f}]"
        lines.append(f"| {task} | `{baseline}` | {tdr:.3f} | {delta} | {fs['success']}/{fs['n']} | {surv:.3f} | {energy:.3f} |")
    lines += ["","## Boundary notes","","- O3 is a saturation/control result if multiple ordinary baselines remain statistically indistinguishable; do not manufacture hardness.","- O4 must be read as a TDR–survival–energy trade-off, not a single-score leaderboard.","- O6 is the strongest current interactive benchmark surface; no Future-Choice Stress claim is implied by these deterministic results.","- Evaluator-only oracles are diagnostic and excluded from online ranking."]
    MD.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"out":str(OUT),"summary":str(MD),"best_by_task":best,**payload["checks"]},sort_keys=True)); return 0


if __name__=="__main__": raise SystemExit(main())
