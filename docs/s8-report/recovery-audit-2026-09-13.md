# 恢复对照公平性与收益归因：核查报告

日期 2026-09-13。核查对象是 `bae79e6`（`docs/s8-report/status-2026-09-13.md`）里的结论。
**本报告取代该报告的第一、四、六节。** 场景与实验资产全部保留，定稿继续暂停。

---

## 一、一句话结论

**"跨重启领先成熟基线 14.1 个点"不成立，它反转成落后。** 那 14.1 个点由两个实现属性之差构成：
基线把版本计数器存在进程内存里，而本文 runtime 的状态从未离开过那个活着的 Python 对象。给
基线一台真的设备影子之后它完全恢复（75.00% → 96.34%），而本文去掉"进程还活着"这个条件后掉到
73.56%。

**另外，稳态差距里也有一个属于本文自己的缺陷。** 无故障轨迹上"成熟基线领先 7.2 个点"中有
**5.5 个点是本文的下发排序缺陷**（测量请求被排在档位写入之前，占掉了 Class A 唯一的一次下行
机会）。修好之后差距是 **1.81 个点**，且基线的下行开销只有本文的 0.6 倍。

**因此按 D8 闸门仍然走"收缩主张"，但理由换了**：不是"成熟设备管理全面追平、不能硬写性能
优势"，而是"基线在每一条轨迹上都领先，而且更省"。**目前没有任何一处经公平对照仍然成立的
本文优势。**

---

## 二、你核对出的四条，逐条复核

| 你的判断 | 复核结果 |
|---|---|
| 14.1 点混了执行方法、是否持久化、身份版本能否恢复三个因素 | **成立**。`policies.py` 里 `VersionedConfigPolicy.on_restart` 清空 `desired/desired_version/issued_version/identities/reported`，而 `RuntimePolicy.on_restart` 只加计数，全部状态留在对象里，`durable_storage = True` 只是把它标成"有持久化" |
| 模型没有证明本文保留的状态能从日志重建 | **成立，而且比你说的更糟**。journal 的 `register` 条目只记接口参数（`profile` / `generation` / `path`），**远端据以 fence 的 `contract_logical` 与 `contract_version` 根本不进日志**。见第四节 |
| 同表 VTC 重启后仍 93.3%，高于本文，"不能只挑掉到 75.0 的对手" | **成立，而且 VTC 更强**：它**完全不需要持久化**就免疫重启（`vtc_style` 与 `vtc_style_durable` 读数逐列相同），因为它根本不用版本字段，远端没有东西可以 fence 它 |
| oracle 已恢复为上界 | **不成立，你的反驳成立**。`business3` 无故障轨迹：版本化配置 **96.34%**，oracle **95.12%**。oracle 是参考策略，不是上界 |
| 单体与组合式的 5.3–5.8 点是实现或策略差异，不能只沿重启路径定位 | **成立，并已定位到根因**。无故障时就已经差 5.34 点（89.07 对 94.41），重启只是让同一差距继续存在。根因是下发顺序，见第五节 |
| `ablate20.json` 的 63.0 / 72.71 与新主表不同，不能拼接 | **成立**。该文件由旧代码产出：同一臂同轨迹同种子，`ours` 记 63.00 / 下行 682.5，而当时代码给 89.07 / 604.8。**覆盖与下行两列都不一致**，所以不是评分口径问题而是运行不同。已撤入 `_withdrawn/` 并重跑 |
| 结果索引明确全部是开发区间种子 | **成立**。`results/README.md` 已写明：种子取自开发区间 0–999，测试区间（seed ≥ 10000）除一致性审计外未被触碰。**本报告没有新增任何测试区间种子** |

---

## 三、决策问题一：给基线合理的持久化之后，本文还有增量吗

**没有。是落后。**

新增三条只改"记账放在哪里"的臂，方法一行不动：

- `versioned_config_shadow` —— 按 AWS IoT Device Shadow 的文档语义：调和文档在平台上，重启后
  读回来（`desired` / `desired_version` / `identities` / `reported*` 存活），只丢进程内的未决簿记。
