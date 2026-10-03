# Layer 2 — Decision-Semantic Compiler

本层拥有 Task + Evidence + Capability + Execution 的程序语义，以及它们到 live decision surface 的编译。

Canonical contracts 见 `RUNTIME-DOMAIN-OWNERSHIP-v1.md`；方法关系见 `PLAN-EVIDENCE-EXECUTION-v1.md`；capability/task registry 见 `COMMUNICATION-DOMAIN-REGISTRY.v0.1.json`；prior-art/claim ceiling 见 `NOVELTY-BOUNDARY-v1.md`。

当前稳定对象包括 audit/control/model/persistent-execution surfaces、plan–evidence dependency、dependency liveness、Decision Sufficiency、EvidenceNeed、semantic plan selection、persistent execution intent 与 semantic-state replanning。ordinary dependency construction 能解释当前正式 workload 时，不为了算法复杂度追加 solver。
