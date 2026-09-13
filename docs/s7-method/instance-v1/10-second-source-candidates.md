# 10 · 第二业务来源候选（检索与取证）

> 本文只做检索与取证，不改动仓库任何代码或结果文件。
> **纪律**：下面每一个数字，都来自我**实际用 `curl` 打开并读到内容**的页面、PDF 或数据文件；每条都标出出处（URL / 文件 / 行 / 列 / 页）。凡"我打不开"或"未提供"的都显式写明，不做推测填充。
> **三类证据标记**：**[实测]** = 我从原始时间戳数据里算出来的；**[原文]** = 页面/PDF 里的逐字文字；**[目录]** = 元数据目录字段。

---

## 0. 结论

**确实找到了**含遥测节奏的第二业务来源，而且不止一个。

| | 首选 | 备选 1 | 备选 2 |
|---|---|---|---|
| 来源 | **USGS 克利夫兰科拉尔滑坡（Cleveland Corral）近实时监测**，两个数据发布 | **广西普适型地质灾害监测**（采购技术参数 + 运维成效要求） | **PermaSense 马特洪峰岩壁监测网** |
| 标识 | DOI `10.5066/P1P9DMFX`（多传感器 15 min）<br>DOI `10.5066/P91G78VN`（GPS 10 min） | PDF 直链（见 §4.1），229 页 | PANGAEA `10.1594/PANGAEA.967586` |
| **带真实时间戳的开放数据** | **有**：42 个 CSV + 1 个 GPS CSV，逐条时间戳，**CC0-1.0 公有领域** | **无**（是采购/运维要求文本，不是数据） | **有**（CC-BY-4.0），但总量 83.8 GB、经 API/工具集拉取 |
| 能直接量出的节奏 | 常规 **900 s** 与 **600 s** 两套网格；GPS 原始历元 **15 s**；22 年断连历史 | 采样与上传**两个独立字段**（采样 0s–24h / 上传 0s–72h）；常态 **1h/条**，形变时 **1–5min/条**；功耗 ≤6 mW–≤3 W、太阳能板 ≥600 W + 蓄电池 ≥400 Ah | 采样 **120 s** → 转发 **30 s** → 聚合 **3600 s**，三层节奏 |
| 相对 Wang 2022 的差异 | **大**：1 h → 15 min；文件中**无事件加密**；一次电池 + 连续工作 + UHF | **中**：节奏形态与 Wang 相近（小时基 + 事件加密），但**两字段独立 + 功耗/在线率指标**是新东西 | **大**：采样 ≪ 上报、三层节奏、**逐样本三时间戳**、backpressure 补传 |

下面 §1–§3 只讲首选（我实测过每一个数字）；§4 讲备选。
§4.6 是**非滑坡业务**的节奏对照（已标注）；§4.7 是字段最全、但**几乎可以确定是合成数据**的 LoRaWAN 遥测集——**只能当 schema 模板，不能当真实证据**，请按该节的警示使用。

---

## 1. 首选候选：USGS Cleveland Corral 滑坡近实时监测（两个数据发布）

同一个滑坡部署、同一套遥测体系（USGS 火山灾害计划的**数据采集 + 无线遥测**），对外发布了两个互补数据集：

- **(A) 多传感器 15 分钟数据集**：1997–2018，位移 / 孔隙水压 / 土壤含水量 / 雨量
- **(B) GPS 10 分钟数据集**：WY2017（2016-10-01 → 2017-09-30），滑坡趾部位移，原始历元 15 s

### 1.1 名称、DOI、URL、许可

**(A) 多传感器**

- 标题：`Landslide monitoring data for the Cleveland Corral landslide near U.S. Highway 50, El Dorado County, California`
- DOI：`10.5066/P1P9DMFX` —— 我实测 `curl -sIL https://doi.org/10.5066/P1P9DMFX` 跳转到
  `https://www.sciencebase.gov/catalog/item/65d8f08fd34ec3e1801e3efc`
- 正式引用（**从 data.usgs.gov 落地页抓到的引用串，逐字**）：
  > `Reid, M.E., Brien, D.L., and LaHusen, R.G., 2025, Landslide monitoring data for the Cleveland Corral landslide near U.S. Highway 50, El Dorado County, California : U.S. Geological Survey data release, https://doi.org/10.5066/P1P9DMFX.`
- 许可（**ScienceBase 条目 JSON 的 `rights` 字段，逐字**）：
  > `This work is marked with the Creative Commons Zero v1.0 Universal (CC0-1.0) public domain dedication; https://creativecommons.org/publicdomain/zero/1.0/.`
  （📌 精确说明：该条目 `license` 字段实测为 **`null`**，**许可要看 `rights` 字段**；(B) GPS 条目同样 `license = null`、`rights` 逐字与上面相同。两处发布均**无 zip 包**，(A) 有 8 个独立文件、(B) 有 4 个独立文件。）
- 同时，data.usgs.gov 落地页内嵌 JSON-LD 的许可字段（逐字）：
  > `"license": "http://www.usa.gov/publicdomain/label/1.0/"`
  （US 政府公有领域标签。我**未能**打开 `usgs.gov/information-policies-and-instructions/copyrights-and-credits` 佐证政策原文：该请求被 CloudFront 以 **403** 拒绝——上面两条元数据字段就是我的许可证据。）
- 目录日期 **[目录]**：`Publication Date 2025-12-15`，`Start 1997-03-22`，`End 2018-09-25`
  - ⚠ 口径不一致：release 自带的 `Landslide_Monitoring_Data_..._CA.xml` 内 `<pubdate>` 写的是 **2024**，而条目日期是 **2025-12-15**。引用年份以条目/官方引用串的 **2025** 为准。

**(B) GPS**

- 标题：`10-Minute GPS Monitoring Data for the Cleveland Corral landslide near U.S. Highway 50, El Dorado County, California`
- ScienceBase 条目：`https://www.sciencebase.gov/catalog/item/64f10cebd34e09595516d84b`
- DOI：**从 CSV 文件第 2 行读到，逐字**：
  > `U.S. Geological Survey data release: https://doi.org/10.5066/P91G78VN`
- 许可：`rights` 字段与 (A) **逐字相同**（CC0-1.0 公有领域奉献）
- 目录日期 **[目录]**：`Start 2017-10-01`，`End 2018-09-30`
  - ⚠ **目录口径与实际数据不一致**：CSV 实际首行 `10/1/2016 0:59`、末行 `9/30/2017 23:49`，即 **WY2017（2016-10-01 → 2017-09-30）**。**以数据为准**（见 §1.3）。

### 1.2 可直接引用的原话（逐字）

**(A) 摘要**（来源：ScienceBase 条目 summary / data.usgs.gov 落地页描述）

> `This USGS data release presents graphical and tabular data from near real-time monitoring of the Cleveland Corral landslide conducted between 1997 and 2018. The monitoring data include 15-minute and daily measurements (in separate files) for four types of sensors on the landslide: 1) piezometers that recorded subsurface pore-water pressures at different depths and locations within the slide mass, 2) extensometers that recorded downslope displacement of the slide ground surface at different locations throughout the slide, 3) volumetric water content sensors that measured soil moisture at the toe of the landslide, and 4) one rain gauge that recorded precipitation, including rainfall and snowmelt.`

> `Data were recorded using data-acquisition systems and radio telemetry developed by the USGS Volcano Hazards Program (Hadley and LaHusen, 1995).`

> `Both sets of files are organized by water year, starting October 1; all times are Pacific Standard Time.`

> `5) 15-minute near-real time monitoring data (.csv format), 6) daily monitoring data – daily maxima for rainfall and medians (of the 15-minute data) for other sensors (.csv format), and 7) description of sensors (.csv format).`

**(B) 摘要**（来源：ScienceBase 条目 summary / 元数据 XML `<abstract>`）

> `Raw GPS data from L1-only receivers were recorded in 15 second epochs using data acquisition systems and radio telemetry developed by the USGS Volcano Hazards Program. The overall system, named LORAS (for Landslide Optimized Real-time data Acquisition System), is further described in Reid and others (2021). The system uses u-blox T4 GPS receivers and Trimble Bullet antennas. The moving GPS receiver, located on the toe of the landslide, is approximately 431 m from the base station.`

> `Static GPS solutions at approximately 10-minute intervals were obtained by post-processing the previous 1-hour of data.`

> `Time gaps in the data sets indicate insufficient GPS data, problems with data telemetry, and/or poor satellite configuration.`

**(B) 处理流程**（元数据 XML `<procdesc>`，逐字节选）

> `Step 1 - ... Files containing L1-GPS data collected every 15 seconds were post-processed to convert from the binary U-Blox file format (.ubx) to RINEX observation files (.obs) using TEQC software ...`

> `Step 2 - ... The converted GPS data from step 1 were processed to obtain a static solution at approximately 10-minute intervals using the preceding one-hour time window.`

**(B) 数据文件内的 cite 行**（我下载后读到的第 1–3 行，逐字）

```
10-Minute GPS Monitoring Data for the Cleveland Corral landslide near U.S. Highway 50,, El Dorado County, California
U.S. Geological Survey data release: https://doi.org/10.5066/P91G78VN
processing steps and reference system described in GPS_Monitoring_Cleveland_Corral_landslide_El_Dorado_County_CA.xml
```

### 1.3 我从原始数据里量出来的数字 [实测]

方法见 §附录 A（可完整复现）。数据来自 `Cleveland_Corral_15_Minute_Data.zip`（6,479,946 B）与 `10Minute_GPS_..._UTM.csv`（3,111,374 B）。

**(B) GPS 10 分钟数据集**

