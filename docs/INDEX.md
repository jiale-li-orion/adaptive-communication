# 文档索引

**[`../README.md`](../README.md) 是唯一的权威文档**——定位、证据、实体分类、现状盘点都在那里。
本目录存放**支撑 README 结论的原始材料**：核验记录、证据文件、逐条调研。

---

## 支撑材料

### s1-input · 课题原始输入
| 文件 | 内容 |
|---|---|
| `research-context.md` | 最初的研究上下文（命题、runtime 语义、Task A/B/C、metrics、pipeline） |
| `week2-deck.md` | 第二周汇报全文 40 页（滑坡泥石流通信综述，含 51 条参考文献） |

### s2-scenario · 场景与需求
| 文件 | 内容 |
|---|---|
| `geohazard-china-context.md` | 中国政策与产业背景（政策文号、北斗约束、低温物理、中通服实况、数据集普查） |
| `lowpower-mountain-recon.md` | 低功耗山区通信的可用数据与仿真工具链 |
| `evidence/` | 3 份被 README §1.2 / §3.1 引用的原始证据（链路物理、数据集、年报政策） |

### s3-novelty · 撞车与空白
| 文件 | 内容 |
|---|---|
| `verified-evidence.md` | **一手核验证据**（IODA/FEMA 实测、INFOCOM 2026 撞车全文引用） |
| `shijin-group-survey.md` | **金石（东大）组调研**：agentic 线、ISAC 实测状态、可借资产、方向信号 |
| `prior-art-mother-papers.md` | TopoLLM / 6GAgentGym / WirelessAgent++ / α³-Bench 逐篇核实 |
| `prior-art-agent-runtime.md` | 机制层"不可声称"清单 + 7 个 gap |
| `venue-and-positioning.md` | 会议 deadline 与定位 |

### s4-fault-source · 故障生态
| 文件 | 内容 |
|---|---|
| `simulation-feasibility.md` | 真实地形 + 真实轨迹 + 能量模型的实测结果与工具链 |
| `dataset-recon.md` | 数据集普查（13 项排序 + 负面结论） |

### s5-benchmark · 约束模型与实验规范
| 文件 | 内容 |
|---|---|
| `s5-1-failure-model.md` | 生命周期状态机 + 故障类与物理生成源的映射 |
| `s6-9-benchmark-comparison.md` | **六个现有 benchmark 的逐条核验**（README §3.3 的依据） |
| `s6-6-same-domain-baselines.md` | 可复现 baseline 逐库核验 + 复现验收标准 |
| `s6-7-experimental-norms.md` | 三个社区的实验规范与可复现性硬数字 |
| `s6-5-data-provenance.md` | 数据来源四层效力表 + 效力威胁 + 实验协议 |
| `s6-2-physical-model-results.md` | 物理模型对比的实测结果 |

---

## 其他

`code/` 13 个可运行脚本 · `data/` SRTM 与下载数据 · `results/` 仿真输出 · `libs/pylibs/` 依赖

```bash
export PYTHONPATH=/home/orion/Communications/libs/pylibs
python3 code/mountain_lora_link.py     # 单点链路预算
python3 code/coverage_map.py           # 区域覆盖图（约 30 s）
python3 code/test_failure_model.py     # 11 类故障验证
```
