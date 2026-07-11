# Case 03：多轮 intake 的词法规则误报风险

## 场景

匿名 A5 trace `TRACE-A5-INTAKE-001-qianfan_ernie_50-A5` 是一个三轮劳动争议 intake。早期 deterministic 检查曾把它标记为 overclaim 并给出 blocked 信号。

复核规则后发现旧词法检测有两类缺陷：一是把“保证”等法律术语裸匹配为结果承诺；二是
没有正确处理否定作用域。这个 ERNIE trace 的旧误报实际来自“无法告诉您一定能赔/一定
能赢”这类否定表达，而不是模型承诺结果。因此不能把旧 flag 写成“模型已经发生
overclaim”或确定发布结论。

## 真正暴露的问题

这个案例首先暴露的是 evaluator 质量问题：关键词规则如果不处理语境、否定和法律术语，会把正常表达转成高风险标签。法律数据产品不能只审模型，也要审评测器。

## 正确处理方式

- 将旧 `overclaim_detected` 视为 lexical flag，而不是事实标签。
- 修正规则后重新生成全部 A5 deterministic artifacts；离线重算的 24 traces 当前为 0 lexical
  flags，但仍需逐条人审，不能据此声称 0 overclaim。
- 由两名 reviewer 阅读完整三轮 trace，分别判断结论强度、事实追问和转人工时机。
- 在 adjudication 前保持 `pending_review`，不把旧 trace-level `blocked` 信号直接映射为
  canonical `response_policy=block`。
- 只有确认存在问题后，才决定是否形成 `badcase`、`regression` 或 preference pair。

## 数据产品启示

A5 pilot 的 24 条 traces / 72 turns 目前证明的是 trace 采集和复核框架可以运行。它不支持未经人工校准的 pass rate、模型比较或 overclaim 发生率。下一轮应同时保存模型标签、规则版本、reviewer A/B 标签和最终 adjudicated label，才能衡量 evaluator 的 false positive 与 false negative。
