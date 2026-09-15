# v1.2/20：独立审查后的有限实验矩阵

承接 [doc19](19-independent-paper-review-2026-09-15.md)。机器可读版本：[JSON](20-review-experiment-matrix-2026-09-15.json)。这里沿用仓库既有 docs 布局，作为本轮 review 的实验主矩阵与待办，不另开重复的 paper 工作树。

**当前只完成 R00。R01/R02 恢复可信测量和模型解释，R04 证明候选可辨识；R03 仅在保留反馈因果主张时需要。R05/R06 均未启动，只有上一步满足晋级条件才做下一步。**

| ID | 类型与状态 | 回答的问题 | 最小交付 / 晋级条件 |
|---|---|---|---|
| R00 | existing_result_audit；analyzed | 已有主张能否由当前代码和结果支持？ | 给出可复现反例；不改变策略轨迹 |
| R01 | measurement_repair；pending | 重复到达与旧遥测能否污染评分和状态？ | 本轮反例消失；分别记录纯评分变化与行为变化；受影响旧产物不再直接引用 |
| R02 | model_validity；pending | 永久死亡及紧任务缺口是否来自已证实器件语义？ | 来源/研究假设分清；采集、接入、回传损失分列；不把未采集记成无线拥塞 |
| R03 | causal_attribution；pending_if_feedback_claim_retained | 差额来自 AoI、电量陈旧，还是无法纠正配置？ | 每个对照只改一项；跨位置理想信息须标诊断而非可实现算法；不能用旧配置持续效果冒充新命令生效 |
| R04 | mechanism_identifiability；partly_analyzed_existing_candidate_fails | 真实未完成义务和机会信息能否改变合法动作？ | 候选触发依赖所称变量且动作可生效；不得以提高阈值代替修正义务对象 |
| R05 | bounded_headroom_probe；not_started | 相同服务成本约束下是否存在比静态/普通规则更好的可执行动作序列？ | 现有一个合法工作点发现非同义/非评分修复的差额；未来信息搜索只作见证 |
| R06 | fair_method_comparison；not_started | 合法观测下的联合执行规划是否优于普通延迟感知 MPC 与规则？ | 相同信息/能力/预算，冻结后留出种子验证；耦合消融有差额 |
| R07 | agent_transfer；deferred | 已有执行机制是否改善真实 agent 工具工作流？ | 真实工具过程、同任务与能力；不能仅把 agent 写入讨论 |
| W01 | manuscript_revision；status_banner_done_body_pending | 稿件是否区分事实、假说与未测边界？ | doc19 替换表落实；先决定可支持的科学主张再排 bib/venue |

候选亮点是待证假说：H1 是动作归因可辨识，H2 是考虑真实执行过程后仍存在的联合收益。没有已接受的方法主张。

当前排除：扩大原相图、为同一结论增加种子、重画投稿图、选 venue、用时变风险义务造增益、引入新端侧 lease/健康旁路、重做 LLM 打分。排除理由是这些动作都不能修复 R01–R04，或者超出现有候选范围。

R01 的旧产物影响清单至少包括 v3joint 评分/图表及使用 Transit.first_* 的分跳分析；逐文件记录影响，不凭本轮一个反例宣布全部历史数值错误。R02 不默认现实设备一定自动复机，也不默认永久死亡正确，两者需有来源或明确研究假设。

R06 必须计入计算开销、命令与备用开销，并完成组件归因和冻结后的独立验证；若尚不可行，保持 not_started，不将本矩阵计为实验已完成。
