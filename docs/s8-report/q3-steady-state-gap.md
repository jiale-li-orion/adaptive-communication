# Q3：无故障稳态下 5.3 个点从哪里来

**范围**：trajectory `none`（无故障），3 天 = 72 h，20 个种子（seed 0..19，开发区间）。
**对象**：`policies.RuntimePolicy`（`ours`）与 `compose.RulePlanner + compose.ContractRuntime`（`rule__contract`）。
**产物**：`code/analysis/steady_gap.py`（14 条臂 × 20 种子，含 `--downlink-per-uplink` 机制探针）、
`code/analysis/steady_gap_counters.py`（逐分支计数）、
`results/steady_gap_q3_attrib.json`、`results/steady_gap_counters_q3_attrib.json`、`results/steady_gap_q3_dpu2.json`。
**纪律**：未修改 `code/monitoring/`、`code/runtime/`、`code/experiments/` 下任何文件；未使用 `scripted` LLM 后端；未调整故障强度（本页全部在 `none` 上）。

```bash
export PYTHONPATH="$PWD/libs/pylibs"
python3 code/analysis/steady_gap.py --seeds 20 --tag q3_attrib
python3 code/analysis/steady_gap_counters.py --seeds 20 --tag q3_attrib
python3 code/analysis/steady_gap.py --seeds 20 --tag q3_dpu2 --downlink-per-uplink 2 \
  --arms "ours,rule__contract,ours W3 before W1"     # 机制探针，见第一节与第六节
python3 code/run_checks.py          # 17/17 通过
```

---

## 一、一句话答案

**这 5.3 个点来自一个 tick 内两条 runtime 把命令交给控制面的顺序，不来自任何一个可调参数。**

`RuntimePolicy.plan` 在一次调用里先返回 W1 的 `request_measurement`、后返回 W3 的 `set_monitoring_profile`
（`code/monitoring/policies.py:950-964` 在 `:983-1104` 之前）；控制面对每个上行机会**只投递节点队列的队首一条**
（`code/monitoring/opportunity.py:384-414`，`_deliver` 里 `queue[0]`，`downlink_per_uplink=1`）；
而 `RuntimePolicy` 在节点有在途操作时**否决一切写入**（`policies.py:1043-1045`，`skip/in_flight`），
`ContractRuntime` 没有这条否决。三者叠加：风险窗开启的那一刻，节点还在常态档，上行节奏是每小时一次
（`MONITORING_PROFILES["normal"]["upload_s"] = 3600`），因而**至多每小时一次下行机会**，
这条唯一的机会被排在队首的测量请求占掉，切档整体推迟**整整一个常态档上行周期**。
把 W1 排到 W3 之后（在 `code/analysis/steady_gap.py` 里对 `plan` 的返回值重排，不改任何参数、
不改任何监控层代码）：

| 臂 | 覆盖率 | 观测空窗 | 下行次数/种子 |
|---|---:|---:|---:|
| `ours` | 89.07% | 6.21% | 604.75 |
| `ours W3 before W1` | **94.53%** | 2.73% | 628.90 |
| `rule__contract` | 94.41% | 2.37% | 941.80 |

即 5.34 个点里的 **5.47 个点**由一个重排拿走，代价是多花 24.15 次下行。20 个种子里，
`rule__contract` 减 `ours` 的逐种子均值是 **+5.34**（与已知读数 89.07 → 94.41 一致），
`rule__contract` 减 `ours W3 before W1` 的逐种子均值是 **−0.13**，即重排之后单体实现反超组合实现。

补一条**不改任何 runtime 代码**的旁证：`run_episode` 的 `downlink_per_uplink` 是场景参数（冻结场景是
Class A 的 1），把它提到 2——即每个上行机会允许投递队首之后的第二条——`ours` 从 89.07% 升到 **94.87%**，
两臂差距从 5.34 点缩到 **0.57 点**。20 种子，`--downlink-per-uplink 2 --tag q3_dpu2`：

