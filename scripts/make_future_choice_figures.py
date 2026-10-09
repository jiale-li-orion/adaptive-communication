#!/usr/bin/env python3
"""Generate publication-quality Future-Choice paper figures from tracked data.

Design goals follow networking/systems paper conventions: each figure answers a
single reviewer question, remains legible in two-column layouts and in grayscale,
and never duplicates a table merely for decoration.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import tempfile

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "paper/generated"

FAILURES = ROOT / "results/benchmark/layer1-paper-deterministic-test/failure-case-studies.json"
B_COMPONENT = ROOT / "results/transfer/asc-pull-query-component-strong-baselines.json"
C_SCALE = ROOT / "results/transfer/uav-attention-n10-scale-statistics.json"
C_SET = ROOT / "results/transfer/uav-attention-set-mst-attribution.json"


mpl.rcParams.update(
    {
        "font.size": 8.0,
        "axes.labelsize": 8.0,
        "axes.titlesize": 8.5,
        "xtick.labelsize": 7.4,
        "ytick.labelsize": 7.4,
        "legend.fontsize": 7.2,
        "axes.linewidth": 0.7,
        "lines.linewidth": 1.2,
        "lines.markersize": 5.2,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.hashsalt": "future-choice-paper-figures-v1",
    }
)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def clean_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", color="0.90", linewidth=0.6, zorder=0)


def normalize_svg(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    path.write_text("\n".join(line.rstrip() for line in text.splitlines()) + "\n", encoding="utf-8")


def save(fig, stem: Path) -> None:
    fig.savefig(
        stem.with_suffix(".pdf"),
        bbox_inches="tight",
        metadata={"CreationDate": None, "ModDate": None},
    )
    svg = stem.with_suffix(".svg")
    fig.savefig(svg, bbox_inches="tight", metadata={"Date": None})
    normalize_svg(svg)
    plt.close(fig)


def render_failure_lifecycles(stem: Path) -> None:
    d = load(FAILURES)["cases"]
    fig, ax = plt.subplots(figsize=(7.05, 2.65), layout="constrained")
    ys = {"delivery": 2.0, "energy": 1.0, "revision": 0.0}

    # Shared 0--13h execution horizon; timeline semantics matter more than
    # decorative color.  Different marker shapes remain distinct in grayscale.
    ax.hlines(list(ys.values()), 0, 13, color="0.72", linewidth=0.8, zorder=0)

    # Delivery-only case.
    x_rel = d["delivery_only"]["first_failed_obligation"]["release_at"] / 3600
    x_dead = d["delivery_only"]["first_failed_obligation"]["deadline"] / 3600
    x_heard = d["delivery_only"]["first_failed_obligation"]["first_heard_at"] / 3600
    y = ys["delivery"]
    ax.plot(x_rel, y, marker="o", mfc="white", mec="black", linestyle="none")
    ax.plot(x_dead, y, marker="|", color="black", ms=10, mew=1.5, linestyle="none")
    ax.plot(x_heard, y, marker="x", color="black", ms=6, mew=1.4, linestyle="none")
    ax.annotate("release", (x_rel, y), xytext=(0, 8), textcoords="offset points", ha="center")
    ax.annotate("deadline", (x_dead, y), xytext=(0, 8), textcoords="offset points", ha="center")
    ax.annotate("first gateway\nheard (late)", (x_heard, y), xytext=(0, -23), textcoords="offset points", ha="center")
    ax.text(10.15, y + 0.03, "3 never heard + 3 late", va="center", fontsize=7.3)

    # Energy / collection case.
    e = d["energy_collection"]["dead_node_lifecycle"]["n13"]
    x_last = e["last_sample_taken_at_s"] / 3600
    x_deadnode = e["first_alive_false_s"] / 3600
    x_next = e["first_missing_obligation"]["release_at"] / 3600
    y = ys["energy"]
    ax.plot(x_last, y, marker="o", mfc="white", mec="black", linestyle="none")
    ax.plot(x_deadnode, y, marker="X", color="black", linestyle="none")
    ax.plot(x_next, y, marker="v", mfc="0.75", mec="black", linestyle="none")
    ax.annotate("last sample", (x_last, y), xytext=(-2, 8), textcoords="offset points", ha="right")
    ax.annotate("node dead", (x_deadnode, y), xytext=(2, -17), textcoords="offset points", ha="left")
    ax.annotate("next obligation:\nno sample", (x_next, y), xytext=(4, 7), textcoords="offset points", ha="left")

    # Task revision case: outage is a real execution constraint, not decoration.
    t = d["task_revision"]
    out0 = t["template_outage"]["outage_start_s"] / 3600
    out1 = t["template_outage"]["outage_end_s"] / 3600
    req = t["revision_required_at_s"] / 3600
    plan = t["first_revision_event_s"]["plan"] / 3600
    sent = t["first_revision_event_s"]["sent"] / 3600
    applied = t["first_revision_event_s"]["applied"] / 3600
    y = ys["revision"]
    ax.fill_betweenx([y - 0.19, y + 0.19], out0, out1, color="0.88", zorder=0)
    ax.text((out0 + out1) / 2, y - 0.23, "backhaul outage", ha="center", va="top", fontsize=7.0)
    ax.plot(req, y, marker="|", color="black", ms=10, mew=1.5, linestyle="none")
    ax.plot(plan, y, marker="o", mfc="white", mec="black", linestyle="none")
    ax.plot(sent, y, marker=">", color="black", linestyle="none")
    ax.plot(applied, y, marker="s", mfc="0.72", mec="black", linestyle="none")
    ax.annotate("300 s task\nrequired / planned", (req, y), xytext=(0, 8), textcoords="offset points", ha="center")
    ax.annotate("first sent/applied", (sent, y), xytext=(0, -18), textcoords="offset points", ha="center")
    ax.text(10.35, y + 0.03, "6/14 nodes fully revised", va="center", fontsize=7.3)

    ax.set_xlim(0, 13)
    ax.set_ylim(-0.55, 2.55)
    ax.set_yticks([2, 1, 0], ["Delivery-only", "Energy / collection", "Task revision"])
    ax.set_xlabel("Simulation time (hours)")
    ax.set_title("Three operational failure layers that aggregate TDR conflates", loc="left", pad=5)
    clean_axes(ax)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    save(fig, stem)


def render_dependency_invalidation(stem: Path) -> None:
    d = load(B_COMPONENT)
    cell = next(c for c in d["cells"] if int(c["components"]) == 16)
    events = cell["events"]
    labels = [
        "Initial build",
        "Send → pending",
        "Gateway receipt",
        "Final ACK",
        "Local time boundary",
        "Global backup budget",
    ]
    recompute = np.array([e["incremental_conflict"]["recomputed_components"] for e in events], dtype=float)
    reuse = np.array([e["incremental_conflict"]["reused_components"] for e in events], dtype=float)
    total = recompute + reuse
    frac_r = recompute / total
    frac_u = reuse / total

    fig, ax = plt.subplots(figsize=(6.95, 2.65), layout="constrained")
    y = np.arange(len(events))[::-1]
    ax.barh(y, frac_u, height=0.58, facecolor="white", edgecolor="black", hatch="///", linewidth=0.8, label="reused")
    ax.barh(y, frac_r, left=frac_u, height=0.58, color="0.25", edgecolor="black", linewidth=0.8, label="recomputed")
    for yi, r, u, t in zip(y, recompute, reuse, total):
        ax.text(1.012, yi, f"{int(r)}/{int(t)} rebuilt", va="center", fontsize=7.2)
    ax.set_yticks(y, labels)
    ax.set_xlim(0, 1.18)
    ax.set_xticks([0, .25, .5, .75, 1.0], ["0", "25", "50", "75", "100"])
    ax.set_xlabel("Conflict components retained / rebuilt (%)")
    ax.set_title("New history does not imply new future-feasibility structure", loc="left", pad=5)
    ax.legend(
        frameon=False,
        ncol=2,
        loc="upper center",
        bbox_to_anchor=(0.52, -0.20),
        borderaxespad=0,
    )
    clean_axes(ax)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    save(fig, stem)


def render_paired_gain(stem: Path) -> None:
    d = load(C_SCALE)["constructive100"]
    order = ["nearest_neighbour", "battery_aware_nn", "greedy_deadline_battery", "nearest_deadline"]
    labels = ["Nearest neighbour", "Battery-aware NN", "Greedy deadline-battery", "Nearest deadline"]
    means, los, his, discord = [], [], [], []
    for policy in order:
        x = d[policy]["future_vs_depth4"]
        ci = x["zero_tardiness_rate_diff"]
        means.append(100 * ci["mean"])
        los.append(100 * ci["lo"])
        his.append(100 * ci["hi"])
        m = x["zero_tardiness_mcnemar"]
        discord.append((m["future_better"], m["future_worse"], m["p_two_sided"]))

    y = np.arange(len(order))[::-1]
    fig, ax = plt.subplots(figsize=(6.95, 2.55), layout="constrained")
    xerr = np.array([np.array(means) - np.array(los), np.array(his) - np.array(means)])
    ax.errorbar(means, y, xerr=xerr, fmt="o", color="black", ecolor="0.25", capsize=3, lw=1.2, zorder=3)
    ax.axvline(0, color="0.45", linewidth=0.8, linestyle="--")
    for xi, yi, (better, worse, p) in zip(means, y, discord):
        ptxt = "<1e-15" if p < 1e-15 else f"={p:.1g}"
        ax.text(his[list(y).index(yi)] + 2.1, yi, f"{better}/{worse} better/worse, p{ptxt}", va="center", fontsize=7.0)
    ax.set_yticks(y, labels)
    ax.set_xlim(-2, 78)
    ax.set_xlabel("FutureChoice − depth-4 zero-tardiness rate (percentage points)\nbootstrap 95% CI; n=100 paired hard-feasible layouts")
    ax.set_title("FutureChoice removes residual depth-4 failures without reverse zero-tardiness harm", loc="left", pad=5)
    clean_axes(ax)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    save(fig, stem)


def render_setmst_ablation(stem: Path) -> None:
    d = load(C_SET)["n10"]["rows"]
    order = ["nearest_neighbour", "battery_aware_nn", "greedy_deadline_battery", "nearest_deadline"]
    labels = ["NN", "Battery-aware", "Greedy", "Nearest deadline"]
    fig, axes = plt.subplots(1, 2, figsize=(7.05, 2.45), layout="constrained", sharey=True)
    y = np.arange(len(order))[::-1]
    specs = [
        ("basic_fallback_ratio_over_exact", "set_mst_fallback_ratio_over_exact", "Exact fallback / pure exact (%)"),
        ("basic_total_ratio_over_exact", "set_mst_total_ratio_over_exact", "Total search proxy / pure exact (%)"),
    ]
    for ax, (bk, sk, title) in zip(axes, specs):
        basic = [100 * d[p]["n10_compute"][bk] for p in order]
        setm = [100 * d[p]["n10_compute"][sk] for p in order]
        for yi, b, s in zip(y, basic, setm):
            ax.plot([s, b], [yi, yi], color="0.55", linewidth=1.0, zorder=1)
        ax.scatter(basic, y, marker="o", facecolors="white", edgecolors="black", label="basic U", zorder=3)
        ax.scatter(setm, y, marker="s", color="black", label="set-MST U", zorder=3)
        for yi, b, s in zip(y, basic, setm):
            ax.text(min(b, s) - 2.3, yi, f"−{100*(1-s/b):.0f}%", ha="right", va="center", fontsize=6.9)
        ax.set_title(title, loc="left", pad=4)
        ax.set_xlim(0, 90)
        clean_axes(ax)
    axes[0].set_yticks(y, labels)
    axes[1].legend(frameon=False, loc="lower right")
    fig.suptitle("Set-level deadline conflict tightens the sound U bound at unchanged task quality", x=0.02, ha="left", fontsize=8.5)
    save(fig, stem)


def render_mechanism_tex() -> str:
    return r"""% Generated by scripts/make_future_choice_figures.py; do not edit.
