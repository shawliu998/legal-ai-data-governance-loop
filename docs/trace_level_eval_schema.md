# Trace-Level Eval Schema

## Overview

The trace schema converts a legal agent run into a product-evaluable object.

Instead of scoring only the final answer, the evaluator can inspect what the user asked, what facts
the agent elicited, what sources were retrieved, what claims were made, whether those claims were
supported, whether risk was calibrated, whether human review was triggered, whether release was
blocked, and which data assets the reviewed record may become.

The schema applies to A0-A4 single-turn product-boundary runs and A5 multi-turn legal intake traces.

## Event Types

Trace-level evaluation can include these event groups:

| Event type           | Purpose                                                             |
| -------------------- | ------------------------------------------------------------------- |
| `turns`              | User and agent messages, with per-turn intent and risk labels       |
| `retrieval_events`   | Retrieved source IDs, ranks, scores, and source-boundary status     |
| `citation_checks`    | Source-ID citation validation and fabricated-citation checks        |
| `claim_checks`       | Claim-level support, source scope, entailment label, product action |
| `risk_checks`        | Unsafe action, overclaim, bad premise, missing fact, escalation     |
| `review_workflow`    | Whether and why the trace should go to human review                 |
| `response_control`   | Per-trace response policy and its required mitigations              |
| `release_gate`       | Optional group-level deployment decision for an evaluated slice    |
| `data_disposition`   | Reviewed eval, SFT, preference, badcase, or regression candidates   |

For A5, the `turns` array carries the multi-turn intake conversation. The other event groups can be
attached to the whole trace or to specific turns.

## Required Fields

| Field                | Meaning                                                                |
| -------------------- | ---------------------------------------------------------------------- |
| `trace_id`           | Stable ID for one evaluated agent run                                  |
| `sample_id`          | Eval case ID                                                           |
| `model_alias`        | Model configuration alias                                              |
| `agent_architecture` | A0-A5 architecture name                                                |
| `legal_slice`        | Product-boundary slice, such as citation grounding or risk calibration |
| `turns`              | Ordered user and agent messages                                        |
| `review_workflow`    | Whether and why the trace should go to review                          |
| `response_control`   | `auto_answer`, `grounded_answer`, `clarify`, `human_review`, or `block` |
| `data_disposition`   | Reviewed eval, SFT, preference, badcase, or regression candidates      |

## Optional Fields

| Field                   | Meaning                                                           |
| ----------------------- | ----------------------------------------------------------------- |
| `legacy_workflow_alias` | V0/V1/V3/V4/V5 if produced by the current runner                  |
| `retrieval_events`      | Retrieved source IDs, expected-source recall, source precision    |
| `citation_checks`       | Cited source IDs, fabricated citation IDs, citation-fidelity label |
| `claim_checks`          | Extracted claims, cited sources, support labels, product actions  |
| `risk_checks`           | Unsafe action, overclaim, bad-premise, or missing-fact checks     |
| `judge_scores`          | Rubric scores and error tags from automated judges                |
| `human_labels`          | Human calibration labels when review has been completed           |
| `release_gate`          | Group-level `candidate_auto_answer`, `limited_release`, or `blocked` |

## Example JSON Object

```json
{
  "trace_id": "TRACE-LPB-CITE-001-qianfan_qwen35_27b-A2",
  "sample_id": "LPB-CITE-001",
  "model_alias": "qianfan_qwen35_27b",
  "agent_architecture": "A2_grounded_retrieval_counsel",
  "legacy_workflow_alias": "V4",
  "legal_slice": "citation_grounding",
  "turns": [
    {
      "turn_index": 1,
      "speaker": "user",
      "message": "请只根据合同片段判断逾期发货是否能要求三倍赔偿。",
      "legal_intent": "source_limited_document_interpretation",
      "risk_markers": ["source_limited_task"]
    },
    {
      "turn_index": 2,
      "speaker": "agent",
      "message_type": "answer",
      "answer_boundary": "limited_to_provided_sources"
    }
  ],
  "retrieval_events": [
    {
      "event_id": "RET-001",
      "query": "source-limited delay delivery triple compensation",
      "retrieved_source_ids": [
        "CONTRACT-001",
        "PLATFORM-001",
        "STAT-CONSUMER-FRAUD-001"
      ],
      "allowed_source_ids": ["CONTRACT-001", "PLATFORM-001"],
      "expected_source_ids": ["CONTRACT-001", "PLATFORM-001"],
      "source_boundary_precision": 0.67,
      "expected_source_recall": 1.0,
      "hard_negative_source_ids": ["STAT-CONSUMER-FRAUD-001"]
    }
  ],
  "citation_checks": [
    {
      "citation_id": "CITE-001",
      "cited_source_id": "PLATFORM-001",
      "citation_fidelity": "valid_source_id"
    }
  ],
  "claim_checks": [
    {
      "claim_id": "CLAIM-001",
      "claim_text": "逾期发货不能仅凭该片段直接推出三倍赔偿。",
      "cited_source_ids": ["PLATFORM-001"],
      "allowed_source_ids": ["CONTRACT-001", "PLATFORM-001"],
      "entailment_label": "supported",
      "support_score": 0.78,
      "product_action": "pass_citation_gate"
    }
  ],
  "risk_checks": [
    {
      "risk_id": "RISK-001",
      "risk_type": "source_boundary",
      "severity": "high",
      "trigger": "answer must stay inside provided contract and platform sources",
      "passed": true
    }
  ],
  "review_workflow": {
    "required": true,
    "workflow_status": "pending_review",
    "reason": "source-limited task with claim-level citation checks"
  },
  "response_control": {
    "response_policy": "human_review",
    "blockers": [],
    "required_mitigations": ["human citation-support review"]
  },
  "data_disposition": {
    "data_asset_routes": ["eval"],
    "route_reason": "source-limited legal claim needs human support validation",
    "acceptance_status": "candidate_pending_review",
    "priority": "P1"
  }
}
```

Allowed claim entailment labels:

- `supported`
- `partially_supported`
- `unsupported`
- `contradicted`
- `no_citation`
- `out_of_scope_source`
- `fabricated_citation`
- `not_reviewable`

## Expected Output Artifacts

Trace components currently appear across separate artifacts:

| Trace component           | Existing artifact                                 |
| ------------------------- | ------------------------------------------------- |
| `turns[0].user.message`   | `eval_input.csv:user_question`                    |
| `turns[-1].agent.message` | `model_run_log.csv:output_text`                   |
| `retrieval_events`        | `retrieval_log.csv`, `rag_contexts.csv`           |
| `citation_checks`         | `citation_verification.csv`                       |
| `claim_checks`            | `claim_entailment.csv`                            |
| `risk_checks`             | `judge_scores.csv:error_tags`, `data_routing.csv` |
| `review_workflow`         | `data_routing.csv`, `human_review_*`              |
| `response_control`        | `data_routing.csv`                                |
| `release_gate`            | `release_gate.csv:release_gate_decision`          |
| `data_disposition`        | `data_routing.csv`                                |

The existing A0-A4 pipeline produces most trace components as separate tables.

The A5 pilot now produces multi-turn trace artifacts in:

```text
outputs/a5_multiturn_intake_pilot_v1/
```

The next implementation step is to materialize one joined A0-A4 `trace_log.jsonl` artifact from the
existing run, retrieval, citation, claim, release-gate, and data-routing tables.
