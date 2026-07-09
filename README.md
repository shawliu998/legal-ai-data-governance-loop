# Legal AI Data Governance & Evaluation 

## 项目概览

本项目围绕法律 AI 的产品边界和数据治理展开，关注模型输出在法律咨询、案情分析、文书生成、限定来源问答和多轮 intake 等场景中的可用性、风险等级和后续处理方式。

项目构建法律任务样本、评分规则、人审队列、发布门槛和数据分流流程。模型输出经过自动评分和抽样复核后，被标记为回归测试、人审、训练数据、偏好数据、发布阻断案例等不同用途。

## 项目背景

法律 AI 的风险不只来自错误答案，也可能来自事实不足、依据不清、风险提示缺失、过度确定等情况。因此，本项目将单条输出放回产品流程中判断：是否可直接回复，是否需要追问，是否需要引用来源，是否应转人工，是否触发发布门槛。

## 完成内容

构建 50-case legal product-boundary eval bank，覆盖法律咨询、案情分析、文书生成、限定来源问答、风险校准和对抗性请求。
跑通 300 条真实 Qianfan API model-agent 输出。
完成 80 条 priority real outputs 人审校准。
完成 72-output RAG V2 focused pilot。
完成 24-trace / 72-turn A5 multi-turn intake pilot。
配套产出 PRD、标注 SOP、rubric、judge prompts、human review queue、release gate、data routing、dashboard 和脱敏证据包。

## 与法律数据产品工作的关系

本项目对应法律数据产品中的场景拆解、评价标准设计、质检与人审流程、风险样本沉淀和数据资产流转。dashboard、release gate 和脱敏证据包用于记录判断依据，支持后续产品策略和数据生产安排。

## 概览

docs/final_portfolio_findings.md：项目结论
docs/project_summary.md：整体流程和 pilot 汇总
docs/case_cards/：典型 badcase 复盘
docs/results_product_boundary_eval.md：真实 API 与 release gate 结果
docs/rag_v2_focused_results.md：RAG source-boundary 结果
docs/a5_multiturn_pilot_results.md：多轮 intake trace 结果

## 项目边界

本项目为 pilot-scale 产品诊断实验，RAG 语料和评测样本均为受控实验材料。结果用于分析模型输出问题、发布门槛、人审路由和后续数据流转，不用于法律咨询服务或公开模型排名。



## Evaluation Questions

The project tracks legal AI outputs through product and data-governance decisions:

Can the model answer directly?
Should it ask clarifying questions first?
Does the answer need grounded sources?
Are cited sources within the allowed corpus?
Are key claims supported by the cited material?
Should the case route to human review?
Should the output be blocked by the release gate?
What data asset should the failure become?

![Product evaluation system preview](assets/product_eval_system_preview.png)

## Main Track

The main track is:

```text
50-case legal product-boundary eval bank
-> 300-output real Qianfan API pilot
-> 72-output RAG V2 focused pilot
-> 24-trace A5 multi-turn intake pilot
-> human calibration
-> release gate and data routing
-> final portfolio findings
-> trace-level eval design
```

Agent architecture naming:

| Agent architecture               | Product meaning                                           | Legacy alias |
| -------------------------------- | --------------------------------------------------------- | ------------ |
| A0 baseline closed-book          | Direct answer without product controls                    | V0           |
| A1 structured legal counsel      | Structured legal reasoning and risk-calibrated answer     | V1           |
| A2 grounded retrieval counsel    | Retrieval-grounded answer with controlled sources         | V4           |
| A3 verifier-router policy layer  | Post-generation verification, routing, and release policy | V3           |
| A4 clarification-first intake    | Single-turn clarification before answering                | V5           |
| A5 multi-turn legal intake agent | Multi-turn intake with user behavior variants             | New pilot    |



## Current Evidence

- 300 / 300 real Qianfan API model-agent outputs completed across 5 models and 5 agent
  configurations.
