# doc53 — v0.7 证据再接地与论文修订（obligation runtime 收敛）

- 日期：2026-09-19
- 触发：doc51（v0.6 独立审查，R1–R8）、DSH 交叉复核（六项事实全部成立）、doc52（Execution-Grounded Obligation Runtime 收敛决策）。
- 范围：零 LLM 花费完成全部确定性修复/重算（r40–r43），硬化 agent harness，按 doc52 重写论文为 v0.7。cross-model / v5 端到端三臂按用户安排留作后续（harness 已就绪）。
- 基线：本轮开始 HEAD=`4f033d9`（工作区干净）。三个已复现正结果（FIFO 3025/7560、节点 purge 3267/7560、中断按期 434）**未被任何修订推翻**。

## 1. 逐条处置（与 doc51/DSH 对齐）

| 项 | 判定 | 处置 | 产物 |
|---|---|---|---|
| R5 purge 新颖性 | **改新颖性归属（决定性）** | 新增标准每记录到期 `generic_expiry`（BPv7 lifetime 语义，creation-relative，到期=业务交付期限 `(⌊t/P⌋+2)P`，不引用义务 id/槽几何/证书）；10 seed 与 `deadline_purge` **逐位等价**。撤"证书驱动新删除算法"，改述为标准 expiry 的业务期限参数化 + 源端零下行位置 + 跨段一致性。 | `r41_expiry_equiv.py/.json`，`network.py` |
| R4 归因可见性 | **改主张（决定性）** | 用网关在任务表到达 ka=20h 时刻**合法可见**证据（heard/received≤ka）重算 2136 条已失约升级义务；在线只可判 53.3%、已判定 100% 准确、46.7% 必须 unknown；离线 time-aware 全局才 100%。纠正旧 r32 把 650 条接入迟到并入 S_cap（旧 977=327 真容量+650 晚到）。 | `r40_local_attribution.py/.json` |
| R1 调用账 | **必须改（计量对象错位）** | 1089 是**决策**数非成功调用数；52 次 parse→hold 是 max_tokens 截断（非模型选 hold）；412 行首轮 attempt 错误在重试成功后未清。硬化 decider：`requests`（实际 HTTP 请求）与 `calls`（决策）分列、逐 attempt 日志、成功清 err、`truncated→hold` 标记。 | `agent_mission.py`，r42 |
| R2 谎报/诚实 | **必须改（结论级）** | 旧"谎报 24/19/0"不成立：A1 中断窗以 hold 为主致旧评分空集零、正常组评分分支未运行、且把"准备下发/要求激活"误当"声称已生效"。根因是观测 `link` 只有接入收据 n_heard、**无回传状态**，造成双向错误。旧"89 不可行登记"是证书提示词注入词计数。 | `r42_claim_relabel.py/.json` |
| R3 证书指示器 | **必须改（结论级新颖性）** | v4 从 n_heard 推断控制面，健康链路也误报。新增 unknown-aware `online_cert_block_v5`：UNREACHABLE 仅取自网络侧当前状态字段（缺省绝不武断，改 UNCONFIRMED）；夜间改真能量账（剩余黑夜×dense 增量能耗 vs 上报 SoC），拆 INFEASIBLE/ADVISORY；几何证书条件化。 | `agent_cert.py`，`r43_cert_v5_replay.py/.json` |
| R6 上界措辞 | 零成本收窄 | 删 upper bound / closes the question / zero-remainder；负结果收窄为"已测策略族/干预式松弛"，不称全局最优或调度空间封闭。 | 论文 §4、§10 |
| R7 边界 | 分项 | 中心 t0 持有 schedule 如实命名 pre-authored schedule（现场视图随表延迟到 20h）；半开首段闭区间写明；send-promise precision 改名 deadline-valid delivery fraction；commands_refused 为准入失败、未发、不占空口，不称计费节省；seeds 6–9 称"多次复用留出集"。 | 论文 §3、§8 |
| R7 seeds"不实" | DSH 判 astra 过头 | r07/r15/r20 一直把 6–9 当留出确认集，无调参痕迹；准确措辞是"复用留出集、非未曾触碰"，已改。 | 论文 §8 |
| commands_refused | 无需改结论 | 计数在准入失败分支，被拒命令未发；论文未把它当计费节省，v0.7 进一步明确为 command hygiene。 | 论文 §7、§8.4 |

## 2. 关键重算数字（权威，论文 v0.7 直接引用）

