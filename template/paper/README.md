# paper/

两份稿件放这里，例如 `paper/en/main.tex` 与 `paper/zh/main.tex`，共享一份 `refs.bib`。

表格体不写在稿件里：`paper/generated/` 存放由 `scripts/make_tables.py` 生成的表格体，稿件用

```latex
\input{../generated/table_<表>.<语言>.tex}
```

引入。生成物入库、不手改；结果文件变动时在同一次提交里重新生成。`code/experiments/audit_tables.py`
检查两者一致，并检查稿件里没有手写的表格行。

构建脚本 `paper/build.sh` 由你配置；`make paper` 会调用它。中英双稿若走不同引擎，在脚本内分开处理。
