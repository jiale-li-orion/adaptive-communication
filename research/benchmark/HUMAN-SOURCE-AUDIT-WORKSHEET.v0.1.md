# Layer-1 Human / Source Audit Worksheet v0.1

状态：PENDING_HUMAN_REVIEW
样本数：23

每条样本必须由 reviewer 独立核查 source extraction、authority/time semantics、task identity、oracle success set 与 evaluator trace。自动脚本不能替代此签字。

## DEV

### HSA-0000 · `T1R-1ef09368b57702`

- role: `EASY_CONFORMANCE_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::2419d35e2fbe::report-7200s`
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

### HSA-0001 · `T1R-29d924c7203e33`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::2419d35e2fbe::report-14400s`
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

### HSA-0002 · `T1R-fcc7e282abdb5a`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0007::55cea7f8f110::report-43200s`
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

### HSA-0003 · `T1R-613beb48b8c6e4`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::2419d35e2fbe::report-14400s`
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

### HSA-0004 · `T1R-59915e15b6d5dc`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0001::3a1861bbd0be::report-43200s`
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

### HSA-0005 · `T1R-207d57c0d5392e`

- role: `INFORMATION_INFEASIBLE_DIAGNOSTIC`
- task: `DB44T2457_2024_warning_reporting::nominal::0009::7a5ac9acae95::report-300s`
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

### HSA-0006 · `T1R-5e36e5660953db`

- role: `NEGATIVE_PHYSICAL_INVALID_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0008::2fd79162efe3::report-7200s`
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

### HSA-0007 · `T1R-0a1ff07772e2b0`

- role: `NEGATIVE_SHORTCUT_REGRESSION_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0007::55cea7f8f110::report-43200s`
- geometry cluster: `GC01`
- source profiles: `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H0_NEGATIVE_SHORTCUT_REGRESSION`, `H1_PARTIAL_OBSERVATION`, `H_RECOVERY_OBJECTIVE_CHECK`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

## TEST

### HSA-0008 · `T1R-f2fd67153d58b5`

- role: `EASY_CONFORMANCE_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::152410c16ef5::report-3600s`
- geometry cluster: `GC03`
- source profiles: `DB44T2457_2024_warning_reporting`
- hardness: `H0_CONFORMANCE`, `H1_PARTIAL_OBSERVATION`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0009 · `T1R-29b53ee4ef4eff`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0001::3a1861bbd0be::report-21600s`
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

### HSA-0010 · `T1R-50eef0057756f2`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::152410c16ef5::report-1800s`
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

### HSA-0011 · `T1R-5cadeb237df289`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::152410c16ef5::report-1800s`
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

### HSA-0012 · `T1R-9ed74038ac2596`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0006::5e24bc254aa5::report-43200s`
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

### HSA-0013 · `T1R-51d81c210de14b`

- role: `INFORMATION_INFEASIBLE_DIAGNOSTIC`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::2419d35e2fbe::report-7200s`
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

### HSA-0014 · `T1R-86e5daef4c6421`

- role: `NEGATIVE_SHORTCUT_REGRESSION_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::2419d35e2fbe::report-14400s`
- geometry cluster: `GC03`
- source profiles: `DB11T1677_2019_rainfall_dual_path`, `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H0_NEGATIVE_SHORTCUT_REGRESSION`, `H2_EVIDENCE_VALUE`, `H5_PASSIVE_PROBE_QUERY_COMPETITION`, `H_RECOVERY_OBJECTIVE_CHECK`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

## TRAIN

### HSA-0015 · `T1R-da48567dda0440`

- role: `EASY_CONFORMANCE_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0002::a832cc7beb0d::report-10800s`
- geometry cluster: `GC02`
- source profiles: `DB11T1677_2019_rainfall_dual_path`, `DB44T2457_2024_warning_reporting`
- hardness: `H0_CONFORMANCE`, `H2_EVIDENCE_VALUE`, `H5_PASSIVE_PROBE_QUERY_COMPETITION`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0016 · `T1R-001fd762a44e32`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0012::dd7553cdd485::report-43200s`
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

### HSA-0017 · `T1R-3b74a62968870b`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0012::dd7553cdd485::report-43200s`
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

### HSA-0018 · `T1R-8f26b1a17a234c`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::2419d35e2fbe::report-14400s`
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

### HSA-0019 · `T1R-5a323efa2067a1`

- role: `HARD_PRE_ADMISSION_SURVIVOR`
- task: `DB44T2457_2024_warning_reporting::nominal::0003::152410c16ef5::report-1800s`
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

### HSA-0020 · `T1R-8f4758ed53df06`

- role: `INFORMATION_INFEASIBLE_DIAGNOSTIC`
- task: `DB44T2457_2024_warning_reporting::nominal::0014::b5b856e65fba::report-300s`
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

### HSA-0021 · `T1R-98a1a3100970b5`

- role: `NEGATIVE_PHYSICAL_INVALID_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0013::2419d35e2fbe::report-7200s`
- geometry cluster: `GC02`
- source profiles: `DB11T1677_2019_rainfall_dual_path`, `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H0_NEGATIVE_SHORTCUT_REGRESSION`, `H1_PARTIAL_OBSERVATION`, `H_RECOVERY_OBJECTIVE_CHECK`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:

### HSA-0022 · `T1R-72cd0a92273f8d`

- role: `NEGATIVE_SHORTCUT_REGRESSION_CONTROL`
- task: `DB44T2457_2024_warning_reporting::nominal::0012::dd7553cdd485::report-43200s`
- geometry cluster: `GC00`
- source profiles: `DB11T1677_2019_rainfall_dual_path`, `DB44T2457_2024_warning_reporting`, `DZT0450_2023_disconnect_recovery`, `JIAOZUO_2024_geohazard_monitoring_deployment`
- hardness: `H0_NEGATIVE_SHORTCUT_REGRESSION`, `H1_PARTIAL_OBSERVATION`, `H_RECOVERY_OBJECTIVE_CHECK`
- source extraction semantics: [ ] PASS  [ ] FAIL
- authority / priority / time semantics: [ ] PASS  [ ] FAIL
- task family identity: [ ] PASS  [ ] FAIL
- oracle success set: [ ] PASS  [ ] FAIL
- evaluator trace: [ ] PASS  [ ] FAIL
- reviewer:
- notes:
