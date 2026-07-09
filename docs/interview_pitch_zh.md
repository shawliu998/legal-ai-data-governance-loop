# 中文面试讲法

## 简短说法

我做的是一个法律 AI 评测和数据整理项目。最开始是从法律评测论文得到启发，但做下来发现，单纯给模型打分不够。法律场景更需要知道模型什么时候不能直接答，什么时候要追问、引用来源、转人工，失败样本后面怎么继续用。

这个项目目前有 300 条真实 Qianfan API 输出、80 条 priority 人审样本、72 条 RAG V2 输出，以及 24 条 A5 多轮 intake trace。最后我把问题样本分到 human review、badcase、regression、SFT 或 preference 数据里，并用 release gate 记录哪些情况不能直接放行。

## 稍微展开

法律 AI 有些错误不是“回答不流畅”，而是看起来很像正确答案。比如事实还没问清就给劳动争议结论，source-limited RAG 里引用了允许材料之外的来源，或者在催收、起诉状、交通事故这类场景里给了过强的行动建议。

所以我把评测拆成几个产品问题：这条能不能直接答，事实够不够，是否需要检索，引用是否支持关键结论，是否要人审，是否触发 release gate。每条输出最后还会有一个数据用途，比如 eval、SFT、preference、badcase、regression 或 human_review。

项目主线包括 50-case 法律产品边界样本、300 条真实模型输出、80 条 priority 人审、RAG V2 focused pilot 和 A5 multi-turn intake pilot。这里面的数字我会按 pilot 来讲，不会说成统计显著 benchmark。

## 我会重点讲的例子

RAG V2 里，检索命中不是最终目标。W4/RAG retrieval 的 expected-source recall 是 100%，但 average source-boundary precision 是 0.50，说明检索能找到目标来源，同时也可能带入不该用的额外来源。所以我会把 source-boundary、citation coverage 和 claim-level support 分开看。

A5 多轮 intake 里，我不会只看最后一句回答。24 traces / 72 turns 里有 6 条 overclaim-flagged traces，这些不是直接定性为法律错误，而是优先进入 human review。这个例子能说明多轮法律 intake 要看整条 trace：追问、错误前提挑战、结论强度和转人工时机。

80 条 priority 人审样本也需要说明边界。它是高风险 / blocker 富集样本，92.5% judge-human agreement 只能作为这个样本上的校准信号，不能包装成整体 judge 准确率。

## 被追问时怎么答

**PLawBench 给了什么启发？**

它让我意识到法律评测不能只看通用问答分数，要把事实、规则、推理、引用和风险拆开看。但我没有复现 PLawBench，重点是把这种拆分接到人审、release gate 和后续数据生产。

**为什么要做人审？**

LLM judge 可以先做结构化筛查，但高风险法律建议、引用支持、是否转人工这些问题需要人工校准。人审的作用不是装饰，而是纠正 judge 和产品路由。

**这个项目和数据产品有什么关系？**

它不只是跑 API。里面有场景拆解、数据字段、rubric、人审队列、release gate、dashboard 和 badcase routing。每个失败样本都要决定下一步去哪类数据，而不是只记一个分数。

**如果继续做，会先补什么？**

我会先补更完整的人审标注，区分 priority review 和随机抽样 review；再把 claim-to-source 标注做细；最后把线上 badcase、人工客服记录、检索日志和模型输出接进同一套数据生产流程。
