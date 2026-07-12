# Legal flywheel v0.1 runbook

This runbook produces the first reviewable release: five SFT, five preference, and five same-source
regression bug reproductions. The v0.1 regressions are not an independent test split. JSONL is the
system of record. Scripts must not edit status fields directly; only
`AssetService` transitions state.

## 1. Build candidates

```bash
.venv/bin/legal-ai-data-loop build-asset-candidates \
  --data-dir data/flywheel \
  --allow-same-source-bug-reproduction
```

The explicit compatibility flag reconstructs this already-reviewed ten-case pilot and marks the five
reused sources as bug reproductions. Without that flag, the standard builder requires 15 distinct
evidenced source cases and assigns mutually exclusive SFT, preference, and regression sources.
Preference candidates require a non-empty reviewed failure response. Regression candidates receive
structured assertions and are never training eligible.

## 2. Prepare the expert review bundle

```bash
.venv/bin/legal-ai-data-loop prepare-flywheel-review \
  --mode api \
  --config configs/pilots/qianfan_product_boundary_eval.yaml \
  --reviewer-a-model qianfan_qwen35_27b \
  --reviewer-b-model qianfan_ernie_50 \
  --output outputs/flywheel/expert_review_bundle.csv
```

This is resumable. It drafts corrections, runs isolated AI-A and AI-B reviews, records deterministic
conflict detection and proposed AI adjudication, runs QA, and stops at `expert_review_pending`. Empty or
invalid model review output is retried but never converted into an approval event.

After final corrections are frozen, run the label-isolated audit protocol. It strips all historical
human/router/review signals, binds each output to the exact correction and snapshot, and stores raw
outputs as restricted evidence:

```bash
.venv/bin/legal-ai-data-loop backfill-asset-lineage
.venv/bin/legal-ai-data-loop run-blind-reviews-v2 --mode api
```

## 3. Legal PhD final review

The legal PhD reviews every row in `outputs/flywheel/expert_review_bundle.csv` and fills:

- `expert_decision`: `accepted`, `rework_required`, or `rejected`;
- `expert_override`: `yes` or `no`;
- `expert_override_reason`: the actual review rationale, including any override reason;
- `self_reported_review_entry_seconds`: positive reviewer-entered duration. It is not instrumented
  active review time and must not be presented as such.

Then import all decisions atomically after validation:

```bash
.venv/bin/legal-ai-data-loop apply-expert-review-bundle \
  --input outputs/flywheel/expert_review_bundle.csv
```

AI output must never be used to populate these human fields. If any asset is reworked or rejected, a
replacement/revision must repeat correction, both independent reviews, adjudication when needed, QA,
and final expert review before the release can contain it.

## 4. Build, rerun, and validate

```bash
.venv/bin/legal-ai-data-loop build-dataset-release \
  --version legal_flywheel_v0.1.0

.venv/bin/legal-ai-data-loop run-asset-regression \
  --force \
  --mode api \
  --config configs/pilots/qianfan_product_boundary_eval.yaml \
  --model-alias qianfan_deepseek_v4_pro \
  --output outputs/flywheel/legal_flywheel_v0.1.0/regression_results.csv

.venv/bin/legal-ai-data-loop validate-dataset-release \
  --release outputs/flywheel/legal_flywheel_v0.1.0
```

Every forced regression command creates a new immutable `regression_attempts/attempt_NN/` directory,
records restricted raw run evidence, usage metadata, prompt/output hashes, and five unique rerun IDs,
and appends to `regression_attempt_events.jsonl`. `regression_results.csv` is only the current official
view. The stabilized path uses `PromptBuilder(V5)` / W4 and assertion revision 2:

```bash
.venv/bin/legal-ai-data-loop upgrade-regression-assertions-v2
```

It updates the manifest and metrics with the observed pass rate. Failed
assertions remain failed; the runner does not rewrite results to improve the metric.

The release builder compares train and test members across `source_case_id`, `source_snapshot_id`,
normalized user-prompt hash, and counterfactual family ID. This v0.1 release has no independent test
members, so its cross-split contamination result is `not_applicable_no_independent_test_split`.

## Evidence boundary

This is a 15-asset pilot, not a representative legal corpus, model leaderboard, or production legal
service. The wording for the released package is: two independent isolated AI pre-reviews and AI
conflict consolidation were used, and every accepted asset was reviewed item-by-item and approved by a
legal PhD.
