#!/usr/bin/env python3
"""把 NASA POWER 的原始 JSON 派生成本实例读的 CSV，并核对哈希与观测区间。

**为什么要单独一个脚本**：`data/` 不入库，原始 JSON 不在仓库里。派生这一步必须可复现、
可核对，否则"来源派生"四个字就没有落点。脚本会打印 SOURCE.md 里记录的那几个数，对不上就报错。

Run: python3 code/analysis/make_irradiance_csv.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import os as _os
import sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_ROOT = _os.path.normpath(_os.path.join(_HERE, "..", ".."))
_DIR = _os.path.join(_ROOT, "data", "downloads", "nasa_power_irradiance")
RAW = _os.path.join(_DIR, "power_hourly_2023_30.33N_94.78E.json")
CSV = _os.path.join(_DIR, "power_hourly_2023_30.33N_94.78E.csv")

#: SOURCE.md 里记下的核对值。改来源就会对不上——那时要同时改 SOURCE.md，不是改这里。
#:
#: 冻结的是**派生 CSV 的内容哈希**，不是原始响应的字节哈希。原始响应里带 API 版本号，
#: NASA 每次升级都会改变它（实测 v2.10.0 → v2.10.2），而 8760 个逐小时数值与派生表逐字节相同。
#: 按响应字节冻结会在数据毫无变化时误报，把真实的不一致淹掉。
EXPECT_ROWS = 8760
EXPECT_IRR_MAX = 1118.82
EXPECT_T_MIN, EXPECT_T_MAX = -20.49, 16.19
EXPECT_GE5 = 1665
EXPECT_CSV_SHA16 = "548afa25f9b0eaa6"


def main() -> int:
    if not _os.path.exists(RAW):
        print(f"缺原始文件 {RAW}\n先按下述命令重取：\n"
              '  curl -sS -o %s "https://power.larc.nasa.gov/api/temporal/hourly/point'
              '?parameters=ALLSKY_SFC_SW_DWN,T2M&community=RE&longitude=94.78&latitude=30.33'
              '&start=20230101&end=20231231&format=JSON"' % RAW)
        return 1
    raw_bytes = open(RAW, "rb").read()
    sha16 = hashlib.sha256(raw_bytes).hexdigest()[:16]
    data = json.loads(raw_bytes.decode("utf-8"))
    par = data["properties"]["parameter"]
    irr, tmp = par["ALLSKY_SFC_SW_DWN"], par["T2M"]
    keys = sorted(irr)
    with open(CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["stamp", "irradiance_wh_m2", "temp_c"])
        for k in keys:
            w.writerow([k, f"{irr[k]:.2f}", f"{tmp[k]:.2f}"])

    csv_sha16 = hashlib.sha256(open(CSV, "rb").read()).hexdigest()[:16]
    raw_sha16 = sha16
    api_ver = str(data.get("header", {}).get("api", {}).get("version", "?"))

    vals_i = [irr[k] for k in keys]
    vals_t = [tmp[k] for k in keys]
    ge5 = sum(1 for x in vals_t if x >= 5.0)
    checks = [
        ("行数", len(keys), EXPECT_ROWS),
        ("辐照峰值", round(max(vals_i), 2), EXPECT_IRR_MAX),
        ("气温下限", round(min(vals_t), 2), EXPECT_T_MIN),
        ("气温上限", round(max(vals_t), 2), EXPECT_T_MAX),
        ("≥5 °C 小时数", ge5, EXPECT_GE5),
        ("派生 CSV SHA-256 前 16 位", csv_sha16, EXPECT_CSV_SHA16),
    ]
    bad = []
    for name, got, want in checks:
        ok = got == want
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got}" + ("" if ok else f"（期望 {want}）"))
        if not ok:
            bad.append(name)
    print(f"写出 {CSV}")
    print(f"  参考：原始响应 SHA-256 前 16 位 {raw_sha16}，POWER API 版本 {api_ver}"
          f"（两者都不作为判定条件）")
    if bad:
        print(f"\n{len(bad)} 项不符：{bad}。来源或派生步骤变了——同步更新 SOURCE.md，"
              f"不要只改本脚本的期望值。")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