### 2.1 R5 / r41（maxcov 固定，10 seed 0–9）
- `deadline_purge` 与 `generic_expiry`：**全部 10 seed 逐位等价**（svc、中断按期 d、死亡、备份 on/late、delivered-oid 集合全等，BIT-IDENTICAL）。
- expiry(=purge) vs FIFO：全时段 svc 均值 **0.3729→0.4150（+4.21 点，95%CI[+3.64,+4.79]，10/10 为正，sd 0.81）**；中断按期总数 **1691→4265（2.52×）**；备份过期记录 **2538→1**；节点死亡 **12→0**。
- expiry vs latest-only：**+5.73 点（CI[+5.06,+6.39]，10/10 为正）**；latest-only svc 0.3578、中断 d 4250（靠丢弃恢复后仍有用的记录追平中断新鲜度）。
- seed0 主点：FIFO svc .4001/d202/on480/late219/dead?；expiry svc .4321/d434/late0/dead0；网关单侧抑制 maxcov_ontime svc .3976/**d194（−8）**/late0 —— 跨段代价转移见证。
- 测试：加 generic_expiry 分支后 test_joint 仍 5/5（默认 FIFO 逐位不变）。

### 2.2 R4 / r40（seed0，ka=72000，n=2136 已过截止升级义务）
- 离线 time-aware 真值：**S_time 588 / S_cap 327 / S_energy 571 / S_access 650**，归因 2136/2136=100%（明确标 offline diagnostic）。
- 在线网关局部可见：**S_time 588 / S_cap 327 / S_access 223 / unknown 998**；覆盖率 **1138/2136=53.3%**，已判定子集准确率 **100%**（混淆仅对角）；unknown=571（没采）+427（ka 后才 heard）。
- 427 条匹配样本 ka 后才 heard、650 条 deadline 后才 heard（例 gw0:rainfall:59400 在 72600 才 heard）。
- 结论：在线 projector 必须把 unknown 作为一等状态；局部处置（源端 expiry）不依赖消解 unknown。

### 2.3 R1/R2 / r42（最终 11 条 r38 轨迹，1089 决策）
- parse→hold **52**（max_tokens 截断，raw 停在字符串中间、completion_tokens 打满 4000）；valid 1037；412 行带首轮 attempt 错误残留。
- 逐臂 parse 失败率：**A0 28/396=7.1%、A0s 19/297=6.4%、A1 5/396=1.3%**（三臂差距混入格式可靠性）。
- 强制中断窗 [4h,20h) 内确定性"link up / commands can apply"乐观断言：**A0 36 / A0s 32 / A1 2**。
- dense orders（三中断种子）：A0 144 / A0s 192 / A1 67；含健康对照总 A0 182 / A0s 192 / A1 95（健康 A0 38、A1 28）。
- 旧"89 不可行登记"：实为证书措辞命中（A1 317 决策含 infeasib/hold/downgrade 类词，A0/A0s 为 0），非逐义务结构登记。
- claim_applied_false（正则有噪声，弱用）：A0 27 / A0s 6 / A1 0。

### 2.4 R3 / r43（11 轨迹观测快照，v4 vs v5 纯函数离线 replay，零 LLM）
- v4 确定性 CONTROL-PLANE-NOT-DELIVERING 断言总计 711（其中强制中断窗内 252）；v5 在观测无网络侧回传字段时 **UNREACHABLE=0、UNCONFIRMED=946**。
- evidence 确认的 5 个健康链路误报时刻（hod 14.0/17.5/7.0/11.0/6.5）：**v4 5/5 误断言、v5 全部 0 unreachable 改 unconfirmed**。
- 夜间 dark 决策 528：v4 全部 528 次"PERMANENTLY kills"统一硬门；v5 真能量账拆为 **ENERGY-INFEASIBLE 189 + NIGHT ENERGY ADVISORY 339**；临近日出 hod 4.5–6（min SoC .010–.017、剩余 0.5–1.5h）v4 仍喊 kills、**v5 全部正确降为 advisory**。
- 定位：反事实**机制见证**（同观测换证书文本），非端到端 v5 运行。

## 3. E-R3a（同模型/跨模型 API 对照）决策：推迟

理由：(1) v5 改了证书与观测，公平三臂须用 v5 重跑所有臂，本质是新一批端到端 LLM 运行，正属用户明确自补的 cross-model 批次；(2) 主贡献（确定性 obligation runtime：unknown 状态语义 + 标准 expiry 定位 + 局部确定证据处置 + locality）不依赖 agent 端到端；(3) n=1 弱对照与用户批次重复；(4) DSH 顺序本就是"仅当 R5 留独立问题才做 R3 API"，而 R5 证明 purge≡expiry、无需 agent API 救新颖性。

