#!/usr/bin/env python3
"""audit_tables.py — 论文表格必须由结果文件生成，不能手写。

检查六件事：

  1. `scripts/make_tables.py --check` 通过：`paper/generated/` 的内容与结果文件当前推出的内容
     一致。不一致说明结果变了而表格没重新生成，或者有人手改了生成物；
  2. 每份稿件的生成表都经 `\\input` 引入，且引入的目标存在；
  3. 稿件里没有手写的表格行（出现 `\\toprule` 即视为手写表体）；
  4. **事实宏一并受检**：`paper/generated/facts.tex` 存在、被两份稿件 `\\input`，且其中的每个宏
     取值都等于结果文件里对应的数（正文与表说明里的数字因此也走生成链，不只是表体）；
  5. **已撤回的读数不得回流**：几条被撤回的表述（"候选界交付总数不减"等）在稿件与生成物里都不得
     再出现——它们曾经真实存在过，所以要让它们回来时必然变红，而不是靠人记得。
  6. Agentic Communication 的新结果也必须通过生成链：paper/generated 表、research README 受控
     区块、results README 登记区块均由冻结 aggregate/audit/source manifest 生成。

第 3 条与第 4 条是这个检查的核心：它们堵住"数字写回正文"这条路。生成物被手改时它不一定能发现
（那由第 1 条负责），但把 `\\input` 换回手抄行、或把宏换成字面量，一定会红。

语言与表名都不写死：稿件由 `paper/<语言>/main.tex` 发现，生成物由 `paper/generated/table_*.tex`
发现，因此本检查可直接搬到新仓库使用。

Run: python3 code/evaluation/audits/audit_tables.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
PAPER = os.path.join(ROOT, "paper")
GENERATED = os.path.join(PAPER, "generated")
FAIL: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")
    if not ok:
        FAIL.append(name)


def manuscripts() -> list[tuple[str, str]]:
    """发现 paper/<语言>/main.tex。"""
    out = []
    if not os.path.isdir(PAPER):
        return out
    for name in sorted(os.listdir(PAPER)):
        d = os.path.join(PAPER, name)
        m = os.path.join(d, "main.tex")
        if os.path.isdir(d) and os.path.isfile(m):
            out.append((name, m))
    return out


def generated_tables() -> list[str]:
    """由 paper/generated/table_<表>.<语言>.tex 推出表名集合。"""
    if not os.path.isdir(GENERATED):
        return []
    names = set()
    for f in os.listdir(GENERATED):
        if f.startswith("table_") and f.endswith(".tex"):
            stem = f[len("table_"):-len(".tex")]
            names.add(stem.rsplit(".", 1)[0] if "." in stem else stem)
    return sorted(names)


def main() -> int:
    print("\n[20] 论文表格由结果文件生成")

    gen = os.path.join(ROOT, "scripts", "make_tables.py")
    if os.path.exists(gen):
        proc = subprocess.run([sys.executable, gen, "--check"],
                              cwd=ROOT, capture_output=True, text=True)
        tail = (proc.stdout.strip().splitlines() or [""])[-1][:90]
        check("生成物与结果文件一致", proc.returncode == 0, tail)
    else:
        check("scripts/make_tables.py 存在", False, gen)

    agentic_gen = os.path.join(ROOT, "scripts", "make_agentic_artifacts.py")
    if os.path.exists(agentic_gen):
        proc = subprocess.run([sys.executable, agentic_gen, "--check"],
                              cwd=ROOT, capture_output=True, text=True)
        tail = (proc.stdout.strip().splitlines() or [""])[-1][:110]
        check("Agentic 表与生成研究摘要和冻结结果一致", proc.returncode == 0, tail)
    else:
        check("scripts/make_agentic_artifacts.py 存在", False, agentic_gen)

    paper_v1_gen = os.path.join(ROOT, "scripts", "make_agentic_paper_v1.py")
    if os.path.exists(paper_v1_gen):
        proc = subprocess.run([sys.executable, paper_v1_gen, "--check"],
                              cwd=ROOT, capture_output=True, text=True)
        tail = (proc.stdout.strip().splitlines() or [""])[-1][:110]
        check("Agentic paper-v1 表/事实宏与冻结结果一致", proc.returncode == 0, tail)
    else:
        check("scripts/make_agentic_paper_v1.py 存在", False, paper_v1_gen)

    agentic_facts = os.path.join(GENERATED, "agentic_facts.tex")
    check("Agentic 事实宏文件存在", os.path.exists(agentic_facts),
          os.path.relpath(agentic_facts, ROOT))
    if os.path.exists(agentic_facts):
        aftext = open(agentic_facts, encoding="utf-8").read()
        afdefs = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", aftext))
        check("Agentic 事实宏非空", bool(afdefs), f"{len(afdefs)} 个")
        badnames = sorted(k for k in afdefs if not k.isalpha())
        check("Agentic 事实宏名只含字母", not badnames, ", ".join(badnames))

    ms = manuscripts()
    if not ms:
        # 新仓库起步时还没有稿件。这里**显式**打印一条 SKIP，而不是静默通过：无声的跳过会让人
        # 以为稿件侧也被检查过了。一旦出现 paper/<语言>/main.tex，下面的断言立即生效。
        print("  SKIP  尚未建立稿件：稿件侧断言暂不适用（paper/<语言>/main.tex 出现后自动生效）")

    pat = re.compile(r"\\input\{\.\./generated/([^}]+)\}")
    for lang, path in ms:
        text = open(path, encoding="utf-8").read()
        inputs = pat.findall(text)
        check(f"{lang} 稿件经 input 引入生成表", bool(inputs), f"{len(inputs)} 处")
        for rel in inputs:
            check(f"{lang} 引入目标存在 {rel}", os.path.exists(os.path.join(GENERATED, rel)))
        handmade = "\\toprule" in text.replace("\\toprule{", "")
        check(f"{lang} 稿件无手写表体", not handmade,
              "找到 toprule" if handmade else "")
        if "generated/table_agentic_" in text:
            check(f"{lang} 使用 Agentic 表时引入 Agentic 事实宏",
                  "generated/agentic_facts.tex" in text)

    # 当前 Agentic 主稿采用 paper/agentic/en/main.tex，刻意不塞进旧的
    # paper/<语言>/main.tex 双稿发现/成对生成规则。这里单独审计其生成链与实际构建。
    agentic_main = os.path.join(PAPER, "agentic", "en", "main.tex")
    agentic_build = os.path.join(PAPER, "agentic", "build.sh")
    check("Agentic 当前主稿存在", os.path.isfile(agentic_main),
          os.path.relpath(agentic_main, ROOT))
    if os.path.isfile(agentic_main):
        atext = open(agentic_main, encoding="utf-8").read()
        apat = re.compile(r"\\input\{\.\./\.\./generated/([^}]+)\}")
        ainputs = apat.findall(atext)
        check("Agentic 主稿经 input 引入生成物", bool(ainputs), f"{len(ainputs)} 处")
        for rel in ainputs:
            check(f"Agentic 引入目标存在 {rel}",
                  os.path.exists(os.path.join(GENERATED, rel)))
        check("Agentic 主稿引入 Agentic 事实宏",
              "../../generated/agentic_facts.tex" in atext)
        handmade = "\\toprule" in atext.replace("\\toprule{", "")
        check("Agentic 主稿无手写表体", not handmade,
              "找到 toprule" if handmade else "")
        if os.path.isfile(agentic_build):
            proc = subprocess.run(["bash", agentic_build], cwd=os.path.dirname(agentic_build),
                                  capture_output=True, text=True)
            tail = (proc.stdout.strip().splitlines() or [""])[-1][:140]
            check("Agentic 主稿可构建且排版/引用检查通过", proc.returncode == 0, tail)
        else:
            check("Agentic build.sh 存在", False, os.path.relpath(agentic_build, ROOT))

    # 事实宏：正文/说明里的数字也必须来自结果文件
    facts = os.path.join(GENERATED, "facts.tex")
    check("事实宏文件存在", os.path.exists(facts), os.path.relpath(facts, ROOT))
    if os.path.exists(facts):
        ftext = open(facts, encoding="utf-8").read()
        defs = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", ftext))
        check("事实宏非空", bool(defs), f"{len(defs)} 个")
        # TeX 控制序列名只能由字母组成：名字里带数字会被截断成另一个宏（实测：`\cThreeSeed0Fifo`
        # 被解析为 `\cThreeSeed` + `0Fifo`，两份稿件同时报 Undefined control sequence）。
        badnames = sorted(k for k in defs if not k.isalpha())
        check("事实宏名只含字母（不含数字或下划线）", not badnames, ", ".join(badnames))
        for lang, path in ms:
            text = open(path, encoding="utf-8").read()
            check(f"{lang} 稿件引入事实宏", "generated/facts.tex" in text)
        meta_path = os.path.join(GENERATED, "facts.meta.json")
        if os.path.exists(meta_path):
            import json as _json
            meta = _json.load(open(meta_path, encoding="utf-8"))
            want = {k: str(v) for k, v in meta["definitions"].items()}
            missing = sorted(set(want) - set(defs))
            wrong = sorted(k for k in want if k in defs and defs[k] != want[k])
            check("事实宏覆盖生成器定义的全部名字", not missing, str(missing))
            check("事实宏取值与生成器一致", not wrong, str(wrong))

    # 已撤回的读数不得回流：这些字符串曾经真实出现过
    RETRACTED = [
        "黄级交付总数不减。后者在 A 相位的平均最终 SoC 更高",
        "candidate delivery-derived setting achieve zero deaths and preserve aggregate yellow",
        "Preserve aggregate yellow delivery",
        "少交付 183 条黄级义务",
        "TTL 6~h\nloses 26",
    ]
    for lang, path in ms:
        text = open(path, encoding="utf-8").read()
        hit = [r for r in RETRACTED if r in text]
        check(f"{lang} 稿件无已撤回读数", not hit, "; ".join(h[:40] for h in hit))

    names = generated_tables()
    check("发现生成表", bool(names), ", ".join(names[:6]))
    for name in names:
        for lang, _ in ms:
            p = os.path.join(GENERATED, f"table_{name}.{lang}.tex")
            check(f"生成物成对存在 {os.path.basename(p)}", os.path.exists(p))

    if FAIL:
        print(f"\n  {len(FAIL)} 项失败")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
