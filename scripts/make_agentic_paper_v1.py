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

    task_rows = [
        ("O1", "Monitoring continuity", "maintain the authorised profile under ordinary intermittent delivery", "TDR, latency, AoI, resource use"),
        ("O2", "Risk escalation", "install denser externally authorised sampling/reporting, globally or on a target subset", "effect scope, install correctness, physical reference"),
        ("O3", "Backhaul-outage sustainment", "sustain service when the primary return path degrades and fallback may become useful", "gateway evidence, backup decision, historical delivery"),
        ("O4", "Energy-constrained monitoring", "execute the same monitoring task under NASA POWER-derived or declared low harvest", "task completion, survival, residual energy, gaps"),
        ("O5", "Recovery and reconciliation", "reconcile configuration/history as disconnected paths recover", "requested/applied/confirmed state, stale or duplicate effects, recovery"),
        ("O6", "Compound long horizon", "combine task revision, access/backhaul interruption, energy pressure, and recovery", "Context evolution, stopping, execution fidelity"),
    ]
    lines = [
        r"\begin{tabular}{p{0.07\textwidth}p{0.20\textwidth}p{0.37\textwidth}p{0.27\textwidth}}",
        r"\toprule",
        r"Task & Operational change & Decision surface & Primary diagnostic / outcome \\",
        r"\midrule",
    ]
    for task, change, surface, outcome in task_rows:
        lines.append(f"{esc(task)} & {esc(change)} & {esc(surface)} & {esc(outcome)} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    write("table_agentic_tasks.en.tex", "\n".join(lines))

    task_rows_zh = [
        ("O1", "监测连续性", "普通间歇交付下维持既定授权监测 profile", "TDR、时延、AoI、资源使用"),
        ("O2", "风险升级", "全局或局部目标上安装外部授权的更密采样/上报配置", "effect scope、安装正确性、物理参照"),
        ("O3", "回传中断维持", "主回传退化时维持服务并判断是否启用 fallback", "网关证据、backup 决策、历史交付"),
        ("O4", "能量受限监测", "NASA POWER 派生或声明低采能条件下执行同一监测任务", "任务完成、存活、剩余能量、监测缺口"),
        ("O5", "恢复与调和", "断连路径恢复后调和配置与历史数据", "requested/applied/confirmed、陈旧/重复 effect、恢复"),
        ("O6", "复合长时运行", "任务修订、接入/回传中断、能量压力与恢复共同发生", "Context 演化、停止、执行一致性"),
    ]
    lines = [
        r"\begin{tabular}{p{0.07\textwidth}p{0.20\textwidth}p{0.37\textwidth}p{0.27\textwidth}}",
        r"\toprule",
        r"任务 & 业务变化 & 决策面 & 主要诊断 / 结果 \\",
        r"\midrule",
    ]
    for task, change, surface, outcome in task_rows_zh:
        lines.append(f"{esc(task)} & {esc(change)} & {esc(surface)} & {esc(outcome)} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    write("table_agentic_tasks.zh.tex", "\n".join(lines))

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
