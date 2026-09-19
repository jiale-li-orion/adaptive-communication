"""部署：真实 SRTM 地形上的一个监测单元。
本模块引用的 `docs/…` 路径为作者本地过程文档，不随仓库发布。

v1.1 §3 要求把**规模**当轴、把**角色**按现场论文给、把"关键测点"的认定交给依据。本模块做三件事：

1. **站址取自真实地形**（SRTM1，1 角秒）。网关固定在既有研究选定的谷地汇聚点；坡面节点按固定
   几何偏置布点。**这是 A 层站址选择**，不是任何具体站点的实测布点。
2. **角色按 S1 给**：S1 的 EI01 是**带雨量计的主节点／网关**，EI02–EI05 是形变子节点。因此本
   模块把雨量计放在网关上，坡面节点为位移测项。**这与旧实现不同**——旧实现把雨量计放在一个叶
   节点上，那是把角色搬离了来源描述。
3. **可达性由 ITM 逐链路算出来**：每节点一条 ITM 损耗，`best_sf` 给出能否闭合。于是"哪些节点
   可达"是**外生事实**，不是参数；而"机会投给谁"才成为一个真实的选择。

ITM 逐链路计算约数秒，结果按 (tile, 坐标) 缓存到 `data/derived/link_budget.json`，
避免每次跑实例都重算。缓存只是加速，**不改变结果**。
"""

from __future__ import annotations

# --- module resolution -------------------------------------------------------
import json
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime",
                                                     "experiments", "analysis",
                                                     "monitoring"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
# -----------------------------------------------------------------------------

import math
from dataclasses import dataclass, field

# ---------------------------------------------------------------- 站址（A 层）

#: 网关：既有研究选定的谷地汇聚点（README §四）。高度取自 SRTM。
GATEWAY_LAT = 30.3300
GATEWAY_LON = 94.7800
GATEWAY_ELEV_M = 2317.0

#: 米/度换算。坡面布点用局部 ENU（东, 北）米坐标表示，比经纬度偏置好推理也好复现。
M_PER_DEG_LAT = 111_320.0

#: 两组坡面的几何布局：组中心距网关的 (东, 北) 偏移（米），以及 3x3 栅格去掉中心的间距。
#:
#: **这是 A 层几何**，取值理由：一个坡面监测单元覆盖一个坡面，栅格跨约 440 m 合理；两组分别放在
#: 近坡与远坡，是为了让**可达性差异由真实地形产生**而不是由参数设定。站址不是按无线条件挑的
#: ——现实中监测点按地质条件布，链路好坏是结果，也正是"节点静默掉线"这件事的来源。
#: 两组坡面的选取规则：**近坡取正北 1.5 km（8/8 通视），远坡取东南 2.5 km（8 位点中 5 个通视）**。
#:
#: 为什么是这个而不是别的：一个监测单元里既要有一个**完全可服务**的坡面（基准条件），也要有一个
#: **部分被地形遮挡**的坡面——只有后者才让"哪个节点、以及它到底可不可达"成为真实的选择。
#: 全通视（如正东 2.0 km，8/8）与全遮挡（如东南 2.5 km 偏北，0/8）都不含这个选择。
#:
#: **一处必须记录的物理事实（实测）**：这些链路里有若干落在**绕射边缘**上——把节点坐标改动
#: 1 米（例如把经纬度四舍五入到 5 位小数），损耗会摆动 **65–70 dB**，可达性判定直接翻转。
#: 1 米的量级远小于真实部署里天线与测点的定位不确定度，因此**这样的位点其"可达性"不是地形事实，
#: 而是坐标巧合**。`build_deployment` 因此做两件事：坐标**不做四舍五入**，并对每个位点做
#: **±`STABILITY_M` 米的扰动检验**，把判定会翻转的位点标为 `marginal` 并默认排除。
#:
#: **选择不是从一次扫描里挑出来的**：方位 × 距离的完整扫描表存放在
#: `docs/s7-method/instance-v1/02-instance-manifest.md`，任何一组几何都可以按同一张表换。
#: 扫描结果同时给出一个结构性事实：**损耗近似二值**（要么 SF7 闭合，要么彻底不可达），
#: 因为遮挡造成的超额损耗（71–107 dB）远大于 SF7→SF12 的 14 dB 灵敏度差。因此"链路质量"在
#: 这套地形上不是平滑梯度，而是通视／不通视——这正是"节点静默掉线"的来源。
GROUP_LAYOUT: dict[int, dict] = {
    0: {"centre_m": (0.0, 1500.0), "spacing_m": 220.0},        # 近坡，正北 1.5 km
    1: {"centre_m": (1768.0, -1768.0), "spacing_m": 220.0},    # 远坡，东南 2.5 km
}

