# Layer-1 Q11 Human / Source Review Packet v0.2-retry-legality

状态：**BLOCKED_PENDING_HUMAN_REVIEW**

机器预审：23 / 23 MACHINE_PASS；机器预审不能替代 reviewer 签字。

人工 reviewer 对每条只需要判断五项：source extraction、authority/time、task identity、oracle success set、evaluator trace。任何 FAIL 都阻塞 Q11。

## HSA-0000 · `T1R-a1295b6f3c146b`

- split / role: `dev` / `EASY_CONFORMANCE_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::46c99c7a49e4::report-7200s`
- geometry cluster: `GC03`
- hardness: `H0_CONFORMANCE`, `H2_EVIDENCE_VALUE`, `H5_PASSIVE_PROBE_QUERY_COMPETITION`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `3`, warning `orange`, report interval `7200s`
- exact role check: expected `NO_PAID_QUERY_REQUIRED`, actual `NO_PAID_QUERY_REQUIRED`
- evaluator replay: `1` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0001 · `T1R-dd653c5b4117f6`

- split / role: `dev` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::56161eba62b8::report-1800s`
- geometry cluster: `GC03`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`, `H_RECOVERY_OBJECTIVE_CHECK`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `1`, warning `orange`, report interval `1800s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `4` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`
  - `JIAOZUO_2024_geohazard_monitoring_deployment` — JIAOZUO_2024 [GOVERNMENT_PROCUREMENT] locator=None snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/field-cases/jiaozuo-geohazard-monitoring-procurement-2024.remote.md'

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0002 · `T1R-ad0061f4abe2a1`

- split / role: `dev` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::46c99c7a49e4::report-7200s`
- geometry cluster: `GC03`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `3`, warning `orange`, report interval `7200s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `4` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`
  - `JIAOZUO_2024_geohazard_monitoring_deployment` — JIAOZUO_2024 [GOVERNMENT_PROCUREMENT] locator=None snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/field-cases/jiaozuo-geohazard-monitoring-procurement-2024.remote.md'

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0003 · `T1R-1633518233e031`

- split / role: `dev` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::56161eba62b8::report-1800s`
- geometry cluster: `GC03`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `1`, warning `orange`, report interval `1800s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `4` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`
  - `JIAOZUO_2024_geohazard_monitoring_deployment` — JIAOZUO_2024 [GOVERNMENT_PROCUREMENT] locator=None snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/field-cases/jiaozuo-geohazard-monitoring-procurement-2024.remote.md'

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0004 · `T1R-9ef27807351744`

- split / role: `dev` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0002::feba66297460::report-21600s`
- geometry cluster: `GC03`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`, `H_RECOVERY_OBJECTIVE_CHECK`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `1`, warning `yellow`, report interval `21600s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `4` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`
  - `JIAOZUO_2024_geohazard_monitoring_deployment` — JIAOZUO_2024 [GOVERNMENT_PROCUREMENT] locator=None snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/field-cases/jiaozuo-geohazard-monitoring-procurement-2024.remote.md'

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0005 · `T1R-871a3f9cefc2c9`

- split / role: `dev` / `INFORMATION_INFEASIBLE_DIAGNOSTIC`
- task: `DB44T2457_2024_warning_reporting::nominal::0009::eac754b31cb2::report-300s`
- geometry cluster: `GC03`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `2`, warning `red`, report interval `300s`
- exact role check: expected `INFORMATION_INFEASIBLE`, actual `INFORMATION_INFEASIBLE`
- V0–V7: expected `INFORMATION_INFEASIBLE_DIAGNOSTIC`, actual `INFORMATION_INFEASIBLE_DIAGNOSTIC`
- evaluator replay: `3` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`
  - `JIAOZUO_2024_geohazard_monitoring_deployment` — JIAOZUO_2024 [GOVERNMENT_PROCUREMENT] locator=None snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/field-cases/jiaozuo-geohazard-monitoring-procurement-2024.remote.md'

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0006 · `T1R-bbced2d31a0588`

- split / role: `dev` / `NEGATIVE_SHORTCUT_REGRESSION_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::56161eba62b8::report-1800s`
- geometry cluster: `GC03`
- hardness: `H0_NEGATIVE_SHORTCUT_REGRESSION`, `H1_PARTIAL_OBSERVATION`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `1`, warning `orange`, report interval `1800s`
- exact role check: expected `NO_PAID_QUERY_REQUIRED`, actual `NO_PAID_QUERY_REQUIRED`
- evaluator replay: `4` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`
  - `JIAOZUO_2024_geohazard_monitoring_deployment` — JIAOZUO_2024 [GOVERNMENT_PROCUREMENT] locator=None snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/field-cases/jiaozuo-geohazard-monitoring-procurement-2024.remote.md'

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0007 · `T1R-b8fa9bc1accc27`

