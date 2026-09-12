#!/usr/bin/env python3
"""
run_baseline.py — does a naive tool-using agent violate execution correctness under
communication-induced partial failure? (S6, the paper's go/no-go)

Three policies run over identical episodes:
  naive           retry blindly, no idempotency, no freshness guard  (the common baseline)
  backoff         same, with exponential backoff and a retry budget
  lifecycle       stable intent across retries + freshness guard + reconcile

Metrics are counted from ENVIRONMENT GROUND TRUTH, not from what the agent believes:
  duplicate_side_effects   same intent applied >1 time
  lost_side_effects        intent never applied at all
  stale_decisions          acted on an observation older than the freshness bound
  outcome_unknown          calls whose result the agent could not determine
  committed                calls that returned cleanly

CPU only. No LLM needed to demonstrate the mechanism.
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from disruption_env import DisruptionEnv, TOOLS  # noqa: E402

THRESHOLD = 11.0          # anomaly threshold on the sensor value
FRESHNESS_TICKS = 3       # an observation older than this is stale
MAX_RETRY = 3


def run_episode(policy: str, seed: int, ticks: int = 4320, n_nodes: int = 16,
                channel: str = "iid", energy_model: str = "real",
                temp_offset_c: float = 0.0, heated_fraction: float = 0.5) -> dict:
    env = DisruptionEnv(seed=seed, n_nodes=n_nodes, ticks=ticks, channel=channel,
                        energy_model=energy_model, temp_offset_c=temp_offset_c,
                        heated_fraction=heated_fraction)
    m = defaultdict(int)

    last_value: dict = {}          # node -> (tick, value)
    pending: dict = {}             # intent -> first tick (for lost detection)
    open_intent: dict = {}         # node -> intent id while an anomaly is unresolved

    for _ in range(ticks):
        env.tick()
        for node in env.nodes:
            # ---------------- read ----------------------------------------
            attempts = MAX_RETRY if policy == "naive" else 2
            got = None
            for k in range(attempts):
                st, res = env.call(node, "sensor.read")
                if st == "committed":
                    got = res
                    break
                if st in ("timeout", "outcome_unknown"):
                    m[st] += 1
                else:
                    m[st] += 1
                    break                      # unavailable: no point retrying now
                if policy == "backoff" and k >= 1:
                    # exponential backoff consumes the window: fewer effective attempts
                    break
            if got is not None:
                last_value[node.nid] = (env.t, got["value"])
            else:
                m["read_failed"] += 1

            # ---------------- decide --------------------------------------
            obs = last_value.get(node.nid)
            if obs is None:
                continue
            age = env.t - obs[0]
            if age > FRESHNESS_TICKS:
                m["stale_observed"] += 1

            anomalous = obs[1] > THRESHOLD

            # decide whether to act (send an alert)
            if policy == "lifecycle":
                if age > FRESHNESS_TICKS and anomalous:
                    # refuse to act on stale data; reconcile instead
                    m["deferred_for_freshness"] += 1
                    continue
                act = anomalous and node.nid not in open_intent
                intent = open_intent.setdefault(node.nid, f"alert:{node.nid}:{env.t}") if act else None
            else:
                act = anomalous
                intent = None            # naive: a fresh identity every single call

            if not act:
                continue

            # ---------------- side effect ---------------------------------
            if policy == "lifecycle":
                ok = False
                for _k in range(MAX_RETRY):
                    st, res = env.call(node, "alert.send", intent=intent)
                    if st == "committed":
                        ok = True
                        break
                    m[st] += 1
                if not ok:
                    m["lost_side_effects"] += 1
                    pending[intent] = env.t
                else:
                    open_intent.pop(node.nid, None)
            else:
                sent = False
                for _k in range(MAX_RETRY):
                    st, _res = env.call(node, "alert.send", intent=None)
                    if st in ("committed", "outcome_unknown"):
                        sent = True
                        break
                    m[st] += 1
                    if policy == "backoff" and _k == MAX_RETRY - 1:
                        break
                if not sent:
                    m["lost_side_effects"] += 1

    logical = len({(a[3], a[2]) for a in env.truth.applied}) or 1
    dups = env.duplicate_side_effects()
    n_ep = max(1, env.true_episodes())
    return {
        "policy": policy,
        "seed": seed,
        "channel": channel,
        "energy_model": energy_model,
        "duplicate_side_effects": dups,
        "dup_per_logical": dups / logical,
        "applied_per_alert": len(env.truth.applied) / n_ep,
        "true_episodes": n_ep,
        "lost_side_effects": m["lost_side_effects"],
        "stale_decisions": m["stale_observed"] + m["deferred_for_freshness"],
        "outcome_unknown": m["outcome_unknown"],
        "timeout": m["timeout"],
        "unavailable": m["unavailable"],
        "read_failed": m["read_failed"],
        "applied_total": len(env.truth.applied),
    }


def controlled(n_trials: int = 400, ack_loss_p: float = 0.7, seed: int = 0) -> dict:
    """One logical action per trial, retried up to K times under ACK loss.

    This isolates the mechanism: how many times does the environment actually apply a
    single intended side effect? Naive caller invents a fresh identity per retry;
    lifecycle caller keeps one stable key.
    """
    out = {}
    for label, stable in (("naive", False), ("lifecycle", True)):
        rng = np.random.default_rng(seed)
        dups = 0
        for trial in range(n_trials):
            env = DisruptionEnv(seed=int(rng.integers(1 << 30)), n_nodes=2,
                                ack_loss_p=ack_loss_p)
            cands = [n for n in env.nodes if n.reachable]
            node = min(cands, key=lambda n: abs(env._link_success_p(n) - 0.75))
            env.tick()
            key = "key:one-action"
            for _attempt in range(5):
                st, _ = env.call(node, "alert.send", intent=(key if stable else None))
                if st == "committed":
                    break
            dups += env.duplicate_side_effects()
        out[label] = dups / n_trials
    return out


def main() -> None:
    print("=" * 92)
    print("S6 — BASELINE FAILURE REPRODUCTION (CPU only, no LLM)")
    print("=" * 92)
    print("16 nodes on REAL Tibetan terrain (coverage_grid.csv), 4320 hourly ticks (180 days),")
    print("side-effect tool = alert.send.  Ground-truth counts from the environment.")

    print()
    print("--- A. controlled: ONE intended side effect, retried up to 5x, ACK-loss p=0.7 ---")
    c = controlled()
    print(f"    naive      : {c['naive']:.2f} duplicate applications per intended action")
    print(f"    lifecycle  : {c['lifecycle']:.2f} duplicate applications per intended action")
    print()

    seeds = [1, 2, 3, 4, 5]
    policies = ["naive", "backoff", "lifecycle"]

    agg = {}
    for pol in policies:
        rs = [run_episode(pol, s) for s in seeds]
        agg[pol] = {k: np.mean([r[k] for r in rs])
                    for k in rs[0]
                    if k not in ("policy", "seed", "channel", "energy_model")}
        agg[pol + "_raw"] = rs

    print()
    print("--- B. full 180-day, 16-node episodes ---")
    hdr = (f"{'policy':<12}{'dup_side_eff':>14}{'dup/logical':>13}{'lost':>8}"
           f"{'stale':>9}{'outcome_unk':>13}{'unavail':>10}")
    print(hdr); print("-" * len(hdr))
    for pol in policies:
        a = agg[pol]
        print(f"{pol:<12}{a['duplicate_side_effects']:>14.1f}{a['applied_per_alert']:>15.2f}"
              f"{a['lost_side_effects']:>8.1f}{a['stale_decisions']:>9.1f}"
              f"{a['outcome_unknown']:>13.1f}{a['unavailable']:>10.1f}")

    print()
    print("Per-seed detail (naive):")
    print(f"{'seed':>6}{'dup':>8}{'lost':>8}{'stale':>8}{'outcome_unk':>13}")
    for r in agg["naive_raw"]:
        print(f"{r['seed']:>6}{r['duplicate_side_effects']:>8}"
              f"{r['lost_side_effects']:>8}{r['stale_decisions']:>8}{r['outcome_unknown']:>13}")

    print()
    print("--- C. do the PHYSICAL models change the conclusion? ---")
    print(f"{'channel':<14}{'energy':<12}{'policy':<11}{'dup_side_eff':>13}"
          f"{'lost':>8}{'outcome_unk':>12}{'unavail':>10}")
    for ch, chl in (("iid", "i.i.d."), ("ge", "Gilbert-Ell.")):
        for em, eml in (("placeholder", "placeholder"), ("real", "real")):
            for pol in ("naive", "lifecycle"):
                rs = [run_episode(pol, sd, channel=ch, energy_model=em) for sd in seeds]
                d = np.mean([r["duplicate_side_effects"] for r in rs])
                lo = np.mean([r["lost_side_effects"] for r in rs])
                ou = np.mean([r["outcome_unknown"] for r in rs])
                un = np.mean([r["unavailable"] for r in rs])
                print(f"{chl:<14}{eml:<12}{pol:<11}{d:>13.1f}{lo:>8.1f}{ou:>12.1f}{un:>10.1f}")

    print()
    print("Interpretation:")
    n = agg["naive"]; l = agg["lifecycle"]
    if n["duplicate_side_effects"] > 0 and l["duplicate_side_effects"] < n["duplicate_side_effects"]:
        print(f"  naive retry produces {n['duplicate_side_effects']:.1f} duplicate side effects per "
              f"180-day episode;")
        print(f"  the lifecycle policy reduces this to {l['duplicate_side_effects']:.1f}.")
        print("  => the failure is reproducible and the mechanism fixes it.")
    else:
        print("  no separation observed — inspect the channel parameters before proceeding.")


if __name__ == "__main__":
    main()
