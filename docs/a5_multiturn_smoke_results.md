# A5 Multi-Turn Intake Smoke Results

## Positioning

This is a small trace-level legal agent smoke test. It is not a model leaderboard and not a statistically powered benchmark.

The goal is to prove that A5 multi-turn legal intake can be evaluated as a trace:

```text
user turn -> agent intake response -> next user turn -> agent response -> release/data route
```

## Run Shape

| Field | Value |
| --- | ---: |
| Cases | 3 |
| Models | 2 |
| Traces | 6 |
| Turns | 18 |
| User behavior types | cooperative, dependent, adversarial |
| Output package | `outputs/a5_multiturn_intake_smoke/` |

Models:

- Qwen3.5-27B
- DeepSeek V4 Pro

Cases:

- `A5-INTAKE-001`: cooperative labor client
- `A5-INTAKE-002`: dependent labor client
- `A5-INTAKE-004`: adversarial debt-collection client

## Results

| Metric | Result |
| --- | ---: |
| Trace pass rate | 100% |
| Average material fact coverage | 83.3% |
| Bad-premise challenge rate | 100% |
| Human-review recommendation rate | 100% |
| Safe redirection rate | 100% |
| Overclaim trace count | 0 |

The 100% trace pass rate is a deterministic smoke-gate result. It means the runner, trace parser, and initial product-risk checks are working on this small sample; it should not be read as a human-validated legal correctness score.

## Product Interpretation

This smoke test moves A5 from design-only to a runnable trace-level eval loop.

The key product finding is not that the agents are ready for autonomous legal intake. The finding is that trace-level checks can expose whether the agent:

- asks for material facts across turns,
- challenges unsafe or dependent-user premises,
- redirects adversarial requests into lawful alternatives,
- recommends human review when the matter is high risk,
- and avoids overconfident legal conclusions.

All 6 traces routed to `human_review_required`, which is the right product posture for this smoke set. The selected cases intentionally include labor coercion and adversarial debt-collection risks.

## Evidence Package

Committed lightweight artifacts:

- `trace_metrics_summary.csv`
- `turn_level_summary.csv`
- `risk_route_summary.csv`
- `redacted_trace_samples.csv`
- `redacted_trace_example.md`
- `artifact_manifest.yaml`

Local-only artifacts:

- `trace_log.jsonl`
- `turn_log.csv`

The raw trace logs contain full model outputs and remain ignored by Git.

## Caveats

- Deterministic trace checks are smoke-test triage signals, not final legal review.
- These checks can miss subtle legal issues such as incomplete statutory grounding, weak issue framing, or inadequate escalation rationale.
- The sample is intentionally tiny: 3 cases and 2 models.
- The next step is human calibration on trace labels using the A5-specific rubric in `docs/a5_trace_judge_rubric.md`.
