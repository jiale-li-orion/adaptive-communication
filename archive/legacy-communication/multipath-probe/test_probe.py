"""test_probe.py — 探针不变量自检。全部通过才允许引用 run_probe 的结论。"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from env import generate_trace, MultipathEnv, PATH_ORDER, ge_params, BAD_BURST_HOURS, PATH_SPECS  # noqa
from controllers import OracleController, RuleMpcController, FixedController  # noqa

PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}  {detail}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


def run(trace, cname):
    env = MultipathEnv(trace)
    ctrl = {"oracle": OracleController, "rule_mpc": RuleMpcController,
            "fixed": FixedController}[cname]()
    for _ in range(trace.T):
        v = env.view()
        a = ctrl.decide(v, env.true_good()) if cname == "oracle" else ctrl.decide(v)
        env.step(a)
    return env.finalize()


def test_conservation_and_shared_denominator():
    print("[1] 守恒与外生分母一致")
    for K in (1, 2, 3):
        for b in ("iid", "chirpbox", "heavy"):
            tr = generate_trace(3, K, b)
            ms = [run(tr, a) for a in ("oracle", "rule_mpc", "fixed")]
            for m in ms:
                check(f"K{K}/{b} 守恒",
                      m["event_delivered"] + m["missed_event"] == m["event_total"] and
                      m["routine_delivered"] + m["missed_routine"] == m["routine_total"])
            check(f"K{K}/{b} 三臂外生分母相同",
                  len({(m["event_total"], m["routine_total"]) for m in ms}) == 1)


def test_oracle_never_wastes_on_bad_path():
    print("[2] oracle 从不在真实坏路径上尝试（wasted=0）")
    worst = 0.0
    for K in (1, 2, 3):
        for b in ("iid", "chirpbox", "heavy"):
            for s in range(8):
                m = run(generate_trace(s, K, b), "oracle")
                worst = max(worst, m["wasted_bad_path"])
    check("oracle wasted_bad_path 恒为 0", worst == 0, f"max={worst}")


def test_determinism():
    print("[3] 同 seed 可复现；trace 与控制器无关")
    m1 = run(generate_trace(5, 3, "chirpbox"), "rule_mpc")
    m2 = run(generate_trace(5, 3, "chirpbox"), "rule_mpc")
    check("两次运行逐字段相同", m1 == m2)
    t1, t2 = generate_trace(7, 3, "heavy"), generate_trace(7, 3, "heavy")
    same = all(np.array_equal(t1.link_good[p], t2.link_good[p]) for p in t1.paths)
    check("同 seed trace 链路序列相同", same and t1.event_hours == t2.event_hours)


def test_ge_fit():
    print("[4] GE 链统计：chirpbox cellular 坏率≈0.312、平均坏突发≈6.38h")
    bad_frac, runs = [], []
    for s in range(40):
        st = generate_trace(s, 1, "chirpbox").link_good["cellular"]
        bad = ~st
        bad_frac.append(bad.mean())
        # 坏态连续段长度
        i, lens = 0, []
        while i < len(bad):
            if bad[i]:
                j = i
                while j < len(bad) and bad[j]:
                    j += 1
                lens.append(j - i)
                i = j
            else:
                i += 1
        if lens:
            runs.append(np.mean(lens))
    check("边际坏率在 [0.20,0.43]", 0.20 < np.mean(bad_frac) < 0.43,
          f"mean bad frac={np.mean(bad_frac):.3f}")
    check("平均坏突发在 [4.5,8.5]h", 4.5 < np.mean(runs) < 8.5,
          f"mean bad burst={np.mean(runs):.2f}h")


def test_quota_cap():
    print("[5] 卫星日配额：每任务总尝试不超过 14×24")
    for s in range(8):
        for a in ("oracle", "rule_mpc", "fixed"):
            m = run(generate_trace(s, 3, "heavy"), a)
            check(f"seed{s}/{a} 卫星用量≤336", m["sat_quota_used"] <= 14 * 24,
                  f"used={m['sat_quota_used']}")
            break


def test_p1_single_path():
    print("[6] P1 sanity：K=1 单路径，状态信息差无法利用替代路径 → 交付率差应很小")
    ds_e, ds_r = [], []
    for s in range(20):
        tr = generate_trace(s, 1, "heavy")
        mo, mr = run(tr, "oracle"), run(tr, "rule_mpc")
        ds_e.append((mo["event_rate"] - mr["event_rate"]) * 100)
        ds_r.append((mo["routine_rate"] - mr["routine_rate"]) * 100)
    check("K=1 oracle-rule event 差均值 < 3pp", abs(np.mean(ds_e)) < 3.0,
          f"mean ΔE={np.mean(ds_e):.3f}pp")
    check("K=1 oracle-rule routine 差均值 < 3pp", abs(np.mean(ds_r)) < 3.0,
          f"mean ΔR={np.mean(ds_r):.3f}pp")


if __name__ == "__main__":
    test_conservation_and_shared_denominator()
    test_oracle_never_wastes_on_bad_path()
    test_determinism()
    test_ge_fit()
    test_quota_cap()
    test_p1_single_path()
    print("=" * 60)
    print(f"{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)
