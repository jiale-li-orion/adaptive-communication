#!/usr/bin/env python3
"""V1 最小回归：obligation binding、unknown 边界、外层 safety。零仿真、零 API。"""
from agent_plan_repair import (PlanRepairDecider, bind_proposal_to_obligations,
                               gate_not_reopened_regression)
from envelope import EnvelopeDecider


class Base:
    kind = "base"
    calls = 0
    total_tokens = 0

    def __init__(self, actions):
        self.actions = dict(actions)

    def decide(self, obs, ctx):
        return dict(self.actions)


def obs(now=21600, hod=12.0, sample=600, report=600, aoi=900,
        cache=1, soc=0.02, soc_age=60, task_end_s=48 * 3600):
    return {
        "now_s": now,
        "clock_hod": hod,
        "mission": {
            "required_period_s": 300,
            "schedule": [
                {"start_s": 0, "period_s": 600, "level": "blue"},
                {"start_s": 21600, "period_s": 300, "level": "yellow"},
            ],
            "task_end_s": task_end_s,
        },
        "link": {"n_heard": 1, "any_node_heard_last_window": True},
        "nodes": [{
            "id": "n00", "alive": True,
            "cur_sample_s": sample, "cur_report_s": report,
            "soc_wh": soc, "soc_evidence_age_s": soc_age,
            "cache_level": cache, "aoi_s": aoi,
            "heard_last_window": True, "in_flight": False,
        }],
    }


