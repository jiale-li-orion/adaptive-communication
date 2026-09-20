# -*- coding: utf-8 -*-
"""control_deadline_witness.py — 控制的截止：命令下发时机的救回与节省见证。

问题（审阅者限定）：固定采样、普通 expiry、maxcov、本地能量规则与**有限主备资源**不变时，
通过既有 `set_report_period` 的**合法下发时机**，能否跨过一条本来错过的可用回传机会，
或在服务不减时减少真实通信成本？

方法：相同前缀分歧。先用 `odp` 臂跑一遍，记下策略**首次下发**的时刻 T0；再跑一条臂把
T0 之后的全部下发整体推迟 D 秒（推迟窗口内 `plan` 直接返回空、且**不推进策略内部状态**，
因此推迟臂在窗口结束后仍会下发它本该发的那条命令）。两次运行同种子、同参数，因此 T0 之前
的轨迹逐位相同，分歧只来自下发时机。

三臂
----
`early`  原样 ODP（首次下发发生在 T0）
`late`   同一条命令推迟 D 秒才允许下发
`quiet`  从不下发（检验"网关已有窗口内副本时不下发"是否服务不减而成本下降）

见证 A（救回）：`early` 交付而 `late` 未交付的义务，且反向位移数不超过救回数。
见证 B（节省）：`quiet` 相对 `early` 服务不降而真实上行/空口/下行成本下降。

必须计入的时序限制：快报命令不能加速承载其自身接收窗口的那次上行（LoRaWAN 1.0.1 §3.3），
因此见证只认"生效之后"的机会，不把已听到的那份样本算作救回。

Run: python3 code/analysis/control_deadline_witness.py [--delay 900] [--seed 0]
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
for _d in ("v3joint", "instance", "physics", "runtime", "experiments", "analysis", "monitoring"):
    _p = os.path.join(ROOT, "code", _d)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import network as net
from joint_run import run_joint

H = lambda h: h * 3600
UP_ONLY = [(0, 600, "blue"), (6 * H(1), 300, "yellow")]
BASE = dict(task_hours=48, tail_hours=1, arm="odp", groups=2,
            sample_interval_s=600, report_period_s=600, routine_period_s=600,
            harvest_mode="solar", harvest_peak_wh_per_hour=0.03, capacity_wh=0.05,
            initial_soc=1.0, outage_start_h=4, outage_hours=16, enable_backup=True,
            backup_rate_s=1200, backup_bytes=78, backup_chooser="maxcov",
            cache_service="generic_expiry", mission_schedule=UP_ONLY,
            # **必须 None**：`joint_run` 里 `elif mission_mode is not None` 排在 `elif arm == "odp"`
            # 之前，只要传了 mission_mode，网关侧的 ObligationDeliveryPolicy 分支就不可达
            # （实测拿到的是 MissionChangePolicy、且零下发）。传 None 才能进入 ODP 分支。
            mission_mode=None, collect_rows=True)

APPLY: dict = collections.defaultdict(list)      # node -> [(t, interval)] 生效档位变更
CTL = {"mode": "early", "t0": None, "delay_s": 900}


import obligation_policy as _op

_ORIG_PLAN = _op.ObligationDeliveryPolicy.plan


def plan(self, view):
    """类级包装：控制下发时机，并记录首次下发时刻。

    推迟臂在窗口内**直接返回空**（不调用原 plan），因此策略内部的 `_last/_issued` 不推进，
    窗口结束后它仍会下发本该下发的命令——这就是"晚一点才允许下发"的干净实现。
    """
    t = view.t_s
    if CTL["mode"] == "quiet":
        return []
    if CTL["mode"] == "late" and CTL["t0"] is not None and t < CTL["t0"] + CTL["delay_s"]:
        return []
    out = _ORIG_PLAN(self, view)
    if out and CTL["t0"] is None:
        CTL["t0"] = t
    return out


_op.ObligationDeliveryPolicy.plan = plan


_ORIG_FLOOR = net.Node._apply_local_floor


def floor(self, t_s):
    before = self.sample_interval_s
    _ORIG_FLOOR(self, t_s)
    if self.sample_interval_s != before:
        APPLY[self.node_id].append((t_s, self.sample_interval_s))


net.Node._apply_local_floor = floor


def run(seed: int) -> dict:
    APPLY.clear()
    r, inst, _ = run_joint(seed=seed, **BASE)
    rows = [x for x in r["rows"] if x["kind"] == "routine" and not x.get("censored")]
    return {"result": r, "inst": inst, "rows": rows,
            "delivered": {x["oid"] for x in rows if x["delivered"]},
            "apply": {k: list(v) for k, v in APPLY.items()},
            "comm": {k: r["communication"].get(k) for k in
                     ("airtime_uplink_h", "airtime_downlink_h", "downlink_attempts")},
            "backup": {k: r["backup"].get(k) for k in
                       ("backup_packets", "backup_bytes_sent", "backup_on", "backup_late")}}


def timeline(rows, oid):
    for x in rows:
        if x["oid"] == oid:
            return {k: x.get(k) for k in ("release_at", "deadline", "first_heard_at",
                                          "first_received_at", "latency_s", "delivered",
                                          "heard_on_time", "received_on_time")}
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=int, default=900)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=os.path.join("results", "control_deadline_witness.json"))
    args = ap.parse_args()
    CTL["delay_s"] = args.delay

    # 第一遍：early，取 T0
    CTL.update(mode="early", t0=None)
    early = run(args.seed)
    t0 = CTL["t0"]

    # 第二遍：late（用 early 的 T0）
    CTL.update(mode="late", t0=t0)
    late = run(args.seed)

    # 第三遍：quiet
    CTL.update(mode="quiet", t0=None)
    quiet = run(args.seed)

    print(f"seed {args.seed}，首次下发时刻 T0 = {t0} s，推迟量 D = {args.delay} s\n")
    for name, d in (("early", early), ("late", late), ("quiet", quiet)):
        sv = d["result"]["routine"]
        print(f"  {name:6s} 服务 {sv['delivered']}/{sv['n']} = {sv['delivered']/sv['n']:.4f}"
              f"  上行 {d['comm']['airtime_uplink_h']*3600:.1f} s"
              f"  下行尝试 {d['comm']['downlink_attempts']}"
              f"  备份包 {d['backup']['backup_packets']}  按期 {d['backup']['backup_on']}"
              f"  过期 {d['backup']['backup_late']}")

    rescued = sorted(early["delivered"] - late["delivered"])
    displaced = sorted(late["delivered"] - early["delivered"])
    print(f"\n见证 A（下发时机）：救回 {len(rescued)} 条，反向位移 {len(displaced)} 条")
    for oid in rescued[:3]:
        print(f"  救回 {oid}")
        print(f"    early: {timeline(early['rows'], oid)}")
        print(f"    late : {timeline(late['rows'], oid)}")

    se, sq = early["result"]["routine"]["delivered"], quiet["result"]["routine"]["delivered"]
    print(f"\n见证 B（节省）：quiet 相对 early 服务 {sq} 对 {se}（{sq - se:+d}）")
    for k in ("airtime_uplink_h", "airtime_downlink_h"):
        print(f"    {k}: {early['comm'][k]*3600:.1f} → {quiet['comm'][k]*3600:.1f} s")
    print(f"    downlink_attempts: {early['comm']['downlink_attempts']} → "
          f"{quiet['comm']['downlink_attempts']}")

    out = {"script": "code/analysis/control_deadline_witness.py", "seed": args.seed,
           "delay_s": args.delay, "t0_first_issue_s": t0,
           "arms": {n: {"svc": d["result"]["routine"]["delivered"],
                        "n": d["result"]["routine"]["n"],
                        "comm": d["comm"], "backup": d["backup"]}
                    for n, d in (("early", early), ("late", late), ("quiet", quiet))},
           "witness_a": {"rescued": len(rescued), "displaced": len(displaced),
                         "rescued_oids": rescued[:20],
                         "examples": [{"oid": o, "early": timeline(early["rows"], o),
                                       "late": timeline(late["rows"], o)} for o in rescued[:5]],
                         "apply_changes_early": early["apply"]},
           "witness_b": {"svc_delta": sq - se}}
    path = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("\nsaved", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
