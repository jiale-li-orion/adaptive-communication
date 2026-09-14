#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2gate 世界生成器（确定性、种子驱动）。规则能力阶梯 + seen/held 开放世界对照。

研究问题（04 号文，pre-LLM 校准细化见 04b）：价值需从语境组合推断时，要多少"结构化"才到顶？
  规则阶梯：rule_linear（固定加性权重，无组合） < rule_keyword（读文本但只做单信号加分、
            不做 AND） < rule_tree（领域专家把**已知**机理写成显式 if-then 组合） < oracle。
  LLM 零样本，不给它写 if-then。三档世界：
    R 纯随机、真值=线性 ⇒ 所有规则到顶（构造性负对照 F1）。
    S(seen) 分层对照，组合全是 rule_tree **覆盖**的已知原型 ⇒ rule_tree 应≈oracle
            （"知识写成规则即解"），而 linear/keyword 有遗憾。
    H(held) 含一个 rule_tree **未写**的组合变体 hidden_residual（雨峰过后、隐患中等、
            低速率却持续加速的滞后蠕变）⇒ rule_tree 也漏，是 LLM 唯一可能追回残差的格子。
关键迷惑项 distractor_lookalike：词面也"加速+隐患高"，但与雨峰同相位（雨增强）⇒ 雨驱虚高；
  单信号关键词会像抬真临滑一样抬它（无法 AND/NOT 区分雨相位），组合规则与语义理解能区分。
所有决策者只看 x、c 文本；真值 v*、原型标签、combo 仅评分/oracle 可见。
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from knapsack import grouped_knapsack, options_from_values

# 一个北斗包汇总多节点：摘要 48B、完整 72B，200B 严格最多装 4 条（4*48=192）⇒ n=8 舍一半。
S_FULL, S_DIGEST, B_BUDGET = 72, 48, 200
RHO_MAIN = 0.7
ALPHA_MAIN = 0.5
ALPHA_GRID = [0.0, 0.25, 0.5, 0.75]

W_R: Dict[str, float] = {"vel": 0.34, "acc": 0.26, "haz": 0.20,
                         "stale": 0.10, "rain": 0.06, "health_bad": 0.04}
A_ENDO, B_PEAK, B_DRIVE, C_FAULT = 0.55, 0.5, 0.42, 0.46


