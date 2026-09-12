# 文档索引

`README.md` 是权威文档，定位、证据、实体分类与现状盘点都在那里。本目录存放支撑其结论的原始材料：核验记录、证据文件与逐条调研。

## 课题输入

| 文件 | 内容 |
|---|---|
| `s1-input/research-context.md` | 最初的研究上下文，含命题、runtime 语义、Task A/B/C、metrics 与 pipeline |
| `s1-input/week2-deck.md` | 第二周汇报全文 40 页，滑坡泥石流通信综述，含 51 条参考文献（由 PPT 提取，未纳入版本控制） |

## 场景与需求

| 文件 | 内容 |
|---|---|
| `s2-scenario/geohazard-china-context.md` | 中国政策与产业背景，含政策文号、北斗约束、低温物理与中通服实况 |
| `s2-scenario/lowpower-mountain-recon.md` | 低功耗山区通信的可用数据与仿真工具链 |
| `s2-scenario/evidence/` | 三份被 README 引用的原始证据，涉及链路物理、数据集与年报政策 |

## 撞车与空白

| 文件 | 内容 |
|---|---|
| `s3-novelty/verified-evidence.md` | 一手核验记录，含 IODA 与 FEMA 的实测数据、INFOCOM 2026 撞车论文的全文引用 |
| `s3-novelty/shijin-group-survey.md` | 金石课题组的调研，含 agentic 研究线、ISAC 工作的实测状态、可借资产与方向信号 |
| `s3-novelty/prior-art-mother-papers.md` | TopoLLM、6GAgentGym、WirelessAgent++、α³-Bench 的逐篇核实 |
| `s3-novelty/prior-art-agent-runtime.md` | 机制层的不可声称清单与 7 个空白 |
| `s3-novelty/venue-and-positioning.md` | 会议截止时间与定位 |

## 故障生态

| 文件 | 内容 |
|---|---|
| `s4-fault-source/simulation-feasibility.md` | 真实地形、真实轨迹与能量模型的实测结果及工具链 |
| `s4-fault-source/dataset-recon.md` | 数据集普查，含 13 项排序与负面结论 |

## 约束模型与实验规范

| 文件 | 内容 |
|---|---|
| `s5-benchmark/s5-1-failure-model.md` | 生命周期状态机，以及故障类与物理生成源的映射 |
| `s5-benchmark/s6-10-wirelessopsbench-artifact-audit.md` | 采用对象的公开 artifact 逐字审计，含不可执行的判定与采用边界 |
| `s5-benchmark/s6-11-execution-layer-results.md` | 执行层在公开任务契约上的 2×2 消融结果与效力威胁 |
| `s5-benchmark/s6-9-benchmark-comparison.md` | 六个现有 benchmark 的逐条核验，为 README 现状盘点的依据 |
| `s5-benchmark/s6-6-same-domain-baselines.md` | 可复现 baseline 的逐库核验与复现验收标准 |
| `s5-benchmark/s6-7-experimental-norms.md` | 通信、系统、LLM-agent 三个社区的实验规范与可复现性统计 |
| `s5-benchmark/s6-5-data-provenance.md` | 数据来源分层、效力威胁与实验协议 |
| `s5-benchmark/s6-2-physical-model-results.md` | 物理模型对比的实测结果 |

## 系统模型

| 文件 | 内容 |
|---|---|
| `s6-model/system-model.md` | 论文 Section II 初稿，含参数表与证据层标注、指标定义、待补清单 |

## 运行

```bash
export PYTHONPATH="$PWD/libs/pylibs"
python3 code/mountain_lora_link.py     # 单点链路预算
python3 code/coverage_map.py           # 区域覆盖图，约 30 s
python3 code/test_failure_model.py     # 11 类故障验证
```
