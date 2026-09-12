# Published quantitative data on failure physics of wireless links to mountain geohazard-monitoring nodes

Focus: Tibetan Plateau / high-altitude China. Compiled from documents actually fetched and read.

**Provenance convention used below**

- `[READ]` = number was read from a page/PDF I actually fetched (URL given).
- `[DERIVED]` = number is arithmetic I performed using published coefficients from a source I read; the source coefficients are quoted so the arithmetic is auditable. These are *not* published table values.
- `[SNIPPET]` = number came only from a search-engine result snippet, not a fetched page.
- `NO PUBLISHED FIGURE FOUND` = searched but found no published number.

---

## 1. Rain fade / rain attenuation (dB)

### 1.1 ITU-R P.838-3 — the governing model and its published coefficients

Source: Recommendation ITU-R P.838-3 (1992-1999-2003-2005), *Specific attenuation model for rain for use in prediction methods* — <https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.838-3-200503-I!!PDF-E.pdf> `[READ]`

- The model is a power law: **γ_R = k · R^α (dB/km)**, where R is rain rate in mm/h; k and α are frequency- and polarization-dependent (equations (1)–(3) of the Recommendation). `[READ]`
- **Table 5 "Frequency-dependent coefficients for estimating specific rain attenuation"** published values (k_H, α_H = horizontal polarization; k_V, α_V = vertical): `[READ]`

| f (GHz) | k_H | α_H | k_V | α_V |
|---|---|---|---|---|
| 1 | 0.0000259 | 0.9691 | 0.0000308 | 0.8592 |
| 2 | 0.0000847 | 1.0664 | 0.0000998 | 0.9490 |
| 4 | 0.0001071 | 1.6009 | 0.0002461 | 1.2476 |
| 6 | 0.0007056 | 1.5900 | 0.0004878 | 1.5728 |
| 10 | 0.01217 | 1.2571 | 0.01129 | 1.2156 |
| 12 | 0.02386 | 1.1825 | 0.02455 | 1.1216 |
| 18 | 0.07078 | 1.0818 | 0.07708 | 1.0025 |
| 20 | 0.09164 | 1.0568 | 0.09611 | 0.9847 |
| 30 | 0.2403 | 0.9485 | 0.2291 | 0.9129 |
| 40 | 0.4431 | 0.8673 | 0.4274 | 0.8421 |
| 50 | 0.6600 | 0.8084 | 0.6472 | 0.7871 |
| 60 | 0.8606 | 0.7656 | 0.8515 | 0.7486 |
| 80 | 1.1704 | 0.7115 | 1.1668 | 0.7021 |
| 100 | 1.3671 | 0.6815 | 1.3680 | 0.6765 |

- **Critical limitation for this report:** Table 5 **begins at 1 GHz**. P.838-3 publishes **no** k/α coefficients for 433 MHz, 470 MHz, 868 MHz or 915 MHz. Any dB/km figure quoted for a LoRa band under P.838 is therefore an extrapolation, not a published value. `[READ]`
- The Recommendation is valid over 1–1000 GHz. `[READ]`

### 1.2 Derived rain attenuation at specific rain rates `[DERIVED]`

Computed by the report author from the published P.838-3 power law γ_R = k·R^α using the Table 5 coefficients quoted above (horizontal polarization). Provided so the report has concrete magnitudes; **these are derived, not published table values.**

At **R = 50 mm/h**:
- **1 GHz (nearest published point to the LoRa bands): γ_R = 0.0000259 × 50^0.9691 = 0.0011 dB/km** — over a 10 km link ≈ 0.011 dB total. Effectively negligible.
- 10 GHz: 0.01217 × 50^1.2571 = **1.66 dB/km**
- 12 GHz (Ku-band downlink): 0.02386 × 50^1.1825 = **2.44 dB/km**
- 20 GHz (Ka-band): 0.09164 × 50^1.0568 = **5.72 dB/km**
- 30 GHz (Ka-band): 0.2403 × 50^0.9485 = **9.82 dB/km**
- 40 GHz: 0.4431 × 50^0.8673 = **13.2 dB/km**

At **R = 100 mm/h**:
- 1 GHz: 0.0000259 × 100^0.9691 = **0.0022 dB/km**
- 12 GHz: 0.02386 × 100^1.1825 = **5.53 dB/km**
- 20 GHz: 0.09164 × 100^1.0568 = **11.9 dB/km**
- 30 GHz: 0.2403 × 100^0.9485 = **19.0 dB/km**

**Implication for the report's argument:** on the published ITU-R model, rain fade is *not* a first-order failure mechanism for sub-1 GHz LPWAN links (433/470/868/915 MHz). It becomes first-order only for Ku/Ka satellite backhaul or microwave hops ≥10 GHz. This is an argument the report should make explicitly rather than attributing LoRa outages to rain.

### 1.3 ITU-R P.530 — NOT RETRIEVABLE

- Recommendation ITU-R P.530 (*Propagation data and prediction methods required for the design of terrestrial line-of-sight systems*) is the umbrella recommendation for rain fade and multipath outage on terrestrial links. **NO PUBLISHED FIGURE EXTRACTED** — the ITU PDF endpoints returned HTTP 404 for every path variant attempted: `R-REC-P.530-17-201712-I!!PDF-E.pdf`, `R-REC-P.530-17-201712-I!!PDF-A.pdf`, `R-REC-P.530-18-202109-I!!PDF-E.pdf`, `...-I!!PDF-A.pdf`, `...-I!!PDF-S.pdf`, `...-I!!PDF-C.pdf`, and `/dms_pub/itu-r/opb/rec/` variants. The landing page <https://www.itu.int/rec/R-REC-P.530-18-202109-S/en> exists but did not render its PDF link through the reader proxy. `[READ — 404s observed]`
- Note that P.838-3 (2005 vintage) *did* resolve under the same URL pattern, so this is a hosting/naming issue at ITU for the newer files, not a general connectivity failure.

