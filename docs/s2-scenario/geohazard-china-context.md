# Real-World Context: Pre-Disaster Monitoring of Landslides and Debris Flows in Power-Constrained Mountainous China (Tibet focus)



**Compiled:** 2026-09-12
**Scope:** Pre-disaster (常态监测/预警) landslide and debris-flow monitoring in power- and communication-constrained mountain regions, especially 西藏.
**Purpose:** Establish the real-world, citable context for a research project on low-power, low-cost communication and signal-enhancement technology to guarantee continuous, stable communication for mountain monitoring nodes.

> **上面这句是合作方的诉求（场景背景），不是本文的研究中心。**
> 本文中心见 [`../../README.md`](../../README.md)：**agent runtime 位于通信实体之上，在它们动态上线/掉线/退化/恢复时维持任务执行**。
> 本文只提供支撑 README §1.2 与 §3.1 的场景与可靠性证据。

### How to read the evidence tags

Every claim below carries the URL it came from. Where a figure could not be verified, it is marked explicitly. Tags used:

- **[READ]** — figure/text read from a page or PDF that was actually fetched in this session.
- **[DERIVED]** — arithmetic performed on published coefficients from a [READ] source; the coefficients are quoted so the arithmetic is auditable. **Not** a published table value.
- **[SNIPPET]** — seen only in a search-engine result snippet; the underlying page was **not** independently opened. Treat as a lead.
- **NO QUANTITATIVE DATA FOUND** — searched and did not find a published number. These negative results are deliberate deliverables, not gaps to be papered over.

**No statistic, document number, or deployment figure in this report was invented.** Where sources conflict, both are shown.

---

## 1. Chinese policy drivers

### 1.1 《全国地质灾害防治"十五五"实施方案》 (2026)

**Document identity — verified.**

- Issuing body: 自然资源部办公厅 (General Office, Ministry of Natural Resources)
- Document number: **自然资办函〔2026〕1198号**
- Date of issue: **2026年7月15日**
- The full plan text is published as a PDF attachment (24 pages) and was read directly.
  - Notice page: <https://www.gov.cn/zhengce/zhengceku/202608/content_7078245.htm> **[READ]**
  - Plan PDF: <https://www.gov.cn/zhengce/zhengceku/202608/P020260817424806858745.pdf> **[READ]**
- News summary (新华社): <https://www.gov.cn/lianbo/202608/content_7077459.htm> **[READ]**

**What it actually requires regarding monitoring and data.**

The plan lists four 防治任务, the second of which is directly relevant: **实施地质灾害监测预警能力提升工程** (implement the geological-hazard monitoring and early-warning capability improvement project). Verbatim from the plan **[READ]** (PDF):

> 完善地质灾害群测群防体系，探索构建地质灾害风险区群测群防管控体系。优化自动化监测网；加密乌蒙山区重点区域和北方地区监测台站；强化与气象、水利、地震、应急管理等部门的监测数据共享，以雨量监测、含水率监测等为主要手段，分区分类推动构建地质灾害风险区监测骨干网。……健全国家—省—市—县地质灾害气象风险预警联动机制，优化递进式的地质灾害气象风险预测、预报、预警产品体系，探索开展县级地质灾害气象风险短临预警。

Translation of the load-bearing clauses: *optimise the automated monitoring network; densify stations in the Wumeng Mountains and the north; **strengthen monitoring-data sharing with the meteorological, water-resources, seismic and emergency-management departments**; build a geohazard **risk-area monitoring backbone network** using rainfall and moisture-content monitoring as the main means; and optimise the progressive (递进式) meteorological risk prediction–forecast–warning product system, exploring county-level nowcasting warnings.*

**Quantified construction targets (专栏 1 and 专栏 3, 2026–2030)** **[READ]** (PDF):

| # | Indicator | 2026–2030 target |
|---|---|---|
| 4 | 新建泥石流监测台站 — new **debris-flow** monitoring stations | **1,757** |
| 5 | 新建滑坡、崩塌监测台站 — new **landslide/rockfall** monitoring stations | **7,996** |
| 6 | 改建地质灾害监测台站 — stations to be **rebuilt/upgraded** | **7,213** |
| 7 | 运行维护已建地质灾害监测台站 — existing stations under **operation & maintenance** | **64,962** |
| 8 | 地质灾害点工程治理 (处) | 4,237 |
| 9 | 地质灾害排危除险 (处) | 6,128 |
| 10 | 地质灾害避险搬迁 (户) | 50,000 |

Debris-flow stations are to be sited with priority to cover 威胁 100 人以上的泥石流沟 (debris-flow gullies threatening more than 100 people). Landslide/rockfall stations are to be sited with priority at 重要灾害点 (important hazard points). The plan also notes an **"人工智能+地质灾害监测预警" pilot in 四川 and 湖北** **[READ]** (PDF).

**Scale of the problem, from the same plan and from 中国地质调查局** **[READ]**:

