#!/usr/bin/env python3
"""joint_plane.py — 在 v1.1 `ControlPlane` 上**叠加一条网关级备用回传腿**（北斗 RDSS 短报文）。

设计原则（见 docs/s7-method/v1.2/08、09）
=========================================
* **不改 v1.1 一个字节**：`JointControlPlane` 子类化 `ControlPlane`，只覆写 `backhaul_forward`。
  `Instance.tick` 第 3 步对 `backhaul_forward()` 返回的每个 `GatewayItem` 统一做
  `center.receive` / 设 `received_at` / `ack`——因此备用腿取走的项只要从该方法返回，就会沿**与
  主回传完全相同**的入账/确认闭环到达中心，无需复制 tick，也不会产生第二套交付语义。
* **主备异构、failover**：主回传（蜂窝）up 时由父类把 `gateway_pending` 取走；主回传 down 时
  父类返回 [] 且**保留** pending，备用腿在固定稀疏机会（每 `backup_rate_s` 一个包）上，按容量
  从**剩余**积压里取项。被取走的项移出 pending，主路恢复后不重复交付。
* **容量按真实字节**：一个备用包净荷 `backup_bytes`，样本按测项字节（displacement 6B/rainfall 4B）
  加固定头累加；一次机会至多一个包（频度约束），装不下的留下次。
* **成功率取 1、当拍发送**（v2probe 简化 1：标准成功率≥95%、时延优于 2s，相对义务窗可忽略；
  偏置对各 chooser 同等）。因此备用取包**不抽签**，跨策略差异只来自 pending 内容，干净可配对。

合法信息：chooser 只用 item 自身的 heard 时刻、样本采集时刻与**公开**义务节奏（period/grace），
不读未来主路何时恢复、不读真值。
"""
from __future__ import annotations

import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
for _p in (_os.path.join(_HERE, "..", "monitoring"), _os.path.join(_HERE, "..", "instance")):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

from opportunity import ControlPlane, GatewayItem  # noqa: E402

#: 接入段每条样本的线上编码字节（node_model.SAMPLE_BYTES），用于估算回传段占用。
DEFAULT_SAMPLE_BYTES = {"displacement": 6, "rainfall": 4}


