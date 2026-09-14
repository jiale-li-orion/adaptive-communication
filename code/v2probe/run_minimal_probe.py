"""v1.2 minimal probe 实验主脚本（预注册 02 号文的执行器）。

流程（守住 v1.1/v1.2 防火墙：只 import v1.1 的 ``one_seed`` 读台账，不改其任何代码）：

  1. 对每个档（P0 无中断 / P1 回传[4h,7h) / P2 接入[4h,7h)）、每个开发种子，
     **只跑一次** ``one_seed(arm='local', placement='gateway', obligation_ledger=True)``
     得到 v1.1 逐义务台账，并用 ``predicted_up_ticks`` 纯函数重建主链路 up 小时序列；
  2. 同一份台账上，叠加备用链路，对 速率{30,60,120,300}s × K{1,4,9,16} 共 16 格、
     6 条臂做纯内存回放（chooser 之间共享同一机会序列与池演化）；
  3. 锚点硬门：``primary_only`` 必须逐义务复算 == v1.1 台账交付，否则报错退出；
  4. 同种子配对，bootstrap 与 t 区间并列，按冻结判据判 P-A / P-B 与三分支。

    python3 code/v2probe/run_minimal_probe.py --seeds 20
    python3 code/v2probe/run_minimal_probe.py --seeds 20 --quick   # 只主例(120,9)

写 ``results/v2probe_minimal.json``。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_CODE = os.path.dirname(_HERE)
for _p in (_HERE, _CODE, *(os.path.join(_CODE, d) for d in
                           ("analysis", "experiments", "instance", "monitoring",
                            "physics", "runtime"))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import backup_model as bm                                              # noqa: E402
from stats_util import paired_compare                                  # noqa: E402
from instance_run import one_seed                                      # noqa: E402
from trace_seed_timeline import build_kwargs                           # noqa: E402
from first_heard_sufficiency import (CONDITIONS, PLACEMENT,            # noqa: E402
                                     predicted_up_ticks)

RES = os.path.normpath(os.path.join(_CODE, "..", "results"))
BASE_TAG = "instance_ccorral_iid_c0.05"
PRIMARY_ARM = "local"           # 固定 900s、中心不干预的最普通主链路系统
RATES = (30, 60, 120, 300)
KS = (1, 4, 9, 16)
MAIN_RATE, MAIN_K = 120, 9
CHOOSERS = bm.CHOOSERS


def _git_head() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, cwd=os.path.dirname(_CODE))
        return out.stdout.strip()
    except Exception:
        return "unknown"


def build_ledger(cond: str, seed: int, base: dict):
    """跑一次 v1.1（不改它），返回 (rows, up_hour_flag, end_s)。"""
    over = CONDITIONS[cond]
    kw = {**base, **over}
    got = (kw["access_outage_h"], kw["access_outage_start_h"],
           kw["outage_hours"], kw["outage_start_h"])
    want = (over["access_outage_h"], over["access_outage_start_h"],
            over["outage_hours"], over["outage_start_h"])
    assert got == want, f"{cond}: 中断四字段不符 {got} != {want}"
    run = one_seed(seed, arm=PRIMARY_ARM, placement=PLACEMENT, trace=True,
                   obligation_ledger=True, **kw)
    end_s = int((base["task_hours"] + base["tail_hours"]) * 3600)
    up_ticks = predicted_up_ticks(seed, kw, end_s)
    rows = bm.rows_from_run(run)
    return rows, bm.up_hours_from_ticks(up_ticks, end_s), end_s


def _agg(vals: list[int]) -> dict:
    n = len(vals)
    mean = sum(vals) / n if n else 0.0
    srt = sorted(vals)
    return {"mean": round(mean, 4), "sum": sum(vals), "min": srt[0] if srt else 0,
            "max": srt[-1] if srt else 0,
            "median": srt[n // 2] if srt else 0, "per_seed": vals}


def evaluate_cell(replays_by_arm: dict[str, list[bm.ReplayResult]]) -> dict:
    """对一个 (cond,rate,K) 格：聚合 + P-A(best chooser vs primary) + P-B(worst vs best)。"""
    arms = {}
    final_ps, rescued_ps, packets_ps = {}, {}, {}
    for arm, rs in replays_by_arm.items():
        final_ps[arm] = [r.n_final_delivered for r in rs]
        rescued_ps[arm] = [r.n_rescued for r in rs]
        packets_ps[arm] = [r.n_packets for r in rs]
        arms[arm] = {
            "final": _agg(final_ps[arm]),
            "rescued": _agg(rescued_ps[arm]),
            "packets": _agg(packets_ps[arm]),
            "wasted_on_recovered_sum": sum(r.n_wasted_on_recovered for r in rs),
            "never_heard_mean": round(sum(r.n_never_heard for r in rs) / len(rs), 3),
            "expired_unsent_mean": round(sum(r.n_expired_unsent for r in rs) / len(rs), 3),
            "rescued_per_packet": round(
                sum(r.n_rescued for r in rs) / max(1, sum(r.n_packets for r in rs)), 4)}

    # 选 best/worst chooser（按 final 的种子均值；全部臂同时列出，不隐藏其余）
    means = {a: arms[a]["final"]["mean"] for a in CHOOSERS}
    best = max(CHOOSERS, key=lambda a: (means[a], a))
    worst = min(CHOOSERS, key=lambda a: (means[a], a))

    out = {"arms": arms, "chooser_final_means": means, "best_chooser": best,
           "worst_chooser": worst}

    # P-A：best chooser vs primary_only
    pa_cmp = paired_compare(final_ps[best], final_ps["primary_only"])
    eff = arms[best]["rescued_per_packet"]
    out["PA"] = {
        "best_vs_primary": pa_cmp, "best_rescued_per_packet": eff,
        "pass": bool(pa_cmp["both_exclude_zero"] and pa_cmp["mean_diff"] > 0
                     and eff >= 0.5)}
    # 每个 chooser vs primary 都列出（防止只报挑中的那个）
    out["all_chooser_vs_primary"] = {
        a: paired_compare(final_ps[a], final_ps["primary_only"]) for a in CHOOSERS}

    # P-B：best vs worst chooser
    pb_cmp = paired_compare(final_ps[best], final_ps[worst])
    out["PB"] = {"best": best, "worst": worst,
                 "best_minus_worst": pb_cmp,
                 "pass": bool(pb_cmp["both_exclude_zero"] and pb_cmp["mean_diff"] > 0)}

    if not out["PA"]["pass"]:
        branch = "NO_GO_actuator_has_no_paired_gain"
    elif not out["PB"]["pass"]:
        branch = "FAILOVER_TRADITIONAL_choice_does_not_matter"
    else:
        branch = "CHOICE_FREEDOM_EXISTS_proceed_to_structured_baseline"
    out["branch"] = branch
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--quick", action="store_true", help="只跑主例 (120s,K=9)")
    ap.add_argument("--out", default="v2probe_minimal")
    args = ap.parse_args()

    cfg = json.load(open(os.path.join(RES, f"{BASE_TAG}.json"), encoding="utf-8"))["config"]
    base = build_kwargs(dict(cfg))
    base.pop("trace", None)
    base.pop("cache_service", None)

    rates = (MAIN_RATE,) if args.quick else RATES
    ks = (MAIN_K,) if args.quick else KS

    # 1) 逐 (cond,seed) 跑一次 v1.1 台账（与 rate/K/arm 无关，复用）
    ledger: dict[str, list] = {}
    anchor_mismatch = {}
    for cond in CONDITIONS:
        ledger[cond] = []
        mismatch = 0
        for seed in range(args.seeds):
            rows, upflag, end_s = build_ledger(cond, seed, base)
            # 锚点硬门：primary_only 回放必须逐义务 == 主链路台账
            prim = bm.replay(rows, "primary_only", MAIN_RATE, MAIN_K, end_s, upflag)
            for o in rows:
                if prim.per_oid[o.oid] != o.primary_delivered:
                    mismatch += 1
            ledger[cond].append((rows, upflag, end_s))
        anchor_mismatch[cond] = mismatch
        print(f"[ledger] {cond:18s} {args.seeds} seeds, anchor mismatch={mismatch}")
        if mismatch:
            raise SystemExit(f"锚点失败 {cond}: primary_only 与台账不一致 {mismatch} 条")

    # 2) 网格回放
    grid: dict = {}
    for cond in CONDITIONS:
        grid[cond] = {}
        for rate in rates:
            for k in ks:
                by_arm: dict[str, list[bm.ReplayResult]] = {a: [] for a in bm.ARMS}
                for rows, upflag, end_s in ledger[cond]:
                    for arm in bm.ARMS:
                        by_arm[arm].append(bm.replay(
                            rows, arm, rate, k, end_s, upflag, failover_gate=True))
                cell = evaluate_cell(by_arm)
                grid[cond][f"r{rate}_K{k}"] = cell
                pa, pb = cell["PA"]["pass"], cell["PB"]["pass"]
                print(f"  {cond:18s} r{rate:3d} K{k:2d} "
                      f"best={cell['best_chooser']:18s} PA={int(pa)} PB={int(pb)} "
                      f"branch={cell['branch']}")

    # 3) 主例与主档判定
    main_key = f"r{MAIN_RATE}_K{MAIN_K}"
    main_by_cond = {cond: grid[cond][main_key] for cond in CONDITIONS}

    # 上界对照：双通道"始终并行"（不做 failover gate）最多能多救多少——只在主例算
    parallel_upper = {}
    for cond in CONDITIONS:
        per_arm = {a: [] for a in bm.ARMS}
        for rows, upflag, end_s in ledger[cond]:
            for arm in bm.ARMS:
                per_arm[arm].append(bm.replay(
                    rows, arm, MAIN_RATE, MAIN_K, end_s, upflag, failover_gate=False))
        parallel_upper[cond] = {
            a: {"final_mean": round(sum(r.n_final_delivered for r in rs) / len(rs), 4),
                "rescued_mean": round(sum(r.n_rescued for r in rs) / len(rs), 4),
                "packets_mean": round(sum(r.n_packets for r in rs) / len(rs), 4)}
            for a, rs in per_arm.items()}

    primary_cond = "P1_backhaul_4h7h"
    verdict_main = {
        "rate": MAIN_RATE, "k": MAIN_K,
        "primary_condition": primary_cond,
        "PA_pass": main_by_cond[primary_cond]["PA"]["pass"],
        "PB_pass": main_by_cond[primary_cond]["PB"]["pass"],
        "branch": main_by_cond[primary_cond]["branch"]}

    # 4) 灵敏度：P-A/P-B 在 16 格上是否方向一致（结论不得依赖单点）
    sensitivity = {}
    for cond in CONDITIONS:
        cells = grid[cond]
        sensitivity[cond] = {
            key: {"PA": c["PA"]["pass"], "PB": c["PB"]["pass"],
                  "best": c["best_chooser"],
                  "best_mean_final": c["chooser_final_means"][c["best_chooser"]],
                  "primary_mean_final": c["arms"]["primary_only"]["final"]["mean"],
                  "branch": c["branch"]}
            for key, c in cells.items()}

    doc = {
        "meta": {
            "title": "Task v1.2 minimal probe —— 受限备用短报文链路回放叠加",
            "preregistration": "docs/s7-method/v1.2/02-pre-registration-minimal-probe-2026-09-14.md",
            "git_head": _git_head(), "seeds": args.seeds,
            "primary_arm": PRIMARY_ARM, "placement": PLACEMENT,
            "rates": list(rates), "ks": list(ks), "main_case": [MAIN_RATE, MAIN_K],
            "arms": list(bm.ARMS),
            "simplifications": [
                "主分析用failover gate:仅主链路当前小时down时启用备用(贴合§5.3.7双模与掉线自动切换);parallel_upper_bound为双通道始终并行的上界",
                "备用成功率取1、发送时延当拍",
                "不计字节分包，容量=每包K条义务样本(K由200B开销派生,主例9)",
                "不计资费/能量，稀缺只由速率×K体现",
                "网关级备用：h*(到网关)后入池；终端级只会更早入池、不影响P-B",
                "备用机会全程均匀且独立于地面中断"],
            "legal_observables": ["h*到网关时刻", "公开deadline", "截至t主链路up历史",
                                  "截至t主链路确认交付时刻"],
            "illegal_in_chooser": ["主链路未来up", "义务最终是否交付(真值)", "未来中断表"]},
        "base_tag": BASE_TAG,
        "anchor_mismatch": anchor_mismatch,
        "main_case_verdict": verdict_main,
        "main_case_by_condition": main_by_cond,
        "parallel_upper_bound": parallel_upper,
        "sensitivity": sensitivity,
        "grid": grid}

    path = os.path.join(RES, f"{args.out}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print(f"\nwrote {path}")
    print("\n=== 主例 (120s/包, K=9) 三档 P-A / P-B ===")
    for cond, c in main_by_cond.items():
        print(f"  {cond:18s} PA={int(c['PA']['pass'])} PB={int(c['PB']['pass'])}"
              f"  branch={c['branch']}")
        for a in CHOOSERS:
            m = c["chooser_final_means"][a]
            cmp_ = c["all_chooser_vs_primary"][a]
            print(f"      {a:18s} final_mean={m:8.3f}  vs_primary Δ={cmp_['mean_diff']:+.3f}"
                  f" boot[{cmp_['bootstrap_lo']:+.3f},{cmp_['bootstrap_hi']:+.3f}]"
                  f" t[{cmp_['t_lo']:+.3f},{cmp_['t_hi']:+.3f}]"
                  f" W/L/T={cmp_['win_loss_tie']} eff={c['arms'][a]['rescued_per_packet']}")
    print(f"\n主档 {primary_cond} 判定：{verdict_main['branch']}")


if __name__ == "__main__":
    main()
