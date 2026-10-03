#!/usr/bin/env python3
"""
test_task_generator.py — regression test for the exogenous demand generator (P0.4, contract §5).

The demand set D is the denominator of the primary metric, and README D4 requires that every method
be scored against the same denominator. That requirement is only worth anything if it is checked, so
this file checks the properties the metric depends on:

  1. DETERMINISM. Same deployment, hours and seed produce byte-identical D.
  2. EXOGENEITY. D is a function of (deployment contents, hours, seed) and of nothing else. There is
     no simulator state to read, so the check is that changing everything an arm could change leaves
     D untouched, and that the module holds no mutable state of its own.
  3. THE TWO GRIDS ARE STACKED. Normal demand covers every hour of the run without being interrupted
     by a risk window, and risk demand is added on top of it inside the risk windows, so instants
     inside a risk window carry both.
  4. RISK WINDOWS. The dense demand lands exactly on hours 12-18 and 48-54, and nowhere else.
  5. DEADLINE ARITHMETIC AND CLIPPING. Every task's window and deadline match the contract §5 table,
     and windows the run cannot satisfy are dropped instead of being debited to every method.
  6. CRITICAL SET. The risk-window critical set is fixed by the deployment and by nothing else.
  7. DEV / TEST SEED RANGES. The two ranges are disjoint and are enforced by the helper functions.
  8. COUNTS. Windows and tasks equal what the table implies, computed here from the table's own
     constants rather than from the generator.

Run from the repository root:
    export PYTHONPATH="$PWD/libs/pylibs"
    python3 code/experiments/test_task_generator.py
Exit code 0 means every check passed.
"""
from __future__ import annotations

# --- module resolution -------------------------------------------------------
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime",
                                                     "experiments", "analysis", "monitoring"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
# -----------------------------------------------------------------------------

import copy
import inspect
import os

from task_generator import (  # noqa: E402
    DEADLINE_S,
    DEFAULT_HOURS,
    DEV_SEED_MAX,
    DEV_SEED_MIN,
    GATEWAY_ELEV_M,
    GATEWAY_LAT,
    GATEWAY_LON,
    MONITORING_PROFILES,
    NODE_COUNT,
    NORMAL_INTERVAL_S,
    PRIORITY_NORMAL,
    PRIORITY_RISK,
    PROFILE_LOW_POWER,
    PROFILE_NORMAL,
    PROFILE_RISK,
    RISK_INTERVAL_S,
    RISK_WINDOWS_H,
    SEED_RANGE_DEV,
    SEED_RANGE_TEST,
    TEST_SEED_MIN,
    build_demand,
    build_deployment,
    canonical_demand_bytes,
    critical_nodes,
    demand_digest,
    demand_seed_range,
    demand_seed_split,
    dev_demand,
    dropped_start_instants,
    expected_counts,
    normal_nodes,
    profile_for_hour,
    risk_window_hours,
    test_demand,
)

HERE = os.path.dirname(os.path.abspath(__file__))
FAILURES: list[str] = []

# Measured quantities one demand window carries: displacement and rainfall. A task carries a single
# measurement_type, so one window becomes this many tasks. Written here rather than imported, so the
# expected counts below are derived from the contract table instead of from the generator.
QUANTITIES_PER_WINDOW = 2


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(name)


# ------------------------------------------------- expected counts from the table alone
def table_counts(hours: int = DEFAULT_HOURS) -> dict:
    """The counts the contract §5 table implies, computed here from the table's own constants.

    Nothing here calls the generator. It uses only the run length, the two cadences, the two
    deadlines and the risk windows:

      normal: one window per NORMAL_INTERVAL_S from 0, kept while start + 90 min fits in the run
      risk:   one window per RISK_INTERVAL_S inside each risk window, kept while start + 10 min fits
      tasks:  QUANTITIES_PER_WINDOW per window
      dropped: the windows that did not fit, which no method could have satisfied
    """
    total_s = hours * 3600
    normal_nominal = [t for t in range(0, total_s, NORMAL_INTERVAL_S)]
    normal_kept = [t for t in normal_nominal if t + DEADLINE_S["normal"] <= total_s]
    risk_nominal = [t for t in range(0, total_s, RISK_INTERVAL_S)
                    if any(a * 3600 <= t < b * 3600 for a, b in RISK_WINDOWS_H)]
    risk_kept = [t for t in risk_nominal if t + DEADLINE_S["risk"] <= total_s]
    return {
        "normal_windows": len(normal_kept),
        "risk_windows": len(risk_kept),
        "normal_tasks": len(normal_kept) * QUANTITIES_PER_WINDOW,
        "risk_tasks": len(risk_kept) * QUANTITIES_PER_WINDOW,
        "total_tasks": (len(normal_kept) + len(risk_kept)) * QUANTITIES_PER_WINDOW,
        "dropped_normal_windows": len(normal_nominal) - len(normal_kept),
        "dropped_risk_windows": len(risk_nominal) - len(risk_kept),
    }