#: 3x3 栅格去掉中心 —— 一个坡面上 8 个测点围成一圈。
_RING3 = tuple((dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dx, dy) != (0, 0))

TILE = "N30E094"
FREQ_MHZ = 868.0
RELIABILITY = 90.0
TX_DBM, G_TX, G_RX, FEEDER = 14.0, 2.0, 2.0, 1.0

#: 位点稳定性检验的扰动半径（米）。取 2 m：真实部署里测点与天线的定位不确定度远大于此。
STABILITY_M = 2.0

CACHE_PATH = _os.path.normpath(
    _os.path.join(_CODE, "..", "data", "derived", "link_budget.json"))


@dataclass(frozen=True)
class SitePoint:
    sid: str
    lat: float
    lon: float
    elev_m: float
    role: str                 # "gateway" | "slope"
    measurand: str            # "rainfall" | "displacement"
    slope_group: int = -1


@dataclass
class Deployment:
    """一个监测单元：网关（带雨量计）+ 坡面节点。"""

    gateway: SitePoint
    nodes: tuple[SitePoint, ...]
    loss_db: dict[str, float] = field(default_factory=dict)   # 节点 -> ITM 损耗
    best_sf: dict[str, int] = field(default_factory=dict)     # 节点 -> 可闭合的最低 SF
    margin_db: dict[str, float] = field(default_factory=dict)
    #: 判定在 ±STABILITY_M 米扰动下会翻转的位点。它们**仍然是真实布点**，但"可达性"对它们不是
    #: 地形事实而是坐标巧合，因此默认排除出主实例，并单列报数。
    marginal: set[str] = field(default_factory=set)

    @property
    def node_ids(self) -> tuple[str, ...]:
        """**主实例的节点**：排除绕射边缘上的位点。"""
        return tuple(n.sid for n in self.nodes if n.sid not in self.marginal)

    @property
    def all_node_ids(self) -> tuple[str, ...]:
        return tuple(n.sid for n in self.nodes)

    def reachable(self, node_id: str) -> bool:
        """该节点能否用任何一个 SF 闭合链路。**外生事实**，不由任何方法改变。"""
        return node_id in self.best_sf

    @property
    def reachable_ids(self) -> tuple[str, ...]:
        return tuple(n for n in self.node_ids if self.reachable(n))

    def summary(self) -> dict:
        return {
            "gateway": self.gateway.sid,
            "n_slope_nodes": len(self.nodes),
            "n_marginal_excluded": len(self.marginal),
            "marginal_ids": sorted(self.marginal),
            "n_reachable": len(self.reachable_ids),
            "loss_db": {k: round(v, 2) for k, v in sorted(self.loss_db.items())},
            "best_sf": dict(sorted(self.best_sf.items())),
        }


# ---------------------------------------------------------------- ITM

