# legal_flywheel_v0.2.0 metrics report

## Release result and split boundary

The release contains 15 accepted assets: 5 SFT, 5 preference, and 5 independent regression tests.
Train and test sources are disjoint across source case, source snapshot, normalized prompt hash,
and counterfactual family ID. The cross-split contamination check passed.

Future standard candidate builds require disjoint train/test sources and compare `source_case_id`,
`source_snapshot_id`, normalized user-prompt hash, and counterfactual family ID.

## Observed workflow metrics

| Metric | Value | Interpretation |
| --- | ---: | --- |
| Blind-v2 AI exact agreement rate | 33.33% | Label-isolated A/B exact agreement. |
| Blind-v2 AI conflict rate | 66.67% | At least one deterministic conflict field. |
| Expert vs blind-v2 divergence rate | 13.33% | Workflow divergence, not model ranking. |
| Self-reported review entry median | 12.0 seconds | Reviewer-entered duration; not instrumented active review time. |
| Official independent regression pass rate | 40.00% | Five real attempt-1 reruns under scoring-v3; strict product gates, not legal accuracy. |

## Official independent regression reruns

| Asset | Result | Failed gate |
| --- | --- | --- |
| ASSET-REGRESSION-006 | passed | none |
| ASSET-REGRESSION-007 | failed | required topics |
| ASSET-REGRESSION-008 | failed | required topics |
| ASSET-REGRESSION-009 | failed | required topics |
| ASSET-REGRESSION-010 | passed | none |

Attempt 1 under scoring-v3 is the official V5/W4 view. Immutable attempt directories and the
append-only `regression_attempt_events.jsonl` are the system of record; `regression_results.csv`
is only the current official view. Failed results are retained and are not legal-correctness scores.

## Evidence boundary

This pilot is not a representative Chinese-law corpus, legal service, statistically reliable
legal-accuracy estimate, or model leaderboard. Full prompts, outputs, expert submissions,
and lineage evidence remain restricted.
