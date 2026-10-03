#!/usr/bin/env python3
"""mission_policy.py — 外部授权任务变更的中心响应策略（doc35 顺序2）。

授权 feed（预警等级→要求周期）是**外生、对所有臂同等开放**的信息（DZ/T 0460 §8.4.2 经会商
升降级、§5.3.3 可远程调采样/上传频率）。策略不判滑坡风险，只决定如何把当前要求编译成配置命令。

三档（先便宜后强，doc33 §9 顺序2）：
  ignore      保持初始配置，不响应变更（量化“忽略合法升级/降级”的代价）；
  comply      照单全收：对 scope 全节点把采样/上报都设为当前要求周期（固定、不看状态）；
  energy_gate 最便宜强普通规则：升级时仅对回报 SoC 健康的节点加密，其余保持疏档并记一次
              “因能量不可兑现”（降级总是允许，疏档省电）。这是现成 EnergyAware 思想的事件触发版，
              不含跨采集/上行/回传段的失约定位（那是候选 C 的待验增量）。
  sustain     强普通规则 S0：外部要求作为“密档目标”，叠加 center.EnergyAwarePolicy 的**持续**
              滞回能量保护（密态跌破 exit_wh 退回常态、疏态升回 healthy_wh 才再加密、去抖）。
              与 energy_gate 的一次性门限不同，它在加密后电被耗低时会真的退回疏档，避免“升级时
              满电→全加密→夜间集体耗尽”的失实结果。降级总是允许回疏档。
  dayfeed     标称昼夜前馈普通规则（S1 的便宜代理）：用场景公开的标称日照钟点（不含随机云未来
              真值），升级态白天有充电盈余时加密、夜间无充电降回常态保命；对夜间物理不可兑现的
              加密记一次不可兑现。用于先探测“前馈普通规则 + 强选包”还剩多少联合空间。

命令机制与 center.DenseSamplingPolicy 完全一致：stamp_pair 一次决策覆盖两个字段、in_flight 不
重复下单、dwell 重试、按节点回执 sample_interval_s/report_period_s 确认（Class A 生效延迟由此体现）。
"""
from __future__ import annotations

from center import (CenterPolicy, CenterView, OP_SET_REPORT_PERIOD,
                    OP_SET_SAMPLING_INTERVAL)
from admission import ResourceGate, hourly_load


def required_period(schedule, t_s: int) -> int:
    """当前时刻外部授权要求的周期（schedule 按 start 升序）。"""
    req = schedule[0][1]
    for start, period, _lvl in schedule:
        if t_s >= start:
            req = period
        else:
            break
    return req


