# Evaluation

本目录拥有跨层评测协议，不拥有 Task 现实性、compiler semantics 或 policy 本身。

- `AGENTIC-ATTRIBUTION-PROTOCOL.v1.json`：runtime/model/evaluator attribution 与 gold replacement。
- `COMPONENT-ABLATION-v1.md`：Layer 2 因果消融。
- `WIRELESSOPSAGENT-STYLE-BASELINE-v1.md`：same-interface strong baseline contract。
- `generated/`：由正式结果生成的摘要，不手工维护数字。

Communication outcome 是 primary；Agent/runtime metrics 用于 failure attribution。Conformance、semantic correctness、system cost、physical outcome 分层报告。
