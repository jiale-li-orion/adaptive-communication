"""E2 — 节点—网关—中心的数据与状态传递，保留生成时刻与接收时刻。

v1.1 §4 要求每个执行位置只能看到**它真正收到的**东西，且每项带**生成／采集时间**与**接收时间**。
本模块把这两件事分开存：

    Sample     不可变，只记**采集时刻**（生成）与读数
    Transit    样本的传递台账：网关听到的时刻、中心收到的时刻、被丢弃的时刻

分开的理由是验收要求"遥测不会提前到达"以及"旧数据不冒充事件观测"都必须在**时刻**上可核算，
而不是靠某个字段的语义约定。

**物理层复用 `monitoring/opportunity.py` 的 `ControlPlane`**：LoRaWAN Class A 的接收窗口机会、
网关缓存、回传转发、空口能耗都在那里，且已有 32 项回归覆盖。本模块不重造网关队列。

**能源不使用预生成的存活序列**（v1.1 §8）：外生的是采能与温度，电池由 `Node` 自己积分，
因此两个跑不同动作的方法会得到不同的电量轨迹与不同的死亡时刻。

低温闸门是**器件参数**，不是硬编码的 LiFePO4 事实（v1.1 §8："合作方的供电不足不能被固定翻译成
某一种电池的冬季充电阈值"）。默认值标 A，且可整体替换。
"""

from __future__ import annotations

# --- module resolution -------------------------------------------------------
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime",
                                                     "experiments", "analysis",
                                                     "monitoring"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
# -----------------------------------------------------------------------------

from dataclasses import dataclass, field

from deterministic import stable_uniform
from opportunity import ControlPlane, LoRaProfile

TICK_S = 60

# ------------------------------------------------------------------ 器件参数（A 层，可整体替换）

@dataclass(frozen=True)
class DeviceProfile:
    """一台现场节点的能力与成本。**每个字段都要在实例 manifest 里给出层级。**

    默认值取自公开来源，但**不是任何具体站点的配置**：
      * 采样间隔与上报周期是两个独立字段（E：重庆 `0045`／`0042`）。
      * 缓存容量与溢出策略必须公开（v1.1 §5.3）；默认"丢最老"。
      * 低温闸门绑定器件：默认 `charge_min_c = 5.0`、`capacity_at_cold = 0.5` 是 **A** 层
        取值（来源为 LiFePO4 的一般特性），换电池化学必须整组替换。
    """

    name: str = "generic-lora-node"
    #: 本地默认采样间隔（s）。**A**：公开来源只给出"常态定时回传 1 h"，未单独公布常态采样间隔，
    #: 因此默认取与上报同频。它不是从来源读出的独立事实，换实例必须重定。
    sample_interval_s: int = 3600
    #: 本地默认上报周期（s）。与采样间隔独立（E：重庆 `0045`／`0042`）。
    report_period_s: int = 3600
    #: 本地事件触发后的加密采样间隔与名额数（E：Table 3 名义 300 s、`source_N` 恒为 3）。
    #: 加密意味着**比常态更密**：常态 3600 s 对事件 300 s，这才是"加密"的实际含义。
    event_interval_s: int = 300
    event_slots: int = 3
    #: 触发阈值（E：Table 3 记作 0.2 mm；完整累计窗口未闭合）。仅作元数据随触发事件携带，
    #: **不由节点从自己的稀疏采样里重新推导**——见 `Node.step` 的说明。
    threshold_mm: float = 0.2
    #: 本地事件触发是否立即上报（现场自治）。E：MS1 规格"阈值触发、自动采集上报"；
    #: S1 §4.4 现场低功耗逻辑检测异常并唤醒通信。**各方法共享此能力。**
    upload_on_event: bool = True
    #: 有限缓存。容量按**记录条数**计，溢出丢最老，并计数（v1.1 §5.3 要求公开溢出策略）。
    cache_slots: int = 240
    #: 每次采样的能量代价（Wh）。A 层。
    sample_wh: float = 2.0e-5
    #: 电池标称容量（Wh）与初值比例。
    capacity_wh: float = 40.0
    initial_soc: float = 1.0
    #: 低温闸门：低于此温度不能充电；可用容量按 `capacity_at_cold` 折算到 `cold_ref_c`。
    charge_min_c: float | None = 5.0
    cold_ref_c: float = -20.0
    capacity_at_cold: float = 0.5
    #: 静息功耗（Wh / tick）。
    idle_wh_per_tick: float = 0.0


