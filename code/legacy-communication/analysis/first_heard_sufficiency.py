"""**first-heard sufficiency audit**（用户 2026-09-14 指定的下一枪）。

不实现任何 policy、不改仿真器。只用**已有**的 v1.1 语义回答一个问题：

    一条义务的端到端交付，是否**一旦给定它的最早合法网关到达时刻 `h*`** 就被决定，
    而与此后到底有几份副本无关？

**模型事实（读码核实，不是假设）**：

1. `opportunity.ControlPlane.backhaul_forward()`：回传可用时**把所有** `gateway_pending`
   交给中心；不可用时**什么都不丢**、留在队列里等下一次。⇒ **不存在「每个副本各自买一次
   回传尝试」的机制**；
2. 逐拍顺序（`network.InstanceState.run`）：先听到上行 → `gateway_ingest` 入队，
   **同一拍**再调 `backhaul_forward` ⇒ 若本小时可回传，`h*` 当拍就能被转发；
3. **转发延迟在本实例路径上恒为 0**：`network.py:721` 调用 `backhaul_forward(t_s)` **不传**
   `delay_s`，而 `ControlPlane` 的该参数默认 0（`backhaul_delay_s` 因此是实例层的一个
   **静默空参数**——只有旧 runner `monitoring/runner.py:577` 传它）；
4. `center.receive()` 无容量、无丢弃，逐样本记 `received_at = t_s`；
5. 回传可用性是**纯函数**：`stable_uniform(seed,"backhaul",hour) < p_good`，
   再叠一个**按小时**的中断门；
6. 评分器的判定是 `received_at <= deadline`。

⇒ 因此预测式是**闭式**的：令 `B(d)` = `d` 之前**最后一次**可回传时刻，
则 `ŷ = 1[h* ≤ B(d)]`。本脚本逐义务、逐种子、逐臂核对 `ŷ == delivered`，
并把「多副本撞窗口」这个**被否证的解释**换成可量化的 `margin = B(d) − h*`。

    python3 code/analysis/first_heard_sufficiency.py --seeds 20

写 `results/first_heard_sufficiency.json`。
"""
from __future__ import annotations

