"""v5 三条件在**传统臂**下的读数：给 LLM 结果做控制。

**为什么必须有这个脚本。** `llm_naive_v5` 全量跑完后，`polar_c0.05` 档是
**779 次调用、0 次动作、服务 0.0/168**。单看这一列，最自然的误读是"模型什么都没做"。
但**服务 0 完全可能来自条件本身**——如果这条链路对**任何**策略都送不到中心，
那 0 就是实例的性质，不是模型的行为。§28/§31 的纪律明确禁止把条件造成的零
记成 agent 推理错误，所以必须先把同一条件下的传统臂跑出来。

    python3 code/analysis/v5_condition_baselines.py

条件**不重新发明**：直接读 `results/instance_<tag>.json` 的 `config` 块，
并用与 `llm_naive_baseline.py` **同一个** `build_kwargs` 映射，因此重放的是**同一个实例**，
不是"差不多的实例"。
"""
from __future__ import annotations

import json
import os as _os
import sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, _CODE,
           *(_os.path.join(_CODE, d) for d in
             ("physics", "runtime", "experiments", "analysis", "monitoring", "instance"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

from trace_seed_timeline import build_kwargs        # noqa: E402
from instance_run import one_seed                   # noqa: E402

RES = _os.path.normpath(_os.path.join(_CODE, "..", "results"))
#: 与 `llm_naive_v5.json` 的 `conditions` 逐字一致。
TAGS = ("adm_noout", "adm_out3", "polar_c0.05")
ARMS = ("local", "aoi", "ea_nb", "ea_aoi", "eh_aoi")
SEED = 0                                            # 协议 `env_seed`


def main() -> None:
    out: dict = {"seed": SEED, "arms": list(ARMS), "by_tag": {}}
    print(f"{'tag':<14}{'arm':<10}{'服务':>6}{'分母':>5}{'缺采':>6}{'缺送':>6}{'AoI s':>9}")
    for tag in TAGS:
        cfg = json.load(open(_os.path.join(RES, f"instance_{tag}.json"),
                             encoding="utf-8"))["config"]
        kw = build_kwargs(dict(cfg))
        kw.pop("trace", None)
        rows = {}
        for arm in ARMS:
            d = one_seed(SEED, arm=arm, **kw)
            r = d["routine"]
            rows[arm] = {"service": r["delivered"], "n": r["n"],
                         "missing_collection": r["missing_collection"],
                         "missing_delivery": r["missing_delivery"],
                         "aoi_mean_s": r["aoi_mean_s"]}
            print(f"{tag:<14}{arm:<10}{r['delivered']:>6}{r['n']:>5}"
                  f"{r['missing_collection']:>6}{r['missing_delivery']:>6}"
                  f"{(r['aoi_mean_s'] or -1):>9.0f}")
        out["by_tag"][tag] = {"config_source": f"results/instance_{tag}.json",
                              "rows": rows,
                              "all_arms_service_zero": all(v["service"] == 0
                                                           for v in rows.values())}
        print()
    path = _os.path.join(RES, "llm_v5_condition_baselines.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"wrote {path}")
    for tag, blk in out["by_tag"].items():
        if blk["all_arms_service_zero"]:
            print(f"  ** {tag}: 五条传统臂全部 0 服务 ⇒ 该档对任何策略都不交付，"
                  f"LLM 的 noop 不得记成推理错误。")


if __name__ == "__main__":
    main()
