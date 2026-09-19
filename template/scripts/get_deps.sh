#!/usr/bin/env bash
# 获取需获取依赖（第三方 Python 包）。幂等：目标目录里已可导入时跳过。
#
# **本文件是占位骨架，必须替换。** 把本项目需要的第三方包写进 PKGS，并让依赖它们的检查在
# 缺失时直接导入失败，而不是静默换用更弱的实现。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="$ROOT/libs/pylibs"
PKGS=()   # 例：PKGS=(numpy itmlogic)

if [ ${#PKGS[@]} -eq 0 ]; then
  echo "scripts/get_deps.sh 尚未配置：PKGS 为空。" >&2
  echo "若本项目没有第三方依赖，删除本文件并在 Makefile 中去掉 deps 目标。" >&2
  exit 1
fi

mkdir -p "$TARGET"
python3 -m pip install --quiet --no-cache-dir --upgrade --target "$TARGET" "${PKGS[@]}"
echo "第三方依赖就绪：$TARGET"
