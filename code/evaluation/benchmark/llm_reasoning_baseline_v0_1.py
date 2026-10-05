#!/usr/bin/env python3
"""Frozen-split LLM/reasoning-agent baseline for Layer-1 v0.1.

The model receives only the causal observation history, public task/deadline
state, public satellite geometry and the same legal action list used by the
placement-preserving deterministic baselines.  Alias/world identity and future
terrestrial truth are never exposed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from time import perf_counter
from typing import Any, Mapping

from openai import OpenAI

from causal_evidence_process_v0_1 import (
    ACK_TIMEOUT_S,
    FINAL_ACK_DELAY_S,
    QUERY_RESPONSE_DELAY_S,
    SATELLITE_COMPLETION_DELAY_S,
    attach_causal_evidence,
)
from dynamic_world_materializer_v0_1 import iter_world_bundles
from exact_reference_oracle_v0_1 import LocalState, _attempt_lattice, _expired, _success
from v8_policy_baselines_v0_1 import _canon, _legal_actions, _normalize_one, _step


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPLIT = ROOT / "results/benchmark/layer1-structure-aware-split-v0.1.json"
DEFAULT_OUT = ROOT / "local_research/current/benchmark/llm-baseline-v0.1"
SYSTEM_PROMPT = """你是山区灾前监测通信调度的通用 reasoning baseline。
你只能使用输入中明确给出的当前可观测历史、公开任务 deadline、公开卫星机会和 legal actions。
隐藏的 terrestrial future/world identity 不可假设。目标是让所有 monitoring obligations 在各自 deadline 前完成。
查询会消耗真实 terrestrial capacity；卫星 fallback 是有限资源。只能从 legal actions 中选一个。
只输出 JSON：{\"choice\": 整数}。不要输出解释。"""


def _load_test_signatures(split_path: Path) -> tuple[dict[str, str], Counter[str]]:
    split = json.loads(split_path.read_text(encoding="utf-8"))
    rep: dict[str, str] = {}
    mult: Counter[str] = Counter()
    for row in split["rows"]:
        if row["split"] != "test" or row["candidate_role"] != "HARD_PRE_ADMISSION_SURVIVOR":
            continue
        sig = str(row["signature"])
        rid = str(row["recipe_id"])
        mult[sig] += 1
        if sig not in rep or rid < rep[sig]:
            rep[sig] = rid
    return rep, mult


def _collect_bundles(rep: Mapping[str, str]) -> dict[str, dict[str, Any]]:
    rid_to_sig = {rid: sig for sig, rid in rep.items()}
    out = {}
    for bundle in iter_world_bundles():
        sig = rid_to_sig.get(str(bundle["recipe_id"]))
        if sig is not None:
            out[sig] = bundle
            if len(out) == len(rep):
                break
    if set(out) != set(rep):
        raise RuntimeError(f"missing test-hard representative bundles: {len(set(rep) - set(out))}")
    return out


def _common_value(values: list[Any]) -> Any:
    return values[0] if values and all(v == values[0] for v in values) else "UNKNOWN"


def _action_json(action: tuple[str, str | None]) -> dict[str, Any]:
    return {"action": action[0], "arg": action[1]}


def _prompt(bundle, at_s: int, states: Mapping[str, LocalState], history: tuple[str, ...], actions) -> str:
    delivered_sets = [set(st.delivered) for st in states.values()]
    delivered_common = sorted(set.intersection(*delivered_sets)) if delivered_sets else []
    pending_sets = [{d.obligation_id for d in st.pending_deliveries} for st in states.values()]
    pending_common = sorted(set.intersection(*pending_sets)) if pending_sets else []
    sat_budget = _common_value([st.satellite_budget for st in states.values()])
    query_pending = _common_value([st.pending_query is not None for st in states.values()])
    future_sat = [
        {
            "start_s": int(w["start_s"]),
            "end_s": int(w["end_s"]),
            "capacity_units": int(w["capacity_units"]),
        }
        for w in bundle["public_environment"]["satellite_windows"]
        if int(w["end_s"]) > at_s
    ]
    payload = {
        "time_s": at_s,
        "obligations": [
            {
                "id": str(o["obligation_id"]),
                "release_s": int(o["release_s"]),
                "deadline_s": int(o["deadline_s"]),
            }
            for o in bundle["obligations"]
        ],
        "observed_delivered_common": delivered_common,
        "attempt_pending_common": pending_common,
        "satellite_budget": sat_budget,
        "query_pending": query_pending,
        "recent_observation_history": list(history[-12:]),
        "public_future_satellite_windows": future_sat,
        "timing_semantics": {
            "terrestrial_final_ack_delay_s": FINAL_ACK_DELAY_S,
            "terrestrial_failure_timeout_s": ACK_TIMEOUT_S,
            "owner_query_response_or_timeout_s": QUERY_RESPONSE_DELAY_S,
            "satellite_completion_delay_s": SATELLITE_COMPLETION_DELAY_S,
        },
        "legal_actions": [
            {"choice": i, **_action_json(action)}
            for i, action in enumerate(actions)
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _parse_choice(text: str, n: int) -> int | None:
    try:
        obj = json.loads(text.strip())
        x = int(obj["choice"])
        return x if 0 <= x < n else None
    except Exception:
        m = re.search(r'"?choice"?\s*[:=]\s*(\d+)', text)
        if m:
            x = int(m.group(1))
            return x if 0 <= x < n else None
        return None


class ModelPolicy:
    def __init__(self, *, model: str, timeout_s: float):
        key = os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured")
        self.client = OpenAI(api_key=key, base_url="https://api.deepseek.com", timeout=timeout_s, max_retries=2)
        self.model = model
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.invalid_actions = 0
        self.cache: dict[str, tuple[int | None, str]] = {}
        self.log: list[dict[str, Any]] = []

    def choose(self, prompt: str, actions) -> int | None:
        digest = sha256(prompt.encode("utf-8")).hexdigest()
        if digest in self.cache:
            choice, raw = self.cache[digest]
        else:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=32,
                reasoning_effort="none",
                extra_body={"thinking": {"type": "disabled"}},
            )
            self.calls += 1
            raw = response.choices[0].message.content or ""
            usage = getattr(response, "usage", None)
            if usage is not None:
                self.prompt_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
                self.completion_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
            choice = _parse_choice(raw, len(actions))
            self.cache[digest] = (choice, raw)
        if choice is None:
            self.invalid_actions += 1
        self.log.append({
            "prompt_sha256": digest,
            "raw_response": raw[:256],
            "choice": choice,
            "legal_action_count": len(actions),
        })
        return choice


def run_bundle(bundle: Mapping[str, Any], *, model: str, timeout_s: float, max_path_decisions: int = 128) -> dict[str, Any]:
    process = attach_causal_evidence(bundle)
    start = min(_attempt_lattice(bundle))
    states = {
        str(w["world_id"]): LocalState(
            satellite_budget=int(bundle["public_environment"]["satellite_budget_units"])
        )
        for w in bundle["worlds"]
    }
    policy = ModelPolicy(model=model, timeout_s=timeout_s)
    decision_nodes = 0
    fail_reason = None
    started = perf_counter()

    def rec(at_s: int, current: Mapping[str, LocalState], history: tuple[str, ...], seen: frozenset[Any], depth: int) -> bool:
        nonlocal decision_nodes, fail_reason
        branches = _normalize_one(bundle, process, at_s, current)
        if len(branches) > 1 or next(iter(branches)) != "same":
            for obs, child in sorted(branches.items()):
                if not rec(at_s, child, history + (obs,), seen, depth):
                    return False
            return True
        current = next(iter(branches.values()))
        if any(_expired(bundle, st, at_s) for st in current.values()):
            fail_reason = "DEADLINE_EXPIRED"
            return False
        if all(_success(bundle, st) for st in current.values()):
            return True
        key = (at_s, _canon(current), sha256("|".join(history).encode()).hexdigest()[:16])
        if key in seen:
            fail_reason = "POLICY_LOOP"
            return False
        if depth >= max_path_decisions:
            fail_reason = "DECISION_CAP"
            return False
        actions = _legal_actions(bundle, process, current, at_s)
        if not actions:
            fail_reason = "NO_LEGAL_ACTION"
            return False
        prompt = _prompt(bundle, at_s, current, history, actions)
        choice = policy.choose(prompt, actions)
        decision_nodes += 1
        if choice is None:
            fail_reason = "INVALID_MODEL_ACTION"
            return False
        stepped = _step(bundle, process, current, at_s, actions[choice])
        if stepped is None:
            fail_reason = "STEP_REJECTED"
            return False
        child, next_t = stepped
        return rec(next_t, child, history, seen | {key}, depth + 1)

    try:
        success = rec(start, states, tuple(), frozenset(), 0)
        error = None
    except Exception as exc:
        success = False
        error = f"{type(exc).__name__}: {exc}"
        fail_reason = "MODEL_OR_RUNTIME_ERROR"
    wall_ms = (perf_counter() - started) * 1000.0
    return {
        "success": success,
        "failure_reason": fail_reason,
        "error": error,
        "decision_nodes": decision_nodes,
        "api_calls": policy.calls,
        "invalid_actions": policy.invalid_actions,
        "prompt_tokens": policy.prompt_tokens,
        "completion_tokens": policy.completion_tokens,
        "wall_ms": wall_ms,
        "decision_log": policy.log,
    }


def _run_one(args):
    sig, bundle, multiplicity, model, timeout_s = args
    row = run_bundle(bundle, model=model, timeout_s=timeout_s)
    row.update({
        "signature": sig,
        "representative_recipe_id": bundle["recipe_id"],
        "projected_test_recipe_count": multiplicity,
    })
    return sig, row


def _load_completed(path: Path) -> dict[str, dict[str, Any]]:
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[str(row["signature"])] = row
    return out


def materialize(*, out_dir: Path, split_path: Path, model: str, workers: int, timeout_s: float, resume: bool, limit_signatures: int | None) -> dict[str, Any]:
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    rows_path = out_dir / "signature-results.jsonl"
    rep, multiplicity = _load_test_signatures(split_path)
    bundles = _collect_bundles(rep)
    completed = _load_completed(rows_path) if resume else {}
    if not resume and rows_path.exists():
        rows_path.unlink()
    todo = sorted(set(rep) - set(completed))
    if limit_signatures is not None:
        todo = todo[:limit_signatures]
    mode = "a" if resume and rows_path.exists() else "w"
    with rows_path.open(mode, encoding="utf-8", buffering=1) as f:
        if workers <= 1:
            for sig in todo:
                _, row = _run_one((sig, bundles[sig], multiplicity[sig], model, timeout_s))
                completed[sig] = row
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        else:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futs = {
                    ex.submit(_run_one, (sig, bundles[sig], multiplicity[sig], model, timeout_s)): sig
                    for sig in todo
                }
                for fut in as_completed(futs):
                    sig, row = fut.result()
                    completed[sig] = row
                    f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    complete = len(completed) == len(rep)
    signature_success = sum(bool(r["success"]) for r in completed.values())
    recipe_success = sum(int(r["projected_test_recipe_count"]) for r in completed.values() if r["success"])
    recipe_total = sum(int(r["projected_test_recipe_count"]) for r in completed.values())
    failures = Counter(str(r["failure_reason"]) for r in completed.values() if not r["success"])
    return {
        "schema_version": "0.1",
        "status": "COMPLETE" if complete else "PARTIAL",
        "provider": "DeepSeek official",
        "model": model,
        "temperature": 0,
        "thinking": "disabled",
        "reasoning_effort": "none",
        "max_tokens": 32,
        "split_ref": str(split_path.relative_to(ROOT)),
        "split_sha256": sha256(split_path.read_bytes()).hexdigest(),
        "information_contract": "frozen test hard signatures; causal observation history + public task/satellite state + placement-preserving legal actions only",
        "test_hard_signature_count": len(rep),
        "completed_signature_count": len(completed),
        "signature_success_count": signature_success,
        "signature_success_rate": signature_success / len(completed) if completed else 0.0,
        "projected_test_recipe_count": recipe_total,
        "projected_test_recipe_success_count": recipe_success,
        "projected_test_recipe_success_rate": recipe_success / recipe_total if recipe_total else 0.0,
        "api_calls": sum(int(r["api_calls"]) for r in completed.values()),
        "prompt_tokens": sum(int(r["prompt_tokens"]) for r in completed.values()),
        "completion_tokens": sum(int(r["completion_tokens"]) for r in completed.values()),
        "invalid_actions": sum(int(r["invalid_actions"]) for r in completed.values()),
        "failure_reasons": dict(sorted(failures.items())),
        "signature_results_ref": str(rows_path.relative_to(ROOT)),
        "release_status": "FROZEN_SPLIT_BASELINE" if complete else "PARTIAL_BASELINE",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--split", type=Path, default=SPLIT)
    ap.add_argument("--model", required=True)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--timeout-s", type=float, default=45.0)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--limit-signatures", type=int)
    ap.add_argument("--manifest", type=Path)
    args = ap.parse_args()
    split_path = args.split if args.split.is_absolute() else ROOT / args.split
    manifest = materialize(
        out_dir=args.out_dir,
        split_path=split_path,
        model=args.model,
        workers=args.workers,
        timeout_s=args.timeout_s,
        resume=args.resume,
        limit_signatures=args.limit_signatures,
    )
    text = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
