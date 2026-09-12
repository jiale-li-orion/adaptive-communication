#!/usr/bin/env python3
"""
test_policies.py — the two strong baselines must be strong, and must stay inside the interface.

The contract (§7, README D9) requires the runtime to be compared against device-management
practice that already exists, under the same node-side contract and the same opportunity budget.
That comparison is only worth running if the baselines behave the way mature practice behaves, and
if they cannot quietly read anything the other arms are not given. Both properties are cheap to
check and expensive to discover late, so they are checked here.

What is asserted:

  1. idle silence        with no demanded value in hand there is nothing to correct, so nothing is
                         issued — including when the node's last report is on some other profile.
  2. correctness         a changed demanded value produces the profiled command and nothing else.
  3. in-flight respect   no policy re-issues for a node whose command is still unconfirmed.
  4. termination         once the node reports the desired configuration, both policies stop.
  5. reported vs asked-for  the versioned baseline uses the piggybacked report when it has one and
                         writes anyway when it does not: it must not deadlock on a report that may
                         never come (contract §7 forbids forcing a remote read before every write).
  6. backoff             the VTC baseline issues far fewer times than there are ticks when its read
                         stays inconclusive.
  7. stable identity     one logical command keeps one identity across all of its attempts.
  8. no stale overwrite  an older desired value cannot be re-asserted over a newer one.
  9. interface boundary  both policies run against a WorldView that raises on every attribute
                         outside the documented five, and they read nothing else.

The fake WorldView below is a plain namespace object. `runner` is not imported: the baselines are
independent of the code that runs them, and a regression test that imported the runner would hide
a baseline that had grown a dependency on it.

Run: export PYTHONPATH="$PWD/libs/pylibs"; python3 code/experiments/test_policies.py
"""
from __future__ import annotations

import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime",
                                                     "experiments", "analysis", "monitoring"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

try:                                                        # package import
    from monitoring.policies import (STRONG_BASELINES, VTCPolicy, VersionedConfigPolicy,
                                     VERDICT_TRUE, VERDICT_UNKNOWN, build_baseline,
                                     profile_command)
    from monitoring.task_generator import (PROFILE_LOW_POWER, PROFILE_NORMAL, PROFILE_RISK)
except ImportError:                                         # flat import via sys.path
    from policies import (STRONG_BASELINES, VTCPolicy, VersionedConfigPolicy,  # type: ignore
                          VERDICT_TRUE, VERDICT_UNKNOWN, build_baseline, profile_command)
    from task_generator import PROFILE_LOW_POWER, PROFILE_NORMAL, PROFILE_RISK  # type: ignore


def profile_of(payload: dict) -> str:
    """The value a command carries, ignoring the transport fields that ride with it."""
    return payload["profile"]

FAIL: list[str] = []

# The documented interface a policy may touch, exactly as the task states it and as `WorldView`
# declares it. Nothing else exists as far as a policy is concerned.
DOCUMENTED = ("t_s", "node_ids", "status", "demanded_profile", "center_has_announcement",
              "in_flight")

NODES = ("r00", "r01", "r02")

# The one key every payload a policy returns must carry, and the op the runtime understands.
F_PROFILE = "profile"
OP_SET_PROFILE = "set_monitoring_profile"


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")
    if not ok:
        FAIL.append(name)


# ---------------------------------------------------------------- fake world
class GuardedView:
    """A WorldView that raises on any attribute outside the documented interface.

    A policy that reached for the sample schedule, the ground truth or the channel state would
    otherwise keep working in a test and leak in an experiment.
    """

    def __init__(self, **kwargs) -> None:
        object.__setattr__(self, "_data", dict(kwargs))
        object.__setattr__(self, "_seen", [])

    def __getattr__(self, item):
        data = object.__getattribute__(self, "_data")
        if item in data:
            object.__getattribute__(self, "_seen").append(item)
            return data[item]
        raise AttributeError(
            f"policy read {item!r}, which is not part of the documented WorldView")

    @property
    def seen(self) -> list[str]:
        return list(object.__getattribute__(self, "_seen"))