### 1.4 Measured rain attenuation at LoRa bands / NB-IoT cellular bands

- **NO PUBLISHED FIGURE FOUND** for measured rain attenuation in dB at 433 MHz, 470 MHz, 868 MHz or 915 MHz.
- **NO PUBLISHED FIGURE FOUND** for measured rain attenuation in dB at NB-IoT/cellular 800/900/1800/2100 MHz bands.
- What was searched: web searches for "LoRa 433 MHz RSSI rain attenuation measurement dB experimental study"; "ITU-R P.838 specific rain attenuation coefficients table 433 MHz 868 MHz 1800 MHz dB/km". Candidate sources identified but **not readable**: `ShalulKamal 2021, "Effect of Weather Condition on LoRa IoT Communication"` at `eprints.utm.my/95469/1/...pdf` — both `http://` and `https://` fetches failed with `ERR_CONNECTION_REFUSED`; the Telkom University / Jurnal Infotel candidates were not fetched. `[READ — fetch failures observed]`

---

## 2. Wet foliage / vegetation attenuation

Source for all of §2.1–2.2: Recommendation **ITU-R P.833-10 (09/2021), *Attenuation in vegetation*** — <https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.833-10-202109-I!!PDF-E.pdf> `[READ]`

### 2.1 Published specific attenuation γ (dB/m), mixed coniferous–deciduous forest, St. Petersburg (Table 1)

Measurements over 105–2200 MHz, paths from a few hundred metres to 7 km, mean tree height 16 m. `[READ]`

| Frequency (MHz) | Polarization | γ (dB/m) | Maximum attenuation A_m (dB) |
|---|---|---|---|
| 105.9 | Horizontal | **0.04** | 9.4 |
| 466.475 | Slant | **0.12** | 18.0 |
| 949.0 | Slant | **0.17** | 26.5 |
| 1852.2 | Slant | **0.30** | 29.0 |
| 2117.5 | Slant | **0.34** | 34.1 |

Relevance: the **466.475 MHz and 949 MHz rows bracket the LoRa/ISM bands**. At ~470 MHz, 0.12 dB/m means a single 20 m depth of canopy costs ≈2.4 dB; 0.17 dB/m at ~950 MHz costs ≈3.4 dB over 20 m. Note these are *depth-dependent only up to A_m* — attenuation saturates at the maximum values in the right-hand column (18.0 dB at 466 MHz, 26.5 dB at 949 MHz) because a lower-loss path around the vegetation eventually exists. `[READ]`

### 2.2 Published wet/in-leaf vs. dry/leafless foliage figures

- **"At frequencies of the order of 1 GHz the specific attenuation through trees in leaf appears to be about 20% greater (dB/m) than for leafless trees."** `[READ]` — this is the only published in-leaf vs. leafless ratio found. It is a *leaf-on vs. leaf-off* comparison, not a *rain-soaked vs. dry* comparison.
- Seasonal variation measured in a forest near Mulhouse (France), 900–2200 MHz: **"Seasonal variations of 2 dB at 900 MHz and 8.5 dB at 2 200 MHz were observed"**; standard deviation of the measurements was **8.7 dB**. `[READ]`
- Southern England, mixed woodland, depth 200 m, **3 605 MHz: A_m = 46 dB**; "Measurements were carried out in summer and winter, but no significant seasonal variation was seen." `[READ]`
- Rio de Janeiro park (tropical trees, mean height 15 m), 900–1800 MHz: A_1 = 0.18 dB, α = 0.752 (in A_m = A_1·f^α, f in MHz). `[READ]`
- Mulhouse forest, 900–2200 MHz: A_1 = 1.15 dB, α = 0.43. `[READ]`
- St. Petersburg, 105.9–2117.5 MHz: A_1 = 1.37 dB, α = 0.42. `[READ]`
- Austria pine slant-path model fitted to measurements: **L(dB) = 0.25 · f^0.39 · d^0.25 · θ^0.05** (f in MHz, d = vegetation depth in m, θ = elevation in degrees). `[READ]`
- Below about 1 GHz, vertically polarized signals tend to experience **higher** attenuation than horizontally polarized, attributed to scattering from tree trunks. `[READ]`
- Attenuation varies due to movement of foliage in wind; the Recommendation stresses values "should be viewed as only typical" because of wide variation in species, density and **water content**. `[READ]`

### 2.3 Specifically wet (water-saturated) foliage

- **NO PUBLISHED FIGURE FOUND** for the dB increase when foliage is *wet* (rain-soaked) versus dry, at any band. P.833-10 names water content as a driver of variation but publishes no wet/dry delta. Searched: "wet foliage attenuation measurement dB per meter vegetation 900 MHz wet leaves versus dry".

### 2.4 Related, directly relevant to wet-canopy radome/antenna wetting

- Clear evidence that **liquid water on a dielectric surface** is the dominant loss (see §3): a 24 GHz wave was attenuated by a flowing water film at **≈18 dB/mm**, whereas the same dry plastic board attenuated it by only **0.2 dB**. <https://onlinepubs.trb.org/Onlinepubs/sr/sr185/185-049.pdf> `[READ]`

---

## 3. Snow and ice accumulation on antennas and radomes

Source: Suzuki, M., Kuroiwa, D., Sha, K., Tsukawaki, T., *Countermeasures Against Snow Accretion and Icing on Radomes*, Transportation Research Board / Highway Research Board SR185 — <https://onlinepubs.trb.org/Onlinepubs/sr/sr185/185-049.pdf> `[READ]`