- 80 priority real outputs were human-reviewed; agreement was 92.5% on a high-risk/blocker-enriched
  review sample.
- 72-output RAG V2 pilot showed retrieval helps evidence availability, but source-boundary and
  claim-level citation gates remain required.
- 24-trace A5 pilot shows the trace-level legal intake eval pipeline can run and exposes
  material-fact elicitation and overclaim-control calibration needs.
- The project produces release-gate, human-review, data-routing, and redacted evidence artifacts
  instead of a model ranking.

## Evidence Packages

- Real API pilot evidence package:
  [outputs/product_boundary_api_pilot_v1/](outputs/product_boundary_api_pilot_v1/)
- RAG V2 evidence package: [outputs/rag_v2_focused_pilot_v1/](outputs/rag_v2_focused_pilot_v1/)
- A5 smoke evidence package:
  [outputs/a5_multiturn_intake_smoke/](outputs/a5_multiturn_intake_smoke/)
- A5 full pilot evidence package:
  [outputs/a5_multiturn_intake_pilot_v1/](outputs/a5_multiturn_intake_pilot_v1/)

## Where To Start

- Final portfolio findings: [docs/final_portfolio_findings.md](docs/final_portfolio_findings.md)
- Project summary: [docs/project_summary.md](docs/project_summary.md)
- Product-boundary results:
  [docs/results_product_boundary_eval.md](docs/results_product_boundary_eval.md)
- Agent product eval V2 design:
  [docs/legal_agent_product_eval_v2_design.md](docs/legal_agent_product_eval_v2_design.md)
- Model boundary memo: [docs/model_boundary_memo.md](docs/model_boundary_memo.md)

## Core Artifacts

Leakage-safe eval dataset
Controlled RAG corpus
Rubric-based judge prompts
Normalized model run logs
Human calibration queue
Release gate table
Data routing table
Claim and citation checks
Dashboard workbook
Redacted evidence packages
Product decision memos

## Appendix

- Trace-level eval schema: [docs/trace_level_eval_schema.md](docs/trace_level_eval_schema.md)
- Focused V2 run plan:
  [docs/legal_agent_product_eval_v2_focused_run_plan.md](docs/legal_agent_product_eval_v2_focused_run_plan.md)
- Focused V2 root config:
  [config.legal_agent_product_eval_v2_focused.yaml](config.legal_agent_product_eval_v2_focused.yaml)
- Focused V2 planned config:
  [configs/experiments/legal_agent_product_eval_v2_focused.yaml](configs/experiments/legal_agent_product_eval_v2_focused.yaml)
- Product PRD: [docs/product_prd.md](docs/product_prd.md)
- RAG V2 focused results: [docs/rag_v2_focused_results.md](docs/rag_v2_focused_results.md)
- Methodology risk register: [docs/methodology_risk_register.md](docs/methodology_risk_register.md)
- A5 smoke results: [docs/a5_multiturn_smoke_results.md](docs/a5_multiturn_smoke_results.md)
- A5 full pilot results: [docs/a5_multiturn_pilot_results.md](docs/a5_multiturn_pilot_results.md)
- A5 trace judge rubric: [docs/a5_trace_judge_rubric.md](docs/a5_trace_judge_rubric.md)
- Redacted A5 trace example:
  [outputs/a5_multiturn_intake_smoke/redacted_trace_example.md](outputs/a5_multiturn_intake_smoke/redacted_trace_example.md)
- A5 multi-turn intake pilot: [docs/multiturn_intake_pilot.md](docs/multiturn_intake_pilot.md)
- RAG V2 improvement plan: [docs/rag_v2_improvement_plan.md](docs/rag_v2_improvement_plan.md)
- Badcase case cards:
  [case 01](docs/case_cards/case_01_overconfident_legal_advice.md),
  [case 02](docs/case_cards/case_02_rag_citation_gap.md),
  [case 03](docs/case_cards/case_03_multiturn_intake_failure.md)
