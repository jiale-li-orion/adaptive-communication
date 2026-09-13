"""中心侧：可见历史、下发动作与回执。

对应 [Task Contract v1.1](../docs/s7-method/task-contract-v1.1.md) §4 的 `O_center(t)` 与 §6 的动作表。

**三条纪律写在代码里。**

1. **策略只看得到中心真正收到的东西。** `CenterView` 由 `Instance` 从"已到达的样本与状态上报"
   构造，环境真值、节点缓存、链路好坏都不在其中。策略拿不到它们在物理上拿不到的信息。
2. **下发不是即时生效的。** 一条命令要经回传到达网关、在网关排队等该节点的接收窗口、再在窗口里
   送达；任何一跳失败都可能让它白花一次机会。`plan` 返回的只是**意图**。
3. **回执是"看得见的配置"，不是"命令已发"。** 中心改完周期之后，只有等节点在下一次上报里
   把 `report_period_s` 带回来，中心才知道生效了。这正是 v1.1 §6 说的"正确性宣告必须来自方法
   可见证据"——`Instance` 只把收到的快照放进 `CenterView.reports`，不代任何策略宣告成功。
"""

from __future__ import annotations

from dataclasses import dataclass, field

OP_SET_REPORT_PERIOD = "set_report_period"
OP_SET_SAMPLING_INTERVAL = "set_sampling_interval"


@dataclass
class CenterView:
    """中心在 t 时刻**合法知道**的一切。除此之外它什么都不知道。"""

    t_s: int
    node_ids: tuple[str, ...]
    #: 已收到的最近一份节点状态上报（含 `report_period_s`、`cache_level`、`soc_wh`）。
    reports: dict[str, dict] = field(default_factory=dict)
    #: 每份上报的**接收时刻**（不是节点生成时刻）。
    report_at: dict[str, int] = field(default_factory=dict)
    #: 每个节点已知的最新样本**采集时刻**。没有收到过任何样本的节点不在其中。
    newest_taken_at: dict[str, int] = field(default_factory=dict)
    #: 已经排在网关队列里、还没送达的节点。中心不该对同一个节点重复下单。
    in_flight: frozenset = frozenset()

    def aoi_s(self, node_id: str) -> int | None:
        """中心视角的 AoI。**从未收到过任何样本时返回 None**，不得当成 0。"""
        newest = self.newest_taken_at.get(node_id)
        return None if newest is None else self.t_s - newest

    def known_report_period(self, node_id: str) -> int | None:
        """中心**已确认**的上报周期。没收到过回执就是 None。"""
        snap = self.reports.get(node_id)
        return None if snap is None else snap.get("report_period_s")

    def heard_recently(self, node_id: str, within_s: int) -> bool:
        at = self.report_at.get(node_id)
        return at is not None and (self.t_s - at) <= within_s


class CenterPolicy:
    """中心策略的接口。`plan` 返回**意图**，不是已发生的事。"""

    name = "base"

    def plan(self, view: CenterView) -> list[tuple[str, dict]]:
        raise NotImplementedError

    def __init__(self) -> None:
        #: 每个节点当前的**目标值**与它的世代号。世代号只在目标改变时递增——于是同一条逻辑
        #: 命令的所有重发共享一个身份，目标变了才换新身份。这正是远端能识别重复的前提。
        self.target: dict[str, object] = {}
        self.generation: dict[str, int] = {}

    def stamp(self, node_id: str, **fields) -> dict:
        """给一条命令盖上世代号。目标没变就不换号。"""
        key = tuple(sorted(fields.items()))
        if self.target.get(node_id) != key:
            self.target[node_id] = key
            self.generation[node_id] = self.generation.get(node_id, 0) + 1
        out = dict(fields)
        out["generation"] = self.generation[node_id]
        return out

    def note_command_sent(self, node_id: str, payload: dict) -> None:
        """中心自己的记账：它发过什么。**这不是回执**，回执只能来自节点上报。"""


