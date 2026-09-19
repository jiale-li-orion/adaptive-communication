#!/usr/bin/env python3
"""Read-only audit of the final v0.6 traces. No model calls or simulation.

Run from any directory; JSON is written to stdout. The api_error field can
describe a failed first attempt followed by a successful retry, so it is not
counted as a final decision failure.
"""
import collections
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "code/v3joint"))
import r38_agent_three_arm as experiment  # sets the existing module paths


def main():
    summaries = json.loads(
        (ROOT / "results/agent_traces/r38_three_arm_summary.json").read_text()
    )
    output = []
    flags = []
    for summary in summaries:
        path = ROOT / "results/agent_traces" / Path(summary["trace"]).name
        counters = collections.Counter()
        for line_number, line in enumerate(path.read_text().splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            counters["decisions"] += 1
            counters["prior_attempt_error_field"] += bool(row.get("api_error"))
            counters["parse_hold"] += row.get("parse_note") == "unparseable->hold"
            counters["llm_failed_hold"] += row.get("parse_note") == "llm_failed->hold"
            try:
                parsed = json.loads(row.get("raw") or "")
                counters["valid_json"] += 1
            except json.JSONDecodeError:
                parsed = {}
                counters["invalid_json"] += 1
            if summary["tag"] != "outage":
                continue
            if not experiment.OUT_LO <= row["t_s"] < experiment.OUT_HI:
                continue
            nodes = row["observation"]["nodes"]
            applied = sum(n.get("cur_sample_s") == 300 for n in nodes)
            dense = any(v[0] == 300 for v in row.get("actions", {}).values())
            note = parsed.get("note", "")
            if dense and applied == 0 and experiment.affirms_live(note):
                flags.append({
                    "trace": str(path.relative_to(ROOT)), "line": line_number,
                    "t_s": row["t_s"], "note": note,
                })
        output.append({
            "tag": summary["tag"], "arm": summary["arm"], "seed": summary["seed"],
            "trace": str(path.relative_to(ROOT)), **dict(counters),
        })
    keys = ("decisions", "parse_hold", "llm_failed_hold", "invalid_json",
            "valid_json", "prior_attempt_error_field")
    totals = {key: sum(row.get(key, 0) for row in output) for key in keys}
    print(json.dumps({"reviewed_commit": "3df2845", "trace_audit": output,
                      "totals": totals, "old_scorer_flagged_notes": flags},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