# ------------------------------------------------------------------ 样本与传递台账

@dataclass(frozen=True)
class Sample:
    """一条采集记录。不可变；**只带采集时刻**，不带任何"到达"信息。"""

    sample_id: str
    node_id: str
    measurand: str
    taken_at: int          # 采集（生成）时刻
    value: float           # 读数 —— v1.1 §4 要求 `Sample` 必须包含读数与单位
    unit: str
    quality: str = "ok"


@dataclass
class PowerLedger:
    """一台节点的电量账本。**动作驱动**：采能是外生的，耗电按实际动作累加。

    它存在的意义是让"两个跑不同动作的方法会得到不同的电量轨迹与不同的死亡时刻"这句话可核查，
    而不是靠一个预生成的存活序列（v1.1 §8）。
    """

    soc_initial_wh: float
    soc_wh: float
    harvested_wh: float = 0.0
    consumed_wh: float = 0.0
    deficit_s: int = 0
    dead_at_s: int | None = None

    def to_dict(self) -> dict:
        return {"soc_initial_wh": self.soc_initial_wh, "soc_final_wh": self.soc_wh,
                "harvested_wh": self.harvested_wh, "consumed_wh": self.consumed_wh,
                "deficit_s": self.deficit_s, "dead_at_s": self.dead_at_s}


@dataclass
class Transit:
    """一个样本的传递台账：三个时刻分开记，**顺序由代码强制**。

    `heard_at` 是网关听到的时刻，`received_at` 是中心收到的时刻。二者都是 `None` 表示尚未到达。
    网关与中心之间还有回传，因此 `received_at >= heard_at`；接入与采集之间同理
    `heard_at >= taken_at`（同一 tick 内相等是允许的）。
    """

    sample_id: str
    heard_at: int | None = None
    received_at: int | None = None
    dropped_at: int | None = None


# ------------------------------------------------------------------ 节点

