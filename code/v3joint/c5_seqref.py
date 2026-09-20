# -*- coding: utf-8 -*-
"""c5_seqref.py — 三方判别中的**中间行**：同信息、非预知的序列优化参照。

为什么有这个文件
----------------
C5 修正后的实测事实是：紧能量格上"能量族"候选（energy_lease / soc_mpc / soc_mpc_cons /
lease_safety）在应用边沿就回退，黄级交付只剩 559/2016（A）、1194/3528（B）；而不看能量的固定
TTL8 拿到 849/2016、2020/3528 且 0 死亡。这个反差说明"保护有代价"，但**没有回答**其中多少是
不可避免的：候选族用的是开环/单切换的预测门，既没有求解后续动作序列，也没有在声明的不确定性下
做非预知最优。缺了这条参照，"保护必然牺牲服务"这句话不成立。

本文件补这条参照，并遵守三条纪律：

1. **同一信息**。参照策略只用与普通组合相同的东西：本地时钟、自己量到的剩余电量、公开任务窗口。
   策略是 `(相对小时, 量化剩余电量)` 的函数；两个不同未来在拿到新信息之前给出同一个动作。
2. **同一动作能力**。密集/稀疏两档，**一次租约、降回稀疏后不得重入**（回传中断期间不再有新的
   授权到达），与实测臂同语义。不引入"单次采样控制"等当前不存在的能力。
3. **同一风险口径**。普通组合与参照都必须在**声明的全部未来**里不死亡；死亡按环境口径判定
   （任一拍 `soc < sample_wh`，见 `code/instance/network.py:_take`），不靠放宽生存要求换服务。

三方表与恒等式
--------------
    普通组合（声明有限族内最强的可行规则）
    非预知参照（本文件 DP：声明动作族内的精确最优）
    全知参照（逐未来最优，蒙特卡洛平均；**是参照不是上界**）
    service(全知) - service(普通) = 信息差额 + 可实现策略差额

台账同源
--------
能量台账与环境逐拍同序（`network.py:_step_power`：`x[k] = min(CAP, x[k-1] + h[k]) - l[k]`）：

  * 容量 50 mWh、单次采样 0.47 mWh（`admission.py`）；
  * 实测小时负载：**稀疏 3.000 mWh/h、密集 6.000 mWh/h**（密集恰为两倍：周期 300 s 对 600 s，
    每个样本带一次上报）。实测脚本 `code/experiments/measure_seqref_calibration.py`，
    冻结记录 `results/reference/c5_seqref_calibration.json`；
  * 采能 `peak * f * sin(pi*rel/12) / 60` 每拍，`rel` 自本地 06:00 起算。

**不在本模型内的东西**（截断边界；引用本文件结论时必须同时引用这一句）：

  * **投递链路**。本文件的"服务"是黄级义务**被采集**（密集档在义务释放时刻生效即计），不是被
    投递。实测中即使密集覆盖整个窗口，采集也只有 535/672、投递 283/672；应用边沿延迟与备份打包
    上限这两级折损不在模型里，靠它们解释差额是错的。
  * **云遮的时间结构**。环境逐拍抽云（`cloud_p=.35, cloud_atten=.25`），本模型按**小时**取一个
    因子，并把实测每小时因子分布（均值 0.7375、标准差 0.047）用等权三点矩匹配离散化。逐拍抖动被
    抹掉，只留小时级不确定；`severity=0` 退化为预期采能，`severity` 是扫描旋钮不是拟合值。
  * **降雨事件的额外采样样本**（实测约 12 次/日）。它进负载，不进决策。
  * **多节点竞争、网关打包与回传**。本文件是**单节点切片**，不能替代完整网络结论。
  * 起始电量取满值（实测 `initial_soc=1.0`），且 0..应用边沿的小时按名义因子推进作为**共同过去**。

跑法
----
    python3 code/v3joint/c5_seqref.py            # 写 results/c5_seqref.json
    python3 code/v3joint/c5_seqref.py --core     # 打印可手算核例的全部算术
"""
from __future__ import annotations

