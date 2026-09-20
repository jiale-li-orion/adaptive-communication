#!/usr/bin/env python3
"""make_tables.py — 由结果文件生成论文表格体。

论文里的表格体不再手写。每个表格体写入 paper/generated/，两份稿件用 `\\input` 包含它，
因此一张表只有一份数字，中英稿不会各自漂移。

生成物入库：评审人看到的就是实际使用的数字。结果文件一旦变动，必须在同一次提交里重新生成，
否则 `code/experiments/audit_tables.py` 会红。

行标签按语言各一份（两份稿件用各自的语言书写行名），数字来自同一处。

用法：
    python3 scripts/make_tables.py            # 写入 paper/generated/
    python3 scripts/make_tables.py --check    # 只比较，不写；有差异则退出非零
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
GEN = os.path.join(ROOT, "paper", "generated")
RES = os.path.join(ROOT, "results")


def load(rel: str):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def f(x: float, nd: int) -> str:
    """十进制四舍五入（ROUND_HALF_UP）。

    直接用 `%.{nd}f` 会按二进制表示决定末位：`0.3695` 的实际存储略小于 0.3695，
    于是输出 `0.369`，而人按四舍五入写 `0.370`——同一份数据产生两种写法。
    这种差异会被误读成"生成值与论文不符"，因此格式化必须在十进制上确定。
    """
    from decimal import Decimal, ROUND_HALF_UP
    q = Decimal(1).scaleb(-nd)
    return str(Decimal(repr(x)).quantize(q, rounding=ROUND_HALF_UP))


# ---------------------------------------------------------------- 各表的构造

def table_walls():
    d = load("results/r30c_walls.json")
    runs, dec = d["runs"], d["decomposition"]
    rows = [
        ("base", "dayfeed, 0.05 Wh", "1200 s/78 B"),
        ("O_bh", "dayfeed, 0.05 Wh", "unlimited"),
        ("O_en", "always-300, 0.50 Wh", "1200 s/78 B"),
        ("O_bo", "always-300, 0.50 Wh", "unlimited"),
    ]
    zh = {"base": "base", "O_bh": "$O_{bh}$", "O_en": "$O_{en}$", "O_bo": "$O_{bo}$"}
    zh_cfg = {"base": "dayfeed, 0.05 Wh", "O_bh": "dayfeed, 0.05 Wh",
              "O_en": "always-300, 0.50 Wh", "O_bo": "always-300, 0.50 Wh"}
    zh_bh = {"base": "1200 s/78 B", "O_bh": "无限", "O_en": "1200 s/78 B", "O_bo": "无限"}
    en_head = {"base": "base", "O_bh": "$O_{bh}$", "O_en": "$O_{en}$", "O_bo": "$O_{bo}$"}
    en, zh_rows = [], []
    for key, energy, bh in rows:
        r = runs[key]
        en.append(f"{en_head[key]} & {energy} & {bh} & {r['delivered']} ({f(r['svc'], 3)})")
        zh_rows.append(f"{zh[key]} & {zh_cfg[key]} & {zh_bh[key]} & {r['delivered']} ({f(r['svc'], 3)})")
    head_en = "Run & Sampling/Energy & Backhaul & Delivered"
    head_zh = "配置 & 采样/能量 & 回传 & 交付"
    return {"en": (head_en, en), "zh": (head_zh, zh_rows),
            "meta": {"backhaul_only": dec["backhaul_only"], "energy_only": dec["energy_only"],
                     "coupled": dec["coupled"], "base_failures": dec["base_failures"]}}


def table_expiry():
    d = load("results/r41_expiry_equiv.json")["queues"]
    order = ["fifo", "latest_only", "generic_expiry", "deadline_purge"]
    lab = {"en": {"fifo": "FIFO (baseline)", "latest_only": "latest-only (AoI)",
                  "generic_expiry": "\\texttt{generic-expiry}$^{\\dagger}$",
                  "deadline_purge": "\\texttt{deadline-purge}$^{\\ddagger}$"},
           "zh": {"fifo": "FIFO（基线）", "latest_only": "latest-only（AoI）",
                  "generic_expiry": "\\texttt{generic-expiry}$^{\\dagger}$",
                  "deadline_purge": "\\texttt{deadline-purge}$^{\\ddagger}$"}}
    out = {}
    for lang, head in (("en", "Edge disposition & Full svc & Outage OT & Expired & Deaths"),
                       ("zh", "边缘处置 & 全时段服务 & 中断按期 & 过期备份 & 死亡")):
        rows = [f"{lab[lang][q]} & {f(d[q]['svc_mean'], 3)} & {d[q]['outage_d_total']} & "
                f"{d[q]['backup_late']} & {d[q]['dead_total']}" for q in order]
        out[lang] = (head, rows)
    out["meta"] = {"seeds": 10}
    return out


def table_lease():
    """配置终止线：以**修正后的当前证据** `results/c5_matrix.json` 为源。

    `r48_ttl_vs_lease.json` 里的 `delivery_geo` 行（候选交付推导界）用的是修正前的预测账本
    （缺电池容量截断），其"零死亡且黄级交付不减"的读数已随 C5 修正撤回；该文件仍在
    `results/README.md` 登记为历史证据，但不再作为本表的数字来源。
    """
    d = load("results/c5_matrix.json")
    phases = load("results/r48_ttl_vs_lease.json")["phases"]   # 相位参数不在矩阵里，仍取登记过的来源
    h = lambda sec: sec // 3600
    PEAK = "0.012"
    # 三臂逐格相同（修正矩阵把它作为一条结论登记），表里只列一条并在说明里写明
    ARMS = ["all_sparse", "nightfloor", "valid_until", "ttl4", "ttl8", "energy_lease"]

    def label(lang, arm, up_h, down_h):
        names = {
            "all_sparse": {"en": "never dense (blue only)", "zh": "从不密集（仅蓝级）"},
            "nightfloor": {"en": f"clock guard (sunset {12}~h)", "zh": f"时钟门（日落 {12}~h）"},
            "valid_until": {"en": f"announced validity ({down_h}~h, Task~1)",
                            "zh": f"预告有效期（{down_h}~h，任务~1）"},
            "ttl4": {"en": f"fixed TTL 4~h (revert {up_h + 4}~h)",
                     "zh": f"固定 TTL 4~h（退回 {up_h + 4}~h）"},
            "ttl8": {"en": f"fixed TTL 8~h (revert {up_h + 8}~h)",
                     "zh": f"固定 TTL 8~h（退回 {up_h + 8}~h）"},
            "energy_lease": {"en": "energy gate, open-loop bound", "zh": "能量门（开环界）"},
        }
        txt = names[arm][lang]
        if arm == "nightfloor":
            return {"en": "clock guard (sunset 12~h)", "zh": "时钟门（日落 12~h）"}[lang]
        return txt

    def sep(lang, ph):
        up, dn = h(phases[ph]["up"]), h(phases[ph]["down"])
        a, b = phases[ph]["out_start"], phases[ph]["out_start"] + phases[ph]["out_hours"]
        if lang == "en":
            return ("\\emph{Phase %s, overcast $\\eta{=}%s$, seeds 0--2 (upgrade %d~h, "
                    "downgrade %d~h, outage %d--%d~h)}" % (ph, PEAK, up, dn, a, b))
        return ("\\emph{相位 %s，阴雨 $\\eta{=}%s$，种子 0--2（升级 %d~h、降级 %d~h、中断 %d--%d~h）}"
                % (ph, PEAK, up, dn, a, b))

    head = {"en": "Local revert bound & Deaths (3 seeds) & Mean svc & Mean final SoC "
                  "& Yellow delivered / total",
            "zh": "本地退回界 & 死亡（3 种子） & 平均服务 & 最终 SoC & 黄级交付 / 总数"}
    out = {}
    for lang in ("en", "zh"):
        rows = []
        for ph in ("A", "B"):
            up_h = h(phases[ph]["up"])
            down_h = h(phases[ph]["down"])
            rows.append("\\multicolumn{5}{l}{%s}\\\\" % sep(lang, ph))
            for arm in ARMS:
                r = d["cells"][f"{ph}|{PEAK}|{arm}"]
                bold = (lambda x: "\\textbf{%s}" % x) if arm in ("ttl8", "energy_lease") \
                    else (lambda x: x)
                rows.append(f"{label(lang, arm, up_h, down_h)} & {bold(str(r['dead_total']))} & "
                            f"{bold(f(r['svc_mean'], 4))} & {f(r['mean_final_soc'], 5)} & "
                            f"{bold('%d/%d' % (r['yellow_delivered_total'], r['yellow_n_total']))}")
            if ph == "A":
                rows.append("\\midrule")
        out[lang] = (head[lang], rows)
    return {"en": out["en"], "zh": out["zh"],
            "meta": {"peak": PEAK, "seeds": 3, "source": "results/c5_matrix.json",
                     "yellow_A": d["cells"][f"A|{PEAK}|ttl8"]["yellow_n_total"],
                     "yellow_B": d["cells"][f"B|{PEAK}|ttl8"]["yellow_n_total"],
                     "upgrade_h_A": h(phases["A"]["up"]), "upgrade_h_B": h(phases["B"]["up"])}}


def table_attribution():
    d = load("results/r40_local_attribution.json")
    truth, on = d["truth_segments"], d["online"]["segments"]
    seg = [("S_time", "\\stime"), ("S_cap", "\\scap"),
           ("S_access", "\\saccess"), ("S_energy", "\\senergy")]
    lab = {"en": {"S_time": " (no return slot; geometry)",
                  "S_cap": " (heard by deadline, not returned)",
                  "S_access": " (heard after deadline)", "S_energy": " (no qualified sample)"},
           "zh": {"S_time": "（无回传槽，几何）", "S_cap": "（按期听到但未回传）",
                  "S_access": "（晚于期限听到）", "S_energy": "（无合格样本）"}}
    unknown = {"en": "\\unk (not separable online)", "zh": "\\unk（在线不可分离）"}
    tail = {"en": ["Total", "Labelled coverage", "Precision on labelled subset"],
            "zh": ["合计", "标注覆盖率", "已标注子集精度"]}
    out = {}
    for lang in ("en", "zh"):
        rows = []
        for key, macro in seg:
            ov = str(truth[key])
            onv = str(on[key]) if on.get(key) is not None else "--- (unknown)"
            rows.append(f"{macro}{lab[lang][key]} & {ov} & {onv}")
        rows.append(f"{unknown[lang]} & --- & {d['online']['unknown']}")
        rows.append("\\midrule")
        rows.append(f"{tail[lang][0]} & {d['n_past_deadline']} & {d['n_past_deadline']}")
        rows.append(f"{tail[lang][1]} & 100\\% & {f(100*d['online']['coverage'], 1)}\\%")
        rows.append(f"{tail[lang][2]} & {f(d['offline']['accuracy'], 3)} & "
                    f"{f(d['online']['labelled_accuracy'], 3)}")
        out[lang] = ({"en": "Segment & Offline truth & Online at $t_a$",
                      "zh": "段 & 离线真值 & 在线（$t_a$）"}[lang], rows)
    out["meta"] = {"coverage": d["online"]["coverage"], "unknown": d["online"]["unknown"]}
    return out


def table_placement():
    d = load("results/agent_traces/r39_table.json")["aggregate"]
    by = {a["arm"]: a for a in d}
    order = ["comply", "dayfeed-c", "env-comply", "comply+floor",
             "dayfeed-c+floor", "env-comply+floor", "pure-local"]
    lab = {"en": {"comply": "comply (naive, unprotected)",
                  "dayfeed-c": "dayfeed-c (centre day/night rule)",
                  "env-comply": "envelope(comply), centre only",
                  "comply+floor": "comply + local guard",
                  "dayfeed-c+floor": "dayfeed-c + local guard",
                  "env-comply+floor": "envelope(comply) + local guard",
                  "pure-local": "pure-local (pre-provisioned, 0 cmds)"},
           "zh": {"comply": "comply（朴素，无保护）",
                  "dayfeed-c": "dayfeed-c（中心昼夜规则）",
                  "env-comply": "envelope(comply)，仅中心",
                  "comply+floor": "comply + 本地门",
                  "dayfeed-c+floor": "dayfeed-c + 本地门",
                  "env-comply+floor": "envelope(comply) + 本地门",
                  "pure-local": "pure-local（预置，0 命令）"}}
    head = {"en": "Configuration & Mean svc & Deaths & Cmds sent & Refused",
            "zh": "配置（除注明外均在中心） & 平均服务 & 死亡 & 发送 & 被拒"}
    out = {}
    for lang in ("en", "zh"):
        rows = []
        for a in order:
            r = by[a]
            bold = (lambda s: "\\textbf{%s}" % s) if a in ("env-comply+floor", "pure-local") else (lambda s: s)
            rows.append(f"{bold(lab[lang][a])} & {bold(f(r['svc_mean'], 3))} & {bold(str(r['dead_total']))} & "
                        f"{bold(str(r['sent_total']))} & {bold(str(r['refused_total']))}")
            if a == "env-comply+floor":
                rows.append("\\midrule")
        out[lang] = (head[lang], rows)
    out["meta"] = {"arms": len(order)}
    return out


def facts() -> dict:
    """正文与表说明里出现的 C5 数字，全部由结果文件算出并写成宏。

    正文里"手抄一个数"与生成表体里"手抄一个数"是同一类问题，因此这里把口径要求的数字一并
    生成：稿件只允许写 `\\cFive...` 宏，具体取值由本函数从 `results/c5_matrix.json` 取出。
    """
    d = load("results/c5_matrix.json")
    PEAK = "0.012"
    cell = lambda ph, arm: d["cells"][f"{ph}|{PEAK}|{arm}"]
    defs = {
        "cFivePeak": str(PEAK),
        "cFiveSeeds": "3",
        "cFiveYellowNA": str(cell("A", "ttl8")["yellow_n_total"]),
        "cFiveYellowNB": str(cell("B", "ttl8")["yellow_n_total"]),
        "cFiveTtlEightYellowA": str(cell("A", "ttl8")["yellow_delivered_total"]),
        "cFiveTtlEightYellowB": str(cell("B", "ttl8")["yellow_delivered_total"]),
        "cFiveTtlEightDeadA": str(cell("A", "ttl8")["dead_total"]),
        "cFiveTtlEightDeadB": str(cell("B", "ttl8")["dead_total"]),
        "cFiveEnergyYellowA": str(cell("A", "energy_lease")["yellow_delivered_total"]),
        "cFiveEnergyYellowB": str(cell("B", "energy_lease")["yellow_delivered_total"]),
        "cFiveEnergyDeadA": str(cell("A", "energy_lease")["dead_total"]),
        "cFiveEnergyDeadB": str(cell("B", "energy_lease")["dead_total"]),
        "cFiveNightfloorDeadA": str(cell("A", "nightfloor")["dead_total"]),
        "cFiveNightfloorDeadB": str(cell("B", "nightfloor")["dead_total"]),
        "cFiveAllSparseYellowA": str(cell("A", "all_sparse")["yellow_delivered_total"]),
        "cFiveEnergyLostA": str(cell("A", "ttl8")["yellow_delivered_total"]
                                - cell("A", "energy_lease")["yellow_delivered_total"]),
        "cFiveEnergyLostB": str(cell("B", "ttl8")["yellow_delivered_total"]
                                - cell("B", "energy_lease")["yellow_delivered_total"]),
        "cFiveTtlFourYellowA": str(cell("A", "ttl4")["yellow_delivered_total"]),
        "cFiveTtlFourYellowB": str(cell("B", "ttl4")["yellow_delivered_total"]),
        "cFiveTtlFourLostB": str(cell("B", "ttl8")["yellow_delivered_total"]
                                - cell("B", "ttl4")["yellow_delivered_total"]),
        "cFiveValidUntilYellowA": str(cell("A", "valid_until")["yellow_delivered_total"]),
        "cFiveValidUntilYellowB": str(cell("B", "valid_until")["yellow_delivered_total"]),
        "cFiveTtlFourRevertA": "6", "cFiveTtlEightRevertA": "10",
        "cFiveTtlFourRevertB": "5", "cFiveTtlEightRevertB": "9",
    }
    # C3（记录到期）：数字取自修正后的 results/r37e_full_seeds.json
    r37 = load("results/r37e_full_seeds.json")
    ss, pp = r37["summary"], r37["paired_purge_minus_fifo"]
    defs.update({
        "cThreeSeedZeroFifo": str(r37["per_seed"]["s0/fifo"]["d"]),
        "cThreeSeedZeroPurge": str(r37["per_seed"]["s0/deadline_purge"]["d"]),
        "cThreeTenSeedFifo": str(ss["fifo"]["outage_on_time_total"]),
        "cThreeTenSeedPurge": str(ss["deadline_purge"]["outage_on_time_total"]),
        "cThreeRatio": f(ss["deadline_purge"]["outage_on_time_total"]
                         / ss["fifo"]["outage_on_time_total"], 2),
        "cThreeExpiredFifo": str(ss["fifo"]["expired_total"]),
        "cThreeExpiredPurge": str(ss["deadline_purge"]["expired_total"]),
        "cThreeDeathsFifo": str(ss["fifo"]["deaths_total"]),
        "cThreeDeathsPurge": str(ss["deadline_purge"]["deaths_total"]),
        "cThreePairedPoints": f(pp["mean_points"], 2),
        "cThreePairedLo": f(pp["ci95_points"][0], 2),
        "cThreePairedHi": f(pp["ci95_points"][1], 2),
        "cThreeSvcFifo": f(ss["fifo"]["svc_mean"], 3),
        "cThreeSvcPurge": f(ss["deadline_purge"]["svc_mean"], 3),
        "cThreeLatestDelta": f(100 * (ss["deadline_purge"]["svc_mean"]
                                      - ss["latest_only"]["svc_mean"]), 2),
    })
    # 同信息停止参照只支持声明模型内的限定结论；正文使用生成统计量。
    seq = load("results/c5_seqref.json")
    priced = [p for cell in seq["cells"].values() for p in cell["priced"].values()]
    defs.update({
        "cNineCells": str(len(seq["cells"])),
        "cNineWeights": str(len(seq["death_penalties"])),
        "cNineComparisons": str(len(priced)),
        "cNineServiceMatches": str(sum(abs(p["gaps"]["service_implementable"]) < 1e-9
                                       for p in priced)),
    })
    lines = ["%% 由 scripts/make_tables.py 生成，勿手改；取值来自 C3/C5/C9 的在册结果。",
             "%% 正文与表说明里的这些数字只允许写成这些宏。"]
    for k in sorted(defs):
        lines.append("\\newcommand{\\%s}{%s}" % (k, defs[k]))
    return "\n".join(lines) + "\n", {"source": "results/c5_matrix.json", "peak": PEAK,
                                     "sources": ["results/c5_matrix.json", "results/r37e_full_seeds.json",
                                                 "results/c5_seqref.json"],
                                     "definitions": defs}


TABLES = {
    "walls": table_walls,
    "expiry": table_expiry,
    "lease": table_lease,
    "attribution": table_attribution,
    "placement": table_placement,
}


COLPEC = {"walls": "llcc", "expiry": "lcccc", "lease": "lcccc",
          "attribution": "lcc", "placement": "lcccc"}


def render(name: str, head: str, rows: list[str]) -> str:
    """拼出表格体。行尾统一补 `\\\\`，规则命令与已带行尾的命令不动。"""
    out = ["\\toprule", head + "\\\\", "\\midrule"]
    for r in rows:
        rs = r.rstrip()
        if rs in ("\\midrule", "\\bottomrule") or rs.endswith("\\\\"):
            out.append(r)
        else:
            out.append(r + "\\\\")
    out.append("\\bottomrule")
    body = "\n".join(out)
    return ("%% 由 scripts/make_tables.py 生成，勿手改；数字来自结果文件。\n"
            "\\begin{tabular}{%s}\n%s\n\\end{tabular}\n" % (COLPEC[name], body))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只比较，不写")
    args = ap.parse_args()

    os.makedirs(GEN, exist_ok=True)
    stale, written = [], []
    for name, fn in TABLES.items():
        spec = fn()
        for lang in ("en", "zh"):
            head, rows = spec[lang]
            text = render(name, head, rows)
            path = os.path.join(GEN, f"table_{name}.{lang}.tex")
            old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
            if old == text:
                continue
            if args.check:
                stale.append(os.path.relpath(path, ROOT))
            else:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
                written.append(os.path.relpath(path, ROOT))
        if not args.check:
            meta_path = os.path.join(GEN, f"table_{name}.meta.json")
            with open(meta_path, "w", encoding="utf-8") as fh:
                json.dump(spec["meta"], fh, ensure_ascii=False, indent=2, sort_keys=True)

    # 数字宏文件：正文与表说明里的 C5 数字只允许写这些宏
    facts_text, facts_meta = facts()
    fp = os.path.join(GEN, "facts.tex")
    fold = open(fp, encoding="utf-8").read() if os.path.exists(fp) else None
    if fold != facts_text:
        if args.check:
            stale.append(os.path.relpath(fp, ROOT))
        else:
            with open(fp, "w", encoding="utf-8") as fh:
                fh.write(facts_text)
            written.append(os.path.relpath(fp, ROOT))
    if not args.check:
        with open(os.path.join(GEN, "facts.meta.json"), "w", encoding="utf-8") as fh:
            json.dump(facts_meta, fh, ensure_ascii=False, indent=2, sort_keys=True)

    if args.check:
        if stale:
            print("生成物与结果文件不一致，需要重新生成：")
            for s in stale:
                print(f"  {s}")
            print("\n运行 python3 scripts/make_tables.py 后与结果变动一起提交。")
            return 1
        print("生成物与结果文件一致")
        return 0
    if written:
        print("已写入：")
        for w in written:
            print(f"  {w}")
    else:
        print("生成物已是最新，无改动")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
