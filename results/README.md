# Results Ownership

`results/` 持有可提交、可引用、可重建的机器证据。`results/CLAIMS.md` 持有 claim state；模块 README 只解释证据归属与用途。

## Current result planes

| Path | Owner / purpose |
|---|---|
| `benchmark/` | **Layer 1**：exact labels、validity/hardness、failure atlas、historical split/freeze、release audit；当前 benchmark coverage 已重开，旧 freeze 只作 regression/provenance |
| `agentic/` | **Layer 2 / Layer 3**：compiler/runtime、future-choice/L-U、incremental frontier、policy/search evaluation，以及历史 A7–A11 Agentic evidence |
| `communication-substrate/` | shared substrate：C* claims、calibration、physics outputs |
| `reference/` | frozen comparator / reproduction reference plane |
| `history/` | withdrawn、superseded、historical registries |
| `legacy-communication/` | 历史 communication method runs 与旧 instance/probe evidence |

当前数字进入 README / paper / figure 的路径固定为：

```text
machine result
    -> generator / audit
    -> generated compact artifact
    -> README / paper / figure projection
```

README 与 manuscript 不单独维护实验数字。

## Agentic result index

[`agentic/README.md`](agentic/README.md) 按 research role 管理长期稳定的实验路径。目录路径保持稳定，研究地位由 index / claim ledger 更新：

- current Layer-2 v2 artifacts：`layer2-v2-*`；
- current Layer-1→Layer-2 bridge audits：`layer1-v02-*`；
- Layer-3 artifacts：统一使用 `layer3-*` 前缀；
- A7–A11 与 O1–O6-era experiments：作为 formal historical baseline、supporting evidence 或 development diagnosis 保留。

大型 raw trace 默认留在本地 research storage；远端优先提交 aggregate / audit / summary / manifest 与论文所需 compact payload。

## History and provenance

`history/withdrawn/` 保存明确撤回或被修正的结果；`history/registries/` 保存早期布局下的 registry。`legacy-communication/` 保存旧通信方法证据。三者均承担 provenance，当前 claim 只有在 `CLAIMS.md` 登记后成立。
