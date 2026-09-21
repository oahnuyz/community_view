# community_wiki

以文档为节点的社区 RAG 原型。当前实现 `naive`、`community` 两种模式；两种模式共用原生工具调用 agent loop。`wiki` 和社区综合报告暂不实现。

## 已实现的需求

| 阶段 | 用户可得到的功能 | 技术路线 |
|---|---|---|
| 1. 文档入库 | 批量读取 TXT、Markdown、可提取文字的 PDF；并发提取每篇文档的 title、关键词、简短摘要，组成文档 overview | asyncio 并发、OpenAI-compatible Chat Completions、JSON schema 与本地校验 |
| 2. 长文档处理 | 超过可配置 token 阈值后逐片处理；明确告知片号、总片数和前片累计信息；最后一片输出全文 overview | Unicode 完整的 token 分片；同篇顺序综合、不同篇并发；不截掉后半篇 |
| 3. 切片及索引 | 原文切片、chunk embedding、文档 overview embedding；chunk 的来源字段只有 doc_id 和 ordinal | tiktoken；SQLite 保存文本/向量；NumPy 精确向量搜索；jieba + BM25 关键词检索 |
| 4. 文档建图 | 配置选择向量、关键词或混合建边，保存所有通过候选与阈值筛选的边及分项得分 | overview 向量余弦；关键词短语 TF-IDF 余弦；每通道 top-k 候选并集 |
| 5. 层次社区 | 超过文档数量阈值就尝试递归拆分；独立分支可并发；保留层级、父子社区、全部覆盖文档 | igraph + Leiden RB modularity；进程池；拆分失败保留叶社区并记日志 |
| 6. 社区描述和联系 | 每个社区并发生成简短 name、overview；父社区直接使用覆盖的全部文档 overview；保存同层社区联系及不同深度叶社区联系 | LLM 描述与下层拆分可同时执行；全量保留跨社区文档边，另存社区间 sum/max 汇总 |
| 7. 检索扩展 | 按 chunk 排名选前 doc_k 个不同文档；自动扩展其叶社区与各自最大关联边连接的叶社区；doc_ids 仅限制 chunk 搜索 | 固定 pipeline；不提供社区工具；单次问题跨全部 agent 轮次去重 |
| 8. Agent 问答 | 多轮搜索、换词、按文档 ID 限定搜索、读取相邻 chunk；naive/community 切换；每题独立上下文 | 少量严格类型工具、原生 tool_calls 循环、同轮工具并发、轮数及重复调用限制、SQLite 运行记录 |

完整的规则、所有参数及代码模块说明见 [实现说明](docs/IMPLEMENTATION.md)。

## 本地运行

已在本项目 `.venv` 安装依赖，使用 Python 3.12。无需数据库服务。`requirements.lock` 记录本次验证使用的依赖版本。

1. 复制 `config.yaml` 为 `config.local.yaml`，修改 `model.chat_model`、`embedding.model`；按服务修改两处 `base_url`。
2. 在独立的 `api_keys.yaml` 填写 `chat_api_key` 和 `embedding_api_key`。主配置用 `keys_file` 指向此文件，实验快照不会包含密钥值。该文件已加入 `.gitignore`。
3. 执行：

```sh
.venv/bin/community-wiki --config config.local.yaml config-check
.venv/bin/community-wiki --config config.local.yaml build /absolute/path/to/documents
.venv/bin/community-wiki --config config.local.yaml ask '这些文档讨论了哪些主要方法？' --mode community
.venv/bin/community-wiki --config config.local.yaml ask '这些文档讨论了哪些主要方法？' --mode naive
```

`build` = `ingest` 后 `cluster`。也可分别运行；入库任意文档失败时命令返回非零，成功的文档保留，`build` 不发布新社区。修正后重跑会跳过内容和提取配置未改变的文档。

```sh
.venv/bin/community-wiki --config config.local.yaml ingest ./documents/a.md ./documents/b.pdf
.venv/bin/community-wiki --config config.local.yaml cluster
.venv/bin/community-wiki --config config.local.yaml search '检索增强' --search-mode hybrid --doc-ids '文档ID1' '文档ID2'
.venv/bin/community-wiki --config config.local.yaml inspect documents
.venv/bin/community-wiki --config config.local.yaml inspect communities
.venv/bin/community-wiki --config config.local.yaml inspect edges
.venv/bin/community-wiki --config config.local.yaml inspect links
.venv/bin/community-wiki --config config.local.yaml inspect stats
.venv/bin/community-wiki --config config.local.yaml inspect run --run-id RUN_ID
```

`search`、`ask` 使用 `--doc-ids ID1 ID2` 限定原文 chunk 范围，不再支持 `--title`。`ask` 的范围约束同时适用于搜索和直接读取；Agent 每次搜索可以用 doc_ids 进一步缩小范围。社区扩展仍可包含范围之外的文档。Agent 只有 `search_chunks` 和 `read_chunks` 两个工具；文档 overview 始终同时提供 `doc_id` 和 `title`，可从首次搜索结果获取 ID 后定向检索，也可用 `inspect documents` 查看本地文档 ID。

