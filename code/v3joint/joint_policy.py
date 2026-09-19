#!/usr/bin/env python3
"""joint_policy.py — C-up v2：可交付机会感知的**采样+上报**联合控制（网关位置，规则版，非 LLM）。
本模块引用的 `docs/…` 路径为作者本地过程文档，不随仓库发布。

结构洞见（docs/s7-method/v1.2/11）：接入与回传分离、回传间歇时，**中心位置**只能看到端到端 AoI，
回传一断 AoI 就虚高，最强本地反馈 ea_aoi 据此密采快报——但数据发不出去，密采的电照耗、冗余还挤占
稀缺备用窗，能量越紧越先死。**网关位置**在接入网仍通时看得到真实积压，知道"数据不缺、只是发不
出去"，反馈应基于**可交付性**而非端到端 AoI：

  * 主路可用：常态（稀疏采样、适中上报），等价最省的强固定臂；
  * 主路断、网关本义务窗口已有副本在等备用：采样保持稀疏、上报放松（不重复密采、不灌冗余）；
  * 主路断、网关无本窗口副本且义务临近"下令→Class A 生效→采/报→赶备用窗"前置期：临时密采快报；
  * 电量低于健康线：无论如何稀疏保命（与 ea_aoi 的 SoC 底线同口径）。

稳定性：决策限频（每 decision_epoch_s 一次）＋快档迟滞（进入/退出用不同阈值），避免备用窗相位
逐拍锯齿导致档位震荡、控制信令爆炸。动作面 = {采样间隔, 上报周期}，与 ea_aoi 完全相同。
`use_backup_window=False` 为消融：只看 (SoC, 义务 slack)，去掉主路/副本/备用窗等下游信息。
"""
from __future__ import annotations
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_CODE = os.path.dirname(_HERE)
for p in [_HERE] + [os.path.join(_CODE, d) for d in ("monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from center import (CenterPolicy, OP_SET_REPORT_PERIOD,           # noqa: E402
                    OP_SET_SAMPLING_INTERVAL)


class GatewayObserver:
    """窄接口：只暴露 C-up 合法使用的网关本地量。plane 由 runner 绑定。"""

    def __init__(self, backup_rate_s: int = 120, enable_backup: bool = True):
        self.plane = None
        self.backup_rate_s = backup_rate_s
        self.enable_backup = enable_backup

    def primary_up(self, t_s: int) -> bool:
        if self.plane is None:
            return True
        return bool(self.plane.backhaul_available(int(t_s // 3600)))

    def next_backup_in_s(self, t_s: int) -> int:
        if not self.enable_backup:
            return 0
        return (self.backup_rate_s - (t_s % self.backup_rate_s)) % self.backup_rate_s


class DeliveryOpportunisticPolicy(CenterPolicy):
    name = "cup"

    def __init__(self, observer: GatewayObserver, period_s: int = 3600,
                 dense_sample_s: int = 600, sparse_sample_s: int = 3600,
                 fast_s: int = 300, mid_s: int = 900, relaxed_s: int = 1800, slow_s: int = 3600,
                 healthy_wh: float = 0.010, lead_s: int = 900, dwell_s: int = 600,
                 decision_epoch_s: int = 300, hysteresis_s: int = 600,
                 use_backup_window: bool = True, gate_sampling: bool = True) -> None:
        super().__init__()
        self.obs = observer
        self.period_s = period_s
        self.dense_sample_s, self.sparse_sample_s = dense_sample_s, sparse_sample_s
        self.fast_s, self.mid_s, self.relaxed_s, self.slow_s = fast_s, mid_s, relaxed_s, slow_s
        self.healthy_wh, self.lead_s = healthy_wh, lead_s
        self.dwell_s, self.decision_epoch_s = dwell_s, decision_epoch_s
        self.hysteresis_s = hysteresis_s
        self.use_backup_window = use_backup_window
        # gate_sampling=False：只按义务相位门控**上报**（= v1.1 已有 ObligationSlackPolicy 的思路），
        # 采样恒稀疏。用于证明"只门控上报救不了采样侧能量失稳，必须门控采样"。
        self.gate_sampling = gate_sampling
        self._last: dict[str, int] = {}
        self._issued: dict[str, tuple[int, int]] = {}
        self._fast: dict[str, bool] = {}        # 快档迟滞状态

    def _want(self, view, nid):
        t = view.t_s
        soc = view.soc_of(nid)
        energy_ok = (soc is None) or soc >= self.healthy_wh
        k = t // self.period_s
        slack = (k + 2) * self.period_s - t
        copies = (view.gateway_copies_in_window or {}).get(nid, 0)

        if not self.use_backup_window:
            urgent = slack < self.period_s
            sample = self.dense_sample_s if (energy_ok and urgent) else self.sparse_sample_s
            report = self.fast_s if urgent else self.mid_s
            return sample, report

        if not energy_ok:
            return self.sparse_sample_s, self.relaxed_s
        if self.obs.primary_up(t):
            self._fast[nid] = False
            return self.sparse_sample_s, self.mid_s

        rate = self.obs.backup_rate_s
        if copies >= 1:
            self._fast[nid] = False
            return self.sparse_sample_s, self.relaxed_s        # 已有副本等备用：不重复密采

        # 无副本：快档迟滞状态机（进入阈值更紧、退出阈值更松，防边界震荡）
        enter = slack <= self.lead_s + rate
        leave = slack <= self.lead_s + rate + self.hysteresis_s
        was_fast = self._fast.get(nid, False)
        is_fast = enter if not was_fast else leave
        self._fast[nid] = is_fast
        if is_fast:
            return self.dense_sample_s, self.fast_s
        return self.sparse_sample_s, self.mid_s

    def plan(self, view):
        # 决策限频：只在 epoch 边界重新评估，避免逐拍锯齿引起档位/信令震荡
        if view.t_s % self.decision_epoch_s != 0:
            return []
        out = []
        for nid in view.node_ids:
            if nid in view.in_flight:
                self._skip("in_flight", nid)
                continue
            last = self._last.get(nid)
            if last is not None and view.t_s - last < self.dwell_s:
                self._skip("dwell", nid)
                continue
            soc = view.soc_of(nid)
            if soc is None:
                self._skip("no_soc", nid)
                continue
            want_sample, want_report = self._want(view, nid)
            if not self.gate_sampling:
                want_sample = self.sparse_sample_s     # 只门控上报消融（= 已有 oblig_slack）
            snap = view.reports.get(nid) or {}
            if (snap.get("sample_interval_s") == want_sample
                    and snap.get("report_period_s") == want_report):
                self._issued.pop(nid, None)
                continue
            if self._issued.get(nid) == (want_sample, want_report):
                continue
            self._last[nid] = view.t_s
            self._issued[nid] = (want_sample, want_report)
            a, b = self.stamp_pair(
                nid,
                {"op": OP_SET_SAMPLING_INTERVAL, "interval_s": want_sample},
                {"op": OP_SET_REPORT_PERIOD, "period_s": want_report})
            out.append((nid, a))
            out.append((nid, b))
        return out
