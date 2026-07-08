# Runbook

This runbook explains how to reproduce the Legal AI Data Governance & Eval Harness from a fresh checkout.

The project is a diagnostic data-loop workflow. It is not a legal advice system, not a model leaderboard, and not an automatic legal correctness engine.

## 1. Environment Setup

From the project root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install .
cp .env.example .env
```

If package import fails in a local editable setup, use the installed wheel command above (`pip install .`) rather than editable install.

## 2. Data Preparation

The source workbook is:

```text
data/Legal_AI_Data_Governance_Eval_Harness_40_Core.xlsx
```

Generate the normalized dataset:

```bash
.venv/bin/python -m legal_eval_harness.cli prepare-data \
  --input-workbook data/Legal_AI_Data_Governance_Eval_Harness_40_Core.xlsx \
  --output-dir data
```

Expected outputs:

```text
data/eval_input.csv
data/gold_labels.csv
data/rubric_items.csv
```

Expected dataset shape:

- 85 samples
- 40 `self_authored_core_40` samples
- 45 `extended_diagnostic_45` samples
- 3 task categories: `consultation`, `case_analysis`, `document_drafting`
- 380 rubric rows
- `sample_metadata.csv` for difficulty, risk level, deep-badcase flag, and human-review flag. This metadata is not prompt-visible.

## 3. Validate Leakage Controls

Run:

```bash
.venv/bin/python -m legal_eval_harness.cli validate \
  --input dataset_manifest.yaml \
  --config config.yaml
```

Check that `Eval_Input` contains only model-visible fields:

- `sample_id`
- `source_dataset`
- `task_category`
- `user_question`
- `known_facts`
- `legal_concepts`
- `jurisdiction`
- `law_snapshot_date`
- `task_type`
- `legal_advice_boundary`

Gold-only fields must not appear in `Eval_Input`:

- `key_missing_facts`
- `expected_clarification_questions`
- `expected_answer_points`
- `risk_points`
- `expected_behavior`
- `rubric_items`
- `human_review_note`

## 4. Run the Mock Pipeline

Mock mode is the default reproducible path because it is deterministic and does not require API keys.

```bash
.venv/bin/python -m legal_eval_harness.cli all \
  --input dataset_manifest.yaml \
  --config config.yaml \
  --mode mock \
  --output-dir outputs
```

Expected pipeline shape:

- 85 samples
- 546 normalized model runs
- 546 judge score rows
- data routes across `eval`, `sft`, `preference`, `badcase`, and `human_review`

Expected output files:

```text
outputs/model_run_log.csv
outputs/judge_scores.csv
outputs/data_routing.csv
outputs/executive_dashboard.xlsx
```

## 5. Inspect the Dashboard

Open:

```text
outputs/executive_dashboard.xlsx
```

Key sheets:

- `Executive_Dashboard`: one-page data decision summary.
- `Dataset_Coverage`: source dataset and task category coverage.
- `Task_Category_Summary`: behavior patterns by legal task type.
- `Badcase_Cards`: concrete examples for human review or data routing.
- `Data_Routing_Summary`: counts by route and task category.
- `Error_Taxonomy`: standardized coarse error tags.
- `Data_Route_Taxonomy`: fixed route definitions.

Do not present this workbook as a model ranking report. It is a data production decision panel.

## 6. Run Tests

```bash
.venv/bin/python -m pytest -q
```

Expected:

```text
9 passed
```

The tests cover:

- gold label isolation
- prompt leakage checks
- task-specific judge prompt selection
- normalized run plan size
- JSON extraction
- fixed data route enum
- dashboard aggregation

## 7. Optional API Mode

Copy `.env.example` to `.env` and fill OpenAI-compatible provider settings:

```text
MODEL_A_BASE_URL=
MODEL_A_API_KEY=
MODEL_A_NAME=
```

Then run:

```bash
.venv/bin/python -m legal_eval_harness.cli all \
  --input dataset_manifest.yaml \
  --config config.yaml \
  --mode api \
  --output-dir outputs
```

API mode is optional. Mock mode is enough to validate the full data loop without external provider variance.

For a small DeepSeek-compatible smoke test, use `config.deepseek.smoke.yaml`. It selects 12 samples and 30 model runs to validate provider integration without turning the project into a model leaderboard. See `docs/api_smoke_run.md`.

## 8. Optional Practice Benchmark Pilot

Generate the separate licensed adapted practice pilot:

```bash
.venv/bin/python -m legal_eval_harness.cli prepare-practice-benchmark \
  --output-dir data/practice_benchmark_pilot \
  --case-limit 20 \
  --consultation-limit 6 \
  --document-limit 4
