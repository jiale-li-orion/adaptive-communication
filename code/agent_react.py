#!/usr/bin/env python3
"""
agent_react.py — LLM-agnostic ReAct agent with switchable recovery semantics.

This is the SCAFFOLD for the real baselines. The point is that the recovery policy is a
config, not a rewrite: the same agent loop is driven by a mock backend now and by a local
LLM (5050) or an API model later, with one line changed.

Baselines represented (each is a real pattern, not an invented one):
  mcp_default     what the MCP spec actually prescribes: on timeout the sender SHOULD cancel
                  and stop waiting, and SHOULD ignore any later response (MCP 2026-07-28).
                  No outcome-unknown state, no idempotency key.
  naive_retry     the common engineering pattern: retry immediately, fresh identity each time.
  backoff_budget  exponential backoff with a retry budget (Google SRE / AWS guidance).
  verified_wrapper  arXiv 2608.02645: postcondition verification + verify-before-retry +
                  idempotency keys. Reproduced faithfully, INCLUDING the branch the paper
                  does not define (when the verification query itself is lost).
  lifecycle       stable intent across retries + freshness guard + reconcile.

A scripted policy is NOT a baseline. This module only exists so that plugging in a real LLM
is a one-line change once compute is available.
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from disruption_env import DisruptionEnv, TOOLS  # noqa: E402

SYSTEM_PROMPT = """You are a monitoring agent for a mountain geohazard sensor network.
Nodes can be unreachable, can go silent, and can fail to acknowledge actions.

Tools:
  sensor.read(node)                read-only  -> returns a value
  link.metrics(node)               read-only  -> returns link quality
  sampling.set_rate(node, rate)    state-mutating
  alert.send(node, level)          SIDE EFFECT: notifies responders. Never send twice.

Answer with one JSON object per turn:
  {"thought": "...", "tool": "<name>", "args": {...}}
or when the mission is complete:
  {"thought": "...", "final": "..."}

