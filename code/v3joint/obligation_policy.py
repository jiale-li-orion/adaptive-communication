#!/usr/bin/env python3
"""obligation_policy.py — R04 正确实例化：义务-交付联合策略（规则版，非 MPC，不接 LLM）。

修复 joint_policy.DeliveryOpportunisticPolicy 的 anchor 恒假（doc19 R1）：
旧策略 `slack=(k+2)P-t` 只看**当前窗口** k=t//P，恒有 P<slack<=2P，紧急分支 `slack<P` 永假；
进入宽限期后上一窗口的负债又被新窗口 index 覆盖、每周期清零。

本策略改为追踪**最老的、网关尚无合格副本且尚未截止的具体义务**：
  * routine 义务 i：窗口 [iP,(i+1)P]，绝对截止 (i+2)P（与 exogenous/评分器同源，公开配置）；
  * 未截止且网关 copies=0 的窗口只可能是 i=cur-1（宽限期内）或 i=cur，取更老者，其 slack 随 t
    真实递减到 0，紧急动作因此能在正确时刻触发，且不依赖抬高阈值。
三态（doc19 §3，全部用网关位置合法可见量，不读环境真值/未来）：
  1. cur-1/cur 窗口网关都已有合格副本（无未完成义务）→ 最省：稀疏采样、适中上报，不重复密采；
  2. 最老未完成义务的窗口样本节点已采到（网关听过的 newest_taken 落在窗口）但网关无副本
     → 缺的是上报：采样维持稀疏省电，逼近可执行前置期时加快上报；
  3. 连该窗口样本都没采到 → 必须在 "下令→Class A 生效→采/报→赶上下一次交付机会" 的前置期内
     启动密采+快报，否则即使动作也来不及，索性不浪费（能量保命线优先）。
主路是否在喂由**网关自己的转发反馈**（gateway_last_forward_ok_at）推断，不读 backhaul_available
环境真值（doc19 R7）；下一次备用机会相位用公开 backup_rate 计算（旧策略漏调用，doc19 R1.4）。
"""
from __future__ import annotations
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_CODE = os.path.dirname(_HERE)
for p in [_HERE] + [os.path.join(_CODE, d) for d in ("monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from center import CenterPolicy, OP_SET_REPORT_PERIOD, OP_SET_SAMPLING_INTERVAL


class ObligationDeliveryPolicy(CenterPolicy):
    name = "odp"

    def __init__(self, observer, period_s: int = 3600,
                 dense_sample_s: int = 600, sparse_sample_s: int = 3600,
                 fast_s: int = 300, mid_s: int = 900, relaxed_s: int = 1800,
                 healthy_wh: float = 0.010, lead_s: int = 900,
                 dwell_s: int = 600, decision_epoch_s: int = 300,
                 primary_stale_s: int = 1800) -> None:
        super().__init__()
        self.obs = observer
        self.period_s = int(period_s)
        self.dense_sample_s, self.sparse_sample_s = dense_sample_s, sparse_sample_s
        self.fast_s, self.mid_s, self.relaxed_s = fast_s, mid_s, relaxed_s
        self.healthy_wh, self.lead_s = healthy_wh, lead_s
        self.dwell_s, self.decision_epoch_s = dwell_s, decision_epoch_s
        # 超过这么久没成功转发过，就按主路受阻处理（纯本地反馈，对所有臂同接口）。
        self.primary_stale_s = primary_stale_s
        self._last: dict[str, int] = {}
        self._issued: dict[str, tuple[int, int]] = {}
        self.last_reason: dict[str, str] = {}     # 记录每个节点本次决策的三态归因，供可辨识见证

    # ------------------------------------------------------------ 合法状态推导
    def _primary_feeds(self, view, t: int) -> bool:
        last = getattr(view, "gateway_last_forward_ok_at", None)
        return last is not None and (t - last) <= self.primary_stale_s

    def oldest_open(self, view, nid):
        """最老的、网关无合格副本且未截止的义务窗口。

        返回 (k, slack_s, node_has_window_sample)；无未完成义务返回 None。
        `k` 窗口索引、绝对截止 (k+2)P、slack=(k+2)P-t（固定截止，随 t 真实递减）。
        `node_has_window_sample`：网关听过的该节点最新样本是否落在窗口 k（=采到了但没到网关）。
        """
        t = view.t_s; P = self.period_s; cur = t // P
        byw = (getattr(view, "gateway_copies_by_window", None) or {}).get(nid, {})
        newest = view.newest_taken_at.get(nid)
        for k in (cur - 1, cur):                    # 更早窗口已截止；只可能欠这两个，先老后新
            if (k + 2) * P <= t:
                continue                            # 已过截止，救不了，不算未完成
            if byw.get(k, 0) == 0:
                node_has = newest is not None and k * P <= newest <= (k + 1) * P
                return k, (k + 2) * P - t, node_has
        return None

    def _want(self, view, nid):
        t = view.t_s
        soc = view.soc_of(nid)
        energy_ok = (soc is None) or soc >= self.healthy_wh
        if not energy_ok:
            self.last_reason[nid] = "energy_guard"
            return self.sparse_sample_s, self.relaxed_s
        opn = self.oldest_open(view, nid)
        if opn is None:
            # 态1：相关窗口网关都已有副本（或当前无欠账）→ 最省，不重复密采
            self.last_reason[nid] = "covered_at_gateway"
            return self.sparse_sample_s, self.mid_s
        k, slack, node_has = opn
        feeds = self._primary_feeds(view, t)
        nxt_backup = self.obs.next_backup_in_s(t) if self.obs is not None else 0
        # 主路在喂：回传会自行恢复转发，不必动用备用前置期，按常规节奏即可。
        horizon = self.lead_s if feeds else self.lead_s + nxt_backup
        if node_has:
            # 态2：采到了、没到网关 → 促上报，采样保持稀疏（再密采只耗电与冗余）
            if slack <= horizon:
                self.last_reason[nid] = "push_report"
                return self.sparse_sample_s, self.fast_s
            self.last_reason[nid] = "covered_soon"
            return self.sparse_sample_s, self.mid_s
        # 态3：窗口样本都还没采到 → 必须在可执行前置期内密采+快报才来得及
        if slack <= horizon:
            self.last_reason[nid] = "must_sample"
            return self.dense_sample_s, self.fast_s
        self.last_reason[nid] = "ahead_of_deadline"
        return self.sparse_sample_s, self.mid_s

    # ------------------------------------------------------------ 每周期决策
    def plan(self, view):
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
            out.append((nid, a)); out.append((nid, b))
        return out
