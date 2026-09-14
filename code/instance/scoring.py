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
    release_at: int = 0
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
             plane=None, task_hours: int | None = None,
             outage: tuple[int, int] | None = None,
             recovery_s: int = 3600,
             collect_rows: bool = False) -> dict:
    """对一次运行评分。返回**分列**的结果字典，不含任何合成分数。

    **尾部观察期（v1.1 §9）。** `hours` 是**运行**长度，`task_hours` 是**义务**覆盖的区间；
    两者之差就是固定的尾部观察期。义务只在 `[0, task_hours)` 内产生，但运行会继续跑到
    `hours`，让"任务期结束前发出、还在路上"的样本有机会到达。

    判定规则不是"跑完就算失败"，而是：

      * 义务的观察截止 `deadline <= 运行末`  → 可以判定，未交付就是 `missing_delivery`；
      * 义务的观察截止 `deadline >  运行末`  → **右删失**：运行结束时它的期限还没到，
        既不能说成功也不能说失败。**删失的留在分母里**，不许悄悄剔掉，也不许无限等待之后
        算作按时完成。
    """
    by_key = _index_samples(log)
    end_s = hours * 3600
    task_s = end_s if task_hours is None else task_hours * 3600

    outcomes: list[ObligationOutcome] = []
    for o in obligations.obligations:
        out = ObligationOutcome(oid=o.oid, kind=o.kind, node_id=o.node_id,
                                measurand=o.measurand, release_at=o.release_at)
        for sample, received_at in by_key.get((o.node_id, o.measurand), ()):
            if not o.matches(sample):
                continue
            out.collected = True
            if received_at is not None and received_at <= o.deadline:
                out.delivered = True
                out.delivered_at = received_at
                out.latency_s = received_at - sample.taken_at
                break
        if not out.delivered and end_s < o.deadline:
            # 运行结束时该义务的观察截止还没到：右删失。**不是失败**，也不能当作成功。
            out.censored = True
        outcomes.append(out)

    res: dict = {"n_obligations": len(outcomes),
                 "by_kind": _split(outcomes)}
    if collect_rows:
        # **逐义务台账（默认关闭）**：§31 第 109 行要"它增加的是**哪条固定义务**的服务"，
        # 聚合量答不了这个问题。`collect_rows=False` 时一个字节都不多记，读数逐位不变。
        res["rows"] = [{"oid": o.oid, "kind": o.kind, "node_id": o.node_id,
                        "release_at": o.release_at, "collected": o.collected,
                        "delivered": o.delivered, "censored": o.censored,
                        "delivered_at": o.delivered_at, "latency_s": o.latency_s}
                       for o in outcomes]

    # -------------------------------------------------- 周期新鲜度与完整性
    res["routine"] = _routine_block(outcomes, log, node_ids, end_s, by_key)

    # -------------------------------------------------- 事件采集与时效
    res["event"] = _event_block(obligations, outcomes)

    # -------------------------------------------------- 能源
    res["energy"] = _energy_block(battery, node_ids, end_s)

    # -------------------------------------------------- 通信代价
    res["communication"] = _comm_block(log, plane)

    # -------------------------------------------------- 不适用项，显式说明原因
    if outage is not None:
        res["recovery"] = recovery_block(obligations, outcomes, log, outage,
                                         run_end_s=end_s, recovery_s=recovery_s)

    if getattr(log, "truth", None) is not None:
        res["propagation"] = event_propagation(log.truth, log)

    res["observation_window"] = {
        "task_hours": task_s // 3600,
        "run_hours": end_s // 3600,
        "tail_s": end_s - task_s,
        "censored_total": sum(o.censored for o in outcomes),
        "note": "删失 = 运行结束时该义务的观察截止还没到；既不算成功也不算失败，留在分母里。",
    }
    res["config_mismatch_s"] = None
    res["not_applicable"] = {
        "config_mismatch_s": "最小实例没有外部配置要求，无法定义'错误配置'；返回 None 而不是 0。",
        "mixed_config_s": "计数器在 Instance.mixed_config_ticks 上，本函数只拿到 log、"
                          "取不到；**不返回恒定值的假列**。需要这一列请从 Instance 取。",
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
        # **必须按「中心收到的时刻」排序，不是按「采集时刻」。**（2026-09-13 修）
        #
        # 第一版写的是 `sorted(s.taken_at ...)`，推进条件用 `stamps[i] <= t`：
        # 于是一条**采集于 0 点、40 h 后才收到**的样本，被算成 0 点就已经在中心手里了。
        # 后果是这一列对**接入中断完全不可见**——实测 49 h 运行、0–40 h 接入中断下
        # `no_observation_s = 0`、`aoi_mean_s` 与无中断时**逐位相同**（1794.58 s），
        # 而那一档实际有 517/672 条义务没送达。AoI 是四个目标之一，这个偏差会污染支配判据。
        #
        # 正确语义：`t` 时刻的年龄 = `t − max{ taken_at : 该样本在 t 之前已被中心收到 }`。
        #
        # 两个坑，都在这里踩过：
        #   ① 排序键必须是**接收时刻**（见上）；
        #   ② `newest` 必须取 **max**，不能"来一条就覆盖"。缓存服务次序取最新优先时，
        #      同一小时内的两次上报会**先到新记录、后到旧记录**（第一次带最新的 9–40 点，
        #      第二次带剩下的 0–8 点），直接覆盖会让"最新采集时刻"**倒退**——实测 t=41 h 时
        #      年龄算成 33 h，而中心其实在 40 h 就拿到了 40 点的记录。
        recv = sorted((r, s.taken_at) for s, r in by_key.get((node_id, measurand), ())
                      if r is not None)
        if not recv:
            no_obs_ticks += end_s // TICK_S
            continue
        i = 0
        newest = None
        for t in range(0, end_s, TICK_S):
            while i < len(recv) and recv[i][0] <= t:
                ta = recv[i][1]
                newest = ta if newest is None or ta > newest else newest
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


# ---------------------------------------------------------------- 中断后恢复

def recovery_block(obligations: ObligationSet, outcomes, log, outage: tuple[int, int],
                   run_end_s: int, recovery_s: int = 3600) -> dict:
    """中断与恢复分列（v1.1 §9、§5.3）。

    只对**落在中断窗及随后固定恢复观察期内**的义务报数，并且**采集缺失与交付缺失分开**：

      * `missing_collection` —— 中断期间节点侧没有产出（没电、或本地规则没跑）。这部分
        **补不回来**：v1.1 §5.3 写明"恢复后不能按旧时间补造当时未采到的读数"；
      * `missing_delivery` —— 采到了但没送到。这部分理论上可由自动补发追回，
        因此单列，不能与上一条合成一个"丢了多少"。

    另外报 `backlog_recovered`：**中断期间采集、中断之后才到达**的样本数。它是"恢复能力"
    最直接的读数——自动补发就是干这件事的。
    """
    out_s, in_s = outage
    window_end = min(run_end_s, in_s + recovery_s)
    rows = [o for o in outcomes if out_s <= o.release_at < window_end]
    recovered = 0
    for sid, sample in log.samples.items():
        tr = log.transit[sid]
        if tr.received_at is None:
            continue
        if out_s <= sample.taken_at < in_s <= tr.received_at:
            recovered += 1
    return {
        "outage_s": [out_s, in_s],
        "outage_hours": round((in_s - out_s) / 3600.0, 3),
        "recovery_observation_s": window_end - in_s,
        "n_obligations_in_window": len(rows),
        "delivered": sum(o.delivered for o in rows),
        "missing_collection": sum(not o.collected for o in rows),
        "missing_delivery": sum(o.collected and not o.delivered and not o.censored
                                for o in rows),
        "censored": sum(o.censored for o in rows),
        "backlog_recovered": recovered,
        "note": ("采集缺失在恢复后补不回来（不补造当时未采到的读数）；交付缺失单列，"
                 "因为它可由自动补发追回。"),
    }


# ---------------------------------------------------------------- 事件传播

def event_propagation(truth, log, burst_window_s: int = 900) -> dict:
    """把一次触发拆成三个时刻：**源发生 → 设备检测 → 中心获知**（v1.1 §9）。

    为什么必须分开：v1.1 §4 明说"事件的原始发生、设备检测、中心获知分别计时"。合成一个"事件时延"
    会把两件性质完全不同的事混起来——**设备没检测到**（本地规则没跑、或节点没电）与
    **检测到了但送不回来**（接入或回传断了）。前者要靠现场自治解决，后者才是通信问题。

    判定方式是从记录里推导，不在循环里埋点：

      * `source_at`   = 环境真值里的触发时刻；
      * `detected_at` = 该节点在触发之后的第一条样本的采集时刻（本地规则被唤醒的产物）；
      * `knowledge_at`= 那些样本里**第一条到达中心**的接收时刻。

    **本实例里"中心获知事件"与"中心拿到首份新数据"是同一个时刻**，因为中心没有第二条获知渠道
    （没有外部公告进入模型）。这两者在本实例中不区分，**不得**据此声称测过它们的差。
    """
    trig = sorted(truth.triggers)
    by_node: dict[str, list] = {}
    for sid, sample in log.samples.items():
        by_node.setdefault(sample.node_id, []).append((sample, log.transit[sid].received_at))
    for v in by_node.values():
        v.sort(key=lambda pair: pair[0].taken_at)

    rows = []
    for source_at, node_id in trig:
        burst = [(smp, rec) for smp, rec in by_node.get(node_id, ())
                 if source_at <= smp.taken_at <= source_at + burst_window_s]
        detected_at = burst[0][0].taken_at if burst else None
        arrivals = [rec for _smp, rec in burst if rec is not None]
        knowledge_at = min(arrivals) if arrivals else None
        rows.append({
            "node_id": node_id,
            "source_at": source_at,
            "detected_at": detected_at,
            "knowledge_at": knowledge_at,
            "detection_latency_s": None if detected_at is None else detected_at - source_at,
            "knowledge_latency_s": None if knowledge_at is None else knowledge_at - source_at,
            "delivery_latency_s": (None if (knowledge_at is None or detected_at is None)
                                   else knowledge_at - detected_at),
        })

    det = [r["detection_latency_s"] for r in rows if r["detection_latency_s"] is not None]
    kno = [r["knowledge_latency_s"] for r in rows if r["knowledge_latency_s"] is not None]
    dly = [r["delivery_latency_s"] for r in rows if r["delivery_latency_s"] is not None]
    return {
        "n_triggers": len(rows),
        "detected": len(det),
        "known_to_center": len(kno),
        "detection_latency_mean_s": _mean(det),
        "knowledge_latency_mean_s": _mean(kno),
        "delivery_latency_mean_s": _mean(dly),
        "detection_latency_p90_s": _pct(det, 90),
        "knowledge_latency_p90_s": _pct(kno, 90),
        "per_trigger": rows,
        "note": ("本实例没有第二条获知渠道，因此'中心获知事件'与'中心拿到首份新数据'同一时刻；"
                 "两者的差未被测过。"),
    }


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
