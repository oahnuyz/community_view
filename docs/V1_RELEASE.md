# community_wiki v1

本次提交作为项目 **v1 版本**，使用本地 Git 注解标签 `v1` 固定版本。

## 版本能力

- 并发生成文档 overview，长文档逐片综合；PDF 转 Markdown，文档切片与 embedding 入库。
- SQLite 独立实验数据库，持久化短文档 ID；向量、关键词或混合建图，递归社区聚类与社区 overview。
- naive / community 两种 agent 检索模式，工具并发执行，每题上下文独立；社区扩展与去重。
- 统一实验入口支持分阶段或全流程执行，记录入库、QA、评分指标和每题 trace；LLM judge 采用 0–4 分及归一化评分。
- 后台顺序实验队列，支持失败记录、继续后续实验及复用已成功入库的文档。

## 本次提交相对上一提交的改动

1. 文档摘要程序侧校验上限由 1000 调整到 1200 字符；prompt / JSON schema 仍为 800 字符，不截断输出。补充 1000、1100、1200 边界测试及文档说明。
2. 新增 MDAQA、WildGraphBench_summary health 子集实验配置，以及 EnterpriseRAGBench → MDAQA 顺序队列配置。
3. 新增 `scripts/run_benchmark_queue.py` 及队列测试：顺序执行、文件锁、状态和退出码记录、失败后继续或跳过剩余任务，并记录运行来源。
4. 补充 EnterpriseRAGBench 两次放宽校验后的续跑、已有数据复用和指标累计说明。
5. 新增五份独立 trace 对比报告：PaperScope gap、results_comparison、trend，EnterpriseRAGBench，MDAQA；新增涵盖六组 naive/community 对照实验的综合分析报告。既有 ScholarQA 报告保留。

## 实验状态与版本对应

- ScholarQA、PaperScope 三类 QA、EnterpriseRAGBench、MDAQA 共六组对照实验已完成。它们在项目演进过程中运行，历史结果应以各自配置和来源记录为准，不能统一宣称由本次提交重新运行产生。
- WildGraphBench_summary health（55 QA、509 TXT）本轮实验已由用户决定放弃。一次重试后入库 506 篇，剩余 3 篇 overview 请求返回 `content_filter`；尚未开始社区构建、QA 或评分。
- 服务器保留该轮数据库、日志、累计指标和失败记录，并通过实验目录中的 `abandoned.json` 记录放弃决定；不再自动续跑。
- `data/` 下的数据库、原始结果、trace 和密钥文件不纳入 Git。报告中的本机数据链接依赖相应本地分析材料，单独克隆仓库不会包含这些材料。

## 验证

- `pytest -q`：86 项通过。
- `ruff check .`：通过。
- `git diff --check`：通过。

本次只创建本地提交和 `v1` 标签，不推送远端，也不重新运行已有实验。