- split / role: `test` / `EASY_CONFORMANCE_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::56161eba62b8::report-3600s`
- geometry cluster: `GC01`
- hardness: `H0_CONFORMANCE`, `H1_PARTIAL_OBSERVATION`, `H_RECOVERY_OBJECTIVE_CHECK`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `1`, warning `orange`, report interval `3600s`
- exact role check: expected `NO_PAID_QUERY_REQUIRED`, actual `NO_PAID_QUERY_REQUIRED`
- evaluator replay: `1` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0008 · `T1R-fdc88203b35be1`

- split / role: `test` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::56161eba62b8::report-1800s`
- geometry cluster: `GC01`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `1`, warning `orange`, report interval `1800s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `3` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`
  - `JIAOZUO_2024_geohazard_monitoring_deployment` — JIAOZUO_2024 [GOVERNMENT_PROCUREMENT] locator=None snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/field-cases/jiaozuo-geohazard-monitoring-procurement-2024.remote.md'

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0009 · `T1R-9b9b706eae299b`

- split / role: `test` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::56161eba62b8::report-1800s`
- geometry cluster: `GC01`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `1`, warning `orange`, report interval `1800s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `3` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`
  - `JIAOZUO_2024_geohazard_monitoring_deployment` — JIAOZUO_2024 [GOVERNMENT_PROCUREMENT] locator=None snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/field-cases/jiaozuo-geohazard-monitoring-procurement-2024.remote.md'

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0010 · `T1R-09a43ac75247b9`

- split / role: `test` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::56161eba62b8::report-1800s`
- geometry cluster: `GC01`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`, `H_RECOVERY_OBJECTIVE_CHECK`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `1`, warning `orange`, report interval `1800s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `4` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`
  - `JIAOZUO_2024_geohazard_monitoring_deployment` — JIAOZUO_2024 [GOVERNMENT_PROCUREMENT] locator=None snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/field-cases/jiaozuo-geohazard-monitoring-procurement-2024.remote.md'

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0011 · `T1R-fcd67ebe4023cb`

- split / role: `test` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::46c99c7a49e4::report-14400s`
- geometry cluster: `GC01`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`, `H_RECOVERY_OBJECTIVE_CHECK`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `3`, warning `orange`, report interval `14400s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `3` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`
  - `JIAOZUO_2024_geohazard_monitoring_deployment` — JIAOZUO_2024 [GOVERNMENT_PROCUREMENT] locator=None snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/field-cases/jiaozuo-geohazard-monitoring-procurement-2024.remote.md'

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0012 · `T1R-57d386577f7c08`

