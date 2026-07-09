# Project Summary

## One-Line Summary

Built a legal AI product-boundary evaluation and data governance system that turns model-agent
behavior into deployment policy, human-review policy, release gates, trace-level risk signals, and
next-round data production actions.

中文一句话：

构建法律 AI agent 产品边界评测与数据闭环治理系统，用真实法律任务 slice 和 trace-level eval 评估模型是否应该回答、追问、引用依据、转人工或阻断发布，并把失败样本路由为
eval、SFT、preference、badcase、regression 或 human_review 数据资产。

## Why This Is Not a Leaderboard

The project does not ask only which model scores highest. It asks:

- Which model-agent architecture is safe enough to answer?
- Which legal tasks require RAG grounding?
- Which cases require clarification-first intake?
- Which traces show unsafe premise-following, missing fact elicitation, or bad release decisions?
- Which failures must enter human review or block release?
- Which outputs should become badcases, SFT candidates, preference pairs, or eval holdout?

## Current Scope

- 50 product-boundary legal cases.
- 6 slices: normal practice, hard legal reasoning, risk calibration, citation grounding, adversarial
  trap, and counterfactual pair.
- A0-A5 agent architecture taxonomy: closed-book baseline, structured legal counsel, grounded
  retrieval counsel, verifier-router policy layer, clarification-first intake, and multi-turn legal
  intake.
- 5 mock model slots for full diagnostics, with a 5-model Qianfan API pilot config for ERNIE 5.0,
  DeepSeek V4 Pro, Qwen3.5-27B, GLM-5.2, and Kimi K2.6.
- 1250 mock model outputs for pipeline verification.
- 12-case Qianfan API pilot completed for 300 real model outputs.
- 8-case RAG V2 focused pilot completed for 72 real model outputs.
- 8-case A5 multi-turn intake pilot completed for 24 real API traces and 72 turns across 3 models.
- 3-case A5 smoke remains as the small reproducibility proof; the main A5 result is now the full
  pilot.
- 80 priority real-output human review rows completed.

## Implementation Highlights

- Designed leakage-safe data separation: `Eval_Input` is visible to the agent, while `Gold_Labels`
  and `Rubric_Items` are visible only to judge and human review.
- Built controlled local RAG with a small legal corpus, retrieval logs, context injection, source-id
  citation verification, and claim-level support triage.
- Improved the controlled RAG corpus by correcting a conflicting employment-policy source and adding
  precise consumer, labor, debt-collection, false-litigation, lease-deposit, and evidence snippets.
- Added judge ensemble calibration and then revised the production scoring plan after API smoke
  tests showed judge JSON instability on some Qianfan model endpoints.
- Used Qwen3.5-27B as the full-run structured judge after it produced 300 / 300 parseable judge
  outputs.
- Implemented data routing into `eval`, `sft`, `preference`, `badcase`, and `human_review`.
- Generated human calibration queues, including a 370-row stratified Chinese legal-review file
  marked as completed human review.
- Completed an 80-row priority human review sample for the real API pilot, with Chinese review
  workbook and judge-human agreement summary.
- Added release-gate outputs for blocked, limited-release, and candidate auto-answer policies.
- Added A0-A5 architecture documentation and trace-level eval schema to connect answer quality,
  retrieval quality, citation quality, risk routing, release gates, and data routes.
- Added an A5 multi-turn legal intake pilot covering cooperative, dependent, withdrawn, and
  adversarial user behavior.

## Real API Pilot Results

- 300 / 300 Qianfan model-agent outputs completed.
- 300 / 300 Qwen judge outputs parsed successfully.
- Human review completed on 80 priority outputs.
- Judge-human agreement on the priority sample: 92.5%.
- Priority sample outcomes: 4 pass, 27 partial pass, 49 fail.
- Confirmed citation or evidence-support issues: 45.
- Confirmed human route overrides: 47.

The API pilot showed that strong models do not remove product-boundary risk. The main failure
patterns were insufficient human-review escalation and source-boundary problems in RAG-style
workflows.

## RAG V2 And Agentic Eval Additions

