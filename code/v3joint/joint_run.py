#!/usr/bin/env python3
"""joint_run.py — 配置—发送联合控制的一次运行装配（v3joint）。

与 v1.1 `experiments/instance_run.one_seed` **逐段对齐**同样的设备/外生/义务/能量装配，唯一差别：
  1. 暴露 `groups/per_group`，可跑 S1 五台最小单元（one_seed 写死 groups=2）；
  2. 在中断门/链路概率都设好之后，把 `inst.plane` 用 :class:`JointControlPlane.adopt` 接管，
     叠加网关级备用回传腿；
  3. `enable_backup=False` 时**必须**与 one_seed 同参结果逐位一致（见 test_joint.py 锚点）。

本文件不做策略比较、不落盘，只提供 `run_joint(...) -> (res, inst, obligations)`。
"""
from __future__ import annotations

import os as _os, sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime", "experiments",
                                                      "analysis", "monitoring", "instance"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

from deployment import build_deployment                       # noqa: E402
from exogenous import (ObligationSet, constant_harvest,      # noqa: E402
                       displacement_series,
                       rule_obligations_for_truth, routine_obligations_by_node,
                       wang_fragment_truth)
from center import SocObservationModel, build_policy          # noqa: E402
from network import DeviceProfile, Instance, nodes_from       # noqa: E402
from scoring import evaluate                                  # noqa: E402
from joint_plane import JointControlPlane                     # noqa: E402


def run_joint(seed: int = 0, task_hours: int = 12, tail_hours: int = 1,
              arm: str = "local", groups: int = 2, per_group: int | None = None,
              sample_interval_s: int = 3600, report_period_s: int = 3600,
              routine_period_s: int = 3600, event_spacing_s: int = 300,
              harvest_wh_per_hour: float = 3.0, capacity_wh: float = 0.05,
              initial_soc: float = 1.0,
              uplink_p_arrive: float = 0.74, backhaul_p_good: float = 0.62,
              burst_p_gb: float | None = None, burst_p_bg: float | None = None,
              outage_start_h: float | None = None, outage_hours: float = 0.0,
              access_outage_start_h: float = 4.0, access_outage_hours: float = 0.0,
              # ---- 备用腿 ----
              enable_backup: bool = True, backup_rate_s: int = 120,
              backup_bytes: int = 200, backup_header_bytes: int = 20,
              backup_chooser: str = "edf", backup_failover: bool = True,
              backup_suppress: bool = True,
              collect_rows: bool = False, placement: str = "center"):
    hours = task_hours + tail_hours
    dep = build_deployment(groups=groups, per_group=per_group)
    prof = DeviceProfile(sample_interval_s=sample_interval_s,
                         report_period_s=report_period_s,
                         event_interval_s=event_spacing_s,
                         capacity_wh=capacity_wh, initial_soc=initial_soc,
                         charge_min_c=5.0, cache_service="fifo",
                         obligation_period_s=routine_period_s,
                         idle_wh_per_tick=0.0,
                         sample_wh=DeviceProfile().sample_wh)
    nodes = nodes_from(dep, profile=prof)
    truth = wang_fragment_truth(0, int(hours), (dep.gateway.sid,))
    truth.displacement = displacement_series(nodes.keys(), int(hours), seed)
    harvest, temp = constant_harvest(nodes.keys(), int(hours), harvest_wh_per_hour, 10.0)
    truth.harvest_wh.update(harvest)
    truth.temp_c.update(temp)

    meas = {k: v.measurand for k, v in nodes.items()}
    obs = routine_obligations_by_node(meas, int(task_hours), period_s=routine_period_s)
    obs = obs + rule_obligations_for_truth(truth, spacing_s=event_spacing_s)
    obligations = ObligationSet(obs)

    pol = build_policy(arm)
    acc = None
    if access_outage_hours > 0:
        acc = (int(access_outage_start_h * 3600),
               int((access_outage_start_h + access_outage_hours) * 3600))
    inst = Instance(nodes, truth, seed=seed, policy=pol, access_outage=acc,
                    burst_p_gb=burst_p_gb, burst_p_bg=burst_p_bg, placement=placement)
    inst.plane.uplink_p_arrive = uplink_p_arrive
    inst.plane.backhaul_p_good = backhaul_p_good
    for pth in inst.plane.paths:
        object.__setattr__(pth, "p_good", backhaul_p_good)
    outage = None
    if outage_hours > 0:
        lo, hi = int(outage_start_h), int(outage_start_h + outage_hours)
        inst.plane.backhaul_gate = lambda hour, _lo=lo, _hi=hi: not (_lo <= hour < _hi)
        outage = (lo * 3600, hi * 3600)
    inst.soc_model = SocObservationModel(max_age_s=None, noise_wh=0.0, bias=1.0,
                                         loss_p=0.0, seed=seed)

    # 备用面在链路/中断门全部设好之后接管，复制全部既有状态。
    inst.plane = JointControlPlane.adopt(
        inst.plane, enable_backup=enable_backup, backup_rate_s=backup_rate_s,
        backup_bytes=backup_bytes, backup_header_bytes=backup_header_bytes,
        chooser=backup_chooser, failover=backup_failover,
        obligation_period_s=routine_period_s, grace_s=routine_period_s,
        obligations=obligations, suppress_duplicates=backup_suppress)

    log = inst.run(int(hours))
    res = evaluate(obligations, log, int(hours), nodes.keys(),
                   battery={k: v.power.to_dict() for k, v in nodes.items()},
                   plane=inst.plane, task_hours=int(task_hours), outage=outage,
                   collect_rows=collect_rows)
    res["backup"] = inst.plane.backup_summary()
    res["deployment"] = dep.summary()
    res["command_counters"] = dict(inst.counters)
    return res, inst, obligations


if __name__ == "__main__":
    # 冒烟：S1 五台、回传中断，local 关/开备用对比
    for en in (False, True):
        r, _, _ = run_joint(seed=0, groups=1, per_group=4, arm="local",
                            outage_start_h=4.0, outage_hours=4.0, enable_backup=en)
        print(f"backup={en}: routine={r['routine']['delivered']}/{r['routine']['n']} "
              f"backup={r['backup'] if en else '-'}")
