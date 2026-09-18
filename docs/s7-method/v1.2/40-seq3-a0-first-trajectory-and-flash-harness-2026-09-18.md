# doc40 — 顺序3 真实 Agent 线束建成与第一条 A0 轨迹（deepseek-flash, seed0）

日期：2026-09-18　状态：**阶段记录，不宣告显著性、不关闭任何候选**（遵循 doc38 §5/§7：最初 3–5 条 A0 轨迹只作诊断）。
承接：doc33（候选 C 总纲）、doc38（工作纲领：四前提修复 + A0/A0-structured/A1 三层臂 + 三类声明）、doc39（四前提代码修复与 r24 诊断）。

---

## 0. 结论（先行）

1. **顺序3 真实 agent 在线线束建成并通过逐位管道验证**：新增 `code/v3joint/agent_mission.py`（`AgentMissionPolicy`，与 `MissionChangePolicy` 同 `CenterPolicy` 接口、同放置、同 `stamp_pair` 生效语义）、`code/v3joint/r25_agent_harness.py`；`joint_run.py` 增加最小注入点 `mission_policy_obj`（默认 `None` 时逐位不变，`test_joint` 5/5、`run_checks` 18/18）。用 `ScriptedDecider(dayfeed)` 走完整 agent 链路，**逐位复现 r24 dayfeed svc=.4001**，证明 agent 与普通规则同信息、同命令链路、同生效、同评分，无隐藏特权或劣势（§2）。
2. **第一条有效真实 A0 轨迹（deepseek-flash, seed0, 主工作点）svc=.3993，追平但未超过最强普通规则 dayfeed=.4001**（差 −0.0008：缺采 +2、缺交付 +4），无节点死亡、末 SoC 略低（.0848 vs .1046），代价是更多命令与能耗。它**没有**出现"理解任务却修错控制层导致灾难"的自然失败：靠合法的 SoC/昼夜反馈，它避免了 comply 式整夜密采（comply=.1649、死 13 台）。
3. **观察到的自然失败停留在"执行段不可见"层面，且在本片段未转化为业务损失**：升级在 h6（中断 h4–20 内）授权，agent 在中断窗反复下发加密命令，**606 次命令被拒、仅 14 次最终生效确认**；但 `CenterView` 不含 `commands_refused`/逐节点"已生效配置"/逐义务段状态，agent 无法区分"配置已请求 / 已生效 / 义务已兑现"。本片段这一缺陷没有造成额外失分，因为：(a) 任务表本身 h20 才经主回传到达网关（doc39 信息边界），(b) h4–20 主回传物理不可达、任何策略都无法在现场执行升级，(c) h20 恢复时为深夜、低 SoC，仅靠聚合 SoC 反馈就足以做出"夜间不密采、日出再加密"的保命决策，(d) 已到网关样本的稀缺回传选包已由 R20 maxcov 做到普通最优。
4. **方法判定**：通用 agent + 四个普通工具建议（dayfeed/sustain/comply/ignore）已经覆盖了**反应式**的昼夜/SoC 配置控制；候选 C 的增量只能来自**义务级、执行段级的跨层编译与修复**（doc33 H1/H1、Astra doc19 的问句"这次配置生效后能帮助哪条未完成义务"）。但在主张该机制之前，**必须先用零‑LLM 强基线证明存在 dayfeed/maxcov 拿不到的可改变损失**——当前 .3993≈.4001 没有给出这个差额。下一步先做义务‑能量‑机会感知的普通滚动规划（MPC）强对照（§7），这正是 doc38 指出"完整 MPC/联合最优尚未完成、不得宣称普通方法已最优"的缺口。

> 本文一切数字来自代码实跑与 trace，不是转述。trace 记录每次决策的完整合法观察、四个工具建议、模型原始返回、用量与解析注记。

---

## 1. 在线线束（同信息、同链路、同生效）

- `AgentMissionPolicy(CenterPolicy)`：center placement（mission 是中心职责）。动作空间＝每节点 `sample_period_s` 与 `report_period_s`，各取 {300,600}，**两字段可分离**；非法值钳制。决策触发：`init`、`req_change`（外生 schedule 段变化）、`recovery`（中心从完全听不到到重新听到任一节点）、有链路时 `grid`（默认 1800s）、完全失联时 `grid_outage`（7200s）。
- **观察只含 `CenterView` 合法证据**：`t_s`、节点 `reports`（report_period_s/sample_interval_s/soc_wh/cache_level/alive/read_at/newest_taken_at）、`in_flight`（网关队列非空）、`soc_model`、外生公开 `mission_schedule`，以及四个**同信息**普通工具建议（dayfeed/sustain/comply/ignore，各给出每节点目标周期）。不读 `evaluate()`、不读全程真值、不读网关本地字段。
- **写配置走原链路**：经 `policy.plan(view)` 返回 `(node,payload)`，由 `Instance._send_command` 按 center placement 走 `plane.center_send`；主回传断时命令 `commands_refused`、不入队；节点在 Class A 接收窗口 `_apply_delivery` 才落地生效。沿用 `stamp_pair` + in-flight + dwell(1800s) + 回执。
- decider 可插拔：`ScriptedDecider`（调普通工具，零 LLM）、`LLMDecider`（deepseek-flash，OpenAI 兼容 `/chat/completions`，`response_format=json_object`，temperature=0）、`ReplayDecider`（从 trace 按决策序号重放，离线零 API 复现 svc）。
- trace（JSONL，每次决策一条）：`t_s/trigger/req/any_heard/observation(含工具建议)/targets_before/actions/targets_after/raw/usage/api_error/parse_note`。

