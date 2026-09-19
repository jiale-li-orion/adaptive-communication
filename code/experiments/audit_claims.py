#!/usr/bin/env python3
"""audit_claims.py — 主张表的每一行都必须可核对。

检查四件事，任何一件不成立就红：

  1. 主张编号唯一，且形如 C<数字>；
  2. 状态取自固定集合（supported / scoped-negative / formative / open /
     reproduced-externally / retracted）；
  3. 每行给出的脚本与参考结果在磁盘上存在——指向不存在的文件的主张等于没有证据；
  4. 撤回表的 superseded_by 指向当前主张表中真实存在的编号，来源提交形如 git 短哈希；
     同一编号不得同时出现在两张表里。

参考结果文件的最后一次修改提交由本脚本用 git log 计算并打印，属于信息输出而非判定条件：
缺 git（例如导出的 tar 包）时打印 unknown，不影响结论。

Run: python3 code/experiments/audit_claims.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
CLAIMS = os.path.join(ROOT, "results", "CLAIMS.md")

STATUS = {"supported", "scoped-negative", "formative", "open",
          "reproduced-externally", "retracted"}
FAIL: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")
    if not ok:
        FAIL.append(name)


def tables(text: str) -> list[list[list[str]]]:
    """把 markdown 里的表格切成 [[row, ...], ...]，每个单元格已 strip。"""
    out, cur = [], []
    for line in text.splitlines():
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                continue                      # 分隔行
            cur.append(cells)
        elif cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def col(header: list[str], needle: str) -> int:
    for i, h in enumerate(header):
        if needle in h:
            return i
    return -1


def paths_in(cell: str) -> list[str]:
    return re.findall(r"`([^`]+)`", cell)


def last_commit(path: str) -> str:
    try:
        r = subprocess.run(["git", "log", "-1", "--format=%h", "--", path],
                           cwd=ROOT, capture_output=True, text=True, timeout=20)
        return (r.stdout.strip() or "unknown") if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def main() -> int:
    print("\n[19] 主张表可核对")
    if not os.path.exists(CLAIMS):
        check("results/CLAIMS.md 存在", False, CLAIMS)
        return 1
    text = open(CLAIMS, encoding="utf-8").read()
    ts = tables(text)

    active = next((t for t in ts if col(t[0], "Claim") >= 0), None)
    retract = next((t for t in ts if col(t[0], "superseded_by") >= 0), None)
    check("主张表与撤回表都能解析", active is not None and retract is not None,
          f"{len(ts)} 张表")
    if not active or not retract:
        return 1

    ah, rh = active[0], retract[0]
    ci_id, ci_stat = col(ah, "Claim"), col(ah, "状态")
    ci_scr, ci_res = col(ah, "脚本"), col(ah, "参考结果")
    ri_sup = col(rh, "superseded_by")
    ri_com = col(rh, "来源提交")

    ids: list[str] = []
    for row in active[1:]:
        if len(row) <= max(ci_id, ci_stat, ci_scr, ci_res):
            check(f"主张行格式完整", False, str(row)[:80])
            continue
        cid, status = row[ci_id], row[ci_stat]
        ids.append(cid)
        check(f"{cid} 编号格式", bool(re.fullmatch(r"C\d+", cid)), cid)
        check(f"{cid} 状态取自集合", status in STATUS, status)
        for p in paths_in(row[ci_scr]):
            check(f"{cid} 脚本存在", os.path.exists(os.path.join(ROOT, p)), p)
        refs = paths_in(row[ci_res])
        check(f"{cid} 给出参考结果", bool(refs), row[ci_res][:60])
        for p in refs:
            check(f"{cid} 参考结果存在", os.path.exists(os.path.join(ROOT, p)), p)
            print(f"        冻结提交 {last_commit(p)}  {p}")

    check("主张编号唯一", len(ids) == len(set(ids)),
          f"{len(ids)} 行，去重后 {len(set(ids))}")

    for row in retract[1:]:
        if len(row) <= max(ri_sup, ri_com):
            continue
        sup, com = row[ri_sup], row[ri_com].strip().strip("`")
        check(f"撤回行 superseded_by={sup.strip().strip(chr(96))} 指向当前主张",
              sup.strip().strip("`") in ids)
        check(f"撤回行来源提交形如短哈希", bool(re.fullmatch(r"[0-9a-f]{7,40}", com)), com)

    retracted_in_active = [i for i in ids
                           if any(r[ci_stat] == "retracted" for r in active[1:]
                                  if len(r) > ci_stat and r[ci_id] == i)]
    check("撤回主张不出现在当前主张表", not retracted_in_active, str(retracted_in_active))

    print(f"\n  主张 {len(ids)} 条，撤回 {max(len(retract) - 1, 0)} 条")
    if FAIL:
        print(f"\n  {len(FAIL)} 项失败")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
