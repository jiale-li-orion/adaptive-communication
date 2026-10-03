#!/usr/bin/env bash
# reproduce_all.sh — 逐主张复现并给出判定。
#
# 对每条主张：先跑出结果文件（除非 --check-only），再与 results/reference/ 的冻结值逐项比较。
# 判定由 artifact/compare_result.py 给出，数值按相对容差比较，不按字符串比较。
#
# 用法：
#   ./artifact/reproduce_all.sh                 全部主张
#   ./artifact/reproduce_all.sh --only C2 C5    只跑指定主张
#   ./artifact/reproduce_all.sh --check-only    只比较，不重跑（用现有结果文件）
#   ./artifact/reproduce_all.sh --list          列出主张与命令
#
# C8 的 agent 主结果由真实模型调用产生，需要 DEEPSEEK_API_KEY，本脚本只跑其中的零 LLM
# 离线重放，并把保存的汇总与冻结值比较；需要凭据的部分在 AE.md 里单列。

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CHECK_ONLY=0
ONLY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --check-only) CHECK_ONLY=1; shift ;;
    --only) shift; while [ $# -gt 0 ] && [ "${1#--}" = "$1" ]; do ONLY="$ONLY $1"; shift; done ;;
    --list) ONLY="__LIST__"; shift ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "未知参数 $1" >&2; exit 2 ;;
  esac
done

# ID | 是否需要真实模型调用 | 复现命令 | 结果文件（逗号分隔） | 冻结参考（可选；逗号分隔）
#
# 第 5 列为空时沿用旧规则：results/reference/<结果 basename>。
# Agentic 结果大量使用 aggregate.json/audit.json，basename 会冲突，因此 A* 显式给出 reference path。
CLAIMS=(
"C1|no|python3 code/legacy-communication/v3joint/r30c_walls.py|results/communication-substrate/claims/r30c_walls.json|results/reference/communication-substrate/claims/r30c_walls.json"
"C2|no|python3 code/legacy-communication/v3joint/r41_expiry_equiv.py|results/communication-substrate/claims/r41_expiry_equiv.json|results/reference/communication-substrate/claims/r41_expiry_equiv.json"
"C3|no|python3 code/legacy-communication/v3joint/r37e_full_seeds.py|results/communication-substrate/claims/r37e_full_seeds.json|results/reference/communication-substrate/claims/r37e_full_seeds.json"
"C4|no|python3 code/legacy-communication/v3joint/r44_fullhorizon_attribution.py|results/communication-substrate/claims/r44_fullhorizon_attribution.json|results/reference/communication-substrate/claims/r44_fullhorizon_attribution.json"
"C5|no|python3 code/legacy-communication/v3joint/c5_matrix.py 0 1 2|results/communication-substrate/claims/c5_matrix.json|results/reference/communication-substrate/claims/c5_matrix.json"
"C6|no|python3 code/legacy-communication/v3joint/r39_envelope.py && python3 code/legacy-communication/v3joint/merge_r39.py|results/communication-substrate/claims/r39_table.json|results/reference/communication-substrate/claims/r39_table.json"
"C7|no|python3 code/legacy-communication/v3joint/r40_local_attribution.py|results/communication-substrate/claims/r40_local_attribution.json|results/reference/communication-substrate/claims/r40_local_attribution.json"
"C8|creds|python3 code/legacy-communication/v3joint/r42_claim_relabel.py && python3 code/legacy-communication/v3joint/r43_cert_v5_replay.py|results/communication-substrate/claims/r42_claim_relabel.json,results/communication-substrate/claims/r43_cert_v5_replay.json,results/communication-substrate/claims/r38_three_arm_summary.json|results/reference/communication-substrate/claims/r42_claim_relabel.json,results/reference/communication-substrate/claims/r43_cert_v5_replay.json,results/reference/communication-substrate/claims/r38_three_arm_summary.json"
"C9|no|python3 code/legacy-communication/v3joint/c5_seqref.py && python3 code/legacy-communication/experiments/measure_seqref_calibration.py|results/communication-substrate/claims/c5_seqref.json,results/communication-substrate/claims/c5_seqref_calibration.json|results/reference/communication-substrate/claims/c5_seqref.json,results/reference/communication-substrate/claims/c5_seqref_calibration.json"
"C10|no|python3 code/legacy-communication/analysis/retention_deadline_audit.py|results/communication-substrate/claims/retention_deadline_audit.json|results/reference/communication-substrate/claims/retention_deadline_audit.json"
"C11|no|python3 code/legacy-communication/analysis/reverse_feedback_budget.py|results/communication-substrate/claims/reverse_feedback_budget.json|results/reference/communication-substrate/claims/reverse_feedback_budget.json"
"A1|no|python3 code/evaluation/agentic/run_o2_risk_escalation.py --variant global --seeds 0,1,2,3,4 && python3 code/evaluation/agentic/run_o2_risk_escalation.py --variant localized --seeds 0,1,2,3,4|results/agentic/o2-risk-escalation-v1/aggregate.json,results/agentic/o2-risk-escalation-v1/audit.json,results/agentic/o2-localized-risk-escalation-v1/aggregate.json,results/agentic/o2-localized-risk-escalation-v1/audit.json|results/reference/agentic/A1-o2-global-aggregate.json,results/reference/agentic/A1-o2-global-audit.json,results/reference/agentic/A1-o2-localized-aggregate.json,results/reference/agentic/A1-o2-localized-audit.json"
"A2|no|python3 code/evaluation/agentic/run_o2_baseline_matrix.py --seeds 0,1,2,3,4|results/agentic/o2-baseline-matrix-v1/aggregate.json,results/agentic/o2-baseline-matrix-v1/audit.json|results/reference/agentic/A2-baseline-aggregate.json,results/reference/agentic/A2-baseline-audit.json"
"A3|no|python3 code/evaluation/agentic/run_source_period_smoke.py --seed 0 && python3 code/evaluation/agentic/run_robustness_matrix.py|results/agentic/source-period-smoke-v1.json,results/agentic/robustness-matrix-v1/aggregate.json,results/agentic/robustness-matrix-v1/audit.json|results/reference/agentic/A3-source-period.json,results/reference/agentic/A3-robustness-aggregate.json,results/reference/agentic/A3-robustness-audit.json"
"A4|no|python3 code/evaluation/agentic/run_task_transfer_qili.py --seeds 0,1,2,3,4|results/agentic/task-transfer-qili-v1/aggregate.json,results/agentic/task-transfer-qili-v1/audit.json|results/reference/agentic/A4-transfer-aggregate.json,results/reference/agentic/A4-transfer-audit.json"
"A5|no|python3 code/evaluation/agentic/run_attribution_matrix_infra.py --turns 20|results/agentic/attribution-matrix-infra-v1/aggregate.json,results/agentic/attribution-matrix-infra-v1/audit.json|results/reference/agentic/A5-attribution-aggregate.json,results/reference/agentic/A5-attribution-audit.json"
"A6|no|python3 code/evaluation/agentic/run_communication_baseline_matrix.py --seeds 0,1,2,3,4|results/agentic/communication-baseline-matrix-v1/aggregate.json,results/agentic/communication-baseline-matrix-v1/audit.json|results/reference/agentic/A6-communication-aggregate.json,results/reference/agentic/A6-communication-audit.json"
)

