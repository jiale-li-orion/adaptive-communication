#!/usr/bin/env python3
"""把**一次运行**的逐事件时间线拉出来，并**严格重放已登记的结果**。

**为什么需要它。** 结果文件只存聚合量（交付/缺采/缺送/下行/不可供电节点小时），**存不下这条链**：
中心看到什么 → 为什么跳过 → 下了什么 → 何时真的生效 → 节点在跑什么配置、还剩多少电、何时死。
"配置生效之后失去有效控制会发生什么"这类问题**只有把链连起来才答得上**。

**重放纪律（2026-09-13 收紧）。** 第一版把 `contract=True` 写死，去重放 `exec_layers=naive`
的登记结果——**三个业务数字偶然对上不代表执行路径相同**。现在：
  * `exec_layer` 从**该 seed/arm 在结果文件里的那一行**读，不是猜的；
  * `config` 里**每一个影响运行的键都必须映射到 `one_seed` 的形参**，映射不到就**报错退出**
    （不静默回默认）；
  * 比较**所有嵌套字段**（业务/能量/通信/执行/账本），排除 `_trace`，逐路径比对，
    任何一处不同就**非零退出**。

Run:
    export PYTHONPATH="$PWD/libs/pylibs"
    python3 code/analysis/trace_seed_timeline.py --tag contcfg_b1.0_out3 --seed 7 --arm ea_nb
"""
from __future__ import annotations

