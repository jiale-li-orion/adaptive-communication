#!/usr/bin/env python3
"""实例层验收：最小闭环的五条手工可核算性质。

这一份是实例层**唯一**的测试文件，只查那些手工能算出来、而且算错了不会自己报错的性质。
它不替代 `run_checks.py` 里的既有 16 项；实例层在 `run_checks.py` 里登记为第 17 项。

查什么，以及为什么每一条都值得查：

  1. 义务在运行前定好        D 由外生输入生成，运行过程中不被改；改变策略不改变分母
  2. 失电不补造样本          无电期间没有样本，且义务仍留在分母里（不是"没采就不算"）
  3. 旧数据不冒充事件观测    窗外的样本不计入该义务；同一样本不能占满三个名额
  4. 遥测不提前到达          采集 ≤ 网关听到 ≤ 中心收到，逐条成立
  5. 手算数目对上            12 h 片段实例 = 12 常态 + 7×3 事件；规则义务 21/21 被采集满足

外加一条**反向**检查：把事件上报关掉，事件交付率必须下降。一个恒为 0 或恒为 1 的列不能拿来做
扫描，所以这里证明这列真的会动。

Run: export PYTHONPATH="$PWD/libs/pylibs"; python3 code/experiments/test_instance.py
"""
from __future__ import annotations

import os as _os, sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime", "experiments",
                                                      "analysis", "monitoring", "instance"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

from deployment import build_deployment
from exogenous import (KIND_EVENT, KIND_ROUTINE, EnvironmentTruth, ObligationSet,
                       constant_harvest,
                       displacement_series, rule_obligations_for_truth,
                       routine_obligations, routine_obligations_by_node,
                       wang_burst_obligations, wang_fragment_truth)
from network import DeviceProfile, HopLog, Instance, Node, nodes_from
from scoring import evaluate, event_propagation

FAIL: list[str] = []

# 片段实例的公共参数。全部集中在顶部，测试里不再散落魔数。
HOURS = 12
NODE = "EI01"
TRIGGERS = 7
SLOTS_PER_TRIGGER = 3
EXPECTED_ROUTINE_SAMPLES = HOURS            # 每 3600 s 一次
EXPECTED_EVENT_SAMPLES = TRIGGERS * SLOTS_PER_TRIGGER


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")
    if not ok:
        FAIL.append(name)


def build(harvest_wh_per_hour: float = 2.0, temp_c: float | None = 10.0,
          report_period_s: int = 3600, upload_on_event: bool = True,
          initial_wh: float | None = None, seed: int = 0):
    """建一个片段实例。所有用例走同一条构造路径，避免各测各的。

    电量用**绝对 Wh** 表达（`initial_wh`），与 manifest 的说法一致。
    """
    dp = DeviceProfile(report_period_s=report_period_s, upload_on_event=upload_on_event)
    nodes = {NODE: Node(NODE, "rainfall", dp, initial_wh=initial_wh)}
    truth = wang_fragment_truth(0, HOURS, (NODE,))
    harvest, temp = constant_harvest((NODE,), HOURS, harvest_wh_per_hour, temp_c)
    truth.harvest_wh, truth.temp_c = harvest, temp
    inst = Instance(nodes, truth, seed=seed)
    log = inst.run(HOURS)
    return nodes, truth, inst, log


def obligations(truth) -> ObligationSet:
    return ObligationSet(rule_obligations_for_truth(truth))


# ------------------------------------------------------------------ 1 分母外生

def test_denominator_is_exogenous() -> None:
    print("\n[1] 义务在运行前定好，改变策略不改变分母")
    _n1, t1, _i1, _l1 = build(upload_on_event=True)
    D1 = obligations(t1)
    _n2, t2, _i2, _l2 = build(upload_on_event=False)
    D2 = obligations(t2)
    ids1 = sorted(o.oid for o in D1.obligations)
    ids2 = sorted(o.oid for o in D2.obligations)
    check("同一外生输入给出同一份义务集", ids1 == ids2, f"{len(ids1)} 条")
    # 义务集由触发直接生成，构造它的函数只读 truth.triggers
    check("触发数 × 名额数 = 事件义务数",
          len(D1) == TRIGGERS * SLOTS_PER_TRIGGER,
          f"{TRIGGERS} x {SLOTS_PER_TRIGGER} = {len(D1)}")


