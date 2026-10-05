#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SRC=ROOT/'results/benchmark/layer1-human-source-audit-v0.1.json'


def main()->int:
    d=json.loads(SRC.read_text(encoding='utf-8'))
    lines=[
        '# Layer-1 Human / Source Audit Worksheet v0.1',
        '',
        f"状态：{d['status']}  ",
        f"样本数：{d['sample_count']}  ",
        '',
        '每条样本必须由 reviewer 独立核查 source extraction、authority/time semantics、task identity、oracle success set 与 evaluator trace。自动脚本不能替代此签字。',
        '',
    ]
    current=None
    for s in d['samples']:
        split=s['split']
        if split!=current:
            current=split
            lines += [f'## {split.upper()}', '']
        lines += [
            f"### {s['sample_id']} · `{s['recipe_id']}`",
            '',
            f"- role: `{s['candidate_role']}`",
            f"- task: `{s['task_case_id']}`",
            f"- geometry cluster: `{s['geometry_shape_cluster']}`",
            f"- source profiles: {', '.join('`'+x+'`' for x in s['source_profiles'])}",
            f"- hardness: {', '.join('`'+x+'`' for x in s['hardness']) or 'none'}",
            '- source extraction semantics: [ ] PASS  [ ] FAIL',
            '- authority / priority / time semantics: [ ] PASS  [ ] FAIL',
            '- task family identity: [ ] PASS  [ ] FAIL',
            '- oracle success set: [ ] PASS  [ ] FAIL',
            '- evaluator trace: [ ] PASS  [ ] FAIL',
            '- reviewer:',
            '- notes:',
            '',
        ]
    print('\n'.join(lines))
    return 0


if __name__=='__main__': raise SystemExit(main())
