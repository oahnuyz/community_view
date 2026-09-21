# ScholarQA-Multi：naive 与 community 的逐题 trace 对比报告

分析日期：2026-09-21。范围：同一 prepared 数据集前 92 条 QA、两次已完成实验；本次只做离线分析，没有重新运行模型、检索或评分。

## 1. 主要结论

community 的单次 judge 平均分从 **3.3261 提升到 3.4239**，归一化从 **83.15% 到 85.60%（+2.45 个百分点）**；总 Agent 轮数从 **264 降到 246（−18）**。但不能把全部分数差当作社区带来的真实准确率变化：至少存在多组“同样缺项，一边扣分另一边不扣”的明显评测一致性疑点。

直接证据最强的是 `hao_photonics_9`：相同查询、相同 chunk 结果、相同轮次，只有 community 多出的 overview 提供了 optomechanical 平台材料，最终答案也补上了该类别。`hao_photonics_10` 的猫态补充同样有明确来源。相反，`weijia_cs_8` 两份 Visprog 答案实质相同，judge 却给 2 和 4，不能视为可靠的社区收益。

轮次减少有三种不同原因：更早得到足够覆盖、减少重复探索/越界读取、将工具并行安排到同一轮。轮次增加也不必然有益：`akari_cs_1` 保持 4 分但从 2 轮增到 5 轮，token 增至约 6.31 倍；`pan_biophysics_4` 轮次下降但工具数反而上升。

## 2. 数据来源与比较口径

- naive：[results.jsonl](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/results.jsonl)；[summary.json](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/summary.json)；[execution.json](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/execution.json)。
- community：[results.jsonl](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/results.jsonl)；[summary.json](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/summary.json)；[execution.json](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/execution.json)。

逐题按 `id` 对齐，并核对 question/gold 一致；两边 QA、judge 均为 92 成功、0 失败。本文的 score/accuracy 指 **LLM judge 的 0–4 分**，normalized accuracy 是均分÷4，不是二元正确率。Δ 都是 community−naive。

`rounds` 是模型调用次数，**包含最终回答轮**；例如 2 轮通常是 1 次工具规划+1 次最终回答。一轮可以并发多个工具；HTTP 重试不增加该值。本文同时统计工具数、错误数和实际 QA token，防止用轮次替代工作量。QA token 包含 query embedding，不含入库和 judge。

已逐行核对两份 SQLite 的 documents/chunks（包含向量字节），内容哈希完全一致：

```text
documents: a354b643eb80a64b174e7a083b8daa991efa9e353a841963599fd2885f7be78a
chunks:    863d50202c8a5e4b7a458d4e5006a90d5b31c529b18f8d15b2ce3930e371bd05
```

92 对 trace 的初始 system/user 消息逐题完全一致。两份 execution 配置仅 storage 路径不同，judge 模型/并发/prompt 一致；community 由实验 `modes` 参数启用，execution 中主配置的 `retrieval.mode: naive` 并不意味着 community 没有启用，trace 中实际返回了 communities。检索默认虽为 vector，Agent 实际大多选择 hybrid：naive 的 255 次搜索为 hybrid 202 / vector 35 / keyword 18，community 的 239 次为 192 / 34 / 13。

限制：两次独立 Agent 运行，首个工具请求完全相同的只有 **31/92** 题，首个返回的有序 chunk ID 完全相同的为 **22/92**。第一轮规划尚未看到社区结果，因此第一轮的 query/并行数差异不能反向归因于社区。温度为 0 也不能从这两次样本证明服务完全确定。trace 保存模型可见消息、工具调用和结果，不包含可供验证的内部推理；本文把“观察到的行为”与“可能原因”区分开，不虚构模型心理。

## 3. 整体结果与分组

| 指标 | naive | community | 变化 |
|---|---:|---:|---:|
| 平均 QA 秒数 | 14.38 | 14.23 | -1.04% |
| 平均 QA tokens（含 embedding） | 36447.59 | 39324.55 | +7.89% |
| 平均 rounds | 2.8696 | 2.6739 | -6.82% |
| judge 总分 | 306 | 315 | +9 |
| judge 均分（满分 4） | 3.3261 | 3.4239 | +0.0978 |
| normalized accuracy | 83.15% | 85.60% | +2.45 pp |
| 工具调用总数 | 299 | 273 | -8.70% |
| 搜索调用 | 255 | 239 | -6.27% |
| 读取调用 | 44 | 34 | -22.73% |
| 逐题去重 overview 数之和 | 1,512 | 3,227 | +113.43% |
| 逐题去重 chunk 数之和 | 1,702 | 1,633 | -4.05% |
| 工具结果字符数之和 | 6,197,485 | 7,883,585 | +27.21% |

overview 和 chunk 统计是“每题内去重后求和”，不同题同一文档仍分别计数；工具结果字符数是 JSON 文本长度，**不是 tokens**，也不等于多轮重复传入的累计输入量。community overview 数增长约 113.43%，但 QA token 仅增加 7.89%，同时总轮次下降，减少了反复传入历史的机会；不能仅靠这些汇总量做严格成本归因，也不能保证这种抵消适用于其他数据集。

| score 变化 \ rounds 变化 | rounds 减少 | rounds 不变 | rounds 增加 | 合计 |
|---|---:|---:|---:|---:|
| score 上升 | 2 | 9 | 5 | 16 |
| score 不变 | 16 | 43 | 8 | 67 |
| score 下降 | 4 | 4 | 1 | 9 |
| 合计 | 22 | 56 | 14 | 92 |

评分增加：11 题 +1、5 题 +2，共 +21 分；下降：6 题 −1、3 题 −2，共 −12 分。两项任一变化的案例共 **49** 个，全部列在第 6 节；其余 43 个“两项不变”不代表答案或检索轨迹完全相同。

### 3.1 按题目 ID 前缀看净变化

这只是数据集分组，不据少量题目推断整个学科的效果。

| 分组 | 题数 | score 净变化 | rounds 净变化 |
|---|---:|---:|---:|
| norman_bio | 10 | -3 | -8 |
| benjamin_bio | 9 | -1 | +3 |
| akari_cs | 10 | +1 | +3 |
| rulin_cs | 3 | +0 | -2 |
| weijia_cs | 9 | +7 | +3 |
| jacqueline_cs | 7 | -2 | -5 |
| pan_biophysics | 9 | +0 | +0 |
| shengyan_photonics | 10 | +2 | -2 |
| minyang_physics | 6 | +0 | -9 |
| hao_photonics | 10 | +4 | +0 |
| yanyu_photonics | 9 | +1 | -1 |

### 3.2 四类变化案例导航

