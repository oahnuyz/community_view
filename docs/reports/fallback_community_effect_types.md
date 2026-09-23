# fallback community 的实际效果：类型、case 数量与证据

## 实验范围与统计口径

对比已完成的 **v2 naive 与开启 LLM fallback 的 community**，不含 community_guide。ScholarQA 使用 187 上同一实验的两个模式；PaperScope 使用 214 的 naive 与 187 的 fallback community，后者复用了相同原文、chunks 和文档 overview。PaperScope 的三类 QA 分开统计。

| 数据集 | 配对 QA | normalized accuracy：N→C | 升分 / 降分 | token 明显增 / 减 | 入选 case |
|---|---|---|---|---|---|
| ScholarQA | 92 | 85.87%→89.13% | 16 / 7 | 12 / 14 | 37 |
| PaperScope/gap | 119 | 62.18%→63.66% | 31 / 25 | 45 / 39 | 98 |
| PaperScope/results_comparison | 116 | 78.02%→82.54% | 39 / 23 | 39 / 41 | 98 |
| PaperScope/trend | 117 | 95.94%→94.02% | 9 / 15 | 28 / 34 | 70 |

共 **444 对 QA**，本报告分析其中 **303 个变化 case**：165 个评分变化、252 个 token 明显变化，二者重叠 114 个。单题 score 为 0–4；“token 明显变化”须同时满足绝对变化至少 10,000、相对 naive 至少 25%。QA token 包含 embedding，不含入库和评测成本。所有类型数量的分母均为这 303 个 case。

下文 N/C 分别表示 naive/community；G 为数据集标注的参考文档集合。**G 外文档不能直接判为无关文档，G 覆盖完整也不等于关键答案证据完整。** 首轮查询大多不同，因此“community 模式升分”不能全部归因于社区信息。报告区分可见的信息使用路径、模式结果变化和未证实的因果解释。

数据来源：[实验来源与索引一致性记录](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/provenance.json)；[逐 case 指标及 trace 事实](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit_revision/detailed_cases.json)。以下计数已与 606 份原始 trace 的答案、文档及社区集合核对。

## 类型与 case 数量

| 类型 | ScholarQA | gap | results_comparison | trend | 合计 | 升分 / 同分 / 降分 |
|---|---|---|---|---|---|---|
| A：概览成为答案素材：补主题或补背景 | 5 | 10 | 10 | 5 | 30 | 11/14/5 |
| B：从社区候选定向读取原文 | 1 | 2 | 4 | 2 | 9 | 1/4/4 |
| C：仍存在参考文档召回缺口 | 9 | 0 | 1 | 2 | 12 | 2/3/7 |
| D：文档已覆盖，仍遗漏主题或关键条件 | 3 | 21 | 5 | 6 | 35 | 0/0/35 |
| E：数值、比较对象、方向或归属错误 | 0 | 1 | 16 | 6 | 23 | 0/0/23 |
| F：探索收缩，token 明显下降 | 14 | 39 | 41 | 34 | 128 | 22/76/30 |
| G：探索或返回载荷扩大，token 明显上升 | 12 | 45 | 39 | 28 | 124 | 41/62/21 |
| H：答案改善，但社区贡献尚未单独识别 | 9 | 25 | 33 | 4 | 71 | 71/0/0 |

这是**可重叠的效果类型**，不能把各行相加当作 QA 总数。例如，社区引导阅读后仍错答且增加 token，可以同时属于 B、E、G。A/B 有直接的上下文或工具路径证据；C/D/E 是社区未能解决的失效类型，不能一概说错误由社区造成；F/G 是成本结果；H 明确保留归因不确定性。

另有 **17 个评分争议 case（12 升、5 降）**，不将其分差直接解释成社区优势或缺陷。70 个降分 case 的主问题可以互斥归为：**参考文档缺口 7、资料齐但漏主题/条件 35、事实对齐错误 23、评分争议 5**。

## A．概览确实会成为答案素材，但“被使用”不等于“答到了关键点”

**30 个 case** 的最终答案引用了仅通过社区 overview 出现的文档 ID，或复述了其特征短语；其中 **11 升分、14 同分、5 降分**。这里的“仅通过 overview”指 community 轨迹中没有该文档的 chunk，不保证 naive 从未见过该文档，也不保证该短语只有一个可能来源。因而 30 是可观察使用线索的数量，不是 30 次有效补证。