# ------------------------------------------------------------------ 2 失电不补造

def test_blackout_invents_nothing() -> None:
    """节点在运行**中途**失电。

    比"从一开始就没电"强的地方在于：它能同时查出三件事——死亡之后不再产生样本、死亡时刻之前的
    样本照常存在、以及死亡之后的义务**仍留在分母里**（不是"没采就不算"）。
    电量按**绝对 Wh** 给：0.3 mWh 够采几条就断电。
    """
    print("\n[2] 失电不补造样本，且义务仍留在分母里")
    # 0.3 mWh ≈ 够采几条就断电（单条采样 2e-5 Wh、单次上行空口 ~2e-5 Wh）
    nodes, truth, inst, log = build(harvest_wh_per_hour=0.0, temp_c=None,
                                    initial_wh=3e-4)
    node = nodes[NODE]
    D = obligations(truth)
    res = evaluate(D, log, HOURS, nodes.keys(), battery={NODE: node.power.to_dict()},
                   plane=inst.plane)

    check("节点在运行中途判死", not node.alive and node.dead_at is not None
          and 0 < node.dead_at < HOURS * 3600, f"dead_at={node.dead_at}s")
    check("死亡之后没有任何样本",
          all(s.taken_at <= node.dead_at for s in log.samples.values()),
          f"{len(log.samples)} 条，最晚 {max((s.taken_at for s in log.samples.values()), default=None)}s")
    check("死亡之前确实采到了样本（不是空跑）", len(log.samples) > 0,
          f"{len(log.samples)} 条")
    check("义务一条都没少（不因没采而免于评分）", len(D) == TRIGGERS * SLOTS_PER_TRIGGER,
          f"{len(D)} 条")
    ev = res["by_kind"][KIND_EVENT]
    check("未采到的记为采集缺失，而不是从分母消失",
          ev["missing_collection"] > 0
          and ev["missing_collection"] + ev["collected"] == ev["n"],
          f"缺采 {ev['missing_collection']} / 已采 {ev['collected']} / 共 {ev['n']}")
    check("失电时长被记进电量账本", node.power.deficit_s > 0,
          f"deficit={node.power.deficit_s}s")


# ------------------------------------------------------------------ 3 旧数据不冒充

def test_stale_cannot_impersonate() -> None:
    print("\n[3] 旧数据不冒充事件观测；同一样本不占满三个名额")
    _n, truth, _i, log = build()
    D = obligations(truth)
    samples = list(log.samples.values())

    # 每条义务各自匹配到几个样本
    hits: dict[str, list[str]] = {o.oid: [] for o in D.obligations}
    for o in D.obligations:
        for s in samples:
            if o.matches(s):
                hits[o.oid].append(s.sample_id)

    over = {oid: v for oid, v in hits.items() if len(v) > 1}
    check("没有任何义务被多个样本同时匹配", not over, f"越界 {len(over)} 条")

    from collections import Counter
    used = Counter(sid for v in hits.values() for sid in v)
    shared = {sid: c for sid, c in used.items() if c > 1}
    check("没有任何样本被多条义务共用（三个名额各用不同样本）", not shared,
          f"共用 {len(shared)} 个")

    # 直接构造：一条窗在 [1000,1000] 的义务，窗外的样本必须不匹配
    one = [o for o in D.obligations if o.window == (o.window[0], o.window[0])][0]
    outside = [s for s in samples if abs(s.taken_at - one.window[0]) > one.tolerance_s]
    check("窗外样本一律不匹配", bool(outside) and not any(one.matches(s) for s in outside),
          f"窗外样本 {len(outside)} 条")


# ------------------------------------------------------------------ 4 三时刻单调

