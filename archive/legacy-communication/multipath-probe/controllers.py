"""controllers.py — 三个控制器。统一接口 decide(view, true_good=None) -> {path: 尝试条数}。

控制器只决定"每条路径这一拍尝试发几条"；发哪些样本由环境按统一 EDF/event 优先出队。
所有控制器都是 view 的纯函数（rule_mpc 每拍从完整尝试历史重算 HMM 信念，无隐藏状态），
因此同一份外生 Trace 下三臂唯一差异就是"状态信息与算法"，严格可比。
"""
from __future__ import annotations

import math
import random
from env import (PATH_SPECS, GOOD_TX_SUCCESS, BAD_TX_SUCCESS, UAV_WINDOWS,
                 UAV_CANCEL_P, ROUTINE_PER_H, EVENT_VALUE, ROUTINE_VALUE)

QG = GOOD_TX_SUCCESS
QB = BAD_TX_SUCCESS
EVENT_MEAN_RATE = (6 * 2 * 12) / 336.0   # 全程 event 平均到达率（控制器不预知具体突发时刻）


def _uav_scheduled(t: int) -> bool:
    hod = t % 24
    return any(a <= hod < b for a, b in UAV_WINDOWS)


def _uav_window_start(t: int) -> int:
    hod = t % 24
    for a, b in UAV_WINDOWS:
        if a <= hod < b:
            return t - (hod - a)
    return -1


class OracleController:
    """上界：看到当前真实好/坏（不预知未来转移、不预知本次随机丢包）。

    只在真实可用路径上发，按 免费→收费 顺序、用 0.95 成功率折算尝试数，从不在坏路径浪费。
    """
    name = "oracle"

    def decide(self, view, true_good=None):
        alloc = {p: 0 for p in view.paths}
        remaining = view.backlog
        if remaining <= 0 or true_good is None:
            return alloc
        # 免费/大带宽优先：uav(窗口内) → cellular → satellite(收费、配额)。
        order = sorted(view.paths, key=lambda p: (PATH_SPECS[p]["money"],
                                                  PATH_SPECS[p]["energy"]))
        for p in order:
            if remaining <= 0:
                break
            spec = PATH_SPECS[p]
            if not true_good.get(p, False):
                continue
            if p == "uav" and not _uav_scheduled(view.t):
                continue
            cap = spec["cap"]
            if p == "satellite":
                cap = min(cap, view.sat_quota_left)
            if cap <= 0:
                continue
            n = min(cap, math.ceil(remaining / QG))
            alloc[p] = n
            remaining -= n * QG  # 期望成功量
        return alloc


def _markov_belief(p, view) -> float:
    """从完整尝试历史重算当前拍的好态后验概率（HMM 滤波，使用真实转移参数）。"""
    spec = view.spec[p]
    p_gb, p_bg = view.ge[p]
    g0 = spec["good_frac"]
    hist = {t: (a, s) for t, a, s in view.history[p]}
    b = g0
    for t in range(view.t + 1):
        if t > 0:
            b = b * (1 - p_gb) + (1 - b) * p_bg if (p_gb > 0 or p_bg > 0) else g0
        if t in hist:
            a, s = hist[t]
            if a > 0:
                lg = QG ** s * (1 - QG) ** (a - s)
                lb = QB ** s * (1 - QB) ** (a - s)
                denom = b * lg + (1 - b) * lb
                b = b * lg / denom if denom > 0 else b
    return min(1.0, max(0.0, b))


def _uav_belief(view) -> float:
    """UAV：窗外 0；窗内以 (1-取消率) 为先验，窗口内状态恒定、只按尝试结果贝叶斯更新。"""
    t = view.t
    if not _uav_scheduled(t):
        return 0.0
    if "uav" not in view.paths:
        return 0.0
    ws = _uav_window_start(t)
    b = 1.0 - UAV_CANCEL_P
    hist = {tt: (a, s) for tt, a, s in view.history["uav"]}
    for tt in range(ws, t + 1):
        if tt in hist:
            a, s = hist[tt]
            if a > 0:
                lg = QG ** s * (1 - QG) ** (a - s)
                lb = QB ** s * (1 - QB) ** (a - s)
                denom = b * lg + (1 - b) * lb
                b = b * lg / denom if denom > 0 else b
    return min(1.0, max(0.0, b))


