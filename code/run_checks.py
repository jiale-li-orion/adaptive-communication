#!/usr/bin/env python3
"""
run_checks.py — one entry point for every check in the repository.

The repository has no CI pipeline, so this is what a pipeline would call. Running it is also how a
human answers "is the tree healthy" without remembering eleven file names and their order.

Each check is a standalone script that prints PASS/FAIL lines and exits non-zero on failure. This
runner does not parse their output; it reports exit codes, because a check that fails silently
while printing confident lines is exactly the failure mode these files exist to prevent.

Two groups, because they answer different questions:

  mechanism   the execution-semantics layer and the frozen mechanism-isolation experiment. These
              back the numbers in README section six and must stay reproducible.
  monitoring  the business-loop simulator built for the paper contract. These back the readings in
              README section seven.

Run: python3 code/run_checks.py [--group mechanism|monitoring|all] [--quiet]
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

CHECKS = {
    "mechanism": [
        ("runtime/operations.py", "执行语义自检：三维正交、五条不变量、三条性质"),
        ("experiments/test_failure_model.py", "11 类故障可复现"),
        ("experiments/test_draw_keys.py", "报文级随机契约"),
        ("experiments/test_journal_schema.py", "持久日志 schema 与字段集校验"),
        ("experiments/audit_consistency.py", "一致性审计：README 与结果文件逐行对齐"),
    ],
    "monitoring": [
        ("experiments/test_energy_model.py", "能量模型手工核算"),
        ("experiments/test_opportunity.py", "控制面机会模型与机会上界"),
        ("experiments/test_node_model.py", "采样/缓存/上传链逐事件对齐"),
        ("experiments/test_task_generator.py", "外生需求生成器"),
        ("experiments/test_scorer.py", "评分器与真值边界"),
        ("experiments/test_interfaces.py", "四接口与可审计证据"),
        ("experiments/test_llm_planner.py", "LLM 规划器、决策校验与调用账目"),
        ("experiments/test_supply.py", "供电模型与可达性耦合"),
        ("experiments/test_faults.py", "六类诊断故障注入"),
        ("experiments/test_policies.py", "强基线：版本化配置与 VTC 风格恢复"),
        ("experiments/test_recovery.py", "恢复归因：从日志重建 runtime 的两个标量"),
        ("experiments/test_instance.py", "实例层验收：Task v1.1 最小闭环的手工可核算性质"),
        ("experiments/audit_fairness.py", "业务层公平性审计"),
    ],
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="all",
                    choices=["mechanism", "monitoring", "all"])
    ap.add_argument("--quiet", action="store_true", help="print only failures")
    args = ap.parse_args()

    groups = list(CHECKS) if args.group == "all" else [args.group]
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [os.path.join(ROOT, "libs", "pylibs"), env.get("PYTHONPATH", "")]).rstrip(os.pathsep)

    failed: list[str] = []
    total = 0
    for group in groups:
        if not args.quiet:
            print(f"\n=== {group} ===")
        for rel, what in CHECKS[group]:
            total += 1
            path = os.path.join(HERE, rel)
            if not os.path.exists(path):
                print(f"  MISSING  {rel}")
                failed.append(rel)
                continue
            proc = subprocess.run([sys.executable, path], cwd=ROOT, env=env,
                                  capture_output=True, text=True)
            ok = proc.returncode == 0
            if not ok:
                failed.append(rel)
            if not args.quiet or not ok:
                print(f"  {'PASS' if ok else 'FAIL'}  {rel:48s} {what}")
            if not ok and proc.stdout:
                tail = [ln for ln in proc.stdout.splitlines() if "FAIL" in ln][-6:]
                for ln in tail:
                    print(f"          {ln.strip()}")

    print("\n" + "-" * 74)
    if failed:
        print(f"  {len(failed)}/{total} 项失败：")
        for f in failed:
            print(f"    - {f}")
        return 1
    print(f"  {total}/{total} 项通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
