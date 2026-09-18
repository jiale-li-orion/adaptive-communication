# -*- coding: utf-8 -*-
"""r37d — deadline_purge 机制的**留出 seed 稳健性**(零 LLM)。

r37c 在开发 seed0 上: maxcov+deadline_purge 相对 maxcov+fifo 中断 on-time 202->434、
全时段 svc .4001->.4321、过期 219->0。本脚本用**留出 seed 6/7/8**(开发用 0-5)验证方向稳定,
排除单 seed 偶发。每 seed 跑 maxcov x {fifo, deadline_purge, latest_only(参照)}, 报 svc/中断d。
"""
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
import r37_conformance as r37
from joint_run import run_joint

BASE = {k: v for k, v in r37.COMMON.items() if k != "seed"}


def run(seed, cs):
    return run_joint(seed=seed, backup_chooser="maxcov", cache_service=cs, **BASE)


def main():
    print("== r37d 留出 seed 稳健性 (maxcov x 队列纪律, seed 6/7/8 留出) ==")
    print(f"{'seed':>5}{'queue':<16}{'svc':>9}{'中断deliv':>10}{'备份on':>8}{'过期':>6}")
    for seed in (6, 7, 8):
        for cs in ("fifo", "deadline_purge", "latest_only"):
            r, inst, obl = run(seed, cs)
            Z = r37.audit(f"s{seed}/{cs}", r, inst, obl)
            print(f"{seed:>5}{cs:<16}{Z['svc']:>9.4f}{Z['d']:>10}{Z['on']:>8}{Z['late']:>6}")
        print()


if __name__ == "__main__":
    main()
