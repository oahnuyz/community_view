# community_view

以整篇文档为图节点的 RAG 系统。先生成文档 overview、原文切片和向量，再对文档图进行层次社区聚类。问答使用 Agent loop，通过原文搜索和社区信息逐步获取证据；可选地筛选历史问题并复用其实际答案，生成社区问答 view，供后续按需读取。

项目使用 Python 3.12+、SQLite、本地精确向量检索、BM25、Leiden 和兼容 Chat Completions 的模型服务，无需单独部署向量数据库。生成、embedding 和 judge 均调用外部 API。

## 1. 系统流程

1. **文档入库**：读取 TXT、Markdown、PDF，为每篇文档生成 `title / keywords / summary`。不同文档并发；长文档按 token 分片，同篇逐片传入前文综合信息，最后生成全文 overview，不静默截掉后半篇。
2. **切片与向量**：原文按 token 切片，每片保存 `doc_id / ordinal / text / vector`；文档 overview 也有一份向量。新文档使用 `D0001` 等短 ID，chunk 编号从 0 开始。
3. **建图**：用文档向量、关键词或混合相似度寻找近邻，保存通过候选筛选和权重阈值的全部文档边。
4. **社区构建**：在全图运行 Leiden，超过 `max_documents` 的社区继续在诱导子图中尝试拆分。所有社区保存层次、父子关系、成员文档及 LLM 生成的 name/overview；当前 main 的检索只使用叶社区。
5. **Agent 问答**：每题拥有独立消息历史和去重状态。普通问答仅提供 `search_chunks`，可按 `doc_ids` 定向搜索正文。同一轮独立工具调用可并发执行。
6. **可选历史答案 view**：记录成功问答展示过的叶社区，逐社区筛掉完全无关的问题，原样保留剩余问题及其实际回答，不重新编译答案。新问答先匹配问题目录，首轮只提供 read_view_answers，第二轮起恢复 search_chunks。
7. **评测**：独立的 LLM-as-judge 阶段对照 gold answer 打 0–4 分，保存逐题理由和归一化均值。

PDF 使用本地 `pdfplumber`，逐页提取正文、书签/字号标题和 Markdown 表格，保留页码标记；没有自动 OCR 或 VLM。没有可提取内容的 PDF 会失败。社区 overview 是基于成员文档 overview 的短描述，不是全文社区报告；当前没有 wiki 模式、父社区召回、交互式 chat 或历史上下文压缩。

## 2. 环境、配置与密钥

在项目目录中操作。已有 Python 3.12 和 uv 时，可创建项目虚拟环境：

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.lock -e '.[dev]'
cp config.yaml config.local.yaml
cp api_keys.example.yaml api_keys.yaml
```

填写 `api_keys.yaml` 中的 `chat_api_key`、`embedding_api_key`，并修改 `config.local.yaml` 的服务地址和模型名称。模型需要支持工具调用和结构化 JSON 输出。若缺少 Python 或 uv，需先准备这些环境；上述命令不是实验运行的一部分。

- [config.yaml](config.yaml)：模型、入库、建图、社区、检索、Agent、知识编译和 prompt 路径，每项均有注释。
- [api_keys.example.yaml](api_keys.example.yaml)：不含真实密钥的示例。真实 `api_keys.yaml` 已被 Git 忽略，不应提交或上传到代码仓库；实验快照只保存密钥文件路径。
- [benchmark.example.yaml](benchmark.example.yaml)：通用实验配置，决定数据集、QA 范围、模式、输出目录和 QA/评测并发。
- `config.*.local.yaml`、`benchmark*.local.yaml`：本地实验配置，已被 Git 忽略。
- **所有 YAML 相对路径都相对于该 YAML 所在目录**，不是终端当前目录。以下示例把配置文件放在项目根目录。

```bash
.venv/bin/community-view --config config.local.yaml config-check
```

`config-check` 只校验配置结构和路径解析，不验证 API 连通性、密钥有效性或数据集是否可用。

## 3. naive、community、community_fallback 的配置

**代码中的检索模式只有 `naive` 和 `community`。`community_fallback` 是实验名称，表示 `community` 使用开启 LLM 后备拆分构建出的社区；不是合法的 `--mode` 或 `modes` 值。**

旧配置若包含已移除的 `community_guide` 模式或 `prompts.community_guide` 字段，需要先移除；程序不会静默将其转换成其他模式。

| 实验名称 | CLI `--mode` / 实验 `modes` | `community.llm_split_fallback` | 返回内容 |
|---|---|---|---|
| naive | `naive` / `[naive]` | 不影响 naive 的召回 | 原文 chunks、命中文档的 overview |
| community | `community` / `[community]` | `false` | 原文 chunks，加叶社区及其成员文档 overview |
| community_fallback | `community` / `[community]` | `true`，并据此生成社区 | 与 community 相同的检索流程，但社区划分可能不同 |

这三组普通对照实验均设 `knowledge.use_compiled: false`。如要为以后编译记录问题映射，可以独立设置 `knowledge.record_questions: true`。

`retrieval.mode` 是 `ask/search` 未指定 `--mode` 时的默认值；实验入口以实验 YAML 的 `modes` 为准。`graph.mode` 决定文档建图，`retrieval.search_mode` 决定 chunk 搜索，两者独立。

### 3.1 naive

```yaml
# config.local.yaml 中的编辑项；其他配置保留
retrieval:
  mode: naive