| 量 | 我实测的值 |
|---|---|
| 行数 | **42,191** |
| 时间窗口 | **2016-10-01 00:59 → 2017-09-30 23:49**（UTC，列名 `date_time_UTC`）；跨度 364.95 d |
| 理论 600 s 槽位 | 52,554；缺失 **10,368**；**数据得率 80.28%** |
| 众数间隔 | **600 s 占 38,772 / 42,190 = 91.90%**（中位数 600 s） |
| 次高频间隔 | 1200 s（1,660 次）、1800 s（444 次）、540 s（229 次）、660 s（217 次）、2400 s（200 次） |
| 断连 >660 s | **n = 2,897**，累计 **2,213.78 h** |
| 断连 >1 h | **n = 226**，累计 1,042.73 h，最长 **99.50 h** |
| 断连 >6 h | n = 32，累计 748.77 h |
| 断连 >24 h | n = 8，累计 481.73 h |

**最长 6 次断连的起止时刻 [实测]**（都在 2016-10 至 2017-01，即冬季）：
`2016-10-07 21:39 → 2016-10-12 01:09`（**99.50 h**）、`2016-12-23 23:58 → 2016-12-27 19:19`（91.35 h）、`2017-01-20 22:49 → 2017-01-23 18:09`（67.33 h）、`2016-10-29 04:59 → 2016-10-31 21:29`（64.50 h）、`2016-11-12 06:57 → 2016-11-14 17:09`（58.20 h）、`2017-01-28 07:18 → 2017-01-30 04:49`（45.52 h）

**(A) 多传感器 15 分钟数据集**

| 量 | middle 站 | toe 站 |
|---|---|---|
| CSV 文件数 | 22（WY1997–WY2018） | 20（**缺 WY2002**） |
| 行数 | **705,470** | **562,107** |
| 时间窗口 | 1997-03-22 14:09 → 2018-09-25 08:55（21.51 y） | 1997-04-04 09:37 → 2017-09-25 13:28（20.48 y） |
| 理论 900 s 槽位 / 缺失 | 754,252 / 52,139 | 718,000 / 159,016 |
| **数据得率** | **93.53%** | **78.29%** |
| **间隔恰为 900 s** | **657,294 / 705,469 = 93.17%** | **517,804 / 562,106 = 92.12%** |
| 间隔 < 10 min 的条数 | **48** | **159** |
| 断连 >30 min | n=9,493，591.7 d（占时间 **7.53%**） | n=11,578，1,723.3 d（**23.04%**） |
| 断连 ≥1 h | n=667，381.9 d | n=1,524，1,486.3 d |
| 断连 ≥24 h | n=36，301.9 d | n=64，1,279.0 d |
| 断连 ≥7 d | n=6，227.3 d | n=9，1,146.8 d |
| 最长单次断连 | **83.8 d** | **609.4 d** |

**单年得率分布（说明"平均 93%"掩盖了很大方差）** —— middle 站：WY1997 95.9%、WY1999 **82.5%**、WY2003 90.2%、**WY2007 99.6%**、WY2018 99.7%；toe 站：**WY2001 仅 24.8%**、WY2003 77.2%、**WY2016 99.7%**。
单次最长断连：middle WY1999 `1999-07-18 22:50 → 1999-08-31 14:00`（1,047.2 h ≈ 43.6 d）；toe WY2017 `2016-11-20 23:47 → 2017-01-01 00:05`（984.3 h）。

**"有没有事件加密"的判定 [实测]**：交付记录是**均匀网格**，没有事件触发的密集段。间隔 < 10 min 的相邻对只有 48（middle）/ 159（toe）条，且最小间隔 1.0 min 属个别跳变；**不存在**密集上报段。→ **该数据集本身不含"阈值触发 → 加密上报"的节奏。**

**采样网格相位 [实测]**：时间戳分钟值逐年漂移（middle：WY1997 以 `:x4/:x9` 为主 → WY2013 以 `:00/:15/:30/:45` 为主 → WY2018 以 `:x9/:x4` 为主）。说明是记录仪本地时钟，**没有绝对时间同步痕迹**；引用时不要假定整点对齐。

### 1.4 附加证据层：同一遥测体系的技术手册（事件规则在这里）

Cleveland Corral 的 (A) 发布把遥测体系归于 `Hadley and LaHusen, 1995`。我把这份手册下载并抽取正文：

- 文献：**Hadley, K.C., and LaHusen, R.G., 1995, Technical manual for the experimental Acoustic Flow Monitor, USGS Open-File Report 95-114**
- URL（我实际下载成功）：`https://pubs.usgs.gov/of/1995/0114/report.pdf`（738,759 B，pypdf 读得 29 页）
- 以下引文均在 **PDF 第 5 页** `THEORY OF OPERATION` 节：

> `The AFM is a micro-powered field computer programmed to continuously analyze the amplitude, frequency and duration of ground vibrations.`

> `The AFM reads and transmits digital data via UHF radio back to a base station receiver at timed intervals. If debris flow activity is detected a data set is sent immediately.`

> `The AFM will remain in alert mode and continue to send flagged data at 1 minute intervals while input levels remain above threshold. When the signal level drops below threshold the AFM resumes normal operation sending unflagged data transmissions at preset timed intervals, typically every 30 minutes.`

> `Power to the preamplifier board is provided by the primary +12VDC battery supply and regulated to +5VDC by U3.`

> `data are modulated by the 300 baud modem and passed to the radio transmitter`

> `Two-way radio communications enable automatic, real-time data transmissions from remote instrument sites to a base station receiver. Users have the ability to query the AFM field units from a base station computer to obtain data or modify system operating parameters.`

> `setting the clock operation modes to a 24 hour cycle with an oscillator frequency of 32.768 KHz`

⚠ **必须标注的口径边界**：AFM 是**泥石流次声监测仪**这一具体仪器的手册，Cleveland Corral 发布只把它作为**遥测体系（data acquisition + radio telemetry）的血统引用**。
因此：**AFM 的"常态 30 min / 告警 1 min"是仪器级默认传输节奏，不是 Cleveland Corral 站点文件里的节奏（那个是 15 min）**。不要等同，只能作为"同一遥测家族的事件触发规则"引用。

### 1.5 逐项对照：这个来源能读出什么

| 你要求的量 | 能读出的值 | 出处（行/列/原文） |
|---|---|---|
| **常规采样间隔** | **(A) 900 s（15 min）**；(B) 原始观测**历元 15 s** | (A) **[原文]** `15-minute and daily measurements`；(B) **[原文]** `recorded in 15 second epochs` |
| **常规上报/回传间隔** | (B) 解算/交付产品 **≈600 s** [实测 91.90%]；(A) 发布只给了 15 min 一个数 → **采样与上报未区分** | (B) **[原文]** `Static GPS solutions at approximately 10-minute intervals`；[实测] §1.3 |
| **采样间隔与上报间隔是否同一个数** | **(B) 不是同一个数**：15 s 原始历元 → 600 s 解算产品（40×）。**(A) 无法区分**：只有一个 15 min | (B) **[原文]** Step 1 + Step 2；⚠ 600 s 是**解算产品间隔**，**不是**无线空口回传间隔——空口间隔**未提供** |
| **事件触发规则与事件期节奏** | 交付数据中**没有事件加密**（[实测] 间隔 <10 min 仅 48/159 条）。同一遥测体系手册给出**常态 30 min → 告警态 1 min**、阈值为声幅阈值 + 持续时间 | **[实测]** §1.3；**[原文]** OFR 95-114 p.5 `typically every 30 minutes` / `at 1 minute intervals` |
| **设备自治/供电方式** | **[原文]** `micro-powered field computer programmed to continuously analyze`（**连续工作，不占空比休眠**）；`primary +12VDC battery supply`（**一次电池**） | **[原文]** OFR 95-114 p.5 |
| **太阳能？休眠电流？占空比？** | **未提供**（(A)(B) 两处发布均无功耗/电流/电池容量字段；手册只给 +12 VDC 与"micro-powered"） | — |
| **通信方式** | **UHF 无线遥测**（非 LoRa / 非 NB-IoT），**双向**，基站可查询与改参数；300 baud 调制解调 | **[原文]** OFR 95-114；**[原文]** (A) `radio telemetry developed by the USGS Volcano Hazards Program` |
| **链路几何（可当链路预算输入）** | 移动 GPS 接收机距基站 **431 m**（`ultra-short baseline`） | **[原文]** (B) `approximately 431 m from the base station` |
| **回传中断/丢包/离线记录** | **有，且可量化**：GPS 得率 80.28%、226 次 >1 h 断连、最长 99.50 h；(A) middle 93.53% / toe 78.29%，9,493 与 11,578 次 >30 min 断连，最长 83.8 d 与 609.4 d | **[实测]** §1.3；**[原文]** (B) `Time gaps in the data sets indicate insufficient GPS data, problems with data telemetry, and/or poor satellite configuration.` |
| **中断归因（哪些是链路、哪些是仪器）** | **部分可归因**，靠 `Cleveland_Corral_Sensor_Descriptions.csv` 的 `notes` 列：<br>`St. Pauli fire destroyed site 7/26/02`<br>`broken instrument` / `broken cable`（mid_E2_B，11/29/2005→6/1/2016）<br>`mechanical failure of rain gage 1/22/16, rainfall for 1/22/16 - 1/27/16 estimated from Sly Park rain gage`<br>`extensometer post toppled to the ground on 3/16/17; topple event was removed from data; post was relocated on 4/25/17` | **[原文]** `Cleveland_Corral_Sensor_Descriptions.csv`，`notes` 列 |
| **每条样本有几个时间戳** | **(A)(B) 各只有 1 个**（`date_time_PST` / `date_time_UTC`）。**没有**"生成时刻/到达时刻/入库时刻"的区分 | **[实测]** 列名 |
| **时区** | (A) `all times are Pacific Standard Time`，列名 `date_time_PST`；(B) 列名 `date_time_UTC` | **[原文]**/[实测] 列名 |

