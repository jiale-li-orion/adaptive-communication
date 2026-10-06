#!/usr/bin/env python3
"""Generate/check paper-facing Layer-1 benchmark assets from source-of-truth artifacts.

Numeric benchmark statistics are derived from frozen repo artifacts. Related-work
coverage is versioned once in related-benchmark-sources.json and drives both the
README comparison table and landscape figure. Nothing paper-facing is hand-copied
into README.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections import Counter
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

mpl.rcParams["svg.hashsalt"] = "layer1-paper-assets-v1"

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = ROOT / "research" / "benchmark"
ASSETS = BENCHMARK_DIR / "assets"
README = BENCHMARK_DIR / "README.md"
RELATED = BENCHMARK_DIR / "related-benchmark-sources.json"
EXACT_SUMMARY = ROOT / "results/benchmark/layer1-exact-labels-v0.2-retry-legality.json"
V8_SUMMARY = ROOT / "results/benchmark/layer1-v8-all-pass-v0.2-retry-legality.json"
SPLIT = ROOT / "results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json"
PUBLIC_FREEZE = ROOT / "results/benchmark/layer1-public-test-freeze-v0.2-retry-legality.json"

BEGIN = "<!-- BEGIN GENERATED:LAYER1_PAPER_ASSETS -->"
END = "<!-- END GENERATED:LAYER1_PAPER_ASSETS -->"
SECTION_TITLE = "## Paper-facing benchmark landscape and statistics"
NEXT_SECTION = "## Benchmark graduation contract"


def derive_distribution_data() -> dict:
    exact_summary = json.loads(EXACT_SUMMARY.read_text())
    v8_summary = json.loads(V8_SUMMARY.read_text())
    split = json.loads(SPLIT.read_text())
    freeze = json.loads(PUBLIC_FREEZE.read_text())

    exact = exact_summary["projected_recipe_classification"]
    v8 = v8_summary["disposition"]
    hard_rows = [r for r in split["rows"] if r["candidate_role"] == "HARD_PRE_ADMISSION_SURVIVOR"]

    hard_split = {}
    for name in ("train", "dev", "test"):
        rows = [r for r in hard_rows if r["split"] == name]
        hard_split[name] = {
            "signatures": len({r["signature"] for r in rows}),
            "recipes": len(rows),
        }

    # All paper-facing counts must close against independent frozen summaries.
    assert sum(exact.values()) == exact_summary["bundle_count"]
    assert sum(v8.values()) == v8_summary["completed_signature_count"]
    assert len({r["signature"] for r in hard_rows}) == v8_summary["survivor_signature_count"]
    assert len(hard_rows) == v8_summary["projected_survivor_recipe_count"]
    assert sum(x["recipes"] for x in hard_split.values()) == len(hard_rows)
    assert split["by_split"]["test"] == freeze["test_case_count"]

    hard_recovery_coverage = {
        name: split["hard_axis_coverage"][name]["recovery_regime"]["observed"]
        for name in ("train", "dev", "test")
    }
    hard_evidence_regimes = sorted({r["evidence_regime"] for r in hard_rows})
    hard_service_processes = sorted({r["service_process"] for r in hard_rows})

    return {
        "exact_projected_labels": exact,
        "v8_signature_outcomes": v8,
        "hard_split": hard_split,
        "hard_recovery_regime_coverage": hard_recovery_coverage,
        "hard_evidence_regimes": hard_evidence_regimes,
        "hard_service_processes": hard_service_processes,
        "notes": {
            "generator_universe_recipes": exact_summary["bundle_count"],
            "v8_input_signatures": v8_summary["completed_signature_count"],
            "hard_survivor_signatures": v8_summary["survivor_signature_count"],
            "hard_survivor_recipes": v8_summary["projected_survivor_recipe_count"],
            "public_test_cases": freeze["test_case_count"],
            "public_test_sha256": freeze["public_cases_sha256"],
        },
        "lineage": {
            "exact_summary": str(EXACT_SUMMARY.relative_to(ROOT)),
            "v8_summary": str(V8_SUMMARY.relative_to(ROOT)),
            "structure_aware_split": str(SPLIT.relative_to(ROOT)),
            "public_test_freeze": str(PUBLIC_FREEZE.relative_to(ROOT)),
        },
    }

def load_related() -> dict:
    return json.loads(RELATED.read_text())


def render_related_csv(related: dict) -> str:
    buf = io.StringIO()
    dims = [key for key, _ in related["dimensions"]]
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["benchmark", *dims])
    for item in related["benchmarks"]:
        writer.writerow([item["name"], *[item["coverage"][k] for k in dims]])
    return buf.getvalue()


def markdown_link(label: str, target: str | None) -> str:
    return f"[{label}]({target})" if target else "—"


def render_readme_block(data: dict, related: dict) -> str:
    n = data["notes"]
    exact = data["exact_projected_labels"]
    split = data["hard_split"]
    recovery = data["hard_recovery_regime_coverage"]
    hard_pct = 100.0 * n["hard_survivor_signatures"] / n["v8_input_signatures"]
    exact_total = n["generator_universe_recipes"]

    lines = [
        BEGIN,
        "",
        "本节由 `scripts/make_layer1_paper_figures.py` **自动生成**。数值 authority 是 committed `results/benchmark` frozen artifacts；related-work judgment authority 是 `related-benchmark-sources.json`。README、CSV 与图均为这两类 authority 的投影。",
        "",
        "### Related benchmark landscape",
        "",
        "![Related benchmark construct coverage](assets/related-benchmark-landscape.svg)",
        "",
        "图中 `S / P / W / —` 分别表示 Strong / Partial / Weak-adjacent / Not a target。该图负责 related-work construct 定位；质量评估与 leaderboard 由各 benchmark 自身指标承担。",
        "",
        "| Benchmark / system | 核心评测任务 | 与本项目直接相关的已占位置 | Paper / artifact | Repo 内审计入口 |",
        "|---|---|---|---|---|",
    ]
    for item in related["benchmarks"]:
        if item["name"] == "Layer-1 v0.2":
            continue
        links = [markdown_link("paper", item.get("paper"))]
        if item.get("artifact"):
            links.append(markdown_link("artifact", item["artifact"]))
        audit = markdown_link("audit", item.get("audit")) if item.get("audit") else "—"
        lines.append(
            f"| **{item['name']}** | {item['task']} | {item['occupied_position']} | {' · '.join(links)} | {audit} |"
        )

    lines += [
        "",
        "当前抢点保持为组合 construct：",
        "",
        "```text",
        "source-grounded operational obligation",
        "+ continuous / non-anticipative interaction",
        "+ action-relative evidence sufficiency",
        "+ costly heterogeneous evidence acquisition",
        "+ physical communication/resource transition",
        "+ obligation-feasibility transition",
        "+ long intermittent outage / recovery semantics",
        "+ external causal exact oracle",
        "```",
        "",
        "论文中的 **Evidence Sufficiency** 直接绑定 action validity 与 future obligation feasibility；inference quality 属于独立评测层。动作后果由未来义务可满足集合的变化刻画，reward 保留为辅助观测。",
        "",
        "### Current v0.2 distribution",
        "",
        "![Layer-1 v0.2 benchmark distribution](assets/v02-distribution-overview.svg)",
        "",
        "下表全部由 frozen artifacts 重算。recipe、solver signature、hard survivor 与 public-test case 各自拥有独立统计口径：",
        "",
        "| Distribution level | Current v0.2 | Interpretation |",
        "|---|---:|---|",
        f"| Generator universe | **{n['generator_universe_recipes']:,} recipes** | exact recipe-label universe；release case count 由 split/freeze authority 定义 |",
        f"| `NO_PAID_QUERY_REQUIRED` | **{exact['NO_PAID_QUERY_REQUIRED']:,} ({100*exact['NO_PAID_QUERY_REQUIRED']/exact_total:.2f}%)** | exact 投影下无需额外付费 query |",
        f"| `PAID_EVIDENCE_REQUIRED` | **{exact['PAID_EVIDENCE_REQUIRED']:,} ({100*exact['PAID_EVIDENCE_REQUIRED']/exact_total:.2f}%)** | paid acquisition 对可实现策略有正价值 |",
        f"| `INFORMATION_INFEASIBLE` | **{exact['INFORMATION_INFEASIBLE']:,} ({100*exact['INFORMATION_INFEASIBLE']/exact_total:.2f}%)** | 各世界可物理解，但不存在合法 observation-matched common policy |",
        f"| `MIXED_WORLD_SOLVABILITY` | **{exact['MIXED_WORLD_SOLVABILITY']:,} ({100*exact['MIXED_WORLD_SOLVABILITY']/exact_total:.2f}%)** | alias bundle 内物理 solvability 不一致 |",
        f"| V8 input | **{n['v8_input_signatures']:,} solver signatures** | 进入 strong-baseline ladder 的结构单元 |",
        f"| V8 survivors | **{n['hard_survivor_signatures']} signatures / {n['hard_survivor_recipes']} recipes** | **{hard_pct:.2f}%** 的 V8 signatures 留下 hard headroom；该集合拥有 hard-core 语义 |",
        f"| Hard train/dev/test | **{split['train']['signatures']}/{split['dev']['signatures']}/{split['test']['signatures']} signatures; {split['train']['recipes']}/{split['dev']['recipes']}/{split['test']['recipes']} recipes** | structure-aware hard split |",
        f"| Frozen public test | **{n['public_test_cases']:,} cases** | entire public test split；SHA256 `{n['public_test_sha256']}` |",
        "",
        "Hard-survivor recovery coverage：" + "；".join(f"`{split_name}`={values}" for split_name, values in recovery.items()) + "。该项负责验证 train/dev/test 均覆盖声明的 recovery 轴；现场 outage 分布由外部 deployment evidence 单独负责。",
        "",
        "### Construct coverage acceptance",
        "",
        "这张表把最早 `调研cache.md §4.7` 的“强×7”目标映射到当前 v0.2。其 authority 范围是 construct-level research freeze；独立 novelty 由 related-work/claim ledger 管理，正式 `BENCHMARK_ADMIT` 由 quality gate 管理。",
        "",
        "| 原始 construct 维度 | v0.2 验收 | 自动化证据摘要 |",
        "|---|---|---|",
        f"| 连续交互 | **PASS / strong** | hard survivors={n['hard_survivor_signatures']}；blind open-loop audit 由 release gate 单独验证 |",
        f"| 主动补信息 | **PASS / strong** | hard evidence regimes={json.dumps(data['hard_evidence_regimes'], ensure_ascii=False)} |",
        f"| 物理通信资源 | **PASS / declared-model strong** | hard service processes={json.dumps(data['hard_service_processes'], ensure_ascii=False)}；query/send resource transition 由规范与 attribution gate 验证 |",
        "| 动作改变后续状态 | **PASS / strong** | send/wait/query/retry/ACK 进入统一 execution/obligation transition contract |",
        f"| 长期失效 / 恢复 | **PASS / benchmark-semantics strong** | recovery coverage by split={json.dumps(data['hard_recovery_regime_coverage'], ensure_ascii=False)} |",
        "| 外部需求可追溯 | **PASS / research freeze; release audit pending** | source/profile/provenance machine closure 已完成；Q11 human review 仍为 release blocker |",
        "| 可计算最优策略 | **PASS / strong** | hindsight / full-current / observation-matched / no-paid-query exact references |",
        "",
        "### Regeneration discipline",
        "",
        "- 数值与比例：只从 committed `results/benchmark` 的 exact summary、V8 summary、structure-aware split 与 public-test freeze 自动读取。",
        "- related-work 链接与定性覆盖：只维护 `related-benchmark-sources.json` 一个 source ledger；README 表与 landscape 图由脚本生成。",
        "- `python3 scripts/make_layer1_paper_figures.py --check` 用于 CI/提交前漂移检查；任何 README/JSON/CSV/图资产不一致均返回非零。",
        "- SVG 为论文候选资产，PNG 为 README/slide 预览。",
        "- 数值更新路径固定为 frozen results → generator → README/JSON/CSV/SVG/PNG；提交前由 `--check` 验证闭环。",
        "",
        END,
    ]
    return "\n".join(lines) + "\n"


def replace_generated_block(text: str, block: str) -> str:
    if BEGIN in text and END in text:
        start = text.index(BEGIN)
        stop = text.index(END, start) + len(END)
        return text[:start] + block.rstrip("\n") + text[stop:]
    if SECTION_TITLE in text and NEXT_SECTION in text:
        start = text.index(SECTION_TITLE) + len(SECTION_TITLE)
        stop = text.index(NEXT_SECTION, start)
        return text[:start] + "\n\n" + block + "\n" + text[stop:]
    raise RuntimeError("README paper-facing section anchors not found")


def remove_old_construct_matrix(text: str) -> str:
    title = "### Construct coverage acceptance matrix"
    nxt = "### Current v0.2 status against the graduation contract"
    if title in text and nxt in text:
        a = text.index(title)
        b = text.index(nxt, a)
        return text[:a] + text[b:]
    return text



def normalize_svg(path: Path) -> None:
    text = path.read_text()
    path.write_text("\n".join(line.rstrip() for line in text.splitlines()) + "\n")

def render_landscape(related: dict, png: Path, svg: Path) -> None:
    dims = related["dimensions"]
    rows = related["benchmarks"]
    score = {"No": 0, "Weak": 1, "Partial": 2, "Strong": 3}
    data = np.array([[score[r["coverage"][k]] for k, _ in dims] for r in rows], dtype=float)
    fig, ax = plt.subplots(figsize=(12.4, 5.8))
    ax.imshow(data, cmap="Greys", vmin=0, vmax=3, aspect="auto")
    ax.set_xticks(np.arange(len(dims)), [label.replace(" ", "\n", 1) for _, label in dims])
    ax.set_yticks(np.arange(len(rows)), [r["name"] for r in rows])
    for i, r in enumerate(rows):
        for j, (k, _) in enumerate(dims):
            value = r["coverage"][k]
            ax.text(j, i, {"Strong":"S","Partial":"P","Weak":"W","No":"—"}[value],
                    ha="center", va="center", color="white" if score[value] >= 2.5 else "black",
                    fontsize=11, fontweight="bold")
    ax.set_title("Related benchmark construct coverage (qualitative, not a quality score)")
    ax.set_xlabel("S = strong, P = partial, W = weak/adjacent, — = not a target")
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.tight_layout()
    fig.savefig(svg, bbox_inches="tight", metadata={"Date": None})
    normalize_svg(svg)
    fig.savefig(png, dpi=220, bbox_inches="tight")
    plt.close(fig)


def render_distribution(data: dict, png: Path, svg: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15.6, 4.8))
    labels = data["exact_projected_labels"]
    ordered = ["NO_PAID_QUERY_REQUIRED", "PAID_EVIDENCE_REQUIRED", "INFORMATION_INFEASIBLE", "MIXED_WORLD_SOLVABILITY"]
    names = ["No paid query", "Paid evidence", "Info infeasible", "Mixed solvability"]
    vals = [labels[k] for k in ordered]
    axes[0].barh(names, vals)
    axes[0].set_xscale("log")
    axes[0].set_title("A. Exact projected labels")
    axes[0].set_xlabel("Recipes (log scale)")
    for y, v in enumerate(vals):
        axes[0].text(v * 1.04, y, f"{v:,}", va="center", fontsize=9)

    v8 = data["v8_signature_outcomes"]
    keys = ["CHEAP_POLICY_RULE", "FINITE_HORIZON", "DEEP_HORIZON", "SURVIVES_V8_LADDER_V0_1"]
    names2 = ["Cheap rule", "Finite horizon", "Deep horizon", "V8 survivor"]
    vals2 = [v8[k] for k in keys]
    axes[1].barh(names2, vals2)
    axes[1].set_xscale("log")
    axes[1].set_title("B. V8 strong-baseline outcomes")
    axes[1].set_xlabel("Solver signatures (log scale)")
    for y, v in enumerate(vals2):
        axes[1].text(v * 1.04, y, f"{v:,}", va="center", fontsize=9)

    split = data["hard_split"]
    recipes = [split[k]["recipes"] for k in ("train", "dev", "test")]
    sigs = [split[k]["signatures"] for k in ("train", "dev", "test")]
    bars = axes[2].bar(["Train", "Dev", "Test"], recipes)
    axes[2].set_title("C. Frozen hard split")
    axes[2].set_ylabel("Hard recipes")
    axes[2].set_ylim(0, max(recipes) * 1.24)
    for bar, r, s in zip(bars, recipes, sigs):
        axes[2].text(bar.get_x() + bar.get_width()/2, r + 2, f"{r} recipes\n{s} sigs", ha="center", va="bottom", fontsize=9)

    n = data["notes"]
    fig.suptitle("Layer-1 v0.2 benchmark distribution overview")
    fig.text(0.5, 0.01,
             f"{n['generator_universe_recipes']:,} recipes; {n['v8_input_signatures']:,} V8 signatures; "
             f"{n['hard_survivor_signatures']} hard signatures / {n['hard_survivor_recipes']} recipes; "
             f"public test = {n['public_test_cases']:,} cases.", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    fig.savefig(svg, bbox_inches="tight", metadata={"Date": None})
    normalize_svg(svg)
    fig.savefig(png, dpi=220, bbox_inches="tight")
    plt.close(fig)


def write_temp_assets(data: dict, related: dict, base: Path) -> dict[str, bytes]:
    base.mkdir(parents=True, exist_ok=True)
    json_path = base / "v02-paper-figure-data.json"
    csv_path = base / "benchmark-landscape.csv"
    rel_png = base / "related-benchmark-landscape.png"
    rel_svg = base / "related-benchmark-landscape.svg"
    dist_png = base / "v02-distribution-overview.png"
    dist_svg = base / "v02-distribution-overview.svg"
    json_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    csv_path.write_text(render_related_csv(related))
    render_landscape(related, rel_png, rel_svg)
    render_distribution(data, dist_png, dist_svg)
    return {p.name: p.read_bytes() for p in (json_path, csv_path, rel_png, rel_svg, dist_png, dist_svg)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated assets/README are stale")
    args = parser.parse_args()

    data = derive_distribution_data()
    related = load_related()
    block = render_readme_block(data, related)
    readme_text = remove_old_construct_matrix(README.read_text())
    expected_readme = replace_generated_block(readme_text, block)

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        generated = write_temp_assets(data, related, Path(td))
        stale = []
        for name, content in generated.items():
            target = ASSETS / name
            if not target.exists() or target.read_bytes() != content:
                stale.append(str(target.relative_to(ROOT)))
        if README.read_text() != expected_readme:
            stale.append(str(README.relative_to(ROOT)))

        if args.check:
            if stale:
                print("stale Layer-1 paper assets:")
                for item in stale:
                    print(" -", item)
                return 1
            print("Layer-1 paper assets are current")
            return 0

        ASSETS.mkdir(parents=True, exist_ok=True)
        for name, content in generated.items():
            (ASSETS / name).write_bytes(content)
        README.write_text(expected_readme)
        print("updated Layer-1 paper assets from source-of-truth artifacts")
        for item in stale:
            print(" -", item)
    return 0


if __name__ == "__main__":
    sys.exit(main())
