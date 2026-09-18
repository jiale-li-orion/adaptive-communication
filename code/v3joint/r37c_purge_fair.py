# -*- coding: utf-8 -*-
"""r37c — cert_purge 增益的**公平性归因**(零 LLM)。

r37 发现 cert_purge(网关本地核销确定失约样本, 释放节点 FIFO 重传) 把中断 on-time 202->420、
svc .4001->.4302。但节点侧**本就有**义务感知重传纪律(cache_service=obligation_greedy/edf/
latest_only, network.py Node.batch), 它们"旧记录不占这次机会/只留最新"。若普通节点纪律已能
拿到同等增益, 则增益应归普通边缘队列管理, 不是证书机制独有(doc38: 普通自动化能覆盖的如实归它)。

本脚本在同主口径下跑 chooser x cache_service 网格:
  maxcov       x fifo / obligation_greedy / edf / latest_only
  cert_purge   x fifo / obligation_greedy
判读:
  - 若 maxcov+obligation_greedy ~= cert_purge+fifo : 增益=普通节点义务纪律, 证书无净增量;
  - 若 cert_purge 仍更高 : 增量来自网关跨节点/真实义务台账驱动的核销(节点只知公开节奏)。
cache_service 默认 fifo(主口径), 仅本脚本显式改; 不改任何默认值。
"""
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
import r37_conformance as r37
from joint_run import run_joint


def run_one2(chooser, cache_service):
    return run_joint(backup_chooser=chooser, cache_service=cache_service, **r37.COMMON)


def main():
    grid = [
        ("maxcov", "fifo"),
        ("maxcov", "deadline_purge"),
        ("maxcov", "obligation_greedy"),
        ("maxcov", "latest_only"),
        ("cert_purge", "fifo"),
        ("cert_purge", "deadline_purge"),
    ]
    print("== r37c cert_purge 公平归因: chooser x 节点队列纪律 (同主口径, 零 LLM) ==")
    hdr = f"{'chooser':<12}{'queue':<18}{'svc':>8}{'中断deliv':>9}{'备份on':>8}{'过期':>6}{'包':>5}{'字节':>7}{'核销':>6}{'prec':>7}"
    print(hdr)
    for chooser, cs in grid:
        r, inst, obl = run_one2(chooser, cs)
        Z = r37.audit(f"{chooser}+{cs}", r, inst, obl)
        prec = Z["on"] / max(1, Z["on"] + Z["late"])
        print(f"{chooser:<12}{cs:<18}{Z['svc']:>8.4f}{Z['d']:>9}{Z['on']:>8}{Z['late']:>6}"
              f"{Z['packets']:>5}{Z['bytes']:>7}{Z['local_purge']:>6}{prec:>7.3f}")


if __name__ == "__main__":
    main()