| 臂 | 覆盖率 | 观测空窗 | 下行/种子 | 切档延迟 |
|---|---:|---:|---:|---:|
| `ours` | 94.87% | 3.80% | 352.40 | 76.91 min |
| `rule__contract` | 95.44% | 2.37% | 458.10 | 52.13 min |
| `ours W3 before W1` | 95.35% | 2.55% | 380.80 | 52.84 min |

**这不是场景结论**（Class A 下一机会只能投一条），它是对机制的直接检验：只要队首不再独占整条机会，
差距自己就没了。加上重排后 `ours W3 before W1`（95.35%）与 `rule__contract`（95.44%）基本持平。

---

## 二、基线核对与确定性

本节所有臂都跑 `run_episode(policy, hours=72, seed=s, fault=None, supply=SupplyFleet(nodes, s), paths=[("backhaul",0.62)])`，
与 `code/experiments/monitoring_trajectories.py:63-86` 的构造逐项相同（`--paths backhaul:0.62`、能量开、`runtime_paths=0`）。

| 臂 | 覆盖率 | 观测空窗 | 下行次数 | 与既有结果文件 |
|---|---:|---:|---:|---|
| `ours` | 89.07% | 6.21% | 604.75 | 与 `results/monitoring_trajectories_business2.json` 完全一致 |
| `rule__contract` | 94.41% | 2.37% | 941.80 | 与 `results/monitoring_trajectories_2x2v3.json` 完全一致 |

`code/analysis/steady_gap.py` 用两个不同 `--tag` 各跑一次 20 种子，14 条臂的 `per_seed` 数组逐位相同
（脚本里未引入任何未播种随机源；`run_episode` 的全部随机数走 `stable_uniform`）。

---

## 三、损失的形状：全部落在风险窗需求上

需求是固定的 430 条（`task_generator.build_tasks`：142 条常态 + 288 条风险，`policies` 权重 `{0:1.0, 1:1.0}`）。
`steady_gap.py` 的 `risk_coverage` 列就是 288 条风险需求的覆盖率。由 `coverage × 430 = normal_hit + risk_hit`
反解常态类命中数：

| 臂 | 覆盖率 | 风险类覆盖 | 反解常态类命中数 | 风险窗开启时"档位还没切过去"的需求占比 |
|---|---:|---:|---:|---:|
| `ours` | 89.07% | 83.72% | 141.9 / 142 | 22.64% |
| `rule__contract` | 94.41% | 91.70% | 141.8 / 142 | 11.04% |
| `ours W3 before W1` | 94.53% | 91.91% | 141.8 / 142 | 10.89% |
| `ours W1 off` | 94.37% | 91.70% | 141.7 / 142 | 11.11% |
| `ours no in_flight veto` | 88.38% | 82.71% | 141.8 / 142 | 23.96% |

**14 条臂的常态类命中数全部是 141.7–141.9/142，即 100%。5.3 个点的全部损失都在风险窗这一类上。**
（风险窗是小时 12–18 与 48–54；`profile_for_hour` 在这两段要求全 16 节点切到 `risk` 档，
采样间隔从 300 s 变 60 s。风险需求只在 8 个关键节点上，窗口长度 5 min、投递截止 10 min。）

第二条读数把"为什么丢"说清楚：`switch_on_delay_min` —— 从风险窗开启到每个节点**真正跑在 `risk` 档**的平均延迟
（从 `record.profile_timeline` 取，未切换的按窗口长 6 h 封顶，16 节点 × 2 个窗口）：

| 臂 | 切档平均延迟 | 配置错配（节点·分钟/运行） |
|---|---:|---:|
| `ours` | **139.82 min** | 7277.4 |
| `rule__contract` | **78.91 min** | 5347.5 |
| `ours W3 before W1` | 72.17 min | 4995.5 |
| `ours W1 off` | 70.47 min | 4974.6 |

**139.82 − 78.91 = 60.91 分钟，恰好等于常态档的上行节奏 `MONITORING_PROFILES["normal"]["upload_s"] = 3600 s`。**
这就是全部机制的量纲：多一条命令排在队首，切档就整整晚一个常态档周期。