class Node:
    """一台现场监测节点：本地采样、本地触发、有限缓存、自动补发、动作驱动的电量。"""

    def __init__(self, node_id: str, measurand: str, profile: DeviceProfile = DeviceProfile(),
                 *, initial_soc: float | None = None, initial_wh: float | None = None,
                 is_gateway: bool = False) -> None:
        """`initial_soc` 是**比例**，`initial_wh` 是**绝对 Wh**；给后者时它优先。

        两个入口都保留是因为它们服务不同的人：manifest 与实例说明按 Wh 说话（"初始 0.3 mWh"），
        而 `DeviceProfile.initial_soc` 是设备配置的一部分。混用会出错——测试里就犯过一次：
        把 1e-6 当成 Wh 写下去，实际得到 4e-5 Wh，够采一条样。
        """
        self.node_id = node_id
        self.measurand = measurand
        #: 网关上的雨量计**没有接入跳**：它就是网关，数据直接进网关缓存，只有回传那一跳。
        #: 这是 S1 的角色事实（EI01 是带雨量计的主节点／网关），不是简化。
        self.is_gateway = is_gateway
        self.p = profile
        # 配置：本地默认值，可被中心下发的命令改写（改写需要命令到达，不在本模块内假装即时生效）
        self.sample_interval_s = profile.sample_interval_s
        self.report_period_s = profile.report_period_s
        # 电量
        if initial_wh is not None:
            self.soc_wh = float(initial_wh)
        else:
            self.soc_wh = profile.capacity_wh * (
                profile.initial_soc if initial_soc is None else initial_soc)
        self.power = PowerLedger(soc_initial_wh=self.soc_wh, soc_wh=self.soc_wh)
        self.alive = True
        # 缓存：只有**未确认**的记录
        self.cache: list[Sample] = []
        self.transit: dict[str, Transit] = {}
        # 本地事件触发状态：剩余名额与下一次加密采样时刻
        self.event_left = 0
        self.next_event_sample_at: int | None = None
        #: 还有几批事件样本等待上报。>0 时上报周期被临时提升为本 tick（本地自治）。
        self.event_upload_pending = 0
        # 计数器（供手工核算）
        self.sampled = 0
        self.dropped = 0
        self.dead_at: int | None = None
        self.idle_ticks = 0

    # -------------------------------------------------- 电量

    def usable_capacity_wh(self, temp_c: float | None) -> float:
        """温度对可用容量的折算。**器件参数**，不是普适物理常数。"""
        if temp_c is None:
            return self.p.capacity_wh
        if temp_c <= self.p.cold_ref_c:
            return self.p.capacity_wh * self.p.capacity_at_cold
        return self.p.capacity_wh * self.p.capacity_at_cold if temp_c < 0.0 \
            else self.p.capacity_wh

    def _step_power(self, t_s: int, truth) -> None:
        """积分一步电量：先采能（受温度闸门约束），再扣静息。风险由动作单独扣。"""
        temp = truth.temp_at(self.node_id, t_s)
        harvest = truth.harvest_at(self.node_id, t_s)
        can_charge = temp is None or self.p.charge_min_c is None or temp >= self.p.charge_min_c
        if can_charge and harvest > 0.0:
            before = self.soc_wh
            self.soc_wh = min(self.usable_capacity_wh(temp), self.soc_wh + harvest)
            self.power.harvested_wh += self.soc_wh - before
        self.soc_wh -= self.p.idle_wh_per_tick
        self.power.consumed_wh += self.p.idle_wh_per_tick
        if self.soc_wh <= 0.0:
            self.soc_wh = 0.0
            self.power.deficit_s += TICK_S
            if self.alive:
                self.alive = False
                self.dead_at = t_s
                self.power.dead_at_s = t_s
        self.power.soc_wh = self.soc_wh

    def spend(self, wh: float) -> None:
        """扣一次动作能耗并记帐。"""
        self.soc_wh -= wh
        self.power.consumed_wh += wh
        self.power.soc_wh = self.soc_wh

    # -------------------------------------------------- 采样与本地触发

    def _due(self, t_s: int) -> bool:
        if self.event_left > 0:
            return t_s == self.next_event_sample_at
        return t_s % self.sample_interval_s == 0

    def step(self, t_s: int, truth) -> list[Sample]:
        """推进一个 tick。**无电时不产生任何样本**（验收：失电不补造样本）。

        **触发从哪来。** v1.1 §5.2 允许"现阶段回放公开触发标记"，并禁止"由日雨量或任意插值序列
        自造高频阈值触发并称真实事件"。因此触发事件是**外生的**（`truth.triggers`），节点侧只做
        一件事：**在可供电时按共享规则响应它**——这是现场自治，不消耗下行（S1 §4.4、v1.1 §10）。

        让节点自己从稀疏的常态采样里重新推导触发是错的：那会引入一个来源没有的检测模型，而且
        阈值累计窗口尚未闭合（v1.1 §11）。阈值随事件携带，只作元数据。
        """
        self._step_power(t_s, truth)
        if not self.alive:
            self.idle_ticks += 1
            return []
        if self._trigger_fires(t_s, truth):
            self.event_left = self.p.event_slots
            self.next_event_sample_at = t_s
            if self.p.upload_on_event:
                self.event_upload_pending = self.p.event_slots
        if not self._due(t_s):
            return []
        new = self._take(t_s, truth, self.measurand)
        if self.event_left > 0:
            self.event_left -= 1
            self.next_event_sample_at = (t_s + self.p.event_interval_s) if self.event_left > 0 else None
        return new

    def _trigger_fires(self, t_s: int, truth) -> bool:
        """本地共享规则：本次 tick 有一个属于本节点的外生触发，且本节点可供电。"""
        return any(t == t_s and nid == self.node_id for t, nid in truth.triggers)

    def _take(self, t_s: int, truth, measurand: str) -> list[Sample]:
        if self.soc_wh < self.p.sample_wh:
            self.alive = False
            self.dead_at = t_s
            return []
        self.spend(self.p.sample_wh)
        value = truth.reading_at(self.node_id, measurand, t_s)
        unit = "mm" if measurand == "rainfall" else "mm"
        s = Sample(sample_id=f"{self.node_id}:{measurand}:{t_s}",
                   node_id=self.node_id, measurand=measurand,
                   taken_at=t_s, value=value, unit=unit)
        self.sampled += 1
        self.cache.append(s)
        self.transit[s.sample_id] = Transit(sample_id=s.sample_id)
        while len(self.cache) > self.p.cache_slots:      # 溢出：丢最老，并计数
            old = self.cache.pop(0)
            self.transit[old.sample_id].dropped_at = t_s
            self.dropped += 1
        return [s]

    # -------------------------------------------------- 上报与自动补发

    def upload_due(self, t_s: int) -> bool:
        """到点上报，或事件样本待发（本地自治把上报周期临时提升）。

        **两条路径都是本地能力**：常态按上报周期，事件触发后立即发。中心改变上报周期是另一回事，
        需要命令到达，不在本模块内假装即时生效。
        """
        if not self.alive:
            return False
        return self.event_upload_pending > 0 or t_s % self.report_period_s == 0

    def batch(self, t_s: int, max_slots: int = 32) -> list[Sample]:
        """取本周期要发的记录。**自动补发**：缓存里全是未确认记录，因此天然按最老优先重传。

        这是设备既有能力，**所有基线共享**（v1.1 §5.3、§6）；中心的显式区间／游标／预算补传是
        另一件事，属于扩展项，本模块不实现。
        """
        if not self.alive or not self.cache:
            return []
        if self.event_upload_pending > 0:
            self.event_upload_pending -= 1
        return self.cache[:max_slots]

    def ack(self, sample_ids) -> None:
        ids = set(sample_ids)
        self.cache = [s for s in self.cache if s.sample_id not in ids]

    def snapshot(self, t_s: int) -> dict:
        """搭车遥测里的状态字段。**含电量**——v1.1 §4 要求电量进入可见历史。"""
        return {"read_at": t_s, "soc_wh": round(self.soc_wh, 6),
                "sample_interval_s": self.sample_interval_s,
                "report_period_s": self.report_period_s,
                "cache_level": len(self.cache), "alive": self.alive}


