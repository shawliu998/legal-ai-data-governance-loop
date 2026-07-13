# legal_flywheel_v0.2.0 — public evidence package

This package is the intentionally limited public view of a 15-asset legal-AI data flywheel pilot.
The full restricted release contains 5 SFT, 5 preference, and 5 source-disjoint independent regression-test assets, item-level legal-expert submissions,
source snapshots, blind-review raw outputs, and restricted model run logs.

The public package contains only:

- 2 redacted example assets permitted by the source release visibility policy;
- aggregate workflow metrics and the evidence-boundary report;
- five regression gate outcomes without raw prompts, answers, hashes, or internal rerun identifiers;
- a hash manifest describing included and deliberately excluded evidence.

The official V5/W4 attempt-1 produced 2 passed / 3 failed under scoring-v3 deterministic gates. Train and test sources are disjoint on source case, source snapshot, normalized user-prompt hash, and counterfactual family ID. This remains a pilot diagnostic estimate, not a legal-accuracy score or model leaderboard.
See `metrics_report.md` for the interpretation and immutable attempt history.

This material is diagnostic evaluation evidence, not legal advice or a production legal service.
Repository code is distributed under the project MIT License; source legal materials remain subject to
their original authority and are not republished in this public package.