---

## 四、逐条候选来源的判定

### 候选 1：重试预算 / 节奏 —— **证伪（不是主因）**

数值上两条 runtime 确实相同（`retry_budget=3, dwell_s=300`），但触发结构不同。
对照 `policies.py:1047-1092` 与 `compose.py:510-549`：

| 情形 | `RuntimePolicy.plan` | `ContractRuntime.dispatch` |
|---|---|---|
| 节点报告的档位＝需求档 | `reported == wanted` → 置 `settled_version`，**且无论证据新旧都结算**（`:1029-1041` 两个分支都 `continue`），不下发 | `_settle_on_evidence` 在 `payload["profile"] == book["profile"]` 时关账（`:471-488`，**不看 `read_at`**），随后 `key in settled` 静默丢弃 |
| 同一逻辑操作已断言≥1 次 | 无独立分支；由下一个分支与 `attempts` 共同约束 | `attempts>=1 and now-first_at < dwell_s` → 跳过（`:528-529`） |
| 连续断言满预算 | `attempts >= retry_budget and now-attempted_since < dwell*retry_budget` → `wait/retry_budget`（`:1050-1057`）；**预算用尽时同 tick 直接续走结论路径**（`:1058-1060` 后不 `continue`） | 预算用尽且冷却未过 → 跳过；冷却已过 → 置 `attempts=0` 并**本 tick 跳过**（`:536-549`） |
| 写入后没有更新的证据 | `issued_version and not fresh_evidence`：`now <= issued_at + ttl_s` 时 `wait/no_evidence_since_write`；**超过 6 h 则强行断言**（`:1062-1083` 的 fall-through） | `attempts>=1 and not _fresh_evidence` → 跳过，**没有截止线**（`:530-535`）；`ttl_s` 字段存在但 `dispatch` 从不读 |
| 有更新的证据但与期望不符 | `now - issued_at < dwell_s` → `wait/dwell`（`:1085-1092`） | 证据新且 `now-first_at >= dwell_s` → 重试 |
| 有在途操作 | `skip/in_flight`，**否决**（`:1043-1045`） | **无此分支** |
| 一个 tick 内的顺序 | W2 → **W1** → W3（`:934-964` 在 `:983` 之前） | profile → W2 → **W1**（`compose.py:144-149`） |

`steady_gap_counters.py` 给出这三条 wait 分支在稳态的实际触发量（20 种子均值，单位：节点·tick/运行，
总量 16×72×60 = 69120）：

| 分支 | 触发次数/运行 |
|---|---:|
| `settle/report_postdates_write` | 54854.2 |
| `settle/state_right_evidence_absent` | 147.7 |
| `skip/in_flight` | 7827.9 |
| `wait/no_evidence_since_write` | 5904.0 |
| `wait/retry_budget` | 187.5 |
| `wait/dwell` | **0.0** |
| `write/assert` | 198.7 |

逐项放宽的读数：

| 臂 | 覆盖率 | Δ覆盖率 | 下行次数 | Δ下行 |
|---|---:|---:|---:|---:|
| `ours` | 89.07% | — | 604.75 | — |
| `ours retry_budget=99` | 89.53% | +0.47 | 620.45 | +15.7 |
| `ours dwell_s=0` | 89.53% | +0.47 | 620.45 | +15.7 |

**判定：证伪。** `dwell` 分支在稳态从不触发（计数为 0），因此 `dwell_s=0` 与 `retry_budget=99` 的读数逐位相同
——两者都只是让"冷却"这条门失效。冷却门值得 **+0.47 个点**，与 5.3 点相差一个数量级。

### 候选 2：下发量 —— **确认"花错地方"，证伪"省下来的就是丢掉的"**

参数逐项放宽**没有一条能到 94%**：14 条臂里参数类的最大值是 `retry_budget=99` / `dwell_s=0` 的 +0.47，
把五个可调参数一次性全放宽也只有 **+0.42**（89.49%，且下行涨到 1044.5）：

