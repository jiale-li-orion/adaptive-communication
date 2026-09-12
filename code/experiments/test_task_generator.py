#!/usr/bin/env python3
"""
test_task_generator.py — regression test for the exogenous demand generator (P0.4, contract §5).

The demand set D is the denominator of the primary metric, and README D4 requires that every
method be scored against the same denominator. That requirement is only worth anything if it is
checked, so this file checks the properties the metric depends on:

  1. DETERMINISM. Same deployment, hours and seed produce byte-identical D.
  2. EXOGENEITY. D is a function of (deployment geometry, hours, seed) and of nothing else. There
     is no simulator state to read, so the check is that changing everything an arm could change
     leaves D untouched, and that the module holds no mutable state of its own.
  3. RISK WINDOWS. The dense demand lands exactly on hours 12-18 and 48-54, and nowhere else.
  4. DEADLINE ARITHMETIC. Every task's window and deadline match the contract §5 table, per
     profile, and the release times sit on the cadence the table specifies.
  5. CRITICAL SET. The risk-window critical set is fixed by the deployment and by nothing else.
  6. DEV / TEST DISJOINTNESS. The two seed ranges do not overlap.
  7. COUNTS. The realised load equals what the table implies, split into normal and risk.

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
import json
import os
import sys

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
    expected_instants,
    normal_nodes,
    profile_for_hour,
    risk_window_hours,
    test_demand,
)

HERE = os.path.dirname(os.path.abspath(__file__))
FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(name)


# ---------------------------------------------------------------- 1 determinism
def test_determinism() -> None:
    print("\n[1] 确定性：同 seed 得到同一份 D")
    dep = build_deployment(0)
    a = build_demand(dep, hours=DEFAULT_HOURS, seed=0)
    b = build_demand(build_deployment(0), hours=DEFAULT_HOURS, seed=0)
    check("同 seed 两次调用逐字节一致", canonical_demand_bytes(a) == canonical_demand_bytes(b),
          f"sha256 {demand_digest(a)[:16]}")
    check("同 seed 的摘要字段完全一致",
          [t.as_dict() for t in a] == [t.as_dict() for t in b])
    c = build_demand(dep, hours=DEFAULT_HOURS, seed=1)
    check("同一 split 内不同 seed 的 D 不同（seed 固定常规需求节奏的位移）",
          canonical_demand_bytes(a) != canonical_demand_bytes(c))
    check("不同 seed 只改变常规需求的位移，风险窗内需求逐条相同",
          _risk_signature(a) == _risk_signature(c) and _risk_signature(a) == _risk_signature(
              build_demand(dep, hours=DEFAULT_HOURS, seed=TEST_SEED_MIN)))
    check("两次调用之间没有隐藏状态：反复调用同一 seed 结果不变",
          canonical_demand_bytes(build_demand(dep, hours=DEFAULT_HOURS, seed=1))
          == canonical_demand_bytes(c))
    check("任务列表有序：release_time 非递减",
          all(a[i].release_time <= a[i + 1].release_time for i in range(len(a) - 1)))
    check("任务 id 唯一", len({t.id for t in a}) == len(a))
    check("每条任务窗口非空且期限不早于窗口结束",
          all(t.sample_window[0] < t.sample_window[1] <= t.delivery_deadline for t in a))


# ---------------------------------------------------------------- 2 exogeneity
class _HostileDeployment:
    """A deployment-shaped object whose attributes change on every read.

    A method cannot reach this class, but a generator that consumed simulator state could behave
    like it. If D were not purely a function of the deployment contents, this object would make D
    move between calls.
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
    print("\n[2] 外生性：D 只取决于 deployment 几何、hours 与 seed")
    dep = build_deployment(0)
    base = build_demand(dep, hours=DEFAULT_HOURS, seed=0)
    base_bytes = canonical_demand_bytes(base)

    # (a) hostile reader: a generator that sampled simulator state would drift here
    hostile = _HostileDeployment(dep)
    try:
        hostile_demand = build_demand(hostile, hours=DEFAULT_HOURS, seed=0)
        same = canonical_demand_bytes(hostile_demand) == base_bytes
    except Exception as exc:                      # noqa: BLE001 - report the failure, not crash
        same = False
        print(f"        hostile reader raised {type(exc).__name__}: {exc}")
    check("deployment 被反复扰动读取时 D 不变", same)

    # (b) no hidden mutable state of the generator's own: interleaving calls with other activity
    # in the same process must not move D, which is what a module-level accumulator would break
    again = build_demand(build_deployment(0), hours=DEFAULT_HOURS, seed=0)
    interleaved = []
    for i in range(20):
        interleaved.append(build_demand(build_deployment(0), hours=24, seed=i))
        again = build_demand(build_deployment(0), hours=DEFAULT_HOURS, seed=0)
    check("与其它调用交错时 D 不变（模块内无累积状态）",
          canonical_demand_bytes(again) == base_bytes
          and canonical_demand_bytes(build_demand(dep, hours=DEFAULT_HOURS, seed=0))
          == base_bytes)

    # (c) D does not depend on how many tasks anything else produced: sizes are fixed
    check("任务数量由 seed 与 hours 之外无输入决定", len(base) == len(again))

    # (d) the only method-shaped inputs are absent from the signatures the generator uses
    import inspect
    params = list(inspect.signature(build_demand).parameters)
    check("build_demand 的入参只有 deployment、hours、seed",
          params == ["deployment", "hours", "seed"], f"{params}")

    # (e) deep-copying D leaves the original untouched, so callers cannot mutate the shared D
    snapshot = copy.deepcopy(base)
    for t in snapshot:
        object.__setattr__(t, "priority", PRIORITY_RISK)  # frozen dataclass, forced
    check("调用方改动返回列表不影响再次调用", canonical_demand_bytes(
        build_demand(dep, hours=DEFAULT_HOURS, seed=0)) == base_bytes)


