#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE/en"

pdflatex -interaction=nonstopmode main.tex >/dev/null
BIBINPUTS="../..:${BIBINPUTS:-}" bibtex main >/dev/null
pdflatex -interaction=nonstopmode main.tex >/dev/null
pdflatex -interaction=nonstopmode main.tex >/dev/null

pages=$(grep -oE 'Output written on main.pdf \([0-9]+ pages' main.log | grep -oE '[0-9]+' || echo '?')
over=$(grep -c 'Overfull' main.log || true)
missing=$(grep -c 'Missing character' main.log || true)
undef=$(grep -cE 'Citation .* undefined|Reference .* undefined' main.log || true)
printf 'agentic/en: %s pages, overfull=%s, missing=%s, undefined=%s\n' \
  "$pages" "$over" "$missing" "$undef"

if [ "$over" -ne 0 ] || [ "$missing" -ne 0 ] || [ "$undef" -ne 0 ]; then
  exit 1
fi