**传感器与型号（取自 `Cleveland_Corral_Sensor_Descriptions.csv`，逐字）**：Unimeasure `HX-PA-400 / HX-VPA-400 / HX-PA-500` 位移计（量程 `0 to 1016 cm` / `0 to 1270 cm`）；孔隙水压 `uses Honeywell 26PCCFA3D`、`Micron MP100E`、`GE Druck PCDR1730`（`0 to 15 psi` / `0 to 10 psi` / `0 to 5 psi`）；土壤含水量 `Decagon EC-5`；雨量计 `Pronamic Rain-O-Matic Professional`，`1 tip = 0.01 inches = 0.254 mm`。

### 1.6 引用陷阱

`CCmiddle_daily_1997_2002.csv` 的**第 3 行**写的是
> `daily rainfall maxima and daily medians other sensors at toe station, 1997 - 2002`

而文件名是 **middle** 站（列名也都是 `mid_*`）。**这是发布方自己的标题行错标**，引用时按**列名**判定站点，不要按第 3 行标题行。

---

## 2. 与 Wang 2022 的差异（逐项）

Wang 2022 侧的值取自本项目内既有登记（`02-instance-manifest.md`、`wang-2022-table3-excerpt.csv`），此处只做对照。

| 维度 | Wang 2022（重庆山区滑坡） | **Cleveland Corral（首选）** | 差异性质 |
|---|---|---|---|
| 常规上报周期 | **1 h（3600 s）** | **15 min（900 s）**（多传感器）／**10 min（600 s）**（GPS 解算） | **4×–6× 更快**，且两种周期并存 |
| 常规采样间隔 | **来源未单独公布**，项目按 3600 s 假定 | (A) 与上报同为 15 min（**未区分**）；(B) **原始历元 15 s**，与 600 s 产品**明确不同** | 第一次有了"采样 ≪ 上报"的**实数分解** |
| 事件节奏 | **20 mm 位移触发** → 3 条密集上报、间隔 ≈**300 s** | **交付数据中无事件加密**（[实测] §1.3）；同体系手册为 30 min 常态 → **1 min** 告警态 | **节奏形态不同**：一个是"小时基 + 突发"，一个是"均匀网格 + 无突发" |
| 设备自治/供电 | **太阳能** + 电池，低功耗现场节点 | **一次电池 +12 VDC**，`micro-powered field computer` 且 **continuous analyze（无休眠占空比）** | **自治方式不同**（差异最大的一项） |
| 通信方式 | **LoRa** | **UHF 无线遥测**，双向可查询，300 baud modem | 体制不同；本来源**无法**给出 LoRa 空口参数 |
| 链路距离 | 未登记 | 移动节点↔基站 **431 m** | 新增可用的链路几何量 |
| 观测时长/规模 | 分析期 2019-12-15 → 2020-09-10（约 9 个月），1 台设备（EI01） | **21.5 年 / 20.5 年**，2 个站（含 upper 为 3 个站），705,470 + 562,107 行 + GPS 42,191 行 | **统计效力完全不同**：能看出跨年、跨仪器的中断分布 |
| 中断/离线 | 未单独公布 | **可量化到单次断连**（226 次 >1 h；最长 99.50 h；toe 最长 609.4 d） | **新增了中断时长的经验分布** |
| 每条样本时间戳 | 触发时刻 + 发送时刻（Table 3 的 `source_trigger_time` / `source_transmission_time`） | 只有 1 列时间戳 | **这一项 Wang 反而更细**（见 §3） |

**一句话**：首选场景不是"让某个方法赢"的场景——它是一个**均匀 15 min 网格 + 长期重中断**的世界，与 Wang 的"小时基 + 事件突发"世界在**周期、自治方式、中断统计**三条轴上同时不同。两者都支持"按期可用性"评测，但压力来源不同：Wang 压**突发排队**，Corral 压**长时间链路/仪器失联下的补传与设备老化**。

---

## 3. 不能支持什么（缺哪些量 → 哪些结论仍不能靠它推广）

1. **不能把 (A) 的采样与上报拆开**。多传感器发布只给"15-minute"，**没有独立的 report interval 数字**。→ 依赖"采样间隔与上报间隔是两个独立可调参数"这一结构的结论，**不能**用 (A) 推广（那仍是 Wang 的 `0042`/`0045` 双字段场景专属；备选 1 广西可补这一轴）。
2. **(B) 的 600 s 是解算产品间隔，不是空口回传间隔**。原始 15 s 数据经 UHF 回传到基站后离线做 RTKLIB 后处理；**"每 15 s 数据多久上一次空口"未提供**。→ 不能把 600 s 当成链路负载周期去算占空比或能耗。
3. **没有任何链路质量字段**。无 RSSI / SNR / 重传次数 / PDOP / 每包接收时刻。断连只能从"时间戳缺失"反推，**无法区分"发不出去"与"没采到"**（(B) 自己把三者并列：`insufficient GPS data, problems with data telemetry, and/or poor satellite configuration`）。→ 受扰链路的**误码/丢包模型不能由此标定**。
4. **无功耗量化**。没有休眠电流、占空比、电池容量 (Wh)、太阳能板功率、能耗曲线。只有"micro-powered"与"+12 VDC 一次电池"。→ 0.001–0.05 Wh 量级的能量预算**不能**由它标定。
   - 部分可补：**广西**（§4.1）给了装置级 `≤6 mW` / `≤3 W 全功耗` / `≤2 W 低功耗` / 太阳能板 `≥600 W` + 蓄电池 `≥400 Ah`；**§4.7** 的表里有 `current_sleep_ma` / `current_measurement_ma` / `current_transmission_ma` / `battery_voltage_v` 四列，**但它几乎可以确定是合成数据**，只能抄 schema 与量级感，不能当实测功耗用。
5. **无 LoRa / NB-IoT 参数**。UHF + 300 baud 的时序**不可直接迁移**到 LoRa 的 ToA/占空比约束。
6. **无灾前边界**。它是 1997–2018 长期监测，发布方**没有标注灾害时间窗口**（背景事件是 1997 年邻近的 Mill Creek 滑坡，属历史背景而非分析期边界）。→ "灾前窗口"时长定义仍不能由它提供。
7. **无中心侧指令交互细节**。只有手册一句"基站可查询/改参数"；**没有**帧格式、命令-响应时序、改配置后是否顺带补一条数据。→ 项目里"改配置需不需要额外下行"的未闭合项**仍未闭合**。
8. **中断归因不完整**。`notes` 列能解释一部分（火灾、断线、仪器损坏、桩倒），但**大部分断连没有原因标注**（如 middle WY1999 那 43.6 d）。→ "链路中断"与"站点停摆"的比例**不能**由它给出。
9. **时间戳只有一列**，且网格相位逐年漂移、无 NTP/绝对时间同步证据。→ 不能支持"端到端时延（生成→到达）"研究；这正是首选相对**备选 2（PermaSense）**最弱的一点。**§4.7** 的表里有 `node_timestamp` vs `platform_received_timestamp` + `latency_seconds`，是一个可直接照抄的字段模板（**但同样是合成数据**）。

---

## 4. 备选

### 4.1 备选 1：广西普适型地质灾害监测——设备参数表 + 运维成效要求（**官方、装置级数字最全**）

- 文件：**《公开招标文件（全流程电子化评标）——2024 年广西地质灾害监测台站建设项目（设备采购部分）》，229 页**。PDF 直链（我实测下载成功，1,781,729 B，`file` 报 `PDF document, version 1.7, 229 page(s)`）：
  `http://oss-gxhlw.unicloudgov.com/guangxi-gov-open-doc/1014AN/450103/10007122169/20244/58ffcc03-4a5b-41aa-aa8b-1532b4350f6a.pdf`
  - **引用信息（PDF 第 1 页封面，逐字）**：`公开招标文件 （全流程电子化评标） 项目名称：2024 年广西地质灾害监测台站建设项目（设备采购部分） 项目编号：GXZC2024-G1-003083-ZXGC 采购人：广西壮族自治区自然资源厅 采购代理机构：广西众鑫工程项目管理有限公司 2024 年 月 日`
  - ⚠ **我未能取得该 PDF 的页面 URL**（检索助手报告平台 `gcy.zfcg.gxzf.gov.cn` 实测连接失败 000）；**文件内未印具体发布日期**（封面只标"2024 年 月 日"）。**无许可/版权声明（未提供）**：全文的"版权"字样只出现在合同条款（知识产权遵守条款）与投标声明格式里，**不是文件自身的版权声明**。
  - 📌 **页码口径**：本文件**PDF 物理页 = 印刷页 + 2**。下文我给的页码是 **PDF 物理页**；引用时请注明口径（例：`1h/条` 在 **PDF p.100 = 印刷 p.98**；设备参数在 **PDF p.14 = 印刷 p.12**）。
- **运维节奏与中断指标（PDF 第 100 页 = 印刷第 98 页，「附件3《广西地质灾害监测台站运行维护要求》→ 三、运维成效要求」，逐字）**：
  > `1、运维期内设备整体（按建设/运维批次统计）在线率不应低于 95%，汛期（每年 4-9月）单台设备连续离线时间不超过 7天，非汛期（每年 10 月-次年 3 月）单台设备连续离线时间不超过 15天。`
  > `2、监测数据应按要求频次采集。当前我区安装数量较多的倾角（加速度）计、GNSS 地表位移、裂缝计、雨量计等设备，正常情况下要求数据采集频次一般为 1h/条，当坡体发生形变时，倾角（加速度）计、GNSS 地表位移、裂缝计应能加密采集数据，1-5min/条为宜。如今后上级技术标准有更新要求，已最新要求为准。`