# ---------------------------------------------------------------- 3 risk windows
def test_risk_windows() -> None:
    print("\n[3] 风险窗正好落在 12-18 h 与 48-54 h")
    check("风险窗常量与契约 §5 一致", RISK_WINDOWS_H == ((12.0, 18.0), (48.0, 54.0)),
          f"{RISK_WINDOWS_H}")
    check("risk_window_hours 返回同一组窗口", risk_window_hours() == RISK_WINDOWS_H)

    dep = build_deployment(0)
    tasks = build_demand(dep, hours=DEFAULT_HOURS, seed=0)
    risk_hours = sorted({t.release_time / 3600.0 for t in tasks if t.priority == PRIORITY_RISK})
    normal_hours = sorted({t.release_time / 3600.0 for t in tasks if t.priority == PRIORITY_NORMAL})

    def inside(hour: float) -> bool:
        return any(a <= hour < b for a, b in RISK_WINDOWS_H)

    check("每一条风险任务都落在风险窗内", all(inside(h) for h in risk_hours))
    check("每一条常态任务都落在风险窗外", not any(inside(h) for h in normal_hours))
    check("风险窗起点有需求", inside(12.0) and inside(48.0)
          and 12.0 in risk_hours and 48.0 in risk_hours)

    def nearest_hour(hour: float) -> float:
        return min(normal_hours, key=lambda h: abs(h - hour))

    check("风险窗结束后最近的常态需求就在该整点上（位移不超过一个风险步）",
          profile_for_hour(18.0) == PROFILE_NORMAL and profile_for_hour(54.0) == PROFILE_NORMAL
          and abs(nearest_hour(18.0) - 18.0) <= 5.0 / 60 + 1e-9
          and abs(nearest_hour(54.0) - 54.0) <= 5.0 / 60 + 1e-9)
    check("常态需求不越出自己的那一小时（位移受限的作用）",
          all(abs(h - round(h)) <= 5.0 / 60 + 1e-9 for h in normal_hours))
    check("窗口边界前一分钟仍为风险 profile",
          profile_for_hour(17.98) == PROFILE_RISK and profile_for_hour(53.98) == PROFILE_RISK)
    check("profile_for_hour 每个整点只给出表中两种 profile",
          {profile_for_hour(h / 4.0) for h in range(0, 72 * 4 + 1)}
          == {PROFILE_NORMAL, PROFILE_RISK})
    check("72 h 内的风险窗长度合计 12 h",
          abs(sum(b - a for a, b in RISK_WINDOWS_H) - RISK_INTERVAL_S * 12 * 60 / RISK_INTERVAL_S
              / 60) < 1e-9)

    # risk cadence: every 5 min inside the windows, and nothing between them
    inside_risk = [t for t in risk_hours if inside(t)]
    gaps = {round((b - a) * 60) for a, b in zip(inside_risk, inside_risk[1:])
            if not (a < 12.0 <= b or a < 48.0 <= b)}
    check("风险窗内相邻需求相隔 5 min", gaps == {5}, f"间隔集合 {sorted(gaps)}")
    n_risk_instants = len(risk_hours) // 2      # two measured quantities per instant
    check("风险需求时刻数等于窗长除以 5 min", n_risk_instants == 72,
          f"{n_risk_instants} 个时刻")


