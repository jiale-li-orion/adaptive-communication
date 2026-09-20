# 论文工作稿

当前稿件围绕**控制失联后持续执行的通信状态、现场证据与执行位置**组织。源端释放是主要正结果，配置回退与精确停止参照说明普通机制足够的范围，Agent 轨迹用于接口失效分析。配置租约和保留视界不再作为待兑现的新算法贡献。

两份稿件独立可读、章节对应，共享 [refs.bib](refs.bib)。本轮重写摘要、引言、问题定义、机制定位、配置评估、讨论与结论，使用现有在册证据；没有新增仿真或模型调用结果。

| 文件 | 版式 | 产物 |
|---|---|---|
| [en/main.tex](en/main.tex) | IEEEtran 双栏 | [英文 PDF](en/main.pdf) |
| [zh/main.tex](zh/main.tex) | article 中文单栏 | [中文 PDF](zh/main.pdf) |

## 论文如何闭环

[RESEARCH_PLAN.md](RESEARCH_PLAN.md) 是当前研究与写作安排，包含已探索方向排除表、一个新增的反馈预算假说，以及三项证据交付：同组件普通组合对照、有限迁移与部署成本、匹配能力的 Agent 接入。它不替代 [CLAIMS](../results/CLAIMS.md) 的主张状态。

当前有可复现的组件正结果。完整系统的独立增量和适用范围仍是决定投稿价值的证据缺口；格式完整与构建通过不代表这些缺口已经完成。老师汇报中的失联配置问题继续保留，后续计划不再承诺配置有效期优于固定 TTL。

## 构建

从根目录运行 `make paper`，或在本目录运行：

```bash
./build.sh
./build.sh en
./build.sh zh
```

英文使用 pdflatex + IEEEtran；中文使用 XeTeX、fontspec 与 Noto Serif CJK SC。当前环境通过 `xetex -fmt=xelatex` 构建，首次运行缓存格式到 `.build/`。构建末尾报告页数、overfull、缺字与未定义引用。

## 结果到正文

稿件通过 `\input` 引入生成表体和事实宏，生成器为 [`scripts/make_tables.py`](../scripts/make_tables.py)。

| 内容 | 数值来源 |
|---|---|
| 资源反事实表 | `results/r30c_walls.json` |
| 记录到期表 / C3 正文宏 | `results/r41_expiry_equiv.json` / `results/r37e_full_seeds.json` |
| 配置回退表 / C5 正文宏 | `results/c5_matrix.json` |
| 在线归因表 | `results/r40_local_attribution.json` |
| 位置对照表 | `results/agent_traces/r39_table.json` |
| C9 停止参照统计宏 | `results/c5_seqref.json` |

生成物在 `generated/` 入库，不手改。运行 `make tables ARGS=--check` 核对生成链，`make check` 核对仓库检查与联合层锚点。后续实验的期望收益只写在研究计划中，不进入摘要或结果段。

历史版本通过 Git 与 `results/_withdrawn/` 定位；`adae80d` 保存本轮主线重写前的稿件与入口。作者本地 `docs/` 不是复现依赖。
