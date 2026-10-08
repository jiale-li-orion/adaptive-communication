# DB11/T 1677-2019 · rainfall monitoring evidence

用途：`DB11T1677_2019_rainfall_dual_path` 的 rainfall monitoring / dual-path / endurance authority index。

## Source identity

- Standard: `DB11/T 1677-2019 地质灾害监测技术规范`
- Issued: 2019-12-25
- Effective: 2020-07-01
- Competent authority / technical owner: 北京市规划和自然资源委员会
- Publishing / supervising authority: 北京市市场监督管理局
- Official standard metadata: `https://std.samr.gov.cn/db/search/stdDBDetailedCNF?id=9B75BDF9C24591B2E05397BE0A0A59E9`
- Official Beijing full-text PDF: `https://ghzrzyw.beijing.gov.cn/biaozhunguanli/bz/gtzy/202011/P020201105397976267685.pdf`
- Relevant locator: §5.2.12 rainfall automated monitoring requirements

## Verified clauses used by the profile

§5.2.12 specifies automated rainfall monitoring and states:

- collected information includes rainfall, collection time, upload time, transmission mode, real-time battery voltage, ambient temperature and signal strength;
- during rainfall, monitoring frequency is at least once every `5 min`;
- without rainfall, monitoring frequency is at least once every `2 h`;
- data transmission should use a `GPRS + BeiDou` dual-channel mode;
- under no sunlight and a 5-minute transmission frequency, a single GPRS path should operate normally for at least `15 d`, while a single BeiDou path should operate normally for at least `7 d`.

These clauses support the current profile values:

```text
dry_max_acquisition_interval_s = 7200
rain_max_acquisition_interval_s = 300
communication_classes = {GPRS, BeiDou}
gprs_no_sun_endurance_days_at_5min = 15
beidou_no_sun_endurance_days_at_5min = 7
observed_device_fields includes battery voltage / signal strength / upload time / transmission mode
```

## Explicit boundary

The standard gives **monitoring/acquisition frequency** and transport/device capability. It does not define a general upper-platform communication-delivery deadline for this profile.

Therefore `communication_completion_semantics` remains `UNRESOLVED` and answer-relevant. The benchmark may not silently reinterpret the 5 min / 2 h acquisition cadence as a delivery deadline.

This file is an evidence index for reviewer reproducibility, not a substitute for the cited official standard text.
