# Legal Agent Product Eval V2 Design

## Positioning

This project should be read as a legal agent product-boundary evaluation system, not as a prompt
leaderboard.

The evaluation asks whether a legal AI product should answer, ask for missing facts, retrieve
grounded sources, route to human review, block the response, or send a reviewed and corrected
failure toward a candidate data asset.

The older `V0` / `V1` / `V3` / `V4` / `V5` workflow names are implementation aliases. The
product-level interpretation should use the `A0`-`A5` agent architecture names below.

## Why This Is Not A Leaderboard

A legal product can fail even when the final answer sounds fluent.

Important failure modes include:

- missing material facts,
- unsafe or deceptive drafting,
- overconfident litigation-outcome claims,
- fabricated citations,
- out-of-scope source use,
- unsupported material legal claims,
- missed human-review escalation.

The output of the project is therefore not a ranked list of models. It is a set of release gates,
human-review routes, model-agent boundary decisions, and next-round data-production actions.

## Unit Of Evaluation

The core unit of evaluation is:

```text
model x agent architecture x legal slice x trace
```

This unit is intentionally broader than a final answer. It captures which model was used, which
product architecture constrained it, what legal slice it handled, and what happened across the
trace.

For single-turn runs, the trace includes the user message, model output, retrieval events, citation
checks, claim checks, risk checks, release gate, and data route.

For A5, the trace becomes multi-turn:

```text
turn_1_user -> turn_1_agent
turn_2_user -> turn_2_agent
...
final_route_or_answer
```

## Agent Architecture Conditions

| Architecture                     | Product meaning                                                      | Legacy alias | Evaluated capability                                                 |
| -------------------------------- | -------------------------------------------------------------------- | ------------ | -------------------------------------------------------------------- |
| A0 baseline closed-book          | Direct answer without product controls                               | V0           | Raw model capability and hallucination risk                          |
| A1 structured legal counsel      | Structured legal issue spotting and risk-calibrated answer           | V1           | Legal reasoning, missing-fact awareness, overclaim control           |
| A2 grounded retrieval counsel    | Retrieval-grounded answer using controlled sources                   | V4           | Source use, citation coverage, source-boundary discipline            |
| A3 verifier-router policy layer  | Post-generation risk/citation verifier and routing policy            | V3           | Release blocking, human-review routing, data routing                 |
| A4 clarification-first intake    | Single-turn intake that asks before answering when facts are missing | V5           | Material fact elicitation and bad-premise challenge                  |
| A5 multi-turn legal intake agent | Multi-turn intake simulator with user behavior variants              | New pilot    | Prioritized questioning, user resistance handling, escalation timing |

The A0-A5 taxonomy makes product decisions explicit and separates architecture choices from model
choices.

## Why 50 Cases Exist

The 50-case product-boundary bank is a focused legal traffic sample, not a statistically complete
legal benchmark.

It includes normal, hard, risk-calibration, citation-grounding, adversarial, and counterfactual
slices so the eval can test product behavior beyond average answer quality.

The 50-case size is large enough to exercise:

- multiple legal task slices,
- controlled source-limited tasks,
- adversarial or unsafe requests,
- near-identical counterfactual cases,
- release-gate and data-routing behavior.

## Why The Real API Pilot Used 12 Cases

The real API pilot used 12 cases because Qianfan model latency and cost varied significantly by
model and agent architecture.

The 12-case pilot still covered the product-boundary slices while producing:

```text
12 cases × 5 Qianfan-hosted model slots × 5 agent architectures = 300 API run records
```

The run set contains 271 non-empty answers and 29 empty responses. It was enough to exercise API
execution, empty-response monitoring, judge parsing, priority human review, release-gate generation,
and evidence-package production; it was not enough for model ranking.

## Why The Next Focused Experiment Is 450 API Run Records

The planned focused experiment is designed to strengthen the product evidence without pretending to
be a general legal benchmark.

The planned run shape is:

```text
50 cases x 3 models x 3 architectures = 450 planned API run records
```