- RAG V2 focused pilot: 72 / 72 real Qianfan outputs completed.
- W4/A2 retrieval found all expected allowed sources, but average source-boundary precision was 0.50
  because top-k retrieval included extra sources.
- Claim-level triage found 555 citation-gate issues among 630 reviewable legal claims; this is a
  strict release-risk gate, not an overall answer-accuracy rate.
- A5 multi-turn intake cases now test material-fact elicitation, bad-premise challenge,
  user-behavior adaptation, and escalation timing.
- A5 smoke test completed on cooperative, dependent, and adversarial user behavior: 6 traces, 18
  turns, 100% bad-premise challenge rate, 100% human-review recommendation rate, and 83.3% average
  material-fact coverage under deterministic triage checks. This validates the trace loop, not
  production readiness.
- A5 full pilot completed across all 8 cases and 3 models: 24 traces, 72 turns, 75.0% deterministic
  trace pass rate, 77.1% average material-fact coverage, and 6 overclaim-flagged traces routed to
  human calibration.
- Trace-level schema maps user turns, retrieval, citation checks, claim checks, risk checks, human
  review, release gate, and data route into one product-evaluable object.

## Product Findings

- Best routine-answer candidate: Qwen3.5-27B or ERNIE/Kimi under A1 structured legal counsel,
  limited to low-risk consultation and no citation defect.
- Best intake/risk-control candidate: A4 clarification-first, especially for missing facts and
  adversarial drafting.
- Agentic eval candidate now completed as pilot: A5 multi-turn legal intake, especially for
  dependent, withdrawn, or adversarial users.
- RAG requirement: source-specific contract, rule, or citation tasks still need RAG, but RAG output
  must be checked for source-boundary discipline.
- Current RAG/verifier limitation: W3 and W4 over-produced human-review routes and surfaced
  unsupported-source issues in the real pilot.
- Release policy: no configuration should be fully auto-released yet; use limited release with human
  review for high-risk and citation-bound cases.

## Core Artifacts

- Project entry point: [README.md](../README.md)
- Results page: [results_product_boundary_eval.md](results_product_boundary_eval.md)
- Agent architecture design:
  [legal_agent_product_eval_v2_design.md](legal_agent_product_eval_v2_design.md)
- Trace-level schema: [trace_level_eval_schema.md](trace_level_eval_schema.md)
- A5 intake pilot: [multiturn_intake_pilot.md](multiturn_intake_pilot.md)
- A5 smoke results: [a5_multiturn_smoke_results.md](a5_multiturn_smoke_results.md)
- A5 full pilot results: [a5_multiturn_pilot_results.md](a5_multiturn_pilot_results.md)
- A5 judge rubric: [a5_trace_judge_rubric.md](a5_trace_judge_rubric.md)
- Methodology risk register: [methodology_risk_register.md](methodology_risk_register.md)
- Model policy memo: [model_boundary_memo.md](model_boundary_memo.md)
- RAG V2 improvement plan: [rag_v2_improvement_plan.md](rag_v2_improvement_plan.md)
- Chinese interview pitch: [interview_pitch_zh.md](interview_pitch_zh.md)
- Product PRD: [product_prd.md](product_prd.md)
- Runbook: [runbook.md](runbook.md)

## Interview Pitch

I built a legal AI product-boundary evaluation and data governance system. The core is not ranking
models by average score, but evaluating whether a legal AI product should answer, ask clarifying
questions, use grounded sources, route to human review, or block release. I ran a real Qianfan API
pilot across ERNIE 5.0, DeepSeek V4 Pro, Qwen3.5-27B, GLM-5.2, and Kimi K2.6, then added human
review on 80 priority outputs, a RAG V2 focused pilot, and a 24-trace A5 multi-turn intake pilot.
The result is a model-agent boundary memo and data loop: failures become eval holdout, SFT
candidates, preference pairs, badcases, regression evals, or human review items.

## Next Step

Use the A5-specific judge rubric to human-calibrate all 24 completed A5 pilot traces, starting with
the 6 overclaim-flagged traces.
