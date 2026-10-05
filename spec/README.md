# Specifications

`spec/` 只保存可作为实现/复现实例输入的规范，不再混放研究路线。

- `substrate/`：当前共享通信 deployment 与 dataset contract。
- `benchmark/`：已 research-freeze 的 Layer-1 Decision Benchmark 规范；规范可以处于 release-pending，但必须与 research authority 的当前版本一致。
- `history/legacy-communication/`：早期 C5/C9/retention 等已结束通信方法的预注册规范，仅用于复现历史结果。

Layer-1 v0.2 已通过研究冻结所需的 source-grounding、causal oracle、hardness 与 held-out construction，因此 normative contract 已进入 [`benchmark/LAYER1-DECISION-BENCHMARK-v0.2.md`](benchmark/LAYER1-DECISION-BENCHMARK-v0.2.md)。它当前仍是 **research-frozen / public-release-pending**：正式 `BENCHMARK_ADMIT` 由 `research/benchmark/BENCHMARK-QUALITY-GATE.v0.1.md` 的 Q0–Q12 与 v0.2 Q11 human/source audit 决定。O1–O6 仍是历史 T1 regime / conformance assets，不能冒充独立 Family。