def main():
    ctx = {"sparse": 600, "dense": 300, "capacity_wh": 0.05,
           "sample_wh": 4.7e-4, "decision_horizon_s": 1800, "pending": [],
           "harvest_zero_outside_daylight": True}

    binding = bind_proposal_to_obligations(obs(), ctx, "n00", 600, 600)
    assert any(o["release_at"] == 21600 for o in binding["sample_obligations"]), binding
    assert all(o["oid"].startswith("n00:routine:t") for o in binding["sample_obligations"])
    assert binding["sample_unknown_oids"], binding
    assert any(o["future"] for o in binding["sample_obligations"]), binding

    # task tail 不能凭最后一个 schedule 段继续制造不存在的新义务。48h 时最后一个黄级窗已经关采样，
    # 只可能还留有送达宽限中的旧义务，所以 sample binding 应为空。
    tail = bind_proposal_to_obligations(
        obs(now=48 * 3600, hod=6.0, aoi=60), ctx, "n00", 600, 600)
    assert tail["sample_obligations"] == [], tail
    assert all(o["release_at"] < 48 * 3600 for o in tail["report_obligations"]), tail

    # pending 是普通 structured-state 证据：binding 必须记录 proposal 是等待、反转还是覆盖它；
    # 这里只诊断，不把常规 pending reconciliation 偷算成 V1 增量。
    pctx = dict(ctx)
    pctx["pending"] = [{"node_id": "n00", "target": [300, 300],
                        "sent_at_s": 21000, "age_s": 600, "in_flight": True}]
    pb = bind_proposal_to_obligations(obs(), pctx, "n00", 600, 600)
    assert pb["pending_relations"][0]["relation"] == "proposal_reverses_unconfirmed_pending", pb
    pb2 = bind_proposal_to_obligations(obs(), pctx, "n00", 300, 300)
    assert pb2["pending_relations"][0]["relation"] == "proposal_matches_pending", pb2

    # minimal-field pending 只约束真正 sent 的字段：sample 已在途时，report proposal 不同不能把
    # 整条 pending 误标成 supersede。
    pctx["pending"] = [{"node_id": "n00", "target": [300, 300],
                        "sent_at_s": 21000, "age_s": 600, "in_flight": None,
                        "fields_sent": ["set_sampling_interval"]}]
    pb3 = bind_proposal_to_obligations(obs(), pctx, "n00", 300, 600)
    assert pb3["pending_relations"][0]["relation"] == "proposal_matches_pending", pb3
    pb4 = bind_proposal_to_obligations(obs(), pctx, "n00", 600, 300)
    assert pb4["pending_relations"][0]["relation"] == "proposal_reverses_unconfirmed_pending", pb4

    # R-b 只恢复 task-required candidate，并记录具体 obligation。
    repair = PlanRepairDecider(Base({"n00": (600, 600)}))
    out = repair.decide(obs(), ctx)
    assert out["n00"][0] == 300, out
    entry = repair.decisions[-1]["log"][0]
    assert entry["rule"] == "R-b-task-conflict-densify", entry
    assert entry["binding_oids"], entry

    # “fresh SoC” 必须有证据时刻；age=None 是 unknown，不能按 fresh 放行 R-b。
    repair = PlanRepairDecider(Base({"n00": (600, 600)}))
    out = repair.decide(obs(soc_age=None), ctx)
    assert out["n00"][0] == 600, out
    assert not repair.decisions[-1]["log"], repair.decisions[-1]

    # R-a 的 source backlog + AoI 不足以撤销仍会影响未来 unknown obligation 的持续采样。
    repair = PlanRepairDecider(Base({"n00": (300, 300)}))
    out = repair.decide(obs(), ctx)
    assert out["n00"][0] == 300, out
    assert not repair.decisions[-1]["log"], repair.decisions[-1]
    assert any(d.get("candidate") == "R-a-upstream-congestion"
               for d in repair.decisions[-1]["diagnostics"]), repair.decisions[-1]

    # 夜间不能 blanket hard-gate：20 mWh 足以覆盖 hod=2 到 6 点 dense-vs-sparse 的安全调整额外账，
    # 所以只能 advisory，保留 R-b 的 candidate。
    outer = EnvelopeDecider(PlanRepairDecider(Base({"n00": (600, 600)})), mode="evidence")
    out = outer.decide(obs(hod=2.0), ctx)
    assert out["n00"] == (300, 600), out
    assert any(c[0] == "night_energy_advisory"
               for c in outer.envelope_log[-1]["corrections"]), outer.envelope_log[-1]

    # 证据充分的 ENERGY-INFEASIBLE 仍必须拥有最终否决权。
    outer = EnvelopeDecider(Base({"n00": (300, 300)}), mode="evidence")
    out = outer.decide(obs(hod=2.0, soc=0.005), ctx)
    assert out["n00"] == (600, 300), out
    assert any(c[0] == "energy_infeasible"
               for c in outer.envelope_log[-1]["corrections"]), outer.envelope_log[-1]

    # 同样的低 SoC 若证据跨过上一段 daylight，期间可能已充电；不能继续当当前低电证明。
    outer = EnvelopeDecider(Base({"n00": (300, 300)}), mode="evidence")
    out = outer.decide(obs(hod=2.0, soc=0.005, soc_age=9 * 3600), ctx)
    assert out["n00"] == (300, 300), out
    assert any(c[0] == "night_energy_advisory"
               for c in outer.envelope_log[-1]["corrections"]), outer.envelope_log[-1]

    # dusk 是调度建议，不是物理不可行证书。
    outer = EnvelopeDecider(Base({"n00": (300, 300)}), mode="evidence")
    out = outer.decide(obs(hod=17.0, soc=0.02), ctx)
    assert out["n00"] == (300, 300), out
    assert any(c[0] == "dusk_advisory"
               for c in outer.envelope_log[-1]["corrections"]), outer.envelope_log[-1]

    reg = gate_not_reopened_regression()
    assert reg["violations"] == [], reg

    # ordinary envelope 不得把 None 偷换成“已确认 sparse”后再据此开放升级。
    unknown = obs()
    unknown["nodes"][0]["cur_sample_s"] = None
    unknown["nodes"][0]["cur_report_s"] = None
    unknown["link"]["n_heard"] = 1
    unknown["link"]["any_node_heard_last_window"] = True
    outer = EnvelopeDecider(Base({"n00": (300, 300)}), mode="evidence")
    out = outer.decide(unknown, ctx)
    assert out["n00"] == (600, 600), out
    assert any(c[0] == "config_unknown"
               for c in outer.envelope_log[-1]["corrections"]), outer.envelope_log[-1]

    # ACCESS receipt 不等于 control-plane reachability。已知当前配置、heard<n 时，ordinary
    # envelope 不得把合法 dense proposal/previous target 回滚成 current；这里只能 advisory。
    partial = obs()
    partial["nodes"][0]["cur_sample_s"] = 600
    partial["nodes"][0]["cur_report_s"] = 600
    partial["link"]["n_heard"] = 0
    partial["link"]["any_node_heard_last_window"] = False
    outer = EnvelopeDecider(Base({"n00": (300, 300)}), mode="evidence")
    out = outer.decide(partial, ctx)
    assert out["n00"] == (300, 300), out
    assert any(c[0] == "access_partial_advisory"
               for c in outer.envelope_log[-1]["corrections"]), outer.envelope_log[-1]

    # 历史 r39 的 legacy mode 必须保持原语义：同一个 ACCESS-partial snapshot 下，
    # 它会把 dense proposal 回滚到 confirmed sparse。该模式只用于注册实验复现。
    legacy = EnvelopeDecider(Base({"n00": (300, 300)}), mode="legacy_clock")
    out = legacy.decide(partial, ctx)
    assert out["n00"] == (600, 600), out
    assert any(c[0] == "control_unconfirmed"
               for c in legacy.envelope_log[-1]["corrections"]), legacy.envelope_log[-1]
    assert legacy.envelope_log[-1]["mode"] == "legacy_clock"

    print("PASS obligation-binding / R-a unknown / R-b candidate / outer-safety")


if __name__ == "__main__":
    main()
