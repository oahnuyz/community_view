# 六组 naive / community 实验：综合结论与改进方向

分析日期：2026-09-21。基于已保存的问答、judge 与工具 trace；没有新增模型调用、重跑实验、修改评分或更改 RAG 实现。ScholarQA 原报告保留，本次新增五份独立报告及本综合报告。

## 1. 当前证据支持的结论

**community 有助于论文/文档发现和粗粒度综合，但目前不是稳定、普适的准确率或效率提升。** 六组里五组记录的 judge 均分上升，MDAQA 略降；所有组的 QA token 都增加。较清楚的正向路径是从相关文档的跨社区边获得另一篇论文的 overview，再直接综合或补查原文。较清楚的瓶颈则是：材料已经召回但最终没采用、没有明确比较对象、表格数字与方法名错配、工具参数失败、反复改写未解决的查询，以及单次 judge 尺度不一致。

不能把全部分差归结为图或社区质量。PaperScope 的 352 对 QA 中，没有一对的首轮整组工具请求完全相同；这些规划差异发生在看到社区内容之前。当前比较是完整系统两次运行的结果，不是固定检索轨迹下的社区因果消融。

## 2. 六组结果总览

| 实验组 | QA数 | 归一化accuracy N→C | 变化（百分点） | 平均rounds N→C | QA token变化 | 平均QA秒 N→C |
|---|---|---|---|---|---|---|
| [ScholarQA-Multi](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/scholarqa_naive_vs_community_trace_analysis.md) | 92 | 83.152% → 85.598% | +2.446 | 2.8696 → 2.6739 | +7.89% | 14.38 → 14.23 |
| [PaperScope / gap](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/paperscope_gap_naive_vs_community_trace_analysis.md) | 119 | 67.857% → 68.487% | +0.630 | 3.6471 → 3.4034 | +14.25% | 76.39 → 69.48 |
| [PaperScope / results_comparison](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/paperscope_results_comparison_naive_vs_community_trace_analysis.md) | 116 | 77.371% → 78.664% | +1.293 | 4.3017 → 4.2414 | +25.02% | 89.65 → 83.11 |
| [PaperScope / trend](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/paperscope_trend_naive_vs_community_trace_analysis.md) | 117 | 93.162% → 96.795% | +3.632 | 3.4530 → 3.5214 | +35.66% | 63.82 → 61.30 |
| [EnterpriseRAGBench](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/enterprise_rag_bench_naive_vs_community_trace_analysis.md) | 80 | 82.500% → 83.125% | +0.625 | 2.5500 → 2.5625 | +27.74% | 19.13 → 24.82 |
| [MDAQA](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/mdaqa_naive_vs_community_trace_analysis.md) | 100 | 79.500% → 79.000% | -0.500 | 3.0600 → 3.0700 | +20.14% | 20.14 → 20.15 |

| 实验组 | 评分上升题 | 评分下降题 | rounds上升题 | rounds下降题 | 任一变化题 |
|---|---|---|---|---|---|
| ScholarQA-Multi | 16 | 9 | 14 | 22 | 49 |
| PaperScope / gap | 35 | 28 | 30 | 45 | 99 |
| PaperScope / results_comparison | 31 | 26 | 37 | 42 | 99 |
| PaperScope / trend | 17 | 5 | 38 | 30 | 72 |
| EnterpriseRAGBench | 11 | 10 | 7 | 7 | 30 |
| MDAQA | 15 | 16 | 23 | 20 | 60 |

总计 **624 道不同 QA、1,248 次问答与评分**，最终均成功；两项任一变化的共 **409** 道，其中 ScholarQA 原报告 49 道、五份新报告 360 道。五份新报告的 360 题均保留执行诊断、gold、完整答案、judge 理由和逐工具时序，其中 38 个重点案例另作内容级与来源级核验。其余案例不强行给出未被证据支持的单一原因。

若只做按题数加权的描述性汇总：score 总分 2006→2041（+35），归一化 80.369%→81.771%（+1.402 个百分点），总 rounds 2111→2067，QA token 83,188,040→103,115,237（+23.95%）。**这不是总体泛化能力的统计估计**：PaperScope 三类复用同一语料，且多个问题复用相同核心论文；不同数据集的问法、并发和环境也不同。

口径：accuracy 是 0–4 judge 均分除以 4；rounds 包含最终回答；QA token 包括查询 embedding，不含入库和 judge；时间是逐题实际执行时长的平均。它们均不是 Recall@k 或二元正确率。没有做重复运行、置信区间或显著性检验，不能声称小幅净增已被统计确认。

