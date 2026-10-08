#!/usr/bin/env bash
set -euo pipefail

# Resource-safe wrapper for the frozen Layer-1 paper LLM test.
#
# Scientific protocol remains owned by PAPER-BASELINE-PROTOCOL.json and the
# Python runner.  This wrapper controls only host scheduling / chunk size:
#   - 2 logical CPUs by default;
#   - low process priority;
#   - single-thread numerical libraries;
#   - 2 new paper rows per invocation;
#   - 2 s cooldown after each row.
#
# Re-run the exact same command until the Python runner returns 0 / aggregate
# complete=true.  Exit code 2 simply means the frozen cohort is not complete yet.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CPU_SET="${LAYER1_LLM_CPU_SET:-0,1}"
MAX_NEW_ROWS="${LAYER1_LLM_MAX_NEW_ROWS:-2}"
SLEEP_S="${LAYER1_LLM_INTER_ROW_SLEEP_S:-2}"

export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

exec nice -n 10 taskset -c "$CPU_SET" \
  python3 code/evaluation/benchmark/run_layer1_paper_llm_eval.py \
    --execute-frozen-test \
    --out results/benchmark/layer1-paper-llm-test \
    --max-new-rows "$MAX_NEW_ROWS" \
    --inter-row-sleep-s "$SLEEP_S"
