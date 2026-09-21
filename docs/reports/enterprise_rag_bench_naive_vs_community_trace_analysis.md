# EnterpriseRAGBench：naive 与 community 的逐题 trace 对比报告

分析日期：2026-09-21。离线分析已完成实验；未重新生成答案、检索、评分或修改原始实验结果。Δ 均为 community−naive。

## 1. 主要结论

净增仅 2 分（+0.625 个百分点），却增加约 27.7% QA token。强正例多体现审批/条件化回答的完整性，负例集中在规范权威、例外条件和完整清单；多个分差存在 judge 不对称。全库计数任务暴露 top-k 检索无法保证完整性，社区能提供候选文档，却不能替代去重的结构化统计。

共 80 题：评分上升 **11**、下降 **10**；iteration 上升 **7**、下降 **7**。两项任一变化的 **30** 题全部进入第 7 节，并附完整 gold、答案、judge 和工具时序；第 8 节覆盖全部题目。第 5 节对重点案例逐项核验机制，其余案例只陈述可验证的执行变化与原判分依据，不虚构模型内部思考，也不把未受控的对照当作因果证明。

## 2. 数据来源与比较口径

- 原实验目录（214）：`/home/ZhangYunhao/community_wiki/data/runs/enterprise_rag_bench_80_naive_community`。
- 本地核验副本：[results.jsonl](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/results.jsonl)、[分类汇总](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/summary_by_category.json)、[execution.json](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/execution.json)、[judge_execution.json](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/judge_execution.json)。
- 当前组 80 对问答及 judge 全部成功；按 QA ID 对齐并核对 question/gold 一致。两种模式共用同一实验数据库，文档与 chunk 索引相同；同题初始 system/user 消息全部一致。三组 PaperScope 复用同一批 93 篇 PDF，不能视为完全独立语料实验。
- 模型 `deepseek-v4-flash`，embedding `doubao-embedding-vision`，QA/judge 并发 5。实际模式以结果行与 trace 为准，不能仅凭配置默认 retrieval.mode 判断。
- 原始 score 是一次 LLM judge 的 0–4 分，normalized accuracy=均分/4，并非二元正确率。本文不改分，也不生成主观“校正准确率”。
- iteration/rounds 是模型调用次数，包含最终回答轮；一轮可并发多个工具，API 重试不直接增加 rounds。工具错误是 tool 消息中的 error，不等于整题失败。
- QA 时间为逐题端到端执行时长，token 包括 query embedding 与各轮 LLM，不含入库和 judge。工具结果字符数是序列化 JSON 的长度；overview/chunk 均每题内去重后再求和，不等同于相关证据数。
- 首轮整组工具请求相同 5/80；首个工具的有序 chunk ID 相同 14/80；两项同时相同 3/80。后续检索还会分叉。首轮不同不能归因于尚未注入的社区信息，temperature=0 不等于服务完全确定。
- 文档数 323，社区总数 78（叶社区 52）。实际共享入库 1571.40 秒、2,455,642 token；包含 Enterprise 入库失败及续跑的累计消耗。

## 3. 整体结果与变化矩阵

| 指标 | naive | community | 变化 |
|---|---|---|---|
| judge总分 | 264 | 266 | +2 |
| judge均分/4 | 3.3000 | 3.3250 | +0.0250 |
| 归一化accuracy（%） | 82.500 | 83.125 | +0.625 |
| 平均QA秒 | 19.13 | 24.82 | +5.69 |
| 平均QA token | 46,092.81 | 58,878.16 | +12,785.35 |
| 平均rounds | 2.5500 | 2.5625 | +0.0125 |
| 总rounds | 204 | 205 | +1 |
| 工具调用 | 230 | 255 | +25 |
| search_chunks | 202 | 198 | -4 |
| read_chunks | 28 | 57 | +29 |
| 工具错误 | 9 | 25 | +16 |
| 整轮全错误 | 3 | 4 | +1 |
| 逐题去重overview数之和 | 876 | 3,128 | +2,252 |
| 逐题去重chunk数之和 | 1,547 | 1,595 | +48 |
| 工具返回字符数 | 6,767,870 | 9,110,569 | +2,342,699 |
| 重复chunk返回次数 | 850 | 689 | -161 |

QA token 变化 **+27.74%**，平均 QA 时间变化 **+29.75%**。时间受请求长度、排队与服务状态影响，两个模式先后运行，不能只从时间差反推算法快慢。

| score变化 / rounds变化 | rounds减少 | rounds相同 | rounds增加 | 合计 |
|---|---|---|---|---|
| score上升 | 1 | 8 | 2 | 11 |
| score不变 | 4 | 50 | 5 | 59 |
| score下降 | 2 | 8 | 0 | 10 |
| 合计 | 7 | 66 | 7 | 80 |

搜索类型（按实际调用参数；default 表示使用配置默认）：

| 模式 | hybrid | vector | keyword | default |
|---|---|---|---|---|
| naive | 157 | 14 | 31 | 0 |
| community | 162 | 5 | 31 | 0 |

工具错误分类：

| 错误原文 | naive | community |
|---|---|---|
| Unknown chunk ordinal | 9 | 20 |
| 2 validation errors for ReadArguments<br>doc_id<br>  Field required [type=missing, input_value={'doc_ids': ['D0106'], 'ordinals': [0]}, input_type=dict]<br>    For further information visit https://errors.pydantic.dev/2.13/v/missing<br>doc_ids<br>  Extra inputs are not permitted [type=extra_forbidden, input_value=['D0106'], input_type=list]<br>    For further information visit https://errors.pydantic.dev/2.13/v/extra_forbidden | 0 | 1 |
| 2 validation errors for ReadArguments<br>doc_id<br>  Field required [type=missing, input_value={'doc_ids': ['D0244'], 'ordinals': [0]}, input_type=dict]<br>    For further information visit https://errors.pydantic.dev/2.13/v/missing<br>doc_ids<br>  Extra inputs are not permitted [type=extra_forbidden, input_value=['D0244'], input_type=list]<br>    For further information visit https://errors.pydantic.dev/2.13/v/extra_forbidden | 0 | 1 |
| 2 validation errors for ReadArguments<br>doc_id<br>  Field required [type=missing, input_value={'doc_ids': ['D0252', 'D0...0316'], 'ordinals': [0]}, input_type=dict]<br>    For further information visit https://errors.pydantic.dev/2.13/v/missing<br>doc_ids<br>  Extra inputs are not permitted [type=extra_forbidden, input_value=['D0252', 'D0253', 'D0267', 'D0286', 'D0316'], input_type=list]<br>    For further information visit https://errors.pydantic.dev/2.13/v/extra_forbidden | 0 | 1 |
| 2 validation errors for ReadArguments<br>doc_id<br>  Field required [type=missing, input_value={'doc_ids': ['D0231', 'D0260'], 'ordinals': [0]}, input_type=dict]<br>    For further information visit https://errors.pydantic.dev/2.13/v/missing<br>doc_ids<br>  Extra inputs are not permitted [type=extra_forbidden, input_value=['D0231', 'D0260'], input_type=list]<br>    For further information visit https://errors.pydantic.dev/2.13/v/extra_forbidden | 0 | 1 |
| Invalid number of chunk ordinals | 0 | 1 |

community 每题平均收到 39.10 份文档 overview；其中 0 题覆盖全部 323 篇文档。

## 4. 四类变化案例导航