import json
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
#: 小时负载 = (每小时采样数) × (sample_wh + 单次上报射频)。两个分量都是实测：
#: `sample_wh` 由代码读出、并由 342 次采样合计 0.16074 Wh 逐位验证；射频 0.010567745/341
#: = 3.0990e-5 Wh/次。逐小时实测值见 results/reference/c5_seqref_calibration.json（稀疏
#: 3.0009e-3、密集中位 6.0505e-3），与下式的偏差在 ±0.6% 内。
#: **声明值只有一个来源**：这两个常数与 `results/reference/c5_seqref_calibration.json` 里的
#: `declared_*` 字段用同一组字面量、同一个表达式算出，因此可以逐位比对（audit_seqref 第 2 项）。
#: 实测得到的全精度值在同一个参考文件的 `measured_*` 里，与声明值的偏差也由那里给出：
#: 声明保留 5 位有效数字，偏差 ~7e-12 Wh/h（相对 2.4e-9），远小于一次密集小时 6 mWh 的量级。
RADIO_WH_PER_REPORT = 3.099046e-5
LOAD_SPARSE_H = 6 * (SAMPLE_WH + RADIO_WH_PER_REPORT)
LOAD_DENSE_H = 12 * (SAMPLE_WH + RADIO_WH_PER_REPORT)
SUNRISE_H = 6.0
DAYLIGHT_H = 12.0
END_HOUR = 49
Q_SOC = 1e-5                  # 电量量化步长；状态向下取整（对安全与服务都不乐观）
CLOUD_NOMINAL = 0.7375        # 实测小时因子均值
CLOUD_SIGMA = 0.047           # 实测小时因子标准差
PHASES = {"A": dict(up_h=2, down_h=6), "B": dict(up_h=1, down_h=8)}
OBL_PER_HOUR = 12             # 窗口内每节点每小时 12 条黄级义务（300 s 网格）
NODES = 14                    # 冻结实例节点数
MC_PATHS = 4000
MC_SEED = 20260920
PEAKS = (0.006, 0.008, 0.010, 0.012, 0.016, 0.030)
SEVERITIES = (0.0, 0.03, 0.047, 0.06, 0.09)
DEGREES = (2, 4, 6, 7, 8, 10, 12)
THETAS = (0.0, 0.002, 0.004, 0.008)


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
    """该小时 60 拍的晴空形状（Wh/tick 除以 peak 后的无量纲量，和为 12/pk 的倍数）。"""
    if hour not in _HOUR_SUN:
        t0 = hour * 3600
        _HOUR_SUN[hour] = np.array([sun_frac(t0 + k * TICK_S) / 60.0
                                    for k in range(TICKS_PER_HOUR)])
    return _HOUR_SUN[hour]


def hour_clear_wh(hour: int, peak: float) -> float:
    return float(peak * hour_sun(hour).sum())


def is_daylight_hour(hour: int) -> bool:
    return float(hour_sun(hour).sum()) > 0.0


def levels(severity: float) -> tuple[float, ...]:
    """等权三点矩匹配离散：均值 = 名义因子，标准差 = severity。severity=0 退化为单一分支。"""
    if severity <= 0.0:
        return (CLOUD_NOMINAL,)
    return (CLOUD_NOMINAL - severity, CLOUD_NOMINAL, CLOUD_NOMINAL + severity)


# ----------------------------------------------------------------- 台账（慢路径：手算与校准）
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
    """整条轨迹。`factors` 只对白天小时有意义（夜里采能为零）。"""
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
    """共同过去：0..up-1 小时按 `past_factor` 推进（默认名义因子）。"""
    return path_trace(soc0, (), {h: past_factor for h in range(up_h)}, peak,
                      end_hour=up_h)["final_soc"]


# ----------------------------------------------------------------- 网格与转移
class Grid:
    """电量网格。量化向下取整。"""

    def __init__(self, quantum: float = Q_SOC):
        self.q = quantum
        self.n = int(round(CAP_WH / quantum)) + 1
        self.soc = np.arange(self.n) * quantum

    def idx(self, soc):
        return np.clip(np.floor(np.asarray(soc, dtype=float) / self.q).astype(int), 0, self.n - 1)


_MAP_CACHE: dict = {}


def hour_maps(grid: Grid, hour: int, peak: float, dense: bool, factors):
    """该小时在网格上的转移：每个天气档给出 (末电量下标, 是否全程存活)。

    对整条网格向量化推进 60 拍。以 `(hour, peak*f, dense)` 为键缓存：采能与 `peak*f` 成正比，
    因此扫描不同 peak/severity 时可复用。
    """
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
    """S[h][i]：自第 h 小时起**永不密集**时，声明全部未来都不死亡、且终末不低于保留量。

    `reserve_wh` 是**终末保留量约束**：地平线结束时电量须不低于它（下游固定职责）。主扫描取 0；
    核例用它把边际权衡露出来。
    """
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


