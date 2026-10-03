# Code Ownership

`code/` 按当前研究对象组织；早期通信方法已从 current runtime 中物理分离。

```text
code/
├── agentic_communication/      Layer 2 canonical runtime/compiler package
├── substrate/                  shared communication system used by every policy
│   ├── instance/               node/cache/obligation/scoring/full instance state
│   ├── monitoring/             Class-A opportunity, interfaces, supply/fault models
│   ├── physics/                terrain/ITM/LoRa/energy physical models
│   ├── runtime/                shared deterministic + durable execution primitives
│   ├── joint/                  current full-sim composition: primary/backup/task change
│   ├── reference/              deterministic physical reference wiring
│   ├── calibration/            source-to-parameter/data derivation scripts
│   └── tests/                  substrate invariants and fairness checks
├── evaluation/
│   ├── agentic/                A1–A11 runners, tests, ablations and model evaluations
│   └── audits/                 claim/repository/table audits
└── legacy-communication/       superseded/killed communication-method experiments
    ├── v2gate/ v2probe/ v3joint/
    ├── experiments/ analysis/ protocols/
    └── runtime/                early ReAct/disruption environment
```

`legacy-communication/` 保留历史复现，不定义当前方法。里面少量 symlink 只把历史 runner 接回 shared substrate，避免复制两套物理实现。

当前层级对应关系：
- Layer 1 benchmark 的构造与 validity authority：`research/benchmark/`；
- Layer 2 compiler：`code/agentic_communication/` + `research/compiler/`；
- Layer 3 policy：compiler 暴露的合法 decision surface 上运行，当前 runner 位于 `evaluation/agentic/`；
- 共享通信系统：`code/substrate/` + `research/substrate/`。

统一检查入口：`python3 code/run_checks.py --group substrate|compiler-eval|claims|paper|legacy|all`。