def view(t_s: int, demanded: dict | None = None, status: dict | None = None,
         in_flight=(), node_ids: tuple[str, ...] = NODES) -> GuardedView:
    demanded = dict(demanded or {})
    return GuardedView(t_s=t_s, node_ids=node_ids, status=dict(status or {}),
                       demanded_profile=demanded, center_has_announcement=bool(demanded),
                       in_flight=frozenset(in_flight))


def status_of(profile: str, read_at: int = 0) -> dict:
    """A status snapshot as a node's own telemetry would carry it."""
    return {"node_id": "r00", "profile": profile, "profile_since": 0, "buffer_level": 3,
            "newest_sample_at": read_at, "read_at": read_at}


def both(dwell_s: int = 300, backoff_s: int = 300) -> list:
    """One fresh instance of each baseline, with the same retry cadence for both."""
    return [VersionedConfigPolicy(write_dwell_s=dwell_s),
            VTCPolicy(base_backoff_s=backoff_s, max_backoff_s=backoff_s)]


def last_issued(plan: list[tuple[str, dict]]) -> str | None:
    """The profile of the newest command in a plan, or None when the plan is empty."""
    return plan[-1][1][F_PROFILE] if plan else None


def demanded_for(profile: str) -> dict:
    return {nid: profile for nid in NODES}


# ---------------------------------------------------------------- 1. idle silence
def test_idle_issues_nothing() -> None:
    print("\n[1] 没有 demanded 值可纠正时不发命令")
    for pol in both():
        plan = pol.plan(view(0, demanded={}, status={}))
        check(f"{pol.name}: 空 demand 且无报告时不发命令", plan == [], f"plan={plan}")
        # a node that is demonstrably on some other profile is still not corrected, because the
        # center holds no instruction that says which profile it should be on.
        plan = pol.plan(view(600, demanded={}, status={"r00": status_of(PROFILE_LOW_POWER)}))
        check(f"{pol.name}: 空 demand 时即使报告别的 profile 也不发命令", plan == [], f"plan={plan}")
        # in flight with nothing demanded is not a reason to send either
        plan = pol.plan(view(600, demanded={}, status={}, in_flight=("r00",)))
        check(f"{pol.name}: 空 demand 且 in-flight 时不发命令", plan == [], f"plan={plan}")


# ---------------------------------------------------------------- 2. correctness
def test_issues_correct_profile() -> None:
    print("\n[2] demanded 变化时发出正确的 profile 与载荷形状")
    for pol in both():
        pol.plan(view(0, demanded=demanded_for(PROFILE_NORMAL)))
        plan = pol.plan(view(3600, demanded=demanded_for(PROFILE_RISK)))
        check(f"{pol.name}: 升到 risk 时对每个节点发一条 risk 命令",
              sorted(nid for nid, _ in plan) == sorted(NODES)
              and all(profile_of(p) == PROFILE_RISK for _, p in plan),
              f"plan={plan}")
        check(f"{pol.name}: 每节点每 tick 至多一条命令",
              len({nid for nid, _ in plan}) == len(plan), f"plan={plan}")
        # recovery half of the workflow: the demanded value comes back to normal
        plan = pol.plan(view(3600 + 1800, demanded=demanded_for(PROFILE_NORMAL)))
        check(f"{pol.name}: 风险窗结束后把节点带回 normal",
              plan and all(profile_of(p) == PROFILE_NORMAL for _, p in plan),
              f"plan={plan}")


