#!/usr/bin/env bash
# 构建 paper/ 下英文稿与中文稿的 PDF。
#   en/  pdflatex + IEEEtran + bibtex
#   zh/  XeTeX + fontspec + Noto Serif CJK SC + bibtex
# 本机没有 xelatex 命令，也没有 ctex/xeCJK/luatexja/CJK 任一中文宏包，且 LuaLaTeX 缺
# luaotfload，fontspec 在 LuaTeX 下无法加载 OpenType 字体。因此中文路径用 XeTeX：它原生
# 支持 OpenType 字体与 CJK 断行，只需要一个自建的 xelatex 格式文件。本脚本在首次运行时
# 用 xetex -ini -etex 生成该格式并缓存在 .build/ 下（已被 .gitignore 忽略）。
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FMTDIR="${TEXMFVAR:-$HERE/.build}"
FMT="$FMTDIR/web2c/xelatex.fmt"

ensure_fmt() {
  if [ -f "$FMT" ]; then return; fi
  echo "[fmt] 未找到 xelatex.fmt，正在生成到 $FMTDIR/web2c/"
  mkdir -p "$FMTDIR/web2c" "$FMTDIR/gen"
  ( cd "$FMTDIR/gen" && xetex -ini -etex -jobname=xelatex -progname=xelatex xelatex.ini >/dev/null 2>&1 )
  mv "$FMTDIR/gen/xelatex.fmt" "$FMT/web2c/xelatex.fmt" 2>/dev/null || mv "$FMTDIR/gen/xelatex.fmt" "$FMT"
  rm -rf "$FMTDIR/gen"
  echo "[fmt] 完成：$FMT"
}

build_en() {
  echo "[en] pdflatex x3 + bibtex"
  cd "$HERE/en"
  pdflatex -interaction=nonstopmode main.tex >/dev/null
  bibtex main >/dev/null
  pdflatex -interaction=nonstopmode main.tex >/dev/null
  pdflatex -interaction=nonstopmode main.tex >/dev/null
  report en
}

build_zh() {
  echo "[zh] xetex x3 + bibtex"
  cd "$HERE/zh"
  export TEXMFVAR="$FMTDIR"
  xetex -fmt=xelatex -interaction=nonstopmode main.tex >/dev/null
  BIBINPUTS="..:${BIBINPUTS:-}" bibtex main >/dev/null
  xetex -fmt=xelatex -interaction=nonstopmode main.tex >/dev/null
  xetex -fmt=xelatex -interaction=nonstopmode main.tex >/dev/null
  report zh
}

report() {
  local d="$1"
  local pages over missing undef
  pages=$(grep -oE 'Output written on main.pdf \([0-9]+ pages' main.log | grep -oE '[0-9]+' || echo '?')
  over=$(grep -cE 'Overfull' main.log || true)
  missing=$(grep -c 'Missing character' main.log || true)
  undef=$(grep -cE 'Citation .* undefined|Reference .* undefined' main.log || true)
  printf '  %s: %s 页, overfull=%s, 缺字=%s, 未定义引用=%s\n' "$d" "$pages" "$over" "$missing" "$undef"
}

case "${1:-all}" in
  en) build_en ;;
  zh) ensure_fmt; build_zh ;;
  all) build_en; ensure_fmt; build_zh ;;
  *) echo "用法: $0 [en|zh|all]" >&2; exit 2 ;;
esac
echo "完成。产物：en/main.pdf、zh/main.pdf"
