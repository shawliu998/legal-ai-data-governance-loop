# 中文简历 Bullet 版本

## 2 行精简版

- 构建法律 AI 数据治理闭环，覆盖需求拆解、rubric eval、人审校准、release gate、badcase routing 和下一轮数据生产。
- 完成 300 条真实输出、80 条人审、72 条 RAG pilot、24 条多轮 trace，沉淀模型边界 memo、dashboard 和数据路由策略。

## 4 行标准版

- 设计 50-case 法律产品边界 eval bank，覆盖咨询、案情分析、文书起草及风险校准、引用 grounding、对抗陷阱等 slice。
- 搭建 A0-A5 model-agent 评测框架，完成 300 / 300 真实 API 输出与 300 / 300 judge 结构化解析，分析回答、追问、RAG、人审和阻断边界。
- 完成 80 条 priority 输出人审，在高风险 / blocker 富集样本上记录 92.5% judge-human agreement，并保留 pilot scale caveat。
- 扩展 RAG source-boundary 和多轮 intake trace eval，将 citation gap、unsupported claim、overclaim 等路由为 eval / SFT / preference / badcase / regression / human_review。

## 偏 DeepSeek 专业领域数据产品经理版本

- 面向专业领域模型数据产品，构建法律 AI 数据治理闭环：任务 slice、数据标准、rubric、人审校准、release gate、badcase routing 和下一轮数据生产。
- 运行 300 条真实 Qianfan API model-agent pilot，覆盖 5 个模型与 A0-A4 agent 架构，将结果用于产品边界而非公开模型排名。
- 设计 RAG focused pilot，评估 source-boundary、material-claim citation coverage 与 claim-level release blocker，明确 RAG 命中不等于可发布。
- 设计 A5 多轮法律 intake pilot，完成 24 traces / 72 turns，用 trace-level eval 识别事实追问、错误前提挑战、overclaim 和人审时机问题。
- 产出 final portfolio findings、model boundary memo、release gate、dashboard、case cards 和 DeepSeek 面试材料。
