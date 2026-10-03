"""v1.2 minimal probe —— 受限备用短报文链路的**回放叠加**引擎（只建模，不跑策略训练）。
本模块引用的 `docs/…` 路径为作者本地过程文档，不随仓库发布。

设计定位（见 `docs/s7-method/v1.2/02-pre-registration-minimal-probe-2026-09-14.md`）
=================================================================================

v1.1 已封版（tag `v1.1-causal-closure`），其结式为
``delivered_i = 1[h_i* <= B(d_i)]``，且网关→中心那一跳**没有**可调度自由度
（链路 up 即全量转发、无容量、无优先级）。v1.2 的 actuator source audit
（`docs/s7-method/v1.2/01-...md`）选定唯一现实动作面：**primary 蜂窝 + 受限备用
短报文（北斗 RDSS）**，硬约束全部来自 A 级标准：发送周期 ≥1 min（民用实配 120 s）、
单包 ≤200 B（≈ 本任务 K 条义务样本/包）。

本模块**不改 v1.1 一个字节**：它只 ``import`` v1.1 的 ``one_seed`` 跑出**逐义务台账**
（``obligation_ledger=True``），然后在台账之上**叠加**一条独立、均匀、全程可用的
备用机会序列，回答预注册冻结的两个问题：

* **P-A（actuator 有没有用）**：任一"使用备用"的臂是否显著优于 ``primary_only``；
* **P-B（"选谁"是不是真问题）**：不同 chooser（装包排序）之间是否有实质差别。

六条臂共用**同一动作面、同一速率、同一容量 K、同一合法可观测集**，只有
"在一个备用机会里把池里哪 K 条装走"的排序不同：

    primary_only      从不使用备用（结果必须逐义务 == v1.1 台账，正确性锚点）
    backup_all        不分诊：与时间/期限无关的确定性序（oid 序），代表"系统默认顺序"
    backup_fifo       先入先出：最早到网关（h* 最小）优先
    backup_latest     最新优先：最晚到网关（h* 最大）优先
    backup_edf        最早截止优先（classic earliest-deadline-first）
    backup_opportunity 机会感知：用**截至 t 的主链路历史**估计"现在不发、主链路自救
                      成功"的希望，希望最小者优先；仍是显式手写规则，**不是 LLM、不是
                      全知**（structured-baseline 阶段才上更强的 MPC 类基线）。

合法可观测集（决策时刻 t，**严禁**未来/真值）
---------------------------------------------
* 每条义务的到网关时刻 h*（``first_heard_at``）与**公开**期限 ``deadline``；
* 主链路**截至 t** 的 up/down 历史（链路级二值，这是 source audit §3.6.4 指出的
  现实中唯一有文档的状态面）；
* 主链路**截至 t** 已确认交付的时刻（``delivered_at``，相当于主链路回执）。
chooser **看不到**：主链路未来何时 up、某义务"最终"会不会被主链路交付、真值。
接口层只把**已截断到 t** 的历史聚合量传给 chooser（``History``），从签名上杜绝偷看。

显式简化（预注册 §7 "简化必须随结果声明"，结果文档逐条复述）
-----------------------------------------------------------
1. 备用链路**成功率取 1**、**发送时延当拍**（标准：成功率≥95%、平均时延优于 2 s，
   相对 900 s 义务窗可忽略；不忽略只会让备用略弱，不改变 chooser 之间的 P-B 对比）；
2. **不计字节级分包**，容量直接用"每包 K 条义务样本"（K 由 200 B−固定开销、每样本
   ≈20 B 派生，主例 K=9）；
3. **不计资费/能量**，资源稀缺只由 速率×K 体现（北斗—地灾链条无单价来源，见 audit）；
4. **网关级备用**：义务样本到网关（h*）后才进备用池。标准里卫星是**终端级**直连，
   终端级只会让入池更早（放松），且所有 chooser 用同一入池时刻，故**不影响 P-B**；
   它只让 P-A 的绝对救回数偏保守，敏感性另做"入池提前"说明；
5. 备用机会**全程均匀且独立于地面中断**（卫星保底，正是它存在的意义）。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional

#: 六条臂；``primary_only`` 是唯一基线，其余五个是 chooser。
ARMS = ("primary_only", "backup_all", "backup_fifo", "backup_latest",
        "backup_edf", "backup_opportunity")
CHOOSERS = ("backup_all", "backup_fifo", "backup_latest",
            "backup_edf", "backup_opportunity")

TICK_S = 60
HOUR_S = 3600


# --------------------------------------------------------------------------- #
# 数据结构
# --------------------------------------------------------------------------- #
@dataclass
class Obl:
    """一条义务在回放中需要的全部信息（全部来自 v1.1 台账，无新数字）。"""
    oid: str
    kind: str
    release_at: Optional[int]
    deadline: int
    h: Optional[int]                       # first_heard_at，到网关时刻
    confirmed_at: Optional[int]            # 主链路确认交付时刻（= delivered_at）
    primary_delivered: bool

    @property
    def primary_lost(self) -> bool:
        return not self.primary_delivered


@dataclass
class History:
    """**截至决策时刻 t** 主链路历史的合法聚合（不含任何 t 之后信息）。"""
    t: int
    observed_hours: int                    # 已经历的完整小时数
    up_hours: int                          # 其中主链路 up 的小时数
    down_streak_h: int                     # 截至 t 连续 down 的小时数

    @property
    def p_up(self) -> float:
        if self.observed_hours <= 0:
            return 0.5                      # 无历史：最大不确定性，不借外部先验
        return self.up_hours / self.observed_hours


@dataclass
class ReplayResult:
    arm: str
    rate_s: int
    k: int
    n_obligations: int
    n_primary_delivered: int
    n_final_delivered: int
    n_rescued: int                         # 主链路丢、靠备用净救回
    n_backup_sent: int                     # 经备用装出的义务条数（含后来主链路自救的）
    n_wasted_on_recovered: int             # 装时以为要救、主链路后来自己交付了
    n_packets: int                         # 实际发出的备用包数（非空机会数）
    n_slots: int                           # 实际占用的包内槽位（= n_backup_sent）
    n_never_heard: int                     # h*=None：网关级简化下备用也够不到
    n_expired_unsent: int                  # 进过池但没轮到、期限已过仍丢失
    n_gated_opportunities: int = 0         # 因主链路 up 而未启用备用的机会数（failover gate）
    per_oid: dict = field(default_factory=dict)

    @property
    def rescued_per_packet(self) -> float:
        """P-A 效率门槛用：平均每个备用包净换回几条义务。"""
        return self.n_rescued / self.n_packets if self.n_packets else 0.0

    @property
    def slot_efficiency(self) -> float:
        return self.n_rescued / self.n_slots if self.n_slots else 0.0


def rows_from_run(run: dict) -> list[Obl]:
    """把 ``one_seed(..., obligation_ledger=True)`` 的 ``_obligations`` 转成 :class:`Obl`。"""
    out: list[Obl] = []
    for r in run["_obligations"]:
        delivered = bool(r["delivered"])
        out.append(Obl(
            oid=r["oid"], kind=r.get("kind", ""),
            release_at=r.get("release_at"), deadline=int(r["deadline"]),
            h=None if r.get("first_heard_at") is None else int(r["first_heard_at"]),
            confirmed_at=(None if not delivered or r.get("delivered_at") is None
                          else int(r["delivered_at"])),
            primary_delivered=delivered))
    return out


# --------------------------------------------------------------------------- #
# 主链路历史（只截断到 t；up_ticks 为 v1.1 纯函数重建的逐 60 s 可回传拍）
# --------------------------------------------------------------------------- #
def _history_at(t: int, up_hour_flag: list[bool]) -> History:
    """``up_hour_flag[h]`` 表示第 h 小时主链路是否可回传。只统计 ``t`` 之前的小时。"""
    cur_h = t // HOUR_S
    observed = min(cur_h, len(up_hour_flag))
    up = sum(1 for h in range(observed) if up_hour_flag[h])
    streak = 0
    for h in range(observed - 1, -1, -1):
        if up_hour_flag[h]:
            break
        streak += 1
    return History(t=t, observed_hours=observed, up_hours=up, down_streak_h=streak)


def up_hours_from_ticks(up_ticks: list[int], end_s: int) -> list[bool]:
    """把逐 60 s 可回传拍聚合成逐小时 up 标志（一小时内任一拍 up 即该小时 up）。"""
    n_h = end_s // HOUR_S + 1
    flag = [False] * n_h
    for tk in up_ticks:
        h = tk // HOUR_S
        if 0 <= h < n_h:
            flag[h] = True
    return flag


# --------------------------------------------------------------------------- #
# chooser —— 全部是确定性排序，输入只有当前池 + t + 已截断历史
# --------------------------------------------------------------------------- #
def _key_all(o: Obl):
    return (o.oid,)


def _key_fifo(o: Obl):
    return (o.h, o.oid)


def _key_latest(o: Obl):
    return (-o.h, o.oid)


def _key_edf(o: Obl):
    return (o.deadline, o.oid)


def _opportunity_score(o: Obl, t: int, hist: History):
    """机会感知分：返回排序键，**越该优先越靠前**。

    ``p_lost_if_skip``＝"若这个机会不发、主链路在剩余窗口内一直不可用"的粗估，
    用截至 t 的经验 up 率做 iid 近似（**仅用于排序，不声称为真实概率**）：
    剩余整小时数越多、历史 up 率越高，主链路自救希望越大，备用优先级越低。
    tie-break 用 EDF（期限更早优先），再用 oid 保证确定性。
    """
    left_h = max(1, math.ceil(max(0, o.deadline - t) / HOUR_S))
    p_up = hist.p_up
    p_lost = (1.0 - p_up) ** left_h
    # 连续 down 越久，短期恢复越不乐观，轻微加权（仍只依赖历史）
    streak_bonus = min(hist.down_streak_h, 12) * 1e-3
    return (-(p_lost + streak_bonus), o.deadline, o.oid)


_CHOOSER_KEYS: dict[str, Callable] = {
    "backup_all": _key_all,
    "backup_fifo": _key_fifo,
    "backup_latest": _key_latest,
    "backup_edf": _key_edf,
}


def order_pool(arm: str, pool: list[Obl], t: int, hist: History) -> list[Obl]:
    if arm == "backup_opportunity":
        return sorted(pool, key=lambda o: _opportunity_score(o, t, hist))
    key = _CHOOSER_KEYS[arm]
    return sorted(pool, key=key)


# --------------------------------------------------------------------------- #
# 单台账回放
# --------------------------------------------------------------------------- #
def replay(rows: list[Obl], arm: str, rate_s: int, k: int, end_s: int,
           up_hour_flag: list[bool], failover_gate: bool = True) -> ReplayResult:
    """在同一份逐义务台账上叠加备用链路，返回单种子结果。

    所有 chooser 共用同一机会序列、同一池演化，只在排序上不同，保证配对公平。

    ``failover_gate=True``（主分析，贴合标准 §5.3.7 双模与厂商"4G 掉线自动切北斗"
    实配）：**仅当主链路在 t 所在小时 down** 时该备用机会才启用；主链路 up 小时
    v1.1 会当拍全量转发（``opportunity.py:419``），没有需要备用的积压。这一 gate
    只依赖 t 时刻合法可见的链路二值状态（source audit §3.6.4：现实中唯一有文档
    的状态面）。``failover_gate=False`` 是"双通道始终并行"的**上界对照**，只用于
    敏感性，不是主张的工作模式。
    """
    assert arm in ARMS, f"unknown arm {arm!r}"
    state = {o.oid: o for o in rows}
    n_primary = sum(1 for o in rows if o.primary_delivered)
    n_never_heard = sum(1 for o in rows if o.h is None)

    if arm == "primary_only":
        # 锚点：不使用备用，最终交付必须与主链路逐义务一致。
        return ReplayResult(
            arm=arm, rate_s=rate_s, k=k, n_obligations=len(rows),
            n_primary_delivered=n_primary, n_final_delivered=n_primary,
            n_rescued=0, n_backup_sent=0, n_wasted_on_recovered=0,
            n_packets=0, n_slots=0, n_never_heard=n_never_heard,
            n_expired_unsent=sum(1 for o in rows
                                 if not o.primary_delivered and o.h is not None),
            per_oid={o.oid: o.primary_delivered for o in rows})

    sent_at: dict[str, int] = {}
    n_packets = 0
    n_gated = 0
    t = rate_s
    while t <= end_s:
        cur_h = t // HOUR_S
        primary_up_now = cur_h < len(up_hour_flag) and up_hour_flag[cur_h]
        if failover_gate and primary_up_now:
            n_gated += 1                              # 主链路当前 up，备用不启用
            t += rate_s
            continue
        # 1) 构造 t 时刻合法待发池
        pool: list[Obl] = []
        for o in rows:
            if o.oid in sent_at:
                continue                          # 已经备用发出
            if o.h is None or o.h > t:
                continue                          # 尚未到网关，不具备发送条件
            if o.deadline < t:
                continue                          # 已过期限，装了也无效
            if o.confirmed_at is not None and o.confirmed_at <= t:
                continue                          # 主链路已确认交付，不占备用槽位
            pool.append(o)
        # 2) 用**只到 t** 的历史排序，取前 K
        if pool:
            hist = _history_at(t, up_hour_flag)
            ordered = order_pool(arm, pool, t, hist)
            pick = ordered[:k]
            if pick:
                n_packets += 1
            for o in pick:
                sent_at[o.oid] = t
        t += rate_s

    # 3) 汇总
    per_oid, n_final, n_rescued, n_sent, n_wasted, n_expired = {}, 0, 0, 0, 0, 0
    for o in rows:
        backup = o.oid in sent_at
        final = o.primary_delivered or backup
        per_oid[o.oid] = final
        n_final += int(final)
        if backup:
            n_sent += 1
            if o.primary_delivered:
                n_wasted += 1                    # 装时未确认、主链路后来自救
            else:
                n_rescued += 1
        elif not o.primary_delivered and o.h is not None and o.deadline < end_s:
            n_expired += 1
    return ReplayResult(
        arm=arm, rate_s=rate_s, k=k, n_obligations=len(rows),
        n_primary_delivered=n_primary, n_final_delivered=n_final,
        n_rescued=n_rescued, n_backup_sent=n_sent,
        n_wasted_on_recovered=n_wasted, n_packets=n_packets, n_slots=n_sent,
        n_never_heard=n_never_heard, n_expired_unsent=n_expired,
        n_gated_opportunities=n_gated,
        per_oid=per_oid)
