#!/usr/bin/env python3
"""Render the Q11 review packet with machine-prechecked evidence attached."""
from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R = ROOT / "results/benchmark"


def _find_check(sample: dict, group: str, name: str) -> dict | None:
    for row in sample["checks"].get(group, []):
        if row["check"] == name:
            return row
    return None


def main() -> int:
    human = json.loads((R / "layer1-human-source-audit-v0.1.json").read_text(encoding="utf-8"))
    pre = json.loads((R / "layer1-human-source-machine-preaudit-v0.1.json").read_text(encoding="utf-8"))
    pre_by_id = {str(x["sample_id"]): x for x in pre["samples"]}

    lines = [
        "# Layer-1 Q11 Human / Source Review Packet v0.1",
        "",
        "状态：**BLOCKED_PENDING_HUMAN_REVIEW**",
        "",
        f"机器预审：{pre['machine_pass_count']} / {pre['sample_count']} MACHINE_PASS；机器预审不能替代 reviewer 签字。",
        "",
        "人工 reviewer 对每条只需要判断五项：source extraction、authority/time、task identity、oracle success set、evaluator trace。任何 FAIL 都阻塞 Q11。",
        "",
    ]
    for sample in human["samples"]:
        sid = str(sample["sample_id"])
        p = pre_by_id[sid]
        source_detail = _find_check(p, "source_extraction_semantics", "all_declared_profiles_exist_and_include_T1")
        task_detail = _find_check(p, "source_extraction_semantics", "task_contract_matches_DB44_source_expansion")
        exact_detail = _find_check(p, "oracle_success_set", "exact_classification_matches_role_expectation")
        v0v7_detail = _find_check(p, "oracle_success_set", "V0_V7_disposition_matches_role_expectation")
        v8_detail = _find_check(p, "oracle_success_set", "V8_disposition_matches_hard_survivor")
        replay_detail = _find_check(p, "evaluator_trace", "all_solvable_physical_witnesses_replay_successfully")
        lines.extend([
            f"## {sid} · `{sample['recipe_id']}`",
            "",
            f"- split / role: `{sample['split']}` / `{sample['candidate_role']}`",
            f"- task: `{sample['task_case_id']}`",
            f"- geometry cluster: `{sample['geometry_shape_cluster']}`",
            f"- hardness: {', '.join(f'`{x}`' for x in sample['hardness']) or '`NONE`'}",
            f"- machine groups: " + ", ".join(f"`{k}={v}`" for k, v in p["group_status"].items()),
        ])
        if task_detail:
            d = task_detail["detail"]
            r = d["recipe"]
            lines.append(
                f"- source-expanded task: grade `{r['monitoring_grade']}`, warning `{r['warning_state']}`, report interval `{r['report_interval_s']}s`"
            )
        if exact_detail:
            d = exact_detail["detail"]
            lines.append(f"- exact role check: expected `{d['expected']}`, actual `{d['actual']}`")
        if v0v7_detail:
            d = v0v7_detail["detail"]
            lines.append(f"- V0–V7: expected `{d['expected']}`, actual `{d['actual']}`")
        if v8_detail:
            d = v8_detail["detail"]
            lines.append(f"- V8: expected `{d['expected']}`, actual `{d['actual']}`")
        if replay_detail:
            d = replay_detail["detail"]
            lines.append(f"- evaluator replay: `{d['replayed_world_count']}` solvable world witness(es), machine failures `{len(d['failures'])}`")
        if source_detail:
            lines.append("- source evidence:")
            for profile, meta in source_detail["detail"].items():
                refs = meta.get("source_refs", [])
                ref_text = "; ".join(
                    f"{x.get('source_id')} [{x.get('source_class')}] locator={x.get('locator')!r} snapshot={x.get('snapshot_ref')!r}"
                    for x in refs
                )
                lines.append(f"  - `{profile}` — {ref_text}")
                if meta.get("unknowns"):
                    lines.append(f"    - unresolved/source gaps to inspect: `{json.dumps(meta['unknowns'], ensure_ascii=False)}`")
        lines.extend([
            "",
            "Reviewer:",
            "",
            "- [ ] source extraction semantics PASS   - [ ] FAIL",
            "- [ ] authority / priority / time semantics PASS   - [ ] FAIL",
            "- [ ] task family identity PASS   - [ ] FAIL",
            "- [ ] oracle success set PASS   - [ ] FAIL",
            "- [ ] evaluator trace PASS   - [ ] FAIL",
            "- reviewer name:",
            "- notes:",
            "",
        ])
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
