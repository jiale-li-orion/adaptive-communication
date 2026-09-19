# spec/ —— 规范性文件

本目录存放**评审人需要的规范性内容**：论文所依据、且必须与代码保持一致的声明。

## 规范性来源地图

同一件事只允许有一个规范来源。填写下表，避免长出第二个副本。

| 内容 | 规范来源 | 由什么保证一致 |
|---|---|---|
| 部署条件（站点几何、拓扑、时间、能量、链路、存储） | `<待填>` | `<待填：哪个检查比对哪份文件与哪段代码>` |
| 结果文件的脚本、命令、口径与分母 | `results/README.md` | `code/experiments/audit_registry.py` 或登记册检查 |
| 被测主张及其状态 | `results/CLAIMS.md` | `code/experiments/audit_claims.py` |
| 论文表格的数字 | `paper/generated/`（由 `scripts/make_tables.py` 生成） | `code/experiments/audit_tables.py` |
| 评审入口与环境声明 | `artifact/AE.md` | `artifact/reproduce_all.sh` 的判定与文档写明的期望值比对 |
| 需获取数据集 | `scripts/get_data.sh` 与 `spec/datasets.md` | `make data` 的核对输出 |

## 两条规则

**数值按数值比，不按字符串比。** 同一件事有 `4.7e-4` 与 `0.00047` 两种合理写法，按字符串比较会把
它们判成不一致，产生噪声；被噪声化的核对很快会被无视，比没有核对更糟。

**代码为准。** 本目录的数值是从代码读出的当前真值。改代码就改这里；两边不一致时以代码为准，
并让检查变红，直到两者重新一致。