# ----------------------------------------------------------------- 非预知 DP
def solve_nonprescient(peak: float, up_h: int, down_h: int, severity: float = CLOUD_SIGMA,
                       quantum: float = Q_SOC, soc_root: float | None = None,
                       grid: Grid | None = None, end_hour: int = END_HOUR,
                       reserve_wh: float = 0.0) -> dict:
    """声明动作族内的非预知精确最优。

    `A[h][i]` = 从窗口第 h 小时、量化电量 i、尚未终止出发的最优期望服务。
    动作：`继续密集`（当拍记 12 条）或 `终止`（吸收态，值 0，此后永久稀疏）。
    约束：任何被选动作的**每个天气分支**都必须存活，且子状态仍可安全续行。
    """
    grid = grid or Grid(quantum)
    lv = levels(severity)
    day_fr = tuple(sorted(set(lv)))
    soc_root = soc_at_apply_edge(peak, up_h) if soc_root is None else soc_root
    S = sparse_suffix_safety(grid, peak, day_fr, end_hour, reserve_wh)
    root = int(grid.idx(soc_root))

    adm = [None] * (end_hour + 1)
    val = [None] * (end_hour + 1)
    pol: dict[int, np.ndarray] = {}
    adm[down_h] = S[down_h].copy()
    val[down_h] = np.where(adm[down_h], 0.0, -np.inf)
    for h in range(down_h - 1, up_h - 1, -1):
        maps = hour_maps(grid, h, peak, True, day_fr)
        cont_ok = np.ones(grid.n, dtype=bool)
        acc = np.zeros(grid.n)
        for endi, alive in maps:
            good = alive & adm[h + 1][endi]
            cont_ok &= good
            acc += np.where(good, val[h + 1][endi], 0.0) / len(maps)
        cont_val = np.where(cont_ok, OBL_PER_HOUR + acc, -np.inf)
        stop_val = np.where(S[h], 0.0, -np.inf)
        pol[h] = cont_ok & (cont_val >= stop_val)
        adm[h] = cont_ok | S[h]
        val[h] = np.maximum(cont_val, stop_val)
    ok = bool(adm[up_h][root])
    return {
        "severity": severity, "levels": list(lv), "quantum": grid.q, "grid_n": grid.n,
        "soc_root": soc_root, "root_idx": root, "admissible": ok,
        "expected_dense_hours": float(val[up_h][root] / OBL_PER_HOUR) if ok else None,
        "expected_service_per_node": float(val[up_h][root]) if ok else None,
        "rule_continue_if_wh": _thresholds(grid, pol, up_h, down_h),
        "_grid": grid, "_val": val, "_adm": adm, "_S": S, "_pol": pol, "_norm": True,
        "_up": up_h, "_down": down_h, "_peak": peak, "_day_fr": day_fr,
    }


def _thresholds(grid: Grid, pol: dict, up_h: int, down_h: int) -> dict:
    """把规则写成"自哪个电量档起继续"的门限，并检查门限单调（规则是电量阈值型）。"""
    out = {}
    for h in range(up_h, down_h):
        arr = pol[h]
        idx = np.flatnonzero(arr)
        mono = bool(np.all(np.diff(arr.astype(int)) >= 0))
        out[str(h)] = {"theta_wh": None if idx.size == 0 else round(float(grid.soc[idx[0]]), 6),
                       "monotone_in_soc": mono, "n_continue": int(arr.sum())}
    return out


def policy_dense(pol: dict, h: int, i: int, up_h: int, down_h: int) -> bool:
    return bool(pol[h][i]) if (up_h <= h < down_h) else False


