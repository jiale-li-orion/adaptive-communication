# 论文仓库统一入口。四条命令对应四类可验证对象。
ROOT := $(CURDIR)
PY   := python3

.PHONY: all check paper tables deps data clean help

all: check

help:
	@echo "make check   检查层：自动收集 code/experiments/ 下的 audit_*.py 与 test_*.py"
	@echo "make paper   构建稿件（需先在 paper/build.sh 配置）"
	@echo "make tables  由结果文件生成论文表格（写入 paper/generated/）"
	@echo "make deps    获取需获取依赖（第三方包）"
	@echo "make data    获取需获取依赖（数据集）"

check:
	$(PY) code/run_checks.py $(ARGS)

paper:
	@test -x paper/build.sh || { echo "paper/build.sh 尚未配置"; exit 1; }
	cd paper && ./build.sh

tables:
	$(PY) scripts/make_tables.py $(ARGS)

deps:
	@test -x scripts/get_deps.sh || { echo "scripts/get_deps.sh 尚未配置"; exit 1; }
	./scripts/get_deps.sh

data:
	@test -x scripts/get_data.sh || { echo "scripts/get_data.sh 尚未配置"; exit 1; }
	./scripts/get_data.sh

clean:
	rm -rf code/__pycache__ code/*/__pycache__
