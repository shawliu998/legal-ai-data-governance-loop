# Project Summary

## One-Line Summary

Built a legal AI product-boundary evaluation and data governance harness that turns model-workflow behavior into deployment policy, human-review policy, release gates, and next-round data production actions.

中文一句话：

构建法律 AI 产品边界评测与数据闭环治理系统，用真实法律任务 slice 评估模型是否应该回答、追问、引用依据、转人工，并把失败样本路由为 eval、SFT、preference、badcase 或 human_review 数据资产。

## Why This Is Not a Leaderboard

The project does not ask only which model scores highest. It asks:

- Which model-workflow configuration is safe enough to answer?
- Which legal tasks require RAG grounding?
- Which cases require clarification-first intake?
- Which failures must enter human review or block release?
- Which outputs should become badcases, SFT candidates, preference pairs, or eval holdout?

## Current Scope

- 50 product-boundary legal cases.
- 6 slices: normal practice, hard legal reasoning, risk calibration, citation grounding, adversarial trap, and counterfactual pair.
- 5 workflow conditions: closed-book, structured prompt, RAG-grounded, RAG plus risk-control/verifier, and clarification-first.
- 5 mock model slots for full diagnostics, with a 4-model Qianfan API pilot config for ERNIE 5.1, DeepSeek V4 Pro, Qwen3.5-27B, and GLM-5.2.
- 1250 mock model outputs for pipeline verification.
- 12-case API pilot dataset prepared for 240 real model outputs.

## Implementation Highlights

- Designed leakage-safe data separation: `Eval_Input` is visible to the agent, while `Gold_Labels` and `Rubric_Items` are visible only to judge and human review.
- Built controlled local RAG with a small legal corpus, retrieval logs, context injection, source-id citation verification, and claim-level support triage.
- Added judge ensemble calibration: DeepSeek V4 Pro and GLM-5.2 as primary judges, ERNIE 5.1 as arbiter, with self-evaluation exclusion.
- Implemented data routing into `eval`, `sft`, `preference`, `badcase`, and `human_review`.
- Generated human calibration queues, including a 370-row stratified Chinese legal-review file marked as completed human review.
- Added release-gate outputs for blocked, limited-release, and candidate auto-answer policies.

## Core Artifacts

- Project entry point: [README.md](../README.md)
- Results page: [results_product_boundary_eval.md](results_product_boundary_eval.md)
- Model policy memo: [model_boundary_memo.md](model_boundary_memo.md)
- Product PRD: [product_prd.md](product_prd.md)
- Runbook: [runbook.md](runbook.md)

## Interview Pitch

I built a legal AI eval-driven data governance harness. The core is not ranking models by average score, but evaluating whether a legal AI product should answer, ask clarifying questions, use grounded sources, route to human review, or block release. The pipeline converts each output into product decisions and data actions: eval holdout, SFT candidate, preference candidate, badcase, or human review. This lets a data product manager explain model boundaries, risk controls, and the next data production loop with evidence rather than anecdotes.

## Next Step

Run the 12-case Qianfan API pilot and update the results page and model boundary memo with real model-workflow findings.