- Labeling SOP: [docs/labeling_sop.md](docs/labeling_sop.md)
- Technical case study: [docs/case_study.md](docs/case_study.md)
- API smoke run plan: [docs/api_smoke_run.md](docs/api_smoke_run.md)
- Reproducible dashboard: [outputs/executive_dashboard.xlsx](outputs/executive_dashboard.xlsx)
- Legacy mock dashboard preview: [assets/dashboard_preview.png](assets/dashboard_preview.png)
- Dataset design: [data/eval_input.csv](data/eval_input.csv),
  [data/gold_labels.csv](data/gold_labels.csv), [data/rubric_items.csv](data/rubric_items.csv)
- Reproduction steps: [docs/runbook.md](docs/runbook.md)
- GitHub upload guide: [docs/git_upload_guide.md](docs/git_upload_guide.md)

## Trace-Level Data Loop

```mermaid
flowchart LR
    A[User message or A5 turn plan] --> B[Agent architecture A0-A5]
    B --> C[Agent trace]
    C --> D[Retrieval events]
    C --> E[Citation checks]
    C --> F[Claim checks]
    C --> G[Risk checks]
    D --> H[Release gate]
    E --> H
    F --> H
    G --> H
    H --> I[Human review route]
    H --> J[Data route]
    J --> K[Eval / SFT / preference / badcase / regression]
```

## What It Demonstrates

- Gold label leakage prevention: Agents only see `Eval_Input`; Judge/Human Review can see
  `Gold_Labels` and `Rubric_Items`.
- Multi-task legal evaluation: `consultation`, `case_analysis`, and `document_drafting`.
- Normalized run logs: one row per model run, supporting multiple model aliases, agent
  architectures, data sources, and task categories.
- Agent architecture comparison: A0-A5 product configurations, with legacy V aliases preserved for
  reproducibility.
- Trace-level eval design: turns, retrieval, citation checks, claim checks, risk checks, release
  gate, and data route.
- A5 multi-turn intake pilot: cooperative, dependent, withdrawn, and adversarial user behavior
  variants.
- Rubric-based LLM Judge: task-specific judge prompts for consultation, case analysis, and document
  drafting.
- Human review queue: high-risk or low-confidence outputs are routed for calibration.
- Standardized error taxonomy and fixed data routes: `eval`, `sft`, `preference`, `badcase`,
  `human_review`.
- Dashboard and model-boundary memo as data decision artifacts, not ranking reports.

## Supporting Tracks

The main track is the legal product-boundary and legal agent eval path above. The repo also keeps
supporting diagnostics:

- 85-sample diagnostic dataset for pipeline stress testing and dashboard reproduction.
- Practice benchmark pilot for adapted real-practice task coverage.
- Qianfan vendor smoke tests for endpoint/model availability.

These supporting tracks are useful for reproducibility and engineering checks, but they are not the
primary product story.

## Dataset

The normalized dataset has 85 samples:

- 40 self-authored core samples from the upgraded workbook.
- 45 internally extended diagnostic samples for scale and task coverage.
- Task categories: consultation, case analysis, document drafting.

The extended samples are synthetic diagnostic scenarios designed for coverage, routing calibration,
and pipeline stress testing.

Primary files:

- `dataset_manifest.yaml`
- `data/eval_input.csv`
- `data/gold_labels.csv`
- `data/rubric_items.csv`
- `data/sample_metadata.csv`

The normalized CSV files are committed because they show the data design directly. The upgraded
40-core workbook is kept as a source artifact; the old 20-sample workbook is excluded from the
default package.

## Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install ".[test]"
cp .env.example .env
```

## Prepare Data

```bash
.venv/bin/python -m legal_eval_harness.cli prepare-data \
  --input-workbook data/Legal_AI_Data_Governance_Eval_Harness_40_Core.xlsx \
  --output-dir data
```

## Validate

```bash
.venv/bin/python -m legal_eval_harness.cli validate \
  --input dataset_manifest.yaml \
  --config config.yaml
