#!/usr/bin/env bash
# 获取需获取依赖（不入库的数据）。幂等：已存在且大小正确的文件跳过。
#
# 地形高程来自 AWS Terrain Tiles 的 SRTM1（1 弧秒）Skadi 分片。布置覆盖网关周边四个
# 1°×1° 瓦片；改名或新增站点时同步修改 TILES 与 spec/instance-v1-manifest.md。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/data/dem/hgt"
BASE="https://s3.amazonaws.com/elevation-tiles-prod/skadi"
TILES=(N29E094 N29E095 N30E094 N30E095)
EXPECT_BYTES=25934402   # 3601 × 3601 × 2 字节，SRTM1 单瓦片

mkdir -p "$DEST"

for tile in "${TILES[@]}"; do
  out="$DEST/$tile.hgt"
  if [ -f "$out" ] && [ "$(stat -c%s "$out")" -eq "$EXPECT_BYTES" ]; then
    echo "skip   $tile.hgt（已存在）"
    continue
  fi
  dir="${tile:0:3}"
  url="$BASE/$dir/$tile.hgt.gz"
  echo "fetch  $tile.hgt"
  curl -fL --retry 3 --retry-delay 2 -o "$out.gz" "$url"
  gunzip -f "$out.gz"
  size=$(stat -c%s "$out")
  if [ "$size" -ne "$EXPECT_BYTES" ]; then
    echo "ERROR  $tile.hgt 大小为 $size，期望 $EXPECT_BYTES" >&2
    exit 1
  fi
done

echo "地形高程就绪：$DEST"

# ---------------------------------------------------------------------------
# 部署点逐小时辐照与气温（NASA POWER，E 层来源事实）。
# 原始 JSON 有哈希可核对，派生脚本 code/analysis/make_irradiance_csv.py 会校验行数、
# 辐照峰值、气温区间与 SHA-256 前 16 位，对不上即报错。2023 全年被实例层检查直接使用；
# 2022 与 2024 供多年份实验使用。
POWER="$ROOT/data/downloads/nasa_power_irradiance"
API="https://power.larc.nasa.gov/api/temporal/hourly/point?parameters=ALLSKY_SFC_SW_DWN,T2M&community=RE&longitude=94.78&latitude=30.33&format=JSON"
mkdir -p "$POWER"

for year in 2022 2023 2024; do
  raw="$POWER/power_hourly_${year}_30.33N_94.78E.json"
  if [ -s "$raw" ]; then
    echo "skip   power ${year} 原始响应（已存在）"
    continue
  fi
  echo "fetch  power ${year} 原始响应"
  curl -fsSL --retry 3 --retry-delay 2 "${API}&start=${year}0101&end=${year}1231" -o "$raw"
done

echo "derive 辐照 CSV（2023 由派生脚本核对哈希）"
python3 "$ROOT/code/analysis/make_irradiance_csv.py"
echo "辐照数据就绪：$POWER"
