#!/usr/bin/env bash
# 获取需获取依赖（不入库的第三方 Python 包）。幂等：目标目录里已可导入时跳过。
#
# 传播模型用 itmlogic（Longley-Rice）。它连同依赖装进 libs/pylibs，与 Makefile 和
# code/run_checks.py 里的 PYTHONPATH 一致。缺它时依赖它的检查直接导入失败，不静默换模型。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="$ROOT/libs/pylibs"
PKGS=(itmlogic)

if PYTHONPATH="$TARGET" python3 -c "import itmlogic" >/dev/null 2>&1; then
  ver=$(PYTHONPATH="$TARGET" python3 -c "import itmlogic, importlib.metadata as m; print(m.version('itmlogic'))" 2>/dev/null || echo "?")
  echo "skip   itmlogic 已就绪（版本 $ver）"
  exit 0
fi

echo "install ${PKGS[*]} -> $TARGET"
mkdir -p "$TARGET"
python3 -m pip install --quiet --no-cache-dir --upgrade --target "$TARGET" "${PKGS[@]}"

if ! PYTHONPATH="$TARGET" python3 -c "import itmlogic" >/dev/null 2>&1; then
  echo "ERROR  itmlogic 安装后仍无法导入，检查 pip 源与网络" >&2
  exit 1
fi
echo "第三方依赖就绪：$TARGET"