def releases(tasks, priority):
    return sorted({t.release_time for t in tasks if t.priority == priority})


# ---------------------------------------------------------------- 1 determinism
def test_determinism() -> None:
    print("\n[1] 确定性：同 seed 得到同一份 D")
    dep = build_deployment(0)
    a = build_demand(dep, hours=DEFAULT_HOURS, seed=0)
    b = build_demand(build_deployment(0), hours=DEFAULT_HOURS, seed=0)
    check("同 seed 两次调用逐字节一致", canonical_demand_bytes(a) == canonical_demand_bytes(b),
          f"sha256 {demand_digest(a)[:16]}")
    check("同 seed 的任务字段完全一致",
          [t.as_dict() for t in a] == [t.as_dict() for t in b])
    check("两次调用之间没有隐藏状态（中间穿插其它时长与 seed 的调用）",
          canonical_demand_bytes(build_demand(dep, hours=24, seed=0)) != canonical_demand_bytes(a)
          and canonical_demand_bytes(build_demand(dep, hours=DEFAULT_HOURS, seed=0))
          == canonical_demand_bytes(a))
    c = build_demand(dep, hours=DEFAULT_HOURS, seed=1)
    check("契约表不含随机抽签，因此同一 split 内不同 seed 得到同一份 D",
          canonical_demand_bytes(a) == canonical_demand_bytes(c))
    check("开发集与测试集 seed 得到同一份 D（参考负载完全由表决定）",
          canonical_demand_bytes(a) == canonical_demand_bytes(
              build_demand(dep, hours=DEFAULT_HOURS, seed=TEST_SEED_MIN)))
    check("任务列表按 release_time 非递减排序",
          all(a[i].release_time <= a[i + 1].release_time for i in range(len(a) - 1)))
    check("任务 id 唯一", len({t.id for t in a}) == len(a))
    check("同一时刻的任务按 measurement_type 有序",
          all(a[i].release_time != a[i + 1].release_time
              or a[i].measurement_type <= a[i + 1].measurement_type
              for i in range(len(a) - 1)))
    check("每条任务窗口非空且期限不早于窗口结束",
          all(t.sample_window[0] < t.sample_window[1] <= t.delivery_deadline for t in a))


# ---------------------------------------------------------------- 2 exogeneity
class _HostileDeployment:
    """A deployment-shaped object whose node order flips on every read.

    A method cannot reach this class, but a generator that leaked container order or simulator state
    into D could behave like it. If D were not purely a function of the deployment's contents, this
    object would make D move between calls.
    """

    def __init__(self, base):
        self._base = base
        self._reads = 0

    @property
    def gateway(self):
        self._reads += 1
        return self._base.gateway

    @property
    def nodes(self):
        self._reads += 1
        return self._base.nodes[::-1] if self._reads % 2 else self._base.nodes

    @property
    def nids(self):
        return tuple(n.nid for n in self.nodes)

    @property
    def critical_nids(self):
        return tuple(n.nid for n in self.nodes if n.critical)

    def nodes_with_role(self, role):
        return tuple(n.nid for n in self.nodes if n.role == role)