knowledge:
  record_questions: false
  use_compiled: false
```

naive 不召回社区，但会提供命中文档的 `doc_id / title / summary`，不展示 keywords。同一问题内文档 overview 只展示一次；原文 chunks 不做这类去重。

```bash
.venv/bin/community-view --config config.local.yaml ingest /path/to/documents
.venv/bin/community-view --config config.local.yaml ask '你的问题' --mode naive
```

### 3.2 community

```yaml
# config.local.yaml 中的编辑项
community:
  llm_split_fallback: false
retrieval:
  mode: community
```

每次 `search_chunks` 返回后，程序固定执行社区扩展：

1. 按 chunk 排名中首次出现的顺序，选前 `doc_k` 个不同文档。
2. 找到这些文档各自所属的叶社区。
3. 对每个选中文档，在其自身的文档边中取最强的合格跨社区边：另一端不在该文档的叶社区，也不在最初选中的 `doc_k` 文档集合中。
4. 加入另一端的叶社区，允许两个叶社区深度不同。本体与关联社区合计最多 `2 × doc_k` 个，再去重，并排除本题已展示过的社区。
5. 返回社区 name、overview、成员 doc_ids，以及尚未展示的成员文档 overview，保留原始命中 chunks。

最强边对应社区若已展示，不会改选次强边。`doc_ids` 仅限制原始 chunk 搜索，社区扩展仍可包含范围外文档。main 不召回父社区。

```bash
.venv/bin/community-view --config config.local.yaml build /path/to/documents
.venv/bin/community-view --config config.local.yaml ask '你的问题' --mode community
```

已完成文档入库时，使用 `cluster` 单独建图和生成社区，不再生成文档 overview 或 embedding：

```bash
.venv/bin/community-view --config config.local.yaml cluster
```

### 3.3 community_fallback

复制完整配置为 `config.fallback.local.yaml`，修改：

```yaml
storage:
  database: data/runs/my_dataset_fallback/index.sqlite3
  log_file: data/runs/my_dataset_fallback/run.log
community:
  llm_split_fallback: true
retrieval:
  mode: community
knowledge:
  record_questions: false
  use_compiled: false