import argparse
import inspect
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for _p in (os.path.join(ROOT, "code", "experiments"),
           os.path.join(ROOT, "code", "instance"),
           os.path.join(ROOT, "code", "monitoring"),
           os.path.join(ROOT, "code", "physics")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from instance_run import one_seed  # noqa: E402

#: `config` 里**不影响这一次运行**的键（输出标签、批量扫描的编排参数）。
#: 这是白名单：任何**不在**里面、又映射不到 `one_seed` 形参的键 → 报错退出。
IGNORE = {"tag", "arms", "seeds", "exec_layers", "dynamic_oracle", "oracle_soc_bins",
          "energy_scale"}
#: 上面逐个手工处理的键（名字与 `one_seed` 形参不同，或需要换算）。
HANDLED = {"backhaul_burst", "uplink_burst", "no_events", "irr_no_source_temp",
           "capacity_wh", "low_wh_per_hour", "charge_min_c"}


def build_kwargs(cfg: dict) -> dict:
    """把登记的 `config` 变成 `one_seed` 的实参。**要么全部映射成功，要么报错退出。**"""
    sig = inspect.signature(one_seed).parameters
    kwargs, unmapped = {}, []
    for k, v in sorted(cfg.items()):
        if k in IGNORE:
            continue
        if k not in sig:
            # 名字与形参不同的四个键**下面单独处理**，不算未映射。
            if k not in HANDLED:
                unmapped.append(k)
            continue
        kwargs[k] = v
    # **四个键在 `main` 里被拆开或取反送进去，必须照抄那一步**——它们的名字与
    # `one_seed` 的形参不同，第一版就是因为这个静默漏掉了 `backhaul_burst`：
    # 于是"重放"跑的是 i.i.d. 链路，而登记结果是突发链路。数字对不上才发现。
    for key, lo, hi in (("backhaul_burst", "burst_p_gb", "burst_p_bg"),
                        ("uplink_burst", "uplink_burst_p_gb", "uplink_burst_p_bg")):
        raw = cfg.get(key)
        if raw:
            a, b = str(raw).split(",")
            kwargs[lo], kwargs[hi] = float(a), float(b)
        else:
            kwargs[lo], kwargs[hi] = None, None
    # `--charge-min-c` 在 `main` 里从字符串转成 float，`off` 转成 None。照抄。
    raw_cmc = cfg.get("charge_min_c")
    if raw_cmc is not None:
        kwargs["charge_min_c"] = None if raw_cmc == "off" else float(raw_cmc)
    if cfg.get("no_events") is not None:
        kwargs["with_events"] = not cfg["no_events"]
    if cfg.get("irr_no_source_temp") is not None:
        kwargs["irr_source_temp"] = not cfg["irr_no_source_temp"]
    # `main` 把 `--energy-scale` 乘进了这两个量之后才调用；`one_seed` 内部只再乘
    # `sample_wh` 与 `idle_wh_per_tick`。这里必须与 `main` 完全一致，否则重放的是另一个实例。
    kwargs["capacity_wh"] = cfg["capacity_wh"] * cfg["energy_scale"]
    kwargs["low_wh_per_hour"] = cfg["low_wh_per_hour"] * cfg["energy_scale"]
    if unmapped:
        raise SystemExit(
            f"**拒绝静默重放**：config 里这些键在 `one_seed` 里没有对应形参——{unmapped}。\n"
            f"  它们可能影响运行（例如 burst 参数），静默丢弃会让重放悄悄跑成另一组条件。\n"
            f"  请把它们接进 `one_seed`，或显式加进本脚本的 IGNORE 白名单并说明理由。")
    return kwargs


def diff_vs_registered(reg, fresh, path=""):
    """与**登记行**比较：只比"登记里有的键"。

    登记文件可能**缺少后来才加的字段**（`intent_reason`、`skip_reasons` 就是），
    那是**新增**不是**不一致**。把"新增"当成不一致，会让每一次重放都误报——
    `rerun_from_config.py` 已经踩过一次同一个坑。
    """
    out = []
    if isinstance(reg, dict) and isinstance(fresh, dict):
        for k in sorted(set(reg), key=str):
            if k == "_trace":
                continue
            out += diff_vs_registered(reg[k], fresh.get(k), f"{path}.{k}" if path else str(k))
    elif isinstance(reg, list) and isinstance(fresh, list):
        if len(reg) != len(fresh):
            out.append(f"{path}[长度 {len(reg)}→{len(fresh)}]")
        else:
            for i, (x, y) in enumerate(zip(reg, fresh)):
                out += diff_vs_registered(x, y, f"{path}[{i}]")
    elif reg != fresh:
        out.append(f"{path}: 登记 {reg!r} ≠ 重放 {fresh!r}")
    return out


def deep_diff(a, b, path=""):
    """递归比较两个结果，返回所有不同的路径。`_trace` 不参与比较。"""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        # 键可能是 `int`（例如按 tick 索引的采能轨迹）与 `str` 混在一起，按 `str` 排序。
        for k in sorted(set(a) | set(b), key=str):
            if k == "_trace":
                continue
            out += deep_diff(a.get(k), b.get(k), f"{path}.{k}" if path else str(k))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}[长度 {len(a)}→{len(b)}]")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                out += deep_diff(x, y, f"{path}[{i}]")
    elif a != b:
        out.append(f"{path}: {a!r} ≠ {b!r}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True, help="已登记的结果文件 tag（不带 instance_ 前缀）")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--node", default="", help="只打印这台节点；空表示全部")
    ap.add_argument("--dump", default="", help="把完整时间线写到这个路径（jsonl）")
    args = ap.parse_args()

    path = os.path.join(ROOT, "results", f"instance_{args.tag}.json")
    doc = json.load(open(path, encoding="utf-8"))
    cfg = dict(doc["config"])

    rows = [r for r in doc["runs"] if r["arm"] == args.arm and r["seed"] == args.seed]
    if not rows:
        raise SystemExit(f"{args.tag} 里没有 arm={args.arm} seed={args.seed} 这一行")
    reg = rows[0]
    layer = reg.get("exec_layer") or "naive"
    if layer not in ("naive", "contract", "atomic"):
        raise SystemExit(f"未知 exec_layer {layer!r}")

    kwargs = build_kwargs(cfg)
    kwargs.pop("trace", None)
    # **执行层从登记行读，不猜。** `contract` 与 `atomic` 都带契约字段；`atomic` 另开整代生效。
    kwargs["contract"] = layer in ("contract", "atomic")
    kwargs["atomic"] = layer == "atomic"
    kwargs["exec_label"] = layer
    # 登记时用了 `--dynamic-oracle` 的那些运行带着真上界；重放必须给它一个（空的）记忆化表，
    # 否则这一列是 None 而登记值是数字——第一版就是这么"报不一致"的。
    kwargs["oracle_cache"] = {} if cfg.get("dynamic_oracle") else None

    print(f"[重放] tag={args.tag} seed={args.seed} arm={args.arm} exec_layer={layer}"
          f"（读自登记行）")

    plain = one_seed(args.seed, arm=args.arm, trace=False, **kwargs)
    traced = one_seed(args.seed, arm=args.arm, trace=True, **kwargs)

    # **先过一遍 JSON。** 登记行是从磁盘读回来的，`int` 键已经变成 `str`、`nan`/`inf` 也已经
    # 落到字符串上。直接拿内存里的对象去比，会得到一整片假差异（`delivery_cdf` 的键就是这种）。
    norm = lambda d: json.loads(json.dumps({k: v for k, v in d.items() if k != "_trace"},
                                           default=str, ensure_ascii=False))
    a, b = norm(plain), norm(traced)
    diffs = diff_vs_registered(reg, a)
    tdiff = deep_diff(a, b)
    print(f"[核对] 与登记行**逐字段**一致: {not diffs}")
    for d in diffs[:10]:
        print("   ", d)
    print(f"[核对] 开 trace 后逐字段相同: {not tdiff}")
    for d in tdiff[:10]:
        print("   ", d)
    if diffs or tdiff:
        print("\n**重放不一致——上面的时间线不能用来做因果归因。**")
        return 1

    ev = traced["_trace"]
    if args.dump:
        with open(args.dump, "w", encoding="utf-8") as fh:
            for e in ev:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")
        print(f"[输出] 时间线 {args.dump}（{len(ev)} 条事件）")

    nodes = sorted({e[1] for e in ev})
    if args.node:
        nodes = [n for n in nodes if n == args.node]
    for nid in nodes:
        mine = [e for e in ev if e[1] == nid]
        states = [e for e in mine if e[2] == "state"]
        if not states:
            continue
        segs, cur = [], None
        for e in states:
            key = (e[3], e[4])
            if cur is None or key != cur[0]:
                if cur is not None:
                    segs.append(cur)
                cur = [key, e[0], e[0], e[5], e[5]]
            else:
                cur[2] = e[0]
                cur[4] = e[5]
        if cur is not None:
            segs.append(cur)
        plans = [e for e in mine if e[2] == "plan"]
        apps = [e for e in mine if e[2] == "applied"]
        dead = next((e[0] for e in states if not e[6]), None)
        print(f"\n=== {nid} ===  意图 {len(plans)} 条、生效写入 {len(apps)} 次、"
              f"死亡 {'—' if dead is None else str(dead) + 's'}")
        print("  生效配置段（起–止, 采样 s, 上报 s, 段内 SoC 起→止）:")
        for k, t0, t1, s0, s1 in segs:
            print(f"    {t0:>6}s–{t1:>6}s  采样 {k[0]:>5}s  上报 {k[1]:>5}s  "
                  f"SoC {s0:.4f} → {s1:.4f}")
        if plans:
            print("  意图(时刻, 字段, 值, 中心当时看到的电量):")
            for e in plans[:24]:
                v = "—" if e[3] is None else f"{e[3]:.4f}"
                print(f"    {e[0]:>6}s  {e[4]:<22} {e[5]:>5}  soc_seen={v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