- **设备参数表（PDF 第 13/22/31/39 页，采购需求一览表，逐字节选）**：
  - **GNSS 地表位移监测设备**（标段 A/B/C/D 各 90/174/18/52 台）：
    > `2、采样间隔：0s～24h；`
    > `3、上传间隔：0s～72h；`
    > `4、通信方式：移动通信/低功率广域网/高低轨卫星通信；`
    > `★7、星频要求和工作模式：BDS+GPS/双星四频，支持内置 MEMS传感器动态触发调整监测频率功能；`
    > `★8、功耗：在采样间隔不低于 15s且上传间隔不低于 15s情况下，接收机正常工作的平均功耗≤2W；`
    > `★11、设备可靠性：MTBF时间≥35000小时；`
    > `16、供电方式：太阳能供电，满足连续 30 个阴雨日正常工作，过压或欠压保护；`
    > `14、数据传输存储：GNSS数据由投标人自行解算后，解算成果数据须实时传输至广西监测预警指定服务器，GNSS原始数据每 3个月备份一次至广西监测预警指定服务器；`
  - **裂缝计**（40 台）：
    > `7、采样间隔：0s～24h；` / `8、上传间隔：0s～72h；`
    > `★14、整机平均功耗：≤6mW，（24小时平均功耗）；`
    > `★15、触发功能：设备具备阈值触发功能，如监测数据超过阈值，可立即采集监测数据并自动上报；`
    > `17、供电方式：内置电池供电，满足连续 3年正常工作，电池可更换；`
  - **倾角加速度计**（395/407 台）：同样 `采样间隔：0s～24h` / `上传间隔：0s～72h` / 阈值触发立即采集上报 / `内置电池供电，满足连续 3 年正常工作，电池可更换`
  - **雨量计**（97 台，PDF 第 15 页）：`7、采样间隔：0s～24h；` / `8、上传间隔：0s～72h；` / `9、通信方式：移动通信/低功率广域网/高低轨卫星通信；` / `12、供电方式：按需供电方式，满足连续 30个阴雨日正常工作；`
  - **泥位计**（95 台，PDF 第 15–16 页；**这是唯一给了明确"功耗模式"配对的设备**）：
    > `4、上传间隔：1s~24h(按需设定)；`
    > `★7、在 IE 浏览器下，可配置全功耗模式和低功耗模式。全功耗模式下，功耗≤3W；低功耗模式下，功耗≤2W；`
    > `8、具有本地存储功能，内存≥256G；`
    > `★13、设备在正常工作条件下，连续工作≥150h，不应出现电气、机械或软件的故障；`
    > `★14、快速启动功能检验:从休眠状态唤醒，可在 40s内预览画面；`
    > `17、供电方式：按需供电方式，满足连续≥30 个阴雨日正常工作(具备过压及欠压保护)，若太阳能供电，配置太阳能板≥600W，蓄电池≥400Ah;`（跨第 15→16 页）
- **运维与响应时限（PDF 第 99 页，逐字节选）**：
  > `（1）站点运维单位在汛期内（每年 4月 1日-9月 30日）应对所有监测站设备进行常规巡检不低于两轮，非汛期（每年 10 月 1日-次年 3 月 31日）应对所有监测站设备进行常规巡检不低于一轮…`
  > `①因设备故障导致的设备离线、监测数据异常触发误报警，必须 1 小时内做出响应，4 小时内远程完成仪器设备故障排查，无法修复的，48小时内到场维修。`
- **安装调试项（PDF 第 95 页，逐字）**：`1.4.6 信息送达调试。包括预警信息下发测试、预警广播现场远程唤醒测试、采集频率动态调整测试等。`（→ "改采样频率"被列为**现场必测项**，佐证该动作空间在真实运维里是可下发的）
- **能读出的数字汇总**：常规采集 **1 h/条**；形变加密 **1–5 min/条**；**采样间隔与上传间隔是两个独立可配置字段**（0s–24h / 0s–72h；泥位计另为 1s–24h）；功耗 **≤2 W**（GNSS，在采样与上传均 ≥15 s 条件下）、**≤6 mW（24 h 平均）**（裂缝计）、**≤3 W 全功耗 / ≤2 W 低功耗可远程配置**（泥位计）；供电=**太阳能（连续 ≥30 个阴雨日；太阳能板 ≥600 W + 蓄电池 ≥400 Ah）** 或 **内置电池（连续 3 年）**；通信=**移动通信/低功率广域网/高低轨卫星通信**；通信标准 **DZ/T 0450-2023**；**在线率 ≥95%**，**汛期连续离线 ≤7 天、非汛期 ≤15 天**；故障响应 **1 h 响应 / 4 h 远程排查 / 48 h 到场**；阈值触发→立即采集并自动上报；MTBF ≥35 000 h；泥位计本地存储 **≥256 GB**
- **⚠ 未提供的量**：招标文件全文**没有** `休眠电流`、`断线续传/离线补传` 的具体数值（这三个词在文件内未出现）——即"中断后怎么补"**未提供**，只有"在线率/离线时长"的**考核指标**
- **同族佐证（我也亲自打开复核过）**：
  - **青海西宁大通县项目公告 PDF**（《2026年度西宁市大通县地质灾害群专结合监测预警 竞争性磋商文件》，65 页，628,678 B，我下载成功）：`https://zcy-gov-open-doc.oss-cn-north-2-gov-1.aliyuncs.com/1023FP/639900/10007432686/20263/f7cc7e6b-471a-4501-a096-c0f447f4cd74.pdf`
    **引用信息（PDF 第 6 页，逐字）**：`公告发布时间 2026年03月03日`；`采购人：大通回族土族自治县自然资源局`；`采购代理机构：青海紫宸工程造价咨询有限公司`；`提交响应文件截止时间 2026 年03 月16 日下午14 时30 分（北京时间）`。项目编号 **青海紫宸竞磋（服务）2026-005号**，预算 **179 万元**。（📌 与广西同样存在页差：本文件 **PDF 物理页 = 印刷页 + 1**；**无许可/版权声明（未提供）**，全文的"版权"字样只出现在合同条款。**HTML 落地页我未取得**，只有 PDF 直链。）
    **PDF 第 61 页「（四）监测设备技术要求 → 1 监测设备技术指标」逐字**：
    > `依据《地质灾害自动化仪器监测预警规范》（DZ/T 0460-2023），自动化监测仪器设备主要技术参数要求如下：表 1 雨量计主要技术参数 … 采样间隔 0s～24h 按需求设定 上传间隔 0s～72h 按需求设定 通信方式 移动通信、低功率广域网、卫星通信 … 通信标准 符合《地质灾害监测数据通信技术要求》（DZ/T 0450-2023）`
    （→ 把上面的参数锚定到了**行业标准 DZ/T 0460-2023 / DZ/T 0450-2023**。）
    该标准的**元数据**我另外打开了一个第三方标准聚合页确认（`https://www.bzpt.com/hb/349524.html`，HTTP 200）：逐字 `标准号：DZ/T 0460-2023 标准名称：地质灾害自动化仪器监测预警规范 发布时间：2023-11-18 实施时间：2024-01-01 中国标准分类号：D02 国际标准分类号：07.060 批准发布部门：自然资源部`。
    ⚠ 该页是**第三方索引站**（页内自述 `本站为网络服务提供者及网络索引服务平台资源索引自网络/用户分享`），**无许可声明**；**标准全文我未能取得**（未打开、不可引用其条文数字）。
  - **专利 CN112927478B**（`https://patents.google.com/patent/CN112927478B/zh`，我打开读到正文）：
    书名项 **逐字**（Google Patents 页内）：`Publication number CN112927478B`；`Application number CN202011609221.0A`；`Inventor 胡辉 林兴立 张世元 胡荣`；`Current Assignee Guangzhou Hannan Engineering Technology Co ltd`；`Filing date 2020-12-30`；`Publication date 2022-09-13`；`Status Active`；`Current 2040-12-30 Anticipated expiration`；同族另有 `CN112927478A`。
    **定位方式**：该 HTML 全文**不含 `[0001]` 式段落编号**（我验证过），因此引用只能用**章节名 + 原文短语**（如 `Description → 背景技术`、`Description → 具体实施方式 → 3)加速度数据处理及阈值比对流程 ①`、`Claims (3) → 权利要求1 → 步骤S1 的 S1.3`）。Google 页自身另有免责声明：`The legal status is an assumption and is not a legal conclusion...`；**该页面未声明专利文献的再使用许可（未提供）**。
    背景技术 **逐字**：
    > `此外，在实际运行中，普适型监测设备往往采用较低监测频率的工作模式，例如1～2小时测量、发送数据一次，实际上1～2小时间隔内的工作周期仅为数分钟，其余大部分时间传感器及通讯模块均处于断电休眠状态，仅保留单片机内部时钟电路运行，以满足在固定时间内唤醒设备进行数据采、发等动作，期间若监测对象出现较大变形，无法及时测量并预警。`
    具体实施方式 **逐字**（**这是一条真实的占空比数字**）：
    > `可设置一次通电采集的时长为120s，采集间隔为1h/次，采样频率为100Hz，也可以根据配置更新指令要求灵活设置。`
    （→ 占空比 = 120 s / 3600 s ≈ **3.3 %**；休眠时"传感器及通讯模块均处于断电休眠状态，仅保留单片机内部时钟电路运行"。⚠ 注意 `1～2小时` 那句出现在**背景技术**，是对**既有设备**的描述与批评，不是本发明参数——引用时勿混淆。）
    摘要 **逐字**（佐证"改配置"确为下行指令）：
    > `通过物联网设备管理系统向普适性监测设备下达配置更新指令，改变数据上传周期与频次`
    方法权利要求/实施方式 **逐字**（**这是全报告里最直接证明"采集周期 ≠ 上报周期"的设备侧逻辑**）：
    > `S1.2若超过预设阈值，则开启无线通信模块电源，与物联网管理系统建立网络通信，发送监测数据；`
    > `S1.3若没有超过预设阈值，则比对当前周期是否为数据上传周期，若为数据上传周期，则打开无线通信模块电源，向云平台发送监测数据；若非数据上传周期，则在接收云平台回复的数据接收成功指令后，切断传感器、外部接口供电，进入休眠状态；`
    > `S1.1周期起始,普适型监测设备接收物联管理系统下发的配置指令设置配置信息,内部传感器与外部接口通电，达到通电稳定时长后，进行采集数据，初步开始阈值判断：`
    告警态节奏 **逐字**（**"事件期节奏"的设备侧定义：从加密直接切到不间断**）：
    > `当监测成果值达到配置更新阈值时，向物联网设备管理系统下发配置更新指令，修改参数配置，缩短数据采集周期、数据上报周期、回复等待时长等参数；`
    > `当综合预警等级达到预警状态，监测数据分析与预警系统发送配置更新指令，将数据采集周期、数据上报周期、回复等待时长等参数修改为不间断采集，普适型监测设备实时采集回传数据；`
    （→ 三层节奏：常态"采集周期/上传周期各自独立" → 超阈值"立即开通信模块上报" → 预警态"不间断采集"；且**休眠是显式状态**：`切断传感器、外部接口供电，进入休眠状态`。这三条比招标文件更细，因为它写的是**设备状态机**。）
