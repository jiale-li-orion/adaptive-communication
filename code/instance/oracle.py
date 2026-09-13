"""上界参考：clairvoyant static selector 与 dynamic upper bound。

**为什么必须有两个，以及名字为什么重要。**

`OracleDeployPolicy` 原先叫"全知上界"，那是错的：它在**两条完整的固定轨迹**（全稀疏 / 全加密）
之间逐节点做**一次性的二选一**，之后不再变。它知道参数，但它不随时间调整。因此一条逐时刻
依据状态调整的策略**可以超过它**（实测在 60% 失电档 `ea_i600` 交付 150.7、它 150.2）。
一条会被超过的东西不能叫上界——审稿人第一个问题就是"既然方法能超过上界，它怎么还是上界"。

所以本模块给两个不同性质的参照：

| 名称 | 知道什么 | 能做什么 | 用途 |
|---|---|---|---|
| **clairvoyant static selector** | 完整参数 | 逐节点一次性选稀疏或加密，之后恒定 | "静态但知情"的参照 |
| **dynamic upper bound** | 完整未来轨迹 | 每个时刻都可换档（这里用松弛求解） | 粗上界，几乎不紧 |
| **dynamic oracle**（`dynamic_oracle`） | 完整未来采能轨迹与义务表 | **逐小时**换档，用离线动态规划求最优档位序列 | 真上界，且紧 |

`dynamic_upper_bound` 的构造见下：它**故意松弛**到只受"总采样次数上限"约束，因此它的解集是
真实可行解集的超集，其最优值 ≥ 真实最优值——这正是"上界"该有的性质。

**但两条松弛叠起来把上界放得太松了**（实测 168/168，等于"全都能做到"，不带信息）。
`dynamic_oracle` 是它的替代：只松弛**可交付性**（假设想发就发得出去），**不松弛时间结构**
（档位只能取离散值、每个小时只能选一个），也**不松弛能量的时间耦合**（逐小时积分，含容量溢出
截断）。于是它仍然是一个上界，但会明显低于 `dynamic_upper_bound`，从而对策略有区分力。
"""

from __future__ import annotations

import os as _os, sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime", "experiments",
                                                      "analysis", "monitoring"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

from exogenous import KIND_ROUTINE
from network import TICK_S

#: 可选的采样间隔档位（s）。与 `DeviceProfile` 的默认 3600 及公开上传周期 `0041` 同族。
INTERVAL_TIERS: tuple[int, ...] = (300, 600, 900, 1800, 3600)

#: 每次上行的空口能耗（Wh）。从实例解剖里实测：532 次上行共 0.0124 Wh → 2.33e-5。
#: **它不是拍出来的常数**，而是 `RadioEnergy` 在 `BUS_V=3.3`、`TX_MA_AT_14DBM` 与
#: 实际 airtime 下的结果；写在这里是把它固定成 oracle 的输入，避免 oracle 与实例各算一遍。
UPLINK_WH = 2.33e-5


