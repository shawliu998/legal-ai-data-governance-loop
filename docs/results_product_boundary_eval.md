# Product Boundary Eval Results

## Positioning

This report is a product-boundary evaluation report, not a model leaderboard.

Core question:

> Which model-workflow configuration should answer, ask clarifying questions, use grounded sources, route to human review, block release, or generate a reusable data asset?

## Current Run Status

| Layer | Status |
| --- | --- |
| 50-case product-boundary dataset | Complete |
| Controlled RAG corpus and retrieval | Complete |
| Mock model-workflow diagnostic run | Complete |
| Judge ensemble design | Complete |
| Human calibration file | Complete for mock diagnostic outputs |
| 12-case Qianfan API pilot dataset | Prepared |
| Real Qianfan API outputs | Pending API credentials/run |

## Mock Diagnostic Artifacts

| Artifact | Path |
| --- | --- |
| Model outputs | `outputs/product_boundary_pilot_mock/model_run_log.csv` |
| Retrieval log | `outputs/product_boundary_pilot_mock/retrieval_log.csv` |
| RAG contexts | `outputs/product_boundary_pilot_mock/rag_contexts.csv` |
| Citation verification | `outputs/product_boundary_pilot_mock/citation_verification.csv` |
| Judge scores | `outputs/product_boundary_pilot_mock/judge_scores.csv` |
| Judge disagreements | `outputs/product_boundary_pilot_mock/judge_disagreements.csv` |
| Judge ensemble summary | `outputs/product_boundary_pilot_mock/judge_ensemble_summary.csv` |
| Data routing | `outputs/product_boundary_pilot_mock/data_routing.csv` |
| Release gate | `outputs/product_boundary_pilot_mock/release_gate.csv` |
| Human calibration | `outputs/product_boundary_pilot_mock/human_review_calibration_stratified.csv` |
| Chinese review file | `outputs/product_boundary_pilot_mock/human_review_calibration_stratified_zh.xlsx` |

Mock diagnostics produced:

- 50 cases.
- 5 model slots.
- 5 workflow conditions.
- 1250 normalized model outputs.
- 500 RAG-enabled outputs.
- 370 stratified human calibration rows.

## API Pilot Plan

The real API pilot is intentionally smaller than the mock diagnostic run:

| Field | Value |
| --- | --- |
| Dataset | `data/product_boundary_api_pilot_v1/dataset_manifest.yaml` |
| Source JSONL | `data/eval_sets/legal_product_boundary_api_pilot_v1.jsonl` |
| Config | `config.qianfan_product_boundary_api_pilot.yaml` |
| Output directory | `outputs/product_boundary_api_pilot_v1/` |
| Cases | 12 |
| Slices | 2 per slice |
| Models | ERNIE 5.0, DeepSeek V4 Pro, Qwen3.5-27B, GLM-5.2, Kimi K2.6 |
| Workflows | W0, W1, W2, W3, W4 |
| Expected model outputs | 300 |
| Judge ensemble | DeepSeek V4 Pro + GLM-5.2 primary judges, Kimi K2.6 arbiter, self-eval excluded |

Run command:

```bash
.venv/bin/python -m legal_eval_harness.cli all \
  --input data/product_boundary_api_pilot_v1/dataset_manifest.yaml \
  --config config.qianfan_product_boundary_api_pilot.yaml \
  --mode api \
  --output-dir outputs/product_boundary_api_pilot_v1
```

## Product Policy Conclusions

These conclusions are the policy frame to validate with real API outputs.

Auto-answer eligible:

- Low-risk `normal_practice` tasks.
- No critical failure.
- No fabricated citation or unsupported claim.
- No unresolved judge disagreement.
- Prefer W1/W3 over W0.

Grounding required:

- `citation_grounding` slice.
- Contract, document, or source-specific interpretation.
- Any answer that claims a rule, clause, or document basis.
- Prefer W2/W3 with citation verification.

Clarification-first required:

- Missing material facts.
- Ambiguous labor, contract, family, or procedural posture.
- Win-rate, lawsuit outcome, or probability questions.
- Prefer W4 when facts are insufficient.

Human review required:

- High-risk labor, marriage/family, accident, administrative penalty, or criminal-civil overlap.
- Deceptive or coercive document drafting.
- Unsupported legal claims or fabricated citations.
- Judge disagreement on risk, route, or critical failure.

Blocked from release:

- Fabricated citations.
- Invented evidence.
- Overconfident win probability.
- Missed human review on high-risk samples.
- Unsafe or deceptive action suggestions.

## Human Calibration Reporting Template

After the API pilot, report:

- Reviewed outputs:
- Judge-human agreement:
- Critical failure agreement:
- Citation-support disagreement:
- Most common judge error:
- Examples corrected by human review:

## Data Production Plan

| Failure Pattern | Route | Data Action |
| --- | --- | --- |
| Fabricated citation | `badcase`, `regression_eval` | Add to source-grounding regression set. |
| Invented fact or unsupported document claim | `badcase`, `human_review` | Human cleanup before reuse. |
| Overconfident win rate | `preference_candidate` | Build preference pairs favoring calibrated uncertainty. |
| Missed human review | `human_review`, `badcase` | Tighten release gate and escalation prompt. |
| Ignored material fact change | `eval_holdout` | Preserve counterfactual pair as holdout. |
| Weak clarification | `sft_candidate` | Add intake checklist examples. |

## Final Result Format

The final API result should not be written as:

```text
Model A: 86
Model B: 83
```

It should be written as:

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