```

Validate the pilot manifest:

```bash
.venv/bin/python -m legal_eval_harness.cli validate \
  --input data/practice_benchmark_pilot/dataset_manifest.yaml \
  --config config.practice_pilot.yaml
```

Expected pilot shape:

- 30 samples
- 20 `case_analysis`
- 6 `consultation`
- 4 `document_drafting`
- 155 rubric rows
- 270 planned normalized runs

Run the pilot pipeline:

```bash
.venv/bin/python -m legal_eval_harness.cli all \
  --input data/practice_benchmark_pilot/dataset_manifest.yaml \
  --config config.practice_pilot.yaml \
  --mode mock \
  --output-dir outputs/practice_benchmark_pilot
```

This pilot is intentionally separate from `dataset_manifest.yaml` so the default diagnostic dataset remains stable.

## 9. Real API Deployment-Eval Smoke Run

After generating `data/practice_benchmark_pilot/`, configure `.env` for:

```text
DEEPSEEK_BASE_URL=
DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=

MODEL_B_BASE_URL=
MODEL_B_API_KEY=
MODEL_B_NAME=

MODEL_C_BASE_URL=
MODEL_C_API_KEY=
MODEL_C_NAME=

JUDGE_BASE_URL=
JUDGE_API_KEY=
JUDGE_MODEL=
```

Optional cost fields can be added for deployment tradeoff analysis:

```text
DEEPSEEK_INPUT_COST_PER_1K=
DEEPSEEK_OUTPUT_COST_PER_1K=
MODEL_B_INPUT_COST_PER_1K=
MODEL_B_OUTPUT_COST_PER_1K=
MODEL_C_INPUT_COST_PER_1K=
MODEL_C_OUTPUT_COST_PER_1K=
```

Run the real API smoke eval:

```bash
.venv/bin/python -m legal_eval_harness.cli all \
  --input data/practice_benchmark_pilot/dataset_manifest.yaml \
  --config config.practice_api_smoke.yaml \
  --mode api \
  --output-dir outputs/practice_api_smoke
```

Expected shape:

- 12 practice samples
- 3 model aliases
- 3 workflow conditions: `W0`, `W1`, `W3`
- 108 model outputs

Use the resulting `Executive_Dashboard`, `Cost_Latency`, `Deployment_Policy`, `Data_Routing_Summary`, and `Badcase_Cards` sheets to complete `docs/results_practice_api_smoke.md`.

Apply `docs/release_gate.md` before making any auto-answer or model-routing claim.

Generate a 20% human calibration sample. Critical rows are always prioritized:

```bash
.venv/bin/python -m legal_eval_harness.cli sample-human-review \
  --runs outputs/practice_api_smoke/model_run_log.csv \
  --scores outputs/practice_api_smoke/judge_scores.csv \
  --routing outputs/practice_api_smoke/data_routing.csv \
  --output outputs/practice_api_smoke/human_review_calibration.csv \
  --sample-rate 0.2 \
  --min-samples 20
```

If critical rows exceed 20% of outputs, the calibration file intentionally exceeds the target sample rate. Critical failures are review obligations, not optional samples.

Generate the release gate table:

```bash
.venv/bin/python -m legal_eval_harness.cli release-gate \
  --runs outputs/practice_api_smoke/model_run_log.csv \
  --scores outputs/practice_api_smoke/judge_scores.csv \
  --routing outputs/practice_api_smoke/data_routing.csv \
  --output outputs/practice_api_smoke/release_gate.csv
```

The release gate table groups by task, model, and workflow. It outputs:

- `release_decision`
- hard `blockers`
- `required_mitigations`
- critical failure, human review, and overclaim rates
- latency and cost fields

## 10. Qianfan Multi-Vendor Smoke Run

Qianfan ModelBuilder supports OpenAI-compatible calls through:

```text
https://qianfan.baidubce.com/v2
```

Configure `.env`:

```text
QIANFAN_BASE_URL=https://qianfan.baidubce.com/v2
QIANFAN_API_KEY=
QIANFAN_JUDGE_MODEL=

