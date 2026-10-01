# Agentic Communication paper workspace

状态：**current working draft**。这里承载当前 Evidence-Grounded Closed-Loop Agentic Communication 论文，不替换 `paper/en/` 与 `paper/zh/` 的历史系统论文工作稿。

## Authority

正文定义与实验协议从以下文件读取：

- `research/EXPERIMENT-DESIGN-v1.md`
- `docs/s6-model/system-model.md`
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

禁止手抄实验数字到正文。

## Current claim ceiling

当前可以写入 Results 的是 runtime/physics conformance、Context materialization、deterministic baseline overhead、source-period/robustness gate、source-derived Operational Task transfer、attribution-protocol infrastructure。

当前**不能**写成完成结果的是 LLM model quality。仓库已有 `communication-planner-json-v1` protocol、R1/R3 CLI 和三-context frozen inputs，但当前环境无 endpoint/key；模型分数必须来自真实 backend run，不能回退 scripted consumer。

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
