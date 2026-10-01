# 论文工作稿

当前论文主线已经进入 **Evidence-Grounded Closed-Loop Agentic Communication**。新主稿位于 [`agentic/en/main.tex`](agentic/en/main.tex)；原 `en/`、`zh/` 两份系统论文工作稿继续保留，用于历史机制/claim 追溯，不被当前稿覆盖。

历史系统稿围绕**控制失联后持续执行的通信状态、现场证据与执行位置**组织。源端释放是主要正结果，配置回退与精确停止参照说明普通机制足够的范围，Agent 轨迹用于接口失效分析。配置租约和保留视界不再作为待兑现的新算法贡献。当前 `agentic/` 稿在这套物理与实验底座上进一步组织 Evidence World、Operational Task、typed Capability、Agent Runtime 与 Communication $\times$ Agent evaluation。

三份工作稿共享 [refs.bib](refs.bib)，但主张边界分开：旧中英文稿保留系统阶段证据；Agentic 英文稿只使用已经冻结的 Agentic deterministic/infrastructure 结果，并把真实模型结果明确留空。

| 文件 | 定位 | 版式 | 产物 |
|---|---|---|---|
| [agentic/en/main.tex](agentic/en/main.tex) | 当前 Agentic Communication 工作稿 | IEEEtran 双栏 | [英文 PDF](agentic/en/main.pdf) |
| [en/main.tex](en/main.tex) | 历史系统论文英文工作稿 | IEEEtran 双栏 | [英文 PDF](en/main.pdf) |
| [zh/main.tex](zh/main.tex) | 历史系统论文中文工作稿 | article 中文单栏 | [中文 PDF](zh/main.pdf) |

## 论文如何闭环

本目录当前保存**原系统论文工作稿及其历史研究计划**。`RESEARCH_PLAN.md` 与 `AGENT_RESEARCH.md` 现在是 compatibility pointer，原正文已进入 `paper/_archive/`；它们继续服务旧代码/claim 追溯，不再拥有当前 Agentic Communication 的实验顺序。

当前 Agent 研究与实验工程请从 [`../research/README.md`](../research/README.md)、[`../research/EXPERIMENT-DESIGN-v1.md`](../research/EXPERIMENT-DESIGN-v1.md) 和 [`../research/ROADMAP.md`](../research/ROADMAP.md) 开始。`agentic/` 正文只引用已经冻结并通过 audit 的 deterministic/infrastructure 结果；真实 LLM 结果仍为空，因为当前环境没有可用 endpoint/key，任何 scripted backend 都不得冒充模型分数。

当前有可复现的组件正结果。完整系统的独立增量和适用范围仍是决定投稿价值的证据缺口；格式完整与构建通过不代表这些缺口已经完成。老师汇报中的失联配置问题继续保留，后续计划不再承诺配置有效期优于固定 TTL。

## 构建

当前 Agentic 主稿从根目录运行：

```bash
make agentic-paper
```

历史系统稿运行 `make paper`，或在本目录运行：

```bash
./build.sh
./build.sh en
./build.sh zh
```

英文使用 pdflatex + IEEEtran；中文使用 XeTeX、fontspec 与 Noto Serif CJK SC。当前环境通过 `xetex -fmt=xelatex` 构建，首次运行缓存格式到 `.build/`。构建末尾报告页数、overfull、缺字与未定义引用。

## 结果到正文

稿件通过 `\input` 引入生成表体和事实宏。历史系统论文数字由 [`scripts/make_tables.py`](../scripts/make_tables.py) 生成；当前 Agentic Communication 结果由 [`scripts/make_agentic_artifacts.py`](../scripts/make_agentic_artifacts.py) 从 `results/agentic/*/{aggregate,audit,source_manifest}.json` 生成。后者同时生成 `paper/generated/agentic_facts.tex`，供正文引用 Agentic 数字时使用，并维护 `research/README.md` 和 `results/README.md` 的受控区块，避免实验数字在结果、研究入口和论文表之间漂移。

| 内容 | 数值来源 |
|---|---|
| 资源反事实表 | `results/r30c_walls.json` |
| 记录到期表 / C3 正文宏 | `results/r41_expiry_equiv.json` / `results/r37e_full_seeds.json` |
| 配置回退表 / C5 正文宏 | `results/c5_matrix.json` |
| 在线归因表 | `results/r40_local_attribution.json` |
| 位置对照表 | `results/agent_traces/r39_table.json` |
| C9 停止参照统计宏 | `results/c5_seqref.json` |
| Agentic O2 global conformance 表 | `results/agentic/o2-risk-escalation-v1/aggregate.json` + `audit.json` |
| Agentic O2 localized Context 表 | `results/agentic/o2-localized-risk-escalation-v1/aggregate.json` + `audit.json` |
| Agentic O2 deterministic baseline matrix | `results/agentic/o2-baseline-matrix-v1/aggregate.json` + `audit.json` |
| Agentic source-period gate | `results/agentic/source-period-smoke-v1.json` |
| Agentic five-axis robustness gate | `results/agentic/robustness-matrix-v1/aggregate.json` + `audit.json` |
| Agentic source-derived task transfer | `results/agentic/task-transfer-qili-v1/aggregate.json` + `audit.json` |

生成物在 `generated/` 入库，不手改。运行 `make tables ARGS=--check` 会同时核对旧表、Agentic 新表、研究摘要和结果登记；`make check` 核对整仓检查与联合层锚点。后续实验的期望收益只写在研究计划中，不进入摘要或结果段。

O2 当前端到端流水线可直接运行：

```bash
make agentic-o2
# 或覆盖种子：make agentic-o2 AGENTIC_SEEDS=0,1,2,3,4
make agentic-baselines
make agentic-robustness
make agentic-transfer
```

历史版本通过 Git 与 `results/_withdrawn/` 定位；`adae80d` 保存本轮主线重写前的稿件与入口。作者本地 `docs/` 不是复现依赖。
