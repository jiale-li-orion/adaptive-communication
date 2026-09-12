# 中国通信服务股份有限公司 (China Communications Services Corp. Ltd., "CCS" / 中通服, 0552.HK)

> 溯源说明：本文件正文引用的形如 `pol_*.md`、`gp_*.md`、`ncdc_*.md` 等小写文件名，
> 是调研时临时工作目录中的证据缓存。该目录已在整理时删除，
> 引用链与 URL 保留在正文，需要复核时按 URL 重新抓取。

## Primary sources: annual reports & policy — evidence file

**Research date:** 2026-09-12 (UTC)
**Scratch dir:** `（已清理的临时工作目录）/`
**Prepared by:** sub-agent "annual reports & policy"

Every figure, quote and page number below was read out of a file downloaded in this session.
Anything not opened is explicitly marked. Nothing is inferred or reconstructed from memory.

---

## 0. Tooling actually used (what worked / what did not)

| Tool | Status | Notes |
|---|---|---|
| `curl` direct to `chinaccs.com.hk` | **worked** | needed a browser `User-Agent`; used for HTML + all PDFs |
| `curl` direct to `gov.cn` | **FAILED** | `http=000`, 0 bytes — TLS/network block. Not retried with escalation (approval prompts disabled in this session) |
| Jina Reader (`https://r.jina.ai/<url>`) | **worked** | used for gov.cn; helper `（已清理的临时工作目录）/f.sh` |
| `python3` + **PyMuPDF (`fitz`) 6.x** | **worked** | all PDF text extraction; script `extract.py` |
| `python3` + **pypdf 6.14.2** | available, not needed | PyMuPDF sufficed |
| `pdftotext` | **NOT INSTALLED** | — |
| CCS site search (`/sc/global/search.php?q=…`) | **UNUSABLE via curl** | returns only the nav menu; result list is rendered client-side (`ir-gcs-*` = Google CSE classes). All 8 keyword queries returned an identical 83-link nav payload ⇒ **no result data obtainable** |

### Critical language finding
**All CCS report PDFs on the `/tc/` path are TRADITIONAL Chinese.** Searching the extracted text for the
simplified forms `应急通信` / `地质灾害` returned **0 hits even where the concept is plainly present** —
the text reads `應急通信` / `應急`. All counts below are therefore given in traditional forms.
There is no simplified-Chinese PDF edition: `https://www.chinaccs.com.hk/sc/ir/reports/ar2025/ar2025.pdf`
returns **HTTP 404**. Only `/tc/` (traditional) and `/en/` (English) PDFs exist.

A second trap: PyMuPDF inserts line breaks inside words (e.g. `泥\n石流`). Raw `grep` under-counts.
Counts below are computed on **whitespace-stripped** text and are therefore reliable.

---

## 1. Report inventory and exact PDF URLs

Source listing page: <https://www.chinaccs.com.hk/sc/ir/reports.php> (and `/en/`)

> **Site bug worth recording:** the listing page's 年报 button links to
> `…/sc/ir/reports/ar2026.php`, which returns **404 / "oops! We couldn't find this page."**
> The annual-report page that actually resolves is **`ar2025.php`**, labelled "中国通信服务股份有限公司 2025 年报"
> (19.40 MB). The listing's own `<img>` is `ar2026.png`, i.e. the page was renamed by publication year but the
> link/image were not updated. Use `ar2025.php`, not `ar2026.php`.

| Report | Landing page | PDF (as linked by that page) | Size | Pages | Downloaded? |
|---|---|---|---|---|---|
| **FY2025 annual report** ("2025 年报") | `https://www.chinaccs.com.hk/sc/ir/reports/ar2025.php` | `https://www.chinaccs.com.hk/tc/ir/reports/ar2025/ar2025.pdf` | 19.40 MB | 262 | **YES** → `pdf/ar2025.pdf`, `txt_ar2025.txt` |
| FY2025 annual report — **English** | (same page, EN) | `https://www.chinaccs.com.hk/en/ir/reports/ar2025/ar2025.pdf` | 21,140,845 B | 262 | **YES** → `pdf/ar2025_en.pdf`, `txt_ar2025_en.txt` |
| **FY2024 annual report** ("2024 年报") | `https://www.chinaccs.com.hk/sc/ir/reports/ar2024.php` | `https://www.chinaccs.com.hk/tc/ir/reports/ar2024/ar2024.pdf` | 19.80 MB | 266 | **YES** → `pdf/ar2024.pdf`, `txt_ar2024.txt` |
| **H1 2026 interim report** ("2026 中期报告") | `https://www.chinaccs.com.hk/sc/ir/reports/ir2026.php` | `https://www.chinaccs.com.hk/tc/ir/reports/ir2026/ir2026.pdf` | 2.79 MB | 47 | **YES** → `pdf/ir2026.pdf`, `txt_ir2026.txt` |
| **H1 2025 interim report** ("2025 中期报告") | `https://www.chinaccs.com.hk/sc/ir/reports/ir2025.php` | `https://www.chinaccs.com.hk/tc/ir/reports/ir2025/ir2025.pdf` | 3.39 MB | 45 | **YES** → `pdf/ir2025.pdf`, `txt_ir2025.txt` |
| FY2024 results press release | `…/sc/media/press/p250327.pdf` | same | 7 pp | — | **YES** → `txt_p250327.txt` |
| H1 2025 results press release | `…/sc/media/press/p250821.pdf` | same | 5 pp | — | **YES** → `txt_p250821.txt` |
| FY2025 results press release | `…/sc/media/press/p260331.pdf` | same | 5 pp | — | **YES** → `txt_p260331.txt` |
| H1 2026 results press release | `…/sc/media/press/p260826.pdf` | same | 5 pp | — | **YES** → `txt_p260826.txt` |

**Page-number convention used below.** The PDF has 3 unnumbered/front-matter pages before the printed
foliation, so **printed page = PDF page index + 3**. Verified on 13 separate pages, e.g.
PDF p.41 prints "44"; PDF p.99 prints "102"; PDF p.156 prints "159"; PDF p.211 prints "214".
Both numbers are given throughout so any citation can be re-checked either way.

---

## 2. Segment revenue — the three segments

### 2.1 FY2025 (year ended 31 December 2025) — the most recent annual report

Exact table, RMB **thousands** ("下表列示二零二四年和二零二五年本集团各项经营收入的金额和变化率"),
**PDF p.41 / printed p.44**, "管理層對財務狀況和經營成果的討論與分析 → 業務收入組合".
URL: <https://www.chinaccs.com.hk/tc/ir/reports/ar2025/ar2025.pdf>

| Segment | FY2025 (RMB'000) | FY2024 (RMB'000) | Change |
|---|---:|---:|---:|
| 電信基建服務 / Telecommunications Infrastructure Services (**TIS**) | **74,391,260** | 75,172,237 | (1.0%) |
| 業務流程外判服務 / Business Process Outsourcing Services (**BPO**) | **44,061,421** | 43,459,018 | 1.4% |
| 應用、內容及其他服務 / Applications, Content and Other Services (**ACO**) | **31,639,928** | 31,368,848 | 0.9% |
| **Total 經營收入 / Total Revenues** | **150,092,609** | 150,000,103 | 0.1% |

