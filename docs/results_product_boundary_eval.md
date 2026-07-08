# Product Boundary Eval Results

## Positioning

This report interprets the stratified legal product-boundary eval.
It should not be written as a model leaderboard.

Core question:

> Which model-workflow configuration should answer, ask clarifying questions, use provided-source grounding, route to human review, or generate a reusable data asset?

## Run Metadata

| Field | Value |
| --- | --- |
| Dataset | `data/product_boundary_pilot/dataset_manifest.yaml` |
| Source JSONL | `data/eval_sets/legal_product_boundary_pilot_v1.jsonl` |
| Config | `config.qianfan_product_boundary_runnable.yaml` |
| Output directory | TODO |
| Cases | 50 |
| Workflows | V0/W0, V1/W1, V4/W2, V3/W3, V5/W4 |
| Model slots | ERNIE 5.1, DeepSeek V4 Pro, Qwen3.5-27B, GLM-5.2, Lite baseline |
| Total planned outputs | 1250 |
| Judge mode | TODO |
| Judge ensemble | DeepSeek V4 Pro + GLM-5.2 primary judges, ERNIE 5.1 arbiter, self-eval excluded |
| Human calibration file | TODO |
| Release gate file | TODO |

## Slice Summary

| Slice | Product Question | Result | Product Decision |
| --- | --- | --- | --- |
| `normal_practice` | Which routine cases can be auto-answered? | TODO | TODO |
| `hard_legal_reasoning` | Which cases need stronger model or human review? | TODO | TODO |
| `risk_calibration` | Does the workflow block unsafe or overconfident outputs? | TODO | TODO |
| `citation_grounding` | Does the workflow stay within provided sources? | TODO | TODO |
| `adversarial_trap` | Does the model refuse bad premises or unsafe requests? | TODO | TODO |
| `counterfactual_pair` | Does the model react to legally material fact changes? | TODO | TODO |

## Workflow Policy

| Workflow | Interpretation | Observed Strength | Observed Risk | Deployment Policy |
| --- | --- | --- | --- | --- |
| W0 closed-book | Raw model behavior. | TODO | TODO | TODO |
| W1 structured legal prompt | Structured legal analysis. | TODO | TODO | TODO |
| W2 RAG grounded | Local-corpus retrieval plus source-constrained answer. | TODO | TODO | TODO |
| W3 RAG + risk-control workflow | Retrieval, workflow answer, citation verification, and routing behavior. | TODO | TODO | TODO |
| W4 clarification-first | Intake before final answer. | TODO | TODO | TODO |

## Release Gate Summary

Use `release_gate.csv`.

| Task Slice | Model | Workflow | Decision | Blockers | Required Mitigation |
| --- | --- | --- | --- | --- | --- |
| TODO | TODO | TODO | TODO | TODO | TODO |

## Data Production Plan

| Failure Pattern | Route | Data Action |
| --- | --- | --- |
| Fabricated citation | `badcase`, `regression_eval` | Add to source-grounding regression set. |
| Invented fact or unsupported document claim | `badcase`, `human_review` | Human cleanup before reuse. |
| Overconfident win rate | `preference_pair` | Build preference pairs favoring calibrated uncertainty. |
| Missed human review | `human_review`, `badcase` | Tighten release gate and escalation prompt. |
| Ignored material fact change | `regression_eval` | Preserve counterfactual pair as holdout. |
| Weak clarification | `sft_candidate` | Add intake checklist examples. |

## Human Calibration

Use `human_review_calibration.csv`.

Use `judge_disagreements.csv` and `judge_ensemble_summary.csv` to prioritize calibration before sampling routine rows.

Use `retrieval_log.csv` and `citation_verification.csv` to separate retrieval failures from generation grounding failures.
Use `claim_checks` for legal-review triage, not as final legal correctness.

Report:

- pass/fail agreement between judge and human reviewer
- critical failure agreement
- score adjustment pattern by workflow
- examples where LLM judge was too lenient or too harsh

## Final Product Decision

Write the final decision as routing policy:

```text
Auto-answer eligible:
Clarification-first required:
Grounding required:
Human review required:
Blocked from release:
Next badcase set:
Next SFT candidates:
Next preference pairs:
Regression eval additions:
```

Mock outputs are only pipeline diagnostics. Use API outputs and human calibration before making deployment claims.