### 优势：直接补上原检索遗漏的 kNN-LM 路线 — `scholarqa:weijia_cs_6`

score **2→4**；QA token **15,127→16,486**（+1,359，+9.0%）；轮次 **2→2**。

问题要求概括 retrieval-augmented language model 的常见架构。N 最终遗漏 kNN-LM；C 的 C0156 社区总览明确列出 kNN-LMs，成员 D0220 的 summary 说明“预训练 LM 与 external datastore 上的 k-nearest-neighbor 模型线性插值”。D0220 没有被搜索或读取出 chunk，也未进入 N 的上下文。

C 随后把 kNN-based interpolation 单列为一类架构，内容与该 summary 对应。核对两侧工具返回，kNN/nearest-neighbor/external-datastore 这组线索只出现在 C 的 D0220 overview 和 C0156 总览中。两边均两轮，增加 1,359 token 就补上一个关键主题：这是本组较强的“社区提供了此前缺失的答案信息”证据，而不是仅仅多返回了相关文档。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/scholar187/naive_scholarqa_weijia_cs_6.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/scholar187/community_scholarqa_weijia_cs_6.json)。

### 优势：参考集合之外的概览也能提供有效补充 — `scholarqa:shengyan_photonics_3`

score **2→4**；QA token **41,084→16,194**（-24,890，-60.6%）；轮次 **3→2**。

问题询问哪些大型系统已展示量子效应。C 只通过 overview 见到 D0052，其关于猫态和分离相空间状态的描述进入了最终答案，答案列出 16 微克机械振子的 Schrödinger cat states。D0052 不在 G 中，不能因此称它为无关材料。

这证明社区能扩展有用的答案素材。不过 C 首轮查询同时更充分覆盖大分子干涉与宏观纠缠，升分和省 token 还有查询组织的贡献；不能把全部 +2 分都归给 D0052。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/scholar187/naive_scholarqa_shengyan_photonics_3.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/scholar187/community_scholarqa_shengyan_photonics_3.json)。

### 缺陷：采用了相关概览，回答却偏向另一种机制 — `scholarqa:yanyu_photonics_3`

score **3→2**；QA token **39,992→112,549**（+72,557，+181.4%）；轮次 **4→7**。

问题需要解释高 Q 微腔/光机械单分子检测及其灵敏度边界。C 的社区共展示 43 篇成员，其中 5 篇属于 G；新增 D0021、D0266、D0410 等参考候选。D0266 没有 chunk，只以 overview 出现，答案却确实使用了它关于高 Q 过滤谱噪声的论点。

随后 C 围绕 resonance shift、spring stiffness、plasmonic enhancement 等线索搜索到第 7 轮，答案仍缺 gold 所要求的蓝失谐 OMO、对应检测实验与数量级结论。它提到 BSA，但放在另一种极限估计里，不能当作回答了目标实验。这里的问题不是社区没有被使用，而是相关素材把可回答范围扩宽，却没有对准问题中最有判别性的机制；结果多花 72,557 token 还降 1 分。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/scholar187/naive_scholarqa_yanyu_photonics_3.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/scholar187/community_scholarqa_yanyu_photonics_3.json)。

这一类型验证了社区的实际信息通路，也暴露了它的边界：**overview 适合补主题和提供候选解释，不自动保证所选解释与问题一致。**

## B．社区能引导到原文，但导航成功不保证更准或更省

按严格路径“先在社区出现、尚无该文档 chunk，之后按该 doc_id 搜索或读取原文”，有 **9 个 case**：1 升分、4 同分、4 降分。另有 **33 个 case** 相比 N 增加了 G 中的文档候选（ScholarQA/gap/comparison/trend 分别 13/7/8/5），但仅增加候选不等于有采用或导航证据，且可能受查询差异影响。

### 有用导航：找到 Dale 论文后集中读取，减少一轮 — `paperscope:gap:76`

score **3→3**；QA token **156,172→88,982**（-67,190，-43.0%）；轮次 **4→3**。

C 在第 1 轮社区中先看到 D0069（Dale’s Law），第 2 轮才通过定向调用取到其原文。这条路径把谱性质、EI 比例和网络大小的限制补入了逐论文回答。

C 最终 3 轮完成，N 为 4 轮，分数均为 3。可确认的优势是社区提供可操作的文档入口，并与更集中阅读、少一轮历史回传共同出现；不能进一步声称它修复了所有限制遗漏。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper214/naive_paperscope_gap_76.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper187/community_paperscope_gap_76.json)。