class MissionChangePolicy(CenterPolicy):
    name = "mission"

    def __init__(self, schedule, mode: str = "comply", scope=None,
                 dwell_s: int = 1800, healthy_wh: float = 0.010,
                 exit_wh: float | None = 0.005, confirm_n: int = 1,
                 day_start_hour: float = 6.0, daylight_h: float = 12.0,
                 send_when_unknown: bool = True) -> None:
        super().__init__()
        self.schedule = sorted(schedule, key=lambda x: x[0])
        self.mode = mode
        self.scope = set(scope) if scope else None
        self.dwell_s = dwell_s
        self.healthy_wh = healthy_wh
        self.exit_wh = exit_wh
        self.confirm_n = max(1, int(confirm_n))
        self.day_start_hour = day_start_hour
        self.daylight_h = daylight_h
        self.send_when_unknown = send_when_unknown
        self.name = f"mission-{mode}"
        self._last: dict[str, int] = {}
        #: 诊断/指标：因能量拒绝加密的（节点, 要求周期, 时刻, 所见SoC）。H1 不可兑现声明的雏形。
        self.refusals: list[tuple[str, int, int, float | None]] = []
        self._last_req: dict[str, int] = {}
        #: energy_gate 的一次性准入结果必须在**同一个 Task revision 整段内持久**。
        #: 第一版只把 `_last_req` 推进到新 req，却没有保存“这次升级被拒后仍应保持的 target”。
        #: 结果是拒绝只生效一个 planner tick：下一 tick 看到 `req == prev_req` 后又把节点改成 dense。
        #: 这里保存该节点当前 Task revision 下真正被准入的 target period；只有 req 再次变化时重判。
        self._energy_gate_target: dict[str, int] = {}
        #: sustain 模式的逐节点滞回状态（策略自身记忆，非环境真值）。
        self._dense_mode: dict[str, bool] = {}
        self._streak: dict[str, tuple[bool, int]] = {}

    def _in_scope(self, nid: str) -> bool:
        return self.scope is None or nid in self.scope

    def plan(self, view: CenterView):
        out = []
        req = required_period(self.schedule, view.t_s)
        sparse = self.schedule[0][1]
        for nid in view.node_ids:
            if not self._in_scope(nid):
                continue
            if nid in view.in_flight:
                self._skip("in_flight", nid)
                continue
            last = self._last.get(nid)
            if last is not None and view.t_s - last < self.dwell_s:
                self._skip("dwell", nid)
                continue
            snap = view.reports.get(nid) or {}
            prev_req = self._last_req.get(nid, sparse)
            soc = view.soc_of(nid)
            want_dense = None          # None 表示不按能量门限（ignore/comply）

            if self.mode == "ignore":
                target_i = target_p = sparse
            elif self.mode == "comply":
                target_i = target_p = req
            elif self.mode == "energy_gate":
                # 一次性门限：仅在**Task requirement revision** 时按当时 SoC 决定，
                # 然后把准入结果持久到下一次 requirement revision。拒绝升级意味着继续跑
                # 上一档已准入 target，而不是“只拒绝这一分钟、下一分钟又照单全收”。
                previous_target = self._energy_gate_target.get(nid, prev_req)
                if req != prev_req:
                    if req < prev_req:
                        healthy = self.send_when_unknown if soc is None else soc >= self.healthy_wh
                        if not healthy and (nid, req) not in {(r[0], r[1]) for r in self.refusals}:
                            self.refusals.append((nid, req, view.t_s, soc))
                        target = req if healthy else previous_target
                    else:
                        # 降级总是放行，主动回到新的较疏 Task target。
                        target = req
                    self._energy_gate_target[nid] = target
                else:
                    target = self._energy_gate_target.get(nid, req)
                target_i = target_p = target
            elif self.mode == "sustain":
                # 持续滞回能量门限（S0 强普通规则）：升级态下随回报 SoC 在密档 req 与常态 sparse
                # 之间粘滞切换，电被耗低会真的退回疏档，电恢复再加密。
                if req >= sparse:
                    want_dense = False
                elif soc is None:
                    want_dense = self.send_when_unknown
                else:
                    was = self._dense_mode.get(nid, soc >= self.healthy_wh)
                    raw = (soc >= self.exit_wh) if (self.exit_wh is not None and was) \
                        else (soc >= self.healthy_wh)
                    side, n = self._streak.get(nid, (raw, 0))
                    n = n + 1 if side == raw else 1
                    self._streak[nid] = (raw, n)
                    want_dense = was if n < self.confirm_n else raw
                    self._dense_mode[nid] = want_dense
                target_i = target_p = req if want_dense else sparse
                if not want_dense and req < sparse and \
                        (nid, req) not in {(r[0], r[1]) for r in self.refusals}:
                    self.refusals.append((nid, req, view.t_s, soc))
            elif self.mode == "dayfeed":
                # 标称昼夜前馈：升级态仅在标称日照窗加密，夜间降回常态保命（不读随机云未来真值）。
                if req >= sparse:
                    td = False
                else:
                    hod = (self.day_start_hour + view.t_s / 3600.0) % 24.0
                    td = self.day_start_hour <= hod < self.day_start_hour + self.daylight_h
                target_i = target_p = req if td else sparse
                if not td and req < sparse and \
                        (nid, req) not in {(r[0], r[1]) for r in self.refusals}:
                    self.refusals.append((nid, req, view.t_s, None))
            else:
                raise ValueError(f"unknown mission mode {self.mode!r}")

            self._last_req[nid] = req
            if (snap.get("sample_interval_s") == target_i
                    and snap.get("report_period_s") == target_p):
                self._skip("at_target", nid)
                continue
            self._last[nid] = view.t_s
            a, b = self.stamp_pair(nid,
                                   {"op": OP_SET_SAMPLING_INTERVAL, "interval_s": target_i},
                                   {"op": OP_SET_REPORT_PERIOD, "period_s": target_p})
            out.append((nid, a))
            out.append((nid, b))
        return out


