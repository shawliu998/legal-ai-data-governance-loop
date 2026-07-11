# 与 DeepSeek 法律数据产品经理岗位的能力映射

## 项目定位

这个项目不是法律问答 Demo，也不是模型排行榜。我关注的是专业领域数据产品经理需要持续回答的四个问题：场景边界如何定义、数据怎样被可靠标注、哪些模型行为阻断发布、失败记录如何进入下一轮数据生产。

## 能力映射

| 岗位能力 | 我在项目中的工作 | 可核验证据 | 当前边界 |
| --- | --- | --- | --- |
| 法律场景抽象 | 将咨询、案情分析、文书、限定来源 QA、对抗请求和多轮 intake 拆成 case/schema | 50-case boundary bank、85 条基础样本、A0–A5 taxonomy | 场景为项目构造，不代表真实线上分布 |
| 数据标准设计 | 定义 gold 隔离、rubric、错误 taxonomy、source/claim/citation 字段 | Data Card、Labeling SOP、380 rubric items | 尚未形成生产级本体和版本治理 |
| 评测与实验 | 设计 mock 管线与三组 API pilot，保留空响应和解析失败 | 300 API runs、72 RAG runs、24 A5 traces | pilot-scale，不支持模型优劣结论 |
| 人审与质检 | 组织两名法律背景 reviewer 独立复核 priority 样本并归并分歧 | 80-row 脱敏汇总、Human Review Methodology | 非随机样本；公开数据不能复算 reviewer-level IAA |
| 发布治理 | 区分回答策略、复核状态、组级发布闸门和数据资产候选 | PRD、release gate、router、Dashboard | 旧字段仅作兼容别名；内部判断使用 canonical schema |
| 数据闭环 | 将问题记录转成 eval/SFT/preference/badcase/regression 候选 | case cards、router、review writeback、回归设计 | 候选不等于已验收训练数据 |
| RAG 可靠性 | 拆分 retrieval、source boundary、citation coverage、claim support | 8 × 3 × 3 的 RAG V2 pilot | controlled corpus，不是完整法律知识库 |
| 项目沟通 | 输出 PRD、SOP、runbook、风险登记和证据包 | `docs/` 与 lightweight evidence packages | 尚未接入真实业务 SLA 和成本台账 |

## 可诚实陈述的实验规模

- Product-boundary API pilot：12 cases × 5 千帆托管模型槽位 × 5 workflows = 300 API run records，其中 271 条非空回答、29 条空响应。
- Priority review：80 条高风险或 blocker 富集记录，由两名法律背景 reviewer 独立复核并归并分歧；不报告无法由公开标签复算的一致率。
- RAG V2：8 cases × 3 千帆托管模型槽位 × 3 workflows = 72 API runs。
- A5：8 cases × 3 千帆托管模型槽位 = 24 traces / 72 turns；deterministic 标记待人工校准。
- Mock/synthetic：用于验证数据管线、字段、路由和 Dashboard，不作为真实模型质量证据。

## 如果进入真实团队，我会优先补什么

1. 将 priority review 与随机抽样分开，保存匿名 reviewer A/B 和 adjudicated labels，报告分项 IAA、precision/recall 与置信区间。
2. 将 query、source、claim、citation span、support label、release action 和 reviewer override 接入统一的数据 lineage。
3. 建立 P0 漏放率、转人工 precision/recall、review backlog、单位安全放行成本和 badcase 闭环时间。
4. 对模型、服务商封装、prompt、检索库和评测器分别做版本化，避免把供应商或工作流影响误归因于基础模型。
5. 把数据资产从“候选路由”推进到抽检、验收、去重、污染检查和训练后回归的完整状态机。

## 面试中的边界表述

我可以说明自己完成了一个小规模、可复现的法律 AI 产品诊断闭环；不能声称完成了生产法律知识库、统计显著模型评测、自动法律 intake，或证明某个模型已经适合法律意见发布。