- **它相对 Wang 2022 的定位**：节奏形态（**1 h 常态 + 形变时 1–5 min 加密**）与 Wang **高度一致**。所以它**不适合**当"差异大的场景"，正确用途是**反向支持**——证明"小时基 + 事件加密"是**中国普适型监测的行业惯例**，Wang 那个节奏片段**不是孤例**。而它带来的**新东西**是：**采样/上传两字段独立**、**功耗与供电的装置级数字**、**在线率与汛期离线上限**。这与"第二个独立业务场景"是两种不同性质的外部效力，建议分开表述。

### 4.2 备选 2：PermaSense 马特洪峰岩壁监测网（**唯一有"逐样本三时间戳"的来源**）

- 数据：`Weber, Samuel; Beutel, Jan; Cicoira, Alessandro (2024): In-situ measurements in steep bedrock permafrost in an Alpine environment on the Matterhorn Hörnligrat, Zermatt Switzerland: 2008-2023 [dataset]. PANGAEA, https://doi.org/10.1594/PANGAEA.967586`
  （更新版：`...2008-2024`，`https://doi.org/10.1594/PANGAEA.983718`，`Data set with annual updates`）
- 许可：**我打开 PANGAEA 页面读到的逐字**：`License: Creative Commons Attribution 4.0 International (CC-BY-4.0)`
- 论文（开放获取；我下载 PDF 并抽取正文）：Weber et al., 2019, *Earth Syst. Sci. Data*, 11, 1203–1237, `https://doi.org/10.5194/essd-11-1203-2019`
- **能读出的节奏数字 [原文]**：
  - 采样：`The data acquisition operation for both single-ended and differential measurements is configured with a static, periodic sampling rate strictly interleaving with networking operations, in our case **120 s**.`
  - 节点→基站转发：`Data are forwarded to a central data sink, a base station, connected to the Internet with a period of **30 s**.`
  - 聚合产品：论文 `generate **60 min** aggregates`；PANGAEA 摘要 `Timeseries derived data products: Cleaned and aggregated **hourly** values`
  - GNSS：Table 5 `Sampling interval` = **30 s**（MH42/MH33/34/35）、**5 s**（MH40/MH43）
  - 倾角计：`It is sampled every **120 s**`
  - → **采样(120 s) ≠ 转发(30 s) ≠ 聚合(3600 s)**，三层节奏齐全
- **自治方式 [原文]**：`autonomous, low-power wireless networked sensors`；`the sensor nodes have been running reliable and autonomous on the order of **years**`；`In cases of network congestion or loss of connectivity, e.g., due to excessive snow build-up or base station failures, data are kept back on local storage on every node using a mechanism called **backpressure**. For this a **1 GB** non-volatile Flash memory storage (SD card) is integrated on every node` —— **这就是 store-and-forward，与项目模型结构同构**
- **通信与中断 [原文]**：`a switch from **3G cellular** connectivity to **IEEE 802.11a 5 GHz WLAN** for long-haul connectivity`；`a (then significant) data gap from **June to August 2009** ... due to a failure in the cooling system of the server room and a longer outage of the server system`
- **最强的一点 [原文]**：`different timing information exists for every data sample referring to the **estimated generation time**, the **time of arrival at the base station** and the **time of storage in the database**` —— **逐样本三个时间戳**，正是首选最缺的那一项
- 规模：`17 different sensor types used at 29 distinct sensor locations consisting of over **231.6 million** data points`；论文给 `**83.8 GB** of data in 41 031 files`
- **读不出的量**：**休眠电流 / 占空比 / 太阳能板功率的具体值未提供**——我 grep 全文，`solar` 只出现在裂缝描述与"网络技术数据可用"的表述里
- **工程注意**：PANGAEA 该条目的数据本体是 `File content / Binary Object`（`Size: 46 data points`），即**打包交付**，不是逐列 CSV；真正的时间序列需经 `http://data.permasense.ch` 或 `https://git.uibk.ac.at/informatik/neslab/public/permasense/permasense_datamgr` 工具集拉取。**不满足"单文件 < 50 MB"**（总量 83.8 GB；只有"每年每点 ≈100 kB"的派生年文件是小文件）。
- **它填的坑**：**"采样 ≠ 上报"的实数分解** + **生成/到达/入库三时间戳** + **backpressure 补传**。若允许加两个场景，**建议首选 + 本备选一起**，因为它们补的是不同的轴。

### 4.3 备选 3：USGS 北卡滑坡站 + USGS 总入口的官方周期口径（**文字级，无原始时间戳**）

- URL（我均以浏览器 UA 打开成功，各 ≈95 KB）：`https://www.usgs.gov/programs/landslide-hazards/science/brights-creek-north-carolina`、`https://www.usgs.gov/programs/landslide-hazards/science/shumont-mountain-north-carolina`
  （⚠ 无浏览器 UA 时 `usgs.gov` 返回 **403**；加 UA 后 200）
- **逐字原文（两站同一句）**：`Data are updated every **30 minutes** and displayed on graphs.`
- 页面标注的监测量 **逐字**：`Recent Conditions Rainfall Soil Water Content Battery Voltage`
- 图注 **逐字**：`View of rain gage, monitoring station enclosure and **solar panel** above a steep slope draining into a tributary of Brights Creek.( Credit: Ben Mirus, USGS)`
- 站点背景 **逐字**：`The USGS and its cooperators at the North Carolina Geological Survey have installed instruments in a steep hillside at Brights Creek, approximately 15 km east of Hendersonville, North Carolina.`
- 事件背景 **逐字**：`View from above of a debris flow near the Brights Creek monitoring station that was triggered during **Hurricane Helene**.`
- 媒体权属 **逐字**：`Media Sources/Usage: Public Domain.`
- **USGS 滑坡实时监测总入口**——**推荐引这一页**：`https://www.usgs.gov/programs/landslide-hazards/science/landslide-monitoring-stations`
  （页面标题 `Landslide Monitoring Stations`，`Active`，页内 `By Landslide Hazards Program May 30, 2018`；⚠ 无浏览器 UA 时 `usgs.gov` 返回 **403**，加 UA 后 200。另一条等价路径 `https://www.usgs.gov/node/279671` 有同一句"update cycles"，但没有下面第 2、3 句）**逐字**：
  > `Continuous, real-time monitoring occurs at some sites and periodic monitoring occurs at others; the most recent measurements are provided online for a few of our monitoring sites. Graphs showing the most recent data are updated regularly with **update cycles ranging from 15 minutes to 24 hours**. **Updates may be interrupted occasionally by instrument, computer, or network malfunctions.** Landslide monitoring data and information provided on this website are preliminary and have not been reviewed for accuracy; therefore the data are subject to revision.`
  **同页站点清单逐字（节选）**：`Alaska: Sitka, AK`；`California: San Francisco Bay Area - East Bay (BALT1) near Castro Valley, CA`；`San Francisco Bay Area – Marin County (BALT2) Site near San Rafael, CA`；`San Francisco Bay Area – SF Peninsula (BALT3) Site near Brisbane, CA`；`San Francisco Bay Area – SF Peninsula (BALT4) Site near Pacifica, CA`；`U.S. Highway 50, CA`；`"Chips" (2021 Dixie Fire) near Belden, CA`
- **能读出的数字**：现场站常规更新间隔 **1800 s**；官方周期**取值域 15 min–24 h**；**官方明确"更新可能因仪器/计算机/网络故障而中断"**（可用来正当化"链路中断"是常态而非异常）；站点 ID `BALT1–BALT4` 可追溯到具体的旧金山湾区站点
- **读不出的量**：**没有暴露 CSV/API 端点**（图表站内渲染），**拿不到逐条时间戳**；采样间隔与上报间隔**未区分**；**无断连记录**；无功耗数值 → **只能做文字级节奏引用，不能从数据量周期**
- **价值**：论证 Cleveland Corral 的 15 min 与 Brights Creek 的 30 min **都在官方区间内**，不是异常样本；并提供"官方现场站周期 + 太阳能 + 电池电压遥测"的一条旁证

### 4.4 我尝试过但**未能打开**的（如实登记）

