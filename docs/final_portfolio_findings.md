# Final Portfolio Findings

This is the one-page product conclusion for the legal data product portfolio.

## What The Project Shows

The project should be presented as a legal AI product-boundary evaluation and data-governance
system. It is not a public model leaderboard.

The strongest part of the project is the data loop: pilot failures become eval holdouts, SFT
candidates, preference pairs, badcases, human-review rows, and regression tests.

## Main Product Findings

Limited auto-answer is only appropriate for low-risk routine consultation.

- Use A1 structured legal counsel as the first candidate architecture.
- Allow only when there is no critical failure, no unsupported material claim, no fabricated
  citation, and no unresolved review disagreement.
- Keep high-risk labor, family, administrative penalty, accident, and adversarial drafting cases out
  of auto-answer.
- Treat model-level scores as deployment signals, not final rankings.

RAG is required for source-specific legal tasks, contract/document interpretation, and questions
asking for grounded citations.

- Use A2 grounded retrieval counsel when the answer depends on a clause, statute excerpt, contract
  fragment, policy, or case summary.
- Do not treat retrieval recall as release readiness.
- Require source-boundary filtering, material-claim citation coverage, and claim-level support
  checks.
- Keep out-of-scope source use, fabricated citations, unsupported claims, and contradicted claims as
  release blockers pending human review.

Clarification-first or multi-turn intake is required when the first user message lacks material
facts or contains a risky premise.

- Use A4 for single-turn clarification before answering.
- Use A5 for multi-turn intake scenarios with cooperative, dependent, withdrawn, or adversarial user
  behavior.
- Evaluate A5 at the trace level: fact elicitation, bad-premise challenge, overclaim control, and
  human-review timing.
- Do not make an A5 product-release claim until human-calibrated trace labels are complete.

## Release Policy

Human review is a product feature, not an eval failure.

Human review is required for:

- high-risk legal domains,
- missing material facts,
- unsafe or deceptive drafting requests,
- judge disagreement on route or critical failure,
- source-boundary or citation-support issues,
- overconfident win-rate or litigation-outcome claims.

Blocked release applies to:

- fabricated citations,
- invented evidence or facts,
- contradicted source use,
- out-of-scope source use in source-limited tasks,
- unsupported material legal claims,
- missed escalation on high-risk cases.

The goal is controlled deployment, not maximal automation.

## Data Routing Policy

Each failure type should become a data asset.

| Failure pattern                         | Data route                 | Next data action                                                     |
| --------------------------------------- | -------------------------- | -------------------------------------------------------------------- |
| Missing material facts                  | `sft_candidate`            | Train intake prompts and fact-elicitation examples                   |
| Safer answer beats overconfident answer | `preference_candidate`     | Build preference pairs for calibrated legal advice                   |
| Fabricated citation or invented fact    | `badcase`                  | Add to P0 regression and release-blocker tests                       |
| Out-of-scope source use                 | `regression_eval`          | Create source-boundary regression cases and retrieval hard negatives |
| Unsupported material claim              | `human_review` / `badcase` | Human label support status, then route to citation SFT or regression |
| Repeated judge-human disagreement       | `eval_holdout`             | Preserve as judge calibration and future evaluator test set          |

## What Not To Claim

- Do not claim this is a statistically significant benchmark.
- Do not claim the controlled RAG corpus is a complete legal knowledge base.
- Do not claim claim entailment is final legal correctness.
- Do not claim Qwen-judge model scores are final rankings.
- Do not claim A5 product readiness before human trace calibration.
- Do not claim the priority-enriched human review sample represents all 300 real API outputs.
- Do not claim the 450-output focused experiment has been completed; it is planned.

## Next Step

The next step is to run the planned 450-output focused experiment and complete human-calibrated A5
trace review before making broader product-readiness claims.
