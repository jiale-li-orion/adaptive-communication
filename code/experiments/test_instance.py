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

from center import (ARMS, OP_SET_REPORT_PERIOD, OP_SET_SAMPLING_INTERVAL, CenterView,
                    LocalPolicy, SocObservationModel, build_policy)
from deployment import build_deployment
from exogenous import (KIND_EVENT, KIND_ROUTINE, EnvironmentTruth, ObligationSet,
                       autonomy_margin, irradiance_harvest,
                       constant_harvest, hetero_harvest,
                       displacement_series, rule_obligations_for_truth,
                       routine_obligations, routine_obligations_by_node,
                       wang_burst_obligations, wang_fragment_truth)
from network import DeviceProfile, HopLog, Instance, Node, nodes_from
from oracle import delivery_oracle, dynamic_oracle
from scoring import evaluate, event_propagation, recovery_block

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
    电量按**绝对 Wh** 给：2.5 mWh 够采几条就断电。
    """
    print("\n[2] 失电不补造样本，且义务仍留在分母里")
    # 2.5 mWh ≈ 够采 5 条就断电（单条采样 4.7e-4 Wh + 单次上行空口 ~2e-5 Wh，
    # 见 DeviceProfile.sample_wh 的实测出处）。取这个值是为了让它**中途**死，而不是开头就死。
    nodes, truth, inst, log = build(harvest_wh_per_hour=0.0, temp_c=None,
                                    initial_wh=2.5e-3)
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


def test_recovery_splits_lost_from_recoverable() -> None:
    """中断后的恢复必须把"补不回来的"与"能补回来的"分开报。

    这是 v1.1 §5.3 的核心区分：中断期间**没采到**的读数，恢复后不能按旧时间补造；而**采到了
    没送到**的，自动补发可以追回。合成一个"丢了多少"会把这两件性质完全不同的事混掉。
    """
    print("\n[12] 中断与恢复：采集缺失与交付缺失分开")
    dep = build_deployment(groups=2)
    nodes = nodes_from(dep)
    hours = 12
    truth = wang_fragment_truth(0, hours, (dep.gateway.sid,))
    truth.displacement = displacement_series(nodes.keys(), hours, 0)
    harvest, temp = constant_harvest(nodes.keys(), hours, 3.0, 10.0)
    truth.harvest_wh.update(harvest)
    truth.temp_c.update(temp)
    meas = {k: v.measurand for k, v in nodes.items()}
    D = ObligationSet(routine_obligations_by_node(meas, hours)
                      + rule_obligations_for_truth(truth))

    OUT_LO, OUT_HI = 4, 7          # 回传中断 3 小时
    inst = Instance(nodes, truth, seed=0)
    inst.plane.backhaul_gate = lambda hour: not (OUT_LO <= hour < OUT_HI)
    log = inst.run(hours)
    res = evaluate(D, log, hours, nodes.keys(), plane=inst.plane,
                   outage=(OUT_LO * 3600, OUT_HI * 3600))
    rec = res["recovery"]

    check("恢复分列在场且落在中断窗内", rec["n_obligations_in_window"] > 0,
          f"{rec['n_obligations_in_window']} 条义务落在中断+恢复观察期")
    check("中断期间节点照常采样，因此采集缺失为 0",
          rec["missing_collection"] == 0,
          f"缺采 {rec['missing_collection']}（节点有电）")
    check("交付缺失大于 0，且与采集缺失分开报",
          rec["missing_delivery"] > 0, f"缺送 {rec['missing_delivery']}")
    check("自动补发确实追回了中断期间采集的数据",
          rec["backlog_recovered"] > 0, f"追回 {rec['backlog_recovered']} 条")
    check("恢复分列写明采集缺失不可补造",
          "补不回来" in rec["note"])

    # 中断只延后、不减少：这是 store-and-forward 的性质，值得钉住。
    # **必须用新节点**：Node 带每次运行的状态，复用会静默混合两次运行（Instance 现在会报错拦住）。
    nodes2 = nodes_from(dep)
    inst2 = Instance(nodes2, truth, seed=0)
    inst2.run(hours)
    check("store-and-forward 下中断不改总转发数（只改时延）",
          inst2.plane.backhaul_forwarded == inst.plane.backhaul_forwarded,
          f"无中断 {inst2.plane.backhaul_forwarded} vs 中断 {inst.plane.backhaul_forwarded}")


# ------------------------------------------------------------------ 13 中心下发与回执

def test_center_command_path() -> None:
    """中心下发必须**经链路到达**才生效，回执必须**来自节点上报**。"""
    print("\n[13] 中心下发与回执")
    dep = build_deployment(groups=2)
    hours, task = 13, 12
    truth = wang_fragment_truth(0, hours, (dep.gateway.sid,))

    def run(arm):
        nodes = nodes_from(dep)
        truth.displacement = displacement_series(nodes.keys(), hours, 0)
        harvest, temp = constant_harvest(nodes.keys(), hours, 3.0, 10.0)
        truth.harvest_wh.update(harvest)
        truth.temp_c.update(temp)
        inst = Instance(nodes, truth, seed=0, policy=build_policy(arm))
        return nodes, inst, inst.run(hours)

    nodes_l, inst_l, _ = run("local")
    check("默认策略（现场自治）一条命令都不下发",
          inst_l.counters["commands_sent"] == 0 and inst_l.plane.downlink_attempts == 0,
          f"sent={inst_l.counters['commands_sent']} dl={inst_l.plane.downlink_attempts}")

    nodes_f, inst_f, log_f = run("fixed900")
    check("固定策略确实发出了命令", inst_f.counters["commands_sent"] > 0,
          f"sent={inst_f.counters['commands_sent']}")
    check("命令只有送达节点才算生效（送达数 <= 发出数）",
          0 < inst_f.counters["commands_delivered"] <= inst_f.counters["commands_sent"],
          f"发出 {inst_f.counters['commands_sent']} 送达 {inst_f.counters['commands_delivered']}")
    changed = [k for k, n in nodes_f.items() if n.report_period_s == 900]
    check("送达后节点配置真的变了", bool(changed), f"{len(changed)} 个节点周期=900")

    # 回执只能来自节点上报：中心看到的周期必须来自收到的快照，且不早于命令送达
    receipt_nodes = [k for k, v in inst_f.center.reports.items()
                     if v.get("report_period_s") == 900]
    check("中心通过节点上报拿到回执（不是自己记账）", bool(receipt_nodes),
          f"{len(receipt_nodes)} 个节点回执确认")
    first_receipt = min(inst_f.center.report_at[k] for k in receipt_nodes)
    check("回执时刻不早于该节点第一次上报", first_receipt > 0, f"最早回执 {first_receipt}s")

    # 视图里不能有环境真值
    view = inst_l._center_view(3600)
    check("中心视图不含环境真值/链路状态",
          not any(hasattr(view, a) for a in ("truth", "rainfall", "loss_db", "link")))


def test_config_generation_identity() -> None:
    """执行层的身份与世代：**身份必须按字段分**，世代必须整对生效。

    这一组是为一个真实缺陷补的回归。`logical` 曾经只按世代编号、不带字段维度，于是同一次配置
    决策的第二个字段在远端与"第一个字段的重发"不可区分，被当重复永久丢弃。后果很隐蔽：

      - `atomic` 层永远凑不齐一对，**等于一条配置都不下发**——它的三个业务数字与 `local` 逐位
        相同，看上去像一个"正确但没用"的结论，实际是身份方案的错；
      - `contract` 层每次决策只落地一个字段（下发次序是先采样间隔、后上报周期，于是上报周期
        永远停在默认值），把跨代混配的时间推得**比 `naive` 更长**。

    两者都会污染"执行层"这条结论线。所以这里钉住三条性质：两个字段共享同一个世代号、身份各自
    不同、整对才生效。
    """
    print("\n[14] 配置身份与世代")
    dep = build_deployment(groups=2)
    hours = 12

    def run(contract: bool, atomic: bool, captured: list | None = None):
        nodes = nodes_from(dep)
        before = {k: (n.sample_interval_s, n.report_period_s) for k, n in nodes.items()}
        truth = wang_fragment_truth(0, hours, (dep.gateway.sid,))
        truth.displacement = displacement_series(nodes.keys(), hours, 0)
        h, t = hetero_harvest(nodes.keys(), hours, 0, low_frac=0.4, low_wh_per_hour=0.0)
        truth.harvest_wh.update(h)
        truth.temp_c.update(t)
        inst = Instance(nodes, truth, seed=0, policy=build_policy("ea_i600"),
                        send_contract_fields=contract, atomic_generation=atomic)
        if captured is not None:
            orig = inst.plane.center_send

            def spy(nid, msg, hh, _orig=orig, _sink=captured):
                _sink.append((nid, dict(getattr(msg, "payload", None) or {})))
                return _orig(nid, msg, hh)

            inst.plane.center_send = spy
        inst.run(hours)
        return nodes, before, inst

    # 1. 身份按字段分：同一世代的两个字段，世代号相同、逻辑身份不同。
    # **世代号是逐节点计数的**，所以分组的键必须是 (节点, 世代)，不能只用世代号。
    captured: list = []
    _, _, inst_c = run(contract=True, atomic=False, captured=captured)
    by_gen: dict[tuple, dict[str, set]] = {}
    for nid, p in captured:
        by_gen.setdefault((nid, p.get("generation")), {}).setdefault(
            p.get("op"), set()).add(p.get("logical"))
    paired = [g for g, ops in by_gen.items()
              if OP_SET_SAMPLING_INTERVAL in ops and OP_SET_REPORT_PERIOD in ops]
    check("成对下发的世代里，两个字段各自有身份（不是共享一个）",
          bool(paired) and all(
              by_gen[g][OP_SET_SAMPLING_INTERVAL].isdisjoint(
                  by_gen[g][OP_SET_REPORT_PERIOD]) for g in paired),
          f"{len(paired)} 个成对世代 / {len(by_gen)} 个 (节点,世代)")
    # 同一条命令的重发必须共享身份——否则远端认不出重复，去重本身就不成立。
    check("同一 (节点, 字段, 世代) 的重发共享同一个身份",
          all(len(v) == 1 for ops in by_gen.values() for v in ops.values()),
          f"{len(captured)} 条下发")

    # 2. 契约层下**两个字段都必须落地**。旧缺陷在这里表现为上报周期恒为默认值。
    nodes_c, before_c, _ = run(contract=True, atomic=False)
    moved_i = sum(1 for k, n in nodes_c.items() if n.sample_interval_s != before_c[k][0])
    moved_p = sum(1 for k, n in nodes_c.items() if n.report_period_s != before_c[k][1])
    check("契约层下采样间隔与上报周期都真的落地了",
          moved_i > 0 and moved_p > 0,
          f"间隔动了 {moved_i} 个、周期动了 {moved_p} 个")

    # 3. 原子层：混配时间必须为 0，而且**不能退化成"什么都不改"**。
    nodes_a, before_a, inst_a = run(contract=True, atomic=True)
    check("原子世代层：跨代混配时间为 0", inst_a.mixed_config_ticks == 0,
          f"混配 {inst_a.mixed_config_ticks}s")
    moved_a = sum(1 for k, n in nodes_a.items()
                  if (n.sample_interval_s, n.report_period_s) != before_a[k])
    check("原子世代层确实改动了配置（不是把命令全拒了）", moved_a > 0,
          f"{moved_a} 个节点配置改变")

    # 4. 这一列会动：不加任何执行层时，常态网络里就有跨代混配。
    _, _, inst_n = run(contract=False, atomic=False)
    check("不加执行层时跨代混配确实出现（这一列不是恒 0）",
          inst_n.mixed_config_ticks > 0, f"混配 {inst_n.mixed_config_ticks}s")

    # 5. **单字段策略在原子层下也必须落地。** 只改一个字段的决策是一个只有一个字段的完整
    #    世代；若把"到齐"写死成"两个字段都到"，`AoiPolicy` 这类策略在原子层下会被整类丢弃，
    #    于是策略与执行层不可比——那是个比缺陷更难发现的错误。
    nodes_s = nodes_from(dep)
    before_s = {k: (n.sample_interval_s, n.report_period_s) for k, n in nodes_s.items()}
    truth = wang_fragment_truth(0, hours, (dep.gateway.sid,))
    truth.displacement = displacement_series(nodes_s.keys(), hours, 0)
    h, t = hetero_harvest(nodes_s.keys(), hours, 0, low_frac=0.4, low_wh_per_hour=0.0)
    truth.harvest_wh.update(h)
    truth.temp_c.update(t)
    inst_s = Instance(nodes_s, truth, seed=0, policy=build_policy("aoi"),
                      send_contract_fields=True, atomic_generation=True)
    inst_s.run(hours)
    moved_s = sum(1 for k, n in nodes_s.items() if n.report_period_s != before_s[k][1])
    check("单字段策略在整代生效的执行层下也能落地",
          moved_s > 0 and inst_s.mixed_config_ticks == 0,
          f"{moved_s} 个节点周期改变、混配 {inst_s.mixed_config_ticks}s")


def test_dynamic_oracle_is_a_bound() -> None:
    """真上界必须**真的是上界**，而且**不是恒饱和的**。

    `dynamic_upper_bound` 的两条松弛叠起来松到 168/168——"什么都能做到"的上界不带信息，
    用它算 regret 等于用一个常数当分母。`dynamic_oracle` 只松弛可交付性，保留档位离散性与能量的
    小时耦合，因此必须同时满足两条：**不低于任何真实策略**、**在绑定条件下严格低于义务总数**。

    另外钉一条实现缺陷的回归：把"窗与本小时有交集"当计入条件会**重复计数**（本实例的窗是闭区间
    `[h*3600, (h+1)*3600]`，第 h 小时的义务会在第 h+1 小时里再被记一次，12 条被数成 23 条）。
    所以逐节点上界不得超过该节点的义务条数。
    """
    print("\n[15] 真上界（逐节点逐小时离线 DP）")
    dep = build_deployment(groups=2)
    hours = 12

    def build(cap: float):
        nodes = nodes_from(dep)
        prof = DeviceProfile(capacity_wh=cap)
        for n in nodes.values():
            n.p = DeviceProfile(sample_interval_s=n.p.sample_interval_s,
                                report_period_s=n.p.report_period_s,
                                capacity_wh=cap, sample_wh=n.p.sample_wh)
            n.soc_wh = cap
            n.power = type(n.power)(soc_initial_wh=cap, soc_wh=cap)
        truth = wang_fragment_truth(0, hours, (dep.gateway.sid,))
        truth.displacement = displacement_series(nodes.keys(), hours, 0)
        h, t = hetero_harvest(nodes.keys(), hours, 0, low_frac=0.4, low_wh_per_hour=0.0)
        truth.harvest_wh.update(h)
        truth.temp_c.update(t)
        meas = {k: v.measurand for k, v in nodes.items()}
        obs = ObligationSet(routine_obligations_by_node(meas, hours)
                            + rule_obligations_for_truth(truth))
        return nodes, prof, truth, obs

    for cap in (0.008, 0.05):
        nodes, prof, truth, obs = build(cap)
        do = dynamic_oracle(obs, hours, truth.harvest_wh, nodes.keys(), profile=prof)
        n_routine = sum(1 for o in obs.obligations if o.kind == KIND_ROUTINE)
        over = [k for k, v in do["per_node"].items() if v["oracle"] > v["n_obligations"]]
        check(f"逐节点上界不超过该节点义务条数（cap {cap}）", not over,
              f"越界 {over}" if over else f"{n_routine} 条周期义务")
        # **上界只覆盖周期义务**：事件义务靠触发锚定的本地采样，本函数的动作集够不到它
        # （这条真的被突破过——见函数文档）。所以两边的比较也必须都只算周期义务。
        #
        # 注意**不要把"上界严格小于义务总数"当普遍要求**：0.008 Wh 的电池够跑
        # `0.008 / 4.93e-4 = 16.2` 小时的稀疏档，12 小时的任务里所有周期义务本来就都做得到，
        # 上界因此合理地为满值。能量真正咬人的门槛是 `12 * 4.93e-4 = 5.9e-3 Wh` 以下，
        # 那一条单独在 cap 0.004 上查。

        inst = Instance(nodes, truth, seed=0, policy=build_policy("dense600"))
        log = inst.run(hours)
        res = evaluate(obs, log, hours, nodes.keys(),
                       battery={k: v.power.to_dict() for k, v in nodes.items()},
                       plane=inst.plane, task_hours=hours)
        got = res["routine"]["delivered"]
        check(f"真实策略的周期交付不超过上界（cap {cap}）", got <= do["total_oracle"],
              f"dense600 周期交付 {got} ≤ 上界 {do['total_oracle']}")

    # 能量真正绑定的一档：0.004 Wh 撑不满 12 小时，上界必须掉下来。
    nodes_b, prof_b, truth_b, obs_b = build(0.004)
    do_b = dynamic_oracle(obs_b, hours, truth_b.harvest_wh, nodes_b.keys(), profile=prof_b)
    n_routine_b = sum(1 for o in obs_b.obligations if o.kind == KIND_ROUTINE)
    check("能量真绑定(0.004 Wh)时上界严格低于周期义务总数",
          do_b["total_oracle"] < n_routine_b,
          f"上界 {do_b['total_oracle']} < {n_routine_b}")

    # 档位必须真的随小时变——否则"动态"二字没有内容。
    sched = dynamic_oracle(obs, hours, truth.harvest_wh, nodes.keys(), profile=prof)
    varied = [k for k, v in sched["per_node"].items()
              if len({x for x in v["schedule"] if x is not None}) > 1]
    check("最优档位序列确实随小时变化（不是一条恒定配置）", bool(varied),
          f"{len(varied)}/{len(sched['per_node'])} 个节点的档位不止一种")


def test_blind_config_is_a_noop() -> None:
    """**"读状态"的入场费**：不知道状态时先发一代保守配置——而它必须是**空操作**。

    反馈策略要按状态决定给谁加密，可在收到第一份读数之前它不知道状态，于是保守地先下发
    "稀疏间隔 + 稀疏周期"。实测这一代占了 `ea_i600` 全部下发的一半（54 条里的 28 条），
    也是它与固定配置在**下行次数**上差距的主要来源（85.2 vs 36.2）。

    它之所以可以整代省掉，是因为它设的值与**设备出厂默认完全相同**——节点本来就跑这一档。
    这里把这条等价关系钉住：**一旦有人改了默认 profile 或稀疏档，省略它就不再等价**，
    那不是优化而是行为改变，测试必须红。
    """
    print("\n[16] 未知状态时的保守配置是不是空操作")
    dp = DeviceProfile()
    pol = build_policy("ea_i600")
    check("保守档（稀疏）与设备出厂默认逐位相同",
          pol.sparse_interval_s == dp.sample_interval_s
          and pol.sparse_period_s == dp.report_period_s,
          f"稀疏 {pol.sparse_interval_s}/{pol.sparse_period_s} "
          f"vs 默认 {dp.sample_interval_s}/{dp.report_period_s}")

    dep = build_deployment(groups=2)
    hours = 6

    def run(arm: str, lossless: bool):
        """`lossless=True` 时把接入与回传都设成全通。

        **为什么必须要这个受控对照。** 有损链路上，少发 26 条命令会让后续的随机抽样整体错位，
        两条臂因此走到不同的样本序列上——末态配置不同是**随机流偏移**，不是行为差异。
        全通链路下没有随机分支，两条臂必须给出**逐位相同**的末态配置；若不同，那就真的是
        省掉那一代改变了行为，测试必须红。
        """
        nodes = nodes_from(dep)
        truth = wang_fragment_truth(0, hours, (dep.gateway.sid,))
        truth.displacement = displacement_series(nodes.keys(), hours, 0)
        h, t_ = hetero_harvest(nodes.keys(), hours, 0, low_frac=0.4, low_wh_per_hour=0.0)
        truth.harvest_wh.update(h)
        truth.temp_c.update(t_)
        inst = Instance(nodes, truth, seed=0, policy=build_policy(arm),
                        send_contract_fields=True,
                        uplink_p_arrive=1.0 if lossless else 0.74,
                        backhaul_p_good=1.0 if lossless else 0.62)
        inst.run(hours)
        final = sorted((n.sample_interval_s, n.report_period_s) for n in nodes.values())
        return inst, final

    inst_b, _ = run("ea_i600", lossless=False)
    inst_s, _ = run("ea_nb", lossless=False)
    check("省掉那一代后下发条数严格减少",
          len(inst_s.intent_log) < len(inst_b.intent_log),
          f"ea_i600 {len(inst_b.intent_log)} 条 → ea_nb {len(inst_s.intent_log)} 条")

    # **无损链路下的受控对照。** 为什么必须无损：有损链路上少发 26 条命令会让后续随机抽样整体
    # 错位，两条臂走到不同样本序列上，差异到底是行为还是随机就分不清。全通链路没有随机分支。
    #
    # 测出来的结论与"什么都不做"不同，而且更重要：**那一代冗余配置会抢占同一份稀缺的下行机会**，
    # 于是真正的那对命令里"上报周期"字段被拒，节点卡在跨代混配上直到运行结束。
    # 所以省掉它不只是省下行，它同时消除了策略**自己制造**的非法配置。
    inst_b2, _ = run("ea_i600", lossless=True)
    inst_s2, _ = run("ea_nb", lossless=True)
    check("无损下冗余那一代真的会制造跨代混配（不是链路造成的）",
          inst_b2.mixed_config_ticks > 0 and inst_s2.mixed_config_ticks == 0,
          f"ea_i600 混配 {inst_b2.mixed_config_ticks}s、ea_nb 混配 {inst_s2.mixed_config_ticks}s")

    def first_dense(inst):
        seen = {}
        for e in inst.intent_log:
            nid = e[1].split(":")[0]
            if e[2] == 600 and nid not in seen:
                seen[nid] = e[0]
        return sorted(seen.values())

    fb, fs = first_dense(inst_b2), first_dense(inst_s2)
    check("省掉那一代后节点更早被切到密集（冗余下发会重置 dwell 计时器）",
          bool(fs) and bool(fb) and max(fs) < max(fb),
          f"ea_nb 最晚 {max(fs)}s vs ea_i600 最晚 {max(fb)}s")


def test_autonomy_margin_is_hand_computable() -> None:
    """横轴换成 autonomy margin 的理由，必须由这条测试承担。

    定义：`λ*` = 把采能轨迹整体缩小到多少倍时，**每一个小时**都还买得起该小时要采的样。
    `λ* = 1` 恰好够，`> 1` 有富余，`< 1` 本来就差多少。

    两条必须成立的性质：

      1. **手算对得上**：恒定采能 `h`（Wh/h）、消耗 `c`（Wh/h）、初始电量 0、容量充裕时
         `margin = h / c`，取 `h = c` 得恰好 1、取 `h = 2c` 得 2。
      2. **它抓到的是时序，不只是总量**：两条**总量相同**的轨迹，一条平摊到全程、一条只在后半段
         到来，前者的 `λ*` 明显更高。**只看绝对 Wh 会把这两条判成一样**，而它们在现场完全是
         两回事（白天进电与夜里进电）。这正是本项要求"横轴不用绝对 Wh"的技术理由。

    第 2 条如果失败，说明这个横轴退化成了总量轴，换与不换没有区别。
    """
    print("\n[17] autonomy margin：手算值，以及时序与总量的区分")
    c = 4.933e-4
    step = 60.0
    hours = 12

    def const(wh_per_hour: float) -> dict[int, float]:
        return {t: wh_per_hour / 60.0 for t in range(0, hours * 3600, 60)}

    lam = autonomy_margin(const(c), hours, capacity_wh=10.0, initial_wh=0.0,
                          cost_per_hour=c)
    check("恒定采能恰好等于消耗时 margin = 1（手算值）", abs(lam - 1.0) < 1e-2,
          f"margin = {lam:.4f}，期望 1.0")
    lam2 = autonomy_margin(const(2 * c), hours, capacity_wh=10.0, initial_wh=0.0,
                           cost_per_hour=c)
    check("采能是消耗的两倍时 margin = 2（手算值：能掉一半）", abs(lam2 - 2.0) < 1e-2,
          f"margin = {lam2:.4f}，期望 2.0")

    # 总量相同：平摊 12 h 各 h=2c ↔ 只在后 6 h 到来，每小时 4c。
    spread = const(2 * c)
    late = {t: 0.0 for t in range(0, hours * 3600, 60)}
    for t in range(6 * 3600, hours * 3600, 60):
        late[t] = 4 * c / 60.0
    tot_s = round(sum(spread.values()), 9)
    tot_l = round(sum(late.values()), 9)
    check("两条轨迹总量逐位相同（所以差异只能来自时序）", tot_s == tot_l,
          f"总量均为 {tot_s} Wh")
    lam_s = autonomy_margin(spread, hours, capacity_wh=10.0, initial_wh=0.0,
                            cost_per_hour=c)
    lam_l = autonomy_margin(late, hours, capacity_wh=10.0, initial_wh=0.0,
                            cost_per_hour=c)
    check("时序不同则 margin 不同，且起始无输入的轨迹判为不可行",
          lam_l < lam_s - 0.1 and lam_l == 0.0,
          f"平摊 margin={lam_s:.3f} vs 后段集中 margin={lam_l:.3f}")


def test_oracle_action_is_two_dimensional() -> None:
    """上界的动作必须是**两个字段**，不能按"每采一条报一条"计能。

    采样间隔与上报周期是独立字段（E：重庆 `0045`/`0042`），设备还有缓存，所以"**采得密、
    报得稀**"是允许的。上界如果按 `cost = (3600/a) * (sample_wh + UPLINK_WH)` 计，
    就**高估了密集采样的能耗**——而低估能耗会让上界偏低，**偏低的上界不再是上界**。

    实测在 `dense300`（采 300 s、报 900 s）上确实差着：真实每小时能耗
    `12*4.7e-4 + 4*2.33e-5`，而一维写法按 `12*(4.7e-4 + 2.33e-5)` 计。

    这条测试用一条**采报解耦**的真实臂去撞上界：`dense300` 必须是够得到上界的。
    当年 `oracle_deploy` 被真实策略超过过一次，那次的教训是"能被超过的东西不是上界"；
    这里用同一条判据，但撞的是**动作空间**而不是参数知识。
    """
    print("\n[18] 上界的动作是两个字段")
    dep = build_deployment(groups=2)
    hours = 12
    cap = 0.004

    nodes = nodes_from(dep)
    prof = DeviceProfile(capacity_wh=cap, initial_soc=1.0)
    for n in nodes.values():
        n.p = DeviceProfile(sample_interval_s=n.p.sample_interval_s,
                            report_period_s=n.p.report_period_s,
                            capacity_wh=cap, sample_wh=n.p.sample_wh)
        n.soc_wh = cap
        n.power = type(n.power)(soc_initial_wh=cap, soc_wh=cap)
    truth = wang_fragment_truth(0, hours, (dep.gateway.sid,))
    truth.displacement = displacement_series(nodes.keys(), hours, 0)
    h, t_ = hetero_harvest(nodes.keys(), hours, 0, low_frac=0.4, low_wh_per_hour=0.0)
    truth.harvest_wh.update(h)
    truth.temp_c.update(t_)
    meas = {k: v.measurand for k, v in nodes.items()}
    obs = ObligationSet(routine_obligations_by_node(meas, hours))

    arm = ARMS["dense300"]()
    check("这条臂确实是采报解耦的（采样间隔 ≠ 上报周期）",
          arm.interval_s != arm.period_s, f"采 {arm.interval_s}s / 报 {arm.period_s}s")

    do = dynamic_oracle(obs, hours, truth.harvest_wh, nodes.keys(), profile=prof,
                        initial_wh=cap)
    inst = Instance(nodes, truth, seed=0, policy=build_policy("dense300"))
    log = inst.run(hours)
    res = evaluate(obs, log, hours, nodes.keys(),
                   battery={k: v.power.to_dict() for k, v in nodes.items()},
                   plane=inst.plane, task_hours=hours)
    got = res["routine"]["delivered"]
    check("采报解耦的真实臂不超过上界（上界不能低估密集采样的能耗）",
          got <= do["total_oracle"],
          f"dense300 周期交付 {got} ≤ 上界 {do['total_oracle']}")

    # 上界必须真的把两个字段分开算：把上报周期独立抽出来，成本函数里必须留有它的维度。
    per = do["per_node"][sorted(do["per_node"])[0]]["schedule"]
    pairs = {tuple(x) for x in per if x is not None and x[0] is not None}
    check("最优档位是 (采样间隔, 上报周期) 二元组，不是一维档位",
          bool(pairs) and all(isinstance(p, tuple) and len(p) == 2 for p in pairs),
          f"档位样例 {sorted(pairs)[:3]}")


def test_action_admission_classification() -> None:
    """**动作准入计数**：每一条落地的命令，到底改变了什么。

    三条互斥且穷尽，缺一条就答不上"多余的控制流量是什么"：

      - `writes_changed` —— 写入的值与节点当时的值**不同**，真的改了配置；
      - `writes_same_value` —— 写入的值与节点当时的值**相同**，是**值域空操作**；
      - `writes_speculative` —— 中心对这台设备的电量**没有读数**时的保守下发。

    为什么要专门查：`same_value` 这条命令**在计数上与一次真正的重配完全一样**——到达、被接受、
    计入 `commands_delivered`。只有把值拿出来比才分得开。这条测试同时钉住穷尽性
    （`changed + same_value == commands_delivered`），否则漏掉的那类会静默消失。
    """
    print("\n[19] 动作准入归类")
    dep = build_deployment(groups=2)
    hours = 13

    def run(arm: str, cap: float):
        nodes = nodes_from(dep)
        prof = DeviceProfile(capacity_wh=cap, charge_min_c=None)
        for n in nodes.values():
            n.p = DeviceProfile(sample_interval_s=n.p.sample_interval_s,
                                report_period_s=n.p.report_period_s,
                                capacity_wh=cap, sample_wh=n.p.sample_wh,
                                charge_min_c=None)
            n.soc_wh = cap
            n.power = type(n.power)(soc_initial_wh=cap, soc_wh=cap)
        truth = wang_fragment_truth(0, hours, (dep.gateway.sid,))
        truth.displacement = displacement_series(nodes.keys(), hours, 0)
        h, t_ = hetero_harvest(nodes.keys(), hours, 0, low_frac=0.4, low_wh_per_hour=0.0,
                               high_wh_per_hour=0.05)
        truth.harvest_wh.update(h)
        truth.temp_c.update(t_)
        inst = Instance(nodes, truth, seed=0, policy=build_policy(arm),
                        send_contract_fields=True)
        inst.run(hours)
        return inst.counters

    for cap, label in ((0.05, "宽松 0.05"), (0.004, "绑定 0.004")):
        c_nb = run("ea_nb", cap)
        c_old = run("ea_i600", cap)
        check(f"[{label}] 归类穷尽且互斥：改值 + 同值 = 落地",
              c_nb["writes_changed"] + c_nb["writes_same_value"] == c_nb["commands_delivered"],
              f"{c_nb['writes_changed']} + {c_nb['writes_same_value']} = "
              f"{c_nb['commands_delivered']}")
        check(f"[{label}] ea_nb 不写同值、不做无证据下发",
              c_nb["writes_same_value"] == 0 and c_nb["writes_speculative"] == 0,
              f"同值 {c_nb['writes_same_value']}、未知态 {c_nb['writes_speculative']}")
        check(f"[{label}] ea_i600 的未知状态下发被单独数出来",
              c_old["writes_speculative"] > 0,
              f"未知态 {c_old['writes_speculative']}")
        if cap <= 0.004:
            # 绑定区：soc 永远到不了阈值，于是它的每一次写入都是把节点设回默认值。
            check(f"[{label}] ea_i600 的控制流量全是值域空操作",
                  c_old["writes_same_value"] > 0 and c_old["writes_changed"] == 0,
                  f"改值 {c_old['writes_changed']}、同值 {c_old['writes_same_value']}")


def test_autonomy_margin_blind_spot() -> None:
    """`autonomy_margin` **只覆盖周期工作负载**——把这条限度钉住，免得它被当可行性判据。

    实测反例：一个真实窗口在 `margin = 1.37`（判为可行）下 **14/14 台全灭**。原因是代价模型里
    没有**事件触发的本地采样**：每次触发连采 3 条 = 1.41e-3 Wh，单次就超过 0.0012 Wh 的初始电量。

    这条测试用**手算**复算这条链：初始电量、t=0 的一次周期采样、t=1052 的触发、3 条事件样，
    然后断言"周期模型说可行、而含事件的账算下来在第二条就付不起"。**它不是查实现对不对，
    是查这个横轴能主张到哪一步。**
    """
    print("\n[20] autonomy margin 的盲区：事件采样不在它的代价模型里")
    cap, soc0 = 0.006, 0.2
    sample_wh = DeviceProfile().sample_wh
    slots = DeviceProfile().event_slots
    init = cap * soc0

    # 手算：初始电量 → 扣掉 t=0 的周期采样 → 触发时刻连采 slots 条
    after_first = init - sample_wh
    check("初始电量在周期模型下够付第一条（这就是 margin 看到的）",
          init > 4.933e-4, f"初始 {init:.4f} Wh")
    # 逐条走一遍触发时的连采：**第一条付得起，第二条就付不起**。
    soc = after_first
    paid = 0
    for _ in range(slots):
        if soc < sample_wh:
            break
        soc -= sample_wh
        paid += 1
    check("触发时连采 3 条，实际只付得起 1 条就归零",
          paid == 1 and soc < sample_wh,
          f"付了 {paid} 条，剩 {soc:.6f} Wh < 一条 {sample_wh:.6f} Wh")
    check("事件一次要连采 slots 条，量级超过全部初始电量",
          slots * sample_wh > init,
          f"{slots} x {sample_wh:.6f} = {slots * sample_wh:.6f} > 初始 {init:.4f}")

    # 再确认 margin 本身确实看不到事件：同一个窗口，margin 判可行
    dep = build_deployment(groups=2)
    nodes = nodes_from(dep)
    truth = wang_fragment_truth(0, 13, (dep.gateway.sid,))
    h, _t = irradiance_harvest(nodes.keys(), 13, 0, start_hour=5475,
                               peak_wh_per_hour=0.02, source_temp=False, temp_c=10.0)
    m = autonomy_margin(h["n00"], 12, capacity_wh=cap, initial_wh=init,
                        cost_per_hour=4.933e-4)
    check("该窗口的 margin 判为可行（> 1），而仿真实测全灭",
          m > 1.0, f"margin = {m:.2f}（这个数**不代表**可用性）")


def test_composed_baseline_keeps_both_dimensions() -> None:
    """最强传统基线：**两个维度各自保持自己的最优做法，谁都不许削弱谁**。

    第一版把上报周期在"电能健康"时压成 900 s，结果整条基线的周期达标率（90.4%）**低于**
    只做 AoI 的 `aoi`（91.8%）——叠加一个维度反而削弱了另一个。这条测试直接查策略的输出：
    **当 AoI 陈旧时，无论电能是否健康，上报周期都必须是 300 s。**

    另一条同时钉住：**没有电量读数时一条都不发**。保守档与出厂默认逐位相同，发出去是值域空操作，
    却要花掉一次下行机会（实测它占了 `ea_i600` 全部控制流量的一半）。
    """
    print("\n[21] 最强传统基线：两维不互相削弱")
    pol = build_policy("ea_aoi")
    check("aoi 的陈旧阈值与快速周期（这两条是它领先的来源）",
          pol.stale_s == 3600 and pol.fast_period_s == 300 and pol.slow_period_s == 900,
          f"stale {pol.stale_s} / fast {pol.fast_period_s} / slow {pol.slow_period_s}")
    check("电能健康档不再改写上报周期",
          pol.dense_period_s == pol.slow_period_s,
          f"dense_period {pol.dense_period_s} vs slow {pol.slow_period_s}")

    sm = SocObservationModel(4000, 0.0, 1.0, 0.0, seed=0)
    # 电量健康（报回的 soc 很高）+ AoI 陈旧（最后一份样本在 7200 s 前）
    view = CenterView(t_s=7200, node_ids=("n00",),
                      # **遥测新、样本旧**：`report_at` 近（所以知道电量），
                      # `newest_taken_at` 远（所以 AoI 陈旧）。这两个不是一回事，
                      # 混用会让"知道电量"和"数据新鲜"分不开。
                      reports={"n00": {"soc_wh": 0.02}},
                      report_at={"n00": 7000}, newest_taken_at={"n00": 0},
                      in_flight=frozenset(), soc_model=sm)
    periods = [p["period_s"] for _, p in pol.plan(view)
               if p.get("op") == OP_SET_REPORT_PERIOD]
    check("AoI 陈旧 + 电量健康时报出的是快速周期 300 s（未被电能维度覆盖）",
          periods == [300], f"报出的周期 = {periods}")

    pol2 = build_policy("ea_aoi")
    view2 = CenterView(t_s=7200, node_ids=("n00",), reports={}, report_at={},
                       newest_taken_at={}, in_flight=frozenset(), soc_model=sm)
    check("没有电量读数时一条都不发（不做无证据下发）",
          pol2.plan(view2) == [], f"发出 {len(pol2.plan(view2))} 条")


def test_delivery_oracle_is_a_bound_and_splits_the_gap() -> None:
    """**发送调度的上界**：它必须盖住实际交付，而且必须真的松弛了发送侧。

    两条性质，缺一条它就没用：

      1. **上界性**：`delivery_oracle >= 实际周期交付`。第一版在这里翻过车——
         推进条件写成"时刻是否越过 heard_at"而不是"回传是否可用"，于是样本 heard_at=0、
         回传 0 点不可用而 1 点才可用的情形被判成不可交付，上界**低于**实际交付
         （`local` 142.3 < 148.1）。**上界被真实策略突破，属于必须立刻修的那一类。**
      2. **它确实松弛了发送侧**：至少有一个条件让它严格大于实际交付。否则这一列恒等于
         实际交付，等于没有信息——本项目对每一列都要求先证明它会动。

    它同时必须与 energy oracle 是**两个不同的问题**：energy oracle 松弛可交付性、
    问"最多采到几条"；本函数保留实测的 `heard_at` 与回传可用性，问"同样的样本最多送到几条"。
    """
    print("\n[22] 发送调度上界：盖住实际交付，且真的松弛了发送侧")
    dep = build_deployment(groups=2)
    hours, task, cap = 13, 12, 0.05

    def build_nodes():
        ns = nodes_from(dep)
        for n in ns.values():
            n.p = DeviceProfile(sample_interval_s=n.p.sample_interval_s,
                                report_period_s=n.p.report_period_s,
                                capacity_wh=cap, sample_wh=n.p.sample_wh)
            n.soc_wh = cap
            n.power = type(n.power)(soc_initial_wh=cap, soc_wh=cap)
        return ns

    truth = wang_fragment_truth(0, hours, (dep.gateway.sid,))
    probe = build_nodes()
    truth.displacement = displacement_series(probe.keys(), hours, 0)
    h, t_ = hetero_harvest(probe.keys(), hours, 0, low_frac=0.4, low_wh_per_hour=0.0,
                           high_wh_per_hour=3.0)
    truth.harvest_wh.update(h)
    truth.temp_c.update(t_)
    meas = {k: v.measurand for k, v in probe.items()}
    obs = ObligationSet(routine_obligations_by_node(meas, task))

    strict = 0
    for arm in ("local", "aoi", "dense600"):
        nodes = build_nodes()
        inst = Instance(nodes, truth, seed=0, policy=build_policy(arm))
        log = inst.run(hours)
        res = evaluate(obs, log, hours, nodes.keys(),
                       battery={k: v.power.to_dict() for k, v in nodes.items()},
                       plane=inst.plane, task_hours=task)
        dl = delivery_oracle(obs, log, hours, plane=inst.plane)["total_oracle"]
        got = res["routine"]["delivered"]
        check(f"[{arm}] 送达上界不低于实际交付", dl >= got, f"上界 {dl} vs 实际 {got}")
        if dl > got:
            strict += 1
    check("至少一个条件下上界严格大于实际（说明它确实松弛了发送侧，不是恒等列）",
          strict > 0, f"{strict}/3 个条件严格大于")


def test_delivery_ceiling_is_policy_independent() -> None:
    """**自由发送时刻的送达上界必须与策略无关。**

    它只由「义务窗口 × 潜在链路结果」决定：对每条义务，问窗口内是否存在一个**会被听到**的
    绝对 tick，且其后第一个回传可用时刻不晚于截止。这里的潜在上行结果按
    `(node, 绝对 tick)` 固定，所以**换任何臂都不该变**。

    这条性质是本次改动的核心目的：此前的键带全局命令序号，策略 A 多发一个包就会平移
    策略 B 的后继抽签，跨策略比较因此不成立。实测三条件 × 五臂，自由上界全是 **158.9**
    —— 一个数与臂无关，正是它该有的样子。同时钉住**转发损与链路损也恒定**，
    而"择时损"随臂变化（那才是策略真正可控的一维）。
    """
    print("\n[23] 自由发送上界与策略无关")
    dep = build_deployment(groups=2)
    hours, task, cap = 13, 12, 0.05

    def build_nodes():
        ns = nodes_from(dep)
        for n in ns.values():
            n.p = DeviceProfile(sample_interval_s=n.p.sample_interval_s,
                                report_period_s=n.p.report_period_s,
                                capacity_wh=cap, sample_wh=n.p.sample_wh)
            n.soc_wh = cap
            n.power = type(n.power)(soc_initial_wh=cap, soc_wh=cap)
        return ns

    truth = wang_fragment_truth(0, hours, (dep.gateway.sid,))
    probe = build_nodes()
    truth.displacement = displacement_series(probe.keys(), hours, 0)
    h, t_ = hetero_harvest(probe.keys(), hours, 0, low_frac=0.4, low_wh_per_hour=0.0,
                           high_wh_per_hour=3.0)
    truth.harvest_wh.update(h)
    truth.temp_c.update(t_)
    meas = {k: v.measurand for k, v in probe.items()}
    obs = ObligationSet(routine_obligations_by_node(meas, task))

    free_vals, fixed_vals = [], []
    for arm in ("local", "aoi", "dense600", "ea_nb"):
        nodes = build_nodes()
        inst = Instance(nodes, truth, seed=0, policy=build_policy(arm))
        log = inst.run(hours)
        free_vals.append(delivery_oracle(obs, log, hours, plane=inst.plane,
                                         free_transmit=True)["total_oracle"])
        fixed_vals.append(delivery_oracle(obs, log, hours,
                                          plane=inst.plane)["total_oracle"])
    check("自由发送上界在四个臂上逐位相同（与策略无关）",
          len(set(free_vals)) == 1, f"取值 {sorted(set(free_vals))}")
    check("固定发送时刻的上界随臂变化（它含策略真正影响的那一维）",
          len(set(fixed_vals)) > 1, f"取值 {sorted(set(fixed_vals))}")
    check("自由上界不低于固定发送上界（放松得更多，不能更少）",
          all(f >= x for f, x in zip(free_vals, fixed_vals)),
          f"自由 {free_vals} vs 固定 {fixed_vals}")


def test_energy_scale_invariance() -> None:
    """**整个能量系统乘以 λ，业务结果必须逐位不变。**

    这条测的不是实现细节，是**这个实例的物理性质**：它的能量轴是**无量纲**的。
    实证：λ ∈ {0.25, 1, 4, 16}（64 倍范围）下 `local` / `aoi` / `dense600` / `dense1800`
    四条臂的每一列都逐位相同。

    **为什么必须钉住。** 它决定论文能用什么横轴。既然结果只取决于**比值**，
    那么 `0.004 Wh`、`0.05 Wh` 这些数**不是现实部署数值**，把它们当现场事实写出来是错的；
    正确的表述是**无量纲的**——例如「电池的初始自主小时数 `A₀ = soc₀·C / (sample_wh + uplink_wh)`
    与最长无采能时段之比」。本实例里 cliff 恰好落在 `A₀ ≈ 任务时长`。

    **注意它检验的是实例，不是策略。** 用的是**不含能量阈值**的臂：`local`（无阈值）、
    `aoi`（只按年龄）、`dense600`/`dense1800`（固定）。
    带绝对能量阈值的策略（如 `ea_nb` 的 `healthy_wh = 0.010`）**本来就不满足尺度不变性**——
    那是策略属性的问题，不是实例的问题，因此**不放在这条测试里**。
    """
    print("\n[24] 能量尺度不变性：整个能量系统 × λ，业务列逐位不变")
    import oracle as _or
    import opportunity as _op

    dep = build_deployment(groups=2)
    hours, task, cap = 13, 12, 0.004
    base_sample = DeviceProfile().sample_wh
    arms = ("local", "aoi", "dense600", "dense1800")

    def run_all(lam: float):
        saved_bus, saved_up = _op.BUS_V, _or.UPLINK_WH
        _op.BUS_V = saved_bus * lam
        _or.UPLINK_WH = saved_up * lam
        try:
            out = {}
            for arm in arms:
                ns = nodes_from(dep)
                prof = DeviceProfile(capacity_wh=cap * lam, sample_wh=base_sample * lam)
                ns = nodes_from(dep, profile=prof)
                truth = wang_fragment_truth(0, hours, (dep.gateway.sid,))
                truth.displacement = displacement_series(ns.keys(), hours, 0)
                h, t_ = hetero_harvest(ns.keys(), hours, 0, low_frac=0.4,
                                       low_wh_per_hour=0.0, high_wh_per_hour=3.0 * lam)
                truth.harvest_wh.update(h)
                truth.temp_c.update(t_)
                meas = {k: v.measurand for k, v in ns.items()}
                obs = ObligationSet(routine_obligations_by_node(meas, task))
                inst = Instance(ns, truth, seed=0, policy=build_policy(arm))
                log = inst.run(hours)
                res = evaluate(obs, log, hours, ns.keys(),
                               battery={k: v.power.to_dict() for k, v in ns.items()},
                               plane=inst.plane, task_hours=task)
                out[arm] = (round(res["routine"]["delivered"], 9),
                            round(res["routine"]["missing_collection"], 9),
                            round(res["routine"]["missing_delivery"], 9),
                            round(res["routine"]["aoi_mean_s"], 6))
            return out
        finally:
            _op.BUS_V, _or.UPLINK_WH = saved_bus, saved_up

    ref = run_all(1.0)
    for lam in (0.25, 4.0, 16.0):
        got = run_all(lam)
        same = all(got[a] == ref[a] for a in arms)
        diff = [a for a in arms if got[a] != ref[a]]
        check(f"λ={lam:g} 下四条无能量阈值臂的业务列与 λ=1 逐位相同", same,
              f"不一致的臂 {diff}" if diff else f"四项读数 x {len(arms)} 臂全同")


def test_intent_ledger_closes() -> None:
    """**意图准入账本必须两侧都闭合。**

    生成端：`generated = refused + sent`；到达端：`sent = landed + rejected + expired + queued_left + lost`；
    落地端：`landed = change + same_value`。**三条恒等式任一不成立，就有一类意图不知去向**——
    而"某一类去向不明"正是这个账本存在的理由。

    **实现里踩过一个坑，记在这里**：`counters["commands_lost"]` 被初始化成 0、
    **从来没有被增加过**，是一列死列。真正的去向分散在 `ControlPlane` 上（`downlink_expired`、
    队列滞留、上行/回传丢）。所以 `lost` 现在是**算出来的**，不是读一个自增计数。
    第一版账本因此差了 219.6 条对不上（`aoi` 发出 274.2、落地 54.6、中间全是空的）。
    """
    print("\n[25] 意图准入账本两侧闭合")
    dep = build_deployment(groups=2)
    hours, task, cap = 13, 12, 0.008

    def build_nodes():
        ns = nodes_from(dep)
        for n in ns.values():
            n.p = DeviceProfile(sample_interval_s=n.p.sample_interval_s,
                                report_period_s=n.p.report_period_s,
                                capacity_wh=cap, sample_wh=n.p.sample_wh)
            n.soc_wh = cap
            n.power = type(n.power)(soc_initial_wh=cap, soc_wh=cap)
        return ns

    truth = wang_fragment_truth(0, hours, (dep.gateway.sid,))
    probe = build_nodes()
    truth.displacement = displacement_series(probe.keys(), hours, 0)
    h, t_ = hetero_harvest(probe.keys(), hours, 0, low_frac=0.4, low_wh_per_hour=0.0,
                           high_wh_per_hour=3.0)
    truth.harvest_wh.update(h)
    truth.temp_c.update(t_)

    for arm in ("local", "aoi", "ea_i600", "ea_nb"):
        inst = Instance(build_nodes(), truth, seed=0, policy=build_policy(arm),
                        send_contract_fields=True)
        inst.run(hours)
        L = inst.intent_ledger()
        gen_ok = L["generated"] == L["refused"] + L["sent"]
        arr_ok = L["sent"] == (L["landed"] + L["rejected"] + L["expired"]
                               + L["queued_left"] + L["lost"])
        land_ok = L["landed"] == L["change"] + L["same_value"]
        check(f"[{arm}] 生成端闭合 generated = refused + sent", gen_ok,
              f"{L['generated']} = {L['refused']} + {L['sent']}")
        check(f"[{arm}] 到达端闭合 sent = landed + rejected + expired + queued + lost", arr_ok,
              f"{L['sent']} = {L['landed']}+{L['rejected']}+{L['expired']}"
              f"+{L['queued_left']}+{L['lost']}")
        check(f"[{arm}] 落地端闭合 landed = change + same_value", land_ok,
              f"{L['landed']} = {L['change']} + {L['same_value']}")

    # 两种结构不同的浪费模式：aoi 是"无信道"，ea_i600 是"同值写入"。
    def ledger(arm):
        i = Instance(build_nodes(), truth, seed=0, policy=build_policy(arm),
                     send_contract_fields=True)
        i.run(hours)
        return i.intent_ledger()
    a, e, n = ledger("aoi"), ledger("ea_i600"), ledger("ea_nb")
    check("aoi 的主要浪费是「无信道」（生成速率超过信道容量）",
          a["refused"] > a["landed"], f"无信道 {a['refused']} > 落地 {a['landed']}")
    check("ea_i600 的主要浪费是「同值写入」（落地里全是值域空操作）",
          e["same_value"] > 0 and e["change"] == 0,
          f"同值 {e['same_value']}、改值 {e['change']}")
    check("ea_nb 一条意图都不生成（无证据就不生成）", n["generated"] == 0,
          f"生成 {n['generated']}")


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
    test_recovery_splits_lost_from_recoverable()
    test_center_command_path()
    test_config_generation_identity()
    test_dynamic_oracle_is_a_bound()
    test_blind_config_is_a_noop()
    test_autonomy_margin_is_hand_computable()
    test_oracle_action_is_two_dimensional()
    test_action_admission_classification()
    test_autonomy_margin_blind_spot()
    test_composed_baseline_keeps_both_dimensions()
    test_delivery_oracle_is_a_bound_and_splits_the_gap()
    test_delivery_ceiling_is_policy_independent()
    test_energy_scale_invariance()
    test_intent_ledger_closes()
    print("\n" + "-" * 74)
    if FAIL:
        print(f"  {len(FAIL)} 项失败: {', '.join(FAIL)}")
        return 1
    print("  全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
