# Statistical Reporting v0.1

状态：Layer 1 frozen reporting protocol

统计单元是 frozen case id。任何 policy/model 比较在同一 split 上使用 paired case alignment，禁止把不同 case 子集的均值直接比较。

确定性 policy 对每个 case 执行一次；存在 sampling、随机探索、随机网络退避或非确定推理时，每个 case 使用固定公布的 seed set 重复运行，默认 10 个 seeds。若模型服务本身无法保证 seed，可重复 10 次并明确标记 provider-side nondeterminism。

主结果报告 success / infeasible-abstain correctness / invalid-run count，并分别报告真实无线请求、被动 observation、模型/上下文 token、planner wall-clock、memo/expanded nodes、fallback resource 使用。不同资源不压成单一 cost。

所有比例和均值报告 95% bootstrap interval；bootstrap 以 case 为重采样单元，stochastic policy 先在 case 内聚合 seed，再在 case 间 bootstrap。成对 policy 差值使用 paired bootstrap。多模型或多指标同时检验时使用 Holm correction，并同时给原始 effect size。

结果按 split、candidate role、hardness、service process、evidence regime、overlap、resource headroom、recovery regime 分层。hard test 另外按 held-out trace cluster 报告。

API/provider/tool failure 单独记 `INVALID_RUN`，不偷偷重试到成功后删除失败记录。允许按预先声明的重试策略恢复 transient transport error，但原始失败次数必须保留。evaluator rejection 计 task failure，不归为 infrastructure invalid run。

任何 benchmark-specific prompt tuning、private-test repeated selection、模型版本漂移、provider 参数变化必须进入报告。公开榜单绑定 benchmark version、model/provider version 与评测日期。