class LocalPolicy(CenterPolicy):
    """不做任何下发。**这是所有其他策略的共同起点**：现场自治照常工作（v1.1 §10）。

    它必须存在，否则任何"中心介入有收益"的结论都无从判断——收益可能只是"多发了几条命令"。
    """

    name = "local"

    def plan(self, view: CenterView) -> list[tuple[str, dict]]:
        return []


class FixedPeriodPolicy(CenterPolicy):
    """把目标定成一个固定值，**依据回执**重试到生效，之后不再动。

    这是"合理但固定"的调度：目标不随观测变，但实现是合格的——下单之后等节点在下次上报里
    把 `report_period_s` 带回来，没确认就按 dwell 重试。一条只在开跑时试一次、回传恰好断掉就
    永久放弃的策略，衡量的是它自己的实现缺陷，不是"固定调度"这个方案（v1.1 §10：不能制造
    能力不对等的对手）。
    """

    def __init__(self, period_s: int = 300, dwell_s: int = 1800) -> None:
        super().__init__()
        self.period_s = period_s
        self.dwell_s = dwell_s
        self.name = f"fixed{period_s}"
        self._last_cmd_at: dict[str, int] = {}

    def plan(self, view: CenterView) -> list[tuple[str, dict]]:
        out = []
        for nid in view.node_ids:
            if view.known_report_period(nid) == self.period_s:
                continue                                   # 回执已确认，不再发
            if nid in view.in_flight:
                continue
            last = self._last_cmd_at.get(nid)
            if last is not None and view.t_s - last < self.dwell_s:
                continue
            self._last_cmd_at[nid] = view.t_s
            out.append((nid, self.stamp(nid, op=OP_SET_REPORT_PERIOD,
                                        period_s=self.period_s)))
        return out


class AoiPolicy(CenterPolicy):
    """依据**中心自己看到的** AoI 调整上报周期：太旧就加密，够新就放宽。

    只使用 `O_center(t)`：`aoi_s` 来自已到达样本的采集时刻，`known_report_period` 来自回执。
    没收到过回执时按"不知道"处理并下单一次。
    """

    def __init__(self, stale_s: int = 3600, fast_s: int = 300, slow_s: int = 900,
                 dwell_s: int = 600) -> None:
        super().__init__()
        self.stale_s, self.fast_s, self.slow_s = stale_s, fast_s, slow_s
        self.dwell_s = dwell_s
        self.name = f"aoi{stale_s}"
        self._last_cmd_at: dict[str, int] = {}

    def _too_soon(self, node_id: str, t_s: int) -> bool:
        last = self._last_cmd_at.get(node_id)
        return last is not None and t_s - last < self.dwell_s

    def plan(self, view: CenterView) -> list[tuple[str, dict]]:
        out = []
        for nid in view.node_ids:
            if nid in view.in_flight or self._too_soon(nid, view.t_s):
                continue
            aoi = view.aoi_s(nid)
            known = view.known_report_period(nid)
            if aoi is None:
                want = self.fast_s                       # 从没收到过，先加密看能不能收到
            elif aoi > self.stale_s:
                want = self.fast_s
            else:
                want = self.slow_s
            if known == want:
                continue                                  # 回执已经确认是这个值，不重复下单
            self._last_cmd_at[nid] = view.t_s
            out.append((nid, self.stamp(nid, op=OP_SET_REPORT_PERIOD, period_s=want)))
        return out


