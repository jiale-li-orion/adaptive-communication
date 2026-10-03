# -*- coding: utf-8 -*-
"""agent_repairable_loss.py — r38 真实轨迹的「可修性清单」（零 API）。

STATUS (2026-09-21): HISTORICAL / CLOSED CANDIDATE SUPPORT.
修正 deadline equality 后，后续预注册 cross-segment probe 未通过进入门槛；本脚本保留为冻结
r38 轨迹的故障清单与审计工具，不再作为当前 V1 repair 方法的进入依据。若未来出现新的
execution-grounded witness，应另开实验编号并重新冻结 ordinary-baseline gate。

口径来源：`paper/AGENT_RESEARCH.md` §6 第一步。

分母固定
--------
`r42_claim_relabel.FINAL` 的 11 份最终轨迹、逐条决策为分母（本仓库 C8 引用的「十一轨迹、
1089 次决策」即此集合）。分母不随筛除结果变化。

决策状态与 node/field 候选
-------------------------
全局只先区分三种 decision state：

`parse`          以 r42 的 authoritative raw-JSON 口径判定最终解析失败；旧 trace 中首轮请求错误但
                 后续 retry 成功的 stale `api_error` 不再计入。
`forced_no_opp`  强制主回传中断窗 `[4h,20h)`；中心新命令无法到达现场，历史 proposal 只做记录。
`normal`         其余可继续做逐节点审计的 decision。

随后按**模型 raw 显式 proposal、旧 parser-normalized action、previous sticky target 与
targets_after 分层**抽取 node/field witness；同一 decision 可以有多条候选：

`parser_omission_target_reset`
    旧 parser 把 raw 中省略的节点自动补成 current confirmed config，从而把未确认 previous target
    静默 reset。它是接口契约 bug，已由 baseline 修复，不算 Candidate A。
`action_on_unknown_node`
    模型 raw 显式修改 alive/SoC 证据 unknown 的节点；普通 unknown/safety handling 覆盖。
`backlog_densify_candidate`
    模型 raw 显式把 sample 加密，而中心看到源端自报 cache>0、AoI 落后。这里只形成“源端积压”
    候选；不能据此声称网关已有合格副本或回传段已定位。
`mission_target_gap`
    decision 后 sticky target 的 sample 与当前授权 dense requirement 冲突。它按来源继续区分
    raw explicit / sticky previous target / parser omission reset；普通 mission-compliance baseline
    必须拥有相同任务、证据与 safety 能力，因此默认不算 V1 独立 witness。

实际结果按**逐义务行 + action horizon**连接：用零 LLM 重放同一轨迹，只列从当前 decision 到下一
decision 之间新 release、或当前尚未过 deadline 的义务及其真实结局。它是结果见证，不是反事实因果；
不再把某节点整场所有 miss 重复贴到每一个 candidate decision 上。

Run: python3 code/analysis/agent_repairable_loss.py [--out results/agent_repairable_loss.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
for _d in ("v3joint", "instance", "physics", "runtime", "experiments", "analysis", "monitoring"):
    _p = os.path.join(ROOT, "code", _d)
    if _p not in sys.path:
        sys.path.insert(0, _p)

from joint_run import run_joint
from agent_mission import AgentMissionPolicy, ReplayDecider
from agent_plan_repair import bind_proposal_to_obligations
from r42_claim_relabel import FINAL, T, note_of

H = lambda h: h * 3600
OUT_LO, OUT_HI = 4 * H(1), 20 * H(1)
UP = [(0, 600, "blue"), (6 * H(1), 300, "yellow")]
BASE = dict(task_hours=48, tail_hours=1, arm="local", groups=2, sample_interval_s=600,
            report_period_s=600, routine_period_s=600, harvest_mode="solar",
            harvest_peak_wh_per_hour=0.03, initial_soc=1.0, outage_start_h=4, outage_hours=16,
            enable_backup=True, backup_rate_s=1200, backup_bytes=78, backup_chooser="maxcov")
DECISION_STATES = ("parse", "forced_no_opp", "normal")
CANDIDATE_TYPES = ("parser_omission_target_reset", "backlog_densify_candidate",
                   "mission_target_gap", "action_on_unknown_node")
#: 逐节点"可达成"所需的电量门。8 mWh 是 C5 的停止门取值；这里只作为**要求**的窄化条件，
#: 不主张"高于它就开启密采有益"。
DENSE_FLOOR_WH = 0.008


def _required_period(obs) -> int:
    return obs["mission"]["required_period_s"]


def _applied(node: dict):
    return (node.get("cur_sample_s"), node.get("cur_report_s"))


def _raw_explicit_ids(rec: dict) -> set[str]:
    """旧 r38 的 actions 已被 parser 用 current config 填满；模型显式节点必须从 raw 恢复。"""
    raw = rec.get("raw")
    if not raw:
        return set()
    try:
        obj = json.loads(raw)
    except Exception:
        try:
            obj = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        except Exception:
            return set()
    if not isinstance(obj, dict):
        return set()
    return {
        a.get("node_id") for a in obj.get("actions", [])
        if isinstance(a, dict) and a.get("node_id") is not None
    }


def _proposed(rec: dict, nid: str, raw_ids: set[str] | None = None):
    """模型显式 proposal 经旧 parser 合法化后的值；省略节点返回 None。"""
    ids = _raw_explicit_ids(rec) if raw_ids is None else raw_ids
    if nid not in ids:
        return None
    v = (rec.get("actions") or {}).get(nid)
    return tuple(v) if isinstance(v, (list, tuple)) and len(v) >= 2 else None


def _effective_target(rec: dict, nid: str, cur: tuple) -> tuple:
    """决策后 sticky target；节点被省略时不是“保持当前配置”，而是保持 previous target。"""
    v = (rec.get("targets_after") or {}).get(nid)
    return tuple(v) if isinstance(v, (list, tuple)) and len(v) >= 2 else cur


def _changed_fields(cur: tuple, tgt: tuple | None) -> list[str]:
    if tgt is None:
        return []
    out = []
    if cur[0] != tgt[0]:
        out.append("sample")
    if cur[1] != tgt[1]:
        out.append("report")
    return out


def _effect_status(cur: tuple, explicit: tuple | None, nxt_node: dict | None) -> str:
    """只对本拍**显式新提议**核对下一观察，不把任意变化误算成这条 proposal 生效。"""
    if explicit is None or explicit == cur:
        return "no_explicit_change"
    if not nxt_node:
        return "unresolved_no_next_observation"
    after = _applied(nxt_node)
    if after == explicit:
        return "confirmed_at_next_observation"
    if after == cur:
        return "unresolved_still_at_confirmed_current"
    return "other_effect_observed"


def _binding(obs: dict, t: int, t1: int, nid: str, target: tuple) -> dict:
    """历史轨迹缺 pending；只补**公开 task end**，其余严格用当拍合法 observation。"""
    bobs = dict(obs)
    mission = dict(obs.get("mission") or {})
    mission["task_end_s"] = int(BASE["task_hours"] * 3600)
    bobs["mission"] = mission
    ctx = {"sparse": 600, "dense": 300,
           "decision_horizon_s": max(60, int(t1 - t)),
           "pending": []}
    return bind_proposal_to_obligations(bobs, ctx, nid, int(target[0]), int(target[1]))


def analyze_trace(recs: list[dict], tag: str) -> tuple[list[dict], list[dict]]:
    """返回 (decision audit, node/field candidate rows)。

    decision 只承担全局排除：最终 parse 失败、强制回传中断、正常。
    repair witness 逐节点抽取；同一 decision 可以有多个候选，避免“第一个节点 break”吞掉其余证据。
    """
    decisions, candidates = [], []
    prev_targets: dict[str, tuple] = {}
    for i, rec in enumerate(recs):
        obs = rec.get("observation") or {}
        nodes = {n.get("id"): n for n in (obs.get("nodes") or [])}
        req = _required_period(obs)
        t = rec["t_s"]
        t1 = int(recs[i + 1].get("t_s")) if i + 1 < len(recs) else t + 1800
        nxt = recs[i + 1].get("observation") if i + 1 < len(recs) else None
        nxt_nodes = {n.get("id"): n for n in (nxt.get("nodes") or [])} if nxt else {}

        # 旧 r38 trace 的 api_error 有 412 行“首轮 attempt 出错、重试成功后未清字段”的历史污染。
        # authoritative 口径沿用 r42：以最终 raw 是否可解析/是否缺失判断真正 parse->hold。
        _note, _parse_ok = note_of(rec)
        if not _parse_ok or _note.startswith("[NO RAW]"):
            state = "parse"
        elif tag == "outage" and OUT_LO <= t < OUT_HI:
            state = "forced_no_opp"
        else:
            state = "normal"

        raw_ids = _raw_explicit_ids(rec) if state == "normal" else set()
        explicit_n = sum(1 for nid in nodes if _proposed(rec, nid, raw_ids) is not None)
        decisions.append({"t_s": t, "next_decision_s": t1, "trigger": rec.get("trigger"),
                          "state": state, "required_period_s": req,
                          "explicit_action_nodes": explicit_n})
        if state != "normal":
            for nid, v in (rec.get("targets_after") or {}).items():
                if isinstance(v, (list, tuple)) and len(v) >= 2:
                    prev_targets[nid] = tuple(v[:2])
            continue

        global_link = bool(obs.get("link", {}).get("any_node_heard_last_window"))
        task_end_s = int(BASE["task_hours"] * 3600)
        task_active = t < task_end_s
        for nid, n in nodes.items():
            cur = _applied(n)
            explicit = _proposed(rec, nid, raw_ids)
            parsed = (rec.get("actions") or {}).get(nid)
            parsed = (tuple(parsed) if isinstance(parsed, (list, tuple)) and len(parsed) >= 2
                      else None)
            prev_target = prev_targets.get(nid)
            effective = _effective_target(rec, nid, cur)
            effect = _effect_status(cur, explicit, nxt_nodes.get(nid))
            explicit_fields = _changed_fields(cur, explicit)
            parser_reset = (explicit is None
                            and prev_target is not None and prev_target != cur
                            and parsed == cur and effective == cur)
            common = {
                "t_s": t, "next_decision_s": t1, "trigger": rec.get("trigger"),
                "node": nid, "required_period_s": req,
                "confirmed_current": list(cur),
                "explicit_proposal": (list(explicit) if explicit is not None else None),
                "parser_action": (list(parsed) if parsed is not None else None),
                "previous_target": (list(prev_target) if prev_target is not None else None),
                "effective_target_after_decision": list(effective),
                "explicit_changed_fields": explicit_fields,
                "effect_status": effect,
                "pending_context": "unavailable_in_r38_trace",
                "task_active": task_active,
            }

            if parser_reset:
                candidates.append({
                    **common,
                    "candidate_type": "parser_omission_target_reset",
                    "proposal_field": _changed_fields(prev_target, cur),
                    "legal_evidence": {
                        "raw_node_omitted": True,
                        "system_prompt_contract": "omitted node keeps previous target",
                        "in_flight": n.get("in_flight"),
                        "heard_last_window": n.get("heard_last_window"),
                    },
                    "binding_oids": [],
                    "matched_baseline": "correct parser/target contract",
                    "v1_witness_eligible": False,
                    "eligibility_reason":
                        "interface-contract bug: parser rewrote omitted node to current config",
                })

            if explicit is not None and explicit != cur:
                unknown = (n.get("alive") is False
                           or (n.get("soc_wh") is None and n.get("alive") is None))
                if unknown:
                    b = _binding(obs, t, t1, nid, explicit)
                    candidates.append({
                        **common, "candidate_type": "action_on_unknown_node",
                        "proposal_field": explicit_fields,
                        "legal_evidence": {"alive": n.get("alive"), "soc_wh": n.get("soc_wh"),
                                           "soc_evidence_age_s": n.get("soc_evidence_age_s")},
                        "binding_oids": b["sample_unknown_oids"][:16],
                        "matched_baseline": "ordinary unknown/safety filter",
                        "v1_witness_eligible": False,
                        "eligibility_reason": "ordinary safety/unknown handling, not obligation repair",
                    })

                backlog = (explicit[0] == 300 and cur[0] != 300
                           and (n.get("cache_level") or 0) > 0
                           and bool(n.get("heard_last_window"))
                           and n.get("aoi_s") is not None and n.get("aoi_s") > req)
                if backlog:
                    b = _binding(obs, t, t1, nid, explicit)
                    blocked = bool(b["sample_unknown_oids"])
                    has_sampling_work = bool(b["sample_obligations"])
                    eligible = (task_active and has_sampling_work and not blocked
                                and effect == "confirmed_at_next_observation")
                    if not task_active or not has_sampling_work:
                        baseline = "ordinary task-lifecycle stop"
                        reason = "no active sampling obligation remains"
                    elif blocked:
                        baseline = None
                        reason = "persistent sample action still affects unknown/future obligations"
                    elif effect != "confirmed_at_next_observation":
                        baseline = None
                        reason = "explicit proposal effect not confirmed"
                    else:
                        baseline = None
                        reason = "candidate survives legal binding"
                    candidates.append({
                        **common, "candidate_type": "backlog_densify_candidate",
                        "proposal_field": ["sample"],
                        "legal_evidence": {
                            "aoi_s": n.get("aoi_s"), "cache_level": n.get("cache_level"),
                            "heard_last_window": n.get("heard_last_window"),
                            "note": "center status recency + source backlog; no gateway/segment claim",
                        },
                        "binding_oids": b["sample_unknown_oids"][:16],
                        "binding_future_unknown": [
                            o["oid"] for o in b["sample_obligations"]
                            if o["future"] and o["status"] != "center_confirmed"
                        ][:16],
                        "binding_sample_obligation_count": len(b["sample_obligations"]),
                        "matched_baseline": baseline,
                        "v1_witness_eligible": eligible,
                        "eligibility_reason": reason,
                    })

            # 决策后的 sticky target 与授权任务冲突；即使本拍省略该节点，也要算，因为 omission
            # 的语义是 keep previous target，不是 keep current confirmed config。
            if task_active and req == 300 and effective[0] != 300:
                b = _binding(obs, t, t1, nid, effective)
                soc_age = n.get("soc_evidence_age_s")
                node_evidence = (bool(n.get("heard_last_window"))
                                 and n.get("alive") is not False
                                 and (n.get("soc_wh") or 0.0) >= DENSE_FLOOR_WH
                                 and soc_age is not None and soc_age <= 2 * req)
                candidates.append({
                    **common, "candidate_type": "mission_target_gap",
                    "proposal_field": ["sample"],
                    "legal_evidence": {
                        "global_link_visible": global_link,
                        "heard_last_window": n.get("heard_last_window"),
                        "alive": n.get("alive"), "soc_wh": n.get("soc_wh"),
                        "soc_evidence_age_s": n.get("soc_evidence_age_s"),
                        "node_evidence_holds_r_b_heuristic": bool(node_evidence),
                        "r_b_freshness_bound_s": 2 * req,
                    },
                    "target_source": (
                        "parser_omission_target_reset" if parser_reset
                        else ("raw_explicit" if explicit is not None else "sticky_previous_target")
                    ),
                    "binding_oids": b["sample_unknown_oids"][:16],
                    "matched_baseline": "ordinary mission-compliance / expert-rule filter",
                    "v1_witness_eligible": False,
                    "eligibility_reason": "matched-capability ordinary baseline directly covers this gap",
                })
        for nid, v in (rec.get("targets_after") or {}).items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                prev_targets[nid] = tuple(v[:2])
    return decisions, candidates


def replay_rows(fn: str, seed: int, outage_hours: int):
    """零 LLM 重放该轨迹，返回 (物理汇总, 逐义务行)。"""
    trace = os.path.join(T, fn)
    dec = ReplayDecider(trace)
    pol = AgentMissionPolicy(UP, dec, decision_grid_s=1800, trace_path=None, tag="replay",
                             capacity_wh=0.05, sample_wh=4.7e-4)
    kw = dict(BASE)
    kw.update(seed=seed, outage_hours=outage_hours, collect_rows=True)
    r, inst, _ = run_joint(**kw, mission_schedule=UP, mission_policy_obj=pol)
    rr = r["routine"]
    return ({"svc": round(rr["delivered"] / rr["n"], 4), "delivered": rr["delivered"],
             "n": rr["n"], "missing_collection": rr.get("missing_collection"),
             "missing_delivery": rr.get("missing_delivery"),
             "dead": len(r["survival"].get("dead", []))},
            [x for x in r.get("rows", []) if x.get("kind") == "routine" and not x.get("censored")])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("results", "agent_repairable_loss.json"))
    args = ap.parse_args()
    out = {"script": "code/analysis/agent_repairable_loss.py",
           "contract": "paper/AGENT_RESEARCH.md §6 第一步（既有轨迹的可修性清单，零 API）",
           "denominator": "r42_claim_relabel.FINAL 的 11 份最终轨迹的逐条决策",
           "trace_set": {f"{k[0]}|{k[1]}|s{k[2]}": v for k, v in FINAL.items()},
           "decision_states": list(DECISION_STATES),
           "candidate_types": list(CANDIDATE_TYPES),
           "historical_pending_context": "unavailable_in_r38_trace",
           "per_trace": {}, "items": []}
    decision_counts = collections.Counter()
    candidate_counts = collections.Counter()
    total_dec = 0
    for key, fn in sorted(FINAL.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
        tag, arm, seed = key
        recs = [json.loads(l) for l in open(os.path.join(T, fn), encoding="utf-8") if l.strip()]
        summary = json.load(open(os.path.join(T, fn.replace(".jsonl", ".summary.json")),
                                 encoding="utf-8"))
        outage_hours = summary.get("outage_hours", 16)
        decisions, candidates = analyze_trace(recs, tag)
        phys, rows = replay_rows(fn, seed, outage_hours)
        per_dec = collections.Counter(it["state"] for it in decisions)
        per_cand = collections.Counter(it["candidate_type"] for it in candidates)
        decision_counts.update(per_dec)
        candidate_counts.update(per_cand)
        total_dec += len(recs)
        # 逐条 node/field candidate 连接它在下一 decision 前可能影响的固定义务。
        # observed miss 是结果见证，不是 counterfactual causality。
        for it in candidates:
            nid = it["node"]
            t0, t1 = int(it["t_s"]), int(it["next_decision_s"])
            affected = [x for x in rows
                        if x.get("node_id") == nid
                        and not x.get("censored")
                        and int(x.get("deadline") or -1) >= t0
                        and int(x.get("release_at") or 10**18) < t1]
            missed = [x for x in affected if not x.get("delivered")]
            miss_collect = [x for x in missed if not x.get("collected")]
            it.update({"trace": f"{tag}|{arm}|s{seed}",
                       "action_horizon_s": [t0, t1],
                       "candidate_obligations_in_action_horizon": len(affected),
                       "observed_missed_obligations_in_action_horizon": len(missed),
                       "observed_missing_collection_in_action_horizon": len(miss_collect),
                       "affected_oids": [x.get("oid") for x in affected[:16]],
                       "missed_oids": [x.get("oid") for x in missed[:16]]})
            out["items"].append(it)
        out["per_trace"][f"{tag}|{arm}|s{seed}"] = {
            "trace": fn, "decisions": len(recs),
            "decision_states": dict(per_dec),
            "candidate_types": dict(per_cand),
            "replay_matches_original": phys["delivered"] == summary.get("delivered")
            and phys["dead"] == summary.get("dead"),
            "original": {"svc": summary.get("svc"), "delivered": summary.get("delivered"),
                         "dead": summary.get("dead")},
            "replay": phys,
            "note": "candidate 结果连接按 action horizon；不提供整场 node-level 因果归因"}
        print(f"{tag}|{arm}|s{seed}: 决策 {len(recs):4d}  "
              f"states={dict(per_dec)}  candidates={dict(per_cand)}  "
              f"重放一致={out['per_trace'][f'{tag}|{arm}|s{seed}']['replay_matches_original']}",
              flush=True)
    out["denominator_total_decisions"] = total_dec
    out["decision_state_totals"] = {c: decision_counts.get(c, 0) for c in DECISION_STATES}
    out["candidate_type_totals"] = {c: candidate_counts.get(c, 0) for c in CANDIDATE_TYPES}
    out["survivor_items_total"] = len(out["items"])
    out["survivor_items_with_observed_miss_in_horizon"] = sum(
        1 for it in out["items"]
        if it.get("observed_missed_obligations_in_action_horizon"))
    out["v1_witness_eligible_total"] = sum(
        1 for it in out["items"] if it.get("v1_witness_eligible"))
    print(f"\n分母（逐条决策）= {total_dec}")
    print("decision states:", dict(out["decision_state_totals"]))
    print("candidate types:", dict(out["candidate_type_totals"]))
    print(f"candidate rows = {len(out['items'])}，action horizon 内观察到 miss = "
          f"{out['survivor_items_with_observed_miss_in_horizon']}，"
          f"V1 witness eligible = {out['v1_witness_eligible_total']}")
    path = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("\nsaved", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
