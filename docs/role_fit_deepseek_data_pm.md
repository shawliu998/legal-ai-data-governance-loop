# 为什么这个项目适合专业领域数据产品经理岗位

我做这个项目时，起点不是“做一个法律模型排行榜”。最开始只是想验证法律 AI 在一些真实产品场景里会怎么出错：事实没问全时会不会直接下结论，引用依据时会不会越界，高风险问题会不会转人工，对抗性文书会不会被模型顺手写出来。

做下去以后，我发现更有价值的部分不是单次评分，而是把这些错误整理成后续能继续使用的数据。比如一个过度自信的劳动争议回答，可以进入 human review；一个引用越界的 RAG 输出，可以变成 source-boundary regression case；一个更安全的回答和一个更冒进的回答，可以做成 preference pair。

这个过程和专业领域数据产品经理的工作有直接关系：需要理解业务场景，定义数据标准和评测口径，安排人审和质检，判断哪些问题影响发布，再把 badcase 分到下一轮 eval、SFT、preference、regression 或 human review 数据里。

项目里已经完成的部分包括：

- 50-case legal product-boundary eval bank，覆盖咨询、案情分析、文书起草、引用 grounding、风险校准和对抗性请求。
- 300 条真实 Qianfan API model-agent 输出，并完成 300 / 300 Qwen judge 结构化解析。
- 80 条 priority 输出人审校准；这个样本是高风险 / blocker 富集样本，所以我只把 92.5% agreement 作为该样本上的校准信号。
- 72-output RAG V2 focused pilot，用来观察 source-boundary、citation coverage 和 claim-level citation gate。
- 24-trace / 72-turn A5 multi-turn intake pilot，用来观察多轮 intake 里的事实追问、错误前提挑战、overclaim 和人审时机。
- release gate、human review queue、data routing、dashboard、redacted evidence package 和 model boundary memo。

如果放到真实团队里，我会优先补三件事。第一，把 priority review 和随机抽样 review 分开，避免把富集样本结论误读成整体准确率。第二，把 RAG 的 claim-to-source 标注做得更细，尤其是 out-of-scope source 和 unsupported claim。第三，把线上 badcase、人工客服记录、检索日志和 release gate 结果接到同一个数据流里，方便持续补 eval、SFT、preference 和 regression 数据。

我不会把这个项目说成完整法律知识库，也不会说它能判断哪个模型更强。它更像一个小规模的产品诊断样例：从场景拆解，到评测和人审，再到发布判断和下一轮数据生产。