- split / role: `test` / `INFORMATION_INFEASIBLE_DIAGNOSTIC`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::46c99c7a49e4::report-7200s`
- geometry cluster: `GC01`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`, `H_RECOVERY_OBJECTIVE_CHECK`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `3`, warning `orange`, report interval `7200s`
- exact role check: expected `INFORMATION_INFEASIBLE`, actual `INFORMATION_INFEASIBLE`
- V0–V7: expected `INFORMATION_INFEASIBLE_DIAGNOSTIC`, actual `INFORMATION_INFEASIBLE_DIAGNOSTIC`
- evaluator replay: `3` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`
  - `JIAOZUO_2024_geohazard_monitoring_deployment` — JIAOZUO_2024 [GOVERNMENT_PROCUREMENT] locator=None snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/field-cases/jiaozuo-geohazard-monitoring-procurement-2024.remote.md'

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0013 · `T1R-c3a3e615c26492`

- split / role: `test` / `NEGATIVE_PHYSICAL_INVALID_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::56161eba62b8::report-3600s`
- geometry cluster: `GC01`
- hardness: `H0_NEGATIVE_SHORTCUT_REGRESSION`, `H2_EVIDENCE_VALUE`, `H5_PASSIVE_PROBE_QUERY_COMPETITION`, `H_RECOVERY_OBJECTIVE_CHECK`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `1`, warning `orange`, report interval `3600s`
- exact role check: expected `MIXED_WORLD_SOLVABILITY`, actual `MIXED_WORLD_SOLVABILITY`
- V0–V7: expected `V1_PHYSICAL_INVALID`, actual `V1_PHYSICAL_INVALID`
- evaluator replay: `3` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`
  - `JIAOZUO_2024_geohazard_monitoring_deployment` — JIAOZUO_2024 [GOVERNMENT_PROCUREMENT] locator=None snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/field-cases/jiaozuo-geohazard-monitoring-procurement-2024.remote.md'

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0014 · `T1R-b4c1f4ecdbe898`

- split / role: `test` / `NEGATIVE_SHORTCUT_REGRESSION_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0006::ed7d8abe7c43::report-43200s`
- geometry cluster: `GC01`
- hardness: `H0_NEGATIVE_SHORTCUT_REGRESSION`, `H2_EVIDENCE_VALUE`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `2`, warning `blue`, report interval `43200s`
- exact role check: expected `NO_PAID_QUERY_REQUIRED`, actual `NO_PAID_QUERY_REQUIRED`
- evaluator replay: `2` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`
  - `JIAOZUO_2024_geohazard_monitoring_deployment` — JIAOZUO_2024 [GOVERNMENT_PROCUREMENT] locator=None snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/field-cases/jiaozuo-geohazard-monitoring-procurement-2024.remote.md'

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0015 · `T1R-b63a903c62e083`

- split / role: `train` / `EASY_CONFORMANCE_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::46c99c7a49e4::report-7200s`
- geometry cluster: `GC00`
- hardness: `H0_CONFORMANCE`, `H1_PARTIAL_OBSERVATION`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `3`, warning `orange`, report interval `7200s`
- exact role check: expected `NO_PAID_QUERY_REQUIRED`, actual `NO_PAID_QUERY_REQUIRED`
- evaluator replay: `1` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0016 · `T1R-c79be1a0612bad`

- split / role: `train` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::56161eba62b8::report-1800s`
- geometry cluster: `GC00`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `1`, warning `orange`, report interval `1800s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `4` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`
  - `JIAOZUO_2024_geohazard_monitoring_deployment` — JIAOZUO_2024 [GOVERNMENT_PROCUREMENT] locator=None snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/field-cases/jiaozuo-geohazard-monitoring-procurement-2024.remote.md'

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0017 · `T1R-4ed0d40ca03dc9`

- split / role: `train` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::56161eba62b8::report-1800s`
- geometry cluster: `GC00`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `1`, warning `orange`, report interval `1800s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `4` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`
  - `JIAOZUO_2024_geohazard_monitoring_deployment` — JIAOZUO_2024 [GOVERNMENT_PROCUREMENT] locator=None snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/field-cases/jiaozuo-geohazard-monitoring-procurement-2024.remote.md'

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0018 · `T1R-8412f71c6bf26b`

- split / role: `train` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::46c99c7a49e4::report-14400s`
- geometry cluster: `GC00`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `3`, warning `orange`, report interval `14400s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `3` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`
  - `JIAOZUO_2024_geohazard_monitoring_deployment` — JIAOZUO_2024 [GOVERNMENT_PROCUREMENT] locator=None snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/field-cases/jiaozuo-geohazard-monitoring-procurement-2024.remote.md'

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0019 · `T1R-9dbe48a1428fcc`

