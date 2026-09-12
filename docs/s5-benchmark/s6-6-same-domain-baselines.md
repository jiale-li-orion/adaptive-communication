# 同领域可复现 baseline 清单（已逐库核验）

> ℹ️ **baseline 池以 [`../README.md`](../README.md) §3.2 为准。**
> 本文档列出的可复现同领域清单**仍然有效**；
> 但其中「第一层/第二层」划分已被 FRAMING 取代——
> 第一层应是 **agentic-communication 方法**。


**核验方式**：GitHub 仓库实际解析 + 目录内容检查 + raw 文件抓取，2026-09-12。
**用途**：确定论文的同领域 baseline，以及可复用的环境与 benchmark。

---

## 一、同领域、有已验证代码的工作

按"能否做我们的 baseline"排序。

### 第一梯队：有论文 + 有代码 + 任务类型相关

| # | 论文 | 会议/期刊 | 代码（已核验内容） | 它的 baseline | 数据/环境 |
|---|---|---|---|---|---|
| **1** | **LMTE**（arXiv 2602.00941） | **IEEE INFOCOM 2026** | `Y-debug-sys/LMTE`：`cl_baselines/`、`ml_baselines/`、`src/`、`lms/`、`scripts/`、`main.py`、Apache-2.0 | **Gurobi 经典解**（COPE / oblivious / optimal）+ 学习式 baseline | GÉANT +4 TE 数据集；LLaMA-3 |
| **2** | **NetConfArena**（arXiv 2608.23179） | arXiv | `liujona/NetConfArena`：**364 文件**；`agent/react.py`、`agent/configs/ReAct.yaml`、`mcp_server/`、`environment/gns3_project.py`、Apache-2.0 | **ReAct vs OneShot**（含完整 prompt 与工具定义） | **GNS3**；96 模板 → 480 实例 → 3840 轨迹；⚠️ 需专有 Cisco 镜像 |
| **3** | **NetArena**（arXiv 2506.03231） | **ICLR 2026** | `Froot-NetSys/NetArena`：`a2a_llm/`、`app-k8s/`、`app-malt/`、`app-route/`、`src/netarena/`、43★ | prompt-based agent vs A2A 框架（agent 平均只拿 13–38%） | **Mininet + Kubernetes**；动态生成查询 |
| **4** | **NIKA**（arXiv 2512.16381） | arXiv | `sands-lab/nika`：**1662 文件 / 1456 代码**，58★ | SOTA LLM agent（可插拔） | **Kathará + Containerlab**；5 场景 54 故障 |
| **5** | **NetOpsBench** | 无同行评审论文 | `NetX-lab/NetOpsBench`：**373 文件 / 307 代码**，30★，**MIT** | 统一评测器（检测/定位/效率/工具使用） | **SONiC-VS + Containerlab**；HF 轨迹数据集 |
| **6** | **WirelessAgent**（arXiv 2505.01074） | **IEEE/CIC China Communications 2026** | **`jwentong/WirelessAgent_R1`**：16 代码文件，47★ | prompt-based + rule-based 最优 | 射线追踪 CQI + 网络切片场景 |
| **7** | **WirelessAgent++ / WirelessBench**（arXiv 2603.00501） | arXiv | `jwentong/WirelessAgent-R2`：**298 文件 / 119 代码**，**MIT** | SOTA prompting + 通用 workflow 优化器 | **WirelessBench（3,392 题）**；MCTS 工作流搜索 |

### 第二梯队：顶会顶刊、有代码，但任务类型偏离

| # | 论文 | 会议/期刊 | 代码 | 说明 |
|---|---|---|---|---|
| 8 | **NetLLM**（arXiv 2402.02338） | **ACM SIGCOMM 2024** | `duowuyms/NetLLM`：**4249 文件**，205★，MIT | LLM 适配（非 agentic）；baseline 是 A3C / CNN / LSTM |
| 9 | **NetConfEval** | **ACM CoNEXT 2024** | `RedHatResearch/conext24-NetConfEval`：124 文件，42★，MIT | 5 类配置任务；有 reproducible `artifact/` 脚本 |
| 10 | **Cellular-X**（arXiv 2504.13190） | **ACM MobiSys 2025**（demo） | `SeaBreezing/Cellular-X`：11 代码文件 | **真实 USRP + srsRAN LTE testbed**；RAG vs 非 RAG |
| 11 | **ORION**（arXiv 2603.03667） | arXiv | **6 个仓库**，其中 `orion-xapp` 1092 代码文件（C++/ASN1c） | O-RAN SMO + rApp + xApp + E2Sim |

### 明确找不到代码的

