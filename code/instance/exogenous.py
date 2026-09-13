"""E1 — 外生过程与业务义务。

Task Contract v1.1 §4 的三分对象在这里实现：

    X(t)  环境真值        只供模拟器与评分器访问
    D     业务义务        由固定外部规则从 X(t) 生成，**在运行之前就定好**
    O_i(t) 各执行位置的可见历史   在 `network.py` 里，任何策略都不能越过它

**本模块最重要的一条性质：D 在运行前生成，且不读任何策略状态。** 这就是验收项"改变策略不改变
需求分母"的实现方式——分母不是算出来的，是先定下来的。

证据层标注沿用 v1.1 §2：E 来源事实 / A 研究选择 / M 本项目输出。凡 A 层参数都必须能被单独改掉。

覆盖到的验收要求：
  * 失电不补造样本 —— 义务照常存在，但节点无电时不产生样本（`node.py`），义务仍留在分母里
  * 旧数据不冒充事件观测 —— 事件义务带自己的采集时间窗，窗外的样本不匹配（`obligation.matches`）
"""

from __future__ import annotations

import csv
import math

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

TICK_S = 60

# ---------------------------------------------------------------- 业务义务

#: 义务的两类。routine 来自周期要求，event 来自外生事件触发。
KIND_ROUTINE = "routine"
KIND_EVENT = "event"


@dataclass(frozen=True)
class Obligation:
    """一条业务义务：某个对象、某个测项、在某段时间里应有一份有效测值到达。

    `release_at` 是义务存在的起始时刻（评分曲线从这里起算）；`window` 是**允许的采集时间范围**；
    `grace_s` 是采集之后允许的送达宽限，**它是研究容忍时延，不是 SLA**（v1.1 §9）。

    采样时刻落在 window 之外、或采集时刻早于 release 的样本**不能**满足本条义务——这正是
    "旧缓存不能冒充新采集"与"旧数据不冒充事件观测"两条验收的落点。
    """

    oid: str
    node_id: str
    measurand: str
    kind: str
    release_at: int
    window: tuple[int, int]
    grace_s: int
    #: 采集匹配容差（s）。公开片段给的是**实时钟上的时刻**（如 00:17:32 = 1052 s），不在运行的
    #: 整数 tick 网格上；仿真在网格上走，因此必须显式声明一个匹配容差，而不是偷偷把时刻改掉。
    #: v1.1 §11 要求 manifest 含"采集匹配容差"，就是这一项。默认 0 表示窗口本身就是判据。
    tolerance_s: int = 0

    @property
    def deadline(self) -> int:
        """从 release 起算的观察截止。超过它未送达，按 v1.1 §9 标右删失。"""
        return self.window[1] + self.grace_s

    def matches(self, sample) -> bool:
        """该样本能否计入本条义务。只用**原始采集时间**判断，不看方法名称或声明。

        容差是**双向**的，且不改变窗口本身：`tolerance_s` 只用于吸收"实时钟 → tick 网格"的
        量化误差，不用于放宽业务判据。
        """
        if sample.node_id != self.node_id or sample.measurand != self.measurand:
            return False
        lo = self.window[0] - self.tolerance_s
        hi = self.window[1] + self.tolerance_s
        return lo <= sample.taken_at <= hi


# ---------------------------------------------------------------- 公开事件片段（E）

#: Wang 等 2022，*Frontiers in Earth Science* 10:899509，Table 3，EI01（带雨量计的主节点／网关），
#: 2020-01-06。**这是已发表的触发／传输记录片段，不是完整连续 trace**（v1.1 §3）。
#: 每组的第一个时刻是触发时刻；后两条是同一组的第 2、3 次传输时刻。
#: 原表还有 1–18 s 的时序偏差，**保留原值，不改成理想时钟**。
WANG_TABLE3_BURSTS: tuple[tuple[int, ...], ...] = (
    (17 * 60 + 32, 22 * 60 + 33, 27 * 60 + 34),
    (49 * 60 + 11, 54 * 60 + 13, 59 * 60 + 13),
    (64 * 60 + 14, 69 * 60 + 15, 74 * 60 + 16),
    (107 * 60 + 27, 112 * 60 + 27, 117 * 60 + 45),
    (496 * 60 + 24, 501 * 60 + 28, 506 * 60 + 26),
    (511 * 60 + 27, 516 * 60 + 28, 521 * 60 + 14),
    (585 * 60 + 20, 590 * 60 + 21, 595 * 60 + 23),
)

