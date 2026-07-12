# Legal flywheel v0.2 independent regression stage

## Current status

The v0.2 stage is prepared but not released. The first expert round accepted one asset and required
rework for four. Those four now have revision-2 corrections and are back at `expert_review_pending`.
No v0.2 dataset version or test result has been released.

| Asset | Self-authored source | Blind-v2 A/B | Consolidated AI proposal |
| --- | --- | --- | --- |
| ASSET-REGRESSION-006 | L-006 | approve / approve | approve; revision 2 pending expert review |
| ASSET-REGRESSION-007 | L-014 | approve / approve | accepted by expert in round 1 |
| ASSET-REGRESSION-008 | L-019 | rework / approve | rework; revision 2 pending expert review |
| ASSET-REGRESSION-009 | L-021 | rework / approve | rework; revision 2 pending expert review |
| ASSET-REGRESSION-010 | L-034 | approve / approve | approve; revision 2 pending expert review |

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
- A real regression rerun is permitted only after legal-expert acceptance and v0.2 membership.

## Reproduction

```bash
legal-ai-data-loop build-independent-regression-candidates

legal-ai-data-loop prepare-flywheel-review \
  --mode api \
  --output outputs/flywheel/v0.2_independent_regression_review.csv

legal-ai-data-loop run-blind-reviews-v2 \
  --mode api \
  --asset-ids \
  ASSET-REGRESSION-006 ASSET-REGRESSION-007 ASSET-REGRESSION-008 \
  ASSET-REGRESSION-009 ASSET-REGRESSION-010

legal-ai-data-loop build-expert-review-bundle \
  --output outputs/flywheel/v0.2_independent_regression_final_review.csv

legal-ai-data-loop validate-v02-review-batch
```

The expert fills exactly four human fields for every row:

- `expert_decision`: `accepted`, `rework_required`, or `rejected`;
- `expert_override`: `yes` or `no`;
- `expert_override_reason`: actual item-level rationale;
- `self_reported_review_entry_seconds`: positive reviewer-entered duration, not instrumented active time.

After review, import the complete five-row file atomically. Any reworked asset must repeat correction,
A/B review, adjudication, QA, blind-v2, and final expert review for the new correction lineage.
