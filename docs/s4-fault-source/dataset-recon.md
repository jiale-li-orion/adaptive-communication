# Dataset Reconnaissance: Lifecycle Traces of Degradation → Outage → Recovery

**Scope:** real or trace-driven data showing network degradation → outage → recovery in disaster / emergency / mountain-monitoring communication scenarios, judged for use as a **replay trace for an agent benchmark** (injecting node/link failures).

**Method:** live HTTP probes against ArcGIS REST, GeoServer/WMS, Zenodo API, IEEE DataPort, and actual dataset downloads (files were fetched and parsed, not just read about). Every claim below is either **VERIFIED BY FETCH** (I downloaded/queried it) or marked **UNVERIFIED**.

**Verification date:** observed 2026-09-12 (all live probes run this session).

---

## 1. FEMA TEMPO — "Communication Impacts" layer

### (1) Exact name and maintainer
`TEMPO_Communication_Impacts`, layer **ID 4** of the `TEMPO/TEMPO` MapServer/FeatureServer on FEMA's ArcGIS server. Data owner: **FEMA HQ Response, Geospatial Office** (contact listed in the layer metadata: Adam Barker, FEMA; Brooke Hatcher, New Light Technologies). The **underlying source is the FCC Disaster Information Reporting System (DIRS)** — FEMA republishes and aggregates it.

- Layer page: <https://gis.fema.gov/arcgis/rest/services/TEMPO/TEMPO/MapServer/4>
- Item info: <https://gis.fema.gov/arcgis/rest/services/TEMPO/TEMPO/FeatureServer/4/iteminfo?f=pjson>

### (2) What it actually contains — **VERIFIED BY FETCH**
Layer type is `esriGeometryPolygon` (county polygons). Confirmed fields (exact spelling preserved):

| field | alias | meaning |
|---|---|---|
| `date_` | Date | daily snapshot date |
| `event` | Event | incident name (`Ian`, `Ida`, `Fiona`, `Nicole`, `Karen`, `HurricaneA`) |
| `fips` / `cnty_fips` / `state_fips` | County FIPS code | 5-digit county key |
| `name`, `state_name`, `state_abbr`, `county_state` | — | county/state labels |
| `cell_sites_served` | Number of cell sites served | denominator |
| `cell_sites_out` | Cell Sites Out | numerator |
| `percentout` / `percent_out` | Percent Out / Percent Cell Towers Out | % out (numeric + string form) |
| `cell_sites_out_due_to_damage` | Number of cell sites out due to damage | **cause category** |
| `cell_sites_out_due_to_power` | Number of cell sites out due to power outage | **cause category** |
| `cell_sites_out_due_to_transpor` | Cell Sites Out Due to Transport | **cause category (truncated field name)** |
| `populationaffected` / `population` | Number of people affected / Pop 2017 | exposure |
| `sqmi`, `fema_regio`, `affected_counties`, `comments`, `lastupdatedon` | — | context |

**Cause categories confirmed present and populated.** Example record fetched: Gilchrist County FL, 2022-10-01, Ian, `cell_sites_served=19`, `cell_sites_out=1`, `percentout=5.3`, damage=0, power=0, transport=1, populationaffected=600. Another: Glades County FL, Ian, `cell_sites_out=6` all attributed to power.

- **Granularity:** space = **county** (no per-site or per-tower records, no site IDs, no coordinates of towers); time = **daily** (`date_`), with `lastupdatedon` giving an intra-day refresh timestamp.
- **Record count:** `returnCountOnly` = **1237** county-day rows (**VERIFIED**).
- **Distinct event distribution (VERIFIED):** Ian 477, Ida 414, Fiona 234, HurricaneA 46, Nicole 34, Karen 32.
- **Time coverage observed (VERIFIED):** distinct `date_` values 2022-05-31, 2022-06-17, 2022-09-20, 2022-09-28 → 2022-10-07, 2022-11-10, plus one null-epoch row (1899-12-30, an empty-date artifact). **Important caveat:** this is what the live layer currently serves. TEMPO appears to be a **rolling/most-recent-events snapshot**, so historical events are not guaranteed to persist. I could **not** verify a long-term archive of TEMPO communication layers. The 2022-09-28 → 2022-10-07 block is a clean daily Ian progression.

### (3) Access — **direct, no key, no paywall, machine-readable**
The service capabilities are `Map,Query,Data` with `maxRecordCount: 2000`. Working queries verified this session:

```
# all records as JSON
https://gis.fema.gov/arcgis/rest/services/TEMPO/TEMPO/MapServer/4/query?where=1%3D1&outFields=*&returnGeometry=false&f=json
# with county geometry as GeoJSON
https://gis.fema.gov/arcgis/rest/services/TEMPO/TEMPO/MapServer/4/query?where=1%3D1&outFields=*&f=geojson
# filtered
https://gis.fema.gov/arcgis/rest/services/TEMPO/TEMPO/FeatureServer/4/query?where=event%3D%27Ian%27&outFields=*&f=json
```
Add `&f=csv` for CSV output. No API key, no authentication, no rate-limit header observed. Related TEMPO layers on the same service: `TEMPO_PowerOutage_Impacts` (6), `TEMPO_Transportation_County_Impacts` (1), `TEMPO_FoodWaterShelter_Impacts` (0) — useful to co-inject correlated power/transport failure.

**Unverified:** whether FCC publishes a *bulk* DIRS archive separate from this. FCC DIRS itself is described in the layer metadata as "a voluntary, web-based system" for providers; I found the FCC DIRS info-sharing manual at <https://www.fcc.gov/sites/default/files/dirs_infosharingmanual0922.pdf> but I did **not** confirm a public per-provider DIRS bulk download. Treat "DIRS raw bulk data" as **UNVERIFIED**.

### (4) License / terms
Layer `copyrightText` = `"FEMA RGO"`. US federal government work; no explicit license or terms-of-use document is attached to the ArcGIS item. Attribution to FEMA is the safe practice. **No explicit open license tag was found — I did not find a CC/public-domain statement, so treat reuse terms as UNVERIFIED-but-presumed-US-Government-public-domain.**

### (5) Size
**1237 polygon features** (county-day rows). Metadata-only query is ~a few hundred KB; with geometry the full GeoJSON is a few MB. Trivially small.

### (6) Time coverage
Effectively **2022 hurricane season** for the currently served rows (plus one 2022-05-31 and one 2022-06-17 row). Not a multi-year continuous archive. **VERIFIED as the current state of the live layer only.**

### (7) Per-node/per-link vs aggregate
**Aggregate only.** County-level *counts* of outages. There is **no per-cell-site availability timeline, no site ID, no link data**. What you *do* get is a per-county **time series** (daily) of an outage fraction, splittable by cause. So: aggregate maps **plus** a real aggregate temporal outage/recovery curve — not node-level.

### (8) Judgment: **PARTIAL (high value for aggregate-ground-truth calibration; not a node/link trace)**
- **Why partial:** It is the single best *real, authoritative, cause-attributed, daily* communications-outage ground truth I found that is openly machine-readable with no paywall. Its cause split (damage / power / transport) directly matches the failure-mode taxonomy this project wants, and the daily cadence over a named event gives a genuine degradation→peak→recovery arc.
- **Why not yes:** granularity is county, not node or link. You cannot replay "which tower failed when." It can serve as (a) a **calibration/validation signal** for a synthetic replay, or (b) an **event schedule generator** (e.g. "in county Hardee on 2022-10-01, 46.2% of sites are down, driven by power") that a replay engine then expands into node failures. Pair it with `TEMPO_PowerOutage_Impacts` to drive the power cause.

---

## 2. ITU Disaster Connectivity Map (ITU DCM)

### (1) Exact name and maintainer
**Disaster Connectivity Map (DCM)** — ITU, in partnership with the **Emergency Telecommunications Cluster (ETC)**; map app hosted by ITU under the Broadband Maps / ICT-data mapping platform.

- Portal: <https://dcm.itu.int/>
- Programme page: <https://www.itu.int/en/ITU-D/Emergency-Telecommunications/Pages/Disaster-Connectivity-Map.aspx>
- Catalogue record: <https://bbmaps.itu.int/geonetwork/srv/metadata/227adef7-e5e9-4c4d-8c36-bcb47de75c5b>

### (2) What it actually contains — **VERIFIED BY FETCH**
The DCM web app is a **Leaflet + GeoServer (WMS)** application. I retrieved its `GetCapabilities` and enumerated the real layers. In the `dcm_prod` workspace there are **60+ layers**, including:

- QoS/measurement point layers: `point_mobile_allscales`, `point_coverage_allscales`, `dcm_mix_allscales`, `point_blueping_allscales`, `point_brownping_allscales`, `point_Green_allscales`, `point_Red_allscales`
- **Time-enabled QoS layers (hourly / daily):** `dcm_scr_1hr_1km`, `dcm_scr_24hr_1km`, `dcm_scr_1hr_allscales`, `dcm_mix_1hr_allscales`, `dcm_mix_24hr_allscales`, `Latest Connectivity By Hour`
- **Archive years:** `dcm_mix_archive_2020_1hr_allscales`, `..._2021_...`, `..._2022_...`
- Coverage layers from third parties: `GSM_2G`, `GSM_3G`, `GSM_4G`, `gsm_merged`, `raster_gsm_oci2g/3g/4g`, `OCI_Global*_2020_*`
- Hazard layers: `GDACS_hazard_events_multiple_geoms`, `gdacs_storm_track_lines/points`, `hz_event_3857`, `hz_json_3857`

