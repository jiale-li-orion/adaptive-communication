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

# ID | 是否需要真实模型调用 | 复现命令 | 结果文件（逗号分隔）
CLAIMS=(
"C1|no|python3 code/v3joint/r30c_walls.py|results/r30c_walls.json"
"C2|no|python3 code/v3joint/r41_expiry_equiv.py|results/r41_expiry_equiv.json"
"C3|no|python3 code/v3joint/r37e_full_seeds.py|results/r37e_full_seeds.json"
"C4|no|python3 code/v3joint/r44_fullhorizon_attribution.py|results/r44_fullhorizon_attribution.json"
"C5|no|python3 code/v3joint/r46_lease_sweep.py && python3 code/v3joint/r47_lease_energy.py && python3 code/v3joint/r48_ttl_vs_lease.py|results/r46_lease_sweep.json,results/r47_lease_energy.json,results/r48_ttl_vs_lease.json"
"C6|no|python3 code/v3joint/r39_envelope.py && python3 code/v3joint/merge_r39.py|results/agent_traces/r39_table.json"
"C7|no|python3 code/v3joint/r40_local_attribution.py|results/r40_local_attribution.json"
"C8|creds|python3 code/v3joint/r42_claim_relabel.py && python3 code/v3joint/r43_cert_v5_replay.py|results/r42_claim_relabel.json,results/r43_cert_v5_replay.json,results/agent_traces/r38_three_arm_summary.json"
)

if [ "$ONLY" = "__LIST__" ]; then
  printf '%-4s %-6s %-58s %s\n' ID 凭据 命令 结果文件
  for row in "${CLAIMS[@]}"; do
    IFS='|' read -r id creds cmd res <<< "$row"
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
  IFS='|' read -r id creds cmd res <<< "$row"
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
  for f in "${files[@]}"; do
    base="$(basename "$f")"
    frozen="results/reference/$base"
    if [ ! -f "$frozen" ]; then
      echo "  FAIL  无冻结值 $frozen"
      ok=0; continue
    fi
    if python3 artifact/compare_result.py "$frozen" "$f"; then
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
