# community_wiki

以文档为节点的社区 RAG 原型。当前实现 `naive`、`community`、`community_guide` 三种模式，共用原生工具调用 agent loop。`wiki` 和社区综合报告暂不实现。

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
| 8. Agent 问答 | 多轮搜索、换词、按文档 ID 限定搜索、读取相邻 chunk；naive/community/community_guide 切换；每题独立上下文 | 少量严格类型工具、原生 tool_calls 循环、同轮工具并发、轮数及重复调用限制、SQLite 运行记录 |

完整的规则、所有参数及代码模块说明见 [实现说明](docs/IMPLEMENTATION.md)。

所有数据集统一使用 `prompts/document.txt` 和 `prompts/community.txt`。QA 上下文中的文档 overview 只展示 `doc_id`、`title`、完整 `summary`，省略关键词；关键词仍保留在入库数据中用于建图。同一问题中每篇文档只展示一次。

`community_guide` 在首次模型调用前，用原始问题按配置的检索方式搜索一次，执行与 community 相同的社区扩展，但只注入社区和文档 overview，不注入命中的 chunks。该模式独有的提示词说明这些资料只是可能相关的初步导览，信息不明确时应继续调用工具。后续工具正常返回原文 chunks，去重记录覆盖首轮及后续全部轮次。固定搜索的耗时和 query embedding token 计入单题指标，不额外计作一次 Agent 轮次。可通过 `ask --mode community_guide`，或实验配置 `modes: [naive, community, community_guide]` 启用。

新长度限制作用于后续生成，不自动修改已有入库数据；写作目标下界不强制填满，字符数包含空格和标点。

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

`search`、`ask` 使用 `--doc-ids ID1 ID2` 限定原文 chunk 范围，不再支持 `--title`。`ask` 的范围约束适用于搜索；Agent 每次搜索可以用 doc_ids 进一步缩小范围。社区扩展仍可包含范围之外的文档。普通问答仅提供 `search_chunks` 工具；文档 overview 始终同时提供 `doc_id` 和 `title`，可从首次搜索结果获取 ID 后定向检索，也可用 `inspect documents` 查看本地文档 ID。

每次 `ask` 和实验中的每条 QA 都有独立的消息历史与去重记录，单次问题内部保留完整工具历史。不提供交互式聊天。运行记录存于 SQLite，可以检查；当前没有从记录恢复执行的功能。

新入库文档使用数据库分配的 `D0001`、`D0002` 等短 ID，重试和重启后保持不变；失败预留可能留下空号，编号不回收。编号在各数据库内独立，旧实验中的 ID 保留。

## 关键初始参数

| 参数 | 默认 | 含义 |
|---|---:|---|
| `overview.concurrency` | 6 | 同时处理的文档数 |
| `overview.fragment_tokens` | 6000 | 单个原文分片的 token 上限 |
| `overview.summary_target_min_chars / summary_max_chars` | 300 / 350 | 文档摘要写作目标区间；schema 上限为 350 |
| `overview.summary_validation_max_chars` | 450 | 本地文档摘要硬上限；超限带错误反馈重试，不截断 |
| `text.chunk_tokens / chunk_overlap_tokens` | 600 / 80 | chunk 大小 / 目标重叠量 |
| `graph.mode / neighbor_k` | hybrid / 15 | 建边方式 / 每个通道候选邻居数 |
| `graph.vector_weight / min_weight` | 0.7 / 0.25 | 混合向量权重 / 保留边阈值 |
| `community.max_documents` | 6 | 超过即尝试拆分，非强制上限 |
| `community.llm_split_fallback` | false | Leiden 无法继续拆分的超阈值社区，是否让 LLM 再划分一次 |
| `community.cluster_workers / description_concurrency` | 5 / 5 | 聚类进程数 / 描述与 LLM 拆分共用并发数 |
| `agent.tool_concurrency` | 4 | 单个问题同一轮工具执行并发数；结果按调用顺序回填和去重，1 为串行 |
| `community.overview_target_min_chars / overview_max_chars` | 150 / 200 | 社区 overview 写作目标区间；schema 上限为 200 |
| `community.overview_validation_max_chars` | 250 | 本地社区 overview 硬上限；超限带错误反馈重试 |
| `retrieval.chunk_k / doc_k` | 12 / 3 | chunk 召回数 / 用于扩展的不同文档数 |
| `agent.max_rounds` | 8 | 单个问题模型调用轮数上限；末轮只生成答案 |

表中列的是首版初始值；当前有效值以 `config.yaml` 为准。模型请求不设置输入/输出 token 上限，使用 API 服务端默认值。长文档分片、chunk 大小及简短 overview 字符长度约束仍保留。

可选 `community.llm_split_fallback: true`：仅对超阈值且 Leiden 返回一个分组的社区触发。LLM 接收社区 name、overview 和所有成员的完整文档 overview（含 doc_id、title、keywords、summary），只返回 `split` 与 `groups`。分组必须完整覆盖文档且每篇恰好出现一次；可选择不拆分。有效子社区按原流程生成 name/overview，但不再递归拆分，即使仍超过阈值也保留。分组错误带具体反馈修正，最多两次；请求或校验最终失败则保留原叶社区并记日志。分组及新增描述耗费计入社区构建阶段，开关关闭时不调用此 prompt。开启或修改拆分 prompt 后需重新执行 cluster，文档及 embedding 无需重新生成。

## 验证与范围

```sh
.venv/bin/pytest -q
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
```