**评分上升（16 题）**：[benjamin_bio_1](#case-benjamin_bio_1)（+1）、[akari_cs_7](#case-akari_cs_7)（+1）、[weijia_cs_1](#case-weijia_cs_1)（+1）、[weijia_cs_4](#case-weijia_cs_4)（+2）、[weijia_cs_6](#case-weijia_cs_6)（+1）、[weijia_cs_8](#case-weijia_cs_8)（+2）、[weijia_cs_9](#case-weijia_cs_9)（+1）、[shengyan_photonics_3](#case-shengyan_photonics_3)（+2）、[shengyan_photonics_4](#case-shengyan_photonics_4)（+1）、[shengyan_photonics_8](#case-shengyan_photonics_8)（+1）、[minyang_physics_5](#case-minyang_physics_5)（+1）、[hao_photonics_3](#case-hao_photonics_3)（+2）、[hao_photonics_4](#case-hao_photonics_4)（+1）、[hao_photonics_9](#case-hao_photonics_9)（+2）、[hao_photonics_10](#case-hao_photonics_10)（+1）、[yanyu_photonics_1](#case-yanyu_photonics_1)（+1）。

**评分下降（9 题）**：[norman_bio_2](#case-norman_bio_2)（-1）、[norman_bio_7](#case-norman_bio_7)（-2）、[benjamin_bio_6](#case-benjamin_bio_6)（-1）、[benjamin_bio_7](#case-benjamin_bio_7)（-1）、[jacqueline_cs_3](#case-jacqueline_cs_3)（-1）、[jacqueline_cs_4](#case-jacqueline_cs_4)（-1）、[shengyan_photonics_10](#case-shengyan_photonics_10)（-2）、[minyang_physics_3](#case-minyang_physics_3)（-1）、[hao_photonics_1](#case-hao_photonics_1)（-2）。

**iteration 上升（14 题）**：[benjamin_bio_1](#case-benjamin_bio_1)（+2）、[benjamin_bio_2](#case-benjamin_bio_2)（+1）、[benjamin_bio_7](#case-benjamin_bio_7)（+1）、[benjamin_bio_10](#case-benjamin_bio_10)（+1）、[akari_cs_1](#case-akari_cs_1)（+3）、[akari_cs_7](#case-akari_cs_7)（+1）、[weijia_cs_1](#case-weijia_cs_1)（+2）、[weijia_cs_9](#case-weijia_cs_9)（+2）、[pan_biophysics_3](#case-pan_biophysics_3)（+1）、[shengyan_photonics_3](#case-shengyan_photonics_3)（+1）、[minyang_physics_2](#case-minyang_physics_2)（+1）、[yanyu_photonics_3](#case-yanyu_photonics_3)（+1）、[yanyu_photonics_4](#case-yanyu_photonics_4)（+1）、[yanyu_photonics_5](#case-yanyu_photonics_5)（+1）。

**iteration 下降（22 题）**：[norman_bio_1](#case-norman_bio_1)（-3）、[norman_bio_2](#case-norman_bio_2)（-1）、[norman_bio_6](#case-norman_bio_6)（-1）、[norman_bio_7](#case-norman_bio_7)（-2）、[norman_bio_8](#case-norman_bio_8)（-1）、[benjamin_bio_8](#case-benjamin_bio_8)（-1）、[benjamin_bio_9](#case-benjamin_bio_9)（-1）、[akari_cs_3](#case-akari_cs_3)（-1）、[rulin_cs_1](#case-rulin_cs_1)（-1）、[rulin_cs_2](#case-rulin_cs_2)（-1）、[weijia_cs_4](#case-weijia_cs_4)（-1）、[jacqueline_cs_6](#case-jacqueline_cs_6)（-3）、[jacqueline_cs_10](#case-jacqueline_cs_10)（-2）、[pan_biophysics_4](#case-pan_biophysics_4)（-1）、[shengyan_photonics_2](#case-shengyan_photonics_2)（-1）、[shengyan_photonics_5](#case-shengyan_photonics_5)（-1）、[shengyan_photonics_10](#case-shengyan_photonics_10)（-1）、[minyang_physics_1](#case-minyang_physics_1)（-3）、[minyang_physics_3](#case-minyang_physics_3)（-5）、[minyang_physics_5](#case-minyang_physics_5)（-1）、[minyang_physics_6](#case-minyang_physics_6)（-1）、[yanyu_photonics_8](#case-yanyu_photonics_8)（-4）。


## 4. 从 trace 可确认的机制

### 4.1 社区补充缺失类别：`hao_photonics_9`（2→4，2→2 轮）

两边唯一查询都是 `physical platforms to study quantum properties of phonons`，返回的 12 个 chunk 与顺序完全相同。community 额外注入的 **Quantum Phononics with Superconducting Circuits and Mechanical Resonators** 社区包含下列未被 naive 召回的成员 overview：

- `c7e688622f789b3f2c87cece40b1ce4318d870525fc2e163720eab836bdf8bbb`，*Non-classical correlations between single photons and phonons from a mechanical oscillator*：含 “non-classical photon–phonon correlations” 对应材料。
- `e0aeffe42c49a07d8612a5f84fa084127bdb2f6e050c9b9944bbe83a3751c096`，*Optically heralded microwave photon addition*：overview 明确说 “demonstrated in an optomechanical transducer”。

最终 community 答案补出 “Optomechanical transducers/nanomechanical resonators”，naive 被扣分的恰是 optomechanical 平台缺失。这是最接近受控比较的正例。关键文档在选中文档的本体叶社区内，因此它证明的是**叶社区成员 overview 的价值**，不能据此单独证明跨社区边的贡献。两边都没有后续读取原文：最终答案可直接利用 overview。

### 4.2 新证据与已有证据利用要分开：`hao_photonics_10`（3→4，2→2 轮）

首个同参查询和 chunk 排序相同。community 新增文档 `cda19405e0ebba15e573830eb6a0f4b38ae8f6e1c5bf3bfb9134d7948ff21b43`（*Schrödinger cat states of a 16-microgram mechanical oscillator*）的 overview，随后答案补上猫态。naive 全部工具上下文没有 `cat state`。但 `ground state` 已存在于 naive chunk，naive 最终仍漏基态；因此该题的“猫态增益”是覆盖增加，“基态增益”是综合更完整。不能笼统说两个要点都是社区新增。

### 4.3 额外查询与扩展共同生效：`shengyan_photonics_3`、`weijia_cs_4`

`shengyan_photonics_3` 的首轮 chunk 一致，但 community 增加 cold atoms/molecules/superfluids 查询才召回 C60、25 kDa 分子，并展开包含 BEC/液氦超流的社区。答案从仅机械系统变成跨多类平台列表，2→4；这支持“扩展帮助综合”，但先发生了不同的第二轮查询，不能归为纯社区效应。

`weijia_cs_4` 第一个 community 工具结果的额外 overview 已给出 SSCD；**同一轮第二个并行查询**也独立返回 SSCD chunk。后者是在模型看到第一个工具结果之前就发出的，不能说“overview 引导了这条查询”。能确认的是社区和独立检索均填补了图像拷贝检测材料，且 community 没有 naive 的两次失败试读。

### 4.4 低相关 chunk 会被放大为整组无关社区：`norman_bio_2`

community 的 vector 查询 `LNP liver accumulation avoid hepatic uptake strategies` 把 *IceCat-1: The IceCube Event Catalog of Alert Tracks* 排进前三个不同文档。程序因此先纳入其本体 **Multi-Messenger Astrophysics and High-Energy Neutrino Observations** 叶社区，再沿该文档的最大关联边（权重约 **0.4406**）连接 *GWTC-1* 文档所在的 **Gravitational-Wave Physics and Astronomy** 社区。

这里不是一条“LNP→天体物理”的错误图边：问题从**向量召回的种子文档不相关**开始，后续天体物理内部的边可能很合理，但对当前问题毫无帮助。第二次搜索额外注入 17 份 overview，其中两个新社区都偏离医学问题。最终答案没有明显把天体物理写进去，因此只能确认噪声与成本，不能断言它造成 −1 分。

### 4.5 工具接口错误是 iteration 的主要混杂因素

413 篇文档中 **346 篇只有 1 个 chunk**（83.78%）；56 篇有 2 个，其余 11 篇有 3–6 个。Agent 却频繁猜测 `[0,1,2,3]` 等序号。当前 `read_chunks` 只要请求中有一个不存在的 ordinal，就整次报错，不返回其中合法部分。

| 读取诊断 | naive | community |
|---|---:|---:|
| read_chunks 次数 | 44 | 34 |
| Unknown chunk ordinal | 37 | 24 |
| 参数 schema 错误 | 1 | 0 |
| 成功读取 | 6 | 10 |
| 发生工具错误的题数 | 21 | 15 |
| 整轮工具全部报错的轮数 | 11 | 7 |

`rulin_cs_2` 的 naive 第 2 工具轮五次读取全部失败，community 恰好少这一轮，评分均 4；`pan_biophysics_4` 的 community 五次失败读取合并一轮，下一轮再成功读取五个 ordinal 0，工具次数比 naive 更多、轮数却更少。这些是 trace 直接可见的执行路径差异。总轮数净减 18、全错误轮净减 4，但不能简单把二者相减作为“纯社区节省轮数”，因为路径间仍会互相影响。

### 4.6 单次 judge 的尺度不一致，必须与真实答案差异分开

| 案例 | 记录分差 | 两份答案中的共同缺项/核心一致点 | judge 不一致之处 |
|---|---:|---|---|
| [weijia_cs_8](#case-weijia_cs_8) | +2 | 均只解释 Visprog，均未展开 ViperGPT/Socratic Models | naive 被按缺框架扣分，community 按核心含义判满分 |
| [hao_photonics_3](#case-hao_photonics_3) | +2 | 均未明确列出 quantum eraser | naive 被扣第三类，community 只覆盖另外两类仍满分 |
| [shengyan_photonics_10](#case-shengyan_photonics_10) | −2 | 均漏电势阱 | naive judge 错把 doughnut/core-shell 当全部核心，community 正确要求电势阱 |
| [jacqueline_cs_4](#case-jacqueline_cs_4) | −1 | 均漏 Orca，均给出 Skill-it | 只对 community 的相同遗漏扣分 |
| [norman_bio_2](#case-norman_bio_2) | −1 | 均漏 hybrid lipid-polymer 明确方案 | 只对 community 扣分 |
| [minyang_physics_5](#case-minyang_physics_5) | +1 | 均未写 adjoint，核心优化说明相近 | 只对 naive 以 adjoint/LDOS 扣分 |

上述判断来自对两份最终回答、gold 和 judge reasoning 的并排阅读，不是重新评分；本报告**不修改任何原始 score，也不计算人为“校正后准确率”**。差异可能包含细微措辞影响和评分随机性，单次运行不能估计稳定收益。

## 5. 改进优先级（建议，未修改系统实现）

1. **先修读取工具的可用性。** 返回文档可用 ordinal 范围/数量，或增加按相邻范围安全读取的语义；对越界请求返回合法序号提示。这样才容易区分检索能力与工具误用导致的轮次。
2. **先复核 judge 再放大结论。** 固定 question/gold，对疑点案例盲化复评并交换输入顺序，或重复独立评分；先做 gold 要点核对再打 0–4 分。无需先重跑 QA。
3. **做离线消融区分信息来源。** 固定相同 query/chunk 轨迹，比较仅 chunks、加本体社区 overview、再加邻接社区 overview。当前样本不能独立证明跨社区边的边际收益。
4. **检查种子相关性。** 在 community 扩展前验证 top-doc 与问题的相关性，重点审计“生物问题→IceCat-1”这样的例子；仅增大图边阈值不一定解决种子不相关问题。
5. **停止条件看问题覆盖而不只看信息量。** 明确检查枚举项、比较维度和限制条件，避免有很多 overview 就提前结束，也避免已有完整答案仍反复核验。
6. **效率同时看轮数、工具数、错误、token 和时间。** 已有日志无需新增逐 API 明细即可做这些诊断。本报告没有引入上下文截断/预算等此前暂缓的功能。

## 6. 全部变化案例：逐题原因与工具时序

共 49 题：先列全部评分变化 25 题，再列评分不变但 rounds 变化的 24 题。每例的原因段是人工对照后的解释；工具表由 trace 直接提取。`新增 overview` 指本次工具结果实际注入数量（已执行问题级去重），不能直接等同新增正确证据。完整答案/gold/judge 以原始结果文件为准。

<a id="case-norman_bio_2"></a>

### 1. norman_bio_2 — 提前结束；评分口径疑点

**问题：** What experimental strategies can be introduced to prevent LNPs to be exclusively accumulated in the liver?

**评分：4→3（Δ-1）；rounds：3→2（Δ-1）。**

工具数 4→2；错误 1→0；文档 overview 18→40；QA tokens 38,229→24,902。

community 在首轮两路搜索后就回答，naive 还进行了一轮搜索（夹带一次无效读取）。两份答案都包含 SORT、组分调整、主动靶向和 PECAM/PLVAP，都没有明确提出 hybrid lipid-polymer 方案；judge 却只以此扣 community 的分，所以 4→3 不能可靠归因于提前结束。更直接的检索缺陷出现在 community 的 vector 查询：前三文档混入 IceCat-1，从而额外注入天体物理和引力波社区。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/7402ddfe05ef4e0cbe84b0e30924ea41.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/cd8ef974a3864c8aa5646f0b57bbfd18.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] prevent LNPs exclusively accumulated in liver lipid nanoparticles hepatic accumulation；全库 | 12 | 11 | 0 | 成功 |
| 1 | search_chunks [vector] strategies to reduce liver tropism of lipid nanoparticles；全库 | 12 | 5 | 0 | 成功 |
| 2 | read_chunks doc_id=256aa8a4a689cbfe046921e581b021e2fd81bcf5368c4fdd610ca44f4a93cfe7 ordinals=[0, 1] | 0 | 0 | 0 | Unknown chunk ordinal |
| 2 | search_chunks [hybrid] SORT molecule extrahepatic delivery LNP composition change proportion organ targeting；全库 | 12 | 2 | 0 | 成功 |

judge 原文：The generated answer accurately captures the main strategies from the gold answers, including SORT nanoparticles, altering LNP composition, and active targeting with specific examples like anti-PECAM/PLVAP, with only additional consistent context.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] experimental strategies to prevent LNPs exclusively accumulated in liver；全库 | 12 | 23 | 3 | 成功 |
| 1 | search_chunks [vector] LNP liver accumulation avoid hepatic uptake strategies；全库 | 12 | 17 | 2 | 成功 |

judge 原文：The generated answer correctly captures most key strategies (SORT, composition modulation, ligand-based active targeting, and endothelial-targeted LNPs) but omits the hybrid lipid-polymer nanoparticle strategy mentioned in the gold answer.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Based on the context, strategies to prevent exclusive liver accumulation of LNPs include:
> 
> - **SORT (selective organ targeting) nanoparticles**: adding a supplemental SORT molecule whose chemical structure determines the LNP's tissue-specific activity, enabling delivery to non-liver tissues (e.g., lungs, spleen).
> - **Changing the LNP composition/proportions**: altering the proportion of LNP components can redirect mRNA delivery to organs such as lungs, spleen, and liver.
> - **Active targeting**: grafting targeting ligands (antibodies, antibody fragments, peptides, aptamers, small sugars/molecules) onto LNPs. For example, endothelial-targeted LNPs (anti-PECAM or anti-PLVAP) redirect modified mRNA-LNPs from liver to lung tissue with substantial lung accumulation.
> - **Passive targeting**: modulating lipid composition to achieve beneficial surface composition, charge, and size, which can enable targeted nucleic acid delivery (e.g., via protein corona/apoE interactions).


**community**

> Based on the context, experimental strategies to prevent LNPs from accumulating exclusively in the liver include:
> 
> - **SORT (selective organ targeting) nanoparticles**: adding a supplemental SORT molecule whose chemical structure determines tissue-specific activity, enabling mRNA/gene-editing delivery to non-liver tissues.
> - **Modulating LNP composition/proportion**: changing the ratio/proportion of LNP components to redirect delivery to organs such as the lungs or spleen.
> - **Active targeting**: grafting targeting ligands (antibodies, antibody fragments, peptides, aptamers, or small sugars/molecules) onto LNPs to engage target-cell surface molecules.
> - **Passive targeting**: tuning lipid composition, surface charge, size, and shape; PEG surface modification reduces opsonization/RES (liver/spleen) clearance.
> - **Endothelial-targeted LNPs**: e.g., anti-PECAM or anti-PLVAP targeted LNPs to redirect mRNA-LNPs from the liver to the lung.

</details>

<a id="case-norman_bio_7"></a>

### 2. norman_bio_7 — 定向搜索替代试读；评分口径疑点

**问题：** What are the production challenges and solutions associated with the large-scale manufacturing of recombinant antibodies?

**评分：4→2（Δ-2）；rounds：5→3（Δ-2）。**

工具数 6→4；错误 2→0；文档 overview 21→25；QA tokens 70,534→36,819。

naive 用四个工具轮逐渐扩展制造挑战，第三轮两次 read_chunks 全部越界；community 用两个工具轮、第二轮直接按 doc_ids 检索 CHO/Fab 和糖基化文档。community 答案更集中于糖链/电荷异质性、CHO 和质谱；两者均未写出植物生产系统，naive 的 judge 忽略该遗漏而 community 被据此扣分。可确认无效读取减少和答案范围收缩，不能把 −2 全部视为社区检索造成的漏召回。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/1d0a77ba8fed4a1ab5dacd1a55a58ee9.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/b3018ab013c34a10b5f7d2b2b0276cd9.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] production challenges and solutions large-scale manufacturing recombinant antibodies；全库 | 12 | 12 | 0 | 成功 |
| 2 | search_chunks [hybrid] manufacturing challenges antibody production aggregation glycosylation titer downstream processing；全库 | 12 | 6 | 0 | 成功 |
| 2 | search_chunks [hybrid] large-scale production challenges recombinant antibody purification yield stability；全库 | 12 | 2 | 0 | 成功 |
| 3 | read_chunks doc_id=c348d39386ff94c9fdefebad45923180e13a939ff242b9e0f0dac66be5633be8 ordinals=[0, 1, 2, 3, 4, 5] | 0 | 0 | 0 | Unknown chunk ordinal |
| 3 | read_chunks doc_id=ccecf87e781cd778df4caccc5a35543546463d89f0383078efbc6b49a1fb0106 ordinals=[0, 1, 2, 3, 4] | 0 | 0 | 0 | Unknown chunk ordinal |
| 4 | search_chunks [hybrid] solutions to manufacturing challenges recombinant antibody production；全库 | 12 | 1 | 0 | 成功 |

judge 原文：The generated answer accurately captures the core challenges and solutions related to glycosylation variability, monitoring, and optimization of culture conditions/genetic engineering, and the additional details are consistent with the gold answers, making it a perfect match despite extra context.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] production challenges solutions large-scale manufacturing recombinant antibodies；全库 | 12 | 23 | 3 | 成功 |
| 1 | search_chunks [vector] recombinant antibody production challenges upstream downstream processing；全库 | 12 | 2 | 0 | 成功 |
| 2 | search_chunks [hybrid] Fab full-length antibody CHO production challenges yield；doc_ids=c348d39386ff | 1 | 0 | 0 | 成功 |
| 2 | search_chunks [hybrid] manufacturing challenge heterogeneity charge variants glycosylation solution；doc_ids=ccecf87e781c,9af18c655c8b,9466e7575801 | 3 | 0 | 0 | 成功 |

judge 原文：The generated answer correctly identifies glycan heterogeneity as a challenge and mentions CHO cell improvements, but it omits key gold-answer solutions such as plant-based systems and the use of mass spectrometry to assess glycosylation profiles, so it is only partially correct.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Based on the context, key production challenges and solutions for large-scale recombinant antibody manufacturing include:
> 
> - **Low yields**: Addressed by engineering recombinant proteins, bioprocess development, and host cell improvements, enabling >10 g/L yields in CHO cell cultures.
> - **Heterogeneity of glycosylation** (which affects effector functions and hinders analysis): Requires focus on quantitation of site-specific glycosylation in manufactured antibody drugs.
> - **Acidic charge variants** (affecting stability, activity, immunogenicity, pharmacokinetics): Managed by monitoring during manufacturing to stay within proven acceptable ranges; a solution is cell culture media supplementation with bioflavonoids to reduce acidic species charge variants.
> - **Aggregation** (linked to immunogenicity/hepatotoxicity and limiting drug loading): Addressed via hydrophilic linkers, site-specific conjugation (e.g., engineered cysteines with selective reduction, in silico site screening to shield hydrophobic linkers), avoiding unnatural amino acids that increase aggregation risk.
> - **Protein misfolding/inclusion bodies** in E. coli for disulfide-bonded proteins: Mitigated by lower growth temperatures, choice of medium, induction time, aeration, and strain.
> - **Recombinant polyclonal antibodies** require new chemistry, manufacturing and control (CMC) technologies; mass-spectrometry-based methods (marker peptides, light-chain LC-MS) provide identification and quality control of the 25-antibody product Sym001.
> - **Antibody selection by affinity only** (phage panning): Overcome by clonal cocultivation of E. coli and eukaryotic cells in miniecosystems to select on biological function.


**community**

> Based on the available context, the large-scale manufacturing challenges and solutions for recombinant antibodies include:
> 
> **Challenges:**
> - **Product heterogeneity**: Charge variants (acidic species from covalent modifications and chemical degradation) and glycan heterogeneity affect stability, activity, immunogenicity, pharmacokinetics, and effector functions; heterogeneity hinders analysis.
> - **Quality control of complex products**: Recombinant polyclonal antibodies (e.g., Sym001 with 25 unique antibodies) require new chemistry, manufacturing, and control (CMC) technologies for well-characterized release.
> 
> **Solutions:**
> - **Recombinant protein engineering, bioprocess development, and host cell improvements** enabling yields >10 g/L in CHO cell cultures.
> - **Cell culture media supplementation with bioflavonoids** to targeted reduction of acidic charge variants.
> - **Monitoring** charge variants during manufacturing to keep them within proven acceptable ranges.
> - **Novel mass spectrometry methods** (marker peptides and light chain LC–MS) for unambiguous identification and relative quantitation of individual antibodies, qualified for quality control.

</details>

<a id="case-benjamin_bio_1"></a>

### 3. benjamin_bio_1 — 轮次增加主要含错误恢复；评分口径疑点

**问题：** What are the benefits of LNP-based drug delivery compared to other nanoparticle-based applications?

**评分：3→4（Δ+1）；rounds：2→4（Δ+2）。**

工具数 2→4；错误 0→1；文档 overview 14→23；QA tokens 15,567→40,805。

naive 首轮两次搜索后回答；community 首轮注入 23 份 overview 后又试读 [0,1]，因越界失败，再对两篇已知文档做定向搜索。两份答案均包含稳定性、载药效率、成本/扩产、临床应用；community 把 reduced immune response 单独列出，但没有明显补齐 naive 被扣分的“较脂质体毒性更小且疗效相近”。+1 有表达/评分阈值因素，不能视为额外两轮带来的确定收益。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/ef4c1b0239854cc096aedb8a34370638.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/205f1c2e0b0a4c39bcd5fb00badb4845.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] benefits of LNP-based drug delivery compared to other nanoparticle-based applications；全库 | 12 | 11 | 0 | 成功 |
| 1 | search_chunks [hybrid] lipid nanoparticles advantages over other nanoparticles；全库 | 12 | 3 | 0 | 成功 |

judge 原文：The generated answer correctly captures most key benefits of LNP delivery (stability, cost, scale-up, encapsulation efficiency, avoiding polymer drawbacks, clinical maturity), but omits some important gold-answer details such as minimized toxicity and similar efficacy compared to liposomes.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] benefits of LNP-based drug delivery compared to other nanoparticle-based applications；全库 | 12 | 23 | 3 | 成功 |
| 2 | read_chunks doc_id=d727dc65df3dce5ba49ddbc01c1596964ea1519178b01e75d4833b21a5bc6cee ordinals=[0, 1] | 0 | 0 | 0 | Unknown chunk ordinal |
| 3 | search_chunks [hybrid] lipid nanoparticles advantages stability cost scale-up liposomes；doc_ids=d727dc65df3d | 1 | 0 | 0 | 成功 |
| 3 | search_chunks [hybrid] lipid nanoparticles advantages over polymer nanoparticles encapsulation immune response；doc_ids=1809b8ddd9dc | 2 | 0 | 0 | 成功 |

judge 原文：The generated answer accurately captures all key benefits from the gold answers, including encapsulation efficiency, reduced immune response, stability, cost/scale-up, clinical translation, and vaccine applications, with no contradictions.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Based on the context, the benefits of LNP-based drug delivery compared to other nanoparticle applications include:
> 
> - **Greater stability** than liposomes, both in biological fluids and during storage, plus lower production cost and better potential for scale-up preparation.
> - **Higher encapsulation/loading efficiency** than polymer nanoparticles (e.g., 59% vs 37% in lipid-polymer hybrids), with the lipid component increasing loading efficiency and permeation.
> - **Controlled release** – the lipid barrier inhibits burst release (20 h vs 7 h to release 50% of drug), improving controlled delivery.
> - **Avoids polymer drawbacks** such as low encapsulation and immune responses induced by high-molecular-weight polymers.
> - **Enhanced physical stability and complex internal architectures** (solid lipid NPs, nanostructured lipid carriers) with ability to control location and timing of drug delivery.
> - **Clinically mature for nucleic acid delivery** – they effectively protect and transport mRNA/siRNA (e.g., Onpattro, COVID-19 mRNA vaccines), and can achieve targeted delivery via passive mechanisms (e.g., apoE–LDLR) without needing clinically approved active targeting ligands.


**community**

> Based on the context, the benefits of LNP-based drug delivery compared to other nanoparticle-based applications include:
> 
> - **Higher encapsulation/loading efficiency** than polymer nanoparticles (e.g., lipid-polymer hybrid NPs reached 59% vs. 37% for pure polymer NPs), with the lipid also increasing drug permeation.
> - **Reduced immune response** compared to polymer nanoparticles (which can easily induce immune responses due to high polymer molecular weight).
> - **Enhanced physical stability and biocompatibility**, including better stability in biological fluids and during storage.
> - **Controlled/sustained release** via the lipid barrier, inhibiting burst release effects.
> - **Lower production cost** and greater potential for **scale-up preparation** compared to liposomes.
> - **Clinically mature and versatile** — a key component of approved products like the COVID-19 mRNA vaccines and Onpattro, capable of targeted (e.g., passive targeting via protein corona, active ligand grafting) delivery of nucleic acids and other agents.

</details>

<a id="case-benjamin_bio_6"></a>

### 4. benjamin_bio_6 — 相近证据下的答案遗漏；评分口径疑点

**问题：** What are different chemical methodologies to form ADC linkers?

**评分：3→2（Δ-1）；rounds：4→4（Δ+0）。**

工具数 6→6；错误 2→1；文档 overview 27→24；QA tokens 66,319→72,399。

两者均 4 轮，naive 有两次越界读取，community 一次。community 虽追加了 click chemistry、lysine/azide 查询，但定向搜索回到已见文档，未补全最终答案中的赖氨酸、maleimide 和 PEG。两份答案都把 carbonate 与 thiol–disulfide exchange 关联；judge 对 naive 说是小错误，对 community 则以多个遗漏给 2 分。这里是未解决的答案覆盖问题叠加判分差异，不能证明社区有害。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/700867b1355d44f4a769723900bf2212.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/ce98223dd71340d8b4beb92752e7ebd6.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] chemical methodologies to form ADC linkers；全库 | 12 | 12 | 0 | 成功 |
| 1 | search_chunks [vector] ADC linker formation chemistry strategies；全库 | 12 | 5 | 0 | 成功 |
| 2 | read_chunks doc_id=07f786a7904dbd84ac36e202b82717aded4b65434525dfc8dcab17a645b5a6ff ordinals=[1, 2, 3, 4, 5] | 0 | 0 | 0 | Unknown chunk ordinal |
| 2 | read_chunks doc_id=311fbdbc9a9d7b056f10498ba91ba43bf38641ce25e3679a9b02292f52d84ee1 ordinals=[1, 2, 3, 4, 5, 6, 7] | 0 | 0 | 0 | Unknown chunk ordinal |
| 3 | search_chunks [hybrid] linker synthesis formation hydrazone disulfide peptide conjugation methods maleimide NHS ester；全库 | 12 | 3 | 0 | 成功 |
| 3 | search_chunks [keyword] ADC linker types cleavable non-cleavable hydrazone disulfide peptide non-cleavable MC SMCC；全库 | 12 | 7 | 0 | 成功 |

judge 原文：The generated answer largely captures the gold answer's distinction between cleavable and non-cleavable linkers and provides correct examples/conjugation strategies, but it contains a minor inaccuracy (carbonate cleavage via thiol-disulfide exchange) and omits lysine conjugation as a key site.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] chemical methodologies to form ADC linkers；全库 | 12 | 20 | 2 | 成功 |
| 1 | search_chunks [hybrid] ADC linker chemistry conjugation methods；全库 | 12 | 2 | 0 | 成功 |
| 2 | search_chunks [hybrid] click chemistry maleimide thiol conjugation linker formation reaction；全库 | 12 | 2 | 0 | 成功 |
| 2 | read_chunks doc_id=311fbdbc9a9d7b056f10498ba91ba43bf38641ce25e3679a9b02292f52d84ee1 ordinals=[0, 1] | 0 | 0 | 0 | Unknown chunk ordinal |
| 3 | search_chunks [hybrid] conjugation via lysine amines click chemistry azide alkyne；doc_ids=311fbdbc9a9d | 1 | 0 | 0 | 成功 |
| 3 | search_chunks [hybrid] site-specific conjugation methods linker formation；doc_ids=8792b03c0ad9 | 1 | 0 | 0 | 成功 |

judge 原文：The generated answer correctly covers cleavable/non-cleavable linkers and some conjugation chemistries, but omits important gold-standard facts such as lysine conjugation, the maleimide-thioester approach for cysteine, and PEG linker incorporation, making it incomplete.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Based on the context, ADC linkers are formed/classified by the following chemical methodologies:
> 
> **Cleavable linkers:**
> - **Hydrazone** – cleaved via acidic degradation in endosomes/lysosomes
> - **Disulfide** – cleaved via thiol–disulfide exchange reactions
> - **Peptide (dipeptide)** – cleaved by protease (cathepsin B)
> - **Carbonate** – cleaved via thiol–disulfide exchange
> 
> **Non-cleavable linkers:**
> - **MC and SMCC** – require complete lysosomal proteolytic degradation of the antibody
> 
> **Conjugation methodologies:**
> - **Thiol conjugation** – reduction of interchain disulfides (TCEP/DTT) to expose cysteines for drug attachment
> - **Site-specific conjugation** – via unnatural amino acids (e.g., azido phenylalanine/lysine) or enzyme-assisted ligation (formyl glycine-generating enzyme, transglutaminase)
> - Steric hindrance modifications (e.g., SPDB-DM4) to enhance linker stability in circulation


**community**

> Based on the context, the chemical methodologies to form ADC linkers include:
> 
> 1. **Conjugation via thiols** – reducing interchain disulfide bonds of IgG1 with TCEP or DTT to generate thiol groups for drug attachment (e.g., Adcetris; homogeneous conjugates via cysteine-to-serine mutations).
> 
> 2. **Cleavable linker chemistries**, formed through:
>    - Hydrazone linkers (acidic degradation)
>    - Disulfide/carbonate linkers (thiol–disulfide exchange reactions)
>    - Peptide/dipeptide linkers (protease cleavage by cathepsin B)
> 
> 3. **Non-cleavable linkers** such as MC and SMCC (require lysosomal proteolytic degradation of the antibody).
> 
> 4. **Site-specific conjugation via unnatural amino acids** – introducing azido methyl-L-phenylalanine, azido lysine, or N-acetyl-L-phenylalanine, whose special functional groups enable controllable, quantitative conjugation.
> 
> 5. **Enzyme-assisted ligation** – using formyl glycine-generating enzyme (FGE) or transglutaminase (TG) to modify specific amino acid residues for site-specific conjugation.
> 
> 6. **Sterically hindered linkers** (e.g., SPDB-DM4) to enhance stability in circulation.

</details>

<a id="case-benjamin_bio_7"></a>

### 5. benjamin_bio_7 — 无效探索与错误恢复增加；评分口径疑点

**问题：** What are potential candidates other than porcine model for xenotransplantation as a means to treat type-1 diabetes?

**评分：4→3（Δ-1）；rounds：5→6（Δ+1）。**

工具数 8→9；错误 0→1；文档 overview 31→46；QA tokens 135,136→164,490。

两者围绕非猪供体反复搜索 bovine/fish/stem cells，最后都回答干细胞衍生 β 细胞、没有其他动物候选。community 多一次越界试读及后续定向读取，最终更强地使用 only 并澄清非人灵长类是受体。judge 扣其漏 artificial pancreas，但 naive 也未把该系统列为方案。额外一轮没有产生新的正确候选；−1 部分可能来自更绝对措辞和评分口径。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/498c027553c748f9a060a3b864794e9f.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/218f306d3608495b86967dbaecce5815.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] xenotransplantation candidates other than porcine type-1 diabetes；全库 | 12 | 10 | 0 | 成功 |
| 1 | search_chunks [hybrid] islet xenotransplantation animal donor candidate non-porcine；全库 | 12 | 3 | 0 | 成功 |
| 2 | search_chunks [hybrid] islet source species bovine tilapia fish stem cell-derived beta cells alternative to pig；全库 | 12 | 6 | 0 | 成功 |
| 2 | search_chunks [hybrid] other potential donor animals xenotransplantation insulin-producing cells non-pig source；全库 | 12 | 1 | 0 | 成功 |
| 3 | search_chunks [keyword] bovine neonatal tilapia fish islet xenotransplantation diabetes donor；全库 | 12 | 4 | 0 | 成功 |
| 3 | search_chunks [keyword] alternatives to pig islets stem cell derived beta cells encapsulation；全库 | 12 | 5 | 0 | 成功 |
| 4 | search_chunks [keyword] tilapia islet xenotransplantation；全库 | 7 | 0 | 0 | 成功 |
| 4 | search_chunks [hybrid] xenogeneic islet source alternative pig candidate stem cell-derived beta cells human；全库 | 12 | 2 | 0 | 成功 |

judge 原文：The generated answer correctly identifies stem cell-derived beta cells as a promising alternative candidate, matching the key alternative mentioned in the gold answer, and accurately notes that no other animal species are mentioned.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] xenotransplantation candidates type-1 diabetes other than porcine；全库 | 12 | 27 | 3 | 成功 |
| 2 | search_chunks [hybrid] bovine islet xenotransplantation diabetes alternative animal source；全库 | 12 | 2 | 0 | 成功 |
| 2 | search_chunks [hybrid] xenotransplantation source other than pig nonhuman primate islet；全库 | 12 | 3 | 0 | 成功 |
| 3 | search_chunks [vector] alternatives pig islet source bovine fish nonhuman primate diabetes xenotransplantation candidate；全库 | 12 | 8 | 1 | 成功 |
| 3 | read_chunks doc_id=1ec1a20fa38f7d472a0211472774006a0ddbf62d0c1234c9399f504350fc9b2a ordinals=[2, 3, 4, 5] | 0 | 0 | 0 | Unknown chunk ordinal |
| 4 | search_chunks [keyword] alternative animal sources fish cattle human islet donors；doc_ids=1ec1a20fa38f | 2 | 0 | 0 | 成功 |
| 4 | read_chunks doc_id=1ec1a20fa38f7d472a0211472774006a0ddbf62d0c1234c9399f504350fc9b2a ordinals=[0, 1] | 2 | 0 | 0 | 成功 |
| 5 | search_chunks [hybrid] zebrafish bovine islets beta cell alternative pig xenotransplantation insulin；全库 | 12 | 6 | 1 | 成功 |
| 5 | search_chunks [vector] donor pancreas alternative beta cell source pig vs other animal xenotransplant T1D；全库 | 12 | 0 | 0 | 成功 |

judge 原文：The generated answer correctly identifies that no other animal species are viable xenotransplant candidates and highlights stem cell-derived beta cells as a promising alternative, but it omits the artificial pancreas system also mentioned in the gold answer and overstates that stem cells are the 'only' candidate.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Based only on the provided context, the potential alternative candidate for xenotransplantation to treat type-1 diabetes is **stem cell-derived beta cells**. The document "Artificial Pancreas or Novel Beta-Cell Replacement Therapies" states that the donor organ shortage may be solved by the utilization of stem cell-derived beta cells, which have shown great promise in animal models and are being tested in clinical studies; immunosuppression may be avoided by encapsulation.
> 
> The context does not mention any other animal species (e.g., bovine, fish) as alternative xenotransplantation candidates for treating type-1 diabetes.


**community**

> Based on the provided context, the only potential candidate mentioned other than the porcine model is **stem cell-derived beta cells** — described as showing promise in animal models and now being tested in clinical studies, with encapsulation to avoid immunosuppression (Nijhoff & de Koning, 2018).
> 
> Nonhuman primates appear in the context only as **recipients** of porcine islets (e.g., pig-to-nonhuman primate islet xenotransplantation), not as donor candidates. No other animal species (e.g., bovine, fish) are mentioned as xenotransplantation candidates for treating type-1 diabetes in the given documents.

</details>

<a id="case-akari_cs_7"></a>

### 6. akari_cs_7 — 扩大反例检索；回答立场仍不一致

**问题：** do we know how true the “superficial alignment hypothesis” is?
A model’s knowledge and capabilities are learnt almost entirely during pretraining, while alignment teaches it which subdistribution of formats should be used when interacting with users
Is it true for all domains/aspects or is it only true for more perceivable aspects like helpfulness?
Does SFT on a huge instruction dataset teach models new knowledge? Pointers to related papers would be appreciated.

**评分：2→3（Δ+1）；rounds：3→4（Δ+1）。**

工具数 4→6；错误 0→0；文档 overview 22→65；QA tokens 50,189→123,553。

community 三个工具轮（naive 两个），追加反事实方向、STaR/Orca/校准等反例，最终比 naive 更完整地说明 alignment 不仅影响风格；judge 因其概括更均衡给 3 分。然而答案仍写“Not really”，与列举的知识/能力增益不协调，且没补齐 gold 的 WebInstruct/MAmmoTH2。可见是更广的检索与综合路径，不是已证明所有新增事实只来自社区。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/2d8285181e9b42f1ad627ff3ab0f631c.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/1606e9bdb5924f13adf3aa43178d6328.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] superficial alignment hypothesis knowledge and capabilities learnt during pretraining alignment teaches subdistribution of formats；全库 | 12 | 10 | 0 | 成功 |
| 1 | search_chunks [hybrid] SFT on large instruction dataset teach models new knowledge capabilities；全库 | 12 | 7 | 0 | 成功 |
| 2 | search_chunks [hybrid] alignment tuning knowledge not learned, only style, helpfulness, capabilities, all domains or only superficial；全库 | 12 | 3 | 0 | 成功 |
| 2 | search_chunks [hybrid] does instruction tuning or fine-tuning add new factual knowledge to language models；全库 | 12 | 2 | 0 | 成功 |

judge 原文：The response correctly summarizes the LIMA hypothesis and supporting token-distribution evidence, but it omits the WebInstruct/MAmmoTH2 finding that large-scale instruction tuning can improve reasoning and overstates 'mostly no' for new capabilities, making the answer incomplete relative to the gold.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] superficial alignment hypothesis knowledge and capabilities learnt during pretraining；全库 | 12 | 34 | 3 | 成功 |
| 1 | search_chunks [hybrid] does SFT on instruction datasets teach models new knowledge；全库 | 12 | 8 | 1 | 成功 |
| 2 | search_chunks [hybrid] alignment tuning effect beyond style reasoning capabilities factuality counterevidence；全库 | 12 | 5 | 1 | 成功 |
| 2 | search_chunks [keyword] Superficial Alignment Hypothesis limits not fully true；全库 | 12 | 13 | 2 | 成功 |
| 3 | search_chunks [hybrid] instruction tuning imparts new abilities knowledge not in pretraining counterexample LIMA criticism；全库 | 12 | 0 | 0 | 成功 |
| 3 | search_chunks [hybrid] imitation models mimic style not factuality capabilities gap fine-tuning imitation data；全库 | 12 | 5 | 1 | 成功 |

judge 原文：The answer correctly captures the mixed evidence and partial validity of the hypothesis, but the direct response to whether SFT on a huge instruction dataset teaches new knowledge is misleadingly phrased as 'Not really' despite citing studies showing fine-tuning can improve reasoning and inject knowledge, which is an imprecision and partial inconsistency with the gold answer's conclusion.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> **How true is the Superficial Alignment Hypothesis?**
> 
> It is supported but not definitively settled for all aspects. Evidence:
> - **LIMA (Zhou et al., 2023)** proposed the hypothesis and showed that fine-tuning a 65B LLaMa on just 1,000 curated examples yields strong performance, concluding "almost all knowledge in large language models is learned during pretraining."
> - **"The Unlocking Spell on Base LLMs" (Lin et al., 2023)** provides the most direct evidence: base and aligned models decode nearly identically on most token positions, with almost all distribution shifts on *stylistic* tokens, which they say "strongly supports" the hypothesis. However, they explicitly conclude that "deeper analysis and theoretical understanding of alignment is crucial," implying it is not yet fully established across all domains/aspects. The evidence in the context centers on style/format (e.g., helpfulness), not a demonstrated proof for every capability.
> 
> **Does SFT on a huge instruction dataset teach models new knowledge?**
> 
> Mixed evidence, mostly no for genuine capabilities/factuality:
> - **"The False Promise of Imitating Proprietary LLMs" (Gudibande et al., 2023):** models fine-tuned on ChatGPT-style imitation data mimic its *style* (confident, well-structured) but not its *factuality*; they close little of the capability gap on tasks not heavily supported in the data. Better base models, not more instruction data, close the gap.
> - **"Fine-Tuning or Retrieval?" (Ovadia et al., 2023):** fine-tuning improves on the base model in most cases, but retrieval (RAG) outperforms it for knowledge injection, and fine-tuning risks catastrophic forgetting. Fine-tuning did help entity knowledge in some cases.
> - Counterpoint: **"RAG vs Fine-tuning" (Balaguer et al., 2024)** found fine-tuning can teach domain-specific skills and incorporate new knowledge (e.g., +6pp accuracy in agriculture, cumulative with RAG), suggesting fine-tuning *can* add knowledge/skills in domain-specific settings.
> 
> **Related papers:** LIMA (Zhou et al., 2023); The Unlocking Spell on Base LLMs (Lin et al., 2023); The False Promise of Imitating Proprietary LLMs (Gudibande et al., 2023); Fine-Tuning or Retrieval? (Ovadia et al., 2023); RAG vs Fine-tuning (Balaguer et al., 2024).


**community**

