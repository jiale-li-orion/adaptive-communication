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
                       displacement_series, hetero_harvest, solar_harvest,
                       irradiance_harvest,
                       rule_obligations_for_truth, routine_obligations_by_node,
                       piecewise_routine_obligations,
                       wang_fragment_truth)
from center import SocObservationModel, build_policy          # noqa: E402
from network import DeviceProfile, Instance, nodes_from       # noqa: E402
from scoring import evaluate                                  # noqa: E402
from joint_plane import JointControlPlane                     # noqa: E402
from joint_policy import DeliveryOpportunisticPolicy, GatewayObserver  # noqa: E402
from obligation_policy import ObligationDeliveryPolicy  # noqa: E402
from mission_policy import MissionChangePolicy  # noqa: E402
from mission_view import MissionViewGate  # noqa: E402


def run_joint(seed: int = 0, task_hours: int = 12, tail_hours: int = 1,
              arm: str = "local", groups: int = 2, per_group: int | None = None,
              sample_interval_s: int = 3600, report_period_s: int = 3600,
              routine_period_s: int = 3600, event_spacing_s: int = 300,
              harvest_wh_per_hour: float = 3.0, capacity_wh: float = 0.05,
              initial_soc: float = 1.0, harvest_mode: str = "uniform",
              harvest_peak_wh_per_hour: float = 0.06,
              blackout_frac: float = 0.0, blackout_start_h: float = 0.0,
              low_frac: float = 0.4, low_wh_per_hour: float = 0.005,
              uplink_p_arrive: float = 0.74, backhaul_p_good: float = 0.62,
              burst_p_gb: float | None = None, burst_p_bg: float | None = None,
              outage_start_h: float | None = None, outage_hours: float = 0.0,
              access_outage_start_h: float = 4.0, access_outage_hours: float = 0.0,
              # ---- 备用腿 ----
              enable_backup: bool = True, backup_rate_s: int = 120,
              backup_bytes: int = 200, backup_header_bytes: int = 20,
              backup_chooser: str = "edf", backup_failover: bool = True,
              backup_suppress: bool = True,
              backup_p_succ: float = 1.0,
              cup_use_window: bool = True, cup_lead_s: int = 900, cup_gate_sampling: bool = True,
              odp_gate_sampling: bool = True, odp_use_backup_phase: bool = True,
              trace: bool = False,
              collect_rows: bool = False, placement: str = "center",
              # ---- 顺序2: 外生授权任务变更(doc35) ----
              mission_schedule=None, mission_mode: str | None = None,
              mission_scope=None, mission_healthy_wh: float = 0.010):
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
    if harvest_mode == "solar":
        harvest, temp = solar_harvest(
            nodes.keys(), int(hours), seed, peak_wh_per_hour=harvest_peak_wh_per_hour)
    elif harvest_mode == "irradiance":
        harvest, temp = irradiance_harvest(
            nodes.keys(), int(hours), seed, peak_wh_per_hour=harvest_peak_wh_per_hour)
    elif harvest_mode == "hetero":
        harvest, temp = hetero_harvest(
            nodes.keys(), int(hours), seed, low_frac=low_frac,
            low_wh_per_hour=low_wh_per_hour, high_wh_per_hour=harvest_wh_per_hour)
    else:
        harvest, temp = constant_harvest(nodes.keys(), int(hours), harvest_wh_per_hour, 10.0)
    if blackout_frac > 0.0:
        from deterministic import stable_uniform as _su
        for nid in nodes:
            if _su(seed, "blackout", nid) < blackout_frac:
                cut = int(blackout_start_h * 3600)
                for tt in harvest[nid]:
                    if tt >= cut:
                        harvest[nid][tt] = 0.0
    truth.harvest_wh.update(harvest)
    truth.temp_c.update(temp)

    meas = {k: v.measurand for k, v in nodes.items()}
    if mission_schedule is not None:
        # 在线变更新任务采用半开窗口独立观测语义(doc38 §4); 单段无变更回退闭区间, 与旧版一致。
        obs = piecewise_routine_obligations(
            meas, int(task_hours), mission_schedule,
            half_open_after_first=len(mission_schedule) >= 2)
    else:
        obs = routine_obligations_by_node(meas, int(task_hours), period_s=routine_period_s)
    obs = obs + rule_obligations_for_truth(truth, spacing_s=event_spacing_s)
    obligations = ObligationSet(obs)

    # 在线新增授权(doc38 §3): 多段 schedule 时现场网关义务视图随任务表更新穿过主回传到达而增量
    # 发布; 单段/固定任务 gate=None, 与旧版逐位一致。独立 scorer 始终持 obligations 全集真值。
    mission_gate = None
    if mission_schedule is not None and len(mission_schedule) >= 2:
        mission_gate = MissionViewGate(meas, int(task_hours), mission_schedule)

    cup_observer = None
    if mission_mode is not None:
        pol = MissionChangePolicy(mission_schedule, mode=mission_mode, scope=mission_scope,
                                  healthy_wh=mission_healthy_wh)
        placement = "center"
    elif arm == "cup":
        cup_observer = GatewayObserver(backup_rate_s=backup_rate_s,
                                       enable_backup=enable_backup)
        pol = DeliveryOpportunisticPolicy(
            cup_observer, period_s=routine_period_s, lead_s=cup_lead_s,
            use_backup_window=cup_use_window, gate_sampling=cup_gate_sampling)
        placement = "gateway"          # C-up 必须在网关位置才能读到网关本地观测
    elif arm == "odp":
        # R04 正确实例化：义务-交付联合策略（最老未完成义务+绝对截止+三态），网关位置
        cup_observer = GatewayObserver(backup_rate_s=backup_rate_s,
                                       enable_backup=enable_backup)
        pol = ObligationDeliveryPolicy(cup_observer, period_s=routine_period_s,
                                       lead_s=cup_lead_s,
                                       gate_sampling=odp_gate_sampling,
                                       use_backup_phase=odp_use_backup_phase)
        placement = "gateway"
    elif arm == "ea_aoi_gw":
        # 机制归因：与 ea_aoi 同一条策略，仅放置到网关——其 AoI 自动改用"网关听到"而非"中心收到"
        pol = build_policy("ea_aoi")
        placement = "gateway"
    else:
        pol = build_policy(arm)
    acc = None
    if access_outage_hours > 0:
        acc = (int(access_outage_start_h * 3600),
               int((access_outage_start_h + access_outage_hours) * 3600))
    inst = Instance(nodes, truth, seed=seed, policy=pol, access_outage=acc,
                    burst_p_gb=burst_p_gb, burst_p_bg=burst_p_bg,
                    placement=placement, trace=trace)
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
        obligations=obligations, suppress_duplicates=backup_suppress,
        backup_p_succ=backup_p_succ, backup_loss_seed=seed,
        mission_gate=mission_gate)
    if cup_observer is not None:
        cup_observer.plane = inst.plane       # 绑定后策略才能读主路状态/备用相位

    log = inst.run(int(hours))
    res = evaluate(obligations, log, int(hours), nodes.keys(),
                   battery={k: v.power.to_dict() for k, v in nodes.items()},
                   plane=inst.plane, task_hours=int(task_hours), outage=outage,
                   collect_rows=collect_rows)
    res["backup"] = inst.plane.backup_summary()
    res["deployment"] = dep.summary()
    res["command_counters"] = dict(inst.counters)
    if mission_mode is not None:
        res["mission_refusals"] = [
            {"node": n, "req_period_s": rq, "at_s": t, "soc_wh": soc}
            for (n, rq, t, soc) in pol.refusals]
    if mission_gate is not None:
        res["mission_timing"] = mission_gate.timing()
    res["survival"] = {
        "alive": sum(1 for n in nodes.values() if getattr(n, "alive", True)),
        "n": len(nodes),
        "mean_final_soc": round(sum(n.soc_wh for n in nodes.values())
                                / (len(nodes) * prof.capacity_wh), 4),
        "dead": sorted(nid for nid, n in nodes.items() if not getattr(n, "alive", True)),
    }
    return res, inst, obligations


if __name__ == "__main__":
    # 冒烟：S1 五台、回传中断，local 关/开备用对比
    for en in (False, True):
        r, _, _ = run_joint(seed=0, groups=1, per_group=4, arm="local",
                            outage_start_h=4.0, outage_hours=4.0, enable_backup=en)
        print(f"backup={en}: routine={r['routine']['delivered']}/{r['routine']['n']} "
              f"backup={r['backup'] if en else '-'}")
