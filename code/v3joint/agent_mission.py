#!/usr/bin/env python3
"""agent_mission.py — 顺序3 真实 Agent 在线任务编译策略（doc38 §5/§7）。

与 MissionChangePolicy **同接口、同 center 放置、同 stamp_pair 命令机制**：Agent 不直接写节点、
不读环境真值、不调 evaluate()；它在离散决策点看到一份只由 CenterView 派生的合法观察 + 外生公开
的授权任务 + 现成普通求解工具(dayfeed/sustain/comply/ignore)的建议，输出每节点目标采样/上报周期，
命令仍经回传进网关队列、在 Class A 接收窗口才落地生效（排队/送达/生效三阶段由仿真与后续回执体现）。

三层臂共用本策略与同一工具集，差别只在 decider：
  A0            = LLMDecider(structured_state=False)：通用 agent + 滚动合法历史 + 普通工具建议；
  A0-structured = LLMDecider(structured_state=True) ：再加显式未决操作列表/逐节点核对流程(普通工程记忆)；
  A1            = 在 A0-structured 上再开**一项**义务链反例反馈（后续文件，先不实现）。

动作空间对所有臂相同：每节点采样周期、上报周期各取协议合法档 {sparse, dense}（默认 600/300 s），
与 mission 等级两档一致；非法模型输出钳制到最近合法档并留痕，不向模型开放任何额外执行特权。

决策点（事件 + 网格，避免每 tick 调 LLM）：首次、授权要求变化沿、回传恢复沿（center 视角从无任何
节点近期上报到有）、固定网格。两次决策之间策略维持 decider 给的目标，按 in_flight/dwell/at_target
节流下发——等价于"agent 提交一份持续配置计划、本地执行器按既有链路安装"。
"""
from __future__ import annotations

import json
import os
import time
import urllib.request

from center import (CenterPolicy, CenterView, OP_SET_REPORT_PERIOD,
                    OP_SET_SAMPLING_INTERVAL)
from mission_policy import required_period

LEGAL_PERIODS = (300, 600)


def _legal_period(v, fallback):
    try:
        p = int(v)
    except (TypeError, ValueError):
        return fallback, False
    if p in LEGAL_PERIODS:
        return p, True
    clamped = min(LEGAL_PERIODS, key=lambda x: abs(x - p))
    return clamped, False


# ---------------------------------------------------------------------------
# 普通求解工具（也是给 LLM 的工具建议）：从合法观察给每节点目标，纯函数、无未来真值
# ---------------------------------------------------------------------------
def dayfeed_targets(obs, sparse, dense, day_start=6.0, daylight=12.0):
    """标称昼夜前馈（与 mission_policy.dayfeed 同规则，但作用于一份观察快照）。"""
    req = obs["mission"]["required_period_s"]
    if req >= sparse:
        p = sparse
    else:
        hod = (day_start + obs["now_s"] / 3600.0) % 24.0
        p = req if (day_start <= hod < day_start + daylight) else sparse
    return {n["id"]: (p, p) for n in obs["nodes"]}


def sustain_targets(obs, sparse, dense, healthy_wh=0.010, exit_wh=0.005):
    """持续滞回能量保护（近似 mission_policy.sustain 的单拍建议：电够则密、否则疏）。"""
    req = obs["mission"]["required_period_s"]
    out = {}
    for n in obs["nodes"]:
        if req >= sparse:
            p = sparse
        else:
            soc = n.get("soc_wh")
            p = req if (soc is not None and soc >= exit_wh) else sparse
        out[n["id"]] = (p, p)
    return out


def comply_targets(obs, sparse, dense):
    req = obs["mission"]["required_period_s"]
    return {n["id"]: (req, req) for n in obs["nodes"]}


def ignore_targets(obs, sparse, dense):
    return {n["id"]: (sparse, sparse) for n in obs["nodes"]}


