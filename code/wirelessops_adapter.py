#!/usr/bin/env python3
"""
wirelessops_adapter.py — WirelessOpsBench task contracts under a disrupted execution layer.

Inherited from WirelessOpsBench (public development split, arXiv 2608.08277):
  * the task contract: family, question, public_input, budgets, legal_transitions, milestones
  * the nine-tool interface and its mutates_state flags
  * the authorization lifecycle: stage -> validate -> commit -> post_check -> rollback

Supplied here, because the public package withholds it:
  * the runtime that executes the contract
  * the evidence ledger the read-only tools serve
  * the CQI provider, which is an ASSUMED-layer substitute (the package ships no ray_tracing
    implementation and no evidence content; see docs/s5-benchmark/s6-10-wirelessopsbench-artifact-audit.md)

Measured here: execution assurance — after a mutation is dispatched, how many times did it
actually land. Task correctness is deliberately NOT re-scored: the public package withholds its
scoring predicates, so re-scoring would mean inventing the benchmark's own answer key.

Deps: numpy only (same as disruption_env).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import statistics as st

from disruption_env import TOOLS as ENV_TOOLS, DisruptionEnv, Node
from operations import MAY_HAVE_EFFECT

HERE = os.path.dirname(os.path.abspath(__file__))
ARTIFACT = os.environ.get(
    "WIRELESSOPS_ARTIFACT",
    os.path.normpath(os.path.join(
        HERE, "..", "other_repo", "wirelessopsbench-artifact-D969", "extracted",
        "WirelessOpsBench-public-development-1d6004f4f809a5d4")),
)

# ---------------------------------------------------------------- tool contract
# The nine public tools. side_effect governs whether the sink dedups the write; it mirrors the
# benchmark's own mutates_state flag, where ONLY commit_policy and rollback_policy are True.
BENCH_TOOLS = {
    "get_primary_evidence":   {"class": "read_only", "side_effect": False},
    "get_secondary_evidence": {"class": "read_only", "side_effect": False},
    "get_entity":             {"class": "read_only", "side_effect": False},
    "get_schema":             {"class": "read_only", "side_effect": False},
    "post_check":             {"class": "read_only", "side_effect": False},
    "stage_policy":           {"class": "state_mut", "side_effect": False},
    "validate_policy":        {"class": "state_mut", "side_effect": False},
    "commit_policy":          {"class": "side_effect", "side_effect": True},
    "rollback_policy":        {"class": "side_effect", "side_effect": True},
}
ENV_TOOLS.update(BENCH_TOOLS)

MUTATING = ("commit_policy", "rollback_policy")

# The 2x2 under test. Identity: does a retry reuse the logical write's key? Verification: does
# the policy ask the entity whether the write landed, and is the question scoped to THIS write?
STABLE_IDENTITY = ("lifecycle", "stable_key_only")
VERIFIES = ("lifecycle", "verified_wrapper")
POLICIES = ("naive", "stable_key_only", "verified_wrapper", "lifecycle")


# ------------------------------------------------------------------------- task
class BenchTask:
    """One public development case and the base contract it projects."""

    def __init__(self, base: dict, case: dict):
        self.base_id = base["base_task_id"]
        self.case_id = case["case_id"]
        self.family = base["family"]
        self.question = base["public_question"]
        self.params = base["public_input"]
        self.budgets = base["budgets"]
        self.legal = list(base["legal_transitions"])
        self.milestones = list(base["milestones"])
        self.profile = base["execution_profile"]
        self.tools = list(self.profile["public_tools"])
        # the entity named by the refresh_then_validate transition, if any
        self.entity = next((t.split(":", 1)[1] for t in self.legal
                            if t.startswith("refresh_then_validate:")), f"{self.family.lower()}-entity")
        self.risk_field = (self.profile["action_schemas"]["stage_policy"]
                           ["proposal_constraints"]["risk_field"])
        self.max_impact = (self.profile["action_schemas"]["stage_policy"]
                           ["proposal_constraints"]["maximum_protected_impact"])
        self.rounds_required = (self.profile["action_schemas"]["validate_policy"]
                                ["evidence_rounds_required"])

    def __repr__(self) -> str:
        return f"<{self.family} {self.case_id[:14]}… entity={self.entity}>"


def load_tasks(families=("WCNS", "WCMSA"), limit=None) -> list[BenchTask]:
    bases = {}
    for f in glob.glob(f"{ARTIFACT}/development/bases/*.json"):
        b = json.load(open(f))
        if b["family"] in families:
            bases[b["base_task_id"]] = b
    cases = {}
    for f in glob.glob(f"{ARTIFACT}/development/cases/*.json"):
        c = json.load(open(f))
        # one case per base: the clean case is not distinguishable publicly, so take the first
        cases.setdefault(c["base_task_id"], c)
    out = [BenchTask(bases[k], cases[k]) for k in sorted(bases) if k in cases]
    return out[:limit] if limit else out


# ------------------------------------------------------------------- cqi layer
class CQIProvider:
    """ASSUMED layer. The package ships no ray_tracing implementation and no CQI values.

    CQI is drawn once per task from a seeded RNG and then held fixed, so that task correctness is
    deterministic and the only moving part in the experiment is the execution layer.
    """

    def __init__(self, seed: int):
        import numpy as np
        self._rng = np.random.default_rng(seed)
        self._cache: dict[str, int] = {}

    def cqi(self, key: str) -> int:
        if key not in self._cache:
            self._cache[key] = int(self._rng.integers(4, 16))
        return self._cache[key]


# ---------------------------------------------------------------------- ledger
class EvidenceLedger:
    """The evaluator-private evidence content, reconstructed minimally.

    The public package exposes no evidence payloads, so the ledger is synthesized with the field
    names the repairs' event records use (entity / payload / source / status / version /
    metadata.issued_at / metadata.state_version).
    """

    def __init__(self, task: BenchTask, cqi: int, tick: int = 0):
        self.task = task
        self.version = 1
        self.cqi = cqi
        self.issued_at = tick
        self.primary = {
            "entity": task.entity,
            "source": "primary",
            "status": "ok",
            "version": self.version,
            "metadata": {"issued_at": tick, "state_version": self.version},
            "payload": {task.risk_field: 0, "cqi": cqi,
                        "slice_capacity_mhz": 90 if task.family == "WCNS" else 30},
        }
        self.secondary = {
            "entity": task.entity,
            "source": "secondary",
            "status": "ok",
            "version": self.version,
            "metadata": {"issued_at": tick, "state_version": self.version},
            "payload": {task.risk_field: 0, "cqi": cqi},
        }

    def read(self, tool: str, tick: int, fresh: bool = True):
        if tool == "get_primary_evidence":
            return dict(self.primary)
        if tool == "get_secondary_evidence":
            return dict(self.secondary)
        if tool == "get_entity":
            return {"entity": self.task.entity, "state_version": self.version}
        if tool == "get_schema":
            return {"risk_field": self.task.risk_field, "max": self.task.max_impact}
        return {}


# -------------------------------------------------------------------- adapter
class WirelessOpsAdapter:
    """Drives one task contract over a link that loses, duplicates and forgets operations."""

    def __init__(self, task: BenchTask, seed: int = 0, policy: str = "lifecycle",
                 channel: str = "ge", ticks: int = 240, rounds: int = 1):
        self.task = task
        self.policy = policy
        self.rounds_requested = max(1, rounds)
        # entities become nodes on real terrain; three roles are enough to express the contract
        self.env = DisruptionEnv(seed=seed, n_nodes=3, ticks=ticks, channel=channel)
        self.roles = ["target", "protected", "gateway"]
        self.node_of = {r: self.env.nodes[i] for i, r in enumerate(self.roles) if i < len(self.env.nodes)}
        self.cqi = CQIProvider(seed).cqi(task.case_id)
        self.ledger = EvidenceLedger(task, self.cqi)
        self.stage_id: str | None = None
        self.staged_impact: int | None = None
        self.rounds = 0
        self.validated = False
        self.committed_version: int | None = None
        self.milestones: set[str] = set()
        self.violations: list[str] = []
        self._anon = 0
        self._last_op: str | None = None
        self.log: list[tuple] = []
        # the operational cycle index: a monitoring mission repeats the same contract
        self.cycle = 0
        self.cycles_settled: list[str] = []
        self.cycles_landed: list[int] = []
        self._cycle_intent: str = ""
        self.verify_unknown = 0

    # ------------------------------------------------------------ observation
    def read_tool(self, tool: str, fresh: bool = True):
        payload = self.ledger.read(tool, self.env.t, fresh)
        self.log.append((self.env.t, "read", tool, fresh))
        return payload

    # --------------------------------------------------------------- staging
    def stage_policy(self, proposal: dict) -> str:
        self.stage_id = f"stage-{self.task.case_id[:12]}-{len(self.log)}"
        self.staged_impact = proposal.get(self.task.risk_field)
        if self.staged_impact is None or self.staged_impact > self.task.max_impact:
            self.violations.append("dangerous_proposal")
        self.log.append((self.env.t, "stage", self.stage_id, self.staged_impact))
        return self.stage_id

    def validate_policy(self, stage_id: str) -> bool:
        if stage_id != self.stage_id:
            self.violations.append("validate_unknown_stage")
            return False
        self.rounds += 1
        if self.rounds < self.task.rounds_required:
            return False
        self.validated = True
        self.milestones.add("evidence_checked")
        self.log.append((self.env.t, "validate", stage_id, self.rounds))
        return True

    # ------------------------------------------------- mutation over the link
    def _intent(self, tool: str) -> str:
        """The logical identity of the write.

        The cycle index is part of the key on purpose: one cycle is one logical write, so retries
        within a cycle must collapse at the sink while the next cycle must genuinely apply again.
        Whether the identity is STABLE across retries is one of the two mechanisms under test.
        """
        if self.policy in STABLE_IDENTITY:
            # stable across retries -> the idempotent sink dedups the repeat
            return f"key:{self.task.case_id[:12]}:{self.task.entity}:{tool}:c{self.cycle}"
        self._anon += 1
        # a fresh identity per attempt -> every retry is a NEW write at the sink
        return f"anon-{self._anon}"

    def dispatch_mutation(self, tool: str, intent: str, **args) -> str:
        if tool not in MUTATING:
            raise ValueError(tool)
        if tool == "commit_policy":
            if not self.validated or args.get("stage_id") != self.stage_id:
                self.violations.append("commit_before_validate")
            self.committed_version = args.get("expected_version")
        node = self.node_of.get("target", self.env.nodes[0])
        self._last_op = self.env.dispatch(node, tool, intent=intent)
        self.log.append((self.env.t, "dispatch", tool, self._last_op))
        return self._last_op

    def poll(self, op_id: str):
        state, payload = self.env.poll(op_id)
        self.log.append((self.env.t, "poll", op_id, state))
        return state, payload

    def post_check(self) -> str:
        """Ask the entity whether THIS cycle's write landed.

        Cycle-scoped on purpose. The unscoped question -- "was commit_policy ever applied
        here" -- is answered yes by an EARLIER cycle's write, and a policy that believes it
        skips the cycle it is actually verifying. The query crosses the same lossy channel,
        so "unknown" is a real answer and the policy has to handle it.
        """
        node = self.node_of["target"]
        res = self.env.verify_intent(node, self._cycle_intent)
        self.log.append((self.env.t, "post_check", self._cycle_intent, res))
        if res == "applied":
            self.milestones.add("policy_committed")
            self.milestones.add("post_checked")
        elif res == "unknown":
            self.verify_unknown += 1
        return res

    def post_check_unscoped(self) -> str:
        """The published verified-wrapper predicate: "was commit_policy applied on this entity?"

        This is what the verification-before-retry wrapper of arXiv 2608.02645 asks. Under a
        repeated operational horizon the question is answered YES by an EARLIER cycle's write,
        so the wrapper concludes the current write is done and stops. It is not a strawman: the
        predicate is correct for a single one-shot episode, which is the setting it was
        published in.
        """
        node = self.node_of["target"]
        res = self.env.verify(node, "commit_policy")
        self.log.append((self.env.t, "verify_unscoped", node.nid, res))
        if res == "unknown":
            self.verify_unknown += 1
        return res

    # ------------------------------------------------------------------ run
    def _landed(self) -> int:
        """Writes of a mutating tool that actually landed on the target, so far."""
        nid = self.node_of["target"].nid
        return len([a for a in self.env.truth.applied if a[1] == nid and a[2] in MUTATING])

    def run(self) -> dict:
        """One episode: drive the same contract for `rounds` operational cycles.

        One cycle intends exactly one logical write. Duplicates are therefore counted exactly,
        as writes that landed minus cycles that were driven -- no inference from the trace.
        """
        self.read_tool("get_primary_evidence")
        self.read_tool("get_secondary_evidence")
        self.read_tool("get_entity")
        self.read_tool("get_schema")

        for c in range(self.rounds_requested):
            if self.env.t >= self.env.ticks:
                break
            self.cycle = c
            self.stage_id = None
            self.validated = False
            self.rounds = 0
            before = self._landed()
            stage = self.stage_policy({"response": {}, self.task.risk_field: 0})
            for _ in range(max(1, self.task.rounds_required)):
                if self.validate_policy(stage):
                    break
            settled = self._drive_commit(stage)
            self.cycles_settled.append(settled)
            self.cycles_landed.append(self._landed() - before)
        self.post_check()
        return self._metrics()

    def _drive_commit(self, stage: str) -> str:
        """Push one cycle's commit to a settled outcome, retrying per the policy."""
        version = 1 + self.cycle
        # one logical write per cycle: every attempt inside the cycle reuses this identity
        self._cycle_intent = self._intent("commit_policy")
        op = self.dispatch_mutation("commit_policy", self._cycle_intent,
                                    stage_id=stage, expected_version=version)
        budget = 3
        attempts = 0
        while self.env.t < self.env.ticks:
            self.env.tick()
            state, _ = self.poll(op)
            if state == "committed":
                return "committed"
            if state in ("outcome_unknown", "timeout"):
                attempts += 1
                if attempts >= budget:
                    return "budget_exhausted"
                if self.policy == "lifecycle":
                    # scoped question, stable key
                    if self.post_check() == "applied":
                        return "reconciled"
                elif self.policy == "verified_wrapper":
                    # unscoped question, fresh key: the published wrapper's combination
                    if self.post_check_unscoped() == "applied":
                        return "verified_done"
                # anything unresolved -> retry. Under a stable key the sink dedups it, so a
                # retry that turns out to be unnecessary is harmless; under a fresh key it is
                # a second write.
                op = self.dispatch_mutation("commit_policy", self._cycle_intent,
                                            stage_id=stage, expected_version=version)
            elif state == "running":
                first = self.env.registry.ops[op].first_dispatch or 0
                if (self.env.t - first) > 48:
                    return "unresolved"
        return "unresolved"

    def _metrics(self) -> dict:
        truth = self.env.truth
        landed = self.cycles_landed
        dup = sum(max(0, n - 1) for n in landed)
        lost = sum(1 for n in landed if n == 0)
        return {
            "case": self.task.case_id[:14],
            "family": self.task.family,
            "policy": self.policy,
            "cycles": len(landed),
            "settled": dict((s, self.cycles_settled.count(s)) for s in set(self.cycles_settled)),
            "applied": sum(landed),
            "duplicates": dup,
            "lost_cycles": lost,
            "deduped_at_sink": getattr(truth, "deduped", 0),
            "verify_unknown": self.verify_unknown,
            "unresolved_ops": len([o for o in self.env.registry.ops.values()
                                   if o.open and o.side_effect]),
            "may_have_effect": len([o for o in self.env.registry.ops.values()
                                    if o.state in MAY_HAVE_EFFECT and o.side_effect]),
            "milestones": len(self.milestones),
            "violations": ";".join(sorted(set(self.violations))),
        }