**Time dimensions (VERIFIED from GetCapabilities):**
- `dcm_scr_1hr_1km` → `<Dimension name="time" units="ISO8601">2013-01-11T00:00:00.000Z/2026-09-12T02:22:23.949Z/PT1H</Dimension>` — **hourly**, nominally 2013→present.
- `dcm_scr_24hr_1km` → same start, `/P1D` — **daily**.
- `Latest Connectivity` (dcm_mix_24hr_allscales) → `2025-10-28T00:00:00.000Z/2025-10-29T00:00:00.000Z/P1D`.

**Crucial caveat (VERIFIED):** these are **declared layer dimensions**, and the start value `2013-01-11` looks like a fixed default rather than proof of 2013 data density. Higher-resolution layers (`dcm_scr_1hr_1km`) serve a **300×300 km region — your data is sparse per grid cell**.

**The ITU catalogue description explicitly states** (VERIFIED quote): *"DCM Connectivity is a rolling worldwide baseline map layer of measurement data... This map layer does not have a time dimension or time field, so cannot be filtered by time."* That description belongs to the **baseline connectivity** layer specifically; the hourly/daily layers do carry a time dimension.

**Underlying measurements are QoS probes, not infrastructure telemetry.** The catalogue description: measurements come *"from software probes installed on end-user devices"* (SpeedChecker: ping ms, download Mbps, upload Mbps), *"processed into point grid cells of 100-km, 10-km, 1-km, and 100-m."* Data sources listed on the portal's own legal notice: ITU Transmission Map, GSMA and Collins Bartholomew coverage maps, OpenCelliD, Meta for Good, Ookla for Good, M-Lab, NetBravo/JRC, GDACS, OpenStreetMap.

### (3) Access — **WMS only; no bulk download; no feature API**
- **Working:** WMS `GetCapabilities` and `GetMap`:
  `https://dcm.itu.int/geoserver/dcm_prod/wms?service=WMS&request=GetCapabilities&version=1.3.0` (**VERIFIED, 1.6 MB XML**)
  There is also a second workspace endpoint `https://dcm.itu.int/geoserver/dcm/wms?`.
- **Broken / unavailable (VERIFIED):** `GetFeatureInfo` fails with
  `The requested Style can not be used with this layer. The style specifies an attribute named 'map_scale', not found in the 'dcm_prod:dcm_scr_1hr_1km' layer`
  — so you **cannot** pull clean attribute records out of the temporal QoS layers as served.
- **Not available:** WFS `GetCapabilities` returns 549 bytes (empty service list), and `DescribeFeatureType` returned nothing → **no WFS feature download**.
- **No bulk download / no documented API / no request form** was found. Access is effectively **map tiles / WMS images**. Bulk extraction would require scraping GetMap rasters or the GeoServer REST admin API (not exposed publicly).

### (4) License / terms
GeoServer capabilities declare `Fees: none` and `AccessConstraints: none` (**VERIFIED**). However the portal's own legal notice is a **broad disclaimer**: ITU and cooperating entities *"do not warrant, guarantee or make any representations (implied or expressed) regarding the use, or the results of use, of the infographics, in terms of correctness, completeness, accuracy, adequacy, reliability, merchantability or fitness for a particular purpose"* and *"expressly disclaim any liability for errors or omissions."*

**No open license (CC-BY etc.) is declared.** Additionally the layer stack mixes **third-party data with its own restrictions** (GSMA/Collins Bartholomew coverage, Meta for Good, Ookla) — those are *not* freely redistributable. **Treat DCM as "viewable, not openly licensed, not bulk-reusable." Confirmed: no explicit license — UNVERIFIED legal basis for redistribution.**

### (5) Size
Not meaningfully quantifiable as a dataset — it is a WMS service. Raster tiles on demand. The `GetCapabilities` document alone is ~1.69 MB.

### (6) Time coverage
Hourly layers declare **2013-01-11 → present**; archive layers exist for **2020, 2021, 2022**; daily layers likewise. Practical density is unknown and the end of the declared range is a moving "now". **The historical depth is UNVERIFIED in practice.**

### (7) Per-node/per-link vs aggregate
**Aggregate + measurement-derived, not infrastructure status.** Grid cells of QoS measurements (ping/download/upload) at 100 km / 10 km / 1 km / 100 m. There are **no cell-site IDs, no per-tower availability, no per-link status, no cause categories**. The portal text mentions highlighting "areas highlighted in red which have persistent network outages" — that is an *inferred* outage from degraded/absent probe measurements, not a reported outage record.

### (8) Judgment: **NO (for node/link failure replay) / PARTIAL as a coarse spatial mask**
- **Why no:** no per-node or per-link availability. No outage/recovery *events* with cause. No bulk download — you would be screen-scraping rasters. Missing time-filterable attribute export. Third-party license encumbrance.
- **Where it is still useful:** a *coarse geographic prior* for where connectivity collapsed during a named disaster, or for choosing which region a replay scenario should target. Also useful as an independent **sanity check** against TEMPO. It cannot be the trace source.
- **Honest note:** the ITU catalogue's own evidence says the baseline layer has **no time field at all**, and the temporal layers are not exportable as attributes. I could not obtain a single machine-readable DCM outage record.

---

## 3. SitkaNet — landslide / mountain monitoring (Alaska)

### (1) Exact name and maintainer
**SitkaNet** — a low-cost, distributed sensor network for landslide monitoring, developed by the **OPEnS Lab (Openly Published Environmental Sensing Lab), Oregon State University**. Related to landslide monitoring near Sitka, Alaska.

- Paper: *SitkaNet: A low-cost, distributed sensor network for landslide monitoring and study*, **HardwareX 9 (2021) e00191**, DOI `10.1016/j.ohx.2021.e00191`
  - Full text: <https://www.hardware-x.com/article/S2468-0672(21)00020-1/fulltext>
  - PMC mirror (open): <https://pmc.ncbi.nlm.nih.gov/articles/PMC9041236/>
- Project wiki: <https://github.com/OPEnSLab-OSU/OPEnS-Lab-Home/wiki/SitkaNet>
- Poster: <https://events.engineering.oregonstate.edu/sites/expo.engr.oregonstate.edu/files/sitkanet_poster_2021.pdf>

### (2) What it actually contains — **VERIFIED BY FETCH (of the open PMC full text)**
The paper is a **hardware design / methods** article. It describes the node design, the hub, soil-moisture/pore-pressure/ tilt sensing, and the LoRa-based telemetry architecture. I searched the full PMC HTML for a data-availability statement and repository links.

**Finding:** the paper's "Associated Data" section contains **only** `Supplementary data 1 mmc1.docx` (11.9 KB) — supplementary material, not a dataset. **There is no data-availability statement, no Zenodo/figshare/Dryad/DataVerse DOI, and no released dataset of any kind.**

- Content type: hardware design + sensor hardware characterization. No packet-level logs, no RSSI/SNR traces, no communication traces released.
- Granularity: **N/A — no dataset.**