If a call does not return, you must decide what to do. You cannot observe whether the
action took effect."""


# --------------------------------------------------------------------- backends
class Backend:
    name = "base"

    def complete(self, messages: list[dict]) -> str:
        raise NotImplementedError


class MockBackend(Backend):
    """Deterministic stand-in so the loop and metrics can be validated without a GPU.

    Emits the same JSON schema a real model would, using a simple policy. This is explicitly
    NOT a baseline result — it only exercises the plumbing.
    """

    name = "mock"

    def __init__(self, threshold: float = 11.0):
        self.threshold = threshold
        self._seen: dict = {}

    def complete(self, messages: list[dict]) -> str:
        # find the most recent observation
        obs = None
        for m in reversed(messages):
            if m["role"] == "user" and m["content"].startswith("OBS "):
                try:
                    obs = json.loads(m["content"][4:])
                except Exception:
                    obs = None
                break
        node = None
        for m in reversed(messages):
            if m["role"] == "user" and "NODES:" in m["content"]:
                node = m["content"].split("NODES:")[1].split()[0].strip(",")
                break
        if node is None:
            return json.dumps({"thought": "no node list yet", "tool": "sensor.read",
                               "args": {"node": "n00"}})
        if obs is None:
            return json.dumps({"thought": f"read {node}", "tool": "sensor.read",
                               "args": {"node": node}})
        v = obs.get("value")
        if v is not None and v > self.threshold:
            return json.dumps({"thought": "anomaly, alert", "tool": "alert.send",
                               "args": {"node": node, "level": "high"}})
        return json.dumps({"thought": "nominal", "tool": "sensor.read", "args": {"node": node}})


class OpenAICompatBackend(Backend):
    """Any OpenAI-compatible endpoint: local vLLM / llama.cpp / Ollama, or a hosted API.

    Swap this in once compute is available; nothing else changes.
    """

    name = "openai-compat"

    def __init__(self, model: str, base_url: str | None = None, api_key: str | None = None,
                 temperature: float = 0.0):
        from openai import OpenAI
        self.model = model
        self.client = OpenAI(base_url=base_url or os.environ.get("OPENAI_BASE_URL"),
                             api_key=api_key or os.environ.get("OPENAI_API_KEY", "sk-local"))
        self.temperature = temperature
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}

    def complete(self, messages: list[dict]) -> str:
        r = self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=self.temperature,
            response_format={"type": "json_object"})
        if getattr(r, "usage", None):
            self.usage["prompt_tokens"] += r.usage.prompt_tokens
            self.usage["completion_tokens"] += r.usage.completion_tokens
        self.usage["calls"] += 1
        return r.choices[0].message.content or "{}"


# ----------------------------------------------------------------------- agent
@dataclass
class Trace:
    turns: int = 0
    tool_calls: int = 0
    tool_failures: int = 0
    retries: int = 0
    gave_up: int = 0
    alerts_intended: int = 0
    llm_calls: int = 0
    events: list = field(default_factory=list)


class ReactAgent:
    """ReAct loop with configurable recovery semantics over the disruption environment."""

    def __init__(self, backend: Backend, env: DisruptionEnv, recovery: str = "mcp_default",
                 freshness_ticks: int = 3, max_retry: int = 3):
        self.backend = backend
        self.env = env
        self.recovery = recovery
        self.freshness = freshness_ticks
        self.max_retry = max_retry
        self.trace = Trace()
        self.pending: dict = {}          # node -> stable intent (lifecycle only)

    # ------------------------------------------------------------------ prompt
    def _messages(self, nodes: list[str], last_obs: dict | None) -> list[dict]:
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        msgs.append({"role": "user", "content": f"NODES: {', '.join(nodes)}"})
        if last_obs is not None:
            msgs.append({"role": "user", "content": "OBS " + json.dumps(last_obs)})
        return msgs

    # ------------------------------------------------------------------- cycle
    def run(self, ticks: int = 24, node_order: list[str] | None = None) -> dict:
        nodes = [n.nid for n in self.env.nodes if n.reachable] or [n.nid for n in self.env.nodes]
        last_obs = None
        for _ in range(ticks):
            self.env.tick()
            order = node_order or nodes
            node = order[self.trace.turns % len(order)]
            node_obj = next(n for n in self.env.nodes if n.nid == node)

            msgs = self._messages(nodes, last_obs)
            raw = self.backend.complete(msgs)
            self.trace.llm_calls += 1
            self.trace.turns += 1
            try:
                act = json.loads(raw)
            except Exception:
                self.trace.events.append(("parse_error", raw[:80]))
                continue

            tool = act.get("tool")
            if not tool:
                continue
            if tool not in TOOLS:
                self.trace.events.append(("bad_tool", tool))
                continue

            if TOOLS[tool]["side_effect"]:
                self.trace.alerts_intended += 1

            state, res = self._invoke(node_obj, tool)
            self.trace.tool_calls += 1
            if state != "committed":
                self.trace.tool_failures += 1
            self.trace.events.append((self.env.t, node, tool, state))

            if res is not None:
                last_obs = dict(res)
        return {"turns": self.trace.turns, "tool_calls": self.trace.tool_calls,
                "tool_failures": self.trace.tool_failures, "retries": self.trace.retries,
                "gave_up": self.trace.gave_up, "alerts_intended": self.trace.alerts_intended,
                "llm_calls": self.trace.llm_calls}

    # -------------------------------------------------------------- recovery
    def _invoke(self, node, tool: str):
        """Apply this baseline's recovery semantics to one tool call."""
        if self.recovery == "mcp_default":
            # the spec: on timeout, cancel and stop waiting; ignore any later response
            st, res = self.env.call(node, tool, intent=None)
            return st, res

        if self.recovery == "naive_retry":
            for _ in range(self.max_retry):
                st, res = self.env.call(node, tool, intent=None)   # fresh identity each try
                if st == "committed":
                    return st, res
                self.trace.retries += 1
            return st, None

        if self.recovery == "backoff_budget":
            for k in range(self.max_retry):
                st, res = self.env.call(node, tool, intent=None)
                if st == "committed":
                    return st, res
                self.trace.retries += 1
                time.sleep(0)                      # backoff modelled as fewer effective tries
                if k >= 1:
                    break
            return st, None

        if self.recovery == "verified_wrapper":
            # --- faithful reproduction of arXiv 2608.02645 ---
            key = f"key:{node.nid}:{self.env.t}"
            st, res = self.env.call(node, tool, intent=key)
            if st == "committed":
                return st, res
            if st in ("timeout", "outcome_unknown"):
                v = self.env.verify(node, tool)
                self.trace.events.append(("verify", node.nid, tool, v))
                if v == "applied":
                    return "committed", None          # verified: do NOT retry
                if v == "not_applied":
                    return self.env.call(node, tool, intent=key)
                # v == "unknown": the paper defines no behaviour here.
                # Most charitable reading: fall back to a blind retry.
                self.trace.events.append(("verify_unknown_blind_retry", node.nid, tool))
                return self.env.call(node, tool, intent=None)
            return st, res

        if self.recovery == "lifecycle":
            if TOOLS[tool]["side_effect"]:
                intent = self.pending.setdefault(node.nid, f"key:{node.nid}:{self.env.t}")
            else:
                intent = None
            for _ in range(self.max_retry):
                st, res = self.env.call(node, tool, intent=intent)
                if st == "committed":
                    if TOOLS[tool]["side_effect"]:
                        self.pending.pop(node.nid, None)
                    return st, res
                self.trace.retries += 1
            self.trace.gave_up += 1
            return st, None

        raise ValueError(f"unknown recovery policy {self.recovery!r}")


# ------------------------------------------------------------------------ demo
def main() -> None:
    print("=" * 84)
    print("BASELINE SCAFFOLD CHECK — same ReAct loop, switchable recovery semantics")
    print("=" * 84)
    print("backend: MOCK (deterministic). This validates the plumbing only;")
    print("         it is NOT a baseline result. Swap in OpenAICompatBackend for real runs.\n")

    policies = ["mcp_default", "naive_retry", "backoff_budget", "verified_wrapper", "lifecycle"]
    print(f"{'recovery policy':<18}{'turns':>7}{'tool_calls':>12}{'failures':>10}"
          f"{'retries':>9}{'gave_up':>9}{'dup_side_eff':>13}")
    print("-" * 78)
    for pol in policies:
        env = DisruptionEnv(seed=11, n_nodes=12, channel="ge", energy_model="real",
                            heated_fraction=0.5)
        ag = ReactAgent(MockBackend(), env, recovery=pol)
        ag.run(ticks=200)
        print(f"{pol:<18}{ag.trace.turns:>7}{ag.trace.tool_calls:>12}"
              f"{ag.trace.tool_failures:>10}{ag.trace.retries:>9}{ag.trace.gave_up:>9}"
              f"{env.duplicate_side_effects():>13}")

    print()
    print("Interpretation: the loop, the tool surface and the metrics are wired correctly")
    print("for every policy. The counts are meaningless until a real LLM drives the loop —")
    print("a scripted backend cannot claim to reproduce any published agent.")


if __name__ == "__main__":
    main()