class ScriptedDecider:
    """管道验证 / 强普通规则：直接采用某条现成规则，不调 LLM。"""
    def __init__(self, mode="dayfeed"):
        self.mode = mode
        self.kind = f"scripted-{mode}"

    def decide(self, obs, ctx):
        sparse = ctx["sparse"]; dense = ctx["dense"]
        if self.mode == "dayfeed":
            return dayfeed_targets(obs, sparse, dense)
        if self.mode == "sustain":
            return sustain_targets(obs, sparse, dense)
        if self.mode == "comply":
            return comply_targets(obs, sparse, dense)
        return ignore_targets(obs, sparse, dense)


class ReplayDecider:
    """从已落盘 trace 按决策序号重放 actions（离线复现 svc，不再调 API）。

    仅在同 seed/同参数/同 policy 触发序列下有效：重放逐拍给出与原始一致的动作，确定性链路下
    节点配置/上报/恢复沿随之重现，故决策触发序列与原 run 对齐。用于进程被杀后复现指标与可重复分析。
    """
    def __init__(self, path):
        self.rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
        self.i = 0
        self.kind = "replay"

    def decide(self, obs, ctx):
        if self.i >= len(self.rows):
            return {}
        r = self.rows[self.i]
        self.i += 1
        return {k: tuple(v) for k, v in r.get("actions", {}).items()}


SYSTEM_PROMPT = """You are the on-duty mission controller for a pre-disaster geohazard (landslide) \
monitoring deployment in a mountainous area.

HARDWARE & SCENE (fixed, true for the whole run):
- Field sensor nodes sample a displacement/rainfall measurand and upload to a local gateway over \
LoRaWAN Class A. The gateway forwards to the central server over an intermittent cellular backhaul; \
a very sparse short-message backup link exists but its packet SELECTION is handled automatically by \
the gateway (you do not control it).
- Nodes are battery + small solar powered. Energy is tight: a sample costs about {sample_wh:.1e} Wh and \
battery capacity is {capacity_wh:.3f} Wh. Dense sampling (period {dense}s) through a long night with \
no harvest can DRAIN and PERMANENTLY kill nodes; sparse period is {sparse}s.
- Class A downlinks are NOT immediate: a config command you emit only reaches a node in its next \
receive window after it transits the backhaul and gateway; during a backhaul outage your commands are \
refused and you also stop receiving fresh telemetry. A command therefore goes queued -> in transit -> \
APPLIED (only confirmed when the node later reports the new config).

YOUR JOB:
- An authorised warning-level schedule tells you the REQUIRED sampling period over time (it is \
exogenous and legitimate; you do NOT judge landslide risk). Compile it into per-node config \
(sample_period_s, report_period_s) that can actually be executed under energy and the link you have.
- Use the tool suggestions (dayfeed/sustain/comply/ignore): they are strong ordinary baselines you may \
adopt or overrule. They cannot see anything you cannot see.
- Protect the mission: dense monitoring has value while the elevated requirement holds and nodes can \
survive it; killing nodes or issuing commands that cannot be applied helps nothing.

OUTPUT STRICT JSON ONLY (no prose outside it):
{{"actions":[{{"node_id":"n00","sample_period_s":300,"report_period_s":300,"reason":"short"}}],
  "note":"one line plan"}}
- Periods must be one of {legal}. Nodes omitted from "actions" KEEP their previous target.
- sample_period_s and report_period_s are two independent protocol fields; set them as you see fit.
- Only act on evidence you can actually see; never assume a command applied until a report confirms it.
"""


