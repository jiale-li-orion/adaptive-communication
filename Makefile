# 论文仓库统一入口。
#
# 三条命令对应三类可验证对象：检查层（check）、论文产物（paper）、论文数字（tables）。
# 其余脚本一律不作为入口使用；入口分散是"同一件事两处写法不一致"的源头。

ROOT := $(CURDIR)
PY   := python3

# 与 code/run_checks.py 内部设置的 PYTHONPATH 一致，保证从根目录与从子目录运行等价。
export PYTHONPATH := $(ROOT)/libs/pylibs:$(ROOT)/code:$(ROOT)/code/substrate/joint:$(ROOT)/code/substrate/instance:$(ROOT)/code/substrate/physics:$(ROOT)/code/substrate/runtime:$(ROOT)/code/substrate/reference:$(ROOT)/code/substrate/monitoring:$(ROOT)/code/evaluation/agentic:$(ROOT)/code/legacy-communication/runtime:$(ROOT)/code/legacy-communication/experiments:$(ROOT)/code/legacy-communication/analysis:$(ROOT)/code/legacy-communication/v3joint

.PHONY: all check paper agentic-paper tables agentic-o2 agentic-diagnosis agentic-baselines agentic-communication-baselines agentic-source-smoke agentic-robustness agentic-transfer agentic-action-context agentic-context-transition agentic-control-opportunity agentic-context-transition-r1 agentic-model-inputs agentic-model-matrix agentic-r1-model agentic-r3-model agentic-preapi deps data clean help

AGENTIC_SEEDS ?= 0,1,2,3,4

all: check paper

help:
	@echo "make check   检查层全量自检 + 联合层锚点（含 vendored 依赖干净 shell 检查）"
	@echo "make paper   构建两份论文稿 PDF"
	@echo "make agentic-paper  构建当前 Agentic Communication 英文工作稿并检查排版/引用"
	@echo "make tables  由结果文件生成论文表格、Agentic 结果摘要与受控文档区块"
	@echo "make agentic-o2  跑 O2 global/localized（默认 seeds $(AGENTIC_SEEDS)）并自动刷新文档/论文生成物"
	@echo "make agentic-diagnosis  跑 O2 diagnosis-first 5-seed paired baseline 并刷新生成物"
	@echo "make agentic-baselines  跑 O2 deterministic Agent baseline matrix 并刷新生成物"
	@echo "make agentic-communication-baselines  跑 Local/AoI/EnergyAware/EDF/maxcov + evaluator-only oracle matrix"
	@echo "make agentic-source-smoke  跑 O4 NASA POWER 2022/2023/2024 source-period full-sim gate"
	@echo "make agentic-robustness  跑 weather/outage/scope/owner/scale 五轴 paired full-sim gate"
	@echo "make agentic-transfer  跑 S14/Qili source-derived Operational Task 5-seed transfer gate"
	@echo "make agentic-action-context  跑 localized O2 action-conditioned Context method probe，并冻结 4 个预注册真实模型事件点"
	@echo "make agentic-context-transition  跑 O5 Task-revision consequence、冻结 Context update 四臂并做 pre-model validate"
	@echo "make agentic-control-opportunity  跑 O5 execution-layer audit + 20-seed remote-evidence/control-opportunity mechanism robustness"
	@echo "make agentic-context-transition-r1 MODEL=<id> [ARGS='...']  在 8 个冻结 Task-transition 输入上跑真实模型 R1"
	@echo "make agentic-model-inputs  冻结 task-conditioned/full-dump/generic-ReAct 三套 O2 R1 输入（无需 API）"
	@echo "make agentic-model-matrix MODEL=<id> [ARGS='...']  同模型三 context 的 R1→R3 统一流水线；需真实 endpoint/key"
	@echo "make agentic-preapi  重跑全部无需 API 的正式 Agentic/communication baseline、robustness、transfer、attribution 与 frozen inputs"
	@echo "make agentic-r1-model MODEL=<id> [ARGS='...']  frozen-input 模型诊断；缺真实 endpoint/key 直接失败"
	@echo "make agentic-r3-model MODEL=<id> [ARGS='...']  full-sim 模型运行；缺真实 endpoint/key 直接失败"
	@echo "make deps    获取需获取依赖（第三方 Python 包，幂等）"
	@echo "make data    获取需获取依赖（地形高程瓦片，幂等）"
	@echo "make all     check 加 paper"

# 检查层。run_checks.py 以退出码判定，不解析被检查脚本的输出。
check:
	$(PY) code/run_checks.py
	$(PY) code/substrate/joint/test_joint.py
	$(PY) scripts/make_layer1_paper_figures.py --check
	$(PY) scripts/make_future_choice_artifacts.py --check

