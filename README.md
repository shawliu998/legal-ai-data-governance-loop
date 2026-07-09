# Legal AI Data Governance & Evaluation 

## 项目概览

本项目围绕法律 AI 的产品边界和数据治理展开，关注模型输出在法律咨询、案情分析、文书生成、限定来源问答和多轮 intake 等场景中的可用性、风险等级和后续处理方式。

项目构建法律任务样本、评分规则、人审队列、发布门槛和数据分流流程。模型输出经过自动评分和抽样复核后，被标记为回归测试、人审、训练数据、偏好数据、发布阻断案例等不同用途。

## 项目背景

法律 AI 的风险不只来自错误答案，也可能来自事实不足、依据不清、风险提示缺失、过度确定等情况。因此，本项目将单条输出放回产品流程中判断：是否可直接回复，是否需要追问，是否需要引用来源，是否应转人工，是否触发发布门槛。

## 完成内容

- 构建 50-case legal product-boundary eval bank，覆盖法律咨询、案情分析、文书生成、限定来源问答、风险校准和对抗性请求。
- 跑通 300 条真实 Qianfan API model-agent 输出。
- 完成 80 条 priority real outputs 人审校准。
- 完成 72-output RAG V2 focused pilot。
- 完成 24-trace / 72-turn A5 multi-turn intake pilot。
- 配套产出 PRD、标注 SOP、rubric、judge prompts、human review queue、release gate、data routing、dashboard 和脱敏证据包。

## 与法律数据产品工作的关系

本项目对应法律数据产品中的场景拆解、评价标准设计、质检与人审流程、风险样本沉淀和数据资产流转。dashboard、release gate 和脱敏证据包用于记录判断依据，支持后续产品策略和数据生产安排。

## 概览

- [docs/final_portfolio_findings.md](docs/final_portfolio_findings.md)：项目结论
- [docs/project_summary.md](docs/project_summary.md)：整体流程和 pilot 汇总
- [docs/case_cards/](docs/case_cards/)：典型 badcase 复盘
- [docs/results_product_boundary_eval.md](docs/results_product_boundary_eval.md)：真实 API 与 release gate 结果
- [docs/rag_v2_focused_results.md](docs/rag_v2_focused_results.md)：RAG source-boundary 结果
- [docs/a5_multiturn_pilot_results.md](docs/a5_multiturn_pilot_results.md)：多轮 intake trace 结果

## 项目边界

本项目为 pilot-scale 产品诊断实验，RAG 语料和评测样本均为受控实验材料。结果用于分析模型输出问题、发布门槛、人审路由和后续数据流转，不用于法律咨询服务或公开模型排名。

## Evaluation Questions

- Can the model answer directly?
- Should it ask clarifying questions first?
- Does the answer need grounded sources?
- Are cited sources within the allowed corpus?
- Are key claims supported by the cited material?
- Should the case route to human review?
- Should the output be blocked by the release gate?
- What data asset should the failure become?

![Product evaluation system preview](assets/product_eval_system_preview.png)

## Main Track

The primary evaluation path is:

```text
50-case legal product-boundary eval bank
-> 300 real Qianfan API model-agent outputs
-> 72-output RAG V2 focused pilot
-> 24-trace / 72-turn A5 multi-turn intake pilot
-> human calibration
-> release gate
-> data routing
-> final portfolio findings
```

## Agent Configurations

| Architecture                     | Product meaning                                           | Legacy alias |
| -------------------------------- | --------------------------------------------------------- | ------------ |
| A0 baseline closed-book          | Direct answer without product controls                    | V0           |
| A1 structured legal counsel      | Structured legal reasoning with risk-calibrated response  | V1           |
| A2 grounded retrieval counsel    | Retrieval-grounded answer with controlled sources         | V4           |
| A3 verifier-router policy layer  | Post-generation verification, routing, and release policy | V3           |
| A4 clarification-first intake    | Single-turn clarification before answering                | V5           |
| A5 multi-turn legal intake agent | Multi-turn intake with user behavior variants             | New pilot    |

