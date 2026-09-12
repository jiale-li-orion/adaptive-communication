#!/usr/bin/env python3
"""
scorer.py — the service metric, computed outside the agent and never visible to it.

The question the paper asks is not whether a command was executed. It is whether a valid
monitoring sample arrived at the center in time. That question is answered from two records kept
outside any runtime:

  * what each node actually measured (the sampling schedule's output), and
  * what actually reached the center and when.

An agent that could read either record would be answering a different and easier question. The
whole execution problem exists because it can read neither: it sees what it was told, when it was
told, and nothing else. Keeping the ground truth in this module and out of the interface layer is
what makes the metric mean what it says, so `RunRecord` is assembled by the experiment runner and
handed to no runtime.

The main metric is the contract's TimelyCoverage: the weighted fraction of demands for which a
valid sample was taken inside the demand's window AND had arrived at the center by its deadline.
Both halves are required. A sample taken but never delivered fails the demand, and so does a
delivery of a sample taken before the window opened.

Reported separately, because an average over them hides the thing being measured:

  * normal, risk and critical-node demands;
  * the end-to-end denominator, which keeps permanently unreachable nodes in it, and beside it
    the physically-servable subset, which is the demands for which at least one uplink was heard
    during their lifetime. The two answer different questions and mixing them flatters every
    method equally;
  * auxiliary quantities the contract asks for: center-side age of information, longest gap,
    configuration mismatch time, spurious measurements, history completeness, radio energy and
    airtime, and the time an operation spent in an unknown state.

Deps: standard library plus this package.
"""
from __future__ import annotations

# --- module resolution -------------------------------------------------------
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime",
                                                     "experiments", "analysis"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
# -----------------------------------------------------------------------------

from dataclasses import dataclass, field

from task_generator import Task, PRIORITY_NORMAL, PRIORITY_RISK

# Weights are fixed before any run and sweepable. Equal weights are the nominal choice: a demand
# is a demand, and letting priority double as a weight would let a method that serves only risk
# windows score well while ordinary monitoring rots.
DEFAULT_WEIGHTS = {PRIORITY_NORMAL: 1.0, PRIORITY_RISK: 1.0}


@dataclass
class RunRecord:
    """The complete ground truth of one run. Assembled by the runner, handed to no runtime."""

    demands: list[Task]
    taken: list                     # Sample: every sample any node took
    arrived: list[tuple]            # (Sample, arrival_second): records that reached the center
    heard_uplinks: list[tuple]      # (node_id, second): uplinks the gateway actually heard
    node_ids: tuple[str, ...]
    durable_nodes: tuple[str, ...] = ()   # nodes that can hold a profile across a power loss
    radio_wh: dict = field(default_factory=dict)
    airtime_ms: float = 0.0
    config_mismatch_s: float = 0.0
    spurious_measurements: int = 0
    unknown_s: float = 0.0
    log_entries: int = 0


@dataclass
class ScoreResult:
    coverage: float
    covered: int
    demands: int
    by_class: dict
    servable: dict
    aux: dict

    def as_dict(self) -> dict:
        return {"coverage": self.coverage, "covered": self.covered, "demands": self.demands,
                "by_class": self.by_class, "servable": self.servable, "aux": self.aux}


def _covered_by(demand: Task, taken_index: dict, arrived_index: dict) -> bool:
    """A demand is met when one sample satisfies BOTH halves of the contract.

    Taken inside the window, and arrived by the deadline. Either half alone is not service: a
    sample taken in the window but still sitting in a node's buffer at the deadline did not
    inform anyone, and a record delivered on time that was measured before the window opened
    describes a moment the demand did not ask about.
    """
    window_start, window_end = demand.sample_window
    for node_id in demand.node_set:
        for sample in taken_index.get((node_id, demand.measurement_type), ()):
            if not window_start <= sample.taken_at <= window_end:
                continue
            arrival = arrived_index.get(sample.sample_id)
            if arrival is not None and arrival <= demand.delivery_deadline:
                return True
    return False


def _index(taken, arrived):
    taken_index: dict[tuple[str, str], list] = {}
    for sample in taken:
        taken_index.setdefault((sample.node_id, sample.measurement_type), []).append(sample)
    arrived_index = {sample.sample_id: arrival for sample, arrival in arrived}
    return taken_index, arrived_index