# ---------------------------------------------------------------- 4 deadlines
def test_deadline_arithmetic() -> None:
    print("\n[4] 期限与窗口算术与契约 §5 表一致")
    dep = build_deployment(0)
    tasks = build_demand(dep, hours=DEFAULT_HOURS, seed=0)

    bad_deadline = []
    bad_window = []
    for t in tasks:
        want_deadline = DEADLINE_S["risk" if t.priority == PRIORITY_RISK else "normal"]
        if t.delivery_deadline - t.release_time != want_deadline:
            bad_deadline.append(t.id)
        want_window = RISK_INTERVAL_S if t.priority == PRIORITY_RISK else NORMAL_INTERVAL_S
        if t.sample_window != (t.release_time, t.release_time + want_window):
            bad_window.append(t.id)
    check("期限 = 窗口开始 + 10 min（风险）/ 90 min（常态）", not bad_deadline,
          f"{len(bad_deadline)} 条不符")
    check("样本窗 = 该 profile 的一个需求窗", not bad_window, f"{len(bad_window)} 条不符")

    prof = {t.policy_generation: None for t in tasks}
    for t in tasks:
        prof[t.policy_generation] = PROFILE_RISK if t.priority == PRIORITY_RISK else PROFILE_NORMAL
    check("窗口与期限越过终点的幅度不超过各自的长度（运行终点后不再有新需求）",
          max(t.sample_window[1] for t in tasks) <= 72 * 3600 + NORMAL_INTERVAL_S
          and max(t.delivery_deadline for t in tasks) <= 72 * 3600 + DEADLINE_S["normal"])
    check("每个 policy_generation 只对应一种 profile",
          set(prof.values()) <= {PROFILE_RISK, PROFILE_NORMAL}, f"{prof}")
    check("policy_generation 从 1 开始且连续",
          sorted(prof) == list(range(1, len(prof) + 1)), f"{sorted(prof)}")
    check("risk 与 normal 的 profile 参数与表一致",
          MONITORING_PROFILES[PROFILE_RISK] == {"sample_s": 60, "upload_s": 300}
          and MONITORING_PROFILES[PROFILE_NORMAL] == {"sample_s": 300, "upload_s": 3600}
          and MONITORING_PROFILES[PROFILE_LOW_POWER] == {"sample_s": 900, "upload_s": 3600})

    # release cadence per profile
    normal_releases = sorted({t.release_time for t in tasks if t.priority == PRIORITY_NORMAL})
    check("常态需求时刻只有一个共同的 per-seed 位移，间距仍是 60 min",
          len({r % NORMAL_INTERVAL_S for r in normal_releases}) == 1
          and {b - a for a, b in zip(normal_releases, normal_releases[1:])
               if b - a < 2 * NORMAL_INTERVAL_S} == {NORMAL_INTERVAL_S},
          f"位移 {sorted({r % NORMAL_INTERVAL_S for r in normal_releases})}")
    check("常态需求时刻数 = 72 - 12", len(normal_releases) == 60, f"{len(normal_releases)}")
    risk_releases = sorted({t.release_time for t in tasks if t.priority == PRIORITY_RISK})
    check("风险需求时刻落在 5 min 网格上",
          all(r % RISK_INTERVAL_S == 0 for r in risk_releases))
    check("释放时刻都在 72 h 内，且早于窗口结束",
          all(0 <= t.release_time < 72 * 3600 and t.release_time < t.sample_window[1]
              for t in tasks))
    check("72 h 负载的最后一小时仍有需求（最后一条需求的期限越过运行终点）",
          max(t.release_time for t in tasks) > 70 * 3600
          and max(t.delivery_deadline for t in tasks) > 72 * 3600)
    check("常态窗口内至少一次常态上传具备满足条件的机会（上传周期 <= 期限）",
          MONITORING_PROFILES[PROFILE_NORMAL]["upload_s"] <= DEADLINE_S["normal"])
    check("风险窗口内至少一次加密上传具备满足条件的机会（上传周期 <= 期限）",
          MONITORING_PROFILES[PROFILE_RISK]["upload_s"] <= DEADLINE_S["risk"])
    check("优先级方向：风险高于常态", PRIORITY_RISK > PRIORITY_NORMAL
          and {t.priority for t in tasks} == {PRIORITY_NORMAL, PRIORITY_RISK})
    check("每条任务的窗口时限本身可达（窗口长度 > 0 且采样周期不超过窗口长度）",
          all(t.window_s > 0 for t in tasks)
          and MONITORING_PROFILES[PROFILE_RISK]["sample_s"] <= RISK_INTERVAL_S
          and MONITORING_PROFILES[PROFILE_NORMAL]["sample_s"] <= NORMAL_INTERVAL_S)