Legacy V0 / V1 / V3 / V4 / V5 labels are kept in code and artifacts for reproducibility.
The project-level discussion uses A0-A5.

## Current Evidence

- 300 / 300 real Qianfan API model-agent outputs completed across 5 models and 5 agent
  configurations.
- 80 priority real outputs reviewed by humans, with 92.5% agreement on a high-risk /
  blocker-enriched review sample.
- 72-output RAG V2 pilot completed; retrieval improved evidence availability, while source-boundary
  and claim-level citation checks remained necessary.
- 24-trace / 72-turn A5 pilot completed; the trace-level intake pipeline exposed material-fact
  elicitation and overclaim-control calibration needs.
- The project produces release-gate, human-review, data-routing, dashboard, and redacted evidence artifacts.

## Core Artifacts

- Leakage-safe eval dataset
- Controlled RAG corpus
- Rubric-based judge prompts
- Normalized model run logs
- Human calibration queue
- Release gate table
- Data routing table
- Claim and citation checks
- Dashboard workbook
- Redacted evidence packages
- Product decision memos

## Where to Start

- [docs/final_portfolio_findings.md](docs/final_portfolio_findings.md): final portfolio findings
- [docs/project_summary.md](docs/project_summary.md): project summary
- [docs/results_product_boundary_eval.md](docs/results_product_boundary_eval.md): product-boundary results
- [docs/rag_v2_focused_results.md](docs/rag_v2_focused_results.md): RAG V2 focused results
- [docs/a5_multiturn_pilot_results.md](docs/a5_multiturn_pilot_results.md): A5 multi-turn intake results
- [docs/case_cards/](docs/case_cards/): selected badcase case cards
- [docs/runbook.md](docs/runbook.md): reproduction steps

## Evidence Packages

- [outputs/product_boundary_api_pilot_v1/](outputs/product_boundary_api_pilot_v1/):
  real API pilot evidence package
- [outputs/rag_v2_focused_pilot_v1/](outputs/rag_v2_focused_pilot_v1/):
  RAG V2 evidence package
- [outputs/a5_multiturn_intake_smoke/](outputs/a5_multiturn_intake_smoke/):
  A5 smoke evidence package
- [outputs/a5_multiturn_intake_pilot_v1/](outputs/a5_multiturn_intake_pilot_v1/):
  A5 full pilot evidence package

## Reproduction

Environment setup, data preparation, validation, mock runs, API runs, release-gate generation, and
dashboard reproduction are documented in [docs/runbook.md](docs/runbook.md).

Main dataset files:

- [dataset_manifest.yaml](dataset_manifest.yaml)
- [data/eval_input.csv](data/eval_input.csv)
- [data/gold_labels.csv](data/gold_labels.csv)
- [data/rubric_items.csv](data/rubric_items.csv)
- [data/sample_metadata.csv](data/sample_metadata.csv)

Generated CSV outputs are reproducible and ignored by Git. The dashboard workbook is committed as a
reviewable output artifact: [outputs/executive_dashboard.xlsx](outputs/executive_dashboard.xlsx).

## Supporting Tracks

- 85-sample diagnostic dataset for pipeline stress testing and dashboard reproduction.
- Practice benchmark pilot for adapted real-practice task coverage.
- Qianfan vendor smoke tests for endpoint and model availability.
- RAG citation and claim-entailment checks for source-boundary analysis.

These tracks support reproducibility and engineering checks. They are not the primary evaluation path.

## Project Boundary

This is a pilot-scale product diagnosis and data-governance project. The controlled RAG corpus and
eval samples are experimental materials. Results are used to analyze model behavior, release-gate
decisions, human-review routing, and next-round data production. They are not used for legal advice,
production legal retrieval, or public model ranking.
