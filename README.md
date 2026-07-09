# 投递版作品集摘要

## 一句话定位

这是一个**法律 AI 数据产品与治理系统**：把法律 AI 评测产品化为需求拆解、数据标准、
rubric eval、人审校准、release gate、badcase routing、RAG source-boundary 检查、dashboard
证据包，以及下一轮 eval / SFT / preference / regression / human review 数据生产闭环。

方法上受 PLawBench 等 rubric-based legal evaluation 思路启发，但本项目不是 PLawBench 复现，
也不是单纯 benchmark 或模型排行榜。

## 目标岗位

- 专业领域数据产品经理
- 法律数据产品经理
- 模型数据策略 / 模型评测与数据治理相关岗位

## 解决的问题

法律 AI 产品不能只问“模型答得好不好”，还必须判断：

- 这个场景是否应该自动回答，还是应该先追问、检索、转人工或阻断发布。
- RAG 输出是否真的只使用允许来源，关键法律主张是否有来源支持。
- 高风险、事实不足、引用缺陷、过度承诺、对抗性需求如何进入人审和 release gate。
- 失败样本应该沉淀成 eval、SFT、preference、badcase、regression 或 human review 数据资产。

## 核心机制

- **Rubric eval**：按法律咨询、案情分析、文书起草等任务设计 judge rubric。
- **数据标准**：将 `Eval_Input`、`Gold_Labels`、`Rubric_Items`、run logs、release gate 和
  data route 分层管理，避免标注泄漏。
- **人审校准**：对高风险、citation issue、release blocker 富集样本进行人工复核。
- **Release gate**：把 fabricated citation、unsupported claim、out-of-scope source、missed
  escalation 等问题转成发布阻断或 limited release 策略。
- **Badcase routing**：把失败样本路由到 eval、SFT、preference、badcase、regression、human_review。
- **RAG source-boundary 检查**：在 source-limited 任务里检查检索来源、引用覆盖和 claim-level
  support。
- **A5 多轮 intake trace eval**：评估模型在多轮法律 intake 中是否追问关键事实、挑战错误前提、控制
  overclaim 并转人工。

## 关键产出

- 50-case legal product-boundary eval bank。
- 300 条真实 Qianfan API model-agent 输出。
- 80 条 priority real outputs 人审校准结果。
- 72-output RAG V2 focused pilot。
- 24-trace / 72-turn A5 multi-turn intake pilot。
- Release gate、人审队列、data routing、dashboard、redacted evidence package、模型边界 memo
  和面试材料。

## 关键结果

- 300 / 300 真实 Qianfan API 输出完成，300 / 300 Qwen judge 输出成功解析。
- 80 条 priority 输出已完成人审；在高风险 / blocker 富集样本上 judge-human agreement 为 92.5%。
- RAG V2 72 条真实输出显示：retrieval 能提升证据可用性，但 source-boundary 和 claim-level
  citation gate 仍是上线前必需控制。
- A5 full pilot 完成 24 traces / 72 turns；deterministic trace pass rate 为 75.0%，并将 6 条
  overclaim-flagged traces 路由为优先人审候选。
- 项目产出的不是“谁分最高”的结论，而是 auto-answer、RAG required、clarification required、
  human review、blocked release 和下一轮数据生产策略。

## 推荐阅读路径

1. 先看本 README 的摘要和主线。
2. 看一页结论：[docs/final_portfolio_findings.md](docs/final_portfolio_findings.md)。
3. 看项目总览：[docs/project_summary.md](docs/project_summary.md)。
4. 看真实 API 与 release gate 结果：
   [docs/results_product_boundary_eval.md](docs/results_product_boundary_eval.md)。
5. 看 RAG source-boundary 结果：
   [docs/rag_v2_focused_results.md](docs/rag_v2_focused_results.md)。
6. 看多轮 intake trace eval：
   [docs/a5_multiturn_pilot_results.md](docs/a5_multiturn_pilot_results.md)。
7. 面试前看：[docs/role_fit_deepseek_data_pm.md](docs/role_fit_deepseek_data_pm.md) 和
   [docs/interview_pitch_deepseek_zh.md](docs/interview_pitch_deepseek_zh.md)。

## 投递时不要这样说

- 不要说这是 PLawBench 复现。
- 不要说这是统计显著的公开法律模型 benchmark。
- 不要说 RAG 已经解决法律幻觉。
- 不要说 A5 已具备自动法律 intake 发布能力。
- 不要把 Qwen judge 分数包装成最终模型排名。

# Legal AI Data Governance Loop

This portfolio project turns legal AI evaluation into a data-governance loop: rubric evaluation,
human calibration, release gates, badcase routing, RAG source-boundary checks, dashboards, and
next-round data production decisions.

## This Is Not

- Not a public model leaderboard.
- Not only a prompt comparison.
- Not a legal chatbot demo.

## Core Questions

- Can the model answer?
- Should it answer?
- Should it ask clarifying questions?
- Should it retrieve grounded sources?
- Are citations supported?
- Should it route to human review?
- Should it be blocked by release gate?
- What data asset should the failure become?

The project is intentionally scoped to controlled local RAG, with no Web UI, no database, and no
open-web legal retrieval.

Core artifacts include a leakage-safe eval dataset, controlled RAG corpus, rubric-based judge,
normalized run logs, human calibration queue, release gate, data router, evidence packages, and
product decision memos.

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

The legacy `V0` / `V1` / `V3` / `V4` / `V5` labels remain in code and artifacts for reproducibility.
The product-level interpretation uses A0-A5.

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

## Open First / Recommended Reading Order

- Final portfolio findings: [docs/final_portfolio_findings.md](docs/final_portfolio_findings.md)
- Project summary: [docs/project_summary.md](docs/project_summary.md)
- Product-boundary results:
  [docs/results_product_boundary_eval.md](docs/results_product_boundary_eval.md)
- Agent product eval V2 design:
  [docs/legal_agent_product_eval_v2_design.md](docs/legal_agent_product_eval_v2_design.md)
- Model boundary memo: [docs/model_boundary_memo.md](docs/model_boundary_memo.md)

## What Not To Claim

This repository should not be read as:

- a public legal model leaderboard,
- a production legal advice system,
- a claim that the 450-output focused run has already been completed,
- a claim that RAG alone solves legal hallucination,
- a claim that Qwen-judge scores are final model rankings.

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
- Interview talk track: [docs/interview_talk_track.md](docs/interview_talk_track.md)
- Chinese interview pitch: [docs/interview_pitch_zh.md](docs/interview_pitch_zh.md)
- DeepSeek role fit: [docs/role_fit_deepseek_data_pm.md](docs/role_fit_deepseek_data_pm.md)
- DeepSeek Chinese interview pitch:
  [docs/interview_pitch_deepseek_zh.md](docs/interview_pitch_deepseek_zh.md)
- Chinese resume bullets: [docs/resume_bullets_zh.md](docs/resume_bullets_zh.md)
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