测试覆盖真实 Leiden、多进程完整构建流程、长文档累计综合、HTTP 协议与重试、标题过滤、三种建边/检索、跨层叶社区扩展、问题级去重及事务失败恢复。测试用可控的模型响应和 embedding，不会产生在线模型费用；真实模型质量和兼容性仍需配置服务后验证。

当前没有 wiki 报告、回答引用追溯、社区分页、上下文压缩、上下文总预算或 OCR。父社区会生成和保存，但检索仅扩展叶社区。向量数据载入内存，精确建图约为 O(N²) 相似度计算，适合先做中小规模验证；大规模数据需后续替换候选搜索为 ANN。文档更新后须全量重建社区，尚不支持局部社区增量更新或删除命令。

## 统一实验接口

所有 `prepared/` 格式数据集使用同一个接口。实验配置见 [benchmark.scholarqa.yaml](benchmark.scholarqa.yaml)，包含数据集路径、输出路径、QA 选择、运行模式和 QA/评分共用的并发数。`count: null` 表示运行全部剩余 QA。当前配置指向 ScholarQA-Multi 清理后的 92 条 QA 与 413 篇语料。

```sh
# 只检查数据与选择样本，不调用模型
.venv/bin/community-wiki benchmark --settings benchmark.scholarqa.yaml --stage prepare
# 以下命令供后续实际实验使用，当前尚未执行
.venv/bin/community-wiki --config config.local.yaml benchmark --settings benchmark.scholarqa.yaml --stage index
.venv/bin/community-wiki --config config.local.yaml benchmark --settings benchmark.scholarqa.yaml --stage ask
.venv/bin/community-wiki --config config.local.yaml benchmark --settings benchmark.scholarqa.yaml --stage judge
```

`--stage all` 依次完成入库、问答和 LLM 评分。文档入库与社区生成也可分别用 `--stage ingest`、`--stage cluster` 执行；`index` 连续执行这两个入库阶段。`run` 是 `ask` 的兼容别名。其他数据集复制一份实验 YAML，修改路径即可；每个实验使用独立数据库和输出目录。

每题的实际回答、gold answer、状态、耗时、token（含 embedding）、轮次，以及评分结果 `evaluation` 写在同一 `results.jsonl` 中；`traces/` 保存完整 Agent 可见对话。入库总耗时与总 token 在 `indexing_metrics.json`，QA 均值和评分均值在 `summary.json`。accuracy 为有效评分的平均值（0–4），normalized_accuracy 为 accuracy/4（0–1）；评分失败/跳过数量单列，缺失评分不记作 0。不输出逐 API 请求明细或缓存命中统计。完整口径见 [实验说明](docs/EXPERIMENTS.md)。

## 社区问题视图

`knowledge.record_questions` 独立控制外部问题与实际展示叶社区的映射记录；`knowledge.use_compiled` 独立控制是否使用问题视图。两者默认关闭；未启用视图时不注入视图说明，也不提供答案读取工具。是否启用 LLM 社区拆分仍由 `community.llm_split_fallback` 独立控制。

`knowledge --stage plan` 根据社区和文档 overview 筛选、压缩、去重历史问题，保存每个提炼问题对应的原始问题。`knowledge --stage compile` 为每个问题运行独立 Agent，复用普通问答的 `agent.txt` 和 `question.txt`；每个社区内逐题编译，不同社区按 `knowledge.concurrency` 并发。`--stage all` 连续完成两步。成功答案可断点复用，完整社区视图以事务发布。

一个社区一个逻辑 view，不设字符上限，不另外生成 view 文件。SQLite 的 `knowledge_views` 保存社区视图信息，`knowledge_answers` 按 `(graph_key, question_id)` 精确索引答案；例如 `C0001-Q0001`。每条答案保留原始问题文本、原始运行 ID，以及可用的外部 QA ID。旧版整篇编译知识不会自动作为新视图使用，已有文档、社区和历史问题映射仍可复用。

启用视图问答时，先将用户问题与提炼问题做向量相似度匹配（`question_k`、`min_question_similarity`），向 Agent 展示去重后命中社区的完整问题目录，不直接注入答案。Agent 使用 `read_view_answers(question_ids)` 精确选读，每题去重，也可用 `search_chunks` 补充原文；当前不强制这两种工具的调用先后顺序。启用视图时，目录匹配替代 community_guide 的首次 chunk 搜索，后续搜索仍遵循所选检索模式。问题向量的生成和查询 token 分别计入编译阶段与 QA 阶段。

提炼和编译使用 `--config` 中 `storage.database` 指定的数据库；普通实验仍使用实验 YAML 指定的数据库。先在相同索引上开启记录并完成问答，然后执行：

```bash
.venv/bin/community-wiki --config config.local.yaml knowledge --stage plan
.venv/bin/community-wiki --config config.local.yaml knowledge --stage compile
```

`knowledge/` 保存阶段指标、编译进度和逐题 trace。重新聚类会改变图版本，旧映射和 view 不会自动用于新图。使用 view 的新实验应复制索引并选择新的输出目录；已发布答案变化后，不允许沿用旧问答结果续跑。

`scripts/run_compiled_benchmark.py --settings PIPELINE.yaml` 可串联记录问答、提炼、编译、复制索引、新知识问答和评测。管线 YAML 包含 `mapping_config`、`mapping_settings`、`compiled_config`、`compiled_settings` 四个路径，均相对该 YAML 解析；记录阶段的模型配置与实验配置必须指向同一个数据库，前后实验输出目录和数据库必须分开。也可分别使用上述命令和现有 `benchmark --stage ask/judge` 运行各阶段。