```

Expected validation shape:

- 85 samples
- 380 rubric rows
- 3 task categories
- 546 planned normalized runs in mock/full diagnostic mode

## Run Mock Pipeline

```bash
.venv/bin/python -m legal_eval_harness.cli all \
  --input dataset_manifest.yaml \
  --config config.yaml \
  --mode mock \
  --output-dir outputs
```

Generated outputs:

- `outputs/model_run_log.csv`
- `outputs/judge_scores.csv`
- `outputs/data_routing.csv`
- `outputs/executive_dashboard.xlsx`

The full generated CSV outputs are reproducible and intentionally ignored by Git. The dashboard
workbook is committed as a reviewable output artifact.

The Excel dashboard includes:

- `Executive_Dashboard`
- `Dataset_Coverage`
- `Task_Category_Summary`
- `Badcase_Cards`
- `Data_Routing_Summary`
- `Error_Taxonomy`
- `Data_Route_Taxonomy`

For full reproduction steps and output checks, see [docs/runbook.md](docs/runbook.md).

For design rationale and selected badcase cards, see [docs/case_study.md](docs/case_study.md).

## API Mode

The LLM client supports OpenAI-compatible providers through `base_url`, `api_key`, and `model`.

```yaml
models:
  - alias: Model_A
    provider: openai_compatible
    base_url: ${MODEL_A_BASE_URL}
    api_key: ${MODEL_A_API_KEY}
    model: ${MODEL_A_NAME}
```

## Practice Benchmark Pilot

For a higher-difficulty real-practice pilot, generate a separate licensed adapted dataset:

```bash
.venv/bin/python -m legal_eval_harness.cli prepare-practice-benchmark \
  --output-dir data/practice_benchmark_pilot \
  --case-limit 20 \
  --consultation-limit 6 \
  --document-limit 4
```

Then validate or run it without changing the default 85-sample diagnostic dataset:

```bash
.venv/bin/python -m legal_eval_harness.cli validate \
  --input data/practice_benchmark_pilot/dataset_manifest.yaml \
  --config config.practice_pilot.yaml

.venv/bin/python -m legal_eval_harness.cli all \
  --input data/practice_benchmark_pilot/dataset_manifest.yaml \
  --config config.practice_pilot.yaml \
  --mode mock \
  --output-dir outputs/practice_benchmark_pilot
```

Default pilot shape:

- 30 adapted practice samples
- 155 rubric rows
- 3 task categories
- 270 planned normalized runs across V0, V1, and V3

For a real-API smoke run focused on deployment decisions:

```bash
.venv/bin/python -m legal_eval_harness.cli all \
  --input data/practice_benchmark_pilot/dataset_manifest.yaml \
  --config config.practice_api_smoke.yaml \
  --mode api \
  --output-dir outputs/practice_api_smoke
```

The API smoke config selects 12 practice samples, 3 model aliases, and 3 workflow conditions:

- `W0`: closed-book answer
- `W1`: structured legal prompt
- `W3`: risk-control workflow agent

`model_run_log.csv` includes `workflow_condition`, `latency_ms`, token counts, `estimated_cost`, and
`usage_source`, so results can be interpreted as deployment tradeoffs rather than a leaderboard.

Use [docs/results_practice_api_smoke.md](docs/results_practice_api_smoke.md) and
[docs/release_gate.md](docs/release_gate.md) to turn the run into model routing, human-review,
release-gate, and data-production decisions.

After an API run, generate the human calibration queue and release gate table:

```bash
.venv/bin/python -m legal_eval_harness.cli sample-human-review \
  --runs outputs/practice_api_smoke/model_run_log.csv \
  --scores outputs/practice_api_smoke/judge_scores.csv \
  --routing outputs/practice_api_smoke/data_routing.csv \
  --output outputs/practice_api_smoke/human_review_calibration.csv