```

只在 Leiden 无法继续拆分超阈值社区时，LLM 才接收社区 name/overview 和全部成员文档 overview，决定是否进一步分组。每个文档必须恰好归属一个子社区；非法分组反馈具体错误、最多修正两次。最终拆分失败时保留原叶社区并记日志。拆出的子社区继续生成 name/overview，但不再递归拆分，即使仍超过阈值也接受。

```bash
.venv/bin/community-view --config config.fallback.local.yaml build /path/to/documents
.venv/bin/community-view --config config.fallback.local.yaml ask '你的问题' --mode community
```

**不能仅在问答前把开关从 false 改为 true，就把普通 community 索引当成 fallback 索引。必须使用对应配置生成的社区。** 文档 overview、chunks 和 embedding 可以复用；普通社区与 fallback 社区应分别保存在独立实验数据库中，避免互相覆盖。

## 4. 当前默认配置与并发

以下是仓库 [config.yaml](config.yaml) 的实际值，不代表每台服务器历史实验的配置：

| 项目 | 当前默认值 |
|---|---|
| 生成 API / 模型 | `https://ark.cn-beijing.volces.com/api/plan/v3` / `deepseek-v4-flash` |
| embedding API / 模型 | 同一根地址 / `doubao-embedding-vision` |
| embedding 协议 / 维数 | `multimodal` / `1024`；标准文本接口可改为 `openai` |
| API 超时 / 失败额外重试 | 300 秒 / 2 次 |
| 温度 / 结构化输出 | `0.0` / `json_schema` |
| 长文原文分片 | 10,000 token，同篇顺序综合 |
| chunk 大小 / 重叠 | 600 / 80 token |
| 文档摘要目标 / 程序硬上限 | 300–350 / 450 字符 |
| 社区 overview 目标 / 程序硬上限 | 150–200 / 250 字符 |
| 建图 | hybrid；每通道 `neighbor_k=15`，`min_weight=0.25`，向量权重 `0.7` |
| 社区 | `max_documents=6`，`llm_split_fallback=false`，resolution=1，seed=42 |
| 默认检索 | `mode=naive`，`search_mode=vector`，`chunk_k=12`，`doc_k=3` |
| 混合搜索 | 两路各取至少 40 个候选，经 RRF 融合；`rrf_constant=60` |
| Agent | 最多 15 轮；相同工具与参数最多调用 2 次 |
| 知识功能 | `record_questions=false`，`use_compiled=false` |
| view 匹配 / 读取 | `question_k=3`，`min_question_similarity=0.2`，一次最多读取 8 个答案 |

生成请求不发送 `max_tokens` / `max_completion_tokens`，采用服务端默认窗口和输出上限；文档分片和摘要字符限制仍然生效。字符数包含空格、标点，不是词数或 token 数。当前回答 prompt 仍包含 `as briefly as possible`。

建图混合权重为 `0.7 × max(0, 文档向量余弦) + 0.3 × 关键词 TF-IDF 余弦`。先取两路近邻并集，再按权重阈值筛边；保存全部通过规则的边，不是保存所有文档二元组。关键词采用完整短语，chunk 关键词检索采用分词后的 BM25。

### 并发分别控制什么

| 参数位置 | 当前值 | 控制范围 |
|---|---:|---|
| `model.concurrency` | 5 | 单个模型客户端允许同时在途的生成 HTTP 请求；文档、社区、Agent、judge、提炼和编译都受此限制 |
| `embedding.concurrency` | 5 | 同一客户端的 embedding HTTP 请求并发 |
| `overview.concurrency` | 5 | 同时处理的文档数；同篇分片仍串行 |
| `community.cluster_workers` | 5 | 不同聚类分支的 CPU 进程数 |
| `community.description_concurrency` | 5 | 社区描述和 LLM fallback 拆分的共享并发 |
| `agent.tool_concurrency` | 5 | 单个 QA 同一轮允许并发执行的工具数 |
| `knowledge.concurrency` | 3 | 同时筛选问题的社区数；旧提炼/编译入口也使用此上限 |
| 实验 YAML 的 `concurrency` | 示例及现有数据集模板为 5 | QA 并发数；judge 复用同一个值；阶段内所有 `modes` 合计受此限制 |

这些限制不是简单相乘。比如 QA 并发为 10、`model.concurrency=5` 时，最多同时有 5 个生成请求，其余等待；每题的多个搜索工具还受 embedding 并发约束。不同进程各有自己的限制，同时启动多个实验会叠加请求量，没有跨进程全局限流。

