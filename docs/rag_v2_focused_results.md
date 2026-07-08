# RAG V2 Focused Pilot Results

## Positioning

This is a focused RAG reliability pilot, not a full legal knowledge-base benchmark.

The question is:

> When legal answers must stay inside provided or retrieved sources, does RAG actually make the answer safer enough for release?

The answer from this pilot is: retrieval improved evidence availability, but generation still needs source-boundary enforcement and claim-level verification.

## Run Shape

| Field | Value |
| --- | ---: |
| Cases | 8 source-limited citation/document cases |
| Models | 3 |
| Workflows | V1 structured, V4 RAG-grounded, V5 clarification-first |
| Model outputs | 72 |
| Judge rows | 72 |
| RAG retrieval rows | 24 |
| Claim rows | 1766 |
| Reviewable legal claims | 630 |

Lightweight evidence package:

`outputs/rag_v2_focused_pilot_v1/`

Full raw outputs remain local and ignored by Git. The committed package contains summaries and redacted samples only.

## Main Results

| Metric | Result |
| --- | ---: |
| Expected-source recall on W4/RAG retrieval | 100% |
| Average source-boundary precision | 0.50 |
| Citation-gate issue rows | 555 |
| Citation-gate issue rate | 88.1% |
| Claim-level release blocker rows | 75 |
| Claim-level release blocker rate | 11.9% |
| Human-review rate under Qwen judge baseline | 54.2% |

The 88.1% citation-gate issue rate is a strict material-claim citation gate. It is designed to surface claims that would need citation repair, source-boundary filtering, human review, or data routing before release; it is not an overall model accuracy rate.

Interpretation:

- Retrieval was good at finding the expected allowed sources.
- Retrieval was not strict enough about source boundary because top-k included extra sources.
- RAG-grounded answers cited more often, but citation coverage alone did not mean the cited source was allowed or sufficient.
- The largest remaining failure mode was material legal claims without explicit citation.

## Workflow Comparison

| Workflow | Avg score | Citation coverage | Citation-gate issue rate | Release-blocker rate | Product interpretation |
| --- | ---: | ---: | ---: | ---: | --- |
| V1 structured prompt | 0.922 | 11.7% | 91.5% | 0.5% | Strong answer quality, weak citation discipline. |
| V4 RAG-grounded | 0.753 | 36.1% | 84.2% | 26.0% | Better citation coverage, but source-boundary failures block release. |
| V5 clarification-first | 0.814 | 9.8% | 91.0% | 0.0% | Safer intake behavior, not sufficient for source-grounded final answers. |

## Failure Taxonomy

| Failure | Count | Product action |
| --- | ---: | --- |
| No citation | 489 | Human review and prompt fix |
| Out-of-scope source | 74 | Source-boundary regression |
| Unsupported | 18 | Badcase and regression eval |
| Contradicted | 1 | Release blocker |

Product conclusion:

- W4 should not be released as "RAG-safe" yet.
- Source-limited tasks need retrieval filtering, not just retrieval ranking.
- Material legal claims should be forced into a claim-citation schema before final answer.
- Out-of-scope source use should remain a release blocker even when the source itself is legally plausible.
- The project value is the ability to locate unreleasable RAG behavior and convert it into hard-negative retrieval pairs, SFT examples, preference pairs, and regression evals.

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

- Add hard-negative retrieval pairs for the extra top-k sources.
- Create SFT examples that require every material claim to cite an allowed source.
- Create preference pairs where the winner refuses to overextend a source.
- Add source-boundary regression cases for each out-of-scope citation pattern.

## Caveats

- Qwen judge scores are baseline signals, not final model rankings.
- Claim entailment is deterministic triage, not a final legal conclusion.
- The focused slice is intentionally hard on citation grounding and should not be generalized to all legal tasks.
