"""v5 三条件在**传统臂**下的读数：给 LLM 结果做控制。

**为什么必须有这个脚本。** `llm_naive_v5` 全量跑完后，`polar_c0.05` 档是
**779 次调用、0 次动作、服务 0.0/168**。单看这一列，最自然的误读是"模型什么都没做"。
但**服务 0 完全可能来自条件本身**——如果这条链路对**任何**策略都送不到中心，
那 0 就是实例的性质，不是模型的行为。§28/§31 的纪律明确禁止把条件造成的零
记成 agent 推理错误，所以必须先把同一条件下的传统臂跑出来。

**为什么必须跑多个种子（第一版只跑了 seed 0，结论下得过重）。**
`polar_c0.05` 的两态突发参数是回传 `(0.00846, 0.0138)`、接入 `(0.0079, 0.0158)`，
**平均坏突发 = 1/p_bad→good ≈ 72.5 h（回传）/ 63.3 h（接入）**，而任务只有 **12 h**。
⇒ 一旦种子从"坏"态起链，**整个 12 h 都落在同一次坏突发里**，服务必然是 0；
从"好"态起链则接近满服务。**这个条件是双峰的**，单一种子什么都说明不了。

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
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20,
                    help="跑几个种子。**必须 >1**：该条件是双峰的，单种子会给出误导性的 0")
    args = ap.parse_args()
    out: dict = {"seeds": args.seeds, "arms": list(ARMS), "by_tag": {}}
    print(f"{'tag':<14}{'arm':<10}{'服务':>6}{'分母':>5}{'缺采':>6}{'缺送':>6}{'AoI s':>9}")
    for tag in TAGS:
        cfg = json.load(open(_os.path.join(RES, f"instance_{tag}.json"),
                             encoding="utf-8"))["config"]
        kw = build_kwargs(dict(cfg))
        kw.pop("trace", None)
        rows = {}
        for arm in ARMS:
            per_seed = [one_seed(s, arm=arm, **kw)["routine"] for s in range(args.seeds)]
            svc = [r["delivered"] for r in per_seed]
            rows[arm] = {
                "service": sum(svc) / len(svc), "n": per_seed[0]["n"],
                "service_per_seed": svc,
                "zero_seeds": sum(1 for v in svc if v == 0),
                "missing_collection": sum(r["missing_collection"] for r in per_seed) / len(per_seed),
                "missing_delivery": sum(r["missing_delivery"] for r in per_seed) / len(per_seed),
                "aoi_mean_s": next((r["aoi_mean_s"] for r in per_seed
                                    if r["aoi_mean_s"] is not None), None),
            }
            print(f"{tag:<14}{arm:<10}{rows[arm]['service']:>6.1f}{rows[arm]['n']:>5}"
                  f"{rows[arm]['missing_collection']:>6.1f}{rows[arm]['missing_delivery']:>6.1f}"
                  f"{rows[arm]['zero_seeds']:>6}/{len(svc)} 个种子为 0")
        out["by_tag"][tag] = {
            "config_source": f"results/instance_{tag}.json", "rows": rows,
            "all_arms_service_zero": all(v["service"] == 0 for v in rows.values()),
            "all_arms_zero_at_seed0": all(v["service_per_seed"][0] == 0 for v in rows.values()),
        }
        print()
    path = _os.path.join(RES, "llm_v5_condition_baselines.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"wrote {path}")
    for tag, blk in out["by_tag"].items():
        if blk["all_arms_service_zero"]:
            print(f"  ** {tag}: 五条传统臂**跨全部种子**都是 0 ⇒ 该档对任何策略都不交付，"
                  f"LLM 的 noop 不得记成推理错误。")
        elif blk["all_arms_zero_at_seed0"]:
            zs = [v["zero_seeds"] for v in blk["rows"].values()]
            print(f"  ** {tag}: **该档是双峰的**——协议冻结的 seed 0 上五条传统臂全为 0，"
                  f"但跨种子看并非恒零（逐臂为 0 的种子数 {zs}／{out['seeds']}）。"
                  f"⇒ 单种子读数**不得**当作'该条件不交付'的证据；"
                  f"这是'坏突发平均 72.5 h ≫ 12 h 任务'造成的离散，不是模型行为。")


if __name__ == "__main__":
    main()