class RuleMpcController:
    """强规则：HMM 信念 + 期望容量分配 + VOI 主动探测。拿到真实转移参数（偏惠设定）。"""
    name = "rule_mpc"

    def __init__(self, probe_lo=0.3, probe_hi=0.7):
        self.lo, self.hi = probe_lo, probe_hi

    def _belief(self, p, view):
        if PATH_SPECS[p]["kind"] == "contact":
            return _uav_belief(view)
        return _markov_belief(p, view)

    def decide(self, view, true_good=None):
        alloc = {p: 0 for p in view.paths}
        remaining = float(view.backlog)
        if remaining <= 0:
            return alloc
        beliefs = {p: self._belief(p, view) for p in view.paths}
        q = {p: beliefs[p] * QG + (1 - beliefs[p]) * QB for p in view.paths}

        # ---------- 无能量预算：第一版逻辑（货币/能量成本优先 + VOI 探测），保持可复现 ----------
        if not view.energy_budget:
            order = sorted(view.paths, key=lambda p: (PATH_SPECS[p]["money"],
                                                      PATH_SPECS[p]["energy"]))
            for p in order:
                if remaining <= 0.5:
                    break
                spec = PATH_SPECS[p]
                cap = spec["cap"]
                if p == "satellite":
                    cap = min(cap, view.sat_quota_left)
                if p == "uav" and not _uav_scheduled(view.t):
                    continue
                if cap <= 0:
                    continue
                qp = q[p]
                uncertain = self.lo <= beliefs[p] <= self.hi
                need_backup = remaining > PATH_SPECS["cellular"]["cap"] or "cellular" not in view.paths
                if uncertain and need_backup and qp >= QB:
                    alloc[p] += 1
                    cap -= 1
                    remaining -= qp
                if cap > 0 and qp >= QB and remaining > 0.5:
                    n = min(cap, math.ceil(remaining / max(qp, 1e-6)))
                    alloc[p] += n
                    remaining -= n * qp
            return alloc

        # ---------- 有能量硬预算：统一的期望成功/能量 fractional-knapsack（无 ad hoc 分档）----------
        # 目标线：按时间线性耗尽预算；本拍能量额度=可持续速率+盈余摊还，积压可在额度内尽量清。
        hours_left = max(1, view.hours_total - view.t)
        target_left = view.energy_budget * hours_left / view.hours_total
        sustainable = view.energy_left / hours_left
        energy_cap = sustainable + max(0.0, view.energy_left - target_left) / hours_left
        energy_cap = min(energy_cap, view.energy_left)

        cands = []
        for p in view.paths:
            spec = PATH_SPECS[p]
            cap = spec["cap"]
            if p == "satellite":
                cap = min(cap, view.sat_quota_left)
            if p == "uav" and not _uav_scheduled(view.t):
                continue
            if cap <= 0 or q[p] <= QB * (1 + 1e-9):
                continue
            cands.append((q[p] / spec["energy"], p, cap, q[p], spec["energy"]))
        cands.sort(key=lambda x: -x[0])

        spent = 0.0
        for _, p, cap, qp, ecost in cands:
            if remaining <= 0.5:
                break
            need = min(cap, math.ceil(remaining / max(qp, 1e-6)))
            for _ in range(need):
                if spent + ecost > energy_cap + 1e-9:
                    break
                alloc[p] += 1
                spent += ecost
                remaining -= qp
        return alloc


def _ks_alloc(paths, t, qq, ecap, backlog, sat_quota, energy_left):
    """统一的期望成功/能量 fractional-knapsack，任意拍可用（供 MPC 前向复用）。"""
    alloc = {p: 0 for p in paths}
    remaining = float(backlog)
    spent = 0.0
    cands = []
    for p in paths:
        spec = PATH_SPECS[p]
        cap = spec["cap"]
        if p == "satellite":
            cap = min(cap, sat_quota)
        if p == "uav" and not _uav_scheduled(t):
            continue
        if cap <= 0 or qq[p] <= QB * (1 + 1e-9):
            continue
        cands.append((qq[p] / spec["energy"], p, cap, qq[p], spec["energy"]))
    cands.sort(key=lambda x: -x[0])
    for _, p, cap, qp, ec in cands:
        if remaining <= 0.5:
            break
        need = min(cap, math.ceil(remaining / max(qp, 1e-6)))
        for _ in range(need):
            if spent + ec > ecap + 1e-9 or spent + ec > energy_left + 1e-9:
                break
            alloc[p] += 1
            spent += ec
            remaining -= qp
    return alloc, spent


