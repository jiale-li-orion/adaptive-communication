# -*- coding: utf-8 -*-
"""r23 非预知性 + 半开独立观测语义见证(doc38 §3/§4)。

W1 初始视图=首段节奏(600)外推全程、闭区间, 不含变更后密义务;
W2 边界样本(taken=22200)通知前=600信念 deadline 22800(复刻 doc38 函数级见证);
W3 两个仅未来段内容不同(300 vs 240)的 schedule, 通知前对内部样本决策完全相同;
W4 中断窗(h4-20)主回传不可达不发布, h20 首个可用小时才发布(gateway_received=72000);
W5 发布后旧信念被真值替换、半开独立观测生效, 两 schedule 对内部样本决策分化;
W6 端到端 gateway_received 与策略是否加密(comply/dayfeed)无关——任务通知独立下发;
W7 半开语义: 600 疏采样无法在边界点双配满足 300 密义务(taken=边界只归一窗)。
"""
import os, sys, types
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from mission_view import MissionViewGate
from joint_plane import JointControlPlane

MEAS = {"n00": "displacement"}
S300 = [(0, 600, "blue"), (21600, 300, "yellow")]
S240 = [(0, 600, "blue"), (21600, 240, "yellow")]
BOUND = types.SimpleNamespace(node_id="n00", measurand="displacement", taken_at=22200)
INTERIOR = types.SimpleNamespace(node_id="n00", measurand="displacement", taken_at=22250)


def fresh_plane(schedule):
    gate = MissionViewGate(MEAS, 48, schedule)   # 默认 half_open_after_first=True
    pl = object.__new__(JointControlPlane)
    pl.period_s, pl.grace_s, pl._mission_gate = 600, 600, gate
    pl._obl_index = {}
    for o in gate.initial_view(gate.truth_routine):
        pl._obl_index.setdefault((o.node_id, o.measurand), []).append(o)
    return pl, gate


def pump(pl, gate, t_s, pathfn):
    due = gate.poll(t_s, pathfn)
    for seg in due:
        pl._install_mission_segment(seg)
    return due


path_outage = lambda h: not (4 <= h < 20)

# W1 初始视图全为 600 闭区间窗、无密义务
pl300, g300 = fresh_plane(S300)
init_routine = [o for lst in pl300._obl_index.values() for o in lst]
assert len(init_routine) == len(g300.belief_routine)
assert all((o.window[1] - o.window[0]) == 600 and not o.match_half_open for o in init_routine), "W1"

# W2 边界样本通知前=600信念 22800（复刻 doc38）
assert pl300._sample_obl(BOUND)[0] == 22800, "W2"
pl240, g240 = fresh_plane(S240)
assert pl240._sample_obl(BOUND)[0] == 22800, "W2"

# W3 通知前(中断 h6/h19)两 schedule 对内部样本完全相同(600信念: t22250∈[22200,22800] dl23400)
assert pump(pl300, g300, 6 * 3600, path_outage) == []
assert pump(pl240, g240, 6 * 3600, path_outage) == []
assert pump(pl300, g300, 19 * 3600 + 3599, path_outage) == []
assert pl300._sample_obl(INTERIOR)[0] == pl240._sample_obl(INTERIOR)[0] == 23400, "W3"
assert not g300.segments[0]["notified"] and not g240.segments[0]["notified"]

# W4 h20 才发布
assert len(pump(pl300, g300, 20 * 3600, path_outage)) == 1
assert len(pump(pl240, g240, 20 * 3600, path_outage)) == 1
assert g300.segments[0]["gw_at"] == g240.segments[0]["gw_at"] == 72000, "W4"

# W5 发布后分化(半开): t22250 -> 300表[22200,22500) dl22800 ; 240表[22080,22320) dl22560
dl300 = pl300._sample_obl(INTERIOR)[0]
dl240 = pl240._sample_obl(INTERIOR)[0]
assert (dl300, dl240) == (22800, 22560), f"W5 {dl300}/{dl240}"
assert dl300 != dl240 and dl300 != 23400 and dl240 != 23400

def count_window(pl, lo):
    return sum(1 for lst in pl._obl_index.values() for o in lst
               if lo <= o.release_at < pl._mission_gate.H)
assert count_window(pl300, 21600) == sum(1 for o in g300.truth_routine
                                        if 21600 <= o.release_at < g300.H), "W5 替换完整"

# W7 半开独立观测: 升级后 300 义务, 一份边界样本只归一窗(不双配)
seg_obl = [o for o in g300.truth_routine if o.release_at in (21900, 22200)]
b = types.SimpleNamespace(node_id="n00", measurand="displacement", taken_at=22200)
hits = [o for o in seg_obl if o.matches(b)]
assert len(hits) == 1 and hits[0].release_at == 22200, f"W7 边界样本应只归一窗, got {[o.release_at for o in hits]}"

# W6 端到端: gateway_received 与策略无关
from joint_run import run_joint
UP = [(0, 600, "blue"), (6 * 3600, 300, "yellow")]
def timing(mode):
    r, _, _ = run_joint(seed=0, task_hours=48, arm="local", groups=2,
                        sample_interval_s=600, report_period_s=600, routine_period_s=600,
                        harvest_mode="solar", harvest_peak_wh_per_hour=0.03, initial_soc=1.0,
                        outage_start_h=4, outage_hours=16, enable_backup=True,
                        backup_rate_s=1200, backup_bytes=78, backup_chooser="maxcov",
                        mission_schedule=UP, mission_mode=mode)
    return r["mission_timing"][0]["gateway_received_at"]
assert timing("comply") == timing("dayfeed") == 72000, "W6"

print("r23 非预知性+半开语义见证全部 PASS")
print("  W2 边界样本通知前=22800(600信念); W5 内部样本通知后 300=22800 / 240=22560 (分化)")
print("  W4/W6 gateway_received=72000(h20), 与策略无关; W7 边界样本半开只归一窗")
