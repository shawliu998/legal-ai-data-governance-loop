# Experiment Design

## Positioning

This is a compact evaluation framework for legal AI data-loop governance. It is designed to support
data product decisions through a self-contained diagnostic dataset.

The workflow uses a compact legal task set and rubric-based judging structure, then implements a
lightweight data loop:

1. Normalize legal samples.
2. Prevent gold label leakage.
3. Run multiple prompt versions across multiple model aliases.
4. Judge outputs with task-specific rubrics.
5. Route failures into data-use buckets.
6. Generate a dashboard for data production decisions.

The current product-boundary extension includes controlled local RAG and citation verification. It
still excludes Web UI, database storage, and open-web legal retrieval.

## Dataset Layers

`Eval_Input` is visible to V0, V1, V2, and V3:

- `sample_id`
- `source_dataset`
- `task_category`
- `user_question`
- `known_facts`
- `legal_concepts`
- `jurisdiction`
- `law_snapshot_date`
- `task_type`
- `legal_advice_boundary`

`Gold_Labels` is visible only to Judge and Human Review:

- `key_missing_facts`
- `expected_clarification_questions`
- `expected_answer_points`
- `risk_points`
- `expected_behavior`
- `human_review_note`

`Rubric_Items` is visible only to Judge and Human Review.

This separation is the primary leakage-control design.

## Dataset Scale

The current diagnostic dataset contains 85 samples:

- `self_authored_core_40`: 40 high-quality core samples.
- `extended_diagnostic_45`: 45 internal extended diagnostic samples.

Task categories:

- `consultation`
- `case_analysis`
- `document_drafting`

The extended samples are for task coverage, scale testing, and data-routing calibration.

An optional practice benchmark pilot can be generated separately under
`data/practice_benchmark_pilot/`. It contains 30 licensed adapted practice samples by default:

- 20 `case_analysis` samples
- 6 `consultation` samples
- 4 `document_drafting` samples
- 155 rubric rows

This pilot is intentionally not merged into the default 85-sample manifest. It is used for
higher-difficulty real-practice evaluation and API runs while keeping the default diagnostic run
deterministic and stable.

## Agent Versions

V0 Direct Answer: Baseline direct response using only `Eval_Input`.

V1 Answer Protocol: Structured legal-information response using only `Eval_Input`.

V2 Blind Review Agent: Reviews V0 output using only `Eval_Input` plus V0 output. It cannot see gold
labels.

V3 Workflow Agent: Runs intake, clarification, legal analysis, risk review, rewrite, and logger
using only `Eval_Input`.

## Experiment Matrix

Full diagnostic run:

- 85 samples
- 3 model aliases
- V0 and V3
- 510 runs

Deep supplement:

- 6 selected badcases from the upgraded core workbook
- 3 model aliases
- V1 and V2 only
- 36 additional runs

Total mock/full run count:

- 546 normalized runs

Practice benchmark pilot run:

- 30 adapted practice samples
- 3 model aliases
- V0, V1, and V3
- 270 normalized runs

Practice API smoke run:

- 12 adapted practice samples
- 3 model aliases
- W0/V0 closed-book answer, W1/V1 structured legal prompt, W3/V3 risk-control workflow
- 108 normalized API outputs
- output-level latency, token count, estimated cost, judge score, critical failure label,
  human-review decision, and data route

The API smoke run should be interpreted as a deployment-eval experiment:

- Which task slices can be auto-answered?
- Which slices require stronger workflow or human review?
- Which model-workflow pair is cost-effective for each task type?
- Which failures should become badcases, SFT examples, preference pairs, or holdout eval samples?

## Task-Specific Judge

Judge can see `Eval_Input`, `Gold_Labels`, and `Rubric_Items`.

Consultation judge focuses on:

- missing facts
- clarification quality
- risk warning
- overclaim control

Case analysis judge focuses on:

- conclusion framing
- fact organization
- reasoning
- legal grounding
- claim/defense and procedure risks

Document drafting judge focuses on:

- document structure
- claims or defenses
- fact organization
- missing attachments/evidence
- risk omissions

The unified score dimensions remain stable across tasks:

- `missing_facts_awareness`
- `clarification_quality`
- `legal_grounding`
- `fact_rule_application`
- `conditional_reasoning`
- `risk_coverage`
- `overclaim_control`
- `hallucination_control`
- `data_tag_usability`

`score_rate = total_score / max_score`.

## Data Routing

Allowed `data_route` values:

- `eval`
- `sft`
- `preference`
- `badcase`
- `human_review`

Examples:

- fabricated citation, high risk, low judge confidence -> `human_review`
- overclaim -> `preference` or `badcase`
- missing facts -> `eval` or `sft`
- missing evidence warning -> `sft`
- weak fact-rule application -> `eval`

The dashboard is a data production panel. It should answer what data to build next, not which model
is best.
