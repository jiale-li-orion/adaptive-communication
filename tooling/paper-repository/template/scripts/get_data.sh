#!/usr/bin/env bash
# 获取需获取依赖（不入库的数据集）。幂等：已存在且校验通过的文件跳过。
#
# **本文件是占位骨架，必须替换。** 检查依赖的每个数据集都在这里获取，并在缺失时由检查打印
# 同样的命令，而不是抛出 traceback。核对方式优先选派生表的内容哈希，避免把传输字节当判据：
# 在线服务常把版本号或时间戳写进响应头，按响应字节冻结会在数据毫无变化时误报。
#
# 参考实现见 adaptive-communication 的 scripts/get_data.sh（地形高程瓦片与 NASA POWER 辐照）。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "scripts/get_data.sh 尚未配置：请在此写入本项目需获取数据集的获取与核对命令。" >&2
echo "若本项目没有需获取依赖，删除本文件并在 Makefile 中去掉 data 目标。" >&2
exit 1
