#!/usr/bin/env bash
# new_paper_repo.sh — 由 template/ 生成一个新的论文仓库。
#
# 机制文件（比较器与两个审计）从本仓库复制，而不是在 template/ 里再放一份：同一份实现只有一处，
# 否则两个副本会各自演化。文档类文件（README、主张表、登记册、AE、spec）属于每个仓库自己的内容，
# 由 template/ 提供。
#
# 用法：
#   ./scripts/new_paper_repo.sh ../my-next-paper
#   ./scripts/new_paper_repo.sh ../my-next-paper --no-git    不初始化 git
#
# 脚本末尾会在新仓库里跑一次 make check 与 make tables --check，接线不通就不算完成。
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TPL="$HERE/template"

#: 从本仓库取走的机制文件：路径相对于仓库根，两边布局相同。
BORROW=(
  "artifact/compare_result.py"
  "code/experiments/audit_claims.py"
  "code/experiments/audit_tables.py"
)

TARGET="${1:-}"
DO_GIT=1
[ "${2:-}" = "--no-git" ] && DO_GIT=0

if [ -z "$TARGET" ]; then
  sed -n '2,16p' "$0"
  exit 2
fi
[ -d "$TPL" ] || { echo "找不到模板目录 $TPL" >&2; exit 1; }
if [ -e "$TARGET" ] && [ -n "$(ls -A "$TARGET" 2>/dev/null)" ]; then
  echo "目标目录已存在且非空：$TARGET" >&2
  exit 1
fi

echo "== 1/6 复制模板到 $TARGET"
mkdir -p "$TARGET"
cp -R "$TPL/." "$TARGET/"

echo "== 2/6 复制机制文件（单一实现来源）"
for rel in "${BORROW[@]}"; do
  src="$HERE/$rel"
  [ -f "$src" ] || { echo "缺机制文件 $rel" >&2; exit 1; }
  mkdir -p "$TARGET/$(dirname "$rel")"
  cp "$src" "$TARGET/$rel"
  echo "   $rel"
done

echo "== 3/6 跑一次示例实验，产出结果文件"
cd "$TARGET"
python3 code/experiments/example_metric.py

echo "== 4/6 生成示例表格"
python3 scripts/make_tables.py >/dev/null
ls paper/generated | sed 's/^/   /'

if [ "$DO_GIT" -eq 1 ]; then
  echo "== 5/6 初始化 git"
  git init -q
  git add -A
  git -c user.name="$(git -C "$HERE" config user.name || echo paper-repo-template)" \
      -c user.email="$(git -C "$HERE" config user.email || echo template@localhost)" \
      commit -q -m "初始化：论文仓库骨架

由 agentic-communication 的 template/ 生成。四条不可违例（克隆可验证、数字单一来源、
主张单一状态、历史不可变）已接好线：主张表、结果登记册、冻结基准、表格生成器与两个审计。
下一步见 template/README.md 的「需要你改的地方」。"
  echo "   已提交初始状态"
else
  echo "== 5/6 跳过 git 初始化"
fi

echo "== 6/6 验证接线"
make check
make tables ARGS=--check

cat <<EOF

新仓库就绪：$(cd "$TARGET" && pwd)

接下来按 template/README.md 的「需要你改的地方」逐项替换：
  1. results/CLAIMS.md      换成真实主张，删掉示例行
  2. results/README.md      登记真实结果文件
  3. scripts/make_tables.py 换成真实表格定义
  4. scripts/get_deps.sh 与 get_data.sh  换成真实的获取命令
  5. artifact/AE.md         填尖括号处的环境与逐主张判定
  6. spec/                  放规范性声明

规范全文：$HERE/PAPER-REPO-STANDARD.md（中文版 PAPER-REPO-STANDARD.zh.md）
EOF
