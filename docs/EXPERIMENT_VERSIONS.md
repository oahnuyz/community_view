# 实验版本备注

本文件所在的 Git 提交冻结了 2026-09-21 PaperScope 后台实验所用的源码和配置。
提交前核对本机与 214 服务器的项目文件哈希；尚未实施短文档 ID，`doc_id` 仍为
规范绝对路径的 SHA-256。已有数据库和历史 trace 不做迁移。

## PaperScope：2026-09-21 09:50 启动的实验

- 服务器项目：`/home/ZhangYunhao/community_wiki`。
- 配置：`config.yaml`、`benchmark.paperscope.yaml`、`requirements.lock`。
- 数据集：`data/benchmarks/paperscope_summary_93_all`，93 篇 PDF，三类共 352 条 QA。
- 结果目录：`data/runs/paperscope_93_naive_community`。
- 两种模式：naive、community；共享一次文档入库与社区生成，各运行问答和 LLM judge。
- PDF：本地 pdfplumber 逐页转换为包含页码、书签/字号标题和表格的 Markdown。
- 文档摘要：prompt/schema 上限 800 字符，本地校验上限 1000 字符；不传模型输出 token 上限。
- 生成和 embedding 服务地址均为 `http://127.0.0.1:8080/v1`。
- 生成模型：`deepseek-v4-flash`；向量模型：`doubao-embedding-vision`，multimodal 接口、1024 维。
- 文档入库、生成请求、embedding、聚类进程、社区描述、Agent 工具、QA/评分并发均为 5。
- 入口：`scripts/run_grouped_benchmark.py`；后台独立进程顺序执行全部阶段，结束后按类别汇总。
- 先前使用 pypdf 的失败 PaperScope 输出已按用户要求清理，不能与本次结果混用。

## ScholarQA：此前已完成的实验

- naive：`data/runs/scholarqa_first_92_naive_20260920_223851`。
- community：`data/runs/scholarqa_first_92_community_20260920_232241`。
- 两轮均为前 92 条 QA，413 篇文档；community 复用 naive 入库结果。
- 对比分析：`docs/reports/scholarqa_naive_vs_community_trace_analysis.md`。

本提交包含上述实验的配置入口、相关实现修复和分析报告，但它是后续 PaperScope 修改后的
代码快照，并非 ScholarQA 当时全部源码与配置的逐字快照。重现 ScholarQA 时应参考各实验
目录保存的配置、指标和 trace，不应直接用当前 PaperScope 参数替代历史参数。

## 版本控制范围

提交包含源码、prompt、配置、锁定依赖、测试、后台入口和文档；`data/`、虚拟环境和
`api_keys.yaml` 按 `.gitignore` 排除。保留 Git 提交并不等同于备份实验数据或服务端模型版本。
