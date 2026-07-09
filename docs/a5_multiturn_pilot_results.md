# A5 Multi-Turn Intake Pilot Results

## Positioning

This is the full A5 pilot for trace-level legal intake evaluation.

It upgrades the earlier 3-case smoke into an 8-case, 3-model, 72-turn real API pilot.

The goal is not to claim that A5 is ready for autonomous legal intake.
The goal is to evaluate whether multi-turn agents can maintain product boundaries across user behavior variants.

## Run Shape

| Field               |                                          Value |
| ------------------- | ---------------------------------------------: |
| Cases               |                                              8 |
| Models              |                                              3 |
| Traces              |                                             24 |
| Turns               |                                             72 |
| User behavior types | cooperative, dependent, withdrawn, adversarial |
| Output package      |        `outputs/a5_multiturn_intake_pilot_v1/` |

Models:

- ERNIE 5.0
- DeepSeek V4 Pro
- Qwen3.5-27B

## Main Results

| Metric                           | Result |
| -------------------------------- | -----: |
| Trace pass rate                  |  75.0% |
| Average material fact coverage   |  77.1% |
| Bad-premise challenge rate       |   100% |
| Human-review recommendation rate |   100% |
| Safe redirection rate            |   100% |
| Overclaim trace count            |      6 |

Model-level deterministic trace signals:

| Model           | Traces | Trace pass rate | Avg material fact coverage | Overclaim traces |
| --------------- | -----: | --------------: | -------------------------: | ---------------: |
| DeepSeek V4 Pro |      8 |           87.5% |                      77.1% |                1 |
| ERNIE 5.0       |      8 |           50.0% |                      72.9% |                4 |
| Qwen3.5-27B     |      8 |           87.5% |                      81.3% |                1 |

Behavior-level deterministic trace signals:

| User behavior      | Traces | Trace pass rate | Avg material fact coverage | Overclaim traces |
| ------------------ | -----: | --------------: | -------------------------: | ---------------: |
| Adversarial client |      9 |           88.9% |                      74.1% |                1 |
| Cooperative client |      6 |           33.3% |                      83.3% |                4 |
| Dependent client   |      6 |           83.3% |                      72.2% |                1 |
| Withdrawn client   |      3 |          100.0% |                      83.3% |                0 |

## Product Interpretation

A5 is no longer only a runnable smoke test.
The project now has a full 8-case, multi-model trace pilot with redacted evidence and a human calibration template.

The result shows that the trace-level eval pipeline can run on real multi-turn legal intake traffic.
It does not support any A5 product-release claim.

The product finding is also more realistic than the smoke result:

- Multi-turn agents consistently challenged unsafe premises and routed high-risk matters to human review.
- Material-fact elicitation remained uneven, especially where the agent needed to balance empathy, issue spotting, and legal boundary control.
- The overclaim detector flagged 6 traces. These are not automatically confirmed legal errors; they are priority human-review candidates.
- Cooperative users were not necessarily easier. Some traces became overconfident when the user supplied more facts, which is a useful product-risk signal.

## Evidence Package

Committed lightweight artifacts:

- `trace_metrics_summary.csv`
- `turn_level_summary.csv`
- `risk_route_summary.csv`
- `redacted_trace_samples.csv`
- `redacted_trace_example.md`
- `human_trace_calibration_template.csv`
- `artifact_manifest.yaml`

Local-only artifacts:

- `trace_log.jsonl`
- `turn_log.csv`

The raw trace logs contain full model outputs and remain ignored by Git.

## Remaining Calibration Work

The next step is not more model calls. It is human calibration.

Review all 24 traces using `docs/a5_trace_judge_rubric.md`, with priority on:

- the 6 overclaim-flagged traces,
- guarantee/debt and false-litigation traces,
- traces where deterministic pass/fail may be a false positive or false negative,
- model differences between ERNIE 5.0 and the other two models.

The human review output should fill:

`outputs/a5_multiturn_intake_pilot_v1/human_trace_calibration_template.csv`

## Caveats

- Deterministic trace checks are triage signals, not final legal review.
- The pilot has 24 traces, enough for product diagnosis but not statistical model superiority claims.
- Overclaim detection is intentionally conservative and can produce false positives.
- Any A5 product-release claim requires human-calibrated trace labels first.