`embedding.batch_size=32` 是标准 `openai` 协议每批文本数，不是并发数；`multimodal` 按每段文本单独请求，不使用该批量值。

## 5. 数据集实验入口

### 5.1 prepared 数据格式

```text
my_dataset/
  dataset_info.json
  documents.jsonl
  qa.jsonl
  corpus/
    ...txt / md / pdf
```

`dataset_info.json` 是数据来源说明。`documents.jsonl` 每行至少包含：

```json
{"id":"source-doc-1","path":"corpus/example.txt","sha256":"文件原始字节的SHA256","size_bytes":1234}
```

`qa.jsonl` 每行至少包含 `id`、`question`，评测还需要非空 `gold_answers`：

```json
{"id":"qa-1","question":"问题文本","gold_answers":["答案一","答案二"],"category":"gap","document_ids":["source-doc-1"]}
```

`category` 和 `document_ids` 可选。manifest 中的原始文档 ID 与入库分配的 `D0001` 不必相同。所有 manifest 文档进入统一语料库；只选前 N 条 QA **不会自动只入库这 N 题的关联文档**。gold、标注 evidence 和参考 document_ids 不传给问答 Agent，也不用于限制其搜索。

### 5.2 一次跑 naive 与 community

```bash
cp benchmark.example.yaml benchmark.local.yaml
```

编辑数据集路径、独立输出目录、数据库和题目范围，保留：

```yaml
modes: [naive, community]
concurrency: 5
```

主配置使用 `community.llm_split_fallback: false`。下面一次完成文档入库、普通社区构建、两模式问答及评测：

```bash
.venv/bin/community-view --config config.local.yaml benchmark --settings benchmark.local.yaml --stage all
```

两种模式共用一次索引，问答各自独立。只跑 naive 时设 `modes: [naive]`；其 `index/all` 不要求构建社区。

### 5.3 单独跑 community_fallback

复制实验配置为 `benchmark.fallback.local.yaml`，使用新的输出目录与数据库：

```yaml
dataset_dir: data/benchmarks/my_dataset
output_dir: data/runs/my_dataset_fallback
database: data/runs/my_dataset_fallback/index.sqlite3
log_file: data/runs/my_dataset_fallback/run.log
start: 0
count: null
modes: [community]
concurrency: 5
```

配合第 3.3 节的 `config.fallback.local.yaml`：

```bash
.venv/bin/community-view --config config.fallback.local.yaml benchmark --settings benchmark.fallback.local.yaml --stage all
```

结果中的 `mode` 仍是 `community`。汇报时根据独立实验目录及 `execution.json` 中的 fallback 开关，将它标为 `community_fallback`。不要写 `modes: [community_fallback]`。

若已有同一数据集的完整文档索引，可在源库未运行写任务时，用 SQLite backup 复制到新的 fallback 数据库，再执行 `cluster → ask → judge`。不要复制旧 `results.jsonl`、`execution.json` 或改写原社区库。示例路径对应上面的 baseline/fallback 配置，目标数据库必须尚不存在：

```bash
.venv/bin/python - <<'PY'
import sqlite3
from pathlib import Path
source = Path('data/runs/my_dataset_baseline/index.sqlite3').resolve()
target = Path('data/runs/my_dataset_fallback/index.sqlite3').resolve()
assert source.is_file() and not target.exists()
target.parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(f'file:{source}?mode=ro', uri=True) as src:
    with sqlite3.connect(target) as dst:
        src.backup(dst)
PY
.venv/bin/community-view --config config.fallback.local.yaml benchmark --settings benchmark.fallback.local.yaml --stage cluster
.venv/bin/community-view --config config.fallback.local.yaml benchmark --settings benchmark.fallback.local.yaml --stage ask
.venv/bin/community-view --config config.fallback.local.yaml benchmark --settings benchmark.fallback.local.yaml --stage judge
```

复用要求文档内容、入库配置及原文路径仍兼容；仅改社区参数不需要重新生成文档向量。切换 embedding 模型/配置不能这样直接复用。复制过来的旧图或知识映射不能当成新聚类后的映射使用，程序按图版本隔离。

