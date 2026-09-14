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
class SocObservationModel:
    """**攻击方法唯一依赖的那个信息。** 反馈策略读的是节点上报的 `soc_wh`；现实中这个量会
    延迟、量化、有偏，报告本身也会丢。本结构把这四件事参数化，用来做反证测试。

    - `max_age_s`：超过这个年龄的观测视为**不可用**（返回 None，策略必须按"不知道"处理）；
    - `noise_wh`：均匀噪声幅度（确定性，由 seed 与节点、观测时刻寻址）；
    - `bias`：乘性偏置（例如电量估计系统性高估）；
    - `loss_p`：报告丢失概率。

    `noise/bias/loss` 都用 `stable_uniform` 寻址，因此同一 (seed, 节点, 观测时刻) 永远给出同一结果，
    实验可复现。默认全零 = 完美观测。
    """

    max_age_s: int | None = None
    noise_wh: float = 0.0
    bias: float = 1.0
    loss_p: float = 0.0
    seed: int = 0

    def observe(self, node_id: str, raw_soc: float | None, observed_at: int | None,
                now_s: int):
        """返回策略**看到**的 SoC；None 表示这份观测不可用。"""
        if raw_soc is None or observed_at is None:
            return None
        if self.loss_p > 0.0:
            from deterministic import stable_uniform
            if stable_uniform(self.seed, "socdrop", node_id, observed_at) < self.loss_p:
                return None
        if self.max_age_s is not None and now_s - observed_at > self.max_age_s:
            return None
        value = raw_soc * self.bias
        if self.noise_wh > 0.0:
            from deterministic import stable_uniform
            u = stable_uniform(self.seed, "socnoise", node_id, observed_at)
            value += (u - 0.5) * 2.0 * self.noise_wh
        return max(0.0, value)


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
    #: **状态观测模型**。默认完美；做反证测试时把它调坏。
    soc_model: SocObservationModel = field(default_factory=SocObservationModel)
    #: —— 以下两个是**网关本地可观测**的转发反馈（doc 48 §4 要求"明确接口和时间戳、同等给所有臂"）。
    #: `_center_view` **不填**它们（中心在回传那一跳的另一端，看不到网关自己的转发是否成功）；
    #: 只有 `_gateway_view` 填。**它们不含任何环境真值与未来信息**：
    #: 前者是"网关上一次真的把缓存交给中心的时刻"，后者是"网关自己还压着多少条"。
    gateway_last_forward_ok_at: int | None = None
    gateway_pending_depth: int | None = None
    #: **网关缓存里最老一条待转发记录的年龄（秒）**——同样是网关本地可观测。
    #: 它是「第二条普通规则族」的输入：**用另一个本地信号判断同一种"回传受阻"**。
    gateway_oldest_pending_age_s: int | None = None

    def soc_of(self, node_id: str) -> float | None:
        """策略**看到**的电量。它可能比真实值旧、脏、偏，或者干脆没到。"""
        snap = self.reports.get(node_id)
        if not snap:
            return None
        return self.soc_model.observe(node_id, snap.get("soc_wh"),
                                      self.report_at.get(node_id), self.t_s)

    def soc_age_s(self, node_id: str) -> int | None:
        """**这条电量证据有多旧**：从它的**源时刻**（节点采到的时刻）算起，不是接收时刻。

        `report_at` 是中心收到的时刻。用它算年龄会把"在路上走了多久"算进证据年龄，
        而策略真正该问的是"这条读数描述的是多久以前的设备状态"。
        """
        snap = self.reports.get(node_id)
        if not snap:
            return None
        src = snap.get("read_at")
        return None if src is None else self.t_s - int(src)

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
        #: 跳过原因计数与"每台节点最后一次跳过的原因"。**诊断用，不参与任何判断。**
        self.skip_counts: dict[str, int] = {}
        self.skip_last: dict[str, tuple[str, int]] = {}
        #: 由 `plan` 的调用方设置的当前时刻，只用来给 `skip_last` 附一个时刻。
        self._skip_t: int = 0

    def stamp(self, node_id: str, **fields) -> dict:
        """给**单字段**命令盖上世代号。目标没变就不换号。

        注意：两个配置字段各自调用它会得到**两条独立的世代序列**，那样"两个字段的世代号不等"
        只是常态，不表示跨代混配。要表达"一次配置决策"请用 `stamp_pair`。
        """
        key = tuple(sorted(fields.items()))
        if self.target.get(node_id) != key:
            self.target[node_id] = key
            self.generation[node_id] = self.generation.get(node_id, 0) + 1
        out = dict(fields)
        out["generation"] = self.generation[node_id]
        #: 这个世代**意图写上哪些字段**。只改一个字段的决策就是一个只有一个字段的完整世代；
        #: 远端据此判断这一代什么时候算到齐。没有这个字段集合，"到齐"就只能靠硬编码"两个字段"，
        #: 于是单字段策略（如 `AoiPolicy`）在整代生效的执行层下会被整类丢弃。
        out["fields"] = [fields["op"]]
        return out

    def stamp_pair(self, node_id: str, left: dict, right: dict) -> tuple[dict, dict]:
        """把**一次配置决策的两个字段**盖上**同一个**世代号。

        协议里 `sampling interval` 与 `report period` 是两个独立字段，但它们由同一次决策产生。
        用一个世代号覆盖这一对，才使得"两个字段的世代不一致"意味着**跨代混配**：节点正在跑
        一个从未被任何 planner 请求过的组合。
        """
        key = ("pair", tuple(sorted(left.items())), tuple(sorted(right.items())))
        if self.target.get(node_id) != key:
            self.target[node_id] = key
            self.generation[node_id] = self.generation.get(node_id, 0) + 1
        g = self.generation[node_id]
        want = [left["op"], right["op"]]
        return ({**left, "generation": g, "fields": list(want)},
                {**right, "generation": g, "fields": list(want)})

    def note_command_sent(self, node_id: str, payload: dict) -> None:
        """中心自己的记账：它发过什么。**这不是回执**，回执只能来自节点上报。"""

    # ------------------------------------------------ 跳过原因（诊断，不改变行为）

    def _skip(self, reason: str, node_id: str | None = None) -> None:
        """记一次"这台节点这次为什么没被下发"。**纯诊断，不参与任何判断。**

        `plan()` 里有四处 `continue`，它们**在日志上长得一模一样**——都表现为"中心没有生成
        意图"。而含义完全不同：链路里还有没送达的命令、策略自己的驻留时间没到、根本没有电量
        证据、目标已经就是那个值。上一轮把"没有生成降档"归因成"无证据不下发"，就是被这个
        **同形**骗了。
        """
        self.skip_counts[reason] = self.skip_counts.get(reason, 0) + 1
        if node_id is not None:
            self.skip_last[node_id] = (reason, self._skip_t)

    def skip_report(self) -> dict:
        """跳过原因汇总。键是原因，值是次数。"""
        return dict(self.skip_counts)


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
                self._skip("in_flight", nid)
                continue
            last = self._last.get(nid)
            if last is not None and view.t_s - last < self.dwell_s:
                self._skip("dwell", nid)
                continue
            snap = view.reports.get(nid) or {}
            done = (snap.get("sample_interval_s") == self.interval_s
                    and snap.get("report_period_s") == self.period_s)
            if done:
                continue
            self._last[nid] = view.t_s
            a, b = self.stamp_pair(nid,
                                   {"op": OP_SET_SAMPLING_INTERVAL,
                                    "interval_s": self.interval_s},
                                   {"op": OP_SET_REPORT_PERIOD,
                                    "period_s": self.period_s})
            out.append((nid, a))
            out.append((nid, b))
        return out


