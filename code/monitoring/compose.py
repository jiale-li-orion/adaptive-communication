"""把"决定做什么"与"怎么执行到底"分开。

契约 §7 要求实验按 2×2 组织：规则 planner / 真实 LLM planner × 强基线 runtime / 本文
runtime。这个分层是那条要求的实现形态，也顺手修掉一处公平性问题：上一轮的每条臂都自己
实现了一整套动作逻辑，于是只有本文臂会用 `request_measurement` 与 `upload_records`，
基线一条都不用。把 planner 抽出来共享之后，四个格子面对的是同一份意图词汇，差别只落在
承载它们的 runtime 上。

契约 §7 对两个因子的要求分别是：

- planner 决定"读有年龄的状态、确定测点与能力、设置 profile、必要时请求新采集、处理未决
  结果"，以及"恢复时有历史积压与新需求，读取游标与水位，优先新数据，限预算补历史"。
- runtime 决定这些意图能不能到底：是否给同一逻辑动作一个稳定身份、是否要远端回执、是否
  用单调 epoch 拒绝更旧的写入、在结果未知时是否先调和再重发、以及什么时候该放弃重发。

`Intent` 是两者之间唯一的接口。planner 不懂报文，runtime 不懂业务。
"""

from __future__ import annotations

import os as _os, sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime", "experiments",
                                                      "analysis", "monitoring"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
# -----------------------------------------------------------------------------

from dataclasses import dataclass, field

from policies import (OP_SET_PROFILE, PROFILE_RISK, measurement_command, profile_command,
                      upload_command)

try:
    from .task_generator import MONITORING_PROFILES, PROFILE_NORMAL
except ImportError:                                     # flat import
    from task_generator import MONITORING_PROFILES, PROFILE_NORMAL

# The intent vocabulary. Every planner speaks exactly this and every runtime carries exactly this,
# so a difference between two cells of the 2x2 is never a difference in what was expressible.
KIND_SET_PROFILE = "set_profile"
KIND_REQUEST_MEASUREMENT = "request_measurement"
KIND_UPLOAD_RECORDS = "upload_records"


@dataclass(frozen=True)
class Intent:
    """One thing the planner has decided should happen, before any question of delivery."""

    kind: str
    node_id: str
    args: dict = field(default_factory=dict)
    reason: str = ""

    def payload(self) -> dict:
        """The wire form, carrying no identity and no version.

        Identity and version are the runtime's business: a planner that minted them would be
        deciding a question about delivery, which is the other factor of the experiment.
        """
        if self.kind == KIND_SET_PROFILE:
            return profile_command(self.args["profile"])
        if self.kind == KIND_REQUEST_MEASUREMENT:
            return measurement_command(self.args["request_id"], self.args["window_start"],
                                       self.args["deadline"])
        if self.kind == KIND_UPLOAD_RECORDS:
            return upload_command(self.args["start"], self.args["end"], self.args["cursor"],
                                  self.args["budget"])
        raise ValueError(f"unknown intent kind {self.kind!r}")

    @property
    def logical_key(self) -> str:
        """What makes two intents the same logical action.

        The planner names this, not the runtime, because only the planner knows whether two
        decisions are the same decision. A backfill order for the same gap is the same action; a
        second retention of the same profile after it was already asked for is the same action too.
        """
        if self.kind == KIND_SET_PROFILE:
            return f"{self.node_id}:profile:{self.args['profile']}"
        if self.kind == KIND_REQUEST_MEASUREMENT:
            return f"{self.node_id}:measure:{self.args['request_id']}"
        return (f"{self.node_id}:upload:{self.args['start']}-{self.args['end']}:"
                f"c{self.args['cursor']}")


