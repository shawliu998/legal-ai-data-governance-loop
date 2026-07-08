# Product Boundary API Pilot V1 Evidence Package

This directory contains a lightweight, GitHub-friendly evidence package for the real Qianfan API pilot.

The full raw run produced 300 model-workflow outputs across 12 legal product-boundary cases, 5 models, and 5 workflow configurations. The full raw CSV outputs remain local and are intentionally ignored by Git. This package commits summaries and redacted samples so reviewers can verify that the real API pilot exists without requiring the entire raw output set.

## Included

- `artifact_manifest.yaml`: artifact list, run shape, and methodology caveats.
- `metrics_summary.csv`: key run, judge, routing, RAG, claim entailment, release, and human review metrics.
- `release_gate_summary.csv`: release-gate count summary.
- `human_calibration_summary_priority_80.csv`: 80-row priority legal-review calibration summary.
- `claim_entailment_summary.csv`: claim-level citation entailment triage summary.
- `redacted_sample_outputs_20.csv`: representative rows with metadata, output length, and output hash; full output text is omitted.

## Key Caveats

- Model-level scores are Qwen-judge baseline signals, not final model rankings.
- Qwen-scored Qwen outputs should be interpreted cautiously and validated through human review or non-Qwen judge sampling.
- The 80-row legal review sample is priority-enriched for high-risk and likely blocker cases, not a random sample of all 300 outputs.
- Claim-level entailment labels are deterministic triage signals for review queues and release gates, not final legal conclusions.
- Full raw model outputs are not committed in this evidence package.
