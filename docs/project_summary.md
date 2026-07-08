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
- 5 mock model slots for full diagnostics, with a 5-model Qianfan API pilot config for ERNIE 5.0, DeepSeek V4 Pro, Qwen3.5-27B, GLM-5.2, and Kimi K2.6.
- 1250 mock model outputs for pipeline verification.
- 12-case Qianfan API pilot completed for 300 real model outputs.
- 80 priority real-output human review rows completed.

## Implementation Highlights

- Designed leakage-safe data separation: `Eval_Input` is visible to the agent, while `Gold_Labels` and `Rubric_Items` are visible only to judge and human review.
- Built controlled local RAG with a small legal corpus, retrieval logs, context injection, source-id citation verification, and claim-level support triage.
- Added judge ensemble calibration and then revised the production scoring plan after API smoke tests showed judge JSON instability on some Qianfan model endpoints.
- Used Qwen3.5-27B as the full-run structured judge after it produced 300 / 300 parseable judge outputs.
- Implemented data routing into `eval`, `sft`, `preference`, `badcase`, and `human_review`.
- Generated human calibration queues, including a 370-row stratified Chinese legal-review file marked as completed human review.
- Completed an 80-row priority human review sample for the real API pilot, with Chinese review workbook and judge-human agreement summary.
- Added release-gate outputs for blocked, limited-release, and candidate auto-answer policies.

## Real API Pilot Results

- 300 / 300 Qianfan model-workflow outputs completed.
- 300 / 300 Qwen judge outputs parsed successfully.
- Human review completed on 80 priority outputs.
- Judge-human agreement on the priority sample: 92.5%.
- Priority sample outcomes: 4 pass, 27 partial pass, 49 fail.
- Confirmed citation or evidence-support issues: 45.
- Confirmed human route overrides: 47.

The API pilot showed that strong models do not remove product-boundary risk. The main failure patterns were insufficient human-review escalation and source-boundary problems in RAG-style workflows.

## Product Findings

- Best routine-answer candidate: Qwen3.5-27B or ERNIE/Kimi under W1 structured prompt, limited to low-risk consultation and no citation defect.
- Best intake/risk-control candidate: W5 clarification-first, especially for missing facts and adversarial drafting.
- RAG requirement: source-specific contract, rule, or citation tasks still need RAG, but RAG output must be checked for source-boundary discipline.
- Current RAG/verifier limitation: W3 and W4 over-produced human-review routes and surfaced unsupported-source issues in the real pilot.
- Release policy: no configuration should be fully auto-released yet; use limited release with human review for high-risk and citation-bound cases.

## Core Artifacts

- Project entry point: [README.md](../README.md)
- Results page: [results_product_boundary_eval.md](results_product_boundary_eval.md)
- Model policy memo: [model_boundary_memo.md](model_boundary_memo.md)
- RAG V2 improvement plan: [rag_v2_improvement_plan.md](rag_v2_improvement_plan.md)
- Interview talk track: [interview_talk_track.md](interview_talk_track.md)
- Product PRD: [product_prd.md](product_prd.md)
- Runbook: [runbook.md](runbook.md)

## Interview Pitch

I built a legal AI eval-driven data governance harness. The core is not ranking models by average score, but evaluating whether a legal AI product should answer, ask clarifying questions, use grounded sources, route to human review, or block release. I ran a real Qianfan API pilot across ERNIE 5.0, DeepSeek V4 Pro, Qwen3.5-27B, GLM-5.2, and Kimi K2.6, then added human review on 80 priority outputs. The result is a model-workflow boundary memo and data loop: failures become eval holdout, SFT candidates, preference pairs, badcases, or human review items.

## Next Step

Expand the controlled RAG corpus and run a second API pilot focused on citation entailment, source-boundary control, and human-calibrated release gates.
