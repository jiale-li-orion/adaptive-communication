#!/usr/bin/env python3
"""mission_view.py — 在线授权任务变更下，**现场网关义务视图的非预知发布门**（doc38 §3）。

修复的信息边界问题（doc38 函数级见证）：
  旧装配把完整未来 ``mission_schedule`` 生成的义务表在 t=0 就交给网关选包器
  （``JointControlPlane.adopt(obligations=全集)``），于是网关在从未收到任务更新的情况下，
  就按变更后的密义务/deadline 选包（同一样本最紧 deadline 22800→22650，无任何接收事件）。

两种合法实例（doc38 §3）：
  * **预告/预装**：完整 schedule 事先下发网关，属公开配置，网关可一直按全集执行
    （``MissionViewGate=None``，旧行为，bit-identical）。
  * **运行中新增授权**（本模块，doc35 在线叙事采用）：中心在会商授权到达后才获知内容，
    网关只在**任务表更新真正穿过主回传到达后**才更新本地义务视图。独立 scorer 仍持完整
    真值（分母不从授权时刻后移）；执行器不可直接查真值。

发布机制（不新增即时信道、登记为最小协议扩展）：
  任务表更新只携带 schedule 段 ``(start, period, level)`` 几个整数，由中心自段生效时刻起
  持续重发，**与中心→网关命令/数据共用同一条主回传、同一个 ``path_available(hour,0)``**，
  在中断窗（``backhaul_gate`` 为假）不可达，首个主回传可用小时到达网关。它不抢数据空口、
  不经过备用腿（备用腿是现场→中心的反向短报文），因此不赋予任何方法额外的即时任务同步。

现场初始视图：首段节奏（sparse）**外推全程**的例行义务（现场以为任务一直如此）＋全部
非例行（事件/规则）义务（本就由现场可观测触发）。每收到一段更新，机械地把该段时间区间
``[start,end)`` 内的旧信念例行义务替换为真值例行义务；已过期的新义务也装入（供积压样本
按真值归类），但其 deadline 已过、不会被 maxcov 当作可挽救的新覆盖。
"""
from __future__ import annotations

from exogenous import (KIND_ROUTINE, piecewise_routine_obligations,
                       routine_obligations_by_node)


class MissionViewGate:
    """随主回传可达性增量发布的现场义务视图。只持有任务表与公开段信息，不含环境真值。"""

    def __init__(self, measurands: dict[str, str], hours: int,
                 schedule: list[tuple[int, int, str]],
                 window_s: int | None = None, grace_s: int | None = None,
                 half_open_after_first: bool = True):
        self.schedule = sorted(schedule, key=lambda x: x[0])
        assert self.schedule[0][0] == 0, "首段必须从 t=0 开始"
        self.meas = dict(measurands)
        self.hours = int(hours)
        self.H = int(hours) * 3600
        self.sparse = self.schedule[0][1]
        self.half_open_after_first = bool(half_open_after_first)

        # 真值例行义务（scorer 分母同源的分段表；变更后段用半开独立观测语义）与现场初始信念
        #（首段节奏全程外推，沿用旧任务闭区间窗口覆盖）。
        self.truth_routine = piecewise_routine_obligations(
            self.meas, hours, self.schedule, window_s=window_s, grace_s=grace_s,
            half_open_after_first=self.half_open_after_first)
        self.belief_routine = routine_obligations_by_node(
            self.meas, hours, period_s=self.sparse,
            window_s=window_s, grace_s=grace_s)

        starts = [s for s, _p, _l in self.schedule]
        bounds = starts[1:] + [self.H]
        # 仅 k>=1 的段需要"到达后发布"；首段在初始视图里。
        self.segments: list[dict] = []
        for (start, period, level), end in zip(self.schedule[1:], bounds[1:]):
            self.segments.append({"start": start, "end": end, "period": period,
                                  "level": level, "notified": False, "gw_at": None})
        self._plane = None  # 由 JointControlPlane.adopt 回填

    # ---- 现场在收到任何任务更新前的合法视图 ----
    def initial_view(self, all_obligations):
        view = list(self.belief_routine)
        view += [o for o in all_obligations if o.kind != KIND_ROUTINE]
        return view

    def segment_ops(self, seg: dict):
        """发布该段：移除区间内旧信念例行义务，加入同区间真值例行义务。"""
        lo, hi = seg["start"], seg["end"]
        remove = [o for o in self.belief_routine if lo <= o.release_at < hi]
        add = [o for o in self.truth_routine if lo <= o.release_at < hi]
        return remove, add

    # ---- 每 tick 由网关调用：把已生效且主回传此刻可达的段发布到现场 ----
    def poll(self, t_s: int, path_available):
        due = []
        hour = t_s // 3600
        for seg in self.segments:
            if seg["notified"] or t_s < seg["start"]:
                continue
            if path_available(hour):
                seg["notified"] = True
                seg["gw_at"] = t_s
                due.append(seg)
        return due

    def timing(self) -> list[dict]:
        """四时间戳中的 issued(=center_received) 与 gateway_received；node_applied 由配置侧记。"""
        return [{"level": s["level"], "period_s": s["period"],
                 "issued_at": s["start"], "gateway_received_at": s["gw_at"]}
                for s in self.segments]
