# Legal flywheel v0.2 independent regression stage

## Current status

The v0.2 release is complete. The first expert round accepted one asset and required
rework for four. The second round required another rework for all four. The third round accepted two
more assets and required rework for two; the fourth round required another rework for those two.
Revision 5 for the remaining two assets was mechanically incomplete, so a deterministic QA gate—not
a fabricated expert decision—returned both to rework. In the complete revision-6 review, the expert
accepted 006 and required targeted legal rework for 009. Asset 009 now has a revision-7 correction,
fresh standard review/QA lineage, revision-scoped blind-v2 evidence, and final expert approval. All
five independent regression assets are accepted and included in `legal_flywheel_v0.2.0` as a source-
disjoint test split. The restricted release and public redacted evidence package both validate.

| Asset | Self-authored source | Blind-v2 A/B | Consolidated AI proposal |
| --- | --- | --- | --- |
| ASSET-REGRESSION-006 | L-006 | approve / approve | accepted by expert at revision 6 |
| ASSET-REGRESSION-007 | L-014 | approve / approve | accepted by expert in round 1 |
| ASSET-REGRESSION-008 | L-019 | approve / approve | accepted by expert in round 3 |
| ASSET-REGRESSION-009 | L-021 | approve / approve | accepted by expert at revision 7 |
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

## Official regression result

The official V5/W4 attempt 1 contains five real hosted-model reruns. The immutable attempt directory
was first scored with exact-topic assertion revision 2 and produced 0/5. Review found that several
failures were literal-match false negatives, so assertion revision 3 registered bounded semantic
aliases without changing any required topic. Deterministic rescoring of the same immutable outputs
produced 2/5 (40%): 006 and 010 passed; 007, 008, and 009 still failed genuine required-topic gates.

The append-only attempt ledger records both the original attempt hash and the scoring-v3 rescore.
No model call was deleted, overwritten, or repeatedly sampled to improve the result. The remaining
failures are product-diagnostic evidence, not legal-accuracy scores.

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

legal-ai-data-loop upgrade-regression-assertions-v3

legal-ai-data-loop build-dataset-release \
  --version legal_flywheel_v0.2.0 \
  --output-dir outputs/flywheel/legal_flywheel_v0.2.0

legal-ai-data-loop run-asset-regression \
  --mode api --force \
  --output outputs/flywheel/legal_flywheel_v0.2.0/regression_results.csv

legal-ai-data-loop rescore-regression-v3 \
  --output outputs/flywheel/legal_flywheel_v0.2.0/regression_results.csv

legal-ai-data-loop validate-dataset-release \
  --release outputs/flywheel/legal_flywheel_v0.2.0

python scripts/build_public_flywheel_release.py \
  --restricted outputs/flywheel/legal_flywheel_v0.2.0 \
  --output release/legal_flywheel_v0.2.0

python scripts/validate_public_flywheel_release.py \
  --release release/legal_flywheel_v0.2.0
```

The expert fills exactly four human fields for every row in the complete remaining-review bundle:

- `expert_decision`: `accepted`, `rework_required`, or `rejected`;
- `expert_override`: `yes` or `no`;
- `expert_override_reason`: actual item-level rationale;
- `self_reported_review_entry_seconds`: positive reviewer-entered duration, not instrumented active time.

The completed review files were imported atomically. Every reworked asset repeated correction, A/B
review, adjudication, QA, blind-v2, and final expert review for its new correction lineage; no earlier
revision's approval or QA was reused.
