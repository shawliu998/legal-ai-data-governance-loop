# Qianfan Multi-Vendor Smoke Results

## Positioning

This report compares Qianfan-hosted model vendor slots as model-workflow configurations for legal AI deployment.
It is not a vendor leaderboard.

Core question:

> For each legal task slice, which vendor/model family and workflow combination is safe, cost-effective, and suitable for auto-answer, human review, or data production?

## Run Metadata

| Field | Value |
| --- | --- |
| Dataset manifest | `data/practice_benchmark_pilot/dataset_manifest.yaml` |
| Config | `config.qianfan_vendors_smoke.yaml` |
| Output directory | `outputs/qianfan_vendors_smoke` |
| Platform | Baidu Qianfan ModelBuilder |
| Base URL | `https://qianfan.baidubce.com/v2` |
| Sample count | 8 |
| Vendor slots | ERNIE 5.0, DeepSeek V4 Pro, Qwen3.5-27B, GLM 5.2, Kimi K2.6 |
| Workflows | W0 closed-book, W1 structured legal prompt, W3 risk-control workflow |
| Total model outputs | 96 |
| Judge model | TODO |

## Executive Findings

Fill after the run:

1. TODO: Best model-workflow candidate for low-risk document drafting.
2. TODO: Best model-workflow candidate for case analysis.
3. TODO: Consultation slices requiring human review regardless of model.
4. TODO: Vendor/model family with strongest cost-latency tradeoff.
5. TODO: Highest-priority data production action.

## Vendor By Task Slice

| Task Slice | Best Candidate | Avoid / Human Review | Reason | Data Action |
| --- | --- | --- | --- | --- |
| Consultation | TODO | TODO | TODO | TODO |
| Case analysis | TODO | TODO | TODO | TODO |
| Document drafting | TODO | TODO | TODO | TODO |

## Workflow Impact

| Workflow | Product Interpretation | Observed Result |
| --- | --- | --- |
| W0 closed-book | Tests raw model tendency and overclaim risk. | TODO |
| W1 structured legal prompt | Tests whether legal framing improves reasoning and boundaries. | TODO |
| W3 risk-control workflow | Tests deployable behavior: intake, missing facts, risk review, routing. | TODO |

## Release Gate Summary

Use `outputs/qianfan_vendors_smoke/release_gate.csv`.

| Task | Vendor | Model Family | Workflow | Decision | Blockers | Required Mitigations |
| --- | --- | --- | --- | --- | --- | --- |
| TODO | TODO | TODO | TODO | TODO | TODO | TODO |

## Human Review Calibration

Use `outputs/qianfan_vendors_smoke/human_review_calibration.csv`.

- Critical failures are mandatory review items.
- Non-critical rows are stratified by task, vendor/model, workflow, and risk.
- Summarize judge-human agreement before claiming one vendor is better.

## Product Policy

Write final policy as routing, not ranking:

```text
Auto-answer eligible:
Human-review required:
Preferred model/workflow by task:
Fallback model/workflow:
Release blockers:
Next badcase set:
Next SFT candidates:
Next preference pairs:
Eval holdout additions:
```
