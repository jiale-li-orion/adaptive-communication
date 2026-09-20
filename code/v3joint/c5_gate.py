# -*- coding: utf-8 -*-
"""c5_gate.py — Task-2 (runtime authorisation) obligation view.

**已在版本控制内**（`code/v3joint/`）：本文件是配置终止线（C5/C9）证据链的一部分，由
`code/v3joint/c5_matrix.py` 使用，结果登记在 `results/c5_matrix.json`。早先的说明写它是未跟踪的
本地文件，那是在 C5 修正重新入库之前。

Why this file exists
--------------------
`code/v3joint/mission_view.py` builds its segments from the *complete* future schedule and
publishes segment ``k`` over ``[start_k, start_{k+1})``. With a three-segment config schedule that
means the gateway, at the moment the upgrade is published (h2), already receives the obligations of
the interval that ends at the future downgrade (h6 or h10) — 48 or 96 dense obligations. The
gateway therefore learns *when the next change is scheduled* before that change is authorised.

The class docstring of `mission_view` states the opposite information model ("中心在会商授权到达后
才获知内容"), so the construction and the stated model disagree. Episode I is unaffected: its last
segment ends at the public task horizon, so extruding to the horizon changes nothing there.

What Task-2 does instead
------------------------
The field keeps the currently authorised regime and *extrapolates it to the task horizon* until the
next update actually traverses the backhaul. When that update arrives, the view for the interval
from its start onward is replaced. The gateway never sees the next segment's real ``end`` early.

Task 1 (announced validity: the upgrade command carries an absolute ``valid_until``) is a different
information condition and keeps the pre-announced schedule; see ``_Dispatch``.

本文件被 `code/v3joint/c5_matrix.py` 导入。`MODE` 显式区分两种信息条件：``task1`` 是预告时刻表
（tracked `mission_view.py` 的逐位行为），``task2`` 是运行时授权下的外推发布。
"""
from __future__ import annotations

import mission_view
from exogenous import piecewise_routine_obligations


class Task2Gate(mission_view.MissionViewGate):
    """Extruded publication: current authorisation runs to the horizon until corrected."""

    def __init__(self, measurands, hours, schedule, window_s=None, grace_s=None,
                 half_open_after_first=True):
        super().__init__(measurands, hours, schedule, window_s=window_s, grace_s=grace_s,
                         half_open_after_first=half_open_after_first)
        self._window_s = window_s
        self._grace_s = grace_s
        # 每段被发布时实际装入的"外推"义务：从该段起点到任务终点，按该段周期生成的同一网格。
        # 网格锚点与 piecewise_routine_obligations 一致（rel = start + j*period），因此在
        # [start, next_start) 内的 oid 与真值完全相同；超出部分才是外推。
        self._extruded: dict[int, list] = {}
        for seg in self.segments:
            start, period = seg["start"], seg["period"]
            gen = piecewise_routine_obligations(
                self.meas, self.hours,
                [(0, self.sparse, "blue"), (start, period, "yellow")],
                window_s=window_s, grace_s=grace_s,
                half_open_after_first=half_open_after_first)
            self._extruded[start] = [o for o in gen if o.release_at >= start]

    def segment_ops(self, seg):
        """Replace the routine view from ``seg['start']`` to the horizon.

        Removal covers (a) the initial sparse belief in that interval and (b) every obligation an
        earlier publication extruded into it. Identity is preserved, so the consumer's
        ``o in lst`` removal actually finds them.
        """
        lo = seg["start"]
        remove = [o for o in self.belief_routine if o.release_at >= lo]
        for prev_start, objs in self._extruded.items():
            if prev_start < lo:
                remove += [o for o in objs if o.release_at >= lo]
        return remove, list(self._extruded[lo])


#: "task1" = pre-announced schedule (tracked behaviour, bit-identical);
#: "task2" = runtime authorisation (extruded publication).
MODE = "task2"


class _Dispatch:
    """Lets joint_run's `MissionViewGate(...)` call resolve per information condition."""

    def __new__(cls, *args, **kwargs):
        target = mission_view.MissionViewGate if MODE == "task1" else Task2Gate
        return target(*args, **kwargs)


def install():
    """Point joint_run's gate name at the dispatcher. Call before run_joint."""
    import joint_run
    joint_run.MissionViewGate = _Dispatch
    return _Dispatch