- **24 GHz wave attenuated by a water film at approximately 18 dB/mm** of film thickness (experimental, water flowing over a 0.5 m × 0.5 m plastic board with gauze to keep the film uniform; theoretical values computed from Hippel (1961) matched). `[READ]`
- **Dry board control: only 0.2 dB attenuation.** `[READ]`
- **Wet snow ~0.33 m thick deposited on a radome surface attenuated an 11 GHz wave by 8.5 dB** — reported in the paper citing N. Takada et al., "Snow Damage at 11 GHz", NTT product report 1801, 1962. `[READ]` (This is a secondary citation; the primary NTT report was not fetched.)
- Measured natural snow deposit on a cone-type FRP radome (3.3 m diameter, 120° flair angle, elevation 85°, Yamagata University rooftop): **thickness approximately 0.2 m at the upper part**. `[READ]`
- Physical mechanism stated: "snow or rime deposited on antennas did not cause any significant trouble for the propagation of microwaves **unless accreted snow or rime contained much free water in it**"; significant loss arises when wet snow accretes or dry snow begins to melt. `[READ]`
- Deposition morphology: on a spherical radome in calm snowfall a **cylindrical deposit** formed vertically on the hemisphere; in windy snowfall snow accreted at **both the windward and lee-side** surfaces. `[READ]`
- Countermeasure energy cost (relevant to remote-node power budgets): rotating a 0.5 m spherical radome (2.14 kg) at 300 r.p.m. required **about 100 W** of DC motor power; a cone-type radome (0.8 m, 2.1 kg) at 300 r.p.m. required **about 26 W**. `[READ]`
- De-icing efficacy boundary: rotation successfully shed snow at air temperatures **above −3 °C**; rime formed by freezing of supercooled droplets at **−9 °C and wind 1.5 m/s** required brushing. `[READ]`

### Gaps in §3

- **NO PUBLISHED FIGURE FOUND** for snow/ice attenuation in dB at sub-1 GHz bands (433/470/868/915 MHz) or at any LPWAN band. The two published figures are at 11 GHz (8.5 dB) and 24 GHz (18 dB/mm).
- **NO PUBLISHED FIGURE FOUND** for documented outage/coverage statistics attributable to antenna/radome icing in mountain monitoring networks.

---

## 4. Extreme cold reducing battery capacity

### 4.1 LiFePO4 / lithium iron phosphate — datasheet-grade capacity vs. temperature

Source: **Victron Energy, Lithium Battery Smart — technical data** — <https://www.victronenergy.it/media/pg/Lithium_Battery_Smart/en/technical-data.html> `[READ]`

Published nominal capacities as a function of temperature, all models (50/100/160/180/200/330 Ah at 12.8 V, and 100/200 Ah at 25.6 V):

| Condition | Published nominal capacity (100 Ah model) | As % of 25 °C rating |
|---|---|---|
| @ 25 °C | 100 Ah | 100% |
| **@ 0 °C** | **80 Ah** | **80%** |
| **@ −20 °C** | **50 Ah** | **50%** |
| @ 25 °C, 330 Ah model | 330 Ah | 100% |
| @ 0 °C, 330 Ah model | 260 Ah | 79% |
| @ −20 °C, 330 Ah model | 160 Ah | 48% |

The same 100% / ~80% / ~50% pattern holds across every model in the published table (e.g. 200 Ah → 160 Ah @ 0 °C → 100 Ah @ −20 °C). Footnote to the table: "* Discharge current ≤1C". `[READ]`

**Charging limit (very important for solar-powered nodes):** `[READ]`
- Operating temperature — **Discharge: −20 °C to +50 °C; Charge: +5 °C to +50 °C.**
- Storage temperature: −45 °C to +70 °C.
- End-of-discharge voltage 11.2 V (12.8 V models), 22.4 V (25.6 V models).
- Capacity loss per 100 cycles at 25 °C, 100% DoD: < 1%.

Caveat on chemistry: the fetched technical-data page gives 12.8 V / 25.6 V nominal lithium and does not itself state "LiFePO4" on the page I read. Victron's product line is LiFePO4, but treat that chemistry attribution as product-family knowledge rather than a fact read from this page.

### 4.2 NMC (Li(Ni0.6Mn0.2Co0.2)O2 / graphite) — peer-reviewed capacity vs. temperature

Source: Leng, Y. et al., *Journal of The Electrochemical Society* (2017), high-energy NMC622/graphite 3.3 Ah pouch cell, ~200 Wh/kg — <http://ecec.me.psu.edu/Pubs/2017-Leng-JES.pdf> `[READ]`

Published 1C discharge capacities at temperature (against the room-temperature 1C capacity of 3.10 Ah): `[READ]`

| Temperature | 1C discharge capacity | % of room-temperature 1C capacity |
|---|---|---|
| ~23 °C (room) | 3.10 Ah | 100% |
| 40 °C | (improves slightly) | >100% |
| **0 °C** | **2.12 Ah** | **68.4%** |
| **−10 °C** | **1.35 Ah** | **43.5%** |
| **−25 °C** | **0.35 Ah** | **11.3%** |

- Stated cause: "reduced conductivity of the electrolyte through the separator and inside the thick electrodes, limited lithium solid diffusivity in the electrode material particles and significantly increased charge-transfer resistance on the electrolyte-electrode interface." `[READ]`
- **Internal resistance effect:** total cell resistance for a 1500-cycle aged cell was **~109 Ω·cm², more than three times that of a fresh cell (~30 Ω·cm²)** — and at low temperature "there is not only a significant capacity fade, but also a great power fade upon aging." `[READ]`
- **Lithium plating:** "significant lithium plating during the final stage of cycle life test occurs, leading to severe capacity fade"; Li plating "at low temperature or over-charge conditions" is named as a primary capacity-fade driver. The paper also reports that cells with thick electrodes (areal capacity ~3.1 mAh/cm²) "tend to lithium plating". `[READ]`
- Cycle life at room temperature: ~1419 cycles to ~75% capacity retention (NMC622), vs 1860 cycles for NMC111 control. `[READ]`