.venv/bin/python -m legal_eval_harness.cli release-gate \
  --runs outputs/practice_api_smoke/model_run_log.csv \
  --scores outputs/practice_api_smoke/judge_scores.csv \
  --routing outputs/practice_api_smoke/data_routing.csv \
  --claim-entailment outputs/practice_api_smoke/claim_entailment.csv \
  --output outputs/practice_api_smoke/release_gate.csv
```

### Supporting Qianfan Vendor Smoke

If using Baidu Qianfan ModelBuilder, use the OpenAI-compatible endpoint:

```text
QIANFAN_BASE_URL=https://qianfan.baidubce.com/v2
```

Fill model names from the Qianfan model center into `.env`, for example:

```text
QIANFAN_MODEL_ERNIE_50=
QIANFAN_MODEL_DEEPSEEK_V4_PRO=
QIANFAN_MODEL_QWEN35_27B=
QIANFAN_MODEL_GLM_52=
QIANFAN_MODEL_KIMI_K26=
QIANFAN_JUDGE_MODEL=
```

Then run the Qianfan-hosted vendor smoke:

```bash
.venv/bin/python -m legal_eval_harness.cli all \
  --input data/practice_benchmark_pilot/dataset_manifest.yaml \
  --config config.qianfan_vendors_smoke.yaml \
  --mode api \
  --output-dir outputs/qianfan_vendors_smoke
```

Default shape:

- 8 practice samples
- 5 Qianfan-hosted model slots: ERNIE 5.0, DeepSeek V4 Pro, Qwen3.5-27B, GLM 5.2, Kimi K2.6
- 3 workflow conditions: W0, W1, W3
- 120 model outputs

This compares deployment behavior by task slice, workflow, risk route, latency, and cost. It is a
supporting availability and routing check, not the primary product story and not a vendor
leaderboard.

## Stratified Legal Product Boundary Eval

The product-boundary eval extends the project beyond hard-case smoke tests. It uses normal, hard,
risk-calibration, citation-grounding, adversarial, and counterfactual slices to reflect realistic
legal product traffic while still exposing differences among strong models.

Primary artifacts:

- Design: [docs/stratified_legal_eval_design.md](docs/stratified_legal_eval_design.md)
- Results template: [docs/results_product_boundary_eval.md](docs/results_product_boundary_eval.md)
- Dataset:
  [data/eval_sets/legal_product_boundary_pilot_v1.jsonl](data/eval_sets/legal_product_boundary_pilot_v1.jsonl)
- Qianfan config:
  [config.qianfan_product_boundary_eval.yaml](config.qianfan_product_boundary_eval.yaml)
- Runnable config:
  [config.qianfan_product_boundary_runnable.yaml](config.qianfan_product_boundary_runnable.yaml)

Validate the dataset:

```bash
.venv/bin/python -m legal_eval_harness.cli validate-product-boundary \
  --input data/eval_sets/legal_product_boundary_pilot_v1.jsonl
```

Prepare a runnable normalized manifest:

```bash
.venv/bin/python -m legal_eval_harness.cli prepare-product-boundary \
  --input-jsonl data/eval_sets/legal_product_boundary_pilot_v1.jsonl \
  --output-dir data/product_boundary_pilot
```

Run the current mock-compatible workflow mapping:

```bash
.venv/bin/python -m legal_eval_harness.cli all \
  --input data/product_boundary_pilot/dataset_manifest.yaml \
  --config config.qianfan_product_boundary_runnable.yaml \
  --mode mock \
  --output-dir outputs/product_boundary_pilot_mock
```

Run cross-judge calibration on the same model outputs:

```bash
.venv/bin/python -m legal_eval_harness.cli run-judge-ensemble \
  --input data/product_boundary_pilot/dataset_manifest.yaml \
  --config config.qianfan_product_boundary_runnable.yaml \
  --runs outputs/product_boundary_pilot_mock/model_run_log.csv \
  --mode mock \
  --output-dir outputs/product_boundary_pilot_mock
