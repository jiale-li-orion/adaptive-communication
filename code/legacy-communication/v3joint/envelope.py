#!/usr/bin/env python3
"""envelope.py — 义务可行性执行层（deterministic feasibility envelope）。

动机（r38 实证）：给通用 LLM agent 的**文本**证书能大幅减少致命错误，但不保证——v3 证书在
"主路夜间恢复"场景被 LLM 违反（午夜编译 dense、整夜密采，seed1 死 13 节点，而 dayfeed 同种子
0 死亡）。本模块把证书里**仍有合法观测依据**的硬约束从“建议”机制化为对任意 planner
（LLM / comply / dayfeed / MPC）输出动作的普通安全过滤。r42/doc51 后不再用 ACCESS heard 证据
推断 control-plane reachability；unknown 配置与夜间/黄昏能量门分别处理。

只使用 planner 同样合法可见的信号（center-view：节点确认配置 cur_*、中心近窗听到节点数
n_heard、外生要求 req、当天时刻 hod），不读环境真值/未来。规则与 agent_cert.online_cert_block
v4 一一对应，是其确定性对偶：

  E1 夜间能量账：只在**该节点已报告 SoC**且“剩余黑夜 dense 相对 sparse 的额外采样能耗 ×
     safety factor”超过该 SoC 时，才把 dense 作为 ENERGY-INFEASIBLE 硬拒绝。证据不足或余额
     足够时只记 advisory；[16,18) dusk 也只 advisory，不把调度偏好冒充物理不可行。
  E2 ACCESS 不冒充控制面：`n_heard` 只证明中心最近收到过节点状态/接入证据，不能推出
     backhaul/downlink command reachability。白天 heard<n 只记 advisory，不据此回滚合法 target；
     真正的 in-flight/dwell/at-target 节流由命令层处理。配置证据本身 unknown 时仍 fail-closed。
  E3 本层不承担 mission compliance：任务要求 dense/sparse 由 planner 或普通 compliance baseline
     决定；envelope 不因 blue/yellow 标签自行生成任务动作。

EnvelopeDecider.decide 返回**全节点**安全目标 map。未被内层点名的节点优先继承 policy 的 previous
sticky target（由 ctx.current_targets 提供），只有旧调用者没有该上下文时才退化到已确认现状；
随后再施加 unknown-config 与证据充分的 energy-infeasible hard gate。
"""
from __future__ import annotations


def enforce_feasibility_legacy(inner_actions, obs, ctx, dense_day_from=6.0,
                               dense_day_to=16.0, dusk_to=18.0):
    """r39 注册实验使用的历史 clock/ACCESS envelope。

    仅用于复现已经登记的 placement 对照。这里故意保留当时的两条假设：夜间/黄昏一律
    hard sparse，以及 elevated daytime 下 `heard<n` 被当作控制面未确认。后续审计已经指出
    ACCESS receipt 不能推出 control-plane reachability，因此新 Agent 实验不得默认使用本模式。
    """
    sparse = ctx["sparse"]
    dense = ctx["dense"]
    hod = float(obs.get("clock_hod", 12))
    heard = int(obs.get("link", {}).get("n_heard", 0))
    nodes = obs.get("nodes", [])
    n = len(nodes) or 1
    req = obs.get("mission", {}).get("required_period_s", sparse)
    elevated = req <= dense
    dark = hod < dense_day_from or hod >= dusk_to
    dusk = dense_day_to <= hod < dusk_to
    open_dense = dense_day_from <= hod < dense_day_to

    def cur_of(nd):
        return (nd.get("cur_sample_s") or sparse, nd.get("cur_report_s") or sparse)

    tgt = {nd["id"]: cur_of(nd) for nd in nodes}
    for nid, v in (inner_actions or {}).items():
        if nid in tgt and v is not None:
            tgt[nid] = (int(v[0]), int(v[1]))

    log = []
    for nd in nodes:
        nid = nd["id"]
        ci, cp = cur_of(nd)
        ti, tp = tgt[nid]
        wants_dense = (ti == dense or tp == dense)
        if dark:
            if ti != sparse or tp != sparse:
                log.append(("night_gate", nid, (ti, tp)))
            ti = tp = sparse
        elif dusk:
            if wants_dense:
                log.append(("dusk_close", nid, (ti, tp)))
            ti = tp = sparse
        elif elevated and wants_dense and not open_dense:
            ti, tp = ci, cp
        elif elevated and wants_dense and open_dense and heard < n and ci != dense:
            log.append(("control_unconfirmed", nid, heard))
            ti, tp = ci, cp
        tgt[nid] = (int(ti), int(tp))
    return tgt, log


