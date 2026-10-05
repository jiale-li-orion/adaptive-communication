# Layer-1 Q11 Human / Source Review Packet v0.1

状态：**BLOCKED_PENDING_HUMAN_REVIEW**

机器预审：23 / 23 MACHINE_PASS；机器预审不能替代 reviewer 签字。

人工 reviewer 对每条只需要判断五项：source extraction、authority/time、task identity、oracle success set、evaluator trace。任何 FAIL 都阻塞 Q11。

## HSA-0000 · `T1R-1ef09368b57702`

- split / role: `dev` / `EASY_CONFORMANCE_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::2419d35e2fbe::report-7200s`
- geometry cluster: `GC01`
- hardness: `H0_CONFORMANCE`, `H1_PARTIAL_OBSERVATION`, `H_RECOVERY_OBJECTIVE_CHECK`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `3`, warning `orange`, report interval `7200s`
- exact role check: expected `NO_PAID_QUERY_REQUIRED`, actual `NO_PAID_QUERY_REQUIRED`
- evaluator replay: `1` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None
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

## HSA-0001 · `T1R-29d924c7203e33`

- split / role: `dev` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::2419d35e2fbe::report-14400s`
- geometry cluster: `GC01`
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
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None
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

## HSA-0002 · `T1R-fcc7e282abdb5a`

- split / role: `dev` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0007::55cea7f8f110::report-43200s`
- geometry cluster: `GC01`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `2`, warning `yellow`, report interval `43200s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `3` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None
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

## HSA-0003 · `T1R-613beb48b8c6e4`

- split / role: `dev` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::2419d35e2fbe::report-14400s`
- geometry cluster: `GC01`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `3`, warning `orange`, report interval `14400s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `4` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None
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

## HSA-0004 · `T1R-59915e15b6d5dc`

- split / role: `dev` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0001::3a1861bbd0be::report-43200s`
- geometry cluster: `GC01`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`, `H_RECOVERY_OBJECTIVE_CHECK`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `1`, warning `blue`, report interval `43200s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `4` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None
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

## HSA-0005 · `T1R-207d57c0d5392e`

- split / role: `dev` / `INFORMATION_INFEASIBLE_DIAGNOSTIC`
- task: `DB44T2457_2024_warning_reporting::nominal::0009::7a5ac9acae95::report-300s`
- geometry cluster: `GC01`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `2`, warning `red`, report interval `300s`
- exact role check: expected `INFORMATION_INFEASIBLE`, actual `INFORMATION_INFEASIBLE`
- V0–V7: expected `INFORMATION_INFEASIBLE_DIAGNOSTIC`, actual `INFORMATION_INFEASIBLE_DIAGNOSTIC`
- evaluator replay: `3` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None
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

## HSA-0006 · `T1R-5e36e5660953db`

- split / role: `dev` / `NEGATIVE_PHYSICAL_INVALID_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0008::2fd79162efe3::report-7200s`
- geometry cluster: `GC01`
- hardness: `H0_NEGATIVE_SHORTCUT_REGRESSION`, `H2_EVIDENCE_VALUE`, `H5_PASSIVE_PROBE_QUERY_COMPETITION`, `H_RECOVERY_OBJECTIVE_CHECK`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `2`, warning `orange`, report interval `7200s`
- exact role check: expected `MIXED_WORLD_SOLVABILITY`, actual `MIXED_WORLD_SOLVABILITY`
- V0–V7: expected `V1_PHYSICAL_INVALID`, actual `V1_PHYSICAL_INVALID`
- evaluator replay: `2` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None
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

## HSA-0007 · `T1R-0a1ff07772e2b0`

- split / role: `dev` / `NEGATIVE_SHORTCUT_REGRESSION_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0007::55cea7f8f110::report-43200s`
- geometry cluster: `GC01`
- hardness: `H0_NEGATIVE_SHORTCUT_REGRESSION`, `H1_PARTIAL_OBSERVATION`, `H_RECOVERY_OBJECTIVE_CHECK`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `2`, warning `yellow`, report interval `43200s`
- exact role check: expected `NO_PAID_QUERY_REQUIRED`, actual `NO_PAID_QUERY_REQUIRED`
- evaluator replay: `3` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None
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