### 5.4 分阶段执行与现有模板

| `benchmark --stage` | 执行内容 |
|---|---|
| `prepare` | 校验 prepared 文件、文档哈希和 QA 范围，不调用模型 |
| `ingest` | 文档 overview、切片、embedding；不生成社区 |
| `cluster` | 建图、聚类及社区描述；不重新生成文档 overview/embedding |
| `index` | ingest；若 `modes` 包含 community，再执行 cluster |
| `ask` | 在已有兼容索引上问答；`run` 是其别名 |
| `judge` | 对已保存回答评分，不重新问答，不要求打开索引或 embedding 服务 |
| `all` | index → ask → judge；**不包含知识提炼与编译** |

```bash
.venv/bin/community-view --config config.local.yaml benchmark --settings benchmark.local.yaml --stage prepare
.venv/bin/community-view --config config.local.yaml benchmark --settings benchmark.local.yaml --stage ingest
.venv/bin/community-view --config config.local.yaml benchmark --settings benchmark.local.yaml --stage cluster
.venv/bin/community-view --config config.local.yaml benchmark --settings benchmark.local.yaml --stage ask
.venv/bin/community-view --config config.local.yaml benchmark --settings benchmark.local.yaml --stage judge
```

现有数据集模板为 `benchmark.scholarqa.yaml`（92 QA）、`benchmark.enterprise.yaml`（80 QA）、`benchmark.paperscope.yaml`（352 QA）、`benchmark.mdaqa.yaml`（100 QA）。它们当前均设置 `modes: [naive, community]`、`concurrency: 5`，路径是历史使用的本地相对路径，运行前必须核对语料是否存在并选择新的结果目录。`count: null` 取 `start` 之后全部 QA；`start` 从 0 开始，按文件顺序选题。

多类别数据集可用以下入口额外生成 `summary_by_category.json`，例如 PaperScope 的 gap、results_comparison、trend 分开汇报：

```bash
.venv/bin/python scripts/run_grouped_benchmark.py --config config.local.yaml --settings benchmark.local.yaml --stages all
```

队列入口为 `scripts/run_benchmark_queue.py --settings benchmark.queue.yaml`，依次执行所列实验；`continue_on_error: true` 表示前一实验失败也继续后续实验。队列中所有实验使用同一主配置，混合普通社区与 fallback 时应分开配置队列或分别运行。后台运行可用：

```bash
mkdir -p data/queues/my_batch
nohup .venv/bin/python scripts/run_benchmark_queue.py --settings benchmark.queue.yaml > data/queues/my_batch/console.log 2>&1 < /dev/null &
```

## 6. 历史答案 view：映射 → 筛选 → view 问答 → 评测

主线采用**历史答案复用＋view 首轮不提供 search**，与服务器 community_view_history_answers_read_only 的检索行为一致。view 是可选功能，CLI mode 仍为 naive/community；使用 fallback 时选择对应的社区索引。

### 6.1 配置

复制完整配置为 config.mapping.local.yaml 和 config.view.local.yaml；复制实验配置为 benchmark.mapping.local.yaml 和 benchmark.view.local.yaml。以下只列需要编辑的字段：

| 配置 | mapping：记录问答、筛选 | view：新问答 |
|---|---|---|
| 主配置 storage.database | data/runs/my_dataset_mapping/index.sqlite3 | data/runs/my_dataset_view/index.sqlite3 |
| 主配置 storage.log_file | data/runs/my_dataset_mapping/run.log | data/runs/my_dataset_view/run.log |
| knowledge.record_questions | true | false |
| knowledge.use_compiled | false | true |
| knowledge.history_results | data/runs/my_dataset_mapping/results.jsonl | null |
| 实验 output_dir | data/runs/my_dataset_mapping | data/runs/my_dataset_view |
| 实验 database / log_file | 与对应主配置 storage 一致 | 与对应主配置 storage 一致 |
| 实验 modes | [community] | [community] |

