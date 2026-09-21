# MDAQA：naive 与 community 的逐题 trace 对比报告

分析日期：2026-09-21。离线分析已完成实验；未重新生成答案、检索、评分或修改原始实验结果。Δ 均为 community−naive。

## 1. 主要结论

平均分略降，净 −2 分（−0.5 个百分点），但逐题有 +4 和 −4 的巨大摆动，不能从均值判断没有变化。最明显的 −4 存在强评分一致性疑点；真实失分则常见“第二篇论文的证据已出现却没用”或“没有锁定对照对象”。更多 overview 没有稳定改善两篇论文的关系比较，反而增加约 20.1% QA token。

共 100 题：评分上升 **15**、下降 **16**；iteration 上升 **23**、下降 **20**。两项任一变化的 **60** 题全部进入第 7 节，并附完整 gold、答案、judge 和工具时序；第 8 节覆盖全部题目。第 5 节对重点案例逐项核验机制，其余案例只陈述可验证的执行变化与原判分依据，不虚构模型内部思考，也不把未受控的对照当作因果证明。

## 2. 数据来源与比较口径

- 原实验目录（214）：`/home/ZhangYunhao/community_wiki/data/runs/mdaqa_first_100_naive_community`。
- 本地核验副本：[results.jsonl](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/results.jsonl)、[分类汇总](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/summary_by_category.json)、[execution.json](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/execution.json)、[judge_execution.json](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/judge_execution.json)。
- 当前组 100 对问答及 judge 全部成功；按 QA ID 对齐并核对 question/gold 一致。两种模式共用同一实验数据库，文档与 chunk 索引相同；同题初始 system/user 消息全部一致。三组 PaperScope 复用同一批 93 篇 PDF，不能视为完全独立语料实验。
- 模型 `deepseek-v4-flash`，embedding `doubao-embedding-vision`，QA/judge 并发 5。实际模式以结果行与 trace 为准，不能仅凭配置默认 retrieval.mode 判断。
- 原始 score 是一次 LLM judge 的 0–4 分，normalized accuracy=均分/4，并非二元正确率。本文不改分，也不生成主观“校正准确率”。
- iteration/rounds 是模型调用次数，包含最终回答轮；一轮可并发多个工具，API 重试不直接增加 rounds。工具错误是 tool 消息中的 error，不等于整题失败。
- QA 时间为逐题端到端执行时长，token 包括 query embedding 与各轮 LLM，不含入库和 judge。工具结果字符数是序列化 JSON 的长度；overview/chunk 均每题内去重后再求和，不等同于相关证据数。
- 首轮整组工具请求相同 4/100；首个工具的有序 chunk ID 相同 15/100；两项同时相同 2/100。后续检索还会分叉。首轮不同不能归因于尚未注入的社区信息，temperature=0 不等于服务完全确定。
- 文档数 143，社区总数 34（叶社区 22）。实际共享入库 1748.57 秒、6,874,449 token；该成本只执行一次，不按 QA 类别或模式重复累计。

## 3. 整体结果与变化矩阵

| 指标 | naive | community | 变化 |
|---|---|---|---|
| judge总分 | 318 | 316 | -2 |
| judge均分/4 | 3.1800 | 3.1600 | -0.0200 |
| 归一化accuracy（%） | 79.500 | 79.000 | -0.500 |
| 平均QA秒 | 20.14 | 20.15 | +0.01 |
| 平均QA token | 61,952.76 | 74,429.98 | +12,477.22 |
| 平均rounds | 3.0600 | 3.0700 | +0.0100 |
| 总rounds | 306 | 307 | +1 |
| 工具调用 | 368 | 376 | +8 |
| search_chunks | 284 | 271 | -13 |
| read_chunks | 84 | 105 | +21 |
| 工具错误 | 12 | 18 | +6 |
| 整轮全错误 | 3 | 8 | +5 |
| 逐题去重overview数之和 | 596 | 3,004 | +2,408 |
| 逐题去重chunk数之和 | 2,539 | 2,532 | -7 |
| 工具返回字符数 | 8,808,840 | 11,697,454 | +2,888,614 |
| 重复chunk返回次数 | 1,147 | 1,069 | -78 |

QA token 变化 **+20.14%**，平均 QA 时间变化 **+0.07%**。时间受请求长度、排队与服务状态影响，两个模式先后运行，不能只从时间差反推算法快慢。

| score变化 / rounds变化 | rounds减少 | rounds相同 | rounds增加 | 合计 |
|---|---|---|---|---|
| score上升 | 3 | 7 | 5 | 15 |
| score不变 | 13 | 40 | 16 | 69 |
| score下降 | 4 | 10 | 2 | 16 |
| 合计 | 20 | 57 | 23 | 100 |

搜索类型（按实际调用参数；default 表示使用配置默认）：

| 模式 | hybrid | vector | keyword | default |
|---|---|---|---|---|
| naive | 220 | 45 | 19 | 0 |
| community | 205 | 48 | 18 | 0 |

工具错误分类：

| 错误原文 | naive | community |
|---|---|---|
| Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | 12 | 13 |
| Invalid number of chunk ordinals | 0 | 1 |
| Expecting property name enclosed in double quotes: line 1 column 35 (char 34) | 0 | 2 |
| 2 validation errors for ReadArguments<br>doc_id<br>  Field required [type=missing, input_value={'doc_ids': ['D0011'], 'ordinals': [1, 2]}, input_type=dict]<br>    For further information visit https://errors.pydantic.dev/2.13/v/missing<br>doc_ids<br>  Extra inputs are not permitted [type=extra_forbidden, input_value=['D0011'], input_type=list]<br>    For further information visit https://errors.pydantic.dev/2.13/v/extra_forbidden | 0 | 1 |
| 2 validation errors for ReadArguments<br>doc_id<br>  Field required [type=missing, input_value={'doc_ids': ['D0059'], 'ordinals': [5, 6, 7]}, input_type=dict]<br>    For further information visit https://errors.pydantic.dev/2.13/v/missing<br>doc_ids<br>  Extra inputs are not permitted [type=extra_forbidden, input_value=['D0059'], input_type=list]<br>    For further information visit https://errors.pydantic.dev/2.13/v/extra_forbidden | 0 | 1 |

community 每题平均收到 30.04 份文档 overview；其中 0 题覆盖全部 143 篇文档。

## 4. 四类变化案例导航

**评分上升（15题）**：[mdaqa:0](#case-mdaqa-0)（+1）、[mdaqa:10](#case-mdaqa-10)（+1）、[mdaqa:31](#case-mdaqa-31)（+1）、[mdaqa:35](#case-mdaqa-35)（+1）、[mdaqa:37](#case-mdaqa-37)（+1）、[mdaqa:38](#case-mdaqa-38)（+2）、[mdaqa:41](#case-mdaqa-41)（+1）、[mdaqa:42](#case-mdaqa-42)（+4）、[mdaqa:67](#case-mdaqa-67)（+1）、[mdaqa:73](#case-mdaqa-73)（+1）、[mdaqa:79](#case-mdaqa-79)（+1）、[mdaqa:83](#case-mdaqa-83)（+1）、[mdaqa:84](#case-mdaqa-84)（+4）、[mdaqa:88](#case-mdaqa-88)（+1）、[mdaqa:89](#case-mdaqa-89)（+1）。

**评分下降（16题）**：[mdaqa:2](#case-mdaqa-2)（-1）、[mdaqa:11](#case-mdaqa-11)（-2）、[mdaqa:13](#case-mdaqa-13)（-1）、[mdaqa:16](#case-mdaqa-16)（-2）、[mdaqa:17](#case-mdaqa-17)（-1）、[mdaqa:20](#case-mdaqa-20)（-2）、[mdaqa:23](#case-mdaqa-23)（-1）、[mdaqa:33](#case-mdaqa-33)（-4）、[mdaqa:34](#case-mdaqa-34)（-2）、[mdaqa:36](#case-mdaqa-36)（-1）、[mdaqa:44](#case-mdaqa-44)（-1）、[mdaqa:45](#case-mdaqa-45)（-1）、[mdaqa:60](#case-mdaqa-60)（-1）、[mdaqa:94](#case-mdaqa-94)（-1）、[mdaqa:98](#case-mdaqa-98)（-2）、[mdaqa:99](#case-mdaqa-99)（-1）。

**iteration上升（23题）**：[mdaqa:4](#case-mdaqa-4)（+1）、[mdaqa:7](#case-mdaqa-7)（+1）、[mdaqa:14](#case-mdaqa-14)（+1）、[mdaqa:33](#case-mdaqa-33)（+1）、[mdaqa:36](#case-mdaqa-36)（+3）、[mdaqa:37](#case-mdaqa-37)（+1）、[mdaqa:38](#case-mdaqa-38)（+3）、[mdaqa:41](#case-mdaqa-41)（+2）、[mdaqa:53](#case-mdaqa-53)（+1）、[mdaqa:54](#case-mdaqa-54)（+2）、[mdaqa:56](#case-mdaqa-56)（+1）、[mdaqa:64](#case-mdaqa-64)（+1）、[mdaqa:68](#case-mdaqa-68)（+1）、[mdaqa:69](#case-mdaqa-69)（+1）、[mdaqa:75](#case-mdaqa-75)（+1）、[mdaqa:78](#case-mdaqa-78)（+1）、[mdaqa:79](#case-mdaqa-79)（+1）、[mdaqa:81](#case-mdaqa-81)（+1）、[mdaqa:82](#case-mdaqa-82)（+1）、[mdaqa:85](#case-mdaqa-85)（+4）、[mdaqa:88](#case-mdaqa-88)（+2）、[mdaqa:92](#case-mdaqa-92)（+1）、[mdaqa:97](#case-mdaqa-97)（+2）。

**iteration下降（20题）**：[mdaqa:2](#case-mdaqa-2)（-4）、[mdaqa:8](#case-mdaqa-8)（-1）、[mdaqa:10](#case-mdaqa-10)（-1）、[mdaqa:13](#case-mdaqa-13)（-2）、[mdaqa:17](#case-mdaqa-17)（-1）、[mdaqa:19](#case-mdaqa-19)（-1）、[mdaqa:25](#case-mdaqa-25)（-1）、[mdaqa:27](#case-mdaqa-27)（-4）、[mdaqa:29](#case-mdaqa-29)（-1）、[mdaqa:31](#case-mdaqa-31)（-1）、[mdaqa:32](#case-mdaqa-32)（-1）、[mdaqa:40](#case-mdaqa-40)（-1）、[mdaqa:44](#case-mdaqa-44)（-1）、[mdaqa:57](#case-mdaqa-57)（-1）、[mdaqa:70](#case-mdaqa-70)（-2）、[mdaqa:72](#case-mdaqa-72)（-1）、[mdaqa:73](#case-mdaqa-73)（-2）、[mdaqa:76](#case-mdaqa-76)（-2）、[mdaqa:80](#case-mdaqa-80)（-4）、[mdaqa:95](#case-mdaqa-95)（-1）。

## 5. 重点机制与可核验证据

### mdaqa:11：同样未展开跨视角对齐，2 分落差需复核

评分 4→2；rounds 2→2。

两份答案都围绕 holistic structure、discriminative regions、local confusion 和 representation learning，均未明确展开 gold 的 semantic alignment across viewpoints/geometric cues。naive judge 仅按核心区域定位给 4，community judge 按缺少其余两项给 2。检索确有不同 chunk/overview，但主要判分理由对共同缺项不对称，不能据此证明新增社区使答案显著变差。

完整对照：[mdaqa:11](#case-mdaqa-11)。

### mdaqa:16：SUS-VAE 已被召回，最终答案却只围绕第一篇

评分 4→2；rounds 2→2。

community 的 overview 从 4→47，但最终只讲 D0047 的 I2I、SA-I2I，漏掉 gold 的 SUS-constrained VAE，4→2 分。同一轮工具中 D0103:0/1 原文和 D0103 overview 已明确含 SUS-constrained VAE，两种模式都拿到了。失分是多论文对照时选择性采用证据，不是图或检索没有覆盖第二篇。文本层还能看到双栏拼接与连字问题，但 overview 已清晰概括 SUS，因此解析问题不能独立解释这次遗漏。

完整对照：[mdaqa:16](#case-mdaqa-16)。

<details>
<summary>展开对应字段的原文节选</summary>

**naive，第 1 轮第 1 次工具，overviews，doc_id=D0103：**

> The paper proposes SUS-constrained VAE for multi-emotion TTS: emotion embedding means are constrained toward the unit-sphere surface and standard deviations set to a constant, improving cluster cohesion over KL-regularized VAE. The emotion embedding is also added as a query, together with textual queries, in multi-query attention th

**naive，第 1 轮第 1 次工具，chunks，doc_id=D0103，ordinal=0：**

> <!-- Page 1 -->
> 
> # 2  Related Work
> IMPROVINGEMOTIONALSPEECHSYNTHESISBYUSINGSUS-CONSTRAINEDVAEAND
> TEXTENCODERAGGREGATION
> FengyuYang,JianLuan,YujunWang
> XiaomiCorporation,Beijing,China
> ABSTRACT averageembeddingvectoroftargetemotiontypemaybeem-
> ployed [5], while [6] even tries to control the emotion in-
> Learning emotion embedding from reference audio is a
> tensity and inter-emotion transition

**community，第 1 轮第 1 次工具，overviews，doc_id=D0103：**

> The paper proposes SUS-constrained VAE for multi-emotion TTS: emotion embedding means are constrained toward the unit-sphere surface and standard deviations set to a constant, improving cluster cohesion over KL-regularized VAE. The emotion embedding is also added as a query, together with textual queries, in multi-query attention th

**community，第 1 轮第 1 次工具，chunks，doc_id=D0103，ordinal=0：**

> <!-- Page 1 -->
> 
> # 2  Related Work
> IMPROVINGEMOTIONALSPEECHSYNTHESISBYUSINGSUS-CONSTRAINEDVAEAND
> TEXTENCODERAGGREGATION
> FengyuYang,JianLuan,YujunWang
> XiaomiCorporation,Beijing,China
> ABSTRACT averageembeddingvectoroftargetemotiontypemaybeem-
> ployed [5], while [6] even tries to control the emotion in-
> Learning emotion embedding from reference audio is a
> tensity and inter-emotion transition

</details>

### mdaqa:20：共同给出 FRAGE，却对 cluster 缺项不同判分

评分 4→2；rounds 2→2。

两边都说明 rare/popular embedding 分区，并给出 FRAGE 对抗训练，均未明确展开 gold 的 cluster-based 替代方案。naive 给 4、community 给 2；后者还多给了 degeneration/CosReg 相关说明。judge 对同一缺项重要性不一致，因此 −2 不应直接解释为社区损害事实正确性。初始首个 query 相同，但 community 首轮多发了一条搜索，仍不属于完全受控的社区消融。

完整对照：[mdaqa:20](#case-mdaqa-20)。

### mdaqa:27：减少接口恢复和旁支搜索，缺项仍在

评分 2→2；rounds 8→4。

naive 第 2 轮两次读取均为非法 JSON，随后恢复读取并继续搜索 D-NeRF 等旁支，8 轮、249,986 token；community 4 轮、88,918 token，无错误。两边同为 2 分，均漏 Meta-Sim。可以确认成本降低来自少一次全失败轮及更少旁支探索，但既没有补齐比较对象，也不能把全部四轮差都归于工具错误。

完整对照：[mdaqa:27](#case-mdaqa-27)。

### mdaqa:33：最大降分主要暴露比较口径与 judge 一致性

评分 4→0；rounds 2→3。

两份答案开头都说 COMRADE 在有/无 Byzantine 时均一轮，后面也都明确 GIANT/DINGO 两轮。naive 判 4，community 判 0；判 0 的 reasoning 只抓住“no difference”而忽略末句对 GIANT/DINGO 的对照。两份回答的核心结构相近，问题本身又可解读为“同一方法在故障/正常状态”或“不同方法之间”，不能把四分落差解释为社区召回失效。community 还多做一轮定向搜索和原文读取，token 19,135→54,834，却未澄清比较对象。先复核题意及盲化评分，再评价这种最大分差。

完整对照：[mdaqa:33](#case-mdaqa-33)。

### mdaqa:36：扩展到大半语料仍未消解模糊对照对象

评分 1→0；rounds 5→8。

naive 5 轮、community 8 轮；community 已给出 124/143 篇文档 overview，15 次工具且无错误，仍称无法从材料建立实时/非实时 plug-and-play 比较，1→0 分。trace 中反复改写通用 latency/efficiency/plug-and-play 查询，没有稳定定位 gold 的 residual adapters 与 O(L log L) 对照。这里不是单纯社区数量不够；应先解决实体/方法指代与无进展循环。仅增加召回规模会进一步增加上下文和成本。

完整对照：[mdaqa:36](#case-mdaqa-36)。

### mdaqa:38：原文精读有助补齐，但两轮消耗在非法 JSON

评分 2→4；rounds 2→5。

community 增加了 word-level correlation-minimization regularization 的比较，2→4 分、2→5 轮。不过第 2、3 轮共四次 read_chunks 参数把 ordinals 写成逗号串，缺少数组方括号，例如 {"doc_id":"D0042","ordinals":6,7,8}，两轮均全部失败；第 4 轮正确读取 D0042 和 D0010 后才回答。增益与成功精读相容，但多出的三轮中两轮是接口恢复，不能说需要三轮更深推理才能提高分数。

完整对照：[mdaqa:38](#case-mdaqa-38)。

### mdaqa:42：人工评估材料两边都有，四分差混合采用差异与尺度效应

评分 0→4；rounds 4→4。

community 明确补写 Quasimodo 的 crowd-rated meaningfulness/typicality/saliency，0→4 分，同为 4 轮。但 naive 首轮已返回 D0036:23 的 crowd judgement 原文与 D0036 overview 中的 Crowd studies，因此不是 community 独自发现人工评估。两边对负知识系统的自动过滤与人工质量评估仍可能混在一起；满分不能作为每项评测机制都完备的证明。这里真实可见的改善是最终答案采用了 Quasimodo 人工评估信息，分差大小还需 judge 复核。

完整对照：[mdaqa:42](#case-mdaqa-42)。

<details>
<summary>展开对应字段的原文节选</summary>

**naive，第 1 轮第 1 次工具，overviews，doc_id=D0036：**

> -negative matrix tri-factorization. The KB has ~2.3M assertions for 80k subjects (v4.3: 6.3M/148k). Crowd studies show higher recall and competitive quality versus ConceptNet, WebChild, TupleKB; QA answer-selection and Taboo word-guessing tasks demonstrate practical gains.

**naive，第 1 轮第 1 次工具，chunks，doc_id=D0036，ordinal=23：**

> ndeachKBweconsideredthetop-5-rankedtriplesas
> apool,anduniformlysampled100assertionsforwhichweobtain
> crowdjudgement.ForQuasimodo,astherankingsbytypicality𝜏
> andbysaliency𝜎 differ,thissamplingtreatedQuasimodo-𝜏 and
> Quasimodo-𝜎asdistinctCSKBs.Thissettingprovidesside-by-side
> comparisonoftriplesforthesamesubjects.
> Inhorizontalsampling,wesampledeachKBseparately;sothey
> coulddifferontheevaluatedsubjects.Weconsi

**community，第 1 轮第 1 次工具，overviews，doc_id=D0036：**

> -negative matrix tri-factorization. The KB has ~2.3M assertions for 80k subjects (v4.3: 6.3M/148k). Crowd studies show higher recall and competitive quality versus ConceptNet, WebChild, TupleKB; QA answer-selection and Taboo word-guessing tasks demonstrate practical gains.

**community，第 1 轮第 1 次工具，chunks，doc_id=D0036，ordinal=23：**

> ndeachKBweconsideredthetop-5-rankedtriplesas
> apool,anduniformlysampled100assertionsforwhichweobtain
> crowdjudgement.ForQuasimodo,astherankingsbytypicality𝜏
> andbysaliency𝜎 differ,thissamplingtreatedQuasimodo-𝜏 and
> Quasimodo-𝜎asdistinctCSKBs.Thissettingprovidesside-by-side
> comparisonoftriplesforthesamesubjects.
> Inhorizontalsampling,wesampledeachKBseparately;sothey
> coulddifferontheevaluatedsubjects.Weconsi

</details>

### mdaqa:84：同类证据被解释成相反结论

评分 0→4；rounds 2→2。

两份回答都描述 alignment posterior sampling、posterior regularization/importance sampling。naive 开头却写“does not increase complexity”，community 写“makes training more complex”，造成 0→4。两边首轮都召回 D0120:0/1 和相同核心 overview；community 有额外相关概览和略不同的第二路检索，但没有独立证据证明其中某一新增片段导致结论翻转。此例主要提醒区分“算法训练方案简洁”与“相对固定对齐新增计算复杂度”，不是缺少论文名称。

完整对照：[mdaqa:84](#case-mdaqa-84)。

<details>
<summary>展开对应字段的原文节选</summary>

**naive，第 1 轮第 1 次工具，overviews，doc_id=D0120：**

> h frozen ELMo and integrated into StructBART via MAP one-best alignments or sampling from alignment uncertainty with posterior regularization (PR) or importance sampling (IS). On gold-only AMR2.0/AMR3.0, PR reaches 84.3/83.1 Smatch without beam search, surpassing MAP/IS and matching prior SOTA, with larger gains on AMR3.0 suggesting better domain generalization. Alignment quality is 96.5 permissive F1, near 

**naive，第 1 轮第 1 次工具，chunks，doc_id=D0120，ordinal=0：**

> point-estimate of the alignment pipeline,
> to-sequencemodeltolearnlatentalignments(Wu
> neglecting the uncertainty due to the inherent
> etal.,2018;Dengetal.,2018;Shankaretal.,2018).
> ambiguity of alignment. In this work we ex-
> Whilestraightforward,thisneuralparameterization
> plore two avenues for overcoming these lim-
> makesitpossibletoeasilyincorporatepretrained itations. First, we propose a neural aligner
> forAMRt

**community，第 1 轮第 1 次工具，overviews，doc_id=D0120：**

> h frozen ELMo and integrated into StructBART via MAP one-best alignments or sampling from alignment uncertainty with posterior regularization (PR) or importance sampling (IS). On gold-only AMR2.0/AMR3.0, PR reaches 84.3/83.1 Smatch without beam search, surpassing MAP/IS and matching prior SOTA, with larger gains on AMR3.0 suggesting better domain generalization. Alignment quality is 96.5 permissive F1, near 

**community，第 1 轮第 1 次工具，chunks，doc_id=D0120，ordinal=0：**

> point-estimate of the alignment pipeline,
> to-sequencemodeltolearnlatentalignments(Wu
> neglecting the uncertainty due to the inherent
> etal.,2018;Dengetal.,2018;Shankaretal.,2018).
> ambiguity of alignment. In this work we ex-
> Whilestraightforward,thisneuralparameterization
> plore two avenues for overcoming these lim-
> makesitpossibletoeasilyincorporatepretrained itations. First, we propose a neural aligner
> forAMRt

</details>

### mdaqa:85：三个整轮被参数语法错误占用

评分 4→4；rounds 3→7。

评分均 4，轮次 3→7、token 36,497→172,366。community 第 2、3、4 轮的全部工具都因 ordinals 未写成 JSON 数组失败（第 4 轮并行两个失败调用），第 5 轮才成功读取。不是未知论文或检索召回率低，而是工具调用协议恢复慢。严格 schema 已发送也未阻止这类返回，应在 schema/提示/错误恢复层明确数组格式并验证服务端工具参数约束是否真正执行。

完整对照：[mdaqa:85](#case-mdaqa-85)。

### mdaqa:94：宽泛问题下，后续检索锁定了不同的比较对象

评分 2→1；rounds 4→4。

naive 后续读 D0084，最终讲 TCN 但漏 PLAtE；community 后续始终限定 D0122，最终把比较对象变成 PLAtE 内部的 RoBERTa/DOM-LM/MarkupLM，遗漏 TCN，2→1 分。两边开头都召回 D0122，社区扩展没有保证跨论文对齐到 gold 的 PLAtE-versus-TCN。问题没有直接命名“these approaches”的对象，宽泛问法与全库检索形成歧义。应先确认对照对象再定向读取；不能简单把更多文档概览当成多文档推理已经完成。

完整对照：[mdaqa:94](#case-mdaqa-94)。

### mdaqa:98：同一轮不等于同一检索工作量，关键对照项遗漏

评分 4→2；rounds 2→2。

两边均为 2 轮，但 naive 首轮发两条查询，第二条带回 D0076 关于 latent-factor independence 的原文，最终对比“建模相关性”与“假设独立”；community 首轮只发一条查询，虽通过扩展知道 D0076，却仅概述因果/非因果分离，漏掉独立性假设，4→2。这包含首轮规划和原文细节覆盖差异；不能把少一个查询归因为先看到社区后提前停止，因为同轮请求在看到结果前已计划完成。

完整对照：[mdaqa:98](#case-mdaqa-98)。

## 6. 改进优先级（建议，未修改系统）

1. 对 “these methods / the two approaches” 先明确要比较的论文与维度，避免早早将后续查询锁定到单篇论文。
2. 最终按两篇论文逐项检查机制、假设、评测维度和复杂度；16/98 说明缺的是证据采用与对比，而非更多泛领域概览。
3. 先修 ordinals 非法 JSON 的恢复路径；38/85 可用于验证修复是否减少无效轮数。
4. 优先复评 11/20/33 等共同缺项或核心相同的回答；对 84 区分训练方案简洁与相对复杂度。
5. 以 36 为负例审查泛化关键词触发的过宽扩展，并用受控实验决定是否需要按问题相关性筛选社区。

## 7. 全部变化案例：诊断、工具时序与完整回答

每例先列观察到的执行变化；重点案例另有人工对照说明。judge reasoning 保留原文，是评分器的解释而非外部事实裁决。下方引用的答案/gold 不截断；原始工具全文由 trace 链接提供。

<a id="case-mdaqa-0"></a>

### mdaqa:0 — 评分与执行路径对照

**问题：** What are the key differences between token-based pruning and weight-based pruning approaches for Vision Transformer compression?

**score：3→4（Δ+1）；rounds：3→3（Δ+0）。**

工具安排：naive 为第1轮1次、第2轮2次；community 为第1轮2次、第2轮2次。最终回答另占一轮。

两边均为 3 轮，但工具总数 3→4，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 33→26、文档 overview 3→20；工具结果字符数 79,351→107,099，QA token 37,678→57,487。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/4b24f0d4fd7f4d2ca92b900a7cd99991.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/d036312b3f2e49a388b4b31724ce071d.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"token-based pruning vs weight-based pruning Vision Transformer compression differences","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0112:0, D0112:2, D0097:4, D0112:1, D0112:3, D0098:16, D0112:22, D0112:14, D0098:0, D0112:4, D0097:3, D0112:21 |
| 2 | 2 | search_chunks {"doc_ids":["D0098"],"query":"difference token pruning weight pruning input-dependent redundancy reduction complementary","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0098:16, D0098:18, D0098:15, D0098:0, D0098:6, D0098:28, D0098:2, D0098:4, D0098:19, D0098:20, D0098:5, D0098:25 |
| 3 | 2 | search_chunks {"doc_ids":["D0097"],"query":"token selection data sparsity weight pruning model sparsity difference input-dependent","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0097:0, D0097:2, D0097:9, D0097:3, D0097:13, D0097:40, D0097:16, D0097:5, D0097:10, D0097:23, D0097:11, D0097:12 |

judge reasoning：

> The generated answer accurately captures the main differences including sequence length reduction and quadratic attention savings, but omits the key difference of token pruning's interpretability advantage.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"token-based pruning vs weight-based pruning Vision Transformer","search_mode":"hybrid","doc_ids":null} | 12 | 20 | 3 | 成功 | D0112:0, D0112:2, D0112:22, D0098:0, D0112:3, D0098:16, D0112:21, D0097:4, D0097:3, D0112:1, D0097:2, D0098:17 |
| 2 | 1 | search_chunks {"query":"token pruning weight pruning comparison ViT compression","search_mode":"vector","doc_ids":null} | 12 | 0 | 0 | 成功 | D0097:0, D0112:0, D0112:2, D0097:4, D0112:9, D0112:22, D0097:2, D0112:1, D0097:1, D0112:3, D0097:16, D0097:7 |
| 3 | 2 | read_chunks {"doc_id":"D0098","ordinals":[16,17,18]} | 3 | 0 | 0 | 成功 | D0098:16, D0098:17, D0098:18 |
| 4 | 2 | search_chunks {"doc_ids":null,"query":"token selection input patch dropping vs weight pruning data-level redundancy model-level redundancy","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0098:15, D0098:16, D0112:24, D0098:18, D0112:2, D0098:6, D0112:14, D0098:0, D0098:4, D0098:13, D0112:4, D0112:25 |

judge reasoning：

> The generated answer accurately captures the core differences between token-based and weight-based pruning, including sequence length reduction, computational savings, and interpretability, while adding consistent supplementary context.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Token-based pruning reduces input sequence length by removing less informative tokens dynamically based on input content, achieving quadratic complexity reduction in self-attention computation. Weight-based pruning focuses on model parameters but maintains the same sequence length, leading to less computational savings. Token pruning also provides better interpretability by showing which image regions are important.

**naive 最终答案**

> Key differences (from the context):
> 
> **What is pruned:**
> - **Token-based pruning**: removes input/data redundancy — dynamically drops uninformative input patch tokens per input instance (data-level sparsity), e.g., via a learned policy/interpreter/top-k token selector.
> - **Weight-based pruning**: removes model/architecture redundancy — drops insignificant weights, attention heads, or MLP neurons (model-level sparsity), e.g., magnitude, gradient, or Taylor importance criteria.
> 
> **Input dependence:**
> - Token-based is **input-dependent/dynamic** — the set of dropped tokens varies per sample; redundancy varies with input content (e.g., higher-resolution images contain more redundancy).
> - Weight-based is generally **static on the model** — the same pruned weights apply to all inputs.
> 
> **Effect on computation:**
> - Token pruning shrinks the input sequence length, which greatly reduces attention cost (attention is quadratic in sequence length), and compresses intermediate features.
> - Weight pruning reduces parameters/FLOPs of linear layers, heads, etc., independent of input length.
> 
> **Relationship/complementarity:**
> - The two are **complementary and orthogonal**: token-based (data-level) redundancy is orthogonal to weight-based (model-level) redundancy, and combining them yields better accuracy–efficiency trade-offs. Token pruning also outperforms weight pruning especially at high FLOPs-reduction ratios.

**community 最终答案**

> Based on the context (IA-RED2, UVC, SViTE):
> 
> **Token-based pruning (e.g., IA-RED2, PatchSlimming, HVT)**
> - Reduces **data-level redundancy**: dynamically drops uninformative input patches/tokens (e.g., via a learned interpreter/policy network), shortening the input sequence.
> - Does not alter the original model's weights; requires no fine-tuning and is model-agnostic, additionally yielding interpretability.
> - Outperforms weight pruning especially when the FLOPs reduction ratio is high.
> 
> **Weight-based pruning (e.g., magnitude-based, SCOP, VTP, SViTE)**
> - Reduces **model-level redundancy**: removes insignificant weights, either unstructured (irregular sparsity, hard to accelerate on hardware) or structured (pruning heads, channels, MLP/FC rows), often requiring train-prune-retrain rounds.
> 
> **Key relationship:** the two are orthogonal/complementary—combining token dropping with weight pruning (IA-RED2 + weight pruning) gives 1.7× acceleration without fine-tuning with only ~1.7% accuracy drop, and jointly optimizing such means (UVC) achieves larger compression (≥50–60% FLOPs savings) with less accuracy loss than token-only or weight-only methods.

</details>

<a id="case-mdaqa-2"></a>

### mdaqa:2 — 评分与执行路径对照

**问题：** What are the key differences in how blocking coalitions are handled between static and dynamic fair division models?

**score：1→0（Δ-1）；rounds：13→9（Δ-4）。**

工具安排：naive 为第1轮2次、第2轮2次、第3轮2次、第4轮2次、第5轮2次、第6轮2次、第7轮2次、第8轮2次、第9轮2次、第10轮2次、第11轮2次、第12轮2次；community 为第1轮2次、第2轮2次、第3轮2次、第4轮2次、第5轮2次、第6轮2次、第7轮2次、第8轮2次。最终回答另占一轮。

轮次减少 4，工具总数 24→16、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 55→48、文档 overview 7→23；工具结果字符数 554,875→429,544，QA token 1,087,758→603,307。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/44f3a526965e478987beed8894a7583b.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/360b662fa6274c58a1cc8b90202b8f0a.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"blocking coalitions static dynamic fair division","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0007:20, D0007:0, D0007:1, D0007:3, D0007:21, D0007:19, D0007:2, D0007:7, D0007:5, D0007:6, D0032:0, D0032:3 |
| 2 | 1 | search_chunks {"query":"blocking coalition core stability dynamic model","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0032:3, D0114:30, D0114:11, D0032:2, D0114:27, D0114:24, D0114:8, D0114:3, D0114:46, D0114:41, D0053:22, D0114:33 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"static fair division blocking coalition dynamic arrival deviation","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0007:0, D0007:1, D0007:20, D0007:2, D0007:3, D0007:5, D0007:6, D0007:21, D0007:19, D0007:7, D0114:8, D0032:3 |
| 4 | 2 | search_chunks {"doc_ids":null,"query":"dynamic fair division game theoretic core blocking coalition envy","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0007:0, D0007:19, D0007:21, D0007:1, D0007:20, D0007:7, D0007:3, D0007:2, D0007:5, D0007:6, D0007:4, D0032:32 |
| 5 | 3 | search_chunks {"doc_ids":null,"query":"blocking coalition fair division static players simultaneously deviate","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0007:0, D0007:20, D0007:21, D0007:3, D0007:19, D0007:1, D0032:3, D0007:2, D0007:7, D0007:4, D0114:8, D0032:2 |
| 6 | 3 | search_chunks {"doc_ids":null,"query":"core stability coalition fair allocation dynamic arrivals departures","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0007:6, D0007:0, D0007:1, D0007:2, D0007:20, D0007:5, D0007:3, D0007:14, D0007:7, D0032:30, D0007:19, D0114:8 |
| 7 | 4 | search_chunks {"doc_ids":["D0007"],"query":"blocking coalition","search_mode":"keyword"} | 0 | 0 | 0 | 成功 | — |
| 8 | 4 | search_chunks {"doc_ids":null,"query":"core blocking coalition fair division allocation game theory static","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0007:21, D0007:20, D0007:0, D0007:3, D0007:1, D0032:3, D0032:32, D0007:19, D0007:4, D0114:8, D0032:30, D0007:5 |
| 9 | 5 | search_chunks {"doc_ids":null,"query":"\"blocking coalition\" fair division dynamic static difference","search_mode":"keyword"} | 12 | 1 | 0 | 成功 | D0007:1, D0007:0, D0007:20, D0007:3, D0007:19, D0007:5, D0032:3, D0007:2, D0007:21, D0032:2, D0007:7, D0068:41 |
| 10 | 5 | search_chunks {"doc_ids":null,"query":"deviation coalition agents arrive depart allocation fairness","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0007:1, D0032:0, D0007:0, D0114:8, D0032:7, D0114:10, D0032:3, D0007:6, D0007:2, D0007:5, D0007:14, D0114:11 |
| 11 | 6 | search_chunks {"doc_ids":null,"query":"blocking coalition static versus dynamic fair division model","search_mode":"keyword"} | 12 | 0 | 0 | 成功 | D0007:1, D0007:0, D0007:20, D0007:3, D0007:5, D0007:19, D0007:2, D0032:3, D0007:21, D0032:2, D0007:7, D0068:41 |
| 12 | 6 | search_chunks {"doc_ids":null,"query":"coalition fair division online offline difference core stability","search_mode":"vector"} | 12 | 0 | 0 | 成功 | D0114:41, D0007:20, D0007:21, D0114:43, D0114:0, D0032:32, D0114:40, D0032:30, D0007:0, D0114:6, D0114:2, D0032:0 |
| 13 | 7 | search_chunks {"doc_ids":null,"query":"fair division static dynamic blocking coalition core deviation","search_mode":"keyword"} | 12 | 0 | 0 | 成功 | D0007:1, D0007:0, D0114:27, D0007:20, D0007:3, D0007:19, D0007:5, D0032:3, D0007:2, D0114:8, D0007:21, D0032:2 |
| 14 | 7 | search_chunks {"doc_ids":null,"query":"dynamic fair division coalition stability arrival departure core","search_mode":"keyword"} | 12 | 1 | 0 | 成功 | D0007:5, D0007:6, D0007:1, D0007:20, D0007:0, D0007:19, D0007:2, D0007:3, D0007:21, D0007:7, D0011:23, D0114:11 |
| 15 | 8 | search_chunks {"doc_ids":null,"query":"fair division coalition core stability dynamic model players leave","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0007:0, D0007:1, D0007:19, D0007:20, D0007:6, D0007:2, D0007:3, D0007:5, D0007:7, D0007:21, D0007:18, D0007:4 |
| 16 | 8 | search_chunks {"doc_ids":null,"query":"blocking coalition static model dynamic model key difference fair division","search_mode":"vector"} | 12 | 0 | 0 | 成功 | D0007:20, D0007:0, D0007:1, D0114:41, D0007:21, D0032:3, D0007:3, D0114:2, D0114:7, D0007:19, D0007:2, D0114:30 |
| 17 | 9 | search_chunks {"doc_ids":null,"query":"coalition dynamic fair division model agents deviate","search_mode":"keyword"} | 12 | 0 | 0 | 成功 | D0007:20, D0007:1, D0007:0, D0007:19, D0114:8, D0007:3, D0007:21, D0007:5, D0007:2, D0007:7, D0032:7, D0032:0 |
| 18 | 9 | search_chunks {"doc_ids":null,"query":"\"fair division\" blocking coalition difference","search_mode":"keyword"} | 12 | 0 | 0 | 成功 | D0032:3, D0007:20, D0007:21, D0032:2, D0007:1, D0007:3, D0007:0, D0114:27, D0007:19, D0114:8, D0007:5, D0007:7 |
| 19 | 10 | search_chunks {"doc_ids":["D0007"],"query":"coalition game theoretic core","search_mode":"keyword"} | 1 | 0 | 0 | 成功 | D0007:19 |
| 20 | 10 | read_chunks {"doc_id":"D0007","ordinals":[8,9,10,11,12]} | 5 | 0 | 0 | 成功 | D0007:8, D0007:9, D0007:10, D0007:11, D0007:12 |
| 21 | 11 | search_chunks {"doc_ids":null,"query":"static model coalition size n/k blocking dynamic model","search_mode":"vector"} | 12 | 0 | 0 | 成功 | D0114:41, D0114:32, D0114:30, D0114:29, D0114:33, D0114:23, D0114:27, D0032:3, D0114:46, D0114:16, D0032:2, D0114:17 |
| 22 | 11 | search_chunks {"doc_ids":null,"query":"core fairness blocking coalition relaxation size improvement","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0114:30, D0032:3, D0114:27, D0114:11, D0114:3, D0114:8, D0114:9, D0032:32, D0114:4, D0032:2, D0114:10, D0114:24 |
| 23 | 12 | search_chunks {"doc_ids":null,"query":"online dynamic core coalition deviating group","search_mode":"hybrid"} | 12 | 1 | 0 | 成功 | D0114:10, D0114:11, D0114:27, D0114:8, D0114:30, D0007:0, D0114:9, D0114:24, D0114:28, D0005:21, D0114:41, D0114:0 |
| 24 | 12 | search_chunks {"doc_ids":null,"query":"dynamic model deviating coalition players arriving simultaneously group fairness","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0007:0, D0007:1, D0007:6, D0007:5, D0007:7, D0007:2, D0007:13, D0007:3, D0114:0, D0007:15, D0007:16, D0007:14 |

judge reasoning：

> The generated answer does not provide the requested differences; it states that the comparison cannot be established from the retrieved content, so it is seriously incomplete relative to the gold answer.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"blocking coalitions static dynamic fair division","search_mode":"hybrid","doc_ids":null} | 12 | 13 | 2 | 成功 | D0007:20, D0007:0, D0007:1, D0007:3, D0007:21, D0007:19, D0007:2, D0007:7, D0007:5, D0007:6, D0032:0, D0032:3 |
| 2 | 1 | search_chunks {"query":"blocking coalition dynamic fair division model","search_mode":"vector","doc_ids":null} | 12 | 10 | 1 | 成功 | D0007:20, D0007:0, D0114:41, D0007:21, D0114:43, D0032:3, D0007:19, D0007:1, D0114:40, D0032:0, D0114:2, D0007:2 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"blocking coalition static dynamic fair division core","search_mode":"keyword"} | 12 | 0 | 0 | 成功 | D0007:1, D0007:0, D0114:27, D0007:20, D0007:3, D0007:19, D0007:5, D0032:3, D0007:2, D0114:8, D0007:21, D0032:2 |
| 4 | 2 | search_chunks {"doc_ids":["D0114"],"query":"blocking coalition dynamic static","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0114:27, D0114:11, D0114:10, D0114:8, D0114:30, D0114:41, D0114:46, D0114:29, D0114:33, D0114:32, D0114:24, D0114:23 |
| 5 | 3 | search_chunks {"doc_ids":null,"query":"blocking coalition online dynamic allocation players core stability","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0007:0, D0114:27, D0007:6, D0007:2, D0007:20, D0114:8, D0007:3, D0007:1, D0114:11, D0114:30, D0032:3, D0032:2 |
| 6 | 3 | search_chunks {"doc_ids":null,"query":"static fair division blocking coalition players arrive departure","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0007:0, D0007:1, D0007:5, D0007:6, D0007:3, D0007:2, D0007:7, D0007:19, D0007:20, D0007:17, D0007:14, D0007:21 |
| 7 | 4 | search_chunks {"doc_ids":null,"query":"core blocking coalition fair division dynamic game stability renegotiation","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0007:20, D0007:0, D0007:19, D0007:21, D0007:1, D0114:8, D0007:3, D0114:27, D0032:3, D0007:7, D0032:32, D0007:2 |
| 8 | 4 | search_chunks {"doc_ids":null,"query":"blocking coalition size requirement n/k deviate center","search_mode":"vector"} | 12 | 0 | 0 | 成功 | D0114:30, D0114:24, D0114:17, D0114:29, D0114:32, D0032:3, D0114:11, D0114:46, D0114:27, D0032:2, D0114:10, D0114:33 |
| 9 | 5 | search_chunks {"doc_ids":null,"query":"blocking coalition deviation dynamic arrivals fairness core empty","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0114:11, D0114:24, D0032:32, D0114:8, D0007:0, D0032:30, D0114:27, D0007:20, D0114:10, D0032:3, D0114:28, D0114:30 |
| 10 | 5 | search_chunks {"doc_ids":null,"query":"coalition of players entitled deviate static proportional solution always exists","search_mode":"keyword"} | 12 | 0 | 0 | 成功 | D0032:3, D0007:2, D0032:2, D0007:5, D0032:5, D0007:0, D0032:13, D0032:10, D0007:3, D0032:4, D0007:1, D0032:26 |
| 11 | 6 | read_chunks {"doc_id":"D0007","ordinals":[0,1,2,3,4,5,6,7,8,9]} | 10 | 0 | 0 | 成功 | D0007:0, D0007:1, D0007:2, D0007:3, D0007:4, D0007:5, D0007:6, D0007:7, D0007:8, D0007:9 |
| 12 | 6 | search_chunks {"doc_ids":null,"query":"group envy-free blocking coalition arrival online fair division dynamic players","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0007:0, D0007:1, D0007:6, D0007:2, D0007:21, D0007:19, D0007:7, D0007:20, D0007:5, D0007:3, D0007:11, D0007:13 |
| 13 | 7 | search_chunks {"doc_ids":null,"query":"blocking coalition fair division static dynamic model player set changes","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0007:0, D0007:1, D0007:3, D0007:20, D0007:2, D0007:19, D0007:7, D0007:21, D0007:5, D0007:4, D0007:6, D0032:2 |
| 14 | 7 | search_chunks {"doc_ids":null,"query":"dynamic fair division coalition stability core arrival departure allocation guaranteed","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0007:6, D0007:0, D0007:1, D0007:5, D0007:20, D0007:2, D0007:3, D0007:19, D0007:21, D0007:7, D0007:4, D0032:30 |
| 15 | 8 | search_chunks {"doc_ids":null,"query":"coalition deviation dynamic model player arrives departs blocking","search_mode":"keyword"} | 12 | 0 | 0 | 成功 | D0007:5, D0007:7, D0032:3, D0032:2, D0007:2, D0007:10, D0114:27, D0007:9, D0007:8, D0007:1, D0007:15, D0114:8 |
| 16 | 8 | search_chunks {"doc_ids":null,"query":"core stability online arrival blocking coalition allocation","search_mode":"vector"} | 12 | 0 | 0 | 成功 | D0114:41, D0114:0, D0114:30, D0114:43, D0114:32, D0114:24, D0032:32, D0114:33, D0007:20, D0114:31, D0007:21, D0114:2 |

judge reasoning：

> The generated answer directly contradicts the gold answer by claiming dynamic models do not discuss blocking coalitions and that the comparison cannot be established, whereas the gold answer specifies dynamic handling considers current and future allocations and imposes more restrictive conditions.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> In static models, blocking coalitions are evaluated based on their current allocation only, while dynamic models must consider both current and future allocations. Static models like proportional clustering allow coalitions of size n/k to block if they can improve their allocation, while dynamic models add constraints that coalitions cannot envy future arrivals and must maintain stability over time. This makes dynamic blocking conditions generally more restrictive.

**naive 最终答案**

> Based on the retrieved content, I can now answer the question.
> 
> The question asks about key differences in how **blocking coalitions** are handled between **static** and **dynamic** fair division models. However, the available collection does not contain a document that directly compares blocking-coalition handling across static vs. dynamic fair division models. What exists is:
> 
> - **Static/online-difference material** (D0007): contrasts static fair division (all players arrive simultaneously, where envy-free/proportional allocations are guaranteed to exist) with dynamic fair division (players arrive one by one over time, where exact envy-free/proportional allocations may not exist). Its "blocking"-type threats are modeled as an **adversary** who designs future players' valuations to force lower-bound violations, not as a coalition that deviates. No blocking-coalition definition (e.g., a minimum-size set that deviates together) appears in this dynamic setting.
> 
> - **Blocking-coalition definitions** (D0032, D0114): these papers define blocking coalitions and core stability (a set S of at least ⌈n/k⌉ agents that can deviate together to improve strictly), but they study **clustering** (public goods/facility location), not the dynamic fair division setting with arrivals/departures, and they do not compare static vs. dynamic models.
> 
> Because the collection does not contain content that addresses blocking coalitions in a dynamic fair division model, the key differences in how blocking coalitions are handled between static and dynamic fair division models **cannot be established** from the provided context. The dynamic fair division paper instead analyzes envy-freeness/proportionality/η-fairness (e.g., O(n)-envy-free, O(log n)-proportional, tight lower bounds), treating fairness violations via adversarial future arrivals rather than via blocking coalitions.

**community 最终答案**

> Based on the available context, blocking coalitions are only formally defined in **static** models (proportional and core fair clustering, D0032/D0114): a coalition S with |S| ≥ n/k blocks a solution if its members can deviate together to a new center and each (proportionality) or the coalition's total (core) strictly improves; a fair solution is one with no such blocking coalition.
> 
> The dynamic fair division model in the collection (D0007) does **not** discuss blocking coalitions as a solution concept. Its key differences are framed through envy-freeness/proportionality instead:
> - In the **static** setting, all players arrive simultaneously and exact envy-free/proportional allocations are guaranteed to exist.
> - In the **dynamic** setting, players arrive/depart over time, exact envy-free/proportional allocations may fail to exist, and an adversary can manipulate future players to violate fairness; fairness is instead guaranteed only approximately (e.g., O(log n)-proportional, O(n)-envy-free) via τ-recallable reallocation of previous players' resources.
> 
> So, while the context contrasts static and dynamic fair division (existence vs. approximation, simultaneous vs. sequential arrivals, reallocation/adversaries), it does not specify how blocking coalitions per se are handled in the dynamic model; that specific comparison cannot be established from the given material.

</details>

<a id="case-mdaqa-4"></a>

### mdaqa:4 — 评分与执行路径对照

**问题：** What are the key differences in how citation information is incorporated into document embeddings between hyperdoc2vec and citation-based contrastive learning?

**score：4→4（Δ+0）；rounds：3→4（Δ+1）。**

工具安排：naive 为第1轮2次、第2轮2次；community 为第1轮2次、第2轮2次、第3轮1次。最终回答另占一轮。

轮次增加 1，工具总数 4→5、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 22→26、文档 overview 2→27；工具结果字符数 65,192→107,651，QA token 39,509→86,487。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具名与解析后的参数完全一致。首个工具返回的有序 chunk ID 不同，仍存在检索结果变化。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/af8085502ed74c728bfd5c7926ecbb31.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/e05906e5a1084a38bd1d4858f09da306.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"hyperdoc2vec citation information document embeddings","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0012:0, D0012:10, D0012:2, D0012:1, D0012:9, D0012:22, D0012:26, D0108:25, D0012:6, D0108:24, D0012:25, D0108:0 |
| 2 | 1 | search_chunks {"query":"citation-based contrastive learning document embeddings","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0108:0, D0108:25, D0108:2, D0108:24, D0108:29, D0108:4, D0108:1, D0108:23, D0108:31, D0108:28, D0012:9, D0012:25 |
| 3 | 2 | read_chunks {"doc_id":"D0012","ordinals":[10]} | 1 | 0 | 0 | 成功 | D0012:10 |
| 4 | 2 | read_chunks {"doc_id":"D0108","ordinals":[3,5,6]} | 3 | 0 | 0 | 成功 | D0108:3, D0108:5, D0108:6 |

judge reasoning：

> The generated answer accurately captures the core difference: hyperdoc2vec directly encodes citation structure via IN/OUT vectors, while contrastive learning uses citations only to guide sampling, fully matching the gold answers.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"hyperdoc2vec citation information document embeddings","search_mode":"hybrid","doc_ids":null} | 12 | 27 | 4 | 成功 | D0012:0, D0012:10, D0012:2, D0012:1, D0012:9, D0012:22, D0012:26, D0108:25, D0108:24, D0012:25, D0108:0, D0012:6 |
| 2 | 1 | search_chunks {"query":"citation-based contrastive learning document embeddings","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0108:0, D0108:25, D0108:2, D0108:24, D0108:29, D0108:1, D0108:4, D0108:23, D0108:31, D0108:28, D0012:9, D0012:25 |
| 3 | 2 | read_chunks {"doc_id":"D0012","ordinals":[10,11,12]} | 3 | 0 | 0 | 成功 | D0012:10, D0012:11, D0012:12 |
| 4 | 2 | read_chunks {"doc_id":"D0108","ordinals":[3,4,5,6]} | 4 | 0 | 0 | 成功 | D0108:3, D0108:4, D0108:5, D0108:6 |
| 5 | 3 | read_chunks {"doc_id":"D0108","ordinals":[7,8]} | 2 | 0 | 0 | 成功 | D0108:7, D0108:8 |

judge reasoning：

> The generated answer fully captures the key distinction from the gold answer: hyperdoc2vec directly encodes citations via IN/OUT vectors, while citation-based contrastive learning uses citation embeddings only to guide contrastive sample selection.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Hyperdoc2vec learns two vectors per document (IN/OUT) to directly model citation relationships in the embedding space, while the contrastive learning approach uses citation graph embeddings to guide the sampling of document pairs for training. The former explicitly encodes citation structure into the representation, while the latter uses citations indirectly to identify semantically similar documents for contrastive learning.

**naive 最终答案**

> Key differences:
> 
> - **hyperdoc2vec** incorporates citations *directly into the learned embeddings*: each document gets two vectors (IN for its role as citing source, OUT for its role as cited target), and citations are modeled explicitly in the training objective (like w2v predicting links), so citation structure is part of the embedding itself.
> 
> - **Citation-based contrastive learning (SciNCL)** does not put citations into the embedding; it uses citation graph embeddings only to *generate training samples*—sampling hard positives and negatives via kNN in citation-embedding space—for triplet/contrastive fine-tuning of a Transformer (SciBERT) document encoder. Citations provide a continuous similarity signal for sample selection rather than being encoded in the document vector itself.

**community 最终答案**

> Based on the context, the key differences are:
> 
> **hyperdoc2vec (D0012):**
> - Citation information is incorporated **directly into the document embedding model itself**: each document gets two vectors (IN vector for its role as citing source, OUT vector for its role as being cited target). For a citation ⟨d_s, C, d_t⟩, the model averages the source's IN vector with the citation-context words C and makes the result predict the target's OUT vector (Eq. 1–3), optimized with negative sampling. Contents are modeled via an additional pv-dm-style objective. So citations and content are jointly modeled in the same embedding objective, and even the citation context words (intent) interact with the vectors.
> 
> **Citation-based contrastive learning (SciNCL, D0108):**
> - Citation information is **not baked into the vector computation**; it is used only to generate contrastive training samples. The model first learns separate **citation graph embeddings** (e.g., via PyTorch BigGraph on S2ORC), then samples positives/negatives from the k-nearest neighbors of the query in that citation-embedding space. These samples are used to train/contrastively fine-tune a SciBERT-based text encoder with a triplet margin loss. Citations therefore provide a continuous, undirected similarity signal only for sample selection (to produce hard positives/negatives), while the final document embeddings are learned from the text through contrastive learning.
> 
> In short: hyperdoc2vec incorporates citations directly into the embedding objective (via IN/OUT vectors), whereas citation-based contrastive learning uses citations only as a signal to construct positive/negative pairs for a contrastive loss on a text encoder.

</details>

<a id="case-mdaqa-7"></a>

### mdaqa:7 — 评分与执行路径对照

**问题：** What are the key approaches to handle symmetric objects in 6D pose estimation?

**score：2→2（Δ+0）；rounds：2→3（Δ+1）。**

工具安排：naive 为第1轮2次；community 为第1轮2次、第2轮1次。最终回答另占一轮。

轮次增加 1，工具总数 2→3、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 20→18、文档 overview 5→13；工具结果字符数 58,354→77,761，QA token 19,348→44,690。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/cff608022746400db28ce068d30a7ad4.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/62f27747082c432cbf46348d2dc0583b.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"symmetric objects 6D pose estimation","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0044:0, D0051:0, D0044:21, D0044:3, D0027:0, D0044:2, D0044:20, D0027:5, D0051:1, D0051:23, D0044:19, D0051:24 |
| 2 | 1 | search_chunks {"query":"pose ambiguity symmetric object handling approach","search_mode":"vector","doc_ids":null} | 12 | 2 | 0 | 成功 | D0044:1, D0044:3, D0051:29, D0090:19, D0016:0, D0044:23, D0044:2, D0027:0, D0027:33, D0090:20, D0044:0, D0044:22 |

judge reasoning：

> The generated answer captures several key approaches from the gold answer (limiting viewpoint ranges, transformer loss, latent representations), but it omits the important approach of predicting multiple possible poses, making it incomplete.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"approaches to handle symmetric objects in 6D pose estimation","search_mode":"hybrid","doc_ids":null} | 12 | 13 | 2 | 成功 | D0044:0, D0044:3, D0044:2, D0027:5, D0051:0, D0027:0, D0027:1, D0044:21, D0051:1, D0027:2, D0051:23, D0044:20 |
| 2 | 1 | search_chunks {"query":"symmetric objects pose estimation ambiguity","search_mode":"vector","doc_ids":null} | 12 | 0 | 0 | 成功 | D0044:1, D0016:0, D0044:2, D0044:0, D0044:3, D0027:33, D0027:0, D0016:20, D0090:19, D0027:32, D0044:21, D0044:20 |
| 3 | 2 | read_chunks {"doc_id":"D0044","ordinals":[1,2,3]} | 3 | 0 | 0 | 成功 | D0044:1, D0044:2, D0044:3 |

judge reasoning：

> The generated answer covers symmetry-aware losses, viewpoint range limiting, and implicit representations, but omits the key approach of predicting multiple possible poses, making it partial rather than perfect.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> The main approaches include: using transformer loss that finds the closest symmetric pose during training, limiting viewpoint ranges, predicting multiple possible poses, and employing latent representations that naturally handle symmetries without explicit supervision.

**naive 最终答案**

> Key approaches for handling symmetric objects in 6D pose estimation:
> 
> 1. **Limiting/transforming pose ranges**: Restricting the range of viewpoints during training rendering, or transforming poses outside the limited range to a symmetric pose within it (e.g., ignoring rotation about the symmetry axis for objects with infinite continuous symmetry like cylinders). Sometimes a CNN is trained to classify view ranges.
> 2. **Point-matching loss**: Loss functions computing the average distance to the nearest points of transformed models between the estimated and annotated pose (e.g., Xiang et al.), though searching nearest 3D points is time-consuming.
> 3. **Template matching**: Matching features to find the nearest pose template and using its pose as an initial guess.
> 4. **Implicit pose representations**: Auto-encoder networks trained without supervision to learn implicit representations of poses that can be close to any symmetric view, avoiding manual handling of symmetric objects (e.g., Sundermeyer et al.).
> 5. **Transformer loss (Pix2Pose)**: A loss that guides predictions to the closest symmetric pose rather than explicitly defined view ranges.

**community 最终答案**

> Key approaches to handle symmetric objects in 6D pose estimation (per the context):
> 
> 1. **Limiting/transforming viewpoint ranges**: restrict the range of poses during rendering/training, or transform poses outside the limited range to a symmetric pose within it. For objects with infinite continuous symmetry on one axis (e.g., cylinders), simply ignore the rotation about that axis.
> 2. **Symmetry-aware loss functions**: design losses that guide predictions to the closest symmetric pose rather than naively penalizing ambiguous views — e.g., Xiang et al.'s loss computing average distance to nearest points of transformed models, or Pix2Pose's transformer loss for objects with a finite number of ambiguous views.
> 3. **Template matching**: match features to the nearest pose template and use the template's pose as an initial guess.
> 4. **Implicit pose representations**: train an auto-encoder to learn implicit pose representations without supervision (e.g., Sundermeyer et al.), so no manual handling of symmetry is needed since the implicit representation can be close to any symmetric view.

</details>

<a id="case-mdaqa-8"></a>

### mdaqa:8 — 评分与执行路径对照

**问题：** What role does multi-view consistency play in learning 3D representations for pose estimation?

**score：4→4（Δ+0）；rounds：3→2（Δ-1）。**

工具安排：naive 为第1轮1次、第2轮2次；community 为第1轮2次。最终回答另占一轮。

轮次减少 1，工具总数 3→2、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 21→19、文档 overview 5→20；工具结果字符数 66,313→76,180，QA token 31,554→23,436。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/ec20bc32299c4c62b9a21220627bf9e8.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/e5cc14ec331941f88896af6b9f4908fd.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"multi-view consistency 3D representation pose estimation","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0051:28, D0066:22, D0066:0, D0051:0, D0016:1, D0051:1, D0066:4, D0051:23, D0066:2, D0057:28, D0051:2, D0051:6 |
| 2 | 2 | search_chunks {"doc_ids":null,"query":"multi-view consistency as supervisory signal learning shape and pose prediction","search_mode":"hybrid"} | 12 | 1 | 0 | 成功 | D0066:22, D0051:28, D0066:0, D0066:23, D0066:2, D0066:4, D0057:27, D0066:1, D0016:20, D0066:8, D0027:0, D0016:0 |
| 3 | 2 | read_chunks {"doc_id":"D0016","ordinals":[1,2,3]} | 3 | 0 | 0 | 成功 | D0016:1, D0016:2, D0016:3 |

judge reasoning：

> The generated answer thoroughly captures the core meaning of the gold answer—multi-view consistency as a self-supervisory signal for learning geometrically consistent 3D representations—and adds relevant, non-contradictory examples and explanations.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"multi-view consistency learning 3D representations pose estimation","search_mode":"hybrid","doc_ids":null} | 12 | 20 | 3 | 成功 | D0051:28, D0066:22, D0066:0, D0066:4, D0016:1, D0051:1, D0051:0, D0066:2, D0057:27, D0057:28, D0051:2, D0066:3 |
| 2 | 1 | search_chunks {"query":"multi-view consistency 3D pose representation","search_mode":"vector","doc_ids":null} | 12 | 0 | 0 | 成功 | D0016:0, D0016:1, D0066:22, D0051:28, D0051:27, D0057:28, D0066:0, D0016:23, D0051:29, D0057:3, D0016:21, D0051:22 |

judge reasoning：

> The generated answer accurately captures the gold answer's core meaning that multi-view consistency provides a self-supervisory signal for learning geometrically consistent 3D representations and pose estimation, with additional relevant examples that do not contradict the gold answer.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Multi-view consistency acts as a self-supervisory signal, helping learn geometrically consistent features and 3D representations by enforcing that predictions from different viewpoints align in 3D space, enabling better generalization and more robust pose estimation.

**naive 最终答案**

> Multi-view consistency plays several key roles in learning 3D representations for pose estimation:
> 
> - **Supervisory signal**: It acts as a self-supervised/unsupervised supervisory signal for learning shape and pose prediction, replacing expensive 3D ground truth or pose annotations (e.g., Tulsiani et al.'s multi-view consistency loss).
> 
> - **Avoids degenerate solutions**: It prevents degenerate reconstructions (e.g., a flat 3D plane that perfectly explains only one image), since multiple views of the same 3D model must reconstruct to the same model.
> 
> - **Enforces consistent representations**: In KeypointNet, a multi-view consistency loss encourages consistent keypoint detections across 3D transformations of an object, yielding geometrically and semantically consistent 3D keypoints that enable accurate relative pose estimation between views (and stable tracking).
> 
> - **Enables render-and-compare pose estimation**: In LatentFusion, multi-view consistency is leveraged (space carving in latent space) to build a latent 3D voxel representation from reference views, which can be rendered from novel viewpoints so pose can be recovered by matching rendered images to the input.
> 
> - **Pose cycle consistency**: In self-supervised point-cloud methods, rotating reconstructions with sampled poses and enforcing cycle consistency on both reconstructions and poses aids training of the pose network.

**community 最终答案**

> Multi-view consistency serves as a supervisory signal for learning 3D representations for pose estimation. In KeypointNet, a multi-view consistency loss encourages consistent keypoint detections across 3D transformations of an object, ensuring stable tracking of discovered 3D keypoints across viewing angles and object instances—which is what makes pose estimation work without ground-truth keypoint annotations. In other works (e.g., point-cloud reconstruction), geometric and pose cycle-consistency losses enforce that multiple views of the same 3D model yield the same reconstruction, with consistent pose predictions, helping avoid degenerate solutions while jointly training shape and pose networks.

</details>

<a id="case-mdaqa-10"></a>

### mdaqa:10 — 评分与执行路径对照

**问题：** What are the key differences in how unsupervised methods handle keypoint detection and alignment compared to supervised approaches?

**score：3→4（Δ+1）；rounds：3→2（Δ-1）。**

工具安排：naive 为第1轮2次、第2轮2次；community 为第1轮2次。最终回答另占一轮。

轮次减少 1，工具总数 4→2、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 38→21、文档 overview 3→13；工具结果字符数 92,615→66,834，QA token 49,327→22,561。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/352d5f82e01347dbb7a7077b3fb1de33.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/b729b4a8380541d99ae7e6c549d4f849.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"unsupervised keypoint detection alignment supervised approaches differences","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0086:0, D0086:12, D0016:27, D0086:3, D0016:13, D0016:25, D0016:24, D0086:16, D0016:14, D0066:13, D0086:15, D0086:18 |
| 2 | 1 | search_chunks {"query":"keypoint detection alignment unsupervised vs supervised","search_mode":"vector","doc_ids":null} | 12 | 0 | 0 | 成功 | D0086:0, D0016:0, D0016:27, D0086:12, D0086:1, D0016:2, D0086:2, D0016:1, D0086:19, D0016:23, D0016:22, D0086:16 |
| 3 | 2 | read_chunks {"doc_id":"D0016","ordinals":[3,4,5,6,7,8,9,10,11,12]} | 10 | 0 | 0 | 成功 | D0016:3, D0016:4, D0016:5, D0016:6, D0016:7, D0016:8, D0016:9, D0016:10, D0016:11, D0016:12 |
| 4 | 2 | read_chunks {"doc_id":"D0086","ordinals":[4,5,6,7,8,9,10,11]} | 8 | 0 | 0 | 成功 | D0086:4, D0086:5, D0086:6, D0086:7, D0086:8, D0086:9, D0086:10, D0086:11 |

judge reasoning：

> The answer accurately captures the core distinction and Skeleton Merger's mechanism, but it omits the CCNs example from the gold answer, making it good but not perfect.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"unsupervised keypoint detection alignment supervised methods differences","search_mode":"hybrid","doc_ids":null} | 12 | 13 | 2 | 成功 | D0086:0, D0086:12, D0016:27, D0016:13, D0016:25, D0086:3, D0086:16, D0016:24, D0016:14, D0086:15, D0016:26, D0086:18 |
| 2 | 1 | search_chunks {"query":"unsupervised versus supervised keypoint detection alignment","search_mode":"vector","doc_ids":null} | 12 | 0 | 0 | 成功 | D0016:0, D0086:0, D0086:1, D0016:1, D0016:23, D0016:2, D0016:22, D0086:19, D0016:27, D0016:20, D0086:12, D0086:2 |

judge reasoning：

> The generated answer accurately captures all key differences and core meaning of the gold answers, including annotation limitations, broader generalization, Skeleton Merger's alignment mechanism, and unsupervised methods matching or exceeding supervised performance, with no contradictions.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Supervised methods rely on limited human-annotated data which restricts their application range, while unsupervised methods like Skeleton Merger and CCNs can work with broader object categories. Skeleton Merger achieves alignment through skeleton topology learning and ordered edge construction, showing competitive or better performance than supervised methods on KeypointNet dataset. CCNs achieve this through view-specific feature extraction using cylindrical convolution kernels. Both demonstrate that carefully designed unsupervised architectures can match or exceed supervised approaches while avoiding annotation limitations.

**naive 最终答案**

> Based on the documents:
> 
> **Supervised approaches** train on human-annotated keypoint labels (e.g., an L2 loss between predicted pixel locations and human labels), with keypoint positions defined a priori. Because keypoint semantics are ambiguous, only limited annotated data exist, so supervised methods cover a limited range of objects and degrade on irregular/uncommon instances.
> 
> **Unsupervised approaches** require no keypoint annotations. They detect keypoints via:
> - **Geometric properties** (traditional hand-crafted detectors like Harris3D, ISS) — stable but not semantically rich, low coverage, unordered and unaligned.
> - **Reconstruction/self-supervision** (Skeleton Merger): an autoencoder whose encoder proposes an *ordered* list of keypoints and predicts skeleton-edge activation strengths; the decoder reconstructs the point cloud from the skeleton, trained with Composite Chamfer Distance. Alignment emerges because the ordered edges define a skeleton topology — wrong ordering yields high reconstruction loss.
> - **Downstream-task optimization** (KeypointNet): keypoints are latent variables optimized end-to-end for a task (relative pose estimation) via multi-view consistency, pose, separation, and silhouette losses, yielding geometrically and semantically consistent keypoints across views/instances.
> 
> Key differences: supervised methods rely on fixed human-defined semantic labels and cannot escape annotation ambiguity/limited categories, whereas unsupervised methods derive alignment from ordered keypoint structures, reconstruction objectives, or downstream geometric tasks, generalizing to more (including irregular) object classes without labels — often matching or outperforming supervised baselines.

**community 最终答案**

> Based on the context, the key differences are:
> 
> **Supervised approaches:**
> - Require large-scale human-annotated keypoint datasets (e.g., Mechanical Turk labels), trained with an L2 loss between predicted keypoint locations and human labels (D0016, D0086).
> - Keypoints are predefined a priori and only cover the limited object range in annotated datasets; they fail to generalize to irregular instances underrepresented in training sets (D0086, D0016).
> - Annotation is expensive, error-prone, and ill-defined due to keypoint ambiguity (e.g., symmetric mugs/jars), limiting applicability (D0086).
> 
> **Unsupervised approaches:**
> - Need no ground-truth keypoint annotations; keypoints are latent variables optimized end-to-end for a downstream task (e.g., relative pose estimation via a differentiable objective plus multi-view consistency loss) or for reconstruction (D0016, D0086).
> - Rely on geometric properties or reconstruction objectives: e.g., Skeleton Merger's autoencoder proposes keypoints and skeleton-edge activation strengths, reconstructs the point cloud, and is guided by Composite Chamfer Distance (fidelity + coverage); alignment comes from the predefined order of skeleton edges (D0086).
> - Traditional unsupervised detectors (Harris3D, ISS) yield stable but semantically poor, low-coverage keypoints that are unordered and unaligned (D0086).
> - Modern unsupervised detectors achieve comparable or better performance than supervised ones (mIoU, rotation errors) and generalize better to irregular/ambiguous objects, since semantics don't need human definition (D0086, D0016).

</details>

<a id="case-mdaqa-11"></a>

### mdaqa:11 — 同样未展开跨视角对齐，2 分落差需复核

**问题：** What role does structural information play in improving object recognition accuracy?

**score：4→2（Δ-2）；rounds：2→2（Δ+0）。**

两份答案都围绕 holistic structure、discriminative regions、local confusion 和 representation learning，均未明确展开 gold 的 semantic alignment across viewpoints/geometric cues。naive judge 仅按核心区域定位给 4，community judge 按缺少其余两项给 2。检索确有不同 chunk/overview，但主要判分理由对共同缺项不对称，不能据此证明新增社区使答案显著变差。

工具安排：naive 为第1轮1次；community 为第1轮1次。最终回答另占一轮。

两边均为 2 轮，但工具总数 1→1，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 12→12、文档 overview 3→19；工具结果字符数 31,077→50,921，QA token 11,281→15,698。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/5cd0273090fd411ea3ea2adfad5e7ca3.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/f843e9f88b0a4ba7ba8efe3910d7876c.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"role of structural information in object recognition accuracy","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0058:3, D0058:4, D0058:25, D0058:20, D0058:2, D0057:0, D0057:2, D0058:0, D0058:23, D0075:0, D0058:9, D0058:13 |

judge reasoning：

> The generated answer accurately captures the core gold point about using holistic structure to localize discriminative regions and adds consistent supporting context without contradiction.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"structural information role in object recognition accuracy","search_mode":"hybrid","doc_ids":null} | 12 | 19 | 3 | 成功 | D0058:3, D0058:4, D0058:20, D0058:0, D0058:25, D0058:2, D0058:1, D0058:9, D0058:14, D0057:2, D0058:23, D0058:22 |

judge reasoning：

> The generated answer correctly captures the role of holistic structural information in localizing discriminative regions, but omits the key facts about semantic alignment across viewpoints and geometric cues beyond appearance, making it only partially complete.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Structural information improves recognition accuracy by: 1) Helping correctly identify discriminative regions through understanding holistic object composition 2) Enabling consistent semantic alignment of object parts across different viewpoints 3) Providing additional geometric cues beyond appearance features for fine-grained recognition.

**naive 最终答案**

> Structural information plays a significant role in image comprehension and improves object recognition accuracy by:
> - Helping correctly identify/localize discriminative regions, since recognizing an object depends largely on its holistic structure (localizing discriminative regions in a well-parsed structure is much easier than in raw feature maps).
> - Preventing the network from falling into local confusion, e.g., distinguishing visually similar objects like front/rear tires of a car or bird legs among twigs, which traditional methods fail at due to lacking cognitive ability for object structures.
> - Enhancing the recognition backbone for more robust representation learning, without extra annotation or inference time cost.

**community 最终答案**

> Structural information helps object recognition by modeling the holistic structure of objects, which correctly localizes the object extent and its discriminative regions. It "reliably prevents the network from falling into local confusion," rectifies the localization of discriminative regions, and enhances robust representation learning—improving accuracy on generic and fine-grained recognition, detection, and segmentation.

</details>

<a id="case-mdaqa-13"></a>

### mdaqa:13 — 评分与执行路径对照

**问题：** How do the approaches to handling sparse rewards in interactive retrieval systems differ in their treatment of global state representation and what are their relative advantages?

**score：3→2（Δ-1）；rounds：5→3（Δ-2）。**

工具安排：naive 为第1轮2次、第2轮2次、第3轮2次、第4轮2次；community 为第1轮2次、第2轮2次。最终回答另占一轮。

轮次减少 2，工具总数 8→4、错误 2→0，整轮全部工具报错的轮数 1→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 33→30、文档 overview 7→35；工具结果字符数 100,793→119,271，QA token 95,387→62,486。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/90b25e84cdb440c4ab396f486c4854e0.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/2e83e35a5eba4d3c9416dbd92bc37cf2.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"sparse rewards interactive retrieval systems global state representation","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0052:16, D0052:1, D0052:0, D0052:2, D0052:18, D0070:0, D0052:6, D0052:15, D0019:24, D0070:1, D0052:3, D0053:22 |
| 2 | 1 | search_chunks {"query":"handling sparse reward exploration interactive retrieval advantages","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0052:16, D0052:0, D0052:1, D0070:0, D0054:20, D0052:18, D0045:24, D0097:0, D0052:19, D0054:1, D0097:2, D0054:12 |
| 3 | 2 | read_chunks {"raw":"{\"doc_id\": \"D0052\", \"ordinals\": 4, 5, 6, 7}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | — |
| 4 | 2 | read_chunks {"raw":"{\"doc_id\": \"D0070\", \"ordinals\": 2, 3, 4, 5}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | — |
| 5 | 3 | read_chunks {"doc_id":"D0052","ordinals":[4,5,6,7]} | 4 | 0 | 0 | 成功 | D0052:4, D0052:5, D0052:6, D0052:7 |
| 6 | 3 | read_chunks {"doc_id":"D0070","ordinals":[0,1,2,3]} | 4 | 0 | 0 | 成功 | D0070:0, D0070:1, D0070:2, D0070:3 |
| 7 | 4 | read_chunks {"doc_id":"D0070","ordinals":[4,5,6,7,8]} | 5 | 0 | 0 | 成功 | D0070:4, D0070:5, D0070:6, D0070:7, D0070:8 |
| 8 | 4 | read_chunks {"doc_id":"D0052","ordinals":[8,9,10,11]} | 4 | 0 | 0 | 成功 | D0052:8, D0052:9, D0052:10, D0052:11 |

judge reasoning：

> The generated answer correctly captures the main approaches and advantages, including CE3's global t-SNE state enabling full exploration and DEG's synthetic-environment densification, but it misses the gold answer's explicit conclusion that the corpus-level approach is more advantageous and omits DEG's limited-exploration caveat, while also adding a claim that DEG uses the same global representation that slightly blurs the contrast.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"sparse rewards interactive retrieval systems global state representation","search_mode":"hybrid","doc_ids":null} | 12 | 24 | 4 | 成功 | D0052:16, D0052:1, D0052:0, D0052:2, D0052:18, D0070:0, D0052:6, D0019:24, D0070:1, D0052:3, D0052:15, D0053:22 |
| 2 | 1 | search_chunks {"query":"sparse reward handling global state representation advantages","search_mode":"hybrid","doc_ids":null} | 12 | 11 | 2 | 成功 | D0072:0, D0059:6, D0105:0, D0053:22, D0059:10, D0026:10, D0105:25, D0059:7, D0080:0, D0010:21, D0073:21, D0009:3 |
| 3 | 2 | read_chunks {"doc_id":"D0070","ordinals":[0,1,2,3,4,5]} | 6 | 0 | 0 | 成功 | D0070:0, D0070:1, D0070:2, D0070:3, D0070:4, D0070:5 |
| 4 | 2 | read_chunks {"doc_id":"D0052","ordinals":[4,5,6,7]} | 4 | 0 | 0 | 成功 | D0052:4, D0052:5, D0052:6, D0052:7 |

judge reasoning：

> The generated answer accurately describes the two approaches and lists some advantages, but it omits the gold answer's key comparative conclusion that the corpus-level (t-SNE global state) approach is more advantageous and that DEG may still suffer from limited exploration.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> The first paper addresses sparse rewards through document environment generation (DEG) by synthesizing positive learning environments from relevant documents, while the second paper tackles it through corpus-level end-to-end exploration using a global state representation compressed via t-SNE. The corpus-level approach proves more advantageous as it allows full exploration of the state space and quick recovery from bad decisions, while DEG focuses on balancing training experiences but may still suffer from limited exploration.

**naive 最终答案**

> Two related approaches are described: **CE3** (D0052) and **DEG** (D0070).
> 
> **CE3 (global representation as the core solution):** Compresses the entire text corpus into a single global low-dimensional representation (t-SNE, dimension 3) kept at all times, encoding both the corpus and retrieval history as the state. This gives the agent access to the full state and action spaces, including under-explored areas, enabling free exploration and recovery from early bad trajectories. Advantage: it outperforms state-of-the-art DS systems and lets user feedback truly control retrieval via a differentiable ranking function.
> 
> **DEG (training-environment enrichment, built on CE3):** Also uses a corpus-level global state representation (following CE3, stacking all documents' doc2vec representations as a snapshot at each time step), but treats sparse rewards primarily as a training problem: it synthesizes additional relevant documents (domain randomization) so the agent meets rewards more frequently, and adds adaptive training that restrains policy change rate based on how far the synthetic environment is from the original (Euclidean distance). Advantage: boosts learning effectiveness by ~22% on unseen topics, provides more stable, lower-variance rewards, and prevents catastrophic forgetting when training on diverse synthetic environments.
> 
> In short: CE3 attacks sparse rewards by making the global state representation give the agent full visibility/exploration over the corpus, while DEG keeps that global representation but attacks sparsity by densifying rewards through synthetic environments with adaptive clipping; CE3's advantage is full-state exploration and better overall retrieval, DEG's is faster, more stable learning and better generalization to unseen topics.

**community 最终答案**

> The collection describes two approaches, both from the same research line (CE3 and its extension DEG):
> 
> **CE3 (D0052):** Treats global state as a low-dimensional t-SNE compression of the *entire corpus*, maintained "at all times." This gives the agent access to the full state and action spaces, including under-explored regions, so it can explore fully and freely.
> 
> **DEG (D0070):** Inherits CE3's corpus-level global state representation (each document segmented into doc2vec vectors; the state is a snapshot of the whole corpus at time t). But it does not change the state representation; instead it attacks sparse rewards at the *environment/training* level—synthesizing extra relevant documents via domain randomization to balance the reward distribution, plus adaptive clipping to limit policy change and avoid catastrophic forgetting.
> 
> **Relative advantages:**
> - CE3's global-state approach enables full exploration of under-explored areas, longer-term planning, and quick recovery from wrong search trajectories (outperforming state-of-the-art DS systems).
> - DEG's synthesis approach boosts learning effectiveness by ~22% (relative) on unseen situations by providing balanced, more informative reward experiences, and adapts conservatively to synthetic environments for more stable, lower-variance training.
> 
> So the key difference: CE3 solves sparse rewards by giving the agent *more visibility* into the global state (exploration), whereas DEG keeps the global state but makes rewards *less sparse* by generating more relevant training documents, with adaptive clipping to protect the learned policy.

</details>

<a id="case-mdaqa-14"></a>

### mdaqa:14 — 评分与执行路径对照

**问题：** What fundamental differences exist between the two approaches in how they enable reinforcement learning agents to recover from poor early decisions in interactive retrieval?

**score：4→4（Δ+0）；rounds：3→4（Δ+1）。**

工具安排：naive 为第1轮1次、第2轮2次；community 为第1轮2次、第2轮2次、第3轮2次。最终回答另占一轮。

轮次增加 1，工具总数 3→6、错误 0→1，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 26→32、文档 overview 5→33；工具结果字符数 67,342→131,253，QA token 32,944→95,165。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/6d9fdb2f0cee456e9a21cb824bfe9e2c.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/4a83472c3fa149bfa7f7f1cae8a0f3eb.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"reinforcement learning recover from poor early decisions interactive retrieval","search_mode":"hybrid","doc_ids":null} | 12 | 5 | 0 | 成功 | D0052:1, D0070:1, D0052:0, D0045:24, D0052:16, D0052:2, D0070:0, D0052:18, D0052:15, D0009:0, D0009:12, D0006:23 |
| 2 | 2 | search_chunks {"doc_ids":["D0070"],"query":"recover wrong decisions sparse rewards domain randomization synthetic environments","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0070:1, D0070:8, D0070:7, D0070:6, D0070:10, D0070:9, D0070:0, D0070:11, D0070:4, D0070:2, D0070:5, D0070:3 |
| 3 | 2 | read_chunks {"doc_id":"D0052","ordinals":[3,4,5,6]} | 4 | 0 | 0 | 成功 | D0052:3, D0052:4, D0052:5, D0052:6 |

judge reasoning：

> The generated answer correctly captures the key distinctions between the two approaches, including DEG's adaptive training with dynamic restraint and the corpus-level/CE3 approach's global representation with differentiable retrieval, without contradicting the gold answers.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"reinforcement learning agent recover from poor early decisions interactive retrieval","search_mode":"hybrid","doc_ids":null} | 12 | 20 | 3 | 成功 | D0052:1, D0052:0, D0052:16, D0045:24, D0052:2, D0070:1, D0070:0, D0052:18, D0006:20, D0006:0, D0009:0, D0105:0 |
| 2 | 1 | search_chunks {"query":"two approaches interactive retrieval RL exploration exploitation recovery","search_mode":"hybrid","doc_ids":null} | 12 | 13 | 2 | 成功 | D0052:1, D0052:0, D0052:16, D0052:2, D0052:3, D0070:0, D0070:1, D0054:0, D0006:21, D0054:1, D0006:20, D0052:11 |
| 3 | 2 | read_chunks {"doc_id":"D0052","ordinals":[4,5,6,7,8,9,10,12,13,14,15]} | 0 | 0 | 0 | Invalid number of chunk ordinals | — |
| 4 | 2 | read_chunks {"doc_id":"D0070","ordinals":[2,3,4,5,6,7]} | 6 | 0 | 0 | 成功 | D0070:2, D0070:3, D0070:4, D0070:5, D0070:6, D0070:7 |
| 5 | 3 | read_chunks {"doc_id":"D0052","ordinals":[4,5,6,7,8]} | 5 | 0 | 0 | 成功 | D0052:4, D0052:5, D0052:6, D0052:7, D0052:8 |
| 6 | 3 | read_chunks {"doc_id":"D0052","ordinals":[9,10,12,13]} | 4 | 0 | 0 | 成功 | D0052:9, D0052:10, D0052:12, D0052:13 |

judge reasoning：

> The generated answer accurately captures the core distinctions between the DEG approach's training-time adaptive policy restraint and the corpus-level approach's global representation with differentiable ranking enabling unrestricted in-episode exploration, with only consistent added detail.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> The DEG approach uses adaptive training with dynamic restraint on policy changes based on environment differences, limiting catastrophic forgetting but potentially constraining exploration. The corpus-level approach maintains a complete global state representation and uses differentiable ranking functions, allowing direct manipulation of document selection and enabling quick recovery from early mistakes through unrestricted exploration of alternative paths.

**naive 最终答案**

> The two approaches enable recovery from poor early decisions in fundamentally different ways:
> 
> **CE3 (architecture/decision-time):** It gives the RL agent direct access to the full state and action spaces by compressing the entire corpus into a global low-dimensional representation (t-SNE), and introduces a differentiable retrieval function. This lets user feedback truly control which documents are returned, so the agent can fully explore under-explored areas and directly adjust its search trajectory during interaction, "quickly recover[ing] from losses in early interactions."
> 
> **DEG (training-time):** It addresses the cause of poor early decisions—sparse, unbalanced rewards. Using domain randomization (Document Environment Generation), it synthesizes many extra relevant documents to create balanced, diverse training environments so the agent meets rewards more frequently and learns a policy with enough reward signals. It also uses adaptive training that restrains the policy's change rate based on how much the synthetic environment differs from the original, preventing catastrophic forgetting and keeping updates conservative—so the agent is less likely to take a big step into a too-good-or-too-bad trajectory and generalizes better in unseen environments.
> 
> In short: CE3 enables recovery by giving the agent complete, differentiable access to explore and correct its trajectory at run time; DEG enables it by enriching/balancing training and constraining policy change so the agent learns robust policies that avoid and recover from bad trajectories.

**community 最终答案**

> The two approaches are CE3 (D0052) and DEG (D0070), and they enable recovery at different stages:
> 
> **CE3 – recovery at exploration/decision time:** It compresses the entire corpus into a global low-dimensional representation, giving the agent access to the full state and action spaces, including under-explored areas. Its differentiable ranking function allows end-to-end manipulation of documents, so after a bad early decision the agent can explore elsewhere in all directions and quickly correct its trajectory.
> 
> **DEG – recovery at training time:** It uses domain randomization (Document Environment Generation) to synthesize more relevant documents, balancing the unbalanced/sparse-reward training experiences so the agent meets rewards more frequently and learns an effective, generalizable policy for unseen situations. Adaptive clipping restrains the policy change rate to prevent catastrophic forgetting. Thus the agent is better trained to avoid wrong decisions when deployed, rather than recovering through in-episode exploration.
> 
> In short: CE3 recovers by giving the agent full exploration capability during retrieval; DEG recovers by improving training experiences so the agent's policy is robust enough to handle unseen situations.

</details>

<a id="case-mdaqa-16"></a>

### mdaqa:16 — SUS-VAE 已被召回，最终答案却只围绕第一篇

**问题：** What improvements were made to address the limitations of using mean-based emotion embedding vectors?

**score：4→2（Δ-2）；rounds：2→2（Δ+0）。**

community 的 overview 从 4→47，但最终只讲 D0047 的 I2I、SA-I2I，漏掉 gold 的 SUS-constrained VAE，4→2 分。同一轮工具中 D0103:0/1 原文和 D0103 overview 已明确含 SUS-constrained VAE，两种模式都拿到了。失分是多论文对照时选择性采用证据，不是图或检索没有覆盖第二篇。文本层还能看到双栏拼接与连字问题，但 overview 已清晰概括 SUS，因此解析问题不能独立解释这次遗漏。

工具安排：naive 为第1轮2次；community 为第1轮2次。最终回答另占一轮。

两边均为 2 轮，但工具总数 2→2，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 17→20、文档 overview 4→47；工具结果字符数 61,501→115,100，QA token 19,708→31,819。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

<details>
<summary>展开 judge 所提实体的字面证据核对</summary>

| 实体/术语 | naive工具中首次匹配 | naive答案 | community工具中首次匹配 | community答案 |
|---|---|---|---|---|
| SUS | 轮1/调用1/D0103:1 | 出现 | 轮1/调用1/D0103:1 | 未匹配 |
| I2I | 轮1/调用1/D0047:3 | 出现 | 轮1/调用1/D0047:3 | 出现 |

这里只检查指定字面串及字母数字边界，不评判上下文是否在讨论同一事实；未匹配不排除同义表述，出现也不代表正确采用。它用于区分“可能未召回”和“已出现但未展开”的复核入口，不能自动判定因果。

</details>

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/d4132500a7484531b7fda75c663470e9.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/f63a03e885954e7aa093e43b9bc27e36.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"mean-based emotion embedding vectors limitations improvements","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0047:3, D0047:2, D0103:0, D0047:4, D0047:1, D0094:0, D0047:0, D0047:5, D0103:1, D0047:9, D0047:6, D0103:8 |
| 2 | 1 | search_chunks {"query":"emotion embedding vector mean average limitation","search_mode":"vector","doc_ids":null} | 12 | 1 | 0 | 成功 | D0047:3, D0103:0, D0047:2, D0018:0, D0047:5, D0103:1, D0047:4, D0047:0, D0094:5, D0018:6, D0094:2, D0018:1 |

judge reasoning：

> The generated answer accurately captures the key improvements from the gold answers, including the I2I ratio for intra/inter-category distances and the SUS-constrained VAE for better cluster cohesion and emotion separation, with additional consistent context.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"limitations of mean-based emotion embedding vectors improvements","search_mode":"hybrid","doc_ids":null} | 12 | 35 | 4 | 成功 | D0047:3, D0047:2, D0103:0, D0047:1, D0047:4, D0103:1, D0047:5, D0047:0, D0094:0, D0047:10, D0047:9, D0047:6 |
| 2 | 1 | search_chunks {"query":"mean embedding vector emotion limitations","search_mode":"vector","doc_ids":null} | 12 | 12 | 2 | 成功 | D0018:0, D0047:3, D0018:1, D0010:21, D0018:6, D0047:4, D0103:0, D0043:2, D0094:12, D0094:1, D0047:2, D0094:5 |

judge reasoning：

> The generated answer correctly captures the first gold improvement (I2I ratio) but omits the second gold improvement (SUS-constrained VAE) and instead substitutes a different method, making it only partially complete.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> The first paper introduced I2I ratio to consider both intra and inter-category distances when selecting representative vectors, while the second paper used SUS-constrained VAE to achieve better cluster cohesion and emotion separation compared to simple mean-based approaches.

**naive 最终答案**

> To address the limitations of mean-based emotion embedding vectors (which ignore the distribution/variance of weights, fail to fully represent the target emotion, and neglect other emotion categories during interpolation), the following improvements were proposed:
> 
> - **I2I (inter-to-intra distance ratio) method**: representative embedding vectors are selected to minimize intra-category distance while maximizing distance to the closest and farthest emotion categories, considering the distributions of the target and other emotion categories simultaneously (rather than simply averaging).
> - **SA-I2I (spread-aware I2I) interpolation**: artificially generates weight-vector distributions for the desired emotion intensity and applies non-linear interpolation using the neutral category as the reference, keeping vectors within emotion-cluster boundaries.
> - **SUS-constrained VAE**: constrains embedding means to lie on the unit-sphere surface with a uniform standard deviation across dimensions, improving cluster cohesion and reducing disturbance.
> 
> These methods achieved better emotional clarity, expressiveness, and intensity controllability than the mean-based approach.

**community 最终答案**

> The improvements (D0047) were:
> 
> 1. **I2I (inter-to-intra distance ratio) method**: Instead of averaging, representative embedding vectors are chosen to maximize the ratio of inter-category distance over intra-category distance, considering the distributions of the target and other emotion categories simultaneously. This yielded representative vectors farther from other emotion clusters, improving emotional clarity.
> 
> 2. **SA-I2I (spread-aware I2I) interpolation**: Artificially generates weight-vector samples with a distribution of desired emotion intensity, then applies the I2I method to find representative vectors, using nonlinear interpolation from neutral to target emotion. This avoids the artifact of linear interpolation (points lying outside emotion cluster regions), enabling smooth, controllable emotion intensity without quality degradation.

</details>

<a id="case-mdaqa-17"></a>

### mdaqa:17 — 评分与执行路径对照

**问题：** How do the evaluation methods differ in assessing emotion expressiveness between the two approaches?

**score：4→3（Δ-1）；rounds：4→3（Δ-1）。**

工具安排：naive 为第1轮1次、第2轮2次、第3轮1次；community 为第1轮2次、第2轮2次。最终回答另占一轮。

轮次减少 1，工具总数 4→4、错误 1→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 24→23、文档 overview 3→42；工具结果字符数 66,244→122,031，QA token 50,661→63,467。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/97a7c8f091c445ff81e36e5ceecd45fb.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/562eefe775424bb787ae11dee7ad3308.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"evaluation methods assessing emotion expressiveness approaches","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0047:0, D0047:1, D0011:18, D0103:0, D0047:2, D0047:4, D0047:10, D0047:5, D0047:8, D0011:19, D0047:3, D0103:1 |
| 2 | 2 | read_chunks {"raw":"{\"doc_id\": \"D0047\", \"ordinals\": 8, 9, 10}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | — |
| 3 | 2 | search_chunks {"query":"subjective evaluation emotional expressiveness A/B preference test mean opinion score","search_mode":"hybrid","doc_ids":["D0103"]} | 12 | 0 | 0 | 成功 | D0103:6, D0103:7, D0103:8, D0103:0, D0103:1, D0103:11, D0103:10, D0103:4, D0103:3, D0103:9, D0103:5, D0103:2 |
| 4 | 3 | read_chunks {"doc_id":"D0047","ordinals":[8,9,10,11]} | 4 | 0 | 0 | 成功 | D0047:8, D0047:9, D0047:10, D0047:11 |

judge reasoning：

> The generated answer accurately captures both papers' evaluation methods, matching the gold answers' key facts with only minor additional context.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"evaluation methods emotion expressiveness two approaches","search_mode":"hybrid","doc_ids":null} | 12 | 34 | 4 | 成功 | D0047:0, D0047:5, D0103:0, D0047:2, D0047:4, D0047:1, D0047:7, D0011:18, D0047:6, D0103:1, D0047:10, D0047:3 |
| 2 | 1 | search_chunks {"query":"assessing emotion expressiveness evaluation","search_mode":"vector","doc_ids":null} | 12 | 8 | 1 | 成功 | D0135:13, D0047:1, D0047:8, D0046:4, D0047:9, D0047:0, D0103:7, D0047:10, D0046:24, D0094:14, D0011:18, D0046:27 |
| 3 | 2 | read_chunks {"doc_id":"D0103","ordinals":[5,6,7,8]} | 4 | 0 | 0 | 成功 | D0103:5, D0103:6, D0103:7, D0103:8 |
| 4 | 2 | read_chunks {"doc_id":"D0047","ordinals":[7,8,9,10]} | 4 | 0 | 0 | 成功 | D0047:7, D0047:8, D0047:9, D0047:10 |

judge reasoning：

> The generated answer correctly identifies most evaluation methods for both approaches, but incorrectly states that MOS was used only for speech quality rather than for emotional clarity and quality as in the gold answer, so it is slightly inaccurate.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> The first paper used preference tests and MOS for emotional clarity and quality, plus accuracy tests for intensity control. The second paper employed MCD scores, A/B preference tests, t-SNE visualization of emotion clusters, and correlation analysis of prosody attributes (energy, duration, F0).

**naive 最终答案**

> The two papers (D0047's I2I/interpolation approach and D0103's SUS-VAE/aggregation approach) evaluate emotional expressiveness differently:
> 
> **D0047** relies on **subjective listening tests only**:
> - A paired preference test where listeners pick which sample represents the emotion more clearly (proposed vs. mean-based method).
> - A "granularity" test where listeners choose the stronger-emotion sample between neighboring interpolation intensity pairs (reported as recognition accuracy).
> - MOS tests assess speech quality, not expressiveness.
> 
> **D0103** combines **objective and subjective measures**:
> - Objective: MCD (mel cepstral distortion) on the test set.
> - Subjective: A/B preference tests (30 samples, 20 listeners) choosing the more expressive audio.
> - Analysis: t-SNE visualization of emotion-embedding clusters, plus Pearson correlation of phoneme-level prosody (energy, duration, F0) against ground truth to measure emotion expressiveness.
> 
> In short, D0047 measures expressiveness purely through listener preference/recognition choices on emotion clarity and intensity, whereas D0103 adds quantitative objective metrics (MCD, prosody correlation with ground truth, embedding cluster cohesion) alongside A/B preference.

**community 最终答案**

> The two approaches differ in how they evaluate emotion expressiveness:
> 
> - **D0047 (I2I/SA-I2I approach)** relies on **subjective tests**: a preference test where listeners select the sample that expresses emotion more clearly (I2I vs. mean-based), plus a granularity test measuring recognition accuracy of neighboring emotion-intensity pairs (choosing the stronger emotion between samples at different interpolation ratios). MOS was used only for speech-quality (not expressiveness), showing no significant difference.
> 
> - **D0103 (SUS-VAE approach)** combines **objective and subjective measures**: MCD (mel cepstral distortion) for closeness to ground truth, Pearson correlation of phoneme-level prosody attributes (relative energy, duration, F0) with ground truth, t-SNE cluster visualization, and A/B preference tests where listeners pick the more expressive sample.
> 
> In short, D0047 assesses expressiveness purely through subjective preference and intensity-granularity recognition, while D0103 assesses it via objective metrics (MCD, prosody correlations) supplemented by A/B preference tests.

</details>

<a id="case-mdaqa-19"></a>

### mdaqa:19 — 评分与执行路径对照

**问题：** How does the anisotropic nature of contextual embeddings manifest differently at global versus local levels?

**score：3→3（Δ+0）；rounds：3→2（Δ-1）。**

工具安排：naive 为第1轮1次、第2轮1次；community 为第1轮2次。最终回答另占一轮。

轮次减少 1，工具总数 2→2、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 14→18、文档 overview 7→57；工具结果字符数 44,300→123,269，QA token 25,631→34,113。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/739f6af3b56f4026b3b49949cad2e035.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/b105428eb3f64b8597a07401bb0402da.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"anisotropic nature of contextual embeddings global versus local levels","search_mode":"hybrid","doc_ids":null} | 12 | 7 | 0 | 成功 | D0094:0, D0094:12, D0094:4, D0008:0, D0113:0, D0094:3, D0020:20, D0115:5, D0115:6, D0018:0, D0071:24, D0071:26 |
| 2 | 2 | read_chunks {"doc_id":"D0094","ordinals":[1,2,3,4]} | 4 | 0 | 0 | 成功 | D0094:1, D0094:2, D0094:3, D0094:4 |

judge reasoning：

> The generated answer correctly captures the global anisotropy vs. local isotropy contrast and BERT/RoBERTa behavior, but omits the key detail that GPT-2 remains fairly anisotropic even at the local level.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"anisotropic nature of contextual embeddings global local","search_mode":"hybrid","doc_ids":null} | 12 | 43 | 5 | 成功 | D0094:0, D0094:12, D0094:4, D0094:1, D0094:3, D0115:5, D0020:20, D0115:6, D0018:0, D0071:24, D0071:26, D0032:13 |
| 2 | 1 | search_chunks {"query":"anisotropy contextual embeddings geometry global level local level","search_mode":"vector","doc_ids":null} | 12 | 14 | 2 | 成功 | D0094:4, D0094:0, D0094:2, D0094:12, D0094:3, D0094:5, D0094:1, D0094:6, D0094:15, D0081:0, D0094:17, D0020:20 |

judge reasoning：

> The generated answer correctly captures the global anisotropy and local isotropy after zero-mean clustering, but omits the important model-specific distinction (BERT/RoBERTa vs GPT-2) mentioned in the gold answer.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> While contextual embeddings are highly anisotropic when viewed globally across all layers, they show significantly more isotropy when analyzed locally within clusters after making each cluster zero-mean. This local-global disparity is particularly pronounced in BERT and RoBERTa, though GPT-2 remains fairly anisotropic even at the local level.

**naive 最终答案**

> At a **global** level, contextual embeddings (BERT, GPT-2, RoBERTa) are extremely anisotropic in all non-input layers, forming a narrow cone where even unrelated words have excessively high cosine similarity. The embedding space appears dominated by a single global dominant direction.
> 
> At a **local** level, the space is significantly more isotropic: when embeddings are clustered (e.g., by k-means) and each cluster is made zero-mean, isotropy greatly improves (BERT and RoBERTa become almost isotropic). Not all clusters share the same dominant directions, so global directions fail to capture local degenerate ones. Locally, different clusters (word types, entities, senses) encode distinct information—e.g., clusters with punctuation/stop words encode structural/contextual information, while verb clusters organize by tense rather than sense.

**community 最终答案**

> At the global level, contextual word embeddings appear extremely anisotropic in all non-input layers—vectors concentrate in a narrow cone, so even unrelated words show excessively positive correlations. At the local level, however, the space is significantly more isotropic: when embeddings are clustered and each cluster is made zero-mean, the distribution is notably more uniform. Moreover, local clusters do not all share the same dominant directions; each cluster has its own cluster-specific dominant directions (e.g., structural information in punctuation/stop-word clusters, tense in verb clusters), so globally computed dominant directions cannot capture or remove these local degenerated directions.

</details>

<a id="case-mdaqa-20"></a>

### mdaqa:20 — 共同给出 FRAGE，却对 cluster 缺项不同判分

**问题：** What role do frequency-based word distributions play in embedding space quality and how can this be addressed?

**score：4→2（Δ-2）；rounds：2→2（Δ+0）。**

两边都说明 rare/popular embedding 分区，并给出 FRAGE 对抗训练，均未明确展开 gold 的 cluster-based 替代方案。naive 给 4、community 给 2；后者还多给了 degeneration/CosReg 相关说明。judge 对同一缺项重要性不一致，因此 −2 不应直接解释为社区损害事实正确性。初始首个 query 相同，但 community 首轮多发了一条搜索，仍不属于完全受控的社区消融。

工具安排：naive 为第1轮1次；community 为第1轮2次。最终回答另占一轮。

两边均为 2 轮，但工具总数 1→2，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 12→16、文档 overview 7→37；工具结果字符数 36,425→101,330，QA token 12,108→28,868。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

<details>
<summary>展开 judge 所提实体的字面证据核对</summary>

| 实体/术语 | naive工具中首次匹配 | naive答案 | community工具中首次匹配 | community答案 |
|---|---|---|---|---|
| FRAGE | 轮1/调用1/D0018:0 | 出现 | 轮1/调用1/D0018:0 | 出现 |

这里只检查指定字面串及字母数字边界，不评判上下文是否在讨论同一事实；未匹配不排除同义表述，出现也不代表正确采用。它用于区分“可能未召回”和“已出现但未展开”的复核入口，不能自动判定因果。

</details>

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/0858ca26f44b421b83ee519ce83ca3f1.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/ec7a31543d804207a31773e8af9cd827.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"frequency-based word distributions embedding space quality","search_mode":"hybrid","doc_ids":null} | 12 | 7 | 0 | 成功 | D0018:0, D0018:2, D0018:1, D0094:0, D0018:14, D0094:2, D0094:1, D0043:17, D0010:22, D0029:7, D0020:20, D0004:9 |

judge reasoning：

> The generated answer accurately captures the core issue of frequency-based subregion division and correctly details the adversarial training solution (FRAGE), consistent with one of the gold answers, with no contradictions.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"frequency-based word distributions embedding space quality","search_mode":"hybrid","doc_ids":null} | 12 | 37 | 5 | 成功 | D0018:0, D0018:2, D0018:1, D0094:0, D0018:14, D0094:2, D0094:1, D0043:17, D0010:22, D0029:7, D0020:20, D0004:9 |
| 2 | 1 | search_chunks {"query":"word frequency distribution affects embedding quality anisotropic","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0018:0, D0018:2, D0094:0, D0094:2, D0018:14, D0094:1, D0018:6, D0043:17, D0094:12, D0043:25, D0020:20, D0043:5 |

judge reasoning：

> The generated answer correctly describes the frequency-based divide and the adversarial training solution, but it omits the cluster-based approach mentioned in the gold answer, making it an incomplete response to how the issue can be addressed.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Word frequency creates a problematic divide where rare and popular words occupy different subregions of the embedding space, even though many rare words share semantic relationships with popular ones. This can be addressed through adversarial training to make embeddings frequency-agnostic, or through cluster-based approaches that handle local regions separately.

**naive 最终答案**

> Word frequency (following Zipf's law) biases embeddings: high- and low-frequency words lie in different subregions of the embedding space, so a rare word and a popular word can be far apart even when semantically similar. This degrades embedding quality, especially for rare words, and limits downstream task performance. It is addressed with FRAGE, an adversarial training method: a discriminator classifies whether an embedding comes from a popular or rare word, while embeddings are optimized to fool it (in addition to minimizing the task loss). At equilibrium the discriminator cannot separate the two, so rare and popular words become mixed in the same region, capturing better semantic information.

**community 最终答案**

> Frequency-based word distributions (following Zipf's law) degrade embedding space quality: embeddings of high-frequency (popular) and low-frequency (rare) words lie in different subregions of the space, so rare and popular words can be far apart even when semantically similar. Rare words' nearest neighbors are usually semantically unrelated rare words, meaning embeddings encode more frequency information than semantic information, which harms rare words and limits downstream task performance. This happens because popular words are sampled and updated more often during training (moving ~2x farther), while rare words rarely update and remain near the origin.
> 
> It can be addressed via adversarial training (FRAGE): a discriminator classifies embeddings as popular/rare, while embeddings are optimized to fool it (and minimize task loss), so rare and popular words become mixed in the same region. Simple frequency reweighting and weight decay were shown to fail or hurt. Relatedly, in generation models, low-frequency tokens degenerate into a narrow cone; cosine-similarity regularization (MLE-CosReg) can enlarge the cone to improve quality.

</details>

<a id="case-mdaqa-23"></a>

### mdaqa:23 — 评分与执行路径对照

**问题：** What role does speaker-specific training play in improving lip-to-speech synthesis quality?

**score：4→3（Δ-1）；rounds：2→2（Δ+0）。**

工具安排：naive 为第1轮1次；community 为第1轮1次。最终回答另占一轮。

两边均为 2 轮，但工具总数 1→1，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 12→12、文档 overview 6→34；工具结果字符数 34,751→69,724，QA token 11,964→19,817。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具名与解析后的参数完全一致。首个工具返回的有序 chunk ID 不同，仍存在检索结果变化。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/16c09e29ef684cb1acb32ae842d80ddf.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/7451a65ebefa4ac9871a14824dc3c8aa.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"speaker-specific training lip-to-speech synthesis quality","search_mode":"hybrid","doc_ids":null} | 12 | 6 | 0 | 成功 | D0067:0, D0067:3, D0115:0, D0067:5, D0135:0, D0067:16, D0115:2, D0067:6, D0143:0, D0067:2, D0103:11, D0047:13 |

judge reasoning：

> The generated answer accurately captures the key facts from the gold answer, including the importance of speaker-specific training, the use of large per-speaker datasets (~20 hours), and the roughly 4x intelligibility improvement, with no contradictions.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"speaker-specific training lip-to-speech synthesis quality","search_mode":"hybrid","doc_ids":null} | 12 | 34 | 4 | 成功 | D0067:0, D0067:3, D0115:0, D0067:5, D0135:0, D0067:16, D0115:2, D0143:0, D0067:2, D0067:6, D0103:11, D0047:13 |

judge reasoning：

> The generated answer correctly captures the key benefits of speaker-specific training (large per-speaker data, 4x intelligibility, natural prosody/voice matching) but omits the important caveat about reduced generalization to unseen speakers.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Speaker-specific training with large amounts of data per speaker (20+ hours) significantly improves synthesis quality compared to multi-speaker approaches, achieving up to 4x better intelligibility and more natural prosody. However, this comes at the cost of reduced generalization to unseen speakers.

**naive 最终答案**

> Speaker-specific training plays a central role in improving lip-to-speech synthesis quality. By learning the speech patterns of an individual speaker (analogous to how lipreaders find it easier to lip-read familiar people), models can capture speaker-specific contextual cues that are essential for accurate speech inference. The Lip2Wav work focuses on learning precise individual speaking styles, and its large per-speaker dataset (about 20 hours and ~5,000-word vocabulary per speaker—800× more data per speaker than multi-speaker datasets) enables accurate modeling of speaker-specific audio-visual cues. This single-speaker, unconstrained approach made the method roughly four times more intelligible than previous works.

**community 最终答案**

> Speaker-specific training allows models to learn precise individual speaking styles and speaker-specific audio-visual cues, which are essential for accurate lip-reading. With large per-speaker data (e.g., ~20 hours/speaker), it enables accurate modeling of speaker-specific audio-visual mappings, making synthesized speech far more intelligible and natural (e.g., Lip2Wav is four times more intelligible than prior works), and matches the target speaker's voice and prosody.

</details>

<a id="case-mdaqa-25"></a>

### mdaqa:25 — 评分与执行路径对照

**问题：** How does the integration of audio and visual modalities in speaker diarization systems address the limitations of single-modality approaches in challenging meeting environments?

**score：4→4（Δ+0）；rounds：3→2（Δ-1）。**

工具安排：naive 为第1轮2次、第2轮1次；community 为第1轮2次。最终回答另占一轮。

轮次减少 1，工具总数 3→2、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 27→15、文档 overview 5→29；工具结果字符数 72,884→85,034，QA token 42,058→26,304。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/8fe0f98eeb564fbd83d160553e385963.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/80df4177efa6436c92138cefe8712ad0.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"audio visual multimodal speaker diarization meeting","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0136:0, D0136:17, D0136:1, D0106:1, D0136:2, D0136:16, D0136:11, D0106:0, D0136:15, D0136:10, D0106:11, D0106:3 |
| 2 | 1 | search_chunks {"query":"fusion audio and visual modalities limitations single modality","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0002:0, D0136:1, D0115:4, D0136:11, D0136:17, D0002:13, D0135:11, D0115:5, D0136:0, D0002:10, D0002:1, D0002:4 |
| 3 | 2 | read_chunks {"doc_id":"D0136","ordinals":[3,4,5,6,7,8,9]} | 7 | 0 | 0 | 成功 | D0136:3, D0136:4, D0136:5, D0136:6, D0136:7, D0136:8, D0136:9 |

judge reasoning：

> The generated answer fully captures the complementary strengths of audio and visual modalities, correctly describes the limitations of ASD and VSD, and reports results consistent with the gold answers.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"audio visual multimodal speaker diarization limitations single modality meeting","search_mode":"hybrid","doc_ids":null} | 12 | 29 | 3 | 成功 | D0136:1, D0136:17, D0136:0, D0136:11, D0106:1, D0136:2, D0106:0, D0136:16, D0136:9, D0136:10, D0136:4, D0106:11 |
| 2 | 1 | search_chunks {"query":"integration of audio and visual modalities in speaker diarization challenging meeting environments","search_mode":"vector","doc_ids":null} | 12 | 0 | 0 | 成功 | D0136:17, D0136:1, D0136:0, D0136:15, D0106:1, D0136:16, D0136:11, D0106:3, D0106:0, D0136:2, D0136:9, D0106:12 |

judge reasoning：

> The generated answer accurately captures the complementary strengths of audio and visual modalities, the specific limitations of single-modality approaches, and the superior performance of the combined system, fully matching the gold standard.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Integration of audio and visual modalities provides complementary strengths - visual modality is robust against acoustic noise and overlapping speech, while audio helps correct errors from poor visual quality (like lip peristalsis). In experiments, audio-visual speaker diarization (AVSD) achieved better performance than audio-only (ASD) or visual-only (VSD) approaches by reducing false alarms, missed detections, and speaker confusion errors. ASD struggled with background noise and speaker overlap, while VSD had high false alarm rates due to lip movements in silent segments. The combined AVSD system leveraged both modalities to overcome their individual weaknesses.

**naive 最终答案**

> Based on the MISP2022 challenge context:
> 
> Audio-only speaker diarization (ASD) degrades in real meetings due to strong background noise (e.g., loud TV noise) and high overlapping-speech ratios, causing high missed-detection and speaker-error rates. Visual-only diarization (VSD) is not disturbed by the harsh acoustic environment and outperforms ASD, but suffers a high false-alarm rate from lip movement without utterance (peristalsis) and poor far-field video quality.
> 
> Integrating audio and visual modalities addresses these limitations through information complementation: audio modality corrects visual errors (e.g., lip-peristalsis confusion, indistinguishable speakers with similar timbre), while visual modality compensates for acoustic failures (e.g., TV noise covering target speech). The fused AVSD system combines both modalities to overcome their individual weaknesses, yielding the best DER (13.09% vs. 31.25% for ASD and 18.69% for VSD), and it also corrects speech recognition errors caused by wrong diarization results.

**community 最终答案**

> In challenging meeting environments, audio-only speaker diarization suffers from strong background noise (e.g., loud TV noise that covers or mimics target speakers) and high ratios of overlapping speech, causing speaker confusion. Visual-only diarization is degraded by low far-field video quality (small lip ROIs, dim light, occlusion) and by "peristalsis" (lip movement without speech). Integrating the two modalities addresses these limits through complementary information: the visual modality is not disturbed by harsh acoustic environments, so it disambiguates speakers and corrects errors the audio modality makes under TV noise; conversely, the audio modality compensates for poor/ambiguous video, correcting speaker confusion caused by lip movement and indistinguishable timbre. Through this audio–visual complementation, diarization results become consistent with ground truth, and the combined (AVSD/AVDR) system outperforms both audio-only (ASD) and visual-only (VSD) approaches, yielding the best overall performance.

</details>

<a id="case-mdaqa-27"></a>

### mdaqa:27 — 减少接口恢复和旁支搜索，缺项仍在

**问题：** What are the key differences in how various neural simulation frameworks handle the disentanglement of static and dynamic scene elements?

**score：2→2（Δ+0）；rounds：8→4（Δ-4）。**

naive 第 2 轮两次读取均为非法 JSON，随后恢复读取并继续搜索 D-NeRF 等旁支，8 轮、249,986 token；community 4 轮、88,918 token，无错误。两边同为 2 分，均漏 Meta-Sim。可以确认成本降低来自少一次全失败轮及更少旁支探索，但既没有补齐比较对象，也不能把全部四轮差都归于工具错误。

工具安排：naive 为第1轮2次、第2轮2次、第3轮2次、第4轮2次、第5轮1次、第6轮2次、第7轮2次；community 为第1轮1次、第2轮3次、第3轮2次。最终回答另占一轮。

轮次减少 4，工具总数 13→6、错误 2→0，整轮全部工具报错的轮数 1→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 60→41、文档 overview 14→25；工具结果字符数 203,742→140,672，QA token 249,986→88,918。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/f031defe03aa4089a3e182878182c84d.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/3a60dfc0d09146f6b540fa51512647ff.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"disentanglement static and dynamic scene elements neural simulation framework","search_mode":"hybrid","doc_ids":null} | 12 | 5 | 0 | 成功 | D0089:0, D0068:0, D0051:27, D0089:8, D0068:6, D0053:22, D0068:11, D0068:8, D0075:0, D0053:26, D0068:15, D0089:1 |
| 2 | 1 | search_chunks {"query":"static dynamic scene disentanglement framework differences","search_mode":"vector","doc_ids":null} | 12 | 4 | 0 | 成功 | D0089:0, D0068:0, D0048:0, D0053:24, D0090:18, D0051:27, D0053:25, D0075:0, D0053:26, D0137:33, D0053:23, D0076:28 |
| 3 | 2 | read_chunks {"raw":"{\"doc_id\": \"D0089\", \"ordinals\": 8, 9, 10}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | — |
| 4 | 2 | read_chunks {"raw":"{\"doc_id\": \"D0068\", \"ordinals\": 7, 8, 11}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | — |
| 5 | 3 | read_chunks {"doc_id":"D0089","ordinals":[8,9,10]} | 3 | 0 | 0 | 成功 | D0089:8, D0089:9, D0089:10 |
| 6 | 3 | read_chunks {"doc_id":"D0068","ordinals":[11,12,13]} | 3 | 0 | 0 | 成功 | D0068:11, D0068:12, D0068:13 |
| 7 | 4 | search_chunks {"doc_ids":null,"query":"static background dynamic objects disentangle neural simulator rendering","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0068:0, D0068:11, D0089:0, D0068:14, D0068:15, D0068:6, D0068:7, D0068:5, D0068:40, D0089:8, D0068:13, D0068:4 |
| 8 | 4 | read_chunks {"doc_id":"D0137","ordinals":[0,1,2]} | 3 | 0 | 0 | 成功 | D0137:0, D0137:1, D0137:2 |
| 9 | 5 | search_chunks {"doc_ids":null,"query":"neural simulator disentangle static dynamic theme content latent world model","search_mode":"hybrid"} | 12 | 2 | 0 | 成功 | D0089:0, D0068:0, D0089:8, D0089:7, D0089:15, D0089:10, D0089:16, D0089:72, D0089:17, D0105:26, D0068:3, D0072:21 |
| 10 | 6 | read_chunks {"doc_id":"D0089","ordinals":[17,18,19,20,21]} | 5 | 0 | 0 | 成功 | D0089:17, D0089:18, D0089:19, D0089:20, D0089:21 |
| 11 | 6 | read_chunks {"doc_id":"D0068","ordinals":[7,8,9]} | 3 | 0 | 0 | 成功 | D0068:7, D0068:8, D0068:9 |
| 12 | 7 | search_chunks {"doc_ids":null,"query":"D-NeRF DeRF decomposed radiance fields dynamic scenes static","search_mode":"hybrid"} | 12 | 2 | 0 | 成功 | D0137:33, D0137:30, D0137:32, D0137:31, D0099:0, D0137:36, D0137:38, D0137:35, D0137:0, D0137:39, D0128:23, D0137:4 |
| 13 | 7 | search_chunks {"doc_ids":null,"query":"neural simulator world model disentangle foreground background video prediction","search_mode":"hybrid"} | 12 | 1 | 0 | 成功 | D0048:0, D0089:77, D0089:0, D0089:8, D0072:21, D0068:0, D0048:1, D0048:2, D0133:0, D0133:1, D0053:22, D0089:49 |

judge reasoning：

> The generated answer accurately describes GameGAN and DriveGAN but omits Meta-Sim, which is a key framework in the gold answer, making it incomplete.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"neural simulation frameworks disentangle static and dynamic scene elements","search_mode":"hybrid","doc_ids":null} | 12 | 25 | 4 | 成功 | D0089:0, D0068:0, D0051:27, D0072:21, D0089:1, D0068:6, D0068:11, D0075:0, D0053:22, D0090:17, D0072:0, D0068:8 |
| 2 | 2 | search_chunks {"doc_ids":["D0068","D0089"],"query":"disentangle static dynamic components rendering engine memory module","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0068:11, D0068:8, D0068:4, D0068:7, D0068:0, D0068:30, D0068:6, D0068:1, D0068:13, D0068:5, D0068:37, D0068:28 |
| 3 | 2 | read_chunks {"doc_id":"D0068","ordinals":[9,10,11]} | 3 | 0 | 0 | 成功 | D0068:9, D0068:10, D0068:11 |
| 4 | 2 | read_chunks {"doc_id":"D0089","ordinals":[2,3]} | 2 | 0 | 0 | 成功 | D0089:2, D0089:3 |
| 5 | 3 | search_chunks {"doc_ids":["D0089"],"query":"theme content latent disentangle static dynamic background object control AdaIN","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0089:15, D0089:16, D0089:17, D0089:87, D0089:7, D0089:85, D0089:21, D0089:29, D0089:30, D0089:24, D0089:0, D0089:8 |
| 6 | 3 | search_chunks {"doc_ids":["D0068"],"query":"temporal cycle loss static dynamic disentangle swapping background dynamic objects","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0068:11, D0068:15, D0068:0, D0068:14, D0068:40, D0068:10, D0068:41, D0068:13, D0068:25, D0068:4, D0068:39, D0068:8 |

judge reasoning：

> The generated answer accurately details GameGAN and DriveGAN but omits Meta-Sim entirely, so it is missing a key component of the gold answer.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> GameGAN explicitly separates static and dynamic elements through a specialized rendering engine and memory module, using temporal cycle loss to encourage disentanglement. DriveGAN takes a more implicit approach by using hierarchical latent spaces where the global latent captures static properties like time of day, while dynamic elements are encoded in the spatial latents. Meta-Sim focuses on disentangling scene attributes that can be modified from fixed structural elements defined by the scene grammar.

**naive 最终答案**

> Based on the context, the key differences are:
> 
> - **DriveGAN**: disentangles static/dynamic in latent space — the encoder produces separate "theme" and "content" latent codes (theme = appearance independent of pixel location, e.g., background color/weather; content = spatial content), and the dynamics engine further disentangles action-dependent vs. action-independent content. Static aspects (theme) can be swapped/sampled without supervision.
> 
> - **GameGAN**: achieves disentanglement architecturally via an external memory module (NTM-style) that stores static elements (walls, background) for long-term consistency, plus a specialized rendering engine that takes K=2 inputs (memory vector and hidden state) and produces object/attribute maps, trained with a temporal cycle loss that forces static elements into memory and keeps dynamic elements (ghosts, food, NPCs) in the hidden state. This enables background/foreground swapping.
> 
> - **Large stochastic RNNs (SVG-based)**: take the opposite approach — they argue handcrafted disentanglement (foreground/background separation, optical flow, segmentation masks) is unnecessary, and instead use minimal inductive bias with maximal network capacity, letting scale alone handle scene dynamics.
> 
> - **NeRF-style dynamic-scene works (D-NeRF, DeRF, Nerfies)** are mentioned as approaches for dynamic scenes (e.g., decomposed radiance fields), but the context gives no detailed mechanism for their static/dynamic separation.

**community 最终答案**

> Based on the collection, the two relevant neural simulators take clearly different approaches:
> 
> **GameGAN (D0068)** — disentangles in the *pixel/rendering space*:
> - Uses an **external memory module** (NTM-style) plus a specialized **rendering engine** and a **temporal cycle loss** to separate static elements (walls, background) from dynamic ones (ghosts, food, fireballs).
> - The rendering engine takes two vectors — the retrieved memory (static content) and the hidden state (dynamic content) — and produces per-type object maps, attribute maps, softmax masks and SPADE layers, compositing the final image as a sum of components.
> - Static content is stored in memory for long-term consistency, enabling component swapping (e.g., replacing background/foreground).
> 
> **DriveGAN (D0089)** — disentangles in the *latent space*:
> - A VAE-GAN with a StyleGAN decoder separates **theme vs. content** latents (theme, e.g., weather, injected via AdaIN; content encodes spatial layout).
> - The dynamics engine further splits content into **action-dependent** features (scene layout) and **action-independent** features (object types) using two separate LSTMs (ConvLSTM + LSTM).
> - No memory module; separation happens in the latent codes rather than through a multi-mask rendering engine.
> 
> In short: GameGAN separates static/dynamic via memory + masked rendering + cycle loss at the image level, while DriveGAN separates them via latent disentanglement (theme/content and action-dependent/independent features).

</details>

<a id="case-mdaqa-29"></a>

### mdaqa:29 — 评分与执行路径对照

**问题：** How can we quantify and control the amount of distribution shift in evaluating machine learning models?

**score：2→2（Δ+0）；rounds：3→2（Δ-1）。**

工具安排：naive 为第1轮1次、第2轮2次；community 为第1轮2次。最终回答另占一轮。

轮次减少 1，工具总数 3→2、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 20→18、文档 overview 8→44；工具结果字符数 71,451→108,026，QA token 34,379→31,223。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/cb9acc4ce7d747f3ba58dfb7001b6614.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/3744d1610a8f424e9aa4de2aef4734a2.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"quantify and control amount of distribution shift in evaluating machine learning models","search_mode":"hybrid","doc_ids":null} | 12 | 8 | 0 | 成功 | D0142:0, D0110:24, D0014:0, D0107:0, D0107:4, D0142:23, D0107:18, D0096:2, D0107:2, D0055:1, D0092:0, D0022:15 |
| 2 | 2 | search_chunks {"doc_ids":["D0107"],"query":"distance score amount of distribution shift between subsets","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0107:6, D0107:8, D0107:4, D0107:11, D0107:10, D0107:0, D0107:18, D0107:3, D0107:13, D0107:7, D0107:2, D0107:5 |
| 3 | 2 | read_chunks {"doc_id":"D0107","ordinals":[5,6,7,8]} | 4 | 0 | 0 | 成功 | D0107:5, D0107:6, D0107:7, D0107:8 |

judge reasoning：

> The generated answer accurately and thoroughly describes the MetaShift graph-based method for quantifying and controlling distribution shift, but omits the other two important quantification methods (planner-based metrics and explicit annotations) listed in the gold answer, making it incomplete.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"quantify and control distribution shift in evaluating machine learning models","search_mode":"hybrid","doc_ids":null} | 12 | 31 | 4 | 成功 | D0110:24, D0142:0, D0014:0, D0142:23, D0110:22, D0107:3, D0107:0, D0107:4, D0092:0, D0096:2, D0107:18, D0076:21 |
| 2 | 1 | search_chunks {"query":"distribution shift metric quantification evaluation","search_mode":"vector","doc_ids":null} | 12 | 13 | 2 | 成功 | D0107:0, D0107:4, D0107:18, D0092:0, D0107:2, D0093:22, D0093:0, D0107:21, D0107:3, D0107:12, D0107:13, D0014:0 |

judge reasoning：

> The generated answer correctly captures MetaShift's distance metric and control mechanism, but omits the other two key methods from the gold answer (planner-based metrics and explicit annotations), making it incomplete.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Distribution shift can be quantified through: 1) Graph-based distance metrics between data subsets as in MetaShift, 2) Planner-based metrics that measure impact on downstream tasks, 3) Explicit annotations of what drives the shift (e.g. context changes). This enables systematic evaluation under controlled amounts of shift.

**naive 最终答案**

> Based on the MetaShift framework:
> 
> **Quantifying shift:** Build a meta-graph whose nodes are data subsets (each defined by a context/metadata tag) and edge weights are the overlap coefficient between subsets. Compute spectral embeddings of the graph nodes and use the **Euclidean distance between embeddings** as a distance score that measures the amount of distribution shift between any two datasets (capturing broader similarities than raw overlap).
> 
> **Controlling shift:** MetaShift allows benchmarking both (1) domain generalization and (2) subpopulation shifts in a well-annotated and well-controlled way:
> - **Domain generalization:** sample distinct subset collections as train vs. test domains; adjust shift magnitude by fixing the test domain and changing the training domain to different distances (e.g., d = 0.44 to 1.43).
> - **Subpopulation shift:** sample train and test from the same subsets but with different mixture weights; adjust magnitude by changing training mixture weights while keeping the test set unchanged.
> 
> This enables studying model behavior under carefully modulated amounts of distribution shift (e.g., ERM performs best for moderate shifts; no method wins for large shifts).

**community 最终答案**

> Based on the context, distribution shift can be quantified and controlled via MetaShift: it provides a **distance score that measures the amount of distribution shift between any two datasets** (quantify), and allows **adjusting the magnitude of the shift by sampling different training subsets while keeping the test set unchanged** (control). Separately, Adaptive Conformal Inference models distribution shift as a learning problem in a single time-varying parameter that is continuously re-estimated to maintain coverage.

</details>

<a id="case-mdaqa-31"></a>

### mdaqa:31 — 评分与执行路径对照

**问题：** What role do distribution alignment metrics play in evaluating synthetic data quality?

**score：2→3（Δ+1）；rounds：3→2（Δ-1）。**

工具安排：naive 为第1轮2次、第2轮2次；community 为第1轮1次。最终回答另占一轮。

轮次减少 1，工具总数 4→1、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 40→12、文档 overview 15→47；工具结果字符数 124,653→86,406，QA token 58,085→23,449。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

<details>
<summary>展开 judge 所提实体的字面证据核对</summary>

| 实体/术语 | naive工具中首次匹配 | naive答案 | community工具中首次匹配 | community答案 |
|---|---|---|---|---|
| Meta-Sim | 轮1/调用1/D0030:0 | 未匹配 | 轮1/调用1/D0030:0 | 出现 |
| MMD | 轮1/调用1/D0030/overview | 出现 | 轮1/调用1/D0030/overview | 出现 |

这里只检查指定字面串及字母数字边界，不评判上下文是否在讨论同一事实；未匹配不排除同义表述，出现也不代表正确采用。它用于区分“可能未召回”和“已出现但未展开”的复核入口，不能自动判定因果。

</details>

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/7040ae847a2a44b7a5d5536a1638b92a.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/2136cb87266047b8a6ce4aefa27e82e0.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"distribution alignment metrics evaluating synthetic data quality","search_mode":"hybrid","doc_ids":null} | 12 | 10 | 0 | 成功 | D0030:0, D0132:12, D0132:13, D0078:1, D0107:0, D0078:0, D0093:0, D0032:0, D0067:13, D0092:0, D0126:5, D0076:0 |
| 2 | 1 | search_chunks {"query":"distribution alignment synthetic data evaluation metric","search_mode":"vector","doc_ids":null} | 12 | 1 | 0 | 成功 | D0107:0, D0093:0, D0107:4, D0093:26, D0093:2, D0093:23, D0093:22, D0107:18, D0092:0, D0107:2, D0065:7, D0093:13 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"metric measuring quality of generated samples distribution similarity synthetic data Mauve FID","search_mode":"hybrid"} | 12 | 4 | 0 | 成功 | D0132:13, D0132:12, D0030:0, D0138:3, D0048:8, D0132:26, D0138:12, D0069:0, D0133:29, D0138:15, D0107:0, D0138:19 |
| 4 | 2 | search_chunks {"doc_ids":["D0030"],"query":"MMD distribution matching loss minimize distribution gap evaluation quality","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0030:9, D0030:8, D0030:0, D0030:12, D0030:10, D0030:2, D0030:23, D0030:3, D0030:1, D0030:28, D0030:11, D0030:22 |

judge reasoning：

> The generated answer correctly describes the general role of distribution alignment metrics, but it omits key specifics from the gold answer, such as Meta-Sim's use of MMD/feature variance gap and PersonX's validation via performance correlation.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"distribution alignment metrics evaluating synthetic data quality","search_mode":"hybrid","doc_ids":null} | 12 | 47 | 6 | 成功 | D0030:0, D0132:12, D0132:13, D0078:1, D0107:0, D0078:0, D0093:0, D0032:0, D0067:13, D0092:0, D0126:5, D0076:0 |

judge reasoning：

> The generated answer correctly explains the role of distribution alignment metrics and accurately cites Meta-Sim's MMD loss, but it omits the feature variance gap and PersonX validation mentioned in the gold answer, making it a solid but incomplete match.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Meta-Sim uses MMD distance and feature variance gap to measure and optimize the distribution alignment between synthetic and real data, while PersonX validates alignment through empirical performance correlation between synthetic and real datasets on standard re-ID models.

**naive 最终答案**

> Based on the context, distribution alignment metrics play a direct role in evaluating synthetic data quality by measuring the similarity between the distribution of generated (synthetic) data and the distribution of real/target data.
> 
> Specifically, from the context:
> - MMD (Maximum Mean Discrepancy) is used as a metric of the similarity of two distributions, comparing the rendered synthetic outputs against real imagery (e.g., Kernel Inception Distance in InceptionV3 feature space).
> - Mauve score is used to compute the similarity of the distributions of the training data and the generated (synthetic) data, serving as a metric measuring the quality of generated samples (higher scores indicate better quality).
> - FID/FVD similarly compare the distribution of features extracted from generated vs. ground-truth/real samples to measure sample quality/realism.
> 
> These metrics are used to quantify how closely synthetic data matches the real-data distribution, thereby assessing the fidelity/quality of the generated data (and can also be used as training objectives to reduce the distribution gap).

**community 最终答案**

> Distribution alignment metrics evaluate synthetic data quality by measuring how closely the synthetic/generated distribution matches the real or target distribution. For example, Meta-Sim uses an MMD (maximum mean discrepancy) distribution-matching loss to minimize the distribution gap between synthetic rendered outputs and real target data, improving content quality; likewise, the DP synthetic text paper uses the Mauve score to compute the similarity between the training data distribution and the generated data as a quality metric, with higher scores indicating higher generated-text quality.

</details>

<a id="case-mdaqa-32"></a>

### mdaqa:32 — 评分与执行路径对照

**问题：** How do the papers differ in their approach to controlling environmental factors in synthetic data?

**score：4→4（Δ+0）；rounds：4→3（Δ-1）。**

工具安排：naive 为第1轮2次、第2轮3次、第3轮3次；community 为第1轮2次、第2轮2次。最终回答另占一轮。

轮次减少 1，工具总数 8→4、错误 3→0，整轮全部工具报错的轮数 1→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 26→31、文档 overview 11→68；工具结果字符数 84,499→170,254，QA token 66,718→81,252。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/17234b940e5d40cca99e312567709690.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/8ad781f23c0d4e79aa550093204d5977.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"controlling environmental factors in synthetic data","search_mode":"hybrid","doc_ids":null} | 12 | 8 | 0 | 成功 | D0022:3, D0076:0, D0030:0, D0142:32, D0132:17, D0089:0, D0022:5, D0093:13, D0022:9, D0030:3, D0017:2, D0076:5 |
| 2 | 1 | search_chunks {"query":"environmental factors synthetic data generation control","search_mode":"vector","doc_ids":null} | 12 | 3 | 0 | 成功 | D0089:0, D0089:10, D0068:23, D0061:18, D0089:73, D0030:1, D0030:3, D0076:0, D0004:11, D0068:21, D0089:8, D0030:30 |
| 3 | 2 | read_chunks {"raw":"{\"doc_id\": \"D0022\", \"ordinals\": 5, 6, 7, 8}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | — |
| 4 | 2 | read_chunks {"raw":"{\"doc_id\": \"D0030\", \"ordinals\": 1, 2, 4}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | — |
| 5 | 2 | read_chunks {"raw":"{\"doc_id\": \"D0089\", \"ordinals\": 8, 9, 10}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | — |
| 6 | 3 | read_chunks {"doc_id":"D0022","ordinals":[5,6,7]} | 3 | 0 | 0 | 成功 | D0022:5, D0022:6, D0022:7 |
| 7 | 3 | read_chunks {"doc_id":"D0089","ordinals":[8,9]} | 2 | 0 | 0 | 成功 | D0089:8, D0089:9 |
| 8 | 3 | read_chunks {"doc_id":"D0030","ordinals":[3,4,5]} | 3 | 0 | 0 | 成功 | D0030:3, D0030:4, D0030:5 |

judge reasoning：

> The generated answer accurately captures the core distinction between Meta-Sim (learned optimization of scene attributes) and PersonX (explicit manual control), and the additional DriveGAN context does not contradict the gold answer.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"controlling environmental factors synthetic data","search_mode":"hybrid","doc_ids":null} | 12 | 37 | 5 | 成功 | D0022:3, D0076:0, D0142:32, D0030:0, D0089:0, D0022:5, D0089:10, D0022:9, D0030:3, D0076:5, D0093:13, D0126:5 |
| 2 | 1 | search_chunks {"query":"synthetic data environment factors controlled","search_mode":"vector","doc_ids":null} | 12 | 20 | 3 | 成功 | D0089:0, D0089:10, D0022:3, D0089:35, D0030:3, D0089:11, D0022:4, D0030:1, D0028:14, D0089:1, D0089:67, D0089:45 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"synthetic data generated environment parameters control illumination weather","search_mode":"keyword"} | 12 | 11 | 2 | 成功 | D0089:0, D0022:3, D0089:8, D0132:12, D0105:2, D0030:3, D0030:17, D0030:18, D0142:32, D0105:0, D0132:13, D0089:49 |
| 4 | 2 | read_chunks {"doc_id":"D0030","ordinals":[5,6,7]} | 3 | 0 | 0 | 成功 | D0030:5, D0030:6, D0030:7 |

judge reasoning：

> The generated answer accurately captures the core distinction between Meta-Sim's automatic optimization and PersonX's explicit manual control, matching the gold answer, and the additional mention of DriveGAN is consistent and does not contradict.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Meta-Sim learns to automatically modify scene attributes through optimization, while PersonX provides explicit manual control over factors like viewpoint, illumination and background to enable controlled experiments analyzing their individual impacts.

**naive 最终答案**

> The papers differ as follows:
> 
> - **PersonX (D0022)**: Controls environmental factors (illumination, cameras, backgrounds, viewpoints) by directly editing the simulator's parameters in a hand-crafted engine, and isolates each factor's influence through carefully designed control/experimental groups and subsets (e.g., pure-color backgrounds to eliminate background influence).
> 
> - **Meta-Sim (D0030)**: Instead of manual control, it *learns* to control scene attributes — a neural network (distribution transformer) modifies scene-graph attributes (object locations, poses, colors, etc.) to match the real-data distribution and downstream task performance, optimizing low-level per-object parameters.
> 
> - **DriveGAN (D0089)**: Achieves control without supervision by disentangling latent components (theme vs. content) in a learned neural simulator, allowing users to control environment aspects such as weather and object locations through these disentangled latent codes.
> 
> In short: PersonX relies on precise manual/engine-level control, Meta-Sim learns to optimize scene parameters toward real distributions and task performance, and DriveGAN learns disentangled latent controls unsupervisedly.

**community 最终答案**

> The papers differ mainly in how environmental factors are controlled in synthetic data:
> 
> 1. **PersonX (D0022)** — manual/precise engine control. Environmental factors (illumination, camera, background, viewpoint) are editable parameters in a Unity-based engine, explicitly manipulated (e.g., viewpoints from 0°–360°, control vs. experimental groups) to quantitatively dissect how factors like viewpoint affect a re-ID system.
> 
> 2. **Meta-Sim (D0030)** — learned/optimized control. A neural network (Distribution Transformer, a GCN) automatically edits mutable scene-graph attributes (object locations, poses, colors, asset IDs) to minimize the distribution gap with real data and optimize downstream task performance, rather than hand-setting environmental parameters.
> 
> 3. **DriveGAN (D0089)** — unsupervised data-driven control. It achieves controllability by learning disentangled latent components (theme/content) without supervision; environmental factors like weather, background color, and object placement are changed by sampling/swapping latent codes in a neural simulator, not by editing explicit parameters.
> 
> In short: PersonX hand-crafts and precisely edits engine parameters; Meta-Sim learns to optimize scene attributes; DriveGAN learns control implicitly through disentangled latent representations.

</details>

<a id="case-mdaqa-33"></a>

### mdaqa:33 — 最大降分主要暴露比较口径与 judge 一致性

**问题：** How does the communication cost per iteration differ between distributed Newton-type methods when handling Byzantine failures versus normal operations?

**score：4→0（Δ-4）；rounds：2→3（Δ+1）。**

两份答案开头都说 COMRADE 在有/无 Byzantine 时均一轮，后面也都明确 GIANT/DINGO 两轮。naive 判 4，community 判 0；判 0 的 reasoning 只抓住“no difference”而忽略末句对 GIANT/DINGO 的对照。两份回答的核心结构相近，问题本身又可解读为“同一方法在故障/正常状态”或“不同方法之间”，不能把四分落差解释为社区召回失效。community 还多做一轮定向搜索和原文读取，token 19,135→54,834，却未澄清比较对象。先复核题意及盲化评分，再评价这种最大分差。

工具安排：naive 为第1轮2次；community 为第1轮2次、第2轮2次。最终回答另占一轮。

轮次增加 1，工具总数 2→4、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 18→25、文档 overview 2→13；工具结果字符数 53,880→100,825，QA token 19,135→54,834。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

<details>
<summary>展开 judge 所提实体的字面证据核对</summary>

| 实体/术语 | naive工具中首次匹配 | naive答案 | community工具中首次匹配 | community答案 |
|---|---|---|---|---|
| COMRADE | 轮1/调用1/D0074/overview | 出现 | 轮1/调用1/D0074/overview | 出现 |
| GIANT | 轮1/调用1/D0074:0 | 出现 | 轮1/调用1/D0074:0 | 出现 |
| DINGO | 轮1/调用1/D0024:0 | 出现 | 轮1/调用1/D0024:0 | 出现 |

这里只检查指定字面串及字母数字边界，不评判上下文是否在讨论同一事实；未匹配不排除同义表述，出现也不代表正确采用。它用于区分“可能未召回”和“已出现但未展开”的复核入口，不能自动判定因果。

</details>

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/02e71ad0705641a18c4f09ee9efd07a3.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/12b82501832043a0a2bec1d206aebe49.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"communication cost per iteration distributed Newton Byzantine","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0074:0, D0074:20, D0024:0, D0024:44, D0024:38, D0024:6, D0024:39, D0024:4, D0074:5, D0024:5, D0074:2, D0074:7 |
| 2 | 1 | search_chunks {"query":"Byzantine failure Newton method communication per iteration","search_mode":"vector","doc_ids":null} | 12 | 0 | 0 | 成功 | D0074:0, D0074:7, D0074:2, D0074:20, D0074:3, D0074:5, D0074:19, D0074:1, D0024:0, D0074:4, D0074:8, D0074:12 |

judge reasoning：

> The generated answer correctly captures the key difference—normal distributed Newton methods (GIANT/DINGO) require two communication rounds per iteration, while Byzantine-resistant versions like COMRADE require only one round using norm-based thresholding—so it fully matches the Gold Answer.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"communication cost per iteration distributed Newton method Byzantine","search_mode":"hybrid","doc_ids":null} | 12 | 13 | 2 | 成功 | D0074:0, D0024:44, D0024:0, D0024:4, D0074:20, D0024:5, D0024:38, D0024:6, D0074:5, D0024:39, D0024:2, D0074:2 |
| 2 | 1 | search_chunks {"query":"communication cost per iteration Byzantine fault tolerance Newton-type","search_mode":"vector","doc_ids":null} | 12 | 0 | 0 | 成功 | D0074:0, D0074:2, D0074:20, D0074:7, D0024:0, D0074:5, D0074:3, D0074:19, D0074:1, D0024:44, D0074:4, D0024:4 |
| 3 | 2 | search_chunks {"doc_ids":["D0074"],"query":"Byzantine communication cost per iteration one round thresholding","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0074:0, D0074:5, D0074:7, D0074:17, D0074:20, D0074:2, D0074:21, D0074:11, D0074:19, D0074:12, D0074:3, D0074:18 |
| 4 | 2 | read_chunks {"doc_id":"D0074","ordinals":[7,8,9,10]} | 4 | 0 | 0 | 成功 | D0074:7, D0074:8, D0074:9, D0074:10 |

judge reasoning：

> The generated answer directly contradicts the gold answer by claiming there is no difference in communication cost and that normal operations use one round per iteration, whereas the gold standard states normal operations require two rounds and Byzantine-resistant methods reduce to one.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> In normal operations, distributed Newton methods require two communication rounds per iteration for sequential estimation of gradients and Hessians, while Byzantine-resistant versions can reduce this to one round by showing sequential estimation is redundant and using norm-based thresholding for Byzantine detection.

**naive 最终答案**

> Based on the context (COMRADE), the per-iteration communication cost is the **same** whether Byzantine failures are present or not. In both cases each worker communicates **only once per iteration**, sending a d-dimensional vector (the local Hessian-inverse-gradient product), giving O(d) communication per iteration.
> 
> Byzantine robustness is handled **at the center machine** via a simple norm-based thresholding rule that discards the β-fraction of workers with the largest update norms—this aggregation step adds no extra communication rounds. This contrasts with normal operations of state-of-the-art methods like GIANT and DINGO, which send gradient and Hessian information sequentially and thus communicate **twice per iteration**.

**community 最终答案**

> Based on the COMRADE paper (D0074), there is **no difference** in per-iteration communication cost between Byzantine-handling and normal operation. In both cases workers communicate **only once per iteration**, sending a d-dimensional vector (the local Hessian-inverse × gradient product), giving **O(d) communication per iteration**. Byzantine robustness is handled entirely at the center machine via norm-based thresholding (trimming the β>α fraction of workers with largest update norms), which adds no extra communication rounds or cost — it only slightly worsens the linear rate and error floor by a constant factor. This is in contrast to methods like GIANT and DINGO, which communicate twice per iteration (O(d) more) but do not address Byzantine failures.

</details>

<a id="case-mdaqa-34"></a>

### mdaqa:34 — 评分与执行路径对照

**问题：** What are the key differences in handling client heterogeneity between clustered federated learning and distributed Newton methods?

**score：4→2（Δ-2）；rounds：3→3（Δ+0）。**

工具安排：naive 为第1轮2次、第2轮2次；community 为第1轮2次、第2轮2次。最终回答另占一轮。

两边均为 3 轮，但工具总数 4→4，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 29→26、文档 overview 4→19；工具结果字符数 118,063→115,690，QA token 52,438→56,980。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/c6f81285e16a4dbd9eab324ed898b5c3.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/68055c6b24c946fba0a3c626cc8fcb85.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"client heterogeneity clustered federated learning","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0071:0, D0071:1, D0071:2, D0071:3, D0071:50, D0071:53, D0071:4, D0071:52, D0071:54, D0071:7, D0071:51, D0074:1 |
| 2 | 1 | search_chunks {"query":"distributed Newton method heterogeneity","search_mode":"hybrid","doc_ids":null} | 12 | 1 | 0 | 成功 | D0024:0, D0024:4, D0024:44, D0071:1, D0074:0, D0074:20, D0024:5, D0024:43, D0071:54, D0071:50, D0071:51, D0074:2 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"data distribution arbitrary heterogeneity workers same objective global model","search_mode":"hybrid"} | 12 | 1 | 0 | 成功 | D0071:1, D0071:24, D0071:25, D0024:0, D0071:22, D0074:6, D0024:40, D0071:0, D0074:1, D0032:14, D0074:0, D0024:6 |
| 4 | 2 | search_chunks {"doc_ids":null,"query":"clustered federated learning versus global model non-iid single model","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0071:0, D0071:4, D0071:2, D0071:3, D0071:1, D0071:54, D0071:53, D0071:55, D0071:52, D0071:24, D0071:26, D0071:25 |

judge reasoning：

> The generated answer correctly captures the key distinction: clustered federated learning explicitly models heterogeneity via clustering, while distributed Newton methods do not cluster but implicitly handle arbitrary data distributions through second-order optimization without explicit modeling.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"client heterogeneity clustered federated learning","search_mode":"hybrid","doc_ids":null} | 12 | 19 | 3 | 成功 | D0071:0, D0071:1, D0071:2, D0071:3, D0071:50, D0071:53, D0071:4, D0071:52, D0071:54, D0071:7, D0071:51, D0074:1 |
| 2 | 1 | search_chunks {"query":"distributed Newton method client heterogeneity","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0024:0, D0024:44, D0071:1, D0024:4, D0074:0, D0074:20, D0024:5, D0024:43, D0071:54, D0071:50, D0071:51, D0071:2 |
| 3 | 2 | read_chunks {"doc_id":"D0074","ordinals":[1,2,3]} | 3 | 0 | 0 | 成功 | D0074:1, D0074:2, D0074:3 |
| 4 | 2 | search_chunks {"query":"data heterogeneity non-iid local functions distributed Newton Byzantine arbitrary data distribution","search_mode":"hybrid","doc_ids":["D0074","D0024"]} | 12 | 0 | 0 | 成功 | D0074:0, D0024:0, D0024:5, D0024:4, D0074:2, D0074:8, D0074:4, D0074:20, D0024:6, D0074:1, D0074:6, D0074:5 |

judge reasoning：

> The generated answer correctly identifies that clustered FL explicitly clusters clients while Newton methods do not, but it omits the key mechanism of implicit heterogeneity handling via second-order optimization and adaptive step sizes, and instead introduces a Byzantine robustness focus that is not in the gold answer.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Clustered federated learning explicitly models client heterogeneity by grouping clients with similar data distributions, while distributed Newton methods handle heterogeneity implicitly through second-order optimization and adaptive step sizes without explicit clustering.

**naive 最终答案**

> **Clustered federated learning (e.g., IFCA)** treats client heterogeneity (non-i.i.d. data) as the central modeling problem: users are partitioned into clusters with different objectives, and the algorithm alternately estimates unknown cluster identities and trains a separate (personalized) model per cluster, yielding personalized predictions.
> 
> **Distributed Newton methods (e.g., DINGO, COMRADE)** instead optimize a single shared global objective across all workers. They handle heterogeneity merely by allowing arbitrary data distributions across workers (DINGO permits any data split, even |S_i| < d) without modeling or exploiting it—no cluster structure is identified, and one global model is learned. They focus on communication efficiency and (in COMRADE) Byzantine robustness via second-order updates rather than personalization.

**community 最终答案**

> Based on the context:
> 
> **Clustered Federated Learning (IFCA, D0071):** Treats client heterogeneity (non-i.i.d. data) as a structural feature to exploit. Users are assumed to be partitioned into clusters with different learning tasks/objectives; since cluster identities are unknown, IFCA alternately estimates cluster membership and optimizes a separate personalized model per cluster via gradient descent. Heterogeneity is leveraged to provide personalized predictions.
> 
> **Distributed Newton methods (COMRADE, D0074; DINGO, D0024):** Do not model heterogeneity as clusters. They assume a single global objective (sum of local functions) that all workers optimize together, with data partitioned across workers (COMRADE assumes homogeneous partitioning; DINGO allows arbitrary distribution but still learns one global model). The main "heterogeneity" concern is not data distribution but Byzantine/adversarial workers — COMRADE handles it with a norm-based thresholding/trimming rule that filters out workers with the largest update norms, yielding an O(1/√s) statistical error floor.
> 
> **Key difference:** Clustered FL leverages heterogeneity by splitting users into clusters and learning distinct cluster-specific models, whereas distributed Newton methods learn a single shared model over arbitrarily/homogeneously distributed data and address worker heterogeneity only in the form of Byzantine robustness.

</details>

<a id="case-mdaqa-35"></a>

### mdaqa:35 — 评分与执行路径对照

**问题：** How do the compression ratios and accuracy trade-offs compare between sentence-level and word-level binary embedding approaches?

**score：2→3（Δ+1）；rounds：2→2（Δ+0）。**

工具安排：naive 为第1轮2次；community 为第1轮2次。最终回答另占一轮。

两边均为 2 轮，但工具总数 2→2，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 18→19、文档 overview 6→29；工具结果字符数 62,532→92,217，QA token 20,181→26,711。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/8f60f14d350943329426d1f59557c831.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/f363942d21e641b8a551027fa473ff58.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"compression ratio accuracy trade-off sentence-level word-level binary embedding","search_mode":"hybrid","doc_ids":null} | 12 | 5 | 0 | 成功 | D0042:3, D0042:41, D0010:15, D0010:18, D0010:11, D0004:9, D0010:22, D0042:0, D0010:1, D0065:9, D0098:17, D0010:0 |
| 2 | 1 | search_chunks {"query":"binary embedding compression sentence word level","search_mode":"vector","doc_ids":null} | 12 | 1 | 0 | 成功 | D0010:22, D0042:0, D0042:44, D0010:0, D0010:1, D0010:20, D0010:3, D0042:3, D0010:18, D0062:22, D0010:10, D0010:4 |

judge reasoning：

> The generated answer captures the general idea of high compression with minimal accuracy loss, but it incorrectly states sentence-level compression as >50x (over 98% reduction) instead of the gold's 37.5x, and it also introduces word-level compression variations that conflict with the gold's uniform 37.5x claim.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"sentence-level word-level binary embedding compression ratio accuracy trade-off","search_mode":"hybrid","doc_ids":null} | 12 | 29 | 4 | 成功 | D0042:3, D0042:41, D0010:18, D0042:4, D0010:15, D0004:9, D0042:0, D0010:0, D0010:22, D0065:9, D0010:1, D0098:17 |
| 2 | 1 | search_chunks {"query":"binary embedding compression ratio accuracy trade-offs sentence word level","search_mode":"vector","doc_ids":null} | 12 | 0 | 0 | 成功 | D0042:0, D0010:0, D0010:1, D0010:22, D0010:20, D0010:3, D0042:44, D0042:47, D0062:22, D0062:24, D0042:3, D0062:0 |

judge reasoning：

> The generated answer correctly captures the main point that both binary embedding approaches achieve similar high compression with ~2% accuracy loss, but it slightly misstates the sentence-level compression ratio (>98% instead of 37.5x) and generalizes word-level accuracy, so it is good but not perfect.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Sentence-level binarization achieves 37.5x compression with only 2% accuracy drop using 256-bit vectors, while word-level binarization achieves similar compression ratios (37.5x) with binary codes and shows minimal performance loss (0.4-2.5%) on downstream tasks. Both approaches demonstrate that binary representations can effectively preserve semantic information while dramatically reducing storage requirements.

**naive 最终答案**

> **Word-level binarization** (D0010): binary vectors use ~37.5× less memory than original real-valued vectors (e.g., 256-bit GloVe vs. 9600-bit original; 64-bit dict2vec reaches a 150× compression rate), with only ~0.4%–2.5% accuracy drop for 256-bit GloVe and ~2% overall on several NLP tasks. Larger datasets (e.g., Yahoo, Amazon) incur bigger losses (~11–16%) when very small (64-bit) codes are used.
> 
> **Sentence-level binarization** (D0042): binary sentence embeddings reduce storage by over 98% (i.e., >50× compression) while degrading downstream performance by only about 2% relative to the continuous counterparts, and Hamming-distance retrieval is competitive with cosine similarity.
> 
> In short, both approaches trade roughly ~2% accuracy for large compression (~37.5× at word level, >98% memory reduction at sentence level), with word-level compression ratios varying more strongly by bit size and dataset size, while sentence-level compression stays around 98%+ with a consistent ~2% degradation.

**community 最终答案**

> Both approaches achieve a similar, near-lossless accuracy trade-off, with slightly different compression ratios:
> 
> - **Word-level** (autoencoder binarization of word embeddings): reduces vector size by ~97% (binary vectors 37.5× smaller, e.g., 256-bit vs 9600-bit GloVe), with only ~2% accuracy loss on similarity, analogy, classification, and sentiment tasks, plus ~30× faster top-k queries. Higher compression (e.g., 64-bit, compression rate 150) increases accuracy loss, especially on larger datasets.
> 
> - **Sentence-level** (binarization of continuous sentence embeddings): reduces storage requirement by over 98%, also degrading downstream performance by only ~2% relative to continuous counterparts. Hamming-distance retrieval over binary codes is competitive with (or superior to) cosine similarity on continuous embeddings and is much faster.
> 
> In short, both sacrifice only ~2% accuracy; sentence-level binarization yields slightly higher memory savings (>98% vs ~97%), while word-level reports larger speedups (~30× vs ~12× for sentence retrieval).

</details>

<a id="case-mdaqa-36"></a>

### mdaqa:36 — 扩展到大半语料仍未消解模糊对照对象

**问题：** What are the key differences in how plug-and-play architectures handle computational efficiency for real-time vs non-real-time applications?

**score：1→0（Δ-1）；rounds：5→8（Δ+3）。**

naive 5 轮、community 8 轮；community 已给出 124/143 篇文档 overview，15 次工具且无错误，仍称无法从材料建立实时/非实时 plug-and-play 比较，1→0 分。trace 中反复改写通用 latency/efficiency/plug-and-play 查询，没有稳定定位 gold 的 residual adapters 与 O(L log L) 对照。这里不是单纯社区数量不够；应先解决实体/方法指代与无进展循环。仅增加召回规模会进一步增加上下文和成本。

工具安排：naive 为第1轮2次、第2轮2次、第3轮2次、第4轮2次；community 为第1轮2次、第2轮2次、第3轮2次、第4轮2次、第5轮2次、第6轮3次、第7轮2次。最终回答另占一轮。

轮次增加 3，工具总数 8→15、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 57→108、文档 overview 29→124；工具结果字符数 234,371→528,975，QA token 180,638→662,221。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/92a384a02157442db212f4f133760569.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/2996c52a552a43a1bd87f2d90ebb9731.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"plug-and-play architecture computational efficiency real-time non-real-time","search_mode":"hybrid","doc_ids":null} | 12 | 8 | 0 | 成功 | D0072:22, D0010:1, D0061:18, D0010:16, D0002:1, D0098:2, D0055:5, D0098:0, D0034:12, D0098:1, D0098:5, D0110:3 |
| 2 | 1 | search_chunks {"query":"plug and play real-time vs non-real-time applications latency throughput","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0061:1, D0010:1, D0089:69, D0061:18, D0002:1, D0048:20, D0055:5, D0089:65, D0010:4, D0097:0, D0086:18, D0098:0 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"plug-and-play architecture computational efficiency real-time applications","search_mode":"keyword"} | 12 | 2 | 0 | 成功 | D0010:1, D0086:18, D0055:5, D0002:1, D0110:3, D0072:22, D0110:11, D0071:0, D0110:4, D0037:1, D0110:0, D0071:1 |
| 4 | 2 | search_chunks {"doc_ids":null,"query":"plug-and-play module latency real-time inference non-real-time","search_mode":"vector"} | 12 | 4 | 0 | 成功 | D0098:0, D0098:2, D0098:14, D0098:16, D0058:7, D0097:0, D0058:13, D0124:2, D0133:0, D0051:0, D0098:5, D0098:1 |
| 5 | 3 | search_chunks {"doc_ids":null,"query":"plug-and-play real-time applications efficiency trade-off non-real-time","search_mode":"hybrid"} | 12 | 7 | 0 | 成功 | D0010:1, D0095:3, D0002:1, D0038:0, D0007:0, D0111:26, D0110:4, D0113:34, D0098:2, D0128:17, D0003:48, D0055:5 |
| 6 | 3 | search_chunks {"doc_ids":null,"query":"plug-in module training only removed at inference no computational overhead deployment","search_mode":"hybrid"} | 12 | 2 | 0 | 成功 | D0058:13, D0058:20, D0058:3, D0097:0, D0097:9, D0058:12, D0097:4, D0097:2, D0133:1, D0062:1, D0075:29, D0111:15 |
| 7 | 4 | search_chunks {"doc_ids":null,"query":"real-time applications require lower latency non-real-time applications can afford heavier computation","search_mode":"vector"} | 12 | 2 | 0 | 成功 | D0062:20, D0099:12, D0098:0, D0128:18, D0098:2, D0062:1, D0099:23, D0010:17, D0074:1, D0128:1, D0010:1, D0037:19 |
| 8 | 4 | read_chunks {"doc_id":"D0058","ordinals":[3,20]} | 2 | 0 | 0 | 成功 | D0058:3, D0058:20 |

judge reasoning：

> The generated answer explicitly states it cannot answer the question and does not provide any of the key differences from the gold answer, such as per-token inference speed with residual adapters for real-time versus reducing O(L^2) to O(L log L) for non-real-time, so it is seriously incomplete.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"plug-and-play architecture computational efficiency real-time","search_mode":"hybrid","doc_ids":null} | 12 | 40 | 6 | 成功 | D0072:22, D0010:1, D0037:1, D0098:2, D0110:3, D0098:1, D0098:0, D0110:4, D0068:35, D0059:21, D0098:5, D0097:24 |
| 2 | 1 | search_chunks {"query":"real-time non-real-time application processing trade-off","search_mode":"hybrid","doc_ids":null} | 12 | 17 | 2 | 成功 | D0095:3, D0104:2, D0031:31, D0100:2, D0037:0, D0111:26, D0104:28, D0128:17, D0100:0, D0104:1, D0099:20, D0104:0 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"plug-and-play module computational efficiency accuracy trade-off latency","search_mode":"hybrid"} | 12 | 20 | 3 | 成功 | D0098:31, D0098:17, D0098:2, D0098:0, D0098:1, D0100:14, D0097:0, D0110:2, D0110:4, D0124:2, D0100:16, D0023:13 |
| 4 | 2 | search_chunks {"doc_ids":null,"query":"plug and play network real time efficiency cost budget","search_mode":"keyword"} | 12 | 1 | 0 | 成功 | D0095:2, D0095:3, D0110:3, D0072:22, D0057:2, D0110:5, D0110:4, D0110:14, D0034:10, D0006:0, D0110:1, D0037:1 |
| 5 | 3 | search_chunks {"doc_ids":null,"query":"plug-in modules real-time inference efficiency training only no overhead","search_mode":"hybrid"} | 12 | 14 | 2 | 成功 | D0058:20, D0058:3, D0097:0, D0097:2, D0011:1, D0097:9, D0058:13, D0137:41, D0058:12, D0097:4, D0002:1, D0097:12 |
| 6 | 3 | search_chunks {"doc_ids":null,"query":"\"plug-and-play\" architecture","search_mode":"keyword"} | 12 | 25 | 3 | 成功 | D0045:24, D0111:42, D0078:4, D0089:84, D0071:41, D0095:25, D0019:14, D0078:3, D0095:1, D0053:0, D0120:16, D0072:22 |
| 7 | 4 | search_chunks {"doc_ids":null,"query":"real-time constraint inference overhead deployment efficiency","search_mode":"hybrid"} | 12 | 1 | 0 | 成功 | D0110:0, D0110:3, D0097:0, D0055:43, D0112:1, D0038:0, D0073:16, D0045:1, D0098:2, D0032:15, D0042:0, D0110:2 |
| 8 | 4 | search_chunks {"doc_ids":null,"query":"non-real-time offline preprocessing cost efficiency plug-in","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0037:0, D0037:1, D0037:15, D0037:17, D0037:16, D0110:3, D0110:0, D0037:3, D0055:42, D0055:5, D0055:43, D0037:5 |
| 9 | 5 | search_chunks {"doc_ids":null,"query":"plug-and-play real-time latency requirement application","search_mode":"keyword"} | 12 | 1 | 0 | 成功 | D0024:36, D0072:22, D0054:0, D0095:26, D0133:1, D0089:100, D0089:69, D0007:1, D0006:3, D0095:18, D0002:1, D0045:1 |
| 10 | 5 | search_chunks {"doc_ids":null,"query":"efficiency trade-off real-time vs offline deployment modular design","search_mode":"hybrid"} | 12 | 5 | 1 | 成功 | D0098:17, D0038:0, D0110:4, D0027:24, D0110:2, D0058:19, D0104:28, D0073:0, D0110:1, D0111:26, D0113:24, D0100:2 |
| 11 | 6 | read_chunks {"doc_id":"D0058","ordinals":[3,12,13,20]} | 4 | 0 | 0 | 成功 | D0058:3, D0058:12, D0058:13, D0058:20 |
| 12 | 6 | read_chunks {"doc_id":"D0124","ordinals":[2,3]} | 2 | 0 | 0 | 成功 | D0124:2, D0124:3 |
| 13 | 6 | search_chunks {"doc_ids":null,"query":"real-time vs offline applications efficiency plug-and-play architecture difference","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0010:1, D0055:40, D0097:3, D0010:3, D0072:22, D0010:0, D0038:0, D0110:4, D0055:42, D0098:17, D0003:48, D0010:4 |
| 14 | 7 | search_chunks {"doc_ids":null,"query":"deployment computational overhead real-time inference","search_mode":"keyword"} | 12 | 0 | 0 | 成功 | D0058:3, D0045:1, D0062:0, D0068:1, D0072:19, D0058:20, D0024:1, D0072:16, D0133:1, D0041:13, D0073:19, D0073:16 |
| 15 | 7 | search_chunks {"doc_ids":null,"query":"real-time application constraint latency budget efficiency","search_mode":"keyword"} | 12 | 0 | 0 | 成功 | D0110:14, D0032:15, D0007:1, D0110:2, D0024:36, D0055:39, D0055:40, D0055:5, D0017:6, D0006:6, D0055:41, D0110:13 |

judge reasoning：

> The generated answer fails to provide the key differences from the gold answer, instead claiming the context does not support a general comparison, which contradicts the required core content.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> For real-time applications like conversations, plug-and-play methods optimize for per-token inference speed using residual adapters (1.5% parameters per style) to avoid the high computational cost of methods like PPLM. For non-real-time applications like long-range modeling, the focus shifts to reducing the O(L^2) complexity to O(L log L) through techniques like FFT-based convolutions, while maintaining parallelizability during training.

**naive 最终答案**

> Based on the context, I cannot fully answer this question because the documents do not contain a direct comparison of plug-and-play architectures specifically for **real-time vs. non-real-time** applications.
> 
> What the context does provide about plug-and-play (plug-in) efficiency:
> - **LIO (D0058)**: Plug-in modules (OEL, SCL) are only active during training and are **removed/disabled at inference**, so they introduce **no computational overhead** and run faster at deployment.
> - **IA-RED2 (D0098)**: A model-agnostic "plugin" redundancy-reduction module that drops uninformative tokens, yielding up to 1.4× speedup on DeiT and 4× on TimeSformer by cutting FLOPs/latency.
> - **DPP-VFX (D0037)**: An exact sampler that shifts computation to preprocessing (sublinear first-sample cost, then constant per-sample cost).
> 
> However, none of these documents explicitly contrast how these mechanisms are tuned for **real-time vs. non-real-time** applications (e.g., latency-constrained inference vs. offline batch processing). That specific comparison cannot be established from the given context.

**community 最终答案**

> Based on the available context, the collection does not contain a document that directly contrasts plug-and-play architectures' computational efficiency for real-time versus non-real-time applications. The retrieved papers address related but distinct issues, so I can only synthesize what is actually stated:
> 
> - **Plug-in/training-only modules (D0058, LIO):** These plug-and-play style modules are explicitly designed so that at inference time they can be disabled/removed — "introduce no computational overhead at inference time" and "no additional computational overhead for model deployment." This is the closest evidence: they keep the deployed (real-time) model cost identical to the baseline, pushing computational cost into training (non-real-time).
> 
> - **Online-serving vs. offline-training cost (D0104):** ADM is explicitly built for real-time bidding, keeping online inference within a strict SLA (~3ms, >99% of responses under 5ms) while shifting heavy cost to offline training (an MLP "saved at most 85% time cost" versus RNN-based DLF's 1400s/epoch).
> 
> However, the context never states a general rule that plug-and-play architectures handle efficiency differently for real-time vs. non-real-time applications, nor does it define such a dichotomy for these architectures. A comparative conclusion (e.g., "real-time favors zero inference overhead via training-time-only modules, while non-real-time favors heavier preprocessing/offline cost") is **not** established by the evidence. I can only report the two specific cases above; I cannot claim a general difference without overstepping the context.

</details>

<a id="case-mdaqa-37"></a>

### mdaqa:37 — 评分与执行路径对照

**问题：** How do the reconstruction capabilities and memory efficiency trade-offs differ between word-level and sentence-level binary embedding approaches?

**score：3→4（Δ+1）；rounds：2→3（Δ+1）。**

工具安排：naive 为第1轮2次；community 为第1轮2次、第2轮2次。最终回答另占一轮。

轮次增加 1，工具总数 2→4、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 18→30、文档 overview 6→28；工具结果字符数 64,213→125,775，QA token 20,044→62,597。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/a77a21af89d34612a829e2af1630bac5.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/76e56957dba74fa7b0a63296c8796d02.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"word-level sentence-level binary embedding reconstruction memory efficiency trade-off","search_mode":"hybrid","doc_ids":null} | 12 | 5 | 0 | 成功 | D0042:3, D0010:4, D0042:4, D0042:2, D0010:16, D0010:22, D0004:9, D0042:0, D0010:0, D0135:2, D0010:1, D0110:2 |
| 2 | 1 | search_chunks {"query":"binary embeddings reconstruction capability memory trade-off","search_mode":"vector","doc_ids":null} | 12 | 1 | 0 | 成功 | D0010:0, D0010:1, D0042:0, D0010:4, D0010:3, D0010:22, D0042:3, D0042:44, D0010:19, D0035:21, D0042:47, D0010:2 |

judge reasoning：

> The generated answer correctly captures the key trade-offs and memory/accuracy figures, but incorrectly states that sentence-level approaches do not reconstruct continuous vectors, which contradicts the gold answer's implication that they require more complex autoencoder architectures for reconstruction.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"word-level sentence-level binary embedding reconstruction memory","search_mode":"hybrid","doc_ids":null} | 12 | 28 | 4 | 成功 | D0042:3, D0010:4, D0042:41, D0042:4, D0042:2, D0010:0, D0010:17, D0010:16, D0042:37, D0094:15, D0042:38, D0004:9 |
| 2 | 1 | search_chunks {"query":"binary embedding reconstruction capability memory efficiency trade-off","search_mode":"vector","doc_ids":null} | 12 | 0 | 0 | 成功 | D0010:0, D0010:1, D0042:0, D0010:4, D0010:3, D0042:3, D0042:44, D0010:15, D0010:19, D0010:17, D0010:22, D0010:2 |
| 3 | 2 | search_chunks {"doc_ids":["D0042"],"query":"reconstruction loss reconstruct real-valued vector decoder","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0042:31, D0042:30, D0042:6, D0042:37, D0042:38, D0042:0, D0042:33, D0042:39, D0042:3, D0042:29, D0042:44, D0042:32 |
| 4 | 2 | read_chunks {"doc_id":"D0042","ordinals":[5,6,7,8]} | 4 | 0 | 0 | 成功 | D0042:5, D0042:6, D0042:7, D0042:8 |

judge reasoning：

> The generated answer accurately captures the key trade-offs, memory reductions, reconstruction roles, and semantic-preserving requirements described in the gold answers.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> While both approaches achieve significant memory reduction (37.5x for word-level and 98.5% for sentence-level), they exhibit different reconstruction characteristics - word-level binarization shows only 2% accuracy loss on semantic tasks with direct reconstruction, while sentence-level requires more complex autoencoder architectures with semantic-preserving objectives to maintain similar performance levels. This difference stems from the increased complexity of preserving sentence-level semantic relationships compared to word-level ones.

**naive 最终答案**

> Word-level binary embedding (D0010) uses an autoencoder whose explicit goal is **reconstruction**: binary codes are stored and real-valued vectors are reconstructed on the fly from the binary codes plus a reconstruction matrix (e.g., 16.1 MB vs. 1.2 GB for 1M words at 128 bits), giving ~97% memory reduction (37.5× smaller) with ~2% accuracy loss; reconstructed vectors often stay competitive (GloVe 512-bit even beats the originals).
> 
> Sentence-level binarization (D0042) instead prioritizes **compact binary codes for fast Hamming-distance retrieval**, not reconstruction of continuous vectors. Its best model (autoencoder with semantic-preserving loss) also degrades performance by only ~2% but saves over 98% of memory; training-free random-projection/PCA variants are competitive at small dimensions.
> 
> In short: both save roughly ~97–98% memory with ~2% loss, but word-level approaches trade memory for the ability to reconstruct real-valued vectors, whereas sentence-level approaches trade reconstruction capability for direct retrieval efficiency with slightly larger memory savings.

**community 最终答案**

> Based on the two papers:
> 
> **Word-level binarization (D0010):** Reconstruction is a central capability — the autoencoder decodes binary codes back into real-valued vectors, so one can store only binary codes plus the reconstruction matrix and compute real-valued vectors on the fly only for needed words (e.g., 16.1MB vs 1.2GB for 1M words at 128 bits). This near-lossless reconstruction costs only ~2% accuracy; vectors shrink ~37.5x (97% memory reduction), with top-K queries ~30x faster.
> 
> **Sentence-level binarization (D0042):** Reconstruction is used only as a *training objective* (L_rec) for the autoencoder, not as an end-use capability — the binary codes are consumed directly via Hamming distance for retrieval. A reconstruction-only objective can yield small reconstruction error but sub-optimal semantic codes, so a semantic-preserving loss is added (AE-binary-SP). Memory savings are larger (>98% footprint reduction, ~2% downstream loss), codes are typically much longer (512–4096 bits), and training-free random/PCA variants are competitive at 512 bits.
> 
> **Key trade-off:** word-level prioritizes faithful reconstruction of real-valued vectors (enabling on-the-fly recovery with minimal loss), whereas sentence-level prioritizes compact, semantically informative binary codes for Hamming-distance retrieval, treating reconstruction merely as a regularizer that must be supplemented by semantic-preserving constraints.

</details>

<a id="case-mdaqa-38"></a>

### mdaqa:38 — 原文精读有助补齐，但两轮消耗在非法 JSON

**问题：** What are the key architectural differences in how these binary embedding methods preserve semantic relationships while reducing dimensionality?

**score：2→4（Δ+2）；rounds：2→5（Δ+3）。**

community 增加了 word-level correlation-minimization regularization 的比较，2→4 分、2→5 轮。不过第 2、3 轮共四次 read_chunks 参数把 ordinals 写成逗号串，缺少数组方括号，例如 {"doc_id":"D0042","ordinals":6,7,8}，两轮均全部失败；第 4 轮正确读取 D0042 和 D0010 后才回答。增益与成功精读相容，但多出的三轮中两轮是接口恢复，不能说需要三轮更深推理才能提高分数。

工具安排：naive 为第1轮2次；community 为第1轮2次、第2轮2次、第3轮2次、第4轮2次。最终回答另占一轮。

轮次增加 3，工具总数 2→8、错误 0→4，整轮全部工具报错的轮数 0→2。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 18→23、文档 overview 2→24；工具结果字符数 58,936→103,490，QA token 19,082→102,386。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/d3e102cdb65a496e816c46d6a1685ba1.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/6d83bc81c5d2494ba101ee775e6ea6ea.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"binary embedding methods preserve semantic relationships reducing dimensionality","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0010:1, D0010:4, D0042:4, D0010:3, D0010:2, D0042:5, D0010:17, D0010:16, D0010:20, D0042:2, D0010:15, D0042:37 |
| 2 | 1 | search_chunks {"query":"binary embedding architectural differences","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0010:3, D0010:19, D0010:16, D0042:4, D0042:31, D0010:4, D0010:17, D0042:41, D0010:1, D0042:38, D0042:3, D0042:36 |

judge reasoning：

> The generated answer accurately describes semantic-preserving autoencoder variants and distinguishes architectural approaches, but omits the word-level method's correlation-minimization regularization, so it is only partially complete.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"binary embedding methods preserve semantic relationships reducing dimensionality","search_mode":"hybrid","doc_ids":null} | 12 | 18 | 3 | 成功 | D0010:1, D0010:4, D0042:4, D0010:3, D0010:2, D0042:5, D0010:17, D0010:16, D0010:20, D0042:2, D0042:3, D0010:15 |
| 2 | 1 | search_chunks {"query":"binary embeddings semantic similarity hashing","search_mode":"vector","doc_ids":null} | 12 | 6 | 1 | 成功 | D0010:3, D0042:47, D0042:3, D0010:20, D0010:19, D0010:10, D0010:0, D0010:22, D0010:1, D0056:33, D0042:4, D0042:0 |
| 3 | 2 | read_chunks {"raw":"{\"doc_id\": \"D0042\", \"ordinals\": 6,7,8}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 35 (char 34) | — |
| 4 | 2 | read_chunks {"raw":"{\"doc_id\": \"D0010\", \"ordinals\": 4,5}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 35 (char 34) | — |
| 5 | 3 | read_chunks {"raw":"{\"doc_id\": \"D0042\", \"ordinals\": 5, 6, 7, 8, 9}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | — |
| 6 | 3 | read_chunks {"raw":"{\"doc_id\": \"D0010\", \"ordinals\": 3, 4, 5}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | — |
| 7 | 4 | read_chunks {"doc_id":"D0042","ordinals":[1,4,5,6,7,8]} | 6 | 0 | 0 | 成功 | D0042:1, D0042:4, D0042:5, D0042:6, D0042:7, D0042:8 |
| 8 | 4 | read_chunks {"doc_id":"D0010","ordinals":[3,4]} | 2 | 0 | 0 | 成功 | D0010:3, D0010:4 |

judge reasoning：

> The generated answer accurately captures the key architectural distinction between the word-level regularization approach and the sentence-level semantic-preserving autoencoder approach, matching the gold answers while adding consistent supporting detail.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> The sentence-level approach uses a semantic-preserving objective augmented with standard autoencoder architecture to encourage informative binary codes, while the word-level method employs a regularization term that minimizes correlations between binary features. The sentence approach focuses on maintaining sentence pair similarities, while the word approach emphasizes preserving individual word semantics, leading to different optimization strategies despite similar autoencoder foundations.

**naive 最终答案**

> Key architectural differences across the methods:
> 
> **1. Hard Thresholding (D0042)** – No learning: each dimension is sign-binarized directly on the pre-trained continuous vector. It preserves semantics only insofar as the original dimensions survive, but there is no training objective to retain semantic information, and the output length must equal the input (no flexible dimensionality reduction).
> 
> **2. Random Projection / LSH-style (D0042)** – No training: a randomly initialized matrix W projects the continuous embedding into an arbitrary target dimension D, then binarizes. It approximates cosine similarity of original vectors (LSH principle), so semantic relationships are preserved probabilistically via random hyperplanes, and dimensionality is freely adjustable.
> 
> **3. PCA (D0042)** – No training per se: a learned projection matrix reduces dimensionality first (keeping embeddings as distinct as possible), then binarization follows. Semantics are preserved by keeping variance/discriminative dimensions, with adaptive, flexible output size.
> 
> **4. Autoencoder with reconstruction loss (D0010; D0042's AE-binary)** – An encoder maps real vectors to bits (Heaviside step, e.g., Φ(x)=h(W·x)) of any chosen size, and a decoder reconstructs the original real-valued vector from the bits. Semantics are preserved by minimizing reconstruction error (MSE), so the binary latent code must retain enough information to rebuild the original embedding; tied weights and tanh decoding are used.
> 
> **5. Autoencoder + semantic-preserving loss (D0042's AE-binary-SP)** – Same autoencoder architecture but adds an explicit triplet/semantic-preserving regularizer, because pure reconstruction can yield small error yet sub-optimal similarity structure. This loss directly encourages the binary codes to preserve similarity relationships from the continuous space (using straight-through gradient estimation).
> 
> In short: training-free methods (threshold/random/PCA) rely on geometric projection properties; learned methods (autoencoders) add reconstruction and/or explicit semantic-preservation objectives, and only the learned autoencoder permits reconstructing real-valued vectors from the binary codes.

**community 最终答案**

> Key architectural differences among the binary embedding methods:
> 
> **Word-level (D0010 – autoencoder binarization):** An encoder maps a real-valued vector x to a binary code Φ(x)=h(W·xᵀ) using a Heaviside step function, with W sized (n×m) so the binary dimension n is chosen arbitrarily (64/128/256). A decoder with tied weights (Wᵀ) reconstructs the real-valued vector ŷ=f(Wᵀ·Φ(x)+c); semantics are preserved via MSE reconstruction loss plus feature-decorrelation. Dimensionality reduction and semantic preservation come from learning, and the decoder allows recovering original vectors.
> 
> **Sentence-level (D0042 – four strategies):**
> 1. **Hard threshold:** direct sign binarization, no training, no dimension reduction (binary length must equal original) — semantic info largely lost.
> 2. **Random projection:** a randomly initialized matrix W maps continuous embeddings to an arbitrarily chosen dimension D, then threshold-binarized (LSH-style); no training, flexible dimension, approximates cosine via Hamming distance.
> 3. **PCA:** learns a projection matrix that reduces dimension while keeping embeddings maximally distinct, then threshold-binarizes; adaptive dimension choice, no training.
> 4. **Autoencoder with semantic-preserving loss:** a regularized autoencoder augmented with a semantic-preserving (triplet) objective; best preservation.
> 
> The core architectural contrast: non-parametric methods (threshold/random projection/PCA) preserve semantics by fixed projections approximating cosine/similarity and allow arbitrary dimension, whereas the autoencoder architectures preserve semantics through learned reconstruction and semantic/triplet losses with trained encoder–decoder structure.

</details>

<a id="case-mdaqa-40"></a>

### mdaqa:40 — 评分与执行路径对照

**问题：** What are the key differences in how these approaches handle the validation and verification of commonsense knowledge assertions?

**score：2→2（Δ+0）；rounds：5→4（Δ-1）。**

工具安排：naive 为第1轮2次、第2轮2次、第3轮2次、第4轮1次；community 为第1轮2次、第2轮3次、第3轮1次。最终回答另占一轮。

轮次减少 1，工具总数 7→6、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 43→38、文档 overview 3→26；工具结果字符数 116,032→139,793，QA token 113,714→101,847。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/74d0a6d56797421e9165f53e05d02d68.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/0464eded33d9448585e7267a2485ee23.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"validation verification commonsense knowledge assertions","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0082:0, D0082:23, D0129:0, D0082:1, D0082:21, D0082:2, D0082:22, D0036:6, D0036:0, D0129:1, D0082:19, D0129:28 |
| 2 | 1 | search_chunks {"query":"approach handle commonsense knowledge validation","search_mode":"vector","doc_ids":null} | 12 | 0 | 0 | 成功 | D0036:0, D0036:1, D0036:28, D0082:0, D0082:23, D0129:2, D0036:30, D0129:30, D0036:2, D0082:21, D0082:22, D0129:0 |
| 3 | 2 | read_chunks {"doc_id":"D0082","ordinals":[3,4,5,6,7,8]} | 6 | 0 | 0 | 成功 | D0082:3, D0082:4, D0082:5, D0082:6, D0082:7, D0082:8 |
| 4 | 2 | read_chunks {"doc_id":"D0129","ordinals":[2,3,4,5,6,7]} | 6 | 0 | 0 | 成功 | D0129:2, D0129:3, D0129:4, D0129:5, D0129:6, D0129:7 |
| 5 | 3 | read_chunks {"doc_id":"D0036","ordinals":[3,4,5,6,7]} | 5 | 0 | 0 | 成功 | D0036:3, D0036:4, D0036:5, D0036:6, D0036:7 |
| 6 | 3 | read_chunks {"doc_id":"D0129","ordinals":[8,9,10,11]} | 4 | 0 | 0 | 成功 | D0129:8, D0129:9, D0129:10, D0129:11 |
| 7 | 4 | read_chunks {"doc_id":"D0036","ordinals":[8,9,10,11,12,13]} | 6 | 0 | 0 | 成功 | D0036:8, D0036:9, D0036:10, D0036:11, D0036:12, D0036:13 |

judge reasoning：

> The answer correctly captures Quasimodo and NEGATER, but it mischaracterizes UnCommonSense as using KB-based and zero-shot LM probing rather than language models fine-tuned on positive knowledge, omitting an important gold-answer detail.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"validation and verification of commonsense knowledge assertions","search_mode":"hybrid","doc_ids":null} | 12 | 16 | 3 | 成功 | D0082:23, D0082:0, D0082:21, D0082:2, D0082:22, D0082:1, D0036:0, D0036:6, D0082:19, D0082:24, D0036:30, D0129:32 |
| 2 | 1 | search_chunks {"query":"approaches handle validation verification commonsense knowledge","search_mode":"vector","doc_ids":null} | 12 | 10 | 1 | 成功 | D0036:1, D0036:0, D0036:2, D0036:12, D0036:28, D0129:22, D0036:8, D0036:4, D0020:20, D0082:22, D0036:30, D0036:11 |
| 3 | 2 | read_chunks {"doc_id":"D0129","ordinals":[8,9,10,11,12]} | 5 | 0 | 0 | 成功 | D0129:8, D0129:9, D0129:10, D0129:11, D0129:12 |
| 4 | 2 | read_chunks {"doc_id":"D0036","ordinals":[10,11,12,13]} | 4 | 0 | 0 | 成功 | D0036:10, D0036:11, D0036:12, D0036:13 |
| 5 | 2 | read_chunks {"doc_id":"D0082","ordinals":[4,5,6,7]} | 4 | 0 | 0 | 成功 | D0082:4, D0082:5, D0082:6, D0082:7 |
| 6 | 3 | search_chunks {"doc_ids":null,"query":"validating commonsense assertions plausibility checking verification corroboration typicality","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0036:11, D0036:8, D0036:22, D0082:0, D0036:0, D0036:19, D0036:9, D0082:23, D0129:0, D0082:22, D0036:15, D0129:26 |

judge reasoning：

> The generated answer correctly captures Quasimodo's multi-source corroboration and NegatER's fine-tuned LM approach, but it inaccurately describes UnCommonSense as using zero-shot probing rather than a fine-tuned LM on positive knowledge, missing a key part of the gold answer.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Quasimodo uses multi-source corroboration (search snippets, Wikipedia, Google Books, image tags) with a regression model to validate positive assertions, while NegatER and UnCommonSense employ language models fine-tuned on positive knowledge to score and rank potential negative assertions based on their contradiction with learned positive beliefs.

**naive 最终答案**

> The three approaches differ in what evidence they use to validate commonsense assertions:
> 
> - **NEGATER** (validation of *negative* assertions): relies solely on a fine-tuned language model's internal positive beliefs. It verifies candidates by ranking how much they "contradict" the LM's positive knowledge — measured by classification scores below a decision threshold or by gradient magnitude (surprisal). It uses no gold negatives and no external sources.
> 
> - **UnCommonSense** (negative assertions): validates via a multi-step scrutiny pipeline — KB-based scoring with sentence embeddings to filter false negatives (semantically-similar statements already known for the target), zero-shot LM plausibility probing (masking the concept and checking if the LM predicts it), and quality checks that drop generic/vague statements. It then ranks by informativeness via sibling frequency. Verification thus combines KB-internal structure (comparable concepts under a local closed-world assumption), an external LM, and statistical frequency.
> 
> - **Quasimodo** (positive assertions): validates through external multi-source corroboration — it checks co-occurrence statistics of the SPO triple across Wikipedia, search-engine answer snippets, Google Books, image tags, and Conceptual Captions, feeding these signals into a learned classifier (naive Bayes / logistic regression) that decides whether a candidate is accepted, then ranks by typicality and saliency.
> 
> In short: NEGATER verifies against an LM's learned positive beliefs (contradiction/surprisal); UnCommonSense verifies via KB-internal similarity, LM plausibility probing, and frequency-based informativeness; Quasimodo verifies via multi-source external web corroboration statistics through a trained acceptance classifier.

**community 最终答案**

> The three approaches differ mainly in what they use as the "source of truth" for validating/verifying commonsense assertions:
> 
> - **Quasimodo (positive assertions):** Verifies candidate triples via a *corroboration* stage — it gathers statistical frequency signals from multiple external sources (Wikipedia, search-engine answer snippets, Google Books, image tags, captions), feeds them into a trained (naive Bayes/logistic-regression) classifier that decides whether a triple is plausible and accepted, then ranks by typicality and saliency. Validation is thus external, multi-source, and classifier-based.
> 
> - **NEGATER (negative assertions):** Uses no external sources and no gold negatives. It fine-tunes a language model on positive KB triples (contrastive learning), then validates candidate negatives by the degree to which they "contradict" the LM's learned positive beliefs — either by scores below a per-relation decision threshold (NEGATER-θ) or by gradient magnitude/surprisal (NEGATER-∇). Verification is purely internal to the LM.
> 
> - **UnCommonSense (negative assertions):** Scrutinizes candidates with two plausibility checks: (1) KB-based scoring using sentence embeddings to detect semantic near-duplicates/false negatives, and (2) LM-based zero-shot probing (masked LM prediction of the target concept) to catch statements the open-world KB simply lacks. It additionally applies quality checks (dropping too-generic/vague statements) and ranks by informativeness via sibling frequency, with provenance generation.
> 
> In short: Quasimodo validates positives using external multi-source evidence via a classifier; NEGATER verifies negatives against a fine-tuned LM's internal positive beliefs; UnCommonSense verifies negatives via a combination of KB-relative (sibling/comparison-based) checks, zero-shot LM probing, and informativeness/quality filters.

</details>

<a id="case-mdaqa-41"></a>

### mdaqa:41 — 评分与执行路径对照

**问题：** How do the approaches differ in addressing the challenge of knowledge sparsity in commonsense assertions?

**score：3→4（Δ+1）；rounds：3→5（Δ+2）。**

工具安排：naive 为第1轮2次、第2轮2次；community 为第1轮1次、第2轮2次、第3轮2次、第4轮2次。最终回答另占一轮。

轮次增加 2，工具总数 4→7、错误 1→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 20→39、文档 overview 4→72；工具结果字符数 87,246→253,138，QA token 45,893→190,102。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

<details>
<summary>展开 judge 所提实体的字面证据核对</summary>

| 实体/术语 | naive工具中首次匹配 | naive答案 | community工具中首次匹配 | community答案 |
|---|---|---|---|---|
| Quasimodo | 轮1/调用1/D0036:5 | 出现 | 轮1/调用1/D0129/overview | 出现 |
| NegatER | 轮1/调用1/D0082:0 | 出现 | 轮1/调用1/D0082:0 | 出现 |
| UnCommonSense | 轮1/调用1/D0129:0 | 出现 | 轮1/调用1/D0129:0 | 出现 |

这里只检查指定字面串及字母数字边界，不评判上下文是否在讨论同一事实；未匹配不排除同义表述，出现也不代表正确采用。它用于区分“可能未召回”和“已出现但未展开”的复核入口，不能自动判定因果。

</details>

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/77470b0ee502414fbf3e45aafbb78695.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/5c5d6298aa07410889b2df58f0560517.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"knowledge sparsity commonsense assertions","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0082:23, D0082:0, D0082:21, D0129:0, D0082:2, D0082:22, D0082:1, D0036:6, D0082:19, D0129:1, D0036:5, D0036:0 |
| 2 | 1 | search_chunks {"query":"sparsity of commonsense knowledge approaches differ","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0082:23, D0082:22, D0082:21, D0082:0, D0082:1, D0082:18, D0082:2, D0129:0, D0082:19, D0082:20, D0036:0, D0036:5 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"sparsity sparse commonsense assertions coverage long tail","search_mode":"hybrid"} | 12 | 1 | 0 | 成功 | D0082:23, D0082:2, D0082:22, D0082:0, D0082:21, D0129:5, D0082:1, D0097:2, D0036:1, D0097:23, D0097:15, D0129:2 |
| 4 | 2 | read_chunks {"raw":"{\"doc_id\": \"D0036\", \"ordinals\": 1, 2, 3, 4}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | — |

judge reasoning：

> The generated answer correctly captures the main difference (Quasimodo uses non-standard sources for positive knowledge, while NegatER and UnCommonSense address negative sparsity), but omits the key detail that the latter two use dense k-nearest neighbors retrieval and semantic similarity to identify relevant concept pairs.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"knowledge sparsity in commonsense assertions","search_mode":"hybrid","doc_ids":null} | 12 | 38 | 5 | 成功 | D0082:23, D0082:0, D0082:21, D0082:2, D0082:22, D0129:0, D0082:1, D0082:19, D0020:16, D0036:6, D0082:24, D0019:24 |
| 2 | 2 | search_chunks {"doc_ids":null,"query":"knowledge sparsity commonsense knowledge base completion structural semantic context","search_mode":"hybrid"} | 12 | 8 | 1 | 成功 | D0082:23, D0082:0, D0082:22, D0082:2, D0082:21, D0082:1, D0082:19, D0129:0, D0082:24, D0012:25, D0020:20, D0020:16 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"sparsity commonsense assertions infrequent concepts addressing challenge","search_mode":"hybrid"} | 12 | 3 | 1 | 成功 | D0129:0, D0129:5, D0082:0, D0082:23, D0129:1, D0082:1, D0129:6, D0082:2, D0082:22, D0129:2, D0013:24, D0140:8 |
| 4 | 3 | search_chunks {"doc_ids":null,"query":"sparse commonsense assertions challenge coverage approach","search_mode":"keyword"} | 12 | 23 | 3 | 成功 | D0082:1, D0086:1, D0082:0, D0086:6, D0086:5, D0142:1, D0110:2, D0020:16, D0110:1, D0110:0, D0054:10, D0129:26 |
| 5 | 3 | search_chunks {"doc_ids":["D0036","D0082","D0129"],"query":"sparsity of commonsense assertions","search_mode":"keyword"} | 12 | 0 | 0 | 成功 | D0082:1, D0082:0, D0082:2, D0082:22, D0082:23, D0036:0, D0082:21, D0129:5, D0129:1, D0082:19, D0082:18, D0082:4 |
| 6 | 4 | read_chunks {"doc_id":"D0082","ordinals":[3,4,5,6,7,18]} | 6 | 0 | 0 | 成功 | D0082:3, D0082:4, D0082:5, D0082:6, D0082:7, D0082:18 |
| 7 | 4 | read_chunks {"doc_id":"D0036","ordinals":[0,1,2,3]} | 4 | 0 | 0 | 成功 | D0036:0, D0036:1, D0036:2, D0036:3 |

judge reasoning：

> The generated answer fully captures the core meaning and key facts of the gold answer, with additional relevant detail that does not contradict it.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Quasimodo tackles sparsity by tapping into non-standard sources like query logs and QA forums to gather implicit commonsense knowledge, while NegatER and UnCommonSense handle sparsity by using dense k-nearest neighbors retrieval and semantic similarity to identify thematically relevant concept pairs for generating negative assertions.

**naive 最终答案**

> Based on the context, the approaches differ mainly in what kind of sparsity they target and how:
> 
> - **Quasimodo (D0036)** tackles the sparseness/bias of online sources: commonsense properties are so mundane they are rarely stated explicitly, so standard sources like Wikipedia are "fairly useless." It instead taps non-standard sources (search-engine query logs and QA forums), corroborates candidates with statistical cues from encyclopedias, books, and image tags, and focuses on salient/typical properties ranked by typicality and saliency.
> 
> - **NEGATER (D0082)** tackles sparsity of *negative* knowledge: most commonsense KBs contain no negatives at all. Rather than random sampling (efficient but inaccurate) or costly human annotation, it ranks out-of-KB statements by likelihood of being negative using a language model fine-tuned only on positive KB statements.
> 
> - **UnCommonSense (D0129)** also addresses the scarcity of negative commonsense, but differs from NEGATER by identifying comparable (sibling) concepts, postulating a local closed-world assumption, and ranking candidate negations by *informativeness* (scrutinized via KB- and LM-based plausibility checks), yielding informative statements like "gorillas are not territorial."
> 
> In short: Quasimodo expands *positive* assertion coverage from non-standard web sources; NEGATER and UnCommonSense expand *negative* assertion coverage—NEGATER via LM-ranked candidate negatives, UnCommonSense via comparable concepts + local CWA ranked by informativeness.

**community 最终答案**

> Based on the context, three approaches address the sparsity of commonsense knowledge differently:
> 
> - **Quasimodo (D0036)** tackles the sparseness/bias of *positive* commonsense assertions in standard sources (commonsense is rarely stated explicitly, e.g., Wikipedia is "fairly useless" for it) by mining non-standard web sources—search-engine query logs and QA forums—then corroborating candidates with statistical cues from encyclopedias, books, image tags, and ranking by typicality/saliency and clustering.
> 
> - **NEGATER (D0082)** addresses the sparsity of *negative* commonsense statements (most KBs contain no negatives) without requiring gold negatives: it fine-tunes an LM on positive KB triples, generates out-of-KB candidates via dense k-NN head/tail replacement, and ranks them by how strongly they contradict the LM's positive beliefs (scores or gradients), explicitly noting baselines are "less effective on highly sparse commonsense KBs."
> 
> - **UnCommonSense (D0129)** addresses the absence of negatives in CSKBs (which store only positives, with absent statements' truth unknown under open-world assumption) by finding comparable/sibling concepts via embeddings and taxonomy, assuming a local closed-world assumption so that positives of comparable concepts absent for the target become negation candidates, then scrutinizing with KB- and LM-based plausibility checks and ranking by informativeness.
> 
> In short: Quasimodo mines positive assertions from non-standard web sources to counter source sparsity; NEGATER repurposes positive LM knowledge to generate negatives without gold labels; UnCommonSense exploits comparable concepts and a local closed-world assumption to materialize informative negatives.

</details>

<a id="case-mdaqa-42"></a>

### mdaqa:42 — 人工评估材料两边都有，四分差混合采用差异与尺度效应

**问题：** What are the fundamental differences in how these systems evaluate the quality and informativeness of their generated assertions?

**score：0→4（Δ+4）；rounds：4→4（Δ+0）。**

community 明确补写 Quasimodo 的 crowd-rated meaningfulness/typicality/saliency，0→4 分，同为 4 轮。但 naive 首轮已返回 D0036:23 的 crowd judgement 原文与 D0036 overview 中的 Crowd studies，因此不是 community 独自发现人工评估。两边对负知识系统的自动过滤与人工质量评估仍可能混在一起；满分不能作为每项评测机制都完备的证明。这里真实可见的改善是最终答案采用了 Quasimodo 人工评估信息，分差大小还需 judge 复核。

工具安排：naive 为第1轮2次、第2轮2次、第3轮1次；community 为第1轮2次、第2轮2次、第3轮2次。最终回答另占一轮。

两边均为 4 轮，但工具总数 5→6，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 49→47、文档 overview 13→68；工具结果字符数 133,089→195,927，QA token 100,866→136,181。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

<details>
<summary>展开 judge 所提实体的字面证据核对</summary>

| 实体/术语 | naive工具中首次匹配 | naive答案 | community工具中首次匹配 | community答案 |
|---|---|---|---|---|
| Quasimodo | 轮1/调用1/D0036:23 | 出现 | 轮1/调用1/D0036:23 | 出现 |
| NegatER | 轮1/调用1/D0082:16 | 出现 | 轮1/调用1/D0129:15 | 出现 |
| UnCommonSense | 轮1/调用1/D0129:16 | 出现 | 轮1/调用1/D0129:5 | 出现 |

这里只检查指定字面串及字母数字边界，不评判上下文是否在讨论同一事实；未匹配不排除同义表述，出现也不代表正确采用。它用于区分“可能未召回”和“已出现但未展开”的复核入口，不能自动判定因果。

</details>

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/a5bd64a7566b43c0846b72702161ef89.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/24781f86e952498c8c8a6345b141286f.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"evaluate quality and informativeness of generated assertions","search_mode":"hybrid","doc_ids":null} | 12 | 8 | 0 | 成功 | D0129:8, D0036:23, D0138:15, D0129:16, D0138:3, D0082:16, D0089:49, D0020:16, D0129:15, D0036:22, D0054:9, D0017:6 |
| 2 | 1 | search_chunks {"query":"informativeness of assertions system differences","search_mode":"hybrid","doc_ids":null} | 12 | 5 | 0 | 成功 | D0129:28, D0089:3, D0117:1, D0129:5, D0129:9, D0022:18, D0129:16, D0089:51, D0129:8, D0009:13, D0132:16, D0008:1 |
| 3 | 2 | read_chunks {"doc_id":"D0129","ordinals":[8,9,10,11,12,13,14,15,16,17]} | 10 | 0 | 0 | 成功 | D0129:8, D0129:9, D0129:10, D0129:11, D0129:12, D0129:13, D0129:14, D0129:15, D0129:16, D0129:17 |
| 4 | 2 | search_chunks {"doc_ids":["D0082"],"query":"informativeness ranking negative statements grammar thematic consistency","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0082:16, D0082:17, D0082:15, D0082:8, D0082:29, D0082:28, D0082:0, D0082:14, D0082:4, D0082:26, D0082:6, D0082:7 |
| 5 | 3 | search_chunks {"doc_ids":["D0036"],"query":"typicality saliency ranking formula informativeness assertion quality","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0036:22, D0036:23, D0036:15, D0036:9, D0036:3, D0036:24, D0036:5, D0036:14, D0036:21, D0036:30, D0036:0, D0036:29 |

judge reasoning：

> The generated answer directly contradicts the gold answer's core claim that Quasimodo evaluates quality through human judgments, instead attributing it to web frequency corroboration, and also omits the human evaluation of true negative rate for NegatER and UnCommonSense.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"evaluate quality informativeness of generated assertions","search_mode":"hybrid","doc_ids":null} | 12 | 35 | 5 | 成功 | D0129:5, D0129:8, D0132:13, D0045:11, D0036:23, D0138:15, D0129:16, D0138:3, D0089:49, D0129:15, D0082:16, D0020:16 |
| 2 | 1 | search_chunks {"query":"fundamental differences evaluating generated assertions quality","search_mode":"hybrid","doc_ids":null} | 12 | 30 | 4 | 成功 | D0119:25, D0129:16, D0133:0, D0004:11, D0060:19, D0141:34, D0082:1, D0117:11, D0036:23, D0078:1, D0065:30, D0094:14 |
| 3 | 2 | read_chunks {"doc_id":"D0129","ordinals":[6,7,8,9,10]} | 5 | 0 | 0 | 成功 | D0129:6, D0129:7, D0129:8, D0129:9, D0129:10 |
| 4 | 2 | read_chunks {"doc_id":"D0082","ordinals":[2,3,4,5,6,7]} | 6 | 0 | 0 | 成功 | D0082:2, D0082:3, D0082:4, D0082:5, D0082:6, D0082:7 |
| 5 | 3 | read_chunks {"doc_id":"D0129","ordinals":[11,12,13,14,15]} | 5 | 0 | 0 | 成功 | D0129:11, D0129:12, D0129:13, D0129:14, D0129:15 |
| 6 | 3 | search_chunks {"query":"Quasimodo typicality saliency ranking informativeness scoring","search_mode":"hybrid","doc_ids":["D0036"]} | 12 | 3 | 1 | 成功 | D0036:23, D0036:22, D0036:24, D0036:3, D0036:28, D0036:27, D0036:5, D0036:0, D0036:26, D0036:15, D0036:9, D0036:21 |

judge reasoning：

> The generated answer accurately captures Quasimodo's human-judged meaningfulness/typicality/saliency and the automated consistency/plausibility-based evaluation used by UnCommonSense and NegatER, with detailed consistent elaboration.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Quasimodo evaluates quality through human judgments of meaningfulness, typicality and saliency of positive assertions, while NegatER and UnCommonSense assess quality through grammatical correctness, thematic consistency, and contradiction with established positive knowledge, along with measuring the true negative rate through human evaluation.

**naive 最终答案**

> The three systems differ fundamentally in what they treat as "quality" and "informativeness":
> 
> **Quasimodo** (positive assertions): Quality = corroboration of frequency signals from multiple web sources (naive Bayes plausibility scores π). Informativeness = probabilistic ranking of the triple: typicality τ = P[p,o|s] (how typical/informative the triple is *for its subject*) and saliency σ = P[s|p,o] (how spontaneously associated the property is).
> 
> **UnCommonSense** (negative assertions): Plausibility/quality = KB-based set-difference with sentence-embedding similarity plus zero-shot BERT (LM) masked probing. Informativeness = how *uncommon the candidate is among comparable sibling concepts* — strict sibling frequency (exact phrasing) or relaxed sibling frequency (semantic similarity via sentence embeddings), with generic/vague statements (holding for ≥β of all concepts) filtered out.
> 
> **NegatER** (negative assertions): Quality defined by grammar (R1) and thematic head–tail consistency (R2). Informativeness (R3) = how much a candidate *contradicts the fine-tuned LM's positive beliefs*: ranked either by classification scores below a decision threshold (candidates that look "almost positive," i.e., most plausible) or by gradient magnitude ("surprisal" — how much the LM's beliefs would need updating to accept the candidate as true).
> 
> In short: Quasimodo grounds informativeness in subject-typicality/saliency from web corroboration; UnCommonSense grounds it in uniqueness relative to sibling concepts (validated by KB+LM plausibility); NegatER grounds it in contradiction/surprisal relative to an LM's learned positive knowledge (constrained by grammar and topical consistency).

**community 最终答案**

> The relevant systems are the commonsense-knowledge systems in this collection (Quasimodo, UnCommonSense, NEGATER), which define "quality" and "informativeness" of generated assertions very differently:
> 
> **Quasimodo** — informativeness is statistical **typicality (τ = P[p,o|s]) and saliency (σ = P[s|p,o])**, derived from corroboration frequency across multiple web sources; quality is judged by crowd ratings of meaningfulness/typicality/saliency, with the pipeline discarding atypical or uninformative properties.
> 
> **UnCommonSense** — informativeness of a negation is its **uniqueness relative to a concept's comparable siblings** (strict/relaxed sibling frequency), plus filtering of generic statements that hold for ≥β of KB concepts; quality is **plausibility**, checked via KB-based sentence-embedding similarity (to remove false negatives) and zero-shot BERT masked-prediction.
> 
> **NEGATER** — informativeness is **task/goal-dependent utility** (R3: a statement is informative if counterproductive or contradictory to a given goal), operationalized as how strongly a statement **contradicts a fine-tuned LM's positive beliefs** (via classification scores or gradients); quality is **grammar and thematic/topical consistency** with positive KB knowledge (R1, R2).
> 
> In short: Quasimodo uses frequency-based typicality/saliency and human-rated meaningfulness; UnCommonSense uses sibling-relative uniqueness and KB/LM plausibility checks; NEGATER uses LM-contradiction and grammar/consistency with positives.

</details>

<a id="case-mdaqa-44"></a>

### mdaqa:44 — 评分与执行路径对照

**问题：** What are the key differences between using attainable utility preservation versus future task consideration for avoiding side effects?

**score：4→3（Δ-1）；rounds：3→2（Δ-1）。**

工具安排：naive 为第1轮2次、第2轮2次；community 为第1轮2次。最终回答另占一轮。

轮次减少 1，工具总数 4→2、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 39→17、文档 overview 5→30；工具结果字符数 100,968→91,909，QA token 54,481→26,699。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

<details>
<summary>展开 judge 所提实体的字面证据核对</summary>

| 实体/术语 | naive工具中首次匹配 | naive答案 | community工具中首次匹配 | community答案 |
|---|---|---|---|---|
| AUP | 轮1/调用1/D0073:0 | 出现 | 轮1/调用1/D0073:0 | 出现 |

这里只检查指定字面串及字母数字边界，不评判上下文是否在讨论同一事实；未匹配不排除同义表述，出现也不代表正确采用。它用于区分“可能未召回”和“已出现但未展开”的复核入口，不能自动判定因果。

</details>

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/3e1179d9f36f4a1b94e4aa210b4d8c87.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/5f08efad14c34a619ef83022de856395.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"attainable utility preservation versus future task consideration avoiding side effects","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0073:0, D0080:0, D0080:22, D0080:19, D0073:19, D0080:1, D0080:16, D0080:18, D0073:18, D0073:17, D0080:17, D0080:3 |
| 2 | 1 | search_chunks {"query":"attainable utility preservation future task consideration","search_mode":"vector","doc_ids":null} | 12 | 3 | 0 | 成功 | D0089:3, D0073:0, D0019:16, D0089:51, D0089:59, D0080:0, D0080:22, D0080:19, D0089:52, D0083:43, D0089:18, D0089:34 |
| 3 | 2 | search_chunks {"doc_ids":["D0073"],"query":"attainable utility preservation baseline inaction auxiliary reward","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0073:0, D0073:6, D0073:3, D0073:2, D0073:1, D0073:7, D0073:23, D0073:26, D0073:8, D0073:28, D0073:21, D0073:18 |
| 4 | 2 | search_chunks {"doc_ids":["D0080"],"query":"comparison attainable utility preservation baseline policy difference","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0080:10, D0080:22, D0080:6, D0080:14, D0080:26, D0080:2, D0080:3, D0080:11, D0080:27, D0080:15, D0080:23, D0080:0 |

judge reasoning：

> The generated answer accurately captures the key differences between AUP and future task consideration, aligns with the gold answers, and adds consistent supporting detail.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"attainable utility preservation future task consideration avoiding side effects","search_mode":"hybrid","doc_ids":null} | 12 | 20 | 3 | 成功 | D0073:0, D0080:0, D0080:22, D0080:19, D0080:1, D0080:16, D0073:19, D0080:17, D0080:18, D0080:3, D0073:18, D0080:2 |
| 2 | 1 | search_chunks {"query":"avoiding side effects attainable utility preservation","search_mode":"vector","doc_ids":null} | 12 | 10 | 1 | 成功 | D0073:0, D0118:26, D0073:19, D0080:0, D0073:1, D0080:19, D0080:18, D0073:3, D0080:17, D0073:2, D0118:25, D0080:22 |

judge reasoning：

> The generated answer correctly captures the core difference between AUP and future task consideration, but it omits the key detail that AUP can work with a single auxiliary reward function while future task approaches require modeling specific possible future tasks and provide more direct optimization.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Attainable utility preservation (AUP) focuses on preserving optimal value for randomly generated auxiliary reward functions, while the future task approach explicitly considers potential future goals in the same environment. AUP can work with a single auxiliary reward function in complex environments, while future task approaches require modeling specific possible future tasks but provide more direct optimization for preserving future capabilities.

**naive 最终答案**

> Based on the documents (D0073 AUP and D0080 future tasks):
> 
> **Attainable Utility Preservation (AUP):**
> - Penalizes the average change in action value (attainable utility) for a set of auxiliary reward functions, comparing each action to a no-op/inaction baseline — the heuristic is that preserving optimal value for many random auxiliary rewards preserves value for the true task.
> - Applies the baseline **stepwise** (to the previous state), relying on inaction rollouts to penalize delayed side effects; this can miss some delayed effects.
> - Is described as a somewhat **ad-hoc** auxiliary reward that works well in practice; can introduce **interference incentives**.
> 
> **Future Task Consideration:**
> - Rewards the ability to complete possible future tasks sampled from a distribution (e.g., uniform over goal states); side effects reduce this future-task value.
> - Runs the baseline policy from the **start of the episode** (initial mode), which avoids the delayed-side-effect failure of stepwise mode.
> - Is **more principled**, deriving the optionality-based auxiliary reward from the simple assumption of future goals and a formal definition of interference.
> - Adds a **baseline policy** (default action such as doing nothing) to filter out tasks not achievable by default, formally avoiding **interference incentives** (proven in the deterministic case).
> 
> In short: AUP preserves attainable utility relative to inaction using a stepwise baseline and is more heuristic, whereas future-task consideration explicitly models future tasks with a from-the-start baseline, giving better theoretical grounding and avoiding both side effects and interference.

**community 最终答案**

> Key differences between the two approaches:
> 
> **Attainable Utility Preservation (AUP):**
> - Penalizes shifts/changes in the ability to achieve randomly generated goals by penalizing average change in action value for a set of auxiliary reward functions (R_AUP = R − λ/|R| Σ|Q*_i(s,a) − Q*_i(s,∅)|).
> - Preserves optimal value for auxiliary reward functions, reasoning that preserving value across many functions preserves value for the true objective.
> - Naturally accounts for irreversibility—only lightly penalizes easily reversible actions.
> 
> **Future task consideration:**
> - Rewards the agent's ability to complete possible future tasks drawn from a distribution (auxiliary reward = value function for future tasks with goal states), rather than penalizing value changes.
> - Requires a baseline policy (e.g., doing nothing) to filter out future tasks not achievable by default; without it, the agent gets an interference incentive (e.g., taking food from a human to make future tasks achievable).
> - With the baseline, it avoids side effects and interference whether or not the current task requires irreversible actions.
> 
> In short: AUP penalizes deviation in attainable utility for randomly generated reward functions; future task consideration positively rewards preserving the ability to perform sampled future tasks, and uses a baseline policy to avoid interference incentives.

</details>

<a id="case-mdaqa-45"></a>

### mdaqa:45 — 评分与执行路径对照

**问题：** How can path-specific effects help distinguish between intended and unintended influences in AI decision-making systems?

**score：4→3（Δ-1）；rounds：2→2（Δ+0）。**

工具安排：naive 为第1轮1次；community 为第1轮2次。最终回答另占一轮。

两边均为 2 轮，但工具总数 1→2，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 12→20、文档 overview 2→21；工具结果字符数 29,024→76,957，QA token 11,080→24,000。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/ec871cdd1b5f45259ce0c0f2c8bdcd96.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/0fad2207e01d4df0b09c01fbcc43c564.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"path-specific effects distinguish intended unintended influences AI decision-making","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0109:15, D0109:16, D0109:17, D0109:18, D0109:26, D0109:25, D0118:0, D0118:11, D0109:1, D0109:14, D0118:5, D0118:23 |

judge reasoning：

> The generated answer accurately captures the core meaning of the gold answers, including path-specific decomposition, justified vs. problematic paths, and PSIE detecting amplified effects, with additional relevant context that does not contradict the gold.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"path-specific effects distinguish intended unintended influences AI decision-making","search_mode":"hybrid","doc_ids":null} | 12 | 21 | 3 | 成功 | D0109:15, D0109:17, D0109:16, D0109:18, D0109:26, D0109:25, D0118:11, D0118:0, D0109:1, D0109:14, D0118:5, D0109:24 |
| 2 | 1 | search_chunks {"query":"intended versus unintended influence path-specific effect","search_mode":"vector","doc_ids":null} | 12 | 0 | 0 | 成功 | D0118:26, D0118:11, D0118:7, D0118:13, D0118:5, D0118:8, D0109:18, D0118:9, D0109:27, D0109:16, D0118:25, D0118:12 |

judge reasoning：

> Generated answer correctly captures the core idea of using path-specific effects to distinguish intended from unintended causal influences and mentions amplified effects on seemingly fair paths, but omits the gold-standard's specific criterion of comparing the effect to the corresponding path to training labels.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Path-specific effects allow us to analyze both direct and indirect causal influences in decision systems. In fair decision-making, some paths (like degree→outcome) may be considered justified while others (like gender→outcome) may be problematic. However, even seemingly justified paths can carry problematic amplified effects - for instance, a degree variable might act as a proxy that amplifies gender bias. Therefore path-specific introduced effects (PSIE) should be examined to determine whether a path carries an effect larger than what is justified by the corresponding path to the training labels.

**naive 最终答案**

> Path-specific effects isolate the causal influence of an action/attribute on an outcome along specific causal paths rather than globally. This lets us distinguish intended from unintended influences:
> 
> - In agent decision-making (D0118), "delicate" parts of the state are those that shouldn't be used as a means to an end (e.g., manipulating users). Training agents to maximize the path-specific causal effect of actions on reward only along paths *not mediated by* delicate state removes the instrumental control incentive over that state — the agent no longer benefits from unintended influence, while intended effects along other paths are preserved.
> 
> - In fairness auditing (D0109), paths from a sensitive attribute to an outcome can be labelled fair ("justified") or unfair, and outcomes are judged by effects along each path (e.g., direct Gender→Outcome vs. indirect Gender→Department→Outcome in Berkeley admissions). Path-specific introduced effects (PSIE) also reveal when a seemingly fair path carries an unwanted amplified effect.
> 
> Thus, PSEs decompose total influence into per-path contributions, so unintended influences (via delicate/unfair paths) can be identified and separated from intended ones.

**community 最终答案**

> Path-specific effects isolate the causal influence of an action (e.g., a sensitive attribute or an agent's action) along a chosen subset of causal paths, while other variables take their "natural" distributions (D0109, D0118). By comparing the effect propagated along different paths, one can identify which paths carry intended influences (e.g., paths not mediated by delicate state) versus unintended ones—such as an agent's manipulation or control of delicate state (side-effects of acting toward another objective), or an amplified effect along a path that initially looked fair (D0109, D0118). Training agents to maximize path-specific effects excluding delicate-state paths removes the incentive to influence that state, distinguishing intended from unintended influences (D0118).

</details>

<a id="case-mdaqa-53"></a>

### mdaqa:53 — 评分与执行路径对照

**问题：** What are the key challenges in leveraging the duality between NLU and NLG for model training?

**score：2→2（Δ+0）；rounds：2→3（Δ+1）。**

工具安排：naive 为第1轮2次；community 为第1轮2次、第2轮2次。最终回答另占一轮。

轮次增加 1，工具总数 2→4、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 17→21、文档 overview 3→29；工具结果字符数 58,239→102,013，QA token 19,085→55,347。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/73f8ba0e7cbe48f4b098bc25c44b4c48.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/0cc7fe8ad7e348eca4008dd1b42a024c.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"duality between NLU and NLG model training challenges","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0033:1, D0063:1, D0063:0, D0033:2, D0063:2, D0063:17, D0033:7, D0033:9, D0033:6, D0033:0, D0063:16, D0033:8 |
| 2 | 1 | search_chunks {"query":"NLU NLG dual learning text generation understanding","search_mode":"vector","doc_ids":null} | 12 | 1 | 0 | 成功 | D0033:0, D0063:0, D0033:1, D0063:2, D0063:3, D0063:1, D0033:9, D0033:11, D0063:5, D0088:26, D0088:20, D0033:7 |

judge reasoning：

> The generated answer covers discrete-output training, distribution estimation, and instability, but omits the key challenge of the asymmetric many-to-one/one-to-many relationship between NLU and NLG, so it is partially correct.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"challenges duality NLU NLG model training","search_mode":"hybrid","doc_ids":null} | 12 | 22 | 3 | 成功 | D0033:1, D0063:1, D0063:0, D0033:2, D0033:6, D0063:2, D0033:9, D0063:16, D0063:17, D0033:7, D0033:0, D0033:8 |
| 2 | 1 | search_chunks {"query":"NLU NLG duality leveraging for training","search_mode":"vector","doc_ids":null} | 12 | 7 | 1 | 成功 | D0033:0, D0063:0, D0033:1, D0063:1, D0033:7, D0063:2, D0088:26, D0088:21, D0088:20, D0063:5, D0033:9, D0045:21 |
| 3 | 2 | read_chunks {"doc_id":"D0063","ordinals":[3,4,6]} | 3 | 0 | 0 | 成功 | D0063:3, D0063:4, D0063:6 |
| 4 | 2 | read_chunks {"doc_id":"D0033","ordinals":[2,3]} | 2 | 0 | 0 | 成功 | D0033:2, D0033:3 |

judge reasoning：

> The generated answer correctly captures the distribution estimation and unsupervised training instability challenges, but omits the key challenges of language's discrete/non-differentiable nature and the asymmetric many-to-one vs one-to-many NLU/NLG relationship.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> The main challenges include: 1) The discrete nature of language making it difficult to directly connect NLU and NLG models due to non-differentiability 2) The asymmetric relationship where NLU is many-to-one while NLG is one-to-many 3) The need for sophisticated data distribution estimation for both semantic frames and natural language 4) The instability in fully unsupervised training despite theoretical soundness.

**naive 最终答案**

> Key challenges include:
> 
> - The dual property between NLU and NLG was rarely explored/exploited; prior models were still trained separately in a supervised manner.
> - Fully unsupervised training leveraging the duality is unstable and hard to optimize (found from experiments), suggesting better dual learning algorithms are needed.
> - The formulation depends on data characteristics—not every NLU dataset is suitable as an NLG task, and vice versa.
> - The true marginal distributions P(x) and P(y) are often unknown and must be estimated (e.g., via language modeling and masked autoencoders), which is difficult.
> - Handling discrete outputs complicates training, requiring straight-through estimators, continuous distributions, or reinforcement learning rewards.

**community 最终答案**

> Based on the context, the key challenges are:
> 
> 1. **Estimating intractable marginal distributions** — the true P(x) and P(y) are often intractable, so they must be approximated via empirical marginal distributions, requiring data-type-specific estimation methods (e.g., language modeling for utterances, masked autoencoder for semantic frames).
> 
> 2. **Data suitability** — not every NLU dataset is suitable for use as an NLG task and vice versa; the framework's formulation depends on the characteristics of the data.
> 
> 3. **Unstable fully-unsupervised optimization** — training the two models in a fully-unsupervised manner was found unstable and hard to optimize, requiring better dual learning algorithms.
> 
> 4. **Modeling dependencies in distribution estimation** — treating slot-value pairs as independent (ignoring complex/implicit dependencies) degrades performance, so dependencies must be captured (e.g., MADE with ensembled decompositions).

</details>

<a id="case-mdaqa-54"></a>

### mdaqa:54 — 评分与执行路径对照

**问题：** How does reward sparsity affect dialog policy learning and what solutions have been proposed to address this?

**score：4→4（Δ+0）；rounds：5→7（Δ+2）。**

工具安排：naive 为第1轮2次、第2轮2次、第3轮2次、第4轮2次；community 为第1轮1次、第2轮2次、第3轮2次、第4轮2次、第5轮2次、第6轮1次。最终回答另占一轮。

轮次增加 2，工具总数 8→10、错误 0→3，整轮全部工具报错的轮数 0→1。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 62→45、文档 overview 18→28；工具结果字符数 234,522→183,086，QA token 178,545→231,565。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/9e96688a086f4167953627ab6fe3869f.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/2002ec3490de4490b6601a438fb0694a.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"reward sparsity dialog policy learning","search_mode":"hybrid","doc_ids":null} | 12 | 5 | 0 | 成功 | D0059:20, D0059:0, D0011:19, D0026:0, D0059:17, D0026:1, D0011:18, D0059:21, D0006:0, D0017:21, D0059:6, D0006:20 |
| 2 | 1 | search_chunks {"query":"sparse reward problem dialogue policy reinforcement learning solution","search_mode":"hybrid","doc_ids":null} | 12 | 1 | 0 | 成功 | D0059:20, D0006:0, D0009:0, D0006:20, D0006:24, D0009:11, D0009:12, D0006:3, D0059:21, D0017:2, D0006:5, D0017:1 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"reward is sparse only given at end of dialogue","search_mode":"hybrid"} | 12 | 1 | 0 | 成功 | D0011:22, D0011:23, D0006:6, D0011:18, D0011:19, D0011:21, D0017:5, D0006:20, D0006:22, D0017:21, D0009:3, D0045:24 |
| 4 | 2 | search_chunks {"doc_ids":null,"query":"sparse reward credit assignment exploration","search_mode":"hybrid"} | 12 | 5 | 0 | 成功 | D0097:0, D0054:20, D0097:2, D0097:5, D0097:24, D0105:0, D0054:10, D0080:0, D0105:25, D0054:13, D0105:28, D0073:21 |
| 5 | 3 | search_chunks {"doc_ids":null,"query":"reward estimation guided dialog policy learning sparse","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0059:20, D0059:0, D0011:19, D0059:17, D0026:0, D0011:18, D0011:22, D0017:21, D0006:22, D0059:6, D0006:0, D0026:4 |
| 6 | 3 | search_chunks {"doc_ids":null,"query":"sparse reward dialogue agent training task success only at end","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0006:12, D0017:12, D0006:15, D0017:21, D0017:5, D0006:16, D0011:22, D0006:20, D0006:6, D0006:5, D0059:20, D0017:11 |
| 7 | 4 | search_chunks {"doc_ids":null,"query":"credit assignment long horizon slow suboptimal convergence reward","search_mode":"hybrid"} | 12 | 5 | 0 | 成功 | D0026:1, D0080:0, D0095:25, D0073:0, D0121:25, D0011:1, D0118:25, D0095:15, D0118:26, D0089:72, D0095:1, D0053:22 |
| 8 | 4 | search_chunks {"doc_ids":null,"query":"reward shaping expert knowledge reward design sparse signal dense","search_mode":"hybrid"} | 12 | 1 | 0 | 成功 | D0105:0, D0011:18, D0011:20, D0118:0, D0105:1, D0011:1, D0080:0, D0080:21, D0090:8, D0118:26, D0009:9, D0105:28 |

judge reasoning：

> The generated answer accurately captures the core effects of reward sparsity and provides solutions consistent with the gold answers, including per-turn/sentiment-based rewards and model-based approaches, with additional relevant detail that does not contradict the gold answers.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"reward sparsity dialog policy learning solutions","search_mode":"hybrid","doc_ids":null} | 12 | 27 | 4 | 成功 | D0059:20, D0059:0, D0011:19, D0026:0, D0026:1, D0059:17, D0011:18, D0059:21, D0006:0, D0017:21, D0059:6, D0006:20 |
| 2 | 2 | search_chunks {"doc_ids":["D0070"],"query":"sparse rewards dialog policy learning","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0070:0, D0070:1, D0070:9, D0070:10, D0070:4, D0070:2, D0070:11, D0070:8, D0070:5, D0070:7, D0070:3, D0070:6 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"sparse reward signal dialog policy learning difficulty credit assignment","search_mode":"hybrid"} | 12 | 1 | 0 | 成功 | D0059:20, D0026:1, D0059:0, D0059:3, D0011:19, D0026:0, D0105:0, D0059:17, D0011:23, D0059:7, D0017:21, D0006:22 |
| 4 | 3 | search_chunks {"doc_ids":null,"query":"sparse reward dialog success reward only at end of dialog dense reward shaping subgoal","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0011:18, D0011:23, D0011:22, D0011:19, D0059:20, D0059:6, D0006:12, D0059:0, D0011:15, D0011:21, D0059:7, D0011:1 |
| 5 | 3 | read_chunks {"raw":"{\"doc_id\": \"D0059\", \"ordinals\": 4, 5, 6, 7}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | — |
| 6 | 4 | read_chunks {"doc_ids":["D0011"],"ordinals":[1,2]} | 0 | 0 | 0 | 2 validation errors for ReadArguments<br>doc_id<br>  Field required [type=missing, input_value={'doc_ids': ['D0011'], 'ordinals': [1, 2]}, input_type=dict]<br>    For further information visit https://errors.pydantic.dev/2.13/v/missing<br>doc_ids<br>  Extra inputs are not permitted [type=extra_forbidden, input_value=['D0011'], input_type=list]<br>    For further information visit https://errors.pydantic.dev/2.13/v/extra_forbidden | — |
| 7 | 4 | read_chunks {"doc_ids":["D0059"],"ordinals":[5,6,7]} | 0 | 0 | 0 | 2 validation errors for ReadArguments<br>doc_id<br>  Field required [type=missing, input_value={'doc_ids': ['D0059'], 'ordinals': [5, 6, 7]}, input_type=dict]<br>    For further information visit https://errors.pydantic.dev/2.13/v/missing<br>doc_ids<br>  Extra inputs are not permitted [type=extra_forbidden, input_value=['D0059'], input_type=list]<br>    For further information visit https://errors.pydantic.dev/2.13/v/extra_forbidden | — |
| 8 | 5 | read_chunks {"doc_id":"D0011","ordinals":[1,2]} | 2 | 0 | 0 | 成功 | D0011:1, D0011:2 |
| 9 | 5 | read_chunks {"doc_id":"D0059","ordinals":[4,5,6]} | 3 | 0 | 0 | 成功 | D0059:4, D0059:5, D0059:6 |
| 10 | 6 | search_chunks {"doc_ids":null,"query":"\"sparse\" reward task-completion dialogue reinforcement learning","search_mode":"keyword"} | 12 | 0 | 0 | 成功 | D0059:20, D0006:12, D0006:5, D0009:13, D0006:0, D0006:3, D0017:1, D0006:19, D0006:2, D0017:20, D0006:20, D0017:5 |

judge reasoning：

> The generated answer fully captures the gold answer's core points about delayed rewards slowing convergence and includes all proposed solutions (immediate/sentiment-based rewards, discriminator-based rewards, and model-based per-turn reward approaches) with additional consistent context.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Reward sparsity makes dialog policy learning inefficient since delayed rewards make convergence slow. Solutions include using immediate rewards from sentiment estimation, discriminator-based rewards, and model-based approaches that can provide per-turn rewards to guide policy learning better.

**naive 最终答案**

> Based on the context:
> 
> **Effect of reward sparsity on dialog policy learning:**
> - Dialog RL commonly uses delayed/sparse rewards (mostly task success given only at the end of a dialogue). Delayed rewards slow convergence speed (D0011).
> - Word-level RL over long multi-turn horizons suffers from credit assignment over a long horizon, leading to slow and sub-optimal convergence (D0026).
> - Rewards are sparse, given only at the end of the dialogue (e.g., success reward, or success = 20/failure = 0 minus dialogue length), providing little per-turn signal to guide the agent (D0006, D0017, D0009).
> 
> **Proposed solutions:**
> - **Reward shaping / per-turn immediate rewards:** Integrating estimated per-turn immediate rewards; expert-based reward shaping (Ferreira & Lefèvre 2013); Interaction Quality (IQ) as immediate reward (Ultes et al. 2017); sentiment-based per-turn rewards (D0011).
> - **Latent Action RL (LaRL):** Treating dialog actions as latent variables so RL/policy gradients apply at the turn level, shortening the horizon and reducing credit-assignment burden (D0026).
> - **Model-based planning / simulated experience:** Deep Dyna-Q and Discriminative Deep Dyna-Q use a world model to generate simulated experience, supplementing sparse real experience for more sample-efficient policy learning (D0006, D0017).
> - **Hierarchical/Feudal RL:** Decomposing decisions into master and sub-policies, improving scalability with the same sparse reward signal (D0009).
> - **Reward decomposition:** Role-aware reward decomposition (system/user/global rewards) providing denser, per-role reward signals (D0059).

**community 最终答案**

> **Effect of reward sparsity:** Dialog RL typically uses delayed rewards, mostly task success computed only at the end of the dialog. Such sparse/delayed rewards slow convergence, and agents may fail to connect a long sequence of actions to a distant future reward and thus never learn how to perform the task.
> 
> **Proposed solutions (from the context):**
> - **Per-turn immediate rewards / reward shaping:** replacing delayed success-only rewards with estimated per-turn rewards, expert-based reward shaping, and immediate-reward signals such as Interaction Quality or user-sentiment-based rewards (D0011).
> - **Reward decomposition:** decomposing the task reward into role-specific and global components, including sub-goal completion rewards (e.g., Hybrid Value Network in MADPL) so agents get more frequent reward signals (D0059).
> - **Model-based planning with a world model:** Deep Dyna-Q / D3Q integrate a learned world model to generate simulated experience (with a discriminator filtering low-quality experience), supplementing sparse real interactions (D0006, D0017).
> - **Domain randomization to densify rewards:** synthesizing more positive environments (e.g., Document Environment Generation) so the agent meets rewards more frequently during training (D0070).
> - **Pretraining from human conversational data** (imitation learning) to bootstrap the policy before RL (D0006, D0059).

</details>

<a id="case-mdaqa-56"></a>

### mdaqa:56 — 评分与执行路径对照

**问题：** How does multi-agent dialog policy learning differ from traditional single-agent approaches?

**score：4→4（Δ+0）；rounds：2→3（Δ+1）。**

工具安排：naive 为第1轮1次；community 为第1轮1次、第2轮1次。最终回答另占一轮。

轮次增加 1，工具总数 1→2、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 12→14、文档 overview 3→12；工具结果字符数 31,175→47,328，QA token 11,199→27,323。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/e3930d10c0cf4bfbb5e99930996700c1.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/f91599863ef84e8283a62e33801b9c4c.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"multi-agent dialog policy learning differs from traditional single-agent approaches","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0059:0, D0059:18, D0059:20, D0059:4, D0059:1, D0017:21, D0059:17, D0059:5, D0006:0, D0059:7, D0006:20, D0006:2 |

judge reasoning：

> The generated answer fully captures the core meaning of the gold answer, including modeling both user and system as agents, simultaneous joint learning, cooperative interaction, and role-aware reward decomposition, with only consistent additional detail.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"multi-agent dialog policy learning versus single-agent","search_mode":"hybrid","doc_ids":null} | 12 | 12 | 2 | 成功 | D0059:0, D0059:18, D0059:20, D0059:17, D0017:21, D0006:0, D0059:4, D0059:1, D0059:5, D0006:20, D0026:17, D0045:24 |
| 2 | 2 | read_chunks {"doc_id":"D0059","ordinals":[2,3]} | 2 | 0 | 0 | 成功 | D0059:2, D0059:3 |

judge reasoning：

> The generated answer fully captures all core aspects of the gold answer, including modeling both user and system as learning agents, role-aware reward decomposition, non-stationarity, and simultaneous cooperative optimization, with no contradictions.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Multi-agent approaches model both user and system as learning agents rather than using a fixed simulator, requiring role-aware reward decomposition, addressing non-stationarity issues, and enabling simultaneous policy optimization through cooperative interaction rather than against a static environment.

**naive 最终答案**

> Multi-agent dialog policy learning differs from traditional single-agent approaches mainly in how the user is modeled and how training proceeds:
> 
> - **User as agent vs. simulator**: Traditional approaches train a system policy against a user simulator (rule-based or data-driven), which requires heavy domain expertise or large labeled data. Multi-agent (MADPL) treats the user as another dialog agent, so both system and user policies are jointly trained simultaneously without building a simulator beforehand, requiring no explicit domain expertise.
> 
> - **Joint learning**: The conversation is modeled as a cooperative interactive process where two agents interact and are learned together, rather than training one policy against a fixed environment.
> 
> - **Training framework**: It uses the actor-critic framework following centralized training with decentralized execution (CTDE)—each actor selects actions based only on its local state-action history, while the critic is trained with all agents' actions, improving scalability over Q-learning for mixed policies.
> 
> - **Reward handling**: Because the two agents have asymmetric roles, it uses a Hybrid Value Network to decompose rewards into system, user, and global components, rather than a single reward for one agent.

**community 最终答案**

> Multi-agent dialog policy learning (MADPL) treats both the system and the user as dialog agents that interact and are jointly trained simultaneously as a cooperative multi-agent RL problem, avoiding the need to explicitly build a user simulator beforehand. Traditional single-agent approaches model the user as a stationary environment, typically via a rule-based or data-driven user simulator, and train only the system policy, which requires heavy domain expertise or considerable data. MADPL also uses role-aware reward decomposition (Hybrid Value Network) and the actor-critic/CTDE framework to handle the non-stationarity of co-adapting agents and asymmetric roles, whereas single-agent learning assumes a fixed environment.

</details>

<a id="case-mdaqa-57"></a>

### mdaqa:57 — 评分与执行路径对照

**问题：** What are the benefits of using hierarchical reinforcement learning for dialog management in large domains?

**score：4→4（Δ+0）；rounds：3→2（Δ-1）。**

工具安排：naive 为第1轮1次、第2轮1次；community 为第1轮2次。最终回答另占一轮。

轮次减少 1，工具总数 2→2、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 14→16、文档 overview 6→20；工具结果字符数 39,744→78,027，QA token 24,385→23,718。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/6a6e1dfdabb54822bed83fd2f77d1a4c.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/5f3687a868b141f296fb2575e4e9db55.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"benefits hierarchical reinforcement learning dialog management large domains","search_mode":"hybrid","doc_ids":null} | 12 | 6 | 0 | 成功 | D0009:0, D0009:12, D0009:13, D0026:20, D0006:24, D0009:1, D0017:22, D0059:20, D0045:24, D0017:23, D0026:1, D0009:11 |
| 2 | 2 | read_chunks {"doc_id":"D0009","ordinals":[1,2,3]} | 3 | 0 | 0 | 成功 | D0009:1, D0009:2, D0009:3 |

judge reasoning：

> The generated answer fully captures and expands on the core benefits of hierarchical RL for large-domain dialog management, including scalability, efficient decomposition, and handling large action spaces, without contradicting the gold answer.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"benefits of hierarchical reinforcement learning dialog management large domains","search_mode":"hybrid","doc_ids":null} | 12 | 20 | 3 | 成功 | D0009:0, D0026:20, D0009:12, D0009:13, D0006:24, D0059:20, D0009:1, D0017:22, D0045:24, D0017:23, D0026:17, D0026:1 |
| 2 | 1 | search_chunks {"query":"hierarchical reinforcement learning scalability dialog","search_mode":"vector","doc_ids":null} | 12 | 0 | 0 | 成功 | D0009:0, D0009:1, D0026:19, D0026:20, D0017:22, D0009:12, D0059:20, D0009:11, D0006:24, D0017:21, D0006:23, D0009:13 |

judge reasoning：

> The generated answer fully captures the core benefits from the gold answer—mitigating scalability issues, handling large action spaces, and improving policy learning—while adding consistent supporting details.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Hierarchical RL helps mitigate scalability issues in large domains by decomposing decisions spatially or temporally, enabling more efficient exploration and policy learning. This allows better handling of large discrete action spaces and complex multi-domain scenarios.

**naive 最终答案**

> Based on the paper "Feudal Reinforcement Learning for Dialogue Management in Large Domains," the benefits of using hierarchical RL (HRL) for dialog management in large domains are:
> 
> - **Scalability to large domains**: Traditional RL fails to scale to large domains due to the curse of dimensionality—the number of trajectories grows exponentially as the state/action space increases. HRL (e.g., Feudal RL) allows RL to scale to domains with a large number of slots by decomposing decisions into steps (a master policy selecting a subset of actions, then a sub-policy choosing a primitive action).
> - **Useful for large discrete action spaces**: It makes large action spaces tractable by using different abstraction levels in each sub-decision.
> - **Better performance**: It substantially outperforms previous state-of-the-art RL baselines in several dialogue domains and environments, with the largest gains in big domains.
> - **No additional reward signals required**: Unlike other HRL methods, it needs no modification of the reward function (no extra rewards per subtask).
> - **Reduced design effort**: The hierarchical structure is fully specified/derived from a flat ontology rather than being handcrafted.
> - **Improved generalization via shared parameters**: Slot-dependent policies with shared parameters and an information-sharing mechanism between slots learn a general way to act in any slot, further increasing scalability.

**community 最终答案**

> Based on the context (Feudal Reinforcement Learning for Dialogue Management in Large Domains):
> 
> - **Mitigates the curse of dimensionality**: Traditional RL fails to scale to large domains as the state space grows; HRL via temporal/space abstraction mitigates this problem.
> - **Enables scalability to many slots**: HRL relying on space abstraction (Feudal RL) allows RL to scale to domains with a large number of slots.
> - **Handles large discrete action spaces**: The master policy selects a subset of primitive actions, then a primitive action is chosen from that subset, making large action spaces tractable.
> - **Abstracts the state space**: Domain ontology structure is used to abstract the state, with each decision step using different parts of the abstracted state.
> - **Information sharing between slots**: Shared-parameter slot policies learn a general way to act in slots, increasing scalability.
> - **No additional reward signals needed**: Unlike other HRL methods, the hierarchical structure is derived from a flat ontology, substantially reducing design effort.
> - **Better performance**: The implementation significantly outperforms previous state-of-the-art RL methods in several dialogue domains and environments.

</details>

<a id="case-mdaqa-60"></a>

### mdaqa:60 — 评分与执行路径对照

**问题：** How do neural models handle the challenge of morphological fusion across different language families?

**score：3→2（Δ-1）；rounds：4→4（Δ+0）。**

工具安排：naive 为第1轮2次、第2轮2次、第3轮2次；community 为第1轮2次、第2轮2次、第3轮2次。最终回答另占一轮。

两边均为 4 轮，但工具总数 6→6，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 39→26、文档 overview 8→23；工具结果字符数 154,713→118,804，QA token 100,882→90,002。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/9cb05cf850c4434aad5212d899e398d6.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/72e8cb583441490a8b1305217b3fab61.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"neural models morphological fusion different language families","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0121:0, D0079:23, D0121:32, D0121:1, D0079:21, D0121:33, D0121:29, D0008:0, D0121:8, D0121:3, D0008:1, D0121:2 |
| 2 | 1 | search_chunks {"query":"morphological fusion neural machine translation","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0121:32, D0121:0, D0121:1, D0121:33, D0079:23, D0063:22, D0121:31, D0121:30, D0043:19, D0064:25, D0060:26, D0064:29 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"fusional languages subword segmentation neural models agglutinative","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0121:0, D0121:3, D0121:1, D0121:2, D0079:1, D0079:23, D0079:21, D0079:5, D0121:7, D0121:25, D0079:20, D0121:27 |
| 4 | 2 | search_chunks {"doc_ids":null,"query":"language families morphological inflection typology neural models encode","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0008:0, D0008:1, D0008:33, D0121:31, D0008:35, D0079:23, D0008:34, D0008:2, D0008:32, D0121:3, D0064:27, D0121:0 |
| 5 | 3 | read_chunks {"doc_id":"D0079","ordinals":[0,2,3,4,5,6]} | 6 | 0 | 0 | 成功 | D0079:0, D0079:2, D0079:3, D0079:4, D0079:5, D0079:6 |
| 6 | 3 | search_chunks {"doc_ids":null,"query":"subword segmentation non-concatenative morphology suitability translation","search_mode":"hybrid"} | 12 | 1 | 0 | 成功 | D0121:28, D0121:0, D0064:25, D0121:27, D0121:1, D0079:23, D0079:21, D0079:22, D0121:2, D0065:23, D0079:1, D0121:29 |

judge reasoning：

> The generated answer correctly captures the central point that higher morphological fusion makes neural models less accurate and harder to handle, but it omits the gold answer's specific finding about fusional versus non-fusional verb forms and the ability to produce acceptable alternative translations, while adding extra relevant details.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"neural models morphological fusion across language families","search_mode":"hybrid","doc_ids":null} | 12 | 22 | 3 | 成功 | D0121:0, D0079:23, D0121:32, D0079:21, D0121:1, D0121:29, D0008:33, D0121:33, D0121:31, D0121:8, D0121:3, D0008:0 |
| 2 | 1 | search_chunks {"query":"morphological fusion neural machine translation handling","search_mode":"hybrid","doc_ids":null} | 12 | 1 | 0 | 成功 | D0121:0, D0121:32, D0121:1, D0121:33, D0121:31, D0079:23, D0121:30, D0064:25, D0121:2, D0063:22, D0043:19, D0064:29 |
| 3 | 2 | read_chunks {"raw":"{\"doc_id\": \"D0121\", \"ordinals\": 4, 5, 6, 7, 9}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | — |
| 4 | 2 | search_chunks {"doc_ids":null,"query":"subword segmentation fusional agglutinative languages handling morphology neural models","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0121:0, D0079:23, D0121:1, D0121:3, D0079:21, D0079:1, D0121:28, D0121:2, D0079:22, D0064:25, D0008:33, D0079:20 |
| 5 | 3 | read_chunks {"doc_id":"D0079","ordinals":[0,1,2]} | 3 | 0 | 0 | 成功 | D0079:0, D0079:1, D0079:2 |
| 6 | 3 | read_chunks {"doc_id":"D0121","ordinals":[4,5]} | 2 | 0 | 0 | 成功 | D0121:4, D0121:5 |

judge reasoning：

> The generated answer correctly notes that higher morphological fusion leads to less accurate MT output, but it omits key gold facts about fusional forms being harder than agglutinative ones and models still producing acceptable alternative translations.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Neural models show varying performance based on fusion levels - highly fusional forms (like Spanish verbs) are harder to translate than agglutinative ones, even with frequent words. This is evidenced by lower accuracy scores for fusional verbs (>0 fusion) compared to non-fusional ones (0 fusion) in MT tasks. However, the models can still generalize and produce acceptable alternative translations, even if not exact matches.

**naive 最终答案**

> Neural models handle morphological fusion mainly by avoiding full-word vocabularies and relying on subword/character-level segmentation (e.g., BPE, unigram LM, SentencePiece) to constrain capacity and generate rare/new words. Because fusional languages merge morphemes and change their surface forms, plain surface segmentation is ineffective, so models instead perform canonical segmentation — treating it as character-level string transduction with neural models such as an LSTM pointer-generator and a hard-monotonic-attention transducer trained via imitation learning — which restores morphemes to their original forms. Across families (analytic English, fusional German, agglutinative Indonesian, polysynthetic Popoluca/Tepehua with fusional phenomena) these models generalize well in low-resource settings, though true low-resource fusional/polysynthetic segmentation remains difficult (accuracy well below emulated settings). Additionally, language embeddings encode morphological typological properties, enabling prediction for unseen language families. Still, higher fusion generally corresponds to less accurate neural MT output, and fusional joints (infixes, circumfixes, non-concatenative processes) are hard to automatize for most languages.

**community 最终答案**

> Based on the context, neural models handle morphological fusion mainly through:
> 
> - **Canonical segmentation** (D0079): In fusional languages morphemes merge and change surface forms, so surface segmentation fails. Neural sequence-to-sequence models (LSTM pointer-generator and a hard-monotonic-attention transducer trained with imitation learning), borrowed from morphological inflection, restore morphemes to their canonical forms. They work well on high-resource languages but remain challenging on truly low-resource ones.
> 
> - **Subword/character segmentation** (D0121): Because a full vocabulary is infeasible, models rely on subword approaches (BPE, unigram LM, Morfessor, PtrNet) to constrain capacity and generate rare/new words. However, fusion is hard to automate—automatic tools aren't designed to identify fusional joints (non-explicit boundaries)—and higher degrees of fusion generally correspond to less accurate MT output.
> 
> - **Language embeddings/typological representation** (D0008): Models learn distributed language embeddings encoding typological (including morphological) properties across families; fine-tuning on morphological inflection improves prediction, aiding generalization across language families.

</details>

<a id="case-mdaqa-64"></a>

### mdaqa:64 — 评分与执行路径对照

**问题：** How does selective differential privacy differ from traditional differential privacy in terms of privacy guarantees and utility gains?

**score：4→4（Δ+0）；rounds：2→3（Δ+1）。**

工具安排：naive 为第1轮2次；community 为第1轮1次、第2轮1次。最终回答另占一轮。

轮次增加 1，工具总数 2→2、错误 0→1，整轮全部工具报错的轮数 0→1。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 15→12、文档 overview 2→21；工具结果字符数 57,525→54,984，QA token 18,987→31,908。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/64aa37cda32a4a038d90ad161ea6ca85.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/d8065f13b0684dd48cb97a0d2686a656.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"selective differential privacy traditional differential privacy guarantee","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0100:0, D0100:6, D0003:4, D0100:2, D0003:0, D0100:21, D0003:46, D0003:3, D0100:1, D0100:3, D0100:7, D0003:12 |
| 2 | 1 | search_chunks {"query":"selective differential privacy utility gain privacy","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0100:0, D0100:2, D0100:6, D0003:46, D0100:3, D0100:21, D0100:1, D0003:0, D0100:17, D0003:4, D0003:44, D0003:1 |

judge reasoning：

> The generated answer accurately captures the core distinction between selective differential privacy and traditional differential privacy, including focused protection for sensitive attributes, reduced noise for utility gains, and improved performance with consistent examples.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"selective differential privacy vs traditional differential privacy privacy guarantees utility","search_mode":"hybrid","doc_ids":null} | 12 | 21 | 4 | 成功 | D0100:0, D0100:21, D0003:46, D0003:0, D0100:3, D0100:2, D0100:6, D0003:4, D0100:1, D0003:44, D0003:3, D0132:21 |
| 2 | 2 | read_chunks {"raw":"{\"doc_id\": \"D0100\", \"ordinals\": 4, 5, 7, 8}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | — |

judge reasoning：

> The generated answer accurately captures the core meaning of selective DP versus traditional DP, including focused protection on sensitive attributes, better utility by adding less noise to non-sensitive parts, and a concrete utility improvement example without contradicting the gold answer.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Selective differential privacy (S-DP) provides focused protection only for sensitive attributes within data records while traditional DP protects entire records uniformly. This targeted approach allows S-DP to achieve better utility by adding less noise to non-sensitive portions while maintaining rigorous privacy guarantees for sensitive data. Empirically, S-DP models achieve up to 25x lower error rates compared to traditional DP approaches.

**naive 最终答案**

> **Privacy guarantees:** Traditional DP protects each data point (record/token) as a whole, treating all information as equally sensitive — an over-pessimistic, undifferentiated guarantee. Selective DP (S-DP) instead provides rigorous, DP-like indistinguishability guarantees only on the sensitive portion of the data, as specified by a user-defined policy function. It protects sensitive attributes in the worst case while not constraining leakage of non-sensitive attributes, as long as sensitive ones stay protected.
> 
> **Utility gains:** Because S-DP only adds noise to private attributes (e.g., via Selective-DPSGD applying DPSGD to private variables and regular SGD to non-private ones), it improves the privacy-utility trade-off, achieving better utilities than traditional DP at the same epsilon (e.g., lower perplexity: 160.04 vs 305.86) while remaining safe under privacy attacks.

**community 最终答案**

> **Privacy guarantees:** Traditional DP protects every data point (record) as a whole, treating all attributes equally — an "over-pessimistic," undifferentiated guarantee. Selective DP (S-DP) instead provides DP-like indistinguishability guarantees only for the sensitive attributes/tokens of a record (chosen by a user-defined policy function), while not constraining leakage of non-sensitive attributes as long as sensitive ones remain protected.
> 
> **Utility gains:** Because S-DP doesn't perturb non-sensitive information, it improves the privacy-utility trade-off of traditional DP, achieving better model utility (e.g., lower perplexity than DPSGD at similar ε, such as 160.04 vs 305.86) while remaining safe against privacy attacks.

</details>

<a id="case-mdaqa-67"></a>

### mdaqa:67 — 评分与执行路径对照

**问题：** What role does graph-based learning play in improving AU recognition performance across different architectural approaches?

**score：3→4（Δ+1）；rounds：2→2（Δ+0）。**

工具安排：naive 为第1轮1次；community 为第1轮2次。最终回答另占一轮。

两边均为 2 轮，但工具总数 1→2，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 12→19、文档 overview 3→37；工具结果字符数 30,524→98,784，QA token 11,135→28,580。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/c2873b22fed84273ab3454221fe555ec.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/be4caab5a3ce43bdaff5bdf9080a72b1.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"graph-based learning AU recognition performance architectural approaches","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0085:0, D0085:9, D0085:1, D0046:0, D0085:3, D0046:2, D0046:15, D0085:4, D0085:8, D0081:0, D0085:11, D0085:5 |

judge reasoning：

> The response correctly conveys the core role of graph-based AU relationship modeling in both approaches, but it slightly omits the co-regularization detail of embedding dependencies into classifier weights and mislabels that method as co-training.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"graph-based learning AU recognition performance","search_mode":"hybrid","doc_ids":null} | 12 | 31 | 4 | 成功 | D0085:9, D0085:0, D0046:0, D0085:1, D0085:3, D0046:15, D0046:2, D0085:4, D0085:5, D0085:2, D0085:11, D0081:0 |
| 2 | 1 | search_chunks {"query":"graph convolutional network facial action unit recognition","search_mode":"hybrid","doc_ids":null} | 12 | 6 | 1 | 成功 | D0085:11, D0046:0, D0085:12, D0085:0, D0085:10, D0046:24, D0085:1, D0002:0, D0046:2, D0058:26, D0002:25, D0002:11 |

judge reasoning：

> The generated answer accurately captures the core meaning of the gold answers, describing how both MARGL and co-regularization use graph-based learning to model AU relationships and improve recognition, with additional consistent details.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Both approaches utilize graph-based learning but in different ways: The MARGL method constructs a multi-level AU relation graph to model intra-level AU relationships and inter-level regional relevance, while the co-regularization approach uses GCN to embed AU dependencies calculated from labeled data into classifier weights. Both demonstrate that incorporating AU relationships via graphs improves recognition accuracy, with MARGL showing improvements in BP4D F1-scores and co-regularization showing particular benefits for coexistent/exclusive AUs like AU4 and AU9.

**naive 最终答案**

> Graph-based learning improves AU recognition performance by modeling AU relationships and embedding that knowledge into the network's features, which boosts accuracy across different architectural designs:
> 
> - **Multi-level graph learning (MARGL, D0085):** A multi-level AU relation graph encodes both intra-level AU correlations and inter-level relevance of the same AU across backbone levels; graph convolution (GCN) message-passing enhances regional ROI features. This contributed to improvements: intra-level relations +0.7%, inter-level relations +0.5%, yielding average F1-frame of 66.1% on BP4D (vs. 60.8% baseline) and 63.8% on DISFA, outperforming prior state-of-the-art.
> 
> - **Semi-supervised co-training (D0046):** A GCN embeds prior AU relationship knowledge from label dependencies, improving recognition robustness, especially for correlated/exclusive AUs, and improving cross-database generalization (e.g., from EmotioNet to BP4D).
> 
> In short, graph-based learning lets different architectures leverage AU relationship knowledge to enhance feature representations and improve AU recognition performance.

**community 最终答案**

> Graph-based learning improves AU recognition by modeling AU relationships and embedding this knowledge into features:
> 
> - **MARGL (D0085)**: A multi-level AU relation graph with graph convolution encodes intra-level AU correlations and inter-level AU regional relevance, enhancing the discrimination of ROI features. Ablations show intra-level relations add ~0.7%, multi-level +0.6%, and inter-level relevance +0.5% in F1-frame; the full model reaches 66.1% (BP4D) and 63.8% (DISFA), outperforming the GGNN-based SRERL by 3.2% and prior SOTA by 7.8%.
> - **Multi-label co-regularization (D0046)**: A GCN embeds prior AU relationship knowledge (e.g., correlated/exclusive AUs) into the semi-supervised framework, improving AU recognition accuracy, robustness, and cross-database generalization (e.g., average F1 68.1% vs. 62.3% baseline on EmotioNet).
> 
> In both architectures, graph-based learning contributes consistent, measurable gains by leveraging AU dependencies.

</details>

<a id="case-mdaqa-68"></a>

### mdaqa:68 — 评分与执行路径对照

**问题：** How does focused attention in document-grounded generation help address the hallucination problem?

**score：4→4（Δ+0）；rounds：2→3（Δ+1）。**

工具安排：naive 为第1轮2次；community 为第1轮1次、第2轮2次。最终回答另占一轮。

轮次增加 1，工具总数 2→3、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 20→20、文档 overview 4→26；工具结果字符数 58,884→93,419，QA token 19,573→44,200。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/00a48feb11a24f80b1399e63d378e0b9.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/ec5efe18753e4bb4ae35303d76df5c65.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"focused attention document-grounded generation hallucination","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0088:0, D0117:14, D0088:2, D0088:26, D0088:3, D0117:0, D0088:1, D0117:13, D0088:7, D0117:11, D0088:6, D0088:23 |
| 2 | 1 | search_chunks {"query":"focus attention reduce hallucination RAG grounding","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0117:14, D0117:11, D0088:14, D0117:0, D0040:21, D0117:4, D0098:4, D0117:7, D0117:19, D0117:5, D0088:13, D0088:1 |

judge reasoning：

> The generated answer accurately captures the core mechanism of focused attention reducing hallucination by grounding outputs in document content, consistent with the gold answer, and adds supporting details without contradiction.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"focused attention document-grounded generation hallucination","search_mode":"hybrid","doc_ids":null} | 12 | 26 | 3 | 成功 | D0088:0, D0117:14, D0088:2, D0088:3, D0088:26, D0117:0, D0088:1, D0117:13, D0088:7, D0117:11, D0088:6, D0088:18 |
| 2 | 2 | search_chunks {"doc_ids":["D0088"],"query":"hallucination reduce grounded attention document content","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0088:3, D0088:0, D0088:2, D0088:14, D0088:15, D0088:1, D0088:26, D0088:7, D0088:13, D0088:6, D0088:16, D0088:17 |
| 3 | 2 | read_chunks {"doc_id":"D0088","ordinals":[4,5,8]} | 3 | 0 | 0 | 成功 | D0088:4, D0088:5, D0088:8 |

judge reasoning：

> The generated answer accurately captures the core mechanism of DoHA/CoDR forcing explicit attention to document content to reduce hallucination, and although it omits the 19.7 BLEU metric, this is non-critical and the answer is fully consistent with the gold answer.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Document-headed attention (DoHA) and context-driven representation (CoDR) techniques help models better ground their outputs in source documents, showing improvements of 19.7 BLEU points on dialogue tasks and reducing hallucination by forcing explicit attention to document content during generation.

**naive 最终答案**

> Focused attention in document-grounded generation addresses hallucination by making the model explicitly attend to the document's content during generation (e.g., adding a document-focused cross-attention head, DoHA, that focuses on the document representation). This grounds the generated text in the document's information, preventing the model from producing generic, content-free responses or hallucinating wrong information—whereas a model conditioned only on context tends to hallucinate facts. Error analysis shows it substantially improves grounding (about 85% of generations are completely or partially grounded when the reference is grounded), though partial hallucination and ungrounded references remain.

**community 最终答案**

> Focused attention (DoHA/CoDR) makes the decoder attend specifically to the document tokens via an extra cross-attention head, so generation is grounded in the document's content rather than only the dialogue context. When conditioned only on context, models produce generic or hallucinated (wrong) information; grounding generation in the document makes the output contain document information and avoids ungrounded, hallucinated content (e.g., in error analysis, ~90% of generations were grounded when the reference was grounded).

</details>

<a id="case-mdaqa-69"></a>

### mdaqa:69 — 评分与执行路径对照

**问题：** How do the approaches to handling occlusion boundaries differ between methods that use non-differentiable sampling versus those using algebraic surfaces, and what are their respective computational implications?

**score：4→4（Δ+0）；rounds：3→4（Δ+1）。**

工具安排：naive 为第1轮2次、第2轮2次；community 为第1轮2次、第2轮2次、第3轮2次。最终回答另占一轮。

轮次增加 1，工具总数 4→6、错误 0→2，整轮全部工具报错的轮数 0→1。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 18→31、文档 overview 4→13；工具结果字符数 73,844→134,092，QA token 41,502→80,764。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/c7616aec6b8a4bf98959560217bf92b7.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/6bb03f22a6ce4710adebf45666a0cd94.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"occlusion boundaries non-differentiable sampling","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0099:0, D0099:3, D0099:4, D0099:2, D0099:1, D0099:5, D0099:10, D0128:0, D0137:31, D0099:6, D0030:10, D0128:18 |
| 2 | 1 | search_chunks {"query":"algebraic surfaces occlusion handling","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0099:2, D0128:0, D0099:0, D0128:25, D0099:3, D0128:21, D0128:18, D0128:2, D0099:5, D0128:5, D0099:4, D0128:6 |
| 3 | 2 | read_chunks {"doc_id":"D0128","ordinals":[6,7]} | 2 | 0 | 0 | 成功 | D0128:6, D0128:7 |
| 4 | 2 | read_chunks {"doc_id":"D0099","ordinals":[3,4,10]} | 3 | 0 | 0 | 成功 | D0099:3, D0099:4, D0099:10 |

judge reasoning：

> The generated answer fully and accurately captures the core meaning and key facts of the gold answers, including the differences in occlusion handling and computational trade-offs, with additional correct details that do not contradict the gold standard.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"occlusion boundaries non-differentiable sampling algebraic surfaces","search_mode":"hybrid","doc_ids":null} | 12 | 13 | 2 | 成功 | D0099:0, D0128:0, D0099:3, D0099:2, D0099:4, D0128:18, D0099:5, D0128:25, D0099:1, D0128:21, D0128:3, D0128:2 |
| 2 | 1 | search_chunks {"query":"occlusion boundary handling computational cost rendering","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0099:3, D0099:2, D0099:0, D0099:8, D0099:12, D0099:4, D0099:11, D0099:17, D0128:0, D0099:16, D0128:18, D0128:1 |
| 3 | 2 | read_chunks {"raw":"{\"doc_id\": \"D0128\", \"ordinals\": 3, 4, 5, 6}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | — |
| 4 | 2 | read_chunks {"raw":"{\"doc_id\": \"D0099\", \"ordinals\": 1, 8, 9, 10}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | — |
| 5 | 3 | search_chunks {"doc_ids":["D0128"],"query":"occlusion depth ordering closed form ray termination","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0128:6, D0128:25, D0128:1, D0128:0, D0128:4, D0128:5, D0128:27, D0128:29, D0128:36, D0128:21, D0128:38, D0128:3 |
| 6 | 3 | search_chunks {"doc_ids":["D0128"],"query":"rendering algorithm splatting depth map silhouette gradient","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0128:0, D0128:18, D0128:1, D0128:16, D0128:15, D0128:2, D0128:39, D0128:3, D0128:12, D0128:17, D0128:10, D0128:25 |

judge reasoning：

> The generated answer accurately captures the key distinctions and computational trade-offs between the non-differentiable sampling/rasterize-then-splat approach and the algebraic surface/fuzzy metaball approach, fully matching the gold answers' core meaning.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> The rasterize-then-splat method uses non-differentiable rasterization for sampling followed by differentiable splatting to handle occlusions, making it independent of mesh complexity but requiring multiple rendering passes. In contrast, the algebraic surface approach uses fuzzy metaballs with order-independent transparency, handling occlusions through weighted averaging of intersections, making it faster but less precise. This fundamental difference leads to a trade-off between accuracy and speed - the first method provides higher quality derivatives at occlusion boundaries but requires more computation, while the second method sacrifices some rendering fidelity for significantly faster CPU performance.

**naive 最终答案**

> **Non-differentiable sampling (RtS — "Rasterize-then-Splat"):** Occlusion boundaries are handled by first sampling the surface with non-differentiable rasterization (Z-buffer, depth peeling, Marching Cubes), then applying differentiable, depth-aware multi-layer Gaussian splatting; splats are composited into front/behind/coincident buffers (S−, S0, S+) to correctly resolve occlusions, including self-occlusions. Computational implications: no shape processing or custom derivative code; cost is bounded by the number of pixels (fixed grid), not surface/mesh complexity; all derivatives via automatic differentiation; simple to implement, but requires closed-form surface evaluation.
> 
> **Algebraic surfaces (Fuzzy Metaballs):** Occlusion (the hidden-surface problem) is resolved analytically/smoothly by blending each ray's Gaussian intersections as a weighted average (OIT-style, O(N) Gaussian evaluations per ray); depth maps and silhouettes are smooth and defined everywhere, so every pixel has a non-zero relationship with all geometry, preserving gradient flow even far from initialization. Computational implications: approximate (sacrifices fidelity), very fast — forward passes 5× and backward passes 30× faster than mesh-based renderers, CPU-friendly (60 lines of JAX, no custom CUDA), but ray-intersection choice affects cost/stability (linear fastest; quadratic 50% slower but most accurate; cubic 2× slower and numerically unstable, producing NaNs).
> 
> In short: sampling methods resolve occlusions discretely then splat differentiably (cost scales with pixels, accurate but more complex), while algebraic-surface methods blend intersections continuously (cheap and robust gradients, but approximate fidelity).

**community 最终答案**

> The two methods resolve occlusion boundaries in fundamentally different ways:
> 
> **Non-differentiable sampling (RtS, D0099):** Occlusion is resolved by a conventional non-differentiable rasterization pass (Z-buffering/depth peeling), then differentiable depth-aware multi-layer splatting produces smooth derivatives at occlusion boundaries. Because the differentiable part is bounded by pixel count rather than surface complexity, cost is independent of mesh size, requires no shape processing, no edge sampling, and no custom CUDA kernels, and works with plain autodiff.
> 
> **Algebraic surfaces (Fuzzy Metaballs, D0128):** Occlusion is avoided rather than resolved—every ray always intersects every Gaussian, and ray termination is computed in closed form, with surface "fuzziness" (smooth, depth-weighted blending of intersections) substituting for hard occlusion boundaries. Every pixel has a non-zero gradient relation to all geometry (even occluded/behind-camera parts), giving smooth, well-defined gradients everywhere.
> 
> **Computational implications:** RtS's cost scales with pixels, not mesh/edge count, and is fast for large meshes (within 2× of nvdiffrast without custom kernels), but assumes a single surface per pixel. Algebraic surfaces compute intersections in closed form (no ray marching, edge sampling, or mesh processing), enabling fast CPU runtimes—forward passes 5× faster and backward passes 30× faster than mesh-based renderers—and low-latency CPU use; the trade-off is deliberately sacrificing rendering fidelity for speed and gradient quality.

</details>

<a id="case-mdaqa-70"></a>

### mdaqa:70 — 评分与执行路径对照

**问题：** What are the key differentiators in how these rendering approaches handle the balance between gradient quality and computational efficiency across different hardware contexts?

**score：4→4（Δ+0）；rounds：5→3（Δ-2）。**

工具安排：naive 为第1轮2次、第2轮2次、第3轮2次、第4轮1次；community 为第1轮2次、第2轮2次。最终回答另占一轮。

轮次减少 2，工具总数 7→4、错误 1→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 42→25、文档 overview 11→33；工具结果字符数 133,166→112,899，QA token 120,703→59,325。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/34060671fc9b4d94bc071e2e32d0f965.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/b49271b493c5403688d442616785ce2b.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"rendering approaches gradient quality computational efficiency hardware","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0128:1, D0099:2, D0128:2, D0128:0, D0099:3, D0128:18, D0128:5, D0099:17, D0030:10, D0097:4, D0099:20, D0099:23 |
| 2 | 1 | search_chunks {"query":"gradient quality vs computational efficiency different hardware contexts","search_mode":"vector","doc_ids":null} | 12 | 6 | 0 | 成功 | D0014:0, D0128:1, D0131:33, D0099:12, D0083:7, D0050:1, D0024:0, D0113:34, D0050:7, D0099:20, D0083:41, D0099:4 |
| 3 | 2 | read_chunks {"raw":"{\"doc_id\": \"D0099\", \"ordinals\": 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | — |
| 4 | 2 | search_chunks {"doc_ids":null,"query":"differentiable renderer CPU GPU gradient quality speed trade-off SoftRasterizer Pulsar PyTorch3D","search_mode":"hybrid"} | 12 | 1 | 0 | 成功 | D0128:1, D0128:22, D0128:2, D0128:0, D0099:21, D0099:2, D0051:0, D0099:0, D0128:10, D0128:17, D0099:19, D0128:36 |
| 5 | 3 | read_chunks {"doc_id":"D0128","ordinals":[10,11,12,13]} | 4 | 0 | 0 | 成功 | D0128:10, D0128:11, D0128:12, D0128:13 |
| 6 | 3 | read_chunks {"doc_id":"D0099","ordinals":[1,3,4,5]} | 4 | 0 | 0 | 成功 | D0099:1, D0099:3, D0099:4, D0099:5 |
| 7 | 4 | read_chunks {"doc_id":"D0099","ordinals":[6,7,8,9,10,11,12,13]} | 8 | 0 | 0 | 成功 | D0099:6, D0099:7, D0099:8, D0099:9, D0099:10, D0099:11, D0099:12, D0099:13 |

judge reasoning：

> The generated answer accurately captures the core differentiators from the gold answers, including both the rasterize-then-splat and algebraic surface approaches, their trade-offs, and the specific CPU/GPU performance implications.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"rendering approaches gradient quality computational efficiency hardware","search_mode":"hybrid","doc_ids":null} | 12 | 26 | 4 | 成功 | D0128:1, D0099:2, D0128:2, D0128:0, D0099:3, D0128:18, D0128:5, D0099:17, D0030:10, D0097:4, D0099:20, D0099:23 |
| 2 | 1 | search_chunks {"query":"gradient quality balance computational efficiency different hardware contexts rendering","search_mode":"vector","doc_ids":null} | 12 | 7 | 1 | 成功 | D0128:1, D0099:20, D0128:0, D0099:12, D0099:2, D0014:0, D0128:18, D0099:0, D0099:19, D0099:23, D0128:22, D0099:4 |
| 3 | 2 | read_chunks {"doc_id":"D0128","ordinals":[3,4,5,6]} | 4 | 0 | 0 | 成功 | D0128:3, D0128:4, D0128:5, D0128:6 |
| 4 | 2 | read_chunks {"doc_id":"D0099","ordinals":[1,5,6,7]} | 4 | 0 | 0 | 成功 | D0099:1, D0099:5, D0099:6, D0099:7 |

judge reasoning：

> The response correctly identifies both approaches' core tradeoffs—rasterize-then-splat for gradient accuracy/occlusion boundaries and algebraic surface for CPU-oriented speed with 5x/30x gains—and adds consistent context without contradicting the gold answers.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> The rasterize-then-splat approach prioritizes gradient accuracy through careful handling of occlusion boundaries using multi-layer splatting, but requires more computational overhead due to multiple rendering passes. It's implemented in standard frameworks for both CPU/GPU but optimized for GPU use. The algebraic surface method explicitly sacrifices some rendering fidelity for computational simplicity, focusing on CPU performance through closed-form solutions and avoiding expensive operations, making it 5x faster for forward passes and 30x faster for backward passes on CPU compared to mesh-based methods. This reflects fundamentally different priorities in the accuracy-speed trade-off.

**naive 最终答案**

> Based on the context, the key differentiators are:
> 
> **Approach to the trade-off:**
> - **Fuzzy Metaballs (D0128)** deliberately sacrifices rendering fidelity for computational simplicity and speed, prioritizing high-quality, smooth gradients that solve vision problems. It uses a compact implicit representation where every pixel has a non-zero gradient relation to all geometry.
> - **RtS / Rasterize-then-Splat (D0099)** keeps a conventional (non-differentiable) forward rasterization pass and adds differentiable, depth-aware multi-layer splatting, so gradient cost is bounded by pixels, not mesh complexity. This yields high-quality derivatives at occlusion boundaries without custom gradient code.
> - **Accurate light-transport renderers** are slower but simulate subtle phenomena; **volume rendering (NeRF)** is naturally differentiable but requires expensive ray marching; **SoftRasterizer/PyTorch3D** need costly closest-point queries/spatial binning and don't scale to large meshes; **Redner** costs grow with occluding-edge count; **nvdiffrast** is fastest but needs tightly optimized, GPU-specific CUDA kernels.
> 
> **Hardware context:**
> - **Fuzzy Metaballs** targets **CPU** runtimes (implemented in JAX with CPU/GPU backends), because many robotics platforms lack a GPU or have it occupied; it is 5× faster forward and 30× faster backward than mesh renderers on CPU.
> - **RtS** needs **no custom CUDA kernels**, so it is portable (implemented via automatic differentiation, e.g., TensorFlow Graphics), yet still within 2× of nvdiffrast and up to 20× faster than PyTorch3D/Redner on GPU (V100).
> - **nvdiffrast** achieves excellent GPU performance but requires **specific GPU hardware** and is hard to adapt to new systems; most other differentiable renderers focus on GPU performance, while Fuzzy Metaballs explicitly prioritizes CPU-friendly operation.

**community 最终答案**

> The key differentiators across the rendering approaches in context:
> 
> **Fuzzy Metaballs (D0128)** — Deliberately trades fidelity for computational simplicity and speed: it produces smooth, high-quality gradients (every pixel has a non-zero gradient relation to all geometry) but inexact/approximate images. It's CPU-focused (JAX supports CPU/GPU backends), since GPUs are often unavailable or occupied on robotics platforms; closed-form ray termination and explicit algebraic form make gradients cheap (forward 5× and backward 30× faster than mesh-based differentiable renderers).
> 
> **RtS / Rasterize-then-Splat (D0099)** — Balances quality and efficiency by keeping the forward pass non-differentiable (conventional Z-buffer rasterization) and making only the image-space splatting differentiable, so all derivatives come from automatic differentiation with no custom CUDA kernels. Cost is bounded by pixel count, not surface complexity, making it portable across hardware (unlike nvdiffrast, which needs tightly optimized, specific-GPU CUDA kernels that are hard to adapt to new systems). It delivers high-quality derivatives (accurate at occlusion boundaries, matching finite differences) at speeds within 2× of nvdiffrast, and converts volume NeRF rendering to surface rendering for a 128× speedup at only ~0.3 PSNR loss.
> 
> **Comparison anchors** — PyTorch3D/SoftRasterizer need spatial binning and don't scale to large meshes; Redner's edge-sampling cost grows with mesh edge count; nvdiffrast achieves excellent speed but is tied to specific GPU hardware. Volume rendering (NeRF) is naturally differentiable but expensive (ray marching), which surface-based approaches avoid by trading a small amount of quality for large efficiency gains.

</details>

<a id="case-mdaqa-72"></a>

### mdaqa:72 — 评分与执行路径对照

**问题：** How do the computational efficiency tradeoffs differ between patch detection-based defenses versus universal adversarial training approaches?

**score：4→4（Δ+0）；rounds：4→3（Δ-1）。**

工具安排：naive 为第1轮2次、第2轮2次、第3轮2次；community 为第1轮2次、第2轮2次。最终回答另占一轮。

轮次减少 1，工具总数 6→4、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 33→33、文档 overview 2→17；工具结果字符数 130,864→130,549，QA token 81,062→61,410。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/91dc2f4c2e164656a5f66b9ad1701648.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/f10f31690d484ca8b0d8ce7bd36e98b6.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"computational efficiency tradeoffs patch detection-based defenses universal adversarial training","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0125:23, D0125:0, D0125:1, D0023:4, D0125:19, D0125:2, D0023:0, D0125:22, D0023:3, D0023:21, D0023:22, D0125:5 |
| 2 | 1 | search_chunks {"query":"patch detection defense computational cost training overhead","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0125:17, D0125:0, D0125:1, D0125:14, D0125:15, D0125:8, D0125:6, D0125:7, D0125:22, D0125:13, D0125:3, D0125:11 |
| 3 | 2 | read_chunks {"doc_id":"D0023","ordinals":[1,2,4,5,6,7]} | 6 | 0 | 0 | 成功 | D0023:1, D0023:2, D0023:4, D0023:5, D0023:6, D0023:7 |
| 4 | 2 | read_chunks {"doc_id":"D0125","ordinals":[16,17]} | 2 | 0 | 0 | 成功 | D0125:16, D0125:17 |
| 5 | 3 | search_chunks {"doc_ids":null,"query":"universal adversarial training Shafahi update network parameters and universal perturbation concurrently overhead","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0023:27, D0023:4, D0023:0, D0023:3, D0023:22, D0023:2, D0023:26, D0023:6, D0023:24, D0023:13, D0125:23, D0023:20 |
| 6 | 3 | search_chunks {"doc_ids":["D0125"],"query":"training time two-stage training accelerate efficiency cost PatchZero detector","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0125:8, D0125:7, D0125:0, D0125:2, D0125:17, D0125:6, D0125:15, D0125:1, D0125:14, D0125:16, D0125:12, D0125:23 |

judge reasoning：

> The generated answer accurately captures the core computational efficiency tradeoff—patch detection is fast at inference with a lightweight detector, while universal adversarial training incurs the main overhead during training—and the peripheral accuracy tradeoff omission does not undermine the primary answer.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"computational efficiency tradeoffs patch detection defenses universal adversarial training","search_mode":"hybrid","doc_ids":null} | 12 | 17 | 3 | 成功 | D0125:0, D0023:4, D0125:1, D0125:23, D0125:19, D0125:2, D0023:0, D0023:21, D0023:3, D0125:5, D0023:24, D0023:22 |
| 2 | 1 | search_chunks {"query":"universal adversarial patch defense detection computationally efficient","search_mode":"vector","doc_ids":null} | 12 | 0 | 0 | 成功 | D0125:0, D0125:23, D0125:22, D0125:1, D0023:22, D0023:24, D0125:20, D0023:4, D0125:19, D0125:21, D0023:1, D0125:2 |
| 3 | 2 | search_chunks {"doc_ids":["D0125"],"query":"efficiency overhead cost inference training PatchZero patch detection","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0125:17, D0125:0, D0125:15, D0125:1, D0125:2, D0125:8, D0125:6, D0125:7, D0125:14, D0125:12, D0125:16, D0125:23 |
| 4 | 2 | search_chunks {"doc_ids":["D0023"],"query":"efficiency compute shared perturbation mini-batch expensive overhead training","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0023:9, D0023:7, D0023:4, D0023:13, D0023:20, D0023:8, D0023:17, D0023:0, D0023:10, D0023:3, D0023:12, D0023:11 |

judge reasoning：

> The generated answer accurately captures the core distinction: patch detection places computational burden at inference with modest overhead while universal adversarial training shifts the cost to training, and it correctly notes PatchZero's clean accuracy preservation versus the robustness-accuracy tradeoff in universal adversarial training, with additional details that are consistent with the gold answer.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Patch detection approaches like PatchZero require only one forward pass through the detector followed by zeroing, making them computationally efficient during inference. In contrast, universal adversarial training requires significant computational overhead during training to generate shared perturbations, though inference is fast. PatchZero maintains clean accuracy while universal adversarial training faces an inherent tradeoff between robustness and accuracy that must be carefully balanced through techniques like loss thresholding.

**naive 最终答案**

> Based on the context:
> 
> **Patch detection-based defense (e.g., PatchZero):** The main computational cost is at inference — it adds a pixel-level patch detector (PSPNet/ResNet-50) to the pipeline. Although it has more parameters (72.2M vs 25.5M), it is far more efficient than certified alternatives: ~60x faster inference (12 min vs 758 min for PatchCleanser on ImageNet) and ~2x lower GPU memory (3.33GB vs 7.32GB), with "moderate overhead." It requires no retraining of the downstream classifier/detector. Training uses a two-stage adversarial scheme (DO attacks then BPDA adaptive attacks) that *accelerates* training and improves robustness.
> 
> **Universal adversarial training (e.g., Shafahi et al.):** The efficiency issue is in training — re-computing a universal perturbation anew for every mini-batch is "prohibitively expensive." Shafahi et al. reduce this overhead by updating network parameters and the universal perturbation *concurrently*, so no separate per-batch perturbation optimization is needed (though it's unclear if the incrementally updated perturbation tracks weight changes well). Related shared adversarial training computes perturbations on-the-fly per mini-batch at the same compute cost as standard adversarial training (189s vs 3118s/3840s for prior defenses), making it far cheaper than older precomputation-based approaches.
> 
> In short: patch detection trades off inference-time overhead (an extra detector, but fast and low-memory) while universal adversarial training trades off training-time cost (perturbation optimization), which concurrent/shared perturbation updates make cheap but with open questions about perturbation tracking.

**community 最终答案**

> The two approaches place their computational cost in different phases:
> 
> **Patch detection–based defense (PatchZero):** Cost is mainly at *inference* — it adds a pixel-level patch detector (PSPNet/ResNet-50, ~72.2M params) to the pipeline. This overhead is moderate: ~12 min inference on ImageNet vs 8 min for the undefended ResNet-50 and 758 min for PatchCleanser, with 3.33GB GPU memory (2× less than PatchCleanser). Crucially, it requires **no retraining of the downstream classifier/detector**, and its two-stage adversarial training only trains the detector, with the scheme specifically designed to *accelerate training in the early stages*. So training cost is confined to the detector, while inference carries moderate extra cost.
> 
> **Universal adversarial training (shared adversarial training):** Cost is mainly at *training* — adversarial training must generate perturbations every mini-batch. Naively re-computing universal perturbations per mini-batch is **prohibitively expensive** (and direct universal-risk evaluation needs large m). The efficiency fix is shared adversarial training: splitting the mini-batch into heaps and computing d/s shared perturbations, which has *essentially the same cost as standard PGD adversarial training* (~189 s/epoch vs 3118 s and 3840 s/epoch for prior universal defenses). The tradeoff is that the *model itself* must be adversarially retrained (with an accuracy-on-clean-data tradeoff), and the cost persists through training rather than at inference.
> 
> In short: detection-based defenses shift cost to inference with low training burden and no downstream retraining; universal adversarial training shifts cost to training (which is where shared perturbation computation brings efficiency gains) but requires retraining the model and sacrificing some clean accuracy.

</details>

<a id="case-mdaqa-73"></a>

### mdaqa:73 — 评分与执行路径对照

**问题：** What are the key differences in how these defense methods handle the transferability of adversarial attacks?

**score：1→2（Δ+1）；rounds：5→3（Δ-2）。**

工具安排：naive 为第1轮1次、第2轮2次、第3轮2次、第4轮1次；community 为第1轮2次、第2轮3次。最终回答另占一轮。

轮次减少 2，工具总数 6→5、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 56→45、文档 overview 5→27；工具结果字符数 160,373→159,773，QA token 126,959→73,868。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

<details>
<summary>展开 judge 所提实体的字面证据核对</summary>

| 实体/术语 | naive工具中首次匹配 | naive答案 | community工具中首次匹配 | community答案 |
|---|---|---|---|---|
| PatchZero | 轮1/调用1/D0125:0 | 出现 | 轮1/调用1/D0125:0 | 出现 |

这里只检查指定字面串及字母数字边界，不评判上下文是否在讨论同一事实；未匹配不排除同义表述，出现也不代表正确采用。它用于区分“可能未召回”和“已出现但未展开”的复核入口，不能自动判定因果。

</details>

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/5d6afe4835324ceb9c7506e1c499e0c0.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/1eece98bc16a40e8aa16e4ef2849c505.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"defense methods transferability of adversarial attacks","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0125:0, D0035:23, D0125:22, D0125:1, D0125:23, D0023:0, D0004:12, D0125:2, D0035:0, D0023:25, D0035:26, D0023:14 |
| 2 | 2 | search_chunks {"doc_ids":["D0035"],"query":"transferability transfer attacks black-box","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0035:27, D0035:23, D0035:15, D0035:62, D0035:61, D0035:16, D0035:17, D0035:13, D0035:25, D0035:63, D0035:0, D0035:19 |
| 3 | 2 | search_chunks {"doc_ids":["D0125"],"query":"transferability transfer attack","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0125:2, D0125:15, D0125:16, D0125:17, D0125:14, D0125:21, D0125:10, D0125:13, D0125:12, D0125:4, D0125:3, D0125:5 |
| 4 | 3 | search_chunks {"doc_ids":["D0023"],"query":"transferability attacks generated for other models","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0023:0, D0023:22, D0023:32, D0023:1, D0023:25, D0023:24, D0023:29, D0023:23, D0023:21, D0023:27, D0023:26, D0023:17 |
| 5 | 3 | search_chunks {"doc_ids":["D0004"],"query":"transferability black-box adversarial examples","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0004:1, D0004:0, D0004:7, D0004:9, D0004:11, D0004:12, D0004:5, D0004:6, D0004:2, D0004:3, D0004:10, D0004:8 |
| 6 | 4 | search_chunks {"doc_ids":null,"query":"adversarial examples transferability more difficult transfer attacks","search_mode":"hybrid"} | 12 | 1 | 0 | 成功 | D0125:0, D0035:63, D0023:25, D0004:0, D0023:0, D0125:2, D0125:1, D0023:23, D0029:0, D0023:1, D0125:22, D0029:3 |

judge reasoning：

> The generated answer omits the gold answer's central facts—PatchZero's two-stage adaptive training and universal adversarial training's explicit shared-perturbation mechanism—and instead emphasizes cross-model transfer and defense generalization, so it does not adequately match the gold.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"defense methods transferability adversarial attacks","search_mode":"hybrid","doc_ids":null} | 12 | 27 | 4 | 成功 | D0125:0, D0125:22, D0035:23, D0125:1, D0125:23, D0035:26, D0035:0, D0023:0, D0125:2, D0023:22, D0023:25, D0023:4 |
| 2 | 1 | search_chunks {"query":"defense transferability of adversarial examples","search_mode":"vector","doc_ids":null} | 12 | 0 | 0 | 成功 | D0023:22, D0023:24, D0035:25, D0035:23, D0035:0, D0023:26, D0004:12, D0004:11, D0035:19, D0023:25, D0023:27, D0125:19 |
| 3 | 2 | search_chunks {"doc_ids":["D0035"],"query":"transfer attacks transferability black-box","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0035:27, D0035:15, D0035:23, D0035:62, D0035:61, D0035:16, D0035:17, D0035:13, D0035:25, D0035:63, D0035:0, D0035:19 |
| 4 | 2 | search_chunks {"doc_ids":["D0125"],"query":"transfer transferability attack types shapes generalization","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0125:2, D0125:1, D0125:15, D0125:17, D0125:16, D0125:14, D0125:13, D0125:10, D0125:21, D0125:4, D0125:12, D0125:3 |
| 5 | 2 | search_chunks {"doc_ids":["D0023"],"query":"transferability transfer universal perturbation other models","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0023:2, D0023:3, D0023:27, D0023:4, D0023:0, D0023:34, D0023:20, D0023:1, D0023:22, D0023:29, D0023:24, D0023:21 |

judge reasoning：

> The generated answer correctly captures the universal/shared adversarial training part, but it mischaracterizes PatchZero by focusing on defense transfer across patch attack types/shapes instead of the gold answer's key mechanism of two-stage training against adaptive/BPDA attacks.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> PatchZero focuses on making the patch detector itself robust to adaptive attacks through two-stage training, first training on direct attacks then reinforcing against BPDA attacks. Universal adversarial training instead handles transferability by explicitly training on shared perturbations across mini-batches, making the model robust to perturbations that must transfer across multiple inputs. This shared perturbation approach provides better generalization against universal attacks compared to per-instance adversarial training.

**naive 最终答案**

> Based on the context, the key differences in handling attack transferability are:
> 
> - **k-WTA (D0035)** actively **reduces attack transferability**: it is harder to transfer-attack k-WTA networks with adversarial examples from other models, and harder to use k-WTA-generated examples to attack other models. Its adversarial examples are described as "disjoint" from ReLU networks' examples despite architectural similarity, and it is more robust than ReLU under the strongest black-box transfer attacks (e.g., across independently trained versions of the same model).
> 
> - **PatchZero (D0125)** instead emphasizes the **transferability/generalization of the defense itself**: its patch detector transfers across different patch shapes (square/diamond/octagon/rectangle) and across attack types (MPGD, MAPGD, MCW), i.e., training on one attack defends effectively against others. It does not frame robustness in terms of blocking cross-model attack transfer.
> 
> - **Shared adversarial training (D0023)** and **HotFlip (D0004)** do not explicitly address cross-model attack transferability; their focus is robustness against universal/per-input perturbations (SAT) and adversarial training on generated examples (HotFlip), respectively.
> 
> So the main difference is: k-WTA targets suppressing transfer-based black-box attacks between models, whereas PatchZero leverages transferability of its defense to unseen shapes/attacks; the other methods don't directly address attack transferability.

**community 最终答案**

> Based on the context:
> 
> - **k-WTA (D0035)**: Handles transferability by breaking it in both directions — its C0-discontinuous activations make it harder for adversarial examples from other models to transfer **into** k-WTA networks, and harder for k-WTA examples to attack other models (its adversarial examples are "disjoint" from ReLU networks' despite similar architecture). It is also more robust than ReLU under transfer attacks across two versions of the same model.
> 
> - **PatchZero (D0125)**: Handles transferability in the opposite sense — its **defense** transfers across attack types and shapes: a detector trained on one patch attack (MPGD, MAPGD, or MCW) defends against the others, and one trained on square patches generalizes to diamond/octagon/rectangle patches.
> 
> - **Shared adversarial training (D0023)**: Addresses universal (input-agnostic) perturbations — attacks that transfer across many inputs. Standard adversarial training already proves quite effective against these, and SAT improves robustness against them by sharing perturbations within mini-batches, though it trades off robustness against image-specific perturbations.
> 
> In short: k-WTA suppresses attack transferability between models; PatchZero's robustness itself transfers across attack variations; SAT targets attacks that transfer across many inputs rather than across models.

</details>

<a id="case-mdaqa-75"></a>

### mdaqa:75 — 评分与执行路径对照

**问题：** How do linear probing and transferability estimation methods compare in their ability to predict language model performance without full fine-tuning?

**score：4→4（Δ+0）；rounds：2→3（Δ+1）。**

工具安排：naive 为第1轮2次；community 为第1轮2次、第2轮2次。最终回答另占一轮。

轮次增加 1，工具总数 2→4、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 20→27、文档 overview 10→25；工具结果字符数 65,723→118,221，QA token 21,307→60,138。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/ea3a99f9df0549c1b1efd234ba1ac0d7.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/a112f3d79bfa4d289d31424ab8a832af.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"linear probing transferability estimation predict language model performance without fine-tuning","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0130:0, D0123:0, D0130:20, D0130:15, D0113:0, D0123:1, D0130:1, D0130:5, D0123:2, D0113:1, D0062:24, D0123:10 |
| 2 | 1 | search_chunks {"query":"transferability estimation methods zero-shot performance prediction","search_mode":"hybrid","doc_ids":null} | 12 | 6 | 0 | 成功 | D0130:0, D0130:20, D0130:15, D0130:14, D0134:29, D0065:30, D0107:0, D0139:30, D0113:1, D0119:20, D0130:22, D0044:18 |

judge reasoning：

> The generated answer accurately captures the key facts and tradeoffs from the gold answers, including the specific accuracy ranges for linear probing and LogME, while adding consistent supporting details.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"linear probing transferability estimation predict language model performance without full fine-tuning","search_mode":"hybrid","doc_ids":null} | 12 | 24 | 3 | 成功 | D0130:0, D0123:0, D0113:0, D0130:15, D0123:1, D0130:20, D0130:5, D0130:1, D0130:22, D0123:10, D0130:10, D0113:23 |
| 2 | 1 | search_chunks {"query":"linear probing vs transferability estimation methods comparison","search_mode":"hybrid","doc_ids":null} | 12 | 1 | 0 | 成功 | D0113:0, D0130:20, D0130:15, D0123:2, D0130:0, D0130:1, D0123:10, D0123:19, D0123:0, D0130:14, D0113:1, D0057:14 |
| 3 | 2 | search_chunks {"doc_ids":["D0130"],"query":"probing compared to transferability measures ranking","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0130:1, D0130:20, D0130:15, D0130:0, D0130:19, D0130:14, D0130:3, D0130:16, D0130:4, D0130:2, D0130:17, D0130:6 |
| 4 | 2 | read_chunks {"doc_id":"D0123","ordinals":[3,4,5]} | 3 | 0 | 0 | 成功 | D0123:3, D0123:4, D0123:5 |

judge reasoning：

> The generated answer accurately captures the core facts and tradeoffs from the gold answer (DEPPROBE 79-89% for dependency parsing, LogME 71% broader, task-specific vs generalizable) with additional consistent context, so it merits a perfect score.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Both approaches show strong predictive power but with different tradeoffs: Linear probing achieves 79-89% accuracy in predicting relative model performance for dependency parsing, while transferability estimation through LogME achieves 71% accuracy across a broader range of tasks. Linear probing provides more interpretable insights into model capabilities but is task-specific, whereas transferability estimation is more generally applicable but provides less explanatory power about why certain models perform better.

**naive 最终答案**

> Both approaches can predict LM performance without full fine-tuning, but they differ in method and accuracy:
> 
> - **Transferability estimation (LogME)**: Applied to frozen embeddings, it correlates positively with final performance in 94% of setups and selects the better encoder 71% of the time, but predictive accuracy drops noticeably after full fine-tuning because frozen representations misalign with fine-tuned ones. LEEP, an alternative measure, achieved only low, unintuitive correlations on NLP.
> 
> - **Linear probing (DEPPROBE)**: Uses lightweight linear probes on frozen (middle-layer) embeddings to predict performance—e.g., for dependency parsing it identifies the better final LM 79–89% of the time (94% for best transfer-language selection, Pearson r up to 0.97, Kendall τ up to 0.88), using orders of magnitude fewer parameters (51k–190k vs 14M–583M) and far less compute (~15 min vs ~1 hour) than a full fine-tuned parser.
> 
> Overall, probing and transferability measures both yield strong rank correlations with final performance without fine-tuning, though probing can be more compute-efficient, while LogME's accuracy also degrades after full fine-tuning.

**community 最终答案**

> Based on the documents:
> 
> **Linear probing (DEPPROBE)** and **transferability estimation (LogME)** are both lightweight methods that predict LM performance from frozen, untuned embeddings without full fine-tuning, but they differ in scope and accuracy:
> 
> - **LogME (transferability estimation)**: Correlates positively with final LM performance in 94% of setups and picks the better encoder 71% of the time across classification and structured prediction tasks. Its predictive power is higher on frozen embeddings and drops after full fine-tuning; it offers an ~86× speedup over fine-tuning.
> 
> - **DEPPROBE (linear probing)**: Extends ranking to graphical/structured prediction tasks (dependency parsing) that transferability measures had not covered, computing the actual target metric (LAS) from frozen embeddings. It selects the better final model 79% of the time (89% excluding the RemBERT outlier) and uses orders of magnitude fewer trainable parameters (e.g., 190k vs 583M), training in minutes versus hours.
> 
> In short, both efficiently rank LMs without fine-tuning, but probing is tailored to and most predictive for structured-prediction tasks, while LogME generalizes across classification/structured prediction; both can be misled when frozen representations misalign with post-fine-tuning ones (e.g., RemBERT).

</details>

<a id="case-mdaqa-76"></a>

### mdaqa:76 — 评分与执行路径对照

**问题：** How does the computational efficiency of different model selection approaches compare relative to their predictive accuracy?

**score：2→2（Δ+0）；rounds：5→3（Δ-2）。**

工具安排：naive 为第1轮2次、第2轮2次、第3轮2次、第4轮2次；community 为第1轮2次、第2轮2次。最终回答另占一轮。

轮次减少 2，工具总数 8→4、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 47→43、文档 overview 17→57；工具结果字符数 156,823→180,044，QA token 147,338→76,845。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/27452e017ee7450ea1e6171e6ac2cefe.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/c7a0ac36f346427abc187872a96c75c1.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"computational efficiency of model selection approaches predictive accuracy","search_mode":"hybrid","doc_ids":null} | 12 | 6 | 0 | 成功 | D0110:5, D0110:2, D0110:4, D0037:1, D0097:15, D0110:23, D0110:0, D0082:12, D0093:21, D0037:0, D0113:23, D0093:0 |
| 2 | 1 | search_chunks {"query":"model selection computational cost accuracy comparison","search_mode":"vector","doc_ids":null} | 12 | 5 | 0 | 成功 | D0037:0, D0062:20, D0093:32, D0037:15, D0037:1, D0037:18, D0037:19, D0062:19, D0083:42, D0140:16, D0076:18, D0010:22 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"model selection approaches compare computational cost and predictive accuracy trade-off","search_mode":"hybrid"} | 12 | 4 | 0 | 成功 | D0037:1, D0062:0, D0111:26, D0037:0, D0100:16, D0100:2, D0110:23, D0093:0, D0140:15, D0100:14, D0123:19, D0023:3 |
| 4 | 2 | search_chunks {"doc_ids":null,"query":"choosing between model selection methods efficiency versus accuracy","search_mode":"vector"} | 12 | 2 | 0 | 成功 | D0093:0, D0110:0, D0110:6, D0038:0, D0110:2, D0082:13, D0021:13, D0123:19, D0093:32, D0110:23, D0110:3, D0093:21 |
| 5 | 3 | read_chunks {"doc_id":"D0113","ordinals":[0,1,22,23]} | 4 | 0 | 0 | 成功 | D0113:0, D0113:1, D0113:22, D0113:23 |
| 6 | 3 | read_chunks {"doc_id":"D0123","ordinals":[0,1,2]} | 3 | 0 | 0 | 成功 | D0123:0, D0123:1, D0123:2 |
| 7 | 4 | read_chunks {"doc_id":"D0113","ordinals":[24,25]} | 2 | 0 | 0 | 成功 | D0113:24, D0113:25 |
| 8 | 4 | read_chunks {"doc_id":"D0123","ordinals":[3,4,5,6]} | 4 | 0 | 0 | 成功 | D0123:3, D0123:4, D0123:5, D0123:6 |

judge reasoning：

> The generated answer correctly captures the general efficiency/accuracy tradeoff and mentions DepProbe's 94% transfer accuracy, but it omits LogME's 86x speedup and the key tradeoff between task-specificity and general applicability, and gives incorrect parameter counts (190k vs. 583M rather than 127k vs. 183M), so it is only partially correct.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"computational efficiency model selection approaches predictive accuracy","search_mode":"hybrid","doc_ids":null} | 12 | 23 | 3 | 成功 | D0110:5, D0110:2, D0110:4, D0140:5, D0140:8, D0037:1, D0097:15, D0110:23, D0082:12, D0110:0, D0093:21, D0037:0 |
| 2 | 1 | search_chunks {"query":"model selection computational cost accuracy comparison","search_mode":"hybrid","doc_ids":null} | 12 | 6 | 1 | 成功 | D0037:1, D0037:0, D0076:18, D0140:16, D0098:20, D0062:20, D0062:19, D0082:13, D0062:0, D0140:5, D0037:15, D0123:12 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"model selection method compare accuracy efficiency ranking without fine-tuning","search_mode":"hybrid"} | 12 | 28 | 4 | 成功 | D0130:1, D0130:10, D0123:0, D0130:15, D0082:9, D0082:13, D0130:6, D0082:8, D0130:0, D0082:14, D0082:10, D0082:2 |
| 4 | 2 | search_chunks {"doc_ids":["D0123"],"query":"efficiency accuracy comparison model ranking DEPPROBE fine-tuned parser","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0123:0, D0123:5, D0123:2, D0123:1, D0123:10, D0123:4, D0123:8, D0123:11, D0123:28, D0123:9, D0123:29, D0123:3 |

judge reasoning：

> The generated answer captures several efficiency/speedup facts but misses the gold's key tradeoff of task-specificity vs general applicability and frames it as computational cost vs accuracy, so it is only partially correct.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Linear probing approaches like DepProbe use 127k parameters compared to 183M for full fine-tuning, while LogME provides an 86x speedup over fine-tuning. Both methods maintain strong predictive power despite their efficiency - DepProbe achieves 94% accuracy for parsing transfer while LogME maintains positive correlation with final performance in 94% of evaluated scenarios. The key tradeoff is between task-specificity and general applicability rather than computational cost.

**naive 最终答案**

> Based on the context, model selection via lightweight approaches trades only slightly on accuracy for large efficiency gains:
> 
> - **Lightweight linear probing (DEPPROBE)** uses three orders of magnitude fewer trainable parameters (190k vs. 583M) and trains in minutes instead of hours, yet predicts the best-performing model the majority of the time — selecting the better final model 79% of the time across 46 LM-language pairs (89% excluding a RemBERT outlier), and the best transfer source 94% of the time in a related study. Its O(n²) decoding also beats O(n³) dynamic programming.
> - **Frozen-encoder approaches** cut inference FLOPs by an order of magnitude (~34 vs ~430 GFLOPs) while nearly matching full fine-tuning accuracy (88.4% vs 90.5%), and surpassing distillation.
> - **Full end-to-end fine-tuning** is the most accurate (90.7%) but the least computationally efficient; the efficiency/accuracy gap is small enough that cheap probing is a viable alternative, though outliers (e.g., RemBERT) can be mis-ranked despite performing best after fine-tuning.

**community 最终答案**

> Different model selection approaches trade computational cost against predictive accuracy:
> 
> - **Full model fine-tuning/training** (e.g., training a full parser per candidate): most accurate as the gold standard, but computationally infeasible/wasteful—training each candidate is expensive (hours; BAP uses 14M–583M trainable parameters).
> - **Lightweight transferability estimation (LogME)**: offers an ~86× speedup over full fine-tuning, and its scores correlate positively with final LM performance in 94% of setups, choosing the better encoder 71% of the time. However, its predictive power drops noticeably after full model fine-tuning because frozen representations misalign with fine-tuned ones.
> - **Linear probing (DEPPROBE)**: uses orders of magnitude less compute (51k–190k trainable parameters vs. up to 583M; minutes vs. hours) and predicts the best-performing LM 79% of the time (89% excluding the RemBERT outlier), with strong correlations to final parser performance. It occasionally misranks models (e.g., RemBERT, which has little latent dependency information but fine-tunes best).
> 
> So lightweight methods achieve high predictive accuracy at a fraction of the computational cost, but remain less accurate than exhaustive full training, with accuracy varying by task and model (e.g., degrading after full fine-tuning or on decoupled architectures).

</details>

<a id="case-mdaqa-78"></a>

### mdaqa:78 — 评分与执行路径对照

**问题：** How do segment-level and system-level correlations differ between various MT evaluation metrics when evaluating high-quality machine translations?

**score：4→4（Δ+0）；rounds：4→5（Δ+1）。**

工具安排：naive 为第1轮1次、第2轮2次、第3轮2次；community 为第1轮2次、第2轮2次、第3轮2次、第4轮2次。最终回答另占一轮。

轮次增加 1，工具总数 5→8、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 29→34、文档 overview 4→20；工具结果字符数 115,787→182,085，QA token 74,643→139,279。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/66d538470ef54e8e90f9a476ff214458.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/f08f6bba1d244b13904c627ab6080978.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"segment-level system-level correlation MT evaluation metrics high-quality machine translation","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0134:0, D0134:3, D0060:0, D0078:0, D0078:22, D0134:1, D0134:2, D0060:24, D0078:1, D0060:1, D0065:1, D0065:26 |
| 2 | 2 | search_chunks {"doc_ids":null,"query":"segment-level correlation system-level correlation strong MT systems high performing top systems","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0134:0, D0078:0, D0060:0, D0134:1, D0134:3, D0060:12, D0134:2, D0065:13, D0134:4, D0065:26, D0078:1, D0060:18 |
| 3 | 2 | search_chunks {"doc_ids":["D0078"],"query":"correlation with human judgement segment level system level top performing systems","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0078:0, D0078:16, D0078:11, D0078:23, D0078:22, D0078:1, D0078:2, D0078:15, D0078:14, D0078:30, D0078:12, D0078:6 |
| 4 | 3 | search_chunks {"doc_ids":null,"query":"high correlation system level frustratingly low segment level penalty BLEU chrF COMET BERTScore","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0134:0, D0078:11, D0060:0, D0078:12, D0065:13, D0134:3, D0078:10, D0134:15, D0060:13, D0078:13, D0078:0, D0078:30 |
| 5 | 3 | read_chunks {"doc_id":"D0078","ordinals":[10,11,12,13]} | 4 | 0 | 0 | 成功 | D0078:10, D0078:11, D0078:12, D0078:13 |

judge reasoning：

> The generated answer accurately captures the core finding that segment-level correlations are much weaker than system-level correlations, particularly for high-quality MT systems, and includes consistent supporting details without contradicting the gold answers.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"segment-level and system-level correlations MT evaluation metrics high-quality machine translations","search_mode":"hybrid","doc_ids":null} | 12 | 18 | 2 | 成功 | D0134:0, D0078:0, D0060:0, D0134:3, D0078:22, D0060:1, D0134:1, D0134:2, D0065:1, D0060:24, D0060:2, D0078:1 |
| 2 | 1 | search_chunks {"query":"correlation metrics BLEU METEOR TER segment system level","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0134:0, D0060:0, D0065:13, D0134:3, D0060:14, D0078:22, D0060:15, D0060:2, D0078:16, D0029:9, D0060:12, D0134:2 |
| 3 | 2 | read_chunks {"doc_id":"D0065","ordinals":[5,6,7]} | 3 | 0 | 0 | 成功 | D0065:5, D0065:6, D0065:7 |
| 4 | 2 | read_chunks {"doc_id":"D0078","ordinals":[4,5]} | 2 | 0 | 0 | 成功 | D0078:4, D0078:5 |
| 5 | 3 | search_chunks {"doc_ids":null,"query":"metrics high-performing high-quality systems segment-level system-level correlation penalty differences","search_mode":"hybrid"} | 12 | 2 | 0 | 成功 | D0134:0, D0060:0, D0134:3, D0134:1, D0065:13, D0060:12, D0134:2, D0060:1, D0060:2, D0093:15, D0078:0, D0026:11 |
| 6 | 3 | read_chunks {"doc_id":"D0078","ordinals":[7,8,9]} | 3 | 0 | 0 | 成功 | D0078:7, D0078:8, D0078:9 |
| 7 | 4 | search_chunks {"doc_ids":null,"query":"differentiate highest performing MT systems top systems segment level correlation penalty metrics","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0134:0, D0134:1, D0134:2, D0078:0, D0134:3, D0060:0, D0060:2, D0078:30, D0065:26, D0060:13, D0078:1, D0065:1 |
| 8 | 4 | search_chunks {"doc_ids":null,"query":"high accuracy regime reliability automatic metrics correlation human evaluation system-level segment-level","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0060:1, D0060:0, D0134:0, D0134:2, D0078:0, D0134:3, D0060:2, D0078:22, D0060:18, D0134:19, D0060:19, D0078:16 |

judge reasoning：

> The generated answer correctly captures the key finding that metrics correlate better at system level than segment level, especially for high-quality MT systems, and includes consistent additional detail.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Metrics struggle more with segment-level correlation compared to system-level, particularly for high-quality MT systems. While metrics like COMET and UniTE show strong system-level correlations, their segment-level performance deteriorates significantly when evaluating top-performing systems. This indicates current metrics have limited capability in distinguishing quality differences between good translations at a granular level.

**naive 最终答案**

> **System-level vs. segment-level correlations:** Metrics (e.g., BLEU, chrF, BERTScore, COMET) show **high correlation with human judgments at the system level** for some language pairs, but suffer a **considerable performance penalty at the segment level**, where correlations are "frustratingly low" and largely uninformative (Ma et al., 2019). Metrics struggle at segment level despite impressive system-level correlation.
> 
> **For high-quality translations specifically:** All submitted metrics exhibit a **dramatic lack of ability to correctly rank strong (high-quality) MT systems**; correlation calculated with standard references breaks down for top systems. Neural metrics differ: COMET models (especially COMET-RANK) demonstrate **robustness to high-performing systems** and better segment-level correlation than BLEU, chrF, BERTScore, and BLEURT, though even they remain competitive rather than fully resolving the gap. XMoverScore-style metrics outperform BLEU at segment level (e.g., +5.7 points) while achieving only comparable system-level correlation, confirming the general pattern that system-level correlation is consistently higher than segment-level across metrics.

**community 最终答案**

> Based on the context:
> 
> **System-level vs. segment-level:** Most MT metrics (BLEU, chrF, COMET, BERTScore, etc.) show **high correlation with human judgments at the system level**, but suffer a **considerable performance penalty at the segment level** (Ma et al., 2019; Freitag et al., 2021b). Segment-level scores are largely uninformative—metrics struggle to distinguish good from bad translations sentence-by-sentence, and even humans have low inter-annotator agreement at that level.
> 
> **High-quality translations:** In the high-accuracy regime, metric reliability is cast into doubt. When restricting evaluation to the **top-performing (high-quality) systems**, correlations calculated with standard references **break down**—metrics fail to adequately differentiate the highest-performing MT systems (e.g., automated and human evaluation can disagree on the top system). Paraphrased/more diverse references improve correlation for top systems, whereas multi-reference BLEU does not.
> 
> **Metric-specific differences:** Neural metrics like COMET remain competitive when scoring top-performing systems (comparable to BLEU/BERTScore/BLEURT), and reference-free XMoverScore surpasses BLEU by 5.7 correlation points at segment level while achieving comparable system-level correlation.

</details>

<a id="case-mdaqa-79"></a>

### mdaqa:79 — 评分与执行路径对照

**问题：** Why do cross-lingual metrics often fail to properly evaluate translations despite showing high correlation with human judgments?

**score：3→4（Δ+1）；rounds：2→3（Δ+1）。**

工具安排：naive 为第1轮1次；community 为第1轮1次、第2轮2次。最终回答另占一轮。

轮次增加 1，工具总数 1→3、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 12→21、文档 overview 4→18；工具结果字符数 32,816→84,941，QA token 11,560→40,118。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/3e4f3808c8c1448a9d80e78953234a2d.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/03effef904e44c6ca808c01eb3b7379d.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"cross-lingual metrics fail to properly evaluate translations high correlation with human judgments","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0078:0, D0060:0, D0134:0, D0134:24, D0060:2, D0060:1, D0065:0, D0065:22, D0078:1, D0134:2, D0134:23, D0065:20 |

judge reasoning：

> The generated answer correctly captures three of the four key reasons (segment-level unreliability, poor discrimination between good/bad translations, and overly permissive literal translations), but omits the explicit point about failing to detect meaning-changing errors and adequacy issues.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"cross-lingual metrics fail to properly evaluate translations despite high correlation with human judgments","search_mode":"hybrid","doc_ids":null} | 12 | 18 | 2 | 成功 | D0078:0, D0060:0, D0134:0, D0065:0, D0065:3, D0134:2, D0065:22, D0078:1, D0134:23, D0065:20, D0078:25, D0060:18 |
| 2 | 2 | search_chunks {"doc_ids":["D0065"],"query":"reasons for failure cross-lingual metrics semantic mismatch translations","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0065:0, D0065:3, D0065:4, D0065:1, D0065:25, D0065:22, D0065:20, D0065:7, D0065:6, D0065:21, D0065:16, D0065:30 |
| 3 | 2 | read_chunks {"doc_id":"D0065","ordinals":[1,2,3]} | 3 | 0 | 0 | 成功 | D0065:1, D0065:2, D0065:3 |

judge reasoning：

> The generated answer accurately captures all key points from the gold answers, including inability to detect literal word-by-word translations, meaning errors, segment-level unreliability, and poor distinction of good vs bad translations, with only minor rewording and additional context.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Cross-lingual metrics often fail because: 1) They have trouble detecting meaning-changing errors and adequacy issues, 2) They show poor capability in discerning good and bad translations across tasks despite correlating well with human judgments overall, 3) They are particularly unreliable for assessing translation usefulness at segment level, and 4) They tend to be overly permissive of literal word-by-word translations that may preserve surface similarity but lose fluency.

**naive 最终答案**

> Cross-lingual metrics often fail to properly evaluate translations despite high correlation with human judgments because:
> 
> 1. Their high correlation with human judgments is mainly at the **system level**; at the **segment (sentence) level** there is a considerable performance penalty, and they struggle to reliably distinguish good from bad translations (D0134).
> 
> 2. They show **negligible correlation with extrinsic downstream task outcomes** (e.g., QA, dialogue state tracking, semantic parsing), so high metric scores do not reflect real translation utility (D0134).
> 
> 3. They are **unable to punish literal word-by-word translations ("translationese") or capture semantically non-sensical paraphrases**, a key limitation of cross-lingual encoders exposed in reference-free MT evaluation (D0065).

**community 最终答案**

> Cross-lingual metrics fail to properly evaluate translations despite high correlation with human judgments for two main reasons:
> 
> 1. **Cross-lingual semantic mismatch**: The representations of mutual translations are not well aligned (e.g., M-BERT constructs a shared multilingual space in an unsupervised fashion without any direct bilingual signal), yielding distant vectors for mutual translations.
> 
> 2. **Inability to punish "translationese"**: These metrics cannot detect or penalize literal, word-by-word translations of the source—a persistent property of MT systems—nor capture semantically nonsensical translations or paraphrases. They are not robust to such "adversarial" MT outputs.
> 
> Additionally, their high correlation with human judgments holds mainly at the **system level**; at the **segment level** there is a considerable performance penalty, and metrics show negligible correlation with actual downstream task outcomes (extrinsic evaluation), so they fail to reliably distinguish good translations from bad ones.

</details>

<a id="case-mdaqa-80"></a>

### mdaqa:80 — 评分与执行路径对照

**问题：** What are the key differences in how these systems approach the temporal aspects of interaction-based learning, from single-step to multi-step planning?

**score：4→4（Δ+0）；rounds：7→3（Δ-4）。**

工具安排：naive 为第1轮2次、第2轮2次、第3轮2次、第4轮2次、第5轮2次、第6轮2次；community 为第1轮2次、第2轮2次。最终回答另占一轮。

轮次减少 4，工具总数 12→4、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 67→38、文档 overview 22→57；工具结果字符数 322,965→179,150，QA token 350,819→84,706。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/ef4fe83e49b747c8ab58e8b79b16886f.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/a941e00e581b4feea0dc8787f2893802.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"temporal aspects interaction-based learning single-step multi-step planning","search_mode":"hybrid","doc_ids":null} | 12 | 6 | 0 | 成功 | D0006:3, D0053:22, D0034:6, D0053:24, D0034:20, D0053:23, D0006:20, D0034:10, D0052:1, D0072:23, D0034:5, D0040:20 |
| 2 | 1 | search_chunks {"query":"multi-step planning learning approaches differences","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0059:20, D0006:5, D0006:13, D0017:0, D0017:7, D0006:2, D0006:20, D0006:0, D0006:24, D0017:24, D0111:13, D0006:3 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"single-step planning versus multi-step planning temporal horizon interaction learning","search_mode":"hybrid"} | 12 | 1 | 0 | 成功 | D0053:3, D0006:20, D0006:0, D0059:20, D0054:15, D0017:0, D0017:24, D0006:3, D0053:22, D0053:24, D0111:13, D0017:7 |
| 4 | 2 | search_chunks {"doc_ids":null,"query":"interaction-based learning temporal aspect differences between methods","search_mode":"hybrid"} | 12 | 4 | 0 | 成功 | D0075:0, D0059:12, D0054:15, D0133:3, D0053:23, D0111:14, D0089:3, D0052:1, D0089:6, D0006:3, D0123:19, D0059:14 |
| 5 | 3 | search_chunks {"doc_ids":null,"query":"single-step interaction multi-step planning compare approaches interaction learning temporal","search_mode":"keyword"} | 12 | 1 | 0 | 成功 | D0052:1, D0006:3, D0090:10, D0034:13, D0090:21, D0090:29, D0034:20, D0059:12, D0034:6, D0034:12, D0090:5, D0034:10 |
| 6 | 3 | search_chunks {"doc_ids":null,"query":"single step learning multi step planning temporal horizon interaction","search_mode":"vector"} | 12 | 1 | 0 | 成功 | D0053:22, D0053:24, D0053:23, D0048:0, D0053:27, D0048:20, D0006:20, D0053:3, D0040:19, D0006:0, D0040:23, D0059:20 |
| 7 | 4 | search_chunks {"doc_ids":null,"query":"single-step interaction multi-step planning difference temporal interaction learning compare","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0059:12, D0075:0, D0006:3, D0053:22, D0053:24, D0090:10, D0034:13, D0053:23, D0053:27, D0090:21, D0052:1, D0059:20 |
| 8 | 4 | read_chunks {"doc_id":"D0090","ordinals":[4,5,6,7,8,9]} | 6 | 0 | 0 | 成功 | D0090:4, D0090:5, D0090:6, D0090:7, D0090:8, D0090:9 |
| 9 | 5 | search_chunks {"doc_ids":null,"query":"\"single-step\" \"multi-step\" planning interaction learning temporal","search_mode":"keyword"} | 12 | 0 | 0 | 成功 | D0034:20, D0034:6, D0006:3, D0034:10, D0034:5, D0034:0, D0034:13, D0089:98, D0052:1, D0090:21, D0034:3, D0034:16 |
| 10 | 5 | search_chunks {"doc_ids":null,"query":"next-step multi-step prediction deterioration error accumulation RNN decoder","search_mode":"hybrid"} | 12 | 1 | 0 | 成功 | D0034:6, D0034:5, D0034:2, D0034:0, D0034:10, D0034:13, D0034:4, D0034:3, D0034:16, D0034:12, D0133:2, D0077:28 |
| 11 | 6 | search_chunks {"doc_ids":null,"query":"planning horizon rollout temporal abstraction compare systems interaction","search_mode":"hybrid"} | 12 | 4 | 0 | 成功 | D0053:3, D0045:2, D0054:18, D0006:23, D0053:22, D0054:14, D0118:26, D0006:3, D0009:0, D0017:7, D0026:19, D0006:20 |
| 12 | 6 | search_chunks {"doc_ids":null,"query":"temporal aspects of interaction-based learning systems single-step multi-step planning differences","search_mode":"vector"} | 12 | 1 | 0 | 成功 | D0053:22, D0006:22, D0006:20, D0045:24, D0059:20, D0053:23, D0059:19, D0053:24, D0026:19, D0080:0, D0072:23, D0006:23 |

judge reasoning：

> The generated answer fully captures the core distinction between single-step and multi-step temporal approaches, including memory-based aggregation, rollouts, and planning, consistent with the gold answers.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"temporal aspects interaction-based learning single-step multi-step planning","search_mode":"hybrid","doc_ids":null} | 12 | 40 | 6 | 成功 | D0006:3, D0053:22, D0034:6, D0053:24, D0034:20, D0053:23, D0034:10, D0048:20, D0040:20, D0052:1, D0006:20, D0034:5 |
| 2 | 1 | search_chunks {"query":"temporal logic interaction learning reward single-step","search_mode":"hybrid","doc_ids":null} | 12 | 15 | 2 | 成功 | D0059:12, D0090:6, D0089:31, D0075:0, D0080:0, D0089:98, D0090:10, D0073:15, D0090:5, D0040:14, D0080:2, D0034:6 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"interaction network rollout multi-step planning one-step model-free","search_mode":"hybrid"} | 12 | 2 | 1 | 成功 | D0090:5, D0090:6, D0053:3, D0072:1, D0053:22, D0053:24, D0068:14, D0053:23, D0068:15, D0006:3, D0053:25, D0090:10 |
| 4 | 2 | search_chunks {"doc_ids":null,"query":"world model direct reinforcement learning planning simulated experience Dyna-Q temporal","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0017:2, D0006:2, D0006:5, D0006:3, D0006:0, D0017:0, D0017:3, D0006:20, D0017:4, D0006:8, D0017:5, D0017:1 |

judge reasoning：

> The generated answer fully captures the gold answer's core distinction between single-step memory-based interaction and explicit multi-step planning, adding specific examples that are consistent and relevant without contradiction.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> The approaches range from single-step interactions with memory-based aggregation to explicit multi-step planning with future trajectory forecasting. Some systems use immediate visual feedback for learning, while others employ model-predictive control and roll out multiple timesteps to plan optimal interaction sequences.

**naive 最终答案**

> Based on the retrieved context, the key differences in how these systems handle the temporal dimension of interaction-based learning are:
> 
> **Single-step (next-step) learning:**
> - **DQN / no-planning baselines (DDQ paper, D3Q)**: learn only from direct single-step real-user interactions (K=0 planning steps), requiring many real dialogues (e.g., ~180 epochs to reach 50% success).
> - **CE3 (D0052)**: acts per timestep, retrieving at each single step; because only single-step feedback is available, the agent cannot "explicitly consider the whole multi-turn goal-oriented process," making learning challenging.
> - **Next-step prediction models (STG2Seq context, D0034)**: optimize only the next time step's error; they deteriorate rapidly for multi-step prediction. RNN-based decoders accumulate errors step by step (each step feeds the previous prediction forward).
> - **AtP baseline "Act-NoHold" (D0090)**: applies a single push action every step, a single mode of interaction typical of prior interactive segmentation works; the full AtP instead predicts one-step rewards per timestep but rolls out T=5 steps with part-memory/history aggregation to discover parts through multi-step dynamic interactions.
> 
> **Multi-step planning:**
> - **DDQ (D0006) / D3Q (D0017)**: integrate K planning steps per direct RL step using a world model (simulated experience). Larger K speeds learning early, but a heuristic later reduces planning steps to avoid low-quality simulated experience; D3Q additionally filters simulated sessions with a discriminator.
> - **STG2Seq (D0034)**: does multi-step prediction without an RNN decoder—the last prediction is fed back only to a short-term encoder (attenuating error accumulation) alongside a long-term encoder and teacher forcing; removing the short-term encoder degenerates the model back to single-step prediction.
> - **Visual Reaction (D0053)**: a model-based planner rolls out sequences of actions over a planning horizon (performance peaks at H=3), forecasting future object states rather than relying on current-state tracking or model-free A3C.
> - **Feudal RL (D0009)**: uses temporal abstraction (hierarchical RL) to decompose decisions into master-level and primitive-action steps.
> - **Affordance navigation (D0054)**: plans over long horizons with A*, with high-frequency replanning treating dynamic hazards as static obstacles; RL baselines struggle over long time horizons without waypoint guidance.
> 
> In short: single-step systems react to the immediate interaction only and suffer from error accumulation or lack of goal-level foresight, whereas multi-step systems use world models, short/long-term encoders, planning horizons, rollouts, or temporal abstraction to look ahead and reduce real interaction cost.

**community 最终答案**

> Based on the context, the systems differ mainly in how much temporal lookahead they build into interaction learning:
> 
> - **Single-step (myopic) action selection**: Act the Part (D0090) predicts one-step pixel-wise hold/push reward maps at each timestep and samples greedily; multi-step behavior only emerges from repeated interaction and part-memory aggregation over ~5–7 steps, with no explicit lookahead. CE3 (D0052) also acts per timestep, with actions limited to two steps per turn (query reformulation, then retrieval).
> 
> - **Multi-step planning via a learned world model**: Deep Dyna-Q (D0006) and D3Q (D0017) treat dialogue as an MDP over a sequence of turns and add explicit "planning" — rolling out K simulated experiences per step of direct RL through a world model (indirect RL), with D3Q adding a discriminator to filter low-quality simulated rollouts.
> 
> - **Model-predictive multi-step planning**: Visual Reaction (D0053) explicitly rolls out sequences of drone actions with a forecaster + model-predictive planner over a planning horizon (optimal H=3); performance depends on horizon length and number of rollouts, unlike reactive tracking baselines.
> 
> - **Temporal-consistent world simulators**: GameGAN (D0068) and DriveGAN (D0089) learn action-conditioned dynamics (LSTM) and are trained/evaluated on long multi-step rollouts (e.g., 32 steps) with temporal discriminators to keep rollouts consistent, supporting simulation-based planning rather than one-step prediction.
> 
> In short: single-step systems choose actions reactively per timestep; multi-step systems either simulate future experiences through a learned world model (Dyna-Q style), search action sequences over a horizon (MPC), or learn long temporally consistent rollouts (neural simulators).

</details>

<a id="case-mdaqa-81"></a>

### mdaqa:81 — 评分与执行路径对照

**问题：** How do these interactive learning systems generalize their learned object understanding to novel instances and categories?

**score：4→4（Δ+0）；rounds：4→5（Δ+1）。**

工具安排：naive 为第1轮2次、第2轮2次、第3轮2次；community 为第1轮2次、第2轮2次、第3轮1次、第4轮1次。最终回答另占一轮。

轮次增加 1，工具总数 6→6、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 38→36、文档 overview 9→41；工具结果字符数 139,723→153,163，QA token 89,040→141,396。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/16855f0628d0436f8600d0a3dfff89ff.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/554cc53fc17d430b8bd838b75d349fa4.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"interactive learning systems generalize learned object understanding to novel instances and categories","search_mode":"hybrid","doc_ids":null} | 12 | 7 | 0 | 成功 | D0090:2, D0090:18, D0090:23, D0090:0, D0051:0, D0069:0, D0051:3, D0075:0, D0075:20, D0086:15, D0016:0, D0058:6 |
| 2 | 1 | search_chunks {"query":"generalization novel categories object recognition robot learning","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0058:0, D0069:0, D0107:21, D0058:3, D0075:0, D0051:3, D0090:18, D0075:20, D0090:14, D0040:19, D0051:28, D0058:17 |
| 3 | 2 | read_chunks {"doc_id":"D0075","ordinals":[1,2,3,4,5,6,7]} | 7 | 0 | 0 | 成功 | D0075:1, D0075:2, D0075:3, D0075:4, D0075:5, D0075:6, D0075:7 |
| 4 | 2 | read_chunks {"doc_id":"D0090","ordinals":[14,15,16]} | 3 | 0 | 0 | 成功 | D0090:14, D0090:15, D0090:16 |
| 5 | 3 | search_chunks {"doc_ids":["D0075"],"query":"generalize novel instances unseen categories spatial embeddings generalization","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0075:6, D0075:30, D0075:0, D0075:20, D0075:19, D0075:21, D0075:18, D0075:17, D0075:12, D0075:13, D0075:23, D0075:1 |
| 6 | 3 | search_chunks {"doc_ids":["D0075"],"query":"evaluation novel object categories results generalization","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0075:2, D0075:17, D0075:13, D0075:21, D0075:16, D0075:5, D0075:15, D0075:30, D0075:0, D0075:20, D0075:1, D0075:19 |

judge reasoning：

> The generated answer fully captures the core meaning and key facts from the gold answers, including category-agnostic interaction policies, motion-based part discovery, physical property learning, and generalization to novel instances and unseen categories, while adding consistent supporting details.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"generalize learned object understanding to novel instances and categories","search_mode":"hybrid","doc_ids":null} | 12 | 26 | 4 | 成功 | D0090:2, D0051:3, D0090:23, D0090:18, D0051:0, D0058:3, D0051:23, D0090:1, D0058:4, D0075:0, D0086:15, D0090:0 |
| 2 | 1 | search_chunks {"query":"interactive learning system object recognition generalization novel categories","search_mode":"hybrid","doc_ids":null} | 12 | 8 | 2 | 成功 | D0090:0, D0058:0, D0058:3, D0090:2, D0090:14, D0058:4, D0069:0, D0107:21, D0058:1, D0058:25, D0075:0, D0051:3 |
| 3 | 2 | read_chunks {"doc_id":"D0075","ordinals":[1,2,3,4]} | 4 | 7 | 1 | 成功 | D0075:1, D0075:2, D0075:3, D0075:4 |
| 4 | 2 | read_chunks {"doc_id":"D0090","ordinals":[14,15]} | 2 | 0 | 0 | 成功 | D0090:14, D0090:15 |
| 5 | 3 | read_chunks {"doc_id":"D0075","ordinals":[5,6,7,8,9,10]} | 6 | 0 | 0 | 成功 | D0075:5, D0075:6, D0075:7, D0075:8, D0075:9, D0075:10 |
| 6 | 4 | read_chunks {"doc_id":"D0075","ordinals":[11,12,13,14,15,16,17]} | 7 | 0 | 0 | 成功 | D0075:11, D0075:12, D0075:13, D0075:14, D0075:15, D0075:16, D0075:17 |

judge reasoning：

> The generated answer fully captures the gold answer's core meaning by explaining category-agnostic, interaction-driven, and motion-based generalization to novel instances and unseen categories, with accurate supporting details and no contradictions.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> The systems demonstrate generalization through different strategies: learning category-agnostic interaction policies, using motion-based part discovery that transfers across objects, and employing visual encoders that capture general physical properties rather than semantic categories. They evaluate generalization on both novel instances of seen categories and completely unseen object categories.

**naive 最终答案**

> Based on the context, these interactive learning systems generalize in the following ways:
> 
> **Learning by Interaction (AI2THOR agent, D0075):** The agent learns purely from self-supervised interaction—raw visual feedback (image differences before/after applying forces) provides supervision, clustering points that move coherently into object masks. Because it relies on physical interaction dynamics and appearance-based spatial embeddings rather than category-specific knowledge, it generalizes to novel instances of seen categories and to novel object categories (tested in Novel Objects scenes where most categories, e.g., pillows, were unseen during training).
> 
> **Act the Part (D0090):** The method makes no category-level assumptions and no class-specific assumptions, learning a single model for all object categories with diverse kinematic structures using flow and touch feedback. Consequently, the same policy and perception models work for unseen instances from seen categories and novel categories with different numbers of parts and joints, and even transfer to real images of unseen categories without fine-tuning.
> 
> In short, both systems avoid category-specific or semantic supervision, instead learning general interaction/motion-based understanding that transfers to novel instances and unseen categories.

**community 最终答案**

> Based on the context, these interactive learning systems generalize because they avoid category-level assumptions and instead learn from interaction-driven visual feedback:
> 
> - **D0075 (Learning by Interaction):** The agent learns interaction scores, force/mass logits, and spatial embeddings purely from self-supervised visual feedback (image differences before/after applying forces), without external annotation or category-specific knowledge. Because it learns generic object motion and appearance-based clustering cues rather than memorizing categories, the same model works for novel instances of seen categories and entirely novel categories (e.g., the Novel Objects split, where most test categories were never seen in training).
> 
> - **D0090 (Act the Part):** The approach makes no class-specific assumptions and uses optical flow and touch feedback as supervision, learning a single model for all object categories with diverse kinematic structures. The same interaction policy and perception model apply to unseen categories because it reasons about motion from visual changes (where to hold/push to move undiscovered parts) rather than relying on category priors — enabling generalization to unseen instances and categories with different numbers of parts and joints, plus transfer to real images without fine-tuning.
> 
> In short: generalization comes from learning interaction/segmentation skills from raw visual motion feedback (self-supervised), unconstrained by category-level assumptions, so the learned models transfer to novel instances and unseen categories.

</details>

<a id="case-mdaqa-82"></a>

### mdaqa:82 — 评分与执行路径对照

**问题：** What are the key differences in how interactive learning approaches handle dynamic versus static elements in the environment?

**score：2→2（Δ+0）；rounds：3→4（Δ+1）。**

工具安排：naive 为第1轮2次、第2轮2次；community 为第1轮2次、第2轮2次、第3轮2次。最终回答另占一轮。

轮次增加 1，工具总数 4→6、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 32→38、文档 overview 8→55；工具结果字符数 105,400→188,293，QA token 51,184→113,775。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/febe187be96f40b5991ab9c7fef86778.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/589bfaa7d52b41dcac7dc2c2045af042.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"interactive learning dynamic versus static elements environment","search_mode":"hybrid","doc_ids":null} | 12 | 6 | 0 | 成功 | D0068:0, D0068:6, D0070:1, D0068:11, D0054:1, D0068:15, D0070:0, D0068:13, D0053:0, D0052:1, D0105:0, D0054:23 |
| 2 | 1 | search_chunks {"query":"dynamic static environment interactive learning approach differences","search_mode":"vector","doc_ids":null} | 12 | 2 | 0 | 成功 | D0070:1, D0068:0, D0054:15, D0017:0, D0089:2, D0053:1, D0053:0, D0068:1, D0054:1, D0070:0, D0070:4, D0054:23 |
| 3 | 2 | read_chunks {"doc_id":"D0068","ordinals":[2,3,4,5,6,7,10,11,12,13]} | 10 | 0 | 0 | 成功 | D0068:2, D0068:3, D0068:4, D0068:5, D0068:6, D0068:7, D0068:10, D0068:11, D0068:12, D0068:13 |
| 4 | 2 | read_chunks {"doc_id":"D0054","ordinals":[0,2,3,4,5,16,17]} | 7 | 0 | 0 | 成功 | D0054:0, D0054:2, D0054:3, D0054:4, D0054:5, D0054:16, D0054:17 |

judge reasoning：

> The generated answer partially matches by discussing affordance-map navigation's treatment of dynamic elements, but it mischaracterizes the affordance map as implicit rather than explicit and omits the object-centric interaction methods' use of dynamics as supervision for physical properties.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"interactive learning dynamic static environment elements","search_mode":"hybrid","doc_ids":null} | 12 | 30 | 5 | 成功 | D0068:0, D0068:6, D0068:11, D0053:0, D0070:1, D0068:15, D0054:1, D0068:13, D0068:14, D0054:4, D0054:2, D0089:0 |
| 2 | 1 | search_chunks {"query":"dynamic vs static elements interactive learning","search_mode":"vector","doc_ids":null} | 12 | 12 | 2 | 成功 | D0019:16, D0068:0, D0068:6, D0068:41, D0070:1, D0111:80, D0075:0, D0053:0, D0053:22, D0089:3, D0053:1, D0089:2 |
| 3 | 2 | read_chunks {"doc_id":"D0068","ordinals":[8,9,10]} | 3 | 0 | 0 | 成功 | D0068:8, D0068:9, D0068:10 |
| 4 | 2 | read_chunks {"doc_id":"D0054","ordinals":[3,5]} | 2 | 0 | 0 | 成功 | D0054:3, D0054:5 |
| 5 | 3 | search_chunks {"doc_ids":null,"query":"static elements stored memory dynamic elements change as game progresses","search_mode":"keyword"} | 12 | 13 | 2 | 成功 | D0068:11, D0068:12, D0068:6, D0068:13, D0068:0, D0068:8, D0068:5, D0068:41, D0068:15, D0068:3, D0054:1, D0055:2 |
| 6 | 3 | search_chunks {"doc_ids":null,"query":"treat dynamic obstacles as outliers ignore when learning geometric map affordance safety margin","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0054:1, D0054:0, D0054:24, D0054:13, D0054:3, D0054:22, D0054:9, D0054:8, D0054:23, D0054:2, D0054:6, D0054:25 |

judge reasoning：

> The generated answer correctly discusses affordance-map navigation's handling of dynamic hazards, but it omits the crucial contrast with object-centric interaction methods that treat dynamics as supervision for learning physical properties, and it characterizes dynamic elements as implicitly rather than explicitly modeled, making it only partially complete.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Affordance map approaches explicitly model dynamic elements as regions to avoid during navigation, while object-centric interaction methods treat dynamics as a source of supervision for learning physical properties. The former focuses on safe navigation by maintaining temporal maps, while the latter uses motion from interaction to segment objects and infer attributes like mass and articulation.

**naive 最终答案**

> Based on the context, interactive learning approaches differ in how they treat dynamic versus static elements:
> 
> **GameGAN** explicitly **disentangles** them: static elements (walls, background) are stored in an external memory module so they persist with long-term consistency when the agent revisits locations, while dynamic elements (ghosts, food, non-player characters) are handled by the dynamics engine/hidden state as things that change as the game progresses. A temporal cycle loss encourages putting static content in memory, enabling component swapping.
> 
> **Affordance-map navigation** treats them asymmetrically: classic geometric maps ignore dynamic obstacles as outliers, whereas the learned affordance map captures dynamics **implicitly**—it learns larger safety margins around dynamic actors—while static geometry is represented explicitly in the geometric map.
> 
> **Visual reaction (drone catch)** focuses on dynamic environments where changes aren't caused by the agent itself: it must forecast future object movement and replan from visual feedback, whereas static elements need no such prediction or reaction.

**community 最终答案**

> Based on the context, two papers show contrasting approaches:
> 
> **GameGAN (D0068)** — a learning-based simulator that explicitly **disentangles static from dynamic elements**:
> - **Static components** (e.g., walls, background, buildings/streets) are stored in an **external memory module** (the internal map) to guarantee long-term consistency — so when the agent returns to a previously visited location, the scene doesn't change.
> - **Dynamic elements** (e.g., moving ghosts, fireballs, food/non-player characters) "can change as the game progresses"; they are drawn from the LSTM dynamics-engine hidden state (not the memory) and generated stochastically, so they don't need to persist.
> - This disentanglement is what enables swapping static backgrounds or dynamic foregrounds.
> 
> **Affordance-map navigation (D0054)** — a self-supervised interactive learning approach:
> - **Static obstacles/geometry** are handled by classic geometric maps (occupancy/navigability maps) that remain reliable over time.
> - **Dynamic actors** (monsters, other agents) are not discarded as outliers; they are **implicitly encoded** in the learned affordance map as larger "margins of safety" around regions near moving actors. Because dynamic actors move, the agent updates the navigability maps at every timestep and re-plans at high frequency to treat them as obstacles.
> 
> So the key difference: **simulation/representation learning (GameGAN) actively separates and persists static content in memory while letting dynamic content be generated on the fly; navigation learning (affordance maps) uses stable geometric maps for static structure and learns implicit safety margins plus frequent re-planning to handle dynamic hazards.**

</details>

<a id="case-mdaqa-83"></a>

### mdaqa:83 — 评分与执行路径对照

**问题：** What are the key tradeoffs between using rule-based versus neural approaches for AMR alignment?

**score：2→3（Δ+1）；rounds：2→2（Δ+0）。**

工具安排：naive 为第1轮1次；community 为第1轮2次。最终回答另占一轮。

两边均为 2 轮，但工具总数 1→2，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 12→15、文档 overview 3→29；工具结果字符数 29,290→89,951，QA token 11,021→26,311。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/46ae2e8f35c54813a85f9c2bab082961.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/a36f38a631a741c0805a0b75dd010750.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"rule-based versus neural approaches AMR alignment tradeoffs","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0120:0, D0019:0, D0120:1, D0019:2, D0019:1, D0120:19, D0120:24, D0019:5, D0019:23, D0019:25, D0013:0, D0019:24 |

judge reasoning：

> The generated answer correctly identifies some tradeoffs like greedy error propagation in rule-based aligners and the need for regularization in neural aligners, but it omits key gold facts: rule-based interpretability, neural avoidance of error propagation via joint optimization, and the strong empirical results of hybrid approaches.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"rule-based versus neural approaches for AMR alignment tradeoffs","search_mode":"hybrid","doc_ids":null} | 12 | 29 | 4 | 成功 | D0120:0, D0019:0, D0019:1, D0120:1, D0019:2, D0120:19, D0120:24, D0019:23, D0019:5, D0019:24, D0019:25, D0013:18 |
| 2 | 1 | search_chunks {"query":"AMR alignment rule-based neural methods comparison","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0120:0, D0019:0, D0019:2, D0120:19, D0019:1, D0120:1, D0120:24, D0019:23, D0013:23, D0019:22, D0019:5, D0013:0 |

judge reasoning：

> The generated answer accurately captures the main rule-based vs neural tradeoffs, but omits the gold answer's key point about hybrid approaches showing the strongest empirical results, making it slightly incomplete.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Rule-based aligners like JAMR provide interpretable alignments but have limited recall and propagate errors due to greedy search. Neural aligners achieve higher recall through learned similarities and avoid error propagation through joint optimization, but require careful regularization to maintain precision. Hybrid approaches combining rule-based constraints with neural flexibility show the strongest empirical results.

**naive 最终答案**

> Key tradeoffs between rule-based and neural AMR alignment:
> 
> **Rule-based (e.g., JAMR/SB-Align):**
> - Pros: Flexible for incorporating linguistic resources (WordNet); provides strong inductive biases that serve as a useful training signal (importance sampling without these constraints failed to improve).
> - Cons: Requires a complex pipeline of rule-based components, pre-processing (lemmatization), and post-processing to satisfy domain-specific constraints; fails to generalize to new domains (e.g., AMR3.0); greedy search propagates errors; struggles with ambiguity and recalling semantically matched word-concept pairs; only ~90% alignment F1.
> 
> **Neural:**
> - Pros: Easy to use (uses word embeddings, less preprocessing, no domain-specific rules); more accurate alignments (96.5 vs 89.2 F1); generalizes better from AMR2.0 to AMR3.0; can produce multiple alignments capturing uncertainty.
> - Cons: More flexible/lower inductive bias (posterior regularization with the constrained aligner outperformed unconstrained importance sampling); when producing multiple alignments, gains recall at the cost of lower precision.

**community 最终答案**

> Key tradeoffs from the context:
> 
> **Rule-based aligners (e.g., JAMR/SB-Align)**
> - Pro: flexible, can incorporate linguistic resources like WordNet.
> - Con: require a complex pipeline of rule-based components plus pre-processing (lemmatization) and post-processing to satisfy domain-specific constraints; greedy search propagates errors and creates dependencies/mutual exclusions between rules; struggle to derive optimal alignments in ambiguous situations; fail to generalize well to new domains (e.g., AMR3.0); yield only ~90% alignment F1; treat alignment as a fixed point-estimate, neglecting inherent alignment uncertainty.
> 
> **Neural aligners**
> - Pro: no complex pipeline—easy to use, depends on less preprocessing and no domain-specific rules; can incorporate pretrained features (e.g., character-aware ELMo embeddings); relax strong independence assumptions of count-based aligners; learn latent alignments and model posterior uncertainty; more accurate alignments and better generalization (AMR2.0→AMR3.0), meaningfully improving over rule-based baselines.
> - Con: relies on embeddings/pretrained features—performance drops substantially without them; needs training, and its flexibility requires strong inductive biases/uncertainty handling (posterior regularization) to be most effective.
> 
> In short: rule-based methods are flexible and resource-incorporating but pipeline-heavy, error-prone, and domain-specific; neural methods are simpler, more accurate, and domain-agnostic but data/embedding-dependent.

</details>

<a id="case-mdaqa-84"></a>

### mdaqa:84 — 同类证据被解释成相反结论

**问题：** How does the incorporation of alignment uncertainty impact the complexity of AMR parser training?

**score：0→4（Δ+4）；rounds：2→2（Δ+0）。**

两份回答都描述 alignment posterior sampling、posterior regularization/importance sampling。naive 开头却写“does not increase complexity”，community 写“makes training more complex”，造成 0→4。两边首轮都召回 D0120:0/1 和相同核心 overview；community 有额外相关概览和略不同的第二路检索，但没有独立证据证明其中某一新增片段导致结论翻转。此例主要提醒区分“算法训练方案简洁”与“相对固定对齐新增计算复杂度”，不是缺少论文名称。

工具安排：naive 为第1轮2次；community 为第1轮2次。最终回答另占一轮。

两边均为 2 轮，但工具总数 2→2，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 16→16、文档 overview 4→36；工具结果字符数 56,528→96,856，QA token 19,024→27,864。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/2edf03fec53e479da4f62a7ea341189c.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/eb7db6a4409d4f80827eaa8d90e6ccca.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"incorporation of alignment uncertainty complexity of AMR parser training","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0120:0, D0120:1, D0120:19, D0013:0, D0120:8, D0019:0, D0019:1, D0019:2, D0120:20, D0120:24, D0120:21, D0019:22 |
| 2 | 1 | search_chunks {"query":"alignment uncertainty AMR parser training complexity","search_mode":"vector","doc_ids":null} | 12 | 1 | 0 | 成功 | D0120:0, D0019:24, D0120:1, D0120:19, D0120:24, D0120:8, D0126:28, D0120:21, D0019:22, D0019:1, D0019:23, D0120:9 |

judge reasoning：

> The generated answer directly contradicts the gold answer by stating that alignment uncertainty does not increase training complexity, whereas the gold answer's core claim is that it does increase complexity.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"alignment uncertainty AMR parser training complexity","search_mode":"hybrid","doc_ids":null} | 12 | 29 | 4 | 成功 | D0120:0, D0120:1, D0120:19, D0120:8, D0019:1, D0019:2, D0013:0, D0120:21, D0019:0, D0120:24, D0120:20, D0019:23 |
| 2 | 1 | search_chunks {"query":"alignment uncertainty complexity parser training","search_mode":"vector","doc_ids":null} | 12 | 7 | 1 | 成功 | D0120:0, D0120:24, D0120:8, D0126:28, D0120:1, D0120:19, D0019:24, D0120:20, D0120:21, D0019:1, D0120:9, D0013:17 |

judge reasoning：

> The generated answer accurately captures the core idea that alignment uncertainty increases AMR parser training complexity via sampling from the posterior, and correctly notes the improved accuracy outweighs the cost.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Incorporating alignment uncertainty increases training complexity: Fixed alignments allow simple maximum likelihood training, latent alignments require variational inference, parser-tuned alignments need multiple parsing runs, and posterior regularization demands sampling-based training. However, the improved parsing accuracy outweighs the additional computational cost.

**naive 最终答案**

> Incorporating alignment uncertainty does not increase the complexity of AMR parser training; it results in a simple training scheme where the parser is trained on oracle actions derived from samples of the neural aligner's posterior distribution (via posterior regularization or importance sampling). It requires only sampling alignments (no Smatch computation), uses the same number of samples as alternatives, and regularizes the parser's intractable posterior toward the aligner's tractable posterior, reducing gradient estimator variance while improving performance without needing beam search at test time.

**community 最终答案**

> Incorporating alignment uncertainty makes AMR parser training more complex: instead of training on a single one-best (MAP) alignment, the parser is trained on oracle action sequences sampled from the neural aligner's posterior distribution over alignments. This is done via posterior regularization or importance sampling, which sample different action sequences during training to regularize the parser's intractable posterior. This added complexity yields more accurate alignments, better domain generalization, and matches state-of-the-art performance without beam search.

</details>

<a id="case-mdaqa-85"></a>

### mdaqa:85 — 三个整轮被参数语法错误占用

**问题：** What are the key differences between reinforcement learning and gradient-based approaches for generating adversarial examples in terms of their semantic preservation capabilities?

**score：4→4（Δ+0）；rounds：3→7（Δ+4）。**

评分均 4，轮次 3→7、token 36,497→172,366。community 第 2、3、4 轮的全部工具都因 ordinals 未写成 JSON 数组失败（第 4 轮并行两个失败调用），第 5 轮才成功读取。不是未知论文或检索召回率低，而是工具调用协议恢复慢。严格 schema 已发送也未阻止这类返回，应在 schema/提示/错误恢复层明确数组格式并验证服务端工具参数约束是否真正执行。

工具安排：naive 为第1轮1次、第2轮2次；community 为第1轮2次、第2轮1次、第3轮1次、第4轮2次、第5轮2次、第6轮1次。最终回答另占一轮。

轮次增加 4，工具总数 3→9、错误 0→4，整轮全部工具报错的轮数 0→3。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 29→33、文档 overview 11→31；工具结果字符数 81,650→121,965，QA token 36,497→172,366。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/c25902658d29401d89b9fedc15b95454.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/ea4916724913467bb82f72fba58929e5.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"reinforcement learning gradient-based adversarial examples semantic preservation","search_mode":"hybrid","doc_ids":null} | 12 | 5 | 0 | 成功 | D0029:1, D0023:23, D0004:0, D0049:3, D0004:1, D0004:11, D0049:29, D0049:28, D0029:16, D0035:0, D0004:9, D0004:3 |
| 2 | 2 | read_chunks {"doc_id":"D0049","ordinals":[4,5,6,7,8,9,10]} | 7 | 0 | 0 | 成功 | D0049:4, D0049:5, D0049:6, D0049:7, D0049:8, D0049:9, D0049:10 |
| 3 | 2 | search_chunks {"query":"reinforcement learning semantic preservation vs gradient-based semantic constraints discriminator","search_mode":"hybrid","doc_ids":null} | 12 | 6 | 0 | 成功 | D0049:3, D0049:27, D0017:3, D0045:24, D0026:17, D0017:2, D0049:4, D0029:7, D0049:13, D0068:23, D0069:17, D0089:72 |

judge reasoning：

> The generated answer accurately captures the core difference—RL uses a learned discriminator to preserve semantics while gradient-based methods rely on handcrafted constraints—and adds consistent supporting details without contradicting the gold answers.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"reinforcement learning gradient-based adversarial examples semantic preservation","search_mode":"hybrid","doc_ids":null} | 12 | 30 | 5 | 成功 | D0029:1, D0023:23, D0004:0, D0049:3, D0004:1, D0004:11, D0049:29, D0029:16, D0049:28, D0029:17, D0035:0, D0004:3 |
| 2 | 1 | search_chunks {"query":"RL adversarial attack semantic preservation gradient method","search_mode":"vector","doc_ids":null} | 12 | 1 | 0 | 成功 | D0023:24, D0023:22, D0004:12, D0029:7, D0049:3, D0049:4, D0049:5, D0029:1, D0004:11, D0068:23, D0029:16, D0023:23 |
| 3 | 2 | read_chunks {"raw":"{\"doc_id\": \"D0049\", \"ordinals\": 0, 1, 2, 6, 7, 8, 9, 10}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | — |
| 4 | 3 | read_chunks {"raw":"{\"doc_id\": \"D0049\", \"ordinals\": 5, 6, 7, 8}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | — |
| 5 | 4 | read_chunks {"raw":"{\"doc_id\": \"D0049\", \"ordinals\": 0, 1, 2, 5, 6, 7}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | — |
| 6 | 4 | read_chunks {"raw":"{\"doc_id\": \"D0029\", \"ordinals\": 7, 8, 9, 10}"} | 0 | 0 | 0 | Expecting property name enclosed in double quotes: line 1 column 36 (char 35) | — |
| 7 | 5 | read_chunks {"doc_id":"D0049","ordinals":[5,6,7,8,9,10]} | 6 | 0 | 0 | 成功 | D0049:5, D0049:6, D0049:7, D0049:8, D0049:9, D0049:10 |
| 8 | 5 | read_chunks {"doc_id":"D0029","ordinals":[7,8,9,10]} | 4 | 0 | 0 | 成功 | D0029:7, D0029:8, D0029:9, D0029:10 |
| 9 | 6 | read_chunks {"doc_id":"D0049","ordinals":[11,12,13,14,15,16]} | 6 | 0 | 0 | 成功 | D0049:11, D0049:12, D0049:13, D0049:14, D0049:15, D0049:16 |

judge reasoning：

> The generated answer accurately captures the core distinction from the gold answers: RL uses a discriminator to preserve semantics while gradient-based methods rely on external constraints and may harm meaning, with all extra details consistent.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Reinforcement learning approaches use a discriminator to explicitly constrain semantics during generation, while gradient-based approaches rely on simple constraints like character swaps or nearest neighbor substitutions. The RL method can achieve better semantic preservation by learning to optimize both attack success and meaning retention, whereas gradient methods make more direct perturbations that may not preserve meaning as effectively.

**naive 最终答案**

> Based on the context (document D0049), the key differences in semantic preservation are:
> 
> - **RL approach**: semantic preservation is enforced by a **learned discriminator** acting as a terminal/survival signal in the environment. It achieves stably high human-evaluated semantic similarity (HE > 3.7) **without any handcrafted semantic constraints**, and needs no target references (works from monolingual data). It is model-agnostic.
> - **Gradient-based approaches**: rely on **handcrafted constraints** in the search space (e.g., embedding similarity, POS matching, stop-word restrictions) or learned language models (which are not apt for typos/UNK). They must tune the modification ratio and can **hardly strike a balance between semantic constraints and degradation**. Their surrogate gradient losses are defined by a fixed tokenization and risk being invalidated once the attack changes tokenization, and they depend on reference and victim gradients.
> 
> In short: RL preserves semantics via an automatically learned discriminator reward, whereas gradient-based methods rely on rigid handcrafted constraints and struggle to balance meaning preservation with attack degradation.

**community 最终答案**

> Key differences in semantic preservation:
> 
> **RL approach (D0049):** Uses a reinforcement-learning (actor-critic) paradigm with a **discriminator as a terminal signal in the environment** to constrain semantics. It achieves **stably high semantic preservation (HE > 3.7) without any handcrafted semantic constraints**, is model-agnostic, and is less likely to perturb easily-modified semantics (e.g., it changes number forms but not to different numbers). It requires no target references (works from monolingual data) and produces comparable degradation with better semantics than gradient search.
> 
> **Gradient-based approach (D0029, D0049):** Optimizes a surrogate gradient-based loss with a **differentiable objective**, perturbing token positions via greedy search/brute force. Semantic preservation is **not intrinsic** — it must be enforced by **handcrafted constraints** (e.g., kNN restricting replacements to nearest embedding neighbors, or CharSwap character swaps to OOV words); naive/unconstrained gradient attacks "do not preserve meaning in general" and break semantics (low HE). Search methods must tune the modification ratio and "can hardly strike a balance between semantic constraints and degradation"; search tends to generate semantically different tokens to achieve degradation, and relies on references and victim gradients.
> 
> In short: RL preserves semantics **implicitly through a learned discriminator reward** (stably high HE, no handcrafted constraints), whereas gradient-based methods preserve semantics **only if explicitly constrained**, and unconstrained gradient attacks tend to destroy meaning.

</details>

<a id="case-mdaqa-88"></a>

### mdaqa:88 — 评分与执行路径对照

**问题：** What are the theoretical guarantees and assumptions required by different conformal prediction methods?

**score：2→3（Δ+1）；rounds：3→5（Δ+2）。**

工具安排：naive 为第1轮2次、第2轮2次；community 为第1轮2次、第2轮3次、第3轮1次、第4轮1次。最终回答另占一轮。

轮次增加 2，工具总数 4→7、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 23→42、文档 overview 2→24；工具结果字符数 73,902→132,608，QA token 40,542→135,126。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/db8272780f094436bdeb903e6da5a123.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/271e3ddd12ff425dbf89c471d6673268.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"theoretical guarantees and assumptions of conformal prediction methods","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0110:3, D0110:25, D0110:4, D0110:5, D0110:0, D0110:22, D0110:2, D0142:0, D0110:20, D0110:7, D0110:21, D0142:1 |
| 2 | 1 | search_chunks {"query":"conformal prediction validity exchangeability coverage guarantee assumptions","search_mode":"hybrid","doc_ids":null} | 12 | 0 | 0 | 成功 | D0110:8, D0110:25, D0110:3, D0142:1, D0110:0, D0110:7, D0110:11, D0110:4, D0110:2, D0110:12, D0110:10, D0110:1 |
| 3 | 2 | read_chunks {"doc_id":"D0142","ordinals":[2,3,4,5]} | 4 | 0 | 0 | 成功 | D0142:2, D0142:3, D0142:4, D0142:5 |
| 4 | 2 | read_chunks {"doc_id":"D0110","ordinals":[9,13]} | 2 | 0 | 0 | 成功 | D0110:9, D0110:13 |

judge reasoning：

> The generated answer accurately covers traditional conformal methods and online PID control, but it omits the category of conditional coverage methods and their assumptions, which is a key part of the gold answer.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"conformal prediction theoretical guarantees assumptions","search_mode":"hybrid","doc_ids":null} | 12 | 24 | 3 | 成功 | D0110:3, D0110:0, D0110:25, D0110:4, D0110:20, D0142:1, D0110:21, D0110:22, D0110:7, D0142:0, D0110:5, D0110:2 |
| 2 | 1 | search_chunks {"query":"conformal prediction methods assumptions exchangeability coverage guarantee","search_mode":"vector","doc_ids":null} | 12 | 0 | 0 | 成功 | D0092:0, D0110:0, D0110:25, D0092:1, D0110:21, D0110:3, D0110:23, D0093:0, D0092:30, D0110:22, D0093:22, D0092:2 |
| 3 | 2 | read_chunks {"doc_id":"D0110","ordinals":[7,8,9,10,11,12,13]} | 7 | 0 | 0 | 成功 | D0110:7, D0110:8, D0110:9, D0110:10, D0110:11, D0110:12, D0110:13 |
| 4 | 2 | read_chunks {"doc_id":"D0092","ordinals":[3,4,5,6]} | 4 | 0 | 0 | 成功 | D0092:3, D0092:4, D0092:5, D0092:6 |
| 5 | 2 | read_chunks {"doc_id":"D0142","ordinals":[2,3,4,5]} | 4 | 0 | 0 | 成功 | D0142:2, D0142:3, D0142:4, D0142:5 |
| 6 | 3 | read_chunks {"doc_id":"D0092","ordinals":[7,8,9,10,11]} | 5 | 0 | 0 | 成功 | D0092:7, D0092:8, D0092:9, D0092:10, D0092:11 |
| 7 | 4 | read_chunks {"doc_id":"D0092","ordinals":[12,13,14,15]} | 4 | 0 | 0 | 成功 | D0092:12, D0092:13, D0092:14, D0092:15 |

judge reasoning：

> The generated answer accurately captures the exchangeability requirement for traditional methods and the asymptotic guarantees for ACI/PID, but it does not explicitly discuss conditional coverage methods and their feature-space guarantees, so it is good but not perfect.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Traditional conformal methods require exchangeability for finite-sample coverage guarantees, while online methods like ACI and PID control provide asymptotic coverage guarantees under minimal assumptions about boundedness of scores. Conditional coverage methods require additional assumptions about the data distribution and model capacity, but aim for stronger guarantees about coverage across feature space.

**naive 最终答案**

> Based on the context, different conformal prediction methods have different guarantees and assumptions:
> 
> **Standard (split) conformal prediction:** Guarantees (1−α) marginal coverage (P(Y ∈ C(X)) ≥ 1−α). Assumes exchangeability (or i.i.d.) between calibration scores and the test score; the guarantee holds distribution-free for any data distribution.
> 
> **CP-Gen (general function classes):** Guarantees approximately valid population coverage (L_coverage ≤ α + ε₀ + ε_coverage, i.e., coverage ≥ 1−α−(ε₀+ε_coverage)) and 2ε_eff-near-optimal efficiency within class. Requires the function class to be "low-capacity" w.r.t. both coverage and efficiency loss (uniform concentration bounds, e.g., Comp(C)/n_cal for finite or VC/Rademacher classes), and the proof assumes the calibration data are i.i.d. (slightly stronger than exchangeability).
> 
> **CP-Gen-Recal (reconformalization):** Guarantees exact (1−α) finite-sample coverage, relying on exchangeability (via a recalibration data split); achieves near-optimal efficiency under additional regularity assumptions (O(ε_eff + ε_coverage + 1/√n_recal)).
> 
> **Conformal PID control (online):** Guarantees deterministic long-run coverage (1/T Σ err_t = α + o(1)) — not probabilistic, holding for all realizations, with no exchangeability and no probabilistic model on the data. Quantile tracking (P control) requires only bounded scores (bound may be unknown); error integration (I control) requires no assumptions on the scores whatsoever (can be unbounded), but the integrator must satisfy a saturation condition and the scorecaster can be arbitrary.

**community 最终答案**

> Based on the context, the different conformal prediction methods have these guarantees and assumptions:
> 
> **1. Vanilla (split/inductive) conformal prediction** (D0110, D0092)
> - Guarantee: valid marginal coverage P(Y ∈ C) ≥ 1−α (exact 1−α with randomization).
> - Assumption: exchangeability of the conformity scores (calibration ∪ test data i.i.d./exchangeable); the guarantee is distribution-free.
> 
> **2. CP-Gen (general function class)** (D0110)
> - Guarantee: approximately valid population coverage (≥ 1−α−(ε₀+ε_coverage)) and near-optimal efficiency (2ε_eff-near-optimal) within class.
> - Assumptions: calibration data i.i.d. (stronger than exchangeability); function class "low-capacity" (small uniform concentration ε for coverage/efficiency — e.g., finite classes or VC/Rademacher classes with K ≪ n parameters), giving O(√Comp(C)/n) bounds.
> 
> **3. CP-Gen-Recal (with reconformalization)** (D0110)
> - Guarantee: exact finite-sample (1−α) coverage.
> - Assumptions: exchangeability (guarantees coverage); near-optimal efficiency O(ε_eff+ε_coverage+1/√n) under additional regularity assumptions.
> 
> **4. Adaptive Conformal Inference (ACI)** (D0092)
> - Guarantee: long-run (time-average) coverage frequency → α, deterministically (rate O(1/T)).
> - Assumption: none on the data-generating distribution (no exchangeability/stationarity required). For approximate single-time coverage: hidden-Markov / small-shift assumptions (stationary chain, Lipschitz bounds), and step-size γ tuned to shift size.
> 
> **5. Conformal PID control** (D0142)
> - Guarantee: deterministic long-run coverage, with no probabilistic model on the data.
> - Assumptions: quantile tracking (P) needs bounded scores; error integration (I) needs no assumptions on scores (unbounded allowed), only a saturation condition on the integrator; scorecasting (D) additionally uses a scorecaster to predict next quantile.
> 
> **6. Distribution-shift variants** (D0092, related work)
> - Likelihood-ratio reweighting (Tibshirani): valid if the conditional distribution of Y|X is constant between train/test and the covariate likelihood ratio is known/accurately estimated.
> - f-divergence-robust method (Cauchois): valid whenever the two distributions are close (D_f ≤ ρ), giving a conservative α.
> 
> Common theme: standard methods hinge on exchangeability for exact coverage; online methods (ACI, PID) trade this for long-run coverage with weaker/no assumptions.

</details>

<a id="case-mdaqa-89"></a>

### mdaqa:89 — 评分与执行路径对照

**问题：** What role does pre-training play in addressing domain/topic shift challenges for table question answering?

**score：3→4（Δ+1）；rounds：4→4（Δ+0）。**

工具安排：naive 为第1轮2次、第2轮2次、第3轮2次；community 为第1轮2次、第2轮1次、第3轮2次。最终回答另占一轮。

两边均为 4 轮，但工具总数 6→5，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 30→34、文档 overview 4→35；工具结果字符数 106,400→133,371，QA token 75,141→97,581。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/9b746e02e7624101be6f25594c3ddacf.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/add1b393a6fe44f3b09822d3038726dd.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"pre-training role addressing domain shift topic shift table question answering","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0102:26, D0102:3, D0102:0, D0102:1, D0126:23, D0126:0, D0102:7, D0102:25, D0102:17, D0126:4, D0062:22, D0082:22 |
| 2 | 1 | search_chunks {"query":"domain shift generalization table QA pre-training","search_mode":"vector","doc_ids":null} | 12 | 0 | 0 | 成功 | D0102:3, D0102:5, D0126:0, D0102:26, D0126:26, D0126:1, D0102:1, D0126:25, D0126:27, D0102:23, D0102:17, D0102:25 |
| 3 | 2 | read_chunks {"doc_id":"D0126","ordinals":[4,5,6]} | 3 | 0 | 0 | 成功 | D0126:4, D0126:5, D0126:6 |
| 4 | 2 | read_chunks {"doc_id":"D0102","ordinals":[6,7,8]} | 3 | 0 | 0 | 成功 | D0102:6, D0102:7, D0102:8 |
| 5 | 3 | read_chunks {"doc_id":"D0126","ordinals":[7,8,9,10]} | 4 | 0 | 0 | 成功 | D0126:7, D0126:8, D0126:9, D0126:10 |
| 6 | 3 | search_chunks {"doc_ids":null,"query":"pretraining helps robustness topic shift domain shift table QA zero-shot unseen topics","search_mode":"keyword"} | 12 | 0 | 0 | 成功 | D0102:7, D0102:3, D0102:0, D0102:6, D0102:8, D0102:1, D0126:0, D0126:22, D0102:28, D0126:21, D0102:2, D0102:26 |

judge reasoning：

> The generated answer correctly captures that pre-training provides language understanding and parsing capabilities and that synthetic pre-training data helps improve cross-topic robustness, but it misses the specific 5-20% improvement figure and frames pre-training as 'limited' rather than directly mitigating performance drops, resulting in a good but slightly imprecise match.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"pre-training domain shift topic shift table question answering","search_mode":"hybrid","doc_ids":null} | 12 | 20 | 3 | 成功 | D0102:3, D0102:26, D0102:0, D0102:6, D0102:7, D0102:1, D0126:23, D0102:17, D0126:0, D0102:25, D0102:21, D0126:4 |
| 2 | 1 | search_chunks {"query":"pre-training role generalization to new domains tables","search_mode":"vector","doc_ids":null} | 12 | 15 | 2 | 成功 | D0126:26, D0126:27, D0107:21, D0126:25, D0102:26, D0123:14, D0062:24, D0102:25, D0126:0, D0130:17, D0084:50, D0126:1 |
| 3 | 2 | read_chunks {"doc_id":"D0126","ordinals":[5,6,7,8]} | 4 | 0 | 0 | 成功 | D0126:5, D0126:6, D0126:7, D0126:8 |
| 4 | 3 | search_chunks {"doc_ids":["D0126"],"query":"robust topical distributional shift pretraining unseen topics","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0126:22, D0126:0, D0126:26, D0126:21, D0126:23, D0126:14, D0126:17, D0126:1, D0126:2, D0126:4, D0126:15, D0126:16 |
| 5 | 3 | read_chunks {"doc_id":"D0102","ordinals":[2,4]} | 2 | 0 | 0 | 成功 | D0102:2, D0102:4 |

judge reasoning：

> The generated answer accurately captures the gold answer's core claim that pre-training, especially with synthetic data, improves robustness to topic shift in table QA, and its added nuance about open-domain pre-training being limited is consistent rather than contradictory.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Pre-training helps mitigate performance drops due to topic shift by providing better language understanding and parsing capabilities, with synthetic pre-training data showing 5-20% improvements in cross-topic performance even without access to target domain data.

**naive 最终答案**

> Pre-training plays a limited but foundational role. Open-domain pre-training (e.g., BERT/TaBERT on Wikipedia text) alone is **insufficient**: despite it, models still drop 5–6% in accuracy on unseen topics (topic shift / domain shift). However, pre-training endows models with language understanding and parsing capabilities, and **topic-specific pre-training/fine-tuning helps**: e.g., extending BERT's vocabulary with topic-specific words and fine-tuning on target-topic corpora yields topic-sensitive representations that improve query–table linking. Likewise, **omnivorous pre-training** (natural data for cross-format alignment + synthetic data for reasoning) makes models significantly more robust under topical distributional shift, outperforming baseline pre-trained models across all topics. So pre-training provides the base capability, but addressing topic shift requires additional topic-aware pre-training/adaptation rather than open-domain pre-training alone.

**community 最终答案**

> Pre-training plays an important but limited role in addressing domain/topic shift in table QA:
> 
> - **Open-domain pre-training alone is insufficient**: Despite pre-training on large open-domain corpora (e.g., BERT, Wikipedia), models like TaBERT still degrade 5–6% on unseen topics because their pretraining data has word/topic distributions distinct from target topics (T3QA/D0102). Additional topic-specific adaptation—vocabulary injection, synthetic question generation, and reranking—is needed.
> 
> - **Task-specific (omnivorous) pre-training improves robustness**: Pretraining on both natural table-text pairs (alignment) and synthetic SQL-derived data (reasoning) endows models with stronger cross-format alignment and reasoning. Under topical distributional shift (WTQ-TS), such pretrained models (OmniTab) outperform baselines (TAPEX) by a large margin across all topics, validating that pretraining confers robustness to topic shift, especially with few annotations (OmniTab/D0126).

</details>

<a id="case-mdaqa-92"></a>

### mdaqa:92 — 评分与执行路径对照

**问题：** What are the key differences in how neural networks handle feature interactions for auction price prediction versus conversion attribution?

**score：2→2（Δ+0）；rounds：8→9（Δ+1）。**

工具安排：naive 为第1轮2次、第2轮2次、第3轮2次、第4轮2次、第5轮2次、第6轮2次、第7轮2次；community 为第1轮2次、第2轮2次、第3轮2次、第4轮2次、第5轮2次、第6轮2次、第7轮2次、第8轮2次。最终回答另占一轮。

轮次增加 1，工具总数 14→16、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 91→92、文档 overview 39→124；工具结果字符数 389,703→529,463，QA token 478,852→771,730。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/b53a3126a3ed4577bf9ccb3b9dc75ad2.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/cb86ceb562904414960422e8a5f651be.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"neural network feature interactions auction price prediction","search_mode":"hybrid","doc_ids":null} | 12 | 4 | 0 | 成功 | D0031:8, D0104:6, D0031:3, D0104:22, D0031:4, D0031:28, D0104:33, D0104:17, D0058:5, D0104:18, D0027:10, D0031:29 |
| 2 | 1 | search_chunks {"query":"neural network feature interactions conversion attribution","search_mode":"hybrid","doc_ids":null} | 12 | 7 | 0 | 成功 | D0101:20, D0083:19, D0058:5, D0076:25, D0076:23, D0113:26, D0046:22, D0076:26, D0052:2, D0076:22, D0076:0, D0090:28 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"conversion attribution neural network feature interaction","search_mode":"keyword"} | 12 | 4 | 0 | 成功 | D0113:26, D0075:5, D0090:5, D0046:22, D0090:16, D0090:10, D0090:6, D0090:29, D0120:13, D0028:19, D0085:3, D0090:3 |
| 4 | 2 | search_chunks {"doc_ids":null,"query":"attribution modeling advertising multi-touch deep learning","search_mode":"hybrid"} | 12 | 2 | 0 | 成功 | D0104:34, D0034:20, D0031:0, D0101:20, D0062:25, D0104:31, D0034:19, D0076:26, D0104:0, D0031:4, D0104:30, D0046:22 |
| 5 | 3 | search_chunks {"doc_ids":null,"query":"Modeling Sequential Dependence Audience Multi-step Conversions Multi-task Learning Targeted Display Advertising","search_mode":"hybrid"} | 12 | 5 | 0 | 成功 | D0026:17, D0045:24, D0062:25, D0104:31, D0031:30, D0034:0, D0085:0, D0104:34, D0116:15, D0119:8, D0095:80, D0104:30 |
| 6 | 3 | search_chunks {"doc_ids":null,"query":"conversion attribution multi-step conversion multi-task learning display advertising","search_mode":"vector"} | 12 | 4 | 0 | 成功 | D0104:31, D0104:30, D0104:34, D0031:30, D0031:32, D0104:33, D0104:1, D0004:12, D0110:0, D0139:33, D0104:29, D0025:19 |
| 7 | 4 | search_chunks {"doc_ids":null,"query":"attribution modeling display advertising conversion credit touchpoints","search_mode":"keyword"} | 12 | 2 | 0 | 成功 | D0104:0, D0031:4, D0104:34, D0113:26, D0121:25, D0031:31, D0104:32, D0015:1, D0104:31, D0031:0, D0104:30, D0101:20 |
| 8 | 4 | search_chunks {"doc_ids":null,"query":"conversion attribution neural network feature interaction prediction","search_mode":"vector"} | 12 | 1 | 0 | 成功 | D0104:30, D0104:31, D0104:33, D0116:17, D0076:25, D0076:23, D0116:15, D0110:0, D0031:30, D0093:0, D0076:26, D0104:34 |
| 9 | 5 | search_chunks {"doc_ids":null,"query":"Attribution Modeling Increases Efficiency of Bidding in Display Advertising","search_mode":"hybrid"} | 12 | 1 | 0 | 成功 | D0104:0, D0031:0, D0031:4, D0110:0, D0104:34, D0104:31, D0031:30, D0142:16, D0104:1, D0110:2, D0104:29, D0031:1 |
| 10 | 5 | search_chunks {"doc_ids":null,"query":"Modeling the Sequential Dependence among Audience Multi-step Conversions with Multi-task Learning in Targeted Display Advertising","search_mode":"keyword"} | 12 | 3 | 0 | 成功 | D0095:0, D0135:1, D0059:3, D0062:25, D0085:0, D0038:1, D0034:0, D0119:0, D0119:8, D0062:3, D0135:0, D0059:20 |
| 11 | 6 | search_chunks {"doc_ids":null,"query":"conversion rate CVR prediction feature interaction neural network advertising","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0031:0, D0104:34, D0031:4, D0031:31, D0104:30, D0075:34, D0104:31, D0090:10, D0104:33, D0090:16, D0104:29, D0031:30 |
| 12 | 6 | search_chunks {"doc_ids":null,"query":"multi-step conversions sequential dependence audience multi-task targeted display","search_mode":"vector"} | 12 | 3 | 0 | 成功 | D0104:31, D0139:1, D0059:18, D0059:17, D0113:26, D0117:15, D0117:13, D0045:21, D0077:25, D0104:30, D0045:24, D0006:22 |
| 13 | 7 | search_chunks {"doc_ids":null,"query":"conversion attribution modeling increases efficiency bidding display advertising neural network","search_mode":"keyword"} | 12 | 1 | 0 | 成功 | D0104:0, D0031:0, D0043:3, D0031:4, D0110:5, D0113:26, D0031:31, D0031:9, D0031:8, D0075:5, D0083:2, D0046:22 |
| 14 | 7 | search_chunks {"doc_ids":null,"query":"attribution modeling conversion credit last click first click","search_mode":"vector"} | 12 | 2 | 0 | 成功 | D0104:31, D0089:3, D0076:26, D0076:0, D0076:23, D0116:0, D0004:12, D0104:33, D0089:51, D0019:16, D0052:18, D0117:13 |

judge reasoning：

> The generated answer correctly describes auction price prediction's feature handling but omits the conversion attribution side entirely, failing to capture the key distinction between temporal dependencies and feature correlations.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"neural network feature interactions auction price prediction","search_mode":"hybrid","doc_ids":null} | 12 | 39 | 5 | 成功 | D0031:8, D0104:6, D0031:3, D0104:22, D0031:28, D0031:4, D0104:33, D0104:18, D0058:5, D0104:17, D0027:10, D0031:29 |
| 2 | 1 | search_chunks {"query":"conversion attribution feature interactions neural network","search_mode":"hybrid","doc_ids":null} | 12 | 22 | 2 | 成功 | D0058:5, D0104:31, D0104:30, D0113:26, D0046:22, D0076:25, D0052:2, D0104:33, D0076:23, D0090:28, D0076:26, D0120:13 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"conversion attribution multi-step conversions display advertising model","search_mode":"hybrid"} | 12 | 5 | 1 | 成功 | D0104:34, D0104:31, D0104:30, D0031:0, D0104:32, D0104:0, D0031:29, D0038:0, D0034:0, D0031:30, D0038:3, D0046:22 |
| 4 | 2 | search_chunks {"doc_ids":null,"query":"attribution model feature interaction CTR OCR conversion prediction","search_mode":"hybrid"} | 12 | 8 | 1 | 成功 | D0104:22, D0104:23, D0031:0, D0104:30, D0075:34, D0104:31, D0090:16, D0104:16, D0135:3, D0075:14, D0104:29, D0075:35 |
| 5 | 3 | search_chunks {"doc_ids":null,"query":"Modeling Sequential Dependence Audience Multi-step Conversions Multi-task Learning Targeted Display Advertising","search_mode":"hybrid"} | 12 | 22 | 3 | 成功 | D0026:17, D0045:24, D0062:25, D0104:31, D0031:30, D0034:0, D0085:0, D0104:34, D0116:15, D0119:8, D0095:80, D0104:30 |
| 6 | 3 | search_chunks {"doc_ids":null,"query":"attribution modeling efficiency bidding display advertising","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0104:34, D0104:0, D0104:3, D0031:0, D0104:31, D0031:4, D0104:30, D0104:32, D0104:2, D0031:31, D0031:9, D0031:29 |
| 7 | 4 | search_chunks {"doc_ids":null,"query":"conversion rate prediction CVR feature interaction embedding attention","search_mode":"hybrid"} | 12 | 1 | 0 | 成功 | D0031:0, D0116:7, D0081:5, D0104:30, D0075:34, D0104:31, D0104:33, D0135:3, D0059:14, D0104:16, D0104:18, D0111:39 |
| 8 | 4 | search_chunks {"doc_ids":null,"query":"sequential dependence among audience multi-step conversions multi-task","search_mode":"vector"} | 12 | 1 | 0 | 成功 | D0104:31, D0116:15, D0116:17, D0139:1, D0139:32, D0139:33, D0116:0, D0116:16, D0091:24, D0059:18, D0104:33, D0077:25 |
| 9 | 5 | search_chunks {"doc_ids":null,"query":"attribution modeling conversion display advertising","search_mode":"keyword"} | 12 | 0 | 0 | 成功 | D0104:0, D0031:4, D0104:34, D0113:26, D0031:31, D0104:32, D0015:1, D0104:31, D0031:0, D0104:30, D0101:20, D0031:29 |
| 10 | 5 | search_chunks {"doc_ids":null,"query":"post-click conversion attribution credit ad touchpoint","search_mode":"hybrid"} | 12 | 10 | 2 | 成功 | D0089:3, D0113:26, D0019:16, D0031:0, D0031:17, D0076:0, D0049:28, D0089:51, D0104:31, D0121:25, D0029:0, D0089:59 |
| 11 | 6 | search_chunks {"doc_ids":null,"query":"attribution","search_mode":"keyword"} | 8 | 12 | 2 | 成功 | D0101:20, D0046:21, D0046:22, D0117:3, D0117:13, D0003:2, D0047:3, D0003:1 |
| 12 | 6 | search_chunks {"doc_ids":null,"query":"conversion attribution model feature interaction CTR prediction components","search_mode":"keyword"} | 12 | 0 | 0 | 成功 | D0075:34, D0090:16, D0090:3, D0138:8, D0135:3, D0031:0, D0075:14, D0104:22, D0075:35, D0090:10, D0041:7, D0113:26 |
| 13 | 7 | search_chunks {"doc_ids":null,"query":"conversion attribution modeling increases efficiency bidding","search_mode":"vector"} | 12 | 0 | 0 | 成功 | D0104:31, D0104:1, D0031:1, D0104:29, D0104:3, D0104:34, D0031:4, D0031:30, D0104:22, D0104:30, D0031:10, D0104:0 |
| 14 | 7 | search_chunks {"doc_ids":null,"query":"user response prediction click conversion rate feature interaction PNN FM AFM attention","search_mode":"vector"} | 12 | 0 | 0 | 成功 | D0104:31, D0104:33, D0104:30, D0104:16, D0104:22, D0104:25, D0104:18, D0104:29, D0104:23, D0139:33, D0116:15, D0056:16 |
| 15 | 8 | search_chunks {"doc_ids":null,"query":"sequential dependence multi-step conversions audience","search_mode":"hybrid"} | 12 | 4 | 1 | 成功 | D0139:1, D0045:24, D0095:80, D0113:26, D0089:38, D0131:33, D0038:1, D0104:31, D0034:0, D0117:13, D0034:5, D0089:3 |
| 16 | 8 | search_chunks {"doc_ids":null,"query":"bidding machine optimizing profits display advertising user response","search_mode":"vector"} | 12 | 0 | 0 | 成功 | D0104:29, D0104:1, D0104:34, D0104:3, D0031:1, D0104:2, D0104:0, D0031:29, D0031:0, D0104:6, D0031:3, D0104:33 |

judge reasoning：

> The generated answer correctly describes DLF's recurrent neural network approach for auction price prediction, but it omits the conversion attribution side (DNA's feature interaction with CIN/AutoInt) and the key distinction, misattributing those interaction components to ADM instead.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> For auction price prediction, DLF uses recurrent neural networks to model sequential price patterns and conditional probabilities, while for conversion attribution, DNA employs feature extractors and interaction components like CIN and AutoInt to capture 2-order feature relationships. The key distinction is that price prediction focuses on temporal dependencies, while conversion attribution emphasizes feature correlations between user, publisher and ad content.

**naive 最终答案**

> Based on the available context, I can only find information about feature interactions in auction price prediction (bid landscape forecasting), not conversion attribution.
> 
> **Auction price prediction (DLF and ADM models):**
> - DLF uses an LSTM (recurrent neural network) to model conditional winning probability over sequential price patterns in a discrete price space, without distributional assumptions.
> - ADM explicitly handles feature interactions by combining 1-order features, 2-order feature-interaction components (e.g., InnerProduct in PNN, FM, AFM, DCN-Mix's Cross Network, CIN, AutoInt's Interacting Layer, NFM's Bi-Interaction Layer, CF), and high-order features, then feeds them to a Softmax layer over price buckets.
> 
> **Conversion attribution:** The context only contains a reference to a related work titled "Modeling the Sequential Dependence among Audience Multi-step Conversions with Multi-task Learning in Targeted Display Advertising" (cited in D0104's reference list), but the document itself is not in this collection. No content about how neural networks handle feature interactions for conversion attribution is available.
> 
> I cannot establish the key differences in feature-interaction handling for conversion attribution, as that information is not present in the provided context.

**community 最终答案**

> Based on the available context, I can only answer for the auction price prediction side; the context does not contain a paper describing how neural networks handle feature interactions for conversion attribution.
> 
> For **auction price prediction** (winning price / bid landscape forecasting, e.g., DLF and ADM):
> - **DLF (Deep Landscape Forecasting)** uses a recurrent neural network (LSTM) to model the **sequential patterns of features over the price space** — the conditional winning probability is modeled step-by-step over price intervals via probability chain rule, with no distributional assumptions and censorship-aware losses.
> - **ADM (Arbitrary Distribution Modeling)** explicitly uses feature interaction: 1-order features (publisher/user/ad/context embeddings) are fed into a 2-order feature extractor (FM, CIN, AutoInt, PNN, AFM, DCN, NFM, etc. — components borrowed from CTR prediction) to capture 2-order interactions (treated like collaborative filtering between website and user features), plus MLP layers for high-order combinations, then concatenated and passed to a Softmax over price buckets. Most 2-order interaction components helped, except InnerProd/FM/AFM in their setting.
> 
> The context provides no information on how neural networks handle feature interactions for conversion attribution, so that part of the question cannot be established from the given documents.

</details>

<a id="case-mdaqa-94"></a>

### mdaqa:94 — 宽泛问题下，后续检索锁定了不同的比较对象

**问题：** What are the key differences in how recent neural approaches handle the challenge of limited contextual information in structured data extraction?

**score：2→1（Δ-1）；rounds：4→4（Δ+0）。**

naive 后续读 D0084，最终讲 TCN 但漏 PLAtE；community 后续始终限定 D0122，最终把比较对象变成 PLAtE 内部的 RoBERTa/DOM-LM/MarkupLM，遗漏 TCN，2→1 分。两边开头都召回 D0122，社区扩展没有保证跨论文对齐到 gold 的 PLAtE-versus-TCN。问题没有直接命名“these approaches”的对象，宽泛问法与全库检索形成歧义。应先确认对照对象再定向读取；不能简单把更多文档概览当成多文档推理已经完成。

工具安排：naive 为第1轮2次、第2轮1次、第3轮1次；community 为第1轮2次、第2轮2次、第3轮1次。最终回答另占一轮。

两边均为 4 轮，但工具总数 4→5，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 26→31、文档 overview 7→47；工具结果字符数 78,541→163,561，QA token 65,952→120,218。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

<details>
<summary>展开 judge 所提实体的字面证据核对</summary>

| 实体/术语 | naive工具中首次匹配 | naive答案 | community工具中首次匹配 | community答案 |
|---|---|---|---|---|
| PLAtE | 轮1/调用1/D0122:0 | 未匹配 | 轮1/调用1/D0122:0 | 出现 |
| TCN | 轮1/调用2/D0084:0 | 出现 | 轮1/调用1/D0084/overview | 未匹配 |

这里只检查指定字面串及字母数字边界，不评判上下文是否在讨论同一事实；未匹配不排除同义表述，出现也不代表正确采用。它用于区分“可能未召回”和“已出现但未展开”的复核入口，不能自动判定因果。

</details>

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/101198e1fb58493899d77d113226b9b1.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/5b1b9c831b214e8eb1b66860c6a5266e.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"neural approaches limited contextual information structured data extraction","search_mode":"hybrid","doc_ids":null} | 12 | 6 | 0 | 成功 | D0122:0, D0122:1, D0122:16, D0122:2, D0079:23, D0122:15, D0122:18, D0122:17, D0113:0, D0020:22, D0088:21, D0126:27 |
| 2 | 1 | search_chunks {"query":"key differences neural methods handling limited context structured extraction","search_mode":"vector","doc_ids":null} | 12 | 1 | 0 | 成功 | D0126:27, D0122:0, D0122:1, D0084:49, D0126:28, D0126:24, D0088:24, D0122:16, D0084:0, D0084:2, D0088:0, D0122:2 |
| 3 | 2 | read_chunks {"doc_id":"D0084","ordinals":[0,1,2,3]} | 4 | 0 | 0 | 成功 | D0084:0, D0084:1, D0084:2, D0084:3 |
| 4 | 3 | read_chunks {"doc_id":"D0084","ordinals":[4,5,6,7,8]} | 5 | 0 | 0 | 成功 | D0084:4, D0084:5, D0084:6, D0084:7, D0084:8 |

judge reasoning：

> The generated answer correctly addresses TCN and the general idea of using broader context, but it entirely omits PLAtE, which is one of the two key approaches in the gold answer, so it is only partially correct.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"neural approaches limited contextual information structured data extraction","search_mode":"hybrid","doc_ids":null} | 12 | 26 | 3 | 成功 | D0122:0, D0122:1, D0122:16, D0122:2, D0079:23, D0122:15, D0122:18, D0122:17, D0113:0, D0020:22, D0088:21, D0126:27 |
| 2 | 1 | search_chunks {"query":"limited context structured data extraction challenge","search_mode":"hybrid","doc_ids":null} | 12 | 21 | 3 | 成功 | D0122:0, D0122:1, D0122:16, D0122:18, D0122:15, D0122:17, D0002:3, D0084:2, D0084:49, D0088:21, D0045:8, D0084:52 |
| 3 | 2 | search_chunks {"doc_ids":["D0122"],"query":"abridged detail limited contextual information list pages DOM-LM MarkupLM RoBERTa","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0122:8, D0122:9, D0122:10, D0122:13, D0122:20, D0122:18, D0122:2, D0122:0, D0122:19, D0122:1, D0122:17, D0122:14 |
| 4 | 2 | read_chunks {"doc_id":"D0122","ordinals":[2,3,4,5,6]} | 5 | 0 | 0 | 成功 | D0122:2, D0122:3, D0122:4, D0122:5, D0122:6 |
| 5 | 3 | read_chunks {"doc_id":"D0122","ordinals":[7,8,9,10,11,12,13]} | 7 | 0 | 0 | 成功 | D0122:7, D0122:8, D0122:9, D0122:10, D0122:11, D0122:12, D0122:13 |

judge reasoning：

> The generated answer describes different models (RoBERTa, DOM-LM, MarkupLM) and does not mention the key facts about PLAtE and TCN or their architectures, so it only weakly addresses the gold answer.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> PLAtE addresses limited context by focusing on list-page extraction with intra-column cell correlation and inter-column relations, while TCN tackles it through a two-stage architecture combining node-level features with relational neural networks to capture both local and global contextual patterns. Both approaches aim to overcome the context limitation but differ in their architectural choices and feature representation strategies.

**naive 最终答案**

> Recent neural approaches differ mainly in whether they rely only on **intra-table context** or also exploit **inter-table context** to overcome limited context in structured data extraction (e.g., relational web tables):
> 
> - **Existing BERT-based approaches** (TaBERT, TURL, etc.) linearize table cells into long sequences and only capture related cell information **within the same table**, losing information implicit in tabular structure (e.g., cells in a column share a type).
> - **TCN (Table Convolutional Network)** instead aggregates context from a **collection of tables** as a graph, using both intra-table attention (informative cells in the same row/column) and three inter-table aggregation modules (cells with the same value, cells in the same schema position, cells linked to the same page topic), so it leverages the full context across tables rather than the limited context of a single table.

**community 最终答案**

> Based on the PLAtE study of list-page extraction (D0122), the three recent neural approaches differ in how they compensate for the limited (abridged) contextual information on list pages:
> 
> - **RoBERTa (text-only):** Uses only the text tokens from the DOM tree and ignores XPaths/HTML tags/other DOM structure. It handled attribute extraction best (F1 0.735), because it relies on text content rather than structure.
> - **DOM-LM (structural):** Encodes DOM context by slicing the tree into subtrees and representing each node by its tag, text, class/id attributes, plus a positional matrix. It uses structural info but tended to over-fit to HTML tags (e.g., misclassifying `<p>` nodes) and disregard text, so it generalized worse to unseen HTML structures.
> - **MarkupLM (XPath-based structure + pre-training):** Represents each node by an XPath embedding plus text, pre-trained on masked markup LM, node-relation prediction, and title-page matching. This structural/relational signal let it best identify product boundaries (segmentation F1 0.787).
> 
> Key differences in handling limited context: text-only modeling (RoBERTa) vs. explicit DOM-structure encoding (DOM-LM) vs. XPath/relation-based structure (MarkupLM); structure helps segmentation but can hurt attribute extraction by overfitting tags; performance also improves when pages contain more products (more in-page examples/context to learn patterns from).

</details>

<a id="case-mdaqa-95"></a>

### mdaqa:95 — 评分与执行路径对照

**问题：** What are the key differences between fixed margin and adaptive margin approaches in few-shot learning?

**score：4→4（Δ+0）；rounds：3→2（Δ-1）。**

工具安排：naive 为第1轮1次、第2轮1次；community 为第1轮1次。最终回答另占一轮。

轮次减少 1，工具总数 2→1、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 13→12、文档 overview 2→8；工具结果字符数 39,322→38,865，QA token 23,099→12,835。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/4ae8ebd1bc5a4683a6476e279efcb524.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/cee6ffcd743a4e8d820536119f88d8d2.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"fixed margin vs adaptive margin few-shot learning","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0069:0, D0069:2, D0069:18, D0069:1, D0069:17, D0069:3, D0069:6, D0069:4, D0069:19, D0069:7, D0069:8, D0028:32 |
| 2 | 2 | read_chunks {"doc_id":"D0069","ordinals":[5,6,7,8]} | 4 | 0 | 0 | 成功 | D0069:5, D0069:6, D0069:7, D0069:8 |

judge reasoning：

> The generated answer accurately captures all key differences, including fixed constant margins versus adaptive semantic-similarity-based margins, with correct directionality and outcomes, and any omission of the specific 15% figure does not detract from the core meaning.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"fixed margin adaptive margin few-shot learning","search_mode":"hybrid","doc_ids":null} | 12 | 8 | 2 | 成功 | D0069:0, D0069:2, D0069:18, D0069:1, D0069:3, D0069:17, D0069:4, D0069:19, D0069:6, D0069:7, D0069:8, D0069:20 |

judge reasoning：

> The generated answer accurately captures all key differences between fixed and adaptive margin approaches, including the constant vs. semantic-similarity-based margins, the direction of margin adjustment, and the resulting better generalization, with no contradictions or missing core facts.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> Fixed margin approaches add a constant margin between all class pairs, while adaptive margin uses semantic similarity between classes to determine appropriate margins - larger margins for similar classes and smaller margins for dissimilar ones. Adaptive margins lead to more discriminative feature embeddings and better generalization, showing 15% relative improvement in few-shot classification accuracy.

**naive 最终答案**

> **Fixed margin (naive additive margin loss, NAML):** assumes all classes are equally far apart and adds a *fixed* margin among all classes. It has limited effectiveness and can cause mistakes on test samples of similar classes, especially in FSL where very few labeled samples are available.
> 
> **Adaptive margin (CRAML/TRAML):** generates a *class- or task-specific* margin based on semantic similarity between classes (measured via word embeddings like GloVe). The margin is larger for similar classes and smaller for dissimilar classes, which separates similar classes better, learns a more discriminative embedding space, and yields stronger generalization, outperforming the fixed margin.

**community 最终答案**

> Based on the context (the Adaptive Margin for Few-Shot Learning paper):
> 
> **Fixed margin:** Assumes all classes should be equally far apart and adds a fixed margin among all classes. It can cause mistakes on test samples of similar classes, especially in FSL where very few labeled samples are available for novel classes. Simply adding a fixed margin has limited effectiveness in FSL.
> 
> **Adaptive margin:** The margin between similar classes should be larger than that between dissimilar classes. Margins are generated adaptively from semantic similarity between classes (class-relevant, via semantic word vectors) or from the semantic context among all classes in a task (task-relevant). This yields a more discriminative embedding space and better generalization to novel classes, outperforming fixed/naive margins.

</details>

<a id="case-mdaqa-97"></a>

### mdaqa:97 — 评分与执行路径对照

**问题：** What are the key methodological differences in how these approaches validate the statistical significance of discovered concepts?

**score：4→4（Δ+0）；rounds：3→5（Δ+2）。**

工具安排：naive 为第1轮2次、第2轮2次；community 为第1轮2次、第2轮2次、第3轮2次、第4轮2次。最终回答另占一轮。

轮次增加 2，工具总数 4→8、错误 0→0，整轮全部工具报错的轮数 0→0。这些计数把实际查询/读取安排与失败恢复分开；它们不支持将全部轮次差机械归因于社区。

每题内去重的 chunk 40→42、文档 overview 14→37；工具结果字符数 122,539→203,060，QA token 56,858→168,512。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分不变仅表示本次 0–4 量表结果相同，不保证答案完全等价；可比较下方两份 reasoning 是否仍保留共同缺项。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/1824b6ae7039444282ed34efe9ad9549.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/a0bf6eda29634f9099e234fc84186676.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"validate statistical significance of discovered concepts","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0140:2, D0101:2, D0140:0, D0101:25, D0140:15, D0140:8, D0101:3, D0140:4, D0140:3, D0140:1, D0140:21, D0140:20 |
| 2 | 1 | search_chunks {"query":"statistical significance testing concept discovery methods","search_mode":"hybrid","doc_ids":null} | 12 | 5 | 0 | 成功 | D0140:2, D0101:0, D0140:24, D0082:0, D0140:0, D0140:1, D0012:28, D0020:23, D0140:5, D0140:23, D0123:19, D0011:6 |
| 3 | 2 | search_chunks {"doc_ids":null,"query":"p-value hypothesis test confidence significance concept","search_mode":"keyword"} | 12 | 7 | 0 | 成功 | D0095:5, D0103:8, D0013:26, D0140:0, D0140:8, D0004:6, D0038:4, D0140:3, D0013:2, D0140:2, D0079:11, D0134:10 |
| 4 | 2 | search_chunks {"doc_ids":["D0101"],"query":"causal influence mutual information validate significance","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0101:17, D0101:10, D0101:5, D0101:18, D0101:16, D0101:19, D0101:4, D0101:0, D0101:1, D0101:15, D0101:6, D0101:11 |

judge reasoning：

> The generated answer fully and accurately captures the core methodological difference between the approaches, including FDR control via knockoffs and causal-effect validation via information flow/transition effects, with no contradictions.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"validate statistical significance of discovered concepts","search_mode":"hybrid","doc_ids":null} | 12 | 33 | 5 | 成功 | D0140:2, D0101:2, D0140:0, D0101:25, D0140:15, D0140:8, D0101:3, D0140:4, D0140:3, D0140:1, D0140:21, D0129:6 |
| 2 | 1 | search_chunks {"query":"statistical significance testing concept discovery permutation baseline","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0140:2, D0140:24, D0101:0, D0140:0, D0082:0, D0140:5, D0140:23, D0011:6, D0123:19, D0011:15, D0101:3, D0013:10 |
| 3 | 2 | search_chunks {"doc_ids":["D0101"],"query":"statistical significance validation concept causal influence mutual information p-value confidence","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0101:17, D0101:11, D0101:16, D0101:10, D0101:6, D0101:5, D0101:4, D0101:0, D0101:19, D0101:1, D0101:18, D0101:15 |
| 4 | 2 | read_chunks {"doc_id":"D0140","ordinals":[5,6,7,8,9]} | 5 | 0 | 0 | 成功 | D0140:5, D0140:6, D0140:7, D0140:8, D0140:9 |
| 5 | 3 | read_chunks {"doc_id":"D0076","ordinals":[0,1,2,3]} | 4 | 0 | 0 | 成功 | D0076:0, D0076:1, D0076:2, D0076:3 |
| 6 | 3 | read_chunks {"doc_id":"D0101","ordinals":[16,17]} | 2 | 0 | 0 | 成功 | D0101:16, D0101:17 |
| 7 | 4 | search_chunks {"doc_ids":null,"query":"concept discovery statistical significance test hypothesis testing concept activation","search_mode":"hybrid"} | 12 | 0 | 0 | 成功 | D0140:24, D0140:0, D0140:2, D0101:4, D0101:0, D0140:23, D0082:0, D0140:3, D0140:5, D0101:1, D0140:4, D0129:6 |
| 8 | 4 | search_chunks {"doc_ids":null,"query":"discovered concepts reliability validation randomization null hypothesis","search_mode":"hybrid"} | 12 | 1 | 0 | 成功 | D0140:2, D0140:1, D0140:0, D0101:2, D0140:23, D0101:3, D0140:4, D0129:5, D0101:0, D0093:23, D0089:11, D0101:25 |

judge reasoning：

> The generated answer accurately captures the core distinction: knockoff-based validation controls FDR with formal guarantees, while the binary concept approach uses causal influence/information flow metrics, and it adds consistent supporting details without contradicting the gold answers.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> The approaches differ significantly in validation: The knockoff-based method provides formal statistical guarantees by controlling the false discovery rate (FDR) of selected concepts through comparison with knockoff samples, while the binary concept approach relies on measuring causal influence through information flow metrics and transition probabilities between classes. The knockoff method offers more rigorous statistical validation but requires additional computation to generate knockoff samples.

**naive 最终答案**

> Based on the two concept-discovery approaches in the collection, the key methodological differences in validating significance are:
> 
> **Knockoff/FDR-based approach (D0140):** Validates concepts by **controlling the False Discovery Rate (FDR)** of selected concepts below a prescribed level q. It generates Model-X Knockoff samples of the learned concepts, compares linear-model coefficients on original vs. knockoff features (statistic Wⱼ), and selects concepts with a data-dependent threshold guaranteeing FDR ≤ q — a formal statistical significance guarantee. The paper explicitly shows Knockoffs control FDR while **L1 regularization does not**.
> 
> **Causal binary-concept approach (D0101):** Does not use hypothesis testing or FDR. Instead it validates discovered concepts through **causal-effect magnitude** — maximizing information flow (mutual information I(γ;Y)) from binary switches to the classifier output, and evaluating the **Total Transition Effect (TTE)** via do-interventions (how alternating each binary switch changes predictions). Significance here is judged by the size of causal influence rather than a statistical error-rate guarantee.
> 
> In short: one provides formal statistical guarantees by controlling the false-discovery rate (Knockoff), while the other relies on causal-effect quantities (mutual information / total transition effect) rather than statistical significance tests.

**community 最终答案**

> Based on the retrieved context, the key methodological difference is between a formal error-rate guarantee versus causal-effect magnitude evaluation:
> 
> - **Knockoff-based concept selection (D0140):** Validates statistical significance by controlling the **False Discovery Rate (FDR)** below a prescribed level q. It generates **Model-X Knockoff samples** of the learned concepts, compares L1-regularized linear-model coefficients of original vs. knockoff variables (statistic W_j), and selects concepts via a threshold τ derived from Theorem 1 (Candès et al.), which provably guarantees FDR ≤ q. The paper explicitly shows Knockoffs control FDR (e.g., q=0.1) while L1-based selection does not.
> 
> - **Causal binary concept discovery (D0101, cf. D0076):** Does not perform formal significance testing. Instead, it validates concepts by measuring the **magnitude of causal influence** — information flow/mutual information I(γ;Y) between binary switches and classifier output (with an estimated prior p*(γ)) and the **Total Transition Effect (TTE)** at test time — and checks **consistency across runs** (similarity of prediction transition graphs) to guard against cherry-picking. "Significance" here is a large causal effect, not an error-rate guarantee.

</details>

<a id="case-mdaqa-98"></a>

### mdaqa:98 — 同一轮不等于同一检索工作量，关键对照项遗漏

**问题：** How do these methods handle the potential correlation between discovered concepts while maintaining causal interpretability?

**score：4→2（Δ-2）；rounds：2→2（Δ+0）。**

两边均为 2 轮，但 naive 首轮发两条查询，第二条带回 D0076 关于 latent-factor independence 的原文，最终对比“建模相关性”与“假设独立”；community 首轮只发一条查询，虽通过扩展知道 D0076，却仅概述因果/非因果分离，漏掉独立性假设，4→2。这包含首轮规划和原文细节覆盖差异；不能把少一个查询归因为先看到社区后提前停止，因为同轮请求在看到结果前已计划完成。

工具安排：naive 为第1轮2次；community 为第1轮1次。最终回答另占一轮。

两边均为 2 轮，但工具总数 2→1，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 19→12、文档 overview 5→20；工具结果字符数 60,342→52,690，QA token 20,053→16,426。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/313aaef55b3d40eda4c737f25f483156.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/2a3664dad79f42248ce6000f2659bedb.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"correlation between discovered concepts causal interpretability","search_mode":"hybrid","doc_ids":null} | 12 | 3 | 0 | 成功 | D0140:23, D0101:0, D0101:2, D0076:0, D0140:1, D0101:3, D0101:10, D0101:19, D0140:2, D0101:25, D0101:1, D0076:3 |
| 2 | 1 | search_chunks {"query":"concept discovery methods handle correlation independence","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0140:2, D0101:0, D0076:10, D0140:1, D0140:23, D0140:3, D0140:0, D0093:22, D0140:5, D0101:3, D0110:53, D0101:4 |

judge reasoning：

> The generated answer accurately captures both key gold points: the binary concept method models correlations via the empirical prior p*(γ), while the generative causal explanation method assumes independence to justify mutual information, and the additional knockoff information does not contradict the gold answer.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"correlation between discovered concepts causal interpretability","search_mode":"hybrid","doc_ids":null} | 12 | 20 | 3 | 成功 | D0140:23, D0101:0, D0101:2, D0076:0, D0140:1, D0101:3, D0101:10, D0101:19, D0140:2, D0101:25, D0076:3, D0101:1 |

judge reasoning：

> The generated answer correctly describes the binary concept method's correlated prior p*(γ) and causal influence metric, but omits the key contrasting fact that the generative causal explanation method assumes independence between latent factors and may miss concept interactions, making the answer incomplete.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> The methods take contrasting approaches: The binary concept method explicitly acknowledges and models concept correlations through an empirically estimated prior distribution p*(γ), arguing that useful concepts are often causally dependent on class information. In contrast, the generative causal explanation method assumes independence between latent factors to simplify the causal influence metric to mutual information, potentially missing important concept interactions.

**naive 最终答案**

> The methods take different stances on concept correlation:
> 
> - **Unsupervised Causal Binary Concepts (D0101):** It rejects the standard VAE independence assumption. Because useful causal concepts are often mutually correlated (they causally depend on the class), it employs an empirical prior p*(γ) that allows and reflects correlation between binary concepts. The factorized posterior q(γ|x) only assumes independence conditioned on a sample and does not imply global independence of the binary switches. Causal interpretability is kept by measuring the information flow from the binary switches to the classifier output, using the data-reflecting (dependent) prior to avoid estimation error.
> 
> - **Concept selection via Model Knockoffs (D0140):** It handles correlation/confounding among concepts by selecting statistically significant concepts with the Model-X Knockoff filter while controlling the False Discovery Rate (FDR), plus Concept Sparsity Regularization (L1 on prediction coefficients). This removes false-positive/confounding concepts (e.g., correlated but non-causal background), so the selected concepts remain reliably interpretable.
> 
> - **Generative causal explanations (D0076):** In contrast, it assumes the latent factors are independent (based on the VAE ELBO properties), and uses that independence to give the mutual-information metric a causal interpretation as information flow; the correlation is thus assumed away rather than modeled.
> 
> So, briefly: D0101 explicitly models the correlation between concepts via an empirical dependent prior while preserving causality through information flow; D0140 uses FDR-controlled Knockoff selection to discard confounding correlated concepts; D0076 assumes factor independence to justify its causal interpretation.

**community 最终答案**

> Based on the context (chiefly D0101, with D0076/D0140 as related methods):
> 
> - Rather than assuming independence of latent factors (as standard VAEs do, via a factorized prior), the method employs a prior p*(γ) that **allows correlation between causal binary concepts**. This is justified because useful concepts (e.g., the middle and bottom strokes of "E") are mutually correlated, and a factorized prior would cause large estimation error and hinder discovery of causal concepts.
> - p*(γ) is estimated empirically from the data using the variational posterior q(γ|x); the factorized posterior only assumes conditional independence given a sample, which does not imply independence of binary switches in p*(γ). The method does not aim to learn the dependence, only to let p*(γ) reflect the correlation present in the data.
> - Causal interpretability is maintained by measuring each concept's causal influence via information flow I(γ;Y) from the binary switch to the classifier output (using a causal DAG), and by separating causal binary switches from concept-specific and global variants, so only causal influences drive the explanation. Related work (D0076) similarly separates causal (α) and non-causal (β) factors maximizing causal influence; D0140 uses knockoffs/FDR control to remove confounding, correlated concepts from explanations.

</details>

<a id="case-mdaqa-99"></a>

### mdaqa:99 — 评分与执行路径对照

**问题：** How do the approaches to handling uncertainty in partially observed environments fundamentally differ between belief entropy minimization and expected free energy minimization?

**score：3→2（Δ-1）；rounds：4→4（Δ+0）。**

工具安排：naive 为第1轮2次、第2轮2次、第3轮1次；community 为第1轮1次、第2轮2次、第3轮1次。最终回答另占一轮。

两边均为 4 轮，但工具总数 5→4，同轮并发安排及工具工作量仍可能不同。

每题内去重的 chunk 27→23、文档 overview 3→11；工具结果字符数 70,506→63,743，QA token 63,719→53,186。字符数不是 token，也不是多轮历史重复输入后的累计量。

首轮整组工具请求不同，这一差异发生在看到任何社区结果之前；首轮规划差不能反向归因于社区。

评分变化的直接记录依据是下方两个 judge reasoning；同时保留 gold 和两份完整答案，可逐项核查其所称的缺失、数字错误或表述差异。当前单对 trace 没有独立分离查询变化、扩展材料、答案综合和 judge 尺度的贡献，故不把 judge 的因果判断当作已验证事实。

[naive完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/5f2876689a5c41ff8e83d5a519a98785.json) · [community完整trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/server/data/runs/mdaqa_first_100_naive_community/traces/d7b5e25f5f6c4d4f8b20127486cb4330.json)

<details>
<summary>展开全部工具时序与 judge 原始理由</summary>

**naive**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"belief entropy minimization partially observed environments","search_mode":"hybrid","doc_ids":null} | 12 | 2 | 0 | 成功 | D0105:3, D0105:2, D0105:0, D0105:5, D0105:4, D0105:1, D0105:23, D0105:9, D0105:7, D0105:14, D0072:20, D0072:0 |
| 2 | 1 | search_chunks {"query":"expected free energy minimization uncertainty active inference","search_mode":"hybrid","doc_ids":null} | 12 | 1 | 0 | 成功 | D0072:19, D0072:0, D0072:1, D0072:20, D0072:18, D0072:16, D0072:2, D0110:21, D0072:15, D0072:25, D0072:23, D0110:23 |
| 3 | 2 | read_chunks {"doc_id":"D0072","ordinals":[2,3,4,5]} | 4 | 0 | 0 | 成功 | D0072:2, D0072:3, D0072:4, D0072:5 |
| 4 | 2 | read_chunks {"doc_id":"D0105","ordinals":[7,8]} | 2 | 0 | 0 | 成功 | D0105:7, D0105:8 |
| 5 | 3 | read_chunks {"doc_id":"D0072","ordinals":[6]} | 1 | 0 | 0 | 成功 | D0072:6 |

judge reasoning：

> The answer correctly captures the EFE decomposition and exploration-exploitation trade-offs, but it slightly contradicts the gold answer by saying belief entropy minimization alone does not incentivize control, whereas the gold answer attributes control to belief entropy minimization through latent state visitation entropy.

**community**

| 调用序号 | 模型轮 | 工具与完整参数 | chunk数 | 新增overview | 新增社区 | 状态 | 返回chunk（doc_id:ordinal） |
|---|---|---|---|---|---|---|---|
| 1 | 1 | search_chunks {"query":"belief entropy minimization expected free energy minimization uncertainty partially observed environments","search_mode":"hybrid","doc_ids":null} | 12 | 11 | 2 | 成功 | D0105:3, D0105:2, D0105:4, D0105:23, D0105:0, D0105:5, D0072:1, D0072:0, D0105:1, D0105:9, D0105:12, D0072:20 |
| 2 | 2 | read_chunks {"doc_id":"D0105","ordinals":[6,7,8,10,11,13]} | 6 | 0 | 0 | 成功 | D0105:6, D0105:7, D0105:8, D0105:10, D0105:11, D0105:13 |
| 3 | 2 | read_chunks {"doc_id":"D0072","ordinals":[2,3,4,5]} | 4 | 0 | 0 | 成功 | D0072:2, D0072:3, D0072:4, D0072:5 |
| 4 | 3 | read_chunks {"doc_id":"D0072","ordinals":[5,6]} | 2 | 0 | 0 | 成功 | D0072:5, D0072:6 |

judge reasoning：

> The response correctly describes EFE's decomposed uncertainty terms, but it contradicts the gold answer by claiming belief entropy minimization only gathers information and does not incentivize control, missing a key distinction.

</details>

<details>
<summary>展开完整 gold 与两份最终答案</summary>

**Gold（保持结果文件中的原始内容；部分条目本身为序列化字典字符串）**

Gold 1：

> While belief entropy minimization directly optimizes the entropy of latent state visitation to encourage both information gathering and control, expected free energy minimization decomposes into separate terms for reducing uncertainty about latent states and model parameters. The former leads to more direct control behaviors while the latter enables explicit exploration-exploitation trade-offs through distinct information gain terms.

**naive 最终答案**

> The two approaches differ fundamentally in what drives action selection:
> 
> - **Belief entropy minimization** (IC2, D0105): The agent acts to minimize the entropy of its belief about the latent state (equivalently, maximize expected latent-state information gain / active state estimation). It only incentivizes *gathering informative observations* — it does not incentivize stabilizing the environment, so once the world is made predictable the agent is agnostic to (won't resist) future changes. Minimizing the *latent visitation* entropy extends this by also incentivizing preventing the environment from changing.
> 
> - **Expected free energy (EFE) minimization** (active inference, D0072): Action selection minimizes expected free energy, which is a composite objective with three terms: (a) likelihood of desired observations (reward/pragmatic value), (b) mutual information between beliefs before and after a new observation (epistemic value — resolving state uncertainty), and (c) expected information gain about model parameters (active learning/curiosity). Thus it explicitly *balances* goal-directed (pragmatic) and uncertainty-reducing (epistemic and active-learning) components, rather than minimizing belief entropy alone.
> 
> In short: belief entropy minimization is purely information-gathering about the latent state (with latent-visitation entropy adding control/stabilization), whereas EFE minimization simultaneously weighs desired outcomes, state uncertainty reduction, and parameter uncertainty reduction.

**community 最终答案**

> The two approaches differ fundamentally in scope and objective:
> 
> **Belief entropy minimization** (IC2) is purely epistemic: it reduces uncertainty in the current belief about the latent state, which is equivalent to maximizing expected latent-state information gain (active state estimation). It only incentivizes gathering informative observations and making the environment predictable — but it is agnostic to future changes and does not incentivize stabilizing/controlling the environment or resisting predictable change. It ignores preferences (reward) and model-parameter uncertainty.
> 
> **Expected free energy (EFE) minimization** (active inference) is a composite objective decomposed into three terms: (a) pragmatic reward-seeking (likelihood of desired observations), (b) epistemic value — the mutual information between beliefs before and after a new observation (i.e., resolving state uncertainty, akin to belief entropy reduction), and (c) active learning — reducing uncertainty about model parameters (novelty/curiosity). Thus EFE subsumes belief-entropy reduction as only one component, while also balancing goal-directed behavior and parameter uncertainty reduction over future horizons.
> 
> In short: belief entropy minimization only targets current state uncertainty via information gathering (once certain, it stops), whereas EFE minimization jointly trades off uncertainty resolution, model-parameter learning, and preferred-outcome pursuit.

</details>

## 8. 全部 100 题总表

| QA ID | score N→C | Δscore | rounds N→C | Δrounds | 工具N→C | 错误N→C | QA token N→C | 诊断 |
|---|---|---|---|---|---|---|---|---|
| mdaqa:0 | 3→4 | +1 | 3→3 | +0 | 3→4 | 0→0 | 37,678→57,487 | [mdaqa:0](#case-mdaqa-0) |
| mdaqa:1 | 4→4 | +0 | 3→3 | +0 | 4→4 | 0→0 | 43,920→64,618 | 两项不变 |
| mdaqa:2 | 1→0 | -1 | 13→9 | -4 | 24→16 | 0→0 | 1,087,758→603,307 | [mdaqa:2](#case-mdaqa-2) |
| mdaqa:3 | 4→4 | +0 | 3→3 | +0 | 3→3 | 0→0 | 40,245→32,896 | 两项不变 |
| mdaqa:4 | 4→4 | +0 | 3→4 | +1 | 4→5 | 0→0 | 39,509→86,487 | [mdaqa:4](#case-mdaqa-4) |
| mdaqa:5 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 19,570→24,854 | 两项不变 |
| mdaqa:6 | 4→4 | +0 | 3→3 | +0 | 4→4 | 0→0 | 48,809→68,807 | 两项不变 |
| mdaqa:7 | 2→2 | +0 | 2→3 | +1 | 2→3 | 0→0 | 19,348→44,690 | [mdaqa:7](#case-mdaqa-7) |
| mdaqa:8 | 4→4 | +0 | 3→2 | -1 | 3→2 | 0→0 | 31,554→23,436 | [mdaqa:8](#case-mdaqa-8) |
| mdaqa:9 | 2→2 | +0 | 4→4 | +0 | 6→6 | 0→0 | 95,689→116,981 | 两项不变 |
| mdaqa:10 | 3→4 | +1 | 3→2 | -1 | 4→2 | 0→0 | 49,327→22,561 | [mdaqa:10](#case-mdaqa-10) |
| mdaqa:11 | 4→2 | -2 | 2→2 | +0 | 1→1 | 0→0 | 11,281→15,698 | [mdaqa:11](#case-mdaqa-11) |
| mdaqa:12 | 3→3 | +0 | 2→2 | +0 | 2→2 | 0→0 | 19,759→23,865 | 两项不变 |
| mdaqa:13 | 3→2 | -1 | 5→3 | -2 | 8→4 | 2→0 | 95,387→62,486 | [mdaqa:13](#case-mdaqa-13) |
| mdaqa:14 | 4→4 | +0 | 3→4 | +1 | 3→6 | 0→1 | 32,944→95,165 | [mdaqa:14](#case-mdaqa-14) |
| mdaqa:15 | 2→2 | +0 | 2→2 | +0 | 1→1 | 0→0 | 11,091→15,968 | 两项不变 |
| mdaqa:16 | 4→2 | -2 | 2→2 | +0 | 2→2 | 0→0 | 19,708→31,819 | [mdaqa:16](#case-mdaqa-16) |
| mdaqa:17 | 4→3 | -1 | 4→3 | -1 | 4→4 | 1→0 | 50,661→63,467 | [mdaqa:17](#case-mdaqa-17) |
| mdaqa:18 | 4→4 | +0 | 2→2 | +0 | 1→1 | 0→0 | 11,693→20,934 | 两项不变 |
| mdaqa:19 | 3→3 | +0 | 3→2 | -1 | 2→2 | 0→0 | 25,631→34,113 | [mdaqa:19](#case-mdaqa-19) |
| mdaqa:20 | 4→2 | -2 | 2→2 | +0 | 1→2 | 0→0 | 12,108→28,868 | [mdaqa:20](#case-mdaqa-20) |
| mdaqa:21 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 18,888→27,489 | 两项不变 |
| mdaqa:22 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 18,662→27,608 | 两项不变 |
| mdaqa:23 | 4→3 | -1 | 2→2 | +0 | 1→1 | 0→0 | 11,964→19,817 | [mdaqa:23](#case-mdaqa-23) |
| mdaqa:24 | 2→2 | +0 | 3→3 | +0 | 4→4 | 0→0 | 41,784→54,583 | 两项不变 |
| mdaqa:25 | 4→4 | +0 | 3→2 | -1 | 3→2 | 0→0 | 42,058→26,304 | [mdaqa:25](#case-mdaqa-25) |
| mdaqa:26 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 19,029→26,456 | 两项不变 |
| mdaqa:27 | 2→2 | +0 | 8→4 | -4 | 13→6 | 2→0 | 249,986→88,918 | [mdaqa:27](#case-mdaqa-27) |
| mdaqa:28 | 4→4 | +0 | 3→3 | +0 | 3→3 | 1→1 | 30,934→47,066 | 两项不变 |
| mdaqa:29 | 2→2 | +0 | 3→2 | -1 | 3→2 | 0→0 | 34,379→31,223 | [mdaqa:29](#case-mdaqa-29) |
| mdaqa:30 | 2→2 | +0 | 2→2 | +0 | 2→1 | 0→0 | 19,295→17,864 | 两项不变 |
| mdaqa:31 | 2→3 | +1 | 3→2 | -1 | 4→1 | 0→0 | 58,085→23,449 | [mdaqa:31](#case-mdaqa-31) |
| mdaqa:32 | 4→4 | +0 | 4→3 | -1 | 8→4 | 3→0 | 66,718→81,252 | [mdaqa:32](#case-mdaqa-32) |
| mdaqa:33 | 4→0 | -4 | 2→3 | +1 | 2→4 | 0→0 | 19,135→54,834 | [mdaqa:33](#case-mdaqa-33) |
| mdaqa:34 | 4→2 | -2 | 3→3 | +0 | 4→4 | 0→0 | 52,438→56,980 | [mdaqa:34](#case-mdaqa-34) |
| mdaqa:35 | 2→3 | +1 | 2→2 | +0 | 2→2 | 0→0 | 20,181→26,711 | [mdaqa:35](#case-mdaqa-35) |
| mdaqa:36 | 1→0 | -1 | 5→8 | +3 | 8→15 | 0→0 | 180,638→662,221 | [mdaqa:36](#case-mdaqa-36) |
| mdaqa:37 | 3→4 | +1 | 2→3 | +1 | 2→4 | 0→0 | 20,044→62,597 | [mdaqa:37](#case-mdaqa-37) |
| mdaqa:38 | 2→4 | +2 | 2→5 | +3 | 2→8 | 0→4 | 19,082→102,386 | [mdaqa:38](#case-mdaqa-38) |
| mdaqa:39 | 2→2 | +0 | 2→2 | +0 | 2→2 | 0→0 | 19,355→23,483 | 两项不变 |
| mdaqa:40 | 2→2 | +0 | 5→4 | -1 | 7→6 | 0→0 | 113,714→101,847 | [mdaqa:40](#case-mdaqa-40) |
| mdaqa:41 | 3→4 | +1 | 3→5 | +2 | 4→7 | 1→0 | 45,893→190,102 | [mdaqa:41](#case-mdaqa-41) |
| mdaqa:42 | 0→4 | +4 | 4→4 | +0 | 5→6 | 0→0 | 100,866→136,181 | [mdaqa:42](#case-mdaqa-42) |
| mdaqa:43 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 18,859→22,971 | 两项不变 |
| mdaqa:44 | 4→3 | -1 | 3→2 | -1 | 4→2 | 0→0 | 54,481→26,699 | [mdaqa:44](#case-mdaqa-44) |
| mdaqa:45 | 4→3 | -1 | 2→2 | +0 | 1→2 | 0→0 | 11,080→24,000 | [mdaqa:45](#case-mdaqa-45) |
| mdaqa:46 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 19,575→26,629 | 两项不变 |
| mdaqa:47 | 1→1 | +0 | 2→2 | +0 | 2→2 | 0→0 | 19,496→26,291 | 两项不变 |
| mdaqa:48 | 4→4 | +0 | 2→2 | +0 | 1→2 | 0→0 | 10,703→22,582 | 两项不变 |
| mdaqa:49 | 4→4 | +0 | 3→3 | +0 | 4→3 | 0→0 | 51,896→42,280 | 两项不变 |
| mdaqa:50 | 4→4 | +0 | 2→2 | +0 | 1→2 | 0→0 | 11,767→28,339 | 两项不变 |
| mdaqa:51 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 19,500→22,285 | 两项不变 |
| mdaqa:52 | 4→4 | +0 | 3→3 | +0 | 3→3 | 0→0 | 40,675→61,868 | 两项不变 |
| mdaqa:53 | 2→2 | +0 | 2→3 | +1 | 2→4 | 0→0 | 19,085→55,347 | [mdaqa:53](#case-mdaqa-53) |
| mdaqa:54 | 4→4 | +0 | 5→7 | +2 | 8→10 | 0→3 | 178,545→231,565 | [mdaqa:54](#case-mdaqa-54) |
| mdaqa:55 | 4→4 | +0 | 2→2 | +0 | 1→1 | 0→0 | 11,356→15,975 | 两项不变 |
| mdaqa:56 | 4→4 | +0 | 2→3 | +1 | 1→2 | 0→0 | 11,199→27,323 | [mdaqa:56](#case-mdaqa-56) |
| mdaqa:57 | 4→4 | +0 | 3→2 | -1 | 2→2 | 0→0 | 24,385→23,718 | [mdaqa:57](#case-mdaqa-57) |
| mdaqa:58 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 19,066→21,786 | 两项不变 |
| mdaqa:59 | 2→2 | +0 | 3→3 | +0 | 4→3 | 0→0 | 48,320→45,466 | 两项不变 |
| mdaqa:60 | 3→2 | -1 | 4→4 | +0 | 6→6 | 0→1 | 100,882→90,002 | [mdaqa:60](#case-mdaqa-60) |
| mdaqa:61 | 2→2 | +0 | 3→3 | +0 | 3→3 | 0→1 | 31,690→43,616 | 两项不变 |
| mdaqa:62 | 4→4 | +0 | 2→2 | +0 | 2→1 | 0→0 | 18,828→15,361 | 两项不变 |
| mdaqa:63 | 4→4 | +0 | 2→2 | +0 | 1→2 | 0→0 | 11,189→25,671 | 两项不变 |
| mdaqa:64 | 4→4 | +0 | 2→3 | +1 | 2→2 | 0→1 | 18,987→31,908 | [mdaqa:64](#case-mdaqa-64) |
| mdaqa:65 | 4→4 | +0 | 3→3 | +0 | 4→5 | 0→0 | 53,756→67,266 | 两项不变 |
| mdaqa:66 | 3→3 | +0 | 2→2 | +0 | 1→2 | 0→0 | 11,030→21,799 | 两项不变 |
| mdaqa:67 | 3→4 | +1 | 2→2 | +0 | 1→2 | 0→0 | 11,135→28,580 | [mdaqa:67](#case-mdaqa-67) |
| mdaqa:68 | 4→4 | +0 | 2→3 | +1 | 2→3 | 0→0 | 19,573→44,200 | [mdaqa:68](#case-mdaqa-68) |
| mdaqa:69 | 4→4 | +0 | 3→4 | +1 | 4→6 | 0→2 | 41,502→80,764 | [mdaqa:69](#case-mdaqa-69) |
| mdaqa:70 | 4→4 | +0 | 5→3 | -2 | 7→4 | 1→0 | 120,703→59,325 | [mdaqa:70](#case-mdaqa-70) |
| mdaqa:71 | 2→2 | +0 | 3→3 | +0 | 4→4 | 0→0 | 54,337→51,038 | 两项不变 |
| mdaqa:72 | 4→4 | +0 | 4→3 | -1 | 6→4 | 0→0 | 81,062→61,410 | [mdaqa:72](#case-mdaqa-72) |
| mdaqa:73 | 1→2 | +1 | 5→3 | -2 | 6→5 | 0→0 | 126,959→73,868 | [mdaqa:73](#case-mdaqa-73) |
| mdaqa:74 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 | 19,144→24,205 | 两项不变 |
| mdaqa:75 | 4→4 | +0 | 2→3 | +1 | 2→4 | 0→0 | 21,307→60,138 | [mdaqa:75](#case-mdaqa-75) |
| mdaqa:76 | 2→2 | +0 | 5→3 | -2 | 8→4 | 0→0 | 147,338→76,845 | [mdaqa:76](#case-mdaqa-76) |
| mdaqa:77 | 4→4 | +0 | 2→2 | +0 | 2→1 | 0→0 | 19,657→15,407 | 两项不变 |
| mdaqa:78 | 4→4 | +0 | 4→5 | +1 | 5→8 | 0→0 | 74,643→139,279 | [mdaqa:78](#case-mdaqa-78) |
| mdaqa:79 | 3→4 | +1 | 2→3 | +1 | 1→3 | 0→0 | 11,560→40,118 | [mdaqa:79](#case-mdaqa-79) |
| mdaqa:80 | 4→4 | +0 | 7→3 | -4 | 12→4 | 0→0 | 350,819→84,706 | [mdaqa:80](#case-mdaqa-80) |
| mdaqa:81 | 4→4 | +0 | 4→5 | +1 | 6→6 | 0→0 | 89,040→141,396 | [mdaqa:81](#case-mdaqa-81) |
| mdaqa:82 | 2→2 | +0 | 3→4 | +1 | 4→6 | 0→0 | 51,184→113,775 | [mdaqa:82](#case-mdaqa-82) |
| mdaqa:83 | 2→3 | +1 | 2→2 | +0 | 1→2 | 0→0 | 11,021→26,311 | [mdaqa:83](#case-mdaqa-83) |
| mdaqa:84 | 0→4 | +4 | 2→2 | +0 | 2→2 | 0→0 | 19,024→27,864 | [mdaqa:84](#case-mdaqa-84) |
| mdaqa:85 | 4→4 | +0 | 3→7 | +4 | 3→9 | 0→4 | 36,497→172,366 | [mdaqa:85](#case-mdaqa-85) |
| mdaqa:86 | 3→3 | +0 | 3→3 | +0 | 3→3 | 0→0 | 36,596→49,217 | 两项不变 |
| mdaqa:87 | 4→4 | +0 | 4→4 | +0 | 6→6 | 0→0 | 101,662→101,311 | 两项不变 |
| mdaqa:88 | 2→3 | +1 | 3→5 | +2 | 4→7 | 0→0 | 40,542→135,126 | [mdaqa:88](#case-mdaqa-88) |
| mdaqa:89 | 3→4 | +1 | 4→4 | +0 | 6→5 | 0→0 | 75,141→97,581 | [mdaqa:89](#case-mdaqa-89) |
| mdaqa:90 | 2→2 | +0 | 2→2 | +0 | 2→2 | 0→0 | 19,589→25,652 | 两项不变 |
| mdaqa:91 | 2→2 | +0 | 3→3 | +0 | 3→3 | 1→0 | 28,948→43,743 | 两项不变 |
| mdaqa:92 | 2→2 | +0 | 8→9 | +1 | 14→16 | 0→0 | 478,852→771,730 | [mdaqa:92](#case-mdaqa-92) |
| mdaqa:93 | 4→4 | +0 | 3→3 | +0 | 4→4 | 0→0 | 44,116→64,290 | 两项不变 |
| mdaqa:94 | 2→1 | -1 | 4→4 | +0 | 4→5 | 0→0 | 65,952→120,218 | [mdaqa:94](#case-mdaqa-94) |
| mdaqa:95 | 4→4 | +0 | 3→2 | -1 | 2→1 | 0→0 | 23,099→12,835 | [mdaqa:95](#case-mdaqa-95) |
| mdaqa:96 | 4→4 | +0 | 2→2 | +0 | 1→1 | 0→0 | 10,496→12,951 | 两项不变 |
| mdaqa:97 | 4→4 | +0 | 3→5 | +2 | 4→8 | 0→0 | 56,858→168,512 | [mdaqa:97](#case-mdaqa-97) |
| mdaqa:98 | 4→2 | -2 | 2→2 | +0 | 2→1 | 0→0 | 20,053→16,426 | [mdaqa:98](#case-mdaqa-98) |
| mdaqa:99 | 3→2 | -1 | 4→4 | +0 | 5→4 | 0→0 | 63,719→53,186 | [mdaqa:99](#case-mdaqa-99) |

## 9. 核验与限制

所有 trace 副本 SHA-256 与服务器采集记录一致，所有模型轮次与 results.jsonl 的 rounds 一致。总体分数、token、耗时和题数已与原汇总交叉核对。没有新增 API 请求、重新评分、修改 gold 或调整实验配置。五组新实验共 532 对 QA；本报告只覆盖标题所示组。完整派生数据与提取脚本见 [summary.json](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/summary.json)、[analyze.py](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921/analyze.py)。

本报告没有随机化重复试验或固定检索轨迹的消融，无法识别“社区算法单独造成的准确率变化”。特别是 query 已变、后续读取不同、judge 本身有尺度差异时，只能报告证据支持到的机制层级。