## HSA-0008 · `T1R-f2fd67153d58b5`

- split / role: `test` / `EASY_CONFORMANCE_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::152410c16ef5::report-3600s`
- geometry cluster: `GC03`
- hardness: `H0_CONFORMANCE`, `H1_PARTIAL_OBSERVATION`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `1`, warning `orange`, report interval `3600s`
- exact role check: expected `NO_PAID_QUERY_REQUIRED`, actual `NO_PAID_QUERY_REQUIRED`
- evaluator replay: `1` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0009 · `T1R-29b53ee4ef4eff`

- split / role: `test` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0001::3a1861bbd0be::report-21600s`
- geometry cluster: `GC03`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`, `H_RECOVERY_OBJECTIVE_CHECK`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `1`, warning `blue`, report interval `21600s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `4` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None
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

## HSA-0010 · `T1R-50eef0057756f2`

- split / role: `test` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::152410c16ef5::report-1800s`
- geometry cluster: `GC03`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `1`, warning `orange`, report interval `1800s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `4` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None
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

## HSA-0011 · `T1R-5cadeb237df289`

- split / role: `test` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::152410c16ef5::report-1800s`
- geometry cluster: `GC03`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`, `H_RECOVERY_OBJECTIVE_CHECK`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `1`, warning `orange`, report interval `1800s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `4` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None
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

## HSA-0012 · `T1R-9ed74038ac2596`

- split / role: `test` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0006::5e24bc254aa5::report-43200s`
- geometry cluster: `GC03`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`, `H_RECOVERY_OBJECTIVE_CHECK`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `2`, warning `blue`, report interval `43200s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `4` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None
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

## HSA-0013 · `T1R-51d81c210de14b`

- split / role: `test` / `INFORMATION_INFEASIBLE_DIAGNOSTIC`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::2419d35e2fbe::report-7200s`
- geometry cluster: `GC03`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`, `H_RECOVERY_OBJECTIVE_CHECK`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `3`, warning `orange`, report interval `7200s`
- exact role check: expected `INFORMATION_INFEASIBLE`, actual `INFORMATION_INFEASIBLE`
- V0–V7: expected `INFORMATION_INFEASIBLE_DIAGNOSTIC`, actual `INFORMATION_INFEASIBLE_DIAGNOSTIC`
- evaluator replay: `3` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None
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

## HSA-0014 · `T1R-86e5daef4c6421`

- split / role: `test` / `NEGATIVE_SHORTCUT_REGRESSION_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::2419d35e2fbe::report-14400s`
- geometry cluster: `GC03`
- hardness: `H0_NEGATIVE_SHORTCUT_REGRESSION`, `H2_EVIDENCE_VALUE`, `H5_PASSIVE_PROBE_QUERY_COMPETITION`, `H_RECOVERY_OBJECTIVE_CHECK`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `3`, warning `orange`, report interval `14400s`
- exact role check: expected `NO_PAID_QUERY_REQUIRED`, actual `NO_PAID_QUERY_REQUIRED`
- evaluator replay: `3` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None
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

## HSA-0015 · `T1R-da48567dda0440`

- split / role: `train` / `EASY_CONFORMANCE_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0002::a832cc7beb0d::report-10800s`
- geometry cluster: `GC02`
- hardness: `H0_CONFORMANCE`, `H2_EVIDENCE_VALUE`, `H5_PASSIVE_PROBE_QUERY_COMPETITION`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `1`, warning `yellow`, report interval `10800s`
- exact role check: expected `NO_PAID_QUERY_REQUIRED`, actual `NO_PAID_QUERY_REQUIRED`
- evaluator replay: `1` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None

Reviewer:

- [ ] source extraction semantics PASS   - [ ] FAIL
- [ ] authority / priority / time semantics PASS   - [ ] FAIL
- [ ] task family identity PASS   - [ ] FAIL
- [ ] oracle success set PASS   - [ ] FAIL
- [ ] evaluator trace PASS   - [ ] FAIL
- reviewer name:
- notes:

## HSA-0016 · `T1R-001fd762a44e32`

- split / role: `train` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0012::dd7553cdd485::report-43200s`
- geometry cluster: `GC00`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`, `H_RECOVERY_OBJECTIVE_CHECK`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `3`, warning `yellow`, report interval `43200s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `3` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None
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

