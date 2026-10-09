# A3 Host Incident — WSL rtnetlink blockage, 2026-10-09

状态：**HOST-BLOCKED / RESUMABLE, NO SCIENTIFIC PROTOCOL CHANGE**。

## 观察与证据

- Frozen paper split 为 30 test coordinates × 2 context modes，精确目标 60 unique row IDs。现场已解析 `results/benchmark/layer1-paper-llm-test/rows.jsonl`：**41 rows / 41 unique IDs / 41 OK**。上次完整 chunk 的 `aggregate.json` 和 `run-manifest.json` 仍记 29，属于派生摘要滞后，不能以它们代替 append-only `rows.jsonl` 判断进度。
- `scripts/run_layer1_paper_llm_safe_chunk.sh` 仍提供 2 CPU affinity、nice +10、BLAS/OMP 单线程、逐行 checkpoint、file lock；本次一次性要求最多 19 个缺失行，控制资源的其他参数未修改。
- 该进程实际处于 `D` 状态，`/proc/<pid>/wchan = rtnl_dumpit`，CPU 近乎空闲、无新增 row；同一主机的另一个常驻进程也卡于 `rtnl_dumpit`。`dmesg` 明确打印 `hv_netvsc ... eth1: sub channel open failed: -12`。2026 年已有上游 WSL issue 报告相同症状与 Hyper-V vmbus/rtnl lock 死锁：https://github.com/microsoft/WSL/issues/41622 （关联 https://github.com/microsoft/WSL/issues/41474）。这里以观测到的 kernel 状态定义 **HOST BLOCKER**；具体锁持有者仍需内核级诊断，不能推定为 DeepSeek/provider failure。
- 当前 RAM 约 7.7 GiB，Swap 约 2.0 GiB 且接近用尽。不得重复启动依赖接口枚举的进程；D-state 通常不会因 userspace SIGTERM 或 API timeout 恢复。

## 保全与恢复

1. **保全** `rows.jsonl`、`traces/`、`source-manifest.json`、`execution-only-migration.json`、`run-manifest.json`；旧 17-row migration 仍为合法 provenance，绝不重新请求已完成 41 rows。
2. 检查原续跑进程是否仍在持锁。如果仍卡于 `rtnl_dumpit`，先在宿主 Windows 层恢复 WSL 内核网络状态；这需要人工协调正在运行的其他工作，不能擅自强制重启、反复 SIGKILL 或并发新 runner。
3. WSL 恢复后，先从 `rows.jsonl` 验证 unique row IDs / frozen source digests。若前次进程已消失且 git 工作区无输出目录外的 dirty tracked 文件，运行 `bash scripts/run_layer1_paper_llm_safe_chunk.sh`，重复默认的最多 6-row chunk 直到 complete。仍在运行的旧进程由 `.runner.lock` 自动阻止并发写入。
4. 执行 `python3 code/evaluation/benchmark/analyze_layer1_paper_llm_test.py`，全部 60 rows/replay/digests通过后，执行 `python3 code/evaluation/benchmark/freeze_layer1_paper_final_release.py`。得到 `BENCHMARK_ADMIT` 前，A5 保留 blocked。

## 声称边界

本事故仅影响 A3 model-spectrum diagnostic 的执行收尾；不影响 A2 已冻结确定性 150-coordinate landscape、A4 lifecycle case studies、B1–B6 correctness、C1–C6 external transfer。不得将 WSL D-state 归入实验 `RUNTIME_FAILURE`，也不得根据 41/60 的临时分布修改冻结模型协议或论文 method claim。
