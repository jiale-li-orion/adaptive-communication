#!/usr/bin/env python3
"""**持续配置的资源准入**：在下发之前，检查一个会持续耗电的配置撑不撑得住。

**要解决的那个具体失效**（由五小时计划 §0–1h 的闸门定位）：`out3` 里中心在 h1 按一条
**准确、健康**的读数（0.0195）下发了加密配置，h3 起失去有效控制，此后它反复重申的仍是
**依据那条陈旧读数算出的加密配置**，节点 h8 耗尽死亡、缺采 11。失效不在"读错了"，
而在于**一次下发把持续负载写进了端侧，而这次决定隐含了"我还来得及改回来"这个前提**。

**准入式**（规格见 `18-method-spec-continuous-config-admission-2026-09-13.md`）：

    对每台节点、每个候选配置 c：
        ∀ u ∈ [t, t+H] :  battery_lo(u | history, c)  ≥  reserve

**三条必须一起成立的性质**：
  1. **在途/部分生效按上界算**——降档只发出未确认时，不提前按低负载计算；
  2. **源时间不被接收时间替代**——证据年龄决定 `battery_lo` 要往下推多久；
  3. **不可行时返回拒绝理由**，不静默换目标后称原动作成功。

**纠错机会上界 `D`**：这是本模块唯一的"机制参数"。
`D = 3 h` 表示"相信最多 3 小时后还能再改"（标准鲁棒过滤器式的有界延迟）；
`D = ∞` 表示"在保护时域内不假设还能改"。**若两者在开发集上没有差别，这个准入层就是
标准方法的适配，不是新机制——那时应当合并两臂而不是称其为候选。**
"""
from __future__ import annotations

import os as _os
import sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
for _p in (_HERE, _os.path.join(_os.path.dirname(_HERE), "monitoring"),
           _os.path.join(_os.path.dirname(_HERE), "physics")):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

from center import CenterPolicy, OP_SET_REPORT_PERIOD, OP_SET_SAMPLING_INTERVAL  # noqa: E402
from oracle import UPLINK_WH  # noqa: E402
import opportunity as _op  # noqa: E402

#: **接收窗口能耗**。每次上行之后节点都要开一次窗口，无论有没有东西等它——
#: 这是本实例的既有语义，准入必须把它算进去，否则会把负载系统性低估（加密上报会成倍增加上行）。
RX_WH = _op.BUS_V * (_op.RX_MA / 1000.0) * (2000.0 / 3.6e6)

#: 默认的稀疏档（= 出厂默认）。所有策略的"退回档"都是它，准入里也用它。
SPARSE = (3600, 3600)


def hourly_load(sample_interval_s: int, report_period_s: int, sample_wh: float) -> float:
    """某个 `(采样间隔, 上报周期)` 配置的**每小时上界能耗**（Wh）。

    **这是上界**：按"每个采样周期都采、每个上报周期都上行"算，不假设任何一次会省下来。
    采样次数与上行次数分别由两个字段决定——它们**是两个独立的字段**（E：重庆 `0045`/`0042`），
    任何一个变大都会单独抬高负载，把两个字段合成一个"周期"会漏掉一半的动作面。
    """
    samples = 3600.0 / max(1, sample_interval_s)
    uplinks = 3600.0 / max(1, report_period_s)
    return samples * sample_wh + uplinks * (UPLINK_WH + RX_WH)


