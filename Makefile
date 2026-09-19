# 论文仓库统一入口。
#
# 三条命令对应三类可验证对象：检查层（check）、论文产物（paper）、论文数字（tables）。
# 其余脚本一律不作为入口使用；入口分散是"同一件事两处写法不一致"的源头。

ROOT := $(CURDIR)
PY   := python3

# 与 code/run_checks.py 内部设置的 PYTHONPATH 一致，保证从根目录与从子目录运行等价。
export PYTHONPATH := $(ROOT)/libs/pylibs:$(ROOT)/code/v3joint:$(ROOT)/code/instance:$(ROOT)/code/physics:$(ROOT)/code/runtime:$(ROOT)/code/experiments:$(ROOT)/code/analysis:$(ROOT)/code/monitoring

.PHONY: all check paper tables clean help

all: check paper

help:
	@echo "make check   检查层：18 项回归 + 5 项联合层锚点"
	@echo "make paper   构建两份论文稿 PDF"
	@echo "make tables  由结果文件生成论文表格（写入 paper/generated/）"
	@echo "make all     check 加 paper"

# 检查层。run_checks.py 以退出码判定，不解析被检查脚本的输出。
check:
	$(PY) code/run_checks.py
	$(PY) code/v3joint/test_joint.py

# 论文产物。中文稿走 XeTeX，英文稿走 pdflatex，细节见 paper/build.sh。
paper:
	cd paper && ./build.sh

# 论文数字。生成物入库，任何结果变动必须在同一次提交里重新生成。
tables:
	@test -f scripts/make_tables.py || { echo "scripts/make_tables.py 尚未实现（P3）"; exit 1; }
	$(PY) scripts/make_tables.py $(ARGS)

# 只清理构建中间产物，不触碰 PDF 与生成表。
clean:
	cd paper && rm -f en/main.aux en/main.log en/main.out en/main.bbl en/main.blg \
	                zh/main.aux zh/main.log zh/main.out zh/main.bbl zh/main.blg