def _load_cache() -> dict:
    if not _os.path.exists(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _save_cache(cache: dict) -> None:
    _os.makedirs(_os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, indent=1, sort_keys=True)


#: DEM 只读一次。放在模块级而不是函数属性里，避免每次调用都走 try/except。
_DEM_CACHE: dict[str, object] = {}


def _dem():
    if "dem" not in _DEM_CACHE:
        from mountain_lora_link import read_hgt
        _DEM_CACHE["dem"] = read_hgt(TILE)
    return _DEM_CACHE["dem"]


def link_budget(gw: SitePoint, node: SitePoint, cache: dict) -> tuple[float, int | None, float]:
    """一条链路的 ITM 损耗与可闭合的 SF。返回 `(loss_db, sf 或 None, margin_db)`。

    缓存键含瓦片、两侧坐标与频段；**缓存只省时间，不参与判定**——同一个键永远给出同一个值，
    因为它就是同一条链路。
    """
    from mountain_lora_link import best_sf, itm_loss, terrain_profile

    key = f"{TILE}|{gw.lat:.5f},{gw.lon:.5f}|{node.lat:.5f},{node.lon:.5f}|{FREQ_MHZ}"
    hit = cache.get(key)
    if hit is not None:
        return hit["loss_db"], hit["best_sf"], hit["margin_db"]

    prof, d_km, _ = terrain_profile(_dem(), TILE, (gw.lat, gw.lon), (node.lat, node.lon))
    losses, _, _ = itm_loss(FREQ_MHZ, d_km, (2.0, 2.0), prof, qr_pct=(RELIABILITY,))
    loss = float(losses[RELIABILITY])
    sf, margin = best_sf(loss, TX_DBM, G_TX, G_RX, FEEDER)
    cache[key] = {"loss_db": loss, "best_sf": sf, "margin_db": float(margin)}
    return loss, sf, float(margin)


def build_deployment(groups: int = 2, per_group: int | None = None,
                     use_terrain: bool = True) -> Deployment:
    """建一个监测单元。

    `groups` × 每组的位点数决定坡面节点数；`per_group=None` 表示取完该组的全部 8 个位点。
    因此规模是 8／16 两档，这就是 v1.1 §3 说的 **scale axis**。

    `use_terrain=False` 时跳过 ITM，把节点全部标为可达——**只用于不关心地形的极速冒烟**；
    这样得到的读数不得用于任何与可达性相关的结论，`loss_db` 记为 NaN 以资区别。
    """
    gateway = SitePoint("gw0", GATEWAY_LAT, GATEWAY_LON, GATEWAY_ELEV_M,
                        role="gateway", measurand="rainfall")
    nodes: list[SitePoint] = []
    for g in range(groups):
        layout = GROUP_LAYOUT[g]
        ce, cn = layout["centre_m"]
        sp = layout["spacing_m"]
        k = len(_RING3) if per_group is None else per_group
        for idx in range(k):
            dx, dy = _RING3[idx]
            east, north = ce + dx * sp, cn + dy * sp
            lat = GATEWAY_LAT + north / M_PER_DEG_LAT
            lon = GATEWAY_LON + east / (M_PER_DEG_LAT * math.cos(math.radians(GATEWAY_LAT)))
            nodes.append(SitePoint(
                sid=f"n{g}{idx}",
                # **不四舍五入**：5 位小数约 1 m，而在绕射边缘上 1 m 能让损耗摆动 65–70 dB。
                lat=lat, lon=lon,
                # 高度由 DEM 取，不再手工列常数——手列的那一版正是与真实地形脱节的原因。
                elev_m=0.0,
                role="slope", measurand="displacement", slope_group=g))

    dep = Deployment(gateway=gateway, nodes=tuple(nodes))
    if not use_terrain:
        dep.best_sf = {n.sid: 12 for n in dep.nodes}
        dep.loss_db = {n.sid: float("nan") for n in dep.nodes}
        dep.margin_db = {n.sid: float("nan") for n in dep.nodes}
        return dep

    from mountain_lora_link import elev_at
    dem = _dem()
    dep = Deployment(gateway=gateway, nodes=tuple(
        SitePoint(n.sid, n.lat, n.lon, float(elev_at(dem, TILE, n.lat, n.lon)),
                  n.role, n.measurand, n.slope_group) for n in dep.nodes))
    cache = _load_cache()
    for site in dep.nodes:
        loss, sf, margin = link_budget(gateway, site, cache)
        dep.loss_db[site.sid] = loss
        dep.margin_db[site.sid] = margin
        if sf is not None:
            dep.best_sf[site.sid] = sf
        if not _verdict_is_stable(gateway, site, sf is not None, cache):
            dep.marginal.add(site.sid)
    _save_cache(cache)
    return dep


def _verdict_is_stable(gw: SitePoint, node: SitePoint, verdict: bool, cache: dict) -> bool:
    """把位点在 ±`STABILITY_M` 米内动一动，可达性判定是否不变。

    动的是**真实地形上的位置**，因此扰动点也要走同一条 ITM 计算。四方向加原点共五次判定；
    只要有一次翻转，这个位点就被标为 `marginal`。

    这不是在"挑好看的位点"：一个判定随 1–2 米翻转的链路，其可达性本来就是未定的，把它当成
    外生事实会把坐标巧合写成物理结论。
    """
    for brg_deg in (0.0, 90.0, 180.0, 270.0):
        r = math.radians(brg_deg)
        dlat = STABILITY_M * math.cos(r) / M_PER_DEG_LAT
        dlon = STABILITY_M * math.sin(r) / (M_PER_DEG_LAT * math.cos(math.radians(gw.lat)))
        moved = SitePoint(node.sid, node.lat + dlat, node.lon + dlon,
                          node.elev_m, node.role, node.measurand, node.slope_group)
        _, sf2, _ = link_budget(gw, moved, cache)
        if (sf2 is not None) != verdict:
            return False
    return True