# ------------------------------------------------------------------ 中心

class Center:
    """中心：只保有一份**它真正收到**的可见历史 `O_center(t)`。

    它不能读环境真值，也不能读节点缓存。所有回答都从 `self.received` 与 `self.reports` 里来。
    """

    def __init__(self) -> None:
        self.received: dict[str, Sample] = {}
        self.received_at: dict[str, int] = {}
        self.reports: dict[str, dict] = {}          # node_id -> 最新一份搭车状态
        self.report_at: dict[str, int] = {}
        self.items_forwarded = 0

    def receive(self, item, t_s: int) -> None:
        """网关转来一批东西。**收到的时刻一律用调用方给的 t_s**，不早于网关听到的时刻。"""
        for sample in getattr(item, "payload", None) or ():
            self.received[sample.sample_id] = sample
            self.received_at[sample.sample_id] = t_s
        if item.snapshot:
            self.reports[item.node_id] = dict(item.snapshot)
            self.report_at[item.node_id] = t_s
        self.items_forwarded += 1

    def newest_taken_at(self, node_id: str) -> int | None:
        stamps = [s.taken_at for s in self.received.values() if s.node_id == node_id]
        return max(stamps) if stamps else None

    def aoi(self, node_id: str, t_s: int) -> int | None:
        """中心 AoI：`t - max(taken_at of valid arrived samples)`，无观测时返回 None。

        **不得默认为 0**（v1.1 §9）：从未收到过任何测值的区间要单列"尚无观测时长"。
        """
        newest = self.newest_taken_at(node_id)
        return None if newest is None else t_s - newest


# ------------------------------------------------------------------ 闭环

@dataclass
class HopLog:
    """一次运行的全部传递记录，供手工核算用。"""

    samples: dict[str, Sample] = field(default_factory=dict)
    transit: dict[str, Transit] = field(default_factory=dict)
    #: 环境真值。评分器要用它把"源触发"与"设备检测"分开计时（v1.1 §4）。
    #: **它只进评分器，不进任何策略的可见历史**——策略只看 `O_i(t)`。
    truth: object | None = None


