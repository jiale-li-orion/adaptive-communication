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
                # 一次性门限：仅在“要求变密的那一刻”按当时 SoC 决定，之后不随耗电回退（消融用）。
                if req < prev_req:
                    healthy = self.send_when_unknown if soc is None else soc >= self.healthy_wh
                    if not healthy and (nid, req) not in {(r[0], r[1]) for r in self.refusals}:
                        self.refusals.append((nid, req, view.t_s, soc))
                    target_i = target_p = req if healthy else prev_req
                else:
                    target_i = target_p = req        # 降级/持平照走
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