| 臂（只改这一处） | 覆盖率 | Δ覆盖率 | 下行次数 | Δ下行 |
|---|---:|---:|---:|---:|
| `ours` | 89.07% | — | 604.75 | — |
| `retry_budget=99` | 89.53% | +0.47 | 620.45 | +15.7 |
| `dwell_s=0` | 89.53% | +0.47 | 620.45 | +15.7 |
| `ttl_s=1` | 89.51% | +0.44 | 624.80 | +20.0 |
| `status_max_age_s=86400` | 89.07% | **+0.00** | 604.75 | **+0.0** |
| `measure_window_mult=1` | 89.30% | +0.23 | 936.25 | +331.5 |
| `measure_window_mult=8` | 89.33% | +0.26 | 381.85 | −222.9 |
| `enable_backfill=True` | 89.07% | **+0.00** | 604.75 | **+0.0** |
| 五个参数全放宽 | 89.49% | +0.42 | 1044.50 | +439.8 |

两个 +0.00 是干净的零结果，值得记下：
- `status_max_age_s` 只在 `_w2_gap` 里被读（`policies.py:890`），而 `_w2_gap` 第一句就是
  `if not self.enable_backfill: return None`（`:881`）——只要补传关着，这个旋钮**恒为死参数**。
- `enable_backfill=True` 也是 +0.00：`_w2_gap` 只在积压 `gap_records > node_batch_max = 240` 时才下单
  （`:903-906`），240 条常态记录＝20 小时，72 h 稳态跑不到。

**"省下来的就是丢掉的那部分吗？"——不是。** 看代价：

| 对照 | Δ覆盖率 | Δ下行次数 |
|---|---:|---:|
| `ours W1 off` − `ours` | **+5.30** | **−281.0** |
| `ours W3 before W1` − `ours` | +5.47 | +24.1 |
| `rule__contract W1 off` − `rule__contract` | −0.13 | −469.8 |

`ours` 少花的 281 次下行**不是它省下来的服务，而是它花错地方的钱**：把这 96 次测量请求去掉，
覆盖率反而涨 5.30 点。另一半同样说明问题：`rule__contract` 也发同样的 96 次请求、也吃掉 469.8 次下行机会，
而它换来的只有 **+0.13 点**（94.41% → 去掉 W1 的 94.28%）。
**在这个稳态里，"多花下行"几乎不改变覆盖率；改变覆盖率的是花在哪条队列位置上。**

### 候选 3：W1 测点请求 —— **确认，但主因是"排在哪里"而不是"发不发"**

两条 runtime **发出的测量请求次数完全相同**：`steady_gap_counters.py` 与逐运行计数都给出
`dispatch/request_measurement = 96.0`/运行，逐种子无差异（2 个风险窗 × 每窗 3 次 × 16 节点）。
`RulePlanner._w1_intents`（`compose.py:178-207`）与 `RuntimePolicy._w1_needs_fresh_measurement`（`policies.py:842-865`）
的判据（未结请求唯一、`now - newest > risk.sample_s * 2`、窗口 = `normal.upload_s * measure_window_mult`）也一致。

差别在**顺序**和**否决**。计数（20 种子均值/运行）：

| 计数 | 值 | 说明 |
|---|---:|---|
| `skip/in_flight` 总次数 | 7827.9 | 写入被否决的节点·tick |
| 其中**有 W1 请求未结** | 6676.5 | 占 **85.3%** |
| 其中没有 W1 请求 | 1151.5 | 余下 14.7% |
| 否决发生时需求是 `risk` | 3891.4 | 即"该切档却没切" |
| 每个 W1 请求平均换来 | 69.5 个被否决的节点·tick | 6676.5 / 96 |

即：96 次测量请求，每一次都让所在节点在**约 70 个节点·分钟**里无法接受任何档位写入
（该运行的总量是 69120 节点·tick，占 9.7%），而它们集中在风险窗内。

三条消融臂把顺序与存在性分开：

