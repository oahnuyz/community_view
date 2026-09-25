# community_view

以整篇文档为图节点的 RAG 系统。先生成文档 overview、原文切片和向量，再对文档图进行层次社区聚类。问答使用 Agent loop，通过原文搜索和社区信息逐步获取证据；可选地把历史问题编译成社区问答 view，供后续按需读取。

项目使用 Python 3.12+、SQLite、本地精确向量检索、BM25、Leiden 和兼容 Chat Completions 的模型服务，无需单独部署向量数据库。生成、embedding 和 judge 均调用外部 API。

## 1. 系统流程

1. **文档入库**：读取 TXT、Markdown、PDF，为每篇文档生成 `title / keywords / summary`。不同文档并发；长文档按 token 分片，同篇逐片传入前文综合信息，最后生成全文 overview，不静默截掉后半篇。
2. **切片与向量**：原文按 token 切片，每片保存 `doc_id / ordinal / text / vector`；文档 overview 也有一份向量。新文档使用 `D0001` 等短 ID，chunk 编号从 0 开始。
3. **建图**：用文档向量、关键词或混合相似度寻找近邻，保存通过候选筛选和权重阈值的全部文档边。
4. **社区构建**：在全图运行 Leiden，超过 `max_documents` 的社区继续在诱导子图中尝试拆分。所有社区保存层次、父子关系、成员文档及 LLM 生成的 name/overview；当前 main 的检索只使用叶社区。
5. **Agent 问答**：每题拥有独立消息历史和去重状态。普通问答仅提供 `search_chunks`，可按 `doc_ids` 定向搜索正文。同一轮独立工具调用可并发执行。
6. **可选知识编译**：记录历史问题展示过的叶社区，筛选、压缩、去重相关问题，逐题运行 Agent 生成答案。后续问答先匹配问题目录，再通过 `read_view_answers` 读取选定答案。
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
| 生成 API / 模型 | `http://127.0.0.1:18080/v1` / `deepseek-v4-flash` |
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
| view 匹配 / 读取 | `question_k=5`，`min_question_similarity=0.0`，一次最多读取 8 个答案 |

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
| `knowledge.concurrency` | 3 | 同时提炼或编译的社区数；一个社区内逐题串行编译 |
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

## 6. compile 实验：映射 → 提炼 → 编译 → 问答 → 评测

compile 是叠加在检索之上的可选能力，不是第三个 `retrieval.mode`。可配合普通 community 或 community_fallback 使用，取决于选用哪份社区索引。

两个独立开关：

| 配置 | 作用 |
|---|---|
| `knowledge.record_questions` | 记录外部问题与实际展示过的叶社区；展示过 view 问题目录的社区也计入，不代表已验证有帮助 |
| `knowledge.use_compiled` | 初始问题向量匹配 view 问题目录，并启用 `read_view_answers` 和对应说明 |

记录映射不需要启用新知识。编译内部问答自动关闭这两个开关，避免递归读取自身答案或污染历史问题。提炼只接收问题文本与来源 ID，不接收 gold 或历史生成答案。

### 6.1 准备两份主配置、两份实验配置

在根目录复制完整配置，再编辑对应字段；下面列的是编辑项，不是可替代完整配置的最小文件。

```bash
cp config.local.yaml config.mapping.local.yaml
cp config.local.yaml config.compiled.local.yaml
cp benchmark.example.yaml benchmark.mapping.local.yaml
cp benchmark.example.yaml benchmark.compiled.local.yaml
```

| 编辑项 | mapping：记录与编译 | compiled：新知识问答 |
|---|---|---|
| 主配置 `storage.database` | `data/runs/my_dataset_mapping/index.sqlite3` | `data/runs/my_dataset_compiled/index.sqlite3` |
| 主配置 `storage.log_file` | `data/runs/my_dataset_mapping/run.log` | `data/runs/my_dataset_compiled/run.log` |
| `knowledge.record_questions` | `true` | `false` |
| `knowledge.use_compiled` | `false` | `true` |
| 实验 `output_dir` | `data/runs/my_dataset_mapping` | `data/runs/my_dataset_compiled` |
| 实验 `database` / `log_file` | 与对应主配置的 storage 一致 | 与对应主配置的 storage 一致 |
| 实验 `modes` | `[community]` | `[community]` |

两套配置的服务、embedding、文档处理、建图及社区设置保持一致。使用 fallback 社区时，两边的 `community.llm_split_fallback` 都设为 `true`。以下流程使用同一数据集、QA 范围和模式，测试的是已见问题的知识复用；不等于独立测试集上的泛化评测。

普通 `benchmark` 使用实验 YAML 的数据库路径覆盖主配置 storage；独立 `knowledge` 命令直接使用主配置 storage，**所以 mapping 两个路径必须一致**。

### 6.2 记录问题与叶社区映射

先准备 mapping 索引：

```bash
.venv/bin/community-view --config config.mapping.local.yaml benchmark --settings benchmark.mapping.local.yaml --stage index
```

然后只跑一次问答，不必评分：