# 论文产物。中文稿走 XeTeX，英文稿走 pdflatex，细节见 paper/build.sh。
paper:
	cd paper && ./build.sh

agentic-paper:
	cd paper/agentic && ./build.sh

# 需获取依赖。检查依赖它们，克隆后先跑这两条；缺失时检查会打印同样的命令。
deps:
	./scripts/get_deps.sh

data:
	./scripts/get_data.sh

# 论文数字。生成物入库，任何结果变动必须在同一次提交里重新生成。
tables:
	@test -f scripts/make_tables.py || { echo "scripts/make_tables.py 尚未实现（P3）"; exit 1; }
	$(PY) scripts/make_tables.py $(ARGS)
	$(PY) scripts/make_agentic_artifacts.py $(ARGS)
	$(PY) scripts/make_agentic_benchmark_manifest.py $(ARGS)
	$(PY) scripts/make_agentic_baseline_registry.py $(ARGS)
	$(PY) scripts/make_agentic_robustness_manifest.py $(ARGS)
	$(PY) scripts/make_agentic_attribution_protocol.py $(ARGS)
	$(PY) scripts/make_agentic_paper_v1.py $(ARGS)
	$(PY) scripts/make_future_choice_artifacts.py $(ARGS)

# Agentic Communication 第一条正式实验流水线：结果 -> audit -> research/results/paper 生成物。
agentic-o2:
	$(PY) code/evaluation/agentic/run_o2_risk_escalation.py --variant global --seeds $(AGENTIC_SEEDS)
	$(PY) code/evaluation/agentic/run_o2_risk_escalation.py --variant localized --seeds $(AGENTIC_SEEDS)
	$(PY) scripts/make_agentic_artifacts.py

agentic-context-transition:
	$(PY) code/evaluation/agentic/run_o5_task_revision_consequence.py
	$(PY) code/evaluation/agentic/freeze_o5_context_transition_devset.py
	$(PY) code/evaluation/agentic/freeze_o5_context_update_ablation.py
	$(PY) code/evaluation/agentic/run_o5_transition_context_model_probe.py --stage validate
	$(PY) code/evaluation/agentic/run_o5_context_update_model_probe.py --stage validate

agentic-control-opportunity:
	$(PY) code/evaluation/agentic/run_o5_task_revision_consequence.py
	$(PY) code/evaluation/agentic/freeze_o5_context_transition_devset.py
	$(PY) code/evaluation/agentic/run_o5_execution_layer_audit.py
	$(PY) code/evaluation/agentic/run_o5_query_delay_multiseed.py --seeds 0:20 --backhaul-delays 0,180,240,300
	$(PY) scripts/make_agentic_artifacts.py

agentic-context-transition-r1:
	@test -n "$(MODEL)" || { echo "MODEL=<model-id> is required"; exit 2; }
	$(PY) code/evaluation/agentic/run_o5_transition_context_model_probe.py --stage r1 --model "$(MODEL)" $(ARGS)
	$(PY) code/evaluation/agentic/run_o5_context_update_model_probe.py --stage r1 --model "$(MODEL)" $(ARGS)
	$(PY) scripts/make_agentic_benchmark_manifest.py
	$(PY) scripts/make_agentic_baseline_registry.py

agentic-diagnosis:
	$(PY) code/evaluation/agentic/run_o2_diagnosis_baseline.py --seeds $(AGENTIC_SEEDS)
	$(PY) scripts/make_agentic_artifacts.py
	$(PY) scripts/make_agentic_baseline_registry.py

agentic-baselines:
	$(PY) code/evaluation/agentic/run_o2_baseline_matrix.py --seeds $(AGENTIC_SEEDS)
	$(PY) scripts/make_agentic_artifacts.py
	$(PY) scripts/make_agentic_baseline_registry.py --check

agentic-communication-baselines:
	$(PY) code/evaluation/agentic/run_communication_baseline_matrix.py --seeds $(AGENTIC_SEEDS)
	$(PY) scripts/make_agentic_artifacts.py

agentic-source-smoke:
	$(PY) code/evaluation/agentic/run_source_period_smoke.py --seed 0
	$(PY) scripts/make_agentic_benchmark_manifest.py --check
	$(PY) scripts/make_agentic_artifacts.py

agentic-robustness:
	$(PY) code/evaluation/agentic/run_robustness_matrix.py
	$(PY) scripts/make_agentic_robustness_manifest.py --check
	$(PY) scripts/make_agentic_artifacts.py

agentic-transfer:
	$(PY) code/evaluation/agentic/run_task_transfer_qili.py --seeds $(AGENTIC_SEEDS)
	$(PY) scripts/make_agentic_artifacts.py