def _clip(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


@dataclass
class Candidate:
    cid: int
    ptype: str
    x: Dict[str, float]
    text: str
    v_star: float = 0.0
    hidden: Dict[str, float] = field(default_factory=dict)


def _z(x):
    return {"vel": _clip(x["vel"] / 40.0, 0, 1), "acc": _clip((x["acc"] + 1) / 2.0, 0, 1),
            "rain": _clip(x["rain"] / 70.0, 0, 1), "stale": _clip(x["stale"] / 24.0, 0, 1),
            "haz": _clip(x["haz"] / 2.0, 0, 1), "health_bad": _clip(1 - x["health"], 0, 1)}


def linear_base(x):
    z = _z(x)
    return sum(W_R[k] * z[k] for k in W_R)


def _memberships(x, z):
    # 内生加速看加速度×非雨峰相位×隐患，**不乘当前速率**：速率尚低但加速强正是临滑前兆
    m_endo = z["acc"] * (1.0 if x["rain_trend"] <= 0 else 0.2) * (0.4 + 0.6 * z["haz"])
    m_peak = z["acc"] * z["rain"] * (1.0 if x["rain_trend"] == 1 else 0.15)  # 与雨峰同相=雨驱
    m_drive = z["vel"] * z["rain"] * (1.0 if x["rain_trend"] == 1 else 0.2) * (1 - z["haz"])
    m_fault = z["health_bad"] * z["vel"] * (1 - z["acc"])
    return m_endo, m_peak, m_drive, m_fault


def combo_base(x):
    z = _z(x)
    me, mp, md, mf = _memberships(x, z)
    return _clip(linear_base(x) + A_ENDO * me - B_PEAK * mp - B_DRIVE * md - C_FAULT * mf, 0, 1.08)


def _scale(b):
    return 100.0 * _clip(b, 0, 1.08) ** 0.8


def _make_text(cid, x):
    trend = {1: "雨势增强", 0: "雨势平稳", -1: "雨势减弱"}[int(x["rain_trend"])]
    acc_word = "仍在加速" if x["acc"] > 0.25 else "趋于平稳" if x["acc"] < -0.25 else "变化平缓"
    haz_word = {0: "历史隐患低", 1: "历史隐患中", 2: "历史隐患高"}[int(x["haz"])]
    health_word = "设备健康" if x["health"] > 0.85 else "设备一般" if x["health"] > 0.7 else "设备状态差"
    return (f"#{cid} 位移速率{x['vel']:.1f}mm/d且{acc_word}，雨强{x['rain']:.0f}mm/h（{trend}），"
            f"距上次成功上报{x['stale']:.0f}h，{health_word}，{haz_word}")


def _sample_x(rng, ptype, link=False):
    g = lambda mu, sd, lo, hi: _clip(rng.gauss(mu, sd), lo, hi)
    if ptype == "anchor_high":
        return dict(vel=g(27, 5, 10, 45), acc=g(0.5, 0.18, -1, 1), rain=g(22, 10, 0, 60),
                    rain_trend=rng.choice([-1, 0]), stale=g(13, 4, 0, 24),
                    health=g(0.92, 0.04, 0.7, 1), haz=rng.choice([1, 2]), slack=rng.randint(60, 1800))
    if ptype == "anchor_low":
        return dict(vel=g(5, 3, 0.1, 14), acc=g(-0.3, 0.2, -1, 1), rain=g(10, 7, 0, 35),
                    rain_trend=rng.choice([-1, 0, 1]), stale=g(4, 3, 0, 24),
                    health=g(0.95, 0.03, 0.7, 1), haz=0, slack=rng.randint(60, 1800))
    if ptype == "distractor_rain":                          # 高vel+暴雨增强+无隐患
        return dict(vel=g(32, 5, 20, 50), acc=g(-0.1, 0.2, -1, 1), rain=g(56, 8, 35, 80),
                    rain_trend=1, stale=g(8, 5, 0, 24), health=g(0.9, 0.05, 0.7, 1),
                    haz=0, slack=rng.randint(60, 1800))
    if ptype == "distractor_lookalike":                     # 词面像临滑(加速+隐患高)但雨增强=雨驱
        return dict(vel=g(15, 3, 8, 24), acc=g(0.6, 0.1, 0.45, 1), rain=g(50, 9, 30, 80),
                    rain_trend=1, stale=g(9, 5, 0, 24), health=g(0.9, 0.05, 0.7, 1),
                    haz=2, slack=rng.randint(60, 1800))
    if ptype == "hidden_endo":                             # 加速+隐患高+雨减弱=真临滑(seen)
        return dict(vel=g(16, 4, 8, 26), acc=g(0.72, 0.1, 0.5, 1), rain=g(18, 8, 0, 40),
                    rain_trend=-1, stale=g(9, 5, 0, 24), health=g(0.92, 0.04, 0.75, 1),
                    haz=2, slack=rng.randint(60, 1800))
    if ptype == "hidden_residual":                         # held：雨峰过后+隐患中+低速持续加速
        return dict(vel=g(11, 3, 4, 18), acc=g(0.66, 0.1, 0.45, 1), rain=g(12, 6, 0, 32),
                    rain_trend=-1, stale=g(10, 5, 0, 24), health=g(0.92, 0.04, 0.75, 1),
                    haz=1, slack=rng.randint(60, 1800))
    raise ValueError(ptype)


def _true_value(x, regime, alpha):
    z = _z(x)
    lin = linear_base(x); combo = combo_base(x)
    true = lin if regime == "R" else (1 - alpha) * lin + alpha * combo
    me, mp, md, mf = _memberships(x, z)
    return true, dict(true=true, lin=lin, combo=combo, me=me, mp=mp, md=md, mf=mf)


_TARGET = {
    "anchor_high":         dict(lin=(0.60, 0.72), true_min=0.55),
    "anchor_low":          dict(lin=(0.14, 0.29), true_max=0.40),
    "distractor_rain":     dict(lin=(0.53, 0.60), combo_max=0.26),
    "distractor_lookalike":dict(lin=(0.54, 0.61), combo_max=0.36),
    "hidden_endo":         dict(lin=(0.44, 0.52), combo_min=0.62),
    "hidden_residual":     dict(lin=(0.28, 0.37), combo_min=0.68),
}
# 200B 最优装 3 条（2full+1digest）。只放 1 个高锚点，使"应选"高真值候选恰为 3：
#   S：high + 2 hidden_endo（规则树能识别 endo ⇒ 到顶）
#   H：high + hidden_endo + hidden_residual（规则树不识别 residual ⇒ 残差）
_LAYOUT = {
    "S": ["anchor_high"] + ["anchor_low"] * 3 + ["distractor_rain",
         "distractor_lookalike"] + ["hidden_endo"] * 2,
    "H": ["anchor_high"] + ["anchor_low"] * 3 + ["distractor_rain",
         "distractor_lookalike", "hidden_endo", "hidden_residual"],
}


def _random_R(rng, n):
    cands = []
    for i in range(n):
        x = {"vel": _clip(rng.gauss(14, 12), 0.1, 60), "acc": _clip(rng.gauss(0, 0.6), -1, 1),
             "rain": _clip(rng.gauss(28, 22), 0, 80),
             "rain_trend": rng.choices([-1, 0, 1], weights=[0.3, 0.4, 0.3])[0],
             "stale": _clip(rng.gauss(9, 6), 0, 24), "health": _clip(rng.gauss(0.9, 0.1), 0.55, 1),
             "haz": rng.choices([0, 1, 2], weights=[0.5, 0.35, 0.15])[0], "slack": rng.randint(60, 1800)}
        true, hid = _true_value(x, "R", 0.0)
        cands.append(Candidate(i, "random", x, _make_text(i, x), _scale(true), hid))
    return cands


def _sample_role(rng, ptype, regime, alpha, tries=400):
    t = _TARGET[ptype]
    for _ in range(tries):
        x = _sample_x(rng, ptype)
        lin, combo = linear_base(x), combo_base(x)
        true, hid = _true_value(x, regime, alpha)
        if not (t["lin"][0] <= lin <= t["lin"][1]):
            continue
        if t.get("combo_min") and combo < t["combo_min"]:
            continue
        if "combo_max" in t and combo > t["combo_max"]:
            continue
        if t.get("true_min") and true < t["true_min"]:
            continue
        if "true_max" in t and true > t["true_max"]:
            continue
        return x, true, hid
    return None


def _build_candidate(rng, ptype, cid, regime, alpha):
    got = _sample_role(rng, ptype, regime, alpha)
    if got is None:
        return None
    x, true, hid = got
    return Candidate(cid, ptype, x, _make_text(cid, x), _scale(true), hid)


def _stratified(rng, regime, alpha, n=8, rho=RHO_MAIN, pool=30, tries=1500):
    """池化构造：每角色只做一次内层拒绝采样建候选池，再快速组合验收（避免整实例重采）。"""
    layout = _LAYOUT[regime]
    pools = {}
    for pt in dict.fromkeys(layout):
        lst, att = [], 0
        while len(lst) < 10 and att < 600:      # 持续补采到每型≥10，杜绝空池/空实例
            att += 1
            c = _build_candidate(rng, pt, 0, regime, alpha)
            if c is not None:
                lst.append(c)
        assert lst, f"empty pool for {pt}"
        pools[pt] = lst

    def pack(cands, opt_fn):
        opts = options_from_values(list(range(n)), S_FULL, S_DIGEST, rho,
                                   lambda i, _f: opt_fn(cands[i]))
        _, choices = grouped_knapsack(opts, B_BUDGET)
        return choices

    for _ in range(tries):
        chosen, used = [], {}
        for j, pt in enumerate(layout):
            idx = rng.randrange(len(pools[pt]))
            src = pools[pt][idx]
            c = Candidate(j, pt, dict(src.x), _make_text(j, src.x), src.v_star, dict(src.hidden))
            chosen.append(c)
        cands = chosen
        ch_o = pack(cands, lambda c: c.v_star)
        ch_lin = pack(cands, rule_linear_value)
        ch_tree = pack(cands, rule_tree_value)

        def gap(ch):
            s_o = sum(_cv(c, ch_o[i], rho) for i, c in enumerate(cands))
            s = sum(_cv(c, ch[i], rho) for i, c in enumerate(cands))
            return (s_o - s) / s_o if s_o > 0 else 0
        g_lin, g_tree = gap(ch_lin), gap(ch_tree)
        types = [c.ptype for c in cands]
        if regime == "S":
            hidden = [i for i, t in enumerate(types) if t.startswith("hidden")]
            ok = (all(ch_o[i] is not None for i in hidden)
                  and all(ch_lin[i] is None for i in hidden)
                  and 0.08 <= g_lin <= 0.32 and g_tree <= 0.04)
        else:
            resid = [i for i, t in enumerate(types) if t == "hidden_residual"]
            ok = (all(ch_o[i] is not None for i in resid)
                  and all(ch_lin[i] is None and ch_tree[i] is None for i in resid)
                  and 0.08 <= g_lin <= 0.36 and 0.05 <= g_tree <= 0.30)
        if ok:
            return cands, True
    return cands, False


def _cv(c, ch, rho):
    return c.v_star if ch == "full" else rho * c.v_star if ch == "digest" else 0.0


def gen_instance(rng, regime, n=8, alpha: Optional[float] = None):
    alpha = ALPHA_MAIN if alpha is None else alpha
    if regime == "R":
        return _random_R(rng, n)
    cands, ok = _stratified(rng, regime, alpha, n)
    if not ok:
        for c in cands:
            c.ptype += "_UNBAL"
    return cands


# ── 三个规则臂的价值函数（信息相同：x 与文本；结构化程度递增） ──
def rule_linear_value(cand):
    return _scale(linear_base(cand.x))


def rule_keyword_value(cand):
    """单信号关键词加分：识词、**不做词间 AND/NOT**（无法区分雨相位）。"""
    x, t, v = cand.x, cand.text, linear_base(cand.x)
    if "仍在加速" in t:
        v += 0.06
    if "历史隐患高" in t:
        v += 0.05
    if "雨势增强" in t:
        v -= 0.02
    if "设备状态差" in t:
        v -= 0.02
    return _scale(v)


def rule_tree_value(cand):
    """显式组合规则：专家把**已知**机理写成离散 if-then（覆盖 seen，未写 held 变体）。"""
    x, v = cand.x, linear_base(cand.x)
    if x["acc"] > 0.5 and x["haz"] == 2 and x["rain_trend"] <= 0:    # 内生临滑（seen）
        v += 0.18
    if x["acc"] > 0.45 and x["rain_trend"] == 1 and x["rain"] > 35:  # 雨峰同相位加速=雨驱
        v -= 0.16
    if x["health"] < 0.7 and x["vel"] > 20 and x["acc"] < 0.2:       # 传感器故障
        v -= 0.13
    # 注：hidden_residual（haz==1、雨峰过后低速持续加速）不在任何已知条目中 ⇒ 不调整
    return _scale(v)
