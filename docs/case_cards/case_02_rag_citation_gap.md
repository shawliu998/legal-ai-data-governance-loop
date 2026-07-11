# Case 02：RAG 回答里的引用边界问题

## 场景

匿名样本 `LPB-CITE-001` 要求模型只根据 `CONTRACT-001` 和 `PLATFORM-001` 判断延迟发货是否能直接三倍赔偿。`LPB-CITE-002` 要求模型只根据 `POLICY-001` 和 `POLICY-002` 判断迟到三次能否直接解除劳动合同。

这类题的重点不是让模型展示法律知识，而是看它能不能守住“只能用给定来源”的边界。

## 模型出了什么问题

RAG 输出有时会引用看起来合理的外部规则，或者对关键结论没有给出明确 citation。一个可核查
的脱敏运行记录是 `RUN-LPB-CITE-001-qianfan_deepseek_v4_pro-V4`（千帆托管模型槽位，
V4/W2），见公开 [RAG redacted sample CSV](../../outputs/rag_v2_focused_pilot_v1/redacted_sample_outputs_20.csv)。

| 字段 | 脱敏证据值 |
| --- | --- |
| `citation_fidelity_label` | `unsupported_claim` |
| `reviewable_claim_count` | `10` |
| strict citation-defect flags | `8` |
| needs-review flags | `9` |
| all-claim source-boundary blockers | `3` |
| `needs_human_review` | `true` |
| 输出证据 | 935 characters；SHA-256 前 12 位 `569e9cf57b87` |

这说明问题不在于“有没有检索到材料”，而在于生成阶段有没有把每个关键 claim 都限制在允许来源里。

## 风险在哪里

用户看到有引用的回答，会自然认为结论已经被来源支持。但如果引用来源越界，或者 citation 没有真正支持 claim，这类回答在法律产品里不能直接放行。

## 我怎么判断这个问题

RAG V2 focused pilot 里，V4/A2 RAG retrieval 的 expected-source recall 是 100%，但 average source-boundary precision 是 0.50。也就是说，检索能找到目标来源，但 top-k 里仍可能混入额外来源。

因此我把 source-boundary、citation coverage 和 claim-level support 分开看。只看 retrieval recall 不够。

## 应该进入哪类处理流程

- 当前回答动作：claim support 未确认时 `human_review`；fabricated、contradicted 或重大 source-boundary 失败时 `block`。
- 复核后数据候选：out-of-scope source 可进入 `regression`，确认的严重问题可进入 `badcase`。
- 只有 reviewer 写出或确认逐 claim 引用的正确版本后，才形成 `sft` 或 `preference` 数据。

## 这个样本后续怎么用

该记录当前是自动 triage 的 `needs_human_review`，不是人审确认错误。经 reviewer 确认、纠正
并验收后，它才适合做 RAG release-gate 测试资产：检索命中不是放行条件，关键 claim 必须有
允许来源支持。
