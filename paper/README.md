# 论文工作稿 —— 英文稿 / 中文稿各一份

**当前初稿。** 由 `docs/s8-report/latex/main.tex`（paper v0.8，提交 `59e5ef1`）压缩、剪枝而来：同一条论证链、同一批数字、同一批表格，删去重复陈述与内部过程说明。**未新增任何结果，未改动仿真实现与 `main.tex`。**

两份文档互为独立成稿，结构一一对应，不合并编排：中文稿是独立可读的中文论文，英文稿是独立可读的英文论文。二者共享同一份 [`refs.bib`](refs.bib)。

> **本地材料说明。** 本文件引用的 `docs/…` 路径属于作者本地的过程文档与逐轮审计记录，不随本仓库发布；远端仓库只包含 `paper/`、`code/`、`results/`、`multipath_probe/` 与根 README。

| 文件 | 语言 | 版式 | 页数 |
|---|---|---|---|
| [`en/main.tex`](en/main.tex) → [`en/main.pdf`](en/main.pdf) | 英文 | IEEEtran journal，双栏 | 9 |
| [`zh/main.tex`](zh/main.tex) → [`zh/main.pdf`](zh/main.pdf) | 中文 | article，单栏 | 14 |

## 构建

```bash
./build.sh          # 两份都构建
./build.sh en       # 只构建英文
./build.sh zh       # 只构建中文
```

英文用 `pdflatex` 加 IEEEtran，中文用 XeTeX。**本机没有 `xelatex` 命令，也没有 `ctex`/`xeCJK`/`luatexja`/`CJK` 任一中文宏包，LuaLaTeX 又缺 `luaotfload`**，因此中文路径由 `xetex -fmt=xelatex` 驱动：`build.sh` 首次运行会用 `xetex -ini -etex` 生成 `xelatex.fmt` 并缓存到 `.build/`（已忽略，不入版本控制）。中文断行由 `\XeTeXlinebreaklocale "zh"` 提供，字体为 Noto Serif CJK SC。

在具备 `texlive-lang-chinese` 与 `xelatex` 的机器上，`zh/main.tex` 也可改用 `ctexart` 编译；当前写法不依赖该宏包，代价是拉丁文与数字沿用 CJK 字体的拉丁字形，等宽实体用 Latin Modern Mono。

## 表格由结果文件生成

两份稿件的五个表体不写在 `main.tex` 里，而是 `\input{../generated/table_<表>.<语言>.tex}`。
生成物由 `python3 scripts/make_tables.py` 从结果文件产出，两份稿共用同一批数字，中英各行标签分开：
同一张表只有一处数字，语言差异只落在行名上。

| 表 | 生成物 | 数据来源 |
|---|---|---|
| 资源墙 | `table_walls.{en,zh}.tex` | `results/r30c_walls.json` |
| 记录到期 | `table_expiry.{en,zh}.tex` | `results/r41_expiry_equiv.json` |
| 配置终止 | `table_lease.{en,zh}.tex` | `results/c5_matrix.json`（修正后的当前证据；`r48_ttl_vs_lease.json` 的候选界行用修正前账本，其"交付不减"读数已随 C5 修正撤回，该文件仍登记为历史证据） |
| 任务表归因 | `table_attribution.{en,zh}.tex` | `results/r40_local_attribution.json` |
| 执行位置 | `table_placement.{en,zh}.tex` | `results/agent_traces/r39_table.json` |

正文与表说明里的 C5 数字同样不手抄：它们写成 `\cFive...` 宏，取值由同一脚本写入
`paper/generated/facts.tex`（来源仍是 `results/c5_matrix.json`）。两份稿件在导言区
`\input{../generated/facts.tex}`。`audit_tables.py` 断言宏取值与结果文件一致、两份稿件都引入它，
并禁止几条已撤回的表述回流。

规则：**生成物不手改。** 结果文件变动时在**同一次提交**里重新生成；`code/experiments/audit_tables.py`
检查生成物与结果文件一致、且稿件里没有手写的表格行。数值按十进制四舍五入（`ROUND_HALF_UP`），
按二进制格式化会让 `0.3695` 输出 `0.369` 而人写 `0.370`，同一份数据出现两种写法。

## 与 `main.tex` 的编号差异

`main.tex` 只给配置释放界编了号（`\eqref{eq:trelcfg}`），四条约束在 `align` 内未单独编号。本初稿把配置释放界编为式 (1)，目标函数为式 (2)，四条约束为式 (3)--(6)，并在中文稿中直接以 (C1)--(C4) 引用；交付链在中文稿中单独编为式 (1)。引用时按各自文件内的编号。

## 自检读数

两份文档的构建读数由 `build.sh` 末尾打印：页数、Overfull 数、缺字数、未定义引用数。当前两份均为 Overfull 0、缺字 0、未定义引用 0，参考文献各 22 条。

## 状态

论文正文的证据边界修订仍按 `docs/s7-method/v1.2/51-independent-review-paper-v06-2026-09-19.md` 与 `docs/s8-report/review-v0.6/experiment_todo.md` 推进；本初稿只做语言压缩与两分编排，未落实 doc51 的全部修订。