| 臂 | 做什么 | 覆盖率 | Δ（对各自基线） | 下行 | 切档延迟 |
|---|---|---:|---:|---:|---:|
| `ours` | — | 89.07% | — | 604.75 | 139.82 min |
| `ours W3 before W1` | 只对 `plan` 的返回值重排，W1 请求照发 | **94.53%** | **+5.47** | 628.90 | 72.17 min |
| `ours W1 off` | W1 判据恒返回 False | 94.37% | +5.30 | 323.75 | 70.47 min |
| `ours no in_flight veto` | 把 `in_flight` 置空后调 `super().plan` | 88.38% | −0.69 | 1040.25 | 144.36 min |
| `rule__contract` | — | 94.41% | — | 941.80 | 78.91 min |
| `rule__contract W1 off` | 组合臂的 `_w1_intents` 返回空 | 94.28% | −0.13 | 472.00 | 77.20 min |

（前四行的 Δ 相对 `ours`，后两行相对 `rule__contract`。）

**判定：确认，且这是 5.3 点的主因。** 但要注意归因的落点：
W1 请求本身对组合臂几乎无害（−0.13），对单体实现有害 5.30 点；**只重排、不删请求，就拿到 5.47 点。**
所以被证伪的是"W1 让 `ours` 多发命令"这个说法——两臂发的一样多——被确认的是
"W1 在 `ours` 里抢到了那条唯一的、稀缺的下行机会，并同时触发 in-flight 否决"。

### 候选 4：结算 / 证据规则 —— **证伪**

`ours` 的 `settled_version` 规则（"证据必须晚于写入"）在稳态**不改变行为**，只改变一个计数器：

- `ours`：当 `reported == wanted` 时进入 `:1029-1041`。证据新 → `settle/report_postdates_write`（54854.2/运行）；
  证据不新 → `reconciles += 1` 后**仍然** `settled_version[node] = issued_version`、仍然 `continue`
  （`settle/state_right_evidence_absent`，147.7/运行）。两条分支的结果都是"不下发"。
- `rule__contract`：`_settle_on_evidence`（`compose.py:471-488`）在 `payload.get("profile") == book["profile"]`
  时关账，**完全不看 `read_at`**。

因此两条 runtime 在稳态的**结算条件相同**（报告档位＝期望档位），差别只是 `ours` 多记了一笔"证据不到"。
能证伪的读数：把"等证据"这条门去掉（`ttl_s=1`，即 `no_evidence_since_write` 分支永不触发），
覆盖率只动 **+0.44**（89.07% → 89.51%），而该分支实际触发 5904.0 次/运行——它触发得多，但几乎不在关键路径上
（风险窗内节点切档失败的主因是队列，不是等证据）。

`open_books / settled / awaiting_reconcile`（`compose.py:444-460`）在 `none` 轨迹上也不产生差异：
`awaiting_reconcile` 只在 `coordinator_restart` 下有内容，`ours` 侧的 `blocked_until_reconciled` 同理。
**没有任何情形是"`ours` 因为等证据而不再断言、`ContractRuntime` 仍在断言"。**
两者都有一条"无新证据就不写"的规则，且两者在稳态都因为每小时到货的遥测而很快解除。

---

## 五、改一个参数 → 覆盖率与代价怎么动（20 种子，全部在 trajectory `none`）

14 条臂 × 20 种子 = 280 次 72 h 运行。Δ 均相对 `ours`。

