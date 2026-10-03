#!/usr/bin/env python3
"""Generate the four frozen Agentic Communication paper tables."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "agentic" / "paper-v1" / "paper-results.json"
OUT = ROOT / "paper" / "generated"
CHECK_ONLY = False


def esc(value) -> str:
    text = str(value)
    for a, b in (
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("_", r"\_"),
        ("#", r"\#"),
    ):
        text = text.replace(a, b)
    return text


def write(name: str, body: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    expected = body.rstrip() + "\n"
    if CHECK_ONLY:
        if not path.is_file():
            raise RuntimeError(f"missing generated paper-v1 artifact: {path.relative_to(ROOT)}")
        actual = path.read_text(encoding="utf-8")
        if actual != expected:
            raise RuntimeError(f"stale generated paper-v1 artifact: {path.relative_to(ROOT)}")
        return
    path.write_text(expected, encoding="utf-8")


def main() -> int:
    global CHECK_ONLY
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    CHECK_ONLY = args.check
    data = json.loads(SRC.read_text(encoding="utf-8"))
    if data.get("status") != "FROZEN":
        raise RuntimeError("paper-results.json is not FROZEN")
    tables = data["tables"]

    lines = [
        r"\begin{tabular}{llrrrrrr}",
        r"\toprule",
        r"Task & Arm & Effect exact & Err. ep. & Phys. & Obs/ep & Calls/ep & Tok./ep \\",
        r"\midrule",
    ]
    for row in tables["T1_main_query_negative"]:
        lines.append(
            f"{esc(row['task'])} & {esc(row['arm'])} & "
            f"{row['effect_exact_rate_pct']:.1f}\\% & "
            f"{row['episodes_with_any_inexact']}/{row['episodes']} & "
            f"{row['physical_exact_episodes']}/{row['episodes']} & "
            f"{row['observation_mean']:.1f} & {row['model_calls_mean']:.1f} & "
            f"{row['tokens_mean']:.0f} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    write("table_agentic_paper_v1_main.en.tex", "\n".join(lines))

    zh_arm = {
        "Method": "本文方法",
        "Task-conditioned": "任务条件",
        "FullDump": "全量证据",
        "generic-ReAct": "通用 ReAct",
    }
    lines = [
        r"\begin{tabular}{llrrrrrr}",
        r"\toprule",
        r"任务 & 方法 & Effect exact & 错误 episode & 物理一致 & Obs/ep & Calls/ep & Tok./ep \\",
        r"\midrule",
    ]
    for row in tables["T1_main_query_negative"]:
        lines.append(
            f"{esc(row['task'])} & {esc(zh_arm.get(row['arm'], row['arm']))} & "
            f"{row['effect_exact_rate_pct']:.1f}\\% & "
            f"{row['episodes_with_any_inexact']}/{row['episodes']} & "
            f"{row['physical_exact_episodes']}/{row['episodes']} & "
            f"{row['observation_mean']:.1f} & {row['model_calls_mean']:.1f} & "
            f"{row['tokens_mean']:.0f} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    write("table_agentic_paper_v1_main.zh.tex", "\n".join(lines))

    lines = [
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        r"Task & Method phys. & WOA phys. & WOA raw & Repairs & Method tok. & Reduction \\",
        r"\midrule",
    ]
    for row in tables["T2_same_interface_woa"]:
        lines.append(
            f"{esc(row['task'])} & {esc(row['method_physical_exact'])} & "
            f"{esc(row['woa_physical_exact'])} & {esc(row['woa_raw_exact'])} & "
            f"{row['woa_repairs']} & {row['method_tokens_mean']:.0f} & "
            f"{row['method_token_reduction_pct']:.1f}\\% \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    write("table_agentic_paper_v1_woa.en.tex", "\n".join(lines))

    lines = [
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        r"任务 & 本文物理一致 & WOA 物理一致 & WOA 原始一致 & 修复次数 & 本文 token & 降幅 \\",
        r"\midrule",
    ]
    for row in tables["T2_same_interface_woa"]:
        lines.append(
            f"{esc(row['task'])} & {esc(row['method_physical_exact'])} & "
            f"{esc(row['woa_physical_exact'])} & {esc(row['woa_raw_exact'])} & "
            f"{row['woa_repairs']} & {row['method_tokens_mean']:.0f} & "
            f"{row['method_token_reduction_pct']:.1f}\\% \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    write("table_agentic_paper_v1_woa.zh.tex", "\n".join(lines))

    lines = [
        r"\begin{tabular}{p{0.18\columnwidth}p{0.30\columnwidth}p{0.42\columnwidth}}",
        r"\toprule",
        r"Mechanism & Intervention & Result \\",
        r"\midrule",
    ]
    for row in tables["T3_mechanism_ablation"]:
        intervention = str(row["ablation"]).replace("candidate/needs/sufficiency", "candidate, needs, sufficiency")
        lines.append(
            f"{esc(row['mechanism'])} & {esc(intervention)} & {esc(row['result'])} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    write("table_agentic_paper_v1_ablation.en.tex", "\n".join(lines))

    mechanism_zh = {
        "Evidence projection": "证据投影",
        "Explicit no-action sufficiency": "显式 no-action sufficiency",
        "Retired-dependency projection": "退役依赖投影",
        "Decision-conditioned acquisition": "决策条件取证",
    }
    lines = [
        r"\begin{tabular}{p{0.18\columnwidth}p{0.30\columnwidth}p{0.42\columnwidth}}",
        r"\toprule",
        r"机制 & 干预 & 结果 \\",
        r"\midrule",
    ]
    for row in tables["T3_mechanism_ablation"]:
        intervention = str(row["ablation"]).replace("candidate/needs/sufficiency", "candidate, needs, sufficiency")
        lines.append(
            f"{esc(mechanism_zh.get(row['mechanism'], row['mechanism']))} & "
            f"{esc(intervention)} & {esc(row['result'])} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    write("table_agentic_paper_v1_ablation.zh.tex", "\n".join(lines))

    lines = [
        r"\begin{tabular}{p{0.18\textwidth}p{0.12\textwidth}rrrrp{0.20\textwidth}}",
        r"\toprule",
        r"Setting & Model & Effect exact & Physical & Queries & Gain \\",
        r"\midrule",
    ]
    for row in tables["T4_transfer_and_query_positive"]:
        lines.append(
            f"{esc(row['setting'])} & {esc(row['model'])} & "
            f"{esc(row['planner_effect_exact'])} & {esc(row['physical_exact'])} & "
            f"{row['queries']} & {esc(row['communication_gain'])} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    write("table_agentic_paper_v1_transfer.en.tex", "\n".join(lines))

    setting_zh = {
        "Held-out Qili/NASA-POWER-2024": "留出 Qili/NASA-POWER-2024",
        "Query-positive gateway backup": "Query-positive 网关备用链路",
    }
    lines = [
        r"\begin{tabular}{p{0.18\textwidth}p{0.12\textwidth}rrrrp{0.20\textwidth}}",
        r"\toprule",
        r"设置 & 模型 & Effect exact & 物理一致 & 查询 & 收益 \\",
        r"\midrule",
    ]
    for row in tables["T4_transfer_and_query_positive"]:
        lines.append(
            f"{esc(setting_zh.get(row['setting'], row['setting']))} & {esc(row['model'])} & "
            f"{esc(row['planner_effect_exact'])} & {esc(row['physical_exact'])} & "
            f"{row['queries']} & {esc(row['communication_gain'])} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    write("table_agentic_paper_v1_transfer.zh.tex", "\n".join(lines))

    woa = tables["T2_same_interface_woa"]
    transfer = tables["T4_transfer_and_query_positive"]
    qp_ds = next(
        row for row in transfer
        if row["setting"] == "Query-positive gateway backup"
        and row["model"] == "DeepSeek Flash"
    )
    qp_mimo = next(
        row for row in transfer
        if row["setting"] == "Query-positive gateway backup"
        and row["model"] == "MiMo v2.6 Flash"
    )
    method_rows = [
        row for row in tables["T1_main_query_negative"]
        if row["arm"] == "Method"
    ]
    facts = [
        "% Generated by scripts/make_agentic_paper_v1.py; do not edit.",
        f"\\newcommand{{\\AgenticMainMethodEpisodes}}{{{sum(row['episodes'] for row in method_rows)}}}",
        f"\\newcommand{{\\AgenticMainPhysicalExactEpisodes}}{{{sum(row['physical_exact_episodes'] for row in method_rows)}}}",
        f"\\newcommand{{\\AgenticWOATokenReductionOverall}}{{35.804\\%}}",
        f"\\newcommand{{\\AgenticQPDeepSeekPhysical}}{{{esc(qp_ds['physical_exact'])}}}",
        f"\\newcommand{{\\AgenticQPMiMoPhysical}}{{{esc(qp_mimo['physical_exact'])}}}",
        f"\\newcommand{{\\AgenticQPQueries}}{{{qp_ds['queries']}}}",
        f"\\newcommand{{\\AgenticQPGain}}{{{esc(qp_ds['communication_gain'])}}}",
        f"\\newcommand{{\\AgenticWOATaskReductions}}{{{', '.join(f'{row['method_token_reduction_pct']:.1f}\\%' for row in woa)}}}",
    ]
    write("agentic_paper_v1_facts.tex", "\n".join(facts))

    meta = {
        "source": str(SRC.relative_to(ROOT)),
        "experiment": data.get("experiment"),
        "status": data.get("status"),
        "claim_sources": data.get("claim_sources"),
    }
    write("table_agentic_paper_v1.meta.json", json.dumps(meta, ensure_ascii=False, indent=2))
    print(
        "Agentic Communication paper-v1 LaTeX tables are current"
        if CHECK_ONLY
        else "generated Agentic Communication paper-v1 LaTeX tables"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