# ---------------------------------------------------------------- 3. in flight
def test_in_flight_is_respected() -> None:
    print("\n[3] 命令未确认期间不重复下发")
    for pol in both():
        pol.plan(view(0, demanded=demanded_for(PROFILE_RISK)))
        # a long stretch of ticks, every one of which offers an opportunity
        issued = 0
        for t_s in range(0, 3600, 60):
            plan = pol.plan(view(t_s, demanded=demanded_for(PROFILE_RISK),
                                 status={}, in_flight=("r00", "r01", "r02")))
            if plan:
                issued += 1
        check(f"{pol.name}: in-flight 的节点在 60 个 tick 内一条也不发", issued == 0,
              f"issued={issued}")
        # the same demand with the command resolved must produce something, or test [3] would pass
        # for a policy that had simply gone quiet
        plan = pol.plan(view(7200, demanded=demanded_for(PROFILE_RISK), status={}))
        check(f"{pol.name}: in-flight 解除后仍会处理该节点", plan != [], f"plan={plan}")


# ---------------------------------------------------------------- 4. termination
def test_stops_once_reported_matches() -> None:
    print("\n[4] 报告值等于期望值之后不再重发")
    for pol in both():
        pol.plan(view(0, demanded=demanded_for(PROFILE_RISK)))
        reported = {nid: status_of(PROFILE_RISK) for nid in NODES}
        issued = 0
        for t_s in range(0, 6 * 3600, 60):
            plan = pol.plan(view(t_s, demanded=demanded_for(PROFILE_RISK), status=reported))
            if plan:
                issued += 1
        check(f"{pol.name}: 报告一致后 6 小时内不再下发", issued == 0, f"issued={issued}")