class AoiLinkPolicy(AoiPolicy):
    """在 `AoiPolicy` 之上多一条：**不把机会花在最近完全没消息的节点上**。

    理由与共享路径有关（v1.1 §7）：节点"已静默"与"我的查询在回程丢了"在观测上不可区分，
    而一次下发本身也要占用同一条链路上的机会。因此对最近 `link_window_s` 内一次都没听到的
    节点，先不下单——它可能根本不可达，把机会花在那里只会白花。这是**信息不足下的判断**，
    不是全知：它同样可能错过一个只是暂时静默、即将回来的节点。
    """

    def __init__(self, link_window_s: int = 7200, **kw) -> None:
        super().__init__(**kw)
        self.link_window_s = link_window_s
        self.name = f"aoi_link{self.stale_s}"
        self.skipped_silent = 0

    def plan(self, view: CenterView) -> list[tuple[str, dict]]:
        out = []
        for nid in view.node_ids:
            if nid in view.in_flight or self._too_soon(nid, view.t_s):
                continue
            if not view.heard_recently(nid, self.link_window_s):
                self.skipped_silent += 1
                continue
            aoi = view.aoi_s(nid)
            known = view.known_report_period(nid)
            want = self.fast_s if (aoi is not None and aoi > self.stale_s) else self.slow_s
            if known == want:
                continue
            self._last_cmd_at[nid] = view.t_s
            out.append((nid, self.stamp(nid, op=OP_SET_REPORT_PERIOD, period_s=want)))
        return out


class DenseSamplingPolicy(CenterPolicy):
    """把所有节点的**采样间隔**改成同一个密集值，之后不再动。

    这是"固定配置"的加强版：它真的会改变电量轨迹，因此在能量绑定的实例里会**把遮荫站点耗死**。
    一条固定配置一旦要密集观测，就无法兼顾"哪些站点撑得住"——那需要**逐节点的状态**，
    而中心恰恰能通过节点上报里的 `soc_wh` 看到它。
    """

    def __init__(self, interval_s: int = 300, period_s: int = 900,
                 dwell_s: int = 3600) -> None:
        super().__init__()
        self.interval_s, self.period_s, self.dwell_s = interval_s, period_s, dwell_s
        self.name = f"dense{interval_s}"
        self._last: dict[str, int] = {}

    def plan(self, view: CenterView) -> list[tuple[str, dict]]:
        out = []
        for nid in view.node_ids:
            if nid in view.in_flight:
                continue
            last = self._last.get(nid)
            if last is not None and view.t_s - last < self.dwell_s:
                continue
            snap = view.reports.get(nid) or {}
            done = (snap.get("sample_interval_s") == self.interval_s
                    and snap.get("report_period_s") == self.period_s)
            if done:
                continue
            self._last[nid] = view.t_s
            out.append((nid, self.stamp(nid, op=OP_SET_SAMPLING_INTERVAL,
                                        interval_s=self.interval_s)))
            out.append((nid, self.stamp(nid, op=OP_SET_REPORT_PERIOD,
                                        period_s=self.period_s)))
        return out


class EnergyAwarePolicy(DenseSamplingPolicy):
    """**依据节点报回来的电量**决定要不要加密：电量健康的才加密，不健康的保持稀疏。

    这一条是唯一无法由固定配置表达的决策：目标值取决于**中心收到的状态**，而状态随
    节点所处地形（遮荫与否）与已消耗的机会而变。中心不读环境真值，只看节点上报里的 `soc_wh`
    与它自己上次下发的意图。
    """

    def __init__(self, healthy_wh: float = 0.010, interval_s: int = 300,
                 period_s: int = 900, sparse_interval_s: int = 3600,
                 sparse_period_s: int = 3600, **kw) -> None:
        super().__init__(interval_s=interval_s, period_s=period_s, **kw)
        self.healthy_wh = healthy_wh
        self.sparse_interval_s = sparse_interval_s
        self.sparse_period_s = sparse_period_s
        self.name = f"energyaware{int(healthy_wh * 1000)}mwh"

    def plan(self, view: CenterView) -> list[tuple[str, dict]]:
        out = []
        for nid in view.node_ids:
            if nid in view.in_flight:
                continue
            last = self._last.get(nid)
            if last is not None and view.t_s - last < self.dwell_s:
                continue
            snap = view.reports.get(nid) or {}
            soc = snap.get("soc_wh")
            if soc is None:
                out.append((nid, self.stamp(nid, op=OP_SET_REPORT_PERIOD,
                                            period_s=self.sparse_period_s)))
                self._last[nid] = view.t_s
                continue
            healthy = soc >= self.healthy_wh
            want_i = self.interval_s if healthy else self.sparse_interval_s
            want_p = self.period_s if healthy else self.sparse_period_s
            if (snap.get("sample_interval_s") == want_i
                    and snap.get("report_period_s") == want_p):
                continue
            self._last[nid] = view.t_s
            out.append((nid, self.stamp(nid, op=OP_SET_SAMPLING_INTERVAL,
                                        interval_s=want_i)))
            out.append((nid, self.stamp(nid, op=OP_SET_REPORT_PERIOD,
                                        period_s=want_p)))
        return out