> ## How true is the Superficial Alignment Hypothesis?
> 
> **Partially, and mainly for perceivable aspects.** The evidence is mixed:
> 
> **Supporting evidence (style/helpfulness):**
> - **LIMA** (Zhou et al., 2023): 1,000 SFT examples suffice; results "strongly suggest that almost all knowledge in LLMs is learned during pretraining, and only limited instruction tuning data is necessary to teach models to produce high quality output."
> - **The Unlocking Spell on Base LLMs / URIAL** (Lin et al., 2023): direct token-level evidence — base and aligned models decode "nearly identically on the majority of token positions," with "most distribution shifts occurring with stylistic tokens." This strongly supports the hypothesis for the style dimension.
> 
> **Counter-evidence / limits (factuality, capabilities, knowledge):**
> - **The False Promise of Imitating Proprietary LLMs** (Gudibande et al., 2023): imitation (SFT) models are "adept at mimicking ChatGPT's style but not its factuality"; on tasks not supported by the data, fine-tuning "closes little to none of the gap." So alignment is *not* sufficient for capabilities/factuality — it only looks good on perceivable aspects.
> - **Fine-Tuning or Retrieval?** (Ovadia et al., 2023): fine-tuning did improve MMLU/current-events and entity knowledge over the base model in most cases, and "FT consistently enhances performance for entities," showing fine-tuning *can* inject some knowledge.
> - **Orca** (referenced there): vastly improved performance over base Llama via SFT on GPT-4 explanation traces.
> - **STaR** (Zelikman et al., 2022): fine-tuning on generated rationales dramatically improves reasoning, i.e., fine-tuning affects capabilities beyond format.
> - **On the Calibration of LLMs and Alignment** (Zhu et al., 2023): instruction tuning significantly *damages* calibration — alignment changes more than style.
> - **RAG vs Fine-tuning** (agriculture case study): fine-tuning teaches domain-specific skills.
> 
> ## Does SFT on a huge instruction dataset teach new knowledge?
> 
> **Not really — and where it appears to, the effect is partial.**
> - Per the hypothesis and LIMA, knowledge comes from pretraining; SFT mainly surfaces it in the right format.
> - Self-Instruct / Instruction Tuning with GPT-4 show SFT greatly improves *instruction following and zero/few-shot generalization*, not factual knowledge per se.
> - The imitation study shows that what looks like capability gain (crowdworker approval) is largely style mimicry; factuality and true capabilities remain limited by the base model.
> 
> **Conclusion:** The hypothesis is well supported for stylistic/perceivable aspects (helpfulness, format), but it does **not** uniformly hold across all aspects — factuality, reasoning, calibration, and knowledge injection are affected by (and can limit) alignment/SFT.
> 
> **Related papers:** Zhou et al. 2023 (LIMA); Lin et al. 2023 (URIAL/Unlocking Spell); Gudibande et al. 2023 (False Promise); Ovadia et al. 2023 (FT vs Retrieval); Zelikman et al. 2022 (STaR); Wang et al. 2022 (Self-Instruct); Zhu et al. 2023 (Calibration).

</details>

<a id="case-weijia_cs_1"></a>

### 7. weijia_cs_1 — 更多探索与部分新方法；评分口径疑点

**问题：** If we have a lot of specialized language models, how can we combine them to build a general system that combine the abilities of different models? Can this unified model be as good as the single large LM?

**评分：3→4（Δ+1）；rounds：3→5（Δ+2）。**

工具数 4→8；错误 0→0；文档 overview 21→82；QA tokens 35,962→186,064。

community 比 naive 多两轮，持续搜索 MoErging 和“小模型组合能否达到大模型”，并成功读取综述 ordinal 0。答案明确提到 weight-ensembling 等细节，但两者都未完整列出 Co-LLM、AdapterSoup、MixDA；两者也都用 Retro 等非模型融合路线支撑比较。judge 对这些遗漏的宽严不同。+1 与补充内容相容，但“更多轮必然更完整”不成立。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/dcf015bbb4694e77bf5650d01928ab7a.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/03164ea9b28c437cb93be43d209ab182.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] combine specialized language models into unified general system；全库 | 12 | 12 | 0 | 成功 |
| 1 | search_chunks [hybrid] unified model as good as single large language model；全库 | 12 | 9 | 0 | 成功 |
| 2 | search_chunks [hybrid] MoErging router aggregate system performance match large model；doc_ids=9f1637543171 | 1 | 0 | 0 | 成功 |
| 2 | search_chunks [hybrid] compose multiple pretrained models zero-shot exchange information new capabilities；doc_ids=57780ac505c5 | 1 | 0 | 0 | 成功 |

judge 原文：The generated answer correctly captures the core MoErging idea of recycling and routing specialized experts for improved performance/generalization, but it omits several specific MoErging methods from the gold answer (e.g., AdapterFusion, Co-LLM, AdapterSoup, MixDA, weight-ensembling) and adds other composition examples, making it accurate but not fully complete.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] combine specialized language models into general system unified model；全库 | 12 | 36 | 5 | 成功 |
| 1 | search_chunks [hybrid] can a unified model be as good as single large language model；全库 | 12 | 12 | 1 | 成功 |
| 2 | search_chunks [hybrid] combine many specialized small models to match or surpass one large model routing experts；全库 | 12 | 27 | 3 | 成功 |
| 2 | search_chunks [hybrid] unified model combining specialized abilities better than a single large language model；全库 | 12 | 4 | 1 | 成功 |
| 3 | search_chunks [hybrid] MoErging mixture of experts merged model matches or outperforms larger single model；全库 | 12 | 3 | 0 | 成功 |
| 3 | read_chunks doc_id=9f16375431710d6981fc424252909118d44f5e15f460430e4dfa29d1ebe105f7 ordinals=[0] | 1 | 0 | 0 | 成功 |
| 4 | search_chunks [hybrid] combined smaller specialized models achieve performance of much larger language model zero-shot；全库 | 12 | 0 | 0 | 成功 |
| 4 | search_chunks [hybrid] Socratic Models composing foundation models zero-shot competitive results multimodal；全库 | 12 | 0 | 0 | 成功 |

judge 原文：The generated answer accurately captures the core concept of MoErging, mentions multiple valid combining methods, and consistently affirms that such systems can match or surpass a single large LM, without contradicting the gold answer.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Based on the context:
> 
> **How to combine specialized models:** 
> - **Model MoErging**: recycle specialized expert models into an aggregate system, using a **router** that decides which expert model(s) to use for a given input (optionally with a fusion/attention module on top of independently trained adapters). This yields improved performance or generalization.
> - **Composition/prompting**: e.g., Socratic Models compose multiple pretrained models zero-shot via multimodal-informed prompting to exchange information and capture new capabilities without finetuning; ViperGPT/Visprog use a code-generation LM to compose vision-and-language models into executable programs.
> 
> **Can it match a single large LM?** Evidence suggests yes, it can be competitive:
> - MoErging aims at improved performance/generalization.
> - Socratic Models are competitive with state-of-the-art zero-shot models.
> - A retrieval-enhanced transformer (Retro) matched GPT-3 performance using 25× fewer parameters; a smaller model (Llemma-7B) with tree search reached accuracy competitive with Llemma-34B using 2× less FLOPs; scaling an LLM achieved performance comparable to GPT-4V.


**community**

> **How to combine them:** Use Model MoErging (merging/routing) methods: recycle the specialized expert models and add a router that decides which expert(s) to use for each input, or merge parameters (e.g., weight-ensembling mixture-of-experts that dynamically integrates shared and task-specific knowledge; fusion modules/attention on top of independently trained task adapters). Alternatively, compose models zero-shot via prompting (e.g., Socratic Models exchange information across models to gain new capabilities without fine-tuning).
> 
> **Can it match a single large LM?** Yes, evidence suggests combined/smaller systems can be as good as or better than a single large LM:
> - Retro matches GPT-3 on the Pile using 25× fewer parameters (via retrieval).
> - MetaICL outperforms models nearly 8× larger; STaR matches a 30× larger fine-tuned model on CommonsenseQA.
> - A smaller model with tree search matches a Llemma-34B model on MATH500 with 2× less FLOPs, and test-time compute lets a small model outperform a 14× larger one.
> - DExperts shows small expert/anti-expert LMs can steer even GPT-3 effectively.

</details>

<a id="case-weijia_cs_4"></a>

### 8. weijia_cs_4 — 社区与并行搜索共同补充 SSCD；减少错误恢复

**问题：** How to evaluate copyright infringement of image generation models?

**评分：2→4（Δ+2）；rounds：4→3（Δ-1）。**

工具数 5→4；错误 2→0；文档 overview 12→66；QA tokens 30,412→66,690。

naive 第 2 轮两次 read_chunks 均越界，随后回到已知文档定向查询，答案漏掉 SSCD。community 首轮第一个工具结果的额外 overview 已含 A Self-Supervised Descriptor for Image Copy Detection；首轮第二个独立查询也召回该文档的 chunk，最终答案明确写 SSCD。2→4 有具体证据补全，但不能把收益单独归于社区，因为并行查询同样提供了原文。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/6f4e15188a614b4aad29c0e2d4b69fc5.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/bd68ff5568254dde9a23450c5d9eb397.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] evaluate copyright infringement of image generation models；全库 | 12 | 12 | 0 | 成功 |
| 2 | read_chunks doc_id=a01d4b9b36d183c9b92fc32dda0cbeccaa006c8718ca6e70d0dc1bfe0b0953a1 ordinals=[0, 1, 2] | 0 | 0 | 0 | Unknown chunk ordinal |
| 2 | read_chunks doc_id=a0fa7ef160da07e4dda93a479fd7f65a2017e1f839efff74211dabfd3f84f0e9 ordinals=[0, 1, 2] | 0 | 0 | 0 | Unknown chunk ordinal |
| 3 | search_chunks [hybrid] copyright evaluation pipeline detection similarity generated image consistency；doc_ids=a01d4b9b36d1 | 1 | 0 | 0 | 成功 |
| 3 | search_chunks [hybrid] style attribution training data copyright evaluation method；doc_ids=a0fa7ef160da | 1 | 0 | 0 | 成功 |

judge 原文：The generated answer covers character and style similarity detection but omits the important private image detection category from the gold answers, while adding extra methods that are not part of the expected classification.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] evaluate copyright infringement of image generation models；全库 | 12 | 47 | 5 | 成功 |
| 1 | search_chunks [hybrid] copyright infringement test image generation model memorization；全库 | 12 | 8 | 1 | 成功 |
| 2 | search_chunks [hybrid] copyright infringement diffusion models evaluation pipeline similarity；全库 | 12 | 1 | 0 | 成功 |
| 2 | search_chunks [hybrid] generated image training data attribution detection copy；全库 | 12 | 10 | 1 | 成功 |

judge 原文：The generated answer accurately captures the core methods from the gold answers—copyrighted character detection, private image detection via SSCD, and style similarity via style descriptors—while adding relevant, non-contradictory context.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Based on the context, copyright infringement of image generation models can be evaluated by:
> 
> 1. **Detection of similarity to copyrighted content**: Run a database search to determine whether properties of the generated image are attributable to specific training data (e.g., extracting style descriptors to attribute a generated image's style to training images; evaluating similarity to copyrighted characters).
> 
> 2. **Consistency with user input**: Check whether the generated image matches the user's prompt (as in the COPYCAT evaluation pipeline, which considers both similarity detection and prompt-consistency).
> 
> 3. **Membership/provenance detection**: Use data watermarks or membership inference to determine whether copyrighted works were used in model training, framed as hypothesis testing with guarantees on false detection rate (e.g., black-box detection with watermarked training data).
> 
> COPYCAT evaluation showed models can generate copyrighted characters even when names aren't explicitly mentioned (e.g., "videogame, plumber" generates Mario), indicating the need for such systematic evaluation.


**community**

> Based on the context, copyright infringement of image generation models can be evaluated by:
> 
> 1. **Detecting similarity to copyrighted content** — e.g., the COPYCAT evaluation suite detects similarity of generated images to copyrighted characters and checks consistency with the user input, showing models can reproduce copyrighted characters even without explicit names in prompts.
> 
> 2. **Attributing generated images to training data** — performing database searches to determine whether image properties are attributable to specific training data; e.g., extracting style descriptors to attribute the style of a generated image to images in the model's training set, or using image copy detection (e.g., SSCD descriptors).
> 
> 3. **Membership inference** — determining whether a given image was in the model's training data (e.g., SecMI for diffusion models, which infers membership via step-wise error comparison).
> 
> 4. **Watermarking / data recording** — using data watermarks or recorded training data artifacts (e.g., Data Portraits) to detect whether copyrighted works were used in pretraining, with guarantees on false detection rates.

</details>

<a id="case-weijia_cs_6"></a>

### 9. weijia_cs_6 — 社区补齐架构类别；仍有分类错误

**问题：** What are the common model architectures for retrieval-augmented language models?

**评分：2→3（Δ+1）；rounds：2→2（Δ+0）。**

工具数 2→1；错误 0→0；文档 overview 15→22；QA tokens 17,379→14,776。

community 首轮额外 overview 包含 kNN-LM 的线性插值方案，naive 所有返回上下文未出现 kNN；最终答案从两个大类扩展到 kNN、Self-RAG 和 retrieve-then-read 等。Self-RAG 实际已在 naive chunk 中，说明一部分提升是已有证据利用得更充分。两者仍把 REALM 归到 cross-attention，因此 community 只升到 3 分。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/1df61a4ea14c4cf7ba9d51d12cb1cafe.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/dec0e0592f46410499c5db0380694295.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] retrieval-augmented language model architectures；全库 | 12 | 12 | 0 | 成功 |
| 1 | search_chunks [vector] RAG model architecture encoder decoder；全库 | 12 | 3 | 0 | 成功 |

judge 原文：The generated answer correctly identifies retrieval-in-context and attention-modification architectures, but misclassifies REALM (which is not cross-attention based) and omits important architectures such as kNN-LM and advanced techniques like self-RAG and query rewriting.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] model architectures retrieval-augmented language models；全库 | 12 | 22 | 4 | 成功 |

judge 原文：The generated answer correctly covers the major RALM architectures (in-context prepending, kNN-LM, RETRO-style cross-attention, Self-RAG, and retrieve-then-read/query rewriting), but it slightly misclassifies REALM as cross-attention-based rather than a retrieval-in-context model, a minor imprecision that prevents a perfect score.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Based on the context, the two common model architectures for retrieval-augmented language models are:
> 
> 1. **Cross-attention based architectures**: LMs modified with special cross-attention mechanisms to encode retrieved text (e.g., REALM, Retro, which uses chunked cross-attention).
> 
> 2. **In-context prepending architectures**: The LM architecture is left unchanged (frozen/black-box), and retrieved documents are simply prepended to the input (e.g., REPLUG, In-Context RALM).


**community**

> Based on the context, common RALM architectures include:
> 
> 1. **Cross-attention-based**: Language models trained with special cross-attention mechanisms to encode retrieved text (e.g., REALM; Retro, which uses a frozen BERT retriever, a differentiable encoder, and chunked cross-attention).
> 
> 2. **Black-box/in-context prepending**: Frozen LMs that simply prepend retrieved documents to the input, leaving the architecture unchanged (e.g., REPLUG, In-Context RALM).
> 
> 3. **kNN-based**: Pre-trained LMs linearly interpolated with a k-nearest-neighbors model (kNN-LM).
> 
> 4. **Self-reflective/adaptive**: A single LM trained to adaptively retrieve on demand and generate/critique using reflection tokens (Self-RAG).
> 
> 5. **Pipeline/retrieve-then-read**: Frameworks that combine a retriever with a black-box reader LM (e.g., retrieve-then-read, Rewrite-Retrieve-Read, RA-DIT dual instruction tuning).

</details>

<a id="case-weijia_cs_8"></a>

### 10. weijia_cs_8 — 强评分一致性疑点

**问题：** Can you explain to me what is Visual programming?

**评分：2→4（Δ+2）；rounds：2→2（Δ+0）。**

工具数 1→1；错误 0→0；文档 overview 12→41；QA tokens 10,490→19,437。

两者都只做一次搜索、两轮结束；答案实质相同，均围绕 Visprog 的 Python-like 模块程序、视觉工具和中间输出展开，均未扩展 ViperGPT/Socratic Models。naive 的 judge 以将大概念等同 Visprog/遗漏其他框架判 2，community 的 judge 则认为抓住核心即可判 4。上下文确实更多，但最终答案没有与 +2 对应的明显事实新增；这是最强的判分不一致候选之一。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/05a66ab5ce10444d81b51f6efdae2d8d.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/366783f76d5b4cae82bcaf5f6f130954.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] What is visual programming?；全库 | 12 | 12 | 0 | 成功 |

judge 原文：The generated answer accurately describes VisProg's mechanism but incorrectly equates Visual Programming with VisProg, omitting the broader concept and other frameworks such as ViperGPT and Socratic Models, making it only partially correct.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] Visual programming；全库 | 12 | 41 | 4 | 成功 |

judge 原文：The generated answer accurately captures the core meaning of visual programming as decomposing vision tasks into modular code invoking vision tools, consistent with the gold answers, with additional relevant details that do not contradict them.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Based on the context, "Visual Programming" refers to **Visprog**, a neuro-symbolic approach for solving complex, compositional visual tasks given natural language instructions. It avoids task-specific training by using the in-context learning ability of large language models to generate Python-like modular programs, which are then executed to produce both the solution and an interpretable rationale. Each line of the generated program can invoke off-the-shelf computer vision models, image processing subroutines, or Python functions, with intermediate outputs consumed by later parts of the program. It was demonstrated on tasks such as compositional visual question answering, zero-shot reasoning on image pairs, factual knowledge object tagging, and language-guided image editing.


**community**

> Based on the context, Visual Programming (Visprog) is a neuro-symbolic approach to solving complex and compositional visual tasks given natural language instructions. It avoids the need for any task-specific training. Instead, it uses the in-context learning ability of large language models to generate Python-like modular programs, which are then executed to get both the solution and a comprehensive, interpretable rationale. Each line of the generated program may invoke one of several off-the-shelf computer vision models, image processing subroutines, or Python functions to produce intermediate outputs consumed by later parts of the program. It has been demonstrated on tasks like compositional visual question answering, zero-shot reasoning on image pairs, factual knowledge object tagging, and language-guided image editing.

</details>

<a id="case-weijia_cs_9"></a>

### 11. weijia_cs_9 — 越界读取造成额外轮次；评分口径疑点

**问题：** How should we analyze the training dynamics of language models?

**评分：2→3（Δ+1）；rounds：2→4（Δ+2）。**

工具数 1→4；错误 0→2；文档 overview 12→49；QA tokens 10,950→61,720。

community 第 2 轮两次 read_chunks 均越界，第 3 轮再搜索；naive 一轮工具后就回答。两者最终都围绕 checkpoints/perplexity/memorization，community 甚至没保留 naive 已写出的“大模型记忆更快”等细节。两次 judge 的扣分理由从“缺 end-task/QA-infused pretraining”换成“缺 repetition/model-size details”。2→3 不能解释为多两轮带来明确新答案要点。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/501e9adc92064985961e384c20f01d53.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/0dacdfd514864e299cd712320237b240.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] how to analyze training dynamics of language models；全库 | 12 | 12 | 0 | 成功 |

judge 原文：The generated answer correctly captures memorization and perplexity prediction aspects from the gold answer, but omits the end-task aware pre-training and QA-infused pre-training approaches, making it only partially complete.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] analyze training dynamics of language models；全库 | 12 | 38 | 5 | 成功 |
| 2 | read_chunks doc_id=8b8492ce0e617451b647d0da51f3e52c33e393bf6bb8cc66bc9a8af869714c2f ordinals=[1, 2, 3] | 0 | 0 | 0 | Unknown chunk ordinal |
| 2 | read_chunks doc_id=648990985a8600b5f71ecae2b8d29cf6c5ae7da67f79267abcd53a554d47f836 ordinals=[1, 2] | 0 | 0 | 0 | Unknown chunk ordinal |
| 3 | search_chunks [hybrid] analyzing training dynamics method checkpoints memorization perplexity loss reduction；全库 | 12 | 11 | 1 | 成功 |

judge 原文：The generated answer correctly captures key aspects such as memorization dynamics and perplexity as a predictor, but it omits specific details like data repetition frequency, the finding that bigger models memorize faster but overfit less, and the 'better than other factors' comparison, making it good but not a perfect match to any single gold answer.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Based on the context, analyze training dynamics by:
> 
> - Examining **intermediate training checkpoints** of models at different scales (e.g., 125M to 175B), evaluating them on next-token prediction, sequence-level generation, and downstream tasks; track which tokens see loss reduction, stagnation, or double-descent behavior, and use **perplexity** as a strong predictor of behaviors like in-context learning.
> - Measuring **memorization dynamics** across dataset size, learning rate, and model size (larger models memorize faster, memorize more before overfitting, and forget less), and analyzing what gets memorized first (e.g., nouns and numbers).


**community**

> Based on the context, training dynamics of language models should be analyzed by:
> 
> - Examining **intermediate training checkpoints** of models at different scales (e.g., 125M to 175B parameters), evaluating them on next-token prediction, sequence-level generation, and downstream tasks (e.g., in-context learning on BIG-Bench).
> - Tracking **perplexity and per-token loss reduction** over training, e.g., which training tokens see the most significant loss reduction, stagnation, or double-descent behavior, and using perplexity as a predictor of behavior.
> - Measuring **memorization dynamics** across training, varying dataset size, learning rate, and model size, and analyzing which content (e.g., parts of speech like nouns and numbers) is memorized first.

</details>

<a id="case-jacqueline_cs_3"></a>

### 12. jacqueline_cs_3 — 最终综合丢失适用边界

**问题：** In knowledge distillation, the teacher model is typically a larger (more powerful) network than the student model. Has there been work showing that the teacher model is size-matched or smaller (but perhaps more targeted in knowledge) than the student model, and for knowledge transfer to still be effective?

**评分：4→3（Δ-1）；rounds：2→2（Δ+0）。**

工具数 2→2；错误 0→0；文档 overview 10→21；QA tokens 15,940→19,175。

两者两轮结束，均召回弱教师蒸馏材料。naive 明确说 NLP 中极弱教师可能损害学生，community 省略这一 caveat，以 remains effective 收尾。judge 的实际理由是 community 对 vision pre-training 表述过宽；naive 也提 vision，因此评分尺度仍有疑点。但漏掉领域/强弱边界是可直接比较到的答案质量变化，不能只看社区覆盖数量。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/16b25a4db5164936b338256c30235f61.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/afad8355ee7c4022a4fbc4c1f35cad0d.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] knowledge distillation teacher model smaller than student model；全库 | 12 | 9 | 0 | 成功 |
| 1 | search_chunks [hybrid] teacher network size-matched or smaller but more targeted knowledge transfer effective；全库 | 12 | 1 | 0 | 成功 |

judge 原文：The generated answer accurately captures the core finding that weaker/smaller teachers can effectively transfer knowledge in knowledge distillation, including the DWT method and the NLP-specific caveat that extremely weak teachers can harm performance.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] knowledge distillation teacher smaller than student model；全库 | 12 | 19 | 2 | 成功 |
| 1 | search_chunks [hybrid] teacher size-matched or smaller but more targeted knowledge transfer effective；全库 | 12 | 2 | 0 | 成功 |

judge 原文：The answer correctly captures the key finding that weaker/smaller teachers can effectively transfer knowledge to larger students and cites relevant work, but slightly overstates by claiming effectiveness in vision pre-training when the gold answers focus on NLP.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Yes. The paper "A Study on Knowledge Distillation from Weak Teacher for Scaling Up Pre-trained Language Models" describes Distillation from Weak Teacher (DWT), which transfers knowledge from a smaller, weaker teacher model to a larger student model to improve its performance. Prior studies show DWT is effective in the vision domain and in NLP pre-training (e.g., enhancing newer/larger models using older or smaller pretrained models). Relatedly, Yuan et al. (2020) found that poorly-trained teachers can still enhance students, and even an extremely weak teacher improves performance in the vision domain. Caveat: in NLP pre-training, an extremely weak teacher can harm student quality, unlike in vision.


**community**

> Yes. The "Distillation from Weak Teacher (DWT)" work transfers knowledge from a smaller, weaker teacher model to a larger student model to improve its performance, and has been shown effective in vision and NLP pre-training. Related work on "Revisiting Knowledge Distillation via Label Smoothing Regularization" also shows that weak students can improve teachers and poorly-trained (worse-performing) teachers can still remarkably enhance students, reinterpreting distillation as regularization. So knowledge transfer remains effective even when the teacher is smaller or weaker than the student.

</details>

<a id="case-jacqueline_cs_4"></a>

### 13. jacqueline_cs_4 — 强评分一致性疑点

**问题：** Data selection has emerged as an important problem for training good language models (i.e., which datapoints to include). Has there been any research on the ordering of datapoints for LMs (i.e., easy to hard curriculum sequence of data points), such that a LM may be trained in a more sample-efficient manner?

**评分：4→3（Δ-1）；rounds：2→2（Δ+0）。**

工具数 2→2；错误 0→0；文档 overview 17→48；QA tokens 17,109→26,504。

两者两轮结束，均解释 Bengio curriculum 和 Skill-it 的 1B vs 3B tokens 结果，均未列出 Orca。community 的 judge 因未写 Orca 给 3，naive 对同一遗漏给 4。community 有更多 overview，并未转化为答案的新覆盖；分差主要值得从评测一致性复核，不能据此断言社区检索降质。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/e5cff458a404418f8893ff2bf20d6d1d.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/17acb27efefd4c6eafcea8600b0e48ef.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] ordering of datapoints curriculum easy to hard sample-efficient language model training；全库 | 12 | 11 | 0 | 成功 |
| 1 | search_chunks [vector] curriculum learning order training data language models；全库 | 12 | 6 | 0 | 成功 |

