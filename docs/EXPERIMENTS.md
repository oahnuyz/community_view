# 统一实验接口与统计口径

当前只完成接口实现、数据校验与离线测试，没有启动真实模型入库、92 题问答或在线评分。

## 数据输入与配置

所有实验读取同一 prepared 格式：`qa.jsonl`、`documents.jsonl`、`dataset_info.json` 和文档 manifest 指向的 corpus 文件。问题按 JSONL 原顺序读取，不对 ID 排序。不把 gold answer、evidence 或标注的 document_ids 传给 Agent，不按每题参考文档限制检索范围。

`benchmark.yaml` 参数（均有注释）：

| 参数 | 用途 |
|---|---|
| dataset_dir | prepared 数据集目录 |
| output_dir | 当前实验独立输出目录 |
| database | 当前实验独立 SQLite 索引，拒绝混入其他语料 |
| log_file | 当前实验日志，含 API 重试及缺失 usage 警告 |
| start | 从 0 开始的 QA 偏移 |
| count | 选取题数；null 表示从 start 到末尾，超出实际题数报错 |
| modes | naive、community 或两者；共用该实验索引 |
| concurrency | 问答/LLM 评分共用并发数；默认 2，阶段内所有模式合计受此限制 |

模型和检索参数仍由主配置 `--config` 提供。两个密钥只放在 `api_keys.yaml`，由主配置的 `keys_file` 指定路径，不写入实验配置快照。`model.concurrency`、`embedding.concurrency` 分别控制模型请求并发，与 QA 并发是不同层面的限制。

```sh
.venv/bin/community-wiki --config config.local.yaml benchmark --settings benchmark.yaml --stage prepare
.venv/bin/community-wiki --config config.local.yaml benchmark --settings benchmark.yaml --stage index
.venv/bin/community-wiki --config config.local.yaml benchmark --settings benchmark.yaml --stage ask
.venv/bin/community-wiki --config config.local.yaml benchmark --settings benchmark.yaml --stage judge
```

- prepare：验证样本、文档哈希、选择范围；只生成清单，不调用模型。
- ingest：只执行文档 overview、原文切片和 embedding 保存，不生成社区。
- cluster：只执行文档建图、社区拆分、社区 name/overview 生成；要求文档入库已完成，不重新生成文档 overview 或 embedding。
- index：连续执行 ingest，并在包含 community 模式时执行 cluster。
- ask：在已完成索引上执行 QA；索引缺失、内容或配置不一致时明确拒绝。run 是 ask 的兼容别名。
- judge：只读取已保存的 QA 回答并评分，不打开索引、不要求 embedding 密钥、不重新问答。
- all：依次 index → ask → judge。

换数据集时复制实验 YAML，修改 dataset_dir、output_dir、database、log_file，以及需要的 start/count。不要在不同数据集之间复用同一个数据库或结果目录。实验目录有进程锁，避免同时运行两个进程重复请求、覆盖结果。

## 统计定义

### 入库

`indexing_metrics.json` 保存：

- `elapsed_seconds`：文档阶段与社区阶段各自实际墙钟时间之和，不将并发文档耗时相加。两个阶段分开执行时，不包含两次命令之间的人工等待；数据集同步、prepare 校验、依赖初始化不属于此时长。
- `llm_input_tokens`、`llm_output_tokens`、`llm_total_tokens`：文档阶段综合、最终 overview 和社区描述等所有生成请求消耗。
- `embedding_tokens`：文档 overview 和 chunks 的全部 embedding 消耗。
- `total_tokens = llm_total_tokens + embedding_tokens`。
- `status` 与 `document_count`，以及 `stages.documents`、`stages.communities` 的分阶段耗时/token。

格式修正产生的新调用计入消耗。失败后续跑时，累计实际执行时间和已知 token，不计两次执行之间的停顿。不输出缓存命中率、命中次数等缓存统计。

### 每题 QA

开始计时的位置是获取 QA 并发槽位之后，结束于最终回答/失败状态及 trace 已记录时。包含所有 Agent 轮次、工具、检索、query embedding、请求内部并发等待和重试等待；不含排队等待 QA 槽位的时间。汇总文件的写入开销不计为回答时间。