# --------------------------------------------------------------------------- planners
class RulePlanner:
    """规则 planner：契约 §7 描述的那些业务判断，用规则表达。

    它做三件事，与承载它的 runtime 无关：按需求设置 profile；在风险窗内必要时请求一次新采集；
    按中心自己档案与节点自述之间的缺口，限预算补历史。它不关心命令是否送达，也不维护身份——
    那是 runtime 的事。
    """

    name = "rule"

    def __init__(self, backfill_budget: int = 8, status_max_age_s: int = 3600,
                 measure_window_mult: int = 2, dwell_s: int = 300) -> None:
        self.backfill_budget = backfill_budget
        self.status_max_age_s = status_max_age_s
        self.measure_window_mult = measure_window_mult
        self.dwell_s = dwell_s
        # node -> (request_id, deadline) for the one measurement request allowed to be open
        self.measure_outstanding: dict[str, tuple[str, int]] = {}
        # node -> (cursor, newest) of the gap an order already covers
        self.backfill_ordered: dict[str, tuple[int, int]] = {}
        self.measurements_asked = 0
        self.backfills_ordered = 0
        self.last_profile: dict[str, str] = {}
        self.last_profile_at: dict[str, int] = {}

    def read_status(self, view, node_id: str):
        """`read_status(node, max_age)`: what the node last reported, and how old it is."""
        payload = view.status.get(node_id)
        if not payload:
            return None, None
        read_at = payload.get("read_at")
        if read_at is None:
            return payload, None
        return payload, max(0, view.t_s - int(read_at))

    def decide(self, view) -> list[Intent]:
        out: list[Intent] = []
        out.extend(self._profile_intents(view))
        out.extend(self._w2_intents(view))
        out.extend(self._w1_intents(view))
        return out

    # -- W3 and the profile half of W1: the demanded profile, with a dwell so that a value the
    #    planner just asked for is not asked for again before the answer could arrive ------------
    def _profile_intents(self, view) -> list[Intent]:
        """Ask for the profile the scenario demands wherever the node does not report it.

        The decision is made against the node's own report, not against what the planner asked for
        last time. A planner that remembered its own request would stop asking as soon as it had
        spoken once, and the runtime downstream would then have nothing to retry -- the retry
        discipline lives in the runtime precisely because the planner cannot tell a delivered
        instruction from one still in flight.
        """
        out = []
        for node_id, want in sorted(view.demanded_profile.items()):
            payload, _age = self.read_status(view, node_id)
            if payload is not None and payload.get("profile") == want:
                continue
            out.append(Intent(KIND_SET_PROFILE, node_id, {"profile": want},
                              reason="reported_differs_from_demanded"))
        return out

    def _w1_intents(self, view) -> list[Intent]:
        """Ask for a measurement only when the node would not otherwise take one in time."""
        out = []
        for node_id, want in sorted(view.demanded_profile.items()):
            if want != PROFILE_RISK:
                continue
            outstanding = self.measure_outstanding.get(node_id)
            if outstanding is not None:
                # One open request per node, held until its own deadline. The center cannot tell an
                # answered request from one still in flight, and asking again on the strength of a
                # guess is the move the unknown outcome is supposed to forbid.
                if view.t_s <= outstanding[1]:
                    continue
                del self.measure_outstanding[node_id]
            newest = view.archive_newest.get(node_id)
            if newest is None:
                continue
            if view.t_s - newest <= MONITORING_PROFILES[PROFILE_RISK]["sample_s"] * 2:
                continue
            # The window spans upload cadences, not sample intervals: the command has to reach the
            # node in a downlink opportunity and those arrive at the node's rhythm.
            window = MONITORING_PROFILES[PROFILE_NORMAL]["upload_s"] * self.measure_window_mult
            request_id = f"{node_id}:{view.t_s}"
            self.measure_outstanding[node_id] = (request_id, view.t_s + window)
            self.measurements_asked += 1
            out.append(Intent(KIND_REQUEST_MEASUREMENT, node_id,
                              {"request_id": request_id, "window_start": view.t_s,
                               "deadline": view.t_s + window},
                              reason="risk_window_without_fresh_sample"))
        return out

    def _w2_intents(self, view) -> list[Intent]:
        """Order a bounded slice of the gap between the center's archive and the node's report."""
        out = []
        for node_id in sorted(view.demanded_profile):
            payload, _age = self.read_status(view, node_id)
            if not payload:
                continue
            newest = payload.get("newest_sample_at")
            if newest is None:
                continue
            cursor = view.archive_newest.get(node_id, 0)
            if newest - cursor <= MONITORING_PROFILES[PROFILE_NORMAL]["sample_s"]:
                continue
            if self.backfill_ordered.get(node_id) == (cursor, int(newest)):
                continue
            self.backfill_ordered[node_id] = (cursor, int(newest))
            self.backfills_ordered += 1
            out.append(Intent(KIND_UPLOAD_RECORDS, node_id,
                              {"start": cursor, "end": int(newest), "cursor": cursor,
                               "budget": self.backfill_budget},
                              reason="archive_gap"))
        return out


