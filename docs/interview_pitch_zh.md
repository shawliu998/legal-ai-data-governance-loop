# 中文面试讲稿

## 30 秒版本

我做的是一个法律 AI 产品边界评测与数据治理系统，不是单纯模型排行榜。

核心问题是：法律 AI 在什么场景可以回答，什么场景应该先追问，什么场景必须用 RAG，什么场景要转人工或直接阻断发布。项目用真实法律任务 slice、不同模型和不同 agent 架构跑真实 API 输出，再把失败样本路由成 eval、SFT、preference、badcase、regression eval 和 human review 数据资产。

最终产出不是“哪个模型分最高”，而是模型路由策略、RAG 使用边界、人审策略、release gate 和下一轮数据生产计划。

## 3 分钟版本

这个项目一开始解决的是一个产品问题：法律 AI 不能只看平均分。一个模型回答得很流畅，但仍然可能编造引用、过度承诺胜诉概率、忽略关键事实、没有转人工，或者在 RAG 场景里引用了不该用的来源。

所以我把评测设计成产品上线决策实验，而不是排行榜。每条输出都要回答六个问题：

- 模型能不能回答？
- 产品上应不应该回答？
- 事实不足时是否应该先追问？
- 是否必须使用 grounded sources？
- 是否应该进入人审？
- 失败样本应该变成什么数据资产？

实验主线包括四部分：

1. 50 个法律产品边界 case，覆盖普通咨询、复杂推理、风险校准、引用 grounding、对抗陷阱和 counterfactual pair。
2. 真实 Qianfan API pilot：12 个 case、5 个模型、5 类 workflow，生成 300 条真实模型输出。
3. RAG V2 focused pilot：72 条真实输出，单独评估检索命中、source-boundary、citation coverage 和 claim-level citation gate。
4. A5 multi-turn intake pilot：8 个多轮法律 intake case，3 个模型，24 条 trace / 72 turns，评估模型是否能在多轮中追问关键事实、挑战错误前提、控制 overclaim 并转人工。

我还做了 80 条 priority 输出的人审校准。这个样本不是随机样本，而是偏向高风险、citation issue、release blocker 的审阅样本，所以我只把 92.5% judge-human agreement 表述为 priority-enriched sample 上的一致率，不把它包装成整体 judge 准确率。

## 关键结果

| 结果                                |                           数字 |
| ----------------------------------- | -----------------------------: |
| 真实模型输出                        |                            300 |
| Qwen judge parse success            |                      300 / 300 |
| 人审 priority outputs               |                             80 |
| 人审 pass / partial / fail          |                    4 / 27 / 49 |
| priority 样本 judge-human agreement |                          92.5% |
| RAG V2 输出                         |                             72 |
| RAG V2 citation-gate issue rate     | 88.1% strict release-risk gate |
| A5 full pilot                       |           24 traces / 72 turns |
| A5 deterministic trace pass rate    |                          75.0% |
| A5 overclaim-flagged traces         |                              6 |

## 产品结论

低风险、非引用依赖的普通咨询，可以考虑 A1 structured legal counsel，在 limited release gate 下回答。

事实不足、用户依赖性强、策略性问题或高风险法律问题，应该优先使用 A4 clarification-first 或 A5 multi-turn intake，而不是直接给最终结论。

涉及合同、法条、案例、政策片段或 source-specific claim 的任务必须使用 RAG，但 RAG 命中来源不等于可上线。RAG V2 显示，即使 expected-source recall 是 100%，仍然会出现 source-boundary、missing citation 和 unsupported claim 问题，所以 RAG 输出必须经过 claim-level citation gate 和 source-boundary verification。

对抗性文书、虚假事实、威胁曝光、过度承诺胜诉概率、编造引用、unsupported claim，应该进入 human review 或直接 block release。

## 我会主动承认的限制

RAG 语料库还是 controlled corpus，不是完整法律知识库。它的价值是验证方法和暴露 source-boundary 风险，不是证明覆盖了全部法律知识。

Claim entailment 目前是 deterministic triage，不是最终法律支持性判断。它适合做 release-risk gate 和人审优先级，不适合直接当成法律结论。

Full-run judge 主要用 Qwen3.5-27B，是因为它在 300 条输出里 JSON 稳定性最好。这个选择有工程合理性，但存在 single-judge 和 self-judge bias，所以结果页明确写成 Qwen judge baseline，并用人审和 ensemble smoke 做校准。

A5 的 75.0% pass rate 仍然是 deterministic trace check，不是人审后的法律正确性。下一步应该用 A5 rubric 审完 24 条 trace，尤其是 6 条 overclaim-flagged trace。

API 样本量是 pilot scale，足够展示产品方法和数据闭环，但不能包装成统计显著的大规模 benchmark。

## 面试官追问时的回答

**为什么不是普通 benchmark？**

因为普通 benchmark 只回答“哪个模型分高”。这个项目回答的是“什么模型和 agent 架构可以在什么法律场景上线，以及失败样本如何进入下一轮数据生产”。

**为什么 RAG 结果看起来问题很多？**

这是有意设计的 strict release-risk gate。法律产品不能只看答案相关性，必须看 material claim 是否有允许来源支持。88.1% 不是整体错误率，而是 citation gate 把需要修复、人审或进入数据生产的 claim 暴露出来。

**为什么用 Qwen 做 judge？**

因为在当前 Qianfan pilot 里，Qwen3.5-27B 的结构化 JSON 输出稳定性最好，300 / 300 parse success。但我没有把它当成最终权威 judge，而是明确写成 baseline，并用 priority human review 和 ensemble smoke 缓解偏差。

**这个项目最像数据产品经理的部分是什么？**

不是调用 API，而是把模型输出转化成产品策略和数据策略：auto-answer、RAG required、clarification required、human review、blocked release，以及 eval/SFT/preference/badcase/regression 的数据路由。

## 收尾一句话

我的核心判断是：法律 AI eval 不应该停在“模型 A 86 分、模型 B 83 分”。真正对产品有价值的是明确模型边界、上线门槛、人审策略和下一轮数据生产闭环。这个项目就是把这套闭环跑通。