# ----------------------------------------------------------------- 规则求值（普通组合与自检）
def evaluate_rule(peak: float, up_h: int, down_h: int, rule, severity: float = CLOUD_SIGMA,
                  quantum: float = Q_SOC, soc_root: float | None = None,
                  grid: Grid | None = None, S=None, end_hour: int = END_HOUR,
                  reserve_wh: float = 0.0) -> dict:
    """求值一条"到点是否继续密集"的规则。终止是吸收态。

    安全：反向对所有声明未来求交；服务：前推概率质量，只统计尚未终止的分支。
    """
    grid = grid or Grid(quantum)
    lv = levels(severity)
    day_fr = tuple(sorted(set(lv)))
    S = S if S is not None else sparse_suffix_safety(grid, peak, day_fr, end_hour, reserve_wh)
    soc_root = soc_at_apply_edge(peak, up_h) if soc_root is None else soc_root
    root = int(grid.idx(soc_root))
    acts = {h: np.asarray(rule(h, grid), dtype=bool) for h in range(up_h, down_h)}

    safe = [None] * (end_hour + 1)
    safe[down_h] = S[down_h].copy()
    for h in range(down_h - 1, up_h - 1, -1):
        cont_ok = np.ones(grid.n, dtype=bool)
        for endi, alive in hour_maps(grid, h, peak, True, day_fr):
            cont_ok &= alive & safe[h + 1][endi]
        safe[h] = np.where(acts[h], cont_ok, S[h])

    P = np.zeros(grid.n)
    P[root] = 1.0
    exp_service = 0.0
    stopped_by = {}
    for h in range(up_h, down_h):
        cont = acts[h]
        mass_cont = float(P[cont].sum())
        mass_stop = float(P[~cont].sum())
        if mass_stop > 1e-12:
            stopped_by[str(h)] = round(mass_stop, 6)
        exp_service += OBL_PER_HOUR * mass_cont
        Q = np.zeros(grid.n)
        w = P * cont / len(day_fr)
        for endi, alive in hour_maps(grid, h, peak, True, day_fr):
            np.add.at(Q, endi, np.where(alive, w, 0.0))
        P = Q
    return {"safe": bool(safe[up_h][root]), "expected_service_per_node": exp_service,
            "expected_dense_hours": exp_service / OBL_PER_HOUR,
            "stopped_mass_by_hour": stopped_by}


# ----------------------------------------------------------------- 普通组合族
def rule_ttl(k_hours: int, up_h: int):
    """固定租约：自应用边沿起密集 k 小时。只看时钟。"""
    return lambda h, grid: np.full(grid.n, (h - up_h) < k_hours, dtype=bool)


def rule_ttl_level(k_hours: int, up_h: int, theta: float):
    """固定租约 + 电量下限，窗口内 k 小时以内且测得电量不低于 theta 时继续。"""
    return lambda h, grid: ((h - up_h) < k_hours) & (grid.soc >= theta - 1e-12)


def plan_safety(peak: float, up_h: int, down_h: int, severity: float, grid: Grid,
                end_hour: int = END_HOUR, reserve_wh: float = 0.0) -> list:
    """`R[h][i]`：在第 h 小时从电量 i 起"密集到窗口末、此后稀疏"能否在**全部声明未来**下存活。

    这就是实测中 `max_feasible_dense_until` / `soc_mpc` 的抽象：开环一次判定，判不可行即终止。
    它是启发式（不求解后续动作序列），因此只能作为普通组合的一员。
    """
    day_fr = tuple(sorted(set(levels(severity))))
    R = [None] * (down_h + 1)
    R[down_h] = sparse_suffix_safety(grid, peak, day_fr, end_hour, reserve_wh)[down_h].copy()
    for h in range(down_h - 1, up_h - 1, -1):
        ok = np.ones(grid.n, dtype=bool)
        for endi, alive in hour_maps(grid, h, peak, True, day_fr):
            ok &= alive & R[h + 1][endi]
        R[h] = ok
    return R


def rule_from_table(table: np.ndarray):
    return lambda h, grid, t=table: t