### (3) How to access
**You cannot.** No dataset is published. The only artifacts are the open-access paper, its 11.9 KB supplementary docx, the project wiki, and open-source hardware/firmware repos under the OPEnS Lab GitHub organization (<https://github.com/OPEnSLab-OSU>). Note also: the HardwareX/ScienceDirect full text is behind Cloudflare bot protection (my direct fetch returned "Just a moment... Enable JavaScript"), which is why I used the open PMC mirror.

### (4) License
Paper: HardwareX is open access (PMC full text available). Hardware/firmware: per-repository OSS licenses in the OPEnS Lab org (**not individually verified here — UNVERIFIED**). **Dataset license: N/A, no dataset exists.**

### (5) Size
N/A (no dataset). Supplementary docx = 11.9 KB.

### (6) Time coverage
N/A (no dataset).

### (7) Per-node/per-link vs aggregate
**Neither — there is no trace data.** Only sensor readings *conceptually*, and even those were not released as data.

### (8) Judgment: **NO**
- **Why no:** the dataset does not exist publicly. This is a hardware paper. No communication traces, no packet-level data, no availability timeline was released. Any claim that SitkaNet provides usable failure traces would be fabrication.
- **Residual value:** the *architecture* (LoRa sensor + hub topology in a landslide setting) is a legitimate **scenario template** for a benchmark — you could model a SitkaNet-like deployment. But the scenario would have to be synthetic.
- **Honesty flag:** I could not access the ScienceDirect fulltext directly (bot wall); my "no data availability statement" conclusion is based on the **open PMC full text**, which is the same article. If a data deposit exists outside the article, it is **UNVERIFIED**.

---

## 4. Avalanche LoRa / SAR dataset (Italian Alps)

**Two Zenodo datasets exist — both VERIFIED by downloading and parsing the archives.**

### 4a. `An Experimental Dataset for Search and Rescue Operations in Avalanche Scenarios Based on LoRa Technology`

### (1) Name and maintainer
Girolami, Mavilia, Berton, Trifirò, Marrocco, Bianco — **CNR (Italian National Research Council) / University of Rome Tor Vergata** (pervasive.ing.uniroma2.it and IRIS CNR repositories).
- **DOI `10.5281/zenodo.13932869`** — <https://zenodo.org/records/13932869>
- Paper: IEEE Xplore <https://xplorestaging.ieee.org/document/10752629>
- Associated Data Article PDF: <https://iris.cnr.it/bitstream/20.500.14243/557362/3/Girolami_ExperimentalDataset_2025.pdf>

### (2) What it actually contains — **VERIFIED BY DOWNLOAD + PARSE**
Downloaded `LoRa-SaR-dataset.zip` (1,825,767 bytes) and extracted it. **6 CSV files, 241,745 data rows total.** Two distinct schemas:

- **Cross tests** (`dataset/cross/march/cross.csv`, `dataset/cross/april/cross.csv`):
  `timestamp, rssi, snr, rx_pos, distance, depth, polarization`
  - March: **115,218 rows**, 2024-03-07 08:16 → 13:12; depths **0 / 0.5 / 1 m**; RSSI **−117 … −11 dBm**; SNR **−1.0 … 13.75 dB**
  - April: **78,412 rows**, 2024-04-11 13:36 → 2024-04-12 09:47; depths **0 / 0.5 m**; RSSI **−111 … −42 dBm**; SNR **4.25 … 13.5 dB**
- **Drone tests** (`dataset/drone/drone.csv`): `timestamp, rssi, snr, longitude, latitude, x, y, depth` — **33,027 rows**, 2024-04-11 07:48 → 11:50; **GPS present** (lat 46.37749–46.37862, lon 11.82595–11.82758); RSSI −111…−54.
- **Max-distance tests** (`dataset/max_dist/march/max_dist.csv`, `april/max_dist_10apr.csv`, `april/max_dist_12apr.csv`): `timestamp, rssi, snr, depth, id_marker, longitude, latitude` — **6,235 / 5,712 / 3,141 rows**; **GPS present**; RSSI down to **−135/−136 dBm**; SNR down to **−15.5 dB** (at/below LoRa demodulation floor).
- Also included: **snow profile PDFs from ARPAV** (nivometric profiles, `20240307_Hres_10cm.pdf`, `20240411_Hres_5cm.pdf`) — these are the "snow depth" evidence, as profiles, not as a numeric column.

**Hardware/radio settings (from the dataset README, VERIFIED):** LILYGO T-beam (ESP32 + SX1276) Meshtastic boards; **TX power 14 dBm; 868 MHz; SF=7; BW=125 kHz; CR=4/5**; 30,000 mAh powerbank. Drone antenna: Caen-RFID WANTENNAX0053 circular-polarized.

**Honest correction to the task's assumption:** there is **no snow-depth numeric field** in the CSVs — snow state is conveyed via (a) the `depth` column (burial depth of the transmitter: 0/0.5/1 m) and (b) the ARPAV snow-profile PDFs. There is **no per-row snow depth**. GPS **is** present, but only in the drone and max-dist files (the cross-test files use `rx_pos` and `distance` instead of lat/lon).

### (3) Access — **direct open download, no account**
`https://zenodo.org/api/records/13932869/files/LoRa-SaR-dataset.zip/content` (VERIFIED, 1.83 MB, HTTP 200). Landing page <https://zenodo.org/records/13932869>.

### (4) License — **CC-BY-4.0 (VERIFIED from Zenodo API)**, open access.

### (5) Size — **1,825,767 bytes (1.83 MB)** zip; 241,745 CSV rows.

### (6) Time coverage — **2024-03-07** and **2024-04-10 … 2024-04-12**. Two seasonal campaigns (dry deep snow vs. wet shallower snow). Minutes-to-hours per individual test, not a long-term deployment.

### (7) Per-node/per-link vs aggregate
**Per-link, short-duration measurements** — this is raw RSSI/SNR per received packet along a transmitter→receiver link, with distance. It is **not** an availability/outage timeline: it is a **propagation/link-budget characterization** (signal vs. distance vs. burial depth vs. snow condition). No packet-loss timeline, no node up/down states, no recovery curve over days.

### (8) Judgment: **PARTIAL**
- **Why partial:** excellent as a **physical-layer link model** — it gives you a real, citable RSSI/SNR-vs-distance-vs-depth curve that a benchmark can use to decide *when a link degrades into unreachability* (note the −135 dBm / −15.5 dB extremes, i.e. the real edge of connectivity). That makes node/link failure injection physically grounded rather than arbitrary.
- **Why not yes:** no temporal outage/recovery structure; test windows are minutes long; no network-of-nodes topology; no per-node availability series. You cannot replay a disaster lifecycle from it alone — you would use it to *parameterize* a link model inside a synthetic replay.

### 4b. `An Experimental Dataset Using UAVs and LoRa Technology in Avalanche Scenarios`

- **DOI `10.5281/zenodo.17339095`** — <https://zenodo.org/records/17339095> — **VERIFIED**
- Creators: Mavilia, La Rosa, Berton, Girolami. Published 2025-07-29. **License CC-BY-4.0. Open access.**
- Single file `dataset.zip`, **10,790,636 bytes (10.8 MB)** — **VERIFIED via Zenodo API**.
- Data: RSSI/SNR from **one buried transmitter + one receiver on a quadcopter drone** flying multiple path typologies over a plateau at **Col de Mez, Soraga, Italy, 1870 m (Dolomites)**, across **April 2024, February 2025, April 2025**. Includes a grid of **121 measurement points covering 100 m × 100 m**.
- Related paper: *An experimental dataset using UAVs and LoRa technology in avalanche scenarios*, ScienceDirect <https://www.sciencedirect.com/science/article/pii/S2352340925009643>
- **Judgment: PARTIAL** — same reasoning as 4a: an aerial link-budget characterization, not an outage timeline. Adds an **airborne-node mobility dimension** useful for modelling a mobile relay/gateway in a mountain scenario. I did **not** download and parse this archive's CSV headers (only metadata verified) — schema is **inferred from the description, marked UNVERIFIED at field level.**

---

## 5. Long-term LoRaWAN metadata datasets with RSSI/SNR/SF/airtime/weather

**Four concrete public datasets verified. The two strongest are ChirpBox and LoED.**

### 5a. ChirpBox — Long-Term Outdoor LoRa Connectivity, Link Quality & Environmental Dataset ★ strongest

### (1) Name and maintainer
`Dataset: Environmental Impact on the Long-Term Connectivity and Link Quality of an Outdoor LoRa Network` — **Pei Tian, Fengxu Yang, Xiaoyuan Ma, Carlo Alberto Boano, Xin Tian, Ye Liu**. Collected on **ChirpBox** (<https://chirpbox.github.io/>) in **Shanghai, China**. TU Graz / ACM.
- **DOI `10.5281/zenodo.5527877`** — <https://zenodo.org/records/5527877>
- Companion paper: *Environmental Impact on the Long-Term Connectivity and Link Quality of an Outdoor LoRa Network*, ACM **DOI `10.1145/3485730.3493696`**

### (2) What it contains — **VERIFIED BY FULL DOWNLOAD AND PARSE (561 MB)**
I downloaded the complete `dataset_03052021_15092021.csv` (**561,810,444 bytes**) and parsed it.

- **Rows: 20,913 network snapshots.**
- **Time span (VERIFIED): 2021-05-03 07:47:03 → 2021-09-15 23:04:02** — 4.5 months, **2,470 distinct hours**.
- **SF distribution (VERIFIED):** SF7 3,494 / SF8 3,494 / SF9 3,496 / SF10 3,462 / SF11 3,472 / SF12 3,495.
- **Channels (VERIFIED):** 470,000 / 480,000 / 490,000 Hz.
- **Nodes: 21** (ids 0–20, from the README's `id_list = list(range(21))`).
- **Exact columns (VERIFIED):**
  `utc, time, sf, channel, tx_power, payload_len, min_snr, max_snr, avg_snr, min_rssi, max_rssi, avg_rssi, max_hop, max_hop_id, max_degree, min_degree, average_degree, average_temperature, symmetry, node_degree_list, node_temperature_list, node_link_matrix, max_rssi_matrix, avg_rssi_matrix, min_rssi_matrix, max_snr_matrix, avg_snr_matrix, min_snr_matrix, symmetry_matrix, weather_temperature, wind_speed, wind_deg, pressure, humidity`
- **Weather is included per record (VERIFIED):** `weather_temperature` (observed range **14.27 … 36.69 °C**), `wind_speed`, `wind_deg`, `pressure`, `humidity`.
- **Network topology is included per snapshot (VERIFIED):** `node_link_matrix` (adjacency per timestamp), `node_degree_list`, `max_hop`/`max_hop_id`, `symmetry`/`symmetry_matrix`, plus full RSSI/SNR matrices.
- **Degree range observed (VERIFIED): `min_degree` spans 0.0 → 20.0.** **A `min_degree` of 0 means at least one node was disconnected from its neighbours** — this is a genuine, exploitable per-node isolation signal.
- Secondary files: `dataset_metadata.zip` (103.4 MB, raw TXT+JSON per measurement), `data_analysis.py`, `metadata_processing.py`, `dataset.ipynb`, `topology_map.png`.

### (3) Access — **direct open download**
- Record: <https://zenodo.org/records/5527877>
- Main CSV: `https://zenodo.org/api/records/5527877/files/dataset_03052021_15092021.csv/content` (VERIFIED, HTTP 200, 561 MB)
- Readme: `https://zenodo.org/api/records/5527877/files/readme.md/content` (VERIFIED)

### (4) License — **CC-BY-4.0 (VERIFIED from Zenodo API)**, open access.

### (5) Size — **561.8 MB main CSV**; 103.4 MB metadata zip; ~0.7 MB topology map.

### (6) Time coverage — **2021-05-03 → 2021-09-15** (4.5 months), ~hourly snapshots.

### (7) Per-node/per-link vs aggregate
**Both per-node AND per-link, as a time series.** This is the standout: it provides per-node degree (including **0/disconnected**), per-link RSSI/SNR matrices, per-node temperature, and network-wide weather, **every hour for 4.5 months**. That is a real link-availability time series — a node whose degree hits 0 has effectively lost all links.

### (8) Judgment: **YES — the best LoRa-side trace candidate**
- **Why yes:** genuine **per-node and per-link time series with an availability proxy (degree = 0 / hop count)**, at hourly granularity over months, openly licensed and directly downloadable. Environment variables (weather, temperature) are co-recorded, which matches the "mountain/weather-driven degradation" framing.
- **Caveat to be honest about:** the degradations are **environmentally induced** (weather, temperature, humidity), **not a disaster**. There is no labelled outage event or recovery-curve annotation — you must *derive* failure episodes from degree/link-matrix thresholds. Also it is an urban Shanghai deployment, not a mountain/disaster site, and it is LoRa point-to-point (ChirpBox), not LoRaWAN.

### 5b. LoED — The LoRaWAN at the Edge Dataset ★ strongest for packet-level LoRaWAN

### (1) Name and maintainer
`LoED: The LoRaWAN at the Edge Dataset` — **Laksh Bhatia, Michael Breza, Ramona Marfievici, Julie A. McCann** (Imperial College London / Digital Catapult). Published at ACM DATA '20.
- **DOI `10.5281/zenodo.4048255`** — <https://zenodo.org/records/4048255>
- Paper PDF: <https://dl.acm.org/doi/epdf/10.1145/3419016.3431491> (also arXiv <https://arxiv.org/abs/2010.14211>, HTML <https://ar5iv.labs.arxiv.org/html/2010.14211>)

### (2) What it contains — **VERIFIED (README fetched; schema from the paper)**
**Nine LoRaWAN gateways in a dense urban environment (London)**, raw payload + gateway metadata.

Exact per-message fields (VERIFIED from paper text): `time` (packet reception time), `physical_payload` (raw payload), `gateway` (which gateway received it), `crc_status` (physical-layer CRC), `frequency`, `spreading_factor`, `bandwidth`, `code_rate`, `rssi`, `snr`, `device_address`, `mtype`, `fcnt` (counter).

Per-gateway inventory (VERIFIED from README table): 9 gateways, lat/lon/altitude given for each, models are Cisco Wireless Gateway for LoRaWAN, Multitech MTCDT-H5-246A-868-EU-GB, and Kerlink Wirnet Station V2.

| gateway | lat | lon | alt (m) | days | total messages |
|---|---|---|---|---|---|
| 00000f0c210281c4 | 51.506900 | −0.1160894 | 25 | 19 | 1,326,687 |
| 00000f0c22433141 | 51.49120 | −0.12774 | 20 | 36 | 144,777 |
| 00000f0c210721f2 | 51.50766 | −0.0989 | 40 | 56 | 5,757,575 |
| 00000f0c224331c4 | 51.5046 | −0.11119 | 2 | 15 | 17,029 |
| 00800000a0001914 | 51.49896 | −0.17801 | 5 | 573 | 76,706 |
| 00800000a0001793 | 51.49843 | −0.17823 | 5 | 552 | 186,592 |
| 00800000a0001794 | 51.49896 | −0.17801 | 5 | 17 | 61,080 |
| 7276ff002e062804 | 51.49904 | −0.1764 | 65 | 131 | 1,201,916 |
| 0000024b0b031c97 | 51.52183 | −0.135 | 66 | 131 | 2,490,639 |

Daily CSVs named `dd_mm_yyyy.csv`.

**Honest note on `airtime`:** the task asked specifically for airtime. LoED gives `spreading_factor`, `bandwidth`, `code_rate`, and `payload` — **airtime is derivable from these** (standard LoRa airtime formula) but is **not a stored column**. ChirpBox likewise has `sf`, `channel`, `payload_len`, `tx_power` — airtime derivable, not stored. **No dataset I verified stores a raw `airtime` field.** Weather: LoED has **no** weather. ChirpBox **does** have weather.

### (3) Access — **direct open download**
- Record: <https://zenodo.org/records/4048255>
- Main archive: `https://zenodo.org/api/records/4048255/files/loed_dataset.zip/content` — **398,252,933 bytes (398 MB)** (VERIFIED via Zenodo API; note my partial range-request download could not be opened as a zip because it was truncated, which is expected for a partial fetch)
- README: `https://zenodo.org/api/records/4048255/files/README.md/content` (VERIFIED, fetched)
- Also `LoRaDatasetPaper.ipynb` (73.5 MB) and `.html` (19.7 MB).

### (4) License — **CC-BY-4.0 (VERIFIED from Zenodo API)**, open access.

### (5) Size — **398 MB** zip; also a 73.5 MB notebook and 19.7 MB HTML.

### (6) Time coverage — the paper frames it as **"nine gateways over a four month period"**, while the README's per-gateway table shows **15 to 573 days** per gateway (inconsistent units/overlap; the per-gateway `days` column is the authoritative detail). **Do not assume uniform 4 months — VERIFIED as inconsistent between sources.**

### (7) Per-node/per-link vs aggregate
**Per-message, per-gateway** — every packet received at every gateway with CRC status, RSSI, SNR, SF. This supports **deriving per-gateway/per-link reception-rate time series** (e.g. CRC-failure rate, packet loss per device per gateway per hour), including long gaps (multiday outages) from the 15–56 day gateways.

### (8) Judgment: **YES (trace-derivable), with schema caveat**
- **Why yes:** it is a **raw packet-level dataset at gateways** with the physical-layer fields needed to compute reception probability, CRC failure, and RSSI/SNR time series. **CRC status per packet is a direct corruption/loss signal.** Gateway uptime/gaps can be derived from message timestamps.
- **Caveats:** it is **urban LoRaWAN uplink only**, no weather, no disaster, and the `days` inconsistency needs reconciliation first. LoED is a great source for *deriving* per-gateway availability; it does not ship an availability label.

### 5c. `LoRa on Ice` — Antarctic sea-ice monitoring, WITH REAL LOST-PACKET FILES ★ best "disaster lifecycle" fit

### (1) Name and maintainer
`LoRa on Ice: dataset to evaluate the LoRa radio technology for sea ice research in Antarctica` — **Jan Rohde, Mara Neudert, Daniel Helms, Maximilian Betz** (**Alfred Wegener Institute / Helmholtz** context; deployment at **Neumayer III station**, Antarctica).
- **DOI `10.5281/zenodo.13693107`** — <https://zenodo.org/records/13693107>

### (2) What it contains — **VERIFIED BY DOWNLOAD + PARSE**
Downloaded `LoRa-on-Ice.zip` (3.6 MB) and extracted it. Three campaigns:

1. `2023-05-12_LoRa-Range-test-on-river` (Germany, motorboat range test): `data2023-5-12.csv` (2,301 lines), `influxdb1.csv` (1,380), `merged_data.csv` (2,301), plus `eval.py` and SNR/RSSI/success-rate plots.
2. `2023-01-01_Antarctica-drift` (**the key one**): `sensorUnit.csv` (18,601 lines, local SD-card log), `influxdb.csv` (11,712 = received), **`drift-received.csv` (11,709 lines)** and **`drift-lost.csv` (6,893 lines)**, plus `drift.m`, `haversine.m`, `radians.m`, plots.
   - Exact `drift-lost.csv` columns (VERIFIED): `TimeRTC, TimeGPS, temp, EMcond, EMinphase, voltage, EMcond_raw, EMinphase_raw, EMcontrolbyte, transmitted, received, latitude, longitude, distance, RSSI, SNR`
   - Lost packets carry `received=0` with `RSSI=NaN, SNR=NaN` — a **direct, per-packet loss record**.
   - `sensorUnit.csv` columns: `TimeRTC; TimeGPS; coordinates; temp; EMcond; EMinphase; voltage; EMcond_raw; EMinphase_raw; EMcontrolbyte; transmitted`
3. `2023-12-13_Antarctica_range-test` (snowmobile across Atka Bay): `data_rangetest.csv` (35,978 lines), `data-influxDB.csv` (220), `rangetest-received.csv` (162, header `timeRTC,timeGPS,latitude,longitude,temp,voltage,received,distance,RSSI,SNR`), `rangetest-lost.csv` (14).

### ⭐ The disaster lifecycle — **VERIFIED from the dataset's own README**
Direct quote from `readme.txt`: *"The system was deployed on December 25, 2022 and was meant to remain stationary for a month. The system stores the measured data locally and additionally sends some datasets to the station using LoRa and LoRaWAN. **On January 01, 2023 the sea ice broke away including the measurement system.** The system kept transmitting data and was recovered by helicopter on January 07, 2023. The system remained intact and the data could be evaluated after the recovery."*

**This is a genuine, documented degradation → outage → recovery sequence:**
- **Baseline/healthy:** 2022-12-25 onward, stationary on intact sea ice.
- **Disruption:** 2023-01-01, ice calves; the node drifts away with the ice, distance to the gateway grows.
- **Degradation → outage:** as distance increases, packets move from `drift-received.csv` into `drift-lost.csv` (**6,893 lost vs 11,709 received — ~37% loss**), each with GPS position and distance-to-station.
- **Recovery:** 2023-01-07 helicopter recovery; data recovered intact.

Success-rate-vs-distance and distance-vs-time plots are shipped (`graphics/package-success-rate-vs-distance.png`, `distance-to-NM3-vs-time_transmitted-and-received.png`).

### (3) Access — **direct open download, no account**
`https://zenodo.org/api/records/13693107/files/LoRa-on-Ice.zip/content` (VERIFIED, 3.6 MB, HTTP 200). Landing page <https://zenodo.org/records/13693107>.

### (4) License — **CC-BY-4.0 (VERIFIED from Zenodo API)**, open access.

### (5) Size — **3.6 MB**. Tiny and fully parseable. ~87,000 total CSV lines across all campaigns.

### (6) Time coverage — **2022-12-25 → 2023-01-07** (the drift campaign, ~2 weeks spanning the event); plus 2023-05-12 and 2023-12-13 range tests.

### (7) Per-node/per-link vs aggregate
**Per-packet, per-link.** Every transmission is individually logged with timestamp, GPS lat/lon, distance to gateway, and **explicit transmitted/received flag** with RSSI/SNR where received. Received vs **lost** are parallel files. This is a **per-link availability timeline with a causal physical driver (drift distance)** — not an aggregate map, not just sensor readings.

### (8) Judgment: **YES — best single "degradation → outage → recovery" narrative dataset found**
- **Why yes:** it is the only dataset I verified that contains (a) a **real disruption event**, (b) **explicit per-packet loss records** (not inferred), (c) **per-packet geo/distance context explaining the loss**, and (d) a **recovery endpoint**. A benchmark can replay `drift-lost.csv` / `drift-received.csv` directly as a link-quality→failure schedule.
- **Caveats:** **one node, one link** (not a multi-node network), and the disruption is a *mobility/distance* failure, not infrastructure damage. Time span is ~2 weeks, and only ~6,893 loss events. Excellent as a **validated physical failure model / single-link trace**; you would need to replicate it across nodes for a multi-node benchmark.

### 5d. `Measurements of LoRaWAN Technology in Urban Scenarios: A Data Descriptor` (bonus, verified)

- **Pavel Masek, Martin Stusek, Ekaterina Svertoka, Jan Pospisil, Radim Burget, Elena Simona Lohan** (Brno University of Technology). **DOI `10.5281/zenodo.6228358`** — <https://zenodo.org/records/6228358> — **VERIFIED via Zenodo API.**
- **License CC-BY-4.0. Open access.**
- Content: JSON records stored in CSV; per-message metadata **including a per-gateway array of reception parameters for each gateway that received the message**. Files verified: `BUT_Long-Term.csv` (26,525 B), `City_center_Long-Term.csv` (29,483 B), `exportMessages_2019 LoRaWAN_CRA_1527_original.json` (1,352,636 B), `..._with_device_position.json` (1,408,381 B), `energyJoules_consumption_per_msgSize_and_SpreadingFactor.txt` (835 B — **this is the closest thing to a real airtime/energy table I verified**), `LICENSE`.
- Coverage: "multiple hours during two days of measurements" plus long-term CSVs. Published 2022-02-22.
- **Judgment: PARTIAL** — useful for multi-gateway reception modelling and the explicit spreading-factor → energy/airtime table, but far too short a window to contain a lifecycle.

### 5e. `Joint Communication and Sensing: LoRaWAN Greenhouse Monitoring` (bonus, verified)

- **Ritesh Kumar Singh, Mohammad Hasan Rahmani, Maarten Weyn, Rafael Berkvens** (University of Antwerp). **DOI `10.5281/zenodo.5793685`** — <https://zenodo.org/records/5793685> — **VERIFIED.**
- **License CC-BY-4.0. Open access.** Files: `Greenhouse-1.xlsx` (32.05 MB), `Greenhouse-2.xlsx` (36.71 MB), `Greenhouse-1-Transformed_Data.xlsx` (2.58 MB).
- **27 sensors (AF 16-42)** with **~19,687 LoRaWAN messages per sensor** over **April–August 2020** (Belgium), and **19 sensors (AF 49-67)** with **~19,009 messages per sensor** over **July–November 2020** (Netherlands). Fields: **temperature, humidity, RSSI, and message reception time**. Both greenhouses had no LoRaWAN coverage, so dedicated gateways were installed.
- **Judgment: PARTIAL** — 5 months × ~45 sensors of **per-sensor RSSI + reception-time** series is genuinely useful for deriving per-node link-loss episodes, but there is no disruption event and no per-gateway/link breakdown (single gateway per site).

---

## 6. Landslide LoRaWAN dataset (sensor data + LoRaWAN system)

**Honest overall finding: I could not find a public landslide dataset that pairs a sensor deployment with released LoRaWAN link-layer telemetry.** What exists is either (a) sensor readings only, (b) papers describing LoRaWAN systems without a data deposit, or (c) LoRa radio datasets with no landslide context. Details:

### 6a. Rockfall/landslide LoRaWAN — Pantelleria Island (paper, **no dataset found**)
`LoRa-Based Wireless Sensors Network for Rockfall and Landslide Monitoring: A Case Study in Pantelleria Island with Portable LoRaWAN Access` — MDPI *Journal of Low Power Electronics and Applications* **12(3):47** — <https://www.mdpi.com/2079-9268/12/3/47>
- Describes a real rockfall/landslide LoRaWAN deployment with a portable LoRaWAN access point.
- **No dataset DOI or download link was found.** **UNVERIFIED whether data was released.** Judgment: **NO** as a dataset (it is a case-study paper).

### 6b. Gaolan mountain loess slope multi-parameter monitoring (sensor data, LoRaWAN linkage unconfirmed)
`Dataset of real time multi-parameter monitoring for loess slopes in Gaolan mountain, Lanzhou, China: Multi-sensor network for hydrology and geophysics` — Li, Han et al., *Data in Brief* (2025), ScienceDirect <https://www.sciencedirect.com/science/article/pii/S2352340925006675>, DOAJ record <https://doaj.org/article/97e1658cb8634209b8d8ced62280efef>
- **Real landslide/mountain multi-sensor monitoring dataset** (hydrology + geophysics).
- **I could not confirm a working download link.** My DataCite query for `"loess slope Gaolan"` returned **0 results**, and I did not locate a Mendeley Data / Zenodo deposit. **UNVERIFIED / likely request-only or behind the journal's supplementary system.**
- Judgment: **NO (unverified access)** — and in any case it is sensor readings, not network availability.

### 6c. Nepal debris-flow / landslide boulder movement (open, but sensor-only)
`Boulder movement in two debris flow channels and a landslide in the Bhote Koshi catchment, Nepal, May to October 2019` — UK CEH catalogue <https://catalogue.ceh.ac.uk/documents/93518ac3-4ded-47fa-b260-38184c09dfc8> and <https://www.data.gov.uk/dataset/9fd69175-28de-488f-bc60-a1582cb673ea/...>
- Open, citable, 2019 field data from a landslide/debris-flow catchment.
- **Sensor/geomorphic readings only. No LoRaWAN, no network telemetry.** Judgment: **NO.**

### 6d. Other verified-but-irrelevant LoRa datasets found while searching
- `Semi-Synthetic LoRaWAN Dataset for Jamming and Battery-Depletion Attack Detection` — <https://zenodo.org/records/22044142>, CC-BY-4.0. **Explicitly semi-synthetic**; models jamming/battery-depletion (an availability disruption) but is not real disaster data. Judgment: **NO for real-trace purposes.**
- `LoRa Mesh - Outdoor Test Info` — <https://zenodo.org/records/22144241>, CC-BY-4.0, tiny topology-test text files. Judgment: **NO (too small/informal).**
- `LoRa Sensor Network Development for Air Quality Monitoring` — <https://zenodo.org/records/5946849>. No landslide/network-failure relevance. Judgment: **NO.**

### Judgment for section 6 overall: **NO**
No public landslide dataset with LoRaWAN link-layer/availability data was found. The closest structurally-analogous *real* mountain/cold-region network telemetry is **`LoRa on Ice`** (section 5c), which is a cold-region scientific sensor deployment with per-packet loss records and a documented disruption — the best available stand-in for a "mountain monitoring network under disruption."

---

## 7. Machine-readable outage traces: CRAWDAD / IEEE DataPort / Zenodo / Cloudflare Radar / BGP

I searched all requested terms: `disaster network outage trace`, `cellular outage dataset`, `network failure trace disaster`, `DTN contact trace disaster`, grassroots/community network outage data (NetCheck, BGP, Outage Observatory, Cloudflare Radar).

### 7.1 ⭐ Cloudflare Radar — **Outage Center API** (best per-network outage timeline, machine-readable)

### (1) Name and maintainer
**Cloudflare Radar — Outage Center (CROC)** and the `radar/annotations/outages` API. Maintainer: **Cloudflare, Inc.**
- App: <https://radar.cloudflare.com/outage-center>
- Docs: <https://github.com/cloudflare/cloudflare-docs/blob/production/src/content/docs/radar/investigate/outages.mdx>
- API ref: <https://developers.cloudflare.com/api/typescript/resources/radar/subresources/annotations/subresources/outages/methods/get/>
- Announcement blog: <https://blog.cloudflare.com/announcing-cloudflare-radar-outage-center/>

### (2) What it contains — **VERIFIED (docs fetched; API behaviour tested)**
Per the official docs, each outage annotation carries exactly the fields this project needs:
- `locations` (country codes), `asns` (**the autonomous system / network that experienced the disruption**), `scope` (e.g. `"Multiple cities in Florida"`), `eventType`, `startDate`, `endDate`, `linkedUrl`, and a nested `outage` object with **`outageCause`** (docs list: government-directed shutdowns, **severe weather or natural disasters**, infrastructure issues such as **cable cuts, power outages**, filtering/blocking) and **`outageType`** (`REGIONAL`, `NATIONWIDE`, `ASN`-level).
- **Real example from the official docs (VERIFIED quote):** `{"scope":"Multiple cities in Florida","startDate":"2022-09-28T19:00:00Z","endDate":"2022-11-02T00:00:00Z","locations":["US"],"outage":{"outageCause":"WEATHER","outageType":"REGIONAL"}}` — i.e. **Hurricane Ian with an explicit start and end date and a WEATHER cause**. Another doc example: Ukraine `POWER_OUTAGE`.

**This is a genuine per-network, per-region outage event with start time, end time, and cause — exactly a degradation→outage→recovery timeline record.**

- **Granularity:** space = **country + region/city, or ASN** (network operator); time = **explicit start and end timestamps** (to the hour or better in practice). Not per-cell-site, not per-link.
- **Access test (VERIFIED):** calling the endpoint **without** a token returns
  `{"success":false,"errors":[{"code":9106,"message":"Missing X-Auth-Key, X-Auth-Email or Authorization headers"}]}` — so an **API token is required**, but this is a **free Cloudflare account API token**, not a paywall.
- Documented call (from the official docs, VERIFIED):
```bash
curl "https://api.cloudflare.com/client/v4/radar/annotations/outages?limit=5&offset=0&dateRange=7d&format=json" \
  --header "Authorization: Bearer <API_TOKEN>"
```

### (3) Access
Public API + web app. **Requires a free Cloudflare API token.** No paywall, no request form, no research agreement.
**Unverified:** I did **not** confirm a bulk historical dump endpoint or how far back `dateRange` can reach. Treat historical depth as **UNVERIFIED**.

### (4) License / terms
Governed by **Cloudflare's API/website terms of service** — **not an open data license**. I found no CC-BY or public-domain dedication for Radar outage annotations. **Marked UNVERIFIED for redistribution; assume "use via API with attribution, redistribution unclear."**

### (5) Size
Annotation events are small JSON records; the app reports outages globally. Volume not precisely determined (**UNVERIFIED**), but outage events are naturally sparse — thousands, not millions.

### (6) Time coverage
Docs examples include **2022-09-28 (Hurricane Ian)** and **2022-10-25 (Ukraine)**. The Outage Center launched in 2022. **Exact earliest date UNVERIFIED.**

### (7) Per-node/per-link vs aggregate
**Per-network (ASN) and per-region event records.** Not per-node/per-link, but explicitly **per-network** — which is the closest thing to "which network went down, where, when, and why," with a cause taxonomy that includes natural disasters and power outages. It is *event-level*, not *site-level*.

### (8) Judgment: **PARTIAL-to-YES (best "outage event with cause + start/end" source; needs a token and is aggregate-level)**
- **Why strong:** it directly provides **start time, end time, cause, scope and affected network/region** for real disasters, including explicit `WEATHER` and `POWER_OUTAGE` causes. That is precisely a lifecycle event record, and it is API-machine-readable.
- **Why not a full yes:** resolution stops at ASN/region, so you cannot replay *which node* failed. Also license is proprietary-ish and history depth is unconfirmed. Best used as the **event schedule / ground-truth envelope** layered on top of a finer-grained trace.

### 7.2 ⭐ InetIntel `internet_outages` — **curated IODA outage/shutdown dataset with begin/end times**

### (1) Name and maintainer
`InetIntel/internet_outages` v0.0.1 — **Zachary S. Bischof** and the **Internet Intelligence Research Lab (InetIntel)**, Georgia Tech, accompanying the **ACM SIGCOMM '23** paper *"Destination Unreachable: Characterizing Internet Outages and Shutdowns"*.
- **DOI `10.5281/zenodo.8318021`** — <https://zenodo.org/records/8318021>
- Related repo: <https://github.com/InetIntel>

### (2) What it contains — **VERIFIED BY DOWNLOAD + PARSE**
Downloaded `internet_outages-v0.0.1.zip` (**1,243,824 bytes**, VERIFIED HTTP 200) and extracted. Main data file: `data/ioda/ioda_investigated_outages_cleaned_phase1+2.csv`.

**VERIFIED: 1,704 outage records** with these exact columns:
`ID, Begin time, End time, Country, IODA BGP visible by human, IODA AP visible by human, IODA IBR visible by human, Scope (based on granularity at which the outage appears in IODA), Region, AS, Cause, Confirmation Status, Manually verified, Grafana URLs, Notes`

**Example record (VERIFIED, real row):** `ID=61AE093F`, Begin `Wednesday, March 17, 2021, 4:40:00 PM`, End `Wednesday, March 17, 2021, 5:40:00 PM`, Country `South Sudan`, Scope `Region (Central Equitoria)`, Cause `Unknown`, Confirmation `Unconfirmed`, Manually verified `YES`, plus a working Grafana URL. Second example: Bangladesh, 2021-02-25 06:40 → 08:00, Scope `Region (Rangpur)`, `IODA AP visible = TRUE`.

**This gives per-outage begin/end timestamps, country, region, AS, and a cause field — a genuine outage/recovery timeline with a documented duration.** The bundle also ships duration CDFs, recurrence CDFs, start-time CDFs, and per-outage timeline figures (`figures/timeline_*_SY.pdf`, `timeline_*_IQ.pdf`, etc.), confirming the paper's temporal analysis.

- **Granularity:** space = **country / region / AS** (the `Scope` column tells you which granularity IODA resolved it at); time = **explicit begin + end timestamps**.

### (3) Access — **direct open download, no account**
`https://zenodo.org/api/records/8318021/files/InetIntel/internet_outages-v0.0.1.zip/content` (VERIFIED, 1.24 MB, HTTP 200). Landing page <https://zenodo.org/records/8318021>.

**Related live API (tested):** the public **IODA API** at Georgia Tech, e.g.
`https://api.ioda.inetintel.cc.gatech.edu/v2/outages/events?from=<epoch>&until=<epoch>`
- **VERIFIED partially:** the endpoint is live, validates parameters (returns HTTP 400 with a full `requestParameters` echo when params are missing), and returns a `copyright` field: *"This data is Copyright (c) 2021-2025 Georgia Tech Research Corporation. All Rights Reserved."*
- **VERIFIED PROBLEM:** queries with my `from`/`until` windows returned **HTTP 500 Internal Server Error**. **So the IODA API was not reliably returning data during this reconnaissance.** The static Zenodo CSV is the dependable artifact.
- IODA portal: <https://ioda.inetintel.cc.gatech.edu/> (HTTP 200, VERIFIED).

### (4) License
Zenodo records the license as **`other-open`** (**VERIFIED from the Zenodo API**). The bundled README is explicit that other component datasets were created by third parties (AccessNow #KeepItOn, V-dem, World Bank, CAIDA, MaxMind, APNIC, etc.) and that *"If you require specific versions of the data for replication, please contact us directly."* The live IODA API asserts **Georgia Tech copyright, all rights reserved**.
**Practical reading: the curated CSV is openly downloadable, but it is NOT a clean CC license, and the live IODA API is explicitly copyrighted. Redistribution terms are UNVERIFIED.**

### (5) Size — **1,243,824 bytes (1.24 MB)** zip; the IODA CSV is **825,955 bytes**; 1,704 rows.

### (6) Time coverage
Records include **2021** dates (verified examples: 2021-03-17, 2021-02-25) and the paper's figures cover a multi-year span. **The exact full date range was not determined — UNVERIFIED.**

### (7) Per-node/per-link vs aggregate
**Aggregate event records, at country/region/AS granularity.** Each record *is* an outage with a begin and end time (so it is a real timeline), but it is **not** per-node or per-link, and there are only ~1,700 events total.

### (8) Judgment: **PARTIAL (excellent ground-truth outage catalogue; too coarse for node/link replay)**
- **Why partial:** it is a **human-curated, verified outage/shutdown catalogue with start and end times, region, AS, and cause** — the best freely downloadable *outage event* dataset, and it is small (1.24 MB) and directly parseable. Ideal for **validating** a synthetic replay or for **sampling realistic outage durations and local start-time distributions** (the shipped CDFs are a real bonus).
- **Why not yes:** country/region/AS granularity only, no node or link topology, and the live API was erroring. Cause is often blank/`Unknown` (unlike TEMPO's explicit damage/power/transport split).

### 7.3 ⭐ BGP-based datasets — CAIDA / RIPE RIS / RouteViews / `bgp_outages`

- **`gkarop/bgp_outages`** — *"Helper scripts to download and analyse BGP data to identify network outages"*: <https://github.com/gkarop/bgp_outages> (**VERIFIED URL exists via search; I did not clone it — UNVERIFIED contents**). This is a **toolkit**, not a dataset — it pulls raw BGP data and derives outages.
- **BGP datasets from RIPE, BCNET, Route Views** (Simon Fraser University, Ljilja Trajković / `cnl` group): <https://www.sfu.ca/~ljilja/cnl/projects/BGP_datasets/> (**found via search; UNVERIFIED contents**).
- **CAIDA** prefix→AS mappings, referenced by InetIntel as <https://catalog.caida.org/dataset/routeviews_ipv4_prefix2as>.
- **Judgment: PARTIAL** — BGP archives (RIPE RIS, RouteViews) are genuinely open, long-running, and machine-readable, and **per-AS reachability timelines can be derived from them** (this is exactly how IODA/InetIntel works). But they are **raw routing data**, not outage traces: extracting an outage lifecycle requires nontrivial processing, is **per-prefix/per-AS**, and has no cause labels. **No single "Outage Observatory with per-network timelines" bulk dataset was confirmed to exist under that name — UNVERIFIED.**

### 7.4 IEEE DataPort — `WORD: Weather-Outage Resilience Dataset`
- **VERIFIED page:** <https://ieee-dataport.org/documents/word-weather-outage-resilience-dataset> — **DOI `10.21227/gbzk-kx76`**; NSF PAR record: <https://par.nsf.gov/biblio/10688561-word-weather-outage-resilience-dataset>
- Authors: Charlotte Wertz, Arslan Ahmad, Apsara Adhikari, Anamika Dubey, Ian Dobson (Washington State University / Iowa State). Funding: PSERC S110.
- **Content (VERIFIED from the page):** links historical weather to **power outage records for over 95% of U.S. counties**. Per-state folders → county sub-folders, each with `merged_eaglei_weather{county}.parquet` containing **full time series from 2015 to 2025**, plus per-county outage-event statistics and data-gap figures. Built from **EAGLE-I + NOAA**. Formats: `*.parquet` and `*.csv`.
- **Size (VERIFIED):** per-state zips — e.g. `texas.zip` **1.24 GB**, `georgia.zip` 750.58 MB, `virginia.zip` 627.91 MB, `kentucky.zip` 524.96 MB; ~50 states → **roughly 15 GB+ total**.
- **ACCESS IS PAYWALLED — VERIFIED:** the page states **"Dataset Access Information — Subscription Required. This dataset requires an IEEE DataPort Subscription to access."** The file list shows `WORD_dataset_zip LOGIN TO ACCESS DATASET FILES`. **This is a real paywall (IEEE DataPort subscription; note IEEE Society members get subscriber access).**
- **A public escape hatch exists (VERIFIED as a URL, contents unverified):** the page links a documentation README for *"data repository at <https://github.com/arslanleo/eagleiDataProcessor>"*, and the underlying inputs (EAGLE-I, NOAA) are described as open-access. I also verified a Figshare EAGLE-I mirror resolves: <https://figshare.com/articles/dataset/EAGLE-I_Power_Outage_Data/24237376> (HTTP 202). So the *raw* outage data is reachable without the subscription; the *processed* WORD product is not.
- **Granularity:** county, **hourly-to-daily time series 2015–2025**. **Per-county, not per-node.** It is **power** outage data, not communications.
- **Judgment: PARTIAL** — excellent, long, county-level **disruption-driver** time series (power failure is one of TEMPO's three explicit communication-outage causes, and Cloudflare's `POWER_OUTAGE` cause). Use it to **drive** comms outages a level above. But: **paywalled at the processed layer**, and it carries no network telemetry at all.

### 7.5 DTN contact traces (CRAWDAD) — searched, **nothing disaster-specific confirmed**
- I searched `CRAWDAD disaster network outage trace`, `DTN contact trace disaster`, and CRAWDAD LoRa traces.
- **Verified-relevant results found:** the Openaire record for **CRAWDAD `oviedo/asturies-er`** (DOI `10.21227/qg9y-n251`) — <https://netherlands.openaire.eu/search/dataset?pid=10.21227%2Fqg9y-n251> — which indexes a real, DOI-bearing contact-trace dataset associated with CRAWDAD (Asturias, Spain). I did **not** independently open the CRAWDAD landing page or its license, so its exact terms remain **UNVERIFIED**.
- **VERIFIED negative:** the CRAWDAD search results surfaced classic datasets such as `cu/rssi` (2009) and DTN methodology papers, **but no disaster-driven, per-link outage/recovery trace was confirmed.** Contact traces give *opportunistic meeting* structure, not *failure/recovery* timelines.
- **Judgment: PARTIAL at best / mostly NO** — DTN contact traces are the right *shape* (per-node, per-contact, timestamped, from mobile nodes, sometimes emergency scenarios) but they record **connectivity opportunities, not outages with a degradation phase and recovery**. `oviedo/asturies-er` is worth inspecting as a mobility/contact substrate (access terms **UNVERIFIED**).

### 7.6 Grassroots / community network outage datasets — **VERIFIED LARGELY UNSUCCESSFUL**
- **NetCheck:** the name is heavily overloaded by consumer utilities — a macOS menu-bar app, a Raspberry Pi uptime logger (`mcloughlan/netcheck`), shell scripts (<https://github.com/TristanBrotherton/netcheck>), an iPhone app, an Iranian connectivity tool (`netcheck-ir` on PyPI), and a student project. **I found no NetCheck research dataset of community-network outages. Treat "NetCheck dataset" as NOT A DATASET / UNVERIFIED.**
- **MIRA (Measuring Internet Resilience in Africa)** — ISOC/AFRINIC project measuring ccTLD and Internet resilience across African economies. Verified references: ISOC Pulse <https://pulse.internetsociety.org/en/blog/2021/05/mira-project-to-provide-overview-of-internets-resiliency-in-africa/>, AFRINIC deck <https://afrinic.net/ast/mira-en-may2021.pdf>, RIPE NCC presentation <https://www.ripe.net/media/documents/KevinChege_MIRA.pdf>. **MIRA produces resilience indices/dashboards; I did NOT verify a downloadable per-network outage timeline dataset.** Marked **UNVERIFIED**.
- **M-Lab** — genuinely open measurement platform: <https://www.measurementlab.net/data/> and <https://github.com/m-lab/website/blob/main/_pages/04-data.md>, plus COVID-19 response dashboards (<https://github.com/m-lab/website/blob/main/_posts/blog/2020-05-20-covid-19-response-dashboards.md>). M-Lab publishes **open, bulk-downloadable, disaggregated measurement data** (BigQuery + per-test archives) with a public-domain-ish/open license. **It is measurement data (throughput/latency per test), so it can show degradation during disasters, but it has no outage labels, no cause, and no per-node availability.** Judgment: **PARTIAL at best; better as an independent corroboration signal.** I did not download M-Lab archives (**licence terms UNVERIFIED here**).
- **Meta / Data for Good network coverage** — used as a DCM source and applied in World Bank / Development Data Partnership disaster notebooks (e.g. <https://datapartnership.org/turkiye-earthquake-impact/notebooks/internet-connectivity/03a-meta-internet-connectivity.html>, <https://worldbank.github.io/alternative-data-for-crisis/notebooks/physical-impact/internet-connectivity-meta.html>). These give **coverage/exposure baselines**, not outage timelines. **Access is via Data for Good partnership; UNVERIFIED.** Judgment: **NO for replay traces.**

### 7.7 Hugging Face "telecom outage" datasets — **VERIFIED AS MOSTLY SYNTHETIC (do not mistake for real traces)**
- `electricsheepafrica/africa-synth-telecom-network-event-logs-nigeria` and `THUgewu/africa-synth-telecom-network-event-logs-nigeria` — the dataset name itself says **`synth`**. License tag `gpl`/`other`. <https://huggingface.co/datasets/electricsheepafrica/africa-synth-telecom-network-event-logs-nigeria>
- `charliekal/nigerian_energy_and_utilities_outage_fault_logs` — <https://huggingface.co/datasets/charliekal/nigerian_energy_and_utilities_outage_fault_logs>, license `other`.
- `vnovaai/EMERGENCY_DISASTER_RESPONSE_V1_JSONL` — the sample rows are clearly **generated** (e.g. `"location": "Townsville-80"`, synthetic timestamps).
- **Judgment: NO for "real or trace-driven" evidence.** These are synthetic/generated and must not be presented as real outage traces. (`TelecomTS: A Multi-Modal Observability Dataset` — arXiv <https://browse-export.arxiv.org/pdf/2510.06063> — was also surfaced; not verified as real-world.)

### 7.8 The 3 most promising machine-readable outage datasets with per-network timelines
As requested, the top 3 from this section — **honestly ranked by whether they carry a real timeline**:

1. **Cloudflare Radar Outage Center API** — per-network (ASN) + per-region **start/end timestamps + cause taxonomy** (WEATHER, POWER_OUTAGE, cable cut, shutdown). Needs a free token. Best *per-network timeline* semantics. Not per-node. <https://developers.cloudflare.com/api/typescript/resources/radar/subresources/annotations/subresources/outages/methods/get/>
2. **InetIntel / IODA `internet_outages` (Zenodo 8318021)** — 1,704 **curated outage records with Begin time, End time, Country, Region, AS, Cause**, open 1.24 MB download, with duration/start-time CDFs. Best *curated, immediately parseable* timeline catalogue. Coarse granularity; the live IODA API was erroring. <https://zenodo.org/records/8318021>
3. **FEMA TEMPO `TEMPO_Communication_Impacts`** — the only one of the three that is **specifically communications infrastructure**, **cause-attributed (damage/power/transport)**, and **daily per-county**, with zero access friction. Best *communications-specific* timeline, at aggregate granularity. <https://gis.fema.gov/arcgis/rest/services/TEMPO/TEMPO/MapServer/4>

*(Runner-up: WORD/EAGLE-I power-outage time series 2015–2025 — best temporal depth by far, but paywalled and about power, not communications.)*

---

## Top candidates for a disruption-replay trace

Ranked by suitability for **replaying node/link failures into an agent benchmark**.

| # | Dataset | Lifecycle granularity | Access | License | Verdict |
|---|---|---|---|---|---|
| 1 | **LoRa on Ice** (Antarctic sea-ice drift, Zenodo 13693107) | **Per-packet, per-link.** Explicit `transmitted`/`received` flags; **6,893 lost vs 11,709 received** packets with timestamp, GPS, distance, RSSI, SNR. Real disruption on **2023-01-01** (ice calving), recovery **2023-01-07**. ~2 weeks, 1 node/1 link. | Direct open download (3.6 MB), no account: `zenodo.org/api/records/13693107/files/LoRa-on-Ice.zip/content` | **CC-BY-4.0** (verified) | **YES** — the only verified dataset with a documented real **degradation → outage → recovery** arc plus explicit per-packet loss records. Caveat: single link; scale up by replication. |
| 2 | **ChirpBox long-term LoRa** (Zenodo 5527877) | **Per-node AND per-link, hourly.** 20,913 snapshots, **21 nodes**, 2021-05-03→09-15 (4.5 mo, 2,470 hours). `node_link_matrix`, degree lists, RSSI/SNR matrices, plus **weather** (temp/wind/pressure/humidity). **`min_degree` reaches 0 → genuine node isolation.** | Direct open download (**561.8 MB** CSV): `zenodo.org/api/records/5527877/files/dataset_03052021_15092021.csv/content` | **CC-BY-4.0** (verified) | **YES** — richest real per-node/per-link time series with an availability proxy. Caveat: environmental (not disaster) degradation; you must *derive* failure episodes from degree thresholds. Urban, not mountain. |
| 3 | **FEMA TEMPO `TEMPO_Communication_Impacts`** (FEMA ArcGIS, layer 4) | **Aggregate per-county, DAILY.** 1,237 county-day rows, 6 named events (Ian, Ida, Fiona, Nicole, Karen, HurricaneA); `cell_sites_out`, `cell_sites_served`, `percentout`, and **cause split: damage / power / transport**; `populationaffected`. | Direct ArcGIS REST query, **no key**: `gis.fema.gov/arcgis/rest/services/TEMPO/TEMPO/MapServer/4/query?where=1%3D1&outFields=*&f=json` | FEMA (`copyrightText: "FEMA RGO"`); **no explicit open license found** | **PARTIAL** — best **real, communications-specific, cause-attributed** outage ground truth with zero access friction, but **county-level counts only**; no site IDs. Use as event schedule/calibration, not a node trace. |
| 4 | **Cloudflare Radar Outage Center API** | **Per-network (ASN) + per-region events with explicit `startDate`/`endDate` and `outageCause` (WEATHER, POWER_OUTAGE, …) / `outageType`.** | API; **requires free Cloudflare API token** (verified 9106 auth error without one) | Cloudflare ToS — **not an open license** (unverified for redistribution) | **PARTIAL** — best **per-network outage event timeline with cause**; resolution stops at ASN/region so no node-level replay. |
| 5 | **InetIntel / IODA `internet_outages`** (Zenodo 8318021) | **Aggregate outage events: `Begin time` + `End time` + Country + Region + AS + Cause.** **1,704 curated records.** Shipped duration/start-time/recurrence CDFs. | Direct open download (**1.24 MB**): `zenodo.org/api/records/8318021/files/InetIntel/internet_outages-v0.0.1.zip/content`. Live IODA API returned **HTTP 500** during testing. | Zenodo: **`other-open`**; IODA API asserts **Georgia Tech copyright, all rights reserved** | **PARTIAL** — great for sampling realistic outage **durations** and validation; too coarse and too few events for node/link replay. |
| 6 | **LoED — LoRaWAN at the Edge** (Zenodo 4048255) | **Per-message, per-gateway.** 9 gateways, ~11.3M messages; fields `time, crc_status, frequency, spreading_factor, bandwidth, code_rate, rssi, snr, device_address, mtype, fcnt, gateway`. Gateway `days` range **15–573**. | Direct open download (**398 MB**): `zenodo.org/api/records/4048255/files/loed_dataset.zip/content` | **CC-BY-4.0** (verified) | **YES (trace-derivable)** — raw packet-level with `crc_status` as a direct loss/corruption signal; derive per-gateway uptime from message gaps. No weather, no labelled outage; reconcile the `days` inconsistency first. |
| 7 | **Avalanche LoRa SAR** (Zenodo 13932869 + 17339095) | **Per-packet link measurements**, minutes-to-hours per test. **241,745 rows**; `timestamp, rssi, snr, depth, distance, rx_pos, polarization`; GPS in drone/max-dist files (**RSSI to −136 dBm, SNR to −15.5 dB**). March + April 2024 (Dolomites, 1870 m). | Direct open download (1.83 MB / 10.8 MB) | **CC-BY-4.0** (verified, both) | **PARTIAL** — no outage timeline, but the **best physical-layer link model** (real RSSI/SNR vs distance vs burial depth vs snow) to decide *when* a link becomes unreachable. No numeric snow-depth field (profiles are PDFs). |
| 8 | **WORD / EAGLE-I power-outage time series** (IEEE DataPort, DOI 10.21227/gbzk-kx76) | **Per-county power-outage time series, 2015–2025** (parquet per county), linked to NOAA weather; >95% of US counties. | **PAYWALLED** — IEEE DataPort subscription required (verified). Raw EAGLE-I inputs are open (Figshare mirror resolves). | IEEE DataPort subscription terms | **PARTIAL** — deep, long disruption-driver series for the **power** cause, but it is power, not communications, and the processed layer is paywalled. |
| 9 | **ITU Disaster Connectivity Map** | **Aggregate QoS grid cells** (100 km / 10 km / 1 km / 100 m), hourly & daily layers declared 2013→present, archives 2020–2022. **No node/link status, no outage events.** | **WMS only.** GetCapabilities/GetMap work; **GetFeatureInfo errors**; **WFS empty**; **no bulk download**. | GeoServer says `Fees: none`, `AccessConstraints: none`, but the portal adds a broad disclaimer and mixes **restricted third-party sources** (GSMA, Collins Bartholomew, Meta, Ookla). **No open license found.** | **NO** — no per-node/per-link data, no outage records, no usable bulk/attribute export, license-encumbered. At best a coarse geographic prior. |
| 10 | **SitkaNet** (HardwareX 2021, OSU OPEnS Lab) | **None — no dataset released.** Only an 11.9 KB supplementary docx. | Not available. Paper open via PMC; ScienceDirect is bot-walled. | N/A (no dataset) | **NO** — a hardware paper. **No communication traces, no packet-level data.** Would be fabricated to claim otherwise. |
| 11 | **Landslide LoRaWAN (Pantelleria; Gaolan loess; Nepal Bhote Koshi)** | Sensor/geomorphic readings only; LoRaWAN link telemetry **not released**; Gaolan download link **unconfirmed** (DataCite query returned 0). | Pantelleria: paper only. Gaolan: **unverified**. Nepal: open via CEH/data.gov.uk but sensor-only. | Varies; Nepal CEH open | **NO** — no public landslide dataset pairs a deployment with LoRaWAN link-layer/availability data. Use **LoRa on Ice** as the cold/mountain-sensor stand-in. |
| 12 | **Hugging Face "telecom outage" logs** (`africa-synth-telecom-network-event-logs-nigeria`, `nigerian_energy_and_utilities_outage_fault_logs`, `EMERGENCY_DISASTER_RESPONSE_V1_JSONL`) | Event logs, but **explicitly synthetic/generated**. | HF dataset pages | `gpl` / `other` | **NO** — synthetic. Do not present as real outage traces. |
| 13 | **DTN / CRAWDAD contact traces** (e.g. `oviedo/asturies-er`, DOI 10.21227/qg9y-n251); **M-Lab**; **MIRA**; **MeteoAlarm-style NetCheck** | Contact/measurement data — **no labelled outage or recovery phase**. | CRAWDAD registration; M-Lab open bulk; MIRA dashboards | Mixed / **unverified** | **NO / PARTIAL** — right shape for DTN contacts, wrong semantics for failure+recovery. **No "NetCheck" outage dataset was confirmed to exist.** |

---

## Bottom line for the benchmark

**There is no single public dataset that provides a complete per-node, per-link, cause-attributed disaster outage-and-recovery timeline with an open license.** The honest recommendation is a **two-layer composition**:

1. **Physical/link failure layer (trace-grounded):** use **`LoRa on Ice`** for the validated single-link degradation→outage→recovery arc (real per-packet losses with GPS/distance), and **ChirpBox** for multi-node, multi-link, 4.5-month hourly per-node/per-link series with a real zero-degree isolation signal. Use the **Avalanche LoRa SAR** RSSI/SNR-vs-distance-vs-depth curves to calibrate *where* a link crosses into unreachability (−136 dBm / −15.5 dB observed floor). Add **LoED** for packet-level `crc_status`-based loss at gateways.
2. **Event/ground-truth orchestration layer (aggregate, authoritative):** use **FEMA TEMPO** for daily, cause-split (damage/power/transport) county-level communications outage counts during named hurricanes, and **Cloudflare Radar** + **InetIntel/IODA** for per-network outage events with explicit start/end times and causes — to schedule and validate when the injected failures should begin, peak, and clear.

**Explicitly rule out as trace sources:** ITU DCM (aggregate QoS rasters, no bulk export, license-encumbered), SitkaNet (no dataset), landslide LoRaWAN (no link-layer data released), and all synthetic Hugging Face "telecom outage" logs.

**Two verification gaps worth chasing next:** (a) whether FCC DIRS publishes a raw per-provider bulk archive beyond FEMA's county aggregation; (b) the true historical depth of both Cloudflare Radar annotations and the IODA API (the latter returned HTTP 500 throughout this reconnaissance).