- **"Rollback Is Not Undo"（IEEE INFOCOM 2026）** —— 闭源，无 artifact（已核实 CLOSED）
- Network CoPilot（INFOCOM 2025）、RIDAS、RepLLM（SIGCOMM 2026）、MobiLLM
- **任何 IEEE JSAC / TCOM / TWC / TMC 2024–2026 的 LLM-agent 公开 artifact** —— **一个都没确认到**
  ⚠️ 但这些期刊很多论文没有 arXiv 版，属**检索盲区，不等于不存在**

---

## 二、关于"顶会顶刊有多常开源代码"的实证

**子代理明确拒绝编造比例**（n=6 太小），这个态度是对的。可信的部分是：

- 手工核对的 6 篇样本里 **3 篇有代码 ≈ 30–50%**，不确定性很大
- **方向性结论稳健**：**benchmark / measurement 类论文开源程度远高于 framework / architecture 类**
  - 四个 agent-network **benchmark**（NetArena / NetConfArena / NIKA / NetOpsBench）**全部开源了实质代码**——因为**benchmark 本身就是贡献**
  - IEEE 期刊/会议的 **framework** 论文多数没开源，ORION 是有代码的例外
- **旁证**：RepLLM（SIGCOMM 2026）自己的 motivation 就写着 **"scarcity of open-source implementations" 是复现网络研究的核心障碍**
  ⇒ **这句话可以直接引用来支撑我们的 baseline 现状说明**

---

## 三、修正后的 baseline 方案

### 第一层 · 同领域（**必需**）

| baseline | 来源 | 搬运成本 |
|---|---|---|
| **B-D1** NetConfArena 的 **ReAct + OneShot harness** | Apache-2.0 | **低**：prompt 与工具定义可直接搬（其工具分类 `get_current_config` 只读 / `apply_config` **副作用** / `execute_validation` 只读 **与我们的完全一致**） |
| **B-D2** WirelessAgent++ 工作流 | MIT | 中：需把 operator 接到我们的环境 |
| **B-D3** NetArena 的 prompt-based agent | ICLR 2026 | 中 |
| B-D4 | LMTE 的**经典 Gurobi 最优** baseline | Apache-2.0 | 中：代表"通信领域的优化方法"这一路 |

### 第二层 · 跨域机制（对照）

| baseline | 来源 |
|---|---|
| B0 | Verified Tool Calls（arXiv 2608.02645，**已实现**） |
| B1 | ReAct（ICLR 2023） |
| B2 | MCP 默认语义（**已实现**） |
| B3 | timeout + blind retry（**已实现**） |

**两层都要，缺一不可。**

### 可复用的 benchmark

| benchmark | 用途 |
|---|---|
| **WirelessBench（3,392 题）** | 证明我们的方法在**领域标准任务**上不退化 |
| NetConfArena / NIKA / NetOpsBench | 可直接对比的**同领域环境** |
| **我们的 disruption benchmark** | 核心 claim |

---

## 四、对我们最有利的一条引用

RepLLM（SIGCOMM 2026）自述的 **"scarcity of open-source implementations"** 加上本次核验结果
（**四个 agent-network benchmark 全开源，但 IEEE 期刊的 framework 论文基本不开源**）
⇒ 可以写成一个**有力且诚实**的现状陈述，同时解释我们为什么这样选 baseline。

---

## 待补

- ⬜ 逐个确认 B-D1 / B-D2 接入我们环境的实际工作量
- ⬜ 确认主实验用哪几个模型（见 §C 的同类论文惯例）

---

# 附录 A · baseline 结构的**正确形态**（子领域惯例，已核实）

## A.1 ⚠️ 一处必须纠正的认识：ReAct 是**脚手架**，不是 baseline

子代理读了 **16 篇** 2024–2026 的 LLM-agent-in-networking 论文全文（逐条 HTTP 核验 artifact 链接），
统计出的**实际惯例**：

| 做法 | 出现率 |
|---|---|
| **前沿模型**（GPT-4o / GPT-5 级）作对照 | **12 / 14** |
| **开源权重模型**（Qwen / Llama）作对照 | **9 / 14** |
| **共享 ReAct 脚手架** | **8 / 14** |
| 经典 / DRL baseline | **仅 5 / 14**，且 NetOps 类论文几乎不用 |
| **人类专家 baseline** | **0 / 14** |

> **⇒ ReAct 通常是"大家共用的脚手架"，baseline 是"模型选择"或"脚手架设计"的消融。**
> **把 ReAct 当 baseline 是错位的**——它是这个子领域的公共地基，不是对手。