class OracleDeployPolicy(DenseSamplingPolicy):
    """**上界参考**：知道部署的真实约束（哪些站点被遮荫／失电），据此逐节点设定。

    它读的是**环境真值**，因此**不是一条可实现的策略**，只是"如果完全知道参数，最好能做到
    什么"的参照。它存在的唯一目的是回答：自适应策略从节点上报里推断出的东西，离"全知"还有多远。
    """

    def __init__(self, constrained: frozenset, interval_s: int = 300, period_s: int = 900,
                 sparse_interval_s: int = 3600, sparse_period_s: int = 3600, **kw) -> None:
        super().__init__(interval_s=interval_s, period_s=period_s, **kw)
        self.constrained = frozenset(constrained)
        self.sparse_interval_s = sparse_interval_s
        self.sparse_period_s = sparse_period_s
        self.name = "oracle_deploy"

    def plan(self, view: CenterView) -> list[tuple[str, dict]]:
        out = []
        for nid in view.node_ids:
            if nid in view.in_flight:
                continue
            last = self._last.get(nid)
            if last is not None and view.t_s - last < self.dwell_s:
                continue
            snap = view.reports.get(nid) or {}
            sparse = nid in self.constrained
            want_i = self.sparse_interval_s if sparse else self.interval_s
            want_p = self.sparse_period_s if sparse else self.period_s
            if (snap.get("sample_interval_s") == want_i
                    and snap.get("report_period_s") == want_p):
                continue
            self._last[nid] = view.t_s
            out.append((nid, self.stamp(nid, op=OP_SET_SAMPLING_INTERVAL,
                                        interval_s=want_i)))
            out.append((nid, self.stamp(nid, op=OP_SET_REPORT_PERIOD, period_s=want_p)))
        return out


#: 第一轮的对照集合。**四条共享同一套现场自治、硬件与能量**，差别只在中心怎么花机会。
ARMS: dict[str, type[CenterPolicy]] = {
    "local": LocalPolicy,
    "fixed300": lambda: FixedPeriodPolicy(300),
    "fixed900": lambda: FixedPeriodPolicy(900),
    "aoi": lambda: AoiPolicy(),
    "aoi_link": lambda: AoiLinkPolicy(),
    "dense300": lambda: DenseSamplingPolicy(300, 900),
    "dense600": lambda: DenseSamplingPolicy(600, 900),
    "dense900": lambda: DenseSamplingPolicy(900, 900),
    "dense1200": lambda: DenseSamplingPolicy(1200, 900),
    "dense1800": lambda: DenseSamplingPolicy(1800, 900),
    "energy_aware": lambda: EnergyAwarePolicy(0.010, 300, 900),
    "ea_h5": lambda: EnergyAwarePolicy(0.005, 300, 900),
    "ea_h15": lambda: EnergyAwarePolicy(0.015, 300, 900),
    "ea_h25": lambda: EnergyAwarePolicy(0.025, 300, 900),
    "ea_i600": lambda: EnergyAwarePolicy(0.010, 600, 900),
    "ea_i600h5": lambda: EnergyAwarePolicy(0.005, 600, 900),
}


def build_policy(name: str) -> CenterPolicy:
    try:
        factory = ARMS[name]
    except KeyError:
        raise ValueError(f"unknown arm {name!r}; have {sorted(ARMS)}") from None
    return factory()
