#!/usr/bin/env python3
"""audit_tables.py — 论文表格必须由结果文件生成，不能手写。

检查三件事：

  1. `scripts/make_tables.py --check` 通过：`paper/generated/` 的内容与结果文件当前推出的内容
     一致。不一致说明结果变了而表格没重新生成，或者有人手改了生成物；
  2. 两份稿件的五个表体都只经 `\\input` 引入生成物，稿件里没有手写的表格行；
  3. 每个 `\\input` 指向的文件存在。

第 2 条是这个检查的核心：它堵住"数字写回正文"这条路。生成物被手改时它不一定能发现（那由第 1 条
负责），但把 `\\input` 换回手抄行一定会红。

Run: python3 code/experiments/audit_tables.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
GENERATED = os.path.join(ROOT, "paper", "generated")
MANUSCRIPTS = {"en": os.path.join(ROOT, "paper", "en", "main.tex"),
               "zh": os.path.join(ROOT, "paper", "zh", "main.tex")}
TABLES = ("walls", "expiry", "lease", "attribution", "placement")
FAIL: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")
    if not ok:
        FAIL.append(name)


def main() -> int:
    print("\n[20] 论文表格由结果文件生成")

    proc = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "make_tables.py"), "--check"],
                          cwd=ROOT, capture_output=True, text=True)
    check("生成物与结果文件一致", proc.returncode == 0,
          (proc.stdout.strip().splitlines() or [""])[-1][:90])

    for lang, path in MANUSCRIPTS.items():
        if not os.path.exists(path):
            check(f"{lang} 稿件存在", False, path)
            continue
        text = open(path, encoding="utf-8").read()
        for name in TABLES:
            target = f"../generated/table_{name}.{lang}.tex"
            check(f"{lang}/{name} 经 input 引入", f"\\input{{{target}}}" in text)
        # 稿件里不得残留构建表格行的 & 与 \toprule
        check(f"{lang} 稿件无手写表体", "\\toprule" not in text,
              "找到 \\toprule" if "\\toprule" in text else "")

    for lang in MANUSCRIPTS:
        for name in TABLES:
            p = os.path.join(GENERATED, f"table_{name}.{lang}.tex")
            check(f"生成物存在 {os.path.basename(p)}", os.path.exists(p))

    if FAIL:
        print(f"\n  {len(FAIL)} 项失败")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