- As of end-2025, China had nearly **280,000** registered geohazard points in the national database, threatening **11.48 million** people and **¥760.1 billion** in property
  ([gov.cn](https://www.gov.cn/lianbo/202608/content_7077459.htm)).
- During 十四五, **27 provinces** built or rebuilt **75,000+ automated geohazard monitoring stations** with nearly **400,000 instruments/devices** installed, benefiting 5 million+ threatened people, with a cumulative **401 successful disaster forecasts** and **1,343 effective hazard warnings**, averting 7,000+ potential casualties
  ([中国地质调查局](https://www.cgs.gov.cn/ywdt/ddyw/202607/t20260707_864423.html)).

**Tibet-specific content in the plan.** The plan defines 21 地质灾害重点防治区 totalling ~3.25 million km², of which 297万 km² are the 17 sudden-onset zones. Three are directly relevant to Tibet **[READ]** (PDF):

1. **中雅鲁藏布江高山区滑坡崩塌泥石流重点防治区** — central-southern Tibet along the middle Yarlung Tsangpo mainstream and main tributaries, **~93,600 km²**; dominated by 高位远程滑坡 (high-position long-runout landslides), rockfalls and debris flows, with **chain-type (链生性) characteristics**; main triggers include rainfall, snow/ice meltwater, seismic activity, and transport/hydropower construction.
2. **怒江上游高山区滑坡崩塌泥石流重点防治区** — eastern Tibet, upper Nu River basin, north-west Hengduan Mountains, **~86,900 km²**; dominated by landslides, rockfalls and debris flows with pronounced high-position and long-runout chain behaviour; triggers include **freeze–thaw cycling (冻融循环)**, heavy rain, seismicity and road-cut slope engineering.
3. **横断山高山峡谷区滑坡崩塌泥石流重点防治区** — western Yunnan, western Sichuan, and **eastern Tibet**, **~234,600 km²**.

The plan explicitly cites 雅鲁藏布江下游水电开发等重大工程建设需求 as a driver for defining the key zones.

> **⚠ Important negative finding for the research framing:** the 十五五 plan document, read in full, contains **no explicit requirement about data-transmission continuity, reporting latency, device power supply, solar/battery sizing, or communication coverage**. Its only communication-adjacent words are about **data sharing between government departments** and the grouping of remote-sensing satellite data. Any claim that the 十五五 plan mandates a particular availability or power target would be **unfounded**. The communication-continuity mandate sits in the 工信部 policy (below) and in the standards (Section 2).

### 1.2 地质灾害监测预警能力提升工程

This is one of the four 防治任务 of the 十五五 plan (see 1.1). It is implemented through the 专栏 3 work deployment quoted above. **There is no separate standalone document titled 《地质灾害监测预警能力提升工程实施方案》 that could be located** — it is a programme within 自然资办函〔2026〕1198号 **[READ]**.

Related technical instruments that *do* exist and *do* carry transmission requirements are the geological-hazard industry standards, cited in the plan itself as normative references **[READ]** (DZ/T 0460-2023 reference list, <https://www.guifanku.com/8b01cbeb45985fa23a5b297ecea114ec.html>):

- **DZ/T 0460-2023** 《地质灾害自动化仪器监测预警规范》 — Specification for geological hazard monitoring and early warning by automation equipment
- **DZ/T 0439-2023** 《地质灾害监测预警设备检测技术要求》 — testing requirements for monitoring/warning equipment
- **DZ/T 0450-2023** 《地质灾害监测数据通信技术要求》 — **technical requirements for geohazard monitoring data communication**

Its scope, verbatim **[READ]**:

> 本文件规定了地质灾害自动化仪器监测预警工作的方案设计、仪器安装与运行维护、数据通信与数据库建设、预警实施、质量管理与过程控制等技术要求。本文件适用于滑坡、崩塌、泥石流等地质灾害自动化仪器监测预警工作。

The plan requires that monitoring data communication and databases be built to a single national standard, achieving connectivity across national–provincial–municipal–county and 群测群防员 levels, and calls for deepened IoT/big-data application **[READ]**:

> 建设全国标准统一的监测数据通信与数据库，充分利用已有系统及共享模式，实现国家级—省级—市级—县级—群测群防员互联互通，深化物联网、大数据等信息技术应用。

The monitored instrument set is defined in the standard as GNSS, 裂缝计 (crack meters), 倾角计 (tilt meters), 加速度计, 含水率仪 (moisture meters), 雨量计 (rain gauges), 泥（水）位计 (debris/water-level gauges) and **视频** (video) **[READ]** (DZ/T 0460-2023 §3.2).

> **⚠ Not verifiable here:** the **numeric** content of DZ/T 0450-2023 (sampling intervals, heartbeat intervals, retransmission/backfill rules, permitted data-loss) and **Appendix B** of DZ/T 0460-2023 (仪器设备主要技术参数表) sit inside paywalled document bodies. Only the tables of contents and scope could be read. Both standards should be obtained from a paid standards service (e.g. 万方标准: <https://d.wanfangdata.com.cn/standard/Ch9TdGFuZGFyZE5ld1NvbHI5UzIwMjYwNzE3MDI0MzAzEg5EWi9UIDA0NTAtMjAyMxoIMjJzZDZheWc%3D>) before any numeric claim is made.

### 1.3 工信部等十四部门《关于加强极端场景应急通信能力建设的意见》 (2025)

**Document identity — verified.**

- Title: 工业和信息化部等十四部门关于加强极端场景应急通信能力建设的意见
- Document number: **工信部联信管〔2024〕256号**
- Date: **2024年12月31日** (published/interpreted January 2025)
- Co-issuing bodies (14): 工业和信息化部、中央空中交通管理委员会办公室、国家发展和改革委员会、公安部、财政部、交通运输部、农业农村部、国家卫生健康委员会、应急管理部、中国气象局、国家能源局、国家林业和草原局、中国民用航空局、国家消防救援局
- Official URL: <https://www.miit.gov.cn/zwgk/zcwj/wjfb/yj/art/2025/art_80059e80ee8b4e659168ab1eebb41cc4.html> **[READ]**

**What it requires — the clauses that bear on this project, verbatim [READ]:**

The overall framing uses 底线思维、极限思维 (bottom-line thinking, extreme-case thinking) and makes **提升断路断电极端条件保障能力** (raising the ability to guarantee service under the extreme conditions of severed roads and power outages) one of the two handles of the policy.

**2027 targets (到2027年)**, verbatim:

> 应急通信步入高质量发展快车道，**空天地海一体**关键技术创新突破，极端条件适用装备有效供给……**灾害易发地区通信网络覆盖水平显著提升，通信网络抗毁韧性切实增强，公网专网协同格局基本形成。**指挥预警智能高效……**基层保底通信能力基本建立**，极端场景保障能力大幅跃升。

**Clauses most relevant to a telecom-engineering supplier:**

| Item | Requirement (verbatim excerpts) |
|---|---|
| （一）推进应急通信技术突破应用 | 推动**跨运营商应急漫游、无人机空中通信、室内定位导航、地下空间信号增强**等适用于极端场景的重点技术研发 |
| （二）研发推广新型应急通信装备 | 重点加强无人空中载体装备、全地形车、**高空基站**等高机动性装备，**应急专网融合终端、背包基站、微波/散射通信装备**等轻量化便携装备，**适应严寒、密林等极端条件装备**以及更适合基层使用的易操作高可靠性设备研发推广 |
| （三）构建应急通信创新发展平台 | 组织制定应急通信标准体系，加强**应急预警、网络抗毁、互联互通**等标准研制 |
| （七）完善资源统筹信息共享机制 | 建立应急通信装备、队伍及易发**"断路、断电、断网"高风险区域台账** |
| （八）推进电信企业管理制度改革 | **电信企业建立应急通信指挥机制，设立应急通信专门机构** |
| （九）增强重点地区通信网络覆盖 | 统筹利用**公众通信网、专用通信网、卫星通信网**，重点提升**灾害多发易发地区、重点国有林区、边境地区、重要国省干线**等的网络覆盖水平。推动**卫星网与地面网的融合协同和统一调度** |
| （十）提高通信网络抗毁韧性水平 | 开展**通信网络抗毁能力普查评估**；**适度提升通信基础设施建设标准**；加快在**易灾乡镇建设超级基站** |
| （十一）建设专网通信支撑服务能力 | 充分利用**甚小口径终端（VSAT）、天通、北斗、高通量、低轨星座**等卫星通信资源，形成统一调度、高效供给和融合应用的**天基应急通信能力** |
| （十二）增强应急通信指挥预警能力 | 加强**铁塔、通信、电力数据共享**；基于**小区广播**技术建强通信网预警信息传播能力……实现**秒级、靶向、安全**的预警信息发布 |
| （十五）加强基层保底应急通信能力 | 基层……要强化**天通卫星电话**等通信装备配备。推动**易灾乡镇、行政村、国有林场强化天通、北斗短报文、应急专网融合终端等小型、易用装备预置和维护** |
| （十七）强化制度建设 | 加大对**灾害多发易发地区政策倾斜**力度 |
| （十八）强化资金投入 | 充分利用现有资金渠道，支撑极端场景应急通信能力建设各项任务……**电信企业每年要安排充分资金保障应急通信工作** |

**Official problem statement** (from the gov.cn 解读, 2025-01-21) **[READ]**:

> 但是，面对极端灾害场景，也暴露出应急通信能力还存在**机制体制有待健全、通信网络韧性有待增强、基层保底通信手段欠缺、保障队伍装备水平不高**等短板弱项。

> **Assessment.** This policy is the strongest and most precise policy hook for the partner's stated problem. It (a) names **断路、断电、断网** as the extreme scenario, (b) puts **北斗短报文 and 天通 explicitly in the "基层保底" (grassroots fallback) tier** for 易灾乡镇/行政村/国有林场, (c) calls for **extreme-condition equipment adapted to 严寒 (severe cold) and 密林 (dense forest)** — which is exactly the Tibet/high-altitude case, and (d) makes **抗毁韧性 and coverage in 灾害多发易发地区** an explicit target. Note that its orientation is emergency response; the **pre-disaster routine-monitoring** framing comes from the 自然资源部/地灾 side, not from this document.

**Two clauses need their addressee kept straight, because it changes the commercial reading:**

- **Item （八）「电信企业建立应急通信指挥机制，设立应急通信专门机构」 is an obligation on 电信企业 (telecom *carriers*), not on suppliers.** 中通服 is a **supplier to carriers**, not a carrier. This clause therefore creates *demand from CCS's customers* rather than a duty on CCS — it should not be cited as something CCS is required to do.
- **Item （四）「建设应急通信产业集群，打造具有核心技术优势的骨干企业……发布指导性产品目录」** is the clause that creates a **supplier-side opportunity**: a state-endorsed emergency-communications product catalogue and industrial cluster. For a partner seeking to position a low-power mountain-monitoring communication product, this is the most directly actionable clause in the entire document.

---

## 2. What monitoring stations actually measure, and how much power they use

### 2.1 The measured quantities and instrument set

The normative instrument set for 滑坡/崩塌/泥石流 automated monitoring, from **DZ/T 0460-2023 §3.2** **[READ]**: GNSS, 裂缝计 (crack meter), 倾角计 (tilt meter), 加速度计 (accelerometer), 含水率仪 (soil moisture), 雨量计 (rain gauge), 泥（水）位计 (debris/water level), and 视频 (video). The 十五五 plan adds that the 风险区监测骨干网 should use **雨量监测、含水率监测** as 主要手段 (rainfall and moisture content as the main means) **[READ]**.

For 泥石流 the standard's instrument list plus standard practice adds 泥位 (debris-flow stage/depth) and, in research-grade observatories, 次声 (infrasound) and 微震/地震 (seismic). **Note:** 孔隙水压力 (pore-water pressure) and 次声 (infrasound) appear in research and reservoir-landslide monitoring rather than in the normative 普适型 instrument list — see 2.4 and the caveat there.

### 2.2 Sampling intervals and data volumes

| Quantity | Sampling interval | Data volume | Evidence |
|---|---|---|---|
| GNSS displacement | Configurable: **采样间隔 0s–24h** on a 普适型 GNSS station; **data update rates 60 s, 15 s, 5 s, 1 Hz, 2 Hz, 5 Hz, 10 Hz** | "GNSS 原始观测值每秒产生数十 KB" (raw GNSS observations produce tens of KB per second); reduced at the edge to "每次几百字节" (a few hundred bytes per transmission) | **[READ]** 米度 M50 spec: <https://www.shmedo.cn/m50ythzgdgnssjcz>; **[READ]** 千寻位置: <https://www.163.com/dy/article/L4KNQLAL05561PS9.html> |
| BeiDou RDSS test transmission interval | **1 min** (data-packet send interval, per BD 420012—2015 test basis) | — | **[READ]** 《基于北斗三号区域短报文通信的滑坡灾害监测数据传输方案设计》, 导航定位与授时 2023, 10(3): 96-107: <https://dhdwyss.spacejournal.cn/article/id/dhdwyss_20230311> |
| Tilt / acceleration (MEMS, in the same GNSS station) | Same 采样间隔 0s–24h range; 倾角精度 ±0.01°, 加速度精度 ±1 mg | Small (a few values per report) | **[READ]** 米度 M50: <https://www.shmedo.cn/m50ythzgdgnssjcz> |
| Repeat reporting cadence in a deployed BeiDou scheme | **正常状态下每小时上报一次状态信息；异常状态下立即触发短报文告警** (hourly status in normal state; immediate short-message alarm on anomaly) | ~hundreds of bytes | **[READ]** 千寻位置: <https://www.163.com/dy/article/L4KNQLAL05561PS9.html> |
| Debris-flow seismic (research observatory) | **100 ms** sampling (蒋家沟) | Large | **[SNIPPET→verified via NCDC metadata API]** see Section 7 |
| Debris-flow kinematics (research observatory) | **1 s** sampling (蒋家沟) | Large | same |
| Soil moisture at depth (Illgraben observatory, comparator) | **5 min** | 165,780 points across 4 depths | **[READ]** EnviDat CKAN API, see Section 7 |

> **⚠ Not found:** a normative table of *required* sampling intervals and permitted data volumes per 测项. These are in DZ/T 0450-2023 and DZ/T 0460-2023 Appendix B, which are paywalled (see 1.2).

### 2.3 Power draw — the only published numbers found

**The most useful published figure found separates sensing from transmission** (风途 FT-WY1 北斗短报文 GNSS 位移监测站) **[READ]** <http://www.ftiot.net/Article-656491.html>:

- **传感器 + LoRa = 0.6 W** (sensing + local radio, idle)
- **传感器 + LoRa + 数据上传 = 0.96 W** (sensing + radio + uplink active)
- → **uplink transmit adds ≈0.36 W** over the idle sensing+radio state.

This is a vendor specification, not an independent measurement, and it is the *only* published same-device idle-vs-transmit power pair found. It is a defensible anchor for modelling transmit duty-cycle energy, and it should be labelled as vendor-sourced in any paper.

**Other power-relevant published figures:**

| Item | Figure | Source |
|---|---|---|
| Ultra-low-power LPWAN chipset for Tibetan Plateau landslide crack data | **< 0.4 W** total for wide-area coverage (哈达玛扩频调制, SWIC 基带芯片, 40 nm ULP process) | **[READ]** 西藏自治区科学技术厅, 北斗遥感"智"护高原: <https://sti.xizang.gov.cn/xwzx/qnkjdt/202508/t20250808_494188.html> |
| 普适型 GNSS module with integrated MEMS tilt/vibration | **< 0.4 W** | same source |
| A tilt sensor specified in a Guizhou public-procurement document | **倾角仪待机功耗 ≤ 50 mW**; 倾角量程 ±30°; −40 ℃~85 ℃; 防护等级 ≥IP66 | **[SNIPPET]** <https://ggzy.guizhou.gov.cn/hallweb/hall/attach/nosession/download?attachId=8a8bb7d59e0d7f1c019e2af4dd3f40ff> — attachment could not be downloaded |
| LoRa link transmit distance specification (Chinese research network) | **> 3 km** | **[READ]** 《复杂环境山地灾害监测智能感知与数据传输关键技术》, 科学技术与工程 2025, 25(2): 640-648 |
| Device operating temperature range (普适型 GNSS) | **−40 ℃ to +75 ℃**; storage −50 ℃ to +85 ℃; IP68; **MTBF ≥ 50,000 h** | **[READ]** 米度 M50: <https://www.shmedo.cn/m50ythzgdgnssjcz> |

### 2.4 How no-grid deployments size solar panel and battery — published numbers

This is the crux of the partner's problem, and there **are** real published configurations. All are design targets, not measured field reliability.

| Configuration | Solar | Battery | Claimed autonomy / load | Source |
|---|---|---|---|---|
| 成都理工大学 solar power supply study (design + lab test, Chengdu) | **30 W** PV | **12 V / 70 Ah** sealed lead-acid | Load **0.6 W @ 5 V**; max charge current **1.47 A**; **15 consecutive rainy/overcast days (15 个阴雨天)** | **[READ]** 王洪辉 等,《地质灾害监测设备太阳能高效供电技术研究》, 自动化与仪表 2011, v.26(9):43-46, DOI 10.19557/j.cnki.1001-9944.2011.09.011: <https://faculty.cdut.edu.cn/wanghonghui/zh_CN/lwcg/72727/content/41706.htm> |
| 华西/杰芯 X1 普适型 GNSS 接收机 | "low-power design reduces the required solar configuration" (no W figure) | **100 Ah** battery | **30 consecutive rainy days (连续 30 个阴雨天)** | **[READ]** <http://www.huasi-measure.com/huasicekong/products/25533052.html> |
| 米度 M50 integrated self-powered GNSS station | Integrated panel (no W figure) | Integrated high-capacity Li-ion (no Ah figure) | **阴雨天典型工况下续航超 90 天**; **提前 30 天低电量告警** | **[READ]** <https://www.shmedo.cn/m50ythzgdgnssjcz> |
| 华测 H7 integrated GNSS station | Integrated solar module | Integrated | **阴雨天典型工况下续航超 90 天**; 提前 30 天电量告警 | **[READ]** <https://www.huace.cn/informationDetail/380> |
| 北斗短报文 + AI camera solution (image-bearing, hence much larger) | **60–120 W** | **20–60 Ah Li-ion** | "**连续 7–15 天**阴雨无间断运行" | **[READ]** <https://www.dyst.com.cn/solution7/1422.html> |

**Interpretation, stated carefully.** Consuming only published vendor/design claims, the relationship is roughly: *solar array in the tens of watts and a battery in the tens of Ah buys on the order of 15–30 rain-days for a sub-1 W sensor node; going to ≥90 rain-days requires either a ~100 Ah battery or an integrated design with adaptive duty-cycling; and adding imaging pushes the array to 60–120 W and costs autonomy (7–15 days).* Every one of these is a **vendor claim**, not an independently measured field result. Two of the ~90-day claims come from different vendors describing the same architecture pattern (自适应变频 / 嵌入式休眠 + 提前30天电量告警), which is suggestive of a common industry design convention rather than independent validation.

> **NO QUANTITATIVE DATA FOUND** for: industrial power-supply sizing standards for 普适型 stations; measured mean-time-between-power-failure (MTBPF); measured battery state-of-health degradation over a Tibetan winter; or measured fraction of nodes lost per winter to power exhaustion. See Section 5 for the physics and Section 4 for the deployment negative results.

---

## 3. 北斗 (BeiDou) short-message / RDSS backhaul — real constraints

### 3.1 BeiDou-3 capability (published)

| Parameter | Value | Source |
|---|---|---|
| **Regional** short-message (区域短报文) max single message | **14,000 bits ≈ 1,000 Chinese characters** | **[READ]** 科普中国《北斗短报文通信介绍》 <https://www.kepuchina.cn/article/articleinfo?ar_id=400216&business_type=100&classify=0>; identical figure in **[READ]** <https://www.163.com/dy/article/INK4K0AP05565WV5.html> and **[READ]** 千寻位置 <https://www.163.com/dy/article/L4KNQLAL05561PS9.html> |
| **Global** short-message (全球短报文) max single message | **560 bits ≈ 40 Chinese characters**, via 14 MEO satellites | **[READ]** 科普中国 (same URL) |
| Terminal transmit power | **可降低到 3 W 以下 (< 3 W)** | **[READ]** 科普中国 (same URL) |
| Message success rate | **区域短报文成功率优于 99.6 %; 全球短报文成功率优于 96.46 %** | **[READ]** 科普中国 (same URL) |
| Latency | 短消息通信时延 **约 0.5 s**; 点对点通信时延 **1~5 s** | **[READ]** 科普中国 (same URL) |
| System inbound capacity | **优于 1,000 万次/小时** (better than 10 million inbound transactions per hour) | **[READ]** <https://www.163.com/dy/article/INK4K0AP05565WV5.html> |
| Frequency bands | S/L band satellite transmission | **[READ]** 科普中国 (same URL) |

### 3.2 Transmission-frequency limit — the binding constraint

The **服务频度 (service frequency)** is defined as the *minimum interval between a terminal's inbound applications for positioning, communication, or position reporting* **[READ]** (<https://blog.csdn.net/pgiot20170801/article/details/163128405>):

> 服务频度指的是北斗终端入站申请定位、通信、位置报告等服务的最短时间间隔。它直接决定了单位时间内的入站次数，也直接影响系统的入站容量分配。

**Current commercial standard product (2026):** the state operator 中国时空信息集团 (China Spatiotemporal Information Group — described as 国家北斗民用短报文唯一运营服务主体) standard product is stated as **"2 级 6 档组合，即单条 131 个汉字、最短发送间隔 120 秒"** — i.e. **131 Chinese characters per message and a minimum send interval of 120 seconds** **[READ]** (<https://blog.csdn.net/pgiot20170801/article/details/163128405>). The same page states that **civilian users can currently only apply for a Grade-2 card (民用只能申请二级卡)**, and that **card issuance fee is a uniform ¥35 per card**, with communication service fees at a national uniform standard charged by usage mode and message count.

The page's frequency and message-length tables themselves are rendered as images and could not be extracted, so the graded ranges are **not** verified here.

**Conflicting/older figure — flag explicitly.** An academic thesis cites a 2015 CSNO statement that regional short-message service was extended to China and surrounding areas with **maximum single transmission raised to 14,000 bits, but that for ordinary users the single transmission does not exceed 628 bits** **[SNIPPET]** (search-result citation of CSNO 2015, host document at <http://center.shao.ac.cn/shao_gnss_ac/publications/Thesis/Songziyuan_The%20Research%20on%20Real-Time%20Precise%20Positioning%20Method%20Based%20on%20BDS-3%20Global%20Satellite%20System%20Service.pdf> — the PDF body could not be fetched; only 240 bytes returned). **The 628-bit general-user limit and the 131-character (≈1,048-bit) current commercial product limit are not consistent, and this report does not resolve which applies to a given card class.** Anyone quoting a message-length limit for a deployment must obtain the actual card's 通信等级 from the operator.

> **⚠ NO QUANTITATIVE DATA FOUND** for: 北斗 short-message **per-message energy cost in joules or mAh** at the terminal; published per-message or per-year **tariff numbers** for industrial RDSS cards (the ¥35 figure is the *card issuance fee only*, and the service fee is described as usage-based and not published as a rate); and the **maximum number of terminals per GEO beam** as a design limit.

### 3.3 Published 地质灾害 monitoring deployments using BeiDou short message

**Documented, with numbers:**

1. **BeiDou-3 RSMC landslide monitoring data-transmission scheme** — 王纯, 杜源, 黄观文 等, 《基于北斗三号区域短报文通信的滑坡灾害监测数据传输方案设计》, 导航定位与授时 2023, 10(3): 96-107 **[READ]** <https://dhdwyss.spacejournal.cn/article/id/dhdwyss_20230311>
   - Tested scheme: **base station on 4G + monitoring station on BeiDou-3 RSMC** (基准站采用4G、监测站采用北斗三号RSMC)
   - **Average transmission success rate 98.46 %**
   - **Average solution latency better than 1.1 s**
   - Real-time monitoring-series accuracy: **horizontal better than 1 cm**; vertical centimetre-level
   - **Test conditions:** BD 420012—2015 performance test basis, **data-packet send interval 1 min**
   - **Not stated:** node count, site location, duration, or whether field or bench. **Do not** cite 98.46 % as network-level availability.

2. **千寻位置 (Qianxun SI) BeiDou-3 short-message scheme for off-grid geohazard monitoring** **[READ]** <https://www.163.com/dy/article/L4KNQLAL05561PS9.html>
   - Hardware: **QX-RD55-301 数传终端 + edge-computing device**; GR2 普适型 GNSS receiver has short-message integrated
   - Architecture — the key engineering idea for the partner's problem: **edge computing + short message**, because "GNSS 原始观测值每秒产生数十 KB 数据，如果直接通过短报文传输，通信频次和数据量远超短报文容量限制". The device performs preprocessing and feature extraction locally and transmits **only the positioning result (3-D coordinates + displacement increment) and a warning flag**, reducing volume "从每秒数十 KB 压缩到每次几百字节"
   - **Smart triggering**: device-side preliminary warning judgement; short message sent only on anomaly; routine data stored locally and backfilled when 4G returns; **normal state reports hourly, anomaly triggers immediately**
   - **Dual-channel automatic switching**: 4G preferred (no frequency limit); automatic switch to BeiDou short message within seconds when 4G is unavailable, with no manual intervention
   - **Validated at**: a **Tibet glacier monitoring project at ~5,000 m altitude (西藏海拔5000米的冰川监测项目)** and a **flash-flood monitoring project at 3,000+ m (海拔3000余米的山洪监测项目)**. "方案已在西藏海拔5000米的冰川监测项目和海拔3000余米的山洪监测项目中验证"
   - Cost comparison given: fibre ~**数万元 per km**; satellite terminal equipment ~**数万元** with monthly fees of **数百至上千元**; the BeiDou short-message terminal is stated to be 远低于卫星通信终端 and suitable for large-scale deployment (no number given)

3. **西藏 林芝市波密县多格烈村 冰雪灾害监测试验点** — LoRa mesh + BeiDou RDSS short message, with 4G for long-cycle backhaul; UAV-deployed nodes; altitude 3,100–3,250 m; **measured average packet loss 2.3288 %** with a full 8-row loss table at **1-minute RDSS message interval**; LoRa stable to **5.421 km through blocking terrain** **[READ]** full PDF: <http://stae.com.cn/ch/reader/create_pdf.aspx?file_no=2402229&flag=1&year_id=2025&quarter_id=2> (王惠明, 刘志明, 何娜, 朱星 等,《复杂环境山地灾害监测智能感知与数据传输关键技术》, 科学技术与工程 2025, 25(2): 640-648)
   - **Test conditions caveat, important:** the packet-loss table itself was measured in **四川西部凉山彝族自治州无人山区** as a *simulation* of the plateau environment at **< −5 ℃** with only **2–3 BeiDou satellites and 3–4 beams visible**; only the long-cycle environmental test ran at the Bomi site (temperature range **−23 ~ 5 ℃**, 22 mm cumulative rainfall). **Do not describe the 2.3288 % table as a Tibet measurement.**

4. **Huawei/Hi-Target 普适型 devices trialled in Tibet** — 中海达 states its 普适型 geohazard monitoring equipment **passed a trial in Tibet (在西藏通过试用)** **[READ]** <https://www.zhdgps.com/newsDetails/xizangshiyong> (see Section 4.2 #8 for the full trial detail: 26 台套, 4G + 北斗短报文 dual mode, 断网自动重拨重连 and 自动补发数据). Hi-Target design claim: **100 Ah battery supports 30+ consecutive rainy days** **[SNIPPET]**.

5. **Tibet autonomous region BeiDou + remote sensing landslide monitoring system** — "遥感＋北斗" system, reported to have been applied at **20 typical hazard sites** across SW/NW/SE China, with **早期识别率 90 % 以上 (early identification rate above 90 %)** and a **2023 西藏自治区科学技术奖二等奖**. Its transport layer breaks through a domestically-controlled LPWAN (**< 0.4 W**). Claim: 灾害早期识别率达90％以上, 在西南、西北、东南等20处典型灾害区得到了成功应用 **[READ]** <https://sti.xizang.gov.cn/xwzx/qnkjdt/202508/t20250808_494188.html>

> **⚠ NO QUANTITATIVE DATA FOUND** for: how many nodes in a real Tibetan geohazard network actually run on BeiDou short message as the *primary* link (as opposed to failover); the fraction of time the short-message path is used; or any field-measured short-message latency/energy for a geohazard deployment.

---

## 4. Real deployments with numbers — and the reliability data that does not exist

### 4.1 The headline negative result

**Measured telemetry reliability for Chinese landslide/debris-flow monitoring networks essentially does not exist in the published, reachable literature.** Chinese sources publish **scale** (station and device counts) and **outcomes** (successful warnings, people evacuated, losses avoided) freely. Metrics such as 数据到报率, 数据完整率, 在线率, 掉线次数, 供电故障率, 设备离线率, 链路可用性, 中断时长 and 节点损失统计 surface **almost exclusively as contractual requirements or as qualitative complaints — with no number attached.** Genuine measured percentages were found for exactly **two** Chinese links, and both are **link-level tests, not network operations** (Section 4.2 #2 and Section 3.3 #1).

**The single most important structural finding:** the Guangdong standard 《地质灾害自动化监测规范》 sets the *acceptance* bar at **在线率 ≥ 70 %** — in the explicit condition 在供电和通信通道畅通时 — while vendor and tender documents speak of **95 %**. **Anyone quoting ~95–99 % availability for Chinese 普适型 monitoring networks is quoting an aspiration or a contract clause, not a measurement.** The very existence of a Xi'an municipal meeting titled 「市资源规划局召开普适型监测设备在线率问题推进会」 (a "promotion meeting on the problem of online rate of 普适型 monitoring devices") is itself evidence that online rate is an acknowledged operational problem — but the page could not be retrieved and yielded no number **[SNIPPET]** <http://zygh.xa.gov.cn/ztzl/ztxchd/fzjz/617116b1f8fd1c0bdc5ba93e.html>.

**A methodological warning that applies to the whole field, from the one good multi-year dataset that does exist.** At the Hochvogel high-alpine site, daily transmission reliability looks excellent (**97.3–100 %**) while the same network's reliability at hourly resolution is **96.7–99.4 % for crack meters but only 56–65 % for snow-buried laser sensors** — and the authors' explicit finding is that **the probability of missing data increases with higher temporal resolution**, because suboptimal conditions and transmission problems are usually short-lived (Section 4.2 #9). **Consequence for this project: any reliability figure quoted without a stated temporal aggregation window is close to meaningless.** A network can be 99 % reliable daily and catastrophically unreliable during the specific short high-rainfall windows when a landslide warning matters. Aggregation window is the first question to ask of any availability number, including the project's own.

### 4.2 Deployments with actual numbers

| # | Location / network | Nodes | Period | Comm tech | Reported numbers | Source |
|---|---|---|---|---|---|---|
| 1 | **西藏自治区** — provincial 普适型 network (拉萨/林芝 focus) | **660 灾害点位, 3,582 台设备** (2021) | network as of 2021; paper 2024 | not stated in abstract | **Qualitative only:** 误报率偏高, 成功案例少, 数据质量不可靠, 部分设备本区不宜使用. **No percentage published.** This is the most on-target paper in the whole search and it still reports no numeric 误报率/在线率/到报率/完整率 | **[READ]** abstract: <https://med.wanfangdata.com.cn/Paper/Detail/PeriodicalPaper_xzkj202405009>; DOI 10.3969/j.issn.1004-3403.2024.05.009 |
| 2 | **西藏 林芝市波密县多格烈村** 冰雪灾害监测试验点 | **4-node and 8-node** configurations | 2025 publication | **LoRa mesh + 北斗RDSS**, 4G for long-cycle | **Average packet loss 2.3288 %**; per-run 1.11 %–3.75 %; **LoRa stable to 5.421 km with terrain blockage**; test env **< −5 ℃**, only **2–3 BeiDou satellites / 3–4 beams**; long-cycle field temp **−23 ~ 5 ℃** | **[READ]** <http://stae.com.cn/ch/reader/create_pdf.aspx?file_no=2402229&flag=1&year_id=2025&quarter_id=2> (**measured in Liangshan, Sichuan — a simulated plateau site — not in Tibet**) |
| 3 | **云南省 昆明市** — 监测预警设备 O&M renewal project | **176 处** (2020–21 build) | 2025-12 contract doc | — | **Required** 在线率 **≥ 95 % 汛期 / ≥ 90 % 非汛期** (requirement, not measurement); cost **3 万元/处**; the project explicitly aims to 降低虚警率 with no baseline given | **[READ]** 昆明市自然资源和规划局: <https://zrzygh.km.gov.cn/c/2025-12-08/5040682.shtml> |
| 3b | **河南省 洛阳市、信阳市** — 普适型 monitoring stations | **70 余处台站, 443 台（套）设备** | 野外验收 2024-09-27~30; 终验 2024-10-23 | **4G** | Tender requirement **设备在线率 ≥ 95 %**; reported outcome only as 设备在线率**良好** — **no measured percentage**; 1 successful warning in Xinyang | **[READ]** 中海达: <https://zhdgps.com/case/henandizhizaihai> |
| 4 | **湖北省 十堰市** — professional monitoring network | **2,732 处** | 2017–2024 | — | **36 successful warnings**, **190 people** evacuated over 19 evacuations, **¥226,218,300** losses avoided. Also: 设备稳定在线率偏低, 误报率偏高, 超期服役设备运维管理工作难度大 (all qualitative) | **[READ]** 中国地质灾害与防治学报: <https://www.zgdzzhyfzxb.com/article/doi/10.16031/j.cghc.202505001?st=aipub> |
| 5 | **广东省 珠海市** — rainfall-threshold warning model | — | — | — | **预警准确率 91.5 %, 命中率 94.7 %, 漏报率 5.3 %, 空报率 16.2 %** — these are **rainfall-threshold model skill, NOT network reliability**. Label accordingly | **[SNIPPET]** |
| 6 | **全国 (national)** | **27万余处** registered hazard points; automated monitoring points **5万多处** (2024-08) vs **6.7万处** (2024–25) | 2024–2025 | — | 2024: **253 起** successful warnings, **42** successful forecasts, **116** effective hazard warnings. 2024–25: 地灾 **5,719 起**, 成功避险 **622 起**, 避免伤亡 **10,235 人**, **7.25 亿元** avoided. 十四五 totals: **75,000+ stations, ~400,000 instruments, 401 successful forecasts, 1,343 effective warnings, 7,000+ potential casualties averted** | **[SNIPPET]** for the 2024/2025 counts; **[READ]** for 十四五 totals: <https://www.cgs.gov.cn/ywdt/ddyw/202607/t20260707_864423.html>. ⚠ **The 5万 and 6.7万 figures are different vintages — cite with dates, do not merge or average them.** |
| 7 | **西藏 昌都市江达县波罗乡白格村 (金沙江白格滑坡)** — emergency monitoring, 2018 | **21 套专业监测设备 = 10 裂缝 + 8 地表位移 + 3 北斗短报文**, helicopter-delivered in 3 sorties; 18 + 3 commissioned by 2018-10-22 | trigger 2018-10-11 07:00; deployment from 10-14 | **北斗短报文 (RDSS)** where there was no terrestrial coverage | Reporting cadence during slow deformation: **简报一日一报**, accelerated as deformation increased — a qualitative cadence, **not** a rate. **No 在线率/到报率/掉线次数/供电故障数 published.** Note: the failure site is administratively **Tibet** (江达县), though the event is usually discussed as Sichuan/Yunnan | **[READ]** 深圳市北斗云: <http://m.northdoo.com.cn/nd.jsp?mid=318&id=296&groupId=14> |
| 8 | **西藏** — 普适型 equipment trial (中海达), organized by 中国地质环境监测院 / 自然资源部地质灾害技术指导中心 | **26 台套** — 雨量计、声光报警器、泥位计、断线报警器 | trial reported 2024-02-19 | **4G + 北斗短报文 dual mode**, explicitly to 解决监测现场信号不稳定带来的风险，提升数据通讯的冗余度 | Design claims: 阴雨天气下可正常工作 **30 天以上**; **断网监控、自动重拨重连**; network recovery triggers **自动补发数据**; periodic self-check status reporting. **No percentages published** — outcome stated as 成功通过试用 | **[READ]** <https://www.zhdgps.com/newsDetails/xizangshiyong> |
| 9 | **Hochvogel, Allgäu Alps, 2,592 m** (non-China comparator) | **10–12 geotechnical sensors** — crack meters, laser distance meters, inclinometers, rain gauge | **operational since Oct 2019; >5 years analysed** | **LoRa, transmitting every 10 min**; many sensors at the **edge of radio range — 2,800 m horizontal / 1,500 m vertical to the gateway, mostly without direct line of sight** | **Daily transmission reliability 97.3–100 %** for most sensors; **hourly 96.7–99.4 % for crack meters but 56–65 % for the laser distance sensors** (snow-covered several months per year). **Probability of missing data increases with higher temporal resolution** | **[READ]** Leinauer & Krautblatter, EGU25-11121, DOI 10.5194/egusphere-egu25-11121: <https://meetingorganizer.copernicus.org/EGU25/EGU25-11121.html>. The full paper is *Quantifying the effective reliability of geotechnical high-alpine real-time monitoring systems*, Engineering Geology, **DOI 10.1016/j.enggeo.2026.108984** — ⚠ **the full paper's abstract could not be read** (ScienceDirect returned a JavaScript shell), so all figures above come from the EGU25 abstract |

### 4.3 Standard thresholds that DEFINE the metrics — including the transmission-latency requirement

This is the most directly useful normative content found for the project, because it is where a **data-transmission-timeliness** requirement actually exists in Chinese practice.

**Source: 《地质灾害自动化监测规范》 (广东省地方标准草案 DB 4XXX)**, 广东省自然资源厅归口, drafted by 广东省地质环境监测总站 & 深圳市地质局 **[READ]** full standard PDF: <http://www.gddzxh.com/editor/net/upload/file/20230113/6380922404268591718962374.pdf>

**Clause 11.3.1 系统数据采集、传输要求 — the published Chinese acceptance thresholds, verbatim:**

| Clause | Requirement |
|---|---|
| a) | 在**供电和通信通道畅通时**，自动化监测数据采集设备应正常工作，且**在线率 ≥ 70 %** |
| b) | 采集的数据中误差应与设备标称精度相符 |
| c) | 自动化监测数据应完整，且**粗差比 ≤ 10 %** |
| d) | **数据采集时间间隔不应大于 120 min**；**现场数据采集至传输监控终端时间间隔不应大于 5 min** |
| e) | **数据采集缺失率不应大于 3 %**；因设备损坏无法修复/设备更换及不可抗力造成的数据缺失不计入应测数据个数；计算方法按 **DL/T 5211 附录 B** 执行 |

**Clause 9.4.6** requires the warning platform to provide real-time dynamic visualisation of 在线状态、在线率、监测数据的完整性、粗差比、采样间隔、时效性 as well as alarm statistics **[READ]**.

**附录 I 监测设备动态质量评价方法及标准** — the standardised metric taxonomy **[READ]**:

- Primary indices with weights: **设备状态 (D) 25 %**, **数据质量 (Q) 55 %**, **预警误报 (W) 20 %**
- Eight secondary indices: **在线状态 DS、在线率 DR、设备类型 DT、完整性 QC、粗差占比 QR、采样间隔 QI、时效性 QT、误报次数 WN**. **DS and QC are control conditions**; the rest are quantitative.
- **在线率 (DR) definition:** 在线率 = **设备实际数据上传的次数 / 统计时段内应上传的次数 × 100 %**
- **在线率 scoring bands:** ≥90 % → 0.15; 80–90 % → 0.10; 70–80 % → 0.05; **<70 % → 0**
- **完整性 (QC):** binary 0 or 1 — the upload must contain the key data items and acquisition time
- **粗差占比 (QR) bands:** ≤3 % / 3–5 % / 5–10 % / >10 %; 粗差 defined as |error| > 3σ (拉依达准则)
- **Composite quality score ω:** [0.9, 1] 优 · [0.8, 0.9) 良 · [0.6, 0.8) 合格 · **< 0.6 不合格**

**Two conclusions follow, and both matter for the project:**

1. **The acceptance bar for 在线率 is ≥70 %**, with a **3 %** data-loss ceiling — and even the top scoring band only starts at 90 %. The wording 在供电和通信通道畅通时 ("when power and communication channels are unobstructed") is an explicit acknowledgement in the standard that the power/communication path is the assumption most likely to fail. **Any claim that Chinese 普适型 networks achieve ~95–99 % availability is a vendor/tender aspiration, not the standards baseline and not a published measurement.**
2. **A hard data-transmission requirement does exist**: field acquisition to transmission terminal **≤ 5 min**, and acquisition interval **≤ 120 min**. This is the concrete, citable continuity/timeliness target the project can design against — it comes from the Guangdong local standard, not from DZ/T 0450-2023 (which remains paywalled, Section 8.3).

**Contrast with tender requirements:** 昆明 **≥95 % 汛期 / ≥90 % 非汛期**; 河南 洛阳市/信阳市 **≥95 %** in the 招标 technical requirements.

### 4.4 Explicit negative results — metrics with ZERO published values found

For **every** item below, a search was run and **no published value exists** in any reachable source. **These are the most valuable results in this section for a research project, because they define the gap the project could fill.**

1. **数据到报率 (data return rate)** — no numeric value for any Chinese network, province or site.
2. **数据完整率 (data completeness rate)** — no numeric value; only the standard's ≤3 % *requirement* and qualitative 数据完好率偏低.
3. **在线率 as a MEASURED value** — not found for any Chinese deployment. Only three *requirements* (昆明 ≥95 %/≥90 %; 河南 ≥95 %; Guangdong ≥70 %). The two sources that discuss it substantively call it **偏低** without a number.
4. **掉线次数 (number of disconnections)** — no published count anywhere.
5. **供电故障 / 供电故障率 / power failure counts** — **no published count or rate.** Only design-level statements. The qualitative complaint 供电不稳 appears without quantification.
6. **设备离线率 (device offline rate)** — no published value.
7. **节点损失统计 (node-loss statistics)** — no source found reporting how many nodes were lost, destroyed, abandoned or decommissioned.
8. **链路可用性 (link availability) and 中断时长 (outage duration)** — no published values for any Chinese deployment. The closest quantitative result in the entire search is **packet loss** (2.3288 %, Section 4.2 #2) and **single-scheme transmission success** (98.46 %, Section 3.3 #1) — neither is a network availability figure.
9. **误报率 as an operational network metric** — no numeric value for any Chinese network; two sources call it 偏高 qualitatively.
10. **漏报率 for an operational network** — no numeric value; only the Zhuhai model figure.

**Regions/sites requested where NO reliability data was found (and in several cases no data at all):**

- **重庆 — 三峡库区** (白水河, 八字门, 树坪, 新滩, 链子崖). The 专业监测年报汇编 exist as dataset metadata only; the underlying reports were not retrievable, and metadata contain no 在线率/到报率.
- **甘肃 — 舟曲 (2010), 黑方台, 兰州.** No reliability data. 黑方台 has three reported successful BeiDou early warnings of loess landslides, but no station counts or failure statistics. A LanZhou University thesis 《甘肃滑坡与泥石流监测体系评价与数据分析研究》 exists and is exactly on-topic, but `ir.lzu.edu.cn` failed with a TLS error — **this is the highest-value unread source for Gansu**.
- **贵州 — 水城, 纳雍, 六盘水.** No data. Only device specs from a procurement attachment (倾角仪待机功耗 ≤50 mW).
- **云南 — 东川蒋家沟泥石流 / 小江流域.** No reliability data, though the station publishes long time-series datasets.
- **四川 — 汶川, 茂县, 丹巴.** No reliability data at these specific sites.
- **西藏 — 樟木/聂拉木, 易贡, 雅鲁藏布江沿线, 川藏铁路沿线.** **No reliability data found for any of these.** Tibet coverage in the reachable evidence is provincial (拉萨/林芝, 2021), Bomi, 江达白格, plus a device trial.
- **招标/中标公告 stating 建设规模 AND 在线率 requirements together** — only one such document (昆明) was read in full.

> **Method caveat to carry forward.** All CNKI access failed on certificate-name errors (`ERR_CERT_COMMON_NAME_INVALID`), and some provincial sites failed on TLS. The Tibet paper's numeric 误报率 may exist in its paywalled body. **The negatives above are negatives over reachable sources, not proof of non-existence.**

---

## 5. Why mountain links break — with published numbers

Full detail, with per-figure provenance, is in `evidence/sub-link-physics.md`. The load-bearing results:

### 5.1 Rain fade — and the important negative result

**ITU-R P.838-3** publishes the governing specific-attenuation coefficients k and α. Table 5 **begins at 1 GHz**: e.g. at 1 GHz **k_H = 0.0000259, α_H = 0.9691**; 10 GHz 0.01217/1.2571; 30 GHz 0.2403/0.9485; 60 GHz 0.8606/0.7656 **[READ]** <https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.838-3-200503-I!!PDF-E.pdf>

**[DERIVED]** from those published coefficients, at **50 mm/h** rain rate: **γ_R ≈ 0.0011 dB/km at 1 GHz** (≈0.011 dB over a 10 km link — negligible), versus **1.66 dB/km @ 10 GHz, 2.44 @ 12 GHz, 5.72 @ 20 GHz, 9.82 @ 30 GHz, 13.2 @ 40 GHz**. At 100 mm/h: 5.53 @ 12 GHz, 11.9 @ 20 GHz, 19.0 @ 30 GHz.

> **This is a first-order finding for the project's framing: rain is NOT a first-order failure mechanism for sub-1 GHz LoRa or for NB-IoT/cellular bands.** Rain is first-order only for Ku/Ka satellite backhaul. **However — P.838 publishes no coefficients below 1 GHz, so published LoRa-band (433/470/868/915 MHz) rain attenuation figures do not exist**, and no independent *measured* LoRa-rain attenuation study was reachable. ITU-R P.530 could not be retrieved (404 on nine URL variants).
>
> **NO PUBLISHED FIGURE FOUND** for: measured rain attenuation at LoRa or NB-IoT/cellular bands; ITU-R P.530 figures; sandstorm attenuation; numeric fog dB/km table.

### 5.2 Vegetation — ITU-R P.833-10 Table 1 **[READ]**

| Frequency | Attenuation | Max attenuation A_m |
|---|---|---|
| 105.9 MHz | **0.04 dB/m** | 9.4 dB |
| 466.475 MHz | **0.12 dB/m** | 18.0 dB |
| 949 MHz | **0.17 dB/m** | 26.5 dB |
| 1852 MHz | **0.30 dB/m** | 29.0 dB |
| 2117.5 MHz | **0.34 dB/m** | 34.1 dB |

In-leaf trees are **~20 % greater dB/m** than leafless at ~1 GHz. Seasonal swing is **2 dB @900 MHz** and **8.5 dB @2200 MHz**. Austria pine model: L = 0.25·f^0.39·d^0.25·θ^0.05.

> **NO PUBLISHED FIGURE FOUND** for the wet (rain-soaked) versus dry foliage delta — a meaningful gap for a project about rain-time link failures.

### 5.3 Snow and ice on antennas/radomes **[READ]** (TRB SR185 185-049)

- A water film on a radome: **~18 dB/mm at 24 GHz** (dry board only 0.2 dB)
- **Wet snow ~0.33 m thick → 8.5 dB loss at 11 GHz**; measured natural deposit 0.2 m on a cone radome
- Rotating de-icing works only above **−3 °C** and costs **100 W** (0.5 m sphere) / **26 W** (0.8 m cone) at 300 rpm

> **NO PUBLISHED FIGURE FOUND** for snow/ice loss at sub-1 GHz, nor any icing outage statistics. **The de-icing power figures (26–100 W) are nonetheless directly relevant to the partner's power budget problem** — anti-icing consumes 1–2 orders of magnitude more than the sensor node itself.

### 5.4 Extreme cold reducing battery capacity — critical for Tibet **[READ]**

| Chemistry | Capacity versus temperature | Source |
|---|---|---|
| **LiFePO4** (Victron Lithium Smart datasheet) | **100 % @25 °C → 80 % @0 °C → 50 % @−20 °C**; **charge range +5 °C to +50 °C** (discharge −20 to +50 °C) | **[READ]** |
| **NMC622** (peer-reviewed, Leng et al. 2017, J. Electrochem. Soc.) | **68.4 % @0 °C, 43.5 % @−10 °C, 11.3 % @−25 °C** at 1C; aged-cell resistance **~109 vs ~30 Ω·cm² (>3× rise)**; documented **lithium plating** | **[READ]** |
| **VRLA lead-acid** (Chilwee GB12-28) | **102 % @40 °C, 100 % @25 °C, 85 % @0 °C, 65 % @−15 °C**; internal resistance 9.0 mΩ @25 °C | **[READ]** |

**Why this matters for Tibet specifically:** the Bomi test site measured field temperatures of **−23 ~ 5 °C** and the simulation site **< −5 °C** (Section 4.2 #2). At −20 °C a LiFePO4 pack delivers **half** its rated capacity and **cannot be charged at all** below +5 °C — so a battery sized on rated Ah will under-deliver by ~2× in a Tibetan winter, and cold-temperature charging must be managed. This directly explains the partner's "most sites lack adequate power supply" statement, and it is the closest thing to a quantitative mechanism for it that could be found.

> **NO PUBLISHED FIGURE FOUND** for lead-acid below −15 °C, Li-ion below −25 °C, or the fraction of capacity lost to lithium plating in a field duty cycle.

### 5.5 Terrain blockage and Fresnel obstruction — ITU-R P.526-13 **[READ]**

Knife-edge diffraction loss **[DERIVED]** from the published J(ν) expression: **6.0 dB at ν=0, 13.9 dB at ν=1, 19.0 dB at ν=2, 22.4 dB at ν=3**. The double-edge correction is valid only when each edge loss exceeds ~15 dB; model accuracy is quoted at ±2 dB.

> **NO PUBLISHED FIGURE FOUND** for the fraction of obstructed links in any real mountain deployment, and no deployment obstruction statistics at all. Note the contrast: with LoRa at ~0.12 dB/m foliage loss, **a single ~20 dB knife-edge obstruction costs more link budget than 150 m of forest** — geometry dominates vegetation.

### 5.6 Lightning — with Chinese, on-target evidence **[READ]**

From 《基于云闪引起自动气象站故障分析》 (2024): Anyue County, 2021 recorded **23,675 lightning flashes, of which 18,820 (79.5 %) were cloud flashes and 4,855 were ground flashes**. **Ten cloud flashes within 1 km over ~4 minutes destroyed BOTH the primary and backup HY3000 data loggers**, with a loss of **¥33,600**. The paper also documents damage at a Chengdu Shuangliu airport automatic weather station (2016), 2008 Nanle (4 time slots lost), 2006 Weifang, and 2005 Shangqiu (hub + 6 computers).

> **NO PUBLISHED FIGURE FOUND** for a **lightning damage rate (雷击损坏率)** for Chinese monitoring stations, or for **Tibet lightning density** — the Tibetan Plateau lightning literature is identifiable (Qie et al. 2022 GRL doi 10.1029/2022GL099894; Li et al. 2020 Atmos. Res. 245:105118; Ma et al. 2021 JTECH 38(3):511–523) but every full-text host blocked the proxy. The cloud-flash result is arguably more important than density anyway: it shows the failure mode is **induced surge from nearby cloud flashes**, which ordinary lightning-rod protection does not address.

### 5.7 Animals, theft, vandalism

The only figure obtained is non-Chinese: rodents do **17 %** of fibre damage on a US network **[SNIPPET]**. **NO PUBLISHED FIGURE FOUND** for Chinese mountain stations, or for theft/vandalism rates anywhere.

### 5.8 Cloud/fog — ITU-R P.840-9 **[READ]**

Liquid water density **ρ_l = 0.05 g/m³** (medium fog, ~300 m visibility) and **0.5 g/m³** (thick fog, ~50 m visibility); γ_c = K_l·ρ_l dB/km. Significant only above ~100 GHz, hence **not a factor for sub-1 GHz mountain links** despite the frequent presence of cloud and fog in Tibetan valleys.

---

## 6. The 中通服 angle

Full primary-source evidence file: `evidence/sub-annual-report-policy.md` (627 lines, all figures read from downloaded annual reports).

### 6.1 What 中国通信服务 actually is

- **中国通信服务股份有限公司** (China Communications Services Corporation Limited, "CCS", **0552.HK**), a state-owned telecom-engineering group spun out of China Telecom.
- **FY2025 revenue: RMB 150,092,609 thousand (≈RMB 150.1 billion)**; FY2024: RMB 150,000,103 thousand. FY2025 segment split **[READ]** (<https://www.chinaccs.com.hk/tc/ir/reports/ar2025/ar2025.pdf>, PDF p.41):

| Segment | FY2025 (RMB'000) | FY2024 (RMB'000) | Change | Mix 2025 |
|---|---:|---:|---:|---:|
| 电信基建服务 TIS | **74,391,260** | 75,172,237 | (1.0 %) | 49.6 % |
| 业务流程外判 BPO | **44,061,421** | 43,459,018 | +1.4 % | 29.3 % |
| 应用、内容及其他 ACO | **31,639,928** | 31,368,848 | +0.9 % | 20.9 % |
| **Total** | **150,092,609** | 150,000,103 | +0.1 % | 100 % |

- Within TIS: **construction services RMB 61,014,658 thousand**, design services RMB 8,939,972 thousand, project supervision and management RMB 4,436,630 thousand. Within BPO: **network maintenance RMB 19,118,078 thousand**. Within ACO: **system integration RMB 19,398,374 thousand**, software development & support RMB 7,114,106 thousand.
- H1 2026 revenue: RMB 74,480,006 thousand **[READ]** (<https://www.chinaccs.com.hk/tc/ir/reports/ir2026/ir2026.pdf>, PDF p.24).
- **FY2025 profit:** 本年利潤 **RMB 3,749,738 thousand**; 本公司股東應佔利潤 **RMB 3,610,019 thousand**, **+0.1 % YoY**; **basic EPS RMB 0.521**; free cash flow RMB 795 million **[READ]** (FY2025 AR, 財務概要 PDF p.260 and MD&A PDF p.39).

**Note on document language:** all CCS report PDFs on the `/tc/` path are **Traditional Chinese**; there is **no simplified-Chinese PDF edition** (`/sc/.../ar2025.pdf` → HTTP 404). Keyword searches for simplified forms return 0 hits even where the concept is plainly present (text reads 應急通信, not 应急通信).

### 6.2 Relevant subsidiaries (named in the FY2025 annual report, note 47, PDF pp.254–258)

CCS's annual report lists only **"若干子公司"** — a *selected subset*, not the full register. Those with direct relevance to the partner's geography and problem:

| Subsidiary | Capital | Business |
|---|---|---|
| **四川省通信产业服务有限公司** | RMB 798 M | 综合电信支撑业务 in Sichuan |
| **雲南省通信產業服務有限公司** | RMB 238 M | Yunnan |
| **重慶市通信產業服務有限公司** | RMB 209 M | Chongqing |
| **貴州省通信產業服務有限公司** | RMB 131 M | Guizhou |
| **甘肅省通信產業服務有限公司** | RMB 129 M | Gansu |
| **青海省通信服務有限公司** | RMB 68 M | Qinghai |
| **新疆維吾爾自治區通信產業服務有限公司** | RMB 195 M | Xinjiang |
| **中國通信建設集團有限公司** | RMB 550 M | 综合电信支撑业务 across northern provinces |
| **中通服軟件科技有限公司** | USD 25 M (60 %) | software |
| **中通服供應鏈股份有限公司** | RMB 1,256 M (73.99 %) | supply chain |

Also named elsewhere in the FY2025 report: **中通服諮詢設計研究院有限公司** (ESG p.113, p.115), **中通服節能技術服務有限公司** (ESG p.111), **通服智能技術有限公司**. **No Tibet-region subsidiary appears** in the disclosed list — Tibet is presumably served via a branch/分公司 rather than a separately capitalised subsidiary, but **this could not be verified from the annual report**.

> **⚠ The full CCS subsidiary register is not in the annual report and was not obtained.** A corporate group-structure page exists at <https://www.chinaccs.com.hk/sc/about/gp_structure.php> but was not opened. **No Tibet-specific CCS legal entity is verified.**

### 6.3 What CCS actually does that bears on this problem

**(a) Remote-area coverage via solar-powered base stations — the closest documented capability.** The FY2025 AR (ESG, PDF p.113 = printed p.116) reports **[READ]**:

> 本集團下屬**中通服諮詢設計研究院有限公司**打造**新疆阿克蘇零碳光儲一體系統沙漠地區應用項目**，通過建設**113 處完全由光伏和儲能供電的通信基站**，有效服務鐵路沿線、油田作業區和農牧民生活區，不僅解決了**偏遠地區網絡覆蓋難題**，更以「零碳智慧基站」的創新模式……

**113 communications base stations powered entirely by PV + storage**, solving remote-area network coverage. This is the single most transferable CCS capability for the partner's problem: **off-grid solar-storage base-station engineering at scale in a Chinese extreme environment.**

**(b) 应急安全 (emergency & safety) as a strategic business line.** FY2025 AR, 董事長報告書 (PDF p.17) **[READ]**:

> （四）應急安全領域 …… 在應急管理方面，聚力打造**「應急+安全」行業解決方案**，面向**氣象、水利、化工、礦山**等重點行業強化專業服務與價值輸出，助力全國多地應急能力提升，在**「人影工程」、基層防災**等領域取得突破。

And 業務概覽 — 戰新業務 (PDF p.25) **[READ]**:

> 在應急方面，以**應急、消防、生態環境、水利、氣象、自然資源、林草**等行業領域為業務主線，聚焦防災減災救災和急難險重突發公共事件處置保障能力，構建大應急完整性智慧產品集、解決方案庫以及一站式信息化服務能力，為政府、化工園區、高危企業等客戶提供**諮詢設計、軟件開發、系統集成及運維**等服務。

**(c) A named product — 「通服應急」** (product no. 4, FY2025 AR PDF p.35) **[READ]**:

> **通服應急** — 以諮詢規劃為引領，以安全應急產業為業務主線，面向工業生產、城市及生態安全三大領域，聚焦**監測預警、應急指揮、防災減災**，打造**安全生產風險監測預警平台、應急救援指揮平台**、化工園區智能化管控平台、工業互聯網+企業安全……**智慧水利信息化管理平台、森林火災風險監測預警平台**等為核心的大應急大安全應用產品圖譜，覆蓋應急、礦山、消防、水利、氣象、**自然資源**等多行業。

Note: the portfolio explicitly covers **监测预警 (monitoring & early warning)** and the **自然资源 (natural resources)** sector — but the named platforms are 安全生产风险监测预警, 应急救援指挥, 森林火灾风险监测预警 and 智慧水利. **No geological-hazard (地质灾害/滑坡/泥石流) monitoring platform product is named.**

**(d) Satellite capability.** FY2024 AR (PDF p.18) names an actual product **[READ]**:

> 聚焦攻關未來產業關鍵技術，發力5G-A、區塊鏈、人工智能+、**衛星通信**、低空經濟等前沿領域，打造區塊鏈數據服務平台、**直連衛星產品「星極通」**、網聯無人機智能應用平台以及人工智能產品集。

FY2025 AR (PDF p.16) reports 衞星互聯網 as a 新型基礎設施 with new-contract value growth of **近40 %** year-on-year. **This is the strongest satellite evidence item in CCS's primary disclosures.**

**(e) Disaster-response operations, including Tibet — and the key gap.** CCS reports substantial 应急通信保障 activity. FY2024 AR (Chairman's Report, PDF p.20) **[READ]**:

> 投身搶險救災保通信工作，在初春局部地區寒潮低溫極端天氣、南方多地特大暴雨洪澇災害、颱風「摩羯」、「貝碧嘉」、**新疆烏什縣7.1級地震、西藏定日縣6.8級地震**等重大災害中，第一時間奔赴災區，全力開展救災**應急通信**保障，**全年共投入人力約15萬人次**，守護通信「生命線」。

FY2025 AR aggregate (ESG, PDF p.156) **[READ]**:

> 二零二五年，本集團累計投入人力**28,000餘人次**、車輛**12,000餘輛次**，修復通信設施超過**28,000餘處**，參與救災工作時間**128,000餘小時**……

FY2025 AR (PDF p.156) documents landslide/debris-flow specific response in **雲南怒江州貢山縣、福貢縣** (崩塌、泥石流, 通信光纜多處中斷), **貴州黔南州三都縣** (山體滑坡 → 全縣通信大面積癱瘓), **重慶巴南、南川等5個區縣** (5 districts/counties' tower base stations and equipment rooms lost power), and (PDF p.157) **四川宜賓市筠連縣** (山體滑坡), **甘肅蘭州榆中縣** (山洪). The H1 2025 interim report (PDF p.10) also mentions **西藏定日縣6.8級地震** and **本集團承建西藏拉薩南北山綠化工程智慧管護系統項目，守護雪域高原生態環境**.

> **⚠ Critical distinction, stated plainly.** Everything in (e) is **POST-disaster emergency response and communications repair**: restoring severed cables, restarting powerless base stations, fixing 動環離線 faults. It is **not pre-disaster geohazard monitoring**. CCS's annual reports **do not present any geological-hazard monitoring network, monitoring platform, or monitoring-communication product.** The word 地質災害 returns **0 hits** across the FY2024/FY2025 annual and interim reports; the actual wording used is 山體滑坡 / 泥石流 / 崩塌 / 暴雨 / 洪澇 / 颱風 / 地震.

**(f) CCS does not cite the 14-ministry policy.** `十四部門`, `极端場景應急通信`, `工信部联信管`, `256号` → **0 hits across all four reports**. The only near-verbatim policy-adjacent phrase found is in the **H1 2025 interim report** (PDF p.8), and it differs: 「……**提升防災減災救災和極端條件應急指揮通信能力**」 — 極端條件應急指揮通信 (emergency **command** communications under extreme conditions), not the policy's 極端場景應急通信. It is the only occurrence of 極端條件 in any of the four reports.

### 6.3b A direct Tibet geohazard role — at the design layer only

This is the single most important item for the partner's positioning, and it materially qualifies the negative finding in 6.3(e).

**中通服咨询设计研究院有限公司 (CCS Consulting & Design Institute) won 「西藏自治区地质灾害风险预警系统建设项目初步设计项目」** — the preliminary design for the Tibet Autonomous Region geohazard risk early-warning system **[READ]**:

| Field | Value |
|---|---|
| Purchaser | **西藏自治区自然资源厅厅机关** (Tibet Autonomous Region Department of Natural Resources) |
| Winning supplier | **中通服咨询设计研究院有限公司** (address 南京市楠溪江东街58号) |
| Price | 「中标价（%）：4.00」 — this is a **下浮率 (discount-rate) bid of 4.00 %**, so **no absolute contract value exists to quote** |
| Procurement method | **单一来源采购** (single-source) |
| Announcement date | **2024-04-18** |

Service scope, verbatim: 「组织开展**地质灾害风险预警系统建设方案设计**，对建立**省－市－县地质灾害风险预警系统**，建设**一套数据中心**，**一套地质灾害风险预警业务系统**，**集成气象数据**，相关**硬件资源、野外调查装备**等配备，实现数据统一管理和数据服务进行详细的方案设计。」

Sources: <http://biaotongtong.com/detail_1602286795_2024-04-18>; <https://xizang.jianyu360.cn/jybx/20240419_24041852743126.html>; <https://xizang.jianyu360.cn/jybx/20240419_24041852752298.html> (the more complete notice, confirming supplier address, 下浮率 pricing and 单一来源 method).

**What this establishes, precisely:** CCS's design institute authored the **preliminary design for a province–city–county three-tier geohazard early-warning system for Tibet's natural-resources department**, including a data centre, a business system and meteorological-data integration. That is a **direct, documented geohazard-monitoring role in exactly the target region** — at the **design/consultancy layer only**, with **no evidence of build or operate phases** and **no evidence of the communication layer being its scope**.

A **合同公示 (contract publication)** that would carry the actual value exists at <http://jianzhuzi.com/jianzhuzi/neirong_rn_1949063.html> but **could not be opened** (326 bytes). This is the top follow-up item for this section.

**Who actually holds the Tibetan monitoring sites.** The monitoring infrastructure evidenced in Tibet belongs to **中国移动西藏公司 (林芝, 536 点位)** and **中国铁塔 (可可西里)** — **not** to CCS. This is consistent with 6.3(e) and is important context: the operator holds the sites, while CCS (if involved) designs the platform around them.

### 6.3c CCS holds real Tibet off-grid power work — the strongest corroboration of the partner's premise

**中国移动通信集团西藏公司 2025–2026 年桅杆、一体化机仓平台、太阳能平台及太阳能系统施工框架集中采购** **[READ]**:

- Budget: **¥78,412,900 excluding tax (¥86,894,700 including tax)**; six winners
- **Share 1: 中国通信建设第二工程局有限公司 — 21.79 % — 日喀则-西九县** (定结、**定日**、聂拉木、吉隆、仲巴、萨嘎、昂仁、拉孜、萨迦)
- **Share 6: 中国通信建设北京工程局有限公司 — 12.66 % — 阿里**
- CCS-group bureaus also hold the reserve positions
- Scope explicitly includes 「**太阳能平台及太阳能系统施工**」 — solar mounting platforms and **solar power system construction**

Source: <https://www.yfbzb.com/winbid/detail/20241126_465941577.html> (note: a sibling agent initially recorded this as `yfyzb.com`; the correct host is **`yfbzb.com`**, re-verified directly).

**Why this matters:** CCS-group construction bureaus hold the **largest share of solar-power construction for China Mobile's base stations in 日喀则's western nine counties (including 定日) and in 阿里** — among the highest and most remote prefectures in Tibet. **This is direct evidence that the partner's organisation already designs, supplies and installs off-grid solar power systems in the exact terrain of interest**, and it is the strongest possible basis for the partner's claim that "most sites lack adequate power supply."

**A third independent strand: CCS claims power-system construction and satellite-network planning as core operator-facing scope.** From the corporate site's 国内电信运营商客户 page **[READ, verified directly]** <https://www.chinaccs.com.hk/sc/business/telecom_operator.php>:

> 「公司拥有丰富的通信建设经验，为客户提供包括**固定网络、移动网络、卫星网络**在内的网络规划……提供覆盖固定及移动通信网络建设各个环节的一体化服务，包括**勘察、设计、工程施工、工程监理**等全过程服务……同时，公司具有雄厚的实力为通信运营商提供土木工程建设及其他配套设施建设服务，包括设备机房建设、土木工程装修、**防雷击设备、环境及电力系统建设**……」

This is significant for three reasons: (i) **卫星网络 appears here and essentially nowhere else in CCS's corporate disclosures** — it establishes satellite backhaul planning as an advertised scope; (ii) **防雷击设备 (lightning-protection equipment) and 环境及电力系统建设 (environmental and power-system construction)** are claimed as core site-support scope, which is notable given that lightning-induced surge is a documented failure mode for mountain stations (Section 5.6); and (iii) it independently corroborates the 浙江省邮电工程建设 **通信变配电** capability and the solar-framework awards above. **Three independent strands now point at power/site infrastructure as a real, advertised CCS line of business — while none point at low-power radio.**

### 6.3d The failure mechanism corroborated: it is POWER, not radio

Two independently sourced items point the same way, and this is a genuinely useful refinement of the problem statement **[READ]**:

- **March 2025 禾木 (Xinjiang) blizzard:** **17 base stations alarmed on damaged power lines**; CCS's 中国通服怡利公司 operated at **−30 °C for 30 hours**, restoring 十余个基站, and ran **high-frequency snow-clearing because solar panels buried in snow stop generating**. Source: <https://m.thepaper.cn/newsDetail_forward_30483598>
- **Operator-scale context:** **>48 % of China Mobile Tibet's base stations are new-energy (solar) powered**. Source: <https://www.news.cn/info/20260909/7e67053d8b1a46c39897269e4203959c/c.html>
- CCS's own FY2025 annual report describes the July Chongqing event as 多处铁塔基站、通信机房**停电** (power loss), not as a radio failure.

**Synthesis:** across the documented events, the initiating failure is the **power path** — snow-buried panels, damaged lines, grid loss — with communications loss following. This aligns with the physics in Section 5.4 (**−20 °C halves LiFePO4 capacity and blocks charging below +5 °C**) far better than with radio propagation. Snow *burial of the panel* is a distinct and under-appreciated failure mode from snow *on the antenna*, and it affects generation rather than propagation.

### 6.3e Tibet earthquake response detail (January 2025 定日 M6.8) — post-disaster, for completeness

**Four CCS units responded, not one, and the equipment list is the analytically interesting part.** The response to the 2025-01-07 定日 M6.8 earthquake **[READ, verified directly]** (<https://www.thepaper.cn/newsDetail_forward_29913860>):

> 「中国通服四川公司迅速启动应急响应机制……中国通服成都分公司火速集结日喀则抢险队伍奔赴灾区，抢险队伍不顾当晚大雪封路、路面受灾严重，连夜驱车8个多小时抵达定日县……**7日当晚11点抢险队伍抢通了灾区第一个基站**。」
> 「中国通服**四川新华物业公司**第一时间响应上级单位指挥，组建**4人抢险队伍，驾驶1辆30KW电源车、1辆240KW电源车，并携带2台卫星电话**，于7日19点30分奔赴定日灾区；**中国通建一局**……迅速集结**应急通信保障车、油机、移动电源**及防寒救灾生命保障物资……**中国通建二局第七分公司日喀则项目部**积极协调人员、车辆、材料前往灾区。」

Site conditions from a second source **[READ, verified directly]** (<https://m.toutiao.com/article/7457814132855685647/>, 「中国通建全力奔赴抗震一线保障通信」):

> 「**海拔4000多米的长所乡**等乡镇，最低气温达**-16℃**。**中国通建二局第七分公司日喀则项目部**第一时间对接地方需求，成立抗震救灾突击队……」

By 10 January the response had covered **42 base stations, 11 emergency leased lines and 13 km of optical cable across 定日县 9乡2镇**, at −16 °C.

**Why the hardware list matters more than it looks.** CCS's emergency answer in Tibet, stated as *equipment*, is **1 × 30 kW and 1 × 240 kW mobile power vehicles plus 2 satellite phones**, deployed into a 4,000 m+ disaster zone alongside 油机 (diesel gensets) and 移动电源. That is **diesel generation for power + satellite for backhaul** — precisely the two capabilities the partner's problem statement implies are *absent* at permanent monitoring sites. The correct reading is not "CCS solves this" but: **CCS possesses both capabilities, and treats them as deployable emergency-response assets rather than fixed-site solutions.** A 240 kW diesel genset is not a permanent-station power architecture; it is the answer to a two-week outage, not to a twenty-year unattended node. That distinction should be kept explicit in the technical report.

**A second, understated finding: CCS-group permanent presence in Tibet is attested four independent ways, and Tibet work is not a fly-in operation.**

| # | Unit | Type | Evidence |
|---|---|---|---|
| 1 | **中通服建设有限公司西藏分公司** — registered **2020-08-04**, 负责人 邓玮; scope includes 通信系统工程服务 / 通信设施安装工程服务 / 通信线路和设备的安装 / 信息系统集成 / 通信网络的维修、维护、优化 | **Registered branch** | **[READ]** job-platform corporate record <https://www.zhaopin.com/companydetail/9154AJUXATLXMOOI9.htm>. ⚠ **Caveat:** the authoritative registry (天眼查) was **geo-blocked** (「当前所在地区暂不支持访问」), so this rests on a job-platform record, not the registry itself |
| 2 | **中国通信建设第一工程局有限公司西藏分公司** | **Registered branch** (and an active hirer — e.g. 「达孜通信工程项目经理 中国通建一局（西藏）」) | **[READ]** <https://www.liepin.com/company/gs106412552/>, <https://www.zhaopin.com/companydetail/915406XUAVDGH8PGYY.htm>, <http://www.xzfxrc.com/job3172693033.shtml> |
| 3 | **中国通建二局第七分公司日喀则项目部** | **Standing resident project department** | **[READ]** Section 6.3e sources |
| 4 | **四川公司西藏业务部** (led by 叶盛 under 工程西藏党支部) | **Internal business department** of the *Sichuan* provincial entity | **[READ]** <https://www.toutiao.com/article/7458541397482750464/> |

**This revises the earlier and too-narrow statement that no Tibet presence could be verified.** The precise position is: **there is no Tibet provincial *company* in the Note-47 disclosure or on the group ownership chart** — but there is documented **standing operational presence**, and CCS runs Tibet largely **through non-Tibet-incorporated units** (note that strand 4 makes Tibet operations a business department of the *Sichuan* entity). O&M feasibility claims should rest on strands 1–4, **not** on an asserted Tibet provincial company.

**Two further items that shape the commercial picture:**

- **CCS is an established Lhasa government supplier, at least for IT operations** **[READ]**: 中通服建设有限公司 won 「拉萨市应急管理局信息化运维服务项目（三次）」 (2026-06-09, 评审总得分 83.68732 — <https://xizang.jianyu360.cn/jybx/20260609_26060860324741.html>) and 「拉萨市一体化政务服务平台和拉萨三级政务服务大厅运维项目」 (采购人 拉萨市行政审批和便民服务局, 评审总得分 88.83182). **Amounts are masked in both sources.** These are **IT operations/maintenance contracts, not network-coverage builds** — they prove a CCS entity is an *established Lhasa government supplier*, nothing more.
- **Even CCS's own supply-chain footprint in Tibet is served from other provinces** **[READ]**: the `*.chinaccsscm.cn` bidding-platform nav bar lists nodes for 总部/上海/中捷/福建/江西/贵州/湖北/四川/新疆/浙江/湖南/江苏 — **there is no 西藏 node** (<https://zb.chinaccsscm.cn/zbgg/292664.jhtml>). A 「中通服供应链股份有限公司西藏分公司」 was seen only in a snippet with the province masked and **no corporate record was found — treat a CCS supply-chain branch in Tibet as unestablished.**

> **⚠ Both new unit names are media labels, not verified legal persons.** 「中国通服四川新华物业公司」 is not a registered entity name (it is likely the property arm of 四川省通信产业服务有限公司 — compare 中通服智慧物业发展有限公司 in Note 47), and neither unit appears in Note 47. They are reported here **only as the sources' labels**, which is why this section is anchored on the parent entities that *are* documented.

### 6.3f Naming traps — four live mis-attribution hazards

Anyone searching for CCS's Tibet presence will hit these, and both produce false claims **[READ]**:

1. **⚠ 西藏通信服务有限责任公司 is a 中国移动 entity, NOT a CHINACCS one.** Get the legal name exactly right: it is **西藏通信服务有限责任公司** (not 西藏自治区通信服务有限公司), **系中国移动通信集团有限公司全资控股的国有独资企业**, founded **2000-10-11**, HQ 拉萨市金珠西路84号, **registered capital only RMB 1,000万**, **2 insured employees (2024)**, 法定代表人 李重严, formerly 西藏通信服务公司 (restructured and renamed 2018-10). Source: <https://baike.baidu.com/item/西藏通信服务有限责任公司>. The danger is sharper than a simple name collision: the entity is **tiny**, yet its name closely imitates the *genuine* CHINACCS pattern 「XX省通信服务有限公司」 (cf. 江苏/陕西/青海), so a "通信服务 + 西藏" search surfaces it as though it were a CCS provincial company. It is not — Tibet is absent from both Note 47 and the ownership chart.
2. **⚠ 中电信应急通信有限公司** (established 2025-01-21, Tianjin Wuqing) is a professional subsidiary of **中国电信集团 — *not* of 中通服**, despite the overlapping "中 / 电信 / 通信" wording. <https://m.nbd.com.cn/articles/2025-01-21/3731163.html>
3. **"中通服建设有限公司 原中国通信建设" is wrong.** 中通服建设有限公司's former legal name was **广东省电信工程有限公司** (renamed 2018-01-22). **中国通信建设集团有限公司** — the Note-47 subsidiary in the table above — is a *different* company, and **中国交通建设 (China Communications Construction)** is unrelated to both.
4. **Provincial entities are separate companies, not 分公司.** 「分公司」 appears only *below* the provincial tier (e.g. 四川省通信产业服务有限公司雅安市分公司, 中通服建设有限公司西藏分公司). Naming is also non-uniform: only ~14 of ~20 provincial entities follow the 「XX省通信产业服务有限公司」 pattern.

**Two items explicitly fenced as unverified, and they must stay that way:** 中时讯通信建设有限公司's CCS affiliation is **NOT** verified (do not assert it); and the masked 林芝 avalanche 包3 supplier is only an **address match** to 中通服咨询设计研究院 — a lead, not a fact.

### 6.4 What the 中通服 angle amounts to

**Verified:** CCS is a RMB ~150 bn-revenue state telecom-engineering group with (i) a large national **network-maintenance** business (RMB 19.1 bn) plus RMB 61.0 bn of **construction**, (ii) **provincial subsidiaries in every province relevant here including Sichuan, Yunnan, Guizhou, Gansu, Qinghai, Xinjiang and Chongqing**, (iii) demonstrated **off-grid solar+storage communications infrastructure at 113 sites in the Taklamakan**, (iv) **the largest share of solar-power construction for China Mobile's base stations in 日喀则's western nine counties (incl. 定日) and 阿里** — the exact terrain of interest, (v) a **direct-to-satellite product (星極通)** and a fast-growing satellite-internet business, (vi) a **应急安全 product line that explicitly includes 监测预警 and the 自然资源 sector**, (vii) a **documented design-layer geohazard role in Tibet** — 中通服咨询设计研究院 won the preliminary design for 西藏自治区地质灾害风险预警系统建设项目 for the Tibet natural-resources department, and (viii) deep, repeatedly demonstrated **post-disaster communications-restoration capability in exactly the landslide/debris-flow provinces of interest**, including Tibet at −16 °C.

**Corrected from an earlier draft of this report:** it is **no longer accurate** to say no CCS geohazard-monitoring involvement exists. CCS's design institute **authored the preliminary design for Tibet's province–city–county geohazard early-warning system** (Section 6.3b). The correct statement is narrower and more interesting: CCS has a **design/consultancy** role in Tibetan geohazard early warning, with **no evidence of a build or operate role**, and **no evidence that the communication layer was within its design scope**.

**Still genuinely absent:** any documented CCS **geohazard monitoring communication product or deployed monitoring network**; any **Tibet-region legal subsidiary** (Section 6.3f trap 1 — do not confuse it with the China Mobile entity); any **published CCS response to the 14-ministry policy** (0 hits across four reports, both languages; FY2024 predates it and FY2025 never cites it); and any **quantified reliability data** from CCS operations.

**The LPWAN gap, stated precisely.** The FY2025 annual report returns **exactly 0 hits** for `NB-IoT`, `低功耗`, `電信普遍服務` and `無人機`, while `物聯網` returns **11 (FY2025) / 17 (FY2024)** occurrences that are all generic technology framing (IoT as a capability adjective alongside AI, big data, blockchain) rather than radio or coverage work. Since the partner's problem is fundamentally an **LPWAN-coverage** problem, this is not a vague negative but a precise one: **CCS publishes nothing on the low-power wide-area axis.** Two caveats the subagent raised and I am preserving: this negative is **scoped to the sources reachable** (微信公众号, provincial subsidiary sites and 招标 databases were not systematically searched), and it is a **search-based negative, not proof**. Those channels were independently searched twice with nothing found, so the negative is stronger than either pass alone — but it remains a negative.

**Two items must remain unasserted:** 中时讯通信建设有限公司's CCS affiliation is unverified, and the masked 林芝 avalanche 包3 supplier is only an address match to 中通服咨询设计研究院.

> **Interpretation for the project.** The partner's problem statement is now **better supported than when this report began**, and in a specific direction: the documented failure mechanism is the **power path**, not radio. CCS installs and maintains off-grid solar for base stations across 阿里 and 日喀则 at scale, and its design institute has already specified a Tibetan geohazard early-warning system — but the organisation has **no published low-power/LPWAN capability and no published geohazard-monitoring communication product**. Meanwhile the Tibetan monitoring sites themselves are held by **中国移动西藏公司 (林芝, 536 点位)** and **中国铁塔**, not by CCS. The natural reading is that the partner is a **network-engineering, power and O&M house seeking the communication layer of the geohazard-monitoring value chain** — a layer it does not currently publish on — and that the 十五五 build programme (7,996 new landslide stations + 1,757 debris-flow stations + 7,213 upgrades + 64,962 under O&M) is the addressable market. **The technical gap and the commercial gap point at the same thing.**

> **Unopened leads worth routing around.** `cnii.com.cn` (人民邮电报) geo-blocks this IP with `403 reason:GeoBL`, making four squarely on-topic articles unreadable — including 「中国通建在5000米高原架起"信息天路"」. **These are the highest-value unopened leads for this section** and need a China-routed proxy or a library database. Also blocked: 天眼查 (regional), `ccgp-xizang.gov.cn` and `ggzy.guizhou.gov.cn` (empty responses), and WeChat (CAPTCHA). The 合同公示 for the Tibet geohazard design contract (Section 6.3b) is the top single follow-up.

---

## 7. Open datasets

Full table with licence and verification depth: `evidence/sub-datasets.md` (44 datasets, every DOI read from repository responses, never constructed). Legend: **V-LP** = landing page opened; **V-API** = repository metadata API; **V-S** = snippet only.

### 7.1 The most useful open items

| Dataset | Repository / DOI | Contents | Time span / interval | Licence & access |
|---|---|---|---|---|
| **GNSS ground monitoring, Hongyanzi landslide, China** | Zenodo `10.5281/zenodo.13254357` | GNSS 3-D displacement from **5 stations**, projected onto InSAR LOS; 1-D displacement time series; 6.8 kB `LOS-GNSS.txt` | 2021-11-11 – 2022-06-04 | **CC-BY-4.0, open anonymous download** |
| **Qili landslide daily rainfall, groundwater depth, GNSS displacement** | Zenodo `10.5281/zenodo.21916040` | **720 consecutive daily records**: date, daily rainfall, groundwater depth, cumulative surface displacement; `data.xlsx` 33.4 kB + README | 2016-01-12 – 2017-12-31; **daily** | **CC-BY-4.0, open** |
| **Rainfall thresholds, Three Gorges reservoir landslides** | Zenodo `10.5281/zenodo.11311851` | Susceptibility layers + rainfall thresholds (DEM, distance-to-river, structural density, hazard polygons); `DEM.tif` 6.5 MB + many `.tif` | not stated | **CC-BY-4.0, open** |
| **Goulinping gully debris-flow seismic (Yang, Chen, Meng — Lanzhou University)** | Zenodo `10.5281/zenodo.10773103` | **Seismic data of 11 flow events in Goulinping gully, 2022** (UTC+8) plus three field-experiment datasets; `.xlsx` 77.1 MB + `.rar` 51.3 MB | 2022, event-based | **CC-BY-4.0, open with downloadable files** — the best openly-downloadable Chinese debris-flow sensor dataset found |
| **LoRa RSSI+SNR, avalanche search & rescue, Italian Dolomites at 1,870 m** | Zenodo `10.5281/zenodo.13932869` (v2); concept `10.5281/zenodo.12750580` | **LoRa RSSI + SNR with ground-truth positions.** Cross test (buried TX at varying depth, 4 receivers at 10 distances × 4 orientations, 0.6–50 m), max-distance test, drone flyover (121-point grid over 100 m²); includes snow profiles (AINEVA Model 4) | **March (dry snow >1 m) and April 2024 (wet snow ~55 cm)** | **CC-BY-4.0, open** — **the single best open alpine LoRa link-trace dataset found, and directly relevant to snow/wet-snow effects on a sub-GHz mountain link** |
| **LoRa signal quality + GPS time series, Sálvora Archipelago, Galicia** | Zenodo `10.5281/zenodo.13835721` | 3 LoRa gateways: device ID, **RSSI and SNR per gateway**, spreading factor, timestamp, GPS lat/lon/alt; gateway altitudes 73/5/31 m | — | **CC-BY-4.0, open** |
| **CRAWDAD `isti/rural`** | IEEE DataPort `10.15783/C7G01C` | **Frame-level link traces**: per-frame receive time, frame length (500/1000/1500 B), sequence number, quality level, **signal level (×0.6 → dB)**, noise level, received/lost status, **number of corrupted bits on CRC failure**; ARQ/RTS-CTS/fragmentation disabled, sampled at 200 frames/s, 200,000 frames per measurement | Navacchio (Pisa), April 2006; rural unobstructed LOS | **Open access** — the only true per-frame loss + CRC-corruption trace found |
| **Illgraben debris-flow observatory, Switzerland** | WSL / **EnviDat** CKAN API | Key record **`10.16904/envidat.489`** — volumetric water content (soil moisture) at **0.25 / 0.45 m** (ECH2O EC-5) and **0.65 / 0.85 m** (TEROS 12), plus water level, temperature, electrical conductivity and air reference pressure at 0.80 m; **165,780 points at 5-minute sampling**, `SM_Illgraben_2022.csv` 1.62 MB. Also event characterisation (`envidat.630` 2023, `envidat.378` 2019–2022), volumes 2000–2017 (`envidat.173`), and a 2024 event set with **cumulative rainfall + radar flow height** (`envidat.448`) | May–Oct 2022 season etc. | ⚠ **Mixed licences:** `envidat.448` is CC-BY-4.0, `envidat.630` CC-BY-SA, but **`envidat.489`, `.378`, `.173` carry the WSL Data Policy, which is not an open licence** |
| **Jiangjia Ravine 蒋家沟 debris flow, Dongchuan, Yunnan** | NCDC 国家冰川冻土沙漠科学数据中心 — a complete six-record 2025 campaign, one DOI each: `10.12072/ncdc.ddfors.db7459.2026` (seismic, **100 ms** resolution, **505.5 MiB**), `.db7458` (kinematic, **1 s**, 4.8 MiB), `.db7460` (grain size), `.db7461` (rheology), `.db7465` (gully cross-sections, daily), `.db7468` (video) | three events on 19/24/29 Jul 2025 | ⚠ **"Login to Access"** — registered account required; **no CC licence** (NCDC agreement) |
| **Three Gorges landslide series** (Baishuihe 白水河 / Bazimen 八字门 / Shuping 树坪 / Xintan 新滩 / Lianziya 链子崖) | **NCDC** `ncdc.ac.cn`, records organised **per landslide per year**. Verified DOIs: `10.12072/ncdc.Sanxia.db0004.2020` (Bazimen 2007–2012: GPS surface displacement + rainfall + Yangtze water level), `10.12072/ncdc.sanxia.db7444.2026` (Bazimen 2019), `10.12072/ncdc.sanxia.db7442.2026` (Shuping 2019), `10.12072/ncdc.Sanxia.db0019.2020` (2018 annual-report compilation, 5 landslides + 1 rock mass, `.doc`, **52.4 MiB**) | 2007–2019 | ⚠ **"Apply to Access" / "Login to Access"**; **no blanket CC licence**; NCDC licence agreement requires citation + acknowledgement of "National Cryosphere Desert Data Center" |
| **Hochvogel, Allgäu Alps, 2,592 m** — *note: this is the monitoring dataset, distinct from the reliability study in Section 4.2 #9* | TUM / EGU | Multi-year high-alpine LoRa monitoring: **10–12 geotechnical sensors** (crack meters, laser distance meters, inclinometers, rain gauge), **>5 years from Oct 2019**, transmitting every 10 min | 2019–ongoing | See the reliability study, Section 4.2 #9 — this is the only source found anywhere publishing **measured multi-year** high-alpine LoRa reliability |
| **Enhanced Natural Terrain Landslide Inventory (ENTLI), Hong Kong** | DATA.GOV.HK / CEDD GEO Open Data (dataset id `cedd_rcd_1636520697377_96152`) | Catalogue of historical natural-terrain landslides + data dictionary PDF; geospatial download via CSDI geoportal, API available | — | Open government data under **CEDD GEO Open Data Terms and Conditions** — **not a CC licence** |

Additional CC-BY-4.0 open landslide records verified by metadata API: Eggerberg/Gradenbach (Austria) `10.5281/zenodo.21033260`; Vögelsberg (Tyrol) `10.5281/zenodo.6337833`; Achoma (Peru) `10.5281/zenodo.17753976`; Pietrapertosa (Italy) `10.5281/zenodo.19099868`. Reissenschuh (Austria) `10.5281/zenodo.6519780` is **restricted with no licence stated**. LoED LoRaWAN-at-the-Edge `10.5281/zenodo.4121430` is **CC-BY-4.0 and open (503.6 MB)** but is an **urban** (London) deployment, not mountain.

### 7.2 DOI verification note (a trap worth recording)

`https://doi.org/10.12072/...` (the NCDC prefix) initially returned **HTTP 000**, which looks like failure but is not: doi.org returns a **302 to the exact NCDC UUID page**, and two such DOIs were cross-checked and matched. The `10.12072` prefix is served by a **non-DataCite registration agency**, which is why DataCite lookups 404 on it. The dead hop is `www.ncdc.ac.cn` being unreachable from this environment.

### 7.3 Explicit negative results for datasets

- **No open dataset was found that logs link quality (RSSI/LQI/PDR) or outage events as a by-product of a Chinese mountain geohazard monitoring network.** The CRAWDAD and LoRa datasets are all non-China deployments.
- **No standalone, openly downloadable Baishuihe / Bazimen / Tanjiaba ML dataset** — the widely-reused "Baishuihe/Bazimen/Tanjiaba displacement" tables circulating in ML papers are **not** published as a standalone open dataset; they are extracted from the access-gated NCDC per-year series or supplied as paper supplements. Zenodo name searches for all three returned zero landslide matches.
- **No tilt-meter or crack-meter time series surfaced for any Chinese landslide**, and **no NB-IoT field dataset** was found anywhere.
- **No geohazard (landslide/debris-flow) sensor time series was found for Gansu, Guizhou, Chongqing or Tibet.**
- **Repository coverage gaps, each for a specific recorded reason:** **ScienceDB (科学数据银行)** not searchable (all candidate API endpoints return 404); **PANGAEA** not searchable (its Elasticsearch `title` field is stored obfuscated, so field-scoped queries return 0 hits); **Dryad** blocked by an Anubis bot-check interstitial; **OpenML** has no landslide dataset; **UCI** direct API/ID lookup failed (reached only via a Kaggle mirror).
- **Not one 国家青藏高原科学数据中心 (TPDC, `data.tpdc.ac.cn`) dataset could be verified.** Login-gated search; dataset pages render as a JavaScript shell returning "No data temporarily" with "Sharing way: Apply for access"; and its DOI prefix **`10.11888` is not registered with DataCite** (lookup returns 404), so TPDC DOIs cannot be validated through the DataCite API and must be confirmed manually inside the portal. **If Tibet/QTP coverage matters, this needs an authenticated session from a network that can reach `data.tpdc.ac.cn`.**

- **No dataset providing in-situ debris-flow 泥位 (stage/flow-depth) time series in China** was found openly. The nearest open flow-height series is the Illgraben 2024 event set (`10.16904/envidat.448`, radar-derived flow height at station CD28) — which is **Swiss, not Chinese**.

> **Important partial correction to the "no Tibet data" finding.** Tibet/QTP coverage does exist at **NCDC**, though not for geohazards: **`10.12072/ncdc.permafrost.db7703.2026`** — active-layer moisture survey samples for the Qinghai–Tibet Plateau permafrost region, **2009–2024** — and **`10.12072/ncdc.nieer.db6676.2024`** — mean annual ground temperature (MAGT) and permafrost thermal stability over the Tibetan Plateau, 2005–2015. **Both are NCDC "Open Access"**, unlike the Three Gorges and 蒋家沟 series. These are permafrost/ground-thermal datasets, **not** landslide or debris-flow monitoring, but they do provide openly usable Tibetan ground-condition context.

---

## 8. Synthesis — what this means for the project, and what is still unverified

### 8.1 The problem is real and the constraint is precise

1. **The build programme is large and funded.** 十五五 adds **7,996** landslide/rockfall stations, **1,757** debris-flow stations, upgrades **7,213**, and runs **64,962** existing stations as O&M — with **Tibet named in three of the 21 key prevention zones**, including a new **雅鲁藏布江下游水电工程** zone ([自然资办函〔2026〕1198号](https://www.gov.cn/zhengce/zhengceku/202608/content_7078245.htm)).

2. **The policy mandate for the *communication* half of this problem is the 14-ministry opinion, not the 十五五 plan.** 工信部联信管〔2024〕256号 names **断路、断电、断网**, requires **抗毁韧性** and coverage in **灾害多发易发地区**, requires equipment **适应严寒、密林等极端条件**, and places **北斗短报文 and 天通 explicitly in the grassroots-fallback tier**. The 十五五 plan, read in full, mandates **no** power, latency or continuity figure — so the project should cite the MIIT document for the communication requirement and the MNR plan for the monitoring network.

3. **The physical mechanism is quantified.** The partner's "lack of power" has a specific, published cause for Tibet: at **−20 °C LiFePO4 delivers ~50 % of rated capacity and cannot be charged below +5 °C**; NMC loses ~89 % at −25 °C; lead-acid loses ~35 % at −15 °C. The partner's "signals frequently interrupted" is **not** primarily rain fade at sub-1 GHz (negligible: ~0.0011 dB/km at 1 GHz, 50 mm/h) — it is **terrain diffraction** (6–22 dB per obstruction), **wet foliage and seasonal canopy**, **snow/ice on the antenna**, and **lightning-induced surge** (documented destroying both primary and backup loggers from nearby cloud flashes).

4. **The design space is bounded by published vendor claims.** Sub-1 W sensor nodes pair with **tens of watts of PV and tens of Ah of battery for ~15–30 rain-days**; ~90 rain-days needs ~100 Ah or adaptive duty-cycling; adding imaging costs 60–120 W and drops autonomy to 7–15 days. **Anti-icing alone costs 26–100 W** — more than the entire sensor node.

5. **BeiDou short message is the established no-coverage backhaul**, with the key architectural lesson being **edge computing before transmission** (raw GNSS is tens of kB/s; the transmitted payload is reduced to a few hundred bytes), **not** raw data tunnelling. Its binding constraints are **message length** (14,000 bits regional / ~131 characters on the current commercial standard product ; 560 bits global) and **send frequency** (120 s minimum on the standard product), plus a **~3 W transmit power** — high relative to a sub-1 W sensor, so duty-cycling is mandatory.

### 8.2 The central opportunity: the reliability data does not exist

**This is the strongest finding in the report for a research proposal.** Across every reachable source, there is:

- **no measured 在线率, 数据到报率, 数据完整率, 掉线次数, 供电故障率, 设备离线率, 节点损失统计, link availability or outage duration for any Chinese landslide or debris-flow monitoring network**, including the one paper written specifically about Tibet's 普适型 network and its problems;
- **only requirements** (Guangdong acceptance **≥70 %**, plus the **≤5 min** field-acquisition-to-transmission latency and **≤3 %** data-loss ceilings; 昆明 **≥95 %/≥90 %**; 河南 **≥95 %**) and **qualitative complaints** (误报率偏高, 数据质量不可靠, 供电不稳, 在线率偏低);
- and the **only measured link-quality numbers** being a **2.3288 % average packet loss** on a LoRa+北斗RDSS network (measured in a Sichuan simulation site, not Tibet), a **98.46 %** transmission success rate for a single BeiDou-3 RSMC scheme, and the **Hochvogel** multi-year dataset (non-China) showing **97.3–100 % daily but 56–65 % hourly for snow-buried sensors**.

A project that instruments and **publishes** a real Tibetan monitoring network's link availability, data-return rate, power-failure and node-loss statistics — **with the temporal aggregation window stated, and at a resolution fine enough to catch the rain-time failures that matter** — would be filling a genuine gap in the literature rather than adding to a crowded field. The Guangzhou-style **≥70 % versus ≥95 %** spread between the acceptance standard and tender aspirations, combined with the Hochvogel resolution effect, shows the operational truth is not merely unmeasured but systematically flattered by coarse reporting windows.

### 8.3 Explicitly NOT verified

| Item | Status |
|---|---|
| Numeric content of **DZ/T 0450-2023** (communication requirements: intervals, heartbeat, backfill, permitted loss) | paywalled — **scope only** read |
| **DZ/T 0460-2023 Appendix B** (instrument technical parameters) | paywalled |
| Tibet **provincial** 十五五 monitoring targets | not found; the national plan gives national figures only |
| **TPDC** (国家青藏高原科学数据中心) permafrost/Tibet datasets | **not reachable** from this environment |
| **CNKI** full texts (incl. the Tibet 拉萨/林芝 paper's body, where a numeric 误报率 may live) | certificate errors on all attempts |
| Lanzhou University Gansu thesis on Gansu monitoring-system evaluation | TLS failure on `ir.lzu.edu.cn` — **highest-value unread source for Gansu** |
| Whether **628 bits** or **~131 characters** is the applicable BeiDou user message limit | sources conflict; must be resolved with the operator |
| Any CCS **geohazard-monitoring communication product**, deployed monitoring network, **build/operate** geohazard role, or **NB-IoT/LPWAN work** | **not found** (negative over reachable sources; the LPWAN result is exact-count: 0 hits for NB-IoT/低功耗/電信普遍服務 in FY2025) |
| A **Tibet provincial *company*** of CCS | **not found** in Note 47 or the group ownership chart — but **four strands of standing operational presence are documented** (§6.3e). Do **not** claim a Tibet provincial company exists; do **not** claim CCS has no Tibet presence |
| 「中通服供应链股份有限公司西藏分公司」 | **unestablished** — snippet only, province masked, no corporate record found |
| ~~Any CCS geohazard-monitoring involvement in Tibet~~ | **SUPERSEDED — this is now partly verified.** 中通服咨询设计研究院有限公司 won the preliminary design for 西藏自治区地质灾害风险预警系统建设项目 (Tibet natural-resources department, 2024-04-18, single-source, 下浮率 4.00 %). Design layer only. See §6.3b |
| The 合同公示 (contract publication) giving the **actual value** of the Tibet geohazard design contract | exists but **could not be opened** (326 bytes) — top follow-up |
| Four on-topic 人民邮电报 articles at `cnii.com.cn`, incl. 「中国通建在5000米高原架起"信息天路"」 | **geo-blocked** (`403 reason:GeoBL`) — highest-value unopened leads in §6 |
| BeiDou **per-message energy** in J or mAh; industrial RDSS **service tariffs** | **no published figures found** |
| Measured **LoRa/NB-IoT band rain attenuation**; wet-vs-dry foliage delta; sub-1 GHz snow/ice loss; **Tibet lightning density**; Chinese station **lightning damage rate**, **rodent damage rate**, **theft rate** | **no published figures found** |

---

### Appendix — primary sources read in full

**Policy** — 自然资办函〔2026〕1198号 + plan PDF (24 pp.); 工信部联信管〔2024〕256号 + gov.cn 解读.
**Standards** — DZ/T 0460-2023 (scope + structure); DZ/T 0450-2023 (title only, paywalled).
**Peer-reviewed** — 导航定位与授时 2023, 10(3):96-107; 科学技术与工程 2025, 25(2):640-648; 自动化与仪表 2011, 26(9):43-46; 西藏科技 2024(05) (abstract).
**Institutional** — 中国地质调查局 2026-07-07; 西藏自治区科学技术厅 2025-08-08.
**Corporate** — CCS FY2024/FY2025 annual reports, H1 2025/H1 2026 interim reports, results press release; vendor specifications (米度, 华测, 华西/杰芯, 千寻位置, 风途, 海康-类北斗监拍方案).
**Standards bodies** — ITU-R P.838-3, P.833-10, P.526-13, P.840-9, P.676-13; TRB SR185 185-049.
**Battery** — Victron Lithium Smart datasheet; Leng et al. 2017 JES; Chilwee GB12-28 datasheet.

*Working evidence files, including the full 44-row dataset table, the 382-line link-physics file with 18 documented gaps, and the 627-line CCS primary-source file, are in `docs/s2-scenario/evidence/`.*