judge 原文：The generated answer accurately captures the core meaning and key facts of the gold answer by identifying curriculum learning and Skill-it as evidence of data ordering research, with additional correct details that do not contradict the gold answer.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] ordering of datapoints curriculum learning easy to hard language model training sample efficient；全库 | 12 | 40 | 4 | 成功 |
| 1 | search_chunks [hybrid] curriculum learning language model training sample efficiency；全库 | 12 | 8 | 2 | 成功 |

judge 原文：The answer correctly identifies curriculum learning and Skill-it with accurate details, but it omits the Orca example, making it slightly incomplete relative to the gold answer.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Yes. Two relevant lines of research exist in the context:
> 
> 1. **Curriculum Learning (Bengio et al., 2009)**: formalized training on examples organized in a meaningful order (gradually more complex, easy-to-hard), showing faster convergence, better local minima, and improved generalization—a continuation-method view of training.
> 
> 2. **Skill-it! (Chen et al., 2023)**: specifically for LMs, formalizes "ordered skill sets" with prerequisite skills, showing skills are learned more efficiently when trained on a mixture with prerequisite skills. Its online sampling algorithm, SKILL-IT, is more sample-efficient: a 3B-parameter LM continually pre-trained on RedPajama achieved higher accuracy with 1B tokens than uniform sampling with 3B tokens.
> 
> So yes, research on easy-to-hard/curriculum ordering exists and demonstrates more sample-efficient LM training (e.g., via ordered skills and prerequisites rather than strictly easy-first sequences).


**community**

> Yes. Two relevant lines of research exist in the provided context:
> 
> 1. **Curriculum Learning (Bengio et al., 2009)** formalized organizing examples in a meaningful order that gradually introduces more complex ones, showing improved generalization and faster convergence in deep networks—though this was for general machine learning, not specifically LMs.
> 
> 2. **Skill-it! (Chen et al., 2023)** directly addresses ordering for language models: it shows that ordered skill sets (with prerequisite-skill orderings) characterize LM training and provide a mechanism for **data-efficient training**. Their SKILL-IT algorithm trains a 3B model on RedPajama with only 1B tokens so it outperforms uniform sampling with 3B tokens on LM Evaluation Harness—demonstrating sample-efficient training via ordered data.
> 
> So yes, research exists showing datapoint ordering/curricula can make LM training more sample-efficient.

</details>

<a id="case-shengyan_photonics_3"></a>

### 14. shengyan_photonics_3 — 新查询拓宽领域，再由社区补全类别

**问题：** What are the large systems in which quantum effects have been successfully demonstrated?

**评分：2→4（Δ+2）；rounds：2→3（Δ+1）。**

工具数 1→3；错误 0→0；文档 overview 11→35；QA tokens 10,892→43,852。

首个查询及有序 chunk IDs 完全一致，naive 只回答机械振子。community 多一轮检索 cold atoms/molecules/superfluids，召回 C60、25 kDa 分子等 chunk，并扩展出涵盖超流、BEC 的社区及成员 overview；最终答案覆盖机械、分子、超导电路、BEC、液氦等。2→4 有清晰内容增量；额外 query 与社区扩展共同作用，不能全部归给首轮社区。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/89a34f49d39243efb62c5ef762a285cb.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/839b916954d142f59d3b3b6d94cf40d3.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] large systems quantum effects successfully demonstrated；全库 | 12 | 11 | 0 | 成功 |

judge 原文：The generated answer correctly captures mechanical resonators as a macroscopic system, but omits other key systems from the gold answers such as matter-wave interference of C60 molecules, superfluids, Josephson effect, and Bose-Einstein condensates, making it only partially complete.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] large systems quantum effects successfully demonstrated；全库 | 12 | 22 | 3 | 成功 |
| 2 | search_chunks [hybrid] quantum effects demonstrated macroscopic large systems cold atoms molecules superfluids；全库 | 12 | 13 | 2 | 成功 |
| 2 | search_chunks [hybrid] largest systems quantum superposition ever demonstrated；全库 | 12 | 0 | 0 | 成功 |

judge 原文：The generated answer accurately captures all the key macroscopic quantum systems mentioned in the gold answers, including C60 and >25 kDa molecule interference, mechanical resonators and entanglement, superfluids, Josephson junctions, and Bose-Einstein condensates, with additional correct examples that do not contradict the gold standard.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Quantum effects have been successfully demonstrated in large mechanical systems, including: a macroscale surface acoustic-wave mechanical resonator (full quantum control and non-classical phonon states), two macroscopic mechanical drumheads with masses of 70 picograms (deterministic entanglement), a microwave-frequency "quantum drum" mechanical resonator (cooled to its quantum ground state with single-phonon control), and two remote micromechanical oscillators (entangled across a 20 cm separation).


**community**

> Based on the context, quantum effects have been successfully demonstrated in the following large/macroscopic systems:
> 
> - **Macroscale mechanical resonators** — e.g., a surface acoustic-wave (SAW) resonator, a ~6 GHz "quantum drum," and nanomechanical/micromechanical oscillators (cooled to quantum ground state, single-phonon control, non-classical states)
> - **Macroscopic mechanical drumheads** (70 picograms) — deterministic entanglement
> - **A 16-microgram solid-state mechanical resonator** — Schrödinger cat states
> - **Molecules beyond 25 kDa** (up to ~2,000 atoms) and **C60 molecules** — matter-wave interference (quantum superposition)
> - **Optically levitated nanoparticles** (femtogram) in cryogenic free space — quantum control
> - **Superconducting circuits** (Josephson phase qubits) — Bell inequality violation in a macroscopic electrical circuit
> - **Bose–Einstein condensates** of dilute atomic vapor (rubidium-87)
> - **Liquid helium** — superfluidity below the λ-point

</details>

<a id="case-shengyan_photonics_4"></a>

### 15. shengyan_photonics_4 — 已有证据利用改善；查询与判分也有差异

**问题：** What progress has been made in trapping and controlling multiple nanoparticles?

**评分：3→4（Δ+1）；rounds：2→2（Δ+0）。**

工具数 1→2；错误 0→0；文档 overview 10→34；QA tokens 10,297→22,768。

community 同一工具轮发两路查询，naive 只有一路，最终明确补出 nanodumbbell 和独立操控细节。nanodumbbell 已在 naive 原始 chunk 和 overview 中，故这不是该事实首次被社区召回，而是综合时被采用。judge 对两者都写的 4×4 也采取了不同评价；+1 有真实表述增量，但纯社区贡献无法分离。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/084381f8295d47d1be83580ab2f5ef2e.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/0d1a1789d29d40998e4fae6f499ab5a5.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] trapping and controlling multiple nanoparticles progress；全库 | 12 | 10 | 0 | 成功 |

judge 原文：The generated answer accurately captures several key advances such as AOD-based trapping, cooling, and tunable interactions, but omits the optical-binding method and the nanodumbbell demonstration, and adds an unsupported 4×4 detail, making it mostly correct but not fully complete.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] trapping and controlling multiple nanoparticles；全库 | 12 | 31 | 4 | 成功 |
| 1 | search_chunks [vector] multiple particle trapping control arrays optical tweezers；全库 | 12 | 3 | 0 | 成功 |

judge 原文：The generated answer accurately captures the key progress described in the gold answer—trapping multiple nanoparticles, independent control, feedback cooling, controlled interactions, and nanodumbbell assembly—while adding consistent supporting detail, so it fully matches the gold standard.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Progress includes: forming 2D arrays of optically levitated nanoparticles in vacuum (e.g., 3×3 and 4×4 arrays) with on-demand rearrangement into arbitrary defect-free patterns; scalable trapping of multiple particles with independently controllable trap position and frequency via AOD-generated tweezers; simultaneous cooling of multiple particles using all-optical cold damping; and tunable light-induced dipole-dipole interactions between particles, enabling control of coupling rates and a route to programmable many-body systems.


**community**

> Progress includes:
> 
> - **Trapping multiple nanoparticles in arrays**: 2D arrays of optically levitated nanoparticles (e.g., 3×3 and 4×4) were created with optical tweezers; initial loading is probabilistic but an auxiliary laser enables on-demand rearrangement into arbitrary, defect-free patterns, plus individual characterization of each particle (e.g., shape) and assembly of nanodumbbells from two particles.
> 
> - **Independent control and cooling**: Programmable arrays generated by rf-driven acousto-optic deflectors allow independent control of trap position and frequency of each particle; a scalable all-optical linear feedback cooling scheme simultaneously cools the center-of-mass motion of multiple (e.g., a pair of) particles.
> 
> - **Controlling interactions**: Tunable light-induced dipole-dipole interactions couple nanoparticles, with full control over conservative and nonconservative coupling rates (e.g., via trap separation and optical phase), enabling switching of optical coupling and observation of electrostatic coupling—a route to programmable many-body systems with tunable nonreciprocal interactions.

</details>

<a id="case-shengyan_photonics_8"></a>

### 16. shengyan_photonics_8 — 扩展覆盖测量类型，但精度/对象限定仍不足

**问题：** What physical quantities can be precisely measured using a levitated nanosphere?

**评分：2→3（Δ+1）；rounds：2→2（Δ+0）。**

工具数 1→2；错误 0→0；文档 overview 11→27；QA tokens 11,040→20,864。

community 答案增加 acceleration、magnetic field 和 displacement，首轮额外 overview 已含 levitated accelerometer，另一独立查询也召回其 chunk。naive 的上下文虽提 magnetic field，但未必是磁场传感器的直接证据，最终答案只列力、力矩、电场。judge 因范围更完整升分，但对数值仍保留扣分。应区分不同粒子/平台，不能把所有悬浮体系的能力无条件移植给 nanosphere。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/092273bcaba84d44a989b08969aa3ccb.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/420fa9cd740742f59924ca914e3ed553.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] levitated nanosphere precisely measure physical quantities；全库 | 12 | 11 | 0 | 成功 |

judge 原文：The generated answer correctly identifies force, torque, and electric field, but omits the magnetic field measurement capability, which is an important key fact in the gold answers.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] physical quantities precisely measured levitated nanosphere；全库 | 12 | 27 | 4 | 成功 |
| 1 | search_chunks [hybrid] levitated nanoparticle measurement force acceleration torque；全库 | 12 | 0 | 0 | 成功 |

judge 原文：The generated answer correctly identifies the main measurable quantities (force, torque, electric/magnetic fields), but some numeric precision values differ from the gold answers, so it is not a perfect match.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Based on the context, a levitated nanosphere can precisely measure:
> - **Force** (force detection sensitivity ~zN/Hz¹ᐟ² and resolution of ~yN)
> - **Torque** (torque sensitivity ~10⁻²⁷ N·m/Hz¹ᐟ² and light-induced torque)
> - **Electric field** (three-dimensional electric field sensing with a net-charged nanoparticle)
> 
> Additionally, it can precisely characterize center-of-mass/torsional motion and temperature of the particle.


**community**

> Based on the context, physical quantities that can be precisely measured using a levitated nanosphere (nanoparticle) include:
> 
> - **Force** – yoctonewton-level force detection (sensitivity ~6.33 zN/Hz^1/2, resolution ~166 yN)
> - **Torque** – ultrasensitive torque detection (down to ~10⁻²⁷ N·m/Hz^1/2)
> - **Electric field** – 3D high-sensitivity electric field measurement (~1 μV/cm/Hz^1/2)
> - **Acceleration** – levitated optomechanical accelerometer (sensitivity ~25.5 μg/Hz^1/2)
> - **Magnetic field** – levitated magnetometer with energy resolution below ℏ
> - **Displacement** – sensitive displacement detection of the levitated particle

</details>

<a id="case-shengyan_photonics_10"></a>

### 17. shengyan_photonics_10 — 提前结束；强评分一致性疑点

**问题：** What are some ways to overcome the heating issue due to residual optical absorption in the a levitated nanoparticle?

**评分：4→2（Δ-2）；rounds：3→2（Δ-1）。**

工具数 4→2；错误 1→0；文档 overview 17→29；QA tokens 38,286→22,514。

首个查询和有序 chunk IDs 一致，naive 再搜索 core-shell/doughnut 并有一次越界读取；community 首轮两路搜索后结束。两份答案均写 doughnut+core-shell、低温，均未写 gold 的电势阱。naive judge 把 doughnut 与 core-shell 当成两个核心方案而给 4，community judge 正确指出另一关键方案电势阱缺失而给 2。该 −2 不能作为社区导致遗漏电阱的证据，因为遗漏在两边都存在。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/bbe79501a3df4c819dea1afe548caea4.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/6f79a23f6c154348a50d063800587706.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] overcome heating residual optical absorption levitated nanoparticle；全库 | 12 | 11 | 0 | 成功 |
| 1 | search_chunks [vector] optical absorption heating nanoparticle feedback cooling；全库 | 12 | 4 | 0 | 成功 |
| 2 | search_chunks [hybrid] core-shell structure doughnut beam reduce light absorption heating levitated particle；全库 | 12 | 2 | 0 | 成功 |
| 2 | read_chunks doc_id=30f9aa2e967451f7f7936aa9743654fa4d87de77e57582f77f25f94f6cc66009 ordinals=[0, 1] | 0 | 0 | 0 | Unknown chunk ordinal |

judge 原文：The generated answer accurately captures both gold-standard approaches (doughnut beams and core-shell nanoparticles) and adds extra consistent methods without contradicting the gold answer.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] overcome heating residual optical absorption levitated nanoparticle；全库 | 12 | 28 | 4 | 成功 |
| 1 | search_chunks [hybrid] residual absorption heating optical trap nanoparticle cooling；全库 | 12 | 1 | 0 | 成功 |

judge 原文：The generated answer correctly identifies the donut beam/core-shell nanoparticle approach but omits the key second approach of using electrically-based potential traps, making it incomplete.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Ways to overcome the heating issue from residual optical absorption:
> 
> 1. Levitate the particle in doughnut-shaped beams instead of Gaussian beams to suppress light absorption—this shows excellent tolerance of heat absorption while keeping a high mechanical quality factor.
> 2. Design a core-shell structure for the (strongly absorptive) particle to reduce heating.
> 3. Operate in cryogenic free space to suppress thermal effects.
> 4. Use cooling techniques such as cavity cooling by coherent scattering or all-optical feedback (cold damping/parametric) cooling.


**community**

> Based on the context, ways to overcome the heating issue from residual optical absorption include:
> 
> - Designing the particle with a core-shell structure and trapping it in doughnut-shaped beams, which show excellent tolerance to heat absorption and preserve the mechanical quality factor.
> - Levitating the particle in cryogenic free space, which suppresses thermal effects sufficiently.
> - Detuning the trapping/probe light away from absorption resonances and reducing input power to limit temperature rise.

</details>

<a id="case-minyang_physics_3"></a>

### 18. minyang_physics_3 — 显著减少重复探索；降分因果不清

**问题：** What astrophysical phenomena and physics theories can be found by the multi-messenger astrophysics (MMA) approach?

**评分：4→3（Δ-1）；rounds：7→2（Δ-5）。**

工具数 12→2；错误 3→0；文档 overview 21→17；QA tokens 210,313→20,010。

首个查询和有序 chunk IDs 一致；naive 用 7 轮、12 次工具调用，多次围绕同一 MMA 文档搜索，累计 3 次工具错误；community 两个首轮查询后在第 2 轮回答。最终 community 的现象/理论列表反而更长。judge 扣 NSBH、eccentric binaries、TDE 等，而 naive 也没有列出这些，所以 −1 不能直接解释成“少查五轮丢失关键内容”；额外内容更杂可能影响判分，但 trace 不能确认评分器内部原因。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/326469e02ff9409c9443f77a65e24935.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/db445d9ad5b74a49a20bc2c4e02e91ee.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] multi-messenger astrophysics phenomena physics theories；全库 | 12 | 10 | 0 | 成功 |
| 1 | search_chunks [vector] multi-messenger astrophysics gravitational waves neutrinos cosmic rays；全库 | 12 | 2 | 0 | 成功 |
| 2 | read_chunks doc_id=f251c4e5191d4fc447e388fc0a2faa10b37dcf1143fa1ab8a6579c69623cdbd0 ordinals=[0, 1, 2, 3, 4, 5] | 0 | 0 | 0 | Unknown chunk ordinal |
| 2 | search_chunks [hybrid] multi-messenger probes general relativity nuclear equation of state cosmic rays ultra-high energy origin；全库 | 12 | 4 | 0 | 成功 |
| 3 | search_chunks [hybrid] probes theories general relativity equation of state cosmic accelerators；doc_ids=f251c4e5191d | 1 | 0 | 0 | 成功 |
| 3 | search_chunks [hybrid] astrophysical phenomena binary neutron star kilonova gamma-ray burst supernova；doc_ids=f251c4e5191d | 1 | 0 | 0 | 成功 |
| 4 | search_chunks [vector] multi-messenger approach probes compact object mergers cosmic rays GRB origins fundamental physics；全库 | 12 | 0 | 0 | 成功 |
| 4 | search_chunks [vector] multi-messenger astrophysics science questions dark matter equation of state nucleosynthesis test general relativity；全库 | 12 | 0 | 0 | 成功 |
| 5 | read_chunks doc_id=f251c4e5191d4fc447e388fc0a2faa10b37dcf1143fa1ab8a6579c69623cdbd0 ordinals=[1] | 0 | 0 | 0 | Unknown chunk ordinal |
| 5 | search_chunks [keyword] multi-messenger astrophysics overview probes gamma-ray bursts origin cosmic rays neutrinos gravitational waves science；全库 | 12 | 4 | 0 | 成功 |
| 6 | search_chunks [hybrid] "multi-messenger" probes of equation of state, cosmic ray acceleration, GRB central engines, fundamental physics tests；全库 | 12 | 1 | 0 | 成功 |
| 6 | read_chunks doc_id=['dfd650560775b90a2fc8b7f77ddf2988d69003b83f8a49074476f5ce21be0d88'] ordinals=[1, 2, 3] | 0 | 0 | 0 | 参数 schema 错误 |

judge 原文：The generated answer accurately captures the key astrophysical phenomena and correctly identifies general relativity, with additional context that does not contradict the gold answers.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] multi-messenger astrophysics phenomena physics theories；全库 | 12 | 17 | 2 | 成功 |
| 1 | search_chunks [hybrid] MMA multi-messenger astronomy discoveries neutron star merger gravitational waves neutrinos；全库 | 12 | 0 | 0 | 成功 |

judge 原文：The generated answer correctly captures many key MMA phenomena and theories, but it omits some gold-answer examples (e.g., NSBH mergers, eccentric binary coalescences, TDEs) and includes some speculative/extra content, making it good but not perfect.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Based on the provided context, the MMA approach reveals the following:
> 
> **Astrophysical phenomena:**
> - Gamma-ray bursts (GRBs) and short GRBs (e.g., GRB 170817A)
> - Active galactic nuclei (AGNs) including blazars (e.g., TXS 0506+056 as a high-energy neutrino source)
> - Supernovae
> - Binary black hole mergers (e.g., GW150914) and binary neutron star mergers (e.g., GW170817)
> - Kilonovae (optical/IR transients from r-process nucleosynthesis in merger ejecta)
> - High-energy cosmic neutrinos (e.g., IceCube-170922A) and diffuse cosmic gamma-ray background
> - Diffuse flux of high-energy cosmic neutrinos (origins unidentified)
> 
> **Physics theories:**
> - General relativity: GW150914's waveform matched the predictions of general relativity for the inspiral, merger, and ringdown of black holes
> - Dark matter properties: black hole and neutron star mergers could provide unique insight into the nature of dark matter, including WIMP and axion candidates in extensions of the Standard Model


**community**

> Based on the context, the multi-messenger astrophysics (MMA) approach finds/studies:
> 
> **Astrophysical phenomena:**
> - Gamma-ray bursts (GRBs), including short GRBs (e.g., GRB 170817A)
> - Active galactic nuclei (AGNs) and blazars (e.g., TXS 0506+056)
> - Supernovae
> - Binary black hole mergers (GW150914, GWTC-1 events)
> - Binary neutron star mergers (GW170817)
> - Kilonovae (e.g., AT 2017gfo/SSS17a), powered by r-process nucleosynthesis in merger ejecta
> - High-energy astrophysical neutrinos (e.g., IceCube-170922A) and their sources
> - Diffuse cosmic gamma-ray background
> - Quark stars, black holes, and exotic compact objects (as possibilities)
> 
> **Physics theories:**
> - General relativity (waveforms matching GR predictions for inspiral, merger, and ringdown)
> - Post-Newtonian approximation and effective one-body approach for relativistic two-body dynamics
> - Numerical relativity and phenomenological/numerical-relativity surrogate waveform models
> - r-process (rapid neutron-capture) nucleosynthesis
> - Dark matter physics (WIMPs, axions, strong CP problem in QCD, Standard Model extensions)
> - Strong equivalence principle (for compact binaries)

</details>

<a id="case-minyang_physics_5"></a>

### 19. minyang_physics_5 — 定向查询避免失败读取；评分口径疑点

**问题：** How to realize Topology Optimization of Cavity-Based Second Harmonic Generation?

**评分：3→4（Δ+1）；rounds：4→3（Δ-1）。**

工具数 5→2；错误 2→0；文档 overview 12→28；QA tokens 30,325→31,162。

首个查询和 chunk 排序一致。naive 第 2 轮两次越界试读、第 3 轮分文档搜索；community 第 2 轮用一个 doc_ids 列表直接检索两篇文档。两份最终答案都强调非线性重叠积分及 Q₁²Q₂|β|²，均没写 adjoint method。naive 被扣 LDOS/adjoint，community 被判核心正确；轮次节省有直接工具证据，+1 的答案增益则不清晰。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/f37b70927eba4210a40df996170640f1.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/4ed8bb0ba5314d29bdfee2092092e14e.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] Topology Optimization of Cavity-Based Second Harmonic Generation；全库 | 12 | 12 | 0 | 成功 |
| 2 | read_chunks doc_id=212caf9309e29d226860c127a4b0eafe8250612f8e64d94b300ef60322067c1d ordinals=[0, 1, 2, 3] | 0 | 0 | 0 | Unknown chunk ordinal |
| 2 | read_chunks doc_id=e819b9297eb9a6b9d3ca89feb2033930658e57ecd78af33c5fa5f5dd43448ef7 ordinals=[0, 1] | 0 | 0 | 0 | Unknown chunk ordinal |
| 3 | search_chunks [hybrid] topology optimization SHG overlap integral nonlinear coupling enhancement factor；doc_ids=212caf9309e2 | 1 | 0 | 0 | 成功 |
| 3 | search_chunks [hybrid] SHG optimization objective overlap integral LDOS fundamental harmonic；doc_ids=e819b9297eb9 | 1 | 0 | 0 | 成功 |

judge 原文：The generated answer correctly identifies the topology optimization of nonlinear overlap and SHG enhancement, but it slightly misrepresents the role of LDOS by saying it should not be maximized and omits the adjoint-variable gradient method mentioned in the gold answer.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] Topology Optimization of Cavity-Based Second Harmonic Generation；全库 | 12 | 28 | 4 | 成功 |
| 2 | search_chunks [hybrid] overlap integral beta SHG objective frequency matching optimization；doc_ids=212caf9309e2,e819b9297eb9 | 2 | 0 | 0 | 成功 |

judge 原文：The generated answer accurately captures the core idea of using topology optimization to maximize the nonlinear overlap integral between cavity modes for second-harmonic generation, consistent with the gold answers' key points about optimizing quality factor and nonlinear coupling.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Based on the context, Topology Optimization of Cavity-Based Second Harmonic Generation (SHG) is realized as follows:
> 
> 1. **Use scalable topology optimization of microcavities** where every pixel of the geometry is a degree of freedom, with the design pattern fully determined by computational search (often thousands of free parameters) with little or no a priori information.
> 
> 2. **Set the optimization objective correctly**: Rather than maximizing Purcell factors or LDOS at individual resonances (e.g., max ε̄α min[LDOS(ω₁), LDOS(2ω₁)]), the key is to **maximize the nonlinear overlap integral β̄ between the fundamental mode E₁ (at ω₁) and harmonic mode E₂ (at 2ω₁)**—described by the special overlap integral (3) between the modes.
> 
> 3. **Maximize the SHG enhancement factor Q₁²Q₂|β̄|²**—this simultaneously ensures frequency matching and small confinement factors while yielding orders-of-magnitude improvements in the nonlinear coupling β̄.
> 
> 4. The approach yields micropost and grating microcavity designs supporting strongly coupled fundamental and harmonic modes with large lifetimes Q₁, Q₂ > 10⁴, and lays the framework for future topology optimization of 2D/3D slab structures.


**community**

> Topology optimization of cavity-based second-harmonic generation is realized by extending the scalable topology optimization of microcavities—where every geometric pixel is a degree of freedom—to SHG. Instead of maximizing individual Purcell factors or mode volumes, the key is to maximize the nonlinear overlap integral β̄ between the fundamental (E1) and harmonic (E2) modes, which simultaneously ensures frequency matching (ω2 = 2ω1) and small confinement factors while maximizing the SHG enhancement factor Q1²Q2|β̄|², yielding orders-of-magnitude improvements in nonlinear coupling. This was applied to obtain micropost and grating microcavity designs with Q1, Q2 > 10⁴.

</details>

<a id="case-hao_photonics_1"></a>

