"""P0：多路径归因补件（doc 58 §P0）。

**不新建平行模拟器**，只在 `information_timing.py` 上加三件东西，并用**短时域**核验：

1. **停止原因台账**（`stop_ledger`）：把「本 epoch 为什么停下来」逐次落账，
   连同当时读到的量（队列长度、可用路径数、容量、卫星配额、剩余能量、额度、信念）。
   旧读数里四种原因**同形**，信息/算法/执行方式因此分不开；
2. **同 epoch「收到 ACK 但延后使用」控制**（`seq_deferred_ack`）：与 `data_ack`
   **同一个逐次执行循环**，差别只有一处——ACK 在本 epoch 内是否被用。
   于是 `seq_deferred_ack − history_only` ≈ **执行方式**，
   `data_ack − seq_deferred_ack` = **信息待遇**；
3. **不带新现场含义的有限状态校验**：两条路径、一条有期限的数据、2–3 次尝试，
   用已知观测概率**枚举**期望交付（见 `test_information_timing.py`）。

**停发规则本轮没有改**（固定 `q <= 0.05`），因此它在台账里被**测量**：
各臂停止原因中 `q_threshold` 的占比就是它到底有多紧。

**回归检查**：改动前后 4 条原臂的 `finalize()` 数值必须**逐位相同**（默认不记台账）。

    python3 multipath_probe/run_p0_decomposition.py --seeds 20 --hours 48

写 `results/p0_information_decomposition.json`。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from env import generate_trace  # noqa: E402
import information_timing as IT  # noqa: E402

RES = os.path.join(ROOT, "results")
ARMS = ("history_only", IT.ARM_SEQ_DEFERRED, "data_ack", "paid_probe", "current_truth")
#: 主条件的预算是 1950（336 h）⇒ 短时域按小时等比缩放，保持同一额度语义
BUDGET_336 = 1950.0
METRICS = ("event_rate", "routine_rate", "attempts", "probe_attempts", "energy",
           "money", "sat_quota_used", "wasted_bad_path", "same_epoch_reroutes",
           "deferred_applied")
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
        8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160,
        14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093,
        20: 2.086}


def t975(df: int) -> float:
    for key in sorted(T975):
        if df <= key:
            return T975[key]
    return 1.96


def paired(rows_a: list[dict], rows_b: list[dict], metric: str) -> dict:
    scale = 100.0 if metric.endswith("_rate") else 1.0
    d = [(b[metric] - a[metric]) * scale for a, b in zip(rows_a, rows_b)]
    mean = sum(d) / len(d)
    var = sum((x - mean) ** 2 for x in d) / (len(d) - 1)
    half = t975(len(d) - 1) * math.sqrt(var / len(d))
    return {"direction": "second_minus_first", "mean": mean, "lo": mean - half,
            "hi": mean + half, "win": sum(x > 1e-12 for x in d),
            "tie": sum(abs(x) <= 1e-12 for x in d), "loss": sum(x < -1e-12 for x in d)}


def summarize(res: dict) -> dict:
    """与 `run_information_timing.summarize_ledger` 同口径（不改旧文件）。"""
    acts = res["action_ledger"]
    reroutes = 0
    for prev, cur in zip(acts, acts[1:]):
        if (prev["t"] == cur["t"] and not prev["success"]
                and prev["path"] != cur["path"] and prev["kind"] == "data"
                and cur["kind"] == "data"):
            reroutes += 1
    out = {k: res[k] for k in ("event_rate", "routine_rate", "attempts",
                               "probe_attempts", "energy", "money",
                               "sat_quota_used", "wasted_bad_path")}
    out["same_epoch_reroutes"] = reroutes
    out["deferred_applied"] = res.get("deferred_applied", 0)
    out["stop_reason_counts"] = res.get("stop_reason_counts", {})
    out["n_stop_rows"] = len(res.get("stop_ledger", []))
    return out


def run_condition(seeds: int, hours: int, budget: float | None) -> dict:
    per_seed = {arm: [] for arm in ARMS}
    stop_rows: list[dict] = []
    for seed in range(seeds):
        trace = generate_trace(seed=seed, K=3, burst="chirpbox", T=hours)
        for arm in ARMS:
            res = IT.run_arm(trace, arm, budget)
            row = summarize(res)
            row["seed"] = seed
            per_seed[arm].append(row)
            stop_rows.extend(res["stop_ledger"])
    pairs = (
        ("execution_mode_seq_deferred_minus_history", "history_only",
         IT.ARM_SEQ_DEFERRED),
        ("information_data_ack_minus_seq_deferred", IT.ARM_SEQ_DEFERRED, "data_ack"),
        ("paid_probe_minus_data_ack", "data_ack", "paid_probe"),
        ("current_truth_minus_data_ack", "data_ack", "current_truth"),
    )
    comparisons = {label: {m: paired(per_seed[a], per_seed[b], m) for m in METRICS}
                   for label, a, b in pairs}
    means = {arm: {m: sum(r[m] for r in rows) / len(rows) for m in METRICS}
             for arm, rows in per_seed.items()}
    return {"means": means, "comparisons": comparisons, "per_seed": per_seed,
            "stop_rows": stop_rows}


def regression_check(hours: int, budget: float | None) -> dict:
    """改动前后 4 条原臂的 `finalize()` 数值必须逐位相同。"""
    old_src = subprocess.run(
        ["git", "show", "HEAD:multipath_probe/information_timing.py"],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout
    with tempfile.TemporaryDirectory() as tmp:
        # 旧模块要能找到它自己的依赖（`env`），因此放进同目录的临时子目录并加入路径
        old_dir = os.path.join(tmp, "old")
        os.makedirs(old_dir)
        for dep in ("env.py",):
            with open(os.path.join(HERE, dep), encoding="utf-8") as fh:
                open(os.path.join(old_dir, dep), "w", encoding="utf-8").write(fh.read())
        with open(os.path.join(old_dir, "old_info_timing.py"), "w",
                  encoding="utf-8") as fh:
            fh.write(old_src)
        sys.path.insert(0, old_dir)
        import old_info_timing as OLD                                  # noqa: E402
        out = {}
        for arm in ("history_only", "data_ack", "paid_probe", "current_truth"):
            same = True
            for seed in (0, 1, 2):
                tr = generate_trace(seed=seed, K=3, burst="chirpbox", T=hours)
                a = OLD.run_arm(tr, arm, budget)
                b = IT.run_arm(tr, arm, budget)
                keys = [k for k in a if k not in ("action_ledger", "evidence_ledger")]
                if any(a[k] != b[k] for k in keys):
                    same = False
            out[arm] = same
        return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--hours", type=int, default=48)
    ap.add_argument("--out", default="p0_information_decomposition")
    args = ap.parse_args()
    budget = BUDGET_336 * args.hours / 336.0

    print(f"短时域 T={args.hours} h，预算 {budget:.2f}（=1950×{args.hours}/336）"
          f"，种子 {args.seeds}")
    reg = regression_check(args.hours, budget)
    print(f"回归检查（改动前后 4 条原臂 finalize() 逐位相同）：{reg}")
    assert all(reg.values()), "改动改变了原有臂的读数 ⇒ 台账不能算纯诊断"

    cond = run_condition(args.seeds, args.hours, budget)
    counts: dict = {}
    for row in cond.pop("stop_rows"):
        key = (row["arm"], row["reason"])
        counts[key] = counts.get(key, 0) + 1
    stop_table = {arm: {r: counts.get((arm, r), 0)
                        for r in IT.STOP_REASONS} for arm in ARMS}
    out = {"hours": args.hours, "budget": budget, "seeds": args.seeds,
           "arms": list(ARMS), "regression_identical": reg,
           "stop_reason_table": stop_table, **cond}
    path = os.path.join(RES, f"{args.out}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"wrote {path}\n")

    print("=== 停止原因表（占该臂全部 epoch 停止记录的比例）")
    hdr = f"{'臂':<20}" + "".join(f"{r[:14]:>16}" for r in IT.STOP_REASONS)
    print(hdr)
    for arm in ARMS:
        tot = sum(stop_table[arm].values()) or 1
        print(f"{arm:<20}" + "".join(
            f"{stop_table[arm][r] / tot:>15.1%}" for r in IT.STOP_REASONS))
    print()
    for label, comp in out["comparisons"].items():
        print(f"--- {label}")
        for m in ("event_rate", "routine_rate", "attempts", "energy"):
            v = comp[m]
            sc = 100.0 if m.endswith("_rate") else 1.0
            unit = "pp" if sc != 1.0 else ""
            print(f"    {m:<14} Δ{v['mean']:+.4f}{unit} [{v['lo']:+.4f},{v['hi']:+.4f}]"
                  f"  {v['win']}/{v['tie']}/{v['loss']}")


if __name__ == "__main__":
    main()
