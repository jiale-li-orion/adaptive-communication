#!/usr/bin/env python3
"""
llm_planner.py — a planner that asks a model what to do, and records what it was told.

The contract requires that a real model take part in the loop, not merely that a prompt exists:
the model receives the task, the node capabilities and the aged evidence, and returns actions with
parameters, then continues from whatever came back. This module is that seam, and it is deliberately
thin — it builds the message, parses the decision, validates it against the action set, and hands the
result to the runner as an ordinary policy.

WHAT THE MODEL MAY SEE is the same `WorldView` a rule-based policy gets, rendered to text: the
instant, the nodes, the profile the scenario demands, and for each node whatever a status read
actually returned. It does not see the demand list, the sample schedule, or what arrived. A planner
that could read those would be solving a different problem, and the leak check in the scorer's
regression file exists to keep the boundary from eroding.

EVERY CALL IS RECORDED, including the ones that fail. The contract asks for calls, latency, tokens,
illegal parameters and the feedback loop, because a planner that emits unparseable decisions and is
quietly rescued by a fallback is not a planner — it is a rule engine with a model-shaped ornament.
`PlannerLog` keeps the raw text alongside the parsed result so that claim can be checked.

CREDENTIALS. A real call needs an endpoint and a key. When either is missing this module says so and
offers a scripted backend instead. The scripted backend is labelled `scripted` everywhere it appears
and its results are plumbing evidence only: it is not a model, and no number it produces may be
reported as an LLM result.

Deps: standard library plus this package. The real backend needs the `openai` client, imported
lazily so the rest of the layer runs without it.
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

import json
import os
import time
from dataclasses import dataclass, field

from task_generator import MONITORING_PROFILES, PROFILE_NORMAL

# The action set the model is allowed to choose from. It matches the center's four interfaces; a
# decision naming anything else is rejected and recorded as an illegal parameter rather than being
# silently dropped.
ACTIONS = ("set_monitoring_profile", "read_status", "do_nothing")

SYSTEM_PROMPT = (
    "You coordinate a pre-disaster mountain monitoring network. Nodes are LoRaWAN Class A: a node "
    "can only receive a downlink inside the short window it opens after one of its own uplinks, so "
    "every command you send costs a scarce opportunity and may not arrive at all.\n"
    "You are told which monitoring profile the scenario demands. Your job is to bring the nodes to "
    "that profile.\n"
    "Reply with one JSON object and nothing else:\n"
    '{"thought": "<one sentence>", "action": "<one of: '
    + ", ".join(ACTIONS) + '>", "args": {...}}\n'
    'For set_monitoring_profile: {"node": "<id>", "profile": "<normal|risk|low_power>"}.\n'
    'For read_status: {"node": "<id>"}.\n'
    'For do_nothing: {}.'
)


@dataclass
class PlannerCall:
    """One model call, parsed or not. Kept raw so the parse failure rate is auditable."""

    at_s: int
    prompt_chars: int
    raw: str
    parsed: dict | None
    error: str | None
    latency_s: float
    backend: str


@dataclass
class PlannerLog:
    calls: list[PlannerCall] = field(default_factory=list)

    @property
    def illegal(self) -> int:
        return sum(1 for c in self.calls if c.error is not None)

    @property
    def parse_rate(self) -> float:
        if not self.calls:
            return float("nan")
        return 1.0 - self.illegal / len(self.calls)

    def summary(self) -> dict:
        return {"backend": self.calls[0].backend if self.calls else None,
                "calls": len(self.calls), "illegal": self.illegal,
                "parse_rate": self.parse_rate,
                "mean_latency_s": (sum(c.latency_s for c in self.calls) / len(self.calls)
                                   if self.calls else float("nan"))}


def render(view) -> str:
    """The decision prompt for one instant. Only what the WorldView carries reaches the model."""
    lines = [f"t = {view.t_s} s ({view.t_s / 3600.0:.2f} h)"]
    if view.center_has_announcement and view.demanded_profile:
        wanted = sorted(set(view.demanded_profile.values()))
        lines.append(f"the scenario demands profile: {', '.join(wanted)}")
    else:
        lines.append("no change is demanded; keep the nodes on their normal profile")
    lines.append(f"profiles available: {', '.join(sorted(MONITORING_PROFILES))}")
    lines.append("nodes:")
    for nid in view.node_ids:
        st = view.status.get(nid)
        if st is None:
            lines.append(f"  {nid}: no status has ever been read")
        else:
            lines.append(f"  {nid}: profile={st.get('profile')} "
                         f"buffer={st.get('buffer_level')} "
                         f"reported_at={st.get('read_at')}s "
                         f"session={st.get('session_id', 'unknown')}")
    if view.in_flight:
        lines.append(f"commands already sent and unconfirmed: {', '.join(sorted(view.in_flight))}")
    lines.append("Reply with the single JSON object.")
    return "\n".join(lines)


def parse_decision(text: str):
    """Parse and validate one decision. Returns (decision, None) or (None, error)."""
    try:
        obj = json.loads(text.strip())
    except Exception as e:                                    # noqa: BLE001
        return None, f"not JSON: {type(e).__name__}"
    if not isinstance(obj, dict):
        return None, "not a JSON object"
    action = obj.get("action")
    if action not in ACTIONS:
        return None, f"unknown action {action!r}"
    args = obj.get("args") or {}
    if not isinstance(args, dict):
        return None, "args is not an object"
    if action == "set_monitoring_profile":
        if not isinstance(args.get("node"), str):
            return None, "missing node"
        if args.get("profile") not in MONITORING_PROFILES:
            return None, f"unknown profile {args.get('profile')!r}"
    if action == "read_status" and not isinstance(args.get("node"), str):
        return None, "missing node"
    return {"action": action, "args": args, "thought": obj.get("thought", "")}, None


class ScriptedBackend:
    """A deterministic stand-in with the model's interface. Not a model; plumbing only.

    It exists so the loop, the prompt rendering, the parser and the accounting can be exercised
    without an endpoint. Every place it appears it is labelled `scripted`, and no number produced
    under it may be reported as a model result.
    """

    name = "scripted"

    def complete(self, messages: list[dict]) -> str:
        body = messages[-1]["content"]
        wanted = "normal"
        for line in body.splitlines():
            if line.startswith("the scenario demands profile:"):
                wanted = line.split(":", 1)[1].split(",")[0].strip()
        nodes, never_read = [], []
        for line in body.splitlines():
            if line.startswith("  ") and ":" in line:
                parts = line.strip().split(":")
                if parts[0].startswith("n"):
                    nodes.append(parts[0])
                    if "no status" in line:
                        never_read.append(parts[0])
        in_flight = []
        for line in body.splitlines():
            if line.startswith("commands already sent"):
                in_flight = [x.strip() for x in line.split(":", 1)[1].split(",") if x.strip()]
        target = next((n for n in nodes if n not in in_flight), None)
        if target is None:
            return json.dumps({"thought": "nothing to send", "action": "do_nothing", "args": {}})
        return json.dumps({"thought": f"bring {target} to {wanted}",
                           "action": "set_monitoring_profile",
                           "args": {"node": target, "profile": wanted}})


def make_real_backend(model: str | None = None, base_url: str | None = None,
                      api_key: str | None = None, timeout: float = 30.0):
    """A real OpenAI-compatible backend, or (None, reason) when it cannot be built or reached.

    The reachability probe is a real request, not a check for the presence of an environment
    variable: an endpoint that answers 401 is not usable, and reporting it as available would turn
    a missing credential into a silent fallback to the scripted backend.
    """
    try:
        from openai import OpenAI
    except Exception as e:                                    # noqa: BLE001
        return None, f"openai client not installed: {type(e).__name__}"

    url = base_url or os.environ.get("OPENAI_BASE_URL")
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not url:
        return None, "OPENAI_BASE_URL is not set"
    if not key:
        return None, "OPENAI_API_KEY is not set"
    try:
        client = OpenAI(base_url=url, api_key=key, timeout=timeout)
        client.models.list()
    except Exception as e:                                    # noqa: BLE001
        return None, f"endpoint not usable: {type(e).__name__}: {str(e)[:120]}"

    class _Backend:
        name = "openai-compatible"

        def __init__(self, client, model):
            self.client = client
            self.model = model

        def complete(self, messages):
            resp = self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=0.0)
            return resp.choices[0].message.content

    return _Backend(client, model or "gpt-4o-mini"), None


class LLMPlannerPolicy:
    """A policy whose decisions come from a model.

    `name` carries the backend so a result table cannot silently mix a model run with a scripted
    one: the label says which it was.
    """

    def __init__(self, backend, *, max_calls_per_tick: int = 1, tick_interval_s: int = 300,
                 max_commands_per_call: int = 4) -> None:
        self.backend = backend
        self.name = f"llm_planner[{getattr(backend, 'name', 'unknown')}]"
        self.log = PlannerLog()
        self.tick_interval_s = tick_interval_s
        self.max_calls_per_tick = max_calls_per_tick
        self.max_commands_per_call = max_commands_per_call
        self._last_call_at = None
        # A decision the model got wrong is not re-asked on the same tick; the next tick tries
        # again. Retrying immediately would spend the whole opportunity budget on one bad reply.
        self._fallback_used = 0

    def plan(self, view) -> list[tuple[str, dict]]:
        if self._last_call_at is not None and view.t_s - self._last_call_at < self.tick_interval_s:
            return []
        self._last_call_at = view.t_s

        messages = [{"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": render(view)}]
        started = time.monotonic()
        try:
            raw = self.backend.complete(messages)
            error = None
        except Exception as e:                                # noqa: BLE001
            raw, error = "", f"backend raised {type(e).__name__}: {str(e)[:100]}"
        latency = time.monotonic() - started

        decision, parse_error = (None, error) if error else parse_decision(raw)
        self.log.calls.append(PlannerCall(
            at_s=view.t_s, prompt_chars=sum(len(m["content"]) for m in messages), raw=raw,
            parsed=decision, error=parse_error, latency_s=latency,
            backend=getattr(self.backend, "name", "unknown")))

        if decision is None:
            # The model produced nothing usable. The run continues without an action rather than
            # being rescued silently: a fallback that completes the model's job would make the
            # illegal-decision rate invisible.
            self._fallback_used += 1
            return []

        action = decision["action"]
        args = decision["args"]
        if action == "set_monitoring_profile":
            node = args["node"]
            if node not in view.node_ids or node in view.in_flight:
                return []
            return [(node, {"op": "set_monitoring_profile", "profile": args["profile"]})]
        if action == "read_status":
            node = args["node"]
            if node not in view.node_ids:
                return []
            # A read is not a command; the runner treats an empty payload as no-op for this layer,
            # so it is recorded in the log and costs nothing here.
            return []
        return []

    def summary(self) -> dict:
        s = self.log.summary()
        s["rejected_decisions"] = self._fallback_used
        return s
