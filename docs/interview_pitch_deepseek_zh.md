# DeepSeek 面试讲法：法律 AI 数据产品与治理系统

## 30 秒版本

我做的是一个法律 AI 数据产品与治理系统，不是单纯 benchmark。核心问题不是“哪个模型平均分最高”，而是法律 AI 在什么场景可以自动回答，什么场景要先追问、使用 RAG、转人工或阻断发布。

项目跑通了 300 条真实 Qianfan API model-agent 输出、80 条 priority 输出人审、72 条 RAG V2 focused pilot，以及 24-trace / 72-turn A5 多轮 intake pilot。最后产出 release gate、badcase routing、人审策略和下一轮 eval / SFT / preference / regression / human review 数据生产方案。

## 90 秒版本

这个项目的定位是法律 AI 数据产品与治理系统。它受 PLawBench 等 rubric-based legal evaluation 方法启发，但我没有把它做成论文复现或公开模型排行榜，而是把评测接到了产品发布和数据生产。

我先设计 50-case product-boundary eval bank，覆盖法律咨询、案情分析、文书起草，以及 normal practice、hard reasoning、risk calibration、citation grounding、adversarial trap 和 counterfactual pair 等 slice。然后用 A0-A5 的 agent 架构去看不同产品策略：直接回答、结构化法律建议、RAG grounding、verifier-router、clarification-first 和 multi-turn intake。

真实 pilot 包括 300 条 Qianfan API 输出、80 条 priority 人审、72 条 RAG V2 输出和 24 条 A5 多轮 trace。最后我关注的不是模型排名，而是哪些输出可以 limited release，哪些要 human review，哪些要 blocked release，以及每个失败样本应该进入 eval、SFT、preference、badcase、regression 还是 human_review。

## 3 分钟版本

我这个项目一开始就不是按“法律 LLM benchmark”来做的，而是按“专业领域 AI 数据产品”来做的。法律 AI 的关键风险是：模型可能回答得很流畅，但事实没问全、引用不受支持、RAG 使用了不该用的来源、对胜诉概率过度承诺，或者高风险场景没有转人工。

所以我把评测对象从“单条答案分数”扩展成“产品决策链路”。每条输出都要判断：能不能回答、应不应该回答、是否需要先追问、是否需要 RAG、引用是否在 source boundary 内、是否应该人审、是否触发 release blocker，以及失败样本要变成什么数据资产。

项目主线有四层证据。第一层是 50-case product-boundary eval bank。第二层是 12-case 真实 Qianfan API pilot，覆盖 5 个模型和 5 类 agent workflow，共 300 条真实输出，并完成 300 / 300 Qwen judge 结构化解析。第三层是 80 条 priority 输出人审，在高风险 / blocker 富集样本上记录 92.5% judge-human agreement。第四层是两个更贴近产品风险的扩展：72-output RAG V2 focused pilot 和 24-trace / 72-turn A5 multi-turn intake pilot。

RAG V2 的重点是说明 retrieval 命中不等于可发布。它检查 expected-source recall、source-boundary precision、citation coverage 和 claim-level release blocker。A5 的重点是说明法律 intake 不能只看最后一句答案，而要看整个 trace：是否追问关键事实、是否挑战错误前提、是否控制 overclaim、是否及时转人工。

最终产出是数据标准、dashboard 证据包、release gate、人审策略、模型边界 memo、badcase
routing 和下一轮数据生产计划。这个叙事更接近 DeepSeek 或类似团队里的专业领域数据产品经理：把需求拆解、领域知识、评测、标注、人审、训练数据和产品发布门槛连成闭环。

## 为什么不是单纯 benchmark？

因为 benchmark 通常回答“哪个模型得分更高”，而这个项目回答的是“哪个模型-agent 架构在什么法律场景下可以被产品使用”。它不把 Qwen judge 分数包装成最终模型排名，也不声称 pilot scale 结果具有统计显著性。

项目里的核心动作是产品化的：auto-answer、clarification required、RAG required、human review、blocked release、data routing。失败样本不会只停留在报表里，而是进入 eval、SFT、preference、badcase、regression 或 human_review。

## PLawBench 给了你什么启发？

PLawBench 这类工作给我的主要启发是 rubric-based legal evaluation：法律评测不能只做通用问答打分，而要把法律任务拆成可审查的维度，例如事实、规则、推理、引用、风险和边界。

但我的项目不是 PLawBench 复现。我的重点是把这种 rubric 思路接到数据产品闭环：真实模型输出、人审校准、release gate、badcase routing、RAG source-boundary 检查，以及下一轮 eval / SFT / preference / regression / human review 数据生产。

## 这个项目如何体现数据产品经理能力？

它体现的是从问题定义到数据闭环的完整链路：

- 定义专业领域产品问题：法律 AI 什么时候可以回答、追问、检索、转人工或阻断发布。
- 设计数据标准：50-case eval bank、任务 slice、gold labels、rubric items、leakage-safe 数据分层、normalized run logs 和 data route 字段。
- 组织真实 pilot：300 条真实 Qianfan API 输出、RAG V2 focused pilot、A5 multi-turn intake pilot。
- 接入人审校准：80 条 priority outputs 人审，并明确 priority-enriched sample 的适用边界。
- 制定发布策略：把 fabricated citation、unsupported claim、out-of-scope source、missed escalation 等映射为 release gate。
- 产出决策材料：dashboard、redacted evidence package、release gate summary 和 model boundary memo。
- 规划下一轮数据生产：把失败样本路由到 eval、SFT、preference、badcase、regression 和 human_review。

## 如果进 DeepSeek，你会怎么继续做？

我会优先把这个方法扩展成可复用的专业领域数据治理机制，而不是只做一次性评测。

第一步是和业务、模型、标注、法务或领域专家一起定义场景边界：哪些任务可自动化，哪些必须人审，哪些直接拒答或安全转向。

第二步是建立数据闭环：线上 badcase、用户反馈、人工客服记录、检索日志、模型输出和 release gate 结果统一进入数据路由，分别生成 eval holdout、SFT 样本、preference pair、regression case 和 human review queue。

第三步是加强专业领域 RAG 与多轮 agent 评测：source-boundary、claim-to-source schema、hard-negative retrieval、多轮 trace rubric、human calibration 和回归监控都要产品化。

第四步是把评测结果接到发布策略，而不是只出排行榜：不同风险层级对应不同 auto-answer、limited release、human review 或 blocked release 门槛。