**评测方式**：**8/14 自造任务**；共享 benchmark 运动自 2026 起
（NetConfEval / NIKA / NetConfArena / FaulT-Bench / TeleCom-Bench（KDD 2026）/ WirelessOptBench / 6GAgentGym），
另有 IETF NMRG 草案提议把 NetConfBench 作为标准（`draft-cui-nmrg-llm-benchmark-01`）。

**artifact**：8/16 有可访问 artifact，但 3 篇公告链接已坏或受限，5 篇什么都没发；该样本中 IEEE 系的最弱。

## A.2 由此得到的正确 baseline 矩阵

**不要**设计成"我们的方法 vs ReAct"，而应设计成**二维矩阵**：

```
              recovery semantics →
        ┌──────────────┬─────────────┬────────────────┬─────────────┐
model ↓ │ MCP 默认语义 │ blind retry │ verified wrap  │  lifecycle  │
────────┼──────────────┼─────────────┼────────────────┼─────────────┤
前沿模型 │              │             │ (2608.02645)   │  (本文)     │
开源权重 │              │             │                │             │
────────┴──────────────┴─────────────┴────────────────┴─────────────┘
```

- **横向**看：同一模型下，恢复语义带来的差异 → **本文的核心 claim**
- **纵向**看：同一恢复语义下，模型强弱带来的差异 → **claim 2（"更强模型也不会让问题消失"）**

再叠加第一层的同领域对照（B-D1…B-D4），构成完整对比。

## A.3 两个直接好处

1. **claim 2 有了标准做法**：子领域惯例本就是"前沿 vs 开源权重"，正好用来证"换更强模型不解决问题"。
2. **评测方式被接受**：8/14 自造任务 ⇒ **自造 disruption benchmark 合规**；
   但按 `s6-7`，**必须附可执行测试用例，不能只用 LLM judge**。

## A.4 实现成本

| 项 | 状态 |
|---|---|
| 脚手架（ReAct 循环 + MCP 风格工具面 + 可切换恢复语义） | ✅ 已实现（`code/agent_react.py`） |
| MCP 默认语义 / blind retry | ✅ 已实现 |
| verified wrapper（2608.02645） | ✅ 已实现 |
| lifecycle（本文） | ✅ 已实现 |
| 前沿模型 + 中档模型 | ⬜ 待定 |

⇒ **除模型本身外，矩阵骨架已全部就位。**



# 附录 B · 核心跨域 baseline B0：arXiv 2608.02645

**"Verified Tool Calls Improve LLM Agent Reliability Under Non-Atomic Failures"**
Isham Kalappurackal Mansoor, Abhishek Phadke, Pratip Rana — arXiv **2608.02645**, 2026-07-31

## B.1 为什么它是最重要的一条

摘要原文：*"a lightweight, **verification-aware tool wrapper** … augments tool calls with
**postcondition verification, verify-before-retry logic, and idempotency keys**"*，
评价方式是 *"a controlled simulated environment with **injected** non-atomic failures"*，
故障类为 *"timeouts after dispatch, delayed visibility, and partial state updates"*。

⇒ **它是"已发表的最强恢复机制"的代表**。只跟 naive retry 比，审稿人会说赢的是稻草人。

## B.2 它的结构性软肋 = 我们的战场

它靠**后置条件验证**，而验证需要**节点能响应验证查询**。
在我们的地形驱动丢包下：**验证者自己也不可达**。

**实测**（信道属性，与 agent 无关）：

| 信道 | 能量 | 验证尝试 | 返回 unknown | **unknown 占比** |
|---|---|---|---|---|
| i.i.d. | placeholder | 2400 | 999 | 41.6% |
| i.i.d. | real | 2400 | 978 | 40.8% |
| G-E | placeholder | 2400 | 1198 | 49.9% |
| **G-E** | **real** | 2400 | 1212 | **50.5%** |

⇒ **最真实配置下，后置条件验证超过一半次数直接失败**，而**原文没有定义这一分支**。

## B.3 三段式实验设计（本文的脊梁）

| 阶段 | 做什么 | 期望 | 作用 |
|---|---|---|---|
| ① **忠实复现** | 在它自己的**注入式**故障上跑它 | 重复动作下降 | **证明我们的实现忠实**，不是稻草人 |
| ② **换故障生态** | 同一实现，跑在**地形驱动**故障上 | 验证者不可达 → 退化 | 找到它结构性失效的工况 |
| ③ **我们的方法** | lifecycle runtime：durable log + reconcile 处理"验证者不可达" | 恢复正确性 | 给出修复 |

**对照的干净之处**：同一方法、两种故障生态（注入 vs 轨迹驱动）。
贡献边界因此是：**不是"我们有更好的机制"，而是"机制的成败取决于故障分布是否被真实建模"**。

## B.4 实现时必须标注的诚实点