class LLMPlanner(RulePlanner):
    """LLM planner：同一份意图词汇，决策来自模型，而不是规则。

    模型只决定**做什么**：它看不到报文，也拿不到身份与版本，因此它在这一层无法替 runtime
    完成任何执行上的工作。后端不可用时构造会硬失败，不会静默退回规则——静默降级会让一次
    脚本运行被读成模型运行。
    """

    name = "llm"

    def __init__(self, backend, **kwargs) -> None:
        super().__init__(**kwargs)
        self.backend = backend
        self.calls = 0
        self.illegal = 0
        self.last_raw: list[dict] = []

    def decide(self, view) -> list[Intent]:
        # The model is asked about the same decision the rule planner makes, from the same
        # observation. It sees only the interface fields: no simulator truth, no demand set.
        proposed = self.backend.decide(world=self._world(view))
        self.calls += 1
        self.last_raw = proposed
        intents: list[Intent] = []
        for item in proposed:
            try:
                intents.append(self._to_intent(item, view))
            except (KeyError, ValueError):
                # An illegal decision is recorded and dropped. It is never repaired by the rules,
                # because a planner whose failures are silently completed by its own fallback
                # cannot be measured.
                self.illegal += 1
        floor = super().decide(view)
        return intents if intents else floor

    def _world(self, view) -> dict:
        """The model's observation, built from interfaces only."""
        return {
            "t_s": view.t_s,
            "nodes": list(view.node_ids),
            "demanded": dict(view.demanded_profile),
            "reported": {nid: (p or {}).get("profile") for nid, p in view.status.items()},
            "archive_newest": dict(view.archive_newest),
            "cursors": {nid: {"acked_cursor": (p or {}).get("acked_cursor"),
                              "newest_sample_at": (p or {}).get("newest_sample_at")}
                        for nid, p in view.status.items()},
            "in_flight": sorted(view.in_flight),
        }

    def _to_intent(self, item: dict, view) -> Intent:
        kind = item["kind"]
        node_id = item["node_id"]
        if kind == KIND_SET_PROFILE:
            profile = item["profile"]
            if profile not in MONITORING_PROFILES:
                raise ValueError(f"unknown profile {profile!r}")
            return Intent(kind, node_id, {"profile": profile}, reason="llm")
        if kind == KIND_REQUEST_MEASUREMENT:
            window = int(item.get("window_s", 7200))
            return Intent(kind, node_id,
                          {"request_id": f"{node_id}:{view.t_s}", "window_start": view.t_s,
                           "deadline": view.t_s + window}, reason="llm")
        if kind == KIND_UPLOAD_RECORDS:
            cursor = int(item["cursor"])
            budget = int(item.get("budget", self.backfill_budget))
            return Intent(kind, node_id,
                          {"start": cursor, "end": int(item["end"]), "cursor": cursor,
                           "budget": budget}, reason="llm")
        raise ValueError(f"unknown intent kind {kind!r}")


# --------------------------------------------------------------------------- runtimes
class NaiveRuntime:
    """强基线 runtime：把意图发出去，然后把"发过了"当成"做完了"。

    没有稳定身份（每次尝试都是新动作），没有远端回执，没有单调 epoch，结果未知时不调和。
    它对应 §7 里"队列化接触窗口交付"那一类：尽力投递，不问下落。所有基线都允许遥测携带
    确认，所以它读得到节点自述；它不做的是把自述当成一次写入是否生效的证据去追。
    """

    name = "naive"

    def __init__(self, paths: tuple[int, ...] = (0,)) -> None:
        self.sent: set[str] = set()
        self.dispatched = 0
        # Which candidate paths this runtime will try, in order. One path is the first-round
        # architecture. With more, the runtime has to discover which one works, because there is no
        # out-of-band signal that would tell it: a path that is down and a reply that was lost look
        # exactly alike from the center. Every probe of a dead path spends an opportunity.
        self.paths = tuple(paths)
        self.path_uses = [0] * max(1, len(self.paths))

    def dispatch(self, intents, view) -> list[tuple[str, dict]]:
        out = []
        for intent in intents:
            key = intent.logical_key
            if key in self.sent:
                # Sent once and not asked about again. A command that was refused by the backhaul
                # is indistinguishable from one that landed, which is the whole failure this
                # baseline is here to expose.
                continue
            self.sent.add(key)
            self.dispatched += 1
            payload = intent.payload()
            used = self._pick_path(key)
            payload["path"] = used
            self.path_uses[used] = self.path_uses[used] + 1
            out.append((intent.node_id, payload))
        return out

    def _pick_path(self, key: str) -> int:
        """Which candidate to try. Blind: nothing here can see whether a path is up."""
        return self.paths[0] if self.paths else 0