def test_no_early_arrival() -> None:
    print("\n[4] 遥测不提前到达：采集 ≤ 网关听到 ≤ 中心收到")
    _n, _t, _i, log = build()
    early_gw = [sid for sid, tr in log.transit.items()
                if tr.heard_at is not None and tr.heard_at < log.samples[sid].taken_at]
    early_c = [sid for sid, tr in log.transit.items()
               if tr.received_at is not None
               and (tr.heard_at is None or tr.received_at < tr.heard_at)]
    check("没有样本早于采集时刻到达网关", not early_gw, f"{len(early_gw)} 条")
    check("没有样本早于网关听到就到达中心", not early_c, f"{len(early_c)} 条")
    check("确实有样本走完了三段（不是空跑）",
          sum(1 for tr in log.transit.values() if tr.received_at is not None) > 0)


# ------------------------------------------------------------------ 5 手算

def test_hand_counted_numbers() -> None:
    print("\n[5] 手算数目对上")
    nodes, truth, inst, log = build()
    total = len(log.samples)
    check("样本总数 = 常态 + 事件",
          total == EXPECTED_ROUTINE_SAMPLES + EXPECTED_EVENT_SAMPLES,
          f"{total} = {EXPECTED_ROUTINE_SAMPLES} + {EXPECTED_EVENT_SAMPLES}")

    D = obligations(truth)
    matched = sum(1 for o in D.obligations
                  if any(o.matches(s) for s in log.samples.values()))
    check("规则事件义务全部被采集满足", matched == len(D), f"{matched}/{len(D)}")

    # 触发吸附：原始时刻保留，误差不超过半个 tick
    errs = [abs(a - b) for (a, _), (b, _) in zip(truth.trigger_originals, truth.triggers)]
    check("触发吸附误差不超过半个 tick", errs and max(errs) <= 30,
          f"max={max(errs)}s（上界 30）")
    check("原始触发时刻被保留", len(truth.trigger_originals) == TRIGGERS,
          f"{len(truth.trigger_originals)} 条")

    # 周期义务与事件义务分列，不合并成一个覆盖分数
    res = evaluate(D, log, HOURS, nodes.keys(),
                   battery={NODE: nodes[NODE].power.to_dict()}, plane=inst.plane)
    check("结果里没有合成分数字段",
          not any(k in res for k in ("score", "total_score", "coverage")))
    check("不适用项返回 None 而不是 0",
          res["config_mismatch_s"] is None and "config_mismatch_s" in res["not_applicable"])


# ------------------------------------------------------------------ 反向检查

def test_event_column_actually_moves() -> None:
    print("\n[6] 反向检查：事件交付率这一列真的会动")
    _n, truth, _i, log_on = build(upload_on_event=True)
    D = obligations(truth)
    _n2, truth2, _i2, log_off = build(upload_on_event=False)
    D2 = obligations(truth2)
    res_on = evaluate(D, log_on, HOURS, {NODE}, plane=None)
    res_off = evaluate(D2, log_off, HOURS, {NODE}, plane=None)
    d_on = res_on["by_kind"][KIND_EVENT]["delivered"]
    d_off = res_off["by_kind"][KIND_EVENT]["delivered"]
    check("关掉本地事件上报后，事件交付数下降",
          d_off < d_on, f"开={d_on} 关={d_off}（各 {TRIGGERS * SLOTS_PER_TRIGGER} 条）")