record_questions 与 use_compiled 是独立开关；后者沿用旧字段名，但也适用于历史答案 view。filter_prompt 默认指向 prompts/knowledge_filter.txt。不同社区的筛选并发由 knowledge.concurrency 控制，QA/judge 并发由实验 YAML 的 concurrency 控制。

两套配置保持文档、embedding、建图和社区设置兼容；使用 fallback 时两边的 community.llm_split_fallback 都为 true。所有路径相对于其 YAML 文件。独立 knowledge-filter 命令直接读取主配置 storage，因此必须与 mapping 实验数据库一致。

### 6.2 记录成功问答与叶社区映射

没有索引时先 index；已有完整兼容索引可以跳过。记录实际展示过的叶社区，不代表这些社区一定有帮助。

```bash
.venv/bin/community-view --config config.mapping.local.yaml benchmark --settings benchmark.mapping.local.yaml --stage index
.venv/bin/community-view --config config.mapping.local.yaml benchmark --settings benchmark.mapping.local.yaml --stage ask
.venv/bin/community-view --config config.mapping.local.yaml benchmark --settings benchmark.mapping.local.yaml --stage judge
```

judge 不是筛选必需条件，可以单独运行。筛选只使用 history_results 指定的单个实验，逐条核对 graph_key、问题、外部 ID、run_id、成功状态及最终 assistant 答案。每个问题 ID 只允许一条成功 community 记录；失败题先续跑 ask。community-fallback 在结果中的 mode 也为 community，须通过对应数据库区分。

仅有 results.jsonl 不够，还需原数据库中匹配的 runs、question_communities 和 question_sources；没有记录映射的旧 QA 不能直接构建 view。不会跨实验选择最高分答案，gold 和评分不进入筛选或 view 内容。

### 6.3 筛选并原样物化历史答案

```bash
.venv/bin/community-view --config config.mapping.local.yaml knowledge-filter
```

LLM 接收社区信息、完整成员文档 overview、历史问题及 ID，只返回保留的 ID。完全或部分相关的问题保留，完全无关的问题筛掉；不改写、压缩、合并或回答问题。程序按原记录顺序保存问题和实际回答，再生成问题向量。非法 ID/重复 ID 等按 validation_retries 反馈修正。

每社区一个逻辑 view，不设字符上限。沿用 knowledge_views、knowledge_answers 表，无需数据库结构迁移；来源信息保留 run_id 和外部问题 ID。

全部社区的筛选及 embedding 成功后，事务替换当前图版本的整批 view，清除本批未覆盖的旧 view。任何社区失败均不发布本批结果，保留原版本；重跑可复用成功任务。切回旧来源问题集时也会重新发布缓存任务。不同图版本的数据互不覆盖。

数据库同目录的 knowledge/filter_summary.json 保存 published、成功/失败数、候选/保留数量及 metrics.filter、metrics.embedding；filter_jobs.json 保存逐社区结果与来源。token 和阶段耗时包含筛选及问题 embedding，不包含答案重编译，因为没有该步骤。

### 6.4 复制索引，再跑 view 问答与评测

使用独立数据库及结果目录，目标必须尚不存在。复用操作不调用模型：

```bash
.venv/bin/python - <<'PY'
from community_view.config import Config
from community_view.experiments.config import BenchmarkConfig
from community_view.experiments.reuse import clone_index
source = BenchmarkConfig.load('benchmark.mapping.local.yaml')
target = BenchmarkConfig.load('benchmark.view.local.yaml')
config = Config.load('config.view.local.yaml')
clone_index(source.database, source.output_dir / 'execution.json', source.dataset_dir, target, config)
PY
.venv/bin/community-view --config config.view.local.yaml benchmark --settings benchmark.view.local.yaml --stage ask
.venv/bin/community-view --config config.view.local.yaml benchmark --settings benchmark.view.local.yaml --stage judge
```

新问题匹配 view 问题向量，取 question_k=3 个正相似度且余弦 ≥ min_question_similarity=0.2 的问题，再对所属社区去重，展示这些社区的完整问题目录。首轮不预置 chunks、社区 overview 或全部答案。read_view_answers(question_ids) 精确返回选定答案，单次最多 read_answer_limit=8 个，每个 QA 内已读答案去重。

