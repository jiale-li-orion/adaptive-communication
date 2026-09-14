"""论文图：`n01:routine:00004` —— 副本数相同、最后一次机会相同，只有首次到达不同。

数据**只来自已登记结果**（`results/first_heard_sufficiency.json`），不改仿真器、不重跑。
脚本先**断言**这条反例的不变式（两臂 `n_heard` 相同、`B(d)` 相同、`h*` 不同），
因此图**不可能**在数据漂移后继续画出一个漂亮的假故事。

    python3 code/analysis/fig_first_heard_counterexample.py

写 `results/figures/fig_first_heard_counterexample.png` 与同名 `.svg`。
"""
from __future__ import annotations

import json
import os as _os
import sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
RES = _os.path.normpath(_os.path.join(_CODE, "..", "results"))
FIGDIR = _os.path.join(RES, "figures")
COND = "P1_backhaul_4h7h"
CAND = "pacing_backlog900_300"
REF = "fixed300"


def load_example() -> dict:
    with open(_os.path.join(RES, "first_heard_sufficiency.json"), encoding="utf-8") as fh:
        d = json.load(fh)
    lost = d["flips"][COND][CAND]["lost_examples"]
    assert lost, "已登记结果里没有该反例（数据结构变了？）"
    ex = lost[0]
    # ---- 不变式：这条图之所以有解释力，全靠这三条同时成立
    assert ex["n_heard_ref"] == ex["n_heard_cand"], (
        f"副本数不再相同（{ex['n_heard_ref']} vs {ex['n_heard_cand']}）⇒ 本图失效")
    assert ex["b_ref"] == ex["b_cand"], (
        f"最后一次可回传机会不再相同（{ex['b_ref']} vs {ex['b_cand']}）⇒ 本图失效")
    assert ex["h_star_ref"] < ex["h_star_cand"], "首次到达不再是「参照更早」⇒ 本图失效"
    assert ex["margin_ref"] >= 0 > ex["margin_cand"], (
        "余量符号不再是「一条过线一条不过」⇒ 本图失效")
    return {"oid": ex["oid"], "seed": ex["seed"], "d": ex["b_ref"],
            "rows": [
                {"arm": REF, "h": ex["h_star_ref"], "margin": ex["margin_ref"],
                 "n_heard": ex["n_heard_ref"], "ok": True},
                {"arm": CAND, "h": ex["h_star_cand"], "margin": ex["margin_cand"],
                 "n_heard": ex["n_heard_cand"], "ok": False}]}


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ex = load_example()
    fig, ax = plt.subplots(figsize=(9.6, 3.4))
    d = ex["d"]
    lo, hi = min(r["h"] for r in ex["rows"]) - 1100, max(r["h"] for r in ex["rows"]) + 2400
    Y = (1.05, 0.30)                      # 两行的 y 位置，**必须落在 ylim 之内**
    ax.set_ylim(-0.05, 1.75)
    ax.set_xlim(lo, hi)

    ax.axvline(d, color="black", ls="--", lw=1.6, zorder=1)
    ax.annotate(f"$d = B(d) = {d}$ s\n(deadline = last available backhaul opportunity)",
                xy=(d, 1.62), xytext=(d - 260, 1.60), fontsize=9, ha="right", va="center",
                arrowprops=dict(arrowstyle="->", lw=1.0))

    for i, r in enumerate(ex["rows"]):
        y = Y[i]
        late = r["h"] > d
        col = "#c0392b" if late else "#1e8449"
        end = d if not late else r["h"]
        ax.plot([r["h"], end], [y, y], color=col, lw=9, solid_capstyle="butt",
                alpha=0.85, zorder=3)
        ax.plot([r["h"]], [y], marker="o", ms=11, color=col, zorder=4)
        ax.text(r["h"], y + 0.14, f"$h^* = {r['h']}$ s", ha="center", fontsize=10.5,
                color=col, fontweight="bold")
        verdict = "delivered" if r["ok"] else "missed"
        # 文字起点必须避开本行的标记点（迟到那一行的标记在 d 右侧）
        ax.text(max(d + 160, r["h"] + 240), y,
                f"margin {r['margin']:+d} s   {verdict}", fontsize=10.5,
                va="center", color=col, fontweight="bold")
        ax.text(lo + 40, y, f"{r['arm']}\n$n_{{\\rm heard}}$ = {r['n_heard']}",
                fontsize=10, va="center", family="monospace")

    ax.set_yticks([])
    ax.set_xlabel("time since task start (s)", labelpad=10)
    ax.set_title(f"Obligation {ex['oid']}  (seed {ex['seed']}, backhaul outage [4h,7h))\n"
                 f"same number of copies, same last opportunity, different first arrival",
                 fontsize=11, loc="left", pad=12)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    fig.text(0.012, 0.015,
             "Both arms have $n_{\\rm heard}=2$ and $B(d)=5400$ s. The only difference is when the first "
             "valid sample reached the gateway, $h^*$:\n"
             "the number of copies does not enter the delivery decision -- the first arrival does.",
             fontsize=9, color="#333333")
    fig.tight_layout(rect=(0, 0.115, 1, 1))
    _os.makedirs(FIGDIR, exist_ok=True)
    for ext in ("png", "svg"):
        pp = _os.path.join(FIGDIR, f"fig_first_heard_counterexample.{ext}")
        fig.savefig(pp, dpi=200)
        print(f"wrote {pp}")


if __name__ == "__main__":
    main()
