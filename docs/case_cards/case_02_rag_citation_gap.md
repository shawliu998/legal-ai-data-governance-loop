# Case 02: RAG Citation Gap

## User Scenario

An anonymized RAG sample, `LPB-CITE-001`, asks whether a consumer can directly claim triple
compensation for delayed shipment using only two provided sources: `CONTRACT-001` and
`PLATFORM-001`. Another source-limited sample, `LPB-CITE-002`, asks whether three late arrivals
allow direct employment termination using only `POLICY-001` and `POLICY-002`.

## Model Failure

The model retrieves or references plausible legal material but fails the product source boundary.
In the RAG V2 redacted evidence, `LPB-CITE-001` and related source-limited cases include outputs
with unsupported-claim labels, no-citation rows, and out-of-scope source counts. The failure is not
that retrieval found nothing; it is that the answer did not keep every material claim inside the
allowed source set.

## Product Risk

The product risk is false grounding. A user sees a cited answer and assumes it is source-supported,
while the answer may have added an external statute, omitted citation for the decisive claim, or
used a source that was plausible but not allowed for this task.

## Rubric Diagnosis

Relevant rubric dimensions:

- Expected-source recall.
- Source-boundary precision.
- Material-claim citation coverage.
- Claim-level support status.
- Fabricated, contradicted, or out-of-scope citation.

The RAG V2 focused pilot showed 100% expected-source recall on W4/RAG retrieval, but average
source-boundary precision was 0.50 and claim-level citation gates still surfaced release blockers.
That makes this a release-risk case, not a simple retrieval recall case.

## Human Review Decision

Route to human review when a material claim has no citation, cites an out-of-scope source, or is not
supported by the cited source. Reviewers should label whether the fix is citation formatting,
source-boundary filtering, claim deletion, or substantive legal review.

## Release Gate Decision

Block release for fabricated citation, contradicted source use, out-of-scope source use in a
source-limited task, or unsupported material legal claims. Do not treat retrieval recall alone as
release readiness.

## Data Routing

- `badcase`: fabricated, contradicted, or unsupported citation patterns.
- `regression`: source-boundary tests and hard-negative retrieval cases.
- `sft`: examples requiring every material claim to cite an allowed source.
- `preference`: safer answers that refuse to overextend weak sources.
- `human_review`: claim-support labeling and citation repair triage.

## Next Data Action

Build hard-negative retrieval pairs for extra top-k sources, add source-boundary regression cases,
and create answer-format examples that force material claims into an explicit claim-to-source
mapping.

## Why This Matters for Legal AI Data Product

Legal RAG is not just retrieval. A data product manager must define which sources are allowed, how
claims are checked against those sources, and which failures become release blockers or new data
assets.
