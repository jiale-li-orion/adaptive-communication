# -*- coding: utf-8 -*-
"""agent_plan_repair.py — V1：把模型的具体提议绑到它仍能影响的义务环节，再决定哪些部分生效。

STATUS (2026-09-21): HISTORICAL PROTOTYPE / CURRENTLY PAUSED.
修正 scorer/runtime deadline equality 后，预注册的跨段 placement/suppression probe 只在 1/4
regime 保留 harmful effect，未通过进入门槛。实现保留用于回归、因果隔离与未来 witness 复用；
当前不得据此继续扩 seed、跨模型或写成 active method contribution。

口径来源：`paper/AGENT_RESEARCH.md` §4、`paper/RESEARCH_PLAN.md` §5 V1。

与已有普通组件的差别是**检查发生在生成之后**：`CertLLMDecider` 在提示里插入由观测算出的
证书文本（生成前），`envelope.enforce_feasibility` 是普通可行性门（夜间能量硬门、未确认升级
抑制）。本模块读模型给出的具体提议，逐个字段判断它还能改变哪段剩余工作，只保留仍有用的部分，
把其余部分带着理由退回修正；它不新造配额、不报警级、不删义务。

三条规则，只用该位置当时拿得到的证据
------------------------------------
`R-a 上游拥塞`：提议把某节点采样加密，而该节点**仍带着未获确认的记录**（`cache_level > 0`）且中心
对该节点的 AoI 已超过任务要求周期——中心手上的证据说明这台节点已经压着没取回的副本、中心对它的
知识也已经落后。此时**只拒绝采样字段**，保留上报字段：更快上报正是把已有副本送出去的手段。

**这条规则能证明什么，必须写清**：`cache_level` 来自节点自报的 `snapshot()`（就是
`len(self.cache)`），它只能证明"该节点当时还持有未确认记录"，**不能**证明"网关已经拿到这条义务的
合格副本、缺口只剩回传段"。要把结论说到后一句，需要网关本地证据（`gateway_copies_in_window`、
`gateway_pending_depth` 一类），而那属于**观测接口扩展**：必须对各臂同等声明、并在执行该检查的
位置可得。当前实现只主张弱命题——"该节点的上游已经在积压，加密会把新增样本压进同一条已经落后的
链路"——并把所用字段原样记进 `decisions`，供评分区分"有证据的拒绝"与"没有证据的拒绝"。

`R-b 加密切忌`（**候选启发式，不是已授权的安全判据**）：提议降采而当前任务段要求加密、且该节点电量
证据在两倍业务周期内、数值高于 8 mWh——把采样恢复到任务要求的档位，交物理结果判断它是否有益。

**8 mWh 没有正向授权依据，必须写清**：它取自 C5 的 `ttl8+lvl8000u`，那里的语义是**停止门**
（SoC 掉到 8 mWh 以下就停密采），不能反推"SoC ≥ 8 mWh ⇒ 现在开启密采安全且有益"；仓库自己的
`sustain_targets` 用的是另一组滞回（`healthy_wh=0.010`、`exit_wh=0.005`）。因此本规则只声称
"**恢复任务要求的加密候选**"，是否有益由匹配物理结果判定；它不得被表述为"保留有益介入"。

`R-c unknown`：证据缺失（`alive`/电量未知）时不新授权、也不整体停机，原样交给普通门。

**组合顺序是硬的：安全门必须在最外层。** V1 只看具体提议、只做局部修复，它**不得重新授权**被普通
安全层拒绝的字段；若把 V1 套在安全门外面，夜间/dusk 被门降成稀疏的档位会被 R-b 重新打开，等于
绕过安全层。因此正确的组合是 `EnvelopeDecider(PlanRepairDecider(inner))`，并由
`gate_not_reopened_regression()` 在每次运行前核对：夜间与 dusk 的最小合法观测下，最终生效档位必须
与安全门的输出逐位一致。

被拒绝或改写的字段连同规则名与所用证据记进 `decisions`；规则名只描述**证据支持的那件事**。
"""
from __future__ import annotations

DENSE = 300
SPARSE = 600
#: 密采电门。与仓库既有 `lvl8000u`（8 mWh）同值，不是新参数。
DENSE_FLOOR_WH = 0.008


def _schedule(obs: dict) -> list[dict]:
    """Agent 已经可见的授权 schedule；这里只排序，不补任何隐藏任务信息。"""
    sched = list((obs.get("mission") or {}).get("schedule") or [])
    return sorted(sched, key=lambda x: int(x.get("start_s", 0)))


