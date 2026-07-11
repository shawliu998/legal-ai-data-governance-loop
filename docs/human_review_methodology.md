# 人审方法与证据边界

## Reviewer 设置

- Reviewer 数量：2 人。
- 背景：均具备法律背景；其中一名为法学博士并通过国家统一法律职业资格考试。
- 标注方式：两人独立阅读模型回答、允许查看的输入、gold labels 和 rubric 后完成判断。
- 分歧处理：独立标注结束后复核分歧，形成用于发布判断和数据处置的最终结论。
- 盲审边界：现有公开记录没有保存 reviewer 是否对模型身份、judge 结论完全盲化的可复核字段，因此本版本不声称完成了严格 blinded review。

公开证据包只保留最终脱敏汇总，不公开 reviewer 身份或含完整模型回答的原始工作簿。80
条记录的最终复核字段均已填写；这一完成度可以由公开汇总核验，但不能反推出两名 reviewer
各自的原始标签。

## 80 条 priority sample

这 80 条不是从全部 API runs 中简单随机抽取，而是重点覆盖：

- 高风险或低置信度记录；
- 可能触发 release blocker 的记录；
- citation 或 claim support 存疑的记录；
- 自动路由可能需要人工调整的记录。

因此，样本中的 pass/fail、critical failure 或 route override 分布都不能外推为总体发生率。

## 为什么本版本不报告一致率

当前公开仓库没有保存可复算的匿名 `reviewer_a_label`、`reviewer_b_label` 与 `adjudicated_label`。仅有最终归并结果不足以验证 reviewer 间一致率，也不足以严格复算 judge-human 的逐项一致性。

因此，本版本撤下单一 agreement 百分比，不把它用于简历、README 或模型结论。这里不是否定人审流程，而是区分“项目内部曾记录的汇总字段”和“公开证据能够独立复核的指标”。

## 当前可以公开说明什么

| 项目 | 可说明内容 | 不能说明内容 |
| --- | --- | --- |
| Review scope | 两名 reviewer 对 80 条 priority-enriched 记录独立复核并归并分歧 | 代表全部 300 API runs 的随机总体 |
| Reviewer background | 两人均具备法律背景；其中一名为法学博士并通过法考 | 仅凭资格即可保证标注绝对正确 |
| Public evidence | 80 条记录的最终复核字段完成度、最终脱敏汇总、流程说明和数据边界 | reviewer-level IAA、Cohen's kappa、总体准确率 |
| Product use | 校准 blocker、转人工和数据处置规则 | 直接证明 judge 或模型达到上线标准 |

## 下一轮应保存的标签

- `reviewer_a_critical_failure` / `reviewer_b_critical_failure`
- `reviewer_a_response_policy` / `reviewer_b_response_policy`
- `reviewer_a_risk_level` / `reviewer_b_risk_level`
- `reviewer_a_citation_support` / `reviewer_b_citation_support`
- `adjudicated_*` 对应字段
- `reviewer_id_hash`、标注时间、guideline version 与 conflict reason
- `model_identity_blinded`、`judge_label_blinded` 与标签锁定时间

有了这些字段后，再分别报告：

- critical-failure 二元一致率与 Cohen's kappa；
- response policy 多分类一致率；
- risk level weighted kappa；
- citation support 分项一致率；
- data asset routes 的逐标签 precision、recall 与 F1。

## 对外推荐表述

> 两名具备法律背景的 reviewer 对 80 条高风险与 blocker 富集记录进行了独立复核，分歧经复核形成最终结论。该样本用于校准发布边界和数据处置，不是随机总体；由于公开证据未保留可复算的 reviewer-level 独立标签，本版本不报告一致率或总体准确率。
