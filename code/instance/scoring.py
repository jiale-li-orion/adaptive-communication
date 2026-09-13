"""E4 — 分列评分器。

Task Contract v1.1 §9 的落地。三条纪律写在代码里，不是写在文档里：

1. **不设大一统加权分数。** 本模块只产出分列的量，没有任何把业务量与成本合成一个标量的函数。
   benchmark 最容易被 argue 的就是权重是作者自己调的。
2. **分母来自 `D`，不来自任何方法实际产生了多少。** 不采样不能改善得分。
3. **未完成不消失。** 超过观察截止仍未交付的条目**标右删失**并留在分母里，不只报告成功者的均值。

阈值曲线里的一切阈值都叫**研究容忍时延**；没有业务来源就不称 SLA。

尚未实现且**显式标注为不适用**的一项：配置正确性（`config_mismatch_s`）。它只对"有明确外部配置
要求的区间"积分，而最小实例还没有外部配置要求，因此本模块返回 `None` 并在结果里写明原因——
返回 0 会被读成"没有错配"，那是错的。
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

from exogenous import KIND_EVENT, KIND_ROUTINE, ObligationSet
from network import TICK_S


@dataclass
class ObligationOutcome:
    """一条义务的结局。**采集与送达分开记**——失电时未采集与采集了没送到是两件事。"""

    oid: str
    kind: str
    node_id: str = ""
    measurand: str = ""
    collected: bool = False          # 有样本落在采集窗内（容差内）
    delivered: bool = False          # 且该样本在观察截止前到达中心
    censored: bool = False           # 到观察期末仍未交付
    delivered_at: int | None = None  # 中心收到的时刻
    latency_s: int | None = None     # 采集时刻 → 中心收到时刻


def _index_samples(log):
    """把 `HopLog` 摊平成按 (node, measurand) 分组的样本列表，附中心接收时刻。"""
    by_key: dict[tuple[str, str], list] = {}
    for sid, sample in log.samples.items():
        by_key.setdefault((sample.node_id, sample.measurand), []).append(
            (sample, log.transit[sid].received_at))
    for v in by_key.values():
        v.sort(key=lambda pair: pair[0].taken_at)
    return by_key


def evaluate(obligations: ObligationSet, log, hours: int, node_ids,
             battery: dict[str, dict] | None = None,
             plane=None) -> dict:
    """对一次运行评分。返回**分列**的结果字典，不含任何合成分数。"""
    by_key = _index_samples(log)
    end_s = hours * 3600

    outcomes: list[ObligationOutcome] = []
    for o in obligations.obligations:
        out = ObligationOutcome(oid=o.oid, kind=o.kind,
                                node_id=o.node_id, measurand=o.measurand)
        for sample, received_at in by_key.get((o.node_id, o.measurand), ()):
            if not o.matches(sample):
                continue
            out.collected = True
            if received_at is not None and received_at <= o.deadline:
                out.delivered = True
                out.delivered_at = received_at
                out.latency_s = received_at - sample.taken_at
                break
        if not out.delivered and end_s <= o.deadline:
            out.censored = True          # 观察期先于截止结束：右删失，不是失败
        outcomes.append(out)

    res: dict = {"n_obligations": len(outcomes),
                 "by_kind": _split(outcomes)}

    # -------------------------------------------------- 周期新鲜度与完整性
    res["routine"] = _routine_block(outcomes, log, node_ids, end_s, by_key)

    # -------------------------------------------------- 事件采集与时效
    res["event"] = _event_block(obligations, outcomes)

    # -------------------------------------------------- 能源
    res["energy"] = _energy_block(battery, node_ids, end_s)

    # -------------------------------------------------- 通信代价
    res["communication"] = _comm_block(log, plane)

    # -------------------------------------------------- 不适用项，显式说明原因
    res["config_mismatch_s"] = None
    res["not_applicable"] = {
        "config_mismatch_s": "最小实例没有外部配置要求，无法定义'错误配置'；返回 None 而不是 0。",
    }
    return res


def _split(outcomes) -> dict:
    """按义务类别分列。

    **采集缺失与送达缺失必须分开**：失电时未采集，与采集了但没送到，是两种不同的业务损害，
    合并成一个"未完成"会把它们混为一谈（v1.1 §5.3、§9）。
    """
    out = {}
    for kind in (KIND_ROUTINE, KIND_EVENT):
        rows = [o for o in outcomes if o.kind == kind]
        if not rows:
            continue
        out[kind] = {
            "n": len(rows),
            "collected": sum(o.collected for o in rows),
            "delivered": sum(o.delivered for o in rows),
            "censored": sum(o.censored for o in rows),
            "missing_collection": sum(not o.collected for o in rows),
            "missing_delivery": sum(o.collected and not o.delivered and not o.censored
                                    for o in rows),
        }
    return out


def _routine_block(outcomes, log, node_ids, end_s, by_key) -> dict:
    """周期新鲜度（中心 AoI）与完整性。

    AoI 用**中心实际收到**的样本算：`t - max(taken_at)`。**从未收到过任何测值的区间返回 None**，
    不得默认为 0（v1.1 §9 的"尚无观测时长"单列）。
    """
    rows = [o for o in outcomes if o.kind == KIND_ROUTINE]

    # AoI 时间平均：按 tick 走一遍中心侧的最新采集时刻。
    # **按义务的 (节点, 测项) 分组**，不按实体——网关只有雨量、坡面节点只有位移，
    # 拿一个实体去算它没有的那个测项，会把整段时间记成"无观测"（实测踩过：43200 s 全段）。
    pairs = sorted({(o.node_id, o.measurand) for o in rows})
    aoi_sum, aoi_ticks, no_obs_ticks = 0, 0, 0
    for node_id, measurand in pairs:
        stamps = sorted(s.taken_at for s, r in by_key.get((node_id, measurand), ())
                        if r is not None)
        if not stamps:
            no_obs_ticks += end_s // TICK_S
            continue
        i = 0
        newest = None
        for t in range(0, end_s, TICK_S):
            while i < len(stamps) and stamps[i] <= t:
                newest = stamps[i]
                i += 1
            if newest is None:
                no_obs_ticks += 1
            else:
                aoi_sum += t - newest
                aoi_ticks += 1
    return {
        "n": len(rows),
        "delivered": sum(o.delivered for o in rows),
        "missing_collection": sum(not o.collected for o in rows),
        "missing_delivery": sum(o.collected and not o.delivered and not o.censored
                                for o in rows),
        "censored": sum(o.censored for o in rows),
        "aoi_mean_s": (aoi_sum / aoi_ticks) if aoi_ticks else None,
        "no_observation_s": no_obs_ticks * TICK_S,
        "latency_mean_s": _mean([o.latency_s for o in rows if o.latency_s is not None]),
        "latency_p90_s": _pct([o.latency_s for o in rows if o.latency_s is not None], 90),
    }


def _event_block(obligations, outcomes) -> dict:
    """事件采集／交付与时效。

    三个时延分开报，**区分发现慢与服务慢**（v1.1 §9）：本模块只持有义务的 release 与中心收到时刻，
    因此报"触发 → 交付"与逐名额时延；"中心何时获知事件"需要一层事件传播记录，最小实例尚未建，
    在 `not_applicable` 里写明。
    """
    rows = [o for o in outcomes if o.kind == KIND_EVENT]
    lat = [o.latency_s for o in rows if o.latency_s is not None]
    return {
        "n_slots": len(rows),
        "slots_matched_by_collection": sum(o.collected for o in rows),
        "slots_delivered": sum(o.delivered for o in rows),
        "match_rate": (sum(o.collected for o in rows) / len(rows)) if rows else None,
        "deliver_rate": (sum(o.delivered for o in rows) / len(rows)) if rows else None,
        "delivery_latency_mean_s": _mean(lat),
        "delivery_latency_p90_s": _pct(lat, 90),
        "censored": sum(o.censored for o in rows),
        # 成功 CDF：未完成的不消失（留在分母里）
        "delivery_cdf": _cdf(lat, len(rows), (0, 300, 600, 1800, 3600)),
    }


def _energy_block(battery, node_ids, end_s) -> dict:
    if not battery:
        return {"note": "未提供电量轨迹"}
    per_node = {nid: battery[nid] for nid in sorted(node_ids) if nid in battery}
    out = {"per_node": {}}
    for nid, b in per_node.items():
        out["per_node"][nid] = {
            "soc_initial_wh": b.get("soc_initial_wh"),
            "soc_final_wh": b.get("soc_final_wh"),
            "harvested_wh": b.get("harvested_wh"),
            "consumed_wh": b.get("consumed_wh"),
            "dead_at_s": b.get("dead_at_s"),
            "deficit_s": b.get("deficit_s", 0),
        }
    del end_s
    return out


def _comm_block(log, plane) -> dict:
    """通信代价分列。查询请求／回复、设置附带上报与链路层确认都归账；同报文搭载只计一次。"""
    out = {
        "samples_collected": len(log.samples),
        "uplinks": None,
        "uplinks_heard": None,
        "gateway_forwarded": None,
        "airtime_uplink_h": None,
    }
    if plane is not None:
        out.update({
            "uplinks": plane.uplinks,
            "uplinks_heard": plane.uplinks_heard,
            "gateway_forwarded": plane.backhaul_forwarded,
            "downlink_attempts": plane.downlink_attempts,
            "airtime_uplink_h": plane.airtime_uplink_ms / 3.6e6,
            "airtime_downlink_h": plane.airtime_downlink_ms / 3.6e6,
        })
    return out


# ---------------------------------------------------------------- 小工具

def _mean(xs):
    return (sum(xs) / len(xs)) if xs else None


def _pct(xs, p):
    if not xs:
        return None
    ordered = sorted(xs)
    k = min(len(ordered) - 1, int(round((p / 100.0) * (len(ordered) - 1))))
    return ordered[k]


def _cdf(latencies, denominator: int, thresholds) -> dict:
    """成功 CDF `Pr(L <= d)`，**分母是全部义务而不是已完成的那几条**（v1.1 §9）。"""
    if not denominator:
        return {}
    return {d: sum(1 for x in latencies if x <= d) / denominator for d in thresholds}
