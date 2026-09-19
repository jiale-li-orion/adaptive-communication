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




def _geometry_conditional(backup_rate_s, elevated_window_s):
    return ("- RETURN GEOMETRY (conditional): the short-message backup offers one small shared packet "
            f"per {backup_rate_s}s; an elevated window (~{elevated_window_s}s) shorter than slot "
            "spacing may contain NO backup slot. IF AND ONLY IF the primary is unavailable across such "
            "a window is its elevated delivery structurally unreturnable; geometry alone does not "
            "establish an outage, and tightening sampling cannot create a slot.")


def online_cert_block_v5(obs, ctx, backup_rate_s=1200, elevated_window_s=600,
                         dense_day_from=6.0, dense_day_to=16.0, dusk_to=18.0, energy_safety=1.3):
    """v5 (doc51 R3 / doc52 sec 2.1,2.3): unknown-aware feasibility projector.

    Keeps three statement classes separate:
      CONFIRMED    - a node report shows cur_sample==target (the only proof of effect);
      UNCONFIRMED  - command in flight / receipts incomplete; implies neither effect nor unreachability;
      UNREACHABLE  - allowed ONLY from an explicit network-side CURRENT state
                     (obs.link.primary_backhaul_state == "down"); LoRa access receipts (n_heard) can
                     never by themselves establish backhaul/control-plane state, so when that field is
                     absent the projector emits UNCONFIRMED.
    Night energy is a computed ledger, not a blanket "dense kills" claim. Geometry is conditional on
    actual backhaul state. Pure function of the observation snapshot and public constants; no future.
    """
    hod = obs.get("clock_hod", 12)
    nodes = obs.get("nodes", [])
    n = len(nodes) or 1
    link = obs.get("link", {})
    heard = int(link.get("n_heard", 0))
    cp = link.get("primary_backhaul_state")          # "up" / "down" / None(unknown)
    dense = ctx.get("dense", 300)
    sparse = ctx.get("sparse", 600)
    sample_wh = ctx.get("sample_wh", 4.7e-4)
    req = obs.get("mission", {}).get("required_period_s", sparse)
    applied_dense = sum(1 for x in nodes if (x.get("cur_sample_s") or sparse) == dense)
    inflight = sum(1 for x in nodes if x.get("in_flight"))
    elevated = req <= dense
    dark = (hod < dense_day_from or hod >= dusk_to)
    dusk = (dense_day_to <= hod < dusk_to)

    def rem_dark(h):
        if h >= dusk_to:
            return max(0.0, (24 - h) + dense_day_from)
        if h < dense_day_from:
            return max(0.0, dense_day_from - h)
        return 0.0

    def extra_wh(h):
        return rem_dark(h) * (3600.0 / dense - 3600.0 / sparse) * sample_wh

    known_soc = [(x.get("id"), x.get("soc_wh")) for x in nodes if x.get("soc_wh") is not None]
    L = ["",
         "FEASIBILITY CERTIFICATE v5 (unknown-aware; from YOUR command ledger, node-confirmed configs, "
         "center receipts you actually see, clock, public constants; no future truth; advisory). Keep "
         "three statement classes distinct: CONFIRMED (a node reports cur_sample=target; the only proof "
         "of effect), UNCONFIRMED (in flight / incomplete receipts; neither effective nor unreachable), "
         "UNREACHABLE (only if a network-side field says the backhaul is CURRENTLY down). LoRa hearing "
         "n_heard is the ACCESS link and can NEVER by itself establish backhaul/control-plane state."]

    if not elevated:
        L.append(f"- Mission currently requires only the sparse {sparse}s baseline; nodes confirming it "
                 "need no change; keep any elevated target unissued until its segment is active.")
        return "\n".join(L)

    e_add = extra_wh(hod)

    if dark:
                        # ---- night energy ledger, highest precedence ----
        poor = [(i, s) for i, s in known_soc if s < energy_safety * e_add] if (e_add > 0 and known_soc) else []
        if poor:
            ids = ", ".join(i for i, _ in poor[:6])
            extra_draws = (3600.0 / dense - 3600.0 / sparse) * rem_dark(hod)
            L.append(
                f"- ENERGY-INFEASIBLE TO OPEN/HOLD dense {dense}s until {dense_day_from:02.0f}:00 (computed "
                f"ledger): ~{rem_dark(hod):.1f} dark hours remain; dense-vs-sparse adds {e_add:.4f} Wh/node "
                f"(~{extra_draws:.0f} extra draws at {sample_wh:.1e} Wh), exceeding the safety-adjusted "
                f"reported SoC of {len(poor)} node(s) ({ids}); with no overnight harvest they reach "
                f"permanent cutoff. Issue sparse {sparse}s to ALL, explicitly DOWNGRADE any node confirming "
                f"{dense}s, defer dense to {dense_day_from:02.0f}:00; log elevated-{dense} energy-infeasible, "
                "never report it running.")
        else:
            basis = "is unavailable" if not known_soc else "covers the computed extra"
            L.append(
                f"- NIGHT ENERGY ADVISORY (not an infeasibility certificate): ~{rem_dark(hod):.1f} dark "
                f"hours remain; dense-vs-sparse extra is {e_add:.4f} Wh/node and reported SoC {basis}; "
                f"opening/holding dense is NOT proven to kill nodes. A conservative controller may keep "
                f"sparse {sparse}s overnight for margin, but do not claim dense is physically impossible.")
        if cp == "down":
            L.append("- CONTROL PLANE: command UNREACHABLE now (network-side reports primary backhaul "
                     "CURRENTLY down; duration not predicted). Sparse is the last applied safe config.")
        elif cp == "up":
            L.append("- CONTROL PLANE: network-side reports primary CURRENTLY up; the night energy ledger "
                     "still governs whether dense may run.")
        else:
            L.append(f"- CONTROL PLANE: command delivery UNCONFIRMED (n_heard={heard}/{n} is LoRa ACCESS "
                     "only; it does NOT prove the backhaul is down). Do not assert unreachable; act on the "
                     "energy ledger via whatever is locally applied and re-evaluate in daylight.")
        L.append(_geometry_conditional(backup_rate_s, elevated_window_s))
        return "\n".join(L)

                        # ---- daylight / dusk ----
    if applied_dense < n:
        if cp == "down":
            L.append("- CONTROL PLANE: command UNREACHABLE now (network-side reports primary CURRENTLY "
                     "down; duration not predicted). Hold the last APPLIED config; a sent-but-unconfirmed "
                     "command is not applied; log command-unreachable for the unconfirmed subset and do "
                     "not re-spam.")
        elif cp == "up":
            L.append(f"- CONTROL PLANE: network-side reports primary CURRENTLY up; {applied_dense}/{n} "
                     f"confirm {dense}s. You MAY compile {dense}s ONCE for the {n-applied_dense} unconfirmed "
                     f"node(s) in daylight; it is CONFIRMED only after a node reports cur_sample={dense}s; "
                     f"do not re-issue to the {inflight} in-flight node(s).")
        else:
            L.append(f"- CONTROL PLANE: command delivery UNCONFIRMED ({applied_dense}/{n} confirm {dense}s, "
                     f"n_heard={heard}/{n}). Partial LoRa receipts neither confirm effect nor prove backhaul "
                     "failure; with no network-side backhaul state you MUST NOT assert 'not delivering'. In "
                     "daylight you may issue the target ONCE for unconfirmed nodes, then keep it UNCONFIRMED "
                     f"until a node reports cur_sample={dense}s; never claim it is running and do not re-spam "
                     "in-flight nodes.")
        if applied_dense == 0:
            L.append(f"- MISSION NOT CONFIRMED IN EFFECT: no node confirms elevated-{dense}s; the field "
                     f"lawfully keeps its last APPLIED ({sparse}s) config. Do not report elevated monitoring "
                     "as running.")
        else:
            L.append(f"- PARTIAL: {applied_dense}/{n} confirm {dense}s; the unconfirmed part is not in "
                     "effect (UNCONFIRMED, not unreachable).")
    else:
        L.append(f"- All {n}/{n} nodes CONFIRM {dense}s (node reports); the elevated config is in effect.")
    if dusk:
        L.append(f"- DUSK POLICY ADVICE (Class A apply/withdraw lead time): opening new dense near hour "
                 f"{hod:.0f} may leave it applied into dark; prefer sparse {sparse}s and downgrade any "
                 f"{dense}s node before {dusk_to:02.0f}:00. This is scheduling advice, not an infeasibility "
                 "proof.")
    L.append(_geometry_conditional(backup_rate_s, elevated_window_s))
    L.append("- LAWFUL ACTIONS (DZ/T 0460 §5.3.3/§8.4.2): emit only what node reports confirm; mark unmet "
             "obligations UNCONFIRMED with the segment (no-return-slot / command-unconfirmed / "
             "energy-infeasible) rather than asserting success or unreachability without evidence; request "
             "added backup quota or a conferred downgrade for what cannot be guaranteed. Never mark an unmet "
             "obligation fulfilled.")
    return "\n".join(L)


class CertLLMDecider(LLMDecider):
    """A1：A0-structured + 决策前一块可行性证书。version="v4" 逐位复现 r38；"v5" 为 unknown-aware。"""

    def __init__(self, model="deepseek-flash", cert_kwargs=None, version="v4", **kw):
        kw.setdefault("structured_state", True)
        super().__init__(model=model, **kw)
        self.cert_kwargs = dict(cert_kwargs or {})
        self.version = version
        self._cert_fn = online_cert_block_v5 if version == "v5" else online_cert_block
        self.kind = kw.get("tag", "A1") + "-cert" + ("-v5" if version == "v5" else "")

    def _prompt(self, obs, ctx):
        sysp, usr = super()._prompt(obs, ctx)
        cert = self._cert_fn(obs, ctx, **self.cert_kwargs)
        marker = "\nDecide now. Emit the strict JSON object."
        if marker in usr:
            usr = usr[: usr.rfind(marker)] + cert + "\n" + marker.lstrip("\n")
        else:
            usr = usr + cert
        return sysp, usr