## 3. 什么情况下社区真正提供了可见帮助

### 3.1 可验证的跨社区发现路径，而不是泛泛的“上下文更多”

[paperscope:trend:231](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/paperscope_trend_naive_vs_community_trace_analysis.md#case-paperscope-trend-231)（2→4 分、4→3 轮）：第一条查询的 chunk 来自 PBADet，程序沿 **PBADet→HASSOD** 边（0.3985591888427734）进入 SSL 社区，注入 JEPA overview；第 2 轮再检索 JEPA 原文。naive 全部工具内容没有 JEPA 材料，最终称不存在对应论文。这支持“跨社区可以补齐原检索未覆盖的研究方向”。不过后续查询没有直接绑定该 doc_id，且首轮整体规划不同，仍不能证明模型仅因那份 overview 才改变查询。

[paperscope:trend:411](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/paperscope_trend_naive_vs_community_trace_analysis.md#case-paperscope-trend-411)（2→4 分、3→2 轮）：community 没有检索到 PBADet chunk，而是由 LDReg→Visual Data-Type Identification 边（0.3668005347251892）带入 PBADet 所在社区的 overview，最终写出趋势。naive 却已检索到 PBADet 原文仍未在答案中采用。这既证明 overview 能支撑粗粒度概述，也说明正向差异包含生成阶段对已有证据的采用。

这两条路径中的边连接的是文档，最终有用的文档还可能是邻接社区的其他成员。不能把“静态相似度较高的文档对”直接等同“对当前问题最有用的文档对”；它可能是发现入口，也可能只是偶然带入了有用成员。

ScholarQA 的 [hao_photonics_9](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/scholarqa_naive_vs_community_trace_analysis.md#case-hao_photonics_9) 与 [hao_photonics_10](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/scholarqa_naive_vs_community_trace_analysis.md#case-hao_photonics_10) 也有平台类别、cat state 由 overview 补齐的直接证据。原报告中这类收益主要来自叶社区成员，不应与本次新确认的跨社区路径混为一谈。

### 3.2 细节题仍依赖原文核验和条件化综合

[enterprise_rag_bench:qst_0344](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/enterprise_rag_bench_naive_vs_community_trace_analysis.md#case-enterprise_rag_bench-qst_0344) 从“没有积分赔付必要”改为 SRE 验证违约、再走审批流程。community 后续对 D0024 的定向检索提供了明确流程。这里的文档在首轮已同时以 chunk/overview 返回，不能说是社区单独发现，但可以确认局部核验改变了最终结论的适用条件。

[mdaqa:38](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/mdaqa_naive_vs_community_trace_analysis.md#case-mdaqa-38) 在成功精读后补齐 word-level correlation regularization（2→4），但新增三轮里两轮全因非法 JSON 失败。因此“精读有用”和“用了更多轮”要分别评价。

## 4. 哪些主要问题不应被归咎于召回不足

### 4.1 已有证据没有进入最终答案

- [enterprise_rag_bench:qst_0352](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/enterprise_rag_bench_naive_vs_community_trace_analysis.md#case-enterprise_rag_bench-qst_0352)：naive 已有 catalog_fallback 的原文和 overview，却没写 Dedicated 价格回退；2→4 的改善不能说成社区独有新证据。
- [mdaqa:16](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/mdaqa_naive_vs_community_trace_analysis.md#case-mdaqa-16)：两边都有 D0103 的 SUS-constrained VAE 原文和概览，community 最后只回答 I2I/SA-I2I，4→2。
- [mdaqa:42](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/mdaqa_naive_vs_community_trace_analysis.md#case-mdaqa-42)：两边都拿到 Quasimodo 的 crowd judgement，只有 community 最终明确采用；0→4 中包含答案综合差异，分差幅度还需复核。
- [paperscope:gap:76](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/paperscope_gap_naive_vs_community_trace_analysis.md#case-paperscope-gap-76)：naive 已找到 EI/RNN overview，最终却漏整个分支。

共同改进方向是**子问题覆盖表和最终证据采用检查**，不是首先把 top-k/doc_k 调大。覆盖表应按问题生成、仅使用检索证据，不把 gold 当作检索或回答的输入。

### 4.2 多文档比较没有明确“比较谁、比什么”

MDAQA 的很多问题使用 “these methods / the two approaches”。[mdaqa:94](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/mdaqa_naive_vs_community_trace_analysis.md#case-mdaqa-94) 最终分别偏向 TCN 和 PLAtE 内部模型；[mdaqa:98](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/mdaqa_naive_vs_community_trace_analysis.md#case-mdaqa-98) 的 community 漏掉另一篇的独立性假设；[mdaqa:36](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/mdaqa_naive_vs_community_trace_analysis.md#case-mdaqa-36) 已拿到 124/143 篇 overview 仍不能定位实时/非实时对照。大量相关领域材料不能替代实体消歧与比较维度。

下一步应要求先在当前问题和已召回内容中确定比较对象，再对各对象做定向搜索。可在离线诊断中用数据集的 document_ids 做 oracle-scope 上界，区分“文档发现失败”与“答案综合失败”，但这不能替代正式无标签检索结果，更不能把 gold/evidence 标签直接喂入正式回答流程。

### 4.3 数字对齐和 PDF 结构仍是独立瓶颈

[paperscope:results_comparison:77](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/paperscope_results_comparison_naive_vs_community_trace_analysis.md#case-paperscope-results_comparison-77) 的 69.0→69.8 被从 SimCLR 配到 BYOL；PBADet/BPJDet 比较还有骨干/实验设置混用。对应 trace 已有数值，局部 Markdown 表格却缺少清晰的方法标签。MDAQA trace 也可见双栏混排和词间空格丢失。

需要核验“论文—方法—数据集—骨干—指标—数值—实验条件”的绑定。PDF 解析质量应抽样对照原表，不因出现数字错误就断言必须换解析器；也不能假定额外社区 overview 会修复表格行列。可先在切片正文保留完整表头/说明，不需要为每个 chunk 增加此前取消的冗余页码元数据。

### 4.4 文档权威、版本和例外条件需要明确处理

[enterprise_rag_bench:qst_0359](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/enterprise_rag_bench_naive_vs_community_trace_analysis.md#case-enterprise_rag_bench-qst_0359) 同时拿到 ADR、gateway 实现和 PM 需求，但 community 用实际差异否定 canonical subcode 契约；[enterprise_rag_bench:qst_0422](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/enterprise_rag_bench_naive_vs_community_trace_analysis.md#case-enterprise_rag_bench-qst_0422) 在 retention 与 Legal Hold 例外的措辞上发生大幅判分差。更多社区材料会暴露更多冲突，系统仍需要说明哪个是规范、哪个是部署现状、哪个已经被替代，以及例外是否适用。

这应先由检索后内部证据整理解决；不能仅按较新的时间或某个文档类型一刀切，也不需要立即引入 wiki 报告生成。

## 5. 单次 judge 的尺度差异足以改变主要结论

以下是优先复核案例，不是人工重新打分：

| 案例 | 原分数 | 核对发现 |
|---|---|---|
| [mdaqa:33](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/mdaqa_naive_vs_community_trace_analysis.md#case-mdaqa-33) | 4→0 | 两边都说 COMRADE 一轮、GIANT/DINGO 两轮，也都区分同一方法有/无故障；judge 对相近核心采用相反尺度。 |
| [mdaqa:11](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/mdaqa_naive_vs_community_trace_analysis.md#case-mdaqa-11) | 4→2 | 两边都未展开跨视角语义对齐/几何线索，只对一边按这些缺项扣分。 |
| [mdaqa:20](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/mdaqa_naive_vs_community_trace_analysis.md#case-mdaqa-20) | 4→2 | 两边都讲 FRAGE、未展开 cluster 替代方案，只有一边因缺项大幅扣分。 |
| [enterprise_rag_bench:qst_0427](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/enterprise_rag_bench_naive_vs_community_trace_analysis.md#case-enterprise_rag_bench-qst_0427) | 3→4 | 同样给出哈希格式/时间，同样未写每条 invoice line 要携带；只有 naive 被扣该项。 |
| [enterprise_rag_bench:qst_0437](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/enterprise_rag_bench_naive_vs_community_trace_analysis.md#case-enterprise_rag_bench-qst_0437) | 2→3 | 同样答 Platform，约 20/约 23 都偏离 gold 16，后者反而得更高分。 |
| [paperscope:trend:243](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/paperscope_trend_naive_vs_community_trace_analysis.md#case-paperscope-trend-243) | 2→3 | 两边都漏 PBADet，却对同一缺项使用不同尺度。 |
| [weijia_cs_8](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/scholarqa_naive_vs_community_trace_analysis.md#case-weijia_cs_8) | 2→4 | 原报告已指出两边只讲 Visprog、均未展开其他框架。 |

因此，应保留原分数和原 reasoning，新增独立的盲化复核版本：隐藏 mode/run_id，先逐项核对 gold 中的核心命题、替代答案与可选补充，再评分。重复独立评分并报告方差；如增加成对比较，应交换 A/B 顺序控制位置偏差。对 gold 与原文有冲突的条目单独标记，不直接训练系统迎合可能有误的参考答案。

现有数据不足以给出“扣除 judge 噪声后的准确率”；本报告不尝试主观修正，也不把所有下降都归为评测问题。MDAQA 16、Enterprise 359、PaperScope results_comparison 77 都有可见的实质答案缺陷。

## 6. iteration 变化要拆成四类执行行为

| 机制 | 具体证据 | 应该如何解读 |
|---|---|---|
| 首轮并行安排不同 | [paperscope:gap:28](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/paperscope_gap_naive_vs_community_trace_analysis.md#case-paperscope-gap-28)；[enterprise_rag_bench:qst_0356](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/enterprise_rag_bench_naive_vs_community_trace_analysis.md#case-enterprise_rag_bench-qst_0356) | 社区还没注入前，工具批次就不同；轮数不等于工作量。 |
| 更多 overview 后较早转为局部核验 | [paperscope:gap:259](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/paperscope_gap_naive_vs_community_trace_analysis.md#case-paperscope-gap-259)；[paperscope:trend:24](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/paperscope_trend_naive_vs_community_trace_analysis.md#case-paperscope-trend-24) | 可减少旁支改写与历史重复输入，但必须同时核对回答缺项。 |
| 参数/范围错误恢复 | [mdaqa:85](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/mdaqa_naive_vs_community_trace_analysis.md#case-mdaqa-85)；[paperscope:results_comparison:332](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/paperscope_results_comparison_naive_vs_community_trace_analysis.md#case-paperscope-results_comparison-332) | 全失败工具轮可直接识别；不能简单从总轮数中减去后当作纯算法成本。 |
| 语义近似查询反复改写 | [paperscope:results_comparison:368](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/paperscope_results_comparison_naive_vs_community_trace_analysis.md#case-paperscope-results_comparison-368)；[paperscope:results_comparison:305](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/paperscope_results_comparison_naive_vs_community_trace_analysis.md#case-paperscope-results_comparison-305) | 完全同参工具去重不足以阻止无进展追索；新增 overview 为零也不必然无新 chunk。 |

MDAQA 85 的四次失败明确是 `ordinals` 缺少 `[]`，不是检索失败；其第 2、3、4 轮全部失败。PaperScope trend 66 同时有数量超限、越界和重复核验，6→13 轮却保持 4 分。Enterprise 437 则 6→5 轮，但工具数 9→17、出现 5 次错误。因此不能只优化平均 iteration。

还要检查最终回答是否真的完成任务。[paperscope:results_comparison:224](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/paperscope_results_comparison_naive_vs_community_trace_analysis.md#case-paperscope-results_comparison-224) 的 naive 最终仅列论文、以 “Now I'll answer…” 结束，仍被系统按非空字符串标记 complete。现有 trace 不能判定是否服务截断，但可以确认用户要求的数值比较没有交付。任务完成度与传输成功应分开记录。

## 7. 上下文规模：去重有效，但多路扩展仍接近全库

PaperScope community 每题平均约 70/93 篇文档 overview：gap 69.80、results_comparison 70.63、trend 69.88；352 题中有 95 题达到至少 80 篇，23 题覆盖全部 93 篇。问题级去重防止同一 overview 反复追加，但不限制一个问题经过多次不同查询后纳入大量不同社区。

这是观察到的覆盖规模，不等同于 70 篇都不相关。趋势题可能受益于较广研究方向，缺陷/数字比较题则通常需要更精确材料。当前结果支持下一步**按问题相关性审查种子与邻接社区**，而不支持直接断言“加更多文档总是好”或“社区必须关闭”。可以保持现阶段不引入复杂分页、硬 token 预算和历史压缩的范围，先验证更有选择性的扩展。

所有组 QA token 上升，PaperScope trend 增幅最大（约 35.66%），尽管其平均时间下降；这与服务端并发/请求调度等混杂因素相容，不能用时间下降否认 token 成本。重复历史输入使额外工具轮放大上下文成本，但现有数据不能把成本精确分摊为某份 overview、某条边或某个服务请求。

## 8. 改进优先级与验收方式

| 优先级 | 方向 | 具体动作 | 验收方式 |
|---|---|---|---|
| P0 | 评测一致性 | 保留原分数，盲化复评疑点；显式区分 gold 核心项、可替代答案、可选细节。 | 相近答案评分一致率、重复评分方差、模式差在复评分下的稳定性。 |
| P0 | 读取工具可用性 | 在 schema/说明中统一 ordinals 数组格式、单次上限；提供合法 ordinal 范围/计数及清晰错误反馈。 | 固定失败案例集的参数错误率、全失败轮数；复核 maxItems 与运行时上限一致。 |
| P1 | 比较对象与覆盖检查 | 先列问题子项及论文/文档对象，再核对答案是否覆盖机制、条件、数字、对照对象。 | 16/94/98/76 等已召回但遗漏的案例减少；不向正式检索注入 gold。 |
| P1 | 数字/表格核验 | 保留表头与实验条件；生成内部比较表再写答案；对解析异常抽样核查原 PDF。 | 方法/数据集/指标配错率、数值事实错误率；77 等表格案例回归。 |
| P1 | 无进展停止与回答完成度 | 跟踪已验证子问题、新 chunk/事实和重复改写；检查最终答案是否只是提纲/承诺。 | 保持质量的前提下，长尾 token/P95 rounds 降低；224 不再假完成。 |
| P2 | 选择性社区扩展 | 比较只加本体叶社区、再加跨社区；按当前问题核验种子与目标社区相关性。 | 固定开局消融的质量/成本差；231/411 正例与36负例共同测试。 |
| P2 | 权威/版本冲突 | 在内部证据中区分规范、实现、旧稿、例外和时间状态。 | 359 等冲突题的条件与契约处理正确性；保留不确定性而非强行统一。 |
| P2 | 完整枚举与计数能力 | 先建立对象清单和去重键，再程序化汇总；明确 top-k 不是全量。 | 437 的确切计数、重复项与遗漏率；不在本次恢复 find_documents。 |

这些都是后续候选工作，本次只生成分析报告。没有更改 API 重试策略、自动调整图参数、增加新的 agent 工具、实现 wiki 报告或交互式 chat。改进应先小样本验证再扩大，不宜同时改 PDF、图、提示词与评测后只比较一个总分。

## 9. 下一轮实验如何让结论更可信

1. **先复评分，不必重入库或重跑 QA。** 冻结已有 answers/gold，给新的 judge 版本单独保存结果；保留原 score 用于可追溯比较。以大分差和相似答案为优先，再随机抽样不变案例检查选择偏差。
2. **固定同一套初始工具请求及 chunk 返回。** 先做固定检索轨迹下的答案生成对照，研究额外信息的直接作用；再做只固定开局、允许后续 agent 自适应的完整系统实验。二者分别回答“上下文信息有没有用”和“会如何改变搜索路线”。
3. **拆分扩展来源。** 当前 naive（chunks＋每文档一次 overview）→本体叶社区→本体＋跨社区；还可将“社区描述”与“成员文档 overview”分开，检验名称/概述是否有独立作用。随机或长度匹配的非相关 overview 仅作为离线负对照，不作为正式配置。
4. **固定语料/图/配置/模型并多次配对运行。** 随机交错模式顺序，减少服务负载时段差；报告每题分差、token/时间/工具错误/长尾，不只均值。PaperScope 按共享问题模板或核心论文做分组分析，避免把相关题当成独立样本夸大置信度。
5. **先评估故障修复，再评估检索策略。** 工具参数修复可以在已有失败调用上离线回放验证格式；模型行为是否改变仍需新的 QA 运行。图参数/种子筛选则需要同题受控对比，不能用修复工具带来的省轮当作图改进。
6. **对照质量目标。** 趋势题看研究方向完整性；缺陷题看前提/边界；结果比较看数值绑定；企业题看权威/例外/枚举；MDAQA 看比较对象和关系。总分之外保留这些错误类别，才能知道参数调整到底解决了什么。

## 10. 报告与可复核产物

- [ScholarQA-Multi](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/scholarqa_naive_vs_community_trace_analysis.md)
- [PaperScope / gap](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/paperscope_gap_naive_vs_community_trace_analysis.md)
- [PaperScope / results_comparison](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/paperscope_results_comparison_naive_vs_community_trace_analysis.md)
- [PaperScope / trend](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/paperscope_trend_naive_vs_community_trace_analysis.md)
- [EnterpriseRAGBench](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/enterprise_rag_bench_naive_vs_community_trace_analysis.md)
- [MDAQA](/Users/yunhaoz/Developer/MyProjects/community_wiki/docs/reports/mdaqa_naive_vs_community_trace_analysis.md)

新分析材料目录：`/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison_20260921`。其中本地保存 1,064 个服务器 trace、原始结果与配置副本、图元数据、逐题派生数据和报告生成脚本；所有新 trace 已与前次采集 SHA-256 校验一致。ScholarQA 引用现有原报告及本地原始数据，本次未改写该报告。各独立报告提供逐题链接，可直接定位原始消息核查。
