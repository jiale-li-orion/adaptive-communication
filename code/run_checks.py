#!/usr/bin/env python3
"""Repository verification entry point organized by ownership.

Groups:
  substrate      shared communication physics/runtime/full-sim invariants
  benchmark      Layer-1 source-grounded benchmark construction guards
  compiler-eval  Decision-Semantic Compiler and Agent evaluation conformance
  claims         claim-ledger / repository-authority checks
  paper          generated-table consistency
  legacy         historical communication experiments kept reproducible

all runs every group, including legacy provenance checks.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

CHECKS = {'benchmark': [('evaluation/benchmark/test_case_contract.py',
                         'Layer-1 benchmark case contract：provenance/oracle/validity/split semantic guards'),
                        ('evaluation/benchmark/test_profile_contract.py',
                         'Layer-1 source profile contract：direct authority/provenance/adjacent evidence guards'),
                        ('evaluation/benchmark/test_profile_expansion.py',
                         'Layer-1 source profile expansion：only explicit source ranges become nominal coordinates'),
                        ('evaluation/benchmark/test_case_generation.py',
                         'Layer-1 nominal case generation：source profiles compile to V0-complete pre-oracle cases without invented hardness'),
                        ('evaluation/benchmark/test_source_derivation.py',
                         'Layer-1 source derivation：source tables/ranges resolve through explicit coverage samplers, not arbitrary draws'),
                        ('evaluation/benchmark/test_t1_reporting_contract.py',
                         'Layer-1 T1 reporting contract：source cadence owns completion deadline; historical research grace is excluded'),
                        ('evaluation/benchmark/test_capability_contract.py',
                         'Layer-1 capability profiles：normative path parameters, source gaps and device-local fallback remain separated'),
                        ('evaluation/benchmark/test_oracle_preflight.py',
                         'Layer-1 oracle preflight：source-resolved cases expose mapping/capability blockers before V1; no silent defaults'),
                        ('evaluation/benchmark/test_trace_contract.py',
                         'Layer-1 trace provenance：empirical/model-derived traces and controlled geometry stress remain distinguishable'),
                        ('evaluation/benchmark/test_case_augmentation.py',
                         'Layer-1 case augmentation：task/capability/trace composition preserves provenance and does not imply hardness'),
                        ('evaluation/benchmark/test_augmented_preflight.py',
                         'Layer-1 augmented preflight：composed worlds clear compatible capability/geometry blockers while payload/service semantics stay explicit'),
                        ('evaluation/benchmark/test_payload_contract.py',
                         'Layer-1 payload profiles：wire size comes from exact standard examples, not guessed average payloads'),
                        ('evaluation/benchmark/test_site_contract.py',
                         'Layer-1 site profiles：task jurisdiction, field-site identity and coordinate provenance are explicit'),
                        ('evaluation/benchmark/test_operationalization.py',
                         'Layer-1 operationalization：source-example payload + named controlled service semantics must clear preflight explicitly'),
                        ('evaluation/benchmark/test_v1_upper_envelope_oracle.py',
                         'Layer-1 V1 sanity oracle：exhaustive release-phase solvability under an explicit service upper envelope'),
                        ('evaluation/benchmark/test_v2_v3_dual_path_audit.py',
                         'Layer-1 V2/V3 audit：multiple legal paths do not count as hardness when ordinary fallback is common-safe'),
                        ('evaluation/benchmark/test_scenario_generator_v0_1.py',
                         'Layer-1 Generator v0.1：deterministic source-grounded scenario generation + exact oracle hard-case mining'),
                        ('evaluation/benchmark/test_deadline_reserve_baseline.py',
                         'Layer-1 degeneracy regression：deadline-aware reserve + EDF must expose Generator-v0.1 collapse'),
                        ('evaluation/benchmark/test_scenario_tree_v0_2.py',
                         'Layer-1 v0.2 alias-bundle：genuine EvidenceNeed exists but depth-2 timing shortcut must remain exposed'),
                        ('evaluation/benchmark/test_feasibility_conflict_planner.py',
                         'Conflict-guided evidence：action-feasibility conflict opens only timely resolving owner EvidenceNeed'),
                        ('evaluation/benchmark/test_feasibility_conflict_bounds.py',
                         'Conflict-guided bounds/context：sound L/U bounds and incremental evidence updates preserve feasibility'),
                        ('evaluation/benchmark/test_feasibility_conflict_policy.py',
                         'Conflict-guided policy：query only when needed; passive/direct mechanisms remain available'),
                        ('evaluation/benchmark/test_multi_evidence_scenario_tree.py',
                         'Multi-evidence async：owner queries can overlap; sufficient/complementary/irrelevant evidence remains distinguishable'),
                        ('evaluation/benchmark/test_conflict_guided_query_search.py',
                         'Conflict-guided query search：sound partition pruning preserves exact evidence decisions while reducing subset solves'),
                        ('evaluation/benchmark/test_scenario_generator_v0_3.py',
                         'Layer-1 Generator v0.3：process-generated mixed evidence regimes + computation-gap pilot'),
                        ('evaluation/benchmark/test_structural_scaling_v0_3.py',
                         'Layer-1 structural scaling：conflict preprocessing has a measurable crossover rather than universal speedup'),
                        ('evaluation/benchmark/test_scenario_generator_v0_4.py',
                         'Layer-1 Generator v0.4：multi-conflict process distribution + unified information/algorithm/computation ledger')],
 'substrate': [('substrate/runtime/operations.py', '执行语义自检：三维正交、五条不变量、三条性质'),
               ('substrate/tests/test_vendored_deps.py', 'vendored itmlogic 在无 PYTHONPATH 的干净 shell 可解析'),
               ('substrate/tests/test_repair_runtime.py', 'repair runtime：同信息 ordinary baselines 与预算语义'),
               ('substrate/tests/test_draw_keys.py', '报文级随机契约'),
               ('substrate/tests/test_journal_schema.py', '持久日志 schema 与字段集校验'),
               ('substrate/tests/test_energy_model.py', '能量模型手工核算'),
               ('substrate/tests/test_opportunity.py', '控制面机会模型与机会上界'),
               ('substrate/tests/test_node_model.py', '采样/缓存/上传链逐事件对齐'),
               ('substrate/tests/test_task_generator.py', '外生需求生成器'),
               ('substrate/tests/test_scorer.py', '评分器与真值边界'),
               ('substrate/tests/test_interfaces.py', '四接口与可审计证据'),
               ('substrate/tests/test_llm_planner.py', 'LLM 规划器、决策校验与调用账目'),
               ('substrate/tests/test_supply.py', '供电模型与可达性耦合'),
               ('substrate/tests/test_faults.py', '六类诊断故障注入'),
               ('substrate/tests/test_policies.py', '强基线：版本化配置与 VTC 风格恢复'),
               ('substrate/tests/test_recovery.py', '恢复归因：从日志重建 runtime 的两个标量'),
               ('substrate/tests/test_instance.py', '实例层验收：Task v1.1 最小闭环的手工可核算性质'),
               ('substrate/tests/audit_fairness.py', '业务层公平性审计'),
               ('substrate/joint/test_joint.py',
                'shared full-sim joint composition anchor / no-backup bit identity')],
 'compiler-eval': [('evaluation/agentic/test_runtime_harness.py',
                    'Agentic Communication runtime：自包含 contract、typed trace、与现有 comply 物理等价'),
                   ('evaluation/agentic/test_replay.py',
                    'Agentic Communication replay：R0 protocol、R1 frozen input、R2 exact context materialization'),
                   ('evaluation/agentic/test_task_catalog_and_trajectory.py',
                    'Agentic Communication benchmark：O1-O6 catalog、trajectory metrics、gold replacement schema'),
                   ('evaluation/agentic/test_planner_ledger.py',
                    'Agentic Communication model boundary：R1 ModelRequest/Attempt/Usage/PlannerDecision ledger'),
                   ('evaluation/agentic/test_owner_scoped_evidence.py',
                    'Agentic Communication evidence ownership：gateway owner read 可达/不可达语义且不改变物理行为'),
                   ('evaluation/agentic/test_evidence_owner_persistence.py',
                    'Agentic Communication Evidence World：跨 owner evidence 持久化并按 freshness 边界刷新'),
                   ('evaluation/agentic/test_live_planner_consumer.py',
                    'Agentic Communication live planner：typed model ledger、structured decision、R3 物理等价'),
                   ('evaluation/agentic/test_global_task_scope_authority.py',
                    'Agentic Communication global scope：Task scope 来自 deployment inventory，FullDump '
                    'baseline-only，O5/O6 candidate gold 与 legacy 五 seed 物理等价'),
                   ('evaluation/agentic/test_candidate_plan_selection.py',
                    'Agentic Communication plan selection：模型只选 Runtime candidate plan id，公共展开器恢复 typed effects 且保持 '
                    'O5 legacy physics'),
                   ('evaluation/agentic/test_no_action_sufficiency.py',
                    'Agentic Communication no-action sufficiency：compact control surface 对 closed hold 状态显式标记 '
                    'sufficient_for_no_action，禁止把无 blocking need 的稳定态写成 undetermined'),
                   ('evaluation/agentic/test_decision_closed_projection_v7.py',
                    'Agentic Communication v7 projection：rejected/dominated plan 不再把旧 unresolved guard 暴露成活跃待办，v6 '
                    '语义/物理保持不变'),
                   ('evaluation/agentic/test_query_positive_gateway_backup.py',
                    'Agentic Communication query-positive：gateway owner evidence 将 backup 从 conditional 闭合到 '
                    'rejected/supported，正分支唯一 effect、其他 fallback 继续 shadow'),
                   ('evaluation/agentic/test_woa_style_context.py',
                    'Agentic Communication WOA-style Context：共享 compact candidate/need/control surface，移除 Method '
                    'sufficiency certificate，同时提供 FullDump 合法 evidence'),
                   ('evaluation/agentic/test_woa_style_adapter.py',
                    'Agentic Communication WOA-style assurance：proposal integrity、dependency-scoped '
                    'repair、revalidation 与 APPLY/HOLD governor conformance'),
                   ('evaluation/agentic/test_query_positive_gateway_backup.py',
                    'Agentic Communication query-positive gateway backup：真实 owner EvidenceNeed 将 conditional '
                    'fallback 闭合为 rejected/supported，并保持其他 fallback shadow'),
                   ('evaluation/agentic/test_baseline_registry.py',
                    'Agentic Communication baseline registry：复用既有强 baseline，online/oracle 信息边界分离'),
                   ('evaluation/agentic/test_gold_replacement.py',
                    'Agentic Communication gold replacement：tool selection/order/arguments 分层归因且不偷渡参数'),
                   ('evaluation/agentic/test_gateway_backup_device_tool.py',
                    'Agentic Communication device tool：typed gateway-backup invocation 真实作用于 JointControlPlane'),
                   ('evaluation/agentic/test_multiround_evidence_tool.py',
                    'Agentic Communication multi-round：remote evidence 跨 simulator tick 后再 Context→device policy'),
                   ('evaluation/agentic/test_remote_observation_timing.py',
                    'Agentic Communication remote read：复用 backhaul_delay_s 与 tick phase ordering，禁止 same-tick oracle '
                    'replan'),
                   ('evaluation/agentic/test_live_gold_replacement.py',
                    'Agentic Communication R3 attribution：错误 planner 经累计 gold layers 恢复 reference physical outcome'),
                   ('evaluation/agentic/test_benchmark_split.py',
                    'Agentic Communication split：2022/2023/2024 source period 先于 seed，O1-O6 坐标可重放'),
                   ('evaluation/agentic/test_r1_evaluation.py',
                    'Agentic Communication R1 metrics：同一 PromptAssembly 上评测 stopping/tool/order/arguments'),
                   ('evaluation/agentic/test_terminal_dts_device_tool.py',
                    'Agentic Communication device tool：terminal-DtS typed gate 复用既有 opportunity/energy physics'),
                   ('evaluation/agentic/test_access_assist_device_tool.py',
                    'Agentic Communication device tool：access-assist typed window 复用既有物理与时长账本'),
                   ('evaluation/agentic/test_model_protocol.py',
                    'Agentic Communication model protocol：稳定 model-facing envelope/schema/hash，无 evaluator truth 泄漏'),
                   ('evaluation/agentic/test_backend_planner_consumer.py',
                    'Agentic Communication model transport：复用 complete(messages) backend，进入 typed decision/usage '
                    'ledger'),
                   ('evaluation/agentic/test_r1_model_eval_cli.py',
                    'Agentic Communication R1 model CLI：冻结 trace/protocol，缺凭证不静默回退 scripted backend'),
                   ('evaluation/agentic/test_diagnosis_first_baseline.py',
                    'Agentic Communication baseline：diagnosis-first 远端探测消耗 decision slack，并可扰动 outage '
                    'control/service'),
                   ('evaluation/agentic/test_fixed_order_baseline.py',
                    'Agentic Communication baseline：fixed-order eager 远端探测进入真实时序并改变 control trajectory'),
                   ('evaluation/agentic/test_generic_react_baseline.py',
                    'Agentic Communication baseline：generic ReAct context 去除 EvidenceNeed/InvestigationState 仍保持同 '
                    'Task/tool/physics'),
                   ('evaluation/agentic/test_model_context_matrix_cli.py',
                    'Agentic Communication model matrix：task-conditioned/full-dump/generic-ReAct 统一 R1→R3，缺凭证不回退'),
                   ('evaluation/agentic/test_r3_model_eval_cli.py',
                    'Agentic Communication R3 model CLI：冻结 task/context/model budget，缺后端不伪造结果'),
                   ('evaluation/agentic/test_upstream_gold_replacement.py',
                    'Agentic Communication upstream gold：Task/EvidenceNeed/Percept/Context 分层替换并恢复 gold assembly '
                    'hash'),
                   ('evaluation/agentic/test_attribution_protocol.py',
                    'Agentic Communication attribution：runtime/model/evaluator layer ownership 与 rerun/posthoc 边界'),
                   ('evaluation/agentic/test_attribution_matrix.py',
                    'Agentic Communication attribution matrix：upstream rerun 与 planner posthoc 累计替换且层间不偷渡'),
                   ('evaluation/agentic/test_metric_contract_extension.py',
                    'Agentic Communication metrics：latency/AoI p50/p90/p95、recovery/resource/lifecycle 标量'),
                   ('evaluation/agentic/test_delivery_oracle_metrics.py',
                    'Agentic Communication oracle metrics：actual→fixed-send→free-send-with-sample→link-opportunity '
                    'ceiling 三分解'),
                   ('evaluation/agentic/test_configuration_execution_metrics.py',
                    'Agentic Communication config metrics：OperationalTask desired vs evaluator-only applied state '
                    '时序积分'),
                   ('evaluation/agentic/test_robustness_manifest.py',
                    'Agentic Communication robustness：weather/outage/scope/owner/scale 五轴成对坐标可编译'),
                   ('evaluation/agentic/test_task_transfer.py',
                    'Agentic Communication transfer：Qili source-derived monitoring phases 编译为 OperationalTask 且保留 '
                    'claim boundary'),
                   ('evaluation/agentic/test_o2_simulator_authority.py',
                    'Agentic Communication experiment authority：O2 派生正式结果统一冻结 DEFAULT_FULLSIM，禁止手抄参数漂移'),
                   ('evaluation/agentic/test_communication_baseline_matrix.py',
                    'Agentic Communication communication baselines：Local/AoI/EnergyAware/backup chooser + '
                    'evaluator-only oracles'),
                   ('evaluation/agentic/test_action_conditioned_context.py',
                    'Agentic Communication method：candidate-action-conditioned context 在 localized O2 收缩 evidence '
                    '且保持物理语义'),
                   ('evaluation/agentic/test_action_context_algorithm.py',
                    'Agentic Communication method：candidate guard 驱动 passive contraction / shared-path evidence '
                    'expansion / disagreement graph'),
                   ('evaluation/agentic/test_mission_energy_gate_persistence.py',
                    'Agentic Communication strong baseline：mission energy_gate 的一次性准入在整个 Task revision 内持久，拒绝不会下一 '
                    'tick 偷偷失效'),
                   ('evaluation/agentic/test_o5_context_update_model_probe.py',
                    'Agentic Communication Task transition：旧 300s candidate 不能覆盖当前 3600s Task authority，R1 '
                    'transition evaluator 固定该语义'),
                   ('evaluation/agentic/test_o5_transition_context_model_probe.py',
                    'Agentic Communication O5 model matrix：h8/h9/h10 三事件 × 四 Context 冻结输入保持 Task authority 与 '
                    'physical consequence 引用')],
 'claims': [('evaluation/audits/audit_claims.py', '主张表：脚本与参考结果存在、状态取自固定集合'),
            ('evaluation/audits/audit_repository_authority.py',
             '仓库 authority：当前稿/CLAIMS/Experiment Design/immutable archive/本地试验区边界不漂移')],
 'paper': [('evaluation/audits/audit_tables.py', '论文表格由结果文件生成，稿件不手写表体')],
 'legacy': [('legacy-communication/experiments/test_failure_model.py', '11 类故障可复现'),
            ('legacy-communication/experiments/audit_consistency.py', '一致性审计：README 与结果文件逐行对齐'),
            ('legacy-communication/experiments/audit_seqref.py', '非预知序列参照：常数同源、台账校准、核例穷举、三方表与恒等式')]}

def main() -> int:
    ap = argparse.ArgumentParser()
    choices = [*CHECKS.keys(), "all"]
    ap.add_argument("--group", default="all", choices=choices)
    ap.add_argument("--quiet", action="store_true", help="print only failures")
    args = ap.parse_args()

    groups = list(CHECKS) if args.group == "all" else [args.group]
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([
        os.path.join(ROOT, "libs", "pylibs"),
        os.path.join(HERE, "substrate", "joint"),
        os.path.join(HERE, "substrate", "instance"),
        os.path.join(HERE, "substrate", "physics"),
        os.path.join(HERE, "substrate", "runtime"),
        os.path.join(HERE, "substrate", "reference"),
        os.path.join(HERE, "substrate", "monitoring"),
        os.path.join(HERE, "evaluation", "benchmark"),
        os.path.join(HERE, "evaluation", "agentic"),
        os.path.join(HERE, "legacy-communication", "runtime"),
        os.path.join(HERE, "legacy-communication", "experiments"),
        os.path.join(HERE, "legacy-communication", "analysis"),
        os.path.join(HERE, "legacy-communication", "v3joint"),
        env.get("PYTHONPATH", ""),
    ]).rstrip(os.pathsep)

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
                print(f"  {'PASS' if ok else 'FAIL'}  {rel:64s} {what}")
            if not ok:
                for stream in (proc.stdout, proc.stderr):
                    if stream:
                        for ln in stream.splitlines()[-12:]:
                            print(f"          {ln}")

    print("\n" + "-" * 86)
    if failed:
        print(f"  {len(failed)}/{total} checks failed:")
        for f in failed:
            print(f"    - {f}")
        return 1
    print(f"  {total}/{total} checks passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
