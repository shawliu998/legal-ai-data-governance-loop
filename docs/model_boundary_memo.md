# Model Boundary Memo: Legal Product Eval

## Compared Models

- ERNIE 5.0
- DeepSeek V4 Pro
- Qwen3.5-27B
- GLM-5.2
- Kimi K2.6

The comparison is model-workflow based, not a public leaderboard. The unit of decision is whether a model-workflow configuration is suitable for a legal product policy: auto-answer, grounded answer, clarification-first, human review, or blocked.

## Main Findings

The real API pilot used 12 legal product-boundary cases, 5 Qianfan-accessible models, and 5 workflow configurations, producing 300 model outputs. Full-run scoring used Qwen3.5-27B as the structured judge because it produced 300 / 300 parseable judge outputs during the pilot. An 80-row priority human review sample was then completed for high-risk outputs, citation issues, and likely release blockers.

This memo is a product boundary memo, not a leaderboard.

Methodology caveat: model-level scores are Qwen-judge baseline signals, not final model rankings. Qwen-scored Qwen outputs should be interpreted cautiously and validated through human review or non-Qwen judge sampling.

1. Best model/workflow for routine consultation: Qwen3.5-27B or ERNIE/Kimi under W1 structured legal prompt, limited to low-risk consultation and no citation defect.
2. Best model/workflow for clarification and risk intake: W5 clarification-first workflow, especially when material facts are missing or the user asks for risky procedural strategy.
3. Best model/workflow for citation-grounded answers: W2/W3-style grounding is required for source-specific tasks, but the pilot showed source-boundary failures; grounded answers need citation verification and human review before release.
4. Most conservative workflow: W3 risk-control/verifier routed 59 / 60 outputs to human review, useful for triage but too conservative for user-facing efficiency without refinement.
5. Most likely failure pattern: insufficient human-review escalation and unsupported or out-of-scope source use, not merely low answer quality.
6. Cost-effective deployment policy: use W1 for low-risk routine consultation, W5 for intake and missing-fact scenarios, and W2/W3 only where source grounding is mandatory and citation verification is enabled.

## Observed Metrics

| Signal | Result |
| --- | ---: |
| Real model outputs | 300 |
| Judge parse success | 300 / 300 |
| Priority human review rows | 80 |
| Human pass / partial / fail | 4 / 27 / 49 |
| Judge-human agreement | 92.5% on priority-enriched sample |
| Confirmed citation or evidence-support issues | 45 |
| Human route overrides | 47 |

Model-level judge baseline:

| Model | Avg score | Human-review route count |
| --- | ---: | ---: |
| Qwen3.5-27B | 0.878 | 48 / 60 |
| ERNIE 5.0 | 0.765 | 49 / 60 |
| DeepSeek V4 Pro | 0.756 | 49 / 60 |
| Kimi K2.6 | 0.730 | 47 / 60 |
| GLM-5.2 | 0.462 | 50 / 60 |

Workflow-level judge baseline:

| Workflow | Version | Avg score | Human-review rate | Product interpretation |
| --- | --- | ---: | ---: | --- |
| Structured legal prompt | V1 | 0.883 | 71.7% | Best low-risk baseline; still needs routing rules. |
| Clarification-first intake | V5 | 0.851 | 68.3% | Strong for missing facts and risk calibration. |
| Provided-context grounded answer | V4 | 0.706 | 95.0% | Required for source-specific answers, but citation discipline is not solved. |
| Closed-book answer | V0 | 0.616 | 70.0% | Useful as baseline, not a release candidate for high-risk tasks. |
| Risk-control/verifier agent | V3 | 0.533 | 98.3% | Conservative triage layer; too much over-routing in current form. |

Human review on the priority sample:

| Workflow | Fail | Partial | Pass |
| --- | ---: | ---: | ---: |
| V0 | 2 | 11 | 0 |
| V1 | 2 | 7 | 3 |
| V3 | 25 | 0 | 0 |
| V4 | 18 | 0 | 0 |
| V5 | 2 | 9 | 1 |

## Product Policy

Auto-answer:

- Candidate scope: routine low-risk consultation where the workflow has no critical failure, no fabricated citation, and no unresolved judge disagreement.
- Prefer W1 structured prompt for the first release gate.
- Do not auto-answer high-risk labor, adversarial drafting, or citation-boundary cases.

RAG required:

- Citation-grounding tasks.
- Contract, document, or provided-source interpretation.
- Any answer that makes source-specific legal or factual claims.
- RAG output must pass source-id citation checks and human calibration before user-facing release.
- If the user asks "only based on these materials", any outside statute, case, or policy source should be treated as a source-boundary issue unless explicitly allowed.

Clarification required:

- Missing material facts.
- Ambiguous labor, contract, family, or dispute posture.
- Win-rate, litigation outcome, or probability questions.
- Prefer W5 when the correct product behavior is to slow down, ask for facts, or refuse to draft unsafe content.

Human review required:

- High-risk labor, marriage/family, accident, administrative penalty, or criminal-civil overlap.
- Deceptive or coercive document drafting.
- Unsupported claims or fabricated citations.
- Judge disagreement on risk, route, or critical failure.

Blocked:

- Fabricated citations.
- Invented evidence or facts.
- Overconfident win probability.
- Missed human review on high-risk cases.
- Unsafe or deceptive action suggestions.
- RAG answers that cite retrieved source IDs but use them to support claims they do not actually entail.

## Data Policy

- `eval_holdout`: stable routine samples and counterfactual pairs for regression.
- `sft_candidate`: repeated missing-fact, evidence-warning, or intake-quality failures.
- `preference_candidate`: paired outputs where one answer is better calibrated or safer.
- `badcase`: critical failures, adversarial traps, fabricated citations, and release blockers.
- `human_review`: high-risk, low-confidence, judge-disagreement, or citation-support cases.

Data routing after human review:

- Passing high-risk answers are not `badcase`; use them as human-review calibration, positive regression examples, or preference winners.
- Partial answers with good legal analysis but missing escalation should become SFT/intake-routing examples.
- Source-boundary failures should become citation-grounding regression cases.
- Unsafe or deceptive drafting failures should stay in badcase and release-gate tests.

## Release Recommendation

No model-workflow configuration should be fully auto-released from this pilot alone.

Recommended first release gate:

- Allow limited auto-answer only for low-risk routine consultation under W1 when citation checks and risk tags are clean.
- Use W5 for intake and clarification where facts are missing.
- Require RAG plus citation verification for source-specific tasks, but route citation-bound answers to human review until claim-level entailment improves.
- Block or human-review all adversarial drafting, invented-evidence, fabricated-citation, and high-risk labor strategy outputs.