class EnergyAwarePolicy(DenseSamplingPolicy):
    """**依据节点报回来的电量**决定要不要加密：电量健康的才加密，不健康的保持稀疏。

    这一条是唯一无法由固定配置表达的决策：目标值取决于**中心收到的状态**，而状态随
    节点所处地形（遮荫与否）与已消耗的机会而变。中心不读环境真值，只看节点上报里的 `soc_wh`
    与它自己上次下发的意图。
    """

    def __init__(self, healthy_wh: float = 0.010, interval_s: int = 300,
                 period_s: int = 900, sparse_interval_s: int = 3600,
                 sparse_period_s: int = 3600, exit_wh: float | None = None,
                 confirm_n: int = 1, send_when_unknown: bool = True, **kw) -> None:
        super().__init__(interval_s=interval_s, period_s=period_s, **kw)
        self.healthy_wh = healthy_wh
        self.sparse_interval_s = sparse_interval_s
        self.sparse_period_s = sparse_period_s
        #: **滞环第二阈值**。`None` 表示单阈值（原行为）：每次只用 `soc >= healthy_wh` 判一次。
        #: 给定值后进入"粘滞模式"——加密态要跌破 `exit_wh` 才退回稀疏，稀疏态要涨到
        #: `healthy_wh` 才加密，两者之间是**死区**。
        self.exit_wh = exit_wh
        #: 切换前要求连续几次观测都落在新的一侧（去抖）。`1` 表示不要求。
        self.confirm_n = max(1, int(confirm_n))
        #: 没有电量读数时要不要先下发一次保守配置。**这是"读状态"的入场费**：不知道状态就得
        #: 先按最保守的来，于是每台设备多一对命令。而保守配置（稀疏间隔 + 稀疏周期）与设备
        #: **出厂默认完全相同**，所以那一代是**空操作**——把它省掉不改变任何行为，只省下行。
        self.send_when_unknown = send_when_unknown
        #: 逐节点的粘滞模式与去抖计数。**这是策略自己的记忆**（它上次下达的是什么），
        #: 不是环境真值。单阈值模式下不用它。
        self._dense_mode: dict[str, bool] = {}
        self._streak: dict[str, tuple[bool, int]] = {}
        self.name = (f"energyaware{int(healthy_wh * 1000)}mwh"
                     + (f"_x{int(exit_wh * 1000)}_c{self.confirm_n}" if exit_wh else ""))

    def plan(self, view: CenterView) -> list[tuple[str, dict]]:
        out = []
        for nid in view.node_ids:
            if nid in view.in_flight:
                self._skip("in_flight", nid)
                continue
            last = self._last.get(nid)
            if last is not None and view.t_s - last < self.dwell_s:
                self._skip("dwell", nid)
                continue
            snap = view.reports.get(nid) or {}
            soc = view.soc_of(nid)
            if soc is None:
                if not self.send_when_unknown:
                    # 等第一份读数再决定。节点保持出厂默认，而默认就是最保守的那一档。
                    self._skip("no_soc", nid)
                    continue
                # 从没收到过电量读数 → 保守地退回稀疏配置。**这里也必须发完整世代**：
                # 只发一个字段，在"整代生效"的执行层下永远凑不齐一对而被丢弃，于是这一整类
                # 节点在任何执行层下都收不到配置，策略与执行层就不可比了。
                a, b = self.stamp_pair(
                    nid,
                    {"op": OP_SET_SAMPLING_INTERVAL, "interval_s": self.sparse_interval_s,
                     "speculative": True},
                    {"op": OP_SET_REPORT_PERIOD, "period_s": self.sparse_period_s,
                     "speculative": True})
                out.append((nid, a))
                out.append((nid, b))
                self._last[nid] = view.t_s
                continue
            if self.exit_wh is None:
                healthy = soc >= self.healthy_wh
            else:
                # **滞环 + 去抖**。单阈值下 `soc` 在阈值附近抖动会让节点在稀疏/加密之间来回翻，
                # 每次翻转都是一对下发命令——下行次数因此翻倍，而那些命令大多什么也没改变。
                # 死区（`exit_wh` 与 `healthy_wh` 之间）让人数不反复；去抖再要求新的一侧连续
                # 出现 `confirm_n` 次，挡掉单次读数毛刺。
                was_dense = self._dense_mode.get(nid, soc >= self.healthy_wh)
                if was_dense:
                    want_dense = soc >= self.exit_wh
                else:
                    want_dense = soc >= self.healthy_wh
                side, n = self._streak.get(nid, (want_dense, 0))
                n = n + 1 if side == want_dense else 1
                self._streak[nid] = (want_dense, n)
                healthy = was_dense if n < self.confirm_n else want_dense
                self._dense_mode[nid] = healthy
            want_i = self.interval_s if healthy else self.sparse_interval_s
            want_p = self.period_s if healthy else self.sparse_period_s
            if (snap.get("sample_interval_s") == want_i
                    and snap.get("report_period_s") == want_p):
                # **必须与 `at_target` 分开记**：目标已经是那个值，但"那个值"可能是**一条
                # 过期读数**算出来的。两者在日志上同形，含义却完全不同——后者是
                # "我按一条过期证据维持了现状"。
                _age = view.soc_age_s(nid)
                self._skip("at_target_evidence_stale" if (_age is None or _age > 3600)
                           else "at_target", nid)
                continue
            self._last[nid] = view.t_s
            # **一次配置决策 → 一个世代号**，覆盖两个字段。若这里对两个字段各盖一次号，
            # "两个字段世代不等"就变成常态，跨代混配根本测不出来（这是实现里踩过的一个错）。
            a, b = self.stamp_pair(nid,
                                   {"op": OP_SET_SAMPLING_INTERVAL, "interval_s": want_i},
                                   {"op": OP_SET_REPORT_PERIOD, "period_s": want_p})
            out.append((nid, a))
            out.append((nid, b))
        return out


