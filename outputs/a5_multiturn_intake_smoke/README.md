# A5 Multi-Turn Intake Smoke Evidence Package

This directory contains a lightweight evidence package for the A5 multi-turn legal intake smoke test.

The smoke test evaluates trace-level behavior: material-fact elicitation, bad-premise challenge, safe redirection, human-review routing, and release decision.

## Scope

- Traces: 6
- Turns: 18
- Cases: 3
- Models: 2
- Trace pass rate: 1.0
- Average material fact coverage: 0.8333

## Included

- `trace_metrics_summary.csv`: high-level trace metrics.
- `turn_level_summary.csv`: redacted turn-level latency, token, status, and hash summary.
- `risk_route_summary.csv`: release decision counts by user behavior and legal domain.
- `redacted_trace_samples.csv`: one row per trace with output hashes only.
- `artifact_manifest.yaml`: machine-readable manifest and caveats.

## Caveats

- This is a small API smoke test, not a full benchmark.
- Deterministic trace checks are triage signals and need human calibration before production release.
- Full raw model outputs remain local/ignored.