**首轮只提供 read_view_answers，程序也拦截该轮的 search_chunks；第二轮起两工具均可用。**空目录仍遵循此限制，与服务器原实现一致；这不强制 Agent 必须读 view，也不保证空目录时自动进入第二轮。最后一轮仍要求直接回答。

关闭 use_compiled 后，不注入 view prompt/目录，不提供读取工具，也不限制首轮 search；普通三模式不变。view 目录匹配独立于 chunk 搜索，后续搜索仍使用原社区扩展和去重逻辑。

### 6.5 完整管线

先准备 mapping 索引，再创建 history.pipeline.local.yaml（路径相对于该文件）：

```yaml
mapping_config: config.mapping.local.yaml
mapping_settings: benchmark.mapping.local.yaml
view_config: config.view.local.yaml
view_settings: benchmark.view.local.yaml
stage_attempts: 3
stage_retry_delay_seconds: 30
```

```bash
.venv/bin/python scripts/run_history_view_benchmark.py --settings history.pipeline.local.yaml
```

执行 mapping ask → mapping judge → 筛选 → 复制索引 → view ask → view judge。每阶段有限重试；未完成则停止后续步骤，成功记录可复用。状态和各阶段日志保存到管线配置所在目录。两轮使用相同 QA 范围和 [community]，数据库及输出独立；这是已见问题复用实验，不等于独立测试集泛化。

### 6.6 兼容旧重编译流程

保留 knowledge --stage plan/compile/all 及 scripts/run_compiled_benchmark.py，供旧实验显式使用；它们会提炼问题并重新调用 Agent 回答。plan_prompt 仅用于此旧流程的问题提炼。答案编译直接复用普通问答的 agent.txt 和 question.txt，不设置或注入编译专用的额外 prompt。

两种生成方式共享 view 表，每个图版本/社区只有一份当前发布 view；对照实验必须使用独立数据库。旧 view 仍可读取，升级后应使用新问答输出目录，不直接续跑旧 execution.json。

## 7. 结果、指标和失败续跑

```text
实验 output_dir/
  selection.json              数据集、原文和所选 QA 的校验信息
  execution.json              QA 配置、签名、并发和统计口径版本，不含密钥值
  indexing_metrics.json       文档/社区入库阶段及总成本
  results.jsonl               每题答案、gold、状态、指标和 evaluation
  summary.json                按 mode 汇总的 QA 与评分指标
  judge_execution.json        judge 配置和 prompt
  traces/<run_id>.json        QA 完整消息及工具结果
  run.log                    API 失败、重试、缺失 usage 等日志
数据库同级 knowledge/
  plan_summary.json          提炼后的阶段快照
  compile_summary.json       编译后的阶段快照
  all_summary.json           使用 knowledge --stage all 时的汇总
  jobs.json                  当前编译任务状态及进度
  traces/<run_id>.json        逐提炼问题的编译 Agent trace
```

| 指标 | 当前计算口径 |
|---|---|
| 入库时间 | 文档阶段、社区阶段实际墙钟时间之和；不累加并发文档各自的时间 |
| 总 token | API 返回的生成总 token + embedding token；优先使用服务返回 total_tokens，否则用输入输出相加 |
| QA 时间 | 获取 QA 并发槽位后开始，包含工具、内部模型等待及重试，直到回答与 trace 保存；不含等待 QA 槽位或之后 judge 的时间 |
| 平均 QA 时间/token/轮次 | 仅成功 QA 的成功尝试指标之和 ÷ 成功 QA 数量 |
| 失败 QA | 指标为 `null`，保留错误与 trace；重跑从零计量，不累计之前失败的成本 |
| Agent 轮次 | 每次进入模型决策/回答循环算一轮，包含最终答案轮；同轮多个工具只算一轮，HTTP 重试不加轮次 |
| judge 平均评分 | `evaluation.accuracy`：有效评分之和 ÷ 有效评分题数，范围 0–4 |
| 汇报的 Accuracy | `evaluation.normalized_accuracy`：平均评分 ÷ 4，范围 0–1；不是严格的完全答对比例 |