def ordinary_family(peak: float, up_h: int, down_h: int, severity: float, grid: Grid | None = None,
                    end_hour: int = END_HOUR) -> dict:
    """声明有限族：固定租约、租约+电量下限、滚动预期门。逐一求值，取可行的最优。"""
    grid = grid or Grid()
    lv = levels(severity)
    day_fr = tuple(sorted(set(lv)))
    S = sparse_suffix_safety(grid, peak, day_fr, end_hour)
    W = down_h - up_h
    # **不按窗口长度截断**：租约长于窗口正是现行 TTL8 的形态，把它排除会让普通组合人为变弱。
    cands = [(f"ttl{k}", rule_ttl(k, up_h)) for k in DEGREES]
    cands += [(f"ttl{k}+lvl{int(round(t*1e6))}u", rule_ttl_level(k, up_h, t))
              for k in DEGREES for t in THETAS]
    R = plan_safety(peak, up_h, down_h, severity, grid, end_hour)
    cands.append(("rolling_expected_dense_to_window_end", rule_from_table(R[up_h])))  # reserve 0
    members = []
    for name, rule in cands:
        ev = evaluate_rule(peak, up_h, down_h, rule, severity, grid=grid, S=S, end_hour=end_hour)
        members.append({"name": name, "safe": ev["safe"],
                        "service_per_node": ev["expected_service_per_node"]})
    safe = [m for m in members if m["safe"]]
    best = max(safe, key=lambda m: (m["service_per_node"], m["name"])) if safe else None
    ties = sorted(m["name"] for m in safe
                  if best is not None and abs(m["service_per_node"] - best["service_per_node"]) < 1e-9)
    return {"window_hours": W, "window_obligations_per_node": OBL_PER_HOUR * W,
            "n_members": len(members), "n_safe": len(safe),
            "members": sorted(members, key=lambda m: (-m["safe"], -m["service_per_node"])),
            "best_ties": ties, "best": best}


# ----------------------------------------------------------------- 全知参照（蒙特卡洛）
_OMNI_CACHE: dict = {}


def omniscient_reference(peak: float, up_h: int, down_h: int, severity: float = CLOUD_SIGMA,
                         n_paths: int = MC_PATHS, seed: int = MC_SEED,
                         end_hour: int = END_HOUR) -> dict:
    """逐未来最优：每条采样路径取"仍能存活的最大密集小时数"，再对路径平均。

    蒙特卡洛估计，**是参照不是上界**：它给的是"知道未来时能做到多少"的估计。
    """
    key = (peak, up_h, down_h, severity, n_paths, seed, end_hour)
    if key in _OMNI_CACHE:
        return _OMNI_CACHE[key]
    rng = np.random.default_rng(seed)
    W = down_h - up_h
    lv = levels(severity)
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
    out = {"paths": n_paths, "seed": seed, "levels": list(lv),
           "mean_max_dense_hours": float(best_k.mean()),
           "mean_service_per_node": float(OBL_PER_HOUR * best_k.mean()),
           "p_max_k": {str(k): float((best_k == k).mean()) for k in range(W + 1)},
           "note": "per-future optimum, Monte-Carlo averaged; a reference, not an upper bound"}
    _OMNI_CACHE[key] = out
    return out


# ----------------------------------------------------------------- 非预知性判别
def nonanticipation_probe(peak: float, up_h: int, down_h: int, severity: float,
                          pol: dict, split_hour: int | None = None) -> dict:
    """两个未来在分叉前必须给出同一个动作。

    造两条未来：`split_hour` 之前同为**高档**因子，之后一条转低档、一条保持高档。分别用 DP 规则
    推进，比较逐小时的动作序列：分叉之前必须逐位相同，分叉之后才允许不同。
    """
    grid = Grid()
    day_fr = tuple(sorted(set(levels(severity))))
    lo, hi = day_fr[0], day_fr[-1]
    split_hour = split_hour or up_h
    out = {}
    for name, after in (("stays_high", hi), ("drops_low", lo)):
        f = {}
        for h in range(END_HOUR):
            f[h] = hi if h < split_hour else after
        soc = CAP_WH
        acts = []
        for h in range(END_HOUR):
            dense = policy_dense(pol, h, int(grid.idx(soc)), up_h, down_h)
            acts.append(bool(dense))
            if is_daylight_hour(h):
                soc, _ = hour_step(soc, h, dense, f[h], peak)
        out[name] = {"actions_by_hour": {str(h): a for h, a in enumerate(acts) if a},
                     "soc_at_split": None}
    a, b = out["stays_high"]["actions_by_hour"], out["drops_low"]["actions_by_hour"]
    agree_before = all(a.get(str(h)) == b.get(str(h)) for h in range(split_hour))
    return {"split_hour": split_hour, "levels": [lo, hi],
            "agree_before_split": bool(agree_before),
            "stays_high": a, "drops_low": b}


# ----------------------------------------------------------------- 可手算核例
#: 核例是**声明**的仪器检查实例，不复现实测数值。设计目标：让"第一小时的实际结果决定后续能否
#: 续租"这一边际权衡真的出现——由边缘电量 `soc_edge` 与终末保留量 `reserve_wh` 两个声明旋钮夹出。
CORE = dict(peak=0.012, up_h=2, down_h=4, severity=0.06, quantum=1e-4, end_hour=4,
            soc_edge=0.0025, reserve_wh=0.0021,
            note="仪器检查实例：核对 DP 递推，并证明仪器在存在可实现差额时有分辨力")


