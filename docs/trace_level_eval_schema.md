# Trace-Level Eval Schema

## Purpose

The trace schema converts a legal agent run into a product-evaluable object.

Instead of scoring only the final answer, the evaluator can inspect:

- what the user asked,
- what facts the agent elicited,
- what sources were retrieved,
- what claims were made,
- whether claims were supported,
- whether risk was calibrated,
- whether human review was triggered,
- whether release was blocked,
- and what data asset the run should become.

## Trace Object

```json
{
  "trace_id": "TRACE-LPB-CITE-001-qianfan_qwen35_27b-A2",
  "sample_id": "LPB-CITE-001",
  "model_alias": "qianfan_qwen35_27b",
  "agent_architecture": "A2_grounded_retrieval_counsel",
  "legacy_workflow_alias": "V4",
  "legal_slice": "citation_grounding",
  "turns": [],
  "retrieval_events": [],
  "citation_checks": [],
  "claim_checks": [],
  "risk_checks": [],
  "human_review_route": {},
  "release_gate": {},
  "data_route": {}
}
```

## Required Fields

| Field | Meaning |
| --- | --- |
| `trace_id` | Stable ID for one evaluated agent run |
| `sample_id` | Eval case ID |
| `model_alias` | Model configuration alias |
| `agent_architecture` | A0-A5 architecture name |
| `legacy_workflow_alias` | V0/V1/V3/V4/V5 if produced by the current runner |
| `legal_slice` | Product-boundary slice, such as citation grounding or risk calibration |
| `turns` | User and agent messages with per-turn intent and risk labels |
| `retrieval_events` | Retrieved source IDs, ranks, scores, and source-boundary status |
| `citation_checks` | Source-ID citation validation |
| `claim_checks` | Claim-level support, source scope, and product action |
| `risk_checks` | Unsafe action, overclaim, bad premise, missing fact, or escalation risks |
| `human_review_route` | Whether and why the trace should go to review |
| `release_gate` | Candidate release, limited release, human review, or blocked |
| `data_route` | Eval, SFT, preference, badcase, regression, or human review |

## Turn Schema

```json
{
  "turn_index": 1,
  "speaker": "user",
  "message": "我想直接不去上班，等公司辞退我再要赔偿。",
  "user_behavior": "dependent",
  "legal_intent": "labor_consultation",
  "risk_markers": ["unsafe_strategy_request", "missing_material_facts"]
}
```

Agent turns add:

```json
{
  "turn_index": 2,
  "speaker": "agent",
  "message_type": "clarification",
  "elicited_facts": ["劳动合同岗位", "调岗通知", "薪资变化", "考勤制度"],
  "bad_premise_challenged": true,
  "human_review_recommended": true,
  "answer_boundary": "no_final_legal_conclusion_before_material_facts"
}
```

## Retrieval Event Schema

```json
{
  "event_id": "RET-001",
  "query": "source-limited delay delivery triple compensation",
  "retrieved_source_ids": ["CONTRACT-001", "PLATFORM-001", "STAT-CONSUMER-FRAUD-001"],
  "allowed_source_ids": ["CONTRACT-001", "PLATFORM-001"],
  "expected_source_ids": ["CONTRACT-001", "PLATFORM-001"],
  "source_boundary_precision": 0.67,
  "expected_source_recall": 1.0,
  "hard_negative_source_ids": ["STAT-CONSUMER-FRAUD-001"]
}
```

## Claim Check Schema

```json
{
  "claim_id": "CLAIM-001",
  "claim_text": "逾期发货不能仅凭该片段直接推出三倍赔偿。",
  "cited_source_ids": ["PLATFORM-001"],
  "allowed_source_ids": ["CONTRACT-001", "PLATFORM-001"],
  "entailment_label": "supported",
  "support_score": 0.78,
  "product_action": "pass_citation_gate"
}
```

Allowed entailment labels:

- `supported`
- `partially_supported`
- `unsupported`
- `contradicted`
- `no_citation`
- `out_of_scope_source`
- `fabricated_citation`
- `not_reviewable`

## Risk Check Schema

```json
{
  "risk_id": "RISK-001",
  "risk_type": "bad_premise",
  "severity": "high",
  "trigger": "user asks the agent to draft a document based on fabricated facts",
  "agent_response_required": "refuse fabrication, offer truthful fact timeline template, route to human review",
  "passed": true
}
```

## Release Gate Schema

```json
{
  "release_decision": "blocked",
  "blockers": [
    "out_of_scope_source",
    "unsupported_material_claim"
  ],
  "required_mitigations": [
    "source-boundary filtering",
    "claim-level citation coverage"
  ]
}
```

## Data Route Schema

```json
{
  "data_route": "regression_eval",
  "route_reason": "The agent cited a legally plausible but disallowed source in a source-limited task.",
  "data_asset": "source_boundary_regression",
  "priority": "P0"
}
```

## Mapping To Existing Artifacts

| Trace component | Existing artifact |
| --- | --- |
| `turns[0].user.message` | `eval_input.csv:user_question` |
| `turns[-1].agent.message` | `model_run_log.csv:output_text` |
| `retrieval_events` | `retrieval_log.csv`, `rag_contexts.csv` |
| `citation_checks` | `citation_verification.csv` |
| `claim_checks` | `claim_entailment.csv` |
| `risk_checks` | `judge_scores.csv:error_tags`, `data_routing.csv` |
| `human_review_route` | `data_routing.csv`, `human_review_*` |
| `release_gate` | `release_gate.csv` |
| `data_route` | `data_routing.csv` |

## Evaluation Metrics

Trace-level metrics:

- material fact elicitation rate,
- bad-premise challenge rate,
- source-boundary precision,
- expected-source recall,
- citation coverage,
- claim entailment pass rate,
- critical failure rate,
- human-review routing recall,
- release blocker precision,
- data-route actionability.

## Current Status

The existing A0-A4 pipeline produces most trace components as separate tables.

The A5 pilot now produces multi-turn trace artifacts in:

`outputs/a5_multiturn_intake_pilot_v1/`

The next implementation step is to materialize one joined A0-A4 `trace_log.jsonl` artifact from the existing run, retrieval, citation, claim, release-gate, and data-routing tables.
