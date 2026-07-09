# Case 02：RAG 回答里的引用边界问题

## 场景

匿名样本 `LPB-CITE-001` 要求模型只根据 `CONTRACT-001` 和 `PLATFORM-001` 判断延迟发货是否能直接三倍赔偿。`LPB-CITE-002` 要求模型只根据 `POLICY-001` 和 `POLICY-002` 判断迟到三次能否直接解除劳动合同。

这类题的重点不是让模型展示法律知识，而是看它能不能守住“只能用给定来源”的边界。

## 模型出了什么问题

RAG 输出有时会引用看起来合理的外部规则，或者对关键结论没有给出明确 citation。RAG V2 的 redacted evidence 里，相关 source-limited case 出现过 unsupported-claim label、no-citation rows 和 out-of-scope source counts。

这说明问题不在于“有没有检索到材料”，而在于生成阶段有没有把每个关键 claim 都限制在允许来源里。

## 风险在哪里

用户看到有引用的回答，会自然认为结论已经被来源支持。但如果引用来源越界，或者 citation 没有真正支持 claim，这类回答在法律产品里不能直接放行。

## 我怎么判断这个问题

RAG V2 focused pilot 里，W4/RAG retrieval 的 expected-source recall 是 100%，但 average source-boundary precision 是 0.50。也就是说，检索能找到目标来源，但 top-k 里仍可能混入额外来源。

因此我把 source-boundary、citation coverage 和 claim-level support 分开看。只看 retrieval recall 不够。

## 应该进入哪类处理流程

- `human_review`：人工确认 claim 是否被来源支持。
- `regression`：把 out-of-scope source 做成边界回归样本。
- `sft`：训练每个 material claim 都要引用允许来源。
- `preference`：偏好不越界、不强行扩展来源的回答。
- `badcase`：保留 fabricated citation、contradicted source 或 unsupported claim。

## 这个样本后续怎么用

它适合做 RAG release gate 的测试样本：检索命中不是放行条件，关键 claim 必须有允许来源支持。
