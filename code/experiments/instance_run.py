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
from exogenous import (ObligationSet, constant_harvest, displacement_series,
                       rule_obligations_for_truth, routine_obligations_by_node,
                       wang_fragment_truth)
from network import DeviceProfile, Instance, nodes_from
from scoring import evaluate

OUT = _os.path.normpath(_os.path.join(_CODE, "..", "results"))


def one_seed(seed: int, task_hours: float, tail_hours: float) -> dict:
    hours = task_hours + tail_hours
    dep = build_deployment(groups=2)
    nodes = nodes_from(dep)
    truth = wang_fragment_truth(0, int(hours), (dep.gateway.sid,))
    truth.displacement = displacement_series(nodes.keys(), int(hours), seed)
    harvest, temp = constant_harvest(nodes.keys(), int(hours), 3.0, 10.0)
    truth.harvest_wh.update(harvest)
    truth.temp_c.update(temp)

    meas = {k: v.measurand for k, v in nodes.items()}
    obligations = ObligationSet(
        routine_obligations_by_node(meas, int(task_hours))
        + rule_obligations_for_truth(truth))

    inst = Instance(nodes, truth, seed=seed)
    log = inst.run(int(hours))
    res = evaluate(obligations, log, int(hours), nodes.keys(),
                   battery={k: v.power.to_dict() for k, v in nodes.items()},
                   plane=inst.plane, task_hours=int(task_hours))

    return {
        "seed": seed,
        "deployment": dep.summary(),
        "n_obligations": res["n_obligations"],
        "by_kind": res["by_kind"],
        "routine": res["routine"],
        "event": res["event"],
        "energy": res["energy"],
        "communication": res["communication"],
        "propagation": {k: v for k, v in res["propagation"].items() if k != "per_trigger"},
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
    ap.add_argument("--tag", default="base")
    args = ap.parse_args()

    runs = [one_seed(s, args.task_hours, args.tail_hours) for s in range(args.seeds)]

    # 聚合：分母类用求和（它们天然是整数），时延与比率类用逐种子均值
    agg = {
        "n_seeds": args.seeds,
        "task_hours": args.task_hours,
        "tail_hours": args.tail_hours,
        "routine_delivered_rate": mean([r["routine"]["delivered"] / r["routine"]["n"]
                                        for r in runs]),
        "event_match_rate": mean([r["event"]["match_rate"] for r in runs]),
        "event_deliver_rate": mean([r["event"]["deliver_rate"] for r in runs]),
        "routine_aoi_mean_s": mean([r["routine"]["aoi_mean_s"] for r in runs]),
        "routine_missing_collection": mean([r["routine"]["missing_collection"] for r in runs]),
        "routine_missing_delivery": mean([r["routine"]["missing_delivery"] for r in runs]),
        "event_missing_collection": mean([r["by_kind"]["event"]["missing_collection"]
                                          for r in runs]),
        "event_missing_delivery": mean([r["by_kind"]["event"]["missing_delivery"]
                                        for r in runs]),
        "detection_latency_mean_s": mean([r["propagation"]["detection_latency_mean_s"]
                                          for r in runs]),
        "knowledge_latency_mean_s": mean([r["propagation"]["knowledge_latency_mean_s"]
                                          for r in runs]),
        "knowledge_latency_p90_s": mean([r["propagation"]["knowledge_latency_p90_s"]
                                         for r in runs]),
        "uplinks": mean([r["communication"]["uplinks"] for r in runs]),
        "uplinks_heard": mean([r["communication"]["uplinks_heard"] for r in runs]),
        "gateway_forwarded": mean([r["communication"]["gateway_forwarded"] for r in runs]),
        "censored": mean([r["observation_window"]["censored_total"] for r in runs]),
    }

    doc = {"config": vars(args), "aggregate": agg, "runs": runs}
    _os.makedirs(OUT, exist_ok=True)
    path = _os.path.join(OUT, f"instance_{args.tag}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True, default=str)

    w = 30
    print(f"实例读数（{args.seeds} 种子，义务 {args.task_hours}h + 尾部 {args.tail_hours}h）")
    print("-" * 62)
    for k, v in agg.items():
        if isinstance(v, float):
            print(f"  {k:<{w}} {v:,.2f}")
        else:
            print(f"  {k:<{w}} {v}")
    print("-" * 62)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
