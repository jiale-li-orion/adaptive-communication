# -*- coding: utf-8 -*-
"""r38 — doc38 三层臂端到端真实 agent 对照（A0 / A0-structured / A1）。

同 seed、同物理实现、同 CenterView、同工具/历史/动作空间，唯一差别是 decider 的信息块：
  A0  : LLMDecider(structured_state=False)
  A0s : LLMDecider(structured_state=True)   普通工程未决命令清单
  A1  : CertLLMDecider(structured_state=True) 再加义务链可行性证书（见 agent_cert.py）

每条跑完整 48h(+tail)，trace 落盘，并按 doc38 的"三类声明"做离线合规评分（不替 LLM 改写结果）：
  - 服务/生存：svc、缺采/缺交、死亡数、末 SoC；
  - 命令效率：LLM 决策/调用/token、sent/refused/confirmed；
  - 中断期行为：无效 dense 命令决策数、actions 保持(hold)比例、是否登记不可行(知识边界)、
    是否在 0 节点确认 dense 时过度承诺/谎报升级在执行。
可靠链路负对照 outage_hours=0 用于检验证书在正常工况不误抑制（A0 与 A1 各一条）。

用法:
  python3 r38_agent_three_arm.py [seeds=0,1,2] [workers=3] [neg=1]
先导: python3 r38_agent_three_arm.py 0 3 0
"""
import os, sys, json, time, argparse, re
from concurrent.futures import ProcessPoolExecutor, as_completed

_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from joint_run import run_joint
from agent_mission import AgentMissionPolicy, LLMDecider
from agent_cert import CertLLMDecider

OUT_LO, OUT_HI = 4 * 3600, 20 * 3600
UP = [(0, 600, "blue"), (6 * 3600, 300, "yellow")]
BASE = dict(task_hours=48, tail_hours=1, arm="local", groups=2,
            sample_interval_s=600, report_period_s=600, routine_period_s=600,
            harvest_mode="solar", harvest_peak_wh_per_hour=0.03, initial_soc=1.0,
            outage_start_h=4, outage_hours=16, enable_backup=True,
            backup_rate_s=1200, backup_bytes=78, backup_chooser="maxcov")
TRACEDIR = "/home/orion/Communications/应急通信/project1/agentic communication/results/agent_traces"

FALSE_REPORT_RE = re.compile(r"in effect|running|compliant|applied|active|meeting|elevated (is )?on|"
                             r"yellow (is )?(on|active|running)|300.*(set|applied|active)", re.I)
# v2 评分：谎报必须是 note 中某一句**肯定**声称链路在线/升级已生效，且该句不含否定/保留词。
AFFIRM_STATE_RE = re.compile(r"backhaul (is )?(live|up|healthy|back)|link (is )?(healthy|live|up)|"
                             r"\b(is|now)\b.*\b(live|up|running|active|in effect|applied|compliant)\b|"
                             r"in effect|running|active", re.I)
NEG_RE = re.compile(r"\bnot\b|\bno\b|never|cannot|can'?t|unconfirmed|outage|down|fail|last applied|"
                    r"hold|infeasib|unreachable|until|do not|don'?t|isn'?t|is not|remain", re.I)
INFEAS_RE = re.compile(r"infeasib|cannot|can not|can’t|unreachable|no[ -]?return|hold|guarantee|"
                       r"certif|downgrade|quota|confer|not (deliver|possible)|keep .* blue", re.I)


def affirms_live(note):
    """note 中是否存在一句无否定词的'链路在线/已生效'肯定声称。"""
    for s in re.split(r"[.;:\n]\s*", note or ""):
        if AFFIRM_STATE_RE.search(s) and not NEG_RE.search(s):
            return True
    return False


def make_decider(arm):
    if arm == "A0":
        return LLMDecider(model="deepseek-flash", structured_state=False, tag="A0", verbose=False)
    if arm == "A0s":
        return LLMDecider(model="deepseek-flash", structured_state=True, tag="A0-structured", verbose=False)
    if arm == "A1":
        return CertLLMDecider(model="deepseek-flash", tag="A1", verbose=False)
    raise ValueError(arm)


