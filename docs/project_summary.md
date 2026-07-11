# Project Summary

## One-Line Summary

Built a pilot-scale legal AI product-boundary evaluation and data-governance workflow that connects scenario design, API reliability, rubric signals, human review, release controls, and next-round data-asset candidates.

中文一句话：

构建法律 AI 产品边界评测与数据治理工作流，判断回答应直接放行、限定来源、先追问、转人工还是阻断，并在复核后规划 eval、SFT、preference、badcase 与 regression 数据资产候选。

## Current Scope

| Layer | Scope | Evidence boundary |
| --- | ---: | --- |
| Core diagnostic data | 85 samples、3 task categories、380 rubric items | 项目构造数据，不代表真实线上分布 |
| Product-boundary bank | 50 cases、6 slices | 用于场景覆盖和产品诊断，不是统计 benchmark |
| Mock/synthetic diagnostics | 546-run 默认管线；1,250-run product-boundary mock | 验证字段、路由、聚合和 Dashboard，不是模型能力证据 |
| Product-boundary API pilot | 12 × 5 千帆托管模型槽位 × 5 workflows = 300 API runs | 271 条非空回答、29 条空响应；不是 300 条有效答案 |
| RAG V2 API pilot | 8 × 3 千帆托管模型槽位 × 3 workflows = 72 API runs | controlled corpus 与自动 triage，不是最终法律正确性 |
| A5 API pilot | 8 × 3 千帆托管模型槽位 = 24 traces / 72 turns | trace 框架已跑通，质量标签尚未逐条人工校准 |
| Priority review | 80 条富集记录、2 名法律背景 reviewer | 非随机；公开证据不能复算 reviewer-level IAA |

## Implementation Highlights

- Separated agent-visible `Eval_Input` from judge/reviewer-only `Gold_Labels` and `Rubric_Items`.
- Built a normalized run log that preserves model slot, workflow, visible fields, output status, latency, and cost signals.
- Added controlled RAG retrieval logs, source-boundary checks, citation verification, and claim-level triage.
- Preserved empty API responses and parse failures as reliability evidence instead of silently dropping them.
- Designed task-specific rubrics, error taxonomy, review sampling, release gates, case cards, and a lightweight evidence package.
- Separated per-response `response_policy`, review `workflow_status`, group-level
  `release_gate_decision`, and downstream `data_asset_routes`; legacy aliases are compatibility-only.

## Human Review

Two legal-background reviewers independently reviewed 80 priority-enriched records and reconciled disagreements; one reviewer holds a doctorate in law and passed China’s national unified legal professional qualification examination.

The public repository does not preserve anonymous reviewer A/B labels, so this version does not report inter-reviewer agreement, judge-human agreement, Cohen's kappa, or a population accuracy estimate. See [Human Review Methodology](human_review_methodology.md).

## Product Findings

- A run-level success status does not guarantee a usable answer: the 300-run product-boundary pilot contains 29 empty responses.
- A total judge score is not a deployment decision; source boundary, material-claim support,
  critical failures, and human-review requirements need separate checks.
- Retrieval success is not answer release readiness. RAG needs source filtering, citation coverage, and claim-to-source support validation.
- Human review is a workflow, not a training-data category. Only reviewed and accepted records should become reusable assets.
- A5 must be evaluated as a complete trace. Until the 24 traces receive reviewer-level calibration, deterministic flags remain queueing signals rather than quality metrics.

## Core Artifacts

- [README](../README.md)
- [Case Study](case_study.md)
- [Human Review Methodology](human_review_methodology.md)
- [DeepSeek Product Note](deepseek_product_note.md)
- [Product-Boundary Results](results_product_boundary_eval.md)
- [RAG V2 Results](rag_v2_focused_results.md)
- [A5 Pilot](a5_multiturn_pilot_results.md)
- [Product PRD](product_prd.md)
- [Data Card](data_card.md)
- [Runbook](runbook.md)

## Interview Pitch

I built a pilot-scale legal AI product-boundary evaluation and data-governance workflow. The key
output is not a model ranking: it is an auditable decision about whether a response should be
released, grounded, clarified, reviewed, or blocked, followed by a reviewed data disposition.

I ran 300 Qianfan API records across 12 cases, five hosted model slots, and five workflows; 271
responses were non-empty and 29 were empty. I then added an 8 × 3 × 3 RAG pilot, a 24-trace
multi-turn intake pilot, and a priority human-review workflow. The evidence supports product
diagnosis and next-round data design, not production legal advice or statistical model superiority.

## Next Steps

1. Preserve reviewer A/B and adjudicated labels for reproducible IAA.
2. Human-calibrate all 24 A5 traces before reporting trace quality metrics.
3. Keep legacy aliases compatibility-only and enforce schema-contract tests when regenerating public artifacts.
4. Add random review sampling, preregistered metrics, confidence intervals, and larger samples before any model comparison.
