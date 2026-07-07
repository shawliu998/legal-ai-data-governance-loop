# Runbook

This runbook explains how to reproduce the Legal AI Data Governance & Eval Harness from a fresh checkout.

The project is a diagnostic data-loop prototype. It is not a legal advice system, not a model leaderboard, and not an automatic legal correctness engine.

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

Mock mode is the default portfolio demo path because it is deterministic and does not require API keys.

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
- `Badcase_Cards`: interview-ready examples for human review or data routing.
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

API mode is optional. For a two-day portfolio submission, mock mode is enough to demonstrate the full data loop.

For a small DeepSeek-compatible smoke test, use `config.deepseek.smoke.yaml`. It selects 12 samples and 30 model runs to validate provider integration without turning the project into a model leaderboard. See `docs/api_smoke_run.md`.

## 8. Common Checks

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

## 9. Demo Script

For interview discussion:

1. Start with `Executive_Dashboard`.
2. Show `Dataset_Coverage` to explain the 40 core + 45 extended sample design.
3. Show `Task_Category_Summary` to explain task-specific evaluation.
4. Show `Badcase_Cards` to discuss 2-3 concrete failures.
5. Explain that Judge is an initial triage layer, while high-risk samples go to human review.