### 4.3 Lead-acid (VRLA/AGM gel) — datasheet-grade capacity vs. temperature

Source: Chilwee Group, model GB12-28, 12 V 28 Ah VRLA gel battery datasheet — <https://www.chilbattery.com/industrial-battery/storage-battery/gb12-28-12v-28ah-vrla-gel-battery.html> `[READ]`

**"Capacity affected by Temperature (20 hour rate)":**

| Temperature | Capacity |
|---|---|
| 40 °C (104 °F) | **102%** |
| 25 °C (77 °F) | **100%** |
| **0 °C (32 °F)** | **85%** |
| **−15 °C (5 °F)** | **65%** |

Other published values from the same datasheet: rated capacity 28 Ah at the 20-hour rate; **internal resistance of a fully charged battery at 25 °C = 9.0 mΩ**; self-discharge at 25 °C leaving **91% after 3 months, 82% after 6 months, 64% after 12 months**; float voltage 13.50–13.80 V. `[READ]`

### 4.4 Gaps in §4

- **NO PUBLISHED FIGURE FOUND** for lead-acid capacity at **−30 °C or −40 °C** (the datasheet table stops at −15 °C = 65%).
- **NO PUBLISHED FIGURE FOUND** for Li-ion/LiFePO4 capacity at **−30 °C or −40 °C** from a source I could read. Attempted: NMBU thesis `flaatten2015.pdf` (LiFePO4 discharge curves at different temperatures) — the reader proxy could not resolve the domain `nmbu.brage.unit.no`; Battery University **BU-502: Discharging at High and Low Temperatures** — direct fetch returned only a tracker image, an elfa.nl PDF mirror returned 445 bytes, and a web.archive.org attempt returned 521 bytes. `[READ — fetch failures observed]`; a search-result snippet title existed for BU-502 but no figure could be read.
- **NO PUBLISHED FIGURE FOUND** for *charging* efficiency or lithium-plating capacity loss expressed as a percentage, from a source I could read. The only hard no-charge-below-freezing datum obtained is the Victron datasheet's **charge range +5 °C to +50 °C**. `[READ]`

---

## 5. Terrain blockage / Fresnel zone obstruction

### 5.1 ITU-R P.526-13 — diffraction model and published loss figures

Source: Recommendation **ITU-R P.526-13 (11/2013), *Propagation by diffraction*** — <https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.526-13-201311-S!!PDF-E.pdf> `[READ]`