| 臂 | 改了什么 | 覆盖率 | Δ覆盖率 | 观测空窗 | 下行/种子 | Δ下行 | 风险类 | 切档延迟 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `ours` | — | 89.07% | — | 6.21% | 604.75 | — | 83.72% | 139.82 min |
| `rule__contract` | 组合实现（对照） | 94.41% | +5.34 | 2.37% | 941.80 | +337.0 | 91.70% | 78.91 min |
| `ours retry_budget=99` | 重试上限 3→99 | 89.53% | +0.47 | 6.24% | 620.45 | +15.7 | 84.41% | 140.47 min |
| `ours dwell_s=0` | 不符等待 300 s→0 | 89.53% | +0.47 | 6.24% | 620.45 | +15.7 | 84.41% | 140.47 min |
| `ours ttl_s=1` | "无证据等待"截止线 6 h→1 s | 89.51% | +0.44 | 5.86% | 624.80 | +20.0 | 84.43% | 131.15 min |
| `ours status_max_age_s=86400` | 状态新鲜度 1 h→24 h | 89.07% | **+0.00** | 6.21% | 604.75 | **+0.0** | 83.72% | 139.82 min |
| `ours measure_window_mult=1` | W1 请求窗口 2 h→1 h | 89.30% | +0.23 | 6.02% | 936.25 | +331.5 | 84.10% | 139.89 min |
| `ours measure_window_mult=8` | W1 请求窗口 2 h→8 h | 89.33% | +0.26 | 6.89% | 381.85 | −222.9 | 84.13% | 141.47 min |
| `ours enable_backfill=True` | W2 补传下单（默认关） | 89.07% | **+0.00** | 6.21% | 604.75 | **+0.0** | 83.72% | 139.82 min |
| `ours all knobs relaxed` | 五个旋钮全放宽 + W2 开 | 89.49% | +0.42 | 4.64% | 1044.50 | +439.8 | 84.36% | 127.09 min |
| `ours W1 off` | 消融：不再请求测量 | **94.37%** | **+5.30** | 2.52% | 323.75 | **−281.0** | 91.70% | 70.47 min |
| `ours W3 before W1` | 消融：写入排在测量请求之前 | **94.53%** | **+5.47** | 2.73% | 628.90 | +24.1 | 91.91% | 72.17 min |
| `ours no in_flight veto` | 消融：去掉在途否决 | 88.38% | −0.69 | 6.11% | 1040.25 | +435.5 | 82.71% | 144.36 min |
| `rule__contract W1 off` | 消融：组合臂不再请求测量 | 94.28% | +5.21 | 3.12% | 472.00 | −132.8 | 91.51% | 77.20 min |

`measure_window_mult` 两行是同一机制的第二个证据。请求窗口也就是"请求未结"的时长，
所以它直接改请求数量（同样 5 个种子、72 h 的单臂计数：`mult=1` → **192.0** 次请求/运行，
`mult=2`（默认）→ **96.0**，`mult=8` → **32.0**）。窗口由 2 h 拉到 8 h 后请求少了 2/3，
被否决的节点·tick 随之减少，覆盖率 +0.26 而下行从 604.75 掉到 381.85；反过来缩到 1 h
则请求翻倍（192 次）、下行涨到 936.25、覆盖率只 +0.23。
这就是"请求量 → 否决时长 → 切档延迟"的单调关系，虽然幅度远小于重排。

---

## 六、机制链条（一句话一条读数）

1. 曲线损失全部在风险窗需求上：14 条臂的常态类命中数都是 141.7–141.9 / 142（100%），风险类 82.7%–91.9%。
2. 风险窗失败几乎全部是"窗口开的时候档位还没切过去"：`ours` 有 22.64% 的风险需求在窗口开启瞬间**该组没有任何节点**在 `risk` 档，
   `rule__contract` 是 11.04%；两臂的切档平均延迟分别是 139.82 min 与 78.91 min。
3. 延迟差 60.91 min ≈ 常态档上行周期 3600 s：节点在风险窗开启时仍在常态档，每小时只有一次下行机会，
   而 `downlink_per_uplink=1` 且 `_deliver` 只取队首 `queue[0]`，所以多一条命令排在前面＝切档晚一个小时。
4. 那条多出来的命令就是 W1：96 次/运行，`ours` 把 `request_measurement` 排在 `set_monitoring_profile` 之前；
   `RulePlanner.decide` 顺序相反（`compose.py:144-149`）。
5. 否决把它放大：`RuntimePolicy` 在 `in_flight` 时拒绝写入（`policies.py:1043-1045`），
   `ContractRuntime` 没有这条；`skip/in_flight` 7827.9 次/运行里 85.3%（6676.5）发生在有 W1 请求未结时，
   其中 3891.4 次的需求是 `risk`。
