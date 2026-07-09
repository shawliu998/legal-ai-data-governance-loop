# 面试里可以怎么讲

## 30 秒

我做了一个法律 AI 评测和数据整理项目。最开始是受法律评测论文启发，但后来发现只给模型打分不够，真正有用的是看模型在哪些场景不该直接回答，以及这些失败样本后面怎么继续用。

项目里有 300 条真实 API 输出、80 条人审样本、一个 RAG citation/source-boundary pilot，还有 24 条多轮 intake trace。最后我把问题样本分到 human review、badcase、regression、SFT 或 preference 数据里，同时用 release gate 记录哪些情况不能直接放行。

## 90 秒

这个项目关注的是法律 AI 的产品边界。比如用户问劳动争议、催收文书、合同条款或交通事故时，模型不一定应该马上给结论。有些问题需要先追问事实，有些必须限制在指定来源里回答，有些要转人工，有些应该直接被发布门槛拦住。

我先做了一组 50-case 的法律场景样本，覆盖咨询、案情分析、文书起草、引用 grounding、风险校准和对抗性请求。然后跑了 300 条真实 Qianfan API model-agent 输出，用 judge 做结构化评分，再抽了 80 条 priority 输出做人审校准。

后面我又单独做了两个更细的方向。一个是 72-output RAG V2 pilot，看引用是不是在允许来源里、关键 claim 有没有支持。另一个是 24-trace / 72-turn A5 多轮 intake pilot，看模型在多轮对话里有没有追问关键事实、挑战错误前提、控制 overclaim 和及时转人工。

我最后整理的不是“哪个模型排第一”，而是哪些失败样本应该进入 human review，哪些应该变成 regression case，哪些可以做 SFT 或 preference 数据，哪些应该作为 release blocker 留下来。

## 3 分钟

我一开始是从 PLawBench 这类法律评测工作得到启发，想看看法律 AI 在实践场景里怎么评。但做的时候很快发现，如果只停在模型分数，离产品决策还有距离。

法律场景里有些错误不是“答错一道题”这么简单。比如用户问“公司调岗降薪，我能不能明天直接不去上班”，模型如果顺着给行动建议，可能会让用户承担旷工风险。再比如 source-limited RAG 任务，模型引用了一个看起来合理但不在允许材料里的来源，这种答案看起来有依据，其实不能直接放行。

所以我把评测拆成几个问题：这条能不能直接答，事实够不够，是否需要检索，引用是否支持关键结论，是否要人审，是否触发 release gate。每条输出最后还会有一个数据用途，比如 eval、SFT、preference、badcase、regression 或 human_review。

目前完成的证据包括：300 条真实 Qianfan API 输出，80 条 priority 人审样本，72 条 RAG V2 输出，以及 24 条 A5 多轮 intake trace。这里面我会特别强调边界：80 条人审是高风险 / blocker 富集样本，不是随机总体；A5 的 trace pass 也是 deterministic triage，不是法律正确性结论。

如果进团队继续做，我会把这个方法接到真实业务日志里。线上用户反馈、人工客服记录、检索日志、模型输出和 release gate 结果都应该回到同一个 badcase 流里，再按用途分到评测、训练、偏好、人审或回归测试。这样评测结果才不会只是报告，而是能持续改数据。

## 面试官可能追问

**PLawBench 给了你什么启发？**

它让我意识到法律评测不能只做通用问答，要把事实、规则、推理、引用和风险拆开看。但我的项目没有复现 PLawBench，重点是把这种拆分方法接到人审、release gate 和后续数据生产。

**为什么要做人审？**

LLM judge 可以先做结构化筛查，但法律场景里有些判断必须人工看，尤其是高风险、引用支持、是否转人工这些问题。这个项目里 80 条 priority 输出就是为了校准 judge 和产品路由，不是为了声称整体准确率。

**RAG 部分说明了什么？**

RAG 找到来源只是第一步。更关键的是回答有没有只使用允许来源，关键 claim 有没有 citation，citation 是否真的支持 claim。RAG V2 的作用就是把这些问题拆出来。

**这个项目和数据产品经理有什么关系？**

它不是只写 prompt 或跑 API。里面有场景拆解、数据字段设计、rubric、human review、release gate、dashboard 和 badcase routing。最后每个失败样本都要决定后续去哪类数据，而不是只记一个分数。

**如果继续做，你会先补什么？**

我会先补更完整的人审标注，区分 priority review 和随机抽样 review；然后加强 claim-to-source 标注；最后把线上 badcase 接入 eval、SFT、preference 和 regression 数据生产。