class LLMDecider:
    def __init__(self, model="deepseek-flash", structured_state=False, api_key=None,
                 base_url="https://api.deepseek.com", max_tokens=4000, timeout_s=90,
                 reasoning_effort="low", tag="A0", verbose=False):
        self.model = model
        self.structured_state = structured_state
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s
        self.reasoning_effort = reasoning_effort
        self.tag = tag
        self.verbose = verbose
        self.kind = tag + ("-structured" if structured_state else "")
        self.calls = 0
        self.total_tokens = 0

    def _prompt(self, obs, ctx):
        sysp = SYSTEM_PROMPT.format(sample_wh=ctx["sample_wh"], capacity_wh=ctx["capacity_wh"],
                                    sparse=ctx["sparse"], dense=ctx["dense"], legal=list(LEGAL_PERIODS))
        lines = ["CURRENT LEGAL OBSERVATION (center view; no future truth):",
                 json.dumps(obs, ensure_ascii=False, indent=None)]
        if ctx.get("history"):
            lines.append("\nRECENT DECISION HISTORY (oldest->newest):")
            lines.append(json.dumps(ctx["history"], ensure_ascii=False))
        if self.structured_state and ctx.get("pending"):
            lines.append("\nPENDING/UNRESOLVED COMMANDS (engineering checklist: verify each applies; "
                         "re-issue only if still wanted and not in-flight):")
            lines.append(json.dumps(ctx["pending"], ensure_ascii=False))
        elif self.structured_state:
            lines.append("\nNo pending commands; verify current configs match the mission.")
        lines.append("\nDecide now. Emit the strict JSON object.")
        return sysp, "\n".join(lines)

    def decide(self, obs, ctx):
        sysp, usr = self._prompt(obs, ctx)
        # flash 是推理模型: 默认 low effort 控制思维长度; 若可见 content 仍为空(推理耗尽预算),
        # 第二次回退到关闭思考, 保证产出 JSON, 而不是把空内容误判成"agent 选择 hold"。
        configs = [
            {"reasoning_effort": self.reasoning_effort, "max_tokens": self.max_tokens},
            {"thinking": {"type": "disabled"}, "max_tokens": min(self.max_tokens, 2000)},
        ]
        raw, err, usage, finish, data = None, None, {}, None, None
        for attempt, cfg in enumerate(configs):
            payload = {"model": self.model,
                       "messages": [{"role": "system", "content": sysp},
                                    {"role": "user", "content": usr}],
                       "temperature": 0,
                       "response_format": {"type": "json_object"}, "stream": False}
            payload.update(cfg)
            req = urllib.request.Request(
                self.base_url + "/chat/completions", data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {self.api_key}",
                         "Content-Type": "application/json"}, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                msg = data["choices"][0]["message"]
                finish = data["choices"][0].get("finish_reason")
                usage = data.get("usage", {})
                if msg.get("content"):
                    raw = msg["content"]
                    break
                err = f"empty content finish={finish}"
            except Exception as e:  # noqa: BLE001
                err = f"{type(e).__name__}: {e}"
                time.sleep(2 + 3 * attempt)
        self.calls += 1
        self.total_tokens += int(usage.get("total_tokens", 0))
        actions, parse_note = self._parse(raw, obs, ctx)
        self._last_raw = raw
        self._last_err = err
        self._last_usage = usage
        self._parse_note = parse_note
        if self.verbose:
            print(f"[{self.kind}] t={obs['now_s']} call={self.calls} tok={usage.get('total_tokens')} "
                  f"err={err} actions={len(actions)} {parse_note}")
        return actions

    @staticmethod
    def _parse(raw, obs, ctx):
        sparse = ctx["sparse"]
        cur = {n["id"]: (n.get("cur_sample_s") or sparse, n.get("cur_report_s") or sparse)
               for n in obs["nodes"]}
        note = ""
        if raw is None:
            return dict(cur), "llm_failed->hold"
        try:
            obj = json.loads(raw)
        except Exception:
            s = raw[raw.find("{"): raw.rfind("}") + 1]
            try:
                obj = json.loads(s)
            except Exception:
                return dict(cur), "unparseable->hold"
        out = dict(cur)
        clamped = 0
        ids = {n["id"] for n in obs["nodes"]}
        for a in obj.get("actions", []):
            nid = a.get("node_id")
            if nid not in ids:
                continue
            fb_s, fb_p = out[nid]
            ps, oks = _legal_period(a.get("sample_period_s"), fb_s)
            pp, okp = _legal_period(a.get("report_period_s"), fb_p)
            clamped += (not oks) + (not okp)
            out[nid] = (ps, pp)
        if clamped:
            note = f"clamped_{clamped}"
        return out, note