\begin{tikzpicture}[
  >=Latex,
  node distance=5mm and 7mm,
  box/.style={draw, rounded corners=2pt, align=center, inner sep=3.5pt, font=\scriptsize, minimum height=7mm},
  branch/.style={draw, rounded corners=2pt, align=center, inner sep=3pt, font=\scriptsize},
  note/.style={font=\scriptsize, align=center},
  flow/.style={->, line width=.8pt},
  reject/.style={draw, dashed, rounded corners=2pt, align=center, inner sep=3pt, font=\scriptsize},
]
\node[note, font=\footnotesize\bfseries] (ta) {(a) Static worst-case reserve};
\node[box, below=2mm of ta] (h1) {same current history $h_t$\\hidden $H\in\{0,1\}$};
\node[branch, below left=5mm and 4mm of h1] (b) {$H=0$\\future obligation $B$};
\node[branch, below right=5mm and 4mm of h1] (c) {$H=1$\\future obligation $C$};
\draw[flow] (h1) -- (b); \draw[flow] (h1) -- (c);
\node[reject, below=7mm of h1] (union) {static union reserves $\{B,C\}$\\remaining budget $1<2$\\\textbf{reject QUERY\_H}};
\draw[flow, dashed] (b) -- (union); \draw[flow, dashed] (c) -- (union);