#: 与上表逐条对应的雨量读数（mm），来自同一 Table 3。第 7 组第 2 条是 3.6，其余多为 0.2／0.0。
WANG_TABLE3_RAINFALL: tuple[tuple[float, ...], ...] = (
    (0.2, 0.0, 0.2),
    (0.2, 0.0, 0.2),
    (0.2, 0.2, 0.0),
    (0.2, 0.0, 0.2),
    (0.2, 0.0, 0.2),
    (0.2, 0.0, 0.2),
    (0.2, 3.6, 0.0),
)

#: 触发阈值（E：Table 3 记作 0.2，单位 mm）。**完整累计／增量窗口未闭合**（v1.1 §11），
#: 因此本文件只用它做"公开片段回放"，不从任意插值序列自造高频触发。
WANG_THRESHOLD_MM = 0.2

#: 名义加密间隔（E：Table 3 实测 286–318 s，名义 300 s）。
EVENT_SPACING_S = 300

#: 每次触发的观测名额数（E：Table 3 的 `source_N` 列恒为 3）。
EVENT_SLOTS = 3


def wang_burst_obligations(node_id: str = "EI01", measurand: str = "rainfall",
                           day_offset_s: int = 36 * 3600,
                           grace_s: int = 600,
                           tolerance_s: int = TICK_S // 2) -> list[Obligation]:
    """**公开片段校验实例**：用 Table 3 的**实际时刻**建义务。

    **它只用于校验事件解析，不用于仿真匹配。** 理由是一个实测出来的量：Table 3 的实际间隔是
    286–318 s，不是名义 300 s。若拿节点侧固定 300 s 的规则实例去匹配这张实际时刻表，漂移会累积，
    第 7 组的第 2 个名额就会掉出容差（实测 20/21）。v1.1 §5.2 要求把这两件事分开：

      * **公开片段校验** —— 用片段核对事件解析（组数、名额数、间隔量级、时序偏差）；
      * **规则实例** —— 从给定触发生成 `t, t+300, t+600` 的名义义务，用于仿真，并显式声明采样容差。

    传输时刻**只能当采集义务的名义时刻**——它既不是中心接收时刻，也不是独立的采样真值（v1.1 §5.2）。
    """
    out: list[Obligation] = []
    for b, times in enumerate(WANG_TABLE3_BURSTS):
        for k, t in enumerate(times):
            rel = day_offset_s + t
            out.append(Obligation(
                oid=f"{node_id}:event:b{b + 1}.{k + 1}",
                node_id=node_id, measurand=measurand, kind=KIND_EVENT,
                release_at=rel, window=(rel, rel), grace_s=grace_s,
                tolerance_s=tolerance_s))
    return out


def rule_burst_obligations(trigger_at: int, burst_index: int, node_id: str = "EI01",
                           measurand: str = "rainfall", n: int = EVENT_SLOTS,
                           spacing_s: int = EVENT_SPACING_S, grace_s: int = 600,
                           tolerance_s: int = 0) -> list[Obligation]:
    """规则实例：一次触发 → `n` 个观测名额，首个与触发同时，其后每 `spacing_s` 一个。

    这是 **A 层理想化**：名义间隔，不是原站逐秒复现。`grace_s` 同为研究容忍时延。
    每次名额的采集窗是它自己的时点，因此**同一个样本不能占满三个名额**——这由
    `matches` 的逐条窗口自然保证。
    """
    out = []
    for k in range(n):
        rel = trigger_at + k * spacing_s
        out.append(Obligation(
            oid=f"{node_id}:event:r{burst_index}.{k + 1}",
            node_id=node_id, measurand=measurand, kind=KIND_EVENT,
            release_at=rel, window=(rel, rel), grace_s=grace_s,
            tolerance_s=tolerance_s))
    return out


def rule_obligations_for_truth(truth, node_id_of=None, **kw) -> list[Obligation]:
    """仿真用：**从环境真值的触发**构造规则义务，与节点侧的规则采样严格对齐。

    触发已经在 `wang_fragment_truth(..., snap=True)` 里吸附到 tick 网格，因此这里生成的时点
    `t, t+300, t+600` 与节点按 `event_interval_s` 采出的时点**逐位相同**，`tolerance_s` 可以为 0。
    这是"规则实例"，明确标为 A 层理想化，不宣称原站逐秒复现（v1.1 §5.2）。
    """
    out: list[Obligation] = []
    for i, (t_s, nid) in enumerate(truth.triggers):
        out.extend(rule_burst_obligations(t_s, i + 1,
                                          node_id=node_id_of(t_s, nid) if node_id_of else nid,
                                          **kw))
    return out


# ---------------------------------------------------------------- 周期义务

#: 常态定时回传周期（E：S1 §5.2 贵州水城系统 1 h，连续运行 9 个月）。
ROUTINE_PERIOD_S = 3600


def routine_obligations(node_ids, hours: int, measurand: str = "displacement",
                        period_s: int = ROUTINE_PERIOD_S,
                        window_s: int | None = None,
                        grace_s: int | None = None) -> list[Obligation]:
    """周期义务：每个（对象, 测项）在每个周期窗口内应有一份有效测值到达中心。

    `period_s` 是**来源支持的配置**（1 h）。它**不规定**节点必须采样 1 h——采样间隔是设备
    参数，与上报周期是两个独立字段（E：重庆 `0045`／`0042`）。`window_s` 默认覆盖整个周期。

    **义务与策略无关**：策略把上报周期改长不能减少应服务的义务（v1.1 §5.1）。
    """
    window_s = period_s if window_s is None else window_s
    grace_s = period_s if grace_s is None else grace_s
    out: list[Obligation] = []
    for node_id in sorted(node_ids):
        for i in range(int(hours * 3600 // period_s)):
            rel = i * period_s
            out.append(Obligation(
                oid=f"{node_id}:routine:{i:05d}",
                node_id=node_id, measurand=measurand, kind=KIND_ROUTINE,
                release_at=rel, window=(rel, rel + window_s), grace_s=grace_s))
    return out


def routine_obligations_by_node(measurands: dict[str, str], hours: int,
                                period_s: int = ROUTINE_PERIOD_S,
                                window_s: int | None = None,
                                grace_s: int | None = None) -> list[Obligation]:
    """按**每个节点自己的测项**建周期义务。

    存在的理由是一个实测出来的错误：`routine_obligations(node_ids, ...)` 给一份节点名单配**同一个**
    测项，于是只有雨量的网关也被发了位移义务，而它永远不会采位移——评分器把网关整段时间记成
    "无观测"，12 小时全段（43200 s）。**一个实体不该被要求提供它没有的测项。**
    """
    out: list[Obligation] = []
    for node_id, measurand in sorted(measurands.items()):
        out.extend(routine_obligations((node_id,), hours, measurand=measurand,
                                       period_s=period_s, window_s=window_s,
                                       grace_s=grace_s))
    return out


# ---------------------------------------------------------------- 环境真值

@dataclass
class EnvironmentTruth:
    """`X(t)` 的载体。**只允许模拟器与评分器读取**，不得进入任何策略的可见历史。

    **这里没有任何预先生成的存活序列。** v1.1 §8 要求"方法共用初始电池、外生天气／采能和设备
    成本，电量与死亡时刻可以因动作不同而变化，不能强行共用预先生成的存活序列"。因此本结构只
    提供**外生**量——采能与温度——电池状态由 `node.Node` 自己积分，两个跑不同动作的方法会得到
    不同的电量轨迹与不同的死亡时刻。
    """

    hours: int
    node_ids: tuple[str, ...]
    #: 降雨增量序列：t -> mm。公开片段实例取 Table 3 读数；规则实例由种子生成并标为合成。
    rainfall: dict[int, float] = field(default_factory=dict)
    #: 位移读数：node_id -> {t: mm}。周期实例用；取值本身不影响投递类指标，但 v1.1 §4 要求
    #: `Sample` 必须带读数与单位，因此这里必须给出一个可追溯的来源而不是随手填 0。
    displacement: dict[str, dict[int, float]] = field(default_factory=dict)
    #: 触发时刻（雨量阈值被越过）。
    triggers: list[tuple[int, str]] = field(default_factory=list)
    #: 外生采能：node_id -> {t: Wh 本 tick 获得}。与任何动作无关。
    harvest_wh: dict[str, dict[int, float]] = field(default_factory=dict)
    #: 外生温度：node_id -> {t: °C}。影响电池可用容量与能否充电，不由动作改变。
    temp_c: dict[str, dict[int, float]] = field(default_factory=dict)
    #: 吸附前的原始触发时刻（实时钟）。保留它，是为了让"我们把时刻改了多少"可被核查。
    trigger_originals: list[tuple[int, str]] = field(default_factory=list)
    #: 本次吸附的最大绝对误差（s）。上界是 tick/2，义务的 tolerance_s 取同一值即可吸收。
    snap_error_max: int = 0

    def rainfall_at(self, t_s: int) -> float:
        return self.rainfall.get(t_s, 0.0)

    def reading_at(self, node_id: str, measurand: str, t_s: int) -> float:
        """某节点某测项在 t 的读数。**这是环境真值**，只有模拟器与评分器可以读。"""
        if measurand == "rainfall":
            return self.rainfall.get(t_s, 0.0)
        return self.displacement.get(node_id, {}).get(t_s, 0.0)

    def harvest_at(self, node_id: str, t_s: int) -> float:
        return self.harvest_wh.get(node_id, {}).get(t_s, 0.0)

    def temp_at(self, node_id: str, t_s: int) -> float | None:
        series = self.temp_c.get(node_id)
        return None if series is None else series.get(t_s)


def constant_harvest(node_ids, hours: int, wh_per_hour: float,
                     temp_c: float | None = None) -> tuple[dict, dict]:
    """最简外生过程：恒定采能（A 层）。

    它存在的意义是让最小闭环先跑通并手工可核算。**真实实例必须换成有出处的采能/温度过程**，
    并在 manifest 里标出来源层级。`temp_c=None` 表示不建模温度闸门，此时电池按标称容量计。
    """
    harvest, temp = {}, {}
    for node_id in node_ids:
        harvest[node_id] = {t: wh_per_hour / 60.0 for t in range(0, hours * 3600, TICK_S)}
        if temp_c is not None:
            temp[node_id] = {t: temp_c for t in range(0, hours * 3600, TICK_S)}
    return harvest, temp


def snap_to_grid(t_s: int, tick_s: int = TICK_S) -> tuple[int, int]:
    """把实时钟上的时刻吸附到运行的整数 tick 网格上，返回 `(吸附后, 绝对误差)`。

    Table 3 给的是实时钟时刻（`00:17:32` = 1052 s），而仿真在 60 s 网格上走。**不把时刻偷偷改掉**：
    原始值留在 `EnvironmentTruth.trigger_originals` 里，误差单独报出来，并在 manifest 声明匹配容差。
    误差上界是 `tick_s // 2`，因此义务的 `tolerance_s` 取同一值即可完全吸收，且相邻事件相隔 300 s
    远大于 `2 x tolerance`，不会串位。
    """
    snapped = (t_s + tick_s // 2) // tick_s * tick_s
    return snapped, abs(snapped - t_s)


def hetero_harvest(node_ids, hours: int, seed: int, low_frac: float = 0.4,
                   low_wh_per_hour: float = 0.005, high_wh_per_hour: float = 0.05,
                   temp_c: float | None = 10.0) -> tuple[dict, dict]:
    """**异质**采能（A 层）：一部分站点被地形或积雪遮住，采能只有其余站点的十分之一。

    为什么要异质：如果每个节点的机会预算都很宽裕，那么"把所有节点都加密"就是可行解，
    固定配置自然够用——上一轮实测正是这个结果（`fixed900` 与 `aoi` 逐位相同）。
    **要让"给谁加密"成为真正的选择，预算必须先成为约束，而且节点之间的预算必须不同。**
    v1.1 §8 已经写了"各电池的能量不可任意互相转移"，这里落实的是它的前提：各站采能不同。
    """
    harvest, temp = {}, {}
    for node_id in node_ids:
        low = stable_uniform(seed, "shade", node_id) < low_frac
        wh = low_wh_per_hour if low else high_wh_per_hour
        harvest[node_id] = {t: wh / 60.0 for t in range(0, hours * 3600, TICK_S)}
        if temp_c is not None:
            temp[node_id] = {t: temp_c for t in range(0, hours * 3600, TICK_S)}
    return harvest, temp


#: 日出钟点（A 层研究取值）。日照窗为 `[SUNRISE_H, SUNRISE_H + daylight_h]`。
SUNRISE_H = 6.0


def solar_harvest(node_ids, hours: int, seed: int, *,
                  day_start_hour: float = 6.0, peak_wh_per_hour: float = 0.06,
                  daylight_h: float = 12.0, cloud_p: float = 0.35,
                  cloud_atten: float = 0.25, snow_frac: float = 0.0,
                  snow_start_h: float = 8.0, shade_frac: float = 0.0,
                  shade_atten: float = 0.1, temp_c: float | None = 10.0) -> tuple[dict, dict]:
    """**合成**的日照采能时间过程 `H_i(t)`（A 层研究取值，**不来自任何实测站点**）。

    为什么必须从"两个独立标量"换成时间过程：`capacity_wh × wh_per_hour` 这两个标量把能量问题
    压成了一个**总量**问题——只要总量够就能跑完，于是"什么时候有电"完全不进入模型。而现场的真实
    困难恰恰是时间的：**日照有昼夜节律，夜里没有输入，电池必须在白天把夜里的份额存下来**；
    云遮是短时的、随机的；积雪是**持续一段时间的零输入**。这三件事都只能由 `H_i(t)` 表达。

    **必须标明的限定**：本函数是**合成曲线**，形状（正弦日照窗 + 逐小时云遮衰减 + 积雪归零）是
    A 层研究选择，参数是可扫描的旋钮而非拟合值。用它做出来的结论**只能读作"在这个形状下如何"**，
    不能读作"实际站点如何"。任何引用处必须同时引用这一句。

    参数：`day_start_hour` 是运行起点对应的**绝对钟点**（决定 12 h 窗口落在白天还是夜里）；
    `cloud_p` 是逐节点逐小时的云遮概率，`cloud_atten` 是云遮时的产能比例；`snow_frac` 比例的
    站点从 `snow_start_h` 起被积雪完全覆盖；`shade_frac` 比例的站点被地形长期遮蔽。
    """
    harvest, temp = {}, {}
    for node_id in node_ids:
        shaded = stable_uniform(seed, "solar_shade", node_id) < shade_frac
        snowy = stable_uniform(seed, "solar_snow", node_id) < snow_frac
        series: dict[int, float] = {}
        for t in range(0, hours * 3600, TICK_S):
            # **日出固定在钟面 06:00，运行窗在钟面上滑动。**
            # 第一版把"正午"写成随 `day_start_hour` 平移的量，于是 `hod - noon` 里两项同步
            # 平移、差值抵消，`day_start_hour` 成了**空参数**——起 0/6/12/18 点四条曲线逐位相同
            # （实测确认）。参数必须证明它会动，这是本项目对每一列的要求，对参数同样适用。
            hod = (day_start_hour + t / 3600.0) % 24.0
            rel = (hod - SUNRISE_H) % 24.0          # 距日出的时长
            if rel <= daylight_h:
                sun = max(0.0, math.sin(math.pi * rel / daylight_h))
            else:
                sun = 0.0
            wh = peak_wh_per_hour * sun
            if wh > 0.0 and stable_uniform(seed, "cloud", node_id, t) < cloud_p:
                wh *= cloud_atten
            if shaded:
                wh *= shade_atten
            if snowy and t >= int(snow_start_h * 3600):
                wh = 0.0
            series[t] = wh / 60.0
        harvest[node_id] = series
        if temp_c is not None:
            temp[node_id] = {t: temp_c for t in range(0, hours * 3600, TICK_S)}
    return harvest, temp


#: NASA POWER 逐小时辐照与气温（部署点 30.33 N / 94.78 E）。
#: 来源、许可、哈希与**必须一起引用的读法**见
#: `data/downloads/nasa_power_irradiance/SOURCE.md`。`data/` 不入库，因此缺文件时要报出重取命令。
IRRADIANCE_CSV = _os.path.normpath(_os.path.join(
    _CODE, "..", "data", "downloads", "nasa_power_irradiance",
    "power_hourly_2023_30.33N_94.78E.csv"))

_FETCH_CMD = ('curl "https://power.larc.nasa.gov/api/temporal/hourly/point'
              '?parameters=ALLSKY_SFC_SW_DWN,T2M&community=RE'
              '&longitude=94.78&latitude=30.33&start=20230101&end=20231231&format=JSON"')

_IRRADIANCE_CACHE: tuple[list[float], list[float]] | None = None


def _load_irradiance() -> tuple[list[float], list[float]]:
    """读一次、缓存。**缺文件时报出重取命令**，而不是让调用方看到一个含糊的 KeyError。"""
    global _IRRADIANCE_CACHE
    if _IRRADIANCE_CACHE is None:
        if not _os.path.exists(IRRADIANCE_CSV):
            raise FileNotFoundError(
                f"缺少来源数据 {IRRADIANCE_CSV}（`data/` 不入库）。重取：\n  {_FETCH_CMD}\n"
                f"然后见 data/downloads/nasa_power_irradiance/SOURCE.md 的派生 CSV 步骤。")
        irr, tmp = [], []
        with open(IRRADIANCE_CSV, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                irr.append(float(row["irradiance_wh_m2"]))
                tmp.append(float(row["temp_c"]))
        _IRRADIANCE_CACHE = (irr, tmp)
    return _IRRADIANCE_CACHE


def irradiance_windows(hours: int, n: int = 0, stride_h: int = 1) -> list[int]:
    """可用的**真实**起点集合（小时索引）：把 8760 小时切成 `hours` 长的窗口，取每隔
    `stride_h` 小时一个起点。`n > 0` 时在整年上**等间隔取 `n` 个**，用于扫"不同季节/天气时段"。

    这是"第二来源场景"的落点：每一个起点都是一段**真实发生过的**天气，不是一个随机种子。
    """
    irr, _ = _load_irradiance()
    total = len(irr)
    starts = list(range(0, total, max(1, stride_h)))
    if n > 0:
        step = max(1, total // n)
        starts = list(range(0, total, step))[:n]
    return starts


def irradiance_harvest(node_ids, hours: int, seed: int, *, start_hour: int = 0,
                       peak_wh_per_hour: float = 0.01, shade_frac: float = 0.0,
                       shade_atten: float = 0.1, snow_frac: float = 0.0,
                       snow_after_h: int = 0, source_temp: bool = True,
                       temp_c: float | None = None) -> tuple[dict, dict]:
    """**来源派生**的采能时间过程：形状取自 NASA POWER 逐小时辐照（E），量级是 A 层换算。

    与 `solar_harvest` 的区别是**因果来源不同**，不是精度不同：

    | | 形状来自 | 能证明什么 |
    |---|---|---|
    | `solar_harvest` | 我写的一个正弦 + 云遮概率 | "在这些**假设的形状**下成立" |
    | `irradiance_harvest` | **2023 年该点位的真实逐小时辐照** | "在这些**真实发生过的天气时段**下成立" |

    **必须一起引用的两步读法（都不是来源事实）**：

    1. **量级换算是 A 层选择。** 来源给的是辐照 Wh/m²，不是这台设备的采能。本函数按
       `wh = peak_wh_per_hour × I(t) / I_max` 归一化后缩放——**形状是来源的，量级是我定的**
       （组件面积 × 效率 × 站点降额被这一个参数吸收）。所以 `peak_wh_per_hour` 是一个
       可扫描的旋钮，不是拟合值。
    2. **时区按 UTC 读**（POWER 的 header 未返回 `time-standard`）。若实际为 +8，日照窗整体平移 8 h。

    温度默认取**来源自带的 `T2M`**（同一张表、同一时刻），于是低温闸门作用在真实气温上，
    而不是一个常数。这一项是比合成曲线**实质更强**的地方（该站点全年最低 −20.49 °C）。

    逐节点降额（`shade_frac` / `snow_frac` / `snow_after_h`）仍然是 A 层叠加，用 `stable_uniform`
    按 (种子, 节点) 抽，因此可复现。
    """
    irr, tmp_series = _load_irradiance()
    total = len(irr)
    imax = max(irr) or 1.0
    n_ticks = hours * 60
    harvest, temp = {}, {}
    for node_id in node_ids:
        shaded = stable_uniform(seed, "irr_shade", node_id) < shade_frac
        snowy = stable_uniform(seed, "irr_snow", node_id) < snow_frac
        series: dict[int, float] = {}
        temps: dict[int, float] = {}
        for tick in range(n_ticks):
            h_idx = (start_hour + tick // 60) % total
            wh_h = peak_wh_per_hour * (irr[h_idx] / imax)
            if shaded:
                wh_h *= shade_atten
            if snowy and (tick // 60) >= snow_after_h:
                wh_h = 0.0
            series[tick * TICK_S] = wh_h / 60.0
            if source_temp:
                temps[tick * TICK_S] = tmp_series[h_idx]
            elif temp_c is not None:
                temps[tick * TICK_S] = temp_c
        harvest[node_id] = series
        if source_temp or temp_c is not None:
            temp[node_id] = temps
    return harvest, temp


def autonomy_margin(harvest_wh: dict[int, float], hours: int, *,
                    capacity_wh: float, initial_wh: float, cost_per_hour: float,
                    hi: float = 64.0, iters: int = 50) -> float:
    """**autonomy margin**：这条采能轨迹还能被削减多少倍，才轮到每小时的义务服务不起。

    定义（手算可核）：`λ_min` = 最小的 `λ`，使得采能取 `λ · H(t)` 时**每一个小时**都还买得起
    该小时需要的采样能耗。返回 **`1 / λ_min`**：

    - `= 1`：**恰好够**，一点富余都没有；
    - `> 1`：有富余，值就是"采能可以掉到原来的几分之一还能撑住"（2 表示能掉一半）；
    - `< 1`：**原本就不够**，值表示还差多少；
    - `= 0`：无论放多大都不可行（例如头几个小时完全没有输入而初始电量又是 0）。

    **单调性方向容易搞反，这里写下来**：容量不受限时采能越多越可行，所以"最大可行 λ"是发散的、
    没有信息。有信息的是**可行 λ 的下确界**——它量的是"离不可行边界还有多远"。第一版按"最大可行
    λ"写，结果每一条都返回上界 8.0，是测试 [17] 抓到的。

    为什么用这个当横轴而不是绝对 Wh：绝对容量（或绝对采能）比较的是两个**标量**，换一个任务时长
    或换一档采样间隔就不可比；而 margin 是**相对这条工作负载、这条采能轨迹**的余量，**1 是天然
    分界**，不同任务、不同间隔下的读数可以放在同一张图上。这正是本项要求"横轴不用绝对 Wh"。

    **逐小时**而不是看总量，是这个定义的关键：总量够而某一个小时不够，仍然不可行——这正是
    日照曲线才暴露得出来的失败模式（白天充满、夜里耗光）。测试 [17] 用两条**总量逐位相同**、
    时序不同的轨迹把这一条钉住。

    二分求下确界：`feasible(λ)` 关于 `λ` 单调不减，所以二分是精确的，不是启发式。
    """
    per_hour = [sum(v for tt, v in harvest_wh.items() if tt // 3600 == h)
                for h in range(hours)]

    def feasible(lam: float) -> bool:
        soc = initial_wh
        for h in range(hours):
            soc = min(capacity_wh, soc + lam * per_hour[h])
            if soc < cost_per_hour:
                return False
            soc -= cost_per_hour
        return True

    if feasible(0.0):
        # 一点采能都不需要（初始电量自己就够跑完）：余量**无上界**。
        # 这不是"很大"，是"这条轨迹的采能与可行性无关"，必须如实报无穷而不是报一个由二分
        # 迭代次数决定的大数（第一版返回 1.76e16，那个数字只反映 `iters`，不反映任何物理量）。
        return float("inf")
    if not feasible(hi):
        return 0.0                     # 连放大 `hi` 倍都不行：真的不可行
    lo, hi_ = 0.0, hi                  # `lo` 不可行或恰好可行，`hi_` 可行
    for _ in range(iters):
        mid = (lo + hi_) / 2.0
        if feasible(mid):
            hi_ = mid
        else:
            lo = mid
    lam_min = hi_
    return float("inf") if lam_min <= 0.0 else 1.0 / lam_min


def wang_fragment_truth(day_offset_s: int = 36 * 3600, hours: int = 24,
                        node_ids: tuple[str, ...] = ("EI01",),
                        snap: bool = True) -> EnvironmentTruth:
    """公开片段的环境真值：把 Table 3 的读数与触发时刻放进时域。

    **只输入已发表的事件标记与读数**，不重构连续 `X(t)`（v1.1 §4、§11）。
    采能与温度不在此设定——公开片段没有给出它们；调用方必须显式提供并标注层级。

    `snap=True` 把触发与读数吸附到 tick 网格（见 `snap_to_grid`），并把原始时刻与最大吸附误差
    记进 `trigger_originals` / `snap_error_max`。
    """
    rain: dict[int, float] = {}
    trig: list[tuple[int, str]] = []
    originals: list[tuple[int, str]] = []
    err = 0
    for b, times in enumerate(WANG_TABLE3_BURSTS):
        for k, t in enumerate(times):
            raw = day_offset_s + t
            if snap:
                stamp, e = snap_to_grid(raw)
                err = max(err, e)
            else:
                stamp = raw
            rain[stamp] = WANG_TABLE3_RAINFALL[b][k]
        raw_trig = day_offset_s + times[0]
        originals.append((raw_trig, node_ids[0]))
        stamp = snap_to_grid(raw_trig)[0] if snap else raw_trig
        trig.append((stamp, node_ids[0]))
    trig.sort()
    return EnvironmentTruth(hours=hours, node_ids=node_ids, rainfall=rain, triggers=trig,
                            trigger_originals=originals, snap_error_max=err)


def synthetic_truth(hours: int, node_ids: tuple[str, ...], seed: int,
                    rain_prob: float = 0.010, trigger_mm: float = WANG_THRESHOLD_MM,
                    day_offset_s: int = 0) -> EnvironmentTruth:
    """**明确标为合成的**诊断过程（A 层）。

    v1.1 §5.2 禁止"由日雨量或任意插值序列自造高频阈值触发并称真实事件"。因此本函数产出的
    实例**必须**在 manifest 里标为合成诊断实例，不得命名为真实 trace benchmark。
    """
    rain, trig = {}, []
    for node_id in node_ids:
        for i in range(hours * 60):
            t = day_offset_s + i * TICK_S
            u = stable_uniform(seed, "rain", node_id, i)
            if u < rain_prob:
                # 触发值取阈值本身；这是合成过程，不是实测雨量。
                mm = round(trigger_mm, 2) if stable_uniform(seed, "rainmag", node_id, i) < 0.6 \
                    else round(3.0 * trigger_mm, 2)
                rain[t] = mm
                if mm >= trigger_mm:
                    trig.append((t, node_id))
    trig.sort()
    # 合成过程的时点本来就取在 tick 网格上，因此不需要吸附。
    return EnvironmentTruth(hours=hours, node_ids=node_ids, rainfall=rain, triggers=trig)


# ---------------------------------------------------------------- 义务集合

@dataclass
class ObligationSet:
    """运行之前就定好的业务义务全集 `D`。

    **分母的唯一来源。** 任何策略都不能增删它；`runner` 也不允许在运行中改写它。
    """

    obligations: list[Obligation]

    def __len__(self) -> int:
        return len(self.obligations)

    @property
    def by_kind(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for o in self.obligations:
            out[o.kind] = out.get(o.kind, 0) + 1
        return out

    def serviceable(self, link_ok) -> "ObligationSet":
        """`link_ok(oid, node_id, t_s) -> bool` 判定某时刻接入是否可用。

        返回**物理上至少有一次机会**的子集（v1.1 §3 的第二个分母）。主分母始终是全集；
        这个子集只用于单列，不能顶替主分母。
        """
        keep = []
        for o in self.obligations:
            if any(link_ok(o, o.node_id, t) for t in range(o.window[0], o.window[1] + 1, TICK_S)):
                keep.append(o)
        return ObligationSet(keep)


def displacement_series(node_ids, hours: int, seed: int,
                        drift_mm_per_day: float = 0.8) -> dict[str, dict[int, float]]:
    """**合成**的位移过程（A 层）：缓慢漂移 + 有界的逐时抖动。

    存在两个理由：一是 v1.1 §4 要求样本带读数；二是让"值驱动决策"这条路径在实例里**有对象**，
    即使本轮不用它。取值本身属于合成诊断过程，**不得**当作任何站点的实测形变。
    """
    out: dict[str, dict[int, float]] = {}
    for node_id in node_ids:
        series: dict[int, float] = {}
        for i in range(hours):
            t = i * 3600
            drift = drift_mm_per_day * i / 24.0
            jitter = (stable_uniform(seed, "disp", node_id, i) - 0.5) * 0.4
            series[t] = round(drift + jitter, 3)
        out[node_id] = series
    return out