def reachable_states(peak: float, up_h: int, down_h: int, severity: float, grid: Grid,
                     soc_root: float) -> dict:
    """窗口内每个决策小时上**有正概率到达**的网格状态（规则只在这些格上被问到）。"""
    day_fr = tuple(sorted(set(levels(severity))))
    states = {up_h: {int(grid.idx(soc_root))}}
    for h in range(up_h, down_h):
        nxt = set()
        for i in sorted(states[h]):
            for dense in (False, True):
                for endi, _alive in hour_maps(grid, h, peak, dense, day_fr):
                    nxt.add(int(endi[i]))
        if h + 1 < down_h:
            states[h + 1] = nxt
    return states


def brute_force_reachable(peak: float, up_h: int, down_h: int, severity: float, grid: Grid,
                          soc_root: float, end_hour: int, reserve_wh: float = 0.0) -> dict:
    """在可达决策格上**穷举每一条规则**，独立核对 DP。

    规则是 `(小时, 量化电量) -> 继续/终止` 的函数，只在这些格上被问到，因此穷举
    `2^(可达格数)` 就覆盖了全部不同的规则。规模由可达格数决定，与电量网格分辨率无关。
    """
    day_fr = tuple(sorted(set(levels(severity))))
    S = sparse_suffix_safety(grid, peak, day_fr, end_hour, reserve_wh)
    states = reachable_states(peak, up_h, down_h, severity, grid, soc_root)
    cells = [(h, i) for h in range(up_h, down_h) for i in sorted(states[h])]
    best, n_safe = None, 0
    for mask in range(1 << len(cells)):
        on = {(h, i) for b, (h, i) in enumerate(cells) if (mask >> b) & 1}

        def rule(h, g, on=on):
            arr = np.zeros(g.n, dtype=bool)
            for (hh, ii) in on:
                if hh == h:
                    arr[ii] = True
            return arr

        ev = evaluate_rule(peak, up_h, down_h, rule, severity, grid=grid, S=S,
                           soc_root=soc_root, end_hour=end_hour, reserve_wh=reserve_wh)
        if ev["safe"]:
            n_safe += 1
            if best is None or ev["expected_service_per_node"] > best["service_per_node"]:
                best = {"mask": mask, "service_per_node": ev["expected_service_per_node"],
                        "continue_at": sorted([list(c) for c in on])}
    return {"n_cells": len(cells), "cells": [list(c) for c in cells],
            "enumerated_rules": 1 << len(cells), "safe_rules": n_safe,
            "best": best,
            "reachable_states_by_hour": {str(h): sorted(states[h]) for h in states}}