class EnergyAoiPolicy(CenterPolicy):
    """**最强传统基线**：能源反馈 + 简单上报，两者都只用合法观测。

    这是把两条各自成熟的常规做法**组合**起来，不引入任何新机制：

      - **采样间隔**由节点上报的 `soc_wh` 决定（电能反馈，与 `EnergyAwarePolicy` 同法）；
      - **上报周期**由中心自己看到的 AoI 决定（与 `AoiPolicy` 同法）；
      - 两者**成对**下发（一次决策一个世代），且**没有电量读数时不发**——那一代是值域空操作。

    **为什么它必须存在。** 实测在宽松条件下 `aoi` 的周期达标率（92.7%）高于
    `EnergyAwarePolicy` 的 `ea_nb`（91.2%）与最优固定配置 `dense600`（91.9%）——
    也就是说"我们想超越的传统做法"如果只拿 `ea_nb` 当代表，**会把门槛设低了**。
    第二阶段的判据是"在冻结 task、冻结 capability、合法观测、强传统基线之下还有没有 residual"，
    那么这条基线必须先做到位。

    **它不是什么**：它不读环境真值、不预测未来、不做任何跨节点协调，也不新增动作——
    动作集合与所有臂完全相同（改采样间隔、改上报周期）。差异只在**什么时候改**。
    """

    def __init__(self, healthy_wh: float = 0.010, dense_interval_s: int = 600,
                 dense_period_s: int = 900, sparse_interval_s: int = 3600,
                 sparse_period_s: int = 3600, stale_s: int = 3600,
                 fast_period_s: int = 300, slow_period_s: int = 900,
                 dwell_s: int = 600, exit_wh: float | None = None,
                 confirm_n: int = 1) -> None:
        super().__init__()
        self.healthy_wh = healthy_wh
        self.dense_interval_s, self.dense_period_s = dense_interval_s, dense_period_s
        self.sparse_interval_s, self.sparse_period_s = sparse_interval_s, sparse_period_s
        self.stale_s, self.fast_period_s, self.slow_period_s = stale_s, fast_period_s, slow_period_s
        self.dwell_s = dwell_s
        self.exit_wh, self.confirm_n = exit_wh, max(1, int(confirm_n))
        self._dense_mode: dict[str, bool] = {}
        self._streak: dict[str, tuple[bool, int]] = {}
        self._last: dict[str, int] = {}
        self.name = "energy_aoi"

    def plan(self, view: CenterView) -> list[tuple[str, dict]]:
        out = []
        for nid in view.node_ids:
            if nid in view.in_flight:
                self._skip("in_flight", nid)
                continue
            last = self._last.get(nid)
            if last is not None and view.t_s - last < self.dwell_s:
                self._skip("dwell", nid)
                continue
            soc = view.soc_of(nid)
            if soc is None:
                # **没有电量读数就不发。** 保守档与出厂默认逐位相同，发出去是值域空操作，
                # 却要花掉一次下行机会（实测它占了 ea_i600 全部控制流量的一半）。
                self._skip("no_soc", nid)
                continue
            # --- 采样间隔：电能反馈 ---
            if self.exit_wh is None:
                dense = soc >= self.healthy_wh
            else:
                was = self._dense_mode.get(nid, soc >= self.healthy_wh)
                want = soc >= (self.exit_wh if was else self.healthy_wh)
                side, n = self._streak.get(nid, (want, 0))
                n = n + 1 if side == want else 1
                self._streak[nid] = (want, n)
                dense = was if n < self.confirm_n else want
            self._dense_mode[nid] = dense
            # --- 上报周期：AoI 反馈 ---
            # **上报周期保持 AoI 逻辑，不被电能状态覆盖。** 第一版在密集时把它压成 900 s，
            # 结果整条基线的达标率（90.4%）反而低于只做 AoI 的 `aoi`（91.8%）——叠加一个维度
            # 不该削弱另一个维度。要成为"最强传统基线"，两维必须各自保持自己的最优做法。
            aoi = view.aoi_s(nid)
            period = self.fast_period_s if (aoi is None or aoi > self.stale_s) \
                else self.slow_period_s
            ni = self.dense_interval_s if dense else self.sparse_interval_s
            snap = view.reports.get(nid) or {}
            if (snap.get("sample_interval_s") == ni
                    and snap.get("report_period_s") == period):
                continue
            self._last[nid] = view.t_s
            a, b = self.stamp_pair(
                nid,
                {"op": OP_SET_SAMPLING_INTERVAL, "interval_s": ni},
                {"op": OP_SET_REPORT_PERIOD, "period_s": period})
            out.append((nid, a))
            out.append((nid, b))
        return out