```

The ensemble layer uses DeepSeek V4 Pro and GLM-5.2 as primary judges, excludes self-evaluation, and
uses Kimi K2.6 as an arbiter when score, critical-failure, or routing labels disagree.

Legacy implementation alias mapping:

| Product architecture            | Legacy alias | Runnable workflow                                                   |
| ------------------------------- | ------------ | ------------------------------------------------------------------- |
| A0 baseline closed-book         | `V0`         | `w0_closed_book`                                                    |
| A1 structured legal counsel     | `V1`         | `w1_structured_legal_prompt`                                        |
| A2 grounded retrieval counsel   | `V4`         | `w2_rag_grounded` with local corpus retrieval and context injection |
| A3 verifier-router policy layer | `V3`         | `w3_risk_control_workflow`                                          |
| A4 clarification-first intake   | `V5`         | `w4_clarification_first`                                            |

The `V*` names remain in configs and artifacts for reproducibility. Portfolio and interview
discussion should use the A0-A5 product architecture names.

RAG component outputs:

- `retrieval_log.csv`: retrieved source IDs, expected-source recall, and context precision.
- `rag_contexts.csv`: per-run source chunks injected into V3/V4 prompts.
- `citation_verification.csv`: cited source IDs, fabricated citation IDs, claim-level support
  checks, unsupported-claim counts, and citation-fidelity labels.
- `claim_entailment.csv`: one row per extracted claim with cited source IDs, allowed-source boundary
  checks, support label, and product action.

Build claim-level citation entailment triage after RAG outputs exist:

```bash
PYTHONPATH=src .venv/bin/python -m legal_eval_harness.cli build-claim-entailment \
  --runs outputs/product_boundary_api_pilot_v1/model_run_log.csv \
  --contexts outputs/product_boundary_api_pilot_v1/rag_contexts.csv \
  --cases-jsonl data/eval_sets/legal_product_boundary_api_pilot_v1.jsonl \
  --rag-only \
  --output outputs/product_boundary_api_pilot_v1/claim_entailment.csv
```

Build a legal-review calibration queue:

```bash
.venv/bin/python -m legal_eval_harness.cli sample-human-review \
  --runs outputs/product_boundary_pilot_mock/model_run_log.csv \
  --scores outputs/product_boundary_pilot_mock/judge_scores.csv \
  --routing outputs/product_boundary_pilot_mock/data_routing.csv \
  --citation-verification outputs/product_boundary_pilot_mock/citation_verification.csv \
  --ensemble-summary outputs/product_boundary_pilot_mock/judge_ensemble_summary.csv \
  --output outputs/product_boundary_pilot_mock/human_review_calibration.csv \
  --sample-rate 0.2 \
  --min-samples 120
```

When critical rows dominate the review queue, build an additional stratified calibration file for
judge-human agreement analysis:

```bash
.venv/bin/python -m legal_eval_harness.cli sample-human-review \
  --runs outputs/product_boundary_pilot_mock/model_run_log.csv \
  --scores outputs/product_boundary_pilot_mock/judge_scores.csv \
  --routing outputs/product_boundary_pilot_mock/data_routing.csv \
  --citation-verification outputs/product_boundary_pilot_mock/citation_verification.csv \
  --ensemble-summary outputs/product_boundary_pilot_mock/judge_ensemble_summary.csv \
  --output outputs/product_boundary_pilot_mock/human_review_calibration_stratified.csv \
  --sample-rate 0.2 \
  --min-samples 120 \
  --random-calibration-min 100
```

This is not a simple leaderboard. It evaluates model-agent configurations under realistic legal
product conditions to decide product routing, release readiness, and next-round data production.

## Project Boundary

This project evaluates model behavior and routes data. It does not provide legal advice, does not
decide final legal correctness, does not perform open-web legal retrieval, and does not rank models.

The main product question is: given legal AI outputs, which failures should become eval samples, SFT
samples, preference pairs, badcases, or human review items?
