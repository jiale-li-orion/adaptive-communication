#!/usr/bin/env python3
"""ASC transfer: observation-conditioned obligations with shared opportunities.

This family extends the simple query-budget counterexample with the actual
conflict object used by Layer 2: multiple hard obligations share a finite set of
future communication opportunities plus a bounded backup resource.

At t=0, semantic query H reveals one of K mutually exclusive future branches.
Each branch activates D hard operational reports.  From t=1..D there are only
D-1 terrestrial opportunities and one backup unit.  Therefore every branch is
individually feasible with minimum backup requirement 1.

A static union-reserve representation that combines all K*D possible future
obligations sees the *same* D-1 terrestrial opportunities and backup budget 1,
so its Hall/min-cut deficit is much larger and it falsely rejects QUERY_H.

Branch feasibility certificates are built with the repository's existing
``ConditionalFeasibilityFrontier`` max-flow/min-cut implementation.  The exact
scenario-tree solver independently replays each branch bundle.  No Layer-2
implementation is modified here; this is an adapter-level transfer test for
observation-conditioned obligation activation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from time import perf_counter
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
BENCH = ROOT / "code/evaluation/benchmark"
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from conditional_feasibility_frontier import ConditionalFeasibilityFrontier  # noqa: E402
from multi_evidence_scenario_tree import Bundle, Obligation, World, solve  # noqa: E402


def branch_bundle(branch: int, depth: int) -> Bundle:
    obligations=tuple(
        Obligation(oid=f"b{branch}:g{j}",release_s=1,deadline_s=depth)
        for j in range(depth)
    )
    terr=tuple(range(1,depth))  # D-1 shared terrestrial opportunities
    return Bundle(
        bundle_id=f"asc-branch-{branch}-d{depth}",
        fixed_event_times=tuple(range(1,depth+1)),
        obligations=obligations,
        satellite_slots=(depth,),
        worlds=(World(world_id=f"w{branch}",terrestrial_slots=terr,evidence_values=()),),
        satellite_budget=1,
        queries=(),
    )


def union_bundle(branches:int,depth:int)->Bundle:
    obligations=tuple(
        Obligation(oid=f"b{b}:g{j}",release_s=1,deadline_s=depth)
        for b in range(branches)
        for j in range(depth)
    )
    terr=tuple(range(1,depth))
    return Bundle(
        bundle_id=f"asc-static-union-k{branches}-d{depth}",
        fixed_event_times=tuple(range(1,depth+1)),
        obligations=obligations,
        satellite_slots=(depth,),
        worlds=(World(world_id="union",terrestrial_slots=terr,evidence_values=()),),
        satellite_budget=1,
        queries=(),
    )


def frontier_summary(bundle:Bundle)->dict[str,Any]:
    started=perf_counter(); frontier=ConditionalFeasibilityFrontier(bundle); certs=frontier.snapshot(); wall=perf_counter()-started
    return {
        "certificate_count":len(certs),
        "min_backup_requirement":max((c.min_satellite_budget for c in certs),default=0),
        "certificates":[{
            "world_ids":list(c.world_ids),
            "min_backup":c.min_satellite_budget,
            "conflicts":[{
                "obligations":list(w.obligations),
                "terrestrial_neighbors":list(w.terrestrial_neighbors),
                "terrestrial_capacity":w.terrestrial_capacity,
                "required_backup":w.required_backup,
            } for w in c.conflict_witnesses],
        } for c in certs],
        "wall_s":wall,
    }


def run_cell(branches:int,depth:int)->dict[str,Any]:
    branch_rows=[]; branch_frontier_wall=0.0; branch_exact_memo=0
    for b in range(branches):
        bundle=branch_bundle(b,depth)
        f=frontier_summary(bundle); exact=solve(bundle)
        assert exact["solvable"] is True
        assert f["min_backup_requirement"]<=bundle.satellite_budget
        branch_frontier_wall+=f["wall_s"]; branch_exact_memo+=int(exact["memo_nodes"])
        branch_rows.append({"branch":b,"frontier":f,"exact_solvable":bool(exact["solvable"]),"exact_memo_nodes":int(exact["memo_nodes"])})

    union=union_bundle(branches,depth); uf=frontier_summary(union)
    union_declared=uf["min_backup_requirement"]<=union.satellite_budget
    # Small cells independently confirm the union impossibility with the exact
    # action solver. Large cells use the sound Hall/min-cut U=0 certificate to
    # avoid exponential irrelevant search.
    union_exact=None
    if branches*depth<=16:
        ex=solve(union); union_exact={"solvable":bool(ex["solvable"]),"memo_nodes":int(ex["memo_nodes"])}
        if branches==1:
            assert ex["solvable"] is True
        else:
            assert ex["solvable"] is False

    flow_forward_edges_per_branch=(
        depth                      # source -> obligation
        + depth*max(0,depth-1)     # obligation -> terrestrial opportunity
        + max(0,depth-1)           # opportunity -> sink
    )
    aggregate_flow_forward_edges=branches*flow_forward_edges_per_branch

    return {
        "branches":branches,
        "depth":depth,
        "future_obligation_count_union":branches*depth,
        "shared_terrestrial_opportunities":max(0,depth-1),
        "backup_budget":1,
        "query_h_conditional":{
            "causal_solvable":all(r["exact_solvable"] for r in branch_rows),
            "worst_branch_min_backup":max(r["frontier"]["min_backup_requirement"] for r in branch_rows),
            "branch_frontier_wall_s":branch_frontier_wall,
            "branch_exact_memo_nodes":branch_exact_memo,
            "branch_exact_memo_nodes_per_branch":branch_exact_memo/branches,
            "flow_forward_edges_per_branch":flow_forward_edges_per_branch,
            "aggregate_flow_forward_edges":aggregate_flow_forward_edges,
            "exact_memo_over_flow_edge_proxy":(
                branch_exact_memo/aggregate_flow_forward_edges
                if aggregate_flow_forward_edges else None
            ),
            "branches":branch_rows,
        },
        "static_union":{
            "frontier":uf,
            "declared_feasible":union_declared,
            "exact":union_exact,
            "false_negative_for_query_h":not union_declared,
        },
    }


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--out",type=Path,default=ROOT/"results/transfer/asc-pull-query-shared-opportunity-frontier.json"); args=ap.parse_args()
    cells=[]
    for branches in (1,2,4,8,16,32):
        for depth in (2,4,8):
            row=run_cell(branches,depth)
            if branches==1:
                assert row["static_union"]["declared_feasible"] is True
            else:
                assert row["static_union"]["false_negative_for_query_h"] is True
                assert row["query_h_conditional"]["causal_solvable"] is True
            cells.append(row)
    nontrivial=[r for r in cells if r["branches"]>1]
    payload={
        "stage":"ASC_PULL_QUERY_SHARED_OPPORTUNITY_CONDITIONAL_FRONTIER",
        "axes":{"branches":[1,2,4,8,16,32],"branch_obligations":[2,4,8]},
        "summary":{
            "cell_count":len(cells),
            "nontrivial_cells":len(nontrivial),
            "conditional_branch_solvable_cells":sum(r["query_h_conditional"]["causal_solvable"] for r in nontrivial),
            "static_union_false_negative_cells":sum(r["static_union"]["false_negative_for_query_h"] for r in nontrivial),
            "max_union_min_backup":max(r["static_union"]["frontier"]["min_backup_requirement"] for r in cells),
            "max_branch_min_backup":max(r["query_h_conditional"]["worst_branch_min_backup"] for r in cells),
            "aggregate_branch_exact_memo_nodes":sum(r["query_h_conditional"]["branch_exact_memo_nodes"] for r in cells),
        },
        "cells":cells,
        "claim_boundary":[
            "Branch-conditioned hard obligations are an explicit ASC transfer stress extension, not attributed to the source Pull-Based paper.",
            "Within each observation branch, conflict certificates are produced by the existing repository max-flow/min-cut ConditionalFeasibilityFrontier implementation.",
            "The static-union baseline intentionally represents a common conservative approximation; its false negatives establish the need for observation-conditioned obligation domains, not standalone algorithmic novelty.",
            "Large-union exact search is skipped when the sound Hall/min-cut certificate already proves U=0."
        ],
    }
    assert payload["summary"]["conditional_branch_solvable_cells"]==len(nontrivial)
    assert payload["summary"]["static_union_false_negative_cells"]==len(nontrivial)
    args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"out":str(args.out),**payload["summary"]},sort_keys=True)); return 0


if __name__=="__main__": raise SystemExit(main())
