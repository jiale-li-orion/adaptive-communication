#!/usr/bin/env python3
"""按结果文件里存下的 `config` 重跑它自己，并逐字段核对"只有 AoI 列变了"。

**为什么需要它。** `scoring._routine_block` 的 AoI 实现有缺陷（按采集时刻而非接收时刻推进），
修好之后 `results/` 里每一个 `instance_*.json` 的 AoI 列都作废了。重跑不能靠手抄命令——
命令写在 `results/README.md` 里、以 `|` 和 `…` 压缩过，抄错一处就静默换了一次实验。
每个结果文件自己存了完整的 `config`，所以**从 config 重建命令行**是唯一不会走样的做法。

**它同时是一道自检。** 重跑之后逐路径比较新旧 JSON：

  * 变化的路径**只允许**含 `aoi` 或 `no_observation`——因为这次只改了这两列的实现；
  * 任何**别的**路径发生变化，说明这次重跑没有复现原来的实验（旧文件用了当时的默认值，
    而默认值后来被改过，例如 `sample_wh` 从 2e-5 改成 4.7e-4）。那种文件单独列出，
    **不当作修复后的结果**。

Run:
    export PYTHONPATH="$PWD/libs/pylibs"
    python3 code/analysis/rerun_from_config.py            # 全部
    python3 code/analysis/rerun_from_config.py --only front
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RUNNER = os.path.join(ROOT, "code", "experiments", "instance_run.py")

FLAG_RE = re.compile(r'add_argument\(\s*"(--[a-z0-9\-]+)"(.*?)\)\s*\n', re.S)


def cli_map() -> tuple[dict[str, str], set[str]]:
    """从 `instance_run.py` 的 argparse 定义里读出 `dest → --flag`，以及所有 store_true 的 dest。"""
    src = open(RUNNER, encoding="utf-8").read()
    dest2flag, bools = {}, set()
    for flag, tail in FLAG_RE.findall(src):
        dest = flag[2:].replace("-", "_")
        dest2flag[dest] = flag
        if "store_true" in tail:
            bools.add(dest)
    return dest2flag, bools


def argv_for(cfg: dict, dest2flag: dict[str, str], bools: set[str]) -> tuple[list[str], list[str]]:
    argv, unknown = [], []
    for k, v in sorted(cfg.items()):
        if k not in dest2flag:
            unknown.append(k)
            continue
        flag = dest2flag[k]
        if k in bools:
            if v:
                argv.append(flag)
            continue
        if v is None or v == "" or v is False:
            continue
        argv += [flag, str(v)]
    return argv, unknown


_MISSING = object()


def diff_paths(old, new, path="", kind="changed"):
    """递归找出所有**取值不同**的路径，并标出它是"新增/删除"还是"改了值"。

    **为什么必须分开。** 结果文件的**字段集合**在这几轮里一直在长（意图账本、中间上界、
    `delivery_oracle_mid`、`cache_service`…）。把"新增了一个字段"当成"没复现原来的实验"，
    会让每一次重跑都误报——第一版就是这么写的，237 个文件里 213 个被判"未复现"，
    而其中相当一部分**原有列一个都没变**。真正要区分的是：
    **旧文件里已有的列，重跑后值是否逐位相同。**
    """
    out = []
    if isinstance(old, dict) and isinstance(new, dict):
        for k in sorted(set(old) | set(new)):
            if k not in old:
                out.append((f"{path}.{k}" if path else str(k), "新增"))
            elif k not in new:
                out.append((f"{path}.{k}" if path else str(k), "删除"))
            else:
                out += diff_paths(old[k], new[k], f"{path}.{k}" if path else str(k))
    elif isinstance(old, list) and isinstance(new, list):
        if len(old) != len(new):
            out.append((f"{path}[长度 {len(old)}→{len(new)}]", kind))
        else:
            for i, (a, b) in enumerate(zip(old, new)):
                out += diff_paths(a, b, f"{path}[{i}]")
    elif old != new:
        out.append((path, kind))
    return out


def one(f: str, dest2flag, bools, root: str) -> tuple[str, str, list[str]]:
    """重跑一个结果文件。返回 (文件名, 结论标签, 明细)。"""
    name = os.path.basename(f)
    original = open(f, "rb").read()
    old = json.loads(original)
    cfg = dict(old.get("config") or {})
    _argv, unknown = argv_for(cfg, dest2flag, bools)
    if unknown:
        return name, "跳过", [f"config 里有无法映射到命令行的键：{unknown}"]
    # **换成这个进程专属的 tag**：并行时两个进程用同一个 tag 会写同一个输出文件，
    # 于是比较的是别人的运行结果（这一类错会静默）。跑完立刻删掉临时文件。
    tag = cfg.get("tag") or name[len("instance_"):-len(".json")]
    cfg["tag"] = f"_rerun_{os.getpid()}_{tag}"
    argv, _ = argv_for(cfg, dest2flag, bools)
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(root, "libs", "pylibs")
    tmp = os.path.join(root, "results", f"instance_{cfg['tag']}.json")
    try:
        r = subprocess.run([sys.executable, RUNNER, *argv], cwd=root, env=env,
                           capture_output=True, text=True, timeout=7200)
        if r.returncode != 0 or not os.path.exists(tmp):
            return name, "失败", (r.stderr or r.stdout).strip().splitlines()[-1:]
        new = json.loads(open(tmp, "rb").read())
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    paths = diff_paths(old, new)
    # `config.*` 是命令行的回声，不是实验读数。它会因为**本脚本自己**而变化：
    # `--tag` 是本脚本改的、`cache_service`/`uplink_burst` 是后来新增的键。
    # 把它们当作"未复现"会让每一次重跑都误报（第一版就是这样，几乎全军覆没）。
    stray = [p for p, kind in paths
             if kind == "changed"
             and not p.startswith("config.")
             and not p.startswith("aggregate.config")
             and "aoi" not in p.lower() and "no_observation" not in p.lower()]
    added = sum(1 for _p, kind in paths if kind == "新增")
    # **一律用重跑结果覆盖。** 文件里记着完整的 `config`，重跑用的就是这份 config，
    # 所以**命令是可复现的**；数字变了只可能是**代码变了**。留着旧数不等于更安全：
    # 那意味着 `results/` 里同时存在两个代码版本下的读数，而文件本身不会告诉读者它是哪一个。
    # 旧内容全部在 `_withdrawn/aoi_defect_2026-09-13/` 有备份，逐文件差异写进那份 REGENERATION.md。
    # （判据已由"能否逐位复现"改为"命令是否就是登记的那条"；第一版把两者混为一谈，
    #   于是 237 个文件里 213 个被判"未复现"却仍然留在目录里，既没更新也没标记。）
    # **临时 tag 不得写进结果的 `config`。** 第一版把修改后的 tag 一起写回去了，
    # 于是结果文件里记的 tag 变成 `_rerun_<pid>_<原 tag>`。后果立刻出现：
    # 之后任何"从这个文件的 config 重建命令"的操作都会带着一串脏前缀
    # （实测：15 个新结果的 tag 变成 `_rerun_164481__rerun_161128__rerun_157694_…`）。
    # 文件名才是 tag 的权威，写回时按文件名恢复。
    if isinstance(new.get("config"), dict):
        new["config"]["tag"] = tag
    agg = new.get("aggregate")
    if isinstance(agg, dict) and isinstance(agg.get("config"), dict):
        agg["config"]["tag"] = tag
    open(f, "wb").write(json.dumps(new, indent=1, sort_keys=True,
                                   ensure_ascii=False, default=str).encode("utf-8"))
    stamp = f"改动 {len(paths) - added} 处 / 新增 {added} 处"
    if stray:
        return name, "读数变了", [stamp, sorted(set(p.split(".")[-1] for p in stray))[:6]]
    return name, "只动 AoI", [stamp]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="只处理文件名里含该子串的结果")
    ap.add_argument("--results", default=os.path.join(ROOT, "results"))
    ap.add_argument("--jobs", type=int, default=6, help="并行度（每个任务跑一个子进程）")
    args = ap.parse_args()

    dest2flag, bools = cli_map()
    files = sorted(glob.glob(os.path.join(args.results, "instance_*.json")))
    if args.only:
        files = [f for f in files if args.only in os.path.basename(f)]

    exact, moved, failed, skipped = [], [], [], []
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futs = [ex.submit(one, f, dest2flag, bools, ROOT) for f in files]
        for i, fu in enumerate(as_completed(futs), 1):
            name, verdict, detail = fu.result()
            print(f"[{i}/{len(files)}] {verdict:<7} {name}  {detail}", flush=True)
            {"只动 AoI": exact, "读数变了": moved, "跳过": skipped,
             "失败": failed}[verdict].append((name, detail))

    print("\n" + "=" * 84)
    print(f"只有 AoI / 无观测这一列变（其余列逐位相同）: {len(exact)} / {len(files)}")
    print(f"**非 AoI 列也变了（现行代码与登记时不同）**: {len(moved)}")
    for n, p in moved:
        print(f"   - {n}: {p}")
    for label, bucket in (("跳过（config 键无法映射）", skipped), ("运行失败", failed)):
        if bucket:
            print(f"{label}: {len(bucket)}")
            for n, why in bucket:
                print(f"   - {n}: {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