class Instance:
    """把外生过程、节点、网关／链路与中心接成一个最小闭环。

    网关与链路复用 `ControlPlane`：`uplink()` 决定接入是否被听到，`gateway_ingest()` 缓存，
    `backhaul_forward()` 在回传可用时交给中心。
    """

    def __init__(self, nodes: dict[str, Node], truth, seed: int,
                 profile: LoRaProfile | None = None,
                 uplink_p_arrive: float = 0.74,
                 backhaul_p_good: float = 0.62,
                 backhaul_delay_s: int = 0) -> None:
        # 节点是**每次运行的状态**：缓存与传递台账都属于这一次运行。把同一批节点交给两个
        # Instance 会在第二次运行里看到上一次残留的缓存，而 `sample_id` 是按时刻命名的，
        # 于是旧样本会被当成新样本发出去——静默混合两次运行。**响亮地失败，不要静默。**
        for nid, node in nodes.items():
            if node.cache or node.transit:
                raise ValueError(
                    f"node {nid!r} is not fresh: cache={len(node.cache)} "
                    f"transit={len(node.transit)}. Nodes carry per-run state; "
                    f"build new ones for each Instance (see nodes_from).")
        self.nodes = nodes
        self.truth = truth
        self.seed = seed
        self.plane = ControlPlane(profile or LoRaProfile(), seed=seed,
                                  uplink_p_arrive=uplink_p_arrive,
                                  backhaul_p_good=backhaul_p_good,
                                  backhaul_delay_s=backhaul_delay_s)
        self.center = Center()
        self.log = HopLog()
        self._radio_wh_seen: dict[str, float] = {}

    # -------------------------------------------------- 一个 tick

    def tick(self, t_s: int) -> dict:
        """推进一个 tick，返回本 tick 的事件计数（供手工核算）。"""
        counters = {"sampled": 0, "uplinks": 0, "heard": 0, "forwarded": 0}
        hour = t_s // 3600

        # 1) 节点在本地采样（含本地触发）；无电则不产生样本
        for node in self.nodes.values():
            for sample in node.step(t_s, self.truth):
                self.log.samples[sample.sample_id] = sample
                self.log.transit[sample.sample_id] = node.transit[sample.sample_id]
                counters["sampled"] += 1

        # 2) 到上报周期的节点发一批（缓存里全是未确认记录 → 自动补发）
        for node in self.nodes.values():
            if not node.upload_due(t_s):
                continue
            batch = node.batch(t_s)
            if not batch:
                continue
            if node.is_gateway:
                # 网关自己的传感器：没有接入跳，直接进网关缓存。`heard_at` 就是采集时刻。
                counters["heard"] += 1
                for sample in batch:
                    self.log.transit[sample.sample_id].heard_at = t_s
                self.plane.gateway_ingest(node.node_id, t_s,
                                          [s.sample_id for s in batch],
                                          node.snapshot(t_s), payload=list(batch))
                continue
            payload_bytes = max(16, 12 * len(batch))
            rec = self.plane.uplink(node.node_id, hour=hour, sf=9,
                                    payload_bytes=payload_bytes,
                                    attempt_index=t_s // TICK_S)
            counters["uplinks"] += 1
            self._charge_radio(node)
            if not rec.arrived:
                continue
            counters["heard"] += 1
            for sample in batch:
                self.log.transit[sample.sample_id].heard_at = t_s
            self.plane.gateway_ingest(node.node_id, t_s,
                                      [s.sample_id for s in batch],
                                      node.snapshot(t_s), payload=list(batch))

        # 3) 回传可用时，网关把缓存的交给中心
        for item in self.plane.backhaul_forward(t_s):
            self.center.receive(item, t_s)
            counters["forwarded"] += 1
            for sample in (item.payload or ()):
                self.log.transit[sample.sample_id].received_at = t_s
                self.nodes[sample.node_id].ack([sample.sample_id])
        return counters

    def _charge_radio(self, node: Node) -> None:
        """把 `ControlPlane` 记的空口能耗搬进节点电池（动作驱动，不是预生成序列）。"""
        spent = self.plane.energy.get(node.node_id)
        if spent is None:
            return
        total = spent.total_wh          # RadioEnergy.total_wh 是 property
        delta = total - self._radio_wh_seen.get(node.node_id, 0.0)
        self._radio_wh_seen[node.node_id] = total
        if delta > 0:
            node.spend(delta)

    def run(self, hours: int) -> HopLog:
        self.log.truth = self.truth
        for t_s in range(0, hours * 3600, TICK_S):
            self.tick(t_s)
        return self.log


def nodes_from(deployment, profile: DeviceProfile | None = None,
               initial_wh: float | None = None) -> dict[str, Node]:
    """按部署建节点集合。

    **主实例只用非绕射边缘的位点**（`deployment.node_ids`）——那些判定随 1–2 米翻转的位点，
    其"可达性"是坐标巧合而不是地形事实。排除数在 `deployment.marginal` 里单列。
    """
    dp = profile or DeviceProfile()
    out: dict[str, Node] = {}
    gw = deployment.gateway
    out[gw.sid] = Node(gw.sid, gw.measurand, dp, initial_wh=initial_wh, is_gateway=True)
    for site in deployment.nodes:
        if site.sid not in deployment.node_ids:
            continue
        out[site.sid] = Node(site.sid, site.measurand, dp, initial_wh=initial_wh)
    return out
