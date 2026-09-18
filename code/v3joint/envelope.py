#!/usr/bin/env python3
"""envelope.py — 义务可行性执行层（deterministic feasibility envelope）。

动机（r38 实证）：给通用 LLM agent 的**文本**证书能大幅减少致命错误，但不保证——v3 证书在
"主路夜间恢复"场景被 LLM 违反（午夜编译 dense、整夜密采，seed1 死 13 节点，而 dayfeed 同种子
0 死亡）。本模块把证书里**有确定物理/协议依据**的硬约束从"建议"机制化为对任意 planner
（LLM / comply / dayfeed / MPC）输出动作的**合法过滤**，使"不永久杀死节点、不对不可达链路
下发、不以未确认配置谎报"成为可复现的执行层属性，而非依赖模型自觉。

只使用 planner 同样合法可见的信号（center-view：节点确认配置 cur_*、中心近窗听到节点数
n_heard、外生要求 req、当天时刻 hod），不读环境真值/未来。规则与 agent_cert.online_cert_block
v4 一一对应，是其确定性对偶：

  E1 夜间能量硬门：hod∈[18,24)∪[0,6) 时，所有节点目标钳为 sparse，并对当前 dense 节点显式
     downgrade（压过任务等级与任何"恢复"）；[16,18) 临近夜不新开/不留 dense。
  E2 控制面确认门：白天升级窗 [6,16) 内，若中心近窗未听到全部节点（heard<n，主路未确认恢复
     或仅备份部分送达），未确认 dense 的节点不得升级（命令此刻不可达，发了也不生效）；
     heard==n 才允许编译 dense。已确认 dense 的节点白天保留。
  E3 非升级段（blue）自然 sparse。

EnvelopeDecider.decide 返回**全节点**目标 map（覆盖 policy.targets 的粘性），未被内层点名的
节点默认保持其已确认现状（at_target 节流使其不产生多余命令）。
"""
from __future__ import annotations


def enforce_feasibility(inner_actions, obs, ctx, dense_day_from=6.0,
                        dense_day_to=16.0, dusk_to=18.0):
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

    # 以"已确认现状"为底（保持），再叠加内层动作；缺失节点保持现状。
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
            ti, tp = ci, cp  # 理论不可达（dark/dusk 已处理）
        elif elevated and wants_dense and open_dense and heard < n and ci != dense:
            # E2：回传未对全部节点恢复，且本节点尚未确认 dense —— 升级命令此刻不可达，抑制。
            log.append(("control_unconfirmed", nid, heard))
            ti, tp = ci, cp
        tgt[nid] = (int(ti), int(tp))
    return tgt, log


class EnvelopeDecider:
    """包装任意 decider，对其动作施加确定性可行性约束。kind 透传用于 trace。"""

    def __init__(self, inner, tag="A1-env", **env_kw):
        self.inner = inner
        self.tag = tag
        self.env_kw = env_kw
        self.kind = tag + "(" + getattr(inner, "kind", inner.__class__.__name__) + ")"
        self.envelope_log = []
        # 透传 LLM 计量属性
        self.calls = getattr(inner, "calls", 0)
        self.total_tokens = getattr(inner, "total_tokens", 0)

    def decide(self, obs, ctx):
        inner_actions = self.inner.decide(obs, ctx)
        self.calls = getattr(self.inner, "calls", self.calls)
        self.total_tokens = getattr(self.inner, "total_tokens", self.total_tokens)
        tgt, log = enforce_feasibility(inner_actions, obs, ctx, **self.env_kw)
        self.envelope_log.append({"t_s": obs["now_s"], "hod": obs.get("clock_hod"),
                                  "heard": obs.get("link", {}).get("n_heard"),
                                  "corrections": log[:20]})
        return tgt
