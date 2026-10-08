# Layer 1 Internal Source / Task / Evaluator Audit

状态：**INTERNAL_ASSISTANT_AUDIT_PASS / no independent external reviewer**
日期：2026-10-09

## 1. Audit identity and boundary

Reviewer：`OpenAI GPT-5.6 Sol`，作为项目内部 assistant-led reviewer 执行。

这份审计替代原计划中要求项目所有者逐条手工签字的流程，但**不冒充独立专家评审**。论文与 release note 只能写：

> internal source/task/evaluator audit completed; no independent external expert review was performed.

原 `HUMAN-SOURCE-AUDIT-PACKET.v0.2-retry-legality.md` 与 worksheet 保留为历史流程，不回写成“真人已签字”。

## 2. Sample coverage

审计样本沿用 frozen v0.2-retry-legality stratified sample：23 items，覆盖 train/dev/test、candidate role、source profile、hardness interactions；机器构造时的 143 个 coverage token 全覆盖。

候选角色：

- 3 × `EASY_CONFORMANCE_CONTROL`
- 12 × `HARD_PRE_ADMISSION_SURVIVOR`
- 3 × `INFORMATION_INFEASIBLE_DIAGNOSTIC`
- 3 × `NEGATIVE_SHORTCUT_REGRESSION_CONTROL`
- 2 × `NEGATIVE_PHYSICAL_INVALID_CONTROL`

样本只使用四个 source profile：

- `DB44T2457_2024_warning_reporting`：23/23
- `DZT0450_2023_disconnect_recovery`：22/23
- `JIAOZUO_2024_geohazard_monitoring_deployment`：20/23
- `DB11T1677_2019_rainfall_dual_path`：12/23

## 3. Direct source audit

### 3.1 DB44/T 2457-2024

证据入口：[`source-evidence/DB44T2457_2024-landslide-table11.md`](source-evidence/DB44T2457_2024-landslide-table11.md)。

复核结论：

- task hazard type 必须固定为 landslide；
- cadence authority 来自 §9.2.2.2 Table 11，而不是此前误用的 ground-fissure Table 15；
- grade × warning-state cadence 的 30min / 1h / 2h / 4h / 6h / 12h / 5min 等 sample boundary 与 Table 11 相容；
- range cell 只枚举 source lower/upper boundary，不创造中点分布。

**PASS**。历史 Table-15 extraction error 已在进入本审计前修复并重生成下游 v0.2-retry-legality lineage。

### 3.2 DB11/T 1677-2019

证据入口：[`source-evidence/DB11T1677_2019-rainfall-monitoring.md`](source-evidence/DB11T1677_2019-rainfall-monitoring.md)。

官方 §5.2.12 可核对：降雨时 ≥1/5min、无雨时 ≥1/2h、GPRS+BeiDou dual channel、无日照且 5min transmission 下 GPRS ≥15d / BeiDou ≥7d，并可观测上传时间、传输方式、电池电压、信号强度等字段。

关键边界：这些是 acquisition / device / transport semantics，**不是 upper-platform delivery deadline**。`communication_completion_semantics` 保持 `UNRESOLVED`，profile 也明确禁止 cadence→delivery-deadline 偷换。

**PASS**。

### 3.3 DZ/T 0450-2023

证据入口：`/home/orion/Communications/source_acquisition/field_evidence/china-geohazard-and-beidou/standards-guidance/dzt0450.txt`。

复核结论：

- local storage 至少保存 7 天；
- communication restored 后将历史数据按规范发送至上一级平台或提供本地下载；
- satellite short-message average latency ≤5s、success ≥95%；
- LEO narrowband single packet ≤200B、average latency ≤5s、success ≥99%；
- 标准**没有**给出一般性的 backlog-vs-fresh sacrifice priority。

`reconnect_backlog_priority` 保持 `UNRESOLVED`，23/23 machine sample 均包含 `unresolved_reconnect_priority_preserved_not_filled` guard。

**PASS**。

### 3.4 Jiaozuo 2024 government procurement

证据入口：`/home/orion/Communications/source_acquisition/field_evidence/china-geohazard-and-beidou/field-cases/jiaozuo-geohazard-monitoring-procurement-2024.remote.md`；公开政府采购项目号 `焦财招标采购-2024-12`。

公开材料可核对：30 个隐患点；采集频率不低于 1/hour、临灾前加密；LoRa→gateway→4G/BeiDou 与 NB-IoT/4G direct upload；bidirectional platform/device management 与本地存储状态读取能力。

关键边界继续保留：通信 priority/capability 不等价于授权中心 policy 每 slot 任意 path override。

**PASS WITH ACCESS NOTE**：repo 保存的是 remote acquisition record 而不是原 PDF bytes；本 audit 已用公开政府采购网页/PDF重新核对核心 clause。该 access form 作为 provenance limitation 公开。

## 4. Five-field audit over 23 frozen samples

### Source extraction semantics — PASS 23/23

- sample source-profile sets 与 frozen recipe 一致；
- 四个 profile 的直接来源与当前 registry 语义一致；
- source gap 不被隐式补值。

### Authority / priority / time semantics — PASS 23/23

- world-bundle / causal-process validator 全部通过；
- DB44 reporting deadline 始终为 release + source interval；
- public satellite geometry 不编码 hidden answer bit；
- DZT reconnect priority 未被填充；
- DB11 acquisition cadence 未作为 sampled delivery deadline authority。

### Task family identity — PASS 23/23

所有 sampled cases 的 protected subject 都属于 T1 Monitoring Information Continuity；capability、query、radio、recovery regime 没有被错误升格成 task family。

### Oracle success set — PASS 23/23

machine preaudit 中 exact classification 与 candidate role expectation 全部匹配；非 physical-invalid role 的 world solvability 关系正确；hard-survivor sample 的 V0–V8 disposition 与 frozen artifacts 一致。

### Evaluator trace — PASS 23/23

所有 solvable-world witness 均可由 independent execution evaluator replay；no-op、unauthorized actor 等 mutation 被拒绝。新的 paper-facing full-simulator audit又覆盖 7/7 release-candidate T1 surfaces，并验证：删实际 sample→缺采、center arrival 推迟→缺送、无关 executed record 不改结果、不同合法 on-time arrival 仍可成功。

## 5. Result

```text
23 / 23 sampled items
× 5 review dimensions
= INTERNAL PASS
```

未发现需要重新打开 task/source/evaluator correctness 的新问题。

## 6. Remaining limitation

未进行独立外部领域专家 review。该事项不再作为内部 benchmark construction blocker，但必须进入论文 limitation / artifact card；不得写成“expert-validated benchmark”或“independent expert audit”。如果未来获得通信/地灾领域 reviewer，可追加 independent review，不改变当前 sample identity。
