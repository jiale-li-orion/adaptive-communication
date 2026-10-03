#!/usr/bin/env python3
"""Guard the long-lived paper-repository authority structure.

This check exists because README rewrites are easy to make cosmetically cleaner while
accidentally deleting constraints that define the paper artifact: the active manuscript,
claim authority, experiment-design authority, immutable history, and the boundary between
the clean remote repository and author-local exploratory material.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[3]
FAIL: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")
    if not ok:
        FAIL.append(name)


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def git_show(spec: str) -> bytes:
    p = subprocess.run(
        ["git", "show", spec], cwd=ROOT, capture_output=True, timeout=30
    )
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode("utf-8", errors="replace"))
    return p.stdout


def main() -> int:
    print("\n[authority] repository entry points / immutable history")

    common_required = [
        "paper/agentic/en/main",
        "paper/_archive/system-paper-2026-09-20",
        "results/CLAIMS.md",
        "research/README.md",
        "research/substrate/SYSTEM-MODEL-v1.md",
        "research/compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md",
        "make agentic-preapi",
        "Operational Task",
        "Runtime TaskContract",
        "local_experiments",
    ]
    for rel in ("README.md", "README.zh.md"):
        text = read(rel)
        for token in common_required:
            check(f"{rel} 保留 authority token", token in text, token)
        check(
            f"{rel} 不把 CLAIMS 降级为历史账本",
            "historical experimental claim ledger" not in text
            and "只持有历史冻结实验主张" not in text,
        )
        check(
            f"{rel} 明示远端/本地研究区边界",
            "Remote repository versus local research zones" in text
            or "远端仓库与本地研究区" in text,
        )

    archive = ROOT / "paper" / "_archive" / "system-paper-2026-09-20"
    meta = (archive / "README.md").read_text(encoding="utf-8")
    for field in ("superseded_by:", "reason:", "source_commit:"):
        check("系统稿 archive metadata 完整", field in meta, field)
    check(
        "系统稿英文 archive 与 source_commit 字节一致",
        (archive / "main.en.tex").read_bytes()
        == git_show("dd4f31a:paper/en/main.tex"),
    )
    check(
        "系统稿中文 archive 与 source_commit 字节一致",
        (archive / "main.zh.tex").read_bytes()
        == git_show("dd4f31a:paper/zh/main.tex"),
    )

    claims = read("results/CLAIMS.md")
    check("CLAIMS 保留 C* namespace", "| C1 |" in claims)
    check("CLAIMS 保留 A* namespace", "| A1 |" in claims)
    check("CLAIMS 明示 sole authority", "唯一 claim-state authority" in claims)

    compat_root = (ROOT / "local_research" / "archive" / "compat").resolve()
    for rel in ("docs", "local_experiments"):
        path = ROOT / rel
        check(f"{rel}/ 是 compatibility symlink", path.is_symlink())
        if path.is_symlink():
            resolved = path.resolve()
            try:
                resolved.relative_to(compat_root)
                under_compat = True
            except ValueError:
                under_compat = False
            check(
                f"{rel}/ 解析到 local_research/archive/compat",
                under_compat,
                str(resolved),
            )
        tracked = subprocess.run(
            ["git", "ls-files", rel], cwd=ROOT, capture_output=True, text=True, timeout=20
        ).stdout.strip()
        check(f"{rel}/ 不进入远端 tracked tree", tracked == "", tracked[:120])

    if FAIL:
        print(f"\n  {len(FAIL)} 项 authority 检查失败")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
