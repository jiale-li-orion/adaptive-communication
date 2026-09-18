#!/usr/bin/env python3
"""agent_cert.py — 顺序3 三层臂中的 A1：在 A0-structured 之上再叠加**一项**义务链可行性证书。

严格对称（doc38 §5）：三臂共用同一 AgentMissionPolicy、同一份合法 center-view 观测、同一工具建议、
同一滚动历史、同一动作空间与节流；A0 / A0-structured / A1 的唯一差别是 decider 在 user prompt
末尾看到的信息块。证书不读环境真值/未来/节点缓存，只把三臂共有观测与公开常量编译成段判定。

版本演进（r38，均为有独立物理/协议依据的机制修正，非"调到赢"）：
- v1 仅在 n_heard==0 判中断，被北斗备份**数据面伪恢复**（中断期 heard≈9–14）骗过 1 次。
- v2 改以"命令未确认 applied<n"为锚，又在恢复后形成**自我实现死锁**（从不下发→永不确认）。
- v3 用收据覆盖度三态（heard<n 阻断 / heard==n 编译-验证 / applied==n 生效），破除死锁，但
  seed1 暴露：主路在**夜间 21:30 恢复**时，A1 午夜编译 dense 并让节点以 300 整夜运行 → 死 13 节点；
  dayfeed 强规则同种子 0 死亡（物理可行）。能量段只是"建议"，压不过"恢复→编译"许可。
- v4 **夜间能量硬门最高优先**：入夜（hod≥18 或 <6）后，无论链路是否恢复、任务是否要求 300，
  一律只准 sparse 并对任何已确认 dense 的节点**主动降级**；dense 编译窗限定白天 [06:00,16:00)
  （留 Class A 生效/撤回余量），[16,18) 临近夜不再新开 dense。与 dayfeed 强规则遵守**同一条**
  对称能量墙，区别只是把它从硬编码规则变成给通用 agent 的实时可行性约束。
"""
from __future__ import annotations

from agent_mission import LLMDecider


