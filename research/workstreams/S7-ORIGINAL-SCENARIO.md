# Workstream A — S7 Original Scenario

## Question

原始灾前山区监测需求中，是否存在天然的 persistent communication commitment，使当前合法动作会改变未来 operational obligations 的可完成集合？

主 task surface：`T1.S7_COMPOUND_CONTINUITY`。

正式 task 选择与否决规则由 [`../benchmark/T1-FUTURE-CHOICE-TASK-SCAN.md`](../benchmark/T1-FUTURE-CHOICE-TASK-SCAN.md) 持有。

## Why this line exists

单独 `S2_INTERMITTENT_BACKHAUL_FALLBACK` 已被 corrected gateway pilot 证明容易退化为 blind-easy、causal-infeasible 或 ordinary myopic-flow solved。继续堆 backhaul process 不再是主线。

S7 已经有现成的真实耦合对象：

- external warning / task revision；
- persistent sampling/report configuration；
- node battery / harvest；
- intermittent access / backhaul / control opportunities；
- gateway store-and-forward / backup；
- long-horizon monitoring obligations。

## Existing executable evidence

历史 `instance_adm_out3` 已经出现 persistent-config failure：在合法、准确的 SoC evidence 下，短视 energy-aware policy 先把节点改成 dense configuration；随后 access/control continuation 消失，配置无法及时撤销，产生后续 missing collection。

10-seed aggregate 中：

- `local`：10/10 seeds 的 routine missing collection = 0；
- `ea_nb`：10/10 seeds 出现 missing collection，范围 4–18；
- `ea_nb_rob3`：逐 seed 与 `ea_nb` 相同，说明“3h 后仍可纠错”的有限纠错假设没有解决问题；
- horizon-safe `ea_nb_cand`：10/10 seeds missing collection = 0。

这个历史结果目前只作为 **mechanism witness**，因为 `ea_nb` 的 dense target 是策略自选，不是 operational authority 下发。

## Current conversion target

把相同机制迁入现有 S7，而不发明新 task/action：

```text
warning authority announces denser monitoring requirement
→ policy decides when to commit/install the persistent profile
→ control/access path may later disappear
→ battery continues to pay for the installed configuration
→ later warning obligations depend on whether a correction continuation still exists
```

当前 O6 weather smoke 的第一条结果是负的：在 2023 四个预注册 NASA POWER 窗口、seed 0、medium-energy O6 下，一小时 early preparation 都比 no-prepare 多 103 条 timely delivery，且没有节点死亡；现有 resource guard 过度保守。因此该 regime **不是** future-choice hard witness。

随后保持 task/action 不变，只扫描仓库里已有的 battery-capacity regime。`0.03 Wh` 开始出现真正的跨阶段 trade-off。固定预声明坐标 `2023-w2 / seed0 / capacity=0.03 Wh`：

- warning profile 在 h5 生效；future-effective revision 已合法到达，early preparation 在 h4 下发；
- early preparation 相对 no-prepare 增加 **101** 条 warning-stage timely obligations；
- 同一动作导致 `n00/n01/n03/n04/n07/n15` 在约 h9.6–h9.75 失活；
- 这 6 个节点在 post-warning 阶段各丢 2 条原本 no-prepare 可以 collection+delivery 的 routine obligations，共 **12** 条；
- 将 battery capacity 放宽到仓库已有 `0.05 Wh` regime 后，post-warning loss 从 12 变为 **0**、死亡从 6 变为 **0**；
- 单独移除 access outage **没有**消除这 12 条 loss。因此这个 bounded witness 当前支持的是 **persistent energy commitment**，不能把“后续控制机会消失”写成必要机制。

强普通规则已经加入第一轮 red-team：

| Rule | warning delivered | post-warning delivered | dead nodes |
|---|---:|---:|---:|
| comply / energy-gate / dayfeed | 268 | 16 | 6 |
| sustain | 188 | 28 | 0 |
| resource-guard | 194 | 28 | 0 |

因此当前不是“一个阈值就修好”的结构。普通规则在 warning 收益与 post-warning continuity 之间形成明显 trade-off；下一步才有资格测试 selective future-choice frontier 是否能拿到更好的 Pareto point。

## Hard gate

只有出现下列结构才升级为 paper task：

1. 同一个 operationally-authorized persistent action 在不同 lawful state/history 下有正负翻转；
2. harmful branch 的 first irreversible loss 是未来 continuation 消失，而不是 evidence 错误或非法动作；
3. strong ordinary EnergyAware / MPC / finite-horizon / placement-aware baseline 不能稳定概括；
4. future-choice certificate / frontier 能解释并避免 loss；
5. 结果来自既有 source/substrate coordinates，而不是事后新增 quota/cache pressure。

## Next

当前已经完成 `out3 → S7 authority-driven commitment` 的第一阶段映射。下一步：

1. 在 h4 合法历史上判断死亡组是否可由当前 evidence 简单区分；当前 SoC 已确认**不能**分开死亡/存活节点；
2. 把 current belief 下的 future resource domain 接到 Layer-2 conditional frontier，而不是再调一个 energy threshold；
3. 对 selective future-choice policy 做 EnergyAware / sustain / resource-guard / bounded MPC red-team；
4. 扩到预注册 weather/year/seed 后才讨论 benchmark-wide hardness。