class ResourceGate:
    """准入判据本体。**它只做一件事：给一个候选配置和一个电量下界，回答撑不撑得住。**"""

    def __init__(self, sample_wh: float, capacity_wh: float, horizon_s: int,
                 correction_s: int | None, reserve_wh: float = 0.0) -> None:
        self.sample_wh = sample_wh
        self.capacity_wh = capacity_wh
        self.horizon_s = int(horizon_s)
        #: 纠错机会上界（秒）。`None` ⇒ 保护时域内不假设还能再改。
        self.correction_s = None if correction_s is None else int(correction_s)
        self.reserve_wh = reserve_wh
        self.checks = 0
        self.accepts = 0
        self.rejects: dict[str, int] = {}

    def _reject(self, reason: str) -> tuple[bool, str]:
        self.rejects[reason] = self.rejects.get(reason, 0) + 1
        return False, reason

    def check(self, soc_lo_wh: float, config: tuple[int, int]) -> tuple[bool, str]:
        """`soc_lo_wh` 是**此刻**的电量下界；`config` 是候选的 `(采样间隔, 上报周期)`。

        逐时推进到保护时域结束：前 `D` 秒按候选配置的负载算，之后按**退回档（稀疏）**算——
        这就是"最多 D 小时后还能改回来"的形式化。`D = None` 时全程按候选配置算。
        """
        self.checks += 1
        if soc_lo_wh <= 0:
            return self._reject("no_evidence_or_empty")
        load_cand = hourly_load(config[0], config[1], self.sample_wh)
        load_sparse = hourly_load(SPARSE[0], SPARSE[1], self.sample_wh)
        soc = soc_lo_wh
        # 第一版用**按小时推进**的离散上界：一小时内的采能与消耗都按最坏方向取。
        # 采能下界 = 0（`hetero` 下 40% 节点恒为 0，中心分辨不出是哪一台）。
        t = 0
        while t < self.horizon_s:
            step = min(3600, self.horizon_s - t)
            if self.correction_s is None or t < self.correction_s:
                soc -= load_cand * (step / 3600.0)
            else:
                soc -= load_sparse * (step / 3600.0)
            if soc < self.reserve_wh:
                # **在保护时域内的哪一段不可行**要能说出来：它决定"是配置太重"还是"时域太长"。
                fail_at = t + step
                return self._reject(
                    f"infeasible_at_{fail_at // 3600}h"
                    f"_correction_{'inf' if self.correction_s is None else self.correction_s // 3600}h")
            t += step
        self.accepts += 1
        return True, "ok"

    def report(self) -> dict:
        return {"checks": self.checks, "accepts": self.accepts,
                "rejects": dict(self.rejects)}


class GatePolicy(CenterPolicy):
    """把准入层套在一条 inner 策略外面。

    **准入只能否决，不能自己生成动作。** 这是"准入"与"新策略"的分界：门背后的动作集合、
    动作语义、观测权限与 inner 完全相同；被拒时节点**保持它原来的配置**，不是被改成一个
    门自己挑的配置。若门能自己挑配置，比的就不是"准入"，而是"又写了一条策略"。
    """

    def __init__(self, inner: CenterPolicy, gate: ResourceGate,
                 sample_wh: float, capacity_wh: float, max_age_s: int | None = None,
                 name: str = "gated") -> None:
        super().__init__()
        self.inner = inner
        self.gate = gate
        self.sample_wh = sample_wh
        self.capacity_wh = capacity_wh
        #: 证据新鲜度门槛（秒）。`None` ⇒ 不看年龄。这是**竞争解释**臂用的：
        #: 如果"只按新鲜读数行动"就能解决失效，准入层就没有增量。
        self.max_age_s = max_age_s
        self.name = name
        self._last_sent: dict[str, tuple[int, int]] = {}
        self.denied: dict[str, int] = {}
        self.denied_reasons: dict[str, int] = {}

    def plan(self, view):
        """**只否决，不生成。** inner 想发什么就发什么；门只回答"这一对配置能不能发"。"""
        proposals = self.inner.plan(view)
        # 两个字段**由同一次决策产生**（`stamp_pair` 给它们同一个世代号），所以要拼成一对
        # 才能拿去算负载。只看单个字段会漏掉"另一个字段仍在旧值"的情况。
        by_node: dict[str, dict] = {}
        for nid, payload in proposals:
            by_node.setdefault(nid, {})[payload.get("op")] = payload
        out = []
        for nid, fields in by_node.items():
            a = fields.get(OP_SET_SAMPLING_INTERVAL)
            b = fields.get(OP_SET_REPORT_PERIOD)
            cur = self._in_effect(view, nid)
            pair = (a.get("interval_s") if a else cur[0],
                    b.get("period_s") if b else cur[1])
            ok, why = self._admit(view, nid, pair)
            if ok:
                if a:
                    out.append((nid, a))
                if b:
                    out.append((nid, b))
                self._last_sent[nid] = pair
            else:
                self.denied[nid] = self.denied.get(nid, 0) + 1
                self.denied_reasons[why] = self.denied_reasons.get(why, 0) + 1
                self._skip("admission_rejected", nid)
        return out

    def _in_effect(self, view, nid: str) -> tuple[int, int]:
        """**可能已生效**的配置：已确认的回执与"发出去但还没确认"的取**较重的那个**。

        性质 1（在途/部分生效按上界算）就实现在这里：降档只发出未确认时，
        `_last_sent` 里还是旧的重配置，于是准入**不会**按低负载算。
        """
        confirmed = (view.reports.get(nid) or {})
        cand = (int(confirmed.get("sample_interval_s") or 3600),
                int(confirmed.get("report_period_s") or 3600))
        sent = self._last_sent.get(nid)
        if sent is not None:
            # 负载更大者胜出（间隔更小 / 周期更小 = 更重）。
            if hourly_load(*sent, self.sample_wh) > hourly_load(*cand, self.sample_wh):
                cand = sent
        return cand

    def _admit(self, view, nid: str, pair: tuple[int, int]) -> tuple[bool, str]:
        """判据：**新配置的负载不得高于"可能已生效"的负载，除非它撑得住保护时域。**

        这一条把"准入"限制成一个**单调**的检查：降低负载永远放行（它只会更安全），
        只有**抬高**负载才需要证明。这样被拒的一定是"想加密"的那些，语义干净。
        """
        cur = self._in_effect(view, nid)
        if hourly_load(*pair, self.sample_wh) <= hourly_load(*cur, self.sample_wh):
            return True, "not_heavier"
        if self.max_age_s is not None:
            age = view.soc_age_s(nid)
            if age is None or age > self.max_age_s:
                return False, "evidence_stale"
        soc = self._soc_lo(view, nid, cur)
        return self.gate.check(soc, pair)

    def _soc_lo(self, view, nid: str, cur: tuple[int, int]) -> float:
        """此刻的电量**下界**：最近一条合法读数，减去"从它的**源时刻**到现在，
        按可能已生效配置发生的消耗上界"。

        用源时刻而不是接收时刻：读数在链路上走的那段时间，节点的电也在掉，
        用接收时刻会把这部分漏掉（性质 2）。
        """
        snap = view.reports.get(nid)
        if not snap or snap.get("soc_wh") is None:
            return -1.0
        age = view.soc_age_s(nid)
        if age is None or age < 0:
            return -1.0
        spent = hourly_load(*cur, self.sample_wh) * (age / 3600.0)
        return float(snap["soc_wh"]) - spent

    def gate_report(self) -> dict:
        return {"denied_nodes": len(self.denied),
                "denied_total": sum(self.denied.values()),
                "denied_reasons": dict(self.denied_reasons),
                "gate": self.gate.report()}