class JointControlPlane(ControlPlane):
    """带一条网关级备用回传腿的控制面。用 :meth:`adopt` 从已构造的普通控制面接管全部状态。"""

    # ---- 构造：不重跑父类 __init__，原样接管 v1.1 已经建好的控制面（含随机链/队列/能耗账本）----
    @classmethod
    def adopt(cls, src: ControlPlane, *, enable_backup: bool = True,
              backup_rate_s: int = 120, backup_bytes: int = 200,
              backup_header_bytes: int = 20, chooser: str = "edf",
              failover: bool = True, obligation_period_s: int = 3600,
              grace_s: int = 3600, sample_bytes: dict | None = None,
              obligations=None, suppress_duplicates: bool = True,
              backup_p_succ: float = 1.0, backup_loss_seed: int = 0,
              mission_gate=None) -> "JointControlPlane":
        obj = object.__new__(cls)
        obj.__dict__.update(src.__dict__)          # 同构接管：不丢任何 v1.1 状态
        obj.enable_backup = bool(enable_backup)
        obj.backup_rate_s = int(backup_rate_s)
        obj.backup_bytes = int(backup_bytes)
        obj.backup_header_bytes = int(backup_header_bytes)
        obj.backup_chooser = chooser
        obj.backup_failover = bool(failover)
        obj.period_s = int(obligation_period_s)
        obj.grace_s = int(grace_s)
        obj.sample_bytes = dict(sample_bytes or DEFAULT_SAMPLE_BYTES)
        # 义务台账（公开节奏）：chooser='obligation' 时用**真实义务截止期**排序，并抑制同义务重复副本
        obj._obl_index: dict = {}
        obj.suppress_duplicates = bool(suppress_duplicates)
        obj._backed_obl_keys: set = set()           # 已用备用送过至少一条合格样本的义务
        obj._cover_seen: set = set()               # cover: 跨包已覆盖义务(仅降优先级,不 suppress/不停发)
        obj._mission_gate = mission_gate
        if obligations is not None:
            _view = (mission_gate.initial_view(obligations.obligations)
                     if mission_gate is not None else obligations.obligations)
            for _o in _view:
                obj._obl_index.setdefault((_o.node_id, _o.measurand), []).append(_o)
        if mission_gate is not None:
            mission_gate._plane = obj
        # 备用腿账本（尝试/发出，全部可审计）
        obj.backup_opportunities = 0     # 到达备用发送节拍且有积压的次数
        obj.backup_gated = 0             # failover 下因主路 up 而未启用的次数
        obj.backup_packets = 0           # 实际发出的非具备用包数
        obj.backup_records = 0           # 经备用送达中心的样本数
        obj.backup_bytes_sent = 0        # 经备用发出的估算字节
        obj.backup_suppressed = 0        # 因同义务已送而抑制、未占稀缺窗的冗余样本
        # **主路专属**成功时刻：只在主回传真的交出数据时更新，备用成功不算主路恢复。
        # Instance 的 gateway_last_forward_ok_at 会把备用返回项也算作"转发成功"，策略要区分
        # "主路是否健康"时必须用这个干净信号。
        obj.last_primary_ok_at = 0
        obj.backup_p_succ = float(backup_p_succ)
        import random as _random
        obj._bk_rng = _random.Random(int(backup_loss_seed))
        return obj

    # ---- 在线任务变更：随主回传可达性增量发布现场义务视图（doc38 §3）----
    def _install_mission_segment(self, seg) -> None:
        remove, add = self._mission_gate.segment_ops(seg)
        for o in remove:
            lst = self._obl_index.get((o.node_id, o.measurand))
            if lst and o in lst:
                lst.remove(o)
        for o in add:
            self._obl_index.setdefault((o.node_id, o.measurand), []).append(o)

    def _pump_mission(self, t_s: int) -> None:
        """已生效且此刻主回传可达的任务表更新发布到网关；gate=None 时零行为（锚点不变）。"""
        if self._mission_gate is None:
            return
        for seg in self._mission_gate.poll(t_s, lambda h: self.path_available(h, 0)):
            self._install_mission_segment(seg)

    # ---- 单条 item 的**净荷**字节（不含包头；一个备用包只计一次固定头）----
    def _item_payload_bytes(self, item: GatewayItem) -> int:
        payload = item.payload or []
        if payload:
            return sum(self.sample_bytes.get(getattr(s, "measurand", "displacement"), 6)
                       for s in payload)
        return len(item.sample_ids) * self.sample_bytes["displacement"]

    def _item_deadline(self, item: GatewayItem) -> int:
        """item 内最急样本对应的（公开）义务截止期 (k+2)*period；无样本则退化为 heard+2period。"""
        taken = [getattr(s, "taken_at", item.heard_at_s) for s in (item.payload or [])]
        t0 = min(taken) if taken else item.heard_at_s
        k = t0 // self.period_s
        return (k + 2) * self.period_s

    def _backup_order(self, items: list[GatewayItem]) -> list[GatewayItem]:
        if self.backup_chooser == "fifo":
            return sorted(items, key=lambda i: (i.heard_at_s, i.node_id))
        if self.backup_chooser == "latest":
            return sorted(items, key=lambda i: (-i.heard_at_s, i.node_id))
        # 默认 EDF：义务截止期早者优先，其次先到网关者
        return sorted(items, key=lambda i: (self._item_deadline(i), i.heard_at_s, i.node_id))

    def _sample_obl(self, s):
        """样本能满足的最紧义务 `(deadline, 代表oid, 全部匹配oid集合)`；无台账则退化为周期公式。"""
        lst = self._obl_index.get((s.node_id, s.measurand))
        if not lst:
            k = s.taken_at // self.period_s
            d = (k + 2) * self.period_s
            return d, None, frozenset()
        matched = [o for o in lst if o.matches(s)]
        if not matched:
            k = s.taken_at // self.period_s
            d = (k + 2) * self.period_s
            return d, None, frozenset()
        dl = min(o.deadline for o in matched)
        oids = frozenset(o.oid for o in matched)
        return dl, min(oids), oids

    # ---- 统一的 cover 族装包引擎(R20 修复:所有变体真正可达、可单测)----
    def _cover_family_pack(self, stream, t_s, cap):
        """返回 (picked_of, used_bytes)。stream 元素=(sk,it,s,okeys)。
        cover         : 跨包 seen + 层0覆盖广度(disjoint纯新增,dl升序) + 层1最新优先补满
        cover_l0only  : 跨包 seen + 仅层0(关闭层1)
        cover_local   : 层0但 seen 每包重置(消融跨包全局记忆) + 层1
        cover2        : 跨包 seen + 层0 + 严格层1(不补纯冗余)
        maxcov        : 教科书 maxcov-recency:阶段1按每字节边际新增有效义务覆盖贪心
                        (包内每选一个重算,期限打破平局),阶段2最新优先补满,不停发
        """
        v = self.backup_chooser
        E = []
        for _sk, it, sx, ok in stream:
            b = self.sample_bytes.get(getattr(sx, "measurand", "displacement"), 6)
            dl, _, _ = self._sample_obl(sx)
            E.append({"it": it, "s": sx, "ok": set(ok), "b": b, "dl": dl, "heard": it.heard_at_s})
        picked = {}
        used = 0

        def chosen_ids():
            return {sx.sample_id for _, sp in picked.values() for sx in sp}

        def take(e):
            nonlocal used
            if used > 0 and used + e["b"] > cap:
                return False
            picked.setdefault(id(e["it"]), (e["it"], []))[1].append(e["s"])
            used += e["b"]
            return True

        seen = set(self._cover_seen) if v != "cover_local" else set()

        if v == "maxcov":
            # 阶段1: 反复选 边际新增有效义务覆盖/字节 最大者; tie=期限早, 再 tie=更新
            while True:
                best, bk = None, None
                for e in E:
                    if e["s"].sample_id in chosen_ids():
                        continue
                    if used > 0 and used + e["b"] > cap:
                        continue
                    fresh = [o for o in e["ok"] if o not in seen] if e["dl"] > t_s else []
                    if not fresh:
                        continue
                    key = (-len(fresh) / e["b"], e["dl"], -e["heard"])
                    if bk is None or key < bk:
                        bk, best = key, e
                if best is None:
                    break
                if take(best):
                    seen |= best["ok"]
            # 阶段2: 剩余容量最新优先补满(不因无新覆盖停发)
            for e in sorted((e for e in E if e["s"].sample_id not in chosen_ids()),
                            key=lambda e: (-e["heard"], e["dl"])):
                take(e)
        else:
            # 层0: 纯新增(义务与 seen 不相交)且仍可挽救(dl>t), dl 升序
            def _fresh0(e):
                return (e["dl"] > t_s) and (not e["ok"] or e["ok"].isdisjoint(seen))
            for e in sorted(E, key=lambda e: (e["dl"], e["heard"])):
                if not _fresh0(e):
                    continue                      # 循环内用最新 seen 动态重判 disjoint
                if take(e):
                    seen |= e["ok"]
            # 层1: 样本时效
            if v in ("cover", "cover_local", "cover2"):
                def _l1ok(e):
                    if e["s"].sample_id in chosen_ids():
                        return False
                    if v == "cover2" and e["ok"] and not (e["ok"] - seen):
                        return False          # 严格层1: 纯冗余不补
                    return True
                for e in sorted((e for e in E if _l1ok(e)),
                                key=lambda e: (-e["heard"], e["dl"])):
                    take(e)
            # cover_l0only: 无层1
        if v != "cover_local":
            self._cover_seen |= seen
        return picked, used

    # ---- 关键覆写：主回传之后，在同一拍叠加备用腿 ----
    def backhaul_forward(self, t_s: int, delay_s: int = 0) -> list[GatewayItem]:
        self._pump_mission(t_s)   # 在线任务表更新随主回传可达性到达（默认 gate=None，零行为）
        primary = super().backhaul_forward(t_s, delay_s)   # 主路 down 时为 []，且保留 pending
        if primary:
            self.last_primary_ok_at = t_s                  # 主路专属成功（备用不计入）
        if not self.enable_backup or t_s % self.backup_rate_s != 0:
            return primary
        # delay 未到的项本轮两种路径都不可发，与父类口径一致
        candidates = [i for i in self.gateway_pending
                      if t_s - i.heard_at_s >= delay_s]
        if not candidates:
            return primary
        if self.backup_failover and self.backhaul_available(int(t_s // 3600)):
            # 双模自动切换：主路 up 时不启用备用（贴合 §5.3.7 场景与厂商实配）
            self.backup_gated += 1
            return primary
        self.backup_opportunities += 1
        cap = self.backup_bytes - self.backup_header_bytes   # 净荷容量（整包只一个固定头）
        # 展开为**跨节点样本流**：obligation 档按真实义务截止期全局排序（event 600s 自然先于
        # routine ~2h）；edf 档保留 item 级周期公式，作为"不看真实义务"的消融对照。
        stream = []
        for it in candidates:
            item_dl = self._item_deadline(it)
            for s in (it.payload or []):
                dl, _, okeys = self._sample_obl(s)
                # salvage: 已过义务截止、再发也无法按期交付的样本不占稀缺包位
                if self.backup_chooser == "salvage" and dl <= t_s:
                    self.backup_suppressed += 1
                    continue
                if self.backup_chooser in ("obligation", "salvage"):
                    sk = (dl, it.heard_at_s, it.node_id)
                elif self.backup_chooser == "fifo":
                    sk = (it.heard_at_s, dl, it.node_id)
                elif self.backup_chooser == "latest":
                    sk = (-it.heard_at_s, dl, it.node_id)
                else:
                    sk = (item_dl, it.heard_at_s, it.node_id)
                stream.append((sk, it, s, okeys))
        stream.sort(key=lambda x: x[0])
        _COVER_FAMILY = ("cover", "cover_l0only", "cover_local", "cover2", "maxcov")
        if self.backup_chooser in _COVER_FAMILY:
            picked_of, used = self._cover_family_pack(stream, t_s, cap)
        else:
            picked_of: dict[int, tuple[GatewayItem, list]] = {}
            used = 0
            for _, it, s, okeys in stream:
                # 冗余抑制：该样本能满足的义务都已用备用送过合格样本，就不再占稀缺窗口
                if (self.backup_chooser in ("obligation", "salvage") and self.suppress_duplicates
                        and okeys and (self._backed_obl_keys & okeys)):
                    self.backup_suppressed += 1
                    continue
                b = self.sample_bytes.get(getattr(s, "measurand", "displacement"), 6)
                if used > 0 and used + b > cap:
                    continue                            # 这条装不下，试后面更小的（4B 雨量）
                picked_of.setdefault(id(it), (it, []))[1].append(s)
                used += b
                if self.backup_chooser in ("obligation", "salvage") and okeys:
                    self._backed_obl_keys |= okeys
            if used == 0:
                empty = [it for it in candidates if not it.payload]
                if not empty:
                    return primary                      # 积压全是已备过的冗余：不发空包、省资费
                it = empty[0]
                picked_of = {id(it): (it, [])}
                used = self._item_payload_bytes(it)
        out, remain = [], []
        for it in self.gateway_pending:
            entry = picked_of.get(id(it))
            if entry is None:
                remain.append(it)
                continue
            _, picked_samples = entry
            picked_ids = [s.sample_id for s in picked_samples]
            picked_set = set(picked_ids)
            out.append(GatewayItem(node_id=it.node_id, heard_at_s=it.heard_at_s,
                                   sample_ids=tuple(picked_ids),
                                   payload=list(picked_samples),
                                   snapshot=it.snapshot, kind="backup"))
            rem_ids = [sid for sid in it.sample_ids if sid not in picked_set]
            if rem_ids:                      # 只发出一部分：源 item 缩成剩余子集，留在积压
                it.sample_ids = tuple(rem_ids)
                if it.payload:
                    pset = picked_set
                    it.payload = [s for s in it.payload if s.sample_id not in pset]
                remain.append(it)
        self.gateway_pending = remain
        self.backup_packets += 1
        self.backup_bytes_sent += used + self.backup_header_bytes
        # 可选整包丢包(默认1.0不抽签、逐位锚点不变):整包以 p_succ 到达;失败则样本已移出 pending、
        # 资费照计但不进 out(不重传;对各 chooser 同等施加)。
        if self.backup_p_succ < 1.0 and self._bk_rng.random() > self.backup_p_succ:
            out = []
        else:
            self.backup_records += sum(len(sp) for _, sp in picked_of.values())
        return primary + out

    def backup_summary(self) -> dict:
        return {"backup_opportunities": self.backup_opportunities,
                "backup_gated": self.backup_gated, "backup_packets": self.backup_packets,
                "backup_records": self.backup_records, "backup_bytes_sent": self.backup_bytes_sent,
                "backup_suppressed": self.backup_suppressed,
                "backup_rate_s": self.backup_rate_s, "backup_bytes": self.backup_bytes,
                "backup_chooser": self.backup_chooser, "backup_failover": self.backup_failover}
