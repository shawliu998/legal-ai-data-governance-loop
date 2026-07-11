# 面试里可以怎么讲

## 30 秒

我做了一个法律 AI 评测和数据整理项目。最开始是受法律评测论文启发，但后来发现只给模型打分不够，真正有用的是看模型在哪些场景不该直接回答，以及这些失败样本后面怎么继续用。

项目里有 300 个千帆 API run records，其中 271 条非空回答、29 条空响应；另有 80 条 priority review、72 个 RAG API runs 和 24 条多轮 intake traces。最后我把“当前回答怎么处理”“复核进行到哪一步”和“复核后可能形成什么数据资产”分开记录。

## 90 秒

这个项目关注的是法律 AI 的产品边界。比如用户问劳动争议、催收文书、合同条款或交通事故时，模型不一定应该马上给结论。有些问题需要先追问事实，有些必须限制在指定来源里回答，有些要转人工，有些应该直接被发布门槛拦住。

我先做了一组 50-case 的法律场景样本，覆盖咨询、案情分析、文书起草、引用 grounding、
风险校准和对抗性请求。然后按 12 cases × 5 千帆托管模型槽位 × 5 workflows 跑了 300 个
API runs；其中 271 条有非空回答、29 条为空。两名法律背景 reviewer 对 80 条 priority
记录独立复核并归并分歧，但因为公开证据未保留 reviewer A/B 标签，我不报告无法复算的
一致率。

后面我又单独做了两个更细的方向。一个是 8 cases × 3 模型槽位 × 3 workflows 的 72-run RAG V2 pilot，看引用是不是在允许来源里、关键 claim 有没有支持。另一个是 8 cases × 3 模型槽位的 24-trace / 72-turn A5 pilot，先验证多轮日志和 trace 评测框架；质量标签还要人工校准。

我最后整理的不是“哪个模型排第一”，而是哪些记录应该先进入 human review，哪些经复核后可成为 regression case，哪些在有正确目标答案或安全对照后可形成 SFT 或 preference 数据，哪些必须作为 release blocker 保留。

## 3 分钟

我一开始是从 PLawBench 这类法律评测工作得到启发，想看看法律 AI 在实践场景里怎么评。但做的时候很快发现，如果只停在模型分数，离产品决策还有距离。

法律场景里有些错误不是“答错一道题”这么简单。比如用户问“公司调岗降薪，我能不能
明天直接不去上班”，模型如果顺着给行动建议，可能会让用户承担旷工风险。再比如
source-limited RAG 任务，模型引用了一个看起来合理但不在允许材料里的来源，这种答案
看起来有依据，其实不能直接放行。

所以我把评测拆成几个问题：这条能不能直接答，事实够不够，是否需要检索，引用是否支持关键结论，是否要人审，是否触发 release gate。复核后再决定它是否成为 eval、SFT、preference、badcase 或 regression 候选；human review 是工作流，不是训练数据用途。

目前完成的证据包括：300 个 product-boundary API runs（271 条非空、29 条空响应）、80 条
priority review、72 个 RAG V2 API runs，以及 24 条 A5 traces / 72 turns。这里面我会特别
强调边界：80 条人审是高风险 / blocker 富集样本，不是随机总体；A5 的 deterministic
flags 尚未逐条人审，所以不当成 pass rate 或法律正确性。

如果进团队继续做，我会把这个方法接到真实业务日志里。线上用户反馈、人工客服记录、
检索日志、模型输出和 release gate 结果都应该回到同一个处置流里：高风险记录先人审，
复核后再进入 eval、SFT、preference、badcase 或 regression。这样评测结果才不会只是报告，
而是能持续改数据。

## 面试官可能追问

**PLawBench 给了你什么启发？**

它让我意识到法律评测不能只做通用问答，要把事实、规则、推理、引用和风险拆开看。但我的项目没有复现 PLawBench；外部 adapted practice pilot 也因仓库缺少可复核 license metadata 而不作为核心证据。主线是自建 product-boundary cases 如何接到人审、release gate 和数据生产。

**为什么要做人审？**

LLM judge 可以先做结构化筛查，但法律场景里有些判断必须人工看，尤其是高风险、引用支持、是否转人工这些问题。这个项目里 80 条 priority review 用于校准流程，不是随机总体；公开证据也不足以复算 reviewer-level 一致率。

**RAG 部分说明了什么？**

RAG 找到来源只是第一步。更关键的是回答有没有只使用允许来源，关键 claim 有没有 citation，citation 是否真的支持 claim。RAG V2 的作用就是把这些问题拆出来。

**这个项目和数据产品经理有什么关系？**

它不是只写 prompt 或跑 API。里面有场景拆解、数据字段设计、rubric、human review、release gate、dashboard 和 badcase routing。最后每个失败样本都要决定后续去哪类数据，而不是只记一个分数。

**如果继续做，你会先补什么？**

我会先补更完整的人审标注，区分 priority review 和随机抽样 review；然后加强 claim-to-source 标注；最后把线上 badcase 接入 eval、SFT、preference 和 regression 数据生产。