```bash
.venv/bin/community-view --config config.mapping.local.yaml benchmark --settings benchmark.mapping.local.yaml --stage ask
```

若已有同一图版本下的成功问题映射，可直接进入提炼。未启用记录时跑过的 QA 不会自动追溯生成映射；不要在同一实验目录中途修改开关后混合续跑，应另建记录实验。

### 6.3 提炼问题集

```bash
.venv/bin/community-view --config config.mapping.local.yaml knowledge --stage plan
```

LLM 根据社区及成员文档 overview，对历史问题进行相关性筛选、压缩和去重，输出问题及对应的原问题 ID 集合。不要求所有历史问题都相关；无相关问题可以返回空列表。非法格式、重复问题或未知来源 ID 会反馈错误并按 `knowledge.validation_retries` 修正。

### 6.4 逐题编译答案

```bash
.venv/bin/community-view --config config.mapping.local.yaml knowledge --stage compile
```

每个提炼问题启动独立 Agent loop，使用当前社区与成员文档 overview 作为初始上下文，复用 `prompts/agent.txt` 和 `prompts/question.txt`，可搜索全库正文。不同社区按 `knowledge.concurrency` 并发，社区内逐题执行；成功答案可以断点复用。

一个社区一个逻辑 view，不设字符上限。`knowledge_answers` 保存问题、答案、原问题映射和问题向量；`knowledge_views` 保存社区名称、embedding 配置签名及发布版本。完整社区 view 以事务发布，失败替换不会覆盖上次完整结果。`knowledge --stage all` 只连续执行 plan 和 compile，不包含问答与评测。

### 6.5 复制已编译索引，再运行新知识问答和评测

compiled 使用独立数据库和结果目录。可以用项目的索引复用接口复制 mapping 索引及 view，要求目标数据库和执行记录尚不存在；以下代码不调用模型：

```bash
.venv/bin/python - <<'PY'
from community_view.config import Config
from community_view.experiments.config import BenchmarkConfig
from community_view.experiments.reuse import clone_index
source = BenchmarkConfig.load('benchmark.mapping.local.yaml')
target = BenchmarkConfig.load('benchmark.compiled.local.yaml')
config = Config.load('config.compiled.local.yaml')
clone_index(source.database, source.output_dir / 'execution.json', source.dataset_dir, target, config)
PY
.venv/bin/community-view --config config.compiled.local.yaml benchmark --settings benchmark.compiled.local.yaml --stage ask
.venv/bin/community-view --config config.compiled.local.yaml benchmark --settings benchmark.compiled.local.yaml --stage judge
```

新问答首先将原问题与提炼问题向量匹配，取 `question_k` 个符合 `min_question_similarity` 的问题，再按社区去重。Agent 获得这些社区的完整问题目录，**不会直接获得全部答案**。它通过 `read_view_answers(question_ids)` 选择答案；每题已读答案去重，其他缺口可用 `search_chunks` 获取原文。当前允许同一轮同时读 view 和搜索，没有强制先读后搜。

关闭 `use_compiled` 时，不注入任何 view 说明或目录，也不提供 `read_view_answers`。普通社区检索的关联边扩展仍保持原样，但 view 目录是按提炼问题相似度独立选出的，不依赖 chunk 命中文档的所属社区。

### 6.6 一次性运行知识实验管线

先完成 mapping 的 `index`，再在 `data/pipelines/my_compile/pipeline.yaml` 放置以下配置（路径相对该文件）：

```yaml
mapping_config: ../../../config.mapping.local.yaml
mapping_settings: ../../../benchmark.mapping.local.yaml
compiled_config: ../../../config.compiled.local.yaml
compiled_settings: ../../../benchmark.compiled.local.yaml
```

```bash
.venv/bin/python scripts/run_compiled_benchmark.py --settings data/pipelines/my_compile/pipeline.yaml
```

该入口串联：**mapping ask → plan → compile → 复制索引 → compiled ask → judge**，不重新入库。若前面的 mapping QA 或编译已按相同配置完成，成功部分可复用。自动管线要求前后数据集、start/count 和 modes 一致；数据库和输出目录必须分开。

管线保存 `pipeline_status.json`。个别社区提炼/编译失败时会记录数量，仍可用已发布的知识继续问答，其他内容依靠原文搜索；这不代表所有社区都编译成功。源 view 改变后，管线拒绝继续使用旧的 compiled 副本，需要新的目标数据库及输出目录。

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
| `knowledge.py`、`knowledge_store.py`、`knowledge_views.py` | 问题提炼、答案编译、发布与读取 |
| `store.py`、`metrics.py` | SQLite 与任务级统计 |
| `experiments/` | prepared 校验、阶段调度、索引复用、QA/评测和汇总 |
| `scripts/` | 分类别汇总、顺序队列、知识实验管线 |
| `prompts/` | 文档、社区、拆分、Agent、问题、judge 和知识相关指令 |

```bash
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts
```

`data/` 保存语料和实验数据，不纳入 Git。`docs/reports/` 保留本地实验报告并被 Git 忽略；系统和实验使用说明统一维护在本 README。