class EhAoiPolicy(CenterPolicy):
    """**有限电池能量采集下的状态更新**：**（电量, 年龄）二维联合门限**。

    这是**文献结构**，不是本项目的启发式。有限电池 EH 源上最小化 AoI 的最优策略是
    **同时按电池状态与当前年龄设门限**（Arafa, Baknina, Ulusoy & Ulukus,
    *Optimal Status Updating with a Finite-Battery Energy Harvesting Source*,
    [arXiv:1905.06679](https://arxiv.org/abs/1905.06679)）。此前仓里的 `ea_aoi` 只是把
    「电量门限」与「年龄门限」**各自独立地叠在一起**，那不是文献里的结构，实测也确实没赢过
    `aoi`——这一次按文献的**联合**形式实现：

        dense  ⟺  (电量 ≥ θ_soc)  **且**  (年龄 > θ_age_dense)
        fast   ⟺  年龄 > θ_age_fast

    **联合而非独立**是要害：只有"能量付得起"**并且**"数据确实旧了"才值得花能量加密。
    两个条件各自成立都不构成理由——那正是 `local → aoi` 与 `ea_nb` 各自只吃一半的原因。

    **限定**：文献结论建立在其自身的信道与服务模型上（阈值结构、不可靠信道、AoI 目标），
    本 instance 的义务口径是"每小时一份有效测值 + 宽限"，不是瞬时 AoI 积分。
    所以这里引的是**策略结构**，不是它的最优性证明。
    """

    def __init__(self, soc_th: float = 0.010, age_dense_s: int = 3600,
                 age_fast_s: int = 3600, dense_interval_s: int = 600,
                 dense_period_s: int = 900, sparse_interval_s: int = 3600,
                 sparse_period_s: int = 3600, fast_period_s: int = 300,
                 slow_period_s: int = 900, dwell_s: int = 600) -> None:
        super().__init__()
        self.soc_th, self.age_dense_s, self.age_fast_s = soc_th, age_dense_s, age_fast_s
        self.dense_interval_s, self.dense_period_s = dense_interval_s, dense_period_s
        self.sparse_interval_s, self.sparse_period_s = sparse_interval_s, sparse_period_s
        self.fast_period_s, self.slow_period_s = fast_period_s, slow_period_s
        self.dwell_s = dwell_s
        self._last: dict[str, int] = {}
        self.name = "eh_aoi"

    def plan(self, view: CenterView) -> list[tuple[str, dict]]:
        out = []
        for nid in view.node_ids:
            if nid in view.in_flight:
                self._skip("in_flight", nid)
                continue
            last = self._last.get(nid)
            if last is not None and view.t_s - last < self.dwell_s:
                self._skip("dwell", nid)
                continue
            soc = view.soc_of(nid)
            if soc is None:
                continue                   # 无电量读数：不发（保守档等于出厂默认，是空操作）
            aoi = view.aoi_s(nid)
            stale = aoi is None or aoi > self.age_dense_s
            dense = (soc >= self.soc_th) and stale
            period = self.fast_period_s if (aoi is None or aoi > self.age_fast_s) \
                else self.slow_period_s
            ni = self.dense_interval_s if dense else self.sparse_interval_s
            snap = view.reports.get(nid) or {}
            if (snap.get("sample_interval_s") == ni
                    and snap.get("report_period_s") == period):
                continue
            self._last[nid] = view.t_s
            a, b = self.stamp_pair(nid, {"op": OP_SET_SAMPLING_INTERVAL, "interval_s": ni},
                                   {"op": OP_SET_REPORT_PERIOD, "period_s": period})
            out.append((nid, a))
            out.append((nid, b))
        return out