class BeliefMPC(RuleMpcController):
    """传统方法天花板：信念状态随机模型预测控制（receding-horizon）。

    用真实 GE 转移对未来信道做情景采样，在多个"当前拍能量激进系数 α"中选期望目标最优；
    不预知未来 event（用平均到达率）、不看当前真实状态（只用 HMM 信念）。event 用两龄桶
    精确维护 2h 截止期。若连它都追不平 oracle，残差才是规则吃不掉的信息/决策价值。
    """
    name = "belief_mpc"

    def __init__(self, horizon=6, scenarios=12, alphas=(0.4, 0.7, 1.0, 1.4, 2.0, 3.0)):
        super().__init__()
        self.H = horizon
        self.S = scenarios
        self.alphas = alphas
        self._ov = None      # 信念覆盖（cheat 臂注入真实状态点分布；正常臂为 None）

    def decide(self, view, true_good=None):
        if view.backlog <= 0:
            return {p: 0 for p in view.paths}
        if not view.energy_budget:
            return super().decide(view)
        if self._ov is not None:
            b0 = {p: (1.0 if self._ov.get(p) else 0.0) for p in view.paths}
        else:
            b0 = {p: self._belief(p, view) for p in view.paths}
        q0 = {p: b0[p] * QG + (1 - b0[p]) * QB for p in view.paths}
        hl = max(1, view.hours_total - view.t)
        target0 = view.energy_budget * hl / view.hours_total
        sus0 = view.energy_left / hl
        base_cap = sus0 + max(0.0, view.energy_left - target0) / hl
        best_a, best_j = 1.0, -1e18
        for a in self.alphas:
            js = [self._rollout(view, dict(b0), a, s) for s in range(self.S)]
            j = sum(js) / len(js)
            if j > best_j:
                best_j, best_a = j, a
        cap = min(view.energy_left, base_cap * best_a)
        alloc, _ = _ks_alloc(view.paths, view.t, q0, cap, view.backlog,
                             view.sat_quota_left, view.energy_left)
        return alloc

    def _rollout(self, view, bel, alpha, seed_s):
        rng = random.Random(((view.t + 1) << 20) ^ (seed_s * 2654435761 & 0xffffffff)
                            ^ int(alpha * 1000))
        E = view.energy_left
        be = float(view.backlog_event)
        ev1, ev0 = be * 0.5, be * 0.5   # 当前 event 积压对半分入两龄桶（保守）
        ro = float(view.backlog_routine)
        tot = 0.0
        for h in range(self.H):
            tt = view.t + h
            ro += ROUTINE_PER_H
            ev0 += EVENT_MEAN_RATE
            good, qq = {}, {}
            for p in view.paths:
                spec = PATH_SPECS[p]
                if spec["kind"] == "markov":
                    good[p] = rng.random() < bel[p]
                elif p == "uav":
                    good[p] = _uav_scheduled(tt) and rng.random() > UAV_CANCEL_P
                else:
                    good[p] = True
                qq[p] = QG if good[p] else QB
            hl = max(1, view.hours_total - tt)
            tgt = view.energy_budget * hl / view.hours_total
            srate = E / hl
            if h == 0:
                scale = alpha
            else:
                qmax = max(qq.values())     # 后续闭环步：好窗口敢冲、坏窗口储蓄
                scale = 2.0 if qmax >= 0.9 else (1.3 if qmax >= 0.6 else 0.8)
            ecap = min(E, (srate + max(0.0, E - tgt) / hl) * scale)
            alloc, spent = _ks_alloc(view.paths, tt, qq, ecap, ev1 + ev0 + ro,
                                     view.sat_quota_left, E)
            E -= spent
            cap_d = sum(n * (QG if good[p] else QB) for p, n in alloc.items())
            d1 = min(cap_d, ev1); ev1 -= d1; cap_d -= d1; tot += d1 * EVENT_VALUE
            d0 = min(cap_d, ev0); ev0 -= d0; cap_d -= d0; tot += d0 * EVENT_VALUE
            dr = min(cap_d, ro);  ro -= dr; tot += dr * ROUTINE_VALUE
            tot -= ev1 * EVENT_VALUE          # ev1 本步未发即过期（机会成本）
            ev1, ev0 = ev0, 0.0
            for p in view.paths:
                pg, pb = view.ge[p]
                if pg > 0 or pb > 0:
                    bel[p] = bel[p] * (1 - pg) + (1 - bel[p]) * pb
                if alloc.get(p, 0) > 0:
                    bel[p] = 1.0 if good[p] else 0.0
            if E <= 0:
                break
        tot -= (ev1 + ev0) * EVENT_VALUE
        if E < 0:
            tot += E * 20
        return tot


class FixedController:
    """工程现状：固定优先级 + 连续失败阈值切换，无概率、无探测。"""
    name = "fixed"

    def __init__(self, fail_switch=3):
        self.fail_switch = fail_switch

    def _cellular_zero_streak(self, view) -> int:
        h = view.history.get("cellular", [])
        streak = 0
        for t, a, s in reversed(h):
            if a == 0:
                continue
            if s == 0:
                streak += 1
            else:
                break
        return streak

    def decide(self, view, true_good=None):
        alloc = {p: 0 for p in view.paths}
        remaining = view.backlog
        if remaining <= 0:
            return alloc
        # 主路径 cellular 固定发到 cap。
        if "cellular" in view.paths:
            n = min(PATH_SPECS["cellular"]["cap"], remaining)
            alloc["cellular"] = n
            remaining -= n
        switched = self._cellular_zero_streak(view) >= self.fail_switch
        # UAV：仅计划窗口、且 cellular 没清完时用。
        if "uav" in view.paths and _uav_scheduled(view.t) and remaining > 0:
            n = min(PATH_SPECS["uav"]["cap"], remaining)
            alloc["uav"] = n
            remaining -= n
        # satellite：cellular 连续失败达阈值才切换兜底。
        if "satellite" in view.paths and (switched or "cellular" not in view.paths) and remaining > 0:
            n = min(PATH_SPECS["satellite"]["cap"], view.sat_quota_left, remaining)
            alloc["satellite"] = n
            remaining -= n
        return alloc


CONTROLLERS = {c.name: c for c in (OracleController, RuleMpcController, FixedController)}
