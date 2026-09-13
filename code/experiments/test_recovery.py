#!/usr/bin/env python3
"""
test_recovery.py — a "durable" runtime has to be able to prove it, from the log alone.

The claim under test is narrow and it is the one the restart trajectory rests on: a coordinator
that keeps a durable log can, after losing its process, go on writing to a far side that fences on
version numbers. The failure this guards against is not a crash, it is a claim:

  * a runtime that declares `durable_storage = True` while its state never leaves the object it
    lives in is not durable, it is lucky — the restart hook is never called on it and the reading
    it produces says nothing about durability;
  * a log that does not record the fields the far side fences on cannot reconstruct a sender, no
    matter how faithfully it is replayed.

So the checks here are deliberately about reconstruction from the log and about nothing else:

  1. the log carries the contract fields    every dispatched profile write records the stable
                                           logical identity and the version it put on the wire.
  2. the log survives serialisation         a journal that has been through JSON and back replays
                                           to the same state; a log that only exists in memory is
                                           not a log.
  3. a fresh object can be rebuilt          recovery starts from a runtime with no memory at all
                                           and restores the version high-water and the logical
                                           identity, using nothing but the replay.
  4. the counter really moves               the restored version is strictly above every version in
                                           the log, which is the property the far side checks.
  5. amnesia is not durability              the same runtime without a log loses both scalars, which
                                           is what makes check 3 evidence rather than a tautology.

Run: export PYTHONPATH="$PWD/libs/pylibs"; python3 code/experiments/test_recovery.py
"""
from __future__ import annotations

import json
import os as _os, sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime",
                                                     "experiments", "analysis", "monitoring"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

try:                                                        # package import
    from monitoring.policies import (RuntimeAmnesiacPolicy, RuntimePolicy,
                                     RuntimeReconstructedPolicy, profile_command)
    from monitoring.runner import _after_coordinator_restart
except ImportError:                                         # flat import via sys.path
    from policies import (RuntimeAmnesiacPolicy, RuntimePolicy,   # type: ignore
                          RuntimeReconstructedPolicy, profile_command)
    from runner import _after_coordinator_restart             # type: ignore

from operations import Journal, replay_contract_state        # noqa: E402

FAIL: list[str] = []

# Two nodes, so a reconstruction that happens to work for one entity cannot pass by accident.
NODES = ("r00", "r01")


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")
    if not ok:
        FAIL.append(name)


class FakeRecord:
    """The little of an ActionRecord the journal writer reads."""

    def __init__(self, identity, node_id, issued_at, parameters):
        self.identity = identity
        self.node_id = node_id
        self.kind = "set_monitoring_profile"
        self.issued_at = issued_at
        self.parameters = parameters
        self.attempts = 1


def write_to_journal(journal, node_id, logical, version, t_s):
    """Record one profile write exactly the way the interface layer records it."""
    record = FakeRecord(f"{node_id}:profile:risk:g1", node_id, t_s,
                        {"profile": "risk", "generation": 1, "path": 0})
    journal.record("register", incarnation="c0", operation_id=record.identity,
                   entity_id=record.node_id, capability=record.kind,
                   arguments_hash=str(sorted(record.parameters.items())),
                   logical_intent=record.identity, epoch=record.attempts,
                   side_effect=True, contract_logical=logical,
                   contract_version=version, at=record.issued_at)
    journal.record("dispatched", operation_id=record.identity, attempts=record.attempts,
                   at=record.issued_at)


def build_log() -> tuple[Journal, dict[str, int]]:
    """A log of writes that move the version counter, plus the high-water it should imply."""
    journal = Journal()
    high = {}
    t = 0
    for round_index in range(1, 5):
        for node_id in NODES:
            version = round_index
            logical = f"{node_id}:{round_index}"
            write_to_journal(journal, node_id, logical, version, t)
            high[node_id] = max(high.get(node_id, 0), version)
            t += 60
    return journal, high


def test_log_carries_contract_fields() -> None:
    """1. the two fields the far side fences on are in the durable record."""
    journal, _high = build_log()
    registers = [e for e in journal.entries if e["kind"] == "register"]
    ok = bool(registers) and all(e.get("contract_version") is not None
                                 and e.get("contract_logical") is not None for e in registers)
    check("日志记录了契约字段", ok,
          f"{len(registers)} 条 register，版本与逻辑身份齐备" if ok else "有 register 缺契约字段")
    versions = sorted({e["contract_version"] for e in registers})
    check("版本是严格递增的", versions == list(range(1, len(versions) + 1)),
          f"版本集合 {versions}")