class ClairvoyantStaticSelector(DenseSamplingPolicy):
    """**clairvoyant static selector**：知道部署的真实约束（哪些站点被遮荫／失电），据此逐节点
    在**稀疏与加密两条固定轨迹之间二选一**，选定之后不再变。

    **它不能叫"上界"。** 它知道参数，但不随时间调整；因此一条逐时刻依据状态的策略**可以超过它**
    （实测 60% 失电档 `ea_i600` 交付 150.7、它 150.2）。一条会被超过的东西不是上界。
    它的正确用途是"**静态但知情**"的参照：用来分离"知道参数"与"随状态调整"这两件事的贡献。
    """

    def __init__(self, constrained: frozenset, interval_s: int = 300, period_s: int = 900,
                 sparse_interval_s: int = 3600, sparse_period_s: int = 3600, **kw) -> None:
        super().__init__(interval_s=interval_s, period_s=period_s, **kw)
        self.constrained = frozenset(constrained)
        self.sparse_interval_s = sparse_interval_s
        self.sparse_period_s = sparse_period_s
        self.name = "clairvoyant_static"

    def plan(self, view: CenterView) -> list[tuple[str, dict]]:
        out = []
        for nid in view.node_ids:
            if nid in view.in_flight:
                self._skip("in_flight", nid)
                continue
            last = self._last.get(nid)
            if last is not None and view.t_s - last < self.dwell_s:
                self._skip("dwell", nid)
                continue
            snap = view.reports.get(nid) or {}
            sparse = nid in self.constrained
            want_i = self.sparse_interval_s if sparse else self.interval_s
            want_p = self.sparse_period_s if sparse else self.period_s
            if (snap.get("sample_interval_s") == want_i
                    and snap.get("report_period_s") == want_p):
                continue
            self._last[nid] = view.t_s
            a, b = self.stamp_pair(nid,
                                   {"op": OP_SET_SAMPLING_INTERVAL, "interval_s": want_i},
                                   {"op": OP_SET_REPORT_PERIOD, "period_s": want_p})
            out.append((nid, a))
            out.append((nid, b))
        return out


class ReportPacingPolicy(CenterPolicy):
    """**只写上报周期**的节奏策略（交付 2 的「普通背压」与「迟滞背压」）。

    **它只用网关本地可观测的量**（doc 48 §4 要求"明确接口和时间戳、同等给所有臂"）：

      - `gateway_pending_depth`：网关自己还压着多少条缓存；
      - `gateway_last_forward_ok_at`：网关上一次**真的**把缓存交给中心的时刻——
        **网关自己知道这次尝试成没成**，这是本地观测；
      - `node.report_period_s` / `node.newest_sample_taken_at`：既有的合法回执与新鲜度。

    **它不读**环境 `path_available`、**不读**未来恢复时刻、**不读**节点真实未上报缓存、
    **不读**中心未确认的交付真值。**没有反馈接口时不慢化**（退化成心跳）——
    不在没有证据时做保守猜测。

    `hysteresis=True` 时要求**连续 `confirm_n` 次**同侧才切换（普通迟滞/切换成本版本）。
    """

    def __init__(self, slow_s: int = 3600, fast_s: int = 900, dwell_s: int = 600,
                 block_after_s: int = 1800, hysteresis: bool = False,
                 confirm_n: int = 2, mode: str = "forward_blocked",
                 backlog_age_s: int = 900) -> None:
        super().__init__()
        #: `forward_blocked`（默认）：按"上一次转发成功距今多久"判受阻；
        #: `pending_backlog`：按"最老待转发记录的年龄"判受阻——**同一谓词的另一种本地信号**。
        assert mode in ("forward_blocked", "pending_backlog"), mode
        self.mode = mode
        self.backlog_age_s = backlog_age_s
        self.slow_s, self.fast_s, self.dwell_s = slow_s, fast_s, dwell_s
        self.block_after_s = block_after_s
        self.hysteresis = hysteresis
        self.confirm_n = max(1, int(confirm_n))
        self._last: dict[str, int] = {}
        self._slow_mode: dict[str, bool] = {}
        self._streak: dict[str, tuple[bool, int]] = {}
        self.name = (f"pacing_{'backlog' if mode == 'pending_backlog' else 'bp'}"
                     f"{slow_s}_{fast_s}" + ("_hyst" if hysteresis else ""))

    def _blocked(self, view: CenterView) -> bool:
        """**回传是否看起来受阻**——只用网关本地可观测的量（两条规则族各用一种信号）。"""
        if self.mode == "pending_backlog":
            age = view.gateway_oldest_pending_age_s
            depth = view.gateway_pending_depth
            if age is None:
                return False                     # 没有反馈接口 ⇒ 不慢化
            if depth is not None and depth <= 0:
                return False                     # 手里没压货
            return age >= self.backlog_age_s
        depth = view.gateway_pending_depth
        last = view.gateway_last_forward_ok_at
        if depth is None or last is None:
            return False            # 没有反馈接口 ⇒ 不慢化
        if depth <= 0:
            return False            # 手里没压货 ⇒ 谈不上下发受阻
        return (view.t_s - last) >= self.block_after_s

    def _want(self, nid: str, view: CenterView) -> int:
        blocked = self._blocked(view)
        if not self.hysteresis:
            return self.slow_s if blocked else self.fast_s
        was = self._slow_mode.get(nid, False)
        side, n = self._streak.get(nid, (blocked, 0))
        n = n + 1 if side == blocked else 1
        self._streak[nid] = (blocked, n)
        state = blocked if n >= self.confirm_n else was
        self._slow_mode[nid] = state
        return self.slow_s if state else self.fast_s

    def plan(self, view: CenterView) -> list[tuple[str, dict]]:
        out = []
        for nid in view.node_ids:
            if nid in view.in_flight:
                self._skip("in_flight", nid)
                continue
            last = self._last.get(nid)
            if last is not None and view.t_s - last < self.dwell_s:
                self._skip("dwell", nid)
                continue
            want = self._want(nid, view)
            snap = view.reports.get(nid) or {}
            if snap.get("report_period_s") == want:
                self._skip("already_confirmed", nid)
                continue
            self._last[nid] = view.t_s
            out.append((nid, self.stamp(nid, op=OP_SET_REPORT_PERIOD, period_s=want)))
        return out