| 目标 | 结果 |
|---|---|
| `usgs.gov/information-policies-and-instructions/copyrights-and-credits` | **403**（CloudFront）；许可改用 ScienceBase `rights` + SDC JSON-LD `license` 佐证 |
| `sciencebase.gov/catalog/itemLinks?itemId=...` | 只返回登录页 HTML，**未取得**同级数据发布列表 |
| `www.mdpi.com/2411-9660/9/6/144`（HTML 与 `/pdf` 两路） | 均 **403**，未读到 MDPI 论文正文 |
| `pangaea.de/?q=Hörnligrat` 站内搜索结果页 | 结果 JS 渲染，静态 HTML 无命中项，未能站内枚举 |
| `gcy.zfcg.gxzf.gov.cn`（广西采购平台页面） | 连接失败（助手报告 000）；只有 PDF 直链可用 |
| `www.nrsis.org.cn`（自然资源部系统下载门户，含一份**部级**普适型设备文档的 `downportal?md5=...` 链接） | **http=000**（连接失败；我实测 `http://www.nrsis.org.cn/` 根域同样 000）。⚠ 该部级文档的**内容我从未读到**，因此**不引用它的任何句子**——这里只登记"它打不开"这一事实，避免后续重复尝试 |
| `www.mnr.gov.cn`（自然资源部主站） | **http=000** |
| `www.ccgp.gov.cn` 地方公告页（如 `.../202603/t20260317_26280639.htm`） | **http=502** |
| 青海候选公告页 `www.qhdzzbfw.gov.cn/ggzy/projectDetail.html?infoid=...` | **http=502**（故青海**只有 PDF 直链**，页面 URL 未取得） |
| 广西采购平台 `www.gcy.zfcg.gxzf.gov.cn` | **http=000**（故广西**只有 PDF 直链**，页面 URL 未取得） |
| 陕西 `ccgp-shaanxi.gov.cn` / 黄山 `ggzy.huangshan.gov.cn` / 湖南常德 `changd.ccgp-hunan.gov.cn` / 贵州 `ggzy.guizhou.gov.cn` 的附件直链 | 超时 / 502 / 打不开（助手报告，我未逐个复核——**引用前请自行打开**） |
| 挪威 NVE HydAPI | **需密钥（401）**；`api.nve.no/doc/jordskredvarsling/` 只有区域预报，**无遥测间隔数字** |
| 意大利 ARPA Lombardia CRMFD 滑坡监测网 | 页面可读，逐字列出子网 `RETE TOPOGRAFICA / RETE INTERFEROMETRIA RADAR / RETE IDROMETEOROLOGICA / MISURE MANUALI / TRASMISSIONE ED ELABORAZIONE DEI DATI`，但实时数据需申请（`Form richiesta dati automatici`），**间隔数字未提供**；ARPA Piemonte 监测页 404 |
| 日本 `river.go.jp`（川の防災情報） | **403**；MLIT 砂防 `https://www.mlit.go.jp/mizukokudo/sabo/` 仅文档 PDF，无遥测数据接口 |
| 意大利 CNR IRPI Gollone 滑坡页 | 页面 200，但正文**无可读的间隔文本**（助手报告；我未复核） |
| `DZ/T 0460-2023`、`DZ/T 0450-2023` 标准全文 | **未打开**（只见其被招标文件引用；DZ/T 0460 的元数据经第三方索引页确认，见 §4.1） |
| `zenodo.org`（记录页与 API，含 IPv4/IPv6/代理多路） | **反复 504 / 超时**（我本人实测 `api/records/13835721` 返回 504、`6228358` 超时）；因此 Zenodo 侧候选**未能打开记录页**，按纪律不列入候选 |

### 4.5 ⚠ 一个**不能当业务场景、但能标定链路**的 LoRaWAN 来源

这是唯一一个我**亲自打开并读到逐字字段**的 LoRaWAN 开放数据。**必须明确：它不是山区滑坡监测部署，因此不能作为"第二业务来源场景"**；它的正确用途是**给受扰链路（RSSI/SNR/丢包）标定**——补的是"LoRa 空口质量"这一轴，而不是"业务节奏"那一轴。

- DOI：`10.5061/dryad.w0vt4b939`；标题（Dryad API 逐字）：
  > `LoRaWAN gateway performance and vehicle tracking data in AERPAW testbed`
- 记录页：`https://datadryad.org/dataset/doi:10.5061/dryad.w0vt4b939`
- 许可（Dryad API `license` 字段逐字）：`https://spdx.org/licenses/CC0-1.0.html` → **CC0-1.0**
- 版本/日期 **[目录]**：`versionNumber: 4`，`publicationDate: "2025-02-04"`；作者 `Sergio Vargas Villar`，机构 `North Carolina State University`
- **场景（摘要逐字）**：`This dataset was collected during an experiment conducted during NC State's Packapalooza festival in August 2024. It evaluates the performance of LoRaWAN gateways by analyzing received telemetry data from a moving vehicle (i.e., helikite). Key metrics include Received Signal Strength Indicator (RSSI), Signal-to-Noise Ratio (SNR), transmission timestamps, and geographic data.`
  → **城市校园、节庆期间、移动载体（helikite）**，**不是山区、不是滑坡监测**（这正是它不能当业务场景的原因）
- **上报节奏（Methods 逐字）**：
  > `The experiment utilized a LoRaWAN-enabled LoStik IoT transmitter connected to a LattePanda MiniPC to transmit telemetry data at **1.5-second intervals**. The transmitted packets contained a combination of timestamps, unique package identifiers, and vehicle telemetry. The data was received by multiple RAK7289CV2-V1 LoRaWAN gateways deployed at different locations (LW1, LW2, LW3, LW4...`
- **包体（记录页 `Files and variables` 逐字节选）**：
  > `File: LoRaWAN_Gateway_Performance_and_Vehicle_Tracking_Data.7z`
  > `CSV Files : failed_tx_packages.csv : Logs of failed transmissions. gateway-dataRate-Table.csv : Summary of data rates grouped by gateway.`
  > `SigMF Files : LoRa_data.sigmf-data : Raw signal data including SNR and RSSI information ...`
- **列/字段名（记录页逐字节选）**：
  > `Received signal strength (rx_rssi)`、`Signal to noise ratio (rx_snr)`、`Reception timestamp (rx_time)`、`The channel used for receiving the data (rx_channel)`、`RF chain id used for receiving the signal (rx_rfChain)`、`Gateway geographic location (rx_location_latitude, rx_location_longitude, rx_location_altitude)`、`Gateway ID (rx_gatewayId)`、`Timestamp of the gateway (rx_timeSinceGpsEpoch)`、`Transmission frequency (tx_frequency)`、`Data rate and frame counter (tx_bandwidth)`、`LoRaWAN Data Rate (dr)`、`Spreading factor (tx_spreadingFactor)`、`GPS data (number_of_satellites)`
- **体积与格式**：`LoRaWAN_Gateway_Performance_and_Vehicle_Tracking_Data.7z` = **1.33 MB（`data-size="1325002"`）**，7z 内含 CSV + SigMF + README；另有 `README.md`
- **下载**：记录页提供 `/downloads/file_stream/3840956`；Dryad 的 API 全量下载端点在无凭据时返回 **401**（反爬），文件本体**我未能下载**，上述列名全部来自记录页文字
- **它填什么坑**：`rx_time`（逐包接收时间戳）+ `rx_rssi` / `rx_snr` / `tx_spreadingFactor` / `dr` + **`failed_tx_packages.csv`（失败传输日志）** → 这是项目里"受扰链路"最缺的那类**真实 LoRa 空口证据**（§3 第 3 条指出的空白）
- **它填不了什么**：与滑坡/泥石流业务**无关**；1.5 s 的发送间隔是**测试台主动灌包**，**不代表任何监测业务节奏**；无节点能量/供电信息；城市多网关覆盖与山区单网关场景不可直接迁移

### 4.6 附：**非滑坡业务**的多级节奏对照（全部注明"非滑坡"，仅作遥测节奏与 API 形态参照）

这三个我**亲自调用了 API 并读到返回**。它们**不是滑坡/泥石流监测**，因此**不能**充当"第二业务来源场景"；它们的价值是提供**同一地区/同一机构的官方遥测节奏取值**与**可直接调用的 API 形态**。

| 来源 | URL（我实测 200） | 我读到的节奏证据 | 是否滑坡业务 |
|---|---|---|---|
| **USGS NWIS 水文站 14211720**（WILLAMETTE RIVER AT PORTLAND, OR） | `https://waterservices.usgs.gov/nwis/iv/?format=rdb&sites=14211720&parameterCd=00060&period=P1D` | 返回列头逐字 `agency_cd site_no datetime tz_cd 117345_00060 117345_00060_cd`；数据行逐字 `USGS 14211720 2026-09-12 04:15 PDT -24900 P`，下一行 `04:20`、`04:25`、`04:30` → **间隔 300 s（5 分钟）**；质量列 `P`（返回头逐字 `Provisional data subject to revision`） | **否**（河流流量） |
| **瑞士 SLF / IMIS 山区测站网** | `https://measurement-api.slf.ch/public/api/imis/measurements?limit=3` | 逐字记录 `"station_code":"ADE2","measure_date":"2026-09-12T11:30:00Z"`，下一条 `12:00:00Z` → **间隔 30 min**；字段逐字 `TA_30MIN_MEAN`、`RH_30MIN_MEAN`、`VW_30MIN_MEAN`、`DW_30MIN_MEAN`、`HS`（雪深） | **否**（雪崩/积雪遥测） |
| **日本 JMA AMeDAS** | `https://www.jma.go.jp/bosai/amedas/data/map/20260913063000.json` | 返回 **1286 个站**；字段逐字含 `precipitation10m`、`sun10m`（10 分钟量）+ URL 时间戳 `...063000` 为 10 分钟粒度 → **10 分钟一版** | **否**（气象/雨量，是日本土砂灾害警戒的输入） |

**用法建议**：若项目只想加**一个**第二业务场景 → 用 §1 首选；若想加**一条节奏梯度**做敏感性 → 可把 **10 min（AMeDAS）/ 15 min（Corral）/ 30 min（NC 站、SLF）/ 300 s（NWIS）/ 600 s（Corral GPS）** 作为"常规周期"的取值集合，但**必须逐个标明哪些是滑坡业务、哪些不是**，不要把后三者的结论说成"滑坡监测场景"。

### 4.7 ⚠ 字段最全、但**几乎可以确定是合成数据**的 LoRaWAN 遥测集（**只能当 schema 模板**）