def online_cert_block(obs, ctx, backup_rate_s: int = 1200, elevated_window_s: int = 600,
                      dense_day_from=6.0, dense_day_to=16.0, dusk_to=18.0):
    """从一份合法 center-view 观测快照生成义务链可行性证书文本（纯函数，无未来真值）。"""
    t = obs["now_s"]
    hod = obs.get("clock_hod", 12)
    nodes = obs.get("nodes", [])
    n = len(nodes) or 1
    heard = int(obs.get("link", {}).get("n_heard", 0))
    dense = ctx.get("dense", 300)
    sparse = ctx.get("sparse", 600)
    cap = ctx.get("capacity_wh", 0.05)
    req = obs.get("mission", {}).get("required_period_s", sparse)

    aois = [x.get("aoi_s") for x in nodes if x.get("aoi_s") is not None]
    max_aoi = max(aois) if aois else None
    applied_dense = sum(1 for x in nodes if (x.get("cur_sample_s") or sparse) == dense)
    inflight = sum(1 for x in nodes if x.get("in_flight"))
    elevated = req <= dense
    data_healthy = heard >= n
    dark = (hod < dense_day_from or hod >= dusk_to)
    dusk = (dense_day_to <= hod < dusk_to)
    can_open_dense = dense_day_from <= hod < dense_day_to
    blocked = elevated and applied_dense < n and not data_healthy
    recover = elevated and applied_dense < n and data_healthy

    L = ["",
         "FEASIBILITY CERTIFICATE (on-site obligation-feasibility projector from YOUR OWN command "
         "ledger, node-confirmed configs, center receipts you actually see, clock, and public "
         "link/device constants; no future truth; advisory, you remain the decision-maker):"]

    # ===== 最高优先：夜间能量硬门（压过任务等级与链路恢复）=====
    if elevated and dark:
        L.append(
            f"- NIGHT ENERGY HARD GATE (hour {hod:.0f}, dark): holding dense {dense}s through the "
            f"remaining dark hours draws more than the {cap:.3f} Wh battery and PERMANENTLY kills "
            "nodes (no restart). This OVERRIDES the elevated mission and ANY backhaul recovery. "
            f"Issue sparse {sparse}s to ALL nodes now, including an explicit DOWNGRADE for the "
            f"{applied_dense} node(s) currently confirming {dense}; do not (re)issue dense until "
            f"{dense_day_from:02.0f}:00. Log elevated-{dense} as energy-infeasible overnight and "
            "request a conferred downgrade; never report it running.")
        if heard < n:
            L.append(
                f"- CONTROL PLANE ALSO NOT DELIVERING: link.n_heard={heard}<{n} (partial/no receipts; "
                "backup is uplink-only and cannot confirm downlinks). Sparse is the last applied safe "
                "config under local autonomy.")
        else:
            L.append(
                f"- Link currently hears {heard}/{n}, but at night that does NOT justify dense: keep "
                "everyone sparse until daylight; compile the elevated requirement after "
                f"{dense_day_from:02.0f}:00.")
        L.append(_geometry(backup_rate_s, elevated_window_s))
        L.append(_lawful_night(sparse, dense_day_from))
        return "\n".join(L)

    # ===== 白天 / 晨昏：控制面三态 =====
    if blocked and heard > 0:
        L.append(
            f"- CONTROL PLANE NOT DELIVERING: period {dense} is required, yet only {applied_dense}/{n} "
            f"nodes CONFIRM it while link.n_heard={heard}<{n}. Those partial receipts are sparse "
            f"BACKUP DATA packets (uplink-only, ~one small shared packet per {backup_rate_s}s) and do "
            "NOT carry/confirm downlink configuration; partial hearing is not a live control channel. "
            "The only evidence control works is a node reporting the new period.")
    elif blocked:
        L.append(
            "- CONTROL PLANE NOT DELIVERING: the CENTER receives nothing from the field "
            f"(link.n_heard={heard}, oldest fresh receipt "
            f"{int(max_aoi) if max_aoi is not None else '?'}s old). Gateway LoRa hearing is not "
            "backhaul delivery. Until a node confirms the new period, treat the backhaul as not "
            "delivering.")
    if blocked:
        L.append(
            f"- COMMAND LEDGER: only {applied_dense}/{n} CONFIRM period={dense} ({inflight} in "
            "flight). Re-emitting dense now cannot be confirmed (Class A downlink crosses "
            "backhaul->gateway->next RX window); a sent-but-unconfirmed command is NOT applied and "
            "must not be re-spammed.")
        if applied_dense == 0:
            L.append(
                f"- MISSION NOT IN EFFECT: no node confirms elevated-{dense}; the field lawfully "
                f"keeps the last APPLIED ({sparse}s) config. Do NOT report elevated monitoring as "
                "running.")
        else:
            L.append(
                f"- PARTIAL: {applied_dense}/{n} confirm {dense}; the rest keep their last applied "
                "config; the unconfirmed part is not in effect.")

    if recover and can_open_dense:
        L.append(
            f"- RETURN LINK RECOVERED (data plane): the center hears ALL {n}/{n} nodes recently, "
            f"consistent with primary recovery. You MAY compile period {dense} ONCE for the "
            f"{n - applied_dense} unconfirmed nodes now (daylight, energy permits). It is IN EFFECT "
            f"only after a node reports cur_sample={dense}; until then do NOT claim it is running and "
            f"do NOT re-issue to in-flight nodes. If it still does not confirm next decision (or "
            f"n_heard falls below {n}), revert to the last applied config and LOG "
            "command-unreachable.")
        if inflight:
            L.append(f"- COMMAND LEDGER: {applied_dense}/{n} confirm, {inflight} in flight; wait "
                     "before re-issuing.")
    elif recover and dusk:
        L.append(
            f"- LINK HEARS ALL {n}/{n}, but dusk is near (hour {hod:.0f}); a dense command opened now "
            "may stay applied into the dark and kill nodes overnight. Do NOT open new dense; keep "
            f"{sparse} and compile {dense} after {dense_day_from:02.0f}:00, and DOWNGRADE any node "
            f"still on {dense} before {dusk_to:02.0f}:00.")
    elif recover and dark:
        # 已在夜间硬门返回，兜底不可达
        pass

    # 白天已全确认、临近夜：安排日落降级
    if elevated and applied_dense == n and dusk:
        L.append(
            f"- DUSK DOWNGRADE: all {n}/{n} confirm {dense}, but schedule sparse {sparse} for every "
            f"node before {dusk_to:02.0f}:00 so dense is never held overnight (battery cannot sustain "
            "it; nodes would die permanently).")

    L.append(_geometry(backup_rate_s, elevated_window_s))
    if blocked:
        L.append(
            "- LAWFUL ACTIONS (DZ/T 0460 §5.3.3 / §8.4.2): (1) actions:[] for commands that cannot "
            "be confirmed now; (2) hold the last lawful APPLIED config / local autonomy; (3) LOG the "
            "obligation-level infeasibility with its segment (no-return-slot / command-unreachable / "
            "energy), never implying success; (4) after the center hears ALL nodes in DAYLIGHT and "
            "commands confirm, compile the guaranteeable subset; request added backup quota or a "
            "conferred downgrade for the rest. Never mark an unmet obligation fulfilled.")
    else:
        L.append(
            "- LAWFUL ACTIONS (DZ/T 0460 §5.3.3 / §8.4.2): in daylight compile only what nodes can "
            f"CONFIRM; downgrade every node to sparse {sparse} before dark; treat node-confirmed "
            "config as the sole proof of effect; keep logging any obligation that cannot be "
            "guaranteed and request added backup quota or a conferred downgrade for it. Never mark "
            "an unmet obligation fulfilled.")
    return "\n".join(L)


def _geometry(backup_rate_s, elevated_window_s):
    return (f"- RETURN GEOMETRY (structural): the short-message backup is one small shared packet "
            f"per {backup_rate_s}s across all nodes; the elevated delivery window "
            f"(~{elevated_window_s}s) is SHORTER than slot spacing, so some elevated windows contain "
            "NO return slot even under optimistic packing. Tightening sampling cannot create a "
            "return slot.")


def _lawful_night(sparse, day_from):
    return ("- LAWFUL NIGHT ACTIONS (DZ/T 0460 §5.3.3 / §8.4.2): keep/issue sparse "
            f"{sparse} everywhere, downgrade any dense node, LOG elevated monitoring as "
            f"energy-infeasible overnight (no false completion), and defer dense compilation to "
            f"{day_from:02.0f}:00 or after a conferred downgrade. Never mark an unmet obligation "
            "fulfilled.")


class CertLLMDecider(LLMDecider):
    """A1：与 A0-structured 相同，仅在 user prompt 决策前追加一块可行性证书。"""

    def __init__(self, model="deepseek-flash", cert_kwargs=None, **kw):
        kw.setdefault("structured_state", True)
        super().__init__(model=model, **kw)
        self.cert_kwargs = dict(cert_kwargs or {})
        self.kind = kw.get("tag", "A1") + "-cert"

    def _prompt(self, obs, ctx):
        sysp, usr = super()._prompt(obs, ctx)
        cert = online_cert_block(obs, ctx, **self.cert_kwargs)
        marker = "\nDecide now. Emit the strict JSON object."
        if marker in usr:
            usr = usr[: usr.rfind(marker)] + cert + "\n" + marker.lstrip("\n")
        else:
            usr = usr + cert
        return sysp, usr
