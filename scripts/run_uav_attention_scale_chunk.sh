#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PANEL="${1:?usage: $0 paper50|constructive100}"
case "$PANEL" in
  paper50) OUT="results/transfer/uav-attention-n10-scale-paper50" ;;
  constructive100) OUT="results/transfer/uav-attention-n10-scale-constructive100" ;;
  *) echo "unknown panel: $PANEL" >&2; exit 64 ;;
esac

CPU_SET="${UAV_SCALE_CPU_SET:-0,1}"
MAX_NEW_SEEDS="${UAV_SCALE_MAX_NEW_SEEDS:-5}"

export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

exec nice -n 10 taskset -c "$CPU_SET" \
  python3 code/evaluation/transfer/run_uav_attention_scale_extension.py \
    --panel "$PANEL" \
    --out "$OUT" \
    --max-new-seeds "$MAX_NEW_SEEDS"