### 导航后仍失控：多读到了论文，却继续追查旁支 — `paperscope:results_comparison:29`

score **3→3**；QA token **367,901→646,269**（+278,368，+75.7%）；轮次 **5→8**。

C 同样先在第 1 轮社区看到 D0069，再在第 2 轮按文档取原文，导航链成立。但后续仍围绕 LoRA、F1 等实验要求继续检索，5 轮扩大到 8 轮。

两边最终同为 3 分，C 多花 278,368 token。社区解决了“可以去读哪篇”，没有解决“读哪些内容已经足以回答”；因此不能把出现定向读取直接记成准确率或效率收益。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper214/naive_paperscope_results_comparison_29.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper187/community_paperscope_results_comparison_29.json)。

## C．语义邻近与最大权重边仍会漏掉关键论文，fallback 还可能缩掉有效覆盖

**12 个重点 case** 的 C 全部上下文仍缺至少一篇 G 文档，其中 **7 个降分**；另 5 个未降分，说明缺 G 不是必然失分。7 个降分分布为 ScholarQA 4、gap 0、comparison 1、trend 2。只有具体答案也遗漏了该文档所对应的主题时，召回缺口才构成更强的失败解释。

### 漏召回：用 video-RL 代替了未进入上下文的 JEPA — `paperscope:trend:69`

score **4→2**；QA token **95,977→105,826**（+9,849，+10.3%）；轮次 **3→3**。

C 展示 48 篇社区成员，包含 4 篇 G 文档，但 D0048（JEPA）既不在 chunk 中，也没有 overview。最终把目标 JEPA 发展线替换成 video-RL，4→2；轮数并未减少。

对照下文 trend:381：那里 JEPA 已在上下文却被替代，此处则真正缺资料。前者需要约束对象选择，这里需要改善候选社区覆盖；两种失败不能统称“回答不够完整”。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper214/naive_paperscope_trend_69.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper187/community_paperscope_trend_69.json)。

### fallback 的结构性风险：略低权重的关键社区被漏掉 — `paperscope:trend:435`

score **4→2**；QA token **153,763→228,601**（+74,838，+48.7%）；轮次 **4→5**。

C 的 59 篇社区成员只包含 4 篇 G 文档，缺 D0003（video-RL）；答案改用 RaMP/VGDF 描述 RL 发展线，遗漏 exogenous noise 与 forward-vs-contrastive 的关键比较。多一轮仍从 4 降到 2。

固定该轨迹实际 chunk 命中、只切换社区结构的重放显示：普通社区可展示 D0003，fallback 拆分后未展示。D0075→D0003 权重为 0.395094，略低于胜出的 D0075→D0073 的 0.395629，关键论文所在社区因此未被扩展。这里有具体的“拆分改变覆盖”证据，而不只是两个模式答案不同。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper214/naive_paperscope_trend_435.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper187/community_paperscope_trend_435.json)。

在 303 个重点 case 的固定命中重放中，**5 个出现 fallback 比普通社区少覆盖 G 文档**：ScholarQA 的 `hao_photonics_8`、`hao_photonics_9`、`yanyu_photonics_1`、`yanyu_photonics_8`，以及 trend:435。它们相对 naive 为 2 升、1 同、2 降，不能将 5 全算成 fallback 导致的降分。确定的缺陷是：**更小的社区与每个命中文档只选一条最强跨社区边结合后，可能把必要邻居排除出去。**

## D．文档已覆盖，社区仍未帮助保留关键主题、条件和失败边界

**35 个降分 case** 属于这一类：C 已覆盖全部 G 文档，最终仍漏主题或条件；ScholarQA 3、gap 21、comparison 5、trend 6。它们说明社区已经完成候选覆盖，但没有完成答案证据组织。不能因此断言社区文本制造了遗漏，能确认的是继续扩大社区并不直接解决当前缺项。

### 同样拿到五篇论文，仍漏掉各方法的具体限制 — `paperscope:gap:265`

score **4→2**；QA token **148,312→114,445**（-33,867，-22.8%）；轮次 **4→3**。

C 的 45 篇社区成员包含全部 5 篇 G；它还实际读取 PE-DQN、JEPA、Dale、RCPS、PBADet 等目标原文。最终却遗漏 PE-DQN 的残余偏差/β/ensemble、DANN 重参数化、RCPS predictor/bounds 和 PBADet 条件，4→2。

