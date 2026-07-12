# legal_flywheel_v0.1.0 metrics report

## Release result and split boundary

The release contains 15 accepted assets: 5 SFT, 5 preference, and 5 regression bug reproductions.
The SFT and preference assets are train members. Because the five regression assets reuse SFT source
cases, they are classified as `bug_reproduction`, not an independent test split. Consequently the
cross-split contamination result is `not_applicable_no_independent_test_split`; no claim of an
independent regression-set estimate is made.

Future standard candidate builds require disjoint train/test sources and compare `source_case_id`,
`source_snapshot_id`, normalized user-prompt hash, and counterfactual family ID.

## Observed workflow metrics

| Metric | Value | Interpretation |
| --- | ---: | --- |
| Blind-v2 AI exact agreement rate | 26.67% | Label-isolated A/B exact agreement. |
| Blind-v2 AI conflict rate | 73.33% | At least one deterministic conflict field. |
| Expert vs blind-v2 divergence rate | 13.33% | Workflow divergence, not model ranking. |
| Self-reported review entry median | 7.0 seconds | Reviewer-entered duration; not instrumented active review time. |
| Official bug-reproduction pass rate | 0.00% | Five real attempt-4 reruns; strict product gates, not legal accuracy. |

## Official bug-reproduction reruns

| Asset | Result | Failed gate |
| --- | --- | --- |
| ASSET-REGRESSION-001 | failed | required topics |
| ASSET-REGRESSION-002 | failed | required topics |
| ASSET-REGRESSION-003 | failed | required topics |
| ASSET-REGRESSION-004 | failed | required topics |
| ASSET-REGRESSION-005 | failed | expected response policy |

Attempt 4 is the official V5/W4 view. Immutable attempt directories and the
append-only `regression_attempt_events.jsonl` are the system of record; `regression_results.csv`
is only the current official view. Failed results are retained and are not legal-correctness scores.

## Evidence boundary

This pilot is not a representative Chinese-law corpus, legal service, independent test estimate,
or model leaderboard. Full prompts, outputs, expert submissions, and lineage evidence remain restricted.
