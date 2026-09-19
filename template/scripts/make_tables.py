#!/usr/bin/env python3
r"""make_tables.py — 由结果文件生成论文表格体。

表格体不手写：生成物写进 `paper/generated/`，稿件用 `\input` 引入，因此一张表只有一处数字。
生成物入库，结果文件变动时必须在同一次提交里重新生成，否则 `audit_tables.py` 会红。

数值按十进制 ROUND_HALF_UP 格式化。直接用 `%.3f` 会按二进制表示决定末位：0.3695 的实际存储
略小于 0.3695，于是输出 0.369，而人按四舍五入写 0.370，同一份数据出现两种写法。

用法：
    python3 scripts/make_tables.py            # 写入 paper/generated/
    python3 scripts/make_tables.py --check    # 只比较，不写；有差异则退出非零
"""
from __future__ import annotations

import argparse
import json
import os
from decimal import Decimal, ROUND_HALF_UP

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
GEN = os.path.join(ROOT, "paper", "generated")

#: 每张表的列宽。加入新表时在这里登记，并写一个返回 (head, rows) 的函数。
COLPEC = {"example": "lcc"}


def load(rel: str):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def f(x: float, nd: int) -> str:
    q = Decimal(1).scaleb(-nd)
    return str(Decimal(repr(x)).quantize(q, rounding=ROUND_HALF_UP))


def table_example():
    """示例表：由 results/example_metric.json 生成。换成真实表的起点。"""
    d = load("results/example_metric.json")
    head = {"en": "Seed & Value (4 dp)", "zh": "种子 & 取值（4 位小数）"}
    out = {}
    for lang in ("en", "zh"):
        rows = [f"{s} & {f(v, 4)}" for s, v in sorted(d["per_seed"].items(), key=lambda kv: int(kv[0]))]
        rows.append("\\midrule")
        rows.append(f"\\textbf{{{ {'en': 'Mean', 'zh': '均值'}[lang] }}} & "
                    f"\\textbf{{{f(d['summary']['mean'], 4)}}}")
        out[lang] = (head[lang], rows)
    return out


TABLES = {"example": table_example}


def render(name: str, head: str, rows: list[str]) -> str:
    out = ["\\toprule", head + "\\\\", "\\midrule"]
    for r in rows:
        rs = r.rstrip()
        if rs in ("\\midrule", "\\bottomrule") or rs.endswith("\\\\"):
            out.append(r)
        else:
            out.append(r + "\\\\")
    out.append("\\bottomrule")
    body = "\n".join(out)
    return ("%% 由 scripts/make_tables.py 生成，勿手改；数字来自结果文件。\n"
            f"\\begin{{tabular}}{{{COLPEC[name]}}}\n{body}\n\\end{{tabular}}\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只比较，不写")
    args = ap.parse_args()

    os.makedirs(GEN, exist_ok=True)
    stale, written = [], []
    for name, fn in TABLES.items():
        spec = fn()
        for lang in ("en", "zh"):
            head, rows = spec[lang]
            text = render(name, head, rows)
            path = os.path.join(GEN, f"table_{name}.{lang}.tex")
            old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
            if old == text:
                continue
            if args.check:
                stale.append(os.path.relpath(path, ROOT))
            else:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
                written.append(os.path.relpath(path, ROOT))

    if args.check:
        if stale:
            print("生成物与结果文件不一致，需要重新生成：")
            for s in stale:
                print(f"  {s}")
            return 1
        print("生成物与结果文件一致")
        return 0
    print("已写入：\n  " + "\n  ".join(written) if written else "生成物已是最新，无改动")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