这不是单纯“overview 太短所以只能泛答”：已经有后续读取，但细节没有完整进入答案。短概览提供了方法地图，却没有让 agent 按每个方法保留假设、失败场景和成本边界。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper214/naive_paperscope_gap_265.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper187/community_paperscope_gap_265.json)。

### 有 JEPA 仍用近邻方法替代：对象选择失衡 — `paperscope:trend:381`

score **4→2**；QA token **391,547→259,349**（-132,198，-33.8%）；轮次 **6→4**。

C 的社区成员达到 80 篇，全部 5 篇 G 均可见，包括 JEPA。最终自监督发展线却主要用 LDReg/NEFTune，遗漏 gold 要求的 JEPA 机制，4→2。

相近候选变多与这种替代同时出现，但 trace 不能证明某一条社区描述必然导致替代。已确认的是“材料存在、对象选错”：修复应约束问题对象与最终答案的对应关系，继续扩更多自监督论文反而未必有帮助。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper214/naive_paperscope_trend_381.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper187/community_paperscope_trend_381.json)。

## E．社区只能定位实验主题，不能替代指标、基线和条件的对齐

**23 个降分 case** 的主要问题是数值、比较对象、方向或归属错误：gap 1、comparison 16、trend 6，ScholarQA 0。这里包括错数字、左右脚/数据集串线、参数方向反写，以及把“本次没找到指标”写成“论文没有报告”。这是实验比较题最突出的社区能力边界。

### 不同 AP 口径串线，相关论文齐全仍得出错误胜负 — `paperscope:results_comparison:32`

score **3→2**；QA token **181,295→104,960**（-76,335，-42.1%）；轮次 **4→3**。

C 已覆盖五篇 G 文档，答案写 PBADet 的 AP 为 43.0/41.8，并称它优于“BPJDet AP 约 30.8–31.8”。回查原文表格，30.8/31.8 实际是 BPJDet 的 head/face mMR，而其对应总体 AP 是 43.6/43.3。C 把不同指标的数字放在一起，得出了错误胜负。少一轮和少 76,335 token 伴随 3→2。

社区 overview 可以提示“这是 part–body association 方法”，却不携带足以支撑该比较的完整 dataset、backbone、类别和 metric 条件。故社区相关性不能充当实验可比性的证据。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper214/naive_paperscope_results_comparison_32.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper187/community_paperscope_results_comparison_32.json)。

### 轮次没变仍把左脚改善写成右脚改善 — `paperscope:results_comparison:236`

score **4→3**；QA token **339,871→367,922**（+28,051，+8.3%）；轮次 **5→5**。

两模式均为 5 轮，C 还定向读取 PBADet，最终仍将 lower mMR 的左脚改善写成右脚，并弱化 COCO 总体差距、夸大 LoRA 的使用，4→3。token 增加未达本报告“明显变化”阈值，但因评分下降被纳入。

本论文还存在正文与表格表述不一致：正文谈 right foot 优势，表 3 的 YOLOv5l6 右脚 mMR 为 BPJDet 49.1、PBADet 50.4，而左脚为 50.4→47.9（越低越好）。所以不能简单称为模型凭空编造。真正缺的是回表核验并处理文表冲突；社区摘要没有提供这层保障。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper214/naive_paperscope_results_comparison_236.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper187/community_paperscope_results_comparison_236.json)。

## F．缩短探索能显著省 token，但省掉的有时是必要核验

token 明显下降共 **128 个 case**。其中 **98 个分数保持或上升（22 升、76 同）**，是可观察的成本收益；另 **30 个降分**，说明不能把更早停止一律视为优化。98 个无分数损失 case 中，97 个轮次下降、1 个轮次不变。

| 成本下降的结果 | ScholarQA | gap | comparison | trend | 合计 |
|---|---|---|---|---|---|
| 分数保持或上升 | 13 | 29 | 29 | 27 | 98 |
| 同时降分 | 1 | 10 | 12 | 7 | 30 |

### 收益：停止长尾重复验证，比社区本身的载荷更重要 — `paperscope:results_comparison:284`

score **3→3**；QA token **1,924,619→190,774**（-1,733,845，-90.1%）；轮次 **15→4**。

