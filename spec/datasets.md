# 需获取数据集

本文件记录不入库、但检查依赖的数据集：来源、参数、单位、许可以及获取与核对方式。获取命令只写一处，就是 [`scripts/get_data.sh`](../scripts/get_data.sh)；本文件说明它拿到的是什么。

| 数据集 | 位置 | 来源 | 被谁使用 |
|---|---|---|---|
| SRTM1 地形高程 | `data/dem/hgt/N29E094`、`N29E095`、`N30E094`、`N30E095`（各 25,934,402 字节） | AWS Terrain Tiles，Skadi 分片的 SRTM1 v3，1 弧秒 | `code/physics/coverage_map.py`、`los_vs_itm.py`、`mountain_lora_link.py`；`code/instance/deployment.py` 的站点几何 |
| 部署点逐小时辐照与气温 | `data/downloads/nasa_power_irradiance/`（2022/2023/2024） | NASA POWER Source Native Resolution Hourly Data，参数 `ALLSKY_SFC_SW_DWN`（Wh/m²）与 `T2M`（°C），社区 `RE`，坐标 30.33 N / 94.78 E | `code/instance/exogenous.py::irradiance_harvest`，多年份实验 |
| ChirpBox 实测链路轨迹 | `data/downloads/chirpbox.csv` | Zenodo `10.5281/zenodo.5527877` | Gilbert-Elliott 两态链拟合，`code/analysis/fit_loss_model.py` |
| WirelessOpsBench 公开制品 | `other_repo/` | 第三方 artifact，按 SHA-256 获取 | 仅作对照，不参与本文结果 |

## 冻结规则

**冻结派生表的内容哈希，不冻结传输字节。** 辐照数据曾固定原始响应的 SHA-256，此后一次获取在逐小时数值与派生表逐字节相同的情况下报出哈希不符，原因是响应头携带 API 版本号，服务已从 `v2.10.0` 升到 `v2.10.2`。按传输字节冻结会在数据毫无变化时误报，而误报会把真实的不一致淹掉。

因此 `code/analysis/make_irradiance_csv.py` 判定的是派生 CSV 的 SHA-256 前 16 位（当前 `548afa25f9b0eaa6`）与五项数值性质（行数 8760、辐照峰值 1118.82 Wh/m²、气温区间 −20.49 至 16.19 °C、≥5 °C 小时数 1665）；原始响应哈希与 API 版本只作为信息输出，不参与判定。

## 缺数据时的行为

检查在缺数据时打印获取命令并以非零退出，不静默跳过，也不改换更弱的模型。`make data` 幂等：已存在且校验通过的文件直接跳过。
