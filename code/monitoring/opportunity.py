#!/usr/bin/env python3
"""
opportunity.py — the control plane, where downlink is an opportunity and not a function call.

The model this replaces treated a command as a call that succeeds or fails on its own schedule.
In the deployment this project studies, downlink is not like that. A LoRaWAN Class A node
initiates every exchange: it transmits, then opens RX1 and RX2, then sleeps. Once asleep there is
no receive window at all. So a downlink opportunity exists only where the node's own uplink
created one, and the number of opportunities a node offers over a horizon is bounded by the
number of uplinks it makes.

Three consequences follow, and they are the reason this module exists:

  * A retry budget cannot manufacture opportunities. Asking again costs energy and occupies the
    channel, and it can only be asked inside a window the node opened.
  * A command can be accepted by the gateway long before it can be delivered. The gateway is a
    store-and-forward party, so "the center sent it" and "the node received it" are separated by
    an interval the center cannot observe.
  * Verification and progress compete for the same scarce resource. A reconciliation read
    consumes an opportunity that could have carried a write.

Every packet is charged its real time on air: preamble, header, coding rate and payload, at the
node's spreading factor and bandwidth. Airtime is not payload bits divided by a nominal bitrate.

Region profile is explicit. The defaults below describe CN470 and must not be read as a
compliance statement: before any regulatory claim, the duty cycle and channel plan have to come
from the deployment's actual band, and a build that kept EU868 limits while describing a Chinese
site would be wrong in both directions.

Deps: numpy-free; standard library plus this package.
"""
from __future__ import annotations

# --- module resolution -------------------------------------------------------
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime",
                                                     "experiments", "analysis"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
# -----------------------------------------------------------------------------

import math
from dataclasses import dataclass, field

from deterministic import stable_uniform


# --------------------------------------------------------------------- radio
@dataclass(frozen=True)
class LoRaProfile:
    """Regional and modulation parameters. Airtime is derived from these, never assumed."""

    region: str = "CN470"
    bw_khz: float = 125.0
    coding_rate: int = 1          # 1..4, meaning 4/(4+cr)
    preamble_symbols: int = 8
    explicit_header: bool = True
    crc: bool = True
    # No duty-cycle limit is applied by default. Whether one applies is a property of the
    # deployment's band, and this value must be set from the real regulation before any
    # compliance claim is made. EU868 would be 0.01 here.
    duty_cycle: float | None = None

    def _low_data_rate_optimise(self, sf: int) -> bool:
        # Standard behaviour: the low-data-rate optimisation is mandatory at SF11/SF12 on 125 kHz.
        return sf >= 11 and self.bw_khz == 125.0

    def time_on_air_ms(self, sf: int, payload_bytes: int) -> float:
        """Semtech-style packet airtime: preamble + header + coded payload.

        Included deliberately: the preamble and the coding rate are a large fraction of the
        time on air for the short frames this deployment sends, so a payload-per-bitrate
        estimate understates the cost of exactly the messages the runtime sends most of.
        """
        if not 7 <= sf <= 12:
            raise ValueError(f"spreading factor {sf} outside 7..12")
        if self.coding_rate not in (1, 2, 3, 4):
            raise ValueError(f"coding rate 4/{4 + self.coding_rate} is not defined")
        tsym_ms = (2 ** sf) / (self.bw_khz * 1000.0) * 1000.0
        t_preamble = (self.preamble_symbols + 4.25) * tsym_ms
        ih = 0 if self.explicit_header else 1
        de = 1 if self._low_data_rate_optimise(sf) else 0
        numerator = 8 * payload_bytes - 4 * sf + 28 + 16 * (1 if self.crc else 0) - 20 * ih
        denominator = 4 * (sf - 2 * de)
        n_payload = 8 + max(math.ceil(numerator / denominator) * (self.coding_rate + 4), 0)
        return t_preamble + n_payload * tsym_ms


# --------------------------------------------------------------------- energy
# Per-radio energy coefficients. These are A-layer assumptions about a device class, not
# measurements of a specific module; a bench measurement replaces them.
TX_MA_AT_14DBM = 44.0
RX_MA = 11.0
SLEEP_UA = 5.0
BUS_V = 3.6