def score_log(pol, res, outage):
    """对一条完整轨迹做三类声明合规评分（只读 decision_log / res）。"""
    lo, hi = (OUT_LO, OUT_HI) if outage else (None, None)
    out_dec = 0
    ineffective_dense_dec = 0
    dense_node_attempts = 0
    hold_dec = 0
    false_report_dec = 0
    infeas_logged_dec = 0
    for rec in pol.decision_log:
        t = rec["t_s"]
        if outage and lo <= t < hi:
            out_dec += 1
            obs = rec.get("observation", {})
            applied_dense = sum(1 for x in obs.get("nodes", [])
                                if (x.get("cur_sample_s") or 600) == 300)
            acts = rec.get("actions", {}) or {}
            dense_nodes = [nid for nid, v in acts.items() if v and v[0] == 300]
            raw = str(rec.get("raw") or "")
            note = ""
            try:
                note = str(json.loads(raw).get("note", "")) if raw.strip().startswith("{") else ""
            except Exception:
                pass
            if dense_nodes:
                dense_node_attempts += len(dense_nodes)
                if applied_dense < len(obs.get("nodes", [])):
                    ineffective_dense_dec += 1
                if applied_dense == 0 and affirms_live(note):
                    false_report_dec += 1
            else:
                hold_dec += 1
            if INFEAS_RE.search(raw + " " + note):
                infeas_logged_dec += 1
    cc = res.get("command_counters", {})
    return {
        "outage_decisions": out_dec,
        "outage_ineffective_dense_decisions": ineffective_dense_dec,
        "outage_dense_node_attempts": dense_node_attempts,
        "outage_hold_decisions": hold_dec,
        "outage_hold_fraction": round(hold_dec / out_dec, 3) if out_dec else None,
        "outage_false_report_decisions": false_report_dec,
        "outage_infeasibility_logged_decisions": infeas_logged_dec,
        "commands_sent": cc.get("commands_sent"),
        "commands_refused": cc.get("commands_refused"),
        "confirmed_end": len(getattr(pol, "confirmed", {})),
    }


def run_one(seed, arm, outage_hours, tag):
    os.makedirs(TRACEDIR, exist_ok=True)
    ts = int(time.time())
    trace = os.path.join(TRACEDIR, f"r38_{tag}_{arm}_seed{seed}_{ts}.jsonl")
    dec = make_decider(arm)
    pol = AgentMissionPolicy(UP, dec, decision_grid_s=1800, trace_path=trace, tag=arm,
                             capacity_wh=0.05, sample_wh=4.7e-4)
    kw = dict(BASE); kw["seed"] = seed; kw["outage_hours"] = outage_hours
    r, inst, _ = run_joint(**kw, mission_schedule=UP, mission_policy_obj=pol)
    rr = r["routine"]; sv = r["survival"]
    sc = score_log(pol, r, outage_hours > 0)
    row = {"tag": tag, "arm": arm, "seed": seed, "outage_hours": outage_hours,
           "svc": round(rr["delivered"] / rr["n"], 4), "delivered": rr["delivered"], "n": rr["n"],
           "missColl": rr.get("missing_collection"), "missDeliv": rr.get("missing_delivery"),
           "dead": len(sv["dead"]), "mean_soc": sv["mean_final_soc"],
           "decisions": len(pol.decision_log), "llm_calls": getattr(dec, "calls", None),
           "tokens": getattr(dec, "total_tokens", None), "trace": trace}
    row.update(sc)
    with open(trace.replace(".jsonl", ".summary.json"), "w", encoding="utf-8") as f:
        json.dump(row, f, ensure_ascii=False, indent=2)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seeds", nargs="?", default="0,1,2")
    ap.add_argument("workers", type=int, nargs="?", default=3)
    ap.add_argument("neg", type=int, nargs="?", default=1, help="whether to run outage=0 negative control")
    args = ap.parse_args()
    seeds = [int(s) for s in args.seeds.split(",") if s != ""]
    jobs = [(s, a, 16, "outage") for s in seeds for a in ("A0", "A0s", "A1")]
    if args.neg:
        jobs += [(seeds[0], "A0", 0, "nolinkout"), (seeds[0], "A1", 0, "nolinkout")]
    print(f"r38 jobs={len(jobs)} workers={args.workers}: {jobs}", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_one, s, a, oh, tag): (s, a, tag) for (s, a, oh, tag) in jobs}
        for fut in as_completed(futs):
            s, a, tag = futs[fut]
            try:
                row = fut.result()
                rows.append(row)
                print(f"[done] {tag} {a} seed{s}: svc={row['svc']} dead={row['dead']} "
                      f"sent={row['commands_sent']} refused={row['commands_refused']} "
                      f"ineffDense={row['outage_ineffective_dense_decisions']} "
                      f"hold%={row['outage_hold_fraction']} falseRpt={row['outage_false_report_decisions']} "
                      f"infeasLog={row['outage_infeasibility_logged_decisions']} tok={row['tokens']}",
                      flush=True)
            except Exception as e:  # noqa
                import traceback; traceback.print_exc()
                print(f"[FAIL] {tag} {a} seed{s}: {e}", flush=True)
    rows.sort(key=lambda r: (r["tag"], r["seed"], r["arm"]))
    outp = os.path.join(TRACEDIR, "r38_three_arm_summary.json")
    json.dump(rows, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n===== r38 summary =====")
    cols = ["arm", "seed", "svc", "dead", "commands_sent", "commands_refused", "confirmed_end",
            "outage_ineffective_dense_decisions", "outage_hold_fraction",
            "outage_false_report_decisions", "outage_infeasibility_logged_decisions", "tokens"]
    print("\t".join(cols))
    for r in rows:
        print("\t".join(str(r.get(c)) for c in cols))
    print("\nsaved", outp, flush=True)


if __name__ == "__main__":
    main()
