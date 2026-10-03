# -*- coding: utf-8 -*-
"""control_deadline_witness.py — 控制的截止：命令下发时机的见证与普通相位规则对手。

问题（审阅者限定）：固定采样、普通 expiry、maxcov、本地能量规则与**有限主备资源**不变时，
通过既有 `set_report_period` 的**合法下发时机**，能否跨过一条本来错过的可用回传机会，
或在服务不减时减少真实通信成本？并回答它是否被普通相位规则覆盖。

四臂（同种子、同参数，只有下发时机与目标来源不同）
--------------------------------------------------
`early`        原样 `odp`（网关侧 `ObligationDeliveryPolicy`）
`late`         把首次下发整体推迟 D 秒（相同前缀分歧；推迟窗口内不推进策略内部状态）
`quiet`        从不下发
`phase_table`  **普通相位规则对手**：换档时刻与目标档都取自公开任务表（6 h → 300/300），
               在每个决策拍对"上报档尚未等于目标"的节点下发，直到节点确认。它用同一条
               Class A 接口与同一备份资源，不读任何本地反馈，也不独占备份日历。

见证与判决
----------
见证 A（救回）：`early` 交付而 `late` 未交付的义务，且反向位移数不超过救回数。
见证 B（节省）：`quiet` 相对 `early` 服务不降而真实上行/空口/下行成本下降。
晋级：两见证至少一类成立**且**胜过相应普通对照（此处即 `phase_table`）。

必须计入的时序限制：快报命令不能加速承载其自身接收窗口的那次上行（LoRaWAN 1.0.1 §3.3），
因此见证只认"生效之后"的机会，不把已听到的那份样本算作救回。

接线警告：`joint_run` 中 `elif mission_mode is not None` 排在 `elif arm == "odp"` **之前**，
传任何 `mission_mode` 都会让网关侧 `ObligationDeliveryPolicy` 分支不可达（实测得到
`MissionChangePolicy` 且零下发）。本诊断因此传 `mission_mode=None`。

跑法与产物边界
--------------
    python3 code/analysis/control_deadline_witness.py --seeds 0 1 2   # 写受控在册件
    python3 code/analysis/control_deadline_witness.py --seed 102      # 探索：只落临时文件

**只有多种子聚合写 `results/control_deadline_witness.json`。** 单种子运行属于探索，缺省落到系统
临时目录并把路径打印出来。这条规则不是洁癖：用 `--seed` 逐种子循环跑过一次，就把三种子聚合件
覆盖成了最后一个种子的单跑结果（`seed: 104`，无 `per_seed`/`summary`），而登记行、`CLAIMS` 与
`results/reference/` 冻结件仍在引用聚合读数，活件与冻结件因此分叉且无人发现。
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))

#: 受控在册件。只有多种子聚合可以写它，见文件头"跑法与产物边界"。
REGISTERED_OUT = os.path.join("results", "control_deadline_witness.json")


def out_path(args, seed: int | None = None) -> str:
    """输出路径：`--out` 显式给出时照用；否则多种子→受控在册件、单种子→系统临时文件。"""
    if args.out:
        return args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    if seed is None:
        return os.path.join(ROOT, REGISTERED_OUT)
    return os.path.join(tempfile.gettempdir(), f"control_deadline_witness_seed{seed}.json")
for _d in ("v3joint", "instance", "physics", "runtime", "experiments", "analysis", "monitoring"):
    _p = os.path.join(ROOT, "code", _d)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import network as net
import obligation_policy as _op
from obligation_policy import OP_SET_REPORT_PERIOD, OP_SET_SAMPLING_INTERVAL
from joint_run import run_joint

H = lambda h: h * 3600
UP_ONLY = [(0, 600, "blue"), (6 * H(1), 300, "yellow")]
BASE = dict(task_hours=48, tail_hours=1, arm="odp", groups=2,
            sample_interval_s=600, report_period_s=600, routine_period_s=600,
            harvest_mode="solar", harvest_peak_wh_per_hour=0.03, capacity_wh=0.05,
            initial_soc=1.0, outage_start_h=4, outage_hours=16, enable_backup=True,
            backup_rate_s=1200, backup_bytes=78, backup_chooser="maxcov",
            cache_service="generic_expiry", mission_schedule=UP_ONLY,
            mission_mode=None, collect_rows=True)

#: 普通相位规则对手的边：换档时刻与目标档都取自**公开任务表**，末边是日落回退
#: （夜间回退是成熟原语，论文自己把它算作普通机制；不给对手这条会对它不公平）。
#: **只改上报周期**，与 ODP 实际动作面一致（实测 ODP 的 n00 生效序列是 [(0,600)]，即它从未改采样档；
#: 若让相位表同时把采样改成 300，节点整夜密采会耗死、服务从 2697 崩到 1109——那是对手不合格，不是结论）。
TABLE_EDGES = ((6 * H(1), 600, 300), (18 * H(1), 600, 600))
#: 判别臂：把相位表的边整体前移 `LEAD_S`，即"按窗口边沿减去生效前置"下发。
#: 若它与 ODP 打平，则候选被一条普通规则覆盖（把边前移就是这么简单的修法）；若仍差，
#: 说明 ODP 的自适应有内容。前移量取 ODP 自带的 `lead_s` 默认值 900 s。
LEAD_S = 900
TABLE_EDGES_LEAD = tuple((edge - LEAD_S, sa, rp) for edge, sa, rp in TABLE_EDGES)
CTL = {"mode": "early", "t0": None, "delay_s": 900}


def table_target_at(t_s: int, edges=TABLE_EDGES) -> tuple[int, int]:
    target = (600, 600)
    for edge, sample, report in edges:
        if t_s >= edge:
            target = (sample, report)
    return target
APPLY: dict = collections.defaultdict(list)

_ORIG_PLAN = _op.ObligationDeliveryPolicy.plan


def plan(self, view):
    """四臂共用的下发入口。

    `late` 在推迟窗口内**直接返回空**（不调用原 `plan`），因此策略内部的 `_last/_issued`
    不推进，窗口结束后它仍会下发本该下发的命令——这是"晚一点才允许下发"的干净实现。
    """
    mode = CTL["mode"]
    if mode == "quiet":
        return []
    if mode == "late" and CTL["t0"] is not None and view.t_s < CTL["t0"] + CTL["delay_s"]:
        return []
    if mode in ("phase_table", "phase_table_lead"):
        edges = TABLE_EDGES_LEAD if mode == "phase_table_lead" else TABLE_EDGES
        if view.t_s % self.decision_epoch_s != 0 or view.t_s < edges[0][0]:
            return []
        sample, report = table_target_at(view.t_s, edges)
        out = []
        for nid in view.node_ids:
            if nid in view.in_flight:
                continue
            snap = view.reports.get(nid) or {}
            if (snap.get("sample_interval_s") == sample
                    and snap.get("report_period_s") == report):
                continue
            a, b = self.stamp_pair(
                nid,
                {"op": OP_SET_SAMPLING_INTERVAL, "interval_s": sample},
                {"op": OP_SET_REPORT_PERIOD, "period_s": report})
            out.append((nid, a))
            out.append((nid, b))
        return out
    out = _ORIG_PLAN(self, view)
    if out and CTL["t0"] is None:
        CTL["t0"] = view.t_s
    return out


_op.ObligationDeliveryPolicy.plan = plan

#: 生效档位变更必须在**每拍轮询**：命令生效发生在控制面（`_send_command` → 节点应用），
#: 不在 `_apply_local_floor` 内，挂在那个函数上只会得到 None（实测踩过）。
_ORIG_STEP = net.Node.step


def step(self, t_s, truth):
    out = _ORIG_STEP(self, t_s, truth)
    hist = APPLY[self.node_id]
    if not hist or hist[-1][1] != self.sample_interval_s:
        hist.append((t_s, self.sample_interval_s))
    return out


net.Node.step = step


def run(seed: int) -> dict:
    APPLY.clear()
    r, inst, _ = run_joint(seed=seed, **BASE)
    rows = [x for x in r["rows"] if x["kind"] == "routine" and not x.get("censored")]
    return {"result": r, "rows": rows,
            "delivered": {x["oid"] for x in rows if x["delivered"]},
            "dead": len(r["survival"].get("dead", [])),
            "apply": {k: list(v) for k, v in APPLY.items()},
            "comm": {k: r["communication"].get(k) for k in
                     ("airtime_uplink_h", "airtime_downlink_h", "downlink_attempts")},
            "backup": {k: r["backup"].get(k) for k in
                       ("backup_packets", "backup_bytes_sent", "backup_on", "backup_late")}}


def rescue_witness(early: dict, late: dict) -> dict:
    """见证 A 的计数：`early` 交付而 `late` 未交付（救回），以及反向位移。

    单种子路径与多种子聚合共用这一个实现——判决措辞要引用救回/位移，而受控文字只能引用受控产物，
    所以计数必须进聚合件，不能只留在 stdout 里。
    """
    rescued = sorted(early["delivered"] - late["delivered"])
    displaced = sorted(late["delivered"] - early["delivered"])
    return {"rescued": len(rescued), "displaced": len(displaced),
            "rescued_oids": rescued, "displaced_oids": displaced}


def timeline(rows, oid):
    for x in rows:
        if x["oid"] == oid:
            return {k: x.get(k) for k in ("release_at", "deadline", "first_heard_at",
                                          "first_received_at", "latency_s", "delivered",
                                          "heard_on_time", "received_on_time")}
    return None


ARMS_ORDER = ("early", "late", "quiet", "table", "tbl_lead")


def multi_seed(args) -> int:
    """多种子聚合：逐种子跑五臂，报告服务差与成本。判决用于 §3 的 go/stop。"""
    per = {a: [] for a in ARMS_ORDER}
    for seed in args.seeds:
        CTL.update(mode="early", t0=None)
        early = run(seed)
        t0 = CTL["t0"]
        CTL.update(mode="late", t0=t0)
        late = run(seed)
        CTL.update(mode="quiet", t0=None)
        quiet = run(seed)
        CTL.update(mode="phase_table", t0=None)
        table = run(seed)
        CTL.update(mode="phase_table_lead", t0=None)
        lead = run(seed)
        for name, d in (("early", early), ("late", late), ("quiet", quiet),
                        ("table", table), ("tbl_lead", lead)):
            per[name].append({"seed": seed, "svc": d["result"]["routine"]["delivered"],
                              "n": d["result"]["routine"]["n"], "dead": d["dead"],
                              "uplink_s": round(d["comm"]["airtime_uplink_h"] * 3600, 1),
                              "downlink_s": round(d["comm"]["airtime_downlink_h"] * 3600, 1),
                              "attempts": d["comm"]["downlink_attempts"]})
        # **见证计数必须进聚合件**：`late` 的救回/位移是判决措辞要引用的量，而受控文字只能引用
        # 受控产物。只把它留在 stdout 里，登记行就没法引用它——这正是"结论在文里、证据不在件里"
        # 的老毛病。两个计数按种子记，同时给合计。
        wa = rescue_witness(early, late)
        per["early"][-1]["witness_a"] = {"rescued": wa["rescued"], "displaced": wa["displaced"],
                                         "rescued_oids": wa["rescued_oids"][:5]}
        per["early"][-1]["witness_b"] = {"svc_delta_quiet_vs_early":
                                         quiet["result"]["routine"]["delivered"]
                                         - early["result"]["routine"]["delivered"]}
        print(f"seed {seed}: early {early['result']['routine']['delivered']}"
              f"  table {table['result']['routine']['delivered']}"
              f"  tbl_lead {lead['result']['routine']['delivered']}"
              f"  quiet {quiet['result']['routine']['delivered']}"
              f"  late {late['result']['routine']['delivered']}"
              f"  救回 {wa['rescued']} 位移 {wa['displaced']}",
              flush=True)
    diff = [e["svc"] - t["svc"] for e, t in zip(per["early"], per["table"])]
    diff_l = [e["svc"] - l["svc"] for e, l in zip(per["early"], per["tbl_lead"])]
    diff_q = [e["svc"] - q["svc"] for e, q in zip(per["early"], per["quiet"])]
    print(f"\n{len(args.seeds)} 种子（{args.seeds}）：")
    print(f"  early − table    {diff}  均值 {sum(diff)/len(diff):+.1f} 条")
    print(f"  early − tbl_lead {diff_l}  均值 {sum(diff_l)/len(diff_l):+.1f} 条")
    print(f"  early − quiet    {diff_q}  均值 {sum(diff_q)/len(diff_q):+.1f} 条")
    for name in ARMS_ORDER:
        a = per[name]
        print(f"  {name:9s} 服务均值 {sum(x['svc'] for x in a)/len(a):7.1f}"
              f"  上行均值 {sum(x['uplink_s'] for x in a)/len(a):7.1f} s"
              f"  下行尝试均值 {sum(x['attempts'] for x in a)/len(a):7.1f}"
              f"  死亡合计 {sum(x['dead'] for x in a)}")
    out = {"script": "code/analysis/control_deadline_witness.py",
           "contract": "§3 控制时机见证（local_experiments/c5_lease/review/PLAN-AFTER-C10）",
           "seeds": args.seeds, "arms_order": list(ARMS_ORDER), "per_seed": per,
           "summary": {"early_minus_table": diff, "early_minus_tbl_lead": diff_l,
                       "early_minus_quiet": diff_q,
                       "mean_early_minus_table": sum(diff) / len(diff),
                       "mean_early_minus_tbl_lead": sum(diff_l) / len(diff_l),
                       "mean_early_minus_quiet": sum(diff_q) / len(diff_q),
                       "rescued_total": sum(x["witness_a"]["rescued"] for x in per["early"]),
                       "displaced_total": sum(x["witness_a"]["displaced"] for x in per["early"]),
                       "rescued_per_seed": [x["witness_a"]["rescued"] for x in per["early"]],
                       "displaced_per_seed": [x["witness_a"]["displaced"] for x in per["early"]],
                       "witness_b_quiet_delta_per_seed": [x["witness_b"]["svc_delta_quiet_vs_early"]
                                                          for x in per["early"]]}}
    path = out_path(args)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("\nsaved", path)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=int, default=900)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--seeds", type=int, nargs="*", default=None,
                    help="多种子聚合；给出时忽略 --seed")
    ap.add_argument("--out", default=None,
                    help="显式输出路径；缺省时多种子写受控在册件、单种子写系统临时文件")
    args = ap.parse_args()
    CTL["delay_s"] = args.delay

    if args.seeds:
        return multi_seed(args)
    CTL.update(mode="early", t0=None)
    early = run(args.seed)
    t0 = CTL["t0"]
    CTL.update(mode="late", t0=t0)
    late = run(args.seed)
    CTL.update(mode="quiet", t0=None)
    quiet = run(args.seed)
    CTL.update(mode="phase_table", t0=None)
    table = run(args.seed)
    CTL.update(mode="phase_table_lead", t0=None)
    table_lead = run(args.seed)

    arms = (("early", early), ("late", late), ("quiet", quiet), ("table", table),
            ("tbl_lead", table_lead))
    print(f"seed {args.seed}，首次下发时刻 T0 = {t0} s，推迟量 D = {args.delay} s\n")
    for name, d in arms:
        svc = d["result"]["routine"]
        print(f"  {name:6s} 服务 {svc['delivered']}/{svc['n']} = {svc['delivered']/svc['n']:.4f}"
              f"  上行 {d['comm']['airtime_uplink_h']*3600:7.1f} s"
              f"  下行 {d['comm']['airtime_downlink_h']*3600:6.1f} s"
              f"  下行尝试 {d['comm']['downlink_attempts']:5d}"
              f"  备份包 {d['backup']['backup_packets']}"
              f"  死亡 {d['dead']}")

    _wa = rescue_witness(early, late)
    rescued, displaced = _wa["rescued_oids"], _wa["displaced_oids"]
    print(f"\n见证 A（下发时机）：救回 {len(rescued)} 条，反向位移 {len(displaced)} 条")
    for oid in rescued[:3]:
        print(f"  救回 {oid}")
        print(f"    early: {timeline(early['rows'], oid)}")
        print(f"    late : {timeline(late['rows'], oid)}")

    se = early["result"]["routine"]["delivered"]
    sq = quiet["result"]["routine"]["delivered"]
    st = table["result"]["routine"]["delivered"]
    sl = table_lead["result"]["routine"]["delivered"]
    print(f"\n见证 B（节省）：quiet 相对 early 服务 {sq} 对 {se}（{sq - se:+d}）")
    for k in ("airtime_uplink_h", "airtime_downlink_h"):
        print(f"    {k}: {early['comm'][k]*3600:.1f} → {quiet['comm'][k]*3600:.1f} s")
    print(f"    downlink_attempts: {early['comm']['downlink_attempts']} → "
          f"{quiet['comm']['downlink_attempts']}")

    print(f"\n普通相位规则对手（边 {TABLE_EDGES}）：table 服务 {st} 对 early {se}（{st - se:+d}）")
    print(f"边前移 {LEAD_S} s 的相位表（边 {TABLE_EDGES_LEAD}）：tbl_lead 服务 {sl} 对 early {se}"
          f"（{sl - se:+d}）；上行 {table_lead['comm']['airtime_uplink_h']*3600:.1f} s；"
          f"下发尝试 {table_lead['comm']['downlink_attempts']}")
    print(f"    上行 {early['comm']['airtime_uplink_h']*3600:.1f} → "
          f"{table['comm']['airtime_uplink_h']*3600:.1f} s；"
          f"下行尝试 {early['comm']['downlink_attempts']} → {table['comm']['downlink_attempts']}")
    print(f"    首次生效档位变更 early {early['apply'].get('n00')}")
    print(f"    首次生效档位变更 table {table['apply'].get('n00')}")

    out = {"script": "code/analysis/control_deadline_witness.py",
           "contract": "§3 控制时机见证（local_experiments/c5_lease/review/PLAN-AFTER-C10）",
           "seed": args.seed, "delay_s": args.delay, "t0_first_issue_s": t0,
           "arms": {n: {"svc": d["result"]["routine"]["delivered"],
                        "n": d["result"]["routine"]["n"],
                        "comm": d["comm"], "backup": d["backup"], "dead": d["dead"],
                        "apply_first_n00": (d["apply"].get("n00") or [None])[0]}
                    for n, d in arms},
           "witness_a": {"rescued": len(rescued), "displaced": len(displaced),
                         "rescued_oids": rescued[:20],
                         "examples": [{"oid": o, "early": timeline(early["rows"], o),
                                       "late": timeline(late["rows"], o)} for o in rescued[:5]]},
           "witness_b": {"svc_delta_quiet_vs_early": sq - se},
           "ordinary_adversary": {"phase_table_edges": [list(e) for e in TABLE_EDGES],
                                  "svc": st, "svc_delta_vs_early": st - se,
                                  "phase_table_lead_edges": [list(e) for e in TABLE_EDGES_LEAD],
                                  "svc_lead": sl, "svc_lead_delta_vs_early": sl - se}}
    path = out_path(args, seed=args.seed)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("\nsaved", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
