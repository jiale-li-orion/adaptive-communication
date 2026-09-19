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

## 与 `main.tex` 的编号差异

`main.tex` 只给配置释放界编了号（`\eqref{eq:trelcfg}`），四条约束在 `align` 内未单独编号。本初稿把配置释放界编为式 (1)，目标函数为式 (2)，四条约束为式 (3)--(6)，并在中文稿中直接以 (C1)--(C4) 引用；交付链在中文稿中单独编为式 (1)。引用时按各自文件内的编号。

## 自检读数

两份文档的构建读数由 `build.sh` 末尾打印：页数、Overfull 数、缺字数、未定义引用数。当前两份均为 Overfull 0、缺字 0、未定义引用 0，参考文献各 22 条。

## 状态

论文正文的证据边界修订仍按 `docs/s7-method/v1.2/51-independent-review-paper-v06-2026-09-19.md` 与 `docs/s8-report/review-v0.6/experiment_todo.md` 推进；本初稿只做语言压缩与两分编排，未落实 doc51 的全部修订。
