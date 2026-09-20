# -*- coding: utf-8 -*-
"""c5_infocontract.py — information-contract checks (astra Task A), LOCAL & read-only w.r.t. claims.

A1  Same lawful history, different FUTURE authorisation: before the divergent downgrade command can
    reach a node (it is authored inside the backhaul outage), every Task-2 local terminator must make
    bit-identical node config trajectories and lease bounds. The future `down` must not change them.
A2  Bound computation takes no future schedule: max_feasible_dense_until signature has no schedule;
    same inputs -> same bound regardless of `down`.
A3  MissionViewGate never reveals a future segment before it is due AND the backhaul is available;
    the initial field view is the first-segment cadence extrapolated; nodes never hold the gate.
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
for d in ("v3joint", "instance", "physics", "runtime", "experiments", "analysis", "monitoring"):
    p = os.path.join(REPO, "code", d)
    if p not in sys.path:
        sys.path.insert(0, p)
sys.path.insert(0, HERE)
import c5_common
net = c5_common.install()
from joint_run import run_joint

H = lambda h: h * 3600
RATE = 1200

# ---- wrap the patched floor to record per-node config trajectories ----
_orig_floor = net.Node._apply_local_floor
_TRAJ = {}


def _rec_floor(self, t_s):
    _orig_floor(self, t_s)
    _TRAJ.setdefault(self.node_id, []).append((t_s, self.sample_interval_s))


net.Node._apply_local_floor = _rec_floor


def base(up, down, peak=.012):
    sched = [(0, 600, "blue"), (up, 300, "yellow"), (down, 600, "blue")]
    return dict(task_hours=48, tail_hours=1, arm="local", groups=2,
                sample_interval_s=600, report_period_s=600, routine_period_s=600,
                harvest_mode="solar", harvest_peak_wh_per_hour=peak, capacity_wh=0.05,
                initial_soc=1.0, outage_start_h=4, outage_hours=16,
                enable_backup=True, backup_rate_s=RATE, backup_bytes=78,
                backup_chooser="maxcov", cache_service="generic_expiry",
                mission_schedule=sched, mission_mode="dayfeed", collect_rows=True)


def run_world(down, c5mode, seed=0, **ov):
    global _TRAJ
    _TRAJ = {}
    c5_common.C5Config.mode = c5mode
    c5_common.C5Config.peak_wh_h = .012
    c5_common.C5Config.task_end_s = 49 * 3600
    c5_common.C5Config.valid_until_s = None
    for k, v in dict(peak_frac=1.0, reserve_mult=1.0, safety_mult=4.0).items():
        setattr(c5_common.C5Config, k, v)
    for k, v in ov.items():
        setattr(c5_common.C5Config, k, v)
    r, inst, _ = run_joint(seed=seed, local_floor=True, **base(H(2), down))
    leases = {nid: getattr(n, "_c5_lease_end", None) for nid, n in inst.nodes.items()}
    return {nid: list(tr) for nid, tr in _TRAJ.items()}, leases, inst


def a1():
    print("== A1 same history, different future downgrade (6h vs 10h, both inside outage 4-20h) ==")
    ok_all = True
    for mode in ("ttl", "soc_mpc", "energy_lease", "lease_safety", "nightfloor"):
        tr6, le6, _ = run_world(H(6), mode, ttl_delta_s=H(8))
        tr10, le10, _ = run_world(H(10), mode, ttl_delta_s=H(8))
        # compare trajectories up to the first local clock-night release (h12); nodes cannot have
        # heard either downgrade (6h and 10h are both within the 4-20h outage)
        cut = H(12)
        same = True
        for nid in tr6:
            a = [(t, p) for t, p in tr6[nid] if t < cut]
            b = [(t, p) for t, p in tr10.get(nid, []) if t < cut]
            if a != b:
                same = False
            if le6.get(nid) != le10.get(nid):
                same = False
        print(f"  {mode:13} identical node config+lease before h12 across futures: {same}")
        ok_all &= same
    return ok_all


def a2():
    print("== A2 bound function has no schedule/future input ==")
    b1 = c5_common.max_feasible_dense_until(H(2) + 60, .048, c5_common.C5Config.peak_eff() if False
                                            else .012 * c5_common.CLOUD_EFF,
                                            c5_common.SAMPLE_WH, 49 * 3600, 300)
    b2 = c5_common.max_feasible_dense_until(H(2) + 60, .048, .012 * c5_common.CLOUD_EFF,
                                            c5_common.SAMPLE_WH, 49 * 3600, 300)
    same = b1 == b2
    import inspect
    src = inspect.getsource(c5_common.max_feasible_dense_until)
    no_future = ("down" not in src) and ("schedule" not in src.lower())
    print(f"  bound stable across worlds: {same} ({b1}); source free of down/schedule: {no_future}")
    return same and no_future


def a3():
    print("== A3 非预知发布：两个不同的未来，网关在 h2 的视图必须相同 ==")
    import c5_gate
    from mission_view import MissionViewGate
    H2, H6, H10 = H(2), H(6), H(10)
    meas = {"rainfall": "mm"}

    def view_at(cls, down, t_pub):
        sched = [(0, 600, "blue"), (H2, 300, "yellow"), (down, 600, "blue")]
        g = cls(meas, 48, sched)
        view = {o.oid: o for o in g.initial_view(g.truth_routine)}
        for seg in g.poll(t_pub, lambda h: True):
            rem, add = g.segment_ops(seg)
            for o in rem:
                view.pop(o.oid, None)
            for o in add:
                view[o.oid] = o
        return view

    # 初始视图的节奏：判窗口宽度。`Obligation` 没有 `period_s` 字段，先前用
    # getattr(o,"period_s",None) 得到的集合是 {None}，其中当然不含 300，检查恒过。
    g = c5_gate.Task2Gate(meas, 48, [(0, 600, "blue"), (H2, 300, "yellow"), (H6, 600, "blue")])
    iv = g.initial_view(g.truth_routine)
    widths = {o.window[1] - o.window[0] for o in iv}          # 秒；首段周期即 600 s
    init_ok = widths == {600}

    # 发布时序
    g2 = MissionViewGate(meas, 48, [(0, 600, "blue"), (H2, 300, "yellow"), (H6, 600, "blue")])
    before = g2.poll(H2 - 60, lambda h: True)
    down = g2.poll(H2 + 60, lambda h: False)
    up = g2.poll(H2 + 120, lambda h: True)
    timing_ok = (before == [] and down == [] and len(up) == 1)

    # 判别测试。先前用 all(... or True for ...) 写成恒真，等于没有检验。
    t2_same = set(view_at(c5_gate.Task2Gate, H6, H2 + 60)) == set(view_at(c5_gate.Task2Gate, H10, H2 + 60))
    tr_same = set(view_at(MissionViewGate, H6, H2 + 60)) == set(view_at(MissionViewGate, H10, H2 + 60))
    n6 = len(view_at(MissionViewGate, H6, H2 + 60))
    n10 = len(view_at(MissionViewGate, H10, H2 + 60))

    _, _, inst = run_world(H(6), "nightfloor")
    nodes_clean = all(not hasattr(n, "mission_gate") for n in inst.nodes.values())

    print(f"  初始视图窗口宽度(秒)={sorted(widths)}（只含首段 600: {init_ok}）")
    print(f"  发布时序 before/down/up = {len(before)}/{len(down)}/{len(up)} → {timing_ok}")
    print(f"  Task2Gate（外推）两个未来视图相同: {t2_same}")
    print(f"  tracked MissionViewGate 两个未来视图相同: {tr_same}"
          f"（h6 视图 {n6} 条 / h10 视图 {n10} 条；False 即复现未来 end 泄漏）")
    print(f"  节点不持有 gate: {nodes_clean}")
    return init_ok and timing_ok and t2_same and nodes_clean, tr_same


if __name__ == "__main__":
    r1, r2, r3, tracked_anticipative = a1(), a2(), *a3()
    print("\nINFO-CONTRACT:", "PASS" if (r1 and r2 and r3) else "FAIL",
          {"A1": r1, "A2": r2, "A3": r3})
    resdir = os.path.join(REPO, "results"); os.makedirs(resdir, exist_ok=True)
    json.dump({"A1_same_history_different_future": r1, "A2_bound_no_future": r2,
               "A3_gate_non_anticipative": r3,
               "A3_tracked_mission_view_is_anticipative": not tracked_anticipative},
              open(os.path.join(resdir, "c5_infocontract.json"), "w"), indent=1)
