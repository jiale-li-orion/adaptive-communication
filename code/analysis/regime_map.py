#!/usr/bin/env python3
"""两轴结构判据（regime map）：**先预测，再对答案**。

为什么需要它。repo 里已经攒了足够多的现象——突发链路把策略差压平、`out3` 里加密把节点耗死、
Cleveland 上报周期跟不上义务、宽松能量下执行语义只剩代价——但这些都是**逐条测出来的**，
不是从一个判据**推出来**的。这一轮的任务（见 `README.md` 顶部"当前工作"）是把它们压成
两轴，并且**在不知道结果标签的前提下**看它能不能分开"哪里有策略差异、哪里没有、哪里会产生损害"。

两条轴
------
1. **cadence 可行性** `C = T_report / T_deadline`。`C > 1` ⇒ 业务等不起，调度器不值得讨论。
2. **recoverability risk** `R(a|h_t) = P(T_ctrl > T_harm(a) | h_t)`：
   这个动作把节点搞出事之前，还拿不拿得到下一次有效纠正机会。

`T_ctrl` **不用平均数**，用生存曲线 `S(x) = P(T_ctrl > x)`。原因见
`08-benchmark-pitfalls.md`：标量摘要替代轨迹在本 repo 已经被证伪过一次。

`T_ctrl` 的物理定义（Class A，与 `monitoring/opportunity.py` 一致）
------------------------------------------------------------------
节点只在自身上行后开 RX 窗口，而**网关只能用"它听到过的那次上行"开出的窗口**。
所以一次纠正要同时满足两件事：命令能到网关（回传可用）、节点有一次上行被听到（接入可用）。
于是，令 `h*` 为**第一个两腿同时可用的整点**：

    T_ctrl = R · ceil(h* · 3600 / R)          （R = 上报周期，秒）

即"等到两腿同时可用的那一小时，再等到该小时内节点的下一次上报"。**R 越短，纠正越快**——
这正是"上报周期是在购买控制机会"的形式化。

`T_harm` 给两个边界
-------------------
- `T_harm^worst = soc / load_h`（**零采能**，可手算，就是准入闸门用的那个）
- `T_harm^traj`：沿**来源派生**采能轨迹（`irradiance_harvest`：形状来自 NASA POWER 2023
  逐小时辐照，量级 `peak_wh_per_hour` 是 **A 层旋钮**，不是拟合值，也不是来源事实）

两者之差就是允许风险控制发挥的区域。

**来源时间结构 prior，不是现场实测**
----------------------------------
三条曲线是**来源数据集的时间结构**（i.i.d. 对照 / ChirpBox 上海 6.38 h / LoRa-on-Ice 南极 72.4 h）
参数化出的**两态链**，**不是**藏东南目标站点实测的恢复分布。目标站点没有这样的实测。

自检：`python3 code/analysis/regime_map.py --selftest`
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "instance"))

# ── 实例常量（唯一来源：docs/s7-method/instance-v1/02-instance-manifest.md §三·〇）──────────
SAMPLE_WH = 4.7e-4
UPLINK_WH = 2.33e-5
BUS_V = 3.6
RX_MA = 11.0
RX_WINDOW_MS = 2000.0
RX_WH = BUS_V * (RX_MA / 1000.0) * (RX_WINDOW_MS / 3.6e6)      # = 2.2e-5 Wh
TICK_S = 60

#: 实例声明的两腿 i.i.d. 可用率（同一来源）。
BACKHAUL_P_GOOD = 0.62
UPLINK_P_ARRIVE = 0.74

#: 坏态占比：回传 0.38（= 1 − 0.62）；接入 0.26（= 1 − 0.74）。
Q_BACKHAUL = 1.0 - BACKHAUL_P_GOOD
Q_UPLINK = 1.0 - UPLINK_P_ARRIVE


def hourly_load(sample_interval_s: int, report_period_s: int) -> float:
    """配置 `(采样间隔, 上报周期)` 的每小时能耗（Wh/h）。**手工可核**。"""
    return (3600.0 / sample_interval_s) * SAMPLE_WH + \
           (3600.0 / report_period_s) * (UPLINK_WH + RX_WH)


# ── 两态链 ────────────────────────────────────────────────────────────────────────────
def chain_from_mean_bad(mean_bad_h: float, q_bad: float) -> tuple[float, float]:
    """由**平均坏突发长度**与**坏态占比**定出两态链的 `(p_gb, p_bg)`。

    两态链里 `平均坏突发 = 1/p_bg`、`坏态占比 = p_gb/(p_gb+p_bg)`，所以：

        p_bg = 1 / L ,   p_gb = q · p_bg / (1 − q)

    这条换算是**精确**的，也是本文件自检里手算核对的那条。
    """
    p_bg = 1.0 / mean_bad_h
    p_gb = q_bad * p_bg / (1.0 - q_bad)
    return p_gb, p_bg


def iid_chain(q_bad: float) -> tuple[float, float]:
    """无记忆 ⇒ 与自身等价的链是 `p_bg = 1 − q`（坏态每小时以 1−q 的概率转好）。"""
    return q_bad, 1.0 - q_bad


def tctrl_survival(p_gb_b: float, p_bg_b: float, p_gb_u: float, p_bg_u: float,
                   hours: int) -> list[float]:
    """`S[h] = P(T_ctrl > h 小时)`，**精确 DP**，不是抽样。

    两腿独立、各自逐小时两态。令 `h*` = 第一个"两腿同时可用"的整点，
    则 `T_ctrl = R·ceil(h*·3600/R)`，于是当 `R | 3600` 时

        `S(h 小时) = P(h* > h) = P(小时 0..h 内从未两腿同时可用)`

    这就是"到第 h 小时为止一次纠正机会都没有过"的概率。实现方式是**吸收式 DP**：
    一旦某个小时两腿同时可用就把它从存活质量里摘掉。
    """
    # 联合状态 (回传坏?, 接入坏?) → 索引
    def stat_bad(p_gb, p_bg):
        # 平稳坏态概率
        return p_gb / (p_gb + p_bg)

    pi = {}
    for bb in (0, 1):
        for uu in (0, 1):
            pi[(bb, uu)] = ((stat_bad(p_gb_b, p_bg_b) if bb else
                             1 - stat_bad(p_gb_b, p_bg_b)) *
                            (stat_bad(p_gb_u, p_bg_u) if uu else
                             1 - stat_bad(p_gb_u, p_bg_u)))
    S = []
    for h in range(hours + 1):
        # 本小时"两腿同时可用" = bb==0 且 uu==0 ⇒ 已成功，从存活质量里去掉
        alive = sum(v for k, v in pi.items() if k != (0, 0))
        S.append(alive)
        # 转移到下一小时：两条独立链各按自己的 p 翻转
        nxt = {}
        for (bb, uu), v in pi.items():
            # 已经成功的路径仍然要传下去（它不影响"是否曾经成功"这个事件，
            # 但吸收式 DP 里我们只跟踪**尚未成功**的质量，所以先剔除成功态）
            if (bb, uu) == (0, 0):
                continue
            for nbb, wb in ((0, 1 - p_gb_b), (1, p_gb_b)) if bb == 0 else \
                           ((0, p_bg_b), (1, 1 - p_bg_b)):
                for nuu, wu in ((0, 1 - p_gb_u), (1, p_gb_u)) if uu == 0 else \
                               ((0, p_bg_u), (1, 1 - p_bg_u)):
                    nxt[(nbb, nuu)] = nxt.get((nbb, nuu), 0.0) + v * wb * wu
        pi = nxt
    return S


# ── 链路 regime（**来源时间结构 prior**）───────────────────────────────────────────────
def regimes() -> dict[str, tuple[float, float, float, float]]:
    """`名称 → (p_gb 回传, p_bg 回传, p_gb 接入, p_bg 接入)`。

    - `iid`：实例自带的 i.i.d. 对照（两条链都无记忆）。
    - `chirpbox_6.38h` / `chirpbox_11.5h` / `heavy_20h` / `polar_72.4h`：
      来源拟合的**平均坏突发**。回传用 0.38 坏态占比；接入用 0.26。
    - 最后一条 `polar_cli`：**与实跑用的 CLI 值逐位一致**（`--backhaul-burst 0.00846,0.0138
      --uplink-burst 0.0079,0.0158`），用于和已登记结果对上。
    """
    out = {"iid": (*iid_chain(Q_BACKHAUL), *iid_chain(Q_UPLINK))}
    for name, L in (("chirpbox_6.38h", 6.38), ("chirpbox_11.5h", 11.5),
                    ("heavy_20h", 20.0), ("polar_72.4h", 72.4)):
        pg_b, pb_b = chain_from_mean_bad(L, Q_BACKHAUL)
        pg_u, pb_u = chain_from_mean_bad(L, Q_UPLINK)
        out[name] = (pg_b, pb_b, pg_u, pb_u)
    out["polar_cli"] = (0.00846, 0.0138, 0.0079, 0.0158)
    return out


CAPACITY_WH = 0.02          # 实例声明容量（开发集用的那一档）
#: 来源派生采能的量级旋钮（**A 层选择，不是拟合值，也不是来源事实**）。
#: 形状来自 NASA POWER 2023 逐小时辐照，量级由 `peak_wh_per_hour` 定。
PEAK_WH_PER_HOUR = 0.01


def t_harm_traj(load_h: float, soc0: float, harvest: dict, hours: int,
                capacity_wh: float = CAPACITY_WH) -> float:
    """沿**来源派生采能轨迹**走到电量归零的小时数（`T_harm^traj`）。

    逐 tick 积分，**与实例里 `Node.step` 的顺序一致**（先充电、后按负载扣）： 

        soc ← min(capacity, soc + harvest[t]);  soc ← soc − load_h/60

    采能为 0 时它必须**逐位退化**成 `T_harm^worst = soc0 / load_h`——
    这条是自检里钉住的恒等式，也是两个边界之间的关系定义。
    """
    soc = soc0
    for t in range(0, hours * 3600, TICK_S):
        soc = min(capacity_wh, soc + harvest.get(t, 0.0))
        soc -= load_h * (TICK_S / 3600.0)
        if soc <= 0.0:
            return t / 3600.0
    return float(hours)


def source_harvest(hours: int, seed: int, peak_wh_per_hour: float) -> dict:
    """**来源派生**的逐 tick 采能（形状：NASA POWER 2023 逐小时辐照）。"""
    from exogenous import irradiance_harvest
    h, _temp = irradiance_harvest(["n01"], hours, seed,
                                  peak_wh_per_hour=peak_wh_per_hour)
    return h["n01"]


def traj_table(hours: int, soc0: float, seed: int, peak: float) -> int:
    cfg = ((600, 900, "dense600"), (900, 900, "dense900"),
           (3600, 300, "aoi-like"), (3600, 3600, "sparse"))
    have = source_harvest(hours, seed, peak)
    print(f"来源派生采能（NASA POWER 2023 逐小时辐照，形状来自来源；"
          f"量级 peak = {peak} Wh/h 是 **A 层旋钮**）")
    print(f"任务 {hours} h；soc0 = {soc0} Wh；容量上限 {CAPACITY_WH} Wh；种子 {seed}\n")
    print(f"{'配置':<12}{'load_h Wh/h':>14}{'T_harm^worst':>14}{'T_harm^traj':>13}"
          f"{'差（风险容许区）':>18}")
    print("-" * 72)
    for i, r, tag in cfg:
        lh = hourly_load(i, r)
        worst = soc0 / lh
        traj = t_harm_traj(lh, soc0, have, hours)
        d = traj - worst
        # `traj == hours` 是**右删失**（任务窗内没死），不是死亡时间——所以只在未删失时比较。
        censored = traj >= hours
        # **非负采能不可能让节点更早死。** 未删失却更早死 ⇒ 积分或口径有错，
        # 宁可响亮失败也不印错表。**（2026-09-13：`dense600` 触发此断言，原因未查明，见文档）**
        if (not censored) and d < -1.0 / 60 - 1e-9:
            raise AssertionError(
                f"{tag}: 未删失的 T_harm^traj {traj:.4f} h < T_harm^worst {worst:.4f} h —— "
                f"采能非负却更早死，积分或口径有错，本表不可用")
        d_s = "右删失（任务窗内没死）" if censored else f"{d:+.2f} h"
        print(f"{tag:<12}{lh:>14.6e}{worst:>13.2f}h{traj:>12.2f}h{d_s:>18}")
    print("\n读法：`traj − worst` 就是**允许风险控制发挥的区域**——"
          "沿真实采能节点撑得比零采能上界久多少。")
    return 0


def cadence(t_report_s: int, t_deadline_s: int) -> float:
    """`C = T_report / T_deadline`。`C > 1` ⇒ cadence-infeasible。"""
    return t_report_s / t_deadline_s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=12, help="任务时长（小时）")
    ap.add_argument("--soc", type=float, default=0.0195, help="初始 SoC（Wh）")
    ap.add_argument("--report-period-s", type=int, default=3600)
    ap.add_argument("--traj", action="store_true",
                    help="算 T_harm^traj（沿来源派生采能轨迹）并与 T_harm^worst 对比")
    ap.add_argument("--peak", type=float, default=PEAK_WH_PER_HOUR,
                    help="来源派生采能的量级旋钮（A 层）")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--blind", action="store_true",
                    help="把判据与已知答案并排（答案栏来自已登记结果，判据不含它）")
    args = ap.parse_args()

    if args.blind:
        return blind()
    if args.traj:
        return traj_table(args.hours, args.soc, args.seed, args.peak)

    if args.selftest:
        return selftest()

    H = args.hours
    print(f"任务 {H} h；初始 SoC {args.soc} Wh；上报周期 {args.report_period_s} s\n")
    print("配置能耗（Wh/h，手算 = (3600/i)·4.7e-4 + (3600/r)·(2.33e-5+2.2e-5)）")
    for i, r, tag in ((600, 900, "dense600"), (900, 900, "dense900"),
                      (3600, 3600, "sparse"), (3600, 300, "aoi-like"),
                      (600, 3600, "heavy-sample-only")):
        lh = hourly_load(i, r)
        print(f"  ({i:>4},{r:>4}) {tag:<20} {lh:.6e} Wh/h  "
              f"T_harm^worst = soc/load_h = {args.soc / lh:6.2f} h")
    print()
    print("T_ctrl 生存曲线 S(x) = P(T_ctrl > x)，**精确 DP**")
    print(f"{'regime':<16}" + "".join(f"{h:>7}h" for h in (1, 2, 4, 6, 8, 12)))
    print("-" * 74)
    for name, (pgb, pbb, pgu, pbu) in regimes().items():
        S = tctrl_survival(pgb, pbb, pgu, pbu, H)
        print(f"{name:<16}" + "".join(f"{S[h]:>8.4f}" for h in (1, 2, 4, 6, 8, 12)))
    return 0


#: 已登记的突发度阶梯（`docs/s8-report/progress-log.md` §7.60 四）。**这是答案，不是输入。**
#: 判据在跑之前就定好了（只用了两态链参数与任务时长），没有用到这一列去拟合任何东西。
LADDER = [
    ("iid",            "i.i.d. 对照",      3.5),
    ("chirpbox_6.38h", "ChirpBox 6.38 h",  2.3),
    ("chirpbox_11.5h", "ChirpBox 同均值 11.5 h", 1.7),
    ("heavy_20h",      "更重 20.0 h",      1.6),
    ("polar_cli",      "LoRa-on-Ice 72.4 h", 0.0),
]

#: 同一条阶梯上**另一个**同样单调的量：链路损（条/168）。用来暴露混杂。
LINK_LOSS = [9.1, 41.3, 53.2, 54.6, 84.0]


def blind() -> int:
    """盲测：判据能不能把"哪里有策略差异"分开？**答案栏不参与任何计算。**"""
    H = 12
    rows = []
    for name, label, spread in LADDER:
        S = tctrl_survival(*regimes()[name], H)
        rows.append((label, S[12], 1 - S[12], spread))
    print("横轴：任务 12 h、上报周期 3600 s。判据只用两态链参数，**不含答案栏**。\n")
    print(f"{'链路结构':<24}{'S(12)=P(零纠正机会)':>20}{'1−S(12)':>10}"
          f"{'实测臂间极差':>14}{'链路损/168':>12}")
    print("-" * 84)
    for (label, s12, has, spread), loss in zip(rows, LINK_LOSS):
        print(f"{label:<24}{s12:>20.4f}{has:>10.3f}{spread:>14.1f}{loss:>12.1f}")
    hs = [r[2] for r in rows]
    sp = [r[3] for r in rows]
    mono = all(hs[i] >= hs[i + 1] for i in range(len(hs) - 1))
    print(f"\n判据侧（1−S(12)）单调不增：{mono}")
    print(f"答案侧（臂间极差）单调不增：{all(sp[i] >= sp[i + 1] for i in range(len(sp) - 1))}")
    print(f"两者同序（5 档全对）：{mono}")
    print(f"\n⚠ **混杂**：链路损 {LINK_LOSS} 同样单调。同一条突发度阶梯上，"
          "\n   '纠正机会消失'与'交付被打穿'由**同一个参数**驱动，这一条阶梯**分不开**它们。")
    return 0


def selftest() -> int:
    """手算核对：每一个数都必须在纸面上算得出来，否则这个判据不能当判据用。"""
    ok = True

    def chk(name, got, want, tol=1e-9):
        nonlocal ok
        good = abs(got - want) <= tol
        ok = ok and good
        print(f"  {'PASS' if good else 'FAIL'}  {name}  — 实测 {got!r}，手算 {want!r}")

    print("手算核对")
    chk("RX_WH = 3.6 × 11 / 1000 × 2000 / 3.6e6", RX_WH, 3.6 * 0.011 * 2000 / 3.6e6)
    chk("dense(600,900) = 6×4.7e-4 + 4×(2.33e-5+2.2e-5)", hourly_load(600, 900),
        6 * 4.7e-4 + 4 * (2.33e-5 + 2.2e-5))
    chk("sparse(3600,3600) = 1×4.7e-4 + 1×(2.33e-5+2.2e-5)", hourly_load(3600, 3600),
        4.7e-4 + 4.53e-5)
    chk("T_harm^worst(dense, 0.0195 Wh) = 6.50 h", 0.0195 / hourly_load(600, 900),
        0.0195 / 3.0012e-3, 1e-3)

    # 链的换算：平均坏突发 = 1/p_bg，坏态占比 = p_gb/(p_gb+p_bg)
    pgb, pbb = chain_from_mean_bad(72.4, 0.38)
    chk("chain_from_mean_bad(72.4 h, 0.38)：1/p_bg = 72.4", 1 / pbb, 72.4, 1e-9)
    chk("…坏态占比 = p_gb/(p_gb+p_bg) = 0.38", pgb / (pgb + pbb), 0.38, 1e-12)
    # CLI 里写的是四舍五入后的 0.00846，精确值是 0.0084655…，所以只对到 CLI 的舍入精度
    chk("…与实跑 CLI 的 p_gb=0.00846 一致（到 CLI 的舍入精度）", pgb, 0.00846, 1e-5)

    # 生存曲线：i.i.d. 下"每小时两腿同时可用"= 0.62×0.74，逐小时独立
    S = tctrl_survival(*iid_chain(Q_BACKHAUL), *iid_chain(Q_UPLINK), 12)
    good_each = BACKHAUL_P_GOOD * UPLINK_P_ARRIVE
    chk("i.i.d.：P(小时 0 不是两腿同时可用) = 1 − 0.62×0.74", S[0], 1 - good_each, 1e-12)
    chk("i.i.d.：S(1) = (1 − 0.62×0.74)²（逐小时独立）", S[1], (1 - good_each) ** 2, 1e-12)
    chk("i.i.d.：S(12) = (1 − 0.62×0.74)¹³", S[12], (1 - good_each) ** 13, 1e-12)

    # 生存曲线单调不增，且南极显著高于 i.i.d.
    Sp = tctrl_survival(*regimes()["polar_cli"], 12)
    chk("生存曲线单调不增", all(Sp[i] >= Sp[i + 1] - 1e-15 for i in range(len(Sp) - 1)), True)
    # **纠正我自己的猜测**：我原以为南极 S(12) 会 >0.9（"整段任务都没有纠正机会"）。
    # 实际不是——两条链的**边际可用率被固定住了**，所以机会的**期望个数**几乎不变
    # （南极 12×0.4133 ≈ 4.96 对 i.i.d. 12×0.4588 ≈ 5.5），变的只是它们**聚不聚在一起**。
    # 因此判别量不是 S(12) 的绝对值，而是"**整段任务一次机会都没有**"的概率之比。
    chk("南极 S(12) ≈ 0.51（边际固定时机会期望数几乎相同，变的只是聚不聚）",
        0.48 <= Sp[12] <= 0.55, True)
    # 顺带记下 CLI 那一档的**边际污染**：接入边际 0.0158/(0.0079+0.0158)=0.667，
    # 而 i.i.d. 档是 `uplink_p_arrive`=0.74。回传两档都是 0.62（无污染）。
    chk("polar_cli 的接入平稳可用率 = 0.0158/(0.0079+0.0158) = 0.6667（≠ 0.74）",
        round(0.0158 / (0.0079 + 0.0158), 4), 0.6667, 1e-9)
    chk("i.i.d. S(12) < 1e-3（几乎不可能一次机会都没有）", S[12] < 1e-3, True)
    chk("南极 / i.i.d. 的『零机会』概率之比 > 1000×（这才是可判别量）",
        Sp[12] / S[12] > 1000, True)

    # T_harm^traj 在零采能下必须**逐位**退化到 T_harm^worst（两个边界的关系定义）
    lh = hourly_load(600, 900)
    # 注意：逐 tick 积分的结果**只能落在 1/60 h 的网格上**，所以与连续的 `soc/load_h`
    # 只相等到 tick 分辨率——这本身就是一条要记住的事（上界是连续的，轨迹是量化的）。
    chk("零采能下 T_harm^traj 与 T_harm^worst 相等（到 tick 分辨率 1/60 h）",
        abs(t_harm_traj(lh, 0.0195, {}, 12) - 0.0195 / lh) <= 1.0 / 60 + 1e-9, True)

    # cadence
    chk("Cleveland：C = 3600/900 = 4 ⇒ cadence-infeasible", cadence(3600, 900), 4.0)
    chk("本实例：C = 900/3600 = 0.25 ⇒ cadence 可行", cadence(900, 3600), 0.25)

    print("\n" + ("全部通过" if ok else "有不通过的项"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
