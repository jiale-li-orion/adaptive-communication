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
from exogenous import (ObligationSet, constant_harvest, displacement_series, hetero_harvest,
                       rule_obligations_for_truth, routine_obligations_by_node,
                       wang_fragment_truth)
from center import ARMS, build_policy
from network import DeviceProfile, Instance, nodes_from
from scoring import evaluate

OUT = _os.path.normpath(_os.path.join(_CODE, "..", "results"))


def one_seed(seed: int, task_hours: float, tail_hours: float,
             outage_start_h: float = 0.0, outage_hours: float = 0.0,
             arm: str = "local", contract: bool = False,
             hold_every: int = 0, hold_s: int = 0,
             harvest_wh_per_hour: float = 3.0, sample_interval_s: int = 3600,
             uplink_p_arrive: float = 0.74, backhaul_p_good: float = 0.62,
             event_spacing_s: int = 300, harvest_mode: str = "uniform",
             access_outage_h: float = 0.0,
             capacity_wh: float = 0.05, low_frac: float = 0.4,
             low_wh_per_hour: float = 0.005) -> dict:
    hours = task_hours + tail_hours
    dep = build_deployment(groups=2)
    prof = DeviceProfile(sample_interval_s=sample_interval_s,
                         event_interval_s=event_spacing_s,
                         capacity_wh=capacity_wh)
    nodes = nodes_from(dep, profile=prof)
    truth = wang_fragment_truth(0, int(hours), (dep.gateway.sid,))
    truth.displacement = displacement_series(nodes.keys(), int(hours), seed)
    if harvest_mode == "hetero":
        harvest, temp = hetero_harvest(nodes.keys(), int(hours), seed,
                                       low_frac=low_frac,
                                       low_wh_per_hour=low_wh_per_hour,
                                       high_wh_per_hour=harvest_wh_per_hour)
    else:
        harvest, temp = constant_harvest(nodes.keys(), int(hours),
                                         harvest_wh_per_hour, 10.0)
    truth.harvest_wh.update(harvest)
    truth.temp_c.update(temp)

    meas = {k: v.measurand for k, v in nodes.items()}
    obligations = ObligationSet(
        routine_obligations_by_node(meas, int(task_hours))
        + rule_obligations_for_truth(truth, spacing_s=event_spacing_s))

    acc = None
    if access_outage_h > 0:
        lo, hi = 4 * 3600, int((4 + access_outage_h) * 3600)
        acc = (lo, hi)
    inst = Instance(nodes, truth, seed=seed, policy=build_policy(arm),
                    send_contract_fields=contract, hold_every=hold_every,
                    hold_s=hold_s, access_outage=acc)
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
    log = inst.run(int(hours))
    res = evaluate(obligations, log, int(hours), nodes.keys(),
                   battery={k: v.power.to_dict() for k, v in nodes.items()},
                   plane=inst.plane, task_hours=int(task_hours), outage=outage)

    return {
        "seed": seed,
        "arm": arm,
        "exec_layer": "contract" if contract else "naive",
        "hazard": {"hold_every": hold_every, "hold_s": hold_s},
        "intent_mismatch_s": inst.intent_mismatch_s(int(hours)),
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
    ap.add_argument("--harvest-wh-per-hour", type=float, default=0.05)
    ap.add_argument("--harvest-mode", default="uniform", choices=["uniform", "hetero"])
    ap.add_argument("--capacity-wh", type=float, default=0.05)
    ap.add_argument("--low-frac", type=float, default=0.4)
    ap.add_argument("--low-wh-per-hour", type=float, default=0.005)
    ap.add_argument("--sample-interval-s", type=int, default=3600)
    ap.add_argument("--uplink-p-arrive", type=float, default=0.74)
    ap.add_argument("--backhaul-p-good", type=float, default=0.62)
    ap.add_argument("--event-spacing-s", type=int, default=300)
    ap.add_argument("--arms", default="local",
                    help="逗号分隔的中心策略，见 instance/center.py 的 ARMS")
    ap.add_argument("--access-outage-h", type=float, default=0.0,
                    help="接入中断时长（小时），固定从第 4 小时开始")
    ap.add_argument("--outage-start-h", type=float, default=0.0)
    ap.add_argument("--outage-hours", type=float, default=0.0)
    ap.add_argument("--tag", default="base")
    args = ap.parse_args()

    arm_names = [a.strip() for a in args.arms.split(",") if a.strip()]
    for a in arm_names:
        if a not in ARMS:
            raise SystemExit(f"unknown arm {a!r}; have {sorted(ARMS)}")
    layers = [x.strip() for x in args.exec_layers.split(",") if x.strip()]
    runs = [one_seed(s, args.task_hours, args.tail_hours,
                     args.outage_start_h, args.outage_hours, a,
                     contract=(L == "contract"), hold_every=args.hold_every,
                     hold_s=args.hold_s, harvest_wh_per_hour=args.harvest_wh_per_hour,
                     sample_interval_s=args.sample_interval_s,
                     uplink_p_arrive=args.uplink_p_arrive,
                     backhaul_p_good=args.backhaul_p_good,
                     event_spacing_s=args.event_spacing_s,
                     harvest_mode=args.harvest_mode, capacity_wh=args.capacity_wh,
                     low_frac=args.low_frac,
                     low_wh_per_hour=args.low_wh_per_hour,
                     access_outage_h=args.access_outage_h)
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
            "dead_nodes_end": mean([sum(1 for v in r["energy"]["per_node"].values()
                                        if v["dead_at_s"] is not None) for r in rs]),
            "deficit_h": mean([sum(v["deficit_s"] for v in r["energy"]["per_node"].values())
                               / 3600.0 for r in rs]),
            "access_blocked": mean([r["access_blocked"] for r in rs]),
            "fenced": mean([r["command_counters"].get("fenced", 0) for r in rs]),
            "deduplicated": mean([r["command_counters"].get("deduplicated", 0) for r in rs]),
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

    doc = {"config": vars(args), "aggregate": agg, "runs": runs}
    _os.makedirs(OUT, exist_ok=True)
    path = _os.path.join(OUT, f"instance_{args.tag}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True, default=str)

    w = 30
    print(f"实例读数（{args.seeds} 种子/臂，义务 {args.task_hours}h + 尾部 {args.tail_hours}h）")
    print("=" * 96)
    hdr = (f"{'arm':<18} {'周期交付':>9} {'缺采':>5} {'缺送':>6} {'AoI s':>7} "
           f"{'事件采集':>8} {'事件交付':>8} {'上行':>6} {'下行试':>6} {'死节点':>6} {'缺电h':>6}")
    print(hdr)
    print("-" * 96)
    for a in agg["arms"]:
        x = agg["arms"][a]
        print(f"{a:<18} {x['routine_delivered']:>9.1f} {x['routine_missing_collection']:>5.1f} "
              f"{x['routine_missing_delivery']:>6.1f} {x['routine_aoi_mean_s']:>7.0f} "
              f"{x['event_match']:>8.1f} {x['event_delivered']:>8.1f} "
              f"{x['uplinks']:>6.1f} {x['downlink_attempts']:>6.1f} "
              f"{x['dead_nodes_end']:>6.1f} {x['deficit_h']:>6.1f}")
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