这是我在整个检索里见到的**唯一同时包含 睡眠/测量/发送电流 + 电池电压 + RSSI/SNR + 生成时刻与到达时刻 + 延迟 + 投递状态**的 LoRaWAN 表。**它的字段设计正好补上 §3 第 3、4、9 条指出的空白**；但它的**数值几乎可以确定是合成的**，因此**只能用来抄 schema、节奏形态与丢包模式，不能当作"真实部署经验证据"**。

- DOI：`10.17632/fn8h5h33ct`；记录页 `https://data.mendeley.com/datasets/fn8h5h33ct`
- 标题（DataCite 逐字）：`Integrated hourly soil, weather, energy, and LoRaWAN telemetry dataset from a solar-powered field monitoring system in Montería, Colombia (2025)`
- 发布者/年份 **[目录]**：`Mendeley Data`，`publicationYear 2026`；作者 `Parodi-Camaño, Tobias` / `Carriazo-Regino, Yulieth` / `Baena-Navarro, Rubén`
- 许可（DataCite `rightsList` 逐字）：`Creative Commons Attribution 4.0 International`（`cc-by-4.0`）
- 文件（我实测下载成功，**3,034,363 B**，`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`）：
  `https://data.mendeley.com/public-files/datasets/fn8h5h33ct/files/13250f26-d5bb-46cb-ad53-81abdfe3bc05/file_downloaded`
- 工作表 **[实测]**：`README / Inputs / Daily_2025 / Hourly_2025 / IoT_Node_Observations / Calibration_Log / Field_Event_Log / Data_Dictionary / Quality_Control_Rules / Monthly_Summary_2025`
- `IoT_Node_Observations` **[实测]**：**8,760 行 × 32 列**；列名逐字如下（**这就是可抄的 schema**）：
  `timestamp, device_id, sensor_node_serial, plot_id, plant_id, latitude, longitude, sensor_depth_cm, soil_moisture_raw, soil_moisture_vwc_pct, soil_temperature_c, soil_ph_raw, soil_ph_calibrated, battery_voltage_v, current_sleep_ma, current_measurement_ma, current_transmission_ma, firmware_version, connection_type, gateway_id, packet_id_sent, packet_id_received, node_timestamp, platform_received_timestamp, latency_seconds, payload_size_bytes, rssi_dbm, snr_db, delivery_status, telemetry_available_flag, calibration_status, maintenance_flag`
- **我实测到的量**：
  - 节奏：`timestamp` 相邻差值 **8,759 个全为 3,600.0 s**（无抖动）→ **采样间隔 = 上报间隔 = 1 h**；窗口 `2025-01-01 00:00 → 2025-12-31 23:00`
  - **能量/自治**：`current_sleep_ma` **0.04–0.186 mA**；`current_measurement_ma` **12.0–39.0 mA**；`current_transmission_ma` **55.0–140.77 mA**；`battery_voltage_v` **3.731–4.2 V** → 可直接算占空比与能耗
  - **双时间戳 + 延迟**：`node_timestamp`（生成）与 `platform_received_timestamp`（到达）**逐条都有**；`latency_seconds` **1.38–5.16 s**，其中 **`-1` 是"缺报"标记**（README 逐字：`latency_seconds=-1 is a missing-transmission marker and must be excluded from effective latency statistics.`）
  - **链路质量**：`rssi_dbm` **−120…−72**；`snr_db` **−4.7…15.0 dB**；`payload_size_bytes`
  - **丢包**：`delivery_status = {received: 8322, missing_telemetry: 438}`（与 `telemetry_available_flag` 1/0 一致）→ 全年得率 **95.0%**
  - 通信：`connection_type` 恒为 `LoRaWAN`；`gateway_id` 恒为 `GW_MON_001`；`sensor_node_serial` 恒为 `SN-MON-PLT-2025-001`（**单节点、单网关**）
- 🚩 **为什么我判定它"几乎可以确定是合成"（这是我自己读到的证据，不是转述）**：
  1. **恰好 8,760 行**、严格整点、全年无抖动 —— 真实野外 LoRaWAN 部署不会这样；
  2. **`packet_id` 自带合成痕迹**：`packet_id_sent` 的样例逐字为 `NODE_001-2025-00001`、**`NODE_001-2025-COMP-00001`**、`NODE_001-2025-COMP-00002`，而对应的 `packet_id_received` 是 **`MISSING-NODE_001-2025-COMP-00002`** —— `-COMP-` 后缀与 `MISSING-` 前缀看起来就是**为填补缺失而生成的占位记录**；
  3. **单节点 / 单网关**，`connection_type` 无变化，缺少真实部署的异质性；
  4. Description 自述是"structured on a **complete calendar grid** of 8,760 **expected** hourly observations"，即**先建网格再回填**的做法。
  → 因此：**可抄 schema、可抄"缺报用 -1 标记"这类工程约定、可用它的丢包率量级做压力测试**；但**不能**用它论证"太阳能现场节点 1 h 上报真实可得率是 95%"，也不能把它的 `current_*_ma` 当作实测器件功耗。
- **未复核线索（我未打开，仅供参考，勿引用）**：助手报告 **Dryad ARHO**（`10.6071/M39Q2V`，CC0-1.0）是**唯一确认的山区部署**——逐字 `from 1510 to 2723 m elevation on the western slope of the Sierra Nevada in California`、`at 15-minute intervals`、`water year 2014 through water year 2017`、组网为 `Metronome systems`（**非 LoRaWAN**）；文件 `American_River_sensor_network_2014-2017.zip` **1.37 GB**，**列名未确认**（README 在包内未打开）。若后续要补"山区 + 15 min"这一轴，值得再花一轮打开它。

---

## 5. 检索渠道与检索式清单（说明"确实找过"）

**渠道（全部实际访问过）**：`web_search`；ScienceBase Catalog API（`sciencebase.gov/catalog/item/<id>?format=json`、`/catalog/file/get/...`）；USGS Science Data Catalog（`data.usgs.gov/datacatalog/data/USGS:<id>`，含内嵌 JSON-LD 许可字段）；USGS Publications Warehouse（`pubs.usgs.gov`）；USGS 站点页（`usgs.gov`，**需浏览器 UA，否则 403**）；PANGAEA（`doi.pangaea.de`，`?format=text` 与 HTML 两种取法）；Zenodo 记录与 API；opendata.swiss CKAN API；PermaSense git 仓库与 ESSD 开放获取 PDF；Google Patents；中国政府采购/招标 PDF 直链；MDPI（**403，未打开**）。

**实际用过的检索式**：
1. `USGS real-time landslide monitoring station data sampling interval telemetry 15-minute`
2. `Chalk Cliffs Colorado debris flow monitoring real-time data USGS data release rainfall soil moisture stage interval`
3. `Hadley LaHusen 1995 "Acoustic Flow Monitor" technical manual USGS open-file report data acquisition telemetry power solar`
4. `普适型地质灾害监测预警 设备技术要求 采样间隔 上报频率 分钟`
5. `landslide monitoring LoRaWAN dataset Zenodo raw packet timestamps received`
6. `Illgraben debris flow monitoring dataset EnviDat WSL open data time series timestamps license`
7. `PermaSense Matterhorn wireless sensor network open data portal timestamps sampling interval duty cycle`
8. `MDPI Sensors LoRaWAN landslide monitoring system table sampling interval report interval sleep current duty cycle solar powered node`
9. `USGS landslide monitoring Shumont Mountain Brights Creek North Carolina "updated every 30 minutes" real-time station`
10. `USGS landslide monitoring "update cycles" "15 minutes to 24 hours" real-time stations`

**按要求排除、未再重复推荐**：意大利阿尔卑斯泥石流事件目录；尼泊尔 Bhote Koshi 落石/巨石位移数据集（检索中确实出现于 CEH / data.gov.uk，仅事件与地貌，**无遥测节奏**）。

**关于"开放 LoRaWAN 山区数据集（带逐条接收时间戳）"这条线 —— 这是本报告唯一的空白**：我另派了一路并行专项检索，并自己也直接试过 Zenodo API（**504 / 超时**）。最终**唯一被我亲自打开并读到逐字字段**的 LoRaWAN 开放数据是 Dryad 的 AERPAW 数据集（见 **§4.5**），而它是**城市校园测试台**，**不是山区、不是滑坡/泥石流业务**。
→ 因此结论是：**"山区 LoRa(WAN) 监测业务的开放遥测数据"这一轴，我没有找到符合要求的来源**。但这一轴的性质是**链路标定**（§4.5 可补 RSSI/SNR/失败累计），**不是业务节奏**——**"第二业务来源场景"这个任务本身已经找到（首选 §1，备选 §4.1–§4.3），不存在"没找到"的问题**。若要补齐山区 LoRa 遥测这一轴，需要单独一轮专项检索（Zenodo 在本网络不可达是主要障碍）。

---

## 6. 可直接下载的 URL、格式与列名（体积均 < 50 MB；**我只给 URL，不下载**）

> 下列 URL 均为我在取证过程中**实际成功下载过**的直链（ScienceBase `file/get` 直链形态）。许可：**CC0-1.0 公有领域奉献**（逐字见 §1.1）。