# --------------------------------------------------------------------- driver
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=30, help="number of public tasks to drive")
    ap.add_argument("--channel", default="ge", choices=["iid", "ge"])
    ap.add_argument("--ticks", type=int, default=600)
    ap.add_argument("--rounds", default="1,8,32", help="operational horizon(s) to sweep")
    ap.add_argument("--families", default="WCNS,WCMSA")
    args = ap.parse_args()

    fams = tuple(args.families.split(","))
    tasks = load_tasks(fams, args.limit)
    horizons = [int(x) for x in args.rounds.split(",")]

    print(f"artifact : {ARTIFACT}")
    print(f"tasks    : {len(tasks)}  families={fams}  channel={args.channel}  ticks={args.ticks}")
    print()

    hdr = (f"{'rounds':>6s} {'policy':10s} {'cycles':>7s} {'dup':>7s} {'dup/1k':>8s} "
           f"{'lost':>6s} {'lost/1k':>8s} {'dedup':>7s} {'vunk':>6s} {'unres':>6s} {'viol':>5s}")
    print(hdr)
    print("-" * len(hdr))

    rows = []
    for R in horizons:
        for pol in POLICIES:
            sub = []
            for i, t in enumerate(tasks):
                ad = WirelessOpsAdapter(t, seed=1000 + i, policy=pol, channel=args.channel,
                                        ticks=args.ticks, rounds=R)
                sub.append(ad.run())
            cyc = sum(r["cycles"] for r in sub)
            dup = sum(r["duplicates"] for r in sub)
            lost = sum(r["lost_cycles"] for r in sub)
            dedup = sum(r["deduped_at_sink"] for r in sub)
            vunk = sum(r["verify_unknown"] for r in sub)
            unres = sum(r["unresolved_ops"] for r in sub)
            vio = sum(1 for r in sub if r["violations"])
            print(f"{R:6d} {pol:10s} {cyc:7d} {dup:7d} {1000*dup/max(1,cyc):8.1f} "
                  f"{lost:6d} {1000*lost/max(1,cyc):8.1f} {dedup:7d} {vunk:6d} {unres:6d} {vio:5d}")
            rows.append({"rounds": R, "policy": pol, "cycles": cyc, "dup": dup,
                         "lost": lost, "dedup": dedup, "vunk": vunk, "unres": unres, "viol": vio,
                         "settled": _merge_settled(sub)})
        print()

    print("settled 分布（cycle 计数）:")
    for r in rows:
        print(f"  rounds={r['rounds']:3d} {r['policy']:10s} {r['settled']}")

    print()
    print("同一 horizon 下 lifecycle 相对 naive 的变化:")
    for R in horizons:
        a = next(r for r in rows if r["rounds"] == R and r["policy"] == "naive")
        b = next(r for r in rows if r["rounds"] == R and r["policy"] == "lifecycle")
        rd = (1 - b["dup"] / a["dup"]) if a["dup"] else float("nan")
        rl = (1 - b["lost"] / a["lost"]) if a["lost"] else float("nan")
        print(f"  rounds={R:3d}  重复副作用 {a['dup']:5d} -> {b['dup']:5d}"
              f" ({-100*rd:+6.1f}%)   零效果 cycle {a['lost']:5d} -> {b['lost']:5d}"
              f" ({-100*rl:+6.1f}%)")


def _merge_settled(sub: list[dict]) -> dict:
    out: dict[str, int] = {}
    for r in sub:
        for k, v in r["settled"].items():
            out[k] = out.get(k, 0) + v
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


if __name__ == "__main__":
    main()