**评分上升（11题）**：[enterprise_rag_bench:qst_0342](#case-enterprise_rag_bench-qst_0342)（+1）、[enterprise_rag_bench:qst_0344](#case-enterprise_rag_bench-qst_0344)（+2）、[enterprise_rag_bench:qst_0345](#case-enterprise_rag_bench-qst_0345)（+1）、[enterprise_rag_bench:qst_0352](#case-enterprise_rag_bench-qst_0352)（+2）、[enterprise_rag_bench:qst_0353](#case-enterprise_rag_bench-qst_0353)（+1）、[enterprise_rag_bench:qst_0366](#case-enterprise_rag_bench-qst_0366)（+1）、[enterprise_rag_bench:qst_0367](#case-enterprise_rag_bench-qst_0367)（+1）、[enterprise_rag_bench:qst_0369](#case-enterprise_rag_bench-qst_0369)（+1）、[enterprise_rag_bench:qst_0375](#case-enterprise_rag_bench-qst_0375)（+1）、[enterprise_rag_bench:qst_0427](#case-enterprise_rag_bench-qst_0427)（+1）、[enterprise_rag_bench:qst_0437](#case-enterprise_rag_bench-qst_0437)（+1）。

**评分下降（10题）**：[enterprise_rag_bench:qst_0343](#case-enterprise_rag_bench-qst_0343)（-1）、[enterprise_rag_bench:qst_0347](#case-enterprise_rag_bench-qst_0347)（-1）、[enterprise_rag_bench:qst_0351](#case-enterprise_rag_bench-qst_0351)（-1）、[enterprise_rag_bench:qst_0359](#case-enterprise_rag_bench-qst_0359)（-1）、[enterprise_rag_bench:qst_0362](#case-enterprise_rag_bench-qst_0362)（-1）、[enterprise_rag_bench:qst_0363](#case-enterprise_rag_bench-qst_0363)（-1）、[enterprise_rag_bench:qst_0373](#case-enterprise_rag_bench-qst_0373)（-1）、[enterprise_rag_bench:qst_0379](#case-enterprise_rag_bench-qst_0379)（-1）、[enterprise_rag_bench:qst_0422](#case-enterprise_rag_bench-qst_0422)（-2）、[enterprise_rag_bench:qst_0447](#case-enterprise_rag_bench-qst_0447)（-1）。

**iteration上升（7题）**：[enterprise_rag_bench:qst_0342](#case-enterprise_rag_bench-qst_0342)（+1）、[enterprise_rag_bench:qst_0345](#case-enterprise_rag_bench-qst_0345)（+1）、[enterprise_rag_bench:qst_0356](#case-enterprise_rag_bench-qst_0356)（+2）、[enterprise_rag_bench:qst_0434](#case-enterprise_rag_bench-qst_0434)（+1）、[enterprise_rag_bench:qst_0439](#case-enterprise_rag_bench-qst_0439)（+1）、[enterprise_rag_bench:qst_0445](#case-enterprise_rag_bench-qst_0445)（+2）、[enterprise_rag_bench:qst_0450](#case-enterprise_rag_bench-qst_0450)（+1）。

**iteration下降（7题）**：[enterprise_rag_bench:qst_0359](#case-enterprise_rag_bench-qst_0359)（-1）、[enterprise_rag_bench:qst_0362](#case-enterprise_rag_bench-qst_0362)（-1）、[enterprise_rag_bench:qst_0365](#case-enterprise_rag_bench-qst_0365)（-1）、[enterprise_rag_bench:qst_0432](#case-enterprise_rag_bench-qst_0432)（-2）、[enterprise_rag_bench:qst_0435](#case-enterprise_rag_bench-qst_0435)（-1）、[enterprise_rag_bench:qst_0437](#case-enterprise_rag_bench-qst_0437)（-1）、[enterprise_rag_bench:qst_0443](#case-enterprise_rag_bench-qst_0443)（-1）。

## 5. 重点机制与可核验证据

### enterprise_rag_bench:qst_0344：新增定向核验补齐服务积分审批流程

评分 2→4；rounds 3→3。

naive 最终提前下结论 “No SLO credits were warranted”，忽略必须按修正后的计量确认违约及审批。community 第 2 轮限定 D0024 检索 credit request，最终补出 SRE breach window→Product entitlement→Finance→Legal→CS 流程，2→4 分。注意 D0024 在 community 首轮已经以 chunk 及 overview 同时返回，不能称为纯社区 overview 独立发现后引导的证据；两边查询也不同。实际可确认的是检索路线转向政策原文且最终保留条件化审批，而不是把测量缺陷直接等同于无赔付资格。

完整对照：[enterprise_rag_bench:qst_0344](#case-enterprise_rag_bench-qst_0344)。

<details>
<summary>展开对应字段的原文节选</summary>

naive 的 overviews 中未找到该 doc_id 下的字面串 `approval`；这是指定字段的文本核对，不是全语料语义不存在证明。

naive 的 chunks 中未找到该 doc_id 下的字面串 `approval`；这是指定字段的文本核对，不是全语料语义不存在证明。

**community，第 1 轮第 1 次工具，overviews，doc_id=D0024：**

> oards, metrics, scope, mitigations. Includes warm-up, update cadence, templates, credit eligibility/approval, evidence logging, and failure modes.

**community，第 1 轮第 1 次工具，chunks，doc_id=D0024，ordinal=0：**

> s updates and written summaries.
> - Route service-credit / compensation requests through the correct approval path.
> 
> This page is **restricted** because it includes internal paging triggers and credit approval guidance.
> 
> ---
> 
> ## What is the Dedicated Throughput SLO (customer-facing summary)
> Dedicated Throughput SLO guarantees a **minimum sustained throughput floor** for an eligible Dedicated deployment und

</details>

### enterprise_rag_bench:qst_0352：相同关键证据已在两边，收益发生在答案采用环节

评分 2→4；rounds 2→2。

community 补写 Dedicated catalog/list-price fallback，2→4 分且同为 2 轮。但逐条查原文可见 naive 首轮已返回 D0322:2 的 catalog_fallback 日志、D0322:0 的 effective_token_price_usd 说明，甚至 D0322 overview 也清楚概括缺失有效价格导致回退。该关键事实并非社区独有。可以说 community 这次回答更完整，不能说“社区新增了 naive 没有检索到的价格回退证据”。这也是用 trace 检验 judge 理由后修正直觉归因的例子。

完整对照：[enterprise_rag_bench:qst_0352](#case-enterprise_rag_bench-qst_0352)。

<details>
<summary>展开对应字段的原文节选</summary>

naive 的 overviews 中未找到该 doc_id 下的字面串 `catalog_fallback`；这是指定字段的文本核对，不是全语料语义不存在证明。

**naive，第 1 轮第 1 次工具，chunks，doc_id=D0322，ordinal=2：**

> .
> 
> Chloe Martin: found it. In optimize-suggestions logs for arkadia-finance, price source = `catalog_fallback` for multiple suggestion computations:
> `price_source=catalog_fallback reason=missing_effective_price org=arkadia-finance project=prod-vpc model=rw-llama-3.1-70b-instruct`
> So yeah, we’re using list price.
> 
> Aditya Rao: ok that explains the $ inflation. % savings might still be directionally ok, but d

community 的 overviews 中未找到该 doc_id 下的字面串 `catalog_fallback`；这是指定字段的文本核对，不是全语料语义不存在证明。

**community，第 1 轮第 1 次工具，chunks，doc_id=D0322，ordinal=2：**

> .
> 
> Chloe Martin: found it. In optimize-suggestions logs for arkadia-finance, price source = `catalog_fallback` for multiple suggestion computations:
> `price_source=catalog_fallback reason=missing_effective_price org=arkadia-finance project=prod-vpc model=rw-llama-3.1-70b-instruct`
> So yeah, we’re using list price.
> 
> Aditya Rao: ok that explains the $ inflation. % savings might still be directionally ok, but d

</details>

### enterprise_rag_bench:qst_0356：顺序安排扩大轮次，质量没有增益

评分 4→4；rounds 3→5。

两边均满分、无工具错误。naive 首轮并行查事故和责任/SLO 目标，第 2 轮并行读取后回答；community 首轮仅查事故，随后读取、再查 taxonomy/TTM/TTF、再读取，3→5 轮，工具仅 4→5，token 48,407→133,313。轮次差主要来自检索与读取的串行组织，加上更宽 overview 历史。首轮规划发生在社区注入之前，因此不能说社区反馈导致了最初的串行安排。

完整对照：[enterprise_rag_bench:qst_0356](#case-enterprise_rag_bench-qst_0356)。

### enterprise_rag_bench:qst_0359：规范与实现冲突没有形成稳定的权威优先级

评分 3→2；rounds 4→3。

两边都拿到 ADR-022 以及 gateway/PM 变体。naive 虽有一次越界读取，最终仍以 canonical subcode 契约给出分支建议；community 少一轮、无工具错误，却认为 subcode 不可协调并要求 SDK 不依赖它，3→2 分。这里的失分是规范/实现/需求稿之间的冲突裁决，不是缺少 error.code 文档。更完整的社区材料可能同时引入更多版本，但 trace 不能证明这些额外材料单独导致错误。检索后需明确权威、状态和适用版本，再将兼容处理与规范要求区分。

完整对照：[enterprise_rag_bench:qst_0359](#case-enterprise_rag_bench-qst_0359)。

### enterprise_rag_bench:qst_0422：保留期限与 Legal Hold 例外的表述边界

评分 4→2；rounds 2→2。

naive 明确先说 exports cannot retrieve older records，再说明 Legal Hold 例外；community 直接说 exports access older records via Legal Hold。两边均提及 legal_hold_id、启用租户、审计记录与废弃 super-admin override，judge 却给 4→2。gold 本身同时包含“不能超期导出”和“超期检索需要 Legal Hold”两层表述，必须澄清 export 与 retrieval 的语义边界。本例不能据 −2 直接认定社区检索出了错误事实；它更接近条件化措辞的差异及评分对边界的敏感性。

完整对照：[enterprise_rag_bench:qst_0422](#case-enterprise_rag_bench-qst_0422)。

### enterprise_rag_bench:qst_0427：核心答案相同、共同遗漏 invoice-line 要求

评分 3→4；rounds 2→2。

两份答案都给出 lowercase SHA-256、PO_NUMBER|PO_LINE_UUID、Tuesday 07:00 PT，均未明确写 included on each invoice line。naive judge 因该遗漏给 3，community judge 给 4。这是明显的复评分优先案例，不能作为社区让政策更新判断更准确的证据。工具数 2→1、轮次不变，查询首轮合并是执行路线差异，发生在读取社区结果之前。

完整对照：[enterprise_rag_bench:qst_0427](#case-enterprise_rag_bench-qst_0427)。

### enterprise_rag_bench:qst_0437：全库计数不可靠；省轮掩盖更多工具和错误

评分 2→3；rounds 6→5。

两边都答 Platform，但估计的总数分别约 20 和约 23，而 gold 为 16。judge 将前者判 2、后者判 3，不能把更偏离数值的后者视为可靠准确率提升。community 虽从 6→5 轮，却由 9→17 次工具，并出现 5 次越界 read_chunks；后续用 doc_ids 限定搜索挽回读取。原始 top-k 检索加文本综合没有形成完整、去重的 action-item 账本，适合用于定位材料，不足以保证跨所有 postmortem 的精确计数。

完整对照：[enterprise_rag_bench:qst_0437](#case-enterprise_rag_bench-qst_0437)。

### enterprise_rag_bench:qst_0445：概览暴露更多短文档，试读失败仍未补齐发布计划

评分 2→2；rounds 3→5。

community 为 5 轮、10 次工具、5 次读取错误；naive 为 3 轮、4 次工具、1 次错误；两边均为 2 分。community 最后一个工具轮只有越界读取，额外尝试没有补齐 Private maintenance window、data residency、精确 SLO thresholds 等缺项。可见问题是从概览拿到 doc_id 后不知道合法 chunk 范围，以及缺少“生产发布计划”的必填要素检查。不能把五个错误直接等价为五轮，因为同轮可以并发多个调用。

完整对照：[enterprise_rag_bench:qst_0445](#case-enterprise_rag_bench-qst_0445)。

## 6. 改进优先级（建议，未修改系统）

1. 把规范文档、实现状态、过时草案、客户特例分开比较，再生成带条件的操作结论。
2. 计数/完整枚举题先建立可核验的候选文档/事件清单，再用程序去重计数；这是未来工具方向，不等于立即恢复已删除的 find_documents。
3. 读取工具告知有效 ordinal 范围与单次数量上限；对短 TXT 的越界读取优先修复。
4. 盲化复核 422/427/437；尤其不要把同样遗漏或更错误的计数被给高分当成社区增益。

## 7. 全部变化案例：诊断、工具时序与完整回答

每例先列观察到的执行变化；重点案例另有人工对照说明。judge reasoning 保留原文，是评分器的解释而非外部事实裁决。下方引用的答案/gold 不截断；原始工具全文由 trace 链接提供。

<a id="case-enterprise_rag_bench-qst_0342"></a>

### enterprise_rag_bench:qst_0342 — 评分与执行路径对照

**问题：** Our Key Management Standard says we must not cache plaintext DEKs, but ADR-007 allows a short-lived in-memory DEK cache. What is the actual policy we should follow, and how should we describe DEK caching and KMS outage behavior in customer-facing rotation materials?

**score：3→4（Δ+1）；rounds：2→3（Δ+1）。**

工具安排：naive 为第1轮2次；community 为第1轮2次、第2轮1次。最终回答另占一轮。

轮次增加 1，工具总数 2→3、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 17→17、文档 overview 6→23；工具结果字符数 70,635→97,584，QA token 20,974→50,324。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

<details>
<summary>展开 judge 所提实体的字面证据核对</summary>

| 实体/术语 | naive工具中首次匹配 | naive答案 | community工具中首次匹配 | community答案 |
|---|---|---|---|---|
| KMS | 轮1/调用1/D0151:0 | 出现 | 轮1/调用1/D0014:0 | 出现 |
| DEK | 轮1/调用1/D0151:0 | 出现 | 轮1/调用1/D0014:0 | 出现 |

这里只检查指定字面串及字母数字边界，不评判上下文是否在讨论同一事实；未匹配不排除同义表述，出现也不代表正确采用。它用于区分“可能未召回”和“已出现但未展开”的复核入口，不能自动判定因果。

</details>

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/295fa1bcef654429b31049bb7a16841f.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/0dc4691a29024319b493df6e2e519fb4.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Key Management Standard must not cache plaintext DEKs","search_mode":"hybrid","doc_ids":null} | 12 | 5 | 0 | 成功 | D0151:0, D0014:0, D0151:4, D0014:3, D0151:2, D0151:1, D0151:6, D0014:4, D0204:0, D0014:1, D0152:0, D0158:3 |
| 2 | 1 | search_chunks {"query":"ADR-007 short-lived in-memory DEK cache KMS outage","search_mode":"hybrid","doc_ids":null} | 12 | 1 | 0 | 成功 | D0014:0, D0009:0, D0014:3, D0151:0, D0204:0, D0014:6, D0151:1, D0204:2, D0151:6, D0009:4, D0151:4, D0204:1 |

judge reasoning：

> The generated answer accurately and thoroughly captures the policy and KMS outage behavior, but omits the specific rotation-related requirements about dual-decrypt/rollback and bounded fallback for key-mismatch/InvalidCiphertext cases.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"cache plaintext DEK in-memory short-lived ADR-007","search_mode":"hybrid","doc_ids":null} | 12 | 23 | 3 | 成功 | D0014:0, D0014:3, D0151:0, D0009:0, D0151:1, D0014:6, D0204:0, D0009:4, D0014:4, D0158:3, D0152:0, D0151:4 |
| 2 | 1 | search_chunks {"query":"Key Management Standard must not cache plaintext DEK","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0151:0, D0014:0, D0014:3, D0151:1, D0151:4, D0151:2, D0009:0, D0151:6, D0014:1, D0152:0, D0014:4, D0158:3 |
| 3 | 2 | read_chunks {"doc_id":"D0204","ordinals":[1,2]} | 2 | 0 | 0 | 成功 | D0204:1, D0204:2 |

judge reasoning：

> The generated answer accurately and comprehensively captures the gold answer's core policy, ADR-007 constraints, approved customer-facing language for DEK caching and KMS outage behavior, and non-disclosure requirements, with only acceptable additional detail.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Follow the Key Management Standard's intent: never persist or long-term cache plaintext DEKs. The only permitted "cache" is the ADR-007 constrained optimization: short-lived, in-process-only reuse of plaintext DEKs that are already in memory for request handling (bounded TTL/size, no disk/DB/distributed cache, disable-able in regulated environments). In customer-facing rotation/outage materials, describe it as: Redwood uses envelope encryption; DEKs are wrapped by the customer's KEK in KMS/HSM; Redwood may retain short-lived in-memory cryptographic material for active workloads but does not rely on indefinite caching of KMS responses. If KMS is unavailable/degraded, operations that require wrap/unwrap may fail fast with explicit errors; Redwood uses timeouts, bounded retries with backoff/jitter, circuit breaker/backpressure to prevent retry storms. Do not promise continued decrypt during a KMS outage or disclose exact timeout/retry/breaker thresholds. During rotation, mention dual-decrypt/rollback, and that we do not fan out across keys on timeout/throttling-only bounded fallback for key-mismatch/InvalidCiphertext-type cases.

**naive 最终答案**

> ## Actual policy
> 
> The two documents reconcile as follows:
> 
> - **Key Management Standard** is the strict baseline: **MUST NOT cache plaintext DEKs** — i.e., no persisted, distributed, or long-lived caching; discard the plaintext DEK from memory as soon as possible.
> - **ADR-007** (the approved, more specific implementation the Standard mandates via the shared wrapper) narrows this with an **exception for short-lived in-memory DEK/plaintext key material** under strict constraints:
>   - TTL default **5 minutes** (configurable downwards); never >15 min without a security exception
>   - Bounded (default 10,000 entries, LRU eviction)
>   - **In-process only** — never persisted to disk/database/distributed cache, never shared cross-host
>   - Cache keys must be hashed (no raw customer identifiers)
>   - Must be **disable-able via config in regulated environments**
> 
> So the actual policy: **plaintext DEKs may be cached only in short-lived process memory (≤5 min, bounded, in-process, never persisted, disable-able); any other plaintext DEK caching is prohibited.** The Standard's "MUST NOT cache plaintext DEKs" targets persistent/long-lived caching; ADR-007 defines the permitted short-lived in-memory form.
> 
> ## Customer-facing rotation materials
> 
> **DEK caching ("Do you cache DEKs?"):**
> - Redwood uses envelope encryption: data is encrypted with a DEK wrapped by a customer-managed KEK in the customer's KMS/HSM.
> - For active workloads, Redwood **may retain short-lived in-memory cryptographic material** to serve requests efficiently (e.g., within a process lifetime), but **does not rely on indefinite caching of KMS responses**.
> - Don't claim we can always decrypt during an outage.
> 
> **KMS outage behavior:**
> - Treat customer KMS as a critical dependency.
> - When KMS degrades, Redwood applies guardrails (timeouts, bounded retries with backoff/jitter, circuit breaker/backpressure) to prevent retry amplification and request storms.
> - If KMS is unavailable for an operation requiring key unwrapping, Redwood **fails fast and returns explicit errors** rather than silently degrading or risking corruption.
> - **Do not disclose** exact timeout values, retry counts, or circuit-breaker thresholds externally.

**community 最终答案**

> **Actual policy (reconciliation):** ADR-007 (published, and the Key Management Standard mandates its wrapper) governs. Plaintext DEKs may be cached **only as short-lived, in-process, in-memory key material**: TTL default 5 minutes (configurable downwards), bounded max entries (default 10,000, LRU), never persisted or shared cross-host, hashed cache keys (no raw customer identifiers), and disable-able via config in regulated environments. What's prohibited is **persisting** plaintext DEKs (disk/DB/distributed cache) or long-lived plaintext caches (>15 min without a security exception) — and metadata caching must respect rotation safeguards (bounded TTL, invalidation on cutover). So the standard's "MUST NOT cache plaintext DEKs" applies to persistent/long-lived caching, not the restricted in-memory cache ADR-007 permits.
> 
> **Customer-facing rotation materials (approved language):**
> - DEK caching: "Redwood uses envelope encryption; data is encrypted with a DEK wrapped by a customer-managed KEK in your KMS/HSM. For active workloads, Redwood may retain short-lived in-memory cryptographic material to serve requests efficiently (e.g., within a process lifetime), but does not rely on indefinite caching of KMS responses."
> - KMS outage: "Redwood treats customer KMS as a critical dependency. When KMS degrades, Redwood applies guardrails (timeouts, bounded retries with backoff/jitter, circuit breaker/backpressure) to prevent retry amplification and request storms. If KMS is unavailable for an operation requiring key unwrapping, Redwood may be unable to unwrap DEKs and fails fast with explicit errors rather than risking silent corruption."
> - Rotation: designed to be reversible (rollback during the cutover window), with a dual-decrypt window.
> - Do **not** disclose: exact timeout values, retry counts, circuit-breaker thresholds, or anything implying Redwood can always decrypt during a KMS outage.

</details>

<a id="case-enterprise_rag_bench-qst_0343"></a>

### enterprise_rag_bench:qst_0343 — 评分与执行路径对照

**问题：** What caused the savings $/day estimates in Optimization Suggestions beta to not match Arkadia Finance billing, and what UI or API changes should we make to prevent this confusion going forward?

**score：4→3（Δ-1）；rounds：2→2（Δ+0）。**

工具安排：naive 为第1轮2次；community 为第1轮2次。最终回答另占一轮。

两边均为 2 轮，但工具总数 2→2，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 16→14、文档 overview 9→35；工具结果字符数 72,182→102,923，QA token 21,034→28,144。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/def645c339a840c196816bb8ceb95ae0.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/f52de05124164a8489fa4d8d73e3045d.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Optimization Suggestions beta savings per day estimates Arkadia Finance billing mismatch","search_mode":"hybrid","doc_ids":null} | 12 | 7 | 0 | 成功 | D0250:0, D0322:0, D0322:1, D0322:2, D0250:1, D0250:3, D0250:2, D0189:0, D0266:0, D0091:2, D0216:3, D0217:3 |
| 2 | 1 | search_chunks {"query":"savings $/day estimate UI API changes prevent confusion","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0189:0, D0250:0, D0250:3, D0189:1, D0322:2, D0322:0, D0250:1, D0250:2, D0322:1, D0135:0, D0060:2, D0135:4 |

judge reasoning：

> The generated answer accurately and comprehensively covers all key causes (pricing fallback, cost basis, adoption assumption, cache warm-up, time window) and the essential UI/API improvements, consistent with the gold answers.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Optimization Suggestions beta savings $/day estimate Arkadia Finance billing mismatch","search_mode":"hybrid","doc_ids":null} | 12 | 35 | 5 | 成功 | D0250:0, D0322:0, D0250:1, D0322:1, D0322:2, D0250:3, D0250:2, D0189:0, D0091:2, D0266:0, D0135:3, D0216:3 |
| 2 | 1 | search_chunks {"query":"savings per day estimate not matching billing","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0250:0, D0250:2, D0250:1, D0250:3, D0322:0, D0322:2, D0189:1, D0322:1, D0189:0, D0255:0, D0266:0, D0091:2 |

judge reasoning：

> The generated answer accurately captures the main causes and most recommended UI/API changes, but omits a few key UI recommendations such as prominently displaying the baseline window/stale_as_of with timezone and offering an adoption scaling control in the UI, making it slightly incomplete.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Mismatch was primarily an expectation/reconciliation gap plus an estimator input gap. The Suggestions beta $/day is an estimated compute-cost delta derived from telemetry aggregates (GPU-sec/tokens) over a trailing baseline window (typically last 7d) with an explicit stale_as_of timestamp; it is not intended to match net invoiced totals. Arkadia compared the headline $/day to Billing export total_cost net of credits/committed-use discounts and with some initial local-time vs UTC day misalignment. Realized savings were further lower because caching was only rolled out to ~50% traffic for ~12 hours (so the first 24h window would be roughly ~25% of the full-adoption daily estimate) and because cache warm-up in the first 6-12+ hours reduced hit uplift versus the estimator steady-state assumption. Additionally, for Arkadia’s Dedicated/VPC setup the estimator could not access effective contracted pricing (missing effective price feed / cost attribution gaps) and fell back to catalog/list token pricing (price_source=catalog_fallback / assumption), inflating the USD/day figure even when the percent savings remained directionally reasonable.
> 
> To prevent confusion:
> UI should explicitly label $/day as "compute-cost estimate (not invoice total)" and prominently display the baseline window and stale_as_of (with timezone). Promote "assumes 100% of traffic for the shown scope" out of the Assumptions section into a top-level callout, and offer a simple rollout/adoption scaling control (or show a scaled range) for canary/A-B rollouts. When price_source is catalog_fallback or effective pricing is unavailable (especially for Dedicated/Private), de-emphasize or suppress $/day and/or show a strong warning tooltip, and consider making % savings the primary sortable field. Add a "How this matches billing" link that explains discounts/credits, invoice-only line items, and recommends comparing against Console Usage Analytics "Inference cost (compute)" for apples-to-apples.
> 
> API should surface pricing/assumption metadata needed for reconciliation: price_source (effective vs catalog_fallback/assumption), an explicit flag like savings_usd_uses_list_price, and the exact baseline window + stale_as_of used. Add an optional adoption_factor/scaled_savings field (or inputs to compute it client-side). Also downgrade/flag confidence when core pricing inputs are missing so we do not show Medium confidence while dollars are based on fallback pricing.

**naive 最终答案**

> **Causes of the mismatch:**
> 1. **Price source fallback**: The estimator used list/catalog price (`price_source=catalog_fallback`) because the `effective_token_price_usd` feed and `cost_attribution.v2` aggregates were missing for Arkadia Finance — not their contracted dedicated rate card, inflating the dollar figures.
> 2. **Different cost basis**: Estimates are compute-cost (GPU-sec + token pricing) and exclude credits, commit discounts, platform fees, and taxes, while billing exports are net of credits/commit.
> 3. **Full-adoption assumption**: The estimator assumes 100% adoption for the shown scope; Arkadia did a 50% phased rollout for ~12 hours.
> 4. **Cache warm-up**: First-day realized savings were lower than steady-state estimates.
> 5. **Time window mismatch**: Trailing-7d baseline with `stale_as_of` vs daily billing; customer initially compared local-time days.
> 
> **UI/API changes to prevent confusion:**
> - **UI**: Promote assumption text in the drawer — "Assumes 100% of traffic" + "Compute-cost estimate (not invoice total)"; make % savings primary and dollars secondary with a tooltip ("Dollar estimates use list price when effective rate not available"); suppress/hide the $ figure for Dedicated/Private when `price_source=catalog_fallback`.
> - **API**: Add a field like `savings_usd_is_estimated_from_list_price=true` (or expose `price_source`); optionally add an `adoption_factor` field or UI control to scale savings by rollout percentage; degrade confidence to "Low" when price source is a fallback; add docs on compute-cost vs invoice reconciliation.

**community 最终答案**

> **Causes of the mismatch (Arkadia Finance):**
> - The estimator used **list/catalog price fallback** (`price_source=catalog_fallback`) because the `effective_token_price_usd` feed / `cost_attribution.v2` aggregates were missing for the org, so dollars were overstated vs the contracted dedicated rate card.
> - Estimates are on a **compute-cost basis** (GPU-sec + token pricing) and exclude credits, commit discounts, platform fees, taxes, so they don't equal net invoiced totals.
> - Estimator **assumes 100% adoption** of the shown scope and doesn't account for partial rollout (Arkadia did a 50% rollout for ~12h) or cache warm-up day-1 effects.
> - **Time window mismatch** (trailing-7d `stale_as_of` vs the UTC days compared; billing local-time vs UTC).
> 
> **Recommended UI/API changes to prevent future confusion:**
> - UI: make % savings primary, dollars secondary; add prominent drawer callouts like "Assumes 100% of traffic" and "Compute-cost estimate (not invoice total)"; clarify that estimates exclude discounts/credits; degrade/hide confidence or suppress $ when `price_source=catalog_fallback` for Dedicated/Private.
> - API: expose `price_source` (or a field like `savings_usd_is_estimated_from_list_price=true`) and optionally an `adoption_factor`/adoption scaling field; fix/backfill the effective price feed; add docs on compute-cost vs invoice reconciliation; steer customers to Console Usage Analytics compute-cost for apples-to-apples comparisons.

</details>

<a id="case-enterprise_rag_bench-qst_0344"></a>

### enterprise_rag_bench:qst_0344 — 新增定向核验补齐服务积分审批流程

**问题：** Do we need to recalculate or annotate Dedicated throughput SLO compliance for streaming-heavy deployments before the streaming double-counting fix, and how should Support handle any credit requests tied to that period?

**score：2→4（Δ+2）；rounds：3→3（Δ+0）。**

naive 最终提前下结论 “No SLO credits were warranted”，忽略必须按修正后的计量确认违约及审批。community 第 2 轮限定 D0024 检索 credit request，最终补出 SRE breach window→Product entitlement→Finance→Legal→CS 流程，2→4 分。注意 D0024 在 community 首轮已经以 chunk 及 overview 同时返回，不能称为纯社区 overview 独立发现后引导的证据；两边查询也不同。实际可确认的是检索路线转向政策原文且最终保留条件化审批，而不是把测量缺陷直接等同于无赔付资格。

工具安排：naive 为第1轮2次、第2轮1次；community 为第1轮2次、第2轮2次。最终回答另占一轮。

两边均为 3 轮，但工具总数 3→4，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 23→24、文档 overview 11→41；工具结果字符数 80,856→136,627，QA token 39,660→59,262。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

<details>
<summary>展开 judge 所提实体的字面证据核对</summary>

| 实体/术语 | naive工具中首次匹配 | naive答案 | community工具中首次匹配 | community答案 |
|---|---|---|---|---|
| SRE | 轮1/调用1/D0181:0 | 出现 | 轮1/调用1/D0181:0 | 出现 |

这里只检查指定字面串及字母数字边界，不评判上下文是否在讨论同一事实；未匹配不排除同义表述，出现也不代表正确采用。它用于区分“可能未召回”和“已出现但未展开”的复核入口，不能自动判定因果。

</details>

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/fef8cd5514f14620ab76929fe73c0179.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/5c48aa1f9a6a46ca8a1fa04a08d21fbe.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Dedicated throughput SLO compliance streaming double-counting fix recalculate annotate","search_mode":"hybrid","doc_ids":null} | 12 | 6 | 0 | 成功 | D0181:0, D0257:2, D0092:6, D0257:0, D0257:1, D0092:5, D0236:0, D0092:2, D0092:0, D0236:3, D0184:0, D0179:0 |
| 2 | 1 | search_chunks {"query":"credit requests streaming-heavy deployments before fix Support handle","search_mode":"hybrid","doc_ids":null} | 12 | 5 | 0 | 成功 | D0266:2, D0236:0, D0266:3, D0236:2, D0236:3, D0181:0, D0230:2, D0230:1, D0307:3, D0217:4, D0257:2, D0251:4 |
| 3 | 2 | read_chunks {"doc_id":"D0092","ordinals":[1,2,3,4,5,6]} | 6 | 0 | 0 | 成功 | D0092:1, D0092:2, D0092:3, D0092:4, D0092:5, D0092:6 |

judge reasoning：

> The generated answer correctly captures the 'annotate, don't recalculate' main point, but its credit-request handling is incomplete and partially contradicts the gold by omitting the required validation via SRE/Observability with corrected accounting and the standard credit-review/approval workflow, while also prematurely concluding no credits are warranted.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Dedicated throughput SLO compliance streaming double-counting fix recalculate annotate credit requests","search_mode":"hybrid","doc_ids":null} | 12 | 34 | 5 | 成功 | D0181:0, D0257:2, D0092:6, D0257:0, D0257:1, D0236:0, D0092:2, D0092:5, D0266:3, D0024:0, D0236:3, D0024:5 |
| 2 | 1 | search_chunks {"query":"streaming double-counting fix SLO compliance Support credit handling","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0257:2, D0236:0, D0181:0, D0257:0, D0236:3, D0257:1, D0092:6, D0266:3, D0179:0, D0266:2, D0181:1, D0030:0 |
| 3 | 2 | search_chunks {"doc_ids":["D0024"],"query":"credit request SLO breach streaming fix affected period how to handle","search_mode":"hybrid"} | 6 | 7 | 1 | 成功 | D0024:5, D0024:4, D0024:0, D0024:1, D0024:2, D0024:3 |
| 4 | 2 | search_chunks {"doc_ids":["D0092"],"query":"recalculate compliance SLO reports spanning deploy window annotate backfill PR-19422","search_mode":"hybrid"} | 7 | 0 | 0 | 成功 | D0092:6, D0092:5, D0092:3, D0092:2, D0092:1, D0092:0, D0092:4 |

judge reasoning：

> The generated answer fully captures the gold meaning: annotate rather than automatically backfill SLO compliance for the pre-fix period, and for credit requests, avoid pre-approval and require SRE validation through the standard approval workflow.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Don't do an automatic backfill/recalculation of Dedicated throughput SLO compliance for the pre-PR-19422 period; instead, annotate any SLO reports/dashboards spanning that boundary because streaming workloads could have inflated tokens/sec (masking real misses). If a customer requests credits tied to that period, Support should not pre-approve; gather the impact window/deployment/tier, engage SRE/Observability to validate the breach using corrected accounting (prefer finalized usage completion tokens rather than the old streaming counter), confirm exclusions, then run the standard credit-review/approval workflow (Product entitlement check + Finance/Legal as needed) and communicate the decision.

**naive 最终答案**

> **Annotate, don't recalculate.** The SLO spec (D0092) states that any backfills or comparisons across the PR-19422 boundary must annotate the change. No backfill/recalculation was planned—the dashboard was annotated for the affected range (2025-02-10 through 2025-03-01) and the known issue was documented in the Dedicated throughput SLO FAQ (D0257). SLO reports spanning the deploy window still need annotation (backfill decision left to SRE, D0181).
> 
> **Credit requests:** Billing was not impacted (billing uses metering events, not SLO throughput counters). The bug inflated the throughput metric (overcounted tokens), so it did not understate compliance. Support should validate SLO evaluator inputs, explain billing is unaffected, and route any credit requests per commercial terms/escalation playbook (CS Rachel Kim / Support Ops Dev Patel). No SLO credits were warranted from this issue.

**community 最终答案**

> **Annotation/recalculation:** Yes—annotate the affected period. The pre-fix (double-counted) streaming metrics inflated tokens/sec by ~2x, so they're not valid for compliance comparisons. The dashboard was annotated for the affected range (2025-02-10 through 2025-03-01), and the formal SLO policy states that any backfills or comparisons across the PR-19422 boundary **must annotate the change**. No backfill was planned; whether to recalculate/backfill SLO reports spanning the deploy window is an **SRE decision** (left as a follow-up). Until then, treat pre-fix streaming throughput values as best-effort and avoid pre/post comparisons.
> 
> **Credit requests tied to that period:** Support should not treat the inflated pre-fix metric as evidence of a breach or grant credits off it. Credits require SRE confirmation of a breach per the **canonical evaluator** (validate SLO evaluator inputs), the breach must not be excluded, and the request must go through the standard approval path (SRE breach window → Product entitlement → Finance → Legal → CS comms). Since the bug was a measurement artifact (billing was unaffected), Support should not confirm a breach or commit to any credit amount until SRE validates the corrected evaluator inputs; no retroactive credit should be issued based on the double-counted figures.

</details>

<a id="case-enterprise_rag_bench-qst_0345"></a>

### enterprise_rag_bench:qst_0345 — 评分与执行路径对照

**问题：** For the Trident Financial Private VPC deal, what is our approved stance on US-only data residency and 7-year audit log retention/export, and which evidence pack artifacts should we share (and how) to back it up?

**score：2→3（Δ+1）；rounds：2→3（Δ+1）。**

工具安排：naive 为第1轮2次；community 为第1轮2次、第2轮2次。最终回答另占一轮。

轮次增加 1，工具总数 2→4、错误 0→1，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 22→24、文档 overview 12→47；工具结果字符数 75,396→142,885，QA token 21,910→64,841。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

<details>
<summary>展开 judge 所提实体的字面证据核对</summary>

| 实体/术语 | naive工具中首次匹配 | naive答案 | community工具中首次匹配 | community答案 |
|---|---|---|---|---|
| SOC 2 | 轮1/调用1/D0142:3 | 未匹配 | 轮1/调用1/D0141/overview | 出现 |

这里只检查指定字面串及字母数字边界，不评判上下文是否在讨论同一事实；未匹配不排除同义表述，出现也不代表正确采用。它用于区分“可能未召回”和“已出现但未展开”的复核入口，不能自动判定因果。

</details>

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/bd8cab3cfeec47c4ae5f829df221e8a5.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/445f2bea36344edc9459b5e2584378b3.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Trident Financial Private VPC deal data residency audit log retention","search_mode":"hybrid","doc_ids":null} | 12 | 8 | 0 | 成功 | D0199:0, D0199:4, D0199:5, D0199:2, D0276:0, D0199:1, D0142:3, D0163:0, D0162:0, D0161:0, D0165:0, D0159:0 |
| 2 | 1 | search_chunks {"query":"US-only data residency 7-year audit log retention export evidence pack","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0146:1, D0146:0, D0148:0, D0148:2, D0143:3, D0163:0, D0163:3, D0146:4, D0148:1, D0146:3, D0144:1, D0199:0 |

judge reasoning：

> The generated answer correctly captures the approved data residency and 7-year audit log stance, but it omits several required evidence pack artifacts (e.g., SOC 2 Type II under NDA, audit log sample/field reference, architecture artifacts) and does not fully describe the mandated secure evidence-pack sharing process, making it only partially complete.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Trident Financial Private VPC data residency audit log retention","search_mode":"hybrid","doc_ids":null} | 12 | 27 | 4 | 成功 | D0199:0, D0199:4, D0199:5, D0276:0, D0199:2, D0163:0, D0199:1, D0161:0, D0165:0, D0206:0, D0159:0, D0162:0 |
| 2 | 1 | search_chunks {"query":"evidence pack artifacts share Trident","search_mode":"hybrid","doc_ids":null} | 12 | 12 | 2 | 成功 | D0147:0, D0147:3, D0146:0, D0147:2, D0199:0, D0199:1, D0199:5, D0148:0, D0146:4, D0199:2, D0148:2, D0159:4 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"Trident evidence pack SOC 2 audit log sample share","search_mode":"hybrid"} | 12 | 8 | 1 | 成功 | D0147:0, D0147:3, D0148:0, D0146:0, D0147:4, D0199:0, D0146:3, D0261:0, D0199:5, D0148:2, D0199:1, D0157:0 |
| 4 | 2 | read_chunks {"doc_id":"D0199","ordinals":[3,6]} | 0 | 0 | 0 | Unknown chunk ordinal | — |

judge reasoning：

> The generated answer correctly captures the approved US residency and 7-year audit log stances and most evidence pack artifacts/sharing steps, but omits the architecture artifacts (data flow diagram and network boundary overview) that the gold answer lists as essential evidence.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Approved stance for Trident Private (VPC): we can commit that customer content (prompts/outputs) is processed and stored within the agreed US region/VPC; we should not agree to absolute "no processing outside the US/no cross-border access ever" language-admin/support access should be framed as controlled, least-privilege, customer-policy-restrictable, and auditable (and avoid "US persons only" as an absolute). For the 7-year audit log requirement: we support audit logging and audit log export; Trident should meet 7-year retention by exporting logs to Trident-controlled storage/SIEM and retaining them there, rather than requiring Redwood to retain audit logs for 7 years. Evidence pack artifacts to share to substantiate this: SOC 2 Type II (under NDA), data residency/region availability statement, data retention policy statement, audit log sample (redacted) + field reference, audit log export patterns overview, plus architecture artifacts (data flow/request processing diagram and network boundary overview; optionally encryption overview). Share via the evidence pack process only: submit an evidence request with prospect/recipients + NDA status + specific artifacts needed; Security/GRC shares via a secure, access-controlled link (recipient-specific/expiring, SOC2 watermarked); do not email SOC2 as an attachment and track recipients/date/NDAs in the deal record/CRM.

**naive 最终答案**

> **Approved stance (per D0199):**
> - **US-only data residency:** We do **not** commit to an absolute "no processing outside the US." We commit that Customer Content (prompts/outputs) is processed and stored in the agreed deployment region/VPC, with admin/support access controlled, limited, and auditable (not an absolute ban on access from outside the US).
> - **7-year audit log retention/export:** We support audit logging and export so Trident can ingest logs into its own SIEM and retain them **7 years (or longer) under Trident's control**; long-term retention is satisfied via export/retention in Trident systems, **not** by Redwood retaining logs for 7 years.
> 
> **Evidence pack artifacts to share (per D0146/D0148):**
> Deliver the **customer-facing Baseline Compliance Pack** (redacted, customer-safe bundle only — no internal dashboards or incident notes), shared via customer-approved channels, containing:
> - **Data residency/region processing summary** (control plane, data plane, telemetry storage regions, configured residency constraints) — backs the in-region commitment.
> - **Audit log coverage summary + time-windowed audit log export** (CSV/JSONL + manifest/checksum) — supports SIEM export/7-year customer-side retention.
> - **Retention configuration export** (effective policy JSON + change history) — shows configurable retention settings.
> 
> **How:** As a single versioned ZIP (`redwood-compliance-pack_<tenant>_private_<region>_<date>_vX.zip`). For Private/VPC, the audit-log exporter may run in Trident's environment — provide template names, command, and output schema, with Solutions Engineering executing inside their environment per agreed access.

**community 最终答案**

> **Approved stance (from D0199, Redwood's counters to Trident):**
> 
> - **US-only data residency:** Redwood can commit that Customer Content (prompts/outputs) is processed and stored within the agreed deployment region/VPC for Private/VPC. It rejects Trident's absolute "no processing outside the US" if it constrains support/metadata — instead, any administrative access is controlled, limited, need-to-know, and auditable.
> - **7-year audit log retention/export:** Redwood supports audit logging and export so Trident can ingest logs into its own SIEM and retain them 7+ years under Trident's control. Long-term retention is satisfied via export/retention in Trident's systems, not by Redwood retaining logs for 7 years.
> 
> **Evidence pack artifacts to share (per D0147, D0148, D0146):**
> - SOC 2 Type II report (NDA required) — to back compliance posture.
> - Redacted audit log sample + field glossary + export patterns overview — to evidence audit log export/SIEM capability.
> - Customer-facing retention statement (retention controls by deployment type) and data residency statement.
> - Baseline Compliance Pack artifacts: audit log coverage summary, retention configuration export (current state + change history), RBAC summary, data residency/processing regions summary.
> 
> **How to share:**
> - Secure, access-controlled link from an approved repository; expiring when possible; SOC 2 watermarked per recipient (via GRC, Olga Petrov).
> - Not via email attachment or procurement-portal upload without Security + Legal approval; record recipients, date, and NDA status in the CRM. Route requests through GRC/evidence intake (Olga Petrov) with Legal (Michael Grant) for redlines.

</details>

<a id="case-enterprise_rag_bench-qst_0347"></a>

### enterprise_rag_bench:qst_0347 — 评分与执行路径对照

**问题：** For an air-gapped on-prem restore into a brand new cluster, what do we need to install before running restore apply, and what will the installer check and report if those prerequisites are missing?

**score：4→3（Δ-1）；rounds：2→2（Δ+0）。**

工具安排：naive 为第1轮2次；community 为第1轮2次。最终回答另占一轮。

两边均为 2 轮，但工具总数 2→2，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 17→17、文档 overview 7→21；工具结果字符数 72,596→89,061，QA token 20,434→24,175。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/7f2a36752f584403a976c7f025774843.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/3964ab74ce1641d0839db03138d4e3fc.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"air-gapped on-prem restore brand new cluster install before restore apply prerequisites missing","search_mode":"hybrid","doc_ids":null} | 12 | 5 | 0 | 成功 | D0282:0, D0282:2, D0282:3, D0282:1, D0172:0, D0065:0, D0065:4, D0172:1, D0071:0, D0081:0, D0081:1, D0071:2 |
| 2 | 1 | search_chunks {"query":"restore apply installer check report missing prerequisites","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0172:0, D0282:0, D0282:3, D0282:1, D0282:2, D0172:1, D0081:0, D0295:3, D0071:5, D0071:4, D0295:1, D0072:4 |

judge reasoning：

> The generated answer fully captures the required prerequisite installs and accurately describes the preflight failure behavior, with only minor permissible extra context.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"air-gapped on-prem restore brand new cluster install prerequisites before restore apply","search_mode":"hybrid","doc_ids":null} | 12 | 21 | 3 | 成功 | D0282:0, D0282:2, D0282:3, D0282:1, D0172:0, D0065:0, D0065:4, D0071:0, D0081:1, D0172:1, D0081:0, D0071:2 |
| 2 | 1 | search_chunks {"query":"installer check prerequisites missing report before running restore apply","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0172:0, D0282:0, D0282:3, D0282:1, D0172:1, D0282:2, D0071:5, D0081:0, D0071:4, D0072:4, D0081:4, D0295:0 |

judge reasoning：

> The generated answer correctly covers the required offline-bundle prerequisites and the preflight CRD readiness check with failure reporting, but omits some additional preflight checks (cluster connectivity, artifact integrity, etc.) and the redacted restore report detail.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> For an air-gapped on-prem restore into a brand new cluster, install the prerequisite CRDs/operators from the offline bundle before running restore apply: cert-manager (with installCRDs=true), external-secrets, and the Redwood control-plane CRDs (via the Redwood control-plane/CRD chart) so CustomResources like Certificate, ExternalSecret, and RedwoodTenant are recognized. If these prerequisites are missing, the installer's restore apply preflight will stop before applying anything, check cluster connectivity plus CRD/GVK readiness (and other preflight items like version compatibility, artifact integrity, and key/storage access), and it will print the exact missing CRDs/GVKs with remediation hints and write a redacted restore report marked as a preflight failure.

**naive 最终答案**

> For an air-gapped on-prem restore into a brand new cluster, before running `restore apply` you must install from the offline bundle (with CRDs enabled, not `--skip-crds`):
> 1. **cert-manager** (`helm upgrade --install cert-manager ./charts/cert-manager -n cert-manager --create-namespace --set installCRDs=true`)
> 2. **external-secrets** (`helm upgrade --install external-secrets ./charts/external-secrets -n external-secrets --create-namespace`)
> 3. **redwood-control-plane chart** (to lay down the Redwood platform CRDs, e.g., `platform.redwood.ai`)
> 
> If those prerequisites (CRDs) are missing, the installer's strict preflight check (which includes namespace/CRD readiness) will **fail fast / hard stop** and report the exact missing resources — which CRD group/version is absent — plus a remediation hint pointing to the runbook. The failure is categorized as `preflight` (exit code 2) in the validation report, and it will not attempt to apply the control-plane chart before CRDs exist. (Note: the earlier installer version only surfaced generic "no matches for kind" errors; the enhanced preflight that explicitly lists missing CRDs was a follow-up.)

**community 最终答案**

> Before running `restore apply` in an air-gapped on-prem restore into a brand new cluster, install from the offline bundle (in order):
> 1. cert-manager (with `installCRDs=true`)
> 2. external-secrets
> 3. redwood-control-plane chart (to lay down the Redwood platform CRDs)
> 
> If those prerequisites are missing, the installer's `restore apply` preflight performs a strict CRD readiness check: it hard-stops (fails fast), prints the exact missing CRD group/version (GVKs) and remediation hints, and reports the failure with error category `preflight` and exit code 2 (preflight), so it never attempts to apply manifests before the CRDs exist.

</details>

<a id="case-enterprise_rag_bench-qst_0351"></a>

### enterprise_rag_bench:qst_0351 — 评分与执行路径对照

**问题：** If Console shows a canary step change to a lower percentage but one region keeps serving the old split, how do we tell whether it is cohorting key behavior, router version skew, or stale config propagation, and what is the recommended mitigation?

**score：4→3（Δ-1）；rounds：2→2（Δ+0）。**

工具安排：naive 为第1轮2次；community 为第1轮1次。最终回答另占一轮。

两边均为 2 轮，但工具总数 2→1，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 15→12、文档 overview 3→32；工具结果字符数 60,423→64,010，QA token 19,445→20,265。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/9a6aec689ebf485aa142e407e7dbef77.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/3104fdd7191d42bd97d2e593568cef30.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"canary step change lower percentage region old split cohorting key router version skew stale config propagation","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0316:3, D0316:4, D0316:1, D0253:1, D0119:1, D0119:0, D0119:3, D0253:2, D0119:4, D0253:0, D0119:2, D0316:2 |
| 2 | 1 | search_chunks {"query":"stale config propagation mitigation router version mismatch canary","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0253:1, D0253:2, D0253:3, D0316:1, D0316:4, D0316:0, D0119:3, D0119:0, D0119:1, D0253:0, D0119:6, D0316:3 |

judge reasoning：

> The generated answer accurately covers the key diagnostic checks and mitigations for cohorting key behavior, router version skew, and stale config propagation, and is fully consistent with the gold answers.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"canary step change lower percentage region serving old split cohorting key router version skew stale config propagation","search_mode":"hybrid","doc_ids":null} | 12 | 32 | 4 | 成功 | D0316:3, D0316:4, D0316:1, D0253:2, D0253:1, D0119:1, D0119:0, D0119:3, D0253:0, D0119:4, D0119:2, D0316:2 |

judge reasoning：

> The generated answer correctly distinguishes and mitigates all three causes, but omits the initial control-plane/orchestrator confirmation and the full general safety hierarchy (rollback baseline, kill-switch fallback), so it is good but not perfect.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> First confirm the control-plane target: fetch rollout from orchestrator (current step %) and compare to observed canary % per region over a 10-15m window. Then check the data plane in the affected region: (1) If router decision logs show configured_canary_percent still equals the old step (even though Console/orchestrator shows the lower %), it's stale config propagation (often watch disconnect / cache); verify per-region route config version/last-applied age and fix by forcing a router config resync/rolling restart in that region (or re-apply/reconcile), and pause/rollback if safety is at risk. (2) If configured_canary_percent matches the new lower % but the region's split stays biased, inspect router logs for cohort_key_source/cohort_key_present/fallback_source/hash_seed: missing stable key causing fallback (e.g., request_id/UUID gives correct aggregate % but no stickiness; legacy IP/route-only seed indicates wrong/old cohorting behavior). (3) If only one region shows legacy cohorting fields/behavior or different hash seed/fallback order, check router build/version by region; that's router version skew-mitigate by redeploying/rolling forward that region to the minimum router version, and optionally set canary_pct=0 for that region as immediate containment. Recommended mitigation when unsure: pause rollout; if any chance of overexposing canary, rollback to baseline; use kill switch only if normal pause/rollback cannot take effect. Longer-term: ensure routers have watchdog + periodic resync and recommend customers send X-Redwood-Cohort-Key or Idempotency-Key (and region affinity if needed) to make cohorting predictable.

**naive 最终答案**

> **How to tell (from router decision/config logs in the affected region):**
> 
> 1. **Cohorting key behavior** – Check log fields `cohort_key_source`, `cohort_key_present`, `fallback_source`, `hash_seed`. If the user key is missing and fallback is IP with `hash_seed=route_id_only`, the cohorting inputs are wrong and bias the assignment (legacy code path).
> 2. **Router version skew** – Check router build/version in that region vs others (e.g., 1.38.2 vs 1.38.3). An older router version using legacy cohorting fallback can produce the mismatch.
> 3. **Stale config propagation** – Check config apply health: `configured_canary_percent` (e.g., still 25) vs `console_step_target_percent` (10), route config version per region, config-watch health / last-applied config age, and watch-stream errors/disconnects.
> 
> The runbook diagnostic: for a single-region mismatch, check route config apply status in that region; validate cohorting hash inputs in routing decision logs.
> 
> **Recommended mitigation:**
> - Containment: set that region's canary to 0% via region override (or pause/rollback if unsure/impacted) to minimize disruption.
> - Version skew: redeploy/roll the region's routers to the correct version, verify cohorting logs show expected hash inputs and observed split, then revert the override.
> - Stale config: rolling-restart the router deployment in that region to force a fresh config pull/resync, then confirm convergence.
> - Long-term: deploy guards for region version skew, required `router_min_version` for rollouts, config watch watchdog + periodic resync, and observed-vs-expected split alerts per region.

**community 最终答案**

> ## How to distinguish the three causes
> 
> Pull routing-decision/cohorting logs in the affected region and check specific fields:
> 
> **1. Stale config propagation**
> - Logs show `configured_canary_percent` = **old split (e.g., 25)** while `console_step_target_percent` = **new split (10)**.
> - Some pods show 10, others 25 (subset serving last-known config).
> - Caused by config-watch stream disconnect with no periodic resync.
> - Confirm via route-config version per region, config apply errors, `router_config_last_apply_age`.
> 
> **2. Router version skew**
> - `configured_canary_percent` shows the new value, but cohorting fields are off: `hash_seed=route_id_only`, `cohort_key_present=false`, `fallback_source=ip`.
> - Caused by legacy fallback behavior in an older router build (e.g., 1.38.2 vs 1.38.3) using a route-only seed/IP fallback instead of tenant+route seed and stable-key precedence.
> - Confirm via build stamp/version in that region.
> 
> **3. Cohort key behavior**
> - Hash inputs and `hash_seed` are correct, but `cohort_key_present=false` because the client doesn't send a stable user/session key, so it falls back to `request_id`/IP.
> - This produces non-deterministic variance, not a systematic old-split; verify logs show expected hash inputs and that observed split matches.
> 
> ## Recommended mitigation
> 
> - **Stale config:** rolling restart of the router deployment in that region to force a full config resync; permanent fix = periodic resync + watch-health watchdog with alerting.
> - **Version skew:** emergency region override (`canary_pct=0` in that region) to contain, redeploy/upgrade routers in the region to the fixed version, verify cohorting logs and observed split, then remove the override. Add a deploy guard requiring a minimum router version.
> - **Cohort key behavior:** rollback and escalate if unstable; recommend customers send stable `x-rw-user-key`/`x-rw-session-id`.
> - General: if impact is ongoing, **pause the rollout** first, then triage.

</details>

<a id="case-enterprise_rag_bench-qst_0352"></a>

### enterprise_rag_bench:qst_0352 — 相同关键证据已在两边，收益发生在答案采用环节

**问题：** A dedicated beta customer says the Suggestions view overstates dollar savings compared to billing after they enable caching in a partial rollout; what is causing the mismatch and what UI and estimator changes should we make to prevent this confusion?

**score：2→4（Δ+2）；rounds：2→2（Δ+0）。**

community 补写 Dedicated catalog/list-price fallback，2→4 分且同为 2 轮。但逐条查原文可见 naive 首轮已返回 D0322:2 的 catalog_fallback 日志、D0322:0 的 effective_token_price_usd 说明，甚至 D0322 overview 也清楚概括缺失有效价格导致回退。该关键事实并非社区独有。可以说 community 这次回答更完整，不能说“社区新增了 naive 没有检索到的价格回退证据”。这也是用 trace 检验 judge 理由后修正直觉归因的例子。

工具安排：naive 为第1轮2次；community 为第1轮2次。最终回答另占一轮。

两边均为 2 轮，但工具总数 2→2，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 14→14、文档 overview 8→35；工具结果字符数 69,443→101,894，QA token 20,347→28,996。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/bbf95cbde96549fa9d1a23dbec582667.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/6bf9d2a5790140f3ab590867015382e5.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Suggestions view overstates dollar savings compared to billing caching partial rollout","search_mode":"hybrid","doc_ids":null} | 12 | 6 | 0 | 成功 | D0250:0, D0250:1, D0250:2, D0189:0, D0250:3, D0322:2, D0322:0, D0322:1, D0189:1, D0255:0, D0219:2, D0266:0 |
| 2 | 1 | search_chunks {"query":"caching estimator savings mismatch billing","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0250:0, D0250:1, D0322:0, D0255:0, D0250:3, D0250:2, D0322:1, D0189:0, D0189:1, D0094:1, D0266:0, D0217:6 |

judge reasoning：

> The generated answer correctly identifies partial rollout, compute-cost vs net billing, and warm-up as causes, but omits the Dedicated list-price fallback issue and related UI/estimator changes for price basis/flagging, making it partially complete.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Suggestions view overstates dollar savings compared to billing after enabling caching partial rollout","search_mode":"hybrid","doc_ids":null} | 12 | 35 | 5 | 成功 | D0250:0, D0250:2, D0250:1, D0189:0, D0250:3, D0322:2, D0322:0, D0322:1, D0189:1, D0255:0, D0219:2, D0094:1 |
| 2 | 1 | search_chunks {"query":"caching partial rollout savings estimator mismatch billing","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0250:0, D0250:1, D0250:3, D0189:0, D0250:2, D0322:0, D0255:0, D0189:1, D0322:1, D0266:0, D0322:2, D0217:6 |

judge reasoning：

> The generated answer fully captures the gold answer's core causes and proposed UI/estimator changes, adding consistent detail without contradicting or omitting any key facts.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Mismatch is mostly expectation/assumption gaps: the caching savings estimator is computed off trailing-7d baseline compute-cost attribution and assumes 100% enablement at the shown route+model scope and steady-state cache hit uplift; the customer only rolled out caching to part of traffic (so realized savings scale down roughly by rollout% and are further reduced during the first 6-12+ hours of cache warm-up). They're also comparing to net invoiced billing totals (credits/commit discounts and non-inference line items) rather than compute-cost, and on Dedicated the $ estimate can be inflated if the estimator falls back to catalog/list price because the effective rate feed is missing.
> 
> Changes: UI should make the assumptions unavoidable in both list and drawer (Compute-cost estimate, not invoice; window/stale_as_of; assumes 100% traffic; expect 48-72h for warm-up) and show price basis/source (effective rate vs list-price fallback); when on Dedicated/Private with list-price fallback, hide $/day or clearly badge it and emphasize % savings instead. Estimator should incorporate an adoption/rollout factor (or let the UI scale by rollout %) and ideally model/report warm-up vs steady-state; also use effective dedicated pricing when available and downgrade confidence/flag the estimate when pricing or billed-token basis inputs are missing.

**naive 最终答案**

> **Cause of mismatch:** Not a billing bug — it's a reconciliation/expectation gap:
> 1. **Partial rollout not modeled:** The caching estimator assumes 100% adoption of the shown route+model scope; it doesn't account for rollout percentage (variant telemetry isn't wired in v0). With a 50%/12h rollout, realized savings ≈ 25% of the headline $/day.
> 2. **Compute-cost vs net billing:** Estimates use cost-attribution aggregates (GPU-sec + token pricing) and exclude credits, committed-use discounts, platform fees, and taxes, so they exceed net invoiced totals.
> 3. **Cache warm-up:** The estimator assumes steady-state uplift (median 7-day prefix reuse); day-1 savings are lower for the first 6–12+ hours.
> 4. **Window mismatch:** Estimates use a trailing-7d baseline + `stale_as_of` with up to 24h ingestion lag; the customer compared UTC invoice days (initially local time).
> 
> **UI changes:** Make assumptions prominent — add inline callout in the drawer: "Assumes 100% of traffic" and "Compute-cost estimate (not invoice total)"; promote assumption text (100% adoption, compute-cost basis, excludes discounts/credits) instead of burying it in the Assumptions section; consider de-emphasizing $/day (people treat the sortable $/day as realized savings).
> 
> **Estimator changes:** Add an optional `adoption_factor` field in the suggestion payload (or a UI control) to scale savings by rollout percentage; add a docs section on reconciliation (compute-cost vs invoice total).

**community 最终答案**

> ## Cause of the mismatch
> 
> This is a reconciliation/expectation gap plus a pricing‑feed bug, not a billing bug:
> 
> 1. **Compute-cost vs. net-invoice basis** – Suggestions $/day is computed from cost-attribution aggregates (GPU‑sec + token pricing) and excludes credits, commit discounts, platform fees, and taxes, so it never equals net invoiced totals.
> 2. **Partial rollout ignored** – The estimator assumes **100% adoption** for the route/model scope shown; it has no rollout/adoption factor in v0. With caching at 50% for ~12h, observed savings are only ~25% of the headline $/day (customer saw ~6–8% vs an ~18–22% full-adoption estimate).
> 3. **Cache warm-up** – The estimator assumes steady-state hit uplift (median 7d prefix-reuse), so first-day realized savings are lower than the estimate (assess over 48–72h).
> 4. **Time-window mismatch** – Estimate uses a trailing-7d baseline + `stale_as_of` (UTC, up to 24h ingestion lag), while the customer compared net billing daily totals (initially in local time).
> 5. **List-price fallback for Dedicated** – For this dedicated customer, `cost_attribution.v2` was partially missing and the `effective_token_price_usd` feed was down, so the estimator fell back to `price_source=catalog_fallback` (list price) instead of their contracted rate card — inflating the dollar figure (%). Savings and latency were still traffic-derived and directionally correct.
> 
> ## UI changes
> 
> - Show **% savings as primary**, dollars as secondary, with a tooltip: "Dollar estimates use list price when effective rate not available."
> - **Suppress/hide $** when `price_source=catalog_fallback` for Dedicated/Private (or flag via a new field like `savings_usd_is_estimated_from_list_price`).
> - Add a prominent inline callout in the drawer: **"Assumes 100% of traffic"** and **"Compute-cost estimate (not invoice total)"**; promote the Assumptions text so it's not buried.
> - **Degrade confidence to "Low"** when a core assumption (price source) is missing, instead of reading "Medium" based on traffic variance alone.
> 
> ## Estimator changes
> 
> - Add an optional **`adoption_factor`** to the suggestion payload (and/or a UI control) to scale savings by rollout percentage for A/B/canary rollouts.
> - **Restore/backfill the `effective_token_price_usd` aggregates** so estimates use the effective (contracted) rate rather than list price.
> - Emit price-source reason codes (`price_source=catalog_fallback`, `missing_effective_price`) into the payload for disclosure and confidence degradation.
> - Add docs clarifying compute-cost vs. invoice reconciliation and rollout scaling.

</details>

<a id="case-enterprise_rag_bench-qst_0353"></a>

### enterprise_rag_bench:qst_0353 — 评分与执行路径对照

**问题：** Before we re-enable paging and hook perf-canary into rollout gates, what exact baseline key, min-sample requirements, and incident-bot dedupe key should we enforce to avoid another false-positive alert storm?

**score：2→3（Δ+1）；rounds：2→2（Δ+0）。**

工具安排：naive 为第1轮2次；community 为第1轮2次。最终回答另占一轮。

两边均为 2 轮，但工具总数 2→2，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 16→19、文档 overview 8→72；工具结果字符数 75,066→147,507，QA token 21,341→39,184。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/8f8f972ad81e4b2fa7d45fd2c3b8fcf8.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/5bcc758a88974c39a8dacd971ca39bfb.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"re-enable paging perf-canary rollout gates baseline key min-sample incident-bot dedupe key","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0105:0, D0105:4, D0012:0, D0105:3, D0105:2, D0105:1, D0012:3, D0012:2, D0012:1, D0012:4, D0073:5, D0297:3 |
| 2 | 1 | search_chunks {"query":"false-positive alert storm baseline min samples incident bot dedupe","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0105:0, D0012:3, D0105:1, D0105:4, D0105:2, D0193:4, D0105:3, D0012:4, D0012:0, D0183:0, D0079:6, D0311:0 |

judge reasoning：

> The baseline key and min-sample requirements are correct, but the incident-bot dedupe key is presented as two ambiguous alternatives rather than the single required combined key, omitting key components from each alternative.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"perf-canary rollout gates paging baseline key min-sample","search_mode":"hybrid","doc_ids":null} | 12 | 46 | 6 | 成功 | D0105:0, D0012:0, D0105:4, D0012:2, D0012:1, D0105:3, D0015:0, D0012:5, D0105:2, D0012:4, D0073:5, D0012:3 |
| 2 | 1 | search_chunks {"query":"incident-bot dedupe key false-positive alert storm","search_mode":"hybrid","doc_ids":null} | 12 | 26 | 3 | 成功 | D0105:0, D0193:4, D0105:2, D0105:4, D0078:0, D0284:2, D0184:0, D0116:0, D0067:3, D0105:3, D0012:3, D0284:0 |

judge reasoning：

> The answer correctly covers the min-sample thresholds and the baseline/dedupe key dimensions, but it slightly misstates the baseline key by making region unconditional (instead of conditional on separate baselines) and presents an incomplete dedupe variant.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Baseline comparisons must use the fixed/immutable baseline keyed like-for-like on: model_id + model_version + runtime_build_id + kernel_set_id (kernel selection/version identifier) + hardware_sku, with region and/or capacity_tier only if we explicitly maintain separate baselines for them; explicitly do not include prompt bucket/shape, run_id, route, or other transient labels. Min-samples gate: per key per evaluation window require >=200 successful requests for latency; for tokens/sec require >=200 successful requests AND >=50,000 total generated tokens; if not met, do not change alert state. Incident-bot dedupe key must include: model_id + model_version + runtime_build_id + kernel_set_id + hardware_sku (+ region if present) + metric_type/alert_type + severity.

**naive 最终答案**

> Per ADR-0142 and the postmortem's completed CPAs, enforce:
> 
> - **Baseline key:** `model_id` + `model_version` + `runtime_build_id` + `hardware_sku` (+ `kernel_set_id` per ADR-0142; `region` per the postmortem's canonical key when present). Explicitly **exclude** prompt bucket/run IDs, and treat "baseline missing" as canary-unhealthy (warn once, stop regression evaluation) instead of falling back to default thresholds.
> - **Min-sample requirements** (per key, per 10-minute evaluation window):
>   - Latency metrics: ≥ **200 successful canary requests** per window.
>   - Tokens/sec: ≥ **200 successful canary requests** AND ≥ **50,000 total generated tokens** per window.
>   - If unmet, no alert state change is allowed.
> - **Incident-bot dedupe key:** `model_id` + `model_version` + `runtime_build_id` + `hardware_sku` + `region` (if present) + `alert_type` (postmortem), or equivalently `kernel_set_id` + `metric_type` + `severity` (ADR-0142).

**community 最终答案**

> Based on the postmortem (D0105) and ADR-0142 (D0012), enforce:
> 
> **Baseline key (canonical, baseline lookup):**
> `model_id` + `model_version` + `runtime_build_id` + `hardware_sku` + `region` — explicitly **not** including prompt bucket/run IDs. (ADR-0142 also lists `kernel_set_id` as a required key field.)
> 
> **Min-sample requirements (per key, per 10-min window):**
> - Latency metrics: minimum **200 successful canary requests** per window.
> - Tokens/sec: minimum **200 successful canary requests** AND **50,000 total generated tokens** per window.
> - If unmet: no alert state change allowed (plus sustained-breach 3/4 windows for paging).
> 
> **Incident-bot dedupe key:**
> `(model_id, model_version, region, hardware_sku, runtime_build_id, alert_type)` per the postmortem CPA. (ADR-0142 variant: `model_id + model_version + runtime_build_id + kernel_set_id + hardware_sku (+ region if present) + metric_type + severity`.)
> 
> Also required before re-enabling: 7-day warning-only bake (baseline hit-rate > 99.5%, no unexpected label growth, alert volume within noise budget), baseline-missing treated as "canary unhealthy" (not default-threshold fallback), alert rules aligned to evaluator grouping, and telemetry-delay suspension (>20 min lag).

</details>

<a id="case-enterprise_rag_bench-qst_0356"></a>

### enterprise_rag_bench:qst_0356 — 顺序安排扩大轮次，质量没有增益

**问题：** For the Acme AI dedicated failover incident with intermittent 500s and fallback churn, what v1 incident type and primary owner should we set, and what time-to-mitigate and time-to-fix targets should CS use in customer updates?

**score：4→4（Δ+0）；rounds：3→5（Δ+2）。**

两边均满分、无工具错误。naive 首轮并行查事故和责任/SLO 目标，第 2 轮并行读取后回答；community 首轮仅查事故，随后读取、再查 taxonomy/TTM/TTF、再读取，3→5 轮，工具仅 4→5，token 48,407→133,313。轮次差主要来自检索与读取的串行组织，加上更宽 overview 历史。首轮规划发生在社区注入之前，因此不能说社区反馈导致了最初的串行安排。

工具安排：naive 为第1轮2次、第2轮2次；community 为第1轮1次、第2轮1次、第3轮2次、第4轮1次。最终回答另占一轮。

轮次增加 2，工具总数 4→5、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 27→33、文档 overview 15→58；工具结果字符数 92,899→178,639，QA token 48,407→133,313。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/d079adcbe8964f8b98351d10ef095147.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/88ccd71b71c84bf29b45eadcea9a1264.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Acme AI dedicated failover incident intermittent 500s fallback churn","search_mode":"hybrid","doc_ids":null} | 12 | 9 | 0 | 成功 | D0279:0, D0279:3, D0279:1, D0279:2, D0236:0, D0259:0, D0112:0, D0116:0, D0266:0, D0113:0, D0104:0, D0108:0 |
| 2 | 1 | search_chunks {"query":"incident type primary owner time-to-mitigate time-to-fix targets CS customer updates","search_mode":"hybrid","doc_ids":null} | 12 | 6 | 0 | 成功 | D0079:0, D0292:0, D0078:0, D0079:1, D0079:5, D0023:0, D0078:1, D0025:3, D0067:3, D0292:3, D0079:6, D0067:0 |
| 3 | 2 | read_chunks {"doc_id":"D0079","ordinals":[2,3,4]} | 3 | 0 | 0 | 成功 | D0079:2, D0079:3, D0079:4 |
| 4 | 2 | read_chunks {"doc_id":"D0279","ordinals":[0,1,2]} | 3 | 0 | 0 | 成功 | D0279:0, D0279:1, D0279:2 |

judge reasoning：

> The generated answer fully matches the gold standard's incident type, contributing system, primary owner, and both CS targets, with only additional non-contradictory context.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Acme AI dedicated failover incident intermittent 500s fallback churn","search_mode":"hybrid","doc_ids":null} | 12 | 36 | 5 | 成功 | D0279:0, D0279:3, D0279:1, D0279:2, D0236:0, D0259:0, D0116:0, D0112:0, D0266:0, D0113:0, D0104:0, D0108:0 |
| 2 | 2 | read_chunks {"doc_id":"D0279","ordinals":[0,1,2,3]} | 4 | 0 | 0 | 成功 | D0279:0, D0279:1, D0279:2, D0279:3 |
| 3 | 3 | search_chunks {"query":"time to mitigate time to fix targets CS customer updates taxonomy v1 incident type","search_mode":"hybrid","doc_ids":null} | 12 | 19 | 2 | 成功 | D0079:0, D0292:0, D0078:0, D0080:0, D0023:0, D0079:1, D0292:3, D0191:0, D0023:4, D0025:3, D0025:0, D0261:1 |
| 4 | 3 | search_chunks {"query":"incident taxonomy v1 Capacity Fleet Shortage owner TTM TTF targets","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 1 | 成功 | D0079:6, D0080:0, D0079:5, D0193:1, D0193:0, D0079:3, D0079:4, D0079:0, D0193:2, D0193:3, D0292:0, D0279:2 |
| 5 | 4 | read_chunks {"doc_id":"D0079","ordinals":[1,2,5,6]} | 4 | 0 | 0 | 成功 | D0079:1, D0079:2, D0079:5, D0079:6 |

judge reasoning：

> The generated answer accurately captures the required incident type/subtype, primary owner, and TTM/TTF targets, matching the gold answer with only acceptable additional context.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Set incident_type/subtype to capacity_fleet.provisioning_lag (insufficient warm capacity during failover; note routing_fallback as a contributing system) with primary owner = Infrastructure/Fleet. For customer updates (Dedicated Sev1), use TTM target 45 minutes and TTF target 3 business days.

**naive 最终答案**

> Based on the incident (D0279) and the v1 ownership/SLA matrix (D0079):
> 
> **v1 incident type:** Capacity / fleet → Provisioning lag / autoscaler failure (regional warm capacity / provisioning lag) — with Routing as a contributing system.
> 
> **Primary owner:** Infrastructure/Fleet.
> 
> **CS targets for customer updates (Dedicated, Sev1):** Time-to-mitigate = 45 minutes; Time-to-fix = 3 business days (default Dedicated Sev1; the 10-business-day Regional GPU shortage override does not apply since this was warm-capacity provisioning lag, not a procurement-constrained shortage).

**community 最终答案**

> Based on the context:
> 
> **v1 incident type:** `capacity_fleet` → Capacity / fleet, subtype **Provisioning lag / autoscaler failure** (regional warm capacity / provisioning lag during failover). Routing/fallback churn is a contributing system, not the primary type.
> 
> **Primary owner:** **Infrastructure/Fleet** (Infra/Fleet), with Smart Routing as secondary/consulted.
> 
> **TTM/TTF targets for CS customer updates (Dedicated Sev1):**
> - **TTM: 45 minutes** (mitigation target)
> - **TTF: 3 business days** (durable fix)
> 
> Note: per the SLA matrix, these are internal remediation targets; CS customer updates should focus on the mitigation ETA and next update time rather than promising specific contract-bound SLA terms.

</details>

<a id="case-enterprise_rag_bench-qst_0359"></a>

### enterprise_rag_bench:qst_0359 — 规范与实现冲突没有形成稳定的权威优先级

**问题：** Can you reconcile the current public error contract for data residency policy blocks across the ADR, the gateway implementation, and the PM requirements, and confirm the exact HTTP status and error.code/subcode fields SDKs should key off of?

**score：3→2（Δ-1）；rounds：4→3（Δ-1）。**

两边都拿到 ADR-022 以及 gateway/PM 变体。naive 虽有一次越界读取，最终仍以 canonical subcode 契约给出分支建议；community 少一轮、无工具错误，却认为 subcode 不可协调并要求 SDK 不依赖它，3→2 分。这里的失分是规范/实现/需求稿之间的冲突裁决，不是缺少 error.code 文档。更完整的社区材料可能同时引入更多版本，但 trace 不能证明这些额外材料单独导致错误。检索后需明确权威、状态和适用版本，再将兼容处理与规范要求区分。

工具安排：naive 为第1轮2次、第2轮3次、第3轮2次；community 为第1轮2次、第2轮3次。最终回答另占一轮。

轮次减少 1，工具总数 7→5、错误 1→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 19→27、文档 overview 7→30；工具结果字符数 143,749→112,011，QA token 82,759→60,269。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

<details>
<summary>展开 judge 所提实体的字面证据核对</summary>

| 实体/术语 | naive工具中首次匹配 | naive答案 | community工具中首次匹配 | community答案 |
|---|---|---|---|---|
| subcode | 轮1/调用1/D0149:0 | 出现 | 轮1/调用1/D0149:0 | 出现 |

这里只检查指定字面串及字母数字边界，不评判上下文是否在讨论同一事实；未匹配不排除同义表述，出现也不代表正确采用。它用于区分“可能未召回”和“已出现但未展开”的复核入口，不能自动判定因果。

</details>

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/a46cc44886db49139bb9420eb4c97964.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/957d9807602d4b5c97f468b5b5f91977.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"data residency policy block error contract HTTP status error code subcode","search_mode":"hybrid","doc_ids":null} | 12 | 5 | 0 | 成功 | D0149:0, D0149:1, D0289:0, D0149:3, D0290:0, D0289:3, D0149:2, D0230:0, D0289:1, D0289:2, D0186:0, D0230:2 |
| 2 | 1 | search_chunks {"query":"ADR gateway implementation PM requirements data residency block SDK","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0290:1, D0149:0, D0290:2, D0176:0, D0290:0, D0186:1, D0289:0, D0289:3, D0289:1, D0186:0, D0014:0, D0289:2 |
| 3 | 2 | read_chunks {"doc_id":"D0186","ordinals":[2]} | 1 | 0 | 0 | 成功 | D0186:2 |
| 4 | 2 | read_chunks {"doc_id":"D0149","ordinals":[4]} | 1 | 0 | 0 | 成功 | D0149:4 |
| 5 | 2 | read_chunks {"doc_id":"D0290","ordinals":[3]} | 0 | 0 | 0 | Unknown chunk ordinal | — |
| 6 | 3 | search_chunks {"doc_ids":null,"query":"residency_policy_violation vs data_residency_policy_violation code naming inconsistency resolved","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0290:0, D0149:3, D0186:0, D0289:1, D0176:0, D0289:0, D0289:3, D0289:2, D0230:2, D0149:4, D0290:2, D0149:2 |
| 7 | 3 | search_chunks {"doc_ids":null,"query":"subcode region_not_allowed primary_region_unavailable residency_region_not_allowed final contract","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0149:1, D0149:3, D0149:2, D0289:0, D0289:2, D0149:0, D0289:1, D0290:0, D0230:0, D0186:2, D0186:0, D0289:3 |

judge reasoning：

> The generated answer correctly identifies the canonical 409/error.code=residency_policy_violation/error.subcode contract and SDK keying fields, but it omits the required handling for a missing subcode/retry behavior and hedges the reconciliation rather than fully asserting ADR-022 as the canonical contract.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"data residency policy block error contract","search_mode":"hybrid","doc_ids":null} | 12 | 15 | 2 | 成功 | D0149:0, D0289:0, D0289:3, D0186:0, D0290:0, D0289:1, D0149:1, D0289:2, D0230:2, D0290:1, D0290:2, D0230:0 |
| 2 | 1 | search_chunks {"query":"error.code subcode HTTP status SDK key off","search_mode":"hybrid","doc_ids":null} | 12 | 15 | 2 | 成功 | D0033:0, D0149:0, D0237:4, D0237:0, D0237:2, D0033:1, D0237:3, D0237:1, D0149:1, D0176:0, D0263:0, D0203:2 |
| 3 | 2 | read_chunks {"doc_id":"D0149","ordinals":[2,3,4]} | 3 | 0 | 0 | 成功 | D0149:2, D0149:3, D0149:4 |
| 4 | 2 | read_chunks {"doc_id":"D0186","ordinals":[1,2]} | 2 | 0 | 0 | 成功 | D0186:1, D0186:2 |
| 5 | 2 | read_chunks {"doc_id":"D0289","ordinals":[3]} | 1 | 0 | 0 | 成功 | D0289:3 |

judge reasoning：

> The answer correctly identifies HTTP 409 and error.code residency_policy_violation but incorrectly claims error.subcode is not reconcileable and SDKs should not key off it, contradicting the gold standard's requirement to branch on subcode and reconcile variants.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Canonical public contract remains ADR-022: residency policy blocks return HTTP 409 Conflict and use the standard error envelope with error.code="residency_policy_violation". SDKs should key primarily off error.code=="residency_policy_violation" (and 409) and then branch on error.subcode in {"region_not_allowed","primary_region_unavailable","policy_misconfigured"}; if subcode is missing, treat it as a generic residency_policy_violation and do not retry by default (except primary_region_unavailable may be retried with backoff without cross-region reroute).
> 
> Gateway enforcement is expected to emit the ADR-022 shape/status for both streaming and non-streaming requests (409 returned before any streaming bytes; if a stream has already started, it must terminate with a final structured error event rather than downgrading to a generic 5xx).
> 
> PM requirements introduced alternate top-level residency codes (e.g. "residency_region_not_allowed" and "residency_cross_region_fallback_blocked") and earlier gateway drafts referenced other variants; these should be reconciled to the ADR by keeping a single top-level error.code ("residency_policy_violation") and expressing the specific reason via subcode (region_not_allowed for targeted/outside allowed set, primary_region_unavailable for fallback-not-permitted/capacity cases, policy_misconfigured for invalid policy state). For robustness during rollout, SDKs may also treat any of the PM/gateway variant residency codes as equivalent to residency_policy_violation and map them onto the same ResidencyPolicyViolationError surface.

**naive 最终答案**

> Based on the documents, the pieces don't fully reconcile — there are real divergences, so let me lay them out.
> 
> **Consistent everywhere: HTTP status**
> - ADR-022 (D0149): **HTTP 409 Conflict** (MUST).
> - Gateway ticket (D0290): 409 per ADR-022.
> - PM requirements (D0289, R1): 409 MUST (403=authz, 422=input, 429=ratelimit).
> - SDK PR (D0176) and bug ticket (D0230): trigger on 409.
> So **HTTP 409 Conflict** is confirmed across ADR, gateway, and PM.
> 
> **Primary error code — NOT consistent:**
> - ADR-022 (source of truth): single stable `error.code = "residency_policy_violation"` + `error.subcode` of `region_not_allowed`, `primary_region_unavailable`, or `policy_misconfigured`.
> - Gateway ticket (D0290) and bug resolution (D0230) align with ADR: `error.code = residency_policy_violation` (no subcode mentioned).
> - Gateway PR (D0186) deviates: `error.code = "data_residency_policy_violation"`, `error.type = invalid_request_error`, and a `residency.reason` field (`target_region_not_allowed`, `fallback_not_permitted`, `policy_missing_primary_region`) — no `subcode`.
> - PM requirements (D0289) deviate differently: three distinct codes (`residency_policy_violation`, `residency_region_not_allowed`, `residency_cross_region_fallback_blocked`) and `error.type = policy_violation` — no subcode.
> - SDK PR (D0176) is code-family agnostic: raises `ResidencyPolicyViolationError` on 409 + any residency `error.code` (e.g. `RESIDENCY_POLICY_VIOLATION`), exposing error_code/request_id/help_url.
> 
> **Answer / confirmation for SDKs:**
> Per the authoritative published contract (ADR-022, which D0290, D0230, and D0176 implement), SDKs should key off:
> - **HTTP status 409 Conflict**
> - **`error.code == "residency_policy_violation"`** (the stable primary discriminant)
> - and discriminate the specific reason via **`error.subcode`** (`region_not_allowed`, `primary_region_unavailable`, `policy_misconfigured`), keying the `ResidencyPolicyViolationError` exception on 409 + the residency code family.
> 
> **However, the contract is not fully reconciled:** the gateway PR (D0186) and PM requirements (D0289) use alternative code schemes (`data_residency_policy_violation` / `residency.reason`, and three separate PM codes with no subcode) that do not match ADR-022's single-code-plus-subcode model. Those documents note open follow-ups (e.g., unifying help_url and code surface, docs alignment), so the exact code/subcode fields the SDKs should key off of are settled only if ADR-022's `residency_policy_violation` + `subcode` scheme is enforced over the D0186/D0289 variants — otherwise the SDK code-family matching in D0176 is the only stable, version-tolerant approach.

**community 最终答案**

> ## Reconciliation
> 
> **HTTP status: consistent — HTTP 409 Conflict** (all three sources agree; 403/422/429 explicitly excluded; not retried as a transient).
> 
> **error.code — reconciled value: `residency_policy_violation`.** This is what the production-verified gateway returns (SUP-28577 confirmed `error.code=residency_policy_violation` with `request_id`/`help_url`), matching ADR-022 and the gateway ticket. Note: the gateway PR's example used `data_residency_policy_violation` — a divergence from ADR that does not match the deployed/runtime code.
> 
> **error.subcode — NOT reconcileable.** Only ADR-022 defines a `subcode` field (`region_not_allowed`, `primary_region_unavailable`, `policy_misconfigured`). Neither the gateway implementation nor the PM requirements emit or require it:
> - Gateway emits only internal `residency.reason` values (`target_region_not_allowed`, `fallback_not_permitted`, `policy_missing_primary_region`) — different strings, and not exposed as `error.subcode`.
> - PM requirements instead define flat alternative codes (`residency_region_not_allowed`, `residency_cross_region_fallback_blocked`) rather than a subcode; it also sets `error.type=policy_violation`, while the gateway sets `invalid_request_error`.
> 
> So the three documents cannot be fully reconciled: they share HTTP 409 and the primary `residency_policy_violation` code, but disagree on the secondary discriminant (subcode vs. flat codes vs. reason codes).
> 
> ## What SDKs should key off of
> - **HTTP 409 Conflict** + **`error.code` in the residency family** (primary: `residency_policy_violation`), mapped to a dedicated `ResidencyPolicyViolationError` (Python/TS/Go), exposing `error_code`, `request_id`, `help_url` (and `http_status=409`). This is the deployed behavior confirmed in D0230 and implemented in D0176.
> - **Do not key off `error.subcode`**: it is specified only in ADR-022 and is not currently returned by the gateway or required by PM. Treat 409 residency blocks as non-retriable by default (per PM/SDK requirements); ADR-022 additionally permits backoff retry only for `primary_region_unavailable`, but that subcode is not present in the actual gateway payload.

</details>

<a id="case-enterprise_rag_bench-qst_0362"></a>

### enterprise_rag_bench:qst_0362 — 评分与执行路径对照

**问题：** What is our v1 standard for streaming timeout enforcement and retry behavior, and do any of the Python, TypeScript, or Go SDKs still violate it based on the parity matrix and recent support tickets?

**score：3→2（Δ-1）；rounds：3→2（Δ-1）。**

工具安排：naive 为第1轮2次、第2轮2次；community 为第1轮2次。最终回答另占一轮。

轮次减少 1，工具总数 4→2、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 29→19、文档 overview 10→24；工具结果字符数 124,732→88,257，QA token 55,674→26,761。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/2080c21caada45ff9cf8ee7a98f392ad.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/bbb9581f2e5b4c32b57c823a56ad095b.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"v1 standard streaming timeout enforcement retry behavior","search_mode":"hybrid","doc_ids":null} | 12 | 5 | 0 | 成功 | D0006:0, D0006:3, D0033:4, D0006:4, D0033:3, D0251:4, D0251:0, D0033:0, D0263:1, D0033:6, D0307:0, D0006:1 |
| 2 | 1 | search_chunks {"query":"parity matrix Python TypeScript Go SDK streaming timeout retry violation","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0033:0, D0033:7, D0175:0, D0251:2, D0033:4, D0246:2, D0033:3, D0307:0, D0307:3, D0006:0, D0033:1, D0303:0 |
| 3 | 2 | search_chunks {"query":"idle timeout TypeScript Go implemented conformance pass streaming","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0033:4, D0307:0, D0175:0, D0307:3, D0033:0, D0006:4, D0006:0, D0251:2, D0175:1, D0175:2, D0006:1, D0033:5 |
| 4 | 2 | search_chunks {"query":"Python SDK v0.18.0 streaming timeout resolved closed ticket","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0251:4, D0251:2, D0251:3, D0251:0, D0246:1, D0251:1, D0246:0, D0246:2, D0303:0, D0246:3, D0321:0, D0258:0 |

judge reasoning：

> The response captures the v1 streaming timeout/retry model and the TS/Go gaps well, but it omits key retry conditions (explicit client cancellation is never retried, retryable=false on post-output disconnects) and adds Python matrix flags not present in the gold answer, so it is good but not a perfect match.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"v1 standard streaming timeout enforcement retry behavior","search_mode":"hybrid","doc_ids":null} | 12 | 24 | 3 | 成功 | D0006:0, D0006:3, D0033:4, D0006:4, D0251:4, D0251:0, D0033:3, D0033:0, D0033:6, D0263:1, D0006:1, D0307:0 |
| 2 | 1 | search_chunks {"query":"parity matrix SDK violation streaming timeout retry","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0033:0, D0033:7, D0033:1, D0033:6, D0175:0, D0251:2, D0237:4, D0251:1, D0246:2, D0251:0, D0006:0, D0006:3 |

judge reasoning：

> The generated answer captures much of the v1 standard and TS/Go status, but it incorrectly suggests Python still has retry-policy inconsistencies and that all three SDKs still violate idle-timeout enforcement, while also omitting important conditions such as explicit client cancellation never being retried and the retryable=false flag on partial-output disconnect errors.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> V1 standard: streaming must be bounded by an overall_timeout_ms hard cap for the full lifecycle (including retries/backoff), plus a stream_idle_timeout_ms that limits time with no bytes/events (default 30000ms, resets on each valid chunk/event). Safety-first streaming retry: never auto-retry once any stream output has been delivered; retry is only allowed if the failure happens before the first byte/event (treating a pre-body 429/5xx/transport failure like a normal request, including honoring Retry-After), and explicit client cancellation is never retried. If a disconnect happens after partial output, the SDK must raise a typed streaming interruption error (retryable=false) with request_id when known and best-effort bytes/events received.
> 
> Based on the parity matrix + recent tickets: Python had a known violation where the streaming iterator ignored configured timeouts (SUP-29410) but this was fixed in redwood-sdk-python 0.18.0 and Python now passes the stalled-stream/streaming-timeout conformance coverage (older 0.17.x still violates). TypeScript still partially violates the v1 timeout model for streaming because idle timeout is not implemented, and it has had streaming edge-case drift (disconnect classification / post-content retry suppression) even though the specific pre-first-byte 429 case (retry + respect Retry-After) was recently fixed and now passes conformance; the earlier non-streaming 400 retry bug was also fixed in TS 2.8.2. Go is improved on v1 retry behavior (Retry-After on 429 is fixed in v0.10.0 and the streaming 429 Retry-After path was brought into conformance), and it is generally aligned on “no retry after events”, but it still partially violates streaming timeout enforcement because stream idle timeout is not consistent/fully implemented per the parity matrix.

**naive 最终答案**

> **v1 standard (streaming timeout + retry):**
> - **Streaming idle timeout**: `stream_idle_timeout_ms` default 30s — max idle time between bytes/events; resets on each valid chunk/event; `overall_timeout_ms` (90s) still applies to streaming.
> - **Retry behavior**: **no automatic retry after any partial output** — SDK must raise a typed streaming disconnect error with request_id, bytes/events received, partial-output flag, and attempt count; retry is allowed only **before the first byte/event** under the standard retry policy; docs must recommend idempotency keys and treat streaming retries as app-level decisions.
> 
> **Still violating (per parity matrix + recent tickets):**
> - **TypeScript**: stream idle timeout still **not implemented** (⚠️ abort cancels fetch, but no idle timeout); retried after some events in one streaming path; sometimes classifies post-content disconnects as retryable network errors.
> - **Go**: stream idle timeout **not consistent** (⚠️ context cancel works, but idle timeout inconsistent); disconnect classification ambiguous (EOF vs server close); historically ignored Retry-After in streaming (fixed in v0.10.0 / conformance now passes).
> - **Python**: streaming timeout ignoring (SUP-29410) was **fixed and closed** in v0.18.0 (overall/read timeouts enforced, typed `RedwoodTimeoutError`), but the matrix still flags pre-first-event retry inconsistency, generic disconnect errors, and partial text lost on mid-chunk exceptions.
> 
> Recent support tickets resolved the 429/Retry-After conformance failures for TS and Go (D0307), the Go Retry-After issue (D0263), and the Python streaming timeout hang (D0251); remaining open gaps are the TS/Go idle-timeout enforcement and streaming disconnect error/retry classification edge cases, plus typed-error rollout for proxy disconnects (D0246, in flight).

**community 最终答案**

> ## v1 Standard (D0006)
> 
> **Streaming timeout enforcement:**
> - `stream_idle_timeout_ms` default **30s** — max idle time between bytes/events; resets on each valid chunk/event
> - `overall_timeout_ms` default **90s** — hard cap that must still apply to streaming requests (even if per-attempt timeouts are higher/infinite)
> 
> **Streaming retry behavior (safety-first):**
> 1. **No automatic retry after partial output** — must raise a typed streaming disconnect error (request_id, bytes/events received, partial-output flag, attempt count)
> 2. **Retry allowed only before the first byte** (e.g., connect failure, TLS error, 503 before body) via the standard policy (max 4 attempts; 408/429/5xx/network; Retry-After honored)
> 3. Manual retry guidance: idempotency keys, log request_id/retry_count, app-level decisions
> 
> ## Violations per parity matrix (D0033) and tickets
> 
> **All three SDKs still show gaps in the parity matrix:**
> 
> - **Python:** ❌ streaming ignored `timeout` in the iterator path (SUP-29410) — but **resolved** by redwood-sdk-python **v0.18.0** (standardized timeout model, explicit overall/read enforcement for streaming). ⚠️ Streaming retry "may retry pre-first-event; inconsistent."
> - **TypeScript:** ⚠️ abort cancels fetch but **idle timeout not implemented**; ⚠️ "retried after some events in one path"; ⚠️ disconnects sometimes misclassified as retryable network errors. (Streaming 429/Retry-After conformance bug was fixed per D0307.)
> - **Go:** ⚠️ context cancel works but **idle timeout not consistent**; ⚠️ ambiguous EOF vs server-close classification. ✅ generally no retry after events. (Retry-After on 429 fixed in v0.10.0; streaming 429 conformance fixed per D0307.)
> 
> **Net:** Per the matrix, **all three still violate streaming idle-timeout enforcement** (Python historically, TS/Go currently not fully implemented), and **Python/TS still show streaming retry-policy inconsistencies** (pre-first-event / after-events). Recent support tickets resolved the Python streaming-timeout hang (v0.18.0) and the TS/Go streaming 429 Retry-After failures (conformance now passing), but the matrix still lists the remaining gaps above as of its last update.

</details>

<a id="case-enterprise_rag_bench-qst_0363"></a>

### enterprise_rag_bench:qst_0363 — 评分与执行路径对照

**问题：** Northbridge Bank reported that request log TTL was not being enforced in us-east and that audit log exports were missing key admin event types; what caused these issues and what customer-facing compliance pack artifacts should we provide to show both retention enforcement and audit log evidence are now correct?

**score：4→3（Δ-1）；rounds：2→2（Δ+0）。**

工具安排：naive 为第1轮2次；community 为第1轮2次。最终回答另占一轮。

两边均为 2 轮，但工具总数 2→2，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 22→23、文档 overview 11→38；工具结果字符数 76,066→106,458，QA token 22,163→29,125。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/c1bbc8710a9d49b49f8d8ad7271de60e.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/2084c52174cf43eab4eb9ff159b5261a.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Northbridge Bank request log TTL not enforced us-east audit log exports missing admin event types","search_mode":"hybrid","doc_ids":null} | 12 | 8 | 0 | 成功 | D0261:0, D0280:0, D0280:1, D0283:0, D0261:2, D0261:1, D0242:0, D0166:0, D0146:5, D0145:0, D0242:2, D0143:0 |
| 2 | 1 | search_chunks {"query":"compliance pack artifact retention enforcement audit log evidence","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0146:0, D0148:0, D0148:2, D0146:3, D0146:4, D0146:1, D0148:3, D0143:3, D0057:0, D0147:0, D0146:5, D0261:0 |

judge reasoning：

> The generated answer accurately captures both root causes and the remediation details, and it correctly describes the customer-facing compliance pack artifacts needed to demonstrate retention enforcement and audit log coverage, matching the gold answers' core meaning without contradictions.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Northbridge Bank request log TTL not enforced us-east audit log exports missing admin event types","search_mode":"hybrid","doc_ids":null} | 12 | 29 | 4 | 成功 | D0261:0, D0280:0, D0280:1, D0283:0, D0261:2, D0261:1, D0242:0, D0166:0, D0146:5, D0145:0, D0242:2, D0143:0 |
| 2 | 1 | search_chunks {"query":"compliance pack artifacts retention enforcement audit log evidence","search_mode":"hybrid","doc_ids":null} | 12 | 9 | 2 | 成功 | D0146:0, D0148:0, D0148:2, D0146:3, D0146:4, D0146:1, D0143:3, D0147:0, D0146:5, D0148:3, D0057:0, D0147:3 |

judge reasoning：

> The generated answer accurately identifies the root causes and fixes for both issues, but omits some specific customer-facing artifacts (e.g., audit_log_coverage_summary.pdf/json, retention_policy_change_history.csv) and is slightly imprecise on lag metrics, so it is good but not perfect.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Request/response log TTL in prod us-east was configured correctly (7 days) and there were no legal-hold exceptions, but purge enforcement fell behind after a telemetry DB maintenance window (index rebuild + higher delete latency). Deletion batches hit "context deadline exceeded", the purge framework retried and auto-throttled (reduced batch size/throughput), and a backlog accumulated (ttl_lag_seconds rose to ~3-5 days) until SRE ran a controlled on-demand backfill purge to (now - 7d) and temporarily increased purge worker concurrency with DB pressure guardrails (QPS/rows-per-minute caps, delete-latency alerts). By 2025-03-13 the backlog was cleared and >7d request logs were no longer queryable; concurrency was then reverted to normal.
> 
> Missing audit admin event types in the evidence export were caused by the audit-log-exporter using a stale, hardcoded event-type allowlist in the "Customer Evidence - Admin Actions" template, which filtered out RBAC role assignment and API key lifecycle events even though they existed in the source audit log store. A corrected export was produced immediately via a no-allowlist query path, and the exporter was then fixed (PR-612) to support explicit time-windowed exports with declared filters, updated templates to include RBAC and credential categories, and added manifest/header metadata showing applied filters; the fix was deployed and re-runs now include the missing events.
> 
> Customer-facing artifacts to provide (from the Baseline Compliance Reporting Pack or equivalent bundle):
> - Retention configuration: retention_policy_effective.json and retention_policy_change_history.csv (show request_logs.ttl_days=7, effective timestamps, and legal_hold disabled), plus retention_policy_readme.pdf if available.
> - Retention enforcement evidence: redacted Retention Controls Verification panels or exported metrics for us-east request_logs showing ttl_lag_seconds returning to normal (<~6h), purge_rows_deleted steady, purge_failures back to baseline, and (optionally) a brief customer-safe remediation timeline noting the 2025-03-10 maintenance and recovery by 2025-03-13.
> - Audit coverage and exports: audit_log_coverage_summary.pdf and audit_log_coverage_summary.json, plus a fresh time-windowed audit export in audit_logs.csv and/or audit_logs.jsonl generated with the updated templates (at minimum Admin/RBAC changes and API key lifecycle), accompanied by audit_logs_manifest.json (record counts, checksums, exporter/template version, and explicit applied filters) demonstrating RBAC changes and API key created/rotated/revoked events are present.

**naive 最终答案**

> ## Causes
> 
> **TTL not enforced in us-east (request/response logs):** Retention policy was correct (TTL=7d, no legal holds). The cause was a telemetry DB maintenance window (index rebuild) that slowed deletion batches; purge jobs hit "context deadline exceeded," auto-retried, throttled, and reduced batch size, creating a purge backlog. `ttl_lag_seconds` climbed to ~280k–420k seconds. It was remediated via a controlled backfill purge to now-7d and increased purge concurrency with DB-pressure guardrails; by 2025-03-13 logs >7 days were no longer queryable.
> 
> **Audit log exports missing admin events:** The `audit-log-exporter` report templates applied a stale hardcoded event-type allowlist that omitted RBAC role-assignment and API-key lifecycle events. Fixed by PR-612 (time-windowed exports, explicit event-type filters, refreshed templates including RBAC + api_key categories, and manifest metadata listing applied filters), deployed to prod; RBAC + api_key events are now included.
> 
> ## Customer-facing compliance pack artifacts to provide
> 
> Per the Baseline Compliance Pack / evidence-collection procedure, provide a customer-safe bundle (ZIP) showing both are correct:
> 
> 1. **Retention configuration export** (JSON + summary) showing effective policy TTL=7d with change history.
> 2. **Retention enforcement verification evidence** — dashboards/metrics showing TTL lag within threshold, purge success, failures, and backlog (purge health) after remediation (30-day incident follow-up window).
> 3. **Audit log export** (CSV/JSONL) re-run with the updated "Customer Evidence – Admin Actions" template over the requested window, now including RBAC + api_key event types, paired with a **manifest listing applied filters and event_type coverage** (and corrected export package as the workaround).
> 4. **Evidence checklist + manifest** (who/when/what, templates, timestamps) to tie config to enforcement.

**community 最终答案**

> **Root causes:**
> 
> 1. **TTL not enforced (us-east):** The retention policy itself was correct (7-day TTL, no legal holds). A telemetry DB maintenance window (index rebuild) slowed purge deletion batches, causing `context deadline exceeded` failures and automatic throttle/backpressure, so `ttl_lag_seconds` climbed to ~280k–420k and records >10 days old remained. Fix: controlled backfill purge to `now-7d` and increased purge concurrency (2→6) with DB-pressure guardrails; lag fell to ~12k sec and >7-day logs were no longer queryable by 2025-03-13.
> 
> 2. **Audit log exports missing admin event types:** The audit-log-exporter report templates applied a stale, hardcoded event-type allowlist that omitted RBAC role-assignment and API-key lifecycle events (`rbac.role_assignment.created/updated`, `api_key.created/revoked`) even though the events existed in the source store. Fix: PR-612 deployed time-windowed exports, explicit event-type filters, refreshed templates including RBAC + api_key categories, and manifest metadata listing applied filters; the "Customer Evidence - Admin Actions" template was re-run and confirmed to include those events.
> 
> **Customer-facing compliance pack artifacts to provide (per the Baseline Compliance Pack / Evidence Collection Procedure):**
> - **Retention configuration export** (JSON + change history): `retention-config_<org>_<date>.json` showing the effective 7-day TTL.
> - **Time-windowed audit log export** (CSV/JSONL) using the updated "Customer Evidence - Admin Actions" (or RBAC/API-key) template for the requested window, now including RBAC + credential lifecycle events.
> - **Retention enforcement verification evidence** (screenshots/exported metrics from the Retention Controls Verification dashboards): `ttl_lag_seconds` (p95 <24h), `purge_rows_deleted` trend, `purge_failures` (<1%), and backlog—documenting the maintenance event and remediation status.
> - **Evidence checklist + manifest** (`evidence_checklist.csv`/`evidence_manifest.json` / `manifest_<org>_<date>.txt`) recording window, templates, applied filters, timestamps, and sign-off.
> 
> These are packaged as `redwood-compliance-pack_northbridge-bank_dedicated_us-east-1_<date>_v<version>.zip` (customer-safe bundle only, no internal dashboards/incident notes).

</details>

<a id="case-enterprise_rag_bench-qst_0365"></a>

### enterprise_rag_bench:qst_0365 — 评分与执行路径对照

**问题：** Fast tier p99 is regressing in canary, what SLO targets and abort criteria apply and what rollback steps should we take? Which dashboards and reason codes should we use to confirm whether admission control or requeue behavior is causing it.

**score：2→2（Δ+0）；rounds：4→3（Δ-1）。**

工具安排：naive 为第1轮2次、第2轮3次、第3轮2次；community 为第1轮2次、第2轮3次。最终回答另占一轮。

轮次减少 1，工具总数 7→5、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 40→28、文档 overview 12→39；工具结果字符数 141,499→134,474，QA token 96,720→64,630。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/d024584a59e248a0adb95b5ee671846e.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/9bea2f2b73a7492696b1a3ff8cd86de5.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"fast tier p99 regression canary SLO target abort criteria rollback","search_mode":"hybrid","doc_ids":null} | 12 | 6 | 0 | 成功 | D0073:5, D0211:1, D0211:2, D0211:0, D0309:0, D0291:0, D0294:0, D0294:4, D0297:0, D0291:2, D0211:5, D0297:2 |
| 2 | 1 | search_chunks {"query":"admission control requeue reason codes dashboard","search_mode":"hybrid","doc_ids":null} | 12 | 5 | 0 | 成功 | D0309:0, D0291:0, D0293:3, D0293:0, D0190:0, D0309:1, D0170:0, D0286:0, D0293:4, D0298:3, D0286:2, D0309:2 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"fast tier SLO target p99 TTFT latency ms value threshold","search_mode":"hybrid"} | 12 | 1 | 0 | 成功 | D0090:1, D0090:2, D0090:0, D0291:0, D0073:4, D0294:0, D0090:3, D0073:1, D0291:1, D0073:0, D0294:4, D0090:4 |
| 4 | 2 | read_chunks {"doc_id":"D0294","ordinals":[1,2,3]} | 3 | 0 | 0 | 成功 | D0294:1, D0294:2, D0294:3 |
| 5 | 2 | read_chunks {"doc_id":"D0073","ordinals":[0,1,2,3,4]} | 5 | 0 | 0 | 成功 | D0073:0, D0073:1, D0073:2, D0073:3, D0073:4 |
| 6 | 3 | read_chunks {"doc_id":"D0211","ordinals":[3,4]} | 2 | 0 | 0 | 成功 | D0211:3, D0211:4 |
| 7 | 3 | read_chunks {"doc_id":"D0309","ordinals":[3,4]} | 2 | 0 | 0 | 成功 | D0309:3, D0309:4 |

judge reasoning：

> The generated answer correctly captures the fast-tier SLO targets and several key rollback/reason-code elements, but it omits important abort criteria (e.g., 5xx/timeout 2x baselines, queue-depth and cardinality guards) and includes some unsupported/incorrect claims such as stable latency with rising 429/503 indicating admission control is working, so it is only partially complete.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"fast tier p99 SLO target canary abort criteria rollback","search_mode":"hybrid","doc_ids":null} | 12 | 22 | 3 | 成功 | D0211:1, D0211:0, D0073:5, D0211:2, D0291:0, D0294:4, D0309:0, D0294:0, D0297:0, D0210:0, D0291:2, D0211:5 |
| 2 | 1 | search_chunks {"query":"admission control requeue reason codes dashboard p99 regression","search_mode":"hybrid","doc_ids":null} | 12 | 9 | 1 | 成功 | D0309:0, D0291:0, D0190:0, D0291:2, D0294:0, D0309:1, D0170:0, D0309:3, D0073:5, D0293:3, D0190:1, D0298:3 |
| 3 | 2 | read_chunks {"doc_id":"D0090","ordinals":[0,1,2]} | 3 | 8 | 1 | 成功 | D0090:0, D0090:1, D0090:2 |
| 4 | 2 | read_chunks {"doc_id":"D0294","ordinals":[1,2,3,4,5]} | 5 | 0 | 0 | 成功 | D0294:1, D0294:2, D0294:3, D0294:4, D0294:5 |
| 5 | 2 | read_chunks {"doc_id":"D0211","ordinals":[3,4]} | 2 | 0 | 0 | 成功 | D0211:3, D0211:4 |

judge reasoning：

> The generated answer correctly captures the fast tier SLOs, most abort criteria, and the general distinction between admission-control and requeue behavior, but it misses or alters key required details: it does not name the actual dashboards from the gold answers (e.g., Tiered Batching Executive Overview, Rollout/Canary Health, Scheduler Deep Dive) and gives different/invented reason-code and metric names for admission control, plus adds a fabricated abort criterion about any paging alert across regions. These are important omissions/inaccuracies for the specific question asked.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Fast tier SLO targets (reference workload envelope: p95 prompt tokens <= 2,048; p95 completion tokens <= 1,024; within per-model capacity guidance; non-streaming normalized at prompt=512/completion=256): streaming TTFT p99 900ms (p95 450ms); streaming inter-token latency p99 60ms/token (p95 35ms/token); non-streaming E2E p99 2.80s (p95 1.60s, p50 0.85s). (For context only: standard TTFT p99 1,200ms and E2E p99 3.80s; cost-efficient TTFT p99 2,000ms and E2E p99 7.00s.)
> 
> Canary abort / rollback criteria (runtime-1.22 rollout checklist): SEV-0 immediate kill switch if fast tier p99 latency regresses >= +25% vs baseline for 30 minutes in any canary region for top-3 models OR any single enterprise priority route; or 5xx >= 2x baseline for 15 minutes; or timeouts/cancellations >= 2x baseline for 15 minutes; or runaway/monotonic queue depth growth for >10 minutes with no recovery and admission control not stabilizing; or metric series cardinality above agreed cap for >10 minutes / ingestion cost spike to paging threshold. SEV-1 pause rollout + revert canary if standard tier p95 regresses >= +15% for 60 minutes; or streaming TTFT regresses >= +20% for 30 minutes; or increased 429/503 due to backpressure without corresponding improvement in tail latency; or Dedicated precedence bug is customer-impacting and reproducible.
> 
> Rollback steps (do scoped first if localized): 1) Scoped rollback: disable tiered defaults for the specific region and/or model_family and/or route (or Dedicated tenant) that is regressing; if only fast tier is problematic, force standard tier only for that scope as an intermediate mitigation. 2) If impact is broad or unclear, flip the global kill switch in control plane: tiered_batching_defaults_enabled=false to revert to legacy/previous batching behavior (propagates within the normal config window). 3) Validate rollback: confirm profile/tier selection telemetry shifts from tiered defaults to legacy/disabled (reason codes move away from tier_default_applied / tier_default and toward legacy/disabled modes), then allow ~10-20 minutes for queues to drain and confirm p99 and queue-wait histograms trend back toward baseline; confirm error rates (5xx, 429/503, timeouts/cancellations) normalize.
> 
> Dashboards to use (on-call path): start with "Tiered Batching: Executive Overview" for per-tier latency percentiles (streaming TTFT and decode token latency / ITL, and non-streaming request latency) plus queue health, batching efficiency, overload/admission signals, and reason-code distribution. For rollout deltas use "Tiered Batching: Rollout / Canary Health" (canary vs control p99/p95 deltas by tier, error deltas, telemetry cardinality guard). For root cause use "Tiered Batching: Scheduler Deep Dive" (prefill vs decode service time, max-wait budget utilization, head-of-line blocking / starvation indicators, continuous batching cycle time). If Dedicated/precedence is suspected, use the restricted "Tiered Batching: Dedicated Overrides and Precedence" dashboard.
> 
> Reason codes and metrics to distinguish admission control vs requeue behavior:
> - Admission control / overload driven: look for elevated redwood_scheduler_admission_reject_total with reason in {overload, queue_full, max_wait_exceeded, policy_denied} and for redwood_scheduler_overload_mode_active toggling to 1; correlate with increased 429/503 and/or drops in accepted RPS. In profile selection, expect selection reason_code shifting toward overload_mode or fallback_variant. Also check tier_source / tier_effective to confirm the tier did not silently change (tier_source should remain default/route_policy/customer_override rather than compatibility_fallback).
> - Requeue / scheduler loop driven (self-inflicted tail): p99 regresses while p50/p95 are stable, queue depth may be modest, but queue-wait percentiles and long-tail queue age increase; in logs/traces and scheduler events look for repeated requeue decisions with reasons like WAIT_BUDGET_EXCEEDED and PREFILL_BATCH_LOCKED (and any fast-tier deadline boost / starvation guard triggers if enabled). In this case admission_reject_total may stay low while queue_wait_seconds_bucket p99/p95 worsens and TTFT p99 inflates. Correlate with batching panels (batch tokens, batch size, fill ratio) and prefill lock / prefill duration indicators in Deep Dive to see if long-prefill batches are monopolizing the prefill lane.
> 
> Profile selection explainability counters to anchor investigation: redwood_batching_profile_selected_total grouped by tier and reason_code (tier_default, route_policy, customer_override, model_constraint, overload_mode, fallback_variant) plus the rollout checklist reason codes used in 1.22 for precedence/fallback auditing (tier_default_applied, route_policy_override, dedicated_tenant_override, model_constraint_fallback, overload_mode_enabled, streaming_protection_applied, guardrail_clamp). Use these to confirm whether the fast tier is actually being applied and whether a fallback/overload profile is being selected during the regression window.

**naive 最终答案**

> ## Fast tier SLO targets (canonical, D0090)
> Fast tier is SLO'd primarily on TTFT/ITL (streaming) and p99:
> - Streaming TTFT: p50 180 ms / p95 450 ms / **p99 900 ms**
> - Inter-token latency: p50 18 / p95 35 / **p99 60 ms/token**
> - Non-streaming E2E: p50 0.85 s / p95 1.60 s / **p99 2.80 s**
> - Paging alert: fast p99 TTFT or request latency above target for >10 min; admission rejects >1% for 10 min.
> 
> ## Abort criteria (D0211, D0073)
> - **SEV-0 (immediate kill switch):** fast tier p99 regression ≥ **+25% vs baseline for 30 min** in any canary region (top-3 models or any enterprise priority route); any paging alert sustained >10 min across ≥2 regions; telemetry ingestion >25% sustained 30 min.
> - **SEV-1 (pause + revert):** standard p95 ≥ +15% for 60 min; TTFT ≥ +20% for 30 min.
> - Canary-specific: fast-tier 429 rate >0.5% steady state, or sustained admission reject rate >1%, or p99 not improving (D0170/D0073).
> 
> ## Rollback steps (D0294, D0211)
> Use smallest blast radius first, then verify:
> 1. Per-route tier override (move route off fast).
> 2. Per-tenant override (Dedicated).
> 3. Disable tiered-batching defaults flag for cohort (region/model family) — or flip fast-tier protections kill switch (`scheduler.tiers.fast.enforce_wait_budget` / admission control off).
> 4. Global kill switch `tiered_batching_defaults_enabled=false` (reverts to legacy behavior).
> 5. Validate: reason codes switch away from `tier_default_applied`, latency returns toward baseline (allow 10–20 min queue drain), queue depth and error rates normalize. Monitor 30 min (or 2x peak window).
> 
> ## Confirming admission control vs requeue (D0294, D0073, D0309)
> Dashboards:
> - **"Tiered Batching: Queue & Backpressure"** / "Overload mode + backpressure": queue depth, queue wait, admission rejects/shed counters by reason, overload_mode gauge.
> - **"Tiered Batching: Scheduler Deep Dive"**: max-wait budget utilization, starvation guard triggers, head-of-line indicators.
> - **"Tiered Batching: Regression Triage" / Rollout-Canary Health**: current vs baseline p99 deltas.
> 
> Reason codes:
> - **Admission control:** `overload_admission_block` / `overload_shed`, `OVERLOADED_FAST_TIER`, reject reasons `overload | queue_full | max_wait_exceeded | policy_denied`, `tier.overload_mode.active`. Rising 429/503 with stable latency = admission control working.
> - **Requeue behavior:** `WAIT_BUDGET_EXCEEDED` → `action: requeue priority=normal`, `PREFILL_BATCH_LOCKED` → requeue, and `REQUEUE_DEADLINE_BOOST`. Queue flat but p99 rising, or repeated admit=false/requeue loops, = requeue storm, not admission control.
> 
> Note: in this specific canary (D0309), the diagnosis points to requeue behavior — logs show `WAIT_BUDGET_EXCEEDED`/`PREFILL_BATCH_LOCKED` requeues at normal priority causing requeue loops (p50/p95 flat, p99 blown to +45%), not admission control.

**community 最终答案**

> ## SLO targets (fast tier, D0090)
> - Streaming TTFT: p50 180ms / p95 450ms / **p99 900ms**
> - Streaming ITL: p50 18 / p95 35 / **p99 60 ms/token**
> - Non-streaming E2E: p50 0.85s / p95 1.60s / **p99 2.80s**
> 
> ## Abort criteria (D0211, D0073)
> - **SEV-0 (kill switch):** fast tier p99 regression **≥ +25% vs baseline for 30 min** in any canary region (top-3 models or any enterprise priority route); 5xx ≥ 2x baseline for 15 min; timeouts/cancellations ≥ 2x baseline for 15 min; runaway queue depth > 10 min; cardinality over cap > 10 min.
> - **SEV-1 (pause + revert):** streaming TTFT regression ≥ +20% for 30 min; increased 429/503 with no tail-latency improvement.
> - **Green gates:** fast p99 TTFT and p99 latency must not exceed SLO targets; no sustained admission reject rate > 1%.
> - Also: any paging alert sustained > 10 min across ≥ 2 regions → immediate rollback.
> 
> ## Rollback steps (D0294, D0211) — smallest blast radius first
> 1. Per-route tier override (Console/policy)
> 2. Per-tenant override (Dedicated)
> 3. Disable tiered-defaults feature flag for the cohort (region/model family)
> 4. Global kill switch: `tiered_batching_defaults_enabled=false` (control plane) → legacy batching
> 
> Then: capture incident window + impacted dimensions; snapshot p99, TTFT, queue depth, batch-size, shed counters; confirm reason codes switch from `tier_default_applied` to disabled; monitor 30 min (or 2x traffic peak) until latency, queue depth, and error rates return to baseline (allow 10–20 min for queue drain).
> 
> ## Confirming admission control vs requeue behavior
> **Dashboards (D0190, D0294):** "Tiered Batching — Queue & Backpressure" (queue depth, queue wait, admission rejects, shed/load-shed counts, overload-mode indicator), "Tiered Batching — Latency & Streaming" (TTFT), "Tiered Batching — Regression Triage" (current vs baseline p99, top offenders), plus "Scheduler health" (queue depth, admission rejects).
> 
> **Reason codes:**
> - Admission control/overload: `overload_admission_block`, `overload_shed`, `tier.overload_mode.active` / `overload_mode_enabled` (HTTP 429/503)
> - Requeue behavior: `WAIT_BUDGET_EXCEEDED`, `PREFILL_BATCH_LOCKED` (with requeue at normal priority → requeue loops), `REQUEUE_DEADLINE_BOOST` (mitigation)
> 
> **Distinguishing signals (D0294, D0309):** rising 429/503 with stable latency = admission control working (fail-fast); rising latency without shedding = admission control not triggering (overload/regression). If queue depth is flat but p99 rises, it's a scheduler/requeue issue rather than overload — e.g., `WAIT_BUDGET_EXCEEDED` requeues + `PREFILL_BATCH_LOCKED` causing requeue storms (the qwen2.5-32b case: p99 +45%, p50/p95 flat, queue depth avg 3–5). Also validate metrics pipeline health first, since cardinality blow-ups can masquerade as latency regressions.

</details>

<a id="case-enterprise_rag_bench-qst_0366"></a>

### enterprise_rag_bench:qst_0366 — 评分与执行路径对照

**问题：** A non-burst Dedicated tenant is seeing tail latency spikes during another tenant's burst window; what should we check first, and when do we reduce burst caps versus trigger the SLO gate or circuit breaker, and what denial reason code will burst customers see?

**score：2→3（Δ+1）；rounds：2→2（Δ+0）。**

工具安排：naive 为第1轮2次；community 为第1轮2次。最终回答另占一轮。

两边均为 2 轮，但工具总数 2→2，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 22→22、文档 overview 8→34；工具结果字符数 77,223→104,450，QA token 22,418→28,938。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/e45d353d0f374decbb6292a7de1fc26e.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/2c1fb17c82b64c6f9cf274d6d345c484.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"burst window non-burst dedicated tenant tail latency SLO gate circuit breaker","search_mode":"hybrid","doc_ids":null} | 12 | 6 | 0 | 成功 | D0087:0, D0298:0, D0182:0, D0182:1, D0298:1, D0082:2, D0317:0, D0082:1, D0087:4, D0087:1, D0133:3, D0182:2 |
| 2 | 1 | search_chunks {"query":"denial reason code burst customers","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0293:3, D0293:0, D0082:4, D0293:2, D0082:1, D0133:4, D0133:0, D0214:2, D0133:6, D0293:4, D0082:0, D0087:4 |

judge reasoning：

> The generated answer misses the critical first step of verifying that the non-burst tenant remained isolated (routing/policy audit logs, capacity attribution, burst_enabled=false, no cross-tenant placement), and it omits the full set of binding guardrail denial codes, though the mitigation order and main SLO_GATED/FLEET_SAFETY_CIRCUIT_OPEN codes are largely correct.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"burst window tail latency spikes Dedicated tenant","search_mode":"hybrid","doc_ids":null} | 12 | 34 | 4 | 成功 | D0249:0, D0249:1, D0087:0, D0214:1, D0317:0, D0133:0, D0298:0, D0082:1, D0133:1, D0249:3, D0082:0, D0249:2 |
| 2 | 1 | search_chunks {"query":"reduce burst caps versus SLO gate circuit breaker denial reason code","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0082:2, D0298:0, D0298:1, D0293:3, D0182:0, D0188:0, D0087:3, D0082:5, D0214:0, D0087:4, D0182:2, D0087:0 |

judge reasoning：

> The generated answer correctly captures the core diagnostic order, the reduce-caps-to-SLO-gate-to-circuit-breaker mitigation sequence, and the primary denial codes, but it introduces ungrounded/possibly inconsistent thresholds and an extra denial code not present in the gold answer, so it is good but not perfect.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> First confirm this is not "burst traffic spilled onto their GPUs": check routing/policy audit logs and capacity attribution that the non-burst tenant remained pinned to its reserved dedicated pool (burst_enabled=false, no fallback/override events, per-node tenant tags show no cross-tenant placement). If isolation is intact, look next for shared-path coupling that can create head-of-line blocking during a burst window: router/ingress queue depth and CPU, scheduler boundary queueing, and especially admission/policy evaluation health (p99 admission decision latency, timeouts, CPU throttling) since some implementations still do a shared capability/policy fetch even for non-burst routes. Also check telemetry freshness/lag, since over-admission (or late denials) can push shared control-plane and routing components into contention even if GPUs are isolated.
> 
> Mitigation order is baseline-first. If you see early or moderate neighbor impact, immediately reduce burst pressure in the impacted region/hardware pool (tighten fleet safety cap / lower effective max_burst_ratio, clamp top-talker tenant burst caps, increase cooldown, and if needed pause the specific sustained-burst tenant) to bring router/admission load down quickly. If non-burst p95/p99 regression crosses the guardrail and is sustained, the SLO regression gate should flip from ALLOW to REDUCE (clamp burst ratio) and then to DISABLE if severe or if it persists past the configured window; if the regression remains after reduction or admission/router health is clearly unstable, engage the regional circuit breaker / disable burst for that region+hardware to hard-stop new burst admissions.
> 
> Burst customers will see denial reason SLO_GATED when the SLO gate is active. If the fleet safety circuit breaker is open they will see FLEET_SAFETY_CIRCUIT_OPEN (some surfaces/logs may label this as GLOBAL_CIRCUIT_OPEN); otherwise denials will show the binding guardrail such as POOL_SATURATED, FLEET_SAFETY_CAP, TENANT_BURST_CAP_REACHED, COOLDOWN_ACTIVE, or ADMISSION_TIMEOUT/TELEMETRY_STALE when control-plane signals are degraded.

**naive 最终答案**

> **Check first:** Confirm the impacted pool key (`region/hardware_class`), verify the tail-latency regression is actually correlated with burst activity (Neighbor Impact dashboard: non-burst vs burst latency deltas, tail amplification), check whether the circuit breaker/SLO gate is already active, and identify top talkers + denial reason codes. Likely causes: fleet safety cap not tight/fast enough, poor baseline/burst isolation, or telemetry lag causing oversubscription.
> 
> **When to do what (least-disruptive first):**
> - **Reduce burst caps** (lower max burst ratio globally, cut per-tenant caps, increase cooldown) — first step when non-burst latency SLO is regressing.
> - **SLO gate** — automatically enters REDUCE (clamps `max_burst_ratio`) when non-burst p95/p99 regression exceeds threshold for `enter_window` (~3m), and DISABLE (denies new burst) when regression is severe or persists past `disable_after` (~10m).
> - **Circuit breaker (hard stop)** — when pool safety caps are exceeded, telemetry is stale (fail-closed), or neighbor impact persists. Decision rule: if non-burst p95 is above SLO threshold for >10 minutes and correlated with burst activity, move to hard stop unless there's a clear fast fix.
> 
> **Denial reason codes burst customers see:** `SLO_GATED` / `NEIGHBOR_SLO_GATE` when the SLO gate reduces/disables burst; `FLEET_SAFETY_CIRCUIT_OPEN` when the fleet circuit breaker is open.

**community 最终答案**

> **Check first:** Confirm the non-burst tenant's traffic never spilled onto burst GPUs (routing/policy still pinned to dedicated pool), then check the shared control-plane path — router queue depth, admission-controller decision latency, and burst pool saturation/telemetry freshness. In the documented incident, the root cause was a shared routing dependency (non-burst routing still hit the same policy/admission evaluation service), so tail latency tracked router queue depth more than GPU busy time.
> 
> **Reduce caps vs. SLO gate vs. circuit breaker (least disruptive first):**
> - **Reduce burst caps** first (lower max burst ratio/per-tenant caps, increase cooldown) — Step 1–2 mitigation.
> - **SLO gate**: automatically enters REDUCE when non-burst p95/p99 regression exceeds threshold for the enter window (default 3m), and DISABLE after a higher threshold or persistence (default 10m).
> - **Circuit breaker / hard stop**: when pool stability is at risk, admission controller is unhealthy, or neighbor impact persists — runbook rule: if non-burst p95 is above SLO threshold for >10 minutes correlated with burst, hard-stop unless a fast fix exists; automated cap reduction escalates to circuit breaker if regression persists >30 min.
> 
> **Denial reason codes burst customers will see:** `SLO_GATED` when the SLO gate reduces/disables burst, and `FLEET_SAFETY_CIRCUIT_OPEN` (a.k.a. `GLOBAL_CIRCUIT_OPEN`) when the circuit breaker is open. Related codes include `POOL_SATURATED`, `NEIGHBOR_SLO_GATE`, and `FLEET_SAFETY_CAP`.

</details>

<a id="case-enterprise_rag_bench-qst_0367"></a>

### enterprise_rag_bench:qst_0367 — 评分与执行路径对照

**问题：** For an enterprise ticket like SUP-1842 where streaming disconnects happen in us-east, when should we escalate from a Support bridge to a formal incident and post a status page update, and what customer update cadence and credits wording should we use?

**score：2→3（Δ+1）；rounds：3→3（Δ+0）。**

工具安排：naive 为第1轮2次、第2轮2次；community 为第1轮2次、第2轮2次。最终回答另占一轮。

两边均为 3 轮，但工具总数 4→4，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 35→26、文档 overview 15→36；工具结果字符数 142,468→113,058，QA token 57,207→58,074。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

<details>
<summary>展开 judge 所提实体的字面证据核对</summary>

| 实体/术语 | naive工具中首次匹配 | naive答案 | community工具中首次匹配 | community答案 |
|---|---|---|---|---|
| SLA | 轮1/调用1/D0243:1 | 出现 | 轮1/调用1/D0243:1 | 出现 |

这里只检查指定字面串及字母数字边界，不评判上下文是否在讨论同一事实；未匹配不排除同义表述，出现也不代表正确采用。它用于区分“可能未召回”和“已出现但未展开”的复核入口，不能自动判定因果。

</details>

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/cab57e52376c4ae7bd2464601c3ec350.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/2facea36067e44d587beddedff0ee4d0.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"SUP-1842 streaming disconnects us-east escalation incident","search_mode":"hybrid","doc_ids":null} | 12 | 5 | 0 | 成功 | D0243:1, D0243:3, D0197:4, D0243:2, D0243:0, D0197:1, D0022:2, D0246:0, D0197:0, D0197:2, D0233:3, D0022:0 |
| 2 | 1 | search_chunks {"query":"escalate support bridge to formal incident status page update","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0022:2, D0022:4, D0124:5, D0022:3, D0124:0, D0124:4, D0025:1, D0022:0, D0023:2, D0124:2, D0026:0, D0023:5 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"Enterprise P0 P1 update cadence 30 minutes 60 minutes status page","search_mode":"hybrid"} | 12 | 2 | 0 | 成功 | D0100:0, D0023:5, D0023:2, D0124:2, D0025:1, D0023:0, D0026:0, D0025:0, D0026:4, D0023:1, D0026:1, D0122:0 |
| 4 | 2 | search_chunks {"doc_ids":null,"query":"stream resets telemetry threshold escalate status page region degradation 10 minutes","search_mode":"hybrid"} | 12 | 4 | 0 | 成功 | D0243:1, D0243:0, D0279:0, D0124:4, D0091:3, D0026:2, D0026:3, D0243:3, D0103:0, D0197:1, D0305:0, D0023:2 |

judge reasoning：

> The generated answer captures many correct escalation triggers, P0/P1 cadences, and the core 'no credit promises/no SLA admissions' wording, but it omits important conditions (tier-critical/SLA-impact escalation, 15-minute persistence trigger, timeout threshold, and next-update-time requirement) and incorrectly states VP CS rather than CS leadership approval for credits.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"SUP-1842 streaming disconnects us-east escalation formal incident","search_mode":"hybrid","doc_ids":null} | 12 | 36 | 4 | 成功 | D0243:1, D0243:3, D0243:2, D0197:4, D0243:0, D0197:0, D0022:2, D0197:1, D0022:0, D0197:2, D0246:0, D0233:3 |
| 2 | 1 | search_chunks {"query":"escalate Support bridge to formal incident status page update criteria","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0124:5, D0022:2, D0124:2, D0022:4, D0025:1, D0022:3, D0124:0, D0124:1, D0022:0, D0023:2, D0026:0, D0023:5 |
| 3 | 2 | read_chunks {"doc_id":"D0023","ordinals":[0,1]} | 2 | 0 | 0 | 成功 | D0023:0, D0023:1 |
| 4 | 2 | read_chunks {"doc_id":"D0124","ordinals":[3,4]} | 2 | 0 | 0 | 成功 | D0124:3, D0124:4 |

judge reasoning：

> The generated answer correctly captures the core escalation, cadence, and credits-wording guidance, but omits some specific SUP-1842 details like the Wednesday, Feb 11 decision timeline and slightly misstates approval routing (VP CS vs CS leadership/Jasmine Liu/Rachel Kim).

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Escalate from a Support bridge to a formal incident (#incidents) and open a status page incident when the issue is no longer customer-specific triage and meets any of the comms-alignment criteria (default to YES unless explicitly waived by IC + CS leadership). Concretely, move to #incidents and treat as incident-worthy if any are true: (1) suspected or confirmed multi-customer impact (2+ customers with the same symptom in the same region/model within 60 minutes, or duplicate inbound volume), (2) evidence or strong suspicion of regional/service degradation even if only one enterprise customer reported first, based on telemetry such as streaming resets/truncations >= 0.5% of streams for 10 minutes, 5xx >= 2% for 10 minutes, timeouts >= 1% for 10 minutes, or p95 latency >= 2x baseline for 15 minutes (do not wait for perfect metrics if impact is credible), (3) mitigation requires coordinated on-call action that changes production behavior (rollback, traffic shift, routing/fallback changes, capacity moves) or you need cross-team coordination/comms roles, (4) tier-critical impact (Enterprise/Dedicated/Private) where SLA or credits concerns are expected, or (5) impact persists beyond ~15 minutes without quick mitigation (if uncertain, open a cautious "Investigating" status incident). Once in #incidents, keep the Support bridge only for customer-specific coordination and mirror the IC as the source of truth.
> 
> Customer update cadence for Enterprise: if P0, first response within 15 minutes (24/7) and meaningful updates every 30 minutes while active; if P1, first response within 30 minutes (24/7) and updates every 60 minutes while actively mitigating. For any declared incident, mirror the IC/comms lead cadence and always include the next update time; if you are blocked or there is no change, still send a time-based "still investigating/monitoring, next update at X" update.
> 
> Credits wording: do not promise credits and do not write "SLA breach" or any admission of fault. Use: "If youd like to request service credits per your agreement, were reviewing the incident timeline and observed impact against the applicable SLA terms and can confirm any applicable credits once the impact assessment is finalized." For SUP-1842 specifically, if pressed, commit only to a decision timeline: "Well get back to you by Wednesday, Feb 11." Any goodwill credit or credit amount requires CS leadership approval (Jasmine Liu; coordinate via Rachel Kim) and route any contract interpretation to Legal (Sofia Mendes); default credit application is a billing adjustment on the next invoice unless CS leadership explicitly approves mid-cycle.

**naive 最终答案**

> **Escalate from bridge to formal incident (#incidents) when any of these are true** (per D0022/D0305/D0124/D0026):
> - Suspected service/regional degradation (elevated 5xx, latency, timeouts, stream resets) — even if only one customer reported it; don't wait for a second customer if dashboards/synthetics show a problem
> - Multi-customer or multi-region impact
> - Streaming health trigger: stream resets/truncations ≥0.5% of streams for 10 min (or sudden step-function increase); also 5xx ≥2% / p95 ≥2x baseline
> - Needs coordinated mitigation (rollback, traffic shift, config change) affecting production, or status-page/comms decision, or cross-team paging
> 
> For a P0/P1 Enterprise case like SUP-1842: page immediately, start bridge within 15 min, notify CS lead, consider exec escalation.
> 
> **Status page:** IC + Support Lead decide within 10 minutes of confirmation; if uncertain, default to opening a status incident ("Investigating"). For region degradation (Hosted) open within 10 min of confirmation. Status page is expected for P0/Sev0–Sev1. Don't include customer names, contract terms, or credit decisions on the status page.
> 
> **Customer update cadence (Enterprise):**
> - P0: first response in 15 min (24/7), updates every 30 min; bridge within 15 min
> - P1: first response in 30 min, updates every 60 min while actively mitigating
> - In practice (SUP-1842): every ~60 min during active mitigation, hourly once stable; internal bridge updates every 30 min for P0/P1
> 
> **Credits wording:** Don't proactively offer/promise credits in the same note as mitigation. If pressed: *"We take this seriously and will evaluate service credits per your agreement once we finalize the incident timeline and impact assessment. We'll get back to you by [date]."* Do not label it an "SLA breach" in Support comms — route to CS + Legal/Finance. You may say: *"We experienced a service degradation impacting streaming stability in us-east"* and *"We're reviewing your request under our service credit policy."* Any goodwill credit beyond contractual credits requires VP CS approval and should be documented as goodwill, not SLA admission. Avoid "root cause confirmed"/"permanently fixed"; use "mitigation applied; metrics back to baseline; monitoring closely; RCA within 5 business days."

**community 最终答案**

> **Escalation from Support bridge to formal incident (#incidents):** Move when any of the following is true (D0022): suspected multi-customer or multi-region impact; error rate/latency suggests service degradation/outage; you need coordinated rollback/mitigation affecting production; you anticipate needing a status page update; or you need structured IC + comms-lead roles. Don't wait for a second customer report if dashboards/synthetics show a problem (D0305).
> 
> **Status page update:** Post when any "YES" criterion is met (D0124): multi-customer impact, **critical-tier (Enterprise/Dedicated/Private) impact where SLA concerns are expected even with limited blast radius** (applies to SUP-1842's enterprise customer), or externally noticeable regional degradation. Likely YES if impact persists >15 min without quick mitigation, or you're doing traffic shifts/rollbacks. IC + Support Lead decide within 10 minutes of confirmation; when uncertain, default to opening a status incident with cautious "Investigating" language.
> 
> **Update cadence (Enterprise, 24/7):** P0 — first response in 15 min, updates every 30 min; P1 — first response in 30 min, updates every 60 min while actively mitigating (D0023). Per the SUP-1842 notes: 30–60 min during active mitigation, then hourly once stable (D0243). Status page/Sev-1: initial ack within 10 min, updates every 30 min, resolution within 15 min, post-incident summary within 1 business day (D0100). Keep comms aligned between emails and status page, and include next update time.
> 
> **Credits wording:** Do not confirm "SLA breach" in Support comms — route formal SLA determination to CS/Legal/Finance (D0243, D0195). Do not proactively promise credits. Approved language: "We experienced a service degradation impacting streaming stability in us-east" and "We're reviewing your request under our service credit policy" (Sofia Mendes, D0243), or "If you'd like to request service credits per your agreement, we can evaluate once we finalize the incident timeline and impact assessment" (D0197). Any goodwill credit must be VP CS-approved and documented as goodwill, not an SLA admission (D0243).

</details>

<a id="case-enterprise_rag_bench-qst_0369"></a>

### enterprise_rag_bench:qst_0369 — 评分与执行路径对照

**问题：** Why were some Hosted API overload errors missing Retry-After, and what changes and alerts ensure it stays consistent across gateway, routing, and streaming paths going forward?

**score：2→3（Δ+1）；rounds：2→2（Δ+0）。**

工具安排：naive 为第1轮2次；community 为第1轮2次。最终回答另占一轮。

两边均为 2 轮，但工具总数 2→2，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 20→19、文档 overview 11→26；工具结果字符数 75,532→93,580，QA token 21,631→25,745。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

<details>
<summary>展开 judge 所提实体的字面证据核对</summary>

| 实体/术语 | naive工具中首次匹配 | naive答案 | community工具中首次匹配 | community答案 |
|---|---|---|---|---|
| SRE | 轮1/调用1/D0011:0 | 出现 | 轮1/调用1/D0011:0 | 未匹配 |

这里只检查指定字面串及字母数字边界，不评判上下文是否在讨论同一事实；未匹配不排除同义表述，出现也不代表正确采用。它用于区分“可能未召回”和“已出现但未展开”的复核入口，不能自动判定因果。

</details>

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/e70dcab62482453e802e46aed7970e76.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/26f2bea310d14ada84009b85210d9c9d.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Hosted API overload errors missing Retry-After header","search_mode":"hybrid","doc_ids":null} | 12 | 6 | 0 | 成功 | D0268:0, D0011:0, D0168:0, D0268:1, D0028:0, D0168:1, D0268:2, D0028:3, D0028:4, D0247:0, D0263:0, D0263:1 |
| 2 | 1 | search_chunks {"query":"Retry-After consistency gateway routing streaming paths alert","search_mode":"hybrid","doc_ids":null} | 12 | 5 | 0 | 成功 | D0168:0, D0013:0, D0168:1, D0203:1, D0290:0, D0263:1, D0268:0, D0263:2, D0019:1, D0247:2, D0019:3, D0103:0 |

judge reasoning：

> The generated answer correctly explains the root cause and core fixes, but omits important details from the gold answer such as the retry_after_ms fallback for SSE streams already in progress, the rate-limit (429) overload classification codes, and the specific 98% presence-rate SRE alerting/rollback criteria.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Hosted API overload error Retry-After missing","search_mode":"hybrid","doc_ids":null} | 12 | 21 | 3 | 成功 | D0268:0, D0011:0, D0028:0, D0168:1, D0168:0, D0268:1, D0028:4, D0011:2, D0247:1, D0268:2, D0247:0, D0028:3 |
| 2 | 1 | search_chunks {"query":"Retry-After consistency gateway routing streaming alert","search_mode":"hybrid","doc_ids":null} | 12 | 5 | 1 | 成功 | D0168:0, D0268:0, D0013:0, D0263:2, D0168:1, D0203:1, D0103:0, D0019:3, D0247:1, D0247:2, D0268:2, D0263:1 |

judge reasoning：

> The generated answer correctly captures the main causes and fixes across gateway/routing/streaming, but omits some important alerting details (e.g., the 98% presence-rate SRE page and rollout/rollback criteria) and some specifics from the gold answer, so it is good but not perfect.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> They were missing because the gateway only set Retry-After on overload responses it generated itself (admission control / breaker paths). When overload was triggered downstream (routing or serving runtime) those services returned the correct overload JSON (overload_error / stable error.code) but often did not set headers, and the gateway sometimes passed the response through without normalizing headers. A related edge case was streaming: once an SSE response has started and headers are committed, the gateway cannot reliably add Retry-After, so late overload termination could not fix the header.
> 
> The fix was to centralize overload response construction and header normalization in the gateway: for any response mapped/classified as a retryable overload or rate limit condition (per ADR-014 codes like overload_shed / overload_circuit_open / overload_queue_full / overload_dependency_unavailable, and 429 codes like rate_limit_exceeded / concurrency_limit_exceeded), the gateway now sets Retry-After (integer seconds) unless it is already present, while preserving the downstream error.code/message. Correlation IDs were also tightened so clients always get a stable request id (prefer inbound X-Request-ID if provided, otherwise generate one) and the gateway echoes it back (with X-Redwood-Correlation-ID additive during the deprecation window). For streaming, the gateway ensures overload admission/rejection happens before initiating the stream so the HTTP error includes Retry-After; if streaming is already underway, the contract is to provide retry_after_ms in the terminal SSE error event instead of relying on headers.
> 
> Going forward, consistency is guarded by explicit observability and canary gates: the gateway emits a retry-after-missing counter (api_gateway.overload.retry_after_missing, with route_group/region/status dimensions) and a presence-rate view, and SRE alerting pages when retry_after_present_rate drops below 98% over 15 minutes for overload-classified responses (with absent-metric guards for regions not yet fully deployed). These checks are part of the rollout/rollback criteria so regressions in Retry-After or correlation headers stop expansion and trigger rollback before they impact more tenants.

**naive 最终答案**

> ## Why Retry-After was missing
> 
> Retry-After was only set on overload responses generated **directly by the gateway's admission-control middleware**. When overload originated from the **downstream routing/runtime path** (e.g., chat/completions, some streaming routes), those services returned the correct overload JSON payload but the gateway **passed the body through without applying header normalization**, so no Retry-After was added. Result: gateway shed 429s had the header, downstream 503s often didn't.
> 
> ## Changes ensuring consistency
> 
> 1. **Gateway normalization (PR-18472):** The gateway now applies a post-processing step that sets/overwrites Retry-After on **any response classified as overload** (`overloaded`, `breaker_open`, `dependency_overloaded`) regardless of origin, unless already present — while preserving the downstream error code/message. Shipped via hotfix under the `overload_protection.retry_after_normalization` flag, rolled out staging → us-east canary → full us-east + eu-west.
> 2. **Shared helper:** Overload response construction is centralized so status, error code/message, retry guidance, and request_id are emitted consistently across gateway, routing, and runtime paths.
> 3. **Streaming (SSE):** Overload rejection is ensured to happen **before the stream is initiated/headers committed** (since Retry-After can't be added after the response is committed).
> 4. **Correlation IDs:** Standardized X-Request-ID / X-Redwood-Correlation-ID plumbing for tracing across all paths.
> 5. **Guardrail:** A test guarantees generic (non-overload) 5xx never gets Retry-After.
> 
> ## Alerts monitoring consistency
> 
> - New canary safety metric: **`api_gateway.overload.retry_after_missing`** counter (dimensions: route_group, region, status; no tenant_id) — wired into logging when the helper isn't used, expected to stay at 0, and alerts if it regresses. SRE monitors sampled logs to confirm headers are present on overload responses (gateway + downstream) with no increase in 5xx, unchanged shed rate, and stable p99.

**community 最终答案**

> **Why missing:** Retry-After was only set by gateway admission-control rejects. Overload responses originating downstream (routing/runtime) returned the correct overload JSON but were passed through without header normalization. For streaming (SSE), once headers are committed Retry-After can't be added, so overload rejection had to happen before the stream starts.
> 
> **Changes going forward:** The gateway now normalizes all overload-classified responses (overloaded, breaker_open, dependency_overloaded) to set Retry-After (unless already present) and consistent correlation/request IDs, via a shared helper used by gateway/routing/runtime overload paths (PR-18472, rolled out under a feature flag). Guard tests ensure generic 5xx never set Retry-After; admission decisions happen before stream initiation; Retry-After is always integer seconds; routing also preserves Retry-After on its own overload payloads.
> 
> **Alerts:** Added the `api_gateway.overload.retry_after_missing` counter (dimensions: route_group, region, status), wired into logging when the helper isn't used—it should stay at 0 and serves as a canary safety check to alert if the header regresses.

</details>

<a id="case-enterprise_rag_bench-qst_0373"></a>

### enterprise_rag_bench:qst_0373 — 评分与执行路径对照

**问题：** What is the expected workflow when a new Sev0 or Sev1 incident is created with incident_type set to unknown, including the temporary owner, when it must be reclassified, and how SLA timers and alerts behave until it is updated?

**score：4→3（Δ-1）；rounds：2→2（Δ+0）。**

工具安排：naive 为第1轮1次；community 为第1轮2次。最终回答另占一轮。

两边均为 2 轮，但工具总数 1→2，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 12→15、文档 overview 4→18；工具结果字符数 33,728→85,347，QA token 11,608→24,474。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

<details>
<summary>展开 judge 所提实体的字面证据核对</summary>

| 实体/术语 | naive工具中首次匹配 | naive答案 | community工具中首次匹配 | community答案 |
|---|---|---|---|---|
| SRE | 轮1/调用1/D0292:0 | 出现 | 轮1/调用1/D0078:2 | 出现 |
| SLA | 轮1/调用1/D0292:0 | 出现 | 轮1/调用1/D0078:0 | 出现 |

这里只检查指定字面串及字母数字边界，不评判上下文是否在讨论同一事实；未匹配不排除同义表述，出现也不代表正确采用。它用于区分“可能未召回”和“已出现但未展开”的复核入口，不能自动判定因果。

</details>

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/027700c251fb44c1bb2db55d53e5f965.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/994208be68dd4965bf0d4d24d0b06379.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Sev0 Sev1 incident unknown incident_type temporary owner reclassify SLA timers alerts","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0292:0, D0078:0, D0292:3, D0079:5, D0079:0, D0292:2, D0078:2, D0026:0, D0292:1, D0079:6, D0078:3, D0292:4 |

judge reasoning：

> The generated answer fully captures the gold answer's key facts—temporary SRE ownership, 10-minute classification requirement, SRE/Platform Control Plane escalation, T+30/T+60 Duty Manager escalation, SLA start and 15-minute grace timer, conservative unknown targets, and alert behavior until reclassification—with only minor wording differences.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Sev0 Sev1 incident created incident_type unknown temporary owner reclassified","search_mode":"hybrid","doc_ids":null} | 12 | 18 | 2 | 成功 | D0078:0, D0078:2, D0292:0, D0079:0, D0078:1, D0292:3, D0078:3, D0079:1, D0079:6, D0026:0, D0292:2, D0080:0 |
| 2 | 1 | search_chunks {"query":"SLA timers alerts incident_type unknown severity","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0292:0, D0292:3, D0292:2, D0078:0, D0079:5, D0292:1, D0079:0, D0026:0, D0078:2, D0080:5, D0078:3, D0078:1 |

judge reasoning：

> The generated answer accurately captures the main workflow, temporary SRE ownership, 10-minute reclassification trigger, SLA grace timer, and conservative unknown-type targets, but slightly omits the escalation at the T+30 checkpoint and the subtype=unknown detail, making it a strong but not perfect match.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> For a new Sev0/Sev1 incident, incident_type=unknown (and subtype=unknown) is only a temporary triage state when there isn't enough evidence to pick a top-level type. While it's unknown, the primary owner must be set to SRE (Reliability) as a temporary owner and the incident channel must note what's known/unknown and the next steps/time to revisit. The IC is accountable for getting it classified and must set a real type/subtype within 10 minutes; if it's still unknown after 10 minutes, page SRE plus Platform Control Plane for default triage, and if still unknown at later checkpoints (T+30 and T+60) escalate to the SRE Duty Manager to force a least-wrong classification. SLA clocks still start when the incident is declared (created_at with severity set). If incident_type is unknown, the SLA system runs a Sev0/Sev1 classification grace timer (15 minutes); after that it applies incident_type="unknown" conservative/default TTM/TTF targets and SLA warnings/breach alerts run against those targets until the incident_type is updated, at which point due-times/alerts update to the correct type/subtype targets with elapsed time counted from the original start.

**naive 最终答案**

> **Workflow for new Sev0/Sev1 incident with `incident_type = unknown`:**
> 
> 1. **Temporary owner:** Primary owner is set to **SRE (Reliability)** temporarily (D0078). If still unknown after 10 minutes, the IC pages **SRE + Platform Control Plane on-call** as default triage (D0079).
> 2. **Required actions:** Post a note in the incident channel listing what is known, what is unknown, next 1–3 disambiguation steps, and the revisit time. Classification must be set within **10 minutes** of declaration; unknown is allowed only temporarily when evidence is insufficient (D0078).
> 3. **Reclassification timing:** Unknown must be revisited at **T+30 min and T+60 min** from incident start for Sev0/Sev1; if still unknown at the second checkpoint, the IC must ask the **SRE Duty Manager** to arbitrate and pick the least-wrong category (D0078).
> 4. **SLA timers:** The clock starts at declaration with severity set. Because the type is unknown, a **classification grace period of 15 minutes** (Sev0/Sev1) runs; after grace, SLA targets default to `incident_type = "unknown"` (conservative defaults per tier/severity) until the type is updated. TTM stops at "Mitigated", TTF at "Resolved" (D0292).
> 5. **Alerts until updated:** Warning alerts fire at **T-30m and T-10m** for the Sev0/Sev1 mitigation target and **T-60m** for the fix target; breach alerts go to Slack + paging per severity — all computed against the conservative "unknown" defaults until reclassification (D0292).

**community 最终答案**

> When a new Sev0/Sev1 incident is created with `incident_type = unknown`:
> 
> **Workflow and temporary owner:**
> - Assign **primary owner = SRE (Reliability)** temporarily.
> - Post a note in the incident channel covering what is known (symptoms, endpoints/regions/tenants), what is unknown (missing signals), the next 1–3 disambiguation steps, and the revisit time.
> - Classification must be set within **10 minutes** of declaration/creation; if still unknown after 10 minutes, the IC pages **SRE + Platform Control Plane on-call** (default triage) and updates the type as soon as evidence emerges.
> 
> **When it must be reclassified:**
> - Revisit at **T+30 min** and **T+60 min** from incident start. Unknown is not a final state.
> - If still unknown at the second checkpoint (T+60), the IC must explicitly get **SRE Duty Manager** help to arbitrate and pick the least-wrong category for reporting/routing.
> 
> **SLA timers and alerts until updated:**
> - A **classification grace period timer** starts (15 minutes for Sev0/Sev1).
> - After the grace period, the SLA clock uses `incident_type = "unknown"` with **conservative/default SLA targets per tier/severity** until the type is updated.
> - Timers run normally from declaration (started when severity is set); on any reclassification, due times are recomputed from the original start time (anchored to start) and audited.
> - SLA warnings (T-30m/T-10m mitigation for Sev0/Sev1; T-60m fix) and breach alerts/paging fire against those conservative unknown defaults until the incident_type is updated.

</details>

<a id="case-enterprise_rag_bench-qst_0375"></a>

### enterprise_rag_bench:qst_0375 — 评分与执行路径对照

**问题：** When a quantization profile is blocked due to a quality regression, how is that enforced differently from an incompatibility fallback, and what should oncall do to verify a customer route is back on baseline using logs, dashboards, and audit history?

**score：3→4（Δ+1）；rounds：2→2（Δ+0）。**

工具安排：naive 为第1轮2次；community 为第1轮2次。最终回答另占一轮。

两边均为 2 轮，但工具总数 2→2，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 23→19、文档 overview 13→48；工具结果字符数 81,643→123,612，QA token 23,377→33,008。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/c190611fa7ce4588a206e8b3e2c631dd.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/39e7a1623a8a4e67a28cb8891b55057d.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"quantization profile blocked due to quality regression enforcement incompatibility fallback","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0059:0, D0259:1, D0016:0, D0187:0, D0259:0, D0016:3, D0187:1, D0016:2, D0259:2, D0016:1, D0059:1, D0016:5 |
| 2 | 1 | search_chunks {"query":"oncall verify customer route back on baseline logs dashboards audit history","search_mode":"hybrid","doc_ids":null} | 12 | 9 | 0 | 成功 | D0242:0, D0146:0, D0148:0, D0119:5, D0146:3, D0212:4, D0050:0, D0105:4, D0259:0, D0261:1, D0028:4, D0146:4 |

judge reasoning：

> The generated answer correctly explains the enforcement difference and covers core verification via logs, dashboards, and audit history, but omits important nuances from the gold answer such as kill-switch/tenant-override audit checks, confirming disabled rather than fallback as the dominant dashboard outcome, and inspecting trace tags/reason codes to distinguish blocked from incompatibility.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"quantization profile blocked quality regression enforcement incompatibility fallback","search_mode":"hybrid","doc_ids":null} | 12 | 32 | 4 | 成功 | D0059:0, D0016:0, D0259:1, D0187:0, D0259:0, D0187:1, D0016:3, D0016:1, D0016:5, D0259:2, D0016:2, D0059:1 |
| 2 | 1 | search_chunks {"query":"verify customer route back on baseline logs dashboards audit history quantization","search_mode":"hybrid","doc_ids":null} | 12 | 16 | 2 | 成功 | D0259:0, D0059:2, D0242:0, D0259:2, D0059:0, D0146:0, D0146:3, D0259:1, D0148:0, D0059:4, D0148:4, D0016:0 |

judge reasoning：

> The generated answer fully captures the key distinction between a quality-regression block and an incompatibility fallback, and accurately details all required oncall verification steps via logs, dashboards, and audit history, consistent with the gold answers.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> A blocked profile (quality regression) is enforced as a hard policy constraint in the control-plane/policy layer: the profile is deterministically not allowed for the specific (model_id, variant, profile_id and often profile_version) even if the route still references it and it would otherwise pass technical compatibility. Resolution returns baseline with an explicit blocked-style signal (distinct from normal incompatibility) so it is observable and does not depend on runtime behavior. An incompatibility fallback is the normal safety path when a profile was requested but fails compatibility or operational prerequisites (e.g., GPU/CUDA/kernel unsupported, KV cache incompatible, max context/request-shape caps exceeded, profile not published in region/tier, artifact fetch timeout/integrity failure). In that case the system falls back to baseline with a machine-readable incompatibility/operational reason code.
> 
> To verify a customer route is back on baseline, oncall should:
> 1) Audit/change history: check Console Change History / audit logs for route.quantization_profile.updated to confirm quantization_profile_ref was set to Default (no profile) or Disabled (and capture actor, timestamp, old/new). If a broader control was used, also check tenant override audit (quant_profiles_enabled=false) and/or quant_profiles.kill_switch.updated for kill switch flips and propagation timing.
> 2) Dashboards: in Console -> Observability -> Quantization Profiles (Quantization Profile Rollout), filter by route_id (and region/tier). Confirm applied/enabled requests for that route drop to ~0, and the dominant outcome becomes disabled (not fallback). If a kill switch was used, confirm outcomes show disabled with kill-switch reason platform-wide or for the scoped environment. Also confirm p95 latency and 5xx return toward pre-incident baseline, and that fallback_rate (if previously elevated) trends down.
> 3) Logs/traces: query recent runtime request logs and traces for that route (last 15-60m) and verify quant_profile_resolution/quant_resolution_outcome is disabled and quant_profile_id is null/absent after the change. If customers provide request_ids, inspect trace tags (quant_profile_id, quant_profile_resolution, quant_profile_fallback_reason) to ensure the post-rollback requests are running baseline; if a block/kill switch is the mechanism while the route still references a profile, expect baseline with an explicit blocked/kill-switch reason rather than an incompatibility reason.

**naive 最终答案**

> **Blocked (quality regression) vs. incompatibility fallback enforcement**
> 
> - **Incompatibility fallback**: The policy engine returns `FALLBACK_BASELINE` with a standardized machine-readable reason code (e.g., `GPU_UNSUPPORTED`, `MAX_CONTEXT_EXCEEDED`) when a requested profile can't be applied for technical reasons (hardware, kernel, context limits, etc.). It's the expected, automatic behavior per the fallback standard.
> - **Blocked due to quality regression**: A known-bad entry is added to the policy engine's constraints/allowlist (keyed by model_id, variant, profile_id, profile_version). Resolution still returns baseline precision deterministically, but `blocked` is treated as a **distinct outcome from `incompatible`** — it gets its own metrics tag (`quant_profile_resolution=blocked`) and audit trail so it can be alerted/observed separately, and returns a human-readable remediation message ("Profile blocked due to quality regression; use default precision or select qp_int8_calib_v2"). It's a hard guardrail: the profile can't be applied even if route config still references it, and existing routes deterministically fall back to baseline on the next config cache refresh. Route-level disable alone isn't sufficient; the block prevents re-enablement.
> 
> **Oncall verification that a customer route is back on baseline**
> 
> - **Logs/traces**: Pick a request_id after the rollback; confirm `quant_profile_id` is absent and `quant_resolution_outcome = disabled` (query logs with `quant_profile_id`, `quant_resolution_outcome (applied|fallback|disabled)`, `route_id`).
> - **Dashboards**: Check per-route `fallback_rate`, `enabled_rate`, p95 latency deltas, and error rate deltas; confirm the Enabled Routes panel drops to ~0 and p95/5xx recover to baseline (within 5–10 minutes per the runbook).
> - **Audit history**: Confirm the change in Console change history — every `quantization_profile_ref` change must have an audit log event with actor, route identifiers, previous value, new value, timestamp, and change source (API/Console), showing the route was set back to baseline/default.

**community 最终答案**

> **Blocked vs. incompatibility fallback (enforcement difference):**
> - A profile blocked due to quality regression is a distinct policy outcome from "incompatible." The policy engine has a known-bad block entry (model_id + variant + profile_id + version) in the quantization profile constraints/allowlist, so the profile cannot be applied even if route config still references it — resolution deterministically returns baseline precision with an explicit "blocked" reason (e.g., `quant_profile_resolution=blocked`), a human-readable remediation message ("Profile blocked due to quality regression; use default precision…"), and separate metrics tags/audit trail so it can be alerted/observed independently.
> - An incompatibility fallback is driven by hard incompatibility (unsupported GPU/kernel, max context exceeded, etc.) and produces `FALLBACK_BASELINE` with a standardized fallback reason code (e.g., `GPU_UNSUPPORTED`, `MAX_CONTEXT_EXCEEDED`) counted under `quant_profile_fallback_requests_total` / fallback_rate. A block is a hard guardrail against re-enablement, not an environmental incompatibility.
> 
> **Oncall verification that a customer route is back on baseline:**
> - **Logs/traces:** pick request_ids after the change; confirm `quant_profile_id` is absent/null and `quant_resolution_outcome` = `disabled` (or baseline) in traces/log annotations.
> - **Dashboards (within 5–10 min):** `enabled_routes` for the route drops to 0; fallback_rate drops (if it was driven by incompatibility) or stays stable if unrelated; p95 returns toward baseline (confirming-recovery checklist: p95 within 5% of pre-incident baseline); 5xx returns to baseline within 10–15 min.
> - **Audit history:** query audit events (`route.quantization_profile.updated`, plus `quant_profiles.kill_switch.updated` if used) for the route — capture actor, tenant_id, route_id, old_value/new_value, timestamp — to confirm the change from the profile to default and who performed it (also evidence the block event via the blocked resolution/audit trail). For design partners, also request 2–3 sample request IDs and confirm output/latency improvement.

</details>

<a id="case-enterprise_rag_bench-qst_0379"></a>

### enterprise_rag_bench:qst_0379 — 评分与执行路径对照

**问题：** If a Private upgrade fails on a Postgres migration lock timeout, what is the recommended operator path to recover or roll back, and what upgrade artifacts and audit events need to be captured for change management?

**score：3→2（Δ-1）；rounds：2→2（Δ+0）。**

工具安排：naive 为第1轮2次；community 为第1轮2次。最终回答另占一轮。

两边均为 2 轮，但工具总数 2→2，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 23→18、文档 overview 11→26；工具结果字符数 76,091→95,430，QA token 21,941→26,562。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/818947fe6c03473194b557eb2ffb2820.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/f909ee35ce544ff9a453288cffa20eba.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Private upgrade fails Postgres migration lock timeout recover rollback","search_mode":"hybrid","doc_ids":null} | 12 | 7 | 0 | 成功 | D0265:0, D0265:1, D0265:2, D0081:4, D0084:2, D0295:0, D0081:2, D0295:3, D0084:3, D0313:0, D0128:4, D0312:0 |
| 2 | 1 | search_chunks {"query":"upgrade artifacts audit events change management capture","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0128:0, D0128:5, D0072:5, D0072:0, D0154:0, D0070:0, D0070:6, D0128:6, D0081:2, D0084:0, D0069:0, D0128:2 |

judge reasoning：

> The generated answer captures the core recovery path and most required artifacts/audit events, but it omits the detailed restore-from-backup procedure and a few change-management specifics such as restore logs/evidence and backup_id in audit fields, so it is not a perfect match.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Private upgrade fails Postgres migration lock timeout recover rollback","search_mode":"hybrid","doc_ids":null} | 12 | 26 | 3 | 成功 | D0265:0, D0265:1, D0265:2, D0081:4, D0084:2, D0295:0, D0081:2, D0295:3, D0084:3, D0313:0, D0128:4, D0312:0 |
| 2 | 1 | search_chunks {"query":"migration lock timeout upgrade artifacts audit events change management","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0265:0, D0265:1, D0265:2, D0084:3, D0295:3, D0081:4, D0128:2, D0128:0, D0084:6, D0070:6, D0072:5, D0071:5 |

judge reasoning：

> The generated answer mostly follows the correct recovery path and captures many artifacts/audit events, but it inaccurately states that once a DB migration has run rollback requires restore and omits the installer rollback path for reversible migrations plus restore audit events/backup_id, which are key details.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> On a Private upgrade Postgres migration lock-timeout failure: stop further progression (do not proceed to data-plane changes), capture the current installer upgrade status/last state and generate a support bundle including the upgrade trace. Attempt forward recovery first by clearing the lock contention: scale down the control-plane deployments to release stale connections, inspect Postgres for long-running transactions and lock waits (pg_stat_activity / lock info), terminate the blocking backend PID (pg_terminate_backend) and retry the migration step (re-run the migration job / re-apply the control-plane stage per the installer plan). If the lock cannot be cleared quickly, migrations appear partially applied, or the plan indicates the migration stage is not safely reversible, move to rollback decisioning: use the installer rollback path only if the upgrade state shows a valid rollback entry point and migrations are marked reversible; otherwise treat rollback as blocked/unsafe and perform restore-from-backup as the authoritative fallback (scale down workloads to prevent writes, restore the control-plane DB from the pre-upgrade snapshot/dump associated with the plan, reconcile Helm releases/values/manifests to the pre-upgrade pinned versions recorded in the upgrade state, then bring CP up and verify CP health before restoring DP and running postchecks).
> 
> For change management, retain and attach: the generated upgrade plan (plan.json / upgrade-plan.json, plus a short summary), the precheck report (precheck-report.json, including any WARN acknowledgements), the backup report/manifest (backup-report.json plus backup_id and snapshot IDs or dump URIs, verification result, and encryption/KMS mode), the upgrade execution outputs (upgrade-report.json and/or persisted state dir/UpgradeRun record with upgrade_id, from/to versions, plan hash, backup_id, per-stage step results) and relevant Kubernetes job logs (migration job) plus installer logs; include rollback-report.json if rollback is attempted, or restore logs/evidence if a backup restore is performed; and the generated support bundle with upgrade trace (redacted of secrets). Audit events minimum set: upgrade_started, prechecks_passed or prechecks_failed, backup_completed or backup_failed, upgrade_completed or upgrade_failed, and if used rollback_invoked plus rollback_completed or rollback_failed (and restore_started/restore_completed for environments requiring restore audit), with environment/cluster id, operator identity, from_version/to_version, upgrade_plan_id/plan hash, upgrade_id/execution id, backup_id, and timestamps.

**naive 最终答案**

> **Recovery / rollback path (recommended operator action):**
> 
> 1. **Stabilize first** — stop further rollout; keep data plane serving. Scale down control plane deployments (`redwood-control-plane-api`, `redwood-console`) to 0 to release stale connections; if still blocked, restart the Postgres pod.
> 2. **Identify and terminate the blocking backend:**
>    - `kubectl exec -n redwood sts/postgres-0 -- psql -c "select pid, state, now()-xact_start as xact_age, query from pg_stat_activity where xact_start is not null order by xact_age desc;"`
>    - `select pg_terminate_backend(<pid>);`
> 3. **Re-run the migration job** by deleting the failed job pod and re-applying the hook (or `helm upgrade --reuse-values`).
> 4. **Verify** — scale control plane back up and check readiness; confirm version endpoints.
> 5. **Rollback decision:** rollback is *blocked* if migrations have partially applied (migrations are unsafe by default unless marked backward-compatible) — then restore from backup is required with operator opt-in. If no migrations ran (charts-only), use `redwood-private rollback --to <previous_version>` / `redwood-private upgrade rollback --state-dir <path> --output rollback-report.json`, then verify post-rollback health.
> 
> **Upgrade artifacts to capture (for change management/retention):**
> - Upgrade plan (`plan.json`) + human summary
> - Precheck report (`precheck-report.json`)
> - Backup report (`backup-report.json`) + backup identifiers
> - Upgrade execution report (`upgrade-report.json`) / state-machine logs
> - Rollback report (`rollback-report.json`) if used
> - Sanitized installer logs + referenced artifact manifests
> - Support bundle with upgrade traces, per-hook job logs, and final state record (UpgradeRun)
> - Retention: 30 days default; 90 days recommended for regulated customers
> 
> **Audit events to capture:**
> - `upgrade_started`
> - `precheck_passed` / `precheck_failed`
> - `backup_completed` / `backup_failed`
> - `upgrade_completed` / `upgrade_failed`
> - `rollback_invoked` / `rollback_completed` / `rollback_failed` (also rollback started/step.completed variants)
> - Required fields: environment id, operator identity, from/to versions, plan id + execution id, timestamps (plus attempt_id, ponr_reached, artifact_digests)

**community 最终答案**

> **Recommended operator path to recover/roll back**
> 
> 1. **Stabilize:** Stop further rollout progression; scale control plane deployments to 0 to release stale DB connections (keep data plane serving).
> 2. **Identify/terminate the blocker:** Query `pg_stat_activity` for long-running transactions and run `pg_terminate_backend(<pid>)` (restart the Postgres pod if still blocked).
> 3. **Re-run the migration job** (delete failed job pod and re-apply the hook, or `helm upgrade --reuse-values`), then scale CP deployments back up and verify readiness (`rollout status`, no CrashLoop/Error pods, version endpoint shows target).
> 4. **Rollback only if required and safe:** Roll back if the migration is non-reversible/non-backward-compatible, CP can't start because it expects new schema, or lock contention can't be stabilized. Migration rollback is unsafe by default — charts-only rollback is allowed only if the DB migration hasn't run; otherwise rollback requires restore from backup with explicit operator opt-in (never auto-restore). Escalate to Release captain (Connor O'Brien), migrations eng (Michael Nguyen), SRE (Sean Gallagher/Rafael Mendes), and Support SME (Owen Phillips).
> 
> **Artifacts to capture for change management**
> - Upgrade plan (`upgrade-plan.json`) + summary, precheck report, backup references + verification report, execution timeline/step results, and rollback invocation report (if used)
> - Upgrade/rollback start-stop timestamps and operator actions (pause/resume/rollback)
> - Support bundle: installer logs, per-hook/migration job logs, final UpgradeRun state record, plan summary, rollback attempt logs — all attached to the change record
> 
> **Audit events to capture**
> - `upgrade_started`, `precheck_passed/failed`, `backup_completed/failed`, `upgrade_completed/failed`, `rollback_invoked/completed/failed` (also `private.upgrade.rollback.started/step.completed/failed/completed`)
> - Required fields on each event: environment/cluster id, operator identity, from/to versions, plan id + execution id, timestamps (plus attempt_id, ponr_reached, artifact_digests for rollback).

</details>

<a id="case-enterprise_rag_bench-qst_0422"></a>

### enterprise_rag_bench:qst_0422 — 保留期限与 Legal Hold 例外的表述边界

**问题：** How do audit log exports access records older than the retention cutoff (super-admin override vs legal hold)?

**score：4→2（Δ-2）；rounds：2→2（Δ+0）。**

naive 明确先说 exports cannot retrieve older records，再说明 Legal Hold 例外；community 直接说 exports access older records via Legal Hold。两边均提及 legal_hold_id、启用租户、审计记录与废弃 super-admin override，judge 却给 4→2。gold 本身同时包含“不能超期导出”和“超期检索需要 Legal Hold”两层表述，必须澄清 export 与 retrieval 的语义边界。本例不能据 −2 直接认定社区检索出了错误事实；它更接近条件化措辞的差异及评分对边界的敏感性。

工具安排：naive 为第1轮1次；community 为第1轮2次。最终回答另占一轮。

两边均为 2 轮，但工具总数 1→2，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 12→17、文档 overview 7→29；工具结果字符数 39,557→97,288，QA token 11,858→25,699。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/37b6229ab4884b5e8567792ff250986d.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/8de722a78513481a9a364db9c4a8ac4b.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"audit log export access records older than retention cutoff super-admin override legal hold","search_mode":"hybrid","doc_ids":null} | 12 | 7 | 0 | 成功 | D0145:0, D0145:1, D0288:0, D0057:0, D0144:0, D0146:2, D0261:0, D0145:3, D0146:1, D0145:2, D0288:1, D0143:3 |

judge reasoning：

> The generated answer fully and accurately captures all key facts from the gold answer, including the retention cutoff, deprecation of super-admin override, legal hold requirement, tenant eligibility, and audit logging with ticket reference.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"audit log export access records older than retention cutoff","search_mode":"hybrid","doc_ids":null} | 12 | 21 | 3 | 成功 | D0145:0, D0145:1, D0288:0, D0146:0, D0144:0, D0261:0, D0057:0, D0146:2, D0146:3, D0145:2, D0276:0, D0280:0 |
| 2 | 1 | search_chunks {"query":"super-admin override legal hold audit log retention","search_mode":"hybrid","doc_ids":null} | 12 | 8 | 1 | 成功 | D0145:0, D0057:0, D0145:1, D0288:0, D0145:3, D0281:0, D0163:2, D0280:0, D0146:2, D0261:0, D0146:1, D0199:5 |

judge reasoning：

> The generated answer correctly describes the legal hold workflow and deprecation of the super-admin override, but it incorrectly states that exports can access older records via legal hold, whereas the gold answer emphasizes that exports cannot pull records older than the tenant retention cutoff.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Exports cannot pull records older than the tenant retention cutoff. The older "super-admin retention override" is deprecated; now any retrieval beyond retention requires an explicit Legal Hold using a legal_hold_id (only for tenants with Legal Hold enabled), and use of the legal_hold_id is logged to the immutable audit stream with a ticket reference.

**naive 最终答案**

> Audit log exports cannot retrieve records older than the tenant retention cutoff. The previous "super-admin retention override" is deprecated. Access to records beyond standard retention now requires an explicit Legal Hold, represented by a `legal_hold_id`, and is only allowed for tenants with Legal Hold enabled; all uses of `legal_hold_id` are logged to the immutable audit stream with a ticket reference.

**community 最终答案**

> Audit log exports access records older than the retention cutoff via an explicit **Legal Hold** (represented by a `legal_hold_id`), which is only allowed for tenants with Legal Hold enabled, and all uses are logged to the immutable audit stream with a ticket reference. The previous **super-admin retention override** has been **deprecated** and replaced by this Legal Hold workflow.

</details>

<a id="case-enterprise_rag_bench-qst_0427"></a>

### enterprise_rag_bench:qst_0427 — 核心答案相同、共同遗漏 invoice-line 要求

**问题：** ClearEdge 2027 pilot: final po_fingerprint format and weekly invoice delivery time?

**score：3→4（Δ+1）；rounds：2→2（Δ+0）。**

两份答案都给出 lowercase SHA-256、PO_NUMBER|PO_LINE_UUID、Tuesday 07:00 PT，均未明确写 included on each invoice line。naive judge 因该遗漏给 3，community judge 给 4。这是明显的复评分优先案例，不能作为社区让政策更新判断更准确的证据。工具数 2→1、轮次不变，查询首轮合并是执行路线差异，发生在读取社区结果之前。

工具安排：naive 为第1轮2次；community 为第1轮1次。最终回答另占一轮。

两边均为 2 轮，但工具总数 2→1，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 18→12、文档 overview 10→40；工具结果字符数 69,709→71,143，QA token 20,715→20,327。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/e71960ba793c4d68a43d5b12d50718c1.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/c33ef7b1631e4e4a8e3789e31198c141.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"ClearEdge 2027 pilot po_fingerprint format","search_mode":"hybrid","doc_ids":null} | 12 | 6 | 0 | 成功 | D0097:0, D0097:2, D0097:1, D0200:0, D0200:2, D0200:1, D0224:0, D0076:0, D0225:0, D0140:5, D0225:4, D0225:3 |
| 2 | 1 | search_chunks {"query":"weekly invoice delivery time","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0097:0, D0200:0, D0097:2, D0200:2, D0200:1, D0097:1, D0096:0, D0216:3, D0096:6, D0266:0, D0096:1, D0094:3 |

judge reasoning：

> The generated answer correctly specifies the SHA-256 format and Tuesday 07:00 PT delivery, but omits the gold requirement that po_fingerprint be included on each invoice line, making it a minor omission rather than a perfect match.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"ClearEdge 2027 pilot po_fingerprint format weekly invoice delivery time","search_mode":"hybrid","doc_ids":null} | 12 | 40 | 5 | 成功 | D0097:0, D0097:2, D0200:0, D0097:1, D0200:2, D0200:1, D0225:0, D0045:0, D0217:3, D0266:0, D0140:5, D0225:4 |

judge reasoning：

> The generated answer correctly captures the final po_fingerprint format (lowercase SHA-256 hex digest of the exact string) and weekly delivery time (Tuesdays by 07:00 PT), with only consistent additional context.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Final requirements: po_fingerprint must be the lowercase SHA-256 hex digest of the exact string `PO_NUMBER|PO_LINE_UUID` (no whitespace) and included on each invoice line; weekly consolidated invoice files are delivered Tuesdays by 07:00 PT. Earlier June 2027 emails mentioned sending raw `PO#|LINEUUID` without hashing and Monday-morning delivery, but that is superseded.

**naive 最终答案**

> Final po_fingerprint format: lowercase **SHA-256 hex digest** of the input string `PO_NUMBER|PO_LINE_UUID` (no whitespace; raw/unhashed string and SHA-1 are prohibited).
> 
> Weekly invoice delivery: **Tuesdays by 07:00 PT**, via ClearEdge SFTP (supersedes the earlier Monday 08:00 PT guidance).

**community 最终答案**

> **po_fingerprint (final):** lowercase SHA-256 hex digest of `PO_NUMBER|PO_LINE_UUID` (no whitespace; raw/unhashed string and SHA-1 prohibited).
> 
> **Weekly invoice delivery:** Tuesdays by 07:00 PT, via ClearEdge SFTP.

</details>

<a id="case-enterprise_rag_bench-qst_0432"></a>

### enterprise_rag_bench:qst_0432 — 评分与执行路径对照

**问题：** Which intake channel has the most reports of "token accounting discrepancy"?

**score：0→0（Δ+0）；rounds：13→11（Δ-2）。**

工具安排：naive 为第1轮1次、第2轮2次、第3轮2次、第4轮2次、第5轮2次、第6轮1次、第7轮2次、第8轮2次、第9轮2次、第10轮2次、第11轮2次、第12轮2次；community 为第1轮1次、第2轮2次、第3轮2次、第4轮2次、第5轮2次、第6轮2次、第7轮2次、第8轮2次、第9轮2次、第10轮2次。最终回答另占一轮。

轮次减少 2，工具总数 22→19、错误 2→1，整轮全部工具报错的轮数 1→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 42→69、文档 overview 31→106；工具结果字符数 493,558→573,543，QA token 791,619→742,480。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具名与解析后的参数完全一致。首个工具返回的有序 chunk ID 也相同；这是较接近受控的开局，但仍非重复实验或独立消融。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/d31df276e5ae4df49f83c7b699a3f5cb.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/f2a2c5c20bfb4bc19b7558bd61c80f99.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"token accounting discrepancy intake channel","search_mode":"hybrid","doc_ids":null} | 12 | 10 | 0 | 成功 | D0030:0, D0198:1, D0256:0, D0245:0, D0198:0, D0319:0, D0255:0, D0257:0, D0217:0, D0217:6, D0266:0, D0181:0 |
| 2 | 2 | search_chunks {"doc_ids":null,"query":"weekly reporting count token accounting origin Slack Gmail Jira number of cases","search_mode":"hybrid"} | 12 | 4 | 0 | 成功 | D0030:0, D0256:0, D0022:2, D0236:0, D0198:0, D0022:0, D0217:3, D0023:4, D0217:4, D0319:0, D0097:1, D0266:0 |
| 3 | 2 | search_chunks {"doc_ids":["D0030"],"query":"most reports intake channel Slack Gmail Jira","search_mode":"hybrid"} | 1 | 0 | 0 | 成功 | D0030:0 |
| 4 | 3 | search_chunks {"doc_ids":null,"query":"token accounting discrepancy most common intake channel Slack majority reports","search_mode":"vector"} | 12 | 2 | 0 | 成功 | D0030:0, D0198:1, D0319:0, D0256:0, D0091:2, D0043:0, D0245:0, D0257:0, D0266:0, D0217:6, D0217:1, D0198:0 |
| 5 | 3 | search_chunks {"doc_ids":["D0030"],"query":"most reports","search_mode":"vector"} | 1 | 0 | 0 | 成功 | D0030:0 |
| 6 | 4 | search_chunks {"doc_ids":null,"query":"token accounting discrepancy origin counts Slack vs Gmail vs Jira number of cases weekly report","search_mode":"keyword"} | 12 | 1 | 0 | 成功 | D0030:0, D0198:0, D0256:0, D0245:0, D0255:0, D0217:0, D0217:4, D0198:1, D0319:0, D0200:1, D0097:0, D0217:3 |
| 7 | 4 | search_chunks {"doc_ids":null,"query":"Slack is the most common intake channel for token accounting reports","search_mode":"vector"} | 12 | 0 | 0 | 成功 | D0030:0, D0198:1, D0319:0, D0266:0, D0091:2, D0245:0, D0236:0, D0256:0, D0217:1, D0257:0, D0043:0, D0091:0 |
| 8 | 5 | search_chunks {"doc_ids":null,"query":"most token accounting discrepancy reports arrived via Slack more than email Jira","search_mode":"keyword"} | 12 | 3 | 0 | 成功 | D0030:0, D0245:0, D0256:0, D0319:0, D0198:0, D0255:0, D0198:1, D0294:0, D0284:0, D0217:0, D0094:4, D0022:0 |
| 9 | 5 | search_chunks {"doc_ids":null,"query":"count of cases by origin channel report totals table token-accounting weekly","search_mode":"vector"} | 12 | 2 | 0 | 成功 | D0030:0, D0266:0, D0256:0, D0181:1, D0319:0, D0284:0, D0245:0, D0093:1, D0019:3, D0198:1, D0257:0, D0236:0 |
| 10 | 6 | read_chunks {"doc_id":"D0030","ordinals":[0,1,2,3]} | 0 | 0 | 0 | Unknown chunk ordinal | — |
| 11 | 7 | search_chunks {"doc_ids":null,"query":"Slack origin most token accounting discrepancy reports count majority","search_mode":"keyword"} | 12 | 1 | 0 | 成功 | D0030:0, D0256:0, D0245:0, D0198:0, D0255:0, D0198:1, D0217:0, D0319:0, D0094:4, D0257:0, D0217:1, D0286:1 |
| 12 | 7 | search_chunks {"doc_ids":null,"query":"\"token-accounting\" weekly reporting origin counts Slack Gmail Jira most","search_mode":"keyword"} | 12 | 2 | 0 | 成功 | D0030:0, D0092:5, D0217:4, D0245:0, D0092:1, D0256:0, D0255:0, D0198:0, D0217:0, D0022:2, D0233:0, D0019:3 |
| 13 | 8 | search_chunks {"doc_ids":null,"query":"majority of token accounting reports come in via Slack","search_mode":"hybrid"} | 12 | 1 | 0 | 成功 | D0030:0, D0319:0, D0245:0, D0198:1, D0256:0, D0093:1, D0217:0, D0198:0, D0092:1, D0091:2, D0253:0, D0181:0 |
| 14 | 8 | search_chunks {"doc_ids":null,"query":"token accounting discrepancy report volume by channel Slack highest","search_mode":"vector"} | 12 | 0 | 0 | 成功 | D0030:0, D0198:1, D0319:0, D0256:0, D0245:0, D0266:0, D0091:2, D0198:0, D0257:0, D0217:1, D0043:0, D0236:0 |
| 15 | 9 | search_chunks {"doc_ids":null,"query":"token accounting discrepancy most reports Slack channel highest volume support","search_mode":"keyword"} | 12 | 1 | 0 | 成功 | D0030:0, D0217:0, D0256:0, D0198:0, D0255:0, D0198:1, D0245:0, D0022:2, D0319:0, D0094:4, D0022:0, D0024:1 |
| 16 | 9 | search_chunks {"doc_ids":null,"query":"Slack receives the most token accounting discrepancy reports compared to Jira and Gmail","search_mode":"vector"} | 12 | 0 | 0 | 成功 | D0030:0, D0198:1, D0091:2, D0245:0, D0319:0, D0266:0, D0256:0, D0198:0, D0043:0, D0217:1, D0257:0, D0217:6 |
| 17 | 10 | search_chunks {"doc_ids":null,"query":"majority of token accounting discrepancy reports Slack origin","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0030:0, D0245:0, D0198:1, D0256:0, D0319:0, D0255:0, D0198:0, D0217:1, D0257:0, D0217:0, D0266:0, D0217:3 |
| 18 | 10 | search_chunks {"doc_ids":null,"query":"token accounting discrepancy origin breakdown Slack Gmail Jira percentage counts cases","search_mode":"keyword"} | 12 | 3 | 0 | 成功 | D0030:0, D0198:0, D0245:0, D0256:0, D0255:0, D0217:0, D0198:1, D0130:4, D0217:4, D0319:0, D0250:3, D0077:0 |
| 19 | 11 | read_chunks {"doc_id":"D0030","ordinals":[1,2]} | 0 | 0 | 0 | Unknown chunk ordinal | — |
| 20 | 11 | search_chunks {"doc_ids":["D0030"],"query":"which channel most reports Slack majority","search_mode":"keyword"} | 1 | 0 | 0 | 成功 | D0030:0 |
| 21 | 12 | search_chunks {"doc_ids":null,"query":"token accounting discrepancy Slack majority of cases most arrived via Slack support threads","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0030:0, D0245:0, D0198:1, D0217:1, D0319:0, D0198:0, D0256:0, D0255:0, D0217:0, D0217:3, D0266:1, D0217:4 |
| 22 | 12 | search_chunks {"doc_ids":null,"query":"\"token accounting\" \"most\" reports channel","search_mode":"keyword"} | 12 | 1 | 0 | 成功 | D0030:0, D0256:0, D0255:0, D0094:4, D0092:5, D0198:0, D0181:0, D0092:1, D0198:1, D0254:0, D0245:0, D0022:0 |

judge reasoning：

> The generated answer incorrectly claims the answer cannot be established from the context, directly contradicting the gold answer that Jira has the most reports.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"token accounting discrepancy intake channel","search_mode":"hybrid","doc_ids":null} | 12 | 16 | 2 | 成功 | D0030:0, D0198:1, D0256:0, D0245:0, D0198:0, D0319:0, D0255:0, D0257:0, D0217:0, D0217:6, D0266:0, D0181:0 |
| 2 | 2 | search_chunks {"query":"count reports per intake channel Slack Gmail Jira weekly reporting token-accounting","search_mode":"hybrid","doc_ids":null} | 12 | 21 | 2 | 成功 | D0030:0, D0022:2, D0022:0, D0236:0, D0256:0, D0091:2, D0026:4, D0092:5, D0303:0, D0257:0, D0198:0, D0319:0 |
| 3 | 2 | search_chunks {"query":"most reports arrived via Slack versus Gmail versus Jira token accounting discrepancy","search_mode":"keyword","doc_ids":["D0030"]} | 1 | 0 | 0 | 成功 | D0030:0 |
| 4 | 3 | search_chunks {"doc_ids":null,"query":"weekly reporting count cases origin Slack Gmail Jira most token accounting reports","search_mode":"vector"} | 12 | 16 | 2 | 成功 | D0030:0, D0156:1, D0124:4, D0319:0, D0022:0, D0022:2, D0124:0, D0100:0, D0320:2, D0049:0, D0270:0, D0207:1 |
| 5 | 3 | search_chunks {"doc_ids":null,"query":"number of token accounting discrepancy reports by channel","search_mode":"keyword"} | 12 | 2 | 0 | 成功 | D0030:0, D0256:0, D0198:0, D0255:0, D0245:0, D0198:1, D0097:0, D0319:0, D0024:1, D0094:4, D0257:0, D0217:0 |
| 6 | 4 | search_chunks {"doc_ids":null,"query":"most token accounting discrepancy reports Slack Gmail Jira weekly reporting counts","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0030:0, D0198:1, D0245:0, D0256:0, D0198:0, D0319:0, D0217:0, D0217:4, D0217:3, D0217:6, D0217:5, D0217:1 |
| 7 | 4 | read_chunks {"doc_id":"D0030","ordinals":[0,1,2]} | 0 | 0 | 0 | Unknown chunk ordinal | — |
| 8 | 5 | search_chunks {"doc_ids":null,"query":"intake channel breakdown counts Slack Gmail Jira number of reports token accounting","search_mode":"keyword"} | 12 | 6 | 1 | 成功 | D0030:0, D0217:4, D0256:0, D0022:0, D0022:2, D0233:0, D0255:0, D0130:4, D0198:0, D0245:0, D0025:1, D0023:5 |
| 9 | 5 | search_chunks {"doc_ids":null,"query":"\"most reports\" OR \"most cases\" OR \"majority\" token accounting discrepancy origin channel","search_mode":"keyword"} | 12 | 2 | 0 | 成功 | D0030:0, D0198:0, D0094:4, D0024:1, D0286:1, D0256:0, D0142:0, D0255:0, D0233:1, D0198:1, D0254:0, D0092:1 |
| 10 | 6 | search_chunks {"doc_ids":["D0030"],"query":"Slack Gmail Jira reports","search_mode":"keyword"} | 1 | 0 | 0 | 成功 | D0030:0 |
| 11 | 6 | search_chunks {"doc_ids":null,"query":"token accounting discrepancy arrived via Slack threads most frequent origin","search_mode":"vector"} | 12 | 0 | 0 | 成功 | D0198:1, D0030:0, D0266:0, D0245:0, D0319:0, D0256:0, D0257:0, D0198:0, D0217:1, D0217:3, D0217:0, D0266:1 |
| 12 | 7 | search_chunks {"doc_ids":null,"query":"token-accounting weekly report Slack 5 Gmail 3 Jira counts table","search_mode":"keyword"} | 12 | 4 | 0 | 成功 | D0030:0, D0023:5, D0217:4, D0219:2, D0245:0, D0217:0, D0256:0, D0022:2, D0200:1, D0096:6, D0294:0, D0062:3 |
| 13 | 7 | search_chunks {"doc_ids":null,"query":"\"token-accounting\" label origin channel description weekly reporting count","search_mode":"keyword"} | 12 | 10 | 2 | 成功 | D0030:0, D0097:1, D0181:0, D0019:3, D0092:5, D0216:3, D0256:0, D0224:1, D0245:0, D0097:0, D0181:1, D0224:2 |
| 14 | 8 | search_chunks {"doc_ids":null,"query":"token accounting discrepancy reports arrived via Slack email Jira number count this week","search_mode":"keyword"} | 12 | 0 | 0 | 成功 | D0030:0, D0256:0, D0198:0, D0217:4, D0245:0, D0255:0, D0217:1, D0217:0, D0198:1, D0319:0, D0097:0, D0284:0 |
| 15 | 8 | search_chunks {"doc_ids":null,"query":"weekly reporting token-accounting Slack Gmail Jira totals","search_mode":"vector"} | 12 | 26 | 3 | 成功 | D0030:0, D0300:0, D0270:0, D0292:0, D0217:1, D0091:2, D0022:2, D0124:0, D0043:0, D0217:0, D0044:0, D0047:0 |
| 16 | 9 | search_chunks {"doc_ids":null,"query":"Slack Gmail Jira token accounting 5 3 2 reports this week","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0030:0, D0217:4, D0077:0, D0217:0, D0236:0, D0022:2, D0300:0, D0292:0, D0022:0, D0217:1, D0270:0, D0294:0 |
| 17 | 9 | search_chunks {"doc_ids":null,"query":"majority of token accounting discrepancy reports came through","search_mode":"keyword"} | 12 | 0 | 0 | 成功 | D0030:0, D0255:0, D0256:0, D0245:0, D0198:0, D0198:1, D0319:0, D0024:1, D0094:4, D0217:0, D0098:2, D0266:0 |
| 18 | 10 | search_chunks {"doc_ids":null,"query":"weekly reporting dashboard token-accounting origin channel breakdown Slack Gmail Jira count","search_mode":"hybrid"} | 12 | 1 | 1 | 成功 | D0030:0, D0022:0, D0022:2, D0091:0, D0091:2, D0043:0, D0256:0, D0217:0, D0217:5, D0217:4, D0025:1, D0091:3 |
| 19 | 10 | search_chunks {"doc_ids":null,"query":"\"intake\" \"token accounting\" Slack Jira Gmail reports count most","search_mode":"keyword"} | 12 | 2 | 0 | 成功 | D0030:0, D0256:0, D0217:4, D0142:0, D0026:4, D0147:2, D0233:0, D0022:0, D0022:2, D0233:3, D0144:2, D0031:0 |

judge reasoning：

> The generated answer directly contradicts the gold answer by claiming the information cannot be established, whereas the gold answer identifies Jira as the channel with the most reports.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Jira (customer-support SUP tickets) has the most "token accounting discrepancy" reports among the provided cases.

**naive 最终答案**

> Based on the available context, the specific report counts per intake channel are not documented — no source states which channel (Slack, Gmail, or Jira) has the most "token accounting discrepancy" reports. The only related information is that these reports "frequently arrive via Slack, email, or Jira," with no tally or ranking given. So the answer cannot be established from the provided context.

**community 最终答案**

> The context does not contain counts or a ranking of token accounting discrepancy reports by intake channel. Document D0030 lists the three approved intake channels (Jira/Slack/Gmail) and explains how to count them by origin, but provides no data on which channel has the most reports, so that cannot be established from the given information.

</details>

<a id="case-enterprise_rag_bench-qst_0434"></a>

### enterprise_rag_bench:qst_0434 — 评分与执行路径对照

**问题：** In Q4 2025, which customer industry segment was featured in the most published customer stories (case studies + one-page success stories)?

**score：4→4（Δ+0）；rounds：3→4（Δ+1）。**

工具安排：naive 为第1轮1次、第2轮2次；community 为第1轮2次、第2轮2次、第3轮2次。最终回答另占一轮。

轮次增加 1，工具总数 3→6、错误 0→1，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 19→25、文档 overview 17→41；工具结果字符数 76,804→149,136，QA token 29,993→85,677。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/bc3da47316d848f79386163141a9a73a.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/f64ee22a3c084705b300714514ffe652.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Q4 2025 customer stories case studies one-page success stories industry segment","search_mode":"hybrid","doc_ids":null} | 12 | 11 | 0 | 成功 | D0220:0, D0139:0, D0223:0, D0171:0, D0138:0, D0137:0, D0136:0, D0140:3, D0218:3, D0140:5, D0221:0, D0133:0 |
| 2 | 2 | search_chunks {"doc_ids":null,"query":"customer story Q4 2025 industry segment markers published","search_mode":"hybrid"} | 12 | 3 | 0 | 成功 | D0139:0, D0138:0, D0223:0, D0220:0, D0136:0, D0137:0, D0171:0, D0140:5, D0171:1, D0229:0, D0067:3, D0231:0 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"one-page success story published quarter Q4 2025","search_mode":"keyword"} | 12 | 3 | 0 | 成功 | D0223:0, D0220:0, D0138:0, D0139:0, D0136:0, D0137:0, D0171:0, D0171:1, D0134:3, D0140:5, D0091:0, D0285:0 |

judge reasoning：

> The generated answer fully matches the gold answer, identifying Fintech as the top segment with 3 published customer stories and the correct breakdown, with only harmless additional detail.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Q4 2025 customer stories case studies one-page success stories industry segment","search_mode":"hybrid","doc_ids":null} | 12 | 28 | 4 | 成功 | D0220:0, D0139:0, D0223:0, D0171:0, D0138:0, D0137:0, D0136:0, D0140:3, D0218:3, D0133:0, D0140:5, D0221:0 |
| 2 | 1 | search_chunks {"query":"published customer stories by industry segment count","search_mode":"hybrid","doc_ids":null} | 12 | 5 | 0 | 成功 | D0139:0, D0220:0, D0223:0, D0137:0, D0138:0, D0136:0, D0171:0, D0256:0, D0257:0, D0116:0, D0301:0, D0093:1 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"Northwind Commerce industry segment case study publication","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0137:0, D0139:0, D0136:0, D0138:0, D0171:0, D0231:0, D0201:1, D0201:0, D0220:0, D0201:2, D0231:2, D0223:0 |
| 4 | 2 | read_chunks {"doc_id":"D0171","ordinals":[0,1,2,3]} | 0 | 0 | 0 | Unknown chunk ordinal | — |
| 5 | 3 | search_chunks {"doc_ids":null,"query":"Helios Atlas customer case study one-pager published story","search_mode":"hybrid"} | 12 | 8 | 1 | 成功 | D0171:0, D0138:0, D0220:0, D0223:0, D0139:0, D0136:0, D0137:0, D0201:1, D0201:0, D0171:1, D0140:3, D0305:1 |
| 6 | 3 | search_chunks {"doc_ids":null,"query":"case study registry list published stories Q4 2025 industry segment count","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0138:0, D0139:0, D0136:0, D0137:0, D0220:0, D0171:0, D0223:0, D0171:1, D0201:0, D0201:1, D0140:5, D0201:3 |

judge reasoning：

> The generated answer exactly matches the gold answer's core facts: Fintech had the most stories in Q4 2025 with 3 total (2 case studies and 1 one-page success story), and additional details are consistent.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Fintech was featured most often in Q4 2025, appearing in 3 published customer stories (2 case studies and 1 one-page success story).

**naive 最终答案**

> **Fintech** was featured in the most published customer stories in Q4 2025 (3 stories: CedarBank and Northbridge Payments case studies, plus the LumenMoney one-pager), ahead of Healthcare, E-commerce, and Legal (1 each).

**community 最终答案**

> **Fintech** — In Q4 2025, Fintech was featured in the most published customer stories: 3 total (Northbridge Payments and CedarBank case studies, plus the LumenMoney one-page success story). Other segments had 1 each (E-commerce/BrightCart, Healthcare/HelixCare, Legal/BrieflyAI).

</details>

<a id="case-enterprise_rag_bench-qst_0435"></a>

### enterprise_rag_bench:qst_0435 — 评分与执行路径对照

**问题：** How many weekly status updates for Project Orion marked the project as 'At Risk'?

**score：4→4（Δ+0）；rounds：3→2（Δ-1）。**

工具安排：naive 为第1轮1次、第2轮2次；community 为第1轮1次。最终回答另占一轮。

轮次减少 1，工具总数 3→1、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 23→12、文档 overview 19→30；工具结果字符数 83,456→53,188，QA token 31,689→15,159。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具名与解析后的参数完全一致。首个工具返回的有序 chunk ID 不同，仍存在检索结果变化。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/6ba449faceee468ea671bad9c72c4908.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/b28e0a21df574ae98e4e460e79f4bef4.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Project Orion weekly status update At Risk","search_mode":"hybrid","doc_ids":null} | 12 | 11 | 0 | 成功 | D0048:0, D0049:0, D0044:0, D0046:0, D0045:0, D0047:0, D0122:0, D0200:0, D0023:2, D0156:1, D0023:1, D0074:1 |
| 2 | 2 | search_chunks {"doc_ids":null,"query":"Project Orion weekly status","search_mode":"keyword"} | 12 | 4 | 0 | 成功 | D0046:0, D0048:0, D0044:0, D0047:0, D0045:0, D0049:0, D0023:2, D0296:1, D0200:1, D0097:0, D0219:0, D0241:1 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"Project Orion status update Overall On Track","search_mode":"keyword"} | 12 | 4 | 0 | 成功 | D0046:0, D0047:0, D0044:0, D0048:0, D0045:0, D0049:0, D0006:3, D0241:2, D0251:3, D0212:1, D0219:1, D0311:1 |

judge reasoning：

> The generated answer accurately matches the gold answer by stating the correct count and dates of the weekly status updates marked 'At Risk'.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Project Orion weekly status update At Risk","search_mode":"hybrid","doc_ids":null} | 12 | 30 | 3 | 成功 | D0048:0, D0049:0, D0044:0, D0046:0, D0045:0, D0047:0, D0122:0, D0200:0, D0123:0, D0023:2, D0156:1, D0023:1 |

judge reasoning：

> The generated answer fully matches the gold answer, correctly stating the count and listing the exact same dates.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Three weekly status updates for Project Orion marked the project as "At Risk" (2026-01-16, 2026-01-23, and 2026-02-06).

**naive 最终答案**

> **3** weekly status updates marked Project Orion as 'At Risk' (2026-01-16, 2026-01-23, 2026-02-06).

**community 最终答案**

> 3 weekly status updates marked the project as 'At Risk' (2026-01-16, 2026-01-23, and 2026-02-06).

</details>

<a id="case-enterprise_rag_bench-qst_0437"></a>

### enterprise_rag_bench:qst_0437 — 全库计数不可靠；省轮掩盖更多工具和错误

**问题：** Across all incident postmortems, which Redwood team was assigned the most follow-up action items?

**score：2→3（Δ+1）；rounds：6→5（Δ-1）。**

两边都答 Platform，但估计的总数分别约 20 和约 23，而 gold 为 16。judge 将前者判 2、后者判 3，不能把更偏离数值的后者视为可靠准确率提升。community 虽从 6→5 轮，却由 9→17 次工具，并出现 5 次越界 read_chunks；后续用 doc_ids 限定搜索挽回读取。原始 top-k 检索加文本综合没有形成完整、去重的 action-item 账本，适合用于定位材料，不足以保证跨所有 postmortem 的精确计数。

工具安排：naive 为第1轮2次、第2轮2次、第3轮2次、第4轮2次、第5轮1次；community 为第1轮2次、第2轮7次、第3轮5次、第4轮3次。最终回答另占一轮。

轮次减少 1，工具总数 9→17、错误 0→5，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 38→56、文档 overview 33→60；工具结果字符数 242,866→192,074，QA token 217,292→146,338。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/ae8bf83cf28543af8c6b35954020be5f.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/09f51822d84242a9863b77c4422c001f.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Redwood team assigned follow-up action items postmortem","search_mode":"hybrid","doc_ids":null} | 12 | 10 | 0 | 成功 | D0207:4, D0114:0, D0111:0, D0272:1, D0116:0, D0140:5, D0109:0, D0207:3, D0207:2, D0117:0, D0199:0, D0107:0 |
| 2 | 1 | search_chunks {"query":"incident postmortem action items owner Redwood","search_mode":"vector","doc_ids":null} | 12 | 8 | 0 | 成功 | D0140:5, D0215:0, D0207:3, D0207:4, D0124:0, D0127:0, D0114:0, D0079:4, D0067:3, D0057:0, D0080:0, D0292:0 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"postmortem follow-up action items owning team","search_mode":"keyword"} | 12 | 5 | 0 | 成功 | D0116:0, D0114:0, D0103:0, D0109:0, D0111:0, D0117:0, D0107:0, D0102:0, D0113:0, D0272:1, D0077:0, D0078:0 |
| 4 | 2 | search_chunks {"doc_ids":null,"query":"P0 Incident Postmortem","search_mode":"keyword"} | 12 | 1 | 0 | 成功 | D0116:0, D0114:0, D0026:0, D0111:0, D0103:0, D0117:0, D0107:0, D0215:0, D0102:0, D0113:0, D0109:0, D0077:0 |
| 5 | 3 | read_chunks {"doc_id":"D0103","ordinals":[1]} | 1 | 0 | 0 | 成功 | D0103:1 |
| 6 | 3 | search_chunks {"doc_ids":null,"query":"postmortem follow-up action items owner","search_mode":"keyword"} | 12 | 1 | 0 | 成功 | D0109:0, D0077:0, D0272:1, D0111:0, D0118:0, D0117:0, D0107:0, D0102:0, D0113:0, D0103:0, D0116:0, D0207:4 |
| 7 | 4 | search_chunks {"doc_ids":null,"query":"Postmortem action items owner team","search_mode":"keyword"} | 12 | 2 | 0 | 成功 | D0109:0, D0077:0, D0117:0, D0111:0, D0107:0, D0102:0, D0113:0, D0103:0, D0116:0, D0060:3, D0114:0, D0209:4 |
| 8 | 4 | search_chunks {"doc_ids":null,"query":"postmortem follow-up","search_mode":"keyword"} | 12 | 2 | 0 | 成功 | D0272:1, D0320:2, D0299:1, D0077:0, D0116:0, D0215:0, D0109:0, D0118:0, D0111:0, D0114:0, D0207:4, D0117:0 |
| 9 | 5 | search_chunks {"doc_ids":null,"query":"Postmortem","search_mode":"keyword"} | 12 | 4 | 0 | 成功 | D0215:0, D0207:4, D0272:1, D0077:0, D0294:5, D0080:6, D0078:2, D0101:0, D0116:0, D0110:0, D0109:0, D0112:0 |

judge reasoning：

> The generated answer correctly identifies the Platform team but provides an inaccurate count (roughly 20 instead of 16), so it is only partially correct.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Redwood team assigned follow-up action items postmortem","search_mode":"hybrid","doc_ids":null} | 12 | 31 | 3 | 成功 | D0207:4, D0114:0, D0111:0, D0116:0, D0140:5, D0109:0, D0207:3, D0223:0, D0117:0, D0207:2, D0107:0, D0199:0 |
| 2 | 1 | search_chunks {"query":"Redwood incident postmortem action items owner","search_mode":"keyword","doc_ids":null} | 12 | 12 | 2 | 成功 | D0077:0, D0207:4, D0112:0, D0108:0, D0272:1, D0118:0, D0113:0, D0109:0, D0115:0, D0104:0, D0215:0, D0111:0 |
| 3 | 2 | read_chunks {"doc_id":"D0102","ordinals":[0,1]} | 0 | 0 | 0 | Unknown chunk ordinal | — |
| 4 | 2 | read_chunks {"doc_id":"D0103","ordinals":[0,1]} | 2 | 0 | 0 | 成功 | D0103:0, D0103:1 |
| 5 | 2 | read_chunks {"doc_id":"D0105","ordinals":[0,1]} | 2 | 8 | 1 | 成功 | D0105:0, D0105:1 |
| 6 | 2 | read_chunks {"doc_id":"D0106","ordinals":[0,1]} | 0 | 0 | 0 | Unknown chunk ordinal | — |
| 7 | 2 | read_chunks {"doc_id":"D0110","ordinals":[0,1]} | 0 | 0 | 0 | Unknown chunk ordinal | — |
| 8 | 2 | read_chunks {"doc_id":"D0101","ordinals":[0,1]} | 0 | 0 | 0 | Unknown chunk ordinal | — |
| 9 | 2 | read_chunks {"doc_id":"D0272","ordinals":[0,1,2]} | 0 | 0 | 0 | Unknown chunk ordinal | — |
| 10 | 3 | search_chunks {"doc_ids":["D0102"],"query":"follow-up action items owner team tokenizer","search_mode":"hybrid"} | 1 | 0 | 0 | 成功 | D0102:0 |
| 11 | 3 | search_chunks {"doc_ids":["D0106"],"query":"corrective actions action items owner capacity exhaustion","search_mode":"hybrid"} | 1 | 0 | 0 | 成功 | D0106:0 |
| 12 | 3 | search_chunks {"doc_ids":["D0110"],"query":"corrective actions action items owner autoscaler quota","search_mode":"hybrid"} | 1 | 0 | 0 | 成功 | D0110:0 |
| 13 | 3 | search_chunks {"doc_ids":["D0101"],"query":"corrective actions action items owner fragmentation","search_mode":"hybrid"} | 1 | 0 | 0 | 成功 | D0101:0 |
| 14 | 3 | search_chunks {"doc_ids":["D0272"],"query":"action items follow-up owner team INC-9821","search_mode":"hybrid"} | 2 | 0 | 0 | 成功 | D0272:1, D0272:0 |
| 15 | 4 | read_chunks {"doc_id":"D0105","ordinals":[2,3]} | 2 | 0 | 0 | 成功 | D0105:2, D0105:3 |
| 16 | 4 | search_chunks {"doc_ids":["D0252","D0253","D0267","D0279","D0286","D0316"],"query":"action items follow-up owner team","search_mode":"hybrid"} | 12 | 9 | 1 | 成功 | D0279:3, D0316:2, D0316:3, D0253:2, D0316:0, D0279:2, D0316:1, D0286:3, D0279:1, D0279:0, D0267:0, D0286:1 |
| 17 | 4 | search_chunks {"doc_ids":["D0273","D0274","D0277","D0315","D0244","D0231","D0260"],"query":"follow-up action items owner team postmortem","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0231:1, D0274:0, D0231:2, D0277:0, D0273:0, D0260:2, D0231:0, D0244:0, D0315:0, D0260:1, D0260:0, D0260:3 |

judge reasoning：

> The generated answer correctly identifies Platform as the team with the most follow-up action items, but it gives an incorrect count (~23 vs 16), making it mostly correct with a minor inaccuracy rather than perfect.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> The **Platform** team was assigned the most follow-up action items across all incident postmortems, with **16** total.

**naive 最终答案**

> **Eng Platform** (Platform) was assigned the most follow-up action items across the incident postmortems (roughly 20 items, e.g., routing-loop postmortem with 4, control-plane postmortem with 3, plus items in the RBAC, rate-limit, streaming, tokenizer, failover, and router-policy postmortems).

**community 最终答案**

> **Eng Platform (Platform)** was assigned the most follow-up action items across the incident postmortems (~23 items, ahead of Eng SRE/SRE with ~21).

</details>

<a id="case-enterprise_rag_bench-qst_0439"></a>

### enterprise_rag_bench:qst_0439 — 评分与执行路径对照

**问题：** How many internal incident writeups at Redwood Inference describe activating automatic fallback (to a different model or region) as part of mitigation?

**score：4→4（Δ+0）；rounds：6→7（Δ+1）。**

工具安排：naive 为第1轮2次、第2轮2次、第3轮2次、第4轮2次、第5轮2次；community 为第1轮2次、第2轮2次、第3轮2次、第4轮2次、第5轮4次、第6轮9次。最终回答另占一轮。

轮次增加 1，工具总数 10→21、错误 0→4，整轮全部工具报错的轮数 0→1。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 50→60、文档 overview 37→95；工具结果字符数 317,922→342,703，QA token 265,639→404,194。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/7b542f1037684c92a63dcf8d497d782f.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/80cd6da8067b4473a35f8783c43ce34f.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"automatic fallback mitigation different model region","search_mode":"hybrid","doc_ids":null} | 12 | 11 | 0 | 成功 | D0115:0, D0118:0, D0104:0, D0112:0, D0058:0, D0108:0, D0060:0, D0209:0, D0058:1, D0085:1, D0067:3, D0016:3 |
| 2 | 1 | search_chunks {"query":"incident writeup activate fallback","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0118:0, D0067:3, D0112:0, D0193:4, D0115:0, D0080:0, D0193:2, D0104:0, D0193:0, D0108:0, D0116:0, D0305:1 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"postmortem mitigation activated fallback automatic","search_mode":"hybrid"} | 12 | 6 | 0 | 成功 | D0104:0, D0112:0, D0118:0, D0115:0, D0108:0, D0207:4, D0111:0, D0067:3, D0272:1, D0110:0, D0114:0, D0292:0 |
| 4 | 2 | search_chunks {"doc_ids":null,"query":"incident postmortem enabled fallback different region different model","search_mode":"vector"} | 12 | 5 | 0 | 成功 | D0115:0, D0113:0, D0207:4, D0118:0, D0108:0, D0112:0, D0105:0, D0080:0, D0316:0, D0185:0, D0279:2, D0104:0 |
| 5 | 3 | search_chunks {"doc_ids":null,"query":"postmortem mitigation activated automatic fallback different model","search_mode":"keyword"} | 12 | 3 | 0 | 成功 | D0104:0, D0118:0, D0112:0, D0108:0, D0121:0, D0115:0, D0111:0, D0272:1, D0080:6, D0010:2, D0207:4, D0078:0 |
| 6 | 3 | search_chunks {"doc_ids":null,"query":"incident writeup fallback enabled mitigation region model","search_mode":"keyword"} | 12 | 5 | 0 | 成功 | D0115:0, D0112:0, D0104:0, D0108:0, D0110:0, D0059:4, D0249:1, D0022:2, D0272:1, D0059:5, D0297:2, D0023:3 |
| 7 | 4 | search_chunks {"doc_ids":null,"query":"postmortem enabled fallback routing lower-context model variant mitigation","search_mode":"keyword"} | 12 | 2 | 0 | 成功 | D0207:2, D0272:0, D0272:1, D0259:1, D0016:5, D0207:4, D0104:0, D0016:0, D0016:2, D0016:3, D0082:2, D0209:4 |
| 8 | 4 | search_chunks {"doc_ids":null,"query":"incident postmortem fallback activated mitigation different model region","search_mode":"vector"} | 12 | 0 | 0 | 成功 | D0207:4, D0115:0, D0113:0, D0104:0, D0118:0, D0067:3, D0108:0, D0112:0, D0105:0, D0272:0, D0080:0, D0209:5 |
| 9 | 5 | search_chunks {"doc_ids":null,"query":"postmortem mitigation enabled automatic fallback","search_mode":"keyword"} | 12 | 0 | 0 | 成功 | D0104:0, D0115:0, D0112:0, D0108:0, D0272:1, D0118:0, D0121:0, D0111:0, D0110:0, D0080:6, D0207:4, D0082:2 |
| 10 | 5 | search_chunks {"doc_ids":null,"query":"incident mitigation auto-fallback activated region model route","search_mode":"hybrid"} | 12 | 1 | 0 | 成功 | D0104:0, D0118:0, D0108:0, D0112:0, D0193:2, D0191:2, D0115:0, D0067:3, D0316:0, D0279:2, D0316:2, D0080:0 |

judge reasoning：

> The generated answer correctly identifies that 4 internal incident writeups describe activating automatic fallback as part of mitigation, matching the gold answer's core count and intent.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"automatic fallback to different model or region mitigation incident","search_mode":"hybrid","doc_ids":null} | 12 | 35 | 3 | 成功 | D0104:0, D0118:0, D0115:0, D0112:0, D0067:3, D0108:0, D0058:0, D0316:0, D0121:0, D0080:0, D0209:0, D0191:2 |
| 2 | 1 | search_chunks {"query":"internal incident writeup Redwood Inference","search_mode":"hybrid","doc_ids":null} | 12 | 24 | 3 | 成功 | D0220:0, D0223:0, D0207:1, D0206:3, D0207:0, D0108:0, D0139:0, D0080:4, D0124:0, D0165:0, D0207:3, D0207:2 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"postmortem mitigation activated fallback model region","search_mode":"hybrid"} | 12 | 5 | 1 | 成功 | D0104:0, D0115:0, D0112:0, D0108:0, D0118:0, D0207:4, D0110:0, D0272:1, D0209:4, D0080:0, D0107:0, D0117:0 |
| 4 | 2 | search_chunks {"doc_ids":null,"query":"incident enabled automatic fallback policy reroute overflow","search_mode":"hybrid"} | 12 | 2 | 0 | 成功 | D0104:0, D0115:0, D0118:0, D0067:3, D0112:0, D0110:0, D0108:0, D0274:0, D0279:0, D0249:1, D0116:0, D0195:1 |
| 5 | 3 | search_chunks {"doc_ids":null,"query":"mitigation enabled automatic fallback different model region postmortem","search_mode":"keyword"} | 12 | 2 | 0 | 成功 | D0104:0, D0118:0, D0115:0, D0112:0, D0108:0, D0272:1, D0121:0, D0111:0, D0110:0, D0010:2, D0080:6, D0048:0 |
| 6 | 3 | search_chunks {"doc_ids":null,"query":"activated automatic region fallback secondary region mitigation","search_mode":"keyword"} | 12 | 2 | 0 | 成功 | D0108:0, D0104:0, D0112:0, D0118:0, D0067:3, D0279:0, D0279:2, D0115:0, D0009:1, D0193:2, D0009:4, D0193:3 |
| 7 | 4 | search_chunks {"doc_ids":null,"query":"\"automatic fallback\" activated mitigation","search_mode":"keyword"} | 12 | 3 | 0 | 成功 | D0104:0, D0112:0, D0108:0, D0118:0, D0115:0, D0046:0, D0067:3, D0121:0, D0058:0, D0111:0, D0082:2, D0085:1 |
| 8 | 4 | search_chunks {"doc_ids":null,"query":"postmortem mitigation enabled fallback routing policy model variant lower context","search_mode":"keyword"} | 12 | 5 | 1 | 成功 | D0207:2, D0272:0, D0272:1, D0016:5, D0259:1, D0207:4, D0104:0, D0016:2, D0016:0, D0016:3, D0082:2, D0207:3 |
| 9 | 5 | read_chunks {"doc_ids":["D0106"],"ordinals":[0]} | 0 | 0 | 0 | 2 validation errors for ReadArguments<br>doc_id<br>  Field required [type=missing, input_value={'doc_ids': ['D0106'], 'ordinals': [0]}, input_type=dict]<br>    For further information visit https://errors.pydantic.dev/2.13/v/missing<br>doc_ids<br>  Extra inputs are not permitted [type=extra_forbidden, input_value=['D0106'], input_type=list]<br>    For further information visit https://errors.pydantic.dev/2.13/v/extra_forbidden | — |
| 10 | 5 | read_chunks {"doc_ids":["D0244"],"ordinals":[0]} | 0 | 0 | 0 | 2 validation errors for ReadArguments<br>doc_id<br>  Field required [type=missing, input_value={'doc_ids': ['D0244'], 'ordinals': [0]}, input_type=dict]<br>    For further information visit https://errors.pydantic.dev/2.13/v/missing<br>doc_ids<br>  Extra inputs are not permitted [type=extra_forbidden, input_value=['D0244'], input_type=list]<br>    For further information visit https://errors.pydantic.dev/2.13/v/extra_forbidden | — |
| 11 | 5 | read_chunks {"doc_ids":["D0252","D0253","D0267","D0286","D0316"],"ordinals":[0]} | 0 | 0 | 0 | 2 validation errors for ReadArguments<br>doc_id<br>  Field required [type=missing, input_value={'doc_ids': ['D0252', 'D0...0316'], 'ordinals': [0]}, input_type=dict]<br>    For further information visit https://errors.pydantic.dev/2.13/v/missing<br>doc_ids<br>  Extra inputs are not permitted [type=extra_forbidden, input_value=['D0252', 'D0253', 'D0267', 'D0286', 'D0316'], input_type=list]<br>    For further information visit https://errors.pydantic.dev/2.13/v/extra_forbidden | — |
| 12 | 5 | read_chunks {"doc_ids":["D0231","D0260"],"ordinals":[0]} | 0 | 0 | 0 | 2 validation errors for ReadArguments<br>doc_id<br>  Field required [type=missing, input_value={'doc_ids': ['D0231', 'D0260'], 'ordinals': [0]}, input_type=dict]<br>    For further information visit https://errors.pydantic.dev/2.13/v/missing<br>doc_ids<br>  Extra inputs are not permitted [type=extra_forbidden, input_value=['D0231', 'D0260'], input_type=list]<br>    For further information visit https://errors.pydantic.dev/2.13/v/extra_forbidden | — |
| 13 | 6 | read_chunks {"doc_id":"D0106","ordinals":[0]} | 1 | 0 | 0 | 成功 | D0106:0 |
| 14 | 6 | read_chunks {"doc_id":"D0244","ordinals":[0]} | 1 | 0 | 0 | 成功 | D0244:0 |
| 15 | 6 | read_chunks {"doc_id":"D0252","ordinals":[0]} | 1 | 6 | 1 | 成功 | D0252:0 |
| 16 | 6 | read_chunks {"doc_id":"D0253","ordinals":[0]} | 1 | 8 | 1 | 成功 | D0253:0 |
| 17 | 6 | read_chunks {"doc_id":"D0267","ordinals":[0]} | 1 | 0 | 0 | 成功 | D0267:0 |
| 18 | 6 | read_chunks {"doc_id":"D0286","ordinals":[0]} | 1 | 3 | 1 | 成功 | D0286:0 |
| 19 | 6 | read_chunks {"doc_id":"D0316","ordinals":[0]} | 1 | 0 | 0 | 成功 | D0316:0 |
| 20 | 6 | read_chunks {"doc_id":"D0231","ordinals":[0]} | 1 | 0 | 0 | 成功 | D0231:0 |
| 21 | 6 | read_chunks {"doc_id":"D0260","ordinals":[0]} | 1 | 0 | 0 | 成功 | D0260:0 |

judge reasoning：

> The generated answer correctly identifies the number (4) and all the same incident dates as the gold answer, with additional consistent details that do not contradict the gold.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> 4 internal incident writeups describe activating automatic fallback as part of mitigation (2025-02-11, 2025-03-03, 2025-06-08, and 2025-07-22).

**naive 最终答案**

> Based on the documents, **4 internal incident writeups** describe activating automatic fallback as part of mitigation:
> 
> 1. **D0115** – EU-West capacity shortage: activated automatic *region* fallback (eu-west-1 → us-east-1)
> 2. **D0104** – Hosted API latency spike: activated automatic *model* fallback (70B → 8B)
> 3. **D0112** – Dedicated cluster degradation: activated automatic fallback to Hosted pool
> 4. **D0108** – Private VPC egress disruption: activated automatic *region* fallback (us-east-1 → us-west-2)
> 
> (D0118 mentions auto-fallback but only as the incident cause/being disabled, not activated as mitigation.)

**community 最终答案**

> **4**
> 
> The internal incident writeups that describe activating automatic fallback (to a different model or region) as part of mitigation are:
> 1. **D0104** (2025-02-11) – automatic model fallback (70b → 8b)
> 2. **D0115** (2025-03-03) – automatic region fallback (eu-west-1 → us-east-1)
> 3. **D0108** (2025-07-22) – automatic region fallback (us-east-1 → us-west-2)
> 4. **D0112** (2025-06-08) – automatic fallback to a Hosted pool
> 
> (D0118 and INC-9821/D0272 involve fallback but not as an explicitly described "automatic fallback" mitigation; D0118's fallback was the incident itself.)

</details>

<a id="case-enterprise_rag_bench-qst_0443"></a>

### enterprise_rag_bench:qst_0443 — 评分与执行路径对照

**问题：** List every internal communication thread (email, Slack, and meeting notes) about the Redwood Private upgrade 'rollback loop' bug (including references to RRB-17 or 'stuck rollback').

**score：4→4（Δ+0）；rounds：4→3（Δ-1）。**

工具安排：naive 为第1轮2次、第2轮2次、第3轮1次；community 为第1轮2次、第2轮2次。最终回答另占一轮。

轮次减少 1，工具总数 5→4、错误 2→1，整轮全部工具报错的轮数 1→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 18→24、文档 overview 12→42；工具结果字符数 66,263→119,005，QA token 57,316→55,242。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具名与解析后的参数完全一致。首个工具返回的有序 chunk ID 也相同；这是较接近受控的开局，但仍非重复实验或独立消融。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/a207a2b302b3474ebe4cc1ce7dbd8374.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/17998e9b942743e2b5d11a3fe1595b73.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Redwood Private upgrade rollback loop bug","search_mode":"hybrid","doc_ids":null} | 12 | 9 | 0 | 成功 | D0194:1, D0313:0, D0155:0, D0194:0, D0196:0, D0081:0, D0312:0, D0084:0, D0070:0, D0081:5, D0128:0, D0128:4 |
| 2 | 1 | search_chunks {"query":"RRB-17 stuck rollback","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0196:0, D0313:0, D0312:0, D0196:1, D0194:0, D0119:0, D0070:7, D0034:0, D0059:2, D0155:0, D0119:1, D0081:5 |
| 3 | 2 | read_chunks {"doc_id":"D0196","ordinals":[1,2,3]} | 0 | 0 | 0 | Unknown chunk ordinal | — |
| 4 | 2 | read_chunks {"doc_id":"D0155","ordinals":[1,2]} | 0 | 0 | 0 | Unknown chunk ordinal | — |
| 5 | 3 | read_chunks {"doc_id":"D0194","ordinals":[1]} | 1 | 0 | 0 | 成功 | D0194:1 |

judge reasoning：

> The generated answer accurately identifies and lists all five internal communication threads with correct titles, participants, and key references to RRB-17, stuck rollback, and workarounds, while adding only non-contradictory extra context.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"Redwood Private upgrade rollback loop bug","search_mode":"hybrid","doc_ids":null} | 12 | 18 | 2 | 成功 | D0194:1, D0313:0, D0155:0, D0194:0, D0196:0, D0081:0, D0312:0, D0084:0, D0070:0, D0081:5, D0128:0, D0128:4 |
| 2 | 1 | search_chunks {"query":"RRB-17 stuck rollback","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0196:0, D0313:0, D0312:0, D0196:1, D0194:0, D0119:0, D0070:7, D0034:0, D0059:2, D0155:0, D0119:1, D0081:5 |
| 3 | 2 | read_chunks {"doc_id":"D0196","ordinals":[1,2]} | 0 | 0 | 0 | Unknown chunk ordinal | — |
| 4 | 2 | search_chunks {"doc_ids":null,"query":"meeting notes rollback loop incident internal discussion","search_mode":"hybrid"} | 12 | 21 | 2 | 成功 | D0196:1, D0155:0, D0116:0, D0313:0, D0196:0, D0215:0, D0074:1, D0212:4, D0194:1, D0194:0, D0158:0, D0315:0 |

judge reasoning：

> The generated answer accurately identifies all five internal communication threads from the gold answers, capturing the key RRB-17 / 'stuck rollback' references and relevant context with only minor acceptable paraphrasing.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Internal threads about the Redwood Private upgrade "rollback loop"/"stuck rollback" bug (RRB-17) are: (1) Slack **#eng** thread where Ethan Park reports "private upgrade rollbacks looping" and Priya references "RRB-17" and the `installer-rollback-lock` ConfigMap workaround; (2) Slack **#incidents** thread **INC-2147** ("Private installer rollbacks looping (possible RRB-17)") covering customer impact, workaround, and patch tracking; (3) Email thread **"Re: Urgent: Redwood Private upgrade keeps rolling back"** (Nina Shah ↔ Ava Chen, cc Jordan Blake/Ethan Park) discussing "rollback stuck" and sharing the lock-delete + controller-restart workaround; (4) Internal email thread **"RRB-17: rollback loop in private installer (root cause + patch plan)"** (Priya ↔ Ethan/Dev/Jordan) detailing root cause, patch plan, and workaround; and (5) Meeting notes **"Acme - Private upgrade escalation (rollback keeps re-triggering)"** (2026-02-14) documenting the "rollback keeps re-triggering"/"stuck rollback" discussion and the same workaround.

**naive 最终答案**

> Based on the context, the internal communication threads about the Redwood Private "rollback loop" bug (RRB-17 / stuck rollback) are:
> 
> 1. **Email thread — D0196**: "RRB-17: rollback loop in private installer (root cause + patch plan)" (Priya Natarajan, Ethan Park, Dev Patel, Jordan Blake; Feb 13, 2026) — root cause, patch plan, runbook update, customer-safe wording.
> 2. **Email thread — D0194**: "Re: Urgent: Redwood Private upgrade keeps rolling back" (Ava Chen, Ethan Park, Jordan Blake, customer Nina Shah; Feb 12, 2026) — customer-reported stuck rollback, identified as likely RRB-17, workaround shared.
> 3. **Slack #eng thread — D0312**: "Looping Private Upgrade Rollbacks" (Ethan Park, Priya Natarajan, Diego Fernandez, Ava Chen) — reports of "stuck rollback", correlation with RRB-17, workaround, runbook snippet, INT ticket.
> 4. **Slack #incidents thread — D0313**: "INC-2147" (Incident Bot, Jordan Blake, Ava Chen, Ethan Park, Priya Natarajan, Dev Patel) — incident opened for looping installer rollbacks (possible RRB-17), impacting Acme and Northwind.
> 5. **Meeting notes — D0155**: "Acme Private upgrade escalation (rollback keeps re-triggering)" (Ava Chen, Ethan Park, Nina Shah, Omar Raza; 2026-02-14) — escalation call discussing the rollback loop / stuck rollback and the workaround.
> 
> (Other documents found, such as runbooks and policies, are documentation, not communication threads.)

**community 最终答案**

> Internal communication threads about the Redwood Private rollback loop bug (RRB-17 / "stuck rollback"):
> 
> 1. **Email thread** (D0194): "Re: Urgent: Redwood Private upgrade keeps rolling back" — Nina Shah (Acme) with Ava Chen, Jordan Blake, Ethan Park (Feb 12, 2026). References "stuck rollback / rollback loop we saw (likely RRB-17)".
> 
> 2. **Email thread** (D0196): "Fwd: RRB-17: rollback loop in private installer (root cause + patch plan)" — Priya Natarajan, Ethan Park, Dev Patel, Jordan Blake (Feb 13, 2026). References RRB-17 root cause, patch plan, workaround.
> 
> 3. **Slack thread** (D0312): "#eng" — Ethan Park, Priya Natarajan, Diego Fernandez, Ava Chen. Discusses looping rollbacks, "stuck rollback," RRB-17, workaround, runbook snippet, INT ticket.
> 
> 4. **Slack thread** (D0313): "#incidents" (INC-2147) — Jordan Blake, Ava Chen, Ethan Park, Priya Natarajan, Dev Patel. References "possible RRB-17" and "upgrade rollback stuck."
> 
> 5. **Meeting notes** (D0155): "Acme Private Upgrade Escalation: Rollback Loop Workaround" — escalation call (2026-02-14) with Ava Chen, Ethan Park, Nina Shah, Omar Raza. Discusses rollback loop/"stuck rollback" (known bug, patch in 2.9.1); does not use "RRB-17" explicitly.

</details>

<a id="case-enterprise_rag_bench-qst_0445"></a>

### enterprise_rag_bench:qst_0445 — 概览暴露更多短文档，试读失败仍未补齐发布计划

**问题：** "What is the complete required content of a production rollout plan for introducing a new LLM model version on Redwood Inference (hosted, dedicated, and private), including required metrics/thresholds, approvals, rollback/fallback rules, and customer-facing communications?"

**score：2→2（Δ+0）；rounds：3→5（Δ+2）。**

community 为 5 轮、10 次工具、5 次读取错误；naive 为 3 轮、4 次工具、1 次错误；两边均为 2 分。community 最后一个工具轮只有越界读取，额外尝试没有补齐 Private maintenance window、data residency、精确 SLO thresholds 等缺项。可见问题是从概览拿到 doc_id 后不知道合法 chunk 范围，以及缺少“生产发布计划”的必填要素检查。不能把五个错误直接等价为五轮，因为同轮可以并发多个调用。

工具安排：naive 为第1轮2次、第2轮2次；community 为第1轮2次、第2轮4次、第3轮3次、第4轮1次。最终回答另占一轮。

轮次增加 2，工具总数 4→10、错误 1→5，整轮全部工具报错的轮数 0→1。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 21→23、文档 overview 16→56；工具结果字符数 83,638→135,642，QA token 43,805→135,810。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/78877c4d935a4591bfc3e584ee8e616d.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/3061b8a8f1a64b61be8a37c7dad0218b.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"production rollout plan introducing new LLM model version Redwood Inference","search_mode":"hybrid","doc_ids":null} | 12 | 10 | 0 | 成功 | D0132:0, D0218:1, D0140:0, D0218:0, D0125:0, D0003:0, D0017:0, D0140:1, D0029:0, D0053:0, D0129:0, D0058:0 |
| 2 | 1 | search_chunks {"query":"rollout plan metrics thresholds approvals rollback fallback customer communication","search_mode":"hybrid","doc_ids":null} | 12 | 6 | 0 | 成功 | D0132:1, D0068:0, D0029:0, D0125:0, D0121:0, D0058:0, D0119:5, D0056:0, D0036:0, D0058:1, D0126:1, D0132:0 |
| 3 | 2 | read_chunks {"doc_id":"D0058","ordinals":[2]} | 0 | 0 | 0 | Unknown chunk ordinal | — |
| 4 | 2 | read_chunks {"doc_id":"D0125","ordinals":[1]} | 1 | 0 | 0 | 成功 | D0125:1 |

judge reasoning：

> The generated answer captures the overall structure and many key approvals/comms details, but it omits important required specifics (exact SLO fail/pass thresholds and windows for several metrics, rollout_slo_guard alert bundle, status-page triggers, and some Private rollback/pinning requirements) and includes slight inaccuracies, making it only partially complete.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"production rollout plan new LLM model version Redwood Inference hosted dedicated private","search_mode":"hybrid","doc_ids":null} | 12 | 37 | 5 | 成功 | D0218:0, D0140:0, D0218:1, D0132:0, D0140:1, D0029:0, D0125:0, D0017:0, D0003:0, D0129:0, D0068:0, D0053:0 |
| 2 | 1 | search_chunks {"query":"rollout plan required metrics thresholds approvals rollback fallback customer communication","search_mode":"hybrid","doc_ids":null} | 12 | 19 | 3 | 成功 | D0132:1, D0068:0, D0125:0, D0029:0, D0121:0, D0058:0, D0036:0, D0126:1, D0132:0, D0058:1, D0056:0, D0128:1 |
| 3 | 2 | read_chunks {"doc_id":"D0132","ordinals":[2]} | 0 | 0 | 0 | Unknown chunk ordinal | — |
| 4 | 2 | read_chunks {"doc_id":"D0085","ordinals":[0]} | 1 | 0 | 0 | 成功 | D0085:0 |
| 5 | 2 | read_chunks {"doc_id":"D0125","ordinals":[1]} | 1 | 0 | 0 | 成功 | D0125:1 |
| 6 | 2 | read_chunks {"doc_id":"D0058","ordinals":[2]} | 0 | 0 | 0 | Unknown chunk ordinal | — |
| 7 | 3 | read_chunks {"doc_id":"D0085","ordinals":[1]} | 1 | 0 | 0 | 成功 | D0085:1 |
| 8 | 3 | read_chunks {"doc_id":"D0058","ordinals":[3]} | 0 | 0 | 0 | Unknown chunk ordinal | — |
| 9 | 3 | read_chunks {"doc_id":"D0017","ordinals":[1]} | 0 | 0 | 0 | Unknown chunk ordinal | — |
| 10 | 4 | read_chunks {"doc_id":"D0058","ordinals":[2]} | 0 | 0 | 0 | Unknown chunk ordinal | — |

judge reasoning：

> The generated answer covers most metrics and core sections, but omits important required Private-specific details (customer-approved maintenance windows, data residency/retention/telemetry changes, network/identity/RBAC dependencies, post-upgrade validation) and specific status-page/incident triggers, so it is incomplete for a fully correct rollout plan.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> A production rollout plan for a new LLM model version on **Redwood Inference (Hosted, Dedicated, and Private)** must be a published plan (linked from the change ticket, using the canonical template) that includes: **(1) Summary** (what/why/expected impact and on-point owner + Slack), **(2) Scope** (Hosted/Dedicated/Private, regions, request types, customer tiers/allowlists), **(3) Versioning & compatibility** (alias, new immutable version id, backward-compat notes for tool-calling/format/limits, max context/output tokens) and links to **READY_FOR_PROD readiness artifacts** (functional compatibility, performance profile, reliability/failure modes, quality baseline, operational ownership/oncall + dashboards), **(4) Success criteria/guardrails with an explicit pass/fail threshold table and windows** using (or stricter than) the required SLOs: 5xx rate pass **≤ baseline +0.05% over 30m** / fail **> baseline +0.20% over 15m**; timeout rate pass **≤ baseline +0.03% over 30m** / fail **> baseline +0.10% over 15m**; admission rejects pass **≤0.5% over 30m** / fail **>2.0% over 10m**; p95 latency (non-streaming) pass **≤ +5% vs baseline over 30m** / fail **> +10% over 15m**; TTFT (streaming) pass **≤ +10% over 30m** / fail **> +25% over 15m**; long-tail fail **p99 > 2.5× baseline for 10m**; capacity fail **GPU saturation >92% for 15m with rising queue time**; tokens/sec/GPU pass **≥ baseline −3% over 60m** / fail **< baseline −8% over 30m**; cache hit rate pass **within −5% abs over 60m** / fail **within −15% abs over 30m**; quality pass **eval ≥ baseline −0.3** / fail **< baseline −0.7**, plus fail if **2+ reproducible customer quality reports within 24h** (canary/ramp decision windows are **≥30m**, full validation **24h after 100%**), **(5) Monitoring plan** (dashboard links, trace/log queries, alert list and owners) and enabling the **rollout_slo_guard** alert bundle (paged SRE on any fail threshold; notify platform/runtime channels), **(6) Rollout steps/strategy** (canary and ramp schedule with decision points recorded; recommended 0.5%→5%→25%→50%→100% with minimum observation windows; blast-radius controls such as per-region caps, max traffic %, allowlists, concurrency caps; A/B plan if used), **(7) Rollback & fallback rules** that map each fail threshold to an action and explicitly define Router policy requirements-**primary version id, ordered fallback chain (must include prior default when making a new default), health-check gates for automatic fallback (5xx/timeouts/saturation), blast-radius controls, and the rollback target policy id**-plus what happens to in-flight/streaming requests; rollback procedure is restoring the prior policy, setting new version traffic to 0%, and confirming recovery within ~15 minutes (escalate if not), and **automatic fallback must trigger** on sustained fail-threshold 5xx/timeouts/admission rejects (noting fallback can mask quality, so quality guardrails still apply), **(8) Customer communications plan** (who is notified, when, channels, and required message content; links to support tickets/emails) following: always notify **Dedicated customers** getting a new default and **all impacted Private customers**; notify Hosted customers for material behavior changes (format/tool-calling/limits/latency/reliability/safety); timing is **Dedicated ≥5 business days**, **Private per contract (default 10 business days)**, **Hosted ≥72h** for material changes (otherwise release notes); messages must include what/why/when (TZ/duration)/best- & worst-case impact/opt-out or pinning path/support contact/rollback posture, and comms must be reviewed by **Customer Success owner + Inference PM** (plus **Security** for regulated Private), and **(9) Approvals & change window** including change class (1-3), approvers and timestamps, and approved window (Hosted/Dedicated prefer Tue-Thu 09:00-14:00 PT; Private must match customer window): Class 1 requires **Oncall Eng Manager or Platform Eng TL**; Class 2 requires **Platform Eng Manager + SRE oncall delegate + Inference PM**; Class 3 requires **VP Eng (or delegate) + Product Director+ and Security if compliance-impacting**; additional mandatory approvers when triggered include **Solutions Eng lead + Private Deployments Eng TL** (any Private), **Customer Success Director** (SLA/contract impact), and **Security & Compliance** (data residency/retention impact). For **Private** rollouts, the plan must also include customer-approved maintenance windows (local time, approver, downtime requirement), current pinning/opt-out and how long the prior version stays available (**≥30 days unless contract says otherwise**), confirmation rollback artifacts are pre-staged and verified, data residency/retention/telemetry changes, network/identity/RBAC dependencies with customer approval, and customer-specific post-upgrade validation; rollback must occur if fail thresholds hit during the window or if the customer requests it. Finally, the plan must specify **status page/incident comms** triggers (e.g., widespread Hosted impact >15m, Private impact outside window, or rollback after >25% ramp/after notifications) and commit to post-rollout validation and documentation (including outcome notes within 48h).

**naive 最终答案**

> The required content of a production rollout plan (per the Change Management Policy, canonical template, readiness standard, and supporting runbooks) is:
> 
> **1. Summary** — what is changing, why now, expected customer impact (best/worst case), who is on point (name + Slack channel).
> 
> **2. Scope** — environments (Hosted/Dedicated/Private), regions, customer tiers/allowlists, request types (chat/completions/embeddings/rerank).
> 
> **3. Versioning & compatibility** — model alias, new version id, backward-compatibility notes (tool calling schema, output formatting, tokenization), max context/output token limits.
> 
> **4. Success criteria / guardrails (explicit pass/fail thresholds + evaluation window), minimum categories:**
> - Reliability: 5xx rate, timeouts, admission rejects (e.g., pass ≤ +0.05% absolute, fail > +0.2% absolute; 5xx > 0.5% for 10 min aborts canary)
> - Latency: p50/p95 end-to-end and TTFT for streaming (e.g., p95 pass ≤ +5% vs baseline, fail > +10%; rollback if TTFT p95 regresses >20% for 30 min)
> - Cost/efficiency: tokens/sec/GPU, cache hit rate, batch efficiency
> - Quality: regression guardrail (eval set delta, e.g., pass ≥ baseline −0.3, fail < baseline −0.7) and customer-reported issues
> - Table must include metric, window, pass threshold, fail threshold, owner.
> 
> **5. Monitoring** — dashboard links, alerts to enable, trace/log queries, who watches what at each ramp step.
> 
> **6. Rollout strategy** — canary design (e.g., 0.5% → 5% → 25% → 50% → 100% with decision points), ramp schedule with timestamps, controls (per-customer allowlist, per-region traffic caps, concurrency caps), A/B plan if used.
> 
> **7. Rollback and fallback rules** — rollback triggers (must map to thresholds), rollback procedure reference, automatic fallback policy (target versions, ordering, constraints; fallback only to compatible versions; triggers = sustained 5xx/timeouts/admission rejects above fail threshold; keep old version as first fallback ≥7 days; for defaults, canary to ≥25% for ≥2h and documented fallback chain including prior default), handling of in-flight/streaming requests.
> 
> **8. Customer communications** — who must be notified (all Dedicated default recipients, all impacted Private customers; Hosted only on material behavior changes), channels (email + support ticket for Dedicated/Private; release notes for Hosted; status page if incident), timing (Dedicated ≥5 business days; Private default 10 business days per contract; Hosted ≥72h for material changes), required message content (what/why/when, impact, opt-out/pinning path with ≥30-day pinning offer, help channel, rollback posture), and approvals (Customer Success owner + inference PM; Security for regulated Private).
> 
> **9. Approvals and change window** — change class; approvers by class (Class 1: oncall Eng Manager or Platform Eng TL; Class 2: Platform Eng Manager + SRE oncall delegate + PM for inference; Class 3: VP Eng + Security + Product Director+; plus Private: Solutions Eng lead + Private Deployments Eng TL; SLA impact: CS Director; data residency: Security & Compliance); approved window (Hosted/Dedicated preferred Tue–Thu 09:00–14:00 PT; Private per customer window, zero-downtime/no-impact confirmation, artifact pre-staging, data residency/network identity checks).
> 
> **10. Post-rollout validation** — final KPIs after full ramp, customer feedback, follow-up tasks/owners; outcome note within 48h; records retained 2 years.

**community 最终答案**

> **Required production rollout plan content (Hosted/Dedicated/Private):**
> 
> **Plan sections (all classes 1–3 must include; template link mandatory):** 1) Summary (what/why/customer impact best & worst case/on-point owner); 2) Scope (environments, regions, customer tiers/allowlists, request types); 3) Versioning & compatibility (alias, version id, backward compat notes, token limits); 4) Success criteria with explicit thresholds; 5) Monitoring plan (dashboards, alerts, owners); 6) Rollout steps (canary %, ramp schedule, decision points, controls); 7) Rollback & fallback rules; 8) Customer communications plan; 9) Approvals & change window; 10) Post-rollout validation (final KPIs, customer feedback, follow-ups). Post-change outcome note within 48h; records retained 2 years.
> 
> **Required metrics/thresholds (min; may be stricter):** Windows: canary 30 min min; ramp step 30 min min (or 2× p95 duration); 24h full-rollout validation.
> - 5xx: pass ≤ baseline +0.05% abs/30min; fail > +0.20% abs/15min
> - Timeouts: pass ≤ baseline +0.03%/30min; fail > +0.10%/15min
> - Admission rejects: pass ≤0.5%/30min; fail >2.0%/10min
> - p95 E2E: pass ≤ +5% vs baseline/30min; fail > +10%/15min
> - TTFT (streaming): pass ≤ +10%/30min; fail > +25%/15min
> - p99: fail >2.5× baseline for 10min
> - GPU saturation: fail sustained >92% for 15min
> - tokens/sec/GPU: pass ≥ baseline −3%/60min; fail < −8%/30min
> - Cache hit: pass within −5% abs/60min; fail within −15% abs/30min
> - Eval delta: pass ≥ baseline −0.3; fail < baseline −0.7
> - Customer quality: fail on 2+ independent reproducible reports within 24h
> Enable `rollout_slo_guard` alert bundle (alias/version/region) during any ramp; pages SRE on fail.
> 
> **Approvals:** Class 1: Oncall Eng Mgr OR Platform Eng TL. Class 2: Platform Eng Mgr + SRE oncall delegate + PM (inference). Class 3: VP Eng + Security + Product (Director+). Additional: Private → Solutions Eng lead + Private Deployments Eng TL; SLA/contract → CS Director; data residency → Security & Compliance. Comms must be reviewed by CS owner + inference PM (+ Security for regulated Private). Change window: Hosted/Dedicated Tue–Thu 09:00–14:00 PT; Private per customer window.
> 
> **Rollback/fallback:** Fallback triggers: sustained 5xx above fail threshold, sustained timeouts, admission rejects from saturation; fallback only to request-type-compatible versions, ordered chain; each fail threshold must map to automatic fallback, manual rollback, or pause-and-investigate. Rollback = restore prior known-good policy in all regions, disable new-version traffic, confirm baseline within 15 min. Default versions additionally need canary ≥25% traffic ≥2h and documented fallback chain incl. prior default (keep old model as first fallback ≥7 days). Private: rollback artifacts pre-staged/verified, prior version runnable, pin available ≥30 days, rollback on threshold fail or customer request with explicit decision-maker and comms channel.
> 
> **Customer communications:** Always notify Dedicated customers receiving new default and impacted Private customers; notify Hosted only for material changes (output format/tool calling, token limits, latency/reliability, safety). Timing: Dedicated ≥5 business days; Private per contract (default 10 business days); Hosted ≥72h for material changes, else release notes. Required message content: what (alias + version id), why (benefit), when (date/time/timezone/duration), impact (best/worst case), opt-out/pin path (pin old version ≥30 days), support channel + escalation, rollback posture. Channels: Dedicated/Private email + support ticket; Hosted release notes (optional email to top orgs); status page rules for incidents/wide impact. Plan must link tickets and note when comms were sent.

</details>

<a id="case-enterprise_rag_bench-qst_0447"></a>

### enterprise_rag_bench:qst_0447 — 评分与执行路径对照

**问题：** What is Redwood Inference's complete end-to-end process for shipping an emergency serving-runtime hotfix to production (Hosted + Dedicated), including required approvals, checklists, rollout/rollback steps, and mandatory customer communications?

**score：4→3（Δ-1）；rounds：2→2（Δ+0）。**

工具安排：naive 为第1轮2次；community 为第1轮2次。最终回答另占一轮。

两边均为 2 轮，但工具总数 2→2，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 16→19、文档 overview 14→36；工具结果字符数 76,214→97,371，QA token 21,949→27,007。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/a811894ca9ab4982b01a9a1d79c86439.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/84c152edca8c4e7d8546e0b00e5d8066.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"emergency serving-runtime hotfix production process approvals checklist rollout rollback","search_mode":"hybrid","doc_ids":null} | 12 | 10 | 0 | 成功 | D0127:0, D0074:0, D0056:0, D0127:1, D0035:0, D0075:0, D0036:0, D0034:1, D0126:0, D0125:0, D0034:0, D0129:0 |
| 2 | 1 | search_chunks {"query":"emergency hotfix customer communication Hosted Dedicated production","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0036:0, D0127:0, D0100:0, D0123:0, D0029:0, D0056:0, D0126:0, D0127:1, D0089:0, D0129:0, D0074:0, D0075:0 |

judge reasoning：

> The generated answer fully captures the gold-standard end-to-end hotfix process, including required approvals, checklist, rollout/rollback steps, and customer communications, with only minor wording differences and consistent additional detail.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"emergency serving-runtime hotfix production release process","search_mode":"hybrid","doc_ids":null} | 12 | 32 | 4 | 成功 | D0035:0, D0074:0, D0127:0, D0127:1, D0056:0, D0075:0, D0036:0, D0034:0, D0034:1, D0126:0, D0075:1, D0021:0 |
| 2 | 1 | search_chunks {"query":"hotfix rollback customer communication checklist approval","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0036:0, D0127:0, D0127:1, D0074:0, D0100:0, D0029:0, D0125:1, D0056:0, D0126:1, D0068:0, D0128:3, D0211:0 |

judge reasoning：

> The generated answer is highly detailed and largely matches the gold standard, covering approvals, PR, signing, validation, rollouts, rollback triggers, communications, and closeout. However, it omits a few specific required details: the full minimum checklist fields (e.g., blast radius), the 15-minute minimum monitoring per Hosted expansion step (only says 'wait for steady state'), and crash loops as an explicit rollback trigger. These are minor omissions/imprecisions rather than major errors, so it is not a perfect match.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> To ship an emergency **serving-runtime hotfix** to production (Hosted + Dedicated), Redwood Inference follows this end-to-end process:
> 
> 1) **Open the emergency change + record the minimum checklist** (in a Linear/Jira ticket and the incident timeline/thread): state the fix hypothesis, what's changing (code/config/infra), blast radius (Hosted regions, Dedicated clusters/customers, model families), risk assessment (security/data/perf), a **rollback plan with explicit triggers**, and who owns post-change monitoring; ensure an incident channel/thread exists with an identified IC.
> 
> 2) **Get required approvals (no exceptions):** two-person approval from **(a) IC (or SRE on-call)** and **(b) the serving-runtime Service Owner (or delegate)**, recorded in PR review/incident thread/change record. Add scenario-based approvals as applicable: **Security on-call** (security/exploit), **Product on-call/PM** (customer-visible behavior changes), and **Customer Success Escalation Manager (CSEM)** when Dedicated/customer maintenance coordination is required.
> 
> 3) **Prepare the hotfix PR (Serving Runtime Hotfix Runbook):** cut `hotfix/runtime-<YYYYMMDD>-<short-issue>`, cherry-pick only the minimal fix, update the Runtime Hotfixes changelog, open a PR (prefer release branch), and obtain emergency reviews from **runtime on-call + SRE on-call (or IC)**; include incident link, risk, rollback, and rollout owners.
> 
> 4) **Build + supply-chain sign artifacts (mandatory):** run the approved hotfix build pipeline to produce the new runtime image in the production registry plus **SBOM** and **provenance attestation**, and **verify cosign signatures/attestations before rollout**; image signing cannot be skipped (SBOM delay is only allowed with Security on-call approval and must be attached within 4 hours).
> 
> 5) **Validate before rollout (minimum required even in Sev-1):** run unit tests for the affected module, one perf canary for a representative model, and a stress test matching the incident pattern; record results in the PR confirming error-rate improvement, **no >10% p95 regression** (same workload), and no increase in OOM/GPU reset counters.
> 
> 6) **Post rollout notes to the incident channel:** new runtime image tag, expected rollout impact (restarts/brief resets), the **canary target**, and **rollback criteria** (metrics + customer symptom). A canary is required unless explicitly waived by IC (with rationale recorded).
> 
> 7) **Roll out to Hosted (Platform/SRE; Hosted Rollout + Rollback Procedure):** announce rollout start + tag; set `runtime_image_tag=<new-tag>` and sync via ArgoCD (`hosted-runtime`). Roll out in order **us-west-2a canary (10%) → us-west-2 (50%) → us-east-1 (50%) → eu-central-1 (50%) → global**, monitoring each step for at least 15 minutes (success rate, p95 for top routes, GPU OOM, router fallback, error-budget burn). **Rollback immediately** by reverting to the last-known-good tag and ArgoCD syncing if 5xx/stream aborts persist >5 min, OOM spikes >2× baseline, p95 regresses >20% for >10 min, crash loops appear, or customer reports correlate with rollout start; announce rollback and next steps in the incident channel.
> 
> 8) **Roll out to Dedicated (Infra + CSEM; Dedicated Cluster Hotfix Rollout Notes):** collect required inputs (customer/cluster ID, current/target tags, expected restart impact, rollback tag, scope), obtain approvals (**IC/SRE + Dedicated service owner + CSEM sign-off on messaging**), and **communicate to customers** (unless IC explicitly waives due to active outage): state brief interruption risk, provide a rollout window, and describe rollback criteria in plain language. Canary one Dedicated cluster first (prefer internal dogfood/lowest-traffic with CSEM approval) and validate ~30 minutes (success rate, p95, OOM, restart frequency, customer health checks); then schedule remaining clusters, rolling **no more than 3 in parallel unless IC approves**. Per cluster: confirm comms sent, update Helm `runtime_image_tag`, ArgoCD sync `dedicated-<cluster-id>-runtime`, watch for CrashLoopBackOff, run customer smoke checks (chat/embeddings/streaming). If rollback triggers hit, revert the tag, restart if needed, and **notify the customer immediately** (CSEM).
> 
> 9) **Mandatory Sev-1 customer communications (Status Page + Customer Notifications):** IC owns accuracy/cadence; CSEM owns direct enterprise/Dedicated outreach; initial acknowledgment **within 10 minutes**, updates **every 30 minutes** while impact continues, and a resolution message **within 15 minutes** of confirmed mitigation. Each update must include customer symptoms, affected surfaces (regions/clusters/models), mitigation steps, ETA with confidence level, and any workarounds; provide a post-incident summary within **1 business day** (required for enterprise).
> 
> 10) **Post-change closeout:** update the incident timeline with start/change/outcome, record cluster/region outcomes, and within **2 business days** complete incident follow-up (what changed and why it worked), document any release-process deviations/corrective actions, remove temporary flags/throttles (with owner + deadline), and create a task to promote the hotfix into the next regular release.