def test_exogeneity() -> None:
    print("\n[2] 外生性：D 只取决于 deployment 内容、hours 与 seed")
    dep = build_deployment(0)
    base = build_demand(dep, hours=DEFAULT_HOURS, seed=0)
    base_bytes = canonical_demand_bytes(base)

    hostile = _HostileDeployment(dep)
    try:
        hostile_demand = build_demand(hostile, hours=DEFAULT_HOURS, seed=0)
        same = canonical_demand_bytes(hostile_demand) == base_bytes
    except Exception as exc:                      # noqa: BLE001 - report the failure, not crash
        same = False
        print(f"        hostile reader raised {type(exc).__name__}: {exc}")
    check("deployment 被反复扰动读取时 D 不变", same)

    check("进程内重新构造 deployment 得到同一份 D",
          canonical_demand_bytes(build_demand(build_deployment(0), hours=DEFAULT_HOURS, seed=0))
          == base_bytes)

    params = list(inspect.signature(build_demand).parameters)
    check("build_demand 的入参只有 deployment、hours、seed",
          params == ["deployment", "hours", "seed"], f"{params}")

    snapshot = copy.deepcopy(base)
    for t in snapshot:
        object.__setattr__(t, "priority", PRIORITY_RISK)  # frozen dataclass, forced
    check("调用方改动返回的列表不影响再次调用",
          canonical_demand_bytes(build_demand(dep, hours=DEFAULT_HOURS, seed=0)) == base_bytes)

    alt_nodes = tuple(
        type(n)(n.nid, n.lat, n.lon, n.elev_m, n.role, n.slope_group,
                n.critical and n.nid != "n01") for n in dep.nodes)
    alt = type(dep)(dep.gateway, alt_nodes)
    check("改动关键集合会改变 D（D 确实依赖 deployment 内容）",
          canonical_demand_bytes(build_demand(alt, hours=DEFAULT_HOURS, seed=0)) != base_bytes)


# ---------------------------------------------------------------- 3 stacked grids
def test_stacked_grids() -> None:
    print("\n[3] 常态与风险需求叠加，而不是互相替代")
    dep = build_deployment(0)
    tasks = build_demand(dep, hours=DEFAULT_HOURS, seed=0)
    normal_releases = set(releases(tasks, PRIORITY_NORMAL))
    risk_releases = set(releases(tasks, PRIORITY_RISK))
    hour_instants_in_risk = sorted(r for r in risk_releases if r % NORMAL_INTERVAL_S == 0)

    check("常态需求覆盖每一个整点（0, 3600, ..., 70*3600），不因风险窗中断",
          normal_releases == set(range(0, 71 * 3600, NORMAL_INTERVAL_S)),
          f"{len(normal_releases)} 个时刻")
    check("风险需求全部落在风险窗内",
          all(any(a * 3600 <= r < b * 3600 for a, b in RISK_WINDOWS_H) for r in risk_releases))
    check("风险窗内的整点同时携带常态需求与风险需求（叠加而非替代）",
          all(r in normal_releases for r in hour_instants_in_risk) and hour_instants_in_risk,
          f"风险窗内 {len(hour_instants_in_risk)} 个整点，其中 "
          f"{sum(1 for r in hour_instants_in_risk if r in normal_releases)} 个也有常态需求")
    check("风险窗内每个整点两族任务都在（常态 + 风险）",
          all({t.priority for t in tasks if t.release_time == h}
              == {PRIORITY_NORMAL, PRIORITY_RISK} for h in hour_instants_in_risk))
    check("风险窗内的整点共 4 条任务（两种观测量各两条）",
          all(sum(1 for t in tasks if t.release_time == h) == 4
              for h in hour_instants_in_risk))
    check("风险窗外的整点只有常态需求",
          all({t.priority for t in tasks if t.release_time == h} == {PRIORITY_NORMAL}
              for h in sorted(normal_releases - set(hour_instants_in_risk))))
    check("常态时刻数 71，风险时刻数 144", len(normal_releases) == 71
          and len(risk_releases) == 144, f"{len(normal_releases)} / {len(risk_releases)}")
    check("同一时刻不会出现两条同族同观测量的任务",
          len({(t.release_time, t.priority, t.measurement_type) for t in tasks}) == len(tasks))
    dep_nids = set(build_deployment(0).nids)
    check("同一时刻两族任务的 node_set 关系明确：常态覆盖全部 16 个节点，风险是关键子集",
          all(set(x.node_set) | set(z.node_set) == dep_nids
              for r in normal_releases & risk_releases
              for x in tasks if x.release_time == r and x.priority == PRIORITY_NORMAL
              and x.measurement_type == "displacement"
              for z in tasks if z.release_time == r and z.priority == PRIORITY_NORMAL
              and z.measurement_type == "rainfall")
          and all(set(y.node_set) <= set(critical_nodes(build_deployment(0)))
                  for r in normal_releases & risk_releases
                  for y in tasks if y.release_time == r and y.priority == PRIORITY_RISK))
    check("同一时刻两族任务在观测量上成对出现",
          all({(t.measurement_type) for t in tasks if t.release_time == r
               and t.priority == PRIORITY_NORMAL} == {"displacement", "rainfall"}
              and {(t.measurement_type) for t in tasks if t.release_time == r
                   and t.priority == PRIORITY_RISK} == {"displacement", "rainfall"}
              for r in normal_releases & risk_releases))


