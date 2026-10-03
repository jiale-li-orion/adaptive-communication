"""P3 的第二、三项交付：**保留种子复核** 与 **正例/无效例的完整时间线**（doc 58 §P3）。

两件事都**先写定规则**：

* **保留种子复核（A 部分）**：doc 58 §P3 规定保留种子只在「候选及参数确定后」使用。
  本轮**没有候选晋级**，因此保留种子**不用于任何晋级判断**；它只被用来检验
  doc 61 §2.3 那条**已在开发种子上成立**的读数是不是**种子特异**的：
  *预注册判据*——在未参与开发的种子 20–39 上，若 `oblig_copies1` 相对
  `pacing_backlog900_300` 的**服务劣势消失**（配对区间含 0），则 doc 61 §2.3 的
  「同一上行预算下副本信号更差」必须**收窄为开发种子特有**。
* **时间线（B 部分）**：doc 58 §P3 要求「所读证据 → 目标产生 → 命令生效 → 具体义务改变」
  的完整链条，且**正例与无效例各一个**。链条用**单种子**逐事件展开，
  因此它**只是例证**，判决仍由 20 种子的配对统计承担。
  选中哪条义务的规则也先写定：**正例**取「在 `oblig_copies3` 下准时送达、
  而在 `pacing_backlog900_300` 下未准时送达」的**编号最小**的那条义务；
  **无效例**取同一条义务在 `oblig_slack` 与其**逐位相同的**消融下的读数。

诊断用的「所读证据」记录器**只读不改**：它包在 `plan` 外面抄一份视图字段，
脚本会**逐位核对**加与不加记录器时两次运行的读数相同。

    python3 code/analysis/p3_timeline_heldout.py
"""
from __future__ import annotations