```
verified_wrapper(node, tool):
    key = idempotency_key(intent)
    st, res = call(node, tool, key)
    if st == committed:  return st, res
    if st in (timeout, outcome_unknown):
        v = verify_postcondition(node, tool)      # ← 关键分支
        if v == APPLIED:      return committed, res        # 不重试
        if v == NOT_APPLIED:  return call(node, tool, key) # 同 key 重试
        if v == UNKNOWN:      ???    # ← 原文未定义
```

**最后那个 `???` 分支就是本文入口。** 复现时按**最有利于它的读法**实现（退化为盲目重试），
并**在论文里明确标注**这是我们的补充而非原文规定。

---

# 附录 C · baseline 复现的验收标准

一个 baseline 算"复现成功"，必须满足：

1. **由真 LLM 驱动**，prompt 与工具描述公开可查
2. **有 trace**：每轮 thought / tool / args / observation 全部落盘，可人工审计
3. **不由我们调参**：策略参数（重试次数、退避曲线、超时阈值）取文献或规范默认值，并给出处
4. **可复现**：固定模型版本 + 固定种子 + 固定 episode 集
5. **成本可报**：token 数与调用次数计入 metrics
6. **公平**：同 episode 集、同种子、配对比较；baseline 的自由参数要调，不能冻结在我们的取值上
7. **含退化参照与上界**：至少一个退化方案（如"不重试"）+ 一个上界（如穷举/最优调度）

## 为什么卡住，以及怎么解开

**卡点**：需要真 LLM 驱动。脚本化的 `if value > 11: alert()` 不叫 ReAct。

| 步骤 | 内容 | 状态 |
|---|---|---|
| 1 | 骨架 + mock 验证 | ✅ 已完成 |
| 2 | 极小 pilot（5 episode × 4 策略 × 1 模型） | ⬜ |
| 3 | 主实验（4 策略 × 2–3 个称职模型 × 数十 episode） | ⬜ |
| 4 | 规模扫描 + ablation | ⬜ |

**可复现性提醒**：API 模型即使 temperature=0 输出也非完全确定 ⇒ **必须报多种子 + 置信区间**，
并把**模型版本与调用日期**写进论文。成本控制靠**短 episode**（失效现象在数十轮内就出现）
与 **prompt caching**（system prompt 与工具定义是静态前缀）。

|---|---|
| 1 | 骨架 + mock 验证 | ✅ CPU 已完成 |
| 2 | 选定模型（前沿 1 个 + 中档 1 个） | 待定 |
| 3 | **极小 pilot**：5 episode × 4 策略 × 1 模型 ≈ 20 次运行 | API |
| 4 | 主实验：4 策略 × 2–3 个称职模型 × 数十 episode | API |
| 5 | 规模扫描 + ablation | API |

**成本与可复现性的诚实说明**：
- **API 模型的输出并非完全确定**，即使 temperature=0 ⇒ **必须报多种子 + 置信区间**，并把模型版本与调用日期写进论文
- 成本控制手段：**短 episode**（失效现象在数十轮内就出现，不需要上千轮）、
  **prompt caching**（system prompt 与工具定义是静态前缀）、
  探索期少跑、定稿期再放大、**便宜模型跑批量，前沿模型跑头条对比**

---

## 附 · 其余带代码的工作

除上表外，另经核验有代码的工作：

| 工作 | 说明 |
|---|---|
| `duowuyms/OpenCATP-LLM` | 城市蜂窝容量/流量预测；baseline 为 LLaMA/OPT/Qwen + LoRA 与非 LLM 预测 |
| `dadsetani/llm-safemit` | IEEE TNSM，Zenodo 有 release，但仅 8 文件/3 代码（**很薄**） |
| `frezazadeh/LangChain-RAG-Technology` | ns-3 + 5G-LENA 多 agent；⚠️ **论文自称是"lightweight mock version"，不是完整实现** |
| `secretcheng/HybridRAG-for-Network-Optimization` | ⚠️ **仅有 README + 1 个 notebook**，是 demo 不是实现 |
| `emilbjornson/scalable-cell-free` | TCOM，系数级可复现 |
| `luanedge/WSR-maximization-for-RIS-system` | TWC，**随附 `without_RIS.m`、`RIS_phaserand.m` 作为独立 baseline 脚本** |
| `BJTU-MIMO/Power_Allocation_DDPG` | TVT |
| `zctzzy/STCNet` | JSAC |

**核验方法**：GitHub API + HTML tree 实际解析，确认含真实源文件（`.py/.c/.cpp/.ipynb/.sh` + 构建文件），**不是 README-only**。
**"README-only" 的失败模式在本次核验中未出现**——反而有两篇是"有代码但不可用"（上表末两行）。
