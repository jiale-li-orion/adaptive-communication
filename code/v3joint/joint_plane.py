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
              grace_s: int = 3600, sample_bytes: dict | None = None) -> "JointControlPlane":
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
        # 备用腿账本（尝试/发出，全部可审计）
        obj.backup_opportunities = 0     # 到达备用发送节拍且有积压的次数
        obj.backup_gated = 0             # failover 下因主路 up 而未启用的次数
        obj.backup_packets = 0           # 实际发出的非具备用包数
        obj.backup_records = 0           # 经备用送达中心的样本数
        obj.backup_bytes_sent = 0        # 经备用发出的估算字节
        return obj

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

    # ---- 关键覆写：主回传之后，在同一拍叠加备用腿 ----
    def backhaul_forward(self, t_s: int, delay_s: int = 0) -> list[GatewayItem]:
        primary = super().backhaul_forward(t_s, delay_s)   # 主路 down 时为 []，且保留 pending
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
        ordered = self._backup_order(candidates)
        cap = self.backup_bytes - self.backup_header_bytes   # 净荷容量（整包只一个固定头）
        # **样本粒度重装**：RDSS 是网关重新打包，不必保持接入段批次；一个备用包按 EDF/FIFO 顺序
        # 贪心装样本到容量满。记录每个源 item 被挑走的样本，未挑完的 item 缩成剩余子集留下次。
        picked_of: dict[int, tuple[GatewayItem, list]] = {}
        used = 0
        done = False
        for it in ordered:
            payload = it.payload or []
            for s in payload:
                b = self.sample_bytes.get(getattr(s, "measurand", "displacement"), 6)
                if used > 0 and used + b > cap:
                    done = True
                    break
                picked_of.setdefault(id(it), (it, []))[1].append(s)
                used += b
            if done:
                break
        if used == 0:        # 兜底：payload 缺失时退化为整 item（至少推进一条）
            it = ordered[0]
            picked_of = {id(it): (it, list(it.payload or []))}
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
        self.backup_records += sum(len(sp) for _, sp in picked_of.values())
        self.backup_bytes_sent += used + self.backup_header_bytes
        return primary + out

    def backup_summary(self) -> dict:
        return {"backup_opportunities": self.backup_opportunities,
                "backup_gated": self.backup_gated, "backup_packets": self.backup_packets,
                "backup_records": self.backup_records, "backup_bytes_sent": self.backup_bytes_sent,
                "backup_rate_s": self.backup_rate_s, "backup_bytes": self.backup_bytes,
                "backup_chooser": self.backup_chooser, "backup_failover": self.backup_failover}