### 20. hao_photonics_1 — 答案组织弱化关键方案；评分尺度疑点

**问题：** What are some ways to overcome the heating issue due to residual optical absorption in the integrated optomechanical devices?

**评分：4→2（Δ-2）；rounds：3→3（Δ+0）。**

工具数 3→3；错误 0→0；文档 overview 16→46；QA tokens 34,747→53,024。

两者都是 3 轮、3 次搜索。naive 把 slab-on-substrate/BIC 单独列为散热方案；community 虽在低温条目括号中写到 slab-on-substrate heat dissipation，却没有将“引入衬底、通过辐射声子通道散热”作为独立机制展开。judge 视为缺失而给 2。可确认是关键方案表达显著性下降，不能说该信息完全没召回或没出现在答案中。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/0731c1ee819444e59464b437cf4a93c0.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/ad48a062a2b542ce9c22076240c803ff.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] heating due to residual optical absorption integrated optomechanical devices；全库 | 12 | 9 | 0 | 成功 |
| 2 | search_chunks [hybrid] reduce optical absorption surface passivation thermal conductance heat removal optomechanical；全库 | 12 | 4 | 0 | 成功 |
| 2 | search_chunks [hybrid] pulsed excitation avoid optical heating optomechanical crystal ground state；全库 | 12 | 3 | 0 | 成功 |

judge 原文：The generated answer correctly captures all three gold-standard strategies—2D optomechanical crystals, substrate/BIC heat dissipation, and pulsed excitation—and adds only non-contradictory supporting details.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] overcome heating issue residual optical absorption integrated optomechanical devices；全库 | 12 | 40 | 6 | 成功 |
| 2 | search_chunks [hybrid] reduce optical absorption surface passivation thermal conductance heat removal optomechanical；全库 | 12 | 0 | 0 | 成功 |
| 2 | search_chunks [hybrid] pulsed excitation mitigate steady-state optical heating optomechanical resonator；全库 | 12 | 6 | 1 | 成功 |

judge 原文：The generated answer correctly includes the 2D optomechanical crystal design and pulsed excitation methods, but it omits the distinct gold method of introducing a substrate for phonon dissipation through radiation channels, making it only partially complete.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Ways to overcome heating from residual optical absorption in integrated optomechanical devices include:
> 
> - Reducing optical absorption via surface passivation.
> - Realizing better thermal contact between the localized acoustic mode and the cold environment.
> - Increasing thermal conductance, e.g., using quasi-2D optomechanical crystal (OMC) cavities whose engineered 2D phononic/photonic bandgap provides extra phonon channels to carry heat away.
> - Using pulsed/short optical excitation instead of continuous-wave pumping, which avoids large steady-state optical heating.
> - Using slab-on-substrate (BIC) architectures, whose heat-dissipation benefits become evident at low temperatures (<1 K), along with suppressed material-absorption loss at low temperatures.
> - Using lower pump power and lower repetition rates.


**community**

> Based on the context, ways to overcome the heating from residual optical absorption in integrated optomechanical devices include:
> 
> - **Increasing thermal conductance / heat removal**: using quasi-2D optomechanical crystal (OMC) cavities that connect to the surrounding chip over a larger in-plane solid angle, providing more phonon modes above the acoustic bandgap to carry heat away (thermal conductance increased ~68×, hot-bath occupancy reduced by ~7.2×); engineered 2D phononic/photonic bandgap structures serve as extra heat-removal channels.
> - **Reducing the absorption itself**: surface passivation to lower optical absorption.
> - **Improving thermal contact** between the localized acoustic mode and the cold environment.
> - **Using pulsed (short) optical excitation** instead of continuous-wave pumping, so operations can be completed before steady-state optical heating builds up.
> - **Operating at low (cryogenic/mK) temperatures**, where material-absorption loss is suppressed (and slab-on-substrate heat dissipation becomes effective below ~1 K).
> - **Lowering pump power and experiment repetition rate** to reduce noise from parasitic absorption.

</details>

<a id="case-hao_photonics_3"></a>

### 21. hao_photonics_3 — 强评分一致性疑点

**问题：** What aspects can be studied using a coupled system of qubits and mechanical resonators?

**评分：2→4（Δ+2）；rounds：2→2（Δ+0）。**

工具数 1→2；错误 0→0；文档 overview 8→24；QA tokens 10,823→21,968。

两者都 2 轮，community 多一个并行 vector 查询，答案增加 cat states 等例子。但 naive 被扣的 quantum eraser 在 community 最终答案中同样没有出现；community judge 只要求 transduction 和 entangled resonators 两类就给 4。不能将 +2 解释为补齐了 gold 的关键第三类。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/52e82a856f884b1e88bb1f2280c65340.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/007d6a1ebcea4f8ba6a96dd5b256c467.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] coupled system of qubits and mechanical resonators aspects studied；全库 | 12 | 8 | 0 | 成功 |

judge 原文：The generated answer captures two of the three gold aspects (quantum transduction and entangled mechanical resonators) but omits the quantum eraser scheme, which is an important key fact.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] coupled system qubits mechanical resonators studied aspects；全库 | 12 | 17 | 2 | 成功 |
| 1 | search_chunks [vector] qubit mechanical resonator coupled system；全库 | 12 | 7 | 1 | 成功 |

judge 原文：The generated answer accurately captures core aspects from the gold answers, particularly quantum transduction and quantum state preparation/tomography of entangled mechanical resonators, with no contradictions, while additional listed topics are relevant and consistent.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Based on the context, a coupled system of qubits and mechanical resonators can be used to study:
> 
> - Cooling a mechanical mode to its quantum ground state
> - Quantum control and measurement of mechanical states (e.g., deterministic creation of single phonons, non-classical Fock-state superpositions, Wigner tomography)
> - Quantum state preparation and tomography of entangled mechanical resonators
> - Mechanical coherence, dissipation, and dephasing (e.g., phonon-number-resolved measurements)
> - Quantum nondemolition (QND) measurements of phonon population
> - Quantum transduction (converting qubit excitations to optical photons via mechanical modes)
> - Linear mechanical quantum computing (phononic beam splitters, two-phonon interference, two-qubit gates)
> - Quantum sensing, information processing, quantum memories, and coupling of disparate quantum systems


**community**

> A coupled qubit–mechanical-resonator system can be used to study:
> 
> - Cooling a mechanical mode to its quantum ground state and quantum-limited measurements of the resonator.
> - Quantum control of mechanical states: creation of single and multi-phonon Fock states, superpositions, coherent states, Schrödinger cat states, and Wigner tomography.
> - Strong and dispersive qubit–phonon coupling, cooperativity, and individually addressable high-Q phonon modes.
> - Phonon-number-resolved (QND) measurements of the resonator.
> - Mechanical coherence, dissipation, and dephasing (e.g., time-dependent coherence measurements via flux modulation).
> - Quantum state preparation and tomography of entangled mechanical resonators; squeezing and multimode entanglement.
> - Quantum transduction (e.g., qubit excitation to optical photons), quantum memories, and photon–phonon interfaces.
> - Linear mechanical quantum computing, e.g., phononic beam splitters and two-phonon interference.
> - Quantum sensing and information processing with phonons, including decoherence at sub-GHz mechanical frequencies.

</details>

<a id="case-hao_photonics_4"></a>

### 22. hao_photonics_4 — 覆盖扩展但概念仍混合

**问题：** What methods have been explored to couple light from a fiber onto a chip under cryogenic temperature?

**评分：2→3（Δ+1）；rounds：2→2（Δ+0）。**

工具数 2→2；错误 0→0；文档 overview 12→39；QA tokens 17,446→24,953。

community 答案增加 dimpled tapered fibers，naive 只列 adiabatic taper 与 grating/angle-polished 两项；两者查询不同且 community 第二路改用 vector。judge 承认主要方法覆盖增加，但指出仍把两种 gold 方法合并、用额外方法替代。属于有可见新增内容、但不能只靠更多类别保证完全正确的案例。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/0d7d2de3adfc4e9a8a894a940420482b.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/d2c8b54d78484f568f6270f27ba8cc41.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] couple light from fiber to chip cryogenic temperature；全库 | 12 | 10 | 0 | 成功 |
| 1 | search_chunks [hybrid] fiber-to-chip coupling at cryogenic temperature methods；全库 | 12 | 2 | 0 | 成功 |

judge 原文：The generated answer correctly captures grating couplers with angle-polished fibers and an adiabatic tapered-fiber approach, but it omits the distinct gold-standard method of evanescent coupling between an adiabatic coupler and a pulled angled fiber, making the answer incomplete.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] couple light from fiber onto chip cryogenic temperature；全库 | 12 | 21 | 3 | 成功 |
| 1 | search_chunks [vector] fiber-to-chip coupling cryogenic；全库 | 12 | 18 | 2 | 成功 |

judge 原文：The generated answer correctly covers the main methods of grating couplers and adiabatic/tapered fiber coupling, but it imperfectly merges two distinct gold methods into one and substitutes an extra method, resulting in slight imprecision and omission of some key distinctions.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Two methods have been explored:
> 
> 1. **Adiabatic fiber-optic couplers** – a slowly tapered optical fiber coupled to a similarly tapered on-chip waveguide (adiabatic mode transfer), made cryo-compatible via a gluing/packaging process that ensures mechanical rigidity; demonstrated at mK temperatures (4 K, 20 mK).
> 
> 2. **Grating couplers with angle-polished fibers** – fibers are angle-polished and glued to on-chip grating couplers, enabling scalable, alignment-free coupling in a dilution refrigerator down to ~7 mK.


**community**

> Methods explored to couple light from a fiber onto a chip at cryogenic temperatures include:
> 
> 1. **Adiabatic fiber-optic couplers** — gradual mode transfer from a slowly tapered optical fiber to a tapered on-chip waveguide, made mechanically rigid via a gluing packaging process; demonstrated down to mK temperatures with >50% efficiency in the telecom band.
> 2. **Grating couplers with angle-polished fibers** — glued angle-polished fibers over grating couplers; demonstrated at 7 mK with 25% single-pass efficiency, scalable to many ports without in-situ alignment stages.
> 3. **Dimpled tapered fibers** — evanescent coupling using a dimpled tapered fiber on a robust holder with high-precision nanopositioning stages in optical-access vacuum chambers, used for cryogenic optomechanical coupling.

</details>

<a id="case-hao_photonics_9"></a>

### 23. hao_photonics_9 — 社区补全的强证据案例

**问题：** What physical platforms can be used to study the quantum properties of phonons?

**评分：2→4（Δ+2）；rounds：2→2（Δ+0）。**

工具数 1→1；错误 0→0；文档 overview 10→20；QA tokens 10,797→14,491。

两者均只有一个同参查询，返回的 12 个 chunk 及顺序完全一致，都第 2 轮回答。community 注入的同叶社区成员 overview 新增 Non-classical correlations… 和 Optically heralded microwave photon addition；naive 的全部工具上下文没有对应 photon–phonon/heralded 描述。community 最终增加 optomechanical transducers，正好补齐 judge 所指出的缺项。这里最能支持“社区 overview 扩展改善分类覆盖”，仍不是随机对照因果证明。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/ef01f2d694df4148ab7eac5d5e8b1bee.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/e14956da85a04100816f3940684d0ac3.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] physical platforms to study quantum properties of phonons；全库 | 12 | 10 | 0 | 成功 |

judge 原文：The generated answer correctly identifies several superconducting-qubit and electromechanical platforms, but it omits the optomechanical interaction platform, which is one of the key categories in the gold answer, so it is only partial.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] physical platforms to study quantum properties of phonons；全库 | 12 | 20 | 3 | 成功 |

judge 原文：The generated answer accurately covers all the physical platforms from the gold answers—optomechanical, superconducting qubit coupled to various acoustic resonators, and electromechanical interfaces—with additional relevant details that do not contradict the gold standard.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Physical platforms for studying quantum properties of phonons include:
> 
> - **Microwave-frequency mechanical resonators** ("quantum drums") coupled to superconducting qubits
> - **Surface acoustic-wave (SAW) resonators** coupled to superconducting qubits (e.g., transmon), also with SQUID-integrated Bragg reflectors for squeezed/entangled states
> - **Bulk acoustic-wave resonators (HBAR)** coupled to superconducting transmon qubits
> - **Phononic crystal resonators** (e.g., lithium niobate) coupled to superconducting qubits (fluxonium)
> - **Crystalline silicon mechanical oscillators** interfaced with superconducting microwave circuits
> - **Phononic integrated circuits** on GaN-on-sapphire
> - **Silicon phononic crystal circuits** with piezoelectric actuators (also LiNbO₃, diamond, GaAs)
> - **Solid-state phononic beam-splitter systems** characterized with superconducting qubits


**community**

> Based on the context, the physical platforms used to study quantum properties of phonons include:
> 
> - **Superconducting qubits coupled to mechanical resonators** (e.g., a microwave-frequency "quantum drum" resonator, cooled to its quantum ground state for single-phonon control)
> - **Surface acoustic wave (SAW) resonators** coupled to superconducting qubits (e.g., transmon qubits on lithium niobate), used for Fock-state control, squeezing, and multimode entanglement (also with integrated SQUIDs)
> - **Bulk acoustic-wave resonators (HBAR)** coupled to superconducting transmon qubits, used to create multi-phonon Fock states and Schrödinger cat states
> - **Phononic crystal resonators** (e.g., lithium niobate) coupled to superconducting qubits (fluxonium or transmon), enabling phonon-number-resolved measurements and entangled resonators
> - **Crystalline silicon oscillators** coupled to superconducting circuits (electromechanical interface for long-lived phonons)
> - **Optomechanical transducers/nanomechanical resonators**, used for non-classical photon–phonon correlations and heralded microwave photon addition
> - **Phononic integrated circuits** (e.g., GaN-on-sapphire) for routing and confining phonons.

</details>

<a id="case-hao_photonics_10"></a>

### 24. hao_photonics_10 — 社区新增猫态证据；已有基态证据利用改善

**问题：** Which quantum states of phonons have been successfully prepared?

**评分：3→4（Δ+1）；rounds：2→2（Δ+0）。**

工具数 2→2；错误 0→0；文档 overview 14→21；QA tokens 17,663→20,457。

两者均 2 轮、2 次搜索；首个同参查询返回同样 chunk。community 首个返回额外带入 16-microgram oscillator 的 Schrödinger cat states overview，而 naive 全部上下文没有 cat state。最终 community 新增猫态与基态，正好对应 naive 的扣分项。不过 ground state 已在 naive 的 chunk 中，故猫态是新信息覆盖，基态是对已有信息的更完整综合；第二个查询也不同。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/b3e855c929934c128f5fa9c0a490eaea.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/904b9ea55b0a4712932a9ce7beb93e68.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] quantum states of phonons successfully prepared；全库 | 12 | 10 | 0 | 成功 |
| 1 | search_chunks [hybrid] phonon quantum state preparation Fock state squeezed；全库 | 12 | 4 | 0 | 成功 |

judge 原文：The generated answer correctly identifies several successfully prepared phonon states such as Fock, two-mode squeezed, and entangled states, but it omits the ground state and Schrödinger cat states, making it a good but incomplete match.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] quantum states of phonons successfully prepared；全库 | 12 | 15 | 2 | 成功 |
| 1 | search_chunks [hybrid] phonon Fock state squeezed state preparation experiment；全库 | 12 | 6 | 1 | 成功 |

judge 原文：The generated answer accurately captures all the quantum phonon states listed in the gold answer—ground, Fock, Schrödinger cat, squeezed, and entangled states—and adds only consistent, relevant details.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> Successfully prepared phonon quantum states include:
> 
> - **Fock states** (up to N=7) and their **superpositions** in an HBAR (Chu et al. 2018).
> - A **non-classical superposition of zero- and one-phonon Fock states** in a surface acoustic-wave resonator (mapped via Wigner tomography).
> - **Single phonons (single quantum excitations)** and **coherent states** in a microwave-frequency "quantum drum" mechanical resonator.
> - **Two-mode squeezed states** between phonons in different SAW modes, and **multipartite entanglement among four acoustic modes**.
> - **Two-phonon entangled states** (quantum eraser/interferometry).
> - **Entangled states of two nanomechanical resonators** (deterministic control and tomography).
> - **Remote entanglement between two micromechanical oscillators** (conditional single-phonon preparation via DLCZ).
> - **Single-phonon Fock states** via optically heralded microwave photon addition in an optomechanical transducer.


**community**

> Based on the context, the following quantum states of phonons have been successfully prepared:
> 
> - **Quantum ground state** (zero-phonon state) of mechanical resonators (e.g., a 6 GHz "quantum drum", HBAR, silicon oscillator).
> - **Single-phonon Fock states** (single quantum excitations).
> - **Multi-phonon Fock states**, up to N = 7, with full quantum tomography in a bulk acoustic-wave resonator.
> - **Superpositions of zero- and one-phonon Fock states** (non-classical superposition) in a SAW resonator, mapped by Wigner tomography.
> - **Coherent states** (created by classical excitation).
> - **Two-mode squeezed states** between phonons in different SAW modes, and **multipartite entanglement** between four acoustic modes.
> - **Two-phonon entangled states** (e.g., in a SAW quantum eraser and phononic beam splitter/two-phonon interference).
> - **Entangled states of two nanomechanical resonators**.
> - **Schrödinger cat states** (coherent superpositions with well-separated phase-space distributions) of a 16-microgram mechanical oscillator.
> - **Non-classical single-phonon states** via photon–phonon correlations (heralded single-phonon Fock states in optomechanical systems).

</details>

<a id="case-yanyu_photonics_1"></a>

### 25. yanyu_photonics_1 — 答案覆盖更广，但核心边界仍未补上

**问题：** How do high-Q dielectric optical microcavities, specifically whispering gallery mode (WGM) resonators, function as biosensors for detecting nanomaterials and biomolecules?

**评分：2→3（Δ+1）；rounds：2→2（Δ+0）。**

工具数 2→2；错误 0→0；文档 overview 19→56；QA tokens 17,150→28,922。

community 仍在 2 轮内回答，增加 thermo-optic、EP 等表述；EP 已存在于 naive 的第二个工具结果，不能当作新增召回证据。两者都没有明确 pristine WGM 不能直接单分子检测的关键 caveat，judge 对该遗漏分别给 2/3。可见综合侧重点变化，但 +1 并不代表已解决最重要的限制条件。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/7177079b8777471f86cabbba260839f9.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/13d7498d12574a45ac399cba2897375b.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] whispering gallery mode resonator biosensor detection nanomaterials biomolecules；全库 | 12 | 12 | 0 | 成功 |
| 1 | search_chunks [hybrid] high-Q dielectric optical microcavity WGM sensing principle；全库 | 12 | 7 | 0 | 成功 |

judge 原文：The generated answer correctly describes the main WGM sensing mechanisms (reactive shift, mode splitting, dissipative broadening) but overstates capabilities by claiming direct detection of single proteins/molecules without clearly noting the gold's important caveat that this has not been achieved on pristine WGM cavities, thus omitting a key constraint.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] whispering gallery mode resonators biosensors detecting nanomaterials biomolecules；全库 | 12 | 29 | 3 | 成功 |
| 1 | search_chunks [hybrid] high-Q dielectric optical microcavity biosensing mechanism；全库 | 12 | 27 | 4 | 成功 |

judge 原文：The generated answer correctly covers the three core sensing mechanisms and relevant details, but omits the gold answer's caveat that direct single-molecule detection is not yet available on pristine WGM cavities and slightly conflates reactive sensing with mode splitting.

</details>

<details>
<summary>展开两份最终回答原文</summary>


**naive**

> High-Q WGM microcavities (microspheres, microtoroids) confine light by total internal reflection, producing narrow resonances highly sensitive to perturbations in their evanescent field. When a nanomaterial or biomolecule binds to the (often functionalized) surface, it perturbs the cavity via:
> 
> - **Reactive (dispersive) interaction**: the target's excess polarizability shifts the resonance frequency/wavelength; the shift scales with surface density and polarizability and inversely with cavity radius (perturbation theory). Binding can also split the mode (doublet/split WGMs).
> - **Dissipative interaction**: lossy particles (e.g., gold nanorods) change the mode linewidth and Q factor, enabling detection of single lossy nanoparticles.
> 
> This enables label-free, real-time detection and sizing of single proteins (BSA, thyroglobulin), viruses (Influenza A, MS2), nucleic-acid hybridization, enzyme–reactant interactions, and even single ions. Sensitivity is boosted by hybrid photonic–plasmonic designs—gold nanorods/nanoshells resonantly coupled to the WGM strongly enhance the local field (up to ~10³), yielding single-molecule/single-virus detection (e.g., frequency shifts up to MHz, limits down to ~5 kDa proteins).


**community**

> High-Q dielectric optical microcavities, such as whispering gallery mode (WGM) resonators, act as biosensors because their ultrahigh Q enhances light–matter interactions in a tiny confined volume. Light circulates by continuous total internal reflection, producing an evanescent field at the surface. When a nanomaterial or biomolecule binds to (or enters the evanescent field of) the resonator, it perturbs the mode. This perturbation is read out through several mechanisms:
> 
> - **Reactive (dispersive) sensing:** the particle causes a resonant frequency/wavelength shift or mode splitting proportional to the perturbation strength. For protein adsorption on microspheres, the shift is inversely proportional to radius and proportional to surface density and excess polarizability, allowing single-protein and single-virus detection and sizing (e.g., Influenza A virions, polystyrene/gold nanoparticles).
> - **Dissipative sensing:** lossy nanoparticles (e.g., gold nanorods) are detected by monitoring linewidth change and mode shift simultaneously.
> - **Thermo-optic sensing:** binding induces a resonant wavelength shift; functionalized surfaces allow label-free single-molecule detection (e.g., interleukin-2 in serum).
> - **Plasmonic enhancement:** gold nanorods coupled to the WGM enhance the local field, boosting frequency shifts (e.g., ~870× for BSA), enabling single-molecule nucleic acid hybridization, protein, ion, and enzyme-reaction detection.
> - **Exceptional-point sensing:** operating at non-Hermitian degeneracies makes the frequency splitting scale as the square root of perturbation, increasing sensitivity for small targets.
> 
> These schemes provide label-free, real-time, continuous detection and sizing of single nanoparticles, viruses, proteins, and even ions in aqueous solution.

</details>

<a id="case-norman_bio_1"></a>

### 26. norman_bio_1 — 更多首轮信息与并行查询后提前结束

**问题：** What are the key mechanisms for lipid nanoparticles (LNPs) to form biomolecular corona with various serum proteins and blood components?

**评分：4→4（Δ+0）；rounds：5→2（Δ-3）。**

工具数 7→2；错误 1→0；文档 overview 23→33；QA tokens 90,527→21,659。

naive 7 次工具调用跨四个工具轮，其中一次读取越界；community 首轮两次并行搜索就得到 33 份 overview，下一轮回答。两者均 4 分。覆盖扩展和首轮双查询与更早停止相容；首个查询本来就不同，不能精确分离社区作用。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/82ac60d7ac434f509f563ad449f8b318.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/704c62592b4c4639be493024446cc47a.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] lipid nanoparticles biomolecular corona serum proteins blood components mechanisms；全库 | 12 | 11 | 0 | 成功 |
| 2 | search_chunks [hybrid] LNP protein corona formation mechanism serum protein adsorption electrostatic hydrophobic apoE apolipoprotein；全库 | 12 | 5 | 0 | 成功 |
| 2 | search_chunks [hybrid] lipid nanoparticle corona complement opsonin immunoglobulin blood coagulation proteins mechanism；全库 | 12 | 0 | 0 | 成功 |
| 3 | search_chunks [hybrid] protein corona Vroman effect hard soft corona exchange lipid nanoparticle surface chemistry charge size；全库 | 12 | 2 | 0 | 成功 |
| 3 | read_chunks doc_id=9f4b84177bedfbbf0971b8d05d6c4d3d05d811835d3a2c3d49c395a0ea0a2e36 ordinals=[1, 2, 3] | 0 | 0 | 0 | Unknown chunk ordinal |
| 4 | search_chunks [hybrid] apolipoprotein E adsorption LNP dePEGylation corona LDLR hepatocyte targeting mechanism；全库 | 12 | 1 | 0 | 成功 |
| 4 | search_chunks [hybrid] nanoparticle corona opsonization complement activation dysopsonin immunoglobulin blood proteins clearance RES；全库 | 12 | 4 | 0 | 成功 |

judge 原文：The generated answer accurately captures the key mechanisms of LNP corona formation, including physicochemical interactions, electrostatic forces, hard/soft corona structure, and composition, with additional consistent details; the omission of the dynamic nature over time is not a critical mechanism for formation and does not contradict the gold answer.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] lipid nanoparticles biomolecular corona serum proteins blood components；全库 | 12 | 23 | 3 | 成功 |
| 1 | search_chunks [hybrid] LNP protein corona formation mechanism；全库 | 12 | 10 | 1 | 成功 |

judge 原文：The generated answer accurately captures the key mechanisms from the gold answer, including electrostatic interactions, hard/soft corona formation, and the role of physicochemical properties, while adding consistent relevant detail about specific protein uptake.

</details>

<a id="case-norman_bio_6"></a>

### 27. norman_bio_6 — 减少一轮，但工具总数和缺项未改善

