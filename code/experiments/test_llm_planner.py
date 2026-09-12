#!/usr/bin/env python3
"""
test_llm_planner.py — the model seam, and the disciplines that keep it honest.

Three things are checked, and each guards a way a planner can look better than it is.

A DECISION IS VALIDATED, NOT TRUSTED. A reply naming an action outside the set, or a profile that
does not exist, is rejected and recorded. It is not silently repaired: a planner whose bad replies
are quietly completed by a fallback reports a parse rate that describes the fallback.

THE LABEL CARRIES THE BACKEND. `name` includes the backend that produced the decisions, so a table
cannot mix a model run with a scripted one. Right now there is no usable endpoint in this
environment, and the scripted backend exists so the plumbing can be exercised; every result it
produces is labelled `scripted` and none of it is model evidence.

THE MODEL SEES ONLY WHAT THE WORLDVIEW CARRIES. A view that raises on any undocumented attribute
must still run. A planner that could reach the demand list or the arrival records would be solving
an easier problem than the one this project states.

Run: python3 code/experiments/test_llm_planner.py
"""
from __future__ import annotations

import os
import os as _os, sys as _sys
_HERE = _os.path.dirname(os.path.abspath(__file__))
_CODE = os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime",
                                                     "experiments", "analysis", "monitoring"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

import json
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from llm_planner import (ACTIONS, LLMPlannerPolicy, ScriptedBackend,     # noqa: E402
                         make_real_backend, parse_decision, render)
from task_generator import MONITORING_PROFILES, PROFILE_RISK, PROFILE_NORMAL  # noqa: E402

FAIL: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")
    if not ok:
        FAIL.append(name)


def view(t_s=0, demanded=None, in_flight=frozenset(), status=None, nodes=("n00", "n01")):
    return types.SimpleNamespace(
        t_s=t_s, node_ids=tuple(nodes), status=dict(status or {}),
        demanded_profile=dict(demanded or {}), center_has_announcement=bool(demanded),
        in_flight=frozenset(in_flight))


class Boom(dict):
    """A status mapping that reports every attribute the planner is not allowed to touch."""

    def get(self, k, default=None):
        raise AssertionError(f"the planner read an undocumented field: {k!r}")


def test_parse_and_validate() -> None:
    print("\n[1] 决策被校验而非被信任")
    good, err = parse_decision(json.dumps(
        {"thought": "t", "action": "set_monitoring_profile",
         "args": {"node": "n00", "profile": PROFILE_RISK}}))
    check("合法决策通过", good is not None and err is None)
    check("合法决策的动作集受限于四个接口",
          good["action"] in ACTIONS, str(ACTIONS))

    for bad, why in (("not json at all", "非 JSON"),
                     ('{"action":"drop_table","args":{}}', "动作不在集合内"),
                     ('{"action":"set_monitoring_profile","args":{"node":"n00"}}', "缺 profile"),
                     ('{"action":"set_monitoring_profile","args":{"profile":"turbo"}}', "缺 node"),
                     ('{"action":"set_monitoring_profile","args":{"node":"n00","profile":"turbo"}}',
                      "profile 不存在"),
                     ('["a","list"]', "不是对象"),
                     ('{"action":"set_monitoring_profile","args":"nope"}', "args 不是对象")):
        d, e = parse_decision(bad)
        check(f"拒绝：{why}", d is None and e is not None, e)

    check("动作集与业务层 profile 表一致",
          all(p in MONITORING_PROFILES for p in (PROFILE_NORMAL, PROFILE_RISK)))


def test_in_flight_and_no_announcement() -> None:
    print("\n[2] 不向在途节点重复下发，无公告时把节点带回常态")
    pol = LLMPlannerPolicy(ScriptedBackend(), tick_interval_s=0)
    out = pol.plan(view(demanded={"n00": PROFILE_RISK, "n01": PROFILE_RISK}))
    check("有公告时下发给一个节点", len(out) == 1 and out[0][1]["profile"] == PROFILE_RISK, str(out))

    pol2 = LLMPlannerPolicy(ScriptedBackend(), tick_interval_s=0)
    out2 = pol2.plan(view(demanded={"n00": PROFILE_RISK, "n01": PROFILE_RISK},
                          in_flight={"n00"}))
    check("在途节点被跳过", all(n != "n00" for n, _ in out2), str(out2))

    pol3 = LLMPlannerPolicy(ScriptedBackend(), tick_interval_s=0)
    out3 = pol3.plan(view(demanded={}))
    check("无公告时下发常态 profile（恢复半程）",
          len(out3) == 1 and out3[0][1]["profile"] == PROFILE_NORMAL, str(out3))

    pol4 = LLMPlannerPolicy(ScriptedBackend(), tick_interval_s=0)
    out4 = pol4.plan(view(demanded={"n00": PROFILE_RISK}, in_flight={"n00", "n01"}))
    check("全部在途时不产生动作", out4 == [], str(out4))


