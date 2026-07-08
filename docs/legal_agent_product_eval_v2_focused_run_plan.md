# Legal Agent Product Eval V2 Focused Run Plan

## Purpose

This is the next formal experiment plan after the completed pilots.

The current repo already contains:

- 300-output real API product-boundary pilot,
- 72-output RAG V2 focused pilot,
- 24-trace A5 multi-turn intake pilot.

The focused run consolidates the main product question into one clearer experiment:

```text
50 legal product-boundary cases
x 3 Qianfan-accessible models
x 3 agent architectures
= 450 model outputs
```

## Why This Run

The current evidence is strong but split across several pilots.
The focused run creates a cleaner main line for interview and portfolio review.

It tests whether each model-agent configuration should:

- answer directly,
- use grounded sources,
- ask clarifying questions,
- route to human review,
- block release,
- or produce a reusable data asset.

## Config

Run-plan config:

`configs/experiments/legal_agent_product_eval_v2_focused.yaml`

This file is a planned experiment config.
It should not be described as completed until output artifacts are generated.

## Scope

Models:

- ERNIE 5.0
- DeepSeek V4 Pro
- Qwen3.5-27B

Agent architectures:

| Architecture | Legacy alias | Product role |
| --- | --- | --- |
| A1 structured legal counsel | V1 | Low-risk structured answer baseline |
| A2 grounded retrieval counsel | V4 | Source-grounded answer with citation checks |
| A4 clarification-first intake | V5 | Missing-fact and risk-calibration intake |

Dataset:

- `data/eval_sets/legal_product_boundary_pilot_v1.jsonl`
- 50 cases across normal, hard reasoning, risk calibration, citation grounding, adversarial, and counterfactual slices.

## Human Calibration

Target: 120 reviewed rows.

Priority rows:

- fabricated citation,
- unsupported material claim,
- out-of-scope source,
- release blocked,
- high-risk human review,
- counterfactual pair.

Keep at least 40 random rows so agreement metrics are not only priority-enriched.

## Expected Outputs

Lightweight committed package:

- `README.md`
- `artifact_manifest.yaml`
- `metrics_summary.csv`
- `release_gate_summary.csv`
- `human_calibration_summary.csv`
- `redacted_sample_outputs.csv`

Local full artifacts:

- `model_run_log.csv`
- `retrieval_log.csv`
- `rag_contexts.csv`
- `citation_verification.csv`
- `claim_entailment.csv`
- `judge_scores.csv`
- `data_routing.csv`
- `release_gate.csv`
- `executive_dashboard.xlsx`

## Success Criteria

The focused run is successful if it can produce:

- clear limited auto-answer rules,
- clear RAG-required rules,
- clear clarification-required rules,
- human-review and blocked-release policies,
- failure-to-data routing for SFT, preference, badcase, regression, and eval holdout.

It should still avoid public leaderboard claims.