agentic-action-context:
	$(PY) code/evaluation/agentic/run_action_conditioned_context_probe.py --seeds $(AGENTIC_SEEDS)
	$(PY) code/evaluation/agentic/run_model_context_matrix.py --stage freeze --variant localized --freeze-seed 0 --contexts task_conditioned,full_dump,generic_react,action_conditioned,action_candidates_full_dump
	$(PY) code/evaluation/agentic/freeze_action_context_devset.py
	$(PY) code/evaluation/agentic/run_o5_task_revision_consequence.py
	$(PY) code/evaluation/agentic/freeze_o5_context_transition_devset.py
	$(PY) code/evaluation/agentic/freeze_o5_context_update_ablation.py
	$(PY) code/evaluation/agentic/run_o5_transition_context_model_probe.py --stage validate
	$(PY) code/evaluation/agentic/run_o5_context_update_model_probe.py --stage validate
	$(PY) scripts/make_agentic_artifacts.py

agentic-model-inputs:
	$(PY) code/evaluation/agentic/run_model_context_matrix.py --stage freeze --variant global --freeze-seed 0 $(ARGS)
	$(PY) scripts/make_agentic_artifacts.py

agentic-model-matrix:
	@test -n "$(MODEL)" || { echo "MODEL=<model-id> is required"; exit 2; }
	$(PY) code/evaluation/agentic/run_model_context_matrix.py --model "$(MODEL)" --stage both $(ARGS)

agentic-preapi:
	$(PY) code/evaluation/agentic/run_catalog_smoke.py --seed 0
	$(PY) code/evaluation/agentic/run_o2_risk_escalation.py --variant global --seeds $(AGENTIC_SEEDS)
	$(PY) code/evaluation/agentic/run_o2_risk_escalation.py --variant localized --seeds $(AGENTIC_SEEDS)
	$(PY) code/evaluation/agentic/run_o2_diagnosis_baseline.py --seeds $(AGENTIC_SEEDS)
	$(PY) code/evaluation/agentic/run_o2_baseline_matrix.py --seeds $(AGENTIC_SEEDS)
	$(PY) code/evaluation/agentic/run_communication_baseline_matrix.py --seeds $(AGENTIC_SEEDS)
	$(PY) code/evaluation/agentic/run_source_period_smoke.py --seed 0
	$(PY) code/evaluation/agentic/run_robustness_matrix.py
	$(PY) code/evaluation/agentic/run_task_transfer_qili.py --seeds $(AGENTIC_SEEDS)
	$(PY) code/evaluation/agentic/run_attribution_matrix_infra.py --turns 20
	$(PY) code/evaluation/agentic/run_action_conditioned_context_probe.py --seeds $(AGENTIC_SEEDS)
	$(PY) code/evaluation/agentic/run_model_context_matrix.py --stage freeze --variant global --freeze-seed 0
	$(PY) code/evaluation/agentic/run_model_context_matrix.py --stage freeze --variant localized --freeze-seed 0 --contexts task_conditioned,full_dump,generic_react,action_conditioned,action_candidates_full_dump
	$(PY) code/evaluation/agentic/freeze_action_context_devset.py
	$(PY) code/evaluation/agentic/run_o5_task_revision_consequence.py
	$(PY) code/evaluation/agentic/freeze_o5_context_transition_devset.py
	$(PY) code/evaluation/agentic/run_o5_execution_layer_audit.py
	$(PY) code/evaluation/agentic/run_o5_query_delay_multiseed.py --seeds 0:20 --backhaul-delays 0,180,240,300
	$(PY) scripts/make_agentic_artifacts.py
	$(PY) scripts/make_agentic_benchmark_manifest.py --check
	$(PY) scripts/make_agentic_baseline_registry.py --check
	$(PY) scripts/make_agentic_robustness_manifest.py --check
	$(PY) scripts/make_agentic_attribution_protocol.py --check
	$(PY) code/run_checks.py --group agentic

agentic-r1-model:
	@test -n "$(MODEL)" || { echo "MODEL=<model-id> is required"; exit 2; }
	$(PY) code/evaluation/agentic/run_r1_model_eval.py --model "$(MODEL)" $(ARGS)

agentic-r3-model:
	@test -n "$(MODEL)" || { echo "MODEL=<model-id> is required"; exit 2; }
	$(PY) code/evaluation/agentic/run_r3_model_eval.py --model "$(MODEL)" $(ARGS)

# 只清理构建中间产物，不触碰 PDF 与生成表。
clean:
	cd paper && rm -f en/main.aux en/main.log en/main.out en/main.bbl en/main.blg \
	                zh/main.aux zh/main.log zh/main.out zh/main.bbl zh/main.blg
