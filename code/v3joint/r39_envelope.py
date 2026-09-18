#!/usr/bin/env python3
"""r39_envelope.py — 确定性可行性执行层对照（无 LLM，不耗 API）。

在与 r38 完全相同的 center 放置 / stamp_pair 命令机制 / 物理与扰动下，比较：
  comply        通用 planner 的朴素行为：盲从授权（elevated 即全程 dense），无保护
  dayfeed-c     center 下发的昼夜前馈强普通规则（受回传/Class A 约束，非本地自治）
  env(comply)   朴素 planner + 可行性 envelope（夜间能量硬门 + 控制面确认门）
  env(dayfeed)  昼夜规则 + envelope（额外的回传感知抑制）
  local-dayfeed 无 center policy 的本地自治 dayfeed（部署基线，命令不依赖回传）
指标：svc、永久死亡数、平均末电、缺采/缺交、命令计数。seed 0/1/2。
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from joint_run import run_joint
from agent_mission import AgentMissionPolicy, ScriptedDecider
from envelope import EnvelopeDecider
import r38_agent_three_arm as R

OUT = os.path.join(R.TRACEDIR, "r39_envelope_summary.json")


def run_policy(seed, decider, tag, floor=False, dayfeed=False):
    pol = AgentMissionPolicy(R.UP, decider, decision_grid_s=1800, trace_path=None,
                             tag=tag, capacity_wh=0.05, sample_wh=4.7e-4)
    kw = dict(R.BASE); kw["seed"] = seed
    r, inst, _ = run_joint(**kw, mission_schedule=R.UP, mission_policy_obj=pol,
                           local_floor=floor, local_dayfeed=dayfeed)
    rr = r["routine"]; sv = r["survival"]; cc = r.get("command_counters", {})
    return {"arm": tag, "seed": seed,
            "svc": round(rr["delivered"] / rr["n"], 4), "delivered": rr["delivered"], "n": rr["n"],
            "missColl": rr.get("missing_collection"), "missDeliv": rr.get("missing_delivery"),
            "dead": len(sv["dead"]), "mean_soc": round(sv["mean_final_soc"], 4),
            "sent": cc.get("commands_sent"), "refused": cc.get("commands_refused")}


def run_local(seed):
    kw = dict(R.BASE); kw["seed"] = seed
    r, inst, _ = run_joint(**kw, mission_schedule=R.UP)
    rr = r["routine"]; sv = r["survival"]
    return {"arm": "local-dayfeed", "seed": seed,
            "svc": round(rr["delivered"] / rr["n"], 4), "delivered": rr["delivered"], "n": rr["n"],
            "missColl": rr.get("missing_collection"), "missDeliv": rr.get("missing_delivery"),
            "dead": len(sv["dead"]), "mean_soc": round(sv["mean_final_soc"], 4),
            "sent": None, "refused": None}


def main():
    seeds = [int(x) for x in (sys.argv[1].split(",") if len(sys.argv) > 1 else "0,1,2".split(","))]
    rows = []
    for s in seeds:
        rows.append(run_local(s))
        arms = [
            ("comply", ScriptedDecider("comply"), False, False),
            ("dayfeed-c", ScriptedDecider("dayfeed"), False, False),
            ("env-comply", EnvelopeDecider(ScriptedDecider("comply"), tag="env-comply"), False, False),
            ("env-dayfeed", EnvelopeDecider(ScriptedDecider("dayfeed"), tag="env-dayfeed"), False, False),
            # 推荐架构：中心 planner/envelope + 节点本地能量自治底座
            ("comply+floor", ScriptedDecider("comply"), True, False),
            ("dayfeed-c+floor", ScriptedDecider("dayfeed"), True, False),
            ("env-comply+floor", EnvelopeDecider(ScriptedDecider("comply"), tag="env-comply"), True, False),
            # 最强本地自治反方：任务表预装、节点本地昼夜执行、零有效中心下行
            ("local-full", ScriptedDecider("comply"), True, True),
        ]
        for name, dec, floor, dayfeed in arms:
            rows.append(run_policy(s, dec, name, floor=floor, dayfeed=dayfeed))
    hdr = ["arm", "seed", "svc", "dead", "mean_soc", "missColl", "missDeliv", "sent", "refused"]
    print("\t".join(hdr))
    for r in rows:
        print("\t".join(str(r.get(k)) for k in hdr))
    # 汇总均值
    import statistics
    print("\n=== means over seeds ===")
    print("arm\tsvc_mean\tdead_total\tsvc_min..max")
    for arm in ["local-dayfeed", "comply", "dayfeed-c", "env-comply", "env-dayfeed",
                "comply+floor", "dayfeed-c+floor", "env-comply+floor", "local-full"]:
        rs = [r for r in rows if r["arm"] == arm]
        sv = [r["svc"] for r in rs]
        print(f"{arm}\t{statistics.mean(sv):.4f}\t{sum(r['dead'] for r in rs)}\t"
              f"{min(sv):.3f}..{max(sv):.3f}")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print("\nsaved", OUT)


if __name__ == "__main__":
    main()
