# Low-Power Communication for Mountain Geohazard Monitoring — Software-Only Research Recon

**Scope:** what a group with **no hardware access** can do on *low-power communication for landslide/debris-flow
pre-disaster sensing nodes* in grid-poor, link-interrupted mountain regions (Tibet / Sichuan / Yunnan class
terrain), using **public datasets + simulation only**, targeting a top-tier venue.

**Date of survey:** September 2026. All URLs below were fetched during this survey; the observed HTTP status is
stated. Anything I could not confirm is explicitly marked **UNVERIFIED**.

**Method note:** Zenodo records were queried through the Zenodo REST API
(`https://zenodo.org/api/records/<id>`); GitHub/GitLab/PyPI through their APIs and `git ls-remote`; dataset
*contents* (CSV headers, zip member lists, row counts) were verified by HTTP **range requests** into the real
artifacts rather than trusting abstracts. Where the brief's premise and the artifact disagreed, the artifact wins
and I say so.

---

## Executive summary — the five things that matter most

1. **All three named Zenodo datasets exist, are live, CC-BY-4.0, and are downloadable.** ChirpBox is
   *substantially better than the brief claims* (it carries full 21×21 per-link RSSI/SNR matrices **plus** weather).
2. **But none of them is a mountain dataset.** ChirpBox is urban Shanghai at 470–490 MHz; LoED is urban London at
   EU868; LoRa on Ice is flat Antarctic sea ice. The only genuinely *alpine* LoRa datasets are the two Italian
   avalanche SAR datasets — and those are **near-field (0.6–50 m) bury-and-find experiments, not km-scale LPWAN
   links**. This gap is the single most important honest finding in this report, and it shapes the whole
   feasibility answer in Section C.
3. **`FLoRa` is not an ns-3 module.** It is an **OMNeT++/INET** framework. The ns-3 LoRaWAN module is
   `signetlabdei/lorawan`, and it currently tracks **ns-3.48** on its `develop` branch and `v0.3.7` tag — but its
   `master` branch is stale at ns-3.29. Two different codebases; do not conflate them.
4. **CRAWDAD no longer exists as an independent archive** — it moved to IEEE DataPort in summer 2022.
   `crawdad.org` is now a stub.
5. **A defensible top-venue paper is possible, but the claim has to change.** "We built a LoRaWAN link model
   validated on real mountain traces" is not supportable from public data. "We built a *replay-validated,
   terrain-aware* link-reliability model, trained and tested on real multi-month LoRa traces, and transferred it to
   High-Mountain-Asia terrain with DEM-informed path loss under an explicit domain-shift analysis" is supportable.
   Section C details the difference and the shortest defensible path.

---

# A. Open datasets usable entirely offline

## A.1 — ChirpBox long-term outdoor LoRa dataset ✅ FULLY VERIFIED (and richer than described)

| Field | Value |
|---|---|
| Exact name | *Dataset: Environmental Impact on the Long-Term Connectivity and Link Quality of an Outdoor LoRa Network* |
| DOI | `10.5281/zenodo.5527877` (concept DOI `10.5281/zenodo.4736501`) |
| Landing page | https://zenodo.org/records/5527877 (HTTP 200) |
| License | **CC-BY-4.0** (verified via Zenodo API `metadata.license`) |
| Creators | Pei Tian, Fengxu Yang, Xiaoyuan Ma, Carlo Alberto Boano, Xin Tian, Ye Liu, Jianming Wei |
| Published / modified | 2021-09-17 / 2024-07-17 |
| Total size | **673.7 MB** across 7 files |
| Deployment | **Shanghai, China (urban)**, 3 May 2021 → 15 Sept 2021 |
| Nodes | **21** (confirmed: README usage example is `id_list = list(range(21))`, and every matrix row has 21 entries) |

**Files** (all direct links verified):

| File | Size | Direct URL |
|---|---|---|
| `dataset_03052021_15092021.csv` | 561.81 MB | https://zenodo.org/api/records/5527877/files/dataset_03052021_15092021.csv/content |
| `dataset_metadata.zip` | 103.42 MB | https://zenodo.org/api/records/5527877/files/dataset_metadata.zip/content |
| `dataset.ipynb` | 7.68 MB | https://zenodo.org/api/records/5527877/files/dataset.ipynb/content |
| `topology_map.png` | 0.69 MB | https://zenodo.org/api/records/5527877/files/topology_map.png/content |
| `data_analysis.py` | 0.04 MB | https://zenodo.org/api/records/5527877/files/data_analysis.py/content |
| `metadata_processing.py` | 0.03 MB | https://zenodo.org/api/records/5527877/files/metadata_processing.py/content |
| `readme.md` | 0.01 MB | https://zenodo.org/api/records/5527877/files/readme.md/content |

**Exact CSV schema** (read from byte range 0–3000 of the real CSV, HTTP 206 — not from the abstract):

```
utc, time, sf, channel, tx_power, payload_len,
min_snr, max_snr, avg_snr, min_rssi, max_rssi, avg_rssi,
max_hop, max_hop_id, max_degree, min_degree, average_degree, average_temperature, symmetry,
node_degree_list, node_temperature_list, node_link_matrix,
max_rssi_matrix, avg_rssi_matrix, min_rssi_matrix,
max_snr_matrix, avg_snr_matrix, min_snr_matrix,
symmetry_matrix,
weather_temperature, wind_speed, wind_deg, pressure, humidity
```

**Verdict on the brief's claims — confirmed, with corrections:**

* ✅ *Per-node and per-link RSSI/SNR matrices* — **CONFIRMED and better than claimed.** There are **six** full
  21×21 matrices per record (`max/avg/min` for **both** RSSI and SNR), plus `node_link_matrix` (a per-link
  packet-reception-ratio-like percentage matrix, values like `100.0`, `95.0`, `25.0`) and `symmetry_matrix`
  (link asymmetry — directly relevant to link-interruption modelling), plus `node_degree_list`,
  `node_temperature_list` and `average_temperature`.
* ✅ *Weather* — **CONFIRMED**, on-board: `weather_temperature, wind_speed, wind_deg, pressure, humidity`.
* ✅ *~21 nodes* — **CONFIRMED** (exactly 21).
* ✅ *~4.5 months* — **CONFIRMED**: 3 May → 15 Sept 2021 ≈ 135 days ≈ 4.4 months.
* ⚠️ **Correction — it is NOT a mountain dataset.** It is the *city of Shanghai*. The brief's framing
  ("regions like Tibet where grid power is scarce") does not match this deployment. Shanghai is flat, dense urban.
* ⚠️ **Correction — radio band is 470/480/490 MHz**, i.e. the Chinese LPWAN band, not EU868/US915. Records show
  `channel = 470000 / 480000 / 490000`, `sf`, `tx_power`, `payload_len`.
* ℹ️ **It is a multi-hop LoRa network (ChirpBox)**, not pure star LoRaWAN — note the `max_hop`, `max_hop_id`,
  `max_degree` fields. This is a *feature* for mountain relay work (multi-hop is the natural answer to
  terrain-blocked links), but it means the traces are **not** LoRaWAN and cannot validate a LoRaWAN MAC claim.
* ⚠️ **Sampling cadence is not continuous.** From the metadata filenames, measurements land roughly every
  **2 hours** (e.g. `...20210817012702...`, `...20210817033302...`, `...20210817053702...`). Do not describe it as
  a continuous per-packet trace.
* ❓ **Node geo-coordinates in machine-readable form: UNVERIFIED.** `topology_map.png` is the deployment map, and
  the notebook supports `plot_type = ["topology", "using_pos0/1/2"]`, implying position data exists somewhere, but
  I could not confirm a clean machine-readable lat/lon table for the 21 nodes. **Treat "absolute node coordinates"
  as unconfirmed** — this matters, because without coordinates you cannot fit a distance-based path-loss model and
  must rely on the per-link matrices as-is.

**Usability for LoRa/LPWAN link-level modelling: HIGH — the best single asset found.** It is the only public
dataset here that gives **simultaneous, per-link, bidirectional, multi-month RSSI *and* SNR *and* PRR for a whole
21-node network with co-recorded weather**. That is exactly the input a link-reliability/replay simulator needs.
The limitation is that the *terrain* is wrong for the target application.