# ---------------------------------------------------------------- 4 risk windows
def test_risk_windows() -> None:
    print("\n[4] 风险窗正好落在 12-18 h 与 48-54 h")
    check("风险窗常量与契约 §5 一致", RISK_WINDOWS_H == ((12.0, 18.0), (48.0, 54.0)),
          f"{RISK_WINDOWS_H}")
    check("risk_window_hours 返回同一组窗口", risk_window_hours() == RISK_WINDOWS_H)
    check("风险窗总长 12 h", abs(sum(b - a for a, b in RISK_WINDOWS_H) - 12.0) < 1e-9)

    dep = build_deployment(0)
    tasks = build_demand(dep, hours=DEFAULT_HOURS, seed=0)
    risk_rel = releases(tasks, PRIORITY_RISK)
    normal_rel = set(releases(tasks, PRIORITY_NORMAL))

    def inside(hour: float) -> bool:
        return any(a <= hour < b for a, b in RISK_WINDOWS_H)

    check("每一条风险需求都落在风险窗内", all(inside(r / 3600.0) for r in risk_rel))
    check("两个风险窗的起点都有风险需求", 12 * 3600 in risk_rel and 48 * 3600 in risk_rel)
    check("风险窗结束后的第一个整点回到常态 profile",
          profile_for_hour(18.0) == PROFILE_NORMAL and profile_for_hour(54.0) == PROFILE_NORMAL
          and 18 * 3600 in normal_rel and 54 * 3600 in normal_rel)
    check("窗口边界前一分钟仍为风险 profile",
          profile_for_hour(17.98) == PROFILE_RISK and profile_for_hour(53.98) == PROFILE_RISK)
    check("profile_for_hour 只给出表中两种 profile",
          {profile_for_hour(h / 10.0) for h in range(0, 721)} == {PROFILE_NORMAL, PROFILE_RISK})

    for start, end in RISK_WINDOWS_H:
        inside_window = [r for r in risk_rel if start * 3600 <= r < end * 3600]
        want = int((end - start) * 3600 / RISK_INTERVAL_S)
        check(f"{start:.0f}-{end:.0f} h 内每 5 min 一个风险需求（{want} 个）",
              len(inside_window) == want
              and all(b - a == RISK_INTERVAL_S for a, b in zip(inside_window, inside_window[1:])),
              f"{len(inside_window)} 个")
    check("两个风险窗之间没有风险需求",
          not [r for r in risk_rel if 18 * 3600 <= r < 48 * 3600])


