#!/usr/bin/env python3
"""
test_journal_schema.py — the durable log refuses what it cannot replay faithfully.

A journal that silently tolerates an entry it does not understand is worse than one that
refuses, because the recovered runtime is then wrong in a way nothing downstream can detect.
The log has usually been rotated away by the time anything unrelated fails.

Four things must be refused:

  1. an entry kind this build does not know
  2. an entry whose schema version this build does not replay
  3. an entry with a field the writer added and the reader does not know about
  4. an entry missing a field the reader requires

The third is the one that matters in practice: a write-side change that adds a field produces a
plausible-looking operation on replay, and nothing about it looks wrong.

Run: python3 code/experiments/test_journal_schema.py
"""
from __future__ import annotations

import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime",
                                                     "experiments", "analysis"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from operations import (Journal, JournalError, JOURNAL_SCHEMA, REGISTRY_KINDS,   # noqa: E402
                        DECISION_KINDS, DurableDecisionStore, OperationRegistry,
                        recover, Outcome, Observation)

FAIL: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")
    if not ok:
        FAIL.append(name)


def expect_error(name: str, fn) -> None:
    try:
        fn()
    except JournalError as e:
        check(name, True, str(e)[:78])
        return
    except Exception as e:                                   # noqa: BLE001
        check(name, False, f"抛出了 {type(e).__name__} 而非 JournalError: {e}")
        return
    check(name, False, "没有抛错")


def good_log() -> Journal:
    j = Journal()
    reg = OperationRegistry(j)
    store = DurableDecisionStore(j)
    op = reg.register("r03", "set_rate", {"rate": "5min"}, "r03:rate:7", 0, True)
    reg.dispatched(op, 1)
    reg.observe(op, Observation.UNKNOWN)
    reg.settle(op, Outcome.APPLIED, 2, "replied")
    store.commit("r03:adhoc:5", 987654)
    return j


def test_append_side() -> None:
    print("\n[1] 写入侧：未知 kind 与字段集不符都当场失败")
    expect_error("未知 kind 拒绝写入", lambda: Journal().record("invented", a=1))
    expect_error("多一个字段拒绝写入", lambda: Journal().record("observe", operation_id="x",
                                                                observation="fresh", extra=1))
    expect_error("少一个字段拒绝写入", lambda: Journal().record("observe", operation_id="x"))
    j = Journal()
    j.record("observe", operation_id="x", observation=Observation.FRESH.value)
    check("合法条目带上版本号", j.entries[0]["v"] == JOURNAL_SCHEMA["observe"][0],
          f"v={j.entries[0]['v']}")


def test_replay_side() -> None:
    print("\n[2] 重放侧：条目被改写后拒绝整条日志")
    j = good_log()
    check("完好日志通过校验", (j.validate() is None), f"{len(j)} 条")

    j2 = good_log()
    j2.entries[0] = {k: v for k, v in j2.entries[0].items() if k != "epoch"}
    expect_error("缺字段的条目被拒", j2.validate)

    j3 = good_log()
    j3.entries[0]["later_field"] = 1
    expect_error("多字段的条目被拒", j3.validate)

    j4 = good_log()
    j4.entries[0]["v"] = 99
    expect_error("版本不符被拒", j4.validate)

    j5 = good_log()
    j5.entries[0]["kind"] = "something_else"
    expect_error("未知 kind 被拒", j5.validate)


def test_recovery_refuses() -> None:
    print("\n[3] 恢复入口先校验，不给出一具「看似正常」的状态")
    j = good_log()
    reg = recover(j)
    check("完好日志可恢复", len(reg.ops) == 1)

    j2 = good_log()
    j2.entries[3]["outcome"] = "applied"          # a settle whose version was stripped
    del j2.entries[3]["v"]
    expect_error("recover 拒绝无法忠实重放的日志", lambda: recover(j2))

    j3 = good_log()
    j3.entries[-1]["value"] = 1                   # decision entry tampered
    del j3.entries[-1]["key"]
    expect_error("DurableDecisionStore.replay 同样拒绝",
                 lambda: DurableDecisionStore.replay(j3))


def test_two_families() -> None:
    print("\n[4] 两个条目族共处一条日志，版本彼此独立")
    j = good_log()
    kinds = [e["kind"] for e in j.entries]
    check("注册表条目与决策条目都在日志里",
          any(k in REGISTRY_KINDS for k in kinds) and any(k in DECISION_KINDS for k in kinds),
          str(kinds))
    check("两族的版本号可分别定义",
          all(isinstance(JOURNAL_SCHEMA[k][0], int) for k in REGISTRY_KINDS + DECISION_KINDS))
    store = DurableDecisionStore.replay(j)
    check("决策可由日志单独重建", store.recall("r03:adhoc:5") == 987654)
    reg = recover(j)
    op = next(iter(reg.ops.values()))
    check("操作状态同样由同一条日志重建",
          op.outcome is Outcome.APPLIED and op.observation is Observation.UNKNOWN)


def test_no_state_without_validation() -> None:
    print("\n[5] 任何恢复路径都先过校验")
    src = open(os.path.join(_CODE, "runtime", "operations.py"), encoding="utf-8").read()
    check("recover 在校验之后才构造注册表",
          src.index("journal.validate()") < src.index("return reg"))
    check("DurableDecisionStore.replay 也在构造前校验",
          "journal.validate()" in src[src.index("class DurableDecisionStore"):
                                      src.index("class RemoteSink")])


def main() -> int:
    print("持久日志 schema 回归测试")
    test_append_side()
    test_replay_side()
    test_recovery_refuses()
    test_two_families()
    test_no_state_without_validation()
    print("\n" + "-" * 74)
    if FAIL:
        print(f"  {len(FAIL)} 项失败：")
        for f in FAIL:
            print(f"    - {f}")
        return 1
    print("  全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
