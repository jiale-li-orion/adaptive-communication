# -*- coding: utf-8 -*-
"""c5_seqref.py — 三方判别中的**中间行**：同信息、非预知的序列优化参照。

口径（v3）

本文件按 `spec/prereg-nonprescient-sequence-v3.md` 实现。v1 与 v2 的两处契约错误已由独立审阅
给出可直接运行的反例，v3 又修正了 v2 的两处**层级**错误：

  * **v2 把"零失电"当成了任务要求。** 仓库自己的来源不支持这个层级：论文目标函数写明
    "计三项：按期交付的义务（服务）、**节点永久死亡**、以及……浪费"——死亡是**被计价的项**；
    论文的评测按臂报告（服务, 死亡）（A1 死亡 4、A0 死亡 35、A0s 死亡 39）而不是把它当准入条件；
    `v3joint_r02_restart.json` 记录"0 存活主要是吸收态产物"（开环复机后采集 .41→.82）；
    登记表里 r47 也已写明不得把所测臂的结果外推成"全部合法策略物理不可行"。
    因此 v3 把风险口径放回**参数层**：`strict`（全部声明未来存活）只是该层的一个端点，
    **主口径**是与论文一致的**计价**（`priced`，死亡罚 λ），并报告 (服务, 死亡概率, 裕度)。
  * **v2 的"序列优化"是空的。** 奖励非负（窗口内 12、窗口外 0）、终止是吸收态且值为 0、
    又没有死亡代价时，"只要还能安全多跑一小时就继续"**恒**弱占优，于是精确最优**恰好等于**
    贪心可行性规则——DP 里没有任何序列内容。v3 用计价恢复真正的取舍：λ>0 时继续要付死亡风险，
    最优规则是状态相关的**停止规则**，不再等于可行性判据（两者都由 `degeneracy_witness` 直接核对）。

v1/v2/v3 的关系：v1、v2 的原文与结果都保留（`…-v1.md`、`…-v2.md`、
`results/c5_seqref_v1_semantics.json`、`results/c5_seqref_v2_semantics.json`），
撤回与取代理由记入 `results/_withdrawn/`。

三条纪律
--------
1. **同一信息**：策略只用 `(相对小时, 量化剩余电量)`，不含未来采能、授权终点、中心在线状态。
   黄级窗口终点只用于计分，不进入执行——动作定义在整个地平线 `[应用边沿, 49h)` 上。
2. **同一动作能力**：密集/稀疏两档，一次租约、降回稀疏不得重入（回传中断期间无新授权）。
3. **同一风险口径**：参与比较的所有行必须用同一个 `(risk_mode, death_penalty)`；口径本身是声明的
   参数并被扫描，不允许为了得到差额而回调。

台账同源
--------
逐拍递推与环境同序（`network.py:_step_power`：`x[k] = min(CAP, x[k-1] + h[k]) - l[k]`）。
容量 50 mWh、单次采样 0.47 mWh、每小时采样数 ×（采样 + 单次上报射频）= 稀疏 3.005943、
密集 6.011886 mWh/h；采能 `peak·f·sin(π·rel/12)/60` 每拍；小时因子均值 0.7375、标准差 0.047
（实测 0.0452（280 样本）、理论 0.0462），等权三点离散、偏移 `= σ·√(3/2)`。
实测与校准见 `code/experiments/measure_seqref_calibration.py` 与
`results/reference/c5_seqref_calibration.json`。

截断边界（引用结论时必须同时引用）
----------------------------------
服务 = 黄级义务**被采集**而非被投递（实测采集 535/672、投递 283/672）；云遮按小时取因子；
单节点切片；动作限于一次租约；起始电量取满值。

跑法
----
    python3 code/v3joint/c5_seqref.py            # 写 results/c5_seqref.json
    python3 code/v3joint/c5_seqref.py --core     # 手算核例的全部算术
    python3 code/v3joint/c5_seqref.py --strict   # 只报 strict 口径的可行性
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))

TICK_S = 60
TICKS_PER_HOUR = 3600 // TICK_S
CAP_WH = 0.05
SAMPLE_WH = 4.7e-4
RADIO_WH_PER_REPORT = 3.099046e-5
LOAD_SPARSE_H = 6 * (SAMPLE_WH + RADIO_WH_PER_REPORT)
LOAD_DENSE_H = 12 * (SAMPLE_WH + RADIO_WH_PER_REPORT)
SUNRISE_H = 6.0
DAYLIGHT_H = 12.0
END_HOUR = 49
Q_SOC = 1e-5
CLOUD_NOMINAL = 0.7375
CLOUD_SIGMA = 0.047
PHASES = {"A": dict(up_h=2, down_h=6), "B": dict(up_h=1, down_h=8)}
OBL_PER_HOUR = 12
NODES = 14
MC_PATHS = 4000
MC_SEED = 20260920
PEAKS = (0.010, 0.012, 0.016, 0.030)
SIGMAS = (0.0, 0.0308, 0.0452, 0.047, 0.06)
DEGREES = (2, 4, 6, 7, 8, 10, 12)
THETAS = (0.0, 0.002, 0.004, 0.008)
DUSK_H = 12
#: 风险口径层。`strict` = 声明全部未来存活（v2 的口径，只作端点报告）；
#: `priced` = 与论文目标函数一致：服务按条计、死亡按次罚 λ。λ 的单位是"条黄级义务"。
RISK_MODES = ("strict", "priced")
DEATH_PENALTIES = (0.0, 12.0, 48.0, 192.0, 768.0)
PRIMARY_LAMBDA = 48.0


# ----------------------------------------------------------------- 层级的依据（写进结果，不靠断言）
def task_semantics_evidence() -> dict:
    """"零失电"属于哪一层：仓库自身来源的核对结果。

    结论：死亡在论文目标函数里是**被计价的项**，在评测里是**被报告的读数**；把它提升成
    "全部未来不得死亡"的任务要求，现有场景来源不支持。因此 v3 把它放在**风险口径参数层**，
    而不是任务要求层。
    """
    return {
        "paper_objective": {
            "where": "paper/zh/main.tex §系统模型（目标函数段）",
            "text": "目标函数计三项：按期交付的义务（服务）、节点永久死亡、以及存活超过释放时刻的"
                    "状态所占资源——浪费的样本、接入尝试、短报文字节与能量。",
            "reading": "死亡是被计价的第三项，不是准入约束",
        },
        "paper_reporting": {
            "where": "paper/zh/main.tex §执行位置决定存活",
            "text": "A1 平均服务 0.358…死亡 4；A0 为 0.296、死亡 35；A0s 为 0.222、死亡 39",
            "reading": "死亡按臂报告、与服务并列，且明确写了小样本下不就服务作显著性判断",
        },
        "restart_experiment": {
            "where": "results/README.md 登记 `v3joint_r02_restart.json`"
                     "（`code/v3joint/r02_restart_compare.py`）",
            "text": "复机后采集率 .41→.82、服务 .06→.27，证明 0 存活主要是吸收态产物",
            "reading": "永久死亡是建模约定且有已知敏感性，不是已确立的任务要求",
        },
        "no_extrapolation_rule": {
            "where": "results/README.md 登记 `r47_lease_energy.json`",
            "text": ".01 各被测臂 dead=40，不能外推为全部合法稀疏策略的物理不可行",
            "reading": "仓库已有先例：所测臂的失败不得上升为物理不可行；本文件的 strict 结论"
                       "虽然由逐拍单调性给出（比外推更强），仍只在该风险口径内成立",
        },
        "placement_decision": {
            "risk_layer": "risk_mode + death_penalty，被扫描、被报告；strict 只是端点",
            "task_layer": "不设零死亡硬约束；死亡按次计价并按概率报告，与论文一致",
            "not_done": "没有为了得到非零差额而回调 λ 或缩小不确定集合",
        },
    }


# ----------------------------------------------------------------- 时间与采能
def offset_of(sigma: float) -> float:
    """等权三点 `{μ−δ, μ, μ+δ}` 的实际标准差是 `δ·sqrt(2/3)`；反解得 `δ = σ·sqrt(3/2)`。"""
    return float(sigma) * math.sqrt(1.5)


def levels(sigma: float) -> tuple[float, ...]:
    if sigma <= 0.0:
        return (CLOUD_NOMINAL,)
    d = offset_of(sigma)
    return (CLOUD_NOMINAL - d, CLOUD_NOMINAL, CLOUD_NOMINAL + d)


def levels_offset(sigma: float) -> float:
    return 0.0 if sigma <= 0.0 else offset_of(sigma)


def sun_frac(t_s: float) -> float:
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
    load = (LOAD_DENSE_H if dense else LOAD_SPARSE_H) / TICKS_PER_HOUR
    soc = min(CAP_WH, float(soc0))
    mn = soc
    for hk in hour_sun(hour) * peak * factor:
        soc = min(CAP_WH, soc + float(hk))
        soc -= load
        mn = min(mn, soc)
    return soc, mn


def path_trace(soc0: float, dense_hours, factors: dict[int, float], peak: float,
               end_hour: int = END_HOUR, stop_at_death: bool = False) -> dict:
    """整条轨迹。`stop_at_death=True` 时首次破线即停（用于计价口径下的服务计数）。"""
    dense_hours = set(dense_hours)
    soc, mn = float(soc0), float(soc0)
    ends, dead_at, served = {}, None, []
    hour = 0
    while hour < end_hour:
        f = factors.get(hour, CLOUD_NOMINAL) if is_daylight_hour(hour) else 1.0
        if soc < SAMPLE_WH:
            dead_at = hour
            if stop_at_death:
                break
        if hour in dense_hours:
            served.append(hour)
        soc, hm = hour_step(soc, hour, hour in dense_hours, f, peak)
        mn = min(mn, hm)
        ends[hour] = soc
        hour += 1
    return {"min_soc": mn, "final_soc": soc, "hour_end": ends, "dead_at_hour": dead_at,
            "served_dense_hours_before_death": served}


def survives(trace: dict) -> bool:
    return trace["min_soc"] >= SAMPLE_WH


def soc_at_apply_edge(peak: float, up_h: int, past_factor: float = CLOUD_NOMINAL,
                      soc0: float = CAP_WH) -> float:
    tr = path_trace(soc0, (), {h: past_factor for h in range(up_h)}, peak, end_hour=up_h)
    return tr["hour_end"].get(up_h - 1, soc0)


def worst_future_factors(up_h: int, sigma: float, low: bool = True) -> dict:
    d = levels_offset(sigma)
    if not low:
        return {h: CLOUD_NOMINAL for h in range(END_HOUR)}
    f = {h: CLOUD_NOMINAL for h in range(up_h)}
    f.update({h: CLOUD_NOMINAL - d for h in range(up_h, END_HOUR) if is_daylight_hour(h)})
    return f


def schedule_worst_case(peak: float, up_h: int, sigma: float, dense_hours, soc0: float = CAP_WH,
                        past_factor: float = CLOUD_NOMINAL) -> dict:
    """确定性时刻表在声明全部未来下的最坏轨迹（全低档是逐点最小未来，精确而非抽样）。"""
    return path_trace(soc0, dense_hours, worst_future_factors(up_h, sigma), peak)


def sparse_future(peak: float, up_h: int, sigma: float, soc0: float = CAP_WH,
                  low: bool = True) -> dict:
    return path_trace(soc0, (), worst_future_factors(up_h, sigma, low), peak)


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


_PD_CACHE: dict = {}


def sparse_death_prob(grid: Grid, peak: float, factors, end_hour: int = END_HOUR):
    """`Pd[h][i]`：自第 h 小时、电量 i 起**永不密集**时，此后在声明分布下死亡的概率。

    计价口径需要它：停止密集并不等于免疫失电，稀疏职责本身仍可能在坏未来里破线。
    """
    key = (grid.n, grid.q, round(peak, 12), tuple(sorted(set(factors))), end_hour)
    if key in _PD_CACHE:
        return _PD_CACHE[key]
    Pd = [None] * (end_hour + 1)
    Pd[end_hour] = np.zeros(grid.n)
    for h in range(end_hour - 1, -1, -1):
        fr = tuple(sorted(set(factors))) if is_daylight_hour(h) else (1.0,)
        acc = np.zeros(grid.n)
        for endi, alive in hour_maps(grid, h, peak, False, fr):
            acc += np.where(alive, Pd[h + 1][endi], 1.0) / len(fr)
        Pd[h] = acc
    _PD_CACHE[key] = Pd
    return Pd


# ----------------------------------------------------------------- 非预知 DP
def solve_nonprescient(peak: float, up_h: int, down_h: int, sigma: float = CLOUD_SIGMA,
                       quantum: float = Q_SOC, soc_root: float | None = None,
                       grid: Grid | None = None, end_hour: int = END_HOUR,
                       reserve_wh: float = 0.0, risk_mode: str = "priced",
                       death_penalty: float = PRIMARY_LAMBDA) -> dict:
    """声明动作族内的非预知精确最优。动作覆盖 `[up_h, end_hour)`；终止为吸收态。

    `risk_mode="strict"`：只允许"每个声明未来都存活且子状态仍可续行"的动作（v2 口径，端点）。
    `risk_mode="priced"`：不设安全约束，死亡按 `death_penalty` 计价（与论文目标函数一致）。
    """
    if risk_mode not in RISK_MODES:
        raise ValueError(risk_mode)
    grid = grid or Grid(quantum)
    day_fr = tuple(sorted(set(levels(sigma))))
    soc_root = soc_at_apply_edge(peak, up_h) if soc_root is None else soc_root
    S = sparse_suffix_safety(grid, peak, day_fr, end_hour, reserve_wh)
    Pd = sparse_death_prob(grid, peak, day_fr, end_hour)
    root = int(grid.idx(soc_root))
    lam = float(death_penalty) if risk_mode == "priced" else math.inf

    adm = [None] * (end_hour + 1)
    val = [None] * (end_hour + 1)
    pol: dict[int, np.ndarray] = {}
    adm[end_hour] = S[end_hour].copy()
    val[end_hour] = np.where(adm[end_hour], 0.0, -np.inf) if risk_mode == "strict" \
        else np.zeros(grid.n)
    for h in range(end_hour - 1, up_h - 1, -1):
        reward = OBL_PER_HOUR if h < down_h else 0
        if risk_mode == "strict":
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
        else:
            acc = np.zeros(grid.n)
            for endi, alive in hour_maps(grid, h, peak, True, day_fr):
                acc += np.where(alive, val[h + 1][endi], -lam) / len(day_fr)
            cont_val = reward + acc
            stop_val = -lam * Pd[h]
            pol[h] = cont_val > stop_val
            adm[h] = np.ones(grid.n, dtype=bool)
            val[h] = np.maximum(cont_val, stop_val)
    ok = bool(adm[up_h][root]) if risk_mode == "strict" else True
    return {
        "risk_mode": risk_mode, "death_penalty": (None if risk_mode == "strict" else lam),
        "sigma": sigma, "levels": list(day_fr), "offset": levels_offset(sigma),
        "quantum": grid.q, "grid_n": grid.n, "soc_root": soc_root, "root_idx": root,
        "feasible_under_strict": bool(adm[up_h][root]) if risk_mode == "strict" else None,
        "expected_service_per_node": (float(val[up_h][root]) if risk_mode == "strict" else None),
        "objective_value": float(val[up_h][root]),
        "rule_continue_if_wh": _thresholds(grid, pol, up_h, end_hour),
        "action_horizon_hours": [up_h, end_hour],
        "_grid": grid, "_pol": pol, "_S": S, "_Pd": Pd, "_adm": adm, "_val": val,
        "_root": root, "_up": up_h,
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


def greedy_rule(grid: Grid, peak: float, sigma: float, up_h: int, end_hour: int,
                reserve_wh: float = 0.0) -> dict:
    """"只要还能安全多跑一小时就继续"的贪心可行性规则（λ=0、计价口径下的精确最优）。"""
    day_fr = tuple(sorted(set(levels(sigma))))
    S = sparse_suffix_safety(grid, peak, day_fr, end_hour, reserve_wh)
    adm = [None] * (end_hour + 1)
    adm[end_hour] = S[end_hour].copy()
    cont = {}
    for h in range(end_hour - 1, up_h - 1, -1):
        ok = np.ones(grid.n, dtype=bool)
        for endi, alive in hour_maps(grid, h, peak, True, day_fr):
            ok &= alive & adm[h + 1][endi]
        cont[h] = ok
        adm[h] = ok | S[h]
    return cont


def degeneracy_witness(peak: float, up_h: int, down_h: int, sigma: float,
                       lam: float = PRIMARY_LAMBDA) -> dict:
    """序列内容是否为空：λ=0 的计价最优是否**恰好等于**贪心可行性规则；λ>0 时是否不再相等。

    这是 v2 的"序列优化"实际为空的直接见证，也是 v3 用计价恢复取舍的直接见证。
    """
    grid = Grid()
    cont = greedy_rule(grid, peak, sigma, up_h, END_HOUR)
    never = {h: np.ones(grid.n, dtype=bool) for h in range(up_h, END_HOUR)}
    strict = solve_nonprescient(peak, up_h, down_h, sigma, grid=grid, risk_mode="strict")
    free = solve_nonprescient(peak, up_h, down_h, sigma, grid=grid, risk_mode="priced",
                              death_penalty=0.0)
    priced = solve_nonprescient(peak, up_h, down_h, sigma, grid=grid, risk_mode="priced",
                                death_penalty=lam)

    def same(pol, ref):
        return all(np.array_equal(pol[h], ref[h]) for h in ref if h in pol)

    return {
        "strict_mode_equals_greedy_feasibility": bool(same(strict["_pol"], cont)),
        "priced_lambda_0_equals_never_stop": bool(same(free["_pol"], never)),
        "priced_lambda_0_equals_greedy_feasibility": bool(same(free["_pol"], cont)),
        "priced_lambda_0_objective_is_flat": bool(
            abs(free["objective_value"] - float(solve_nonprescient(
                peak, up_h, down_h, sigma, grid=grid, risk_mode="priced",
                death_penalty=0.0)["objective_value"])) < 1e-12),
        "priced_lambda_gt_0_equals_greedy_feasibility": bool(same(priced["_pol"], cont)),
        "priced_lambda_gt_0_equals_never_stop": bool(same(priced["_pol"], never)),
        "lambda_used": lam,
        "hours_compared": len([h for h in cont if h in priced["_pol"]]),
        "why": (
            "奖励非负（窗口内 12、窗口外 0）、终止吸收且值为 0 时：strict 口径把会死的分支剪掉，"
            "最优恰好等于「还能安全多跑一小时就继续」的贪心可行性规则，序列内容为空；"
            "λ=0 的计价口径下死亡免费，继续恒不劣，最优是永不终止（哪怕必然失电）。两种都是退化。"
            "只有 λ>0（死亡被计价，与论文目标函数一致）才出现真正的取舍：最优既不是贪心可行性规则，"
            "也不是永不终止，而是状态相关的停止规则。")}


# ----------------------------------------------------------------- 规则求值（全地平线）
def evaluate_rule(peak: float, up_h: int, down_h: int, rule, sigma: float = CLOUD_SIGMA,
                  quantum: float = Q_SOC, soc_root: float | None = None,
                  grid: Grid | None = None, S=None, end_hour: int = END_HOUR,
                  reserve_wh: float = 0.0, risk_mode: str = "priced",
                  death_penalty: float = PRIMARY_LAMBDA, Pd=None) -> dict:
    """求值一条"第 h 小时是否继续密集"的规则；规则被问到 `[up_h, end_hour)` 的每一小时。

    求值器不接受终点参数。`strict` 口径下返回是否安全；`priced` 口径下返回
    目标值 = 期望服务 − λ·死亡概率，并给出两者的分量。
    """
    grid = grid or Grid(quantum)
    day_fr = tuple(sorted(set(levels(sigma))))
    Pd = Pd if Pd is not None else sparse_death_prob(grid, peak, day_fr, end_hour)
    S = S if S is not None else sparse_suffix_safety(grid, peak, day_fr, end_hour, reserve_wh)
    soc_root = soc_at_apply_edge(peak, up_h) if soc_root is None else soc_root
    root = int(grid.idx(soc_root))
    acts = {h: np.asarray(rule(h, grid), dtype=bool) for h in range(up_h, end_hour)}
    lam = float(death_penalty) if risk_mode == "priced" else math.inf

    if risk_mode == "strict":
        safe = [None] * (end_hour + 1)
        safe[end_hour] = S[end_hour].copy()
        for h in range(end_hour - 1, up_h - 1, -1):
            cont_ok = np.ones(grid.n, dtype=bool)
            for endi, alive in hour_maps(grid, h, peak, True, day_fr):
                cont_ok &= alive & safe[h + 1][endi]
            safe[h] = np.where(acts[h], cont_ok, S[h])
        P = np.zeros(grid.n)
        P[root] = 1.0
        svc = 0.0
        for h in range(up_h, end_hour):
            cont = acts[h]
            if h < down_h:
                svc += OBL_PER_HOUR * float(P[cont].sum())
            Q = np.zeros(grid.n)
            w = P * cont / len(day_fr)
            for endi, alive in hour_maps(grid, h, peak, True, day_fr):
                np.add.at(Q, endi, np.where(alive, w, 0.0))
            P = Q
        return {"risk_mode": "strict", "safe": bool(safe[up_h][root]),
                "expected_service_per_node": svc, "p_death": None,
                "objective_value": None if not safe[up_h][root] else svc,
                "dense_hour_actions": {str(h): bool(acts[h][root]) for h in acts}}

    P = np.zeros(grid.n)
    P[root] = 1.0
    svc, p_death = 0.0, 0.0
    for h in range(up_h, end_hour):
        cont = acts[h]
        if h < down_h:
            svc += OBL_PER_HOUR * float(P[cont].sum())
        stop_mass = np.where(~cont, P, 0.0)
        if stop_mass.any():
            p_death += float((stop_mass * Pd[h]).sum())
        Q = np.zeros(grid.n)
        w = P * cont / len(day_fr)
        for endi, alive in hour_maps(grid, h, peak, True, day_fr):
            p_death += float((w * (~alive)).sum())
            np.add.at(Q, endi, np.where(alive, w, 0.0))
        P = Q
    return {"risk_mode": "priced", "safe": None, "expected_service_per_node": svc,
            "p_death": p_death, "objective_value": svc - lam * p_death,
            "dense_hour_actions": {str(h): bool(acts[h][root]) for h in acts}}


# ----------------------------------------------------------------- 普通组合族
def rule_ttl(k_hours: int, up_h: int):
    return lambda h, grid: np.full(grid.n, (h - up_h) < k_hours, dtype=bool)


def rule_ttl_level(k_hours: int, up_h: int, theta: float):
    return lambda h, grid: ((h - up_h) < k_hours) & (grid.soc >= theta - 1e-12)


def rule_nightfloor(up_h: int, dusk_h: int = DUSK_H):
    return lambda h, grid: np.full(grid.n, h < dusk_h, dtype=bool)


def plan_threshold(peak: float, up_h: int, sigma: float, grid: Grid, dense_to_h: int,
                   end_hour: int = END_HOUR, reserve_wh: float = 0.0):
    day_fr = tuple(sorted(set(levels(sigma))))
    R = sparse_suffix_safety(grid, peak, day_fr, end_hour, reserve_wh)[dense_to_h].copy()
    for h in range(dense_to_h - 1, up_h - 1, -1):
        ok = np.ones(grid.n, dtype=bool)
        for endi, alive in hour_maps(grid, h, peak, True, day_fr):
            ok &= alive & R[endi]
        R = ok
    return R


def rule_rolling_dusk(peak: float, up_h: int, sigma: float, dusk_h: int = DUSK_H):
    """能量族候选的抽象：按**名义账本**判断"从此刻密集到日落"是否可行，不可行即终止。"""
    cache: dict = {}

    def table() -> np.ndarray:
        if "v" not in cache:
            cache["v"] = plan_threshold(peak, up_h, sigma, Grid(), dusk_h)
        return cache["v"]

    return lambda h, grid: table() if h < dusk_h else np.zeros(grid.n, dtype=bool)


def rule_valid_until(up_h: int, down_h: int):
    """Task 1（命令携带绝对有效期）：密集恰好到预告终点。**不同信息条件，单列对照。**"""
    return lambda h, grid: np.full(grid.n, (up_h <= h < down_h), dtype=bool)


def ordinary_family(peak: float, up_h: int, down_h: int, sigma: float, grid: Grid | None = None,
                    end_hour: int = END_HOUR, risk_mode: str = "priced",
                    death_penalty: float = PRIMARY_LAMBDA) -> dict:
    grid = grid or Grid()
    day_fr = tuple(sorted(set(levels(sigma))))
    S = sparse_suffix_safety(grid, peak, day_fr, end_hour)
    Pd = sparse_death_prob(grid, peak, day_fr, end_hour)
    cands = [(f"ttl{k}", rule_ttl(k, up_h)) for k in DEGREES]
    cands += [(f"ttl{k}+lvl{int(round(t*1e6))}u", rule_ttl_level(k, up_h, t))
              for k in DEGREES for t in THETAS]
    cands.append(("nightfloor_dusk", rule_nightfloor(up_h)))
    cands.append(("rolling_dusk_openloop", rule_rolling_dusk(peak, up_h, sigma)))
    members = []
    for name, rule in cands:
        ev = evaluate_rule(peak, up_h, down_h, rule, sigma, grid=grid, S=S, Pd=Pd,
                           end_hour=end_hour, risk_mode=risk_mode, death_penalty=death_penalty)
        members.append({"name": name, "safe": ev["safe"],
                        "service_per_node": ev["expected_service_per_node"],
                        "p_death": ev["p_death"], "objective_value": ev["objective_value"]})
    if risk_mode == "strict":
        pool = [m for m in members if m["safe"]]
        best = max(pool, key=lambda m: (m["service_per_node"], m["name"])) if pool else None
    else:
        pool = members
        best = max(members, key=lambda m: (m["objective_value"], m["name"])) if members else None
    ties = sorted(m["name"] for m in pool if best is not None
                  and abs((m["objective_value"] if risk_mode == "priced"
                           else m["service_per_node"])
                          - (best["objective_value"] if risk_mode == "priced"
                             else best["service_per_node"])) < 1e-9)
    task1 = evaluate_rule(peak, up_h, down_h, rule_valid_until(up_h, down_h), sigma, grid=grid,
                          S=S, Pd=Pd, end_hour=end_hour, risk_mode=risk_mode,
                          death_penalty=death_penalty)
    return {"risk_mode": risk_mode, "death_penalty": death_penalty,
            "n_members": len(members),
            "n_safe_or_pool": len(pool), "members": sorted(
                members, key=lambda m: (-(m["objective_value"] if risk_mode == "priced"
                                          else m["service_per_node"]), m["name"])),
            "best": best, "best_ties": ties,
            "task1_reference": {"name": "valid_until(announced)",
                                "service_per_node": task1["expected_service_per_node"],
                                "p_death": task1["p_death"],
                                "objective_value": task1["objective_value"],
                                "note": "不同信息条件，仅供对照，不参与同一信息条件的比较"}}


# ----------------------------------------------------------------- 全知参照
_OMNI_CACHE: dict = {}


def omniscient_reference(peak: float, up_h: int, down_h: int, sigma: float = CLOUD_SIGMA,
                         n_paths: int = MC_PATHS, seed: int = MC_SEED,
                         end_hour: int = END_HOUR, death_penalty: float = PRIMARY_LAMBDA) -> dict:
    """逐未来最优：每条路径在 `k ≤ W` 中选择使 `服务 − λ·死亡` 最大的密集小时数。

    服务只计**死亡之前**落在窗口内的密集小时（节点一旦失电就不再产生服务）。
    蒙特卡洛估计，**是参照不是上界**。
    """
    key = (peak, up_h, down_h, sigma, n_paths, seed, end_hour, death_penalty)
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
    lam = float(death_penalty)
    best_val = np.full(n_paths, -np.inf)
    best_svc = np.zeros(n_paths)
    best_dead = np.zeros(n_paths)
    for k in range(W + 1):
        dh = set(range(up_h, up_h + k))
        soc = np.full(n_paths, CAP_WH)
        alive = np.ones(n_paths, dtype=bool)
        svc = np.zeros(n_paths)
        died = np.zeros(n_paths, dtype=bool)
        for h in range(end_hour):
            if h in dh and h < down_h:
                svc += np.where(alive, OBL_PER_HOUR, 0.0)
            was_alive = alive.copy()
            hv = peak * F[:, h, None] * sun[h][None, :]
            ld = load_dn if h in dh else load_sp
            mn = soc.copy()
            for j in range(TICKS_PER_HOUR):
                soc = np.minimum(CAP_WH, soc + hv[:, j]) - ld
                np.minimum(mn, soc, out=mn)
            alive = alive & (mn >= SAMPLE_WH)
            died |= was_alive & (~alive)
            if h >= up_h and not alive.any():
                break
        val = svc - lam * died
        take = val > best_val
        best_val = np.where(take, val, best_val)
        best_svc = np.where(take, svc, best_svc)
        best_dead = np.where(take, died, best_dead)
    out = {"paths": n_paths, "seed": seed, "levels": list(lv), "offset": levels_offset(sigma),
           "death_penalty": lam,
           "mean_objective_value": float(best_val.mean()),
           "mean_service_per_node": float(best_svc.mean()),
           "p_death": float(best_dead.mean()),
           "mean_service_when_safe_required": None,
           "note": "per-future optimum with death priced; Monte-Carlo averaged, a reference"}
    _OMNI_CACHE[key] = out
    return out


# ----------------------------------------------------------------- strict 口径的可行性（端点）
def strict_feasibility(peak: float, up_h: int, sigma: float) -> dict:
    """**strict 口径**（声明全部未来存活）下最稀疏职责是否可行。

    这不是任务层结论。依据：论文目标函数把死亡计为一项；登记表在 `v3joint_r02_restart.json`
    与 r47 中分别指出"0 存活主要是吸收态产物"与"不得外推为物理不可行"。本函数只回答
    "在 α=0 这个风险端点下能不能"，并把结果作为**该口径**的性质报告。
    """
    tr = sparse_future(peak, up_h, sigma)
    return {"risk_mode": "strict", "sigma": sigma, "offset": levels_offset(sigma),
            "sparse_min_soc_wh_low_branch": tr["min_soc"],
            "feasible_under_strict": bool(survives(tr)),
            "scope": "该结论只在该风险口径内成立；不构成任务要求或物理不可行的判断"}


def critical_sigma(peak: float, up_h: int, down_h: int, kind: str = "sparse_only",
                   hi: float = 0.30, steps: int = 24) -> float | None:
    """二分"strict 口径仍可行的最大标准差 σ"（同为 σ 单位，可直接与实测比较）。"""
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
    """同一策略、同一天气、两个不同隐藏计分终点下的配置轨迹必须逐位相同。"""
    grid = Grid()
    a = evaluate_rule(peak, up_h, down_h, rule, sigma, grid=grid, risk_mode="priced")
    b = evaluate_rule(peak, up_h, alt_down_h, rule, sigma, grid=grid, risk_mode="priced")
    return {"true_window_end_h": down_h, "alternative_window_end_h": alt_down_h,
            "executed_dense_hours_identical": bool(
                a["dense_hour_actions"] == b["dense_hour_actions"]),
            "service_at_true_end": a["expected_service_per_node"],
            "service_at_alternative_end": b["expected_service_per_node"],
            "note": "终点只影响计分，不影响执行"}


def policy_window_invariance(peak: float, up_h: int, down_h: int, sigma: float,
                             alt_down_h: int, risk_mode: str = "priced",
                             death_penalty: float = PRIMARY_LAMBDA) -> dict:
    """同一策略在两个计分终点下的**整张规则表**必须逐位相同（不是逐终点重解）。"""
    a = solve_nonprescient(peak, up_h, down_h, sigma, risk_mode=risk_mode,
                           death_penalty=death_penalty)
    b = solve_nonprescient(peak, up_h, alt_down_h, sigma, risk_mode=risk_mode,
                           death_penalty=death_penalty)
    shared = [h for h in a["_pol"] if h in b["_pol"]]
    same = all(np.array_equal(a["_pol"][h], b["_pol"][h]) for h in shared)
    return {"window_end_h": down_h, "alternative_window_end_h": alt_down_h,
            "risk_mode": risk_mode, "hours_compared": len(shared),
            "rule_table_bit_identical": bool(same)}


def post_window_execution_witness(peak: float, up_h: int, down_h: int,
                                  sigma: float = CLOUD_SIGMA) -> dict:
    """业务计分在窗口结束，配置必须继续跑：永不终止的规则要一直密集到地平线。"""
    ev = evaluate_rule(peak, up_h, down_h, lambda h, g: np.ones(g.n, dtype=bool), sigma,
                       risk_mode="priced")
    tr = path_trace(CAP_WH, range(up_h, END_HOUR), worst_future_factors(up_h, sigma), peak)
    return {"rule": "never terminate",
            "service_scored_per_node": ev["expected_service_per_node"],
            "config_runs_to_horizon": bool(END_HOUR - 1 >= down_h),
            "p_death": ev["p_death"],
            "min_soc_low_branch": tr["min_soc"],
            "note": "计分只数窗口内的密集小时；配置与能耗继续到地平线，不在真值终点降档"}


def never_stop_is_not_free(peak: float, up_h: int, down_h: int, sigma: float) -> dict:
    """strict 口径的最小见证：规则从不主动终止时，安全判定必须反映它真的不终止。"""
    grid = Grid()
    day_fr = tuple(sorted(set(levels(sigma))))
    S = sparse_suffix_safety(grid, peak, day_fr)
    ev = evaluate_rule(peak, up_h, down_h, lambda h, g: np.ones(g.n, dtype=bool), sigma,
                       grid=grid, S=S, risk_mode="strict")
    tr = path_trace(CAP_WH, range(up_h, END_HOUR), worst_future_factors(up_h, sigma), peak)
    return {"rule": "always continue dense over the whole horizon",
            "evaluator_safe": ev["safe"], "true_safe_under_low_branch": bool(survives(tr)),
            "agree": bool(ev["safe"] == survives(tr))}


def ttl8_physical_execution(peak: float, up_h: int, down_h: int, sigma: float) -> dict:
    """TTL8+8 mWh 门物理执行到自己的结束时刻，在低采能未来里看最低电量。"""
    d = levels_offset(sigma)
    f = worst_future_factors(up_h, sigma)
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
            "dense_hours_executed": dense_hours, "stopped_at_hour": stopped,
            "min_soc_wh_low_branch": mn, "declared_safety_floor_wh": SAMPLE_WH,
            "safe_under_low_branch": bool(mn >= SAMPLE_WH),
            "min_soc_wh_v1_offset_convention": mn_v1,
            "v1_offset_convention_matches_review": bool(abs(mn_v1 - 0.0003295257) < 1e-9)}


def sparse_dominance_witness(peak: float, up_h: int, sigma: float, n: int = 8,
                             seed: int = 7) -> dict:
    """逐拍单调性：任一未来任一时刻，全程稀疏的电量不低于任何密集安排。"""
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


def brute_force_reachable(peak: float, up_h: int, down_h: int, sigma: float, grid: Grid,
                          soc_root: float, end_hour: int, reserve_wh: float = 0.0,
                          risk_mode: str = "strict",
                          death_penalty: float = PRIMARY_LAMBDA) -> dict:
    """在可达决策格上穷举每一条规则，独立核对 DP（规模由可达格数决定）。"""
    day_fr = tuple(sorted(set(levels(sigma))))
    S = sparse_suffix_safety(grid, peak, day_fr, end_hour, reserve_wh)
    Pd = sparse_death_prob(grid, peak, day_fr, end_hour)
    states = {up_h: {int(grid.idx(soc_root))}}
    for h in range(up_h, end_hour - 1):
        nxt = set()
        for i in sorted(states[h]):
            for dense in (False, True):
                for endi, _alive in hour_maps(grid, h, peak, dense, day_fr):
                    nxt.add(int(endi[i]))
        states[h + 1] = nxt
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

        ev = evaluate_rule(peak, up_h, down_h, rule, sigma, grid=grid, S=S, Pd=Pd,
                           soc_root=soc_root, end_hour=end_hour, reserve_wh=reserve_wh,
                           risk_mode=risk_mode, death_penalty=death_penalty)
        if risk_mode == "strict":
            if ev["safe"]:
                n_safe += 1
                cur = ev["expected_service_per_node"]
                if best is None or cur > best["objective_value"]:
                    best = {"mask": mask, "objective_value": cur,
                            "continue_at": sorted([list(c) for c in on])}
        else:
            n_safe += 1
            cur = ev["objective_value"]
            if best is None or cur > best["objective_value"]:
                best = {"mask": mask, "objective_value": cur,
                        "service_per_node": ev["expected_service_per_node"],
                        "p_death": ev["p_death"],
                        "continue_at": sorted([list(c) for c in on])}
    return {"n_cells": len(cells), "cells": [list(c) for c in cells],
            "enumerated_rules": 1 << len(cells), "n_admissible": n_safe, "best": best,
            "reachable_states_by_hour": {str(h): sorted(states[h]) for h in states}}


def core_instance(verbose: bool = False) -> dict | None:
    p = CORE
    grid = Grid(p["quantum"])
    E = p["end_hour"]
    root_soc = p["soc_edge"]
    bf = brute_force_reachable(p["peak"], p["up_h"], p["down_h"], p["sigma"], grid,
                               root_soc, E, p["reserve_wh"], risk_mode="strict")
    dp = solve_nonprescient(p["peak"], p["up_h"], p["down_h"], p["sigma"],
                            quantum=p["quantum"], soc_root=root_soc, grid=grid, end_hour=E,
                            reserve_wh=p["reserve_wh"], risk_mode="strict")
    dpv = dp["expected_service_per_node"]
    best_ttl = None
    for k in range(1, E - p["up_h"] + 1):
        ev = evaluate_rule(p["peak"], p["up_h"], p["down_h"], rule_ttl(k, p["up_h"]),
                           p["sigma"], quantum=p["quantum"], grid=grid, soc_root=root_soc,
                           end_hour=E, reserve_wh=p["reserve_wh"], risk_mode="strict")
        if ev["safe"] and (best_ttl is None or ev["expected_service_per_node"] > best_ttl[1]):
            best_ttl = (k, ev["expected_service_per_node"])
    out = {"declared": {k: v for k, v in p.items()},
           "risk_mode": "strict", "purpose": "递推验证（strict 口径下规则族内的精确最优）",
           "level_factors": list(levels(p["sigma"])), "level_offset": levels_offset(p["sigma"]),
           "level_std_check": float(np.std(levels(p["sigma"]))),
           "hour_clear_wh": round(hour_clear_wh(p["up_h"], p["peak"]), 8),
           "hour_load_wh": {"sparse": LOAD_SPARSE_H, "dense": LOAD_DENSE_H},
           "cap_wh": CAP_WH, "sample_wh": SAMPLE_WH,
           "soc_edge_wh": root_soc, "reserve_wh": p["reserve_wh"],
           "brute_force": bf,
           "dp": {"admissible": dp["feasible_under_strict"], "service_per_node": dpv,
                  "continue_if": dp["rule_continue_if_wh"]},
           "best_safe_ttl": {"k": best_ttl[0], "service_per_node": best_ttl[1]} if best_ttl else None,
           "dp_matches_brute_force": bool(bf["best"] is not None
                                          and abs(bf["best"]["objective_value"] - dpv) < 1e-9)}
    if verbose:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    return out


# ----------------------------------------------------------------- 单元
def cell(phase: str, peak: float, sigma: float) -> dict:
    p = PHASES[phase]
    up_h, down_h = p["up_h"], p["down_h"]
    W = down_h - up_h
    grid = Grid()
    day_fr = tuple(sorted(set(levels(sigma))))
    S = sparse_suffix_safety(grid, peak, day_fr)
    Pd = sparse_death_prob(grid, peak, day_fr)
    root_soc = soc_at_apply_edge(peak, up_h)
    out = {"phase": phase, "peak_wh_per_h": peak, "sigma": sigma,
           "offset": levels_offset(sigma),
           "window_hours": W, "window_obligations_per_node": OBL_PER_HOUR * W,
           "window_obligations_network_per_seed": OBL_PER_HOUR * W * NODES,
           "soc_at_apply_edge": round(root_soc, 6),
           "strict": strict_feasibility(peak, up_h, sigma),
           "critical_sigma_strict": {
               "sparse_only": critical_sigma(peak, up_h, down_h, "sparse_only"),
               "full_window_lease": critical_sigma(peak, up_h, down_h, "full_window"),
               "measured_sigma": CLOUD_SIGMA},
           "priced": {}}
    for lam in DEATH_PENALTIES:
        dp = solve_nonprescient(peak, up_h, down_h, sigma, grid=grid, soc_root=root_soc,
                                risk_mode="priced", death_penalty=lam)
        dp_rule = (lambda h, g, pol=dp["_pol"]: pol[h] if h in pol else np.zeros(g.n, dtype=bool))
        ver = evaluate_rule(peak, up_h, down_h, dp_rule, sigma, grid=grid, S=S, Pd=Pd,
                            soc_root=root_soc, risk_mode="priced", death_penalty=lam)
        fam = ordinary_family(peak, up_h, down_h, sigma, grid=grid, risk_mode="priced",
                              death_penalty=lam)
        omni = omniscient_reference(peak, up_h, down_h, sigma, death_penalty=lam)
        ord_best = fam["best"]
        gaps = {
            "objective_total": omni["mean_objective_value"] - ord_best["objective_value"],
            "objective_implementable": dp["objective_value"] - ord_best["objective_value"],
            "objective_information": omni["mean_objective_value"] - dp["objective_value"],
            "service_total": omni["mean_service_per_node"] - ord_best["service_per_node"],
            "service_implementable": ver["expected_service_per_node"] - ord_best["service_per_node"],
            "service_information": omni["mean_service_per_node"]
                                    - ver["expected_service_per_node"],
            "p_death_ordinary": ord_best["p_death"], "p_death_nonprescient": ver["p_death"],
            "p_death_omniscient": omni["p_death"],
            "identity_residual": (omni["mean_objective_value"] - dp["objective_value"])
                                 + (dp["objective_value"] - ord_best["objective_value"])
                                 - (omni["mean_objective_value"] - ord_best["objective_value"]),
        }
        out["priced"][str(lam)] = {
            "death_penalty": lam,
            "nonprescient": {"objective_value": dp["objective_value"],
                             "service_per_node": ver["expected_service_per_node"],
                             "p_death": ver["p_death"],
                             "rule_continue_if_wh": dp["rule_continue_if_wh"],
                             "selfcheck_objective_agrees": bool(
                                 abs(ver["objective_value"] - dp["objective_value"]) < 1e-9)},
            "ordinary": {"name": ord_best["name"], "objective_value": ord_best["objective_value"],
                         "service_per_node": ord_best["service_per_node"],
                         "p_death": ord_best["p_death"], "best_ties": fam["best_ties"],
                         "candidates": fam["members"], "task1_reference": fam["task1_reference"]},
            "omniscient": omni,
            "gaps": gaps,
        }
    return out


def main() -> int:
    if "--core" in sys.argv:
        core_instance(verbose=True)
        return 0
    strict_only = "--strict" in sys.argv
    out = {
        "contract": "spec/prereg-nonprescient-sequence-v3.md",
        "supersedes": {
            "pre_registrations": ["spec/prereg-nonprescient-sequence-v1.md",
                                  "spec/prereg-nonprescient-sequence-v2.md"],
            "results": ["results/c5_seqref_v1_semantics.json",
                        "results/c5_seqref_v2_semantics.json"],
            "reasons": [
                "v1：求值器在真值终点替策略自动降档；等权三点把偏移当标准差",
                "v2：把'零失电'当成任务要求（论文目标函数把死亡计为一项，评测按臂报告死亡，"
                "r02 记录 0 存活主要是吸收态产物）；且奖励非负 + 终止吸收 + 死亡不计价时，"
                "所谓序列最优恰好等于贪心可行性规则，序列内容为空",
            ],
            "archive": "results/_withdrawn/2026-09-20-c9-v1-semantics.md、"
                       "results/_withdrawn/2026-09-20-c9-v2-semantics.md",
        },
        "task_semantics": task_semantics_evidence(),
        "model": {
            "constants": {"cap_wh": CAP_WH, "sample_wh": SAMPLE_WH,
                          "load_sparse_wh_per_h": LOAD_SPARSE_H,
                          "load_dense_wh_per_h": LOAD_DENSE_H,
                          "cloud_nominal": CLOUD_NOMINAL, "cloud_sigma": CLOUD_SIGMA,
                          "obligations_per_node_hour": OBL_PER_HOUR, "nodes": NODES,
                          "end_hour": END_HOUR, "quantum_wh": Q_SOC,
                          "mc_paths": MC_PATHS, "mc_seed": MC_SEED},
            "risk_layer": {"modes": list(RISK_MODES),
                           "death_penalties": list(DEATH_PENALTIES),
                           "primary_lambda": PRIMARY_LAMBDA,
                           "note": "口径是参数层，被扫描并被报告；strict（α=0）只是端点，"
                                   "不作为任务要求"},
            "action_space": "自应用边沿到地平线的每一小时：继续密集 | 终止（吸收，此后永久稀疏）",
            "information_set": "(相对小时, 量化剩余电量)；不含未来采能、授权终点、中心在线状态；"
                               "黄级窗口终点只用于计分，不进入执行",
            "objective": "priced：期望服务 − λ·死亡概率（与论文目标函数三项中的两项对应）",
            "boundaries": [
                "服务 = 黄级义务被采集，不含投递链路折损（实测采集 535/672、投递 283/672）",
                "云遮按小时取因子；三点等权离散，偏移 = σ·sqrt(3/2) 以匹配 σ",
                "单节点切片，不含多节点竞争、网关打包与回传",
                "起始电量取满值；动作能力限于一次租约",
                "λ 是声明旋钮，论文权重未定，因此报告扫描而非单一取值",
            ],
        },
        "peaks": list(PEAKS), "sigmas": list(SIGMAS), "death_penalties": list(DEATH_PENALTIES),
        "cells": {}, "witnesses": {}, "core": core_instance(),
    }
    up_a, dn_a = PHASES["A"]["up_h"], PHASES["A"]["down_h"]
    out["witnesses"] = {
        "degeneracy": degeneracy_witness(0.016, up_a, dn_a, CLOUD_SIGMA),
        "never_stop_is_not_free": never_stop_is_not_free(0.012, up_a, dn_a, CLOUD_SIGMA),
        "ttl8_physical_execution": ttl8_physical_execution(0.012, up_a, dn_a, CLOUD_SIGMA),
        "sparse_dominance": sparse_dominance_witness(0.012, up_a, CLOUD_SIGMA),
        "post_window_execution": post_window_execution_witness(0.016, up_a, dn_a, CLOUD_SIGMA),
        "endpoint_invariance_fixed_rule": endpoint_invariance_probe(
            0.012, up_a, dn_a, CLOUD_SIGMA, rule_ttl_level(8, up_a, 0.008), 10),
        "policy_window_invariance_strict": policy_window_invariance(
            0.016, up_a, dn_a, CLOUD_SIGMA, 10, risk_mode="strict"),
        "policy_window_invariance_priced": policy_window_invariance(
            0.016, up_a, dn_a, CLOUD_SIGMA, 10, risk_mode="priced",
            death_penalty=PRIMARY_LAMBDA),
        "hidden_endpoint_not_modelled": {
            "note": "v3 不把授权终点建成决策变量：节点只按自己的规则停止，"
                    "窗口终点仅用于计分。因此'隐藏授权终点改变执行'在结构上不可能发生；"
                    "priced 口径的策略合法地依赖**公开任务表**（黄级窗口），这与隐藏终点是两件事，"
                    "由 spec v3 §3 声明。",
            "revocation_endpoint_is_a_decision_input": False,
            "mission_schedule_is_public_and_used_for_scoring_only": True}
    }
    dg = out["witnesses"]["degeneracy"]
    print("口径层级（依据见 task_semantics）：风险口径是参数层，strict 只是端点")
    print(f"  退化见证：strict 口径最优 == 贪心可行性规则？"
          f"{dg['strict_mode_equals_greedy_feasibility']}；"
          f"λ=0 计价最优 == 永不终止？{dg['priced_lambda_0_equals_never_stop']}；"
          f"λ={dg['lambda_used']:g} 时与两者都不同？"
          f"{not dg['priced_lambda_gt_0_equals_greedy_feasibility'] and not dg['priced_lambda_gt_0_equals_never_stop']}")
    pw = out["witnesses"]["post_window_execution"]
    print(f"  窗口后仍执行：计分 {pw['service_scored_per_node']:.0f} 条，"
          f"配置跑到地平线={pw['config_runs_to_horizon']}，低档死亡概率={pw['p_death']:.3f}")
    print()
    for phase in PHASES:
        for peak in PEAKS:
            for sig in SIGMAS:
                c = cell(phase, peak, sig)
                out["cells"][f"{phase}|{peak}|{sig}"] = c
                if strict_only:
                    continue
                st = c["strict"]
                head = (f"{phase} p={peak:<6} σ={sig:<6} strict可行="
                        f"{st['feasible_under_strict']!s:5}"
                        f"(稀疏最低 {st['sparse_min_soc_wh_low_branch']*1000:+8.4f} mWh)")
                print(head)
                for lam in DEATH_PENALTIES:
                    r = c["priced"][str(lam)]
                    g = r["gaps"]
                    print(f"    λ={lam:<6g} 非预知 服务={r['nonprescient']['service_per_node']:6.2f} "
                          f"P死={r['nonprescient']['p_death']:.4f} | "
                          f"普通 {r['ordinary']['name']:<22} 服务={r['ordinary']['service_per_node']:6.2f} "
                          f"P死={r['ordinary']['p_death']:.4f} | "
                          f"全知 服务={r['omniscient']['mean_service_per_node']:6.2f} "
                          f"P死={r['omniscient']['p_death']:.4f} | "
                          f"可实现Δ={g['objective_implementable']:+7.2f} 信息Δ={g['objective_information']:+7.2f}")
    os.makedirs(os.path.join(REPO, "results"), exist_ok=True)
    path = os.path.join(REPO, "results", "c5_seqref.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("\nsaved", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