# ---------------------------------------------------------------- 5 deadlines and clipping
def test_deadline_arithmetic() -> None:
    print("\n[5] 期限算术与不可满足窗口的裁剪")
    dep = build_deployment(0)
    tasks = build_demand(dep, hours=DEFAULT_HOURS, seed=0)
    total_s = 72 * 3600

    bad_deadline, bad_window = [], []
    for t in tasks:
        if t.delivery_deadline - t.release_time != DEADLINE_S[
                "risk" if t.priority == PRIORITY_RISK else "normal"]:
            bad_deadline.append(t.id)
        want_window = RISK_INTERVAL_S if t.priority == PRIORITY_RISK else NORMAL_INTERVAL_S
        if t.sample_window != (t.release_time, t.release_time + want_window):
            bad_window.append(t.id)
    check("期限 = 窗口开始 + 10 min（风险）/ 90 min（常态）", not bad_deadline,
          f"{len(bad_deadline)} 条不符")
    check("样本窗 = 该 profile 的一个需求窗", not bad_window, f"{len(bad_window)} 条不符")
    check("没有任务的期限落在运行结束之后（不可满足的窗口已裁掉）",
          all(t.delivery_deadline <= total_s for t in tasks),
          f"最大期限 {max(t.delivery_deadline for t in tasks)} / 运行终点 {total_s}")
    check("释放时刻都在运行区间内", all(0 <= t.release_time < total_s for t in tasks))
    check("窗口结束时刻都在运行区间内", all(t.sample_window[1] <= total_s for t in tasks))

    want = table_counts(DEFAULT_HOURS)
    dropped = dropped_start_instants(total_s)
    check("被裁掉的常态窗口 = 1（最后整点的 90 min 期限越过 72 h）",
          dropped[0] == want["dropped_normal_windows"] == 1, f"{dropped[0]}")
    check("被裁掉的风险窗口 = 0（风险窗在 18:00 关闭，其内最后一条的期限正好到 18:00）",
          dropped[1] == want["dropped_risk_windows"] == 0, f"{dropped[1]}")
    check("被裁窗口确实不在 D 中（71 h 的常态需求不存在）",
          max(t.release_time for t in tasks if t.priority == PRIORITY_NORMAL) == 70 * 3600
          and 71 * 3600 not in {t.release_time for t in tasks})
    check("裁剪只发生在网格末端：70 h 及以前整点一个不少",
          {t.release_time for t in tasks if t.priority == PRIORITY_NORMAL}
          == set(range(0, 71 * 3600, NORMAL_INTERVAL_S)))

    partial = build_demand(dep, hours=14, seed=0)
    p_total = 14 * 3600
    p_dropped = dropped_start_instants(p_total)
    p_want = table_counts(14)
    check("运行在风险窗中途结束时，越界的风险窗口也被裁掉",
          all(t.delivery_deadline <= p_total for t in partial)
          and max(t.release_time for t in partial if t.priority == PRIORITY_RISK)
          == p_total - DEADLINE_S["risk"])
    check("短运行的被裁窗口数与独立算出的表值一致",
          p_dropped == (p_want["dropped_normal_windows"], p_want["dropped_risk_windows"])
          and p_dropped[1] > 0, f"{p_dropped}")

    generations = sorted({t.policy_generation for t in tasks})
    check("政策代数共 5 段：常态/风险/常态/风险/常态",
          generations == [1, 2, 3, 4, 5], f"{generations}")
    by_gen = {g: {t.priority for t in tasks if t.policy_generation == g} for g in generations}
    check("每个代数段内的 profile 归属稳定：风险段含风险任务，常态段不含",
          all((PRIORITY_RISK in by_gen[g]) == (g in (2, 4)) for g in generations))
    check("风险段也同时含常态任务（叠加）",
          all(PRIORITY_NORMAL in by_gen[g] for g in (2, 4)), f"{by_gen}")
    seg_hours = {g: (min(t.release_time for t in tasks if t.policy_generation == g) / 3600.0,
                     max(t.release_time for t in tasks if t.policy_generation == g) / 3600.0)
                 for g in generations}
    # the last risk instant inside a 6 h window, in hours
    last_of_window = (RISK_INTERVAL_S * (int(6 * 3600 / RISK_INTERVAL_S) - 1)) / 3600.0
    check("每段政策代数的时刻范围正好覆盖该段（常态段到 11 h / 47 h / 70 h，风险段到窗内最后一条）",
          all(abs(seg_hours[g][0] - lo) < 1e-9 and abs(seg_hours[g][1] - hi) < 1e-9
              for g, lo, hi in ((1, 0.0, 11.0), (2, 12.0, 12.0 + last_of_window),
                                (3, 18.0, 47.0), (4, 48.0, 48.0 + last_of_window),
                                (5, 54.0, 70.0))), f"{seg_hours}")
    check("risk 与 normal 的 profile 参数与表一致",
          MONITORING_PROFILES[PROFILE_RISK] == {"sample_s": 60, "upload_s": 300}
          and MONITORING_PROFILES[PROFILE_NORMAL] == {"sample_s": 300, "upload_s": 3600}
          and MONITORING_PROFILES[PROFILE_LOW_POWER] == {"sample_s": 900, "upload_s": 3600})
    check("优先级方向：风险高于常态",
          PRIORITY_RISK > PRIORITY_NORMAL
          and {t.priority for t in tasks} == {PRIORITY_NORMAL, PRIORITY_RISK})
    check("每种 profile 的上传周期都不超过对应期限（窗口内存在可满足的机会）",
          MONITORING_PROFILES[PROFILE_NORMAL]["upload_s"] <= DEADLINE_S["normal"]
          and MONITORING_PROFILES[PROFILE_RISK]["upload_s"] <= DEADLINE_S["risk"])
    check("每种 profile 的采样周期都不超过其需求窗长度",
          MONITORING_PROFILES[PROFILE_RISK]["sample_s"] <= RISK_INTERVAL_S
          and MONITORING_PROFILES[PROFILE_NORMAL]["sample_s"] <= NORMAL_INTERVAL_S)