class NotifiedMissionPolicy(MissionChangePolicy):
    """Gateway policy that can use only Task revisions actually delivered by MissionViewGate."""

    def __init__(self, mission_gate, mode: str = "comply", scope=None,
                 preparation_lead_s: int = 0, record_trace: bool = False,
                 preparation_resource_guard: bool = False,
                 preparation_sample_wh: float | None = None,
                 preparation_capacity_wh: float | None = None,
                 preparation_correction_s: int | None = None,
                 preparation_reserve_wh: float = 0.0,
                 **kwargs) -> None:
        self.mission_gate = mission_gate
        self.preparation_lead_s = max(0, int(preparation_lead_s))
        self.record_trace = bool(record_trace)
        self.decision_trace: list[dict] = []
        self.preparation_resource_guard = bool(preparation_resource_guard)
        if self.preparation_resource_guard and mode != "comply":
            raise ValueError("preparation_resource_guard currently isolates comply-mode preparation only")
        self._prep_gate = None
        if self.preparation_resource_guard:
            if preparation_sample_wh is None or preparation_capacity_wh is None:
                raise ValueError("resource-guarded preparation requires sample_wh and capacity_wh")
            self._prep_gate = ResourceGate(
                sample_wh=float(preparation_sample_wh),
                capacity_wh=float(preparation_capacity_wh),
                correction_s=preparation_correction_s,
                reserve_wh=float(preparation_reserve_wh),
            )
        self._prep_sample_wh = None if preparation_sample_wh is None else float(preparation_sample_wh)
        self._prep_denied: dict[str, int] = {}
        self._prep_denied_reasons: dict[str, int] = {}
        super().__init__([mission_gate.schedule[0]], mode=mode, scope=scope, **kwargs)
        self.name = f"mission-notified-{mode}"

    def _trace_view(self, view: CenterView, visible) -> None:
        if not self.record_trace or view.t_s % 3600 != 0:
            return
        nodes = [nid for nid in view.node_ids if self._in_scope(nid)]
        soc = [view.soc_of(nid) for nid in nodes]
        soc_known = [float(x) for x in soc if x is not None]
        ages = [view.soc_age_s(nid) for nid in nodes]
        ages_known = [int(x) for x in ages if x is not None]
        aois = [view.aoi_s(nid) for nid in nodes]
        aois_known = [int(x) for x in aois if x is not None]
        self.decision_trace.append({
            "t_s": int(view.t_s),
            "visible_schedule": [list(x) for x in visible],
            "report_count": sum(1 for nid in nodes if nid in view.reports),
            "in_flight_count": sum(1 for nid in nodes if nid in view.in_flight),
            "soc_known": len(soc_known),
            "soc_mean": (sum(soc_known) / len(soc_known)) if soc_known else None,
            "soc_min": min(soc_known) if soc_known else None,
            "soc_max": max(soc_known) if soc_known else None,
            "soc_age_mean": (sum(ages_known) / len(ages_known)) if ages_known else None,
            "soc_age_max": max(ages_known) if ages_known else None,
            "aoi_mean": (sum(aois_known) / len(aois_known)) if aois_known else None,
            "aoi_max": max(aois_known) if aois_known else None,
            "gateway_last_forward_age_s": (
                None if view.gateway_last_forward_ok_at is None
                else int(view.t_s - view.gateway_last_forward_ok_at)),
            "gateway_pending_depth": view.gateway_pending_depth,
            "gateway_oldest_pending_age_s": view.gateway_oldest_pending_age_s,
            "nodes": {
                nid: {
                    "soc_wh": view.soc_of(nid),
                    "soc_age_s": view.soc_age_s(nid),
                    "aoi_s": view.aoi_s(nid),
                    "in_flight": nid in view.in_flight,
                    "sample_interval_s": (view.reports.get(nid) or {}).get("sample_interval_s"),
                    "report_period_s": (view.reports.get(nid) or {}).get("report_period_s"),
                    "cache_level": (view.reports.get(nid) or {}).get("cache_level"),
                }
                for nid in nodes
            },
        })

    def plan(self, view: CenterView):
        # No direct read of future gate.segments: visible_schedule is the information boundary.
        visible = self.mission_gate.visible_schedule()
        self._trace_view(view, visible)
        # A delegated future Task must not make the gateway re-enforce the current deployment
        # profile before there is something useful to prepare/execute.  This keeps "Task intent
        # arrived early" separate from "start dense monitoring early" and avoids shifting the
        # ordinary dwell/retry clock merely because the contract was delivered.
        densification_starts = []
        prev = int(visible[0][1])
        for start, period, _level in visible[1:]:
            start, period = int(start), int(period)
            if period < prev:
                densification_starts.append(max(0, start - self.preparation_lead_s))
            prev = period
        if densification_starts and view.t_s < min(densification_starts):
            return []
        if len(visible) == 1:
            return []
        if self.preparation_lead_s <= 0:
            self.schedule = visible
            return super().plan(view)

        # A received future densification may be staged earlier to buy Class-A
        # installation opportunities.  Sparse/recovery revisions are never
        # pulled earlier because that would under-serve the still-active task.
        staged = [visible[0]]
        prev_period = int(visible[0][1])
        for start, period, level in visible[1:]:
            start, period = int(start), int(period)
            if period < prev_period:
                staged.append((max(0, start - self.preparation_lead_s), period,
                               f"prepare:{level}"))
            staged.append((start, period, level))
            prev_period = period
        self.schedule = sorted(staged, key=lambda x: x[0])
        actual_req = required_period(visible, view.t_s)
        staged_req = required_period(self.schedule, view.t_s)
        early_preparation = staged_req < actual_req
        if not early_preparation or self._prep_gate is None:
            return super().plan(view)

        # Resource admission applies only to the *extra early* action.  Snapshot
        # state first so a rejected preparation does not advance MissionChangePolicy
        # dwell/generation state and therefore cannot suppress the authoritative
        # command when the real Task becomes effective.
        before = {
            nid: {
                "last": self._last.get(nid),
                "last_req": self._last_req.get(nid),
                "target": self.target.get(nid),
                "generation": self.generation.get(nid),
            }
            for nid in view.node_ids
        }
        proposals = super().plan(view)
        by_node: dict[str, list[tuple[str, dict]]] = {}
        for nid, payload in proposals:
            by_node.setdefault(nid, []).append((nid, payload))
        out = []
        for nid, rows in by_node.items():
            snap = view.reports.get(nid) or {}
            cur = (
                int(snap.get("sample_interval_s") or self.mission_gate.schedule[0][1]),
                int(snap.get("report_period_s") or self.mission_gate.schedule[0][1]),
            )
            pair = list(cur)
            for _nn, payload in rows:
                if payload.get("op") == OP_SET_SAMPLING_INTERVAL:
                    pair[0] = int(payload["interval_s"])
                elif payload.get("op") == OP_SET_REPORT_PERIOD:
                    pair[1] = int(payload["period_s"])
            soc = view.soc_of(nid)
            age = view.soc_age_s(nid)
            if soc is None or age is None or self._prep_sample_wh is None:
                ok, why = False, "no_evidence"
            else:
                soc_lo = float(soc) - hourly_load(*cur, self._prep_sample_wh) * (float(age) / 3600.0)
                # Protect until the next *visible* relaxation.  If no recovery
                # Task has reached the gateway yet, conservatively protect to the
                # Task horizon rather than reading an unseen future revision.
                end_s = int(self.mission_gate.H)
                for start, period, _level in visible:
                    if int(start) > view.t_s and int(period) > staged_req:
                        end_s = int(start)
                        break
                ok, why = self._prep_gate.check(soc_lo, tuple(pair), max(0, end_s - view.t_s))
            if ok:
                out.extend(rows)
                continue
            self._prep_denied[nid] = self._prep_denied.get(nid, 0) + 1
            self._prep_denied_reasons[why] = self._prep_denied_reasons.get(why, 0) + 1
            old = before[nid]
            for mapping, key in ((self._last, "last"), (self._last_req, "last_req"),
                                 (self.target, "target"), (self.generation, "generation")):
                if old[key] is None:
                    mapping.pop(nid, None)
                else:
                    mapping[nid] = old[key]
        return out

    def preparation_gate_report(self) -> dict | None:
        if self._prep_gate is None:
            return None
        return {
            "denied_nodes": len(self._prep_denied),
            "denied_total": sum(self._prep_denied.values()),
            "denied_reasons": dict(self._prep_denied_reasons),
            "gate": self._prep_gate.report(),
        }


class DelegatedCenterFallbackPolicy(MissionChangePolicy):
    """Center-side ordinary fallback for a gateway-delegated Task revision.

    The center keeps its full authorized Task schedule.  It suppresses only the *currently active*
    non-initial revision after the runtime has positive evidence that the gateway received that
    revision.  Thus delegation is an additive safety composition, not an owner replacement.
    """

    def __init__(self, mission_gate, schedule, mode: str = "comply", scope=None, **kwargs) -> None:
        self.mission_gate = mission_gate
        super().__init__(schedule, mode=mode, scope=scope, **kwargs)
        self.name = f"mission-center-fallback-{mode}"

    def plan(self, view: CenterView):
        if self.mission_gate.revision_received_for_time(view.t_s):
            return []
        return super().plan(view)
