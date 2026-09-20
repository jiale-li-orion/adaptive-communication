# -*- coding: utf-8 -*-
"""rerun_original_matrix.py — 按修正前的语义重跑原主表，还原被覆盖的 results/c5_matrix.json。

修正前语义 = 无容量截断的预测账本 + tracked `MissionViewGate`（全部臂，不区分信息条件）。
本脚本把这两处换回去，其余一律不动，然后调用原封不动的 `c5_matrix.main()`。

它同时充当修正的对照：还原结果与本轮 review/ 下记录的原始读数逐格比对，即可确认修正只动了
我们声称动的那两处，没有夹带。

用法：python3 rerun_original_matrix.py        # 写回 results/c5_matrix.json
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for d in ("v3joint", "instance", "physics", "runtime", "experiments", "analysis", "monitoring"):
    p = os.path.join(ROOT, "code", d)
    if p not in sys.path:
        sys.path.insert(0, p)
sys.path.insert(0, HERE)

import mission_view            # noqa: E402
import c5_common as c          # noqa: E402
import c5_matrix as m          # noqa: E402  （导入即装好 c5_gate 分派）
import c5_gate                 # noqa: E402


def _uncapped(soc0, t0, dense_until, peak_eff, reserve_wh, task_end_s):
    """修正前的账本：`soc0 + cumsum(harv - load)`，没有容量上界。"""
    n = max(0, (task_end_s - t0 + c.TICK - 1) // c.TICK)
    if n == 0:
        return soc0, soc0
    _, harv, load = c._ledger_terms(t0, dense_until, peak_eff, n)
    soc = soc0 + np.cumsum(harv - load)
    return float(soc.min()), float(soc[-1])


class _TrackedGateDispatch:
    """无视 MODE，一律给 tracked 门，即修正前所有臂共用的那一个。"""

    def __new__(cls, *args, **kwargs):
        return mission_view.MissionViewGate(*args, **kwargs)


def main() -> int:
    c._rollout_min = _uncapped
    c5_gate._Dispatch = _TrackedGateDispatch
    import joint_run
    joint_run.MissionViewGate = _TrackedGateDispatch
    print("== 原语义复跑：无截断账本 + tracked 门（不区分信息条件）==", flush=True)
    m.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