N 围绕 JEPA 的 CE/MSE/L2、预测头与检测指标反复改写查询，直至 15 轮上限；C 对 JEPA/RCPS/PBADet/NEFTune 定向读取后，在少量补搜后第 4 轮结束，两边均为 3 分。

节省 1,733,845 token，其中输入 token 减少 1,727,690。C 仍展示 50 篇社区成员，说明一次加入更多概览不等于总成本必然升高；少了 11 轮携带完整历史的请求，才是本题大幅省 token 的直接原因。但没有固定查询消融，不能说这 11 轮都是社区语义质量带来的。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper214/naive_paperscope_results_comparison_284.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper187/community_paperscope_results_comparison_284.json)。

### 代价：首轮材料后即答，把必要限制一起省掉 — `paperscope:gap:10`

score **3→2**；QA token **345,690→75,108**（-270,582，-78.3%）；轮次 **6→2**。

C 首轮工具返回后即结束，6→2 轮；51 篇社区成员包含全部五篇 G。它却漏 PBADet 单部件收益与阈值、RTB mode coverage/off-policy、4-bit 理论/部分量化等关键边界，3→2。

社区已经给到论文身份与大意，但这道 gap 题要的是失败条件。少付 270,582 token 的同时省掉了相应核验，所以不能把“原文没读也能回答”当作短 overview 足够的证据。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper214/naive_paperscope_gap_10.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper187/community_paperscope_gap_10.json)。

## G．更宽的上下文可能延长探索；新增成本多数没有换来分数提升

token 明显上升共 **124 个 case**：**41 个升分，83 个未升分（62 同、21 降）**。83 个未升分 case 中，77 个轮次增加、6 个轮次相同；其中只有 12 个工具错误次数比 N 更多，不能把大部分额外成本归咎于错误重试。更多相关线索、较大的原文返回、后续验证和历史反复发送都要分开看。

| 成本上升的结果 | ScholarQA | gap | comparison | trend | 合计 |
|---|---|---|---|---|---|
| 同时升分 | 3 | 16 | 19 | 3 | 41 |
| 没有升分 | 9 | 29 | 20 | 25 | 83 |

### 缺陷：不断扩展损失函数验证，同样满分却多花约 59.6 万 token — `paperscope:trend:60`

score **4→4**；QA token **99,371→695,145**（+595,774，+599.5%）；轮次 **3→9**。

N 3 轮已经得到 4 分；C 继续查询 JEPA L2/CE、离散 codebook、target encoder、prediction head、InfoNCE 等，到 9 轮仍是 4 分。它的 60 篇社区成员只含 5 篇 G，但不能把其余 55 篇全部判为无关；可以确认的是，这条更长路线没有新增被评分认可的趋势内容。

增加的 595,774 token 中，591,420 是输入 token。这里社区及相关资料提供了更宽的可探索背景，agent 没有依据“还有哪项主问未解决”停止。首轮查询也有差异，不能把全部旁支说成社区诱发；可验证的缺陷是启用社区后的流程没有控制住无收益的长尾验证。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper214/naive_paperscope_trend_60.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper187/community_paperscope_trend_60.json)。

### 收益：多花成本确实补上了具体失败条件 — `paperscope:gap:208`

score **2→4**；QA token **189,063→282,431**（+93,368，+49.4%）；轮次 **4→5**。

C 比 N 多一轮，并补读 PBADet、Dale、4-bit optimizer 等原文，最终写出 N 未充分交代的 NMS/超参、量化零点和谱病态等边界，2→4。

这是 41 个“增 token 且升分”的例子：社区可作为论文索引，但关键收益来自定向找出具体条件，而不是展示 71 篇社区成员本身。优化目标应是保留这类有效补读，同时减少与缺项无关的泛搜索。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper214/naive_paperscope_gap_208.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper187/community_paperscope_gap_208.json)。

### 同轮数也会更贵：每轮返回体量及历史曝光增加 — `paperscope:results_comparison:263`

score **4→4**；QA token **222,555→339,179**（+116,624，+52.4%）；轮次 **5→5**。

两边均 5 轮、4 分；C 多花 116,624 token，其中输入增加 115,022。双方都验证物种/性状的 F1/AUROC，但 C 的并行读取和返回体量更大，不应写成“多轮探索导致”。