**naive 最终答案**

> **Complete end-to-end process for shipping an emergency serving-runtime hotfix (Hosted + Dedicated):**
> 
> **1. Approvals (per Emergency Change Policy v3, cannot be skipped)**
> - Two-person approval before production impact: (1) Incident Commander (or On-call SRE if not in incident mode) + (2) Service Owner (or delegate).
> - Additional: Security on-call (security/exploit), Product on-call/PM (customer-visible behavior change), Customer Success escalation manager (any customer-maintenance coordination for Dedicated/Private).
> - During Red change state: IC + service owner + SRE on-call.
> 
> **2. Build the hotfix (Serving Runtime Hotfix Runbook + Build/Signing)**
> - Cut branch `hotfix/runtime-<YYYYMMDD>-<short-issue>`; cherry-pick only the minimum fix; update CHANGELOG.
> - Open GitHub PR (target release branch or main) reviewed by runtime on-call + SRE on-call (or IC); PR includes incident link, hypothesis, risk, rollback, rollout owners.
> - Build/sign artifacts: cosign-signed multi-arch container image, CycloneDX SBOM, SLSA L3 provenance attestation (GitHub Actions `release-hotfix.yml`, label `hotfix-ready`); verify with cosign before rollout. Image signing cannot be skipped.
> - Validate: affected-module unit tests, one perf-canary (e.g., Llama 3.1 70B), one stress test at the incident pattern; triggering error must improve/eliminate, p95 not >10% worse, no OOM/GPU-reset increase.
> - Post rollout notes in incident channel: image tag, expected impact (restarts/connection resets), canary target, rollback criteria.
> 
> **3. Checklist (recorded in ticket/PR/incident timeline)**
> - Hypothesis, blast radius (Hosted regions; Dedicated clusters/customers; model families), rollback plan with explicit trigger, risk assessment (data integrity/security/performance), what is changing, monitoring owner. Ticket (Linear/Jira), GitHub PR/SHA, approvals, incident timeline updates.
> 
> **4. Hosted rollout (Platform/SRE per Hosted Rollout + Rollback Procedure)**
> - Canary us-west-2a @10% → us-west-2 @50% → us-east-1 @50% → eu-central-1 @50% → global (or canary in an unaffected region for region-specific issues). Minimum 15-min canary monitoring: success rate, p95 top-3 routes, GPU OOM, router fallback, error budget burn. Pass: no >0.2% sustained error increase, p95 not >10% worse, no crash-looping pods.
> - Execute: announce in incident channel/#eng-releases, set `runtime_image_tag`, ArgoCD sync `hosted-runtime`, wait for steady state before expanding.
> 
> **5. Dedicated rollout (Infra + CSEM per Dedicated Cluster Hotfix Rollout Notes)**
> - Gather customer/cluster ID, current/target/rollback tags, impact statement, issue scope.
> - Canary on one cluster first (dogfood or lowest-traffic, with CSEM approval); validate 30 min (success rate, p95, GPU OOM, restarts, customer health checks); schedule remaining clusters, max 3 in parallel unless IC approves.
> - Per cluster: confirm customer comms sent (or waived by IC), set `runtime_image_tag` in helm values, ArgoCD `dedicated-<cluster-id>-runtime`, watch for CrashLoopBackOff, run customer smoke checks (chat, embeddings, streaming).
> 
> **6. Mandatory customer communications (Sev-1 Comms Requirements)**
> - Status page (public) and/or targeted email; Slack #incidents. IC owns accuracy/cadence; CSEM owns direct enterprise outreach for Dedicated.
> - Cadence: initial ack within 10 min of Sev-1; updates every 30 min; resolution within 15 min of mitigation; post-incident summary within 1 business day. Content: symptoms, affected surfaces, mitigation, ETA with confidence, workarounds.
> - Dedicated hotfix: if restarting pods, send short note about brief interruptions, provide a time window, and rollback criteria in plain language (e.g., "revert within 15 minutes if errors increase").
> 
> **7. Rollback (per triggers; roll back immediately, don't wait for update cadence)**
> - Hosted triggers: elevated 5xx/stream aborts >5 min; GPU OOM >2x baseline; p95 regression >20% for >10 min; customer reports correlating with rollout. Procedure: revert `runtime_image_tag` to last known good, ArgoCD sync `hosted-runtime`, confirm steady state, post rollback in incident channel, update status page wording.
> - Dedicated triggers per emergency rollback runbook (TTFT >30% regression in 2+ regions for 10+ min, >2% generation-route errors, sustained canary degradation, GPU OOM/kernel crash loops): freeze/pause rollout, pin prior release tag per cluster (rw-release set-tag/deploy), verify health, lock tag to prevent auto-advance, notify customer immediately via CSEM.
> - Announce rollback in incident channel and update status page to reflect mitigation change.
> 
> **8. Post-change (within 2 business days)**
> - Incident review follow-up (root cause, change, why it worked); document deviations and corrective actions; remove temporary flags/throttles; update incident timeline; promote hotfix into the next regular release branch; record cluster-by-cluster outcomes.

**community 最终答案**

> **Complete emergency serving-runtime hotfix process (Hosted + Dedicated):**
> 
> **1. Preconditions:** Emergency-change approvals recorded; incident channel with IC identified; rollback plan exists (previous runtime image tag + restart procedure).
> 
> **2. Approvals (mandatory, cannot be skipped):**
> - Two-person approval: (a) IC (or on-call SRE if not incident mode) + (b) Service Owner.
> - Scenario add-ons: Security on-call (security/exploit), Product on-call/PM (customer-visible behavior change), Customer Success escalation manager (any customer maintenance coordination).
> 
> **3. Code (per runbook):**
> - Cut branch `hotfix/runtime-<YYYYMMDD>-<short-issue>`; cherry-pick only the minimum fix; update CHANGELOG.
> - Open GitHub PR (release branch preferred); reviewers: runtime on-call + SRE on-call (or IC); PR description includes incident link, hypothesis, risk, rollback, rollout owners.
> - Record ticket (Linear/Jira), PR/commit SHA, approvals, and incident timeline (start, change time, outcome).
> 
> **4. Build + sign:** Label `hotfix-ready`, trigger "Release Runtime Hotfix" (GitHub Actions; Buildkite fallback only if degraded). Artifacts: signed container image (cosign; signing cannot be skipped), CycloneDX SBOM, SLSA L3 provenance, in production registry. Verify with `cosign verify` + `verify-attestation` before rollout. Emergency exception (Security on-call approval, recorded in incident channel): only temporary SBOM upload delay, attached within 4 hours.
> 
> **5. Validation checklist (minimum):** Unit tests for affected module; one perf-canary (e.g., Llama 3.1 70B); one stress test at incident-triggering pattern. Pass: triggering error improves/eliminated, p95 no >10% regression vs previous image, no increase in OOM/GPU resets.
> 
> **6. Rollout notes (post in incident channel):** new image tag, expected impact (restarts/brief resets), canary target, rollback criteria (metrics + customer symptom).
> 
> **7. Hosted rollout:** Handoff to Platform/SRE. Order: canary us-west-2a (10%) → us-west-2 (50%) → us-east-1 (50%) → eu-central-1 (50%) → global (or canary unaffected region first if region-specific). Canary monitored ≥15 min (success rate, p95 top-3 routes, GPU OOM, router fallback, error-budget burn). Pass: no sustained error increase >0.2% abs, p95 ≤+10%, no new crash-looping pods. Execute: announce in incident channel/#eng-releases, set `runtime_image_tag`, ArgoCD sync `hosted-runtime`, wait for steady state before expanding.
> 
> **8. Dedicated rollout:** Handoff to Infra + CSEM. Gather customer name/cluster ID, current/target tags, impact statement, rollback tag, issue scope. Approvals: IC/SRE on-call, Dedicated service owner, CSEM sign-off on messaging. Canary one cluster first (dogfood/lowest traffic, CSEM approval), validate 30 min (success rate, p95, GPU OOM, restarts, customer health checks); then schedule others, max 3 clusters parallel unless IC approves. Per cluster: confirm comms sent (or waived by IC for active outage), set `runtime_image_tag`, ArgoCD `dedicated-<cluster-id>-runtime`, watch for CrashLoopBackOff, run customer smoke checks (chat, embeddings, streaming).
> 
> **9. Rollback (roll back immediately if triggers met — don't wait for update cadence):**
> - Hosted triggers: elevated 5xx/stream aborts >5 min; GPU OOM >2x baseline; p95 regression >20% >10 min; customer reports correlate with rollout start. Procedure: revert `runtime_image_tag` to last-known-good, ArgoCD sync, confirm steady state, post reason in incident channel.
> - Dedicated: revert image tag, restart deployment if needed, notify customer immediately (CSEM).
> - Announce rollback in incident channel and update status page wording to reflect mitigation change.
> 
> **10. Mandatory customer communications:**
> - Sev-1 cadence: initial ack within 10 min of declaration; updates every 30 min while impact ongoing; resolution within 15 min of mitigation; post-incident summary within 1 business day. Content: symptoms, affected surfaces (regions/clusters/model families), mitigation, ETA with confidence, workarounds. Status page when impact broad; email for Dedicated-specific impact.
> - Dedicated hotfix specifics: if runtime pods restart, send short note that brief interruptions may occur; provide time window (even approximate); provide plain-language rollback criteria (e.g., "revert within 15 minutes"). CSEM notifies impacted customers directly (email + optional call), including maintenance action, duration, failover status. Comms owned by IC (accuracy/cadence), CSEM (enterprise outreach), SRE on-call (technical status/ETA).
> 
> **11. Post-change (within 2 business days):** incident-review follow-up (root cause, change, why it worked), document deviations/corrective actions, remove temporary flags/throttles, update incident timeline, promote hotfix into next regular release, record cluster-by-cluster outcomes (Dedicated).

</details>

<a id="case-enterprise_rag_bench-qst_0450"></a>

### enterprise_rag_bench:qst_0450 — 评分与执行路径对照

**问题：** How many Fireflies sales-call transcripts mention a customer requirement for data residency (keeping data in a specific region/country)?

**score：0→0（Δ+0）；rounds：9→10（Δ+1）。**

工具安排：naive 为第1轮2次、第2轮2次、第3轮2次、第4轮2次、第5轮2次、第6轮2次、第7轮2次、第8轮2次；community 为第1轮2次、第2轮2次、第3轮2次、第4轮2次、第5轮2次、第6轮2次、第7轮2次、第8轮2次、第9轮2次。最终回答另占一轮。

轮次增加 1，工具总数 16→18、错误 0→1，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 69→81、文档 overview 38→123；工具结果字符数 421,620→504,198，QA token 520,870→808,051。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/2b6265565e05407793a832c40d85b18f.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/enterprise_rag_bench_80_naive_community/traces/73405ffc330b4895a076cda1940482e0.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"data residency requirement customer","search_mode":"hybrid","doc_ids":null} | 12 | 7 | 0 | 成功 | D0160:0, D0159:0, D0318:1, D0162:0, D0206:5, D0318:2, D0165:0, D0318:0, D0206:3, D0289:2, D0289:1, D0206:1 |
| 2 | 1 | search_chunks {"query":"keeping data in specific region country","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0161:0, D0163:5, D0162:0, D0141:2, D0164:0, D0163:1, D0159:1, D0318:1, D0289:2, D0141:1, D0159:0, D0206:4 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"data residency requirement customer call transcript meeting","search_mode":"vector"} | 12 | 0 | 0 | 成功 | D0160:0, D0318:0, D0163:0, D0318:2, D0159:0, D0162:0, D0318:1, D0165:0, D0161:0, D0206:2, D0206:0, D0206:1 |
| 4 | 2 | search_chunks {"doc_ids":null,"query":"residency hard requirement EU-only Germany UK in-country","search_mode":"keyword"} | 12 | 1 | 0 | 成功 | D0162:0, D0160:0, D0159:0, D0164:0, D0159:1, D0165:0, D0008:1, D0163:5, D0318:1, D0141:1, D0206:1, D0159:2 |
| 5 | 3 | search_chunks {"doc_ids":null,"query":"meeting transcript call residency data must stay region","search_mode":"keyword"} | 12 | 3 | 0 | 成功 | D0159:0, D0165:0, D0163:0, D0164:0, D0163:6, D0162:0, D0161:0, D0157:0, D0160:0, D0157:1, D0144:1, D0007:4 |
| 6 | 3 | search_chunks {"doc_ids":null,"query":"customer requires data not leave country border sovereignty","search_mode":"keyword"} | 12 | 1 | 0 | 成功 | D0164:0, D0162:0, D0163:0, D0163:3, D0161:0, D0141:4, D0141:1, D0163:5, D0163:1, D0008:5, D0008:4, D0209:2 |
| 7 | 4 | read_chunks {"doc_id":"D0157","ordinals":[1,2,3]} | 3 | 0 | 0 | 成功 | D0157:1, D0157:2, D0157:3 |
| 8 | 4 | search_chunks {"doc_ids":null,"query":"data residency region deployment meeting call transcript customer requirement","search_mode":"vector"} | 12 | 0 | 0 | 成功 | D0160:0, D0162:0, D0318:0, D0161:0, D0163:0, D0165:0, D0318:1, D0159:0, D0206:2, D0206:0, D0206:1, D0318:2 |
| 9 | 5 | search_chunks {"doc_ids":null,"query":"Fireflies.ai recorded transcript sales call","search_mode":"keyword"} | 12 | 6 | 0 | 成功 | D0157:1, D0158:11, D0157:0, D0267:0, D0135:4, D0007:4, D0225:5, D0137:0, D0158:0, D0163:6, D0032:1, D0032:2 |
| 10 | 5 | read_chunks {"doc_id":"D0157","ordinals":[3,4,5]} | 3 | 0 | 0 | 成功 | D0157:3, D0157:4, D0157:5 |
| 11 | 6 | search_chunks {"doc_ids":null,"query":"Fireflies recorded by auto-summary","search_mode":"keyword"} | 12 | 6 | 0 | 成功 | D0157:1, D0267:0, D0157:0, D0061:5, D0158:0, D0061:6, D0002:1, D0098:0, D0154:0, D0072:3, D0092:4, D0061:4 |
| 12 | 6 | search_chunks {"doc_ids":null,"query":"data residency requirement Fireflies call","search_mode":"keyword"} | 12 | 3 | 0 | 成功 | D0157:0, D0289:1, D0159:0, D0267:0, D0160:0, D0162:0, D0164:0, D0165:0, D0142:0, D0186:0, D0147:3, D0318:1 |
| 13 | 7 | search_chunks {"doc_ids":null,"query":"\"Fireflies\" recorded meeting","search_mode":"keyword"} | 12 | 4 | 0 | 成功 | D0157:1, D0157:0, D0267:0, D0158:0, D0158:11, D0224:8, D0052:6, D0215:0, D0002:1, D0164:0, D0072:3, D0081:0 |
| 14 | 7 | read_chunks {"doc_id":"D0158","ordinals":[0,1,2]} | 3 | 0 | 0 | 成功 | D0158:0, D0158:1, D0158:2 |
| 15 | 8 | search_chunks {"doc_ids":null,"query":"Fireflies recording transcript","search_mode":"keyword"} | 12 | 2 | 0 | 成功 | D0158:11, D0157:9, D0267:0, D0158:0, D0157:1, D0163:0, D0007:4, D0163:6, D0073:6, D0052:6, D0219:3, D0032:1 |
| 16 | 8 | search_chunks {"doc_ids":null,"query":"Recorded by Fireflies sales call data residency must stay US EU","search_mode":"keyword"} | 12 | 1 | 0 | 成功 | D0289:2, D0165:0, D0157:0, D0149:3, D0318:0, D0206:0, D0206:1, D0162:0, D0149:1, D0186:0, D0157:1, D0267:0 |

judge reasoning：

> The generated answer contradicts the gold answer by claiming only 1 transcript mentions data residency, whereas the gold answer states 8 transcripts, so it is incorrect.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"data residency requirement customer region country","search_mode":"hybrid","doc_ids":null} | 12 | 16 | 2 | 成功 | D0160:0, D0162:0, D0318:1, D0141:1, D0159:1, D0159:0, D0206:5, D0163:5, D0165:0, D0318:0, D0164:0, D0289:2 |
| 2 | 1 | search_chunks {"query":"Fireflies sales call transcript","search_mode":"hybrid","doc_ids":null} | 12 | 14 | 2 | 成功 | D0163:6, D0157:1, D0157:9, D0240:0, D0157:0, D0140:5, D0219:4, D0032:0, D0158:11, D0008:0, D0140:3, D0218:3 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"Recorded by Fireflies","search_mode":"keyword"} | 12 | 33 | 4 | 成功 | D0157:0, D0157:1, D0267:0, D0002:1, D0098:0, D0158:11, D0081:0, D0071:4, D0005:0, D0061:5, D0080:0, D0070:4 |
| 4 | 2 | search_chunks {"doc_ids":null,"query":"Fireflies.ai transcript sales call","search_mode":"keyword"} | 12 | 14 | 2 | 成功 | D0158:11, D0157:1, D0267:0, D0135:4, D0007:4, D0225:5, D0137:0, D0158:0, D0157:0, D0163:6, D0032:1, D0032:2 |
| 5 | 3 | search_chunks {"doc_ids":null,"query":"Fireflies","search_mode":"keyword"} | 5 | 0 | 0 | 成功 | D0267:0, D0158:11, D0158:0, D0157:1, D0157:0 |
| 6 | 3 | search_chunks {"doc_ids":null,"query":"\"Recorded by: Fireflies\" transcript","search_mode":"keyword"} | 12 | 9 | 2 | 成功 | D0157:1, D0158:11, D0157:0, D0007:4, D0267:0, D0158:0, D0032:1, D0163:6, D0032:0, D0032:2, D0002:1, D0098:0 |
| 7 | 4 | search_chunks {"doc_ids":null,"query":"\"Auto-summary (Fireflies)\"","search_mode":"keyword"} | 12 | 3 | 0 | 成功 | D0267:0, D0158:0, D0157:1, D0158:11, D0157:0, D0070:1, D0163:0, D0260:0, D0092:4, D0061:4, D0034:0, D0191:2 |
| 8 | 4 | search_chunks {"doc_ids":null,"query":"\"Fireflies.ai\"","search_mode":"keyword"} | 12 | 4 | 0 | 成功 | D0267:0, D0157:1, D0157:0, D0158:11, D0139:0, D0135:4, D0203:3, D0070:6, D0198:0, D0203:0, D0225:5, D0138:0 |
| 9 | 5 | search_chunks {"doc_ids":null,"query":"\"Recorded by\"","search_mode":"keyword"} | 12 | 10 | 1 | 成功 | D0002:1, D0098:0, D0081:0, D0071:4, D0157:0, D0005:0, D0061:5, D0080:0, D0070:4, D0081:6, D0013:2, D0276:0 |
| 10 | 5 | search_chunks {"doc_ids":null,"query":"Meeting header Duration Attendees Transcript sales call","search_mode":"keyword"} | 12 | 10 | 1 | 成功 | D0158:0, D0155:0, D0157:1, D0163:0, D0156:0, D0159:0, D0157:0, D0052:6, D0007:4, D0164:0, D0163:6, D0215:0 |
| 11 | 6 | search_chunks {"doc_ids":["D0160","D0162","D0163","D0164","D0165","D0159","D0161","D0156"],"query":"Fireflies","search_mode":"keyword"} | 0 | 0 | 0 | 成功 | — |
| 12 | 6 | search_chunks {"doc_ids":["D0160","D0162","D0163","D0164","D0165","D0159","D0161","D0156"],"query":"Recorded by Fireflies auto-summary","search_mode":"keyword"} | 12 | 0 | 0 | 成功 | D0163:0, D0163:2, D0159:0, D0163:3, D0159:1, D0165:1, D0159:4, D0161:0, D0162:0, D0165:0, D0159:3, D0163:4 |
| 13 | 7 | search_chunks {"doc_ids":null,"query":"Auto-summary","search_mode":"keyword"} | 12 | 1 | 0 | 成功 | D0070:1, D0163:0, D0260:0, D0092:4, D0061:4, D0034:0, D0191:2, D0001:1, D0061:5, D0260:3, D0224:1, D0061:0 |
| 14 | 7 | search_chunks {"doc_ids":null,"query":"Transcript","search_mode":"keyword"} | 12 | 9 | 1 | 成功 | D0007:4, D0163:6, D0032:1, D0032:0, D0032:2, D0158:11, D0157:9, D0155:0, D0007:2, D0159:0, D0158:0, D0157:1 |
| 15 | 8 | read_chunks {"doc_id":"D0158","ordinals":[0,1,2,3,4,5,6,7,8,9,10]} | 0 | 0 | 0 | Invalid number of chunk ordinals | — |
| 16 | 8 | read_chunks {"doc_id":"D0157","ordinals":[2,3,4,5,6,7,8]} | 7 | 0 | 0 | 成功 | D0157:2, D0157:3, D0157:4, D0157:5, D0157:6, D0157:7, D0157:8 |
| 17 | 9 | search_chunks {"doc_ids":["D0158"],"query":"residency region country","search_mode":"keyword"} | 1 | 0 | 0 | 成功 | D0158:10 |
| 18 | 9 | read_chunks {"doc_id":"D0158","ordinals":[1]} | 1 | 0 | 0 | 成功 | D0158:1 |

