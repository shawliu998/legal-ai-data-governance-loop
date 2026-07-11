# DeepSeek 产品观察

本页说明项目与 DeepSeek 法律数据产品工作的关系，不做公开模型排名。

## 先说明接入边界

项目中的 `qianfan_deepseek_v4_pro` 是通过百度智能云千帆 OpenAI-compatible 接口调用的托管模型槽位，不是对 DeepSeek 官方 API、官方服务稳定性或全量模型版本的独立测试。模型名称、服务封装、推理参数和供应商侧实现都可能影响结果。

因此，本页只描述该托管槽位在本项目有限样本中的工程和产品现象，不把它外推为“DeepSeek 法律能力结论”。

## 样本覆盖

| Pilot | DeepSeek 槽位覆盖 | 总体实验规模 | 可以说明什么 |
| --- | ---: | ---: | --- |
| Product boundary | 12 cases × 5 workflows = 60 API runs | 12 × 5 hosted slots × 5 workflows = 300 API runs | 观察结构化输出、空响应、风险路由和工作流差异 |
| RAG V2 | 8 cases × 3 workflows = 24 API runs | 8 × 3 hosted slots × 3 workflows = 72 API runs | 观察 source boundary、citation 与 claim support 失败模式 |
| A5 intake | 8 traces / 24 turns | 24 traces / 72 turns | 验证多轮日志与 trace-level 评测框架；尚无人工校准指标 |

Product-boundary pilot 的全部 300 个 API run records 中有 271 条非空回答、29 条空响应；其中 DeepSeek 托管槽位为 58 条非空、2 条空响应。空响应被保留为可靠性信号，不计作有效模型回答。

## 与岗位相关的三类观察

### 1. 结构化回答与可发布性是两个问题

结构完整、表达谨慎的回答仍可能引用允许范围之外的来源，或出现 material claim 缺少支持。对法律产品而言，不能用一个总分替代 source-boundary、claim-support 和 release-blocker 检查。

### 2. Reasoning 与结构化输出需要工程兜底

有限 judge smoke 中出现过 reasoning content 占用 completion budget、最终 `content` 为空或 JSON 不完整的现象。这是本项目里的工程观察，不足以归因为某个模型的普遍特征。合理的产品动作包括：

- 为结构化答案预留独立预算；
- 对 schema parsing 设置重试和 fallback；
- 保留空响应与 parse failure，不从统计分母静默删除；
- 低置信度或解析失败进入人工复核；
- 避免同模型 self-judge 直接决定发布。

### 3. 多轮 intake 必须看完整 trace

A5 为 DeepSeek 托管槽位收集了 8 条 traces、24 个 turns。当前 deterministic 规则只用于筛选待复核 trace，尚未完成逐条人工校准，因此不报告 pass rate、事实覆盖率或与其他模型的比较结果。

产品上应检查每一轮是否提出高影响问题、是否挑战错误前提、是否控制结论强度，以及何时转人工，而不是只看最后一条回复。

## 岗位能力映射

| DeepSeek 法律数据产品工作 | 本项目证据 | 下一步补强 |
| --- | --- | --- |
| 领域场景与边界定义 | 50-case product-boundary bank、A0–A5 workflow taxonomy | 接入真实脱敏 query 分布并做覆盖率审计 |
| 数据标准与评测 | rubric、错误 taxonomy、claim/source 分层 | 预注册指标、扩大盲审和随机样本 |
| 数据生产闭环 | release gate、review queue、reviewer 回写、data-asset 候选路由 | 扩展资产抽检、验收、去重、隐私检查与训练后回归状态机 |
| 模型可靠性 | 保留空响应、解析失败、citation blocker | 加入线上可观测性与版本回归 |
| 跨团队协作 | PRD、SOP、数据卡、runbook、evidence package | 补充标注成本、SLA 和发布复盘机制 |

## 表达边界

- 不把千帆托管槽位等同于 DeepSeek 官方 API 全量表现。
- 不把 Qwen judge 信号当成 DeepSeek 法律能力排名。
- 不把 60、24 或 8 条有限样本外推为统计显著结论。
- 不把 controlled RAG 当成生产法律检索。
- 不在人审 trace calibration 完成前报告 A5 质量指标。
