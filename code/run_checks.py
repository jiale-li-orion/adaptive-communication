#!/usr/bin/env python3
"""
run_checks.py — one entry point for every check in the repository.

The repository has no CI pipeline, so this is what a pipeline would call. Running it is also how a
human answers "is the tree healthy" without remembering eleven file names and their order.

Each check is a standalone script that prints PASS/FAIL lines and exits non-zero on failure. This
runner does not parse their output; it reports exit codes, because a check that fails silently
while printing confident lines is exactly the failure mode these files exist to prevent.

Three groups, because they answer different questions:

  mechanism   the execution-semantics layer and the frozen mechanism-isolation experiment.
  monitoring  the business-loop simulator built for the paper contract.
  claims      the claim table: every claim must name an existing script and an existing reference
              result, with one status drawn from a fixed set. This is what keeps a claim and the
              evidence for it from drifting apart across revisions.
  paper       the manuscripts' tables must be generated from the result files rather than typed
              into the text, so a re-run cannot leave a stale number in the paper.
  seqref      the pre-registered non-prescient sequence reference: declared constants have one
              source, the hand-checkable core matches exhaustive enumeration and still resolves a
              real gap, and the tested cells' three-row table and identity hold.
  agentic     the self-contained OperationalTask/EvidenceWorld/Context/Capability runtime preserves
              existing physical behavior while emitting a typed auditable trace.

Run: python3 code/run_checks.py [--group mechanism|monitoring|claims|paper|seqref|all] [--quiet]
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

CHECKS = {
    "mechanism": [
        ("runtime/operations.py", "执行语义自检：三维正交、五条不变量、三条性质"),
        ("experiments/test_failure_model.py", "11 类故障可复现"),
        ("experiments/test_vendored_deps.py", "vendored itmlogic 在无 PYTHONPATH 的干净 shell 可解析"),
        ("experiments/test_repair_runtime.py", "repair runtime：同信息 ordinary baselines 与预算语义"),
        ("experiments/test_draw_keys.py", "报文级随机契约"),
        ("experiments/test_journal_schema.py", "持久日志 schema 与字段集校验"),
        ("experiments/audit_consistency.py", "一致性审计：README 与结果文件逐行对齐"),
    ],
    "monitoring": [
        ("experiments/test_energy_model.py", "能量模型手工核算"),
        ("experiments/test_opportunity.py", "控制面机会模型与机会上界"),
        ("experiments/test_node_model.py", "采样/缓存/上传链逐事件对齐"),
        ("experiments/test_task_generator.py", "外生需求生成器"),
        ("experiments/test_scorer.py", "评分器与真值边界"),
        ("experiments/test_interfaces.py", "四接口与可审计证据"),
        ("experiments/test_llm_planner.py", "LLM 规划器、决策校验与调用账目"),
        ("experiments/test_supply.py", "供电模型与可达性耦合"),
        ("experiments/test_faults.py", "六类诊断故障注入"),
        ("experiments/test_policies.py", "强基线：版本化配置与 VTC 风格恢复"),
        ("experiments/test_recovery.py", "恢复归因：从日志重建 runtime 的两个标量"),
        ("experiments/test_instance.py", "实例层验收：Task v1.1 最小闭环的手工可核算性质"),
        ("experiments/audit_fairness.py", "业务层公平性审计"),
    ],
    "claims": [
        ("experiments/audit_claims.py", "主张表：脚本与参考结果存在、状态取自固定集合"),
    ],
    "paper": [
        ("experiments/audit_tables.py", "论文表格由结果文件生成，稿件不手写表体"),
    ],
    "seqref": [
        ("experiments/audit_seqref.py", "非预知序列参照：常数同源、台账校准、核例穷举、三方表与恒等式"),
    ],
    "agentic": [
        ("experiments/agentic/test_runtime_harness.py",
         "Agentic Communication runtime：自包含 contract、typed trace、与现有 comply 物理等价"),
        ("experiments/agentic/test_replay.py",
         "Agentic Communication replay：R0 protocol、R1 frozen input、R2 exact context materialization"),
        ("experiments/agentic/test_task_catalog_and_trajectory.py",
         "Agentic Communication benchmark：O1-O6 catalog、trajectory metrics、gold replacement schema"),
        ("experiments/agentic/test_planner_ledger.py",
         "Agentic Communication model boundary：R1 ModelRequest/Attempt/Usage/PlannerDecision ledger"),
        ("experiments/agentic/test_owner_scoped_evidence.py",
         "Agentic Communication evidence ownership：gateway owner read 可达/不可达语义且不改变物理行为"),
        ("experiments/agentic/test_evidence_owner_persistence.py",
         "Agentic Communication Evidence World：跨 owner evidence 持久化并按 freshness 边界刷新"),
        ("experiments/agentic/test_live_planner_consumer.py",
         "Agentic Communication live planner：typed model ledger、structured decision、R3 物理等价"),
        ("experiments/agentic/test_baseline_registry.py",
         "Agentic Communication baseline registry：复用既有强 baseline，online/oracle 信息边界分离"),
        ("experiments/agentic/test_gold_replacement.py",
         "Agentic Communication gold replacement：tool selection/order/arguments 分层归因且不偷渡参数"),
        ("experiments/agentic/test_gateway_backup_device_tool.py",
         "Agentic Communication device tool：typed gateway-backup invocation 真实作用于 JointControlPlane"),
        ("experiments/agentic/test_multiround_evidence_tool.py",
         "Agentic Communication multi-round：Context→evidence tool→world revision→Context→device policy"),
        ("experiments/agentic/test_live_gold_replacement.py",
         "Agentic Communication R3 attribution：错误 planner 经累计 gold layers 恢复 reference physical outcome"),
        ("experiments/agentic/test_benchmark_split.py",
         "Agentic Communication split：2022/2023/2024 source period 先于 seed，O1-O6 坐标可重放"),
        ("experiments/agentic/test_r1_evaluation.py",
         "Agentic Communication R1 metrics：同一 PromptAssembly 上评测 stopping/tool/order/arguments"),
        ("experiments/agentic/test_terminal_dts_device_tool.py",
         "Agentic Communication device tool：terminal-DtS typed gate 复用既有 opportunity/energy physics"),
        ("experiments/agentic/test_access_assist_device_tool.py",
         "Agentic Communication device tool：access-assist typed window 复用既有物理与时长账本"),
        ("experiments/agentic/test_model_protocol.py",
         "Agentic Communication model protocol：稳定 model-facing envelope/schema/hash，无 evaluator truth 泄漏"),
        ("experiments/agentic/test_backend_planner_consumer.py",
         "Agentic Communication model transport：复用 complete(messages) backend，进入 typed decision/usage ledger"),
        ("experiments/agentic/test_r1_model_eval_cli.py",
         "Agentic Communication R1 model CLI：冻结 trace/protocol，缺凭证不静默回退 scripted backend"),
        ("experiments/agentic/test_diagnosis_first_baseline.py",
         "Agentic Communication baseline：diagnosis-first 固定探测保持物理等价但增加证据/模型/tool 开销"),
        ("experiments/agentic/test_fixed_order_baseline.py",
         "Agentic Communication baseline：fixed-order eager 探测保持物理等价但增加无关 tool/model 开销"),
        ("experiments/agentic/test_generic_react_baseline.py",
         "Agentic Communication baseline：generic ReAct context 去除 EvidenceNeed/InvestigationState 仍保持同 Task/tool/physics"),
        ("experiments/agentic/test_model_context_matrix_cli.py",
         "Agentic Communication model matrix：task-conditioned/full-dump/generic-ReAct 统一 R1→R3，缺凭证不回退"),
        ("experiments/agentic/test_r3_model_eval_cli.py",
         "Agentic Communication R3 model CLI：冻结 task/context/model budget，缺后端不伪造结果"),
        ("experiments/agentic/test_upstream_gold_replacement.py",
         "Agentic Communication upstream gold：Task/EvidenceNeed/Percept/Context 分层替换并恢复 gold assembly hash"),
        ("experiments/agentic/test_attribution_protocol.py",
         "Agentic Communication attribution：runtime/model/evaluator layer ownership 与 rerun/posthoc 边界"),
        ("experiments/agentic/test_attribution_matrix.py",
         "Agentic Communication attribution matrix：upstream rerun 与 planner posthoc 累计替换且层间不偷渡"),
        ("experiments/agentic/test_metric_contract_extension.py",
         "Agentic Communication metrics：latency/AoI p50/p90/p95、recovery/resource/lifecycle 标量"),
        ("experiments/agentic/test_delivery_oracle_metrics.py",
         "Agentic Communication oracle metrics：actual→fixed-send→free-send-with-sample→link-opportunity ceiling 三分解"),
        ("experiments/agentic/test_configuration_execution_metrics.py",
         "Agentic Communication config metrics：OperationalTask desired vs evaluator-only applied state 时序积分"),
        ("experiments/agentic/test_robustness_manifest.py",
         "Agentic Communication robustness：weather/outage/scope/owner/scale 五轴成对坐标可编译"),
        ("experiments/agentic/test_task_transfer.py",
         "Agentic Communication transfer：Qili source-derived monitoring phases 编译为 OperationalTask 且保留 claim boundary"),
        ("experiments/agentic/test_o2_simulator_authority.py",
         "Agentic Communication experiment authority：O2 派生正式结果统一冻结 DEFAULT_FULLSIM，禁止手抄参数漂移"),
        ("experiments/agentic/test_communication_baseline_matrix.py",
         "Agentic Communication communication baselines：Local/AoI/EnergyAware/backup chooser + evaluator-only oracles"),
    ],
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="all",
                    choices=["mechanism", "monitoring", "claims", "paper", "seqref", "agentic", "all"])
    ap.add_argument("--quiet", action="store_true", help="print only failures")
    args = ap.parse_args()

    groups = list(CHECKS) if args.group == "all" else [args.group]
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [os.path.join(ROOT, "libs", "pylibs"), env.get("PYTHONPATH", "")]).rstrip(os.pathsep)

    failed: list[str] = []
    total = 0
    for group in groups:
        if not args.quiet:
            print(f"\n=== {group} ===")
        for rel, what in CHECKS[group]:
            total += 1
            path = os.path.join(HERE, rel)
            if not os.path.exists(path):
                print(f"  MISSING  {rel}")
                failed.append(rel)
                continue
            proc = subprocess.run([sys.executable, path], cwd=ROOT, env=env,
                                  capture_output=True, text=True)
            ok = proc.returncode == 0
            if not ok:
                failed.append(rel)
            if not args.quiet or not ok:
                print(f"  {'PASS' if ok else 'FAIL'}  {rel:48s} {what}")
            if not ok and proc.stdout:
                tail = [ln for ln in proc.stdout.splitlines() if "FAIL" in ln][-6:]
                for ln in tail:
                    print(f"          {ln.strip()}")

    print("\n" + "-" * 74)
    if failed:
        print(f"  {len(failed)}/{total} 项失败：")
        for f in failed:
            print(f"    - {f}")
        return 1
    print(f"  {total}/{total} 项通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
