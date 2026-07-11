# A5 Multi-Turn Intake Smoke Reference

This directory contains a lightweight evidence package for an A5 multi-turn legal intake run.

The run evaluates trace-level behavior: material-fact elicitation, bad-premise challenge, safe redirection, and a trace review recommendation.

## Status

This 6-trace / 18-turn package is an earlier smoke reference. The current portfolio evidence is the [24-trace / 72-turn pilot](../a5_multiturn_intake_pilot_v1/README.md).

## Scope

- Traces: 6
- Turns: 18
- Cases: 3
- Models: 2
- API-completed turns: 18
- Non-empty answer turns: 18
- Empty answer turns: 0
- Lexical overclaim flags requiring human calibration: 0

## Included

- `trace_metrics_summary.csv`: high-level trace metrics.
- `turn_level_summary.csv`: redacted turn-level latency, token, status, and hash summary.
- `risk_route_summary.csv`: trace review recommendation counts by user behavior and legal domain.
- `redacted_trace_samples.csv`: one row per trace with output hashes only.
- `redacted_trace_example.md`: one redacted trace summary for reviewer inspection.
- `human_trace_calibration_template.csv`: row-level human review template for A5 trace rubric scoring.
- `artifact_manifest.yaml`: machine-readable manifest and caveats.

## Caveats

- This is a limited API smoke/pilot run, not a full benchmark.
- No model behavior pass rate is reported before human trace calibration.
- `lexical_overclaim_flag` is a lexical triage signal, not a human-validated semantic overclaim finding.
- A zero lexical flag count does not establish that no semantic overclaim exists.
- Deterministic trace checks are triage signals and need human calibration before production release.
- Raw model outputs remain local/ignored and are excluded from the tracked evidence package.