## 2. phase0 管道见证（零 API，逐位对齐）

`ScriptedDecider("dayfeed")`、grid=60 走完整 agent 链路：

| 量 | agent 线束 | r24 MissionChangePolicy dayfeed |
|---|---|---|
| svc（n=7560，半开对齐 h6） | **.4001** | .4001 |
| missing_collection | 2588 | 2588 |
| missing_delivery | 1947 | 1947 |
| dead | 0 | 0 |
| 末 SoC | .1046 | .1046 |
| 命令 confirmed / sent / refused | 14 / 84 / 472 | — |
| 任务表网关到达 gw | 72000（h20） | 72000 |

逐位相等 ⇒ 注入点与 agent 线束没有给 agent 任何隐藏特权或劣势，后续 A0/A1 的差额只能来自决策本身。

## 3. deepseek-flash 接口故障与修复（故障数据已剔除）

- **现象**：首次跑批（trace `A0_seed0_1789737746`，已删除）62 次决策几乎全部 `unparseable->hold`，节点全程 600 从未加密。
- **根因**：deepseek-**flash 是推理模型**，返回 `usage.completion_tokens_details.reasoning_tokens`；当时 `max_tokens=1400`，1400 个 completion token **全部是 reasoning_tokens**，`finish_reason=length`、可见 `message.content=""`。这是接口/预算配置错误，**不是 agent 的自然失败**，按 doc38 不得作为结果。
- **smoke 探测**（`smoke_api.py`，简单两节点决策）：默认配置 reasoning 仅 76–168 token 即可输出正确 JSON；`reasoning_effort="low"` 被接受（reasoning 76/total 289）；`thinking={"type":"disabled"}` 真正关闭思考（reasoning=None/total 193/0.8s）；`enable_thinking=false` 被忽略。
- **修复**：`LLMDecider` 默认 `reasoning_effort="low"`、`max_tokens=4000`；若首轮可见 content 仍为空（推理耗尽预算），第二次自动回退 `thinking={"type":"disabled"}` 强制产出 JSON。解析仍失败才记 `unparseable->hold`。

## 4. 第一条有效 A0 轨迹（seed0，主工作点）

设置同 r24 主口径：48h、14 节点（gw0＋13 位移）、solar peak .03、init SoC 1、主回传 h4–20 中断、备份 r1200/78B + maxcov、升级 600→300 于 h6 授权、任务表 h20（72000s）才到网关、非首段半开对齐 h6（n=7560）。

| 策略 | svc | missColl | missDeliv | dead | 末 SoC |
|---|---|---|---|---|---|
| ignore（不升级） | .3233 | 3523 | 1593 | 0 | — |
| **dayfeed（最强普通反应式）** | **.4001** | 2588 | 1947 | 0 | .1046 |
| sustain（滞回 SoC 门限） | .1667 | 5158 | 1142 | 13 | — |
| comply（立即全程 300） | .1649 | 5161 | 1152 | 13 | — |
| **A0（deepseek-flash，真实 LLM）** | **.3993** | 2590 | 1951 | 0 | .0848 |

A0 账：99 次决策（init1/req_change1/recovery1/grid96）、命令 sent=112、**refused=606**、confirmed=14、LLM calls=99、约 **518k token**、gw=72000、5 次解析回退/hold。

**行为时间线**（来自 trace 逐决策）：
- h0 init（蓝级 600）：保持稀疏 600/600，正确。
- h5.5 起在 req 仍为 600 时即 **pre-stage** 300（note："Yellow 300 starts at t=21600; pre-stage 300/300"）；h6 req_change 决定全密 300。但 h4 起主回传已断，**h5.5–h20 的加密命令全部被拒**，节点实际停在中断前已生效的 600。
- h20 recovery（任务表与链路同时恢复，时值深夜、SoC 低）：note "Hold sparse at night; dense 300 would drain low-SOC nodes"、"SOC ~0.011 too low for 300, keep 600 to avoid permanent death"，**夜间保持稀疏保命**。
- h24.5（日出）起全密 300；h26.5–h37 对低 SoC 节点**差异化**保留 600（dense=13/sparse=1），并出现**采样/上报周期分离**（如 n13/n15 采 300 报 600、n00 采 600 报 300）。
- h36 日落后再次转稀疏；h48 日出后重新加密。
- ReplayDecider 离线重放该 trace：svc=.3993 与在线逐位一致（验证可复现与记账正确）。