# ---------------------------------------------------------------- 6 critical set
def test_critical_set() -> None:
    print("\n[6] 关键测点集合由 deployment 固定")
    dep0 = build_deployment(0)
    dep_test = build_deployment(TEST_SEED_MIN)
    check("关键集合不随 seed 变化", critical_nodes(dep0) == critical_nodes(dep_test),
          f"{critical_nodes(dep0)}")
    check("关键集合是 16 节点中的 8 个", len(critical_nodes(dep0)) == 8)
    check("关键集合每个坡面组 4 个",
          all(sum(1 for n in dep0.nodes if n.critical and n.slope_group == g) == 4
              for g in (0, 1)))
    check("两个坡面组各 8 个节点",
          all(sum(1 for n in dep0.nodes if n.slope_group == g) == 8 for g in (0, 1)))
    check("常态需求覆盖全部 16 个节点", normal_nodes(dep0) == dep0.nids == tuple(
        f"n{i:02d}" for i in range(NODE_COUNT)))

    tasks = build_demand(dep0, hours=DEFAULT_HOURS, seed=0)
    critical = set(critical_nodes(dep0))
    disp = set(dep0.nodes_with_role("deformation"))
    rain = set(dep0.nodes_with_role("rainfall"))
    normal_tasks = [t for t in tasks if t.priority == PRIORITY_NORMAL]
    risk_tasks = [t for t in tasks if t.priority == PRIORITY_RISK]

    check("常态需求的 node_set 覆盖全部 16 个节点",
          set().union(*[set(t.node_set) for t in normal_tasks]) == set(dep0.nids))
    check("常态 displacement 任务用全部 10 个形变节点",
          {frozenset(t.node_set) for t in normal_tasks
           if t.measurement_type == "displacement"} == {frozenset(disp)})
    check("常态 rainfall 任务用全部 2 个雨量计",
          {frozenset(t.node_set) for t in normal_tasks if t.measurement_type == "rainfall"}
          == {frozenset(rain)})
    check("风险需求的 node_set 是关键子集",
          all(set(t.node_set) <= critical for t in risk_tasks))
    check("风险需求用满关键形变集与两个雨量计",
          all(set(t.node_set) == (critical & disp if t.measurement_type == "displacement"
                                  else critical & rain) for t in risk_tasks))
    check("非关键节点从不进入风险分母",
          not (set().union(*[set(t.node_set) for t in risk_tasks]) - critical))
    check("每条任务的 node_set 非空且属于该 deployment",
          all(t.node_set and set(t.node_set) <= set(dep0.nids) for t in tasks))
    check("测量类型与节点角色一致",
          all((t.measurement_type == "rainfall") == (set(t.node_set) <= rain) for t in tasks))


