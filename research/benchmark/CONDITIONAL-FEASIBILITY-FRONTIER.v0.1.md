# Conditional Feasibility Frontier v0.1

状态：method-development prototype

目标不是缓存“当前答案”，而是维护：

- 哪些后续方案仍可行；
- 这些方案依赖哪些资源与证据；
- 这些依赖在哪个资源区间内仍有效；
- 哪类事件会让证书失效；
- 失效后只重算受影响部分。

当前实现：

1. 对 terrestrial delivery 子问题构造 obligation-slot flow；
2. 通过 residual min-cut / Hall deficiency 产生集合级冲突见证，而非逐报告 mandatory 标记；
3. 每个证书保存 world support、minimum backup requirement、resource validity domain、evidence/execution dependencies；
4. query observation 只缩小相容世界并重建受影响证书；
5. satellite budget 只在跨越证书有效边界时触发失效；
6. 无法安全判定的边界仍交 exact non-anticipative solver。

当前 v0.1 只覆盖单位报告、单位 terrestrial opportunity、normalized satellite budget。它不是最终 v0.5 process，也不声称一般复杂度改进。

下一步验证重点来自 cache06/Astra：

- incremental frontier 与 full rebuild 在每个合法前缀一致；
- 证书失效规则不会删除仍可行策略；
- 计算工作随受影响 conflict width，而不是每次随全历史重来；
- 低耦合场景允许普通 planner 更划算；
- 只有在动态重叠 conflict / event interleaving 下才应出现结构收益。