@dataclass
class RadioEnergy:
    """Energy spent by radio activity, in Wh, kept separate from the node's own load."""

    tx_wh: float = 0.0
    rx_wh: float = 0.0

    def add_tx(self, airtime_ms: float, tx_current_ma: float = TX_MA_AT_14DBM) -> None:
        self.tx_wh += BUS_V * (tx_current_ma / 1000.0) * (airtime_ms / 3.6e6)

    def add_rx(self, window_ms: float) -> None:
        self.rx_wh += BUS_V * (RX_MA / 1000.0) * (window_ms / 3.6e6)

    @property
    def total_wh(self) -> float:
        return self.tx_wh + self.rx_wh


# --------------------------------------------------------------------- messages
@dataclass
class DownlinkMessage:
    """One message the center wants delivered to a node.

    `identity` is the logical operation this message carries. It is part of every random draw
    this message takes part in, so two different operations queued at the same node and hour do
    not share an outcome.
    """

    identity: str
    kind: str                      # 'command' | 'read_request'
    payload_bytes: int
    enqueued_at: int
    expires_at: int | None = None
    #: 命令携带的参数（例如要设置的字段与新值）。**默认空**，因此既有的调用点与读数逐位不变；
    #: 加了它之后，实例层的中心下发不再需要把参数塞进 `kind` 字符串里。
    payload: dict = field(default_factory=dict)


@dataclass
class Delivery:
    message: DownlinkMessage
    node_id: str
    hour: int
    opportunity_index: int         # which uplink of this node carried it


@dataclass(frozen=True)
class PathSpec:
    """One candidate way for the center to reach the gateway.

    The first-round architecture has exactly one (the intermittent cellular backhaul). Adding a
    second is how the "there is always an out-of-band channel" objection is answered honestly rather
    than by assertion: a supplementary path shares the gateway, the power and the last hop with the
    primary one, so it can improve whether a **command** arrives and cannot improve whether its
    **effect** is observed. The evidence still comes back on the node's own uplink, which is shared.
    """

    name: str
    p_good: float


@dataclass
class GatewayItem:
    """One thing the gateway has heard and not yet handed to the center.

    An uplink that reached the gateway is not yet visible to the center. The gateway buffers it
    and forwards when the backhaul is up, so the observation path is node to gateway to center
    rather than node to center. Collapsing the gateway into the center made every fault that
    targets the return path inert, which is why this exists.
    """

    node_id: str
    heard_at_s: int
    sample_ids: tuple[str, ...]
    snapshot: dict
    identity: str | None = None       # set when the item is an acknowledgement rather than telemetry
    kind: str = "telemetry"
    payload: object = None            # opaque to this module; the runner pairs it with its records


@dataclass
class UplinkRecord:
    node_id: str
    hour: int
    opportunity_index: int          # -1 when the gateway did not hear the uplink
    payload_bytes: int
    airtime_ms: float
    arrived: bool = True
    delivered: list[Delivery] = field(default_factory=list)


