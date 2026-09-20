# -*- coding: utf-8 -*-
"""c5_seqref.py — 三方判别中的**中间行**：同信息、非预知的序列优化参照。

口径（v2）

本文件按 `spec/prereg-nonprescient-sequence-v2.md` 实现。v1（`…-v1.md`，结果
`results/c5_seqref_v1_semantics.json`）有两处契约错误，独立审阅已给出可直接运行的反例
（独立审阅的本地记录 `local_experiments/c5_lease/review/` 不随仓库发布；其反例已在本文件与
`code/experiments/audit_seqref.py` 中重建，克隆可自行核对）：

  1. **真值终点替策略自动降档**。v1 的求值器只把规则执行到黄级窗口终点 `down_h`，随后接上
     "此后始终稀疏"的安全性。那等于免费给了节点"真实授权结束时本地终止"的能力——正是 C5 要研究的
     缺口。反例：一个永远返回"继续密集"的规则在 v1 里被评为**安全且满窗**；把 `TTL8+8 mWh 门`
     真正执行到它自己的结束时刻（h10，而不是在未知的 h6 自动降档），最低电量掉到 0.3295 mWh，
     低于本模型声明的 0.47 mWh 安全线。
  2. **等权三点没有匹配声明的标准差**。`{μ−s, μ, μ+s}` 等权时 `std = s·sqrt(2/3)`，所以
     `s=.047` 的实际标准差是 .03838，不是 .047。v2 直接用标准差作为参数：偏移 `= σ·sqrt(3/2)`。

v2 的执行语义（两条硬约束）：

  * **隐藏终点不得改变执行**。策略的动作定义在整个地平线 `[应用边沿, 49h)` 上；求值器**不再**在
    `down_h` 处截断，也不接受任何"终点"参数。黄级窗口终点只用于**计分**（窗口外没有黄级义务），
    不用于停配置。跨隐藏终点的同一策略必须给出逐位相同的配置与能耗轨迹——由
    `endpoint_invariance_probe` 直接验证。
  * **离散化与声明一致**。`levels(σ)` 的实际标准差必须等于 σ（由 `audit_seqref.py` 断言）。

为什么有这个参照
----------------
C5 修正后的实测是：紧能量格上"能量族"候选在应用边沿就回退，黄级交付只剩 559/2016（A）、
1194/3528（B）；而不看能量的固定 TTL8 拿到 849/2016、2020/3528 且 0 死亡。这个反差说明
"保护有代价"，但没有回答其中多少不可避免。参照的用途就是回答它，并遵守三条纪律：**同一信息**
（策略只用 `(相对小时, 量化剩余电量)`）、**同一动作能力**（密集/稀疏两档，一次租约不得重入）、
**同一风险口径**（声明的全部未来里都不得死亡，按环境口径任一拍 `soc < sample_wh` 即判死）。

三方表与恒等式
--------------
    普通组合（声明有限族内最强的可行成员）
    非预知参照（本文件 DP：声明动作族内的精确最优）
    全知参照（逐未来最优，蒙特卡洛平均；**是参照不是上界**）
    service(全知) − service(普通) = 信息差额 + 可实现策略差额

两个差额**分别计算、分别判定**：可实现差额为正本身就是结果，不因仍低于全知而被取消（v1 的判定表
把二者混为一谈，已改）。

台账同源
--------
能量台账与环境逐拍同序（`network.py:_step_power`：`x[k] = min(CAP, x[k-1] + h[k]) - l[k]`）：

  * 容量 50 mWh、单次采样 0.47 mWh（`admission.py`）；
  * 小时负载按**实测分量**给出：每小时采样数 ×（采样 + 单次上报射频），
    稀疏 3.005943 mWh/h、密集 6.011886 mWh/h。实测见
    `code/experiments/measure_seqref_calibration.py` 与
    `results/reference/c5_seqref_calibration.json`（台账校准：49 个小时末电量最大偏差 1.13e-4 Wh）；
  * 采能 `peak · f · sin(π·rel/12) / 60` 每拍，`rel` 自本地 06:00 起算；小时因子均值 0.7375、
    **标准差 0.047（声明值；实测 0.0452（280 个节点×小时样本）、理论 0.0462）**。

**不在本模型内的东西**（截断边界；引用本文件结论时必须同时引用这一句）：

  * **投递链路**。本文件的"服务"是黄级义务**被采集**（密集档在义务释放时刻生效即计），不是被
    投递。实测中即使密集覆盖整个窗口，采集也只有 535/672、投递 283/672。
  * **云遮的时间结构**。环境逐拍抽云，本模型按**小时**取一个因子并做三点离散，逐拍抖动被抹掉。
  * **单节点切片**。不含多节点竞争、网关打包与回传。
  * **动作能力限于一次租约**；不含重入、不含单次采样控制、不含新的观测通道。

跑法
----
    python3 code/v3joint/c5_seqref.py                # 写 results/c5_seqref.json
    python3 code/v3joint/c5_seqref.py --core         # 打印可手算核例的全部算术
    python3 code/v3joint/c5_seqref.py --feasibility  # 只判可行性，不跑三方性能搜索
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))

# ----------------------------------------------------------------- 声明常数
TICK_S = 60
TICKS_PER_HOUR = 3600 // TICK_S
CAP_WH = 0.05                 # 冻结实例 capacity_wh
SAMPLE_WH = 4.7e-4            # 单次采样；同时是"还能不能采一条"的死亡阈
#: 小时负载 = 每小时采样数 ×（sample_wh + 单次上报射频）。声明值与校准参考的 `declared_constants`
#: 用同一组字面量、同一表达式算出，可逐位比对；实测全精度值在同文件的 `measured_constants`。
RADIO_WH_PER_REPORT = 3.099046e-5
LOAD_SPARSE_H = 6 * (SAMPLE_WH + RADIO_WH_PER_REPORT)
LOAD_DENSE_H = 12 * (SAMPLE_WH + RADIO_WH_PER_REPORT)
SUNRISE_H = 6.0
DAYLIGHT_H = 12.0
END_HOUR = 49
Q_SOC = 1e-5                  # 电量量化步长；状态向下取整（对安全与服务都不乐观）
CLOUD_NOMINAL = 0.7375        # 实测量 0.73877（280 样本）；声明值保持原常量
CLOUD_SIGMA = 0.047           # **标准差**（声明）：实测 0.0452、理论 0.0462
PHASES = {"A": dict(up_h=2, down_h=6), "B": dict(up_h=1, down_h=8)}
OBL_PER_HOUR = 12             # 窗口内每节点每小时 12 条黄级义务（300 s 网格）
NODES = 14                    # 冻结实例节点数
MC_PATHS = 4000
MC_SEED = 20260920
PEAKS = (0.006, 0.008, 0.010, 0.012, 0.016, 0.030)
SIGMAS = (0.0, 0.02, 0.0308, 0.0388, 0.0452, 0.047, 0.06, 0.09)
DEGREES = (2, 4, 6, 7, 8, 10, 12)
THETAS = (0.0, 0.002, 0.004, 0.008)
DUSK_H = 12                   # 本地日落（相对小时）


def offset_of(sigma: float) -> float:
    """等权三点 `{μ−δ, μ, μ+δ}` 的实际标准差是 `δ·sqrt(2/3)`；反解得 `δ = σ·sqrt(3/2)`。

    v1 直接把 δ 当标准差用，真实的 σ 只有声明值的 0.8165 倍——不确定性集合被缩小了三分之一。
    """
    return float(sigma) * math.sqrt(1.5)


def levels(sigma: float) -> tuple[float, ...]:
    """三点等权离散；**参数是标准差**，不是支撑半宽。`sigma=0` 退化为单点（预期采能）。"""
    if sigma <= 0.0:
        return (CLOUD_NOMINAL,)
    d = offset_of(sigma)
    return (CLOUD_NOMINAL - d, CLOUD_NOMINAL, CLOUD_NOMINAL + d)


def levels_offset(sigma: float) -> float:
    return 0.0 if sigma <= 0.0 else offset_of(sigma)


# ----------------------------------------------------------------- 时间与采能
def sun_frac(t_s: float) -> float:
    """本地 06:00 日出、12 h 日照窗的正弦形状（与 `exogenous.solar_harvest` 同式）。"""
    hod = (SUNRISE_H + t_s / 3600.0) % 24.0
    rel = (hod - SUNRISE_H) % 24.0
    if rel > DAYLIGHT_H:
        return 0.0
    return max(0.0, float(np.sin(np.pi * rel / DAYLIGHT_H)))


_HOUR_SUN: dict[int, np.ndarray] = {}


def hour_sun(hour: int) -> np.ndarray:
    if hour not in _HOUR_SUN:
        t0 = hour * 3600
        _HOUR_SUN[hour] = np.array([sun_frac(t0 + k * TICK_S) / 60.0
                                    for k in range(TICKS_PER_HOUR)])
    return _HOUR_SUN[hour]


def hour_clear_wh(hour: int, peak: float) -> float:
    return float(peak * hour_sun(hour).sum())


def is_daylight_hour(hour: int) -> bool:
    return float(hour_sun(hour).sum()) > 0.0


# ----------------------------------------------------------------- 台账（慢路径）
def hour_step(soc0: float, hour: int, dense: bool, factor: float, peak: float) -> tuple[float, float]:
    """单小时逐步递推。返回 (小时末电量, 小时内最低电量)。"""
    load = (LOAD_DENSE_H if dense else LOAD_SPARSE_H) / TICKS_PER_HOUR
    soc = min(CAP_WH, float(soc0))
    mn = soc
    for hk in hour_sun(hour) * peak * factor:
        soc = min(CAP_WH, soc + float(hk))
        soc -= load
        mn = min(mn, soc)
    return soc, mn


def path_trace(soc0: float, dense_hours, factors: dict[int, float], peak: float,
               end_hour: int = END_HOUR) -> dict:
    dense_hours = set(dense_hours)
    soc, mn = float(soc0), float(soc0)
    ends = {}
    for h in range(end_hour):
        f = factors.get(h, CLOUD_NOMINAL) if is_daylight_hour(h) else 1.0
        soc, hm = hour_step(soc, h, h in dense_hours, f, peak)
        mn = min(mn, hm)
        ends[h] = soc
    return {"min_soc": mn, "final_soc": soc, "hour_end": ends}


def survives(trace: dict) -> bool:
    """环境口径：任一拍低于 `sample_wh` 即判死（`network.py:_take` 与 `_step_power`）。"""
    return trace["min_soc"] >= SAMPLE_WH


def soc_at_apply_edge(peak: float, up_h: int, past_factor: float = CLOUD_NOMINAL,
                      soc0: float = CAP_WH) -> float:
    return path_trace(soc0, (), {h: past_factor for h in range(up_h)}, peak,
                      end_hour=up_h)["final_soc"]


def schedule_worst_case(peak: float, up_h: int, sigma: float, dense_hours, soc0: float = CAP_WH,
                        past_factor: float = CLOUD_NOMINAL) -> dict:
    """**确定性时刻表**在声明全部未来下的最坏轨迹。

    采能对电量单调、电量对采能单调，且"全低档"是声明集合里的逐点最小未来，因此一条标量轨迹
    就是最坏情形——这是精确结论，不是抽样。状态反馈型规则不能用这个捷径（它必须走网格求交）。
    """
    d = levels_offset(sigma)
    f = {h: past_factor for h in range(up_h)}
    f.update({h: CLOUD_NOMINAL - d for h in range(up_h, END_HOUR) if is_daylight_hour(h)})
    return path_trace(soc0, dense_hours, f, peak)


def sparse_future(peak: float, up_h: int, sigma: float, soc0: float = CAP_WH,
                  low: bool = True) -> dict:
    """应用边沿之后全程稀疏、且取声明集合里对生存最不利的因子（默认低档）。"""
    d = levels_offset(sigma)
    if low:
        f = {h: CLOUD_NOMINAL for h in range(up_h)}
        f.update({h: CLOUD_NOMINAL - d for h in range(up_h, END_HOUR) if is_daylight_hour(h)})
    else:
        f = {h: CLOUD_NOMINAL for h in range(END_HOUR)}
    return path_trace(soc0, (), f, peak)


# ----------------------------------------------------------------- 网格与转移
class Grid:
    def __init__(self, quantum: float = Q_SOC):
        self.q = quantum
        self.n = int(round(CAP_WH / quantum)) + 1
        self.soc = np.arange(self.n) * quantum

    def idx(self, soc):
        return np.clip(np.floor(np.asarray(soc, dtype=float) / self.q).astype(int), 0, self.n - 1)


_MAP_CACHE: dict = {}


def hour_maps(grid: Grid, hour: int, peak: float, dense: bool, factors):
    """该小时在网格上的转移：每个天气档给出 (末电量下标, 是否全程存活)。向量化推进 60 拍。"""
    out = []
    for f in factors:
        key = (grid.n, grid.q, hour, round(peak * f, 12), bool(dense))
        if key not in _MAP_CACHE:
            load = (LOAD_DENSE_H if dense else LOAD_SPARSE_H) / TICKS_PER_HOUR
            soc = grid.soc.copy()
            mn = soc.copy()
            for hk in hour_sun(hour) * (peak * f):
                soc = np.minimum(CAP_WH, soc + float(hk)) - load
                np.minimum(mn, soc, out=mn)
            _MAP_CACHE[key] = (grid.idx(soc), mn >= SAMPLE_WH - 1e-12)
        out.append(_MAP_CACHE[key])
    return out


_S_CACHE: dict = {}


def sparse_suffix_safety(grid: Grid, peak: float, factors, end_hour: int = END_HOUR,
                         reserve_wh: float = 0.0):
    """S[h][i]：自第 h 小时起**永不密集**时，声明全部未来都不死亡且终末不低于保留量。"""
    key = (grid.n, grid.q, round(peak, 12), tuple(sorted(set(factors))), end_hour,
           round(reserve_wh, 12))
    if key in _S_CACHE:
        return _S_CACHE[key]
    S = [None] * (end_hour + 1)
    S[end_hour] = grid.soc >= reserve_wh - 1e-12
    for h in range(end_hour - 1, -1, -1):
        fr = tuple(sorted(set(factors))) if is_daylight_hour(h) else (1.0,)
        ok = np.ones(grid.n, dtype=bool)
        for endi, alive in hour_maps(grid, h, peak, False, fr):
            ok &= alive & S[h + 1][endi]
        S[h] = ok
    _S_CACHE[key] = S
    return S


# ----------------------------------------------------------------- 非预知 DP（全地平线动作）
def solve_nonprescient(peak: float, up_h: int, down_h: int, sigma: float = CLOUD_SIGMA,
                       quantum: float = Q_SOC, soc_root: float | None = None,
                       grid: Grid | None = None, end_hour: int = END_HOUR,
                       reserve_wh: float = 0.0) -> dict:
    """声明动作族内的非预知精确最优，动作定义在 `[up_h, end_hour)` 全段。

    `A[h][i]` = 从第 h 小时、量化电量 i、尚未终止出发的最优期望服务（黄级义务数）。
    终止是吸收态（值 0，此后永久稀疏）。奖励只在黄级窗口 `[up_h, down_h)` 内计数——
    **窗口终点只影响计分，不影响执行**。
    """
    grid = grid or Grid(quantum)
    day_fr = tuple(sorted(set(levels(sigma))))
    soc_root = soc_at_apply_edge(peak, up_h) if soc_root is None else soc_root
    S = sparse_suffix_safety(grid, peak, day_fr, end_hour, reserve_wh)
    root = int(grid.idx(soc_root))

    adm = [None] * (end_hour + 1)
    val = [None] * (end_hour + 1)
    pol: dict[int, np.ndarray] = {}
    adm[end_hour] = S[end_hour].copy()
    val[end_hour] = np.where(adm[end_hour], 0.0, -np.inf)
    for h in range(end_hour - 1, up_h - 1, -1):
        reward = OBL_PER_HOUR if h < down_h else 0
        cont_ok = np.ones(grid.n, dtype=bool)
        acc = np.zeros(grid.n)
        for endi, alive in hour_maps(grid, h, peak, True, day_fr):
            good = alive & adm[h + 1][endi]
            cont_ok &= good
            acc += np.where(good, val[h + 1][endi], 0.0) / len(day_fr)
        cont_val = np.where(cont_ok, reward + acc, -np.inf)
        stop_val = np.where(S[h], 0.0, -np.inf)
        pol[h] = cont_ok & (cont_val >= stop_val)
        adm[h] = cont_ok | S[h]
        val[h] = np.maximum(cont_val, stop_val)
    ok = bool(adm[up_h][root])
    return {
        "sigma": sigma, "levels": list(day_fr), "offset": levels_offset(sigma),
        "quantum": grid.q, "grid_n": grid.n, "soc_root": soc_root, "root_idx": root,
        "admissible": ok,
        "expected_dense_hours": float(val[up_h][root] / OBL_PER_HOUR) if ok else None,
        "expected_service_per_node": float(val[up_h][root]) if ok else None,
        "policy_dense_hours_by_hour": {str(h): bool(pol[h][root]) for h in pol
                                       if h >= up_h and pol[h][root]},
        "rule_continue_if_wh": _thresholds(grid, pol, up_h, end_hour),
        "action_horizon_hours": [up_h, end_hour],
        "_grid": grid, "_pol": pol, "_S": S, "_adm": adm, "_val": val,
    }


def _thresholds(grid: Grid, pol: dict, up_h: int, end_hour: int) -> dict:
    out = {}
    for h in range(up_h, end_hour):
        arr = pol[h]
        idx = np.flatnonzero(arr)
        out[str(h)] = {"theta_wh": None if idx.size == 0 else round(float(grid.soc[idx[0]]), 6),
                       "monotone_in_soc": bool(np.all(np.diff(arr.astype(int)) >= 0)),
                       "n_continue": int(arr.sum())}
    return out


# ----------------------------------------------------------------- 规则求值（全地平线）
def evaluate_rule(peak: float, up_h: int, down_h: int, rule, sigma: float = CLOUD_SIGMA,
                  quantum: float = Q_SOC, soc_root: float | None = None,
                  grid: Grid | None = None, S=None, end_hour: int = END_HOUR,
                  reserve_wh: float = 0.0, return_safe: bool = False) -> dict:
    """求值一条"第 h 小时是否继续密集"的规则。**规则被问到 `[up_h, end_hour)` 的每一小时**。

    终止是吸收态：某小时判停之后，此后一律稀疏（其安全性 = `S[h]`）。求值器不接受任何"终点"
    参数，因此隐藏授权终点无法改变执行。黄级窗口终点只决定奖励是否计数。
    """
    grid = grid or Grid(quantum)
    day_fr = tuple(sorted(set(levels(sigma))))
    S = S if S is not None else sparse_suffix_safety(grid, peak, day_fr, end_hour, reserve_wh)
    soc_root = soc_at_apply_edge(peak, up_h) if soc_root is None else soc_root
    root = int(grid.idx(soc_root))
    acts = {h: np.asarray(rule(h, grid), dtype=bool) for h in range(up_h, end_hour)}

    safe = [None] * (end_hour + 1)
    safe[end_hour] = S[end_hour].copy()
    for h in range(end_hour - 1, up_h - 1, -1):
        cont_ok = np.ones(grid.n, dtype=bool)
        for endi, alive in hour_maps(grid, h, peak, True, day_fr):
            cont_ok &= alive & safe[h + 1][endi]
        safe[h] = np.where(acts[h], cont_ok, S[h])

    P = np.zeros(grid.n)
    P[root] = 1.0
    exp_service = 0.0
    stopped_by = {}
    for h in range(up_h, end_hour):
        cont = acts[h]
        mass_cont = float(P[cont].sum())
        mass_stop = float(P[~cont].sum())
        if mass_stop > 1e-12 and not stopped_by:
            stopped_by[str(h)] = round(mass_stop, 6)
        if h < down_h:
            exp_service += OBL_PER_HOUR * mass_cont
        Q = np.zeros(grid.n)
        w = P * cont / len(day_fr)
        for endi, alive in hour_maps(grid, h, peak, True, day_fr):
            np.add.at(Q, endi, np.where(alive, w, 0.0))
        P = Q
    out = {"safe": bool(safe[up_h][root]), "expected_service_per_node": exp_service,
           "expected_dense_hours": exp_service / OBL_PER_HOUR,
           "stopped_mass_by_hour": stopped_by,
           "dense_hour_actions": {str(h): bool(acts[h][root]) for h in acts}}
    if return_safe:
        out["_safe"] = safe
    return out


# ----------------------------------------------------------------- 普通组合族（同一信息条件）
def rule_ttl(k_hours: int, up_h: int):
    """固定租约：自应用边沿起密集 k 小时。**只在第 k 小时自行停止**，不看黄级窗口终点。"""
    return lambda h, grid: np.full(grid.n, (h - up_h) < k_hours, dtype=bool)


def rule_ttl_level(k_hours: int, up_h: int, theta: float):
    """固定租约 + 电量下限：k 小时以内且测得电量不低于 theta 时继续。"""
    return lambda h, grid: ((h - up_h) < k_hours) & (grid.soc >= theta - 1e-12)


def rule_nightfloor(up_h: int, dusk_h: int = DUSK_H):
    """时钟夜门：白天一直密集到日落，日落起稀疏（不看黄级窗口终点）。"""
    return lambda h, grid: np.full(grid.n, h < dusk_h, dtype=bool)


def plan_threshold(peak: float, up_h: int, sigma: float, grid: Grid, dense_to_h: int,
                   end_hour: int = END_HOUR, reserve_wh: float = 0.0):
    """`R[i]`：自应用边沿、电量 i 起"密集到 `dense_to_h`、此后稀疏"是否在全部未来安全。

    这是实测中 `max_feasible_dense_until` 的形状：开环一次判定，判不可行即回退。它**不使用**
    黄级窗口终点（v1 的滚动门以窗口末为界，属终点泄漏，已改）。
    """
    day_fr = tuple(sorted(set(levels(sigma))))
    R = sparse_suffix_safety(grid, peak, day_fr, end_hour, reserve_wh)[dense_to_h].copy()
    for h in range(dense_to_h - 1, up_h - 1, -1):
        ok = np.ones(grid.n, dtype=bool)
        for endi, alive in hour_maps(grid, h, peak, True, day_fr):
            ok &= alive & R[endi]
        R = ok
    return R


def rule_rolling_dusk(peak: float, up_h: int, sigma: float, dusk_h: int = DUSK_H):
    """能量族候选的抽象：只要"从此刻密集到日落、之后稀疏"按名义账本仍可存活，就继续密集。

    开环判定，且**不含黄级窗口终点**；判不可行即终止。
    """
    cache: dict = {}

    def table() -> np.ndarray:
        if "v" not in cache:
            cache["v"] = plan_threshold(peak, up_h, sigma, Grid(), dusk_h)
        return cache["v"]

    return lambda h, grid: table() if h < dusk_h else np.zeros(grid.n, dtype=bool)


def rule_valid_until(up_h: int, down_h: int):
    """Task 1（升级命令携带绝对有效期）：密集恰好到预告终点。**不同信息条件，单列对照。**"""
    return lambda h, grid: np.full(grid.n, (up_h <= h < down_h), dtype=bool)


def ordinary_family(peak: float, up_h: int, down_h: int, sigma: float, grid: Grid | None = None,
                    end_hour: int = END_HOUR) -> dict:
    """声明有限族：固定租约、租约+电量下限、时钟夜门、滚动预期门（均 Task 2，同一信息条件）。

    Task 1 的 `valid_until` 单列在 `task1_reference`，**不并入**同一信息条件的比较。
    """
    grid = grid or Grid()
    day_fr = tuple(sorted(set(levels(sigma))))
    S = sparse_suffix_safety(grid, peak, day_fr, end_hour)
    cands = [(f"ttl{k}", rule_ttl(k, up_h)) for k in DEGREES]
    cands += [(f"ttl{k}+lvl{int(round(t*1e6))}u", rule_ttl_level(k, up_h, t))
              for k in DEGREES for t in THETAS]
    cands.append(("nightfloor_dusk", rule_nightfloor(up_h)))
    cands.append(("rolling_dusk_openloop", rule_rolling_dusk(peak, up_h, sigma)))
    members = []
    for name, rule in cands:
        ev = evaluate_rule(peak, up_h, down_h, rule, sigma, grid=grid, S=S, end_hour=end_hour)
        members.append({"name": name, "safe": ev["safe"],
                        "service_per_node": ev["expected_service_per_node"],
                        "dense_hours_executed": [int(k) for k, v in ev["dense_hour_actions"].items()
                                                 if v]})
    safe = [m for m in members if m["safe"]]
    best = max(safe, key=lambda m: (m["service_per_node"], m["name"])) if safe else None
    ties = sorted(m["name"] for m in safe
                  if best is not None and abs(m["service_per_node"] - best["service_per_node"]) < 1e-9)
    task1 = evaluate_rule(peak, up_h, down_h, rule_valid_until(up_h, down_h), sigma,
                          grid=grid, S=S, end_hour=end_hour)
    return {"window_hours": down_h - up_h, "n_members": len(members), "n_safe": len(safe),
            "members": sorted(members, key=lambda m: (-m["safe"], -m["service_per_node"])),
            "best": best, "best_ties": ties,
            "task1_reference": {"name": "valid_until(announced)", "safe": task1["safe"],
                                "service_per_node": task1["expected_service_per_node"],
                                "note": "不同信息条件，仅供对照，不参与同一信息条件的比较"}}


# ----------------------------------------------------------------- 全知参照（蒙特卡洛）
_OMNI_CACHE: dict = {}


def omniscient_reference(peak: float, up_h: int, down_h: int, sigma: float = CLOUD_SIGMA,
                         n_paths: int = MC_PATHS, seed: int = MC_SEED,
                         end_hour: int = END_HOUR) -> dict:
    """逐未来最优：每条路径取"仍能存活的最大密集小时数 k"，服务按 `12·min(k, 窗口长度)` 计。

    v1 把 k 直接当服务小时数，长密集段因此被高估（相位 A 窗口只有 4 h，k=10 会记成 120 条）。
     `k > W` 与 `k = W` 服务相同而负载更大，故最优 `k ≤ W`（由逐拍单调性），候选只需 `W+1` 个。

    蒙特卡洛估计，**是参照不是上界**。
    """
    key = (peak, up_h, down_h, sigma, n_paths, seed, end_hour)
    if key in _OMNI_CACHE:
        return _OMNI_CACHE[key]
    rng = np.random.default_rng(seed)
    W = down_h - up_h
    lv = levels(sigma)
    F = np.full((n_paths, end_hour), CLOUD_NOMINAL)
    for h in range(end_hour):
        if is_daylight_hour(h):
            F[:, h] = rng.choice(list(lv), size=n_paths)
    load_sp = LOAD_SPARSE_H / TICKS_PER_HOUR
    load_dn = LOAD_DENSE_H / TICKS_PER_HOUR
    sun = np.stack([hour_sun(h) for h in range(end_hour)])
    best_k = np.zeros(n_paths, dtype=int)
    for k in range(W + 1):
        dh = set(range(up_h, up_h + k))
        soc = np.full(n_paths, CAP_WH)
        mn = soc.copy()
        for h in range(end_hour):
            hv = peak * F[:, h, None] * sun[h][None, :]
            ld = load_dn if h in dh else load_sp
            for j in range(TICKS_PER_HOUR):
                soc = np.minimum(CAP_WH, soc + hv[:, j]) - ld
                np.minimum(mn, soc, out=mn)
        best_k = np.where(mn >= SAMPLE_WH, k, best_k)
    scored = np.minimum(best_k, W)
    out = {"paths": n_paths, "seed": seed, "levels": list(lv), "offset": levels_offset(sigma),
           "mean_max_dense_hours": float(best_k.mean()),
           "mean_scored_dense_hours": float(scored.mean()),
           "mean_service_per_node": float(OBL_PER_HOUR * scored.mean()),
           "p_scored_k": {str(k): float((scored == k).mean()) for k in range(W + 1)},
           "note": "per-future optimum, Monte-Carlo averaged; a reference, not an upper bound"}
    _OMNI_CACHE[key] = out
    return out


# ----------------------------------------------------------------- 可行性（先判，再谈性能）
def feasibility(peak: float, up_h: int, sigma: float) -> dict:
    """最稀疏职责是否在该不确定集合与风险口径下可行。

    **这是性能搜索的前置条件。** 负载对动作逐拍单调（密集 ≥ 稀疏），容量截断转移对电量单调，
    因此在任一固定未来里，全程稀疏的轨迹是**所有策略的上界**：它一旦破线，任何策略都破线，
    此时该口径下不存在可行策略，讨论服务差额没有意义。
    """
    tr = sparse_future(peak, up_h, sigma)
    tr_nom = sparse_future(peak, up_h, sigma, low=False)
    return {
        "sigma": sigma, "offset": levels_offset(sigma),
        "sparse_min_soc_wh_low_branch": tr["min_soc"],
        "sparse_final_soc_wh_low_branch": tr["final_soc"],
        "sparse_min_soc_wh_nominal": tr_nom["min_soc"],
        "feasible": bool(survives(tr)),
        "reason": None if survives(tr) else
                  "最稀疏职责在声明的低采能未来里已破线；由逐拍单调性，该口径下无可行策略",
    }


def critical_sigma(peak: float, up_h: int, down_h: int, kind: str = "sparse_only",
                   hi: float = 0.30, steps: int = 24, grid: Grid | None = None) -> float | None:
    """二分"仍可行的最大标准差"。返回的是 **σ**，可直接与实测 0.047 比较（v1 比的是偏移）。"""
    grid = grid or Grid()

    if kind == "sparse_only":
        def ok(s: float) -> bool:
            return bool(survives(sparse_future(peak, up_h, s)))
    else:
        W = down_h - up_h
        dense = set(range(up_h, up_h + W))

        def ok(s: float) -> bool:
            return bool(survives(schedule_worst_case(peak, up_h, s, dense)))

    if not ok(0.0):
        return None
    if ok(hi):
        return hi
    a, b = 0.0, hi
    for _ in range(steps):
        m = (a + b) / 2.0
        if ok(m):
            a = m
        else:
            b = m
    return round(a, 6)


# ----------------------------------------------------------------- 非预知性判别
def endpoint_invariance_probe(peak: float, up_h: int, down_h: int, sigma: float,
                              rule, alt_down_h: int) -> dict:
    """同一策略、同一天气，两个**不同隐藏终点**下的配置轨迹必须逐位相同。

    这正是 v1 缺的那项证据：v1 的求值器在真值终点自动降档，于是"终点的值"改变了执行。
    这里终点只进计分，因此执行轨迹必须一致；只有服务数（计分窗口不同）允许不同。
    """
    grid = Grid()
    a = evaluate_rule(peak, up_h, down_h, rule, sigma, grid=grid)
    b = evaluate_rule(peak, up_h, alt_down_h, rule, sigma, grid=grid)
    return {"true_window_end_h": down_h, "alternative_window_end_h": alt_down_h,
            "executed_dense_hours_identical": bool(a["dense_hour_actions"] == b["dense_hour_actions"]),
            "dense_hour_actions": a["dense_hour_actions"],
            "service_at_true_end": a["expected_service_per_node"],
            "service_at_alternative_end": b["expected_service_per_node"],
            "note": "终点只影响计分，不影响执行；配置与能耗轨迹必须一致"}


def hidden_endpoint_counterexample(peak: float, up_h: int, down_h: int, sigma: float) -> dict:
    """独立反例：把 `TTL8+8 mWh 门`做**物理执行**（跑到它自己的结束时刻，不在真值终点降档），
    在声明集合的低采能未来里看最低电量。v1 在 h6 处替它降档，因而漏掉了这个后果。"""
    d = levels_offset(sigma)
    f = {h: CLOUD_NOMINAL for h in range(up_h)}
    f.update({h: CLOUD_NOMINAL - d for h in range(up_h, END_HOUR) if is_daylight_hour(h)})
    soc = CAP_WH
    for h in range(up_h):
        soc, _ = hour_step(soc, h, False, CLOUD_NOMINAL, peak)
    dense_hours, mn, stopped = [], soc, None
    for h in range(up_h, END_HOUR):
        dense = (stopped is None) and (h - up_h) < 8 and soc >= 0.008
        if not dense and stopped is None:
            stopped = h
        if dense:
            dense_hours.append(h)
        soc, hm = hour_step(soc, h, dense, f.get(h, 1.0), peak)
        mn = min(mn, hm)
    # 同一见证在 v1 的偏移约定（δ = σ）下必须复现独立审阅报告的值 0.3295257 mWh
    f_v1 = {h: (CLOUD_NOMINAL if h < up_h else CLOUD_NOMINAL - sigma) for h in range(END_HOUR)}
    soc_v1 = CAP_WH
    for h in range(up_h):
        soc_v1, _ = hour_step(soc_v1, h, False, CLOUD_NOMINAL, peak)
    mn_v1, stopped_v1 = soc_v1, None
    for h in range(up_h, END_HOUR):
        dense = (stopped_v1 is None) and (h - up_h) < 8 and soc_v1 >= 0.008
        if not dense and stopped_v1 is None:
            stopped_v1 = h
        soc_v1, hm = hour_step(soc_v1, h, dense, f_v1.get(h, 1.0), peak)
        mn_v1 = min(mn_v1, hm)
    return {"rule": "ttl8+lvl8000u, executed to its own stop (no truncation at the true end)",
            "dense_hours_executed": dense_hours,
            "stopped_at_hour": stopped,
            "min_soc_wh_low_branch": mn,
            "declared_safety_floor_wh": SAMPLE_WH,
            "safe_under_low_branch": bool(mn >= SAMPLE_WH),
            "min_soc_wh_low_branch_v1_offset_convention": mn_v1,
            "v1_offset_convention_matches_review": bool(abs(mn_v1 - 0.0003295257) < 1e-9)}


def policy_window_invariance(peak: float, up_h: int, down_h: int, sigma: float,
                             alt_down_h: int) -> dict:
    """**同一策略**在两个不同计分窗口终点下的规则表必须逐位相同。

    审阅要求"不能逐终点重新解一个策略再称非预知"。这里直接核对：用两个终点各解一次 DP，
    比较整张规则表（不是只看根状态）。相同即说明该策略不依赖终点；若不同，必须如实报告
    （那意味着策略用到了计分窗口这一公开任务参数，需要在口径里声明）。
    """
    a = solve_nonprescient(peak, up_h, down_h, sigma)
    b = solve_nonprescient(peak, up_h, alt_down_h, sigma)
    shared = [h for h in a["_pol"] if h in b["_pol"]]
    same = all(np.array_equal(a["_pol"][h], b["_pol"][h]) for h in shared)
    return {"window_end_h": down_h, "alternative_window_end_h": alt_down_h,
            "hours_compared": len(shared), "rule_table_bit_identical": bool(same),
            "root_actions": {"at_%d" % down_h: {str(h): bool(a["_pol"][h][a["root_idx"]])
                                                for h in shared if a["_pol"][h][a["root_idx"]]},
                             "at_%d" % alt_down_h: {str(h): bool(b["_pol"][h][b["root_idx"]])
                                                    for h in shared if b["_pol"][h][b["root_idx"]]}}}


def never_stop_is_not_free(peak: float, up_h: int, down_h: int, sigma: float) -> dict:
    """v1 缺陷的最小见证：规则从不主动终止时，安全判定必须反映**它真的不终止**。"""
    ev = evaluate_rule(peak, up_h, down_h, lambda h, g: np.ones(g.n, dtype=bool), sigma)
    d = levels_offset(sigma)
    f = {h: (CLOUD_NOMINAL if h < up_h else CLOUD_NOMINAL - d) for h in range(END_HOUR)}
    tr = path_trace(CAP_WH, range(up_h, END_HOUR), f, peak)
    return {"rule": "always continue dense over the whole horizon",
            "evaluator_safe": ev["safe"],
            "evaluator_service_per_node": ev["expected_service_per_node"],
            "true_min_soc_wh_low_branch": tr["min_soc"],
            "true_safe_under_low_branch": bool(survives(tr)),
            "agree": bool(ev["safe"] == survives(tr))}


def sparse_dominance_witness(peak: float, up_h: int, sigma: float, n: int = 8,
                             seed: int = 7) -> dict:
    """逐拍单调性的数值见证：任一未来的任一时刻，全程稀疏的电量都不低于任何密集安排的。

    这是"稀疏已破线 ⇒ 无可行策略"这条推论的依据，因此必须给出凭据而不是断言。
    """
    rng = np.random.default_rng(seed)
    lv = list(levels(sigma))
    worst = 0.0
    for _ in range(n):
        f = {h: float(rng.choice(lv)) for h in range(up_h, END_HOUR) if is_daylight_hour(h)}
        sp = path_trace(CAP_WH, (), f, peak)
        dn = path_trace(CAP_WH, range(up_h, min(up_h + 4, END_HOUR)), f, peak)
        worst = max(worst, max(0.0, dn["min_soc"] - sp["min_soc"]))
    return {"trials": n, "max_dense_minus_sparse_min_soc_wh": worst,
            "monotone_as_claimed": bool(worst <= 1e-12)}


# ----------------------------------------------------------------- 可手算核例
CORE = dict(peak=0.012, up_h=2, down_h=4, sigma=0.047, quantum=1e-4, end_hour=4,
            soc_edge=0.0025, reserve_wh=0.0021,
            note="仪器检查实例：核对 DP 递推，并证明仪器在存在可实现差额时有分辨力")


def reachable_states(peak: float, up_h: int, down_h: int, sigma: float, grid: Grid,
                     soc_root: float, end_hour: int) -> dict:
    """每个决策小时上有正概率到达的网格状态（规则只在这些格上被问到）。"""
    day_fr = tuple(sorted(set(levels(sigma))))
    states = {up_h: {int(grid.idx(soc_root))}}
    for h in range(up_h, end_hour - 1):
        nxt = set()
        for i in sorted(states[h]):
            for dense in (False, True):
                for endi, _alive in hour_maps(grid, h, peak, dense, day_fr):
                    nxt.add(int(endi[i]))
        states[h + 1] = nxt
    return states


def brute_force_reachable(peak: float, up_h: int, down_h: int, sigma: float, grid: Grid,
                          soc_root: float, end_hour: int, reserve_wh: float = 0.0) -> dict:
    """在可达决策格上穷举每一条规则，独立核对 DP（规模由可达格数决定，与网格分辨率无关）。"""
    day_fr = tuple(sorted(set(levels(sigma))))
    S = sparse_suffix_safety(grid, peak, day_fr, end_hour, reserve_wh)
    states = reachable_states(peak, up_h, down_h, sigma, grid, soc_root, end_hour)
    cells = [(h, i) for h in range(up_h, end_hour) for i in sorted(states[h])]
    best, n_safe = None, 0
    for mask in range(1 << len(cells)):
        on = {(h, i) for b, (h, i) in enumerate(cells) if (mask >> b) & 1}

        def rule(h, g, on=on):
            arr = np.zeros(g.n, dtype=bool)
            for (hh, ii) in on:
                if hh == h:
                    arr[ii] = True
            return arr

        ev = evaluate_rule(peak, up_h, down_h, rule, sigma, grid=grid, S=S,
                           soc_root=soc_root, end_hour=end_hour, reserve_wh=reserve_wh)
        if ev["safe"]:
            n_safe += 1
            if best is None or ev["expected_service_per_node"] > best["service_per_node"]:
                best = {"mask": mask, "service_per_node": ev["expected_service_per_node"],
                        "continue_at": sorted([list(c) for c in on])}
    return {"n_cells": len(cells), "cells": [list(c) for c in cells],
            "enumerated_rules": 1 << len(cells), "safe_rules": n_safe, "best": best,
            "reachable_states_by_hour": {str(h): sorted(states[h]) for h in states}}


def core_instance(verbose: bool = False) -> dict | None:
    p = CORE
    grid = Grid(p["quantum"])
    E = p["end_hour"]
    root_soc = p["soc_edge"]
    bf = brute_force_reachable(p["peak"], p["up_h"], p["down_h"], p["sigma"], grid,
                               root_soc, E, p["reserve_wh"])
    dp = solve_nonprescient(p["peak"], p["up_h"], p["down_h"], p["sigma"],
                            quantum=p["quantum"], soc_root=root_soc, grid=grid, end_hour=E,
                            reserve_wh=p["reserve_wh"])
    dpv = dp["expected_service_per_node"] if dp["admissible"] else 0.0
    best_ttl = None
    for k in range(1, E - p["up_h"] + 1):
        ev = evaluate_rule(p["peak"], p["up_h"], p["down_h"], rule_ttl(k, p["up_h"]),
                           p["sigma"], quantum=p["quantum"], grid=grid, soc_root=root_soc,
                           end_hour=E, reserve_wh=p["reserve_wh"])
        if ev["safe"] and (best_ttl is None or ev["expected_service_per_node"] > best_ttl[1]):
            best_ttl = (k, ev["expected_service_per_node"])
    out = {"declared": {k: v for k, v in p.items()}, "level_factors": list(levels(p["sigma"])),
           "level_offset": levels_offset(p["sigma"]),
           "level_std_check": float(np.std(levels(p["sigma"]))),
           "hour_clear_wh": round(hour_clear_wh(p["up_h"], p["peak"]), 8),
           "hour_load_wh": {"sparse": LOAD_SPARSE_H, "dense": LOAD_DENSE_H},
           "cap_wh": CAP_WH, "sample_wh": SAMPLE_WH,
           "soc_edge_wh": root_soc, "reserve_wh": p["reserve_wh"],
           "brute_force": bf,
           "dp": {"admissible": dp["admissible"], "service_per_node": dpv,
                  "expected_dense_hours": dp["expected_dense_hours"],
                  "continue_if": dp["rule_continue_if_wh"]},
           "best_safe_ttl": {"k": best_ttl[0], "service_per_node": best_ttl[1]} if best_ttl else None,
           "dp_matches_brute_force": bool(bf["best"] is not None and dp["admissible"]
                                          and abs(bf["best"]["service_per_node"] - dpv) < 1e-9)}
    if verbose:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    return out


# ----------------------------------------------------------------- 单元
def cell(phase: str, peak: float, sigma: float) -> dict:
    p = PHASES[phase]
    up_h, down_h = p["up_h"], p["down_h"]
    W = down_h - up_h
    feas = feasibility(peak, up_h, sigma)
    out = {"phase": phase, "peak_wh_per_h": peak, "sigma": sigma,
           "offset": levels_offset(sigma),
           "window_hours": W, "window_obligations_per_node": OBL_PER_HOUR * W,
           "window_obligations_network_per_seed": OBL_PER_HOUR * W * NODES,
           "soc_at_apply_edge": round(soc_at_apply_edge(peak, up_h), 6),
           "feasibility": feas,
           "critical_sigma": {"sparse_only": critical_sigma(peak, up_h, down_h, "sparse_only"),
                              "full_window_lease": critical_sigma(peak, up_h, down_h, "full_window"),
                              "measured_sigma": CLOUD_SIGMA}}
    if not feas["feasible"]:
        out.update({"status": "infeasible",
                    "nonprescient": {"admissible": False, "service_per_node": None},
                    "ordinary": {"name": None, "service_per_node": None},
                    "omniscient": None, "gaps": None})
        return out

    grid = Grid()
    day_fr = tuple(sorted(set(levels(sigma))))
    S = sparse_suffix_safety(grid, peak, day_fr)
    root_soc = soc_at_apply_edge(peak, up_h)
    dp = solve_nonprescient(peak, up_h, down_h, sigma, grid=grid, soc_root=root_soc)
    dp_rule = (lambda h, g, pol=dp["_pol"]: pol[h] if h in pol else np.zeros(g.n, dtype=bool))
    ver = evaluate_rule(peak, up_h, down_h, dp_rule, sigma, grid=grid, S=S, soc_root=root_soc)
    dp_svc = dp["expected_service_per_node"] if dp["admissible"] else None
    fam = ordinary_family(peak, up_h, down_h, sigma, grid=grid)
    omni = omniscient_reference(peak, up_h, down_h, sigma)
    ord_svc = fam["best"]["service_per_node"] if fam["best"] else None
    omni_svc = omni["mean_service_per_node"]
    gaps = None
    if dp_svc is not None and ord_svc is not None:
        gaps = {"implementable_strategy_per_node": dp_svc - ord_svc,
                "information_per_node": omni_svc - dp_svc,
                "total_per_node": omni_svc - ord_svc,
                "protection_cost_per_node": OBL_PER_HOUR * W - dp_svc,
                "identity_residual": (omni_svc - dp_svc) + (dp_svc - ord_svc)
                                     - (omni_svc - ord_svc)}
    out.update({
        "status": "feasible",
        "nonprescient": {"admissible": dp["admissible"], "service_per_node": dp_svc,
                         "expected_dense_hours": dp["expected_dense_hours"],
                         "rule_continue_if_wh": dp["rule_continue_if_wh"],
                         "action_horizon_hours": dp["action_horizon_hours"],
                         "selfcheck_service_agrees": (dp_svc is not None and
                                                      abs(ver["expected_service_per_node"]
                                                          - dp_svc) < 1e-9)},
        "ordinary": {"name": fam["best"]["name"] if fam["best"] else None,
                     "service_per_node": ord_svc, "best_ties": fam["best_ties"],
                     "n_safe_of": [fam["n_safe"], fam["n_members"]],
                     "candidates": fam["members"],
                     "task1_reference": fam["task1_reference"]},
        "omniscient": omni,
        "gaps": gaps,
    })
    return out


def main() -> int:
    if "--core" in sys.argv:
        core_instance(verbose=True)
        return 0
    only_feas = "--feasibility" in sys.argv
    out = {
        "contract": "spec/prereg-nonprescient-sequence-v2.md",
        "supersedes": {
            "pre_registration": "spec/prereg-nonprescient-sequence-v1.md",
            "result": "results/c5_seqref_v1_semantics.json",
            "reason": "v1 的求值器在真值终点自动降档（隐藏终点改变了执行）；且等权三点的实际"
                      "标准差只有声明值的 sqrt(2/3)。独立审阅见 "
                      "反例已由 audit_seqref.py 与 results/c5_seqref.json 的 counterexamples "
                      "字段随仓库复现，归档见 results/_withdrawn/2026-09-20-c9-v1-semantics.md",
        },
        "model": {
            "constants": {"cap_wh": CAP_WH, "sample_wh": SAMPLE_WH,
                          "load_sparse_wh_per_h": LOAD_SPARSE_H,
                          "load_dense_wh_per_h": LOAD_DENSE_H,
                          "cloud_nominal": CLOUD_NOMINAL, "cloud_sigma": CLOUD_SIGMA,
                          "obligations_per_node_hour": OBL_PER_HOUR, "nodes": NODES,
                          "end_hour": END_HOUR, "quantum_wh": Q_SOC,
                          "mc_paths": MC_PATHS, "mc_seed": MC_SEED},
            "action_space": "自应用边沿到地平线的每一小时：继续密集 | 终止（吸收，此后永久稀疏）",
            "information_set": "(相对小时, 量化剩余电量)；不含未来采能、授权终点、中心在线状态；"
                               "黄级窗口终点只用于计分，不进入执行",
            "risk": "声明全部未来下均不死亡（任一拍 soc < sample_wh 即判死，环境口径）",
            "objective": "期望服务 = 12 × 窗口内期望密集小时数；不得删除义务",
            "boundaries": [
                "服务 = 黄级义务被采集，不含投递链路折损（实测采集 535/672、投递 283/672）",
                "云遮按小时取因子（逐拍抖动被抹掉）；三点等权离散，偏移 = σ·sqrt(3/2) 以匹配 σ",
                "单节点切片，不含多节点竞争、网关打包与回传",
                "起始电量取满值（实测 initial_soc=1.0）",
                "动作能力限于一次租约；不含重入与单次采样控制",
            ],
        },
        "peaks": list(PEAKS), "sigmas": list(SIGMAS),
        "cells": {}, "counterexamples": {}, "endpoint_invariance": {}, "core": core_instance(),
    }
    up_a, dn_a = PHASES["A"]["up_h"], PHASES["A"]["down_h"]
    out["counterexamples"]["never_stop_is_not_free"] = never_stop_is_not_free(
        0.012, up_a, dn_a, CLOUD_SIGMA)
    out["counterexamples"]["ttl8_physical_execution"] = hidden_endpoint_counterexample(
        0.012, up_a, dn_a, CLOUD_SIGMA)
    out["counterexamples"]["sparse_dominance"] = sparse_dominance_witness(0.012, up_a, CLOUD_SIGMA)
    out["endpoint_invariance"]["ttl8_alt_window_end"] = endpoint_invariance_probe(
        0.012, up_a, dn_a, CLOUD_SIGMA, rule_ttl_level(8, up_a, 0.008), 10)
    # 可行峰值上：同一 DP 策略在两个计分窗口终点下的规则表必须逐位相同
    out["endpoint_invariance"]["dp_policy_alt_window_end_peak016"] = policy_window_invariance(
        0.016, up_a, dn_a, CLOUD_SIGMA, 10)
    print("独立反例与不变性：")
    ns = out["counterexamples"]["never_stop_is_not_free"]
    print(f"  never-stop 规则：求值器判定安全={ns['evaluator_safe']}  "
          f"真实低档安全={ns['true_safe_under_low_branch']}  两者一致={ns['agree']}")
    hc = out["counterexamples"]["ttl8_physical_execution"]
    print(f"  TTL8 物理执行：dense={hc['dense_hours_executed']}  停止于 h{hc['stopped_at_hour']}  "
          f"min_soc={hc['min_soc_wh_low_branch']:.10f} Wh  安全={hc['safe_under_low_branch']}")
    sd = out["counterexamples"]["sparse_dominance"]
    print(f"  稀疏逐拍占优见证：max(dense−sparse)={sd['max_dense_minus_sparse_min_soc_wh']:.3e} Wh  "
          f"成立={sd['monotone_as_claimed']}")
    ei = out["endpoint_invariance"]["ttl8_alt_window_end"]
    print(f"  跨隐藏终点执行一致（真值 6h vs 10h）：{ei['executed_dense_hours_identical']}")
    dp_ei = out["endpoint_invariance"]["dp_policy_alt_window_end_peak016"]
    print(f"  可行峰值上 DP 规则表对终点不变（比较 {dp_ei['hours_compared']} 个小时）："
          f"{dp_ei['rule_table_bit_identical']}")
    print()

    for phase in PHASES:
        for peak in PEAKS:
            for sig in SIGMAS:
                c = cell(phase, peak, sig)
                out["cells"][f"{phase}|{peak}|{sig}"] = c
                if c["status"] == "infeasible":
                    print(f"{phase} p={peak:<6} sigma={sig:<6} **不可行**：稀疏最低 "
                          f"{c['feasibility']['sparse_min_soc_wh_low_branch']*1000:+.5f} mWh  "
                          f"(临界 sigma={c['critical_sigma']['sparse_only']})")
                else:
                    g = c["gaps"]
                    gs = "None" if g is None else f"{g['implementable_strategy_per_node']:+7.2f}"
                    gi = "None" if g is None else f"{g['information_per_node']:+7.2f}"
                    print(f"{phase} p={peak:<6} sigma={sig:<6} "
                          f"DP={c['nonprescient']['service_per_node']} "
                          f"ORD={c['ordinary']['service_per_node']}({c['ordinary']['name']}) "
                          f"可实现={gs} 信息={gi}")
    os.makedirs(os.path.join(REPO, "results"), exist_ok=True)
    path = os.path.join(REPO, "results", "c5_seqref.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("\nsaved", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