\node[note, font=\footnotesize\bfseries, right=23mm of ta] (tb) {(b) Observation-conditioned future choices};
\node[box, below=2mm of tb] (qh) {QUERY\_H\\cost $1$};
\node[branch, below left=6mm and 4mm of qh] (hb) {$H=0$ observed\\QUERY\_B};
\node[branch, below right=6mm and 4mm of qh] (hc) {$H=1$ observed\\QUERY\_C};
\draw[flow] (qh) -- node[note, left] {$z=0$} (hb);
\draw[flow] (qh) -- node[note, right] {$z=1$} (hc);
\node[box, below=5mm of qh] (cert) {$L(h_t,\mathrm{QUERY\_H})=1$\\one replayable causal policy\\budget $1$ on each realized branch};
\draw[flow] (hb) -- (cert); \draw[flow] (hc) -- (cert);

\node[note, font=\footnotesize\bfseries, right=24mm of tb] (tc) {(c) Exact-correct runtime};
\node[box, below=2mm of tc] (a) {candidate action $a$};
\node[box, below=of a] (carry) {carried certificate valid?};
\node[box, below=of carry] (u) {sound optimistic $U(a)=0$?};
\node[box, below=of u] (l) {constructive $L(a)=1$?};
\node[box, below=of l] (ex) {exact fallback};
\draw[flow] (a) -- (carry); \draw[flow] (carry) -- (u); \draw[flow] (u) -- (l); \draw[flow] (l) -- (ex);
\node[note, right=2mm of carry] {reuse};
\node[note, right=2mm of u] {prune impossible};
\node[note, right=2mm of l] {certify feasible};
\node[note, right=2mm of ex] {resolve remainder};
\end{tikzpicture}
"""


def expected_outputs(base: Path) -> dict[Path, bytes]:
    render_failure_lifecycles(base / "fig_layer1_failure_lifecycles")
    render_dependency_invalidation(base / "fig_dependency_local_invalidation")
    render_paired_gain(base / "fig_uav_paired_gain")
    render_setmst_ablation(base / "fig_setmst_ablation")
    (base / "fig_future_choice_mechanism.tex").write_text(render_mechanism_tex(), encoding="utf-8")
    manifest = {
        "stage": "FUTURE_CHOICE_PAPER_FIGURES",
        "inputs": {
            str(p.relative_to(ROOT)): sha(p)
            for p in (FAILURES, B_COMPONENT, C_SCALE, C_SET)
        },
        "figures": [
            "fig_future_choice_mechanism.tex",
            "fig_layer1_failure_lifecycles.pdf/svg",
            "fig_dependency_local_invalidation.pdf/svg",
            "fig_uav_paired_gain.pdf/svg",
            "fig_setmst_ablation.pdf/svg",
        ],
        "design": "vector-first; grayscale-safe markers/hatches; no decorative radar/pie charts",
    }
    (base / "future_choice_figures.meta.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return {p.relative_to(base): p.read_bytes() for p in base.iterdir()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    GEN.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        expected = expected_outputs(base)
        stale = []
        for rel, content in expected.items():
            target = GEN / rel
            if not target.exists() or target.read_bytes() != content:
                stale.append(str(target.relative_to(ROOT)))
        if args.check:
            if stale:
                raise SystemExit("Future-Choice figure drift: " + ", ".join(stale))
            print("Future-Choice paper figures are current")
            return 0
        for rel, content in expected.items():
            (GEN / rel).write_bytes(content)
        print("Generated Future-Choice paper figures")
        for item in stale:
            print(" -", item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