def enforce_feasibility(inner_actions, obs, ctx, dense_day_from=6.0,
                        dense_day_to=16.0, dusk_to=18.0, energy_safety=1.3):
    sparse = ctx["sparse"]
    dense = ctx["dense"]
    hod = float(obs.get("clock_hod", 12))
    heard = int(obs.get("link", {}).get("n_heard", 0))
    nodes = obs.get("nodes", [])
    n = len(nodes) or 1
    req = obs.get("mission", {}).get("required_period_s", sparse)
    elevated = req <= dense
    dark = hod < dense_day_from or hod >= dusk_to
    dusk = dense_day_to <= hod < dusk_to
    open_dense = dense_day_from <= hod < dense_day_to
    sample_wh = float(ctx.get("sample_wh", 4.7e-4))
    zero_dark_harvest = bool(ctx.get("harvest_zero_outside_daylight", False))

    def rem_dark(h):
        if h >= dusk_to:
            return max(0.0, (24.0 - h) + dense_day_from)
        if h < dense_day_from:
            return max(0.0, dense_day_from - h)
        return 0.0

    dark_extra_wh = (rem_dark(hod)
                     * (3600.0 / dense - 3600.0 / sparse)
                     * sample_wh)

    def soc_is_monotone_upper_bound(nd):
        """旧 SoC 是否仍可作为当前 SoC 的保守上界。

        只有显式声明黑夜 harvest=0，且证据时间仍落在**同一段黑夜**内时成立。跨过 daylight 的
        stale low SoC 可能已经被充电抬高，不能用于 hard infeasibility 证明。
        """
        if not dark or not zero_dark_harvest:
            return False
        age = nd.get("soc_evidence_age_s")
        if age is None:
            return False
        try:
            age = max(0.0, float(age))
        except (TypeError, ValueError):
            return False
        elapsed_dark_h = ((24.0 - dusk_to) + hod) if hod < dense_day_from else (hod - dusk_to)
        return age <= max(0.0, elapsed_dark_h) * 3600.0 + 1e-9

    def cur_of(nd):
        s, r = nd.get("cur_sample_s"), nd.get("cur_report_s")
        # None 是“中心尚未确认”，不是 sparse。返回值层仍需 concrete target，因此下面 ordinary
        # envelope 对 unknown 节点一律 fail-closed 到 sparse；但日志必须保留 unknown 语义，
        # 不能把“没有证据”伪装成“已确认 600/600”。
        return (s if s is not None else sparse, r if r is not None else sparse)

    # 省略节点的语义是 KEEP previous target，不是 reset 到当前 confirmed config。
    # previous target 由 AgentMissionPolicy 通过 ctx.current_targets 提供；旧调用者没有该字段时才
    # 退化到 confirmed current。这样 envelope 仍可返回全节点 map，同时不破坏 sticky-target contract。
    previous = ctx.get("current_targets") or {}
    tgt = {}
    for nd in nodes:
        nid = nd["id"]
        pv = previous.get(nid)
        if isinstance(pv, (list, tuple)) and len(pv) >= 2:
            tgt[nid] = (int(pv[0]), int(pv[1]))
        else:
            tgt[nid] = cur_of(nd)
    for nid, v in (inner_actions or {}).items():
        if nid in tgt and v is not None:
            tgt[nid] = (int(v[0]), int(v[1]))

    log = []
    for nd in nodes:
        nid = nd["id"]
        config_unknown = (nd.get("cur_sample_s") is None
                          or nd.get("cur_report_s") is None)
        ci, cp = cur_of(nd)
        ti, tp = tgt[nid]
        wants_dense = (ti == dense or tp == dense)
        if config_unknown:
            # 普通 unknown-safe 行为：没有配置回执时不从 unknown 推断当前档位，也不允许升级。
            # concrete sparse 只是执行层的保守 candidate，不是对节点真实配置的声明。
            if (ti, tp) != (sparse, sparse):
                log.append(("config_unknown", nid, (ti, tp)))
            ti = tp = sparse
        elif dark and wants_dense:
            soc = nd.get("soc_wh")
            proof_ok = soc_is_monotone_upper_bound(nd)
            if (soc is not None and proof_ok and dark_extra_wh > 0
                    and float(soc) < energy_safety * dark_extra_wh):
                log.append(("energy_infeasible", nid, float(soc), dark_extra_wh,
                            nd.get("soc_evidence_age_s")))
                # 这份账只量化 sampling 的额外能耗；没有证据证明 fast report 也不可行。
                # 因此 hard gate 只拒绝 sample densification，保留 planner 的 report target。
                ti = sparse
            else:
                log.append(("night_energy_advisory", nid, soc, dark_extra_wh,
                            nd.get("soc_evidence_age_s"), proof_ok))
        elif dusk:
            if wants_dense:
                log.append(("dusk_advisory", nid, (ti, tp)))
        elif elevated and wants_dense and open_dense and heard < n:
            # n_heard 是 ACCESS receipt，不是 control-plane reachability（r42/doc51 已明确）。
            # 因而不能据 heard<n 把“previous target 仍为 dense、当前只确认了一半字段”回滚成
            # confirmed current；这既破坏 sticky-target/pending 语义，也把接入证据误当控制面证据。
            # ordinary envelope 在这里保持 planner/previous target；真正的 in-flight/dwell/at-target
            # 节流由 AgentMissionPolicy 的命令层处理。
            log.append(("access_partial_advisory", nid, heard))
        tgt[nid] = (int(ti), int(tp))
    return tgt, log


class EnvelopeDecider:
    """包装任意 decider，对其动作施加确定性可行性约束。kind 透传用于 trace。"""

    def __init__(self, inner, tag="A1-env", mode="evidence", **env_kw):
        self.inner = inner
        self.tag = tag
        self.env_kw = env_kw
        if mode not in ("evidence", "legacy_clock"):
            raise ValueError(f"unknown envelope mode: {mode}")
        self.mode = mode
        self.kind = tag + "(" + getattr(inner, "kind", inner.__class__.__name__) + ")"
        self.envelope_log = []
        # 透传 LLM 计量属性
        self.calls = getattr(inner, "calls", 0)
        self.total_tokens = getattr(inner, "total_tokens", 0)

    def decide(self, obs, ctx):
        inner_actions = self.inner.decide(obs, ctx)
        self.calls = getattr(self.inner, "calls", self.calls)
        self.total_tokens = getattr(self.inner, "total_tokens", self.total_tokens)
        fn = enforce_feasibility_legacy if self.mode == "legacy_clock" else enforce_feasibility
        tgt, log = fn(inner_actions, obs, ctx, **self.env_kw)
        self.envelope_log.append({"t_s": obs["now_s"], "hod": obs.get("clock_hod"),
                                  "heard": obs.get("link", {}).get("n_heard"),
                                  "mode": self.mode,
                                  "corrections": log[:20]})
        return tgt