**问题：** What are the critical factors affecting the library design and diversity in phage display for effective antibody discovery?

**评分：2→2（Δ+0）；rounds：5→4（Δ-1）。**

工具数 5→5；错误 1→1；文档 overview 17→29；QA tokens 45,811→57,907。

两者都 5 次工具调用、各一次越界读取。community 将两个搜索放在首轮并行，因此由 5 轮降到 4 轮，最终仍漏 phage system/format/panning，均 2 分。不能把少一轮当作更准确或更少工具工作量。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/076df34315f9422baf2a10627c899314.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/1cdc9bbd0fe34f859b8b73698b1919aa.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] critical factors affecting library design and diversity in phage display antibody discovery；全库 | 12 | 12 | 0 | 成功 |
| 2 | read_chunks doc_id=580e6fe78984c38e72290d2a8ab5f1079c74c24995c5373c94737001664243bf ordinals=[0, 1, 2, 3] | 0 | 0 | 0 | Unknown chunk ordinal |
| 3 | search_chunks [vector] library size quality functionality sequence diversity natural synthetic semi-synthetic design factors；全库 | 12 | 5 | 0 | 成功 |
| 4 | search_chunks [hybrid] library design factors transformation efficiency functionality CDR diversity；doc_ids=580e6fe78984 | 1 | 0 | 0 | 成功 |
| 4 | search_chunks [keyword] phage display library design diversity antibody discovery critical factors；全库 | 12 | 0 | 0 | 成功 |

judge 原文：The generated answer correctly addresses library diversity and design factors but omits key gold-answer points such as phage display system design, display formats, panning strategies, and integration of NGS/computational methods.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] critical factors affecting library design and diversity in phage display for antibody discovery；全库 | 12 | 22 | 3 | 成功 |
| 1 | search_chunks [vector] phage display antibody library design diversity factors；全库 | 12 | 2 | 0 | 成功 |
| 2 | read_chunks doc_id=580e6fe78984c38e72290d2a8ab5f1079c74c24995c5373c94737001664243bf ordinals=[1, 2, 3, 4, 5] | 0 | 0 | 0 | Unknown chunk ordinal |
| 3 | search_chunks [vector] factors library design functionality diversity source transformation efficiency；doc_ids=580e6fe78984 | 1 | 0 | 0 | 成功 |
| 3 | search_chunks [hybrid] library size quality functionality determinants transformation efficiency CDR design；全库 | 12 | 5 | 0 | 成功 |

judge 原文：The generated answer correctly identifies library diversity and NGS as important factors, but it omits the critical role of phage display system design (phage type, antibody format, and panning strategies), making it incomplete.

</details>

<a id="case-norman_bio_8"></a>

### 28. norman_bio_8 — 更早结束，覆盖缺陷保留

**问题：** How has the integration of recombinant antibody technology impacted the field of vaccine development and immune therapy?

**评分：2→2（Δ+0）；rounds：3→2（Δ-1）。**

工具数 4→2；错误 0→0；文档 overview 21→29；QA tokens 40,322→19,464。

community 首轮两次搜索后结束，naive 额外搜索一轮；两者均未覆盖疫苗抗原/载体策略而为 2 分。轮次减少是过程缩短，不是问题已经回答充分。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/7d3daac801534469bc93c99aef079f83.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/2571d51bc98e49e9abc944e7d5dbef85.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] recombinant antibody technology vaccine development immune therapy；全库 | 12 | 12 | 0 | 成功 |
| 1 | search_chunks [vector] impact recombinant antibody immunotherapy；全库 | 12 | 6 | 0 | 成功 |
| 2 | search_chunks [hybrid] recombinant antibody vaccine immune therapy impact advantages；全库 | 12 | 1 | 0 | 成功 |
| 2 | search_chunks [vector] recombinant technology transformed immunology therapeutics diagnostics；全库 | 12 | 2 | 0 | 成功 |

judge 原文：The generated answer thoroughly covers immunotherapy and mentions diagnostic assays, but omits the key impact of recombinant proteins as vaccine antigens and chimeric vector prime-boost strategies, making it incomplete.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] recombinant antibody technology vaccine development immune therapy；全库 | 12 | 27 | 4 | 成功 |
| 1 | search_chunks [vector] recombinant antibodies impact vaccines immunotherapy；全库 | 12 | 2 | 0 | 成功 |

judge 原文：The generated answer thoroughly covers recombinant antibodies in immunotherapy but omits the key vaccine-development role of recombinant proteins/vectors as antigens, mentioning only diagnostic/QC applications, making it partially incomplete.

</details>

<a id="case-benjamin_bio_2"></a>

### 29. benjamin_bio_2 — 重复追索缺失信息与错误恢复

**问题：** What are the biochemical analytical tools to assess the integrity and stability of LNPs?

**评分：2→2（Δ+0）；rounds：3→4（Δ+1）。**

工具数 3→5；错误 1→2；文档 overview 15→27；QA tokens 24,228→56,419。

community 增加一轮 characterization/RiboGreen 搜索，并有两次越界读取，naive 只有一次。两者最终都漏 UHPLC/RiboGreen 等 gold 要点，均 2 分。多轮探索没有填补缺项。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/b922884eadea49858caf78108803cf90.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/d17fbca7a87248b7b864d83c5346dd49.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] biochemical analytical tools assess integrity stability lipid nanoparticles LNPs；全库 | 12 | 11 | 0 | 成功 |
| 2 | search_chunks [hybrid] analytical techniques LNP integrity stability HPLC fluorescence RiboGreen encapsulation size；全库 | 12 | 4 | 0 | 成功 |
| 2 | read_chunks doc_id=96f8957f539ca860ae7974d576ff30a4c1e19a12e5c2ad54f2e4c6b8d3172e7a ordinals=[1, 2, 3, 4] | 0 | 0 | 0 | Unknown chunk ordinal |

judge 原文：The generated answer correctly lists several key techniques (DLS, cryo-TEM, RP-IP HPLC, CE/gel) but omits important gold-answer tools including UHPLC for lipid components and RiboGreen assay for encapsulation efficiency, making it incomplete.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] biochemical analytical tools to assess integrity and stability of lipid nanoparticles LNPs；全库 | 12 | 19 | 2 | 成功 |
| 2 | search_chunks [hybrid] LNP encapsulation efficiency assay RiboGreen mRNA integrity analytical characterization；全库 | 12 | 6 | 1 | 成功 |
| 2 | read_chunks doc_id=f3b2b65e54692d2c671596c5bc0b731a3c0d8d892b611e882d40a3a03b6f369b ordinals=[1, 2, 3] | 0 | 0 | 0 | Unknown chunk ordinal |
| 3 | search_chunks [hybrid] characterization methods LNP size zeta potential encapsulation RiboGreen integrity stability assessment tools；全库 | 12 | 2 | 0 | 成功 |
| 3 | read_chunks doc_id=96f8957f539ca860ae7974d576ff30a4c1e19a12e5c2ad54f2e4c6b8d3172e7a ordinals=[1, 2, 3, 4] | 0 | 0 | 0 | Unknown chunk ordinal |

judge 原文：The generated answer correctly lists several key techniques (HPLC, CE, gel electrophoresis, DLS, cryo-TEM) but omits important tools like UHPLC for lipid components and the RiboGreen assay for encapsulation efficiency, making it incomplete.

</details>

<a id="case-benjamin_bio_8"></a>

### 30. benjamin_bio_8 — 工具轮减少但无效读取仍多

**问题：** What are some ways to overcome ethical challenges in xenotransplantation?

**评分：2→2（Δ+0）；rounds：5→4（Δ-1）。**

工具数 7→5；错误 2→3；文档 overview 27→38；QA tokens 97,406→61,661。

naive 两次越界读取，community 三次；community 用更多首轮 overview 后减少搜索，却在后续反复读越界序号。4 轮对 5 轮并不代表工具可靠性更好；两者仍漏隐私/社会接纳等伦理要点而为 2 分。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/468b1a0e7c8542bdaa3f882a9fb07150.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/2921b448c8b3400bbbcc26e69c5e0394.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] overcome ethical challenges in xenotransplantation；全库 | 12 | 10 | 0 | 成功 |
| 1 | search_chunks [hybrid] xenotransplantation ethical issues solutions；全库 | 12 | 1 | 0 | 成功 |
| 2 | search_chunks [hybrid] public education informed consent guidelines regulation xenotransplantation ethics；全库 | 12 | 4 | 0 | 成功 |
| 3 | read_chunks doc_id=c11bdfac32810b0caf79f1f7fbcec0a50d28443bb1324307774d18c05ce0bebc ordinals=[1, 2, 3] | 0 | 0 | 0 | Unknown chunk ordinal |
| 3 | read_chunks doc_id=1f0a9932e5482515d479badfeaed8dbfe5c27e37b07575f479f882dcf8f8b620 ordinals=[1, 2, 3] | 0 | 0 | 0 | Unknown chunk ordinal |
| 4 | search_chunks [hybrid] way to address ethical challenge education public discussion monitoring informed consent；全库 | 12 | 7 | 0 | 成功 |
| 4 | search_chunks [hybrid] fair equitable distribution organs risks benefits xenotransplantation；全库 | 12 | 5 | 0 | 成功 |

judge 原文：The generated answer correctly identifies some relevant approaches such as education and public discussion, but omits important ethical strategies from the gold answer like monitoring recipients' privacy and addressing societal acceptance of recipients.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] overcome ethical challenges in xenotransplantation；全库 | 12 | 36 | 4 | 成功 |
| 2 | search_chunks [hybrid] public education discussion informed consent regulation oversight ethical challenges xenotransplantation；全库 | 12 | 2 | 0 | 成功 |
| 2 | read_chunks doc_id=1f0a9932e5482515d479badfeaed8dbfe5c27e37b07575f479f882dcf8f8b620 ordinals=[1, 2, 3] | 0 | 0 | 0 | Unknown chunk ordinal |
| 3 | read_chunks doc_id=c11bdfac32810b0caf79f1f7fbcec0a50d28443bb1324307774d18c05ce0bebc ordinals=[2, 3, 4] | 0 | 0 | 0 | Unknown chunk ordinal |
| 3 | read_chunks doc_id=17166582445d17833f049b7c1303dc7bfdfd928d35b1bf4cbe8bb8aa2f9bc996 ordinals=[1, 2, 3] | 0 | 0 | 0 | Unknown chunk ordinal |

judge 原文：The generated answer captures several valid approaches like education, ethical debate, distribution, and animal welfare, but omits important gold ethical points about recipient monitoring/privacy and societal acceptance/stigmatization, making it only partially complete.

</details>

<a id="case-benjamin_bio_9"></a>

### 31. benjamin_bio_9 — 更早给出同样错误的结论

**问题：** Is it possible for microcapsules to cross the blood brain barrier?

**评分：0→0（Δ+0）；rounds：3→2（Δ-1）。**

工具数 2→1；错误 0→0；文档 overview 16→17；QA tokens 26,415→12,350。

首个同参查询后 community 就结束，naive 又搜索一轮。两者都否定微米粒子穿越 BBB，与 gold 的 1.14/9.55 μm 实例相冲突，均 0 分。此例警示扩展和早停不能替代反例检查；报告不据此判定临床事实，只核对本数据集答案。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/9c7534eb07fe4fd799b41fb2c5824e12.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/f4b2dc9758c94702bc76b4601d684391.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] microcapsules cross blood brain barrier；全库 | 12 | 11 | 0 | 成功 |
| 2 | search_chunks [hybrid] microcapsule brain delivery nanoparticle BBB crossing；全库 | 12 | 5 | 0 | 成功 |

judge 原文：The generated answer directly contradicts the gold answers by claiming micro-sized particles cannot cross the BBB, while the gold answers provide evidence that micron-scale plastic particles and bacteria can cross.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] microcapsules cross blood brain barrier；全库 | 12 | 17 | 2 | 成功 |

judge 原文：The generated answer directly contradicts the gold answers by claiming micron-scale particles like microcapsules are unlikely to cross the BBB, whereas the gold evidence states that 1.14 µm and 9.55 µm polystyrene microspheres can cross it.

</details>

<a id="case-benjamin_bio_10"></a>

### 32. benjamin_bio_10 — 补查分期仍未消解冲突

**问题：** What is the correlation between the efficacy of the EPR effect and the progression of tumor (benign, solid tumor, metastasis, etc.)?

**评分：2→2（Δ+0）；rounds：3→4（Δ+1）。**

工具数 2→4；错误 0→0；文档 overview 12→24；QA tokens 23,655→62,958。

community 多查 benign/metastatic 等子问题，工具数 2→4，轮数 3→4。答案仍含早期小肿瘤几乎无 EPR 的说法，两边均 2 分。新增社区背景未自动解决分期描述不一致。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/55801f339f4e43e78e4557402496ba8c.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/a26c6b94d6fa458f8d94cb5f56a651de.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] EPR effect efficacy tumor progression benign solid tumor metastasis；全库 | 12 | 10 | 0 | 成功 |
| 2 | search_chunks [hybrid] EPR effect benign tumor metastasis efficacy tumor progression stage；全库 | 12 | 2 | 0 | 成功 |

judge 原文：The generated answer correctly captures the late-stage heterogeneous EPR effect and the lack of vasculature in benign lesions, but it incorrectly states that early/small tumors have scarcely any EPR effect, contradicting the gold answer's 'more uniform EPR effect' in early-stage tumors.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] EPR effect efficacy tumor progression benign solid tumor metastasis；全库 | 12 | 19 | 2 | 成功 |
| 2 | search_chunks [hybrid] benign tumor EPR effect not applicable malignant solid tumor metastasis；全库 | 12 | 2 | 0 | 成功 |
| 2 | search_chunks [hybrid] metastatic liver cancer EPR effect uptake retention lipiodol；全库 | 12 | 2 | 0 | 成功 |
| 3 | search_chunks [hybrid] benign tumor EPR effect malignant cancer leaky vasculature；全库 | 12 | 1 | 0 | 成功 |

judge 原文：The generated answer captures the heterogeneity in late-stage tumors and mentions early tumor uniformity, but it omits the critical benign-stage condition of lacking proper vasculature and inaccurately states that early small tumors have scarcely any EPR effect.

</details>

<a id="case-akari_cs_1"></a>

### 33. akari_cs_1 — 过度核验与一次越界恢复

**问题：** Are there any papers showing the effectiveness of quality filtering of LLM pre-training data using more advanced models such as BERT? I found many prior studies only use fasttext but it could make the filtering models pretty weak...

**评分：4→4（Δ+0）；rounds：2→5（Δ+3）。**

工具数 2→7；错误 0→1；文档 overview 15→42；QA tokens 16,673→105,287。

naive 两个首轮查询即答全 Llama 3/FineWeb；community 在同样 4 分下继续读长文档，先请求 [3,4,5,6,7] 越界，再成功读 [4,5]，随后进行额外 RoBERTa/BERT 搜索。轮次 2→5、token 16,673→105,287；更多 overview 未触发更好的停止决策。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/25c9b148d1e4472ca74955335608bfbb.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/07812d36328d4b0dabfd4059c51bbae7.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] quality filtering of LLM pre-training data using BERT classifier；全库 | 12 | 10 | 0 | 成功 |
| 1 | search_chunks [hybrid] pre-training data filtering fastText BERT classifier；全库 | 12 | 5 | 0 | 成功 |

judge 原文：The generated answer accurately identifies the key papers (Llama 3 and FineWeb) demonstrating advanced-model-based quality filtering with correct details, and it adds a relevant BERT comparison without contradicting the gold answer.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] quality filtering LLM pre-training data using BERT classifier；全库 | 12 | 32 | 3 | 成功 |
| 1 | search_chunks [hybrid] fasttext classifier filtering pre-training data effectiveness；全库 | 12 | 1 | 0 | 成功 |
| 2 | read_chunks doc_id=44b7159aa3ec92b81ec588b4126127a270c1d6b58914337fe6e4c00192708461 ordinals=[3, 4, 5, 6, 7] | 0 | 0 | 0 | Unknown chunk ordinal |
| 3 | read_chunks doc_id=44b7159aa3ec92b81ec588b4126127a270c1d6b58914337fe6e4c00192708461 ordinals=[4, 5] | 2 | 0 | 0 | 成功 |
| 3 | search_chunks [hybrid] Roberta classifier quality filtering effectiveness results compared fasttext；doc_ids=44b7159aa3ec | 6 | 0 | 0 | 成功 |
| 4 | search_chunks [hybrid] BERT classifier quality score filter web corpus pretraining data curation；全库 | 12 | 3 | 0 | 成功 |
| 4 | search_chunks [keyword] Roberta DistilRoberta quality classifier Llama 2 predictions document filtering experiments；全库 | 12 | 6 | 0 | 成功 |

judge 原文：The generated answer accurately captures the core examples (Llama 3's RoBERTa-based classifiers and FineWebEdu's Llama-3-70B annotations) and key facts from the gold answer, with no contradictions.

</details>

<a id="case-akari_cs_3"></a>

### 34. akari_cs_3 — 首轮覆盖后较早停止

**问题：** Hi everyone! I was wondering if anyone knows about work on how LLM fine-tuning (perhaps when done poorly) causes the model to become worse at some things? For example, I’ve heard lots of anecdotes that fine-tuning LLMs for specific tasks “hurts their generation ability”, but I’m looking for papers with more systematic exploration.

**评分：4→4（Δ+0）；rounds：3→2（Δ-1）。**

工具数 3→2；错误 0→0；文档 overview 17→41；QA tokens 40,739→26,791。

community 两个首轮查询后回答，naive 还有一轮泛化/灾难遗忘搜索。两者均准确写出 format specialization、RTE/TriviaQA 和缓解办法，均 4 分；可能是扩展后的证据更充分，也含首轮 query 差异。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/b6da28fe364a49c59a12d3f78c3d077c.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/b05c6791ed364c61a2860c448ff83edd.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] fine-tuning LLM hurts generation ability degradation systematic；全库 | 12 | 9 | 0 | 成功 |
| 1 | search_chunks [hybrid] catastrophic forgetting fine-tuning language models becomes worse；全库 | 12 | 5 | 0 | 成功 |
| 2 | search_chunks [hybrid] fine-tuning distorts pretrained knowledge degrades capabilities benchmark；全库 | 12 | 3 | 0 | 成功 |

judge 原文：The generated answer accurately captures the gold answer's key findings—fine-tuning harms generalization via format specialization, the RTE/TriviaQA 90% observation, and mitigations like two-stage parameter-efficient tuning and ICL-based training—with only minor labeling differences and additional consistent context.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] fine-tuning hurts generation ability catastrophic forgetting LLM；全库 | 12 | 35 | 5 | 成功 |
| 1 | search_chunks [hybrid] fine-tuning degrades model performance capabilities systematic study；全库 | 12 | 6 | 1 | 成功 |

judge 原文：The generated answer accurately captures the gold answer's core findings about fine-tuning causing format specialization and loss of generalization, including the RTE/TriviaQA example, and adds only consistent additional context.

</details>

<a id="case-rulin_cs_1"></a>

### 35. rulin_cs_1 — 从泛化探索改为定向确认

**问题：** What are the latest works on finetuning an auto-regressive LM for dense passage retrieval? How are their performance compared with bi-directional encoders?

**评分：4→4（Δ+0）；rounds：4→3（Δ-1）。**

工具数 5→4；错误 0→0；文档 overview 22→51；QA tokens 78,549→52,150。

naive 三个工具轮持续扩大 dense retrieval 查询；community 首轮后第二轮按 doc_ids 确认性能比较。两者都覆盖 NV-Embed、LLM2Vec、E5-Mistral、GRIT，均 4 分。少一轮与更直接的定位核验相符。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/820bd5ea5e664dd5ad1245cea875a348.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/fcf4827e5e244cfe81cb50a47338b070.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] finetuning auto-regressive language model dense passage retrieval；全库 | 12 | 12 | 0 | 成功 |
| 1 | search_chunks [hybrid] auto-regressive LM retrieval performance compared bi-directional encoder；全库 | 12 | 3 | 0 | 成功 |
| 2 | search_chunks [hybrid] finetune decoder-only LLM dense passage retrieval outperform BERT bidirectional encoder MTEB；全库 | 12 | 3 | 0 | 成功 |
| 2 | search_chunks [vector] dense retrieval decoder-only auto-regressive fine-tuning bidirectional attention；全库 | 12 | 2 | 0 | 成功 |
| 3 | search_chunks [hybrid] dense passage retrieval fine-tuning LLM bidirectional encoders comparison BEIR；全库 | 12 | 2 | 0 | 成功 |

judge 原文：The generated answer accurately identifies and describes all key latest works (NV-Embed, LLM2Vec, E5-Mistral, GRIT) and correctly states that they outperform bi-directional encoder models, matching the gold answers.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] finetuning auto-regressive language model dense passage retrieval；全库 | 12 | 23 | 4 | 成功 |
| 1 | search_chunks [hybrid] autoregressive LM retriever compared with bi-encoder bidirectional；全库 | 12 | 11 | 1 | 成功 |
| 2 | search_chunks [hybrid] outperform BERT bidirectional dense retrieval benchmark results；doc_ids=320fd61a324e | 1 | 6 | 1 | 成功 |
| 2 | search_chunks [hybrid] outperform encoder-only models bidirectional attention dense retrieval；doc_ids=2aa2b42b9ff7 | 1 | 11 | 1 | 成功 |

judge 原文：The generated answer accurately captures the core information from the gold answers, listing the same latest works (NV-Embed, LLM2Vec, E5-Mistral, GRIT) and correctly stating that they outperform bi-directional encoders in dense retrieval, with additional consistent details.

</details>

<a id="case-rulin_cs_2"></a>

### 36. rulin_cs_2 — 去掉整轮失败读取

**问题：** How do people train a long-context Transformer model over 32K context length using sequence parallelism techniques? How are these methods compared with each other?

**评分：4→4（Δ+0）；rounds：3→2（Δ-1）。**

工具数 7→2；错误 5→0；文档 overview 17→52；QA tokens 34,014→28,186。

naive 第 2 工具轮一次发出五个 read_chunks，全部 Unknown chunk ordinal；community 首轮两次查询后直接生成同样 4 分答案。少的一轮在 naive 中没有获得任何证据，是最清楚的无效轮消除案例。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/1f9a6bfe55684402b94faefa61f1caba.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/582e7d22cb6c4526b6b2030dce939755.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] sequence parallelism long-context Transformer 32K context length training；全库 | 12 | 12 | 0 | 成功 |
| 1 | search_chunks [hybrid] sequence parallel methods comparison DeepSpeed-Ulysses Megatron Ring Attention；全库 | 12 | 5 | 0 | 成功 |
| 2 | read_chunks doc_id=bba99e078141c946babbb062c97af45f9a60ea93f3617d80e2291c33c2689368 ordinals=[1, 2, 3] | 0 | 0 | 0 | Unknown chunk ordinal |
| 2 | read_chunks doc_id=30686cbd8cd4d7d19a1ebc79d8911e3eb843249784bcacd19221cdacfa222ff0 ordinals=[1, 2, 3] | 0 | 0 | 0 | Unknown chunk ordinal |
| 2 | read_chunks doc_id=264cc67ffeda1af4a36d7adb7f16cb80f7da0ec8932cdd626f1b5282194e40bc ordinals=[1, 2, 3] | 0 | 0 | 0 | Unknown chunk ordinal |
| 2 | read_chunks doc_id=c653dd5ebab33ce8a555fbcb65da3c9c4e7adcdbd2f6026d5bc59803bec5ca54 ordinals=[1, 2, 3] | 0 | 0 | 0 | Unknown chunk ordinal |
| 2 | read_chunks doc_id=50f07c55a5d9ec31f317fadcd54365d0dc21c22e8791c66e13144c9328d9d5f4 ordinals=[1, 2, 3] | 0 | 0 | 0 | Unknown chunk ordinal |

judge 原文：The generated answer accurately and comprehensively captures all key sequence-parallelism methods and comparative performance results from the gold answers, with additional consistent details that do not contradict them.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] long-context Transformer training 32K sequence parallelism；全库 | 12 | 37 | 4 | 成功 |
| 1 | search_chunks [hybrid] sequence parallelism methods comparison LongNet Ring Attention；全库 | 12 | 15 | 2 | 成功 |

judge 原文：The generated answer accurately and comprehensively captures all key methods and comparisons from the gold answers, with additional details that are consistent and do not contradict the ground truth.

</details>

<a id="case-jacqueline_cs_6"></a>

### 37. jacqueline_cs_6 — 减少重复定向搜索和失败读取

**问题：** Social bias in large language models is an endemic problem, as models often inherit and amplify stereotypical judgments due to naturally occurring, yet undesirable statistical associations from training corpora. What are some recent techniques on post-trained, aligned LMs that mitigate social bias?

**评分：4→4（Δ+0）；rounds：6→3（Δ-3）。**

工具数 8→4；错误 1→0；文档 overview 31→62；QA tokens 124,649→66,090。

