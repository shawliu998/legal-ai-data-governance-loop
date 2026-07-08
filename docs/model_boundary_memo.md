# Model Boundary Memo: Legal Product Eval

## Compared Models

- ERNIE 5.1
- DeepSeek V4 Pro
- Qwen3.5-27B
- GLM-5.2

The comparison is model-workflow based, not a public leaderboard. The unit of decision is whether a model-workflow configuration is suitable for a legal product policy: auto-answer, grounded answer, clarification-first, human review, or blocked.

## Main Findings

To be finalized after the 12-case Qianfan API pilot.

1. Best model/workflow for routine consultation:
2. Best model/workflow for citation-grounded answers:
3. Most conservative model under missing facts:
4. Most likely failure pattern:
5. Most cost-effective deployment policy:

## Product Policy

Auto-answer:

- Candidate scope: routine low-risk consultation where the workflow has no critical failure, no fabricated citation, and no unresolved judge disagreement.

RAG required:

- Citation-grounding tasks.
- Contract, document, or provided-source interpretation.
- Any answer that makes source-specific legal or factual claims.

Clarification required:

- Missing material facts.
- Ambiguous labor, contract, family, or dispute posture.
- Win-rate, litigation outcome, or probability questions.

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

## Data Policy

- `eval_holdout`: stable routine samples and counterfactual pairs for regression.
- `sft_candidate`: repeated missing-fact, evidence-warning, or intake-quality failures.
- `preference_candidate`: paired outputs where one answer is better calibrated or safer.
- `badcase`: critical failures, adversarial traps, fabricated citations, and release blockers.
- `human_review`: high-risk, low-confidence, judge-disagreement, or citation-support cases.

## API Pilot Plan

Run the 12-case pilot before finalizing model-specific claims:

```bash
.venv/bin/python -m legal_eval_harness.cli all \
  --input data/product_boundary_api_pilot_v1/dataset_manifest.yaml \
  --config config.qianfan_product_boundary_api_pilot.yaml \
  --mode api \
  --output-dir outputs/product_boundary_api_pilot_v1
```

Expected output scale:

- 12 cases
- 4 models
- 5 workflows
- 240 model outputs

After the API pilot, update this memo with observed model-workflow recommendations instead of average-score rankings.