- `versioned_config_version_only` —— 只保住版本计数器与当前意图，不留"节点报了什么"。
- `vtc_style_durable` —— 同一套 verify-then-act，背后是持久存储。

```bash
python3 code/experiments/monitoring_trajectories.py --days 3 --seeds 20 \
  --arms versioned_config,versioned_config_shadow,versioned_config_version_only,vtc_style,\
ours,ours_amnesiac,ours_reconstructed,oracle \
  --trajectories none,coordinator_restart --tag fairrestart3
```

| 臂 | 无故障 | 协调者重启 | 差 | 关键观测空窗（重启） | 下行尝试 | fenced |
|---|---:|---:|---:|---:|---:|---:|
| `versioned_config_shadow` | 96.34% | **96.34%** | 0.00 | 1.64% | 372.6 | 0 |
| `versioned_config_version_only` | 96.34% | **96.34%** | 0.00 | 1.64% | 372.6 | 0 |
| `versioned_config`（原基线） | 96.34% | 75.00% | −21.34 | 18.56% | 286.2 | 2.7 |
| `vtc_style` | 93.28% | 93.28% | 0.00 | 2.99% | 250.8 | 0 |
| `vtc_style_durable` | 93.28% | 93.28% | 0.00 | 2.99% | 250.8 | 0 |
| 本文 `ours` | 94.53% | 94.53% | 0.00 | 2.73% | 628.9 | 0 |
| `ours_amnesiac` | 94.53% | **73.56%** | **−20.97** | 19.69% | 430.9 | 0 |
| `ours_reconstructed` | 94.53% | **94.53%** | 0.00 | 2.73% | 628.9 | 0 |
| oracle | 95.12% | 95.12% | 0.00 | 1.66% | 235.0 | 0 |

**"持久保存版本号就够了"还是"必须保存完整操作历史"？两个独立答案都是"只需要版本号"。**

- `versioned_config_version_only` 与完整的 `versioned_config_shadow` **逐列相同**（96.34 / 372.6 /
  47.5 / 1.64）——影子文档里除计数器之外的字段，对恢复没有任何额外贡献。
- `ours_reconstructed` 只消费**每节点两个整数**（最高契约版本 + 那条版本携带的逻辑身份）就恢复
  了全部 20.97 个点。见第四节。

**这条答案削弱而不是加强本文的主张**：任何一条愿意存一个计数器的实现都能拿到同一份恢复能力，
而成熟设备影子本来就存。

---

## 四、决策问题二：本文的恢复状态能从声明的持久来源重建吗

**原来的实现不能，而且缺的不是"证据"是"字段"。**

三处结构性发现：

**一、`RuntimePolicy.on_restart` 什么都不重建。** 它只加计数、更新 `awaiting_reconcile`。状态
之所以还在，是因为 runner 传的是同一个策略对象，而 runner 用的是同一个进程。

**二、journal 里没有远端据以 fence 的字段。** `AgentInterface._enqueue` 写入的 `register` 条目
只有 `arguments_hash=str(sorted(record.parameters.items()))`，而 `parameters` 是
`{profile, generation, path}`——`generation` 还是 runner 自己的全局计数器。**策略放在报文上的
`version` 与 `logical` 从未经过接口层，因此从未进过日志。** 无论怎么回放都重建不出一个不被
fence 的发送方。

**修法。** `JOURNAL_SCHEMA` 的 `register` 由 v1 升到 **v2**，加 `contract_logical` 与
`contract_version`；`_check_fields` 是双向精确的，所以 **v1 日志会被明确拒绝**而不是被猜着读。
新增 `operations.replay_contract_state(journal)`：只取每个实体的版本高水位与那条版本的逻辑身份。

**三、`ours_reconstructed` 是"真的死了又活过来"，不是"手写一串 clear()"。** 重启时它把自己交回
构造函数（`self.__init__(**self._constructed_with)`），然后只从 journal 回放重建。读数与
`ours` **逐种子、逐列完全一致**（20 个种子的覆盖率与其他 10 个指标全部相同）。

