# -*- coding: utf-8 -*-
"""reverse_feedback_budget.py — R1（有限反向预算下的保留责任）的编码/机会账与延迟确认判别。

问题
----
`runner.py` 在回传把一批记录交给中心的那一刻调用 `rt.confirm(item.sample_ids)`，节点缓存被
同步、零空口地释放（`network.Node.ack`）。真实执行里节点要知道"中心已完成"，必须有一条反向
消息，而 Class A 每个上行机会只给一条下行。R1 假说因此是：确认与配置争用同一条下行，联合选择
才有意义。`paper/RESEARCH_PLAN.md` §4 要求**先做字节与机会账，再实现策略**，并明确：若普通
聚合能在下一次上行后顺带确认全部新接管数据、同时容纳配置，立即托管就已消除竞争，R1 关闭。

本脚本交付该账，并且不停在论证上
------------------------------
账本之外，直接把"免费瞬时确认"这个简化去掉：把 `Node.ack` 的实际清缓存动作推迟 k 个**该节点
自己的上行机会**（k=0 即现状）。这测的是同一个物理问题——反向证据晚到几个机会，会不会改变
按期交付、缺采、电量、空口与备用字节。账说"不绑定"而延迟又说"无后果"，才能关闭 R1；两者
只要有一处给出后果，就有逐事件见证可查。

臂
--
`ack0`  现状：中心收到即释放（k=0）
`ack1`  释放推迟 1 个上行机会（确认搭下一次下行）
`ack2`  推迟 2 个
`ack4`  推迟 4 个

口径与 C10 审计一致（相位 A、peak .012、ttl8、48 h、中断 4--20 h、`generic_expiry`），
因此读数可与 `results/retention_deadline_audit.json` 对照；只加确认时延这一处改动。

Run: python3 code/analysis/reverse_feedback_budget.py [--seeds 100 101 102] [--out ...]
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
for _d in ("v3joint", "instance", "physics", "runtime", "experiments", "analysis", "monitoring"):
    _p = os.path.join(ROOT, "code", _d)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import c5_common
import c5_gate

c5_gate.MODE = "task2"
c5_gate.install()
import network as net
import opportunity as _op

H = lambda h: h * 3600
SCHED = [(0, 600, "blue"), (H(2), 300, "yellow"), (H(6), 600, "blue")]
PEAK = 0.012
ARMS = ("ack0", "ack1", "ack2", "ack4")
MODE = {"k": 0}

_ORIG_ACK = net.Node.ack
_ORIG_BATCH = net.Node.batch
PENDING: dict = collections.defaultdict(list)     # node_id -> [(opp_index, [sample_id, ...])]
OPP_SEEN: collections.Counter = collections.Counter()


def ack(self, sample_ids) -> None:
    """把"中心已完成"这条反向证据按 k 个上行机会延后生效。

    k=0 走原路径。k>0 时先入队，等到该节点自己的第 (入队机会 + k) 次上行机会再真正释放——
    这正是 Class A 的形状：确认只能搭下一次接收窗口，不能凭空即时到达。
    """
    k = MODE["k"]
    ids = [s for s in (sample_ids or []) if s]
    if not ids:
        return
    if k <= 0:
        return _ORIG_ACK(self, ids)
    PENDING[self.node_id].append((OPP_SEEN[self.node_id] + k, ids))


def batch(self, t_s: int, max_slots: int = 32):
    """每次上行机会：先结算到期的确认，再按原始语义取批。"""
    OPP_SEEN[self.node_id] += 1
    if MODE["k"] > 0 and PENDING.get(self.node_id):
        now = OPP_SEEN[self.node_id]
        due = [ids for (at, ids) in PENDING[self.node_id] if at <= now]
        if due:
            PENDING[self.node_id] = [(at, ids) for (at, ids) in PENDING[self.node_id] if at > now]
            for ids in due:
                _ORIG_ACK(self, ids)
    return _ORIG_BATCH(self, t_s, max_slots)


net.Node.ack = ack
net.Node.batch = batch
c5_common.install()
from joint_run import run_joint


def budget_table() -> dict:
    """字节与机会账：现有编码下，一次上行所需的托管收据加配置能不能装进同一下行。

    判定按 `paper/RESEARCH_PLAN.md` §4 的关闭条件写死：若确认能在**下一次上行**后顺带完成、
    且同时容纳配置，则普通托管已消除候选声称的竞争，R1 关闭。这里把两个量都算出来而不是断言。
    """
    prof = _op.LoRaProfile()
    sf = 12
    dl_slots = 1                                   # Class A：每个上行机会至多一条下行
    frames = {"uplink_sample": 20, "downlink_config_field": 16, "downlink_read_status": 8,
              "bitmap_receipt_8_records": 9, "bitmap_receipt_32_records": 13}
    rows = []
    for period in (600, 300):
        slots = dl_slots * 3600 / period
        need = 2 + 1          # 一次调档两条字段消息 + 一条位图收据
        rows.append({"report_period_s": period,
                     "uplink_opportunities_per_h": round(3600 / period, 2),
                     "downlink_slots_per_h": round(slots, 2),
                     "messages_needed_per_config_cycle": need,
                     "slots_surplus_per_h": round(slots - need, 2),
                     "airtime_ms_16B_at_sf12": round(prof.time_on_air_ms(sf, 16), 1),
                     "airtime_ms_33B_at_sf12": round(prof.time_on_air_ms(sf, 33), 1)})
    return {
        "profile": {"region": prof.region, "sf_checked": sf, "bw_khz": prof.bw_khz,
                    "coding_rate": prof.coding_rate, "duty_cycle": prof.duty_cycle},
        "class_a_downlink_per_uplink": dl_slots,
        "frame_bytes": frames,
        "bitmap_receipt_encoding": "1 bit/记录 + 1 B 头",
        "opportunity_rows": rows,
        "verdict": {
            "piggyback_eliminates_claimed_contention": all(r["slots_surplus_per_h"] > 0
                                                          for r in rows),
            "closure_condition": ("下一次上行后顺带确认全部新接管数据、并同时容纳配置"),
            "reason": ("每个上行机会一条下行；一次调档需要两条字段消息加一条位图收据，共 3 条，"
                       "而 600 s 档每小时有 6 个上行机会、黄级 300 s 档有 12 个，故收据与配置"
                       "**不争用**同一个机会。竞争只在「确认必须与配置落在同一拍」时才会出现，"
                       "而这一步由下面的延迟臂直接测量其物理代价。"),
        },
    }


def run(k: int, seed: int) -> dict:
    MODE["k"] = k
    PENDING.clear()
    OPP_SEEN.clear()
    c5_common.C5Config.mode = "ttl"
    c5_common.C5Config.ttl_delta_s = 8 * H(1)
    c5_common.C5Config.peak_wh_h = PEAK
    c5_common.C5Config.task_end_s = 49 * H(1)
    r, inst, _ = run_joint(seed=seed, local_floor=True, task_hours=48, tail_hours=1, arm="local",
                           groups=2, sample_interval_s=600, report_period_s=600,
                           routine_period_s=600, harvest_mode="solar",
                           harvest_peak_wh_per_hour=PEAK, capacity_wh=0.05, initial_soc=1.0,
                           outage_start_h=4, outage_hours=16, enable_backup=True,
                           backup_rate_s=1200, backup_bytes=78, backup_chooser="maxcov",
                           cache_service="generic_expiry", mission_schedule=SCHED,
                           mission_mode="dayfeed", collect_rows=True)
    rows = [x for x in r["rows"] if x["kind"] == "routine" and not x.get("censored")]
    rr = r["routine"]
    socs = [getattr(n, "_c5_min_soc", n.soc_wh) for n in inst.nodes.values()]
    comm = r.get("communication", {})
    bk = r.get("backup", {})
    return {"svc": rr["delivered"] / rr["n"], "delivered": rr["delivered"], "n": rr["n"],
            "missing_collection": rr.get("missing_collection"),
            "missing_delivery": rr.get("missing_delivery"),
            "dead": len(r["survival"].get("dead", [])),
            "min_soc_wh": min(socs),
            "mean_final_soc": r["survival"].get("mean_final_soc"),
            "airtime_uplink_s": round(comm.get("airtime_uplink_h", 0.0) * 3600, 1),
            "airtime_downlink_s": round(comm.get("airtime_downlink_h", 0.0) * 3600, 2),
            "uplinks": comm.get("uplinks"),
            "uplinks_heard": comm.get("uplinks_heard"),
            "gateway_forwarded": comm.get("gateway_forwarded"),
            "samples_collected": comm.get("samples_collected"),
            "downlink_attempts": comm.get("downlink_attempts"),
            "backup_packets": bk.get("backup_packets"),
            "backup_bytes_sent": bk.get("backup_bytes_sent"),
            "cache_dropped": sum(getattr(n, "dropped", 0) for n in inst.nodes.values()),
            "n_rows": len(rows)}


def ci95(xs):
    n = len(xs)
    m = st.mean(xs)
    if n < 2:
        return m, m, m
    h = 1.96 * st.stdev(xs) / (n ** 0.5)
    return m, m - h, m + h


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="*", default=[100, 101, 102])
    ap.add_argument("--out", default=os.path.join("results", "reverse_feedback_budget.json"))
    args = ap.parse_args()
    out = {"script": "code/analysis/reverse_feedback_budget.py",
           "purpose": "R1 的字节/机会账与延迟确认判别（确认与配置是否真的争用同一条下行）",
           "contract": "paper/RESEARCH_PLAN.md §4",
           "phase": "A", "peak": PEAK, "seeds": args.seeds, "arms": list(ARMS),
           "encoding_budget": budget_table(), "runs": {}}
    per = {a: [] for a in ARMS}
    for s in args.seeds:
        for a in ARMS:
            row = run(int(a[3:]), s)
            per[a].append(row)
            out["runs"][f"{s}|{a}"] = row
            print(f"seed {s} {a:5s} 服务 {row['svc']:.4f}  交付 {row['delivered']:5}/{row['n']}"
                  f"  缺采 {row['missing_collection']:5}  缺交 {row['missing_delivery']:5}"
                  f"  死亡 {row['dead']:2}  minSoC {row['min_soc_wh']*1000:7.3f} mWh"
                  f"  上行 {row['airtime_uplink_s']:7.1f} s  下行 {row['airtime_downlink_s']:5.1f} s"
                  f"  备用包 {row['backup_packets']}", flush=True)
    summary = {}
    for a in ARMS:
        sv = [100 * x["svc"] for x in per[a]]
        summary[a] = {"svc_mean_pct": round(st.mean(sv), 4),
                      "delivered_total": sum(x["delivered"] for x in per[a]),
                      "n_total": sum(x["n"] for x in per[a]),
                      "missing_collection_total": sum(x["missing_collection"] or 0 for x in per[a]),
                      "missing_delivery_total": sum(x["missing_delivery"] or 0 for x in per[a]),
                      "dead_total": sum(x["dead"] for x in per[a]),
                      "min_soc_wh": min(x["min_soc_wh"] for x in per[a]),
                      "airtime_uplink_s_mean": round(st.mean([x["airtime_uplink_s"] for x in per[a]]), 1),
                      "backup_packets_total": sum(x["backup_packets"] or 0 for x in per[a])}
    for a in ARMS[1:]:
        d = [100 * (x["svc"] - y["svc"]) for x, y in zip(per[a], per["ack0"])]
        m, lo, hi = ci95(d)
        summary[a]["vs_ack0_points"] = round(m, 4)
        summary[a]["vs_ack0_ci95"] = [round(lo, 4), round(hi, 4)]
        summary[a]["vs_ack0_positive_seeds"] = sum(1 for v in d if v > 0)
        summary[a]["delivered_delta"] = [x["delivered"] - y["delivered"]
                                         for x, y in zip(per[a], per["ack0"])]
    out["summary"] = summary
    print(f"\n合计（相位 A，peak .012，ttl8，{len(args.seeds)} 种子）：")
    for a in ARMS:
        s = summary[a]
        extra = (f"  vs ack0 {s['vs_ack0_points']:+.4f} 点 CI{s['vs_ack0_ci95']}"
                 f" 交付差 {s['delivered_delta']}" if a != "ack0" else "")
        print(f"  {a:5s} 服务 {s['svc_mean_pct']:7.4f}%  交付 {s['delivered_total']}/{s['n_total']}"
              f"  缺采 {s['missing_collection_total']}  缺交 {s['missing_delivery_total']}"
              f"  死亡 {s['dead_total']}  minSoC {s['min_soc_wh']*1000:.3f} mWh"
              f"  上行均值 {s['airtime_uplink_s_mean']} s  备用包 {s['backup_packets_total']}{extra}")
    path = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("\nsaved", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