naive 反复定向查询同一文档并读越界，共五个工具轮；community 首轮获得 47 份 overview，再补两路搜索，第三轮回答。两者均覆盖 GenderAlign 和 few-shot debiasing，4 分保持。轮次下降与更早覆盖多个方法相容，不能把因果完全归给社区。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/4dd0819d359f4e76878a268109f0a817.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/4c38eb4fb61f4b8e9023b5ed7fc843de.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] techniques mitigate social bias in post-trained aligned language models；全库 | 12 | 11 | 0 | 成功 |
| 2 | search_chunks [hybrid] post-training debiasing parameter efficient fine-tuning RLHF aligned models reduce stereotypes；全库 | 12 | 8 | 0 | 成功 |
| 2 | search_chunks [hybrid] mitigate social bias inference-time decoding prompting aligned LLM；全库 | 12 | 7 | 0 | 成功 |
| 3 | search_chunks [hybrid] post-processing bias mitigation techniques aligned models decoding；doc_ids=5ef54bfd2786 | 1 | 0 | 0 | 成功 |
| 3 | search_chunks [hybrid] bias mitigation fine-tuning alignment reinforcement learning from human feedback；doc_ids=5ef54bfd2786 | 1 | 0 | 0 | 成功 |
| 4 | read_chunks doc_id=5ef54bfd27865c03b0a409214b905298c9cf96ee1e59fb3c0124d8a72554611e ordinals=[1, 2, 3] | 0 | 0 | 0 | Unknown chunk ordinal |
| 5 | search_chunks [hybrid] bias mitigation reinforcement learning human feedback fairness aligned LLM post-training；全库 | 12 | 2 | 0 | 成功 |
| 5 | search_chunks [hybrid] gender bias mitigation few-shot prompting instruction-tuned model stereotypes；全库 | 12 | 3 | 0 | 成功 |

judge 原文：The generated answer accurately captures the two key techniques from the gold answers (GenderAlign and the interpretability-informed few-shot MT debiasing) and adds a relevant, non-contradictory RAIN example.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] techniques to mitigate social bias in post-trained aligned large language models；全库 | 12 | 44 | 5 | 成功 |
| 1 | search_chunks [vector] social bias mitigation alignment training stereotype；全库 | 12 | 3 | 0 | 成功 |
| 2 | search_chunks [keyword] debiasing aligned LLMs post-training bias mitigation stereotype fairness methods；全库 | 12 | 2 | 0 | 成功 |
| 2 | search_chunks [vector] gender bias mitigation alignment dataset post-trained model；全库 | 12 | 13 | 2 | 成功 |

judge 原文：The generated answer fully captures the core facts of the gold answers, including the GenderAlign dataset for debiasing alignment and the few-shot learning intervention for instruction-tuned machine translation, with accurate additional details that do not contradict the gold standard.

</details>

<a id="case-jacqueline_cs_10"></a>

### 38. jacqueline_cs_10 — 减少围绕同一方法的反复搜索

**问题：** Contrastive learning is an effective technique for learning good discriminative embedding representations, and was a popular training strategy for encoder-only LMs. With the recent popularity of causal, decoder-only LMs, have there been any works which show that contrastive learning can also help improve generative performance for this architecture?

**评分：4→4（Δ+0）；rounds：6→4（Δ-2）。**

工具数 10→6；错误 1→1；文档 overview 37→73；QA tokens 192,964→113,607。

naive 多轮围绕 SimCTG/CoNT 改写 query，并有一次越界读取；community 同样有一次越界但只用三个工具轮。两者均 4 分，community 第一轮更广的 overview 可能帮助较早形成方案列表，但首轮输入不同。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/f6461667f0a54bf8a4303d980961b125.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/52f622a4024146d0bd755f0646b9d297.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] contrastive learning decoder-only causal language model generative performance；全库 | 12 | 12 | 0 | 成功 |
| 1 | search_chunks [vector] contrastive learning improves text generation decoder-only LM；全库 | 12 | 8 | 0 | 成功 |
| 2 | search_chunks [hybrid] contrastive training GPT-2 SimCTG contrastive search generation；全库 | 12 | 5 | 0 | 成功 |
| 2 | search_chunks [vector] contrastive learning improves generative performance decoder-only causal LM training；全库 | 12 | 0 | 0 | 成功 |
| 3 | search_chunks [hybrid] SimCTG contrastive learning GPT-2 generation；全库 | 12 | 5 | 0 | 成功 |
| 3 | search_chunks [keyword] contrastive learning causal decoder-only LM improves generation open-ended text；全库 | 12 | 4 | 0 | 成功 |
| 4 | read_chunks doc_id=728f82d232e1874d74690e9e892f801b947968fbf10cf44c4fe9d5e7d9a6252a ordinals=[0, 1, 2, 3] | 0 | 0 | 0 | Unknown chunk ordinal |
| 4 | search_chunks [hybrid] SimCTG contrastive framework neural text generation GPT-2 decoder；全库 | 12 | 2 | 0 | 成功 |
| 5 | search_chunks [hybrid] contrastive search decoding contrastive learning GPT-2 language model open-ended text generation diversity；全库 | 12 | 1 | 0 | 成功 |
| 5 | search_chunks [hybrid] CoNT contrastive training decoder model architecture；doc_ids=728f82d232e1 | 1 | 0 | 0 | 成功 |

judge 原文：The generated answer accurately captures the core information about CoNT from the gold answer, including contrastive learning improving autoregressive generation by sampling from own predictions to alleviate exposure bias, with no contradictions.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] contrastive learning causal decoder-only language model generative performance；全库 | 12 | 50 | 5 | 成功 |
| 1 | search_chunks [vector] contrastive learning improve generation decoder-only LM；全库 | 12 | 12 | 1 | 成功 |
| 2 | read_chunks doc_id=728f82d232e1874d74690e9e892f801b947968fbf10cf44c4fe9d5e7d9a6252a ordinals=[0, 1, 2, 3, 4, 5, 6, 7, 8] | 0 | 0 | 0 | Unknown chunk ordinal |
| 2 | search_chunks [hybrid] SimCTG contrastive framework neural text generation decoder-only GPT；全库 | 12 | 1 | 0 | 成功 |
| 3 | search_chunks [hybrid] contrastive learning GPT-2 decoder-only text generation SimCTG contrastive search；全库 | 12 | 3 | 0 | 成功 |
| 3 | search_chunks [vector] contrastive learning improves autoregressive language model generation open-domain；全库 | 12 | 7 | 2 | 成功 |

judge 原文：The generated answer accurately captures the core facts about CoNT from the gold answer, including the sequence-level contrastive loss, sampling from the model's own predictions to alleviate exposure bias, and using the learned similarity score during inference, with no contradictions.

</details>

<a id="case-pan_biophysics_3"></a>

### 39. pan_biophysics_3 — 增加主题核验，分数已到上限

**问题：** What orgnelle level reaction may contribute to the hetergeniety in dynamic imaging of cell ?

**评分：4→4（Δ+0）；rounds：3→4（Δ+1）。**

工具数 4→5；错误 1→1；文档 overview 23→39；QA tokens 31,525→44,477。

community 在失败试读后，对线粒体 ATP 和反应噪声再查询一轮；naive 少一轮。均 4 分，因此本指标未显示额外探索收益，不代表答案细节完全相同。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/ef90183b522849e18ab5438578b1495a.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/e8032b8ef8a44a1d9a790fa31c9a7a63.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] organelle level reaction heterogeneity dynamic imaging of cell；全库 | 12 | 12 | 0 | 成功 |
| 1 | search_chunks [vector] mitochondria heterogeneity dynamic imaging；全库 | 12 | 5 | 0 | 成功 |
| 2 | read_chunks doc_id=b221e9521205850a393869b9b88c90ab98673f34a85d315cd099ba528a883702 ordinals=[0, 1, 2, 3] | 0 | 0 | 0 | Unknown chunk ordinal |
| 2 | search_chunks [keyword] organelle reaction noise heterogeneity dynamic imaging reaction intermediate scale；全库 | 12 | 6 | 0 | 成功 |

judge 原文：The generated answer accurately and concisely captures the core meaning that organelle-level reactions, including mitochondrial ATP production and intermediate-scale noise, contribute to heterogeneity in dynamic cell imaging, matching the gold answer without contradiction.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] organelle level reaction heterogeneity dynamic imaging of cell；全库 | 12 | 29 | 3 | 成功 |
| 2 | read_chunks doc_id=b221e9521205850a393869b9b88c90ab98673f34a85d315cd099ba528a883702 ordinals=[0, 1, 2, 3, 4, 5] | 0 | 0 | 0 | Unknown chunk ordinal |
| 2 | search_chunks [vector] organelle reactions heterogeneity dynamic imaging noise sources；doc_ids=b221e9521205 | 1 | 0 | 0 | 成功 |
| 3 | search_chunks [hybrid] mitochondrial ATP production heterogeneity single cell dynamic imaging metabolic profiles；全库 | 12 | 7 | 1 | 成功 |
| 3 | search_chunks [keyword] organelle level reaction noise heterogeneity dynamic imaging intermediate scale variations；全库 | 12 | 3 | 0 | 成功 |

judge 原文：The generated answer accurately captures the core idea that organelle-level reactions, specifically mitochondrial ATP dynamics and general organelle variations, contribute to heterogeneity in dynamic cell imaging, consistent with the gold answer.

</details>

<a id="case-pan_biophysics_4"></a>

### 40. pan_biophysics_4 — 并行分组改变轮次，工具数反而增加

**问题：** How to recognzie and suppress OCT autocorrelation artifact.

**评分：4→4（Δ+0）；rounds：6→5（Δ-1）。**

工具数 11→13；错误 3→5；文档 overview 24→22；QA tokens 57,057→50,207。

community 6→5 轮，但工具数 11→13；它把五次越界 read_chunks 放同一轮，下一轮再并行读取五个 ordinal 0。naive 为三次越界读取。两者 4 分。该例证明 iteration 不是工作量或效率的充分指标，也不能把并行后轮数下降都归给社区。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/25ae32111fd4465e9a836ef8329e026d.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/0821dc231a464bbb823f880d68d59be8.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] OCT autocorrelation artifact recognize suppress；全库 | 12 | 12 | 0 | 成功 |
| 2 | read_chunks doc_id=c1c2ab8dc0288681c4cd9fdf79051e8df194504316d00cf057da9164b0e2a2f2 ordinals=[0, 1, 2, 3, 4] | 0 | 0 | 0 | Unknown chunk ordinal |
| 2 | read_chunks doc_id=556d0bca8a84fc636e9db43722041ec39f91163a31fabdec1d2eb06f27b3d671 ordinals=[0, 1, 2, 3, 4] | 0 | 0 | 0 | Unknown chunk ordinal |
| 2 | read_chunks doc_id=2656f90092d430ea601181692f2d200eeadac01cccb4b396fdcf9a8b7966cc3b ordinals=[0, 1, 2, 3, 4] | 0 | 0 | 0 | Unknown chunk ordinal |
| 3 | search_chunks [keyword] autocorrelation artifact removal technique；doc_ids=c1c2ab8dc028 | 1 | 0 | 0 | 成功 |
| 3 | search_chunks [keyword] eliminate autocorrelation artifacts processing；doc_ids=556d0bca8a84 | 1 | 0 | 0 | 成功 |
| 3 | search_chunks [keyword] piezoelectric fiber stretcher autocorrelation artifact；doc_ids=2656f90092d4 | 1 | 0 | 0 | 成功 |
| 4 | search_chunks [hybrid] recognize autocorrelation artifact image；全库 | 12 | 4 | 0 | 成功 |
| 4 | search_chunks [keyword] autocorrelation artifact appears mirror image；全库 | 12 | 6 | 0 | 成功 |
| 5 | read_chunks doc_id=a545bba739f42ec0627dc419e86dc19052b66ff1ea42992e49f7202c1b73c989 ordinals=[0] | 1 | 0 | 0 | 成功 |
| 5 | search_chunks [keyword] autocorrelation artifact ghost mirror image；全库 | 12 | 2 | 0 | 成功 |

judge 原文：The generated answer accurately captures the recognition principle of distinguishing signal from noise and enumerates all key suppression methods from the gold papers without contradictions, so it is perfect.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] OCT autocorrelation artifact recognize suppress；全库 | 12 | 21 | 3 | 成功 |
| 2 | search_chunks [hybrid] how to recognize autocorrelation artifact OCT mirror image suppression technique；全库 | 12 | 1 | 0 | 成功 |
| 2 | search_chunks [hybrid] autocorrelation artifact recognition suppression；doc_ids=a545bba739f4,2656f90092d4,c1c2ab8dc028,556d0bca8a84,6ccc468f2989 | 5 | 0 | 0 | 成功 |
| 3 | read_chunks doc_id=a545bba739f42ec0627dc419e86dc19052b66ff1ea42992e49f7202c1b73c989 ordinals=[0, 1, 2, 3, 4, 5] | 0 | 0 | 0 | Unknown chunk ordinal |
| 3 | read_chunks doc_id=2656f90092d430ea601181692f2d200eeadac01cccb4b396fdcf9a8b7966cc3b ordinals=[0, 1, 2, 3, 4, 5] | 0 | 0 | 0 | Unknown chunk ordinal |
| 3 | read_chunks doc_id=c1c2ab8dc0288681c4cd9fdf79051e8df194504316d00cf057da9164b0e2a2f2 ordinals=[0, 1, 2, 3, 4, 5] | 0 | 0 | 0 | Unknown chunk ordinal |
| 3 | read_chunks doc_id=556d0bca8a84fc636e9db43722041ec39f91163a31fabdec1d2eb06f27b3d671 ordinals=[0, 1, 2, 3, 4, 5] | 0 | 0 | 0 | Unknown chunk ordinal |
| 3 | read_chunks doc_id=6ccc468f2989cf87a833f3a25b4d079e6d68a0c6803519aab239ebfc27302c28 ordinals=[0, 1, 2, 3, 4, 5] | 0 | 0 | 0 | Unknown chunk ordinal |
| 4 | read_chunks doc_id=a545bba739f42ec0627dc419e86dc19052b66ff1ea42992e49f7202c1b73c989 ordinals=[0] | 1 | 0 | 0 | 成功 |
| 4 | read_chunks doc_id=2656f90092d430ea601181692f2d200eeadac01cccb4b396fdcf9a8b7966cc3b ordinals=[0] | 1 | 0 | 0 | 成功 |
| 4 | read_chunks doc_id=c1c2ab8dc0288681c4cd9fdf79051e8df194504316d00cf057da9164b0e2a2f2 ordinals=[0] | 1 | 0 | 0 | 成功 |
| 4 | read_chunks doc_id=556d0bca8a84fc636e9db43722041ec39f91163a31fabdec1d2eb06f27b3d671 ordinals=[0] | 1 | 0 | 0 | 成功 |
| 4 | read_chunks doc_id=6ccc468f2989cf87a833f3a25b4d079e6d68a0c6803519aab239ebfc27302c28 ordinals=[0] | 1 | 0 | 0 | 成功 |

judge 原文：The generated answer accurately captures the core suppression methods and recognition-related distinction between true signals and noise from the gold answers, with no meaningful contradictions.

</details>

<a id="case-shengyan_photonics_2"></a>

### 41. shengyan_photonics_2 — 并行首轮覆盖后结束

**问题：** What recent experiments have verified the existence of the Casimir force at the micro- and nanoscale?

**评分：4→4（Δ+0）；rounds：3→2（Δ-1）。**

工具数 3→2；错误 0→0；文档 overview 13→43；QA tokens 31,315→25,926。

naive 首轮单查询、第二轮补两次 Casimir 查询；community 首轮两次查询后结束。两者均 4 分。少一轮同时伴随初始调用分组和社区覆盖变化，无法仅凭 trace 分离贡献。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/8e560aa47461455fb666e4345be4f2f4.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/aa5a399bd59c4bd8b735a8916e6d7b12.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] experiments verified existence Casimir force micro nanoscale；全库 | 12 | 9 | 0 | 成功 |
| 2 | search_chunks [hybrid] measured Casimir force microsphere plate separation experiment verification；全库 | 12 | 2 | 0 | 成功 |
| 2 | search_chunks [hybrid] Casimir force measurement nanoscale torsion balance atomic force microscope；全库 | 12 | 2 | 0 | 成功 |

judge 原文：The generated answer accurately captures all three described experiments and their key results, consistent with the gold answer and adding only compatible details.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] experiments verifying Casimir force micro nanoscale；全库 | 12 | 21 | 3 | 成功 |
| 1 | search_chunks [vector] Casimir force measurement experiment verification；全库 | 12 | 22 | 3 | 成功 |

judge 原文：The generated answer accurately captures the key facts of the gold experiments, including the 2017 silicon T-shaped protrusion/comb-actuator measurement and the 2019 Casimir-mediated phonon heat transfer measurement, while adding relevant non-contradictory context.

</details>

<a id="case-shengyan_photonics_5"></a>

### 42. shengyan_photonics_5 — 少一轮但相同关键错误保留

**问题：** Which integrated phononic devices have been realized?

**评分：2→2（Δ+0）；rounds：3→2（Δ-1）。**

工具数 3→2；错误 0→0；文档 overview 14→18；QA tokens 39,240→19,479。

community 省掉一轮器件列表搜索，仍与 naive 一样把偏振转换器归为仅提案/数值验证，并遗漏 beam splitter 等 gold 项，均 2 分。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/3142f1406ae7492ba18375cd6c2ac85b.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/453ee2f569f246a1b58015ed8f707c68.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] integrated phononic devices realized；全库 | 12 | 9 | 0 | 成功 |
| 1 | search_chunks [vector] realization of integrated phononic circuits devices；全库 | 12 | 4 | 0 | 成功 |
| 2 | search_chunks [hybrid] integrated phononic devices have been realized waveguides couplers resonators filters；全库 | 12 | 1 | 0 | 成功 |

judge 原文：The answer correctly includes several realized phononic devices like GaN-on-sapphire waveguides/ring resonators and acoustic modulators, but it omits key gold devices such as the phonon beam splitter and PT-symmetric isolator/circulator, and incorrectly claims the quasi-Rayleigh/Love mode converter was not experimentally realized.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] integrated phononic devices realized；全库 | 12 | 16 | 3 | 成功 |
| 1 | search_chunks [vector] phononic integrated circuit devices demonstrated；全库 | 12 | 2 | 0 | 成功 |

judge 原文：The answer correctly identifies many realized integrated phononic devices, but it wrongly claims the quasi-Rayleigh/quasi-Love polarization converter was only proposed/numerically validated (whereas the gold answer treats it as realized) and omits the realized phonon beam splitter, so it is only partially correct.

</details>

<a id="case-minyang_physics_1"></a>

### 43. minyang_physics_1 — 减少重复搜索和读取恢复

**问题：** What methods can be used to simulate Binary Black Holes in numerical relativity?

**评分：4→4（Δ+0）；rounds：6→3（Δ-3）。**

工具数 12→3；错误 3→0；文档 overview 22→17；QA tokens 180,610→38,698。

naive 共 12 次工具调用，三次越界后又成功读三次 ordinal 0；community 仅三次搜索，6→3 轮，均 4 分。其核心 PN/NR/EOB/phenomenological/surrogate 方法已足够，后续试读对判分没有可见帮助。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/b0eccdc3c0bc47279a144a4db2db327e.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/6845bcbdd69242ce908ffb9d8a35f95c.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] methods to simulate binary black holes numerical relativity；全库 | 12 | 11 | 0 | 成功 |
| 1 | search_chunks [vector] binary black hole simulation techniques numerical relativity；全库 | 12 | 4 | 0 | 成功 |
| 2 | search_chunks [hybrid] numerical relativity simulation methods puncture gauge generalized harmonic binary black hole；全库 | 12 | 0 | 0 | 成功 |
| 2 | search_chunks [vector] post-Newtonian effective one-body numerical relativity matching waveforms binary；全库 | 12 | 0 | 0 | 成功 |
| 3 | search_chunks [keyword] numerical relativity binary black hole simulations methods；全库 | 12 | 5 | 0 | 成功 |
| 3 | search_chunks [hybrid] hybridized numerical relativity waveforms post-Newtonian matching effective one body surrogate；全库 | 12 | 2 | 0 | 成功 |
| 4 | read_chunks doc_id=57f62e3ca61f74ba08c57d0cf5771644ee611847c8b29c505b877a31ca99fd4b ordinals=[0, 1, 2, 3] | 0 | 0 | 0 | Unknown chunk ordinal |
| 4 | read_chunks doc_id=54fa3e3b65f9ef000195392ac955f83a150f0f139c4fdcc9efdbea4e57272485 ordinals=[0, 1] | 0 | 0 | 0 | Unknown chunk ordinal |
| 4 | read_chunks doc_id=de4402695b76a31f0319fa73dbcca72ab4753979255267417b24bc0c9c65cfd9 ordinals=[0, 1] | 0 | 0 | 0 | Unknown chunk ordinal |
| 5 | read_chunks doc_id=57f62e3ca61f74ba08c57d0cf5771644ee611847c8b29c505b877a31ca99fd4b ordinals=[0] | 1 | 0 | 0 | 成功 |
| 5 | read_chunks doc_id=54fa3e3b65f9ef000195392ac955f83a150f0f139c4fdcc9efdbea4e57272485 ordinals=[0] | 1 | 0 | 0 | 成功 |
| 5 | read_chunks doc_id=de4402695b76a31f0319fa73dbcca72ab4753979255267417b24bc0c9c65cfd9 ordinals=[0] | 1 | 0 | 0 | 成功 |

judge 原文：The generated answer accurately captures all the key methods from the gold answers (PN, NR, EOB, phenomenological, surrogates) with correct descriptions and no contradictions.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] simulate binary black holes numerical relativity methods；全库 | 12 | 17 | 2 | 成功 |
| 2 | search_chunks [hybrid] numerical relativity binary black hole simulation technique generalized harmonic BSSN puncture excision；全库 | 12 | 0 | 0 | 成功 |
| 2 | search_chunks [vector] numerical relativity binary black hole evolution method simulation approach；全库 | 12 | 0 | 0 | 成功 |

judge 原文：The generated answer accurately identifies all the key methods from the gold answers—post-Newtonian theory, numerical relativity simulations, effective-one-body formalism, phenomenological waveforms, and NR surrogates—without contradictions or omissions.

</details>

<a id="case-minyang_physics_2"></a>

### 44. minyang_physics_2 — 相同工具数被分散到更多轮

**问题：** What messager are combined in multi-messenger astrophysics approach?

**评分：4→4（Δ+0）；rounds：5→6（Δ+1）。**

工具数 6→6；错误 1→1；文档 overview 20→22；QA tokens 84,228→95,497。

两者都是 6 次调用、一次越界读取、4 分；community 将调用分散到五个工具轮，naive 四个，最终都列 photons/GW/neutrinos/cosmic rays。主要是调用编排及核验路径差异，不是检索工作量增加。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/1abc707ee4c542e9a32fd136cd8dc6fc.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/8e3d3d14f3d340d09ef8bfc7ab44acb5.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] multi-messenger astrophysics messengers combined；全库 | 12 | 9 | 0 | 成功 |
| 2 | read_chunks doc_id=f251c4e5191d4fc447e388fc0a2faa10b37dcf1143fa1ab8a6579c69623cdbd0 ordinals=[0, 1, 2, 3] | 0 | 0 | 0 | Unknown chunk ordinal |
| 2 | search_chunks [hybrid] cosmic rays gravitational waves neutrinos photons messengers combined；全库 | 12 | 5 | 0 | 成功 |
| 3 | search_chunks [hybrid] cosmic rays neutrinos gravitational waves photons messengers；doc_ids=f251c4e5191d | 1 | 0 | 0 | 成功 |
| 3 | search_chunks [hybrid] multi-messenger approach combining electromagnetic waves neutrinos cosmic rays gravitational waves；全库 | 12 | 0 | 0 | 成功 |
| 4 | search_chunks [keyword] messengers gravitational waves neutrinos cosmic rays electromagnetic photons；全库 | 12 | 6 | 0 | 成功 |

judge 原文：The generated answer correctly and completely identifies all four messengers—electromagnetic radiation, neutrinos, cosmic rays, and gravitational waves—matching the gold answer's core meaning.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] multi-messenger astrophysics messengers combined；全库 | 12 | 19 | 2 | 成功 |
| 2 | search_chunks [hybrid] messengers gravitational waves neutrinos cosmic rays electromagnetic；doc_ids=f251c4e5191d | 1 | 0 | 0 | 成功 |
| 3 | read_chunks doc_id=f251c4e5191d4fc447e388fc0a2faa10b37dcf1143fa1ab8a6579c69623cdbd0 ordinals=[1, 2, 3, 4, 5] | 0 | 0 | 0 | Unknown chunk ordinal |
| 4 | search_chunks [hybrid] combination of gravitational waves electromagnetic radiation neutrinos cosmic rays；全库 | 12 | 1 | 0 | 成功 |
| 4 | search_chunks [hybrid] multi-messenger approach combines；doc_ids=06cfb381e342 | 6 | 0 | 0 | 成功 |
| 5 | search_chunks [hybrid] cosmic rays as messenger ultra-high-energy cosmic rays multi-messenger；全库 | 12 | 2 | 0 | 成功 |

judge 原文：The generated answer correctly identifies all four messengers (electromagnetic radiation, gravitational waves, neutrinos, and cosmic rays) as combined in multi-messenger astrophysics, matching the gold answer's core meaning.