# --------------------------------------------------------------------- the plane
class ControlPlane:
    """Opportunity-constrained downlink over a store-and-forward gateway.

    The path a command takes is: center -> backhaul -> gateway queue -> (the node's next uplink)
    -> RX window -> node. Each arrow can fail, and the failures are not interchangeable: a
    backhaul outage delays the command at the center, a gateway queue delay holds it until an
    opportunity exists, and an RX-window loss loses the attempt but leaves the command queued.

    `downlink_per_uplink` is a scenario parameter, not a design choice. Class A gives at most one
    successful downlink per uplink in this model; a PSM Active Time window could carry several,
    which is why the parameter exists rather than a constant.
    """

    def __init__(self, profile: LoRaProfile, seed: int, downlink_per_uplink: int = 1,
                 rx_window_ms: float = 2000.0, backhaul_p_good: float = 0.62,
                 uplink_p_arrive: float = 0.74, backhaul_delay_s: int = 0,
                 burst_p_gb: float | None = None, burst_p_bg: float | None = None,
                 uplink_burst_p_gb: float | None = None,
                 uplink_burst_p_bg: float | None = None):
        if downlink_per_uplink < 1:
            raise ValueError("downlink_per_uplink must be at least 1")
        self.profile = profile
        self.seed = seed
        self.downlink_per_uplink = downlink_per_uplink
        self.rx_window_ms = rx_window_ms
        self.backhaul_p_good = backhaul_p_good
        self.uplink_p_arrive = uplink_p_arrive
        #: **两态马尔可夫回传**（可选）。`None` 表示保持原来的**逐小时独立同分布**。
        #:
        #: 为什么要它：仓库自己从 ChirpBox 拟合出平均下行突发 **6.38 h**，而同丢失率下的
        #: i.i.d. 对照只有 **1.45 h**（**突发度 4.39×**）。但实例里的 `path_available` 一直是
        #: i.i.d. ——**拟合出来的时间相关性从未被用上**。在一个 residual 主要落在 delivery 侧的
        #: 实例里，这比"数据弱"更严重：**连已有的拟合都没用**。
        #:
        #: 参数取 `(p_gb, p_bg)`，**从平稳分布起链、逐小时递推**，因此状态序列只由
        #: `(seed, 绝对小时)` 决定，**与策略无关**（跨策略比较的前提）。
        self.burst_p_gb, self.burst_p_bg = burst_p_gb, burst_p_bg
        self._burst_series: list[bool] = []
        #: **上行接入的突发模型**（可选，逐节点）。设置后**替代**原来逐分钟的 i.i.d. 抽签：
        #: 小时级的可用性由两态链给出（平稳可用概率仍是 `uplink_p_arrive`），
        #: 于是**只改突发度、不改均值**。
        self.uplink_burst_p_gb, self.uplink_burst_p_bg = (uplink_burst_p_gb,
                                                          uplink_burst_p_bg)
        self._ul_burst: dict[str, list[bool]] = {}
        self.backhaul_gate = None
        # Store-and-forward latency on the gateway-to-center hop. Zero means the gateway forwards
        # as soon as the link is up; a positive value models a batch that leaves on a schedule.
        self.backhaul_delay_s = int(backhaul_delay_s)
        # Candidate paths, primary first. One path is the first-round architecture; a second is the
        # independent-management-path control, and it is never offered as a health channel.
        self.paths: list[PathSpec] = [PathSpec("backhaul", backhaul_p_good)]
        self.path_accepted: dict[int, int] = {}
        self.path_refused: dict[int, int] = {}

        self.queued: dict[str, list[DownlinkMessage]] = {}
        # Store-and-forward at the gateway. Nothing here is visible to the center yet.
        self.gateway_pending: list[GatewayItem] = []
        self.backhaul_forwarded = 0
        self.backhaul_backlog_peak = 0
        self.energy: dict[str, RadioEnergy] = {}

        # Counters. The opportunity bound is asserted on these, so they are not diagnostics.
        self.uplinks = 0
        self.uplinks_heard = 0
        self.opportunities_created: dict[str, int] = {}
        # Attempts, not successes. An attempt spends the opportunity whether or not it lands,
        # so bounding only the deliveries would let a model retry without limit and still pass.
        self.opportunities_used: dict[str, int] = {}
        self.backhaul_accepted = 0
        self.backhaul_refused = 0
        self.downlink_attempts = 0
        self.downlink_delivered = 0
        self.downlink_lost = 0
        self.downlink_expired = 0
        self.airtime_uplink_ms = 0.0
        self.airtime_downlink_ms = 0.0

    # ------------------------------------------------------------- center side
    def path_available(self, hour: int, path: int = 0) -> bool:
        """Whether candidate path `path` is up this hour. Exogenous, shared by all methods.

        Each path draws independently, so a supplementary link fails on its own schedule rather than
        with the primary. What does not vary is everything downstream of the gateway: a path that is
        up still delivers nothing to a node with no power, no RX window, or a dead radio, and it
        still carries no evidence back, because the evidence rides the node's uplink.

        `backhaul_gate` is an optional additional condition the run may install, used by the fault
        trajectories to take the primary path down for a window. It can only ever make it less
        available, never more, so a fault cannot hand an arm an advantage.
        """
        spec = self.paths[path]
        if path == 0:
            # The primary path keeps the key it has always had. Changing it would redraw every hour
            # of the exogenous trace and silently invalidate every reading taken before the second
            # path existed -- the numbers would move and nothing would say why.
            if self.backhaul_gate is not None and not self.backhaul_gate(hour):
                return False
            if self.burst_p_gb is not None and self.burst_p_bg is not None:
                return self._burst_available(hour)
            return stable_uniform(self.seed, "backhaul", hour) < spec.p_good
        # A supplementary path draws on its own key, so it fails on its own schedule rather than
        # with the primary. It shares everything downstream of the gateway, which is what keeps it
        # from being an out-of-band health channel.
        return stable_uniform(self.seed, "path", spec.name, hour) < spec.p_good

    def _ul_burst_state(self, node_id: str, hour: int) -> bool:
        """逐节点两态马尔可夫接入：坏态以 `p_bg` 转好、好态以 `p_gb` 转坏；首小时从平稳分布抽。

        平稳好态概率取 `min(1, uplink_p_arrive / 1.0)`——即**保持与 i.i.d. 相同的边际可用率**，
        所以两者之差**只在时间结构上**。状态只由 `(seed, 节点, 0..h)` 决定，**与策略无关**。
        """
        gb, bg = self.uplink_burst_p_gb, self.uplink_burst_p_bg
        good_frac = min(1.0, max(0.0, self.uplink_p_arrive))
        seq = self._ul_burst.setdefault(node_id, [])
        while len(seq) <= hour:
            h = len(seq)
            if h == 0:
                seq.append(stable_uniform(self.seed, "ulburst0", node_id, gb, bg) < good_frac)
                continue
            prev_bad = not seq[h - 1]
            u = stable_uniform(self.seed, "ulburst", node_id, h)
            seq.append(u < bg if prev_bad else not (u < gb))
        return seq[hour]

    def _burst_available(self, hour: int) -> bool:
        """两态马尔可夫：坏态以 `p_bg` 转好、好态以 `p_gb` 转坏；首小时从**平稳分布**抽。

        逐小时递推并缓存，所以第 h 小时的状态只由 `(seed, 0..h)` 决定——**与策略无关**。
        """
        gb, bg = self.burst_p_gb, self.burst_p_bg
        while len(self._burst_series) <= hour:
            h = len(self._burst_series)
            if h == 0:
                bad = stable_uniform(self.seed, "burst0", gb, bg) < (gb / (gb + bg))
                self._burst_series.append(not bad)
                continue
            prev_bad = not self._burst_series[h - 1]
            u = stable_uniform(self.seed, "burst", h)
            self._burst_series.append(u < bg if prev_bad else not (u < gb))
        return self._burst_series[hour]

    def backhaul_available(self, hour: int) -> bool:
        """Whether the primary path is up. Kept as the name the rest of the model already uses."""
        return self.path_available(hour, 0)

    def center_send(self, node_id: str, message: DownlinkMessage, hour: int,
                    path: int = 0) -> bool:
        """Center -> gateway over one candidate path. Returns whether the gateway accepted it.

        Acceptance is not delivery. The message joins the node's queue at the gateway and waits
        for an opportunity, which is exactly the interval the center cannot observe. A refusal on
        one path says nothing about the others, and -- this is the part that matters -- a path that
        carried the command says nothing about whether the node acted on it.
        """
        if not self.path_available(hour, path):
            self.backhaul_refused += 1
            self.path_refused[path] = self.path_refused.get(path, 0) + 1
            return False
        self.queued.setdefault(node_id, []).append(message)
        self.path_accepted[path] = self.path_accepted.get(path, 0) + 1
        self.backhaul_accepted += 1
        return True

    def queued_count(self, node_id: str) -> int:
        return len(self.queued.get(node_id, ()))

    # -------------------------------------------------------------- node side
    def prune(self, node_id: str, hour: int) -> int:
        """Drop queued messages whose validity has passed. Returns how many were dropped.

        Expiry is a property of time, not of a window opening. Pruning only inside the delivery
        path would let a node that never gets heard accumulate expired commands without bound,
        and would make the queue's contents depend on the node's uplink luck rather than on the
        deadlines the center set.
        """
        queue = self.queued.get(node_id)
        if not queue:
            return 0
        live = [m for m in queue if m.expires_at is None or m.expires_at >= hour]
        dropped = len(queue) - len(live)
        self.downlink_expired += dropped
        if live:
            self.queued[node_id] = live
        else:
            self.queued.pop(node_id, None)
        return dropped

    # --------------------------------------------------------------- gateway side
    def gateway_ingest(self, node_id: str, heard_at_s: int, sample_ids, snapshot: dict,
                       identity: str | None = None, kind: str = "telemetry",
                       payload: object = None) -> GatewayItem:
        """Buffer what the gateway heard. Not visible to the center until the backhaul carries it."""
        item = GatewayItem(node_id=node_id, heard_at_s=heard_at_s,
                           sample_ids=tuple(sample_ids), snapshot=dict(snapshot),
                           identity=identity, kind=kind, payload=payload)
        self.gateway_pending.append(item)
        self.backhaul_backlog_peak = max(self.backhaul_backlog_peak, len(self.gateway_pending))
        return item

    def backhaul_forward(self, t_s: int, delay_s: int = 0) -> list[GatewayItem]:
        """Hand buffered items to the center, if the backhaul is up at this instant.

        A store-and-forward gateway holds everything it has heard until the link is back, so a
        backhaul outage delays telemetry by its own duration rather than dropping it. That is why
        a backhaul fault now reaches the metric: the records are late, and a late record can miss
        a delivery deadline it would otherwise have met.
        """
        if not self.backhaul_available(int(t_s // 3600)):
            return []
        forwarded = [i for i in self.gateway_pending if t_s - i.heard_at_s >= delay_s]
        self.gateway_pending = [i for i in self.gateway_pending if t_s - i.heard_at_s < delay_s]
        self.backhaul_forwarded += len(forwarded)
        return forwarded

    def uplink(self, node_id: str, hour: int, sf: int, payload_bytes: int,
               attempt_index: int = 0) -> UplinkRecord:
        """The node transmits. An opportunity exists only if the gateway heard it.

        The node opens RX1/RX2 after every transmission regardless, but the gateway can only use
        a window it knows about, and it knows about one only by having received the uplink that
        preceded it. Counting opportunities per transmission rather than per received uplink
        would overstate the control channel's capacity and, worse, would give the coordinator
        windows that no real gateway could have scheduled into.

        The transmit costs its full time on air either way, and the node pays for the receive
        window either way: both are spent before the node can learn whether anyone heard it.
        """
        self.uplinks += 1
        airtime = self.profile.time_on_air_ms(sf, payload_bytes)
        self.airtime_uplink_ms += airtime
        energy = self.energy.setdefault(node_id, RadioEnergy())
        energy.add_tx(airtime)
        # The node opens RX1/RX2 after every uplink whether or not anything is waiting for it.
        # Charging the window only when a downlink is attempted would make an idle node look free
        # to poll, which is the opposite of the constraint this module models.
        energy.add_rx(self.rx_window_ms)

        self.prune(node_id, hour)
        if self.uplink_burst_p_gb is not None and self.uplink_burst_p_bg is not None:
            heard = self._ul_burst_state(node_id, hour)
        else:
            heard = stable_uniform(self.seed, "ul", node_id, hour,
                                   attempt_index) < self.uplink_p_arrive
        if not heard:
            self.uplinks_unheard = getattr(self, "uplinks_unheard", 0) + 1
            return UplinkRecord(node_id=node_id, hour=hour, opportunity_index=-1,
                                payload_bytes=payload_bytes, airtime_ms=airtime, arrived=False)

        self.uplinks_heard += 1
        index = self.opportunities_created.get(node_id, 0)
        self.opportunities_created[node_id] = index + 1
        record = UplinkRecord(node_id=node_id, hour=hour, opportunity_index=index,
                              payload_bytes=payload_bytes, airtime_ms=airtime, arrived=True)
        record.delivered = self._deliver(node_id, hour, index, sf)
        return record

    def _deliver(self, node_id: str, hour: int, opportunity_index: int,
                 sf: int) -> list[Delivery]:
        """Deliver queued messages inside the window this uplink opened."""
        queue = self.queued.get(node_id)
        if not queue:
            return []

        delivered: list[Delivery] = []
        for slot in range(self.downlink_per_uplink):
            self.prune(node_id, hour)
            queue = self.queued.get(node_id)
            if not queue:
                break

            message = queue[0]
            self.downlink_attempts += 1
            self.opportunities_used[node_id] = self.opportunities_used.get(node_id, 0) + 1
            airtime = self.profile.time_on_air_ms(sf, message.payload_bytes)
            self.airtime_downlink_ms += airtime
            self.energy.setdefault(node_id, RadioEnergy()).add_tx(airtime)

            # **潜在结果按"机会"固定，不按"报文"固定。**
            #
            # 这一行原先用 `message.identity`（= `cmd{全局序号}`）当键。它的副作用是
            # **counterfactual 污染**：任何一处多发一条命令都会推进全局序号，于是**所有节点
            # 后续的下行抽签全部平移**——策略 A 多发一个包之后，策略 B 看到的"随机链路"
            # 已经不是同一条。跨策略比较（尤其"再聪明一点还能拿回几条"这类问题）因此不成立。
            #
            # 改成按 `(node_id, opportunity_index, slot)` 抽签：`opportunity_index` 是
            # **这台节点的第 k 次机会**，是**物理资源**，与队列里放了什么、放了多少无关。
            # 语义上正确的读法是："这台节点得到的第 k 次机会有固定的命运，策略只决定是否使用它。"
            # 注意各机会之间仍然是独立的：机会数由节点自己的上行节奏决定，改上报周期本来就会
            # 改变机会数——那是策略**真的**在改变它拥有的资源，不是污染。
            u = stable_uniform(self.seed, "rx-win", node_id, opportunity_index, slot)
            if u < self._downlink_success_p(sf):
                queue.pop(0)
                self.downlink_delivered += 1
                delivered.append(Delivery(message=message, node_id=node_id, hour=hour,
                                          opportunity_index=opportunity_index))
            else:
                self.downlink_lost += 1

        if not queue:
            self.queued.pop(node_id, None)
        return delivered

    def _downlink_success_p(self, sf: int) -> float:
        """Probability the downlink survives this hop.

        A-layer: a single figure for the access hop, standing in for the terrain-driven loss
        distribution the physics layer computes. It is a scenario parameter here because the
        business layer's question is about opportunity allocation, not about propagation; the
        propagation model is exercised in the mechanism-isolation layer.
        """
        return 0.72

    def downlink_opportunities(self, node_id: str) -> int:
        return self.opportunities_created.get(node_id, 0) * self.downlink_per_uplink

    # ---------------------------------------------------------------- invariant
    def check_opportunity_bound(self) -> None:
        """No node may have received more downlink attempts than its uplinks created.

        This is the module's reason to exist. A model that lets a command be retried without an
        uplink is not modelling Class A, and the error is invisible in the results: it looks like
        a runtime that retries well.
        """
        for node_id, used in self.opportunities_used.items():
            limit = self.downlink_opportunities(node_id)
            if used > limit:
                raise AssertionError(
                    f"{node_id}: {used} downlink attempts but only {limit} opportunities "
                    f"({self.opportunities_created.get(node_id, 0)} uplinks x "
                    f"{self.downlink_per_uplink})")
        total_attempts = self.downlink_attempts
        total_opportunity = self.uplinks_heard * self.downlink_per_uplink
        if total_attempts > total_opportunity:
            raise AssertionError(
                f"{total_attempts} downlink attempts against {total_opportunity} opportunities "
                f"({self.uplinks_heard} heard uplinks x {self.downlink_per_uplink}; "
                f"{self.uplinks} transmitted)")

    def summary(self) -> dict:
        return {
            "uplinks": self.uplinks,
            "uplinks_heard": self.uplinks_heard,
            "opportunities": self.uplinks_heard * self.downlink_per_uplink,
            "backhaul_accepted": self.backhaul_accepted,
            "backhaul_refused": self.backhaul_refused,
            "downlink_attempts": self.downlink_attempts,
            "downlink_delivered": self.downlink_delivered,
            "downlink_lost": self.downlink_lost,
            "downlink_expired": self.downlink_expired,
            "backhaul_forwarded": self.backhaul_forwarded,
            "backhaul_backlog_peak": self.backhaul_backlog_peak,
            "backhaul_backlog_now": len(self.gateway_pending),
            "path_accepted": dict(self.path_accepted),
            "path_refused": dict(self.path_refused),
            "opportunities_used": dict(self.opportunities_used),
            "airtime_uplink_ms": self.airtime_uplink_ms,
            "airtime_downlink_ms": self.airtime_downlink_ms,
            "radio_wh": {k: v.total_wh for k, v in self.energy.items()},
        }