- **Single knife-edge obstacle (§4.1):** the diffraction loss is J(ν) dB, where ν is the Fresnel–Kirchhoff diffraction parameter; "Figure 9 gives, as a function of ν, the loss J(ν) (dB)." The published approximation is `J(ν) = 6.9 + 20·log10( √((ν − 0.1)² + 1) + ν − 0.1 )` dB. (Note: PDF text extraction of this formula was character-garbled in the fetched copy; the form quoted is the standard one published at P.526-13 §4.1 and is consistent with the Recommendation's own Figure 9.) `[READ]`
- **Values of J(ν) computed from that published formula** `[DERIVED]`:
  - ν = 0 (obstacle grazing the line of sight, zero Fresnel clearance): **6.0 dB**
  - ν = 1: **13.9 dB**
  - ν = 2: **19.0 dB**
  - ν = 3: **22.4 dB**
- **Thick obstacles / rounded ridges (§4.2):** the loss of an equivalent knife-edge is augmented by a correction term T(m,n) (equations (34a)/(34b)); "as R tends to zero, T(m,n) also tends to zero. Thus equation (32) reduces to knife-edge diffraction for a cylinder of zero radius." `[READ]`
- **Two obstacles (§4.3):** the Deygout-type method applies single knife-edge theory successively; the correction term L_c "is valid when **each of L₁ and L₂ exceeds about 15 dB**", so double-obstruction mountain paths with less than ~15 dB per edge fall outside the published validity range. `[READ]`
- **Over-the-horizon paths (§3.1):** "only the first term of the residue series is important. Even near or at the horizon this approximation can be used with a **maximum error around 2 dB** in most cases." `[READ]`
- **Accuracy statement (§3.1.1):** "Equation (13) is accurate to **better than 2 dB** for values of X, Y₁ and Y₂ that are constrained by [stated inequality]." `[READ]`
- **Zero-diffraction clearance (§3.2):** if the obstacle height h exceeds the required clearance h_req, "the diffraction loss for the path is **zero**"; otherwise loss is interpolated as A(dB) = [1 − h/h_req]·A_h. This gives a citable criterion for Fresnel-clearance-driven link failure. `[READ]`
- The Recommendation explicitly states that real obstacles are more complex than the idealized knife-edge or cylinder, "so that the indications provided in this Recommendation should be regarded only as an approximation", and cites the Bullington construction and a cylinder-fitting step-by-step method (Attachment 1 to Annex 1) for computing loss over multiple ridges for any terrain profile. `[READ]`

### 5.2 Documented fraction of obstructed links in mountain deployments

- **NO PUBLISHED FIGURE FOUND** for the fraction of obstructed (non-line-of-sight / Fresnel-obstructed) links in a real mountain monitoring deployment, and none specific to the Tibetan Plateau.
- Searched: "mountain wireless sensor network LoRa deployment line of sight obstruction percentage links Fresnel zone blocked field study". Identified candidate sources that publish Fresnel-zone *occupancy* metrics — "FresSim: A Coverage Simulator for LoRaWAN Based on Fresnel Zone" (<https://stc.computer.org/csdl/pds/api/csdl/proceedings/download-article/2a1SO89BCDe/pdf>), "A terrain-aware Fresnel zone simulator for LoRa link feasibility in non-Urban areas" (<https://www.sciencedirect.com/science/article/pii/S2542660526001423>), and MDPI *Sensors* 20(14):4034 (<https://www.mdpi.com/1424-8220/20/14/4034/xml>) — but no deployment statistics were extracted. `[SNIPPET]`

---

## 6. Lightning

### 6.1 Chinese AWS lightning-damage case with published flash counts

Source: 《基于云闪引起自动气象站故障分析》 ("Analysis of automatic weather station malfunction caused by cloud flash"), 《高原山地气象研究》/Plateau and Mountain Meteorology Research, 2024, DOI 10.3969/j.issn.1674-2184.2024.Z1.021 — <https://www.gysdqxyj.cn/cn/article/Y2024/IS1/133> `[READ]`

Published figures: `[READ]`

- **Anyue County, Ziyang, Sichuan, 2021: 23,675 lightning flashes total — 18,820 cloud flashes (云闪) and 4,855 ground flashes (地闪); cloud flashes were 79.5% of all flashes.** (Positive/negative breakdown of ground flashes: 1,111 positive, 3,744 negative.)
- **Within a 1 km radius of the Anyue national basic weather station, on 3 September 2021 between 01:21:11 and 01:25:05 (≈4 minutes), there were 10 cloud flashes and zero ground flashes.** Cloud flash heights ranged from **2.1 km to 12.2 km**.
- **Damage outcome: both the primary HY3000 data collector AND the backup HY3000 data collector failed to collect data.** Automatic weather station data terminated at 01:25 (the data logger updates once per minute), so the failure was attributed to the 01:24 cloud flash.
- **Direct economic loss: 3.36 万元 (33,600 CNY).**
- No burn marks from a direct strike were found on site; the article concludes the cause was **lightning-induced (inductive) overvoltage/surge coupled onto unshielded data lines**, listing four specific installation defects: (1) data-transmission and power cables run together in the same trench duct with insufficient separation; (2) duct covers missing, cables essentially bare; (3) metal ducting not bonded/earthed, no jumpers at joints; (4) data logger connected directly to the data cable with neither shielded cable nor a signal SPD surge protector.
- The article adds that station staff reported the **HY3000 data collector "had been struck and destroyed by lightning many times" (曾多次被雷电击坏)** since the site entered service. `[READ]`
- Stated qualitative risk driver: the AWS is "highly integrated, low withstand-voltage, relatively sensitive and fragile", and the observation field is "in open, unobstructed or relatively elevated terrain, the equipment isolated, long-term exposed, so the probability of being struck by lightning is extremely high" (遭受雷击几率极高). **The article publishes no damage *rate* (e.g. strikes/station-year or % of stations).** `[READ]`

### 6.2 Further documented Chinese AWS lightning-damage cases (same article, cited from Chinese literature) `[READ]`

- **2016, Chengdu Shuangliu International Airport east runway, AWS model MAWS301:** lightning damaged the AWS equipment module, the **QBR101 battery charging module**, the **QML201 data logger** and the **WS425 ultrasonic wind sensor**.
- **12 July 2008, Nanle County, Henan:** AWS data logger struck by lightning; **4 observation time slots (22:00 through 01:00) went missing**.
- **2 August 2006, Weifang, Shandong (CAWS600B AWS):** lightning caused all observation data except precipitation to be missing.
- **23 July 2005, Shangqiu, Henan:** lightning damaged **1 AWS hub, 1 EN-type wind data processor, 1 stabilized power supply, and 6 computers**; preliminary analysis attributed it to a lightning electromagnetic pulse introduced via signal lines.
- **5 June 2020, Liucheng County, Guangxi (DZZ5 AWS):** lightning caused equipment failure.

### 6.3 High-altitude station fault taxonomy (Qinghai)

Source: 罗延年, 李永顺, 马季芳 (Luo Yannian, Li Yongshun, Ma Jifang), 青海省海西州气象局, 《高海拔地区新型区域自动气象站常见故障及处理方法》 ("Common faults and treatment methods of new regional automatic weather station in high altitude areas"), 《气象水文海洋仪器》Meteorological Hydrological and Marine Instruments, 2023, 40(2): 134–136, ZTFLH P415.1+2 — <http://www.qxswhy.com/CN/Y2023/V40/I2/134> `[READ — abstract only]`

- The paper explicitly "sorts out the **frequent faults of the data acquisition system, power supply system, communication system and meteorological observation sensors** of new regional automatic weather stations" in high-altitude areas (Haixi Prefecture, Qinghai, elevation in the Delingha area). This is a citable Chinese-language source establishing the four failure domains (acquisition / power / communication / sensors) for high-altitude stations. `[READ]`
- **NO PUBLISHED FIGURE FOUND** — the accessible abstract contains no numeric fault rates or percentages; only the HTML full text (1 KB) was offered and the full PDF was not retrievable.

### 6.4 Lightning density maps for Tibet / Tibetan Plateau

- **NO PUBLISHED FIGURE FOUND** for flash density (flashes km⁻² yr⁻¹) over the Tibetan Plateau from any source I could actually read. Attempts and outcomes:
  - AGU *JGR Atmospheres*, "Lightning activities on the Tibetan Plateau as observed by the lightning imaging sensor" (doi 10.1029/2002JD003304), <https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2002JD003304> — returned **549 bytes**, no content. `[READ — failure]`
  - 《地球物理学报》Chinese Journal of Geophysics, "SPATIAL AND TEMPORAL DISTRIBUTION OF LIGHTNING ACTIVITIES OVER THE TIBETAN PLATEAU", <http://geophy.cn/en/article/id/cjg_554> — returned only the reference list, no abstract/body numbers. `[READ — partial]`
  - AMS *J. Atmos. Oceanic Technol.*, Ma Ruiyang et al. 2021, "Spatiotemporal lightning activity detected by WWLLN over the Tibetan Plateau…", <https://journals.ametsoc.org/view/journals/atot/38/3/JTECH-D-20-0080.1.xml> — returned **883 bytes**. `[READ — failure]`
  - NUIST page on the Second Tibetan Plateau Scientific Expedition volume led by Prof. Qie Xiushu, <https://cic.nuist.edu.cn/2025/0930/c3032a290665/page.htm> — returned **241 bytes**. `[READ — failure]`
- **Citable references identified but not read** (useful for the report's bibliography, no numbers claimed):
  - Qie Xiushu, Qie Kai, Wei Lei, et al. 2022, "Significantly increased lightning activity over the Tibetan Plateau and its relation to thunderstorm genesis", *Geophys. Res. Lett.* 49(16): e2022GL099894, doi 10.1029/2022GL099894.
  - Li Jinliang, Wu Xueke, Yang Jing, et al. 2020, "Lightning activity and its association with surface thermodynamics over the Tibetan Plateau", *Atmospheric Research* 245: 105118, doi 10.1016/j.atmosres.2020.105118.
  - Fan Penglei, Zheng Dong, Zhang Yijun, et al. 2018, "A performance evaluation of the World Wide Lightning Location Network (WWLLN) over the Tibetan Plateau", *J. Atmos. Oceanic Technol.* 35(4): 927–939, doi 10.1175/JTECH-D-17-0144.1.
  - Qie Xiushu, Yuan Tie, Xie Yiran, et al. 2004, "Spatial and temporal distribution of lightning activities over the Tibetan Plateau", *Chinese J. Geophysics* 47(6): 997–1002.
  - Gesangzhaxi, Yixilamu, Zhaduo 2021, "Analysis on the distribution characteristics of lightning activity in the Qinghai–Tibet Plateau", *Xizang Science and Technology* (7): 44–49, doi 10.3969/j.issn.1004-3403.2021.07.012.
  - Source of these citations (read): <https://www.iapjournals.ac.cn/dqkx/en/article/doi/10.3878/j.issn.1006-9895.2304.22217> `[READ — bibliography only]`

---

## 7. Animal damage / rodent chewing and theft / vandalism

### 7.1 Published rodent-damage figure (not China-specific)

Source: *The Atlantic*, "Squirrels Do 17% of the Damage to Fiber Optic Network", 2011 — <https://www.theatlantic.com/technology/archive/2011/08/squirrels-do-17-of-the-damage-to-fiber-optic-network/243319/> `[READ]`

- **"According to Level 3 Communications, which maintains an 84,000-mile fiber network, the cute rodents do 17 percent of the damage to their fiber optic network."** `[READ]`
- Caveat for the report: this is a US carrier's operational estimate quoted by a news outlet, covering terrestrial fiber (not wireless mountain nodes), and the underlying Level 3 blog post was not fetched — the figure is a news-media quotation of an operator statement, not a peer-reviewed measurement.

### 7.2 Gaps in §7

- **NO PUBLISHED FIGURE FOUND** for rodent/animal chewing damage rates on mountain geohazard-monitoring stations or their cables in China.
- **NO PUBLISHED FIGURE FOUND** for theft or vandalism rates on mountain monitoring stations in China (no quantitative source located or fetched).
- Searched: "rodent chewing damage fiber optic cable telecommunication outage statistics percent wildlife gnawing"; "青藏高原 自动气象站 雷击 故障 统计 通信 中断 监测站" (which returned the lightning sources in §6 rather than animal/theft data). Even the Chinese AWS fault papers located in §6.3 name "frequent faults" of acquisition/power/communication/sensors but do not, in their accessible abstracts, quantify animal damage or theft.

---

## 8. Cloud / fog and sandstorm attenuation

### 8.1 Cloud and fog — ITU-R P.840-9

Source: Recommendation **ITU-R P.840-9 (08/2023), *Attenuation due to clouds and fog*** — <https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.840-9-202308-I!!PDF-E.pdf> `[READ]`

Published model and figures: `[READ]`

- Specific attenuation within a cloud or fog: **γ_c(f, T) = K_l(f, T) · ρ_l  (dB/km)**, where **K_l is the cloud liquid water specific attenuation coefficient in (dB/km)/(g/m³)** and ρ_l is liquid water density. `[READ]`
- K_l is computed from a double-Debye dielectric permittivity model, **K_l(f,T) = 0.819·f / ( ε″(f)·(1 + η(f)²) )** in (dB/km)/(g/m³), valid for the Rayleigh approximation (droplets generally < 0.01 cm) **up to 200 GHz**. `[READ]`
- **Published liquid water densities: "The liquid water density in fog is typically about 0.05 g/m³ for medium fog (visibility of the order of 300 m) and 0.5 g/m³ for thick fog (visibility of the order of 50 m)."** `[READ]`
- **Frequency dependence note: "At frequencies of the order of 100 GHz and above, attenuation due to fog may be significant."** `[READ]`
- The Recommendation's stated applicability: attenuation due to clouds "may be a factor of importance especially for microwave systems **well above 10 GHz** or low-availability systems"; methods cover **1–200 GHz**, for Earth–space slant paths, using integrated cloud liquid water content from local data, reference profiles or digital maps. `[READ]`
- **NO PUBLISHED FIGURE FOUND** for a numeric K_l table or tabulated dB/km cloud attenuation value — the fetched copy contains the model and the two ρ_l values, but no extracted numeric K_l table.

### 8.2 Atmospheric gases (context for high-altitude dry/cold atmosphere)

Source: Recommendation **ITU-R P.676-13 (08/2022), *Attenuation by atmospheric gases and related effects*** — <https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.676-13-202208-I!!PDF-E.pdf> `[READ — model text]`

- Specific attenuation due to dry air and water vapour is computed as a sum of spectral lines: **γ = γ_o + γ_w = 0.1820·f·(N″_Oxygen(f) + N″_Water Vapour(f))  (dB/km)**. `[READ]`
- Figure 1 of the Recommendation is stated to give specific attenuation calculated from 0 to 1000 GHz at 1 GHz intervals for **pressure 1013.25 hPa, temperature 15 °C, water vapour density 7.5 g/m³ (standard) and a dry atmosphere**. `[READ]`
- Methods cover **1–1000 GHz** (Annex 1, arbitrary profiles) and **1–350 GHz** (Annex 2, approximate, from surface pressure/temperature/water-vapour density). `[READ]`
- **NO PUBLISHED NUMERIC dB/km VALUE EXTRACTED** — the fetched copy gives the model and the reference conditions but I did not extract tabulated values (Figure 1 is an image).

### 8.3 Sandstorm / dust storm attenuation

- **NO PUBLISHED FIGURE FOUND.** Searched: "dust storm sandstorm attenuation microwave signal dB measured dust storm effect on wireless link". Candidate sources identified but none read: "Dust Storm Attenuation Modeling Based on Measurements in Sudan" (`infona.pl/resource/bwmeta1.element.ieee-art-000007948717`), "Microwave and Millimeter-Wave Attenuation in Sand and Dust Storms" (`infona.pl/resource/bwmeta1.element.ieee-art-000005770171`), "Dust storms attenuation measurements at 14GHz and 21 GHz in Sudan", and a KFUPM MSc thesis referencing Alhaider and Ali's Riyadh measurements — the KFUPM PDF fetch produced no output file and was not retried within budget. `[READ — failures observed]`

### 8.4 Relevance caveat for the Tibetan Plateau

Neither P.840 nor P.676 publishes altitude-corrected values. Because both cloud/fog attenuation (∝ liquid water path) and gaseous attenuation (∝ water vapour density and pressure) scale with atmospheric water content, and Tibetan Plateau sites sit at very high altitude with low absolute humidity, applying sea-level P.840/P.676 defaults to a plateau node would over-estimate both. **NO PUBLISHED PLATEAU-SPECIFIC dB CORRECTION FOUND.**

---

## Summary table of the hard numbers obtained

| Quantity | Value | Source |
|---|---|---|
| P.838-3 k_H, α_H @ 1 GHz | 0.0000259, 0.9691 | ITU-R P.838-3 Table 5 |
| P.838-3 k_H, α_H @ 10 / 30 / 60 GHz | 0.01217/1.2571 · 0.2403/0.9485 · 0.8606/0.7656 | ITU-R P.838-3 Table 5 |
| γ_R, 1 GHz, 50 mm/h (nearest published point to LoRa bands) | 0.0011 dB/km `[DERIVED]` | from P.838-3 |
| γ_R, 30 GHz, 50 / 100 mm/h | 9.82 / 19.0 dB/km `[DERIVED]` | from P.838-3 |
| Vegetation γ @ 466 MHz / 949 MHz | 0.12 / 0.17 dB/m; A_m 18.0 / 26.5 dB | ITU-R P.833-10 Table 1 |
| In-leaf vs leafless vegetation penalty @ ~1 GHz | ~20% greater dB/m | ITU-R P.833-10 |
| Seasonal vegetation swing @ 900 / 2200 MHz | 2 dB / 8.5 dB | ITU-R P.833-10 |
| 24 GHz water film on radome | ~18 dB/mm (dry board: 0.2 dB) | TRB SR185 185-049 |
| 11 GHz, ~0.33 m wet snow on radome | 8.5 dB | TRB SR185 185-049 (citing Takada 1962) |
| Knife-edge loss J(ν) at ν = 0 / 1 / 2 / 3 | 6.0 / 13.9 / 19.0 / 22.4 dB `[DERIVED]` | ITU-R P.526-13 §4.1 |
| LiFePO4 capacity @ 0 / −20 °C | 80% / 50% of 25 °C rating | Victron Lithium Smart technical data |
| LiFePO4 permitted charge range | +5 °C to +50 °C (discharge −20 to +50) | Victron Lithium Smart technical data |
| NMC622 1C capacity @ 0 / −10 / −25 °C | 68.4% / 43.5% / 11.3% | Leng et al. 2017, JES |
| NMC622 aged-cell resistance rise | ~109 vs ~30 Ω·cm² (>3×) | Leng et al. 2017, JES |
| VRLA capacity @ 0 / −15 °C | 85% / 65% of 25 °C rating | Chilwee GB12-28 datasheet |
| Fog liquid water density | 0.05 g/m³ (300 m vis) / 0.5 g/m³ (50 m vis) | ITU-R P.840-9 |
| AWS lightning flashes, Anyue 2021 | 23,675 total; 18,820 cloud (79.5%); 4,855 ground | Plateau & Mountain Met. Res. 2024 |
| AWS cloud-flash event, 1 km radius, ~4 min | 10 cloud flashes, 0 ground; main + backup loggers destroyed; loss 3.36万元 | Plateau & Mountain Met. Res. 2024 |
| Rodent share of fiber damage | 17% | The Atlantic / Level 3 Communications |

---

## Could not verify

Explicit list of items where **no published figure was found**, with what was searched. No number has been estimated or invented for any of these.

1. **Measured rain attenuation in dB at LoRa bands (433, 470, 868, 915 MHz).** NO PUBLISHED FIGURE FOUND. Searched: "LoRa 433 MHz RSSI rain attenuation measurement dB experimental study"; "ITU-R P.838 … 433 MHz 868 MHz 1800 MHz". ITU-R P.838-3 Table 5 begins at 1 GHz and publishes no sub-1 GHz coefficients. The UTM LoRa weather paper could not be fetched (connection refused).
2. **Measured rain attenuation at NB-IoT/cellular 800/900/1800/2100 MHz.** NO PUBLISHED FIGURE FOUND. Searched the same queries; no readable source located.
3. **ITU-R P.530 rain-fade and outage-prediction figures.** NO PUBLISHED FIGURE FOUND. The PDF 404'd at every URL variant attempted; the landing page did not yield a link through the reader proxy.
4. **Wet (rain-soaked) vs. dry foliage attenuation delta.** NO PUBLISHED FIGURE FOUND. P.833-10 gives in-leaf vs. leafless (~20% at ~1 GHz) but no wet/dry delta. Searched: "wet foliage attenuation measurement dB per meter vegetation 900 MHz wet leaves versus dry".
5. **Snow/ice attenuation in dB at sub-1 GHz / LoRa bands.** NO PUBLISHED FIGURE FOUND. Only 11 GHz (8.5 dB) and 24 GHz (18 dB/mm water film) figures exist in the source read.
6. **Documented outage/coverage statistics attributable to antenna/radome icing in mountain monitoring networks.** NO PUBLISHED FIGURE FOUND.
7. **Fraction of Fresnel-obstructed links in a real mountain LPWAN/sensor deployment.** NO PUBLISHED FIGURE FOUND. Searched: "mountain wireless sensor network LoRa deployment line of sight obstruction percentage links Fresnel zone blocked field study"; candidate Fresnel-occupancy simulator papers identified but no deployment statistics extracted.
8. **Lead-acid capacity at −30 °C and −40 °C.** NO PUBLISHED FIGURE FOUND. Datasheet table read stops at −15 °C = 65%.
9. **Li-ion / LiFePO4 capacity at −30 °C and −40 °C.** NO PUBLISHED FIGURE FOUND. NMBU thesis domain unresolvable; Battery University BU-502 direct fetch, elfa.nl PDF mirror, and web.archive.org mirror all failed (288 / 445 / 521 bytes).
10. **Quantified charging-loss / lithium-plating capacity penalty as a percentage.** NO PUBLISHED FIGURE FOUND. Only the Victron datasheet's hard **+5 °C to +50 °C charge range** was obtained.
11. **Chinese lightning damage *rate* for monitoring stations** (e.g. strikes per station-year, or % of stations damaged per year, or 雷击损坏率). NO PUBLISHED FIGURE FOUND. The Chinese source read documents individual cases and flash counts but publishes no rate for stations. Searched: "监测站 雷击 损坏 率 青藏高原 闪电定位 密度 数据"; "青藏高原 自动气象站 雷击 故障 统计 通信 中断 监测站".
12. **Lightning flash-density map / numeric density for Tibet or the Tibetan Plateau (flashes km⁻² yr⁻¹).** NO PUBLISHED FIGURE FOUND. AGU (549 B), geophy.cn (reference list only), AMS JTECH (883 B), NUIST (241 B) all failed to yield content; the iapjournals page yielded only a bibliography. Citable references are listed in §6.4 without numbers.
13. **Numeric K_l table / tabulated dB/km cloud or fog attenuation.** NO PUBLISHED FIGURE FOUND in the fetched P.840-9 copy — the model and the two liquid-water-density values were obtained, but no tabulated attenuation value was extracted.
14. **Numeric gaseous attenuation values (dB/km) from ITU-R P.676-13.** NO PUBLISHED NUMERIC VALUE EXTRACTED — model, reference conditions (1013.25 hPa, 15 °C, 7.5 g/m³) and frequency ranges were obtained; Figure 1 is an image.
15. **Sandstorm / dust-storm attenuation in dB.** NO PUBLISHED FIGURE FOUND. Searched: "dust storm sandstorm attenuation microwave signal dB measured dust storm effect on wireless link". Identified Sudan 14/21 GHz measurements, "Microwave and Millimeter-Wave Attenuation in Sand and Dust Storms", and Alhaider & Ali's Riyadh work — none readable; KFUPM thesis fetch produced no output.
16. **Rodent/animal cable-chewing damage rate on mountain monitoring stations in China.** NO PUBLISHED FIGURE FOUND. The only rodent number obtained is the operator-quoted 17% squirrel share of US fiber damage (§7.1).
17. **Theft / vandalism rates on mountain monitoring stations in China.** NO PUBLISHED FIGURE FOUND — no quantitative source located at all.
18. **Any plateau-specific (high-altitude) correction to ITU-R cloud/fog or gaseous attenuation.** NO PUBLISHED FIGURE FOUND.

### Tooling limitations encountered (recorded so the gaps are not mistaken for absence of literature)

- ITU recommendation PDFs are hosted under inconsistent filenames: P.838-3 (2005), P.833-10, P.840-9 and P.676-13 resolved at the `dms_pubrec/itu-r/rec/p/R-REC-P.xxx-…-I!!PDF-E.pdf` pattern, but P.526 resolved only via the older `-S` (summary) variant, and **no P.530 URL variant resolved**.
- Several publishers (Wiley/AGU, AMS, ScienceDirect, some Chinese journal platforms, NMBU, Battery University, UTM eprints, KFUPM eprints) either blocked the reader proxy, returned near-empty stubs, or refused connections. Where a URL is given for such a source in this file, the figure was **not** obtained from it.
