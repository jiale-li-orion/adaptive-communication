#!/usr/bin/env python3
"""Dynamic observation / certificate-reuse audit for the ASC transfer.

K=2^L hidden branches are distinguished by L sequential semantic query bits.
Each branch owns a fixed D-obligation shared-opportunity problem from
``asc_pull_query_shared_opportunity_frontier``.  Query observations only narrow
which branch is active; they do not change that branch's opportunity/resource
graph.

Two correct planners are compared over the *entire observation tree*:

1. fresh branch-aware flow: after every observation node, rebuild the conflict
   frontier for every branch still in that support;
2. persistent conditional frontier: build one certificate per branch at the
   root, then reuse those certificates while observations only narrow support.

Because all mutually-exclusive query outcomes must be considered during
non-anticipative planning, each query level contains K total branch instances
across its nodes.  Fresh rebuilding therefore repeats the same structural work
at every level; persistent domains do not.

This adapter uses the repository's existing max-flow/min-cut
``ConditionalFeasibilityFrontier`` for every actual certificate build.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from time import perf_counter


ROOT=Path(__file__).resolve().parents[3]
TRANSFER=ROOT/"code/evaluation/transfer"
BENCH=ROOT/"code/evaluation/benchmark"
for p in (TRANSFER,BENCH):
    if str(p) not in sys.path: sys.path.insert(0,str(p))

from asc_pull_query_shared_opportunity_frontier import branch_bundle  # noqa: E402
from conditional_feasibility_frontier import ConditionalFeasibilityFrontier  # noqa: E402


def bits(branch:int,levels:int)->tuple[int,...]:
    return tuple((branch>>(levels-1-i))&1 for i in range(levels))


def build_one(branch:int,depth:int):
    started=perf_counter(); f=ConditionalFeasibilityFrontier(branch_bundle(branch,depth)); certs=f.snapshot(); wall=perf_counter()-started
    assert certs and max(c.min_satellite_budget for c in certs)==1
    return certs,wall


def supports_at_level(branches:int,levels:int,level:int)->list[tuple[int,...]]:
    """Supports after ``level`` revealed bits; level 0 is the root support."""
    groups={}
    for b in range(branches):
        prefix=bits(b,levels)[:level]
        groups.setdefault(prefix,[]).append(b)
    return [tuple(v) for _k,v in sorted(groups.items())]


def run_cell(levels:int,depth:int)->dict:
    branches=2**levels

    # Persistent: exactly one real frontier construction per branch.
    persistent={}; p_wall=0.0
    for b in range(branches):
        certs,wall=build_one(b,depth); persistent[b]=certs; p_wall+=wall

    # Every support at every observation level must be representable by simple
    # selection of already-built branch domains.
    reuse_checks=0
    for level in range(levels+1):
        for support in supports_at_level(branches,levels,level):
            for b in support:
                certs=persistent[b]
                assert max(c.min_satellite_budget for c in certs)==1
                reuse_checks+=1

    # Fresh baseline: root build plus a complete rebuild after every query
    # observation node. Across each level the active-branch cardinalities sum K.
    fresh_builds=0; fresh_wall=0.0
    for level in range(levels+1):
        for support in supports_at_level(branches,levels,level):
            for b in support:
                certs,wall=build_one(b,depth); fresh_wall+=wall; fresh_builds+=1
                # Equality against persistent domain is semantic, not ID-based.
                assert max(c.min_satellite_budget for c in certs)==max(c.min_satellite_budget for c in persistent[b])

    # Event-local invalidation control: after all bits reveal one branch, a
    # backup-budget commit 1->0 crosses only that active branch's certificate
    # domain. Inactive mutually-exclusive branch domains need not be rebuilt.
    realized=branches-1
    active_cert_count=len(persistent[realized])
    invalidated=sum(not c.valid_for_budget(0) for c in persistent[realized])
    assert invalidated==active_cert_count

    return {
        "levels":levels,
        "branches":branches,
        "depth":depth,
        "persistent":{
            "frontier_builds":branches,
            "wall_s":p_wall,
            "reuse_checks_over_full_observation_tree":reuse_checks,
            "post_leaf_budget_commit_invalidated_certificates":invalidated,
            "post_leaf_budget_commit_untouched_inactive_branches":branches-1,
        },
        "fresh":{
            "frontier_builds":fresh_builds,
            "wall_s":fresh_wall,
        },
        "reuse":{
            "build_ratio_persistent_over_fresh":branches/fresh_builds,
            "saved_frontier_builds":fresh_builds-branches,
            "theoretical_ratio":1/(levels+1),
        },
    }


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--depth",type=int,default=8); ap.add_argument("--out",type=Path,default=ROOT/"results/transfer/asc-pull-query-dynamic-frontier-reuse.json"); args=ap.parse_args()
    rows=[run_cell(level,args.depth) for level in (1,2,3,4,5)]
    for row in rows:
        assert abs(row["reuse"]["build_ratio_persistent_over_fresh"]-row["reuse"]["theoretical_ratio"])<1e-12
    payload={
        "stage":"ASC_PULL_QUERY_DYNAMIC_CONDITIONAL_FRONTIER_REUSE",
        "depth":args.depth,
        "rows":rows,
        "summary":{
            "max_branches":max(r["branches"] for r in rows),
            "max_query_levels":max(r["levels"] for r in rows),
            "max_fresh_frontier_builds":max(r["fresh"]["frontier_builds"] for r in rows),
            "max_persistent_frontier_builds":max(r["persistent"]["frontier_builds"] for r in rows),
            "max_saved_frontier_builds":max(r["reuse"]["saved_frontier_builds"] for r in rows),
            "best_persistent_over_fresh_build_ratio":min(r["reuse"]["build_ratio_persistent_over_fresh"] for r in rows),
        },
        "claim_boundary":[
            "This audit isolates observation-only support narrowing: branch opportunity/resource graphs are intentionally unchanged so certificate reuse is provably safe.",
            "Frontier-build count is a deterministic structural-work metric; wall-time is reported but not used as a theorem because each flow instance is tiny.",
            "The next stronger gate must combine observation narrowing with resource/time events that invalidate only a subset of conflict components, rather than all branch certificates."
        ],
    }
    args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"out":str(args.out),**payload["summary"]},sort_keys=True)); return 0


if __name__=="__main__": raise SystemExit(main())