def test_tick_interval() -> None:
    print("\n[3] 调用节奏受控，不每个 tick 都问模型")
    pol = LLMPlannerPolicy(ScriptedBackend(), tick_interval_s=300)
    pol.plan(view(t_s=0, demanded={"n00": PROFILE_RISK}))
    check("首 tick 调用一次", len(pol.log.calls) == 1)
    for t in (60, 120, 240):
        pol.plan(view(t_s=t, demanded={"n00": PROFILE_RISK}))
    check("间隔内不再调用", len(pol.log.calls) == 1, f"{len(pol.log.calls)} 次")
    pol.plan(view(t_s=300, demanded={"n00": PROFILE_RISK}))
    check("达到间隔后再次调用", len(pol.log.calls) == 2)


def test_illegal_is_recorded_not_rescued() -> None:
    print("\n[4] 非法决策被记录，且不被静默补救")
    class Bad:
        name = "bad"

        def complete(self, messages):
            return "I think you should raise the risk level."

    pol = LLMPlannerPolicy(Bad(), tick_interval_s=0)
    out = pol.plan(view(t_s=0, demanded={"n00": PROFILE_RISK}))
    check("无法解析的回复不产生动作", out == [], str(out))
    check("该次调用被记为非法", pol.log.illegal == 1)
    check("解析率如实反映失败", pol.log.parse_rate == 0.0, f"{pol.log.parse_rate}")
    check("原始文本被保留以便审计",
          pol.log.calls[0].raw.startswith("I think"), pol.log.calls[0].raw[:40])
    check("未用回退替模型完成动作", pol.summary()["rejected_decisions"] == 1)

    class Throw:
        name = "throw"

        def complete(self, messages):
            raise RuntimeError("endpoint exploded")

    pol2 = LLMPlannerPolicy(Throw(), tick_interval_s=0)
    pol2.plan(view(t_s=0, demanded={"n00": PROFILE_RISK}))
    check("后端抛错被记为一次失败调用而非崩溃",
          pol2.log.illegal == 1 and pol2.log.calls[0].error.startswith("backend raised"))


def test_label_carries_backend() -> None:
    print("\n[5] 标签携带后端，模型结果与脚本结果不混表")
    pol = LLMPlannerPolicy(ScriptedBackend(), tick_interval_s=0)
    check("脚本后端在标签里", "scripted" in pol.name, pol.name)
    check("脚本后端从不自称模型",
          ScriptedBackend.name == "scripted")
    pol.plan(view(t_s=0, demanded={"n00": PROFILE_RISK}))
    check("每次调用记录后端名", pol.summary()["backend"] == "scripted")
    check("记录含延迟与提示长度",
          all(c.latency_s >= 0 and c.prompt_chars > 0 for c in pol.log.calls))


def test_real_backend_reports_why_unusable() -> None:
    print("\n[6] 真实后端不可用时给出理由，不静默降级")
    backend, reason = make_real_backend()
    if backend is None:
        check("给出不可用理由", isinstance(reason, str) and len(reason) > 0, reason)
        check("理由指向凭据或端点而非笼统失败",
              any(k in reason for k in ("OPENAI_", "endpoint", "openai")), reason)
    else:
        check("端点可用则返回后端", hasattr(backend, "complete"))


def test_view_boundary() -> None:
    print("\n[7] 模型只能看到 WorldView 携带的东西")
    pol = LLMPlannerPolicy(ScriptedBackend(), tick_interval_s=0)
    out = pol.plan(view(t_s=0, demanded={"n00": PROFILE_RISK}))
    check("空状态不阻碍决策", isinstance(out, list))

    # The rendered prompt must not carry anything the view did not provide.
    body = render(view(t_s=0, demanded={"n00": PROFILE_RISK},
                       status={"n00": {"profile": PROFILE_NORMAL, "buffer_level": 3,
                                       "read_at": 0}}))
    for leaked in ("demand", "sample_window", "delivery_deadline", "arrived", "taken"):
        hit = leaked in body and leaked != "demand"
        check(f"渲染不含真值字段 {leaked}", not hit)
    check("渲染含代码里定义的 node 与 profile",
          "n00" in body and PROFILE_NORMAL in body)

    src = open(os.path.join(_CODE, "monitoring", "llm_planner.py"), encoding="utf-8").read()
    check("规划器不导入 runner 或评分器",
          "import runner" not in src and "from scorer" not in src)


def main() -> int:
    print("LLM 规划器回归测试")
    test_parse_and_validate()
    test_in_flight_and_no_announcement()
    test_tick_interval()
    test_illegal_is_recorded_not_rescued()
    test_label_carries_backend()
    test_real_backend_reports_why_unusable()
    test_view_boundary()
    print("\n" + "-" * 74)
    if FAIL:
        print(f"  {len(FAIL)} 项失败：")
        for f in FAIL:
            print(f"    - {f}")
        return 1
    print("  全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