# ---------------------------------------------------------------- 7 dev / test
def test_dev_test_split() -> None:
    print("\n[7] 开发集与测试集 seed 区间")
    dev_lo, dev_hi = demand_seed_range("dev")
    te_lo, te_hi = demand_seed_range("test")
    span = f"dev [{dev_lo},{dev_hi}] test [{te_lo},{te_hi if te_hi else 'inf'})"
    check("两个 seed 区间不相交", te_lo > dev_hi, span)
    check("区间常量与导出的常量一致",
          (dev_lo, dev_hi) == (DEV_SEED_MIN, DEV_SEED_MAX)
          and (te_lo, te_hi) == SEED_RANGE_TEST and te_lo == TEST_SEED_MIN)
    check("区间外的 seed 被拒绝", _raises(lambda: demand_seed_split(5000))
          and dev_hi < 5000 < te_lo)
    check("dev seed 判为 dev、test seed 判为 test",
          demand_seed_split(DEV_SEED_MIN) == "dev" and demand_seed_split(DEV_SEED_MAX) == "dev"
          and demand_seed_split(TEST_SEED_MIN) == "test")
    check("dev_demand 拒绝测试 seed", _raises(lambda: dev_demand(seed=TEST_SEED_MIN)))
    check("test_demand 拒绝开发 seed", _raises(lambda: test_demand(seed=DEV_SEED_MAX)))
    check("未在任一 split 的 seed 被 build_demand 拒绝",
          _raises(lambda: build_demand(build_deployment(0), hours=24, seed=5000)))

    dev_tasks = dev_demand(hours=DEFAULT_HOURS, seed=DEV_SEED_MIN)
    test_tasks = test_demand(hours=DEFAULT_HOURS, seed=TEST_SEED_MIN)
    check("两个区间的代表 seed 产生的 D 逐字节一致（参考负载由表完全决定）",
          canonical_demand_bytes(dev_tasks) == canonical_demand_bytes(test_tasks))
    check("因此开发集与测试集的需求内容相同：隔离只能放在随运行变化的因子上",
          {t.signature() for t in dev_tasks} == {t.signature() for t in test_tasks})
    check("两个集合规模都等于表推出的任务数",
          len(dev_tasks) == len(test_tasks) == table_counts(DEFAULT_HOURS)["total_tasks"],
          f"{len(dev_tasks)} / {len(test_tasks)}")


def _raises(fn) -> bool:
    try:
        fn()
    except Exception:                             # noqa: BLE001 - any rejection counts
        return True
    return False


# ---------------------------------------------------------------- 8 counts
def test_counts() -> None:
    print("\n[8] 窗口数与任务数等于契约表推出的值")
    dep = build_deployment(0)
    want = table_counts(DEFAULT_HOURS)
    tasks = build_demand(dep, hours=DEFAULT_HOURS, seed=0)
    normal = [t for t in tasks if t.priority == PRIORITY_NORMAL]
    risk = [t for t in tasks if t.priority == PRIORITY_RISK]

    check("常态需求窗 71 个（每小时一个，最后整点的期限越过 72 h 被裁掉）",
          want["normal_windows"] == 71, f"{want['normal_windows']}")
    check("风险需求窗 144 个（12 h / 5 min）", want["risk_windows"] == 144,
          f"{want['risk_windows']}")
    check("常态任务 142 条（71 窗 × 2 观测量）", len(normal) == want["normal_tasks"] == 142,
          f"{len(normal)}")
    check("风险任务 288 条（144 窗 × 2 观测量）", len(risk) == want["risk_tasks"] == 288,
          f"{len(risk)}")
    check("总任务数 430 条", len(tasks) == want["total_tasks"] == 430, f"{len(tasks)}")
    check("被裁窗口共 1 个（1 常态 + 0 风险）",
          dropped_start_instants(72 * 3600) == (want["dropped_normal_windows"],
                                                want["dropped_risk_windows"]) == (1, 0))
    check("任务数是其所在网格时刻数的 2 倍",
          len(normal) == 2 * len(releases(tasks, PRIORITY_NORMAL))
          and len(risk) == 2 * len(releases(tasks, PRIORITY_RISK)))
    check("生成器自报的 expected_counts 与本文件独立算出的表值一致",
          expected_counts(DEFAULT_HOURS) == want, f"{expected_counts(DEFAULT_HOURS)}")

    for hours in (1, 6, 12, 13, 14, 18, 24, 48, 54, 72, 96):
        want_h = table_counts(hours)
        got = build_demand(dep, hours=hours, seed=0)
        got_normal = sum(1 for t in got if t.priority == PRIORITY_NORMAL)
        got_risk = sum(1 for t in got if t.priority == PRIORITY_RISK)
        check(f"{hours} h：常态 {want_h['normal_tasks']} + 风险 {want_h['risk_tasks']}，"
              f"无越界期限",
              got_normal == want_h["normal_tasks"] and got_risk == want_h["risk_tasks"]
              and all(t.delivery_deadline <= hours * 3600 for t in got),
              f"实测 {got_normal}/{got_risk}")
        check(f"{hours} h：expected_counts 与被裁窗口数与表一致",
              expected_counts(hours) == want_h
              and dropped_start_instants(hours * 3600)
              == (want_h["dropped_normal_windows"], want_h["dropped_risk_windows"]))

    check("hours<=0 被拒绝", _raises(lambda: build_demand(dep, hours=0, seed=0)))


