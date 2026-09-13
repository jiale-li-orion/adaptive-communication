#!/usr/bin/env python3
"""实例读数：多节点、真实地形下的分列结果。

这是实例层**唯一**的读数脚本。它不做方法比较，只把当前实例在多个种子下的分列指标落盘，
让"这些数从哪里来"可复现（D29）。

```bash
export PYTHONPATH="$PWD/libs/pylibs"
python3 code/experiments/instance_run.py --seeds 20 --task-hours 12 --tail-hours 1 --tag base
```

**这个实例是什么。** 一个监测单元：网关带雨量计 + 13 个坡面位移测点（真实 SRTM/ITM 布点，
绕射边缘上的 3 个位点已排除）。业务事件来自 Wang 等 2022 Table 3 的公开片段（7 组触发）；
常态为 1 h 定时。采能是**合成的恒定过程**（A 层），因此**能源相关读数不得外推**。

**这个实例不是什么。** 不是真实 trace benchmark；不是任何站点的配置；不含中心下发动作。
"""
from __future__ import annotations

import argparse
import json
import os as _os, sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime", "experiments",
                                                      "analysis", "monitoring", "instance"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

from deployment import build_deployment
from exogenous import (ObligationSet, autonomy_margin, constant_harvest,
                       displacement_series, hetero_harvest, solar_harvest,
                       rule_obligations_for_truth, routine_obligations_by_node,
                       wang_fragment_truth)
from center import ARMS, ClairvoyantStaticSelector, SocObservationModel, build_policy
from network import DeviceProfile, Instance, nodes_from
from oracle import dynamic_oracle
from scoring import evaluate

OUT = _os.path.normpath(_os.path.join(_CODE, "..", "results"))


