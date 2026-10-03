#!/usr/bin/env python3
"""example_metric.py — 模板的示例实验：一条确定性、可复现、无需凭据的最小链路。

它存在的理由不是产生科学结论，而是让骨架的接线可被验证：脚本产出结果文件，结果文件喂给
表格生成器，主张表指向两者，检查核对三者一致。换成真实实验时保持同样的四段接线。

Run: python3 code/experiments/example_metric.py
"""
from __future__ import annotations

import json
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "results", "example_metric.json")

SEEDS = [0, 1, 2, 3, 4]


def measure(seed: int) -> float:
    """占位测量：确定性伪随机，不依赖任何外部状态。"""
    return ((seed * 2654435761) % 1000) / 1000.0


def main() -> int:
    per_seed = {str(s): round(measure(s), 4) for s in SEEDS}
    vals = list(per_seed.values())
    out = {
        "run": "example_metric",
        "seeds": SEEDS,
        "per_seed": per_seed,
        "summary": {"mean": round(statistics.mean(vals), 4),
                    "min": min(vals), "max": max(vals)},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print(f"写出 {os.path.relpath(OUT, ROOT)}  mean={out['summary']['mean']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