## A.2 — LoED "LoRaWAN at the Edge" ✅ FULLY VERIFIED (fields confirmed from the actual zip)

| Field | Value |
|---|---|
| Exact name | *LoED: The LoRaWAN at the Edge Dataset* |
| DOI | `10.5281/zenodo.4048255` (concept `10.5281/zenodo.4048254`) |
| Landing page | https://zenodo.org/records/4048255 (HTTP 200) |
| License | **CC-BY-4.0** |
| Creators | Laksh Bhatia, Michael Breza, Ramona Marfievici, Julie A. McCann (DATA '20 workshop) |
| Published / modified | 2020-09-25 / 2021-09-13 |
| Total size | 491.5 MB (`loed_dataset.zip` = 398.25 MB) |
| Direct URL | https://zenodo.org/api/records/4048255/files/loed_dataset.zip/content |

**Exact CSV schema — verified by reading the zip's central directory and inflating the first 4 KB of real daily
files** (HTTP range requests; this bypasses the README's vagueness):

```
time, device_address, physical_payload, gateway, crc_status, frequency,
spreading_factor, bandwidth, code_rate, rssi, snr, size, mtype, fcnt, fport
```

Sample row (verbatim from `loed_dataset/05_06_2020.csv`):
```
2020-06-05T00:00:11.983453Z,26012682,QIImASYAjukBZgBfFqTd3l+2XA==,0000024b0b031c97,1,868300000,7,125,4/5,-83,10,-1,010,59790,1
```

**Verdict on the brief's claims — all CONFIRMED:**

* ✅ `time, crc_status, frequency, spreading_factor, bandwidth, code_rate, rssi, snr, device address, gateway` —
  **all present**, plus `physical_payload` (base64), `size`, `mtype`, `fcnt`, `fport`.
* ✅ **9 gateways CONFIRMED**, with the README giving ID / location description / lat / lon / altitude / model /
  days / total messages / max-per-day / avg-per-day. Gateway models: Cisco Wireless Gateway for LoRaWAN,
  Multitech MTCDT-H5-246A-868-EU-GB, Kerlink Wirnet Station V2.
* ✅ **Message count CONFIRMED**: summing the README table = **11,262,001 messages** total.
* ✅ **Coverage (computed from the zip index)**: **188 daily CSV files**, date range **2019-02-08 → 2020-09-02**,
  **1.51 GB uncompressed**. Per-gateway campaign lengths differ sharply — from 15 days (indoor ground floor) to
  **573 days** (a Multitech inside a university building). Note the union of *files* spans ~19 months while
  individual gateway campaigns are shorter.
* Location: **urban London** (lat ≈ 51.49–51.52, lon ≈ −0.18 to −0.10), EU868 band, `crc_status` present.

**⚠️ CRITICAL LIMITATION for link-level modelling: there is no transmitter-side ground truth.**
LoED records **only what gateways received**. There is no record of what was transmitted, by whom, or when, from
the device side. Therefore **you cannot compute true packet delivery ratio or packet error rate per link** from
LoED alone — you can only compute *reception* statistics. The `crc_status` field lets you split CRC-valid from
CRC-invalid receptions (useful as an SNR-proxy for PHY-level modelling), but any "PDR" you report would be an
assumption, not a measurement. **ChirpBox does not have this problem** (its `node_link_matrix` is symmetric
per-link packet exchange between peers), which is a strong reason to prefer ChirpBox for link-level work and to use
LoED for *network-level / gateway-side / MAC-layer* questions.

**Usability: HIGH for gateway-side and MAC/network-layer modelling, urban EU868 only. MEDIUM for PHY link models.**
Also: the `physical_payload` field is base64 app payload — useful if you want realistic traffic/payload
distributions, and `mtype`/`fcnt`/`fport` support full MAC-layer replay.

## A.3 — LoRa on Ice ✅ VERIFIED (per-packet TX/RX with GPS, distance, RSSI, SNR)

| Field | Value |
|---|---|
| Exact name | *LoRa on Ice: dataset to evaluate the LoRa radio technology for sea ice research in Antarctica* |
| DOI | `10.5281/zenodo.13693107` |
| Landing page | https://zenodo.org/records/13693107 (HTTP 200) |
| License | **CC-BY-4.0** |
| Creators | Jan Rohde, Mara Neudert, Daniel Helms, Maximilian Betz |
| Published | 2024-09-05 |
| Size | **3.6 MB** (single `LoRa-on-Ice.zip`) — trivially small, download it whole |
| Direct URL | https://zenodo.org/api/records/13693107/files/LoRa-on-Ice.zip/content |

**Contents (verified by downloading and listing the zip):** three campaigns, each with data + MATLAB (`*.m`)
evaluation scripts + rendered PNG figures:

1. `2023-05-12_LoRa-Range-test-on-river/` — **Germany**, motorboat range test on a river, gateway on a high roof,
   ChirpStack + InfluxDB. Files: `data2023-5-12.csv`, `merged_data.csv`, `influxdb1.csv`, `eval.py`.
2. `2023-01-01_Antarctica-drift/` — **Antarctica**, drifting sensor unit near Neumayer III.
   `drift-received.csv` (**11,709 data rows**) and `drift-lost.csv`, plus `sensorUnit.csv` and `influxdb.csv`.
3. `2023-12-13_Antarctica_range-test/` — **Antarctica** range test. `data_rangetest.csv` (**35,977 data rows**),
   `rangetest-received.csv`, `rangetest-lost.csv`, `data-influxDB.csv`.

**Exact schema of the received-side file** (verbatim header from `drift-received.csv`):
```
TimeRTC, TimeGPS, temp, EMcond, EMinphase, voltage, EMcond_raw, EMinphase_raw,
EMcontrolbyte, transmitted, received, latitude, longitude, distance, RSSI, SNR
```
and the range-test device-side header (`data_rangetest_header.txt`):
```
RTC-Time, GPS-Time, coordinates, temp, EM cond, EM Inphase, voltage,
EM cond raw, EM Inphase raw, EM controlbyte, transmit status, Datarate
```

**Verdict on the brief's claim — CONFIRMED.** Per-packet **transmitted** and **received** records with **GPS
latitude/longitude, computed distance, RSSI and SNR**. The `drift-lost.csv` / `rangetest-lost.csv` files are the
key asset: they give the **missing** counterpart, so unlike LoED you *can* derive a genuine success rate vs
distance. The dataset even ships `package-success-rate-vs-distance.png` and `SNR-RSSI-vs-distance.png`.

**Physical relevance to the target problem:** genuinely extreme — a remote, cold, unpowered site with an
intermittently available link, which matches the *operational* flavour of the Tibet problem far better than the
urban datasets. But the *propagation* environment is **flat sea ice**, not mountain relief; and it is a
**single-link, point-to-point, boat/drifter campaign**, not a network. Useful as a hard, cold-climate, packet-level
ground-truth anchor; not as a terrain model. Note the transmitted/received columns are flags, and loss events are
in the separate `*-lost.csv` files — you must join on time.

## A.4 — Avalanche / snow / alpine LoRa datasets ✅ VERIFIED (two real datasets; important scope caveat)

Two genuinely alpine, snow-covered, CC-BY-4.0 LoRa datasets exist. Both are from the same Italian group at
Col de Mez in the **Dolomites at 1,870 m**. **Both are near-field search-and-rescue localization experiments,
not long-range LPWAN link studies** — read the caveat before building on them.

**(a) UAV + LoRa avalanche dataset (2025, the larger one)**

| Field | Value |
|---|---|
| Exact name | *An Experimental Dataset Using UAVs and LoRa Technology in Avalanche Scenarios* |
| DOI | `10.5281/zenodo.17339095` |
| Landing page | https://zenodo.org/records/17339095 (HTTP 200) |
| License | **CC-BY-4.0** |
| Creators | Fabio Mavilia, Davide La Rosa, Andrea Berton, Michele Girolami |
| Published | 2025-07-29 |
| Size / files | **10.79 MB**, single `dataset.zip` |
| Direct URL | https://zenodo.org/api/records/17339095/files/dataset.zip/content |

Contents: **one buried transmitter + one receiver on a drone**, at Col de Mez (Soraga, Italy), 1,870 m, across
**three campaigns (April 2024, February 2025, April 2025)** with differing snow depth/condition. Flight patterns:
compact Greek-key, perimeter-with-diagonals, zigzag, free-form over a 100 m × 100 m grid centred on the burial;
plus patterns over >50,000 m². **Fields:** `dateString, timestamp, rssi, snr, longitude, latitude, height
(a.g.l.), altitude (a.s.l.), speed, depth (burial depth), runID`, plus per-test UAV telemetry at finer resolution,
plus **snow profiles per AINEVA Model 4**.

**(b) Avalanche SAR LoRa dataset (2024)**

| Field | Value |
|---|---|
| Exact name | *An Experimental Dataset for Search and Rescue Operations in Avalanche Scenarios Based on LoRa Technology* |
| DOI | `10.5281/zenodo.13932869` |
| Landing page | https://zenodo.org/records/13932869 (HTTP 200) |
| License | **CC-BY-4.0** |
| Creators | Michele Girolami, Fabio Mavilia, Andrea Berton, Sandra Trifirò, Gaetano Marrocco, Giulio Maria Bianco |
| Published | 2024-07-16 |
| Size / files | **1.83 MB**, single `LoRa-SaR-dataset.zip` |
| Direct URL | https://zenodo.org/api/records/13932869/files/LoRa-SaR-dataset.zip/content |

Contents: **three test types** — *Cross test* (1 buried TX, 4 RX on tripod at 10 distances × 4 orientations;
distances **0.6, 1.2, 1.8, 3, 5, 10, 20, 30, 40, 50 m**), *Maximum Distance test* (receiver carried away until
signal loss, 2-minute dwell at markers), *Drone Flyover test* (121 points on a 100 m² grid). Snow: **March 2024
dry, >1 m deep; April 2024 wet, ~55 cm**. **Fields:** cross → `timestamp, rssi, snr, rx_pos, distance, depth,
polarization`; max_dist → `timestamp, rssi, snr, depth, id_marker, longitude, latitude`; plus drone test, plus
**AINEVA Model 4 snow profiles**.

**🚨 Scope caveat — read before citing:** the distances are **0.6–50 m**, and even the drone grids are **100 m**.
This is **near-field, through-snow, buried-transmitter** propagation for victim localization — a completely
different regime from a km-scale mountain LPWAN uplink. These datasets **cannot** support claims about
kilometre-scale mountain LoRa links. What they *can* legitimately support is (i) **snow/ice attenuation and
buried-antenna models** at 868 MHz, (ii) **depth- and wetness-dependent loss**, and (iii) as evidence that
seasonal snowpack is a first-order, time-varying propagation term — which is a legitimate and under-served input
to a geohazard-sensing link model, since Himalayan/Tibetan nodes are snow-covered for months.

**Other avalanche/snow/alpine LoRa datasets: NONE FOUND.** A targeted Zenodo search (`title:"LoRa"` and
snow/alpine/glacier/avalanche queries) returned only these two LoRa items; the other "avalanche"/"snow" hits are
unrelated (Catalan linguistics, oral leucoplakia, snow-physics datasets with no radio content). There is **no
public long-range alpine LoRa link-quality dataset** that I could find. Statement: **this dataset does not exist
in the public record as far as I can determine.**

## A.5 — Other public LoRa / LoRaWAN link-quality and packet-level datasets

### Strong additions found (all verified via Zenodo/GitHub APIs)

**(a) LoRa packet capture in Strasbourg, France (2020–2025) — the longest-duration option found**

| Field | Value |
|---|---|
| DOI / page | `10.5281/zenodo.20390366` — https://zenodo.org/records/20390366 (HTTP 200) |
| License | **CC-BY-4.0** |
| Creators | Fabrice Theoleyre, Guillaume Schreiner (ICube, Univ. Strasbourg) |
| Published / modified | 2026-05-26 / 2026-09-03 |
| Size | **25.5 GB**, 5 annual `tar.gz` files (2020 … 2025) + README |
| Coverage | **Oct 2020 → Aug 2025 (~5 years)** |

This is a **production-network capture over ~5 years** from **10 outdoor + 29 indoor antennas**, four gateway
types, strongest antenna an 8 dBi outdoor unit on a **73 m** rooftop, with observed range **up to 15 km**.
**Fields verified from the README's Elasticsearch mapping**: `rssi`, `snr`, `crcStatus`, `spreadingFactor`,
`frequency`, `channel`, `gatewayId`, `gatewayId_hash`, `antenna`, `time`, `timeSinceGpsEpoch`,
`frequencyDeviation`, `fineTimestampType`, `devAddr`, `devEui`, plus `dup_infos` (duplicate-reception metadata —
i.e. **which gateways heard the same packet**, giving multi-gateway reception/coverage structure).
**Practical cost:** it is delivered as Elasticsearch index dumps and the README's own procedure is to stand up an
Elasticsearch + Kibana VM/Docker via `elasticdump`. Supporting code:
https://github.com/ICube-Networks/lora-analysis. **This is the best candidate for long-horizon, multi-gateway,
large-scale link-statistics work, at the cost of a heavier ingestion pipeline.**

**(b) IoT4Cows — rural LoRaWAN telemetry, Colombia (2026) — best *rural* path-loss dataset found**

| Field | Value |
|---|---|
| DOI / page | `10.5281/zenodo.21515312` — https://zenodo.org/records/21515312 (HTTP 200) |
| License | **CC-BY-4.0** |
| Creators | Guillermo Guzman, Wilder Castellanos |
| Published | 2026-07-23 |
| Size | **28.5 MB**, 3 CSVs + README |
| Direct URL | https://zenodo.org/api/records/21515312/files/README.md/content (README); CSVs linked from the record |

**136,794 uplink messages** from **3 collar-mounted end devices** on free-grazing cattle, **150-hectare
dual-purpose farm, Guamal, Orinoquía, Colombia (3.88 N, 73.77 W)**, **single eight-channel gateway**.
Nominal config: **SF8, 125 kHz BW, CR 4/5, US915, OTAA, ADR disabled, 32-byte payload, 15 s interval**.
**Fields:** RSSI, SNR, spreading factor, bandwidth, channel frequency, frame counter, **plus GNSS position from
the payload**. The authors state the dataset was produced explicitly to support **coverage characterisation,
packet reception ratio and empirical path-loss modelling**. **This is the single most on-point dataset for
"rural, mobile, GNSS-georeferenced LoRaWAN path loss"** — and unlike LoED it has GNSS per message, so
distance-dependent loss is derivable. Terrain is grazed plains, not mountains, but it is **rural and low-density**,
which is far closer to a mountain-valley deployment than urban London or Shanghai.

**(c) Sigfox & LoRaWAN for fingerprint localization in urban and rural areas (Aernouts et al.)**

| Field | Value |
|---|---|
| DOI / page | `10.5281/zenodo.3342253` — https://zenodo.org/records/3342253 (HTTP 200) |
| License | **CC-BY-4.0**; 2019-07-19; 178.3 MB |
| Contents | `lorawan_dataset_antwerp.csv` (**130,430 LoRaWAN messages**, Antwerp city centre), `sigfox_dataset_rural.csv` (**25,638 messages**, rural between Antwerp and Ghent), `sigfox_dataset_antwerp.csv` (**14,378**), `lorawan_antwerp_2019_dataset.csv/.json.txt`, `sigfox_bs_mapping.csv` |

3-month collection, GPS-tagged devices, **RSSI per base station** for many base stations simultaneously
(a genuine multi-BS RSSI matrix). Fields include receive time, BS IDs and per-BS RSSI. **Caveat: RSSI only, no
SNR**; and it exists for *localization*, so it is spatially rich but temporally shallow. Also mirrored on Kaggle
as "LoRaWAN Antwerp 2019 dataset" (CC-BY-4.0) — the Kaggle copy is a repackaging and correctly credits the Zenodo DOI.

**(d) LoRaWAN LR-FHSS end-device current consumption measurements (2024) — energy-model ground truth**

| Field | Value |
|---|---|
| DOI / page | `10.5281/zenodo.13838241` — https://zenodo.org/records/13838241 (HTTP 200) |
| License | **CC-BY-4.0**; 2024-09-26; **784 MB**, 8 CSVs (~98 MB each) |
| Paper | Sanchez-Vital et al., *Sensors* 24(17):5770, 2024 — https://doi.org/10.3390/s24175770 |

Raw **current-consumption traces** (`ACKDR8/9/10/11.csv`, `noACKDR8/9/10/11.csv`) for an **LR1121DVK1TBKS**
end-device talking to a Kerlink iBTS Compact, on a **Keysight 14585A** power analyzer, for uplink LR-FHSS at
multiple data rates, with and without confirmation, 4-byte payload, +14 dBm. **This is real measured energy data**,
which is exactly what a "low-power" paper needs and is much scarcer than link-quality data. It is LR-FHSS rather
than legacy LoRa, so use it for the energy-budget half of a study and pair it with a LoRa airtime model.

**(e) LoRaWAN path loss, indoor office, one full year (2026)**

| Field | Value |
|---|---|
| DOI / page | `10.5281/zenodo.19089760` — https://zenodo.org/records/19089760 (HTTP 200) |
| License | **CC-BY-4.0**; 2026-03-18; **3.67 GB**, 3 CSVs |
| Paper | Obiri & Van Laerhoven, *IEEE Access* 13:83148–83170, 2025 — doi:10.1109/ACCESS.2025.3569164 |

**2.66 million time-stamped records**, **6 LoRaWAN nodes** → **1 gateway**, 1/min, **1 Oct 2023 → 30 Sept 2024
(one full year)**. Includes **RSSI, SNR, SF, plus effective signal power (ESP) and noise power (NP)**, alongside
**temperature, relative humidity, barometric pressure, PM2.5 and CO₂**. **Environment:** indoor office (Univ.
Siegen) — *not* mountain. Its value is methodological: it is the clearest public demonstration of
**environment-aware path-loss modelling with co-recorded meteorology over a full annual cycle**, and it shows how
ESP/NP are extracted. Its own framing ("environment-aware modeling", 6G) is directly transplantable to a
weather-coupled mountain link model.

**(f) Raw-IQ and satellite datasets (for PHY-layer work)**

| Dataset | DOI / page | Size | License | Note |
|---|---|---|---|---|
| **LoRaIQ** — annotated IQ samples | `10.5281/zenodo.20341802` — https://zenodo.org/records/20341802 | **71 GB** (5 files) | CC-BY-4.0 | 2026-05-20. `dataset.csv` + `sigmfs.zip` + `rrh_locations.md` + `load_and_plot_samples.py`. Real IQ with annotations → allows **software demodulation/decoding experiments entirely offline**. |
| **LoRadar** — satellite–ground LoRa raw IQ | `10.5281/zenodo.16302856` — https://zenodo.org/records/16302856 | **23 GB** (19 parts) | CC-BY-4.0 | 2025-07-22. Relevant if you consider satellite backhaul for remote mountain nodes. |

**(g) LoRaWAN traffic analysis, 4 European cities (2023)**

`10.5281/zenodo.8090619` — https://zenodo.org/records/8090619 (HTTP 200), **CC-BY-4.0**, 1.18 GB across
`csv.zip` / `log.zip` / `pcap.zip` / `png.zip`. Sniffer captures in **Liège, Graz, Vienna, Brno**, on specified
RX0/RX1 channels at 125 kHz, all SFs, with root and session keys published so payloads decode. **Caveat: it is a
sniffer capture — no RSSI/SNR** — so it is a *traffic/MAC* dataset, not a link-quality dataset.

**Smaller / lower-value items found (listed for completeness, honestly rated):**

* `10.5281/zenodo.1560654` — **LoRaWAN Measurement Campaigns in Lebanon** (2018), CC-BY-4.0, 0.18 MB.
  Indoor + outdoor, **urban and rural (Bekaa valley)**, 3 antenna heights (0.2–3 m), includes a MATLAB path-loss
  model. **Lebanon is mountainous**, so this is thematically relevant — but it is an 0.18 MB measurement table,
  not a trace, and is 8 years old.
* `10.5281/zenodo.8189235` — **LoRa in Buildings** (2023), CC-BY-4.0, **0.6 MB**. Indoor, data + heatmaps. Indoor-only.
* `10.5281/zenodo.13835721` — **LoRa signal quality and GPS positioning time series** (2024), CC-BY-4.0, **0.1 MB**.
  One small `dataset.csv`. Too small to be a primary source.
* `10.5281/zenodo.8001284` — **Lora Experiment Dataset** (2023), CC-BY-4.0, **0.01 MB**. Student coursework artifact.
* `10.5281/zenodo.22144241` — **LoRa Mesh - Outdoor Test Info** (2026), CC-BY-4.0, **~0.02 MB**, 5 plain `.txt`
  files with *no description at all*. Real but undocumented and tiny; **UNVERIFIED usefulness**.

### Kaggle (verified through the Kaggle public API)

* **The Tour Perret LoRaWAN frames dataset** — https://www.kaggle.com/datasets/campusiot/the-tour-perret-lorawan-frames-dataset —
  **421,937 LoRaWAN messages received between June 2021 and June 2023 (2 years)**, 106.2 MB, endpoints on the Tour
  Perret in **Grenoble, France** ("the tower for watching the mountains"), received by indoor and outdoor gateways
  installed by LIG Lab. License listed as **"Other (specified in description)"** → **check terms before reuse**.
  **This is a strong long-duration complement to the Strasbourg set and is far easier to ingest (plain CSV).**
* **The Helium LoRaWAN frames dataset** — https://www.kaggle.com/datasets/campusiot/the-helium-lorawan-frames-dataset —
  95,795 frames, same group, same licence caveat.
* **LoRa Field-Test P2P CAN Telemetry Dataset** — https://www.kaggle.com/datasets/rubencroall/lora-can-telemetry-dataset —
  **CC-BY-4.0**, 4.0 MB. Real packet-level point-to-point LoRa measurements across **distances 6.25 m → 100 m**,
  **SF7–SF12**, **BW 62.5/125/250/500 kHz**, **TX power 2/12/20 dBm**, with packet-loss indicators, per-config PER,
  RSSI, corrected/filtered RSSI variants, airtime, timing and **energy estimates**. Excellent for calibrating a
  **PHY/energy config sweep** offline; range is again short.
* "LoRaWAN IoT Network Performance Dataset" and "Passive LoRaWAN Traffic Dataset" (CC-BY-4.0, 0.2 MB) — exist;
  small, provenance weaker; **UNVERIFIED utility**.
* The generic Kaggle search for `lora` is dominated by **Valorant esports** datasets (LORA/LoRa substring
  collisions). Use `lorawan` as the query term.

### CRAWDAD — ⚠️ IMPORTANT STATUS CHANGE

**CRAWDAD no longer exists as an independent archive.** From the live site: *"CRAWDAD has moved to
IEEE-Dataport — The datasets in the Community Resource for Archiving Wireless Data at Dartmouth (CRAWDAD)
repository are now hosted as the CRAWDAD Collection on IEEE Dataport"*, and *"starting in summer 2022 is being
housed on IEEE DataPort."*

* `https://crawdad.org/` — HTTP 200, but is now a **stub/redirect** to IEEE DataPort; all deep paths
  (`/search/?q=`, `/all/`, `sitemap.xml`, `index.xml`) return **404**.
* **Real location:** https://ieee-dataport.org/collections/crawdad (HTTP 200).
* **No LoRa/LoRaWAN CRAWDAD dataset was found.** IEEE DataPort's search UI is JavaScript-rendered, so a
  keyword scrape of `/search?keywords=lora` returned 0 server-side links; **I could not programmatically confirm
  either the presence or the absence of a LoRa item in that collection — mark as UNVERIFIED**, but note that
  CRAWDAD is historically a WLAN/mobility archive, so a LoRa link-quality dataset there is unlikely.

### The honest summary of the dataset landscape

**There is no public, long-duration, packet-level LoRa link-quality dataset from high mountain terrain.** The
available assets split cleanly into four buckets, and a credible study must be explicit about which bucket it is
borrowing from:

| Bucket | Datasets | What it gives you | What it cannot give you |
|---|---|---|---|
| **Terrain-poor, link-rich** | ChirpBox, LoED, Strasbourg, Tour Perret | Real multi-month per-link RSSI/SNR/PRR, MAC behaviour, multi-gateway reception | Any statement about mountain/terrain propagation |
| **Terrain-rich, link-poor (near-field)** | Avalanche SAR ×2 | Snow/ice/burial attenuation vs depth and wetness at 868 MHz | km-scale mountain path loss |
| **Rural / cold / remote** | IoT4Cows, LoRa on Ice | Rural path loss w/ GNSS; cold-climate packet loss vs distance | Mountain relief, dense-network behaviour |
| **Energy / PHY** | LR-FHSS current consumption, LoRaFieldTest CAN, LoRaIQ, LoRadar | Measured energy, config-sweep PER, real IQ | Propagation over terrain |

<!-- SECTION_A678_PLACEHOLDER -->

---

# B. Simulation toolchain

## B.1 — ns-3 LoRaWAN modules

### `signetlabdei/lorawan` — the de-facto standard ns-3 LoRaWAN module ✅ VERIFIED

| Field | Value |
|---|---|
| URL | https://github.com/signetlabdei/lorawan |
| What it does | ns-3 module for LoRaWAN network simulation (LoRa PHY w/ interference & capture, LoRaWAN MAC incl. Class A, gateways, network server, ADR, energy model) |
| Language / license | C++ / **GPL-2.0** |
| Latest release | **v0.3.7, published 2026-07-15** |
| Last commit | **2026-09-07** — actively maintained |
| Popularity | 224 stars, 151 forks, 17 open issues |
| ns-3 App Store | listed as `lorawan` (page https://apps.nsnam.org/app/lorawan returns HTML 200) |

**ns-3 version compatibility — verified and slightly subtle.** The repo carries an `NS3-VERSION` file pinning the
supported ns-3 release:

* `master` branch → `release ns-3.29` ← **stale**, and its README still documents the old **`waf`** build system.
* `develop` branch and the **`v0.3.7` tag** → **`release ns-3.48`** ← **current**, with a **CMake**
  `CMakeLists.txt` (`ninja-build`, `ccache` in the documented prerequisites), i.e. the modern ns-3 build.

The official install recipe (from the develop README) checks out ns-3 to the pinned tag automatically:
```bash
git clone https://gitlab.com/nsnam/ns-3-dev.git && cd ns-3-dev &&
git clone https://github.com/signetlabdei/lorawan src/lorawan &&
tag=$(< src/lorawan/NS3-VERSION) && tag=${tag#release } && git checkout $tag -b $tag
```
**Practical instruction: use the `develop` branch (or the `v0.3.7` tag), never `master`, and note that the
`master` README's `waf` instructions are obsolete.** As of this survey the current ns-3 release is **ns-3.48**
(nsnam lists releases through ns-3.48 at https://www.nsnam.org/releases/), so module and simulator are in step.

Module source files include `lora-phy.cc`, `lora-interference-helper.cc`,
`correlated-shadowing-propagation-loss-model.cc`, `building-penetration-loss.cc`,
`class-a-end-device-lorawan-mac.cc`, `network-server.cc`, `network-controller.cc`, `adr-component.cc`,
`hex-grid-position-allocator.cc`, `lora-radio-energy-model.cc`, `lora-packet-tracker.cc` — i.e. it has a
**correlated-shadowing** propagation model, an **energy model**, and a **packet tracker**, all directly useful here.

### FLoRa — ⚠️ CORRECTION: it is **OMNeT++**, not ns-3

The brief lists FLoRa among "ns-3 LoRaWAN modules". **That is incorrect.**

| Field | Value |
|---|---|
| Official site | **https://flora.aalto.fi/** (HTTP 200) — *"A framework for LoRa simulations with **OMNeT++**"* |
| Repository | **https://github.com/florasim/flora** (HTTP 200) |
| Description | *"This is a set of modules to simulate LoRa networks"* |
| Language | C++ (OMNeT++ / **INET** framework) |
| Latest release | **v1.3.0, published 2026-05-21** — *"Updated code for INET 4.6.0"* |
| Last commit | 2026-05-20 (repo pushed 2026-09-09) — actively maintained |
| Popularity | 64 stars, 46 forks, 30 open issues |
| License | GitHub API reports **NOASSERTION / not detected** → ⚠️ **license UNVERIFIED — check the repo's own LICENSE file before use** |

Site-stated capabilities (from flora.aalto.fi): *"software framework for carrying out end-to-end simulations of
Long Range (LoRa) networks; Accurate model of LoRa physical layer (including collisions and capture effect);
Simulations with one (or more) gateways; End-to-end simulations, including accurate modeling of the backhaul
network; Statistics of energy consumption in network."* Version history: 1.0.0 (Apr 2021) → 1.1.0 (Jun 2022,
OMNeT++ 6 / INET 4.4) → 1.2.0 (Apr 2026, INET 4.5.4) → **1.3.0 (May 2026, INET 4.6.0)**.
Governing publications: Slabicki, Premsankar & Di Francesco, *"Adaptive Configuration of LoRa Networks for Dense
IoT Deployments"*, IEEE/IFIP NOMS 2018.

**Consequence:** choosing FLoRa means committing to the **OMNeT++/INET** toolchain, which is a different
ecosystem from ns-3 with no interop. Pick one and say why in the paper.

**Note:** `signetlabdei/FLoRa` **does not exist** (GitHub 404; GitLab project lookup returns
`404 Project Not Found`). Neither does `flora-lorawan/FLoRa` (404) nor `ComNets-Bremen/FLoRa` (404). Do not cite
those URLs.

### Other ns-3 LoRa/LoRaWAN extensions

* **`drakkar-lig/lora-ns3-module`** — https://github.com/drakkar-lig/lora-ns3-module (HTTP 200). "Lora module on
  ns-3", C++, **GPL-2.0**, 14 stars. **Effectively abandoned: last commit 2021-12-09** (the final commit is a
  `3.35_fix` merge), no releases. Tied to the ns-3.27/3.35 era. **Not recommended for new work** — mention only to
  justify choosing `signetlabdei/lorawan`.
* The brief's phrase *"the official ns-3 `lorawan` module"* is best read as `signetlabdei/lorawan`, which **is**
  distributed through the official ns-3 App Store. It is third-party-maintained (SignetLab/Univ. Padova) but
  App-Store-listed; there is no separate ns-3-core LoRaWAN module.

## B.2 — Standalone LoRa simulators

### LoRaSim (the original, Lancaster) — real, but frozen since 2017

| Field | Value |
|---|---|
| Official page | **https://www.lancaster.ac.uk/scc/sites/lora/lorasim.html** (HTTP 200) |
| Mirror (page says *"This website has now been moved to GitHub"*) | **https://mcbor.github.io/lorasim** (HTTP 200) |
| Download | **`lorasim-20170710.tgz` — verified HTTP 200, 112,640 bytes** |
| Language / deps | Python (SimPy), requires `matplotlib`, `simpy`, `numpy` |
| License | **CC-BY-4.0** (page links http://creativecommons.org/licenses/by/4.0/) |
| Last updated | **10 July 2017** — effectively **frozen** |
| Scripts | `loraDir.py` (single BS), `loraDirMulBs.py` (up to 24 BSs), `directionalLoraIntf.py`, `oneDirectionalLoraIntf.py` |
| Papers | Bor, Roedig, Voigt, Alonso, *"Do LoRa Low-Power Wide-Area Networks Scale?"*, MSWiM 2016; Voigt et al., *"Mitigating Inter-Network Interference in LoRa Networks"*, EWSN 2017 |

⚠️ **Python 2 era** — the page's own instructions say `mkvirtualenv -p python2 lorasim`. It models collisions and
scalability, not terrain. Treat as a **citation-worthy baseline**, not a working platform; legacy note:
`http://homepages.lancs.ac.uk/~bor1/lora/lorasim.html` is **dead (HTTP 502)**.

### "LoRaWAN-Sim" — ⚠️ NO SUCH TOOL FOUND

I could not find a simulator officially named **"LoRaWAN-Sim"**: `github.com/nicolagrazioli/LoRaWAN-Sim` → **404**,
`github.com/gabrielporto/lorawan-sim` → **404**. The name appears to be a conflation. **Report it as not found
rather than citing a guess.** The closest real, credible equivalents are below.

### LWN-Simulator (UniCT-ARSLab) — the closest thing to a maintained "LoRaWAN simulator"

| Field | Value |
|---|---|
| URL | https://github.com/UniCT-ARSLab/LWN-Simulator (HTTP 200) |
| Description | *"A LoRaWAN nodes' and network simulator that works with a real LoRaWAN environment (such as Chirpstack) and equipped with a web interface for real-time interaction"* |
| Language / license | **Go** / **MIT** |
| Latest release | **v1.0.3, 2025-01-03** |
| Last commit | 2025-02-04 |
| Popularity | 121 stars, 64 forks, 15 open issues |
| Follow-up paper | *"Enhancing LoRaWAN Simulator for Real-World Integration and Research Experimentation"* (IEEE, 2026 — https://ieeexplore.ieee.org/abstract/document/11324054, **UNVERIFIED beyond the search index**) |

Its distinguishing feature is that it can drive **real** LoRaWAN network servers (ChirpStack), which is
interesting if you ever want an emulation path — but the last commit is early 2025, so treat maintenance as
**slowing**.

### Newer entrants (2024–2026)

* **`MatthijsReyers/lora-simulator` (+ arXiv 2605.21136) — the most interesting 2026 development.**
  Repo: https://github.com/MatthijsReyers/lora-simulator (HTTP 200).
  Paper: **https://arxiv.org/abs/2605.21136** — *"LoRa and LoRaWAN simulator-cum-emulator with CAD and capture
  effect in Python"*, Matthijs Reyers, Niels Hokke, R.R. Venkatesha Prasad; **submitted 20 May 2026, revised
  11 Jun 2026** (verified from the arXiv abstract page).
  Stated design: pure Python, *"a custom asyncio-based simulation kernel, a three-phase packet delivery model that
  reproduces the capture effect, a full LoRaWAN 1.0.4 stack, and a containerized firmware system that
  cross-compiles real STM32 C firmware and redirects HAL calls into the simulator via CFFI"*, distributed as a
  Python package with **no external simulation framework or dependencies**.
  ⚠️ **License UNVERIFIED**: no `LICENSE`, `LICENSE.md`, `LICENSE.txt`, `COPYING` or `pyproject.toml` at the repo
  root (all HTTP 404), and no `lora-simulator` package on PyPI (404). **Confirm licensing before building on it.**
  Its **CAD (channel-activity-detection) + capture-effect** modelling and its *firmware-in-the-loop* trick are
  genuinely useful for an energy/LBT study.
* **`HADJAMOR/NC_LoRaSim`** — "NC-LoRaSim is a web-based, no-code simulation platform for LoRaWAN networks",
  last push **2026-03-24**, 4 stars. Very low maturity; **UNVERIFIED quality**.
* **`Rich-King395/LoRaSimPlus`** — "LoRaWAN Simulator developed based on Simpy", last push **2026-03-30**,
  3 stars. **UNVERIFIED quality.**
* Numerous `LoRaSim` forks exist on GitHub (`adwaitnd/lorasim` 28★, `AlexSartori/LoRaSim` 13★,
  `LounesMD/LoRaSIM` (MIT, 6★), `websense/lorasimulator` (GPL-3.0), `paafam/LoRaSim`, etc.) but **none is an
  authoritative continuation**; several are stale forks of the 2017 Lancaster code.

**Recommendation:** for a top-venue paper the defensible editor/reference choice is
**ns-3 + `signetlabdei/lorawan` (ns-3.48)** for network/MAC behaviour, with **`itmlogic`/ITM** supplying terrain-aware
path loss, and optionally **FLoRa/OMNeT++** as a cross-check. LoRaSim should appear only as a historical baseline.

## B.4 — Sionna / Sionna RT (NVIDIA)

| Field | Value |
|---|---|
| URL | https://github.com/NVlabs/sionna (HTTP 200) — docs https://nvlabs.github.io/sionna/ |
| What it does | Open-source library for research on communication systems: **PHY** (link-level), **SYS** (system-level), **RT** (differentiable ray tracing). RT covers radio-map computation, path solving, materials, antenna patterns/arrays. |
| Current version | **v2.1.0, released 2026-09-09** (latest GitHub release; last commit 2026-09-09) — actively maintained |
| License | **Apache-2.0** (verified from the `LICENSE` file: `SPDX-License-Identifier: Apache-2.0`, "Copyright (c) 2021-2026 NVIDIA CORPORATION") |
| Language | Python (repo metadata language is Jupyter Notebook; the library is Python) |
| Popularity | 1,597 stars, 410 forks |
| Install | `pip install sionna` / `pip install sionna-rt` / `pip install sionna-no-rt` |

**Runtimes — important 2026 change:** the README states *"Sionna PHY and Sionna SYS require **Python 3.11+** and
**PyTorch 2.9+**"*. Sionna has moved off TensorFlow onto **PyTorch**. Ubuntu 24.04 recommended.

**Does it need a GPU?** **No — CPU is supported, with an extra dependency.** The README says: *"To run Sionna RT
on CPU, **LLVM** is required by [Mitsuba]"*. GPU (CUDA) is recommended for speed (for PHY/SYS the README points to
the PyTorch CUDA/driver guide). So a hardware-free, **CPU-only** group can run Sionna RT; expect slow ray tracing,
and budget for it.

**Can it import terrain/DEM for outdoor ray tracing?** ⚠️ **Not natively — you must convert the DEM to a mesh.**
Verified evidence: Sionna RT loads scenes via `sionna.rt.load_scene(filename)` / `load_scene_from_string(...)`,
and the API docs state *"Sionna uses the simple XML-based format from **Mitsuba 3**"*. Scenes are therefore
`Mitsuba 3 XML + .obj/.ply` triangle meshes. The RT tutorial list contains *"Tutorial on Loading and Editing of
Scenes"* but **no DEM/terrain tutorial**, and I found no `terrain`/`DEM`/`elevation` import in the RT docs index.
Corroborating third-party evidence that this is a known workflow gap: a community tool
**`junglir-del/glb_to_rt`** — *"Convert glb to .xml+.ply for Sionna RT and do simulations based on real map with
terrain"* (last push 2026-08-01). **Conclusion: the standard route is DEM → triangulated mesh (.obj/.ply, e.g. via
QGIS/Blender) → Mitsuba XML → Sionna RT; there is no tested, official one-command DEM importer (mark the
"no official importer" claim as strongly indicated but not formally documented by NVIDIA).** For large mountain
AOIs this conversion is a real engineering task and a real ray-tracing cost.

**Relevance judgement:** Sionna RT is genuinely attractive for a **terrain-aware, differentiable** channel study
(it can, in principle, produce path gain over a real mountain mesh with diffraction). But for LoRa-class links at
470/868 MHz over kilometres, ray tracing is computationally heavy — ray tracing is far more natural at higher
frequencies and shorter ranges. **The pragmatic split is: use ITM/ITU-R for the km-scale terrain path loss, and
use Sionna RT on a small, carefully chosen mountain sub-area as a high-fidelity spot-check.** Also note Sionna's
RIS/ISAC emphasis is *not* what a geohazard-sensing paper needs, so cite Sionna as a tool, not as a topic.

<!-- SECTION_B356_PLACEHOLDER -->

---

# C. Feasibility judgement

**The premise:** (i) no hardware, (ii) real-data-grounded simulation is wanted, (iii) target is IEEE JSAC / TCOM /
TWC / TMC / INFOCOM / MobiCom class.

## C.1 What kind of credible paper *can* be produced from public traces + simulation only

**Not possible — be honest about this up front:**

* ❌ **A measurement/experimental paper.** "We deployed N nodes in Tibetan terrain and measured…" is unavailable.
  Any paper whose contribution is *new empirical data from the target environment* cannot be written. Reviewers
  at these venues read the abstract's first sentence; do not imply measurements you did not take.
* ❌ **A mountain-LoRa validation paper.** Because **no public long-range mountain LoRa link dataset exists**
  (Section A.5), any claim of the form "our model matches measured mountain LoRa behaviour" has **no ground truth
  to match**. Attempting it is the single fastest route to rejection.
* ❌ **A hardware/energy-measurement paper.** You can *use* the LR-FHSS current traces (A.5d), but you cannot
  claim to have characterised a new node's power draw.
* ❌ **A protocol paper whose evaluation is a real deployment.** INFOCOM/MobiCom especially expect a testbed, and
  often an **artifact-evaluation** process with runnable code; a pure simulation paper there needs an unusually
  strong theoretical or methodological core to survive.
* ⚠️ **A general "LoRa in the mountains is hard" survey.** Too thin for these venues.

**Realistically possible and defensible — five viable shapes, roughly in ascending difficulty:**

1. **Replay-calibrated link-model methodology (lowest risk).**
   Take ChirpBox (per-link RSSI/SNR/PRR matrices, weather, 4.5 months) and/or Strasbourg (5 years, multi-gateway)
   and *replay* them to build and validate a **statistical link-reliability model** that predicts per-link PRR from
   RSSI/SNR plus **time-varying environmental covariates** (temperature, humidity, pressure, wind, snow). Then
   apply that model to High-Mountain-Asia terrain where the *channel* is supplied by ITM/ITU-R over a real DEM.
   **The contribution is the method — weather-coupled, terrain-aware link reliability with rigorous replay
   validation — not the location.** This is the shortest defensible path and the one I would pick.
2. **Scheduling / energy-availability theory for intermittently connected, energy-harvesting sensing nodes.**
   A purely analytical + simulation contribution — e.g. an outage-aware, solar-budget-aware transmission policy
   whose *link* model is validated on real traces and whose *terrain* closure comes from DEM+ITM. Venues like
   TMC/TCOM/JSAC accept this shape; the theory must be genuinely non-trivial (not an MDP re-derivation), and
   baselines must be strong.
3. **Placement / relay-placement optimisation over real terrain with a validated link model.**
   "Where do you put k relays and which nodes are one-hop vs two-hop, given a DEM and a link model calibrated on
   real traces, under a solar energy budget?" ChirpBox's multi-hop fields (`max_hop`, `max_hop_id`, `node_degree`)
   give real multi-hop topology statistics to sanity-check against.
4. **A rigorous domain-shift / generalisation study (high risk, high reward).**
   Explicitly ask: *how well does a link model trained on urban/suburban LoRa traces transfer to mountain
   terrain?* Quantify the gap, propose terrain-conditioned correction, and be honest that it is validated by
   simulation only. This turns the field's biggest weakness (no mountain data) into the paper's *subject*. Only do
   this if you can afford for the answer to be "transfer is poor" — that is a legitimate and publishable result,
   but it is not the paper a group hoping to claim a mountain solution wants.
5. **PHY-layer contribution using the raw-IQ datasets (LoRaIQ 71 GB, LoRadar 23 GB).**
   Software-defined demodulation/decoding, detection under interference, or CAD analysis, entirely offline on real
   IQ. Fully legitimate and hardware-free — but note these are *not* mountain datasets, so the geohazard framing
   becomes decorative rather than load-bearing. Better aimed at a PHY/communications venue than a
   geohazard-motivated one.

**What makes any of these defensible at a top venue is one of two things:** either a **theoretical contribution
that stands on its own** (so the evaluation is corroboration, not proof), or a **methodological contribution with
unusually rigorous, honest validation** (replay fidelity, cross-dataset generalisation, uncertainty
quantification, ablations). Simulation-only is survivable *if the validation discipline is better than the
field's norm*. It is not survivable if the evaluation is "we ran ns-3 and our scheme is 12 % better than
ADR".

## C.2 Shortest path to a defensible result — the concrete stack

| Layer | Choice | Why this one |
|---|---|---|
| **Link ground truth** | **ChirpBox** (`10.5281/zenodo.5527877`) | Only public set with per-link, **bidirectional**, multi-month **RSSI + SNR + PRR** + weather for a whole 21-node network. Directly replayable. |
| **Scale / duration cross-check** | **Strasbourg** (`10.5281/zenodo.20390366`) and/or **Tour Perret** (Kaggle) | 5 years / 2 years, many gateways → tests whether your model holds over years and across gateway populations. Tour Perret is plain CSV (cheap); Strasbourg needs Elasticsearch (expensive). |
| **Rural/mobile path-loss anchor** | **IoT4Cows** (`10.5281/zenodo.21515312`) | Rural, GNSS per message, 136 k uplinks, explicitly built for coverage/PRR/path-loss work. |
| **Snow/seasonal attenuation term** | **Avalanche SAR sets** (`10.5281/zenodo.17339095`, `13932869`) | The only alpine snow LoRa measurements; use for a *snow-depth/wetness attenuation* sub-model with a stated range-of-validity (≤50 m, 868 MHz). |
| **Cold/remote packet-loss anchor** | **LoRa on Ice** (`10.5281/zenodo.13693107`) | Real TX/RX + loss records with GPS/distance — lets you validate a success-vs-distance curve honestly. |
| **Energy model ground truth** | **LR-FHSS current traces** (`10.5281/zenodo.13838241`) + **LoRa CAN field test PER/energy** (Kaggle) | Measured energy, not datasheet guesses. |
| **Terrain** | **Copernicus DEM GLO-30** and/or **SRTM 30 m**, **ALOS AW3D30** | See A.6 — free, global, machine-readable; the standard input for profile-based propagation. |
| **Path loss over terrain** | **`itmlogic`** (MIT, PyPI 1.2, active) and/or **`pyITM`** (MIT), plus **ITU-R P.1546-6 / P.2001 / P.1812** | ITM/Longley–Rice is the canonical irregular-terrain model and has working Python implementations; ITU-R gives the modern standardised alternatives for cross-checking. |
| **Network/MAC simulation** | **ns-3.48 + `signetlabdei/lorawan` v0.3.7 (`develop`)** | Current, maintained, has interference/capture, ADR, correlated shadowing, energy model, packet tracker. |
| **Weather driver** | **ERA5 / ERA5-Land**, **GPM IMERG**, **CHIRPS** | See A.7 — supplies the real meteorological time series that makes the "environment-aware" claim honest. |
| **High-fidelity spot-check** | **Sionna RT v2.1.0** on a small mesh converted from the DEM | Differentiable ray tracing as an independent check on the ITM path loss — optional but a strong reviewer signal. |

**The minimal defensible pipeline (what I would actually build):**

1. **Convert the DEM to terrain profiles** for a chosen High-Mountain-Asia AOI (Copernicus GLO-30 / SRTM 30 m).
2. **Compute terrain path loss** for candidate node–gateway geometries with `itmlogic` (ITM) and cross-check with
   ITU-R P.1546/P.2001; sanity-check a small subset with Sionna RT over a converted mesh.
3. **Calibrate the link model on real traces.** Use ChirpBox to fit RSSI/SNR→PRR and to learn how much of the
   residual variance is explained by weather covariates; validate by **held-out time windows and held-out links**
   (not random row splits — that is the classic reviewer trap in trace-based papers).
4. **Validate transfer** on IoT4Cows (rural), LoRa on Ice (cold/remote, with real loss records), and the avalanche
   sets (snow term), reporting **where the model fails**. Pre-register the failure metric.
5. **Run the network study in ns-3** (scheduling/relay placement/duty cycling) with the calibrated link model,
   under a solar energy budget, driven by real ERA5/IMERG weather for the AOI.
6. **Report uncertainty and ablations**: sensitivity to DEM source, to propagation model, to calibration dataset,
   and an explicit **domain-shift table** (trained on X, tested on Y).

**Timeline realism:** steps 1–4 are the honest bulk of the work (months); step 5 is comparatively quick once the
link model is trusted. Groups typically invert this and over-invest in ns-3.

## C.3 Honest risks

1. **🔴 Reviewers will ask for testbed validation — this is the dominant risk.** At INFOCOM and MobiCom especially,
   "simulation only" is a recognised rejection trigger, and both communities increasingly run **artifact
   evaluation** requiring runnable, reproducible code. Expect at least one reviewer to write *"the authors provide
   no experimental validation."* **Mitigations:** (a) aim the theory/systems contribution at **JSAC / TCOM / TMC**,
   where analytical work with careful simulation is more accepted than at INFOCOM/MobiCom; (b) make **replay
   validation on real traces** the headline — it is real data, and it is a stronger validation story than ns-3
   alone; (c) provide a **fully reproducible artifact** (code, seeds, exact dataset DOIs, pinned ns-3/module
   versions) — cheap to do and it defuses a lot of criticism; (d) never imply measurements you did not take.
2. **🔴 Domain mismatch between the data you have and the claim you want.** The largest technical risk is not
   methodological, it is that all the good link data is urban/flat and the target is mountain. A reviewer who
   knows the datasets will catch "we validate mountain LoRa using Shanghai urban traces" immediately.
   **Mitigation:** make the mismatch an explicit, quantified part of the paper (see shape 4), and *never* let it
   be an unstated assumption.
3. **🟠 Propagation-model uncertainty is large and must be reported.** ITM, P.1546, P.2001 and P.1812 disagree by
   many dB over irregular terrain; the choice of DEM (30 m vs 90 m) changes terrain profiles; vegetation and
   snow are poorly represented in all of them. **If your conclusions flip when you swap propagation model or DEM,
   the paper is not ready.** Run that sensitivity analysis and report it as a first-class result.
4. **🟠 Data-licensing and redistribution traps.** ChirpBox, LoED, LoRa on Ice, avalanche sets, Strasbourg,
   IoT4Cows, Aernouts, LR-FHSS are **CC-BY-4.0** (attribution required — cite the DOI, fine for papers).
   ⚠️ **Two exceptions to check before you build:** the **Kaggle Tour Perret / Helium datasets are
   "Other (specified in description)"**, not CC-BY, and **FLoRa's license is not detected (NOASSERTION)**.
   Also **Copernicus DEM and SRTM have their own attribution/redistribution terms** (see A.6) that differ from
   CC-BY — do not assume all "open" data is CC-BY.
5. **🟠 Zone-appropriate radio parameters.** ChirpBox is **470–490 MHz** (China), LoED is **EU868**, IoT4Cows is
   **US915**, and the avalanche sets are **EU868**. A Tibetan deployment would use China's 470–510 MHz LPWAN
   allocations. **Frequency-dependent path loss, duty cycle and regulatory limits all differ** — mixing bands
   without saying so is a factual error a reviewer can catch. State every parameter's provenance.
6. **🟡 Sampling-density honesty.** ChirpBox is ~**2-hourly**, not continuous; LoED has **no transmitter-side
   ground truth** (so no true PDR); the avalanche sets are **≤50 m**; the sniffer/traffic datasets have **no
   RSSI/SNR**. Each of these bounds what you may claim. Put a **"dataset limitations" table** in the paper —
   reviewers reward this and it pre-empts the attack.
7. **🟡 Tool maintenance exposure.** `signetlabdei/lorawan` (GPL-2.0, v0.3.7 July 2026) is healthy but is a
   **GPL-2.0** dependency (relevant if you plan to release combined code under a permissive licence), and its
   **`master` branch is stale at ns-3.29** — pin the `v0.3.7` tag and record it. `drakkar-lig` is dead; LoRaSim is
   frozen at 2017/Python 2; the promising 2026 Python simulator has **no license file**. Pin every version and
   commit hash in your artifact.
8. **🟡 The "so what" risk for a geohazard audience.** A geoscience reviewer may ask why a communications paper
   addresses landslides at all, and a comms reviewer may find the geohazard framing ornamental. **Mitigation:**
   ground the application in a concrete, cited monitoring requirement (e.g. sampling interval and latency needed
   for rainfall-triggered debris-flow early warning) and show that your design meets it — or pick a
   communications venue and keep the geohazard framing to the motivation. Do not sit between the two.

## C.4 Bottom line

* **Go** — but reframe. The defensible paper is **"replay-validated, terrain-aware, weather-coupled link
  reliability for energy-autonomous sensing nodes, with explicit domain-shift analysis"** — validated on real
  public LoRa traces (which *is* real data) and applied to High-Mountain-Asia terrain via DEM-driven ITM/ITU-R
  propagation in ns-3.48.
* **Shortest path** is the table in C.2: ChirpBox as the calibration core, IoT4Cows + LoRa on Ice + the avalanche
  sets as independent validation, `itmlogic`+DEM for terrain, `signetlabdei/lorawan` on ns-3.48 for the network
  study, LR-FHSS current traces for the energy budget.
* **Biggest unavoidable gap** is the absence of any public long-duration mountain LoRa link dataset. **Design the
  paper so this gap is a stated, analysed limitation rather than a hidden assumption** — that is the difference
  between a paper that survives review and one that does not.
* **Venue advice:** JSAC/TCOM/TMC are materially more hospitable to theory+simulation than INFOCOM/MobiCom. If you
  intend INFOCOM/MobiCom, plan for artifact evaluation and consider adding a small validation dataset you collect
  later, or partner with a group that can take a single gateway to altitude for a day — **even a few days of one
  real mountain link would be the highest-value single addition to this project.**

---

## Appendix — verification log (what was actually fetched)

Every URL cited above was requested during this survey. Representative evidence:

* Zenodo API `GET /api/records/{5527877, 4048255, 13693107, 17339095, 13932869, 20390366, 21515312, 3342253,
  13838241, 19089760, 20341802, 16302856, 8090619, 8189235, 13835721, 1560654, 8001284, 22144241}` → **HTTP 200**,
  with license/creators/sizes/file URLs read from the JSON.
* ChirpBox CSV header and first data row read by **HTTP range request** (`Range: bytes=0-3000` → **HTTP 206**).
* LoED zip **central directory** read by range requests → **188 daily CSVs, 2019-02-08 → 2020-09-02**, and real CSV
  headers inflated from the archive to confirm the field list.
* LoRa on Ice zip **downloaded in full (3,597,321 bytes, HTTP 200)** and members/headers/row counts read locally.
* `git ls-remote https://github.com/signetlabdei/lorawan` → branch/tag list including `v0.3.7`; `NS3-VERSION` fetched
  per branch → `release ns-3.48` (develop, v0.3.7) vs `release ns-3.29` (master).
* GitHub API repo/release/commit metadata for `signetlabdei/lorawan`, `florasim/flora`, `NVlabs/sionna`,
  `NTIA/itm`, `edwardoughton/itmlogic`, `tmd224/pyitm`, `drakkar-lig/lora-ns3-module`, `UniCT-ARSLab/LWN-Simulator`.
  *(Note: the unauthenticated GitHub API rate limit was hit mid-survey; later checks used raw content endpoints and
  `git ls-remote` instead, which are not rate-limited the same way.)*
* `itmlogic` MIT license text read from `raw.githubusercontent.com/edwardoughton/itmlogic/master/LICENSE`;
  PyPI `https://pypi.org/pypi/itmlogic/json` → version 1.2, uploaded 2025-03-17.
* ITU-R page `https://www.itu.int/rec/R-REC-P.1546/en` → **HTTP 200**, listing **P.1546-6 (08/2019), "In force"**;
  P.2001 and P.1812 pages also **HTTP 200**.
* `flora.aalto.fi` → **HTTP 200** confirming OMNeT++/INET basis and the 1.0.0→1.3.0 version history.
* `crawdad.org` → **HTTP 200** stub with the move notice; **all deep paths 404**;
  `ieee-dataport.org/collections/crawdad` → **HTTP 200**.
* Kaggle public API `GET /api/v1/datasets/list?search=...` → **HTTP 200** for the dataset inventories quoted.
* **Dead / non-existent (do not cite):** `signetlabdei/FLoRa` (GitHub 404, GitLab `404 Project Not Found`),
  `flora-lorawan/FLoRa` (404), `ComNets-Bremen/FLoRa` (404), `nicolagrazioli/LoRaWAN-Sim` and
  `gabrielporto/lorawan-sim` (404), `http://homepages.lancs.ac.uk/~bor1/lora/lorasim.html` (HTTP 502),
  PyPI `lora-simulator` (404).