def _obligation_oid(node_id: str, release_at: int, period_s: int,
                    schedule_len: int) -> str:
    """复刻公开 routine obligation 身份；不读取 scorer。"""
    if schedule_len <= 1:
        return f"{node_id}:routine:{int(release_at // period_s):05d}"
    return f"{node_id}:routine:t{int(release_at):07d}"


def _sample_matches(taken_at: int | None, lo: int, hi: int,
                    half_open: bool) -> bool:
    if taken_at is None:
        return False
    return (lo <= taken_at < hi) if half_open else (lo <= taken_at <= hi)


def bind_proposal_to_obligations(obs: dict, ctx: dict, node_id: str,
                                 sample_period_s: int,
                                 report_period_s: int) -> dict:
    """把一个持续配置 proposal 绑到下一决策视界内的公开 routine obligations。

    只用 `mission.schedule`、当前时刻、中心已经收到的节点证据和 pending command。
    “中心没看见”只能得到 unknown，不能推出“现场没采/网关没收到”。
    """
    now = int(obs.get("now_s") or 0)
    horizon = max(60, int(ctx.get("decision_horizon_s") or 1800))
    end = now + horizon
    sched = _schedule(obs)
    task_end_raw = (obs.get("mission") or {}).get("task_end_s")
    task_end = None if task_end_raw is None else int(task_end_raw)
    nmap = {n.get("id"): n for n in (obs.get("nodes") or [])}
    nd = nmap.get(node_id) or {}
    aoi = nd.get("aoi_s")
    newest_taken = None if aoi is None else now - int(aoi)
    obligations = []

    for j, seg in enumerate(sched):
        start = int(seg.get("start_s") or 0)
        period = int(seg.get("period_s") or ctx.get("sparse") or SPARSE)
        if j + 1 < len(sched):
            seg_end = int(sched[j + 1].get("start_s"))
        else:
            # 正式 constructor 的最后一段严格截止在 task horizon；旧 observation 没有该字段时，
            # 只保守扫描到当前 action horizon 附近，保持兼容而不声称知道任务终点。
            seg_end = task_end if task_end is not None else end + period
        # deadline = release + 2*period；从仍可能未过 deadline 的旧窗开始扫即可。
        scan_lo = max(start, now - 2 * period)
        k = max(0, (scan_lo - start) // period)
        rel = start + k * period
        half_open = bool(len(sched) >= 2 and j > 0)
        while rel < seg_end and rel <= end:
            win_lo, win_hi = rel, rel + period
            deadline = win_hi + period
            if deadline >= now:
                confirmed = (_sample_matches(newest_taken, win_lo, win_hi, half_open)
                             and now <= deadline)
                obligations.append({
                    "oid": _obligation_oid(node_id, rel, period, len(sched)),
                    "release_at": rel,
                    "window": [win_lo, win_hi],
                    "deadline": deadline,
                    "period_s": period,
                    "status": "center_confirmed" if confirmed else "unknown",
                    "sample_actionable": bool(win_hi > now if half_open else win_hi >= now),
                    "report_actionable": bool(not confirmed and deadline >= now),
                    "future": bool(rel > now),
                })
            rel += period

    sample_obs = [o for o in obligations
                  if o["sample_actionable"] and o["release_at"] <= end]
    report_obs = [o for o in obligations
                  if o["report_actionable"] and o["release_at"] <= end]
    pending = [p for p in (ctx.get("pending") or [])
               if p.get("node_id") == node_id]
    current = [nd.get("cur_sample_s"), nd.get("cur_report_s")]
    proposal = [int(sample_period_s), int(report_period_s)]
    pending_relations = []
    for p in pending:
        tgt = list(p.get("target") or [])
        fields = list(p.get("fields_sent") or [])
        idx = []
        if "set_sampling_interval" in fields:
            idx.append(0)
        if "set_report_period" in fields:
            idx.append(1)
        if not idx and len(tgt) >= 2:
            # 兼容旧 pending schema：没有字段集合时只能按完整 target 判断。
            idx = [0, 1]
        matches = (len(tgt) >= 2 and bool(idx)
                   and all(proposal[i] == tgt[i] for i in idx))
        reverses = (len(tgt) >= 2 and bool(idx)
                    and all(current[i] is not None
                            and proposal[i] == current[i]
                            and tgt[i] != current[i] for i in idx))
        supersedes = (len(tgt) >= 2 and bool(idx)
                      and any(proposal[i] != tgt[i] for i in idx))
        if matches:
            relation = "proposal_matches_pending"
        elif reverses:
            relation = "proposal_reverses_unconfirmed_pending"
        elif supersedes:
            relation = "proposal_supersedes_pending"
        else:
            relation = "pending_relation_unknown"
        pending_relations.append({
            "target": tgt,
            "fields_sent": fields,
            "sent_at_s": p.get("sent_at_s"),
            "age_s": p.get("age_s"),
            "in_flight": p.get("in_flight"),
            "relation": relation,
        })
    return {
        "node_id": node_id,
        "proposal": [int(sample_period_s), int(report_period_s)],
        "now_s": now,
        "decision_horizon_s": horizon,
        "horizon_end_s": end,
        "task_end_s": task_end,
        "sample_obligations": sample_obs,
        "report_obligations": report_obs,
        "sample_unknown_oids": [o["oid"] for o in sample_obs
                                if o["status"] != "center_confirmed"],
        "report_unknown_oids": [o["oid"] for o in report_obs
                                if o["status"] != "center_confirmed"],
        "pending_effects": pending,
        "pending_relations": pending_relations,
        "evidence": {
            "aoi_s": aoi,
            "newest_center_received_sample_taken_at": newest_taken,
            "cache_level": nd.get("cache_level"),
            "heard_last_window": nd.get("heard_last_window"),
            "soc_wh": nd.get("soc_wh"),
            "soc_evidence_age_s": nd.get("soc_evidence_age_s"),
            "cur_sample_s": nd.get("cur_sample_s"),
            "cur_report_s": nd.get("cur_report_s"),
        },
    }


class PlanRepairDecider:
    """包装任意 decider，对其**具体提议**做义务绑定的局部修复。`kind` 透传用于 trace。"""

    def __init__(self, inner, tag="V1-repair", enable_return_gap=True, enable_over_hold=True,
                 dense=DENSE, sparse=SPARSE, floor_wh=DENSE_FLOOR_WH):
        self.inner = inner
        self.tag = tag
        self.enable_return_gap = enable_return_gap
        self.enable_over_hold = enable_over_hold
        self.dense, self.sparse, self.floor_wh = dense, sparse, floor_wh
        self.kind = tag + "(" + getattr(inner, "kind", inner.__class__.__name__) + ")"
        self.decisions: list[dict] = []
        self.calls = getattr(inner, "calls", 0)
        self.total_tokens = getattr(inner, "total_tokens", 0)

    # ---- 证据读取（只读观测，不看未来、不读仿真真值缓存） ----
    @staticmethod
    def _nodes(obs):
        return {n.get("id"): n for n in (obs.get("nodes") or [])}

    def decide(self, obs, ctx):
        proposed = self.inner.decide(obs, ctx) or {}
        self.calls = getattr(self.inner, "calls", self.calls)
        self.total_tokens = getattr(self.inner, "total_tokens", self.total_tokens)
        req = (obs.get("mission") or {}).get("required_period_s")
        nodes = self._nodes(obs)
        out, log, diagnostics = {}, [], []
        for nid, v in proposed.items():
            try:
                sample, report = int(v[0]), int(v[1])
            except (TypeError, IndexError, ValueError):
                continue
            n = nodes.get(nid) or {}
            new_sample, new_report = sample, report
            cache_level = n.get("cache_level")
            aoi = n.get("aoi_s")
            soc = n.get("soc_wh")
            soc_age = n.get("soc_evidence_age_s")
            binding = bind_proposal_to_obligations(obs, ctx, nid, sample, report)
            if (self.enable_return_gap and sample == self.dense
                    and (n.get("cur_sample_s") or self.sparse) != self.dense
                    and cache_level and cache_level > 0
                    and aoi is not None and req and aoi > req):
                unknown = binding["sample_unknown_oids"]
                future_unknown = [o["oid"] for o in binding["sample_obligations"]
                                  if o["future"] and o["status"] != "center_confirmed"]
                # source backlog + stale AoI 不足以撤销一个会持续影响未来窗口的采样配置。
                # 只有一个完整决策视界内受影响的 sampling obligations 都已由中心确认时才允许退采样。
                if binding["sample_obligations"] and not unknown and not future_unknown:
                    new_sample = n.get("cur_sample_s") or self.sparse
                    log.append({"node": nid, "rule": "R-a-upstream-congestion-safe-window",
                                "kept": ["report"], "declined": ["sample"],
                                "binding_oids": [o["oid"] for o in
                                                 binding["sample_obligations"]][:12],
                                "evidence": {"cache_level": cache_level, "aoi_s": aoi,
                                             "required_period_s": req,
                                             "evidence_scope":
                                                 "center-local backlog + AoI; all affected "
                                                 "sampling obligations in decision horizon confirmed",
                                             "proposed": [sample, report],
                                             "applied": [new_sample, new_report]}})
                else:
                    diagnostics.append({
                        "node": nid,
                        "candidate": "R-a-upstream-congestion",
                        "reason_not_repaired":
                            "persistent sampling also affects unknown/future obligations",
                        "unknown_oids": unknown[:12],
                        "pending_relations": binding["pending_relations"],
                        "binding": binding,
                    })
            elif (self.enable_over_hold and sample == self.sparse and req == self.dense
                    and soc is not None and soc >= self.floor_wh
                    and soc_age is not None and soc_age <= 2 * req
                    and binding["sample_unknown_oids"]):
                # 恢复 task-required densification candidate；外层 ordinary envelope 保留最终否决权。
                new_sample = self.dense
                log.append({"node": nid, "rule": "R-b-task-conflict-densify",
                            "kept": ["sample"], "declined": [],
                            "binding_oids": binding["sample_unknown_oids"][:12],
                            "pending_relations": binding["pending_relations"],
                            "evidence": {"soc_wh": soc, "soc_evidence_age_s": soc_age,
                                         "freshness_bound_s": 2 * req,
                                         "required_period_s": req, "floor_wh": self.floor_wh,
                                         "authorization":
                                             "candidate-heuristic; common safety still applies",
                                         "floor_semantics": "heuristic, not a safety theorem",
                                         "proposed": [sample, report],
                                         "applied": [new_sample, new_report]}})
            out[nid] = (new_sample, new_report)
        self.decisions.append({"t_s": obs.get("now_s"), "n_proposed": len(proposed),
                               "n_repaired": len(log), "log": log[:12],
                               "diagnostics": diagnostics[:12]})
        return out


def _min_legal_obs(hod: float, soc: float = 0.02, req: int = 300) -> dict:
    """最小合法观测：够让夜间/dusk 门与 R-b 各自表态。"""
    node = {"id": "n00", "alive": True, "soc_wh": soc, "soc_evidence_age_s": 60.0,
            "aoi_s": 600.0, "cur_sample_s": 600, "cur_report_s": 600, "cache_level": 0,
            "in_flight": False, "heard_last_window": True}
    return {"now_s": int(hod * 3600), "clock_hod": hod,
            "mission": {"required_period_s": req,
                        "schedule": [{"start_s": 0, "period_s": 600, "level": "blue"},
                                     {"start_s": 6 * 3600, "period_s": 300, "level": "yellow"}],
                        "seconds_into_current_segment": 0},
            "link": {"any_node_heard_last_window": True, "n_heard": 1},
            "nodes": [node]}


def gate_not_reopened_regression() -> dict:
    """回归：V1 不得重新授权被普通安全门拒绝的字段。

    本回归不规定 envelope 在每个时段必须 hard-gate 还是 advisory；那由当前 ordinary safety
    证据规则自己决定。这里只比较“同一 proposal 直接过 envelope”与“先做 V1 repair、再过最外层
    envelope”的最终输出：凡 envelope 已经根据合法证据作出的硬修正，V1 都不能在它之后重新打开。
    """
    from envelope import enforce_feasibility
    ctx = {"dense": DENSE, "sparse": SPARSE, "capacity_wh": 0.05, "sample_wh": 4.7e-4}
    cases, bad = [], []
    for hod in (0.5, 5.0, 17.5, 19.0, 23.0, 12.0):
        obs = _min_legal_obs(hod)
        want = {"n00": [DENSE, DENSE]}          # 模型提议加密
        env_out, _ = enforce_feasibility(dict(want), obs, ctx)
        repaired = PlanRepairDecider(_Const(want), tag="reg").decide(obs, ctx)
        gate_outer, _ = enforce_feasibility(dict(repaired), obs, ctx)
        gate_inner = dict(env_out)
        reopened = {k: [list(repaired[k]), list(gate_outer[k])] for k in repaired}
        row = {"clock_hod": hod, "envelope_output": env_out, "v1_output": repaired,
               "gate_outer_final": gate_outer,
               "gate_outer_equals_envelope": gate_outer == env_out,
               "v1_differs_from_envelope": repaired != env_out}
        cases.append(row)
        if not row["gate_outer_equals_envelope"]:
            bad.append(hod)
        del gate_inner, reopened
    return {"cases": cases, "violations": bad,
            "invariant": "V1 位于 ordinary EnvelopeDecider 内层；最终动作不得越过 envelope 的硬修正"}


class _Const:
    """回归用：直接返回固定提议的 decider。"""

    def __init__(self, actions):
        self.actions = actions
        self.kind = "const"

    def decide(self, obs, ctx):
        return {k: tuple(v) for k, v in self.actions.items()}
