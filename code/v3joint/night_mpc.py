#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""night_mpc.py — 合法信息的标称能量前馈滚动规划（doc19/doc33 要求的强反方，零 LLM）。

与 dayfeed/night_budget 同处 center、同合法视图，不读随机云未来/环境真值。区别是不再手设
"黎明缓冲 R"，而是直接积分仿真所用的**标称半正弦日照曲线**（云遮用公开 cloud_p 的期望系数），
滚动判断"现在这一步能否安全地加密(300)"：

  构造一条对当前加密最不利、但仍满足白天义务的未来耗电轨迹做可行性下界：
    当前步密(300) → 其后命令生效延迟 L 内被迫继续密 → 之后夜间一律疏(600，最省电)、
    白天随升级密(300，有充电支撑)；沿 [now, now+horizon] 用标称充电曲线积分 soc，
    若任意时刻 soc >= floor 则当前可密，否则必须疏。
  滚动执行：每 grid 重算，随 soc 消耗"能密则密、逼近预算极限自动转疏"，自然得到前密后疏；
  夜间还要求主路近期可达(heard)——采了发不出(短截止期)的密采无交付意义。

这是 robust-feasible MPC 的一维简化（动作面只有两档持续配置）。它把 r26b 里手设的 R/L 换成
物理积分：黎明爬坡由半正弦曲线决定，命令延迟 L 显式计费。期望云系数 kc 与 L 给敏感性，不调结果。
"""
from __future__ import annotations
import math

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


class NightMpcPolicy(CenterPolicy):
    name = "night-mpc"

    def __init__(self, schedule, scope=None, dwell_s: int = 1800,
                 day_start_hour: float = 6.0, daylight_h: float = 12.0,
                 peak_wh_per_hour: float = 0.03, cloud_p: float = 0.35,
                 cloud_atten: float = 0.25, cloud_mode: str = "mean",
                 sample_wh: float = 4.7e-4, report_wh: float = 2.33e-5,
                 capacity_wh: float = 0.05, cmd_latency_s: int = 1800,
                 grid_s: int = 1800, horizon_h: float = 30.0,
                 floor_samples: float = 2.0, hear_s: int = 1200) -> None:
        super().__init__()
        self.schedule = sorted(schedule, key=lambda x: x[0])
        self.scope = set(scope) if scope else None
        self.dwell_s = dwell_s
        self.day_start = day_start_hour
        self.daylight = daylight_h
        self.peak = peak_wh_per_hour
        if cloud_mode == "sunny":
            self.kc = 1.0
        elif isinstance(cloud_mode, str) and cloud_mode.startswith("kc:"):
            self.kc = float(cloud_mode.split(":", 1)[1])
        else:
            self.kc = (1.0 - cloud_p) + cloud_p * cloud_atten
        self.sample_wh = sample_wh
        self.report_wh = report_wh
        self.capacity = capacity_wh
        self.L = cmd_latency_s
        self.grid = grid_s
        self.horizon_s = int(horizon_h * 3600)
        self.floor = floor_samples * sample_wh
        self.hear_s = hear_s
        self.name = "mission-night-mpc"
        self._last: dict[str, int] = {}
        self._cache: dict[tuple, tuple[int, int]] = {}
        self.refusals: list[tuple[str, int, int, float | None]] = []
        self.trace: list[tuple] = []

    def _in_scope(self, nid):
        return self.scope is None or nid in self.scope

    def _hod(self, t_s):
        return (self.day_start + t_s / 3600.0) % 24.0

    def _is_day(self, t_s):
        hod = self._hod(t_s)
        return self.day_start <= hod < self.day_start + self.daylight

    def _harvest_wh(self, u0_s, dt_s):
        """步 [u0,u0+dt) 的标称期望充电 Wh：步中点太阳高度，半正弦 × 期望云系数。"""
        mid = u0_s + dt_s / 2.0
        hod = (self.day_start + mid / 3600.0) % 24.0
        rel = (hod - self.day_start) % 24.0
        sun = math.sin(math.pi * rel / self.daylight) if rel <= self.daylight else 0.0
        return max(0.0, sun) * self.peak * self.kc * (dt_s / 3600.0)

    def _heard(self, view, nid):
        ra = view.report_at.get(nid)
        return ra is not None and (view.t_s - ra) <= self.hear_s

    def _soc_estimate(self, view, nid):
        """保守当前 soc：用最近报告 soc，按报告时档外推证据年龄期间的耗电（不计充电，偏低估）。"""
        snap = view.reports.get(nid)
        if not snap or snap.get("soc_wh") is None:
            return None
        soc = float(snap["soc_wh"])
        read_at = snap.get("read_at", view.t_s)
        iv = snap.get("sample_interval_s", 600) or 600
        rp = snap.get("report_period_s", 600) or 600
        dt = max(0, view.t_s - read_at)
        soc -= (dt / iv) * self.sample_wh + (dt / rp) * self.report_wh
        return max(0.0, soc)

    def _can_be_dense_now(self, t0, soc0, heard):
        """当前步(升级)取密(300)是否存在不破 floor 的未来计划（未来取最省电合法轨迹作下界）。"""
        dt = self.grid
        req = required_period(self.schedule, t0)
        sparse = self.schedule[0][1]
        soc = soc0
        u = t0
        # 阶段：当前步 + 命令延迟 L 内，若当前决定密则节点被迫继续密（命令未及生效）。
        forced_dense_until = t0 + dt + self.L
        end = t0 + self.horizon_s
        while u < end:
            day = self._is_day(u + dt // 2)
            r = required_period(self.schedule, u)
            upgraded = r < sparse
            if upgraded:
                if day:
                    iv = rp = r                      # 白天：义务要求密，且有充电
                else:
                    # 夜间：强制延迟窗内密（当前决定的后果），其后最省电=疏
                    iv = rp = (req if u < forced_dense_until else sparse)
            else:
                iv = rp = sparse
            n_s = dt / iv
            n_r = dt / rp
            cost = n_s * self.sample_wh + n_r * self.report_wh
            soc += self._harvest_wh(u, dt) - cost
            if soc > self.capacity:
                soc = self.capacity
            if soc < self.floor:
                return False
            u += dt
        return True

    def plan(self, view: CenterView):
        out = []
        t = view.t_s
        req = required_period(self.schedule, t)
        sparse = self.schedule[0][1]
        gi = t // self.grid
        for nid in view.node_ids:
            if not self._in_scope(nid) or nid in view.in_flight:
                continue
            last = self._last.get(nid)
            if last is not None and t - last < self.dwell_s:
                continue
            key = (nid, gi)
            if key in self._cache:
                target_i, target_p = self._cache[key]
            else:
                if req >= sparse:
                    target_i = target_p = sparse
                else:
                    soc = self._soc_estimate(view, nid)
                    heard = self._heard(view, nid)
                    day = self._is_day(t)
                    if soc is None:
                        # 无任何证据：不主动加密（保守），与 send_when_unknown=False 一致
                        target_i = target_p = sparse
                        dense = False
                    elif day:
                        dense = self._can_be_dense_now(t, soc, heard)
                        target_i = target_p = req if dense else sparse
                    else:
                        dense = bool(heard and self._can_be_dense_now(t, soc, heard))
                        target_i = target_p = req if dense else sparse
                        if not dense and (nid, req) not in {(r[0], r[1]) for r in self.refusals}:
                            if soc is not None:
                                self.refusals.append((nid, req, t, soc))
                    self._cache[key] = (target_i, target_p)
                    if t % 1800 < 60:
                        self.trace.append((t, nid, round(soc, 5) if soc is not None else None,
                                           int(day), int(heard), target_i))
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
