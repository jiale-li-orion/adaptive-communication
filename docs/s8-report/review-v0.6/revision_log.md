# v0.6 修订表（审查对象 3df2845）

本轮只审查与保存证据，未修改论文、实验实现和原结果。完整论证见 [doc51](../../s7-method/v1.2/51-independent-review-paper-v06-2026-09-19.md)。以下所有待修项均未标完成。

| ID | 问题及影响 | 类型 | 最小处理 | 阻塞投稿 |
|---|---|---|---|---|
| R1 | 99 decisions 被称为 99 API calls；52 次解析回退被遗漏；重试 token 漏账 | 已有数据分析/实现计量 | 公开逐臂 parsing/retry 表；新运行逐请求记账；保留旧轨迹为混合运行 | 是 |
| R2 | false-report 混淆要求/计划/生效；正常组根本不评分；89 为宽泛关键词命中 | 已有数据重标 | 审全部 43 条阳性与 A1 note，再定分母、类型和知识边界；不按发 dense 与否决定评分 | 是 |
| R3 | A1 包含专家规则/输出模板/额外常量；证书有错误确定性 | 语义修订+最小对照 | 事实/unknown/策略建议分离；给对照同一常量及普通规则说明 | 是 |
| R4 | 到达 100% 归因读全局样本与未来 heard | 实现观察边界/重评 | 按 location 和 received_at 截断；无法辨识保留 unknown；旧表降离线诊断 | 是 |
| R5 | purge 固定期限与普通 expiry 没有被区分 | 文献/语义基线 | 先证明或否定与同期限 TTL 的等价；相同则撤算法新颖性，不跑假对照 | 是 |
| R6 | 资源干预/贪心/规则比较被称全体策略上界 | 文本即可 | 删除最优前沿与控制空间关闭；保留已测负结果与干预诊断 | 是 |
| R7a | 三种子无死亡被称安全保证；r38 四死未同 Agent+L0 复验 | 文本/条件性补证 | 改为所测实例零死亡；若保留组合收益须直接测组合 | 是 |
| R7b | 中心 t0 已知未来授权，初段闭窗口；不可称统一动态未知任务/全半开 | 契约+文稿 | 明确中心预告、网关延迟；按实际窗口写法；若改语义须新结果版本 | 是 |
| R7c | send precision、refused cost、未见种子三个口径越界 | 文本/现成账本 | 采用客观按期记录率、真实传输量；撤全项目 unseen | 是 |
| R8 | 摘要 823 词、六行标题、六贡献、内部 doc/核验语言外泄 | 文稿 | 主文收为问题/方法/对照三段；摘要约 200–250 词；内部说明移 provenance | 是 |

可直接替换的英文（先固定科学口径，再整体修稿）：

- R6: “Across the tested policies and operating points, we did not observe a robust delivery gain from additional centre-side configuration optimisation. The resource interventions identify limiting factors; they do not establish global optimality.”
- R1: “The study contains 1,089 decision epochs across 11 trajectories. Fifty-two model outputs were not parseable and invoked a hold-to-reported-configuration fallback; the reported trajectory outcomes include those interventions.”
- R4: “The current retrospective attribution uses simulator-wide sample histories and serves as an offline diagnostic. Achievable attribution from gateway-local evidence remains to be evaluated.”
- R5: “Deadline-based cache expiration improves delivery relative to FIFO repair and latest-only replacement in this model. The result identifies an access–backhaul interaction; it does not yet establish an algorithmic advantage over ordinary expiration with the same deadlines.”
- R3: “Adding state-dependent expert guidance improves the outcomes of this controller relative to the tested pending-command checklist. Further controls are needed to separate certificate content from policy instructions and output-format effects.”
- R7a: “The node-local night rule eliminated observed brownouts in the three tested seeds. This empirical result is not a survival guarantee under arbitrary energy trajectories.”

不要直接改图表里的死亡/服务观察值；改的是它们支持的推论。24/19 与 89 在重新标注前仅保留为旧评分器输出，不继续称已核验的语义事实。