#: **合法配置网格**（两个字段各自独立，E：重庆 `0045`／`0042`）。取值**全部来自仓库已当作合法
#: 的集合**，没有发明任何新取值——见
#: `docs/s7-method/instance-v1/34-pre-registration-config-grid-2026-09-14.md` §2。
GRID_SAMPLING = (300, 600, 900, 1200, 1800, 3600)
GRID_REPORT = (300, 600, 900, 1800, 3600)
#: 每周期采样能耗（Wh）。与 `DeviceProfile.sample_wh` 同源
#: （Ragnoli 等, *JLPEA* 12(3):47, 2022）。
GRID_SAMPLE_WH = 4.7e-4
#: 每周期上报能耗（Wh）。与已登记式子 `load_h = (3600/i)·4.7e-4 + (3600/r)·4.53e-5` 同源。
GRID_REPORT_WH = 4.53e-5


class GridConfigPolicy(DenseSamplingPolicy):
    """**合法配置网格臂**：把一对固定值同时写在两个字段上，之后不再改。

    行为与 `DenseSamplingPolicy` **逐位相同**（同一套 `plan`、同一对字段、同一 dwell），
    唯一差别是名字把 `report` 那一维也带上了——原臂名字只有 `dense{interval}`，
    而网格里同一个 sampling 对应多个 report，名字必须区分得开才读得了表。

    **它不是新机制。** `ARMS` 里本来就有 `denseN = DenseSamplingPolicy(N, 900)`，
    覆盖 `report = 900` 那一行；本类只是把同一件事铺满**其余 20 个合法点**。
    """

    def __init__(self, interval_s: int, period_s: int, **kw) -> None:
        super().__init__(interval_s=interval_s, period_s=period_s, **kw)
        if interval_s not in GRID_SAMPLING or period_s not in GRID_REPORT:
            raise ValueError(f"({interval_s}, {period_s}) 不在合法网格 {GRID_SAMPLING}×{GRID_REPORT} 上")
        self.name = f"grid{interval_s}x{period_s}"


class RollingConfigSearchPolicy(CenterPolicy):
    """**普通滚动搜索**（同预测、同观测的普通 MPC）：候选集 = 合法网格 ∪ {保持现状}。

    这是 §31 第 77 行要求的"**简单滚动搜索**参照"，也是第 79 行要求的"具有**相同预测和观测**的
    普通 MPC"。它**故意是普通的**——用任何现成最优控制教材都能写出这一条，
    因此它赢下来的东西**不得**记成本项目的方法贡献。

    **它只用在线可得的信息 + 明确声明的模型**（§31 第 67 行）：

      - 观测：`CenterView` 里**该节点已确认的**配置与电量读数（`soc_of`）。**没有回执时绝不按
        "我要求的配置"扣算能源**——所以"当前配置"取的是快照里的 `sample_interval_s`/
        `report_period_s`（已确认），不是自己上一次的意图；
      - 预测：**历史标定的标称采能率**（场景声明的 A 层常量），**不使用任何未来真值**；
      - 链路：`uplink_p_arrive` 与 `backhaul_p_good` 两个**场景声明**的概率，对所有臂公开。

    **目标**：在剩余时域内最大化**预期按期交付**，先按**可行性**过滤（预测电量不得转负，
    且计入电池溢出），再排序；同分取**能耗更低**者。**没有任何需要调参的权重。**

    预期交付 = `P(采集) × P(送达)`，其中
      * `P(采集) = min(1, 义务周期 / 采样间隔)`——**更密不增加交付，只多耗电**（仓库已登记的结论）；
      * `P(送达) = 1 − (1 − p_uplink·p_backhaul)^(义务周期 / 上报周期)`。

    **它怎么对待"两次字段写入的实际等待与可能的中间配置"**（第 69 行）：
    一次决策**成对写入**（`stamp_pair`，同一个世代），并且**上一对还在途时不重复下单**
    （`in_flight` 直接跳过）。跨代混配由实例的 `mixed_config_s` 单列读数核验。
    """

    GRID_SAMPLING = GRID_SAMPLING
    GRID_REPORT = GRID_REPORT

    def __init__(self, routine_period_s: int = 3600, horizon_end_s: int = 12 * 3600,
                 uplink_p: float = 0.74, backhaul_p: float = 0.62,
                 harvest_wh_per_hour: float = 0.05, capacity_wh: float = 0.05,
                 dwell_s: int = 600) -> None:
        super().__init__()
        self.routine_period_s = int(routine_period_s)
        self.horizon_end_s = int(horizon_end_s)
        self.uplink_p, self.backhaul_p = float(uplink_p), float(backhaul_p)
        self.harvest_wh_per_hour = float(harvest_wh_per_hour)
        self.capacity_wh = float(capacity_wh)
        self.dwell_s = int(dwell_s)
        self._last: dict[str, int] = {}
        #: **为什么选它 / 为什么不换**：第 69 行要求输出"可行替代配置或保持原配置的原因"。
        self.reasons: dict[str, int] = {}
        self.choices: dict[str, tuple] = {}
        self.name = "rolling_search"

    def _load_h(self, i: int, r: int) -> float:
        return GRID_SAMPLE_WH * (3600.0 / i) + GRID_REPORT_WH * (3600.0 / r)

    def _search(self, soc_wh: float, t_s: int) -> tuple[tuple[int, int], str]:
        h_rem = max(0.0, (self.horizon_end_s - t_s) / 3600.0)
        p_link = self.uplink_p * self.backhaul_p
        feasible, allc = [], []
        for i in self.GRID_SAMPLING:
            for r in self.GRID_REPORT:
                load = self._load_h(i, r)
                soc_end = min(soc_wh + self.harvest_wh_per_hour * h_rem, self.capacity_wh) \
                    - load * h_rem
                p_collect = min(1.0, self.routine_period_s / i)
                k = max(1.0, self.routine_period_s / r)
                p_deliver = 1.0 - (1.0 - p_link) ** k
                exp_delivered = p_collect * p_deliver
                allc.append(((i, r), load, exp_delivered, soc_end))
                if soc_end >= 0.0:
                    feasible.append(((i, r), load, exp_delivered))
        if not feasible:
            # 一个都撑不住 ⇒ 先保命：取能耗最低的一档，而不是继续追交付。
            cheapest = min(allc, key=lambda x: x[1])
            return cheapest[0], "infeasible_min_load"
        feasible.sort(key=lambda x: (-x[2], x[1], -x[0][0], -x[0][1]))
        return feasible[0][0], "feasible_max_delivered"

    def plan(self, view: CenterView) -> list[tuple[str, dict]]:
        out = []
        for nid in view.node_ids:
            if nid in view.in_flight:
                self._skip("in_flight", nid)
                continue
            last = self._last.get(nid)
            if last is not None and view.t_s - last < self.dwell_s:
                self._skip("dwell", nid)
                continue
            soc = view.soc_of(nid)
            if soc is None:
                # 没有电量证据就不动。保守档与出厂默认逐位相同，发出去是值域空操作却要花一次机会。
                self._skip("no_soc", nid)
                continue
            snap = view.reports.get(nid) or {}
            current = (snap.get("sample_interval_s"), snap.get("report_period_s"))
            best, why = self._search(soc, view.t_s)
            self.reasons[why] = self.reasons.get(why, 0) + 1
            self.choices[nid] = best
            if best == current:
                self._skip("keep_current", nid)
                continue
            self._last[nid] = view.t_s
            a, b = self.stamp_pair(
                nid,
                {"op": OP_SET_SAMPLING_INTERVAL, "interval_s": best[0]},
                {"op": OP_SET_REPORT_PERIOD, "period_s": best[1]})
            out.append((nid, a))
            out.append((nid, b))
        return out

    def search_report(self) -> dict:
        """第 69 行要求的"可行替代配置或保持原配置的原因"的汇总。"""
        return {"reasons": dict(self.reasons),
                "last_choice_per_node": {k: list(v) for k, v in self.choices.items()}}


