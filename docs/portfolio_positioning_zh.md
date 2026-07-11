# Portfolio Positioning

这份说明保留项目的求职定位信息，避免把 README 写成岗位投递页。

## 适配方向

- 专业领域数据产品经理
- 法律数据产品经理
- 模型数据策略 / 模型评测与数据治理相关岗位

## 为什么这个项目相关

项目展示的是专业领域 AI 评测如何接到产品决策和数据生产：从法律任务拆解、样本设计、评分规则、人审校准，到 release gate、badcase 归因和下一轮数据用途规划。

可展开讲的证据包括：

- 50-case product-boundary eval bank。
- 12 cases × 5 千帆托管模型槽位 × 5 workflows = 300 个 API run records，其中 271 条非空回答、29 条空响应。
- 两名法律背景 reviewer 独立复核 80 条 priority 记录并归并分歧；公开证据不能复算 reviewer-level 一致率。
- 8 cases × 3 千帆托管模型槽位 × 3 workflows = 72-run RAG V2 focused pilot。
- 8 cases × 3 千帆托管模型槽位 = 24-trace / 72-turn A5 pilot；质量标签尚待人工校准。
- release gate、human review queue、data routing、dashboard 和 redacted evidence package。

## 面试中建议的表达边界

- 不说这是 PLawBench 复现。
- 不说这是公开法律模型排行榜。
- 不说 RAG 已经解决法律幻觉。
- 不说 A5 已具备自动法律 intake 发布能力。
- 不把 Qwen judge 分数包装成最终模型排名。
- 不把千帆托管槽位结果等同于模型官方 API 全量表现。
- 不把 mock/synthetic 产物当成真实模型能力证据。
