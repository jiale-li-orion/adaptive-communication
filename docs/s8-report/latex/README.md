# 论文工作稿与构建

更新：2026-09-19。当前 `main.tex` / `main.pdf` 为 **v0.6**，对应提交 `3df2845`，PDF 20 页。2026-09-19 的独立审查与方法收敛尚未全部写回正文；本轮整理入口，不改论文或重新编译 PDF。

- [main.pdf](main.pdf)：当前工作稿。
- [main.tex](main.tex)、[refs.bib](refs.bib)：正文与书目源码。
- [doc51：独立审查](../../s7-method/v1.2/51-independent-review-paper-v06-2026-09-19.md)：原始轨迹、合法信息边界、expiry 对照与主张核验。
- [doc52：方法收敛](../../s7-method/v1.2/52-runtime-convergence-assessment-2026-09-19.md)：Execution-Grounded Obligation Runtime 的组织方式及必要修正。
- [修订表](../review-v0.6/revision_log.md)、[最小执行计划](../review-v0.6/experiment_todo.md)：文稿与实验的下一步。

## 当前证据状态

期限清理相对指定 FIFO/latest-only 对照的正结果保留；同期限普通 expiry 的增量尚待判别。R39 支持所测条件下的本地规则部署效果。真实 Agent 11 条轨迹已完成，但证书输入含普通策略指令与额外常量，不能直接归为独立证书收益。

待修正文中的全局最优前沿、合法在线归因 100%、零回退及配置谎报计数等表述，具体证据见 doc51。可编译性与书目格式不代表这些科学问题已闭合。

## 构建

从本目录执行；需要 TeX Live 的 `pdflatex` 与 `bibtex`：

```bash
pdflatex -interaction=nonstopmode main
bibtex main
pdflatex -interaction=nonstopmode main
pdflatex -interaction=nonstopmode main
```

旧 v0.1 入口及其当时证据映射已移入[论文 README 历史快照](../../早期状态/2026-09-19-latex-README-history.md)。项目最新状态见[根 README](../../../README.md)。