# ---------------------------------------------------------------- deployment shape
def test_deployment_shape() -> None:
    print("\n[9] 部署：16 节点 / 2 坡面组 / 1 网关")
    dep = build_deployment(0)
    check("网关坐标与 README §四 一致",
          dep.gateway.lat == 30.3300 and dep.gateway.lon == 94.7800
          and abs(dep.gateway.lat - GATEWAY_LAT) < 1e-9
          and abs(dep.gateway.lon - GATEWAY_LON) < 1e-9)
    check("网关海拔 2317 m", dep.gateway.elev_m == 2317.0
          and abs(dep.gateway.elev_m - GATEWAY_ELEV_M) < 1e-9)
    check("16 个节点", len(dep.nodes) == NODE_COUNT == 16)
    check("两个坡面组", {n.slope_group for n in dep.nodes} == {0, 1})
    check("两个组各 8 个节点且 node id 唯一",
          len({n.nid for n in dep.nodes}) == 16
          and all(sum(1 for n in dep.nodes if n.slope_group == g) == 8 for g in (0, 1)))
    check("角色只有形变与雨量两类",
          {n.role for n in dep.nodes} == {"deformation", "rainfall"})
    check("每组各一个雨量计",
          all(sum(1 for n in dep.nodes if n.role == "rainfall" and n.slope_group == g) == 1
              for g in (0, 1)))
    check("节点不在网关位置上，两组占用不同坐标格点",
          all((n.lat, n.lon) != (GATEWAY_LAT, GATEWAY_LON) for n in dep.nodes)
          and len({(n.lat, n.lon) for n in dep.nodes}) == 16)
    check("两组具有不同高程分布（两个坡面组确有差异）",
          len({tuple(sorted(n.elev_m for n in dep.nodes if n.slope_group == g))
               for g in (0, 1)}) == 2)
    check("节点几何不随 seed 变化",
          build_deployment(0).nodes == build_deployment(TEST_SEED_MIN).nodes)
    check("node_set 的成员都是部署内的节点（无幽灵节点）",
          all(set(t.node_set) <= set(dep.nids)
              for t in build_demand(dep, hours=DEFAULT_HOURS, seed=0)))


# ---------------------------------------------------------------- documented choices
def test_documented_choices() -> None:
    """The module documents the choices the contract left open; check they are still stated."""
    print("\n[10] 契约未明确处的文档化选择")
    path = os.path.join(_CODE, "monitoring", "task_generator.py")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    check("模块说明包含 A 层声明（非安全标准、非客户 SLA）",
          "not a geohazard safety standard" in text and "customer SLA" in text)
    check("模块说明写明了开发/测试 seed 区间",
          "development seeds 0-999" in text and "10000" in text)
    check("模块说明注明坐标与高程为研究假设",
          "research assumption" in text and "not surveyed monuments" in text)
    check("模块说明说明两个网格是叠加的", "STACKED" in text)
    check("模块说明说明不可满足的窗口被裁掉", "NOT IN D" in text)
    check("模块说明记录了样本窗与期限的解释",
          "a valid sample is taken" in text or "INSIDE" in text)
    check("任务字段与契约 §4 的八项一一对应",
          all(field in text for field in ("id", "node_set", "measurement_type", "release_time",
                                          "sample_window", "delivery_deadline", "priority",
                                          "policy_generation")))
    check("三个 profile 以数据形式暴露且数值与表一致",
          set(MONITORING_PROFILES) == {PROFILE_NORMAL, PROFILE_RISK, PROFILE_LOW_POWER}
          and MONITORING_PROFILES[PROFILE_LOW_POWER]["sample_s"] == 15 * 60
          and MONITORING_PROFILES[PROFILE_LOW_POWER]["upload_s"] == 60 * 60)


def main() -> int:
    print("外生需求生成器回归测试（P0.4，契约 §5）")
    test_determinism()
    test_exogeneity()
    test_stacked_grids()
    test_risk_windows()
    test_deadline_arithmetic()
    test_critical_set()
    test_dev_test_split()
    test_counts()
    test_deployment_shape()
    test_documented_choices()
    print("\n" + "-" * 74)
    if FAILURES:
        print(f"  {len(FAILURES)} 项失败: {', '.join(FAILURES)}")
        return 1
    print("  全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
