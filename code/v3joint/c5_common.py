# -*- coding: utf-8 -*-
"""c5_common.py — C5 configuration-termination family: prediction ledger and online strategies.

**已在版本控制内**（`code/v3joint/`）。早先的说明写它是"未跟踪的本地脚手架"，那是在 C5 修正
重新入库之前；本文件现在是配置终止线（C5/C9）证据链的一部分，由 `code/v3joint/c5_matrix.py`
使用、结果登记在 `results/c5_matrix.json`。过程材料（旧 FINDINGS、paper_v09、探针）仍留在
`local_experiments/`，不进仓库。

它 monkeypatch `Node._apply_local_floor`，加入*在线*配置终止策略；这些策略只能用节点在当时
合法拥有的信息（自测电量、本地时钟、公开昼夜曲线、协议周期 P、已部署任务端点、链路可靠性、
预授权回退权）。任务 2 的策略**不读**未来降级时刻 `down`。

All arms share: clock night floor (dense->sparse at dusk), generic_expiry record cache, maxcov backup
packing, identical install path (a dense config is detected at the node on the rising edge, i.e. when
the field actually applies over the air — never pre-installed at t=0).
"""
from __future__ import annotations
import math
import numpy as np

TICK = 60
DENSE = 300
SPARSE = 600
DAY_START = 6          # t=0 maps to local 06:00 sunrise
DUSK_H = 18            # local sunset hour-of-day
DAYLIGHT = 12.0
SAMPLE_WH = 4.7e-4
CAP_WH = 0.05
# cloud expectation for the synthetic harvester: E[factor] = (1-p)+p*atten, p=.35, atten=.25
CLOUD_EFF = (1 - 0.35) + 0.35 * 0.25     # = 0.7375

_UPLINK_WH = 2.33e-5
_RX_WH = None


def _rx_wh():
    global _RX_WH
    if _RX_WH is None:
        try:
            from admission import RX_WH
            _RX_WH = RX_WH
        except Exception:
            _RX_WH = 0.0
    return _RX_WH


def sun_factor(t_s) -> np.ndarray:
    t = np.asarray(t_s, dtype=float)
    hod = (DAY_START + t / 3600.0) % 24.0
    rel = (hod - DAY_START) % 24.0
    return np.where(rel <= DAYLIGHT, np.maximum(0.0, np.sin(np.pi * rel / DAYLIGHT)), 0.0)


def load_per_tick_array(period_s: int, n: int, uplink_p_arrive: float) -> np.ndarray:
    """Wh consumed per tick under a fixed config; uplink energy scaled by expected attempts 1/p."""
    samples_per_tick = TICK / period_s
    uplinks_per_tick = TICK / period_s
    per_tick = (samples_per_tick * SAMPLE_WH
                + uplinks_per_tick * (_UPLINK_WH + _rx_wh()) / max(1e-6, uplink_p_arrive))
    return np.full(n, per_tick)


def _ledger_terms(t0: int, dense_until: int, peak_eff: float, n: int):
    """每拍的采能与负载，单位 Wh/tick。收割单位与 exogenous.solar_harvest 一致（wh/60）。"""
    t = np.arange(t0, t0 + n * TICK, TICK)
    harv = peak_eff * sun_factor(t) / 60.0
    load = np.where(t < dense_until,
                    load_per_tick_array(DENSE, n, C5Config.uplink_p_arrive),
                    load_per_tick_array(SPARSE, n, C5Config.uplink_p_arrive))
    return t, harv, load


