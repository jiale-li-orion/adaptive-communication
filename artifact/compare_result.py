#!/usr/bin/env python3
"""compare_result.py — 按容差深比较两份 JSON，打印前若干处差异。

用法：
    python3 artifact/compare_result.py <冻结值> <本次值> [--rtol 1e-9] [--max-diff 8]

退出码 0 表示在容差内相等，1 表示存在差异。数值按相对容差比较，其余类型要求严格相等；
浮点直接按 `==` 比较会把 `0.4` 与 `0.4000000000000001` 判成不一致，产生噪声。

Run: python3 artifact/compare_result.py results/reference/x.json results/x.json
"""
from __future__ import annotations

import argparse
import json
import sys


def walk(a, b, path, rtol, out, limit):
    if len(out) >= limit:
        return
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f"{path}.{k}: 本次新增")
            elif k not in b:
                out.append(f"{path}.{k}: 本次缺失")
            else:
                walk(a[k], b[k], f"{path}.{k}", rtol, out, limit)
        return
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: 长度 {len(a)} -> {len(b)}")
            return
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, f"{path}[{i}]", rtol, out, limit)
        return
    if isinstance(a, bool) or isinstance(b, bool):
        if a is not b:
            out.append(f"{path}: {a} -> {b}")
        return
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if abs(a - b) <= rtol * max(1.0, abs(a), abs(b)):
            return
        out.append(f"{path}: {a} -> {b}")
        return
    if a != b:
        out.append(f"{path}: {a!r} -> {b!r}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("frozen")
    ap.add_argument("fresh")
    ap.add_argument("--rtol", type=float, default=1e-9)
    ap.add_argument("--max-diff", type=int, default=8)
    args = ap.parse_args()

    try:
        a = json.load(open(args.frozen, encoding="utf-8"))
    except FileNotFoundError:
        print(f"FAIL  冻结值缺失 {args.frozen}")
        return 1
    try:
        b = json.load(open(args.fresh, encoding="utf-8"))
    except FileNotFoundError:
        print(f"FAIL  本次结果缺失 {args.fresh}")
        return 1

    diffs: list[str] = []
    walk(a, b, "$", args.rtol, diffs, args.max_diff)
    if diffs:
        print(f"FAIL  与冻结值不符（前 {len(diffs)} 处）")
        for d in diffs:
            print(f"        {d}")
        return 1
    print("PASS  与冻结值一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
