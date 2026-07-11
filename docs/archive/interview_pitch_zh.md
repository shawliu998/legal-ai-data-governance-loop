# 中文面试讲法

## 简短说法

我做的是一个法律 AI 评测和数据整理项目。最开始是从法律评测论文得到启发，但做下来发现，单纯给模型打分不够。法律场景更需要知道模型什么时候不能直接答，什么时候要追问、引用来源、转人工，失败样本后面怎么继续用。

当前准确口径是 300 个千帆 API run records，其中 271 条非空回答、29 条空响应；另有 80 条 priority review、72 个 RAG API runs，以及 24 条 A5 traces / 72 turns。human review 是工作流，复核后再决定数据资产候选。

## 稍微展开

法律 AI 有些错误不是“回答不流畅”，而是看起来很像正确答案。比如事实还没问清就给劳动争议结论，source-limited RAG 里引用了允许材料之外的来源，或者在催收、起诉状、交通事故这类场景里给了过强的行动建议。

所以我把评测拆成几个产品问题：这条能不能直接答，事实够不够，是否需要检索，引用是否支持关键结论，是否要人审，是否触发 release gate。复核后再决定 eval、SFT、preference、badcase 或 regression 候选。

项目主线包括 50-case 法律产品边界样本、300-run API pilot（271 条非空、29 条空响应）、80 条 priority review、72-run RAG V2 pilot 和 24-trace A5 pilot。这里面的数字按 pilot 来讲，不说成统计显著 benchmark。

## 我会重点讲的例子

RAG V2 里，检索命中不是最终目标。V4/A2 RAG retrieval 的 expected-source recall 是 100%，但 average source-boundary precision 是 0.50，说明检索能找到目标来源，同时也可能带入不该用的额外来源。所以我会把 source-boundary、citation coverage 和 claim-level support 分开看。

A5 多轮 intake 里，我不会只看最后一句回答。24 traces / 72 turns 的 deterministic flags 还没有逐条人审，因此不报告 pass rate 或模型比较；它们只用于安排 trace review 优先级。

80 条 priority review 也需要说明边界。两名法律背景 reviewer 独立标注并归并分歧；由于公开证据没有 reviewer A/B 标签，本版本不报告一致率、法律正确率或总体准确率。

## 被追问时怎么答

**PLawBench 给了什么启发？**

它让我意识到法律评测不能只看通用问答分数，要把事实、规则、推理、引用和风险拆开看。但我没有复现 PLawBench，重点是把这种拆分接到人审、release gate 和后续数据生产。

**为什么要做人审？**

LLM judge 可以先做结构化筛查，但高风险法律建议、引用支持、是否转人工这些问题需要人工校准。人审的作用不是装饰，而是纠正 judge 和产品路由。

**这个项目和数据产品有什么关系？**

它不只是跑 API。里面有场景拆解、数据字段、rubric、人审队列、release gate、dashboard 和 badcase routing。每个失败样本都要决定下一步去哪类数据，而不是只记一个分数。

**如果继续做，会先补什么？**

我会先补更完整的人审标注，区分 priority review 和随机抽样 review；再把 claim-to-source 标注做细；最后把线上 badcase、人工客服记录、检索日志和模型输出接进同一套数据生产流程。