6. 代价方向明确：`ours W1 off` 少花 281.0 次下行且多 5.30 点；`ours W3 before W1` 多花 24.1 次下行且多 5.47 点。
7. 把队首阻塞去掉（`--downlink-per-uplink 2`，只改场景参数，不改代码），`ours` 89.07% → 94.87%，
   两臂差距 5.34 → 0.57 点。**机制本身被直接检验过，而不是只由消融推断。**

---

## 七、我没解释掉的部分

1. **种子间的残余摆动没有分解。** 逐种子上 `rule__contract − ours` 从 −5.12（seed 8）到 +10.47（seed 1、7）。
   `ours W3 before W1` 之后这个差的均值是 −0.13，但逐种子仍在 ±5 之间摆动（seed 4 是 −4.88、seed 18 是 +2.56）。
   这部分与 runtime 无关（同一批臂在 seed 8/17 上一起掉到 76–82%），但我没有找出它由部署的哪一项决定。
2. **"顺序"与"在途否决"没有做完整因子分解。** 我只测了 2 个单因子点 + 1 个（顺序）修复点：
   去掉否决但保留原顺序会让读数**变差** 0.69 点且下行暴涨 435.5 次，这与"否决放大 W1"的说法方向相反，
   说明两者是交互项而不是可加的。要给出准确的分解需要一个 2×2（顺序 × 否决）并加上"否决只对 W1 生效"的第三格，
   而"否决只对 W1 生效"无法用构造参数表达，需要在 `code/monitoring/policies.py` 里改分支——
   按纪律我没有改。
3. **"去掉否决 ⇒ 下行 +435 而覆盖率 −0.69"没查到机制。** 我怀疑是排队积压把机会耗在同值的重复写入上，
   再经由能量模型（`SupplyFleet` 对下行 RX/TX 计费）压低节点可用性，但没有测；本页只用 `none` 轨迹，
   没有能量专项读数支持这个猜测。
4. **W1 在组合臂上收益接近零。** 在组合臂里这 96 次请求换来的覆盖率是 **+0.13 点**
   （去掉后 94.41% → 94.28%），代价是 469.8 次下行机会。为什么同一个请求在组合臂里几乎既不帮助也不伤害、
   在单体实现里却伤害 5.30 点，我给出的解释只有"排序 + 否决"这一条路径，没有排除别的路径。
5. **没测的边界**：`measure_window_mult=8` 让覆盖率微升而观测空窗略升（6.21% → 6.89%），
   这两个指标在这里不同向，我没有解释。

---

## 八、没测的假设与没做完的扫描

前两条要改 `code/monitoring/`，按纪律只记录、不在本页实现；后两条不需要改代码，只是没跑完。

1. **否决的适用范围**：把 `skip/in_flight` 从"任何在途操作"收窄为"在途的 profile 写入"，
   保留对单位置采集请求的放行。这直接检验第七节第 2 条，需要改 `policies.py:1043-1045`。
2. **对称化顺序**：把 `RulePlanner.decide` 改成 W1 在 W3 之前，看组合实现是否也掉 5 点。
   这检验"顺序是主因"是不是只在单体实现里成立，需要改 `compose.py:144-149`。
3. **完整的多槽扫描**：`downlink_per_uplink` 已经是 `run_episode` 的参数，不需要改代码。
   本页只做了 `1 → 2` 一个点（见第一节与第六节第 7 条），确认机制；**没有**做
   `downlink_per_uplink ∈ {1,2,4}` × 14 条臂的完整扫描，因此"第二槽就能拿回 4.77 点、第三槽还剩多少"没有读数。
4. **`ContractRuntime` 读不读 `ttl_s`**：它的 `ttl_s` 字段在 `dispatch` 里从未被读（`compose.py:437, 439` 之后再无出现，
   即组合 runtime 没有"放弃等待"的截止线）。稳态下遥测每小时到货所以不显形，需要一条故障轨迹才能测。
