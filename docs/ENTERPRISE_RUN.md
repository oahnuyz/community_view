# EnterpriseRAGBench 服务器实验

入口：`scripts/run_grouped_benchmark.py --config config.yaml --settings benchmark.enterprise.yaml`。
使用服务器 `/home/ZhangYunhao/community_wiki/.venv/bin/python` 启动独立后台进程。

数据源：`/noraiddata/ZhangYunhao/ov-wiki-benchmark-data/prepared/enterprise_rag_bench_selected_80`，
原样复制到项目 `data/benchmarks/enterprise_rag_bench_selected_80`，不修改原始 prepared 数据。
323 篇 TXT 按物理文件分别入库，保留数据集故意设置的重复文档；80 条 QA 包括
project_related 40 条、conflicting_info 20 条、completeness 20 条。

新数据库按规范绝对路径排序预留 `D0001` 到 `D0323`；入库失败重试保留预留编号。
一次文档入库 → 一次社区构建 → naive/community 各 80 次问答 → 各 80 次评分 → 分类别汇总。
沿用 `config.yaml` 的模型、PDF/文本处理、摘要限制、检索和全部并发设置；各并发均为 5。
两个 API 地址均为服务器本机 `http://127.0.0.1:8080/v1`。

输出：`data/runs/enterprise_rag_bench_80_naive_community/`。

- `process.json`：后台 PID、启动命令及部署的 Git 提交号。
- `run_status.json`、`exit_code.txt`：运行状态和退出码。
- `console.log`、`run.log`：日志。
- `indexing_metrics.json`：共享入库/社区构建耗时和 token。
- `results.jsonl`：回答、gold、单题指标和评分。
- `traces/`：单题 agent loop。
- `summary.json`、`summary_by_category.json`：按模式及类别汇总。

旧 ScholarQA 和 PaperScope 结果及其数据库、长 ID、历史 trace 全部保留，不做迁移。
本实验的编号仅在本数据库内有意义，不是跨数据集统一文档编号。
