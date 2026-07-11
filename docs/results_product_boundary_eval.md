# Product-Boundary API Pilot Results

## Positioning

This report documents pilot-scale product and data evidence. It is not a public model leaderboard, a legal-accuracy benchmark, or a production-release approval.

## Evidence Layers

| Layer | Shape | Purpose | Boundary |
| --- | ---: | --- | --- |
| Mock/synthetic diagnostic | 50 cases × 5 synthetic model slots × 5 workflows = 1,250 runs | Stress-test run planning, schemas, routing, review sampling, and Dashboard | Not real model-quality evidence |
| Product-boundary API pilot | 12 cases × 5 Qianfan-hosted model slots × 5 workflows = 300 API runs | Observe API reliability, product-boundary signals, and release-risk patterns | 271 non-empty answers, 29 empty responses; not a powered benchmark |
| RAG V2 API pilot | 8 cases × 3 Qianfan-hosted model slots × 3 workflows = 72 API runs | Isolate retrieval, source boundary, citation coverage, and claim support | Controlled corpus and automated triage; not full legal retrieval reliability |
| A5 API pilot | 8 cases × 3 Qianfan-hosted model slots = 24 traces / 72 turns | Validate multi-turn logging and trace-level review design | Deterministic flags not yet human-calibrated |
| Priority human review | 80 enriched product-boundary records | Calibrate high-risk, citation, blocker, and routing decisions | Non-random; public labels cannot reproduce reviewer-level agreement |
| Focused V2 experiment | 50 × 3 × 3 = 450 planned runs | Proposed next formal experiment | Planned, not completed |

The model names are provider-hosted slots as exposed through Baidu AI Cloud Qianfan at run time. They should not be treated as identical to official model APIs or as clean foundation-model attribution.

## Product-Boundary API Run Integrity

| Check | Result |
| --- | ---: |
| Planned API run records | 300 |
| Unique run IDs | 300 |
| Non-empty model answers | 271 |
| Empty responses | 29 |
| Cases | 12 |
| Hosted model slots | 5 |
| Workflows | 5 |
| Structured judge rows | 300 |

The 300 records aggregate into 75 model-workflow-task slices. Under the current deterministic gate
policy, `release_gate_decision` contains 35 `blocked` and 40 `limited_release` slices, with no
`candidate_auto_answer` slice. These are policy outputs from this pilot—not production approvals,
human-confirmed error rates, or a model ranking.

The API client recorded all 300 calls with run-level status, but answer text inspection shows that 29 responses were empty. Accordingly, this project uses “300 API run records,” not “300 valid model outputs.” Judge JSON parseability is an engineering property and does not establish judge correctness.

## Artifacts

Public lightweight evidence:

- `outputs/product_boundary_api_pilot_v1/README.md`
- `artifact_manifest.yaml`
- `metrics_summary.csv`
- `release_gate_summary.csv`
- `claim_entailment_summary.csv`
- `human_calibration_summary_priority_80.csv`
- `redacted_sample_outputs_20.csv`

Full response text, detailed judge rows, retrieval logs, review workbooks, and raw traces remain local and are intentionally excluded from the public package.

## What The API Pilot Revealed

### 1. Reliability failures must remain in the denominator

An empty final answer can occur even when transport-level execution is recorded as successful. Product metrics should therefore distinguish attempted run, API success, non-empty answer, parseable structured answer, and releasable answer.

### 2. A judge score is not a release action

The Qwen3.5-27B hosted slot provided a parseable structured-judge baseline for the run set. Those scores are used as triage inputs only. They are affected by judge choice, prompt, model self-evaluation risk, empty answers, and the small case set.

Deployment decisions must separately consider critical failures, missing facts, source boundary,
citation support, and human-review requirements.

### 3. RAG retrieval is not release readiness

The first pilot and the focused RAG iteration both showed that retrieved context can coexist with uncited material claims, out-of-scope sources, unsupported claims, or contradicted claims. These automated labels are conservative queueing signals, not final legal entailment judgments.

For source-limited tasks, a response should not be released unless:

- every used source is allowed;
- material claims carry citations where required;
- cited text supports the associated claim;
- no fabricated, contradicted, or out-of-scope critical claim remains;
- unresolved cases are reviewed.

### 4. Human review changes data disposition

Two legal-background reviewers independently reviewed 80 priority-enriched records and reconciled disagreements. One reviewer holds a doctorate in law and passed China’s national unified legal professional qualification examination.