**已就绪的 harness（用户批次可直接用）**：
- `agent_cert.py`：`online_cert_block_v5` / `CertLLMDecider(version="v4"|"v5")`；v5 支持可选观测字段 `link.primary_backhaul_state`（网络侧当前状态，非时长预测）。
- `agent_mission.py`：`requests` vs `calls`、`_last_attempts`、`api_requests/attempts/parse_hold` 决策字段、重试成功清 err、截断标记。
- `r42_claim_relabel.py`：对称重标蓝本（每臂、两组、每决策都评，报分母，不依赖是否发 dense）。
- 建议批次：A0 / A0s / A1 均用 v5 重跑多 seed；新增 **A0s+expert**（给普通臂同样的昼夜策略、几何常量、确认规则与 note 模板，但**不给**段 projector），以剥离"专家提示包"与"结构化 projector"的独立增量；跨模型复跑；端到端串 L0 后再评估四死。

## 4. 论文 v0.7 变更对照

- 标题：`Execution-Grounded Obligation Runtime ...: Local Evidence, Deadline-Aligned Expiry, and Honest Infeasibility`；系统名 ObliRun。
- 摘要：823 词跨两页 → 单页（约 350 词），三点结构（partial observability / local-certainty expiry / locality + formative agent）。
- 贡献：6 条 → 4 条，统一对齐 obligation-runtime 单一对象。
- RQ1：几何证书改**条件性**（给定网络侧确认的不可用区间 [4h,20h]；602/588/14、lead 0.2–14h 中位 7.2h 保留并加条件）；容量证书不编译期断言。
- RQ2（新 Table 2）：在线 53.3%/精度 100%/46.7% unknown vs 离线 time-aware 100%（588/327/650/571）；显式三类声明 confirmed/unconfirmed/unreachable。
- RQ3（新 Table 3）：purge 改名 deadline-aligned expiry，加入 generic_expiry 逐位等价行；撤算法新颖性，保留跨段一致性/业务期限依据/源端位置；正结果数字全保留。
- RQ4（Table 4）：locality 三要素公式；零死亡改"所测三种子经验结果"，删 guaranteed survival；不把 r39 的 0 填入 r38 残留四死（agent 未串 L0）；commands_refused 改 command hygiene。
- RQ5（Table 5）：降为 formative；撤"零谎报/零 fallback/89 不可行登记"；列准确调用账、双向链路误判、v5 离线见证；端到端 v5/跨模型/matched-capability 明确列 future。
- 全局：删 upper bound/closes/zero-remainder/guaranteed/never touched/100% 在线归因；负结果收窄已测策略族；清"verified in this environment / full text not opened / doc38 protocol"等内部审计语（含 refs.bib note）；pre-authored schedule、半开首段、deadline-valid fraction、复用留出集等口径修正。
- 图：Fig1 义务链（S_access 改 collected-not-heard-in-time、加 unknown 注）、Fig2 三层 runtime（L0 改 computed ledger + deadline-aligned expiry、L2 改三类声明）保留。
- 构建：18 页，22 条 refs 全解析、无 undefined citation/reference、无 LaTeX error。

## 5. 复现

```bash
R='/home/orion/Communications/应急通信/project1/agentic communication'
export PYTHONPATH="$R/libs/pylibs:$R/code/v3joint:$R/code/instance:$R/code/physics:$R/code/runtime:$R/code/experiments:$R/code/analysis:$R/code/monitoring"
python3 code/v3joint/r40_local_attribution.py
python3 code/v3joint/r41_expiry_equiv.py
python3 code/v3joint/r42_claim_relabel.py
python3 code/v3joint/r43_cert_v5_replay.py
python3 code/v3joint/test_joint.py     # 5/5
python3 code/run_checks.py             # 18/18（r40–r43 已登记 results/README.md）
```

## 6. 仍开放（不阻塞 working draft）

- v5 端到端三臂 + A0s+expert matched-capability + 跨模型 + 端到端串 L0（用户 cross-model 批次）。
- 多义务/任务版本重叠下 expiry 释放键改为"记录仍有效的最晚义务期限"；BPv7 custody hand-off 与源端 expiry 的部署对比。
- 更宽部署参数扫描（备份速率/载荷、节点数、容量、云遮、复机阈值）；brownout 复机敏感性。
- venue/署名未定（作者行仍 working draft / \today）。
