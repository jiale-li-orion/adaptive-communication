"""v1.2 minimal probe 的配对统计：同种子配对差 + bootstrap 区间 + Student-t 区间并列。

与 `code/analysis/paired_ci.py` 同一原则：**配对、不做两个独立均值**；零是逐种子断言。
这里额外给一个配对 bootstrap（对逐种子差值序列有放回重采样），与 t 区间互相印证——
两者都排除 0 才称"显著"，避免单一区间口径下结论。
"""
from __future__ import annotations

import random as _random

from paired_ci import paired as _t_paired


def paired_diff(a: list[float], b: list[float]) -> list[float]:
    n = min(len(a), len(b))
    return [a[i] - b[i] for i in range(n)]


def bootstrap_mean_ci(diffs: list[float], n_boot: int = 10000,
                      seed: int = 20260914, alpha: float = 0.05) -> dict:
    """配对 bootstrap：对差值序列有放回抽 n 个、取均值，重复 n_boot 次，取分位区间。"""
    n = len(diffs)
    if n == 0:
        return {"n": 0, "mean": None, "lo": None, "hi": None}
    rng = _random.Random(seed)
    mean = sum(diffs) / n
    boots = []
    for _ in range(n_boot):
        acc = 0.0
        for _j in range(n):
            acc += diffs[rng.randrange(n)]
        boots.append(acc / n)
    boots.sort()
    lo = boots[int((alpha / 2) * n_boot)]
    hi = boots[int((1 - alpha / 2) * n_boot) - 1]
    pos = sum(1 for d in diffs if d > 0)
    neg = sum(1 for d in diffs if d < 0)
    zer = n - pos - neg
    return {"n": n, "mean": round(mean, 6), "lo": round(lo, 6), "hi": round(hi, 6),
            "excludes_zero": not (lo <= 0.0 <= hi),
            "signs": [pos, neg, zer]}


def paired_compare(a: list[float], b: list[float], n_boot: int = 10000,
                   seed: int = 20260914) -> dict:
    """a−b 的完整配对比较：均值差、bootstrap CI、t CI、胜负平。"""
    diffs = paired_diff(a, b)
    boot = bootstrap_mean_ci(diffs, n_boot=n_boot, seed=seed)
    tst = _t_paired(a, b)
    return {
        "n": len(diffs),
        "mean_diff": boot["mean"],
        "bootstrap_lo": boot["lo"], "bootstrap_hi": boot["hi"],
        "bootstrap_excludes_zero": boot["excludes_zero"],
        "t_lo": round(tst["lo"], 6), "t_hi": round(tst["hi"], 6),
        "t_excludes_zero": not (tst["lo"] <= 0.0 <= tst["hi"]),
        "win_loss_tie": boot["signs"],
        "both_exclude_zero": bool(boot["excludes_zero"] and tst["lo"] <= tst["hi"]
                                  and not (tst["lo"] <= 0.0 <= tst["hi"]))}