class AgentMissionPolicy(CenterPolicy):
    name = "agent-mission"

    def __init__(self, schedule, decider, scope=None, dwell_s=1800,
                 decision_grid_s=1800, outage_grid_s=7200, day_start_hour=6.0,
                 daylight_h=12.0, capacity_wh=0.05, sample_wh=4.7e-4, healthy_wh=0.010,
                 hear_within_s=1800, trace_path=None, tag="A0") -> None:
        super().__init__()
        self.schedule = sorted(schedule, key=lambda x: x[0])
        self.decider = decider
        self.scope = set(scope) if scope else None
        self.dwell_s = dwell_s
        self.grid = decision_grid_s
        self.outage_grid = outage_grid_s
        self.day_start = day_start_hour
        self.daylight = daylight_h
        self.capacity_wh = capacity_wh
        self.sample_wh = sample_wh
        self.healthy_wh = healthy_wh
        self.hear_within_s = hear_within_s
        self.trace_path = trace_path
        self.tag = tag
        self.sparse = self.schedule[0][1]
        self.dense = min(p for _, p, _ in self.schedule)
        self.targets: dict[str, tuple[int, int]] = {}
        self.history: list[dict] = []
        self.sent_ledger: dict[str, dict] = {}     # nid -> 最近下发目标/时刻/世代
        self.confirmed: dict[str, tuple[int, int]] = {}
        self._last_decide_t = -10**9
        self._last_req = self.sparse
        self._last_any_heard = False
        self._first = True
        self.decision_log: list[dict] = []

    def _in_scope(self, nid):
        return self.scope is None or nid in self.scope

    def _observation(self, view: CenterView):
        nodes = []
        any_heard = False
        for nid in view.node_ids:
            snap = view.reports.get(nid) or {}
            heard = view.heard_recently(nid, self.hear_within_s)
            any_heard = any_heard or heard
            soc = view.soc_of(nid)
            nodes.append({
                "id": nid,
                "alive": snap.get("alive") if snap else None,
                "soc_wh": (round(soc, 6) if soc is not None else None),
                "soc_evidence_age_s": view.soc_age_s(nid),
                "aoi_s": view.aoi_s(nid),
                "cur_sample_s": snap.get("sample_interval_s") if snap else None,
                "cur_report_s": snap.get("report_period_s") if snap else None,
                "cache_level": snap.get("cache_level") if snap else None,
                "in_flight": nid in view.in_flight,
                "heard_last_window": heard,
            })
        req = required_period(self.schedule, view.t_s)
        obs = {
            "now_s": view.t_s,
            "clock_hod": round((self.day_start + view.t_s / 3600.0) % 24.0, 2),
            "mission": {
                "required_period_s": req,
                "schedule": [{"start_s": a, "period_s": p, "level": lv}
                             for a, p, lv in self.schedule],
                "seconds_into_current_segment": (
                    view.t_s - max(a for a, _, _ in self.schedule if a <= view.t_s)),
            },
            "link": {"any_node_heard_last_window": any_heard,
                     "n_heard": sum(1 for n in nodes if n["heard_last_window"])},
            "nodes": nodes,
        }
        # 现成普通求解工具建议（与 agent 同信息；A0 也拥有）
        obs["tool_suggestions"] = {
            "dayfeed": dayfeed_targets(obs, self.sparse, self.dense,
                                       self.day_start, self.daylight),
            "sustain": sustain_targets(obs, self.sparse, self.dense, self.healthy_wh),
            "comply": comply_targets(obs, self.sparse, self.dense),
            "ignore": ignore_targets(obs, self.sparse, self.dense),
        }
        return obs, req, any_heard

    def _pending_list(self, view):
        out = []
        for nid, info in self.sent_ledger.items():
            cur = view.reports.get(nid) or {}
            applied = (cur.get("sample_interval_s") == info["target"][0]
                       and cur.get("report_period_s") == info["target"][1])
            if not applied:
                out.append({"node_id": nid, "target": list(info["target"]),
                            "sent_at_s": info["at_s"], "in_flight": nid in view.in_flight,
                            "age_s": view.t_s - info["at_s"]})
        return out

    def plan(self, view: CenterView):
        obs, req, any_heard = self._observation(view)

        # 已确认生效的命令移出未决账（依据真实回执，不读真值）。
        for nid, info in list(self.sent_ledger.items()):
            cur = view.reports.get(nid) or {}
            if (cur.get("sample_interval_s") == info["target"][0]
                    and cur.get("report_period_s") == info["target"][1]):
                self.confirmed[nid] = info["target"]
                self.sent_ledger.pop(nid, None)

        trigger = None
        if self._first:
            trigger = "init"
        elif req != self._last_req:
            trigger = "req_change"
        elif (not self._last_any_heard) and any_heard:
            trigger = "recovery"
        elif view.t_s - self._last_decide_t >= self.grid and any_heard:
            trigger = "grid"
        elif view.t_s - self._last_decide_t >= self.outage_grid and not any_heard:
            trigger = "grid_outage"

        if trigger is not None:
            ctx = {"sparse": self.sparse, "dense": self.dense,
                   "capacity_wh": self.capacity_wh, "sample_wh": self.sample_wh,
                   "history": self.history[-6:],
                   "pending": self._pending_list(view)}
            actions = self.decider.decide(obs, ctx)
            for nid, tgt in actions.items():
                if self._in_scope(nid):
                    self.targets[nid] = (int(tgt[0]), int(tgt[1]))
            rec = {"t_s": view.t_s, "trigger": trigger, "req": req,
                   "any_heard": any_heard, "observation": obs,
                   "actions": {k: list(v) for k, v in actions.items()},
                   "targets_after": {k: list(v) for k, v in self.targets.items()}}
            if isinstance(self.decider, LLMDecider):
                rec.update(decider=self.decider.kind, raw=self.decider._last_raw,
                           api_error=self.decider._last_err, usage=self.decider._last_usage,
                           parse_note=getattr(self.decider, "_parse_note", ""))
            self.decision_log.append(rec)
            if self.trace_path:
                with open(self.trace_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self.history.append({"t_s": view.t_s, "trigger": trigger, "req": req,
                                 "link_ok": any_heard,
                                 "actions": {k: list(v) for k, v in list(actions.items())[:14]},
                                 "note": rec.get("parse_note", "")})
            self._last_decide_t = view.t_s
            self._first = False
        self._last_req = req
        self._last_any_heard = any_heard

        # 按既有节流把目标经真实链路下发（与 MissionChangePolicy 同构）。
        out = []
        for nid in view.node_ids:
            if not self._in_scope(nid) or nid not in self.targets:
                continue
            if nid in view.in_flight:
                self._skip("in_flight", nid); continue
            last_sent = self.sent_ledger.get(nid, {}).get("at_s")
            if last_sent is not None and view.t_s - last_sent < self.dwell_s:
                self._skip("dwell", nid); continue
            ti, tp = self.targets[nid]
            snap = view.reports.get(nid) or {}
            if snap.get("sample_interval_s") == ti and snap.get("report_period_s") == tp:
                self._skip("at_target", nid); continue
            a, b = self.stamp_pair(nid,
                                   {"op": OP_SET_SAMPLING_INTERVAL, "interval_s": ti},
                                   {"op": OP_SET_REPORT_PERIOD, "period_s": tp})
            out.append((nid, a)); out.append((nid, b))
            self.sent_ledger[nid] = {"target": [ti, tp], "at_s": view.t_s,
                                     "generation": a.get("generation")}
            self._last = getattr(self, "_last", {})
            self._last[nid] = view.t_s
        return out