def one_seed(seed: int, task_hours: float, tail_hours: float,
             outage_start_h: float = 0.0, outage_hours: float = 0.0,
             arm: str = "local", contract: bool = False,
             hold_every: int = 0, hold_s: int = 0,
             harvest_wh_per_hour: float = 3.0, sample_interval_s: int = 3600,
             uplink_p_arrive: float = 0.74, backhaul_p_good: float = 0.62,
             event_spacing_s: int = 300, harvest_mode: str = "uniform",
             access_outage_h: float = 0.0, access_outage_start_h: float = 4.0,
             blackout_start_h: float = 0.0,
             blackout_frac: float = 0.0,
             soc_max_age_s: int | None = None, soc_noise_wh: float = 0.0,
             soc_bias: float = 1.0, soc_loss_p: float = 0.0, hold_op: str | None = None,
             atomic: bool = False, exec_label: str | None = None,
             capacity_wh: float = 0.05, low_frac: float = 0.4,
             low_wh_per_hour: float = 0.005,
             oracle_cache: dict | None = None,
             oracle_soc_bins: int = 200,
             solar_day_start_h: float = 6.0, solar_peak_wh_per_hour: float = 0.06,
             solar_cloud_p: float = 0.35, solar_cloud_atten: float = 0.25,
             solar_snow_frac: float = 0.0, solar_snow_start_h: float = 8.0,
             solar_shade_frac: float = 0.0,
             initial_soc: float = 1.0) -> dict:
    hours = task_hours + tail_hours
    dep = build_deployment(groups=2)
    prof = DeviceProfile(sample_interval_s=sample_interval_s,
                         event_interval_s=event_spacing_s,
                         capacity_wh=capacity_wh, initial_soc=initial_soc)
    nodes = nodes_from(dep, profile=prof)
    truth = wang_fragment_truth(0, int(hours), (dep.gateway.sid,))
    truth.displacement = displacement_series(nodes.keys(), int(hours), seed)
    if harvest_mode == "solar":
        # **合成**日照时间过程（A 层）。形状是研究选择，不是拟合值——结论只能读作
        # "在这个形状下如何"。见 `solar_harvest` 的文档。
        harvest, temp = solar_harvest(
            nodes.keys(), int(hours), seed, day_start_hour=solar_day_start_h,
            peak_wh_per_hour=solar_peak_wh_per_hour, cloud_p=solar_cloud_p,
            cloud_atten=solar_cloud_atten, snow_frac=solar_snow_frac,
            snow_start_h=solar_snow_start_h, shade_frac=solar_shade_frac)
    elif harvest_mode == "hetero":
        harvest, temp = hetero_harvest(nodes.keys(), int(hours), seed,
                                       low_frac=low_frac,
                                       low_wh_per_hour=low_wh_per_hour,
                                       high_wh_per_hour=harvest_wh_per_hour)
    else:
        harvest, temp = constant_harvest(nodes.keys(), int(hours),
                                         harvest_wh_per_hour, 10.0)
    if blackout_frac > 0.0:
        # **节点失电**：从第 `blackout_start_h` 小时起，一部分站点的采能被切断（积雪掩埋、
        # 线路受损）。它们仍会照常采样直到电量耗尽，**然后彻底停止**——因此后果是
        # **采集缺失**，而不是交付缺失。这是与接入/回传中断最本质的区别（v1.1 §5.3）。
        from deterministic import stable_uniform as _su
        for nid in nodes:
            if _su(seed, "blackout", nid) < blackout_frac:
                cut_at = int(blackout_start_h * 3600)
                for tt in harvest[nid]:
                    if tt >= cut_at:
                        harvest[nid][tt] = 0.0

    truth.harvest_wh.update(harvest)
    truth.temp_c.update(temp)

    # **autonomy margin**：把采能轨迹整体缩小到多少倍时，每小时的义务还服务得起。
    # 基准工作负载 = 每小时一条样（`sample_wh + UPLINK_WH`）。1 是天然分界，跨任务可比。
    # **必须与实例用同一个初始电量**，否则这个横轴描述的是另一个系统。`initial_soc=1.0`
    # （满格启动）会让 margin 恒为无穷——初始电量自己就能跑完整个任务时，采能与可行性无关，
    # 那个横轴没有任何信息量。扫 margin 时必须配一个需要采能的初始电量。
    _cost_h = (prof.sample_wh + 2.33e-5)
    margins = [autonomy_margin(harvest[nid], int(task_hours),
                               capacity_wh=capacity_wh,
                               initial_wh=initial_soc * capacity_wh,
                               cost_per_hour=_cost_h) for nid in nodes]
    margin_mean = sum(margins) / len(margins) if margins else 0.0
    margin_min = min(margins) if margins else 0.0

    meas = {k: v.measurand for k, v in nodes.items()}
    obligations = ObligationSet(
        routine_obligations_by_node(meas, int(task_hours))
        + rule_obligations_for_truth(truth, spacing_s=event_spacing_s))

    # **真上界**：逐节点、逐小时的离线动态规划，读完整未来采能轨迹。它不依赖臂，所以按
    # (种子, 条件) 记忆化——否则每个臂都会重算一遍同一个值。
    oracle_total = None
    if oracle_cache is not None:
        okey = (seed, int(task_hours), capacity_wh, initial_soc, low_frac,
                low_wh_per_hour, harvest_wh_per_hour, harvest_mode, blackout_start_h,
                blackout_frac, event_spacing_s, solar_day_start_h,
                solar_peak_wh_per_hour, solar_cloud_p, solar_cloud_atten,
                solar_snow_frac, solar_shade_frac, oracle_soc_bins)
        if okey not in oracle_cache:
            # **上界必须与实例用同一个初始电量。** 不传时 `dynamic_oracle` 默认取满容量，于是
            # `--initial-soc 0.2` 的实例被拿去比一个"满格开局"的上界——那仍然是上界（电更多只会
            # 更可行），但它放宽的正好是本轮要扫的那一维，会把 regret 系统性报小。
            oracle_cache[okey] = dynamic_oracle(
                obligations, int(task_hours), truth.harvest_wh, nodes.keys(),
                profile=prof, initial_wh=initial_soc * capacity_wh,
                soc_bins=oracle_soc_bins)["total_oracle"]
        oracle_total = oracle_cache[okey]

    acc = None
    if access_outage_h > 0:
        lo = int(access_outage_start_h * 3600)
        hi = int((access_outage_start_h + access_outage_h) * 3600)
        acc = (lo, hi)
    # 上界参考需要知道哪些站点受约束（遮荫或失电）。它读环境真值，**不是可实现策略**，
    # 只作参照；因此它由 runner 直接构造，不放进 ARMS 供一般调用。
    if arm == "clairvoyant_static":
        # **上界参考必须是真正可行的判据。** 前两版都错了，而且错法本身有信息量：
        #   · 第一版按"历史最大采能"判 → 失电从第 4 h 才切断，被切断的节点看起来仍健康；
        #   · 第二版按"全程采能总和"判 → 0.02 Wh 的电池**存不下** 4 小时采到的 0.2 Wh，
        #     早段电池满了、采能白白溢出，晚段照样饿死。
        # 也就是说：**从静态参数推不出正确的逐节点间隔**——那是一个把采能时序、电池容量与
        # 消耗率耦合起来的动态可行性问题。所以参考必须**逐节点模拟一遍稀疏/加密两条轨迹**，
        # 取可行的那条。这不是"知道参数"，这是"知道参数并且算过"。
        feasible = set()
        for nid in nodes:
            soc = prof.capacity_wh
            ok = True
            for t_s in range(0, int(hours) * 3600, 60):
                soc = min(prof.capacity_wh, soc + harvest.get(nid, {}).get(t_s, 0.0))
                if t_s % 300 == 0:
                    soc -= prof.sample_wh
                if soc <= 0:
                    ok = False
                    break
            if ok:
                feasible.add(nid)
        constrained = frozenset(nid for nid in nodes if nid not in feasible)
        pol = ClairvoyantStaticSelector(constrained)
    else:
        pol = build_policy(arm)
    inst = Instance(nodes, truth, seed=seed, policy=pol,
                    send_contract_fields=contract, hold_every=hold_every,
                    hold_s=hold_s, access_outage=acc, hold_op=hold_op,
                    atomic_generation=atomic)
    inst.plane.uplink_p_arrive = uplink_p_arrive
    inst.plane.backhaul_p_good = backhaul_p_good
    for pth in inst.plane.paths:
        object.__setattr__(pth, "p_good", backhaul_p_good)
    outage = None
    if outage_hours > 0:
        # 回传中断窗。`backhaul_gate` 只能让路径更不可用，因此中断不会给任何一方送好处。
        lo, hi = int(outage_start_h), int(outage_start_h + outage_hours)
        inst.plane.backhaul_gate = lambda hour, _lo=lo, _hi=hi: not (_lo <= hour < _hi)
        outage = (lo * 3600, hi * 3600)
    inst.soc_model = SocObservationModel(max_age_s=soc_max_age_s, noise_wh=soc_noise_wh,
                                         bias=soc_bias, loss_p=soc_loss_p, seed=seed)
    log = inst.run(int(hours))
    res = evaluate(obligations, log, int(hours), nodes.keys(),
                   battery={k: v.power.to_dict() for k, v in nodes.items()},
                   plane=inst.plane, task_hours=int(task_hours), outage=outage)

    return {
        "seed": seed,
        "arm": arm,
        "exec_layer": exec_label or ("contract" if contract else "naive"),
        "hazard": {"hold_every": hold_every, "hold_s": hold_s},
        "intent_mismatch_s": inst.intent_mismatch_s(int(hours)),
        "mixed_config_s": inst.mixed_config_ticks,
        "dynamic_oracle": oracle_total,
        "autonomy_margin": margin_mean,
        "autonomy_margin_min": margin_min,
        "command_counters": dict(inst.counters),
        "deployment": dep.summary(),
        "n_obligations": res["n_obligations"],
        "by_kind": res["by_kind"],
        "routine": res["routine"],
        "event": res["event"],
        "energy": res["energy"],
        "communication": res["communication"],
        "propagation": {k: v for k, v in res["propagation"].items() if k != "per_trigger"},
        "recovery": res.get("recovery"),
        "access_blocked": inst.access_blocked,
        "observation_window": res["observation_window"],
        "not_applicable": res["not_applicable"],
    }


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--task-hours", type=float, default=12.0)
    ap.add_argument("--tail-hours", type=float, default=1.0)
    ap.add_argument("--exec-layers", default="naive",
                    help="逗号分隔：naive(不发契约字段) / contract(发稳定身份与单调版本)")
    ap.add_argument("--hold-every", type=int, default=0,
                    help="每 k 条下发扣留一条；0 表示不扣留")
    ap.add_argument("--hold-s", type=int, default=0)
    ap.add_argument("--hold-op", default=None,
                    help="只扣留某一类字段命令，用于构造跨代混配（例如 set_sampling_interval）")
    ap.add_argument("--harvest-wh-per-hour", type=float, default=0.05)
    ap.add_argument("--harvest-mode", default="uniform", choices=["uniform", "hetero", "solar"])
    ap.add_argument("--capacity-wh", type=float, default=0.05)
    ap.add_argument("--low-frac", type=float, default=0.4)
    ap.add_argument("--low-wh-per-hour", type=float, default=0.005)
    ap.add_argument("--sample-interval-s", type=int, default=3600)
    ap.add_argument("--uplink-p-arrive", type=float, default=0.74)
    ap.add_argument("--backhaul-p-good", type=float, default=0.62)
    ap.add_argument("--event-spacing-s", type=int, default=300)
    ap.add_argument("--arms", default="local",
                    help="逗号分隔的中心策略，见 instance/center.py 的 ARMS")
    ap.add_argument("--soc-max-age-s", type=int, default=None)
    ap.add_argument("--soc-noise-wh", type=float, default=0.0)
    ap.add_argument("--soc-bias", type=float, default=1.0)
    ap.add_argument("--soc-loss-p", type=float, default=0.0)
    ap.add_argument("--blackout-start-h", type=float, default=0.0,
                    help="从第几小时起切断部分站点的采能（节点失电）")
    ap.add_argument("--blackout-frac", type=float, default=0.0)
    ap.add_argument("--access-outage-h", type=float, default=0.0,
                    help="接入中断时长（小时）")
    ap.add_argument("--access-outage-start-h", type=float, default=4.0)
    ap.add_argument("--outage-start-h", type=float, default=0.0)
    ap.add_argument("--outage-hours", type=float, default=0.0)
    ap.add_argument("--dynamic-oracle", action="store_true",
                    help="同时计算真上界（逐节点逐小时离线 DP，读完整未来采能轨迹）")
    ap.add_argument("--oracle-soc-bins", type=int, default=200)
    ap.add_argument("--initial-soc", type=float, default=1.0,
                    help="初始电量比例。扫 autonomy margin 时要用小于 1 的值")
    ap.add_argument("--solar-day-start-h", type=float, default=6.0,
                    help="运行起点对应的绝对钟点，决定 12h 窗口落在白天还是夜里")
    ap.add_argument("--solar-peak-wh-per-hour", type=float, default=0.06)
    ap.add_argument("--solar-cloud-p", type=float, default=0.35)
    ap.add_argument("--solar-cloud-atten", type=float, default=0.25)
    ap.add_argument("--solar-snow-frac", type=float, default=0.0)
    ap.add_argument("--solar-snow-start-h", type=float, default=8.0)
    ap.add_argument("--solar-shade-frac", type=float, default=0.0)
    ap.add_argument("--tag", default="base")
    args = ap.parse_args()

    arm_names = [a.strip() for a in args.arms.split(",") if a.strip()]
    for a in arm_names:
        if a not in ARMS and a != "clairvoyant_static":
            raise SystemExit(f"unknown arm {a!r}; have {sorted(ARMS)} + clairvoyant_static")
    layers = [x.strip() for x in args.exec_layers.split(",") if x.strip()]
    for L in layers:
        if L not in ("naive", "contract", "atomic"):
            raise SystemExit(f"unknown exec layer {L!r}; have naive/contract/atomic")
    _oracle_cache: dict = {}
    runs = [one_seed(s, args.task_hours, args.tail_hours,
                     args.outage_start_h, args.outage_hours, a,
                     contract=(L in ("contract", "atomic")), hold_every=args.hold_every,
                     atomic=(L == "atomic"), exec_label=L,
                     hold_s=args.hold_s, harvest_wh_per_hour=args.harvest_wh_per_hour,
                     sample_interval_s=args.sample_interval_s,
                     uplink_p_arrive=args.uplink_p_arrive,
                     backhaul_p_good=args.backhaul_p_good,
                     event_spacing_s=args.event_spacing_s,
                     harvest_mode=args.harvest_mode, capacity_wh=args.capacity_wh,
                     low_frac=args.low_frac,
                     low_wh_per_hour=args.low_wh_per_hour,
                     access_outage_h=args.access_outage_h,
                     access_outage_start_h=args.access_outage_start_h,
                     blackout_start_h=args.blackout_start_h,
                     blackout_frac=args.blackout_frac,
                     soc_max_age_s=args.soc_max_age_s, soc_noise_wh=args.soc_noise_wh,
                     soc_bias=args.soc_bias, soc_loss_p=args.soc_loss_p,
                     hold_op=args.hold_op,
                     oracle_cache=(_oracle_cache if args.dynamic_oracle else None),
                     oracle_soc_bins=args.oracle_soc_bins,
                     solar_day_start_h=args.solar_day_start_h,
                     solar_peak_wh_per_hour=args.solar_peak_wh_per_hour,
                     solar_cloud_p=args.solar_cloud_p,
                     solar_cloud_atten=args.solar_cloud_atten,
                     solar_snow_frac=args.solar_snow_frac,
                     solar_snow_start_h=args.solar_snow_start_h,
                     solar_shade_frac=args.solar_shade_frac,
                     initial_soc=args.initial_soc)
            for a in arm_names for L in layers for s in range(args.seeds)]

    # 聚合：**按臂分组**。分母类用求和天然是整数，时延与比率类用逐种子均值。
    def agg_of(rs):
        a = {
            "n_seeds": len(rs),
            "routine_delivered": mean([r["routine"]["delivered"] for r in rs]),
            "routine_missing_collection": mean([r["routine"]["missing_collection"] for r in rs]),
            "routine_missing_delivery": mean([r["routine"]["missing_delivery"] for r in rs]),
            "routine_aoi_mean_s": mean([r["routine"]["aoi_mean_s"] for r in rs]),
            "event_match": mean([r["event"]["slots_matched_by_collection"] for r in rs]),
            "event_delivered": mean([r["event"]["slots_delivered"] for r in rs]),
            "event_missing_delivery": mean([r["by_kind"]["event"]["missing_delivery"]
                                            for r in rs]),
            "knowledge_latency_mean_s": mean([r["propagation"]["knowledge_latency_mean_s"]
                                              for r in rs]),
            "uplinks": mean([r["communication"]["uplinks"] for r in rs]),
            "uplinks_heard": mean([r["communication"]["uplinks_heard"] for r in rs]),
            "downlink_attempts": mean([(r["communication"].get("downlink_attempts") or 0)
                                       for r in rs]),
            "commands_sent": mean([r["command_counters"]["commands_sent"] for r in rs]),
            "commands_delivered": mean([r["command_counters"]["commands_delivered"]
                                        for r in rs]),
            "commands_refused": mean([r["command_counters"]["commands_refused"] for r in rs]),
            "censored": mean([r["observation_window"]["censored_total"] for r in rs]),
            "intent_mismatch_min": mean([r["intent_mismatch_s"] / 60.0 for r in rs]),
            "mixed_config_min": mean([r["mixed_config_s"] / 60.0 for r in rs]),
            "dead_nodes_end": mean([sum(1 for v in r["energy"]["per_node"].values()
                                        if v["dead_at_s"] is not None) for r in rs]),
            "deficit_h": mean([sum(v["deficit_s"] for v in r["energy"]["per_node"].values())
                               / 3600.0 for r in rs]),
            "access_blocked": mean([r["access_blocked"] for r in rs]),
            "fenced": mean([r["command_counters"].get("fenced", 0) for r in rs]),
            "deduplicated": mean([r["command_counters"].get("deduplicated", 0) for r in rs]),
            # `inf`（初始电量自己就够跑完，采能与可行性无关）不进均值，否则会把均值拉成 inf。
            # **全部为 inf 时报 `None`，不报 0**——报 0 会变成一列看起来有值、实际是回退默认值的
            # 假数据，而 0 在这个定义下恰恰意味着"完全不可行"，正好读反。
            "autonomy_margin": (mean([r["autonomy_margin"] for r in rs
                                      if r["autonomy_margin"] != float("inf")])
                                if any(r["autonomy_margin"] != float("inf") for r in rs)
                                else None),
            "autonomy_margin_min": (mean([r["autonomy_margin_min"] for r in rs
                                          if r["autonomy_margin_min"] != float("inf")])
                                    if any(r["autonomy_margin_min"] != float("inf")
                                           for r in rs) else None),
            "dynamic_oracle": mean([r["dynamic_oracle"] for r in rs
                                    if r.get("dynamic_oracle") is not None]) if any(
                r.get("dynamic_oracle") is not None for r in rs) else None,
            # 达标率 = **周期交付** / 真上界。**分子分母必须是同一个量**：真上界只覆盖周期义务
            # （事件义务靠触发锚定的本地采样，上界的动作集够不到，且事件列在全部臂上恒定、
            # 明令不得支撑结论）。曾经这里用"周期+事件"做分子，于是 dense600 在容量 0.05 下
            # 报出 100.1% 的达标率——**上界被突破**。与"相对事后最优固定配置"的 regret 不同，
            # 这个分母不受测试条件改变的操纵。
            "oracle_coverage": (mean([r["routine"]["delivered"] for r in rs]) /
                                mean([r["dynamic_oracle"] for r in rs
                                      if r.get("dynamic_oracle") is not None])
                                if any(r.get("dynamic_oracle") is not None for r in rs)
                                else None),
        }
        if args.outage_hours > 0:
            rec = [r["recovery"] for r in rs if r["recovery"]]
            a.update({
                "recovery_n_obligations": mean([x["n_obligations_in_window"] for x in rec]),
                "recovery_delivered": mean([x["delivered"] for x in rec]),
                "recovery_missing_collection": mean([x["missing_collection"] for x in rec]),
                "recovery_missing_delivery": mean([x["missing_delivery"] for x in rec]),
                "recovery_backlog_recovered": mean([x["backlog_recovered"] for x in rec]),
            })
        return a

    agg = {"n_seeds": args.seeds, "task_hours": args.task_hours,
           "tail_hours": args.tail_hours, "config": vars(args), "arms": {}}
    for a in arm_names:
        for L in layers:
            key = a if layers == ["naive"] else f"{a}__{L}"
            agg["arms"][key] = agg_of([r for r in runs
                                       if r["arm"] == a and r["exec_layer"] == L])

    # **后验最优固定**：如果知道这个测试条件、可以重新标定，最好的固定配置能到多少。
    # 它把"标定差距"与"反馈收益"分开：固定配置的 regret 相对它算，反馈的优势相对它算。
    fixed_keys = [k for k in agg["arms"] if k.startswith("dense") and "__" not in k]
    if len(fixed_keys) >= 2:
        best = max(fixed_keys, key=lambda k: agg["arms"][k]["routine_delivered"])
        agg["best_fixed_posthoc"] = dict(agg["arms"][best])
        agg["best_fixed_posthoc"]["_which"] = best


    doc = {"config": vars(args), "aggregate": agg, "runs": runs}
    _os.makedirs(OUT, exist_ok=True)
    path = _os.path.join(OUT, f"instance_{args.tag}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True, default=str)

    w = 30
    print(f"实例读数（{args.seeds} 种子/臂，义务 {args.task_hours}h + 尾部 {args.tail_hours}h）")
    print("=" * 96)
    hdr = (f"{'arm':<18} {'周期交付':>9} {'缺采':>5} {'缺送':>6} {'AoI s':>7} "
           f"{'事件采集':>8} {'事件交付':>8} {'上行':>6} {'下行试':>6} {'死节点':>6} {'混配min':>8}"
           + (" {:>8} {:>8}".format("真上界", "周期达标%") if args.dynamic_oracle else "")
           + (" {:>9} {:>9}".format("margin均", "margin最小")
              if args.harvest_mode == "solar" else ""))
    print(hdr)
    print("-" * 96)
    for a in agg["arms"]:
        x = agg["arms"][a]
        print(f"{a:<18} {x['routine_delivered']:>9.1f} {x['routine_missing_collection']:>5.1f} "
              f"{x['routine_missing_delivery']:>6.1f} {x['routine_aoi_mean_s']:>7.0f} "
              f"{x['event_match']:>8.1f} {x['event_delivered']:>8.1f} "
              f"{x['uplinks']:>6.1f} {x['downlink_attempts']:>6.1f} "
              f"{x['dead_nodes_end']:>6.1f} {x['mixed_config_min']:>8.0f}"
              + (" {:>8.1f} {:>7.1f}%".format(x["dynamic_oracle"] or 0.0,
                                              100.0 * (x["oracle_coverage"] or 0.0))
                 if args.dynamic_oracle else "")
              + (" {:>9} {:>9}".format(
                     "—" if x["autonomy_margin"] is None else f"{x['autonomy_margin']:.2f}",
                     "—" if x["autonomy_margin_min"] is None
                     else f"{x['autonomy_margin_min']:.2f}")
                 if args.harvest_mode == "solar" else ""))
    print("=" * 96)
    if args.outage_hours > 0:
        print("恢复分列（中断窗内 + 固定恢复观察期）")
        for a in agg["arms"]:
            x = agg["arms"][a]
            print(f"  {a:<18} 义务 {x['recovery_n_obligations']:.0f} 交付 {x['recovery_delivered']:.1f} "
                  f"缺采 {x['recovery_missing_collection']:.1f} 缺送 {x['recovery_missing_delivery']:.1f} "
                  f"补发追回 {x['recovery_backlog_recovered']:.1f}")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