**受控对照（这才让上面那条成为证据而不是同义反复）**：`ours_amnesiac` 与 `ours_reconstructed`
只差"有没有日志"，前者 `durable_storage = False`（运行本身不给它日志），重启后掉 **20.97** 个点。

**回归测试** `code/experiments/test_recovery.py` 七项：日志带契约字段；日志经 JSON 往返后逐字节
相同且重放结果不变；新对象能从日志重建高水位与逻辑身份；无日志臂两个标量都归零；`memory`
模式行为未变；不接受 `journal` 参数的钩子不被强行传参；`profile_command` 同时带两个契约字段。

**顺带修好的第四处（D39）。** runner 把 `in_flight`（网络侧"命令还没送达"的簿记）直接当成
`view.in_flight`（中心"我知道自己有命令在外"的信念）交给所有臂。协调者重启后命令确实还在网关
里，但一个没有持久化记录的中心不该知道这件事。原实现把这个信念送给了所有臂，等于把重启本该
拿掉的能力还回去。现在拆成 `in_flight`（送达簿记）与 `center_belief`（中心信念，无日志臂重启
时清空）。

---

## 五、决策问题三：单体与组合式究竟差在哪里

**差在一个 tick 内的下发顺序，与重启无关——无故障轨迹上就已经差 5.34 点。**

**机制。** `RuntimePolicy.plan` 在一次调用里先返回 W1 的 `request_measurement`、后返回 W3 的
`set_monitoring_profile`；控制面对每个上行机会**只投递节点队列的队首一条**（Class A 的
`downlink_per_uplink = 1`）；而 `RuntimePolicy` 在节点有在途操作时**否决一切写入**，组合式没有
这条。三者叠加：风险窗开启时节点还在常态档、每小时只有一次下行机会，**这唯一的机会被排在队首
的测量请求占掉，切档整体推迟一个常态档上行周期**。

**证据（trajectory `none`，72 h，20 种子；完整版见 `docs/s8-report/q3-steady-state-gap.md`）。**

| 检验 | 读数 |
|---|---|
| 损失的位置 | 14 条配置的常态类命中数全部 141.7–141.9 / 142（**100%**），差异全在风险窗需求（82.7%–91.9%） |
| 切档延迟 | `ours` 139.82 min 对 `rule__contract` 78.91 min，**差 60.91 min ≈ 常态档上行周期 3600 s** |
| 只重排、不改任何参数 | `ours` 89.07% → **94.53%**（下行 604.75 → 628.90） |
| 参数逐项放宽 | **没有一条能到 94%**：最大 +0.47（`retry_budget=99` 与 `dwell_s=0` 读数逐位相同），五参数全放宽 +0.42 |
| 死参数 | `status_max_age_s`（1 h→24 h）与 `enable_backfill=True` 都是 **+0.00**；`wait/dwell` 分支稳态触发 **0 次** |
| 两臂发的测量请求 | **完全一样**（96.0 次/运行，逐种子无差异）——差别只在排在哪个位置 |
| 否决的规模 | `skip/in_flight` 7827.9 次/运行，其中 **85.3%** 发生在有 W1 请求未结时，3891.4 次的需求是 `risk` |
| 代价方向 | `ours` 关掉 W1 少花 **281.0** 次下行且 **+5.30 点**；而 W1 在组合臂里只值 **+0.13 点** |
| 不改代码的机制检验 | 把场景参数 `--downlink-per-uplink` 提到 2（非结论，仅用于检验队首阻塞），`ours` 89.07% → **94.87%**，两臂差距 5.34 → **0.57** 点 |

**修法。** `RuntimePolicy.plan` 返回前按接口优先级稳定排序：**档位写入 → 测量请求 → 补传下单**。
档位写入是唯一改变节点回访频率的命令，它既让窗口后半段可观测，又会产生那条测量请求本来想要的
样本。**修正后单体 94.53% 与组合格 94.41% / 94.92% 基本持平，那条"5.3–5.8 点的实现分歧"消失。**

