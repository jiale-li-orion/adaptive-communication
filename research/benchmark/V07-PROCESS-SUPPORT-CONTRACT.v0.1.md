# Layer-1 v0.7 Process-Support Contract v0.1

状态：**PRE-GENERATOR FROZEN CONTRACT**  
父 lineage：v0.6 official r4（generation reproducibility PASS / V3 validity FAIL）  
输入 authority：`cache06.md §3/§7`、`ENVIRONMENT-GENERATION-CONTRACT.v0.1.md`、`GENERATION-AXES.v0.2.json`

## 1. 为什么必须另开 v0.7

v0.6 不是因为某个 proposed method 失败而重做。全量 validity audit 证明其 process-support 定义自身与 family 名称/`cache06` contract 不一致：`SINGLE_RECOVERY` 与 `REINTERRUPTIBLE` 都允许 `ALL_DOWN`，即一个在整个 episode 内**从未恢复**的世界。

同时 v0.6 的 `TIGHT=max_w(min backup demand)` 是为了保证 support 内每个世界单独物理可解。`ALL_DOWN` 因而把 TIGHT 推到 obligation count；公开 satellite geometry 又能单独完成全部 obligation，最终构造出全局 blind satellite-only shortcut。

因此修复对象是 **process semantics**，不是 budget 数字。v0.6 r4 保持冻结，作为 negative construction lineage。

## 2. v0.7 唯一允许变化的科学轴

### `STEADY_AVAILABLE_CONTROL`

唯一世界：全 stage `UP`。它是 easy/conformance control，不拥有 dynamic-hardness claim。

### `SINGLE_RECOVERY`

一个合法 world 必须：

1. 至少出现一次 `DOWN`；
2. `DOWN` 只形成一个 contiguous run；
3. 该 run 后面至少存在一个 `UP` stage。

因此 `ALL_DOWN`、纯 `ALL_UP`、以及 episode 结束前从未恢复的 trailing outage 都不属于该 candidate family。

### `REINTERRUPTIBLE`

一个合法 world 必须：

1. 有一个或两个 `DOWN` runs；
2. 至少发生一次 `DOWN → UP` recovery；
3. 当 stage count 允许时，support 集中必须存在 recovery 后再次进入 `DOWN` 的 worlds。

这描述“可以恢复、再次中断”的**支持集**，不声明现场概率。

### `FULL_BINARY_SUPPORT`

继续枚举所有 binary stage sequences，包括 `ALL_DOWN`。但它明确是 `DIAGNOSTIC_CONTROL`，用来检查 worst-case provisioning / robust-support collapse，不承担主 hard-family claim。

## 3. 明确不改的东西

v0.7 不因 v0.6 shortcut 结果调整：

- DB44 source cadence / deadline；
- 两流、4–6 obligation composition；
- public Connecta geometry、mask、slice 与 dedupe；
- terrestrial opportunity phase；
- terrestrial capacity `{1,2}`；
- receipt / final-ACK timing profiles；
- remote query delay ratios；
- receipt-summary payload；
- normal send-as-probe / passive ACK；
- satellite window capacity；
- `TIGHT / BALANCED / SLACK_CONTROL` budget derivation。

特别是 **TIGHT 仍然是 support 内 max per-world minimum backup demand**。如果新的 support 仍被 blind/open-loop 解掉，继续按 validity gate 降级；不允许把 budget 改到“刚好让它难”。

## 4. Admission discipline

v0.7 generator 只负责 materialize `GENERATION-AXES.v0.2.json`。生成后按固定顺序：

```text
physical feasibility
→ blind/open-loop shortcut
→ full-current / exact / no-paid-query
→ dynamic sufficiency / send-probe competition
→ mechanism intervention
→ ordinary baseline ladder
→ structural split
```

`STEADY_AVAILABLE_CONTROL` 与 `FULL_BINARY_SUPPORT` 即使全被 shortcut 解掉也保留，作为控制面；candidate hardness 只允许从 `SINGLE_RECOVERY` / `REINTERRUPTIBLE` 中自然出现。
