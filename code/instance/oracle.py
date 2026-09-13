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
| **dynamic upper bound** | 完整未来轨迹 | 每个时刻都可换档（这里用松弛求解） | 真上界 |

`dynamic_upper_bound` 的构造见下：它**故意松弛**到只受"总采样次数上限"约束，因此它的解集是
真实可行解集的超集，其最优值 ≥ 真实最优值——这正是"上界"该有的性质。
"""

from __future__ import annotations

import os as _os, sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime", "experiments",
                                                      "analysis", "monitoring"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

from network import TICK_S


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