**这是缺陷不是调参**：一个"先要样本、再换档位"的顺序，在"一个机会只投一条、且写入被在途操作
否决"的链路上，等于把换档推后一个周期；而 `RulePlanner.decide` 的顺序本来就是反的，
所以两条实现此前读的是**不同的策略**，却被并排放在 §7.30 的同一张表里。

**没查清的部分（照录，不含糊）**：种子间残余摆动（`rule__contract − ours` 从 −5.12 到 +10.47）
未分解；"顺序 × 在途否决"没做完整因子分解（单独去掉否决反而 −0.69 点、下行 +435.5，方向相反）；
"去掉否决导致下行暴涨"的二次机制没查（怀疑走能量模型，未测）；W1 在组合臂里几乎零收益却吃掉
469.8 次机会，只给了"排序 + 否决"一条解释路径。

---

## 六、修正后重量的读数

**业务层五臂（`--tag business3`，20 种子，七条轨迹）**

| 轨迹 | 本地规则 | 版本化配置 | VTC 风格 | 本文 | oracle |
|---|---:|---:|---:|---:|---:|
| 无故障 | 49.2 | **96.3** | 93.3 | 94.5 | 95.1 |
| `request_lost` | 49.2 | 95.8 | 92.5 | 93.5 | **96.0** |
| `ack_lost` | 49.2 | 96.3 | 93.3 | 94.5 | **96.3** |
| `stale_command` | 49.2 | 96.3 | 93.2 | 94.5 | 95.1 |
| **`coordinator_restart`** | 49.2 | **75.0** | 93.3 | 94.5 | 95.1 |
| `node_restart` | 49.2 | 96.1 | 93.4 | 94.8 | 95.4 |
| `backhaul_only` | 49.0 | 96.2 | 92.9 | 94.7 | 95.8 |

**关键变化：本文从五条臂里最低的一条升到第二高**（89.07 → 94.53），下行开销 628.9（基线 372.6）。

**消融（`--tag ablate20v3`）**：`ours`、`ours_no_evidence`、`ours_no_contract` 三条的覆盖率**逐列
相同**（94.53%），唯一的区分在 `stale_command` 上：`ours_no_contract` 出现 0.25 次陈旧乱序与
0.05 次覆盖回退，其余四条臂都是 0。**契约字段承的是"不产生顺序违规"，不是覆盖率。**

---

## 七、这一轮撤销或改写的结论

1. **"跨重启领先 14.1 个点"作废**（原状态报告 §一、§四）。公平化后反转成落后 1.81 个点。
2. **"设备影子擅长维持当前状态，不擅长重建我做过什么"作废**（§一）。它把基线的实现缺陷当成了
   方法边界。
3. **"本文 runtime 对协调者重启免疫"作废**（§四）。它靠的是同一个 Python 对象；去掉这个条件后
   掉 20.97 个点。
4. **"稳态差距 7.2 个点"改写为 1.81 个点**（§四、§六）。其中 5.5 个点是本文的下发排序缺陷。
5. **"5.3–5.8 点的实现分歧未查清"作废**（§六"需你决定的三件事"第 2 项）。已定位到下发顺序，
   修好后两条实现持平。
6. **"oracle 已恢复为上界"作废**（§四）。96.34% > 95.12%。
7. **"决定结果的是远端契约，不是 runtime 内部机器"撤回**（§四）。四条消融与本文读数相同，只能
   说明冗余或未被触发，不能反推归因（新增 D40）。
8. **"消融已与定稿主表对齐"作废**。`ablate20.json` 与主表两列都不一致，已撤下并重跑。
9. **两条实现不再可以混在一张表里比较**——这条限制现在解除了，因为它们的差别是缺陷已被修掉。

---

## 八、路线判定

按你给的四行判定表：