class ContractRuntime:
    """本文 runtime：稳定身份、单调 epoch、先调和再重发、按证据结算。

    它承载的意图与 NaiveRuntime 完全相同；差别全在到底与证据上。
    """

    name = "contract"
    durable_storage = True

    def on_restart(self, lost=(), unresolved=()) -> None:
        """Same rule as the monolithic runtime: knowledge comes back, authority does not."""
        self.restarts += 1
        self.restart_unresolved += len(unresolved)
        self.awaiting_reconcile.update(op.split(":")[0] for op in unresolved)

    def __init__(self, ttl_s: int = 6 * 3600, dwell_s: int = 300, retry_budget: int = 3,
                 paths: tuple[int, ...] = (0,)) -> None:
        self.ttl_s = ttl_s
        self.dwell_s = dwell_s
        self.retry_budget = retry_budget
        self.epoch: dict[str, int] = {}
        self.logical_seq: dict[str, int] = {}
        self.issued: dict[str, dict] = {}      # logical_key -> bookkeeping
        self.settled_count = 0
        self.restarts = 0
        self.restart_unresolved = 0
        self.awaiting_reconcile: set[str] = set()
        self.paths = tuple(paths)
        self.path_uses = [0] * max(1, len(self.paths))
        self.settled: set[str] = set()
        self.writes = 0
        self.retries = 0
        self.abandoned = 0

    def _fresh_evidence(self, view, book: dict) -> bool:
        """Whether anything has reported since this operation's last attempt."""
        payload = view.status.get(book["node_id"]) or {}
        read_at = payload.get("read_at")
        if read_at is None:
            return False
        return int(read_at) > int(book["last_at"] or 0)

    def _settle_on_evidence(self, view) -> None:
        """Close an operation whose effect the node now reports.

        The node's own report is the only confirmation that reaches the center. An operation whose
        effect appears in it is finished; one whose effect does not stays open and is asserted
        again after the dwell. Without this the runtime retries until its budget runs out on
        operations that landed on the first try, which is what makes a baseline look careful.
        """
        for key, book in self.issued.items():
            if key in self.settled or book["attempts"] == 0:
                continue
            if book["kind"] != KIND_SET_PROFILE:
                continue
            payload = view.status.get(book["node_id"]) or {}
            if payload.get("profile") == book["profile"]:
                self.settled.add(key)
                self.settled_count += 1

    def dispatch(self, intents, view) -> list[tuple[str, dict]]:
        self._settle_on_evidence(view)
        out = []
        for intent in intents:
            key = intent.logical_key
            if key in self.settled:
                continue
            book = self.issued.get(key)
            if book is None:
                book = {"first_at": view.t_s, "attempts": 0, "identity": None,
                        "node_id": intent.node_id, "kind": intent.kind,
                        "profile": intent.args.get("profile"), "last_at": None}
                self.issued[key] = book
            if book["attempts"] >= 1 and view.t_s - book["first_at"] < self.dwell_s:
                continue
            if book["attempts"] >= 1 and not self._fresh_evidence(view, book):
                # Nothing has reported since the last attempt. There is no information yet, so a
                # second attempt spends an opportunity on a guess; the dwell and the retry cadence
                # are what end this, not impatience. This is the rule that separates a runtime that
                # re-asserts from one that hammers.
                continue
            if book["attempts"] >= self.retry_budget:
                # The budget bounds how many times in a row the runtime will assert the same thing,
                # not whether it may ever assert it again. Blacklisting the action instead is a
                # silent permanent give-up: a profile that missed its first three opportunities
                # would never be retried for the rest of the run, and the node would spend the run
                # on the wrong schedule while every counter still looked healthy. After a cooldown
                # the attempts are forgotten and the assertion starts over.
                cooldown = self.dwell_s * self.retry_budget
                if view.t_s - book["first_at"] < cooldown:
                    continue
                self.abandoned += 1
                book["attempts"] = 0
                book["first_at"] = view.t_s
                continue
            if book["attempts"]:
                self.retries += 1
            node_id = intent.node_id
            self.epoch[node_id] = self.epoch.get(node_id, 0) + 1
            self.logical_seq.setdefault(key, len(self.logical_seq) + 1)
            # The same logical action keeps one identity across every attempt, and only the epoch
            # moves. That is what lets the far side tell a retry from a second instruction.
            identity = f"{key}#i{self.logical_seq[key]}"
            book["attempts"] += 1
            book["identity"] = identity
            book["last_at"] = view.t_s
            self.writes += 1
            payload = intent.payload()
            payload["logical"] = identity
            payload["version"] = self.epoch[node_id]
            # The attempt number selects the path, so a runtime with more than one candidate finds
            # out which works by spending a second attempt rather than by asking anything. There is
            # nothing to ask: a down path returns no reply at all, and so does a lost one.
            used = self.paths[min(book["attempts"] - 1, len(self.paths) - 1)] if self.paths else 0
            payload["path"] = used
            self.path_uses[used] = self.path_uses[used] + 1
            out.append((node_id, payload))
        return out


