# DeepSeek / 专业领域数据产品经理岗位匹配说明

## Target Role

目标岗位：专业领域数据产品经理、法律数据产品经理、模型数据策略、模型评测与数据治理相关岗位。

我会把这个项目定位为**法律 AI 数据产品与治理系统**，而不是单纯法律 LLM benchmark。它展示的是如何把专业领域评测转成数据闭环、上线边界、人审机制和下一轮数据生产策略。

## Why This Project Fits

这个项目从法律场景出发，但核心能力可迁移到其他专业领域：定义任务边界、设计 rubric、组织评测数据、运行模型-agent pilot、识别 badcase、制定 release gate、设计人审校准，并把失败样本路由到 eval / SFT / preference / regression / human review。

已有证据包括 50-case product-boundary eval bank、300 条真实 Qianfan API 输出、80 条 priority 输出人审、72-output RAG V2 focused pilot，以及 24-trace / 72-turn A5 multi-turn intake pilot。这些材料支撑项目不是停留在 prompt demo，而是覆盖数据设计、评测执行、风险治理和产品决策。

## Role Requirement × Project Evidence

| 岗位能力 | 项目证据 |
| --- | --- |
| 专业领域任务理解 | 覆盖法律咨询、案情分析、文书起草，以及 normal practice、hard reasoning、risk calibration、citation grounding、adversarial trap、counterfactual pair 等 slice。 |
| 数据标准与标注体系设计 | 设计 leakage-safe 数据分层：agent 只看 `Eval_Input`，judge / human review 可看 `Gold_Labels` 和 `Rubric_Items`，并沉淀 normalized run logs、release gate、data route 等结构化字段。 |
| Rubric-based eval | 为不同法律任务构建 judge rubric，并把结果映射到 auto-answer、clarification、RAG、human review、blocked release 等产品动作。 |
| 模型与 agent workflow 对比 | 运行 A0-A5 架构：closed-book、structured counsel、grounded retrieval、verifier-router、clarification-first、multi-turn intake。 |
| 真实模型 pilot 执行 | 完成 300 / 300 真实 Qianfan API 输出，并完成 300 / 300 Qwen judge 结构化解析。 |
| 人审与校准 | 完成 80 条 priority real outputs 人审，在高风险 / blocker 富集样本上得到 92.5% judge-human agreement，同时保留样本偏置 caveat。 |
| RAG 数据治理 | RAG V2 72 条真实输出评估 expected-source recall、source-boundary precision、citation coverage 和 claim-level citation gate。 |
| Release gate 设计 | 把 fabricated citation、unsupported claim、out-of-scope source、missed escalation 等定义为 limited release 或 blocked release 条件。 |
| Badcase 与下一轮数据生产 | 将失败样本路由到 eval、SFT、preference、badcase、regression、human_review，形成专业领域数据治理闭环。 |
| Dashboard 与证据包 | 输出 executive dashboard、redacted evidence package、release gate summary 和模型边界 memo，服务产品决策而非单一分数展示。 |
| 多轮 agent 评测 | A5 full pilot 完成 24 traces / 72 turns，覆盖 cooperative、dependent、withdrawn、adversarial user behavior。 |
| 风险表达与边界意识 | 明确不声称统计显著 benchmark、不声称 RAG 解决法律幻觉、不声称 A5 可自主发布、不把 judge 分数包装为最终模型排名。 |

## What I Would Improve in a Real Team

- 扩大人审规模，并把 priority review 与随机抽样 review 分开报告。
- 引入更多法律专家标注，建立 reviewer disagreement、appeal 和 calibration meeting 机制。
- 将 source-boundary 检查接入更严格的 claim-to-source schema，而不是只依赖后处理 triage。
- 为 RAG 增加 hard-negative retrieval 数据、source filtering、citation repair 和 regression suite。
- 将 A5 多轮 trace 的人审标签补齐，并沉淀成 multi-turn SFT / preference / regression 数据。
- 建立线上 badcase intake：用户反馈、人工客服、模型日志、检索日志和 release gate 结果统一进入数据路由。
- 在团队环境中接入隐私合规、权限控制、数据版本管理、灰度发布和 dashboard 监控。

## Interview Talking Points

- 我做的不是“法律模型排名”，而是“法律 AI 在什么条件下可以回答、追问、检索、转人工或阻断发布”的数据产品系统。
- PLawBench 这类方法给我的启发是 rubric-based legal evaluation，但我的项目重点是把 rubric eval 接到人审、release gate、badcase routing 和下一轮数据生产。
- 300 条真实 API 输出展示我跑通了模型-agent pilot；80 条人审说明我没有只依赖 LLM judge；RAG V2 和 A5 支撑我关注 source boundary 和多轮 trace 这类真实产品风险。
- 如果进入 DeepSeek 或类似团队，我会优先把专业领域数据闭环做成可复用机制：数据准入、评测 rubric、人审校准、badcase 归因、训练数据生产、回归评测和发布门槛。