| 核查结果 | 本轮实际读数 | 判定 |
|---|---|---|
| 简单持久化/版本恢复就消除优势 | **是**：`versioned_config_version_only` 完全恢复（96.34%），比本文高 1.81 个点 | **命中** |
| 公平恢复后特定真实任务仍需要额外操作历史，且本文有成本优势 | 否：本文只需要两个标量，与"存一个计数器"同价；且本文下行开销是基线的 1.7 倍 | 不成立 |
| 算法优势消失，但能系统揭示多类方案的能力边界 | 目前能说的是"这一套场景下没有优势"；是否构成可发表的评测贡献，本轮没有做也不足以判断 | 待评估 |
| 优势持续依赖基线缺陷或实现分歧 | 是，两处都命中了 | **命中** |

**因此：停止把跨协调者生命周期作为本文独有贡献；保留工程成果；不自动转投评测论文。**
第二行不成立意味着"收缩主张"也不成立——没有剩下可收缩的边界。

---

## 九、产物与复现

| 产物 | 内容 |
|---|---|
| `code/monitoring/policies.py` | 新臂 `versioned_config_shadow` / `versioned_config_version_only` / `vtc_style_durable` / `ours_amnesiac` / `ours_reconstructed`；`RuntimePolicy` 的 `durability` 三态；下发顺序优先级排序 |
| `code/runtime/operations.py` | `JOURNAL_SCHEMA` register v2（`contract_logical` / `contract_version`）；`replay_contract_state()` |
| `code/monitoring/interfaces.py` | `set_monitoring_profile` 接契约字段并写入日志；`replay_contract_state()` |
| `code/monitoring/runner.py` | 重启钩子按需传 journal；`center_belief` 与 `in_flight` 拆开 |
| `code/experiments/test_recovery.py` | 新增 7 项恢复回归测试（`run_checks.py` 现 17/17） |
| `results/monitoring_trajectories_business3.json` | 业务层定稿表（§六） |
| `results/monitoring_trajectories_fairrestart3.json` | 恢复归因定稿表（§7.33） |
| `results/monitoring_trajectories_ablate20v3.json` | 消融重跑（§7.35） |
| `results/steady_gap_q3_attrib.json` 等三件 | 稳态归因（§7.34） |
| `docs/s8-report/q3-steady-state-gap.md` | 稳态归因完整文档（含未解释项） |
| `README.md` | 新增 D37–D40 与 §7.33 / §7.34 / §7.35；§7.30 标注作废；§六 两张主表换成 `business3` |
| `results/_withdrawn/MANIFEST.md` | 新撤下五个文件及逐条理由 |

复现：`export PYTHONPATH="$PWD/libs/pylibs"`，然后

```bash
python3 code/run_checks.py                                   # 17/17
python3 code/experiments/monitoring_trajectories.py --days 3 --seeds 20 \
  --arms local_rules,versioned_config,vtc_style,ours,oracle --tag business3
python3 code/experiments/monitoring_trajectories.py --days 3 --seeds 20 \
  --arms versioned_config,versioned_config_shadow,versioned_config_version_only,vtc_style,\
ours,ours_amnesiac,ours_reconstructed,oracle \
  --trajectories none,coordinator_restart --tag fairrestart3
python3 code/analysis/steady_gap.py --seeds 20 --tag q3_attrib
```

**全部种子的取值落在开发区间 0–999。测试区间（seed ≥ 10000）本轮未被触碰。**

---

## 十、仍然缺的东西（不比上面三条更优先，但记下来）

- **真实 LLM planner**：仍缺 `OPENAI_API_KEY`，`scripted` 后端的数字一律不得当模型证据。
- **"顺序 × 在途否决"的完整因子分解**：本轮只做到"重排能解释 5.47 点"，没做到干净分离两个因子。
- **W1 该不该发**：`ours` 关掉 W1 少花 281.0 次下行且多 5.30 点，`rule__contract` 的 W1 只值
  0.13 点。**这看着像第二个同类缺陷**（与 §7.23/D32 的补传下单同构），但"要不要发测量请求"
  是设计决策不是排序问题，本轮没有替你做。
- **论文六组产物**里仍缺：效果发生但回执丢失的时间线、实体/依赖图、完整失败案例、讨论节。
- **`disruption_env.py:270`** 的 `alive` 覆盖缺陷与 `energy.py` 构造期初值被静默截断两处未修。