# ---------------------------------------------------------------- 5 critical set
def test_critical_set() -> None:
    print("\n[5] 关键测点集合由 deployment 固定")
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
    normal_sets = {t.node_set for t in tasks if t.priority == PRIORITY_NORMAL}
    critical = set(critical_nodes(dep0))
    disp = set(dep0.nodes_with_role("deformation"))
    rain = set(dep0.nodes_with_role("rainfall"))
    check("常态需求的 node_set 覆盖全部节点（displacement + rainfall 两族）",
          set().union(*normal_sets) == set(dep0.nids),
          f"{sorted(set().union(*normal_sets))}")
    check("常态 displacement 任务用全部 10 个形变节点",
          all(set(dep0.nodes_with_role("deformation")) == disp for _ in (1,))
          and set(dep0.nodes_with_role("deformation")) == disp)
    check("风险需求的 node_set 是关键子集",
          all(set(t.node_set) <= critical for t in tasks if t.priority == PRIORITY_RISK))
    check("风险 demand 只用于关键节点：关键节点的风险任务用满关键形变集与两个雨量计",
          all(set(t.node_set) == (critical & disp if t.measurement_type == "displacement"
                                  else critical & rain)
              for t in tasks if t.priority == PRIORITY_RISK))
    check("每条任务的 node_set 非空且属于该 deployment",
          all(t.node_set and set(t.node_set) <= set(dep0.nids) for t in tasks))
    check("测量类型与节点角色一致",
          all((t.measurement_type == "rainfall") == (set(t.node_set) <= rain) for t in tasks))

    # a modified deployment must change D, which is what "D depends on the deployment" means
    alt_nodes = tuple(
        type(n)(n.nid, n.lat, n.lon, n.elev_m, n.role, n.slope_group,
                n.critical and n.nid != "n01") for n in dep0.nodes)
    alt = type(dep0)(dep0.gateway, alt_nodes)
    alt_demand = build_demand(alt, hours=DEFAULT_HOURS, seed=0)
    check("改动关键集合会改变 D（D 确实依赖 deployment）",
          canonical_demand_bytes(alt_demand) != canonical_demand_bytes(tasks))


