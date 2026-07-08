# Final Portfolio Findings

This is the one-page product conclusion for the legal data product portfolio.

The project should be presented as a legal AI product-boundary evaluation and data-governance system.
It is not a public model leaderboard.

## 1. Limited Auto-Answer Scope

Limited auto-answer is only appropriate for low-risk routine consultation.

Recommended policy:

- Use A1 structured legal counsel as the first candidate architecture.
- Allow only when there is no critical failure, no unsupported material claim, no fabricated citation, and no unresolved review disagreement.
- Keep high-risk labor, family, administrative penalty, accident, and adversarial drafting cases out of auto-answer.
- Treat model-level scores as deployment signals, not final rankings.

Product interpretation:

Routine consultation can be partially automated, but only behind risk tags and release gates.
The right product question is not "which model scored highest"; it is "which outputs are eligible for limited release."

## 2. RAG + Citation Gate Required

RAG is required for source-specific legal tasks, contract/document interpretation, and questions asking for grounded citations.

Recommended policy:

- Use A2 grounded retrieval counsel when the answer depends on a clause, statute excerpt, contract fragment, policy, or case summary.
- Do not treat retrieval recall as release readiness.
- Require source-boundary filtering, material-claim citation coverage, and claim-level support checks.
- Keep out-of-scope source use, fabricated citations, unsupported claims, and contradicted claims as release blockers pending human review.

Product interpretation:

The RAG V2 pilot showed why "adding retrieval" is not enough.
The project value is that it can locate unreleasable RAG behavior and turn it into retrieval hard negatives, citation SFT examples, preference pairs, and regression evals.

## 3. Clarification / A5 Intake Required

Clarification-first or multi-turn intake is required when the first user message lacks material facts or contains a risky premise.

Recommended policy:

- Use A4 for single-turn clarification before answering.
- Use A5 for multi-turn intake scenarios with cooperative, dependent, withdrawn, or adversarial user behavior.
- Evaluate A5 at the trace level: fact elicitation, bad-premise challenge, overclaim control, and human-review timing.
- Do not claim A5 is release-ready until human-calibrated trace labels are complete.

Product interpretation:

A5 has proven that the trace-level eval pipeline can run on real multi-turn legal intake traffic.
It has not proven autonomous legal intake readiness.

The next calibration priority is material-fact elicitation and overclaim control.

## 4. Human Review / Blocked Release

Human review is a product feature, not an eval failure.

Human review required:

- high-risk legal domains,
- missing material facts,
- unsafe or deceptive drafting requests,
- judge disagreement on route or critical failure,
- source-boundary or citation-support issues,
- overconfident win-rate or litigation-outcome claims.

Blocked release:

- fabricated citations,
- invented evidence or facts,
- contradicted source use,
- out-of-scope source use in source-limited tasks,
- unsupported material legal claims,
- missed escalation on high-risk cases.

Product interpretation:

The release gate should block critical failures and route uncertain but potentially useful outputs to human review.
The goal is controlled deployment, not maximal automation.

## 5. Failure-To-Data Routing

Each failure type should become a data asset.

| Failure pattern                         | Data route                 | Next data action                                                     |
| --------------------------------------- | -------------------------- | -------------------------------------------------------------------- |
| Missing material facts                  | `sft_candidate`            | Train intake prompts and fact-elicitation examples                   |
| Safer answer beats overconfident answer | `preference_candidate`     | Build preference pairs for calibrated legal advice                   |
| Fabricated citation or invented fact    | `badcase`                  | Add to P0 regression and release-blocker tests                       |
| Out-of-scope source use                 | `regression_eval`          | Create source-boundary regression cases and retrieval hard negatives |
| Unsupported material claim              | `human_review` / `badcase` | Human label support status, then route to citation SFT or regression |
| Repeated judge-human disagreement       | `eval_holdout`             | Preserve as judge calibration and future evaluator test set          |

Product interpretation:

The strongest part of the project is the data loop:
online or pilot failures become eval holdouts, SFT candidates, preference pairs, badcases, human-review rows, and regression tests.

## What Not To Claim

- Do not claim this is a statistically significant benchmark.
- Do not claim the controlled RAG corpus is a complete legal knowledge base.
- Do not claim claim entailment is final legal correctness.
- Do not claim Qwen-judge model scores are final rankings.
- Do not claim A5 is production-ready before human trace calibration.
