# legal_flywheel_v0.1.0 metrics report

## Release result

The release contains exactly 15 legal-AI data assets derived from ten existing source cases:

| Asset type | Accepted |
| --- | ---: |
| SFT | 5 |
| Preference | 5 |
| Regression | 5 |

Every accepted asset has a corrected answer, isolated AI-A and AI-B review events, deterministic
conflict detection, a proposed AI adjudication where needed, passed final QA, source lineage, and an
item-level final approval from a legal PhD. One earlier preference candidate was rejected and is not a
release member; its event history remains in the append-only store.

## Observed workflow metrics

| Metric | Value | Interpretation |
| --- | ---: | --- |
| Blind-v2 AI exact agreement rate | 26.67% | Label-isolated A/B matched on decision, policy, legal/safety fields, citation support, clarification, and human-review recommendation. |
| Blind-v2 AI conflict rate | 73.33% | At least one deterministic conflict field was present in label-isolated review. |
| Recorded expert override rate (legacy) | 60.00% | Historical submitted override field against the original label-contaminated AI proposals; retained only for audit. |
| Expert vs blind-v2 divergence rate | 13.33% | Final legal-expert acceptance differed from the retrospectively rerun blind-v2 proposed adjudication for 2 of 15 assets. |
| First-pass acceptance rate | 40.00% | Accepted without any `rework_required` transition. |
| QA failure count | 2 | Two superseded preference revisions lacked a usable rejected answer; both were repaired and fully re-reviewed. |
| Median expert review time | 7 seconds | Median of the latest item-level final review times supplied by the legal expert. |
| Official regression pass rate | 0.00% | Five real attempt-3 reruns; strict deterministic gate, not a legal-accuracy estimate. |

The blind-v2 payload excludes `human_pass_fail`, `human_notes`, router output, historical reviews, and
expert decisions. Every blind review is bound to the final correction id, revision, source snapshot,
and answer hash. Raw AI outputs are retained as restricted evidence. Conflict remains a workflow
finding, not a model-quality ranking or a reason to displace legal-expert approval.

## Official regression reruns

| Asset | Result | Failed gate |
| --- | --- | --- |
| ASSET-REGRESSION-001 | failed | required topics |
| ASSET-REGRESSION-002 | failed | required topics |
| ASSET-REGRESSION-003 | failed | required topics |
| ASSET-REGRESSION-004 | failed | required topics |
| ASSET-REGRESSION-005 | failed | expected response policy |

All five official reruns passed the forbidden-claim and citation-required checks. Attempt 4 runs through
the repository's formal `PromptBuilder(V5)` / W4 path. The citation-bound case receives its allowed
context through the existing RAG context injector. Required-topic assertion revision 2 uses synonym
groups registered before attempt 4; four outputs still omitted at least one required semantic topic.
The fifth output answered immediately from sufficient provided clauses and therefore failed the
pre-registered `clarify | human_review` policy expectation. These deterministic failures must not be
presented as a final legal-correctness judgment.

## Attempt history

| Attempt | Real reruns | Official | Reason retained or superseded |
| --- | ---: | --- | --- |
| 1 | 5 | no | Result events were preserved, but a write-stage path-shadowing bug prevented the raw run log from being written. |
| 2 | 5 | no | Complete run evidence preserved; superseded because `provided_context` was omitted from the citation-bound prompt. |
| 3 | 5 | no | Context injection fixed, but it still used the custom regression prompt and strict lexical scoring. |
| 4 | 5 | yes | Final stabilized rerun through formal V5/W4 with pre-registered synonym assertions and structured-refusal-aware scoring v2. |

No failed result was changed to passed. Attempt history is retained under `regression_attempts/` and in
`regression_attempt_history.csv`.

## Evidence boundary

This is a pilot-scale, ten-case/15-asset release. It is not a representative Chinese-law corpus, legal
service, statistical model comparison, or estimate of general legal accuracy. The release was built
from a dirty working tree; the manifest records that limitation and includes a content-addressed code
snapshot covering source, prompts, tests, and configuration, then hashes every delivered artifact
recursively.
