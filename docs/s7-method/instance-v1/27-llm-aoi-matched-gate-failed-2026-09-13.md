# A′（AoI-matched semantic target）：真实 LLM baseline 的仪器闸门**未通过**

日期：2026-09-13。协议 `llm_naive_v3`（`sha256=2112620282fc1519…`，`derives_from` v2）。基线 `79b0ff8`。
按用户裁决：选 **A′**；**`C′` 不开**、**`B′` 暂缓**。

## 一、必须记的定性更正（用户裁定，我接受）

§7.98/§7.99 那个 200 epoch 结果（79/200 老化、11 次动作）**只能标注为
`objective mismatch / conservative-agent observation`**，**不得**写成"LLM 行动不足 failure"。

理由：在"满足现有监测义务"这个目标下 LLM 选择近乎 `local` 的行为，**与 repo 早已反复发现的事实一致**——
默认配置与本地自治本就能承担大量业务，**Task v1.1 明确不要求中心必须有增益**。
硬把它解释成"应该多动手却没动"，**很容易又滑回"为了让 agent 有事做而定义任务"**。
**数据保留，但不得用来判 planning amplification。**

## 二、v3 协议（A′ 的实现）

- **不给宽泛自然语言目标**。外部规则产生 desired target，**与 `AoiPolicy(stale_s=3600, fast_s=300,
  slow_s=900)` 同一个 target function**：`g_i(t) = 300 if AoI_i 空 or AoI_i > 3600 else 900`。
- LLM 的任务只有一句：「当前 desired effect 是 `report_period = g_i(t)`；依据 confirmed state、
  pending state、最近 tool outcome，决定现在是否需要调用工具。」
- 状态**只给事实**（7 个键，与协议 `node_fields` 逐字一致）：
  `id` / `aoi_s` / `desired_target` / `confirmed_target` / `pending_effect` / `pending_age_s` / `evidence_age_s`。
- **prompt 不含**「pending 时不要重复」「失败后等待」「避免冗余重试」——**这些正是要观察的行为**。
- **不改 Task v1.1、不改 condition、不改 action surface、不改 planner cadence。**

## 三、闸门结果：**两项判据都没过 ⇒ 全量不启动**

`adm_noout × seed0 × 200 epoch`（350 s）：

| 量 | 值 |
|---|---|
| **`actions`** | **`{'noop': 200}`** |
| **① target agreement** | **`0 一致 / 0 不一致` ⇒ 无从评估**（零动作） |
| **② semantic episodes** | **0**（closed 0） |
| `same-target unresolved replan` | 0 |
| `stale_epochs` / `unseen_epochs` | 0 / 200 |
| service / AoI | 160.0 / 168 ；3517 s |
| 输入 token | **783/次**（上限 1000 ✓） |
| 解析失败 | **0** |

**⇒ 按目标规定（"两项都过才启动全量"）：如实报告并停，全量 3 × 720 不启动。**

## 四、仪器已逐项排除（这次不能归因于仪器）

7 个键与协议逐字一致；单次输入实测 **783 < 1000**；prompt 与状态键名一致（`confirmed_target` 已在状态里）；
prompt 无任何"该不该重发"的提示；**零解析失败**、原始输出全是合法 JSON；
桩对象核对过状态确实把 `desired_target=900 / confirmed_target=3600 / pending_effect=true` **作为事实摆出**。

**本轮实测陈述（克制表述）**：

> **在"目标明确、`desired≠confirmed` 且 pending 已如实给出"的条件下，
> 真实 LLM 在 200/200 个 decision epoch 里选择 `noop`，没有产生任何 semantic episode。**

**但这不是对预注册判据的判定**：判据 1 要求 target agreement 正常，而**没有任何动作可供评估**；
判据 2 要求 unresolved 下的重复 planning，而**没有 planning**。
⇒ **要判"有没有 planning amplification"，必须先观察到非零动作；当前状态下观察不到。**

## 五、这条线的位置

- **已实测**：在 A′ 目标 + `deepseek-flash`(non-thinking) + 本实例条件下，**真实 LLM 不产生动作**。
- **未实测**：planning amplification（无动作 ⇒ 无量可测）。
- **不再开**：`C′`（会把"没事做"变成"必须做事"，破坏因果纪律）；`B′` 暂缓（目标欠定义，
  且把 `ea_nb` 阈值写进 prompt 就是让 LLM 模仿 `ea_nb`）。

## 六、复现

```bash
eval "$(grep -E '^[[:space:]]*export[[:space:]]+DEEPSEEK_API_KEY=' ~/.bashrc | tail -1)"
export PYTHONPATH="$PWD/libs/pylibs"
python3 code/analysis/llm_naive_baseline.py --call-limit 200 --tags adm_noout
```
**启动务必写成独立语句**（`cd` / `export` / `nohup` 各一行）——`cmd && nohup ... &` 会把整条 `&&` 链后台化、
重定向在子 shell 里失效（踩过，见 §7.102）。
