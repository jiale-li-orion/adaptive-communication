# -*- coding: utf-8 -*-
"""r37e — deadline_purge 的 seed 0-9 全扫 + 配对置信区间(零 LLM)。

r37d 只用留出 seed 6/7/8; 本脚本跑满 10 个 seed (0-9), 每 seed 三档
maxcov x {fifo, deadline_purge, latest_only}, 报告全时段 svc、中断 on-time(d)、
备份 on/过期, 并给 deadline_purge-fifo 的配对差均值与 95% CI(配对 t, t_{.975,9}=2.262),
以及 deadline_purge 对 latest_only 的全时段支配核对。
"""
import os, sys, math
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
import r37_conformance as r37
from joint_run import run_joint

BASE = {k: v for k, v in r37.COMMON.items() if k != "seed"}
SEEDS = list(range(10))
QS = ("fifo", "deadline_purge", "latest_only")
T9 = 2.262  # two-sided 95%, df=9


def run(seed, cs):
    return run_joint(seed=seed, backup_chooser="maxcov", cache_service=cs, **BASE)


def mean(xs):
    return sum(xs) / len(xs)


def sd(xs):
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def ci(diffs):
    m, s = mean(diffs), sd(diffs)
    h = T9 * s / math.sqrt(len(diffs))
    return m, s, m - h, m + h


def _ndead(v):
    """r37.audit 的 dead 是节点列表，取长度；兼容历史上返回计数的情况。"""
    return len(v) if isinstance(v, (list, tuple)) else int(v)


def main():
    rows = {}
    print("== r37e seed 0-9 全扫 (maxcov x 队列) ==")
    print(f"{'seed':>5}{'queue':<16}{'svc':>9}{'中断d':>8}{'备份on':>8}{'过期':>6}")
    for seed in SEEDS:
        for cs in QS:
            r, inst, obl = run(seed, cs)
            Z = r37.audit(f"s{seed}/{cs}", r, inst, obl)
            rows[(seed, cs)] = Z
            print(f"{seed:>5}{cs:<16}{Z['svc']:>9.4f}{Z['d']:>8}{Z['on']:>8}{Z['late']:>6}")
        print()

    print("== 汇总 (n=10) ==")
    for cs in QS:
        sv = [rows[(s, cs)]['svc'] for s in SEEDS]
        dd = [rows[(s, cs)]['d'] for s in SEEDS]
        late = sum(rows[(s, cs)]['late'] for s in SEEDS)
        on = sum(rows[(s, cs)]['on'] for s in SEEDS)
        print(f"{cs:<16} svc 均值 {mean(sv):.4f} (sd {sd(sv):.4f})  "
              f"中断d 总 {sum(dd):>5} 均 {mean(dd):.1f}  备份on总 {on:>5}  过期总 {late}")

    print("\n== 配对差 deadline_purge - fifo ==")
    dsvc = [rows[(s, 'deadline_purge')]['svc'] - rows[(s, 'fifo')]['svc'] for s in SEEDS]
    dd = [rows[(s, 'deadline_purge')]['d'] - rows[(s, 'fifo')]['d'] for s in SEEDS]
    m, s, lo, hi = ci(dsvc)
    print(f"svc 差(点): 逐seed " + ",".join(f"{x*100:+.1f}" for x in dsvc))
    print(f"svc 差均值 {m*100:+.2f} 点, sd {s*100:.2f}, 95%CI [{lo*100:+.2f},{hi*100:+.2f}], "
          f"全部为正: {all(x > 0 for x in dsvc)}")
    print(f"中断d 差: 逐seed " + ",".join(f"{x:+d}" for x in dd))
    tf = sum(rows[(s, 'fifo')]['d'] for s in SEEDS)
    tp = sum(rows[(s, 'deadline_purge')]['d'] for s in SEEDS)
    print(f"中断d 总 {tf} -> {tp} ({tp/max(tf,1):.2f}x), 配对均差 {mean(dd):+.1f}")
    print(f"过期: fifo 总 {sum(rows[(s,'fifo')]['late'] for s in SEEDS)} -> "
          f"purge 总 {sum(rows[(s,'deadline_purge')]['late'] for s in SEEDS)}")

    print("\n== deadline_purge vs latest_only (全时段) ==")
    pv = [rows[(s, 'deadline_purge')]['svc'] - rows[(s, 'latest_only')]['svc'] for s in SEEDS]
    m, s, lo, hi = ci(pv)
    print(f"svc 差(点): 逐seed " + ",".join(f"{x*100:+.1f}" for x in pv))
    print(f"purge-latest svc 差均值 {m*100:+.2f} 点, 95%CI [{lo*100:+.2f},{hi*100:+.2f}], "
          f"purge 全部支配: {all(x > 0 for x in pv)}")

    # --- 机器可读结果：论文表格与主张表的参考值都读这一份 ---
    import json as _json
    # 只落盘标量：r37.audit 的返回里带每条义务的完整行与义务对象，直接 dump 会写出
    # 数 MB 的中间结构，把主张所需的读数淹没。
    _SCALARS = ("svc", "dead", "n", "d", "on", "late", "onb", "lateb",
                "packets", "records", "bytes", "suppressed", "local_purge")
    per_seed = {}
    for s_ in SEEDS:
        for cs in QS:
            z = rows[(s_, cs)]
            per_seed[f"s{s_}/{cs}"] = {
                k: (len(z[k]) if k == "dead" and isinstance(z[k], (list, tuple)) else z[k])
                for k in _SCALARS}
    dsvc = [rows[(s, "deadline_purge")]["svc"] - rows[(s, "fifo")]["svc"] for s in SEEDS]
    dl = [rows[(s, "deadline_purge")]["late"] - rows[(s, "fifo")]["late"] for s in SEEDS]
    m_svc, s_svc, lo_d, hi_d = ci(dsvc)
    out = {
        "run": "r37e_full_seeds",
        "seeds": SEEDS,
        "queues": list(QS),
        "chooser": "maxcov",
        "per_seed": per_seed,
        "summary": {
            cs: {
                "svc_mean": round(mean([rows[(s, cs)]["svc"] for s in SEEDS]), 4),
                "svc_sd": round(sd([rows[(s, cs)]["svc"] for s in SEEDS]), 4),
                "outage_on_time_total": sum(rows[(s, cs)]["d"] for s in SEEDS),
                "backup_on_total": sum(rows[(s, cs)]["on"] for s in SEEDS),
                "expired_total": sum(rows[(s, cs)]["late"] for s in SEEDS),
                "deaths_total": sum(_ndead(rows[(s, cs)]["dead"]) for s in SEEDS),
            } for cs in QS
        },
        "paired_purge_minus_fifo": {
            "per_seed_points": [round(x * 100, 3) for x in dsvc],
            "mean_points": round(m_svc * 100, 3),
            "ci95_points": [round(lo_d * 100, 3), round(hi_d * 100, 3)],
            "all_positive": all(x > 0 for x in dsvc),
            "expired_records_delta_total": sum(dl),
            "outage_on_time_delta_total": (sum(rows[(x, "deadline_purge")]["d"] for x in SEEDS)
                                          - sum(rows[(x, "fifo")]["d"] for x in SEEDS)),
        },
    }
    _p = os.path.join(_CODE, "..", "results", "r37e_full_seeds.json")
    _json.dump(out, open(_p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n写出 {_p}")


if __name__ == "__main__":
    main()