def dynamic_oracle(obligations, hours: int, harvest_by_node: dict[str, dict[int, float]],
                   node_ids, *, profile, initial_wh: float | None = None,
                   soc_bins: int = 200,
                   intervals: tuple[int, ...] = INTERVAL_TIERS,
                   report_periods: tuple[int, ...] = INTERVAL_TIERS,
                   kinds: tuple[str, ...] = (KIND_ROUTINE,),
                   tail_hours: int = 0) -> dict:
    """**真上界**：逐节点、逐小时的离线动态规划，读完整未来的采能轨迹。

    状态 `soc` 离散成 `soc_bins` 档；每小时选一个采样间隔档位；收益是当天该节点**能被满足的
    义务条数**。向后递推：

        V[h][s] = max_a { reward(h, a) + V[h+1][ clip(s + H(h) - cost(a)) ] }

    **动作是两个字段，不是一个。** 采样间隔与上报周期是**独立字段**（E：重庆 `0045`/`0042`），
    节点还有缓存（`cache_slots`），所以"采得密、报得稀"是允许的。因此：

        cost(a_i, a_p) = (3600/a_i) * sample_wh + (3600/a_p) * UPLINK_WH
        reward         = 只看 a_i（服务义务靠**采样**，不靠上报频率）

    第一版把动作写成一维、并按"每采一条报一条"计能，于是**高估了密集采样的能耗**
    （`dense300` 采 300 s / 报 900 s 的真实能耗是 `12*4.7e-4 + 4*2.33e-5`，而它按
    `12*(4.7e-4+2.33e-5)` 计）——**低估能耗会让上界偏低，偏低的上界不再是上界**。
    测试 [18] 用一条"采得密、报得稀"的臂把这条钉住。

    `s + H(h) < cost` 表示这一档真跑不起，该动作不可行。收益按义务的 `window` 与该档位能否在
    窗内落下一条样计算。

    **只覆盖 `kinds` 里的义务，默认只算周期义务。** 这不是图省事，是两条硬理由：

      1. **事件义务有实例里拿不到的额外能力。** 实例在触发时刻做**触发锚定的**本地采样
         （触发落在 1052 s 这类实时钟时刻，不在 300 s 网格上），而本函数动作集只有周期档位。
         于是真实策略能满足事件义务而本函数认为够不到——实测 `dense600` 在容量 0.05 下交付
         184 条、而上界只有 171 条，**上界被突破**（`test_instance.py` [15] 抓到）。一条能被
         超过的东西不是上界。
      2. **事件列本来就不许用来支撑结论。** 事件采集/交付在全部臂、全部设置下恒为 21.0/16.8
         （现场自治，不经过中心），本项目既有纪律明令它没有区分力。两侧都不计入，才对得上。

    同时**这一点使上界更强**：真实策略还要为事件采样花电，而本函数不给这笔电，因此留给周期
    采样的预算比真实更宽——方向仍然是上界。

    **后果**：`dynamic_upper_bound` 与它都是上界，但只有后者对策略有区分力。
    """
    n_bins = max(2, int(soc_bins))
    cap = profile.capacity_wh
    step = cap / n_bins
    init = cap if initial_wh is None else min(cap, initial_wh)

    by_node: dict[str, list] = {}
    for o in obligations.obligations:
        if o.kind in kinds:
            by_node.setdefault(o.node_id, []).append(o)

    total, per_node = 0, {}
    for node_id in node_ids:
        obs = by_node.get(node_id, [])
        harvest = harvest_by_node.get(node_id, {})
        # 逐小时采能之和。**顺序无关**：同小时内先采后耗与先耗后采只差一个小时内的时间分辨率，
        # 而 DP 的状态本来就是小时。这一步是刻意的粗化，会让上界略微偏宽——方向安全。
        h_wh = [sum(v for t, v in harvest.items() if t // 3600 == h) for h in range(hours)]

        # 逐小时收益：档位 a 在该小时内能落下多少次采样，据此判断能否覆盖每条义务的窗。
        #
        # **每条义务只在 `window[0]` 所在的小时里计入一次。** 按"窗与本小时有交集"来计会重复计数：
        # 本实例的窗是 `[h*3600, (h+1)*3600]` 的闭区间，`hi < h*3600` 的严格比较让第 h 小时的
        # 义务在**第 h+1 小时里又被记一次**，12 条义务被数成 23 条（实测踩到）。
        # 窗跨小时时这里只用前一个小时内的采样相位，属于保守；本实例的窗 ≤ 3600 s 且与小时对齐，
        # 所以不改变结果。
        reward: list[dict[int, float]] = []
        buckets: list[list] = [[] for _ in range(hours)]
        for o in obs:
            lo = max(o.window[0], o.release_at) - o.tolerance_s
            hi = o.window[1] + o.tolerance_s
            h_o = lo // 3600
            if 0 <= h_o < hours:
                buckets[h_o].append((lo, hi))
        for h in range(hours):
            r = {}
            for a in intervals:
                got = 0
                for lo, hi in buckets[h]:
                    # 本小时内是否存在一个采样相位落进窗内（最优相位，对策略是松弛）
                    first = -(-lo // a)               # ceil(lo / a)，对负下界也成立
                    if a * first <= hi:
                        got += 1
                r[a] = float(got)
            reward.append(r)

        # 两个字段各自的单位小时能耗。采样决定服务，上报只花钱。
        cost_sample = {a: (3600 / a) * profile.sample_wh for a in intervals}
        cost_uplink = {p: (3600 / p) * UPLINK_WH for p in report_periods}
        # 加上"本小时不采样"这个动作（代价 0、收益 0）。它不是可有可无的：
        # 没有它，电量耗尽的节点会让**整条轨迹**看起来不可行（`V_next` 为 NEG、
        # `reward + (-inf) = -inf` 而 `-inf > -inf` 为假，档位留在 None），于是 DP 强迫节点
        # 必须撑满整个时间窗，把"先采样、后耗尽停摆"这个完全合法的结果误判成不可行
        # （实测：0.004 Wh 的节点能采 8 小时，却被报成 0 条义务）。
        # 物理上节点耗尽就是**停止采样**，所以"不采样"必须是一个动作。
        # 它同时是松弛（真实策略不能任意跳过整点），因此不破坏上界性质。
        # 动作 = (采样间隔, 上报周期)；`None` 表示本小时不采样、不上报（代价 0）。
        actions: list[tuple[int | None, int | None]] = [
            (a, p) for a in intervals for p in report_periods] + [(None, None)]
        cost = {(a, p): cost_sample[a] + cost_uplink[p]
                for a in intervals for p in report_periods}
        cost[(None, None)] = 0.0

        NEG = float("-inf")
        V_next = [0.0] * (n_bins + 1)
        choice = [[None] * (n_bins + 1) for _ in range(hours)]
        for h in range(hours - 1, -1, -1):
            V = [NEG] * (n_bins + 1)
            for b in range(n_bins + 1):
                soc = b * step
                for act in actions:
                    avail = soc + h_wh[h] - cost[act]
                    if avail < 0:
                        continue                       # 这一档跑不起
                    nb = min(n_bins, int(avail / step))
                    v = (0.0 if act[0] is None else reward[h][act[0]]) + V_next[nb]
                    if v > V[b]:
                        V[b] = v
                        choice[h][b] = act
            V_next = V
        start = min(n_bins, int(init / step))
        best = V[start]

        # 前向重放，得到真正会被执行的档位序列与电量轨迹。用固定的起始档去读 `choice` 是错的：
        # 每一小时的 SoC 不同，档位也随之不同。
        schedule, socs, b, soc = [], [], start, init
        for h in range(hours):
            a = choice[h][b]
            schedule.append(a)
            if a is None or a[0] is None:
                socs.append(soc)
                continue
            soc = min(cap, soc + h_wh[h] - cost[a])
            socs.append(soc)
            b = min(n_bins, int(soc / step))
        best_int = 0 if best == NEG else int(round(best))

        total += best_int
        per_node[node_id] = {
            "n_obligations": len(obs),
            "oracle": best_int,
            "schedule": schedule,
            "soc_wh": [round(x, 6) for x in socs],
            "hours_sampled": sum(1 for a in schedule if a is not None and a[0] is not None),
        }
    return {"total_oracle": total, "per_node": per_node, "soc_bins": n_bins,
            "intervals": list(intervals), "report_periods": list(report_periods),
            "note": ("真上界：松弛可交付性（假设一定送得到）、按标称容量算、每义务取最优采样相位；"
                     "不松弛档位离散性与能量的小时耦合。逐小时收益由义务窗与该档位能否在窗内"
                     "落样决定，故它同时反映'加密才拿得到事件义务'与'加密会耗死电池'这对取舍。")}


def affordable_samples(harvest: dict[int, float], initial_wh: float, capacity_wh: float,
                       sample_wh: float, tick_s: int = TICK_S) -> int:
    """在**不发生电量告负**的前提下，这台节点最多能采多少次样。

    这是真实能量约束的精确表述，也是动态上界里唯一的约束：逐时刻积分，
    采能先进电池（受容量上限截断——**溢出是真实的，0.02 Wh 的电池存不下 4 小时采到的
    0.2 Wh**），再看能不能再采一条。它用到的知识是完整未来的 `harvest`，因此只属于上界。
    """
    soc = initial_wh
    n = 0
    for t_s in sorted(harvest):
        soc = min(capacity_wh, soc + harvest[t_s])
        if soc >= sample_wh:
            soc -= sample_wh
            n += 1
    return n


def dynamic_upper_bound(obligations, nodes, truth, profile, plane,
                        harvest_by_node: dict[str, dict[int, float]],
                        initial_wh: float | None = None) -> dict:
    """动态上界：逐时刻可换档 + 看完整未来，用**两个松弛**求出的上界。

    **松弛一（时间）：** 真实策略的采样是周期性的（间隔只能取档位值）；这里允许在任意 tick
    采样、任意 tick 上传，只要一条义务的采集窗内有某个时刻能让样本在截止前走完
    接入＋网关＋回传。**接入跳假设总能成功**——真实策略受 ``uplink_p_arrive`` 限制，
    但上界可以假设它想听就听得到。于是可交付性只由**回传轨迹**决定。
    这使可行解集成为真实解集的超集：任何真实策略送到的义务都落在这个集合里。

    **松弛二（能量）：** 真实策略的采样受间隔档位与"事先不能看未来"约束；这里只要求
    "总采样次数 ≤ 电量允许的次数"（``affordable_samples``，逐时刻精确积分，含容量溢出截断）。

    上界 = 逐节点 min(可交付义务数, 电量买得起的采样次数)。两条松弛都只会放宽，不会收紧，
    所以这个值**不会低于**任何真实策略能达到的交付数。
    """
    prof = profile
    init = prof.capacity_wh if initial_wh is None else initial_wh

    by_node: dict[str, list] = {}
    for o in obligations.obligations:
        by_node.setdefault(o.node_id, []).append(o)

    per_node, total = {}, 0
    for node_id, obs in by_node.items():
        deliverable = 0
        for o in obs:
            # 采集窗内任一时点采样后，能否在截止前遇到一次可用的回传
            ok = False
            for t in range(o.window[0], o.window[1] + 1, TICK_S):
                if any(plane.backhaul_available(f // 3600)
                       for f in range(t, o.deadline + 1, TICK_S)):
                    ok = True
                    break
            if ok:
                deliverable += 1
        afford = affordable_samples(harvest_by_node.get(node_id, {}), init,
                                    prof.capacity_wh, prof.sample_wh)
        ub = min(len(obs), deliverable, afford)
        per_node[node_id] = {"n_obligations": len(obs), "link_deliverable": deliverable,
                             "affordable_samples": afford, "ub": ub}
        total += ub
    return {"total_ub": total, "per_node": per_node,
            "note": ("两条松弛：时间上允许任意时刻采样与上传（接入跳假设总能成功，"
                     "可交付性由回传轨迹决定）；能量上只要求总采样次数不超过电量允许值。"
                     "可行解集是真实解集的超集，故为上界。它会高于任何真实策略。")}
