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
