# Legal flywheel v0.2 independent regression stage

## Current status

The v0.2 stage is prepared but not released. The first expert round accepted one asset and required
rework for four. The second round required another rework for all four. The third round accepted two
more assets and required rework for two; the fourth round required another rework for those two.
Revision 5 for the remaining two assets was mechanically incomplete, so a deterministic QA gate—not
a fabricated expert decision—returned both to rework. In the complete revision-6 review, the expert
accepted 006 and required targeted legal rework for 009. Asset 009 now has a revision-7 correction,
fresh standard review/QA lineage, and revision-scoped blind-v2 evidence. It is the only asset at
`expert_review_pending`. No v0.2 dataset version or test result has been released.

| Asset | Self-authored source | Blind-v2 A/B | Consolidated AI proposal |
| --- | --- | --- | --- |
| ASSET-REGRESSION-006 | L-006 | approve / approve | accepted by expert at revision 6 |
| ASSET-REGRESSION-007 | L-014 | approve / approve | accepted by expert in round 1 |
| ASSET-REGRESSION-008 | L-019 | approve / approve | accepted by expert in round 3 |
| ASSET-REGRESSION-009 | L-021 | approve / approve | approve; revision 7 pending expert review |
| ASSET-REGRESSION-010 | L-034 | rework / approve | accepted by expert override in round 3 |

AI proposals cannot accept an asset. The legal expert must review the actual prompt, correction,
assertion, AI findings, and QA evidence in the restricted review CSV.

## Evidence boundary

- Sources come from `self_authored_core_40`; the adapted practice benchmark is excluded because its
  local manifest does not record a verifiable upstream license.
- The stored source baseline is a deterministic synthetic/mock engineering artifact. It is not real
  model-quality evidence.
- All five candidate sources are disjoint from the v0.1 SFT/preference train sources on source case,
  source snapshot, normalized prompt hash, and counterfactual family ID.
- Corrections and both review paths used real hosted model calls. Blind-v2 excludes gold labels,
  router output, historical review, and expert decisions.
- Blind-v2 event IDs and raw evidence paths are revision-scoped, so a rework cannot reuse or overwrite
  evidence from the prior correction.
- Correction generation now records provider `finish_reason`, rejects length-truncated outputs before
  storage, retries with a concise-output instruction, and uses a larger generation ceiling.
- QA also rejects empty answers, unbalanced Markdown delimiters, unclosed code fences, and long
  answers that stop without sentence-closing punctuation. Existing pending corrections that fail
  this mechanical gate are auditably requeued by `qa_system` without creating a legal-expert event.
- Release construction copies the bound expert submission and current blind-v2 raw outputs into the
  restricted release instead of relying on a manual evidence-copy step.
- A real regression rerun is permitted only after legal-expert acceptance and v0.2 membership.

## Reproduction

```bash
legal-ai-data-loop build-independent-regression-candidates

legal-ai-data-loop requeue-incomplete-corrections

legal-ai-data-loop prepare-flywheel-review \
  --mode api \
  --output outputs/flywheel/v0.2_independent_regression_review.csv

legal-ai-data-loop run-blind-reviews-v2 \
  --mode api \
  --asset-ids \
  ASSET-REGRESSION-006 ASSET-REGRESSION-007 ASSET-REGRESSION-008 \
  ASSET-REGRESSION-009 ASSET-REGRESSION-010

legal-ai-data-loop build-expert-review-bundle \
  --output outputs/flywheel/v0.2_independent_regression_all_remaining_final.csv

legal-ai-data-loop validate-v02-review-batch
```

The expert fills exactly four human fields for every row in the complete remaining-review bundle:

- `expert_decision`: `accepted`, `rework_required`, or `rejected`;
- `expert_override`: `yes` or `no`;
- `expert_override_reason`: actual item-level rationale;
- `self_reported_review_entry_seconds`: positive reviewer-entered duration, not instrumented active time.

After review, import the complete current pending-asset file atomically. Assets 006, 007, 008, and
010 are already accepted and are intentionally excluded from the editable row. Any newly reworked
asset must repeat correction, A/B review, adjudication, QA, blind-v2, and final expert review for the
new correction lineage; that later review cannot be eliminated without allowing unreviewed legal
text into a release.