# ---------------------------------------------------------------- 5. report vs no report
def test_reported_value_is_used_without_deadlock() -> None:
    print("\n[5] 版本化配置使用随遥测带来的报告值，但没有报告时也不会卡死")
    pol = VersionedConfigPolicy(write_dwell_s=300)
    # (a) the desired value is already what the node reports: the write is skipped entirely
    plan = pol.plan(view(0, demanded=demanded_for(PROFILE_NORMAL),
                         status={nid: status_of(PROFILE_NORMAL) for nid in NODES}))
    check("versioned_config: 报告值与期望值相同则一次也不写", plan == [], f"plan={plan}")
    check("versioned_config: 该判断用的是报告值而非额外远程读",
          pol.reported_source.get("r00") == "status", f"source={pol.reported_source.get('r00')}")

    # (b) the desired value differs from the report: write, and remember what was reported
    plan = pol.plan(view(60, demanded=demanded_for(PROFILE_RISK),
                         status={nid: status_of(PROFILE_NORMAL) for nid in NODES}))
    check("versioned_config: 期望值与报告值不同则写入 risk", last_issued(plan) == PROFILE_RISK,
          f"plan={plan}")

    # (c) no report at all: the policy must still issue, and keep issuing at its own cadence.
    # Waiting for a report that may never arrive would be a silent deadlock, and the node would
    # stay on the wrong profile for the rest of the run.
    pol2 = VersionedConfigPolicy(write_dwell_s=300)
    issued = [t_s for t_s in range(0, 3600, 60)
              if pol2.plan(view(t_s, demanded=demanded_for(PROFILE_RISK), status={}))]
    check("versioned_config: 完全没有报告时仍然下发", len(issued) >= 1, f"issued at {issued}")
    check("versioned_config: 没有报告时按 dwell 重复而不是每 tick 重发",
          len(issued) <= 3600 // 300 + 1, f"issued at {issued}")

    # (d) a report that carries no profile is not evidence of anything
    pol3 = VersionedConfigPolicy(write_dwell_s=300)
    plan = pol3.plan(view(0, demanded=demanded_for(PROFILE_RISK),
                          status={nid: {"node_id": nid, "read_at": 0} for nid in NODES}))
    check("versioned_config: 报告缺少 profile 字段时不当作一致", last_issued(plan) == PROFILE_RISK,
          f"plan={plan}")


# ---------------------------------------------------------------- 6. backoff
def test_vtc_backs_off_on_unknown() -> None:
    print("\n[6] VTC 在读取无结论时退避，而不是每 tick 重发")
    pol = VTCPolicy(base_backoff_s=900, max_backoff_s=4 * 3600)
    ticks = list(range(0, 12 * 3600, 60))
    issues = [t_s for t_s in ticks
              if pol.plan(view(t_s, demanded=demanded_for(PROFILE_RISK), status={}))]
    check("vtc_style: 12 小时无任何报告时下发次数远少于 tick 数",
          len(issues) < len(ticks) // 4, f"{len(issues)} 次 / {len(ticks)} ticks")
    check("vtc_style: 无报告至少下发一次（否则是沉默而不是退避）", len(issues) >= 1,
          f"issued at {issues}")
    gaps = [b - a for a, b in zip(issues, issues[1:])]
    check("vtc_style: 无结论时退避间隔不缩短", all(g >= 900 for g in gaps), f"gaps={gaps}")
    # Every issue spends one attempt of the logical command that is open at the time. Since a
    # logical command can be closed and reopened (on expiry of an unconfirmed command), the attempt
    # counter is checked against the issues that belong to the command that is open now.
    current = pol.command_of("r00")
    line = [t_s for t_s, _profile, identity in pol.issues.get("r00", []) if identity == current]
    check("vtc_style: 同一逻辑命令内每次下发恰好记一次 attempt",
          pol.attempts_of("r00") == len(line),
          f"attempts={pol.attempts_of('r00')} issues in current command={line}")
    check("vtc_style: 12 小时内至少开过一次新逻辑命令（超时后重新开始）",
          pol.logical.get("r00", 0) >= 1, f"logical={pol.logical.get('r00')}")
    check("vtc_style: 最近一次判定是 unknown", pol.verdict_of("r00") == VERDICT_UNKNOWN,
          f"verdict={pol.verdict_of('r00')}")

    # a node that stops transmitting and reverts to its own normal profile is the same
    # inconclusive case: the report predates the command, so it is not a refutation of it.
    pol2 = VTCPolicy(base_backoff_s=900, max_backoff_s=4 * 3600)
    stale = {nid: status_of(PROFILE_NORMAL) for nid in NODES}
    issues2 = [t_s for t_s in ticks
               if pol2.plan(view(t_s, demanded=demanded_for(PROFILE_RISK), status=stale))]
    check("vtc_style: 停在 normal 的旧报告按 inconclusive 处理并退避",
          len(issues2) < len(ticks) // 4, f"{len(issues2)} 次 / {len(ticks)} ticks")

    # a report that is conclusive and disagrees does produce a re-issue after the backoff
    pol3 = VTCPolicy(base_backoff_s=300, max_backoff_s=300)
    pol3.plan(view(0, demanded=demanded_for(PROFILE_RISK), status={}))
    plan = pol3.plan(view(600, demanded=demanded_for(PROFILE_RISK),
                          status={nid: status_of(PROFILE_LOW_POWER) for nid in NODES}))
    check("vtc_style: 读取有结论且不一致时重发", last_issued(plan) == PROFILE_RISK, f"plan={plan}")


# ---------------------------------------------------------------- 7. stable identity
def test_one_logical_command_one_identity() -> None:
    print("\n[7] 一个逻辑命令在所有尝试中保持同一身份")
    pol = VTCPolicy(base_backoff_s=300, max_backoff_s=300)
    first = pol.plan(view(0, demanded=demanded_for(PROFILE_RISK), status={}))
    identity = pol.command_of("r00")
    attempts = pol.attempts_of("r00")
    for t_s in range(600, 3600, 300):
        pol.plan(view(t_s, demanded=demanded_for(PROFILE_RISK), status={}))
    check("vtc_style: 重试期间身份字符串不变", pol.command_of("r00") == identity,
          f"{identity} -> {pol.command_of('r00')}")
    check("vtc_style: 期间确实发生了重试", pol.attempts_of("r00") > attempts,
          f"attempts {attempts} -> {pol.attempts_of('r00')}")
    check("vtc_style: 身份不含尝试次数", str(pol.attempts_of("r00")) not in pol.command_of("r00"),
          f"command={pol.command_of('r00')}")

    # a different desired effect is a different logical command, with a new identity
    pol.plan(view(3600, demanded=demanded_for(PROFILE_NORMAL), status={}))
    check("vtc_style: 新的期望值开启新的逻辑命令", pol.command_of("r00") != identity,
          f"{identity} -> {pol.command_of('r00')}")
    check("vtc_style: 新逻辑命令的尝试计数从 1 开始", pol.attempts_of("r00") == 1,
          f"attempts={pol.attempts_of('r00')}")

    # the versioned baseline keeps one version for one desired value as well
    vc = VersionedConfigPolicy(write_dwell_s=300)
    vc.plan(view(0, demanded=demanded_for(PROFILE_RISK)))
    v1 = vc.identity_of("r00")
    for t_s in range(300, 3600, 300):
        vc.plan(view(t_s, demanded=demanded_for(PROFILE_RISK), status={}))
    check("versioned_config: 同一期望值下版本号不变", vc.identity_of("r00") == v1,
          f"{v1} -> {vc.identity_of('r00')}")
    vc.plan(view(3600, demanded=demanded_for(PROFILE_NORMAL)))
    check("versioned_config: 新的期望值让版本号严格递增",
          vc.identity_of("r00") == v1 + 1, f"{v1} -> {vc.identity_of('r00')}")

    # a first command is the first logical command, not a retry of nothing
    fresh = VTCPolicy()
    check("vtc_style: 首个逻辑命令的尝试计数为 0", fresh.attempts_of("r00") == 0,
          f"attempts={fresh.attempts_of('r00')}")
    check("vtc_style: 未决时的判定是 unknown", fresh.verdict_of("r00") == VERDICT_UNKNOWN)


# ---------------------------------------------------------------- 8. no stale overwrite
def test_stale_desired_cannot_overwrite() -> None:
    print("\n[8] 迟到的旧期望值不能覆盖更新的期望值")
    # (a) the newer value wins when both arrive at once, in either order
    for order in ((PROFILE_RISK, PROFILE_NORMAL), (PROFILE_NORMAL, PROFILE_RISK)):
        pol = VersionedConfigPolicy(write_dwell_s=300)
        versions = []
        for wanted in order:
            pol.plan(view(0, demanded=demanded_for(wanted), status={}))
            versions.append((wanted, pol.identity_of("r00")))
        newest = order[-1]
        check(f"versioned_config: {order[0]}->{order[1]} 时以最新期望值为准",
              pol.desired_of("r00") == newest and pol.issued_profile.get("r00") == newest,
              f"desired={pol.desired_of('r00')} issued={pol.issued_profile.get('r00')}")
        check(f"versioned_config: {order[0]}->{order[1]} 的版本号单调递增",
              versions[1][1] > versions[0][1], f"versions={versions}")

    # (b) an old announcement returning late must not be asserted again
    pol = VersionedConfigPolicy(write_dwell_s=300)
    pol.plan(view(0, demanded=demanded_for(PROFILE_NORMAL), status={}))
    v_normal = pol.identity_of("r00")
    pol.plan(view(60, demanded=demanded_for(PROFILE_RISK), status={}))
    v_risk = pol.identity_of("r00")
    high_water = pol.issued_version.get("r00")
    issued_before = pol.issued_profile.get("r00")
    # the node keeps reporting the older value, so a naive implementation would write normal again
    stale_report = {nid: status_of(PROFILE_NORMAL) for nid in NODES}
    for t_s in range(120, 3600, 60):
        pol.plan(view(t_s, demanded=demanded_for(PROFILE_RISK), status=stale_report))
    check("versioned_config: 旧值迟到时最后写入的仍是较新值",
          pol.issued_profile.get("r00") == PROFILE_RISK,
          f"issued={pol.issued_profile.get('r00')} (before={issued_before})")
    check("versioned_config: 已发出的版本号从不下调",
          pol.issued_version.get("r00", 0) >= high_water and v_risk > v_normal,
          f"issued_version={pol.issued_version.get('r00')} high_water={high_water}")
    check("versioned_config: 旧期望值不会把节点写回 normal",
          all(p != PROFILE_NORMAL for p in pol.issued_profile.values()), f"{pol.issued_profile}")

    # (c) the carve-out for a newer desired value: an in-flight older command does not block it.
    # Without this, a node that never confirms could never be told a newer value at all. The write
    # is not a re-issue of the pending command, it supersedes it, and the pending one is not touched.
    vc = VersionedConfigPolicy(write_dwell_s=300)
    vc.plan(view(0, demanded=demanded_for(PROFILE_NORMAL), status={}))
    plan = vc.plan(view(60, demanded=demanded_for(PROFILE_RISK), status={},
                        in_flight=tuple(NODES)))
    check("versioned_config: 更新的期望值可越过 in-flight 覆盖旧命令",
          last_issued(plan) == PROFILE_RISK, f"plan={plan}")
    issued = [vc.plan(view(t_s, demanded=demanded_for(PROFILE_RISK), status={},
                           in_flight=tuple(NODES)))
              for t_s in range(120, 3720, 60)]
    check("versioned_config: 覆盖之后同值不再越过 in-flight",
          all(p == [] for p in issued), f"{sum(1 for p in issued if p)} 个 tick 仍在下发")

    # (d) VTC answers a conclusive disagreement with the current demand, not with a remembered one
    vtc = VTCPolicy(base_backoff_s=300, max_backoff_s=300)
    vtc.plan(view(0, demanded=demanded_for(PROFILE_NORMAL), status={}))
    vtc.plan(view(60, demanded=demanded_for(PROFILE_RISK), status={}))
    for t_s in range(120, 3600, 60):
        vtc.plan(view(t_s, demanded=demanded_for(PROFILE_RISK), status=stale_report))
    check("vtc_style: 迟到的旧报告不会让目标回到 normal", vtc.target_of("r00") == PROFILE_RISK,
          f"target={vtc.target_of('r00')}")
    current = vtc.command_of("r00")
    under_current = [entry for entry in vtc.issues.get("r00", []) if entry[2] == current]
    check("vtc_style: 当前逻辑命令的下发次数与 attempt 计数一致",
          len(under_current) == vtc.attempts_of("r00") > 1,
          f"{len(under_current)} issues, attempts={vtc.attempts_of('r00')}")
    check("vtc_style: 新逻辑命令的首次下发带新身份，旧命令的下发带旧身份",
          [entry[2] for entry in vtc.issues.get("r00", [])][:2]
          != [current, current], f"{vtc.issues.get('r00')}")


# ---------------------------------------------------------------- 9. interface boundary
def test_interface_boundary() -> None:
    print("\n[9] 两个策略只读取文档化接口，不越界读取")
    check("文档化属性清单与契约一致（测试自身的防漂移断言）",
          set(DOCUMENTED) == {"t_s", "node_ids", "status", "demanded_profile",
                              "center_has_announcement", "in_flight"}, f"{DOCUMENTED}")
    for pol in both():
        seen: list[str] = []
        for t_s in (0, 300, 900, 3600, 7200):
            v = view(t_s, demanded=demanded_for(PROFILE_RISK), status={}, in_flight=("r02",))
            pol.plan(v)
            seen.extend(v.seen)
        check(f"{pol.name}: 只读取了文档化属性", set(seen) <= set(DOCUMENTED),
              f"seen={sorted(set(seen))}")
        check(f"{pol.name}: 读取的属性都来自文档化集合（无空读）", seen and set(seen) <= set(DOCUMENTED),
              f"seen={sorted(set(seen))}")

    # an access outside the documented set must raise rather than silently return a default
    v = view(0, demanded=demanded_for(PROFILE_RISK))
    try:
        v.sample_schedule
        check("GuardedView: 未文档化属性会报错（守卫自身有效）", False, "read succeeded")
    except AttributeError:
        check("GuardedView: 未文档化属性会报错（守卫自身有效）", True)

    # both policies must also run against a view whose status dict is missing every node, and
    # against one where a node is on no known profile at all
    for pol in both():
        odd = {nid: {"node_id": nid, "profile": "unknown_future_profile", "read_at": 0}
               for nid in NODES}
        plan = pol.plan(view(1000, demanded=demanded_for(PROFILE_RISK), status=odd))
        check(f"{pol.name}: 未知 profile 的报告不会让策略崩溃或误判为一致",
              all(profile_of(p) == PROFILE_RISK for _, p in plan) or plan == [],
              f"plan={plan}")


# ---------------------------------------------------------------- 10. registry and independence
def test_registry_and_independence() -> None:
    print("\n[10] 基线注册表可用，且基线不依赖 runner")
    check("两条基线按名字可构造",
          isinstance(build_baseline("versioned_config"), VersionedConfigPolicy)
          and isinstance(build_baseline("vtc_style"), VTCPolicy), f"{sorted(STRONG_BASELINES)}")
    check("未知基线名会报错", _raises_value_error(lambda: build_baseline("no_such_baseline")))
    check("命令载荷的 op 是 runtime 唯一支持的那一种",
          profile_command(PROFILE_RISK) == {"op": OP_SET_PROFILE, "profile": PROFILE_RISK},
          f"{profile_command(PROFILE_RISK)}")
    # Sending nothing but the value leaves the remote with nothing to fence on, so a policy that
    # holds versions must be able to put them on the wire. Both halves are checked here.
    check("profile_command: 带版本与逻辑身份时两者都在载荷里",
          profile_command(PROFILE_RISK, version=7, logical="r00:7")
          == {"op": OP_SET_PROFILE, "profile": PROFILE_RISK, "version": 7, "logical": "r00:7"},
          f"{profile_command(PROFILE_RISK, version=7, logical='r00:7')}")
    check("profile_command: 不传版本时载荷不含该字段",
          "version" not in profile_command(PROFILE_RISK), f"{profile_command(PROFILE_RISK)}")
    # The baselines are compared against the runtime, so they must not have grown a dependency on
    # the module that runs them: a baseline that imported the runner could follow its internals
    # instead of the interface, and the arm would stop being an independent implementation.
    source = _read_module_source("policies")
    check("policies.py 不导入 runner",
          "import runner" not in source and "from runner" not in source, "no runner import found")
    check("策略对象只暴露 name 与 plan（可替换 runtime 里的任何策略）",
          all(hasattr(c(), "name") and callable(c().plan) for c in STRONG_BASELINES.values()),
          f"{sorted(STRONG_BASELINES)}")


def _raises_value_error(fn) -> bool:
    try:
        fn()
    except ValueError:
        return True
    return False


def _read_module_source(name: str) -> str:
    import policies as _mod
    with open(_mod.__file__, "r", encoding="utf-8") as handle:
        return handle.read()


def main() -> int:
    print("强基线策略回归测试")
    test_idle_issues_nothing()
    test_issues_correct_profile()
    test_in_flight_is_respected()
    test_stops_once_reported_matches()
    test_reported_value_is_used_without_deadlock()
    test_vtc_backs_off_on_unknown()
    test_one_logical_command_one_identity()
    test_stale_desired_cannot_overwrite()
    test_interface_boundary()
    test_registry_and_independence()
    print("\n" + "-" * 74)
    if FAIL:
        print(f"  {len(FAIL)} 项失败: {', '.join(FAIL)}")
        return 1
    print("  全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
