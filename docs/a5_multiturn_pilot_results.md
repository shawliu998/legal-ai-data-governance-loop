# A5 Multi-Turn Intake Pilot

## 定位

A5 pilot 用于验证法律 intake 的多轮日志和 trace-level 评测框架，不用于声称模型已经能够自主完成法律 intake。

## 实验规模

```text
8 cases × 3 千帆托管模型槽位 = 24 traces
24 traces × 3 turns = 72 turns
```

覆盖 ERNIE 5.0、DeepSeek V4 Pro 和 Qwen3.5-27B 三个千帆托管槽位，以及 cooperative、dependent、withdrawn、adversarial 四类用户行为。

72 个 turn records 均记录了正常返回状态；完整对话保存在本地 raw artifacts，仓库只提交长度、hash、状态和脱敏 trace 示例。

## 当前完成的工作

- 保留每轮 user message、预期 agent move、模型响应状态、长度、延迟和 token 信号。
- 在 trace 层检查关键事实追问、错误前提挑战、结论强度、safe redirection 和转人工时机。
- 生成 deterministic triage flags，用于确定优先人审队列；修复词法与否定作用域后，离线
  重算的 24 traces 当前为 0 lexical flags，但这不等于人审确认的 0 overclaim。
- A5 产物把队列动作单独记录为 `trace_review_recommendation`；本轮 24 traces 均为
  `human_review_required`。这是高风险 intake pilot 的规则性复核建议，不是 pass/fail、
  `response_policy` 或人审确认结论。
- 生成 24 行 human trace calibration template，供后续逐条复核。

## 为什么不报告 pass rate 或模型比较

当前 pass/fail、fact coverage 和 overclaim 标记来自关键词与启发式规则，尚未由 reviewer 对 24 条完整 traces 逐条校准。有限样本上的模型百分比容易把规则偏差包装成模型能力差异。

因此，本版本撤下：

- A5 总体 pass rate；
- DeepSeek、ERNIE、Qwen 的模型级 pass rate；
- 未经人审确认的 behavior-level 百分比；
- 任何自动法律 intake 发布结论。

deterministic flags 仍保留在原始证据中，定位是“待复核信号”，不是质量指标。

## 产品意义

单轮回答评测无法覆盖以下问题：

- Agent 是否先问最高影响事实，而不是机械列问题清单；
- 用户依赖模型替其决策时，Agent 是否保持边界；
- 用户要求威胁、曝光、伪造或规避责任时，Agent 是否挑战前提；
- 获得更多事实后，Agent 是否反而给出过强结论；
- 何时应停止继续问答并转人工。

A5 的价值是把这些行为保存为完整 trace，并为后续 reviewer-level 标注、preference pair 和 regression case 提供结构。

## 证据包

公开轻量产物：

- `trace_metrics_summary.csv`：deterministic triage 汇总，不能视为人审质量指标；
- `turn_level_summary.csv`：72 个 turns 的脱敏运行元数据；
- `risk_route_summary.csv`：规则信号分组；
- `redacted_trace_samples.csv` 与 `redacted_trace_example.md`；
- `human_trace_calibration_template.csv`；
- `artifact_manifest.yaml`。

本地 raw artifacts：

- `trace_log.jsonl`
- `turn_log.csv`

## 下一步

1. 两名 reviewer 独立复核全部 24 条 traces。
2. 保存 reviewer A/B、adjudicated labels 和 guideline version。
3. 对 deterministic flag 计算 precision、recall 和 false-positive slice。
4. 只有校准后再报告 trace-level 指标；样本扩大后再讨论模型差异。

## 边界

- 24 traces 只支持流程验证和定性诊断。
- 千帆托管槽位结果不等同于模型官方 API 全量表现。
- deterministic checks 不是法律正确性判断。
- 当前没有 A5 产品发布或自动法律 intake 结论。