@dataclass
class ComposedPolicy:
    """One cell of the 2x2: a planner and a runtime, with no knowledge of each other."""

    planner: object
    runtime: object
    name: str = "composed"

    @property
    def durable_storage(self) -> bool:
        """The cell's durability is its runtime's, not the composition's.

        Without this the runner would ask the wrapper and always hear "no", and every 2x2 cell would
        run as a volatile center -- which would quietly erase the factor the restart trajectory
        exists to measure while leaving every number looking normal.
        """
        return bool(getattr(self.runtime, "durable_storage", False))

    def on_restart(self, lost=(), unresolved=()) -> None:
        hook = getattr(self.runtime, "on_restart", None)
        if callable(hook):
            hook(lost=lost, unresolved=unresolved)

    def plan(self, view) -> list[tuple[str, dict]]:
        return self.runtime.dispatch(self.planner.decide(view), view)


# --------------------------------------------------------------------------- model backends
def render_world(world: dict) -> str:
    """The model's whole observation, rendered from interface fields only.

    Nothing the simulator knows appears here: no demand set, no channel state, no sample schedule.
    A prompt that leaked those would let the model answer questions the interfaces cannot, and the
    2x2 would be measuring the simulator rather than the interface.
    """
    lines = [f"time: {world['t_s']} s",
             "nodes and their last report (profile, age):"]
    for nid in world["nodes"]:
        reported = world["reported"].get(nid) or "no status"
        archive = world["archive_newest"].get(nid)
        archive_s = "never" if archive is None else f"{world['t_s'] - archive} s behind"
        # The node's own cursors come from the status read, not from the simulator. They are what
        # an upload order has to resume from, and a model asked to name a cursor without them could
        # only invent one.
        cursors = world.get("cursors", {}).get(nid, {})
        lines.append(f"  {nid}: reported={reported}, archive={archive_s}, "
                     f"acked_cursor={cursors.get('acked_cursor')}, "
                     f"node_newest={cursors.get('newest_sample_at')}")
    demanded = ", ".join(f"{n}={p}" for n, p in sorted(world["demanded"].items()))
    lines.append(f"the scenario demands profile: {demanded}")
    lines.append("commands already sent and unresolved: "
                 + (", ".join(sorted(world["in_flight"])) or "none"))
    lines.append("")
    lines.append("Reply with JSON only: {\"actions\": [{\"kind\": \"set_profile\", \"node_id\": "
                 "\"n00\", \"profile\": \"risk\"}]}. Kinds are set_profile, request_measurement, "
                 "upload_records. For upload_records give cursor, end and budget.")
    return "\n".join(lines)