按工具结果字符数乘随后发送次数计算，chunks 的累计曝光从 651,211 增至 934,846 字符，文档 overview 从 30,058 增至 107,456，另有社区描述 19,012。这是原文载荷与社区载荷共同增加，不能把全部 token 增量算给社区元信息；字符曝光仅用于解释机制，不替代 API usage。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper214/naive_paperscope_results_comparison_263.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/paper187/community_paperscope_results_comparison_263.json)。

## H．看到升分仍不足以证明社区起了独立作用

有 **71 个升分 case**（ScholarQA 9、gap 25、comparison 33、trend 4）未发现 A 的仅-overview采用线索，也未发现 B 的显式导航链，且不属于已标记的评分争议。它们往往表现为更好地使用已经获得的论文、选择更准确的段落或组织更完整的答案。可以计入模式的实际收益，**不能直接计为社区独有信息带来的收益**；也不能反过来断言社区完全没影响模型。

### 已有论文被更完整采用，新增概览并不是已证明的提分来源 — `scholarqa:akari_cs_3`

score **3→4**；QA token **15,333→17,236**（+1,903，+12.4%）；轮次 **2→2**。

C 最终用 D0195 的 FTICL 与 D0383 的 ProMoT 回应缓解办法；这两篇 N 也已经获得。C 新增的仅-overview文档 D0126 没有在答案中被明确采用，两边均 2 轮。

因此 3→4 的确说明 C 这次回答更完整，却不能解释为社区发现了此前没有的解决办法。候选组织可能改变了取舍，首轮查询和生成差异也可能影响结果；这类 case 需要固定工具返回后的上下文消融才能进一步归因。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/scholar187/naive_scholarqa_akari_cs_3.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/20260923_fallback_case_audit/traces/scholar187/community_scholarqa_akari_cs_3.json)。

17 个评分争议也需从“社区效果”中隔开。例如 gap:355 的两答案都未单列问题未要求的 Dale，N judge 因此扣分、C judge 明确不扣，形成 2→4；comparison:242 的两答案围绕四个明确主题，C 却因未答 gold 额外列出的 PBADet 从 4 降到 3。这些分差不能用来证明社区补漏或干扰。

## 已验证的效果与改进优先级

| 优先级 | 改进方向 | case 依据 | 希望保留或修复的效果 |
|---|---|---|---|
| P0 | 回答前按问题列出对象、所需条件/比较轴，并检查哪些仍缺证据 | 35 个资料齐但漏答；23 个事实对齐错误 | 保留社区导览，避免把“看见论文”误当成“答齐问题”；gap 核假设/失败边界，comparison 绑定 dataset、metric、baseline、条件 |
| P0 | 为每次继续检索要求一个明确未解决的主问项，并对重复变体与无新增证据建立停止条件 | 83 个增成本未升分；98 个降成本不降分；30 个降成本却降分 | 压缩无收益探索，同时保留必要核验；不采用统一砍轮数的办法 |
| P0（评测） | 复核问题/gold 范围冲突，对相同遗漏使用一致判分口径 | 17 个已标记评分争议 | 避免按评分噪声优化社区召回或答案内容 |
| P1 | 以问题对子社区/文档候选重排；近似并列的跨社区边保留有区别的候选，避免只取最大边 | 12 个参考缺口，7 个伴随降分；固定命中重放有 5 个 fallback 覆盖损失 | 保留小社区的聚焦效果，补回拆分与单边选择漏掉的必要主题 |
| P1 | 社区与文档概览优先做导航；按问题需要补充实验/限制原文，选择性展示扩展成员 | 30 个概览采用线索收益混合；9 个导航有正有负；comparison:263 同轮载荷增加 | 保留 kNN-LM 式低成本补主题，减少旁支背景挤占注意力；不能按 G 外一刀切删除 |
| P2 | 固定查询和 chunk 返回，对比有/无社区描述、有/无成员 overview，再单独对比 fallback 分组 | 71 个升分尚未识别出直接采用或导航线索 | 把社区的信息收益、组织作用、查询波动和 fallback 的结构作用拆开验证 |

当前证据最支持的是：**社区有用，已能补入答案主题并提供可执行的文档导航；但主要瓶颈通常已从“找哪篇”转到“读哪段、对齐什么条件、何时停止”。** 在这批变化 case 中，不能把 95 次升分全算作社区成功，也不能把降分全归咎于社区噪声。优先改进答案覆盖、精确证据定位和探索收束，再扩大或细化社区，依据更充分。