if [ "$ONLY" = "__LIST__" ]; then
  printf '%-4s %-6s %-58s %s\n' ID 凭据 命令 结果文件
  for row in "${CLAIMS[@]}"; do
    IFS='|' read -r id creds cmd res refs <<< "$row"
    printf '%-4s %-6s %-58s %s\n' "$id" "$creds" "${cmd:0:56}" "$res"
  done
  exit 0
fi

selected() {
  [ -z "$ONLY" ] && return 0
  for x in $ONLY; do [ "$x" = "$1" ] && return 0; done
  return 1
}

pass=0; fail=0; skipped=0
for row in "${CLAIMS[@]}"; do
  IFS='|' read -r id creds cmd res refs <<< "$row"
  selected "$id" || continue

  echo
  echo "=== $id ==="
  if [ "$creds" = "creds" ]; then
    echo "  说明：主结果需要真实模型调用（DEEPSEEK_API_KEY）；本脚本只跑零 LLM 的离线重放部分。"
  fi

  if [ "$CHECK_ONLY" -eq 0 ]; then
    echo "  运行 ${cmd}"
    if ! eval "$cmd" >/dev/null 2>&1; then
      echo "  FAIL  复现命令退出非零"
      fail=$((fail+1)); continue
    fi
  else
    echo "  --check-only：不重跑"
  fi

  ok=1
  IFS=',' read -ra files <<< "$res"
  ref_files=()
  if [ -n "${refs:-}" ]; then
    IFS=',' read -ra ref_files <<< "$refs"
    if [ "${#ref_files[@]}" -ne "${#files[@]}" ]; then
      echo "  FAIL  结果文件与冻结参考数量不一致"
      ok=0
    fi
  fi
  for i in "${!files[@]}"; do
    f="${files[$i]}"
    if [ -n "${refs:-}" ]; then
      frozen="${ref_files[$i]}"
    else
      base="$(basename "$f")"
      frozen="results/reference/$base"
    fi
    if [ ! -f "$frozen" ]; then
      echo "  FAIL  无冻结值 $frozen"
      ok=0; continue
    fi
    # Agentic audits hash run_manifest/runtime traces; those hashes are useful for
    # a single run but include non-semantic timestamps. Freeze the verdict fields,
    # not the wall-clock identity of a rerun.
    if python3 artifact/compare_result.py "$frozen" "$f" --ignore-key result_hashes; then
      :
    else
      ok=0
    fi
  done
  if [ "$ok" -eq 1 ]; then pass=$((pass+1)); else fail=$((fail+1)); fi
done

echo
echo "----------------------------------------------------------------------"
echo "  通过 $pass 条，失败 $fail 条"
[ "$fail" -eq 0 ]
