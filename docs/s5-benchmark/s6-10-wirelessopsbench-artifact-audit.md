# WirelessOpsBench 公开 artifact 逐字审计

对象为本地 `other_repo/wirelessopsbench-artifact-D969/` 下的 `WirelessOpsBench-public-development-1d6004f4f809a5d4.zip`。核验方式为解包后逐记录读取，无外部转述。

## 一、来源与完整性

| 项 | 值 |
|---|---|
| 压缩包 SHA-256 | `df832540beae8cdfe776ea0ffbe294be1355421c1279e69479e0b0655428940d` |
| README 声明 SHA-256 | 同上，核验通过 |
| 许可 | MIT |
| 论文 | WirelessOpsAgent: A Benchmark and Agent Design for Action Assurance in Wireless Networks，arXiv `2608.08277`，CC BY 4.0 |
| 作者 | Zijian Lu, Yiping Zuo, Hao Xu, Weicong Chen, Xin He, Jiajia Guo, Shi Jin |
| CITATION.cff | `Anonymous Authors`，`the accompanying anonymous paper`，version `1d6004f4f809a5d4` |
| 上游 | WirelessBench，revision `47cc6e50b3e69dcda4bf2ee8b06b705a0a7b1ec4`，六份 jsonl 共 3,392 行 |
| 发布日 | 2026-08-01 |

CITATION.cff 匿名意味着该论文处于评审中，正式引用须待其公开。

## 二、记录构成

公开包只有数据，无 runner、无 scoring 谓词、无 fault schedule。

| 目录 | 数量 | 体积 | 内容 |
|---|---:|---:|---|
| `development/bases/` | 300 | 2.4 MB | 任务契约、工具 schema、预算、状态机 |
| `development/cases/` | 2400 | 20 MB | 参与者可见的 case |
| `development/repairs/` | 180 | 2.4 MB | 损坏的公开前缀与 task context |
| `public-manifest.json` | 1 | 822 KB | 2,880 条 `kind` / `path` / `record_id` / `sha256` 索引 |

三族各 100 base。每 base 八个 case：一个 clean 加七个故障孪生。repairs 中 105 条含 12 个事件、75 条含 8 个，事件类型为 `tool`（1,140）与 `action`（720），全部 1,860 个 `result.status` 均为 `ok`，`corrupt_prefix` 内部无故障痕迹。

论文所述完整冻结集为 900 base、900 clean、6,300 故障孪生、540 归因与修复记录，final 分片不在包内。

## 三、公开包不可执行，这是本节的关键结论

四条独立证据：

1. **同一 base 的八个 case，`public_task` 逐字节相同**，只有 `case_id` 不同。故障不由数据承载。
2. **`public_input` 只含任务参数**。WCNS 为 `embb_users` / `urllc_users` / `region` / `service_request` / `user_x` / `user_y`；WCMSA 为 `current_position` / `trajectory` / `latency_requirement` / `min_rate`；WCHW 为空对象 `{}`。不存在证据账本内容。
3. **无任何答案、gold、reference 或 label 字段**。全库检索只命中的是动作 schema 里的 `expected_version`。
4. **`ray_tracing` 不在 `tool_schemas` 里**。200 份 WCNS 与 WCMSA 的题面要求 *"You MUST call the ray_tracing tool"*，但声明的 9 个工具不含它。题面与工具契约不自洽。

READY 证据与评测谓词被评测端扣留，DATASET_CARD 与 EVALUATION 的表述一致：*"Evaluator-private initial states, schedules, labels, reference interventions, and scoring predicates are excluded"*，且服务器 *"not yet online"*。

因此可直接取用的是任务契约层，不是可运行的 episode。评测接口也不在包内。

## 四、可继承的接口

工具面九项，其中真正变更状态的只有两项。

| 工具 | `mutates_state` | 角色 |
|---|---|---|
| `get_primary_evidence` | False | 读证据 |
| `get_secondary_evidence` | False | 读证据 |
| `get_entity` | False | 读实体 |
| `get_schema` | False | 读模式 |
| `post_check` | False | 后置验证 |
| `stage_policy` | False | 暂存提案 |
| `validate_policy` | False | 校验 |
| `commit_policy` | **True** | 提交授权 |
| `rollback_policy` | **True** | 回滚 |

状态机三族同构，仅前缀不同：`stage_<fam>` → `validate_evidence` → `commit_authorization` → `post_check` → `rollback`，另加一条 `refresh_then_validate:<entity_id>` 指名某实体的刷新路径。里程碑为 `evidence_checked` → `policy_committed` → `post_checked`。预算为 `max_model_calls` 24、`max_steps` 24、`max_tokens` 32000、`max_tool_calls` 12、`wall_time_ms` 60000。

`commit_policy` 要求 `stage_id` 与 `expected_version`，即乐观并发。`stage_policy` 带风险带：`risk_field` 为 `protected_*_impact`，`maximum_protected_impact` 为 28 或 40 等，超过该值即为 `dangerous_proposal`。

## 五、七类故障条件

DATASET_CARD 与 README 一致列出七条：

1. Temporal inconsistency，含 stale 与 out-of-order 观测
2. Missing required evidence
3. Conflicting sources
4. Schema drift
5. Entity misbinding
6. Concurrent version drift
7. False-success updates

七条全部刻画证据账本的可信度，判据是"这条记录可不可信"。无一条描述动作分发之后的传输语义。

## 六、采用边界

可继承：任务文本与参数、九工具契约与 `mutates_state` 标记、预算、合法迁移与里程碑、动作 schema 的乐观并发与风险带、七类故障作为对照故障轴。

须自建：证据账本内容、`ray_tracing` CQI 提供者、runtime、scoring 谓词。公开包不含这四项，这一层即本项目所补的执行层。

不可声称：与论文所报数值可比。artifact 不含 baseline 分数、轨迹、token 数、成本与延迟，DATASET_CARD 的 Limitations 明列于此。要复现需同时重写其 agent 与其 fault injector，两者均不公开。

本文在其任务契约上补的是 **Execution assurance**：判据是动作分发之后到底发生了几次、有没有发生。相邻关系为 WirelessOpsBench 的 Task correctness → Action assurance，本文接 Execution assurance。

两组判据不可互相表达。其 false-success update 是上报成功而状态未生效，本文的 ACK 丢失是状态已生效而回执未达，重试即产生重复副作用，方向相反。其 concurrent version drift 由数据面并发写者造成，本文的视图落后由控制面链路中断造成。派发后节点失联、pending 被遗忘、重放顺序错、网关抖动、分区分歧、协调者重启六类在其故障表中没有对应项，因为其 episode 把工具调用视为必然送达。

接入点在两个 `mutates_state=True` 的工具外侧的 dispatch → execute → observe 环上。
