# Tracked Historical Executable Bundles

`archive/` 保存已经进入 Git、仍需按原路径复现的历史可执行研究 bundle。这里承担 **tracked provenance**，不承担当前 research authority。

当前内容：

- `legacy-communication/multipath-probe/`：2026-09-14 多路径 × 隐状态回传 go/no-go probe。其 README 保留原始 preregistration、结果解释与当时路径语义。

写入规则：

1. 当前实现进入 `code/` 对应 owner；
2. 当前机器结果进入 `results/`；
3. 当前研究语义进入 `research/` / `spec/`；
4. `archive/` 只接收需要长期保持原目录结构的 tracked historical executable bundle。

Git 提供文件级演化历史；`research/history/` 保存被替代的研究 authority；`results/history/` 保存被替代的机器结果。三类历史按对象分开。
