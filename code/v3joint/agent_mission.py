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
    """持续滞回能量保护的单拍近似。

    已确认处于 dense 的节点用 exit 门决定是否继续保持；已确认 sparse / 配置未知的节点只有达到
    healthy 门才允许重新进入 dense。它没有完整策略的跨拍 streak 状态，因此只是同信息的普通建议。
    """
    req = obs["mission"]["required_period_s"]
    out = {}
    for n in obs["nodes"]:
        if req >= sparse:
            p = sparse
        else:
            soc = n.get("soc_wh")
            cur_i, cur_p = n.get("cur_sample_s"), n.get("cur_report_s")
            was_dense = (cur_i == dense or cur_p == dense)
            threshold = exit_wh if was_dense else healthy_wh
            p = req if (soc is not None and soc >= threshold) else sparse
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
        self.calls = 0              # decisions (one per decide() call)
        self.requests = 0           # actual HTTP requests (>= decisions when retries occur)
        self.total_tokens = 0

    def _prompt(self, obs, ctx):
        sysp = SYSTEM_PROMPT.format(sample_wh=ctx["sample_wh"], capacity_wh=ctx["capacity_wh"],
                                    sparse=ctx["sparse"], dense=ctx["dense"], legal=list(LEGAL_PERIODS))
        lines = ["CURRENT LEGAL OBSERVATION (center view; no future truth):",
                 json.dumps(obs, ensure_ascii=False, indent=None)]
        if ctx.get("current_targets"):
            lines.append(
                "\nCURRENT STICKY TARGETS (policy intent, NOT confirmed node state; "
                "omitted nodes KEEP these):")
            lines.append(json.dumps(ctx["current_targets"], ensure_ascii=False))
        if ctx.get("history"):
            lines.append("\nRECENT DECISION HISTORY (oldest->newest):")
            lines.append(json.dumps(ctx["history"], ensure_ascii=False))
        if self.structured_state and ctx.get("pending"):
            lines.append("\nPENDING/UNRESOLVED COMMANDS (center ledger: accepted by the control plane "
                         "but not yet confirmed by a node report. in_flight=null means delivery stage "
                         "is UNKNOWN at the center, not false. Do not infer queued/dropped/applied from "
                         "absence of confirmation; re-issue only under the ordinary retry/backoff policy):")
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
        attempts_log = []
        for attempt, cfg in enumerate(configs):
            self.requests += 1
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
                    err = None            # success on this attempt clears the first attempt's error
                    attempts_log.append({"attempt": attempt, "ok": True, "finish": finish,
                                         "total_tokens": usage.get("total_tokens"),
                                         "completion_tokens": usage.get("completion_tokens")})
                    break
                err = f"empty content finish={finish}"
                attempts_log.append({"attempt": attempt, "ok": False, "finish": finish, "error": err})
            except Exception as e:  # noqa: BLE001
                err = f"{type(e).__name__}: {e}"
                attempts_log.append({"attempt": attempt, "ok": False, "error": err})
                time.sleep(2 + 3 * attempt)
        self.calls += 1
        self.total_tokens += int(usage.get("total_tokens", 0))
        actions, parse_note = self._parse(raw, obs, ctx)
        self._last_actions = dict(actions)
        if raw is not None and parse_note == "unparseable->hold" and finish == "length":
            parse_note = "truncated->hold"   # max_tokens cut the JSON mid-string, not a chosen hold
        self._last_raw = raw
        self._last_err = err
        self._last_usage = usage
        self._parse_note = parse_note
        self._last_requests = len(attempts_log)
        self._last_attempts = attempts_log
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
            # HOLD 的契约是“保持 policy 已有 target”，不是把 target 改写成当前已确认配置。
            # AgentMissionPolicy 只更新 actions 中显式出现的节点，因此空 dict 才是真正的 hold。
            return {}, "llm_failed->hold"
        try:
            obj = json.loads(raw)
        except Exception:
            s = raw[raw.find("{"): raw.rfind("}") + 1]
            try:
                obj = json.loads(s)
            except Exception:
                return {}, "unparseable->hold"
        # SYSTEM_PROMPT 明确约定：省略节点 KEEP previous target。
        # 因此这里只返回模型显式列出的节点；不能先用 current confirmed config 填满全表，
        # 否则会把尚未确认的 previous target 隐式撤销。
        out = {}
        clamped = 0
        ids = {n["id"] for n in obs["nodes"]}
        for a in obj.get("actions", []):
            nid = a.get("node_id")
            if nid not in ids:
                continue
            # 显式节点内若某字段非法/缺失，也不能静默撤销该字段尚未确认的 previous target。
            # wrapper ctx 已携带 policy sticky targets；旧调用者没有它时才退回当前已确认值。
            prev = (ctx.get("current_targets") or {}).get(nid)
            if isinstance(prev, (list, tuple)) and len(prev) >= 2:
                fb_s, fb_p = int(prev[0]), int(prev[1])
            else:
                fb_s, fb_p = cur[nid]
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
                 hear_within_s=1800, trace_path=None, tag="A0",
                 task_end_s: int | None = None,
                 minimal_field_commands: bool = False,
                 use_physical_inflight: bool = True,
                 target_scoped_dwell: bool = False) -> None:
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
        # 公开任务定义的一部分，不是未来环境真值。用于 proposal 后置检查在 tail observation
        # 中停止制造已经不存在的新 routine obligations；None 保持旧 harness 行为/兼容旧轨迹。
        self.task_end_s = None if task_end_s is None else int(task_end_s)
        # False 保留 r38 及历史实验“任一字段不一致就 stamp_pair 两字段”的旧执行语义；
        # 新 Agent baseline 应显式开启 True，只发送 confirmed current 与 target 真正不同的字段。
        # 这是 ordinary execution hygiene，不是 Candidate A 能力。
        self.minimal_field_commands = bool(minimal_field_commands)
        # True 仅保留 r38/旧实验复现：CenterView.in_flight 直接读取 gateway queue，是已知的信息特权。
        # 新 Agent baseline 应显式 False，只用中心自己“已发送但未从节点回执确认”的 sent_ledger。
        self.use_physical_inflight = bool(use_physical_inflight)
        # False 保持 r38 历史语义：任意最近 attempt 都触发 dwell；新 baseline 显式 True，
        # 只把 dwell 当“同 target retry backoff”，避免旧 target 冻结后来的新 generation。
        self.target_scoped_dwell = bool(target_scoped_dwell)
        self.sparse = self.schedule[0][1]
        self.dense = min(p for _, p, _ in self.schedule)
        self.targets: dict[str, tuple[int, int]] = {}
        self.history: list[dict] = []
        # generated/attempted 与真正被 control plane 接受是两件事。旧实现一在 plan() 生成命令就写
        # sent_ledger，导致 backhaul refusal 也被提示给 Agent 为“已发送未确认”。
        self.attempt_ledger: dict[str, dict] = {}  # nid -> 最近生成意图；只用于 dwell/backoff
        self.sent_ledger: dict[str, dict] = {}     # nid -> _send_command 成功接受的最近目标/时刻/世代
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
            attempt = self.attempt_ledger.get(nid) or {}
            last_attempt = None
            if attempt:
                accepted = list(attempt.get("accepted_fields") or [])
                refused = list(attempt.get("refused_fields") or [])
                attempted = list(attempt.get("fields") or [])
                if accepted and refused:
                    status = "partial_accept"
                elif refused and not accepted:
                    status = "refused_by_control_plane"
                elif accepted:
                    status = "accepted_by_control_plane"
                else:
                    status = "generated_not_submitted_yet"
                last_attempt = {
                    "target": list(attempt.get("target") or []),
                    "at_s": attempt.get("at_s"),
                    "age_s": (None if attempt.get("at_s") is None
                              else view.t_s - int(attempt["at_s"])),
                    "generation": attempt.get("generation"),
                    "fields_attempted": attempted,
                    "fields_accepted": accepted,
                    "fields_refused": refused,
                    "status": status,
                }
            nodes.append({
                "id": nid,
                "alive": snap.get("alive") if snap else None,
                "soc_wh": (round(soc, 6) if soc is not None else None),
                "soc_evidence_age_s": view.soc_age_s(nid),
                "aoi_s": view.aoi_s(nid),
                "cur_sample_s": snap.get("sample_interval_s") if snap else None,
                "cur_report_s": snap.get("report_period_s") if snap else None,
                "cache_level": snap.get("cache_level") if snap else None,
                # 旧 harness 直接读 gateway queue；新 baseline 禁止这个信息特权。中心只知道
                # “我发过、但还没从节点状态回执确认”，不能区分仍在飞 / 已丢 / 已应用但回执未回。
                "in_flight": ((nid in view.in_flight) if self.use_physical_inflight else None),
                "in_flight_source": ("gateway_queue_legacy" if self.use_physical_inflight
                                     else "unavailable_at_center"),
                "pending_unconfirmed": nid in self.sent_ledger,
                # 中心自己刚才调用 control-plane send 得到的返回值属于合法 tool result；
                # 它不是 gateway queue 真值，也不是 APPLIED 回执。A0/A0s/A1 都应同等可见。
                "last_command_attempt": last_attempt,
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
                "task_end_s": self.task_end_s,
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

    @staticmethod
    def _sent_fields_applied(cur: dict, info: dict) -> bool:
        """只核对真正已被 control plane 接受的字段。

        minimal-field / partial-accept 下，target 仍保存完整 policy target，但未发送字段不能参与
        pending 完成判定。旧 trace/旧调用者没有 fields 时退化到两字段都检查。
        """
        target = list(info.get("target") or [])
        if len(target) < 2:
            return False
        fields = list(info.get("fields") or
                      [OP_SET_SAMPLING_INTERVAL, OP_SET_REPORT_PERIOD])
        checks = []
        if OP_SET_SAMPLING_INTERVAL in fields:
            checks.append(cur.get("sample_interval_s") == target[0])
        if OP_SET_REPORT_PERIOD in fields:
            checks.append(cur.get("report_period_s") == target[1])
        return bool(checks) and all(checks)

    def _pending_list(self, view):
        out = []
        for nid, info in self.sent_ledger.items():
            cur = view.reports.get(nid) or {}
            applied = self._sent_fields_applied(cur, info)
            if not applied:
                out.append({"node_id": nid, "target": list(info["target"]),
                            "sent_at_s": info["at_s"],
                            "in_flight": ((nid in view.in_flight)
                                          if self.use_physical_inflight else None),
                            "in_flight_source": ("gateway_queue_legacy" if self.use_physical_inflight
                                                 else "unavailable_at_center"),
                            "pending_unconfirmed": True,
                            "age_s": view.t_s - info["at_s"],
                            "fields_sent": list(info.get("fields") or [])})
        return out

    def note_command_sent(self, node_id: str, payload: dict) -> None:
        """只在 control plane 真正接受命令后把 intent 晋级为 sent/pending。

        Instance._send_command() 仅在 center_send/gateway_send 成功时调用本回调；因此这里才是
        “已发送、等待节点确认”的合法边界。节点真正 APPLIED 仍只能由后续 report 确认。
        """
        info = self.attempt_ledger.get(node_id) or {}
        target = info.get("target")
        if target is None:
            target = list(self.targets.get(node_id, ()))
        if len(target) < 2:
            return
        gen = payload.get("generation")
        op = payload.get("op")
        if info:
            accepted = info.setdefault("accepted_fields", [])
            if op is not None and op not in accepted:
                accepted.append(op)
        prev = self.sent_ledger.get(node_id)
        fields = []
        if prev is not None and prev.get("generation") == gen:
            fields.extend(prev.get("fields") or [])
        if op is not None and op not in fields:
            fields.append(op)
        self.sent_ledger[node_id] = {
            "target": list(target),
            "at_s": int(info.get("at_s", getattr(self, "_skip_t", 0))),
            "generation": gen,
            "fields": fields,
        }

    def note_command_refused(self, node_id: str, payload: dict) -> None:
        """记录 center_send/gateway_send 的**提交拒绝**；不把它伪装成 pending。"""
        info = self.attempt_ledger.get(node_id)
        if not info:
            return
        op = payload.get("op")
        refused = info.setdefault("refused_fields", [])
        if op is not None and op not in refused:
            refused.append(op)

    def plan(self, view: CenterView):
        # 已确认生效的命令移出未决账（依据真实回执，不读真值）。
        for nid, info in list(self.sent_ledger.items()):
            cur = view.reports.get(nid) or {}
            if self._sent_fields_applied(cur, info):
                self.confirmed[nid] = (
                    cur.get("sample_interval_s"), cur.get("report_period_s"))
                self.sent_ledger.pop(nid, None)
                # 旧实现的 dwell 依赖 sent_ledger：一旦目标确认，sent entry 被清掉，后续新目标可立即
                # 进入。拆出 attempt_ledger 后必须保留这一行为；仅清与刚确认目标相同的旧 attempt，
                # 若期间已经生成了更新 target，则不能误删新的 backoff 状态。
                attempt = self.attempt_ledger.get(nid)
                full_target_confirmed = (
                    cur.get("sample_interval_s") == info["target"][0]
                    and cur.get("report_period_s") == info["target"][1])
                if (attempt is not None and full_target_confirmed
                        and list(attempt.get("target") or []) == list(info["target"])):
                    self.attempt_ledger.pop(nid, None)

        # 先根据合法节点回执收口 pending，再构造本拍 observation；新 baseline 因而只看到
        # center-side unconfirmed ledger，不读取 gateway queue 的即时空/非空状态。
        obs, req, any_heard = self._observation(view)

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
            # 给 proposal 后置检查一个**真实的动作持续视界**：在链路可见时最迟下一 grid
            # 会再次决策；完全听不到节点时使用 outage_grid。它不是未来真值，只是本策略自己的
            # 再决策上界。repair 层据此判断一个持久配置会影响哪些近期义务，避免只看“当前窗”
            # 就撤掉会继续影响后续窗口的配置。
            decision_horizon_s = self.grid if any_heard else self.outage_grid
            ctx = {"sparse": self.sparse, "dense": self.dense,
                   "capacity_wh": self.capacity_wh, "sample_wh": self.sample_wh,
                   # 当前 Agent 场景的公开采能模型：日照窗 [day_start, day_start+daylight)，
                   # 窗外合成 solar harvest 为 0。envelope 只有在 SoC 证据落在同一段无采能
                   # 黑夜内时，才可把 stale low SoC 当作当前 SoC 的保守上界。
                   "harvest_zero_outside_daylight": True,
                   "day_start_hour": self.day_start,
                   "daylight_h": self.daylight,
                   "history": self.history[-6:],
                   "pending": self._pending_list(view),
                   # wrapper 需要知道“省略节点时应继续维持什么 target”。只给当前 confirmed
                   # config 会重演 parser omission bug：未确认 previous target 会被静默撤销。
                   "current_targets": {k: list(v) for k, v in self.targets.items()},
                   "decision_horizon_s": decision_horizon_s}
            targets_before = {k: list(v) for k, v in self.targets.items()}
            actions = self.decider.decide(obs, ctx)
            for nid, tgt in actions.items():
                if self._in_scope(nid):
                    self.targets[nid] = (int(tgt[0]), int(tgt[1]))
            rec = {"t_s": view.t_s, "trigger": trigger, "req": req,
                   "any_heard": any_heard, "observation": obs,
                   # 这两项是真正进入 decider 的执行上下文。旧 r38 没落它们，因此旧轨迹无法
                   # 事后精确审计 pending-effect；新轨迹必须保留，避免再从 targets_after 猜。
                   "decision_horizon_s": decision_horizon_s,
                   "pending": list(ctx["pending"]),
                   "targets_before": targets_before,
                   # actions 是最终 decider/interface 输出。裸 LLM/repair 通常是 explicit delta，
                   # outer envelope 为施加安全约束会返回全节点 target map；因此不能再把这个字段
                   # 解释成“模型显式提议”。模型 proposal 独立记在 model_actions。
                   "actions": {k: list(v) for k, v in actions.items()},
                   "action_semantics": "interface output after wrappers; may be delta or full target map",
                   "targets_after": {k: list(v) for k, v in self.targets.items()}}
            # wrapper 后的真正 closed-loop 也必须保留 inner LLM 的原始提议/请求账。
            llm = self.decider
            seen = set()
            while not isinstance(llm, LLMDecider) and hasattr(llm, "inner") and id(llm) not in seen:
                seen.add(id(llm)); llm = llm.inner
            if isinstance(llm, LLMDecider):
                _pn = getattr(llm, "_parse_note", "")
                rec.update(decider=getattr(self.decider, "kind", self.decider.__class__.__name__),
                           llm_decider=llm.kind, raw=llm._last_raw,
                           model_actions={k: list(v) for k, v in getattr(llm, "_last_actions", {}).items()},
                           model_action_semantics="explicit model delta; omitted node keeps previous target",
                           api_error=llm._last_err, usage=llm._last_usage,
                           parse_note=_pn,
                           api_requests=getattr(llm, "_last_requests", 1),
                           attempts=getattr(llm, "_last_attempts", []),
                           parse_hold=(_pn or "").endswith("->hold"))
            self.decision_log.append(rec)
            if self.trace_path:
                with open(self.trace_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            hist = {
                "t_s": view.t_s, "trigger": trigger, "req": req, "link_ok": any_heard,
                "interface_actions": {k: list(v) for k, v in list(actions.items())[:14]},
                "targets_after": {k: list(v) for k, v in list(self.targets.items())[:14]},
                "note": rec.get("parse_note", ""),
            }
            if rec.get("model_actions") is not None:
                hist["model_actions"] = {
                    k: list(v) for k, v in list(rec["model_actions"].items())[:14]
                }
            self.history.append(hist)
            self._last_decide_t = view.t_s
            self._first = False
        self._last_req = req
        self._last_any_heard = any_heard

        # 按既有节流把目标经真实链路下发（与 MissionChangePolicy 同构）。
        out = []
        for nid in view.node_ids:
            if not self._in_scope(nid) or nid not in self.targets:
                continue
            if self.use_physical_inflight and nid in view.in_flight:
                self._skip("in_flight", nid); continue
            attempt = self.attempt_ledger.get(nid, {})
            last_attempt = attempt.get("at_s")
            # dwell 是“同一个 target 的重试退避”，不能把后来的新 target / 新 generation
            # 一起冻结。否则 req_change / safety correction 在旧 attempt 后 30 min 内会被无条件卡住。
            same_attempt_target = list(attempt.get("target") or []) == [*self.targets[nid]]
            dwell_applies = (same_attempt_target if self.target_scoped_dwell else True)
            if (dwell_applies and last_attempt is not None
                    and view.t_s - last_attempt < self.dwell_s):
                self._skip("dwell", nid); continue
            ti, tp = self.targets[nid]
            snap = view.reports.get(nid) or {}
            if snap.get("sample_interval_s") == ti and snap.get("report_period_s") == tp:
                self._skip("at_target", nid); continue
            if self.minimal_field_commands:
                payloads = []
                if snap.get("sample_interval_s") != ti:
                    payloads.append({"op": OP_SET_SAMPLING_INTERVAL, "interval_s": ti})
                if snap.get("report_period_s") != tp:
                    payloads.append({"op": OP_SET_REPORT_PERIOD, "period_s": tp})
                if len(payloads) == 1:
                    out.append((nid, self.stamp(nid, **payloads[0])))
                elif len(payloads) == 2:
                    a, b = self.stamp_pair(nid, payloads[0], payloads[1])
                    out.append((nid, a)); out.append((nid, b))
            else:
                a, b = self.stamp_pair(nid,
                                       {"op": OP_SET_SAMPLING_INTERVAL, "interval_s": ti},
                                       {"op": OP_SET_REPORT_PERIOD, "period_s": tp})
                out.append((nid, a)); out.append((nid, b))
            generated = [payload for nn, payload in out if nn == nid]
            self.attempt_ledger[nid] = {
                "target": [ti, tp], "at_s": view.t_s,
                "generation": generated[-1].get("generation") if generated else None,
                "fields": [x.get("op") for x in generated],
                "accepted_fields": [], "refused_fields": [],
            }
            self._last = getattr(self, "_last", {})
            self._last[nid] = view.t_s
        return out