import argparse
import json
import os as _os
import sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, _CODE, *(_os.path.join(_CODE, d) for d in
                          ("physics", "runtime", "experiments", "analysis",
                           "monitoring", "instance"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

from opportunity import ControlPlane, LoRaProfile                       # noqa: E402
from instance_run import one_seed                                        # noqa: E402
from trace_seed_timeline import build_kwargs                             # noqa: E402

RES = _os.path.normpath(_os.path.join(_CODE, "..", "results"))
BASE_TAG = "instance_ccorral_iid_c0.05"
TICK_S = 60
PLACEMENT = "gateway"
DWELL = 600
ARMS = ("fixed300", "pacing_backlog900_300", "oblig_copies1", "oblig_copies3")
CONDITIONS = {
    "P0_no_outage": dict(access_outage_h=0.0, access_outage_start_h=4.0,
                         outage_hours=0.0, outage_start_h=0.0),
    "P1_backhaul_4h7h": dict(access_outage_h=0.0, access_outage_start_h=4.0,
                             outage_hours=3.0, outage_start_h=4.0),
    "P2_access_4h7h": dict(access_outage_h=3.0, access_outage_start_h=4.0,
                           outage_hours=0.0, outage_start_h=0.0),
}
#: 「deadline-critical」的判据：余量小于一个上报档位即认为贴着最后机会。
CRITICAL_MARGIN_S = 900


def _register() -> None:
    import center as C
    C.ARMS["fixed300"] = lambda: C.FixedPeriodPolicy(300, dwell_s=DWELL)
    C.ARMS["pacing_backlog900_300"] = (
        lambda: C.ReportPacingPolicy(slow_s=900, fast_s=300, dwell_s=DWELL,
                                     mode="pending_backlog"))
    for k in (1, 3):
        C.ARMS[f"oblig_copies{k}"] = (
            lambda _k=k: C.ObligationCopiesPolicy(k=_k, fast_s=300, slow_s=900,
                                                  dwell_s=DWELL))


def predicted_up_ticks(seed: int, kw: dict, end_s: int) -> list[int]:
    """**重建** exogeneous 回传可用性（与运行共用同一 `(seed, p_good, gate, burst)`）。

    可用性是 `stable_uniform(seed, "backhaul", hour) < p_good` 的纯函数，因此这里
    用一个**新的** `ControlPlane` 按同样参数取值即可复现整条时间线——
    **不需要给仿真器加任何诊断字段**。
    """
    plane = ControlPlane(LoRaProfile(), seed=seed,
                         uplink_p_arrive=kw["uplink_p_arrive"],
                         backhaul_p_good=kw["backhaul_p_good"],
                         burst_p_gb=kw.get("burst_p_gb"),
                         burst_p_bg=kw.get("burst_p_bg"),
                         backhaul_delay_s=kw.get("backhaul_delay_s", 0))
    if kw["outage_hours"] > 0:
        lo = int(kw["outage_start_h"])
        hi = int(kw["outage_start_h"] + kw["outage_hours"])
        plane.backhaul_gate = lambda hour, _lo=lo, _hi=hi: not (_lo <= hour < _hi)
    hours = end_s // 3600
    out: list[int] = []
    for hour in range(hours + 1):
        if not plane.backhaul_available(hour):
            continue
        out.extend(range(hour * 3600, min((hour + 1) * 3600, end_s), TICK_S))
    return out


def _mean(xs):
    v = [x for x in xs if x is not None]
    return round(sum(v) / len(v), 4) if v else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--out", default="first_heard_sufficiency")
    args = ap.parse_args()
    _register()

    cfg = json.load(open(_os.path.join(RES, f"{BASE_TAG}.json"), encoding="utf-8"))["config"]
    base = build_kwargs(dict(cfg))
    base.pop("trace", None)
    base.pop("cache_service", None)
    assert not base.get("backhaul_burst"), "本审计只在逐小时 i.i.d. 回传上成立"
    task_h = int(base["task_hours"])
    end_s = int((base["task_hours"] + base["tail_hours"]) * 3600)

    out: dict = {"base": BASE_TAG, "placement": PLACEMENT, "seeds": args.seeds,
                 "arms": list(ARMS), "end_s": end_s, "tick_s": TICK_S,
                 "critical_margin_s": CRITICAL_MARGIN_S,
                 "reconstruction": {}, "sufficiency": {}, "margin": {},
                 "flips": {}, "copies": {}, "ineffective_band": {},
                 "mismatch_examples": []}

    for cond, over in CONDITIONS.items():
        kw = {**base, **over}
        got = (kw["access_outage_h"], kw["access_outage_start_h"],
               kw["outage_hours"], kw["outage_start_h"])
        want = (over["access_outage_h"], over["access_outage_start_h"],
                over["outage_hours"], over["outage_start_h"])
        assert got == want, f"{cond}: 中断设置与声明不符 {got} != {want}"
        out["reconstruction"][cond], out["sufficiency"][cond] = {}, {}
        out["margin"][cond], out["copies"][cond] = {}, {}
        out["ineffective_band"][cond] = {}
        per_arm_rows: dict[str, list] = {a: [] for a in ARMS}
        up_cache: dict[int, list[int]] = {}

        for arm in ARMS:
            agree = disagree = 0
            # ⚠ **这两个集合必须逐种子比对**：`up_set` 是**该种子**的可回传拍，
            # 而真实转发拍只能与**同一个种子**的集合比。第一版把它们放在种子循环**外**，
            # 于是拿「20 个种子的并集」去减「最后一个种子的集合」，报出 24 个假越界拍
            # ——**审计脚本自己的作用域 bug，不是仿真器的问题**（逐种子单独跑时越界 0 个）。
            realized_ticks: set[int] = set()
            not_predicted: set[int] = set()
            margins_del: list = []
            margins_miss: list = []
            n_critical = 0
            copies_del: list = []
            copies_miss: list = []
            n_h_none = n_censored = 0
            # **「准时到网关」× 「交付」的 2×2**（P1 用的是前一列，交付用的是后一列）：
            # `otg_not_delivered` 就是 P1 那个「+6.45 准时到网关」的去向——
            # 落在 `(B(d), d]` 这条**对交付无效的带**里。
            tab = {"otg_delivered": 0, "otg_not_delivered": 0,
                   "late_delivered": 0, "late_not_delivered": 0}
            gap_d_minus_b: list = []

            for seed in range(args.seeds):
                run = one_seed(seed, arm=arm, placement=PLACEMENT, trace=True,
                               obligation_ledger=True, **kw)
                if seed not in up_cache:
                    up_cache[seed] = predicted_up_ticks(seed, kw, end_s)
                ups = up_cache[seed]
                up_set = set(ups)
                last_tick = end_s - TICK_S
                # 实现侧真实发生过的转发时刻：逐义务台账的 `first_received_at`
                # （= 该义务首份副本被中心收到的拍）。它是**全部转发拍的一个子集**
                # （没有义务副本的转发拍不产生读数），因此只用于做**包含**检查。
                seed_realized = {row["first_received_at"] for row in run["_obligations"]
                                 if row["first_received_at"] is not None}
                realized_ticks |= seed_realized
                # **逐种子**做包含检查：真实转发拍必须落在**同一种子**的可回传拍里
                not_predicted |= (seed_realized - up_set)
                for row in run["_obligations"]:
                    oid = row["oid"]
                    h = row["first_heard_at"]
                    d = min(row["deadline"], last_tick)
                    later = [t for t in ups if t <= d]
                    b = later[-1] if later else None
                    yhat = int(h is not None and b is not None and h <= b)
                    y = int(bool(row["delivered"]))
                    margin = None if (h is None or b is None) else b - h
                    if h is None:
                        n_h_none += 1
                    if row["censored"]:
                        n_censored += 1
                    if yhat == y:
                        agree += 1
                    else:
                        disagree += 1
                        if len(out["mismatch_examples"]) < 20:
                            out["mismatch_examples"].append(
                                {"cond": cond, "arm": arm, "seed": seed, "oid": oid,
                                 "h_star": h, "deadline": row["deadline"],
                                 "last_up_tick_before_d": b, "yhat": yhat,
                                 "delivered": y, "collected": row["collected"],
                                 "censored": row["censored"],
                                 "n_heard": row["n_heard"],
                                 "n_received": row["n_received"]})
                    on_time_gw = (h is not None and h <= row["deadline"])
                    if on_time_gw and y:
                        tab["otg_delivered"] += 1
                    elif on_time_gw and not y:
                        tab["otg_not_delivered"] += 1
                    elif y:
                        tab["late_delivered"] += 1
                    else:
                        tab["late_not_delivered"] += 1
                    if b is not None:
                        gap_d_minus_b.append(row["deadline"] - b)
                    if y:
                        if margin is not None:
                            margins_del.append(margin)
                        copies_del.append(row["n_heard"])
                    else:
                        if margin is not None:
                            margins_miss.append(margin)
                        copies_miss.append(row["n_heard"])
                        if margin is not None and -CRITICAL_MARGIN_S <= margin < 0:
                            n_critical += 1
                    per_arm_rows[arm].append(
                        {"seed": seed, "oid": oid, "h_star": h, "b": b,
                         "delivered": y, "margin": margin,
                         "n_heard": row["n_heard"],
                         "n_received": row["n_received"]})

            out["reconstruction"][cond][arm] = {
                "n_predicted_up_ticks": len(ups),
                "n_realized_forward_ticks": len(realized_ticks),
                "realized_ticks_not_predicted_up": sorted(not_predicted)[:20],
                "n_realized_not_predicted": len(not_predicted)}
            out["sufficiency"][cond][arm] = {
                "agree": agree, "disagree": disagree,
                "agreement_rate": round(agree / max(1, agree + disagree), 6),
                "n_h_star_none": n_h_none, "n_censored": n_censored}
            out["margin"][cond][arm] = {
                "delivered_mean_s": _mean(margins_del),
                "delivered_min_s": min(margins_del) if margins_del else None,
                "delivered_p10_s": (sorted(margins_del)[len(margins_del) // 10]
                                    if margins_del else None),
                "missed_mean_s": _mean(margins_miss),
                "missed_max_s": max(margins_miss) if margins_miss else None,
                "n_missed_within_one_period": n_critical,
                "n_delivered": len(margins_del), "n_missed": len(margins_miss)}
            out["copies"][cond][arm] = {
                "n_heard_delivered_mean": _mean(copies_del),
                "n_heard_missed_mean": _mean(copies_miss)}
            # 末次机会距截止有多远 + 「无效带」有多大
            srt = sorted(gap_d_minus_b)
            out["ineffective_band"][cond][arm] = {
                "n_obligations": agree + disagree,
                **tab,
                # ⚠ 这一格**必须为 0**：首次到网关晚于截止却仍交付，在 store-and-forward 下
                # 不可能（`received_at <= deadline` 要求转发拍 ≤ 截止，而转发拍 ≥ 首次到网关拍）。
                "late_delivered_MUST_BE_ZERO": tab["late_delivered"],
                "band_share": round(tab["otg_not_delivered"] / max(1, agree + disagree), 6),
                "d_minus_B_mean_s": _mean(gap_d_minus_b),
                "d_minus_B_p10_s": srt[len(srt) // 10] if srt else None,
                "d_minus_B_median_s": srt[len(srt) // 2] if srt else None,
                "d_minus_B_p90_s": srt[int(len(srt) * 0.9)] if srt else None,
                "n_no_up_before_deadline": sum(1 for g in gap_d_minus_b
                                               if g is None)}

        # ---- 「被推过最后机会」的逐义务翻转分析（候选 vs fixed300）
        for cand in ("pacing_backlog900_300", "oblig_copies1", "oblig_copies3"):
            by_ref = {(r["seed"], r["oid"]): r for r in per_arm_rows["fixed300"]}
            by_c = {(r["seed"], r["oid"]): r for r in per_arm_rows[cand]}
            keys = sorted(set(by_ref) & set(by_c))
            gained, lost, both_ok = [], [], 0
            both_bad = 0
            for k in keys:
                a, b = by_ref[k], by_c[k]
                row = {"seed": k[0], "oid": k[1],
                       "h_star_ref": a["h_star"], "h_star_cand": b["h_star"],
                       "margin_ref": a["margin"], "margin_cand": b["margin"],
                       "b_ref": a["b"], "b_cand": b["b"],
                       "n_heard_ref": a["n_heard"], "n_heard_cand": b["n_heard"]}
                if a["delivered"] and b["delivered"]:
                    both_ok += 1
                elif (not a["delivered"]) and (not b["delivered"]):
                    both_bad += 1
                elif b["delivered"] and not a["delivered"]:
                    gained.append(row)
                else:
                    lost.append(row)
            lost_margins = [x["margin_ref"] for x in lost if x["margin_ref"] is not None]
            out["flips"].setdefault(cond, {})[cand] = {
                "n_matched_obligations": len(keys),
                "both_delivered": both_ok, "both_missed": both_bad,
                "n_gained": len(gained), "n_lost": len(lost),
                # 丢失者在**参照臂**下的余量：若这批余量本来很大（很早就到网关），
                # 而候选把它推过了 `B(d)`，那就是「改善非瓶颈 stage 把 failure 往后搬」。
                "lost_margin_ref_mean_s": _mean(lost_margins),
                "lost_margin_ref_max_s": max(lost_margins) if lost_margins else None,
                "lost_margin_cand_mean_s": _mean([x["margin_cand"] for x in lost]),
                "n_lost_that_were_comfortable_ref": sum(
                    1 for m in lost_margins if m > CRITICAL_MARGIN_S),
                "gained_margin_cand_mean_s": _mean([x["margin_cand"] for x in gained]),
                "gained_h_star_earlier_than_ref": sum(
                    1 for x in gained if x["h_star_cand"] is not None
                    and x["h_star_ref"] is not None and x["h_star_cand"] < x["h_star_ref"]),
                "gained_h_star_later_than_ref": sum(
                    1 for x in gained if x["h_star_cand"] is not None
                    and x["h_star_ref"] is not None and x["h_star_cand"] > x["h_star_ref"]),
                "lost_examples": lost[:10], "gained_examples": gained[:5]}
        print(f"  {cond} 重建/充分性已算（{len(ARMS)} 臂 × {args.seeds} 种子）")

    path = _os.path.join(RES, f"{args.out}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"\nwrote {path}\n")

    print("=== 重建检查：真实转发时刻是否都是预测的「可回传拍」")
    for cond in CONDITIONS:
        for arm in ARMS:
            r = out["reconstruction"][cond][arm]
            print(f"  {cond:18s} {arm:24s} 预测可回传拍 {r['n_predicted_up_ticks']:6d}"
                  f"  真实转发拍 {r['n_realized_forward_ticks']:5d}"
                  f"  落在预测之外 {r['n_realized_not_predicted']}")
    print("\n=== 充分性：ŷ = 1[h* <= B(d)] 是否逐义务等于 delivered")
    for cond in CONDITIONS:
        for arm in ARMS:
            s = out["sufficiency"][cond][arm]
            m = out["margin"][cond][arm]
            print(f"  {cond:18s} {arm:24s} 一致 {s['agree']:4d} 不一致 {s['disagree']:3d}"
                  f"  ({s['agreement_rate']:.6f})  |  交付余量 均值 {m['delivered_mean_s']}"
                  f" 最小 {m['delivered_min_s']}  |  未交付且差 {CRITICAL_MARGIN_S}s 内 "
                  f"{m['n_missed_within_one_period']}")
    print("\n=== 「准时到网关」× 「交付」：无效带 (B(d), d] 有多大")
    for cond in CONDITIONS:
        for arm in ARMS:
            t = out["ineffective_band"][cond][arm]
            print(f"  {cond:18s} {arm:24s} 准时&交付 {t['otg_delivered']:5d}"
                  f" | **准时但不交付** {t['otg_not_delivered']:4d}（占 {t['band_share']:.1%}）"
                  f" | 晚到却交付 {t['late_delivered']}（须为 0）"
                  f" | 截止−B(d) 均值 {t['d_minus_B_mean_s']} 中位 {t['d_minus_B_median_s']}")
    print("\n=== 翻转分析（候选 − fixed300，逐义务配对）")
    for cond, d in out["flips"].items():
        for cand, f in d.items():
            print(f"  {cond:18s} {cand:24s} 配对 {f['n_matched_obligations']:4d}"
                  f"  双交付 {f['both_delivered']:4d} 双未交付 {f['both_missed']:4d}"
                  f"  新增 {f['n_gained']:3d} 丢失 {f['n_lost']:3d}"
                  f"  |  丢失者在参照下的余量均值 {f['lost_margin_ref_mean_s']}"
                  f"（>1 档的 {f['n_lost_that_were_comfortable_ref']} 条）")


if __name__ == "__main__":
    main()