每题存 `elapsed_seconds`、`llm_input_tokens`、`llm_output_tokens`、`llm_total_tokens`、`embedding_tokens`、`total_tokens`、`rounds`。上下文在后续轮次再次发送时，按服务返回的 usage 再次计数。

**平均 QA 时间 = 各 QA 的实际耗时之和 / 已执行 QA 数量**；完整运行后分母为所选题数（本次为 92）。平均 token 和平均轮次使用同样分母。失败题也计入已执行数量及实际消耗，并单列成功/失败数量，不把失败题当作成功回答。

`rounds` 是实际进入的 Agent 模型调用轮数，包含最终答案轮和最终失败轮；HTTP 请求重试不增加 Agent 轮数。一轮可按 `agent.tool_concurrency` 并发执行多个工具，全部完成并按调用顺序回填后才进入下一轮；工具子任务继承本题的 token 统计作用域。

中断后重跑会跳过成功题；失败题可重新执行，其实际耗时、token、轮次累计到同一题，同时保留旧尝试的 trace 引用。既不会重复增加 QA 分母，也不会丢失失败尝试的实际成本。

### usage 与重试

API 请求失败（HTTP 错误、网络错误或非 JSON 响应）最多额外重试 2 次，即最多 3 次尝试。每次失败明确记录作用域、用途、尝试次数、错误类别和是否继续重试，不记录认证头。

成功响应缺失 usage 时，不重试，日志写明 `Missing usage ... tokens=0; continuing without retry`，本次 token 按 0 统计并继续。失败响应若有可用 usage 则计入，未提供则为 0。不通过本地 tokenizer 估算消耗。服务返回的 cached/reasoning 子项不再叠加到总数中。

任务作用域使用 ContextVar：入库并发子任务共享入库累加器，每题 QA 有独立累加器。不会用全局计数器前后差值推算单题消耗，因此并发 QA 的 embedding 消耗也不会串题。

## 每题初始 prompt

模板位于 `prompts/question.txt`，按用户指定原文：

```text
Answer this question as briefly as possible. Use only the information in the context.Do not use any external source.

Question: {question}
```

系统指令继续规定工具使用和检索行为。这里只替换初始用户消息中的问题占位符，不附加参考答案。

## 结果组织

```text
output_dir/
├── selection.json          # 数据集、文档及选中 QA 清单
├── execution.json          # 模型/检索配置、prompt 指纹、QA 并发数
├── indexing_metrics.json   # 入库总耗时和 token 汇总
├── results.jsonl           # 每题回答 + gold + 状态 + 单题指标 + evaluation 评分
├── traces/<run_id>.json     # 每个 QA 的完整 Agent 可见对话
├── judge_execution.json    # 评分 prompt 和共用模型配置（无密钥值）
├── summary.json            # QA 均值、评分均值、归一化分数及完成情况
├── index.sqlite3           # 默认数据库位置
└── run.log                 # 失败、重试、usage 缺失等运行日志
```

`results.jsonl` 每个 QA/模式一行，评分完成后在同一行追加 evaluation，不另建一份评分结果表。基础字段包含 `id, mode, question, gold_answers, answer, status, run_id, trace_file` 和全部单题指标。`answer` 是模型真实最终输出，不做二次概括。失败题 answer 为 null，附 error；重新执行的失败题还带 prior_attempts。结果按 QA 文件顺序原子保存，实际并发完成顺序不影响输出顺序。

trace 保存系统/初始用户消息、每轮 assistant 消息与原生工具调用、对应工具结果及最终回答；可看到实际被加入上下文的 chunks、社区和文档 overview。它不包含逐 API 请求 usage、归属、耗时明细。日志和 SQLite 也不再新增逐请求明细记录。

## LLM-as-judge 评分轮

