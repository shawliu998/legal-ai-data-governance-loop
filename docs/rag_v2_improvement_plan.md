# RAG V2 Improvement Plan

## Why V2 Is Needed

The first real API pilot proved that RAG is necessary for source-specific legal tasks, but it also exposed a product risk: retrieved context does not automatically make an answer grounded.

Observed V1 issues:

- The controlled corpus is useful for demonstration, but too small to represent a serious legal knowledge base.
- Some legal rules are summarized rather than represented as precise statute, contract, policy, or case text.
- Citation verification is mostly source-id and lexical-support based.
- The system can flag missing or out-of-scope citations, but cannot yet reliably decide whether a cited source actually entails the legal conclusion.
- W3/W4 workflows over-routed to human review and still produced source-boundary failures.

V2 should focus on citation reliability and product release gates, not simply on adding more documents.

## V2 Goals

1. Expand the controlled legal corpus while keeping source boundaries clear.
2. Upgrade citation verification from source-id matching to claim-level support checking.
3. Separate retrieval quality from answer quality.
4. Generate better data assets for grounding failures.
5. Re-run a smaller citation-focused API pilot to measure whether grounding failures decrease.

## Corpus Expansion

Target corpus size for V2:

| Source Type                  | Target Count | Purpose                                                                  |
| ---------------------------- | -----------: | ------------------------------------------------------------------------ |
| Statute or rule excerpts     |        40-60 | Ground common civil, labor, consumer, contract, and procedure claims.    |
| Contract clauses             |        20-30 | Test source-limited document interpretation.                             |
| Platform or company policies |        15-25 | Test internal-rule boundaries and employment scenarios.                  |
| Case rule summaries          |        20-30 | Test analogical reasoning without pretending to be full case retrieval.  |
| Evidence snippets            |        20-30 | Test whether outputs distinguish facts, evidence, and legal conclusions. |

Design principles:

- Every source has a stable `source_id`.
- Every source has `jurisdiction`, `source_type`, `effective_scope`, and `allowed_task_slice`.
- Source text should be exact enough to support or not support a claim.
- Similar but conflicting sources should be included to test retrieval discrimination.
- Some cases should explicitly restrict the model to a subset of sources.

## Claim-Level Citation Entailment

V2 should evaluate each important legal claim:

```text
claim -> cited source(s) -> entailment label -> product action
```

Proposed labels:

| Label                 | Meaning                                                               | Product Action                       |
| --------------------- | --------------------------------------------------------------------- | ------------------------------------ |
| `supported`           | The cited source directly supports the claim.                         | Can pass citation gate.              |
| `partially_supported` | The source supports part of the claim, but the answer overextends it. | Human review or revision.            |
| `unsupported`         | The source does not support the claim.                                | Badcase and regression eval.         |
| `contradicted`        | The source points against the claim.                                  | Release blocker.                     |
| `no_citation`         | Claim needed support but no citation was provided.                    | Human review and prompt/routing fix. |
| `out_of_scope_source` | The source may be true but was not allowed for this task.             | Source-boundary regression.          |

Minimal implementation:

- Extract 1-5 material claims from each output.
- Map each claim to cited source IDs.
- Ask a structured judge to label support using only the cited source text.
- Route unsupported or contradicted claims to badcase and regression eval.

Current implementation status:

- A deterministic first-pass command is implemented as `build-claim-entailment`.
- It emits `claim_entailment.csv` and `claim_entailment_summary.csv`.
- It supports allowed-source boundary checks through `--cases-jsonl`.
- It can be passed into `release-gate` through `--claim-entailment`.
- The controlled corpus has been expanded from 45 to 52 sources and a conflicting `POLICY-001` source was corrected to match the source-limited employment-policy case.
- False positives were reduced by filtering intake/question fragments and scoring combined cited sources for multi-source claims.
- It should be treated as triage before human review, not as final legal entailment.
- A focused RAG V2 pilot has now been run on 8 source-limited citation/document cases, 3 Qianfan-hosted models, and 3 workflows, producing 72 / 72 successful model outputs.
- The focused pilot evidence package is committed at `outputs/rag_v2_focused_pilot_v1/`.
- The focused pilot found 100% expected-source recall for W4/RAG retrieval, but only 0.50 average source-boundary precision because top-k retrieval also included extra sources.
- Claim-level triage found 555 citation-gate issues among 630 reviewable legal claims, mostly uncited material claims.
- W4/RAG improved citation coverage but introduced 74 out-of-scope source claims, so source-specific legal tasks still need source-boundary filtering and claim-level verification before release.

## Retrieval Metrics

Add retrieval-level checks before generation scoring:

| Metric                    | Question                                                         |
| ------------------------- | ---------------------------------------------------------------- |
| Context recall            | Did retrieval include the expected source?                       |
| Context precision         | Were top-k sources actually relevant?                            |
| Source-boundary precision | Did retrieval avoid disallowed sources for source-limited tasks? |
| Distractor resistance     | Did the model ignore retrieved but irrelevant sources?           |
| Citation coverage         | Did material claims cite sources when required?                  |
| Citation entailment       | Did cited sources support the claims?                            |

## V2 API Pilot Design

Do not rerun the full 300-output pilot first. Run a focused V2 pilot:

| Dimension    | Plan                                                   |
| ------------ | ------------------------------------------------------ |
| Cases        | 8-12 citation/document cases                           |
| Models       | Qwen3.5-27B, ERNIE 5.0, one challenger model           |
| Workflows    | W1 structured, W4 RAG-grounded, W5 clarification-first |
| Outputs      | 72-108                                                 |
| Human review | All citation failures plus 20 clean-looking passes     |

Primary hypothesis:

> Claim-level citation entailment will reduce false confidence in RAG outputs and produce better release-gate decisions than source-id verification alone.

Secondary hypotheses:

- Better source boundaries will reduce out-of-scope legal citations.
- W4 will improve only when retrieval precision and entailment checking are both present.
- Some source-specific tasks should still require human review even after RAG improves.

## Release Gate Changes

Add these V2 blockers:

- Any `contradicted` citation entailment label.
- Any `unsupported` material legal conclusion in a high-risk answer.
- Any answer that violates an explicit "only use these sources" instruction.
- Any generated source ID not present in retrieved or provided context.

Allow limited release only when:

- Retrieval includes expected sources.
- Material claims are cited.
- All material citation labels are `supported` or low-risk `partially_supported`.
- The task is not high-risk or adversarial.

## Data Production Loop

| Failure                                 | Data Asset                                   |
| --------------------------------------- | -------------------------------------------- |
| Source not retrieved                    | Retrieval eval and corpus metadata fix.      |
| Wrong source retrieved                  | Hard negative pair for retriever/reranker.   |
| Source cited but unsupported            | Citation entailment regression case.         |
| Out-of-scope source used                | Source-boundary badcase.                     |
| Good answer with calibrated uncertainty | Preference winner and positive eval example. |
| Correct refusal or clarification        | SFT/intake exemplar.                         |

## Success Criteria

V2 should be considered successful if:

- Citation-support failure rate drops on the focused citation slice.
- Human reviewers disagree less with automated citation labels.
- W4 grounded answers become safer without routing nearly every output to human review.
- The release gate can distinguish "RAG answer is grounded" from "RAG answer merely cites something."