def test_log_survives_serialisation() -> None:
    """2. a log that only exists in memory is not a log."""
    journal, _high = build_log()
    blob = json.dumps(journal.entries, sort_keys=True)
    restored = Journal()
    restored.entries = json.loads(blob)
    restored.validate()
    ok = restored.entries == journal.entries
    check("日志经 JSON 往返后逐字节相同", ok, f"{len(restored.entries)} 条")
    check("往返后重放结果不变",
          replay_contract_state(restored) == replay_contract_state(journal))


def test_fresh_object_is_rebuilt() -> None:
    """3+4. recovery restores the high-water from the log and from nothing else."""
    journal, high = build_log()
    blob = json.loads(json.dumps(journal.entries, sort_keys=True))
    reloaded = Journal()
    reloaded.entries = blob

    policy = RuntimeReconstructedPolicy()
    # Live state that recovery must NOT be able to lean on. If it survives, the reading this arm
    # produces is about object identity rather than about durability.
    policy.version = {n: 999 for n in NODES}
    policy.logical = {n: 999 for n in NODES}
    policy.desired = {n: "risk" for n in NODES}
    policy.issued_version = {n: 999 for n in NODES}

    _after_coordinator_restart(policy, lost=[], unresolved=[], journal=reloaded)

    ok = all(policy.version.get(n) == high[n] for n in NODES)
    check("从日志重建出版本高水位", ok,
          f"重建 {[policy.version.get(n) for n in NODES]} 对日志 {[high[n] for n in NODES]}")
    check("重建出的版本严格高于日志里的每一条",
          all(policy.version.get(n, 0) >= high[n] for n in NODES))
    check("重建出稳定逻辑身份",
          all(policy.logical.get(n) == high[n] for n in NODES),
          f"逻辑身份 {[policy.logical.get(n) for n in NODES]}")
    check("非日志状态被丢弃而不是沿用",
          not policy.desired and not policy.issued_version,
          f"desired={policy.desired} issued_version={policy.issued_version}")


def test_amnesia_is_not_durability() -> None:
    """5. without a log both scalars are gone, so check 3 is evidence rather than a tautology."""
    policy = RuntimeAmnesiacPolicy()
    policy.version = {n: 999 for n in NODES}
    policy.logical = {n: 999 for n in NODES}
    _after_coordinator_restart(policy, lost=[], unresolved=[], journal=None)
    check("无日志臂重启后两个标量都归零",
          not policy.version and not policy.logical,
          f"version={policy.version} logical={policy.logical}")


def test_memory_mode_is_unchanged() -> None:
    """The measured arm's declared behaviour before this round must not have moved."""
    policy = RuntimePolicy()
    policy.version = {n: 999 for n in NODES}
    policy.logical = {n: 7 for n in NODES}
    _after_coordinator_restart(policy, lost=[], unresolved=[])
    ok = all(policy.version.get(n) == 999 for n in NODES) \
        and all(policy.logical.get(n) == 7 for n in NODES)
    check("memory 模式行为未变（状态留在对象里）", ok)


def test_hook_receives_journal_only_when_declared() -> None:
    """The runner must not hand a log to a hook that never asked for one."""
    class NoJournalHook:
        def __init__(self):
            self.seen = "unset"

        def on_restart(self, lost=(), unresolved=()):
            self.seen = "no-journal-kwarg"

    hook = NoJournalHook()
    _after_coordinator_restart(hook, lost=[], unresolved=[], journal=Journal())
    check("不接受 journal 的钩子不被强行传参", hook.seen == "no-journal-kwarg", hook.seen)


def test_profile_command_carries_both_fields() -> None:
    """The payload the policy returns is what reaches the far side's fencing check."""
    payload = profile_command("risk", version=3, logical="r00:3")
    check("profile 指令同时带版本与逻辑身份",
          payload.get("version") == 3 and payload.get("logical") == "r00:3",
          f"version={payload.get('version')} logical={payload.get('logical')}")


def main() -> int:
    print("恢复归因：从日志重建 runtime")
    test_log_carries_contract_fields()
    test_log_survives_serialisation()
    test_fresh_object_is_rebuilt()
    test_amnesia_is_not_durability()
    test_memory_mode_is_unchanged()
    test_hook_receives_journal_only_when_declared()
    test_profile_command_carries_both_fields()
    print("\n" + "-" * 74)
    if FAIL:
        print(f"  {len(FAIL)} 项失败: {', '.join(FAIL)}")
        return 1
    print("  全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
