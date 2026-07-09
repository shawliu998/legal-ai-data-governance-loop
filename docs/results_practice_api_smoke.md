# Practice API Smoke Results

## Positioning

This report evaluates model-workflow configurations for legal AI deployment decisions. It is not a
model leaderboard and does not provide legal advice.

Core question:

> Which model-workflow configurations are suitable for which legal task slices, under what risk
> controls, and what data assets should be produced from failures?

## Run Metadata

Fill after the API run:

| Field                  | Value                                                                      |
| ---------------------- | -------------------------------------------------------------------------- |
| Dataset manifest       | `data/practice_benchmark_pilot/dataset_manifest.yaml`                      |
| Config                 | `config.practice_api_smoke.yaml`                                           |
| Output directory       | `outputs/practice_api_smoke`                                               |
| Human calibration file | `outputs/practice_api_smoke/human_review_calibration.csv`                  |
| Release gate file      | `outputs/practice_api_smoke/release_gate.csv`                              |
| Sample count           | 12                                                                         |
| Model aliases          | `DeepSeek_Target`, `Strong_Closed_Baseline`, `Open_or_CN_Baseline`         |
| Workflows              | `W0 closed-book`, `W1 structured legal prompt`, `W3 risk-control workflow` |
| Total model outputs    | 108                                                                        |
| Judge mode             | API                                                                        |
| Human review sample    | TODO                                                                       |

## Hypotheses

| Hypothesis                                                                                | Product Meaning                                                   | Result |
| ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | ------ |
| H1: Structured workflows reduce overclaim on incomplete legal facts.                      | Decide whether direct answer should be allowed for consultation.  | TODO   |
| H2: Higher-capability models help case analysis more than routine document drafting.      | Decide model routing by task type.                                | TODO   |
| H3: Risk-control workflow increases human_review routing but reduces critical failures.   | Decide release gate and escalation policy.                        | TODO   |
| H4: Citation or legal-basis failures should become regression badcases, not SFT examples. | Decide data route by failure type.                                | TODO   |
| H5: Cost/latency tradeoffs differ by task slice.                                          | Decide whether to use expensive models only for high-risk slices. | TODO   |

## Executive Findings

Replace TODO with metrics from `outputs/practice_api_smoke/executive_dashboard.xlsx`.

1. TODO: Best auto-answer candidate slice.
2. TODO: Highest-risk task/workflow combination.
3. TODO: Workflow that most improves overclaim control.
4. TODO: Main cost/latency tradeoff.
5. TODO: Highest-priority data production action.

## Task Slice Policy

| Task Slice        | Recommended Workflow | Model Policy | Human Review Policy | Data Production |
| ----------------- | -------------------- | ------------ | ------------------- | --------------- |
| Consultation      | TODO                 | TODO         | TODO                | TODO            |
| Case analysis     | TODO                 | TODO         | TODO                | TODO            |
| Document drafting | TODO                 | TODO         | TODO                | TODO            |

## Deployment Policy

Use the `Deployment_Policy` sheet and `outputs/practice_api_smoke/release_gate.csv`.

| Task | Workflow | Auto-answer Eligible | Reason | Required Guardrail |
| ---- | -------- | -------------------- | ------ | ------------------ |
| TODO | TODO     | yes/no               | TODO   | TODO               |

## Release Gate Summary

Use `release_gate.csv`.

| Task | Model | Workflow | Decision | Blockers | Required Mitigations |
| ---- | ----- | -------- | -------- | -------- | -------------------- |
| TODO | TODO  | TODO     | TODO     | TODO     | TODO                 |

## Data Routing Summary

Use `Data_Routing_Summary` and `Badcase_Cards`.

| Data Route     | What Goes Here                                                    | Next Action                                           |
| -------------- | ----------------------------------------------------------------- | ----------------------------------------------------- |
| `human_review` | High-risk or low-confidence outputs.                              | Human calibration and release-blocking review.        |
| `badcase`      | Regression-worthy failures such as overclaim or fabricated basis. | Add to regression eval set.                           |
| `preference`   | Paired good/bad outputs for the same case.                        | Build preference pairs for risk-control behavior.     |
| `sft`          | Stable improvement examples such as missing evidence warning.     | Convert into supervised training examples.            |
| `eval`         | Diagnostic coverage samples.                                      | Hold out for future model/workflow regression checks. |

## Representative Badcases

### Badcase 1: Consultation Overclaim

- sample_id: TODO
- model/workflow: TODO
- failure: TODO
- product decision: TODO
- data route: TODO

### Badcase 2: Case Analysis Reasoning Gap

- sample_id: TODO
- model/workflow: TODO
- failure: TODO
- product decision: TODO
- data route: TODO

### Badcase 3: Document Drafting Risk

- sample_id: TODO
- model/workflow: TODO
- failure: TODO
- product decision: TODO
- data route: TODO

## Judge Calibration Plan

For this smoke run:

- 100% of outputs are scored by rubric-based LLM judge.
- `human_review_calibration.csv` targets 20% of outputs, prioritizing all critical failures and a
  stratified sample across model/workflow/task. If critical rows exceed 20%, the file intentionally
  exceeds the target sample rate.
- Critical items override average score.
- Pairwise comparisons should swap A/B order when used for preference examples.
- Report judge-human agreement before making claims about model superiority.

## Final Product Decision

TODO: Write this as a deployment decision, not a ranking.

Example:

> The safest first release policy is to allow auto-answer only for low-risk document-drafting tasks
> when W3 passes risk checks. Consultation and high-risk case analysis should use W3 plus
> human_review routing. Overclaim and missing-evidence failures should feed preference and SFT data
> production respectively, while legal-basis failures should be reserved as regression badcases.
