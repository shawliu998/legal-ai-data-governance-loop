# Model-Agent Product Boundary Memo

## Decision Unit

The unit of analysis is a model-slot × workflow × legal-case API run, not a foundation-model leaderboard score. The five slots were accessed through Baidu AI Cloud Qianfan and therefore include provider hosting, model version, prompt, retrieval, and generation-parameter effects.

## Pilot Shape

```text
12 legal product-boundary cases
× 5 Qianfan-hosted model slots
× 5 workflows
= 300 API run records
```

- 271 records contain non-empty model answers.
- 29 records contain empty responses, despite run-level status being recorded as successful.
- The five slots were ERNIE 5.0, DeepSeek V4 Pro, Qwen3.5-27B, GLM-5.2, and Kimi K2.6 as exposed through Qianfan at run time.
- Qwen3.5-27B was used as a structured judge baseline. Parseability is an engineering signal, not evidence of judge accuracy.
- Two legal-background reviewers independently reviewed 80 priority-enriched records and reconciled disagreements. The public evidence does not preserve reviewer A/B labels, so no agreement rate is reported.

## What The Pilot Supports

The pilot supports qualitative product-boundary findings:

1. Empty responses and schema failures must remain visible in reliability metrics.
2. Low-risk routine consultation may be considered for limited release only after critical checks pass.
3. Missing material facts should trigger clarification before substantive advice.
4. Source-specific tasks need grounded retrieval plus source-boundary, citation, and claim-support checks.
5. High-risk, coercive, deceptive, or unsupported outputs require human review or blocking.
6. A single judge score cannot determine release or training-data acceptance.

It does not support:

- a public ranking of the five model names;
- a conclusion about DeepSeek official API performance;
- statistical superiority between models or workflows;
- production legal-advice readiness;
- population accuracy inferred from the priority review sample.

## Canonical Product Actions

| Situation | `response_policy` | `workflow_status` | Proposed `data_asset_routes` |
| --- | --- | --- | --- |
| Low risk, facts sufficient, no critical issue | `auto_answer` | `released` after checks | `eval`, positive regression candidate |
| Answer depends on allowed sources and support checks pass | `grounded_answer` | `released` after checks | `eval`, grounded regression candidate |
| Material facts missing | `clarify` | `released` | `sft`, intake eval candidates after correction |
| High risk or unresolved uncertainty | `human_review` | `pending_review` | decided after review |
| Fabricated citation, unsafe action, invented evidence, contradicted source | `block` | `blocked` | `badcase`, `regression`; preference only with a reviewed safe counterpart |

`human_review` is not a final training-data asset. Likewise, a router-selected SFT or preference destination is only a candidate until correction, review, privacy checks, deduplication, and acceptance are complete.

## RAG Policy

RAG is required when an answer depends on a supplied clause, policy excerpt, contract fragment, statute excerpt, or other source-specific material. Retrieval alone is insufficient. Before release, the product should verify:

- retrieved sources fall within the allowed source boundary;
- material claims carry citations where required;
- cited passages support the associated claims;
- no critical claim is contradicted or fabricated;
- unresolved cases enter review rather than being auto-released.

The current RAG corpus is controlled and small. It tests the workflow, not full legal retrieval reliability.

## Human Review Policy

Human review is required for high-risk domains, missing facts with material consequences, coercive or deceptive drafting, unsafe action suggestions, unsupported material claims, source-boundary failures, and unresolved judge uncertainty.

Future review exports should preserve anonymous reviewer A/B labels, adjudicated labels, guideline version, timestamps, and conflict reasons so that IAA and routing performance can be independently reproduced.

## Release Recommendation

No model-agent configuration should be fully auto-released from this pilot alone. The next valid step is a larger preregistered evaluation with random blind review, reviewer-level labels, calibrated release metrics, and separate attribution for model, host, workflow, retrieval, and judge effects.