QIANFAN_MODEL_ERNIE_51=
QIANFAN_MODEL_DEEPSEEK_V4_PRO=
QIANFAN_MODEL_QWEN35_27B=
QIANFAN_MODEL_GLM_52=
```

Use exact model names from the Qianfan model center. If one vendor slot is unavailable, remove that model block from `config.qianfan_vendors_smoke.yaml` or leave only the vendors you can call.

Run:

```bash
.venv/bin/python -m legal_eval_harness.cli all \
  --input data/practice_benchmark_pilot/dataset_manifest.yaml \
  --config config.qianfan_vendors_smoke.yaml \
  --mode api \
  --output-dir outputs/qianfan_vendors_smoke
```

Expected default shape:

- 8 practice samples
- 4 Qianfan-hosted model vendor slots: ERNIE 5.1, DeepSeek V4 Pro, Qwen3.5-27B, GLM 5.2
- 3 workflow conditions: `W0`, `W1`, `W3`
- 96 model outputs

Generate calibration and release-gate files:

```bash
.venv/bin/python -m legal_eval_harness.cli sample-human-review \
  --runs outputs/qianfan_vendors_smoke/model_run_log.csv \
  --scores outputs/qianfan_vendors_smoke/judge_scores.csv \
  --routing outputs/qianfan_vendors_smoke/data_routing.csv \
  --output outputs/qianfan_vendors_smoke/human_review_calibration.csv

.venv/bin/python -m legal_eval_harness.cli release-gate \
  --runs outputs/qianfan_vendors_smoke/model_run_log.csv \
  --scores outputs/qianfan_vendors_smoke/judge_scores.csv \
  --routing outputs/qianfan_vendors_smoke/data_routing.csv \
  --output outputs/qianfan_vendors_smoke/release_gate.csv
```

Report this as a deployment policy experiment:

- Which task slice fits which vendor/model family?
- Which workflow reduces high-risk routing?
- Which failures become badcase, SFT, preference, or holdout eval?
- Which model-workflow combinations pass or fail release gates?

## 11. Stratified Product Boundary Eval

The stratified product-boundary eval is a JSONL suite designed to test normal, hard, risk, citation, adversarial, and counterfactual legal product traffic.

Validate it:

```bash
.venv/bin/python -m legal_eval_harness.cli validate-product-boundary \
  --input data/eval_sets/legal_product_boundary_pilot_v1.jsonl
```

Expected shape:

- 50 cases
- 6 `normal_practice`
- 6 `hard_legal_reasoning`
- 5 `risk_calibration`
- 5 `citation_grounding`
- 4 `adversarial_trap`
- 6 `counterfactual_pair`

Use `config.qianfan_product_boundary_eval.yaml` as the product-boundary experiment spec. The first version is intentionally schema-validated and mock-compatible; automatic RAG retrieval can be added later without changing the dataset schema.

Prepare normalized CSV files and a manifest for the existing runner:

```bash
.venv/bin/python -m legal_eval_harness.cli prepare-product-boundary \
  --input-jsonl data/eval_sets/legal_product_boundary_pilot_v1.jsonl \
  --output-dir data/product_boundary_pilot
```

Expected normalized shape:

- 50 samples
- 200 rubric rows
- task categories mapped into the current runner vocabulary:
  - `consultation`
  - `case_analysis`
  - `document_drafting`

Validate the runnable manifest:

```bash
.venv/bin/python -m legal_eval_harness.cli validate \
  --input data/product_boundary_pilot/dataset_manifest.yaml \
  --config config.qianfan_product_boundary_runnable.yaml
```

Expected planned run count:

```text
50 cases × 5 model slots × 5 current workflow versions = 1250 normalized runs
```

Current runnable workflow mapping:

- `V0` -> `w0_closed_book`
- `V1` -> `w1_structured_legal_prompt`
- `V4` -> `w2_rag_grounded` using local corpus retrieval and retrieved context injection
- `V3` -> `w3_risk_control_workflow`
- `V5` -> `w4_clarification_first`

Run the mock-compatible product-boundary pipeline:

```bash
.venv/bin/python -m legal_eval_harness.cli all \
  --input data/product_boundary_pilot/dataset_manifest.yaml \
  --config config.qianfan_product_boundary_runnable.yaml \
  --mode mock \
  --output-dir outputs/product_boundary_pilot_mock
```

RAG is enabled in `config.qianfan_product_boundary_runnable.yaml` for `V4` and `V3`. The corpus is `data/rag_corpus/legal_sources.csv`.

Expected RAG outputs:

- `retrieval_log.csv`: retrieved source IDs, expected source IDs, recall, precision, and retrieval status.
- `rag_contexts.csv`: source chunks injected into each RAG-enabled run.
- `citation_verification.csv`: cited source IDs, valid source IDs, fabricated source IDs, claim-level support checks, unsupported-claim counts, and citation-fidelity label.

Run judge ensemble calibration after `model_run_log.csv` exists:

```bash
.venv/bin/python -m legal_eval_harness.cli run-judge-ensemble \
  --input data/product_boundary_pilot/dataset_manifest.yaml \
  --config config.qianfan_product_boundary_runnable.yaml \
  --runs outputs/product_boundary_pilot_mock/model_run_log.csv \
  --mode mock \
  --output-dir outputs/product_boundary_pilot_mock