judge reasoning：

> The generated answer claims only 1 transcript, directly contradicting the gold answer of 8 transcripts.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> 8 transcripts mention a customer requirement for data residency (e.g., EU-only, UK-only, Germany-only, US-only/us‑east‑1, or strict in-country processing).

**naive 最终答案**

> Based on my searches, the transcripts explicitly recorded by Fireflies.ai are D0157 (Northpeak Analytics) and D0158 (MedData Systems). Both involve customer calls about data residency:
> 
> 1. **D0157 (Northpeak Analytics)** – Ravi Deshpande states: "Data residency: we have workloads that must stay US. Sometimes specifically us-east-1." – This is a customer requirement for keeping data in a specific region.
> 2. **D0158 (MedData Systems)** – While this call focuses on on-prem backup/restore, it involves air-gap constraints and data staying in their boundary, though not explicitly a "data residency requirement" in the strict sense (keys stay in their boundary; backups on-prem). It doesn't clearly state a customer requirement for data to remain in a specific country/region.
> 
> The answer depends on whether we count only explicit Fireflies recordings. Among the transcripts I found, **D0157 (Northpeak Analytics)** is the Fireflies-recorded sales call where a customer explicitly states a data residency requirement (workloads must stay US / us-east-1). D0158 (MedData) is also Fireflies-recorded, but its requirement is about on-prem hosting/air-gap and keys staying in their boundary rather than a stated region/country residency requirement.
> 
> However, I should be careful. Let me verify whether other transcripts (D0160-D0165, D0159, etc.) are also Fireflies transcripts, since they discuss data residency too, but they don't carry the "Recorded by: Fireflies.ai" header. The question specifically asks about "Fireflies sales-call transcripts."
> 
> Based on the evidence:
> - **D0157** is explicitly recorded by Fireflies.ai and contains a customer data residency requirement (must stay US, specifically us-east-1).
> - **D0158** is a Fireflies transcript (auto-summary says "Auto-summary (Fireflies)") but its content is about backup/restore and retention, not a data residency requirement per se (keys must stay in their boundary; on-prem hosting). It's not really a "data residency" requirement for a specific region/country.
> 
> So the answer: **1 transcript** (D0157 – Northpeak Analytics) mentions a customer requirement for data residency.
> 
> Wait, but let me double-check whether D0158 mentions anything about data residency. Reading D0158: "we don't want any vendor-managed keys. Keys have to stay in our boundary." "on-prem in two data centers" "air-gap constraints" "retention-wise audit logs seven years." This is about backup/retention, not data residency per se. It doesn't state a requirement to keep data in a specific country/region.
> 
> So the answer is 1 (D0157).
> 
> Let me answer briefly.</think>**1** transcript.
> 
> The Fireflies.ai-recorded sales call **Northpeak Analytics – Procurement via AWS Marketplace** (D0157) includes a customer requirement for data residency: *"Data residency: we have workloads that must stay US. Sometimes specifically us-east-1."*
> 
> The other Fireflies-recorded call (MedData Systems, D0158) concerns on-prem backup/restore and key/retention controls, not a stated requirement to keep data in a specific country/region.

