# -*- coding: utf-8 -*-
"""r25 顺序3 agent 线束。
phase0: ScriptedDecider(dayfeed) 走 AgentMissionPolicy 全链路, 应对齐 r24 dayfeed(.4001, 0 死亡),
        并见证命令真实下发/在 Class A 生效/决策与命令计数, 证明 agent 接线正确(不花 API)。
phase1(llm): deepseek-flash A0 单条轨迹, trace 落盘。用法: python3 r25_agent_harness.py llm [seed]
"""
import os, sys, json
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from joint_run import run_joint
from agent_mission import AgentMissionPolicy, ScriptedDecider, LLMDecider, ReplayDecider

BASE = dict(seed=0, task_hours=48, tail_hours=1, arm="local", groups=2,
    sample_interval_s=600, report_period_s=600, routine_period_s=600,
    harvest_mode="solar", harvest_peak_wh_per_hour=0.03, initial_soc=1.0,
    outage_start_h=4, outage_hours=16, enable_backup=True,
    backup_rate_s=1200, backup_bytes=78, backup_chooser="maxcov")
UP = [(0, 600, "blue"), (6 * 3600, 300, "yellow")]


def summarize(tag, r, inst, pol):
    rr = r["routine"]; sv = r["survival"]; b = r["backup"]
    gw = [t.get("gateway_received_at") for t in r.get("mission_timing", [])]
    cc = r.get("command_counters", {})
    final_cfg = {nid: (n.sample_interval_s, n.report_period_s)
                 for nid, n in list(inst.nodes.items())[:4]}
    print(f"--- {tag} ---")
    print(f"  svc={rr['delivered']/rr['n']:.4f} n={rr['n']} missColl={rr.get('missing_collection')} "
          f"missDeliv={rr.get('missing_delivery')} dead={len(sv['dead'])} 末SoC={sv['mean_final_soc']}")
    print(f"  decisions={len(pol.decision_log)} confirmed={len(pol.confirmed)} "
          f"cmds_sent={cc.get('commands_sent')} refused={cc.get('commands_refused')} gw={gw}")
    print(f"  sample final cfg(head)={final_cfg}")
    trig = {}
    for d in pol.decision_log:
        trig[d["trigger"]] = trig.get(d["trigger"], 0) + 1
    print(f"  triggers={trig}")
    return rr["delivered"] / rr["n"]


def run_with(decider, grid, trace=None, tag="A0", seed=0):
    pol = AgentMissionPolicy(UP, decider, decision_grid_s=grid, trace_path=trace, tag=tag,
                             capacity_wh=0.05, sample_wh=4.7e-4)
    kw = dict(BASE); kw["seed"] = seed
    r, inst, _ = run_joint(**kw, mission_schedule=UP, mission_policy_obj=pol)
    return r, inst, pol


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "phase0"
    if mode == "phase0":
        # 参照: MissionChangePolicy dayfeed 修复后 = .4001
        r, inst, pol = run_with(ScriptedDecider("dayfeed"), 60, tag="scripted-dayfeed")
        svc = summarize("scripted dayfeed grid=60 (管道验证, 应对齐 .4001)", r, inst, pol)
        assert abs(svc - 0.4001) < 0.02, f"管道偏离 dayfeed 基准: {svc}"
        assert len(pol.decision_log) > 20 and pol.confirmed, "决策/生效见证缺失"
        print("PHASE0 OK: agent 接线正确, 命令经真实链路下发并生效。")
    elif mode == "llm":
        seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        structured = len(sys.argv) > 3 and sys.argv[3] == "structured"
        tag = "A0-structured" if structured else "A0"
        os.makedirs("results/agent_traces", exist_ok=True)
        trace = f"results/agent_traces/{tag}_seed{seed}_{int(__import__('time').time())}.jsonl"
        dec = LLMDecider(model="deepseek-flash", structured_state=structured,
                         tag=tag, verbose=True)
        r, inst, pol = run_with(dec, 1800, trace=trace, tag=tag, seed=seed)
        summarize(f"{tag} deepseek-flash seed={seed}", r, inst, pol)
        print(f"LLM calls={dec.calls} total_tokens={dec.total_tokens} trace={trace}")
        rr = r["routine"]; sv = r["survival"]
        with open(trace.replace(".jsonl", ".summary.json"), "w", encoding="utf-8") as f:
            json.dump({"tag": tag, "seed": seed,
                       "svc": rr["delivered"] / rr["n"], "n": rr["n"],
                       "missColl": rr.get("missing_collection"),
                       "missDeliv": rr.get("missing_delivery"),
                       "dead": len(sv["dead"]), "soc": sv["mean_final_soc"],
                       "calls": dec.calls, "tokens": dec.total_tokens, "trace": trace,
                       "gw": [t.get("gateway_received_at") for t in r.get("mission_timing", [])]},
                      f, ensure_ascii=False, indent=2)
        print("summary ->", trace.replace(".jsonl", ".summary.json"))
    elif mode == "replay":
        tracep = sys.argv[2]
        seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        dec = ReplayDecider(tracep)
        r, inst, pol = run_with(dec, 1800, trace=None, tag="A0-replay", seed=seed)
        summarize(f"replay {os.path.basename(tracep)}", r, inst, pol)
        final_cfg = {nid: (n.sample_interval_s, n.report_period_s)
                     for nid, n in inst.nodes.items()}
        print("final cfg all:", json.dumps(final_cfg, ensure_ascii=False))