```

Expected ensemble outputs:

- `judge_ensemble_scores.csv`: one row per output and judge, with answer model, judge model, self-eval exclusion, and raw judge payload.
- `judge_disagreements.csv`: score gap, critical-failure mismatch, route mismatch, arbitration trigger, and arbiter used.
- `judge_ensemble_summary.csv`: per-run stable/arbitrated/human-calibration status and final risk route.

For API mode, set the Qianfan model env vars in `config.qianfan_product_boundary_runnable.yaml`. The default design uses DeepSeek V4 Pro and GLM-5.2 as primary judges, ERNIE 5.1 as arbiter, and blocks judge self-evaluation.

Build the legal-review calibration queue:

```bash
.venv/bin/python -m legal_eval_harness.cli sample-human-review \
  --runs outputs/product_boundary_pilot_mock/model_run_log.csv \
  --scores outputs/product_boundary_pilot_mock/judge_scores.csv \
  --routing outputs/product_boundary_pilot_mock/data_routing.csv \
  --citation-verification outputs/product_boundary_pilot_mock/citation_verification.csv \
  --ensemble-summary outputs/product_boundary_pilot_mock/judge_ensemble_summary.csv \
  --output outputs/product_boundary_pilot_mock/human_review_calibration.csv \
  --sample-rate 0.2 \
  --min-samples 120
```

If critical rows already exceed the target sample rate, the file intentionally grows beyond 20%. Critical failures are review obligations. For judge calibration and evaluation reporting, also create a stratified file that keeps all critical rows and adds routine non-critical samples across task, model, workflow, and risk strata:

```bash
.venv/bin/python -m legal_eval_harness.cli sample-human-review \
  --runs outputs/product_boundary_pilot_mock/model_run_log.csv \
  --scores outputs/product_boundary_pilot_mock/judge_scores.csv \
  --routing outputs/product_boundary_pilot_mock/data_routing.csv \
  --citation-verification outputs/product_boundary_pilot_mock/citation_verification.csv \
  --ensemble-summary outputs/product_boundary_pilot_mock/judge_ensemble_summary.csv \
  --output outputs/product_boundary_pilot_mock/human_review_calibration_stratified.csv \
  --sample-rate 0.2 \
  --min-samples 120 \
  --random-calibration-min 100
```

As the legal reviewer, fill `human_citation_support`, `human_unsupported_claims`, `human_route_override`, `human_data_action`, and `human_notes`. These fields are intentionally separate from automated judge labels so judge-human agreement can be measured later.

After review, summarize agreement and confirmed issues:

```bash
.venv/bin/python -m legal_eval_harness.cli summarize-human-calibration \
  --input outputs/product_boundary_pilot_mock/human_review_calibration.csv \
  --output outputs/product_boundary_pilot_mock/human_calibration_summary.csv
```

Mock release-gate decisions are only pipeline diagnostics. Do not interpret them as real deployment readiness until API outputs and human calibration are available.

## 12. Common Checks

Confirm output row counts:

```bash
.venv/bin/python - <<'PY'
import pandas as pd
for path in [
    "data/eval_input.csv",
    "data/gold_labels.csv",
    "data/rubric_items.csv",
    "outputs/model_run_log.csv",
    "outputs/judge_scores.csv",
    "outputs/data_routing.csv",
]:
    df = pd.read_csv(path)
    print(path, df.shape)
PY
```

Confirm route vocabulary:

```bash
.venv/bin/python - <<'PY'
import pandas as pd
print(sorted(pd.read_csv("outputs/data_routing.csv")["data_route"].unique()))
PY
```

Allowed values:

```text
eval, sft, preference, badcase, human_review
```

## 13. Walkthrough Script

For review discussion:

1. Start with `Executive_Dashboard`.
2. Show `Dataset_Coverage` to explain the 40 core + 45 extended sample design.
3. Show `Task_Category_Summary` to explain task-specific evaluation.
4. Show `Badcase_Cards` to discuss 2-3 concrete failures.
5. Explain that Judge is an initial triage layer, while high-risk samples go to human review.