def core_instance(verbose: bool = False) -> dict | None:
    """核例：2 个窗口小时、3 档天气、地平线 4 小时，量级小到可手算。

    规模小到可以把**可达决策格上的每一条规则**枚举出来，因此 DP 可以被独立核对。
    """
    p = CORE
    grid = Grid(p["quantum"])
    lv = levels(p["severity"])
    day_fr = tuple(sorted(set(lv)))
    E = p["end_hour"]
    root_soc = p["soc_edge"]
    bf = brute_force_reachable(p["peak"], p["up_h"], p["down_h"], p["severity"], grid,
                               root_soc, E, p["reserve_wh"])
    dp = solve_nonprescient(p["peak"], p["up_h"], p["down_h"], p["severity"],
                            quantum=p["quantum"], soc_root=root_soc, grid=grid, end_hour=E,
                            reserve_wh=p["reserve_wh"])
    dpv = dp["expected_service_per_node"] if dp["admissible"] else 0.0
    best_ttl = None
    for k in range(p["down_h"] - p["up_h"] + 1):
        ev = evaluate_rule(p["peak"], p["up_h"], p["down_h"], rule_ttl(k, p["up_h"]),
                           p["severity"], quantum=p["quantum"], grid=grid, soc_root=root_soc,
                           end_hour=E, reserve_wh=p["reserve_wh"])
        if ev["safe"] and (best_ttl is None or ev["expected_service_per_node"] > best_ttl[1]):
            best_ttl = (k, ev["expected_service_per_node"])
    out = {"declared": {k: v for k, v in p.items()}, "level_factors": list(lv),
           "hour_clear_wh": round(hour_clear_wh(p["up_h"], p["peak"]), 8),
           "hour_harvest_wh": {f"f={round(f, 4)}": round(hour_clear_wh(p["up_h"], p["peak"]) * f, 8)
                               for f in lv},
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


# ----------------------------------------------------------------- 临界严重度
def sparse_only_safe(peak: float, up_h: int, severity: float, soc0: float = CAP_WH) -> bool:
    """只剩最稀疏职责（全程稀疏）时，最坏未来是否仍能存活。

    共同过去按名义因子（声明），应用边沿之后按**低档**因子——这是声明集合里对生存最不利的未来。
    """
    f = {h: CLOUD_NOMINAL for h in range(up_h)}
    f.update({h: CLOUD_NOMINAL - severity for h in range(up_h, END_HOUR)
              if is_daylight_hour(h)})
    return survives(path_trace(soc0, (), f, peak))


def critical_severity(peak: float, up_h: int, down_h: int, grid: Grid | None = None,
                      hi: float = 0.30, steps: int = 22) -> dict:
    """二分两个边界：满窗租约仍安全的 `s_full`，以及全程稀疏仍安全的 `s_sparse`。"""
    grid = grid or Grid()
    W = down_h - up_h
    ttl_full = rule_ttl(W, up_h)

    def full_ok(sev: float) -> bool:
        ev = evaluate_rule(peak, up_h, down_h, ttl_full, sev, grid=grid)
        return bool(ev["safe"])

    def bisect(pred) -> float | None:
        if not pred(0.0):
            return None
        if pred(hi):
            return hi
        a, b = 0.0, hi
        for _ in range(steps):
            mid = (a + b) / 2.0
            if pred(mid):
                a = mid
            else:
                b = mid
        return round(a, 6)

    return {"s_full_window_lease": bisect(full_ok),
            "s_sparse_only": bisect(lambda s: sparse_only_safe(peak, up_h, s)),
            "measured_sigma": CLOUD_SIGMA, "search_hi": hi}


# ----------------------------------------------------------------- 单元
def cell(phase: str, peak: float, severity: float) -> dict:
    p = PHASES[phase]
    up_h, down_h = p["up_h"], p["down_h"]
    grid = Grid()
    lv = levels(severity)
    day_fr = tuple(sorted(set(lv)))
    S = sparse_suffix_safety(grid, peak, day_fr)
    root_soc = soc_at_apply_edge(peak, up_h)
    dp = solve_nonprescient(peak, up_h, down_h, severity, grid=grid, soc_root=root_soc)
    dp_rule = (lambda h, g, pol=dp["_pol"]: pol[h] if h in pol else np.zeros(g.n, dtype=bool))
    ver = evaluate_rule(peak, up_h, down_h, dp_rule, severity, grid=grid, S=S, soc_root=root_soc)
    dp_svc = dp["expected_service_per_node"] if dp["admissible"] else None
    fam = ordinary_family(peak, up_h, down_h, severity, grid=grid)
    omni = omniscient_reference(peak, up_h, down_h, severity)
    ord_svc = fam["best"]["service_per_node"] if fam["best"] else None
    omni_svc = omni["mean_service_per_node"]
    W = down_h - up_h
    gaps = None
    if dp_svc is not None and ord_svc is not None:
        gaps = {"implementable_strategy_per_node": dp_svc - ord_svc,
                "information_per_node": omni_svc - dp_svc,
                "total_per_node": omni_svc - ord_svc,
                "protection_cost_per_node": OBL_PER_HOUR * W - dp_svc,
                "identity_residual": (omni_svc - dp_svc) + (dp_svc - ord_svc) - (omni_svc - ord_svc)}
    return {
        "phase": phase, "peak_wh_per_h": peak, "severity": severity,
        "window_hours": W, "window_obligations_per_node": OBL_PER_HOUR * W,
        "window_obligations_network_per_seed": OBL_PER_HOUR * W * NODES,
        "soc_at_apply_edge": round(root_soc, 6),
        "nonprescient": {"admissible": dp["admissible"], "service_per_node": dp_svc,
                         "expected_dense_hours": dp["expected_dense_hours"],
                         "rule_continue_if_wh": dp["rule_continue_if_wh"],
                         "selfcheck_service_agrees": (
                             dp_svc is not None
                             and abs(ver["expected_service_per_node"] - dp_svc) < 1e-9)},
        "critical_severity": critical_severity(peak, up_h, down_h, grid=grid),
        "ordinary": {"name": fam["best"]["name"] if fam["best"] else None,
                     "service_per_node": ord_svc, "best_ties": fam["best_ties"],
                     "n_safe_of": [fam["n_safe"], fam["n_members"]],
                     "candidates": fam["members"]},
        "omniscient": omni,
        "gaps": gaps,
        "nominal_only_service_per_node": None,
    }


def main() -> int:
    if "--core" in sys.argv:
        core_instance(verbose=True)
        return 0
    out = {
        "model": {
            "constants": {"cap_wh": CAP_WH, "sample_wh": SAMPLE_WH,
                          "load_sparse_wh_per_h": LOAD_SPARSE_H, "load_dense_wh_per_h": LOAD_DENSE_H,
                          "cloud_nominal": CLOUD_NOMINAL, "cloud_sigma": CLOUD_SIGMA,
                          "obligations_per_node_hour": OBL_PER_HOUR, "nodes": NODES,
                          "end_hour": END_HOUR, "quantum_wh": Q_SOC,
                          "mc_paths": MC_PATHS, "mc_seed": MC_SEED},
            "action_space": "窗口内每小时：继续密集 | 终止（终止后永久稀疏，不得重入）",
            "information_set": "(相对小时, 量化剩余电量)；不含未来采能、授权终点、中心在线状态",
            "risk": "声明全部未来下均不死亡（任一拍 soc < sample_wh 即判死，环境口径）",
            "objective": "期望服务 = 12 × 期望密集小时数；不得删除义务",
            "boundaries": [
                "服务 = 黄级义务被采集，不含投递链路折损（实测采集 535/672、投递 283/672）",
                "云遮按小时取因子（逐拍抖动被抹掉）；三点等权矩匹配；severity 是旋钮",
                "单节点切片，不含多节点竞争、网关打包与回传",
                "起始电量取满值（实测 initial_soc=1.0）",
                "动作能力限于一次租约；不含重入与单次采样控制",
            ],
        },
        "peaks": list(PEAKS), "severities": list(SEVERITIES),
        "degrees": list(DEGREES), "thetas": list(THETAS),
        "cells": {}, "nonanticipation": {}, "core": core_instance(),
    }
    for phase in PHASES:
        for peak in PEAKS:
            for sev in SEVERITIES:
                c = cell(phase, peak, sev)
                nom = solve_nonprescient(peak, PHASES[phase]["up_h"], PHASES[phase]["down_h"], 0.0)
                c["nominal_only_service_per_node"] = (nom["expected_service_per_node"]
                                                      if nom["admissible"] else None)
                out["cells"][f"{phase}|{peak}|{sev}"] = c
                if phase == "A" and peak == 0.012 and sev == CLOUD_SIGMA:
                    dp = solve_nonprescient(peak, PHASES[phase]["up_h"], PHASES[phase]["down_h"], sev)
                    out["nonanticipation"][f"{phase}|{peak}|{sev}"] = nonanticipation_probe(
                        peak, PHASES[phase]["up_h"], PHASES[phase]["down_h"], sev, dp["_pol"])
                dpv = c["nonprescient"]["service_per_node"]
                print(f"{phase} p={peak:<6} sev={sev:<5} W={c['window_hours']} "
                      f"DP={dpv if dpv is None else round(dpv, 2)!s:>7} "
                      f"ORD={c['ordinary']['service_per_node'] if c['ordinary']['service_per_node'] is None else round(c['ordinary']['service_per_node'], 2)!s:>7}"
                      f"({c['ordinary']['name']}) "
                      f"OMNI={round(c['omniscient']['mean_service_per_node'], 2):>7} "
                      f"strat={None if not c['gaps'] else round(c['gaps']['implementable_strategy_per_node'], 2)} "
                      f"info={None if not c['gaps'] else round(c['gaps']['information_per_node'], 2)} "
                      f"selfcheck={c['nonprescient']['selfcheck_service_agrees']}", flush=True)
    os.makedirs(os.path.join(REPO, "results"), exist_ok=True)
    path = os.path.join(REPO, "results", "c5_seqref.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("saved", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