评分使用用户提供的完整英文 prompt，保存于 `prompts/judge.txt`。每条请求仅包含该条 QA 的 question、系统实际生成的 answer、以及用 ` | ` 连接的 gold_answers。没有 Agent loop、工具或检索，返回严格 JSON：`{"score": 0..4, "reasoning": "..."}`。score 必须为整数，拒绝字符串、布尔值、小数、越界值和空白理由。

评分与问答共用 `model` 的服务、模型、密钥、温度、结构化输出与 HTTP 重试配置；生成请求不传输出 token 上限，使用 API 服务端默认值；并发使用实验 `concurrency`。若已有 QA 执行配置，单独评分会检查模型设置、并发与当时 QA 一致，避免无意混用。评分格式校验失败最多修正 `model.retries` 次；缺失 usage 仍按 0 统计并继续，不因 usage 缺失重试。

每题的 `evaluation` 包含：

- status：complete / failed / skipped；只有 complete 才有有效分数。
- score：0–4 整数；normalized_score：score/4；reasoning：模型评分理由。
- 评分耗时与生成 token 汇总。这些值不增加 QA 的 elapsed_seconds、total_tokens 或 rounds。

summary 中按模式保存 `evaluation.accuracy = 有效评分之和 / 有效评分题数`；`normalized_accuracy = accuracy / 4`，范围为 0–1。例如两题 4 分、2 分，accuracy=3，normalized_accuracy=0.75。这是 rubric 平均分及归一化值，不是“答对题数占比”。

完整评完 92 题时，分母为 92。若部分评分失败，均值暂按已成功评分的题计算，同时明确记录 scored/total/failed/skipped/pending，不能把部分均值当作完整实验结果；没有有效分数时两项均为 null。评分请求失败不伪造 0 分。问答失败、没有非空实际回答、gold 无效的题标记 skipped；缺少 QA 结果记录则要求先完成 ask。

重复运行 judge 会跳过同一 prompt/设置/回答下已成功评分的题，只重试失败评分；更改评分 prompt 或回答后会重新评分相应记录。只修改评分 prompt 不会导致重新入库或问答。成功问答仍按原有机制跳过，保持模型真实输出不变。

单独执行各阶段：

```sh
.venv/bin/community-wiki --config config.local.yaml benchmark --settings benchmark.yaml --stage ingest
.venv/bin/community-wiki --config config.local.yaml benchmark --settings benchmark.yaml --stage cluster
.venv/bin/community-wiki --config config.local.yaml benchmark --settings benchmark.yaml --stage ask
.venv/bin/community-wiki --config config.local.yaml benchmark --settings benchmark.yaml --stage judge
```

一次执行全部阶段：

```sh
.venv/bin/community-wiki --config config.local.yaml benchmark --settings benchmark.yaml --stage all
```

## 模块

- `experiments/config.py`：统一实验配置。
- `experiments/dataset.py`：prepared 输入、选择、哈希验证与索引一致性检查。
- `experiments/runner.py`：统一阶段调度、QA 并发、续跑和 Agent trace。
- `experiments/indexing.py`：可拆分的文档/社区入库轮及成本汇总。
- `experiments/judge.py`：并发 LLM 评分、格式校验、评分续跑。
- `experiments/results.py`：统一结果持久化及 QA/评分汇总。
- `metrics.py`：任务级 token 和轮次累加。
- `credentials.py`：独立密钥文件读取。
- `llm.py`：API 最多两次重试、缺失 usage 记零并继续。

## ScholarQA-Multi 清理记录

服务器 raw/prepared 的 QA 文件均已删除 `bohao_cs_1` 至 `bohao_cs_9`。prepared QA 和 raw 筛选文件由 101 条变成 92 条；两份 raw 未筛选源文件由 108 条变成 99 条，仍保留原先已排除的 7 条无效 QA。目录和文件原名中的 101 保留，避免破坏既有路径；实际数量以内容和 dataset_info 为准。

413 篇文档仍全部由前 92 题引用；没有删除文档。文档元数据中的已删除 QA 关联及 dataset_info 也已同步更新，本机 prepared 副本已同步。修改前备份位于服务器 `backups/scholarqa-before-trim-20260920T120029Z.tar.gz`。
