# Agentic Communication paper workspace

状态：**current working draft**。这里承载当前 Evidence-Grounded Closed-Loop Agentic Communication 论文，不替换 `paper/en/` 与 `paper/zh/` 的历史系统论文工作稿。

## Authority

正文定义与实验协议从以下文件读取：

- `research/EXPERIMENT-DESIGN-v1.md`
- `research/SYSTEM-MODEL-v1.md`
- `research/OWNERSHIP-v1.md`
- `research/COMMUNICATION-DOMAIN-REGISTRY.v0.1.json`
- `research/AGENTIC-BASELINE-REGISTRY.v1.json`
- `research/AGENTIC-BENCHMARK-SPLIT.v1.json`
- `research/AGENTIC-ROBUSTNESS-MATRIX.v1.json`
- `research/AGENTIC-ATTRIBUTION-PROTOCOL.v1.json`

数字与表格只从 `results/agentic/` 的 frozen result 生成：

- `paper/generated/agentic_facts.tex`
- `paper/generated/table_agentic_o2_*.tex`
- `paper/generated/table_agentic_robustness.*.tex`
- `paper/generated/table_agentic_task_transfer.*.tex`
- `paper/generated/table_agentic_attribution_infra.*.tex`
- `paper/generated/table_agentic_v6_confirmatory.*.tex`（仅在正式 confirmatory `audit.json=PASS` 后生成）

禁止手抄实验数字到正文。

## Current claim ceiling

当前正文 claim ceiling 为 `results/CLAIMS.md` A7–A11。A1–A6 继续承担 runtime/fairness/infrastructure 证据；A7–A11 已覆盖 v6 live-model main table、same-interface WirelessOpsAgent-style comparison、held-out task/source/model transfer，以及 DeepSeek/MiMo query-positive evidence-acquisition loop。

论文不得把 A7 解释成复杂多候选推理：123/123 Method requests 均只有一个 ready supported plan 且 visible EvidenceNeed 为空。A8 只支持同可靠性下的模型成本差异，不支持“比 WirelessOpsAgent 更可靠”。A10/A11 只支持一个 frozen gateway-backup acquisition family 的双模型闭环，不支持全局最优 evidence acquisition。

当前方法进入 paper freeze。novelty boundary 由 `research/NOVELTY-BOUNDARY-v1.md` 约束；basis-selection side study 已因 frozen workloads 不存在真实 alternative-proof choice 而按 kill criterion 终止。模型实验始终禁止回退 scripted consumer。

## Build

```bash
cd paper/agentic/en
pdflatex -interaction=nonstopmode main.tex
BIBINPUTS=../..: bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

构建前建议：

```bash
make tables ARGS=--check
make check
```