## 5. 自然失败诊断（doc38 §6 三类声明的口径）

- A0 表现出比 dayfeed 更丰富的行为（pre-stage、按节点 SoC 差异化、采样/上报分离），但这些"智能"**锚在聚合遥测与昼夜启发式上，不锚在具体义务的截止期与执行段位置**，因此未转化为覆盖增益，反多耗了电（SoC .0848<.1046）。
- 真正的能力缺口对应 doc33 H1 与 Astra doc19：控制器看不到"**命令是否已生效 / 合格样本在节点还是网关 / 哪些义务在何段失约**"。trace 中 606 次 refused 发生在主回传断期间，但 A0 的可见视图没有"未生效命令"簿记，也没有逐义务段状态，无法回答"这次配置生效后能帮助哪条未完成义务、下一次纠正前持续消耗多少"。
- **但本片段该缺口不产生可改变的业务损失**（§0.3 四原因）。因此当前只能记为"**声明可靠性 / 执行可见性缺陷**"，**不得**写成监测性能提升机会，也不得据此宣称 A1 必然有效（doc38 §7.4）。

## 6. 边界与不得过度外推

- 仅 **1 条轨迹、单 seed、单段升级片段**；按 doc38，不宣告显著性、不关闭方法类、不写成 agent 成败定论。
- A0 已携带四个普通工具建议；它追平 dayfeed 说明"反应式昼夜/SoC 控制"这一子问题普通工具已覆盖。这**不**等于跨层任务编译问题已解决。
- 5 次 LLM 解析回退/hold 是模型接口层面的噪声，已在 trace 标注；评估 agent 能力时这类 hold 按实际发生计入（不替模型补做正确动作）。

## 7. 下一步（决定候选 C 生死的零‑LLM 强基线优先）

按 Astra doc19/doc33 与 doc38"先用最便宜强反方"，在接更多真实 LLM 之前：

1. **义务‑能量‑机会感知的普通滚动规划器（MPC，强基线，不调 LLM）**：以合法可见信息（当前 SoC、昼夜能量模型、已收到证据、**逐义务截止期与段状态**、主/备发送机会、Class A 配置生效延迟）在短视域枚举合法动作序列（每节点采样/上报∈{300,600}），最小化"缺采＋缺交付"并以不死为硬约束；配"只调上游／只调备用／联合"消融。主工作点（中断＋r1200/78 稀缺备份）对比 dayfeed/maxcov，并扫开发种子 0–5。
   - 若联合/义务感知规划 **显著 > .4001 且不致死**：存在可改变损失 ⇒ 候选 C 成立的空间打开；MPC 作为机制内的普通求解器，agent 的可辩护角色是"把变化任务编译成 MPC 的义务/能力约束、在不可兑现时给出带原因的声明、在证据变化时局部修复"，随后再做 A0-structured（普通簿记/未决操作列表/核对流程）与 A1（义务链反例反馈）的同 agent 前后对照。
   - 若普通规划 **≈ dayfeed/maxcov**：该片段选择性加密/联合无增益，如实关闭 H1 在本工作点的增益主张，转 H2（升级后降级/解除片段：在途命令、已采未传、已耗能、已开窗未到期义务的保留），再按 doc38 §7.5 评估负结果可投性。
2. 排队（不阻塞）：可靠链路负对照（无中断，查 agent 是否画蛇添足）、降级/解除片段（H2）、复机敏感性 `restart_threshold_mult`、3–5 条 A0 与 A0-structured 轨迹。

## 8. 产物与复现

- 新增（本次提交）：`code/v3joint/agent_mission.py`、`code/v3joint/r25_agent_harness.py`；改 `code/v3joint/joint_run.py`（`mission_policy_obj` 注入，默认逐位不变）。
- trace/汇总：`results/agent_traces/A0_seed0_1789738644.jsonl`（99 决策全 I/O）与同名 `.summary.json`。接口故障废跑 trace 已删除、不进入证据。
- 复现：`python3 code/v3joint/r25_agent_harness.py phase0`（管道，零 API）；`… llm 0`（真实 A0，需 `DEEPSEEK_API_KEY`）；`… replay results/agent_traces/A0_seed0_1789738644.jsonl 0`（离线重放）。
- API：模型 `deepseek-flash`（推理模型）；`reasoning_effort="low"`、`max_tokens=4000`、空 content 回退 `thinking={"type":"disabled"}`；本条约 518k token。
- 自检：`test_joint` 5/5、`run_checks` 18/18（提交前复跑）。
