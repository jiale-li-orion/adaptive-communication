#!/usr/bin/env python3
"""run_checks.py — 唯一检查入口。

自动收集 `code/experiments/` 下文件名以 `audit_` 或 `test_` 开头的脚本并逐个运行。每个检查是
独立脚本，打印 PASS/FAIL 并以退出码表示结论；本入口只看退出码，不解析它们的输出文字，因为
"检查失败却打印自信的行"正是这些检查存在的理由。

新增检查只需把文件放进 `code/experiments/`，不需要改本文件。

Run: python3 code/run_checks.py [--quiet]
"""
from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def discover() -> list[str]:
    out: list[str] = []
    for pat in ("code/experiments/audit_*.py", "code/experiments/test_*.py"):
        out += sorted(os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(ROOT, pat)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="只打印失败项")
    args = ap.parse_args()

    checks = discover()
    if not checks:
        print("  未发现检查：在 code/experiments/ 放置 audit_*.py 或 test_*.py")
        return 1

    failed = []
    for rel in checks:
        proc = subprocess.run([sys.executable, os.path.join(ROOT, rel)],
                              cwd=ROOT, capture_output=True, text=True)
        ok = proc.returncode == 0
        if not ok:
            failed.append(rel)
        if not args.quiet or not ok:
            print(f"  {'PASS' if ok else 'FAIL'}  {rel}")
        if not ok:
            for ln in [x for x in proc.stdout.splitlines() if "FAIL" in x][-6:]:
                print(f"          {ln.strip()}")

    print("\n" + "-" * 74)
    if failed:
        print(f"  {len(failed)}/{len(checks)} 项失败：")
        for f in failed:
            print(f"    - {f}")
        return 1
    print(f"  {len(checks)}/{len(checks)} 项通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