QA 总 token 包含查询 embedding；使用 view 时还包括问题目录匹配的 embedding。编译生成问题向量计入编译阶段，judge 成本单列，不混入 QA。未完成/失败题不计入 QA 均值，但成功、失败数量单列；没有成功题时均值为 `null`、总 token 为 0。`completed_qa_count` 是已落盘题数，包含失败题。

失败或跳过的评分不按 0 分填入 Accuracy；汇报时必须同时查看 `scored/total/failed/skipped/pending`。judge 共用 QA 的生成模型和并发设置。成功问答与成功评分会跳过；QA 失败重跑只保留成功尝试指标，judge 同签名失败重试的成本仍累计。

入库和知识编译阶段仍累计失败后续跑的已知成本。编译快照的 `metrics.plan` 和 `metrics.compile` 分别记录两个阶段，最新 compile/all 汇总已经包含之前提炼成本：例如 plan=10,000、compile=90,000，总共是 100,000，不能再加旧 plan 文件中的 10,000。`wall_seconds` 是本次知识命令执行任务的墙钟时间；`metrics.*.elapsed_seconds` 是各社区对应任务的耗时累加，两者不可混用。

API 失败默认最多额外重试两次并写日志。未返回 usage 时不因此重试，token 记 0；这不是完整服务端账单。成功 QA 内部的 API 重试计入该次指标。格式校验修正请求也会消耗 token。强制终止进程可能丢失尚未落盘的在途统计。

配置、prompt、数据或知识版本变化后，使用新输出目录；旧累计 QA 成本口径也不能与新口径直接混合续跑。已有实验结果不会自动重算。各实验独立数据库，程序会拒绝索引中混入 prepared 语料以外的文档。

## 8. 工具、模块和验证

`search_chunks(query, search_mode, doc_ids)` 支持 vector、keyword、hybrid；`search_mode=null` 使用默认值，`doc_ids=null` 搜全库、空列表不返回 chunks。Agent 不能调用 `read_chunks`，仍可通过限定 doc_ids 的搜索获取正文。`ask --doc-ids ...` 的问题级范围与工具范围取交集；社区扩展不受其限制。

```bash
.venv/bin/community-view --config config.local.yaml search '检索词' --search-mode hybrid --doc-ids D0001 D0002
.venv/bin/community-view --config config.local.yaml inspect documents
.venv/bin/community-view --config config.local.yaml inspect communities
.venv/bin/community-view --config config.local.yaml inspect run --run-id RUN_ID
```

`inspect` 和普通 `ask/search` 使用主配置的 `storage.database`。查看某个实验时，要把该路径指向对应实验数据库。

| 模块 | 职责 |
|---|---|
| `config.py`、`credentials.py`、`llm.py` | 配置、独立密钥、HTTP 协议、请求并发和重试 |
| `text.py`、`pdf.py`、`overviews.py`、`ingest.py` | 文档解析、累计综合、切片和入库 |
| `graph.py`、`communities.py`、`community_split.py` | 加权边、递归 Leiden、LLM fallback |
| `retrieval.py`、`agent.py`、`models.py` | 检索扩展、工具循环、问题级上下文去重 |
| `historical_views.py`、`knowledge_store.py`、`knowledge_views.py` | 历史问答核对、筛选、view 发布和读取 |
| `knowledge.py` | 兼容旧问题提炼和答案重编译流程 |
| `store.py`、`metrics.py` | SQLite 与任务级统计 |
| `experiments/` | prepared 校验、阶段调度、索引复用、QA/评测和汇总 |
| `scripts/` | 分类别汇总、顺序队列、知识实验管线 |
| `prompts/` | 文档、社区、拆分、Agent、问题、judge 和知识相关指令 |

```bash
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts
```

`data/` 保存语料和实验数据，不纳入 Git。`docs/reports/` 保留本地实验报告并被 Git 忽略；系统和实验使用说明统一维护在本 README。