- split / role: `train` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::46c99c7a49e4::report-14400s`
- geometry cluster: `GC00`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`, `H_RECOVERY_OBJECTIVE_CHECK`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `3`, warning `orange`, report interval `14400s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `3` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`
  - `JIAOZUO_2024_geohazard_monitoring_deployment` — JIAOZUO_2024 [GOVERNMENT_PROCUREMENT] locator=None snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/field-cases/jiaozuo-geohazard-monitoring-procurement-2024.remote.md'

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0020 · `T1R-f2549b6152bcc1`

- split / role: `train` / `INFORMATION_INFEASIBLE_DIAGNOSTIC`
- task: `DB44T2457_2024_warning_reporting::nominal::0009::eac754b31cb2::report-300s`
- geometry cluster: `GC00`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `2`, warning `red`, report interval `300s`
- exact role check: expected `INFORMATION_INFEASIBLE`, actual `INFORMATION_INFEASIBLE`
- V0–V7: expected `INFORMATION_INFEASIBLE_DIAGNOSTIC`, actual `INFORMATION_INFEASIBLE_DIAGNOSTIC`
- evaluator replay: `4` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`
  - `JIAOZUO_2024_geohazard_monitoring_deployment` — JIAOZUO_2024 [GOVERNMENT_PROCUREMENT] locator=None snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/field-cases/jiaozuo-geohazard-monitoring-procurement-2024.remote.md'

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0021 · `T1R-e08fbf74daf43a`

- split / role: `train` / `NEGATIVE_PHYSICAL_INVALID_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::46c99c7a49e4::report-7200s`
- geometry cluster: `GC02`
- hardness: `H0_NEGATIVE_SHORTCUT_REGRESSION`, `H1_PARTIAL_OBSERVATION`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `3`, warning `orange`, report interval `7200s`
- exact role check: expected `MIXED_WORLD_SOLVABILITY`, actual `MIXED_WORLD_SOLVABILITY`
- V0–V7: expected `V1_PHYSICAL_INVALID`, actual `V1_PHYSICAL_INVALID`
- evaluator replay: `2` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`
  - `JIAOZUO_2024_geohazard_monitoring_deployment` — JIAOZUO_2024 [GOVERNMENT_PROCUREMENT] locator=None snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/field-cases/jiaozuo-geohazard-monitoring-procurement-2024.remote.md'

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0022 · `T1R-351eb88e144efb`

- split / role: `train` / `NEGATIVE_SHORTCUT_REGRESSION_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0002::feba66297460::report-14400s`
- geometry cluster: `GC00`
- hardness: `H0_NEGATIVE_SHORTCUT_REGRESSION`, `H2_EVIDENCE_VALUE`, `H5_PASSIVE_PROBE_QUERY_COMPETITION`, `H_RECOVERY_OBJECTIVE_CHECK`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `1`, warning `yellow`, report interval `14400s`
- exact role check: expected `NO_PAID_QUERY_REQUIRED`, actual `NO_PAID_QUERY_REQUIRED`
- evaluator replay: `3` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='9.2.2.2 / Table 11: landslide automated monitoring data reporting frequency' snapshot='research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md'
  - `DZT0450_2023_disconnect_recovery` — DZT0450_2023 [STANDARD] locator='6.3.2.5-7.4' snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt'
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "reconnect_backlog_priority", "reason": "no general priority/completion semantics yet"}]`
  - `JIAOZUO_2024_geohazard_monitoring_deployment` — JIAOZUO_2024 [GOVERNMENT_PROCUREMENT] locator=None snapshot='source_acquisition/field_evidence/china-geohazard-and-beidou/field-cases/jiaozuo-geohazard-monitoring-procurement-2024.remote.md'

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:
