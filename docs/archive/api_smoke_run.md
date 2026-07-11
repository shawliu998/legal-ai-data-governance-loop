# DeepSeek API Smoke Run

> Archived provider-integration note. The current portfolio evidence is the Qianfan-hosted
> product-boundary, RAG V2, and A5 pilots; this 30-run note is not a DeepSeek capability result.

## Purpose

The API smoke run validates that the evaluation system can connect to an OpenAI-compatible provider
and process real model outputs through the same data-governance loop.

It is intentionally small:

- 12 selected samples
- 1 provider alias
- V0 and V3 full smoke versions
- V1 and V2 only for 3 deep badcases
- 30 model runs total

This is not a model ranking experiment.

## Configuration

Use:

```text
configs/pilots/deepseek.smoke.yaml
```

Environment variables:

```bash
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=<your_api_key>
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_JUDGE_MODEL=deepseek-v4-flash
```

The project uses the OpenAI-compatible client path, so DeepSeek is configured as an
`openai_compatible` provider.

## Smoke Sample Set

The smoke config selects:

- Labor consultation: `L-001`, `L-004`
- Contract/consumer consultation: `L-008`, `L-018`
- Case analysis: `L-025`, `L-032`, `X-CASE-008`
- Document drafting: `L-037`, `L-040`, `X-DOC-003`, `X-DOC-010`
- Extended consultation: `X-CONS-001`

Deep badcases:

- `L-004`
- `L-008`
- `L-040`

Expected run count:

```text
12 samples * 1 model * V0/V3 = 24
3 badcases * 1 model * V1/V2 = 6
Total = 30 model runs
```

## Run Commands

Prepare data:

```bash
.venv/bin/python -m legal_eval_harness.cli prepare-data \
  --input-workbook data/Legal_AI_Data_Governance_Eval_Harness_40_Core.xlsx \
  --output-dir data
```

Validate the smoke run plan:

```bash
.venv/bin/python -m legal_eval_harness.cli validate \
  --input dataset_manifest.yaml \
  --config configs/pilots/deepseek.smoke.yaml
```

Run real API mode:

```bash
.venv/bin/python -m legal_eval_harness.cli all \
  --input dataset_manifest.yaml \
  --config configs/pilots/deepseek.smoke.yaml \
  --mode api \
  --output-dir outputs/deepseek_smoke
```

Expected outputs:

```text
outputs/deepseek_smoke/model_run_log.csv
outputs/deepseek_smoke/judge_scores.csv
outputs/deepseek_smoke/data_routing.csv
outputs/deepseek_smoke/executive_dashboard.xlsx
```

## What To Inspect

Check run status:

```bash
.venv/bin/python - <<'PY'
import pandas as pd
runs = pd.read_csv("outputs/deepseek_smoke/model_run_log.csv")
print(runs["run_status"].value_counts())
print(runs[["sample_id", "version", "run_status", "output_length"]].head(20))
PY
```

Check Judge parse quality:

```bash
.venv/bin/python - <<'PY'
import pandas as pd
scores = pd.read_csv("outputs/deepseek_smoke/judge_scores.csv")
print(scores["parsed_ok"].value_counts())
print(scores[["sample_id", "version", "score_rate", "risk_level", "judge_confidence"]].head(20))
PY
```

Check route distribution:

```bash
.venv/bin/python - <<'PY'
import pandas as pd
routing = pd.read_csv("outputs/deepseek_smoke/data_routing.csv")
print(routing["data_route"].value_counts())
print(routing[["sample_id", "version", "main_error_type", "data_route", "priority"]].head(20))
PY
```

## Acceptance Criteria

The smoke run is successful if:

- At least 90% of model runs have `run_status = ok`.
- Judge output has `parsed_ok = true` for most rows.
- No protected gold fields appear in model-visible prompts.
- V2 outputs are generated from V0 output and visible input only.
- Router outputs only fixed `data_route` values.
- Dashboard can be opened and used for badcase review.

## How To Present Results

If API smoke run is completed, mention it as:

```text
In addition to deterministic mock mode, I ran a 30-run DeepSeek-compatible API smoke test to validate provider integration, JSON judge parsing, route stability, and dashboard generation on real model outputs.
```

Do not present the smoke run as a model leaderboard.

## Current Repository State

The repository includes the smoke-run configuration and commands.

Real API output files are not committed by default because they may contain provider-specific output
text and are reproducible from the documented command.