#: 第一轮的对照集合。**四条共享同一套现场自治、硬件与能量**，差别只在中心怎么花机会。
ARMS: dict[str, type[CenterPolicy]] = {
    "local": LocalPolicy,
    "fixed300": lambda: FixedPeriodPolicy(300),
    "fixed900": lambda: FixedPeriodPolicy(900),
    "aoi": lambda: AoiPolicy(),
    # **`aoi` 的前沿**：把同一个 AoI 策略沿三条旋钮展开，画出"传统方法能覆盖的区域"。
    # 旋钮：`stale_s`（多旧才加密，反应强度）、`fast_s`（加密档的上报周期，激进程度）、
    # `slow_s`（够新时的上报周期，空闲成本）。全部是**同一个策略结构**的参数取值，
    # 不是新机制——这一步的目的是知道传统做法的边界在哪里，而不是再发明启发式。
    "aoi_t900": lambda: AoiPolicy(stale_s=900),
    "aoi_t1800": lambda: AoiPolicy(stale_s=1800),
    "aoi_t7200": lambda: AoiPolicy(stale_s=7200),
    "aoi_t14400": lambda: AoiPolicy(stale_s=14400),
    "aoi_f600": lambda: AoiPolicy(fast_s=600),
    "aoi_f900": lambda: AoiPolicy(fast_s=900),
    "aoi_s1800": lambda: AoiPolicy(slow_s=1800),
    "aoi_s3600": lambda: AoiPolicy(slow_s=3600),
    # 端点：`fast_s == slow_s` 时策略退化成**固定周期上报**，于是 frontier 上同时有
    # "最省的传统做法"与"固定配置"两类参照点。
    "aoi_const300": lambda: AoiPolicy(fast_s=300, slow_s=300),
    "aoi_const3600": lambda: AoiPolicy(fast_s=3600, slow_s=3600),
    # **文献结构**：有限电池 EH 下的 (电量, 年龄) 二维联合门限（见 EhAoiPolicy 文档）。
    "eh_aoi": lambda: EhAoiPolicy(),
    "eh_aoi_t1800": lambda: EhAoiPolicy(age_dense_s=1800, age_fast_s=1800),
    "eh_aoi_s5": lambda: EhAoiPolicy(soc_th=0.005),
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
    # 下行代价的 Pareto 臂：单阈值 ea_i600 在容量 0.02 附近每种子发 69–83 次下行。
    # 死区 + 去抖把"翻转"压掉，目标是把下行压向固定配置的 36.5 而不损失服务。
    "ea_hyst1": lambda: EnergyAwarePolicy(0.010, 600, 900, exit_wh=0.006, confirm_n=2),
    "ea_hyst2": lambda: EnergyAwarePolicy(0.010, 600, 900, exit_wh=0.004, confirm_n=3),
    "ea_hyst3": lambda: EnergyAwarePolicy(0.010, 600, 900, exit_wh=0.002, confirm_n=4),
    # 省掉"未知状态时的保守配置"那一代（它与出厂默认相同，是空操作）。
    "ea_nb": lambda: EnergyAwarePolicy(0.010, 600, 900, send_when_unknown=False),
    #: **竞争解释臂**：只把电量阈值抬高，不加入任何准入。计划允许预先声明至多三个阈值候选，
    #: 这三档（0.010 / 0.015 / 0.018）就是全部，**不扫参**。
    "ea_nb_t15": lambda: EnergyAwarePolicy(0.015, 600, 900, send_when_unknown=False),
    "ea_nb_t18": lambda: EnergyAwarePolicy(0.018, 600, 900, send_when_unknown=False),
    "ea_nb_hyst": lambda: EnergyAwarePolicy(0.010, 600, 900, exit_wh=0.006, confirm_n=2,
                                            send_when_unknown=False),
    # **最强传统基线**：能源反馈（采样间隔）+ AoI 反馈（上报周期），成对下发、无读数不发。
    "ea_aoi": lambda: EnergyAoiPolicy(),
    "ea_aoi_h": lambda: EnergyAoiPolicy(exit_wh=0.006, confirm_n=2),
    # ---------------------------------------------------------------- 判定 B：合法配置网格
    # **补全 30 个合法点的静态前沿**（§31 第 77 行要求"所有合法配置的静态前沿"）。
    # 其中 10 个点本来就有臂覆盖（`report=900` 那行由 `dense*`、`sampling=3600` 那列由
    # `fixed*`/`aoi_const*`/`aoi_f600`/`aoi_s1800`），这里把它们**显式重述**成 `gridIxR`，
    # 使"所有合法配置"这个名字与实际跑过的集合逐项对齐；另外 20 个内部点是首次跑。
    # **取值一律来自 `GRID_SAMPLING × GRID_REPORT`，不新增动作面、不改任何既有臂的语义。**
    "grid300x300": lambda: GridConfigPolicy(300, 300),
    "grid300x600": lambda: GridConfigPolicy(300, 600),
    "grid300x900": lambda: GridConfigPolicy(300, 900),
    "grid300x1800": lambda: GridConfigPolicy(300, 1800),
    "grid300x3600": lambda: GridConfigPolicy(300, 3600),
    "grid600x300": lambda: GridConfigPolicy(600, 300),
    "grid600x600": lambda: GridConfigPolicy(600, 600),
    "grid600x900": lambda: GridConfigPolicy(600, 900),
    "grid600x1800": lambda: GridConfigPolicy(600, 1800),
    "grid600x3600": lambda: GridConfigPolicy(600, 3600),
    "grid900x300": lambda: GridConfigPolicy(900, 300),
    "grid900x600": lambda: GridConfigPolicy(900, 600),
    "grid900x900": lambda: GridConfigPolicy(900, 900),
    "grid900x1800": lambda: GridConfigPolicy(900, 1800),
    "grid900x3600": lambda: GridConfigPolicy(900, 3600),
    "grid1200x300": lambda: GridConfigPolicy(1200, 300),
    "grid1200x600": lambda: GridConfigPolicy(1200, 600),
    "grid1200x900": lambda: GridConfigPolicy(1200, 900),
    "grid1200x1800": lambda: GridConfigPolicy(1200, 1800),
    "grid1200x3600": lambda: GridConfigPolicy(1200, 3600),
    "grid1800x300": lambda: GridConfigPolicy(1800, 300),
    "grid1800x600": lambda: GridConfigPolicy(1800, 600),
    "grid1800x900": lambda: GridConfigPolicy(1800, 900),
    "grid1800x1800": lambda: GridConfigPolicy(1800, 1800),
    "grid1800x3600": lambda: GridConfigPolicy(1800, 3600),
    "grid3600x300": lambda: GridConfigPolicy(3600, 300),
    "grid3600x600": lambda: GridConfigPolicy(3600, 600),
    "grid3600x900": lambda: GridConfigPolicy(3600, 900),
    "grid3600x1800": lambda: GridConfigPolicy(3600, 1800),
    "grid3600x3600": lambda: GridConfigPolicy(3600, 3600),
    # **`rolling_search` 故意不放进 `ARMS`。** 它必须按**场景声明的**参数构造
    # （义务周期、剩余时域、两个链路概率、采能率、电池容量），而 `ARMS` 的工厂**拿不到**这些。
    # 在这里放一个"用默认值"的条目，只会让 `--arms rolling_search` **静默**跑成另一组条件——
    # 那正是 `build_kwargs` 的文档里写死的病："静默重放会悄悄跑成另一个实例，数字对不上才发现"。
    # 处理方式与仓库既有的 `clairvoyant_static` 一致（`instance_run.py` 直接构造、不进 ARMS），
    # 也与 `llm_naive_baseline.py` 的做法一致：**实验脚本在运行时注入**
    # `C.ARMS["rolling_search"] = <按场景参数构造的工厂>`（见 `code/experiments/config_grid_run.py`）。
}


def build_policy(name: str) -> CenterPolicy:
    try:
        factory = ARMS[name]
    except KeyError:
        raise ValueError(f"unknown arm {name!r}; have {sorted(ARMS)}") from None
    return factory()
