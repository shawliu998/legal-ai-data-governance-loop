# Legal Agent Product Eval V2 Design

## Positioning

This project should be read as a legal agent product-boundary evaluation system, not as a prompt leaderboard.

The core unit of evaluation is:

```text
model x agent architecture x legal task slice x trace
```

The older `V0` / `V1` / `V3` / `V4` / `V5` workflow names are implementation aliases. The product-level interpretation should use the `A0`-`A5` agent architecture names below.

## Agent Architecture Taxonomy

| Architecture | Product meaning | Legacy alias | Evaluated capability |
| --- | --- | --- | --- |
| A0 baseline closed-book | Direct answer without product controls | V0 | Raw model capability and hallucination risk |
| A1 structured legal counsel | Structured legal issue spotting and risk-calibrated answer | V1 | Legal reasoning, missing-fact awareness, overclaim control |
| A2 grounded retrieval counsel | Retrieval-grounded answer using controlled sources | V4 | Source use, citation coverage, source-boundary discipline |
| A3 verifier-router policy layer | Post-generation risk/citation verifier and routing policy | V3 | Release blocking, human-review routing, data routing |
| A4 clarification-first intake | Single-turn intake that asks before answering when facts are missing | V5 | Material fact elicitation and bad-premise challenge |
| A5 multi-turn legal intake agent | Multi-turn intake simulator with user behavior variants | New pilot | Prioritized questioning, user resistance handling, escalation timing |

## Why This Matters

Legal AI product evaluation cannot stop at answer quality. The product has to decide:

- whether the agent should answer now,
- whether it needs retrieval,
- whether it should ask clarifying questions,
- whether the user is asking for unsafe or unsupported help,
- whether the answer can be released,
- and what data asset the failure should become.

The A0-A5 taxonomy makes those product decisions explicit. It also separates architecture choices from model choices.

## Trace-Level Eval Surface

Each evaluated interaction should be represented as a trace:

```text
user_message
agent_message
retrieval_events
citation_checks
claim_checks
risk_checks
human_review_route
release_gate
data_route
```

For A5, the trace becomes multi-turn:

```text
turn_1_user -> turn_1_agent
turn_2_user -> turn_2_agent
...
final_route_or_answer
```

The evaluation object is no longer only the final answer. It is the full path from user facts to retrieval, reasoning, escalation, release decision, and data routing.

## Current Implementation Mapping

| Layer | Current artifact | Status |
| --- | --- | --- |
| A0-A4 prompts/workflows | `prompts/`, `config.qianfan_product_boundary_api_pilot.yaml` | Implemented through legacy V aliases |
| 50-case eval bank | `data/eval_sets/legal_product_boundary_pilot_v1.jsonl` | Implemented |
| 300-output real API pilot | `outputs/product_boundary_api_pilot_v1/` | Implemented with lightweight evidence package |
| RAG V2 focused pilot | `outputs/rag_v2_focused_pilot_v1/` | Implemented with lightweight evidence package |
| Claim-level citation triage | `build-claim-entailment` | Implemented as deterministic review-queue signal |
| Release gate | `release-gate` | Implemented |
| A5 multi-turn intake cases | `data/eval_sets/legal_agent_multiturn_intake_pilot_v1.jsonl` | 8-case pilot added |
| A5 multi-turn intake smoke | `outputs/a5_multiturn_intake_smoke/` | 6 traces / 18 turns completed |
| A5 multi-turn intake full pilot | `outputs/a5_multiturn_intake_pilot_v1/` | 24 traces / 72 turns completed |
| Trace-level schema | `docs/trace_level_eval_schema.md` | Design-level schema added |
| Focused V2 full-run plan | `configs/experiments/legal_agent_product_eval_v2_focused.yaml` | Planned 450-output formal experiment |

## A5 Multi-Turn Intake Goals

A5 tests whether an agent can manage a legal intake conversation, not just answer a static prompt.

It should evaluate:

- material-fact elicitation priority,
- whether the agent challenges bad premises,
- whether it avoids overconfident legal conclusions before facts are known,
- whether it adapts to cooperative, dependent, withdrawn, or adversarial users,
- whether it stops asking and routes to human review at the right time.

## Product Release Policy

A0 and A1 can support low-risk draft answers only when no critical failure appears.

A2 is required for source-specific tasks, but the RAG V2 pilot shows that retrieval recall is not enough. Source-boundary and claim-level citation gates must pass before release.

A3 is a policy layer, not a user-facing answer mode. It is useful when release gates and human-review routing are the product requirement.

A4 is appropriate when the first user message lacks material facts.

A5 is required before claiming the product supports legal intake agents.
The current A5 pilot proves the trace-level eval pipeline can run, but it does not prove release readiness.

A5 should be evaluated on trace quality, material-fact elicitation, overclaim control, and human-review timing, not only final answer quality.
