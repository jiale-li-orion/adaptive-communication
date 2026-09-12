# Open datasets: landslide & debris-flow monitoring, and mountain wireless telemetry

Survey compiled for a technical report. **Compiled by direct API/landing-page retrieval**, not by
search-snippet inference.

## Verification legend

| Code | Meaning |
|---|---|
| **V-LP** | Verified by opening the dataset **landing page** (rendered via r.jina.ai) and reading title/DOI/license there |
| **V-API** | Verified by retrieving the **repository's own metadata API** record (Zenodo `/api/records`, EnviDat CKAN `package_show`, Kaggle `/api/v1/datasets/view`, DataCite) |
| **V-S** | Seen only in a search result snippet — DOI/title NOT independently confirmed. Treat as a lead. |

All DOIs below are copied verbatim from the repository response, never constructed by hand.

**DOI resolution spot-check (performed last).** `https://doi.org/<DOI>` was resolved for a sample:
`10.16904/envidat.489`, `10.16904/envidat.448`, `10.15783/C7G01C`, `10.5281/zenodo.13254357` and
`10.5281/zenodo.10773103` all returned **HTTP 200**. The `10.12072` (NCDC) DOIs returned an
**HTTP 302 redirect to the exact `www.ncdc.ac.cn/portal/metadata/<uuid>` page recorded here** —
e.g. `10.12072/ncdc.ddfors.db7459.2026` → `…/5164622c-f19b-4517-a93d-501c52c5a132` (matching row
#25) and `10.12072/ncdc.Sanxia.db0004.2020` → `…/66fad1a6-0d1d-11e6-af40-5cc5d45ad3ae` (matching
row #1). This independently cross-validates the Chinese DOIs. The final hop to `www.ncdc.ac.cn`
itself times out from this environment, which is a network reachability issue and **not** a
broken DOI.

---

## Category 1 — Landslide displacement / rainfall / pore-pressure time series

### 1a. Three Gorges Reservoir landslides (China) — National Cryosphere Desert Data Center (NCDC, 国家冰川冻土沙漠科学数据中心), `ncdc.ac.cn`

This is the **primary open archive for the classic Three Gorges landslide monitoring series**
(Baishuihe 白水河 / Bazimen 八字门 / Shuping 树坪 / Xintan 新滩 / Lianziya 链子崖). Records are
organised **per landslide per year**, so the series is many DOIs rather than one. All are
**"Apply to Access"** or **"Login to Access"** — i.e. registration + a data-request step, *not*
anonymous download. There is **no blanket CC license**; use is governed by the NCDC license
agreement (citation + acknowledgement of "National Cryosphere Desert Data Center" required).

| # | Dataset title | Repository | DOI | Contents | Time span / interval | Location | Format / size | License / access | Ver. |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2007–2012 Deformation monitoring Data of Bazimen Landslide in Zigui County, Three Gorges Reservoir Area | NCDC | `10.12072/ncdc.Sanxia.db0004.2020` | GPS surface-displacement results, landslide rainfall, Yangtze river water level | 2007–2012; interval not stated | Zigui Co., Hubei (Three Gorges) | not stated | NCDC agreement; **Apply to Access** | **V-LP** |
| 2 | Monitoring data on deformation, rainfall and reservoir water level of Bazimen landslide … 2019 | NCDC | `10.12072/ncdc.sanxia.db7444.2026` | Basic landslide characteristics + GPS surface-displacement table + rainfall + reservoir level | 2019 | Zigui Co., Hubei | not stated | NCDC agreement; **Apply to Access** | **V-LP** |
| 3 | Monitoring data on deformation, rainfall, and reservoir water level of Shuping landslide … 2019 | NCDC | `10.12072/ncdc.sanxia.db7442.2026` | Same schema as above for Shuping landslide | 2019 | Zigui Co., Hubei | not stated | NCDC agreement; **Apply to Access** | **V-LP** |
| 4 | Annual report collection of professional monitoring on Baishuihe, Bazimen, Shuping, Xintan landslides and Lianziya dangerous rock mass … (2018) | NCDC | `10.12072/ncdc.Sanxia.db0019.2020` | Compilation of professional monitoring annual reports, 5 landslides + 1 rock mass | 2018/01/01–2018/12/31 | Three Gorges, bbox E110.27–111.00, N30.62–31.17 (WGS84) | `.doc`, 52.4 MiB | NCDC agreement; **Apply to Access** | **V-LP** |

> **Note on Baishuihe / Bazimen machine-learning datasets.** The widely reused "Baishuihe /
> Bazimen / Tanjiaba landslide displacement" tables circulating in ML papers are **not** published
> as a standalone open dataset. They are extracted from this NCDC per-year series or supplied as
> paper supplements. See "Could not verify" below.

### 1b. Other Chinese landslide monitoring time series (Zenodo)

| # | Dataset title | Repository | DOI | Contents | Time span / interval | Location | Format / size | License | Ver. |
|---|---|---|---|---|---|---|---|---|---|
| 5 | GNSS Ground Monitoring Data of the Hongyanzi Landslide Area in China from 11 Nov 2021 to 4 Jun 2022 | Zenodo | `10.5281/zenodo.13254357` | GNSS 3-D displacement from **5 stations**, projected onto InSAR LOS; 1-D displacement time series | 2021-11-11 – 2022-06-04 | Hongyanzi landslide, China | `LOS-GNSS.txt`, 6.8 kB | **CC-BY-4.0**, open (anonymous download) | **V-LP + V-API** |
| 6 | Daily rainfall, groundwater depth, and GNSS displacement data from the Qili landslide, China (2016–2017) | Zenodo | `10.5281/zenodo.21916040` | 720 consecutive daily records: `Date`, daily rainfall, groundwater depth, cumulative surface displacement | 2016-01-12 – 2017-12-31; **daily** | Qili landslide, Quzhou, Zhejiang | `data.xlsx` 33.4 kB + README | **CC-BY-4.0**, open | **V-LP + V-API** |
| 7 | Rainfall threshold data for landslides in the Three Gorges reservoir area | Zenodo | `10.5281/zenodo.11311851` | Landslide susceptibility layers + rainfall thresholds (rasters: DEM, distance-to-river, structural density, disaster polygons) | not stated | Three Gorges reservoir area | `DEM.tif` 6.5 MB, many `.tif`/`.tfw`/`.vat.dbf`, `Code.zip` 5.9 kB | **CC-BY-4.0**, open | **V-API** (files enumerated) |

### 1c. Landslide monitoring time series outside China (Zenodo, metadata-verified)

| # | Dataset title | Repository | DOI | Contents | Location | License / access | Ver. |
|---|---|---|---|---|---|---|---|
| 8 | Groundwater and landslide displacement records of the Eggerberg slope (Gradenbach landslide, Carinthia, Austria) | Zenodo | `10.5281/zenodo.21033260` | Groundwater + displacement records | Carinthia, Austria | CC-BY-4.0, open | **V-API** |
| 9 | Data sets for assessing potential CC impacts on the activity of the Vögelsberg landslide | Zenodo | `10.5281/zenodo.6337833` | Climate/landslide activity modelling inputs | Tyrol, Austria | CC-BY-4.0, open | **V-API** |
| 10 | Data and scripts for the analysis of Achoma landslide precursors | Zenodo | `10.5281/zenodo.17753976` | Precursor analysis data + scripts | Achoma, Peru | CC-BY-4.0, open | **V-API** |
| 11 | Pietrapertosa landslide monitoring data | Zenodo | `10.5281/zenodo.19099868` (and `.19099869`) | Monitoring data | Pietrapertosa, Italy | CC-BY-4.0, open | **V-API** |
| 12 | Monitoring of the Reissenschuh landslide based on periodical DGNSS measurements | Zenodo | `10.5281/zenodo.6519780` | Periodic DGNSS measurements | Reissenschuh, Austria | **No license stated; access RESTRICTED** | **V-API** |

### 1d. Hong Kong landslide inventory

| # | Dataset title | Repository | URL / DOI | Contents | Format | License / access | Ver. |
|---|---|---|---|---|---|---|---|
| 13 | Enhanced Natural Terrain Landslide Inventory (ENTLI) | DATA.GOV.HK (CEDD / GEO Open Data) | https://data.gov.hk/en-data/dataset/hk-cedd-csu-cedd-entli (no DOI; CSDI dataset id `cedd_rcd_1636520697377_96152`) | Catalogue of historical natural-terrain landslides; data dictionary PDF supplied | Geospatial download via CSDI geoportal; API available | Open government data; governed by **CEDD GEO Open Data Terms and Conditions** (https://www.ginfo.cedd.gov.hk/GEOOpenData/Disclaimer_en.html) — not a CC license | **V-LP** |

### 1e. ML-ready tabular landslide-sensor datasets

| # | Dataset title | Repository | DOI / URL | Contents | Format / size | License | Ver. |
|---|---|---|---|---|---|---|---|
| 14 | Wireless Sensor Network Landslide Dataset ("Data from Sensors for the Prediction of Landslides") | Kaggle (mirrored from UCI ML Repository) | https://www.kaggle.com/datasets/ucimachinelearning/wireless-sensor-network-landslide-dataset | **This is the closest thing found to a multi-sensor landslide station table.** 30+ columns with declared sensor provenance: rainfall 24 h / 3-day / 7-day (rain gauge), slope angle (inclinometer + DEM), **soil saturation (soil moisture probe)**, **soil moisture content (soil moisture probe)**, **pore water pressure kPa (vibrating-wire piezometer)**, **microseismic activity (geophone/accelerometer)**, **acoustic emission dB**, **soil strain (strain gauge / FBG)**, soil temperature (thermistor), **TDR reflection index (time-domain reflectometry)**, soil pH, clay/sand/silt %, soil erosion rate, vegetation/NDVI, aspect, elevation, land use, earthquake activity, proximity to water, distance to road, temperature, humidity | 3.24 MB | **CC0: Public Domain** | **V-API** (Kaggle API record incl. full column dictionary) |
| 15 | Barry Arm Landslide Displacement Data | Kaggle | https://www.kaggle.com/datasets/saurabhshahane/barry-arm-landslide-displacement-data | Landslide displacement data (Barry Arm, Alaska) | not stated | CC BY 4.0 | **V-API** (list record) |
| 16 | Landslide4Sense | Kaggle | https://www.kaggle.com/datasets/tekbahadurkshetri/landslide4sense | Sentinel-2 based landslide mapping benchmark — **imagery, not sensor time series** | 3.06 GB | "Other (specified in description)" | **V-API** (list record) |

> **Caveat on #14:** the Kaggle record does not name the field site, deployment period, or station
> count, and the value ranges look like a generated/compiled teaching table rather than raw
> station telemetry. Use it as an ML input, **not** as a citable field-monitoring record.

---

## Category 2 — Debris-flow monitoring datasets

### 2a. Illgraben, Switzerland (WSL / EnviDat) — the best-documented open debris-flow observatory

All records below were retrieved through the **EnviDat CKAN API** (`/api/3/action/package_show`),
which returns DOI, license, author ORCIDs, and direct CSV download URLs.

| # | Dataset title | DOI | Contents & sensors | Time span / interval | Format / size | License | Ver. |
|---|---|---|---|---|---|---|---|
| 17 | **Volumetric Water Content Measurements at Illgraben 2022** | `10.16904/envidat.489` | VWC (soil moisture) at **0.25 m / 0.45 m** (ECH2O EC-5) and **0.65 m / 0.85 m** (TEROS 12); water level, temperature, electrical conductivity, air reference pressure at 0.80 m (CTD10) | May–Oct 2022 (2022 debris-flow season); **165,780 data points at 5-minute sampling**; CTD10 only until 27 Jun 2022 | `SM_Illgraben_2022.csv` 1.62 MB + `readme.md` | **WSL Data Policy** (not CC) | **V-API** |
| 18 | Illgraben debris-flow characteristics 2023 | `10.16904/envidat.630` | Occurrence date/time, peak flow depth, peak flow velocity, total volume, bulk density | 2023 season, event-based; updated annually | CSV 786 B + `Readme.txt` | **CC-BY-SA** | **V-API** |
| 19 | Illgraben debris-flow characteristics 2019–2022 | `10.16904/envidat.378` | Same variable set as above, 4 seasons | 2019–2022 | CSV | WSL Data Policy | **V-API** |
| 20 | Debris-flow volumes at the Illgraben 2000–2017 | `10.16904/envidat.173` | Debris-flow bulk volumes from the WSL monitoring station | 2000–2017, event-based | CSV 2.0 kB | WSL Data Policy | **V-API** |
| 21 | Debris flow observation at Illgraben 2024: Event Data 15 June / 21 June | `10.16904/envidat.448` | **Cumulative rainfall at station CD1** + **radar-based flow height at CD28**, for two events | 15 & 21 Jun 2024; event time series | 4 × CSV, 34–86 kB each | **CC-BY-4.0** | **V-API** |
| 22 | Dataset for "Sorting and Surging 3D LiDAR and Pulse-Doppler Radar Analysis of a Natural Debris Flow" | `10.3929/ethz-b-000717695` | 3-D LiDAR + pulse-Doppler radar + camera video of the 30 Jun 2022 Illgraben event | 30 Jun 2022 | not stated | CC-BY-SA | **V-API** (list record) |
| 23 | Source code for: Evaluating methods for debris-flow prediction based on rainfall in an Alpine catchment | `10.16904/envidat.240` | Rainfall-threshold computation code (Hirschberg et al. 2021 method) — **code, not data** | — | Python | "Other (specified in description)" | **V-API** |
| 24 | Data for Numerical Investigation of Sediment Yield Underestimation in Supply-Limited Mountain Basins with Short Records | `10.16904/envidat.303` | AWE-GEN climate-forcing time series + hydrological outputs | — | not stated | WSL Data Policy | **V-API** |

### 2b. Jiangjia Ravine / Jiangjiagou 蒋家沟, Dongchuan, Yunnan (China) — NCDC

A complete 2025 field campaign, six companion records, one DOI each. All **"Login to Access"**
(registered account required; no CC license — NCDC agreement).

| # | Dataset title | DOI | Contents | Interval | Format / size | Access | Ver. |
|---|---|---|---|---|---|---|---|
| 25 | **Seismic data of debris flow at Jiangjia Ravine, Yunnan, China (2025)** | `10.12072/ncdc.ddfors.db7459.2026` | Monitoring data of three debris-flow micro-earthquakes (19, 24, 29 Jul 2025) | **100 ms** time resolution | `.xlsx`, `.docx`; **505.5 MiB** | Login to Access | **V-LP** |
| 26 | Debris-flow kinematic data at Jiangjia Ravine, Dongchuan, Yunnan, China (2025) | `10.12072/ncdc.ddfors.db7458.2026` | Movement elements of three debris-flow events | **1 s** | `.xlsx`, `.docx`; 4.8 MiB | Login to Access | **V-LP** |
| 27 | Particle size distribution of debris flows at Jiangjia Ravine, Dongchuan, Yunnan, China (2025) | `10.12072/ncdc.ddfors.db7460.2026` | Grain-size distribution, three samples | event-based | `.xlsx`; 1.1 MiB | Login to Access | **V-LP** |
| 28 | Rheological data of debris-flow slurry at Jiangjia Ravine, Yunnan, China (2025) | `10.12072/ncdc.ddfors.db7461.2026` | Slurry rheological parameters, three samples | event-based | `.xlsx`; 227.1 KiB | Login to Access | **V-LP** |
| 29 | Measurement Records of Debris Flow Gully Sections in Jiangjiagou, Yunnan Province (2025) | `10.12072/ncdc.ddfors.db7465.2026` | Two cross-section surveys (Mar & Nov 2025) | **daily** | `.xlsx`, `.docx`; 941.0 KiB | Login to Access | **V-LP** |
| 30 | Video of debris flows that occurred at Jiangjia Ravine, Dongchuan, Yunnan, China (2025) | `10.12072/ncdc.ddfors.db7468.2026` | Video of the three 2025 events | — | video | Login to Access | **V-LP** |

### 2c. Other debris-flow datasets

| # | Dataset title | Repository | DOI | Contents | Sensors / notes | License | Ver. |
|---|---|---|---|---|---|---|---|
| 31 | Dataset for "Characterization of stream, hyperconcentrated and debris flows from seismic signals" (Yang, Chen, Meng — Lanzhou University) | Zenodo | `10.5281/zenodo.10773103` | **Seismic data of 11 flow events in Goulinping gully, 2022 (UTC+8)**, plus three field-experiment datasets | Seismic; `.xlsx` 77.1 MB + `.rar` 51.3 MB (**128.3 MB total**) | **CC-BY-4.0**, listed Open with downloadable files | **V-LP** |
| 32 | Two multi-temporal datasets to track debris flow after the 2008 Wenchuan earthquake | Zenodo | `10.5281/zenodo.6891244` | Post-earthquake debris-flow tracking, Wenchuan | Remote-sensing/debris-flow mapping | CC-BY-4.0 | **V-API** |
| 33 | Debris Flow Hazard-Causing Factors Dataset for the Yunnan Section of the Nujiang River Basin, China | Zenodo | `10.5281/zenodo.17490357` | Topographic/hydrological/geological/meteorological/vegetation factors for DL prediction — **static factors, not time series** | — | CC-BY-4.0 | **V-API** |
| 34 | Worldwide Debris-Flow Dataset and Pareto-Poisson Simulation Code | Zenodo | `10.5281/zenodo.18743612` | Global debris-flow event compilation + simulation code | — | CC-BY-4.0 | **V-API** |
| 35 | Digital elevation model of differences of two debris flow event in Chutou gully | Zenodo | `10.5281/zenodo.6668720` | DoD of two events | — | CC-BY-4.0 | **V-API** |
| 36 | Debris Flow Dataset for Debris Flow Velocity Inversion based on Optical Flow | Zenodo | `10.5281/zenodo.17514494` | USGS large-scale flume experiments (2007/2015/2017), raw + optical-flow derived velocity | Video; multiple `.mp4`, up to 45 MB each | CC-BY-4.0 | **V-API** |

---

## Category 3 — China high-mountain / permafrost / soil-moisture monitoring

| # | Dataset title | Repository | DOI | Contents | Access | Ver. |
|---|---|---|---|---|---|---|
| 37 | Sample data set of moisture survey in the active layer of the permafrost region of the Qinghai-Tibet Plateau (2009–2024) | NCDC (`permafrost` collection) | `10.12072/ncdc.permafrost.db7703.2026` | Active-layer moisture survey samples, Qinghai–Tibet Plateau | **Open Access** | **V-LP** |
| 38 | The mean annual ground temperature (MAGT) and permafrost thermal stability dataset over Tibetan Plateau for 2005–2015 | NCDC (`nieer` collection) | `10.12072/ncdc.nieer.db6676.2024` | Mean annual ground temperature + permafrost thermal stability | **Open Access** | **V-LP** |

**TPDC (国家青藏高原科学数据中心, `data.tpdc.ac.cn`) — access limitation, see "Could not verify".**
The Centre's search requires login, and dataset pages render as a JS shell that returns
"No data temporarily" with **"Sharing way: Apply for access"**. Its DOI prefix `10.11888` is **not
registered with DataCite** (a lookup returns 404), so TPDC DOIs cannot be validated through the
DataCite API and must be confirmed manually inside the portal.

---

## Category 4 — Wireless-link / network telemetry traces in mountain or remote terrain

| # | Dataset title | Repository | DOI | Contents | Environment | Format / size | License / access | Ver. |
|---|---|---|---|---|---|---|---|---|
| 39 | **CRAWDAD `isti/rural`** — transmission distance vs. packet loss on a Wi-Fi network in rural areas | IEEE DataPort (CRAWDAD) | `10.15783/C7G01C` | **Frame-level link traces**: per-frame receive time, frame length (500/1000/1500 B), sequence number, quality level, **signal level (×0.6 → dB)**, **noise level**, received/lost status, number of corrupted bits on CRC failure. Fixed speeds 1 / 2 / 5.5 / 11 Mb/s; ARQ, RTS/CTS and fragmentation disabled so the channel is sampled at **200 frames/s, 200,000 frames per measurement** | Wide uncultivated field, unobstructed line-of-sight, rural; Navacchio (Pisa), **April 2006**; 802.11b ad hoc, two IBM ThinkPad R40e | Text traces, several distance/speed/length combos; aggregation files per 1000 frames | **Open access** on IEEE DataPort | **V-LP** |
| 40 | CRAWDAD `kth/rss` — Radio Signal Strength + robot location | IEEE DataPort (CRAWDAD) | `10.15783/C7088F` | **RSSI in dBm** with robot position/orientation/velocity from odometry; indoor trace = **5 receivers** (4 directional + 1 omnidirectional antenna) | Indoor (KTH) and **semi-outdoor** (Dortmund) | Trace columns documented (timestamp s/ms, x, y, z, orientation, velocities, RSS1–RSS5 dBm) | **Open access** on IEEE DataPort | **V-LP** |
| 41 | An Experimental Dataset for Search and Rescue Operations in Avalanche Scenarios Based on LoRa Technology | Zenodo | `10.5281/zenodo.13932869` (v2); concept DOI `10.5281/zenodo.12750580` | **LoRa RSSI + SNR** with ground-truth positions. Three test types: *cross test* (buried TX at varying depth, 4 receivers on tripod at 10 distances × 4 orientations, 0.6–50 m), *maximum-distance test* (receiver walked until signal loss, 2-min samples at markers), *drone flyover* (121-point grid over 100 m²). Includes snow profiles (AINEVA Model 4) | **Plateau at Col de Mez, Falcade, Italian Dolomites, 1,870 m**, March (dry snow >1 m) and April 2024 (wet snow ~55 cm) | `LoRa-SaR-dataset.zip` 1.8 MB; CSV columns: timestamp, rssi, snr, rx_pos/distance/depth/polarization, or lon/lat/x/y | **CC-BY-4.0**, open | **V-LP + V-API** |
| 42 | LoRa signal quality and GPS positioning time series dataset | Zenodo | `10.5281/zenodo.13835721` | Time series from **3 LoRa gateways**: device ID, **RSSI and SNR per gateway (3×)**, LoRa spreading factor, timestamp, GPS lat/lon/altitude | **Sálvora Archipelago, Galicia, Spain** (Atlantic Islands of Galicia National Park); gateway altitudes 73 m / 5 m / 31 m | Single CSV | **CC-BY-4.0**, open | **V-LP + V-API** |
| 43 | LoED: The LoRaWAN at the Edge Dataset | Zenodo | `10.5281/zenodo.4121430` (v3) | Raw LoRaWAN gateway payload records + metadata from **9 gateways**; daily CSVs | **Urban** (London) — *not* mountain; included as LPWAN link-trace reference | `LoED_LoRaWAN_at_edge_dataset.zip` + sample zip + parser notebook/py; **503.6 MB** total | **CC-BY-4.0**, open | **V-LP + V-API** |
| 44 | An Experimental Dataset Using UAVs and LoRa Technology in Avalanche Scenarios | Zenodo | `10.5281/zenodo.16572816` | LoRa measurements with a UAV in avalanche scenario | Italian Dolomites (same group as #41) | not stated | **CC-BY-4.0**, open | **V-API** |

### Assessment of Category 4

- **Genuine multi-day mountain WSN link-quality traces with PDR/outage logs are scarce.**
  The best-fitting items are #41 and #42 (LoRa RSSI/SNR in alpine and rugged-island terrain) and
  #39 (frame-level Wi-Fi loss vs. distance in open rural terrain — the only one with true
  per-frame loss and CRC-corruption counters).
- **#40 and #43 are not mountain deployments** (indoor/semi-outdoor and urban respectively) but are
  the standard citable link-quality traces and are open.
- **No dataset was found that logs link quality (RSSI/LQI/PDR) as a by-product of a Chinese
  mountain geohazard monitoring network.** See "Could not verify".

---

## Could not verify / not found

### A. Chinese geohazard monitoring data behind application barriers (real, but not openly downloadable)

| Item | Where | Why not verified as open |
|---|---|---|
| TPDC (国家青藏高原科学数据中心) datasets, incl. 青藏高原多年冻土综合监测数据集（2002–2018） (`casearthpoles.tpdc.ac.cn/zh-hans/data/789e838e-16ac-4539-bb7e-906217305a1d/`) | `data.tpdc.ac.cn` | Search requires login; dataset page renders as a JS shell showing "No data temporarily" and **"Sharing way: Apply for access"**. The CAS-Earth-Poles mirror host `casearthpoles.tpdc.ac.cn` refused connections entirely (ERR_CONNECTION_REFUSED), as did `poles.westdc.cn`. **Prefix `10.11888` is absent from DataCite** (index lookup → 404), so TPDC DOIs cannot be confirmed via API. |
| Baishuihe landslide 2023 deformation/rainfall/reservoir monitoring data (`huanghe.ac.cn/metadata/299fcbb2-65f9-4085-a196-34bce8f568c7`) | 黄河数据中心 / NCDC mirror | Landing page returned **HTTP 500 Internal Server Error** through the reader proxy on two attempts. The DOI could not be read. |
| ENTLI at `hkss.cedd.gov.hk` | HKSS | All `hkss.cedd.gov.hk/hkss/eng/...` paths requested returned **HTTP 404**; the working route is DATA.GOV.HK (#13). |

### B. Explicit negative results — searched, nothing qualifying found

1. **No open dataset of wireless-link traces (RSSI/LQI/PDR/outage logs) from a Chinese mountain
   geohazard-monitoring wireless sensor network.** Searched: Zenodo API (`wireless sensor network
   landslide`, `LoRa mountain`, `LPWAN field measurement`), DataCite, CRAWDAD/IEEE DataPort,
   Kaggle API, ScienceDB. The only Chinese entries found are application-gated NCDC station
   records with no link-layer telemetry.
2. **No open NB-IoT field-measurement dataset for mountainous terrain located.** LoRa dominates
   the open LPWAN-measurement literature (#41–#44); no NB-IoT equivalent surfaced.
3. **No standalone, openly downloadable "Baishuihe / Bazimen / Tanjiaba" ML displacement dataset.**
   Those tables are derived from the NCDC per-year records (#1–#4, all apply-to-access) or supplied
   as journal supplements. Searched Zenodo API with `Baishuihe`, `Bazimen`, `Tanjiaba`,
   `Three Gorges landslide displacement` — the only exact hits were unrelated taxonomic records,
   confirming the name search returns nothing (Zenodo reported 621 hits for those tokens, **none**
   matching a landslide dataset).
4. **ScienceDB (科学数据银行, `scidb.cn`) could not be searched.** No working public search
   endpoint: `/api/sdb-search/dataset`, `/api/sdb-search/dataset/search` and `/api/search/dataset`
   all returned **HTTP 404**. **No ScienceDB dataset is reported here.**
5. **PANGAEA could not be searched usefully.** Its Elasticsearch index at
   `ws.pangaea.de/es/pangaea/panmd/_search` returns hits whose `title` field is stored
   obfuscated/encoded, and field-scoped queries (`title:"debris flow"`) returned **0 hits**;
   `?format=json` on the web UI returns HTML. **No PANGAEA dataset is reported here.**
6. **Dryad blocked automated retrieval.** `datadryad.org/search` returned an Anubis bot-check
   interstitial ("Validating… / Loading…") instead of results. **No Dryad dataset is reported
   here** (only Dryad DOIs seen incidentally in unrelated DataCite noise).
7. **OpenML has no landslide dataset.** `data/list/data_name/landslide` returned
   `{"error":{"code":"372","message":"No results"}}`.
8. **UCI ML Repository direct lookup failed.** The guessed URL `archive.ics.uci.edu/dataset/447/...`
   resolved to an unrelated dataset ("Condition monitoring of hydraulic systems"), and
   `archive.ics.uci.edu/api/datasets?search=landslide` returned 404. The UCI-origin WSN landslide
   dataset is therefore cited through its **Kaggle mirror (#14, CC0)**, which was verified via the
   Kaggle API.
9. **IEEE DataPort search pages are not machine-readable.** `ieee-dataport.org/search?query=landslide`
   rendered only unrelated featured content, `/search/site/...` returned 404, and a JSON search
   endpoint returned 404. The two CRAWDAD datasets (#39, #40) were verified by opening their
   **direct** landing pages, not through search.
10. **No open debris-flow *stage/discharge hydrograph* dataset for Jiangjia Gully** was found — the
   2025 NCDC records cover seismic, kinematics, grain size, rheology, sections and video, but are
   login-gated and are not a continuous stage record.
11. **No open tilt-meter or crack-meter (displacement transducer) time-series dataset** for any
    Chinese landslide was found. The nearest equivalents are GPS/GNSS surface displacement
    (#1–#6) and the compiled sensor table (#14).
12. **No dataset found for Gansu, Guizhou, Chongqing, or Tibet specifically containing geohazard
    monitoring sensor time series.** The Chinese monitoring time series located are concentrated in
    Hubei (Three Gorges), Zhejiang, and Yunnan; the Tibet/QTP holdings are permafrost ground
    temperature and active-layer moisture (#37, #38), i.e. environmental rather than
    landslide-specific.

### C. Repository-by-repository coverage for the requested list

| Repository | Outcome |
|---|---|
| **Zenodo** | Searched via REST API (`/api/records`). Datasets #5–#12, #31–#36, #41–#44. **Productive.** |
| **DataCite** | Searched via `/dois`. Used to enumerate datasets and to test TPDC prefix coverage (negative). **Productive for enumeration.** |
| **IEEE DataPort** | Search not machine-readable; **direct landing pages** verified for CRAWDAD #39, #40. |
| **Figshare** | API (`/v2/articles/search`) works but returned only journal supplementary tables (PLOS/Frontiers .t001–.s002), no monitoring time series. **No qualifying dataset.** |
| **PANGAEA** | Index unusable programmatically (see B5). **No result.** |
| **Dryad** | Bot-protected (see B6). **No result.** |
| **Kaggle** | `/api/v1/datasets/list` and `/api/v1/datasets/view` work well. Datasets #14–#16. **Productive.** |
| **ScienceDB (科学数据银行)** | No working public search endpoint (HTTP 404). **No result.** |
| **TPDC (data.tpdc.ac.cn)** | Login-gated; DOIs not in DataCite. **No result.** |
| **国家地球系统科学数据中心 / NCDC (ncdc.ac.cn)** | Search renders via reader proxy at `/portal/metadata?q=…`. Datasets #1–#4, #25–#30, #37, #38. **Most productive single source for Chinese material.** DOIs resolve via doi.org but the `10.12072` prefix is served by a non-DataCite registration agency. |
| **HydroShare** | `/hsapi/resource/?q=landslide` works (8,892 hits) but results are GIS/coursework resources; **no sensor time series** identified. |
| **UCI ML Repository** | Direct API 404 / wrong-ID resolution; dataset reached via Kaggle mirror (#14). |
| **OpenML** | No results (B7). |

---

## Practical notes for the report

- **Best fully-open, immediately downloadable monitoring time series in the survey:**
  #17 (Illgraben soil moisture / water level, 5-min, 165,780 points), #5 and #6 (Chinese
  GNSS + rainfall/groundwater, CC-BY-4.0), #31 (Goulinping debris-flow seismic, CC-BY-4.0),
  #39 and #41/#42 (link-quality traces, all open).
- **Richest Chinese archives are permission-gated, not open.** NCDC's Three Gorges and Jiangjia
  Ravine series are the highest-value items for a China-focused report, but each requires a login
  or an access application and carries the NCDC license agreement rather than a CC license. Budget
  lead time for the requests.
- **License families encountered:** CC-BY-4.0 (most Zenodo), CC-BY-SA (some EnviDat), **CC0**
  (Kaggle #14), **WSL Data Policy** (several EnviDat records — *not* an open license, verify terms
  before redistribution), **NCDC agreement** (Chinese records), **CEDD GEO Open Data Terms** (HK).
- **Sampling rates captured:** Jiangjia Ravine seismic **100 ms**; Jiangjia Ravine kinematics **1 s**;
  Illgraben soil moisture **5 min**; CRAWDAD isti/rural **200 frames/s**; Qili landslide **daily**.