def rollout_stepwise(soc0: float, t0: int, dense_until: int, peak_eff: float,
                     task_end_s: int) -> tuple[float, float]:
    """逐步递推的参考实现：直接照抄环境的步序。

    环境每拍（network.py: `Node.step` -> `_step_power` -> 动作扣费）：
      1) 采能按可用容量截断后进电池：`soc = min(capacity, soc + harvest)`；
      2) 静息（本实例为 0）；
      3) 采样与空口消耗：`soc -= load`。
    因此一步的递推是 `x[k] = min(C, x[k-1] + h[k]) - l[k]`。

    本函数是慢路径，存在的唯一理由是给下面的向量化实现当对照。
    """
    n = max(0, (task_end_s - t0 + TICK - 1) // TICK)
    _, harv, load = _ledger_terms(t0, dense_until, peak_eff, n)
    soc = float(soc0)
    mn = float(soc0)
    for k in range(n):
        soc = min(CAP_WH, soc + float(harv[k]))
        soc -= float(load[k])
        if soc < mn:
            mn = soc
    return mn, soc


def _rollout_min(soc0: float, t0: int, dense_until: int, peak_eff: float, reserve_wh: float,
                 task_end_s: int) -> tuple[float, float]:
    """Vectorised forward SoC ledger from t0 to task_end: dense until dense_until then sparse.
    Returns (min_soc, final_soc). Expected (cloud-adjusted) solar, no same-day cloud draws.

    **容量截断必须在这里。** 环境的收割按可用容量截断（`soc = min(CAP, soc + harvest)`），
    此前本账本用 `soc0 + cumsum(harv - load)` 累加，没有上界，于是可以攒出高于 `CAP_WH` 的
    电量，把"预测可行"打在物理上存不下的能量上。一族的边界结论（开环候选死亡、滚动门零死亡）
    都建立在这份账本上，因此这条漏项会改变主结论，而不只是精度。

    单侧截断的向量化：先算未截断的净轨迹 `raw`，再减去累计溢出。逐步版本见
    `rollout_stepwise`，两者在 `selfcheck_ledger` 中逐点比对。
    """
    n = max(0, (task_end_s - t0 + TICK - 1) // TICK)
    if n == 0:
        return soc0, soc0
    _, harv, load = _ledger_terms(t0, dense_until, peak_eff, n)
    raw = soc0 + np.cumsum(harv - load)
    spill = np.maximum.accumulate(np.maximum(0.0, raw + load - CAP_WH))
    soc = raw - spill
    return float(min(soc0, soc.min())), float(soc[-1])


def selfcheck_ledger(trials: int = 12, seed: int = 0) -> float:
    """向量化账本与逐步递推的最大偏差（Wh）。用于在复跑前证明两者是同一个模型。"""
    rng = np.random.default_rng(seed)
    worst = 0.0
    for _ in range(trials):
        soc0 = float(rng.uniform(0.0, CAP_WH))
        t0 = int(rng.integers(0, 12 * 3600))
        dense_until = int(t0 + rng.integers(0, 12 * 3600))
        peak = float(rng.uniform(0.004, 0.06))
        end = int(rng.integers(t0 + 3600, 49 * 3600))
        a = _rollout_min(soc0, t0, dense_until, peak, 0.0, end)
        b = rollout_stepwise(soc0, t0, dense_until, peak, end)
        worst = max(worst, abs(a[0] - b[0]), abs(a[1] - b[1]))
    return worst


def feasible(soc0, t0, dense_until, peak_eff, reserve_wh, task_end_s) -> bool:
    mn, _ = _rollout_min(soc0, t0, dense_until, peak_eff, reserve_wh, task_end_s)
    return mn >= reserve_wh


def dusk_of(t_s: int) -> int:
    return (t_s // 86400) * 86400 + 43200


def max_feasible_dense_until(t0: int, soc0: float, peak_eff: float, reserve_wh: float,
                             task_end_s: int, align_s: int | None = None) -> int:
    """Latest absolute t dense may run (today, <=dusk) while surviving to task_end.

    Feasibility is monotone non-increasing in the dense duration -> binary search.
    """
    dusk = dusk_of(t0)
    if not feasible(soc0, t0, t0, peak_eff, reserve_wh, task_end_s):
        tau = t0
    else:
        lo, hi = t0, dusk
        if feasible(soc0, t0, hi, peak_eff, reserve_wh, task_end_s):
            tau = hi
        else:
            while lo < hi:
                mid = ((lo + hi) // TICK // 2 * TICK)
                if mid <= lo:
                    mid = lo + TICK
                if feasible(soc0, t0, mid, peak_eff, reserve_wh, task_end_s):
                    lo = mid
                else:
                    hi = mid - TICK
                if hi - lo <= TICK:
                    break
            tau = lo if feasible(soc0, t0, lo, peak_eff, reserve_wh, task_end_s) else t0
    if align_s:
        tau = (tau // align_s) * align_s
        tau = max(t0, tau)
    return min(tau, dusk)


class C5Config:
    mode = "nightfloor"          # nightfloor|ttl|valid_until|soc_mpc|energy_lease|lease_safety
    ttl_delta_s = 8 * 3600
    valid_until_s = None
    peak_wh_h = 0.03
    use_cloud_expectation = True
    peak_frac = 1.0              # fraction of expected peak used in the local ledger (1=expected,<1 conservative)
    reserve_mult = 1.0           # reserve = reserve_mult * SAMPLE_WH
    safety_mult = 4.0            # extra-conservative reserve for the lease safety net
    align_s = DENSE
    uplink_p_arrive = 0.74
    task_end_s = 49 * 3600

    @classmethod
    def peak_eff(cls, frac=None):
        base = cls.peak_wh_h * (CLOUD_EFF if cls.use_cloud_expectation else 1.0)
        return base * (cls.peak_frac if frac is None else frac)

    @classmethod
    def reserve(cls, mult=None):
        return SAMPLE_WH * (cls.reserve_mult if mult is None else mult)


def install():
    import network as net
    if getattr(net.Node, "_c5_patched", False):
        return net

    def floor(self, t_s):
        lf = self.local_floor
        if lf is None:
            return
        day_start = lf.get("day_start", DAY_START)
        dusk = lf.get("dusk", DUSK_H)
        dense = lf["dense"]
        sparse = lf["sparse"]
        hod = (day_start + t_s / 3600.0) % 24.0
        night = hod < day_start or hod >= dusk

        if not hasattr(self, "_c5_min_soc"):
            self._c5_min_soc = self.soc_wh
            self._c5_soc_t = t_s
        if self.soc_wh < self._c5_min_soc:
            self._c5_min_soc = self.soc_wh

        cfg = C5Config
        cur_dense = self.sample_interval_s == dense
        was = getattr(self, "_c5_was", False)
        if (not was) and cur_dense:
            self._c5_enter_t = t_s
            self._c5_enter_soc = self.soc_wh
            self._c5_lease_end = None
            if cfg.mode == "ttl":
                self._c5_lease_end = t_s + cfg.ttl_delta_s
            elif cfg.mode == "valid_until":
                self._c5_lease_end = cfg.valid_until_s
            elif cfg.mode in ("energy_lease", "lease_safety"):
                # open-loop feed-forward bound installed at apply time, from measured SoC only
                self._c5_lease_end = max_feasible_dense_until(
                    t_s, self.soc_wh, cfg.peak_eff(), cfg.reserve(),
                    cfg.task_end_s, cfg.align_s)
        self._c5_was = cur_dense

        revert, why = False, None
        if night and cur_dense:
            revert, why = True, "clock_night"
        elif cur_dense and self._c5_lease_end is not None and t_s >= self._c5_lease_end:
            revert, why = True, "lease_end"
        elif cur_dense and cfg.mode in ("soc_mpc", "lease_safety"):
            # rolling receding-horizon energy feasibility using CURRENT measured SoC.
            # keep dense iff it can still cover the next yellow window while surviving to task end.
            if cfg.mode == "lease_safety":
                # safety net uses a more conservative ledger; the open-loop plan otherwise stands
                rsv, pf = cfg.reserve(cfg.safety_mult), cfg.peak_eff()
            else:
                rsv, pf = cfg.reserve(), cfg.peak_eff()
            tau_t = max_feasible_dense_until(t_s, self.soc_wh, pf, rsv,
                                             cfg.task_end_s, cfg.align_s)
            if tau_t < t_s + cfg.align_s:
                revert, why = True, ("safety" if cfg.mode == "lease_safety" else "mpc")
        if revert:
            if self.sample_interval_s == dense:
                self.sample_interval_s = sparse
            if self.report_period_s == dense:
                self.report_period_s = sparse
            if not getattr(self, "_c5_revert_t", None):
                self._c5_revert_t = t_s
                self._c5_revert_why = why

    net.Node._apply_local_floor = floor
    net.Node._c5_patched = True
    return net