#: 受准入层管辖的臂 → (inner 臂, 时域用剩多少, 纠错机会上界秒, 证据新鲜度门槛秒)。
#: `horizon 0` = 不做可行性检查（只用于隔离"新鲜度过滤"这一个因素）。
GATED_ARMS = {
    # **阈值臂不在这里**：它们是 `center.ARMS` 里的纯策略（只换 `healthy_wh`，不带门）。
    # 第一版把它们放进了这张表，于是"阈值臂"实际上被套上了完整候选门——测出来的不是阈值。
    # 只按新鲜度过滤：证据超过 1 h 就不行动。
    "ea_nb_fresh": ("ea_nb", "zero", None, 3600),
    # 鲁棒可行性过滤：相信"最多 3 小时后还能再改"。
    "ea_nb_rob3": ("ea_nb", "horizon", 3 * 3600, None),
    # 候选：保护时域内**不假设还能改**。
    "ea_nb_cand": ("ea_nb", "horizon", None, None),
}


def build_gated(arm: str, *, sample_wh: float, capacity_wh: float,
                horizon_s: int, inner: CenterPolicy | None = None):
    """按臂名构造带准入的包装。**不在表里的臂返回 `None`**（调用方回退到 `build_policy`）。"""
    spec = GATED_ARMS.get(arm)
    if spec is None:
        return None
    inner_arm, horizon_kind, correction_s, max_age = spec
    from center import ARMS
    if inner is None:
        inner = ARMS[inner_arm]()
    H = 0 if horizon_kind == "zero" else horizon_s
    gate = ResourceGate(sample_wh=sample_wh, capacity_wh=capacity_wh,
                        horizon_s=H, correction_s=correction_s)
    return GatePolicy(inner, gate, sample_wh=sample_wh, capacity_wh=capacity_wh,
                      max_age_s=max_age, name=arm)
