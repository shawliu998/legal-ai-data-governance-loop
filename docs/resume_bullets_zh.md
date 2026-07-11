# 中文简历 Bullet

## 2 行版

- 拆解法律 AI 咨询、案情分析、文书起草、引用 grounding 等场景，设计 50-case 产品边界评测集与 rubric。
- 跑通 300 个千帆 API runs（271 条非空回答、29 条空响应），组织两名法律背景 reviewer 独立复核 80 条 priority 记录，并完成 72-run RAG pilot 与 24-trace 多轮 intake pilot。

## 4 行版

- 设计法律 AI 产品边界评测集，覆盖咨询、案情分析、文书起草、风险校准、引用 grounding 和对抗性请求。
- 搭建 rubric eval 与双 reviewer 复核流程，完成 12 cases × 5 千帆托管模型槽位 × 5 workflows 的 300-run API pilot，并保留 29 条空响应作为可靠性信号。
- 做 RAG citation/source-boundary 检查，将 unsupported claim、out-of-scope source、missing citation 路由到人审或回归测试。
- 将 overclaim、missed escalation、citation gap 等记录连接到发布动作、人审流程及 eval / SFT / preference / badcase / regression 数据资产候选。

## 专业领域数据产品经理版本

- 拆解法律 AI 高风险场景，设计评测字段、rubric、人审队列和 release gate。
- 完成 300-run 千帆 API pilot（271 条非空、29 条空响应）与 80 条 priority review，用 dashboard 和 evidence package 支撑产品边界判断。
- 设计 RAG citation/source-boundary pilot，识别 source 越界、citation 缺失和 claim 支持不足问题。
- 设计 24-trace / 72-turn A5 多轮 intake pilot，验证 trace 采集和人工校准框架，不包装未校准 pass rate。
- 建立 badcase routing，将当前发布动作、复核状态与复核后的 eval、SFT、preference、badcase、regression 候选分开管理。