The public package does not preserve reviewer A/B labels. This version therefore does not report
reviewer agreement, judge-human agreement, Cohen's kappa, or a population accuracy estimate. The
sample is useful for process design and qualitative correction, not for extrapolating rates to all
API runs.

### 5. Provider-hosted reasoning and JSON need fallbacks

Targeted smoke tests surfaced empty final content and truncated structured responses on some hosted
endpoints. This observation is limited to the tested Qianfan configurations. It motivates separate
output budgets, schema retry/fallback, empty-response monitoring, and human escalation; it does not
establish a general defect in any named foundation model.

## RAG V2 Focused Pilot

```text
8 source-limited cases
× 3 Qianfan-hosted model slots
× 3 workflows
= 72 API run records
```

All 72 records contained non-empty answers. The pilot compared structured, grounded, and clarification-oriented workflows on a controlled corpus. Its primary contribution is the field and evidence design: retrieval metrics are separated from answer, source-boundary, citation, and claim-support signals.

Detailed report: [RAG V2 Focused Results](rag_v2_focused_results.md).

## A5 Multi-Turn Pilot

```text
8 cases
× 3 Qianfan-hosted model slots
= 24 traces / 72 turns
```

All 72 turn records show normal response status. The pilot validates trace collection, behavior
metadata, deterministic queueing rules, redacted evidence, and a human-calibration template. The
separate `trace_review_recommendation` field is `human_review_required` for all 24 traces by pilot
rule; it is a queue recommendation, not a trace quality label or record-level `response_policy`.

Because the 24 traces have not received reviewer-level calibration, this version does not report trace pass rate, model-level pass rate, or behavior-level quality percentages. Deterministic overclaim, fact-coverage, and redirection flags remain review-priority signals only.

Detailed report: [A5 Multi-Turn Pilot](a5_multiturn_pilot_results.md).

## Canonical Product Decisions

The design separates three concepts:

1. `response_policy`: what to do with the current answer—`auto_answer`, `grounded_answer`, `clarify`, `human_review`, or `block`.
2. `workflow_status`: where the record is in review—such as `pending_review`, `reviewed`, `blocked`, or `released`.
3. `data_asset_routes`: proposed downstream destinations—`eval`, `sft`, `preference`, `badcase`, or
   `regression`; only reviewed and accepted records become reusable assets.

The current router, Dashboard builder, release gate, and review-writeback path use this canonical
model. `release_decision` and `data_route` are retained only as compatibility aliases and are not
used for internal routing logic. Group-level deployment gating is stored separately as
`release_gate_decision`. A candidate route never means that an uncorrected failed answer is approved
as training gold.

## Release Policy

- Consider limited automatic answering only for low-risk, fact-sufficient records with no critical issue.
- Ask clarifying questions when material facts are missing.
- Require grounded retrieval and claim-support checks for source-specific tasks.
- Route high-risk or unresolved cases to human review.
- Block fabricated citations, invented evidence, unsafe action suggestions, contradicted critical claims, and material source-boundary violations.

No model-agent configuration should be fully auto-released from this pilot alone.

## Data Production Policy

| Reviewed failure pattern | Candidate assets | Required handling |
| --- | --- | --- |
| Missing material facts | `sft`, `eval` | Reviewer writes or approves the target intake behavior |
| Safer answer vs overconfident answer | `preference`, `regression` | Preserve both reviewed responses and pairing rationale |
| Fabricated citation or invented fact | `badcase`, `regression` | Keep as P0 release-blocker test; never use raw failure as positive SFT |
| Out-of-scope source use | `regression`, `eval` | Add source-boundary hard negative and allowed-source metadata |
| Unsupported material claim | `badcase`, `regression` | Human-label support span before reuse |
| Judge uncertainty | `eval` | Preserve for evaluator calibration after adjudication |

## What Not To Claim

- Do not call 300 API run records “300 valid answers.”
- Do not rank the hosted model slots from this small, judge-dependent pilot.
- Do not equate Qianfan-hosted slots with official model API performance.
- Do not treat automated claim labels as final legal correctness.
- Do not infer population rates from the 80-row priority review.
- Do not report reviewer agreement without reproducible reviewer A/B labels.
- Do not report A5 quality metrics before trace-level human calibration.
- Do not describe the planned 450-run experiment as completed.
