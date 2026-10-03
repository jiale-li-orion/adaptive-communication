#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""night_budget.py — 零-LLM、合法信息的"夜间能量预算前馈"任务配置强规则（候选 C 的强反方）。

与 dayfeed 同信息（标称昼夜 + 当前 SoC + center 合法视图 + 外生公开 schedule），不读随机云未来、
不读环境真值；只把 dayfeed 的"夜一律疏"替换为一个**显式能量可行**的夜间加密判据。它是 doc19
"延迟感知滚动规划"在能量维的确定性、保守实现，用来回答：在 .05Wh 电池 / 两档持续配置 / Class A
生效延迟 / 采样欠压即死 / 短截止期下，夜间加密到底还有没有 dayfeed 没拿到的可改变损失。

夜间升级段、主路近期可达(center 收讫年龄<=hear_s)时，判"现在保持 300"是否能量可行。可行性必须
计入两段 dayfeed 没显式算、但 r26 朴素版实测致死的成本：
  L 命令生效延迟  现在下令切疏，最坏 L 秒后才在 Class A 窗口落地，期间节点被迫继续密采；
  R 黎明爬坡缓冲  日出瞬间太阳能≈0，要约 R 秒充电才盈余，而白天本就 300，这段密采须预先留电。
最小保命耗电轨迹（现在密一个延迟窗 L → 其后到日出疏 → 日出后 R 密）：
  E_min = [ L/req + (T_dawn-L)/sparse + R/req ] * sample_wh + floor
仅当 soc >= E_min 才现在密；否则疏，并在本夜锁存（前密后疏一次切换，不依赖命令及时回切）。
所有量为公开器件/标称天文量；保守地把黎明 R 内充电计为 0（不赌日出曲线）。
"""
from __future__ import annotations

from center import (CenterPolicy, CenterView, OP_SET_REPORT_PERIOD,
                    OP_SET_SAMPLING_INTERVAL)


def required_period(schedule, t_s: int) -> int:
    req = schedule[0][1]
    for start, period, _lvl in sorted(schedule, key=lambda x: x[0]):
        if t_s >= start:
            req = period
        else:
            break
    return req


class NightBudgetPolicy(CenterPolicy):
    name = "night-budget"

    def __init__(self, schedule, scope=None, dwell_s: int = 1800,
                 day_start_hour: float = 6.0, daylight_h: float = 12.0,
                 sample_wh: float = 4.7e-4, reserve_samples: float = 2.0,
                 hear_s: int = 1200, cmd_latency_s: int = 3600,
                 dawn_ramp_s: int = 7200) -> None:
        super().__init__()
        self.schedule = sorted(schedule, key=lambda x: x[0])
        self.scope = set(scope) if scope else None
        self.dwell_s = dwell_s
        self.day_start = day_start_hour
        self.day_end = day_start_hour + daylight_h
        self.sample_wh = sample_wh
        self.floor = reserve_samples * sample_wh
        self.hear_s = hear_s
        self.cmd_latency_s = cmd_latency_s
        self.dawn_ramp_s = dawn_ramp_s
        self.name = "mission-night-budget"
        self._last: dict[str, int] = {}
        self._relaxed_night: dict[str, int] = {}
        self.refusals: list[tuple[str, int, int, float | None]] = []
        self.last_reason: dict[str, str] = {}
        # 诊断：每次决策的 (t,nid,soc,T_dawn,E_min,can_dense,heard)
        self.budget_trace: list[tuple] = []

    def _in_scope(self, nid: str) -> bool:
        return self.scope is None or nid in self.scope

    def _hod(self, t_s: int) -> float:
        return (self.day_start + t_s / 3600.0) % 24.0

    def _is_day(self, hod: float) -> bool:
        return self.day_start <= hod < self.day_end

    def _seconds_to_dawn(self, hod: float) -> float:
        if hod < self.day_start:
            return (self.day_start - hod) * 3600.0
        if hod >= self.day_end:
            return (24.0 - hod + self.day_start) * 3600.0
        return 0.0

    def _night_id(self, t_s: int) -> int:
        h = self.day_start + t_s / 3600.0
        return int((h - self.day_end) // 24) + 1

    def _heard(self, view: CenterView, nid: str) -> bool:
        ra = view.report_at.get(nid)
        return ra is not None and (view.t_s - ra) <= self.hear_s

    def plan(self, view: CenterView):
        out = []
        t = view.t_s
        req = required_period(self.schedule, t)
        sparse = self.schedule[0][1]
        hod = self._hod(t)
        day = self._is_day(hod)
        for nid in view.node_ids:
            if not self._in_scope(nid) or nid in view.in_flight:
                continue
            last = self._last.get(nid)
            if last is not None and t - last < self.dwell_s:
                continue

            if req >= sparse:
                target_i = target_p = sparse
                reason = "no_upgrade"
            elif day:
                target_i = target_p = req
                reason = "day_dense"
            else:
                nid_night = self._night_id(t)
                soc = view.soc_of(nid)
                heard = self._heard(view, nid)
                T = self._seconds_to_dawn(hod)
                L = min(self.cmd_latency_s, T)
                n_commit = L / req
                n_tail = max(0.0, T - L) / sparse
                n_dawn = self.dawn_ramp_s / req
                E_min = (n_commit + n_tail + n_dawn) * self.sample_wh + self.floor
                relaxed = self._relaxed_night.get(nid) == nid_night
                can_dense = bool(heard and soc is not None and not relaxed
                                 and soc >= E_min)
                if heard and soc is not None and not can_dense and not relaxed:
                    self._relaxed_night[nid] = nid_night
                    relaxed = True
                    if (nid, req) not in {(r[0], r[1]) for r in self.refusals}:
                        self.refusals.append((nid, req, t, soc))
                if t % 1800 < 60:
                    self.budget_trace.append((t, nid, round(soc, 5) if soc is not None else None,
                                              round(T / 3600, 2), round(E_min, 5),
                                              can_dense, heard, relaxed))
                if can_dense:
                    target_i = target_p = req
                    reason = f"night_dense(T={T/3600:.1f},E={E_min:.4f})"
                else:
                    target_i = target_p = sparse
                    reason = ("night_no_link" if not heard
                              else "night_relaxed" if relaxed
                              else "night_budget_low")
            self.last_reason[nid] = reason

            snap = view.reports.get(nid) or {}
            if (snap.get("sample_interval_s") == target_i
                    and snap.get("report_period_s") == target_p):
                continue
            self._last[nid] = t
            a, b = self.stamp_pair(nid,
                                   {"op": OP_SET_SAMPLING_INTERVAL, "interval_s": target_i},
                                   {"op": OP_SET_REPORT_PERIOD, "period_s": target_p})
            out.append((nid, a))
            out.append((nid, b))
        return out
