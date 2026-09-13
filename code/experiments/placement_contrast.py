"""§31 候选 1 第一项判别：**同一确定性策略置于中心 vs 网关**。

判定规则**先写定**在
`docs/s7-method/instance-v1/33-pre-registration-placement-2026-09-14.md`；
本脚本只负责执行与读数，**不得**按结果回头改规则。

唯一改变的变量（§31 第 108 行）：规则**在哪求值**、命令**从哪产生**。
策略对象与参数、义务、初值、空口机会、节点队列、接收窗口、能耗模型、未来外生过程全部相同。

    python3 code/experiments/placement_contrast.py --seeds 20 --arms ea_aoi,aoi
"""
from __future__ import annotations

import argparse
import json
import os as _os
import statistics as st
import sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, _CODE,
           *(_os.path.join(_CODE, d) for d in
             ("physics", "runtime", "analysis", "instance", "monitoring"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

from instance_run import one_seed                                        # noqa: E402

OUT = _os.path.normpath(_os.path.join(_CODE, "..", "results"))

#: **已登记条件**：逐项照 `results/instance_arms.json` 的 `config` 块固定。
#: 不在此处临时改任何值——条件一变，"与已登记前沿可比"就不成立。
BASE = dict(
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
    atomic=False,
)

#: 四档条件（§31 第 53 行）。四档共用**同一批种子**，因此同一种子下外生过程逐位相同。
CONDITIONS = {
    "C0_no_outage": {},
    "C1_backhaul": dict(outage_start_h=4.0, outage_hours=3.0),
    "C2_access": dict(access_outage_start_h=4.0, access_outage_h=3.0),
    "C3_both": dict(outage_start_h=4.0, outage_hours=3.0,
                    access_outage_start_h=4.0, access_outage_h=3.0),
}
PLACEMENTS = ("center", "gateway")

#: 中断窗（秒）。四档里凡有中断的都是同一个窗，便于对照。
OUT_START_S, OUT_END_S = 4 * 3600, 7 * 3600


def extract(run: dict) -> dict:
    """把 §31 第 53 行要求的五项记录量从一次运行里取出来。"""
    rt = run["routine"]
    en = (run.get("energy") or {}).get("per_node") or {}
    cm = run.get("communication") or {}
    cc = run.get("command_counters") or {}
    consumed = [v.get("consumed_wh") or 0.0 for v in en.values()]
    finals = [v.get("soc_final_wh") for v in en.values() if v.get("soc_final_wh") is not None]
    return {
        # ① 服务
        "service": rt["delivered"], "service_denom": rt["n"],
        # ② 缺采（另有缺送单列，不与缺采混）
        "missing_collection": rt["missing_collection"],
        "missing_delivery": rt["missing_delivery"],
        "aoi_mean_s": rt["aoi_mean_s"],
        # ③ 能源
        "energy_consumed_wh": round(sum(consumed), 8),
        "nodes_dead": sum(1 for v in en.values() if v.get("dead_at_s") is not None),
        "soc_final_min_wh": (min(finals) if finals else None),
        # ⑤ 通信量（**按来源分列**：省的是哪一段必须看得见）
        "uplinks": cm.get("uplinks"),
        "uplinks_heard": cm.get("uplinks_heard"),
        "downlink_attempts": cm.get("downlink_attempts"),
        "airtime_uplink_h": cm.get("airtime_uplink_h"),
        "airtime_downlink_h": cm.get("airtime_downlink_h"),
        "commands_sent": cc.get("commands_sent"),
        "commands_sent_by_gateway": cc.get("commands_sent_by_gateway", 0),
        "commands_refused": cc.get("commands_refused"),
        "mixed_config_s": run.get("mixed_config_s"),
    }


def _cfg_changes(events) -> list[dict]:
    """④ 配置生效时刻：从 trace 的 `state` 事件里取每台节点配置**真正变化**的时刻。

    `state` 是节点侧**此刻真实在跑什么**（两个周期字段 + 电量 + 是否活着），
    因此它的变化点就是"生效时刻"的定义——**不是**"中心发出了什么"。
    每台节点的首个观测只作基线，不计为一次变化。
    """
    last: dict[str, tuple] = {}
    out = []
    for ev in events:
        if ev[2] != "state":
            continue
        _t, nid, _k, i, r = ev[0], ev[1], ev[2], ev[3], ev[4]
        if nid not in last:
            last[nid] = (i, r)
            continue
        if last[nid] != (i, r):
            last[nid] = (i, r)
            out.append({"t_s": _t, "node": nid,
                        "sampling_interval_s": i, "report_period_s": r})
    return out


def _plans(events) -> list[dict]:
    """意图生成时刻，连同**这条决策所用证据的年龄**。

    `soc_age_s`（trace 的 `plan` 事件第 6 项）按**源时刻**算，正是"做出这个判断时，
    我手里的证据有多旧"。两处放置的对照量就落在这里：中心读中心收到的遥测，
    网关读网关自己听到的遥测，同一套规则因此拿到**不同年龄的证据**。
    """
    return [{"t_s": ev[0], "node": ev[1], "op": ev[4], "value": ev[5],
             "evidence_age_s": ev[6], "reason": ev[7]}
            for ev in events if ev[2] == "plan"]


def summarise(runs: list[dict]) -> dict:
    keys = [k for k in extract(runs[0]) if k not in ("service_denom",)]
    out = {}
    for k in keys:
        vals = [extract(r)[k] for r in runs]
        vals = [v for v in vals if v is not None]
        out[k] = round(st.mean(vals), 4) if vals else None
    out["n_seeds"] = len(runs)
    return out


def trace_readout(runs_with_trace: list[dict]) -> dict:
    """从带 trace 的运行里取**因果轨迹**（§31 第 109 行）。"""
    plans, changes, ages = [], [], []
    for r in runs_with_trace:
        ev = r.get("_trace") or []
        plans += _plans(ev)
        ics = _cfg_changes(ev)
        changes += ics
        ages += [p["evidence_age_s"] for p in plans if p["evidence_age_s"] is not None]
    in_out = [c for c in changes if OUT_START_S <= c["t_s"] < OUT_END_S]
    after = [c for c in changes if c["t_s"] >= OUT_END_S]
    return {
        "n_plan_intents": len(plans),
        "first_plan_t_s": (min((p["t_s"] for p in plans), default=None)),
        "evidence_age_s": {
            "min": (min(ages) if ages else None),
            "median": (st.median(ages) if ages else None),
            "max": (max(ages) if ages else None),
            "mean": (round(st.mean(ages), 1) if ages else None),
        },
        "n_config_changes": len(changes),
        "config_changes_in_outage": len(in_out),
        "first_config_change_t_s": (min((c["t_s"] for c in changes), default=None)),
        "first_config_change_after_outage_t_s": (min((c["t_s"] for c in after), default=None)),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--arms", default="ea_aoi,aoi")
    ap.add_argument("--trace-seeds", type=int, default=3,
                    help="带 trace 的种子数（只用于因果轨迹，不改变行为）")
    ap.add_argument("--out", default="placement_contrast")
    args = ap.parse_args()

    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    seeds = list(range(args.seeds))
    result: dict = {"config": {"base": BASE, "conditions": CONDITIONS,
                               "placements": list(PLACEMENTS), "arms": arms,
                               "seeds": args.seeds, "trace_seeds": args.trace_seeds},
                    "aggregate": {}, "trajectory": {}, "raw": {}}

    for arm in arms:
        result["aggregate"][arm] = {}
        for cond, extra in CONDITIONS.items():
            result["aggregate"][arm][cond] = {}
            per_placement: dict[str, list[dict]] = {}
            for pl in PLACEMENTS:
                runs = []
                for s in seeds:
                    r = one_seed(s, arm=arm, placement=pl, **BASE, **extra)
                    runs.append(r)
                per_placement[pl] = runs
                result["aggregate"][arm][cond][pl] = summarise(runs)
                result["raw"].setdefault(arm, {}).setdefault(cond, {})[pl] = \
                    [extract(r) for r in runs]
            # **配对差**：同一种子下 gateway − center。只报差值与其符号计数，
            # 不替读者决定"是否显著"——样本量小，显著性要另说。
            c, g = per_placement["center"], per_placement["gateway"]
            diffs = {}
            for k in ("service", "missing_collection", "missing_delivery", "aoi_mean_s",
                      "energy_consumed_wh", "downlink_attempts", "commands_sent",
                      "uplinks", "airtime_uplink_h"):
                d = [extract(gi)[k] - extract(ci)[k]
                     for ci, gi in zip(c, g)
                     if extract(gi)[k] is not None and extract(ci)[k] is not None]
                if d:
                    diffs[k] = {"mean": round(st.mean(d), 4),
                                "min": round(min(d), 4), "max": round(max(d), 4),
                                "n_gt0": sum(1 for x in d if x > 1e-9),
                                "n_lt0": sum(1 for x in d if x < -1e-9),
                                "n_eq0": sum(1 for x in d if abs(x) <= 1e-9),
                                "n": len(d)}
            result["aggregate"][arm][cond]["_paired_gateway_minus_center"] = diffs

    # 因果轨迹：只对每个臂的前 `trace_seeds` 个种子开 trace（**不改变行为**，已核）。
    for arm in arms:
        result["trajectory"][arm] = {}
        for cond, extra in CONDITIONS.items():
            result["trajectory"][arm][cond] = {}
            for pl in PLACEMENTS:
                runs = [one_seed(s, arm=arm, placement=pl, trace=True, **BASE, **extra)
                        for s in range(args.trace_seeds)]
                result["trajectory"][arm][cond][pl] = trace_readout(runs)

    path = _os.path.join(OUT, f"{args.out}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    print(f"wrote {path}")
    _print_table(result, arms)


def _print_table(result: dict, arms: list[str]) -> None:
    print()
    print("执行位置对照（同一策略，只有求值位置与命令来源不同）——按 §31 第 53 行五项记录量")
    print("=" * 118)
    hdr = (f"{'条件':<14}{'位置':<9}{'服务':>7}{'缺采':>7}{'缺送':>7}{'AoI s':>8}"
           f"{'能耗Wh':>10}{'下行试':>8}{'命令':>7}{'网关发':>7}{'上行':>7}")
    print(hdr)
    print("-" * 118)
    for arm in arms:
        print(f"### 臂 {arm}")
        for cond in CONDITIONS:
            for pl in PLACEMENTS:
                a = result["aggregate"][arm][cond][pl]
                print(f"{cond:<14}{pl:<9}{a['service']:>7.1f}{a['missing_collection']:>7.1f}"
                      f"{a['missing_delivery']:>7.1f}{(a['aoi_mean_s'] or 0):>8.0f}"
                      f"{a['energy_consumed_wh']:>10.4f}{(a['downlink_attempts'] or 0):>8.1f}"
                      f"{(a['commands_sent'] or 0):>7.1f}{a['commands_sent_by_gateway']:>7.1f}"
                      f"{(a['uplinks'] or 0):>7.0f}")
            d = result["aggregate"][arm][cond]["_paired_gateway_minus_center"]
            svc = d.get("service", {})
            print(f"{'':<14}{'Δ(网关-中心)':<9}服务 {svc.get('mean')} "
                  f"(更好{svc.get('n_gt0')}/更差{svc.get('n_lt0')}/平{svc.get('n_eq0')}, n={svc.get('n')})"
                  f" | 缺采 {d.get('missing_collection', {}).get('mean')}"
                  f" | 下行 {d.get('downlink_attempts', {}).get('mean')}")
        print("-" * 118)
    print()
    print("因果轨迹（证据年龄 = 该次决策所用证据有多旧；配置生效时刻取节点真实状态变化点）")
    print("-" * 118)
    for arm in arms:
        for cond in CONDITIONS:
            row = []
            for pl in PLACEMENTS:
                t = result["trajectory"][arm][cond][pl]
                row.append(f"{pl}: 意图{t['n_plan_intents']} 证据年龄中位{t['evidence_age_s']['median']}"
                           f" 配置变化{t['n_config_changes']}")
            print(f"{arm:<8}{cond:<14}" + " | ".join(row))


if __name__ == "__main__":
    main()