Sub-lines from the same table (FY2025 / FY2024, RMB'000):
- TIS: design services 8,939,972 / 9,917,391 (9.9%); construction services 61,014,658 / 60,673,388 (+0.6%); project supervision and management 4,436,630 / 4,581,458 (3.2%)
- BPO: network maintenance 19,118,078 / 18,754,785 (+1.9%); property management 8,306,956 / 8,122,502 (+2.3%); supply chain 13,731,835 / 13,559,545 (+1.3%); sub-total core BPO 41,156,869 / 40,436,832 (+1.8%); products distribution 2,904,552 / 3,022,186 (3.9%)
- ACO: system integration 19,398,374 / 19,594,996 (1.0%); software development & system support 7,114,106 / 6,241,050 (+14.0%); value-added services 2,607,850 / 2,749,632 (5.2%); others 2,519,598 / 2,783,170 (9.5%)

Revenue mix (same page): TIS 49.6% / BPO 29.3% / ACO 20.9% in 2025; 50.1% / 29.0% / 21.1% in 2024.

**Two independent confirmations of the identical totals** inside the same PDF:
- Notes to the consolidated financial statements, **note 4 「經營收入」/ "4. Revenues"**, PDF p.211 / printed p.214:
  `電信基建服務收入 74,391,260 / 75,172,237` · `業務流程外判服務收入 44,061,421 / 43,459,018` ·
  `應用、內容及其他服務收入 31,639,928 / 31,368,848` · total `150,092,609 / 150,000,103`.
- Five-year 「財務概要」/ "FINANCIAL SUMMARY", PDF p.260 / printed p.263 — adds FY2023: TIS 76,136,756;
  BPO 43,550,614; ACO 28,927,306; total 148,614,676.

MD&A rounding in the narrative (PDF p.39 / printed p.42), verbatim:
> 「來自電信基建服務的收入為人民幣74,391百萬元，同比下降1.0%；來自業務流程外判服務的收入為人民幣
> 44,062百萬元，同比增長1.4%；來自應用、內容及其他服務的收入為人民幣31,640百萬元，同比增長0.9%。」

(Note the narrative rounds BPO to 44,062 and ACO to 31,640; the audited table says 44,061,421 and 31,639,928.)

### 2.2 FY2024 (year ended 31 December 2024) — verified against the FY2024 report itself

Source: FY2024 annual report, **PDF p.43** (revenue table) and **PDF p.214** (note 4).
URL: <https://www.chinaccs.com.hk/tc/ir/reports/ar2024/ar2024.pdf>

| Segment | FY2024 (RMB'000) | FY2023 (RMB'000) |
|---|---:|---:|
| 電信基建服務 TIS | **75,172,237** | 76,136,756 |
| 業務流程外判服務 BPO | **43,459,018** | 43,550,614 |
| 應用、內容及其他服務 ACO | **31,368,848** | 28,927,306 |
| 經營收入 Total | **150,000,103** | 148,614,676 |

### 2.3 Interim periods

**H1 2026** (six months ended 30 June 2026), note 5 「經營收入」, **PDF p.24** (prints "22").
URL: <https://www.chinaccs.com.hk/tc/ir/reports/ir2026/ir2026.pdf>

| Segment | H1 2026 (RMB'000) | H1 2025 (RMB'000) |
|---|---:|---:|
| 電信基建服務 TIS | **36,601,738** | 38,272,609 |
| 業務流程外判服務 BPO | **22,104,178** | 22,382,937 |
| 應用、內容及其他服務 ACO | **15,774,090** | 16,283,705 |
| 經營收入 Total | **74,480,006** | 76,939,251 |

**H1 2025** (six months ended 30 June 2025), note 5, **PDF p.23** (prints "21").
URL: <https://www.chinaccs.com.hk/tc/ir/reports/ir2025/ir2025.pdf>

| Segment | H1 2025 (RMB'000) | H1 2024 (RMB'000) |
|---|---:|---:|
| 電信基建服務 TIS | **38,272,609** | 37,666,188 |
| 業務流程外判服務 BPO | **22,382,937** | 22,162,474 |
| 應用、內容及其他服務 ACO | **16,283,705** | 14,583,291 |
| 經營收入 Total | **76,939,251** | 74,411,953 |

---

## 3. Total revenue and net profit

### FY2025 (from FY2025 annual report)
- **經營收入 / Total revenues: RMB 150,092,609 thousand (≈RMB150,093 million)**, +0.1% YoY — PDF p.41 (printed 44) and p.211 (printed 214).
- **本年利潤 / Profit for the year: RMB 3,749,738 thousand** — 財務概要, PDF p.260 (printed 263).
- **本公司股東應佔利潤 / Profit attributable to equity shareholders of the Company: RMB 3,610,019 thousand (≈RMB3,610 million)**, +0.1% YoY — PDF p.260 and PDF p.39 (printed 42).
- 每股基本盈利 basic EPS RMB 0.521. Free cash flow RMB 795 million (PDF p.39).
- MD&A verbatim (PDF p.39 / printed 42): 「全年經營收入達到人民幣150,093百萬元，較二零二四年增長0.1%。本公司股東應佔利潤為人民幣3,610百萬元，較二零二四年增長0.1%。」

### FY2024 (from FY2024 annual report)
- Total revenue **RMB 150,000,103 thousand**; profit for the year **RMB 3,753,397 thousand**;
  **profit attributable to shareholders RMB 3,606,861 thousand (≈RMB3,607 million)**, +0.6% YoY; basic EPS RMB 0.521.
  MD&A states 自由現金流 RMB 5,214 million. (FY2024 AR, 財務重點 p.13 area and MD&A; five-year summary PDF p.264.)

### H1 2026 and H1 2025 (interim summaries)
- **H1 2026:** 經營收入 RMB 74,480 million, −3.2% YoY; 淨利潤/本公司股東應佔利潤 **RMB 1,970 million, −7.5%**
  (−3.2% on a comparable basis excluding dividend income); basic EPS RMB 0.284; gross profit 7,432 (−5.8%);
  gross margin verbatim 「毛利率為10.0%，同比降幅有所趨緩」; free cash flow −7,706. (ir2026 PDF p.4, 「摘要」)
  Also on that page, verbatim: 「本集團深挖AI+巨大市場潛能，上半年AI+領域（AIDC、AI應用）收入同比增長62%，
  佔經營收入比重為10%。」 and 「本集團佈局「六大空間+」新賽道，包括AIDC、AI應用、通服智維、雙碳、配電網和
  低空經濟等在內的「六大空間+」業務，新簽合同額同比提升11%，佔總新簽合同額約34%…」
- **H1 2025:** 經營收入 RMB 76,939 million, +3.4% YoY; **RMB 2,129 million, +0.2%** in profit attributable to shareholders; basic EPS RMB 0.307; gross profit 7,888 (−2.8%); free cash flow −7,627. (ir2025 PDF p.4, 「摘要」)
  > Note on 淨利潤 wording: the FY2024 AR footnote 2 states 「净利润指本公司股东应占利润」 ("net profit" means profit attributable to the Company's shareholders). Treat CCS "净利润" and "股东应占利润" as the same measure.

---

## 4. Mentions of 应急通信 / 地质灾害 / 应急安全 / 卫星 / 物联网 / NB-IoT / 偏远 etc.

### 4.1 Keyword census (whitespace-normalised exact substring counts)

| Term | FY2025 AR | FY2024 AR | H1 2025 IR | H1 2026 IR |
|---|---:|---:|---:|---:|
| 應急通信 | **1** | **4** | 0 | 0 |
| 應急 (any) | 39 | 60 | 10 | 4 |
| **地質災害** | **0** | **0** | 0 | 0 |
| 地質 (any) | 0 | 0 | 0 | 0 |
| 山體滑坡 (landslide) | **2** | 0 | 0 | 0 |
| 泥石流 (mudslide) | 1 | 0 | 0 | 0 |
| 崩塌 | 1 | 0 | 0 | 0 |
| 地震 (earthquake) | 0 | 7 | 1 | 1 |
| 颱風 (typhoon) | 4 | 4 | 1 | 0 |
| 洪澇 | 2 | 2 | 0 | 1 |
| 暴雨 | 3 | 2 | 0 | 1 |
| 衛星 (satellite) | **1** | **3** | 0 | 0 |
| 物聯網 (IoT) | 11 | 17 | 2 | 0 |
| **NB-IoT** | **0** | **0** | 0 | 0 |
| **低功耗** | **0** | **0** | 0 | 0 |
| **電信普遍服務 / 普遍服務** | **0** | **0** | 0 | 0 |
| 高原 (plateau) | 0 | 0 | 1 | 0 |
| 偏遠 (remote) | 1 | 0 | 0 | 0 |
| 山區 (mountainous) | 0 | 0 | 0 | 0 |
| **極端場景 (extreme scenarios)** | **0** | **0** | 0 | 0 |
| 極端條件 (extreme conditions) | 0 | 0 | **1** | 0 |
| 無人機 (drone) | 0 | 1 | 0 | 1 |
| 低空經濟 | 4 | 7 | 1 | 5 |
| 十四部門 (the 14 ministries) | 0 | 0 | 0 | 0 |

**Headline answers:**
1. **地質災害 / 地灾 appears nowhere** in any of the four reports (0 hits, exact and normalised).
   CCS instead narrates specific events as **山體滑坡 / 泥石流 / 崩塌 / 暴雨 / 洪澇 / 颱風**.
2. **應急通信 appears exactly once in the FY2025 annual report** — as an ESG stakeholder-table cell,
   not in the business/MD&A narrative. It appears **4× in FY2024** and **0× in either interim report**.
3. The phrase **極端場景** (the policy's key term) **appears nowhere**. The nearest CCS wording is
   「極端條件應急指揮通信能力」 in the H1 2025 interim report.
4. **No NB-IoT, no 低功耗, no 電信普遍服務, no 無人機 in the FY2025 AR** (drone appears 1× only in FY2024).

### 4.2 The single 應急通信 mention in the FY2025 annual report — EXACT QUOTE

Location: 環境、社會及管治報告 (ESG Report) → 「持份者溝通」 (Communication with Stakeholders)
stakeholder table, row **「社區」 (Community)**, PDF p.99 = **printed p.102**.
URL: <https://www.chinaccs.com.hk/tc/ir/reports/ar2025/ar2025.pdf>

Chinese (verbatim):
> 社區 ｜ 社區溝通活動 ｜ 保護環境 節能減排、節約用水用電 ｜ 社區共建活動 ｜ **保障應急通信** ｜ **積極投入抗災救災和通信保障工作** ｜ 社會公益活動 ｜ 關愛弱勢群體 ｜ 參與鄉村振興、助殘濟困

English, same page (verbatim):
> Community ｜ Community communication activity ｜ Protect the environment / Energy saving, emission reduction and conservation of water and electricity ｜ Community building activity ｜ **Safeguard emergency communications** ｜ **Actively engage in disaster relief and communications safeguard** ｜ Public welfare activity ｜ Care for the underprivileged groups

This is a **stakeholder-expectation / company-response pair** in a table, i.e. CCS's forward commitment,
**not** a project description. It is the only occurrence of the term in the FY2025 AR.

### 4.3 The four 應急通信 mentions in the FY2024 annual report — EXACT QUOTES

URL: <https://www.chinaccs.com.hk/tc/ir/reports/ar2024/ar2024.pdf>

**(a) 董事長報告書 (Chairman's Report), PDF p.20, printed p.23** — verbatim:
> 「本集團積極回饋社會，做好防災救災和通信支撐保障工作。圓滿完成神舟十九號載人飛船發射通信保障任務，
> 為「博鰲亞洲論壇2024年年會」、「第七屆中國國際進口博覽會」、「2024年世界互聯網大會烏鎮峰會」等國家重要
> 活動提供通信服務。投身搶險救災保通信工作，在初春局部地區寒潮低溫極端天氣、南方多地特大暴雨洪澇災害、
> 颱風「摩羯」、「貝碧嘉」、新疆烏什縣7.1級地震、西藏定日縣6.8級地震等重大災害中，第一時間奔赴災區，
> 全力開展救災**應急通信**保障，全年共投入人力約15萬人次，守護通信「生命線」。」

**(b) ESG stakeholder table, PDF p.105, printed p.108** — same cell as FY2025: 「社區 … **保障應急通信** 積極投入抗災救災和通信保障工作」.

**(c) ESG 「重大活動通信保障 → 護航神州十九號」, PDF p.157, printed p.160** — verbatim:
> 「本集團下屬甘肅公司在「神州十九號」載人飛船發射一周前，正式啟動**應急通信**保障預案確定保障人員，整理
> 保障物資成立應急保障先鋒隊。「神州十九號」載人飛船發射24小時前應急保障先鋒隊進駐場地對保障區域內涉及的
> 基站逐個檢查，排除動環離線等故障，時刻檢測電源供電情況確保區域網絡運行平穩。」

**(d) ESG disaster narrative, PDF p.159, printed p.162** — verbatim:
> 「新疆維吾爾自治區阿克蘇地區烏什縣發生7.1級地震。地震發生後，本集團下屬新疆公司迅速啟動應急響應機制，
> 第一時間組建救援隊伍趕赴地震受災地區，開展**應急通信**保障工作。」
(same page also: 「南方低溫雨雪冰凍災害 … 本集團下屬湖南公司迎「寒」而上 … 累計投入施工人員12,414人次，生產車輛3,951輛次；累計恢復故障（ODN及基站）13,801處。」)

### 4.4 Geological-hazard wording in the FY2025 annual report — EXACT QUOTES

Location: ESG Report → 「社會參與 → 抗災」. **PDF p.156 = printed p.159.**

> 「五月，雲南省怒江州貢山縣、福貢縣遭受罕見持續強降雨襲擊，山體在雨水長期浸泡下松動失穩，**崩塌、泥石流**
> 頻頻發生，道路被沖毀掩埋，通信光纜多處中斷。本集團下屬雲南公司迅速啟動通信應急響應機制，全力投入搶險救災。
> 六月，貴州省黔南州三都縣遭遇連續強降特大暴雨襲擊，引發**山體滑坡**、道路塌方、河水暴漲，導致全縣通信
> 大面積癱瘓。本集團下屬貴州公司迅速組建聯合搶險指揮部，兵分兩路全力搶修通信。
> 七月，強降雨導致重慶巴南、南川等5個區縣多處鐵塔基站、通信機房停電，多處桿路及通信光纜受損。本集團下屬
> 重慶公司迅速集結力量，多線同步開展搶險救援 …」

Aggregate figure, same page, verbatim:
> 「二零二五年，本集團累計投入人力28,000餘人次、車輛12,000餘輛次，修復通信設施超過28,000餘處，
> 參與救災工作時間128,000餘小時 …」

**PDF p.157 = printed p.160** (「洪澇災害」/「颱風」/「暴雪」), verbatim:
> 「二月，四川宜賓市筠連縣突發**山體滑坡**，本集團下屬四川公司第一時間啟動應急預案，由宜賓分公司組建搶險
> 小組，奔赴受災一線，緊急開展網絡搶修，為救援保障提供暢通的網絡支持。
> 八月，甘肅蘭州市榆中縣等地遭遇連續強降雨引發山洪災害 …本集團下屬甘肅公司第一時間組建搶險隊伍趕赴現場，
> 爭分奪秒搶修通信生命線。」
> 「颱風 — 九月，第18號超強颱風「樺加沙」攜強風暴雨席捲而來 …本集團下屬廣東公司 …奮戰在通信保障和搶險救災一線」
> 「暴雪 — 四月，內蒙古錫林郭勒盟遭遇罕見暴風雪。本集團下屬中國通信建設北京工程局組成搶先團隊在–20℃極寒中
> 持續作業，累計搶修基站13站次，重點區域通信全部恢復。」

English edition, same pagination — **PDF p.156 = printed "Annual Report 2025 159"**, verbatim:
> "In May, Gongshan County and Fugong County in Nujiang Prefecture, Yunnan Province, were struck by rare, persistent
> heavy rainfall. Prolonged water saturation destabilized mountain slopes, triggering frequent **landslides and
> mudslides**. Roads were washed away and buried, while communications cables were severed in multiple locations.
> **Yunnan Company of the Group swiftly activated its emergency communications response mechanism** …
> In June, Sandu County in Qiannan Prefecture, Guizhou Province, endured consecutive extreme downpours. This
> triggered **landslides**, road collapses, and surging rivers, causing widespread communications outages …"

**PDF p.157 = printed 160**, verbatim:
> "In February, a **sudden landslide** in Junlian County, Yibin City, Sichuan Province. Sichuan Company of the Group
> immediately activated its emergency response plan. … In August, continuous heavy rainfall triggered flash floods in
> Yuzhong County and other areas of Lanzhou City, Gansu Province …"

**PDF p.99 = printed 102** — the 應急通信 quote given in §4.2 above.

### 4.5 應急安全 as a strategic business line (no "應急通信" wording)

**FY2025 AR, 董事長報告書, PDF p.17 = printed p.20**, verbatim:
> 「（四） 應急安全領域
> 本集團致力於建強公共安全治理和網絡信息安全能力，築牢經濟社會發展的安全底座。在應急管理方面，聚力打造
> 「應急+安全」行業解決方案，面向氣象、水利、化工、礦山等重點行業強化專業服務與價值輸出，助力全國多地
> 應急能力提升，在「人影工程」、基層防災等領域取得突破。在網信安全方面，強化自主可控的網絡安全運營產品
> 及數據安全產品供給 …」

English (same page), verbatim:
> "**4. The Field of Emergency Management and Security** — The Group is committed to strengthening public safety
> governance as well as network information security capabilities … In emergency management, it focused on creating
> "emergency management + security" industry solutions, enhancing professional services and value delivery for key
> industries such as meteorology, water conservancy, chemical, and mining. The Group supported improvements in
> emergency response capabilities in many regions across the country, and achieved breakthroughs in areas such as
> "weather modification engineering" and grassroots disaster prevention."

**FY2025 AR, 業務概覽 — 戰新業務, PDF p.25 = printed p.28**, verbatim:
> 「在應急方面，以應急、消防、生態環境、水利、氣象、自然資源、林草等行業領域為業務主線，聚焦防災減災救災
> 和急難險重突發公共事件處置保障能力，構建大應急完整性智慧產品集、解決方案庫以及一站式信息化服務能力，
> 為政府、化工園區、高危企業等客戶提供諮詢設計、軟件開發、系統集成及運維等服務。」

**Product named 「通服應急」 (product no. 4)**, FY2025 AR PDF p.35 = printed p.38, verbatim:
> 「**通服應急** — 以諮詢規劃為引領，以安全應急產業為業務主線，面向工業生產、城市及生態安全三大領域，
> 聚焦監測預警、應急指揮、防災減災，打造安全生產風險監測預警平台、應急救援指揮平台、化工園區智能化管控
> 平台、工業互聯網+企業安全…智慧水利信息化管理平台、森林火災風險監測預警平台等為核心的大應急大安全應用
> 產品圖譜，覆蓋應急、礦山、消防、水利、氣象、自然資源等多行業。」

### 4.6 The closest CCS wording to "extreme-scenario emergency communications"

**H1 2025 interim report, 董事長報告書, PDF p.8 (prints "6")**, verbatim:
> 「（四） 應急安全領域
> 本集團助力構建現代化應急管理體系，護航客戶網絡與信息安全，夯實社會安全發展基礎。在應急管理方面，充分
> 發揮前沿數字技術優勢，利用人工智能大模型賦能行業應用，幫助礦山、化工、水利、消防等重點領域客戶實現
> 應急管理智能化轉型，**提升防災減災救災和極端條件應急指揮通信能力**。在網信安全方面，打造多款自主可控的
> 網信安全產品 …」
URL: <https://www.chinaccs.com.hk/tc/ir/reports/ir2025/ir2025.pdf>
This is the **only** occurrence of 極端條件 in any of the four reports. Note it says
「極端條件應急指揮通信能力」 (emergency *command* communications under extreme conditions) —
not the policy's 「極端場景應急通信能力」.

Same interim, PDF p.10, verbatim (disaster response):
> 「本集團堅持以人民為中心，完成搶險救災、重要活動、鄉村振興相關建設和通信保障任務。在雲南、貴州、重慶、
> 湖北、湖南、廣西等地強降雨，以及西藏定日縣6.8級地震、颱風「蝴蝶」等重大災害中，全力搶修受損通信設施，
> 參與災後全面恢復重建，成為應急救援和民生保障的堅實支撐。」
And (PDF p.10): 「本集團承建西藏拉薩南北山綠化工程智慧管護系統項目，守護**雪域高原**生態環境 …」

### 4.7 Satellite

**FY2024 AR, 董事長報告書, PDF p.18 = printed p.21**, verbatim — names an actual satellite product:
> 「聚焦攻關未來產業關鍵技術，發力5G-A、區塊鏈、人工智能+、**衛星通信**、低空經濟等前沿領域，打造區塊鏈
> 數據服務平台、**直連衛星產品「星極通」**、網聯無人機智能應用平台以及人工智能產品集。」
Cross-confirmed identically in the FY2024 results press release (p250327, PDF p.4):
> 「發力5G-A、區塊鏈、人工智能+、衛星通信、低空經濟等前沿領域，打造區塊鏈數據服務平台、直連衛星產品
> 「星極通」、網聯無人機智能應用平台以及人工智能產品集。」
**This is the single strongest satellite-evidence item in the primary sources** (直連衛星 = direct-to-satellite
/ D2D satellite connectivity). It appears in FY2024 only.

**FY2025 AR, PDF p.16 = printed p.19**, verbatim:
> 「憑藉新一代數智、綠色技術優勢，以及總包總集一體化服務能力，投身通智超算、5G-A、**衛星互聯網**、低空等
> 新型基礎設施建設 … 全年來自該領域新簽合同額增速近40%」

### 4.8 IoT (物聯網) and 偏遠 (remote)

FY2025 AR has 11 物聯網 occurrences, all generic technology-capability framing, e.g.
- PDF p.17 = printed p.20: 「本集團依託人工智能、**物聯網**、大數據等前沿技術，「諮詢+總包+軟件+平台+服務」一體化服務能力 …」
- PDF p.26 = printed p.29: named project 「某集團供水**物聯網**平台建設項目」
- PDF p.36-37 = printed p.39-40: 「首創行業**物聯網**關將庫端數據以直採方式實時歸集 … 守護大國糧倉安全」(grain-storage)
- PDF p.112 = printed p.115 (climate): 「加大5G、雲計算、**物聯網**、大數據、區塊鏈、AI等新技術應用」

**偏遠 (remote) — the only occurrence, FY2025 AR PDF p.113 = printed p.116**, verbatim:
> 「本集團下屬中通服諮詢設計研究院有限公司打造新疆阿克蘇零碳光儲一體系統沙漠地區應用項目，通過建設113處
> 完全由光伏和儲能供電的通信基站，有效服務鐵路沿線、油田作業區和農牧民生活區，不僅解決了**偏遠地區**網絡
> 覆蓋難題，更以「零碳智慧基站」的創新模式，為全球沙漠場景綠色能源建設提供了可複製、可推廣的「塔里木樣本」。」
English (PDF p.113): "It not only solves the problem of **network coverage in remote areas** … "Tarim Model"."

### 4.9 FY2025 report explicitly does NOT cite the policy
`十四部門`, `极端场景应急通信`, `工信部联信管`, `256号` → **0 hits across all four reports.**
So: **the CCS FY2025 annual report does not reference the 14-ministry policy at all.**

---

## 5. Principal subsidiaries named in the annual report

**There is no 「主要附屬公司」 heading** in the FY2025 AR. The relevant disclosure is
**note 47 「子公司」/ "47. Subsidiaries"**, PDF p.254 = printed p.257 and PDF p.255 = printed p.258,
which lists companies "主要影響本集團的經營業績、資產及負債的**若干**子公司" — i.e. **a selected subset,
not the full register**. Columns: 公司名稱 / 法律性質 / 註冊成立地點 / 本公司持有的所有權及表決權比例 (2025 & 2024) /
已發行及繳足股本 / 主要業務.

Named entities (verbatim, with registered/paid-up capital as printed):

| Company (verbatim) | Ownership % (2025=2024) | Issued & paid-up capital | Principal business (abridged, verbatim phrases) |
|---|---|---|---|
| 廣東省通信產業服務有限公司 | 100 | 人民幣2,688百萬元 | 於廣東省通過子公司提供綜合電信支撐業務 |
| 浙江省通信服務控股集團有限公司 | 100 | 人民幣1,498百萬元 | 於浙江省…綜合電信支撐業務 |
| 上海市信產通信服務有限公司 | 100 | 人民幣1,376百萬元 | 於上海市… |
| 福建省通信產業服務有限公司 | 100 | 人民幣281百萬元 | 於福建省… |
| 湖北省信產通信服務有限公司 | 100 | 人民幣317百萬元 | 於湖北省… |
| 江蘇省通信服務有限公司 | 100 | 人民幣578百萬元 | 於江蘇省… |
| 安徽省通信產業服務有限公司 | 100 | 人民幣420百萬元 | 於安徽省… |
| 江西省通信產業服務有限公司 | 100 | 人民幣200百萬元 | 於江西省… |
| 湖南省通信產業服務有限公司 | 100 | 人民幣886百萬元 | 於湖南省… |
| 廣西壯族自治區通信產業服務有限公司 | 100 | 人民幣322百萬元 | 於廣西壯族自治區… |
| 重慶市通信產業服務有限公司 | 100 | 人民幣209百萬元 | 於重慶市… |
| 四川省通信產業服務有限公司 | 100 | 人民幣798百萬元 | 於四川省… |
| 貴州省通信產業服務有限公司 | 100 | 人民幣131百萬元 | 於貴州省… |
| 雲南省通信產業服務有限公司 | 100 | 人民幣238百萬元 | 於雲南省… |
| 陝西省通信服務有限公司 | 100 | 人民幣145百萬元 | 於陝西省… |
| 甘肅省通信產業服務有限公司 | 100 | 人民幣129百萬元 | 於甘肅省… |
| 青海省通信服務有限公司 | 100 | 人民幣68百萬元 | 於青海省… |
| 新疆維吾爾自治區通信產業服務有限公司 | 100 | 人民幣195百萬元 | 於新疆維吾爾自治區… |
| 中國通信建設集團有限公司 | 100 | 人民幣550百萬元 | 於中國北部省份通過子公司提供綜合電信支撐業務 |
| 中國通信服務國際有限公司 | 100 | 港幣846.87百萬元 | 註冊地：香港特別行政區 |
| 中數通信息有限公司 | 60.38 | 人民幣120百萬元 | 提供綜合電信支撐業務 |
| 中通服軟件科技有限公司 | 60 | 美元25百萬元 | 提供綜合電信支撐業務 |
| 寧夏回族自治區通信產業服務有限公司 | 100 | 人民幣106百萬元 | 於寧夏回族自治區… |
| 山東省信息產業服務有限公司 | 100 | 人民幣200百萬元 | 於山東省… |
| 中英海底系統有限公司 | 100 | 人民幣327百萬元 | 提供海底電纜建設和其他相關業務 |
| 海南省通信產業服務有限公司 | 100 | 人民幣141百萬元 | 於海南省… |
| 中通服供應鏈股份有限公司 | 73.99 | 人民幣1,256百萬元 | 提供綜合電信支撐業務 |
| 內蒙古自治區通信服務有限公司 | 100 | 人民幣30百萬元 | 於內蒙古自治區… |
| 通服資本控股有限公司 | 100 | 人民幣500百萬元 | 資本投資 |
| 中通服智慧物業發展有限公司 | 100 | 人民幣50百萬元 | 提供物業服務 |
| 通服智能技術有限公司 | 100 | 人民幣100百萬元 ("—"printed) | 提供綜合電信支撐業務 |

(Note: `通服智能技術有限公司` prints an em-dash for paid-up capital in the FY2025 note; the character
sequence in the extracted table is `–`. Recorded as printed.)

Other subsidiaries named **elsewhere** in the FY2025 AR (not in note 47) — useful for the 应急 line:
- **中通服和信科技有限公司** — named only on the **corporate website**, not in the AR (see §7).
- 中通服諮詢設計研究院有限公司 — ESG, PDF p.113 (Xinjiang zero-carbon base stations) & p.115 (zero-carbon park).
- 華信諮詢設計研究院有限公司 — ESG, PDF p.115 (water-cooled green data centre).
- 中通服節能技術服務有限公司 — ESG, PDF p.111 (data-centre air governance white paper).
- 中國通信建設集團有限公司 — co-founder of 零碳發展聯盟, ESG PDF p.111; and 中國通信建設北京工程局 (blizzard response, PDF p.157).
- 中通服供應鏈股份有限公司 — 6 auction subsidiaries named: 中捷通信有限公司、上海通貿國際供應鏈管理有限公司、浙江中通通信有限公司、江蘇中博通信有限公司、福建省中通通信有限公司、湖北信通通信有限公司 (ESG PDF p.120 = printed p.123).
- Group structure page (not the AR): <https://www.chinaccs.com.hk/sc/about/gp_structure.php>

Also from 大事記 (PDF p.7-9): 2015 成立全資子公司中通服供應鏈管理有限公司 (renamed 中通服供應鏈股份有限公司, 2023);
2017 成立全資子公司通服資本控股有限公司; 2023 收購 中英海底系統有限公司 49% 外方股權 (now 全資).

---

## 6. POLICY — 工信部等十四部门《关于加强极端场景应急通信能力建设的意见》

### 6.1 Document identity and official URLs — both opened and read

| Item | Value |
|---|---|
| Title | 工业和信息化部等十四部门关于加强极端场景应急通信能力建设的意见 |
| Document number | **工信部联信管〔2024〕256号** |
| Signed / dated | **2024年12月31日** (printed at the foot of the document, after the 14 signatory bodies) |
| Issuing bodies (14, verbatim) | 工业和信息化部；中央空中交通管理委员会办公室；国家发展和改革委员会；公安部；财政部；交通运输部；农业农村部；国家卫生健康委员会；应急管理部；中国气象局；国家能源局；国家林业和草原局；中国民用航空局；国家消防救援局 |
| **Official gov.cn URL** | <https://www.gov.cn/zhengce/zhengceku/202501/content_7000295.htm> — **OPENED**, full text 24,502 bytes → `pol_govcn.md` |
| Official MIIT URL | <https://www.miit.gov.cn/zwgk/zcwj/wjfb/yj/art/2025/art_80059e80ee8b4e659168ab1eebb41cc4.html> — direct/Jina fetch **blocked (429 rate-limit)**, but the MIIT mirror below **opened** fine |
| MIIT mirror (OPENED) | <https://wap.miit.gov.cn/jgsj/xgj/gzdt/art/2025/art_8ba85168e1664c41a7546e0d63577a14.html> → `pol_miit2.md` (12,283 bytes, text matches gov.cn) |
| **Official interpretation 「解读」** | <https://www.gov.cn/zhengce/202501/content_7000297.htm> — **OPENED** → `pol_jiedu.md`; source line reads 「2025-01-21 21:02 来源： 工业和信息化部网站」 |

**Publication date.** The document itself is dated **2024-12-31** and is filed by gov.cn under the
**202501** (January 2025) directory; the official interpretation was posted **2025-01-21**, and Xinhua's
news item on the joint issuance is dated **2025-01-22** ([news.cn](http://www.news.cn/info/20250122/8bea1c1776e3479990634ef6e3d78d0b/c.html)).
Prefer the document date **2024-12-31** with gov.cn publication in **January 2025**.

### 6.2 Key requirements — verbatim

**总体要求 (Overall requirements), opening paragraph:**
> 「为深入贯彻落实习近平总书记关于应急管理、防灾减灾救灾的重要指示批示精神，适应新时期极端场景和大安全
> 大应急对应急通信提出的更高要求，进一步强化部门联动，形成工作合力，持续推动应急通信能力现代化建设，
> 加快构建国家大应急通信框架，提出如下意见：」
> 「坚持总体国家安全观，坚持以人民为中心，坚持**底线思维、极限思维**，围绕构建国家大应急通信框架，以创新
> 突破技术装备为基础，以改革完善工作机制为保障，以夯实网络基础和**提升断路断电极端条件保障能力**为抓手，
> 全面提升应对极端场景应急通信能力，有力护航中国式现代化建设。」

**2027 target (到2027年):**
> 「应急通信步入高质量发展快车道，**空天地海一体**关键技术创新突破，极端条件适用装备有效供给，应急通信
> 特色服务持续拓展。应急通信供需对接清晰顺畅，部门间衔接协同更加高效，**电信企业应急管理改革加快推进**。
> 灾害易发地区通信网络覆盖水平显著提升，通信网络**抗毁韧性**切实增强，**公网专网协同**格局基本形成。
> 指挥预警智能高效，队伍力量体系健全有力，跨区域保障能力显著提升，**基层保底通信能力基本建立**，极端场景
> 保障能力大幅跃升。」

**Six sections / 17 numbered items** (「一」–「六」, items 「（一）」–「（十七）」):
二、推动应急通信创新突破 (items 1–4) · 三、加快应急通信机制改革 (5–8) ·
四、夯实应急通信网络基础 (9–11) · 五、强化极端场景保障能力 (12–15) · 六、保障措施 (16–17).

Verbatim highlights most relevant to a telecom-engineering supplier:

- **(一) 推进应急通信技术突破应用** — 「推动**跨运营商应急漫游、无人机空中通信、室内定位导航、地下空间信号增强**等适用于极端场景的重点技术研发，加快推进人工智能、通信大数据等新一代信息通信技术以及安全技术应用…」（工业和信息化部、公安部、应急管理部按职责分工负责）
- **(二) 研发推广新型应急通信装备** — 「重点加强**无人空中载体装备、全地形车、高空基站**等高机动性装备，**应急专网融合终端、背包基站、微波/散射通信装备**等轻量化便携装备，适应**严寒、密林**等极端条件装备以及更适合基层使用的易操作高可靠性设备研发推广。」（工信部、公安部、应急管理部、国家消防救援局）
- **(三) 构建应急通信创新发展平台** — 「产学研联合创建**应急通信工程实验室和技术研发中心**…组织制定**应急通信标准体系**，加强应急预警、网络抗毁、互联互通等标准研制。」（工信部、应急管理部）
- **(四) 推动应急通信产业生态繁荣** — 「建设**应急通信产业集群**，打造具有核心技术优势的骨干企业…完善应急通信公共服务平台，**发布指导性产品目录**…」（工信部、应急管理部）
- **(五) 构建应急通信供需对接机制**；**(七)** 「建立应急通信装备、队伍及易发**「断路、断电、断网」高风险区域台账**，完善急时电信企业间资源共用、互备及协同抢修机制…」
- **(八) 推进电信企业管理制度改革** — 「**电信企业建立应急通信指挥机制，设立应急通信专门机构**，统筹建设发展、运行维护、政企服务等部门资源力量做好应急通信工作，制定应急通信人员专项管理办法…」（工业和信息化部负责）
- **(九) 增强重点地区通信网络覆盖** — 「统筹利用**公众通信网、专用通信网、卫星通信网**，重点提升**灾害多发易发地区、重点国有林区、边境地区、重要国省干线**等的网络覆盖水平。推动**卫星网与地面网的融合协同和统一调度**…」（工信部、应急管理部、国家林草局）
- **(十) 提高通信网络抗毁韧性水平** — 「开展**通信网络抗毁能力普查评估**工作，摸清通信网络抗灾底数，**适度提升通信基础设施建设标准**…加快在**易灾乡镇建设超级基站**…」（工业和信息化部负责）
- **(十一) 建设专网通信支撑服务能力** — 「构建符合应急实战需求、与公网互通的专用通信网，形成**公专协同**的应急通信网络能力体系。加快建设我国自主可控的全球卫星通信系统，充分利用**甚小口径终端（VSAT）、天通、北斗、高通量、低轨星座**等卫星通信资源，形成统一调度、高效供给和融合应用的**天基应急通信能力**。」（工信部、应急管理部、国家林草局、国家消防救援局）
- **(十二) 增强应急通信指挥预警能力** — 「升级国家通信网应急指挥调度系统，加强**铁塔、通信、电力数据共享**…基于**小区广播**技术建强通信网预警信息传播能力…实现**秒级、靶向、安全**的预警信息发布。」（工信部、中国气象局）
- **(十三) 提高应急通信区域保障能力** — 「布局建设**应急通信综合保障区域中心**，集中储备装备物资…加强各型**应急通信无人航空器**配备部署和规范管理…」
- **(十四) 提升通信保障队伍实战能力** — 「依托国家综合性消防救援队伍组建国家、区域、省、市级应急指挥通信队伍，建设国家、省级**应急通信联训基地**…加强**全地形车、卫星便携站、应急专网融合终端**等装备配备。」
- **(十五) 加强基层保底应急通信能力** — 「基层…要强化**天通卫星电话**等通信装备配备…推动**易灾乡镇、行政村、国有林场**强化**天通、北斗短报文、应急专网融合终端**等小型、易用装备预置和维护。加强卫星站、卫星终端等通信设备在**船舶、海上设施**的配备…」
- **(十六) 强化组织实施** — 「各电信企业要**制定提升本企业应急通信能力发展规划**，做好资源配套，强化任务落实。要加强**政策宣贯解读**，积极回应舆论和民众关切…」
- **(十七) 强化制度建设** — 「完善应急通信预案体系…加大对**灾害多发易发地区政策倾斜**力度。」

**From the official 解读 (gov.cn, 2025-01-21)** — verbatim, the framing of the problem:
> 「但是，面对极端灾害场景，也暴露出应急通信能力还存在**机制体制有待健全、通信网络韧性有待增强、基层保底
> 通信手段欠缺、保障队伍装备水平不高**等短板弱项。」
> 「二是坚持问题导向，以创新突破技术装备为基础，以改革完善工作机制为保障，以夯实网络基础为抓手，加快推动
> 补强应急通信短板弱项；三是**强化极限思维**，重点加强**指挥预警、物资装备、保障队伍、基层保底**等关键能力…」
> 保障措施 four items: 「一是强化组织实施…二是强化制度建设…三是**强化资金投入**，充分利用现有资金渠道，积极
> 支持应急通信重大项目，电信企业保障资金投入。四是强化监督考核…」

---

## 7. Did CCS or its subsidiaries publish any response / interpretation / aligned project?

**Finding: NO published response or interpretation of the 14-ministry policy was found from CCS or any
subsidiary. There is, however, a substantial body of CCS "应急安全" business activity that overlaps the
policy's subject matter, and one near-verbatim policy-adjacent phrase in the H1 2025 interim report.**

Evidence by category:

**(a) Verified: no citation of the policy anywhere in the primary reports.**
`十四部门` / `十四部門` / `极端场景应急通信` / `極端場景應急通信` / `工信部联信管` / `256号` = **0 hits** in
FY2025 AR, FY2024 AR, H1 2026 IR, H1 2025 IR (both language editions where applicable).

**(b) Verified: the closest CCP-language alignment, H1 2025 interim report, PDF p.8** (quoted in §4.6):
「提升防災減災救災和**極端條件應急指揮通信能力**」 — thematically aligned with the policy's
「极端场景应急通信能力」, but **not** presented as a response to it, and worded differently.

**(c) Verified: CCS corporate website has a dedicated 「应急安全」 strategic-emerging-industry page** —
<https://www.chinaccs.com.hk/sc/business/emergency_mgmt_security.php> (opened, 29,630 bytes).
It contains **no** mention of the policy, of 极端场景, of 应急通信 as a term, or of 卫星.
Verbatim opening and the IoT/disaster-monitoring case:
> 「在应急方面，以**应急、消防、生态环境、水利、气象、自然资源、林草、人防**等八大行业领域为业务主线，打造
> **超40款行业和装备应用产品**，为政府、化工园区、高危企业等客户提供咨询设计、软件开发、系统集成及运维等业务。」
> 「**自然灾害监测预警平台** — 本集团下属**中通服和信科技有限公司**的自然灾害预警平台，基于GIS地理信息技术、
> **物联网**、大数据、人工智能、数字孪生等技术手段，针对防汛防洪抗旱监测预警业务实际场景，覆盖三防业务单位…」
> 「**尾矿库安全生产风险监测预警系统** — 本集团下属中通服和信科技有限公司聚焦尾矿库重大安全风险…结合实时气象、
> **地质**等数据，建立灾害仿真模型，模拟溃坝事故后果的动态展示…」
> 「**国家某区域应急救援中心信息化项目** — 该区域应急救援中心为国家六大应急中心之一，聚焦灾害应对…涵盖视频显示、
> 指挥控制、音频通讯等系统…」
> 「**某直辖市防洪调度应急指挥平台设计施工总承包项目** … 入选**水利部**新型基础设施建设典型案例。」
> 「**某省应急「运维」、「集成」、「集成+运维」项目** … 带动某省应急业务规模由400万元提升至超亿元」

**(d) Verified: FY2024 disclosures show engagement with 应急管理部 (MEM) R&D**, FY2024 results press release
`p250327` PDF p.4, verbatim:
> 「参与**应急管理部国家重点研发计划「重大自然灾害防控与公共安全」重点专项「灾害事故应急情境下的智能生成
> 决策知识库关键技术」项目**，实现灾害现场时空信息的动态高效整合、智能分析与应急救援决策支援。…全年来自
> **应急安全领域新签合同额增速超30%**。」
This is a real, named, government-programme alignment — but it is a **2024 R&D programme** under MEM,
parallel to (not a response to) the MIIT-led 14-ministry policy.

**(e) Verified: FY2024 satellite product 「星極通」** (direct-to-satellite), §4.7 — materially aligned with the
policy's 「充分利用…天通、北斗…等卫星通信资源」 and 「基层保底应急通信」, but again not framed as such.

**(f) MENTIONS FOUND VIA WEB SEARCH — snippet-only, unopened** (flagged as such):
H1 2026 interim report's 低空經濟 section names a self-developed product that is the clearest
"extreme-scenario" asset: verbatim from the opened file ir2026 PDF p.8 —
> 「本集團深耕交通、政府、應急等重點行業客戶…迭代優化**無人機偵測平台、「靈空」低空應急實戰應用平台**等
> 自研產品，滿足客戶低空監管、低空安防、「一網統飛」、應急救援、培訓賦能、飛手服務等業務需求。上半年，
> 來自該領域新簽合同額增速高達66%。」
(「靈空」低空應急實戰應用平台 = "Lingkong" low-altitude emergency practical-application platform.)

**(g) NOT FOUND:** no CCS press release, no 解读, no 宣贯 notice, no 项目公告 on chinaccs.com.hk referencing
《关于加强极端场景应急通信能力建设的意见》. Searches run (see §9) returned only government/industry-media
sources for the policy and unrelated CCS procurement notices.

---

## 8. Corporate-site sweep (Task 3) — pages opened, with keyword results

All pages below were fetched and read in this session (`f.sh`, files `ar_*.md` in the scratch dir).

| URL | 应急通信 | 极端场景 | 卫星 | 地灾/地质灾害 | 低功耗/NB-IoT | 物联网 | 电信普遍服务 |
|---|---|---|---|---|---|---|---|
| <https://www.chinaccs.com.hk/sc/media/news.php> | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| <https://www.chinaccs.com.hk/sc/media/news.php?year=2026> | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| <https://www.chinaccs.com.hk/sc/media/news.php?year=2025> | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| <https://www.chinaccs.com.hk/sc/media/news.php?year=2024> | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| <https://www.chinaccs.com.hk/sc/business/emergency_mgmt_security.php> | ✗ (as a term) | ✗ | ✗ | ✗ | ✗ | **✓** | ✗ |
| <https://www.chinaccs.com.hk/sc/business/telecom_operator.php> | ✗ | ✗ | **✓ 卫星网络** | ✗ | ✗ | ✗ | ✗ |
| <https://www.chinaccs.com.hk/sc/business/smart_city.php> | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** | ✗ |
| <https://www.chinaccs.com.hk/sc/business/aco.php> | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** | ✗ |
| <https://www.chinaccs.com.hk/sc/business/non_operator.php> | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** | ✗ |
| <https://www.chinaccs.com.hk/sc/business/key_cases_products.php> | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** | ✗ |
| <https://www.chinaccs.com.hk/sc/business/tis.php>, `bpo.php`, `business.php`, `digital_infrastructure.php`, <https://www.chinaccs.com.hk/sc/about/strategies.php> | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

**The only 卫星 hit on the corporate site** — <https://www.chinaccs.com.hk/sc/business/telecom_operator.php>, verbatim:
> 「公司拥有丰富的通信建设经验，为客户提供包括**固定网络、移动网络、卫星网络**在内的网络规划，提供固定及
> 移动业务市场咨询、业务咨询、管理咨询等各种专业咨询服务…」

**News headlines 2024–2026 (verbatim, from the opened news pages)** — none concerns emergency
communications, satellites, or geological disaster. FY2025/2026 items are: 「公布2026年中期业绩」,
「公布2025年全年业绩」, 「公布2025年中期业绩」, 「公布2024年全年业绩」, 「人工智能创新成果亮相北京科博会」,
「获《Corporate Governance Asia》颁发「亚洲可持续发展奖」」, 「连续五年在《Extel》获评选为「最受尊崇企业」」,
「荣获第十七届中国数据中心大会多项大奖」, 「建成全球最长百公里级空芯光缆干线」, 「全球首个风电海底数据中心正式落成」,
「三江源国家大数据基地」, 「在「2025中国软件百强」排名提升至第三名」, index-inclusion notices.

**Results press releases (opened, full text grepped) — keyword hits:**
- `p250327` (FY2024 results, 2025-03-27): 卫星通信 ✓, 「星極通」 ✓ (verbatim in §7d), 应急安全 ✓, 物联网 ✓, **应急通信 ✗**
- `p250821` (H1 2025 results): 应急安全 ✓, 物联网 ✓, **卫星 ✗**
- `p260331` (FY2025 results, 2026-03-31): **卫星互联网 ✓** (「投身通智超算、5G-A、卫星互联网、低空等新型基础设施建设」), 应急安全 ✓, 物联网 ✓
- `p260826` (H1 2026 results, 2026-08-26): 应急 ✓ (incl. 「「靈空」低空应急实战应用平台」), **卫星 ✗**

---

## 9. "Could not verify" / limitations

1. **CCS site search is unusable programmatically.** `/sc/global/search.php?q=…` returns only the navigation
   menu for every query (client-side/Google-CSE rendered, `ir-gcs-*` classes). Therefore the §8 table reflects
   **the specific pages I fetched**, not an exhaustive site-wide search. A page I did not fetch might contain
   a given keyword.
2. **gov.cn direct `curl` is blocked** (`http=000`, 0 bytes). All gov.cn text was obtained through the Jina
   Reader proxy. The MIIT article URL `…/art_80059e80ee8b4e659168ab1eebb41cc4.html` returned rate-limit 429
   via the proxy; I substituted the **MIIT mobile mirror** (`wap.miit.gov.cn`, same 文章 id family), whose text
   matches gov.cn. I could not read the desktop MIIT page itself.
3. **No exact gov.cn "发布日期" field was read.** gov.cn pages carry 索引号/成文日期/发布日期 metadata in HTML,
   but since direct curl was blocked I only have: document date **2024-12-31**, gov.cn folder **202501**,
   interpretation timestamp **2025-01-21**, Xinhua report **2025-01-22**. I did not fabricate a precise date.
4. **No complete subsidiary register.** The FY2025 AR note 47 lists only "若干子公司" (selected subsidiaries).
   The full list of CCS subsidiaries is **not** in the annual report and was not obtained. The corporate
   group-structure page <https://www.chinaccs.com.hk/sc/about/gp_structure.php> was **not** opened by me
   (a sibling agent's file `gp_structure.md` exists in the scratch dir; I did not rely on it).
5. **`ar2026.php` (linked from the reports listing as the 年报) returns 404.** I used `ar2025.php`
   (labelled 2025 年报). If CCS intends `ar2026` to be a distinct FY2026 annual report, it is not yet published.
6. **No simplified-Chinese PDF edition exists** (`/sc/.../ar2025.pdf` → 404), so every Chinese quote here is
   **Traditional** Chinese as printed. Simplified equivalents are my normalisations for the search only.
7. **`file` reported "15 page(s)" for `ir2026.pdf` while PyMuPDF extracted 47 pages.** PyMuPDF's count (47,
   matching 14 PDF fragments + body) is the one I used; the discrepancy is a `file(1)` heuristic artefact.
8. **No CCS/subsidiary response to the 14-ministry policy was found** — this is a **negative finding over the
   sources I could reach**, not proof of non-existence. Company WeChat/微信公众号, provincial subsidiary sites,
   and 招标/中标 databases were not systematically searched. One search returned a subsidiary procurement
   notice (`中通服科信信息技术有限公司`, <https://sczb.chinaccsscm.cn/zbgg/451737.jhtml>) — **snippet-only,
   unopened**, and it concerns a management-IT O&M project, not emergency communications.
9. **`地質災害` is genuinely absent** from all four reports (0 hits exact and whitespace-normalised).
   Do **not** report that the annual report discusses 地质灾害; report the actual wording:
   山體滑坡 / 泥石流 / 崩塌 / 暴雨 / 洪澇 / 颱風 / 地震.

---

## 10. Local files produced (all under `（已清理的临时工作目录）/`)

Reports: `pdf/ar2025.pdf`, `pdf/ar2025_en.pdf`, `pdf/ar2024.pdf`, `pdf/ir2026.pdf`, `pdf/ir2025.pdf`,
`pdf/p250327.pdf`, `pdf/p250821.pdf`, `pdf/p260331.pdf`, `pdf/p260826.pdf`
Text: `txt_ar2025.txt`, `txt_ar2025_en.txt`, `txt_ar2024.txt`, `txt_ir2026.txt`, `txt_ir2025.txt`,
`txt_p250327.txt`, `txt_p250821.txt`, `txt_p260331.txt`, `txt_p260826.txt`
Policy: `pol_govcn.md` (gov.cn full text), `pol_miit2.md` (MIIT mirror), `pol_jiedu.md` (official 解读)
Site pages: `ar_reports_sc.md`, `ar_reports_en.md`, `ar_news*.md`, `ar_biz_*.md`, `ar_strategies.md`, `raw_*.html`
Tools: `extract.py` (PyMuPDF extractor), `ctx.py` (keyword+page context), `f.sh` (Jina fetch/cache)