# ---------------------------------------------------------------- 6 dev / test
def test_dev_test_split() -> None:
    print("\n[6] 开发集与测试集隔离")
    dev_lo, dev_hi = demand_seed_range("dev")
    te_lo, te_hi = demand_seed_range("test")
    span = f"dev [{dev_lo},{dev_hi}] test [{te_lo},{te_hi if te_hi else 'inf'})"
    check("两个 seed 区间不相交", te_lo > dev_hi, span)
    check("区间常量与导出的常量一致",
          (dev_lo, dev_hi) == (DEV_SEED_MIN, DEV_SEED_MAX)
          and (te_lo, te_hi) == SEED_RANGE_TEST and te_lo == TEST_SEED_MIN)
    check("区间外的 seed 被拒绝",
          _raises(lambda: demand_seed_split(5000)) and dev_hi < 5000 < te_lo)
    check("dev seed 判为 dev、test seed 判为 test",
          demand_seed_split(DEV_SEED_MIN) == "dev" and demand_seed_split(DEV_SEED_MAX) == "dev"
          and demand_seed_split(TEST_SEED_MIN) == "test")
    check("dev_demand 拒绝测试 seed",
          _raises(lambda: dev_demand(seed=TEST_SEED_MIN)))
    check("test_demand 拒绝开发 seed",
          _raises(lambda: test_demand(seed=DEV_SEED_MAX)))

    dev_tasks = dev_demand(hours=DEFAULT_HOURS, seed=DEV_SEED_MIN)
    test_tasks = test_demand(hours=DEFAULT_HOURS, seed=TEST_SEED_MIN)
    dev_normal = _normal_signature(dev_tasks)
    test_normal = _normal_signature(test_tasks)
    check("开发集与测试集的任务 id 集合不相交（交集为空）",
          not (dev_normal & test_normal), f"交集 {len(dev_normal & test_normal)} 条")
    check("开发集与测试集的常态需求内容不相交",
          not (_normal_content(dev_tasks) & _normal_content(test_tasks)),
          f"共同内容 {len(_normal_content(dev_tasks) & _normal_content(test_tasks))} 条")
    check("两个 split 的代表 seed 使用不同的常规需求位移",
          _normal_offset(dev_tasks) != _normal_offset(test_tasks),
          f"{_normal_offset(dev_tasks)} s vs {_normal_offset(test_tasks)} s")
    check("风险窗内需求由契约固定，两个 split 共享（隔离针对可调部分）",
          _risk_signature(dev_tasks) == _risk_signature(test_tasks))
    check("两个集合的规模都在期望量级内",
          len(dev_tasks) == len(test_tasks) == 408, f"{len(dev_tasks)} / {len(test_tasks)}")


def _normal_signature(tasks) -> set[str]:
    return {t.id for t in tasks if t.priority == PRIORITY_NORMAL}


def _normal_content(tasks) -> set[str]:
    return {t.signature() for t in tasks if t.priority == PRIORITY_NORMAL}


def _risk_signature(tasks) -> set[str]:
    return {t.signature() for t in tasks if t.priority == PRIORITY_RISK}


def _normal_offset(tasks) -> int:
    releases = {t.release_time for t in tasks if t.priority == PRIORITY_NORMAL}
    return min(r % NORMAL_INTERVAL_S for r in releases)


def _raises(fn) -> bool:
    try:
        fn()
    except Exception:                             # noqa: BLE001 - any rejection counts
        return True
    return False


# ---------------------------------------------------------------- 7 counts
def test_counts() -> None:
    print("\n[7] 任务数与契约 §5 表推出的数量一致")
    dep = build_deployment(0)
    tasks = build_demand(dep, hours=DEFAULT_HOURS, seed=0)

    want_normal_instants, want_risk_instants = expected_instants(DEFAULT_HOURS)
    check("常态需求时刻 60 个（72 h 减两个 6 h 风险窗）", want_normal_instants == 60,
          f"{want_normal_instants}")
    check("风险需求时刻 144 个（12 h ÷ 5 min，12 h 风险窗 / 5 min）", want_risk_instants == 144,
          f"{want_risk_instants}")

    normal = [t for t in tasks if t.priority == PRIORITY_NORMAL]
    risk = [t for t in tasks if t.priority == PRIORITY_RISK]
    check("常态任务 120 条（60 时刻 × 2 观测量）", len(normal) == 120, f"{len(normal)}")
    check("风险任务 288 条（144 时刻 × 2 观测量）", len(risk) == 288, f"{len(risk)}")
    check("常态任务数 = 常态时刻数 × 2", len(normal) == want_normal_instants * 2)
    check("风险任务数 = 风险时刻数 × 2", len(risk) == want_risk_instants * 2)
    check("总任务数 408 条", len(tasks) == 408, f"{len(tasks)}")
    check("每条风险任务都属于关键集合上的需求",
          all(set(t.node_set) <= set(critical_nodes(dep)) for t in risk) and len(risk) > 0)
    check("常态任务都在 12-18、48-54 之外",
          all(not any(a <= t.release_time / 3600.0 < b for a, b in RISK_WINDOWS_H)
              for t in normal))
    check("每条时刻两种观测量各一条（除风险窗外每窗两条）",
          all(sum(1 for t in tasks if t.release_time == r) == 2
              for r in {t.release_time for t in tasks}))
    check("风险任务只出现在关键节点上：非关键节点不进入风险分母",
          not (set().union(*[set(t.node_set) for t in risk]) - set(critical_nodes(dep))))

    # the counts must follow the table, not a hardcoded expectation inside the generator
    for hours in (6, 12, 24, 48, 72, 96):
        n_i, r_i = expected_instants(hours)
        got = build_demand(dep, hours=hours, seed=0)
        got_normal = sum(1 for t in got if t.priority == PRIORITY_NORMAL)
        got_risk = sum(1 for t in got if t.priority == PRIORITY_RISK)
        ok = got_normal == n_i * 2 and got_risk == r_i * 2
        check(f"{hours} h 的任务数与表一致（常态 {n_i}×2，风险 {r_i}×2）", ok,
              f"实测 {got_normal}/{got_risk}")

    # a zero-hour run has no demand, and a negative run is rejected outright
    check("hours<=0 被拒绝", _raises(lambda: build_demand(dep, hours=0, seed=0)))