import json
import os as _os
import random
import sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, _CODE, *(_os.path.join(_CODE, d) for d in
                          ("physics", "runtime", "experiments", "analysis",
                           "monitoring", "instance"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

import center as C                                                       # noqa: E402
from instance_run import one_seed                                        # noqa: E402
from trace_seed_timeline import build_kwargs                             # noqa: E402

RES = _os.path.normpath(_os.path.join(_CODE, "..", "results"))
BASE_TAG = "instance_ccorral_iid_c0.05"
PLACEMENT = "gateway"
DWELL = 600
HELDOUT = tuple(range(20, 40))          # 未参与开发的保留种子
DEV_RULE = ("若在种子 20-39 上 oblig_copies1 相对 pacing_backlog900_300 的服务劣势"
            "区间含 0，则 doc 61 §2.3 收窄为开发种子特有")
CONDITIONS = {
    "P0_no_outage": dict(access_outage_h=0.0, access_outage_start_h=4.0,
                         outage_hours=0.0, outage_start_h=0.0),
    "P1_backhaul_4h7h": dict(access_outage_h=0.0, access_outage_start_h=4.0,
                             outage_hours=3.0, outage_start_h=4.0),
    "P2_access_4h7h": dict(access_outage_h=3.0, access_outage_start_h=4.0,
                           outage_hours=0.0, outage_start_h=0.0),
}
HELD_ARMS = ("fixed300", "pacing_backlog900_300", "oblig_copies1")
VIEW_FIELDS = ("gateway_pending_depth", "gateway_oldest_pending_age_s",
               "gateway_last_forward_ok_at", "gateway_copies_in_window")


def _register() -> None:
    C.ARMS["fixed300"] = lambda: C.FixedPeriodPolicy(300, dwell_s=DWELL)
    C.ARMS["pacing_backlog900_300"] = (
        lambda: C.ReportPacingPolicy(slow_s=900, fast_s=300, dwell_s=DWELL,
                                     mode="pending_backlog"))
    C.ARMS["oblig_copies1"] = (
        lambda: C.ObligationCopiesPolicy(k=1, fast_s=300, slow_s=900, dwell_s=DWELL))
    C.ARMS["oblig_copies3"] = (
        lambda: C.ObligationCopiesPolicy(k=3, fast_s=300, slow_s=900, dwell_s=DWELL))
    C.ARMS["oblig_slack"] = (
        lambda: C.ObligationSlackPolicy(fast_s=300, slow_s=900, dwell_s=DWELL,
                                        obligation_period_s=900, command_delay_s=600))


def _mean(xs):
    v = [x for x in xs if x is not None]
    return round(sum(v) / len(v), 6) if v else None


def _boot(d, n=2000, seed=0):
    if not d:
        return None
    rnd = random.Random(seed)
    k = len(d)
    m = sorted(_mean([d[rnd.randrange(k)] for _ in range(k)]) for _ in range(n))
    return [round(m[int(0.025 * n)], 4), round(m[int(0.975 * n) - 1], 4)]


def part_a(base: dict, out: dict) -> None:
    print("\n=== A 保留种子复核（种子 20-39，不用于晋级）")
    print("预注册判据：" + DEV_RULE)
    out["heldout"] = {"seeds": list(HELDOUT), "rule": DEV_RULE, "conditions": {}}
    for cond, over in CONDITIONS.items():
        kw = {**base, **over}
        runs = {a: [one_seed(s, arm=a, placement=PLACEMENT, **kw) for s in HELDOUT]
                for a in HELD_ARMS}
        block = {}
        for a in HELD_ARMS:
            block[a] = {"service": _mean([r["routine"]["delivered"] for r in runs[a]]),
                        "uplinks": _mean([r["communication"]["uplinks"] for r in runs[a]]),
                        "missing_collection": _mean(
                            [r["routine"]["missing_collection"] for r in runs[a]])}
        d_s = [x["routine"]["delivered"] - y["routine"]["delivered"]
               for x, y in zip(runs["oblig_copies1"], runs["pacing_backlog900_300"])]
        d_u = [x["communication"]["uplinks"] - y["communication"]["uplinks"]
               for x, y in zip(runs["oblig_copies1"], runs["pacing_backlog900_300"])]
        block["paired_copies1_minus_backlog"] = {
            "service": {"mean": _mean(d_s), "ci95": _boot(d_s, seed=hash(cond) % 9999),
                        "n_pos": sum(1 for x in d_s if x > 0),
                        "n_neg": sum(1 for x in d_s if x < 0)},
            "uplinks": {"mean": _mean(d_u), "ci95": _boot(d_u, seed=hash(cond) % 7919),
                        "n_pos": sum(1 for x in d_u if x > 0),
                        "n_neg": sum(1 for x in d_u if x < 0)}}
        out["heldout"]["conditions"][cond] = block
        si = block["paired_copies1_minus_backlog"]["service"]
        ui = block["paired_copies1_minus_backlog"]["uplinks"]
        verdict = ("服务劣势在保留种子上**复现**（区间不含 0）"
                   if si["ci95"] and si["ci95"][1] < 0 else
                   "服务劣势**未在保留种子上复现** ⇒ doc 61 §2.3 须收窄")
        print(f"  {cond}: 服务 Δ{si['mean']:+.2f} CI {si['ci95']} ({si['n_pos']}/{si['n_neg']})"
              f" | 上行 Δ{ui['mean']:+.1f} CI {ui['ci95']} ({ui['n_pos']}/{ui['n_neg']})"
              f" ⇒ {verdict}")
        block["verdict"] = verdict


def part_b(base: dict, out: dict) -> None:
    """**正例与无效例的完整时间线**（单种子例证）。

    记录器通过 `ARMS` 注册（`one_seed` 不接受现成策略对象）：注册一个 `_rec_<臂>`
    工厂，返回的策略把 `plan` 包一层——**先抄视图字段、再原样调用原 `plan`、把命令原样返回**。
    脚本随后**逐位核对**带记录器与不带记录器两次运行的读数相同（`recorder_is_read_only`），
    因此记录动作本身不会制造任何差异。
    """
    print("\n=== B 完整时间线（单种子例证；判决仍由 20 种子统计承担）")
    seed = 0
    kw = {**base, **CONDITIONS["P1_backhaul_4h7h"]}
    ARMS_TO_TRACE = ("fixed300", "pacing_backlog900_300", "oblig_copies3",
                     "oblig_slack", "oblig_copies1")

    def record_factory(arm: str, sink: list):
        def build():
            pol = C.ARMS[arm]()
            inner = pol.plan

            def wrapped(view):
                cmds = inner(view)
                sink.append({
                    "t_s": view.t_s,
                    "pending_depth": view.gateway_pending_depth,
                    "oldest_pending_age_s": view.gateway_oldest_pending_age_s,
                    "last_forward_ok_at": view.gateway_last_forward_ok_at,
                    "copies_in_window": dict(view.gateway_copies_in_window or {}),
                    "cmds": [(n, p.get("period_s")) for n, p in cmds]})
                return cmds
            pol.plan = wrapped
            return pol
        return build

    runs, views = {}, {}
    for a in ARMS_TO_TRACE:
        sink: list = []
        C.ARMS[f"_rec_{a}"] = record_factory(a, sink)
        runs[a] = one_seed(seed, arm=f"_rec_{a}", placement=PLACEMENT, trace=True,
                           obligation_ledger=True, **kw)
        views[a] = sink

    # 仪器自检：带记录器 ≡ 不带记录器（逐位）
    same = {}
    for a in ARMS_TO_TRACE:
        plain = one_seed(seed, arm=a, placement=PLACEMENT, trace=True,
                         obligation_ledger=True, **kw)
        same[a] = (plain["routine"] == runs[a]["routine"]
                   and plain["communication"] == runs[a]["communication"]
                   and plain["_obligations"] == runs[a]["_obligations"])
    out["timeline"] = {"seed": seed, "condition": "P1_backhaul_4h7h",
                       "recorder_is_read_only": same, "examples": {}}
    print(f"  记录器只读自检（逐位相同）：{same}")
    assert all(same.values()), "记录器改变了运行 ⇒ 时间线不可用"

    def rows(run):
        return {r["oid"]: r for r in run["_obligations"]}

    r3, rb, rsl, r1 = (rows(runs["oblig_copies3"]), rows(runs["pacing_backlog900_300"]),
                       rows(runs["oblig_slack"]), rows(runs["oblig_copies1"]))
    # **选中规则先写定**：copies3 准时送达而 backlog 未准时送达的、编号最小的义务
    flips = sorted(oid for oid in r3
                   if r3[oid]["received_on_time"] and not rb[oid]["received_on_time"])
    print(f"  正例候选（copies3 准时送达 ∧ backlog 未准时送达）：{len(flips)} 条")
    ex: dict = {"n_flip_obligations": len(flips)}
    if flips:
        oid = flips[0]
        ob3, obb, obs = r3[oid], rb[oid], rsl[oid]
        node = ob3["node_id"]
        lo, hi = ob3["release_at"] - 2700, ob3["deadline"] + 1800
        keep = ("release_at", "deadline", "first_heard_at", "first_received_at",
                "heard_on_time", "received_on_time", "delivered", "n_heard", "n_received")
        chain = []
        for e in runs["oblig_copies3"]["_trace"]:
            if e[1] != node or not (lo <= e[0] <= hi):
                continue
            if e[2] == "plan":
                chain.append({"t_s": e[0], "kind": "plan", "op": e[4], "value": e[5],
                              "soc_seen": e[3], "soc_age_s": e[6],
                              "reason": e[7] if len(e) > 7 else None})
            elif e[2] == "sent":
                chain.append({"t_s": e[0], "kind": "sent", "logical": e[3],
                              "op": e[4], "value": e[5]})
            elif e[2] == "applied":
                chain.append({"t_s": e[0], "kind": "applied", "field": e[3],
                              "value": e[4], "logical": e[5]})
        ex.update({
            "oid": oid, "node": node, "release_at": ob3["release_at"],
            "deadline": ob3["deadline"], "window_s": [lo, hi],
            "obligation_by_arm": {
                "oblig_copies3": {k: ob3[k] for k in keep},
                "pacing_backlog900_300": {k: obb[k] for k in keep},
                "oblig_slack": {k: obs[k] for k in keep}},
            "chain": chain,
            # **所读证据**：该节点在该窗口内每次决策前合法看到的量
            "evidence_read": [
                {"t_s": v["t_s"], "pending_depth": v["pending_depth"],
                 "oldest_pending_age_s": v["oldest_pending_age_s"],
                 "last_forward_ok_at": v["last_forward_ok_at"],
                 "copies_in_window": v["copies_in_window"].get(node),
                 "cmds": v["cmds"]}
                for v in views["oblig_copies3"]
                if lo <= v["t_s"] <= hi and any(n == node for n, _ in v["cmds"])],
            "null_example": {
                "claim": ("同一条义务在 oblig_slack 与 oblig_copies1 下**逐位相同**"
                          "（doc 61 §3 的退化）：候选的两条区分支在本轮参数下不可达"),
                "slack_equals_copies1_obligations": (rsl[oid] == r1[oid]),
                "slack_equals_copies1_routine": (runs["oblig_slack"]["routine"]
                                                 == runs["oblig_copies1"]["routine"]),
                "slack_equals_copies1_communication": (
                    runs["oblig_slack"]["communication"]
                    == runs["oblig_copies1"]["communication"])},
        })
        out["timeline"]["examples"]["positive"] = ex
        print(f"  正例义务 {oid}（节点 {node}）：release {ob3['release_at']} "
              f"deadline {ob3['deadline']}")
        print(f"    copies3 首次到网关 {ob3['first_heard_at']} / 到中心 "
              f"{ob3['first_received_at']}（准时 {ob3['received_on_time']}）")
        print(f"    backlog 首次到网关 {obb['first_heard_at']} / 到中心 "
              f"{obb['first_received_at']}（准时 {obb['received_on_time']}）")
        print(f"    链条 {len(chain)} 条事件，证据行 {len(ex['evidence_read'])} 条；"
              f"无效例逐位相同 = {ex['null_example']['slack_equals_copies1_routine']}")
    else:
        print("  本种子没有正例 ⇒ 按 doc 58 §P3 交付否证链（见 doc 62）")
    return out


def main() -> None:
    _register()
    cfg = json.load(open(_os.path.join(RES, f"{BASE_TAG}.json"), encoding="utf-8"))["config"]
    base = build_kwargs(dict(cfg))
    base.pop("trace", None)
    base.pop("cache_service", None)
    out = {"base": BASE_TAG, "placement": PLACEMENT, "dwell_s": DWELL}
    part_a(base, out)
    part_b(base, out)
    path = _os.path.join(RES, "p3_timeline_heldout.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
