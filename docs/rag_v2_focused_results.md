# RAG V2 Focused Pilot Results

## Positioning

This is a focused RAG reliability pilot, not a full legal knowledge-base benchmark.

The question is:

> When legal answers must stay inside provided or retrieved sources, does RAG actually make the
> answer safer enough for release?

The answer from this pilot is: retrieval improved evidence availability, but generation still needs
source-boundary enforcement and claim-level verification.

## Run Shape

| Field                   |                                                  Value |
| ----------------------- | -----------------------------------------------------: |
| Cases                   |               8 source-limited citation/document cases |
| Qianfan-hosted model slots |                                                   3 |
| Workflows               | V1 structured, V4 RAG-grounded, V5 clarification-first |
| API run records         |                                                     72 |
| Judge rows              |                                                     72 |
| RAG retrieval rows      |                                                     24 |
| Claim rows              |                                                   1766 |
| Reviewable legal claims |                                                    630 |

Lightweight evidence package:

`outputs/rag_v2_focused_pilot_v1/`

Full answer text remains local and ignored by Git. The committed package contains summaries and
redacted samples only.

## Main Results

| Metric                                            | Result |
| ------------------------------------------------- | -----: |
| Expected-source recall on V4/A2 RAG retrieval     | 100% across 24 controlled retrieval rows |
| Average source-boundary precision                 |   0.50 |
| Reviewable-claim strict citation-defect flags     | 555 / 630 (88.1%) |
| Reviewable-claim support needs-review flags       | 591 / 630 (93.81%; includes 36 `partially_supported`) |
| All-claim source-boundary blockers                 | 75 / 1766 (4.25%) |

The 88.1% figure is the trigger rate of a strict deterministic citation rule among 630 claims marked
reviewable. The release gate uses the broader 591/630 needs-review count: the 555 strict defects plus
36 `partially_supported` claims. The 4.25% blocker rate uses all 1,766 extracted claim rows as its
denominator and counts 75 `out_of_scope_source` or `contradicted` rows.

All three metrics are designed to surface claims that need citation repair, source-boundary filtering, or
human review. They are not answer-error rates, legal-accuracy rates, or human-confirmed labels.

Interpretation:

- Retrieval was good at finding the expected allowed sources.
- Retrieval was not strict enough about source boundary because top-k included extra sources.
- RAG-grounded answers cited more often, but citation coverage alone did not mean the cited source
  was allowed or sufficient.
- The largest remaining failure mode was material legal claims without explicit citation.

## Workflow Comparison

| Workflow               | All claim rows | Reviewable claims | Citation flags | Source-boundary blockers | Product interpretation |
| ---------------------- | -------------: | ----------------: | -------------: | -----------------------: | ---------------------- |
| V1 structured prompt   | 719 | 223 | 204 | 1 | Structured answer path still needs explicit citation requirements. |
| V4 RAG-grounded        | 743 | 285 | 240 | 74 | Retrieval adds citations but also concentrates out-of-scope-source flags. |
| V5 clarification-first | 304 | 122 | 111 | 0 | Intake behavior is not a substitute for a grounded final answer. |

## Failure Taxonomy

| Failure             | Count | Product action              |
| ------------------- | ----: | --------------------------- |
| No citation         |   489 | Human review and prompt fix |
| Out-of-scope source |    74 | Source-boundary regression  |
| Unsupported         |    18 | Badcase and regression eval |
| Contradicted        |     1 | Release blocker             |

Product conclusion:

- V4/A2 should not be described as "RAG-safe" from this pilot.
- Source-limited tasks need retrieval filtering, not just retrieval ranking.
- Material legal claims should be forced into a claim-citation schema before final answer.
- Out-of-scope source use should remain a release blocker even when the source itself is legally
  plausible.
- The project value is the ability to locate unreleasable RAG behavior and route it to review.
  Only reviewed and corrected records may then become hard-negative retrieval candidates, SFT
  examples, preference pairs, or regression evals.

## Deployment Policy

Auto-answer:

- Not recommended for source-limited legal QA in the current V2 pilot.

RAG required:

- Contract/document interpretation.
- Questions that explicitly ask to cite provided sources.
- Any answer that depends on a clause, policy, evidence excerpt, or case summary.

Human review required:

- Any out-of-scope source citation.
- Any unsupported or contradicted material legal claim.
- Any source-limited task with missing citation on a material claim.

Next data production:

- After review, add hard-negative retrieval candidates for the extra top-k sources.
- After correction and acceptance, create SFT examples that require every material claim to cite an
  allowed source.
- Create reviewed preference pairs where the winner refuses to overextend a source.
- Add confirmed source-boundary patterns to regression evals.

## Caveats

- Qwen judge scores are baseline signals, not final model rankings.
- Claim entailment is deterministic triage, not a final legal conclusion.
- The focused slice is intentionally hard on citation grounding and should not be generalized to all
  legal tasks.
