# 论文仓库启动模板

这是从 `adaptive-communication` 沉淀出的骨架，用于新建论文仓库。规范全文见仓库根的
`PAPER-REPO-STANDARD.md`（中文版 `PAPER-REPO-STANDARD.zh.md`）。

## 用法

在 `adaptive-communication` 里运行：

```bash
./scripts/new_paper_repo.sh ../my-next-paper
```

脚本会：复制本模板 → 从当前仓库取三个机制文件（`artifact/compare_result.py`、
`code/experiments/audit_claims.py`、`code/experiments/audit_tables.py`）→ 跑一次示例实验 →
初始化 git → 执行 `make check` 验证接线。检查通过即表示骨架可用。

手工方式：把本目录内容拷到新仓库，再从 `adaptive-communication` 取上述三个机制文件。

## 起手就跑通的窄路径

模板带一条完整的最小链路，用来证明接线有效，而不是留一堆空文件：

```text
code/experiments/example_metric.py   产出 results/example_metric.json
        ↓（scripts/make_tables.py）
paper/generated/table_example.<语言>.tex
        ↓（审稿表只经 \input 引入）
results/CLAIMS.md 的 C1 行指向上面两者
        ↓（code/experiments/audit_claims.py、audit_tables.py）
make check
```

跑通之后把示例替换成真实实验，并保持同样的四段接线。

## 需要你改的地方

| 文件 | 改什么 |
|---|---|
| `results/CLAIMS.md` | 换成论文真实主张；示例行删除 |
| `results/README.md` | 登记真实结果文件的脚本、命令、口径、分母 |
| `artifact/AE.md` | 尖括号 `<...>` 处填环境、获取步骤、逐主张期望判定 |
| `scripts/make_tables.py` | 换成真实表格定义与数据来源 |
| `scripts/get_data.sh` | 换成真实需获取依赖的获取命令 |
| `spec/` | 放规范性声明（部署条件、评测契约、数据集来源） |
| `code/experiments/` | 放实验脚本；文件名以 `audit_` 或 `test_` 开头即被入口自动收集 |

## 四条不可违例

克隆可验证、数字单一来源、主张单一状态、历史不可变。每条都有对应检查：`make check` 里的
`audit_claims.py` 与 `audit_tables.py`，以及 `make data` 缺失时打印获取命令的行为。
