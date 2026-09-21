# PaperScope 服务器实验

服务器项目路径：`/home/ZhangYunhao/community_wiki`。

实验配置为 `benchmark.paperscope.yaml`，模型与 embedding 地址均为
`http://127.0.0.1:8080/v1`（服务器本机）。密钥仍独立保存在 `api_keys.yaml`。

合并数据集包含 93 篇 PDF，以及 gap 119 题、results_comparison 116 题、trend
117 题。原始 prepared 数据不修改。两个检索模式共用同一次文档入库、向量索引和
社区构建，各自运行全部 352 题，随后执行 LLM judge。问答与评分合计并发均为 5。
文档处理、生成请求、embedding、社区描述、聚类分支、单题工具调用并发也均为 5。

入口为 `scripts/run_grouped_benchmark.py`，内部执行 `benchmark --stage all`：
文档入库 → 社区生成 → 两种模式问答 → 评分 → 按类别汇总。
每道题的上下文独立。外层启动器使用独立进程会话、关闭标准输入并将输出写入日志，
因此 SSH 断开和当前 Codex 会话结束不会中断实验；服务器重启后不会自动恢复。

结果目录为 `data/runs/paperscope_93_naive_community/`：

- `process.json`：启动信息和后台进程 PID。
- `console.log` / `run.log`：控制台与实验日志，包括解析和 API 错误。
- `run_status.json` / `exit_code.txt`：运行状态及最终退出码。
- `indexing_metrics.json`：共享入库及社区生成耗时和 token。
- `results.jsonl`：逐题实际回答、gold answer、状态、指标和评分。
- `summary.json`：按检索模式汇总。
- `summary_by_category.json`：结束后按 QA 类别及检索模式汇总。
- `traces/`：逐题 agent loop trace（具体文件名由实验模块生成）。

查看状态（在服务器执行）：

```sh
cd /home/ZhangYunhao/community_wiki
cat data/runs/paperscope_93_naive_community/run_status.json
tail -n 30 data/runs/paperscope_93_naive_community/console.log
```

## PDF 解析改版

当前源码改为 PDFParser → 本地 pdfplumber → 逐页正文、书签或字体标题、Markdown 表格。
新解析版本计入入库签名，禁止无意复用旧解析索引。按用户要求清理旧 PaperScope 实验
输出和索引后，在上方目录从头统一重建 93 篇文档；PDF 数据源保留。
文档摘要 prompt/schema 仍为 800 字符，程序侧允许 1000 字符。
新流程仍只读取文字层，不做 OCR；字号标题、表格结构和公式不保证完全还原。
若入库失败，流水线会停止，避免使用缺少文档的索引继续问答。