def test_routine_and_fragment() -> None:
    print("\n[7] 周期义务与公开片段解析")
    ro = routine_obligations((NODE,), hours=2)
    check("周期义务数 = 对象数 x 小时数", len(ro) == 2, f"{len(ro)} 条")
    check("周期义务类别正确", all(o.kind == KIND_ROUTINE for o in ro))

    frag = wang_burst_obligations(day_offset_s=0)
    check("公开片段解析出 7 组", len(frag) // SLOTS_PER_TRIGGER == TRIGGERS)
    gaps = [frag[i * 3 + k + 1].window[0] - frag[i * 3 + k].window[0]
            for i in range(TRIGGERS) for k in range(SLOTS_PER_TRIGGER - 1)]
    check("片段的名义间隔为 300 s，实际 286–318 s 全部保留",
          len(gaps) == TRIGGERS * 2 and min(gaps) >= 280 and max(gaps) <= 320,
          f"{len(gaps)} 个间隔, {min(gaps)}–{max(gaps)} s（未吸附成理想时钟）")


# ------------------------------------------------------------------ 8 多节点与真实地形

def test_multinode_terrain() -> None:
    """多节点 + 真实地形：可达性是外生事实，且量纲上自洽。

    这一组要查的是**结构**，不是性能：一个实体不该被要求提供它没有的测项；绕射边缘上的位点
    不该当成地形事实；网关上的雨量计没有接入跳。
    """
    print("\n[8] 多节点与真实地形")
    dep = build_deployment(groups=2)
    check("排除绕射边缘位点后主实例非空",
          len(dep.node_ids) > 0, f"主实例 {len(dep.node_ids)} 个，排除 {len(dep.marginal)} 个")
    check("被排除的位点被单列出来（不是静默丢掉）",
          all(m in {n.sid for n in dep.nodes} for m in dep.marginal),
          f"marginal={sorted(dep.marginal)}")

    nodes = nodes_from(dep)
    check("网关作为独立实体在场，且测项是雨量",
          dep.gateway.sid in nodes and nodes[dep.gateway.sid].measurand == "rainfall"
          and nodes[dep.gateway.sid].is_gateway)
    check("坡面节点是位移测项",
          all(n.measurand == "displacement" for k, n in nodes.items()
              if k != dep.gateway.sid))

    meas = {k: v.measurand for k, v in nodes.items()}
    D = ObligationSet(routine_obligations_by_node(meas, HOURS))
    asked = {(o.node_id, o.measurand) for o in D.obligations}
    provided = {(k, v.measurand) for k, v in nodes.items()}
    check("没有任何实体被要求提供它没有的测项", asked <= provided,
          f"越界 {sorted(asked - provided)}")
    check("周期义务数 = 实体数 x 小时数",
          len(D) == len(nodes) * HOURS, f"{len(D)} = {len(nodes)} x {HOURS}")


def test_multinode_run() -> None:
    """多节点闭环跑一遍：分列读数自洽，且没有整段无观测这种结构性错误。"""
    print("\n[9] 多节点闭环")
    dep = build_deployment(groups=2)
    nodes = nodes_from(dep)
    truth = wang_fragment_truth(0, HOURS, ("gw0",))
    truth.displacement = displacement_series(nodes.keys(), HOURS, 0)
    harvest, temp = constant_harvest(nodes.keys(), HOURS, 3.0, 10.0)
    truth.harvest_wh.update(harvest)
    truth.temp_c.update(temp)

    meas = {k: v.measurand for k, v in nodes.items()}
    D = ObligationSet(routine_obligations_by_node(meas, HOURS)
                      + rule_obligations_for_truth(truth))
    inst = Instance(nodes, truth, seed=0)
    log = inst.run(HOURS)
    res = evaluate(D, log, HOURS, nodes.keys(),
                   battery={k: v.power.to_dict() for k, v in nodes.items()},
                   plane=inst.plane)

    rt = res["routine"]
    check("周期侧没有任何实体整段无观测", rt["no_observation_s"] == 0,
          f"aoi_mean={rt['aoi_mean_s']:.0f}s, no_obs={rt['no_observation_s']}s")
    check("缺采与已采相加等于分母",
          rt["missing_collection"] + rt["n"] - rt["missing_delivery"] - rt["censored"]
          == rt["delivered"], f"缺采 {rt['missing_collection']} / 缺送 {rt['missing_delivery']}")
    check("事件名额全部被采集满足",
          res["event"]["slots_matched_by_collection"] == res["event"]["n_slots"],
          f"{res['event']['slots_matched_by_collection']}/{res['event']['n_slots']}")

    # 网关传感器的区别**不是"听到时刻等于采集时刻"**——缓存里更早的样本会在本次上报时被一起
    # 发出，因此 heard_at 晚于 taken_at 是正常的缓冲行为。真正的区别是**没有接入跳，因此没有接入丢失**：
    # 网关采到的样本一条都不会丢在接入上（只要缓存没溢出）。
    gw = dep.gateway.sid
    gw_samples = [sid for sid, smp in log.samples.items() if smp.node_id == gw]
    gw_heard = [sid for sid in gw_samples if log.transit[sid].heard_at is not None]
    check("网关传感器没有接入跳：采到的样本全部进入网关缓存",
          len(gw_heard) == len(gw_samples),
          f"{len(gw_heard)}/{len(gw_samples)}（坡面节点会因接入丢失而少于此数）")
    slope_heard = [sid for sid, smp in log.samples.items()
                   if smp.node_id != gw and log.transit[sid].heard_at is not None]
    slope_all = [sid for sid, smp in log.samples.items() if smp.node_id != gw]
    check("坡面节点确实有接入丢失（否则这一列没有区分力）",
          len(slope_heard) < len(slope_all),
          f"坡面听到 {len(slope_heard)}/{len(slope_all)}")


# ------------------------------------------------------------------ 10 传播与删失

def test_propagation_splits_the_two_latencies() -> None:
    """触发 → 检测 → 获知必须分开计时，否则"本地没检测到"会被读成"通信慢"。"""
    print("\n[10] 事件传播：检测与获知分开计时")
    _n, truth, inst, log = build()
    pg = event_propagation(truth, log)

    check("每个触发都有一条传播记录", pg["n_triggers"] == TRIGGERS, f"{pg['n_triggers']}")
    check("检测时刻不早于源触发时刻",
          all(r["detected_at"] is None or r["detected_at"] >= r["source_at"]
              for r in pg["per_trigger"]))
    check("获知时刻不早于检测时刻",
          all(r["knowledge_at"] is None or r["detected_at"] is None
              or r["knowledge_at"] >= r["detected_at"] for r in pg["per_trigger"]))
    check("两项时延确实分开报，且不相等",
          pg["knowledge_latency_mean_s"] is not None
          and pg["knowledge_latency_mean_s"] > pg["detection_latency_mean_s"],
          f"检测 {pg['detection_latency_mean_s']:.0f}s vs 获知 "
          f"{pg['knowledge_latency_mean_s']:.0f}s")


def test_tail_decides_what_may_be_judged() -> None:
    """尾部观察期决定**哪些义务可以被判定**，而不是"跑完就算失败"。"""
    print("\n[11] 尾部观察期与右删失")
    # **直接测判定规则，不依赖投递是否走运。** 用一个空记录：没有样本，因此每条义务都既未采集
    # 也未交付，唯一的区别只剩"它的观察截止在不在运行末之前"。
    D = ObligationSet(routine_obligations(("a",), hours=2))    # 截止 7200 与 10800
    empty = HopLog()

    short = evaluate(D, empty, 1, ("a",), plane=None, task_hours=2)["observation_window"]
    full = evaluate(D, empty, 3, ("a",), plane=None, task_hours=2)["observation_window"]

    check("观察截止超出运行末的义务标右删失（手工：2 条都超）",
          short["censored_total"] == 2, f"运行 1h 删失 {short['censored_total']}")
    check("运行覆盖全部截止后不再有删失（手工：0 条）",
          full["censored_total"] == 0, f"运行 3h 删失 {full['censored_total']}")
    check("删失的留在分母里，没有被剔掉",
          short["task_hours"] == full["task_hours"] == 2, f"task_hours={short['task_hours']}")
    check("尾部长度被如实报出（运行 3h - 义务 2h = 1h）",
          full["run_hours"] - full["task_hours"] == 1 and full["tail_s"] == 3600,
          f"run={full['run_hours']}h task={full['task_hours']}h tail={full['tail_s']}s")


def main() -> int:
    print("实例层验收（Task Contract v1.1）")
    test_denominator_is_exogenous()
    test_blackout_invents_nothing()
    test_stale_cannot_impersonate()
    test_no_early_arrival()
    test_hand_counted_numbers()
    test_event_column_actually_moves()
    test_routine_and_fragment()
    test_multinode_terrain()
    test_multinode_run()
    test_propagation_splits_the_two_latencies()
    test_tail_decides_what_may_be_judged()
    print("\n" + "-" * 74)
    if FAIL:
        print(f"  {len(FAIL)} 项失败: {', '.join(FAIL)}")
        return 1
    print("  全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
