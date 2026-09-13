"""产出**一条完整的逐 epoch 决策时间线**（§31 第 109 行的因果轨迹要求）。

判定 A 的聚合读数在 `placement_contrast.json`；本文档线要的是**把链连起来**：
新证据何时在两处分别可见、目标何时生成、配置何时真正生效、以及这些怎么落到缺采／交付。
**聚合量存不下这条链**，所以这里单独落一份。

两个放置各自跑**同一个种子、同一套外生过程**（回传中断窗 [4h,7h) 相同），
因此两条时间线的差异**只能来自"规则在哪求值、命令从哪产生"**。

    python3 code/analysis/placement_timeline.py

写 `results/placement_timeline.json`。
"""
from __future__ import annotations

import json
import os as _os
import sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, _CODE,
           *(_os.path.join(_CODE, d) for d in
             ("physics", "runtime", "experiments", "analysis", "monitoring", "instance"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

from instance_run import one_seed                                        # noqa: E402

RES = _os.path.normpath(_os.path.join(_CODE, "..", "results"))
ARM, SEED = "ea_aoi", 0
OUT_START_S, OUT_END_S = 4 * 3600, 7 * 3600
#: 与 `placement_contrast.py` 的 `BASE + C1_backhaul` 逐项相同（已登记条件）。
KW = dict(
    task_hours=12.0, tail_hours=1.0,
    harvest_wh_per_hour=0.05, harvest_mode="uniform",
    capacity_wh=0.05, low_frac=0.4, low_wh_per_hour=0.005,
    sample_interval_s=3600, report_period_s=3600, routine_period_s=3600,
    uplink_p_arrive=0.74, backhaul_p_good=0.62, event_spacing_s=300,
    with_events=True, initial_soc=1.0, idle_wh_per_tick=0.0,
    charge_min_c=5.0, cache_service="fifo",
    solar_day_start_h=6.0, solar_peak_wh_per_hour=0.06,
    solar_cloud_p=0.35, solar_cloud_atten=0.25,
    soc_max_age_s=None, soc_noise_wh=0.0, soc_bias=1.0, soc_loss_p=0.0,
    contract=False, exec_label="naive", hold_every=0, hold_s=0, hold_op=None,
    atomic=False, trace=True,
    outage_start_h=4.0, outage_hours=3.0,          # C1 回传中断
)


def timeline(events) -> dict:
    """把 trace 事件整理成逐 epoch 行 + 两条事件链。

    逐 epoch 行只放**决策相关**的聚合（不复制 14 台节点的原始读数）：
    `t_s`、有证据的节点数、最旧证据年龄、在途命令数、超期节点数。
    事件链放全：`plans`（目标生成时刻 + 该决策所用**证据年龄**）与
    `config_changes`（节点**真实**配置变化 = 生效时刻）。
    """
    per_epoch: dict[int, dict] = {}
    plans, changes = [], []
    last_cfg: dict[str, tuple] = {}
    soc_age_now: dict[str, int | None] = {}
    for ev in events:
        t_s, nid, kind = ev[0], ev[1], ev[2]
        row = per_epoch.setdefault(t_s, {"t_s": t_s, "n_nodes": 0, "n_with_evidence": 0,
                                         "max_evidence_age_s": None, "n_overdue": 0,
                                         "n_in_flight": 0})
        if kind == "state":
            _t, _n, _k, i, r, _soc, _alive = ev
            row["n_nodes"] += 1
            if nid not in last_cfg:
                last_cfg[nid] = (i, r)
            elif last_cfg[nid] != (i, r):
                last_cfg[nid] = (i, r)
                changes.append({"t_s": t_s, "node": nid,
                                "sampling_interval_s": i, "report_period_s": r})
        elif kind == "plan":
            _t, _n, _k, soc, op, val, age, reason = ev
            if age is not None:
                row["n_with_evidence"] += 1
                cur = row["max_evidence_age_s"]
                row["max_evidence_age_s"] = age if cur is None else max(cur, age)
                soc_age_now[nid] = age
            plans.append({"t_s": t_s, "node": nid, "soc_wh": soc, "op": op, "value": val,
                          "evidence_age_s": age, "reason": reason})
        elif kind == "sent":
            pass          # `sent` 只是下发侧的成本记账，决策链由上两类构成
    epochs = [per_epoch[k] for k in sorted(per_epoch)]
    # 超期 = 该 epoch 里证据年龄超过一个义务周期（3600 s）的节点数；用于看"证据到底多旧"。
    for row in epochs:
        row["n_overdue"] = sum(1 for a in soc_age_now.values()
                               if a is not None and a > 3600)
    return {"epochs": epochs, "plans": plans, "config_changes": changes}


def main() -> None:
    out = {"arm": ARM, "seed": SEED, "condition": "C1_backhaul",
           "outage_window_s": [OUT_START_S, OUT_END_S],
           "note": ("两个放置用**同一个种子、同一套外生过程**；差异只能来自"
                    "『规则在哪求值、命令从哪产生』。`plans` 里的 `evidence_age_s` 是"
                    "**该次决策所用证据有多旧**（按源时刻算）——它就是"
                    "『新证据何时在该位置可见』的可观测代理。"),
           "placements": {}}
    for pl in ("center", "gateway"):
        d = one_seed(SEED, arm=ARM, placement=pl, **KW)
        tl = timeline(d["_trace"])
        rt = d["routine"]
        out["placements"][pl] = {
            **tl,
            "metrics": {"service": rt["delivered"], "denom": rt["n"],
                        "missing_collection": rt["missing_collection"],
                        "missing_delivery": rt["missing_delivery"],
                        "aoi_mean_s": rt["aoi_mean_s"],
                        "commands_sent": d["command_counters"].get("commands_sent"),
                        "commands_sent_by_gateway":
                            d["command_counters"].get("commands_sent_by_gateway", 0),
                        "mixed_config_s": d["mixed_config_s"]},
        }
    path = _os.path.join(RES, "placement_timeline.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"wrote {path}")
    for pl, blk in out["placements"].items():
        ages = [p["evidence_age_s"] for p in blk["plans"] if p["evidence_age_s"] is not None]
        in_out = [c for c in blk["config_changes"] if OUT_START_S <= c["t_s"] < OUT_END_S]
        after = [c for c in blk["config_changes"] if c["t_s"] >= OUT_END_S]
        print(f"  {pl:<8} epoch={len(blk['epochs'])} 意图={len(blk['plans'])} "
              f"证据年龄中位={sorted(ages)[len(ages)//2] if ages else None} "
              f"配置变化={len(blk['config_changes'])}（中断内 {len(in_out)}）"
              f" 中断后首次生效={min((c['t_s'] for c in after), default=None)} "
              f"服务={blk['metrics']['service']}/{blk['metrics']['denom']}")


if __name__ == "__main__":
    main()