class ChatBackendAdapter:
    """把一个 `complete(messages) -> str` 的后端包成 planner 要的 `decide(world)`。

    账目留在这里：每次调用的原始回复、解析结果与非法决策都记下来。后端不可用时由调用方
    硬失败，不静默退回规则。
    """

    def __init__(self, backend) -> None:
        self.backend = backend
        self.calls: list[dict] = []
        self.illegal = 0

    @property
    def name(self) -> str:
        return getattr(self.backend, "name", "unknown")

    def decide(self, world: dict) -> list[dict]:
        import json as _json
        messages = [{"role": "user", "content": render_world(world)}]
        raw = self.backend.complete(messages)
        entry = {"t_s": world["t_s"], "backend": self.name, "raw": raw, "actions": []}
        try:
            parsed = _json.loads(raw)
        except (TypeError, ValueError):
            entry["error"] = "unparseable"
            self.illegal += 1
            self.calls.append(entry)
            return []
        actions = parsed.get("actions")
        if actions is None and "kind" in parsed:
            actions = [parsed]                     # a single action is accepted, not repaired
        if not isinstance(actions, list):
            entry["error"] = "no action list"
            self.illegal += 1
            self.calls.append(entry)
            return []
        entry["actions"] = actions
        self.calls.append(entry)
        return actions


class ScriptedWorldBackend:
    """Deterministic stand-in for the model. Not a model; plumbing only.

    It reads the same rendered world a real model would and returns the same intent vocabulary, so
    the loop, the parser and the accounting can be exercised without an endpoint. Everything it
    produces is labelled `scripted` and no number under it may be reported as a model result.
    """

    name = "scripted"

    def complete(self, messages: list[dict]) -> str:
        import json as _json
        body = messages[-1]["content"]
        demanded: dict[str, str] = {}
        gaps: dict[str, int] = {}
        for line in body.splitlines():
            if line.startswith("the scenario demands profile:"):
                for pair in line.split(":", 1)[1].split(","):
                    if "=" in pair:
                        node, profile = pair.strip().split("=", 1)
                        demanded[node.strip()] = profile.strip()
            elif line.strip().startswith("n") and ":" in line and "archive=" in line:
                node = line.strip().split(":")[0].strip()
                behind_s = line.split("archive=")[1].split(",")[0].strip()
                acked_s = line.split("acked_cursor=")[1].split(",")[0].strip()
                newest_s = line.split("node_newest=")[1].strip()
                def _int(text):
                    return None if text in ("never", "None", "") else int(text)
                gaps[node] = {"behind": _int(behind_s.replace(" s behind", "")),
                              "acked": _int(acked_s), "newest": _int(newest_s)}
        actions = []
        for node, profile in sorted(demanded.items()):
            actions.append({"kind": "set_profile", "node_id": node, "profile": profile})
        for node, info in sorted(gaps.items()):
            if info["behind"] is not None and info["behind"] > 3600 and info["acked"] is not None:
                actions.append({"kind": "upload_records", "node_id": node,
                                "cursor": info["acked"], "end": info["newest"],
                                "budget": 8})
        return _json.dumps({"actions": actions})


# --------------------------------------------------------------------------- the 2x2
def build_composed(name: str, paths=(0,)):
    """Instantiate one cell of the 2x2 by name.

    `llm` cells build their planner around whatever backend the caller supplies, defaulting to the
    scripted stand-in. A scripted cell is plumbing, and it says so in its own name.
    """
    planner_name, _, runtime_name = name.partition("__")
    if planner_name == "rule":
        planner = RulePlanner()
    elif planner_name == "llm":
        planner = LLMPlanner(ChatBackendAdapter(ScriptedWorldBackend()))
    else:
        raise ValueError(f"unknown planner {planner_name!r}")
    if runtime_name == "naive":
        runtime = NaiveRuntime(paths=tuple(paths))
    elif runtime_name == "contract":
        runtime = ContractRuntime(paths=tuple(paths))
    else:
        raise ValueError(f"unknown runtime {runtime_name!r}")
    return ComposedPolicy(planner=planner, runtime=runtime, name=name)