每次 `ask` 和实验中的每条 QA 都有独立的消息历史与去重记录，单次问题内部保留完整工具历史。不提供交互式聊天。运行记录存于 SQLite，可以检查；当前没有从记录恢复执行的功能。

## 关键初始参数

| 参数 | 默认 | 含义 |
|---|---:|---|
| `overview.concurrency` | 6 | 同时处理的文档数 |
| `overview.fragment_tokens` | 6000 | 单个原文分片的 token 上限 |
| `overview.summary_max_chars` | 800 | prompt 和 JSON schema 中的文档摘要字符上限 |
| `overview.summary_validation_max_chars` | 1000 | 本地文档摘要校验上限；其他字段仍按原限制校验 |
| `text.chunk_tokens / chunk_overlap_tokens` | 600 / 80 | chunk 大小 / 目标重叠量 |
| `graph.mode / neighbor_k` | hybrid / 15 | 建边方式 / 每个通道候选邻居数 |
| `graph.vector_weight / min_weight` | 0.7 / 0.25 | 混合向量权重 / 保留边阈值 |
| `community.max_documents` | 20 | 超过即尝试拆分，非强制上限 |
| `community.cluster_workers / description_concurrency` | 2 / 4 | 聚类进程数 / 描述并发数 |
| `agent.tool_concurrency` | 4 | 单个问题同一轮工具执行并发数；结果按调用顺序回填和去重，1 为串行 |
| `community.overview_max_chars` | 500 | 社区 overview 字符上限 |
| `retrieval.chunk_k / doc_k` | 12 / 3 | chunk 召回数 / 用于扩展的不同文档数 |
| `agent.max_rounds` | 8 | 单个问题模型调用轮数上限；末轮只生成答案 |

表中列的是首版初始值；当前有效值以 `config.yaml` 为准。模型请求不设置输入/输出 token 上限，使用 API 服务端默认值。长文档分片、chunk 大小及简短 overview 字符长度约束仍保留。

## 验证与范围

```sh
.venv/bin/pytest -q
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
```

测试覆盖真实 Leiden、多进程完整构建流程、长文档累计综合、HTTP 协议与重试、标题过滤、三种建边/检索、跨层叶社区扩展、问题级去重及事务失败恢复。测试用可控的模型响应和 embedding，不会产生在线模型费用；真实模型质量和兼容性仍需配置服务后验证。

当前没有 wiki 报告、回答引用追溯、社区分页、上下文压缩、上下文总预算或 OCR。父社区会生成和保存，但检索仅扩展叶社区。向量数据载入内存，精确建图约为 O(N²) 相似度计算，适合先做中小规模验证；大规模数据需后续替换候选搜索为 ANN。文档更新后须全量重建社区，尚不支持局部社区增量更新或删除命令。

## 统一实验接口

所有 `prepared/` 格式数据集使用同一个接口。实验配置见 [benchmark.yaml](benchmark.yaml)，包含数据集路径、输出路径、QA 选择、运行模式和 QA/评分共用的并发数。`count: null` 表示运行全部剩余 QA。当前配置指向 ScholarQA-Multi 清理后的 92 条 QA 与 413 篇语料。

```sh
# 只检查数据与选择样本，不调用模型
.venv/bin/community-wiki benchmark --settings benchmark.yaml --stage prepare
# 以下命令供后续实际实验使用，当前尚未执行
.venv/bin/community-wiki --config config.local.yaml benchmark --settings benchmark.yaml --stage index
.venv/bin/community-wiki --config config.local.yaml benchmark --settings benchmark.yaml --stage ask
.venv/bin/community-wiki --config config.local.yaml benchmark --settings benchmark.yaml --stage judge
```

`--stage all` 依次完成入库、问答和 LLM 评分。文档入库与社区生成也可分别用 `--stage ingest`、`--stage cluster` 执行；`index` 连续执行这两个入库阶段。`run` 是 `ask` 的兼容别名。其他数据集复制一份实验 YAML，修改路径即可；每个实验使用独立数据库和输出目录。

每题的实际回答、gold answer、状态、耗时、token（含 embedding）、轮次，以及评分结果 `evaluation` 写在同一 `results.jsonl` 中；`traces/` 保存完整 Agent 可见对话。入库总耗时与总 token 在 `indexing_metrics.json`，QA 均值和评分均值在 `summary.json`。accuracy 为有效评分的平均值（0–4），normalized_accuracy 为 accuracy/4（0–1）；评分失败/跳过数量单列，缺失评分不记作 0。不输出逐 API 请求明细或缓存命中统计。完整口径见 [实验说明](docs/EXPERIMENTS.md)。
