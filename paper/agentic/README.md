# Agentic Communication paper workspace

状态：**buildable historical Agentic manuscript snapshot / not current paper control plane**。这里保存 2026-10-02/03 收敛出的 Evidence-Grounded Closed-Loop Agentic Communication 稿件。当前 2026-10-09 paper control plane 已转到 `research/workstreams/PAPER-SYNTHESIS.md`：A benchmark + B direct ASC Future-Choice + C independent external mission validation；`results/CLAIMS.md` F1–F7 是下一版 Future-Choice claim ceiling。

## Authority

正文定义与实验协议从以下文件读取：

- `research/README.md`
- `research/substrate/SYSTEM-MODEL-v1.md`
- `research/compiler/RUNTIME-DOMAIN-OWNERSHIP-v1.md`
- `research/compiler/COMMUNICATION-DOMAIN-REGISTRY.v0.1.json`
- `research/policy/BASELINE-REGISTRY.v1.json`
- `research/benchmark/CONFORMANCE-SPLIT.v1.json`
- `research/benchmark/CONFORMANCE-ROBUSTNESS-MATRIX.v1.json`
- `research/evaluation/AGENTIC-ATTRIBUTION-PROTOCOL.v1.json`

数字与表格只从 `results/agentic/` 的 frozen result 生成：

- `paper/generated/agentic_facts.tex`
- `paper/generated/table_agentic_o2_*.tex`
- `paper/generated/table_agentic_robustness.*.tex`
- `paper/generated/table_agentic_task_transfer.*.tex`
- `paper/generated/table_agentic_attribution_infra.*.tex`
- `paper/generated/table_agentic_v6_confirmatory.*.tex`（仅在正式 confirmatory `audit.json=PASS` 后生成）

禁止手抄实验数字到正文。

## Current claim ceiling

**本快照正文**的 claim ceiling 仍为 `results/CLAIMS.md` A7–A11；它不会自动吸收后续 F* 结果。**下一版 manuscript** 的 current method/transfer ceiling 由 `results/CLAIMS.md` F1–F7 + Layer-1 B* 共同定义，综合结构见 `research/workstreams/PAPER-SYNTHESIS.md`。

论文不得把 A7 解释成复杂多候选推理：123/123 Method requests 均只有一个 ready supported plan 且 visible EvidenceNeed 为空。A8 只支持同可靠性下的模型成本差异，不支持“比 WirelessOpsAgent 更可靠”。A10/A11 只支持一个 frozen gateway-backup acquisition family 的双模型闭环，不支持全局最优 evidence acquisition。

A7–A11 对应的方法与结果在本稿内冻结；novelty boundary 由 `research/compiler/NOVELTY-BOUNDARY-v1.md` 约束，basis-selection side study 仍按既有 kill criterion 关闭。这个 freeze 不外推到整个项目：新的 Layer 1 Decision Benchmark 一旦建立，下一版稿件可以重新组织 benchmark、compiler 与 policy 的证据层级。模型实验始终禁止回退 scripted consumer。

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
