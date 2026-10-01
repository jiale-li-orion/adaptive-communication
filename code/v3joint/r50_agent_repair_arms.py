# -*- coding: utf-8 -*-
"""r50 — V1 的匹配提议离线干预对照：同一份模型提议，三种执行接口，按物理结果计分。

STATUS (2026-09-21): HISTORICAL CAUSAL-ISOLATION HARNESS / DO NOT EXPAND.
corrected probe 未通过进入门槛，V1 当前暂停。本脚本只保留“同一 proposal 下接口改写造成什么
物理后果”的离线工具价值；不得把 replay 结果当闭环 Agent 结果，也不得继续调用模型扩展该候选。

口径来源：`paper/AGENT_RESEARCH.md` §4；**不是** §6 第二步的闭环 Agent 验证。

这个实验是什么、不是什么
------------------------
**是**：匹配提议的离线干预（action-filter causal isolation）。模型提议只收集一次并落盘，三臂在
**同一份提议、同一 seed、同一物理实例、同一本地保护**上重放，差别只有接口层。它回答的是
"给定完全相同的模型提议，接口层改写这一刀造成什么物理后果"。

**不是**：闭环 Agent 对照。`ReplayDecider` 自己注明只在"同 policy 触发序列"下有效；接口层改变
采样/上报周期之后，telemetry、pending、history、`any_heard` 乃至后续 decision trigger 都会分叉，
分叉之后继续消费原始轨迹的第 k 个提议，那个提议已经是在**另一个观测/历史**下生成的。
`paper/AGENT_RESEARCH.md` §6 明确禁止把这种回放当成新的闭环 Agent 结果。要做闭环，每个臂必须
各自看到自己的观测与历史、各自调用同模型同提示同预算，那是另开的一个小实验。

三臂与消融
----------
  `agent`        裸：模型提议原样执行（逐位复现原 run）
  `agent_env`    再加普通状态/安全过滤：`envelope.enforce_feasibility`（unknown config
                 fail-closed、夜间/dusk 门；ACCESS partial 只 advisory）——普通 baseline
  `agent_repair` 再加 V1：`PlanRepairDecider`

**组合顺序是硬的：安全门在最外层**，即 `EnvelopeDecider(PlanRepairDecider(inner))`。反过来会把
夜间/dusk 被门降成稀疏的档位由 V1 重新打开，等于绕过安全层；`gate_not_reopened_regression()`
在每次运行前核对这条不变量，不通过就直接退出。

消融 `repair_noRa` / `repair_noRb` 分别关掉 V1 的两条规则；`ctrl_dayfeed` / `ctrl_sustain` 是强
确定性控制器的单列性能参照（不调 API）。计分用物理结果；**有益动作误拒**由 `agent_env` 与
`agent_repair` 的配对差读出。可靠链路（`outage_hours=0`）同场作负对照。

Run:
  python3 code/v3joint/r50_agent_repair_arms.py --seeds 0 1 2 [--neg] [--replay-only]
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import statistics as st
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
for _d in ("v3joint", "instance", "physics", "runtime", "experiments", "analysis", "monitoring"):
    _p = os.path.join(ROOT, "code", _d)
    if _p not in sys.path:
        sys.path.insert(0, _p)

from joint_run import run_joint
from agent_mission import AgentMissionPolicy, LLMDecider, ReplayDecider, ScriptedDecider
from envelope import EnvelopeDecider
from agent_plan_repair import PlanRepairDecider

H = lambda h: h * 3600
UP = [(0, 600, "blue"), (6 * H(1), 300, "yellow")]
BASE = dict(task_hours=48, tail_hours=1, arm="local", groups=2, sample_interval_s=600,
            report_period_s=600, routine_period_s=600, harvest_mode="solar",
            harvest_peak_wh_per_hour=0.03, initial_soc=1.0, outage_start_h=4,
            enable_backup=True, backup_rate_s=1200, backup_bytes=78, backup_chooser="maxcov",
            # 所有竞争臂共享成熟普通执行保护；Candidate A 不靠迟到旧命令覆盖/半代配置制造收益。
            # atomic_generation 已支持 payload.fields，因此单字段命令也能作为完整一代独立生效。
            send_contract_fields=True, atomic_generation=True)
TRACEDIR = os.path.join(ROOT, "results", "agent_traces")
MODEL = "deepseek-flash"
PAIR_ARMS = ("agent", "agent_env", "agent_repair")


def _trigger_sequence(trace: str) -> list[tuple[int, str | None]]:
    rows = [json.loads(x) for x in open(trace, encoding="utf-8") if x.strip()]
    return [(int(r.get("t_s", -1)), r.get("trigger")) for r in rows]


def _trigger_match(source: list[tuple[int, str | None]],
                   replay_rows: list[dict]) -> tuple[bool, dict | None]:
    got = [(int(r.get("t_s", -1)), r.get("trigger")) for r in replay_rows]
    n = min(len(source), len(got))
    for i in range(n):
        if source[i] != got[i]:
            return False, {"index": i, "source": list(source[i]), "replay": list(got[i])}
    if len(source) != len(got):
        return False, {"index": n,
                       "source": (list(source[n]) if n < len(source) else None),
                       "replay": (list(got[n]) if n < len(got) else None),
                       "source_len": len(source), "replay_len": len(got)}
    return True, None


def _phys(r) -> dict:
    rr = r["routine"]
    sv = r["survival"]
    comm = r.get("communication", {})
    bk = r.get("backup", {})
    cc = r.get("command_counters", {})
    return {"svc": round(rr["delivered"] / rr["n"], 4), "delivered": rr["delivered"], "n": rr["n"],
            "missing_collection": rr.get("missing_collection"),
            "missing_delivery": rr.get("missing_delivery"),
            "dead": len(sv.get("dead", [])), "mean_final_soc": sv.get("mean_final_soc"),
            "min_final_soc": sv.get("min_final_soc"),
            "airtime_uplink_s": round(comm.get("airtime_uplink_h", 0.0) * 3600, 1),
            "airtime_downlink_s": round(comm.get("airtime_downlink_h", 0.0) * 3600, 2),
            "uplinks": comm.get("uplinks"), "uplinks_heard": comm.get("uplinks_heard"),
            "backup_packets": bk.get("backup_packets"), "backup_bytes_sent": bk.get("backup_bytes_sent"),
            "commands_sent": cc.get("commands_sent"), "commands_delivered": cc.get("commands_delivered"),
            "commands_refused": cc.get("commands_refused")}


def collect(seed: int, tag: str, outage_hours: int) -> str:
    """在线收集一份模型提议并落盘（只做一次，供三臂共用）。"""
    os.makedirs(TRACEDIR, exist_ok=True)
    trace = os.path.join(TRACEDIR, f"r50_{tag}_S_seed{seed}_{int(time.time())}.jsonl")
    dec = LLMDecider(model=MODEL, structured_state=True, tag="r50-S", verbose=False)
    # `task_end_s` 是公开任务定义（手稿的任务时长），不是未来环境真值。GPT §11.1 要求新
    # collect/replay 显式传它，否则 binding 会在 48 h 之后的 tail observation 里继续虚构
    # 已经不存在的 routine obligations。
    pol = AgentMissionPolicy(UP, dec, decision_grid_s=1800, trace_path=trace, tag="S",
                             capacity_wh=0.05, sample_wh=4.7e-4,
                             task_end_s=BASE["task_hours"] * 3600,
                             minimal_field_commands=True,
                             use_physical_inflight=False,
                             target_scoped_dwell=True)
    kw = dict(BASE)
    kw.update(seed=seed, outage_hours=outage_hours)
    r, _, _ = run_joint(**kw, mission_schedule=UP, mission_policy_obj=pol)
    row = _phys(r)
    row.update(tag=tag, seed=seed, outage_hours=outage_hours, trace=trace,
               decisions=len(pol.decision_log), llm_calls=getattr(dec, "calls", None),
               tokens=getattr(dec, "total_tokens", None))
    with open(trace.replace(".jsonl", ".summary.json"), "w", encoding="utf-8") as f:
        json.dump(row, f, ensure_ascii=False, indent=2)
    print(f"[collect] {tag} seed{seed}: svc={row['svc']} delivered={row['delivered']}"
          f" dead={row['dead']} calls={row['llm_calls']} tok={row['tokens']}", flush=True)
    return trace


def _make_decider(arm: str, trace: str):
    """组合顺序：**安全门永远在最外层**。V1 只做局部修复，不得重新授权被门拒绝的字段。"""
    base = ReplayDecider(trace)
    if arm == "agent":
        return base
    if arm == "agent_env":
        return EnvelopeDecider(base, tag="r50-env", mode="evidence")
    if arm == "agent_repair":
        return EnvelopeDecider(PlanRepairDecider(base, tag="r50-repair"), tag="r50-env",
                               mode="evidence")
    if arm == "repair_noRa":
        return EnvelopeDecider(PlanRepairDecider(base, tag="r50-noRa", enable_return_gap=False),
                               tag="r50-env", mode="evidence")
    if arm == "repair_noRb":
        return EnvelopeDecider(PlanRepairDecider(base, tag="r50-noRb", enable_over_hold=False),
                               tag="r50-env", mode="evidence")
    raise ValueError(arm)


def replay(arm: str, trace: str, seed: int, outage_hours: int) -> dict:
    dec = _make_decider(arm, trace)
    pol = AgentMissionPolicy(UP, dec, decision_grid_s=1800, trace_path=None, tag=arm,
                             capacity_wh=0.05, sample_wh=4.7e-4,
                             task_end_s=BASE["task_hours"] * 3600,
                             minimal_field_commands=True,
                             use_physical_inflight=False,
                             target_scoped_dwell=True)
    kw = dict(BASE)
    kw.update(seed=seed, outage_hours=outage_hours)
    r, _, _ = run_joint(**kw, mission_schedule=UP, mission_policy_obj=pol)
    out = _phys(r)
    out["arm"] = arm
    seq_ok, first_div = _trigger_match(_trigger_sequence(trace), pol.decision_log)
    out["trigger_sequence_match"] = seq_ok
    out["trigger_sequence_first_divergence"] = first_div
    env = getattr(dec, "envelope_log", None)
    if env is None and hasattr(dec, "inner"):
        env = getattr(dec.inner, "envelope_log", None)
    out["env_corrections"] = sum(len(x.get("corrections") or []) for x in (env or []))
    rp = getattr(dec, "decisions", None)
    if rp is None and hasattr(dec, "inner"):
        rp = getattr(dec.inner, "decisions", None)
    rules = collections.Counter()
    for d in (rp or []):
        for e in d.get("log", []):
            rules[e["rule"]] += 1
    out["repair_rules"] = dict(rules)
    out["repair_touched_decisions"] = sum(1 for d in (rp or []) if d.get("n_repaired"))
    return out


def control(mode: str, seed: int, outage_hours: int) -> dict:
    dec = ScriptedDecider(mode)
    pol = AgentMissionPolicy(UP, dec, decision_grid_s=1800, trace_path=None, tag=f"ctrl-{mode}",
                             capacity_wh=0.05, sample_wh=4.7e-4,
                             task_end_s=BASE["task_hours"] * 3600,
                             minimal_field_commands=True,
                             use_physical_inflight=False,
                             target_scoped_dwell=True)
    kw = dict(BASE)
    kw.update(seed=seed, outage_hours=outage_hours)
    r, _, _ = run_joint(**kw, mission_schedule=UP, mission_policy_obj=pol)
    out = _phys(r)
    out.update(arm=f"ctrl_{mode}", kind="strong deterministic reference")
    return out


def ci95(xs):
    n = len(xs)
    m = st.mean(xs)
    if n < 2:
        return m, m, m
    h = 1.96 * st.stdev(xs) / (n ** 0.5)
    return m, m - h, m + h


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="*", default=[0, 1, 2])
    ap.add_argument("--neg", action="store_true", help="同场跑可靠链路负对照（outage_hours=0）")
    ap.add_argument("--replay-only", action="store_true",
                    help="不调 API，复用既有 r50 轨迹")
    ap.add_argument("--out", default=os.path.join("results", "agent_repair_arms.json"))
    args = ap.parse_args()

    # 安全门不被 V1 重开：不变量不通过就直接退出，不产出任何读数。
    from agent_plan_repair import gate_not_reopened_regression
    reg = gate_not_reopened_regression()
    out_gate = {"invariant": reg["invariant"], "violations": reg["violations"],
                "cases": reg["cases"]}
    if reg["violations"]:
        print(f"FAIL 安全门被 V1 重开（clock_hod={reg['violations']}）；拒绝运行。")
        return 1

    scenarios = [(f"seed{s}", s, 16, "outage") for s in args.seeds]
    if args.neg:
        scenarios.append((f"seed{args.seeds[0]}", args.seeds[0], 0, "nolinkout"))

    traces, out = {}, {"script": "code/v3joint/r50_agent_repair_arms.py",
                       "contract": ("paper/AGENT_RESEARCH.md §4：匹配提议的离线干预对照"
                                    "（action-filter causal isolation）"),
                       "not_this": ("不是 §6 第二步的闭环 Agent 验证：提议只在同一观测/历史下收集一次，"
                                    "接口层改写后状态会分叉，之后的提议来自另一个历史。闭环要求每臂各自"
                                    "观测、各自调用同模型同提示同预算，另开一个小实验。"),
                       "gate_invariant": ("EnvelopeDecider 在最外层；V1 不得重新授权被安全门拒绝的字段"),
                       "model": MODEL, "prompt": "structured_state=True（与 r38 A0s 同提示）",
                       "matching": ("模型提议每 scenario 只收集一次并落盘，三臂在同一份提议上重放；"
                                    "臂间差别只有接口层，本地保护、expiry、工具、解析预算、seed 与"
                                    "实例参数完全相同。"),
                       "arms": list(PAIR_ARMS) + ["repair_noRa", "repair_noRb"],
                       "controls": ["ctrl_dayfeed", "ctrl_sustain"],
                       "gate_regression": out_gate,
                       "scenarios": {}, "collect": {}, "replay": [], "controls": []}
    for name, seed, oh, tag in scenarios:
        if args.replay_only:
            cand = sorted([f for f in os.listdir(TRACEDIR)
                           if f.startswith(f"r50_{tag}_S_seed{seed}_") and f.endswith(".jsonl")])
            if not cand:
                print(f"[skip] 没有既有 r50 轨迹: {tag} seed{seed}")
                continue
            trace = os.path.join(TRACEDIR, cand[-1])
        else:
            trace = collect(seed, tag, oh)
        traces[name] = (trace, seed, oh, tag)
        out["collect"][name] = {"trace": os.path.basename(trace), "seed": seed,
                                "outage_hours": oh, "tag": tag}
    for name, (trace, seed, oh, tag) in traces.items():
        for arm in out["arms"]:
            row = replay(arm, trace, seed, oh)
            row.update(scenario=name, seed=seed, outage_hours=oh, tag=tag,
                       trace=os.path.basename(trace))
            out["replay"].append(row)
            print(f"[replay] {name:8s} {arm:12s} svc={row['svc']:.4f} 交付 {row['delivered']:5}"
                  f" 缺采 {row['missing_collection']:5} 缺交 {row['missing_delivery']:5}"
                  f" 死亡 {row['dead']:2} 上行 {row['airtime_uplink_s']:7.1f}s"
                  f" 命令 sent/refused {row['commands_sent']}/{row['commands_refused']}"
                  f" 门修正 {row['env_corrections']:3d} V1规则 {row['repair_rules']}"
                  f" trigger_match={row['trigger_sequence_match']}", flush=True)
    for name, (trace, seed, oh, tag) in traces.items():
        for mode in ("dayfeed", "sustain"):
            row = control(mode, seed, oh)
            row.update(scenario=name, seed=seed, outage_hours=oh, tag=tag)
            out["controls"].append(row)
            print(f"[ctrl]   {name:8s} {mode:9s} svc={row['svc']:.4f} 交付 {row['delivered']:5}"
                  f" 缺采 {row['missing_collection']:5} 缺交 {row['missing_delivery']:5}"
                  f" 死亡 {row['dead']:2}", flush=True)

    # 配对汇总：只对同一 scenario 内可配对的臂
    by = collections.defaultdict(dict)
    for row in out["replay"]:
        by[row["scenario"]][row["arm"]] = row
    pair = {}
    for a in ("agent_env", "agent_repair", "repair_noRa", "repair_noRb"):
        d, s = [], []
        for sc, arms in by.items():
            if (a in arms and "agent" in arms
                    and arms[a].get("trigger_sequence_match")
                    and arms["agent"].get("trigger_sequence_match")):
                d.append(arms[a]["delivered"] - arms["agent"]["delivered"])
                s.append(arms[a]["svc"] - arms["agent"]["svc"])
        if d:
            m, lo, hi = ci95(d)
            pair[f"{a}_minus_agent"] = {"delivered_delta": d, "mean": round(m, 2),
                                        "ci95": [round(lo, 2), round(hi, 2)],
                                        "mean_svc_delta": round(st.mean(s), 5)}
    for a in ("agent_repair", "repair_noRa", "repair_noRb"):
        d = []
        for sc, arms in by.items():
            if (a in arms and "agent_env" in arms
                    and arms[a].get("trigger_sequence_match")
                    and arms["agent_env"].get("trigger_sequence_match")):
                d.append(arms[a]["delivered"] - arms["agent_env"]["delivered"])
        if d:
            m, lo, hi = ci95(d)
            pair[f"{a}_minus_agent_env"] = {"delivered_delta": d, "mean": round(m, 2),
                                            "ci95": [round(lo, 2), round(hi, 2)]}
    out["paired"] = pair
    print("\n配对差（交付条数）：")
    for k, v in pair.items():
        print(f"  {k:28s} {v['delivered_delta']}  均值 {v['mean']:+}  CI{v.get('ci95')}")
    path = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("\nsaved", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
