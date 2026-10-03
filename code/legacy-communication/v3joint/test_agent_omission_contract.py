#!/usr/bin/env python3
"""Agent 输出契约回归：omission/HOLD 必须保留 previous target。零 API。"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
for _d in ("v3joint", "instance", "physics", "runtime", "experiments", "analysis", "monitoring"):
    _p = os.path.join(ROOT, "code", _d)
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agent_mission import AgentMissionPolicy, LLMDecider, sustain_targets
from envelope import enforce_feasibility


def _obs():
    return {
        "nodes": [
            {"id": "n00", "cur_sample_s": 600, "cur_report_s": 600},
            {"id": "n01", "cur_sample_s": 300, "cur_report_s": 600},
        ]
    }


def main():
    ctx = {"sparse": 600}

    # 模型只显式修改 n00；n01 被省略，parser 不得把 current config 伪装成新的 action。
    raw = json.dumps({
        "actions": [{
            "node_id": "n00",
            "sample_period_s": 300,
            "report_period_s": 300,
        }]
    })
    actions, note = LLMDecider._parse(raw, _obs(), ctx)
    assert note == "", (actions, note)
    assert actions == {"n00": (300, 300)}, actions
    assert "n01" not in actions, actions

    # API/解析失败的 HOLD 同样必须返回空动作，由 policy 保留已有 sticky target。
    actions, note = LLMDecider._parse(None, _obs(), ctx)
    assert actions == {} and note == "llm_failed->hold", (actions, note)
    actions, note = LLMDecider._parse("not-json", _obs(), ctx)
    assert actions == {} and note == "unparseable->hold", (actions, note)

    # omission 契约只有在模型明确知道 current sticky target 时才闭合；不能靠最近几条 history 猜。
    d = object.__new__(LLMDecider)
    d.structured_state = False
    _sysp, usr = d._prompt(
        {"now_s": 0, "nodes": []},
        {"sample_wh": 4.7e-4, "capacity_wh": 0.05, "sparse": 600, "dense": 300,
         "current_targets": {"n00": [300, 600]}, "history": []})
    assert "CURRENT STICKY TARGETS" in usr, usr
    assert '"n00": [300, 600]' in usr, usr

    # wrapper 也必须遵守 omission contract：previous target 尚未确认时，模型省略节点不能被
    # EnvelopeDecider 的“全节点 map”重置成当前 confirmed config。
    eobs = {
        "clock_hod": 12.0,
        "mission": {"required_period_s": 300},
        "link": {"n_heard": 1},
        "nodes": [{"id": "n00", "cur_sample_s": 600, "cur_report_s": 600,
                   "soc_wh": 0.001, "soc_evidence_age_s": 60}],
    }
    ectx = {"sparse": 600, "dense": 300, "sample_wh": 4.7e-4,
            "harvest_zero_outside_daylight": True,
            "current_targets": {"n00": [300, 300]}}
    out, corr = enforce_feasibility({}, eobs, ectx)
    assert out["n00"] == (300, 300), (out, corr)

    # 同一 previous target 到夜间，只有证据充分的 energy-infeasible 才能 hard revoke。
    eobs["clock_hod"] = 23.0
    out, corr = enforce_feasibility({}, eobs, ectx)
    assert out["n00"] == (600, 300), (out, corr)
    assert any(c[0] == "energy_infeasible" for c in corr), corr

    # SoC 足够时夜间只能 advisory；时钟本身不能证明 dense sample 不可行。
    eobs["nodes"][0]["soc_wh"] = 0.05
    out, corr = enforce_feasibility({}, eobs, ectx)
    assert out["n00"] == (300, 300), (out, corr)
    assert any(c[0] == "night_energy_advisory" for c in corr), corr

    # 显式节点内非法/缺字段仍可按当前确认配置做逐字段 fallback；不影响省略语义。
    raw = json.dumps({
        "actions": [{
            "node_id": "n01",
            "sample_period_s": 123,
            "report_period_s": None,
        }]
    })
    actions, note = LLMDecider._parse(raw, _obs(), ctx)
    assert actions == {"n01": (300, 600)}, actions
    assert note == "clamped_2", note

    # 字段级 malformed 也不能撤销 previous target：n01 当前 report=600，但 policy 仍有
    # 未确认 report=300；模型只给合法 sample、漏掉 report 时应保留 previous report=300。
    ctx_pending = {"sparse": 600, "current_targets": {"n01": [300, 300]}}
    raw = json.dumps({
        "actions": [{
            "node_id": "n01",
            "sample_period_s": 300,
            "report_period_s": None,
        }]
    })
    actions, note = LLMDecider._parse(raw, _obs(), ctx_pending)
    assert actions == {"n01": (300, 300)}, actions
    assert note == "clamped_1", note

    # 新 baseline 的执行器只发送 confirmed current 与 target 真正不同的字段。
    class _Dec:
        kind = "const"
        def decide(self, obs, ctx):
            return {"n00": (300, 600)}

    class _View:
        t_s = 0
        node_ids = ["n00"]
        reports = {"n00": {"read_at": 0, "alive": True, "soc_wh": 0.02,
                           "sample_interval_s": 600, "report_period_s": 600,
                           "cache_level": 0}}
        report_at = {"n00": 0}
        newest_taken_at = {"n00": 0}
        in_flight = set()
        def heard_recently(self, nid, within_s): return True
        def soc_of(self, nid): return 0.02
        def soc_age_s(self, nid): return 0
        def aoi_s(self, nid): return 0

    pol = AgentMissionPolicy([(0, 300, "yellow")], _Dec(),
                             minimal_field_commands=True,
                             use_physical_inflight=False)
    base_cmds = pol.plan(_View())
    assert len(base_cmds) == 1, base_cmds
    assert base_cmds[0][1].get("op") == "set_sampling_interval", base_cmds
    assert base_cmds[0][1].get("fields") == ["set_sampling_interval"], base_cmds

    # 新 Agent baseline 不得消费 CenterView 里“gateway queue 是否非空”的精确特权。
    # 同一个合法中心历史下，即使 legacy view.in_flight 暗示队列非空，仍只按自己的
    # attempt/sent ledger 决定是否重试；旧复现模式则保留原 skip 行为。
    v = _View()
    v.in_flight = {"n00"}
    legal = AgentMissionPolicy([(0, 300, "yellow")], _Dec(),
                               minimal_field_commands=True,
                               use_physical_inflight=False)
    cmds = legal.plan(v)
    assert len(cmds) == 1, cmds
    nobs, _, _ = legal._observation(v)
    assert nobs["nodes"][0]["in_flight"] is None, nobs
    assert nobs["nodes"][0]["in_flight_source"] == "unavailable_at_center", nobs
    assert nobs["nodes"][0]["pending_unconfirmed"] is False, nobs

    legacy = AgentMissionPolicy([(0, 300, "yellow")], _Dec(),
                                minimal_field_commands=True,
                                use_physical_inflight=True)
    cmds = legacy.plan(v)
    assert cmds == [], cmds

    # plan() 只是生成 intent；control plane 尚未接受前，不得伪装成“已发送未确认”的 pending。
    assert pol._pending_list(_View()) == [], pol.sent_ledger
    assert pol.attempt_ledger["n00"]["target"] == [300, 600], pol.attempt_ledger
    pol.note_command_sent("n00", base_cmds[0][1])
    pending = pol._pending_list(_View())
    assert len(pending) == 1 and pending[0]["target"] == [300, 600], pending
    assert pending[0]["fields_sent"] == ["set_sampling_interval"], pending
    sent_obs, _, _ = pol._observation(_View())
    la = sent_obs["nodes"][0]["last_command_attempt"]
    assert la["status"] == "accepted_by_control_plane", la
    assert la["fields_accepted"] == ["set_sampling_interval"], la

    # 被 control plane 明确拒绝的写入是合法 tool result：必须对普通 A0 也可见，且绝不能进入 pending。
    refused_pol = AgentMissionPolicy([(0, 300, "yellow")], _Dec(),
                                     minimal_field_commands=True,
                                     use_physical_inflight=False)
    refused_cmds = refused_pol.plan(_View())
    refused_pol.note_command_refused("n00", refused_cmds[0][1])
    assert refused_pol._pending_list(_View()) == [], refused_pol.sent_ledger
    refused_obs, _, _ = refused_pol._observation(_View())
    la = refused_obs["nodes"][0]["last_command_attempt"]
    assert la["status"] == "refused_by_control_plane", la
    assert la["fields_refused"] == ["set_sampling_interval"], la
    assert pending[0]["in_flight"] is None, pending
    assert pending[0]["in_flight_source"] == "unavailable_at_center", pending

    # partial accept 的 pending 完成只看 fields_sent：未发送的 report 字段不得把已确认 sample
    # 永久挂成 pending。
    partial_pol = AgentMissionPolicy([(0, 300, "yellow")], _Dec(),
                                     minimal_field_commands=True,
                                     use_physical_inflight=False)
    partial_pol.sent_ledger["n00"] = {
        "target": [300, 300], "at_s": 0, "generation": 1,
        "fields": ["set_sampling_interval"]}
    pv = _View()
    pv.reports = {"n00": {"read_at": 60, "alive": True, "soc_wh": 0.02,
                          "sample_interval_s": 300, "report_period_s": 600,
                          "cache_level": 0}}
    pv.t_s = 60
    assert partial_pol._pending_list(pv) == [], partial_pol._pending_list(pv)

    # dwell 只限制“同 target 重试”，不能让旧 attempt 阻塞后来的新 target。
    class _FlipDec:
        kind = "flip"
        def decide(self, obs, ctx):
            return {"n00": (600, 300)} if obs["now_s"] < 60 else {"n00": (300, 300)}

    class _FlipView(_View):
        t_s = 0

    flip = AgentMissionPolicy([(0, 600, "blue"), (60, 300, "yellow")], _FlipDec(),
                              dwell_s=1800, minimal_field_commands=True,
                              target_scoped_dwell=True)
    first = flip.plan(_FlipView())
    assert first, first
    # 不更新 confirmed report，模拟第一目标尚未生效；60s 后任务变化产生新 target。
    _FlipView.t_s = 60
    second = flip.plan(_FlipView())
    assert second, (flip.targets, flip.attempt_ledger, flip.skip_report())
    assert flip.attempt_ledger["n00"]["target"] == [300, 300], flip.attempt_ledger

    # sustain tool suggestion 也要保留 10/5 mWh 滞回语义：6 mWh 可维持已经 dense 的节点，
    # 但不能把一个 sparse/unknown 节点重新升级成 dense。
    sobs = {
        "mission": {"required_period_s": 300},
        "nodes": [
            {"id": "dense", "soc_wh": 0.006, "cur_sample_s": 300, "cur_report_s": 300},
            {"id": "sparse", "soc_wh": 0.006, "cur_sample_s": 600, "cur_report_s": 600},
            {"id": "unknown", "soc_wh": 0.006, "cur_sample_s": None, "cur_report_s": None},
        ],
    }
    sout = sustain_targets(sobs, 600, 300, healthy_wh=0.010, exit_wh=0.005)
    assert sout["dense"] == (300, 300), sout
    assert sout["sparse"] == (600, 600), sout
    assert sout["unknown"] == (600, 600), sout

    print("PASS omission keeps previous target / HOLD emits no target rewrite")


if __name__ == "__main__":
    main()