The 450-run experiment is planned, not completed. It should focus on the architecture comparisons
that matter most for product release: structured counsel, grounded retrieval, and
clarification-first intake.

## Trace-Level Eval Versus Final-Answer Scoring

Final-answer-only scoring asks whether the last response looks good.

Trace-level eval asks whether the product behaved correctly along the way:

- Did the agent ask for material facts before reaching a conclusion?
- Did retrieval include allowed and expected sources?
- Did the answer cite sources when making material legal claims?
- Did cited sources actually support the claims?
- Did risk checks catch unsafe premises or overclaims?
- Did the system route to human review at the right time?
- Did the release gate block critical failures?
- After review, did the failure enter the right candidate data asset and acceptance workflow?

This matters because a legally polished final answer can still be unreleasable if it used
unsupported citations, skipped escalation, or violated source boundaries.

## Response Policy, Release Gates, And Data Routing

At record level, `response_policy` decides whether to auto-answer, provide a grounded answer,
clarify, enter human review, or block. At model-workflow-task-slice level,
`release_gate_decision` aggregates evidence into `candidate_auto_answer`, `limited_release`, or
`blocked`.

Blocking conditions include:

- fabricated citations,
- invented evidence or facts,
- contradicted source use,
- out-of-scope source use in source-limited tasks,
- unsupported material legal claims,
- missed escalation on high-risk cases.

After review, data routing turns each failure into a candidate next action:

| Failure pattern                         | Candidate data assets      |
| --------------------------------------- | -------------------------- |
| Missing material facts                  | `sft`, `eval`              |
| Safer answer beats overconfident answer | `preference`, `regression` |
| Fabricated citation or invented fact    | `badcase`, `regression`    |
| Out-of-scope source use                 | `regression`, `eval`       |
| Unsupported material claim              | `badcase`, `regression`    |
| Evaluator uncertainty                   | `eval`                     |

`human_review` is a workflow action, not a data asset. A candidate route does not approve an
uncorrected failure as training data.

## Current Implementation Mapping

| Layer                           | Current artifact                                               | Status                                           |
| ------------------------------- | -------------------------------------------------------------- | ------------------------------------------------ |
| A0-A4 prompts/workflows         | `prompts/`, `configs/pilots/qianfan_product_boundary_api_pilot.yaml`   | Implemented through legacy V aliases             |
| 50-case eval bank               | `data/eval_sets/legal_product_boundary_pilot_v1.jsonl`         | Implemented                                      |
| 300-run API pilot               | `outputs/product_boundary_api_pilot_v1/`                       | 271 non-empty answers / 29 empty responses       |
| RAG V2 focused pilot            | `outputs/rag_v2_focused_pilot_v1/`                             | Implemented with lightweight evidence package    |
| Claim-level citation triage     | `build-claim-entailment`                                       | Implemented as deterministic review-queue signal |
| Release gate                    | `release-gate`                                                 | Implemented                                      |
| A5 multi-turn intake cases      | `data/eval_sets/legal_agent_multiturn_intake_pilot_v1.jsonl`   | 8-case pilot added                               |
| A5 multi-turn intake full pilot | `outputs/a5_multiturn_intake_pilot_v1/`                        | 24 traces / 72 turns completed                   |
| Trace-level schema              | `docs/trace_level_eval_schema.md`                              | Design-level schema added                        |
| Focused V2 full-run plan        | `configs/experiments/legal_agent_product_eval_v2_focused.yaml` | Planned 450-run formal experiment                |

## A5 Multi-Turn Intake Goals

A5 tests whether an agent can manage a legal intake conversation, not just answer a static prompt.

It should evaluate:

- material-fact elicitation priority,
- whether the agent challenges bad premises,
- whether it avoids overconfident legal conclusions before facts are known,
- whether it adapts to cooperative, dependent, withdrawn, or adversarial users,
- whether it stops asking and routes to human review at the right time.

The current A5 pilot shows the trace-level eval pipeline can run, but it does not support any
product-release claim before human-calibrated trace labels are complete.
