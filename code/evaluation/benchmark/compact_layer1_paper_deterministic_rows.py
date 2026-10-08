#!/usr/bin/env python3
"""Compact resumable deterministic-paper JSONL into one canonical row per ID.

The execution runner appends rows immediately for crash-safe resume. Historical
partial runs can therefore leave byte-identical duplicate row IDs. This tool
preserves the append-only raw log and creates a sorted canonical table only if
every duplicate occurrence is semantically identical.
"""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/"results/benchmark/layer1-paper-deterministic-test"
RAW=BASE/"rows.jsonl"
CANON=BASE/"rows.canonical.jsonl"
AUDIT=BASE/"compaction-audit.json"


def _sha(path:Path)->str:
    return sha256(path.read_bytes()).hexdigest()


def _canon(row:dict)->str:
    return json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(",",":"))


def main()->int:
    by=defaultdict(list)
    physical=0
    with RAW.open(encoding="utf-8") as fh:
        for lineno,line in enumerate(fh,1):
            if not line.strip(): continue
            physical+=1
            row=json.loads(line)
            by[str(row["row_id"])].append((lineno,row))
    mismatches=[]; duplicate_ids=[]
    for row_id,vals in sorted(by.items()):
        forms={_canon(row) for _line,row in vals}
        if len(vals)>1: duplicate_ids.append(row_id)
        if len(forms)!=1:
            mismatches.append({"row_id":row_id,"lines":[line for line,_ in vals]})
    if mismatches:
        raise AssertionError({"duplicate_semantic_mismatches":mismatches[:10],"count":len(mismatches)})

    with CANON.open("w",encoding="utf-8") as fh:
        for row_id in sorted(by):
            fh.write(json.dumps(by[row_id][0][1],ensure_ascii=False,sort_keys=True)+"\n")

    kinds={}
    for vals in by.values():
        kind=str(vals[0][1]["kind"]); kinds[kind]=kinds.get(kind,0)+1
    payload={
        "stage":"LAYER1_PAPER_DETERMINISTIC_ROW_COMPACTION",
        "raw_rows":physical,
        "canonical_rows":len(by),
        "duplicate_row_ids":len(duplicate_ids),
        "duplicate_extra_rows":physical-len(by),
        "semantic_mismatch_duplicate_ids":len(mismatches),
        "max_multiplicity":max(len(v) for v in by.values()),
        "canonical_kind_counts":dict(sorted(kinds.items())),
        "raw_sha256":_sha(RAW),
        "canonical_sha256":_sha(CANON),
        "claim_boundary":[
            "The append-only raw execution log is preserved unchanged.",
            "Compaction removes only byte-semantically identical duplicate row IDs; any disagreement would abort instead of selecting a preferred result.",
            "All paper statistics must use rows.canonical.jsonl."
        ],
    }
    assert payload["canonical_rows"]==960,payload
    assert payload["canonical_kind_counts"]=={"evaluator_only_oracle":210,"online_baseline":750},payload
    AUDIT.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"audit":str(AUDIT),**payload},sort_keys=True)); return 0


if __name__=="__main__": raise SystemExit(main())
