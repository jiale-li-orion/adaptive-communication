# DB44/T 2457-2024 · landslide reporting cadence evidence

用途：`DB44T2457_2024_warning_reporting` 的 T1 reporting task authority。该 profile 只使用 **滑坡（landslide）** 自动化监测数据上报频率，不再把其他地质灾害类型的表格混入同一 cadence table。

## Source identity

- Standard: `DB44/T 2457-2024 地质灾害自动化监测规范`
- Issued: 2024-01-17; effective: 2024-04-17
- Competent authority: 广东省市场监督管理局
- Technical owner: 广东省自然资源厅
- Official metadata: `https://std.samr.gov.cn/db/search/stdDBDetailed?id=1246284D0D1733D1E06397BE0A0A569F`
- Public full-text copy used for page-level verification: `https://qxb-img-osscache.qixin.com/standards/baa686084442d07ae4895ca8d10baed9.pdf`
- Locator: §9.2.2.2, Table 11, PDF printed page 21 (`滑坡自动化监测数据上报频率建议值`)

The official metadata confirms that the standard covers landslide, collapse, debris flow, ground collapse, land subsidence and ground fissure. §9.2.2 states that reporting frequency depends on **geohazard type**, monitoring grade and warning grade. Therefore the hazard type is part of the source-table identity and cannot be omitted when selecting a cadence table.

## Table 11 values used by the profile

Columns are: stable/no warning, warning level IV, III, II, I.

| Monitoring grade | Stable | IV | III | II | I |
| --- | --- | --- | --- | --- | --- |
| 1 | 1–3 d | 6–12 h | 4–6 h | 30–60 min | 5 min |
| 2 | 3–5 d | 12–24 h | 6–12 h | 1–2 h | 5 min |
| 3 | 5–7 d | 1–2 d | 12–24 h | 2–4 h | 5 min |

Benchmark warning-state mapping remains:

```text
none_stable → stable/no warning
blue        → warning level IV
yellow      → warning level III
orange      → warning level II
red         → warning level I
```

Range-valued cells are still expanded only at their lower/upper source boundaries; no midpoint or probability distribution is invented.

## Correction note

The pre-release profile before 2026-10-05 accidentally encoded the values from **Table 15 (ground fissure)** while naming the profile generically as warning reporting. Q11 source review exposed this mismatch before `BENCHMARK_ADMIT`. The corrected profile fixes `hazard_type=landslide` and uses Table 11. All downstream recipes, exact labels, V0–V9, held-out split, frozen-test baselines and release digests must be regenerated before Q11 can be signed.

This file is a reviewer evidence index, not a replacement for the cited standard text.