**community 最终答案**

> 1 — only D0157 (Northpeak Analytics procurement call, recorded by Fireflies.ai), where the customer states a requirement that workloads must stay in the US / us-east-1.

</details>

## 8. 全部 80 题总表

| QA ID | score N→C | Δscore | rounds N→C | Δrounds | 工具N→C | 错误N→C | QA token N→C | 诊断 |
|---|---|---|---|---|---|---|---|---|
| enterprise_rag_bench:qst_0341 | 3→3 | +0 | 2→2 | +0 | 2→2 | 0→0 | 20,682→34,257 | 两项不变 |
| enterprise_rag_bench:qst_0342 | 3→4 | +1 | 2→3 | +1 | 2→3 | 0→0 | 20,974→50,324 | [enterprise_rag_bench:qst_0342](#case-enterprise_rag_bench-qst_0342) |
| enterprise_rag_bench:qst_0343 | 4→3 | -1 | 2→2 | +0 | 2→2 | 0→0 | 21,034→28,144 | [enterprise_rag_bench:qst_0343](#case-enterprise_rag_bench-qst_0343) |
| enterprise_rag_bench:qst_0344 | 2→4 | +2 | 3→3 | +0 | 3→4 | 0→0 | 39,660→59,262 | [enterprise_rag_bench:qst_0344](#case-enterprise_rag_bench-qst_0344) |
| enterprise_rag_bench:qst_0345 | 2→3 | +1 | 2→3 | +1 | 2→4 | 0→1 | 21,910→64,841 | [enterprise_rag_bench:qst_0345](#case-enterprise_rag_bench-qst_0345) |
| enterprise_rag_bench:qst_0346 | 2→2 | +0 | 4→4 | +0 | 5→6 | 1→2 | 64,641→91,967 | 两项不变 |
| enterprise_rag_bench:qst_0347 | 4→3 | -1 | 2→2 | +0 | 2→2 | 0→0 | 20,434→24,175 | [enterprise_rag_bench:qst_0347](#case-enterprise_rag_bench-qst_0347) |
| enterprise_rag_bench:qst_0348 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 20,501→24,255 | 两项不变 |
| enterprise_rag_bench:qst_0349 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 18,897→25,685 | 两项不变 |
| enterprise_rag_bench:qst_0350 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 22,093→30,265 | 两项不变 |
| enterprise_rag_bench:qst_0351 | 4→3 | -1 | 2→2 | +0 | 2→1 | 0→0 | 19,445→20,265 | [enterprise_rag_bench:qst_0351](#case-enterprise_rag_bench-qst_0351) |
| enterprise_rag_bench:qst_0352 | 2→4 | +2 | 2→2 | +0 | 2→2 | 0→0 | 20,347→28,996 | [enterprise_rag_bench:qst_0352](#case-enterprise_rag_bench-qst_0352) |
| enterprise_rag_bench:qst_0353 | 2→3 | +1 | 2→2 | +0 | 2→2 | 0→0 | 21,341→39,184 | [enterprise_rag_bench:qst_0353](#case-enterprise_rag_bench-qst_0353) |
| enterprise_rag_bench:qst_0354 | 3→3 | +0 | 2→2 | +0 | 2→2 | 0→0 | 23,054→28,094 | 两项不变 |
| enterprise_rag_bench:qst_0355 | 3→3 | +0 | 2→2 | +0 | 2→2 | 0→0 | 18,716→25,087 | 两项不变 |
| enterprise_rag_bench:qst_0356 | 4→4 | +0 | 3→5 | +2 | 4→5 | 0→0 | 48,407→133,313 | [enterprise_rag_bench:qst_0356](#case-enterprise_rag_bench-qst_0356) |
| enterprise_rag_bench:qst_0357 | 3→3 | +0 | 2→2 | +0 | 2→2 | 0→0 | 20,591→28,915 | 两项不变 |
| enterprise_rag_bench:qst_0358 | 3→3 | +0 | 2→2 | +0 | 2→2 | 0→0 | 20,695→28,207 | 两项不变 |
| enterprise_rag_bench:qst_0359 | 3→2 | -1 | 4→3 | -1 | 7→5 | 1→0 | 82,759→60,269 | [enterprise_rag_bench:qst_0359](#case-enterprise_rag_bench-qst_0359) |
| enterprise_rag_bench:qst_0360 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 18,973→30,965 | 两项不变 |
| enterprise_rag_bench:qst_0361 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 20,872→32,745 | 两项不变 |
| enterprise_rag_bench:qst_0362 | 3→2 | -1 | 3→2 | -1 | 4→2 | 0→0 | 55,674→26,761 | [enterprise_rag_bench:qst_0362](#case-enterprise_rag_bench-qst_0362) |
| enterprise_rag_bench:qst_0363 | 4→3 | -1 | 2→2 | +0 | 2→2 | 0→0 | 22,163→29,125 | [enterprise_rag_bench:qst_0363](#case-enterprise_rag_bench-qst_0363) |
| enterprise_rag_bench:qst_0364 | 2→2 | +0 | 2→2 | +0 | 2→2 | 0→0 | 21,671→24,700 | 两项不变 |
| enterprise_rag_bench:qst_0365 | 2→2 | +0 | 4→3 | -1 | 7→5 | 0→0 | 96,720→64,630 | [enterprise_rag_bench:qst_0365](#case-enterprise_rag_bench-qst_0365) |
| enterprise_rag_bench:qst_0366 | 2→3 | +1 | 2→2 | +0 | 2→2 | 0→0 | 22,418→28,938 | [enterprise_rag_bench:qst_0366](#case-enterprise_rag_bench-qst_0366) |
| enterprise_rag_bench:qst_0367 | 2→3 | +1 | 3→3 | +0 | 4→4 | 0→0 | 57,207→58,074 | [enterprise_rag_bench:qst_0367](#case-enterprise_rag_bench-qst_0367) |
| enterprise_rag_bench:qst_0368 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 21,128→26,972 | 两项不变 |
| enterprise_rag_bench:qst_0369 | 2→3 | +1 | 2→2 | +0 | 2→2 | 0→0 | 21,631→25,745 | [enterprise_rag_bench:qst_0369](#case-enterprise_rag_bench-qst_0369) |
| enterprise_rag_bench:qst_0370 | 3→3 | +0 | 2→2 | +0 | 2→2 | 0→0 | 19,625→30,041 | 两项不变 |
| enterprise_rag_bench:qst_0371 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 21,668→28,089 | 两项不变 |
| enterprise_rag_bench:qst_0372 | 2→2 | +0 | 2→2 | +0 | 2→2 | 0→0 | 20,780→24,048 | 两项不变 |
| enterprise_rag_bench:qst_0373 | 4→3 | -1 | 2→2 | +0 | 1→2 | 0→0 | 11,608→24,474 | [enterprise_rag_bench:qst_0373](#case-enterprise_rag_bench-qst_0373) |
| enterprise_rag_bench:qst_0374 | 3→3 | +0 | 2→2 | +0 | 2→2 | 0→0 | 19,901→28,889 | 两项不变 |
| enterprise_rag_bench:qst_0375 | 3→4 | +1 | 2→2 | +0 | 2→2 | 0→0 | 23,377→33,008 | [enterprise_rag_bench:qst_0375](#case-enterprise_rag_bench-qst_0375) |
| enterprise_rag_bench:qst_0376 | 2→2 | +0 | 2→2 | +0 | 2→2 | 0→0 | 20,026→28,743 | 两项不变 |
| enterprise_rag_bench:qst_0377 | 2→2 | +0 | 2→2 | +0 | 2→2 | 0→0 | 20,991→24,566 | 两项不变 |
| enterprise_rag_bench:qst_0378 | 3→3 | +0 | 2→2 | +0 | 2→2 | 0→0 | 19,889→24,703 | 两项不变 |
| enterprise_rag_bench:qst_0379 | 3→2 | -1 | 2→2 | +0 | 2→2 | 0→0 | 21,941→26,562 | [enterprise_rag_bench:qst_0379](#case-enterprise_rag_bench-qst_0379) |
| enterprise_rag_bench:qst_0380 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 20,524→30,427 | 两项不变 |
| enterprise_rag_bench:qst_0411 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 19,873→22,901 | 两项不变 |
| enterprise_rag_bench:qst_0412 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 19,115→30,246 | 两项不变 |
| enterprise_rag_bench:qst_0413 | 4→4 | +0 | 2→2 | +0 | 1→1 | 0→0 | 10,938→19,939 | 两项不变 |
| enterprise_rag_bench:qst_0414 | 4→4 | +0 | 2→2 | +0 | 1→2 | 0→0 | 11,055→24,777 | 两项不变 |
| enterprise_rag_bench:qst_0415 | 4→4 | +0 | 2→2 | +0 | 1→1 | 0→0 | 12,262→17,321 | 两项不变 |
| enterprise_rag_bench:qst_0416 | 4→4 | +0 | 2→2 | +0 | 1→2 | 0→0 | 11,499→29,253 | 两项不变 |
| enterprise_rag_bench:qst_0417 | 4→4 | +0 | 2→2 | +0 | 1→1 | 0→0 | 12,242→16,254 | 两项不变 |
| enterprise_rag_bench:qst_0418 | 4→4 | +0 | 2→2 | +0 | 2→1 | 0→0 | 21,649→19,678 | 两项不变 |
| enterprise_rag_bench:qst_0419 | 4→4 | +0 | 2→2 | +0 | 1→1 | 0→0 | 11,634→20,070 | 两项不变 |
| enterprise_rag_bench:qst_0420 | 4→4 | +0 | 2→2 | +0 | 1→2 | 0→0 | 11,124→30,527 | 两项不变 |
| enterprise_rag_bench:qst_0421 | 4→4 | +0 | 2→2 | +0 | 2→1 | 0→0 | 19,239→17,362 | 两项不变 |
| enterprise_rag_bench:qst_0422 | 4→2 | -2 | 2→2 | +0 | 1→2 | 0→0 | 11,858→25,699 | [enterprise_rag_bench:qst_0422](#case-enterprise_rag_bench-qst_0422) |
| enterprise_rag_bench:qst_0423 | 4→4 | +0 | 2→2 | +0 | 1→1 | 0→0 | 12,412→19,941 | 两项不变 |
| enterprise_rag_bench:qst_0424 | 4→4 | +0 | 2→2 | +0 | 2→1 | 0→0 | 20,044→19,293 | 两项不变 |
| enterprise_rag_bench:qst_0425 | 4→4 | +0 | 2→2 | +0 | 2→1 | 0→0 | 21,240→17,931 | 两项不变 |
| enterprise_rag_bench:qst_0426 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 20,826→32,274 | 两项不变 |
| enterprise_rag_bench:qst_0427 | 3→4 | +1 | 2→2 | +0 | 2→1 | 0→0 | 20,715→20,327 | [enterprise_rag_bench:qst_0427](#case-enterprise_rag_bench-qst_0427) |
| enterprise_rag_bench:qst_0428 | 4→4 | +0 | 2→2 | +0 | 2→1 | 0→0 | 19,974→18,800 | 两项不变 |
| enterprise_rag_bench:qst_0429 | 4→4 | +0 | 2→2 | +0 | 1→1 | 0→0 | 11,546→17,890 | 两项不变 |
| enterprise_rag_bench:qst_0430 | 4→4 | +0 | 2→2 | +0 | 1→2 | 0→0 | 11,527→33,136 | 两项不变 |
| enterprise_rag_bench:qst_0431 | 4→4 | +0 | 2→2 | +0 | 1→1 | 0→0 | 12,415→16,396 | 两项不变 |
| enterprise_rag_bench:qst_0432 | 0→0 | +0 | 13→11 | -2 | 22→19 | 2→1 | 791,619→742,480 | [enterprise_rag_bench:qst_0432](#case-enterprise_rag_bench-qst_0432) |
| enterprise_rag_bench:qst_0433 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 20,786→24,879 | 两项不变 |
| enterprise_rag_bench:qst_0434 | 4→4 | +0 | 3→4 | +1 | 3→6 | 0→1 | 29,993→85,677 | [enterprise_rag_bench:qst_0434](#case-enterprise_rag_bench-qst_0434) |
| enterprise_rag_bench:qst_0435 | 4→4 | +0 | 3→2 | -1 | 3→1 | 0→0 | 31,689→15,159 | [enterprise_rag_bench:qst_0435](#case-enterprise_rag_bench-qst_0435) |
| enterprise_rag_bench:qst_0436 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 17,081→31,156 | 两项不变 |
| enterprise_rag_bench:qst_0437 | 2→3 | +1 | 6→5 | -1 | 9→17 | 0→5 | 217,292→146,338 | [enterprise_rag_bench:qst_0437](#case-enterprise_rag_bench-qst_0437) |
| enterprise_rag_bench:qst_0438 | 4→4 | +0 | 2→2 | +0 | 1→1 | 0→0 | 9,574→14,267 | 两项不变 |
| enterprise_rag_bench:qst_0439 | 4→4 | +0 | 6→7 | +1 | 10→21 | 0→4 | 265,639→404,194 | [enterprise_rag_bench:qst_0439](#case-enterprise_rag_bench-qst_0439) |
| enterprise_rag_bench:qst_0440 | 4→4 | +0 | 4→4 | +0 | 7→10 | 2→2 | 67,462→79,592 | 两项不变 |
| enterprise_rag_bench:qst_0441 | 2→2 | +0 | 2→2 | +0 | 2→2 | 0→0 | 21,251→28,082 | 两项不变 |
| enterprise_rag_bench:qst_0442 | 3→3 | +0 | 2→2 | +0 | 2→2 | 0→0 | 21,265→28,834 | 两项不变 |
| enterprise_rag_bench:qst_0443 | 4→4 | +0 | 4→3 | -1 | 5→4 | 2→1 | 57,316→55,242 | [enterprise_rag_bench:qst_0443](#case-enterprise_rag_bench-qst_0443) |
| enterprise_rag_bench:qst_0444 | 3→3 | +0 | 3→3 | +0 | 5→4 | 0→2 | 42,944→56,232 | 两项不变 |
| enterprise_rag_bench:qst_0445 | 2→2 | +0 | 3→5 | +2 | 4→10 | 1→5 | 43,805→135,810 | [enterprise_rag_bench:qst_0445](#case-enterprise_rag_bench-qst_0445) |
| enterprise_rag_bench:qst_0446 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 20,011→25,970 | 两项不变 |
| enterprise_rag_bench:qst_0447 | 4→3 | -1 | 2→2 | +0 | 2→2 | 0→0 | 21,949→27,007 | [enterprise_rag_bench:qst_0447](#case-enterprise_rag_bench-qst_0447) |
| enterprise_rag_bench:qst_0448 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 18,177→22,887 | 两项不变 |
| enterprise_rag_bench:qst_0449 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 20,547→30,671 | 两项不变 |
| enterprise_rag_bench:qst_0450 | 0→0 | +0 | 9→10 | +1 | 16→18 | 0→1 | 520,870→808,051 | [enterprise_rag_bench:qst_0450](#case-enterprise_rag_bench-qst_0450) |

## 9. 核验与限制

所有 trace 副本 SHA-256 与服务器采集记录一致，所有模型轮次与 results.jsonl 的 rounds 一致。总体分数、token、耗时和题数已与原汇总交叉核对。没有新增 API 请求、重新评分、修改 gold 或调整实验配置。五组新实验共 532 对 QA；本报告只覆盖标题所示组。完整派生数据与提取脚本见 [summary.json](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/summary.json)、[analyze.py](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/analyze.py)。

本报告没有随机化重复试验或固定检索轨迹的消融，无法识别“社区算法单独造成的准确率变化”。特别是 query 已变、后续读取不同、judge 本身有尺度差异时，只能报告证据支持到的机制层级。
