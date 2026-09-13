#!/usr/bin/env python3
"""实例读数：多节点、真实地形下的分列结果。

这是实例层**唯一**的读数脚本。它不做方法比较，只把当前实例在多个种子下的分列指标落盘，
让"这些数从哪里来"可复现（D29）。

```bash
export PYTHONPATH="$PWD/libs/pylibs"
python3 code/experiments/instance_run.py --seeds 20 --task-hours 12 --tail-hours 1 --tag base
```

**这个实例是什么。** 一个监测单元：网关带雨量计 + 13 个坡面位移测点（真实 SRTM/ITM 布点，
绕射边缘上的 3 个位点已排除）。业务事件来自 Wang 等 2022 Table 3 的公开片段（7 组触发）；
常态为 1 h 定时。采能是**合成的恒定过程**（A 层），因此**能源相关读数不得外推**。

**这个实例不是什么。** 不是真实 trace benchmark；不是任何站点的配置；不含中心下发动作。
"""
from __future__ import annotations

import argparse
import json
import os as _os, sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime", "experiments",
                                                      "analysis", "monitoring", "instance"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

from deployment import build_deployment
from exogenous import (ObligationSet, autonomy_margin, constant_harvest,
                       displacement_series, hetero_harvest, irradiance_harvest,
                       solar_harvest,
                       rule_obligations_for_truth, routine_obligations_by_node,
                       wang_fragment_truth)
from center import ARMS, ClairvoyantStaticSelector, SocObservationModel, build_policy
from network import DeviceProfile, Instance, nodes_from
import oracle as _oracle
import opportunity as _opportunity
from oracle import delivery_oracle, dynamic_oracle
from scoring import evaluate

OUT = _os.path.normpath(_os.path.join(_CODE, "..", "results"))


