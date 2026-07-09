# 中文简历 Bullet

## 2 行版

- 拆解法律 AI 咨询、案情分析、文书起草、引用 grounding 等场景，设计 50-case 产品边界评测集与 rubric。
- 跑通 300 条真实模型输出、80 条人审、72 条 RAG pilot、24 条多轮 trace，产出 release gate、dashboard 和 badcase 数据路由。

## 4 行版

- 设计法律 AI 产品边界评测集，覆盖咨询、案情分析、文书起草、风险校准、引用 grounding 和对抗性请求。
- 搭建 rubric eval 与人审校准流程，完成 300 / 300 真实 API 输出和 80 条 priority 输出复核。
- 做 RAG citation/source-boundary 检查，将 unsupported claim、out-of-scope source、missing citation 路由到人审或回归测试。
- 将 overclaim、missed escalation、citation gap 等 badcase 分流到 eval / SFT / preference / regression / human_review 数据用途。

## 专业领域数据产品经理版本

- 拆解法律 AI 高风险场景，设计评测字段、rubric、人审队列和 release gate。
- 完成 300 条真实模型输出与 80 条 priority 人审，用 dashboard 和 evidence package 支撑产品边界判断。
- 设计 RAG citation/source-boundary pilot，识别 source 越界、citation 缺失和 claim 支持不足问题。
- 设计 A5 多轮 intake pilot，观察事实追问、错误前提挑战、overclaim 和人审时机。
- 建立 badcase routing，将失败样本分到 eval、SFT、preference、regression 或 human_review 数据。