def _physically_servable(demand: Task, heard_by_node: dict) -> bool:
    """Whether any of the demand's nodes was heard at all during the demand's lifetime.

    This is the line between "the runtime failed to deliver" and "the deployment offered no
    opportunity". Keeping the two apart is why the servable subset is reported beside the
    end-to-end figure rather than instead of it: the end-to-end number is what an operator
    experiences, and the subset is what a runtime can be held responsible for.

    A-layer definition: servable means at least one uplink from one of the demand's nodes reached
    the gateway between release and deadline. A stricter reading would require the sample itself
    to have been taken in that window, which would credit a node for opportunities it never used.
    """
    for node_id in demand.node_set:
        for second in heard_by_node.get(node_id, ()):
            if demand.release_time <= second <= demand.delivery_deadline:
                return True
    return False


def score(record: RunRecord, weights: dict | None = None) -> ScoreResult:
    weights = dict(DEFAULT_WEIGHTS if weights is None else weights)
    taken_index, arrived_index = _index(record.taken, record.arrived)

    heard_by_node: dict[str, list[int]] = {}
    for node_id, second in record.heard_uplinks:
        heard_by_node.setdefault(node_id, []).append(second)

    buckets = {
        "normal": {"w": 0.0, "hit": 0.0, "n": 0, "ok": 0},
        "risk": {"w": 0.0, "hit": 0.0, "n": 0, "ok": 0},
        "critical": {"w": 0.0, "hit": 0.0, "n": 0, "ok": 0},
    }
    total_w = hit_w = 0.0
    covered = 0
    servable_n = servable_ok = 0

    for demand in record.demands:
        met = _covered_by(demand, taken_index, arrived_index)
        weight = weights.get(demand.priority, 1.0)
        total_w += weight
        hit_w += weight if met else 0.0
        covered += int(met)

        klass = "risk" if demand.priority == PRIORITY_RISK else "normal"
        buckets[klass]["w"] += weight
        buckets[klass]["n"] += 1
        buckets[klass]["hit"] += weight if met else 0.0
        buckets[klass]["ok"] += int(met)

        critical = klass == "risk"
        if critical:
            buckets["critical"]["w"] += weight
            buckets["critical"]["n"] += 1
            buckets["critical"]["hit"] += weight if met else 0.0
            buckets["critical"]["ok"] += int(met)

        if _physically_servable(demand, heard_by_node):
            servable_n += 1
            servable_ok += int(met)

    by_class = {
        name: {"demands": b["n"], "covered": b["ok"],
               "coverage": (b["hit"] / b["w"]) if b["w"] else float("nan")}
        for name, b in buckets.items()
    }

    # History completeness: of the records the nodes took and would have kept, how many reached
    # the center at all. Independent of timing on purpose — a record that arrives late still
    # belongs in the archive, and a method that trades the archive for timeliness should show it.
    arrived_ids = set(arrived_index)
    archived = sum(1 for s in record.taken if s.sample_id in arrived_ids)

    aux = {
        "radio_wh": record.radio_wh,
        "airtime_ms": record.airtime_ms,
        "config_mismatch_s": record.config_mismatch_s,
        "spurious_measurements": record.spurious_measurements,
        "unknown_s": record.unknown_s,
        "log_entries": record.log_entries,
        "archive_completeness": (archived / len(record.taken)) if record.taken else float("nan"),
        "records_taken": len(record.taken),
        "records_arrived": len(arrived_index),
    }

    return ScoreResult(
        coverage=(hit_w / total_w) if total_w else float("nan"),
        covered=covered,
        demands=len(record.demands),
        by_class=by_class,
        servable={"demands": servable_n, "covered": servable_ok,
                  "coverage": (servable_ok / servable_n) if servable_n else float("nan")},
        aux=aux,
    )


def format_score(result: ScoreResult, label: str = "") -> str:
    lines = []
    if label:
        lines.append(f"{label}")
    lines.append(f"  按期有效监测覆盖率 {100 * result.coverage:6.1f}%  "
                 f"({result.covered}/{result.demands} 条需求)")
    lines.append(f"    常态 {100 * result.by_class['normal']['coverage']:6.1f}%  "
                 f"风险 {100 * result.by_class['risk']['coverage']:6.1f}%  "
                 f"关键节点 {100 * result.by_class['critical']['coverage']:6.1f}%")
    sv = result.servable
    lines.append(f"    物理可服务子集 {100 * sv['coverage']:6.1f}%  "
                 f"({sv['covered']}/{sv['demands']} 条)")
    aux = result.aux
    lines.append(f"    档案完整率 {100 * aux['archive_completeness']:5.1f}%   "
                 f"配置错配 {aux['config_mismatch_s'] / 60:7.1f} min   "
                 f"空口 {aux['airtime_ms'] / 3.6e6:6.2f} h")
    return "\n".join(lines)