| 内容 | 体积 | URL |
|---|---|---|
| 15 分钟多传感器数据（42 个 CSV，按水文年） | **6,479,946 B** | `https://www.sciencebase.gov/catalog/file/get/65d8f08fd34ec3e1801e3efc?f=__disk__c8%2F95%2F0d%2Fc8950d9a624d974e0b6cfc27909535b41a497271` |
| 日值数据（5 个 CSV） | 100,977 B | `https://www.sciencebase.gov/catalog/file/get/65d8f08fd34ec3e1801e3efc?f=__disk__55%2F1f%2F43%2F551f438bde6184b042210725835b84cd274e7031` |
| 传感器说明（含起止日期与故障 `notes`） | 9,858 B | `https://www.sciencebase.gov/catalog/file/get/65d8f08fd34ec3e1801e3efc?f=__disk__99%2Fe0%2Fe6%2F99e0e629c519e708294dd68348536f25ca52b776` |
| 传感器坐标（UTM Zone 10N） | 10,045 B | `https://www.sciencebase.gov/catalog/file/get/65d8f08fd34ec3e1801e3efc?f=__disk__3f%2F08%2F3b%2F3f083b92d8b04eb9209024c94ad59b99286e6c87` |
| 元数据 XML | 18,951 B | `https://www.sciencebase.gov/catalog/file/get/65d8f08fd34ec3e1801e3efc?f=__disk__5d%2F95%2F0a%2F5d950a973c21e9ff770539297de848f11fe02f25` |
| **10 分钟 GPS 位移数据（单 CSV）** | **3,111,374 B** | `https://www.sciencebase.gov/catalog/file/get/64f10cebd34e09595516d84b?f=__disk__11%2F6d%2F4b%2F116d4bef89bb84fe6ae05a9074c59cb8451a30fe` |
| GPS 元数据 XML（含 §1.2 全部 procedure 步骤） | 12,927 B | `https://www.sciencebase.gov/catalog/file/get/64f10cebd34e09595516d84b?f=__disk__25%2Ffc%2Fe7%2F25fce71b9f1602b05fbba9e393a6eafa1c51f8a8` |
| GPS 发布另附：**`OPUSreport_detailed.txt`**（NGS OPUS 解算报告，基站坐标来源） | 15,651 B（`text/plain`，首行逐字 `FILE: base1600_rev.04o OP1706736825695` / `NGS OPUS SOLUTION REPORT`） | `https://www.sciencebase.gov/catalog/file/get/64f10cebd34e09595516d84b?f=__disk__e7%2F65%2F3d%2Fe7653db996e5492cd37437d2b2b655d58985a8dd` |
| GPS 发布另附：**`Cleveland_Corral_GPS_locations.jpg`**（接收机位置图，1609×3050） | 514,313 B | `https://www.sciencebase.gov/catalog/file/get/64f10cebd34e09595516d84b?f=__disk__7f%2Ffb%2F04%2F7ffb04c497ae4dadabe05b44489eafc9225b4486` |

**另（LoRa 链路标定用，非业务场景，见 §4.5）**：`https://datadryad.org/dataset/doi:10.5061/dryad.w0vt4b939`
→ 文件 `LoRaWAN_Gateway_Performance_and_Vehicle_Tracking_Data.7z`，**1.33 MB（1,325,002 B）**，许可 **CC0-1.0**；记录页下载路径 `/downloads/file_stream/3840956`。
⚠ Dryad 的 API 全量下载端点无凭据时返回 **401**，我**未能下载文件本体**，列名来自记录页文字。

**列名（逐字，来自我下载到的文件）**

15 分钟数据（例 `CCmiddle_WY2018.csv`，**第 4 行为表头**；第 1–2 行为引用串、第 3 行为站点/水文年标题）：
```
date_time_PST,mid_downslope_extensometer_cm_mid_E2_B,mid_shallow_piezometer_cm_mid_P1,mid_deep_open_tube_piezometer_cm_mid_P2,mid_upslope_mid_deep_driven_piezometer_cm_mid_P5,mid_downslope_mid_deep_driven_piezometer_cm_mid_P6,mid_precipitation_mm_mid_R,mid_cumprecipitation_mm_mid_R
```
数据行样例（逐字）：`10/1/2017 0:14,1.4,-0.2,-0.8,,0.5,0,0`
→ 时间格式 `M/D/YYYY H:MM`（**PST**，无秒）；空字段表示该传感器当时无数据。

toe 站（`CCtoe_WY2017.csv`，第 4 行）：
```
date_time_PST,toe_extensometerC_cm_toe_E5_C,toe_shallow_piezometerB_cm_toe_P7_B,toe_east_piezometerC_cm_toe_P8_C,toe_east_piezometerD_cm_toe_P8_D,toe_west_piezometerD_cm_toe_P9_D,toe_volumetric_water_contentA_toe_M1_A,toe_volumetric_water_contentB_toe_M1_B
```

日值（`CCmiddle_daily_1997_2002.csv`，第 4 行；注意 §1.6 的标题行错标）：
```
date,mid_upslope_extensometer_cm_mid_E1,mid_downslope_extensometer_cm_mid_E2_A,mid_shallow_piezometer_cm_mid_P1,mid_deep_open_tube_piezometer_cm_mid_P2,mid_deep_buried_pressure_transducer_cm_mid_P3,mid_precipitation_mm_mid_R
```

GPS 10 分钟（第 4 行为表头）：
```
date_time_UTC,easting_m,northing_m,orthometric_ht_m,ellipsoidal_ht_m,horizontal_displacement_m,3D_displacement_m
```
数据行样例（逐字）：`10/1/2016 0:59,724142.3988,4295109.672,1062.9386,1037.986632,,`
→ 时间格式 `M/D/YYYY H:MM`（**UTC**，无秒）；NAD83 UTM Zone 10N / NAVD88。

传感器说明表头（第 5 行起为数据）：
```
instrument name,location,parameter measured,instrument ID,units of measurement,start date,end date,manufacturer,model,serial number,piezometer construction type,depth: ground to sensor diaphragm (m) ,range of sensor,notes
```

---

## 附录 A：复现命令（每个数字都可回查）

```bash
# 1) 拉取两个数据集（体积见 §6）
curl -sL --max-time 240 "https://www.sciencebase.gov/catalog/file/get/65d8f08fd34ec3e1801e3efc?f=__disk__c8%2F95%2F0d%2Fc8950d9a624d974e0b6cfc27909535b41a497271" -o 15min.zip && unzip -q 15min.zip -d x15
curl -sL --max-time 180 "https://www.sciencebase.gov/catalog/file/get/64f10cebd34e09595516d84b?f=__disk__11%2F6d%2F4b%2F116d4bef89bb84fe6ae05a9074c59cb8451a30fe" -o gps.csv

# 2) 量节奏与断连（§1.3 全部数字由这段产生）
python3 - <<'PY'
import csv,glob,os
from collections import Counter
from datetime import datetime
def parse(f):
    out=[]
    for r in csv.reader(open(f)):
        if len(r)>1 and r[0].count('/')==2:
            for fmt in ('%m/%d/%Y %H:%M','%m/%d/%Y %H:%M:%S'):
                try: out.append(datetime.strptime(r[0].strip(),fmt)); break
                except ValueError: pass
    return out
base='x15/Cleveland_Corral_15_Minute_Data'
for station,pat in [('middle','Cleveland_Corral_middle_15minute/CCmiddle_WY*.csv'),
                    ('toe','Cleveland_Corral_toe_15minute/CCtoe_WY*.csv')]:
    ts=sorted(sum((parse(f) for f in glob.glob(os.path.join(base,pat))),[]))
    dl=[(b-a).total_seconds()/60 for a,b in zip(ts,ts[1:])]
    span=(ts[-1]-ts[0]).total_seconds()/60
    print(station,'rows',len(ts),'yield%',round(100*len(ts)/(int(span//15)+1),2),
          'exact900s%',round(100*Counter(round(d,1) for d in dl)[15.0]/len(dl),2),
          'gaps>30min',sum(1 for d in dl if d>30))
ts=sorted(parse('gps.csv'))
dl=[(b-a).total_seconds() for a,b in zip(ts,ts[1:])]
print('GPS rows',len(ts),'exact600s%',round(100*Counter(dl)[600]/len(dl),2),
      'gaps>1h',sum(1 for d in dl if d>3600),'max gap h',round(max(dl)/3600,2))
PY

# 3) 抽取 OFR 95-114 的事件规则原文（§1.4）
curl -sL --max-time 120 "https://pubs.usgs.gov/of/1995/0114/report.pdf" -o ofr.pdf
python3 -c "
import pypdf,re
r=pypdf.PdfReader('ofr.pdf'); t='\n'.join(p.extract_text() or '' for p in r.pages)
i=t.replace(chr(10),' ').find('alert mode'); print(t.replace(chr(10),' ')[i-700:i+700])"

# 4) 读出许可与目录日期（§1.1）
curl -sL "https://www.sciencebase.gov/catalog/item/65d8f08fd34ec3e1801e3efc?format=json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['rights']); print(d['dates'])"
curl -sL "https://data.usgs.gov/datacatalog/data/USGS:64f10cebd34e09595516d84b" | grep -o '"license": *"[^"]*"'

# 5) 现场站与总入口的原文（usgs.gov 需要浏览器 UA，否则 403）
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
curl -sL -A "$UA" "https://www.usgs.gov/programs/landslide-hazards/science/brights-creek-north-carolina" | grep -o "Data are updated every 30 minutes[^<]*"
curl -sL -A "$UA" "https://www.usgs.gov/node/279671" | grep -o "update cycles ranging from 15 minutes to 24 hours"

# 6) 中国普适型两份 PDF（§4.1）——我只读了这一条命令取出的文本
curl -sL --max-time 120 "http://oss-gxhlw.unicloudgov.com/guangxi-gov-open-doc/1014AN/450103/10007122169/20244/58ffcc03-4a5b-41aa-aa8b-1532b4350f6a.pdf" -o gx.pdf   # 229 页
curl -sL --max-time 120 "https://zcy-gov-open-doc.oss-cn-north-2-gov-1.aliyuncs.com/1023FP/639900/10007432686/20263/f7cc7e6b-471a-4501-a096-c0f447f4cd74.pdf" -o qh.pdf  # 65 页
python3 -c "
import pypdf,re
r=pypdf.PdfReader('gx.pdf'); t=re.sub(r'\s+',' ',r.pages[99].extract_text() or ''); i=t.find('运维成效要求'); print(t[i:i+700])"
```

---

*本文件为检索与取证记录；未改动仓库内任何其他文件，未运行项目实验脚本，未执行 git 操作。*