## HSA-0017 · `T1R-3b74a62968870b`

- split / role: `train` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0012::dd7553cdd485::report-43200s`
- geometry cluster: `GC00`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `3`, warning `yellow`, report interval `43200s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `4` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None
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

## HSA-0018 · `T1R-8f26b1a17a234c`

- split / role: `train` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::2419d35e2fbe::report-14400s`
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
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None
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

## HSA-0019 · `T1R-5a323efa2067a1`

- split / role: `train` / `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::152410c16ef5::report-1800s`
- geometry cluster: `GC00`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `1`, warning `orange`, report interval `1800s`
- exact role check: expected `PAID_EVIDENCE_REQUIRED`, actual `PAID_EVIDENCE_REQUIRED`
- V0–V7: expected `V0_V7_PASS`, actual `V0_V7_PASS`
- V8: expected `SURVIVES_V8_LADDER_V0_1`, actual `SURVIVES_V8_LADDER_V0_1`
- evaluator replay: `4` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None
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

## HSA-0020 · `T1R-8f4758ed53df06`

- split / role: `train` / `INFORMATION_INFEASIBLE_DIAGNOSTIC`
- task: `DB44T2457_2024_warning_reporting::nominal::0014::b5b856e65fba::report-300s`
- geometry cluster: `GC00`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `3`, warning `red`, report interval `300s`
- exact role check: expected `INFORMATION_INFEASIBLE`, actual `INFORMATION_INFEASIBLE`
- V0–V7: expected `INFORMATION_INFEASIBLE_DIAGNOSTIC`, actual `INFORMATION_INFEASIBLE_DIAGNOSTIC`
- evaluator replay: `4` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None
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

## HSA-0021 · `T1R-98a1a3100970b5`

- split / role: `train` / `NEGATIVE_PHYSICAL_INVALID_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::2419d35e2fbe::report-7200s`
- geometry cluster: `GC02`
- hardness: `H0_NEGATIVE_SHORTCUT_REGRESSION`, `H1_PARTIAL_OBSERVATION`, `H_RECOVERY_OBJECTIVE_CHECK`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `3`, warning `orange`, report interval `7200s`
- exact role check: expected `MIXED_WORLD_SOLVABILITY`, actual `MIXED_WORLD_SOLVABILITY`
- V0–V7: expected `V1_PHYSICAL_INVALID`, actual `V1_PHYSICAL_INVALID`
- evaluator replay: `2` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None
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

## HSA-0022 · `T1R-72cd0a92273f8d`

- split / role: `train` / `NEGATIVE_SHORTCUT_REGRESSION_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0012::dd7553cdd485::report-43200s`
- geometry cluster: `GC00`
- hardness: `H0_NEGATIVE_SHORTCUT_REGRESSION`, `H1_PARTIAL_OBSERVATION`, `H_RECOVERY_OBJECTIVE_CHECK`
- machine groups: `authority_priority_time_semantics=MACHINE_PASS`, `evaluator_trace=MACHINE_PASS`, `oracle_success_set=MACHINE_PASS`, `source_extraction_semantics=MACHINE_PASS`, `task_family_identity=MACHINE_PASS`
- source-expanded task: grade `3`, warning `yellow`, report interval `43200s`
- exact role check: expected `NO_PAID_QUERY_REQUIRED`, actual `NO_PAID_QUERY_REQUIRED`
- evaluator replay: `2` solvable world witness(es), machine failures `0`
- source evidence:
  - `DB11T1677_2019_rainfall_dual_path` — DB11T1677_2019 [LOCAL_STANDARD] locator='rainfall monitoring clauses' snapshot=None
    - unresolved/source gaps to inspect: `[{"answer_relevant": true, "field": "communication_completion_semantics", "reason": "Acquisition cadence cannot be silently reinterpreted as communication-delivery deadline."}]`
  - `DB44T2457_2024_warning_reporting` — DB44T2457_2024 [LOCAL_STANDARD] locator='warning-level reporting frequency table' snapshot=None
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

