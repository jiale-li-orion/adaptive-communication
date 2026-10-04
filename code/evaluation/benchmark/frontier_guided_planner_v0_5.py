#!/usr/bin/env python3
"""Frontier-guided exact planner for v0.5.

The frontier is used only as a conservative upper-bound precheck.  If the
optimistic remaining-feasibility diagnostic proves a world impossible, the
prefix is pruned.  Otherwise control falls back to the unchanged exact
non-anticipative solver.  No heuristic score may delete an unresolved action.
"""
from __future__ import annotations

from dynamic_scenario_tree_v0_5 import Bundle,LocalState,solve
from dynamic_feasibility_frontier_v0_5 import _world_certificate


def frontier_prefix_upper_bound(bundle:Bundle,t:int,states:dict[str,LocalState]) -> bool:
    world_map={w.world_id:w for w in bundle.worlds}
    for wid,st in states.items():
        pending_cover=set()
        for d in st.pending_deliveries:
            if not d.accepted or d.final_ack_at_s is None or d.final_ack_at_s<=t:
                continue
            deadline=next(o.deadline_s for o in bundle.obligations if o.oid==d.oid)
            if d.final_ack_at_s<=deadline:
                pending_cover.add(d.oid)
        cert,_=_world_certificate(
            bundle,world_map[wid],
            delivered=set(st.final_delivered),
            violated=set(st.violated_obligations),
            pending_cover=pending_cover,
            at_s=t,
            satellite_budget=st.sat_budget,
        )
        if not cert.optimistic_backup_feasible:
            return False
    return True


def solve_frontier_guided(bundle:Bundle,**kwargs):
    return solve(bundle,prefix_upper_bound=frontier_prefix_upper_bound,**kwargs)