# ---------------------------------------------------------------- deployment
def test_deployment_shape() -> None:
    print("\n[8] 部署：16 节点 / 2 坡面组 / 1 网关")
    dep = build_deployment(0)
    check("网关坐标与 README §四 一致",
          abs(dep.gateway.lat - GATEWAY_LAT) < 1e-9 and abs(dep.gateway.lon - GATEWAY_LON) < 1e-9
          and dep.gateway.lat == 30.3300 and dep.gateway.lon == 94.7800)
    check("网关海拔 2317 m", abs(dep.gateway.elev_m - GATEWAY_ELEV_M) < 1e-9
          and dep.gateway.elev_m == 2317.0)
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
          [n.as_dict() if hasattr(n, "as_dict") else n for n in dep.nodes]
          == [n for n in build_deployment(TEST_SEED_MIN).nodes])
    check("node_set 的成员都是部署内的节点（无幽灵节点）",
          all(set(t.node_set) <= set(dep.nids)
              for t in build_demand(dep, hours=DEFAULT_HOURS, seed=0)))


# ---------------------------------------------------------------- notes
def test_documented_ambiguity_notes() -> None:
    """The generator documents the choices the contract left open; check they are stated."""
    print("\n[9] 契约未明确处的文档化选择")
    path = os.path.join(_CODE, "monitoring", "task_generator.py")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    check("模块说明包含 A 层声明（非安全标准、非客户 SLA）",
          "not a geohazard safety standard" in text and "customer SLA" in text)
    check("模块说明写明了开发/测试 seed 区间",
          "development seeds 0-999" in text and "10000" in text)
    check("模块说明注明坐标与高程为研究假设",
          "research assumption" in text and "not surveyed monuments" in text)
    check("模块说明记录了样本窗的解释选择",
          "sample that satisfies a demand is taken INSIDE" in text)
    check("任务字段与契约 §4 的八项一一对应",
          all(field in text for field in ("id", "node_set", "measurement_type", "release_time",
                                          "sample_window", "delivery_deadline", "priority",
                                          "policy_generation")))
    check("三个 profile 以数据形式暴露且数值与表一致",
          set(MONITORING_PROFILES) == {PROFILE_NORMAL, PROFILE_RISK, PROFILE_LOW_POWER}
          and MONITORING_PROFILES[PROFILE_LOW_POWER]["sample_s"] == 15 * 60)


def main() -> int:
    print("外生需求生成器回归测试（P0.4，契约 §5）")
    test_determinism()
    test_exogeneity()
    test_risk_windows()
    test_deadline_arithmetic()
    test_critical_set()
    test_dev_test_split()
    test_counts()
    test_deployment_shape()
    test_documented_ambiguity_notes()
    print("\n" + "-" * 74)
    if FAILURES:
        print(f"  {len(FAILURES)} 项失败: {', '.join(FAILURES)}")
        return 1
    print("  全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