def one_seed(seed: int, task_hours: float, tail_hours: float,
             outage_start_h: float = 0.0, outage_hours: float = 0.0,
             arm: str = "local", contract: bool = False,
             hold_every: int = 0, hold_s: int = 0,
             harvest_wh_per_hour: float = 3.0, sample_interval_s: int = 3600,
             report_period_s: int = 3600, routine_period_s: int = 3600,
             with_events: bool = True, trace: bool = False,
             uplink_p_arrive: float = 0.74, backhaul_p_good: float = 0.62,
             event_spacing_s: int = 300, harvest_mode: str = "uniform",
             access_outage_h: float = 0.0, access_outage_start_h: float = 4.0,
             blackout_start_h: float = 0.0,
             blackout_frac: float = 0.0,
             soc_max_age_s: int | None = None, soc_noise_wh: float = 0.0,
             soc_bias: float = 1.0, soc_loss_p: float = 0.0, hold_op: str | None = None,
             atomic: bool = False, exec_label: str | None = None,
             capacity_wh: float = 0.05, low_frac: float = 0.4,
             low_wh_per_hour: float = 0.005,
             oracle_cache: dict | None = None,
             oracle_soc_bins: int = 200,
             solar_day_start_h: float = 6.0, solar_peak_wh_per_hour: float = 0.06,
             solar_cloud_p: float = 0.35, solar_cloud_atten: float = 0.25,
             solar_snow_frac: float = 0.0, solar_snow_start_h: float = 8.0,
             solar_shade_frac: float = 0.0,
             initial_soc: float = 1.0,
             irr_start_h: int = 0, irr_peak_wh_per_hour: float = 0.01,
             irr_shade_frac: float = 0.0, irr_snow_frac: float = 0.0,
             irr_snow_after_h: int = 0, irr_source_temp: bool = True,
             irr_year: int = 2023,
             burst_p_gb: float | None = None, burst_p_bg: float | None = None,
             uplink_burst_p_gb: float | None = None,
             uplink_burst_p_bg: float | None = None,
             charge_min_c: float | None = 5.0,
             idle_wh_per_tick: float = 0.0,
             cache_service: str = "fifo",
             energy_scale: float = 1.0) -> dict:
    hours = task_hours + tail_hours
    dep = build_deployment(groups=2)
    #: `energy_scale` 同时作用于**采样能耗**与**电池容量**（空口母线在 `main` 里按同一 λ 缩放）。
    #: 三者一起缩放才是真正的"把整个能量系统乘以 λ"，否则只是改了比例、不是尺度检验。
    # **`sample_interval_s` 与 `report_period_s` 是两个独立字段**（E：重庆 `0045`/`0042`），
    # 因此两个都要能单独设定。此前 `report_period_s` 只能吃 `DeviceProfile` 的默认值，
    # 于是"换一个业务场景（常态 900 s 上报）"在命令行上根本表达不出来。
    prof = DeviceProfile(sample_interval_s=sample_interval_s,
                         report_period_s=report_period_s,
                         event_interval_s=event_spacing_s,
                         capacity_wh=capacity_wh, initial_soc=initial_soc,
                         charge_min_c=charge_min_c,
                         cache_service=cache_service,
                         idle_wh_per_tick=idle_wh_per_tick * energy_scale,
                         sample_wh=DeviceProfile().sample_wh * energy_scale)
    nodes = nodes_from(dep, profile=prof)
    truth = wang_fragment_truth(0, int(hours), (dep.gateway.sid,))
    truth.displacement = displacement_series(nodes.keys(), int(hours), seed)
    if harvest_mode == "irradiance":
        # **来源派生**：形状取自 NASA POWER 2023 逐小时辐照（E），量级是 A 层换算。
        # 温度默认取来源自带的 `T2M`——这一项会让**低温闸门作用在真实气温上**。
        harvest, temp = irradiance_harvest(
            nodes.keys(), int(hours), seed, start_hour=irr_start_h,
            peak_wh_per_hour=irr_peak_wh_per_hour, shade_frac=irr_shade_frac,
            snow_frac=irr_snow_frac, snow_after_h=irr_snow_after_h,
            source_temp=irr_source_temp, year=irr_year)
    elif harvest_mode == "solar":
        # **合成**日照时间过程（A 层）。形状是研究选择，不是拟合值——结论只能读作
        # "在这个形状下如何"。见 `solar_harvest` 的文档。
        harvest, temp = solar_harvest(
            nodes.keys(), int(hours), seed, day_start_hour=solar_day_start_h,
            peak_wh_per_hour=solar_peak_wh_per_hour, cloud_p=solar_cloud_p,
            cloud_atten=solar_cloud_atten, snow_frac=solar_snow_frac,
            snow_start_h=solar_snow_start_h, shade_frac=solar_shade_frac)
    elif harvest_mode == "hetero":
        harvest, temp = hetero_harvest(nodes.keys(), int(hours), seed,
                                       low_frac=low_frac,
                                       low_wh_per_hour=low_wh_per_hour,
                                       high_wh_per_hour=harvest_wh_per_hour)
    else:
        harvest, temp = constant_harvest(nodes.keys(), int(hours),
                                         harvest_wh_per_hour, 10.0)
    if blackout_frac > 0.0:
        # **节点失电**：从第 `blackout_start_h` 小时起，一部分站点的采能被切断（积雪掩埋、
        # 线路受损）。它们仍会照常采样直到电量耗尽，**然后彻底停止**——因此后果是
        # **采集缺失**，而不是交付缺失。这是与接入/回传中断最本质的区别（v1.1 §5.3）。
        from deterministic import stable_uniform as _su
        for nid in nodes:
            if _su(seed, "blackout", nid) < blackout_frac:
                cut_at = int(blackout_start_h * 3600)
                for tt in harvest[nid]:
                    if tt >= cut_at:
                        harvest[nid][tt] = 0.0

    truth.harvest_wh.update(harvest)
    truth.temp_c.update(temp)

    # **autonomy margin**：把采能轨迹整体缩小到多少倍时，每小时的义务还服务得起。
    # 基准工作负载 = 每小时一条样（`sample_wh + UPLINK_WH`）。1 是天然分界，跨任务可比。
    # **必须与实例用同一个初始电量**，否则这个横轴描述的是另一个系统。`initial_soc=1.0`
    # （满格启动）会让 margin 恒为无穷——初始电量自己就能跑完整个任务时，采能与可行性无关，
    # 那个横轴没有任何信息量。扫 margin 时必须配一个需要采能的初始电量。
    # **无量纲横轴**：初始自主小时数 `A_0 = soc_0 * C / load_h`，
    # 其中 `load_h` 是"每小时的名义负载"，必须把**静息功耗**也算进去——
    # 否则 `idle_wh_per_tick > 0` 时这个横轴就不代表自主时长（实测：idle 会让
    # "停止采样也照样耗电"成为一条新的失效路径）。
    _cost_h = (prof.sample_wh + _oracle.UPLINK_WH
               + 3600.0 * idle_wh_per_tick * energy_scale)
    margins = [autonomy_margin(harvest[nid], int(task_hours),
                               capacity_wh=capacity_wh,
                               initial_wh=initial_soc * capacity_wh,
                               cost_per_hour=_cost_h) for nid in nodes]
    margin_mean = sum(margins) / len(margins) if margins else 0.0
    margin_min = min(margins) if margins else 0.0

    meas = {k: v.measurand for k, v in nodes.items()}
    # **第二业务场景**：`routine_period_s` 是"常态多久要有一条按期记录"，
    # `with_events` 决定要不要叠上 Wang 片段的事件义务。
    # 换场景只动这两个量与设备的两个周期字段，**动作面与基线集合原封不动**。
    _obs = routine_obligations_by_node(meas, int(task_hours),
                                       period_s=routine_period_s)
    if with_events:
        _obs = _obs + rule_obligations_for_truth(truth, spacing_s=event_spacing_s)
    obligations = ObligationSet(_obs)

    # **真上界**：逐节点、逐小时的离线动态规划，读完整未来采能轨迹。它不依赖臂，所以按
    # (种子, 条件) 记忆化——否则每个臂都会重算一遍同一个值。
    oracle_total = None
    if oracle_cache is not None:
        okey = (seed, int(task_hours), capacity_wh, initial_soc, low_frac,
                low_wh_per_hour, harvest_wh_per_hour, harvest_mode, blackout_start_h,
                blackout_frac, event_spacing_s, routine_period_s, with_events,
                solar_day_start_h,
                solar_peak_wh_per_hour, solar_cloud_p, solar_cloud_atten,
                solar_snow_frac, solar_shade_frac, oracle_soc_bins)
        if okey not in oracle_cache:
            # **上界必须与实例用同一个初始电量。** 不传时 `dynamic_oracle` 默认取满容量，于是
            # `--initial-soc 0.2` 的实例被拿去比一个"满格开局"的上界——那仍然是上界（电更多只会
            # 更可行），但它放宽的正好是本轮要扫的那一维，会把 regret 系统性报小。
            oracle_cache[okey] = dynamic_oracle(
                obligations, int(task_hours), truth.harvest_wh, nodes.keys(),
                profile=prof, initial_wh=initial_soc * capacity_wh,
                soc_bins=oracle_soc_bins)["total_oracle"]
        oracle_total = oracle_cache[okey]

    acc = None
    if access_outage_h > 0:
        lo = int(access_outage_start_h * 3600)
        hi = int((access_outage_start_h + access_outage_h) * 3600)
        acc = (lo, hi)
    # 上界参考需要知道哪些站点受约束（遮荫或失电）。它读环境真值，**不是可实现策略**，
    # 只作参照；因此它由 runner 直接构造，不放进 ARMS 供一般调用。
    if arm == "clairvoyant_static":
        # **上界参考必须是真正可行的判据。** 前两版都错了，而且错法本身有信息量：
        #   · 第一版按"历史最大采能"判 → 失电从第 4 h 才切断，被切断的节点看起来仍健康；
        #   · 第二版按"全程采能总和"判 → 0.02 Wh 的电池**存不下** 4 小时采到的 0.2 Wh，
        #     早段电池满了、采能白白溢出，晚段照样饿死。
        # 也就是说：**从静态参数推不出正确的逐节点间隔**——那是一个把采能时序、电池容量与
        # 消耗率耦合起来的动态可行性问题。所以参考必须**逐节点模拟一遍稀疏/加密两条轨迹**，
        # 取可行的那条。这不是"知道参数"，这是"知道参数并且算过"。
        feasible = set()
        for nid in nodes:
            soc = prof.capacity_wh
            ok = True
            for t_s in range(0, int(hours) * 3600, 60):
                soc = min(prof.capacity_wh, soc + harvest.get(nid, {}).get(t_s, 0.0))
                if t_s % 300 == 0:
                    soc -= prof.sample_wh
                if soc <= 0:
                    ok = False
                    break
            if ok:
                feasible.add(nid)
        constrained = frozenset(nid for nid in nodes if nid not in feasible)
        pol = ClairvoyantStaticSelector(constrained)
    else:
        pol = build_policy(arm)
    inst = Instance(nodes, truth, seed=seed, policy=pol,
                    send_contract_fields=contract, hold_every=hold_every,
                    hold_s=hold_s, access_outage=acc, hold_op=hold_op,
                    atomic_generation=atomic,
                    burst_p_gb=burst_p_gb, burst_p_bg=burst_p_bg,
                    uplink_burst_p_gb=uplink_burst_p_gb,
                    uplink_burst_p_bg=uplink_burst_p_bg, trace=trace)
    inst.plane.uplink_p_arrive = uplink_p_arrive
    inst.plane.backhaul_p_good = backhaul_p_good
    for pth in inst.plane.paths:
        object.__setattr__(pth, "p_good", backhaul_p_good)
    outage = None
    if outage_hours > 0:
        # 回传中断窗。`backhaul_gate` 只能让路径更不可用，因此中断不会给任何一方送好处。
        lo, hi = int(outage_start_h), int(outage_start_h + outage_hours)
        inst.plane.backhaul_gate = lambda hour, _lo=lo, _hi=hi: not (_lo <= hour < _hi)
        outage = (lo * 3600, hi * 3600)
    inst.soc_model = SocObservationModel(max_age_s=soc_max_age_s, noise_wh=soc_noise_wh,
                                         bias=soc_bias, loss_p=soc_loss_p, seed=seed)
    log = inst.run(int(hours))
    # **发送侧三分解**：只松弛转发（固定发送时刻）与再松弛"何时发送"（自由发送时刻）。
    _delivery_total = delivery_oracle(obligations, inst.log, int(hours),
                                      plane=inst.plane)["total_oracle"]
    _delivery_free = delivery_oracle(obligations, inst.log, int(hours),
                                     plane=inst.plane,
                                     free_transmit=True)["total_oracle"]
    # 中间上界：**样本必须真的采到过**，只把"什么时候发"交给上界。
    _delivery_mid = delivery_oracle(obligations, inst.log, int(hours),
                                    plane=inst.plane, free_transmit=True,
                                    require_sample=True)["total_oracle"]
    res = evaluate(obligations, log, int(hours), nodes.keys(),
                   battery={k: v.power.to_dict() for k, v in nodes.items()},
                   plane=inst.plane, task_hours=int(task_hours), outage=outage)

    return {
        "seed": seed,
        "arm": arm,
        "exec_layer": exec_label or ("contract" if contract else "naive"),
        "hazard": {"hold_every": hold_every, "hold_s": hold_s},
        "intent_mismatch_s": inst.intent_mismatch_s(int(hours)),
        "mixed_config_s": inst.mixed_config_ticks,
        "dynamic_oracle": oracle_total,
        # **发送调度上界**：同样的样本、同一条实测链路，最多能送到几条。
        "delivery_oracle": _delivery_total,
        "delivery_oracle_free_tx": _delivery_free,
        "delivery_oracle_mid": _delivery_mid,
        "intent_ledger": inst.intent_ledger(),
        "intent_reason": inst.intent_reasons(),
        #: **跳过原因**：这台节点这次为什么没被下发。`plan()` 里四处 `continue` 在日志上
        #: 同形，含义完全不同；不分开记就无法回答"中心为什么不再下发"。
        "skip_reasons": pol.skip_report(),
        "autonomy_margin": margin_mean,
        "autonomy_margin_min": margin_min,
        "command_counters": dict(inst.counters),
        "deployment": dep.summary(),
        "n_obligations": res["n_obligations"],
        "by_kind": res["by_kind"],
        "routine": res["routine"],
        "event": res["event"],
        "energy": res["energy"],
        "communication": res["communication"],
        "propagation": {k: v for k, v in res["propagation"].items() if k != "per_trigger"},
        "recovery": res.get("recovery"),
        "access_blocked": inst.access_blocked,
        "observation_window": res["observation_window"],
        "not_applicable": res["not_applicable"],
        #: **只在 `trace=True` 时非空**。逐事件时间线属于诊断产物，不进结果文件的常规列。
        **({"_trace": inst.trace_events} if trace else {}),
    }


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--task-hours", type=float, default=12.0)
    ap.add_argument("--tail-hours", type=float, default=1.0)
    ap.add_argument("--exec-layers", default="naive",
                    help="逗号分隔：naive(不发契约字段) / contract(发稳定身份与单调版本)")
    ap.add_argument("--hold-every", type=int, default=0,
                    help="每 k 条下发扣留一条；0 表示不扣留")
    ap.add_argument("--hold-s", type=int, default=0)
    ap.add_argument("--hold-op", default=None,
                    help="只扣留某一类字段命令，用于构造跨代混配（例如 set_sampling_interval）")
    ap.add_argument("--harvest-wh-per-hour", type=float, default=0.05)
    ap.add_argument("--harvest-mode", default="uniform",
                    choices=["uniform", "hetero", "solar", "irradiance"])
    ap.add_argument("--capacity-wh", type=float, default=0.05)
    ap.add_argument("--low-frac", type=float, default=0.4)
    ap.add_argument("--low-wh-per-hour", type=float, default=0.005)
    ap.add_argument("--sample-interval-s", type=int, default=3600)
    ap.add_argument("--uplink-p-arrive", type=float, default=0.74)
    ap.add_argument("--backhaul-p-good", type=float, default=0.62)
    ap.add_argument("--event-spacing-s", type=int, default=300)
    ap.add_argument("--arms", default="local",
                    help="逗号分隔的中心策略，见 instance/center.py 的 ARMS")
    ap.add_argument("--soc-max-age-s", type=int, default=None)
    ap.add_argument("--soc-noise-wh", type=float, default=0.0)
    ap.add_argument("--soc-bias", type=float, default=1.0)
    ap.add_argument("--soc-loss-p", type=float, default=0.0)
    ap.add_argument("--blackout-start-h", type=float, default=0.0,
                    help="从第几小时起切断部分站点的采能（节点失电）")
    ap.add_argument("--blackout-frac", type=float, default=0.0)
    ap.add_argument("--access-outage-h", type=float, default=0.0,
                    help="接入中断时长（小时）")
    ap.add_argument("--access-outage-start-h", type=float, default=4.0)
    ap.add_argument("--outage-start-h", type=float, default=0.0)
    ap.add_argument("--outage-hours", type=float, default=0.0)
    ap.add_argument("--dynamic-oracle", action="store_true",
                    help="同时计算真上界（逐节点逐小时离线 DP，读完整未来采能轨迹）")
    ap.add_argument("--oracle-soc-bins", type=int, default=200)
    ap.add_argument("--uplink-burst", default="",
                    help="逐节点两态马尔可夫接入 `p_gb,p_bg`；留空 = 逐分钟 i.i.d.")
    ap.add_argument("--backhaul-burst", default="",
                    help="两态马尔可夫回传 `p_gb,p_bg`；留空 = 逐小时 i.i.d.（原行为）")
    ap.add_argument("--irr-year", type=int, default=2023,
                    choices=[2022, 2023, 2024],
                    help="辐照年份。三年都有；2023 是最冷的一年")
    ap.add_argument("--irr-start-h", type=int, default=0,
                    help="取 2023 年逐小时辐照的起点（小时索引，8760 内回绕）")
    ap.add_argument("--irr-peak-wh-per-hour", type=float, default=0.01)
    ap.add_argument("--irr-shade-frac", type=float, default=0.0)
    ap.add_argument("--irr-snow-frac", type=float, default=0.0)
    ap.add_argument("--irr-snow-after-h", type=int, default=0)
    ap.add_argument("--irr-no-source-temp", action="store_true",
                    help="不用来源气温（改用 10°C 常数）——用于把时序形状与低温闸门分开")
    ap.add_argument("--idle-wh-per-tick", type=float, default=0.0,
                    help="静息功耗（Wh/tick）。默认 0——**这是一个 A 层取值**，见 manifest")
    ap.add_argument("--report-period-s", type=int, default=3600,
                    help="设备本地默认上报周期（s）。**与采样间隔是两个独立字段**")
    ap.add_argument("--routine-period-s", type=int, default=3600,
                    help="常态义务的周期（s）：多久必须有一条按期记录。换业务场景时改它")
    ap.add_argument("--no-events", action="store_true",
                    help="不叠加 Wang 片段的事件义务（第二业务场景没有事件加密时用）")
    ap.add_argument("--charge-min-c", default="5.0",
                    help="低温充电闸门（°C）；`off` 表示不设闸门")
    ap.add_argument("--cache-service", choices=("fifo", "lifo", "latest_only"), default="fifo",
                    help="缓存服务次序：`fifo` 最老优先（设备既有自动补发，默认）；"
                         "`lifo` 最新优先（AoI 文献的标准服务纪律）。"
                         "**这是实例属性，不是策略动作**——换它等于换实例，所有臂必须同值重跑")
    ap.add_argument("--initial-soc", type=float, default=1.0,
                    help="初始电量比例。扫 autonomy margin 时要用小于 1 的值")
    ap.add_argument("--solar-day-start-h", type=float, default=6.0,
                    help="运行起点对应的绝对钟点，决定 12h 窗口落在白天还是夜里")
    ap.add_argument("--solar-peak-wh-per-hour", type=float, default=0.06)
    ap.add_argument("--solar-cloud-p", type=float, default=0.35)
    ap.add_argument("--solar-cloud-atten", type=float, default=0.25)
    ap.add_argument("--solar-snow-frac", type=float, default=0.0)
    ap.add_argument("--solar-snow-start-h", type=float, default=8.0)
    ap.add_argument("--solar-shade-frac", type=float, default=0.0)
    ap.add_argument("--energy-scale", type=float, default=1.0,
                    help="把**整套能量系统**（采样能耗、电池容量、空口母线、采能、上界上行能耗）同时乘以 λ。配合 base 值取 C/λ、H/λ 即可检验尺度不变性")
    ap.add_argument("--tag", default="base")
    args = ap.parse_args()

    # **能量尺度不变性检验。** 把整个能量系统同时乘以 `λ`：采样能耗、电池容量、
    # 空口母线电压（tx 与 rx 都线性跟随）、以及两个上界代价模型里的上行能耗。
    # 若业务列在 `λ` 下**逐位相同**，说明这个实例在能量上是**无量纲**的——
    # 悬崖只活在比值上，绝对 Wh **不是**现实部署数值。
    # 这是 A 层有效性里最要紧的一条：它决定论文该用绝对能量还是无量纲 slack。
    if args.energy_scale != 1.0:
        lam = float(args.energy_scale)
        _ES_SAVED = (_opportunity.BUS_V, _oracle.UPLINK_WH)
        _opportunity.BUS_V = _ES_SAVED[0] * lam
        _oracle.UPLINK_WH = _ES_SAVED[1] * lam

    arm_names = [a.strip() for a in args.arms.split(",") if a.strip()]
    for a in arm_names:
        if a not in ARMS and a != "clairvoyant_static":
            raise SystemExit(f"unknown arm {a!r}; have {sorted(ARMS)} + clairvoyant_static")
    layers = [x.strip() for x in args.exec_layers.split(",") if x.strip()]
    for L in layers:
        if L not in ("naive", "contract", "atomic"):
            raise SystemExit(f"unknown exec layer {L!r}; have naive/contract/atomic")
    _oracle_cache: dict = {}
    runs = [one_seed(s, args.task_hours, args.tail_hours,
                     args.outage_start_h, args.outage_hours, a,
                     contract=(L in ("contract", "atomic")), hold_every=args.hold_every,
                     atomic=(L == "atomic"), exec_label=L,
                     hold_s=args.hold_s, harvest_wh_per_hour=args.harvest_wh_per_hour,
                     sample_interval_s=args.sample_interval_s,
                     report_period_s=args.report_period_s,
                     routine_period_s=args.routine_period_s,
                     with_events=not args.no_events,
                     uplink_p_arrive=args.uplink_p_arrive,
                     backhaul_p_good=args.backhaul_p_good,
                     event_spacing_s=args.event_spacing_s,
                     harvest_mode=args.harvest_mode,
                     capacity_wh=args.capacity_wh * args.energy_scale,
                     energy_scale=args.energy_scale,
                     low_frac=args.low_frac,
                     low_wh_per_hour=args.low_wh_per_hour * args.energy_scale,
                     access_outage_h=args.access_outage_h,
                     access_outage_start_h=args.access_outage_start_h,
                     blackout_start_h=args.blackout_start_h,
                     blackout_frac=args.blackout_frac,
                     soc_max_age_s=args.soc_max_age_s, soc_noise_wh=args.soc_noise_wh,
                     soc_bias=args.soc_bias, soc_loss_p=args.soc_loss_p,
                     hold_op=args.hold_op,
                     oracle_cache=(_oracle_cache if args.dynamic_oracle else None),
                     oracle_soc_bins=args.oracle_soc_bins,
                     solar_day_start_h=args.solar_day_start_h,
                     solar_peak_wh_per_hour=args.solar_peak_wh_per_hour,
                     solar_cloud_p=args.solar_cloud_p,
                     solar_cloud_atten=args.solar_cloud_atten,
                     solar_snow_frac=args.solar_snow_frac,
                     solar_snow_start_h=args.solar_snow_start_h,
                     solar_shade_frac=args.solar_shade_frac,
                     initial_soc=args.initial_soc,
                     irr_start_h=args.irr_start_h,
                     irr_peak_wh_per_hour=args.irr_peak_wh_per_hour * args.energy_scale,
                     irr_shade_frac=args.irr_shade_frac,
                     irr_snow_frac=args.irr_snow_frac,
                     irr_snow_after_h=args.irr_snow_after_h,
                     irr_source_temp=not args.irr_no_source_temp,
                     irr_year=args.irr_year,
                     burst_p_gb=(float(args.backhaul_burst.split(',')[0])
                                 if args.backhaul_burst else None),
                     burst_p_bg=(float(args.backhaul_burst.split(',')[1])
                                 if args.backhaul_burst else None),
                     uplink_burst_p_gb=(float(args.uplink_burst.split(',')[0])
                                        if args.uplink_burst else None),
                     uplink_burst_p_bg=(float(args.uplink_burst.split(',')[1])
                                        if args.uplink_burst else None),
                     charge_min_c=(None if args.charge_min_c == 'off'
                                   else float(args.charge_min_c)),
                     idle_wh_per_tick=args.idle_wh_per_tick,
                     cache_service=args.cache_service)
            for a in arm_names for L in layers for s in range(args.seeds)]

    # 聚合：**按臂分组**。分母类用求和天然是整数，时延与比率类用逐种子均值。
    def agg_of(rs):
        a = {
            "n_seeds": len(rs),
            "routine_delivered": mean([r["routine"]["delivered"] for r in rs]),
            "routine_missing_collection": mean([r["routine"]["missing_collection"] for r in rs]),
            "routine_missing_delivery": mean([r["routine"]["missing_delivery"] for r in rs]),
            "routine_aoi_mean_s": mean([r["routine"]["aoi_mean_s"] for r in rs]),
            # **第二业务场景没有事件义务**（Cleveland Corral 的交付数据里没有事件加密），
            # 于是 `by_kind` 里根本没有 `event` 这一项。这里必须返回 `None` 而不是 0——
            # 0 会被读成"事件全部没送到"，而事实是"这个场景没有事件"。
            "event_match": mean([r["event"]["slots_matched_by_collection"] for r in rs])
            if all("event" in r["by_kind"] for r in rs) else None,
            "event_delivered": mean([r["event"]["slots_delivered"] for r in rs])
            if all("event" in r["by_kind"] for r in rs) else None,
            "event_missing_delivery": mean([r["by_kind"]["event"]["missing_delivery"]
                                            for r in rs])
            if all("event" in r["by_kind"] for r in rs) else None,
            "knowledge_latency_mean_s": mean([r["propagation"]["knowledge_latency_mean_s"]
                                              for r in rs]),
            "uplinks": mean([r["communication"]["uplinks"] for r in rs]),
            "uplinks_heard": mean([r["communication"]["uplinks_heard"] for r in rs]),
            "downlink_attempts": mean([(r["communication"].get("downlink_attempts") or 0)
                                       for r in rs]),
            "commands_sent": mean([r["command_counters"]["commands_sent"] for r in rs]),
            "commands_delivered": mean([r["command_counters"]["commands_delivered"]
                                        for r in rs]),
            "commands_refused": mean([r["command_counters"]["commands_refused"] for r in rs]),
            "censored": mean([r["observation_window"]["censored_total"] for r in rs]),
            "intent_mismatch_min": mean([r["intent_mismatch_s"] / 60.0 for r in rs]),
            "mixed_config_min": mean([r["mixed_config_s"] / 60.0 for r in rs]),
            "dead_nodes_end": mean([sum(1 for v in r["energy"]["per_node"].values()
                                        if v["dead_at_s"] is not None) for r in rs]),
            "deficit_h": mean([sum(v["deficit_s"] for v in r["energy"]["per_node"].values())
                               / 3600.0 for r in rs]),
            "access_blocked": mean([r["access_blocked"] for r in rs]),
            "fenced": mean([r["command_counters"].get("fenced", 0) for r in rs]),
            "deduplicated": mean([r["command_counters"].get("deduplicated", 0) for r in rs]),
            # **动作准入归类**（v1.1：多余的控制流量是什么）。三条互斥且穷尽。
            "writes_changed": mean([r["command_counters"].get("writes_changed", 0) for r in rs]),
            "writes_same_value": mean([r["command_counters"].get("writes_same_value", 0)
                                       for r in rs]),
            "writes_speculative": mean([r["command_counters"].get("writes_speculative", 0)
                                        for r in rs]),
            # **意图准入账本**两侧合计
            "intent_generated": mean([r["intent_ledger"]["generated"] for r in rs]),
            "intent_lost": mean([r["intent_ledger"]["lost"] for r in rs]),
            "intent_rejected": mean([r["intent_ledger"]["rejected"] for r in rs]),
            "intent_stale_gen": mean([r["intent_ledger"]["stale_gen"] for r in rs]),
            "intent_refused": mean([r["intent_ledger"]["refused"] for r in rs]),
            "intent_expired": mean([r["intent_ledger"]["expired"] for r in rs]),
            **{f"skip_{k}": mean([r["skip_reasons"].get(k, 0) for r in rs])
               for k in ("in_flight", "dwell", "no_soc", "at_target",
                         "at_target_evidence_stale")},
            # **生成原因**（轨 C）：三类互斥且完备，`generated[reason] = sent[reason] + refused[reason]`。
            # 结果侧（change/same_value/unknown/stale）说的是"这条意图干了什么"；
            # 原因侧说的是"它为什么会被生成"——**只有原因侧能在生成之前把它消掉**。
            **{f"intent_reason_{k}": mean([r["intent_reason"]["generated"][k] for r in rs])
               for k in ("unknown_state", "target_change", "resend")},
            **{f"intent_reason_sent_{k}": mean([r["intent_reason"]["sent"][k] for r in rs])
               for k in ("unknown_state", "target_change", "resend")},
            # `inf`（初始电量自己就够跑完，采能与可行性无关）不进均值，否则会把均值拉成 inf。
            # **全部为 inf 时报 `None`，不报 0**——报 0 会变成一列看起来有值、实际是回退默认值的
            # 假数据，而 0 在这个定义下恰恰意味着"完全不可行"，正好读反。
            "autonomy_margin": (mean([r["autonomy_margin"] for r in rs
                                      if r["autonomy_margin"] != float("inf")])
                                if any(r["autonomy_margin"] != float("inf") for r in rs)
                                else None),
            "autonomy_margin_min": (mean([r["autonomy_margin_min"] for r in rs
                                          if r["autonomy_margin_min"] != float("inf")])
                                    if any(r["autonomy_margin_min"] != float("inf")
                                           for r in rs) else None),
            # **发送侧分解**：实际交付 + 发送侧损失（可控）+ 链路侧损失（不可控）= 总义务。
            "delivery_oracle": mean([r.get("delivery_oracle", 0) for r in rs]),
            "delivery_oracle_free_tx": mean([r.get("delivery_oracle_free_tx", 0) for r in rs]),
            "delivery_oracle_mid": mean([r.get("delivery_oracle_mid", 0) for r in rs]),
            "dynamic_oracle": mean([r["dynamic_oracle"] for r in rs
                                    if r.get("dynamic_oracle") is not None]) if any(
                r.get("dynamic_oracle") is not None for r in rs) else None,
            # 达标率 = **周期交付** / 真上界。**分子分母必须是同一个量**：真上界只覆盖周期义务
            # （事件义务靠触发锚定的本地采样，上界的动作集够不到，且事件列在全部臂上恒定、
            # 明令不得支撑结论）。曾经这里用"周期+事件"做分子，于是 dense600 在容量 0.05 下
            # 报出 100.1% 的达标率——**上界被突破**。与"相对事后最优固定配置"的 regret 不同，
            # 这个分母不受测试条件改变的操纵。
            "oracle_coverage": (mean([r["routine"]["delivered"] for r in rs]) /
                                mean([r["dynamic_oracle"] for r in rs
                                      if r.get("dynamic_oracle") is not None])
                                if any(r.get("dynamic_oracle") is not None for r in rs)
                                else None),
        }
        if args.outage_hours > 0:
            rec = [r["recovery"] for r in rs if r["recovery"]]
            a.update({
                "recovery_n_obligations": mean([x["n_obligations_in_window"] for x in rec]),
                "recovery_delivered": mean([x["delivered"] for x in rec]),
                "recovery_missing_collection": mean([x["missing_collection"] for x in rec]),
                "recovery_missing_delivery": mean([x["missing_delivery"] for x in rec]),
                "recovery_backlog_recovered": mean([x["backlog_recovered"] for x in rec]),
            })
        return a

    agg = {"n_seeds": args.seeds, "task_hours": args.task_hours,
           "tail_hours": args.tail_hours, "config": vars(args), "arms": {}}
    for a in arm_names:
        for L in layers:
            key = a if layers == ["naive"] else f"{a}__{L}"
            agg["arms"][key] = agg_of([r for r in runs
                                       if r["arm"] == a and r["exec_layer"] == L])

    # **后验最优固定**：如果知道这个测试条件、可以重新标定，最好的固定配置能到多少。
    # 它把"标定差距"与"反馈收益"分开：固定配置的 regret 相对它算，反馈的优势相对它算。
    fixed_keys = [k for k in agg["arms"] if k.startswith("dense") and "__" not in k]
    if len(fixed_keys) >= 2:
        best = max(fixed_keys, key=lambda k: agg["arms"][k]["routine_delivered"])
        agg["best_fixed_posthoc"] = dict(agg["arms"][best])
        agg["best_fixed_posthoc"]["_which"] = best


    doc = {"config": vars(args), "aggregate": agg, "runs": runs}
    _os.makedirs(OUT, exist_ok=True)
    path = _os.path.join(OUT, f"instance_{args.tag}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True, default=str)

    def _n(v):
        # 没有事件义务的场景里这些列是 `None`。打印成 `—`，**不打印 0**。
        return "—" if v is None else f"{v:.1f}"

    w = 30
    print(f"实例读数（{args.seeds} 种子/臂，义务 {args.task_hours}h + 尾部 {args.tail_hours}h）")
    print("=" * 96)
    hdr = (f"{'arm':<18} {'周期交付':>9} {'缺采':>5} {'缺送':>6} {'AoI s':>7} "
           f"{'事件采集':>8} {'事件交付':>8} {'上行':>6} {'下行试':>6} {'死节点':>6} {'混配min':>8}"
           + (" {:>8} {:>8}".format("真上界", "周期达标%") if args.dynamic_oracle else "")
           + (" {:>9} {:>9}".format("margin均", "margin最小")
              if args.harvest_mode == "solar" else "")
           + " {:>7} {:>7} {:>7}".format("改值", "同值", "未知态")
           + " {:>8} {:>8} {:>8} {:>8} {:>8}".format(
               "转发损", "择时损", "采集损", "链路损", "自由上界")
           + " {:>7} {:>7} {:>6} {:>6}".format("意图生成", "无信道", "丢失", "被拒"))
    print(hdr)
    print("-" * 96)
    for a in agg["arms"]:
        x = agg["arms"][a]
        print(f"{a:<18} {x['routine_delivered']:>9.1f} {x['routine_missing_collection']:>5.1f} "
              f"{x['routine_missing_delivery']:>6.1f} {x['routine_aoi_mean_s']:>7.0f} "
              f"{_n(x['event_match']):>8} {_n(x['event_delivered']):>8} "
              f"{x['uplinks']:>6.1f} {x['downlink_attempts']:>6.1f} "
              f"{x['dead_nodes_end']:>6.1f} {x['mixed_config_min']:>8.0f}"
              + (" {:>8.1f} {:>7.1f}%".format(x["dynamic_oracle"] or 0.0,
                                              100.0 * (x["oracle_coverage"] or 0.0))
                 if args.dynamic_oracle else "")
              + (" {:>9} {:>9}".format(
                     "—" if x["autonomy_margin"] is None else f"{x['autonomy_margin']:.2f}",
                     "—" if x["autonomy_margin_min"] is None
                     else f"{x['autonomy_margin_min']:.2f}")
                 if args.harvest_mode == "solar" else "")
              + " {:>7.1f} {:>7.1f} {:>7.1f}".format(
                  x["writes_changed"], x["writes_same_value"], x["writes_speculative"])
              + " {:>8.1f} {:>8.1f} {:>8.1f} {:>8.1f} {:>8.1f}".format(
                  x["delivery_oracle"] - x["routine_delivered"],
                  x["delivery_oracle_mid"] - x["delivery_oracle"],
                  x["delivery_oracle_free_tx"] - x["delivery_oracle_mid"],
                  168.0 - x["delivery_oracle_free_tx"],
                  x["delivery_oracle_free_tx"])
              + " {:>7.1f} {:>7.1f} {:>6.1f} {:>6.1f}".format(
                  x["intent_generated"], x["intent_refused"], x["intent_lost"],
                  x["intent_rejected"]))
    print("=" * 96)
    if args.outage_hours > 0:
        print("恢复分列（中断窗内 + 固定恢复观察期）")
        for a in agg["arms"]:
            x = agg["arms"][a]
            print(f"  {a:<18} 义务 {x['recovery_n_obligations']:.0f} 交付 {x['recovery_delivered']:.1f} "
                  f"缺采 {x['recovery_missing_collection']:.1f} 缺送 {x['recovery_missing_delivery']:.1f} "
                  f"补发追回 {x['recovery_backlog_recovered']:.1f}")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
