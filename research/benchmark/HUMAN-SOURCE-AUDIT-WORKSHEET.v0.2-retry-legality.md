# Layer-1 Human / Source Audit Worksheet v0.2-retry-legality

状态：PENDING_HUMAN_REVIEW
样本数：23

每条样本必须由 reviewer 独立核查 source extraction、authority/time semantics、task identity、oracle success set 与 evaluator trace。自动脚本不能替代此签字。

## DEV

### HSA-0000 · `T1R-a1295b6f3c146b`

- role: `EASY_CONFORMANCE_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::46c99c7a49e4::report-7200s`
- geometry cluster: `GC03`
- source profiles: `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`
- hardness: `H0_CONFORMANCE`, `H2_EVIDENCE_VALUE`, `H5_PASSIVE_PROBE_QUERY_COMPETITION`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0001 · `T1R-dd653c5b4117f6`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::56161eba62b8::report-1800s`
- geometry cluster: `GC03`
- source profiles: `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`, `H_RECOVERY_OBJECTIVE_CHECK`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0002 · `T1R-ad0061f4abe2a1`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::46c99c7a49e4::report-7200s`
- geometry cluster: `GC03`
- source profiles: `DB11T1677_2019_rainfall_dual_path`, `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0003 · `T1R-1633518233e031`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::56161eba62b8::report-1800s`
- geometry cluster: `GC03`
- source profiles: `DB11T1677_2019_rainfall_dual_path`, `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0004 · `T1R-9ef27807351744`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0002::feba66297460::report-21600s`
- geometry cluster: `GC03`
- source profiles: `DB11T1677_2019_rainfall_dual_path`, `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`, `H_RECOVERY_OBJECTIVE_CHECK`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0005 · `T1R-871a3f9cefc2c9`

- role: `INFORMATION_INFEASIBLE_DIAGNOSTIC`
- task: `DB44T2457_2024_warning_reporting::nominal::0009::eac754b31cb2::report-300s`
- geometry cluster: `GC03`
- source profiles: `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0006 · `T1R-bbced2d31a0588`

- role: `NEGATIVE_SHORTCUT_REGRESSION_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::56161eba62b8::report-1800s`
- geometry cluster: `GC03`
- source profiles: `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H0_NEGATIVE_SHORTCUT_REGRESSION`, `H1_PARTIAL_OBSERVATION`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

## TEST

### HSA-0007 · `T1R-b8fa9bc1accc27`

- role: `EASY_CONFORMANCE_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::56161eba62b8::report-3600s`
- geometry cluster: `GC01`
- source profiles: `DB11T1677_2019_rainfall_dual_path`, `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`
- hardness: `H0_CONFORMANCE`, `H1_PARTIAL_OBSERVATION`, `H_RECOVERY_OBJECTIVE_CHECK`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0008 · `T1R-fdc88203b35be1`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::56161eba62b8::report-1800s`
- geometry cluster: `GC01`
- source profiles: `DB11T1677_2019_rainfall_dual_path`, `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0009 · `T1R-9b9b706eae299b`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::56161eba62b8::report-1800s`
- geometry cluster: `GC01`
- source profiles: `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0010 · `T1R-09a43ac75247b9`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::56161eba62b8::report-1800s`
- geometry cluster: `GC01`
- source profiles: `DB11T1677_2019_rainfall_dual_path`, `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`, `H_RECOVERY_OBJECTIVE_CHECK`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0011 · `T1R-fcd67ebe4023cb`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::46c99c7a49e4::report-14400s`
- geometry cluster: `GC01`
- source profiles: `DB11T1677_2019_rainfall_dual_path`, `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`, `H_RECOVERY_OBJECTIVE_CHECK`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0012 · `T1R-57d386577f7c08`

- role: `INFORMATION_INFEASIBLE_DIAGNOSTIC`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::46c99c7a49e4::report-7200s`
- geometry cluster: `GC01`
- source profiles: `DB11T1677_2019_rainfall_dual_path`, `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`, `H_RECOVERY_OBJECTIVE_CHECK`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0013 · `T1R-c3a3e615c26492`

- role: `NEGATIVE_PHYSICAL_INVALID_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::56161eba62b8::report-3600s`
- geometry cluster: `GC01`
- source profiles: `DB11T1677_2019_rainfall_dual_path`, `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H0_NEGATIVE_SHORTCUT_REGRESSION`, `H2_EVIDENCE_VALUE`, `H5_PASSIVE_PROBE_QUERY_COMPETITION`, `H_RECOVERY_OBJECTIVE_CHECK`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0014 · `T1R-b4c1f4ecdbe898`

- role: `NEGATIVE_SHORTCUT_REGRESSION_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0006::ed7d8abe7c43::report-43200s`
- geometry cluster: `GC01`
- source profiles: `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H0_NEGATIVE_SHORTCUT_REGRESSION`, `H2_EVIDENCE_VALUE`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

## TRAIN

### HSA-0015 · `T1R-b63a903c62e083`

- role: `EASY_CONFORMANCE_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::46c99c7a49e4::report-7200s`
- geometry cluster: `GC00`
- source profiles: `DB44T2457_2024_warning_reporting`
- hardness: `H0_CONFORMANCE`, `H1_PARTIAL_OBSERVATION`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0016 · `T1R-c79be1a0612bad`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::56161eba62b8::report-1800s`
- geometry cluster: `GC00`
- source profiles: `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0017 · `T1R-4ed0d40ca03dc9`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::56161eba62b8::report-1800s`
- geometry cluster: `GC00`
- source profiles: `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0018 · `T1R-8412f71c6bf26b`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::46c99c7a49e4::report-14400s`
- geometry cluster: `GC00`
- source profiles: `DB11T1677_2019_rainfall_dual_path`, `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0019 · `T1R-9dbe48a1428fcc`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::46c99c7a49e4::report-14400s`
- geometry cluster: `GC00`
- source profiles: `DB11T1677_2019_rainfall_dual_path`, `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`, `H_RECOVERY_OBJECTIVE_CHECK`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0020 · `T1R-f2549b6152bcc1`

- role: `INFORMATION_INFEASIBLE_DIAGNOSTIC`
- task: `DB44T2457_2024_warning_reporting::nominal::0009::eac754b31cb2::report-300s`
- geometry cluster: `GC00`
- source profiles: `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H2_EVIDENCE_VALUE`, `H3_SHARED_RESOURCE_CONFLICT`, `H4_COUPLED_SEQUENTIAL_COMMITMENT`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0021 · `T1R-e08fbf74daf43a`

- role: `NEGATIVE_PHYSICAL_INVALID_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::46c99c7a49e4::report-7200s`
- geometry cluster: `GC02`
- source profiles: `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H0_NEGATIVE_SHORTCUT_REGRESSION`, `H1_PARTIAL_OBSERVATION`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0022 · `T1R-351eb88e144efb`

- role: `NEGATIVE_SHORTCUT_REGRESSION_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0002::feba66297460::report-14400s`
- geometry cluster: `GC00`
- source profiles: `DB11T1677_2019_rainfall_dual_path`, `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H0_NEGATIVE_SHORTCUT_REGRESSION`, `H2_EVIDENCE_VALUE`, `H5_PASSIVE_PROBE_QUERY_COMPETITION`, `H_RECOVERY_OBJECTIVE_CHECK`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:
