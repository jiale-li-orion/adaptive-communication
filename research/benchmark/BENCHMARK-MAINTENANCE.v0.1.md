# Benchmark Maintenance v0.1

状态：Layer 1 lifecycle authority

Layer 1 分开版本化 `source snapshot`、`source profile`、`schema`、`generator`、`environment/evidence process`、`oracle/evaluator`、`split` 与 `release`。release manifest 记录每个冻结文件的 SHA-256；任何影响 case identity、success predicate、oracle label 或 test split 的修改必须发布新 benchmark version。

外部 source stale 时保留原 snapshot 与引用。replacement source 先进入新 profile version，重跑 source/task validity 与 Q0–Q12，不能静默覆盖旧 leaderboard target。

若发现 evaluator flaw：先公开 flaw、受影响版本和影响范围；旧结果标记 `INVALIDATED` 或 `MIGRATION_REQUIRED`；修复后的 evaluator 使用新 version 和新 digest；需要改变 gold success set 时发布新 benchmark release，旧分数不与新分数混排。

新增 Family、task surface、capability profile 或 empirical trace 不直接并入主分数。它们先作为 candidate extension 独立跑 source audit、V0–V9、Q0–Q12、held-out split 与 baseline ladder，通过后才能进入下一 release。

Leaderboard/result 必须绑定 benchmark version、release manifest digest、model/provider version 与评测时间。release 后禁止通过修改 generator、隐藏 field、prompt 或 private variant 来追着被评模型调 difficulty。
