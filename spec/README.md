# Specifications

`spec/` 只保存可作为实现/复现实例输入的规范，不再混放研究路线。

- `substrate/`：当前共享通信 deployment 与 dataset contract。
- `history/legacy-communication/`：早期 C5/C9/retention 等已结束通信方法的预注册规范，仅用于复现历史结果。

Operational Task / Decision Benchmark 的新规范将在通过 `research/benchmark/README.md` 的 source-grounding 与 validity gate 后进入独立 benchmark spec；当前不把 O1–O6 conformance catalog 冒充完整 Decision Benchmark。