</details>

<a id="case-minyang_physics_6"></a>

### 45. minyang_physics_6 — 早停但概念边界未修正

**问题：** What are the ways to perform optomechincal cooling

**评分：3→3（Δ+0）；rounds：3→2（Δ-1）。**

工具数 3→1；错误 0→0；文档 overview 20→46；QA tokens 36,082→22,315。

community 一次搜索带入 46 份 overview 即回答，naive 再查询 sideband/feedback/cryogenic。两者仍将低温制冷与光力冷却的边界混淆而为 3 分；更短路径并不等于消除了错误。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/206674920e6d4de99d428424aac09b65.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/3128f4ac6f3b40798cd34494d2884393.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] ways to perform optomechanical cooling；全库 | 12 | 12 | 0 | 成功 |
| 2 | search_chunks [hybrid] radiation pressure cooling sideband cooling cold damping parametric feedback electrostatic；全库 | 12 | 6 | 0 | 成功 |
| 2 | search_chunks [hybrid] cryogenic refrigeration dilution refrigerator cooling mechanical resonator optomechanical；全库 | 12 | 2 | 0 | 成功 |

judge 原文：The generated answer correctly identifies both feedback cooling and cavity/radiation-pressure cooling as the main optomechanical cooling methods, but it slightly overreaches by listing cryogenic refrigeration as a way to perform optomechanical cooling, which is not one of the gold answer's optomechanical cooling types.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] ways to perform optomechanical cooling；全库 | 12 | 46 | 6 | 成功 |

judge 原文：The generated answer correctly includes the two main optomechanical cooling methods (feedback cooling and cavity/radiation-pressure cooling), but it incorrectly lists cryogenic refrigeration as a way to reach the quantum ground state, which contradicts the gold answer's statement that cryogenic cooling alone is insufficient.

</details>

<a id="case-yanyu_photonics_3"></a>

### 46. yanyu_photonics_3 — 增加有效读取却仍遗漏核心机制

**问题：** How does particle binding to a high-Q optical microcavity induce a resonance shift, and what are the limitations and enhancements required for sensitive single-protein detection using cavity optomechanics?

**评分：2→2（Δ+0）；rounds：2→3（Δ+1）。**

工具数 2→5；错误 0→0；文档 overview 13→64；QA tokens 18,186→64,273。

community 比 naive 多一轮，并成功读取 [0,1] 和 [0]、定向搜索 optomechanical spring；这些不是工具错误。最终仍没写齐 blue-detuned oscillation、频移转换及精度增强等 gold 核心细节，均 2 分。问题是获得证据后是否按问题要点综合，而不只是搜索次数。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/d97c19b0072e474fa9d31de2f9b880bb.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/39f6fd39c3204e4a809dd264715e7948.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] particle binding high-Q optical microcavity resonance shift single-protein detection；全库 | 12 | 11 | 0 | 成功 |
| 1 | search_chunks [hybrid] cavity optomechanics single protein detection limitations enhancement sensitivity；全库 | 12 | 2 | 0 | 成功 |

judge 原文：The answer correctly explains the resonance shift mechanism and some limitations/enhancements, but omits the cavity optomechanics approach that is the central enhancement described in the gold answers.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] particle binding high-Q optical microcavity resonance shift single-protein detection cavity optomechanics；全库 | 12 | 28 | 3 | 成功 |
| 1 | search_chunks [hybrid] limitations enhancements sensitive single-protein detection cavity optomechanics；全库 | 12 | 36 | 5 | 成功 |
| 2 | read_chunks doc_id=f5362d1ea09e62b65422e64b6447a58f9ed1dc16b1fa587ba5328c6f5bc80649 ordinals=[0, 1] | 2 | 0 | 0 | 成功 |
| 2 | read_chunks doc_id=ac941621951ae0ee7fc6e890156db397aed84a7884a99700bc93b683ab93e766 ordinals=[0] | 1 | 0 | 0 | 成功 |
| 2 | search_chunks [hybrid] optomechanical spring sensing single molecule binding shifts mechanical frequency cavity；doc_ids=ac941621951a | 1 | 0 | 0 | 成功 |

judge 原文：The generated answer correctly describes the resonance-shift mechanism and the optomechanical advantage of avoiding a plasmonic antenna, but it omits key cavity-optomechanics details from the gold answer such as blue-detuned optomechanical oscillation, mechanical frequency-shift transduction, Q-dependent resolution scaling, six-orders-of-magnitude enhancement, and the BSA single-molecule demonstration.

</details>

<a id="case-yanyu_photonics_4"></a>

### 47. yanyu_photonics_4 — 额外确认已充分的核心公式

**问题：** How do exceptional points (EPs) in optical resonators enhance the sensitivity of sensors compared to traditional diabolic points (DPs) for detecting nanoparticles and biomolecules?

**评分：4→4（Δ+0）；rounds：2→3（Δ+1）。**

工具数 1→3；错误 0→0；文档 overview 11→55；QA tokens 10,312→56,513。

community 第二工具轮再次搜索 linear vs square-root scaling；naive 一轮工具后已回答正确。两者 4 分，2→3 轮体现保守核验/停止差异，未带来可见评分收益。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/ca74006697694b58b0d9ea229e5139e6.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/6bd5e44f1b814ec698cab8652e2e99e0.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] exceptional points optical resonators sensitivity enhancement diabolic points nanoparticle biomolecule detection；全库 | 12 | 11 | 0 | 成功 |

judge 原文：The generated answer correctly captures the fundamental square-root vs linear scaling at EP vs DP, the resulting sensitivity enhancement for small perturbations, and the applications to nanoparticle and biomolecule detection, consistent with the gold answers.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] exceptional points optical resonators enhance sensitivity sensors compared diabolic points nanoparticles biomolecules；全库 | 12 | 41 | 4 | 成功 |
| 1 | search_chunks [vector] exceptional point EP sensitivity nanoparticle detection diabolic point DP；全库 | 12 | 3 | 0 | 成功 |
| 2 | search_chunks [hybrid] diabolic point exceptional point sensitivity scaling linear square root perturbation；全库 | 12 | 11 | 1 | 成功 |

judge 原文：The generated answer accurately captures the core distinction that EP sensors rely on square-root splitting versus linear DP splitting, yielding greater sensitivity for small perturbations, and correctly relates this to enhanced biosensing, consistent with the gold answers.

</details>

<a id="case-yanyu_photonics_5"></a>

### 48. yanyu_photonics_5 — 反复改写仍未找到/采用核心相衬方案

**问题：** What are the current state of the art in which photonic metamaterial surfaces are utilized to enhance Label-Free Imaging in Phase Contrast Microscopy and Refractometric Microscopy?

**评分：2→2（Δ+0）；rounds：4→5（Δ+1）。**

工具数 6→8；错误 0→0；文档 overview 30→75；QA tokens 84,546→174,609。

community 四个工具轮、8 次搜索，naive 三轮、6 次；community 已获取 75 份 overview，但最终仍漏甚至否定 gold 的 phase-contrast metasurface 方案，两者 2 分。更多概览不保证关键子问题覆盖，应检查目标文献是否存在于节选语料及其具体命中。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/b7e4e87b026c441f87b6e6f9fbd3f16d.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/7ae925fa694f4cb2ac6a4ccb9558b66b.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] photonic metamaterial surface label-free imaging phase contrast microscopy；全库 | 12 | 12 | 0 | 成功 |
| 1 | search_chunks [hybrid] refractometric microscopy metamaterial surface enhancement；全库 | 12 | 7 | 0 | 成功 |
| 2 | search_chunks [hybrid] phase contrast microscopy photonic metamaterial label-free imaging enhancement；全库 | 12 | 1 | 0 | 成功 |
| 2 | search_chunks [hybrid] refractometric imaging metasurface phase contrast label-free；全库 | 12 | 3 | 0 | 成功 |
| 3 | search_chunks [hybrid] phase contrast imaging refractive index sensitivity metamaterial microscopy unstained；全库 | 12 | 4 | 0 | 成功 |
| 3 | search_chunks [hybrid] label-free imaging refractometric biosensing metasurface figure of merit RIU；全库 | 12 | 3 | 0 | 成功 |

judge 原文：The answer is partially correct and includes relevant refractometric metasurface techniques and PCEM/PROM, but it omits the core phase contrast microscopy state-of-the-art (Balaur's silver-coated metasurface ptychographic phase microscopy and Kwon's cascaded metasurface quantitative phase microscope) and misclassifies PCEM/PROM.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] photonic metamaterial surfaces enhance label-free imaging phase contrast microscopy refractometric microscopy；全库 | 12 | 28 | 4 | 成功 |
| 1 | search_chunks [vector] metasurface label-free imaging enhancement phase contrast refractometric；全库 | 12 | 21 | 3 | 成功 |
| 2 | search_chunks [hybrid] phase contrast microscopy metasurface label-free imaging；全库 | 12 | 0 | 0 | 成功 |
| 2 | search_chunks [hybrid] refractometric microscopy photonic crystal metasurface label-free imaging；全库 | 12 | 1 | 0 | 成功 |
| 3 | search_chunks [keyword] metamaterial surface enhance phase contrast refractometric microscopy label-free review；全库 | 12 | 9 | 1 | 成功 |
| 3 | search_chunks [hybrid] "phase contrast" OR "refractometric" microscopy photonic metamaterial surface state of the art；全库 | 12 | 2 | 0 | 成功 |
| 4 | search_chunks [keyword] "phase contrast" microscopy imaging enhancement substrate；全库 | 12 | 12 | 1 | 成功 |
| 4 | search_chunks [hybrid] metasurface enhanced phase imaging quantitative phase label-free；全库 | 12 | 2 | 0 | 成功 |

judge 原文：The generated answer correctly covers several refractometric microscopy advances but incorrectly omits and even denies the phase contrast microscopy applications described in the gold answers, which are a required part of the question.

</details>

<a id="case-yanyu_photonics_8"></a>

### 49. yanyu_photonics_8 — 消除越界与重复定向搜索，但质量上限未突破

**问题：** What are the limitations of usinhg quantitative reverse transcriptase PCR to detect miRNA at a very low concentration?

**评分：2→2（Δ+0）；rounds：8→4（Δ-4）。**

工具数 11→5；错误 2→0；文档 overview 21→38；QA tokens 130,325→67,693。

naive 8 轮含两次越界试读及多次重复定向 query，community 4 轮无工具错误，token 130,325→67,693。两者仍漏酶扩增/引物/偏差等限制而为 2 分；主要收益是减少无效探索，不是回答变正确。

证据：[naive trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_naive_20260920_223851/traces/f22b47938a2445ab8052544576ea2ac4.json) · [community trace](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/runs/scholarqa_first_92_community_20260920_232241/traces/e9f0fd21483f457997ac58312ca5d003.json)。下表轮号为所属 assistant 模型轮。

<details>
<summary>展开两轮工具时序与 judge 理由</summary>


**naive**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] limitations of quantitative reverse transcriptase PCR detecting miRNA low concentration；全库 | 12 | 10 | 0 | 成功 |
| 2 | read_chunks doc_id=61e504fd594cbf7515fc2e7f169032c69cc6b4d4367890802bf49f89bc0e89f5 ordinals=[0, 1, 2, 3, 4] | 0 | 0 | 0 | Unknown chunk ordinal |
| 2 | search_chunks [hybrid] RT-qPCR detection limit low concentration miRNA sensitivity limitations background；全库 | 12 | 5 | 0 | 成功 |
| 3 | read_chunks doc_id=61e504fd594cbf7515fc2e7f169032c69cc6b4d4367890802bf49f89bc0e89f5 ordinals=[2, 3, 4, 5] | 0 | 0 | 0 | Unknown chunk ordinal |
| 4 | search_chunks [hybrid] detection limit low concentration sensitivity qPCR background amplification；doc_ids=61e504fd594c | 2 | 0 | 0 | 成功 |
| 4 | search_chunks [hybrid] limiting amounts input material low concentration detection limitation；doc_ids=ace22422f27d | 1 | 0 | 0 | 成功 |
| 5 | search_chunks [hybrid] RT-qPCR limitations low concentration miRNA detection alternative；doc_ids=651ec53e516c | 2 | 0 | 0 | 成功 |
| 6 | search_chunks [vector] RT-qPCR quantitative limitation low concentration digital single molecule detection why；doc_ids=651ec53e516c | 2 | 0 | 0 | 成功 |
| 6 | read_chunks doc_id=651ec53e516cb64f3a71a7cd8979bc84d515eeb85dd8ffc6dd6a3f59b70b653e ordinals=[0, 1] | 2 | 0 | 0 | 成功 |
| 7 | search_chunks [keyword] RT-qPCR limitation quantitative miRNA low concentration sensitivity insufficient detection；全库 | 12 | 3 | 0 | 成功 |
| 7 | search_chunks [vector] reverse transcription quantitative PCR cannot detect very low abundance miRNA limitation；全库 | 12 | 3 | 0 | 成功 |

judge 原文：The generated answer captures some relevant limitations (RNA isolation and background interference) but omits key gold-standard limitations such as enzymatic amplification, sequence biases, unique primer requirements for short miRNA targets, and failure for small volumes, making it only partially correct.


**community**

| 轮次 | 工具及输入 | chunk 数 | 新增 overview | 新增社区 | 结果 |
|---|---|---:|---:|---:|---|
| 1 | search_chunks [hybrid] limitations of quantitative reverse transcriptase PCR to detect miRNA at very low concentration；全库 | 12 | 33 | 3 | 成功 |
| 2 | search_chunks [hybrid] RT-qPCR miRNA detection low concentration sensitivity limitations background noise；全库 | 12 | 5 | 0 | 成功 |
| 2 | search_chunks [vector] quantitative PCR detecting low abundance miRNA problems detection limit；doc_ids=ace22422f27d,61e504fd594c,651ec53e516c | 5 | 0 | 0 | 成功 |
| 3 | search_chunks [hybrid] qPCR background false positive detection low abundance sensitivity；doc_ids=61e504fd594c | 2 | 0 | 0 | 成功 |
| 3 | search_chunks [hybrid] low amount input material recovery detection limit RT-qPCR efficiency；doc_ids=ace22422f27d | 1 | 0 | 0 | 成功 |

judge 原文：The generated answer correctly identifies some limitations (poor recovery from low input and background/specificity issues), but omits other key limitations from the gold answer, particularly the requirement for enzymatic amplification and labor-intensive processing.

</details>

## 7. 全部 92 题总表

按数据集原始顺序排列；每个变化案例可跳转到详细分析。

| QA ID | score N→C | Δscore | rounds N→C | Δrounds | tools N→C | errors N→C |
|---|---:|---:|---:|---:|---:|---:|
| [norman_bio_1](#case-norman_bio_1) | 4→4 | +0 | 5→2 | -3 | 7→2 | 1→0 |
| [norman_bio_2](#case-norman_bio_2) | 4→3 | -1 | 3→2 | -1 | 4→2 | 1→0 |
| norman_bio_3 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 |
| norman_bio_4 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 |
| norman_bio_5 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 |
| [norman_bio_6](#case-norman_bio_6) | 2→2 | +0 | 5→4 | -1 | 5→5 | 1→1 |
| [norman_bio_7](#case-norman_bio_7) | 4→2 | -2 | 5→3 | -2 | 6→4 | 2→0 |
| [norman_bio_8](#case-norman_bio_8) | 2→2 | +0 | 3→2 | -1 | 4→2 | 0→0 |
| norman_bio_9 | 4→4 | +0 | 2→2 | +0 | 1→1 | 0→0 |
| norman_bio_10 | 4→4 | +0 | 3→3 | +0 | 3→3 | 0→1 |
| [benjamin_bio_1](#case-benjamin_bio_1) | 3→4 | +1 | 2→4 | +2 | 2→4 | 0→1 |
| [benjamin_bio_2](#case-benjamin_bio_2) | 2→2 | +0 | 3→4 | +1 | 3→5 | 1→2 |
| benjamin_bio_3 | 4→4 | +0 | 6→6 | +0 | 8→9 | 1→1 |
| benjamin_bio_5 | 4→4 | +0 | 2→2 | +0 | 2→1 | 0→0 |
| [benjamin_bio_6](#case-benjamin_bio_6) | 3→2 | -1 | 4→4 | +0 | 6→6 | 2→1 |
| [benjamin_bio_7](#case-benjamin_bio_7) | 4→3 | -1 | 5→6 | +1 | 8→9 | 0→1 |
| [benjamin_bio_8](#case-benjamin_bio_8) | 2→2 | +0 | 5→4 | -1 | 7→5 | 2→3 |
| [benjamin_bio_9](#case-benjamin_bio_9) | 0→0 | +0 | 3→2 | -1 | 2→1 | 0→0 |
| [benjamin_bio_10](#case-benjamin_bio_10) | 2→2 | +0 | 3→4 | +1 | 2→4 | 0→0 |
| [akari_cs_1](#case-akari_cs_1) | 4→4 | +0 | 2→5 | +3 | 2→7 | 0→1 |
| akari_cs_2 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 |
| [akari_cs_3](#case-akari_cs_3) | 4→4 | +0 | 3→2 | -1 | 3→2 | 0→0 |
| akari_cs_4 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 |
| akari_cs_5 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 |
| akari_cs_6 | 4→4 | +0 | 2→2 | +0 | 1→2 | 0→0 |
| [akari_cs_7](#case-akari_cs_7) | 2→3 | +1 | 3→4 | +1 | 4→6 | 0→0 |
| akari_cs_8 | 2→2 | +0 | 2→2 | +0 | 1→2 | 0→0 |
| akari_cs_9 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 |
| akari_cs_10 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 |
| [rulin_cs_1](#case-rulin_cs_1) | 4→4 | +0 | 4→3 | -1 | 5→4 | 0→0 |
| [rulin_cs_2](#case-rulin_cs_2) | 4→4 | +0 | 3→2 | -1 | 7→2 | 5→0 |
| rulin_cs_3 | 3→3 | +0 | 3→3 | +0 | 4→4 | 0→0 |
| [weijia_cs_1](#case-weijia_cs_1) | 3→4 | +1 | 3→5 | +2 | 4→8 | 0→0 |
| weijia_cs_3 | 4→4 | +0 | 2→2 | +0 | 2→1 | 0→0 |
| [weijia_cs_4](#case-weijia_cs_4) | 2→4 | +2 | 4→3 | -1 | 5→4 | 2→0 |
| weijia_cs_5 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 |
| [weijia_cs_6](#case-weijia_cs_6) | 2→3 | +1 | 2→2 | +0 | 2→1 | 0→0 |
| weijia_cs_7 | 4→4 | +0 | 2→2 | +0 | 1→1 | 0→0 |
| [weijia_cs_8](#case-weijia_cs_8) | 2→4 | +2 | 2→2 | +0 | 1→1 | 0→0 |
| [weijia_cs_9](#case-weijia_cs_9) | 2→3 | +1 | 2→4 | +2 | 1→4 | 0→2 |
| weijia_cs_10 | 4→4 | +0 | 2→2 | +0 | 1→2 | 0→0 |
| jacqueline_cs_1 | 4→4 | +0 | 2→2 | +0 | 1→2 | 0→0 |
| jacqueline_cs_2 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 |
| [jacqueline_cs_3](#case-jacqueline_cs_3) | 4→3 | -1 | 2→2 | +0 | 2→2 | 0→0 |
| [jacqueline_cs_4](#case-jacqueline_cs_4) | 4→3 | -1 | 2→2 | +0 | 2→2 | 0→0 |
| jacqueline_cs_5 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 |
| [jacqueline_cs_6](#case-jacqueline_cs_6) | 4→4 | +0 | 6→3 | -3 | 8→4 | 1→0 |
| [jacqueline_cs_10](#case-jacqueline_cs_10) | 4→4 | +0 | 6→4 | -2 | 10→6 | 1→1 |
| pan_biophysics_1 | 4→4 | +0 | 2→2 | +0 | 2→1 | 0→0 |
| pan_biophysics_2 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 |
| [pan_biophysics_3](#case-pan_biophysics_3) | 4→4 | +0 | 3→4 | +1 | 4→5 | 1→1 |
| [pan_biophysics_4](#case-pan_biophysics_4) | 4→4 | +0 | 6→5 | -1 | 11→13 | 3→5 |
| pan_biophysics_5 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 |
| pan_biophysics_6 | 4→4 | +0 | 2→2 | +0 | 1→1 | 0→0 |
| pan_biophysics_7 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 |
| pan_biophysics_8 | 4→4 | +0 | 2→2 | +0 | 1→2 | 0→0 |
| pan_biophysics_9 | 3→3 | +0 | 2→2 | +0 | 1→2 | 0→0 |
| shengyan_photonics_1 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 |
| [shengyan_photonics_2](#case-shengyan_photonics_2) | 4→4 | +0 | 3→2 | -1 | 3→2 | 0→0 |
| [shengyan_photonics_3](#case-shengyan_photonics_3) | 2→4 | +2 | 2→3 | +1 | 1→3 | 0→0 |
| [shengyan_photonics_4](#case-shengyan_photonics_4) | 3→4 | +1 | 2→2 | +0 | 1→2 | 0→0 |
| [shengyan_photonics_5](#case-shengyan_photonics_5) | 2→2 | +0 | 3→2 | -1 | 3→2 | 0→0 |
| shengyan_photonics_6 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 |
| shengyan_photonics_7 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 |
| [shengyan_photonics_8](#case-shengyan_photonics_8) | 2→3 | +1 | 2→2 | +0 | 1→2 | 0→0 |
| shengyan_photonics_9 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 |
| [shengyan_photonics_10](#case-shengyan_photonics_10) | 4→2 | -2 | 3→2 | -1 | 4→2 | 1→0 |
| [minyang_physics_1](#case-minyang_physics_1) | 4→4 | +0 | 6→3 | -3 | 12→3 | 3→0 |
| [minyang_physics_2](#case-minyang_physics_2) | 4→4 | +0 | 5→6 | +1 | 6→6 | 1→1 |
| [minyang_physics_3](#case-minyang_physics_3) | 4→3 | -1 | 7→2 | -5 | 12→2 | 3→0 |
| minyang_physics_4 | 2→2 | +0 | 6→6 | +0 | 10→9 | 2→2 |
| [minyang_physics_5](#case-minyang_physics_5) | 3→4 | +1 | 4→3 | -1 | 5→2 | 2→0 |
| [minyang_physics_6](#case-minyang_physics_6) | 3→3 | +0 | 3→2 | -1 | 3→1 | 0→0 |
| [hao_photonics_1](#case-hao_photonics_1) | 4→2 | -2 | 3→3 | +0 | 3→3 | 0→0 |
| hao_photonics_2 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 |
| [hao_photonics_3](#case-hao_photonics_3) | 2→4 | +2 | 2→2 | +0 | 1→2 | 0→0 |
| [hao_photonics_4](#case-hao_photonics_4) | 2→3 | +1 | 2→2 | +0 | 2→2 | 0→0 |
| hao_photonics_5 | 4→4 | +0 | 2→2 | +0 | 1→2 | 0→0 |
| hao_photonics_6 | 2→2 | +0 | 2→2 | +0 | 1→1 | 0→0 |
| hao_photonics_7 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 |
| hao_photonics_8 | 3→3 | +0 | 2→2 | +0 | 2→1 | 0→0 |
| [hao_photonics_9](#case-hao_photonics_9) | 2→4 | +2 | 2→2 | +0 | 1→1 | 0→0 |
| [hao_photonics_10](#case-hao_photonics_10) | 3→4 | +1 | 2→2 | +0 | 2→2 | 0→0 |
| [yanyu_photonics_1](#case-yanyu_photonics_1) | 2→3 | +1 | 2→2 | +0 | 2→2 | 0→0 |
| yanyu_photonics_2 | 4→4 | +0 | 2→2 | +0 | 2→2 | 0→0 |
| [yanyu_photonics_3](#case-yanyu_photonics_3) | 2→2 | +0 | 2→3 | +1 | 2→5 | 0→0 |
| [yanyu_photonics_4](#case-yanyu_photonics_4) | 4→4 | +0 | 2→3 | +1 | 1→3 | 0→0 |
| [yanyu_photonics_5](#case-yanyu_photonics_5) | 2→2 | +0 | 4→5 | +1 | 6→8 | 0→0 |
| yanyu_photonics_6 | 4→4 | +0 | 2→2 | +0 | 1→1 | 0→0 |
| yanyu_photonics_7 | 4→4 | +0 | 2→2 | +0 | 1→1 | 0→0 |
| [yanyu_photonics_8](#case-yanyu_photonics_8) | 2→2 | +0 | 8→4 | -4 | 11→5 | 2→0 |
| yanyu_photonics_9 | 2→2 | +0 | 2→2 | +0 | 2→2 | 0→0 |

## 8. 复核与产物

- 本报告读取 184 份 trace，校验每份 assistant 消息数等于结果中的 rounds；共解析 572 个工具调用/返回。
- 原始实验文件未更改。所有统计均由已保存数据计算，没有新的模型或 judge 消耗。
- [结构化逐题 trace 分析数据](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/trace_comparison.json)。
- [报告生成脚本（含逐题人工分析）](/Users/yunhaoz/Developer/MyProjects/community_wiki/data/analysis/build_trace_report.py)。