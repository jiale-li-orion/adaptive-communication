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

from center import (OP_SET_REPORT_PERIOD, OP_SET_SAMPLING_INTERVAL, CenterPolicy,
                    CenterView, LocalPolicy)
from deterministic import stable_uniform
from opportunity import ControlPlane, DownlinkMessage, LoRaProfile

TICK_S = 60

#: **一次上报机会能服务的记录条数**（`Node.batch` 的 `max_slots` 默认值）。
#: §31 §五 指出这类缓存/打包机制的**正确激活量**是"积压记录数**超过一次载荷容量**"——
#: 不是"断链超过 32 个上报周期"（那只在采样与上报周期相同时成立），也不能只看包数或清空率。
CACHE_PAYLOAD_SLOTS = 32

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
    #: 缓存被取走的**服务次序**，即"一次上报机会该花在哪几条记录上"。
    #: - `fifo`：最老优先（设备既有的自动补发语义；v1.1 §5.3、§6 把它定为**各方法共享的既有能力**）；
    #: - `lifo`：最新优先取一批，**旧记录仍留在缓存里**（因此载荷一直满）；
    #: - `latest_only`：只留最新一条，旧记录**丢弃**（AoI 文献的标准队列纪律：
    #:   新记录抢占、旧记录不再重传）。载荷最小、能耗最低，代价是旧义务永久放弃。
    #: **这是实例属性，不是策略动作。** 动作面仍然只有 `sampling interval` 与 `report period`
    #: 两个字段；换服务次序等于换一个实例，**所有臂必须在同一取值下重跑**才构成公平对照。
    cache_service: str = "fifo"
    #: **监测义务节奏（s）**——打包纪律要把一条记录映射到"它在服务哪条义务"上：
    #: 窗口 `k = taken_at // obligation_period_s`，该窗口的观察截止是 `(k+2)·period`
    #: （与 `exogenous.Obligation.deadline` 同定义，见那里的 `window[1] + grace_s`）。
    #:
    #: **这是一项显式声明的 A 层设备能力**（§31 §五）：设备的打包软件**知道自己的监测契约节奏**。
    #: `fifo`/`lifo`/`latest_only` **不使用**它；`edf`/`obligation_greedy` 使用。
    #: **所有臂在同一取值下跑**，因此它不偏向任何方法——不存在"把更好的固件只给本文"。
    obligation_period_s: int = 3600
    #: 单次采样周期的能量代价（Wh）。**取自实测剖面**：活跃窗口约 15 s、平均 35.7 mA、母线 3.3 V
    #: → 约 4.9e-4 Wh/周期（Ragnoli 等, *JLPEA* 12(3):47, 2022）。减去 `RadioEnergy` 另计的空口
    #: 部分后取 4.7e-4。**原先默认 2e-5 比它低约 25 倍**，那使能量约束在整轮实验里都没有被触到
    #: （电池恒满、零死节点），能源列因此不携带信息。这是本轮修正的一处 A 层取值。
    sample_wh: float = 4.7e-4
    #: 电池标称容量（Wh）与初值比例。
    #: 电池标称容量（Wh）。0.05 Wh ≈ 13.5 mAh @3.7 V，是**小型现场站**的量级；取大值会让
    #: "多采一点"与"熬过这个冬天"之间的取舍消失，而那正是本场景要建模的取舍。
    capacity_wh: float = 0.05
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
        #: **执行层状态**：远端见过哪些逻辑身份、以及版本高水位。这两样决定"重复能否被识别"
        #: 与"更旧的写入能否被拒绝"。没有它们时，一条迟到很久的命令会照常生效。
        self.applied_logicals: set[str] = set()
        self.applied_version = 0
        #: 中心最近一次**想**让它跑的上报周期，以及中心认为已经在位的值。用于算配置错配时长。
        self.wanted_period_s: int | None = None
        #: 每个配置字段各自生效到第几代。**两个字段的世代不一致 = 跨代混配**：节点正在跑一个
        #: 没有任何 planner 请求过的组合（如"新上传周期 + 旧采样间隔"）。协议里
        #: `sampling interval` 与 `report period` 本来就是两个独立字段，间歇链路下极易错位。
        self.field_generation: dict[str, int | None] = {"interval": None, "period": None}
        #: 已到货但**尚未成对**的字段：generation -> {field: value}
        self.pending_fields: dict[int, dict] = {}
        #: 最近一次**完整成对生效**的世代号。
        self.config_generation: int | None = None
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
            # 缺电时长按"节点不存活"计，**不按 soc<=0 计**：节点也可能因为"剩余电量不够采一条"
            # 而被判死，那时 soc 并不为 0。只按 soc<=0 计会让这类死亡完全不进账本（实测踩过：
            # deficit 恒为 0，而节点明明已经死了）。
            self.power.deficit_s += TICK_S
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
        """取本周期要发的记录。**自动补发**：缓存里全是未确认记录，按 `cache_service` 决定次序。

        `fifo`（默认）＝最老优先重传：这是设备既有能力，**所有基线共享**（v1.1 §5.3、§6）。
        `lifo` ＝最新优先：一次机会只花在最新的记录上。两者是**同一个实例的两个取值**，
        不是两个策略——中心的动作面在两种取值下完全相同。

        中心的显式区间／游标／预算补传是另一件事，属于扩展项，本模块不实现。
        """
        if not self.alive or not self.cache:
            return []
        if self.event_upload_pending > 0:
            self.event_upload_pending -= 1
        if self.p.cache_service == "lifo":
            # 最新优先：取最新的一批，并按"最新在前"排列。一次上报里整批同时到达，
            # 因此批内次序不影响读数，取序只决定**哪些记录占掉这次机会**。
            # 注意：旧记录**留在缓存里**，于是此后每次机会都带着满批载荷——空口时间与能耗
            # 因此居高不下。这正是 AoI 文献里"只保留最新"要避免的那件事，见 `latest_only`。
            return self.cache[-max_slots:][::-1]
        if self.p.cache_service == "latest_only":
            # **只留最新**：AoI 文献的标准队列纪律（新记录抢占、旧记录丢弃）。
            # 它把载荷压到最小（一条记录），因此每次机会的空口时间与能耗都最低；
            # 代价是被丢掉的旧义务永久拿不回来。**丢弃要记账**，否则缓存溢出计数会失真。
            newest = self.cache[-1]
            for old in self.cache[:-1]:
                self.transit[old.sample_id].dropped_at = t_s
                self.dropped += 1
            self.cache = [newest]
            return [newest]
        if self.p.cache_service in ("edf", "obligation_greedy"):
            # **两种"按义务"的纪律**（§31 §五 第一项判别要求加入的两条）。
            # 它们只用**设备自己知道的东西**：缓存的未确认记录 + 自己的监测契约节奏。
            # 不需要中心告知"哪些已经被收到"——被收到的记录由 `ack()` 移出缓存（**见限定**：
            # 本实例的 ack 是中心收到时同步施加的，不占空口，这一简化对所有纪律同等有利）。
            period = max(1, int(self.p.obligation_period_s))
            if self.p.cache_service == "edf":
                # **EDF**：按义务窗口升序（等价于观察截止升序），窗内再按采集时刻升序。
                # 这是教科书最早截止期优先，**没有任何需要调的权重**。
                ordered = sorted(self.cache,
                                 key=lambda s: (s.taken_at // period, s.taken_at))
                return ordered[:max_slots]
            # **按有效监测义务匹配的普通贪心**：**一条义务只花一个名额**——
            # 每个窗口只留**窗内最新**的那条（窗内更新更可取），再按窗口升序取。
            # 旧记录**不丢弃**（只是不占这次机会），因此不改变后续义务的可得性。
            newest_in_window: dict[int, Sample] = {}
            for s in self.cache:
                k = s.taken_at // period
                cur = newest_in_window.get(k)
                if cur is None or s.taken_at > cur.taken_at:
                    newest_in_window[k] = s
            return [newest_in_window[k] for k in sorted(newest_in_window)][:max_slots]
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
                 burst_p_gb: float | None = None, burst_p_bg: float | None = None,
                 uplink_burst_p_gb: float | None = None,
                 uplink_burst_p_bg: float | None = None,
                 backhaul_delay_s: int = 0,
                 policy: CenterPolicy | None = None,
                 send_contract_fields: bool = False,
                 hold_every: int = 0, hold_s: int = 0, hold_op: str | None = None,
                 atomic_generation: bool = False,
                 access_outage: tuple[int, int] | None = None,
                 placement: str = "center",
                 trace: bool = False) -> None:
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
                                  burst_p_gb=burst_p_gb, burst_p_bg=burst_p_bg,
                                  uplink_burst_p_gb=uplink_burst_p_gb,
                                  uplink_burst_p_bg=uplink_burst_p_bg,
                                  backhaul_delay_s=backhaul_delay_s)
        #: 中心策略。默认不下发任何命令——**这是所有方法的共同起点**，现场自治照常工作。
        self.policy: CenterPolicy = policy or LocalPolicy()
        #: 执行层开关：报文是否携带稳定逻辑身份与单调版本。
        self.send_contract_fields = send_contract_fields
        #: **按世代原子应用**：一次配置决策的两个字段要么都生效、要么都不生效。
        #: 逐字段 fencing 做不到这件事——它拒掉陈旧的那个字段、却留下新的另一个字段，
        #: 于是节点跑在一个从未被任何 planner 请求过的混合配置上（实测混配时间反而更长）。
        self.atomic_generation = atomic_generation
        self.center = Center()
        self.log = HopLog()
        #: **执行位置**（v1.1 §4 的"每个执行位置只能看到它真正收到的"）。
        #:   `center`  —— 现状：策略读中心收到的遥测，命令经回传进网关队列（默认，逐位不变）。
        #:   `gateway` —— 位置对照臂：**同一个策略对象、同一套规则**，改由网关用它自己**真正听到**
        #:                的遥测来求值，命令直接从网关进节点队列（不经回传）。
        #: 其余一切（空口机会、节点队列、接收窗口、能耗、策略参数）两处完全相同——
        #: 只允许读取各位置实际可见的信息，这正是 §31 第 53 行要求的对照条件。
        if placement not in ("center", "gateway"):
            raise ValueError(f"placement must be 'center' or 'gateway', got {placement!r}")
        self.placement = placement
        #: **网关自己保存的遥测**：它听到过的每台节点的最近一份状态快照与听到时刻。
        #: 必须独立于 `plane.gateway_pending` 存——因为 `backhaul_forward()` 会把已转发的条目
        #: 从 `gateway_pending` 里**移走**，网关若只靠那张表就会被"转发"这个动作抹掉记忆。
        #: 现实中网关当然记得自己收到过什么；这里只是把它如实建出来。
        self.gateway_reports: dict[str, dict] = {}
        self.gateway_report_at: dict[str, int] = {}
        self.gateway_newest_taken_at: dict[str, int] = {}
        #: **打包机制的激活量**（§31 §五）：积压超过一次载荷容量的 (tick, 节点) 次数峰值，
        #: 以及缓存的平均深度。**必须逐条件量它，不能只挑长中断**——40 h 断链单点
        #: 不能证明实际部署常见收益。
        self.cache_over_payload_ticks = 0
        self.cache_over_payload_peak = 0
        self.cache_len_sum = 0
        self.cache_len_n = 0
        self._radio_wh_seen: dict[str, float] = {}
        self.command_seq = 0
        self.counters = {"commands_sent": 0, "commands_delivered": 0,
                         "commands_refused": 0,
                         "deduplicated": 0, "fenced": 0,
                         # **逐命令归类**（v1.1 的"动作准入"计数）。三条互斥且穷尽：
                         #   changed   —— 写入的值与节点当时的值**不同**，真的改了配置；
                         #   same      —— 写入的值与节点当时的值**相同**，是**值域空操作**；
                         #   speculative —— 中心对这台设备的电量**没有读数**时的保守下发。
                         # 分开数才答得上"多余的控制流量是什么"。只数总量答不了。
                         "writes_changed": 0, "writes_same_value": 0,
                         "writes_speculative": 0, "stale_generation_dropped": 0}
        #: 延迟释放：identity -> 允许到达的最早时刻。空表示网络不扣留任何命令。
        self.hold_until: dict[str, int] = {}
        #: 被网络扣留、对中心不可见的命令：(释放时刻, 节点, 报文)。
        self.held: list[tuple[int, str, object]] = []
        self.hold_every = hold_every
        self.hold_s = hold_s
        #: 只扣留某一类字段命令。**多字段跨代一致性的构造手段**：若只扣留
        #: `set_sampling_interval` 而放过 `set_report_period`，节点的采样间隔会落后于世代，
        #: 而上传周期照常前进，于是形成一个**从未被任何 planner 请求过的混合配置**
        #: （例如"新上传周期 + 旧采样间隔"）。这正是两个独立配置字段在间歇链路下的真实风险。
        self.hold_op = hold_op
        self.mixed_config_ticks = 0
        #: 接入中断窗 (start_s, end_s)：**节点仍有电、仍在采样，只是上行到不了网关**。
        #: 与回传中断的区别是丢失发生在哪一跳，而这两跳的业务后果不同（v1.1 §5.3）。
        self.access_outage = access_outage
        self.access_blocked = 0
        #: 中心下发的**意图**日志：(t_s, node_id, 目标周期)。用于算"中心自己的意图有没有在位"。
        #: 它与"外部配置要求"不同——v1.1 §9 只对后者算错配时长，这里是意图达成度，不是正确性。
        self.intent_log: list[tuple[int, str, int]] = []
        #: **生成原因分类的计数**。账本已按 `change`/`same_value`/`unknown`/`stale` 分了**结果**，
        #: 但"为什么会产生这条意图"是另一个问题，而且它才是**能在生成侧消掉浪费**的那个问题
        #: （轨 C 要的正是这一层）。三类互斥且完备，见 `_note_intent_reason` 与 `intent_reasons()`。
        self._intent_reason_counts: dict[str, dict[str, int]] = {
            "generated": {"unknown_state": 0, "target_change": 0, "resend": 0},
            # 成本侧：**这条意图有没有真的占掉一次下行机会**——生成侧与到达侧的成本不同，
            # 混在一起就答不上"浪费在哪一跳"。
            "sent": {"unknown_state": 0, "target_change": 0, "resend": 0},
        }
        self._target_of: dict[str, tuple] = {}
        #: **逐事件时间线（默认关闭）。** 打开时记下"中心看到什么 → 下了什么 → 节点何时真的生效
        #: → 节点当时在跑什么配置/还剩多少电"。**结果文件只存聚合量，存不下这条链**，
        #: 而"配置生效之后持续耗电"这类问题只有把链连起来才答得上。
        #: 关闭时**一个字节都不记**，所以带 trace 的运行必须与登记的结果逐位相同（已核）。
        self.trace = trace
        self.trace_events: list[tuple] = []
        #: 最近一次为某节点生成的意图属于哪一类，供 `_send_command` 记 **sent 侧**的成本。
        self._last_reason: dict[str, str] = {}
        #: 状态观测模型，由 runner 注入。默认完美观测。
        from center import SocObservationModel as _SocModel
        self.soc_model = _SocModel()
        self.held_dispatched = 0

    # -------------------------------------------------- 一个 tick

    def tick(self, t_s: int) -> dict:
        """推进一个 tick，返回本 tick 的事件计数（供手工核算）。"""
        counters = {"sampled": 0, "uplinks": 0, "heard": 0, "forwarded": 0}
        hour = t_s // 3600

        # 0) **过期的下发命令按时间清理，与投递路径无关。**
        #
        # `prune` 的文档写着"过期是时间的性质、不是窗口打开的性质"，但在这之前它**只在
        # 投递路径里被调用**（`uplink` 与 `_deliver`）。接入中断期间 `tick` 在到达 `uplink`
        # 之前就 `continue` 了，于是那条规则**一次也没有被执行**：队列既不清空、也不过期。
        # 而 `CenterView.in_flight` 定义为"该节点队列非空"，所以一次足够长的接入中断会让
        # **`in_flight` 永久为真**，每条策略都在读电量之前 `continue` 掉该节点——
        # **中心被永久静音，而日志上看起来像"策略决定不再下发"**。
        # 这一步把时间驱动真正落实：每个 tick 对每个节点清理一次。
        for node_id in self.nodes:
            counters["pruned"] = counters.get("pruned", 0) + \
                self.plane.prune(node_id, t_s)

        # 1) 节点在本地采样（含本地触发）；无电则不产生样本
        for node in self.nodes.values():
            for sample in node.step(t_s, self.truth):
                self.log.samples[sample.sample_id] = sample
                self.log.transit[sample.sample_id] = node.transit[sample.sample_id]
                counters["sampled"] += 1
            if self.trace:
                # 节点侧**此刻真实在跑什么**：两个周期字段、真实电量、是否还活着。
                self.trace_events.append(
                    (t_s, node.node_id, "state", node.sample_interval_s,
                     node.report_period_s, round(node.soc_wh, 8), node.alive))

        # 1.4) **量打包机制的激活量**：积压是否真的跨过了"一次机会能服务的容量"。
        #      只记数，不改任何行为（关掉它读数逐位不变）。
        for node in self.nodes.values():
            depth = len(node.cache)
            self.cache_len_sum += depth
            self.cache_len_n += 1
            if depth > CACHE_PAYLOAD_SLOTS:
                self.cache_over_payload_ticks += 1
                self.cache_over_payload_peak = max(self.cache_over_payload_peak, depth)

        # 1.5) 策略按**它所处位置看得见的东西**决定要不要下发。
        #      `center` —— 读中心收到的遥测，命令经回传进网关队列，等接收窗口（默认，逐位不变）。
        #      `gateway` —— **同一个策略对象、同一套规则**，改读网关自己真正听到的遥测；
        #                   命令直接进网关队列（位置在下游，命令不必再经回传）。
        view = (self._gateway_view(t_s) if self.placement == "gateway"
                else self._center_view(t_s))
        # 跳过原因要带时刻；`_skip_t` **只用于记录**，不参与判断。
        self.policy._skip_t = t_s
        for node_id, payload in self.policy.plan(view):
            self._note_intent_reason(node_id, payload, view)
            if self.trace:
                # **诊断字段（不参与判断）**：把中心**这条证据有多旧**一起记下来。
                # 为什么必须记：闭环的资格先用 `T_loop` 的两条腿衡量，而 `T_evidence`
                # （新证据真正到中心的时延）在 trace 里**原本测不到**——`state` 是节点侧
                # 自己的时刻，`plan` 只有中心相信的值，没有接收侧时刻。`soc_age_s()` 按
                # **源时刻**算（测试 [29] 覆盖），所以它就是这个决策所用证据的年龄。
                # 只加字段、不改条件、不改策略；加了之后读数逐位不变（测试 [28] 钉住）。
                self.trace_events.append(
                    (t_s, node_id, "plan", view.soc_of(node_id), payload.get("op"),
                     payload.get("period_s", payload.get("interval_s")),
                     view.soc_age_s(node_id),
                     # **诊断字段**：本条意图的**生成原因**（`unknown_state`/`target_change`/`resend`，
                     # 由上面刚调用的 `_note_intent_reason` 写在 `_last_reason` 上）。
                     # episode 聚合要按"同一个 target 的所有重试属于同一 episode"来切，
                     # 而切分依据正是这三类语义——**复用现有语义，不新造一套**。
                     self._last_reason.get(node_id)))
            self._send_command(node_id, payload, t_s, origin=self.placement)

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
                self._note_gateway_heard(node, t_s, batch)
                self.plane.gateway_ingest(node.node_id, t_s,
                                          [s.sample_id for s in batch],
                                          node.snapshot(t_s), payload=list(batch))
                continue
            if self.access_outage is not None and \
                    self.access_outage[0] <= t_s < self.access_outage[1]:
                # 接入中断：上行根本没到网关。**节点照常采样与缓存**，因此这里的损失全部是
                # 交付侧，采集侧不受影响——与失电的区别正在于此。
                self.access_blocked += 1
                continue
            payload_bytes = max(16, 12 * len(batch))
            rec = self.plane.uplink(node.node_id, hour=hour, sf=9,
                                    payload_bytes=payload_bytes,
                                    attempt_index=t_s // TICK_S)
            counters["uplinks"] += 1
            for delivery in rec.delivered:
                ident = delivery.message.identity
                release_at = self.hold_until.get(ident)
                if release_at is not None:
                    if t_s < release_at:
                        # 网络把它扣住了。**关键：它不能留在网关队列里。** 被扣留的命令对中心
                        # 是不可见的——中心看到网关队列空了，就会认为这条已经了结，于是继续下发
                        # 新的目标。留在队列里会让 `in_flight` 永远为真、中心永不重发，危险交错
                        # 根本不可能形成（这是实现里踩过的一个错）。因此扣留件放在**独立的持有表**
                        # 里，只在释放时刻回到投递路径。
                        self.held.append((release_at, node.node_id, delivery.message))
                        self.counters["held_waiting"] = self.counters.get("held_waiting", 0) + 1
                        continue
                    self.hold_until.pop(ident, None)
                self._apply_delivery(delivery, t_s)
            self._charge_radio(node)
            if not rec.arrived:
                continue
            counters["heard"] += 1
            for sample in batch:
                self.log.transit[sample.sample_id].heard_at = t_s
            self._note_gateway_heard(node, t_s, batch)
            self.plane.gateway_ingest(node.node_id, t_s,
                                      [s.sample_id for s in batch],
                                      node.snapshot(t_s), payload=list(batch))

        # 2.5 命令在接收窗口里送达 → 落到节点上。**送达才是生效**，不是发出。
        # （下发在 uplink 内部完成，此处只统计；应用已在 `_apply_delivery` 里做。）

        # 2.7) 释放到期的扣留件。**迟到到达**：中心早已按新目标下过别的命令。
        released = [x for x in self.held if x[0] <= t_s]
        self.held = [x for x in self.held if x[0] > t_s]
        for _rel, node_id, message in released:
            self.counters["held_released"] = self.counters.get("held_released", 0) + 1
            self._apply_delivery(type("D", (), {"node_id": node_id, "message": message})(), t_s)

        # 3) 回传可用时，网关把缓存的交给中心
        for item in self.plane.backhaul_forward(t_s):
            self.center.receive(item, t_s)
            counters["forwarded"] += 1
            for sample in (item.payload or ()):
                self.log.transit[sample.sample_id].received_at = t_s
                self.nodes[sample.node_id].ack([sample.sample_id])
        # 跨代混配：两个配置字段的世代号不一致，说明节点正在跑一个**没有任何 planner 请求过
        # 的组合**（如"新上报周期 + 旧采样间隔"）。协议里 sampling interval 与 report period
        # 本来就是两个独立字段，间歇链路下极易错位。按 v1.1 §9 这属于**代价**，单列，不计正确性。
        for node in self.nodes.values():
            gi = node.field_generation.get("interval")
            gp = node.field_generation.get("period")
            if gi is not None and gp is not None and gi != gp:
                self.mixed_config_ticks += TICK_S

        return counters

    # -------------------------------------------------- 中心侧

    def _center_view(self, t_s: int) -> CenterView:
        """把中心**真正收到的**东西整理成视图。环境真值与节点缓存都不在其中。"""
        newest: dict[str, int] = {}
        for sample in self.center.received.values():
            cur = newest.get(sample.node_id)
            if cur is None or sample.taken_at > cur:
                newest[sample.node_id] = sample.taken_at
        in_flight = frozenset(
            nid for nid in self.nodes if self.plane.queued_count(nid) > 0)
        return CenterView(t_s=t_s, node_ids=tuple(self.nodes), reports=self.center.reports,
                          report_at=self.center.report_at, newest_taken_at=newest,
                          in_flight=in_flight, soc_model=self.soc_model)

    def _note_gateway_heard(self, node, t_s: int, batch) -> None:
        """把"网关此刻真正听到了什么"记进**网关自己的**台账。

        **必须与 `plane.gateway_ingest` 分开记。** 那张 `gateway_pending` 是"还没转交给中心"
        的待发表，`backhaul_forward()` 一旦转发就会把条目**移走**；网关若只靠它，
        "转发"这个动作会把网关对自己收到过什么的记忆抹掉——那是伪造出来的失忆，
        不是任何真实设备的行为。
        """
        self.gateway_reports[node.node_id] = node.snapshot(t_s)
        self.gateway_report_at[node.node_id] = t_s
        newest = self.gateway_newest_taken_at.get(node.node_id)
        for sample in batch:
            if newest is None or sample.taken_at > newest:
                newest = sample.taken_at
        if newest is not None:
            self.gateway_newest_taken_at[node.node_id] = newest

    def _gateway_view(self, t_s: int) -> CenterView:
        """网关在 t 时刻**合法知道**的一切——严格来自它自己听到的上行。

        **不读环境真值、不读节点缓存、不读中心收到的东西。** 返回的是与 `_center_view`
        **同一个 `CenterView` 结构**，于是**同一个策略对象**在两处读的是同一种接口，
        两处之差只剩"数据来源"这一个变量——这正是 §31 第 53 行"只允许读取各位置实际可见的
        信息"要隔离的东西。

        **一处已知的建模简化（必须在论文里声明）**：`in_flight` 在 `_center_view` 里本来就是
        按"网关队列非空"算的，也就是**中心被赋予了对网关队列的可见性**——这是本仓库既有的
        建模选择，不是本次改动引入的。这里对网关用**同一个表达式**，因此它不会给网关侧带来
        相对优势；但它确实让"中心不知道队列"这一更严格的读法没有被测到。
        """
        in_flight = frozenset(
            nid for nid in self.nodes if self.plane.queued_count(nid) > 0)
        return CenterView(t_s=t_s, node_ids=tuple(self.nodes),
                          reports=self.gateway_reports,
                          report_at=self.gateway_report_at,
                          newest_taken_at=self.gateway_newest_taken_at,
                          in_flight=in_flight, soc_model=self.soc_model)

    def _send_command(self, node_id: str, payload: dict, t_s: int,
                      origin: str = "center") -> None:
        """把一条意图放进回传。**它此刻还没有到达任何地方。**

        契约字段由**臂**决定发不发：`send_contract_fields=True` 时随报文带上稳定逻辑身份与单调
        版本，远端据此能识别重复、拒绝更旧的写入。两条臂用同一条中心策略、同一套动作，差别只在
        这两个字段——这满足 v1.1 §10"执行层的差异应在同一动作集合下体现"。
        """
        self.command_seq += 1
        body = dict(payload)
        if self.send_contract_fields:
            # 逻辑身份必须**按字段**定：`sampling interval` 与 `report period` 虽然共享一个世代号，
            # 但它们是两条可独立重发的命令。身份里省掉字段维度，同一次决策的第二个字段在远端
            # 就与"第一个字段的重发"不可区分，会被当成重复而永久丢弃——那样原子层永远凑不齐一对，
            # 契约层则每次只落地一个字段。**两个字段都携带同一个 `generation`，身份必须各自不同。**
            body["logical"] = (f"{node_id}:{payload.get('op', 'cmd')}:"
                               f"{payload.get('generation', 0)}")
            body["version"] = self.command_seq
        msg = DownlinkMessage(
            identity=f"cmd{self.command_seq:05d}",
            kind=payload.get("op", "command"),
            payload_bytes=16,
            enqueued_at=t_s,
            expires_at=t_s + 6 * 3600,
            payload=body)
        if origin == "gateway":
            # **网关自己产生命令**：没有回传跳，因此不会被 `path_available` 拒绝。
            # 下游完全不变——同一个节点队列、同一个接收窗口、同一份空口能耗、同样会丢。
            ok = self.plane.gateway_send(node_id, msg)
        else:
            ok = self.plane.center_send(node_id, msg, t_s // 3600)
        if ok:
            self.counters["commands_sent"] += 1
            if origin == "gateway":
                # 通信量必须能按**来源**分列，否则"网关位置省了多少下行"答不上来。
                self.counters["commands_sent_by_gateway"] = \
                    self.counters.get("commands_sent_by_gateway", 0) + 1
            if self.trace:
                # **诊断字段**：把这条命令的**逻辑身份**记下来，闭环诊断才能**按身份**配对
                # 而不是按"同节点同值"。`aoi` 有 67% 的 intent 是重发（§6.24），按值配对会让
                # 多条 plan 认领同一次 `applied`。身份由上面的 `body["logical"]` 定义
                # （`{node}:{op}:{generation}`），节点侧用 `applied_logicals` 去重，是同一个串。
                self.trace_events.append(
                    (t_s, node_id, "sent", body.get("logical"), body.get("op"),
                     body.get("period_s", body.get("interval_s"))))
            _r = self._last_reason.get(node_id)
            if _r is not None:
                self._intent_reason_counts["sent"][_r] += 1
            if body.get("op") in (OP_SET_REPORT_PERIOD, OP_SET_SAMPLING_INTERVAL):
                val = int(body.get("period_s", body.get("interval_s")))
                self.intent_log.append((t_s, node_id + ":" + body["op"], val))
            # 延迟释放：按固定步长扣留一部分命令，让它们越过中心后来的目标变更。
            # **按真实下发武装**，不按时钟时刻武装——按时刻武装会落在什么都不发生的分钟上。
            hold_it = False
            if self.hold_op is not None:
                hold_it = (body.get("op") == self.hold_op)
            elif self.hold_every:
                hold_it = (self.counters["commands_sent"] % self.hold_every == 0)
            if hold_it:
                self.hold_until[f"cmd{self.command_seq:05d}"] = t_s + self.hold_s
                self.counters["held"] = self.counters.get("held", 0) + 1
            self.policy.note_command_sent(node_id, payload)
        else:
            self.counters["commands_refused"] += 1

    def _note_intent_reason(self, node_id: str, payload: dict, view) -> None:
        """给每条**刚生成的**意图归类它的**生成原因**。三类互斥且完备。

        **为什么必须单独做这一层。** 账本已经按**结果**分了 `change`/`same_value`/`unknown`/`stale`，
        但"这条意图为什么会被生成"是另一个问题——而**只有在生成侧才能把它消掉**
        （轨 C 的全部意义在此）。三类：

        | 类别 | 判据（只用中心**真的看得见**的东西） | 它对应哪一种浪费 |
        |---|---|---|
        | `unknown_state` | 中心**从未**收到过这台节点的回执（`view.report_at` 里没有它） | 无证据动作 |
        | `target_change` | 这次的目标与**上一次为该节点生成的目标**不同 | 观测驱动的改值 |
        | `resend` | 目标与上一次相同（含"上一次是别的字段、这次换了字段"） | 追一个没被确认的目标 |

        **判据故意全部取自 `CenterView`**，不读环境真值、不读节点内部状态——否则这个分类本身就
        成了只有上帝视角才能算的量，不能用来评估一个**Host 侧**准入层能做到什么。

        **限定**：`resend` 里同时混着两种东西——"上一次还没被回执确认"（合理重发）与
        "回执早已确认、节点却又报告了旧值"（被忽视后的重发）。本方法**不区分这两者**，
        因为区分它们需要一个尚未实现的判据（要按字段比世代，而单字段策略根本没有成对世代）。
        """
        known = view.report_at.get(node_id) is not None
        target = tuple(sorted(payload.items()))
        prev = self._target_of.get(node_id)
        if not known:
            reason = "unknown_state"
        elif prev is not None and target != prev:
            reason = "target_change"
        else:
            reason = "resend"
        # **目标只按"意图内容"比较，不按世代号**：世代号是策略自己的记账，
        # 同一条逻辑命令的重发本来就会共享世代号，把世代号算进去会把"重发"误判成"改值"。
        self._target_of[node_id] = target
        self._intent_reason_counts["generated"][reason] += 1
        self._last_reason[node_id] = reason

    def intent_reasons(self) -> dict:
        """生成原因分类的结果，附**成本**与闭合恒等式。

        `generated[reason] = sent[reason] + refused[reason]`——被拒的那些意图**没有** `sent` 侧的计数，
        因此这里把 `refused` 按差额算出，并在测试里断言两侧闭合。
        """
        gen, sent = self._intent_reason_counts["generated"], self._intent_reason_counts["sent"]
        refused = {k: gen[k] - sent[k] for k in gen}
        return {"generated": dict(gen), "sent": dict(sent), "refused": refused,
                "total_generated": sum(gen.values()),
                "note": "生成原因只有三类：无回执（unknown_state）/目标变了（target_change）/重发（resend）。"
                        "`refused` 是按差额算的，因为拿不到下行机会的那些意图不会进 `sent` 侧。"}

    def intent_ledger(self) -> dict:
        """**意图准入账本**：一条 planner 意图从产生到落地（或没落地）的完整分账。

        分**生成端**与**到达端**两侧记，因为两侧的失效原因完全不同，混在一起就答不上
        「多余的控制流量是什么」：

        | 侧 | 类别 | 含义 |
        |---|---|---|
        | 生成端 | `refused` | **`ControlPlane.center_send` 因回传路径当时不可用而拒绝**（`path_available(hour, path)` 为假，`_send_command` 里配对的 `else` 分支）。**不是**"下行机会额度用尽"——那是别的东西，原写法是错的 |
        | 生成端 | `sent` | 真的发出去了 |
        | 到达端 | `landed` | 到了节点并被接受 |
        | 到达端 | `lost` | 发出去了但没到（链路丢） |
        | 到达端 | `dedup` | 同一条逻辑身份已经生效过 → 拒 |
        | 到达端 | `fenced` | 版本比节点已生效的更旧 → 拒 |
        | 到达端 | `stale_gen` | **整代**比节点已生效的更旧 → 拒（只有原子层会有） |

        落地的那些再按**值域**分：`change`（真的改了配置）/ `same_value`（值域空操作）/
        `speculative`（中心当时没有这台设备的电量读数——**这是生成端的无证据标记**，
        与它最终改了还是没改无关，所以与前两类**正交**，不是互斥的一类）。

        **恒等式**（两侧各自闭合）：`generated = refused + sent`；
        `sent = landed + lost + dedup + fenced + stale_gen`；`landed = change + same_value`。
        """
        c, pl = self.counters, self.plane
        sent = c["commands_sent"]
        landed = c["commands_delivered"]
        dedup, fenced = c["deduplicated"], c["fenced"]
        stale = c.get("stale_generation_dropped", 0)
        expired = getattr(pl, "downlink_expired", 0)
        queued = sum(len(v) for v in getattr(pl, "queued", {}).values())
        # **`lost` 是算出来的，不是一个自增计数。** 原先 `counters["commands_lost"]`
        # 被初始化成 0、**从来没有被增加过**——一列死列（"看起来有值、永远不动"是本项目
        # 反复抓过的那一类）。真正的去向分散在 `plane` 上：过期、滞留队列、上行/回传丢。
        lost = sent - landed - dedup - fenced - stale - expired - queued
        return {
            "generated": sent + c["commands_refused"],
            "refused": c["commands_refused"],
            "sent": sent,
            "landed": landed,
            "lost": lost,
            "expired": expired,
            "queued_left": queued,
            "dedup": dedup, "fenced": fenced, "stale_gen": stale,
            "rejected": dedup + fenced + stale,
            "change": c["writes_changed"],
            "same_value": c["writes_same_value"],
            "speculative": c["writes_speculative"],
        }

    def _apply_delivery(self, delivery, t_s: int) -> None:
        """命令真的到了节点。到这一步才算生效——之前都只是意图。

        **执行层在这里。** 报文的契约字段（`logical` 稳定身份、`version` 单调版本）决定远端能否
        认出"这是同一条逻辑命令的重发"以及"这比我已经生效的更旧"。两个字段都缺席时，一条迟到很久
        的命令会照常生效，把更新的配置覆盖回去——**这是方案属性，不是实现细节**，所以由臂来控制
        发不发这两个字段，而不是由中心策略控制。
        """
        node = self.nodes.get(delivery.node_id)
        if node is None or not node.alive:
            return
        payload = getattr(delivery.message, "payload", None) or {}
        if payload.get("speculative"):
            # 中心**没有这台设备的电量读数**就下了发——保守，但没有任何证据支持"状态需要改变"。
            self.counters["writes_speculative"] += 1
        logical = payload.get("logical")
        version = payload.get("version")

        if logical is not None and logical in node.applied_logicals:
            self.counters["deduplicated"] += 1
            return
        if version is not None and version < node.applied_version:
            self.counters["fenced"] += 1
            return
        if logical is not None:
            node.applied_logicals.add(logical)
        if version is not None:
            node.applied_version = version

        op = payload.get("op")
        gen = payload.get("generation")
        if self.atomic_generation and gen is not None:
            # 按世代缓冲：**这一代意图写的字段全部到齐**才一起生效；更新的世代一旦生效，
            # 更旧的整个丢弃。
            if node.config_generation is not None and int(gen) < node.config_generation:
                self.counters["stale_generation_dropped"] = \
                    self.counters.get("stale_generation_dropped", 0) + 1
                return
            slot = node.pending_fields.setdefault(int(gen), {})
            slot[op] = payload
            # **世代由"这次决策意图写的字段集合"定义，不是由"必须两个字段"定义。**
            # 只改上报周期的决策就是一个只有一个字段的完整世代，它到齐就该生效；把"到齐"
            # 写死成两个字段，会让单字段策略在下发后永远悬着、一条配置都落不了地。
            want = set(payload.get("fields") or [op])
            if want <= set(slot):
                for f in sorted(want):
                    self._apply_field(node, slot[f], gen)
                    if self.trace:
                        self.trace_events.append(
                            (t_s, node.node_id, "applied", f,
                             slot[f].get("period_s", slot[f].get("interval_s")),
                             slot[f].get("logical")))
                node.config_generation = int(gen)
                node.pending_fields = {k: v for k, v in node.pending_fields.items()
                                       if k > int(gen)}
                self.counters["commands_delivered"] += len(want)
            return
        if self._apply_field(node, payload, gen):
            self.counters["commands_delivered"] += 1
            if self.trace:
                self.trace_events.append(
                    (t_s, node.node_id, "applied", payload.get("op"),
                     payload.get("period_s", payload.get("interval_s")),
                     payload.get("logical")))

    def _note_write(self, want, current) -> None:
        """**动作准入计数**：这次写入到底改变了什么。

        `writes_same_value` 是"值域空操作"——命令到达、被接受、被计入 `commands_delivered`，
        但节点本来就在跑这个值。**它在计数上与一次真正的重配完全一样**，只有把值拿出来比才分得开。
        """
        if want == current:
            self.counters["writes_same_value"] += 1
        else:
            self.counters["writes_changed"] += 1

    def _apply_field(self, node, payload: dict, gen) -> bool:
        """把**单个**配置字段写进节点。

        **逐字段写入就是契约层的行为**（谁先到谁先生效，于是可能跑在跨代混配上）；整代生效
        由调用方保证。两条路径共用这一个写入点，免得"改了行为"和"改了生效时机"各自漂移。
        """
        op = payload.get("op")
        if op == OP_SET_REPORT_PERIOD:
            want = max(60, int(payload["period_s"]))
            self._note_write(want, node.report_period_s)
            node.report_period_s = want
            node.field_generation["period"] = gen
            return True
        if op == OP_SET_SAMPLING_INTERVAL:
            # **这一条会改变电量轨迹**：采样间隔是密集观测的主要能耗来源（v1.1 §8 的
            # "动作驱动的电量演化"）。把它调密，遮荫站点会耗尽电量而永久失去服务。
            want = max(60, int(payload["interval_s"]))
            self._note_write(want, node.sample_interval_s)
            node.sample_interval_s = want
            node.field_generation["interval"] = gen
            return True
        return False

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

    def intent_mismatch_s(self, hours: int) -> int:
        """节点实际周期与中心**最新意图**不一致的 tick 数（秒）。

        度量的是"中心自己的意图有没有达成"，不是"配置对不对"——v1.1 §9 只对有明确外部配置要求的
        区间算错配时长，这里的意图是中心自己选的优化值，因此**不得**把它当成正确性错误，只能当代价。
        """
        total = 0
        latest: dict[str, int] = {}
        by_t: dict[int, list[tuple[str, int]]] = {}
        for t_s, key, period in self.intent_log:
            by_t.setdefault(t_s, []).append((key, period))
        for t_s in range(0, hours * 3600, TICK_S):
            for nid, period in by_t.get(t_s, ()):
                latest[nid] = period
            for key, period in latest.items():
                nid, _, op = key.partition(":")
                node = self.nodes.get(nid)
                if node is None or not node.alive:
                    continue
                actual = (node.report_period_s if op == OP_SET_REPORT_PERIOD
                          else node.sample_interval_s)
                if actual != period:
                    total += TICK_S
        return total

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
